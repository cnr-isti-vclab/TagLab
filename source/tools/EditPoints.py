import numpy as np

from PyQt5.QtCore import Qt, QObject, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QImageReader, QFont
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsItem, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

class EditPoints(QObject):

    log = pyqtSignal(str)

    def __init__(self, scene):
        super(EditPoints, self).__init__()

        self.scene = scene
        self.points = []

        self.border_pen = QPen(Qt.black, 3)
        #        pen.setJoinStyle(Qt.MiterJoin)
        #        pen.setCapStyle(Qt.RoundCap)
        self.border_pen.setCosmetic(True)

        self.qpath_gitem = self.scene.addPath(QPainterPath(), self.border_pen)
        self.qpath_gitem.setZValue(5)
        self.last_editborder_points = []
        self.last_blob = None

    def reset(self):
        self.qpath_gitem.setPath(QPainterPath())
        self.points = []


    #return true if the first points for a tool
    def startDrawing(self, x, y):

        first_start = False
        if len(self.points) == 0:  # first point, initialize
            self.qpath_gitem.setPath(QPainterPath())
            first_start = True

            message = "[TOOL] DRAWING starts.."
            self.log.emit(message)

        self.points.append(np.array([[x, y]]))

        path = self.qpath_gitem.path()
        path.moveTo(QPointF(x, y))
        self.qpath_gitem.setPath(path)
        self.scene.invalidate()

        return first_start

    def move(self, x, y):

        if len(self.points) == 0:
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

#return false if nothing to undo remains.
    def undo(self):
        if len(self.points) == 0:
            return False

        self.points.pop()

        path = QPainterPath()
        for line in self.points:
            if len(line) == 0:
                continue
            path.moveTo(QPointF(line[0][0], line[0][1]))

            for point in line:
                path.lineTo(QPointF(point[0], point[1]))

        self.qpath_gitem.setPath(path)
        self.scene.invalidate()        
        return True