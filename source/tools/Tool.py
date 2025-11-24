from PyQt5.QtCore import QObject, pyqtSignal

from source.Blob import Blob

class Tool(QObject):
    
    # custom signals
    infoMessage = pyqtSignal(str)
    log = pyqtSignal(str)
    blobInfo = pyqtSignal(Blob, str)

    def __init__(self, viewerplus):
        super(Tool, self).__init__()
        # link to viewerplus
        self.viewerplus = viewerplus
        # instructions and messages
        self.tool_instructions = None
        self.tool_message = None
        # signal-slot connections
        self.log[str].connect(self.viewerplus.logMessage)
        self.blobInfo[Blob, str].connect(self.viewerplus.logBlobInfo)

    # virtual methods
    def activate(self):
        """Called when the tool is activated. Override to show messages and initialize."""
        pass
    
    def deactivate(self):
        """Called when the tool is deactivated. Override to clear messages and cleanup."""
        pass
    
    def leftPressed(self, x, y, mods=None):
        pass
    def rightPressed(self, x, y, mods=None):
        pass
    def mouseMove(self, x, y, mods=None):
        pass
    def leftReleased(self, x, y):
        pass
    def rightReleased(self, x, y):
        pass
    def wheel(self, delta, mods=None):
        pass
    def apply(self):
        pass
    def reset(self):
        pass