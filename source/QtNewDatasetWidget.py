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

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QCheckBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

class QtNewDatasetWidget(QWidget):

    def __init__(self, parent=None):
        super(QtNewDatasetWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        TEXT_SPACE = 100
        LINEWIDTH = 300

        ###########################################################

        self.lblDatasetFolder = QLabel("Dataset folder: ")
        self.lblDatasetFolder.setFixedWidth(TEXT_SPACE)
        self.lblDatasetFolder.setAlignment(Qt.AlignRight)
        self.lblSplitMode = QLabel("Dataset split:")
        self.lblSplitMode.setFixedWidth(TEXT_SPACE)
        self.lblSplitMode.setAlignment(Qt.AlignRight)

        layoutH0a = QVBoxLayout()
        layoutH0a.setAlignment(Qt.AlignRight)
        layoutH0a.addWidget(self.lblDatasetFolder)
        layoutH0a.addWidget(self.lblSplitMode)

        ###########################################################

        self.editDatasetFolder = QLineEdit("temp")
        self.editDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.comboSplitMode = QComboBox()
        self.comboSplitMode.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.comboSplitMode.setFixedWidth(LINEWIDTH)
        self.comboSplitMode.addItem("Uniform")
        self.comboSplitMode.addItem("Random")
        self.comboSplitMode.addItem("Biologically-inspired")

        layoutH0b = QVBoxLayout()
        layoutH0b.setAlignment(Qt.AlignLeft)
        layoutH0b.addWidget(self.editDatasetFolder)
        layoutH0b.addWidget(self.comboSplitMode)

        ###########################################################

        self.btnChooseDatasetFolder = QPushButton("...")
        self.btnChooseDatasetFolder.setMaximumWidth(20)
        self.btnChooseDatasetFolder.clicked.connect(self.chooseDatasetFolder)

        layoutH0c = QVBoxLayout()
        layoutH0c.addWidget(self.btnChooseDatasetFolder)
        layoutH0c.addStretch()

        layoutH1 = QHBoxLayout()
        layoutH1.addLayout(layoutH0a)
        layoutH1.addLayout(layoutH0b)
        layoutH1.addLayout(layoutH0c)

        ###########################################################

        self.checkOversampling = QCheckBox("Oversampling")
        self.checkOversampling.setFixedWidth(TEXT_SPACE)
        self.checkTiles = QCheckBox("Show exported tiles")

        layoutH2 = QHBoxLayout()
        layoutH2.setAlignment(Qt.AlignCenter)
        layoutH2.addStretch()
        layoutH2.addWidget(self.checkOversampling)
        layoutH2.addWidget(self.checkTiles)
        layoutH2.addStretch()

        ###########################################################

        layoutH3 = QHBoxLayout()

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnExport = QPushButton("Export")

        layoutH3.setAlignment(Qt.AlignRight)
        layoutH3.addStretch()
        layoutH3.addWidget(self.btnCancel)
        layoutH3.addWidget(self.btnExport)

        ###########################################################

        layoutV = QVBoxLayout()
        layoutV.addLayout(layoutH1)
        layoutV.addLayout(layoutH2)
        layoutV.addLayout(layoutH3)
        self.setLayout(layoutV)

        self.setWindowTitle("Export New Dataset - Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

    @pyqtSlot()
    def chooseDatasetFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose a Folder to Export the Dataset", "")
        if folderName:
            self.editDatasetFolder.setText(folderName)

    def getDatasetFolder(self):

        return self.editDatasetFolder.text()

    def getSplitMode(self):

        return self.comboSplitMode.currentText()

