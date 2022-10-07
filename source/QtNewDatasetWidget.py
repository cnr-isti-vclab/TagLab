
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

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QCheckBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

class QtNewDatasetWidget(QWidget):

    closed = pyqtSignal()

    def __init__(self, export_area, parent=None):
        super(QtNewDatasetWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        TEXT_SPACE = 150
        LINEWIDTH = 300

        ###########################################################

        self.lblDatasetFolder = QLabel("Dataset folder: ")
        self.lblDatasetFolder.setFixedWidth(TEXT_SPACE)
        self.lblDatasetFolder.setAlignment(Qt.AlignRight)
        self.lblExportArea = QLabel("Area to export: ")
        self.lblExportArea.setFixedWidth(TEXT_SPACE)
        self.lblExportArea.setAlignment(Qt.AlignRight)

        self.lblSplitMode = QLabel("Dataset split:")
        self.lblSplitMode.setFixedWidth(TEXT_SPACE)
        self.lblSplitMode.setAlignment(Qt.AlignRight)
        self.lblTargetScale = QLabel("Target pixel size:")
        self.lblTargetScale.setFixedWidth(TEXT_SPACE)
        self.lblTargetScale.setAlignment(Qt.AlignRight)


        layoutH0a = QVBoxLayout()
        layoutH0a.setAlignment(Qt.AlignRight)
        layoutH0a.addWidget(self.lblDatasetFolder)
        layoutH0a.addWidget(self.lblExportArea)
        layoutH0a.addWidget(self.lblSplitMode)
        layoutH0a.addWidget(self.lblTargetScale)

        ###########################################################

        self.editDatasetFolder = QLineEdit("")
        self.editDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.editExportArea = QLineEdit("")
        self.editExportArea.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editExportArea.setMinimumWidth(LINEWIDTH)
        self.comboSplitMode = QComboBox()
        self.comboSplitMode.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.comboSplitMode.setFixedWidth(LINEWIDTH)
        self.comboSplitMode.addItem("Uniform (vertical)")
        self.comboSplitMode.addItem("Uniform (horizontal)")
        # self.comboSplitMode.addItem("Random")
        self.comboSplitMode.addItem("Biologically-inspired")
        self.editTargetScale = QLineEdit("1.0")
        self.editTargetScale .setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editTargetScale .setMinimumWidth(LINEWIDTH)

        self.area_to_export = [0, 0, 0, 0]
        self.setAreaToExport(export_area[0], export_area[1], export_area[2], export_area[3])

        layoutH0b = QVBoxLayout()
        layoutH0b.setAlignment(Qt.AlignLeft)
        layoutH0b.addWidget(self.editDatasetFolder)
        layoutH0b.addWidget(self.editExportArea)
        layoutH0b.addWidget(self.comboSplitMode)
        layoutH0b.addWidget(self.editTargetScale)

        ###############################################################

        self.btnChooseDatasetFolder = QPushButton("...")
        self.btnChooseDatasetFolder.clicked.connect(self.chooseDatasetFolder)

        self.btnChooseExportArea = QPushButton()
        exportAreaIcon = QIcon("icons\\select_area.png")
        self.btnChooseExportArea.setIcon(exportAreaIcon)

        layoutH0c = QVBoxLayout()
        layoutH0c.addWidget(self.btnChooseDatasetFolder)
        layoutH0c.addWidget(self.btnChooseExportArea)
        layoutH0c.addStretch()

        layoutH1 = QHBoxLayout()
        layoutH1.addLayout(layoutH0a)
        layoutH1.addLayout(layoutH0b)
        layoutH1.addLayout(layoutH0c)

        ###########################################################

        # self.checkOversampling = QCheckBox("Oversampling")
        self.checkTiles = QCheckBox("Show Exported Tiles")
        self.checkCoco = QCheckBox("Export In Coco Panoptic Format")

        layoutH2 = QHBoxLayout()
        layoutH2.addWidget(self.checkTiles)
        layoutH2.addWidget(self.checkCoco)
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

        self.setWindowTitle("Export New Training Dataset - Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

    @pyqtSlot()
    def chooseDatasetFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose a Folder to Export the Dataset", "")
        if folderName:
            self.editDatasetFolder.setText(folderName)

    def closeEvent(self, event):
        self.closed.emit()
        super(QtNewDatasetWidget, self).closeEvent(event)

    def setAreaToExport(self, top, left, width, height):

        txt = str(int(left)) + ',' + str(int(top)) + ',' + str(int(width)) + ',' + str(int(height))
        self.area_to_export = [top, left, width, height]
        self.editExportArea.setText(txt)

    def getAreaToExport(self):

        return self.area_to_export

    def getDatasetFolder(self):

        return self.editDatasetFolder.text()

    def getSplitMode(self):

        return self.comboSplitMode.currentText()

    def getTargetScale(self):

        return float(self.editTargetScale.text())


