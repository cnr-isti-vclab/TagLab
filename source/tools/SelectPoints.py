import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QFont
from PyQt5.QtWidgets import QGraphicsItem
from snuggs import number

from source.tools.Tool import Tool
from PyQt5.QtCore import pyqtSlot, pyqtSignal


class SelectPoints(Tool):
    """
    Tool to select N points on the orthoimage.
    """

    lastSelectedPoint = pyqtSignal(float, float)

    def __init__(self, viewerplus, pick_points):
        super(SelectPoints, self).__init__(viewerplus)

        self.pick_points = pick_points
        self.N_points = 1
        self.idx_points = 0
        self.scene = viewerplus.scene

        self.image_width = 0
        self.image_height = 0

        self.CROSS_LINE_WIDTH = 2
        self.pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}

    def reset(self):

        self.pick_points.reset()
        self.selected_points = []

    def leftPressed(self, x, y, mods):

        points = self.pick_points.points

        if x >= 0 and y >= 0 and x < self.image_width and self.image_height:

            if len(points) < self.N_points:
                self.pick_points.points.append(np.array([x, y]))
                self.idx_points += 1
                self.drawSelectedPoints()
            else:
                self.idx_points = self.idx_points % self.N_points
                self.pick_points.points[self.idx_points] = np.array([x, y])
                self.idx_points += 1
                self.drawSelectedPoints()

            self.lastSelectedPoint.emit(x, y)

    def setNumberOfPointsToSelect(self, number_of_points):
        """
        Set the number of points to select.
        """
        self.N_points = number_of_points
        self.idx_points = 0
        self.pick_points.reset()
        self.drawSelectedPoints()

    def setImageSize(self, w, h):
        """
        Set the image size to assign points correctly.
        """
        self.image_width = w
        self.image_height = h

    @pyqtSlot(int, int)
    def setPoints(self, idx, point):

        x = point[0]
        y = point[1]

        if x >= 0 and y >= 0 and x < self.image_width and y < self.image_height:
            self.pick_points.points[idx] = np.array([x, y])
            self.drawSelectedPoints()

    def drawSelectedPoints(self):

        points = self.pick_points.points.copy()

        self.pick_points.reset()

        # add points and draw them
        for pt in points:
            self.pick_points.addPoint(pt[0], pt[1], self.pick_style)






