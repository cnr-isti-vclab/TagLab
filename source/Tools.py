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
from source.tools.PlaceAnnPoint import PlaceAnnPoint

from PyQt5.QtCore import Qt, QObject, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR


import importlib
if importlib.util.find_spec("segment_anything"):
    from source.tools.Sam import Sam

#from source.tools.SamInteractive import SamInteractive


# class Tools(object):
class Tools(QObject):    
    tol_mess = pyqtSignal(str)
    
    def __init__(self, viewerplus):
        
        super(Tools, self).__init__()  # Call the QObject constructor

        self.tool = "MOVE"
        self.scene = viewerplus.scene
        self.viewerplus = viewerplus

        self.pick_points = PickPoints(self.scene)
        self.edit_points = EditPoints(self.scene)
        self.scribbles = Scribbles(self.scene)
        self.corrective_points = CorrectivePoints(self.scene)

        self.CROSS_LINE_WIDTH = 2
        self.extreme_pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.red,  'size': 6}

        self.SAM_is_available = False
        if importlib.util.find_spec("segment_anything"):
            self.SAM_is_available = True

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
            # "BRICKS": BricksSegmentation(self.viewerplus),
            "RULER": Ruler(self.viewerplus, self.pick_points),
            "FOURCLICKS": FourClicks(self.viewerplus, self.pick_points),
            "PLACEANNPOINT": PlaceAnnPoint(self.viewerplus),
            "MATCH": Match(self.viewerplus),
            "SELECTAREA": SelectArea(self.viewerplus, self.pick_points),
            "RITM": Ritm(self.viewerplus, self.corrective_points),
            #"SAMINTERACTIVE": SamInteractive(self.viewerplus, self.corrective_points),
        }

        if self.SAM_is_available:
            self.tools["SAM"] = Sam(self.viewerplus)

    def setTool(self, tool):
        self.resetTools()      
        self.tool = tool

    def resetTools(self):

        self.pick_points.reset()
        self.edit_points.reset()
        self.scribbles.reset()
        self.corrective_points.reset()

        self.scene.invalidate(self.scene.sceneRect())

        self.tools["FOURCLICKS"].reset()
        self.tools["RITM"].reset()
        self.tools["SELECTAREA"].reset()

        if self.SAM_is_available:
            self.tools["SAM"].reset()
            #self.tools["SAMINTERACTIVE"].reset()

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

    def enableSAM(self):
        if self.SAM_is_available:
            self.tools["SAM"].enable(True)

    def disableSAM(self):
        if self.SAM_is_available:
            self.tools["SAM"].enable(False)
      
    #QUIRINO: method to select tools for tool message window      
    def toolMessage(self):
        if self.tool == "WATERSHED" or self.tool == "SAM" or self.tool == "RITM"\
              or self.tool == "FREEHAND" or self.tool == "BRICKS" or self.tool == "FOURCLICKS":
            self.tol_mess.emit(self.tools[self.tool].tool_message)
        else:
            self.tol_mess.emit(None)
            

    def leftPressed(self, x, y, mods = None):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].leftPressed(x, y, mods)

    def rightPressed(self, x, y, mods = None):
        if self.tool == "RITM" or self.tool == "SAMINTERACTIVE" or self.tool == "WATERSHED":
            self.tools[self.tool].rightPressed(x, y, mods)

    def mouseMove(self, x, y, mods = None):
        if self.tool == "MOVE":
            return
        if self.tool == "WATERSHED" or self.tool == "FREEHAND" or self.tool == "EDITBORDER":
            self.tools[self.tool].mouseMove(x, y, mods)
        else:
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





