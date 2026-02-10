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

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QPointF, QEvent
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF, QFont
from PyQt5.QtWidgets import QWidget, QTableWidget, QTextEdit, QTableWidgetItem, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QGroupBox, QComboBox, QFileDialog, QMessageBox
import math
import cv2
import numpy as np
import json
import os


class QtCourseAnalysis(QWidget):
    """
    Widget for course analysis functionality.
    Provides three command buttons and a log area to display information.
    """

    def __init__(self, viewer, parent=None):
        super(QtCourseAnalysis, self).__init__(parent)

        # DATA ##########################################################
        # active viewer
        self.activeviewer = viewer
        # the set of working blobs, that contain the blobs being analyzed
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        # data structure to hold recognized courses
        self.coursesData = None
        # color mode for displaying regions
        self.colorMode = "ID"  # Options: "NONE", "ID", "INCLINATION"

        # store geometric entities for overlay
        self.colorizedEntities = []
        self.polylineEntities = []
        self.lineSegmentData = []  # Store metadata for each line segment: (course_index, segment_index, point1, point2)
        self.inclinationLines = []  # Store inclination visualization lines
        self.segmentInclinationEntities = []  # Store segment-by-segment inclination visualizations
        
        # Cut mode state
        self.cutModeActive = False
        
        # Merge mode state
        self.mergeModeActive = False
        self.firstMergeBlob = None  # First blob selected for merge
        self.firstMergeBlobHighlight = None  # Highlight graphics for first blob
        self.blobToCourseMap = {}  # Map blob to (course_index, position_in_course)


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
        controlsGroup = QGroupBox("Courses Detection and Editing")
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
        self.editXGapTolerance.setToolTip("Maximum X gap (relative to average blob width in course)")
        
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
        
        self.btnRecognize = QPushButton("Recognize Courses")
        self.btnRecognize.clicked.connect(self.recognizeCourses)
        
        self.btnCutCourse = QPushButton("✂ Cut Course")
        self.btnCutCourse.setToolTip("Click to activate cut mode, then click near a polyline to split the course")
        self.btnCutCourse.setCheckable(True)
        self.btnCutCourse.clicked.connect(self.toggleCutMode)
        
        self.btnMergeCourses = QPushButton("🔗 Merge Courses")
        self.btnMergeCourses.setToolTip("Click to activate merge mode, then click on first/last regions of two different courses to connect them")
        self.btnMergeCourses.setCheckable(True)
        self.btnMergeCourses.clicked.connect(self.toggleMergeMode)
        
        button_layout.addWidget(self.btnRecognize)
        button_layout.addWidget(self.btnCutCourse)
        button_layout.addWidget(self.btnMergeCourses)
        button_layout.addStretch()
        
        controlsLayout.addLayout(button_layout)
        
        # Save/Restore buttons layout
        saveload_layout = QHBoxLayout()
        
        self.btnSave = QPushButton("💾 Save State")
        self.btnSave.setToolTip("Save the current courses state to a JSON file")
        self.btnSave.clicked.connect(self.saveState)
        
        self.btnRestore = QPushButton("📂 Restore State")
        self.btnRestore.setToolTip("Restore courses state from a JSON file")
        self.btnRestore.clicked.connect(self.restoreState)
        
        saveload_layout.addWidget(self.btnSave)
        saveload_layout.addWidget(self.btnRestore)
        saveload_layout.addStretch()
        
        controlsLayout.addLayout(saveload_layout)
        controlsGroup.setLayout(controlsLayout)
        mainLayout.addWidget(controlsGroup)

        # Table widget for course data
        self.coursesTable = QTableWidget()
        self.coursesTable.setColumnCount(6)
        self.coursesTable.setHorizontalHeaderLabels(["Color", "Regions", "Y pos", "Avg Height", "Width", "Inclination"])
        self.coursesTable.setStyleSheet("QTableWidget { background-color: rgb(50,50,50); color: white; gridline-color: rgb(80,80,80); } QHeaderView::section { background-color: rgb(60,60,60); color: white; }")
        self.coursesTable.setMinimumHeight(150)
        self.coursesTable.setEditTriggers(QTableWidget.NoEditTriggers)
        mainLayout.addWidget(self.coursesTable)
        
        # GROUP BOX for course analysis
        analysisGroup = QGroupBox("Course Analysis")
        analysisGroup.setStyleSheet("QGroupBox { background-color: rgb(45,45,45); color: white; border: 2px solid rgb(80,80,80); border-radius: 5px; margin-top: 10px; padding-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        analysisLayout = QVBoxLayout()
        
        # Color mode dropdown
        color_mode_layout = QHBoxLayout()
        lblColorMode = QLabel("Color Mode:")
        self.comboColorMode = QComboBox()
        self.comboColorMode.addItems(["NONE", "ID", "INCLINATION"])
        self.comboColorMode.setCurrentText("ID")
        self.comboColorMode.setToolTip("Select how to colorize regions: NONE (no color), ID (random pastel colors), INCLINATION (color ramp based on course angle)")
        self.comboColorMode.currentTextChanged.connect(self.onColorModeChanged)
        self.comboColorMode.setMaximumWidth(150)
        color_mode_layout.addWidget(lblColorMode)
        color_mode_layout.addWidget(self.comboColorMode)
        color_mode_layout.addStretch()
        analysisLayout.addLayout(color_mode_layout)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        self.btnAnalyzeInclination = QPushButton("Show Inclination")
        self.btnAnalyzeInclination.setToolTip("Compute and show/hide the inclination angle for each course by fitting a line through all centroids")
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
        self.setWindowTitle("Course Analysis")
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
        super(QtCourseAnalysis, self).closeEvent(event)

    @pyqtSlot()
    def onSelectionChanged(self):
        """Called when the selection changes in the viewer"""
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        self.writeLog("Selection changed. Now {} region(s) selected.".format(len(self.workingBlobs)))

    @pyqtSlot(str)
    def onColorModeChanged(self, mode):
        """Called when the color mode dropdown changes"""
        self.colorMode = mode
        if self.coursesData is not None and len(self.coursesData) > 0:
            self.displayCourses()
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
        
        return super(QtCourseAnalysis, self).eventFilter(obj, event)

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
    def recognizeCourses(self):
        """
        Recognize courses using incremental algorithm.
        """
        if len(self.workingBlobs) == 0:
            self.writeLog("No regions selected!")
            return

        self.logArea.clear()
        self.writeLog("Recognizing courses...")
        
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
        
        # Detect courses using incremental method
        self.coursesData = self.detectCoursesIncremental(y_tolerance_factor, ytb_tolerance_factor, height_tolerance_factor, x_gap_factor)
        
        # Log results
        self.writeLog("Found {} course(s)".format(len(self.coursesData)))
        
        # Compute inclination for all courses automatically
        self.computeInclination()
        
        # Populate table with course data
        self.populateCoursesTable()
        
        # Display courses
        self.displayCourses()
        
        # Redisplay visualizations if they were active
        if self.btnAnalyzeInclination.isChecked():
            self.displayInclinationLines()
        if self.btnSegmentInclination.isChecked():
            self.displaySegmentInclination()

    def computeInclination(self):
        """
        Compute the inclination for all courses.
        """
        if self.coursesData is None or len(self.coursesData) == 0:
            return
        
        for course in self.coursesData:
            if course['num_blobs'] < 2:
                course['inclination_deg'] = 0.0
                course['inclination_rad'] = 0.0
                continue
            
            # Get all centroids
            centroids_x = [blob.centroid[0] for blob in course['blobs']]
            centroids_y = [blob.centroid[1] for blob in course['blobs']]
            
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
            
            course['inclination_deg'] = angle_deg
            course['inclination_rad'] = angle_rad
            course['fit_slope'] = slope
            course['fit_intercept'] = intercept
    
    @pyqtSlot()
    def toggleInclination(self):
        """
        Toggle the display of inclination lines.
        """
        if self.coursesData is None or len(self.coursesData) == 0:
            self.writeLog("No courses detected. Please run course detection first.")
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
        if self.coursesData is None or len(self.coursesData) == 0:
            self.writeLog("No courses detected. Please run course detection first.")
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
        self.cutModeActive = self.btnCutCourse.isChecked()
        
        if self.cutModeActive:
            # Check if there are courses to cut
            if self.coursesData is None or len(self.coursesData) == 0:
                self.writeLog("No courses detected. Please run course detection first.")
                self.btnCutCourse.setChecked(False)
                self.cutModeActive = False
                return
            
            # Deactivate merge mode if active
            if self.mergeModeActive:
                self.btnMergeCourses.setChecked(False)
                self.btnMergeCourses.setStyleSheet("")
                self.mergeModeActive = False
                self.clearMergeSelection()
            
            self.btnCutCourse.setStyleSheet("background-color: rgb(200, 100, 100); color: white; font-weight: bold;")
            self.writeLog("Cut mode activated. Click near a polyline to split the course.")
            self.activeviewer.setCursor(Qt.SizeHorCursor)
        else:
            self.btnCutCourse.setStyleSheet("")
            self.writeLog("Cut mode deactivated.")
            self.activeviewer.setCursor(Qt.ArrowCursor)
    
    @pyqtSlot()
    def toggleMergeMode(self):
        """
        Toggle merge mode on/off.
        """
        self.mergeModeActive = self.btnMergeCourses.isChecked()
        
        if self.mergeModeActive:
            # Check if there are courses to merge
            if self.coursesData is None or len(self.coursesData) == 0:
                self.writeLog("No courses detected. Please run course detection first.")
                self.btnMergeCourses.setChecked(False)
                self.mergeModeActive = False
                return
            
            # Deactivate cut mode if active
            if self.cutModeActive:
                self.btnCutCourse.setChecked(False)
                self.btnCutCourse.setStyleSheet("")
                self.cutModeActive = False
            
            self.btnMergeCourses.setStyleSheet("background-color: rgb(100, 150, 200); color: white; font-weight: bold;")
            self.clearMergeSelection()
            self.writeLog("Merge mode activated. Click on the first/last region of a course.")
            self.activeviewer.setCursor(Qt.PointingHandCursor)
        else:
            self.btnMergeCourses.setStyleSheet("")
            self.clearMergeSelection()
            self.writeLog("Merge mode deactivated.")
            self.activeviewer.setCursor(Qt.ArrowCursor)
    
    def populateCoursesTable(self):
        """
        Populate the table with detected courses data.
        """
        if self.coursesData is None or len(self.coursesData) == 0:
            self.coursesTable.setRowCount(0)
            return
        self.coursesTable.setRowCount(len(self.coursesData))
        for i, course in enumerate(self.coursesData):
            # Color indicator
            color = self.getPastelColor(i, len(self.coursesData))
            color_item = QTableWidgetItem("")
            color_item.setBackground(QBrush(color))
            self.coursesTable.setItem(i, 0, color_item)
            # Number of regions
            self.coursesTable.setItem(i, 1, QTableWidgetItem(str(course['num_blobs'])))
            # Y position
            self.coursesTable.setItem(i, 2, QTableWidgetItem("{:.1f}".format(course['centroid_y'])))
            # Average height
            self.coursesTable.setItem(i, 3, QTableWidgetItem("{:.1f}".format(course['avg_height'])))
            # Width
            self.coursesTable.setItem(i, 4, QTableWidgetItem("{:.1f}".format(course['width'])))
            # Inclination
            if 'inclination_deg' in course:
                self.coursesTable.setItem(i, 5, QTableWidgetItem("{:.2f}°".format(course['inclination_deg'])))
            else:
                self.coursesTable.setItem(i, 5, QTableWidgetItem("-"))
        self.coursesTable.resizeColumnsToContents()

    ########################################################################################
    # COURSE DETECTION ALGORITHM

    def detectCoursesIncremental(self, y_tolerance_factor=0.3, ytb_tolerance_factor=0.3, height_tolerance_factor=0.3, x_gap_factor=3.0):
        """
        Detect courses incrementally by building courses one at a time.
        A blob is added to a course if it's compatible with the last (rightmost) blob in the course:
        - Its centroid Y is within tolerance of the last blob's Y (tolerance based on last blob's height)
        - Its top and bottom Y positions are within tolerance (tolerance based on last blob's height)
        - Its height is within tolerance of the last blob's height
        - The X gap is not too large (tolerance based on average blob width in course)
        
        Args:
            y_tolerance_factor: Tolerance for Y centroid position (relative to last blob height)
            ytb_tolerance_factor: Tolerance for Y top/bottom position (relative to last blob height)
            height_tolerance_factor: Tolerance for height variation (relative to last blob height)
            x_gap_factor: Maximum X gap (relative to average blob width in course)
            
        Returns:
            List of course objects, each containing blobs and metadata
        """
        if len(self.workingBlobs) == 0:
            return []
        
        # Keep track of unassigned blobs
        unassigned = self.workingBlobs[:]
        courses = []
        
        while unassigned:
            # Start a new course with the first unassigned blob (leftmost by X)
            unassigned.sort(key=lambda b: b.centroid[0])
            first_blob = unassigned.pop(0)
            
            current_course = {
                'blobs': [first_blob],
                'centroid_y': first_blob.centroid[1],
                'avg_height': first_blob.bbox[3],
                'min_y': first_blob.bbox[0],
                'max_y': first_blob.bbox[0] + first_blob.bbox[3]
            }
            
            # Try to add more blobs to this course
            while unassigned:
                # Get the rightmost (last) blob in the current course
                last_blob = current_course['blobs'][-1]
                last_y = last_blob.centroid[1]
                last_height = last_blob.bbox[3]
                last_x = last_blob.centroid[0]
                last_top = last_blob.bbox[0]
                last_bottom = last_blob.bbox[0] + last_blob.bbox[3]
                
                # Calculate tolerances based on the last blob
                y_tolerance = last_height * y_tolerance_factor
                ytb_tolerance = last_height * ytb_tolerance_factor
                
                # Calculate average width of blobs in current course for X gap tolerance
                avg_width = sum([b.bbox[2] for b in current_course['blobs']]) / len(current_course['blobs'])
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
                    # No more compatible blobs for this course
                    break
                
                # Add the best blob to the current course
                current_course['blobs'].append(best_blob)
                unassigned.remove(best_blob)
                
                # Update course statistics
                current_course['centroid_y'] = sum([b.centroid[1] for b in current_course['blobs']]) / len(current_course['blobs'])
                current_course['avg_height'] = sum([b.bbox[3] for b in current_course['blobs']]) / len(current_course['blobs'])
                current_course['min_y'] = min(current_course['min_y'], best_blob.bbox[0])
                current_course['max_y'] = max(current_course['max_y'], best_blob.bbox[0] + best_blob.bbox[3])
            
            courses.append(current_course)
        
        # Sort blobs within each course by X coordinate and compute final metadata
        for course in courses:
            course['blobs'].sort(key=lambda b: b.centroid[0])
            course['num_blobs'] = len(course['blobs'])
            course['min_x'] = min([b.bbox[1] for b in course['blobs']])
            course['max_x'] = max([b.bbox[1] + b.bbox[2] for b in course['blobs']])
            course['height'] = course['max_y'] - course['min_y']
            course['width'] = course['max_x'] - course['min_x']
        
        # Sort courses: primarily by Y position, secondarily by X position for courses at similar Y
        # Use average height as tolerance for "similar Y"
        avg_course_height = sum([r['avg_height'] for r in courses]) / len(courses) if courses else 0
        y_tolerance = avg_course_height * 0.5  # Courses within 50% of avg height are considered "same level"
        
        def course_sort_key(course):
            # Quantize Y position to group similar courses, then sort by X within groups
            y_bucket = int(course['centroid_y'] / y_tolerance) if y_tolerance > 0 else course['centroid_y']
            return (y_bucket, course['min_x'])
        
        courses.sort(key=course_sort_key)
        
        return courses


    ########################################################################################

    def displayCourses(self):
        """
        Display blobs colorized by their course assignment.
        """
        if self.coursesData is None or len(self.coursesData) == 0:
            return
        
        self.removeColorizedEntities()
        self.removePolylineEntities()
        self.lineSegmentData = []  # Clear line segment metadata
        self.blobToCourseMap = {}  # Clear blob-to-course mapping
        
        # Calculate max absolute inclination for color ramp
        max_abs_inclination = 0.0
        if self.colorMode == "INCLINATION":
            for course in self.coursesData:
                if 'inclination_deg' in course:
                    max_abs_inclination = max(max_abs_inclination, abs(course['inclination_deg']))
        
        for course_index, course in enumerate(self.coursesData):
            # Determine color based on mode
            if self.colorMode == "NONE":
                # Don't draw filled blobs
                pass
            elif self.colorMode == "ID":
                color = self.getPastelColor(course_index, len(self.coursesData))
                pen = QPen(Qt.NoPen)
                brush = QBrush(color)
                
                # Draw filled blobs
                for blob in course['blobs']:
                    min_row, min_col, _, _ = blob.bbox
                    contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cnt = contours[0]
                    polygon = QPolygonF([QPointF(float(point[0][0])+min_col+0.5, float(point[0][1])+min_row+0.5) for point in cnt])
                    newItemC = self.activeviewer.scene.addPolygon(polygon, pen, brush)
                    newItemC.setZValue(10)
                    self.colorizedEntities.append(newItemC)
            
            elif self.colorMode == "INCLINATION":
                # Get inclination-based color
                if 'inclination_deg' in course and max_abs_inclination > 0:
                    color = self.getInclinationColor(course['inclination_deg'], max_abs_inclination)
                else:
                    color = QColor(128, 128, 128)  # Grey for no inclination data
                
                pen = QPen(Qt.NoPen)
                brush = QBrush(color)
                
                # Draw filled blobs
                for blob in course['blobs']:
                    min_row, min_col, _, _ = blob.bbox
                    contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cnt = contours[0]
                    polygon = QPolygonF([QPointF(float(point[0][0])+min_col+0.5, float(point[0][1])+min_row+0.5) for point in cnt])
                    newItemC = self.activeviewer.scene.addPolygon(polygon, pen, brush)
                    newItemC.setZValue(10)
                    self.colorizedEntities.append(newItemC)
            
            # Build blob-to-course mapping for merge functionality
            for pos, blob in enumerate(course['blobs']):
                self.blobToCourseMap[blob] = (course_index, pos)
            
            # Draw line segments connecting consecutive regions
            if len(course['blobs']) > 1:
                # Create pen for the lines (contrasting color for visibility)
                line_pen = QPen(QColor(0, 0, 0))  # Black for high contrast
                line_pen.setWidth(3)
                line_pen.setCosmetic(True)
                
                # Draw a line from each region to the next one
                for i in range(len(course['blobs']) - 1):
                    blob1 = course['blobs'][i]
                    blob2 = course['blobs'][i + 1]
                    
                    point1 = QPointF(blob1.centroid[0], blob1.centroid[1])
                    point2 = QPointF(blob2.centroid[0], blob2.centroid[1])
                    
                    line_item = self.activeviewer.scene.addLine(point1.x(), point1.y(), 
                                                                  point2.x(), point2.y(), 
                                                                  line_pen)
                    line_item.setZValue(15)  # Draw above blobs
                    self.polylineEntities.append(line_item)
                    
                    # Store line segment metadata for cut functionality
                    self.lineSegmentData.append((course_index, i, point1, point2))
            
            # Draw white dots at centroids
            dot_pen = QPen(Qt.NoPen)
            dot_brush = QBrush(QColor(255, 255, 255))  # White
            dot_radius = 5
            
            for blob in course['blobs']:
                center = QPointF(blob.centroid[0], blob.centroid[1])
                dot_item = self.activeviewer.scene.addEllipse(
                    center.x() - dot_radius, center.y() - dot_radius,
                    dot_radius * 2, dot_radius * 2,
                    dot_pen, dot_brush
                )
                dot_item.setZValue(16)  # Draw above lines
                self.polylineEntities.append(dot_item)
            
            # Draw course number on first blob (above centroid)
            first_blob = course['blobs'][0]
            text_x = first_blob.centroid[0]
            
            text_item = self.activeviewer.scene.addText(str(course_index + 1))
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
        Display inclination lines for each course with angle labels.
        """
        self.removeInclinationLines()
        
        if self.coursesData is None or len(self.coursesData) == 0:
            return
        
        for course_index, course in enumerate(self.coursesData):
            if 'fit_slope' not in course or course['num_blobs'] < 2:
                continue
            
            slope = course['fit_slope']
            intercept = course['fit_intercept']
            
            # Calculate line endpoints across the course's extent
            x_start = course['min_x']
            x_end = course['max_x']
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
            
            angle_text = "{:.2f}°".format(course['inclination_deg'])
            
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
        Display inclination angles for each segment between consecutive regions in each course.
        """
        self.removeSegmentInclinationEntities()
        
        if self.coursesData is None or len(self.coursesData) == 0:
            return
        
        # Calculate max absolute inclination across all segments for color normalization
        max_abs_segment_angle = 0.0
        for course in self.coursesData:
            if course['num_blobs'] < 2:
                continue
            for i in range(len(course['blobs']) - 1):
                blob1 = course['blobs'][i]
                blob2 = course['blobs'][i + 1]
                dx = blob2.centroid[0] - blob1.centroid[0]
                dy = blob2.centroid[1] - blob1.centroid[1]
                angle_rad = math.atan2(-dy, dx)
                angle_deg = math.degrees(angle_rad)
                max_abs_segment_angle = max(max_abs_segment_angle, abs(angle_deg))
        
        for course_index, course in enumerate(self.coursesData):
            if course['num_blobs'] < 2:
                continue
            
            # Analyze each segment between consecutive blobs
            for i in range(len(course['blobs']) - 1):
                blob1 = course['blobs'][i]
                blob2 = course['blobs'][i + 1]
                
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
        if self.coursesData is None or len(self.coursesData) == 0:
            self.writeLog("No courses to merge!")
            return
        
        # Find which blob was clicked
        clicked_blob = None
        for course in self.coursesData:
            for blob in course['blobs']:
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
        
        # Check if blob is in our course data
        if clicked_blob not in self.blobToCourseMap:
            return
        
        course_index, pos_in_course = self.blobToCourseMap[clicked_blob]
        course = self.coursesData[course_index]
        
        # Check if it's first or last in the course
        is_first = (pos_in_course == 0)
        is_last = (pos_in_course == len(course['blobs']) - 1)
        
        if not (is_first or is_last):
            self.writeLog("Click ignored: Region must be first or last in its course.")
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
            self.writeLog("Selected {} region of course {}. Now click on a first/last region of another course.".format(
                position, course_index + 1))
        else:
            # This is the second selection
            first_course_index, first_pos = self.blobToCourseMap[self.firstMergeBlob]
            
            # Check if same course
            if first_course_index == course_index:
                self.writeLog("Cannot merge a course with itself!")
                self.clearMergeSelection()
                self.writeLog("Selection cleared. Click on a first/last region to start.")
                return
            
            # Perform the merge
            self.mergeCourses(first_course_index, first_pos, course_index, pos_in_course)
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
    
    def mergeCourses(self, course1_idx, pos1, course2_idx, pos2):
        """
        Merge two courses by connecting them at the specified positions.
        """
        course1 = self.coursesData[course1_idx]
        course2 = self.coursesData[course2_idx]
        
        is_first1 = (pos1 == 0)
        is_last1 = (pos1 == len(course1['blobs']) - 1)
        is_first2 = (pos2 == 0)
        is_last2 = (pos2 == len(course2['blobs']) - 1)
        
        # Determine how to connect the courses
        # Two valid cases: course1_end-course2_start OR course2_end-course1_start
        merged_blobs = None
        
        if is_last1 and is_first2:
            # course1 ... | ... course2
            merged_blobs = course1['blobs'] + course2['blobs']
        elif is_last2 and is_first1:
            # course2 ... | ... course1
            merged_blobs = course2['blobs'] + course1['blobs']
        else:
            self.writeLog("Invalid merge: Cannot connect these positions.")
            return
        
        # Remove both old courses and add the merged course
        indices_to_remove = sorted([course1_idx, course2_idx], reverse=True)
        new_courses = self.coursesData[:]
        
        for idx in indices_to_remove:
            del new_courses[idx]
        
        new_courses.append(self.createCourseData(merged_blobs))
        self.coursesData = new_courses
        
        # Sort courses to preserve ordering
        self.sortCourses()
        
        # Recompute inclination for merged courses
        self.computeInclination()
        
        # Refresh visualization and table
        self.displayCourses()
        self.populateCoursesTable()
        self.removeInclinationLines()  # Clear old inclination lines after merge
        self.removeSegmentInclinationEntities()  # Clear old segment angles after merge
        
        # Redisplay inclination if button is checked
        if self.btnAnalyzeInclination.isChecked():
            self.displayInclinationLines()
        
        # Redisplay segment angles if button is checked
        if self.btnSegmentInclination.isChecked():
            self.displaySegmentInclination()
        
        self.writeLog("Merge complete. Now {} courses total.".format(len(self.coursesData)))

    ########################################################################################

    def createCourseData(self, blobs):
        """
        Create course metadata dictionary from a list of blobs.
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

    def sortCourses(self):
        """
        Sort courses by Y position (top to bottom), then by X position (left to right) for courses at similar Y.
        """
        if not self.coursesData or len(self.coursesData) == 0:
            return
        
        # Use average height as tolerance for "similar Y"
        avg_course_height = sum([r['avg_height'] for r in self.coursesData]) / len(self.coursesData)
        y_tolerance = avg_course_height * 0.5  # Courses within 50% of avg height are considered "same level"
        
        def course_sort_key(course):
            # Quantize Y position to group similar courses, then sort by X within groups
            y_bucket = int(course['centroid_y'] / y_tolerance) if y_tolerance > 0 else course['centroid_y']
            return (y_bucket, course['min_x'])
        
        self.coursesData.sort(key=course_sort_key)

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
        Handle a mouse click in cut mode. Find the closest line segment and split the course.
        """
        if self.coursesData is None or len(self.coursesData) == 0:
            self.writeLog("No courses to cut!")
            return
        
        if len(self.lineSegmentData) == 0:
            self.writeLog("No line segments found. Please run course detection first.")
            return
        
        # Find the closest line segment
        min_distance = float('inf')
        closest_segment = None
        
        for segment_info in self.lineSegmentData:
            course_idx, seg_idx, p1, p2 = segment_info
            distance = self.distancePointToLineSegment(click_x, click_y, p1.x(), p1.y(), p2.x(), p2.y())
            
            if distance < min_distance:
                min_distance = distance
                closest_segment = segment_info
        
        # If click is reasonably close to a line segment (within 50 pixels)
        if closest_segment and min_distance < 50:
            course_idx, seg_idx, p1, p2 = closest_segment
            self.splitCourse(course_idx, seg_idx)
        else:
            self.writeLog("Click too far from any polyline. Try clicking closer to a line.")
    
    def splitCourse(self, course_index, segment_index):
        """
        Split a course at the specified segment index.
        The course is split so that blobs [0...segment_index] go to the first half,
        and blobs [segment_index+1...] go to the second half.
        """
        if course_index >= len(self.coursesData):
            self.writeLog("Invalid course index!")
            return
        
        course = self.coursesData[course_index]
        
        if segment_index >= len(course['blobs']) - 1:
            self.writeLog("Cannot split at this position!")
            return
        
        # Split the blob list
        first_half = course['blobs'][:segment_index + 1]
        second_half = course['blobs'][segment_index + 1:]
        
        if len(first_half) == 0 or len(second_half) == 0:
            self.writeLog("Cannot create empty courses!")
            return
        
        # Replace the original course with the two new courses
        new_courses = (
            self.coursesData[:course_index] +
            [self.createCourseData(first_half), self.createCourseData(second_half)] +
            self.coursesData[course_index + 1:]
        )
        
        self.coursesData = new_courses
        
        # Sort courses to preserve ordering
        self.sortCourses()
        
        # Recompute inclination for split courses
        self.computeInclination()
        
        # Refresh the visualization and table
        self.displayCourses()
        self.populateCoursesTable()
        self.removeInclinationLines()  # Clear old inclination lines after split
        self.removeSegmentInclinationEntities()  # Clear old segment angles after split
        
        # Redisplay inclination if button is checked
        if self.btnAnalyzeInclination.isChecked():
            self.displayInclinationLines()
        
        # Redisplay segment angles if button is checked
        if self.btnSegmentInclination.isChecked():
            self.displaySegmentInclination()
        
        # Log the result
        self.writeLog("Course split complete. Now {} courses total.".format(len(self.coursesData)))

    ########################################################################################
    # SAVE/RESTORE STATE FUNCTIONS
    ########################################################################################
    
    @pyqtSlot()
    def saveState(self):
        """
        Save the current state of courses to a JSON file.
        """
        if self.coursesData is None or len(self.coursesData) == 0:
            QMessageBox.warning(self, "No Data", "No courses detected yet. Please run 'Recognize Courses' first.")
            return
        
        # Get the project folder as the default directory
        default_dir = ""
        if hasattr(self.activeviewer, 'project') and self.activeviewer.project.filename:
            project_file = self.activeviewer.project.filename
            default_dir = os.path.dirname(project_file)
        
        # Open file dialog in the project folder
        filters = "Course Analysis State (*.json)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save Course Analysis State", default_dir, filters)
        
        if not filename:
            return
        
        if not filename.endswith('.json'):
            filename += '.json'
        
        try:
            # Prepare data to save
            state_data = {
                'version': '1.0',
                'tolerance_params': {
                    'y_tolerance': self.editYTolerance.text(),
                    'ytb_tolerance': self.editYTBTolerance.text(),
                    'height_tolerance': self.editHeightTolerance.text(),
                    'x_gap_tolerance': self.editXGapTolerance.text()
                },
                'color_mode': self.colorMode,
                'selected_blob_ids': [int(blob.id) for blob in self.workingBlobs],  # Convert to regular int
                'courses': []
            }
            
            # Save each course's data
            for course in self.coursesData:
                course_data = {
                    'blob_ids': [int(blob.id) for blob in course['blobs']],  # Convert to regular int
                    'centroid_y': float(course.get('centroid_y', course.get('y_pos', 0.0))),  # Convert to float
                    'avg_height': float(course['avg_height']),
                    'width': float(course['width']),
                    'inclination_deg': float(course.get('inclination_deg', 0.0)),
                    'inclination_rad': float(course.get('inclination_rad', 0.0)),
                    'num_blobs': int(course['num_blobs'])
                }
                state_data['courses'].append(course_data)
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            self.writeLog(f"State saved to: {os.path.basename(filename)}")
            QMessageBox.information(self, "Success", f"Course analysis state saved successfully to:\n{filename}")
            
        except Exception as e:
            self.writeLog(f"Error saving state: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save state:\n{str(e)}")
    
    @pyqtSlot()
    def restoreState(self):
        """
        Restore courses state from a JSON file.
        """
        # Get the project folder as the default directory
        default_dir = ""
        if hasattr(self.activeviewer, 'project') and self.activeviewer.project.filename:
            project_file = self.activeviewer.project.filename
            default_dir = os.path.dirname(project_file)
        
        # Open file dialog
        filters = "Course Analysis State (*.json)"
        filename, _ = QFileDialog.getOpenFileName(self, "Restore Course Analysis State", default_dir, filters)
        
        if not filename:
            return
        
        try:
            # Read from file
            with open(filename, 'r') as f:
                state_data = json.load(f)
            
            # Validate version
            if 'version' not in state_data:
                QMessageBox.warning(self, "Invalid File", "This file does not appear to be a valid course analysis state file.")
                return
            
            # Restore tolerance parameters
            if 'tolerance_params' in state_data:
                params = state_data['tolerance_params']
                self.editYTolerance.setText(params.get('y_tolerance', '0.3'))
                self.editYTBTolerance.setText(params.get('ytb_tolerance', '0.3'))
                self.editHeightTolerance.setText(params.get('height_tolerance', '0.3'))
                self.editXGapTolerance.setText(params.get('x_gap_tolerance', '3.0'))
            
            # Restore color mode
            if 'color_mode' in state_data:
                self.colorMode = state_data['color_mode']
                self.comboColorMode.setCurrentText(self.colorMode)
            
            # Get all available blobs from the image
            all_blobs = self.activeviewer.annotations.seg_blobs
            blob_dict = {blob.id: blob for blob in all_blobs}
            
            # Restore selected blobs - validate IDs
            missing_selected = []
            if 'selected_blob_ids' in state_data:
                selected_ids = state_data['selected_blob_ids']
                self.workingBlobs = []
                for bid in selected_ids:
                    if bid in blob_dict:
                        self.workingBlobs.append(blob_dict[bid])
                    else:
                        missing_selected.append(bid)
                
                if missing_selected:
                    self.writeLog(f"Warning: {len(missing_selected)} selected region(s) not found: {missing_selected}")
            
            # Restore courses - validate blob IDs and check for missing/partial courses
            if 'courses' in state_data:
                self.coursesData = []
                total_missing_blobs = 0
                skipped_courses = 0
                
                for course_idx, course_data in enumerate(state_data['courses']):
                    blob_ids = course_data['blob_ids']
                    course_blobs = []
                    missing_in_course = []
                    
                    # Validate each blob ID in the course
                    for bid in blob_ids:
                        if bid in blob_dict:
                            course_blobs.append(blob_dict[bid])
                        else:
                            missing_in_course.append(bid)
                            total_missing_blobs += 1
                    
                    # Only restore course if at least some blobs were found
                    if len(course_blobs) > 0:
                        # Always use createCourseData to ensure all fields are present
                        course = self.createCourseData(course_blobs)
                        # Preserve saved inclination values if they exist
                        course['inclination_deg'] = course_data.get('inclination_deg', 0.0)
                        course['inclination_rad'] = course_data.get('inclination_rad', 0.0)
                        
                        if missing_in_course:
                            self.writeLog(f"Course {course_idx}: {len(missing_in_course)} blob(s) missing, recalculated properties")
                        
                        self.coursesData.append(course)
                    else:
                        # All blobs in this course are missing
                        self.writeLog(f"Warning: Course {course_idx} skipped - all {len(blob_ids)} blob(s) missing: {blob_ids}")
                        skipped_courses += 1
                
                # Summary of restoration issues
                if total_missing_blobs > 0 or skipped_courses > 0:
                    summary = f"Restoration issues: {total_missing_blobs} blob(s) missing across courses"
                    if skipped_courses > 0:
                        summary += f", {skipped_courses} course(s) completely skipped"
                    self.writeLog(summary)
            
            # Update displays
            self.logArea.clear()
            self.writeLog(f"State restored from: {os.path.basename(filename)}")
            self.writeLog(f"Loaded {len(self.coursesData)} course(s) with {len(self.workingBlobs)} region(s)")
            
            # Report validation results
            if missing_selected:
                self.writeLog(f"⚠ {len(missing_selected)} selected region(s) no longer exist in project")
            
            total_restored = sum(len(course['blobs']) for course in self.coursesData)
            total_expected = sum(len(course_data['blob_ids']) for course_data in state_data.get('courses', []))
            if total_restored < total_expected:
                self.writeLog(f"⚠ {total_expected - total_restored} region(s) from courses no longer exist in project")
            
            # Recompute fit_slope and fit_intercept for inclination display
            self.computeInclination()
            
            # Populate table and display
            self.populateCoursesTable()
            self.displayCourses()
            
            # Redisplay visualizations if they were active
            if self.btnAnalyzeInclination.isChecked():
                self.displayInclinationLines()
            if self.btnSegmentInclination.isChecked():
                self.displaySegmentInclination()
            
            QMessageBox.information(self, "Success", f"Course analysis state restored successfully from:\n{filename}")
            
        except json.JSONDecodeError as e:
            self.writeLog(f"Error: Invalid JSON file: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to parse JSON file:\n{str(e)}")
        except Exception as e:
            self.writeLog(f"Error restoring state: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to restore state:\n{str(e)}")

