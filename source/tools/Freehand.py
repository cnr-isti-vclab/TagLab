from source.tools.Tool import Tool
from source.Blob import Blob

class Freehand(Tool):
    def __init__(self, viewerplus, edit_points):
        super(Freehand, self).__init__(viewerplus)
        self.viewerplus = viewerplus
        self.edit_points = edit_points

    def leftPressed(self, x, y):
        if self.edit_points.startDrawing(x, y):
            self.log.emit("[TOOL][FREEHAND] DRAWING starts..")

    def mouseMove(self, x, y):
        self.edit_points.move(x, y)

    def apply(self):
        print("Apply!")
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
        print("invalid")
        if flagValid is True:
            print("valid")
            blob.setId(self.viewerplus.annotations.progressive_id)
            self.viewerplus.annotations.progressive_id += 1

            self.viewerplus.resetSelection()
            self.viewerplus.addBlob(blob, selected=True)
            self.blobInfo.emit(blob, "[TOOL][FREEHAND][BLOB-CREATED]")
            self.viewerplus.saveUndo()

            self.log.emit("[TOOL][FREEHAND] Operation ends.")

        else:
            self.log.emit("[TOOL][FREEHAND] Operation ends (INVALID SNAP!).")


        self.viewerplus.resetTools()