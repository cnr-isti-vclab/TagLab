import math
from typing import Optional

import numpy as np
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot, QLineF, QRectF, QPoint
from PyQt5.QtGui import QImage, QMouseEvent, QPen, QFont, QCloseEvent, QKeyEvent, QOpenGLShaderProgram, QOpenGLShader, \
    QOpenGLVersionProfile, QMatrix4x4, QWheelEvent, QOpenGLTexture, QVector2D
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

    def __init__(self, vSrc, fSrc, parent=None):
        super(QtSimpleOpenGlShaderViewer, self).__init__(parent)
        # Open GL
        self.gl: Optional[QOpenGLFunctions_2_0] = None
        self.program: Optional[QOpenGLShaderProgram] = None
        self.textures: list[QOpenGLTexture] = []
        self.vertPos = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        self.vertTex = [(0, 1), (0, 0), (1, 1), (1, 0)]
        self.vSrc = vSrc
        self.fSrc = fSrc
        # Transformation status
        self.t = [0.0, 0.0]
        self.s = 1.0
        self.w = 100
        self.h = 100
        # Gesture
        self.lastPos = None

    def initializeGL(self) -> None:
        """
        Sets up the OpenGL resources and state.
        Gets called once before the first time resizeGL() or paintGL() is called.
        """
        # Load openg from requested profile
        profile = QOpenGLVersionProfile()
        profile.setVersion(2, 0)
        self.gl = self.context().versionFunctions(versionProfile=profile)
        self.gl.initializeOpenGLFunctions()
        # Create shaders
        vshader = QOpenGLShader(QOpenGLShader.Vertex, self)
        fshader = QOpenGLShader(QOpenGLShader.Fragment, self)
        checkGL(vshader, vshader.compileSourceCode(self.vSrc))
        checkGL(fshader, fshader.compileSourceCode(self.fSrc))
        # Create & Compile program
        self.program = QOpenGLShaderProgram()
        checkGL(self.program, self.program.addShader(vshader))
        checkGL(self.program, self.program.addShader(fshader))
        self.program.bindAttributeLocation('aPos', 0)
        self.program.bindAttributeLocation('aTex', 1)
        checkGL(self.program, self.program.link())
        # Bind program
        checkGL(self.program, self.program.bind())
        # Position array
        self.program.enableAttributeArray(0)
        self.program.setAttributeArray(0, self.vertPos)
        # Texture array
        self.program.enableAttributeArray(1)
        self.program.setAttributeArray(1, self.vertTex)
        # Constant uniforms
        self.program.setUniformValue('uTexL', 0)
        self.program.setUniformValue('uTexR', 1)

    def paintGL(self) -> None:
        """
        Renders the OpenGL scene.
        Gets called whenever the widget needs to be updated.
        """
        # Create TRS matrix
        matrix = QMatrix4x4()
        matrix.translate(self.t[0], self.t[1], 0)
        matrix.scale(self.s, self.s, 1)
        # Clear
        self.gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        self.gl.glClear(self.gl.GL_COLOR_BUFFER_BIT)
        # Update uniforms
        self.program.setUniformValue("uMatrix", matrix)
        # Textures MUST be loaded by the time paint is called
        self.textures[0].bind(0)
        self.textures[1].bind(1)
        # Draw quad
        self.gl.glDrawArrays(self.gl.GL_TRIANGLE_STRIP, 0, 4)

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
        # Update quad to always fitCenter
        side = min(w, h)
        self.vertPos = [(-side / w, -side / h), (-side / w, side / h), (side / w, -side / h), (side / w, side / h)]
        # Upload new array
        self.program.setAttributeArray(0, self.vertPos)

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
        self.t[0] += dx
        self.t[1] -= dy
        # Redraw
        self.update()

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
        self.s += event.angleDelta().y() / 180
        self.s = min(max(self.s, 0.75), 16.0)
        factor = self.s / lastScale
        # Find normalized mouse pos
        [mx, my] = [event.pos().x() / (self.w // 2) - 1, event.pos().y() / (self.h // 2) - 1]
        # Zoom towards mouse pos
        self.t[0] = (mx - (mx - self.t[0]) * factor)
        self.t[1] = (my - (my + self.t[1]) * factor) * -1
        # Redraw
        self.update()

    def setImages(self, referenceImg: QImage, imgToAlign: QImage) -> None:
        """
        Called by the container widget to set the images to compare.
        :param: referenceImg the QImage to take as reference
        :param: imgToAlign the QImage to beg aligned
        """
        # Release old textures
        for tex in self.textures:
            tex.release()
        # Create textures
        self.textures = [
            QOpenGLTexture(referenceImg),
            QOpenGLTexture(imgToAlign)
        ]
        # Update texture parameters
        for tex in self.textures:
            tex.setMinMagFilters(QOpenGLTexture.Nearest, QOpenGLTexture.Nearest)
            # tex.generateMipMaps()


class AlphaPreviewViewer(QtSimpleOpenGlShaderViewer):
    """
    Implementation of QtSimpleOpenGlShaderViewer to customize shaders and uniforms.
    """

    V_SHADER_SOURCE = """
    precision highp float;
    attribute vec2 aPos;
    attribute vec2 aTex;
    uniform mat4 uMatrix;
    varying vec2 vTex;
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
    uniform float uRot;
    uniform vec2 uTra;
    void main(void) {
        vec2 lTex = vec2(vTex.x / (1 - uTra.x), vTex.y / (1 - uTra.y));
        vec2 rTex = vec2((vTex.x - uTra.x) / (1 - uTra.x), (vTex.y - uTra.y) / (1 - uTra.y));
    
        vec4 lColRGBA = texture2D(uTexL, lTex);
        vec4 rColRGBA = texture2D(uTexR, rTex);

        bool isInB = (vTex.x >= uTra.x && vTex.y >= uTra.y);
        bool isInA = (vTex.x <= (1-uTra.x) && vTex.y <= (1-uTra.y));
        
        // .______________.
        // |AAAAAAAAAA    |  A is the "Reference Image"
        // |AAAAAAAAAA    |  B is the "Image to Align"
        // |AAAAAA####BBBB|  # is where the two images overlap
        // |AAAAAA####BBBB|
        // |      BBBBBBBB|
        // |      BBBBBBBB|
        // |______________|
        
        if (isInA && isInB) {
            float alpha = uAlpha;
            if (lColRGBA.r == 0.0 && lColRGBA.g == 0.0 && lColRGBA.b == 0.0 && lColRGBA.a == 0.0) alpha = 1.0;
            if (rColRGBA.r == 0.0 && rColRGBA.g == 0.0 && rColRGBA.b == 0.0 && rColRGBA.a == 0.0) alpha = 0.0;
            gl_FragColor = mix(lColRGBA, rColRGBA, alpha);
        } else {
            vec4 col = (isInA) ? lColRGBA : (isInB) ? rColRGBA : vec4(0, 0, 0, 1);
            gl_FragColor = col;
        }
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
        self.rot = 0
        self.tra = QVector2D(0, 0)

    def paintGL(self) -> None:
        """
        Override to update uniforms before painting
        """
        # Update uniforms
        self.program.setUniformValue("uAlpha", self.alpha)
        self.program.setUniformValue("uRot", self.rot)
        self.program.setUniformValue("uTra", self.tra)
        # Forward
        super(AlphaPreviewViewer, self).paintGL()

    def updateAlpha(self, alpha: float) -> None:
        """
        Public method to update Alpha parameter.
        :param: alpha the new value for alpha [0.0, 1.0]
        """
        self.alpha = max(min(alpha, 1.0), 0.0)
        self.update()

    def updateRotation(self, rot: float) -> None:
        """
        Public method to update Rotation parameter.
        :param: rot the new value for rotation (in degrees)
        """
        self.rot = np.deg2rad(max(min(rot, 180.0), -180.0))
        self.update()

    def updateTranslation(self, tra: np.array) -> None:
        """
        Public method to update Translation parameter.
        :param: tra the new value for translation (normalized [0.0, 1.0])
        """
        self.tra = QVector2D(tra[0], tra[1])
        self.update()


class GrayPreviewViewer(QtSimpleOpenGlShaderViewer):
    """
    Implementation of QtSimpleOpenGlShaderViewer to customize shaders and uniforms.
    """

    V_SHADER_SOURCE = """
    precision highp float;
    attribute vec2 aPos;
    attribute vec2 aTex;
    uniform mat4 uMatrix;
    varying vec2 vTex;
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
    uniform float uRot;
    uniform vec2 uTra;
    uniform float uThr;
    void main(void) {
        vec2 lTex = vec2(vTex.x / (1 - uTra.x), vTex.y / (1 - uTra.y));
        vec2 rTex = vec2((vTex.x - uTra.x) / (1 - uTra.x), (vTex.y - uTra.y) / (1 - uTra.y));
    
        vec4 lColRGBA = texture2D(uTexL, lTex);
        vec4 rColRGBA = texture2D(uTexR, rTex);
        
        float lGray = dot(vec3(0.2126, 0.7152, 0.0722), lColRGBA.rgb);
        float rGray = dot(vec3(0.2126, 0.7152, 0.0722), rColRGBA.rgb);
        
        bool isInB = (vTex.x >= uTra.x && vTex.y >= uTra.y);
        bool isInA = (vTex.x <= (1-uTra.x) && vTex.y <= (1-uTra.y));
        
        // .______________.
        // |AAAAAAAAAA    |  A is the "Reference Image"
        // |AAAAAAAAAA    |  B is the "Image to Align"
        // |AAAAAA####BBBB|  # is where the two images overlap
        // |AAAAAA####BBBB|
        // |      BBBBBBBB|
        // |      BBBBBBBB|
        // |______________|
        
        if (isInA && isInB) {
            float col = abs(lGray - rGray);
            if (col <= uThr) col = 0.0;
            gl_FragColor = vec4(col, col, col, 1);
        } else {
            float col = (isInA) ? lGray : (isInB) ? rGray : 0;
            gl_FragColor = vec4(col, col, col, 1);
        }
    }
    """

    def __init__(self, parent=None):
        super(GrayPreviewViewer, self).__init__(
            GrayPreviewViewer.V_SHADER_SOURCE,
            GrayPreviewViewer.F_SHADER_SOURCE,
            parent
        )
        # Custom parameters
        self.rot = 0.0
        self.tra = QVector2D(0.0, 0.0)
        self.thr = 0.0

    def paintGL(self) -> None:
        """
        Override to update uniforms before painting
        """
        # Update uniforms
        self.program.setUniformValue("uRot", self.rot)
        self.program.setUniformValue("uTra", self.tra)
        self.program.setUniformValue("uThr", self.thr)
        # Forward
        super(GrayPreviewViewer, self).paintGL()

    def updateRotation(self, rot: float) -> None:
        """
        Public method to update Rotation parameter.
        :param: rot the new value for rotation (in degrees)
        """
        self.rot = np.deg2rad(max(min(rot, 180.0), -180.0))
        self.update()

    def updateTranslation(self, tra: np.array) -> None:
        """
        Public method to update Translation parameter.
        :param: tra the new value for translation (normalized [0.0, 1.0])
        """
        self.tra = QVector2D(tra[0], tra[1])
        self.update()

    def updateThreshold(self, thr: int) -> None:
        """
        Public method to update Threshold parameter.
        :param: thr the new value for threshold [0, 255]
        """
        self.thr = min(max(thr / 255.0, 0.0), 1.0)
        self.update()


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

    def __init__(self, identifier: int, pos: [int], typ: SOFT_MARKER | HARD_MARKER):
        self.identifier = identifier
        self.lViewPos = [pos[0], pos[1]]
        self.rViewPos = [pos[0], pos[1]]
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
        [lmx, lmy] = self.lViewPos
        [rmx, rmy] = self.rViewPos
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
        [lmx, lmy] = self.lViewPos
        [rmx, rmy] = self.rViewPos
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

        # ==============================================================
        # Top buttons
        # ==============================================================

        # Sync
        self.checkBoxSync = QCheckBox("Sync")
        self.checkBoxSync.setChecked(True)
        self.checkBoxSync.setFocusPolicy(Qt.NoFocus)
        self.checkBoxSync.setMaximumWidth(80)
        self.checkBoxSync.stateChanged[int].connect(self.toggleSync)

        # Preview
        self.checkBoxPreview = QCheckBox("Preview")
        self.checkBoxPreview.setChecked(False)
        self.checkBoxPreview.setFocusPolicy(Qt.NoFocus)
        self.checkBoxSync.setMaximumWidth(80)
        self.checkBoxPreview.stateChanged[int].connect(self.togglePreview)

        # Auto Align
        self.autoAlignButton = QPushButton("Auto-Align")
        self.autoAlignButton.setFixedWidth(150)
        self.autoAlignButton.setFixedHeight(30)
        self.autoAlignButton.clicked.connect(self.onAutoAlignRequested)

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
        self.xSlider.setMinimum(0)
        self.xSlider.setMaximum(256)
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
        self.ySlider.setMinimum(0)
        self.ySlider.setMaximum(256)
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
        self.moveUpButton = QPushButton("Up")
        self.moveUpButton.setFixedWidth(100)
        self.moveUpButton.setFixedHeight(30)
        self.moveUpButton.clicked.connect(self.onYValueDecremented)
        self.moveDownButton = QPushButton("Down")
        self.moveDownButton.setFixedWidth(100)
        self.moveDownButton.setFixedHeight(30)
        self.moveDownButton.clicked.connect(self.onYValueIncremented)

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
        self.rotateLeftButton.clicked.connect(self.onRotValueDecremented)
        self.rotateRightButton = QPushButton("Rotate Right")
        self.rotateRightButton.setFixedWidth(200)
        self.rotateRightButton.setFixedHeight(30)
        self.rotateRightButton.clicked.connect(self.onRotValueIncremented)

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
        layout1.addWidget(self.checkBoxPreview)
        layout1.addWidget(self.autoAlignButton)
        layout1.addWidget(self.confirmAlignmentButton)
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
        layout4.addWidget(self.moveUpButton)
        layout4.addWidget(self.moveDownButton)
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
        self.checkBoxPreview.stateChanged.emit(0)

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
                self.__updateMarkers()
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

    @pyqtSlot(int)
    def toggleSync(self, value: int) -> None:
        """
        Callback called when the sync mode is turned on/off.
        :param: value a boolean to enable/disable the sync mode.
        """
        # If Enabled
        if value:
            # Share each action with the other widget
            self.leftImgViewer.viewHasChanged[float, float, float].connect(self.rightImgViewer.setViewParameters)
            self.rightImgViewer.viewHasChanged[float, float, float].connect(self.leftImgViewer.setViewParameters)
        else:
            # Disconnect the two widgets
            self.leftImgViewer.viewHasChanged[float, float, float].disconnect()
            self.rightImgViewer.viewHasChanged[float, float, float].disconnect()

    @pyqtSlot(int)
    def togglePreview(self, value: int) -> None:
        """
        Callback called when the Preview Mode is turned on/off.
        :param: value a boolean representing if the mode is checked.
        """
        # Hide / Show widgets
        self.__togglePreviewMode(value != 0)
        # If preview is set
        if value:
            # Initialize and update the view
            self.__initializePreview()
            self.__updatePreview()

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
        self.checkBoxPreview.setChecked(True)

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
        self.__updateMarkers()

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
        self.__updateMarkers()

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
            self.markers[self.selectedMarker].rViewPos[0] += dx
            self.markers[self.selectedMarker].rViewPos[1] += dy
            # If user is dragging marker on the left viewer
            if isLeft:
                # Update also the right one
                self.markers[self.selectedMarker].lViewPos[0] += dx
                self.markers[self.selectedMarker].lViewPos[1] += dy
            self.__clearMarker(self.selectedMarker, False)
            # Redraw markers
            self.__updateMarkers()
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
                self.__updateMarkers()

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
        self.__updateMarkers()

    def __mapToViewer(self, pos: [int], isLeft: bool) -> [int]:
        """
        Private method that maps a pos [x, y] into the viewer space.
        :param: pos the position to map
        :param: isLeft a boolean to choose which viewer to use
        :return: the converted 2d vector
        """
        viewer = self.leftImgViewer if isLeft else self.rightImgViewer
        return viewer.clipScenePos(viewer.mapToScene(pos))

    def __findMarkerAt(self, pos: [int], isLeft: bool) -> Optional[int]:
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
        :param: onlyText is a boolean that specifies to only clear textObjs.
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

    def __addMarker(self, pos: [int]) -> None:
        """
        Private method to add a marker at pos [x, y].
        :param: pos the position where to add the marker
        """
        # Find next available ID
        identifier = max(self.markers, key=lambda x: x.identifier).identifier + 1 if len(self.markers) > 0 else 1
        # Create a marker obj
        self.markers.append(MarkerObjData(identifier, pos, MarkerObjData.SOFT_MARKER))

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
            # Left identifier
            textL = QGraphicsTextItem()
            textL.setHtml(
                '<div style="background:' + marker.pen.color().name() + ';">' + str(marker.identifier) + '</p>')
            textL.setFont(QFont("Roboto", 12, QFont.Bold))
            textL.setOpacity(0.75)
            textL.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            textL.setDefaultTextColor(Qt.black)
            textL.setZValue(8)
            # Right identifier
            textR = QGraphicsTextItem()
            textR.setHtml(
                '<div style="background:' + marker.pen.color().name() + ';">' + str(marker.identifier) + '</p>')
            textR.setFont(QFont("Roboto", 12, QFont.Bold))
            textR.setOpacity(0.75)
            textR.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            textR.setDefaultTextColor(Qt.black)
            textR.setZValue(8)
            # Left error
            errL = QGraphicsTextItem()
            errL.setHtml('<div style="background:' + marker.pen.color().name() + ';">' + str(marker.error) + '</p>')
            errL.setFont(QFont("Roboto", 12, QFont.Bold))
            errL.setOpacity(0.5)
            errL.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            errL.setDefaultTextColor(Qt.black)
            errL.setZValue(7)
            # Right error
            errR = QGraphicsTextItem()
            errR.setHtml('<div style="background:' + marker.pen.color().name() + ';">' + str(marker.error) + '</p>')
            errR.setFont(QFont("Roboto", 12, QFont.Bold))
            errR.setOpacity(0.5)
            errR.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            errR.setDefaultTextColor(Qt.black)
            errR.setZValue(7)
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

    def __updateMarkers(self) -> None:
        """
        Private method to redraw markers.
        """
        # Try pre-computing the align algorithm
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
        pxSize1 = self.project.images[index1].pixelSize()
        pxSize2 = self.project.images[index2].pixelSize()
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
        self.__updatePreviewSize(channel1.qimage, pxSize1, channel2.qimage, pxSize2)
        # Update viewer
        self.leftImgViewer.setImg(self.__padImage(channel1.qimage, pxSize1))
        self.leftImgViewer.px_to_mm = pxSize1
        self.rightImgViewer.setImg(self.__padImage(channel2.qimage, pxSize2))
        self.rightImgViewer.px_to_mm = pxSize2
        # Update overlay images
        self.__deleteAllMarkers()
        self.__updateMarkers()
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
        self.xSlider.setMaximum(pw // 2)
        self.ySlider.setMaximum(ph // 2)

    def __initializePreview(self) -> None:
        """
        Private method called to initialize the preview.
        """
        # Retrieve images
        img1 = self.leftImgViewer.img_map
        img2 = self.rightImgViewer.img_map
        # Pass images to viewers
        self.leftPreviewViewer.setImages(img1, img2)
        self.rightPreviewViewer.setImages(img1, img2)

    def __updatePreview(self, onlyAlpha: bool = False) -> None:
        """
        Private method to update the preview.
        :param: onlyAlpha is a boolean that represents whether the changes are only on the alpha.
        """
        # Update alpha value
        self.leftPreviewViewer.updateAlpha(self.alpha / 100.0)
        if not onlyAlpha:
            # Update R and T values
            self.leftPreviewViewer.updateRotation(self.R / 10.0)
            self.leftPreviewViewer.updateTranslation(self.T / self.previewSize)
            self.rightPreviewViewer.updateRotation(self.R / 10.0)
            self.rightPreviewViewer.updateTranslation(self.T / self.previewSize)
            self.rightPreviewViewer.updateThreshold(self.threshold)

    def __togglePreviewMode(self, isPreviewMode: bool) -> None:
        """
        Private method to set widget visibility to toggle the Preview Mode on/off.
        :param: isPreviewMode a boolean value to enable / disable the Preview Mode
        """
        # (Preview-ONLY) widgets
        self.leftPreviewViewer.setVisible(isPreviewMode)
        self.rightPreviewViewer.setVisible(isPreviewMode)
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
        q = [marker.lViewPos for marker in self.markers]
        p = [marker.rViewPos for marker in self.markers]

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

        # Save results

        T = [T[0, 0], T[0, 1]]
        self.T = np.array(T)
        self.xSlider.setValue(T[0])
        self.ySlider.setValue(T[1])

        # R = [[R[0, 0], R[0, 1]],
        #       R[1, 0], R[1, 1]]
        R = np.rad2deg(math.acos(round(R[0, 0], 4)))
        self.R = R
