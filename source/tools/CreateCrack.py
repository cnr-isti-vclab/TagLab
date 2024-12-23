from source.QtCrackWidget import QtCrackWidget
from PyQt5.QtCore import Qt, pyqtSlot

from source.tools.Tool import Tool

class CreateCrack(Tool):
    def __init__(self, viewerplus):
        super(CreateCrack, self).__init__(viewerplus)

    def leftPressed(self, x, y, mods):

        selected_blob = self.viewerplus.annotations.clickedBlob(x, y)
        if selected_blob is None:
            return

        is_visible = self.viewerplus.project.isLabelVisible(selected_blob.class_name)
        if is_visible is False:
            return

        self.viewerplus.resetSelection()
        self.viewerplus.addToSelectedList(selected_blob)

        #cracWidget needs to be in Viewerplus for resetTools()
        crackWidget = self.viewerplus.crackWidget
        if crackWidget is None:
            # copy blob, for undo reasons.
            blob = selected_blob.copy()
            self.blobInfo.emit(blob, "[TOOL][CREATECRACK][BLOB-SELECTED]")

            crackWidget = QtCrackWidget(self.viewerplus.img_map, self.viewerplus.annotations, blob, x, y, parent=self.viewerplus)
            crackWidget.setWindowModality(Qt.WindowModal)
            crackWidget.btnCancel.clicked.connect(self.crackCancel)
            crackWidget.btnApply.clicked.connect(self.crackApply)
            crackWidget.closeCrackWidget.connect(self.crackCancel)
            crackWidget.show()
            self.viewerplus.crackWidget = crackWidget


    @pyqtSlot()
    def crackCancel(self):
        self.viewerplus.resetTools()

    @pyqtSlot()
    def crackApply(self):

        new_blobs = self.viewerplus.crackWidget.apply()
        self.blobInfo.emit(self.viewerplus.selected_blobs[0], "[TOOL][CREATECRACK][BLOB-SELECTED]")
        #self.viewerplus.removeBlob(self.viewerplus.selected_blobs[0])

        if len(new_blobs) == 1:
            self.viewerplus.updateBlob(self.viewerplus.selected_blobs[0], new_blobs[0])
            self.blobInfo.emit(new_blobs[0], "[TOOL][CREATECRACK][BLOB-EDITED]")
        else:
            self.viewerplus.removeBlob(self.viewerplus.selected_blobs[0])
            for blob in new_blobs:
                self.viewerplus.addBlob(blob, selected=True)
                self.blobInfo.emit(blob, "[TOOL][CREATECRACK][BLOB-EDITED]")

            self.viewerplus.project.updateCorrespondences("CRACK", new_blobs, self.viewerplus.selected_blobs[0], "")

        self.viewerplus.saveUndo()
        self.crackCancel()



