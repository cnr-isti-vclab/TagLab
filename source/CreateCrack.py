from source.QtCrackWidget import QtCrackWidget
from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR

from source.Tool import Tool

class CreateCrack(Tool):
    def __init__(self, viewerplus):
        Tool.__init__(self, viewerplus)

    def leftPressed(self, x, y):
        selected_blob = self.viewerplus.annotations.clickedBlob(x, y)

        if selected_blob is None:
            return

        self.viewerplus.resetSelection()
        self.viewerplus.addToSelectedList(selected_blob)

        crackWidget = self.viewerplus.crackWidget
        if crackWidget is None:
            # copy blob, for undo reasons.
            blob = selected_blob.copy()
            self.logBlobInfo(blob, "[TOOL][CREATECRACK][BLOB-SELECTED]")

            crackWidget = QtCrackWidget(self.viewerplus.img_map, self.viewerplus.annotations, blob, x, y, parent=self)
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
        self.logBlobInfo(self.viewerplus.selected_blobs[0], "[TOOL][CREATECRACK][BLOB-SELECTED]")
        self.viewerplus.removeBlob(self.viewerplus.selected_blobs[0])
        for blob in new_blobs:
            self.viewerplus.addBlob(blob, selected=True)
            self.logBlobInfo(blob, "[TOOL][CREATECRACK][BLOB-EDITED]")

        self.viewerplus.saveUndo()
        self.crackCancel()



