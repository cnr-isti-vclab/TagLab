import numpy as np

from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QImageReader, QFont
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsItem, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

class EditPoints(object):
    def __init__(self, scene):

        self.scene = scene
        self.points = []

        self.border_pen = QPen(Qt.black, 3)
        #        pen.setJoinStyle(Qt.MiterJoin)
        #        pen.setCapStyle(Qt.RoundCap)
        self.border_pen.setCosmetic(True)

        self.qpath_gitem = self.scene.addPath(QPainterPath(), self.border_pen)
        self.last_editborder_points = []

    def reset(self):
        self.qpath_gitem.setPath(QPainterPath())
        self.points = []


    #return true if the first points for a tool
    def startDrawing(self, x, y):

        first_start = False
        if len(self.points) == 0:  # first point, initialize
            self.qpath_gitem = self.scene.addPath(QPainterPath(), self.border_pen)
            first_start = True

#            message = "[TOOL][" + self.tool + "] DRAWING starts.."
#            logfile.info(message)

        self.points.append(np.array([[x, y]]))

        path = self.qpath_gitem.path()
        path.moveTo(QPointF(x, y))
        self.qpath_gitem.setPath(path)
        self.scene.invalidate()

        return first_start

    def move(self, x, y):

        if len(self.edit_points) == 0:
            return
        # check that a move didn't happen before a press
        last_line = self.points[-1]

        last_point = self.points[-1][-1]
        if x != last_point[0] or y != last_point[1]:
            self.points[-1] = np.append(last_line, [[x, y]], axis=0)
            path = self.qpath_gitem.path()
            path.lineTo(QPointF(x, y))
            self.qpath_gitem.setPath(path)
            self.scene.invalidate()