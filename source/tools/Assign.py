from source.tools.Tool import Tool

class Assign(Tool):
    def __init__(self, viewerplus):
        super(Assign, self).__init__(viewerplus)
        self.active_label = None


    def setActiveLabel(self, label):

        self.active_label = label


    def leftPressed(self, x, y, mods):

        if self.active_label is None:
            return #do nothing, no label is set

        selected_blob = self.viewerplus.annotations.clickedBlob(x, y)

        if selected_blob is not None:
            self.viewerplus.addToSelectedList(selected_blob)
            for blob in self.viewerplus.selected_blobs:
                self.viewerplus.setBlobClass(blob, self.active_label)

            message ="[TOOL][ASSIGN] Blob(s) assigned ({:d}) (CLASS={:s}).".format(len(self.viewerplus.selected_blobs), self.active_label)
            self.viewerplus.logfile.info(message)

            self.viewerplus.saveUndo()
            self.viewerplus.resetSelection()