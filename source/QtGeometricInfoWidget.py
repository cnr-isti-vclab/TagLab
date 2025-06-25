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
        self.regions_table.setStyleSheet("QTableWidget { background-color: rgb(50,50,50);  }"
                                        "QHeaderView::section { background-color: rgb(80,80,80); color: white; }"
                                        "QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }"                                        
                                        "QTableWidget::item { padding: 5px; color: white;}"
                                        "QTableWidget::item:selected { background-color: rgb(50,50,120);")

        layout.addWidget(self.regions_table)

        # add a table for min/max/average values
        self.stats_table = QTableWidget()
        self.stats_table.setRowCount(5)
        self.stats_table.setColumnCount(len(self.properties))
        headerLabels = [self.properties[prop]["label"] for prop in self.properties]
        self.stats_table.setHorizontalHeaderLabels(headerLabels)
        #setting tooltip for headers
        for i, prop in enumerate(self.properties):
            self.stats_table.horizontalHeaderItem(i).setToolTip(self.properties[prop]["name"])        
        self.stats_table.setVerticalHeaderLabels(["MIN", "MAX", "AVG", "STD", "MED"])
        self.stats_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stats_table.setSelectionMode(QTableWidget.NoSelection)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setShowGrid(True)
        self.stats_table.setAlternatingRowColors(False)
        self.stats_table.setStyleSheet("QTableWidget { background-color: rgb(50,50,50); }"
                                        "QHeaderView::section { background-color: rgb(80,80,80); color: white; }"
                                        "QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }"
                                        "QTableWidget::item { padding: 5px; color: white;}"
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
            line = ["average"] + [str(self.geometricStats[prop]["average"]) for prop in self.properties]
            data.append(line)
            line = ["std."] + [str(self.geometricStats[prop]["std"]) for prop in self.properties]
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
        "class": {"name": "Class of region",
                "label": "CLASS",
                "calculable": False,
                "round": 0},
        "centroidx": {"name": "Centroid, X coordinate (mm)",
                 "label": "CENTROID\nX",
                 "calculable": True,
                 "round": 2},
        "centroidy": {"name": "Centroid, Y coordinate (mm)",
                 "label": "CENTROID\nY",
                 "calculable": True,
                 "round": 2},
        "area": {"name": "Area of region (mm2)",
                 "label": "AREA",
                 "calculable": True,
                 "round": 1},
        "perimeter": {"name": "Perimeter of region (mm)",
                      "label": "PERIMETER",
                      "calculable": True,
                      "round": 1},
        #"solidity": {"name": "Solidity",        # solidity is a derived measuree, it is area/area_convex, so it could be computed later
        #             "label": "SOLIDITY",       # if I change my mind, I'll add it back in another set of derived properties
        #             "calculable": True,
        #             "round": 3},
        "areaConvex": {"name": "Area of Convex Hull (mm2)",
                       "label": "CONVEX\nAREA",
                       "calculable": True,
                       "round": 1},
        "areaBox": {"name": "Area of Bounding Box (mm2)",
                    "label": "BBOX\nAREA",
                    "calculable": True,
                    "round": 1},
        "widthBox": {"name": "Horizontal size of\nBounding Box (mm)",
                    "label": "BBOX\nWIDTH",
                    "calculable": True,
                    "round": 1},
        "heightBox": {"name": "Vertical size of\nBounding Box (mm)",
                      "label": "BBOX\nHEIGHT",
                      "calculable": True,
                      "round": 1},
        "eccentricity": {"name": "Eccentricity of fitted ellipse\n(0=round, 1=elongated)",
                         "label": "ELLIPSE\nECCENTRICITY",
                         "calculable": True,
                         "round": 3},
        "orientation": {"name": "Orientation of fitted ellipse\n(degrees: 0=vertical, 90=horizontal)",
                        "label": "ELLIPSE\nORIENTATION",
                        "calculable": True,
                        "round": 3},                         
        "major_axis_length": {"name": "Major Axis Length\nof fitted ellipse (mm)",
                              "label": "ELLIPSE\nMAJ AXIS",
                              "calculable": True,
                              "round": 1},
        "minor_axis_length": {"name": "Minor Axis Length\nof fitted ellipse (mm)",
                              "label": "ELLIPSE\nMIN AXIS",
                              "calculable": True,
                              "round": 1}
    }

    # compute the measures
    def computeMeasures(self):
        # get measurements for the selected blobs
        self.geometricData = {}
        for blob in self.parent.activeviewer.selected_blobs:
            pxmm = self.parent.activeviewer.px_to_mm
            pxmm2 = pxmm * pxmm
            blobMeasure = measure.regionprops(blob.getMask())
            self.geometricData[blob.id] = {}
            # base properties
            self.geometricData[blob.id]["class"] = blob.class_name
            self.geometricData[blob.id]["centroidx"] = round(blob.centroid[0], self.properties["centroidx"]["round"])
            self.geometricData[blob.id]["centroidy"] = round(self.parent.activeviewer.image.height - blob.centroid[1], self.properties["centroidy"]["round"]) # warning, image Y coordinate is inverted
            self.geometricData[blob.id]["area"] = round(blob.area * pxmm2, self.properties["area"]["round"])            
            self.geometricData[blob.id]["perimeter"] = round(blob.perimeter * pxmm, self.properties["perimeter"]["round"])
            #self.geometricData[blob.id]["solidity"] = round(blobMeasure[0].solidity, self.properties["solidity"]["round"])  # see comment above about solidity and why is hidden
            # convex hull
            self.geometricData[blob.id]["areaConvex"] = round(blobMeasure[0].area_convex * pxmm2, self.properties["areaConvex"]["round"])
            # bbox fit
            self.geometricData[blob.id]["areaBox"] = round(blobMeasure[0].area_bbox * pxmm2, self.properties["areaBox"]["round"])
            self.geometricData[blob.id]["widthBox"] = round((blobMeasure[0].bbox[3] - blobMeasure[0].bbox[1]) * pxmm, self.properties["widthBox"]["round"]) #warning: bbox is in (min_row, min_col, max_row, max_col) format
            self.geometricData[blob.id]["heightBox"] = round((blobMeasure[0].bbox[2] - blobMeasure[0].bbox[0]) * pxmm, self.properties["heightBox"]["round"]) #warning: bbox is in (min_row, min_col, max_row, max_col) format
            #ellipse fit
            self.geometricData[blob.id]["eccentricity"] = round(blobMeasure[0].eccentricity, self.properties["eccentricity"]["round"])
            self.geometricData[blob.id]["orientation"] = round((blobMeasure[0].orientation * 180 / math.pi), self.properties["orientation"]["round"])
            self.geometricData[blob.id]["major_axis_length"] = round(blobMeasure[0].major_axis_length * pxmm, self.properties["major_axis_length"]["round"])
            self.geometricData[blob.id]["minor_axis_length"] = round(blobMeasure[0].minor_axis_length * pxmm, self.properties["minor_axis_length"]["round"])
            # rectangle fit

        # compute the stats
        self.geometricStats = {}
        for key in self.properties:
            if self.properties[key]["calculable"]:
                values = [self.geometricData[blob.id][key] for blob in self.parent.activeviewer.selected_blobs]
                self.geometricStats[key] = {
                    "min": min(values),
                    "max": max(values),
                    "average": round(sum(values) / len(values), self.properties[key]["round"]),
                    "std": round((sum((x - (sum(values) / len(values))) ** 2 for x in values) / len(values)) ** 0.5, self.properties[key]["round"]),
                    "median": sorted(values)[len(values) // 2],
                }
            else:
                self.geometricStats[key] = {
                    "min": "-",
                    "max": "-",
                    "average": "-",
                    "std": "-",
                    "median": "-"
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
            self.stats_table.setItem(2, i, QTableWidgetItem(str(self.geometricStats[prop]["average"])))
            self.stats_table.item(2, i).setTextAlignment(Qt.AlignRight)
            self.stats_table.setItem(3, i, QTableWidgetItem(str(self.geometricStats[prop]["std"])))
            self.stats_table.item(3, i).setTextAlignment(Qt.AlignRight)
            self.stats_table.setItem(4, i, QTableWidgetItem(str(self.geometricStats[prop]["median"])))
            self.stats_table.item(4, i).setTextAlignment(Qt.AlignRight)

        # resize to fit contents
        self.regions_table.resizeColumnsToContents()
        self.stats_table.resizeColumnsToContents()



