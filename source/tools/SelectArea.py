import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QFont
from PyQt5.QtWidgets import QGraphicsItem
from source.tools.Tool import Tool
from PyQt5.QtCore import pyqtSlot, pyqtSignal


class SelectArea(Tool):

    rectChanged = pyqtSignal(int, int, int, int)
    released = pyqtSignal()

    def __init__(self, viewerplus, pick_points ):
        super(SelectArea, self).__init__(viewerplus)

        self.pick_points = pick_points
        self.scene = viewerplus.scene
        self.selected_area_rect = None

    def leftPressed(self, x, y, mods):

        points = self.pick_points.points

        # first point
        if len(points) == 0:
            self.pick_points.points.append(np.array([x, y]))
            self.pick_points.points.append(np.array([x, y]))
        else:
            self.pick_points.reset()
            self.selected_area_rect = None

    def leftReleased(self, x, y):

        self.released.emit()

    def mouseMove(self, x, y):

        if len(self.pick_points.points) > 0:
            self.pick_points.points[1][0] = x
            self.pick_points.points[1][1] = y

            start = self.pick_points.points[0]
            end = self.pick_points.points[1]

            # draw the selected area
            self.drawArea()

            # notify that the selected area is changed
            self.rectChanged.emit(start[0], start[1], end[0] - start[0], end[1] - start[1])

    def setAreaStyle(self, style_name):

        if style_name == "WORKING":
            self.area_style = QPen(Qt.white, 5, Qt.DashLine)
        elif style_name == "EXPORT_DATASET":
            self.area_style = QPen(Qt.magenta, 5, Qt.DashLine)
        elif style_name == "PREVIEW":
            self.area_style = QPen(Qt.white, 3, Qt.DotLine)
        else:
            self.area_style = QPen(Qt.white, 3, Qt.DashLine)

        self.area_style.setCosmetic(True)

    def drawArea(self):

        x = self.pick_points.points[0][0]
        y = self.pick_points.points[0][1]
        w = self.pick_points.points[1][0] - self.pick_points.points[0][0]
        h = self.pick_points.points[1][1] - self.pick_points.points[0][1]

        if self.selected_area_rect is None:
            self.selected_area_rect = self.scene.addRect(x, y, w, h, self.area_style)
            self.selected_area_rect.setZValue(6)
            self.pick_points.markers.append(self.selected_area_rect)
        else:
            self.selected_area_rect.setVisible(True)
            self.selected_area_rect.setRect(x, y, w, h)






