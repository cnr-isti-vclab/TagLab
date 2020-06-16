import numpy as np
from skimage.measure import points_in_poly

from PyQt5.QtCore import Qt, pyqtSignal

from source.tools.Tool import Tool

class SplitBlob(Tool):
    def __init__(self, viewerplus, pick_points):
        super(SplitBlob, self).__init__(viewerplus)

        self.pick_points = pick_points

        self.CROSS_LINE_WIDTH = 2
        self.pick_style   = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}

        infoMessage = pyqtSignal(str)

    def leftPressed(self, x, y, mods):
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

        condition = points_in_poly(np.array([[x, y]]), self.viewerplus.selected_blobs[0].contour)
        if condition[0] != True:
            self.infoMessage.emit("Click on the selected area to split.")
            return

        self.pick_points.addPoint(x, y, self.pick_style)

    def apply(self):
        selected_blob = self.viewerplus.selected_blobs[0]
        points = self.pick_points.points

        self.viewerplus.removeBlob(selected_blob)
        created_blobs = self.viewerplus.annotations.splitBlob(self.viewerplus.img_map, selected_blob, points)

        self.blobInfo.emit(selected_blob, "[TOOL][SPLITBLOB][BLOB-SELECTED]")

        for blob in created_blobs:
            self.viewerplus.addBlob(blob, selected=True)
            self.blobInfo.emit(blob, "[TOOL][SPLITBLOB][BLOB-CREATED]")

        self.log.emit("[TOOL][SPLITBLOB] Operation ends.")

        self.viewerplus.saveUndo()
        self.viewerplus.resetTools()