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

from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QImage, QIntValidator
from PyQt5.QtWidgets import QApplication, QWidget, QProgressBar, QMessageBox, QSizePolicy, QSlider, QLabel, \
    QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout
from source.QtImageViewer import QtImageViewer
from source.Annotation import Annotation
from skimage import measure
from skimage import feature
from skimage import morphology
from scipy import ndimage as ndi
import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
import torch
from models.isegm.inference import clicker
from models.isegm.inference.predictors import get_predictor
from models.isegm.inference import utils
from source.utils import cropQImage, cropImage, qimageToNumpyArray, maskToQImage, rgbToQImage
from source.Mask import paintMask
import random

class QtBricksWidget(QWidget):

    closeBricksWidget = pyqtSignal()

    def __init__(self, orthoimage, pixel_size, macroarea_blob, parent=None):
        super(QtBricksWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.pixel_size = pixel_size  # in mm

        # put the background outside the selected macroarea
        self.orthoimage_cropped = cropQImage(orthoimage, macroarea_blob.bbox)
        img = qimageToNumpyArray(self.orthoimage_cropped)
        mask = macroarea_blob.getMask()
        img[mask == 0] = [40, 40, 40]
        self.orthoimage_cropped = rgbToQImage(img)
        self.macroarea_blob = macroarea_blob

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)

        EDIT_WIDTH = 200
        SLIDER_WIDTH = 300

        self.lblMinW = QLabel("Min width (cm):")
        self.lblMaxW = QLabel("Max width (cm):")
        self.lblMinH = QLabel("Min height (cm):")
        self.lblMaxH = QLabel("Max height (cm):")
        self.editMinW = QLineEdit("")
        self.editMinW.setFixedWidth(EDIT_WIDTH)
        self.editMinW.setPlaceholderText("Minimum width of a brick")
        self.editMinW.setValidator(QIntValidator())
        self.editMaxW = QLineEdit("")
        self.editMaxW.setFixedWidth(EDIT_WIDTH)
        self.editMaxW.setPlaceholderText("Maximum width of a brick")
        self.editMaxW.setValidator(QIntValidator())
        self.editMinH = QLineEdit("")
        self.editMinH.setFixedWidth(EDIT_WIDTH)
        self.editMinH.setPlaceholderText("Mininum height of a brick")
        self.editMinH.setValidator(QIntValidator())
        self.editMaxH = QLineEdit("")
        self.editMaxH.setFixedWidth(EDIT_WIDTH)
        self.editMaxH.setPlaceholderText("Maximum height of a brick")
        self.editMaxH.setValidator(QIntValidator())

        l1 = QVBoxLayout()
        l1.addWidget(self.lblMinW)
        l1.addWidget(self.lblMinH)
        l2 = QVBoxLayout()
        l2.addWidget(self.editMinW)
        l2.addWidget(self.editMinH)
        l3 = QVBoxLayout()
        l3.addWidget(self.lblMaxW)
        l3.addWidget(self.lblMaxH)
        l4 = QVBoxLayout()
        l4.addWidget(self.editMaxW)
        l4.addWidget(self.editMaxH)

        layoutSize = QHBoxLayout()
        layoutSize.addLayout(l1)
        layoutSize.addLayout(l2)
        layoutSize.addLayout(l3)
        layoutSize.addLayout(l4)

        self.BLUR_STRENGTH_MINVALUE = 10.0
        self.BLUR_STRENGTH_MAXVALUE = 150.0

        self.EDGE_SIGMA_MINVALUE = 1.0
        self.EDGE_SIGMA_MAXVALUE = 10.0

        self.sliderBlurStrength = QSlider(Qt.Horizontal)
        self.sliderBlurStrength.setFocusPolicy(Qt.StrongFocus)
        self.sliderBlurStrength.setMinimumWidth(SLIDER_WIDTH)
        self.sliderBlurStrength.setMinimum(1)
        self.sliderBlurStrength.setMaximum(100)
        self.sliderBlurStrength.setValue(10)
        self.sliderBlurStrength.setTickInterval(5)
        self.sliderBlurStrength.setAutoFillBackground(True)
        self.sliderBlurStrength.valueChanged.connect(self.sliderBlurStrengthChanged)

        self.sliderEdgeSigma = QSlider(Qt.Horizontal)
        self.sliderEdgeSigma.setFocusPolicy(Qt.StrongFocus)
        self.sliderEdgeSigma.setMinimumWidth(SLIDER_WIDTH)
        self.sliderEdgeSigma.setMinimum(1)
        self.sliderEdgeSigma.setMaximum(100)
        self.sliderEdgeSigma.setValue(10)
        self.sliderEdgeSigma.setTickInterval(5)
        self.sliderEdgeSigma.setAutoFillBackground(True)
        self.sliderEdgeSigma.valueChanged.connect(self.sliderEdgeSigmaChanged)

        value = self.sliderBlurStrength.value()
        self.blur_strength = self.BLUR_STRENGTH_MINVALUE + (value / 100.0) * (self.BLUR_STRENGTH_MAXVALUE - self.BLUR_STRENGTH_MINVALUE)
        value = self.sliderEdgeSigma.value()
        self.edge_sigma = self.EDGE_SIGMA_MINVALUE + (value / 100.0) * (self.EDGE_SIGMA_MAXVALUE - self.EDGE_SIGMA_MINVALUE)

        self.lblBlurStrength = QLabel("Blur strength: 20")
        self.lblBlurStrength.setAutoFillBackground(True)
        txt = "Blur strength: {:.3f}".format(self.blur_strength)
        self.lblBlurStrength.setText(txt)

        self.lblEdgeSigma = QLabel("Edge sigma: 20")
        self.lblEdgeSigma.setAutoFillBackground(True)
        txt = "Edge sigma: {:.3f}".format(self.edge_sigma)
        self.lblEdgeSigma.setText(txt)

        layoutFilterLabels = QVBoxLayout()
        layoutFilterLabels.addWidget(self.lblBlurStrength)
        layoutFilterLabels.addWidget(self.lblEdgeSigma)

        layoutFilterSliders = QVBoxLayout()
        layoutFilterSliders.addWidget(self.sliderBlurStrength)
        layoutFilterSliders.addWidget(self.sliderEdgeSigma)

        layoutFilter = QHBoxLayout()
        layoutFilter.addLayout(layoutFilterLabels)
        layoutFilter.addLayout(layoutFilterSliders)

        layoutParams = QVBoxLayout()
        layoutParams.addLayout(layoutSize)
        layoutParams.addLayout(layoutFilter)

        self.btnPreview = QPushButton("Preview")
        self.btnPreview.clicked.connect(self.preview)
        self.btnPreview.setMinimumWidth(60)
        self.btnPreview.setMinimumHeight(60)

        layoutTop = QHBoxLayout()
        layoutTop.addStretch()
        layoutTop.addWidget(self.btnPreview)
        layoutTop.addLayout(layoutParams)
        layoutTop.addStretch()

        IMAGEVIEWER_W = 800
        IMAGEVIEWER_H = 500
        self.viewer = QtImageViewer()
        self.viewer.disableScrollBars()
        self.viewer.enablePan()
        self.viewer.enableZoom()
        self.viewer.setFixedWidth(IMAGEVIEWER_W)
        self.viewer.setFixedHeight(IMAGEVIEWER_H)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.setAutoFillBackground(True)

        self.btnApply = QPushButton("Apply")
        self.btnApply.setAutoFillBackground(True)

        layoutButtons = QHBoxLayout()
        layoutButtons.addWidget(self.btnCancel)
        layoutButtons.addWidget(self.btnApply)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimumWidth(300)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setAutoFillBackground(True)

        layout = QVBoxLayout()
        layout.addLayout(layoutTop)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.viewer)
        layout.addLayout(layoutButtons)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.progress_bar.hide()

        self.viewer.setImg(self.orthoimage_cropped)

        self.setAutoFillBackground(True)

        self.setWindowTitle("Bricks Segmentation")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        self.ritm_net = None
        self.predictor_params = {'brs_mode': 'NoBRS'}
        self.init_mask = None
        self.clicker = clicker.Clicker()  # handles clicked point (original code of RITM)
        self.edges = None
        self.seeds = None
        self.seg_bricks = []
        self.min_width = 0
        self.max_width = 0
        self.min_heihgt = 0
        self.max_height = 0

    def keyPressEvent(self, event):

        # ESCAPE reset the current operation, so it closes the widget
        if event.key() == Qt.Key_Escape:
            self.closeBricksWidget.emit()

    @pyqtSlot()
    def sliderBlurStrengthChanged(self):

        # update value
        newvalue = float(self.sliderBlurStrength.value())
        newvalue = self.BLUR_STRENGTH_MINVALUE + (newvalue / 100.0) * (self.BLUR_STRENGTH_MAXVALUE - self.BLUR_STRENGTH_MINVALUE)
        txt = "Blur strength: {:.3f}".format(newvalue)
        self.lblBlurStrength.setText(txt)
        self.blur_strength = newvalue

    @pyqtSlot()
    def sliderEdgeSigmaChanged(self):

        # update value
        newvalue = float(self.sliderEdgeSigma.value())
        newvalue = self.EDGE_SIGMA_MINVALUE + (newvalue / 100.0) * (self.EDGE_SIGMA_MAXVALUE - self.EDGE_SIGMA_MINVALUE)
        txt = "Edge sigma: {:.3f}".format(newvalue)
        self.lblEdgeSigma.setText(txt)
        self.edge_sigma = newvalue

    def setupBricksSize(self):
        """
        Cpnnvert the bricks' size (in cm) to pixels and check if all the values have been inserted.
        """

        txt = self.editMinW.text()
        if txt == "":
            return False
        else:
            self.min_width = int((int(txt) * 10.0) / self.pixel_size)

        txt = self.editMaxW.text()
        if txt == "":
            return False
        else:
            self.max_width = int((int(txt) * 10.0) / self.pixel_size)

        txt = self.editMinH.text()
        if txt == "":
            return False
        else:
            self.min_height = int((int(txt) * 10.0) / self.pixel_size)

        txt = self.editMaxH.text()
        if txt == "":
            return False
        else:
            self.max_height = int((int(txt) * 10.0) / self.pixel_size)

        return True

    def seedExtraction(self, input_image):

        size = self.min_width
        image = qimageToNumpyArray(input_image)

        # denoise
        blurred = cv2.bilateralFilter(image, 3, self.blur_strength, 30)

        # posterization
        blurred2 = cv2.pyrMeanShiftFiltering(blurred, 3, 40, maxLevel=1)

        gray = cv2.cvtColor(blurred2, cv2.COLOR_BGR2GRAY)
        self.edges = feature.canny(gray, sigma=self.edge_sigma)
        clean = morphology.remove_small_objects(self.edges, 50, connectivity=4)
        distance = ndi.distance_transform_edt(~clean)

        local_max = feature.peak_local_max(distance, indices=False, min_distance=size)
        markers = measure.label(local_max, connectivity=2)
        labels = morphology.watershed(-distance, markers)

        regions = measure.regionprops(markers)
        self.seeds = []
        for region in regions:
            self.seeds.append(region.coords[0])

    def createBlobs(self, input_image):

        # load RITM network (if necessary)
        if self.ritm_net is None:

            model_name = 'ritm_corals.pth'
            model_path = os.path.join("models", model_name)

            if not torch.cuda.is_available():
                print("CUDA NOT AVAILABLE!")
                device = torch.device("cpu")
            else:
                device = torch.device("cuda:0")

            try:
                self.ritm_net = utils.load_is_model(model_path, device, cpu_dist_maps=False)
                self.ritm_net.to(device)
                # initialize predictor
                self.predictor = get_predictor(self.ritm_net, device=device, **self.predictor_params)

            except Exception as e:
                box = QMessageBox()
                box.setText("Could not load the Ritm network. You might need to run update.py.")
                box.exec()

        input_image = qimageToNumpyArray(input_image)

        annotations = Annotation()

        # for each seed create segment a brick using RITM

        self.progress_bar.show()
        self.progress_bar.reset()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(len(self.seeds))
        self.progress_bar.setValue(0)

        self.seg_bricks = []
        for i, seed in enumerate(self.seeds):

            # crop image
            bbox = [seed[0]-160, seed[1]-240, 480, 320]
            crop_image = cropImage(input_image, bbox)
            self.predictor.set_input_image(crop_image)

            qimg = rgbToQImage(crop_image)

            # create clicks
            self.clicker.reset_clicks()

            # generate positive clicks
            y = 160
            x = 240 - self.min_width / 2
            click = clicker.Click(is_positive=True, coords=(y, x))
            self.clicker.add_click(click)

            y = 160
            x = 240 + self.min_width / 2
            click = clicker.Click(is_positive=True, coords=(y, x))
            self.clicker.add_click(click)

            y = 160 - self.min_height / 2
            x = 240
            click = clicker.Click(is_positive=True, coords=(y, x))
            self.clicker.add_click(click)

            y = 160 + self.min_height / 2
            x = 240
            click = clicker.Click(is_positive=True, coords=(y, x))
            self.clicker.add_click(click)

            # generate negative clicks
            # pen = QPen(Qt.white)
            # brush = QBrush(Qt.red)
            # painter = QPainter(qimg)
            # painter.setBrush(brush)
            # painter.setPen(pen)
            #
            # neg_counter = 0
            # for j in range(100):
            #
            #     x = random.randint(0, 480)
            #     y = random.randint(0, 320)
            #
            #     if abs(x - 240) > w_max and abs(y - 160) > h_max and neg_counter < 10:
            #         painter.drawEllipse(x, y, 5, 5)
            #         click = clicker.Click(is_positive=False, coords=(y, x))
            #         self.clicker.add_click(click)
            #         neg_counter = neg_counter + 1
            #
            # brush.setColor(Qt.green)
            # painter.setBrush(brush)
            # painter.drawEllipse(240, 160, 5, 5)
            # painter.end()
            # qimg.save("C:\\temp\\punti.png")

            self.init_mask = None
            pred = self.predictor.get_prediction(self.clicker, prev_mask=self.init_mask)

            segm_mask = pred > 0.5
            segm_mask = segm_mask.astype(np.int32)
            segm_mask = segm_mask*255
            torch.cuda.empty_cache()

            offsety = self.macroarea_blob.bbox[0] + bbox[0]
            offsetx = self.macroarea_blob.bbox[1] + bbox[1]

            area_min = self.min_width * self.min_height * 5.0
            blobs = annotations.blobsFromMask(segm_mask, offsetx, offsety, area_min)

            area_max = self.max_width * self.max_height
            for blob in blobs:
                if blob.area < area_max:
                    self.seg_bricks.append(blob)

            self.progress_bar.setValue(i)

    @pyqtSlot()
    def preview(self):

        if self.setupBricksSize() is not True:
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Bricks segmentation")
            msgBox.setText("Please, enter the minimum and maximum size of the bricks.")
            msgBox.exec()
            return

        self.seedExtraction(self.orthoimage_cropped)

        mask_preview = maskToQImage(self.edges.astype(np.int32))

        pen = QPen(Qt.white)
        brush = QBrush(Qt.red)
        painter = QPainter(mask_preview)
        painter.setBrush(brush)
        painter.setPen(pen)
        for seed in self.seeds:
            painter.drawEllipse(seed[1], seed[0], 5, 5)
        painter.end()

        self.viewer.setOpacity(0.5)
        self.viewer.setOverlayImage(mask_preview)


    def apply(self):

        if self.setupBricksSize() is not True:
            msgBox = QMessageBox()
            msgBox.setWindowTitle("Bricks segmentation")
            msgBox.setText("Please, enter the minimum and maximum size of the bricks.")
            msgBox.exec()
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.seedExtraction(self.orthoimage_cropped)
        self.createBlobs(self.orthoimage_cropped)
        QApplication.restoreOverrideCursor()

        return self.seg_bricks

