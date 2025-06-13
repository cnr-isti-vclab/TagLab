import sys

import numpy as np
# import cv2
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QTextEdit, QLineEdit, QSlider, QMenu, QCheckBox, QMenuBar, QAction, QDialog
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush, QPolygonF
from PyQt5.QtCore import pyqtSignal, Qt, QBuffer, QPointF

from source.QtImageViewer import QtImageViewer
from source.QtExportRows import ExportDialog
from source import genutils

from skimage.transform import hough_line, hough_line_peaks
from skimage.morphology import skeletonize, thin

from skimage.graph import route_through_array
import networkx as nx

# from scipy.interpolate import interp1d
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt, convolve

# from skimage import measure, morphology, io, color
from skimage.draw import line
from scipy.spatial import KDTree

# import svgwrite
# from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QMessageBox
# from subprocess import check_call

# from itertools import combinations


TEXTBOX_H = 100
class RowsWidget(QWidget):

    closeRowsWidget = pyqtSignal()

    # def __init__(self, image_cropped, created_blobs, offset, parent=None):
    def __init__(self, cropped_image, mask_array, blobs, rect, parent = None, screen_size = None):    
        super(RowsWidget, self).__init__(parent)

        # self.q_skel = None

        # i = 0
        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        if screen_size is not None:   
            width = int(screen_size.width() * 0.9)
            height = int(screen_size.height()* 0.9)
            self.setMinimumSize(width, height)
            self.resize(width, height)
            self.IMAGEVIEWER_W = width//2 - 40
            self.IMAGEVIEWER_H = height - 400
        else:
            self.setMinimumWidth(1440)
            self.setMinimumHeight(900)   
            self.IMAGEVIEWER_W = 640
            self.IMAGEVIEWER_H = 480  

        self.setWindowTitle("Rows Analysis")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)

        self.parent_viewer = None
        if parent:
            self.parent_viewer = parent
            self.scale = self.parent_viewer.image.map_px_to_mm_factor
            # print(f"Scale is {self.scale}")
            self.blob_list = blobs
            rettangolo = self.parent_viewer.dragSelectionRect.rect()
            self.off = [rettangolo.x(), rettangolo.y()]
        
        self.image_cropped = cropped_image
        # self.image_mask = image_mask
        self.maschera = mask_array
        self.masch = None
        self.blob_image = None
        self.image_overlay = None
        self.skeleton = None
        self.thickness = None
        self.thickness_image = None
        self.thickness_data = []
        self.branch_points =  []
        self.edges = []

        self.rect = rect
        self.blob_list = blobs
        self.centroids = []
        self.bboxes = []        

        self.set_anglebox = False
        self.set_thickbox = False

        #create line viewer
        line_viewer_layout = QVBoxLayout()
        self.line_viewer = QtImageViewer()
        self.line_viewer.disableScrollBars()
        self.line_viewer.enablePan()
        self.line_viewer.enableZoom()
        self.line_viewer.setFixedWidth(self.IMAGEVIEWER_W)
        self.line_viewer.setFixedHeight(self.IMAGEVIEWER_H)
        self.line_viewer.setImg(self.image_cropped)

        # Enable context menu policy
        self.line_viewer.setContextMenuPolicy(Qt.CustomContextMenu)
        self.line_viewer.customContextMenuRequested.connect(self.showMaskLinesMenu)
        self.lines = []

        # Create checkable actions for the mask and lines
        self.actionShowMask = QAction("Show Mask", self)
        self.actionShowMask.setCheckable(False)
        self.actionShowMask.toggled.connect(self.toggleShowMask)
        self.mask_checked = False

        self.actionShowThickness = QAction("Show Thickness Map", self)
        self.actionShowThickness.setCheckable(False)
        self.actionShowThickness.toggled.connect(self.toggleShowThickness)
        self.thickness_checked = False

        self.actionShowBlobs = QAction("Show Blobs", self)
        self.actionShowBlobs.setCheckable(False)
        self.actionShowBlobs.toggled.connect(self.toggleShowBlobs)
        self.blobs_checked = False

        self.actionShowLines = QAction("Show Lines", self)
        self.actionShowLines.setCheckable(False)
        self.actionShowLines.toggled.connect(self.toggleShowLines)
        self.line_checked = False
        line_viewer_layout.addWidget(self.line_viewer, alignment=Qt.AlignTop)
        
        # line_viewer_layout.setSpacing(45)
        
        lineslopes_layout = QVBoxLayout()
        
        lineangle_label = QLabel(f"Data")
        
        self.angleTextBox = QTextEdit(self)
        self.angleTextBox.setReadOnly(True)
        self.angleTextBox.setFixedWidth(self.IMAGEVIEWER_W)
        self.angleTextBox.setFixedHeight(TEXTBOX_H)

        # Add export lines
        # self.btnLineExport = QPushButton("Export Line Data")
        # self.btnLineExport.clicked.connect(self.exportLineViewerData)

        lineslopes_layout.setSpacing(5)  # Reduce spacing to bring QLabel closer to QTextEdit

        lineslopes_layout.addWidget(lineangle_label, alignment=Qt.AlignBottom)
        lineslopes_layout.addWidget(self.angleTextBox, alignment=Qt.AlignTop)
        # lineslopes_layout.addWidget(self.btnLineExport, alignment=Qt.AlignTop)
        # lineslopes_layout.addWidget(self.btnLineExport, alignment=Qt.AlignTop)


        # line_viewer_layout.addLayout(lineslopes_layout)
        # line_viewer_layout.addWidget(lineangle_label, alignment=Qt.AlignTop)
        # line_viewer_layout.addWidget(self.angleTextBox, alignment=Qt.AlignTop)
        # line_viewer_layout.addWidget(self.btnLineExport, alignment=Qt.AlignBottom)
        

        # create skeleton viewer
        skel_viewer_layout = QVBoxLayout()
        self.skel_viewer = QtImageViewer()
        self.skel_viewer.disableScrollBars()
        self.skel_viewer.enablePan()
        self.skel_viewer.enableZoom()
        self.skel_viewer.setFixedWidth(self.IMAGEVIEWER_W)
        self.skel_viewer.setFixedHeight(self.IMAGEVIEWER_H)
        self.skel_viewer.setImg(self.image_cropped)

        #draw blobs
        # for blob in self.blob_list:
        #     self.parent_viewer.drawBlob(blob)

        # Enable context menu policy
        self.skel_viewer.setContextMenuPolicy(Qt.CustomContextMenu)
        self.skel_viewer.customContextMenuRequested.connect(self.showSkelMenu)

        # Create checkable actions for the mask and lines
        self.actionShowSkel = QAction("Show Skeleton", self)
        
        self.actionShowSkel.setCheckable(False)
        self.actionShowSkel.toggled.connect(self.toggleShowSkel)
        self.skel_checked = False

        self.actionShowBranch = QAction("Show Branch Points", self)
        
        self.actionShowBranch.setCheckable(False)
        self.actionShowBranch.toggled.connect(self.toggleShowBranch)
        self.branch_checked = False

        self.actionShowEdges = QAction("Show Edges", self)
        
        self.actionShowEdges.setCheckable(False)
        self.actionShowEdges.toggled.connect(self.toggleShowEdges)
        self.edges_checked = False

        skel_viewer_layout.addWidget(self.skel_viewer, alignment=Qt.AlignTop)

        skel_viewer_layout.setSpacing(15)
        
        
        brickdist_layout = QHBoxLayout()

        self.row_dist = 20
        brickdist_label = QLabel(f"Rows distance:")
        self.BrickDistBox = QLineEdit(self)
        self.BrickDistBox.setReadOnly(False)
        self.BrickDistBox.setFixedWidth(150)
        self.BrickDistBox.setFixedHeight(25)
        self.BrickDistBox.setText(str(self.row_dist))

        
        brickdist_layout.addWidget(brickdist_label, alignment=Qt.AlignCenter)
        brickdist_layout.addWidget(self.BrickDistBox, alignment=Qt.AlignLeft)
        brickdist_layout.setSpacing(2)
    
        # skelangle_layout = QVBoxLayout()
        # skelangle_label = QLabel(f"Slopes")
        # self.skelTextBox = QTextEdit(self)
        # self.skelTextBox.setReadOnly(True)
        # self.skelTextBox.setFixedWidth(self.IMAGEVIEWER_W)
        # self.skelTextBox.setFixedHeight(TEXTBOX_H)
        # layout.addWidget(self.angleTextBox)
        # Add export lines
        # self.btnSkelExport = QPushButton("Export Skeleton Data")
        # self.btnSkelExport.clicked.connect(self.exportSkelViewerData)
        # skel_viewer_layout.addWidget(self.btnSkelExport, alignment=Qt.AlignTop)
        # skelangle_layout.setSpacing(5)  # Reduce spacing to bring QLabel closer to QTextEdit
        # skel_viewer_layout.addWidget(self.btnSkelExport, alignment=Qt.AlignBottom)

        
        # skelangle_layout.addWidget(skelangle_label, alignment=Qt.AlignBottom)
        # skelangle_layout.addWidget(self.skelTextBox, alignment=Qt.AlignTop)
        # skelangle_layout.addWidget(self.btnSkelExport, alignment=Qt.AlignTop)

        # skel_viewer_layout.addLayout(skelangle_layout)

        # skel_viewer_layout.setSpacing(5)

        # Create a horizontal layout for the viewers
        viewers_layout = QHBoxLayout()
        
        # Add line_viewer to viewers layout
        # viewers_layout.addWidget(self.line_viewer, alignment=Qt.AlignLeft)
        viewers_layout.addLayout(line_viewer_layout)
        
        viewers_layout.setSpacing(10)
        
        # Add skeleton viewer to viewers layout
        # viewers_layout.addWidget(self.skel_viewer, alignment=Qt.AlignTop)
        viewers_layout.addLayout(skel_viewer_layout)
        # Add the viewers to the main layout
        
        # viewers_layout.setSpacing(10)

        # Add the viewers layout to the main layout
        # layout.addLayout(viewers_layout)
        # layout.addLayout(layoutTop)
        # layout.addWidget(self.progress_bar)
        # layout.addWidget(self.viewer, alignment=Qt.AlignCenter)
        # layout.addLayout(layoutButtons)

        textbox_layout = QHBoxLayout()
        # Add line slopes and rows distance widgets to the layout
        textbox_layout.addLayout(lineslopes_layout)
        textbox_layout.setSpacing(10)
        textbox_layout.addLayout(brickdist_layout)   

        # self.angleTextBox = QTextEdit(self)
        # self.angleTextBox.setReadOnly(True)
        # layout.addWidget(self.angleTextBox)

        # self.setLayout(layout)

        # layout.addWidget(self.btnExport)#, alignment=Qt.AlignCenter)

        # Add slider for structuring element size
        slider_layout = QVBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(50)
        self.slider.setValue(21)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.updateStructuringElement)
        self.slider.setFixedHeight(30)

        value = self.slider.value()

        if self.scale:
            self.slider_label = QLabel(f"Joint Thickness (mm): {((value-1)//2) * float(self.scale)}")
        else:
            self.slider_label = QLabel(f"Joint Thickness (px): {((value-1)//2)}")
        

        self.slider_label.setFixedHeight(30)
        
        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.slider)

        self.structuring_element_size = self.slider.value()

        # buttons for data processing
        data_button_layout = QHBoxLayout()
        self.btnCompute = QPushButton("Compute")
        self.btnCompute.clicked.connect(self.computeRows)
        data_button_layout.setAlignment(Qt.AlignLeft)
        data_button_layout.addWidget(self.btnCompute)
        data_button_layout.addStretch()

        #buttons for output
        output_button_layout = QHBoxLayout()
        self.btnBlob = QPushButton("Add mask as region to project")
        self.btnBlob.clicked.connect(self.addMaskToProject)
        self.btnBlob.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btnBlob.setEnabled(False)
        self.btnBlob.setToolTip("Add the mask as a region to the project, so it can be used in other analyses.")
        self.btnExport = QPushButton("Export Data")
        self.btnExport.clicked.connect(self.exportData)
        self.btnExport.setEnabled(False)
        output_button_layout.addWidget(self.btnBlob)
        output_button_layout.addWidget(self.btnExport)
        output_button_layout.setAlignment(Qt.AlignLeft)

        # separator line for visual separation
        separator = QLabel()
        separator.setFixedHeight(3)
        separator.setStyleSheet("background-color: #666; margin-top: 10px; margin-bottom: 10px;")

        # bottom row buttons
        bottom_layout = QHBoxLayout()
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.closeWidget)
        bottom_layout.setAlignment(Qt.AlignRight)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btnClose)

        ##########################################################################################################################
        #Create the full window layout and assemble the widgets
        layout = QVBoxLayout()

        layout.setSpacing(10)
        # Add the viewers layout to the main layout
        layout.addLayout(viewers_layout) 
        layout.addLayout(textbox_layout, stretch=1)    
        layout.addLayout(slider_layout)
        layout.setSpacing(10)
        # Add the button rows
        layout.addLayout(data_button_layout)
        layout.addLayout(output_button_layout)
        # separator line
        layout.addWidget(separator)
        # Add the bottom layout with the close button
        layout.addLayout(bottom_layout)

        # self.line_viewer.setImg(self.image_cropped)
        # self.skel_viewer.setImg(self.image_cropped)

        self.setLayout(layout)    
    
    def updateStructuringElement(self, value):
        self.structuring_element_size = value
        if self.scale:
            self.slider_label.setText(f"Joint Thickness (mm): {((value-1)//2) * float(self.scale)}")
        else:
            self.slider_label.setText(f"Joint Thickness (px): {((value-1)//2)}")
            
    def computeRows(self):
        if self.set_anglebox == True or self.set_thickbox == True:
            self.resetAngleTextBox()

        # enable export buttons
        self.btnBlob.setEnabled(True)
        self.btnExport.setEnabled(True)

        _, self.masch = self.maskGrow(self.maschera, self.structuring_element_size)
        # self.houghTansformation(final_mask)
        self.lines = self.houghTansformation(self.masch)

        # i += 1
        self.skeleton = self.applySkeletonization(self.masch)

        self.thickness_image = self.thicknessMap(self.masch)

        self.actionShowLines.setCheckable(True)
        self.actionShowMask.setCheckable(True)
        self.actionShowThickness.setCheckable(True)
        self.actionShowBlobs.setCheckable(True)

        self.line_checked = True
        self.actionShowLines.setChecked(True)
        self.mask_checked = True
        self.actionShowMask.setChecked(True)
        
        self.toggleMaskLines(self.line_checked, self.mask_checked, self.thickness_checked, self.blobs_checked)
        self.toggleShowLines(self.line_checked)
        self.toggleShowMask(self.mask_checked)
        
        # Get row_distance from  BrickDistBox
        try:
            self.row_dist = int(self.BrickDistBox.text())
        except ValueError:
            self.row_dist = 20

        self.branch_points, self.edges = self.vectorBranchPoints(self.skeleton)

        # self.connectBranchPoints(self.branch_points, brick_width, brick_dist)
        # print(self.branch_points)
        self.actionShowSkel.setCheckable(True)

        if self.edges_checked == False:
            self.actionShowSkel.setChecked(True)
        else:
            self.actionShowSkel.setChecked(False)

        self.actionShowBranch.setCheckable(True)
        self.actionShowBranch.setChecked(True)
        self.actionShowEdges.setCheckable(True)
        # self.actionShowBranch.setChecked(True)
        branch_image = self.drawBranchSkel(self.skeleton, self.branch_points, self.edges, self.branch_checked, self.skel_checked, self.edges_checked)
        self.skel_viewer.setOpacity(1.0)
        self.skel_viewer.setOverlayImage(branch_image)

    
    def closeWidget(self):
        self.closeRowsWidget.emit()
        self.close()

    def maskGrow(self, mask, value):
        #GROW DEI BLOB, LA MALTA È QUELLA CHE DISTA x PIXEL DAL BLOB
        rect_mask_grow = mask.copy()

        # Create a structuring element that defines the neighborhood
        # 21x21 to cover 10 positions around each 1 (10 positions
        structuring_element = np.ones((value, value), dtype=np.uint8)
        structuring_element_half = np.ones((value//2, value//2), dtype=np.uint8)
        print(f"Structuring element size: {value}")
        rect_mask_grow = binary_dilation(mask, structure=structuring_element)
        rect_mask_grow_sub = rect_mask_grow - mask

        # rect_mask_grow = rect_mask_grow - mask

        # Save the rect_mask_grow as a matplotlib figure
        # plt.figure(figsize=(10, 10))
        # plt.imshow(rect_mask_grow_sub, cmap='gray')
        # plt.axis('off')
        # plt.savefig("rect_mask_grow.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        rect_mask_eroded = binary_erosion(rect_mask_grow, structure=structuring_element_half)

        # Save the rect_mask_eroded as a matplotlib figure
        # plt.figure(figsize=(10, 10))
        # plt.imshow(rect_mask_eroded, cmap='gray')
        # plt.axis('off')
        # plt.savefig("rect_mask_eroded.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        rect_mask_final = rect_mask_eroded - mask

        # Save the rect_mask_eroded as a matplotlib figure
        # plt.figure(figsize=(10, 10))
        # plt.imshow(rect_mask_final, cmap='gray')
        # plt.axis('off')
        # plt.savefig("rect_mask_final.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        return rect_mask_grow_sub, rect_mask_final
    
    def updateAngleTextBox(self, angles, index, color='red'):
        current_text = self.angleTextBox.toHtml()
        new_text = ''.join([f'<div style="color: {color};">line {str(index+1)}: {angle}</div>' for angle in angles])
        self.angleTextBox.setHtml(current_text + new_text)
    
    def resetAngleTextBox(self):
        self.angleTextBox.clear()
        self.set_anglebox = False
        self.set_thickbox = False

    # def updateSkelTextBox(self, angles, index, color='red'):
    #     current_text = self.skelTextBox.toHtml()
    #     new_text = ''.join([f'<span style="color: {color};">line {str(index+1)}: {angle}</span><br>' for angle in angles])
    #     self.skelTextBox.setHtml(current_text + new_text)

    # def resetSkelTextBox(self):
    #     self.skelTextBox.clear()
        # self.set_textbox = False

    def boundary_clamp(self, mask, x0, y0, x1, y1):
        
        #Find the range of the line ((x0, y0), (x1, y1)) clamped to the mask.
        height, width = mask.shape

        # Generate points along the line (using Bresenham's or linear interpolation)
        num_points = max(abs(x1 - x0), abs(y1 - y0))  # Ensure enough points
        x_values = np.linspace(x0, x1, num_points).astype(int)
        y_values = np.linspace(y0, y1, num_points).astype(int)
        
        # Clamp points within the image bounds
        valid_indices = (x_values >= 0) & (x_values < width) & (y_values >= 0) & (y_values < height)
        x_values, y_values = x_values[valid_indices], y_values[valid_indices]
        
        # Check mask values along the line
        mask_values = mask[y_values, x_values]
        non_zero_indices = np.where(mask_values > 0)[0]
        
        if len(non_zero_indices) > 0:
            # Get start and end of the non-zero segment
            start_idx = non_zero_indices[0]
            end_idx = non_zero_indices[-1]
            return (x_values[start_idx], y_values[start_idx]), (x_values[end_idx], y_values[end_idx])
        else:
            # Line does not intersect the non-zero mask area
            return None
    
    def houghTansformation(self, mask):
        # Apply the Hough Line Transformation
        h, theta, d = hough_line(mask)

        # Visualize the Hough Transform accumulator
        # plt.figure(figsize=(10, 6))
        # plt.imshow(np.log(1 + h), extent=[np.rad2deg(theta[0]), np.rad2deg(theta[-1]), d[-1], d[0]],
        #         cmap='hot', aspect=1.5)
        # plt.title('Hough Transform Accumulator')
        # plt.xlabel('Theta (degrees)')
        # plt.ylabel('Rho (pixels)')
        # plt.colorbar(label='Votes')
        # # plt.show()
        # plt.savefig("hough_transf.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        # Extract peaks from the accumulator
        lines = []
        height, width = mask.shape

        for _, angle, dist in zip(*hough_line_peaks(h, theta, d)):
            # Calculate line endpoints
            try:
                # Points for the line at the left and right image boundaries
                y0 = (dist - 0 * np.cos(angle)) / np.sin(angle)  # y-intercept at x=0
                y1 = (dist - width * np.cos(angle)) / np.sin(angle)  # y-intercept at x=width

                # Check for valid values within the image bounds
                if np.isfinite(y0) and np.isfinite(y1):  # Ensure values are not infinite
                    x0, x1 = 0, width
                    if y0 < 0 or y1 < 0:
                        pass
                    else:
                        point1, point2 = self.boundary_clamp(mask, int(x0), int(y0), int(x1), int(y1))
                        # print(point1, point2)
                        if point1 and point2:
                            lines.append((point1, point2, angle))

                    # if 0 <= y0 < height and 0 <= y1 < height:  # Clamp to image bounds
                    #     lines.append(((0, int(y0)), (width, int(y1)), angle))

            except ZeroDivisionError:
                # Handle cases where sin(angle) is zero (e.g., vertical lines)
                continue

        # print(f"Detected\n \
        #       {lines}")

        # Check for intersections
        lines_ints = lines.copy()
        intersections = []
        intersection_points = []

        for i, line1 in enumerate(lines_ints):
            for j, line2 in enumerate(lines_ints):
                if i >= j:
                    continue
                if self.do_lines_intersect(line1, line2):
                    intersection = self.point_intersection(line1, line2)
                    intersections.append((line1, line2, intersection))
                    # if intersection:
                        # intersections.append((line1, line2))
                    # print(intersections)
                    intersection_points.append(intersection)
                    # print(f"Intersection at: {intersection}")

        # Visualize lines and intersections on the original mask
        # plt.figure(figsize=(8, 8))
        # plt.imshow(mask, cmap='gray')
        # plt.axis('off')

        # for ((x0, y0), (x1, y1), ang) in lines:
        #     plt.plot((x0, x1), (y0, y1), color='b')  # Plot detected lines in red

        # for (px, py) in intersection_points:
        #     plt.plot(px, py, 'ro')  # Plot intersections as red dots

        # plt.title('Detected Lines and Intersections')
        # plt.savefig("hough_lines_with_intersections.png", bbox_inches='tight', pad_inches=0)
        # # plt.show()
        # plt.close()

        # Remove lines that are part of intersections from lines_ints
        for line1, line2, _ in intersections:
            if line1 in lines_ints:
                lines_ints.remove(line1)
            if line2 in lines_ints:
                lines_ints.remove(line2)

        # Remove duplicate lines from intersections
        unique_intersections = []
        seen_lines = set()

        for line1, line2, intersection in intersections:
            if line1 not in seen_lines and line2 not in seen_lines:
                unique_intersections.append((line1, line2, intersection))
                seen_lines.add(line1)
                seen_lines.add(line2)

        intersections = unique_intersections
        
        # print(f"Intersections list: {intersections}")        
        intersections_cut = []
        # plt.figure(figsize=(8, 8))
        # plt.imshow(mask, cmap='gray')
        # plt.axis('off')        
        
        for (line1, line2, (ix, iy)) in intersections:
            (x1, y1), (x2, y2), ang1 = line1
            (x3, y3), (x4, y4), ang2 = line2

            # Plot the first line up to the intersection point
            plt.plot((x1, ix), (y1, iy), color='b')
            # plt.plot((ix, x2), (iy, y2), color='g')

            # Plot the second line from to the intersection point
            # plt.plot((x3, ix), (y3, iy), color='g')
            plt.plot((ix, x4), (iy, y4), color='g')
            intersections_cut.append(((x1, y1), (int(ix), int(iy)), ang1))
            intersections_cut.append(((int(ix), int(iy)), (x2, y2), ang2))

            # Plot the intersection point
            plt.plot(ix, iy, 'ro')

        # Draw lines between two intersection points
        for (line1, line2, (ix, iy)) in intersections:
            for (line3, line4, (jx, jy)) in intersections:
                # if line4 not in inter_intersections:
                if line1 == line3 or line2 == line4:
                    plt.plot((ix, jx), (iy, jy), color='yellow')  # Plot line between intersections in yellow
                    # print(f"line3 and line4 are {line3} and {line4}")
                    # inter_intersections.append((jx,jy))

        for line in lines_ints:
            # print(line)
            (x0, y0), (x1, y1), _ = line
            plt.plot((x0, x1), (y0, y1), color='r')

        # plt.title('Detected Lines and Intersections')
        # plt.savefig("spezzate_with_intersections.png", bbox_inches='tight', pad_inches=0)
        plt.close()
       
        # # Remove intersectin lines with smaller angles
        # for line1, line2 in intersections:
        #     if line1[2] < line2[2]:  # Compare angles
        #         if line1 in lines:
        #             lines.remove(line1)
        #     else:
        #         if line2 in lines:
        #             lines.remove(line2)

        lines_with_color = []
        for line in lines_ints:
            color = tuple(np.random.randint(0, 256, 3))
            line_with_color = (*line, color)
            lines_with_color.append(line_with_color)

        # intersections_with_color = []
        # for line1, line2, _ in intersections:
        #     color1 = tuple(np.random.randint(0, 256, 3))
        #     color2 = tuple(np.random.randint(0, 256, 3))
        #     line1_with_color = (*line1, color1)
        #     line2_with_color = (*line2, color2)
        #     lines_with_color.append(line1_with_color)
        #     lines_with_color.append(line2_with_color)

        for line in intersections_cut:
            color = tuple(np.random.randint(0, 256, 3))
            line_with_color = (*line, color)
            lines_with_color.append(line_with_color)

        sorted_lines_with_color = sorted(lines_with_color, key=lambda entry: entry[0][1])
        
        return sorted_lines_with_color
    
    def ccw(self, A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    
    # Function to check if two line segments intersect
    def do_lines_intersect(self, line1, line2):
        A, B, _ = line1
        C, D, _ = line2
        A, B, _ = line1
        C, D, _ = line2
        return self.ccw(A, C, D) != self.ccw(B, C, D) and self.ccw(A, B, C) != self.ccw(A, B, D)
    
    # Function to calculate the intersection point of two line segments
    def point_intersection(self,line1, line2):
        (x1, y1), (x2, y2), _ = line1
        (x3, y3), (x4, y4), _ = line2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return None

        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom

        return px, py

####################################################################################################################

    def applySkeletonization(self, mask):
        # Apply skeletonization
        skeleton = skeletonize(mask)
        # skeleton = median(skeleton, disk(1))
        # skeleton = thin(mask)
        
        # h, w = skeleton.shape
        # dwg = svgwrite.Drawing(f"skeleton.svg", size=(w, h))
        
        # # Draw skeleton as black lines
        # y, x = np.where(skeleton)
        # for i in range(len(y)):
        #     dwg.add(dwg.circle(center=(int(x[i]), int(y[i])), r=0.5, fill="black"))

        # # Save SVG file
        # dwg.save()
        # print("Saved skeleton as skeleton.svg")

        # Visualize the skeleton
        # plt.figure(figsize=(8,8))
        # plt.imshow(skeleton, cmap='gray')
        # plt.title('Skeletonized Mask')
        # plt.savefig("skeletonized_mask.png", bbox_inches='tight', pad_inches=0)
        # plt.close()
        return skeleton

    def thicknessMap(self, mask):

        # Method to get a thickness map from mask
        dist = distance_transform_edt(mask)
        
        # plt.figure(figsize=(10, 5))
        # # plt.subplot(1, 2, 2)
        # plt.title("Distance Transform")
        # plt.imshow(dist, cmap='viridis')
        # plt.colorbar()
        # plt.savefig("dist.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        thickness = dist * 2

        thickness_nonzero = thickness[mask > 0]
        mean_thickness = np.mean(thickness_nonzero)
        max_thickness = np.max(thickness_nonzero)
        min_thickness = np.min(thickness_nonzero)
        self.thickness_data = [mean_thickness, max_thickness, min_thickness]

        # mean_thickness = np.mean(thickness)
        # print(f"Mean thickness along skeleton: {mean_thickness:.2f} pixels")
        

        if thickness.max() > 0:
            norm = thickness / thickness.max()
            norm = np.power(norm, 0.5)
        else:
            norm = (thickness * 0)

        # Create QImage from numpy array
        h, w = thickness.shape
        thickness_img = QImage(w, h, QImage.Format_RGB32)

        cmap = cm.get_cmap('viridis')

        for y in range(h):
            for x in range(w):
                if mask[y, x]:
                    v = norm[y, x]
                    
                    # Colormap with green gradient (very flat)
                    # r = 0
                    # g = int(255 - 255 * v)
                    # g = max(0, min(255, g))
                    # b = 0

                    # Colormap with viridis gradient of matplotlib
                    r_f, g_f, b_f, _ = cmap(v)
                    r = int(r_f * 255)
                    g = int(g_f * 255)
                    b = int(b_f * 255)
                    thickness_img.setPixelColor(x, y, QColor(r, g, b))
                else:
                    thickness_img.setPixelColor(x, y, QColor(0, 0, 0))  # black background
        
        # # Colormap in grayscale
        # if thickness.max() > 0:
        #     thickness_norm = (thickness / thickness.max() * 255).astype(np.uint8)
        # else:
        #     thickness_norm = (thickness * 0).astype(np.uint8)

        # # Create QImage from numpy array
        # h, w = thickness_norm.shape
        # thickness_img = QImage(thickness_norm.data, w, h, w, QImage.Format_Grayscale8).copy()

        # thickness_img.save("thickness_image.png", "PNG")

        return thickness_img
    
    def updateThicknessTextBox(self, thickness_data, color='white'):
        
        #Update the angleTextBox with thickness statistics.

        if self.scale:
            thickness_data = [
                value * float(self.scale) for value in thickness_data
            ]
            unit = "mm"
        else:
            unit = "px"


        mean_thickness, max_thickness, min_thickness = thickness_data

        # print(f"Mean thickness: {mean_thickness:.2f} {unit}")
        # print(f"Max thickness: {max_thickness:.2f} {unit}")
        # print(f"Min thickness: {min_thickness:.2f} {unit}")

        text = (
            f'<div style="color: {color};">'
            f"<b>Thickness Statistics:</b><br>"
            f"Mean: {mean_thickness:.2f} {unit}<br>"
            f"Max: {max_thickness:.2f} {unit}<br>"
            f"Min: {min_thickness:.2f} {unit}<br>"
            f"</div>"
        )
        current_text = self.angleTextBox.toHtml()
        self.angleTextBox.setHtml(current_text + text)

    def vectorBranchPoints(self,skeleton):

        # Extract skeleton pixels
        y, x = np.where(skeleton)
        coords = list(zip(y, x))

        # Create graph
        G = nx.Graph()
        neighbor_offsets = [(-1, -1), (-1, 0), (-1, 1),
                            ( 0, -1),          ( 0, 1),
                            ( 1, -1), ( 1, 0), ( 1, 1)]

        skeleton_set = set(coords)  # for fast lookup

        for y0, x0 in coords:
            for dy, dx in neighbor_offsets:
                neighbor = (y0 + dy, x0 + dx)
                if neighbor in skeleton_set:
                    G.add_edge((x0, y0), (neighbor[1], neighbor[0]))  # note: (x, y) order

        # Branch points: nodes with degree > 2
        branch_points = [node for node in G.nodes if G.degree(node) > 2]

        # Optional: Visualize
        # plt.imshow(skeleton, cmap='gray')
        # for x, y in branch_points:
        #     plt.plot(x, y, 'ro', markersize=3)
        # plt.title('Branch Points')
        # plt.savefig("arara.png", bbox_inches='tight', pad_inches=0)
        # # plt.show()
        # plt.close()
        
        # Plot skeleton
        # plt.figure(figsize=(8, 8))
        # plt.imshow(skeleton, cmap='gray')

        # Plot edges (lines between connected nodes)
        # for (x1, y1), (x2, y2) in G.edges:
        #     plt.plot([x1, x2], [y1, y2], color='blue', linewidth=0.5)

        # Plot branch points
        # for x, y in branch_points:
        #     plt.plot(x, y, 'ro', markersize=3)

        # for i, (x1, y1) in enumerate(branch_points):
        #     for j in range(i+1, len(branch_points)):
        #         x2, y2 = branch_points[j]
        #         plt.plot([x1, x2], [y1, y2], color='green', linestyle='--', linewidth=0.5)

        # plt.title('Skeleton with Edges and Branch Points')
        # plt.axis('off')
        # plt.savefig("arara.png", bbox_inches='tight', pad_inches=0)
        # # plt.show()
        # plt.close()

        
        visited_edges = set()
        segments = []

        for bp in branch_points:
            for neighbor in G.neighbors(bp):
                edge = tuple(sorted([bp, neighbor]))
                if edge in visited_edges:
                    continue

                path = [bp, neighbor]
                current = neighbor
                prev = bp

                while True:
                    visited_edges.add(tuple(sorted([prev, current])))
                    neighbors = [n for n in G.neighbors(current) if n != prev]

                    if len(neighbors) != 1 or current in branch_points:
                        # We hit another branch point or an endpoint
                        break

                    next_node = neighbors[0]
                    path.append(next_node)
                    prev, current = current, next_node

                # Only add if it ends at another branch or endpoint
                if current in branch_points or G.degree[current] == 1:
                    color = tuple(np.random.randint(0, 256, 3))  # Generate a random RGB color
                    dx = path[-1][0] - path[0][0]
                    dy = path[-1][1] - path[0][1]
                    dist = np.hypot(dx, dy)
                    angle = np.arctan2(dy, dx)  # Angle in radians
                    angle_deg = np.degrees(angle)  # Convert to degrees
                    segments.append((path[0], path[-1], color, angle_deg, dist))
                    # segments.append((path[0], path[-1]))

        # # Plot the skeleton
        # plt.figure(figsize=(8, 8))
        # # plt.imshow(skeleton, cmap='gray')

        # # Plot segments between branch points, recreates the skeleton in another way
        # # for segment in segments:
        # #     x_vals, y_vals = zip(*segment)
        # #     color = tuple(np.random.rand(3))  # Generate a random RGB color
        # #     plt.plot(x_vals, y_vals, color=color, linewidth=2)

        # # Plot polylines between branch points, that is connected nodes
        # for start, end, color in segments:
        #     x_vals = [start[0], end[0]]
        #     y_vals = [start[1], end[1]]
        #     # color = tuple(np.random.rand(3))  # Generate a random RGB color
        #     plt.plot(x_vals, y_vals, color=color, linewidth=2)

        # # Plot branch points
        # for x, y in branch_points:
        #     plt.plot(x, y, 'ro', markersize=3)

        # plt.title('Directly Connected Branch Points')
        # plt.axis('off')
        # # plt.show()
        # plt.savefig("wawawa.png", bbox_inches='tight', pad_inches=0)
        # plt.close()
        
        # angle = 90
        # filtered_segments = []
        # y_threshold = 25  # Adjust this threshold as needed 
        # # Plot only segments that are nearly horizontal (same Y level)
        # for start, end in segments:
        #     y1, y2 = start[1], end[1]  # Remember: start = (x, y)

        #     if abs(y1 - y2) <= y_threshold:
        #         x_vals = [start[0], end[0]]
        #         y_vals = [start[1], end[1]]
                
        #         dx = end[0] - start[0]
        #         dy = end[1] - start[1]
        #         # angle_deg = np.degrees(np.arctan(dy, dx))
                
                
        #         color = tuple(np.random.rand(3))  # Random RGB color
        #         # filtered_segments.append((start, end))
        #         plt.plot(x_vals, y_vals, color=color, linewidth=2)

        # # Optionally, still show branch points
        # for x, y in branch_points:
        #     plt.plot(x, y, 'ro', markersize=3)

        # plt.title(f'Segments with Δy ≤ {y_threshold}')
        # plt.axis('off')
        # plt.savefig("horizontal_segments.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        # Convert branch points to (y, x) format
        branch_points = [(y, x) for x, y in branch_points]

        return branch_points, segments
        
    
    #####MASK-LINES METHODS#####
    
    def paintLinesImage(self, image, lines):
        painter = QPainter(image)
        pen = QPen(Qt.red, 5)

        # with QPainter(image) as painter:
        for i, ((x0, y0), (x1, y1), angle, color) in enumerate(lines):
            # color = colors.pop(0)          
            pen.setColor(QColor(color[0], color[1], color[2]))
            painter.setPen(pen)
            painter.drawLine(x0, y0, x1, y1)

            # Draw angle value at the midpoint of the line
            mid_x = int((x0 + x1) / 2)
            mid_y = int((y0 + y1) / 2) - 10  # Slightly above the line

            # Convert angle to degrees and format
            if angle < 0:
                angle_disp = np.pi/2 + angle
            else:
                angle_disp = angle - np.pi/2
            angle_deg = np.rad2deg(angle_disp)
            angle_text = f"{angle_deg:.2f}°"

            painter.drawText(mid_x, mid_y, angle_text)

        painter.end()

        # Save the image with lines
        # image.save("image.png")

        #Set the mask with lines as image overlay
        # self.image_overlay = image
        return image
    
    def drawBlobs(self, blob_image, blobs):
            if blob_image is None:
                print("No image loaded in the viewer.")
                return
            
            if not blobs:
                print("No blobs to display.")
                return

            # Use QPainter to draw blobs
            painter = QPainter(blob_image)
            # pen = QPen(QColor(255, 0, 0), 2)  # Red color with a width of 2
            # painter.setPen(pen)

            for  blob in blobs:
                # set the color for the contour same of the blob 
                label_color = self.parent_viewer.project.classBrushFromName(blob).color()  
                pen = QPen(label_color, 4)  # Use the label color for the contour
                painter.setPen(pen)
                
                cx, cy = blob.centroid
                # print(f" centroid is {blob.centroid}")

                mapped_centroid = [cx - self.off[0], cy - self.off[1]]
                # print(f"mapped centroid is {mapped_centroid}")

                # Draw the centroid on the image
                painter.setBrush(QBrush(QColor(0, 0, 255)))  # Blue color for the centroid
                painter.drawEllipse(int(mapped_centroid[0]) - 5, int(mapped_centroid[1]) - 5, 10, 10)  # Circle with radius 5
                
                painter.setBrush(Qt.NoBrush)  # No fill
                
                # x, y, width, height = blob.bbox  # blob boundingbox 
                # print(f"original is {blob.bbox}")
                # mapped = [int(x - self.off[1]), int(y - self.off[0])] 
                # print(f"mapped is {mapped}")
                # painter.drawRect(mapped[1], mapped[0], width, height)

                # Draw the perimeter (contour)
                contour = blob.contour
                if contour is not None and len(contour) > 1:
                    # Map the contour points to the viewer's coordinate system
                    mapped_contour = [
                        QPointF(point[0] - self.off[0], point[1] - self.off[1]) for point in contour
                    ]

                    # Create a QPolygonF from the mapped contour
                    polygon = QPolygonF(mapped_contour)

                    # Draw the perimeter                
                    painter.drawPolygon(polygon)


            painter.end()

            # Save the blob_image to a file
            # blob_image.save("blob_image.png")

            # Update the viewer with the new image
            # self.line_viewer.setOverlayImage(overlay_image)
            return blob_image

    def showMaskLinesMenu(self, position):
            menu = QMenu(self)
            menu.addAction(self.actionShowMask)
            menu.addAction(self.actionShowThickness)
            menu.addAction(self.actionShowBlobs)
            
            # Add a separator line between actions in the context menu
            self.actionSeparator = QAction(self)
            self.actionSeparator.setSeparator(True)
            menu.addAction(self.actionSeparator)
            
            menu.addAction(self.actionShowLines)

            menu.exec_(self.line_viewer.mapToGlobal(position))

    def toggleShowMask(self, checked):
        if checked:
            self.mask_checked = True
            self.blobs_checked = False
            self.thickness_checked = False
            self.actionShowBlobs.setChecked(False)
            self.actionShowThickness.setChecked(False)
        else:
            self.mask_checked = False
        
        self.toggleMaskLines(self.line_checked, self.mask_checked, self.thickness_checked, self.blobs_checked)

    def toggleShowThickness(self, checked):
        if checked:
            self.thickness_checked = True
            self.mask_checked = False
            self.blobs_checked = False
            self.actionShowMask.setChecked(False)
            self.actionShowBlobs.setChecked(False)

            self.updateThicknessTextBox(self.thickness_data, color='white')
            self.set_thickbox = True

        else:
            self.thickness_checked = False
            # self.resetAngleTextBox()
            self.set_thickbox = False
        
        if self.set_thickbox == False and self.set_anglebox == True:
            self.resetAngleTextBox()
            self.angleTextBox.setHtml('<div style="color: white;"><b>Slopes:</b></div>')
            for i, (_, _, ang, color) in enumerate(self.lines):
            # for i, (_, _,ang, color) in enumerate(sorted_lines_with_color):            
                if ang < 0:
                    ang = np.pi/2 + ang  
                else:
                    ang = ang - np.pi/2

                ang_deg = np.rad2deg(ang)
                # ang = round(ang, 4)
                ang_deg = round(ang_deg, 4)

                self.updateAngleTextBox([ang_deg], i, color=f'rgb({color[0]},{color[1]},{color[2]})')
        elif self.set_anglebox == False and self.set_thickbox == False:
            self.resetAngleTextBox()
        self.toggleMaskLines(self.line_checked, self.mask_checked, self.thickness_checked, self.blobs_checked)
    
    def toggleShowBlobs(self, checked):
        if checked:
            self.blobs_checked = True
            self.mask_checked = False
            self.actionShowMask.setChecked(False)
            self.actionShowThickness.setChecked(False)
        else:
            self.blobs_checked = False
        
        self.toggleMaskLines(self.line_checked, self.mask_checked, self.thickness_checked, self.blobs_checked)

    def toggleShowLines(self, checked):
        if checked:
            self.line_checked = True

            if self.set_anglebox == False:
                self.angleTextBox.setHtml('<div style="color: white;"><b>Slopes:</b></div>')
                for i, (_, _, ang, color) in enumerate(self.lines):
                # for i, (_, _,ang, color) in enumerate(sorted_lines_with_color):            
                    if ang < 0:
                        ang = np.pi/2 + ang  
                    else:
                        ang = ang - np.pi/2

                    ang_deg = np.rad2deg(ang)
                    # ang = round(ang, 4)
                    ang_deg = round(ang_deg, 4)

                    self.updateAngleTextBox([ang_deg], i, color=f'rgb({color[0]},{color[1]},{color[2]})')
                    self.set_anglebox = True
        else:
            self.line_checked = False
            # self.resetAngleTextBox()
            self.set_anglebox = False

        if self.set_anglebox == False and self.set_thickbox == True:
            self.resetAngleTextBox()
            self.updateThicknessTextBox(self.thickness_data, color='white')
        elif self.set_anglebox == False and self.set_thickbox == False:
            self.resetAngleTextBox()
            
            
        
        self.toggleMaskLines(self.line_checked, self.mask_checked, self.thickness_checked, self.blobs_checked)

    def toggleMaskLines(self, line_checked, mask_checked, thickness_checked, blobs_checked):
        if line_checked  == True and mask_checked == True:
            qmask = genutils.maskToQImage(self.masch)
            mask_with_lines = self.paintLinesImage(qmask, self.lines)

            self.line_viewer.setOpacity(0.7)
            self.line_viewer.setOverlayImage(mask_with_lines)

        elif line_checked == True and blobs_checked == True: 
            # image = self.image_cropped.copy()
            image = QImage(self.image_cropped.size(), QImage.Format_ARGB32)
            image.fill(Qt.transparent)
            image_with_lines = self.paintLinesImage(image, self.lines)

            self.blob_image = self.drawBlobs(image_with_lines, self.blob_list)

            self.line_viewer.setOpacity(0.9)
            self.line_viewer.setOverlayImage(self.blob_image)

        elif line_checked == True and thickness_checked == True:
            image = self.thickness_image.copy() 
            image = image.convertToFormat(QImage.Format_ARGB32)
            image_with_lines = self.paintLinesImage(image, self.lines)
            self.line_viewer.setOpacity(0.7)
            self.line_viewer.setOverlayImage(image_with_lines)

        elif line_checked == True and mask_checked == False and thickness_checked == False and blobs_checked == False:
            # image = self.image_cropped.copy()
            image = QImage(self.image_cropped.size(), QImage.Format_ARGB32)
            image.fill(Qt.transparent)
            image_with_lines = self.paintLinesImage(image, self.lines)

            self.line_viewer.setOpacity(0.7)
            self.line_viewer.setOverlayImage(image_with_lines)
        
        elif line_checked == False and mask_checked == True:
            qmask = genutils.maskToQImage(self.masch)
            
            self.line_viewer.setOpacity(0.7)
            self.line_viewer.setOverlayImage(qmask)
        
        elif line_checked == False and thickness_checked == True:
            if self.thickness_image is not None:
                image = self.thickness_image.copy()
                self.line_viewer.setOpacity(0.7)
                self.line_viewer.setOverlayImage(image)
            else:
                print("Thickness image is not available.")

        elif line_checked == False and blobs_checked == True: 
            # image = self.image_cropped.copy()
            image = QImage(self.image_cropped.size(), QImage.Format_ARGB32)
            image.fill(Qt.transparent)
            
            self.blob_image = self.drawBlobs(image, self.blob_list)

            self.line_viewer.setOpacity(0.9)
            self.line_viewer.setOverlayImage(self.blob_image)
        
        else:
            self.line_viewer.setFixedWidth(self.IMAGEVIEWER_W)
            self.line_viewer.setFixedHeight(self.IMAGEVIEWER_H)
            self.line_viewer.setImg(self.image_cropped)

            self.blob_image = None

    #####BRANCHSKELETON METHODS#####

    def showSkelMenu(self, position):
            menu = QMenu(self)
            menu.addAction(self.actionShowSkel)
            menu.addAction(self.actionShowEdges)

             # Add a separator line between actions in the context menu
            self.actionSeparator = QAction(self)
            self.actionSeparator.setSeparator(True)
            menu.addAction(self.actionSeparator)

            menu.addAction(self.actionShowBranch)

            menu.exec_(self.skel_viewer.mapToGlobal(position))
    
    def toggleShowSkel(self, checked):
        if checked:
            self.skel_checked = True
            self.edges_checked = False
            self.actionShowEdges.setChecked(False)
        else:
            self.skel_checked = False
        
        self.toggleSkelBranchEdges(self.skel_checked, self.branch_checked, self.edges_checked)

    def toggleShowBranch(self, checked):
        if checked:
            self.branch_checked = True
        else:
            self.branch_checked = False
        
        self.toggleSkelBranchEdges(self.skel_checked, self.branch_checked, self.edges_checked)

    def toggleShowEdges(self, checked):
        if checked:
            self.edges_checked = True
            self.skel_checked = False
            self.actionShowSkel.setChecked(False)
        else:
            self.edges_checked = False
            # self.resetSkelTextBox()
        
        self.toggleSkelBranchEdges(self.skel_checked, self.branch_checked, self.edges_checked)

    def toggleSkelBranchEdges(self, skel, branch, edges):
        if skel == True or branch == True or edges == True:
            branch_image = self.drawBranchSkel(self.skeleton, self.branch_points, self.edges, branch, skel, edges)
            self.skel_viewer.setOpacity(1.0)
            self.skel_viewer.setOverlayImage(branch_image)
        
        else:
            self.skel_viewer.setFixedWidth(self.IMAGEVIEWER_W)
            self.skel_viewer.setFixedHeight(self.IMAGEVIEWER_H)
            self.skel_viewer.setImg(self.image_cropped)

    def drawBranchSkel(self, skeleton, branch_points, connections, branch, skel, conn):
         # Create a transparent QImage from the skeleton and branch points
        branch_image = QImage(skeleton.shape[1], skeleton.shape[0], QImage.Format_ARGB32)
        branch_image.fill(Qt.transparent)
        painter = QPainter(branch_image)

        if skel:
            pen = QPen(Qt.blue, 2)
            painter.setPen(pen)

            h, w = skeleton.shape
            neighbor_offsets = [(-1, -1), (-1, 0), (-1, 1),
                                ( 0, -1),          ( 0, 1),
                                ( 1, -1), ( 1, 0), ( 1, 1)]
            yx = np.column_stack(np.where(skeleton))
            skeleton_set = set((y, x) for y, x in yx)
            for y, x in yx:
                for dy, dx in neighbor_offsets:
                    ny, nx_ = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx_ < w and (ny, nx_) in skeleton_set:
                        # To avoid duplicate lines, only draw if neighbor is "after" current
                        if (ny > y) or (ny == y and nx_ > x):
                            painter.drawLine(x, y, nx_, ny)

            # # to draw the skeleton by points in yellow
            # pen = QPen(Qt.yellow, 2)
            # painter.setPen(pen)

            # for (y, x) in zip(*np.where(skeleton)):
            #     painter.drawPoint(x, y)
        
        if conn: 
            pen = QPen(Qt.green, 3)

            # Draw filtered segments
            y_threshold = self.row_dist
            print(f"len of connections is {len(connections)}")
            filterd_segments = []  
            for start, end, color, angle, dist in connections:
                y1, y2 = start[1], end[1]  # Remember: start = (x, y)
                if abs(y1 - y2) <= y_threshold:  # Filter segments
                    filterd_segments.append((start, end, color, angle, dist))
                    
            print(f"len of filtered segments pre is {len(filterd_segments)}")
                    
            for i, (start, end, color, angle, dist) in enumerate(filterd_segments):                    
                pen.setColor(QColor(color[0], color[1], color[2]))
                painter.setPen(pen)
                # print(f"angle of {i} is {angle}")
                if dist > 2:
                    painter.drawLine(start[0], start[1], end[0], end[1])

                    # self.updateSkelTextBox([angle], i, color=f'rgb({color[0]},{color[1]},{color[2]})')

                    # #Draw the angle value above each line
                    # angle_text = f"{angle:.2f}°"
                    # text_x = (start[0] + end[0]) // 2 - 20
                    # text_y = (start[1] + end[1]) // 2 - 10  # Slightly above the line
                    # painter.drawText(text_x, text_y, angle_text)

        if branch:                
            # pen = QPen(QColor(255, 0, 0, 100), )
            # painter.setPen(pen)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 0, 0))
            for point in branch_points:
                painter.drawEllipse(point[1] - 2, point[0] - 2, 4, 4)
        
        painter.end()

        return branch_image

    #####EXPORT METHODS#####

    def addMaskToProject(self):
        if self.parent_viewer:
            self.parent_viewer.exportMaskAsBlob(self.masch, offset=self.off, class_name="Empty")
        return

    # Unified export function for both line and skeleton data.
    def exportData(self):
        dialog = ExportDialog(self)
        # Show all checkboxes and options
        dialog.angle_checkbox.show()
        dialog.mask_checkbox.show()
        dialog.line_checkbox.show()
        dialog.blob_checkbox.show()
        dialog.skeleton_checkbox.show()
        dialog.branch_points_checkbox.show()
        dialog.edges_checkbox.show()
        dialog.format_label.show()
        dialog.format_combo.show()

        # Set current state as default
        dialog.angle_checkbox.setChecked(self.line_checked)
        dialog.mask_checkbox.setChecked(self.mask_checked)
        dialog.line_checkbox.setChecked(self.line_checked)
        dialog.blob_checkbox.setChecked(self.blobs_checked)
        dialog.skeleton_checkbox.setChecked(self.skel_checked)
        dialog.branch_points_checkbox.setChecked(self.branch_checked)
        dialog.edges_checkbox.setChecked(self.edges_checked)

        # Connect format change to onExportFormatChanged method
        # dialog.format_combo.currentTextChanged.connect(
        #     lambda _: self.onExportFormatChanged(dialog)
        # )
        # # Set initial state
        # self.onExportFormatChanged(dialog)

        if dialog.exec_() != QDialog.Accepted:
            return

        options = dialog.getExportOptions()
        file_path = options["path"]
        export_angles = options.get("export_angles", False)
        export_thickness = options.get("export_thickness", False)
        export_mask = options.get("export_mask", False)
        export_lines = options.get("export_lines", False)
        export_blobs = options.get("export_blobs", False)
        export_skeleton = options.get("export_skeleton", False)
        export_branch_points = options.get("export_branch_points", False)
        export_edges = options.get("export_edges", False)
        export_format = options.get("format", "")
        export_success = False

        
        if export_angles and hasattr(self, "lines"):
            angles_filename = f"{file_path}_angles.csv"
            with open(angles_filename, "w") as angle_file:
                angle_file.write("Line Index,Angle (degrees)\n")
                for i, (_, _, angle, _) in enumerate(self.lines):
                    if angle < 0:
                        angle = np.pi/2 + angle  
                    else:
                        angle = angle - np.pi/2
                    angle_deg = np.rad2deg(angle)
                    angle_file.write(f"{i + 1},{angle_deg:.2f}\n")
            export_success = True

        if export_thickness and hasattr(self, "thickness_image"):
            thick_filename = f"{file_path}_thickness.csv"
            with open(thick_filename, "w") as thick_file:
                # writer = csv.writer(csvfile)
                # writer.writerow(["Mean", "Max", "Min"])
                # writer.writerow([f"{self.thickness_data[0]:.2f}", f"{self.thickness_data[1]:.2f}", f"{self.thickness_data[2]:.2f}"])
                thick_file.write("Mean,Max,Min\n")
                thick_file.write(f"{self.thickness_data[0]:.2f},{self.thickness_data[1]:.2f},{self.thickness_data[2]:.2f}\n")
            export_success = True
        
        # DXF export (if selected)
        if export_format == ".dxf":
            if not file_path.lower().endswith(".dxf"):
                file_path += ".dxf"
            dialog.mask = self.masch if export_mask else None
            dialog.lines = self.lines if export_lines else []
            dialog.skeleton = self.skeleton if export_skeleton else None
            dialog.branch_points = self.branch_points if export_branch_points else []
            dialog.edges = self.edges if export_edges else []
            dialog.blobs = self.blob_list if export_blobs else []

            georef_filename = None
            if hasattr(self.parent_viewer.image, 'georef_filename') and self.parent_viewer.image.georef_filename:
                georef_filename = self.parent_viewer.image.georef_filename

            dialog.DXFExport(
                file_path, export_skeleton, export_branch_points, export_edges, export_blobs, export_mask, export_lines,
                georef=georef_filename, offset=self.off,
                img_size=(self.parent_viewer.image.width, self.parent_viewer.image.height)
            )
            export_success = True

        # PNG/CSV export for each selected option
        else:
            if export_mask:
                mask_filename = f"{file_path}_mask.png"
                if self.line_checked and hasattr(self, "lines"):
                    qmask = genutils.maskToQImage(self.masch)
                    mask_with_lines = self.paintLinesImage(qmask, self.lines)
                    # self.blob_image = mask_with_lines
                    self.blob_image = self.paintLinesImage(self.image_cropped,self.lines)
                    mask_with_lines.save(mask_filename)
                else:
                    mask_image = genutils.maskToQImage(self.masch)
                    mask_image.save(mask_filename)
                export_success = True

            if export_blobs:
                blobs_filename = f"{file_path}_blobs.png"
                blob_image = self.drawBlobs(self.blob_image, self.blob_list)
                blob_image.save(blobs_filename)
                export_success = True

            if export_skeleton and self.skeleton is not None:
                skeleton_filename = f"{file_path}_skeleton.png"
                branch_image = self.drawBranchSkel(
                    self.skeleton, self.branch_points, self.edges,
                    export_branch_points, export_skeleton, export_edges
                )
                branch_image.save(skeleton_filename)
                export_success = True

            if export_edges and self.edges:
                edges_filename = f"{file_path}_edges.png"
                edge_image = self.drawBranchSkel(
                    self.skeleton, self.branch_points, self.edges,
                    self.branch_checked, self.skel_checked, self.edges_checked
                )
                edge_image.save(edges_filename)
                angles_filename = f"{file_path}_edges_angles.csv"
                with open(angles_filename, "w") as file:
                    file.write("Connection Index,Angle (degrees)\n")
                    for i, (_, _, _, angle, _) in enumerate(self.edges):
                        file.write(f"{i + 1},{angle:.2f}\n")
                export_success = True

        if export_success:
            QMessageBox.information(self, "Export Successful", "Data exported successfully.")
        else:
            QMessageBox.warning(self, "Export Failed", "No data to export.")

    


  