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

class QtTYNWidget(QWidget):

    def __init__(self, annotations, parent=None):
        super(QtTYNWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        TEXT_SPACE = 120

        ###########################################################

        self.lblDatasetFolder = QLabel("Dataset folder: ")
        self.lblDatasetFolder.setFixedWidth(TEXT_SPACE)
        self.lblDatasetFolder.setAlignment(Qt.AlignRight)

        self.lblClassifierName = QLabel("Classifier name:")
        self.lblClassifierName.setFixedWidth(TEXT_SPACE)
        self.lblDatasetFolder.setAlignment(Qt.AlignRight)

        self.lblNetworkName = QLabel("Network name:")
        self.lblNetworkName.setFixedWidth(TEXT_SPACE)
        self.lblNetworkName.setAlignment(Qt.AlignRight)

        self.lblEpochs = QLabel("Number of epochs:")
        self.lblEpochs.setFixedWidth(TEXT_SPACE)
        self.lblEpochs.setAlignment(Qt.AlignRight)

        self.lblLR = QLabel("Learning Rate: ")
        self.lblLR.setFixedWidth(TEXT_SPACE)
        self.lblLR.setAlignment(Qt.AlignRight)

        self.lblL2 = QLabel("L2 Regularization: ")
        self.lblL2.setFixedWidth(TEXT_SPACE)
        self.lblL2.setAlignment(Qt.AlignRight)

        self.lblBS = QLabel("Batch Size: ")
        self.lblBS.setFixedWidth(TEXT_SPACE)
        self.lblBS.setAlignment(Qt.AlignRight)

        layoutH1a = QVBoxLayout()
        layoutH1a.setAlignment(Qt.AlignRight)
        layoutH1a.addWidget(self.lblDatasetFolder)
        layoutH1a.addWidget(self.lblNetworkName)
        layoutH1a.addWidget(self.lblEpochs)
        layoutH1a.addWidget(self.lblLR)
        layoutH1a.addWidget(self.lblL2)
        layoutH1a.addWidget(self.lblBS)

        LINEWIDTH = 300
        self.editDatasetFolder = QLineEdit("temp")
        self.editDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editDatasetFolder.setFixedWidth(LINEWIDTH)
        self.editClassifierName = QLineEdit("myclassifier")
        self.editClassifierName.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editClassifierName.setFixedWidth(LINEWIDTH)
        self.editClassifierName.setReadOnly(False)
        self.editNetworkName = QLineEdit("mynetwork")
        self.editNetworkName.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editNetworkName.setFixedWidth(LINEWIDTH)
        self.editNetworkName.setReadOnly(False)
        self.editEpochs = QLineEdit("2")
        self.editEpochs.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editEpochs.setFixedWidth(LINEWIDTH)
        self.editEpochs.setReadOnly(False)
        self.editLR = QLineEdit("0.00005")
        self.editLR.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editLR.setReadOnly(False)
        self.editLR.setFixedWidth(LINEWIDTH)
        self.editL2 = QLineEdit("0.0005")
        self.editL2.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editL2.setReadOnly(False)
        self.editL2.setFixedWidth(LINEWIDTH)
        self.editBatchSize = QLineEdit("4")
        self.editBatchSize.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editBatchSize.setReadOnly(False)
        self.editBatchSize.setFixedWidth(LINEWIDTH)


        layoutH1b = QVBoxLayout()
        layoutH1b.setAlignment(Qt.AlignLeft)
        layoutH1b.addWidget(self.editDatasetFolder)
        layoutH1b.addWidget(self.editNetworkName)
        layoutH1b.addWidget(self.editEpochs)
        layoutH1b.addWidget(self.editLR)
        layoutH1b.addWidget(self.editL2)
        layoutH1b.addWidget(self.editBatchSize)

        layoutH1c = QVBoxLayout()
        self.btnChooseDatasetFolder = QPushButton("...")
        self.btnChooseDatasetFolder.setMaximumWidth(20)
        self.btnChooseDatasetFolder.clicked.connect(self.chooseDatasetFolder)
        layoutH1c.addWidget(self.btnChooseDatasetFolder)
        layoutH1c.addStretch()

        layoutH1 = QHBoxLayout()
        layoutH1.addLayout(layoutH1a)
        layoutH1.addLayout(layoutH1b)
        layoutH1.addLayout(layoutH1c)


        ###########################################################

        layoutH3 = QHBoxLayout()

        self.btnHelp = QPushButton("Help")
        self.btnHelp.clicked.connect(self.help)
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnTrain = QPushButton("Train")

        layoutH3.setAlignment(Qt.AlignRight)
        layoutH3.addStretch()
        layoutH3.addWidget(self.btnHelp)
        layoutH3.addWidget(self.btnCancel)
        layoutH3.addWidget(self.btnTrain)

        ###########################################################

        layoutV = QVBoxLayout()
        layoutV.addLayout(layoutH1)
        layoutV.addLayout(layoutH3)
        # layoutV.setSpacing(3)
        self.setLayout(layoutV)

        self.setWindowTitle("Train Your Network - Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


    @pyqtSlot()
    def chooseDatasetFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose a Folder to Export the Dataset", "")
        if folderName:
            self.editDatasetFolder.setText(folderName)

    @pyqtSlot()
    def help(self):
        pass

    def getDatasetFolder(self):

        return self.editDatasetFolder.text()

    def getEpochs(self):

        return int(self.editEpochs.text())

    def getLR(self):

        return float(self.editLR.text())

    def getWeightDecay(self):

        return float(self.editDecay.text())

