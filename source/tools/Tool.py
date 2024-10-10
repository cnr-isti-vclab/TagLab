from PyQt5.QtCore import QObject, pyqtSignal

from source.Blob import Blob

class Tool(QObject):

    # custom signals
    infoMessage = pyqtSignal(str)
    log = pyqtSignal(str)
    blobInfo = pyqtSignal(Blob, str)

    def __init__(self, viewerplus):
        super(Tool, self).__init__()
        self.viewerplus = viewerplus

        # signal-slot connections
        self.log[str].connect(self.viewerplus.logMessage)
        self.blobInfo[Blob, str].connect(self.viewerplus.logBlobInfo)

    def leftPressed(self, x, y, mods = None):
        pass

    def rightPressed(self, x, y, mods = None):
        pass

    def mouseMove(self, x, y, mods = None):
        pass

    def leftReleased(self, x, y):
        pass

    def wheel(self, delta):
        pass

    def apply(self):
        pass