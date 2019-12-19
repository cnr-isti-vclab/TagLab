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

class QtExportWidget(QWidget):

    def __init__(self, map, annotations, parent=None):
        super(QtExportWidget, self).__init__(parent)

        self.ann = annotations
        self.map = map

        self.setStyleSheet("background-color: rgba(60,60,65,100); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        layoutH0 = QHBoxLayout()
        self.lblFolder = QLabel("Folder name: ")


        self.editFoldername = QLineEdit("exports")


        self.editFoldername.setMinimumWidth(300)
        self.btnChooseFolder = QPushButton("...")
        self.btnChooseFolder.setMaximumWidth(20)
        self.btnChooseFolder.clicked.connect(self.chooseFolder)

        layoutH0.setAlignment(Qt.AlignLeft)
        layoutH0.addStretch()
        layoutH0.addWidget(self.lblFolder)
        layoutH0.addWidget(self.editFoldername)
        layoutH0.addWidget(self.btnChooseFolder)

        layoutH1 = QHBoxLayout()

        self.lblFilename = QLabel("File name: ")
        self.editFilename = QLineEdit("table.csv")
        self.editFilename.setMinimumWidth(300)
        self.btnChooseFile = QPushButton("...")
        self.btnChooseFile.setMaximumWidth(20)
        self.btnChooseFile.clicked.connect(self.chooseFile)

        layoutH1.setAlignment(Qt.AlignLeft)
        layoutH1.addStretch()
        layoutH1.addWidget(self.lblFilename)
        layoutH1.addWidget(self.editFilename)
        layoutH1.addWidget(self.btnChooseFile)

        layoutH2 = QHBoxLayout()

        self.lblSaveAs = QLabel("Save As: ")

        self.comboSaveAs = QComboBox()
        self.comboSaveAs.setMinimumWidth(300)
        self.comboSaveAs.addItem("Data Table - Scripps Data Format")
        self.comboSaveAs.addItem("Images - Scripps Data Format")
        self.comboSaveAs.currentIndexChanged.connect(self.formatChanged)

        layoutH2.setAlignment(Qt.AlignLeft)
        layoutH2.addStretch()
        layoutH2.addWidget(self.lblSaveAs)
        layoutH2.addWidget(self.comboSaveAs)
        layoutH2.addStretch()

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnExport = QPushButton("Export")
        self.btnExport.clicked.connect(self.export)

        layoutH3 = QHBoxLayout()
        layoutH3.setAlignment(Qt.AlignRight)
        layoutH3.addStretch()
        layoutH3.addWidget(self.btnCancel)
        layoutH3.addWidget(self.btnExport)

        layoutV = QVBoxLayout()
        layoutV.addLayout(layoutH0)
        layoutV.addLayout(layoutH1)
        layoutV.addLayout(layoutH2)
        layoutV.addLayout(layoutH3)
        layoutV.setSpacing(3)
        self.setLayout(layoutV)

        self.setWindowTitle("EXPORT DATA")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

    @pyqtSlot()
    def chooseFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose Folder", "")

        if folderName:
            self.editFoldername.setText(folderName)

    @pyqtSlot()
    def chooseFile(self):

        index = self.comboSaveAs.currentIndex()

        filters = "All Files (*)"
        if index == 0:
            filters = "CSV (*.csv)"
        elif index == 1:
            filters = "PNG (*.png)"
        elif index == 2:
            pass

        fileName, _ = QFileDialog.getSaveFileName(self, "Input File", "", filters)
        if fileName:
            basename = os.path.basename(fileName)
            self.editFilename.setText(basename)

    @pyqtSlot(int)
    def formatChanged(self, index):

        if index == 0:

            # DATA TABLE - SCRIPPS DATA FORMAT
            self.editFilename.setText("table.csv")

        elif index == 1:

            # IMAGE DATA - SCRIPPS DATA FORMAT
            self.editFilename.setText("map.png")

        elif index == 2:
            pass


    @pyqtSlot()
    def export(self):

        index = self.comboSaveAs.currentIndex()

        if index == 0:

            # DATA TABLE - SCRIPPS DATA FORMAT
            fullname = os.path.join(self.editFoldername.text(), self.editFilename.text())
            self.ann.export_data_table_for_Scripps(fullname)

        elif index == 1:

            # IMAGE DATA - SCRIPPS DATA FORMAT
            fullname = os.path.join(self.editFoldername.text(), self.editFilename.text())
            self.ann.export_image_data_for_Scripps(self.map, fullname)

        elif index == 2:

            pass

        print("DATA EXPORTED !!")

        self.close()