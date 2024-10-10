from source.tools.Tool import Tool
from PyQt5.QtCore import Qt

class Cut(Tool):
    def __init__(self, viewerplus, edit_points):
        super(Cut, self).__init__(viewerplus)

        self.edit_points = edit_points

    def leftPressed(self, x, y, mods):
        if mods == Qt.ShiftModifier:

            if self.edit_points.startDrawing(x, y):
                self.log.emit("[TOOL][EDITBORDER] DRAWING starts..")

    def mouseMove(self, x, y, mods):
        if mods == Qt.ShiftModifier:
            self.edit_points.move(x, y)

    def apply(self):
        points = self.edit_points.points
        if len(points) == 0:
            self.infoMessage.emit("You need to draw something for this operation.")
            return


        if len(self.viewerplus.selected_blobs) != 1:
            self.infoMessage.emit("A single selected area is required.")
            return

        selected_blob = self.viewerplus.selected_blobs[0]
        created_blobs = self.viewerplus.annotations.cut(selected_blob, points)

        self.blobInfo.emit(selected_blob, "[TOOL][CUT][BLOB-SELECTED]")

        self.viewerplus.removeBlob(selected_blob)
        for blob in created_blobs:
            self.viewerplus.addBlob(blob, selected=True)
            self.blobInfo.emit(blob, "[TOOL][CUT][BLOB-CREATED]")

        self.log.emit("[TOOL][CUT] Operation ends.")

        self.viewerplus.saveUndo()

        self.viewerplus.resetTools()