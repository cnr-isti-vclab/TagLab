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
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QDialog, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source.Annotation import Annotation

from source import utils

class QtClassifierWidget(QWidget):

    def __init__(self, classifiers, parent=None):
        super(QtClassifierWidget, self).__init__(parent)

        self.classifiers = classifiers

        self.setStyleSheet("background-color: rgba(60,60,65,100); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

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

        layoutH1 = QHBoxLayout()
        layoutH1.addLayout(layoutH1a)
        layoutH1.addLayout(layoutH1b)

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
        layoutV.addLayout(layoutH2)
        layoutV.setSpacing(3)
        self.setLayout(layoutV)

        self.setWindowTitle("SELECT CLASSIFIER")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

    @pyqtSlot(int)
    def classifierChanged(self, index):

        classifier = self.classifiers[index]
        self.editFilename.setText(classifier["Weights"])
        self.editNClasses.setText(str(classifier["Num. Classes"]))
        self.editClasses.setText(self.classes2str(classifier["Classes"]))
        self.editScale.setText(str(classifier["Scale"]))
        self.editAvgColor.setText(self.avgcolor2str(classifier["Average Norm."]))

    def classifier_name(self):

        return self.classifiers[self.comboClassifier.index()]['Classifier Name']

    def classes2str(self, classes_list):

        txt = str(classes_list)
        txt = txt.replace('[', '')
        txt = txt.replace(']', '')
        txt = txt.replace("'", '')
        return txt

    def avgcolor2str(self, avgcolor_list):

        txt = "R = {0:.2f}, G = {1:.2f}, B = {2:.2f} ".format(avgcolor_list[0]*255.0, avgcolor_list[1]*255.0, avgcolor_list[2]*255.0)
        return txt


