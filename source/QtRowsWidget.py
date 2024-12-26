import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QSizePolicy
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import pyqtSignal, Qt
import numpy as np
import cv2
from source import genutils
from source.QtImageViewer import QtImageViewer

from skimage.transform import hough_line, hough_line_peaks
from scipy.interpolate import interp1d

from skimage.draw import line
from PyQt5.QtGui import QPainter, QPen, QBrush
import matplotlib.pyplot as plt

from skimage import measure
from skimage.morphology import skeletonize
from scipy.spatial import KDTree



class RowsWidget(QWidget):

    closeRowsWidget = pyqtSignal()

    # def __init__(self, image_cropped, created_blobs, offset, parent=None):
    def __init__(self, image_mask,  cropped_image, mask_array, blobs, rect, parent = None):
        super(RowsWidget, self).__init__(parent)

        i = 0
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

        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.closeWidget)
        layout.addWidget(self.btnClose)
        
        self.setLayout(layout)
            
        # self.q_image = genutils.rgbToQImage(self.image_cropped)
        # self.viewer.setImg(self.image_cropped)
        self.houghTansformation(self.maschera, i)

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

    def houghTansformation(self, mask, i):
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
                        lines.append(((0, int(y0)), (width, int(y1))))

            except ZeroDivisionError:
                # Handle cases where sin(angle) is zero (e.g., vertical lines)
                continue

        # # Group lines that intersect each other
        # grouped_lines = []
        # used_lines = set()
        # for i, line1 in enumerate(lines):
        #     if i in used_lines:
        #         continue
        #     group = [line1]
        #     for j, line2 in enumerate(lines):
        #         if i != j and j not in used_lines:
        #             if self.lines_intersect(line1, line2):
        #                 group.append(line2)
        #                 used_lines.add(j)
        #     grouped_lines.append(group)
        #     used_lines.add(i)
        # print(grouped_lines)

        # # Interpolate a single line through the intersection points of each group
        # plt.figure(figsize=(8, 8))
        # plt.imshow(mask, cmap='gray')
        # for group in grouped_lines:
        #     if len(group) > 1:
        #         intersection_points = []
        #         for line in group:
        #             intersection_points.append(line[0])
        #             intersection_points.append(line[1])
        #         intersection_points = np.array(intersection_points)
        #         intersection_points = intersection_points[np.argsort(intersection_points[:, 0])]
        #         x = intersection_points[:, 0]
        #         y = intersection_points[:, 1]
        #         f = interp1d(x, y, kind='linear', fill_value='extrapolate')
        #         plt.plot(x, f(x), '-r')
        #     else:
        #         (x0, y0), (x1, y1) = group[0]
        #         plt.plot((x0, x1), (y0, y1), '-r')
        # plt.title('Interpolated Lines')
        # plt.savefig("interpolated_lines.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        # Visualize lines on the original mask
        plt.figure(figsize=(8, 8))
        plt.imshow(mask, cmap='gray')
        for (x0, y0), (x1, y1) in lines:
            plt.plot((x0, x1), (y0, y1), '-r')
        plt.title('Detected Lines')
        # plt.show()
        plt.savefig((f"hough_lines_{str(i)}.png"), bbox_inches='tight', pad_inches=0)
        plt.close()

        plt.figure(figsize=(8, 8))
        plt.imshow(mask, cmap='gray')
        # Draw lines
        for (x0, y0), (x1, y1) in lines:
            plt.plot((x0, x1), (y0, y1), '-r')

        # Draw centroids        
        local_rect = self.rect.boundingRect()
        for blob in self.blob_list:
            centroid = blob.centroid
            plt.plot(centroid[0] - local_rect.left(), centroid[1]-local_rect.top(), 'bo')  # Plot centroids as blue dots

        # plt.title('Mask with Detected Lines and Centroids')
        # plt.savefig("mask_with_centroids.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        for blob in self.blob_list:
            bbox = blob.bbox
            top, left, width, height = bbox
            rect = plt.Rectangle((left - local_rect.left(), top - local_rect.top()), width, height, linewidth=1, edgecolor='g', facecolor='none')
            plt.gca().add_patch(rect)

        plt.title('Mask with Detected Lines, Centroids, and Bounding Boxes')
        plt.savefig("mask_with_centroids_and_bboxes.png", bbox_inches='tight', pad_inches=0)
        plt.close()

        # Draw the detected lines on the qimage mask
        # image_with_lines = self.image_mask.copy()
        image_with_lines = self.image_cropped.copy()
        painter = QPainter(image_with_lines)
        pen = QPen(Qt.red, 5)
        painter.setPen(pen)

        for (x0, y0), (x1, y1) in lines:
            painter.drawLine(x0, y0, x1, y1)

        painter.end()

        # Save the image with lines
        image_with_lines.save("image_with_lines.png")

        # self.image_mask = image_with_lines
        self.image_cropped = image_with_lines

        # self.viewer.setOpacity(0.5)
        # self.viewer.setOverlayImage(self.image_mask)

#####################################################################################################3

    def lines_intersect(line1, line2):
        # Check if two lines intersect
        (x0, y0), (x1, y1) = line1
        (x2, y2), (x3, y3) = line2
        denom = (y3 - y2) * (x1 - x0) - (x3 - x2) * (y1 - y0)
        if denom == 0:
            return False  # Lines are parallel
        ua = ((x3 - x2) * (y0 - y2) - (y3 - y2) * (x0 - x2)) / denom
        ub = ((x1 - x0) * (y0 - y2) - (y1 - y0) * (x0 - x2)) / denom
        return 0 <= ua <= 1 and 0 <= ub <= 1


    def applySkeletonization(self, mask):
        # Apply skeletonization
        skeleton = skeletonize(mask)

        # Visualize the skeleton
        plt.figure(figsize=(8, 8))
        plt.imshow(skeleton, cmap='gray')
        plt.title('Skeletonized Mask')
        plt.savefig("skeletonized_mask.png", bbox_inches='tight', pad_inches=0)
        plt.close()

        # Update the viewer with the skeletonized mask
        # skeleton_image = genutils.numpyArrayToQImage(skeleton.astype(np.uint8) * 255)
        # self.viewer.setOverlayImage(skeleton_image)
        return skeleton

    def connectSkeletonIntersections(self, skeleton):
        # Find intersection points in the skeleton
        intersection_points = self.findIntersectionPoints(skeleton)

        # Create a KDTree for efficient neighbor search
        tree = KDTree(intersection_points)

        # Plot the intersection points and their connections
        plt.figure(figsize=(8, 8))
        plt.imshow(skeleton, cmap='gray')

        for point in intersection_points:
            x0, y0 = point
            # Find neighbors within a radius of 5 rows
            indices = tree.query_ball_point(point, r=10)
            for idx in indices:
                x1, y1 = intersection_points[idx]
                if (x0, y0) != (x1, y1):
                    plt.plot([x0, x1], [y0, y1], '-o', color=np.random.rand(3,))

        plt.title('Skeleton with Intersection Points Connections')
        plt.savefig("intersection_points_connections.png", bbox_inches='tight', pad_inches=0)
        plt.close()
        
        # # Create a copy of the original image to draw on
        # image_with_lines = self.image_mask.copy()
        # painter = QPainter(image_with_lines)
        # pen = QPen(Qt.green, 2)
        # painter.setPen(pen)

        # # Draw lines connecting intersection points
        # for i in range(len(intersection_points) - 1):
        #     x0, y0 = intersection_points[i]
        #     x1, y1 = intersection_points[i + 1]
        #     painter.drawLine(x0, y0, x1, y1)

        # painter.end()

        # # Update the viewer with the new image
        # self.image_mask = image_with_lines
        # self.viewer.setOverlayImage(self.image_mask)

    def findIntersectionPoints(self, skeleton):
        # Find intersection points in the skeleton
        intersection_points = []
        for y in range(1, skeleton.shape[0] - 1):
            for x in range(1, skeleton.shape[1] - 1):
                if skeleton[y, x] == 1:
                    neighbors = skeleton[y-1:y+2, x-1:x+2].sum() - 1
                    if neighbors > 2:
                        intersection_points.append((x, y))
        return intersection_points