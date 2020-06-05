from source.tools.Tool import Tool
from source.Blob import Blob
from PyQt5.QtCore import Qt

#this class is not actually doing nothing, matching functions live in TagLab.py
class  Match(Tool):
    def __init__(self, viewerplus):
        super(Match, self).__init__(viewerplus)
        self.viewerplus = viewerplus

    def leftPressed(self, x, y, mods):
        selected_blob = self.viewerplus.annotations.clickedBlob(x, y)
        if selected_blob is None:
            return
        if mods & Qt.ShiftModifier:
            if selected_blob in self.viewerplus.selected_blobs:
                self.viewerplus.removeFromSelectedList(selected_blob)
            else:
                self.viewerplus.addToSelectedList(selected_blob)
        else:
            self.viewerplus.resetSelection()
            self.viewerplus.addToSelectedList(selected_blob)
            self.viewerplus.updateInfoPanel.emit(selected_blob)
            self.viewerplus.newSelection.emit()

        pass

    def leftReleased(self, x, y):
        pass