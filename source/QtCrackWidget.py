from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QDialog, QSizePolicy, QSlider, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source.QtImageViewerPlus import QtImageViewerPlus
from skimage.color import rgb2gray
from source import utils

import matplotlib.pyplot as plt

class QtCrackWidget(QWidget):

    closeCrackWidget = pyqtSignal()

    def __init__(self, map, blob, x, y, parent=None):
        super(QtCrackWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(60,60,65); color: white")

        self.qimg_cropped = utils.cropQImage(map, blob.bbox)
        arr = utils.qimageToNumpyArray(self.qimg_cropped)
        self.input_arr = rgb2gray(arr) * 255
        self.tolerance = 20
        self.blob = blob
        self.xmap = x
        self.ymap = y
        self.qimg_crack = QImage(self.qimg_cropped.width(), self.qimg_cropped.height(), QImage.Format_RGB32)
        self.qimg_crack.fill(qRgb(0, 0, 0))

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedWidth(400)
        self.setFixedHeight(400)

        SLIDER_WIDTH = 200
        IMAGEVIEWER_SIZE = 300  # SIZE x SIZE

        self.sliderTolerance = QSlider(Qt.Horizontal)
        self.sliderTolerance.setFocusPolicy(Qt.StrongFocus)
        self.sliderTolerance.setMinimumWidth(SLIDER_WIDTH)
        self.sliderTolerance.setMinimum(1)
        self.sliderTolerance.setMaximum(100)
        self.sliderTolerance.setValue(self.tolerance)
        self.sliderTolerance.setTickInterval(5)
        self.sliderTolerance.setAutoFillBackground(True)
        self.sliderTolerance.valueChanged.connect(self.sliderToleranceChanged)

        self.lblTolerance = QLabel("Tolerance: 20")
        self.lblTolerance.setAutoFillBackground(True)
        str = "Tolerance {}".format(self.tolerance)
        self.lblTolerance.setText(str)

        layoutTolerance = QHBoxLayout()
        layoutTolerance.addWidget(self.lblTolerance)
        layoutTolerance.addWidget(self.sliderTolerance)

        self.viewerplus = QtImageViewerPlus()
        self.viewerplus.disableScrollBars()
        self.viewerplus.setFixedWidth(IMAGEVIEWER_SIZE)
        self.viewerplus.setFixedHeight(IMAGEVIEWER_SIZE)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.setAutoFillBackground(True)

        self.btnApply = QPushButton("Apply")
        self.btnApply.setAutoFillBackground(True)

        layoutButtons = QHBoxLayout()
        layoutButtons.addWidget(self.btnCancel)
        layoutButtons.addWidget(self.btnApply)

        layoutV = QVBoxLayout()
        layoutV.addLayout(layoutTolerance)
        layoutV.addWidget(self.viewerplus)
        layoutV.addLayout(layoutButtons)
        layoutV.setSpacing(10)
        self.setLayout(layoutV)

        self.viewerplus.setImage(self.qimg_cropped)
        self.preview()

        self.setAutoFillBackground(True)

        self.setWindowTitle("Crack")


    def keyPressEvent(self, event):

        if event.key() == Qt.Key_Escape:

            # RESET CURRENT OPERATION
            self.closeCrackWidget.emit()


    @pyqtSlot()
    def sliderToleranceChanged(self):

        # update tolerance value
        newvalue = self.sliderTolerance.value()
        str1 = "Tolerance {}".format(newvalue)
        self.lblTolerance.setText(str1)
        self.tolerance = newvalue

        # update the preview of the crack segmentation
        self.preview()

    @pyqtSlot()
    def preview(self):

        arr = self.input_arr.copy()
        mask_crack = self.blob.createCrack(arr, self.xmap, self.ymap, self.tolerance, preview=True)
        self.qimg_crack = utils.maskToQImage(mask_crack)
        self.viewerplus.setOpacity(0.5)
        self.viewerplus.setOverlayImage(self.qimg_crack)


    def apply(self):

        mask_crack = self.blob.createCrack(self.input_arr, self.xmap, self.ymap, self.tolerance, preview=False)
