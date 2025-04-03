import sys

import numpy as np
import cv2
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QTextEdit, QSlider, QMenu, QCheckBox, QMenuBar, QAction
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush
from PyQt5.QtCore import pyqtSignal, Qt, QBuffer

from source.QtImageViewer import QtImageViewer
from source import genutils

from skimage.transform import hough_line, hough_line_peaks
from skimage.morphology import skeletonize, thin

from skimage.graph import route_through_array
import networkx as nx

from scipy.interpolate import interp1d
from scipy.ndimage import binary_dilation, binary_erosion, convolve

from skimage import measure, morphology, io, color
from skimage.draw import line
from scipy.spatial import KDTree

import svgwrite
from PyQt5.QtSvg import QSvgRenderer

IMAGEVIEWER_W = 640
IMAGEVIEWER_H = 480
class RowsWidget(QWidget):

    closeRowsWidget = pyqtSignal()

    # def __init__(self, image_cropped, created_blobs, offset, parent=None):
    def __init__(self, cropped_image, mask_array, blobs, rect, parent = None):
        super(RowsWidget, self).__init__(parent)

        # self.q_skel = None

        # i = 0
        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(1440)
        self.setMinimumHeight(900)

        # IMAGEVIEWER_W = 700
        # IMAGEVIEWER_H = 640
        

        self.setWindowTitle("Rows Analysis")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.image_cropped = cropped_image
        # self.image_mask = image_mask
        self.maschera = mask_array
        self.masch = None
        self.image_overlay = None
        self.skeleton = None
        self.branch_points =  []

        self.rect = rect
        self.blob_list = blobs
        self.centroids = []
        self.bboxes = []

        self.set_textbox = False

        #create line viewer
        self.line_viewer = QtImageViewer()
        self.line_viewer.disableScrollBars()
        self.line_viewer.enablePan()
        self.line_viewer.enableZoom()
        self.line_viewer.setFixedWidth(IMAGEVIEWER_W)
        self.line_viewer.setFixedHeight(IMAGEVIEWER_H)

        # Enable context menu policy
        self.line_viewer.setContextMenuPolicy(Qt.CustomContextMenu)
        self.line_viewer.customContextMenuRequested.connect(self.showLinesMenu)
        self.lines = []

        # Create checkable actions for the mask and lines
        self.actionShowMask = QAction("Show Mask", self)
        
        self.actionShowMask.setCheckable(False)
        self.actionShowMask.toggled.connect(self.toggleShowMask)
        self.mask_checked = False

        self.actionShowLines = QAction("Show Lines", self)
        
        self.actionShowLines.setCheckable(False)
        self.actionShowLines.toggled.connect(self.toggleShowLines)
        self.line_checked = False

        # create skeleton viewer
        self.skel_viewer = QtImageViewer()
        self.skel_viewer.disableScrollBars()
        self.skel_viewer.enablePan()
        self.skel_viewer.enableZoom()
        self.skel_viewer.setFixedWidth(IMAGEVIEWER_W)
        self.skel_viewer.setFixedHeight(IMAGEVIEWER_H)

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
        
        #Create the layout
        layout = QVBoxLayout()
        
        # Create a horizontal layout for the viewers
        viewers_layout = QHBoxLayout()
        
        # Add line_viewer to viewers layout
        viewers_layout.addWidget(self.line_viewer, alignment=Qt.AlignLeft)
        # Add skeleton viewer to viewers layout
        viewers_layout.addWidget(self.skel_viewer, alignment=Qt.AlignRight)
        # Add the viewers to the main layout
        layout.addLayout(viewers_layout)

        # Add the viewers layout to the main layout
        # layout.addLayout(viewers_layout)
        # layout.addLayout(layoutTop)
        # layout.addWidget(self.progress_bar)
        # layout.addWidget(self.viewer, alignment=Qt.AlignCenter)
        # layout.addLayout(layoutButtons)
        layout.setSpacing(10)

        self.angleTextBox = QTextEdit(self)
        self.angleTextBox.setReadOnly(True)
        layout.addWidget(self.angleTextBox)

        
        # self.setLayout(layout)

        # Add slider for structuring element size
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(50)
        self.slider.setValue(21)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.updateStructuringElement)

        value = self.slider.value()

        self.slider_label = QLabel(f"Pixel Grow: {(value-1)//2}")
        
        layout.addWidget(self.slider_label)
        layout.addWidget(self.slider)

        self.structuring_element_size = self.slider.value()

        layout.setSpacing(10)
        
        button_layout = QHBoxLayout()
        self.btnOk = QPushButton("OK")
        self.btnOk.clicked.connect(self.applyHough)
        button_layout.addWidget(self.btnOk)

        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.closeWidget)
        button_layout.addWidget(self.btnClose)
        layout.addLayout(button_layout)

        self.line_viewer.setImg(self.image_cropped)
        self.skel_viewer.setImg(self.image_cropped)

        self.setLayout(layout)

    # # Define the toggle functions
    # def toggleShowMask(self, checked):
    #     if checked:
    #         self.line_viewer.setOverlayImage(self.maschera)  # Show mask
    #     else:
    #         self.line_viewer.setOverlayImage(None)  # Hide mask

    # def toggleShowLines(self, checked):
    #     if checked:
    #         self.line_viewer.setOverlayImage(self.image_overlay)  # Show lines
    #     else:
    #         self.line_viewer.setOverlayImage(None)  # Hide lines
    
    
    def updateStructuringElement(self, value):
        self.structuring_element_size = value
        self.slider_label.setText(f"Pixel Grow: {(value-1)//2}")
            
    def applyHough(self):
        if self.set_textbox == True:
            self.resetAngleTextBox()

        _, self.masch = self.maskGrow(self.maschera, self.structuring_element_size)
        # self.houghTansformation(final_mask)
        self.lines = self.houghTansformation(self.masch)

        self.actionShowLines.setCheckable(True)
        self.actionShowMask.setCheckable(True)

        self.line_checked = True
        self.actionShowLines.setChecked(True)
        self.mask_checked = True
        self.actionShowMask.setChecked(True)
        self.toggleShow(self.line_checked, self.mask_checked)

        # i += 1
        self.skeleton = self.applySkeletonization(self.masch)
        self.branch_points = self.branchPoints(self.skeleton)
        self.actionShowSkel.setCheckable(True)
        self.actionShowSkel.setChecked(True)
        self.actionShowBranch.setCheckable(True)
        self.actionShowBranch.setChecked(True)

        # _, _, img = self.vectorBranchPoints(skel)
                
        # _, skel_int = self.findIntersectionPoints(skel)
        # self.vectorBranchPoints(skel)

        # # # self.connectSkeletonIntersections(skel)
        # self.houghTansformation(skel, i)

        self.set_textbox = True

        # self.skel_viewer.setOpacity(1.0)
        # self.skel_viewer.setOverlayImage(skel_int)
        # self.skel_viewer.setOverlayImage(img)
        
        
        # self.line_viewer.setOpacity(0.7)
        # self.line_viewer.setOverlayImage(self.image_overlay)


    def closeWidget(self):
        self.closeRowsWidget.emit()
        self.close()

    def maskGrow(self, mask, value):
        #GROW DEI BLOB, LA MALTA È QUELLA CHE DISTA x PIXEL DAL BLOB
        rect_mask_grow = mask.copy()

        # Create a structuring element that defines the neighborhood
        # 21x21 to cover 10 positions around each 1 (10 positions
        # structuring_element = np.ones((21, 21), dtype=np.uint8)
        # structuring_element = np.ones((self.structuring_element_size, self.structuring_element_size), dtype=np.uint8)
        structuring_element = np.ones((value, value), dtype=np.uint8)
        structuring_element_half = np.ones((value//2, value//2), dtype=np.uint8)
        print(f"Structuring element size: {value}")
        rect_mask_grow = binary_dilation(mask, structure=structuring_element)
        rect_mask_grow_sub = rect_mask_grow - mask

        # rect_mask_grow = rect_mask_grow - mask

        # Save the rect_mask_grow as a matplotlib figure
        plt.figure(figsize=(10, 10))
        plt.imshow(rect_mask_grow_sub, cmap='gray')
        plt.axis('off')
        plt.savefig("rect_mask_grow.png", bbox_inches='tight', pad_inches=0)
        plt.close()

        rect_mask_eroded = binary_erosion(rect_mask_grow, structure=structuring_element_half)

        # Save the rect_mask_eroded as a matplotlib figure
        plt.figure(figsize=(10, 10))
        plt.imshow(rect_mask_eroded, cmap='gray')
        plt.axis('off')
        plt.savefig("rect_mask_eroded.png", bbox_inches='tight', pad_inches=0)
        plt.close()

        rect_mask_final = rect_mask_eroded - mask

        # Save the rect_mask_eroded as a matplotlib figure
        plt.figure(figsize=(10, 10))
        plt.imshow(rect_mask_final, cmap='gray')
        plt.axis('off')
        plt.savefig("rect_mask_final.png", bbox_inches='tight', pad_inches=0)
        plt.close()


        return rect_mask_grow_sub, rect_mask_final
    
    # def updateAngleTextBox(self, angles):
    def updateAngleTextBox(self, angles, index, color='red'):
        current_text = self.angleTextBox.toHtml()
        new_text = ''.join([f'<span style="color: {color};">line {str(index+1)}: {angle}</span><br>' for angle in angles])
        self.angleTextBox.setHtml(current_text + new_text)

    def resetAngleTextBox(self):
        self.angleTextBox.clear()
        self.set_textbox = False

    def boundary_clamp(self, mask, x0, y0, x1, y1):
        """
        Find the range of the line ((x0, y0), (x1, y1)) clamped to the mask.
        """
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
        plt.figure(figsize=(10, 6))
        plt.imshow(np.log(1 + h), extent=[np.rad2deg(theta[0]), np.rad2deg(theta[-1]), d[-1], d[0]],
                cmap='hot', aspect=1.5)
        plt.title('Hough Transform Accumulator')
        plt.xlabel('Theta (degrees)')
        plt.ylabel('Rho (pixels)')
        plt.colorbar(label='Votes')
        # plt.show()
        plt.savefig("hough_transf.png", bbox_inches='tight', pad_inches=0)
        plt.close()

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
        plt.figure(figsize=(8, 8))
        plt.imshow(mask, cmap='gray')
        plt.axis('off')

        for ((x0, y0), (x1, y1), ang) in lines:
            plt.plot((x0, x1), (y0, y1), color='b')  # Plot detected lines in red

        for (px, py) in intersection_points:
            plt.plot(px, py, 'ro')  # Plot intersections as red dots

        plt.title('Detected Lines and Intersections')
        plt.savefig("hough_lines_with_intersections.png", bbox_inches='tight', pad_inches=0)
        # plt.show()
        plt.close()

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
        plt.figure(figsize=(8, 8))
        plt.imshow(mask, cmap='gray')
        plt.axis('off')        
        
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

        plt.title('Detected Lines and Intersections')
        plt.savefig("spezzate_with_intersections.png", bbox_inches='tight', pad_inches=0)
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

        # print(f"lines: {sorted_lines_with_color}")
        # sorted_intersections_with_color = sorted(intersections_with_color, key=lambda entry: entry[0][1])
        # print(f"intersections: {sorted_intersections_with_color}")
        # print(sorted_lines_with_color)

        # Visualize lines on the original mask
        # plt.figure(figsize=(8, 8))
        # plt.imshow(mask, cmap='gray')
        
        # for i, ((x0, y0), (x1, y1), _, color) in enumerate(sorted_lines_with_color):

        #     plt.plot((x0, x1), (y0, y1), color=np.array(color) / 255)

        # plt.title('Detected Lines')
        # plt.savefig("hough_lines.png", bbox_inches='tight', pad_inches=0)
        # plt.show()  # Display the plot
        # plt.close()
    
        # Draw the detected lines on the qimage mask
        # image_with_lines = self.image_mask.copy()
        # image_with_lines = self.image_cropped.copy()
        # # image_with_lines = genutils.maskToQImage(mask)
        # image_with_lines = self.image_cropped.copy()
        # painter = QPainter(image_with_lines)
        # pen = QPen(Qt.red, 5)

        # # with QPainter(image_with_lines) as painter:
        # for i, ((x0, y0), (x1, y1), ang, color) in enumerate(sorted_lines_with_color):
        #     # color = colors.pop(0)          
        #     pen.setColor(QColor(color[0], color[1], color[2]))
        #     painter.setPen(pen)
        #     painter.drawLine(x0, y0, x1, y1)

        #     if ang < 0:
        #         ang = np.pi/2 + ang  
        #     else:
        #         ang = ang - np.pi/2

        #     ang_deg = np.rad2deg(ang)
        #     # ang = round(ang, 4)
        #     ang_deg = round(ang_deg, 4)

            
        #     # self.updateAngleTextBox([ang], i, color=f'rgb({color[0]},{color[1]},{color[2]})')
        for i, (_, _, ang, color) in enumerate(sorted_lines_with_color):
        # for i, (_, _,ang, color) in enumerate(sorted_lines_with_color):            
            if ang < 0:
                ang = np.pi/2 + ang  
            else:
                ang = ang - np.pi/2

            ang_deg = np.rad2deg(ang)
            # ang = round(ang, 4)
            ang_deg = round(ang_deg, 4)

            self.updateAngleTextBox([ang_deg], i, color=f'rgb({color[0]},{color[1]},{color[2]})')

        # # pen = QPen(Qt.blue, 5)
        # # painter.setPen(pen)
        # # for (line1, line2) in intersections:
        # #     # (x0, y0), (x1, y1) = line1
        # #     # painter.drawLine(x0, y0, x1, y1)
        # #     (x2, y2), (x3, y3), _ = line2
        # #     painter.drawLine(x2, y2, x3, y3)
        # # pen = QPen(Qt.blue, 5)
        # # painter.setPen(pen)
        # # for (line1, line2) in intersections:
        # #     # (x0, y0), (x1, y1) = line1
        # #     # painter.drawLine(x0, y0, x1, y1)
        # #     (x2, y2), (x3, y3), _ = line2
        # #     painter.drawLine(x2, y2, x3, y3)

        # painter.end()

        # # Save the image with lines
        # image_with_lines.save("image_with_lines.png")

        # #Set the mask with lines as image overlay
        # self.image_overlay = image_with_lines
        
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
        # skeleton = skeletonize(mask)
        # skeleton = median(skeleton, disk(1))
        skeleton = thin(mask)
        
        h, w = skeleton.shape
        dwg = svgwrite.Drawing(f"skeleton.svg", size=(w, h))
        
        # Draw skeleton as black lines
        y, x = np.where(skeleton)
        for i in range(len(y)):
            dwg.add(dwg.circle(center=(int(x[i]), int(y[i])), r=0.5, fill="black"))

        # Save SVG file
        dwg.save()
        print("Saved skeleton as skeleton.svg")

        # Create a QImage with the same size as the skeleton
        # q_image = QImage(skeleton.shape[1], skeleton.shape[0], QImage.Format_ARGB32)
        # q_image.fill(Qt.transparent)

        # # Draw the skeleton on the QImage
        # painter = QPainter(q_image)
        # pen = QPen(Qt.blue, 1)
        # painter.setPen(pen)

        # for (y, x) in zip(*np.where(skeleton)):
        #     painter.drawPoint(x, y)

        # painter.end()

        # # Save the QImage
        # q_image.save("skeleton_qimage.png")

        # Visualize the skeleton
        plt.figure(figsize=(8,8))
        plt.imshow(skeleton, cmap='gray')
        plt.title('Skeletonized Mask')
        plt.savefig("skeletonized_mask.png", bbox_inches='tight', pad_inches=0)
        plt.close()

        return skeleton
     
    def branchPoints(self, skeleton, filename="skeleton_vector.svg"):
        # Define a kernel to detect branch points
        kernel = np.array([[1, 1, 1],
                   [1, 10, 1],
                   [1, 1, 1]])

        # Convolve the skeleton with the kernel
        convolved = convolve(skeleton.astype(np.uint8), kernel, mode='constant', cval=0) - 10

        # Find branch points where the convolved result equals 11
        branch_points = (convolved >= 3) & skeleton

        # Get coordinates
        # endpoints_yx = np.column_stack(np.where(endpoints))
        branch_points_yx = np.column_stack(np.where(branch_points))

        # Remove branch points that are too close to each other
        filtered_branch_points_yx = []
        for point in branch_points_yx:
            if not any(np.linalg.norm(point - np.array(existing_point)) < 5 for existing_point in filtered_branch_points_yx):
                filtered_branch_points_yx.append(point)

        ################################################################################################
        h, w = skeleton.shape
        dwg = svgwrite.Drawing('pippo.svg', size=(w, h))
        
        # Draw skeleton as black lines
        y, x = np.where(skeleton)
        for i in range(len(y)):
            dwg.add(dwg.circle(center=(int(x[i]), int(y[i])), r=0.5, fill="blue"))

        # Draw branch points as red circles
        for point in filtered_branch_points_yx:
            dwg.add(dwg.circle(center=(int(point[1]), int(point[0])), r=2, fill="red"))

        # Save SVG file
        dwg.save()
        print(f"Saved SVG as pippo.svg")
        ################################################################################################

        # # Create a QImage from the skeleton and branch points
        # q_image = QImage(skeleton.shape[1], skeleton.shape[0], QImage.Format_ARGB32)
        # q_image.fill(Qt.transparent)

        # painter = QPainter(q_image)
        # pen = QPen(Qt.blue, 5)
        # painter.setPen(pen)

        # # Draw skeleton
        # for (y, x) in zip(*np.where(skeleton)):
        #     painter.drawPoint(x, y)

        # # Draw branch points
        # pen.setColor(Qt.red)
        # painter.setPen(pen)
        # painter.setBrush(QBrush(Qt.red))
        # for point in filtered_branch_points_yx:
        #     painter.drawEllipse(point[1], point[0], 10, 10)

        # painter.end()

        # ################################################################################################

        # # Plot results
        # fig, ax = plt.subplots(figsize=(6, 6))
        # ax.imshow(skeleton, cmap='gray')
        # # ax.scatter(endpoints_yx[:, 1], endpoints_yx[:, 0], color='red', label='Endpoints', s=80, marker='o')
        # for (y, x) in filtered_branch_points_yx:
        # # for (y, x) in branch_points_yx:
        #     ax.scatter(x, y, color=np.random.rand(3,), s=40, marker='x')
        # ax.set_title("Skeleton with Branch Points")
        # # ax.legend()
        # ax.axis("off")

        # plt.savefig("branch_points_on_skeleton.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        # image = self.drawBranchSkel(skeleton, filtered_branch_points_yx, branch=True, skel=False)   

        # return branch_points, q_image
        return filtered_branch_points_yx

    def vectorBranchPoints(self,skeleton):

        # Extract skeleton pixels
        y, x = np.where(skeleton)

        zipped = zip(y,x)

        # Create a graph from skeleton
        G = nx.Graph()
        for (i, j) in zip(y, x):
            G.add_node((i, j))

        # Find edges (connect nearby pixels)
        # for (i, j) in zip(y, x):
        for (i, j) in zipped:
            for dy, dx in [(-1,0), (1,0), (0,-1), (0,1)]:  # 4-neighborhood
                ni, nj = i + dy, j + dx
                if (ni, nj) in G:
                    G.add_edge((i, j), (ni, nj))


        print(len(G.nodes()))
        # Draw nodes and edges of the graph
        pos = {node: (node[1], -node[0]) for node in G.nodes()}  # Flip y-axis for correct orientation

        nx.draw_networkx_nodes(G, pos, node_size=0.25, node_color="red")
        nx.draw_networkx_edges(G, pos, width=2, edge_color="blue")

        img = self.saveGraphToQImage(G, pos, skeleton)
    
        return G, pos, img
    
    def saveGraphToQImage(self, graph, pos, skeleton, output_file="graph.png"):

        width, height = skeleton.shape[1], skeleton.shape[0]
        # Create a QImage with the specified dimensions
        q_image = QImage(skeleton.shape[1], skeleton.shape[0], QImage.Format_ARGB32)
        q_image.fill(Qt.white)  # Fill the background with white

        # Create a QPainter to draw on the QImage
        painter = QPainter(q_image)
        pen = QPen(Qt.black, 1)  # Black pen for edges
        painter.setPen(pen)

       # Scale positions to fit the QImage
        scaled_pos = {node: (x, height - y) for node, (x, y) in pos.items()}  # Flip y-axis for QImage

        # Draw edges
        for edge in graph.edges():
            node1, node2 = edge
            x1, y1 = scaled_pos[node1]
            x2, y2 = scaled_pos[node2]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw nodes
        pen.setColor(Qt.red)  # Red pen for nodes
        painter.setPen(pen)
        for node in graph.nodes():
            x, y = scaled_pos[node]
            painter.drawEllipse(int(x) - 2, int(y) - 2, 4, 4)  # Draw a small circle for each node

        # Finish painting
        painter.end()

        # Save the QImage to a file
        q_image.save(output_file)
        print(f"Graph saved to {output_file}")

        return q_image
        
        # self.drawBranchPoints(G, pos)
        
        # plt.figure(figsize=(8, 8))
        # nx.draw_networkx_nodes(G, pos, node_size=0.25, node_color="red")
        # nx.draw_networkx_edges(G, pos, width=2, edge_color="blue")


        # plt.title("Skeleton Graph with Intersections")
        # plt.savefig("vectorized_skeleton.png", bbox_inches='tight', pad_inches=0)
        # plt.close()


        


    def drawBranchSkel(self, skeleton, branch_points, branch, skel):
         # Create a QImage from the skeleton and branch points
        branch_image = QImage(skeleton.shape[1], skeleton.shape[0], QImage.Format_ARGB32)
        branch_image.fill(Qt.transparent)
        painter = QPainter(branch_image)

        if branch:                
            pen = QPen(Qt.red, 10)
            painter.setPen(pen)
            painter.setBrush(QBrush(Qt.red))
            for point in branch_points:
                painter.drawEllipse(point[1], point[0], 10, 10)

        if skel:
            pen = QPen(Qt.blue, 5)
            painter.setPen(pen)

            # Draw skeleton
            for (y, x) in zip(*np.where(skeleton)):
                painter.drawPoint(x, y)

        painter.end()

        return branch_image

    # def drawEdges(self,skeleton):
    #     # Create a QImage from the skeleton and branch points
    #     skel_image = QImage(skeleton.shape[1], skeleton.shape[0], QImage.Format_ARGB32)
    #     skel_image.fill(Qt.transparent)

    #     painter = QPainter(skel_image)
    #     pen = QPen(Qt.blue, 5)
    #     painter.setPen(pen)

    #     # Draw skeleton
    #     for (y, x) in zip(*np.where(skeleton)):
    #         painter.drawPoint(x, y)

    #     return skel_image


        # plt.title("Skeleton Graph with Intersections")
        # plt.savefig("vectorized_skeleton.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

###############################################################################

    def paintLinesImage(self, image, lines):
        painter = QPainter(image)
        pen = QPen(Qt.red, 5)

        # with QPainter(image) as painter:
        for i, ((x0, y0), (x1, y1), ang, color) in enumerate(lines):
            # color = colors.pop(0)          
            pen.setColor(QColor(color[0], color[1], color[2]))
            painter.setPen(pen)
            painter.drawLine(x0, y0, x1, y1)

            # if ang < 0:
            #     ang = np.pi/2 + ang  
            # else:
            #     ang = ang - np.pi/2

            # ang_deg = np.rad2deg(ang)
            # # ang = round(ang, 4)
            # ang_deg = round(ang_deg, 4)

            
            # self.updateAngleTextBox([ang], i, color=f'rgb({color[0]},{color[1]},{color[2]})')
            # self.updateAngleTextBox([ang_deg], i, color=f'rgb({color[0]},{color[1]},{color[2]})')

        # pen = QPen(Qt.blue, 5)
        # painter.setPen(pen)
        # for (line1, line2) in intersections:
        #     # (x0, y0), (x1, y1) = line1
        #     # painter.drawLine(x0, y0, x1, y1)
        #     (x2, y2), (x3, y3), _ = line2
        #     painter.drawLine(x2, y2, x3, y3)
        # pen = QPen(Qt.blue, 5)
        # painter.setPen(pen)
        # for (line1, line2) in intersections:
        #     # (x0, y0), (x1, y1) = line1
        #     # painter.drawLine(x0, y0, x1, y1)
        #     (x2, y2), (x3, y3), _ = line2
        #     painter.drawLine(x2, y2, x3, y3)

        painter.end()

        # Save the image with lines
        # image.save("image.png")

        #Set the mask with lines as image overlay
        # self.image_overlay = image
        return image

    def showLinesMenu(self, position):
            menu = QMenu(self)
            menu.addAction(self.actionShowMask)
            menu.addAction(self.actionShowLines)
            menu.exec_(self.line_viewer.mapToGlobal(position))

    def toggleShowMask(self, checked):
        if checked:
            self.mask_checked = True
        else:
            self.mask_checked = False
        
        self.toggleShow(self.line_checked, self.mask_checked)

    def toggleShowLines(self, checked):
        if checked:
            self.line_checked = True
        else:
            self.line_checked = False
        
        self.toggleShow(self.line_checked, self.mask_checked)

    def toggleShow(self, line_checked, mask_checked):
        
        if line_checked  == True and mask_checked == True:
            # lines = self.houghTansformation(self.masch)
            qmask = genutils.maskToQImage(self.masch)
            mask_with_lines = self.paintLinesImage(qmask, self.lines)

            self.line_viewer.setOpacity(0.7)
            self.line_viewer.setOverlayImage(mask_with_lines)
        
        elif line_checked == True and mask_checked == False:
            # lines = self.houghTansformation(self.masch)
            # lines = self.applyHough()
            image = self.image_cropped.copy()
            image_with_lines = self.paintLinesImage(image, self.lines)

            self.line_viewer.setOpacity(0.7)
            self.line_viewer.setOverlayImage(image_with_lines)
        
        elif line_checked == False and mask_checked == True:
            # lines = self.houghTansformation(mask)
            qmask = genutils.maskToQImage(self.masch)
            
            self.line_viewer.setOpacity(0.7)
            self.line_viewer.setOverlayImage(qmask)
        
        else:
            self.line_viewer.setFixedWidth(IMAGEVIEWER_W)
            self.line_viewer.setFixedHeight(IMAGEVIEWER_H)
            self.line_viewer.setImg(self.image_cropped)

######################################################################

    def showSkelMenu(self, position):
            menu = QMenu(self)
            menu.addAction(self.actionShowSkel)
            menu.addAction(self.actionShowBranch)
            menu.addAction(self.actionShowEdges)
            menu.exec_(self.skel_viewer.mapToGlobal(position))
    
    def toggleShowSkel(self, checked):
        if checked:
            self.skel_checked = True
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
        else:
            self.edges_checked = False
        
        self.toggleSkelBranchEdges(self.skel_checked, self.branch_checked, self.edges_checked)


    def toggleSkelBranchEdges(self, skel, branch, edges):
        if skel == True or branch == True:
            branch_image = self.drawBranchSkel(self.skeleton, self.branch_points, branch, skel)
            self.skel_viewer.setOpacity(1.0)
            self.skel_viewer.setOverlayImage(branch_image)
        
        
        elif skel == False and branch == False and edges == True:
            pass
        
        elif skel == True and branch == False and edges == True:
            pass
        
        elif skel == False and branch == True and edges == True:
            pass

        else:
            self.skel_viewer.setFixedWidth(IMAGEVIEWER_W)
            self.skel_viewer.setFixedHeight(IMAGEVIEWER_H)
            self.skel_viewer.setImg(self.image_cropped)
