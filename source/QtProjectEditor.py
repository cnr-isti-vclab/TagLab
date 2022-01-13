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


from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal, QEvent
from PyQt5.QtWidgets import QGridLayout, QWidget, QScrollArea,QGroupBox, QColorDialog, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout, QTextEdit, QTableWidget, QTableWidgetItem, QFrame
import os, json, re
from source.RegionAttributes import RegionAttributes
from copy import deepcopy

class QtProjectEditor(QWidget):
    closed = pyqtSignal()
    def __init__(self, project, parent=None):
        super(QtProjectEditor, self).__init__(parent)
        self.project = project

        self.setStyleSheet('.map-item { border: 1px solid grey } ')

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        self.area = QScrollArea()
        v = QVBoxLayout()
        self.area.setLayout(v)
        layout.addWidget(self.area)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        btn_apply = QPushButton("Close")
        btn_apply.clicked.connect(self.close)

        layout.addLayout(buttons_layout)
#
        self.setLayout(layout)

        self.setWindowTitle("Maps editor")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.fillMaps()

    @pyqtSlot()
    def fillMaps(self):
        layout = self.area.layout()
        for i in reversed(range(layout.count())): 
            child = layout.itemAt(i)
            widget = child.widget()
            layout.removeItem(child)
            if widget:
                widget.setParent(None)

#            child.setParent(None)

        for img in self.project.images:
            map_widget = QWidget()
            map_widget.setProperty("class", "map-item");
            map_widget.setMaximumHeight(100)
            layout.addWidget(map_widget)
            
            map_layout = QHBoxLayout()
            map_layout.addWidget(QLabel(img.acquisition_date + ": " + img.name))
            map_widget.setLayout(map_layout)

            edit = QPushButton("edit")
            edit.setMaximumWidth(80)
            edit.clicked.connect(lambda x, img=img: self.editMap(img))
            map_layout.addWidget(edit)

            delete = QPushButton("delete")
            delete.setMaximumWidth(80)
            delete.clicked.connect(lambda x, img=img: self.deleteMap(img))
            map_layout.addWidget(delete)

        layout.addStretch()
            #self.mapList.addItem()

    def editMap(self, img):
        self.parent().editMapSettingsImage(img)

        # mapWidget actually disconnects everything before show
        self.parent().mapWidget.accepted.connect(self.fillMaps)

    def deleteMap(self, img):

        reply = QMessageBox.question(self, "Deleting map",
                                     "About to delete map: " + img.name + ". Are you sure?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self.parent().deleteImage(img)
        self.fillMaps()

    def closeEvent(self, event):
        self.closed.emit()