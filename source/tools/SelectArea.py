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
        self.released_flag = True
        self.area_style = None

        self.image_width = 0
        self.image_height = 0

    def reset(self):

        self.pick_points.reset()
        self.selected_area_rect = None

    def leftPressed(self, x, y, mods):

        points = self.pick_points.points

        # first point
        if self.released_flag:
            self.pick_points.reset()
            self.selected_area_rect = None
            self.released_flag = False

            self.pick_points.points.append(np.array([x, y]))
            self.pick_points.points.append(np.array([x, y]))

    def leftReleased(self, x, y):

        self.released_flag = True
        self.drawArea()
        self.released.emit()

    def mouseMove(self, x, y):

        if len(self.pick_points.points) > 0:
            self.pick_points.points[1][0] = x
            self.pick_points.points[1][1] = y

            # draw the selected area
            self.drawArea()

            # notify that the selected area is changed
            x, y, w, h = self.fromPointsToArea()
            self.rectChanged.emit(x, y, w, h)

    def setImageSize(self, w, h):
        """
        Set the image size to calculate the maximum admissible area of the selection.
        """

        self.image_width = w
        self.image_height = h

    def fromPointsToArea(self):
        """
        It transforms the picked points into the selected area.
        """

        p1 = self.pick_points.points[0]
        p2 = self.pick_points.points[1]

        x = min(p1[0], p2[0])
        y = min(p1[1], p2[1])
        w = abs(p2[0] - p1[0])
        h = abs(p2[1] - p1[1])

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x + w > self.image_width:
            w = self.image_width - x
        if y + h > self.image_height:
            h = self.image_height - y

        return x, y, w, h

    def setWorkingAreaStyle(self, pen):

        self.working_area_style = pen

    def setAreaStyle(self, style_name):

        if style_name == "WORKING":
            self.area_style = self.working_area_style
        elif style_name == "EXPORT_DATASET":
            self.area_style = QPen(Qt.magenta, 3, Qt.DashLine)
        elif style_name == "SAMPLING_AREA":
            self.area_style = QPen(Qt.yellow, 2, Qt.DashLine)
        elif style_name == "PREVIEW":
            self.area_style = QPen(Qt.white, 3, Qt.DotLine)
        else:
            self.area_style = QPen(Qt.white, 3, Qt.DashLine)

        self.area_style.setCosmetic(True)

    @pyqtSlot(int, int, int, int)
    def setSelectionRectangle(self, x, y, w, h):

        self.pick_points.reset()
        self.pick_points.points.append(np.array([x, y]))
        self.pick_points.points.append(np.array([x + w, y + h]))

        self.drawArea()

    def drawArea(self):

        if self.area_style is not None:

            x, y, w, h = self.fromPointsToArea()

            if self.selected_area_rect is None:
                self.selected_area_rect = self.scene.addRect(x, y, w, h, self.area_style)
                self.selected_area_rect.setZValue(6)
                self.selected_area_rect.setVisible(True)

                self.pick_points.markers.append(self.selected_area_rect)
            else:
                self.selected_area_rect.setRect(x, y, w, h)






