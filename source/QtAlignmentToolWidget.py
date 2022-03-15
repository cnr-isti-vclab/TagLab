import cv2
import numpy
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot
from PyQt5.QtGui import QImage, QMouseEvent, QPen, QFont
from PyQt5.QtWidgets import QWidget, QSizePolicy, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QSlider, QApplication, \
    QCheckBox, QPushButton, QMessageBox, QGraphicsTextItem

from source.QtImageViewer import QtImageViewer


class QtAlignmentToolWidget(QWidget):
    closed = pyqtSignal()

    SOFT_MARKER = 0
    HARD_MARKER = 1

    SOFT_MARKER_W = 1
    HARD_MARKER_W = 1

    MARKER_SIZE = 16
    MARKER_WIDTH = 4

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
        self.resolution = 1
        self.mkSize = QtAlignmentToolWidget.MARKER_SIZE
        self.mkWidth = QtAlignmentToolWidget.MARKER_WIDTH
        self.previewSize = None
        self.rotation = numpy.identity(2)
        self.offset = [0, 0]
        self.cachedLeftGrayArray = None
        self.cachedRightGrayArray = None
        self.cachedLeftRGBAArray = None
        self.cachedRightRGBAArray = None
        self.leftPreviewParams = [0, 0, 0]
        self.rightPreviewParams = [0, 0, 0]
        self.lastMousePos = None
        self.isDragging = False
        self.selectedMarker = None
        self.hoveringSceneObjs = None
        self.hoveringMarker = None
        self.markers = []

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

        # Resolution
        self.resolutions = [{"name": "Original", "factor": 1},
                            {"name": "Decreased", "factor": 2},
                            {"name": "X-Decreased", "factor": 4},
                            {"name": "XX-Decreased", "factor": 8},
                            {"name": "Extreme", "factor": 16}]
        self.resolutionCombobox = QComboBox()
        self.resolutionCombobox.setMaximumWidth(200)

        for res in self.resolutions:
            self.resolutionCombobox.addItem(res["name"])

        self.resolutionCombobox.setCurrentIndex(0)
        self.resolutionCombobox.currentIndexChanged.connect(self.resolutionChanges)

        # Layout
        self.buttons = QVBoxLayout()
        layout1 = QHBoxLayout()
        layout1.addWidget(self.checkBoxSync)
        layout1.addWidget(self.checkBoxPreview)
        layout1.addWidget(self.autoAlignButton)
        layout1.addWidget(self.confirmAlignmentButton)
        layout1.addWidget(self.resolutionCombobox)
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

        self.leftPreviewViewer = QtImageViewer()
        self.rightPreviewViewer = QtImageViewer()

        self.leftPreviewViewer.viewHasChanged[float, float, float].connect(self.rightPreviewViewer.setViewParameters)
        self.rightPreviewViewer.viewHasChanged[float, float, float].connect(self.leftPreviewViewer.setViewParameters)

        self.leftPreviewViewer.viewHasChanged[float, float, float].connect(self.onLeftPreviewParamsChanged)
        self.rightPreviewViewer.viewHasChanged[float, float, float].connect(self.onRightPreviewParamsChanged)

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

    def closeEvent(self, event):
        self.closed.emit()
        super(QtAlignmentToolWidget, self).closeEvent(event)

    @pyqtSlot(int)
    def leftImageChanges(self, index):
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
    def rightImageChanges(self, index):
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
    def toggleSync(self, value):
        """
        Callback called when the sync mode is toggled on/off.
        :param: value a boolean to set the enable/disable the sync mode.
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
    def togglePreview(self, value):
        """
        Callback called when the Preview Mode is toggled on/off.
        :param: value a boolean representing if the mode is toggled.
        """
        # Hide / Show widgets
        self.__togglePreviewMode(value)
        # If preview is set
        if value:
            # Initialize and update the view
            self.__initializePreview()
            self.__updatePreview()

    @pyqtSlot(int)
    def previewAlphaValueChanges(self, value):
        """
        Callback called when the alpha value changes.
        :param: value the new value
        """
        # Update alpha value and slider text
        self.alpha = value
        self.alphaSliderLabel.setText("A: " + str(value))
        # Update preview
        self.__updatePreview(onlyAlpha=True)

    @pyqtSlot()
    def onXValueIncremented(self):
        """
        Callback called when the x value of the offset changes by +1.
        """
        # Forward
        self.xSlider.setValue(self.offset[0] + 1)

    @pyqtSlot()
    def onXValueDecremented(self):
        """
        Callback called when the x value of the offset changes by -1.
        """
        # Forward
        self.xSlider.setValue(self.offset[0] - 1)

    @pyqtSlot(int)
    def xOffsetChanges(self, value):
        """
        Callback called when the x value of the offset changes.
        :param: value the new value
        """
        # Update offset value and slider text
        self.offset[0] = value
        self.xSliderLabel.setText("X: " + str(value))
        # Update preview
        self.__updatePreview()

    @pyqtSlot()
    def onYValueIncremented(self):
        """
        Callback called when the - value of the offset changes by +1.
        """
        # Forward
        self.ySlider.setValue(self.offset[1] + 1)

    @pyqtSlot()
    def onYValueDecremented(self):
        """
        Callback called when the - value of the offset changes by -1.
        """
        # Forward
        self.ySlider.setValue(self.offset[1] - 1)

    @pyqtSlot(int)
    def yOffsetChanges(self, value):
        """
        Callback called when the y value of the offset changes.
        :param: value the new value
        """
        # Update offset value and slider text
        self.offset[1] = value
        self.ySliderLabel.setText("Y: " + str(value))
        # Update preview
        self.__updatePreview()

    @pyqtSlot(int)
    def thresholdValueChanges(self, value):
        """
        Callback called when the threshold value changes.
        :param: value the new value
        """
        # Update threshold value and slider text
        self.threshold = value
        self.thresholdSliderLabel.setText("T: " + str(value))
        # Update preview
        self.__updatePreview()

    @pyqtSlot(float, float, float)
    def onLeftPreviewParamsChanged(self, posx, posy, zoom):
        """
        Callback called when left preview viewer's view params changes.
        :param: posx the new posx param
        :param: posy the new posy param
        :param: zoom the new zoom param
        """
        # Store parameters
        self.leftPreviewParams = [posx, posy, zoom]

    @pyqtSlot(float, float, float)
    def onRightPreviewParamsChanged(self, posx, posy, zoom):
        """
        Callback called when right preview viewer's view params changes.
        :param: posx the new posx param
        :param: posy the new posy param
        :param: zoom the new zoom param
        """
        # Store parameters
        self.rightPreviewParams = [posx, posy, zoom]

    @pyqtSlot(int)
    def resolutionChanges(self, index):
        """
        Callback called when the resolution changes.
        :param: index of the new resolution
        """
        self.resolution = self.resolutions[index]["factor"]
        # Update edit
        self.__updateImgViewers()
        # Update preview
        self.__initializePreview()
        self.__updatePreview()

    @pyqtSlot(QMouseEvent)
    def onLeftViewMouseDown(self, event):
        """
        Callback called on a mouse down event over the left viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseDown(event, True)

    @pyqtSlot(QMouseEvent)
    def onLeftViewMouseMove(self, event):
        """
        Callback called on a mouse move event over the left viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseMove(event, True)

    @pyqtSlot(QMouseEvent)
    def onLeftViewMouseUp(self, event):
        """
        Callback called on a mouse up event over the left viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseUp(event, True)

    @pyqtSlot()
    def onLeftViewMouseOut(self):
        """
        Callback called when the mouse left the left viewer space.
        """
        # Forward
        self.__onMouseOut(True)

    @pyqtSlot(QMouseEvent)
    def onRightViewMouseDown(self, event):
        """
        Callback called on a mouse down event over the right viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseDown(event, False)

    @pyqtSlot(QMouseEvent)
    def onRightViewMouseMove(self, event):
        """
        Callback called on a mouse move event over the right viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseMove(event, False)

    @pyqtSlot(QMouseEvent)
    def onRightViewMouseUp(self, event):
        """
        Callback called on a mouse up event over the right viewer.
        :param: event the mouse event
        """
        # Forward
        self.__onMouseUp(event, False)

    @pyqtSlot()
    def onRightViewMouseOut(self):
        """
        Callback called when the mouse left the right viewer space.
        """
        # Forward
        self.__onMouseOut(False)

    @pyqtSlot()
    def onAutoAlignRequested(self):
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
        [R, T] = self.__leastSquaresWithSVD()
        # Switch to preview mode
        self.checkBoxPreview.setChecked(True)

    @pyqtSlot()
    def onConfirmAlignment(self):
        """
        Callback called when the user request to confirm and save alignment data.
        """
        # Save data
        # TODO
        # Close widget (?)
        self.close()

    def __onMouseDown(self, event, isLeft):
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

    def __onMouseUp(self, event, isLeft):
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

    def __onMouseMove(self, event, isLeft):
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
            self.markers[self.selectedMarker]["rViewPos"][0] += dx
            self.markers[self.selectedMarker]["rViewPos"][1] += dy
            # If user is dragging marker on the left viewer
            if isLeft:
                # Update also the right one
                self.markers[self.selectedMarker]["lViewPos"][0] += dx
                self.markers[self.selectedMarker]["lViewPos"][1] += dy
            # Redraw markers
            self.__clearMarker(self.selectedMarker)
            self.__drawMarkers()
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

    def __onMouseOut(self, isLeft):
        """
        Private method called when the mouse left a viewer space.
        :param: isLeft a boolean to choose emitting viewer
        """
        # Clear status
        self.isDragging = False
        self.selectedMarker = None
        self.__clearHoveringMarker()

    def __mapToViewer(self, pos, isLeft):
        """
        Private method that maps a pos [x, y] into the viewer space.
        :param: pos the position to map
        :param: isLeft a boolean to choose which viewer to use
        :return: the converted 2d vector
        """
        viewer = self.leftImgViewer if isLeft else self.rightImgViewer
        return viewer.clipScenePos(viewer.mapToScene(pos))

    def __getMarkerBBOX(self, i):
        """
        Private method to retrieve bbox of selected marker.
        :param: i the index of the marker to evaluate
        :return: [bboxL, bboxR] the bbox of each view
        """
        # Unpack pos
        [lmx, lmy] = self.markers[i]["lViewPos"]
        [rmx, rmy] = self.markers[i]["rViewPos"]
        # Create bbox
        side = self.mkSize + self.mkWidth
        return [
            [lmx - side, lmy - side, lmx + side, lmy + side],
            [rmx - side, rmy - side, rmx + side, rmy + side],
        ]

    def __findMarkerAt(self, pos, isLeft):
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
            [bboxL, bboxR] = self.__getMarkerBBOX(i)
            [x1, y1, x2, y2] = bboxL if isLeft else bboxR
            # Check if bbox contains pos
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        return None

    def __toggleMarker(self, i):
        """
        Private method to "toggle" marker with index i.
        By toggling a marker, it changes type until deleted.
        :param: i the index of the marker to toggle.
        """
        # HARD -> SOFT
        if self.markers[i]["mkType"] == QtAlignmentToolWidget.HARD_MARKER:
            self.markers[i]["mkType"] = QtAlignmentToolWidget.SOFT_MARKER
        # SOFT -> HARD
        elif self.markers[i]["mkType"] == QtAlignmentToolWidget.SOFT_MARKER:
            self.markers[i]["mkType"] = QtAlignmentToolWidget.HARD_MARKER
        # Redraw markers
        self.__clearMarker(i)
        self.__drawMarkers()

    def __clearHoveringMarker(self):
        """
        Private method to clear hovering data.
        """
        # Clear only if exists
        if self.hoveringMarker is not None:
            # Retrieve scene objs
            [rectL, rectR] = self.hoveringSceneObjs
            # Remove them from scenes
            self.leftImgViewer.scene.removeItem(rectL)
            self.rightImgViewer.scene.removeItem(rectR)
            self.hoveringMarker = None
            self.hoveringSceneObjs = None
            # Invalidate scenes
            self.leftImgViewer.scene.invalidate()
            self.rightImgViewer.scene.invalidate()

    def __drawHoveringMarker(self, i):
        """
        Private method to draw hovering box.
        :param: i the index of the marker to hover
        :return: the objs created
        """
        # Create drawing pen
        pen = QPen(Qt.white, 1)
        # Retrieve bbox
        [bboxL, bboxR] = self.__getMarkerBBOX(i)
        [lx1, ly1, lx2, ly2] = bboxL
        [rx1, ry1, rx2, ry2] = bboxR
        # Draw rects
        rectL = self.leftImgViewer.scene.addRect(lx1, ly1, lx2 - lx1, ly2 - ly1, pen)
        rectR = self.rightImgViewer.scene.addRect(rx1, ry1, rx2 - rx1, ry2 - ry1, pen)
        rectL.setZValue(6)
        rectR.setZValue(6)
        # Invalidate scenes
        self.leftImgViewer.scene.invalidate()
        self.rightImgViewer.scene.invalidate()
        return [rectL, rectR]

    def __clearMarker(self, i):
        """
        Private method to clear marker scene objs.
        :param: i the index of the marker to clear.
        """
        # Remove items from scene
        for [objL, objR] in self.markers[i]["sceneObjs"]:
            self.leftImgViewer.scene.removeItem(objL)
            self.leftImgViewer.scene.removeItem(objR)
        # Clear array
        self.markers[i]["sceneObjs"] = []

    def __addMarker(self, pos):
        """
        Private method to add a marker at pos [x, y].
        :param: pos the position where to add the marker
        """
        # Find ID
        identifier = max(self.markers, key=lambda x: x["id"], default={"id": 0})["id"] + 1
        # Create a marker obj
        self.markers.append({
            "id": identifier,  # identifier
            "lViewPos": [pos[0], pos[1]],  # left view position
            "rViewPos": [pos[0], pos[1]],  # right view position
            "mkType": QtAlignmentToolWidget.SOFT_MARKER,  # marker type
            "sceneObjs": []  # Scene objects
        })
        # Redraw markers
        self.__drawMarkers()

    def __drawMarkerSymb(self, identifier, lpos, rpos, pen):
        """
        Private method to draw a marker.
        :param: identifier the marker id
        :param: lpos the position where to draw the marker
        :param: rpos the position where to draw the marker
        :return: the added objects
        """
        # Unpack coords
        [lx, ly] = lpos
        [rx, ry] = rpos
        # Lines to draw
        lines = [
            ([-self.mkSize, -self.mkSize], [-1 * self.mkWidth / 2, -1 * self.mkWidth / 2]),  # TL - 0
            ([+1 * self.mkWidth / 2, +1 * self.mkWidth / 2], [+self.mkSize, +self.mkSize]),  # 0 - BR
            ([-self.mkSize, +self.mkSize], [-1 * self.mkWidth / 2, +1 * self.mkWidth / 2]),  # BL - 0
            ([+1 * self.mkWidth / 2, -1 * self.mkWidth / 2], [+self.mkSize, -self.mkSize]),  # 0 - TR
        ]
        objs = []
        # Draw lines
        for ([dxs, dys], [dxe, dye]) in lines:
            lineL = self.leftImgViewer.scene.addLine(lx + dxs, ly + dys, lx + dxe, ly + dye, pen)
            lineR = self.rightImgViewer.scene.addLine(rx + dxs, ry + dys, rx + dxe, ry + dye, pen)
            lineL.setZValue(5)
            lineR.setZValue(5)
            objs.append([lineL, lineR])
        # Draw texts
        textL = QGraphicsTextItem()
        textL.setPos(lx, ly - self.mkSize * 2)
        textR = QGraphicsTextItem()
        textR.setPos(rx, ry - self.mkSize * 2)
        for text in [textL, textR]:
            text.setHtml('<div style="background:#000000;">' + str(identifier) + '</p>')
            text.setFont(QFont("Roboto", 8, QFont.Bold))
            text.setDefaultTextColor(Qt.white)
            text.setZValue(7)
        # Add text to scenes
        self.leftImgViewer.scene.addItem(textL)
        self.rightImgViewer.scene.addItem(textR)
        # Add objs
        objs.append([textL, textR])
        return objs

    def __drawMarker(self, marker):
        """
        Private method to draw marker obj.
        :param: marker the marker to draw
        """
        # Redraw only "cleared" one
        if len(marker["sceneObjs"]) > 0:
            return
        # Unpack pos
        lpos = marker["lViewPos"]
        rpos = marker["rViewPos"]
        # Switch pen on marker
        if marker["mkType"] == QtAlignmentToolWidget.SOFT_MARKER:
            pen = QPen(Qt.yellow, self.mkWidth)
        elif marker["mkType"] == QtAlignmentToolWidget.HARD_MARKER:
            pen = QPen(Qt.red, self.mkWidth)
        else:
            pen = QPen(Qt.white, self.mkWidth)
        # Draw symbol
        marker["sceneObjs"] = self.__drawMarkerSymb(marker["id"], lpos, rpos, pen)

    def __drawMarkers(self):
        """
        Private method to update markers overlay image.
        """
        # Create empty arrays
        h, w = self.previewSize[0] // self.resolution, self.previewSize[1] // self.resolution
        # Draw markers
        for marker in self.markers:
            self.__drawMarker(marker)
        # Invalidate scene
        self.leftImgViewer.scene.invalidate()
        self.rightImgViewer.scene.invalidate()

    def __updateImgViewers(self):
        """
        Private method to update the viewers
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
        img1 = self.__toNumpyArray(channel1.qimage, False, False)
        img1 = self.__toQImage(img1, QImage.Format_RGBA8888)
        img2 = self.__toNumpyArray(channel2.qimage, False, False)
        img2 = self.__toQImage(img2, QImage.Format_RGBA8888)
        # Update viewer
        self.leftImgViewer.setImg(img1)
        self.leftImgViewer.px_to_mm = pxSize1
        self.rightImgViewer.setImg(img2)
        self.rightImgViewer.px_to_mm = pxSize2
        # Update overlay images
        self.markers = []
        self.__drawMarkers()

    def __toNumpyArray(self, img, applyResolution, isGrayScale):
        """
        Private method to create a numpy array from QImage.
        :param: img contains the QImage to transform
        :param: applyResolution a boolean to toggle resolution
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
        # Scale down by resolution factor
        if applyResolution:
            [ah, aw] = [rh // self.resolution, rw // self.resolution]
            arr = cv2.resize(arr, (aw, ah), interpolation=cv2.INTER_AREA)
            arr = arr.reshape((ah, aw, 4))
            arr[:, :, 3] = 255
            [rh, rw] = [ah, aw]
        # Gray scale
        if isGrayScale:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2GRAY)
            arr = arr.reshape((rh, rw, 1))
        return arr

    def __toQImage(self, arr, imgFormat):
        """
        Private method to transform a numpy array into a QImage.
        :param: arr is the numpy array of shape (h, w, c)
        :param: imgFormat is the format of the image to create
        :return: a QImage
        """
        # Retrieve the shape
        [h, w, c] = arr.shape
        # Create and return the image
        img = QImage(arr.data, w, h, c * w, imgFormat)
        return img

    def __offsetArrays(self, a, b):
        """
        Private method to offset two numpy arrays.
        The array are offset in a "complementary" way:
            - the first (a) is offset from the bottom right.
            - the second (b) is offset from the top left.
        :param: a the first numpy array of shape (h, w, c)
        :param: b the second numpy array of shape (h, w, c)
        :return: the tuple (offset(a), offset(b))
        """
        # Retrieve the shape
        [h, w, _] = b.shape
        # Retrieve the offset
        [dx, dy] = self.offset
        # Scale offset down by the resolution factor
        dx = dx // self.resolution
        dy = dy // self.resolution
        # Transform each array and return the tuple
        tmp1 = a[dy:, dx:]
        tmp2 = b[:h - dy, :w - dx]
        return tmp1, tmp2

    def __processPreviewArrays(self, a, b):
        """
        Private method to create a numpy array representing the difference image for the preview.
        :param: a the first numpy array with shape (h, w, c)
        :param: b the second numpy array with shape (h, w, c)
        :return: the preview numpy array
        """
        # Offset arrays
        [tmp1, tmp2] = self.__offsetArrays(a, b)
        # Compute the absolute difference
        shape = tmp1.shape
        tmp = cv2.absdiff(
            # Blur to reduce small errors
            cv2.medianBlur(tmp1, 7),
            cv2.medianBlur(tmp2, 7)
        )
        tmp = tmp.reshape(shape)
        # Compute the threshold
        tmp = numpy.where(tmp < self.threshold, 0, tmp)
        return tmp

    def __updatePreviewSize(self, img1, img2):
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

    def __initializePreview(self):
        """
        Private method called once when the Preview Mode is turned on.
        It initializes all the necessary numpy arrays.
        """
        # Clear stored preview's view parameters
        self.leftPreviewParams = [0, 0, 0]
        self.rightPreviewParams = [0, 0, 0]
        # Retrieve indexes
        index1 = self.leftCombobox.currentIndex()
        index2 = self.rightCombobox.currentIndex()
        # Images
        img1 = self.project.images[index1].channels[0].qimage
        img2 = self.project.images[index2].channels[0].qimage
        # Load arrays: Gray Scale
        self.cachedLeftGrayArray = self.__toNumpyArray(img1, True, True)
        self.cachedRightGrayArray = self.__toNumpyArray(img2, True, True)
        # Load arrays: RGBA Scale
        self.cachedLeftRGBAArray = self.__toNumpyArray(img1, True, False)
        self.cachedRightRGBAArray = self.__toNumpyArray(img2, True, False)

    def __updatePreview(self, onlyAlpha=False):
        """
        Private method to update the preview.
        :param: onlyAlpha is a boolean that represents whether the changes are only on the alpha section.
        """
        # ==============================================================
        # Update alpha section
        # ==============================================================
        # Clear view
        self.leftPreviewViewer.clear()
        # Compute offset for RGBA preview
        tmp1, tmp2 = self.__offsetArrays(self.cachedLeftRGBAArray, self.cachedRightRGBAArray)
        # Transform cached array into QImage
        img1 = self.__toQImage(tmp1.copy(), QImage.Format_RGBA8888)
        img2 = self.__toQImage(tmp2.copy(), QImage.Format_RGBA8888)
        # Update preview img, opacity and overlay img
        self.leftPreviewViewer.setImg(img1, self.leftPreviewParams[2])
        self.leftPreviewViewer.setOpacity(numpy.clip(self.alpha, 0.0, 100.0) / 100.0)
        self.leftPreviewViewer.setOverlayImage(img2)
        # Jump this section to make the alpha changes apply faster
        if not onlyAlpha:
            # ==============================================================
            # Gray scale
            # ==============================================================
            # Clear view
            self.rightPreviewViewer.clear()
            # Apply transformations to GRAY preview
            tmp = self.__processPreviewArrays(self.cachedLeftGrayArray, self.cachedRightGrayArray)
            # Transform cached array into QImage
            img = self.__toQImage(tmp.copy(), QImage.Format_Grayscale8)
            # Update preview img
            self.rightPreviewViewer.setImg(img, self.rightPreviewParams[2])

    def __togglePreviewMode(self, isPreviewMode):
        """
        Private method to set widget visibility to toggle the Preview Mode on/off.
        :param: isPreviewMode a boolean value to enable / disable the Preview Mode
        """
        # (Preview-ONLY) widgets
        self.leftPreviewViewer.setVisible(isPreviewMode)
        self.rightPreviewViewer.setVisible(isPreviewMode)
        self.confirmAlignmentButton.setVisible(isPreviewMode)
        self.resolutionCombobox.setVisible(isPreviewMode)
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

    def __leastSquaresWithSVD(self):
        """

        """
        R = None
        T = None
        return [R, T]
