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
from PyQt5.QtWidgets import QSlider,QGroupBox, QWidget, QDialog, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source.Annotation import Annotation

from source import utils

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

        LINEWIDTH = 300
        self.editFilename = QLineEdit(classifiers[0]["Weights"])
        self.editFilename.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editFilename.setReadOnly(True)
        self.editFilename.setFixedWidth(LINEWIDTH)
        self.editNClasses = QLineEdit(str(classifiers[0]["Num. Classes"]))
        self.editNClasses.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editNClasses.setReadOnly(True)
        self.editNClasses.setFixedWidth(LINEWIDTH)
        self.editClasses = QLineEdit(self.classes2str(classifiers[0]["Classes"]))
        self.editClasses.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editClasses.setFixedWidth(LINEWIDTH)
        self.editClasses.setReadOnly(True)
        self.editScale = QLineEdit(str(classifiers[0]["Scale"]))
        self.editScale.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editScale.setFixedWidth(LINEWIDTH)
        self.editScale.setReadOnly(True)
        self.editAvgColor = QLineEdit(self.avgcolor2str(classifiers[0]["Average Norm."]))
        self.editAvgColor.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editAvgColor.setFixedWidth(LINEWIDTH)
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
        self.btnPrev = QPushButton("Preview")

        layoutButtons = QHBoxLayout()
        layoutButtons.setAlignment(Qt.AlignLeft)
        layoutButtons.addWidget(self.btnChooseArea)
        layoutButtons.addWidget(self.btnPrev)

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

        self.QlabelThresh = QLabel("Uncertainty Threshold:")
        self.QlabelThreshValue = QLabel("0.0")

        self.QlabelTransparency = QLabel("Transparency:")
        self.QlabelTransparencyValue = QLabel("50.0")


        SLIDER_WIDTH = 200

        self.sliderScores = QSlider(Qt.Horizontal)
        self.sliderScores.setFocusPolicy(Qt.StrongFocus)
        self.sliderScores.setMinimumWidth(SLIDER_WIDTH)
        self.sliderScores.setMinimum(0)
        self.sliderScores.setMaximum(50)
        self.sliderScores.setValue(0)
        self.sliderScores.setTickInterval(20)
        self.sliderScores.setAutoFillBackground(True)
        self.sliderScores.valueChanged.connect(self.sliderScoresChanged)

        layoutSliderScores = QHBoxLayout()
        layoutSliderScores.addWidget(self.QlabelThreshValue)
        layoutSliderScores.addWidget(self.sliderScores)

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
        layoutSliderTransparency.addWidget(self.QlabelTransparencyValue)
        layoutSliderTransparency.addWidget(self.sliderTransparency)

        layoutThreshold = QVBoxLayout()
        layoutThreshold.setAlignment(Qt.AlignTop)
        layoutThreshold.addWidget(self.QlabelThresh)
        layoutThreshold.addLayout(layoutSliderScores)
        layoutThreshold.setSpacing(20)
        layoutThreshold.addWidget(self.QlabelTransparency)
        layoutThreshold.addLayout(layoutSliderTransparency)

        layoutPred= QHBoxLayout()
        layoutPred.addLayout(layoutTiles)
        layoutPred.addLayout(layoutThreshold)

        layoutPreview = QVBoxLayout()
        layoutPreview.addLayout(layoutButtons)
        layoutPreview.addLayout(layoutPred)

        self.groupPrew = QGroupBox("Check Classifier Prediction")
        self.groupPrew.setLayout(layoutPreview)
        #self.groupPrew.hide()

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

        self.QlabelThresh.hide()
        self.QlabelThreshValue.hide()

        self.setWindowTitle("Select Classifier")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.rgb_image = None
        self.labelimage = None

    def setRGBPreview(self, image):

        self.QPixmapRGB = QPixmap.fromImage(image)
        self.rgb_image = image.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        size = self.LABEL_SIZE
        self.QlabelRGB.setPixmap(self.QPixmapRGB.scaled(QSize(size, size), Qt.KeepAspectRatio))

    def setLabelPreview(self, image):

        self.labelimage = image
        self.updateLabelPreview()

    def updateLabelPreview(self):

        opacity = self.sliderTransparency.value() / 100.0

        backimg = self.rgb_image.copy(0, 0, self.rgb_image.width(), self.rgb_image.height())
        painter = QPainter()
        painter.begin(backimg)
        painter.setCompositionMode(QPainter.CompositionMode_Overlay)
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

    def classes2str(self, classes_list):

        txt = str(classes_list)
        txt = txt.replace('[', '')
        txt = txt.replace(']', '')
        txt = txt.replace("'", '')
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
        self.sliderScores.hide()

    def disableSliders(self):

        self.sliderScores.setEnabled(False)
        self.sliderTransparency.setEnabled(False)
        self.sliderScores.hide()

    def closeEvent(self, event):
        self.closed.emit()