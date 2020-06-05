from PyQt5.QtCore import QObject, pyqtSignal

from source.Blob import Blob

class Tool(QObject):
    infoMessage = pyqtSignal(str)
    log = pyqtSignal(str)
    blobInfo = pyqtSignal(Blob, str)

    def __init__(self, viewerplus):
        super(Tool, self).__init__()
        self.viewerplus = viewerplus

    def leftPressed(self, x, y, mods = None):
        pass

    def mouseMove(self, x, y):
        pass

    def leftReleased(self, x, y):
        pass

    def apply(self):
        pass