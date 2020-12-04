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

        TEXT_SPACE = 180

        ###### Labels

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

        layoutLabels = QVBoxLayout()
        layoutLabels.setAlignment(Qt.AlignRight)
        layoutLabels.addWidget(self.lblDatasetFolder)
        layoutLabels.addWidget(self.lblNetworkName)
        layoutLabels.addWidget(self.lblEpochs)
        layoutLabels.addWidget(self.lblLR)
        layoutLabels.addWidget(self.lblL2)
        layoutLabels.addWidget(self.lblBS)

        ##### Edits

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

        layoutEdits = QVBoxLayout()
        layoutEdits.setAlignment(Qt.AlignLeft)
        layoutEdits.addWidget(self.editDatasetFolder)
        layoutEdits.addWidget(self.editNetworkName)
        layoutEdits.addWidget(self.editEpochs)
        layoutEdits.addWidget(self.editLR)
        layoutEdits.addWidget(self.editL2)
        layoutEdits.addWidget(self.editBatchSize)

        ###### Right buttons

        self.btnChooseDatasetFolder = QPushButton("...")
        self.btnChooseDatasetFolder.setMaximumWidth(20)
        self.btnChooseDatasetFolder.clicked.connect(self.chooseDatasetFolder)
        layoutRightButtons = QVBoxLayout()
        layoutRightButtons.addWidget(self.btnChooseDatasetFolder)
        layoutRightButtons.addStretch()

        ##### Help (on the right)

        helpTxt = "Train-Your-Network allows to train a DeepLab V3+ with a given dataset.\
                   The dataset must be exported with the <em>Export New Dataset</em> option.\
                   It is recommended to not change the default training parameters (learning rate and regularization).\
                   Increase the <em>Batch Size</em> requires a lot of GPU memory."

        self.labelTopHelp = QLabel(helpTxt)
        self.labelTopHelp.setWordWrap(True)
        self.labelTopHelp.setMaximumWidth(550)
        self.labelTopHelp.setMaximumHeight(300)

        TEXT_SPACE = 400
        self.lblH1 = QLabel("Folder containing the exported tiles")
        self.lblH1.setWordWrap(True)
        self.lblH1.setFixedWidth(TEXT_SPACE)
        self.lblH2 = QLabel("Name of the network (saved network gets this name)")
        self.lblH2.setWordWrap(True)
        self.lblH2.setFixedWidth(TEXT_SPACE)
        self.lblH3 = QLabel("Number of epochs to use for the training.")
        self.lblH3.setWordWrap(True)
        self.lblH3.setFixedWidth(TEXT_SPACE)
        self.lblH4 = QLabel("Something to say?")
        self.lblH4.setWordWrap(True)
        self.lblH4.setFixedWidth(TEXT_SPACE)
        self.lblH5 = QLabel("Something to say?")
        self.lblH5.setWordWrap(True)
        self.lblH5.setFixedWidth(TEXT_SPACE)
        self.lblH6 = QLabel("The effective batch size is multiplied by 4.")
        self.lblH6.setWordWrap(True)
        self.lblH6.setFixedWidth(TEXT_SPACE)

        layoutRightHelp = QVBoxLayout()
        layoutRightHelp.addWidget(self.lblH1)
        layoutRightHelp.addWidget(self.lblH2)
        layoutRightHelp.addWidget(self.lblH3)
        layoutRightHelp.addWidget(self.lblH4)
        layoutRightHelp.addWidget(self.lblH5)
        layoutRightHelp.addWidget(self.lblH6)

        ##### Main layout

        self.layoutMain = QHBoxLayout()
        self.layoutMain.addLayout(layoutLabels)
        self.layoutMain.addLayout(layoutEdits)
        self.layoutMain.addLayout(layoutRightButtons)
        self.layoutMain.addLayout(layoutRightHelp)

        ###########################################################

        self.btnHelp = QPushButton("Help")
        self.btnHelp.clicked.connect(self.help)
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnTrain = QPushButton("Train")

        layoutBottomButtons = QHBoxLayout()
        layoutBottomButtons.setAlignment(Qt.AlignRight)
        layoutBottomButtons.addStretch()
        layoutBottomButtons.addWidget(self.btnHelp)
        layoutBottomButtons.addWidget(self.btnCancel)
        layoutBottomButtons.addWidget(self.btnTrain)

        ###########################################################

        layoutFinal = QVBoxLayout()
        layoutFinal.addWidget(self.labelTopHelp)
        layoutFinal.addLayout(self.layoutMain)
        layoutFinal.addLayout(layoutBottomButtons)
        self.setLayout(layoutFinal)
        self.labelTopHelp.setVisible(False)
        self.lblH1.setVisible(False)
        self.lblH2.setVisible(False)
        self.lblH3.setVisible(False)
        self.lblH4.setVisible(False)
        self.lblH5.setVisible(False)
        self.lblH6.setVisible(False)

        self.setWindowTitle("Train Your Network - Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.w = 0
        self.h = 0

    @pyqtSlot()
    def chooseDatasetFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose a Folder to Export the Dataset", "")
        if folderName:
            self.editDatasetFolder.setText(folderName)

    @pyqtSlot()
    def help(self):

        if self.labelTopHelp.isVisible():
            self.lblH1.hide()
            self.lblH2.hide()
            self.lblH3.hide()
            self.lblH4.hide()
            self.lblH5.hide()
            self.lblH6.hide()
            self.labelTopHelp.hide()
            self.setMaximumWidth(self.w)
            self.setMaximumHeight(self.h)
            self.adjustSize()
        else:
            self.w = self.width()
            self.h = self.height()
            self.lblH1.show()
            self.lblH2.show()
            self.lblH3.show()
            self.lblH4.show()
            self.lblH5.show()
            self.lblH6.show()
            self.labelTopHelp.show()

    def getDatasetFolder(self):

        return self.editDatasetFolder.text()

    def getEpochs(self):

        return int(self.editEpochs.text())

    def getLR(self):

        return float(self.editLR.text())

    def getWeightDecay(self):

        return float(self.editL2.text())

    def getBatchSize(self):

        return int(self.editBatchSize.text())

