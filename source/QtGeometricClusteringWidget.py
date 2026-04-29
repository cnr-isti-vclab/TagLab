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

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QPointF
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF
from PyQt5.QtWidgets import (QWidget, QTextEdit, QPushButton, QHBoxLayout, QVBoxLayout, 
                              QGroupBox, QMessageBox, QComboBox, QCheckBox, QLabel, 
                              QTableWidget, QTableWidgetItem, QSplitter, QSpinBox,
                              QDoubleSpinBox, QApplication, QSizePolicy, QRadioButton, QButtonGroup)
from skimage import measure
import math
import cv2
import numpy as np
import os

# Fix for Windows scikit-learn threading issue
os.environ["LOKY_MAX_CPU_COUNT"] = "1"

from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, MeanShift, SpectralClustering, estimate_bandwidth
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from scipy.stats import gaussian_kde

# Matplotlib for plotting
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class QtGeometricClusteringWidget(QWidget):
    """
    Widget for geometric clustering functionality.
    Performs clustering analysis on selected regions based on geometric properties.
    """

    closewidget = pyqtSignal()

    # -----------------------------------------------------------------------
    # TOOLTIPS — edit all tooltip text here
    # -----------------------------------------------------------------------
    TOOLTIPS = {
        # --- geometric properties (shown on the checkboxes) ---
        "area":          "Total area of the region in mm² (px² if no scale is set).",
        "perimeter":     "Length of the region boundary in mm (px if no scale is set).",
        "bboxMaj":       "Longest side of the axis-aligned bounding box in mm.",
        "bboxMin":       "Shortest side of the axis-aligned bounding box in mm.",
        "bboxAspect":    "Ratio of the longest to the shortest side of the bounding box (dimensionless).",
        "bboxWidth":     "Horizontal extent of the bounding box in mm.",
        "bboxHeight":    "Vertical extent of the bounding box in mm.",
        "ellipseMaj":    "Length of the major axis of the best-fit ellipse in mm.",
        "ellipseMin":    "Length of the minor axis of the best-fit ellipse in mm.",
        "ellipseAspect": "Ratio of major to minor axis of the best-fit ellipse (dimensionless).",
        "ellipseOrient": "Angle (degrees) of the major axis relative to the horizontal.",
        "ellipseEcc":    "Eccentricity of the best-fit ellipse (0 = perfect circle, 1 = line; dimensionless).",
        "rectMaj":       "Longest side of the minimum-area bounding rectangle in mm.",
        "rectMin":       "Shortest side of the minimum-area bounding rectangle in mm.",
        "rectAspect":    "Ratio of longest to shortest side of the minimum-area bounding rectangle (dimensionless).",
        "rectOrient":    "Rotation angle (degrees) of the minimum-area bounding rectangle.",
        "rectFill":      "Ratio of region area to minimum bounding rectangle area (dimensionless; 1 = fills rectangle perfectly, lower = rounder or more irregular).",
        "convexArea":    "Area of the convex hull that encloses the region in mm².",
        "solidity":      "Ratio of region area to convex hull area (dimensionless; 1 = perfectly convex, lower = more irregular/concave).",
        # --- algorithm selector ---
        "algoCombo":     "Clustering algorithm to apply to the selected geometric properties.",
        # --- algorithm-specific parameters ---
        "paramSpin":     "Number of clusters (K) used by K-Means and Hierarchical algorithms.",
        "epsSpin":       "Neighborhood radius for DBSCAN. Smaller values produce tighter, more numerous clusters.",
        "bandwidthSpin": "Kernel bandwidth for Mean Shift. Set to 0 to estimate it automatically from the data.",
        # --- action controls ---
        "btnCluster":    "Run clustering on the selected regions using the chosen algorithm and properties.",
        "cbShowClusters":"Overlay region colors in the image viewer (colored by class or cluster).",
    }

    _GROUPBOX_STYLE = """
        QGroupBox {
            background-color: rgb(45,45,45);
            color: white;
            border: 2px solid rgb(80,80,80);
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
    """

    _SPINBOX_STYLE = """
        QAbstractSpinBox {
            background-color: rgb(60,60,60);
            color: white;
            border: 1px solid rgb(100,100,100);
            padding: 2px;
        }
    """

    def __init__(self, viewer, parent=None):
        super(QtGeometricClusteringWidget, self).__init__(parent)

        # DATA ##########################################################
        # active viewer
        self.activeviewer = viewer
        # the set of working blobs, that contain the blobs being analyzed
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        # store computed geometric data
        self.geometricData = {}
        # store plot data (feature matrix built from checkboxes + geometricData)
        self.plotData = None
        # store clustering results
        self.clusterLabels = None
        # store colorized entities for visualization
        self.colorizedEntities = []

        # EVENTS ###########################################################
        # Connect to selectionChanged signal of the activeviewer
        if hasattr(self.activeviewer, 'selectionChanged'):
            self.activeviewer.selectionChanged.connect(self.onSelectionChanged)
        # Connect single click so clicking a blob in the viewer selects the table row
        if hasattr(self.activeviewer, 'leftMouseButtonPressed'):
            self.activeviewer.leftMouseButtonPressed.connect(self.onViewerClick)

        # INTERFACE ###########################################################
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(40,40,40); 
                color: white;
            }
            QToolTip { 
                background-color: rgb(240,240,240); 
                color: black; 
                border: 1px solid rgb(100,100,100);
                padding: 3px;
            }
        """)

        mainLayout = QVBoxLayout()

        # GROUP BOX for property selection
        propSelGroup = QGroupBox("Properties for Clustering")
        propSelGroup.setStyleSheet(self._GROUPBOX_STYLE)
        propSelLayout = QHBoxLayout()

        prop_groups = [
            ("Basic", [
                ("area",          "Area"),
                ("perimeter",     "Perimeter"),
            ]),
            ("Bounding Box", [
                ("bboxMaj",       "Major Extent"),
                ("bboxMin",       "Minor Extent"),
                ("bboxAspect",    "Aspect Ratio"),
                ("bboxWidth",     "Width (horiz)"),
                ("bboxHeight",    "Height (vert)"),
            ]),
            ("Ellipse", [
                ("ellipseMaj",    "Maj Axis"),
                ("ellipseMin",    "Min Axis"),
                ("ellipseAspect", "Aspect Ratio"),
                ("ellipseOrient", "Orientation"),
                ("ellipseEcc",    "Eccentricity"),
            ]),
            ("Min Rectangle", [
                ("rectMaj",       "Maj Side"),
                ("rectMin",       "Min Side"),
                ("rectAspect",    "Aspect Ratio"),
                ("rectOrient",    "Orientation"),
            ]),
            ("Convex Hull", [
                ("convexArea",    "Conv. Area"),
            ]),
            ("Derived", [
                ("solidity",      "Solidity"),
                ("rectFill",      "Rect. Fill"),
            ]),
        ]
        default_checked = {"area"}
        self.propCheckboxes = {}
        for group_name, props in prop_groups:
            colLayout = QVBoxLayout()
            lbl = QLabel(group_name)
            lbl.setStyleSheet("font-weight: bold; color: rgb(200,200,200); padding-bottom: 4px;")
            colLayout.addWidget(lbl)
            for key, display in props:
                cb = QCheckBox(display)
                cb.setChecked(key in default_checked)
                cb.setToolTip(self.TOOLTIPS.get(key, ""))
                cb.stateChanged.connect(self.onPropertyChanged)
                self.propCheckboxes[key] = cb
                colLayout.addWidget(cb)
            colLayout.addStretch()
            propSelLayout.addLayout(colLayout)

        self.propDisplayNames = {key: display for _, props in prop_groups for key, display in props}
        propSelLayout.addStretch()
        propSelGroup.setLayout(propSelLayout)
        propSelGroup.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mainLayout.addWidget(propSelGroup)

        # GROUP BOX for clustering controls
        controlsGroup = QGroupBox("Clustering Configuration")
        controlsGroup.setStyleSheet(self._GROUPBOX_STYLE)
        controlsLayout = QVBoxLayout()

        # Algorithm and parameters
        algoLayout = QHBoxLayout()
        
        lblAlgo = QLabel("Algorithm:")
        self.algoCombo = QComboBox()
        self.algoCombo.addItems(["K-Means", "DBSCAN", "Hierarchical", "Mean Shift", "Spectral"])
        self.algoCombo.setToolTip(self.TOOLTIPS["algoCombo"])
        self.algoCombo.currentTextChanged.connect(self.onAlgorithmChanged)
        
        self.lblParam = QLabel("Num Clusters:")
        self.paramSpin = QSpinBox()
        self.paramSpin.setMinimum(2)
        self.paramSpin.setMaximum(20)
        self.paramSpin.setValue(3)
        self.paramSpin.setToolTip(self.TOOLTIPS["paramSpin"])
        self.paramSpin.setStyleSheet(self._SPINBOX_STYLE)

        self.epsSpin = QDoubleSpinBox()
        self.epsSpin.setMinimum(0.1)
        self.epsSpin.setMaximum(10.0)
        self.epsSpin.setSingleStep(0.1)
        self.epsSpin.setValue(0.5)
        self.epsSpin.setDecimals(2)
        self.epsSpin.setToolTip(self.TOOLTIPS["epsSpin"])
        self.epsSpin.setVisible(False)
        self.epsSpin.setStyleSheet(self._SPINBOX_STYLE)

        self.bandwidthSpin = QDoubleSpinBox()
        self.bandwidthSpin.setMinimum(0.0)
        self.bandwidthSpin.setMaximum(100.0)
        self.bandwidthSpin.setSingleStep(0.1)
        self.bandwidthSpin.setValue(0.0)
        self.bandwidthSpin.setDecimals(2)
        self.bandwidthSpin.setToolTip(self.TOOLTIPS["bandwidthSpin"])
        self.bandwidthSpin.setVisible(False)
        self.bandwidthSpin.setStyleSheet(self._SPINBOX_STYLE)

        self.btnCluster = QPushButton("Run Clustering")
        self.btnCluster.setToolTip(self.TOOLTIPS["btnCluster"])
        self.btnCluster.clicked.connect(self.runClustering)
        self.btnCluster.setEnabled(False)
        
        self.cbShowClusters = QCheckBox("Show in viewer")
        self.cbShowClusters.setToolTip(self.TOOLTIPS["cbShowClusters"])
        self.cbShowClusters.setChecked(True)
        self.cbShowClusters.stateChanged.connect(self.toggleClusterVisualization)
        self.cbShowClusters.setEnabled(False)
        
        algoLayout.addWidget(lblAlgo)
        algoLayout.addWidget(self.algoCombo)
        algoLayout.addSpacing(20)
        algoLayout.addWidget(self.lblParam)
        algoLayout.addWidget(self.paramSpin)
        algoLayout.addWidget(self.epsSpin)
        algoLayout.addWidget(self.bandwidthSpin)
        algoLayout.addSpacing(20)
        algoLayout.addWidget(self.btnCluster)
        algoLayout.addWidget(self.cbShowClusters)
        algoLayout.addStretch()
        
        controlsLayout.addLayout(algoLayout)

        # Color-by controls
        colorByLayout = QHBoxLayout()
        colorByLayout.addWidget(QLabel("Color by:"))
        self.rbClass = QRadioButton("Class")
        self.rbCluster = QRadioButton("Cluster")
        self.rbClass.setChecked(True)
        self.rbCluster.setEnabled(False)
        self.colorByGroup = QButtonGroup(self)
        self.colorByGroup.addButton(self.rbClass)
        self.colorByGroup.addButton(self.rbCluster)
        self.colorByGroup.buttonClicked.connect(self.onColorModeChanged)
        colorByLayout.addWidget(self.rbClass)
        colorByLayout.addWidget(self.rbCluster)
        colorByLayout.addStretch()
        controlsLayout.addLayout(colorByLayout)

        controlsGroup.setLayout(controlsLayout)
        controlsGroup.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mainLayout.addWidget(controlsGroup)

        # Create splitter for results (table and plot)
        resultsSplitter = QSplitter(Qt.Horizontal)
        
        # Results table
        self.resultsTable = QTableWidget()
        self.resultsTable.verticalHeader().setVisible(False)
        self.resultsTable.setStyleSheet("""
            QTableWidget { 
                background-color: rgb(50,50,50); 
            }
            QHeaderView::section { 
                background-color: rgb(80,80,80); 
                color: white; 
            }
            QTableWidget::item { 
                padding: 5px; 
                color: white;
            }
            QTableWidget::item:selected { 
                background-color: rgb(50,50,120); 
            }
        """)
        
        # Matplotlib plot
        self.figure = Figure(figsize=(5, 4), facecolor='#2a2a2a', layout='constrained')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: rgb(42,42,42);")
        
        resultsSplitter.addWidget(self.resultsTable)
        resultsSplitter.addWidget(self.canvas)
        resultsSplitter.setStretchFactor(0, 1)
        resultsSplitter.setStretchFactor(1, 1)
        
        mainLayout.addWidget(resultsSplitter)

        # Log area - text display for output
        self.logArea = QTextEdit()
        self.logArea.setReadOnly(True)
        self.logArea.setStyleSheet("QTextEdit { background-color: rgb(50,50,50); color: white; }")
        self.logArea.setMinimumHeight(80)
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
        self.setWindowTitle("Geometric Clustering")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)
        
        # Set size based on screen dimensions (70% width, 75% height)
        screen = QApplication.primaryScreen().geometry()
        width = int(screen.width() * 0.60)
        height = int(screen.height() * 0.70)
        self.setMinimumWidth(width)
        self.setMinimumHeight(height)
        self.resize(width, height)

        # Highlight state
        self.highlightedEntity = None
        self._highlightScatter = None

        # Connect table selection to highlight handler
        self.resultsTable.itemSelectionChanged.connect(self.onTableSelectionChanged)

        # Compute all properties for current selection at startup
        classes = {b.class_name for b in self.workingBlobs}
        self.writeLog("{} selected regions. {} classes [{}]".format(
            len(self.workingBlobs), len(classes), ", ".join(sorted(classes))))
        self.writeLog("")
        self.computeProperties()
        if self.geometricData:
            self._refreshPlot()

    def closeEvent(self, event):
        # Disconnect viewer signal so selection changes no longer trigger computation
        if hasattr(self.activeviewer, 'selectionChanged'):
            try:
                self.activeviewer.selectionChanged.disconnect(self.onSelectionChanged)
            except (TypeError, RuntimeError):
                pass
        if hasattr(self.activeviewer, 'leftMouseButtonPressed'):
            try:
                self.activeviewer.leftMouseButtonPressed.disconnect(self.onViewerClick)
            except (TypeError, RuntimeError):
                pass
        # Remove highlight and colorized entities
        self.removeHighlight()
        self.removeColorizedEntities()
        # emit the signal to notify the main window
        self.closewidget.emit()
        super(QtGeometricClusteringWidget, self).closeEvent(event)

    @pyqtSlot(float, float)
    def onViewerClick(self, x, y):
        """Called on left mouse press in viewer. If the clicked blob is in the working set
        and the table is populated, selects the matching row in the results table."""
        if self.plotData is None:
            return
        blob = self.activeviewer.annotations.clickedBlob(x, y)
        if blob is None:
            return
        working_ids = {b.id for b in self.workingBlobs}
        if blob.id not in working_ids:
            return
        for row in range(self.resultsTable.rowCount()):
            id_item = self.resultsTable.item(row, 0)
            if id_item is not None and id_item.data(Qt.UserRole) == blob.id:
                self.resultsTable.selectRow(row)
                self.resultsTable.scrollToItem(id_item)
                break

    @pyqtSlot()
    def onSelectionChanged(self):
        """Called when the selection changes in the viewer"""
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        self.writeLog("Selection changed. Now {} region(s) selected.".format(len(self.workingBlobs)))
        # Reset all data
        self.geometricData = {}
        self.plotData = None
        self.clusterLabels = None
        self.btnCluster.setEnabled(False)
        self.cbShowClusters.setEnabled(False)
        self.colorByGroup.blockSignals(True)
        self.rbCluster.setEnabled(False)
        self.rbClass.setChecked(True)
        self.colorByGroup.blockSignals(False)
        self.removeHighlight()
        self.removeColorizedEntities()
        # Clear stale table and plot
        self.resultsTable.clear()
        self.resultsTable.setRowCount(0)
        self.resultsTable.setColumnCount(0)
        self.figure.clear()
        self.canvas.draw()
        # Recompute properties and plot for the new selection
        if len(self.workingBlobs) > 0:
            self.computeProperties()
            self._refreshPlot()

    def onAlgorithmChanged(self, algo_name):
        """Update parameter controls based on selected algorithm"""
        self.paramSpin.setVisible(False)
        self.epsSpin.setVisible(False)
        self.bandwidthSpin.setVisible(False)
        if algo_name == "DBSCAN":
            self.lblParam.setText("Eps:")
            self.epsSpin.setVisible(True)
        elif algo_name == "Mean Shift":
            self.lblParam.setText("Bandwidth (0=auto):")
            self.bandwidthSpin.setVisible(True)
        else:
            self.lblParam.setText("Num Clusters:")
            self.paramSpin.setVisible(True)

    def onColorModeChanged(self, btn):
        """Called when the color-by radio selection changes."""
        self.updatePlot()
        if self.cbShowClusters.isChecked() and self.plotData is not None:
            self.updateViewerOverlay()

    def writeLog(self, message):
        """Write a message to the log area"""
        self.logArea.append(message)


    ########################################################################################
    # GEOMETRIC COMPUTATION FUNCTIONS
    ########################################################################################

    def computeProperties(self):
        """Compute all geometric properties for all selected regions"""
        if len(self.workingBlobs) == 0:
            self.btnCluster.setEnabled(False)
            return

        pxmm = self.activeviewer.px_to_mm
        pxmm2 = pxmm * pxmm
        self.geometricData = {}

        for blob in self.workingBlobs:
            mask_uint8 = blob.getMask().astype(np.uint8)
            blobMeasure = measure.regionprops(mask_uint8)
            if not blobMeasure:
                self.writeLog("Warning: blob {} has empty mask, skipping.".format(blob.id))
                continue

            region = blobMeasure[0]
            d = {}

            # Basic
            d['area']      = blob.area * pxmm2
            d['perimeter'] = blob.perimeter * pxmm

            # Axis-Aligned Bounding Box
            bboxW = (region.bbox[3] - region.bbox[1]) * pxmm
            bboxH = (region.bbox[2] - region.bbox[0]) * pxmm
            d['bboxWidth']  = bboxW
            d['bboxHeight'] = bboxH
            bboxMaj = max(bboxW, bboxH)
            bboxMin = min(bboxW, bboxH)
            d['bboxMaj']    = bboxMaj
            d['bboxMin']    = bboxMin
            d['bboxAspect'] = bboxMaj / bboxMin if bboxMin > 0 else 1.0

            # Fitted Ellipse
            maj  = region.major_axis_length * pxmm
            min_ = region.minor_axis_length * pxmm
            d['ellipseMaj']    = maj
            d['ellipseMin']    = min_
            d['ellipseAspect'] = maj / min_ if min_ > 0 else 1.0
            orientation = (region.orientation * 180 / math.pi) - 90.0
            if orientation < -90:   orientation += 180
            elif orientation > 90:  orientation -= 180
            d['ellipseOrient'] = orientation
            d['ellipseEcc']    = region.eccentricity

            # Minimum Rectangle
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                rect = cv2.minAreaRect(contours[0])
                if rect[1][1] >= rect[1][0]:
                    rect = (rect[0], (rect[1][1], rect[1][0]), rect[2] - 90.0)
                majSide = rect[1][0] * pxmm
                minSide = rect[1][1] * pxmm
                d['rectMaj']    = majSide
                d['rectMin']    = minSide
                d['rectAspect'] = majSide / minSide if minSide > 0 else 1.0
                d['rectOrient'] = -rect[2]
                rect_area = majSide * minSide
                d['rectFill']   = (blob.area * pxmm2) / rect_area if rect_area > 0 else 1.0
            else:
                d['rectMaj'] = d['rectMin'] = d['rectAspect'] = d['rectOrient'] = d['rectFill'] = 0.0

            # Convex Hull
            d['convexArea'] = region.area_convex * pxmm2
            d['solidity']   = region.area / region.area_convex if region.area_convex > 0 else 1.0

            self.geometricData[blob.id] = d

        self.writeLog("Properties computed for {} regions. Ready for clustering.".format(
            len(self.geometricData)))
        self.btnCluster.setEnabled(True)

    def buildPlotData(self):
        """Build the feature matrix from selected properties and geometricData."""
        selected_props = [key for key, cb in self.propCheckboxes.items() if cb.isChecked()]
        if not selected_props or not self.geometricData:
            self.plotData = None
            self.cbShowClusters.setEnabled(False)
            return
        data_matrix = []
        blob_ids = []
        for blob in self.workingBlobs:
            if blob.id not in self.geometricData:
                continue
            row = [self.geometricData[blob.id][prop] for prop in selected_props]
            data_matrix.append(row)
            blob_ids.append(blob.id)
        if not data_matrix:
            self.plotData = None
            self.cbShowClusters.setEnabled(False)
            return
        X = np.array(data_matrix)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        self.plotData = {
            'X': X,
            'X_scaled': X_scaled,
            'blob_ids': blob_ids,
            'properties': selected_props,
        }
        self.cbShowClusters.setEnabled(True)

    def _refreshPlot(self):
        """Rebuild the feature matrix, redraw the plot, refresh the table and viewer overlay."""
        self.buildPlotData()
        self.displayResults()
        self.updatePlot()
        if self.cbShowClusters.isChecked() and self.plotData is not None:
            self.updateViewerOverlay()

    @pyqtSlot(int)
    def onPropertyChanged(self, state):
        """Called when a property checkbox is toggled. Invalidates clustering and refreshes plot."""
        self.clusterLabels = None
        self.colorByGroup.blockSignals(True)
        self.rbCluster.setEnabled(False)
        self.rbClass.setChecked(True)
        self.colorByGroup.blockSignals(False)
        # Clear stale cluster results from table (will be repopulated by _refreshPlot)
        if self.geometricData:
            self._refreshPlot()

    ########################################################################################
    # CLUSTERING FUNCTIONS
    ########################################################################################

    def runClustering(self):
        """Run geometric clustering analysis on selected regions"""
        if len(self.workingBlobs) == 0:
            self.writeLog("No regions selected!")
            return
        
        if not self.geometricData:
            self.writeLog("Please compute properties first!")
            return

        # Check which properties are selected
        selected_props = [key for key, cb in self.propCheckboxes.items() if cb.isChecked()]

        if len(selected_props) == 0:
            QMessageBox.warning(self, "No Properties Selected",
                              "Please select at least one property for clustering.")
            return

        self.writeLog("Running clustering with properties: {}".format(", ".join(selected_props)))

        # Ensure plot data is built from the current property selection
        if self.plotData is None or self.plotData['properties'] != selected_props:
            self.buildPlotData()
        if self.plotData is None:
            return

        blob_ids = self.plotData['blob_ids']
        X_scaled = self.plotData['X_scaled']

        # Apply clustering algorithm
        algo_name = self.algoCombo.currentText()
        n_clusters = self.paramSpin.value()

        # Guard: cannot have more clusters than samples
        if algo_name in ("K-Means", "Hierarchical", "Spectral") and n_clusters > len(blob_ids):
            QMessageBox.warning(self, "Too Many Clusters",
                "Number of clusters ({}) exceeds the number of regions ({}).".format(
                    n_clusters, len(blob_ids)))
            return

        try:
            if algo_name == "K-Means":
                clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                labels = clusterer.fit_predict(X_scaled)

            elif algo_name == "DBSCAN":
                eps = self.epsSpin.value()
                clusterer = DBSCAN(eps=eps, min_samples=2, n_jobs=1)
                labels = clusterer.fit_predict(X_scaled)
                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                self.writeLog("DBSCAN found {} clusters (eps={:.2f})".format(n_clusters, eps))

            elif algo_name == "Hierarchical":
                clusterer = AgglomerativeClustering(n_clusters=n_clusters)
                labels = clusterer.fit_predict(X_scaled)

            elif algo_name == "Mean Shift":
                bw = self.bandwidthSpin.value()
                if bw == 0.0:
                    bw = estimate_bandwidth(X_scaled, quantile=0.2)
                    self.writeLog("Mean Shift: auto bandwidth = {:.4f}".format(bw))
                if bw == 0.0:
                    self.writeLog("Mean Shift: bandwidth is 0 (all points identical?), using fallback 0.5")
                    bw = 0.5
                clusterer = MeanShift(bandwidth=bw, bin_seeding=True)
                labels = clusterer.fit_predict(X_scaled)
                n_clusters = len(set(labels))
                self.writeLog("Mean Shift found {} clusters".format(n_clusters))

            elif algo_name == "Spectral":
                clusterer = SpectralClustering(n_clusters=n_clusters, random_state=42,
                                               affinity='nearest_neighbors', n_jobs=1)
                labels = clusterer.fit_predict(X_scaled)

        except Exception as e:
            self.writeLog("Error during clustering: {}".format(str(e)))
            QMessageBox.critical(self, "Clustering Error", 
                               "An error occurred during clustering:\n{}".format(str(e)))
            return
        
        self.clusterLabels = labels
        # Enable cluster radio and switch to it (block signal to avoid double overlay update)
        self.colorByGroup.blockSignals(True)
        self.rbCluster.setEnabled(True)
        self.rbCluster.setChecked(True)
        self.colorByGroup.blockSignals(False)

        # Display results
        self.displayResults()
        self.updatePlot()
        
        self.writeLog("Clustering complete. Found {} clusters.".format(
            len(set(labels)) - (1 if -1 in labels else 0)))
        
        # Update viewer overlay
        self.cbShowClusters.setEnabled(True)
        if self.cbShowClusters.isChecked():
            self.updateViewerOverlay()

    def displayResults(self):
        """Display regions in the table. Shows Cluster column only when clustering has been run."""
        if self.plotData is None:
            return

        has_clusters = self.clusterLabels is not None
        labels = self.clusterLabels
        blob_ids = self.plotData['blob_ids']
        properties = self.plotData['properties']
        X = self.plotData['X']

        # Columns: Region ID, Class, [Cluster,] properties
        n_cols = (3 if has_clusters else 2) + len(properties)
        self.resultsTable.clear()
        self.resultsTable.setRowCount(len(blob_ids))
        self.resultsTable.setColumnCount(n_cols)

        if has_clusters:
            headers = ["Region ID", "Class", "Cluster"] + [self.propDisplayNames.get(p, p) for p in properties]
        else:
            headers = ["Region ID", "Class"] + [self.propDisplayNames.get(p, p) for p in properties]
        self.resultsTable.setHorizontalHeaderLabels(headers)

        # Sort by cluster when available (noise last), otherwise keep blob order
        if has_clusters:
            sort_key = np.where(labels == -1, labels.max() + 1 if labels.max() >= 0 else 0, labels)
            sorted_indices = np.argsort(sort_key, kind='stable')
        else:
            sorted_indices = np.arange(len(blob_ids))

        blob_map = {b.id: b for b in self.workingBlobs}
        prop_col_offset = 3 if has_clusters else 2
        for row, idx in enumerate(sorted_indices):
            blob_id = blob_ids[idx]

            # Region ID
            id_item = QTableWidgetItem(str(blob_id))
            id_item.setData(Qt.UserRole, blob_id)
            id_item.setTextAlignment(Qt.AlignCenter)
            self.resultsTable.setItem(row, 0, id_item)

            # Class name
            blob = blob_map.get(blob_id)
            class_name = blob.class_name if blob is not None else ""
            class_item = QTableWidgetItem(class_name)
            class_item.setTextAlignment(Qt.AlignCenter)
            class_item.setBackground(self.getClassColor(class_name))
            self.resultsTable.setItem(row, 1, class_item)

            # Cluster (optional)
            if has_clusters:
                label = labels[idx]
                cluster_text = str(label) if label != -1 else "Noise"
                cluster_item = QTableWidgetItem(cluster_text)
                cluster_item.setTextAlignment(Qt.AlignCenter)
                if label != -1:
                    cluster_item.setBackground(self.getClusterColor(label))
                self.resultsTable.setItem(row, 2, cluster_item)

            # Properties
            for j, prop in enumerate(properties):
                value_item = QTableWidgetItem("{:.2f}".format(X[idx, j]))
                value_item.setTextAlignment(Qt.AlignRight)
                self.resultsTable.setItem(row, prop_col_offset + j, value_item)

        self.resultsTable.resizeColumnsToContents()
        self.resultsTable.setColumnWidth(1, 80)

    def updatePlot(self):
        """Plot data colored by class or by cluster."""
        if self.plotData is None:
            self.figure.clear()
            self.canvas.draw()
            return

        color_mode = 'cluster' if (self.rbCluster.isChecked() and self.clusterLabels is not None) else 'class'
        X_scaled = self.plotData['X_scaled']
        X_original = self.plotData['X']
        properties = self.plotData['properties']
        blob_ids = self.plotData['blob_ids']
        n = len(blob_ids)

        # Build per-point group key and color lookup
        if color_mode == 'cluster':
            labels_arr = self.clusterLabels
            group_keys = [int(labels_arr[i]) for i in range(n)]
            noise_key = -1
            def get_color(k):
                return self.getClusterColor(k) if k != -1 else QColor(128, 128, 128)
            def fmt_label(k):
                return 'Noise' if k == -1 else 'Cluster {}'.format(k)
        else:
            blob_map = {b.id: b for b in self.workingBlobs}
            group_keys = [blob_map[bid].class_name if bid in blob_map else '' for bid in blob_ids]
            noise_key = None
            def get_color(k):
                return self.getClassColor(k)
            def fmt_label(k):
                return k if k else 'Unknown'

        unique_keys = sorted(set(group_keys),
                             key=lambda k: (k == noise_key, str(k) if k is not None else ''))
        group_indices = {}
        for i, k in enumerate(group_keys):
            group_indices.setdefault(k, []).append(i)

        self.figure.clear()
        ax = self.figure.add_subplot(111, facecolor='#2a2a2a')
        n_features = X_scaled.shape[1]

        if n_features == 1:
            x_vals = X_original[:, 0]
            pad = max((x_vals.max() - x_vals.min()) * 0.15, 1e-6)
            x_range = np.linspace(x_vals.min() - pad, x_vals.max() + pad, 400)
            max_density = 0.0
            overall_density = None
            if len(x_vals) >= 2:
                overall_density = gaussian_kde(x_vals)(x_range)
                max_density = max(max_density, overall_density.max())
            group_densities = {}
            for k in [gk for gk in unique_keys if gk != noise_key]:
                pts = x_vals[np.array(group_indices[k])]
                if len(pts) >= 2:
                    weight = len(pts) / len(x_vals)
                    d = gaussian_kde(pts)(x_range) * weight
                    group_densities[k] = d
                    max_density = max(max_density, d.max())
            rug_y = -0.04 * max_density if max_density > 0 else -0.04
            if overall_density is not None:
                ax.plot(x_range, overall_density, color='white', lw=2.0,
                        linestyle='--', alpha=0.6, label='All data')
            for k in [gk for gk in unique_keys if gk != noise_key]:
                color = get_color(k)
                color_str = color.name()
                pts = x_vals[np.array(group_indices[k])]
                if k in group_densities:
                    ax.fill_between(x_range, group_densities[k], alpha=0.25, color=color_str)
                    ax.plot(x_range, group_densities[k], color=color_str, lw=1.5, label=fmt_label(k))
                ax.plot(pts, np.full_like(pts, rug_y), '|',
                        color=color_str, markersize=12, lw=1.5, clip_on=False)
            if noise_key in group_indices:
                pts = x_vals[np.array(group_indices[noise_key])]
                ax.plot(pts, np.full_like(pts, rug_y), '|',
                        color='gray', markersize=12, lw=1.5, label='Noise', clip_on=False)
            ax.set_xlabel(self.propDisplayNames.get(properties[0], properties[0]), color='white')
            ax.set_ylabel('Density', color='white')
            title = 'Cluster Distribution' if color_mode == 'cluster' else 'Class Distribution'
            ax.set_title(title, color='white', fontsize=12, pad=10)
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('white')
            ax.legend(facecolor='#3a3a3a', edgecolor='white', labelcolor='white')
            ax.grid(True, alpha=0.3, color='gray', axis='x')
            X_plot = np.column_stack([x_vals, np.zeros(n)])
            self.plotData['X_plot'] = X_plot
            self.canvas.draw()
            return

        elif n_features == 2:
            X_plot = X_original
            xlabel = self.propDisplayNames.get(properties[0], properties[0])
            ylabel = self.propDisplayNames.get(properties[1], properties[1])
        else:
            pca = PCA(n_components=2)
            X_plot = pca.fit_transform(X_scaled)
            var = pca.explained_variance_ratio_
            xlabel = "PC1 ({:.1f}% var)".format(var[0] * 100)
            ylabel = "PC2 ({:.1f}% var)".format(var[1] * 100)

        # Scatter: non-noise groups first
        for k in [gk for gk in unique_keys if gk != noise_key]:
            idxs = np.array(group_indices[k])
            color = get_color(k)
            ax.scatter(X_plot[idxs, 0], X_plot[idxs, 1],
                       c=[color.name()], label=fmt_label(k),
                       s=50, alpha=0.7, edgecolors='white', linewidths=0.5, marker='o')

        # Noise points (cluster mode only)
        if noise_key in group_indices:
            idxs = np.array(group_indices[noise_key])
            ax.scatter(X_plot[idxs, 0], X_plot[idxs, 1],
                       facecolors='none', edgecolors='gray', linewidths=1.2,
                       label='Noise', s=60, alpha=0.8, marker='o')

        # Rug marks on both axes
        x_min, x_max = X_plot[:, 0].min(), X_plot[:, 0].max()
        y_min, y_max = X_plot[:, 1].min(), X_plot[:, 1].max()
        x_rug_y = y_min - (y_max - y_min) * 0.04
        y_rug_x = x_min - (x_max - x_min) * 0.04
        for k in [gk for gk in unique_keys if gk != noise_key]:
            idxs = np.array(group_indices[k])
            color = get_color(k)
            ax.plot(X_plot[idxs, 0], np.full(len(idxs), x_rug_y), '|',
                    color=color.name(), markersize=10, lw=1.2, clip_on=False, alpha=0.7)
            ax.plot(np.full(len(idxs), y_rug_x), X_plot[idxs, 1], '_',
                    color=color.name(), markersize=10, lw=1.2, clip_on=False, alpha=0.7)
        if noise_key in group_indices:
            idxs = np.array(group_indices[noise_key])
            ax.plot(X_plot[idxs, 0], np.full(len(idxs), x_rug_y), '|',
                    color='gray', markersize=10, lw=1.2, clip_on=False, alpha=0.7)
            ax.plot(np.full(len(idxs), y_rug_x), X_plot[idxs, 1], '_',
                    color='gray', markersize=10, lw=1.2, clip_on=False, alpha=0.7)

        ax.set_xlabel(xlabel, color='white')
        ax.set_ylabel(ylabel, color='white')
        title = 'Cluster Distribution' if color_mode == 'cluster' else 'Class Distribution'
        ax.set_title(title, color='white', fontsize=12, pad=10)
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
        ax.legend(facecolor='#3a3a3a', edgecolor='white', labelcolor='white')
        ax.grid(True, alpha=0.3, color='gray')

        self.plotData['X_plot'] = X_plot
        self.canvas.draw()

    def getClusterColor(self, cluster_id):
        """Get a distinct color for each cluster"""
        colors = [
            QColor(255, 100, 100),  # Red
            QColor(100, 255, 100),  # Green
            QColor(100, 100, 255),  # Blue
            QColor(255, 255, 100),  # Yellow
            QColor(255, 100, 255),  # Magenta
            QColor(100, 255, 255),  # Cyan
            QColor(255, 150, 100),  # Orange
            QColor(150, 100, 255),  # Purple
            QColor(100, 255, 150),  # Light green
            QColor(255, 100, 150),  # Pink
        ]
        return colors[cluster_id % len(colors)]

    def getClassColor(self, class_name):
        """Return QColor for a class using the TagLab label fill color."""
        try:
            label = self.activeviewer.project.labels.get(class_name)
            if label is not None:
                fill = label.fill
                return QColor(int(fill[0]), int(fill[1]), int(fill[2]))
        except Exception:
            pass
        return QColor(180, 180, 180)

    ########################################################################################
    # VISUALIZATION FUNCTIONS
    ########################################################################################

    def toggleClusterVisualization(self, state):
        """Toggle viewer overlay visibility"""
        if state == Qt.Checked:
            if self.colorizedEntities:
                for item in self.colorizedEntities:
                    item.setVisible(True)
            else:
                self.updateViewerOverlay()
        else:
            for item in self.colorizedEntities:
                item.setVisible(False)

    def _addBlobOverlayPolygon(self, blob, color):
        """Draw a filled polygon for blob in the viewer overlay and register it."""
        min_row, min_col, _, _ = blob.bbox
        contours, _ = cv2.findContours(
            blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return
        cnt = contours[0]
        polygon = QPolygonF([
            QPointF(float(pt[0][0]) + min_col + 0.5, float(pt[0][1]) + min_row + 0.5)
            for pt in cnt
        ])
        item = self.activeviewer.scene.addPolygon(polygon, QPen(Qt.NoPen), QBrush(color))
        item.setZValue(10)
        self.colorizedEntities.append(item)

    def updateViewerOverlay(self):
        """Redraw all viewer overlay polygons colored by cluster or class."""
        self.removeColorizedEntities()
        use_clusters = self.rbCluster.isChecked() and self.clusterLabels is not None
        id_to_label = (
            dict(zip(self.plotData['blob_ids'], self.clusterLabels))
            if use_clusters else {}
        )
        for blob in self.workingBlobs:
            if use_clusters:
                label = id_to_label.get(blob.id, -1)
                if label == -1:
                    continue  # skip DBSCAN noise
                color = self.getClusterColor(label)
            else:
                color = self.getClassColor(blob.class_name)
            self._addBlobOverlayPolygon(blob, color)

    def removeColorizedEntities(self):
        """Remove colorized shapes from the viewer"""
        if self.colorizedEntities:
            for item in self.colorizedEntities:
                self.activeviewer.scene.removeItem(item)
            self.colorizedEntities = []

    def removeHighlight(self):
        """Remove viewer outline highlight and scatter highlight marker"""
        if self.highlightedEntity is not None:
            try:
                self.activeviewer.scene.removeItem(self.highlightedEntity)
            except (AttributeError, RuntimeError):
                pass
            self.highlightedEntity = None
        if self._highlightScatter is not None:
            try:
                self._highlightScatter.remove()
                if self.figure.axes:
                    self.canvas.draw()
            except Exception:
                pass
            self._highlightScatter = None

    def onTableSelectionChanged(self):
        """Highlight the selected region in the scatter plot and in the viewer."""
        self.removeHighlight()
        selected = self.resultsTable.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        id_item = self.resultsTable.item(row, 0)
        if id_item is None:
            return
        blob_id = id_item.data(Qt.UserRole)
        if blob_id is None:
            return

        # Find the blob
        blob = next((b for b in self.workingBlobs if b.id == blob_id), None)
        if blob is None:
            return

        # --- Highlight in viewer: draw a thick yellow outline ---
        min_row, min_col, _, _ = blob.bbox
        contours, _ = cv2.findContours(
            blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            cnt = contours[0]
            polygon = QPolygonF([
                QPointF(float(pt[0][0]) + min_col + 0.5, float(pt[0][1]) + min_row + 0.5)
                for pt in cnt
            ])
            pen = QPen(QColor(255, 255, 0))
            pen.setWidth(5)
            pen.setCosmetic(True)
            outline = self.activeviewer.scene.addPolygon(polygon, pen, QBrush())
            outline.setZValue(12)
            self.highlightedEntity = outline

        # --- Highlight in scatter plot ---
        X_plot = self.plotData.get('X_plot') if self.plotData else None
        blob_ids = self.plotData.get('blob_ids') if self.plotData else None
        if X_plot is not None and blob_ids is not None and self.figure.axes:
            try:
                idx = list(blob_ids).index(blob_id)
                ax = self.figure.axes[0]
                self._highlightScatter = ax.scatter(
                    [X_plot[idx, 0]], [X_plot[idx, 1]],
                    s=220, facecolors='none', edgecolors='yellow',
                    linewidths=2.5, zorder=15)
                self.canvas.draw()
            except (ValueError, IndexError):
                pass
