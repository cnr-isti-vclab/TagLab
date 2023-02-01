import math
import inspect
from typing import Optional, Tuple, List

import numpy as np
import cv2
import rasterio as rio

from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot, QLineF, QRectF, QPoint, QPointF
from PyQt5.QtGui import QImage, QMouseEvent, QPen, QFont, QCloseEvent, QKeyEvent, QOpenGLShaderProgram, QOpenGLShader, \
    QOpenGLVersionProfile, QMatrix4x4, QWheelEvent, QOpenGLTexture, QOpenGLFramebufferObject, QVector4D, QVector2D
from PyQt5.QtWidgets import QWidget, QHeaderView, QSizePolicy, QVBoxLayout, QLabel, QLineEdit, QTableWidget, QTableView, \
    QHBoxLayout, QTableWidgetItem, QComboBox, QSlider, QApplication, \
    QCheckBox, QPushButton, QMessageBox, QGraphicsTextItem, QGraphicsItem, QOpenGLWidget, QGraphicsRectItem
from PyQt5._QOpenGLFunctions_2_0 import QOpenGLFunctions_2_0

from source.QtImageViewer import QtImageViewer


def checkGL(obj, res):
    """
    Syntactic sugar for error check + log
    """
    if not res:
        msg = obj.log()
        print(msg.strip("\n\t "))
        callee1 = inspect.stack()[1]
        callee2 = inspect.stack()[2]
        print("\t\t^^^^^ at function '", callee1.function, "':", callee1.lineno)
        print("\t\t^^^^^ at function '", callee2.function, "':", callee2.lineno)


class QtSimpleOpenGlShaderViewer(QOpenGLWidget):
    """
    Custom widget to handle img preview with shaders.
    It handles zoom and pan of the view.
    It has a scriptable pass (defined by its derived class).
    Uses a dirty flag to ensure the update does not use extra compute power if not needed.
    """

    V_SHADER_SOURCE = """
    #version 120
    // precision highp float;
    attribute vec2 aPos;
    attribute vec2 aTex;
    varying vec2 vTex;
    uniform mat4 uMatrix;
    void main(void) {
        vTex = aTex;
        gl_Position = uMatrix * vec4(aPos, 0, 1);
    }
    """

    F_SHADER_SOURCE = """
    #version 120
    // precision highp float;
    varying vec2 vTex;
    uniform sampler2D uTex;
    void main(void) {
        if (vTex.x > 1.0 || vTex.y > 1.0) {
            gl_FragColor = vec4(0.0);
        }
        else {    
            gl_FragColor = texture2D(uTex, vTex);
        }
    }
    """

    V_SHADER_SOURCE_POINTS = """
    #version 120
    // precision highp float;
    attribute vec2 aPos;
    uniform float uSize;
    uniform mat4 uMatrix;
    void main(void) {
        gl_PointSize = uSize;
        gl_Position = uMatrix * vec4(aPos, 0, 1);
    }
    """

    F_SHADER_SOURCE_POINTS = """
    #version 120
    // precision highp float;
    uniform vec4 uCol;
    void main(void) {
        vec2 coord = (gl_PointCoord - 0.5) * 2.0;
        float distFromCenter = length(coord);
        if (distFromCenter >= 1.0) {
            gl_FragColor = vec4(0);
        } else {
            gl_FragColor = vec4(uCol);
        }
    }
    """

    REF_POINT_COLOR = QVector4D(1.0, 1.0, 1.0, 1.0)
    ALI_POINT_COLOR = QVector4D(0.0, 1.0, 1.0, 1.0)

    QUAD_V = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    QUAD_T = [(0, 1), (0, 0), (1, 1), (1, 0)]

    def __init__(self, vSrc, fSrc, parent=None):
        super(QtSimpleOpenGlShaderViewer, self).__init__(parent)
        # Open GL
        self.gl: Optional[QOpenGLFunctions_2_0] = None
        self.programs: List[QOpenGLShaderProgram] = []
        self.textures: List[QOpenGLTexture] = []
        self.framebuffers: List[QOpenGLFramebufferObject] = []
        self.pointProgram: Optional[QOpenGLShaderProgram] = None
        self.points: Tuple[List[QVector2D], List[QVector2D]] = ([], [])
        self.vSrc = vSrc
        self.fSrc = fSrc
        self.keepFB = False
        self.drawPoints = True
        # Transformation status
        self.t: QPointF = QPointF(0.0, 0.0)
        self.s = 1.0
        self.w = 100
        self.h = 100
        self.sizeL = QPointF(0, 0)
        self.sizeR = QPointF(0, 0)
        # Gesture
        self.lastPos = None
        self.minZoom = 0.25
        self.maxZoom = 128.0
        # Alignment data
        self.rot = 0
        self.tra: QPointF = QPointF(0, 0)
        # [SCALE] self.sca = 1

    def __createProgram(self, vSrc: str, fSrc: str, hasTex: bool) -> Optional[QOpenGLShaderProgram]:
        """
        Private method to create a Shader Program with passed v-shader and f-shader.
        :param: vSrc the source code of the vertex shader
        :param: fSrc the source code of the fragment shader
        :param: hasTex a boolean to toggle "aTex" attr for vertex buffer
        :return: the created program or None (on error)
        """
        # Create & Compile Vertex Shader
        vShader = QOpenGLShader(QOpenGLShader.Vertex, self)
        checkGL(vShader, vShader.compileSourceCode(vSrc))
        # Create & Compile Fragment Shader
        fShader = QOpenGLShader(QOpenGLShader.Fragment, self)
        checkGL(fShader, fShader.compileSourceCode(fSrc))
        # Create Program
        program = QOpenGLShaderProgram()
        # Attach shaders
        checkGL(program, program.addShader(vShader))
        checkGL(program, program.addShader(fShader))
        # Bind attrs
        program.bindAttributeLocation('aPos', 0)
        if hasTex:
            program.bindAttributeLocation('aTex', 1)
        # Link program
        checkGL(program, program.link())
        # Return newly created program
        return program if program.isLinked() else None

    def initializeGL(self) -> None:
        """
        Sets up the OpenGL resources and state.
        Gets called once before the first time resizeGL() or paintGL() is called.
        """
        # Load opengl for requested profile
        profile = QOpenGLVersionProfile()
        profile.setVersion(2, 0)
        self.gl = self.context().versionFunctions(versionProfile=profile)
        self.gl.initializeOpenGLFunctions()
        # Create Program #0 (default pass)
        self.programs.append(self.__createProgram(
            QtSimpleOpenGlShaderViewer.V_SHADER_SOURCE,
            QtSimpleOpenGlShaderViewer.F_SHADER_SOURCE,
            hasTex=True
        ))
        # Create Program #1 (scriptable pass)
        self.programs.append(self.__createProgram(self.vSrc, self.fSrc, hasTex=True))
        # Create Program for drawing points
        self.pointProgram = self.__createProgram(
            QtSimpleOpenGlShaderViewer.V_SHADER_SOURCE_POINTS,
            QtSimpleOpenGlShaderViewer.F_SHADER_SOURCE_POINTS,
            hasTex=False
        )

    def __drawTexturePass(self, i: int, mat: QMatrix4x4) -> None:
        """
        Private method to draw texture onto framebuffer.
        :param: i the index of texture & dest framebuffer
        :param: mat the matrix for the transformation
        """

        if self.textures is None:  # textures has not been created yet
            return

        if len(self.textures) <= i:
            return

        # Bind FB and Program
        checkGL(self.framebuffers[i], self.framebuffers[i].bind())
        checkGL(self.programs[0], self.programs[0].bind())
        # Bind texture
        self.gl.glActiveTexture(self.gl.GL_TEXTURE0)
        self.gl.glBindTexture(self.gl.GL_TEXTURE_2D, self.textures[i].textureId())
        # Update uniforms
        self.programs[0].setUniformValue("uTex", 0)
        self.programs[0].setUniformValue("uMatrix", mat)
        # Compute sizes
        maxw = max(self.sizeL.x(), self.sizeR.x())
        maxh = max(self.sizeL.y(), self.sizeR.y())
        wratio = maxw / (self.sizeL.x() if i == 0 else self.sizeR.x())
        hratio = maxh / (self.sizeL.y() if i == 0 else self.sizeR.y())
        # Reload quad data
        self.programs[0].enableAttributeArray(0)
        self.programs[0].setAttributeArray(0, QtSimpleOpenGlShaderViewer.QUAD_V.copy())
        self.programs[0].enableAttributeArray(1)
        self.programs[0].setAttributeArray(1,
                                           [(x * wratio, y * hratio) for (x, y) in QtSimpleOpenGlShaderViewer.QUAD_T])
        # Draw quad
        self.gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        self.gl.glClear(self.gl.GL_COLOR_BUFFER_BIT)
        self.gl.glDrawArrays(self.gl.GL_TRIANGLE_STRIP, 0, 4)
        # Release FB and Program
        checkGL(self.framebuffers[i], self.framebuffers[i].release())
        self.programs[0].release()

    def __drawFrameBufferPass(self, mat: QMatrix4x4) -> None:
        """
        Private method to draw framebuffer with scripted program.
        :param: mat the transformation matrix
        """

        if self.programs is None:
            return

        if len(self.programs) <= 1:  # textures has not been created yet
            return

        # Bind Program
        checkGL(self.programs[1], self.programs[1].bind())
        # Bind Textures (from Frame Buffers)
        self.gl.glActiveTexture(self.gl.GL_TEXTURE0)
        self.gl.glBindTexture(self.gl.GL_TEXTURE_2D, self.framebuffers[0].texture())
        self.gl.glActiveTexture(self.gl.GL_TEXTURE1)
        self.gl.glBindTexture(self.gl.GL_TEXTURE_2D, self.framebuffers[1].texture())
        # Update uniforms
        self.programs[1].setUniformValue("uMatrix", mat)
        self.programs[1].setUniformValue("uTexL", 0)
        self.programs[1].setUniformValue("uTexR", 1)
        # Pass custom uniforms
        self.customUniforms(self.programs[1])
        # Reload quad data
        self.programs[1].enableAttributeArray(0)
        self.programs[1].setAttributeArray(0, QtSimpleOpenGlShaderViewer.QUAD_V.copy())
        self.programs[1].enableAttributeArray(1)
        self.programs[1].setAttributeArray(1, QtSimpleOpenGlShaderViewer.QUAD_T.copy())
        # Draw quad
        self.gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        self.gl.glClear(self.gl.GL_COLOR_BUFFER_BIT)
        self.gl.glDrawArrays(self.gl.GL_TRIANGLE_STRIP, 0, 4)
        # Release Program
        self.programs[1].release()

    def __drawPointsPass(self, i: int, mat: QMatrix4x4, col: QVector4D) -> None:
        """
        Private method to draw points over the final draw pass.
        :param: i the index of the points list to draw
        :param: mat the transformation matrix
        :param: col a vec4 containing the color (normalized)
        """
        # Jump draw pass if points size is zero
        if len(self.points[i]) == 0:
            return
        # Bind Program
        checkGL(self.pointProgram, self.pointProgram.bind())
        # Update uniforms
        self.pointProgram.setUniformValue("uMatrix", mat)
        self.pointProgram.setUniformValue("uCol", col)
        self.pointProgram.setUniformValue("uSize", 10.0)
        # Reload points data
        self.pointProgram.enableAttributeArray(0)
        self.pointProgram.setAttributeArray(0, self.points[i])
        # Draw points
        self.gl.glEnable(self.gl.GL_BLEND)
        self.gl.glBlendFunc(self.gl.GL_SRC_ALPHA, self.gl.GL_ONE_MINUS_SRC_ALPHA)
        self.gl.glEnable(self.gl.GL_POINT_SPRITE)
        self.gl.glEnable(self.gl.GL_VERTEX_PROGRAM_POINT_SIZE)
        self.gl.glDrawArrays(self.gl.GL_POINTS, 0, len(self.points[i]))
        self.gl.glDisable(self.gl.GL_VERTEX_PROGRAM_POINT_SIZE)
        self.gl.glDisable(self.gl.GL_POINT_SPRITE)
        self.gl.glDisable(self.gl.GL_BLEND)
        # Release Program
        self.pointProgram.release()

    def paintGL(self) -> None:
        """
        Renders the OpenGL scene.
        Gets called whenever the widget needs to be updated.
        """
        matrix1 = QMatrix4x4()  # For 1st Quad
        matrix2 = QMatrix4x4()  # For 2nd Quad
        matrix3 = QMatrix4x4()  # Transformation Matrix
        matrix4 = QMatrix4x4()  # For reversing framebuffer
        matrix5 = QMatrix4x4()  # For normalizing points to [-1, 1]
        # Rotation (pivot is the top left corner), Translation and Scale
        matrix2.translate(self.tra.x(), -self.tra.y(), 0)
        matrix2.translate(-1.0, 1.0, 0.0)
        matrix2.rotate(-self.rot, 0.0, 0.0, 1.0)
        # [SCALE] matrix2.scale(self.sca, self.sca, 1.0)
        matrix2.translate(1.0, -1.0, 0.0)
        # Aspect Ratio / Pan / Zoom
        matrix3.scale(min(self.w, self.h) / self.w, min(self.w, self.h) / self.h, 1)
        matrix3.translate(self.t.x(), -self.t.y(), 0)
        matrix3.scale(self.s, self.s, 1)
        # Check if needs to redraw buffers
        # (Needed only when user zoom or pan or manually changes offset or rotation)
        if not self.keepFB:
            self.__drawTexturePass(0, matrix3 * matrix1)  # Draw tex 0 into fb 0
            self.__drawTexturePass(1, matrix3 * matrix2)  # Draw tex 1 into fb 1
            self.keepFB = True  # Clear dirty flag
        # Draw fb into screen (scriptable)
        matrix4.scale(1, -1, 1)
        self.__drawFrameBufferPass(matrix4)
        # Draw marker points
        matrix5.translate(-1, 1, 0)
        matrix5.scale(2, -2, 1)
        if self.drawPoints:
            self.__drawPointsPass(0, matrix3 * matrix1 * matrix5, QtSimpleOpenGlShaderViewer.REF_POINT_COLOR)
            self.__drawPointsPass(1, matrix3 * matrix2 * matrix5, QtSimpleOpenGlShaderViewer.ALI_POINT_COLOR)

    def resizeGL(self, w: int, h: int) -> None:
        """
        Sets up the OpenGL viewport, projection, etc.
        Gets called whenever the widget has been resize (and once at the beginning).
        :param: w the new width
        :param: h the new height
        """
        # Store new size
        self.w = w
        self.h = h
        # Update gl viewport
        self.gl.glViewport(0, 0, w, h)
        # Recreate frame buffers
        self.framebuffers = [
            QOpenGLFramebufferObject(w, h),
            QOpenGLFramebufferObject(w, h)
        ]
        # Redraw
        self.redraw(False)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse press event over the widget.
        :param: event the mouse event
        """
        # Filters out non left-button events
        if event.button() != Qt.LeftButton:
            return
        # Store last pos
        self.lastPos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse move event over the widget.
        :param: event the mouse event
        """
        # Check if user is dragging
        if self.lastPos is None:
            return
        # Compute movements delta
        dx = (event.x() - self.lastPos.x()) / (self.w // 2)
        dy = (event.y() - self.lastPos.y()) / (self.h // 2)
        self.lastPos = event.pos()
        # Update translation
        wh = min(self.w, self.h) / self.w
        hw = min(self.w, self.h) / self.h
        self.t.setX(self.t.x() + dx / wh)
        self.t.setY(self.t.y() + dy / hw)
        # Redraw
        self.redraw(False)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse release event over the widget.
        :param: event the mouse event
        """
        # Filters out non left-button events
        if event.button() != Qt.LeftButton:
            return
        # Clear lastPos
        self.lastPos = None

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        Callback called on a mouse wheel event over the widget.
        :param: event the mouse event
        """
        # Update scale
        lastScale = self.s
        self.s = self.s * pow(pow(2, 0.5), event.angleDelta().y() / 100.0)
        self.s = min(max(self.s, self.minZoom), self.maxZoom)
        factor = self.s / lastScale
        factor = 1
        # Find normalized mouse pos
        [mx, my] = [event.pos().x() / (self.w // 2) - 1, event.pos().y() / (self.h // 2) - 1]
        # Zoom towards mouse pos
        self.t.setX(mx - (mx - self.t.x()) * factor)
        self.t.setY(my - (my - self.t.y()) * factor)
        # Redraw
        self.redraw(False)

    def initializeData(self, referenceImg: QImage, imgToAlign: QImage, sizeL: QPointF, sizeR: QPointF,
                       referencePoints: List[QPointF], pointsToAlign: List[QPointF]) -> None:
        """
        Called by the container widget to upload data to show.
        :param: referenceImg the QImage to take as reference
        :param: imgToAlign the QImage to beg aligned
        :param: sizeL the size of the left image
        :param: sizeR the size of the right image
        :param: referencePoints the list of points on the "reference image"
        :param: pointsToAlign the list of points on the "image to align"
        """
        # Create textures
        self.textures = [
            QOpenGLTexture(referenceImg),
            QOpenGLTexture(imgToAlign)
        ]
        # Update texture parameters
        for tex in self.textures:
            tex.setMinMagFilters(QOpenGLTexture.Nearest, QOpenGLTexture.Nearest)
            tex.setWrapMode(QOpenGLTexture.ClampToEdge)
            tex.generateMipMaps()
        # Store image sizes
        self.sizeL = sizeL
        self.sizeR = sizeR
        # Save points
        self.points = ([QVector2D(p) for p in referencePoints.copy()], [QVector2D(p) for p in pointsToAlign.copy()])
        # Redraw
        self.redraw(False)

    def updateRotation(self, rot: float) -> None:
        """
        Public method to update Rotation parameter.
        :param: rot the new value for rotation (in degrees)
        """
        self.rot = max(min(rot, 180.0), -180.0)
        self.redraw(False)

    def updateTranslation(self, tra: QPointF) -> None:
        """
        Public method to update Translation parameter.
        :param: tra the new value for translation
        """
        self.tra = QPointF(tra.x(), tra.y())
        self.redraw(False)

    # [SCALE] def updateScale(self, sca: float) -> None:
    # [SCALE]     """
    # [SCALE]     Public method to update Scale parameter.
    # [SCALE]     :param: sca the new value for scale
    # [SCALE]     """
    # [SCALE]     if sca <= 0.0:
    # [SCALE]         raise Exception("Invalid scale value")
    # [SCALE]     self.sca = sca
    # [SCALE]     self.redraw(False)

    def setPointsVisibility(self, visibility: bool) -> None:
        """
        Public method to turn on/off points.
        :param: visibility a boolean that set visibility
        """
        self.drawPoints = visibility
        self.redraw(True)

    def customUniforms(self, program: QOpenGLShaderProgram) -> None:
        """
        To be implemented by inheriting class.
        """
        pass

    def redraw(self, keepFB: bool = True) -> None:
        """
        Public method to schedule an update.
        :param: keepFB is a boolean that tries to schedule a fast update by not redrawing tex onto fb
        """
        self.keepFB = self.keepFB and keepFB
        self.update()


class AlphaPreviewViewer(QtSimpleOpenGlShaderViewer):
    """
    Implementation of QtSimpleOpenGlShaderViewer that apply alpha transformation to the two textures.
    """

    V_SHADER_SOURCE = """
    #version 120
    // precision highp float;
    attribute vec2 aPos;
    attribute vec2 aTex;
    varying vec2 vTex;
    uniform mat4 uMatrix;
    void main(void) {
        vTex = aTex;
        gl_Position = uMatrix * vec4(aPos, 0, 1);
    }
    """

    F_SHADER_SOURCE = """
    #version 120
    // precision highp float;
    varying vec2 vTex;
    uniform sampler2D uTexL;
    uniform sampler2D uTexR;
    uniform float uAlpha;
    void main(void) {
        // Sample textures
        vec4 lColRGBA = texture2D(uTexL, vTex);
        vec4 rColRGBA = texture2D(uTexR, vTex);
        
        // Check for valid pixel
        bool hasLeftPixel  = (lColRGBA.a != 0.0);
        bool hasRightPixel = (rColRGBA.a != 0.0);

        // Result color (default value is black)
        vec4 col = vec4(0, 0, 0, 1);
        
        // Check if is an overlapping pixel
        // if (hasLeftPixel && hasRightPixel) {
            
            // Mix colors
            col = mix(lColRGBA, rColRGBA, uAlpha);
            
        // } else {
        //     if (hasLeftPixel)  col = lColRGBA;
        //     if (hasRightPixel) col = rColRGBA;
        // }
        
        // Output color
        gl_FragColor = col;
    }
    """

    def __init__(self, parent=None):
        super(AlphaPreviewViewer, self).__init__(
            AlphaPreviewViewer.V_SHADER_SOURCE,
            AlphaPreviewViewer.F_SHADER_SOURCE,
            parent
        )
        # Custom parameters
        self.alpha = 0.5

    def customUniforms(self, program: QOpenGLShaderProgram) -> None:
        """
        Override to update uniforms before painting
        :param: program the ShaderProgram to use to upload custom uniforms
        """
        # Update uniforms
        program.setUniformValue("uAlpha", self.alpha)

    def updateAlpha(self, alpha: float) -> None:
        """
        Public method to update Alpha parameter.
        :param: alpha the new value for alpha [0.0, 1.0]
        """
        self.alpha = max(min(alpha, 1.0), 0.0)
        self.redraw()


class GrayPreviewViewer(QtSimpleOpenGlShaderViewer):
    """
    Implementation of QtSimpleOpenGlShaderViewer that apply the "absolute difference" pixel-perfect.
    """

    V_SHADER_SOURCE = """
    #version 120
    // precision highp float;
    attribute vec2 aPos;
    attribute vec2 aTex;
    varying vec2 vTex;
    uniform mat4 uMatrix;
    void main(void) {
        vTex = aTex;
        gl_Position = uMatrix * vec4(aPos, 0, 1);
    }
    """

    F_SHADER_SOURCE = """
    #version 120
    // precision highp float;

    varying vec2 vTex;

    uniform sampler2D uTexL;
    uniform sampler2D uTexR;
    uniform float uThr;

    // Utility function to convert RGBA color to GRAY scale (keeping alpha)
    vec4 rgba2gray(vec4 RGBA) {
        // Wikipedia article about luminance conversion:
        // https://en.wikipedia.org/wiki/Luma_(video)
        vec3 RGBA_TO_GRAY = vec3(0.2126, 0.7152, 0.0722);
        float col = dot(RGBA_TO_GRAY, RGBA.rgb);
        return vec4(col, col, col, RGBA.a);
    }

    void main(void) {
        // Sample textures
        vec4 lColRGBA = texture2D(uTexL, vTex);
        vec4 rColRGBA = texture2D(uTexR, vTex);
        
        // Convert to gray scale
        vec4 lColGray = rgba2gray(lColRGBA);
        vec4 rColGray = rgba2gray(rColRGBA);
        
        // Check for valid pixel
        bool hasLeftPixel  = (lColRGBA.a != 0.0);
        bool hasRightPixel = (rColRGBA.a != 0.0);

        // Result color (default value is black)
        vec4 col = vec4(0, 0, 0, 1);
        
        // Check if is an overlapping pixel
        if (hasLeftPixel && hasRightPixel) {
            
            // Compute the abs-diff
            col = vec4(abs(lColGray.rgb - rColGray.rgb).rgb, 1.0);
            
            // Threshold
            if (col.r <= uThr) col.rgb = vec3(0.0);
            
        } else {
            if (hasLeftPixel)  col = lColGray;
            if (hasRightPixel) col = rColGray;
        }
        
        // Output color
        gl_FragColor = col;
    }
    """

    def __init__(self, parent=None):
        super(GrayPreviewViewer, self).__init__(
            GrayPreviewViewer.V_SHADER_SOURCE,
            GrayPreviewViewer.F_SHADER_SOURCE,
            parent
        )
        # Custom parameters
        self.thr = 0.0

    def customUniforms(self, program: QOpenGLShaderProgram) -> None:
        """
        Override to update uniforms before painting
        :param: program the ShaderProgram to use to upload custom uniforms
        """
        # Update uniforms
        program.setUniformValue("uThr", self.thr)

    def updateThreshold(self, thr: int) -> None:
        """
        Public method to update Threshold parameter.
        :param: thr the new value for threshold [0, 255]
        """
        self.thr = min(max(thr / 255.0, 0.0), 1.0)
        self.redraw()


class MarkerObjData:
    """
    Marker data class.
    Contains position inside each viewer (left and right).
    """

    # Types
    SOFT_MARKER = 0
    HARD_MARKER = 1

    # Weights
    SOFT_MARKER_W = 1
    HARD_MARKER_W = 3

    # Draw properties
    MARKER_SIZE = 8
    MARKER_WIDTH = 5
    HARD_MARKER_COLOR = Qt.red
    SOFT_MARKER_COLOR = Qt.yellow
    MARKER_HOVER_COLOR = Qt.white
    MARKER_HOVER_WIDTH = 3

    def __init__(self, identifier: int, lpos: Optional[QPointF], rpos: Optional[QPointF],
                 pxSizeL: float, pxSizeR: float, typ: SOFT_MARKER | HARD_MARKER):
        self.identifier = identifier
        self.pxSizeL = pxSizeL
        self.pxSizeR = pxSizeR
        self.lViewPos: Optional[QPointF] = lpos
        self.rViewPos: Optional[QPointF] = rpos
        self.typ = typ
        self.sceneObjs = []
        self.textObjs = []
        self.errorx = None
        self.errory = None
        self.error = None
        self.weight = 0
        self.pen = QPen(Qt.white, MarkerObjData.MARKER_WIDTH)
        self.pen.setCosmetic(True)
        # Update data
        self.__update()

    def toggleType(self) -> None:
        """
        Toggle type from SOFT to HARD and back.
        """
        if self.typ == MarkerObjData.HARD_MARKER:
            self.typ = MarkerObjData.SOFT_MARKER
        elif self.typ == MarkerObjData.SOFT_MARKER:
            self.typ = MarkerObjData.HARD_MARKER
        # Update data
        self.__update()

    def getBBox(self) -> Tuple[Optional[QRectF], Optional[QRectF]]:
        """
        Retrieve bbox of marker for left and right view.
        :return: (bboxL, bboxR) the two boxes
        """
        bboxL = bboxR = None
        # Create bbox for left viewer
        if self.lViewPos is not None:
            [lmx, lmy] = [self.lViewPos.x() / self.pxSizeL, self.lViewPos.y() / self.pxSizeL]
            sideL = MarkerObjData.MARKER_SIZE / self.pxSizeL
            bboxL = QRectF(lmx - sideL, lmy - sideL, sideL * 2 + 1, sideL * 2 + 1)
        # Create bbox for right viewer
        if self.rViewPos is not None:
            [rmx, rmy] = [self.rViewPos.x() / self.pxSizeR, self.rViewPos.y() / self.pxSizeR]
            sideR = MarkerObjData.MARKER_SIZE / self.pxSizeR
            bboxR = QRectF(rmx - sideR, rmy - sideR, sideR * 2 + 1, sideR * 2 + 1)
        return bboxL, bboxR

    def getLines(self) -> List[Tuple[Optional[QLineF], Optional[QLineF]]]:
        """
        Retrieve the lines to draw the marker inside the two views.
        :return: [(lineLeft, lineRight)] the lines list
        """
        linesL = linesR = []
        # Create line list for left viewer
        if self.lViewPos is not None:
            [lmx, lmy] = [self.lViewPos.x() / self.pxSizeL, self.lViewPos.y() / self.pxSizeL]
            sideL = MarkerObjData.MARKER_SIZE / self.pxSizeL
            linesL = [
                ([-sideL + 1, -sideL + 1], [0, 0]), ([1, 1], [+sideL, +sideL + 0]),  # Top Left -> Bot Right
                ([-sideL + 1, +sideL + 0], [0, 1]), ([1, 0], [+sideL, -sideL + 1]),  # Top Right -> Bot Left
            ]
            linesL = [
                QLineF(lmx + lStart[0], lmy + lStart[1], lmx + lEnd[0], lmy + lEnd[1])
                for ([lStart, lEnd]) in linesL
            ]
        # Create line list for right viewer
        if self.rViewPos is not None:
            [rmx, rmy] = [self.rViewPos.x() / self.pxSizeR, self.rViewPos.y() / self.pxSizeR]
            sideR = MarkerObjData.MARKER_SIZE / self.pxSizeR
            linesR = [
                ([-sideR + 1, -sideR + 1], [0, 0]), ([1, 1], [+sideR, +sideR + 0]),  # Top Left -> Bot Right
                ([-sideR + 1, +sideR + 0], [0, 1]), ([1, 0], [+sideR, -sideR + 1]),  # Top Right -> Bot Left
            ]
            linesR = [
                QLineF(rmx + rStart[0], rmy + rStart[1], rmx + rEnd[0], rmy + rEnd[1])
                for ([rStart, rEnd]) in linesR
            ]
        # Ensure same size
        if len(linesL) < len(linesR):
            linesL = [None] * len(linesR)
        if len(linesR) < len(linesL):
            linesR = [None] * len(linesL)
        # Create lines and zip them
        return [(lineL, lineR) for (lineL, lineR) in zip(linesL, linesR)]

    def setLPos(self, pos: QPointF) -> None:
        """
        Update the marker position on the left viewer.
        :param: lpos the new lpos
        """
        self.lViewPos = QPointF(pos.x(), pos.y())

    def setRPos(self, pos: QPointF) -> None:
        """
        Update the marker position on the right viewer.
        :param: rpos the new rpos
        """
        self.rViewPos = QPointF(pos.x(), pos.y())

    def isComplete(self) -> bool:
        """
        Public method to query the marker "status".
        :return: a boolean that indicates if the marker is complete.
        """
        return self.lViewPos is not None and self.rViewPos is not None

    def move(self, dx: float, dy: float, moveLeft: bool, moveRight: bool) -> None:
        """
        Private method to "move" the marker.
        :param: dx the delta on the x axis
        :param: dy the delta on the y axis
        :param: moveLeft a boolean to turn on/off movement of the position in the left view
        :param: moveRight a boolean to turn on/off movement of the position in the right view
        """
        if moveLeft and self.lViewPos is not None:
            self.lViewPos = QPointF(self.lViewPos.x() + dx, self.lViewPos.y() + dy)
        if moveRight and self.rViewPos is not None:
            self.rViewPos = QPointF(self.rViewPos.x() + dx, self.rViewPos.y() + dy)

    def __update(self) -> None:
        """
        Private method to keep internal data coherent.
        """
        # Update data on type
        if self.typ == MarkerObjData.SOFT_MARKER:
            self.pen.setColor(MarkerObjData.SOFT_MARKER_COLOR)
            self.weight = MarkerObjData.SOFT_MARKER_W
        elif self.typ == MarkerObjData.HARD_MARKER:
            self.pen.setColor(MarkerObjData.HARD_MARKER_COLOR)
            self.weight = MarkerObjData.HARD_MARKER_W


class QtAlignmentToolWidget(QWidget):
    """
    A custom widget that show two images and, with the help of the user, can align the right image to the left one.
    The user needs to place some markers to declare the matches.
    This tool contains also a preview page that shows a "preview" of the results before confirming the alignment.
    """

    closed = pyqtSignal()

    # [SCALE] # Number of samples used when calculating approx scale
    # [SCALE] SCALE_SAMPLING_COUNT = 64

    ROT_PRECISION = 100  # 1 / 100

    # [SCALE] SCALE_PRECISION = 100  # 1 / 100
    # [SCALE] SCALE_RANGE = 0.50  # [-50%, +50%]

    def __init__(self, project, parent=None):
        super(QtAlignmentToolWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        # ==============================================================

        self.project = project
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(600)
        self.setWindowTitle("Alignment Tool")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.syncEnabled = True
        self.alpha = 50
        self.threshold = 32
        self.sizeL: QPointF = QPointF(0.0, 0.0)
        self.sizeR: QPointF = QPointF(0.0, 0.0)
        # [SCALE] self.canScale = False
        # [SCALE] self.svdRes = [0, [0, 0], 0]
        self.svdRes = [0, [0, 0]]
        self.R = np.rad2deg(0) * QtAlignmentToolWidget.ROT_PRECISION
        self.T = np.array([0, 0])
        # [SCALE] self.S = 1 * QtAlignmentToolWidget.SCALE_PRECISION
        self.lastMousePos = None
        self.isDragging = False
        self.selectedMarker = None
        self.hoveringSceneObjs = None
        self.hoveringMarker = None
        self.lMarkerIndex = 0
        self.rMarkerIndex = 0
        self.markers: List[MarkerObjData] = []
        self.markers_copy = None
        self.pxSizeL = 1.0
        self.pxSizeR = 1.0
        self.error_table_flag = False

        # ==============================================================
        # Top buttons
        # ==============================================================

        # Sync
        self.syncCheck = QCheckBox("Sync")
        self.syncCheck.setChecked(True)
        self.syncCheck.setFocusPolicy(Qt.NoFocus)
        self.syncCheck.setMaximumWidth(80)
        self.syncCheck.stateChanged[int].connect(self.toggleSync)

        # Auto Align
        self.autoAlignButton = QPushButton("Preview Alignment")
        self.autoAlignButton.setFixedWidth(200)
        self.autoAlignButton.setFixedHeight(20)
        self.autoAlignButton.clicked.connect(self.onAutoAlignRequested)

        # Back to Edit
        self.backToEditButton = QPushButton("Back to Edit")
        self.backToEditButton.setFixedWidth(150)
        self.backToEditButton.setFixedHeight(20)
        self.backToEditButton.clicked.connect(self.onBackToEditRequested)

        # Clear Markers
        self.clearMarkersButton = QPushButton("Clear Markers")
        self.clearMarkersButton.setFixedWidth(200)
        self.clearMarkersButton.setFixedHeight(20)
        self.clearMarkersButton.clicked.connect(self.onClearMarkersRequested)

        # [SCALE] # Allow Scale
        # [SCALE] self.allowScaleButton = QCheckBox("Allow Scale")
        # [SCALE] self.allowScaleButton.setChecked(False)
        # [SCALE] self.allowScaleButton.setFocusPolicy(Qt.NoFocus)
        # [SCALE] self.allowScaleButton.stateChanged[int].connect(self.toggleScaleLock)

        # Show Markers
        self.showMarkersCheck = QCheckBox("Show Markers")
        self.showMarkersCheck.setChecked(True)
        self.showMarkersCheck.setFocusPolicy(Qt.NoFocus)
        self.showMarkersCheck.stateChanged[int].connect(self.toggleMarkersVisibility)

        # Reset transformations
        self.resetTransfButton = QPushButton("Reset Transformations")
        self.resetTransfButton.setFixedWidth(300)
        self.resetTransfButton.setFixedHeight(20)
        self.resetTransfButton.clicked.connect(self.onResetTransformations)

        # Confirm Alignment
        self.confirmAlignmentButton = QPushButton("Confirm")
        self.confirmAlignmentButton.setFixedWidth(100)
        self.confirmAlignmentButton.setFixedHeight(20)
        self.confirmAlignmentButton.clicked.connect(self.onConfirmAlignment)

        # Slider
        self.alphaSliderLabel = QLabel("Alpha: " + str(self.alpha))
        self.alphaSliderLabel.setMinimumWidth(100)
        self.alphaSlider = QSlider(Qt.Horizontal)
        self.alphaSlider.setFocusPolicy(Qt.StrongFocus)
        self.alphaSlider.setMinimum(0)
        self.alphaSlider.setMaximum(100)
        self.alphaSlider.setValue(50)
        self.alphaSlider.setTickInterval(1)
        self.alphaSlider.setMinimumWidth(50)
        self.alphaSlider.setAutoFillBackground(True)
        self.alphaSlider.valueChanged.connect(self.previewAlphaValueChanges)

        # Slider (X)
        self.xSliderLabel = QLabel("Tx: " + str(self.T[0]))
        self.xSliderLabel.setMinimumWidth(100)
        self.xSlider = QSlider(Qt.Horizontal)
        self.xSlider.setFocusPolicy(Qt.StrongFocus)
        self.xSlider.setMinimum(-256)
        self.xSlider.setMaximum(+256)
        self.xSlider.setTickInterval(1)
        self.xSlider.setValue(self.T[0])
        self.xSlider.setMinimumWidth(50)
        self.xSlider.setAutoFillBackground(True)
        self.xSlider.valueChanged.connect(self.xOffsetChanges)

        # Slider (Y)
        self.ySliderLabel = QLabel("Ty: " + str(self.T[1]))
        self.ySliderLabel.setMinimumWidth(100)
        self.ySlider = QSlider(Qt.Horizontal)
        self.ySlider.setFocusPolicy(Qt.StrongFocus)
        self.ySlider.setMinimum(-256)
        self.ySlider.setMaximum(+256)
        self.ySlider.setTickInterval(1)
        self.ySlider.setValue(self.T[1])
        self.ySlider.setMinimumWidth(50)
        self.ySlider.setAutoFillBackground(True)
        self.ySlider.valueChanged.connect(self.yOffsetChanges)

        # Arrows (<, ^, ...)
        self.moveLeftButton = QPushButton("-")
        self.moveLeftButton.setFixedWidth(20)
        self.moveLeftButton.setFixedHeight(20)
        self.moveLeftButton.clicked.connect(self.onXValueDecremented)
        self.moveRightButton = QPushButton("+")
        self.moveRightButton.setFixedWidth(20)
        self.moveRightButton.setFixedHeight(20)
        self.moveRightButton.clicked.connect(self.onXValueIncremented)
        self.moveDownButton = QPushButton("+")
        self.moveDownButton.setFixedWidth(20)
        self.moveDownButton.setFixedHeight(20)
        self.moveDownButton.clicked.connect(self.onYValueIncremented)
        self.moveUpButton = QPushButton("-")
        self.moveUpButton.setFixedWidth(20)
        self.moveUpButton.setFixedHeight(20)
        self.moveUpButton.clicked.connect(self.onYValueDecremented)

        # Slider (Rot)
        self.rSliderLabel = QLabel("R: " + str(self.R / QtAlignmentToolWidget.ROT_PRECISION))
        self.rSliderLabel.setMinimumWidth(100)
        self.rSlider = QSlider(Qt.Horizontal)
        self.rSlider.setFocusPolicy(Qt.StrongFocus)
        self.rSlider.setMinimum(-180 * QtAlignmentToolWidget.ROT_PRECISION)
        self.rSlider.setMaximum(180 * QtAlignmentToolWidget.ROT_PRECISION)
        self.rSlider.setTickInterval(1)
        self.rSlider.setValue(self.R)
        self.rSlider.setMinimumWidth(50)
        self.rSlider.setAutoFillBackground(True)
        self.rSlider.valueChanged.connect(self.rotationAngleChanges)

        # Rotate Left / Right
        self.rotateLeftButton = QPushButton("+")
        self.rotateLeftButton.setFixedWidth(20)
        self.rotateLeftButton.setFixedHeight(20)
        self.rotateLeftButton.clicked.connect(self.onRotValueIncremented)
        self.rotateRightButton = QPushButton("-")
        self.rotateRightButton.setFixedWidth(20)
        self.rotateRightButton.setFixedHeight(20)
        self.rotateRightButton.clicked.connect(self.onRotValueDecremented)

        # [SCALE] # Slider (Scale)
        # [SCALE] self.sSliderLabel = QLabel("S: " + str(self.S / QtAlignmentToolWidget.SCALE_PRECISION))
        # [SCALE] self.sSliderLabel.setMinimumWidth(200)
        # [SCALE] self.sSlider = QSlider(Qt.Horizontal)
        # [SCALE] self.sSlider.setFocusPolicy(Qt.StrongFocus)
        # [SCALE] self.sSlider.setMinimum(1)
        # [SCALE] self.sSlider.setMaximum(200)
        # [SCALE] self.sSlider.setTickInterval(1)
        # [SCALE] self.sSlider.setValue(self.S)
        # [SCALE] self.sSlider.setMinimumWidth(50)
        # [SCALE] self.sSlider.setAutoFillBackground(True)
        # [SCALE] self.sSlider.valueChanged.connect(self.scaleValueChanges)
        # [SCALE] self.sSlider.setEnabled(False)

        # [SCALE] # Scale increase / decrease
        # [SCALE] self.scaleDecButton = QPushButton("-")
        # [SCALE] self.scaleDecButton.setFixedWidth(20)
        # [SCALE] self.scaleDecButton.setFixedHeight(20)
        # [SCALE] self.scaleDecButton.clicked.connect(self.onScaleValueDecremented)
        # [SCALE] self.scaleDecButton.setEnabled(False)
        # [SCALE] self.scaleIncButton = QPushButton("+")
        # [SCALE] self.scaleIncButton.setFixedWidth(20)
        # [SCALE] self.scaleIncButton.setFixedHeight(20)
        # [SCALE] self.scaleIncButton.setEnabled(False)
        # [SCALE] self.scaleIncButton.clicked.connect(self.onScaleValueIncremented)

        # Slider (Threshold)
        self.thresholdSliderLabel = QLabel("Threshold: " + str(self.threshold))
        self.thresholdSliderLabel.setMinimumWidth(100)
        self.thresholdSlider = QSlider(Qt.Horizontal)
        self.thresholdSlider.setFocusPolicy(Qt.StrongFocus)
        self.thresholdSlider.setMinimum(0)
        self.thresholdSlider.setMaximum(256)
        self.thresholdSlider.setValue(64)
        self.thresholdSlider.setTickInterval(1)
        self.thresholdSlider.setMinimumWidth(50)
        self.thresholdSlider.setAutoFillBackground(True)
        self.thresholdSlider.valueChanged.connect(self.thresholdValueChanges)

        # Layout
        self.buttons = QHBoxLayout()
        self.buttons.addWidget(self.syncCheck)
        self.buttons.addWidget(self.backToEditButton)
        self.buttons.addWidget(self.clearMarkersButton)
        self.buttons.addWidget(self.resetTransfButton)
        self.buttons.addWidget(self.showMarkersCheck)
        # [SCALE] self.buttons.addWidget(self.allowScaleButton)
        self.buttons.addWidget(self.autoAlignButton)
        self.buttons.addWidget(self.confirmAlignmentButton)
        self.buttons.setAlignment(self.syncCheck, Qt.AlignLeft)
        self.buttons.setAlignment(self.backToEditButton, Qt.AlignLeft)
        self.buttons.setAlignment(self.clearMarkersButton, Qt.AlignCenter)
        self.buttons.setAlignment(self.resetTransfButton, Qt.AlignCenter)
        self.buttons.setAlignment(self.showMarkersCheck, Qt.AlignCenter)
        # [SCALE] self.buttons.setAlignment(self.allowScaleButton, Qt.AlignCenter)
        self.buttons.setAlignment(self.autoAlignButton, Qt.AlignRight)
        self.buttons.setAlignment(self.confirmAlignmentButton, Qt.AlignRight)

        self.layoutSliders = QVBoxLayout()
        layout3 = QHBoxLayout()
        layout3.addWidget(self.xSliderLabel)
        layout3.addWidget(self.xSlider)
        layout3.addWidget(self.moveRightButton)
        layout3.addWidget(self.moveLeftButton)
        self.layoutSliders.addLayout(layout3)
        layout4 = QHBoxLayout()
        layout4.addWidget(self.ySliderLabel)
        layout4.addWidget(self.ySlider)
        layout4.addWidget(self.moveDownButton)
        layout4.addWidget(self.moveUpButton)
        self.layoutSliders.addLayout(layout4)
        layout5 = QHBoxLayout()
        layout5.addWidget(self.rSliderLabel)
        layout5.addWidget(self.rSlider)
        layout5.addWidget(self.rotateLeftButton)
        layout5.addWidget(self.rotateRightButton)
        self.layoutSliders.addLayout(layout5)
        # [SCALE] layout6 = QHBoxLayout()
        # [SCALE] layout6.addWidget(self.sSliderLabel)
        # [SCALE] layout6.addWidget(self.sSlider)
        # [SCALE] layout6.addWidget(self.scaleIncButton)
        # [SCALE] layout6.addWidget(self.scaleDecButton)
        # [SCALE] self.layoutSliders.addLayout(layout6)

        self.table = QTableWidget(10, 5)
        self.table.setHorizontalHeaderLabels(["Add/remove", "Point Id", "X err", "Y err", "Dist err"])
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.verticalHeader().hide()
        self.table.setMaximumHeight(200)
        self.table.setStyleSheet("QTableCornerButton::section { background-color: rgb(40,40,40); }"
                                 "QHeaderView::section { background-color: rgb(40,40,40); }")

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        self.labelmeanx = QLabel("Mean Ex: ")
        self.labelmeanx.setFixedWidth(120)
        self.meanex = QLabel(" ")

        self.layoutmeanx = QHBoxLayout()
        self.layoutmeanx.addWidget(self.labelmeanx)
        self.layoutmeanx.addWidget(self.meanex)

        self.labelmeany = QLabel("Mean Ey: ")
        self.labelmeany.setFixedWidth(120)
        self.meaney = QLabel(" ")

        self.layoutmeany = QHBoxLayout()
        self.layoutmeany.addWidget(self.labelmeany)
        self.layoutmeany.addWidget(self.meaney)

        self.labelmeanerr = QLabel("Mean Dist: ")
        self.labelmeanerr.setFixedWidth(120)
        self.meanerror = QLabel(" ")

        self.layoutmeanerror = QHBoxLayout()
        self.layoutmeanerror.addWidget(self.labelmeanerr)
        self.layoutmeanerror.addWidget(self.meanerror)

        self.layoutmeanerrors = QVBoxLayout()
        self.layoutmeanerrors.addLayout(self.layoutmeanx)
        self.layoutmeanerrors.addLayout(self.layoutmeany)
        self.layoutmeanerrors.addLayout(self.layoutmeanerror)

        self.layoutTop = QHBoxLayout()
        self.layoutTop.addLayout(self.layoutSliders)
        self.layoutTop.addSpacing(50)
        self.layoutTop.addWidget(self.table)
        self.layoutTop.addSpacing(50)
        self.layoutTop.addLayout(self.layoutmeanerrors)
        self.layoutTop.addSpacing(10)

        # ==============================================================
        # Middle UI containing map selector and map viewer
        # ==============================================================

        # Left
        self.leftComboboxLabel = QLabel("Reference Image")
        self.leftCombobox = QComboBox()

        for image in self.project.images:
            self.leftCombobox.addItem(image.name)

        self.leftCombobox.setCurrentIndex(0)
        self.leftCombobox.currentIndexChanged.connect(self.leftImageChanges)

        self.leftImgViewer = QtImageViewer()
        self.leftImgViewer.setOpacity(1)
        self.leftImgViewer.mouseDown.connect(self.onLeftViewMouseDown)
        self.leftImgViewer.mouseUp.connect(self.onLeftViewMouseUp)
        self.leftImgViewer.mouseMove.connect(self.onLeftViewMouseMove)
        self.leftImgViewer.mouseOut.connect(self.onLeftViewMouseOut)
        self.leftImgViewer.viewHasChanged[float, float, float].connect(self.leftImgViewerParamsChanges)

        layout8 = QHBoxLayout()
        layout8.addWidget(self.leftComboboxLabel)
        layout8.addWidget(self.leftCombobox)
        layout8.setStretchFactor(self.leftComboboxLabel, 1)
        layout8.setStretchFactor(self.leftCombobox, 1)
        leftLayout = QVBoxLayout()
        leftLayout.addLayout(layout8)
        leftLayout.addWidget(self.leftImgViewer)

        # Right
        self.rightComboboxLabel = QLabel("Image to align")
        self.rightCombobox = QComboBox()

        for image in self.project.images:
            self.rightCombobox.addItem(image.name)

        self.rightCombobox.setCurrentIndex(0)
        self.rightCombobox.currentIndexChanged.connect(self.rightImageChanges)

        self.rightImgViewer = QtImageViewer()
        self.rightImgViewer.setOpacity(1)
        self.rightImgViewer.mouseDown.connect(self.onRightViewMouseDown)
        self.rightImgViewer.mouseUp.connect(self.onRightViewMouseUp)
        self.rightImgViewer.mouseMove.connect(self.onRightViewMouseMove)
        self.rightImgViewer.mouseOut.connect(self.onRightViewMouseOut)
        self.rightImgViewer.viewHasChanged[float, float, float].connect(self.rightImgViewerParamsChanges)

        layout9 = QHBoxLayout()
        layout9.addWidget(self.rightComboboxLabel)
        layout9.addWidget(self.rightCombobox)
        layout9.setStretchFactor(self.rightComboboxLabel, 1)
        layout9.setStretchFactor(self.rightCombobox, 1)
        rightLayout = QVBoxLayout()
        rightLayout.addLayout(layout9)
        rightLayout.addWidget(self.rightImgViewer)

        # Layout
        self.editLayout = QHBoxLayout()
        self.editLayout.addLayout(leftLayout)
        self.editLayout.setStretchFactor(leftLayout, 1)
        self.editLayout.addLayout(rightLayout)
        self.editLayout.setStretchFactor(rightLayout, 1)

        # ==============================================================
        # UI for preview
        # ==============================================================

        self.leftPreviewViewer = AlphaPreviewViewer()
        self.rightPreviewViewer = GrayPreviewViewer()

        layoutAS = QHBoxLayout()
        layoutAS.addWidget(self.alphaSliderLabel)
        layoutAS.addWidget(self.alphaSlider)

        layoutDIFF = QHBoxLayout()
        layoutDIFF.addWidget(self.thresholdSliderLabel)
        layoutDIFF.addWidget(self.thresholdSlider)

        self.previewLayoutL = QVBoxLayout()
        self.previewLayoutL.addLayout(layoutAS)
        self.previewLayoutL.addWidget(self.leftPreviewViewer)

        self.previewLayoutR = QVBoxLayout()
        self.previewLayoutR.addLayout(layoutDIFF)
        self.previewLayoutR.addWidget(self.rightPreviewViewer)

        self.previewLayout = QHBoxLayout()
        self.previewLayout.addLayout(self.previewLayoutL)
        self.previewLayout.addLayout(self.previewLayoutR)

        # ==============================================================
        # Initialize layouts
        # ==============================================================

        content = QVBoxLayout()
        content.addLayout(self.buttons)
        content.addLayout(self.layoutTop)
        content.addLayout(self.editLayout)
        content.addLayout(self.previewLayout)

        self.setLayout(content)

        # ==============================================================
        # Initialize views by simulating clicks on the UI
        # ==============================================================

        self.project.images[0].channels[0].loadData()
        self.project.images[1].channels[0].loadData()

        self.leftCombobox.currentIndexChanged.emit(0)
        self.rightCombobox.currentIndexChanged.emit(1)

        self.syncCheck.stateChanged.emit(1)

        self.__togglePreviewMode(False)

        # ==============================================================

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Override parent's method to intercept close events.
        :param: event the close event
        """
        # Emit signal
        self.closed.emit()
        # Default
        super(QtAlignmentToolWidget, self).closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Override parent's method to intercept key events.
        :param: event the key press event
        """
        # Keyboard handling
        if event.key() == Qt.Key_Delete:
            # Delete hovering marker
            if self.hoveringMarker is not None:
                i = self.hoveringMarker
                self.__clearHoveringMarker()
                self.__deleteMarker(i)
                # Redraw markers
                self.__updateMarkers(keepAlgResults=False)
        # Default
        super(QtAlignmentToolWidget, self).keyPressEvent(event)

    @pyqtSlot(int)
    def leftImageChanges(self, index: int) -> None:
        """
        Callback called when the user select a new image for the left view.
        :param: index of the new image
        """
        # Validate index
        N = len(self.project.images)
        if index == -1 or index >= N:
            return
        # Ensure indexes are different
        if index == self.rightCombobox.currentIndex():
            self.rightCombobox.setCurrentIndex((index + 1) % N)
        else:
            # Forward to private method
            self.__updateImgViewers()

    @pyqtSlot(int)
    def rightImageChanges(self, index: int) -> None:
        """
        Callback called when the user select a new image for the right view.
        :param: index of the new image
        """
        # Validate index
        N = len(self.project.images)
        if index == -1 or index >= N:
            return
        # Ensure indexes are different
        if index == self.leftCombobox.currentIndex():
            self.leftCombobox.setCurrentIndex((index + 1) % N)
        else:
            # Forward to private method
            self.__updateImgViewers()

    @pyqtSlot(float, float, float)
    def leftImgViewerParamsChanges(self, posx: float, posy: float, zoom: float) -> None:
        """
        Callback called on view params changes.
        :param: posx the new x offset from left
        :param: posy the new y offset from top
        :param: zoom the new zoom (pixel_size agnostic)
        """
        # Clear text items to update visibility
        for i in range(0, len(self.markers)):
            self.__clearMarker(i, True)
        # Redraw
        self.__updateMarkers(keepAlgResults=True)
        # Update right one (if sync is enabled)
        if self.syncEnabled:
            self.rightImgViewer.setViewParameters(posx, posy, zoom)

    @pyqtSlot(float, float, float)
    def rightImgViewerParamsChanges(self, posx: float, posy: float, zoom: float) -> None:
        """
        Callback called on view params changes.
        :param: posx the new x offset from left
        :param: posy the new y offset from top
        :param: zoom the new zoom (pixel_size agnostic)
        """
        # Clear text items to update visibility
        for i in range(0, len(self.markers)):
            self.__clearMarker(i, True)
        # Redraw
        self.__updateMarkers(keepAlgResults=True)
        # Update left one (if sync is enabled)
        if self.syncEnabled:
            self.leftImgViewer.setViewParameters(posx, posy, zoom)

    @pyqtSlot(int)
    def toggleSync(self, value: int) -> None:
        """
        Callback called when the sync mode is turned on/off.
        :param: value a boolean to enable/disable the sync mode.
        """
        # Update mode
        self.syncEnabled = value
        # Changes can be forwarded if needed by storing last values and forcing update here

    @pyqtSlot(int)
    def toggleMarkersVisibility(self, value: int) -> None:
        """
        Callback called when the checkbox for marker visibility it toggled.
        :param: value a boolean representing the checkbox status.
        """
        # Forward to viewer
        self.leftPreviewViewer.setPointsVisibility(value != 0)
        self.rightPreviewViewer.setPointsVisibility(value != 0)

    # [SCALE] @pyqtSlot(int)
    # [SCALE] def toggleScaleLock(self, value: int) -> None:
    # [SCALE]     """
    # [SCALE]     Callback called when the checkbox that allow scale is toggled.
    # [SCALE]     :param: value a boolean representing the checkbox status.
    # [SCALE]     """
    # [SCALE]     # Update canScale
    # [SCALE]     self.canScale = value != 0
    # [SCALE]     # Recompute svd
    # [SCALE]     self.__leastSquaresWithSVD()
    # [SCALE]
    # [SCALE]     # Update preview (if needed)
    # [SCALE]     self.__updatePreview()

    @pyqtSlot()
    def onBackToEditRequested(self) -> None:
        """
        Callback called when the Preview Mode is turned on/off.
        :param: value a boolean representing if the mode is checked.
        """
        # Recompute svd ---  WHY?
        # self.__leastSquaresWithSVD()
        self.markers = self.markers_copy.copy()
        # Hide preview widgets
        self.__togglePreviewMode(False)

    @pyqtSlot(int)
    def previewAlphaValueChanges(self, value: int) -> None:
        """
        Callback called when the alpha value changes.
        :param: value the new alpha value
        """
        # Update alpha value and slider text
        self.alpha = value
        self.alphaSliderLabel.setText("Alpha: " + str(value))

        # Update preview
        self.error_table_flag = False
        self.__updatePreview()

    @pyqtSlot()
    def onXValueIncremented(self) -> None:
        """
        Callback called when the x value of the offset changes by +1.
        """
        # Forward
        self.xSlider.setValue(self.T[0] + 1)

    @pyqtSlot()
    def onXValueDecremented(self) -> None:
        """
        Callback called when the x value of the offset changes by -1.
        """
        # Forward
        self.xSlider.setValue(self.T[0] - 1)

    @pyqtSlot(int)
    def xOffsetChanges(self, value: int) -> None:
        """
        Callback called when the x value of the offset changes.
        :param: value the new x value
        """
        # Update offset value and slider text
        self.T[0] = value
        self.xSliderLabel.setText("Tx: " + str(value))

        # Update preview
        self.error_table_flag = True
        self.__updatePreview()

    @pyqtSlot()
    def onYValueIncremented(self) -> None:
        """
        Callback called when the y value of the offset changes by +1.
        """
        # Forward
        self.ySlider.setValue(self.T[1] + 1)

    @pyqtSlot()
    def onYValueDecremented(self) -> None:
        """
        Callback called when the y value of the offset changes by -1.
        """
        # Forward
        self.ySlider.setValue(self.T[1] - 1)

    @pyqtSlot(int)
    def yOffsetChanges(self, value: int) -> None:
        """
        Callback called when the y value of the offset changes.
        :param: value the new y value
        """
        # Update offset value and slider text
        self.T[1] = value
        self.ySliderLabel.setText("Ty: " + str(value))

        # Update preview
        self.error_table_flag = True
        self.__updatePreview()

    @pyqtSlot()
    def onRotValueIncremented(self) -> None:
        """
        Callback called when the value of the rotation changes by +1.
        """
        # Forward
        self.rSlider.setValue(self.R + 1)

    @pyqtSlot()
    def onRotValueDecremented(self) -> None:
        """
        Callback called when the value of the rotation changes by -1.
        """
        # Forward
        self.rSlider.setValue(self.R - 1)

    # [SCALE] @pyqtSlot()
    # [SCALE] def onScaleValueIncremented(self) -> None:
    # [SCALE]     """
    # [SCALE]     Callback called when the value of the scale should be increase.
    # [SCALE]     """
    # [SCALE]     # Forward
    # [SCALE]     self.sSlider.setValue(self.S + 1)

    # [SCALE] @pyqtSlot()
    # [SCALE] def onScaleValueDecremented(self) -> None:
    # [SCALE]     """
    # [SCALE]     Callback called when the value of the scale should be decreased.
    # [SCALE]     """
    # [SCALE]     # Forward
    # [SCALE]     self.sSlider.setValue(self.S - 1)

    @pyqtSlot(int)
    def rotationAngleChanges(self, value: int) -> None:
        """
        Callback called when the value of the rotation changes.
        :param: value the new rot value
        """
        self.R = value
        self.rSliderLabel.setText("R: " + str(self.R / QtAlignmentToolWidget.ROT_PRECISION))

        # Update preview
        self.error_table_flag = True
        self.__updatePreview()

    # [SCALE] @pyqtSlot(int)
    # [SCALE] def scaleValueChanges(self, value: int) -> None:
    # [SCALE]     """
    # [SCALE]     Callback called when the value of the scale changes.
    # [SCALE]     :param: value the new sca value
    # [SCALE]     """
    # [SCALE]     self.S = value
    # [SCALE]     self.sSliderLabel.setText("S: " + str(self.S / QtAlignmentToolWidget.SCALE_PRECISION))
    # [SCALE]
    # [SCALE]     # Update preview
    # [SCALE]     self.error_table_flag = True
    # [SCALE]     self.__updatePreview()

    @pyqtSlot(int)
    def thresholdValueChanges(self, value: int) -> None:
        """
        Callback called when the threshold value changes.
        :param: value the new threshold value
        """
        # Update threshold value and slider text
        self.threshold = value
        self.thresholdSliderLabel.setText("Threshold: " + str(value))

        # Update preview
        self.error_table_flag = False
        self.__updatePreview()

    @pyqtSlot(QMouseEvent)
    def onLeftViewMouseDown(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse down event over the left viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseDown(event, True)

    @pyqtSlot(QMouseEvent)
    def onLeftViewMouseMove(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse move event over the left viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseMove(event, True)

    @pyqtSlot(QMouseEvent)
    def onLeftViewMouseUp(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse up event over the left viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseUp(event, True)

    @pyqtSlot()
    def onLeftViewMouseOut(self) -> None:
        """
        Callback called when the mouse left the left viewer space.
        """
        # Forward
        self.__onMouseOut(True)

    @pyqtSlot(QMouseEvent)
    def onRightViewMouseDown(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse down event over the right viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseDown(event, False)

    @pyqtSlot(QMouseEvent)
    def onRightViewMouseMove(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse move event over the right viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseMove(event, False)

    @pyqtSlot(QMouseEvent)
    def onRightViewMouseUp(self, event: QMouseEvent) -> None:
        """
        Callback called on a mouse up event over the right viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseUp(event, False)

    @pyqtSlot()
    def onRightViewMouseOut(self) -> None:
        """
        Callback called when the mouse left the right viewer space.
        """
        # Forward
        self.__onMouseOut(False)

    @pyqtSlot()
    def onResetTransformations(self) -> None:
        """
        Callback called when the user reset transformations (to improve quality of life in the manual pipeline)
        """
        # Reset transformation values
        self.rSlider.setValue(self.svdRes[0])
        self.xSlider.setValue(self.svdRes[1][0])
        self.ySlider.setValue(self.svdRes[1][1])
        # [SCALE] self.sSlider.setValue(self.svdRes[2])
        # Redraw preview
        self.__updatePreview()

    @pyqtSlot()
    def onClearMarkersRequested(self) -> None:
        """
        Callback called when the user request the auto alignment process to start.
        """
        # Clear all markers
        self.__deleteAllMarkers()
        self.__updateMarkers(keepAlgResults=False)

    @pyqtSlot()
    def onAutoAlignRequested(self) -> None:
        """
        Callback called when the user request the auto alignment process to start.
        """
        # Ensure enough valid markers were added
        if not self.__hasValidMarkers():
            msgBox = QMessageBox()
            msgBox.setText("""
At least 3 marker are required. Use the right button to place markers.
Markers that do not apper in both views are considered invalid.
All markers must be valid to proceed.
            """)
            msgBox.exec()
            return
        # Switch to preview mode
        self.__togglePreviewMode(True)
        # Initialize and update the view
        self.__initializePreview()
        self.__updatePreview()

    @pyqtSlot()
    def onConfirmAlignment(self) -> None:
        """
        Callback called when the user request to confirm and save alignment data.
        """
        # TODO: Apply the scale to the mm_to_px_factor
        QApplication.setOverrideCursor(Qt.WaitCursor)
        # Retrieve Images
        index1 = self.leftCombobox.currentIndex()
        index2 = self.rightCombobox.currentIndex()
        image1 = self.project.images[index1]
        image2 = self.project.images[index2]
        image1W, image1H = image1.channels[0].qimage.width(), image1.channels[0].qimage.height()
        image2W, image2H = image2.channels[0].qimage.width(), image2.channels[0].qimage.height()

        # ================================ Transformation Data =============================================
        # Calculate affine matrix
        trax = self.T[0]
        tray = self.T[1]
        rot = self.R / QtAlignmentToolWidget.ROT_PRECISION
        # [SCALE] sca = self.S / QtAlignmentToolWidget.SCALE_PRECISION
        # Extract components
        R = cv2.getRotationMatrix2D((0, 0), -rot, 1.0)[::, :2]
        T = [trax / image2.pixelSize(), tray / image2.pixelSize()]

        # Compute borders
        bbox: QRectF = image2.annotations.computeBBoxWithAffineTransform(R, T)
        leftB = abs(int(min(bbox.left(), 0)))
        topB = abs(int(min(bbox.top(), 0)))
        rightB = int(max(bbox.right() - image2W, 0))
        bottomB = int(max(bbox.bottom() - image2H, 0))

        # Extract geo-ref from the reference image
        if image1.georef_filename is not None and image1.georef_filename != "":
            with rio.open(image1.georef_filename, "r") as geoFile:
                geoRef = geoFile.crs
                geoTra = geoFile.transform
        else:
            geoRef = None
            geoTra = None

        # ================================ Image 2 =============================================
        # Create a roto-translated copy
        cpy2 = image2.copyTransform("_coreg", rot, T, [leftB, rightB, topB, bottomB], geoTra, geoRef)
        # Add it to the project
        self.project.addNewImage(cpy2, sort=False)

        # ================================ Image 1 =============================================
        # Convert pixelSize of Image2 => pixelSize of Image1
        leftB = int(leftB * image2.pixelSize() / image1.pixelSize())
        topB = int(topB * image2.pixelSize() / image1.pixelSize())
        # Create only when needed
        if leftB > 0 or topB > 0:
            cpy1 = image1.copyTransform("_ref", 0, np.array([0, 0]), [leftB, 0, topB, 0], geoTra, geoRef)
            self.project.addNewImage(cpy1, sort=False)

        # ================================ Markers =============================================
        refMarkers = [[m.lViewPos.x(), m.lViewPos.y()] for m in self.markers]
        refImageIndex = index1
        coregMarkers = [[m.rViewPos.x(), m.rViewPos.y()] for m in self.markers]
        coregImageIndex = index2
        markersWeights = [m.typ for m in self.markers]
        self.project.addOrUpdateMarkers(
            refImgId=refImageIndex,
            refMarkers=refMarkers,
            coregImgId=coregImageIndex,
            coregMarkers=coregMarkers,
            markersTypes=markersWeights,
        )

        # ATTENTION: Last step since it causes shifting of indexes
        self.project.orderImagesByAcquisitionDate()

        # ================================ End =============================================
        QApplication.restoreOverrideCursor()
        # Close widget (?)
        box = QMessageBox()
        box.setText("The co-registered image has been added to the project and saved in your folder")
        box.exec()
        self.close()

    def __onMouseDown(self, event: QMouseEvent, isLeft: bool) -> None:
        """
        Private method called on mouse down event.
        :param: event the mouse event
        :param: isLeft a boolean to choose emitting viewer
        """
        # Filters out non-right-button events
        if event.button() != Qt.RightButton:
            return
        # Map mouse pos
        pos = self.__mapToViewer(event.pos(), isLeft)
        self.lastMousePos = pos
        # Check if any marker exist at current position
        hovering = self.__findMarkerAt(pos, isLeft)
        # Set dragging index (can be None)
        self.selectedMarker = hovering
        # Update hovering
        self.__clearHoveringMarker()
        if hovering is not None:
            self.hoveringMarker = hovering
            self.hoveringSceneObjs = self.__drawHoveringMarker(hovering)
        # Redraw markers
        self.__updateMarkers(keepAlgResults=True)

    def __onMouseUp(self, event: QMouseEvent, isLeft: bool) -> None:
        """
        Private method called on mouse up event.
        :param: event the mouse event
        :param: isLeft a boolean to choose emitting viewer
        """
        # Filters out non-right-button events
        if event.button() != Qt.RightButton:
            return
        # Map mouse pos
        pos = self.__mapToViewer(event.pos(), isLeft)
        # Check if any marker exist at current position
        hovering = self.__findMarkerAt(pos, isLeft)
        # Ensure user wasn't dragging a marker
        if not self.isDragging:
            if hovering is None:
                # Create marker
                pxSize = self.pxSizeL if isLeft else self.pxSizeR
                mkPos = QPointF(pos.x() * pxSize, pos.y() * pxSize)
                self.__addMarker(mkPos, isLeft)
            else:
                # Toggle marker
                self.__toggleMarker(hovering)
        # Clear status
        self.isDragging = False
        self.selectedMarker = None
        # Update hovering
        self.__clearHoveringMarker()
        if hovering is not None:
            self.hoveringMarker = hovering
            self.hoveringSceneObjs = self.__drawHoveringMarker(hovering)
        # Redraw markers
        self.__updateMarkers(keepAlgResults=False)

    def __onMouseMove(self, event: QMouseEvent, isLeft: bool) -> None:
        """
        Private method called on mouse move event.
        :param: event the mouse event
        :param: isLeft a boolean to choose emitting viewer
        """
        # Map mouse pos
        pos = self.__mapToViewer(event.pos(), isLeft)
        # Update dragging status (if needed)
        if not self.isDragging and self.selectedMarker is not None:
            self.isDragging = True
        # Check if user is dragging a marker
        if self.isDragging:
            # Calculate delta
            pxSize = self.pxSizeL if isLeft else self.pxSizeR
            dx = (pos.x() - self.lastMousePos.x()) * pxSize
            dy = (pos.y() - self.lastMousePos.y()) * pxSize
            self.lastMousePos = pos
            # Update marker position
            self.markers[self.selectedMarker].move(dx, dy, isLeft, True)
            self.__clearMarker(self.selectedMarker, False)
            # Redraw markers
            self.__updateMarkers(keepAlgResults=False)
        else:
            # Check for hover
            hovering = self.__findMarkerAt(pos, isLeft)
            if self.hoveringMarker != hovering:
                # Clear older rect
                self.__clearHoveringMarker()
                # Update hovering data
                if hovering is not None:
                    self.hoveringMarker = hovering
                    self.hoveringSceneObjs = self.__drawHoveringMarker(hovering)
                # Redraw markers
                self.__updateMarkers(keepAlgResults=True)

    def __onMouseOut(self, isLeft: bool) -> None:
        """
        Private method called when the mouse left a viewer space.
        :param: isLeft a boolean to choose emitting viewer
        """
        # Clear status
        self.isDragging = False
        self.selectedMarker = None
        self.__clearHoveringMarker()
        # Redraw markers
        self.__updateMarkers(keepAlgResults=True)

    def __mapToViewer(self, pos: QPoint, isLeft: bool) -> QPointF:
        """
        Private method that maps a pos [x, y] into the viewer space.
        :param: pos the position to map
        :param: isLeft a boolean to choose which viewer to use
        :return: the converted 2d vector
        """
        viewer = self.leftImgViewer if isLeft else self.rightImgViewer
        tmp = viewer.mapToScene(pos)
        tmp = QPointF(min(max(tmp.x(), 0), viewer.imgwidth), min(max(tmp.y(), 0), viewer.imgheight))
        return tmp

    def __findMarkerAt(self, pos: QPointF, isLeft: bool) -> Optional[int]:
        """
        Private method to find marker under [x, y].
        :param: pos the position to check
        :param: isLeft a boolean to choose which viewer to use
        :return: the index of the marker found or None
        """
        # Iterate over the markers list to check if any marker exists at [x, y]
        for (i, marker) in enumerate(self.markers):
            # Find marker bbox
            (bboxL, bboxR) = self.markers[i].getBBox()
            bbox: QRectF = bboxL if isLeft else bboxR
            # Check if bbox contains pos
            if bbox is not None and bbox.contains(pos):
                return i
        return None

    def __toggleMarker(self, i: int) -> None:
        """
        Private method to "toggle" marker with index i.
        :param: i the index of the marker to toggle.
        """
        # Forward
        self.markers[i].toggleType()
        self.__clearMarker(i, False)

    def __clearHoveringMarker(self) -> None:
        """
        Private method to clear hovering data.
        """
        # Clear only if exists
        if self.hoveringMarker is not None:
            # Retrieve scene objs
            (rectL, rectR) = self.hoveringSceneObjs
            # Remove them from scenes
            if rectL is not None:
                self.leftImgViewer.scene.removeItem(rectL)
            if rectR is not None:
                self.rightImgViewer.scene.removeItem(rectR)
            self.hoveringMarker = None
            self.hoveringSceneObjs = None

    def __drawHoveringMarker(self, i: int) -> Tuple[Optional[QGraphicsRectItem], Optional[QGraphicsRectItem]]:
        """
        Private method to draw hovering box.
        :param: i the index of the marker to hover
        :return: the (leftRect, rightRect) created
        """
        # Create drawing pen
        pen = QPen(MarkerObjData.MARKER_HOVER_COLOR, MarkerObjData.MARKER_HOVER_WIDTH)
        pen.setCosmetic(True)
        # Retrieve bbox
        (bboxL, bboxR) = self.markers[i].getBBox()
        # Draw rects
        rectL = rectR = None
        if bboxL is not None:
            rectL = self.leftImgViewer.scene.addRect(bboxL, pen)
            rectL.setZValue(6)
        if bboxR is not None:
            rectR = self.rightImgViewer.scene.addRect(bboxR, pen)
            rectR.setZValue(6)
        return rectL, rectR

    def __deleteAllMarkers(self) -> None:
        """
        Private method to remove all the markers.
        """
        for i in range(0, len(self.markers)):
            self.__clearMarker(i, False)
        self.markers = []
        self.lMarkerIndex = 0
        self.rMarkerIndex = 0

    def __deleteMarker(self, i: int) -> None:
        """
        Private method to remove a marker from the markers list.
        :param: i the index of the marker
        """
        self.__clearMarker(i, False)
        marker = self.markers[i]
        self.markers = self.markers[:i] + self.markers[i + 1:]
        if marker.lViewPos is not None:
            self.lMarkerIndex -= 1
        if marker.rViewPos is not None:
            self.rMarkerIndex -= 1

    def __clearMarker(self, i: int, onlyText: bool) -> None:
        """
        Private method to clear marker scene objs.
        :param: i the index of the marker to clear.
        :param: onlyText is a boolean that specifies to only clear text items.
        """
        # Remove items from scene
        for [objL, objR] in self.markers[i].textObjs:
            if objL is not None:
                self.leftImgViewer.scene.removeItem(objL)
            if objR is not None:
                self.leftImgViewer.scene.removeItem(objR)
        # Clear array
        self.markers[i].textObjs = []
        if not onlyText:
            # Remove items from scene
            for [objL, objR] in self.markers[i].sceneObjs:
                if objL is not None:
                    self.leftImgViewer.scene.removeItem(objL)
                if objR is not None:
                    self.leftImgViewer.scene.removeItem(objR)
            # Clear array
            self.markers[i].sceneObjs = []

    def __createNewMarker(self, lpos: Optional[QPointF], rpos: Optional[QPointF]) -> None:
        """
        Private method to add a marker at pos [x, y].
        :param: lpos the position where to add the marker (left viewer)
        :param: rpos the position where to add the marker (right viewer)
        """
        # Find next available ID
        identifier = max(self.markers, key=lambda x: x.identifier).identifier + 1 if len(self.markers) > 0 else 1
        # Create a marker obj
        marker = MarkerObjData(identifier, lpos, rpos, self.pxSizeL, self.pxSizeR, MarkerObjData.SOFT_MARKER)
        self.markers.append(marker)

    def __addMarker(self, pos: QPointF, isLeft: bool) -> None:
        """
        Private method to add a marker at pos [x, y].
        :param: pos the position where to add the marker
        :param: isLeft a boolean to flag right / left viewer
        """
        # Find marker obj at index and update its position
        if isLeft:
            # Check if we must create a *NEW* marker
            if self.lMarkerIndex >= self.rMarkerIndex:
                self.__createNewMarker(pos, None)
            else:
                self.markers[self.lMarkerIndex].setLPos(pos)
            self.__clearMarker(self.lMarkerIndex, False)
            self.lMarkerIndex += 1
        else:
            # Check if we must create a *NEW* marker
            if self.rMarkerIndex >= self.lMarkerIndex:
                self.__createNewMarker(None, pos)
            else:
                self.markers[self.rMarkerIndex].setRPos(pos)
            self.__clearMarker(self.rMarkerIndex, False)
            self.rMarkerIndex += 1

    def __drawMarker(self, marker: MarkerObjData) -> None:
        """
        Private method to draw marker obj.
        :param: marker the marker to draw
        """
        # Redraw only if needed
        if len(marker.sceneObjs) == 0:
            # Draw lines
            sceneObjs = []
            for (leftLine, rightLine) in marker.getLines():
                lineL = lineR = None
                if leftLine is not None:
                    lineL = self.leftImgViewer.scene.addLine(leftLine, marker.pen)
                    lineL.setZValue(5)
                if rightLine is not None:
                    lineR = self.rightImgViewer.scene.addLine(rightLine, marker.pen)
                    lineR.setZValue(5)
                sceneObjs.append([lineL, lineR])
            # Update list
            marker.sceneObjs = sceneObjs
        # Redraw only if needed
        if len(marker.textObjs) == 0:
            # Draw labels
            textObjs = []
            color = marker.pen.color().name()
            (bboxL, bboxR) = marker.getBBox()
            textL = textR = None
            errL = errR = None
            zoomL = self.leftImgViewer.zoom_factor
            zoomR = self.rightImgViewer.zoom_factor
            # Left viewer
            if marker.lViewPos is not None:
                # Left identifier
                textL = QGraphicsTextItem()
                textL.setHtml(
                    '<div style="background:' + color + ';">' + str(marker.identifier) + '</p>')
                textL.setFont(QFont("Roboto", 12, QFont.Bold))
                textL.setOpacity(0.75)
                textL.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                textL.setDefaultTextColor(Qt.black)
                textL.setZValue(8)
                # Center text to top side
                textL.adjustSize()
                pos = bboxL.topLeft()
                pos.setX(pos.x() + 0.5 + (MarkerObjData.MARKER_SIZE - textL.textWidth() / 2.0 / zoomL) / self.pxSizeL)
                pos.setY(pos.y() - textL.boundingRect().height() / zoomL)
                textL.setPos(pos)
                # Left error
                lErrorLabelVisibility = (self.leftImgViewer.zoom_factor > 3.25)
                errL = QGraphicsTextItem()
                errL.setHtml('<div style="background:' + color + ';">' + str(marker.error) + '</p>')
                errL.setFont(QFont("Roboto", 12, QFont.Bold))
                errL.setOpacity(0.5)
                errL.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                errL.setDefaultTextColor(Qt.black)
                errL.setZValue(7)
                errL.setVisible(lErrorLabelVisibility)
                # Center text to bottom side
                errL.adjustSize()
                pos = bboxL.bottomLeft()
                pos.setX(pos.x() + 0.5 + (MarkerObjData.MARKER_SIZE - errL.textWidth() / 2.0 / zoomL) / self.pxSizeL)
                errL.setPos(pos)
                # Add text to scenes
                self.leftImgViewer.scene.addItem(textL)
                self.leftImgViewer.scene.addItem(errL)
            # Right viewer
            if marker.rViewPos is not None:
                # Right identifier
                textR = QGraphicsTextItem()
                textR.setHtml('<div style="background:' + color + ';">' + str(marker.identifier) + '</p>')
                textR.setFont(QFont("Roboto", 12, QFont.Bold))
                textR.setOpacity(0.75)
                textR.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                textR.setDefaultTextColor(Qt.black)
                textR.setZValue(8)
                # Center text to top side
                textR.adjustSize()
                pos = bboxR.topLeft()
                pos.setX(pos.x() + 0.5 + (MarkerObjData.MARKER_SIZE - textR.textWidth() / 2.0 / zoomR) / self.pxSizeR)
                pos.setY(pos.y() - textR.boundingRect().height() / zoomR)
                textR.setPos(pos)
                # Right error
                rErrorLabelVisibility = (self.rightImgViewer.zoom_factor > 3.25)
                errR = QGraphicsTextItem()
                errR.setHtml('<div style="background:' + color + ';">' + str(marker.error) + '</p>')
                errR.setFont(QFont("Roboto", 12, QFont.Bold))
                errR.setOpacity(0.5)
                errR.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                errR.setDefaultTextColor(Qt.black)
                errR.setZValue(7)
                errR.setVisible(rErrorLabelVisibility)
                # Center text to bottom side
                errR.adjustSize()
                pos = bboxR.bottomLeft()
                pos.setX(pos.x() + 0.5 + (MarkerObjData.MARKER_SIZE - errR.textWidth() / 2.0 / zoomR) / self.pxSizeR)
                errR.setPos(pos)
                # Add text to scenes
                self.rightImgViewer.scene.addItem(textR)
                self.rightImgViewer.scene.addItem(errR)
            # Update list
            textObjs.append([textL, textR])
            textObjs.append([errL, errR])
            marker.textObjs = textObjs

    def __updateMarkers(self, keepAlgResults: bool) -> None:
        """
        Private method to redraw markers.
        :param: keepAlgResults is a boolean that speeds up redraw when no calculation are required.
        """
        # Try pre-computing the align algorithm
        if not keepAlgResults:
            self.__leastSquaresWithSVD()
        # Draw markers
        for marker in self.markers:
            self.__drawMarker(marker)
        # Invalidate scene
        self.leftImgViewer.scene.invalidate()
        self.rightImgViewer.scene.invalidate()

    def __updateImgViewers(self) -> None:
        """
        Private method to update the edit page viewers
        """
        # Retrieve indexes
        index1 = self.leftCombobox.currentIndex()
        index2 = self.rightCombobox.currentIndex()
        # Pixel size
        self.pxSizeL = self.project.images[index1].pixelSize()
        self.pxSizeR = self.project.images[index2].pixelSize()
        # Default channel (0)
        channel1 = self.project.images[index1].channels[0]
        channel2 = self.project.images[index2].channels[0]
        # Check if channel is loaded
        if channel1.qimage is None:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            channel1.loadData()
            QApplication.restoreOverrideCursor()
        if channel2.qimage is None:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            channel2.loadData()
            QApplication.restoreOverrideCursor()
        # Update preview size
        self.__updateSizes(channel1.qimage, self.pxSizeL, channel2.qimage, self.pxSizeR)
        # Update viewer
        self.leftImgViewer.setImg(channel1.qimage)
        self.leftImgViewer.px_to_mm = self.pxSizeL
        self.rightImgViewer.setImg(channel2.qimage)
        self.rightImgViewer.px_to_mm = self.pxSizeR
        # Delete old markers
        self.__deleteAllMarkers()
        # Clear data of last comparison
        self.alphaSlider.setValue(50)
        self.thresholdSlider.setValue(32)
        self.rSlider.setValue(0)
        self.xSlider.setValue(0)
        self.ySlider.setValue(0)
        # [SCALE] self.sSlider.setValue(0)
        # Restore previously saved markers
        projectMarkers = self.project.retrieveMarkersOrEmpty(
            refImgId=self.project.images[index1].id,
            coregImgId=self.project.images[index2].id,
        )
        for (i, savedMarker) in enumerate(projectMarkers):
            refPos = savedMarker['refPos']
            coregPos = savedMarker['coregPos']
            lPos = QPointF(refPos[0], refPos[1])
            rPos = QPointF(coregPos[0], coregPos[1])
            typ = savedMarker['type']
            self.__addMarker(pos=lPos, isLeft=True)
            self.__addMarker(pos=rPos, isLeft=False)
            if typ == MarkerObjData.HARD_MARKER:
                self.__toggleMarker(i)
        self.__updateMarkers(keepAlgResults=False)

    def __updateSizes(self, img1: QImage, pxSize1: float, img2: QImage, pxSize2: float) -> None:
        """
        Private method to update internal reference size for preview images.
        The preview size must contains both images.
        :param: img1 the first image to contain
        :param: pxSize1 the px_to_mm of the img1
        :param: img2 the second image to contain
        :param: pxSize2 the px_to_mm of the img2
        """
        # Retrieve sizes
        h1, w1 = img1.height() * pxSize1, img1.width() * pxSize1
        self.sizeL = QPointF(w1, h1)
        h2, w2 = img2.height() * pxSize2, img2.width() * pxSize2
        self.sizeR = QPointF(w2, h2)
        # Find box containing both images
        ph, pw = max(h1, h2), max(w1, w2)
        # Update preview size
        self.xSlider.setMinimum(-pw)
        self.xSlider.setMaximum(+pw)
        self.ySlider.setMinimum(-ph)
        self.ySlider.setMaximum(+ph)

    def __initializePreview(self) -> None:
        """
        Private method called to initialize the preview.
        """
        # Retrieve images
        img1 = self.leftImgViewer.img_map
        img2 = self.rightImgViewer.img_map
        # Retrieve markers
        (q, p) = self.__normalizedMarkers()
        # Pass images to viewers
        self.leftPreviewViewer.initializeData(img1, img2, self.sizeL, self.sizeR, q, p)
        self.rightPreviewViewer.initializeData(img1, img2, self.sizeL, self.sizeR, q, p)
        self.markers_copy = self.markers.copy()
        self.__fillTable()
        self.table.itemChanged[QTableWidgetItem].connect(self.updateComputation)
        self.__updateMeanErrors()

    def __updatePreview(self) -> None:
        """
        Private method to update the preview.
        """
        # Update R and T values
        trax = (self.T[0] * 2.0) / max(self.sizeL.x(), self.sizeR.x())
        tray = (self.T[1] * 2.0) / max(self.sizeL.y(), self.sizeR.y())
        rot = self.R / QtAlignmentToolWidget.ROT_PRECISION
        # [SCALE] sca = self.S / QtAlignmentToolWidget.SCALE_PRECISION
        self.leftPreviewViewer.updateRotation(rot)
        self.leftPreviewViewer.updateTranslation(QPointF(trax, tray))
        # [SCALE] self.leftPreviewViewer.updateScale(sca)
        self.rightPreviewViewer.updateRotation(rot)
        self.rightPreviewViewer.updateTranslation(QPointF(trax, tray))
        # [SCALE] self.rightPreviewViewer.updateScale(sca)

        # Update threshold
        self.rightPreviewViewer.updateThreshold(self.threshold)

        # Update alpha value
        self.leftPreviewViewer.updateAlpha(self.alpha / 100.0)

        # update error table
        if self.error_table_flag is True:
            # self.__updateErrorTableAfterManualAdjustment()
            self.__computeErrors()
            self.__updateErrorTable()

    def __updateErrorTableAfterManualAdjustment(self):

        # for (i, marker) in enumerate(self.markers):
        #     marker.error = None
        #     self.__clearMarker(i, True)
        #
        # # Ensure at least 3 marker are placed
        # if not self.__hasValidMarkers():
        #     return
        #

        R = np.deg2rad(self.R / QtAlignmentToolWidget.ROT_PRECISION)
        # [SCALE] S = self.S / QtAlignmentToolWidget.SCALE_PRECISION

        maxw = max(self.sizeL.x(), self.sizeR.x())
        maxh = max(self.sizeL.y(), self.sizeR.y())

        tx = self.T[0] / maxw
        ty = self.T[1] / maxh

        for marker in self.markers:
            qx = float(marker.lViewPos.x())
            qy = float(marker.lViewPos.y())

            px = float(marker.rViewPos.x())
            py = float(marker.rViewPos.y())

            px_n = px / maxw
            py_n = py / maxh

            # apply rotation and translation
            px_n = (math.cos(R) * px_n - math.sin(R) * py_n) + tx
            py_n = (math.sin(R) * px_n + math.cos(R) * py_n) + ty

            px = px_n * maxw
            py = py_n * maxh

            # FIXME: apply scaling
            # TODO

            marker.errorx = round(qx - px, 2)
            marker.errory = round(qy - py, 2)
            marker.error = round(math.sqrt(marker.errorx ** 2 + marker.errory ** 2), 2)

        self.__updateErrorTable()

    def __togglePreviewMode(self, isPreviewMode: bool) -> None:
        """
        Private method to set widget visibility to toggle the Preview Mode on/off.
        :param: isPreviewMode a boolean value to enable / disable the Preview Mode
        """
        # (Preview-ONLY) widget
        self.meanex.setVisible(isPreviewMode)
        self.meaney.setVisible(isPreviewMode)
        self.meanerror.setVisible(isPreviewMode)
        self.labelmeanx.setVisible(isPreviewMode)
        self.labelmeany.setVisible(isPreviewMode)
        self.labelmeanerr.setVisible(isPreviewMode)
        self.table.setVisible(isPreviewMode)
        self.leftPreviewViewer.setVisible(isPreviewMode)
        self.rightPreviewViewer.setVisible(isPreviewMode)
        self.backToEditButton.setVisible(isPreviewMode)
        self.resetTransfButton.setVisible(isPreviewMode)
        self.showMarkersCheck.setVisible(isPreviewMode)
        self.confirmAlignmentButton.setVisible(isPreviewMode)
        self.alphaSliderLabel.setVisible(isPreviewMode)
        self.alphaSlider.setVisible(isPreviewMode)
        self.thresholdSliderLabel.setVisible(isPreviewMode)
        self.thresholdSlider.setVisible(isPreviewMode)
        self.xSliderLabel.setVisible(isPreviewMode)
        self.xSlider.setVisible(isPreviewMode)
        self.moveLeftButton.setVisible(isPreviewMode)
        self.moveRightButton.setVisible(isPreviewMode)
        self.ySliderLabel.setVisible(isPreviewMode)
        self.ySlider.setVisible(isPreviewMode)
        self.moveUpButton.setVisible(isPreviewMode)
        self.moveDownButton.setVisible(isPreviewMode)
        self.rSliderLabel.setVisible(isPreviewMode)
        self.rSlider.setVisible(isPreviewMode)
        self.rotateLeftButton.setVisible(isPreviewMode)
        self.rotateRightButton.setVisible(isPreviewMode)
        # [SCALE] self.sSliderLabel.setVisible(False)
        # [SCALE] self.sSlider.setVisible(False)
        # (NON-Preview-ONLY) widgets
        self.leftImgViewer.setVisible(not isPreviewMode)
        self.rightImgViewer.setVisible(not isPreviewMode)
        self.clearMarkersButton.setVisible(not isPreviewMode)
        self.syncCheck.setVisible(not isPreviewMode)
        self.autoAlignButton.setVisible(not isPreviewMode)
        self.leftComboboxLabel.setVisible(not isPreviewMode)
        self.leftCombobox.setVisible(not isPreviewMode)
        self.rightComboboxLabel.setVisible(not isPreviewMode)
        self.rightCombobox.setVisible(not isPreviewMode)

    def __hasValidMarkers(self) -> bool:
        """
        Private method to check if we have enough markers to compute the alignment.
        :return: a boolean to indicates if we have enough valid markers to proceed.
        """
        # At least 3 markers
        if len(self.markers) < 3:
            return False
        # All markers must be "complete" (have lpos and rpos)
        for marker in self.markers:
            if not marker.isComplete():
                return False
        # Valid !
        return True

    def __normalizedMarkers(self) -> Tuple[List[QPointF], List[QPointF]]:
        """
        Private method to retrieve markers with normalized coord.
        :return: tuple with the two list of markers
        """
        # Normalize markers relative to max side
        maxw = max(self.sizeL.x(), self.sizeR.x())
        maxh = max(self.sizeL.y(), self.sizeR.y())
        leftPoints = [QPointF(marker.lViewPos.x() / maxw, marker.lViewPos.y() / maxh) for marker in self.markers]
        rightPoints = [QPointF(marker.rViewPos.x() / maxw, marker.rViewPos.y() / maxh) for marker in self.markers]
        return leftPoints, rightPoints

    @pyqtSlot(QTableWidgetItem)
    def updateComputation(self, item_changed):

        flag_update_table = True

        num = 0
        for i in range(0, self.table.rowCount()):
            item = self.table.item(i, 0)
            if item is not None:
                if item.checkState() == Qt.Checked:
                    num = num + 1
            else:
                flag_update_table = False

        if flag_update_table:

            if num > 3:
                self.markers = []
                for i in range(0, self.table.rowCount()):
                    item = self.table.item(i, 0)
                    if item.checkState() == Qt.Checked:
                        self.markers.append(self.markers_copy[i])

                self.__leastSquaresWithSVD()

                # update points
                (q, p) = self.__normalizedMarkers()
                self.leftPreviewViewer.points = ([QVector2D(pt) for pt in q.copy()], [QVector2D(pt) for pt in p.copy()])
                self.leftPreviewViewer.redraw()
                self.rightPreviewViewer.points = (
                    [QVector2D(pt) for pt in q.copy()], [QVector2D(pt) for pt in p.copy()])
                self.rightPreviewViewer.redraw()

                # update table
                self.__computeErrors()
                self.__updateErrorTable()

            else:
                box = QMessageBox()
                box.setText("This marker cannot be enabled, you always need at least four markers")
                box.exec()
                item_changed.setCheckState(Qt.Checked)

    def __updateErrorTable(self) -> None:

        for i in range(0, self.table.rowCount()):
            item = self.table.item(i, 0)
            if item is None:
                return

        self.table.blockSignals(True)

        c = 0
        for i in range(0, self.table.rowCount()):
            item = self.table.item(i, 0)
            if item.checkState() == Qt.Checked:
                self.table.setItem(i, 1, QTableWidgetItem(str(self.markers[c].identifier)))
                self.table.setItem(i, 2, QTableWidgetItem(str(self.markers[c].errorx)))
                self.table.setItem(i, 3, QTableWidgetItem(str(self.markers[c].errory)))
                self.table.setItem(i, 4, QTableWidgetItem(str(self.markers[c].error)))
                c = c + 1
            else:
                self.table.setItem(i, 2, QTableWidgetItem(""))
                self.table.setItem(i, 3, QTableWidgetItem(""))
                self.table.setItem(i, 4, QTableWidgetItem(""))

        self.__updateMeanErrors()

        self.error_table_flag = False

        self.table.blockSignals(False)

    def __fillTable(self) -> None:

        #### icon, id, ex, ey, edist ####

        self.table.setFocusPolicy(Qt.NoFocus)

        self.table.setRowCount(len(self.markers_copy))
        for i in range(0, len(self.markers_copy)):
            chbx = QTableWidgetItem()
            chbx.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chbx.setCheckState(Qt.CheckState.Checked)

            self.table.setItem(i, 0, chbx)
            self.table.setItem(i, 1, QTableWidgetItem(str(self.markers_copy[i].identifier)))
            self.table.setItem(i, 2, QTableWidgetItem(str(self.markers_copy[i].errorx)))
            self.table.setItem(i, 3, QTableWidgetItem(str(self.markers_copy[i].errory)))
            self.table.setItem(i, 4, QTableWidgetItem(str(self.markers_copy[i].error)))

    def __updateMeanErrors(self):

        sumex = 0.0
        sumey = 0.0
        sumerr = 0.0

        for i in range(0, len(self.markers)):
            sumex = sumex + abs(self.markers[i].errorx)
            sumey = sumey + abs(self.markers[i].errory)
            sumerr = sumerr + self.markers[i].error

        meanerrorx = round((sumex / len(self.markers)), 1)
        meanerrory = round(sumey / len(self.markers), 1)
        meanerror = round(sumerr / len(self.markers), 1)
        self.meanex.setText(("{:.3f}".format(meanerrorx)))
        self.meaney.setText(("{:.3f}".format(meanerrory)))
        self.meanerror.setText(("{:.3f}".format(meanerror)))

    def __computeErrors(self):

        # FIXME: scale is not considered

        # NOTE: self.R is an angle (in degree) and not a rotation matrix
        angle = np.deg2rad(self.R / QtAlignmentToolWidget.ROT_PRECISION)
        # [SCALE] S = self.S / QtAlignmentToolWidget.SCALE_PRECISION

        maxw = max(self.sizeL.x(), self.sizeR.x())
        maxh = max(self.sizeL.y(), self.sizeR.y())
        T = [self.T[0] / maxw, self.T[1] / maxh]

        (q, p) = self.__normalizedMarkers()

        Rmat = np.matrix([[math.cos(-angle), math.sin(-angle)],
                          [-math.sin(-angle), math.cos(-angle)]])

        sol = [(Rmat @ [pi.x(), pi.y()] + T) for pi in p]
        sol = [QPointF(s[0, 0], s[0, 1]) for s in sol]

        # Compute errors
        err = [[a.x() - b.x(), a.y() - b.y()] for (a, b) in zip(sol, q)]
        err = [(x * maxw, y * maxh) for (x, y) in err]
        disterr = [math.sqrt(x ** 2 + y ** 2) for (x, y) in err]
        for (i, (e, marker)) in enumerate(zip(disterr, self.markers)):
            marker.errorx = round(err[i][0], 1)
            marker.errory = round(err[i][1], 1)
            marker.error = round(e, 1)

    def __leastSquaresWithSVD(self) -> None:
        """
        Private method to compute the Least-Squares Rigid Motion using SVD.
        This algorithm tries to MINIMIZE the equation:
            sum(
                w[i] * abs(
                        (R * p[i] + T) - q[i]
                    ) ^ 2
            )
        where R is the rotation matrix and T is the translation vec (to find)
        """
        # Reset results
        # [SCALE] self.svdRes = [0, [0, 0], 0]
        self.svdRes = [0, [0, 0]]

        # Reset each marker error
        for (i, marker) in enumerate(self.markers):
            marker.error = None
            self.__clearMarker(i, True)

        # Ensure at least 3 marker are placed
        if not self.__hasValidMarkers():
            return

        # ==================================================================================
        # [0] Retrieve vars
        # ==================================================================================
        # n  = #points
        # d  = dim of points (2 for 2D, etc...)
        # w  = weights
        # sw = sum of weights
        # q  = points (reference)
        # p  = points (to align)
        # ==================================================================================
        n = len(self.markers)
        d = 2
        w = [marker.weight for marker in self.markers]
        sw = sum(w)
        (q, p) = self.__normalizedMarkers()

        # [SCALE] # ==================================================================================
        # [SCALE] # [Extra] Pre-Scale
        # [SCALE] # ==================================================================================
        # [SCALE] def dist(a: QPointF, b: QPointF):
        # [SCALE]     return math.sqrt(((a.x() - b.x()) ** 2 + (a.y() - b.y()) ** 2))
        # [SCALE]
        # [SCALE] S = 1.0
        # [SCALE] if self.canScale:
        # [SCALE]     samples = []
        # [SCALE]     for si in range(QtAlignmentToolWidget.SCALE_SAMPLING_COUNT):
        # [SCALE]         i = random.randint(0, n - 1)
        # [SCALE]         j = random.randint(0, n - 1)
        # [SCALE]         if i != j:
        # [SCALE]             samples.append(dist(p[i], p[j]) / dist(q[i], q[j]))
        # [SCALE]     S = float(sum(samples)) / len(samples)
        # [SCALE]     S = 1.0 / S
        # [SCALE]
        # [SCALE] p = [point * S for point in p]

        # ==================================================================================
        # [1] Compute the weighted centroids _q (for q) and _p (for p)
        # ==================================================================================
        _p = [0, 0]
        _q = [0, 0]
        for i in range(0, n):
            f = w[i] / sw
            _p[0] += p[i].x() * f
            _p[1] += p[i].y() * f
            _q[0] += q[i].x() * f
            _q[1] += q[i].y() * f

        # ==================================================================================
        # [2] Compute the centered vectors y (for q) and x (for p)
        # ==================================================================================
        y = [[qi.x() - _q[0], qi.y() - _q[1]] for qi in q]
        x = [[pi.x() - _p[0], pi.y() - _p[1]] for pi in p]

        # ==================================================================================
        # [3] Compute the covariance matrix C (dxd)
        # ==================================================================================
        # X = [[x[0][0], x[1][0], x[2][0], ...],
        #      [x[0][1], x[1][1], x[2][1], ...],
        #      ...]
        # Y = [[y[0][0], y[1][0], y[2][0], ...],
        #      [y[0][1], y[1][1], y[2][1], ...],
        #      ...]
        # W = diagonal(w[0], w[1], ..., w[n])
        # ==================================================================================
        X = np.transpose(np.asmatrix(x))
        Xt = np.transpose(X)
        Y = np.transpose(np.asmatrix(y))
        Yt = np.transpose(Y)
        W = np.identity(n) * w
        C = X @ W @ Yt

        # ==================================================================================
        # [4] Compute SVD & Find rotation
        # ==================================================================================
        u, s, vt = np.linalg.svd(C)
        v = np.transpose(vt)
        ut = np.transpose(u)
        detvut = np.linalg.det(v @ ut)
        tmp = np.identity(d)
        tmp[-1, -1] = detvut
        R = v @ tmp @ ut

        # ==================================================================================
        # [5] Find translation
        # ==================================================================================
        T = _q - R @ _p

        # ==================================================================================
        # [6] Solution
        # ==================================================================================
        sol = [(R @ [pi.x(), pi.y()] + T) for pi in p]
        sol = [QPointF(s[0, 0], s[0, 1]) for s in sol]

        # Compute errors
        err = [[a.x() - b.x(), a.y() - b.y()] for (a, b) in zip(sol, q)]
        maxw = max(self.sizeL.x(), self.sizeR.x())
        maxh = max(self.sizeL.y(), self.sizeR.y())
        err = [(x * maxw, y * maxh) for (x, y) in err]
        disterr = [math.sqrt(x ** 2 + y ** 2) for (x, y) in err]
        for (i, (e, marker)) in enumerate(zip(disterr, self.markers)):
            marker.errorx = round(err[i][0], 2)
            marker.errory = round(err[i][1], 2)
            marker.error = round(e, 2)

        # Results
        R = math.atan2(R[1, 0], R[0, 0])
        R = np.rad2deg(R)
        self.R = R * QtAlignmentToolWidget.ROT_PRECISION
        self.svdRes[0] = self.R

        T = [T[0, 0] * maxw, T[0, 1] * maxh]
        self.T = np.array(T)
        self.svdRes[1] = [self.T[0], self.T[1]]

        # [SCALE] S = round(S, 2)
        # [SCALE] self.S = S * QtAlignmentToolWidget.SCALE_PRECISION
        # [SCALE] self.svdRes[2] = self.S

        # Update UI
        # [SCALE] self.sSlider.blockSignals(True)
        self.xSlider.setValue(self.T[0])
        self.ySlider.setValue(self.T[1])
        self.rSlider.setValue(self.R)
        # [SCALE] self.sSlider.setMinimum(round(self.S * (1.0 - QtAlignmentToolWidget.SCALE_RANGE)))
        # [SCALE] self.sSlider.setMaximum(round(self.S * (1.0 + QtAlignmentToolWidget.SCALE_RANGE)))
        # [SCALE] self.sSlider.setValue(self.S)
        # [SCALE] self.sSlider.setEnabled(self.canScale)
        # [SCALE] self.scaleIncButton.setEnabled(self.canScale)
        # [SCALE] self.scaleDecButton.setEnabled(self.canScale)
        # [SCALE] self.sSlider.blockSignals(False)

        # check if __computeErrors is ok
        # self.__computeErrors()
        # for i, marker in enumerate(self.markers):
        #    print("X difference:", marker.errorx - round(err[i][0], 2))
        #    print("Y difference:", marker.errory - round(err[i][1], 2))
