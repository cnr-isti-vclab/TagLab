import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QFont
from PyQt5.QtWidgets import QGraphicsItem
from source.tools.Tool import Tool
from PyQt5.QtCore import pyqtSlot, pyqtSignal


class WorkingArea(Tool):
    rectChanged = pyqtSignal(int, int, int, int)
    def __init__(self, viewerplus, pick_points ):
        super(WorkingArea, self).__init__(viewerplus)
        self.pick_points = pick_points
        self.scene = viewerplus.scene
        self.rect = None


    def leftPressed(self, x, y, mods):
        points = self.pick_points.points
        # first point
        if len(points) == 0:
            self.pick_points.points.append(np.array([x, y]))
            self.pick_points.points.append(np.array([x, y]))

        else:
            self.pick_points.reset()

    def mouseMove(self, x, y):

        if len(self.pick_points.points) > 1:
            self.pick_points.points[1][0] = x
            self.pick_points.points[1][1] = y
            self.drawRectangle()



    def drawRectangle(self):

        dragSelectionStyle = QPen(Qt.magenta, 5, Qt.DashLine)
        dragSelectionStyle.setCosmetic(True)
        start = self.pick_points.points[0]
        end = self.pick_points.points[1]

        if self.rect is None:
            self.rect = self.scene.addRect(start[0], start[1], end[0] - start[0], end[1] - start[1], dragSelectionStyle)
            self.rect.setZValue(5)
        else:
            self.rect.setRect(start[0], start[1], end[0] - start[0], end[1] - start[1])

        self.rectChanged.emit(start[0], start[1], end[0] - start[0], end[1] - start[1])





