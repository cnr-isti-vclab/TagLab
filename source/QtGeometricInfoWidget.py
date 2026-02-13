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
from PyQt5.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout,  QCheckBox, QRadioButton, QLayout, QFileDialog, QMessageBox, QComboBox, QGraphicsPolygonItem, QGroupBox, QDialog
from skimage import measure
import math
import csv
import cv2
import numpy as np

# Custom table widget item that sorts by numeric value stored in UserRole
class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # Sort by the numeric value stored in UserRole, not the display text
        self_value = self.data(Qt.UserRole)
        other_value = other.data(Qt.UserRole)
        
        # Handle cases where values might be strings (like class names)
        if isinstance(self_value, str) or isinstance(other_value, str):
            return str(self_value) < str(other_value)
        
        # For numeric values, compare them directly
        try:
            return float(self_value) < float(other_value)
        except (TypeError, ValueError):
            return str(self_value) < str(other_value)


class QtGeometricInfoWidget(QWidget):

    # define the properties to compute
    properties = {
        "class": {"name": "Class of region",
                "label": "CLASS",
                "calculable": False,
                "round": 0,
                "attribute" : False},
        "centroidX": {"name": "Centroid, X coordinate (mm)",
                 "label": "CENTROID\nX",
                 "calculable": True,
                 "round": 1,
                 "attribute" : False},
        "centroidY": {"name": "Centroid, Y coordinate (mm)",
                 "label": "CENTROID\nY",
                 "calculable": True,
                 "round": 1,
                 "attribute" : False},
        "area": {"name": "Area of region (mm2)",
                 "label": "AREA",
                 "calculable": True,
                 "round": 1,
                 "attribute" : False},
        "perimeter": {"name": "Perimeter of region (mm)",
                      "label": "PERIMETER",
                      "calculable": True,
                      "round": 1,
                      "attribute" : False},
        #"solidity": {"name": "Solidity",        # solidity is a derived measuree, it is area/area_convex, so it could be computed later
        #             "label": "SOLIDITY",       # if I change my mind, I'll add it back in another set of derived properties
        #             "calculable": True,
        #             "round": 3},

        "areaConvex": {"name": "Area of Convex Hull (mm2)",
                       "label": "CONVEX\nAREA",
                       "calculable": True,
                       "round": 1,
                       "attribute" : True},

        "areaBBox": {"name": "Area of Axis-Aligned\nBounding Box (mm2)",
                    "label": "BBOX\nAREA",
                    "calculable": True,
                    "round": 1,
                    "attribute" : True},
        "widthBBox": {"name": "Horizontal size of\nAxis-Aligned Bounding Box (mm)",
                    "label": "BBOX\nWIDTH",
                    "calculable": True,
                    "round": 1,
                    "attribute" : False},
        "heightBBox": {"name": "Vertical size of\nAxis-Aligned Bounding Box (mm)",
                      "label": "BBOX\nHEIGHT",
                      "calculable": True,
                      "round": 1,
                      "attribute" : False},

        "areaRectangle": {"name": "Area of Minimum Rectangle (mm2)",
                          "label": "RECTANGLE\nAREA",
                          "calculable": True,
                          "round": 1,
                          "attribute" : False},
        "majSideRectangle": {"name": "Major Side\nof Minimum Rectangle (mm)",
                           "label": "RECTANGLE\nMAJ SIDE",
                           "calculable": True,
                           "round": 1,
                           "attribute" : True},
        "minSideRectangle": {"name": "Minor Side\nof Minimum Rectangle (mm)",
                            "label": "RECTANGLE\nMIN SIDE",
                            "calculable": True,
                            "round": 1,
                            "attribute" : True},
        "orientationRectangle": {"name": "Orientation of Minimum Rectangle\n(degrees, 0=horizontal)",
                           "label": "RECTANGLE\nORIENTATION",
                           "calculable": True,
                           "round": 2,
                           "attribute" : True},

        "majAxisEllipse": {"name": "Major Axis Length\nof fitted Ellipse (mm)",
                              "label": "ELLIPSE\nMAJ AXIS",
                              "calculable": True,
                              "round": 1,
                              "attribute" : True},
        "minAxisEllipse": {"name": "Minor Axis Length\nof fitted Ellipse (mm)",
                              "label": "ELLIPSE\nMIN AXIS",
                              "calculable": True,
                              "round": 1,
                              "attribute" : True},
        "orientationEllipse": {"name": "Orientation of fitted Ellipse\n(degrees, 0=horizontal)",
                        "label": "ELLIPSE\nORIENTATION",
                        "calculable": True,
                        "round": 2,
                        "attribute" : True},
        "eccentricityEllipse": {"name": "Eccentricity of fitted Ellipse\n(0=round, 1=elongated)",
                         "label": "ELLIPSE\nECCENTRICITY",
                         "calculable": True,
                         "round": 3,
                         "attribute" : True},
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
        self.fittedRectangleEntities = []
        self.fittedEllipseEntities = []
        self.colorizedEntities = []
        self.highlightedEntity = None  # Store the highlighted region outline

        # EVENTS ###########################################################
        # Connect to selectionChanged signal of the activeviewer
        if hasattr(self.activeviewer, 'selectionChanged'):
            self.activeviewer.selectionChanged.connect(self.onSelectionChanged)
        # connect the close event to notify the main window
        self.closewidget.connect(self.close)

        # INTERFACE ###########################################################
        self.setStyleSheet("background-color: rgb(40,40,40); color: white;"
                          "QToolTip { background-color: rgb(240,240,240); color: black; border: 1px solid rgb(100,100,100); padding: 3px; }")
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
        self.regions_table.setSortingEnabled(True)
        self.regions_table.setShowGrid(True)
        self.regions_table.setAlternatingRowColors(False)
        self.regions_table.setStyleSheet("QTableWidget { background-color: rgb(50,50,50);  }"
                                        "QHeaderView::section { background-color: rgb(80,80,80); color: white; }"
                                        "QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }"                                        
                                        "QTableWidget::item { padding: 5px; color: white;}"
                                        "QTableWidget::item:selected { background-color: rgb(50,50,120); }")
        
        # Connect to table selection changed signal to highlight selected region
        self.regions_table.itemSelectionChanged.connect(self.onTableSelectionChanged)
        # Install event filter to allow deselection by clicking empty table area
        self.regions_table.viewport().installEventFilter(self)

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

        # GROUP BOX for visualization controls
        visualizationGroup = QGroupBox("Visualization")
        visualizationGroup.setStyleSheet("QGroupBox { background-color: rgb(45,45,45); color: white; border: 2px solid rgb(80,80,80); border-radius: 5px; margin-top: 10px; padding-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; } QToolTip { background-color: rgb(240,240,240); color: black; border: 1px solid rgb(100,100,100); padding: 3px; }")
        visualizationLayout = QVBoxLayout()

        # First row - fitted shapes buttons
        fitted_layout = QHBoxLayout()
        self.btnToggleRectangles = QPushButton("Show Rectangles")
        self.btnToggleRectangles.setToolTip("Show/hide fitted minimum area rectangles")
        self.btnToggleRectangles.clicked.connect(self.toggleRectangles)
        self.btnToggleEllipses = QPushButton("Show Ellipses")
        self.btnToggleEllipses.setToolTip("Show/hide fitted ellipses with major and minor axes")
        self.btnToggleEllipses.clicked.connect(self.toggleEllipses)
        fitted_layout.addWidget(self.btnToggleRectangles)
        fitted_layout.addWidget(self.btnToggleEllipses)
        fitted_layout.addStretch()
        visualizationLayout.addLayout(fitted_layout)

        # Second row - colorize by property
        colorize_layout1 = QHBoxLayout()
        self.btnColorize1 = QPushButton("Colorize by")
        self.btnColorize1.setToolTip("Colorize the shapes by a specific property")
        self.btnColorize1.clicked.connect(self.colorizeByProperty)
        self.propertyChooserInput = QComboBox()
        propertyList = []
        for prop in self.properties:
            if self.properties[prop]["calculable"]:
                propertyList.append(prop)
        self.propertyChooserInput.addItems(propertyList)
        self.propertyChooserInput.currentTextChanged.connect(self.onPropertyChanged)
        
        self.propertyMinInput = QLineEdit()
        self.propertyMinInput.setMaximumWidth(80)
        self.propertyMinInput.setToolTip("Minimum value for color ramp")
        self.propertyMinInput.editingFinished.connect(self.onColorRangeChanged)
        
        self.propertyMaxInput = QLineEdit()
        self.propertyMaxInput.setMaximumWidth(80)
        self.propertyMaxInput.setToolTip("Maximum value for color ramp")
        self.propertyMaxInput.editingFinished.connect(self.onColorRangeChanged)

        lblMinMax = QLabel("<-range->")
        
        self.cbCenteredRamp = QCheckBox("Centered on")
        self.cbCenteredRamp.setToolTip("Use diverging color ramp centered on specified value (gray at center, blue below, red above)")
        self.cbCenteredRamp.stateChanged.connect(self.onColorRangeChanged)
        
        self.propertyCenterInput = QLineEdit()
        self.propertyCenterInput.setText("0")
        self.propertyCenterInput.setMaximumWidth(80)
        self.propertyCenterInput.setToolTip("Center value for diverging color ramp")
        self.propertyCenterInput.editingFinished.connect(self.onColorRangeChanged)

        self.btnRemoveColor = QPushButton("🗑️")
        self.btnRemoveColor.setMaximumWidth(40)
        self.btnRemoveColor.setToolTip("Remove colorization")
        self.btnRemoveColor.clicked.connect(self.removeColorizedEntities)
        colorize_layout1.addWidget(self.btnColorize1)
        colorize_layout1.addWidget(self.propertyChooserInput)
        colorize_layout1.addWidget(self.btnRemoveColor)
        colorize_layout1.addSpacing(10)
        colorize_layout1.addWidget(self.propertyMinInput)
        colorize_layout1.addWidget(lblMinMax)
        colorize_layout1.addWidget(self.propertyMaxInput)
        colorize_layout1.addSpacing(10)
        colorize_layout1.addWidget(self.cbCenteredRamp)
        colorize_layout1.addWidget(self.propertyCenterInput)

        colorize_layout1.addStretch()
        visualizationLayout.addLayout(colorize_layout1)

        # Third row - colorize by squareness/roundness
        colorize_layout2 = QHBoxLayout()
        self.btnColorize2 = QPushButton("Colorize by squareness/roundness")
        self.btnColorize2.clicked.connect(self.colorizeByShape)
        self.thresholdInput0 = QLineEdit()
        self.thresholdInput0.setText("0.5")
        self.thresholdInput0.setMaximumWidth(60)
        self.thresholdInput1 = QLineEdit()
        self.thresholdInput1.setText("1")
        self.thresholdInput1.setMaximumWidth(60)
        colorize_layout2.addWidget(self.btnColorize2)
        colorize_layout2.addWidget(self.thresholdInput0)
        colorize_layout2.addWidget(self.thresholdInput1)
        colorize_layout2.addStretch()
        visualizationLayout.addLayout(colorize_layout2)

        visualizationGroup.setLayout(visualizationLayout)
        mainLayout.addWidget(visualizationGroup)

        # GROUP BOX for export controls
        exportGroup = QGroupBox("Export")
        exportGroup.setStyleSheet("QGroupBox { background-color: rgb(45,45,45); color: white; border: 2px solid rgb(80,80,80); border-radius: 5px; margin-top: 10px; padding-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; } QToolTip { background-color: rgb(240,240,240); color: black; border: 1px solid rgb(100,100,100); padding: 3px; }")
        exportLayout = QVBoxLayout()
        
        # First row - Export CSV
        csv_layout = QHBoxLayout()
        self.btnExportCSV = QPushButton("Export to CSV")
        self.btnExportCSV.setToolTip("Export the data to a CSV file")
        self.btnExportCSV.clicked.connect(self.exportToCSV)
        self.cbIncludeStats = QCheckBox("Include stats")
        self.cbIncludeStats.setToolTip("Include stats in the exported CSV file")
        self.cbIncludeStats.setChecked(False)
        csv_layout.addWidget(self.btnExportCSV)
        csv_layout.addWidget(self.cbIncludeStats)
        csv_layout.addStretch()
        exportLayout.addLayout(csv_layout)
        
        # Second row - Add as Attributes
        attr_layout = QHBoxLayout()
        self.btnAddAsAttributes = QPushButton("Add Geometric Measurements as Region Attributes")
        self.btnAddAsAttributes.setToolTip("Add the computed geometric measurements as attributes to the selected regions")
        self.btnAddAsAttributes.clicked.connect(self.showAddAttributesDialog)
        attr_layout.addWidget(self.btnAddAsAttributes)
        attr_layout.addStretch()
        exportLayout.addLayout(attr_layout)
        
        exportGroup.setLayout(exportLayout)
        mainLayout.addWidget(exportGroup)

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

        # compute measures and populate the table
        if len(self.workingBlobs) > 0:
            self.computeMeasures()
        else:
            QMessageBox.warning(self, "No Selection", "Please select at least one region before opening this widget.")
        return

    # close the widget
    closewidget = pyqtSignal()
    def closeEvent(self, event):
        # remove fitted and colorized shapes, if any
        self.removeFittedRectangles()
        self.removeFittedEllipses()
        self.removeColorizedEntities()
        self.removeHighlight()  # Remove highlight when closing
        # Remove event filter
        self.regions_table.viewport().removeEventFilter(self)
        # emit the signal to notify the main window
        self.closewidget.emit()
        super(QtGeometricInfoWidget, self).closeEvent(event)
        return

    def eventFilter(self, obj, event):
        """
        Event filter to catch mouse clicks in the table viewport.
        Allows deselection by clicking on empty areas.
        """
        if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
            if obj == self.regions_table.viewport():
                # Get the item at the clicked position
                pos = event.pos()
                item = self.regions_table.itemAt(pos)
                if item is None:
                    # Clicked on empty area - clear selection
                    self.regions_table.clearSelection()
                    return False  # Let the table handle it normally
                return False  # Let normal selection handling proceed
        
        return super(QtGeometricInfoWidget, self).eventFilter(obj, event)

    @pyqtSlot()
    def onSelectionChanged(self): # Called when the selection changes in the viewer
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
        self.removeFittedRectangles()
        self.removeFittedEllipses()
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
        # Temporarily disable sorting while populating
        self.regions_table.setSortingEnabled(False)
        
        self.regions_table.setRowCount(len(self.workingBlobs))
        self.regions_table.setVerticalHeaderLabels(["-" for i in range(len(self.workingBlobs))])
        #fill the table with the selected blobs
        for blob in self.workingBlobs:
            row = self.workingBlobs.index(blob)
            # ID column
            id_item = NumericTableWidgetItem(str(blob.id))
            id_item.setData(Qt.UserRole, blob.id)  # Store numeric value for sorting
            id_item.setTextAlignment(Qt.AlignCenter)
            self.regions_table.setItem(row, 0, id_item)
            
            # Property columns
            for i, prop in enumerate(self.properties):
                value = self.geometricData[blob.id][prop]
                # Format the display text
                if isinstance(value, (int, float)):
                    # Format with the specified number of decimals
                    display_text = f"{value:.{self.properties[prop]['round']}f}"
                    prop_item = NumericTableWidgetItem(display_text)
                    prop_item.setData(Qt.UserRole, value)  # Store numeric value for sorting
                else:
                    prop_item = NumericTableWidgetItem(str(value))
                    prop_item.setData(Qt.UserRole, str(value))  # Store string for sorting
                prop_item.setTextAlignment(Qt.AlignRight)
                self.regions_table.setItem(row, i+1, prop_item)

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
        
        # Re-enable sorting after populating
        self.regions_table.setSortingEnabled(True)
        return

########################################################################################
# FITTED SHAPES FUNCTIONS
########################################################################################

    # toggle the visibility of the fitted rectangles in the viewer
    def toggleRectangles(self):    
        if self.btnToggleRectangles.text() == "Show Rectangles":
            self.btnToggleRectangles.setText("Hide Rectangles")
            self.displayFittedRectangles()
        else:
            self.btnToggleRectangles.setText("Show Rectangles")
            self.removeFittedRectangles()
        return

    # toggle the visibility of the fitted ellipses in the viewer
    def toggleEllipses(self):    
        if self.btnToggleEllipses.text() == "Show Ellipses":
            self.btnToggleEllipses.setText("Hide Ellipses")
            self.displayFittedEllipses()
        else:
            self.btnToggleEllipses.setText("Show Ellipses")
            self.removeFittedEllipses()
        return

    # display fitted rectangles in the viewer
    def displayFittedRectangles(self):
        for blob in self.workingBlobs:
            min_row, min_col, _, _ = blob.bbox
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
            self.fittedRectangleEntities.append(newItemR)
        return

    # display fitted ellipses with axes in the viewer
    def displayFittedEllipses(self):
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
            self.fittedEllipseEntities.append(newItemE)
            
            ######################################## ELLIPSE AXES
            # Draw major axis
            major_half = region.major_axis_length / 2
            major_x1 = cx_full + major_half * cos_angle
            major_y1 = cy_full + major_half * sin_angle
            major_x2 = cx_full - major_half * cos_angle
            major_y2 = cy_full - major_half * sin_angle
            
            major_pen = QPen(QColor(255, 255, 0, 191))  # 75% transparent yellow
            major_pen.setWidth(2)
            major_pen.setCosmetic(True)
            
            major_axis_item = self.activeviewer.scene.addLine(major_x1, major_y1, major_x2, major_y2, major_pen)
            major_axis_item.setZValue(11)  # Draw above ellipse
            self.fittedEllipseEntities.append(major_axis_item)
            
            # Draw minor axis
            minor_half = region.minor_axis_length / 2
            minor_x1 = cx_full - minor_half * sin_angle
            minor_y1 = cy_full + minor_half * cos_angle
            minor_x2 = cx_full + minor_half * sin_angle
            minor_y2 = cy_full - minor_half * cos_angle
            
            minor_pen = QPen(QColor(0, 255, 255, 191))  # 75% transparent cyan
            minor_pen.setWidth(2)
            minor_pen.setCosmetic(True)
            
            minor_axis_item = self.activeviewer.scene.addLine(minor_x1, minor_y1, minor_x2, minor_y2, minor_pen)
            minor_axis_item.setZValue(11)  # Draw above ellipse
            self.fittedEllipseEntities.append(minor_axis_item)
        return

    # remove fitted rectangles from the viewer
    def removeFittedRectangles(self):
        if self.fittedRectangleEntities:
            for item in self.fittedRectangleEntities:
                self.activeviewer.scene.removeItem(item)
            self.fittedRectangleEntities = []
            self.btnToggleRectangles.setText("Show Rectangles")
        return

    # remove fitted ellipses from the viewer
    def removeFittedEllipses(self):
        if self.fittedEllipseEntities:
            for item in self.fittedEllipseEntities:
                self.activeviewer.scene.removeItem(item)
            self.fittedEllipseEntities = []
            self.btnToggleEllipses.setText("Show Ellipses")
        return

    # Handle table selection changes to highlight the corresponding region
    @pyqtSlot()
    def onTableSelectionChanged(self):
        """Highlight the region corresponding to the selected table row"""
        # Remove previous highlight
        self.removeHighlight()
        
        # Get selected row
        selected_rows = self.regions_table.selectedItems()
        if not selected_rows:
            return
        
        # Get the blob ID from the first column of the selected row
        row = selected_rows[0].row()
        id_item = self.regions_table.item(row, 0)
        if not id_item:
            return
        
        try:
            blob_id = int(id_item.text())
        except (ValueError, AttributeError):
            return
        
        # Find the blob with this ID
        blob = None
        for b in self.workingBlobs:
            if b.id == blob_id:
                blob = b
                break
        
        if not blob:
            return
        
        try:
            # Create a thick colored outline for the blob
            pen = QPen(QColor(255, 255, 0))  # Yellow color
            pen.setWidth(5)
            pen.setCosmetic(True)
            
            # Create polygon from blob contour
            points = [QPointF(x, y) for x, y in blob.contour]
            polygon = QPolygonF(points)
            
            # Add to scene
            outline_item = self.activeviewer.scene.addPolygon(polygon, pen, QBrush())
            outline_item.setZValue(12)  # Draw on top
            
            self.highlightedEntity = outline_item
        except (AttributeError, RuntimeError):
            # Blob might have been deleted or scene no longer valid
            pass
    
    # Remove the highlighted region outline
    def removeHighlight(self):
        """Remove the highlighted region outline from the scene"""
        if self.highlightedEntity:
            try:
                self.activeviewer.scene.removeItem(self.highlightedEntity)
            except (AttributeError, RuntimeError):
                # Scene or item might no longer be valid
                pass
            self.highlightedEntity = None

########################################################################################
# COLORIZE FUNCTIONS
########################################################################################

    # called when property selection changes - update min/max fields
    def onPropertyChanged(self, property_name):
        """Update min/max input fields when property selection changes"""
        if property_name and self.workingBlobs and len(self.workingBlobs) > 0:
            values = [self.geometricData[blob.id][property_name] for blob in self.workingBlobs]
            min_value = min(values)
            max_value = max(values)
            self.propertyMinInput.setText(str(min_value))
            self.propertyMaxInput.setText(str(max_value))
        return

    # called when min/max range is manually edited - update colorization
    def onColorRangeChanged(self):
        """Re-apply colorization when min/max values are manually changed"""
        if self.colorizedEntities:  # Only update if currently colorized
            self.colorizeByProperty()
        return

    # colorize the shapes by a specific property
    def colorizeByProperty(self):
        # Check if there are working blobs
        if not self.workingBlobs or len(self.workingBlobs) == 0:
            return
        
        # determine which property is selected
        selected_property = self.propertyChooserInput.currentText()
        if not selected_property:
            return
        
        # Get min/max from input fields, or calculate if empty
        try:
            min_value = float(self.propertyMinInput.text())
            max_value = float(self.propertyMaxInput.text())
        except (ValueError, AttributeError):
            try:
                values = [self.geometricData[blob.id][selected_property] for blob in self.workingBlobs]
                if not values:
                    return
                min_value = min(values)
                max_value = max(values)
                self.propertyMinInput.setText(str(min_value))
                self.propertyMaxInput.setText(str(max_value))
            except (KeyError, AttributeError):
                return
        
        self.displayColorizedEntities(selected_property, min_value, max_value)
        return

    # display colorized shapes in the viewer
    def displayColorizedEntities(self, property, min_value, max_value):
        self.removeColorizedEntities()  # remove previous colorized entities, if any
        value_range = max_value - min_value if max_value != min_value else 1.0  # avoid division by zero
        
        # Check if using centered/diverging color ramp
        use_centered = self.cbCenteredRamp.isChecked()
        
        if use_centered:
            try:
                center_value = float(self.propertyCenterInput.text())
            except (ValueError, AttributeError):
                center_value = 0.0
                self.propertyCenterInput.setText("0")
        
        # create a color map
        for blob in self.workingBlobs:
            min_row, min_col, _, _ = blob.bbox
            value = self.geometricData[blob.id][property]
            # Clamp value to [min_value, max_value] range
            value = max(min_value, min(value, max_value))
            
            if use_centered:
                # Diverging color ramp: blue (low) -> gray (center) -> red (high)
                if value < center_value:
                    # Below center: interpolate from blue to gray
                    lower_range = center_value - min_value if center_value > min_value else 1.0
                    t = (center_value - value) / lower_range  # 1.0 at min, 0.0 at center
                    r = int(128 * (1 - t))  # 0 to 128
                    g = int(128 * (1 - t))  # 0 to 128
                    b = int(128 + 127 * t)  # 128 to 255
                elif value > center_value:
                    # Above center: interpolate from gray to red
                    upper_range = max_value - center_value if max_value > center_value else 1.0
                    t = (value - center_value) / upper_range  # 0.0 at center, 1.0 at max
                    r = int(128 + 127 * t)  # 128 to 255
                    g = int(128 * (1 - t))  # 128 to 0
                    b = int(128 * (1 - t))  # 128 to 0
                else:
                    # Exactly at center: gray
                    r, g, b = 128, 128, 128
                color = QColor(r, g, b, 255)
            else:
                # Standard sequential ramp: blue (low) to red (high)
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
            polygon = QPolygonF([QPointF(float(point[0][0])+min_col+0.5, float(point[0][1])+min_row+0.5) for point in cnt])
            newItemC = self.activeviewer.scene.addPolygon(polygon, pen, brush)
            newItemC.setZValue(10)  # Draw above most items
            self.colorizedEntities.append(newItemC)
        return
    
    # colorize the shapes by squareness/roundness
    def colorizeByShape(self):
        self.removeColorizedEntities()  # remove previous colorized entities, if any
        for blob in self.workingBlobs:
            min_row, min_col, _, _ = blob.bbox
            # compute squareness as... 
            rectangle_area = self.geometricData[blob.id]["majSideRectangle"] * self.geometricData[blob.id]["minSideRectangle"]
            value = self.geometricData[blob.id]["area"] / rectangle_area
            value = max(0.0, min(value, 1.0))  # clamp to [0, 1]
            tMin = float(self.thresholdInput0.text())
            tMax = float(self.thresholdInput1.text())
            # map ramped value to [0, 1] based on thresholds
            if value <= tMin:
                value = 0.0
            elif value >= tMax:
                value = 1.0
            else:
                value = (value - tMin) / (tMax - tMin)
            value = value * value  # make the ramp quadratic for better visual effect
            # map value to color
            r = int(value * 255)
            g = 0
            b = int((1 - value) * 255)
            color = QColor(r, g, b, 255)  # fully opaque
            pen = QPen(Qt.NoPen)
            brush = QBrush(color)
            # draw the blob's filled contour
            contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnt = contours[0]
            polygon = QPolygonF([QPointF(float(point[0][0])+min_col+0.5, float(point[0][1])+min_row+0.5) for point in cnt])
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
        for blob in self.workingBlobs:
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

    # Show dialog to select which attributes to add
    def showAddAttributesDialog(self):
        # Create a modal dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Attributes to Add")
        dialog.setStyleSheet("background-color: rgb(40,40,40); color: white;")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Add instruction label
        info_label = QLabel("Select the geometric measurements to add as region attributes:")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Create checkboxes for each property that has attribute=True
        self.attribute_checkboxes = {}
        for prop in self.properties:
            if self.properties[prop].get("attribute", False):
                checkbox = QCheckBox(self.properties[prop]["name"])
                checkbox.setChecked(True)  # Default to checked
                self.attribute_checkboxes[prop] = checkbox
                layout.addWidget(checkbox)
        
        # Add buttons
        button_layout = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_none = QPushButton("Select None")
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")
        
        button_layout.addWidget(btn_select_all)
        button_layout.addWidget(btn_select_none)
        button_layout.addStretch()
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Connect buttons
        btn_select_all.clicked.connect(lambda: self.toggleAllCheckboxes(True))
        btn_select_none.clicked.connect(lambda: self.toggleAllCheckboxes(False))
        btn_ok.clicked.connect(dialog.accept)
        btn_cancel.clicked.connect(dialog.reject)
        
        # Show dialog and process result
        if dialog.exec_() == QDialog.Accepted:
            self.addAttributesToRegions()
    
    def toggleAllCheckboxes(self, checked):
        """Toggle all attribute checkboxes"""
        for checkbox in self.attribute_checkboxes.values():
            checkbox.setChecked(checked)
    
    def addAttributesToRegions(self):
        """Add selected geometric measurements as attributes to regions"""
        # Get selected attributes
        selected_attrs = [prop for prop, checkbox in self.attribute_checkboxes.items() if checkbox.isChecked()]
        
        if not selected_attrs:
            QMessageBox.information(self, "No Attributes Selected", "Please select at least one attribute to add.")
            return
        
        # Get the project's region_attributes
        project = self.activeviewer.project
        
        # For each selected attribute, check if it exists in the project's region_attributes
        # If not, create it
        attributes_added = []
        for prop in selected_attrs:
            if not project.region_attributes.has(prop):
                # Create a new attribute definition
                attr_def = {
                    'name': prop,
                    'type': 'decimal number',
                    'min': None,
                    'max': None,
                    'keywords': []
                }
                project.region_attributes.data.append(attr_def)
                attributes_added.append(prop)
        
        # If new attributes were added, update the UI
        if attributes_added:
            # Update the groupbox_blobpanel to show the new attributes
            parent = self.parent()
            if parent and hasattr(parent, 'groupbox_blobpanel'):
                parent.groupbox_blobpanel.updateRegionAttributes(project.region_attributes)
        
        # Now add the values to each blob's data dictionary
        for blob in self.workingBlobs:
            for prop in selected_attrs:
                # Get the computed value from geometricData
                value = self.geometricData[blob.id][prop]
                # Store it in the blob's data dictionary
                blob.data[prop] = value
        
        # If there's a currently displayed blob in the info panel, refresh it
        parent = self.parent()
        if parent and hasattr(parent, 'blob_with_info_displayed') and parent.blob_with_info_displayed:
            if parent.blob_with_info_displayed in self.workingBlobs:
                parent.updatePanelInfo(parent.blob_with_info_displayed)
        
        # Show success message
        msg = f"Added {len(selected_attrs)} geometric measurements to {len(self.workingBlobs)} regions."
        if attributes_added:
            msg += f"\n\nNew attribute definitions created: {', '.join(attributes_added)}"
        
        QMessageBox.information(self, "Success", msg)
