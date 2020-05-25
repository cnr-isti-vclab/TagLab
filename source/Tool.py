from PyQt5.QtCore import pyqtSignal

from source.Blob import Blob

class Tool(object):
    def __init__(self, viewerplus):
        self.viewerplus = viewerplus

        infoMessage = pyqtSignal(str)
        log = pyqtSignal(str)
        blobInfo = pyqtSignal(Blob, str)

    def leftPressed(self, x, y):
        pass

    def mouseMove(self, x, y):
        pass

    def leftReleased(self, x, y):
        pass