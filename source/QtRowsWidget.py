import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QSizePolicy, QTextEdit
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QSizePolicy, QTextEdit
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import pyqtSignal, Qt
import numpy as np
import cv2
from source import genutils
from source.QtImageViewer import QtImageViewer

from skimage.transform import hough_line, hough_line_peaks
from scipy.interpolate import interp1d

from skimage.draw import line
from PyQt5.QtGui import QPainter, QPen, QBrush,QColor
from PyQt5.QtGui import QPainter, QPen, QBrush,QColor
import matplotlib.pyplot as plt

from skimage import measure
from skimage.morphology import skeletonize
from scipy.spatial import KDTree



class RowsWidget(QWidget):

    closeRowsWidget = pyqtSignal()

    # def __init__(self, image_cropped, created_blobs, offset, parent=None):
    def __init__(self, image_mask,  cropped_image, mask_array, blobs, rect, parent = None):
        super(RowsWidget, self).__init__(parent)

        # i = 0
        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)

        IMAGEVIEWER_W = 800
        IMAGEVIEWER_H = 450
        self.viewer = QtImageViewer()
        self.viewer.disableScrollBars()
        self.viewer.enablePan()
        self.viewer.enableZoom()
        self.viewer.setFixedWidth(IMAGEVIEWER_W)
        self.viewer.setFixedHeight(IMAGEVIEWER_H)

        self.setWindowTitle("Rows Analysis")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.image_cropped = cropped_image
        self.image_mask = image_mask
        self.maschera = mask_array

        self.rect = rect
        self.blob_list = blobs
        self.centroids = []
        self.bboxes = []

        layout = QVBoxLayout()
        # layout.addLayout(layoutTop)
        # layout.addWidget(self.progress_bar)
        layout.addWidget(self.viewer)
        # layout.addLayout(layoutButtons)
        layout.setSpacing(10)

        self.angleTextBox = QTextEdit(self)
        self.angleTextBox.setReadOnly(True)
        layout.addWidget(self.angleTextBox)

        self.angleTextBox = QTextEdit(self)
        self.angleTextBox.setReadOnly(True)
        layout.addWidget(self.angleTextBox)

        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.closeWidget)
        layout.addWidget(self.btnClose)
        
        self.setLayout(layout)
            
        # self.q_image = genutils.rgbToQImage(self.image_cropped)
        # self.viewer.setImg(self.image_cropped)
        self.houghTansformation(self.maschera)

        # i += 1
        # skel = self.applySkeletonization(self.maschera)
        # # # self.connectSkeletonIntersections(skel)
        # self.houghTansformation(skel, i)

        # self.viewer.setOpacity(0.8)
        # self.viewer.setOverlayImage(self.image_mask)
        self.viewer.setImg(self.image_cropped)

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
        # angles = []
        # angles = []
        height, width = mask.shape
        # intersection_points = []
        for _, angle, dist in zip(*hough_line_peaks(h, theta, d)):
            # Calculate line endpoints
            try:
                # Points for the line at the left and right image boundaries
                y0 = (dist - 0 * np.cos(angle)) / np.sin(angle)  # y-intercept at x=0
                y1 = (dist - width * np.cos(angle)) / np.sin(angle)  # y-intercept at x=width

                # Check for valid values within the image bounds
                if np.isfinite(y0) and np.isfinite(y1):  # Ensure values are not infinite
                    if 0 <= y0 < height and 0 <= y1 < height:  # Clamp to image bounds
                        lines.append(((0, int(y0)), (width, int(y1)), angle))

            except ZeroDivisionError:
                # Handle cases where sin(angle) is zero (e.g., vertical lines)
                continue

        # print(f"Detected\n \
        #       {lines}")

        # Check for intersections
        lines_ints = lines.copy()
        intersections = []
        for i in range(len(lines_ints)):
            for j in range(i + 1, len(lines_ints)):
                if self.do_lines_intersect(lines_ints[i], lines_ints[j]):
                    intersections.append((lines_ints[i], lines_ints[j]))
                    # lines.remove(lines[i])
                    # lines.remove(lines[j])

        # Remove lines that are part of intersections
        for line1, line2 in intersections:
            if line1 in lines:
                lines.remove(line1)
            # if line2 in lines:
            #     lines.remove(line2)

        lines_with_color = []
        for line in lines:
            color = tuple(np.random.randint(0, 256, 3))
            line_with_color = (*line, color)
            lines_with_color.append(line_with_color)

        
        sorted_lines_with_color = sorted(lines_with_color, key=lambda entry: entry[0][1])
        # print(sorted_lines_with_color)

        # Visualize lines on the original mask
        plt.figure(figsize=(8, 8))
        plt.imshow(mask, cmap='gray')
        
        for i, ((x0, y0), (x1, y1), ang, color) in enumerate(sorted_lines_with_color):

            plt.plot((x0, x1), (y0, y1), color=np.array(color) / 255)
            
            ang = np.pi/2 + ang  
            ang = round(ang, 4)
            ang = np.rad2deg(ang)
            
            self.updateAngleTextBox([ang], i, color=f'rgb({color[0]},{color[1]},{color[2]})')

        plt.title('Detected Lines')
        plt.savefig("hough_lines.png", bbox_inches='tight', pad_inches=0)
        plt.show()  # Display the plot
        plt.close()
    
        # Draw the detected lines on the qimage mask
        # image_with_lines = self.image_mask.copy()
        image_with_lines = self.image_cropped.copy()
        painter = QPainter(image_with_lines)
        pen = QPen(Qt.red, 5)

        # with QPainter(image_with_lines) as painter:
        for ((x0, y0), (x1, y1), _, color) in sorted_lines_with_color:
            # color = colors.pop(0)          
            pen.setColor(QColor(color[0], color[1], color[2]))
            painter.setPen(pen)
            painter.drawLine(x0, y0, x1, y1)

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

        # self.image_mask = image_with_lines
        self.image_cropped = image_with_lines

        # self.viewer.setOpacity(0.5)
        # self.viewer.setOverlayImage(self.image_mask)


    # Function to check if two line segments intersect
    def do_lines_intersect(self, line1, line2):
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        A, B, _ = line1
        C, D, _ = line2
        A, B, _ = line1
        C, D, _ = line2
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)
