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

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnExport = QPushButton("Apply")
        self.btnExport.clicked.connect(self.export)

        layoutH2 = QHBoxLayout()
        layoutH2.setAlignment(Qt.AlignRight)
        layoutH2.addStretch()
        layoutH2.addWidget(self.btnCancel)
        layoutH2.addWidget(self.btnExport)

        layoutV = QVBoxLayout()
        layoutV.addLayout(layoutH0)
        #layoutV.addLayout(layoutH1)
        layoutV.addLayout(layoutH2)
        layoutV.setSpacing(3)
        self.setLayout(layoutV)

        self.setWindowTitle("SELECT CLASSIFIER")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

    @pyqtSlot(int)
    def classifierChanged(self, index):

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