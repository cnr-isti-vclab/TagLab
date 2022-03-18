import math
from typing import Optional

import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot, QLineF, QRectF, QPoint
from PyQt5.QtGui import QImage, QMouseEvent, QPen, QFont, QCloseEvent, QKeyEvent, QOpenGLShaderProgram, QOpenGLShader, \
    QOpenGLVersionProfile, QMatrix4x4, QWheelEvent, QOpenGLTexture, QVector2D, QOpenGLFramebufferObject, QVector4D
from PyQt5.QtWidgets import QWidget, QSizePolicy, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QSlider, QApplication, \
    QCheckBox, QPushButton, QMessageBox, QGraphicsTextItem, QGraphicsItem, QOpenGLWidget, QGraphicsRectItem
from PyQt5._QOpenGLFunctions_2_0 import QOpenGLFunctions_2_0

from source.QtImageViewer import QtImageViewer


def checkGL(obj, res):
    """
    Syntactic sugar for error check + log
    """
    if not res:
        print(obj.log())


class QtSimpleOpenGlShaderViewer(QOpenGLWidget):
    """
    Custom widget to handle img preview with shaders.
    """

    V_SHADER_SOURCE = """
    precision highp float;
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
    precision highp float;
    varying vec2 vTex;
    uniform sampler2D uTex;
    void main(void) {
        gl_FragColor = texture2D(uTex, vTex);
    }
    """

    V_SHADER_SOURCE_POINTS = """
    precision highp float;
    attribute vec2 aPos;
    uniform float uSize;
    uniform mat4 uMatrix;
    void main(void) {
        gl_PointSize = uSize;
        gl_Position = uMatrix * vec4(aPos, 0, 1);
    }
    """

    F_SHADER_SOURCE_POINTS = """
    precision highp float;
    uniform vec4 uCol;
    void main(void) {
        vec2 coord = (gl_PointCoord - 0.5) * 2.0;
        float distFromCenter = length(coord);
        if (distFromCenter >= 1.0) {
            gl_FragColor = vec4(0, 0, 0, 0);
        } else {
            gl_FragColor = uCol;
        }
    }
    """

    QUAD_V = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    QUAD_T = [(0, 1), (0, 0), (1, 1), (1, 0)]

    def __init__(self, vSrc, fSrc, parent=None):
        super(QtSimpleOpenGlShaderViewer, self).__init__(parent)
        # Open GL
        self.gl: Optional[QOpenGLFunctions_2_0] = None
        self.programs: list[QOpenGLShaderProgram] = []
        self.textures: list[QOpenGLTexture] = []
        self.framebuffers: list[QOpenGLFramebufferObject] = []
        self.pointProgram: Optional[QOpenGLShaderProgram] = None
        self.points = [[], []]
        self.vSrc = vSrc
        self.fSrc = fSrc
        self.keepFB = False
        self.drawPoints = True
        # Transformation status
        self.t = [0.0, 0.0]
        self.s = 1.0
        self.w = 100
        self.h = 100
        self.ratioWH = 1.0
        # Gesture
        self.lastPos = None
        self.minZoom = 0.25
        self.maxZoom = 128.0
        # Alignment data
        self.rot = 0
        self.tra = QVector2D(0, 0)

    def __createProgram(self, vSrc: str, fSrc: str, hasTex: bool) -> Optional[QOpenGLShaderProgram]:
        """
        Private method to create a Shader Program with passed v-shader and f-shader.
        :param: vSrc the source code of the vertex shader
        :param: fSrc the source code of the fragment shader
        :param: loadQuad a boolean to toggle pre upload of quad data
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
        # Bind FB and Program
        checkGL(self.framebuffers[i], self.framebuffers[i].bind())
        checkGL(self.programs[0], self.programs[0].bind())
        # Bind texture
        self.gl.glActiveTexture(self.gl.GL_TEXTURE0)
        self.gl.glBindTexture(self.gl.GL_TEXTURE_2D, self.textures[i].textureId())
        # Update uniforms
        self.programs[0].setUniformValue("uTex", 0)
        self.programs[0].setUniformValue("uMatrix", mat)
        # Reload quad data
        self.programs[0].enableAttributeArray(0)
        self.programs[0].setAttributeArray(0, QtSimpleOpenGlShaderViewer.QUAD_V.copy())
        self.programs[0].enableAttributeArray(1)
        self.programs[0].setAttributeArray(1, QtSimpleOpenGlShaderViewer.QUAD_T.copy())
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
        # Create Matrix for 1st Quad
        matrix1 = QMatrix4x4()
        matrix1.scale(self.ratioWH, 1, 1)               # Keep aspect ratio
        # Create Matrix for 2nd Quad
        matrix2 = QMatrix4x4()
        matrix2.scale(self.ratioWH, 1, 1)               # Keep aspect ratio
        matrix2.rotate(self.rot, 0.0, 0.0, 1.0)         # Rotation (pivot is the image center)
        matrix2.translate(self.tra[0], self.tra[1], 0)  # Translation
        # Create Transformation Matrix
        matrix3 = QMatrix4x4()
        matrix3.scale(min(self.w, self.h) / self.w, min(self.w, self.h) / self.h, 1)  # Keep aspect ratio
        matrix3.translate(self.t[0], -self.t[1], 0)                                   # Pan
        matrix3.scale(self.s, self.s, 1)                                              # Zoom
        # Check if needs to redraw buffers
        # (Needed only when user zoom or pan or manually changes offset or rotation)
        if not self.keepFB:
            # Draw tex 0 into fb 0
            self.__drawTexturePass(0, matrix3 * matrix1)
            # Draw tex 1 into fb 1
            self.__drawTexturePass(1, matrix3 * matrix2)
            # Clear dirty flag
            self.keepFB = True
        # Create Matrix (for reversing framebuffer)
        matrix4 = QMatrix4x4()
        matrix4.scale(1, -1, 1)
        # Draw fb into screen (scriptable)
        self.__drawFrameBufferPass(matrix4)
        # Draw marker points
        if self.drawPoints:
            self.__drawPointsPass(0, matrix3 * matrix1, QVector4D(1.0, 0.0, 0.0, 1.0))
            self.__drawPointsPass(1, matrix3 * matrix2, QVector4D(1.0, 1.0, 0.0, 1.0))

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
        self.t[0] += dx / wh
        self.t[1] += dy / hw
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
        # Find normalized mouse pos
        [mx, my] = [event.pos().x() / (self.w // 2) - 1, event.pos().y() / (self.h // 2) - 1]
        # Zoom towards mouse pos
        self.t[0] = mx - (mx - self.t[0]) * factor
        self.t[1] = my - (my - self.t[1]) * factor
        # Redraw
        self.redraw(False)

    def initializeData(self, referenceImg: QImage, imgToAlign: QImage, ratioWH: float,
                       referencePoints: list[tuple[float, float]], pointsToAlign: list[tuple[float, float]]) -> None:
        """
        Called by the container widget to upload data to show.
        :param: referenceImg the QImage to take as reference
        :param: imgToAlign the QImage to beg aligned
        :param: ratioWH the w/h ratio
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
            # tex.generateMipMaps()
        # Store image ratio
        self.ratioWH = ratioWH
        # Save points
        self.points = [referencePoints.copy(), pointsToAlign.copy()]
        # Redraw
        self.redraw(False)

    def updateRotation(self, rot: float) -> None:
        """
        Public method to update Rotation parameter.
        :param: rot the new value for rotation (in degrees)
        """
        self.rot = max(min(rot, 180.0), -180.0)
        self.redraw(False)

    def updateTranslation(self, tra: np.array) -> None:
        """
        Public method to update Translation parameter.
        :param: tra the new value for translation (normalized [-1.0, 1.0])
        """
        self.tra = QVector2D(tra[0], tra[1])
        self.redraw(False)

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
    Implementation of QtSimpleOpenGlShaderViewer to customize shaders and uniforms.
    """

    V_SHADER_SOURCE = """
    precision highp float;
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
    precision highp float;
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
        if (hasLeftPixel && hasRightPixel) {
            
            // Mix colors
            col = mix(lColRGBA, rColRGBA, uAlpha);
            
        } else {
            if (hasLeftPixel)  col = lColRGBA;
            if (hasRightPixel) col = rColRGBA;
        }
        
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
    Implementation of QtSimpleOpenGlShaderViewer to customize shaders and uniforms.
    """

    V_SHADER_SOURCE = """
    precision highp float;
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
    precision highp float;

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
            if (col.r <= uThr) col.rgb = 0.0;
            
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
    """

    SOFT_MARKER_W = 1
    HARD_MARKER_W = 2

    SOFT_MARKER = 0
    HARD_MARKER = 1

    MARKER_SIZE = 8
    MARKER_WIDTH = 5

    def __init__(self, identifier: int, pos: tuple[float, float], pxSizeL: float, pxSizeR: float,
                 typ: SOFT_MARKER | HARD_MARKER):
        self.identifier = identifier
        self.pxSizeL = pxSizeL
        self.pxSizeR = pxSizeR
        self.lViewPos = [pos[0], pos[1]]
        self.rViewPos = [pos[0], pos[1]]
        print(self.lViewPos, self.rViewPos)
        self.typ = typ
        self.sceneObjs = []
        self.textObjs = []
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

    def getBBox(self) -> tuple[QRectF, QRectF]:
        """
        Retrieve bbox of marker for left and right view.
        :return: (bboxL, bboxR) the two boxes
        """
        # Unpack pos
        [lmx, lmy] = [self.lViewPos[0] / self.pxSizeL, self.lViewPos[1] / self.pxSizeL]
        [rmx, rmy] = [self.rViewPos[0] / self.pxSizeR, self.rViewPos[1] / self.pxSizeR]
        # Create bbox
        side = MarkerObjData.MARKER_SIZE
        return (
            QRectF(lmx - side, lmy - side, side * 2 + 1, side * 2 + 1),
            QRectF(rmx - side, rmy - side, side * 2 + 1, side * 2 + 1),
        )

    def getLines(self) -> list[tuple[QLineF, QLineF]]:
        """
        Retrieve the lines to draw the marker inside the two views.
        :return: [(lineLeft, lineRight)] the lines list
        """
        # Unpack pos
        [lmx, lmy] = [self.lViewPos[0] / self.pxSizeL, self.lViewPos[1] / self.pxSizeL]
        [rmx, rmy] = [self.rViewPos[0] / self.pxSizeR, self.rViewPos[1] / self.pxSizeR]
        # Create line list
        side = MarkerObjData.MARKER_SIZE
        lines = [
            ([-side + 1, -side + 1], [0, 0]),  # TL - c
            ([+1, +1], [+side, +side]),  # c - BR
            ([-side + 1, +side], [0, +1]),  # BL - c
            ([1, 0], [+side, -side + 1]),  # c - TR
        ]
        # Create lines and zip them
        return [(
            QLineF(lmx + dxs, lmy + dys, lmx + dxe, lmy + dye),
            QLineF(rmx + dxs, rmy + dys, rmx + dxe, rmy + dye)
        ) for ([dxs, dys], [dxe, dye]) in lines]

    def __update(self) -> None:
        """
        Private method to keep internal data coherent.
        """
        # Update data on type
        if self.typ == MarkerObjData.SOFT_MARKER:
            self.pen.setColor(Qt.yellow)
            self.weight = MarkerObjData.SOFT_MARKER_W
        elif self.typ == MarkerObjData.HARD_MARKER:
            self.pen.setColor(Qt.red)
            self.weight = MarkerObjData.HARD_MARKER_W


class QtAlignmentToolWidget(QWidget):
    """
    A custom widget that show two images and, with the help of the user, can align the right image to the left one.
    The user needs to place some markers to declare the matches.
    This tool contains also a preview page that shows a "preview" of the results before confirming the alignment.
    """

    closed = pyqtSignal()

    def __init__(self, project, parent=None):
        super(QtAlignmentToolWidget, self).__init__(parent)

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
        self.previewSize = None
        self.R = np.rad2deg(0)
        self.T = np.array([0, 0])
        self.lastMousePos = None
        self.isDragging = False
        self.selectedMarker = None
        self.hoveringSceneObjs = None
        self.hoveringMarker = None
        self.markers: list[MarkerObjData] = []
        self.pxSizeL = 1.0
        self.pxSizeR = 1.0

        # ==============================================================
        # Top buttons
        # ==============================================================

        # Sync
        self.checkBoxSync = QCheckBox("Sync")
        self.checkBoxSync.setChecked(True)
        self.checkBoxSync.setFocusPolicy(Qt.NoFocus)
        self.checkBoxSync.setMaximumWidth(80)
        self.checkBoxSync.stateChanged[int].connect(self.toggleSync)

        # Auto Align
        self.autoAlignButton = QPushButton("Auto-Align")
        self.autoAlignButton.setFixedWidth(150)
        self.autoAlignButton.setFixedHeight(30)
        self.autoAlignButton.clicked.connect(self.onAutoAlignRequested)

        # Back to Edit
        self.backToEditButton = QPushButton("Back to Edit")
        self.backToEditButton.setFixedWidth(150)
        self.backToEditButton.setFixedHeight(30)
        self.backToEditButton.clicked.connect(self.onBackToEditRequested)

        # Show Markers
        self.checkShowMarkers = QCheckBox("Show Markers")
        self.checkShowMarkers.setChecked(True)
        self.checkShowMarkers.setFocusPolicy(Qt.NoFocus)
        self.checkShowMarkers.stateChanged[int].connect(self.toggleMarkersVisibility)

        # Confirm Alignment
        self.confirmAlignmentButton = QPushButton("Confirm")
        self.confirmAlignmentButton.setFixedWidth(100)
        self.confirmAlignmentButton.setFixedHeight(30)
        self.confirmAlignmentButton.clicked.connect(self.onConfirmAlignment)

        # Slider
        self.alphaSliderLabel = QLabel("A: " + str(self.alpha))
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
        self.xSliderLabel = QLabel("X: " + str(self.T[0]))
        self.xSliderLabel.setMinimumWidth(50)
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
        self.ySliderLabel = QLabel("Y: " + str(self.T[1]))
        self.ySliderLabel.setMinimumWidth(50)
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
        self.moveLeftButton = QPushButton("Left")
        self.moveLeftButton.setFixedWidth(100)
        self.moveLeftButton.setFixedHeight(30)
        self.moveLeftButton.clicked.connect(self.onXValueDecremented)
        self.moveRightButton = QPushButton("Right")
        self.moveRightButton.setFixedWidth(100)
        self.moveRightButton.setFixedHeight(30)
        self.moveRightButton.clicked.connect(self.onXValueIncremented)
        self.moveDownButton = QPushButton("Down")
        self.moveDownButton.setFixedWidth(100)
        self.moveDownButton.setFixedHeight(30)
        self.moveDownButton.clicked.connect(self.onYValueDecremented)
        self.moveUpButton = QPushButton("Up")
        self.moveUpButton.setFixedWidth(100)
        self.moveUpButton.setFixedHeight(30)
        self.moveUpButton.clicked.connect(self.onYValueIncremented)

        # Slider (Rot)
        self.rSliderLabel = QLabel("R: " + str(self.R / 10.0))
        self.rSliderLabel.setMinimumWidth(100)
        self.rSlider = QSlider(Qt.Horizontal)
        self.rSlider.setFocusPolicy(Qt.StrongFocus)
        self.rSlider.setMinimum(-1800)
        self.rSlider.setMaximum(1800)
        self.rSlider.setTickInterval(1)
        self.rSlider.setValue(self.R)
        self.rSlider.setMinimumWidth(50)
        self.rSlider.setAutoFillBackground(True)
        self.rSlider.valueChanged.connect(self.rotationAngleChanges)

        # Rotate Left / Right
        self.rotateLeftButton = QPushButton("Rotate Left")
        self.rotateLeftButton.setFixedWidth(200)
        self.rotateLeftButton.setFixedHeight(30)
        self.rotateLeftButton.clicked.connect(self.onRotValueIncremented)
        self.rotateRightButton = QPushButton("Rotate Right")
        self.rotateRightButton.setFixedWidth(200)
        self.rotateRightButton.setFixedHeight(30)
        self.rotateRightButton.clicked.connect(self.onRotValueDecremented)

        # Debug Slider (Threshold)
        self.thresholdSliderLabel = QLabel("T: " + str(self.threshold))
        self.thresholdSliderLabel.setMinimumWidth(50)
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
        self.buttons = QVBoxLayout()
        layout1 = QHBoxLayout()
        layout1.addWidget(self.checkBoxSync)
        layout1.setAlignment(self.checkBoxSync, Qt.AlignLeft)
        layout1.addWidget(self.backToEditButton)
        layout1.setAlignment(self.backToEditButton, Qt.AlignLeft)
        layout1.addWidget(self.autoAlignButton)
        layout1.setAlignment(self.autoAlignButton, Qt.AlignRight)
        layout1.addWidget(self.checkShowMarkers)
        layout1.addWidget(self.confirmAlignmentButton)
        layout1.setAlignment(self.confirmAlignmentButton, Qt.AlignRight)
        self.buttons.addLayout(layout1)
        layout2 = QHBoxLayout()
        layout2.addWidget(self.alphaSliderLabel)
        layout2.addWidget(self.alphaSlider)
        layout2.addWidget(self.thresholdSliderLabel)
        layout2.addWidget(self.thresholdSlider)
        self.buttons.addLayout(layout2)
        layout3 = QHBoxLayout()
        layout3.addWidget(self.xSliderLabel)
        layout3.addWidget(self.xSlider)
        layout3.addWidget(self.moveLeftButton)
        layout3.addWidget(self.moveRightButton)
        self.buttons.addLayout(layout3)
        layout4 = QHBoxLayout()
        layout4.addWidget(self.ySliderLabel)
        layout4.addWidget(self.ySlider)
        layout4.addWidget(self.moveDownButton)
        layout4.addWidget(self.moveUpButton)
        self.buttons.addLayout(layout4)
        layout5 = QHBoxLayout()
        layout5.addWidget(self.rSliderLabel)
        layout5.addWidget(self.rSlider)
        layout5.addWidget(self.rotateLeftButton)
        layout5.addWidget(self.rotateRightButton)
        self.buttons.addLayout(layout5)

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
        self.editLayout.addLayout(rightLayout)

        # ==============================================================
        # UI for preview
        # ==============================================================

        self.leftPreviewViewer = AlphaPreviewViewer()
        self.rightPreviewViewer = GrayPreviewViewer()

        self.previewLayout = QHBoxLayout()
        self.previewLayout.addWidget(self.leftPreviewViewer)
        self.previewLayout.addWidget(self.rightPreviewViewer)

        # ==============================================================
        # Initialize layouts
        # ==============================================================

        content = QVBoxLayout()
        content.addLayout(self.buttons)
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

        self.checkBoxSync.stateChanged.emit(1)

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
        self.leftPreviewViewer.setPointsVisibility(value != 0)
        self.rightPreviewViewer.setPointsVisibility(value != 0)

    @pyqtSlot()
    def onBackToEditRequested(self) -> None:
        """
        Callback called when the Preview Mode is turned on/off.
        :param: value a boolean representing if the mode is checked.
        """
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
        self.alphaSliderLabel.setText("A: " + str(value))
        # Update preview
        self.__updatePreview(onlyAlpha=True)

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
        self.xSliderLabel.setText("X: " + str(value))
        # Update preview
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
        self.ySliderLabel.setText("Y: " + str(value))
        # Update preview
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

    @pyqtSlot(int)
    def rotationAngleChanges(self, value: int) -> None:
        """
        Callback called when the value of the rotation changes.
        :param: value the new rot value
        """
        self.R = value
        self.rSliderLabel.setText("R: " + str(self.R / 10.0))
        # Update preview
        self.__updatePreview()

    @pyqtSlot(int)
    def thresholdValueChanges(self, value: int) -> None:
        """
        Callback called when the threshold value changes.
        :param: value the new threshold value
        """
        # Update threshold value and slider text
        self.threshold = value
        self.thresholdSliderLabel.setText("T: " + str(value))
        # Update preview
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
    def onAutoAlignRequested(self) -> None:
        """
        Callback called when the user request the auto alignment process to start.
        """
        # Ensure at least 3 marker is placed
        if len(self.markers) < 3:
            msgBox = QMessageBox()
            msgBox.setText("At least 3 marker is required. Use the right button to place markers.")
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
        # Save data
        # TODO
        # Close widget (?)
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
                # pxSize = self.pxSizeL if isLeft else self.pxSizeR
                # mkPos = [pos[0] * pxSize, pos[1] * pxSize]
                self.__addMarker(pos)
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
            dx = (pos[0] - self.lastMousePos[0])
            dy = (pos[1] - self.lastMousePos[1])
            self.lastMousePos = pos
            # Update marker position
            self.markers[self.selectedMarker].rViewPos[0] += dx * self.pxSizeR
            self.markers[self.selectedMarker].rViewPos[1] += dy * self.pxSizeR
            # If user is dragging marker on the left viewer
            if isLeft:
                # Update also the right one
                self.markers[self.selectedMarker].lViewPos[0] += dx * self.pxSizeL
                self.markers[self.selectedMarker].lViewPos[1] += dy * self.pxSizeL
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

    def __mapToViewer(self, pos: tuple[float, float], isLeft: bool) -> tuple[float, float]:
        """
        Private method that maps a pos [x, y] into the viewer space.
        :param: pos the position to map
        :param: isLeft a boolean to choose which viewer to use
        :return: the converted 2d vector
        """
        viewer = self.leftImgViewer if isLeft else self.rightImgViewer
        pos = viewer.clipScenePos(viewer.mapToScene(pos))
        return pos

    def __findMarkerAt(self, pos: tuple[float, float], isLeft: bool) -> Optional[int]:
        """
        Private method to find marker under [x, y].
        :param: pos the position to check
        :param: isLeft a boolean to choose which viewer to use
        :return: the index of the marker found or None
        """
        # Unpack pos
        [x, y] = pos
        # Iterate over the markers list to check if any marker exists at [x, y]
        for (i, marker) in enumerate(self.markers):
            # Find marker bbox
            (bboxL, bboxR) = self.markers[i].getBBox()
            bbox: QRectF = bboxL if isLeft else bboxR
            # Check if bbox contains pos
            if bbox.contains(x, y):
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
            self.leftImgViewer.scene.removeItem(rectL)
            self.rightImgViewer.scene.removeItem(rectR)
            self.hoveringMarker = None
            self.hoveringSceneObjs = None

    def __drawHoveringMarker(self, i: int) -> tuple[QGraphicsRectItem, QGraphicsRectItem]:
        """
        Private method to draw hovering box.
        :param: i the index of the marker to hover
        :return: the (leftRect, rightRect) created
        """
        # Create drawing pen
        pen = QPen(Qt.white, 1)
        pen.setCosmetic(True)
        # Retrieve bbox
        (bboxL, bboxR) = self.markers[i].getBBox()
        # Draw rects
        rectL = self.leftImgViewer.scene.addRect(bboxL, pen)
        rectR = self.rightImgViewer.scene.addRect(bboxR, pen)
        rectL.setZValue(6)
        rectR.setZValue(6)
        return rectL, rectR

    def __deleteAllMarkers(self) -> None:
        """
        Private method to remove all the markers.
        """
        for i in range(0, len(self.markers)):
            self.__clearMarker(i, False)
        self.markers = []

    def __deleteMarker(self, i: int) -> None:
        """
        Private method to remove a marker from the markers list.
        :param: i the index of the marker
        """
        self.__clearMarker(i, False)
        self.markers = self.markers[:i] + self.markers[i + 1:]

    def __clearMarker(self, i: int, onlyText: bool) -> None:
        """
        Private method to clear marker scene objs.
        :param: i the index of the marker to clear.
        :param: onlyText is a boolean that specifies to only clear text items.
        """
        # Remove items from scene
        for [objL, objR] in self.markers[i].textObjs:
            self.leftImgViewer.scene.removeItem(objL)
            self.leftImgViewer.scene.removeItem(objR)
        # Clear array
        self.markers[i].textObjs = []
        if not onlyText:
            # Remove items from scene
            for [objL, objR] in self.markers[i].sceneObjs:
                self.leftImgViewer.scene.removeItem(objL)
                self.leftImgViewer.scene.removeItem(objR)
            # Clear array
            self.markers[i].sceneObjs = []

    def __addMarker(self, pos: tuple[float, float]) -> None:
        """
        Private method to add a marker at pos [x, y].
        :param: pos the position where to add the marker
        """
        # Find next available ID
        identifier = max(self.markers, key=lambda x: x.identifier).identifier + 1 if len(self.markers) > 0 else 1
        # Create a marker obj
        self.markers.append(MarkerObjData(identifier, pos, self.pxSizeL, self.pxSizeR, MarkerObjData.SOFT_MARKER))

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
                lineL = self.leftImgViewer.scene.addLine(leftLine, marker.pen)
                lineR = self.rightImgViewer.scene.addLine(rightLine, marker.pen)
                lineL.setZValue(5)
                lineR.setZValue(5)
                sceneObjs.append([lineL, lineR])
            # Update list
            marker.sceneObjs = sceneObjs
        # Redraw only if needed
        if len(marker.textObjs) == 0:
            # Draw labels
            textObjs = []
            color = marker.pen.color().name()
            lErrorLabelVisibility = (self.leftImgViewer.zoom_factor > 3.25)
            rErrorLabelVisibility = (self.rightImgViewer.zoom_factor > 3.25)
            # Left identifier
            textL = QGraphicsTextItem()
            textL.setHtml(
                '<div style="background:' + color + ';">' + str(marker.identifier) + '</p>')
            textL.setFont(QFont("Roboto", 12, QFont.Bold))
            textL.setOpacity(0.75)
            textL.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            textL.setDefaultTextColor(Qt.black)
            textL.setZValue(8)
            # Right identifier
            textR = QGraphicsTextItem()
            textR.setHtml('<div style="background:' + color + ';">' + str(marker.identifier) + '</p>')
            textR.setFont(QFont("Roboto", 12, QFont.Bold))
            textR.setOpacity(0.75)
            textR.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            textR.setDefaultTextColor(Qt.black)
            textR.setZValue(8)
            # Left error
            errL = QGraphicsTextItem()
            errL.setHtml('<div style="background:' + color + ';">' + str(marker.error) + '</p>')
            errL.setFont(QFont("Roboto", 12, QFont.Bold))
            errL.setOpacity(0.5)
            errL.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            errL.setDefaultTextColor(Qt.black)
            errL.setZValue(7)
            errL.setVisible(lErrorLabelVisibility)
            # Right error
            errR = QGraphicsTextItem()
            errR.setHtml('<div style="background:' + color + ';">' + str(marker.error) + '</p>')
            errR.setFont(QFont("Roboto", 12, QFont.Bold))
            errR.setOpacity(0.5)
            errR.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            errR.setDefaultTextColor(Qt.black)
            errR.setZValue(7)
            errR.setVisible(rErrorLabelVisibility)
            # Update text pos
            (bboxL, bboxR) = marker.getBBox()
            textL.setPos(bboxL.topRight())
            textR.setPos(bboxR.topRight())
            errL.setPos(bboxL.topLeft())
            errR.setPos(bboxR.topLeft())
            # Add text to scenes
            self.leftImgViewer.scene.addItem(textL)
            self.rightImgViewer.scene.addItem(textR)
            self.leftImgViewer.scene.addItem(errL)
            self.rightImgViewer.scene.addItem(errR)
            textObjs.append([textL, textR])
            textObjs.append([errL, errR])
            # Update list
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
        self.__updatePreviewSize(channel1.qimage, self.pxSizeL, channel2.qimage, self.pxSizeR)
        # Update viewer
        self.leftImgViewer.setImg(self.__padImage(channel1.qimage, self.pxSizeL))
        self.leftImgViewer.px_to_mm = self.pxSizeL
        self.rightImgViewer.setImg(self.__padImage(channel2.qimage, self.pxSizeR))
        self.rightImgViewer.px_to_mm = self.pxSizeR
        # Update overlay images
        self.__deleteAllMarkers()
        self.__updateMarkers(keepAlgResults=False)
        # Clear data of last comparison
        self.alphaSlider.setValue(50)
        self.thresholdSlider.setValue(32)
        self.rSlider.setValue(0)
        self.xSlider.setValue(0)
        self.ySlider.setValue(0)

    def __padImage(self, img: QImage, pxSize: float) -> QImage:
        """
        Private method to create a padded image of size self.previewSize
        :param: img the image to pad
        :param: pxSize the px_to_mm of the img
        :return: a new image with [0, 0, 0, 0] as padding (right and bottom)
        """
        return self.__toQImage(self.__toNumpyArray(img, pxSize), QImage.Format_RGBA8888)

    def __toNumpyArray(self, img: QImage, pxSize: float) -> np.ndarray:
        """
        Private method to create a numpy array from QImage.
        :param: img contains the QImage to transform
        :param: pxSize the px_to_mm of the img
        :return: an numpy array of shape (h, w, channels)
        """
        # Retrieve and convert image into selected format
        img = img.convertToFormat(QImage.Format_RGBA8888)
        h, w = img.height(), img.width()
        # Retrieve a pointer to the modifiable memory view of the image
        ptr = img.bits()
        # Update pointer size
        ptr.setsize(h * w * 4)
        # Create numpy array
        arr = np.frombuffer(ptr, np.uint8).reshape((h, w, 4))
        # Pad img
        [rh, rw] = [self.previewSize[0] / pxSize, self.previewSize[1] / pxSize]
        [ph, pw] = [int(rh - h), int(rw - w)]
        arr = np.pad(arr, [(0, ph), (0, pw), (0, 0)], mode='constant', constant_values=0)
        return arr

    def __toQImage(self, arr: np.ndarray, imgFormat: int) -> QImage:
        """
        Private method to transform a numpy array into a QImage.
        :param: arr is the numpy array of shape (h, w, c)
        :param: imgFormat is the format of the image to create
        :return: the QImage
        """
        # Retrieve the shape
        [h, w, c] = arr.shape
        # Create and return the image
        return QImage(arr.data, w, h, c * w, imgFormat)

    def __updatePreviewSize(self, img1: QImage, pxSize1: float, img2: QImage, pxSize2: float) -> None:
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
        h2, w2 = img2.height() * pxSize2, img2.width() * pxSize2
        # Find box containing both images
        ph, pw = max(h1, h2), max(w1, w2)
        # Update preview size
        self.previewSize = [ph, pw]
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
        # Retrieve ratio
        [h, w] = self.previewSize
        ratioWH = w / h
        # Retrieve markers
        [ph, pw] = self.previewSize
        q = [[(marker.lViewPos[0] / pw) * 2 - 1.0, (marker.lViewPos[1] / ph) * -2 + 1.0] for marker in self.markers]
        p = [[(marker.rViewPos[0] / pw) * 2 - 1.0, (marker.rViewPos[1] / ph) * -2 + 1.0] for marker in self.markers]
        # Pass images to viewers
        self.leftPreviewViewer.initializeData(img1, img2, ratioWH, q, p)
        self.rightPreviewViewer.initializeData(img1, img2, ratioWH, q, p)

    def __updatePreview(self, onlyAlpha: bool = False) -> None:
        """
        Private method to update the preview.
        :param: onlyAlpha is a boolean that represents whether the changes are only on the alpha.
        """
        # Update alpha value
        self.leftPreviewViewer.updateAlpha(self.alpha / 100.0)
        if not onlyAlpha:
            # Update R and T values
            tra = (self.T * 2.0) / self.previewSize
            rot = self.R / 10.0
            self.leftPreviewViewer.updateRotation(rot)
            self.leftPreviewViewer.updateTranslation(tra)
            self.rightPreviewViewer.updateRotation(rot)
            self.rightPreviewViewer.updateTranslation(tra)
            # Update threshold
            self.rightPreviewViewer.updateThreshold(self.threshold)

    def __togglePreviewMode(self, isPreviewMode: bool) -> None:
        """
        Private method to set widget visibility to toggle the Preview Mode on/off.
        :param: isPreviewMode a boolean value to enable / disable the Preview Mode
        """
        # (Preview-ONLY) widgets
        self.leftPreviewViewer.setVisible(isPreviewMode)
        self.rightPreviewViewer.setVisible(isPreviewMode)
        self.backToEditButton.setVisible(isPreviewMode)
        self.checkShowMarkers.setVisible(isPreviewMode)
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
        # (NON-Preview-ONLY) widgets
        self.leftImgViewer.setVisible(not isPreviewMode)
        self.rightImgViewer.setVisible(not isPreviewMode)
        self.checkBoxSync.setVisible(not isPreviewMode)
        self.autoAlignButton.setVisible(not isPreviewMode)
        self.leftComboboxLabel.setVisible(not isPreviewMode)
        self.leftCombobox.setVisible(not isPreviewMode)
        self.rightComboboxLabel.setVisible(not isPreviewMode)
        self.rightCombobox.setVisible(not isPreviewMode)

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
        # Reset each marker error
        for (i, marker) in enumerate(self.markers):
            marker.error = None
            self.__clearMarker(i, True)

        # print("__leastSquaresWithSVD called")

        # Ensure at least 3 marker are placed
        if len(self.markers) < 3:
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
        [ph, pw] = self.previewSize
        q = [[(marker.lViewPos[0] - pw / 2), -(marker.lViewPos[1] - ph / 2)] for marker in self.markers]
        p = [[(marker.rViewPos[0] - pw / 2), -(marker.rViewPos[1] - ph / 2)] for marker in self.markers]

        # ==================================================================================
        # [1] Compute the weighted centroids _q (for q) and _p (for p)
        # ==================================================================================
        _p = [0, 0]
        _q = [0, 0]
        for i in range(0, n):
            f = w[i] / sw
            _p[0] += (p[i][0] * f)
            _p[1] += (p[i][1] * f)
            _q[0] += (q[i][0] * f)
            _q[1] += (q[i][1] * f)

        # ==================================================================================
        # [2] Compute the centered vectors y (for q) and x (for p)
        # ==================================================================================
        y = [[qi[0] - _q[0], qi[1] - _q[1]] for qi in q]
        x = [[pi[0] - _p[0], pi[1] - _p[1]] for pi in p]

        # ==================================================================================
        # [3] Compute the covariance matrix S (dxd)
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
        S = X @ W @ Yt

        # ==================================================================================
        # [4] Compute SVD & Find rotation
        # ==================================================================================
        u, s, vt = np.linalg.svd(S)
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
        sol = [(R @ pi + T) for pi in p]
        sol = [[s[0, 0], s[0, 1]] for s in sol]

        # Compute errors
        err = [[a[0] - b[0], a[1] - b[1]] for (a, b) in zip(sol, q)]
        err = [math.sqrt(x ** 2 + y ** 2) for (x, y) in err]
        for (i, (e, marker)) in enumerate(zip(err, self.markers)):
            # TODO pixel -> mm
            marker.error = round(e, 2)

        T = [T[0, 0], T[0, 1]]
        self.T = np.array(T)
        self.xSlider.setValue(T[0])
        self.ySlider.setValue(T[1])

        R = np.rad2deg(math.acos(round(R[0, 0], 4)))
        self.R = R * 10.0
        self.rSlider.setValue(R)
