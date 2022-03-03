import numpy
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot
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
        self.previewButton = QCheckBox("Preview")
        self.previewButton.setChecked(False)
        self.previewButton.setFocusPolicy(Qt.NoFocus)
        self.previewButton.setMinimumWidth(40)
        self.previewButton.stateChanged[int].connect(self.togglePreview)

        # Slider
        self.alphaSlider = QSlider(Qt.Horizontal)
        self.alphaSlider.setFocusPolicy(Qt.StrongFocus)
        self.alphaSlider.setMinimumWidth(400)
        self.alphaSlider.setMinimum(1)
        self.alphaSlider.setMaximum(100)
        self.alphaSlider.setValue(50)
        self.alphaSlider.setTickInterval(1)
        self.alphaSlider.setAutoFillBackground(True)
        self.alphaSlider.valueChanged.connect(self.previewAlphaValueChanged)

        # Layout
        self.buttons = QHBoxLayout()
        self.buttons.addWidget(self.checkBoxSync)
        self.buttons.addWidget(self.previewButton)
        self.buttons.addWidget(self.alphaSlider)

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

        self.previewViewer = QtImageViewer()

        self.previewLayout = QHBoxLayout()
        self.previewLayout.addWidget(self.previewViewer)

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
        self.previewButton.stateChanged.emit(0)

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

    def preparePreview(self):
        index = self.leftCombobox.currentIndex()
        baseImage = self.project.images[index].channels[0].qimage

        self.previewViewer.setImg(baseImage)
        self.alphaSlider.setValue(50)

    def togglePreviewMode(self, isPreviewMode):
        self.previewViewer.setVisible(isPreviewMode)
        self.alphaSlider.setVisible(isPreviewMode)
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
            self.togglePreviewMode(True)
            self.preparePreview()
        else:
            self.togglePreviewMode(False)

    @pyqtSlot(int)
    def previewAlphaValueChanged(self, value):
        index = self.rightCombobox.currentIndex()
        overlayImage = self.project.images[index].channels[0].qimage

        self.previewViewer.setOpacity(numpy.clip(value, 0.0, 100.0) / 100.0)
        self.previewViewer.setOverlayImage(overlayImage)
