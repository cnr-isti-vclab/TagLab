# TagLab                                               
# A semi-automatic segmentation tool                                    
#
# Copyright(C) 2019                                         
# Visual Computing Lab                                           
# ISTI - Italian National Research Council                              
# All rights reserved.                                                      
                                                                          
# This program is free software; you can redistribute it and/or modify      
# it under the terms of the GNU General Public License as published by      
# the Free Software Foundation; either version 2 of the License, or         
# (at your option) any later version.                                       
                                                                           
# This program is distributed in the hope that it will be useful,           
# but WITHOUT ANY WARRANTY; without even the implied warranty of            
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             
#GNU General Public License (http://www.gnu.org/licenses/gpl.txt)          
# for more details.                                               

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, qRgb
from PyQt5.QtWidgets import QWidget, QSizePolicy, QSlider, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source.QtImageViewer import QtImageViewer
from source.Blob import Blob
from source import genutils
import numpy as np
from skimage.color import rgb2gray
from skimage import measure
from skimage.filters import gaussian
from skimage.morphology import flood

class QtCrackWidget(QWidget):

    closeCrackWidget = pyqtSignal()

    def __init__(self, map, annotations, blob, x, y, parent=None):
        super(QtCrackWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(60,60,65); color: white")

        self.qimg_cropped = genutils.cropQImage(map, blob.bbox)
        arr = genutils.qimageToNumpyArray(self.qimg_cropped)
        self.input_arr = rgb2gray(arr) * 255
        self.tolerance = 20
        self.annotations = annotations
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

        self.viewer = QtImageViewer()
        self.viewer.disableScrollBars()
        self.viewer.setFixedWidth(IMAGEVIEWER_SIZE)
        self.viewer.setFixedHeight(IMAGEVIEWER_SIZE)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.setAutoFillBackground(True)

        self.btnApply = QPushButton("Apply")
        self.btnApply.setAutoFillBackground(True)

        layoutButtons = QHBoxLayout()
        layoutButtons.addWidget(self.btnCancel)
        layoutButtons.addWidget(self.btnApply)

        layoutV = QVBoxLayout()
        layoutV.addLayout(layoutTolerance)
        layoutV.addWidget(self.viewer)
        layoutV.addLayout(layoutButtons)
        layoutV.setSpacing(10)
        self.setLayout(layoutV)

        self.viewer.setImg(self.qimg_cropped)
        self.preview()

        self.setAutoFillBackground(True)

        self.setWindowTitle("Create Crack")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

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

    def createCrack(self, blob, input_arr, x, y, tolerance, preview=True):
        """
        Given a inner blob point (x,y), the function use it as a seed for a paint bucket tool and create
        a correspondent blob hole
        """

        box = blob.bbox
        x_crop = x - box[1]
        y_crop = y - box[0]

        input_arr = gaussian(input_arr, 2)
        # input_arr = segmentation.inverse_gaussian_gradient(input_arr, alpha=1, sigma=1)

        blob_mask = blob.getMask()

        crack_mask = flood(input_arr, (int(y_crop), int(x_crop)), tolerance=tolerance).astype(int)
        cracked_blob = np.logical_and((blob_mask > 0), (crack_mask < 1))
        cracked_blob = cracked_blob.astype(int)

        if preview:
            return cracked_blob

        regions = measure.regionprops(measure.label(cracked_blob))

        area_th = 1000
        created_blobs = []

        for region in regions:
            if region.area > area_th:
                b = Blob(region, box[1], box[0], self.annotations.getFreeId())
                b.class_name = blob.class_name
                created_blobs.append(b)

        return created_blobs

    @pyqtSlot()
    def preview(self):

        arr = self.input_arr.copy()
        mask_crack = self.createCrack(self.blob, arr, self.xmap, self.ymap, self.tolerance, preview=True)
        self.qimg_crack = genutils.maskToQImage(mask_crack)
        self.viewer.setOpacity(0.5)
        self.viewer.setOverlayImage(self.qimg_crack)


    def apply(self):

        return self.createCrack(self.blob, self.input_arr, self.xmap, self.ymap, self.tolerance, preview=False)
