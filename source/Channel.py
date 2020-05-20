
class Channel(Object):
    def __init__(self):
        self.filepath = None                     #relative (TO WHAT?) path to the image
        self.type = None                         #[rgb | dem]
        self.qimage = None                         #store QImage here for visualization


    def load(self):
        pass

    def unload(self):
        pass