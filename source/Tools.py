from PyQt5.QtCore import Qt

from source.tools.PickPoints import PickPoints
from source.tools.EditPoints import EditPoints


from source.tools.CreateCrack import CreateCrack
from source.tools.SplitBlob import SplitBlob
from source.tools.Assign import Assign
from source.tools.EditBorder import EditBorder
from source.tools.Cut import Cut
from source.tools.Freehand import Freehand
from source.tools.Ruler import Ruler
from source.tools.DeepExtreme import DeepExtreme
from source.tools.Match import Match



class Tools(object):
    def __init__(self, viewerplus):

        self.tool = "MOVE"
        self.scene = viewerplus.scene
        self.viewerplus = viewerplus

        self.pick_points = PickPoints(self.scene)
        self.edit_points = EditPoints(self.scene)

        self.CROSS_LINE_WIDTH = 2
        self.extreme_pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.red,  'size': 6}



        # DATA FOR THE CREATECRACK TOOL
        self.crackWidget = None

        #TOOLS OPTIONS
        self.refine_grow = 0.0

    def createTools(self):
        # TOOLS
        self.tools = {
            "CREATECRACK": CreateCrack(self.viewerplus),
            "SPLITBLOB": SplitBlob(self.viewerplus, self.pick_points),
            "ASSIGN": Assign(self.viewerplus),
            "EDITBORDER": EditBorder(self.viewerplus, self.edit_points),
            "CUT": Cut(self.viewerplus, self.edit_points),
            "FREEHAND": Freehand(self.viewerplus, self.edit_points),
            "RULER": Ruler(self.viewerplus, self.pick_points),
            "DEEPEXTREME": DeepExtreme(self.viewerplus, self.pick_points),
            "MATCH": Match(self.viewerplus)
        }
        # connect infomessage, log, blobinfo for   all tools with self.infoWidget.setInfoMessage(

    def setTool(self, tool):
        self.resetTools()
        self.tool = tool

    def resetTools(self):
        self.pick_points.reset()
        self.edit_points.reset()

        self.scene.invalidate(self.scene.sceneRect())

        if self.viewerplus.crackWidget is not None:
            self.viewerplus.crackWidget.close()
        self.viewerplus.crackWidget = None

        if self.tool == "AUTOCLASS":
            self.corals_classifier.stopProcessing()


    #logfile, annotations, selecttion, activelabelbname, undo
    def leftPressed(self, x, y):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].leftPressed(x, y)

    def mouseMove(self, x, y):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].mouseMove(x, y)

    def leftReleased(self, x, y):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].leftReleased(x, y)

    def applyTool(self):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].apply()





