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

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QPointF
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF, QPainterPath
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,  QCheckBox, QRadioButton, QLayout, QFileDialog, QMessageBox, QComboBox, QGraphicsPolygonItem
from skimage import measure
import math
import csv
import cv2
import numpy as np

class QtGeometricInfoWidget(QWidget):

    # define the properties to compute
    properties = {
        "class": {"name": "Class of region",
                "label": "CLASS",
                "calculable": False,
                "round": 0},
        "centroidX": {"name": "Centroid, X coordinate (mm)",
                 "label": "CENTROID\nX",
                 "calculable": True,
                 "round": 2},
        "centroidY": {"name": "Centroid, Y coordinate (mm)",
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

        "areaBBox": {"name": "Area of Axis-Aligned\nBounding Box (mm2)",
                    "label": "BBOX\nAREA",
                    "calculable": True,
                    "round": 1},
        "widthBBox": {"name": "Horizontal size of\nAxis-Aligned Bounding Box (mm)",
                    "label": "BBOX\nWIDTH",
                    "calculable": True,
                    "round": 1},
        "heightBBox": {"name": "Vertical size of\nAxis-Aligned Bounding Box (mm)",
                      "label": "BBOX\nHEIGHT",
                      "calculable": True,
                      "round": 1},

        "areaRectangle": {"name": "Area of Minimum Rectangle (mm2)",
                          "label": "RECTANGLE\nAREA",
                          "calculable": True,
                          "round": 1},
        "majSideRectangle": {"name": "Major Side\nof Minimum Rectangle (mm)",
                           "label": "RECTANGLE\nMAJ SIDE",
                           "calculable": True,
                           "round": 1},
        "minSideRectangle": {"name": "Minor Side\nof Minimum Rectangle (mm)",
                            "label": "RECTANGLE\nMIN SIDE",
                            "calculable": True,
                            "round": 1},
        "orientationRectangle": {"name": "Orientation of Minimum Rectangle\n(degrees, 0=horizontal)",
                           "label": "RECTANGLE\nORIENTATION",
                           "calculable": True,
                           "round": 1},

        "majAxisEllipse": {"name": "Major Axis Length\nof fitted Ellipse (mm)",
                              "label": "ELLIPSE\nMAJ AXIS",
                              "calculable": True,
                              "round": 1},
        "minAxisEllipse": {"name": "Minor Axis Length\nof fitted Ellipse (mm)",
                              "label": "ELLIPSE\nMIN AXIS",
                              "calculable": True,
                              "round": 1},
        "orientationEllipse": {"name": "Orientation of fitted Ellipse\n(degrees, 0=horizontal)",
                        "label": "ELLIPSE\nORIENTATION",
                        "calculable": True,
                        "round": 3},
        "eccentricityEllipse": {"name": "Eccentricity of fitted Ellipse\n(0=round, 1=elongated)",
                         "label": "ELLIPSE\nECCENTRICITY",
                         "calculable": True,
                         "round": 3},
    }


    # initialize the widget
    def __init__(self, viewer, parent=None):
        super(QtGeometricInfoWidget, self).__init__(parent)

        # DATA ##########################################################
        # active viewer, mostly for drawing
        self.activeviewer = viewer
        # the set of working blobs, that contain the blobs being analyzed
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        # store the geometric data and stats
        self.geometricData = {}
        self.geometricStats = {}
        # store geometric entities for overlay
        self.fittedEntities = []
        self.colorizedEntities = []

        # EVENTS ###########################################################
        # Connect to selectionChanged signal of the activeviewer
        if hasattr(self.activeviewer, 'selectionChanged'):
            self.activeviewer.selectionChanged.connect(self.onSelectionChanged)
        # connect the close event to notify the main window
        self.closewidget.connect(self.close)

        # INTERFACE ###########################################################
        self.setStyleSheet("background-color: rgb(40,40,40); color: white;")
        mainLayout = QVBoxLayout()

        # add a table to show the regions and their measurements
        self.regions_table = QTableWidget()
        self.regions_table.setColumnCount(len(self.properties)+1)
        headerLabels = ["ID"] + [self.properties[prop]["label"] for prop in self.properties]
        self.regions_table.setHorizontalHeaderLabels(headerLabels)
        #setting tooltip for headers
        for i, prop in enumerate(self.properties):
            self.regions_table.horizontalHeaderItem(i+1).setToolTip(self.properties[prop]["name"])
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

        mainLayout.addWidget(self.regions_table)

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
        mainLayout.addWidget(self.stats_table)

        self.btnRecompute = QPushButton("")
        self.btnRecompute.clicked.connect(self.updateWorkingBlobs)
        self.btnRecompute.setEnabled(False)
        mainLayout.addWidget(self.btnRecompute)

        # add horizontal line separator to layout
        separator1 = QLabel()
        separator1.setStyleSheet("QLabel { border-bottom: 1px solid rgb(80,80,80); }")
        mainLayout.addWidget(separator1)

        # buttons for additional functions
        button_layout = QHBoxLayout()

        self.btnToggleFitted = QPushButton("Show Fitted Shapes")
        self.btnToggleFitted.setToolTip("Show fitted ellipses and minimum rectangles")
        self.btnToggleFitted.clicked.connect(self.toggleFittedShapes)
        self.btnColorize1 = QPushButton("Colorize by")
        self.btnColorize1.setToolTip("Colorize the shapes by a specific property")
        self.btnColorize1.clicked.connect(self.colorizeByProperty)
        self.propertyChooserInput = QComboBox() # add a dropdown with available properties
        propertyList = []
        for prop in self.properties:
            if self.properties[prop]["calculable"]:
                propertyList.append(prop)
        self.propertyChooserInput.addItems(propertyList)
        self.btnRemoveColor = QPushButton("X")
        self.btnRemoveColor.setToolTip("Remove colorization")
        self.btnRemoveColor.clicked.connect(self.removeColorizedEntities)

        button_layout.addStretch()
        button_layout.addWidget(self.btnToggleFitted)
        button_layout.addStretch()
        button_layout.addWidget(self.btnColorize1)
        button_layout.addWidget(self.propertyChooserInput)
        button_layout.addWidget(self.btnRemoveColor)
        button_layout.addStretch()

        button_layout.setAlignment(Qt.AlignLeft)
        mainLayout.addLayout(button_layout)

        # add horizontal line separator to layout
        separator2 = QLabel()
        separator2.setStyleSheet("QLabel { border-bottom: 1px solid rgb(80,80,80); }")
        mainLayout.addWidget(separator2)

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
        export_layout.setAlignment(Qt.AlignLeft)
        mainLayout.addLayout(export_layout)

        # add horizontal line separator to layout
        separatorBottom = QLabel()
        separatorBottom.setStyleSheet("QLabel { border-bottom: 1px solid rgb(80,80,80); }")
        mainLayout.addWidget(separatorBottom)

        # bottom row buttons
        bottom_layout = QHBoxLayout()
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.close)
        bottom_layout.setAlignment(Qt.AlignRight)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btnClose)
        mainLayout.addLayout(bottom_layout)

        # set the layout and window properties
        self.setLayout(mainLayout)
        self.setWindowTitle("Compute Geometric Info")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(1024)
        self.setMinimumHeight(600)

        # compute measures  and populate the table
        self.computeMeasures()
        return

    # close the widget
    closewidget = pyqtSignal()
    def closeEvent(self, event):
        # remove fitted and colorized shapes, if any
        self.removeFittedShapes()
        self.removeColorizedEntities()
        # emit the signal to notify the main window
        self.closewidget.emit()
        super(QtGeometricInfoWidget, self).closeEvent(event)
        return

    @pyqtSlot()
    def onSelectionChanged(self):
        # Called when the selection changes in the viewer
        #self.computeMeasures()
        print("Selection changed, but not recomputing measures automatically.")
        self.btnRecompute.setEnabled(True)
        self.btnRecompute.setText("Selection has changed, update the regions working set")
        self.btnRecompute.setStyleSheet("QPushButton { background-color: rgb(200,50,50); color: white; }")
        return

    def updateWorkingBlobs(self):
        self.btnRecompute.setEnabled(False)
        self.btnRecompute.setText("")
        # set button color to original state
        self.btnRecompute.setStyleSheet("QPushButton { background-color: rgb(50,50,50); color: white; }")
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        self.computeMeasures()
        return

########################################################################################
# COMPUTE AND DISPLAY FUNCTIONS
########################################################################################

    # compute the measures
    def computeMeasures(self):
        # remove previous fitted and colorized shapes, if any
        self.removeFittedShapes()
        self.removeColorizedEntities()
        # reset the geometric data and stats
        self.geometricData = {}
        self.geometricStats = {}
        # get measurements for the selected blobs
        for blob in self.workingBlobs:
            pxmm = self.activeviewer.px_to_mm
            pxmm2 = pxmm * pxmm
            blobMeasure = measure.regionprops(blob.getMask())
            self.geometricData[blob.id] = {}
            # base properties
            self.geometricData[blob.id]["class"] = blob.class_name
            self.geometricData[blob.id]["centroidX"] = round(blob.centroid[0], self.properties["centroidX"]["round"])
            self.geometricData[blob.id]["centroidY"] = round(self.activeviewer.image.height - blob.centroid[1], self.properties["centroidY"]["round"]) # warning, image Y coordinate is inverted
            self.geometricData[blob.id]["area"] = round(blob.area * pxmm2, self.properties["area"]["round"])            
            self.geometricData[blob.id]["perimeter"] = round(blob.perimeter * pxmm, self.properties["perimeter"]["round"])
            #self.geometricData[blob.id]["solidity"] = round(blobMeasure[0].solidity, self.properties["solidity"]["round"])  # see comment above about solidity and why is hidden
            # convex hull
            self.geometricData[blob.id]["areaConvex"] = round(blobMeasure[0].area_convex * pxmm2, self.properties["areaConvex"]["round"])
            # bbox fit
            self.geometricData[blob.id]["areaBBox"] = round(blobMeasure[0].area_bbox * pxmm2, self.properties["areaBBox"]["round"])
            self.geometricData[blob.id]["widthBBox"] = round((blobMeasure[0].bbox[3] - blobMeasure[0].bbox[1]) * pxmm, self.properties["widthBBox"]["round"]) #warning: bbox is in (min_row, min_col, max_row, max_col) format
            self.geometricData[blob.id]["heightBBox"] = round((blobMeasure[0].bbox[2] - blobMeasure[0].bbox[0]) * pxmm, self.properties["heightBBox"]["round"]) #warning: bbox is in (min_row, min_col, max_row, max_col) format
            # ellipse fit
            self.geometricData[blob.id]["eccentricityEllipse"] = round(blobMeasure[0].eccentricity, self.properties["eccentricityEllipse"]["round"])
            # Convert skimage orientation (0=vertical, CCW) to 0=horizontal, CCW, in degrees, constrained to [-90, 90]
            orientation = (blobMeasure[0].orientation * 180 / math.pi) - 90.0
            if orientation < -90: orientation += 180
            elif orientation > 90: orientation -= 180
            self.geometricData[blob.id]["orientationEllipse"] = round(orientation, self.properties["orientationEllipse"]["round"])
            self.geometricData[blob.id]["majAxisEllipse"] = round(blobMeasure[0].major_axis_length * pxmm, self.properties["majAxisEllipse"]["round"])
            self.geometricData[blob.id]["minAxisEllipse"] = round(blobMeasure[0].minor_axis_length * pxmm, self.properties["minAxisEllipse"]["round"])

            # minimum rectangle fit
            contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnt = contours[0]
            rect = cv2.minAreaRect(cnt)
            if rect[1][1] >= rect[1][0]:  # swap sides and rotate angle to have major side first
                rect = (rect[0], (rect[1][1], rect[1][0]), rect[2] - 90.0)
            self.geometricData[blob.id]["areaRectangle"] = round((rect[1][0] * rect[1][1]) * pxmm2, self.properties["areaRectangle"]["round"])            
            self.geometricData[blob.id]["majSideRectangle"] = round(rect[1][0] * pxmm, self.properties["majSideRectangle"]["round"])
            self.geometricData[blob.id]["minSideRectangle"] = round(rect[1][1] * pxmm, self.properties["minSideRectangle"]["round"])
            self.geometricData[blob.id]["orientationRectangle"] = round(-rect[2], self.properties["orientationRectangle"]["round"])

        # compute the stats
        for key in self.properties:
            if self.properties[key]["calculable"]:
                values = [self.geometricData[blob.id][key] for blob in self.workingBlobs]
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

        # now, populate the table
        self.populateTable()                
        return


    # populate the list of regions and attributes
    def populateTable(self):
        self.regions_table.setRowCount(len(self.workingBlobs))
        self.regions_table.setVerticalHeaderLabels(["-" for i in range(len(self.workingBlobs))])
        #fill the table with the selected blobs
        for blob in self.workingBlobs:
            row = self.workingBlobs.index(blob)
            self.regions_table.setItem(row, 0, QTableWidgetItem(str(blob.id)))
            self.regions_table.item(row, 0).setTextAlignment(Qt.AlignCenter)
            for i, prop in enumerate(self.properties):
                self.regions_table.setItem(row, i+1, QTableWidgetItem(str(self.geometricData[blob.id][prop])))
                self.regions_table.item(row, i+1).setTextAlignment(Qt.AlignRight)

        # TODO: each set of properties could have a different color, to help visual parsing of the table
        # colorize the columns
        #for row in range(self.regions_table.rowCount()):
        #    item = self.regions_table.item(row, 2)
        #    if item:
        #        item.setBackground(QColor(255, 255, 0))  # Yellow background

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
        return

########################################################################################
# FITTED SHAPES FUNCTIONS
########################################################################################

    # toggle the visibility of the fitted shapes in the viewer
    def toggleFittedShapes(self):    
        if self.btnToggleFitted.text() == "Show Fitted Shapes":
            self.btnToggleFitted.setText("Hide Fitted Shapes")
            self.displayFittedShapes()
        else:
            self.btnToggleFitted.setText("Show Fitted Shapes")
            self.removeFittedShapes()
        return

    # display fitted shapes in the viewer
    def displayFittedShapes(self):
        # show the fitted shapes
        for blob in self.workingBlobs:
            blobMeasure = measure.regionprops(blob.getMask())
            region = blobMeasure[0]
            # The centroid is relative to the mask, so offset by bbox
            min_row, min_col, _, _ = blob.bbox
            cy, cx = region.centroid
            cx_full = cx + min_col
            cy_full = cy + min_row
            ######################################## ELLIPSE
            path = QPainterPath()
            # Approximate ellipse with points
            num_points = 64
            theta = np.linspace(0, 2 * np.pi, num_points)
            # Fix orientation: skimage uses 0=vertical (CCW), OpenCV/viewer uses 0=horizontal (CCW), but angle direction is opposite
            orientation = -(region.orientation - np.pi / 2)
            cos_angle = np.cos(orientation)
            sin_angle = np.sin(orientation)
            for i, t in enumerate(theta):
                x = (region.major_axis_length / 2) * np.cos(t)
                y = (region.minor_axis_length / 2) * np.sin(t)
                x_rot = x * cos_angle - y * sin_angle + cx_full
                y_rot = x * sin_angle + y * cos_angle + cy_full
                if i == 0:
                    path.moveTo(QPointF(x_rot, y_rot))
                else:
                    path.lineTo(QPointF(x_rot, y_rot))
            path.closeSubpath()
            pen = QPen(QColor(0, 255, 0, 191)) # 75% transparent green
            pen.setWidth(2)
            pen.setCosmetic(True)
            newItemE = self.activeviewer.scene.addPath(path, pen)
            newItemE.setZValue(10)  # Draw above most items
            self.fittedEntities.append(newItemE)
            ######################################## RECTANGLE
            contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            rect = cv2.minAreaRect(contours[0])
            if rect[1][1] >= rect[1][0]:  # swap sides and rotate angle to have major side first
                rect = (rect[0], (rect[1][1], rect[1][0]), rect[2] - 90.0)
            box_points = cv2.boxPoints(rect)
            # Offset box_points by the mask's position in the full image
            box_points_global = box_points + np.array([min_col + 0.5, min_row + 0.5]) # +0.5 to center the line on the pixel
            polygon = QPolygonF([QPointF(float(x), float(y)) for x, y in box_points_global])
            pen = QPen(QColor(255, 0, 0, 191)) # 75% transparent red
            pen.setWidth(2)
            pen.setCosmetic(True)
            newItemR = self.activeviewer.scene.addPolygon(polygon, pen)
            newItemR.setZValue(10)  # Draw above most items
            self.fittedEntities.append(newItemR)
        return
    # remove fitted shapes from the viewer
    def removeFittedShapes(self):
        if self.fittedEntities:
            for item in self.fittedEntities:
                self.activeviewer.scene.removeItem(item)
            self.fittedEntities = []
            self.btnToggleFitted.setText("Show Fitted Shapes")
        return

########################################################################################
# COLORIZE FUNCTIONS
########################################################################################

    # colorize the shapes by a specific property
    def colorizeByProperty(self):
        # determine which property is selected
        selected_property = self.propertyChooserInput.currentText()
        self.displayColorizedEntities(selected_property)
        return

    # display colorized shapes in the viewer
    def displayColorizedEntities(self, property):
        self.removeColorizedEntities()  # remove previous colorized entities, if any
        # get the min and max values for the selected property
        values = [self.geometricData[blob.id][property] for blob in self.workingBlobs]
        min_value = min(values)
        max_value = max(values)
        value_range = max_value - min_value if max_value != min_value else 1.0  # avoid division by zero
        # create a color map from blue (low) to red (high)
        for blob in self.workingBlobs:
            min_row, min_col, _, _ = blob.bbox
            value = self.geometricData[blob.id][property]
            normalized_value = (value - min_value) / value_range
            r = int(normalized_value * 255)
            g = 0
            b = int((1 - normalized_value) * 255)
            color = QColor(r, g, b, 255)  # fully opaque
            pen = QPen(Qt.NoPen)
            brush = QBrush(color)
            # draw the blob's filled contour
            contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnt = contours[0]
            polygon = QPolygonF([QPointF(float(point[0][0])+min_col, float(point[0][1])+min_row) for point in cnt])
            newItemC = self.activeviewer.scene.addPolygon(polygon, pen, brush)
            newItemC.setZValue(10)  # Draw above most items
            self.colorizedEntities.append(newItemC)
        return
        
    # remove colorized shapes from the viewer
    def removeColorizedEntities(self):
        if self.colorizedEntities:
            for item in self.colorizedEntities:
                self.activeviewer.scene.removeItem(item)
            self.colorizedEntities = []
        return


########################################################################################
# EXPORT FUNCTIONS
########################################################################################

# export the data to a CSV file
    def exportToCSV(self):
        # open a file dialog to choose the file name
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, "Save measures table as CSV", "", "CSV Files (*.csv)", options=options)
        if not fileName:    return
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
        for blob in self.activeviewer.workingBlobs:
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