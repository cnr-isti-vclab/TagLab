import numpy as np
from skimage.measure import points_in_poly

from source.QtCrackWidget import QtCrackWidget
from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR

from source.PickPoints import PickPoints
from source.Tool import Tool

class SplitBlob(Tool):
    def __init__(self, viewerplus, pick_points):
        Tool.__init__(self, viewerplus)

        self.pick_points = pick_points

        self.CROSS_LINE_WIDTH = 2
        self.pick_style   = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}

        infoMessage = pyqtSignal(str)

    def leftPressed(self, x, y):
        selected_blobs = self.viewerplus.selected_blobs
        # no selected blobs: select it!
        if len(selected_blobs) == 0:
            selected_blob = self.viewerplus.annotations.clickedBlob(x, y)
            if selected_blob is None:
                self.infoMessage.emit("Click on an area to split.")
                return
            self.viewerplus.addToSelectedList(selected_blob)

        if len(selected_blobs) != 1:
            self.infoMessage.emit("A single selected area is required.")
            self.pick_points.reset()
            return

        condition = points_in_poly(np.array([[x, y]]), self.selected_blobs[0].contour)
        if condition[0] != True:
            self.infoMessage.emit("Click on the selected area to split.")
            return

        self.pick_points.addPoint(x, y, self.pick_style)