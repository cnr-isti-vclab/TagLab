import numpy as np

from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QBrush, QImageReader, QFont
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsItem, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

class CorrectivePoints(object):
    def __init__(self, scene):
        # DATA FOR THE INTERACTIVE CLICK-BASED SEGMENTATION (POSITIVE AND NEGATIVE CLICKS)
        # markers = displayed points on scene
        # pos_neg_clicks = sign of clicked point in order (for the undo operation)
        self.positive_points = []
        self.negative_points = []
        self.markers = []
        self.RADIUS = 7
        self.scene = scene
        self.pos_neg_clicks = []

    def reset(self):
        self.positive_points.clear()
        self.negative_points.clear()
        for marker in self.markers:
            self.scene.removeItem(marker)
        self.markers.clear()

    def addPoint(self, x, y, positive=True):

        if positive:
            self.positive_points.append(np.array([x, y]))
            brush = QBrush(Qt.SolidPattern)
            brush.setColor(Qt.green)
            self.pos_neg_clicks.append("positive")
        else:
            self.negative_points.append(np.array([x, y]))
            brush = QBrush(Qt.SolidPattern)
            brush.setColor(Qt.red)
            self.pos_neg_clicks.append("negative")

        pen = QPen(Qt.white)
        pen.setWidth(1)
        pen.setCosmetic(True)
        point = self.scene.addEllipse(x, y, self.RADIUS, self.RADIUS, pen, brush)
        point.setZValue(5)
        self.markers.append(point)

    def removeLastPoint(self):

        number_of_clicks = self.nclicks()
        if number_of_clicks == 0:
            return

        if len(self.pos_neg_clicks) > 0:
            last_click_type = self.pos_neg_clicks.pop()

        if last_click_type == "positive":
            if len(self.positive_points) > 0:
                self.positive_points.pop()
        else:
            if len(self.negative_points) > 0:
                self.negative_points.pop()

        if len(self.markers) > 0:
            marker = self.markers.pop()
            self.scene.removeItem(marker)

    def nclicks(self):
        # total number of clicked points
        return len(self.positive_points) + len(self.negative_points)
