from PyQt5.QtCore import Qt

from source.tools.PickPoints import PickPoints
from source.tools.EditPoints import EditPoints
from source.tools.Scribbles import Scribbles
from source.tools.CorrectivePoints import CorrectivePoints

from PyQt5.QtCore import Qt, QObject, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR

import os
import importlib


class _LazyTool:

    def __init__(self, module_name, class_name, *args):
        object.__setattr__(self, "_module_name", module_name)
        object.__setattr__(self, "_class_name", class_name)
        object.__setattr__(self, "_args", args)
        object.__setattr__(self, "_instance", None)

    def _load(self):
        if self._instance is None:
            module = importlib.import_module(self._module_name)
            tool_class = getattr(module, self._class_name)
            object.__setattr__(self, "_instance", tool_class(*self._args))
        return self._instance

    def __getattr__(self, name):
        return getattr(self._load(), name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            setattr(self._load(), name, value)

    def deactivate(self):
        if self._instance is not None:
            self._instance.deactivate()

    def reset(self):
        if self._instance is not None:
            self._instance.reset()

    def enable(self, enabled):
        if enabled:
            self._load().enable(True)
        elif self._instance is not None:
            self._instance.enable(False)

# class Tools(object):
class Tools(QObject):
    
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

            modelName = "sam_vit_h_4b8939"
            models_dir = os.path.join(self.viewerplus.taglab_dir, "models")
            path = os.path.join(models_dir, modelName + '.pth')

            if os.path.exists(path):
                self.SAM_is_available = True

        # DATA FOR THE CREATECRACK TOOL
        self.crackWidget = None
        

    def createTools(self):
        # TOOLS - create all the tools
        self.tools = {
            "CREATECRACK": _LazyTool("source.tools.CreateCrack", "CreateCrack", self.viewerplus),
            "SPLITBLOB": _LazyTool("source.tools.SplitBlob", "SplitBlob", self.viewerplus, self.pick_points),
            "ASSIGN": _LazyTool("source.tools.Assign", "Assign", self.viewerplus),
            "EDITBORDER": _LazyTool("source.tools.EditBorder", "EditBorder", self.viewerplus, self.edit_points),
            "CUT": _LazyTool("source.tools.Cut", "Cut", self.viewerplus, self.edit_points),
            "FREEHAND": _LazyTool("source.tools.Freehand", "Freehand", self.viewerplus, self.edit_points),
            "WATERSHED": _LazyTool("source.tools.Watershed", "Watershed", self.viewerplus, self.scribbles),
            # "BRICKS": BricksSegmentation(self.viewerplus),
            "RULER": _LazyTool("source.tools.Ruler", "Ruler", self.viewerplus, self.pick_points),
            "FOURCLICKS": _LazyTool("source.tools.FourClicks", "FourClicks", self.viewerplus, self.pick_points),
            "PLACEANNPOINT": _LazyTool("source.tools.PlaceAnnPoint", "PlaceAnnPoint", self.viewerplus),
            "MATCH": _LazyTool("source.tools.Match", "Match", self.viewerplus),
            "SELECTPOINTS": _LazyTool("source.tools.SelectPoints", "SelectPoints", self.viewerplus, self.pick_points),
            "SELECTAREA": _LazyTool("source.tools.SelectArea", "SelectArea", self.viewerplus, self.pick_points),
            "RITM": _LazyTool("source.tools.Ritm", "Ritm", self.viewerplus, self.corrective_points),
            "ROWS": _LazyTool("source.tools.Rows", "Rows", self.viewerplus),
        }
        if self.SAM_is_available:   #just if SAM is available
            self.tools["SAM"] = _LazyTool("source.tools.Sam", "Sam", self.viewerplus, self.pick_points)
            self.tools["SAMINTERACTIVE"] = _LazyTool("source.tools.SAMInteractive", "SAMInteractive", self.viewerplus, self.pick_points)


    def setTool(self, tool):
        # Deactivate the current tool before switching
        if self.tool in self.tools:
            self.tools[self.tool].deactivate()
        
        self.resetTools()      
        self.tool = tool
        
        # Activate the new tool
        if self.tool in self.tools:
            self.tools[self.tool].activate()


    def resetTools(self):
        # reset all helpers
        self.pick_points.reset()
        self.edit_points.reset()
        self.scribbles.reset()
        self.corrective_points.reset()
        # invalidate scene
        self.scene.invalidate(self.scene.sceneRect())
        # reset each tool
        self.tools["FOURCLICKS"].reset()
        self.tools["RITM"].reset()
        self.tools["SELECTPOINTS"].reset()
        self.tools["SELECTAREA"].reset()
        self.tools["WATERSHED"].reset()
        self.tools["ROWS"].reset()
        if self.SAM_is_available:
            self.tools["SAM"].reset()
            self.tools["SAMINTERACTIVE"].reset()
        # stop autoclassification
        if self.tool == "AUTOCLASS":
            self.corals_classifier.stopProcessing()
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


    def enableSAMInteractive(self):
        if self.SAM_is_available:
            self.tools["SAMINTERACTIVE"].enable(True)
    def disableSAMInteractive(self):
        if self.SAM_is_available:
            self.tools["SAMINTERACTIVE"].enable(False)

    # def enableRows(self):
    #     # if self.SAM_is_available:
    #     self.tools["ROWS"].enable(True)
    # def disableRows(self):
    #     # if self.SAM_is_available:
    #     self.tools["ROWS"].enable(False)
    

    def enableRITM(self):
            self.tools["RITM"].enable(True)
    def disableRITM(self):
            self.tools["RITM"].enable(False)
            
    def leftPressed(self, x, y, mods=None):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].leftPressed(x, y, mods)

    def rightPressed(self, x, y, mods=None):
        if self.tool == "MOVE":
            return        
        self.tools[self.tool].rightPressed(x, y, mods)

    def mouseMove(self, x, y, mods=None):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].mouseMove(x, y, mods)

    def leftReleased(self, x, y):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].leftReleased(x, y)

    def rightReleased(self, x, y):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].rightReleased(x, y)

    def wheel(self, delta, mods=None):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].wheel(delta, mods)

    def applyTool(self):
        if self.tool == "MOVE":
            return
        self.tools[self.tool].apply()






