import numpy
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QWidget, QSizePolicy, QVBoxLayout, QLabel, QHBoxLayout, QComboBox, QSlider, QApplication, \
    QCheckBox

from source.QtImageViewer import QtImageViewer


class QtAlignmentToolWidget(QWidget):
    closed = pyqtSignal()

    def __init__(self, project, parent=None):
        super(QtAlignmentToolWidget, self).__init__(parent)

        # ==============================================================

        self.project = project
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setWindowTitle("Alignment Tool")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        self.offset = [40, 20]
        self.arr1 = None
        self.arr2 = None
        self.arr3 = None
        self.arr4 = None

        # ==============================================================
        # Top buttons
        # ==============================================================

        # Sync
        self.checkBoxSync = QCheckBox("Sync")
        self.checkBoxSync.setChecked(True)
        self.checkBoxSync.setFocusPolicy(Qt.NoFocus)
        self.checkBoxSync.setMinimumWidth(40)
        self.checkBoxSync.stateChanged[int].connect(self.toggleSync)

        # Preview
        self.checkBoxPreview = QCheckBox("Preview")
        self.checkBoxPreview.setChecked(False)
        self.checkBoxPreview.setFocusPolicy(Qt.NoFocus)
        self.checkBoxPreview.setMinimumWidth(40)
        self.checkBoxPreview.stateChanged[int].connect(self.togglePreview)

        # Manual offset
        self.xSliderLabel = QLabel("X:")
        self.xSlider = QSlider(Qt.Horizontal)
        self.xSlider.setMinimum(1)
        self.xSlider.setMaximum(64)
        self.xSlider.setTickInterval(1)
        self.xSlider.setValue(self.offset[0])
        self.xSlider.setMinimumWidth(50)
        self.xSlider.valueChanged.connect(self.xOffsetChanged)
        self.ySliderLabel = QLabel("Y:")
        self.ySlider = QSlider(Qt.Horizontal)
        self.ySlider.setMinimum(1)
        self.ySlider.setMaximum(64)
        self.ySlider.setTickInterval(1)
        self.ySlider.setValue(self.offset[1])
        self.ySlider.setMinimumWidth(50)
        self.ySlider.valueChanged.connect(self.yOffsetChanged)

        # Slider
        self.alphaSliderLabel = QLabel("Alpha")
        self.alphaSlider = QSlider(Qt.Horizontal)
        self.alphaSlider.setFocusPolicy(Qt.StrongFocus)
        self.alphaSlider.setMinimumWidth(200)
        self.alphaSlider.setMinimum(1)
        self.alphaSlider.setMaximum(100)
        self.alphaSlider.setValue(50)
        self.alphaSlider.setTickInterval(1)
        self.alphaSlider.setAutoFillBackground(True)
        self.alphaSlider.valueChanged.connect(self.previewAlphaValueChanged)

        # Layout
        self.buttons = QHBoxLayout()
        self.buttons.addWidget(self.checkBoxSync)
        self.buttons.addWidget(self.checkBoxPreview)
        self.buttons.addWidget(self.alphaSliderLabel)
        self.buttons.addWidget(self.alphaSlider)
        self.buttons.addWidget(self.xSliderLabel)
        self.buttons.addWidget(self.xSlider)
        self.buttons.addWidget(self.ySliderLabel)
        self.buttons.addWidget(self.ySlider)

        # ==============================================================
        # Middle UI containing map selector and map viewer
        # ==============================================================

        # Left
        self.leftCombobox = QComboBox()
        self.leftCombobox.setMinimumWidth(200)

        for image in self.project.images:
            self.leftCombobox.addItem(image.name)

        self.leftCombobox.setCurrentIndex(0)
        self.leftCombobox.currentIndexChanged.connect(self.leftImageChanged)

        self.leftImgViewer = QtImageViewer()

        leftLayout = QVBoxLayout()
        leftLayout.addWidget(self.leftCombobox)
        leftLayout.addWidget(self.leftImgViewer)

        # Right
        self.rightCombobox = QComboBox()
        self.rightCombobox.setMinimumWidth(200)

        for image in self.project.images:
            self.rightCombobox.addItem(image.name)

        self.rightCombobox.setCurrentIndex(0)
        self.rightCombobox.currentIndexChanged.connect(self.rightImageChanged)

        self.rightImgViewer = QtImageViewer()

        rightLayout = QVBoxLayout()
        rightLayout.addWidget(self.rightCombobox)
        rightLayout.addWidget(self.rightImgViewer)

        # Layout
        self.editLayout = QHBoxLayout()
        self.editLayout.addLayout(leftLayout)
        self.editLayout.addLayout(rightLayout)

        # ==============================================================
        # UI for preview
        # ==============================================================

        self.aplhaPreviewViewer = QtImageViewer()
        self.leftPreviewViewer = QtImageViewer()
        self.rightPreviewViewer = QtImageViewer()

        self.previewLayout = QHBoxLayout()
        self.previewLayout.addWidget(self.aplhaPreviewViewer)
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

        self.checkBoxSync.stateChanged.emit(1)
        self.checkBoxPreview.stateChanged.emit(0)

        self.leftCombobox.currentIndexChanged.emit(0)
        self.rightCombobox.currentIndexChanged.emit(1)

        # ==============================================================

    def closeEvent(self, event):
        self.closed.emit()
        super(QtAlignmentToolWidget, self).closeEvent(event)

    def __updateImgViewer(self, index, isLeft):
        """
        Updates the viewer and ensure that two different images are selected.
        """
        # Validate index
        N = len(self.project.images)
        if index == -1 or index >= N:
            return

        # Default channel (0)
        channel = self.project.images[index].channels[0]

        # Check if channel is loaded
        if channel.qimage is None:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            channel.loadData()
            QApplication.restoreOverrideCursor()

        # Check with viewer to update
        if isLeft:
            self.leftImgViewer.setImg(channel.qimage)

            # Ensure indexes are different
            if index == self.rightCombobox.currentIndex():
                self.rightCombobox.setCurrentIndex((index + 1) % N)

        else:
            self.rightImgViewer.setImg(channel.qimage)

            # Ensure indexes are different
            if index == self.leftCombobox.currentIndex():
                self.leftCombobox.setCurrentIndex((index + 1) % N)

    @pyqtSlot(int)
    def leftImageChanged(self, index):
        # Forward to private method
        self.__updateImgViewer(index, True)

    @pyqtSlot(int)
    def rightImageChanged(self, index):
        # Forward to private method
        self.__updateImgViewer(index, False)

    @pyqtSlot(int)
    def toggleSync(self, value):
        """
        If sync mode is toggle, viewer events are shared.
        """
        if value:
            self.leftImgViewer.viewHasChanged[float, float, float].connect(self.rightImgViewer.setViewParameters)
            self.rightImgViewer.viewHasChanged[float, float, float].connect(self.leftImgViewer.setViewParameters)
        else:
            self.leftImgViewer.viewHasChanged[float, float, float].disconnect()
            self.rightImgViewer.viewHasChanged[float, float, float].disconnect()

    def __updatePreview(self):
        if self.arr1 is None:
            index = self.leftCombobox.currentIndex()
            baseImage = self.project.images[index].channels[0].qimage
            img1 = baseImage.convertToFormat(QImage.Format_Grayscale8)
            width1, height1 = img1.width(), img1.height()
            ptr1 = img1.bits()
            ptr1.setsize(height1 * width1 * 1)
            self.arr1 = numpy.frombuffer(ptr1, numpy.uint8).reshape(height1, width1, 1).copy()
        else:
            self.leftPreviewViewer.clear()

        if self.arr2 is None:
            index2 = self.rightCombobox.currentIndex()
            baseImage2 = self.project.images[index2].channels[0].qimage
            img2 = baseImage2.convertToFormat(QImage.Format_Grayscale8)
            width2, height2 = img2.width(), img2.height()
            ptr2 = img2.bits()
            ptr2.setsize(height2 * width2 * 1)
            self.arr2 = numpy.frombuffer(ptr2, numpy.uint8).reshape(height2, width2, 1).copy()
        else:
            self.leftPreviewViewer.clear()

        [h, w, c] = self.arr2.shape

        tmp1 = self.arr1[self.offset[0]:, self.offset[1]:]
        tmp2 = self.arr2[:w-self.offset[0], :h-self.offset[1]]

        # Abs of (a-b) => 20-40 = 20 NOT 235 (255 - 20)
        arrA = numpy.subtract(tmp1, tmp2)
        self.qimg1 = QImage(arrA.data, arrA.shape[1], arrA.shape[0], arrA.shape[1], QImage.Format_Grayscale8)

        self.leftPreviewViewer.setImg(self.qimg1)

        # self.aplhaPreviewViewer.setImg(baseImage)
        # self.alphaSlider.setValue(50)

    def __togglePreviewMode(self, isPreviewMode):
        self.aplhaPreviewViewer.setVisible(isPreviewMode)
        self.leftPreviewViewer.setVisible(isPreviewMode)
        self.rightPreviewViewer.setVisible(isPreviewMode)
        self.alphaSliderLabel.setVisible(isPreviewMode)
        self.alphaSlider.setVisible(isPreviewMode)
        self.xSliderLabel.setVisible(isPreviewMode)
        self.xSlider.setVisible(isPreviewMode)
        self.ySliderLabel.setVisible(isPreviewMode)
        self.ySlider.setVisible(isPreviewMode)
        self.leftImgViewer.setVisible(not isPreviewMode)
        self.rightImgViewer.setVisible(not isPreviewMode)
        self.checkBoxSync.setVisible(not isPreviewMode)
        self.leftCombobox.setVisible(not isPreviewMode)
        self.rightCombobox.setVisible(not isPreviewMode)

    @pyqtSlot(int)
    def togglePreview(self, value):
        """
        If preview mode is toggle, preview layout is set.
        """
        if value:
            self.__togglePreviewMode(True)
            self.__updatePreview()
        else:
            self.__togglePreviewMode(False)

    @pyqtSlot(int)
    def previewAlphaValueChanged(self, value):
        index = self.rightCombobox.currentIndex()
        overlayImage = self.project.images[index].channels[0].qimage
        self.aplhaPreviewViewer.setOpacity(numpy.clip(value, 0.0, 100.0) / 100.0)
        self.aplhaPreviewViewer.setOverlayImage(overlayImage)

    @pyqtSlot(int)
    def xOffsetChanged(self, value):
        self.offset[0] = value
        self.__updatePreview()

    @pyqtSlot(int)
    def yOffsetChanged(self, value):
        self.offset[1] = value
        self.__updatePreview()
