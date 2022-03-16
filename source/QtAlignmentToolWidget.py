from typing import Optional

import cv2
import numpy
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot, QLineF, QRectF
from PyQt5.QtGui import QImage, QMouseEvent, QPen, QFont, QCloseEvent, QKeyEvent
from PyQt5.QtWidgets import QWidget, QSizePolicy, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QSlider, QApplication, \
    QCheckBox, QPushButton, QMessageBox, QGraphicsTextItem, QGraphicsItem, QOpenGLWidget, QGraphicsRectItem

from source.QtImageViewer import QtImageViewer


class QtSimpleOpenGlShaderViewer(QOpenGLWidget):
    """
    Custom widget to handle img preview with shaders.
    """

    def __init__(self, parent=None):
        super(QtSimpleOpenGlShaderViewer, self).__init__(parent)

    def paintGL(self) -> None:
        pass

    def resizeGL(self, w: int, h: int) -> None:
        pass

    def initializeGL(self) -> None:
        pass


class MarkerObjData:
    """
    Marker data class.
    """

    SOFT_MARKER_W = 1
    HARD_MARKER_W = 1

    SOFT_MARKER = 0
    HARD_MARKER = 1

    MARKER_SIZE = 8
    MARKER_WIDTH = 5

    def __init__(self, identifier: int, pos: [], typ: SOFT_MARKER | HARD_MARKER, objs: [QGraphicsItem]):
        self.id = identifier
        self.lViewPos = [pos[0], pos[1]]
        self.rViewPos = [pos[0], pos[1]]
        self.typ = typ
        self.objs = objs
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

    def getBBox(self) -> (QRectF, QRectF):
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

    def getLines(self) -> [(QLineF, QLineF)]:
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
        return zip(
            [QLineF(lmx + dxs, lmy + dys, lmx + dxe, lmy + dye) for ([dxs, dys], [dxe, dye]) in lines],
            [QLineF(rmx + dxs, rmy + dys, rmx + dxe, rmy + dye) for ([dxs, dys], [dxe, dye]) in lines],
        )

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
        self.rotation = numpy.identity(2)
        self.offset = [0, 0]
        self.lastMousePos = None
        self.isDragging = False
        self.selectedMarker = None
        self.hoveringSceneObjs = None
        self.hoveringMarker = None
        self.markers: [MarkerObjData] = []

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
        self.alphaSlider.setMaximumWidth(200)
        self.alphaSlider.setAutoFillBackground(True)
        self.alphaSlider.valueChanged.connect(self.previewAlphaValueChanges)

        # Manual offset
        self.xSliderLabel = QLabel("X: " + str(self.offset[0]))
        self.xSliderLabel.setMinimumWidth(50)
        self.ySliderLabel = QLabel("Y: " + str(self.offset[1]))
        self.ySliderLabel.setMinimumWidth(50)

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

        # Debug Slider (X)
        self.xSlider = QSlider(Qt.Horizontal)
        self.xSlider.setFocusPolicy(Qt.StrongFocus)
        self.xSlider.setMinimum(0)
        self.xSlider.setMaximum(256)
        self.xSlider.setTickInterval(1)
        self.xSlider.setValue(self.offset[0])
        self.xSlider.setMinimumWidth(50)
        self.xSlider.setAutoFillBackground(True)
        self.xSlider.valueChanged.connect(self.xOffsetChanges)

        # Debug Slider (Y)
        self.ySlider = QSlider(Qt.Horizontal)
        self.ySlider.setFocusPolicy(Qt.StrongFocus)
        self.ySlider.setMinimum(0)
        self.ySlider.setMaximum(256)
        self.ySlider.setTickInterval(1)
        self.ySlider.setValue(self.offset[1])
        self.ySlider.setMinimumWidth(50)
        self.ySlider.setAutoFillBackground(True)
        self.ySlider.valueChanged.connect(self.yOffsetChanges)

        # Debug Slider (Threshold)
        self.thresholdSliderLabel = QLabel("T: " + str(self.threshold))
        self.thresholdSliderLabel.setMinimumWidth(50)
        self.thresholdSlider = QSlider(Qt.Horizontal)
        self.thresholdSlider.setFocusPolicy(Qt.StrongFocus)
        self.thresholdSlider.setMinimum(0)
        self.thresholdSlider.setMaximum(256)
        self.thresholdSlider.setValue(64)
        self.thresholdSlider.setTickInterval(1)
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

        layout5 = QHBoxLayout()
        layout5.addWidget(self.leftComboboxLabel)
        layout5.addWidget(self.leftCombobox)
        layout5.setStretchFactor(self.leftComboboxLabel, 1)
        layout5.setStretchFactor(self.leftCombobox, 1)
        leftLayout = QVBoxLayout()
        leftLayout.addLayout(layout5)
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

        layout6 = QHBoxLayout()
        layout6.addWidget(self.rightComboboxLabel)
        layout6.addWidget(self.rightCombobox)
        layout6.setStretchFactor(self.rightComboboxLabel, 1)
        layout6.setStretchFactor(self.rightCombobox, 1)
        rightLayout = QVBoxLayout()
        rightLayout.addLayout(layout6)
        rightLayout.addWidget(self.rightImgViewer)

        # Layout
        self.editLayout = QHBoxLayout()
        self.editLayout.addLayout(leftLayout)
        self.editLayout.addLayout(rightLayout)

        # ==============================================================
        # UI for preview
        # ==============================================================

        self.leftPreviewViewer = QtSimpleOpenGlShaderViewer()
        self.rightPreviewViewer = QtSimpleOpenGlShaderViewer()

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
                self.__clearMarker(i)
                self.markers = self.markers[:i] + self.markers[i + 1:]
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
        self.xSlider.setValue(self.offset[0] + 1)

    @pyqtSlot()
    def onXValueDecremented(self) -> None:
        """
        Callback called when the x value of the offset changes by -1.
        """
        # Forward
        self.xSlider.setValue(self.offset[0] - 1)

    @pyqtSlot(int)
    def xOffsetChanges(self, value: int) -> None:
        """
        Callback called when the x value of the offset changes.
        :param: value the new x value
        """
        # Update offset value and slider text
        self.offset[0] = value
        self.xSliderLabel.setText("X: " + str(value))
        # Update preview
        self.__updatePreview()

    @pyqtSlot()
    def onYValueIncremented(self) -> None:
        """
        Callback called when the y value of the offset changes by +1.
        """
        # Forward
        self.ySlider.setValue(self.offset[1] + 1)

    @pyqtSlot()
    def onYValueDecremented(self) -> None:
        """
        Callback called when the y value of the offset changes by -1.
        """
        # Forward
        self.ySlider.setValue(self.offset[1] - 1)

    @pyqtSlot(int)
    def yOffsetChanges(self, value: int) -> None:
        """
        Callback called when the y value of the offset changes.
        :param: value the new y value
        """
        # Update offset value and slider text
        self.offset[1] = value
        self.ySliderLabel.setText("Y: " + str(value))
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
        # Process markers
        self.__leastSquaresWithSVD()
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
            # Redraw markers
            self.__clearMarker(self.selectedMarker)
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

    def __onMouseOut(self, isLeft: bool) -> None:
        """
        Private method called when the mouse left a viewer space.
        :param: isLeft a boolean to choose emitting viewer
        """
        # Clear status
        self.isDragging = False
        self.selectedMarker = None
        self.__clearHoveringMarker()

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
        # Redraw markers
        self.__clearMarker(i)
        self.__updateMarkers()

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
            # Invalidate scenes
            self.leftImgViewer.scene.invalidate()
            self.rightImgViewer.scene.invalidate()

    def __drawHoveringMarker(self, i: int) -> (QGraphicsRectItem, QGraphicsRectItem):
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
        # Invalidate scenes
        self.leftImgViewer.scene.invalidate()
        self.rightImgViewer.scene.invalidate()
        return rectL, rectR

    def __clearMarker(self, i: int) -> None:
        """
        Private method to clear marker scene objs.
        :param: i the index of the marker to clear.
        """
        # Remove items from scene
        for [objL, objR] in self.markers[i].objs:
            self.leftImgViewer.scene.removeItem(objL)
            self.leftImgViewer.scene.removeItem(objR)
        # Clear array
        self.markers[i].objs = []

    def __addMarker(self, pos: [int]) -> None:
        """
        Private method to add a marker at pos [x, y].
        :param: pos the position where to add the marker
        """
        # Find next available ID
        identifier = max(self.markers, key=lambda x: x.id).id + 1 if len(self.markers) > 0 else 1
        # Create a marker obj
        self.markers.append(MarkerObjData(identifier, pos, MarkerObjData.SOFT_MARKER, []))
        # Redraw markers
        self.__updateMarkers()

    def __drawMarker(self, marker: MarkerObjData) -> None:
        """
        Private method to draw marker obj.
        :param: marker the marker to draw
        """
        # Redraw only "cleared" one
        if len(marker.objs) > 0:
            return
        # Draw lines
        objs = []
        for (leftLine, rightLine) in marker.getLines():
            lineL = self.leftImgViewer.scene.addLine(leftLine, marker.pen)
            lineR = self.rightImgViewer.scene.addLine(rightLine, marker.pen)
            lineL.setZValue(5)
            lineR.setZValue(5)
            objs.append([lineL, lineR])
        # Draw texts
        textL = QGraphicsTextItem(str(marker.id))
        textR = QGraphicsTextItem(str(marker.id))
        for text in [textL, textR]:
            text.setHtml('<div style="background:' + marker.pen.color().name() + ';">' + str(marker.id) + '</p>')
            text.setFont(QFont("Roboto", 12, QFont.Bold))
            text.setOpacity(0.75)
            text.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            text.setDefaultTextColor(Qt.black)
            text.setZValue(7)
        # Update text pos
        (bboxL, bboxR) = marker.getBBox()
        textL.setPos(bboxL.topRight())
        textR.setPos(bboxR.topRight())
        # Add text to scenes
        self.leftImgViewer.scene.addItem(textL)
        self.rightImgViewer.scene.addItem(textR)
        objs.append([textL, textR])
        # Update list
        marker.objs = objs

    def __updateMarkers(self) -> None:
        """
        Private method to redraw markers.
        """
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
        self.__updatePreviewSize(channel1.qimage, channel2.qimage)
        # Image
        img1 = self.__toNumpyArray(channel1.qimage, False)
        img1 = self.__toQImage(img1, QImage.Format_RGBA8888)
        img2 = self.__toNumpyArray(channel2.qimage, False)
        img2 = self.__toQImage(img2, QImage.Format_RGBA8888)
        # Update viewer
        self.leftImgViewer.setImg(img1)
        self.leftImgViewer.px_to_mm = pxSize1
        self.rightImgViewer.setImg(img2)
        self.rightImgViewer.px_to_mm = pxSize2
        # Update overlay images
        self.markers = []
        self.__updateMarkers()

    def __toNumpyArray(self, img: QImage, isGrayScale: bool) -> numpy.ndarray:
        """
        Private method to create a numpy array from QImage.
        :param: img contains the QImage to transform
        :param: isGrayScale a boolean to add conversion in grayscale
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
        arr = numpy.frombuffer(ptr, numpy.uint8).reshape((h, w, 4))
        # Pad img
        [rh, rw] = self.previewSize
        [ph, pw] = [rh - h, rw - w]
        arr = numpy.pad(arr, [(0, ph), (0, pw), (0, 0)], mode='constant')
        # Gray scale
        if isGrayScale:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
            arr = arr.reshape((rh, rw, 1))
        return arr

    def __toQImage(self, arr: numpy.ndarray, imgFormat: int) -> QImage:
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

    def __updatePreviewSize(self, img1: QImage, img2: QImage) -> None:
        """
        Private method to update internal reference size for preview images.
        The preview size must contains both images.
        :param: img1 the first image to contain
        :param: img2 the second image to contain
        """
        # Retrieve sizes
        h1, w1 = img1.height(), img1.width()
        h2, w2 = img2.height(), img2.width()
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
        pass

    def __updatePreview(self, onlyAlpha: bool = False) -> None:
        """
        Private method to update the preview.
        :param: onlyAlpha is a boolean that represents whether the changes are only on the alpha section.
        """
        # ==============================================================
        # Update alpha section
        # ==============================================================
        if not onlyAlpha:
            # ==============================================================
            # Gray scale
            # ==============================================================
            pass

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
        """
        R = None
        T = None
