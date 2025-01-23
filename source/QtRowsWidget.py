import sys

import numpy as np
import cv2
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QSizePolicy, QTextEdit
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtCore import pyqtSignal, Qt

from source.QtImageViewer import QtImageViewer
from source import genutils

from skimage.transform import hough_line, hough_line_peaks
from skimage.morphology import skeletonize
from scipy.interpolate import interp1d
from skimage import measure
from skimage.draw import line
from scipy.spatial import KDTree

class RowsWidget(QWidget):

    closeRowsWidget = pyqtSignal()

    # def __init__(self, image_cropped, created_blobs, offset, parent=None):
    def __init__(self, cropped_image, mask_array, blobs, rect, parent = None):
        super(RowsWidget, self).__init__(parent)

        # i = 0
        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(1024)
        self.setMinimumHeight(900)

        IMAGEVIEWER_W = 1024
        IMAGEVIEWER_H = 640
        self.viewer = QtImageViewer()
        self.viewer.disableScrollBars()
        self.viewer.enablePan()
        self.viewer.enableZoom()
        self.viewer.setFixedWidth(IMAGEVIEWER_W)
        self.viewer.setFixedHeight(IMAGEVIEWER_H)

        self.setWindowTitle("Rows Analysis")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.image_cropped = cropped_image
        # self.image_mask = image_mask
        self.maschera = mask_array
        self.image_overlay = None

        self.rect = rect
        self.blob_list = blobs
        self.centroids = []
        self.bboxes = []

        layout = QVBoxLayout()
        # layout.addLayout(layoutTop)
        # layout.addWidget(self.progress_bar)
        layout.addWidget(self.viewer, alignment=Qt.AlignCenter)
        # layout.addLayout(layoutButtons)
        layout.setSpacing(10)

        self.angleTextBox = QTextEdit(self)
        self.angleTextBox.setReadOnly(True)
        layout.addWidget(self.angleTextBox)

        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.closeWidget)
        layout.addWidget(self.btnClose)
        
        self.setLayout(layout)
            
        self.houghTansformation(self.maschera)

        # i += 1
        # skel = self.applySkeletonization(self.maschera)
        # # # self.connectSkeletonIntersections(skel)
        # self.houghTansformation(skel, i)
        
        self.viewer.setImg(self.image_cropped)
        self.viewer.setOpacity(0.7)
        self.viewer.setOverlayImage(self.image_overlay)

    def closeWidget(self):
        self.closeRowsWidget.emit()
        self.close()

    # def updateAngleTextBox(self, angles):
    def updateAngleTextBox(self, angles, index, color='red'):
        current_text = self.angleTextBox.toHtml()
        new_text = ''.join([f'<span style="color: {color};">line {str(index+1)}: {angle}</span><br>' for angle in angles])
        self.angleTextBox.setHtml(current_text + new_text)

    def resetAngleTextBox(self):
        self.angleTextBox.clear()

    # def updateAngleTextBox(self, angles):
    def updateAngleTextBox(self, angles, index, color='red'):
        current_text = self.angleTextBox.toHtml()
        new_text = ''.join([f'<span style="color: {color};">line {str(index+1)}: {angle}</span><br>' for angle in angles])
        self.angleTextBox.setHtml(current_text + new_text)

    def resetAngleTextBox(self):
        self.angleTextBox.clear()

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
                        point1, point2 = self.boundary_clamp(mask, x0, y0, x1, y1)
                        print(point1, point2)
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
                    intersections.append((line1, line2))
                    if intersection:
                        # intersections.append((line1, line2))
                        intersection_points.append(intersection)
                        print(f"Intersection at: {intersection}")

        # Visualize lines and intersections on the original mask
        plt.figure(figsize=(8, 8))
        plt.imshow(mask, cmap='gray')
        plt.axis('off')

        for ((x0, y0), (x1, y1), ang) in lines_ints:
            plt.plot((x0, x1), (y0, y1), color='b')  # Plot detected lines in red

        for (px, py) in intersection_points:
            plt.plot(px, py, 'ro')  # Plot intersections as red dots

        plt.title('Detected Lines and Intersections')
        plt.savefig("hough_lines_with_intersections.png", bbox_inches='tight', pad_inches=0)
        plt.show()
        plt.close()

        # Remove intersectin lines with smaller angles
        for line1, line2 in intersections:
            if line1[2] < line2[2]:  # Compare angles
                if line1 in lines:
                    lines.remove(line1)
            else:
                if line2 in lines:
                    lines.remove(line2)

        lines_with_color = []
        for line in lines:
            color = tuple(np.random.randint(0, 256, 3))
            line_with_color = (*line, color)
            lines_with_color.append(line_with_color)

        
        sorted_lines_with_color = sorted(lines_with_color, key=lambda entry: entry[0][1])
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
        image_with_lines = genutils.maskToQImage(self.maschera)
        painter = QPainter(image_with_lines)
        pen = QPen(Qt.red, 5)

        # with QPainter(image_with_lines) as painter:
        for i, ((x0, y0), (x1, y1), ang, color) in enumerate(sorted_lines_with_color):
            # color = colors.pop(0)          
            pen.setColor(QColor(color[0], color[1], color[2]))
            painter.setPen(pen)
            painter.drawLine(x0, y0, x1, y1)

            if ang < 0:
                ang = np.pi/2 + ang  
            else:
                ang = ang - np.pi/2

            ang_deg = np.rad2deg(ang)
            # ang = round(ang, 4)
            ang_deg = round(ang_deg, 4)

            
            # self.updateAngleTextBox([ang], i, color=f'rgb({color[0]},{color[1]},{color[2]})')
            self.updateAngleTextBox([ang_deg], i, color=f'rgb({color[0]},{color[1]},{color[2]})')

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
        image_with_lines.save("image_with_lines.png")

        #Set the mask with lines as image overlay
        self.image_overlay = image_with_lines

        # self.image_mask = image_with_lines
        # self.image_cropped = image_with_lines

        # self.viewer.setOpacity(0.5)
        # self.viewer.setOverlayImage(self.image_mask)


   
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
