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

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,  QCheckBox, QRadioButton, QLayout, QFileDialog, QMessageBox
from skimage import measure
import math
import csv

class QtGeometricInfoWidget(QWidget):

    closewidget = pyqtSignal()
    mode = pyqtSignal(str)

    def __init__(self, wiew, parent=None):
        super(QtGeometricInfoWidget, self).__init__(parent)

        self.parent = parent
        self.activeviewer = wiew

        self.geometricData = None

        ###########################################################
        self.setStyleSheet("background-color: rgb(40,40,40); color: white;")
        ###########################################################
        layout = QVBoxLayout()

        # add a table to show the regions and their measurements
        self.regions_table = QTableWidget()
        self.regions_table.setRowCount(len(parent.activeviewer.selected_blobs))
        self.regions_table.setColumnCount(len(self.properties)+1)
        headerLabels = ["ID"] + [self.properties[prop]["label"] for prop in self.properties]
        self.regions_table.setHorizontalHeaderLabels(headerLabels)
        #setting tooltip for headers
        for i, prop in enumerate(self.properties):
            self.regions_table.horizontalHeaderItem(i+1).setToolTip(self.properties[prop]["name"])
        self.regions_table.setVerticalHeaderLabels(["-" for i in range(len(parent.activeviewer.selected_blobs))])
        self.regions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.regions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.regions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.regions_table.setSortingEnabled(False)
        self.regions_table.setShowGrid(True)
        self.regions_table.setAlternatingRowColors(False)
        self.regions_table.setStyleSheet("QTableWidget { background-color: rgb(60,60,60); color: white; }"
                                        "QHeaderView::section { background-color: rgb(80,80,80); color: white; }"
                                        "QTableWidget::item { padding: 5px; }"
                                        "QTableWidget::item:selected { background-color: rgb(50,50,120); }")

        layout.addWidget(self.regions_table)

        # add a table for min/max/average values
        self.stats_table = QTableWidget()
        self.stats_table.setRowCount(5)
        self.stats_table.setColumnCount(len(self.properties))
        headerLabels = [self.properties[prop]["label"] for prop in self.properties]
        self.stats_table.setHorizontalHeaderLabels(headerLabels)
        self.stats_table.setVerticalHeaderLabels(["MIN", "MAX", "AVG", "STD", "MED"])
        self.stats_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stats_table.setSelectionMode(QTableWidget.NoSelection)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setShowGrid(True)
        self.stats_table.setAlternatingRowColors(False)
        self.stats_table.setStyleSheet("QTableWidget { background-color: rgb(60,60,60); color: white; }"
                                        "QHeaderView::section { background-color: rgb(80,80,80); color: white; }"
                                        "QTableWidget::item { padding: 5px; }"
                                        "QTableWidget::item:selected { background-color: rgb(50,50,120); }")
        layout.addWidget(self.stats_table)

        # buttons for exporting data
        export_layout = QHBoxLayout()
        self.btnExportCSV = QPushButton("Export to CSV")
        self.btnExportCSV.setToolTip("Export the data to a CSV file")
        self.btnExportCSV.clicked.connect(self.exportToCSV) 
        self.cbIncludeStats = QCheckBox("Include stats")
        self.cbIncludeStats.setToolTip("Include stats in the exported CSV file")
        self.cbIncludeStats.setChecked(False)
        export_layout.addWidget(self.btnExportCSV)
        export_layout.addWidget(self.cbIncludeStats)
        export_layout.setAlignment(Qt.AlignHCenter)
        layout.addLayout(export_layout)

        # add horizontal line separator to layput
        separator = QLabel()
        separator.setStyleSheet("QLabel { border-bottom: 1px solid rgb(80,80,80); }")
        layout.addWidget(separator) 

        # bottom row buttons
        bottom_layout = QHBoxLayout()
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.close)
        bottom_layout.setAlignment(Qt.AlignRight)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btnClose)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.setWindowTitle("Compute Geometric Info")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(1024)
        self.setMinimumHeight(600)

        # compute measures
        self.computeMeasures()
        # now, populate the table
        self.populateTable()


    # close the widget
    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtGeometricInfoWidget, self).closeEvent(event)


    # export the data to a CSV file
    def exportToCSV(self):
        # open a file dialog to choose the file name
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Save measures table as CSV", "", "CSV Files (*.csv)", options=options)
        if not fileName:
            return

        # fields and data to write
        fields = ["ID"] + [prop for prop in self.properties]
        data = []
        # if the user wants to include stats, add them to the data
        if self.cbIncludeStats.isChecked():
            line = ["minimum"] + [str(self.geometricStats[prop]["min"]) for prop in self.properties]
            data.append(line)
            line = ["maximum"] + [str(self.geometricStats[prop]["max"]) for prop in self.properties]
            data.append(line)
            line = ["average"] + [str(round(self.geometricStats[prop]["average"],3)) for prop in self.properties]
            data.append(line)
            line = ["std."] + [str(round(self.geometricStats[prop]["std"],3)) for prop in self.properties]
            data.append(line)
            line = ["median"] + [str(self.geometricStats[prop]["median"]) for prop in self.properties]
            data.append(line)
        # add the data for each blob
        for blob in self.parent.activeviewer.selected_blobs:
            line = [blob.id]
            for prop in self.properties:
                line.append(self.geometricData[blob.id][prop])
            data.append(line)

        # write the data to the file
        try:
            with open(fileName, mode='w', newline='') as file:
                writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(fields)
                for line in data:
                    writer.writerow(line)
        except Exception as e:
            print(f"Error writing to file: {e}")
            QMessageBox.critical(self, "Error", f"Could not write to file: {e}")

        return

    properties = {
        "area": {"name": "Area",
                 "label": "AREA",
                 "calculable": True},
        "areaBox": {"name": "Area Box",
                    "label": "BBOX A.",
                    "calculable": True},
        "areaConvex": {"name": "Area Convex",
                       "label": "CONVEX A.",
                       "calculable": True},
        "perimeter": {"name": "Perimeter",
                      "label": "PERIM.",
                      "calculable": True},
        "P2": {"name": "P2",
               "label": "P2",
               "calculable": True},
        "eccentricity": {"name": "Eccentricity",
                         "label": "ECCENTR.",
                         "calculable": True},
        "major_axis_length": {"name": "Major Axis Length",
                              "label": "MAJ AXIS",
                              "calculable": True},
        "minor_axis_length": {"name": "Minor Axis Length",
                              "label": "MIN AXIS",
                              "calculable": True},        
        "orientation": {"name": "Orientation",
                        "label": "ORIENT.",
                        "calculable": True},
        "solidity": {"name": "Solidity",
                     "label": "SOLIDITY",
                     "calculable": True}
    }

    # compute the measures
    def computeMeasures(self):
        # get measurements for the selected blobs
        self.geometricData = {}
        for blob in self.parent.activeviewer.selected_blobs:
            self.geometricData[blob.id] = {}
            self.geometricData[blob.id]["perimeter"] = blob.perimeter
            blobMeasure = measure.regionprops(blob.getMask())
            self.geometricData[blob.id]["area"] = round(blobMeasure[0].area,1)
            self.geometricData[blob.id]["areaBox"] = round(blobMeasure[0].area_bbox,1)
            self.geometricData[blob.id]["areaConvex"] = round(blobMeasure[0].area_convex,1)
            self.geometricData[blob.id]["P2"] = round(blobMeasure[0].perimeter,1)
            self.geometricData[blob.id]["eccentricity"] = round(blobMeasure[0].eccentricity,3)
            self.geometricData[blob.id]["orientation"] = round((blobMeasure[0].orientation * 180 / math.pi),3)
            self.geometricData[blob.id]["major_axis_length"] = round(blobMeasure[0].major_axis_length,1)
            self.geometricData[blob.id]["minor_axis_length"] = round(blobMeasure[0].minor_axis_length,1)
            self.geometricData[blob.id]["solidity"] = round(blobMeasure[0].solidity,3)

        # compute the stats        
        self.geometricStats = {}
        for key in self.properties:
            if self.properties[key]["calculable"]:
                values = [self.geometricData[blob.id][key] for blob in self.parent.activeviewer.selected_blobs]
                self.geometricStats[key] = {
                    "min": min(values),
                    "max": max(values),
                    "average": sum(values) / len(values),
                    "std": (sum((x - (sum(values) / len(values))) ** 2 for x in values) / len(values)) ** 0.5,
                    "median": sorted(values)[len(values) // 2],
                }
            else:
                self.geometricStats[key] = {
                    "min": 0,
                    "max": 0,
                    "average": 0,
                    "std": 0,
                    "median": 0
                }                
        return

    # populate the list of regions and attributes
    def populateTable(self):
        #fill the table with the selected blobs
        for blob in self.parent.activeviewer.selected_blobs:
            row = self.parent.activeviewer.selected_blobs.index(blob)
            self.regions_table.setItem(row, 0, QTableWidgetItem(str(blob.id)))
            self.regions_table.item(row, 0).setTextAlignment(Qt.AlignCenter)
            for i, prop in enumerate(self.properties):
                self.regions_table.setItem(row, i+1, QTableWidgetItem(str(self.geometricData[blob.id][prop])))
                self.regions_table.item(row, i+1).setTextAlignment(Qt.AlignRight)

        # fill the stats table
        for i, prop in enumerate(self.properties):
            self.stats_table.setItem(0, i, QTableWidgetItem(str(self.geometricStats[prop]["min"])))
            self.stats_table.item(0, i).setTextAlignment(Qt.AlignRight)
            self.stats_table.setItem(1, i, QTableWidgetItem(str(self.geometricStats[prop]["max"])))
            self.stats_table.item(1, i).setTextAlignment(Qt.AlignRight)
            self.stats_table.setItem(2, i, QTableWidgetItem(str(round(self.geometricStats[prop]["average"],3))))
            self.stats_table.item(2, i).setTextAlignment(Qt.AlignRight)
            self.stats_table.setItem(3, i, QTableWidgetItem(str(round(self.geometricStats[prop]["std"],3))))
            self.stats_table.item(3, i).setTextAlignment(Qt.AlignRight)
            self.stats_table.setItem(4, i, QTableWidgetItem(str(self.geometricStats[prop]["median"])))
            self.stats_table.item(4, i).setTextAlignment(Qt.AlignRight)

        # resize to fit contents
        self.regions_table.resizeColumnsToContents()
        self.stats_table.resizeColumnsToContents()



