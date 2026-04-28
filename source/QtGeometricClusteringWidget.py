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

        # GROUP BOX for property selection
        propSelGroup = QGroupBox("Properties for Clustering")
        propSelGroup.setStyleSheet("""
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
                self.propCheckboxes[key] = cb
                colLayout.addWidget(cb)
            colLayout.addStretch()
            propSelLayout.addLayout(colLayout)

        propSelLayout.addStretch()
        propSelGroup.setLayout(propSelLayout)
        propSelGroup.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mainLayout.addWidget(propSelGroup)

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
        self.logSelectedRegions()
        self.computeProperties()

    def closeEvent(self, event):
        # Disconnect viewer signal so selection changes no longer trigger computation
        if hasattr(self.activeviewer, 'selectionChanged'):
            try:
                self.activeviewer.selectionChanged.disconnect(self.onSelectionChanged)
            except (TypeError, RuntimeError):
                pass
        # Remove highlight and colorized entities
        self.removeHighlight()
        self.removeColorizedEntities()
        # emit the signal to notify the main window
        self.closewidget.emit()
        super(QtGeometricClusteringWidget, self).closeEvent(event)

    @pyqtSlot()
    def onSelectionChanged(self):
        """Called when the selection changes in the viewer"""
        self.workingBlobs = self.activeviewer.selected_blobs[:]
        self.writeLog("Selection changed. Now {} region(s) selected.".format(len(self.workingBlobs)))
        # Reset clustering results
        self.geometricData = {}
        self.clusterLabels = None
        self.btnCluster.setEnabled(False)
        self.cbShowClusters.setEnabled(False)
        self.removeHighlight()
        self.removeColorizedEntities()
        # Clear stale table and plot
        self.resultsTable.clear()
        self.resultsTable.setRowCount(0)
        self.resultsTable.setColumnCount(0)
        self.figure.clear()
        self.canvas.draw()
        # Recompute properties for the new selection
        if len(self.workingBlobs) > 0:
            self.computeProperties()

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
            else:
                d['rectMaj'] = d['rectMin'] = d['rectAspect'] = d['rectOrient'] = 0.0

            # Convex Hull
            d['convexArea'] = region.area_convex * pxmm2

            self.geometricData[blob.id] = d

        self.writeLog("Properties computed for {} regions. Ready for clustering.".format(
            len(self.geometricData)))
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
        selected_props = [key for key, cb in self.propCheckboxes.items() if cb.isChecked()]

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
            # Region ID — store blob_id in UserRole for row lookup
            id_item = QTableWidgetItem(str(blob_id))
            id_item.setData(Qt.UserRole, blob_id)
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
        
        # Plot clusters first, then noise on top
        unique_labels = sorted(set(labels))
        # Draw clusters first so noise points are rendered on top
        for label in [l for l in unique_labels if l != -1]:
            color = self.getClusterColor(label)
            color_str = color.name()
            mask = labels == label
            ax.scatter(X_plot[mask, 0], X_plot[mask, 1],
                      c=[color_str], label=f'Cluster {label}',
                      s=50, alpha=0.7, edgecolors='white', linewidths=0.5, marker='o')

        # Draw noise points as unfilled circles
        if -1 in unique_labels:
            mask = labels == -1
            ax.scatter(X_plot[mask, 0], X_plot[mask, 1],
                      facecolors='none', edgecolors='gray', linewidths=1.2,
                      label='Noise', s=60, alpha=0.8, marker='o')
        
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
        
        # Store X_plot for scatter-highlight lookup
        self.clusterData['X_plot'] = X_plot

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
        X_plot = self.clusterData.get('X_plot') if self.clusterData else None
        blob_ids = self.clusterData.get('blob_ids') if self.clusterData else None
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
