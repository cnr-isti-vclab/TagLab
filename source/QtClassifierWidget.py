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

import os

from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QSlider,QGroupBox, QCheckBox,  QWidget, QDialog, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source.Annotation import Annotation
import numpy as np

from source import genutils

class QtClassifierWidget(QWidget):

    closed = pyqtSignal()

    def __init__(self, classifiers, parent=None):
        super(QtClassifierWidget, self).__init__(parent)

        self.classifiers = classifiers

        self.setStyleSheet("background-color: rgba(60,60,65,100); color: white")


        layoutH0 = QHBoxLayout()

        self.lblClassifier = QLabel("Classifier: ")

        self.comboClassifier = QComboBox()
        self.comboClassifier.setMinimumWidth(300)
        for classifier in classifiers:
            self.comboClassifier.addItem(classifier['Classifier Name'])

        self.comboClassifier.currentIndexChanged.connect(self.classifierChanged)

        layoutH0.setAlignment(Qt.AlignLeft)
        layoutH0.addStretch()
        layoutH0.addWidget(self.lblClassifier)
        layoutH0.addWidget(self.comboClassifier)
        layoutH0.addStretch()

        self.lblFilename = QLabel("Filename: ")
        self.lblNClasses = QLabel("N. of classes: ")
        self.lblClasses = QLabel("Classes recognized: ")
        self.lblScale = QLabel("Training scale (px-to-mm): ")
        self.lblAvgColor = QLabel("Training avg. color: ")

        layoutH1a = QVBoxLayout()
        layoutH1a.setAlignment(Qt.AlignRight)
        layoutH1a.addWidget(self.lblFilename)
        layoutH1a.addWidget(self.lblNClasses)
        layoutH1a.addWidget(self.lblClasses)
        layoutH1a.addWidget(self.lblScale)
        layoutH1a.addWidget(self.lblAvgColor)
        self.lblAvgColor.hide()

        self.editFilename = QLineEdit(classifiers[0]["Weights"])
        self.editFilename.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editFilename.setReadOnly(True)

        self.editNClasses = QLineEdit(str(classifiers[0]["Num. Classes"]))
        self.editNClasses.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editNClasses.setReadOnly(True)

        self.editClasses = QLineEdit(self.classes2str(classifiers[0]["Classes"]))
        self.editClasses.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")

        self.editClasses.setReadOnly(True)
        self.editScale = QLineEdit(str(classifiers[0]["Scale"]))
        self.editScale.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")

        self.editScale.setReadOnly(True)
        self.editAvgColor = QLineEdit(self.avgcolor2str(classifiers[0]["Average Norm."]))
        self.editAvgColor.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editAvgColor.setReadOnly(True)

        layoutH1b = QVBoxLayout()
        layoutH1b.setAlignment(Qt.AlignLeft)
        layoutH1b.addWidget(self.editFilename)
        layoutH1b.addWidget(self.editNClasses)
        layoutH1b.addWidget(self.editClasses)
        layoutH1b.addWidget(self.editScale)
        layoutH1b.addWidget(self.editAvgColor)
        self.editAvgColor.hide()


        layoutH1 = QHBoxLayout()
        layoutH1.addLayout(layoutH1a)
        layoutH1.addLayout(layoutH1b)

        #prev panel

        self.btnChooseArea = QPushButton()
        ChooseAreaIcon = QIcon("icons\\select_area.png")
        self.btnChooseArea.setIcon(ChooseAreaIcon)
        self.chkAutocolor = QCheckBox("Auto color")
        self.chkAutolevel = QCheckBox("Auto contrast")
        self.btnPrev = QPushButton("Preview")


        SLIDER_WIDTH = 160

        self.QlabelThresh = QLabel("Prediction threshold:")
        self.QlabelThreshValue = QLabel("0.5")

        self.QlabelTransparency = QLabel("Transparency:")
        self.QlabelTransparencyValue = QLabel("50.0")

        self.sliderTransparency = QSlider(Qt.Horizontal)
        self.sliderTransparency.setFocusPolicy(Qt.StrongFocus)
        self.sliderTransparency.setMinimumWidth(SLIDER_WIDTH)
        self.sliderTransparency.setMinimum(0)
        self.sliderTransparency.setMaximum(100)
        self.sliderTransparency.setValue(50)
        self.sliderTransparency.setTickInterval(20)
        self.sliderTransparency.setAutoFillBackground(True)
        self.sliderTransparency.valueChanged.connect(self.sliderTransparencyChanged)

        layoutSliderTransparency = QHBoxLayout()
        layoutSliderTransparency.addWidget(self.QlabelTransparency)
        layoutSliderTransparency.addWidget(self.QlabelTransparencyValue)
        layoutSliderTransparency.addWidget(self.sliderTransparency)

        self.sliderScores = QSlider(Qt.Horizontal)
        self.sliderScores.setFocusPolicy(Qt.StrongFocus)
        self.sliderScores.setMinimumWidth(SLIDER_WIDTH)
        self.sliderScores.setMinimum(0)
        self.sliderScores.setMaximum(100)
        self.sliderScores.setValue(50)
        self.sliderScores.setTickInterval(20)
        self.sliderScores.setAutoFillBackground(True)
        self.sliderScores.valueChanged.connect(self.sliderScoresChanged)

        layoutSliderScores = QHBoxLayout()
        layoutSliderScores.addWidget(self.QlabelThresh)
        layoutSliderScores.addWidget(self.QlabelThreshValue)
        layoutSliderScores.addWidget(self.sliderScores)

        layoutButtons = QHBoxLayout()
        layoutButtons.setAlignment(Qt.AlignLeft)
        layoutButtons.addWidget(self.btnChooseArea)
        layoutButtons.addWidget(self.chkAutocolor)
        self.chkAutocolor.stateChanged.connect(self.useAutocolor)
        layoutButtons.addWidget(self.chkAutolevel)
        self.chkAutolevel.stateChanged.connect(self.useAutoLevel)
        layoutButtons.addWidget(self.btnPrev)
        layoutButtons.addStretch()
        layoutButtons.addLayout(layoutSliderTransparency)
        layoutButtons.addSpacing(20)
        layoutButtons.addLayout(layoutSliderScores)

        self.LABEL_SIZE = 600

        self.QlabelRGB = QLabel("")
        self.QPixmapRGB = QPixmap(self.LABEL_SIZE, self.LABEL_SIZE)
        self.QPixmapRGB.fill(Qt.black)
        self.QlabelRGB.setPixmap(self.QPixmapRGB)

        self.QlabelPred = QLabel("")
        self.QPixmapPred = QPixmap(self.LABEL_SIZE, self.LABEL_SIZE)
        self.QPixmapPred.fill(Qt.black)
        self.QlabelPred.setPixmap(self.QPixmapPred)

        layoutTiles = QHBoxLayout()
        layoutTiles.setAlignment(Qt.AlignTop)
        layoutTiles.addWidget(self.QlabelRGB)
        layoutTiles.addWidget(self.QlabelPred)

        layoutPreview = QVBoxLayout()
        layoutPreview.addLayout(layoutButtons)
        layoutPreview.addLayout(layoutTiles)

        self.groupPrew = QGroupBox("Check Classifier Prediction")
        self.groupPrew.setLayout(layoutPreview)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnApply = QPushButton("Apply")

        layoutH2 = QHBoxLayout()
        layoutH2.setAlignment(Qt.AlignRight)
        layoutH2.addStretch()
        layoutH2.addWidget(self.btnCancel)
        layoutH2.addWidget(self.btnApply)

        layoutV = QVBoxLayout()
        layoutV.addLayout(layoutH0)
        layoutV.addLayout(layoutH1)
        layoutV.addSpacing(10)
        layoutV.addWidget(self.groupPrew)
        layoutV.addLayout(layoutH2)
        layoutV.setSpacing(3)
        self.setLayout(layoutV)

        self.setWindowTitle("Select Classifier")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.rgb_image = None
        self.labelimage = None

        self.preview_area = [0, 0, 0, 0]

    def colorPreview(self):

        if self.rgb_image is not None:

            if not self.chkAutocolor.isChecked() and not self.chkAutolevel.isChecked():
                self.setRGBPreview(self.rgb_image)

            elif self.chkAutocolor.isChecked() and not self.chkAutolevel.isChecked():
                color_rgb = self.rgb_image.convertToFormat(QImage.Format_RGB32)
                color_rgb = genutils.qimageToNumpyArray(color_rgb)
                color_rgb = genutils.whiteblance(color_rgb)
                color_rgb_qimage = genutils.rgbToQImage(color_rgb)
                self.QPixmapRGB = QPixmap.fromImage(color_rgb_qimage)
                size = self.LABEL_SIZE
                self.QlabelRGB.setPixmap(self.QPixmapRGB.scaled(QSize(size, size), Qt.KeepAspectRatio))

            elif not self.chkAutocolor.isChecked() and self.chkAutolevel.isChecked():
                color_rgb = self.rgb_image.convertToFormat(QImage.Format_RGB32)
                color_rgb = genutils.qimageToNumpyArray(color_rgb)
                color_rgb = genutils.autolevel(color_rgb, 1.0)
                color_rgb_qimage = genutils.rgbToQImage(color_rgb)
                self.QPixmapRGB = QPixmap.fromImage(color_rgb_qimage)
                size = self.LABEL_SIZE
                self.QlabelRGB.setPixmap(self.QPixmapRGB.scaled(QSize(size, size), Qt.KeepAspectRatio))

            elif self.chkAutocolor.isChecked() and self.chkAutolevel.isChecked():

                #always apply first auto color then autolevel
                color_rgb = self.rgb_image.convertToFormat(QImage.Format_RGB32)
                color_rgb = genutils.qimageToNumpyArray(color_rgb)
                #this returns a float64
                color_rgb = genutils.whiteblance(color_rgb)
                color_rgb = color_rgb.astype(np.uint8)
                level_rgb = genutils.autolevel(color_rgb, 1.0)
                color_rgb_qimage = genutils.rgbToQImage(level_rgb)
                self.QPixmapRGB = QPixmap.fromImage(color_rgb_qimage)
                size = self.LABEL_SIZE
                self.QlabelRGB.setPixmap(self.QPixmapRGB.scaled(QSize(size, size), Qt.KeepAspectRatio))


    @pyqtSlot(int, int, int, int)
    def updatePreviewArea(self, x, y, width, height):

        width = min(2048, width)
        height = min(2048, height)
        self.preview_area = [x, y, width, height]

    def getPreviewArea(self):

        x = self.preview_area[0]
        y = self.preview_area[1]
        w = self.preview_area[2]
        h = self.preview_area[3]

        return x, y, w, h

    @pyqtSlot(int)
    def useAutocolor(self):
        self.colorPreview()


    @pyqtSlot(int)
    def useAutoLevel(self):
        self.colorPreview()


    def setRGBPreview(self, image):

        self.QPixmapRGB = QPixmap.fromImage(image)
        self.rgb_image = image.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        size = self.LABEL_SIZE
        self.QlabelRGB.setPixmap(self.QPixmapRGB.scaled(QSize(size, size), Qt.KeepAspectRatio))

    def setLabelPreview(self, image):

        self.labelimage = image
        self.updateLabelPreview()

    def updateLabelPreview(self):

        if self.rgb_image is not None and self.labelimage is not None:
            opacity = 1.0 - (self.sliderTransparency.value() / 100.0)
            backimg = self.rgb_image.copy(0, 0, self.rgb_image.width(), self.rgb_image.height())
            painter = QPainter()
            painter.begin(backimg)
            painter.setOpacity(opacity)
            painter.drawImage(0, 0, self.labelimage)
            painter.end()
            self.QPixmapPred = QPixmap.fromImage(backimg)
            size = self.LABEL_SIZE
            self.QlabelPred.setPixmap(self.QPixmapPred.scaled(QSize(size, size), Qt.KeepAspectRatio))

    @pyqtSlot(int)
    def classifierChanged(self, index):

        classifier = self.classifiers[index]
        self.editFilename.setText(classifier["Weights"])
        self.editNClasses.setText(str(classifier["Num. Classes"]))
        self.editClasses.setText(self.classes2str(classifier["Classes"]))
        self.editScale.setText(str(classifier["Scale"]))
        self.editAvgColor.setText(self.avgcolor2str(classifier["Average Norm."]))

    def selected(self):

        return self.classifiers[self.comboClassifier.currentIndex()]

    def classes2str(self, classes_dict):

        txt = ""
        for key in classes_dict.keys():
            txt += key
            txt += ", "

        # remove the last commas
        txt = txt[:-2]
        return txt

    def avgcolor2str(self, avgcolor_list):

        txt = "R = {0:.2f}, G = {1:.2f}, B = {2:.2f} ".format(avgcolor_list[0]*255.0, avgcolor_list[1]*255.0, avgcolor_list[2]*255.0)
        return txt

    @pyqtSlot()
    def sliderScoresChanged(self):

        # update tolerance value
        newvalue = self.sliderScores.value()/100.0
        txt = "{:.2f}".format(newvalue)
        self.QlabelThreshValue.setText(txt)

    @pyqtSlot()
    def sliderTransparencyChanged(self):

        # update transparency value
        newvalue = self.sliderTransparency.value()
        txt = "{:.0f}%".format(newvalue)
        self.QlabelTransparencyValue.setText(txt)

        self.updateLabelPreview()

    def enableSliders(self):

        self.sliderScores.setEnabled(True)
        self.sliderTransparency.setEnabled(True)

    def disableSliders(self):

        self.sliderScores.setEnabled(False)
        self.sliderTransparency.setEnabled(False)

    def closeEvent(self, event):
        self.closed.emit()