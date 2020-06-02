from source.tools.Tool import Tool
from source.Blob import Blob

#this class is not actually doing nothing, matching functions live in TagLab.py
class  Match(Tool):
    def __init__(self, viewerplus):
        super(Match, self).__init__(viewerplus)
        self.viewerplus = viewerplus

