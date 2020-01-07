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
from PyQt5.QtWidgets import QWidget, QCheckBox, QFileDialog, QSizePolicy, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

from source.Annotation import Annotation

class QtHistogramWidget(QWidget):

    def __init__(self, annotations, parent=None):
        super(QtHistogramWidget, self).__init__(parent)

        self.ann = annotations
        self.labels_info = annotations.labels_info

        self.checkBoxes = []  # list of QCheckBox

        self.setStyleSheet("background-color: rgba(60,60,65,100); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)

        # look for existing labels in annotations
        labels_set = set()
        for blob in self.ann.seg_blobs:
            labels_set.add(blob.class_name)

        labels_layout = QVBoxLayout()

        CLASS_LABELS_HEIGHT = 20
        LABELS_FOR_ROW = 4
        for i, label_name in enumerate(labels_set):

            chkBox = QCheckBox(label_name)
            chkBox.setChecked(True)

            btnC = QPushButton("")
            btnC.setFlat(True)

            color = self.labels_info[label_name]
            r = color[0]
            g = color[1]
            b = color[2]
            text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"

            btnC.setStyleSheet(text)
            btnC.setAutoFillBackground(True)
            btnC.setFixedWidth(CLASS_LABELS_HEIGHT)
            btnC.setFixedHeight(CLASS_LABELS_HEIGHT)

            if i % LABELS_FOR_ROW == 0:
                layout = QHBoxLayout()
                labels_layout.addLayout(layout)

            self.checkBoxes.append(chkBox)
            layout.addWidget(chkBox)
            layout.addWidget(btnC)
            layout.addSpacing(20)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnPreview = QPushButton("Preview")
        self.btnPreview.clicked.connect(self.preview)
        self.btnSaveAs = QPushButton("Save As")
        self.btnSaveAs.clicked.connect(self.saveas)

        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnCancel)
        buttons_layout.addWidget(self.btnPreview)
        buttons_layout.addWidget(self.btnSaveAs)


        self.lblPreview = QLabel("PREVIEW GOES HERE")
        self.lblPreview.setFixedWidth(500)
        self.lblPreview.setFixedHeight(300)

        layoutV = QVBoxLayout()
        layoutV.addWidget(self.lblPreview)
        layoutV.addLayout(labels_layout)
        layoutV.addLayout(buttons_layout)
        layoutV.setSpacing(3)
        self.setLayout(layoutV)

        self.setWindowTitle("CREATE AND EXPORT HISTOGRAM")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


    @pyqtSlot()
    def cancel(self):

        self.close()

    @pyqtSlot()
    def preview(self):

        print("Labels selected for the preview:")

        for checkbox in self.checkBoxes:

            if checkbox.isChecked():
                print(checkbox.text())

    @pyqtSlot()
    def saveas(self):
        """
        Save the current histograms.
        """

        filters = "PNG (*.png)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save as", "", filters)

        if filename:

            pass
