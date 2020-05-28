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

class QtMapSettingsWidget(QWidget):

    def __init__(self, parent=None):
        super(QtMapSettingsWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        TEXT_SPACE = 100



        ###########################################################

        layoutH0 = QHBoxLayout()

        self.lblMapFile = QLabel("Map File: ")
        self.lblMapFile.setFixedWidth(TEXT_SPACE)
        self.lblMapFile.setAlignment(Qt.AlignRight)
        self.lblMapFile.setMinimumWidth(150)

        self.editMapFile = QLineEdit("map.png")
        self.editMapFile.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editMapFile.setMinimumWidth(300)
        self.editMapFile.setPlaceholderText("map.png")
        self.btnChooseMapFile = QPushButton("...")
        self.btnChooseMapFile.setMaximumWidth(20)
        self.btnChooseMapFile.clicked.connect(self.chooseMapFile)

        layoutH0.setAlignment(Qt.AlignLeft)
        layoutH0.addWidget(self.lblMapFile)
        layoutH0.addWidget(self.editMapFile)
        layoutH0.addWidget(self.btnChooseMapFile)
        layoutH0.addStretch()

        ###########################################################

        layoutH03D = QHBoxLayout()

        self.lbl3DMapFile = QLabel("3D Map File: ")
        self.lbl3DMapFile.setFixedWidth(TEXT_SPACE)
        self.lbl3DMapFile.setAlignment(Qt.AlignRight)
        self.lbl3DMapFile.setMinimumWidth(150)

        self.edit3DMapFile = QLineEdit()
        self.edit3DMapFile.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit3DMapFile.setMinimumWidth(300)
        self.btnChoose3DMapFile = QPushButton("...")
        self.btnChoose3DMapFile.setMaximumWidth(20)
        self.btnChoose3DMapFile.clicked.connect(self.choose3DMapFile)

        layoutH03D.setAlignment(Qt.AlignLeft)
        layoutH03D.addWidget(self.lbl3DMapFile)
        layoutH03D.addWidget(self.edit3DMapFile)
        layoutH03D.addWidget(self.btnChoose3DMapFile)
        layoutH03D.addStretch()

        ###########################################################

        layoutH1 = QHBoxLayout()

        self.lblAcquisitionDate = QLabel("Acquisition Date: ")
        self.lblAcquisitionDate.setFixedWidth(TEXT_SPACE)
        self.lblAcquisitionDate.setAlignment(Qt.AlignRight)
        self.lblAcquisitionDate.setMinimumWidth(150)

        self.editAcquisitionDate = QLineEdit()
        self.editAcquisitionDate.setPlaceholderText("YYYY-MM-DD")
        self.editAcquisitionDate.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editAcquisitionDate.setMinimumWidth(150)

        layoutH1.setAlignment(Qt.AlignLeft)
        layoutH1.addWidget(self.lblAcquisitionDate)
        layoutH1.addWidget(self.editAcquisitionDate)
        layoutH1.addStretch()

        ###########################################################

        layoutH2 = QHBoxLayout()

        self.lblScaleFactor = QLabel("Px-to-mm: ")
        self.lblScaleFactor.setFixedWidth(TEXT_SPACE)
        self.lblScaleFactor.setAlignment(Qt.AlignRight)
        self.lblScaleFactor.setMinimumWidth(150)

        self.editScaleFactor = QLineEdit("1.0")
        self.editScaleFactor.setMinimumWidth(150)
        self.editScaleFactor.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        layoutH2.setAlignment(Qt.AlignLeft)
        layoutH2.addWidget(self.lblScaleFactor)
        layoutH2.addWidget(self.editScaleFactor)
        layoutH2.addStretch()

        ###########################################################

        layoutH3 = QHBoxLayout()

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnApply = QPushButton("Apply")

        layoutH3.setAlignment(Qt.AlignRight)
        layoutH3.addStretch()
        layoutH3.addWidget(self.btnCancel)
        layoutH3.addWidget(self.btnApply)

        ###########################################################

        layoutV = QVBoxLayout()
        layoutV.addLayout(layoutH0)
        layoutV.addLayout(layoutH03D)
        layoutV.addLayout(layoutH1)
        layoutV.addLayout(layoutH2)
        layoutV.addLayout(layoutH3)
        # layoutV.setSpacing(3)
        self.setLayout(layoutV)

        self.setWindowTitle("MAP SETTINGS")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


    @pyqtSlot()
    def chooseMapFile(self):

        filters = "Image (*.png *.jpg)"
        fileName, _ = QFileDialog.getOpenFileName(self, "Input Map File", "", filters)
        if fileName:
            self.editMapFile.setText(fileName)

    @pyqtSlot()
    def choose3DMapFile(self):

        filters = "Image (*.png *.tif *.tiff)"
        fileName, _ = QFileDialog.getOpenFileName(self, "Input 3D Map File", "", filters)
        if fileName:
            self.edit3DMapFile.setText(fileName)


