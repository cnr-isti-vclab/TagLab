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
from PyQt5.QtGui import QImage, QImageReader, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source import genutils

class QtMapSettingsWidget(QWidget):

    accepted = pyqtSignal()
    def __init__(self, parent=None):
        super(QtMapSettingsWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)


        TEXT_SPACE = 100

        self.fields = {
            "name"            : {"name": "Map Name:"        , "value": "", "place": "Name of the map"        , "width": 300, "action": None },
            "rgb_filename"    : {"name": "RGB Image:"       , "value": "", "place": "Path of the rgb image"  , "width": 300, "action": self.chooseMapFile },
            "depth_filename"  : {"name": "Depth Image:"     , "value": "", "place": "Path of the depth image", "width": 300, "action": self.chooseDEMFile },
            "acquisition_date": {"name": "Acquisition Date:", "value": "", "place": "YYYY-MM-DD"             , "width": 150, "action": None },
            "px_to_mm"        : {"name": "Pixel size (mm):"        , "value": "", "place": ""                    , "width": 150, "action": None }
        }
        self.data = {}

        layoutV = QVBoxLayout()

        for key, field in self.fields.items():
            label = QLabel(field["name"])
            label.setFixedWidth(TEXT_SPACE)
            label.setAlignment(Qt.AlignRight)
            label.setMinimumWidth(150)

            edit = QLineEdit(field["value"])
            edit.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
            edit.setMinimumWidth(field["width"])
            edit.setPlaceholderText(field["place"])
            edit.setMaximumWidth(20)
            field["edit"] = edit

            button = None
            if field["action"] is not None:
                button = QPushButton("...")
                button.setMaximumWidth(20)
                button.clicked.connect(field["action"])
                field["button"] = button

            layout = QHBoxLayout()
            layout.setAlignment(Qt.AlignLeft)
            layout.addWidget(label)
            layout.addWidget(edit)
            if button is not None:
                layout.addWidget(button)
            layout.addStretch()
            layoutV.addLayout(layout)

        buttons_layout = QHBoxLayout()

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnApply = QPushButton("Apply")
        self.btnApply.clicked.connect(self.accept)

        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnCancel)
        buttons_layout.addWidget(self.btnApply)

        ###########################################################

        layoutV.addLayout(buttons_layout)
        self.setLayout(layoutV)

        self.setWindowTitle("Map Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

    def disableRGBloading(self):
        self.fields["rgb_filename"]["edit"].setEnabled(False)
        self.fields["rgb_filename"]["button"].hide()

    def enableRGBloading(self):
        self.fields["rgb_filename"]["edit"].setEnabled(True)
        self.fields["rgb_filename"]["button"].show()

    @pyqtSlot()
    def chooseMapFile(self):

        filters = "Image (*.png *.jpg *.jpeg *.tif *.tiff)"
        fileName, _ = QFileDialog.getOpenFileName(self, "Input Map File", "", filters)
        if fileName:
            self.fields["rgb_filename"]["edit"].setText(fileName)

    @pyqtSlot()
    def chooseDEMFile(self):

        filters = "Image (*.png *.tif *.tiff)"
        fileName, _ = QFileDialog.getOpenFileName(self, "Input 3D Map File", "", filters)
        if fileName:
            self.fields["depth_filename"]["edit"].setText(fileName)

    @pyqtSlot()
    def accept(self):

        for key, field in self.fields.items():
            self.data[key] = field["edit"].text()

        if self.data["name"] == "":
            msgBox = QMessageBox()
            msgBox.setText("Please, enter a name for the map.")
            msgBox.exec()
            return

        # check if the RGB map file exists
        rgb_filename = self.data['rgb_filename']
        if not os.path.exists(rgb_filename):
            msgBox = QMessageBox()
            msgBox.setText("The RGB image file does not seems to exist.")
            msgBox.exec()
            return

        # check if the depth map file exists
        depth_filename = self.data['depth_filename']
        if not os.path.exists(rgb_filename):
            msgBox = QMessageBox()
            msgBox.setText("The depth map file does not seems to exist.")
            msgBox.exec()
            return

        # check validity of the acquisition date
        txt = self.data["acquisition_date"]
        if not genutils.isValidDate(txt):
            msgBox = QMessageBox()
            msgBox.setText("Invalid date format. Please, enter the acquisition date as YYYY-MM-DD.")
            msgBox.exec()
            return

        # TODO: redundat check, remove it ?
        image_reader = QImageReader(rgb_filename)
        size = image_reader.size()
        if size.width() > 32767 or size.height() > 32767:
            msgBox = QMessageBox()
            msgBox.setText("The image is too big. TagLab is limited to 32767x32767 pixels.")
            msgBox.exec()
            return

        self.accepted.emit()
        self.close()

