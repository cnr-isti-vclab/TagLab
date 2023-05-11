import numpy as np

from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QImageReader, QFont
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsItem, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

class PickPoints(object):
    def __init__(self, scene):
        # DATA FOR THE RULER, DEEP EXTREME, RITM, SAM INTERACTIVE, and SPLIT TOOLS
        self.points = []
        self.markers = []
        self.CROSS_LINE_WIDTH = 2
        self.scene = scene

    def reset(self):
        self.points.clear()
        for marker in self.markers:
            self.scene.removeItem(marker)
        self.markers.clear()

    def addPoint(self, x, y, style):
        self.points.append(np.array([x, y]))

        if self.scene is not None:

            pen = QPen(style['color'])
            pen.setWidth(style['width'])
            pen.setCosmetic(True)

            size = style['size']
            point = self.scene.addEllipse(x, y, 0, 0, pen)
            point.setZValue(5)
            line1 = self.scene.addLine(- size, -size, +size, +size, pen)
            line1.setPos(QPointF(x, y))
            line1.setParentItem(point)
            line1.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            line1.setZValue(5)

            line2 = self.scene.addLine(- size, + size, + size, - size, pen)
            line2.setPos(QPointF(x, y))
            line2.setParentItem(point)
            line2.setFlag(QGraphicsItem.ItemIgnoresTransformations)
            line2.setZValue(5)
            # no need to add the lines to the markers, the parent will take care of them
            self.markers.append(point)