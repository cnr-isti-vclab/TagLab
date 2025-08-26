from source.tools.Tool import Tool
from source.Blob import Blob

from PyQt5.QtCore import Qt

class Freehand(Tool):
    def __init__(self, viewerplus, edit_points):
        super(Freehand, self).__init__(viewerplus)
        self.viewerplus = viewerplus
        self.edit_points = edit_points

        message = "<p><i>Segment by drawing a CLOSED curve on the map</i></p>"
        message += "<p>- SHIFT + LMB to draw</p>"
        message += "<p>SPACEBAR to apply segmentation</p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'

    def leftPressed(self, x, y, mods):
        if mods == Qt.ShiftModifier:
            if self.edit_points.startDrawing(x, y):
                self.log.emit("[TOOL][FREEHAND] DRAWING starts..")

    def mouseMove(self, x, y, mods=None):
        self.edit_points.move(x, y)

    def apply(self):
        if len(self.edit_points.points) == 0:
            self.infoMessage.emit("You need to draw something for this operation.")
            return

        blob = Blob(None, 0, 0, 0)

        try:
            flagValid = blob.createFromClosedCurve(self.edit_points.points)
        except Exception:
            self.infoMessage.emit("Failed creating area.")
            self.log.emit("[TOOL][FREEHAND] FREEHAND operation not done (invalid snap).")
            return

        if flagValid is True:
            blob.setId(self.viewerplus.annotations.getFreeId())

            self.viewerplus.resetSelection()
            self.viewerplus.addBlob(blob, selected=True)
            self.viewerplus.project.updateCorrespondences("ADD", self.viewerplus.image, [blob], None, "")
            self.blobInfo.emit(blob, "[TOOL][FREEHAND][BLOB-CREATED]")
            self.viewerplus.saveUndo()

            self.log.emit("[TOOL][FREEHAND] Operation ends.")

        else:
            self.log.emit("[TOOL][FREEHAND] Operation ends (INVALID SNAP!).")
            return


        self.viewerplus.resetTools()