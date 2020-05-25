from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from source.Tool import Tool

class Cut(Tool):
    def __init__(self, viewerplus, edit_points):
        Tool.__init__(self, viewerplus)

        self.edit_points = edit_points

    def leftPressed(self, x, y):
        if self.edit_points.startDrawing(x, y):
            self.log.emit("[TOOL][EDITBORDER] DRAWING starts..")

    def mouseMove(self, x, y):
        self.edit_points.move(x, y)
