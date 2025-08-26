from source.tools.Tool import Tool
from PyQt5.QtCore import Qt

class EditBorder(Tool):
    def __init__(self, viewerplus, edit_points):
        super(EditBorder, self).__init__(viewerplus)
        self.edit_points = edit_points

        message = "<p><i>Modify the border of an existing region</i></p>"
        message += "<p>Double click to select a region</p>"
        message += "<p>- SHIFT + LMB to draw a line that intersects the border of the selected region</p>"
        message += "<p>SPACEBAR to modify the border</p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'

    def leftPressed(self, x, y, mods):
        if mods == Qt.ShiftModifier:
            if self.edit_points.startDrawing(x, y):
                self.log.emit("[TOOL][EDITBORDER] DRAWING starts..")

    def mouseMove(self, x, y, mods=None):
        self.edit_points.move(x, y)

    def apply(self):
        points = self.edit_points.points
        if len(points) == 0:
            self.infoMessage.emit("You need to draw something for this operation.")
            return

        if len(self.viewerplus.selected_blobs) != 1:
            self.infoMessage.emit("A single selected area is required.")
            self.viewerplus.resetSelection()
            self.viewerplus.resetTools()
            return

        selected_blob = self.viewerplus.selected_blobs[0]

        blob = selected_blob.copy()
        self.edit_points.last_blob = blob
        self.edit_points.last_editborder_points = points
        self.viewerplus.annotations.editBorder(blob, points)

        self.blobInfo.emit(selected_blob, "[TOOL][EDITEDBORDER][BLOB-SELECTED]")
        self.blobInfo.emit(blob, "[TOOL][EDITEDBORDER][BLOB-EDITED]")

        self.log.emit("[TOOL][EDITBORDER] Operation ends.")

        self.viewerplus.updateBlob(selected_blob, blob, selected=True)
        self.viewerplus.saveUndo()

        self.viewerplus.resetTools()
