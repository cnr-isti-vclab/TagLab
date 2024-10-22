from source.tools.Tool import Tool

class Cut(Tool):
    def __init__(self, viewerplus, edit_points):
        super(Cut, self).__init__(viewerplus)

        self.edit_points = edit_points

        message = "<p><i>Divide an existing region</i></p>"
        message += "<p>Double click to select a region</p>"
        message += "<p>- LMB + drag to draw a line that bisects the selected region<br/>\
                    - CTRL + LMB + drag to pan view</p>"
        message += "<p>SPACEBAR to divide the region into two</p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'

    def leftPressed(self, x, y, mods):
        if self.edit_points.startDrawing(x, y):
            self.log.emit("[TOOL][CUT] DRAWING starts..")

    def mouseMove(self, x, y):
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

        self.viewerplus.project.updateCorrespondences("REPLACE", self.viewerplus.image, created_blobs, [selected_blob], "")

        self.log.emit("[TOOL][CUT] Operation ends.")

        self.viewerplus.saveUndo()

        self.viewerplus.resetTools()