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

        message = "<p><i>Place an annotation point</i></p>"
        message += "<p>- SHIFT + LMB to place the point</p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'

    def activate(self):
        self.viewerplus.showMessage(self.tool_message)

    def deactivate(self):
        self.viewerplus.clearMessage()

    def leftPressed(self, x, y, mods):


        if mods == Qt.ShiftModifier:
            point = Point(x, y, "Empty", self.viewerplus.annotations.getFreePointId())
            self.viewerplus.drawPointAnn(point)
            self.viewerplus.addBlob(point, True)



