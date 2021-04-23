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
# GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

import os

from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QImageReader, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout
from source import utils
from source.Grid import Grid


class QtGridWidget(QWidget):
    accepted = pyqtSignal()

    def __init__(self, viewerplus, parent=None):
        super(QtGridWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        self.grid = Grid(viewerplus)

        TEXT_SPACE = 100

        self.fields = {
            "width": {"name": "Width:", "value": "10000", "place": "Width of your grid (m)", "width": 300 ,"action": None},

            "height": {"name": "Height:", "value": "10000", "place": "Height of your grid (m)", "width": 300, "action": None},

            "number_cell_y": {"name": "Rows:", "value": "8", "place": "Number of horizontal cells", "width": 300, "action": None},

            "number_cell_x": {"name": "Columns :", "value": "8", "place": "Number of vertical cells", "width": 300,  "action": None},

            "Position": {"name": "Position:", "value": " ", "place": "(0,0)", "width": 150,
                              "action": self.setPosition}

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
                button = QPushButton("")
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


        WorkingAreaIcon = QIcon("icons\\select_area.png")
        self.fields["Position"]["button"].setIcon(WorkingAreaIcon)

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

        self.setWindowTitle("Grid Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.setGrid()
        self.fields["width"]["edit"].textChanged.connect(self.setGrid)
        self.fields["height"]["edit"].textChanged.connect(self.setGrid)
        self.fields["number_cell_x"]["edit"].textChanged.connect(self.setGrid)
        self.fields["number_cell_y"]["edit"].textChanged.connect(self.setGrid)

    @pyqtSlot()
    def setGrid(self):
        for key, field in self.fields.items():
            self.data[key] = field["edit"].text()
        self.grid.setGrid(int(self.data["width"]), int(self.data["height"]), int(self.data["number_cell_x"]), int(self.data["number_cell_y"]))




    @pyqtSlot()
    def setPosition(self):
        pass

    @pyqtSlot()
    def accept(self):

        for key, field in self.fields.items():
            self.data[key] = field["edit"].text()

        self.accepted.emit()
        self.close()

