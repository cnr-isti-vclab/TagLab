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
from source.Grid import Grid


class QtGridWidget(QWidget):
    accepted = pyqtSignal()

    def __init__(self, viewerplus, parent=None):
        super(QtGridWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        self.viewerplus = viewerplus
        self.pixels_to_meters = viewerplus.image.pixelSize() / 1000.0
        self.width_m = self.pixelsToMeters(viewerplus.image.width)
        self.height_m = self.pixelsToMeters(viewerplus.image.height)

        self.posx_m = 0.0
        self.posy_m = 0.0

        self.grid = Grid()

        TEXT_WIDTH = 100

        self.fields = {
            "width": {"name": "Width (m):", "value": str(self.width_m), "place": "Width of your grid (m)", "width": 200 ,"action": None},

            "height": {"name": "Height (m):", "value": str(self.height_m), "place": "Height of your grid (m)", "width": 200, "action": None},

            "number_cell_y": {"name": "Rows:", "value": "8", "place": "Number of horizontal cells", "width": 200, "action": None},

            "number_cell_x": {"name": "Columns :", "value": "8", "place": "Number of vertical cells", "width": 200,  "action": None},

            "position": {"name": "Position:", "value": "(0,0)", "place": "Pick the top-left point", "width": 200, "action": self.toggleSetPosition}
        }
        self.data = {}

        layoutV = QVBoxLayout()

        for key, field in self.fields.items():
            label = QLabel(field["name"])
            label.setFixedWidth(TEXT_WIDTH)
            label.setAlignment(Qt.AlignRight)
            label.setMinimumWidth(TEXT_WIDTH)

            edit = QLineEdit(field["value"])
            edit.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
            edit.setMinimumWidth(field["width"])
            edit.setPlaceholderText(field["place"])
            edit.setMaximumWidth(20)
            field["edit"] = edit

            button = None
            if field["action"] is not None:
                button = QPushButton("")
                button.setFixedWidth(30)
                button.setFixedHeight(30)
                field["button"] = button
                button.setCheckable(True)
                button.setChecked(False)
                button.clicked.connect(field["action"])

            layout = QHBoxLayout()
            layout.setAlignment(Qt.AlignLeft)
            layout.addWidget(label)
            layout.addWidget(edit)
            if button is not None:
                layout.addWidget(button)
            layout.addStretch()
            layoutV.addLayout(layout)


        WorkingAreaIcon = QIcon("icons\\corner.png")
        self.fields["position"]["button"].setIcon(WorkingAreaIcon)

        buttons_layout = QHBoxLayout()

        self.btnCancel = QPushButton("Cancel")

        self.btnApply = QPushButton("Apply")
        self.btnApply.clicked.connect(self.apply)

        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnCancel)
        buttons_layout.addWidget(self.btnApply)

        ###########################################################

        layoutV.addLayout(buttons_layout)
        self.setLayout(layoutV)

        self.setWindowTitle("Grid Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint| Qt.WindowTitleHint)

        self.grid.setScene(self.viewerplus.scene)
        self.setGrid()

        # connections
        self.fields["width"]["edit"].editingFinished.connect(self.setGrid)
        self.fields["height"]["edit"].editingFinished.connect(self.setGrid)
        self.fields["number_cell_x"]["edit"].editingFinished.connect(self.setGrid)
        self.fields["number_cell_y"]["edit"].editingFinished.connect(self.setGrid)

    def pixelsToMeters(self, px):
        return round(px * self.pixels_to_meters, 3)

    def metersToPixels(self, m):
        return round(m / self.pixels_to_meters)

    @pyqtSlot()
    def setGrid(self):
        for key, field in self.fields.items():
            self.data[key] = field["edit"].text()

        w = self.metersToPixels(float(self.data["width"]))
        h = self.metersToPixels(float(self.data["height"]))
        self.grid.undrawGrid()
        self.grid.setGrid(w, h, int(self.data["number_cell_x"]), int(self.data["number_cell_y"]))
        self.grid.drawGrid()

    @pyqtSlot(float, float)
    def setGridPosition(self, x, y):

        xm = self.pixelsToMeters(x)
        ym = self.pixelsToMeters(y)

        txt = "({:.3f},{:.3f})".format(xm, ym)
        self.fields["position"]["edit"].setText(txt)

        self.grid.setGridPosition(x, y)

    @pyqtSlot()
    def toggleSetPosition(self):

        button = self.fields["position"]["button"]

        if button.isChecked():
            self.viewerplus.leftMouseButtonPressed[float, float].connect(self.setGridPosition)
        else:
            self.viewerplus.leftMouseButtonPressed[float, float].disconnect()


    @pyqtSlot()
    def apply(self):

        button = self.fields["position"]["button"]
        if button.isChecked():
             self.viewerplus.leftMouseButtonPressed[float, float].disconnect()
        self.accepted.emit()
        self.close()


