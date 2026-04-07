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
                              QLineEdit, QTableWidget, QTableWidgetItem, QSplitter, QSpinBox,
                              QDoubleSpinBox, QApplication, QSizePolicy)
from skimage import measure
import math
import cv2
import numpy as np
import os

# Fix for Windows scikit-learn threading issue
os.environ["LOKY_MAX_CPU_COUNT"] = "1"

from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Matplotlib for plotting
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class QtGeometricClusteringWidget(QWidget):
    """
    Widget for geometric clustering functionality.
    Performs clustering analysis on selected regions based on geometric properties.
    """

    closewidget = pyqtSignal()

    def __init__(self, viewer, parent=None):
        super(QtGeometricClusteringWidget, self).__init__(parent)

        # DATA ##########################################################
        # active viewer
        self.activeviewer = viewer
        # the set of working blobs, that contain the blobs being analyzed
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        # store computed geometric data
        self.geometricData = {}
        # store clustering results
        self.clusterLabels = None
        self.clusterData = None
        # store colorized entities for visualization
        self.colorizedEntities = []

        # EVENTS ###########################################################
        # Connect to selectionChanged signal of the activeviewer
        if hasattr(self.activeviewer, 'selectionChanged'):
            self.activeviewer.selectionChanged.connect(self.onSelectionChanged)

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

        # GROUP BOX for computation settings
        computeGroup = QGroupBox("Geometric Properties Computation")
        computeGroup.setStyleSheet("""
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
        """)
        computeLayout = QHBoxLayout()
        
        lblFitting = QLabel("Fitting Method:")
        self.fittingCombo = QComboBox()
        self.fittingCombo.addItems(["Axis-Aligned BBox", "Fitted Ellipse", "Minimum Rectangle"])
        self.fittingCombo.setToolTip("Choose which fitting method to use for width, height, and aspect ratio")
        
        self.btnCompute = QPushButton("Compute Properties")
        self.btnCompute.setToolTip("Compute geometric properties for all selected regions")
        self.btnCompute.clicked.connect(self.computeProperties)
        
        computeLayout.addWidget(lblFitting)
        computeLayout.addWidget(self.fittingCombo)
        computeLayout.addWidget(self.btnCompute)
        computeLayout.addStretch()
        
        computeGroup.setLayout(computeLayout)
        computeGroup.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mainLayout.addWidget(computeGroup)

        # GROUP BOX for clustering controls
        controlsGroup = QGroupBox("Clustering Configuration")
        controlsGroup.setStyleSheet("""
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
        """)
        controlsLayout = QVBoxLayout()

        # Property selection
        propLayout = QHBoxLayout()
        propLayout.addWidget(QLabel("Properties to use:"))
        
        self.cbArea = QCheckBox("Area")
        self.cbArea.setChecked(True)
        self.cbArea.setToolTip("Use area of region")
        
        self.cbWidth = QCheckBox("Width")
        self.cbWidth.setChecked(True)
        self.cbWidth.setToolTip("Use width from selected fitting method")
        
        self.cbHeight = QCheckBox("Height")
        self.cbHeight.setChecked(True)
        self.cbHeight.setToolTip("Use height from selected fitting method")
        
        self.cbAspect = QCheckBox("Aspect Ratio")
        self.cbAspect.setChecked(True)
        self.cbAspect.setToolTip("Use aspect ratio (width/height)")
        
        propLayout.addWidget(self.cbArea)
        propLayout.addWidget(self.cbWidth)
        propLayout.addWidget(self.cbHeight)
        propLayout.addWidget(self.cbAspect)
        propLayout.addStretch()
        controlsLayout.addLayout(propLayout)

        # Algorithm and parameters
        algoLayout = QHBoxLayout()
        
        lblAlgo = QLabel("Algorithm:")
        self.algoCombo = QComboBox()
        self.algoCombo.addItems(["K-Means", "DBSCAN", "Hierarchical"])
        self.algoCombo.currentTextChanged.connect(self.onAlgorithmChanged)
        
        self.lblParam = QLabel("Num Clusters:")
        self.paramSpin = QSpinBox()
        self.paramSpin.setMinimum(2)
        self.paramSpin.setMaximum(20)
        self.paramSpin.setValue(3)
        self.paramSpin.setToolTip("Number of clusters for K-Means and Hierarchical")
        self.paramSpin.setStyleSheet("""
            QSpinBox {
                background-color: rgb(60,60,60);
                color: white;
                border: 1px solid rgb(100,100,100);
                padding: 2px;
            }
        """)

        self.epsSpin = QDoubleSpinBox()
        self.epsSpin.setMinimum(0.1)
        self.epsSpin.setMaximum(10.0)
        self.epsSpin.setSingleStep(0.1)
        self.epsSpin.setValue(0.5)
        self.epsSpin.setDecimals(2)
        self.epsSpin.setToolTip("Eps (neighborhood radius) for DBSCAN; smaller = tighter clusters")
        self.epsSpin.setVisible(False)
        self.epsSpin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: rgb(60,60,60);
                color: white;
                border: 1px solid rgb(100,100,100);
                padding: 2px;
            }
        """)
        
        self.btnCluster = QPushButton("Run Clustering")
        self.btnCluster.setToolTip("Perform geometric clustering on selected regions")
        self.btnCluster.clicked.connect(self.runClustering)
        self.btnCluster.setEnabled(False)
        
        self.cbShowClusters = QCheckBox("Show clusters in viewer")
        self.cbShowClusters.setToolTip("Show/hide cluster colorization in the viewer")
        self.cbShowClusters.setChecked(True)
        self.cbShowClusters.stateChanged.connect(self.toggleClusterVisualization)
        self.cbShowClusters.setEnabled(False)
        
        algoLayout.addWidget(lblAlgo)
        algoLayout.addWidget(self.algoCombo)
        algoLayout.addSpacing(20)
        algoLayout.addWidget(self.lblParam)
        algoLayout.addWidget(self.paramSpin)
        algoLayout.addWidget(self.epsSpin)
        algoLayout.addSpacing(20)
        algoLayout.addWidget(self.btnCluster)
        algoLayout.addWidget(self.cbShowClusters)
        algoLayout.addStretch()
        
        controlsLayout.addLayout(algoLayout)
        controlsGroup.setLayout(controlsLayout)
        controlsGroup.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mainLayout.addWidget(controlsGroup)

        # Create splitter for results (table and plot)
        resultsSplitter = QSplitter(Qt.Horizontal)
        
        # Results table
        self.resultsTable = QTableWidget()
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
        self.figure = Figure(figsize=(5, 4), facecolor='#2a2a2a')
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

        # Initialize log with selection info
        self.logSelectedRegions()
        self.writeLog("Click 'Compute Properties' to start.")
        
        # Set cursor to arrow (in case it was changed by another tool)
        self.activeviewer.setCursor(Qt.ArrowCursor)

    def closeEvent(self, event):
        # Remove colorized entities
        self.removeColorizedEntities()
        # Reset cursor to arrow
        self.activeviewer.setCursor(Qt.ArrowCursor)
        # emit the signal to notify the main window
        self.closewidget.emit()
        super(QtGeometricClusteringWidget, self).closeEvent(event)

    @pyqtSlot()
    def onSelectionChanged(self):
        """Called when the selection changes in the viewer"""
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        self.writeLog("Selection changed. Now {} region(s) selected.".format(len(self.workingBlobs)))
        # Reset computed data
        self.geometricData = {}
        self.clusterLabels = None
        self.btnCluster.setEnabled(False)
        self.cbShowClusters.setEnabled(False)
        self.removeColorizedEntities()
        # Clear stale table and plot
        self.resultsTable.clear()
        self.resultsTable.setRowCount(0)
        self.resultsTable.setColumnCount(0)
        self.figure.clear()
        self.canvas.draw()

    def onAlgorithmChanged(self, algo_name):
        """Update parameter controls based on selected algorithm"""
        if algo_name == "DBSCAN":
            self.lblParam.setText("Eps:")
            self.paramSpin.setVisible(False)
            self.epsSpin.setVisible(True)
        else:
            self.lblParam.setText("Num Clusters:")
            self.paramSpin.setVisible(True)
            self.epsSpin.setVisible(False)

    def writeLog(self, message):
        """Write a message to the log area"""
        self.logArea.append(message)

    def logSelectedRegions(self):
        """Log information about currently selected regions"""
        num_selected = len(self.workingBlobs)
        # Count unique classes
        classes = set()
        for blob in self.workingBlobs:
            classes.add(blob.class_name)
        num_classes = len(classes)
        self.writeLog("{} selected regions. {} classes [{}]".format(
            num_selected, num_classes, ", ".join(sorted(classes))))
        self.writeLog("")

    ########################################################################################
    # GEOMETRIC COMPUTATION FUNCTIONS
    ########################################################################################

    def computeProperties(self):
        """Compute geometric properties for all selected regions"""
        if len(self.workingBlobs) == 0:
            self.writeLog("No regions selected!")
            return

        self.writeLog("Computing geometric properties...")
        
        fitting_method = self.fittingCombo.currentText()
        pxmm = self.activeviewer.px_to_mm
        pxmm2 = pxmm * pxmm
        
        self.geometricData = {}
        
        for blob in self.workingBlobs:
            mask = blob.getMask()
            mask_uint8 = mask.astype(np.uint8)
            blobMeasure = measure.regionprops(mask_uint8)

            if not blobMeasure:
                self.writeLog("Warning: blob {} has empty mask, skipping.".format(blob.id))
                continue

            region = blobMeasure[0]

            self.geometricData[blob.id] = {}

            # Always compute area
            self.geometricData[blob.id]["area"] = blob.area * pxmm2

            # Compute width, height, aspect based on fitting method
            if fitting_method == "Axis-Aligned BBox":
                width = (region.bbox[3] - region.bbox[1]) * pxmm
                height = (region.bbox[2] - region.bbox[0]) * pxmm
                self.geometricData[blob.id]["width"] = width
                self.geometricData[blob.id]["height"] = height
                self.geometricData[blob.id]["aspect"] = width / height if height > 0 else 1.0

            elif fitting_method == "Fitted Ellipse":
                maj_axis = region.major_axis_length * pxmm
                min_axis = region.minor_axis_length * pxmm
                self.geometricData[blob.id]["width"] = maj_axis
                self.geometricData[blob.id]["height"] = min_axis
                self.geometricData[blob.id]["aspect"] = maj_axis / min_axis if min_axis > 0 else 1.0

            elif fitting_method == "Minimum Rectangle":
                contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not contours:
                    self.writeLog("Warning: no contours for blob {}, skipping.".format(blob.id))
                    continue
                rect = cv2.minAreaRect(contours[0])
                if rect[1][1] >= rect[1][0]:  # swap sides to have major side first
                    rect = (rect[0], (rect[1][1], rect[1][0]), rect[2] - 90.0)
                maj_side = rect[1][0] * pxmm
                min_side = rect[1][1] * pxmm
                self.geometricData[blob.id]["width"] = maj_side
                self.geometricData[blob.id]["height"] = min_side
                self.geometricData[blob.id]["aspect"] = maj_side / min_side if min_side > 0 else 1.0
        
        self.writeLog("Computed properties for {} regions using {}.".format(
            len(self.workingBlobs), fitting_method))
        self.writeLog("Ready for clustering.")
        self.btnCluster.setEnabled(True)

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
        selected_props = []
        if self.cbArea.isChecked():
            selected_props.append("area")
        if self.cbWidth.isChecked():
            selected_props.append("width")
        if self.cbHeight.isChecked():
            selected_props.append("height")
        if self.cbAspect.isChecked():
            selected_props.append("aspect")
        
        if len(selected_props) == 0:
            QMessageBox.warning(self, "No Properties Selected", 
                              "Please select at least one property for clustering.")
            return

        self.writeLog("Running clustering with properties: {}".format(", ".join(selected_props)))
        
        # Prepare data matrix
        data_matrix = []
        blob_ids = []
        for blob in self.workingBlobs:
            row = [self.geometricData[blob.id][prop] for prop in selected_props]
            data_matrix.append(row)
            blob_ids.append(blob.id)
        
        X = np.array(data_matrix)
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Apply clustering algorithm
        algo_name = self.algoCombo.currentText()
        n_clusters = self.paramSpin.value()

        # Guard: cannot have more clusters than samples
        if algo_name in ("K-Means", "Hierarchical") and n_clusters > len(self.workingBlobs):
            QMessageBox.warning(self, "Too Many Clusters",
                "Number of clusters ({}) exceeds the number of regions ({}).".format(
                    n_clusters, len(self.workingBlobs)))
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
                
        except Exception as e:
            self.writeLog("Error during clustering: {}".format(str(e)))
            QMessageBox.critical(self, "Clustering Error", 
                               "An error occurred during clustering:\n{}".format(str(e)))
            return
        
        self.clusterLabels = labels
        self.clusterData = {
            'X': X,
            'X_scaled': X_scaled,
            'blob_ids': blob_ids,
            'properties': selected_props,
            'scaler': scaler
        }
        
        # Display results
        self.displayResults()
        self.plotClusters()
        
        self.writeLog("Clustering complete. Found {} clusters.".format(
            len(set(labels)) - (1 if -1 in labels else 0)))
        
        # Automatically show clusters in viewer
        self.cbShowClusters.setEnabled(True)
        if self.cbShowClusters.isChecked():
            self.visualizeClusters()

    def displayResults(self):
        """Display clustering results in table"""
        if self.clusterLabels is None:
            return
        
        labels = self.clusterLabels
        blob_ids = self.clusterData['blob_ids']
        properties = self.clusterData['properties']
        X = self.clusterData['X']
        
        # Setup table
        self.resultsTable.clear()
        self.resultsTable.setRowCount(len(blob_ids))
        self.resultsTable.setColumnCount(2 + len(properties))
        
        headers = ["Region ID", "Cluster"] + [p.capitalize() for p in properties]
        self.resultsTable.setHorizontalHeaderLabels(headers)
        
        # Fill table sorted by cluster label (DBSCAN noise points at the end)
        sort_key = np.where(labels == -1, labels.max() + 1 if labels.max() >= 0 else 0, labels)
        sorted_indices = np.argsort(sort_key, kind='stable')
        for row, idx in enumerate(sorted_indices):
            blob_id = blob_ids[idx]
            label = labels[idx]
            # Region ID
            id_item = QTableWidgetItem(str(blob_id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.resultsTable.setItem(row, 0, id_item)

            # Cluster label
            cluster_text = str(label) if label != -1 else "Noise"
            cluster_item = QTableWidgetItem(cluster_text)
            cluster_item.setTextAlignment(Qt.AlignCenter)
            # Color by cluster
            if label != -1:
                color = self.getClusterColor(label)
                cluster_item.setBackground(color)
            self.resultsTable.setItem(row, 1, cluster_item)

            # Properties
            for j, prop in enumerate(properties):
                value_item = QTableWidgetItem("{:.2f}".format(X[idx, j]))
                value_item.setTextAlignment(Qt.AlignRight)
                self.resultsTable.setItem(row, 2 + j, value_item)
        
        self.resultsTable.resizeColumnsToContents()

    def plotClusters(self):
        """Plot clustering results in 2D scatter plot"""
        if self.clusterLabels is None:
            return
        
        X_scaled = self.clusterData['X_scaled']
        X_original = self.clusterData['X']
        labels = self.clusterLabels
        properties = self.clusterData['properties']
        
        self.figure.clear()
        ax = self.figure.add_subplot(111, facecolor='#2a2a2a')
        
        n_features = X_scaled.shape[1]
        
        # Handle different numbers of features
        if n_features == 1:
            # Only 1 feature - plot as 1D with fixed jitter for reproducibility
            rng = np.random.default_rng(seed=0)
            X_plot = np.column_stack([X_original[:, 0], rng.standard_normal(X_original.shape[0]) * 0.1])
            xlabel = properties[0].capitalize()
            ylabel = "Jitter"
            
        elif n_features == 2:
            # Exactly 2 features - plot directly, use original values
            X_plot = X_original
            xlabel = properties[0].capitalize()
            ylabel = properties[1].capitalize()
            
        else:
            # 3+ features - use PCA to reduce to 2D (on scaled values)
            pca = PCA(n_components=2)
            X_plot = pca.fit_transform(X_scaled)
            var_explained = pca.explained_variance_ratio_
            xlabel = "PC1 ({:.1f}% var)".format(var_explained[0] * 100)
            ylabel = "PC2 ({:.1f}% var)".format(var_explained[1] * 100)
        
        # Plot each cluster with different color
        unique_labels = set(labels)
        for label in unique_labels:
            if label == -1:
                # Noise points (for DBSCAN)
                color_str = 'gray'
                marker = 'x'
                edgecolor = None
                linewidth = 0
            else:
                color = self.getClusterColor(label)
                color_str = color.name()
                marker = 'o'
                edgecolor = 'white'
                linewidth = 0.5
            
            mask = labels == label
            ax.scatter(X_plot[mask, 0], X_plot[mask, 1], 
                      c=[color_str], label=f'Cluster {label}' if label != -1 else 'Noise',
                      s=50, alpha=0.7, edgecolors=edgecolor, linewidths=linewidth, marker=marker)
        
        ax.set_xlabel(xlabel, color='white')
        ax.set_ylabel(ylabel, color='white')
        ax.set_title('Clustering Results', color='white', fontsize=12, pad=10)
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.legend(facecolor='#3a3a3a', edgecolor='white', labelcolor='white')
        ax.grid(True, alpha=0.3, color='gray')
        
        self.figure.tight_layout()
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

    ########################################################################################
    # VISUALIZATION FUNCTIONS
    ########################################################################################

    def toggleClusterVisualization(self, state):
        """Toggle cluster colorization visibility"""
        if state == Qt.Checked:
            if self.clusterLabels is not None:
                self.visualizeClusters()
        else:
            self.removeColorizedEntities()

    def visualizeClusters(self):
        """Colorize regions in the viewer by cluster membership"""
        if self.clusterLabels is None:
            return
        
        self.removeColorizedEntities()
        
        labels = self.clusterLabels
        blob_ids = self.clusterData['blob_ids']
        
        id_to_label = dict(zip(blob_ids, labels))
        for blob in self.workingBlobs:
            label = id_to_label.get(blob.id, -1)

            if label == -1:
                # Skip noise points
                continue

            color = self.getClusterColor(label)

            # Draw the blob's filled contour
            min_row, min_col, _, _ = blob.bbox
            contours, _ = cv2.findContours(blob.getMask().astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            cnt = contours[0]
            polygon = QPolygonF([QPointF(float(point[0][0])+min_col+0.5, float(point[0][1])+min_row+0.5) for point in cnt])
            
            pen = QPen(Qt.NoPen)
            brush = QBrush(color)
            newItem = self.activeviewer.scene.addPolygon(polygon, pen, brush)
            newItem.setZValue(10)  # Draw above most items
            self.colorizedEntities.append(newItem)

    def removeColorizedEntities(self):
        """Remove colorized shapes from the viewer"""
        if self.colorizedEntities:
            for item in self.colorizedEntities:
                self.activeviewer.scene.removeItem(item)
            self.colorizedEntities = []
