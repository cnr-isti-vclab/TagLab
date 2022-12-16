import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPen, QFont
from PyQt5.QtWidgets import QGraphicsItem
from source.tools.Tool import Tool
from source.Point import Point


class PlaceAnnPoint(Tool):

    def __init__(self, viewerplus):
        super(PlaceAnnPoint, self).__init__(viewerplus)
        self.viewerplus = viewerplus


    def leftPressed(self, x, y, mods):

        print('clicked')

        if mods == Qt.ShiftModifier:
            point = Point(x, y, "Empty", self.viewerplus.annotations.getFreePointId())
            self.viewerplus.annotations.addPoint(point)
            self.viewerplus.addBlob(point, True)



