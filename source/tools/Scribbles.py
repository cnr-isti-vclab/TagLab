import numpy as np

from PyQt5.QtCore import Qt, QObject, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QBrush, QCursor, QColor
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsItem, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

from source.Label import Label

class Scribbles(QObject):
    log = pyqtSignal(str)

    def __init__(self, scene):
        super(Scribbles, self).__init__()

        self.scene = scene
        self.points = []
        self.size = []
        self.current_size = 50

        self.border_pen = QPen(Qt.black, self.current_size)
        self.border_pen.setCapStyle(Qt.RoundCap)
        self.border_pen.setCosmetic(False)

        self.current_label = Label("Background", "Background", description=None, fill=[0, 0, 0])

        self.qpath_gitem = None
        self.qpath_list = []

        self.setCustomCursor()

    def reset(self):

        for qpath_gitem in self.qpath_list:
            qpath_gitem.setPath(QPainterPath())

        self.points = []
        self.label = []
        self.size = []

    def setCustomCursor(self):

        pxmap = QPixmap(self.current_size, self.current_size)
        pxmap.fill(QColor("transparent"))
        painter = QPainter(pxmap)
        color = self.current_label.fill
        brush = QBrush(QColor(color[0], color[1], color[2]))
        painter.setBrush(brush)
        painter.drawEllipse(0, 0, self.current_size, self.current_size)
        painter.end()
        custom_cursor = QCursor(pxmap)
        QApplication.setOverrideCursor(custom_cursor)

    def setLabel(self, label):

        self.current_label = label

        # new cursor color
        color = label.fill
        qt_color = QColor(color[0], color[1], color[2])
        self.border_pen.setColor(qt_color)

        self.setCustomCursor()

    def setSize(self, delta_size):

        new_size = self.current_size + delta_size

        if new_size < 10:
            new_size = 10
        elif new_size > 200:
            new_size = 200

        self.current_size = new_size
        self.border_pen.setWidth(new_size)

        self.setCustomCursor()

    # return true if the first points for a tool
    def startDrawing(self, x, y):

        first_start = False
        if len(self.points) == 0:  # first point, initialize
            first_start = True
            message = "[TOOL] DRAWING starts.."
            self.log.emit(message)

        self.points.append(np.array([[x, y]]))
        self.label.append(self.current_label)
        self.size.append(self.current_size)

        self.qpath_gitem = self.scene.addPath(QPainterPath(), self.border_pen)
        self.qpath_gitem.setZValue(5)

        path = self.qpath_gitem.path()
        path.moveTo(QPointF(x, y))
        self.qpath_list.append(self.qpath_gitem)

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
            path = self.qpath_list[-1].path()
            path.lineTo(QPointF(x, y))
            self.qpath_gitem.setPath(path)
            self.qpath_gitem.setPen(self.border_pen)
            self.scene.invalidate()