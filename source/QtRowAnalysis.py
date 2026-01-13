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

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QPointF, QEvent, QRectF
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF, QPainterPath, QFont
from PyQt5.QtWidgets import QWidget, QTableWidget, QTextEdit, QTableWidgetItem, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QGroupBox, QGraphicsPathItem, QComboBox
import math
import cv2
import numpy as np


class QtRowAnalysis(QWidget):
    """
    Widget for row analysis functionality.
    Provides three command buttons and a log area to display information.
    """

    def __init__(self, viewer, parent=None):
        super(QtRowAnalysis, self).__init__(parent)

        # DATA ##########################################################
        # active viewer
        self.activeviewer = viewer
        # the set of working blobs, that contain the blobs being analyzed
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        # data structure to hold recognized rows
        self.rowsData = None
        # color mode for displaying regions
        self.colorMode = "ID"  # Options: "NONE", "ID", "INCLINATION"

        # store geometric entities for overlay
        self.colorizedEntities = []
        self.polylineEntities = []
        self.lineSegmentData = []  # Store metadata for each line segment: (row_index, segment_index, point1, point2)
        self.inclinationLines = []  # Store inclination visualization lines
        self.segmentInclinationEntities = []  # Store segment-by-segment inclination visualizations
        
        # Cut mode state
        self.cutModeActive = False
        
        # Merge mode state
        self.mergeModeActive = False
        self.firstMergeBlob = None  # First blob selected for merge
        self.firstMergeBlobHighlight = None  # Highlight graphics for first blob
        self.blobToRowMap = {}  # Map blob to (row_index, position_in_row)


        # EVENTS ###########################################################
        # Connect to selectionChanged signal of the activeviewer
        if hasattr(self.activeviewer, 'selectionChanged'):
            self.activeviewer.selectionChanged.connect(self.onSelectionChanged)
        
        # Install event filter to catch mouse clicks in viewer
        self.activeviewer.viewport().installEventFilter(self)

        # INTERFACE ###########################################################
        self.setStyleSheet("background-color: rgb(40,40,40); color: white; QToolTip { background-color: rgb(50,50,50); color: white; border: 1px solid rgb(100,100,100); }")
        mainLayout = QVBoxLayout()

        # GROUP BOX for detection and editing controls
        controlsGroup = QGroupBox("Row Detection and Editing")
        controlsGroup.setStyleSheet("QGroupBox { background-color: rgb(45,45,45); color: white; border: 2px solid rgb(80,80,80); border-radius: 5px; margin-top: 10px; padding-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        controlsLayout = QVBoxLayout()
        
        # Tolerance parameters layout
        tolerance_layout = QHBoxLayout()
        
        lblYTolerance = QLabel("Y Centroid Gap:")
        self.editYTolerance = QLineEdit("0.3")
        self.editYTolerance.setMaximumWidth(60)
        self.editYTolerance.setToolTip("Tolerance for Y centroid position (relative to adjacent blob height)")

        lblYTBTolerance = QLabel("Y top/bottom Gap:")
        self.editYTBTolerance = QLineEdit("0.3")
        self.editYTBTolerance.setMaximumWidth(60)
        self.editYTBTolerance.setToolTip("Tolerance for Y top/bottom position (relative to adjacent blob height)")

        lblHeightTolerance = QLabel("Height Variation:")
        self.editHeightTolerance = QLineEdit("0.3")
        self.editHeightTolerance.setMaximumWidth(60)
        self.editHeightTolerance.setToolTip("Tolerance for height variation (relative to adjacent blob height)")
        
        lblXGapTolerance = QLabel("X Gap:")
        self.editXGapTolerance = QLineEdit("3.0")
        self.editXGapTolerance.setMaximumWidth(60)
        self.editXGapTolerance.setToolTip("Maximum X gap (relative to average blob width in row)")
        
        tolerance_layout.addWidget(lblYTolerance)
        tolerance_layout.addWidget(self.editYTolerance)
        tolerance_layout.addSpacing(20)
        tolerance_layout.addWidget(lblYTBTolerance)
        tolerance_layout.addWidget(self.editYTBTolerance)
        tolerance_layout.addSpacing(20)
        tolerance_layout.addWidget(lblHeightTolerance)
        tolerance_layout.addWidget(self.editHeightTolerance)
        tolerance_layout.addSpacing(20)
        tolerance_layout.addWidget(lblXGapTolerance)
        tolerance_layout.addWidget(self.editXGapTolerance)
        tolerance_layout.addStretch()
        
        controlsLayout.addLayout(tolerance_layout)

        # Buttons layout
        button_layout = QHBoxLayout()
        
        self.btnRecognize = QPushButton("Recognize Rows")
        self.btnRecognize.clicked.connect(self.recognizeRows)
        
        self.btnCutRow = QPushButton("✂ Cut Row")
        self.btnCutRow.setToolTip("Click to activate cut mode, then click near a polyline to split the row")
        self.btnCutRow.setCheckable(True)
        self.btnCutRow.clicked.connect(self.toggleCutMode)
        
        self.btnMergeRows = QPushButton("🔗 Merge Rows")
        self.btnMergeRows.setToolTip("Click to activate merge mode, then click on first/last regions of two different rows to connect them")
        self.btnMergeRows.setCheckable(True)
        self.btnMergeRows.clicked.connect(self.toggleMergeMode)
        
        button_layout.addWidget(self.btnRecognize)
        button_layout.addWidget(self.btnCutRow)
        button_layout.addWidget(self.btnMergeRows)
        button_layout.addStretch()
        
        controlsLayout.addLayout(button_layout)
        controlsGroup.setLayout(controlsLayout)
        mainLayout.addWidget(controlsGroup)

        # Table widget for row data
        self.rowsTable = QTableWidget()
        self.rowsTable.setColumnCount(6)
        self.rowsTable.setHorizontalHeaderLabels(["Color", "Regions", "Y pos", "Avg Height", "Width", "Inclination"])
        self.rowsTable.setStyleSheet("QTableWidget { background-color: rgb(50,50,50); color: white; gridline-color: rgb(80,80,80); } QHeaderView::section { background-color: rgb(60,60,60); color: white; }")
        self.rowsTable.setMinimumHeight(150)
        self.rowsTable.setEditTriggers(QTableWidget.NoEditTriggers)
        mainLayout.addWidget(self.rowsTable)
        
        # GROUP BOX for row analysis
        analysisGroup = QGroupBox("Row Analysis")
        analysisGroup.setStyleSheet("QGroupBox { background-color: rgb(45,45,45); color: white; border: 2px solid rgb(80,80,80); border-radius: 5px; margin-top: 10px; padding-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        analysisLayout = QVBoxLayout()
        
        # Color mode dropdown
        color_mode_layout = QHBoxLayout()
        lblColorMode = QLabel("Color Mode:")
        self.comboColorMode = QComboBox()
        self.comboColorMode.addItems(["NONE", "ID", "INCLINATION"])
        self.comboColorMode.setCurrentText("ID")
        self.comboColorMode.setToolTip("Select how to colorize regions: NONE (no color), ID (random pastel colors), INCLINATION (color ramp based on row angle)")
        self.comboColorMode.currentTextChanged.connect(self.onColorModeChanged)
        self.comboColorMode.setMaximumWidth(150)
        color_mode_layout.addWidget(lblColorMode)
        color_mode_layout.addWidget(self.comboColorMode)
        color_mode_layout.addStretch()
        analysisLayout.addLayout(color_mode_layout)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        self.btnAnalyzeInclination = QPushButton("Show Inclination")
        self.btnAnalyzeInclination.setToolTip("Compute and show/hide the inclination angle for each row by fitting a line through all centroids")
        self.btnAnalyzeInclination.setCheckable(True)
        self.btnAnalyzeInclination.clicked.connect(self.toggleInclination)
        
        self.btnSegmentInclination = QPushButton("Show Segment Angles")
        self.btnSegmentInclination.setToolTip("Show/hide the inclination angle for each segment between consecutive regions")
        self.btnSegmentInclination.setCheckable(True)
        self.btnSegmentInclination.clicked.connect(self.toggleSegmentInclination)
        
        buttons_layout.addWidget(self.btnAnalyzeInclination)
        buttons_layout.addWidget(self.btnSegmentInclination)
        buttons_layout.addStretch()
        
        analysisLayout.addLayout(buttons_layout)
        
        analysisGroup.setLayout(analysisLayout)
        mainLayout.addWidget(analysisGroup)

        # Log area - text display for output
        self.logArea = QTextEdit()
        self.logArea.setReadOnly(True)
        self.logArea.setStyleSheet("QTextEdit { background-color: rgb(50,50,50); color: white; }")
        self.logArea.setMinimumHeight(100)
        self.logArea.setMaximumHeight(120)
        mainLayout.addWidget(self.logArea)

        # Bottom row buttons
        bottom_layout = QHBoxLayout()
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.close)
        bottom_layout.setAlignment(Qt.AlignRight)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btnClose)
        mainLayout.addLayout(bottom_layout)

        # set the layout and window properties
        self.setLayout(mainLayout)
        self.setWindowTitle("Row Analysis")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        # Initialize log with selection info
        self.logSelectedRegions()

    # close the widget
    closewidget = pyqtSignal()
    
    def closeEvent(self, event):
        # remove colorized shapes and polylines, if any
        self.removeColorizedEntities()
        self.removePolylineEntities()
        self.removeInclinationLines()
        self.removeSegmentInclinationEntities()
        # Remove event filter
        self.activeviewer.viewport().removeEventFilter(self)
        # emit the signal to notify the main window
        self.closewidget.emit()
        super(QtRowAnalysis, self).closeEvent(event)

    @pyqtSlot()
    def onSelectionChanged(self):
        """Called when the selection changes in the viewer"""
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        self.writeLog("Selection changed. Now {} region(s) selected.".format(len(self.workingBlobs)))

    @pyqtSlot(str)
    def onColorModeChanged(self, mode):
        """Called when the color mode dropdown changes"""
        self.colorMode = mode
        if self.rowsData is not None and len(self.rowsData) > 0:
            self.displayRows()
            # Redisplay inclination and segment angles if active
            if self.btnAnalyzeInclination.isChecked():
                self.displayInclinationLines()
            if self.btnSegmentInclination.isChecked():
                self.displaySegmentInclination()

    def writeLog(self, message):
        """Write a message to the log area"""
        self.logArea.append(message)
    
    def eventFilter(self, obj, event):
        """
        Event filter to catch mouse clicks in the viewer when cut or merge mode is active.
        """
        if event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
            scenePos = self.activeviewer.mapToScene(event.pos())
            
            if self.cutModeActive:
                # Get click position in scene coordinates
                self.handleCutClick(scenePos.x(), scenePos.y())
                return True  # Event handled
            
            elif self.mergeModeActive:
                # Handle merge mode click on blobs
                self.handleMergeClick(scenePos.x(), scenePos.y())
                return True  # Event handled
        
        return super(QtRowAnalysis, self).eventFilter(obj, event)

    def logSelectedRegions(self):
        num_selected = len(self.workingBlobs)
        # Count unique classes
        classes = set()
        for blob in self.workingBlobs:
            classes.add(blob.class_name)
        num_classes = len(classes)
        self.writeLog("{} selected regions. {} classes [{}]".format(num_selected, num_classes, ", ".join(sorted(classes))))
        self.writeLog("")

    ########################################################################################
    # COMMAND FUNCTIONS (STUBS)
    ########################################################################################

    @pyqtSlot()
    def recognizeRows(self):
        """
        Recognize rows using incremental algorithm.
        """
        if len(self.workingBlobs) == 0:
            self.writeLog("No regions selected!")
            return

        self.logArea.clear()
        self.writeLog("Recognizing rows...")
        
        # Read tolerance values from input fields
        try:
            y_tolerance_factor = float(self.editYTolerance.text())
            ytb_tolerance_factor = float(self.editYTBTolerance.text())
            height_tolerance_factor = float(self.editHeightTolerance.text())
            x_gap_factor = float(self.editXGapTolerance.text())
        except ValueError:
            self.writeLog("Error: Invalid tolerance values. Using defaults (0.3, 0.3, 0.3, 3.0)")
            y_tolerance_factor = 0.3
            ytb_tolerance_factor = 0.3
            height_tolerance_factor = 0.3
            x_gap_factor = 3.0
        
        # Detect rows using incremental method
        self.rowsData = self.detectRowsIncremental(y_tolerance_factor, ytb_tolerance_factor, height_tolerance_factor, x_gap_factor)
        
        # Log results
        self.writeLog("Found {} row(s)".format(len(self.rowsData)))
        
        # Compute inclination for all rows automatically
        self.computeInclination()
        
        # Populate table with row data
        self.populateRowsTable()
        
        # Display rows
        self.displayRows()
        
        # Redisplay visualizations if they were active
        if self.btnAnalyzeInclination.isChecked():
            self.displayInclinationLines()
        if self.btnSegmentInclination.isChecked():
            self.displaySegmentInclination()

    def computeInclination(self):
        """
        Compute the inclination for all rows.
        """
        if self.rowsData is None or len(self.rowsData) == 0:
            return
        
        for row in self.rowsData:
            if row['num_blobs'] < 2:
                row['inclination_deg'] = 0.0
                row['inclination_rad'] = 0.0
                continue
            
            # Get all centroids
            centroids_x = [blob.centroid[0] for blob in row['blobs']]
            centroids_y = [blob.centroid[1] for blob in row['blobs']]
            
            # Fit a line using least squares: y = mx + b
            # Using numpy polyfit for simplicity
            coeffs = np.polyfit(centroids_x, centroids_y, 1)
            slope = coeffs[0]
            intercept = coeffs[1]
            
            # Convert slope to angle in degrees
            # Negate the slope because image Y-axis points downward
            # Positive angle = counterclockwise rotation from horizontal
            angle_rad = math.atan(-slope)
            angle_deg = math.degrees(angle_rad)
            
            row['inclination_deg'] = angle_deg
            row['inclination_rad'] = angle_rad
            row['fit_slope'] = slope
            row['fit_intercept'] = intercept
    
    @pyqtSlot()
    def toggleInclination(self):
        """
        Toggle the display of inclination lines.
        """
        if self.rowsData is None or len(self.rowsData) == 0:
            self.writeLog("No rows detected. Please run row detection first.")
            self.btnAnalyzeInclination.setChecked(False)
            return
        
        if self.btnAnalyzeInclination.isChecked():
            # Show inclination lines
            self.displayInclinationLines()
            
            # Update button appearance
            self.btnAnalyzeInclination.setStyleSheet("background-color: rgb(100, 150, 200); color: white; font-weight: bold;")
            self.btnAnalyzeInclination.setText("Hide Inclination")
        else:
            # Hide inclination
            self.removeInclinationLines()
            self.btnAnalyzeInclination.setStyleSheet("")
            self.btnAnalyzeInclination.setText("Show Inclination")
    
    @pyqtSlot()
    def toggleSegmentInclination(self):
        """
        Toggle the display of segment-by-segment inclination angles.
        """
        if self.rowsData is None or len(self.rowsData) == 0:
            self.writeLog("No rows detected. Please run row detection first.")
            self.btnSegmentInclination.setChecked(False)
            return
        
        if self.btnSegmentInclination.isChecked():
            # Show segment inclination angles
            self.displaySegmentInclination()
            
            # Update button appearance
            self.btnSegmentInclination.setStyleSheet("background-color: rgb(150, 100, 200); color: white; font-weight: bold;")
            self.btnSegmentInclination.setText("Hide Segment Angles")
        else:
            # Hide segment inclination
            self.removeSegmentInclinationEntities()
            self.btnSegmentInclination.setStyleSheet("")
            self.btnSegmentInclination.setText("Show Segment Angles")
    
    @pyqtSlot()
    def toggleCutMode(self):
        """
        Toggle cut mode on/off.
        """
        self.cutModeActive = self.btnCutRow.isChecked()
        
        if self.cutModeActive:
            # Check if there are rows to cut
            if self.rowsData is None or len(self.rowsData) == 0:
                self.writeLog("No rows detected. Please run row detection first.")
                self.btnCutRow.setChecked(False)
                self.cutModeActive = False
                return
            
            # Deactivate merge mode if active
            if self.mergeModeActive:
                self.btnMergeRows.setChecked(False)
                self.btnMergeRows.setStyleSheet("")
                self.mergeModeActive = False
                self.clearMergeSelection()
            
            self.btnCutRow.setStyleSheet("background-color: rgb(200, 100, 100); color: white; font-weight: bold;")
            self.writeLog("Cut mode activated. Click near a polyline to split the row.")
            self.activeviewer.setCursor(Qt.SizeHorCursor)
        else:
            self.btnCutRow.setStyleSheet("")
            self.writeLog("Cut mode deactivated.")
            self.activeviewer.setCursor(Qt.ArrowCursor)
    
    @pyqtSlot()
    def toggleMergeMode(self):
        """
        Toggle merge mode on/off.
        """
        self.mergeModeActive = self.btnMergeRows.isChecked()
        
        if self.mergeModeActive:
            # Check if there are rows to merge
            if self.rowsData is None or len(self.rowsData) == 0:
                self.writeLog("No rows detected. Please run row detection first.")
                self.btnMergeRows.setChecked(False)
                self.mergeModeActive = False
                return
            
            # Deactivate cut mode if active
            if self.cutModeActive:
                self.btnCutRow.setChecked(False)
                self.btnCutRow.setStyleSheet("")
                self.cutModeActive = False
            
            self.btnMergeRows.setStyleSheet("background-color: rgb(100, 150, 200); color: white; font-weight: bold;")
            self.clearMergeSelection()
            self.writeLog("Merge mode activated. Click on the first/last region of a row.")
            self.activeviewer.setCursor(Qt.PointingHandCursor)
        else:
            self.btnMergeRows.setStyleSheet("")
            self.clearMergeSelection()
            self.writeLog("Merge mode deactivated.")
            self.activeviewer.setCursor(Qt.ArrowCursor)
    
    def populateRowsTable(self):
        """
        Populate the table with detected rows data.
        """
        if self.rowsData is None or len(self.rowsData) == 0:
            self.rowsTable.setRowCount(0)
            return
        self.rowsTable.setRowCount(len(self.rowsData))
        for i, row in enumerate(self.rowsData):
            # Color indicator
            color = self.getPastelColor(i, len(self.rowsData))
            color_item = QTableWidgetItem("")
            color_item.setBackground(QBrush(color))
            self.rowsTable.setItem(i, 0, color_item)
            # Number of regions
            self.rowsTable.setItem(i, 1, QTableWidgetItem(str(row['num_blobs'])))
            # Y position
            self.rowsTable.setItem(i, 2, QTableWidgetItem("{:.1f}".format(row['centroid_y'])))
            # Average height
            self.rowsTable.setItem(i, 3, QTableWidgetItem("{:.1f}".format(row['avg_height'])))
            # Width
            self.rowsTable.setItem(i, 4, QTableWidgetItem("{:.1f}".format(row['width'])))
            # Inclination
            if 'inclination_deg' in row:
                self.rowsTable.setItem(i, 5, QTableWidgetItem("{:.2f}°".format(row['inclination_deg'])))
            else:
                self.rowsTable.setItem(i, 5, QTableWidgetItem("-"))
        self.rowsTable.resizeColumnsToContents()

    ########################################################################################
    # ROW DETECTION ALGORITHM

    def detectRowsIncremental(self, y_tolerance_factor=0.3, ytb_tolerance_factor=0.3, height_tolerance_factor=0.3, x_gap_factor=3.0):
        """
        Detect rows incrementally by building rows one at a time.
        A blob is added to a row if it's compatible with the last (rightmost) blob in the row:
        - Its centroid Y is within tolerance of the last blob's Y (tolerance based on last blob's height)
        - Its top and bottom Y positions are within tolerance (tolerance based on last blob's height)
        - Its height is within tolerance of the last blob's height
        - The X gap is not too large (tolerance based on average blob width in row)
        
        Args:
            y_tolerance_factor: Tolerance for Y centroid position (relative to last blob height)
            ytb_tolerance_factor: Tolerance for Y top/bottom position (relative to last blob height)
            height_tolerance_factor: Tolerance for height variation (relative to last blob height)
            x_gap_factor: Maximum X gap (relative to average blob width in row)
            
        Returns:
            List of row objects, each containing blobs and metadata
        """
        if len(self.workingBlobs) == 0:
            return []
        
        # Keep track of unassigned blobs
        unassigned = self.workingBlobs[:]
        rows = []
        
        while unassigned:
            # Start a new row with the first unassigned blob (leftmost by X)
            unassigned.sort(key=lambda b: b.centroid[0])
            first_blob = unassigned.pop(0)
            
            current_row = {
                'blobs': [first_blob],
                'centroid_y': first_blob.centroid[1],
                'avg_height': first_blob.bbox[3],
                'min_y': first_blob.bbox[0],
                'max_y': first_blob.bbox[0] + first_blob.bbox[3]
            }
            
            # Try to add more blobs to this row
            while unassigned:
                # Get the rightmost (last) blob in the current row
                last_blob = current_row['blobs'][-1]
                last_y = last_blob.centroid[1]
                last_height = last_blob.bbox[3]
                last_x = last_blob.centroid[0]
                last_top = last_blob.bbox[0]
                last_bottom = last_blob.bbox[0] + last_blob.bbox[3]
                
                # Calculate tolerances based on the last blob
                y_tolerance = last_height * y_tolerance_factor
                ytb_tolerance = last_height * ytb_tolerance_factor
                
                # Calculate average width of blobs in current row for X gap tolerance
                avg_width = sum([b.bbox[2] for b in current_row['blobs']]) / len(current_row['blobs'])
                x_gap_tolerance = avg_width * x_gap_factor
                
                # Find the best compatible blob (leftmost among compatible ones that are to the RIGHT)
                best_blob = None
                best_x = float('inf')
                
                for blob in unassigned:
                    blob_y = blob.centroid[1]
                    blob_height = blob.bbox[3]
                    blob_x = blob.centroid[0]
                    blob_top = blob.bbox[0]
                    blob_bottom = blob.bbox[0] + blob.bbox[3]
                    
                    # Only consider blobs to the RIGHT of the last blob
                    if blob_x <= last_x:
                        continue
                    
                    # Check X gap constraint (gap should not be too large)
                    x_gap = blob_x - last_x
                    if x_gap > x_gap_tolerance:
                        continue
                    
                    # Check Y centroid compatibility with last blob (tolerance based on last blob's height)
                    y_distance = abs(blob_y - last_y)
                    if y_distance > y_tolerance:
                        continue
                    
                    # Check Y top/bottom compatibility (tolerance based on last blob's height)
                    top_gap = abs(blob_top - last_top)
                    bottom_gap = abs(blob_bottom - last_bottom)
                    if bottom_gap > ytb_tolerance:
                        continue
                    if top_gap > ytb_tolerance:
                        continue 

                    # Check height compatibility with last blob (tolerance based on last blob's height)
                    height_ratio = blob_height / last_height
                    if not ((1.0 - height_tolerance_factor) <= height_ratio <= (1.0 + height_tolerance_factor)):
                        continue
                    
                    # This blob passes all checks - it's the leftmost compatible one, so take it
                    best_blob = blob
                    break  # Exit the loop immediately
                
                if best_blob is None:
                    # No more compatible blobs for this row
                    break
                
                # Add the best blob to the current row
                current_row['blobs'].append(best_blob)
                unassigned.remove(best_blob)
                
                # Update row statistics
                current_row['centroid_y'] = sum([b.centroid[1] for b in current_row['blobs']]) / len(current_row['blobs'])
                current_row['avg_height'] = sum([b.bbox[3] for b in current_row['blobs']]) / len(current_row['blobs'])
                current_row['min_y'] = min(current_row['min_y'], best_blob.bbox[0])
                current_row['max_y'] = max(current_row['max_y'], best_blob.bbox[0] + best_blob.bbox[3])
            
            rows.append(current_row)
        
        # Sort blobs within each row by X coordinate and compute final metadata
        for row in rows:
            row['blobs'].sort(key=lambda b: b.centroid[0])
            row['num_blobs'] = len(row['blobs'])
            row['min_x'] = min([b.bbox[1] for b in row['blobs']])
            row['max_x'] = max([b.bbox[1] + b.bbox[2] for b in row['blobs']])
            row['height'] = row['max_y'] - row['min_y']
            row['width'] = row['max_x'] - row['min_x']
        
        # Sort rows: primarily by Y position, secondarily by X position for rows at similar Y
        # Use average height as tolerance for "similar Y"
        avg_row_height = sum([r['avg_height'] for r in rows]) / len(rows) if rows else 0
        y_tolerance = avg_row_height * 0.5  # Rows within 50% of avg height are considered "same level"
        
        def row_sort_key(row):
            # Quantize Y position to group similar rows, then sort by X within groups
            y_bucket = int(row['centroid_y'] / y_tolerance) if y_tolerance > 0 else row['centroid_y']
            return (y_bucket, row['min_x'])
        
        rows.sort(key=row_sort_key)
        
        return rows


    ########################################################################################

    def displayRows(self):
        """
        Display blobs colorized by their row assignment.
        """
        if self.rowsData is None or len(self.rowsData) == 0:
            return
        
        self.removeColorizedEntities()
        self.removePolylineEntities()
        self.lineSegmentData = []  # Clear line segment metadata
        self.blobToRowMap = {}  # Clear blob-to-row mapping
        
        # Calculate max absolute inclination for color ramp
        max_abs_inclination = 0.0
        if self.colorMode == "INCLINATION":
            for row in self.rowsData:
                if 'inclination_deg' in row:
                    max_abs_inclination = max(max_abs_inclination, abs(row['inclination_deg']))
        
        for row_index, row in enumerate(self.rowsData):
            # Determine color based on mode
            if self.colorMode == "NONE":
                # Don't draw filled blobs
                pass
            elif self.colorMode == "ID":
                color = self.getPastelColor(row_index, len(self.rowsData))
                pen = QPen(Qt.NoPen)
                brush = QBrush(color)
                
                # Draw filled blobs
                for blob in row['blobs']:
                    min_row, min_col, _, _ = blob.bbox
                    contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cnt = contours[0]
                    polygon = QPolygonF([QPointF(float(point[0][0])+min_col+0.5, float(point[0][1])+min_row+0.5) for point in cnt])
                    newItemC = self.activeviewer.scene.addPolygon(polygon, pen, brush)
                    newItemC.setZValue(10)
                    self.colorizedEntities.append(newItemC)
            
            elif self.colorMode == "INCLINATION":
                # Get inclination-based color
                if 'inclination_deg' in row and max_abs_inclination > 0:
                    color = self.getInclinationColor(row['inclination_deg'], max_abs_inclination)
                else:
                    color = QColor(128, 128, 128)  # Grey for no inclination data
                
                pen = QPen(Qt.NoPen)
                brush = QBrush(color)
                
                # Draw filled blobs
                for blob in row['blobs']:
                    min_row, min_col, _, _ = blob.bbox
                    contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cnt = contours[0]
                    polygon = QPolygonF([QPointF(float(point[0][0])+min_col+0.5, float(point[0][1])+min_row+0.5) for point in cnt])
                    newItemC = self.activeviewer.scene.addPolygon(polygon, pen, brush)
                    newItemC.setZValue(10)
                    self.colorizedEntities.append(newItemC)
            
            # Build blob-to-row mapping for merge functionality
            for pos, blob in enumerate(row['blobs']):
                self.blobToRowMap[blob] = (row_index, pos)
            
            # Draw line segments connecting consecutive regions
            if len(row['blobs']) > 1:
                # Create pen for the lines (contrasting color for visibility)
                line_pen = QPen(QColor(0, 0, 0))  # Black for high contrast
                line_pen.setWidth(3)
                line_pen.setCosmetic(True)
                
                # Draw a line from each region to the next one
                for i in range(len(row['blobs']) - 1):
                    blob1 = row['blobs'][i]
                    blob2 = row['blobs'][i + 1]
                    
                    point1 = QPointF(blob1.centroid[0], blob1.centroid[1])
                    point2 = QPointF(blob2.centroid[0], blob2.centroid[1])
                    
                    line_item = self.activeviewer.scene.addLine(point1.x(), point1.y(), 
                                                                  point2.x(), point2.y(), 
                                                                  line_pen)
                    line_item.setZValue(15)  # Draw above blobs
                    self.polylineEntities.append(line_item)
                    
                    # Store line segment metadata for cut functionality
                    self.lineSegmentData.append((row_index, i, point1, point2))
            
            # Draw white dots at centroids
            dot_pen = QPen(Qt.NoPen)
            dot_brush = QBrush(QColor(255, 255, 255))  # White
            dot_radius = 5
            
            for blob in row['blobs']:
                center = QPointF(blob.centroid[0], blob.centroid[1])
                dot_item = self.activeviewer.scene.addEllipse(
                    center.x() - dot_radius, center.y() - dot_radius,
                    dot_radius * 2, dot_radius * 2,
                    dot_pen, dot_brush
                )
                dot_item.setZValue(16)  # Draw above lines
                self.polylineEntities.append(dot_item)
            
            # Draw row number on first blob (above centroid)
            first_blob = row['blobs'][0]
            text_x = first_blob.centroid[0]
            
            text_item = self.activeviewer.scene.addText(str(row_index + 1))
            text_item.setDefaultTextColor(QColor(255, 255, 255))  # White
            
            # Position above the first blob's centroid by text height + 5 pixels
            text_height = text_item.boundingRect().height()
            text_y = first_blob.centroid[1] - text_height - 2
            
            text_item.setPos(text_x - text_item.boundingRect().width() / 2, text_y)  # Center the text
            text_item.setZValue(17)  # Draw above dots
            self.polylineEntities.append(text_item)
        return

    # remove colorized shapes from the viewer
    def removeColorizedEntities(self):
        if self.colorizedEntities:
            for item in self.colorizedEntities:
                self.activeviewer.scene.removeItem(item)
            self.colorizedEntities = []
        return

    def removePolylineEntities(self):
        """
        Remove all polylines from the scene.
        """
        if self.polylineEntities:
            for item in self.polylineEntities:
                self.activeviewer.scene.removeItem(item)
            self.polylineEntities = []
        return
    
    def removeInclinationLines(self):
        """
        Remove all inclination lines from the scene.
        """
        if self.inclinationLines:
            for item in self.inclinationLines:
                self.activeviewer.scene.removeItem(item)
            self.inclinationLines = []
        return
    
    def removeSegmentInclinationEntities(self):
        """
        Remove all segment inclination visualizations from the scene.
        """
        if self.segmentInclinationEntities:
            for item in self.segmentInclinationEntities:
                self.activeviewer.scene.removeItem(item)
            self.segmentInclinationEntities = []
        return
    
    def displayInclinationLines(self):
        """
        Display inclination lines for each row with angle labels.
        """
        self.removeInclinationLines()
        
        if self.rowsData is None or len(self.rowsData) == 0:
            return
        
        for row_index, row in enumerate(self.rowsData):
            if 'fit_slope' not in row or row['num_blobs'] < 2:
                continue
            
            slope = row['fit_slope']
            intercept = row['fit_intercept']
            
            # Calculate line endpoints across the row's extent
            x_start = row['min_x']
            x_end = row['max_x']
            y_start = slope * x_start + intercept
            y_end = slope * x_end + intercept
            
            # Create thick white line with black outline for inclination
            # Draw black outline first (wider)
            outline_pen = QPen(QColor(0, 0, 0))
            outline_pen.setWidth(6)
            outline_pen.setCosmetic(True)
            
            outline_item = self.activeviewer.scene.addLine(x_start, y_start, x_end, y_end, outline_pen)
            outline_item.setZValue(18)
            self.inclinationLines.append(outline_item)
            
            # Draw white line on top
            line_pen = QPen(QColor(255, 255, 255))
            line_pen.setWidth(4)
            line_pen.setCosmetic(True)
            
            line_item = self.activeviewer.scene.addLine(x_start, y_start, x_end, y_end, line_pen)
            line_item.setZValue(19)
            self.inclinationLines.append(line_item)
            
            # Add angle text at the middle of the line
            x_mid = (x_start + x_end) / 2
            y_mid = (y_start + y_end) / 2
            
            angle_text = "{:.2f}°".format(row['inclination_deg'])
            
            # Create text item to measure size
            font = QFont()
            font.setBold(True)
            
            # Create simple text item with black color
            text_item = self.activeviewer.scene.addText(angle_text)
            text_item.setFont(font)
            text_item.setDefaultTextColor(QColor(0, 0, 0))  # Black text
            
            text_rect = text_item.boundingRect()
            text_width = text_rect.width()
            text_height = text_rect.height()
            
            # Create background rectangle (half height of font)
            padding = 3
            bg_height = text_height / 2 + padding * 2
            bg_width = text_width + padding * 2
            bg_x = x_mid - bg_width / 2
            bg_y = y_mid - bg_height - 5
            
            # Draw black outline rectangle
            outline_rect_pen = QPen(QColor(0, 0, 0))
            outline_rect_pen.setWidth(2)
            outline_rect_pen.setCosmetic(True)
            bg_brush = QBrush(QColor(255, 255, 255))  # White fill
            
            bg_rect = self.activeviewer.scene.addRect(bg_x, bg_y, bg_width, bg_height, outline_rect_pen, bg_brush)
            bg_rect.setZValue(20)
            self.inclinationLines.append(bg_rect)
            
            # Position text centered in the background rectangle
            text_x = bg_x + padding
            text_y = bg_y + (bg_height - text_height) / 2
            text_item.setPos(text_x, text_y)
            text_item.setZValue(21)
            self.inclinationLines.append(text_item)
        
        return
    
    def displaySegmentInclination(self):
        """
        Display inclination angles for each segment between consecutive regions in each row.
        """
        self.removeSegmentInclinationEntities()
        
        if self.rowsData is None or len(self.rowsData) == 0:
            return
        
        # Calculate max absolute inclination across all segments for color normalization
        max_abs_segment_angle = 0.0
        for row in self.rowsData:
            if row['num_blobs'] < 2:
                continue
            for i in range(len(row['blobs']) - 1):
                blob1 = row['blobs'][i]
                blob2 = row['blobs'][i + 1]
                dx = blob2.centroid[0] - blob1.centroid[0]
                dy = blob2.centroid[1] - blob1.centroid[1]
                angle_rad = math.atan2(-dy, dx)
                angle_deg = math.degrees(angle_rad)
                max_abs_segment_angle = max(max_abs_segment_angle, abs(angle_deg))
        
        for row_index, row in enumerate(self.rowsData):
            if row['num_blobs'] < 2:
                continue
            
            # Analyze each segment between consecutive blobs
            for i in range(len(row['blobs']) - 1):
                blob1 = row['blobs'][i]
                blob2 = row['blobs'][i + 1]
                
                x1, y1 = blob1.centroid[0], blob1.centroid[1]
                x2, y2 = blob2.centroid[0], blob2.centroid[1]
                
                # Calculate segment inclination
                dx = x2 - x1
                dy = y2 - y1
                
                # Calculate angle (negate dy for image coordinates)
                angle_rad = math.atan2(-dy, dx)
                angle_deg = math.degrees(angle_rad)
                
                # Position label at midpoint of segment
                x_mid = (x1 + x2) / 2
                y_mid = (y1 + y2) / 2
                
                angle_text = "{:.1f}°".format(angle_deg)
                
                # Create text item
                font = QFont()
                font.setPointSize(8)
                font.setBold(True)
                
                text_item = self.activeviewer.scene.addText(angle_text)
                text_item.setFont(font)
                text_item.setDefaultTextColor(QColor(0, 0, 0))  # Black text
                
                text_rect = text_item.boundingRect()
                text_width = text_rect.width()
                text_height = text_rect.height()
                
                # Create compact background rectangle
                padding = 2
                bg_height = text_height * 0.6 + padding * 2
                bg_width = text_width + padding * 2
                bg_x = x_mid - bg_width / 2
                bg_y = y_mid - bg_height / 2
                
                # Get color based on segment inclination
                bg_color = self.getInclinationColor(angle_deg, max_abs_segment_angle)
                
                # Draw colored background with black outline
                outline_rect_pen = QPen(QColor(0, 0, 0))
                outline_rect_pen.setWidth(1)
                outline_rect_pen.setCosmetic(True)
                bg_brush = QBrush(bg_color)
                
                bg_rect = self.activeviewer.scene.addRect(bg_x, bg_y, bg_width, bg_height, outline_rect_pen, bg_brush)
                bg_rect.setZValue(22)
                self.segmentInclinationEntities.append(bg_rect)
                
                # Position text centered in background
                text_x = bg_x + padding
                text_y = bg_y + (bg_height - text_height) / 2
                text_item.setPos(text_x, text_y)
                text_item.setZValue(23)
                self.segmentInclinationEntities.append(text_item)
        
        return

    ########################################################################################
    # MERGE FUNCTIONALITY
    
    def clearMergeSelection(self):
        """
        Clear the merge selection state and remove highlight.
        """
        if self.firstMergeBlobHighlight:
            self.activeviewer.scene.removeItem(self.firstMergeBlobHighlight)
            self.firstMergeBlobHighlight = None
        self.firstMergeBlob = None
    
    def handleMergeClick(self, click_x, click_y):
        """
        Handle a mouse click in merge mode. Find which blob was clicked.
        """
        if self.rowsData is None or len(self.rowsData) == 0:
            self.writeLog("No rows to merge!")
            return
        
        # Find which blob was clicked
        clicked_blob = None
        for row in self.rowsData:
            for blob in row['blobs']:
                # Check if click is within blob's bounding box
                bbox = blob.bbox  # [top, left, width, height]
                if (bbox[1] <= click_x <= bbox[1] + bbox[2] and 
                    bbox[0] <= click_y <= bbox[0] + bbox[3]):
                    clicked_blob = blob
                    break
            if clicked_blob:
                break
        
        if not clicked_blob:
            return  # Click was not on a blob
        
        # Check if blob is in our row data
        if clicked_blob not in self.blobToRowMap:
            return
        
        row_index, pos_in_row = self.blobToRowMap[clicked_blob]
        row = self.rowsData[row_index]
        
        # Check if it's first or last in the row
        is_first = (pos_in_row == 0)
        is_last = (pos_in_row == len(row['blobs']) - 1)
        
        if not (is_first or is_last):
            self.writeLog("Click ignored: Region must be first or last in its row.")
            # If we had a first selection, clear it and restart
            if self.firstMergeBlob:
                self.clearMergeSelection()
                self.writeLog("Selection cleared. Click on a first/last region to start.")
            return
        
        # If this is the first selection
        if self.firstMergeBlob is None:
            self.firstMergeBlob = clicked_blob
            self.highlightBlob(clicked_blob)
            position = "first" if is_first else "last"
            self.writeLog("Selected {} region of row {}. Now click on a first/last region of another row.".format(
                position, row_index + 1))
        else:
            # This is the second selection
            first_row_index, first_pos = self.blobToRowMap[self.firstMergeBlob]
            
            # Check if same row
            if first_row_index == row_index:
                self.writeLog("Cannot merge a row with itself!")
                self.clearMergeSelection()
                self.writeLog("Selection cleared. Click on a first/last region to start.")
                return
            
            # Perform the merge
            self.mergeRows(first_row_index, first_pos, row_index, pos_in_row)
            self.clearMergeSelection()
    
    def highlightBlob(self, blob):
        """
        Draw a highlight around the selected blob.
        """
        # Remove old highlight if exists
        if self.firstMergeBlobHighlight:
            self.activeviewer.scene.removeItem(self.firstMergeBlobHighlight)
        
        # Draw a thick yellow outline around the blob
        min_row, min_col, _, _ = blob.bbox
        contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnt = contours[0]
        polygon = QPolygonF([QPointF(float(point[0][0])+min_col+0.5, float(point[0][1])+min_row+0.5) for point in cnt])
        
        pen = QPen(QColor(255, 255, 0))  # Yellow
        pen.setWidth(5)
        pen.setCosmetic(True)
        brush = QBrush(Qt.NoBrush)
        
        self.firstMergeBlobHighlight = self.activeviewer.scene.addPolygon(polygon, pen, brush)
        self.firstMergeBlobHighlight.setZValue(20)  # Draw above everything
    
    def mergeRows(self, row1_idx, pos1, row2_idx, pos2):
        """
        Merge two rows by connecting them at the specified positions.
        """
        row1 = self.rowsData[row1_idx]
        row2 = self.rowsData[row2_idx]
        
        is_first1 = (pos1 == 0)
        is_last1 = (pos1 == len(row1['blobs']) - 1)
        is_first2 = (pos2 == 0)
        is_last2 = (pos2 == len(row2['blobs']) - 1)
        
        # Determine how to connect the rows
        # Two valid cases: row1_end-row2_start OR row2_end-row1_start
        merged_blobs = None
        
        if is_last1 and is_first2:
            # row1 ... | ... row2
            merged_blobs = row1['blobs'] + row2['blobs']
        elif is_last2 and is_first1:
            # row2 ... | ... row1
            merged_blobs = row2['blobs'] + row1['blobs']
        else:
            self.writeLog("Invalid merge: Cannot connect these positions.")
            return
        
        # Remove both old rows and add the merged row
        indices_to_remove = sorted([row1_idx, row2_idx], reverse=True)
        new_rows = self.rowsData[:]
        
        for idx in indices_to_remove:
            del new_rows[idx]
        
        new_rows.append(self.createRowData(merged_blobs))
        self.rowsData = new_rows
        
        # Sort rows to preserve ordering
        self.sortRows()
        
        # Recompute inclination for merged rows
        self.computeInclination()
        
        # Refresh visualization and table
        self.displayRows()
        self.populateRowsTable()
        self.removeInclinationLines()  # Clear old inclination lines after merge
        self.removeSegmentInclinationEntities()  # Clear old segment angles after merge
        
        # Redisplay inclination if button is checked
        if self.btnAnalyzeInclination.isChecked():
            self.displayInclinationLines()
        
        # Redisplay segment angles if button is checked
        if self.btnSegmentInclination.isChecked():
            self.displaySegmentInclination()
        
        self.writeLog("Merge complete. Now {} rows total.".format(len(self.rowsData)))

    ########################################################################################

    def createRowData(self, blobs):
        """
        Create row metadata dictionary from a list of blobs.
        """
        return {
            'blobs': blobs,
            'num_blobs': len(blobs),
            'centroid_y': sum([b.centroid[1] for b in blobs]) / len(blobs),
            'avg_height': sum([b.bbox[3] for b in blobs]) / len(blobs),
            'min_y': min([b.bbox[0] for b in blobs]),
            'max_y': max([b.bbox[0] + b.bbox[3] for b in blobs]),
            'min_x': min([b.bbox[1] for b in blobs]),
            'max_x': max([b.bbox[1] + b.bbox[2] for b in blobs]),
            'height': max([b.bbox[0] + b.bbox[3] for b in blobs]) - min([b.bbox[0] for b in blobs]),
            'width': max([b.bbox[1] + b.bbox[2] for b in blobs]) - min([b.bbox[1] for b in blobs])
        }

    def sortRows(self):
        """
        Sort rows by Y position (top to bottom), then by X position (left to right) for rows at similar Y.
        """
        if not self.rowsData or len(self.rowsData) == 0:
            return
        
        # Use average height as tolerance for "similar Y"
        avg_row_height = sum([r['avg_height'] for r in self.rowsData]) / len(self.rowsData)
        y_tolerance = avg_row_height * 0.5  # Rows within 50% of avg height are considered "same level"
        
        def row_sort_key(row):
            # Quantize Y position to group similar rows, then sort by X within groups
            y_bucket = int(row['centroid_y'] / y_tolerance) if y_tolerance > 0 else row['centroid_y']
            return (y_bucket, row['min_x'])
        
        self.rowsData.sort(key=row_sort_key)

    def getPastelColor(self, index, total):
        """
        Returns a diverse pastel QColor based on index and total count.
        index: The index of the color to generate (0-based).  total: The total number of colors needed
        """
        if total <= 0:
            total = 1
        # Use golden ratio for maximum color diversity
        golden_ratio = 0.618033988749895
        hue = (index * golden_ratio) % 1.0
        # Pastel colors: high saturation (40-60%), high value (85-95%)
        saturation = 0.5
        value = 0.9
        # Convert to 0-359 range for QColor (HSV)
        h = int(hue * 360)
        s = int(saturation * 255)
        v = int(value * 255)
        color = QColor()
        color.setHsv(h, s, v, 255)  # 255 = fully opaque
        return color
    
    def getInclinationColor(self, inclination_deg, max_abs_inclination):
        """
        Returns a color based on inclination angle.
        Grey = 0 degrees
        Blue-ish = positive angles (counterclockwise)
        Red-ish = negative angles (clockwise)
        The intensity increases with the absolute value of the angle.
        
        Args:
            inclination_deg: The inclination angle in degrees
            max_abs_inclination: The maximum absolute inclination across all rows
        
        Returns:
            QColor representing the inclination
        """
        if max_abs_inclination == 0:
            return QColor(128, 128, 128)  # Grey
        
        # Normalize to [-1, 1]
        normalized = inclination_deg / max_abs_inclination
        
        # Base grey color
        grey = 180
        
        if normalized > 0:
            # Positive angle -> Blue-ish
            # Interpolate from grey to blue
            r = int(grey * (1 - normalized))
            g = int(grey * (1 - normalized * 0.5))
            b = int(grey + (255 - grey) * normalized)
        else:
            # Negative angle -> Red-ish
            # Interpolate from grey to red
            abs_normalized = abs(normalized)
            r = int(grey + (255 - grey) * abs_normalized)
            g = int(grey * (1 - abs_normalized * 0.5))
            b = int(grey * (1 - abs_normalized))
        
        return QColor(r, g, b, 200)  # Slight transparency
    
    def distancePointToLineSegment(self, px, py, x1, y1, x2, y2):
        """
        Calculate the distance from point (px, py) to line segment from (x1, y1) to (x2, y2).
        Returns the minimum distance.
        """
        # Vector from point1 to point2
        dx = x2 - x1
        dy = y2 - y1
        
        # If the segment is actually a point
        if dx == 0 and dy == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        # Parameter t of the closest point on the line
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        
        # Clamp t to [0, 1] to stay on the segment
        t = max(0, min(1, t))
        
        # Closest point on the segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Distance from point to closest point
        return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    def handleCutClick(self, click_x, click_y):
        """
        Handle a mouse click in cut mode. Find the closest line segment and split the row.
        """
        if self.rowsData is None or len(self.rowsData) == 0:
            self.writeLog("No rows to cut!")
            return
        
        if len(self.lineSegmentData) == 0:
            self.writeLog("No line segments found. Please run row detection first.")
            return
        
        # Find the closest line segment
        min_distance = float('inf')
        closest_segment = None
        
        for segment_info in self.lineSegmentData:
            row_idx, seg_idx, p1, p2 = segment_info
            distance = self.distancePointToLineSegment(click_x, click_y, p1.x(), p1.y(), p2.x(), p2.y())
            
            if distance < min_distance:
                min_distance = distance
                closest_segment = segment_info
        
        # If click is reasonably close to a line segment (within 50 pixels)
        if closest_segment and min_distance < 50:
            row_idx, seg_idx, p1, p2 = closest_segment
            self.splitRow(row_idx, seg_idx)
        else:
            self.writeLog("Click too far from any polyline. Try clicking closer to a line.")
    
    def splitRow(self, row_index, segment_index):
        """
        Split a row at the specified segment index.
        The row is split so that blobs [0...segment_index] go to the first row,
        and blobs [segment_index+1...] go to the second row.
        """
        if row_index >= len(self.rowsData):
            self.writeLog("Invalid row index!")
            return
        
        row = self.rowsData[row_index]
        
        if segment_index >= len(row['blobs']) - 1:
            self.writeLog("Cannot split at this position!")
            return
        
        # Split the blob list
        first_half = row['blobs'][:segment_index + 1]
        second_half = row['blobs'][segment_index + 1:]
        
        if len(first_half) == 0 or len(second_half) == 0:
            self.writeLog("Cannot create empty rows!")
            return
        
        # Replace the original row with the two new rows
        new_rows = (
            self.rowsData[:row_index] +
            [self.createRowData(first_half), self.createRowData(second_half)] +
            self.rowsData[row_index + 1:]
        )
        
        self.rowsData = new_rows
        
        # Sort rows to preserve ordering
        self.sortRows()
        
        # Recompute inclination for split rows
        self.computeInclination()
        
        # Refresh the visualization and table
        self.displayRows()
        self.populateRowsTable()
        self.removeInclinationLines()  # Clear old inclination lines after split
        self.removeSegmentInclinationEntities()  # Clear old segment angles after split
        
        # Redisplay inclination if button is checked
        if self.btnAnalyzeInclination.isChecked():
            self.displayInclinationLines()
        
        # Redisplay segment angles if button is checked
        if self.btnSegmentInclination.isChecked():
            self.displaySegmentInclination()
        
        # Log the result
        self.writeLog("Row split complete. Now {} rows total.".format(len(self.rowsData)))
