
class Channel(object):
    def __init__(self, filename = None, type = None):
        self.filename = filename                     #relative (TO WHAT?) path to the image
        self.type = type                         #[rgb | dem]
        self.qimage = None                         #store QImage here for visualization

    def load(self):
        pass

    def unload(self):
        pass