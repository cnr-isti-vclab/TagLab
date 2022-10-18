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


from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal, QEvent, QDate
from PyQt5.QtWidgets import QGridLayout, QWidget, QScrollArea,QGroupBox, QColorDialog, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout, QTextEdit, QTableWidget, QTableWidgetItem, QFrame
import rasterio as rio
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
        self.setMinimumWidth(800)
        self.setMinimumHeight(300)

        self.area = QScrollArea()
        self.area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.area.setMaximumHeight(250)
        widget = QWidget()
        widget.setLayout(QVBoxLayout())
        widget.setMinimumHeight(150)
        self.area.setWidget(widget)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(btn_close)

        layout = QVBoxLayout()
        layout.addWidget(self.area)
        layout.addLayout(buttons_layout)
#
        self.setLayout(layout)

        self.setWindowTitle("Maps editor")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.fillMaps()

    @pyqtSlot()
    def fillMaps(self):

        layout = QVBoxLayout()

        for img in self.project.images:
            map_widget = QWidget()

            self.text = QTextEdit()
            map_widget.setProperty("class", "map-item")
            self.text.setMinimumWidth(1000)

            date = self.convertDate(img.acquisition_date)
            day = date.day()
            year = date.year()
            self.text.setHtml(
            "<b>Map size in pixels</b>" + " : " + "(" + str(img.width) + "," + str(img.height) + ")")
            self.text.append("<b>Map pixel size in mm</b>" + " : " + str(img.map_px_to_mm_factor))
            self.text.append("<b>Map acquisition date</b>" + " : " + str(day) + " " + date.longMonthName(date.month()) + " " +  str(year))

            if img.georef_filename == "":
                self.text.append("<b>Map georeference information</b>" + " : None.")
            else:
                self.text.append("<b>Map georeference information</b>" + " : <br><pre>" + self.georefAvailable(
                img.georef_filename) + "</pre>")

            self.text.append("<b>DEM availability</b>" + " : " + str(self.boolToWord(len(img.channels)>1)))
            self.text.document().adjustSize()  # calculate size

            self.text.setMinimumHeight(self.text.document().size().height())

            map_layout = QHBoxLayout()
            map_layout.addWidget(QLabel("<b>Map name</b>" + " : " + img.name))

            edit = QPushButton("edit")
            edit.setMaximumWidth(80)
            edit.clicked.connect(lambda x, img=img: self.editMap(img))
            map_layout.addWidget(edit)

            #crop = QPushButton("crop")
            #crop.setMaximumWidth(80)
            #crop.clicked.connect(lambda x, img=img: self.cropMap(img))
            #map_layout.addWidget(crop)

            delete = QPushButton("delete")
            delete.setMaximumWidth(80)
            delete.clicked.connect(lambda x, img=img: self.deleteMap(img))
            map_layout.addWidget(delete)

            info_layout = QVBoxLayout()
            info_layout.addLayout(map_layout)
            info_layout.addWidget(self.text)

            map_widget.setLayout(info_layout)
            layout.addWidget(map_widget)

        # update the scroll area
        widget_to_scroll = QWidget()
        widget_to_scroll.setLayout(layout)
        self.area.setWidget(widget_to_scroll)


    def editMap(self, img):
        self.parent().editMapSettingsImage(img)

        # mapWidget actually disconnects everything before show
        self.parent().mapWidget.accepted.connect(self.fillMaps)

    def cropMap(self, img):

        self.parent().cropMapImage(img)

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


    def georefAvailable(self, path):

        if path == "":
            return "None"
        else:
            img = rio.open(path)
            geoinfo = img.crs

            from osgeo import osr
            srs = osr.SpatialReference()
            srs.ImportFromWkt(geoinfo.to_wkt())
            pretty_wkt = srs.ExportToPrettyWkt()
            return pretty_wkt

    def boolToWord(self, bool):

        if bool == True:
            return "Yes"
        else:
            return "No"

    def convertDate(self, str):
        myDate = QDate.fromString(str, 'yyyy-MM-dd')
        return myDate


