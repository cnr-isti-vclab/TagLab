from PyQt5.QtCore import Qt

from source.tools.PickPoints import PickPoints
from source.tools.EditPoints import EditPoints
from source.tools.Scribbles import Scribbles
from source.tools.CorrectivePoints import CorrectivePoints


from source.tools.CreateCrack import CreateCrack
from source.tools.SplitBlob import SplitBlob
from source.tools.Assign import Assign
from source.tools.EditBorder import EditBorder
from source.tools.Watershed import Watershed
from source.tools.BricksSegmentation import BricksSegmentation
from source.tools.Cut import Cut
from source.tools.Freehand import Freehand
from source.tools.Ruler import Ruler
from source.tools.FourClicks import FourClicks
from source.tools.Match import Match
from source.tools.SelectArea import SelectArea
from source.tools.Ritm import Ritm
from source.tools.Sam import Sam
from source.tools.SamInteractive import SamInteractive

from source.tools.PlaceAnnPoint import PlaceAnnPoint



class Tools(object):
    def __init__(self, viewerplus):

        self.tool = "MOVE"
        self.scene = viewerplus.scene
        self.viewerplus = viewerplus

        self.pick_points = PickPoints(self.scene)
        self.edit_points = EditPoints(self.scene)
        self.scribbles = Scribbles(self.scene)
        self.corrective_points = CorrectivePoints(self.scene)

        self.CROSS_LINE_WIDTH = 2
        self.extreme_pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.red,  'size': 6}

        # DATA FOR THE CREATECRACK TOOL
        self.crackWidget = None

    def createTools(self):
        # TOOLS - create all the tools
        self.tools = {
            "CREATECRACK": CreateCrack(self.viewerplus),
            "SPLITBLOB": SplitBlob(self.viewerplus, self.pick_points),
            "ASSIGN": Assign(self.viewerplus),
            "EDITBORDER": EditBorder(self.viewerplus, self.edit_points),
            "CUT": Cut(self.viewerplus, self.edit_points),
            "FREEHAND": Freehand(self.viewerplus, self.edit_points),
            "WATERSHED": Watershed(self.viewerplus, self.scribbles),
            "BRICKS": BricksSegmentation(self.viewerplus),
            "RULER": Ruler(self.viewerplus, self.pick_points),
            "FOURCLICKS": FourClicks(self.viewerplus, self.pick_points),
            "PLACEANNPOINT": PlaceAnnPoint(self.viewerplus),
            "MATCH": Match(self.viewerplus),
            "SELECTAREA": SelectArea(self.viewerplus, self.pick_points),
            "SAM": Sam(self.viewerplus),
            "SAMINTERACTIVE": SamInteractive(self.viewerplus, self.corrective_points),
            "RITM": Ritm(self.viewerplus, self.corrective_points)
        }
        # connect infomessage, log, blobinfo for   all tools with self.infoWidget.setInfoMessage(

    def setTool(self, tool):
        self.resetTools()
        self.tool = tool

    def resetTools(self):

        self.pick_points.reset()
        self.edit_points.reset()
        self.scribbles.reset()
        self.corrective_points.reset()

        self.scene.invalidate(self.scene.sceneRect())

        self.tools["SAMINTERACTIVE"].reset()
        self.tools["FOURCLICKS"].reset()
        self.tools["RITM"].reset()
        self.tools["SAM"].reset()
        self.tools["SELECTAREA"].reset()

        if self.tool == "AUTOCLASS":
            self.corals_classifier.stopProcessing()

        if self.tool == "WATERSHED":
            self.current_blobs = []

        # close crack widget
        if self.viewerplus.crackWidget is not None:
            self.viewerplus.crackWidget.close()
        self.viewerplus.crackWidget = None

        # close bricks widget
        if self.viewerplus.bricksWidget is not None:
            self.viewerplus.bricksWidget.close()
        self.viewerplus.bricksWidget = None

    #logfile, annotations, selecttion, activelabelbname, undo

    def leftPressed(self, x, y, mods = None):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].leftPressed(x, y, mods)

    def rightPressed(self, x, y, mods = None):
        if self.tool == "RITM" or self.tool == "SAMINTERACTIVE":
            self.tools[self.tool].rightPressed(x, y, mods)

    def mouseMove(self, x, y):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].mouseMove(x, y)

    def leftReleased(self, x, y):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].leftReleased(x, y)

    def wheel(self, delta):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].wheel(delta)

    def applyTool(self):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].apply()





