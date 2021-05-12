from source.QtBricksWidget import QtBricksWidget
from PyQt5.QtCore import Qt, pyqtSlot
from source.tools.Tool import Tool

class BricksSegmentation(Tool):
    def __init__(self, viewerplus):
        super(BricksSegmentation, self).__init__(viewerplus)

    def leftPressed(self, x, y, mods):

        selected_blob = self.viewerplus.annotations.clickedBlob(x, y)
        if selected_blob is None:
            return

        self.viewerplus.resetSelection()
        self.viewerplus.addToSelectedList(selected_blob)

        if self.viewerplus.bricksWidget is None:
            # copy blob, for undo reasons.
            blob = selected_blob.copy()
            self.setupWidget(blob)

    def setupWidget(self, blob):

        bricksWidget = self.viewerplus.bricksWidget
        if bricksWidget is None:
            bricksWidget = QtBricksWidget(self.viewerplus.img_map, blob, parent=self.viewerplus)
            bricksWidget.setWindowModality(Qt.WindowModal)
            bricksWidget.btnCancel.clicked.connect(self.bricksCancel)
            bricksWidget.btnApply.clicked.connect(self.bricksApply)
            bricksWidget.closeBricksWidget.connect(self.bricksCancel)
            bricksWidget.show()
            self.viewerplus.bricksWidget = bricksWidget


    @pyqtSlot()
    def bricksCancel(self):
        self.viewerplus.resetTools()

    @pyqtSlot()
    def bricksApply(self):

        new_blobs = self.viewerplus.bricksWidget.apply()
        self.blobInfo.emit(self.viewerplus.selected_blobs[0], "[TOOL][CREATECRACK][BLOB-SELECTED]")

        self.viewerplus.removeBlob(self.viewerplus.selected_blobs[0])
        for blob in new_blobs:
            self.viewerplus.addBlob(blob, selected=True)
            self.blobInfo.emit(blob, "[TOOL][CREATECRACK][BLOB-EDITED]")

        self.viewerplus.saveUndo()
        self.bricksCancel()



