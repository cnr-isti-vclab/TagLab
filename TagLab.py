# TagLab
# A semi-automatic segmentation tool
#
# Copyright(C) 2019
# Visual Computing Lab
# ISTI - Italian National Research Council
# All rights reserved.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

import sys
import os
import time
import datetime

import json
import numpy as np
import numpy.ma as ma
from skimage import measure
from skimage.measure import points_in_poly

from PyQt5.QtCore import Qt, QSize, QDir, QPoint, QPointF, QTimer, pyqtSlot, pyqtSignal, QSettings, QFileInfo
from PyQt5.QtGui import QPainterPath, QFont, QColor, QPolygonF, QImageReader, QImage, QPixmap, QIcon, QKeySequence, \
    QPen, QBrush, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QDialog, QMenuBar, QMenu, QSizePolicy, QScrollArea, \
    QLabel, QToolButton, QPushButton, QSlider, \
    QMessageBox, QGroupBox, QHBoxLayout, QVBoxLayout, QTextEdit, QLineEdit, QGraphicsView, QAction, QGraphicsItem

# PYTORCH
try:
    import torch
    from torch.nn.functional import upsample
except Exception as e:
    print("Incompatible version between pytorch, cuda and python.\n" +
          "Knowing working version combinations are\n: Cuda 10.0, pytorch 1.0.0, python 3.6.8" + str(e))
   # exit()

from collections import OrderedDict

# DEEP EXTREME
import models.deeplab_resnet as resnet
from models.dataloaders import helpers as helpers

# CUSTOM
from source.QtImageViewerPlus import QtImageViewerPlus
from source.QtMapViewer import QtMapViewer
from source.QtMapSettingsWidget import QtMapSettingsWidget
from source.QtLabelsWidget import QtLabelsWidget
from source.QtInfoWidget import QtInfoWidget
from source.QtHelpWidget import QtHelpWidget
from source.QtProgressBarCustom import QtProgressBarCustom
from source.QtCrackWidget import QtCrackWidget
from source.QtHistogramWidget import QtHistogramWidget
from source.QtClassifierWidget import QtClassifierWidget
from source.QtComparePanel import QtComparePanel
from source.Blob import Blob
from source.Annotation import Annotation
from source.MapClassifier import MapClassifier
from source import utils

# LOGGING
import logging

# configure the logger
now = datetime.datetime.now()
LOG_FILENAME = "tool" + now.strftime("%Y-%m-%d-%H-%M") + ".log"
logging.basicConfig(level=logging.DEBUG, filemode='w', filename=LOG_FILENAME, format = '%(asctime)s %(levelname)-8s %(message)s')
logfile = logging.getLogger("tool-logger")


class TagLab(QWidget):

    def __init__(self, parent=None):
        super(TagLab, self).__init__(parent)

        ##### CUSTOM STYLE #####

        self.setStyleSheet("background-color: rgb(55,55,55); color: white")

        ##### DATA INITIALIZATION AND SETUP #####

        self.TAGLAB_VERSION = "TagLab 0.2"

        # LOAD CONFIGURATION FILE

        f = open("config.json", "r")
        config_dict = json.load(f)
        self.available_classifiers = config_dict["Available Classifiers"]
        self.labels = config_dict["Labels"]

        logfile.info("[INFO] Initizialization begins..")

        # MAP VIEWER preferred size (longest side)
        self.MAP_VIEWER_SIZE = 400

        self.taglab_dir = os.getcwd()
        self.project_name = "NONE"
        self.map_image_filename = "map.png"
        self.map_acquisition_date = "YYYY-MM-DD"
        self.map_px_to_mm_factor = 1.0

        self.project_to_save = ""

        self.recentFileActs = []
        self.maxRecentFiles = 4
        self.separatorRecentFilesAct = None

        # ANNOTATION DATA
        self.annotations = Annotation(self.labels)
        self.undo_operations = []
        self.undo_position = -1
        """Temporary variable to hold the added and removed of the last operation."""
        self.undo_operation = { 'remove':[], 'add':[], 'class':[], 'newclass':[] }
        """Max number  of undo operations"""
        self.max_undo = 100

        ##### INTERFACE #####
        #####################

        self.mapWidget = None
        self.classifierWidget = None

        self.tool_used = "MOVE"        # tool currently used
        self.tool_orig = "MOVE"        # tool originally used when a shift key changes the current tool
        self.current_selection = None  # blob currently selected
        self.refine_grow = 0.0


        ##### TOP LAYOUT

        ##### LAYOUT EDITING TOOLS (VERTICAL)

        flatbuttonstyle1 = """
        QPushButton:checked { background-color: rgb(100,100,100); }
        QPushButton:hover   { border: 1px solid darkgray;         }"""

        flatbuttonstyle2 = """
        QPushButton:checked { background-color: rgb(100,100,100); }
        QPushButton:hover   { border: 1px solid rgb(255,100,100); }"""


        self.btnMove        = self.newButton("move.png",     "Move",                  flatbuttonstyle1, self.move)
        self.btnAssign      = self.newButton("bucket.png",   "Assign class",          flatbuttonstyle1, self.assign)
        self.btnEditBorder  = self.newButton("edit.png",     "Edit border",           flatbuttonstyle1, self.editBorder)
        self.btnCut         = self.newButton("scissors.png", "Cut Segmentation",      flatbuttonstyle1, self.cut)
        self.btnFreehand    = self.newButton("pencil.png",   "Freehand segmentation", flatbuttonstyle1, self.freehandSegmentation)
        self.btnCreateCrack = self.newButton("crack.png",    "Create crack",          flatbuttonstyle1, self.createCrack)
        self.btnSplitBlob   = self.newButton("split.png",    "Split Blob",            flatbuttonstyle1, self.splitBlob)
        self.btnRuler       = self.newButton("ruler.png",    "Measure tool",          flatbuttonstyle1, self.ruler)
        self.btnDeepExtreme = self.newButton("dexter.png",   "4-click segmentation",  flatbuttonstyle2, self.deepExtreme)
        self.btnAutoClassification = self.newButton("auto.png", "Fully automatic classification", flatbuttonstyle2, self.selectClassifier)

        layout_tools = QVBoxLayout()
        layout_tools.setSpacing(0)
        layout_tools.addWidget(self.btnMove)
        layout_tools.addWidget(self.btnAssign)
        layout_tools.addWidget(self.btnFreehand)
        layout_tools.addWidget(self.btnEditBorder)
        layout_tools.addWidget(self.btnCut)
        layout_tools.addWidget(self.btnCreateCrack)
        layout_tools.addWidget(self.btnSplitBlob)
        layout_tools.addWidget(self.btnRuler)
        layout_tools.addSpacing(10)
        layout_tools.addWidget(self.btnDeepExtreme)
        layout_tools.addWidget(self.btnAutoClassification)
        layout_tools.addStretch()

        #CONTEXT MENU ACTIONS

        self.assignAction       = self.newAction("Assign Class",            "A",   self.assignOperation)
        self.deleteAction       = self.newAction("Delete Labels",           "Del", self.deleteSelectedBlobs)
        self.mergeAction        = self.newAction("Merge Overlapped Labels", "M",   self.union)
        self.divideAction       = self.newAction("Divide Labels",           "D",   self.divide)
        self.subtractAction     = self.newAction("Subtract Labels",         "S",   self.subtract)
        self.refineAction       = self.newAction("Refine Border",           "R",   self.refineBorderOperation)
        self.refineActionDilate = self.newAction("Refine Border Dilate",    "+",   self.refineBorderDilate)
        self.refineActionErode  = self.newAction("Refine Border Erode",     "-",   self.refineBorderErode)
        self.fillAction       = self.newAction("Fill Label",                "F",   self.fillLabel)

        #       in case we want a refine all selected borders
        #        refineActionAll = QAction("Refine All Borders", self)
        #        refineActionAll.setShortcut(QKeySequence("^"))
        #        refineActionAll.setShortcutVisibleInContextMenu(True)
        #        menu.addAction(refineActionAll)
        #            self.refineAllBorders()

        ###### LAYOUT MAIN VIEW

        layout_viewer = QVBoxLayout()

        self.lblSlider = QLabel("Transparency: 0%")

        self.sliderTrasparency = QSlider(Qt.Horizontal)
        self.sliderTrasparency.setFocusPolicy(Qt.StrongFocus)
        self.sliderTrasparency.setMinimumWidth(200)
        self.sliderTrasparency.setStyleSheet(slider_style2)
        self.sliderTrasparency.setMinimum(0)
        self.sliderTrasparency.setMaximum(100)
        self.sliderTrasparency.setValue(0)
        self.sliderTrasparency.setTickInterval(10)
        self.sliderTrasparency.valueChanged.connect(self.sliderTrasparencyChanged)

        self.labelViewInfo = QLabel("100% | top:0 left:0 right:0 bottom:0         ")

        layout_slider = QHBoxLayout()
        layout_slider.addWidget(self.lblSlider)
        layout_slider.addWidget(self.sliderTrasparency)
        layout_slider.addWidget(self.labelViewInfo)

        self.viewerplus = QtImageViewerPlus()
        self.viewerplus.viewUpdated.connect(self.updateViewInfo)

        layout_viewer.setSpacing(1)
        layout_viewer.addLayout(layout_slider)
        layout_viewer.addWidget(self.viewerplus)


        ##### LAYOUT - labels + blob info + navigation map

        # LABELS
        self.labels_widget = QtLabelsWidget(self.labels)

        scroll_area = QScrollArea()
        scroll_area.setStyleSheet("background-color: rgb(40,40,40); border:none")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setMinimumHeight(200)
        scroll_area.setWidget(self.labels_widget)

        groupbox_labels = QGroupBox("Labels Panel")

        layout_groupbox = QVBoxLayout()
        layout_groupbox.addWidget(scroll_area)
        groupbox_labels.setLayout(layout_groupbox)

        # COMPARE PANEL
        self.compare_panel = QtComparePanel()

        scroll_area2 = QScrollArea()
        scroll_area2.setStyleSheet("background-color: rgb(40,40,40); border:none")
        scroll_area2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area2.setMinimumHeight(100)
        scroll_area2.setWidget(self.compare_panel)

        groupbox_comparison = QGroupBox("Comparison Panel")

        layout_groupbox2 = QVBoxLayout()
        layout_groupbox2.addWidget(scroll_area2)
        groupbox_comparison.setLayout(layout_groupbox2)

        # BLOB INFO
        groupbox_blobpanel = QGroupBox("Segmentation Info Panel")
        lblInstance = QLabel("Instance Name: ")
        self.editInstance = QLineEdit()
        self.editInstance.setMinimumWidth(80)
        self.editInstance.setMaximumHeight(25)
        self.editInstance.setStyleSheet("background-color: rgb(40,40,40); border: none")
        lblId = QLabel("Id: ")
        self.editId = QLineEdit()
        self.editId.setMinimumWidth(80)
        self.editId.setMaximumHeight(25)
        self.editId.setStyleSheet("background-color: rgb(40,40,40);  border: none")

        blobpanel_layoutH1 = QHBoxLayout()
        blobpanel_layoutH1.addWidget(lblInstance)
        blobpanel_layoutH1.addWidget(self.editInstance)
        blobpanel_layoutH1.addWidget(lblId)
        blobpanel_layoutH1.addWidget(self.editId)

        lblcl = QLabel("Class: ")
        self.lblClass = QLabel("<b>Empty</b>")
        self.lblP = QLabel("Perimeter: ")
        self.lblA = QLabel("Area: ")
        blobpanel_layoutH2 = QHBoxLayout()
        blobpanel_layoutH2.addWidget(lblcl)
        blobpanel_layoutH2.addWidget(self.lblClass)
        blobpanel_layoutH2.addSpacing(6)
        blobpanel_layoutH2.addWidget(self.lblP)
        blobpanel_layoutH2.addWidget(self.lblA)
        blobpanel_layoutH2.addStretch()

        lblNote = QLabel("Note:")
        self.editNote = QTextEdit()
        self.editNote.setMinimumWidth(100)
        self.editNote.setMaximumHeight(50)
        self.editNote.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editNote.textChanged.connect(self.noteChanged)
        layout_blobpanel = QVBoxLayout()
        layout_blobpanel.addLayout(blobpanel_layoutH1)
        layout_blobpanel.addLayout(blobpanel_layoutH2)
        layout_blobpanel.addWidget(lblNote)
        layout_blobpanel.addWidget(self.editNote)
        groupbox_blobpanel.setLayout(layout_blobpanel)

        # INFO WIDGET
        self.infoWidget = QtInfoWidget(self)

        # MAP VIEWER
        self.mapviewer = QtMapViewer(self.MAP_VIEWER_SIZE)
        self.mapviewer.setImage(None)

        layout_labels = QVBoxLayout()
        self.mapviewer.setStyleSheet("background-color: rgb(40,40,40); border:none")
        layout_labels.addWidget(self.infoWidget)
        layout_labels.addWidget(groupbox_labels)
        layout_labels.addWidget(groupbox_comparison)
        layout_labels.addWidget(groupbox_blobpanel)
        layout_labels.addStretch()
        layout_labels.addWidget(self.mapviewer)

        layout_labels.setAlignment(self.mapviewer, Qt.AlignHCenter)

        ##### MAIN LAYOUT

        main_view_layout = QHBoxLayout()
        main_view_layout.addLayout(layout_tools)
        main_view_layout.addLayout(layout_viewer)
        main_view_layout.addLayout(layout_labels)

        main_view_layout.setStretchFactor(layout_viewer, 10)
        main_view_layout.setStretchFactor(layout_labels, 1)

        self.menubar = self.createMenuBar()

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.menubar)
        main_layout.addLayout(main_view_layout)

        self.setLayout(main_layout)

        self.setProjectTitle("NONE")

        ##### FURTHER INITIALIZAION #####
        #################################

        self.map_top = 0
        self.map_left = 0
        self.map_bottom = 0
        self.map_right = 0

        # set default opacity
        self.sliderTrasparency.setValue(50)
        self.transparency_value = 0.5

        self.img_map = None
        self.img_thumb_map = None
        self.img_overlay = QImage(16, 16, QImage.Format_RGB32)

        # EVENTS
        self.labels_widget.visibilityChanged.connect(self.updateVisibility)

        self.compare_panel.hideAnnotations.connect(self.hidePrevBlobs)
        self.compare_panel.showAnnotations.connect(self.showPrevBlobs)

        self.mapviewer.leftMouseButtonPressed.connect(self.updateMainView)
        self.mapviewer.mouseMoveLeftPressed.connect(self.updateMainView)

        self.viewerplus.leftMouseButtonPressed.connect(self.toolsOpsLeftPressed)
        self.viewerplus.leftMouseButtonReleased.connect(self.toolsOpsLeftReleased)
        self.viewerplus.rightMouseButtonPressed.connect(self.toolsOpsRightPressed)
        self.viewerplus.mouseMoveLeftPressed.connect(self.toolsOpsMouseMove)
        self.viewerplus.leftMouseButtonDoubleClicked.connect(self.selectOp)

        self.viewerplus.customContextMenuRequested.connect(self.openContextMenu)


        self.current_selection = None

        # DRAWING SETTINGS
        self.border_pen = QPen(Qt.black, 3)
#        pen.setJoinStyle(Qt.MiterJoin)
#        pen.setCapStyle(Qt.RoundCap)
        self.border_pen.setCosmetic(True)
        self.border_selected_pen = QPen(Qt.white, 3)
        self.border_selected_pen.setCosmetic(True)

        self.border_pen_for_appended_blobs = QPen(Qt.black, 3)
        self.border_pen_for_appended_blobs.setStyle(Qt.DotLine)
        self.border_pen_for_appended_blobs.setCosmetic(True)

        self.CROSS_LINE_WIDTH = 2

        # DATA FOR THE SELECTION
        self.selected_blobs = []
        self.MAX_SELECTED = 5 # maximum number of selected blobs
        self.dragSelectionStart = None
        self.dragSelectionRect = None
        self.dragSelectionStyle = QPen(Qt.white, 1, Qt.DashLine)
        self.dragSelectionStyle.setCosmetic(True)


        # DATA FOR THE EDITBORDER , CUT and FREEHAND TOOLS
        self.edit_points = []
        self.edit_qpath_gitem = None

        # DATA FOR THE CREATECRACK TOOL
        self.crackWidget = None

        # DATA FOR THE RULER, DEEP EXTREME and SPLIT TOOLS
        self.pick_points_number = 0
        self.pick_points = []
        self.pick_markers = []

        self.split_pick_style   = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}
        self.ruler_pick_style   = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}
        self.extreme_pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.red,  'size': 6}

        # NETWORKS
        self.deepextreme_net = None
        self.corals_classifier = None

        # a dirty trick to adjust all the size..
        self.showMinimized()
        self.showMaximized()

        logfile.info("[INFO] Inizialization finished!")

        # autosave timer
        self.timer = None

        self.move()

    #just to make the code less verbose
    def newAction(self, text, shortcut, callback):
        action  = QAction(text, self)
        action.setShortcut(QKeySequence(shortcut))
        action.setShortcutVisibleInContextMenu(True)
        action.triggered.connect(callback)
        return action


    def newButton(self, icon, tooltip, style, callback):
        ICON_SIZE = 48
        BUTTON_SIZE = 54

        button = QPushButton()
        button.setEnabled(True)
        button.setCheckable(True)
        button.setFlat(True)
        button.setStyleSheet(style)
        button.setMinimumWidth(ICON_SIZE)
        button.setMinimumHeight(ICON_SIZE)
        button.setIcon(QIcon(os.path.join("icons", icon)))
        button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        button.setMaximumWidth(BUTTON_SIZE)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        return button

    def activateAutosave(self):

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.autosave)
        #self.timer.start(1800000)  # save every 3 minute
        self.timer.start(600000)  # save every 3 minute

    @pyqtSlot()
    def autosave(self):
        filename, file_extension = os.path.splitext(self.project_name)
        self.save(filename + "_autosave.json")

    # call by pressing right button
    def openContextMenu(self, position):

        menu = QMenu(self)
        menu.setAutoFillBackground(True)

        str = "QMenu::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(255, 255, 255);\
            }"

        menu.setStyleSheet(str)

        menu.addAction(self.assignAction)
        menu.addAction(self.deleteAction)

        menu.addSeparator()

        menu.addAction(self.mergeAction)
        menu.addAction(self.divideAction)
        menu.addAction(self.subtractAction)

        menu.addSeparator()
        menu.addAction(self.refineAction)
        menu.addAction(self.refineActionDilate)
        menu.addAction(self.refineActionErode)

        menu.addAction(self.fillAction)


        action = menu.exec_(self.viewerplus.mapToGlobal(position))


    def setProjectTitle(self, project_name):

        title = "TagLab - [Project: " + project_name + "]"
        self.setWindowTitle(title)

        if project_name is not "NONE":

            settings = QSettings('VCLAB', 'TagLab')
            files = settings.value('recentFileList')

            if files:

                try:
                    files.remove(project_name)
                except ValueError:
                    pass

                files.insert(0, project_name)
                del files[self.maxRecentFiles:]

                settings.setValue('recentFileList', files)
            else:
                files = []
                files.append(project_name)
                settings.setValue('recentFileList', files)

            self.updateRecentFileActions()


    def clampCoords(self, x, y):

        xc = max(0, min(int(x), self.img_map.width()))
        yc = max(0, min(int(y), self.img_map.height()))
        return (xc, yc)

    def createMenuBar(self):

        ##### PROJECTS

        newAct = QAction("New Project", self)
        newAct.setShortcut('Ctrl+N')
        newAct.setStatusTip("Create a new project")
        newAct.triggered.connect(self.newProject)

        openAct = QAction("Open Project", self)
        openAct.setShortcut('Ctrl+O')
        openAct.setStatusTip("Open an existing project")
        openAct.triggered.connect(self.openProject)

        saveAct = QAction("Save Project", self)
        saveAct.setShortcut('Ctrl+Alt+S')
        saveAct.setStatusTip("Save current project")
        saveAct.triggered.connect(self.saveProject)

        for i in range(self.maxRecentFiles):
            self.recentFileActs.append(QAction(self, visible=False, triggered=self.openRecentProject))

        # THIS WILL BECOME "ADD MAP" TO ADD MULTIPLE MAPS (e.g. depth, different years)
        loadMapAct = QAction("Load Map", self)
        loadMapAct.setShortcut('Ctrl+L')
        loadMapAct.setStatusTip("Set and load a map")
        loadMapAct.triggered.connect(self.setMapToLoad)

        ### IMPORT

        appendAct = QAction("Append Annotations to Current", self)
        appendAct.setStatusTip("Append to this project the annotations of another project")
        appendAct.triggered.connect(self.appendAnnotations)

        compareAct = QAction("Compare Annotations", self)
        compareAct.setStatusTip("Compare the current annotations with the one of another project")
        compareAct.triggered.connect(self.compareAnnotations)

        importAct = QAction("Import Label Map", self)
        importAct.setStatusTip("Import a label map")
        importAct.triggered.connect(self.importLabelMap)


        ### EXPORT

        exportDataTableAct = QAction("Export Annotations as Data Table", self)
        #exportDataTableAct.setShortcut('Ctrl+??')
        exportDataTableAct.setStatusTip("Export current annotations as CSV table")
        exportDataTableAct.triggered.connect(self.exportAnnAsDataTable)

        exportMapAct = QAction("Export Annotations as Map", self)
        #exportMapAct.setShortcut('Ctrl+??')
        exportMapAct.setStatusTip("Export current annotations as a map")
        exportMapAct.triggered.connect(self.exportAnnAsMap)

        exportHistogramAct = QAction("Export Histograms", self)
        # exportHistogramAct.setShortcut('Ctrl+??')
        exportHistogramAct.setStatusTip("Export histograms of current annotations")
        exportHistogramAct.triggered.connect(self.exportHistogramFromAnn)

        #exportShapefilesAct = QAction("Export as Shapefiles", self)
        #exportShapefilesAct.setShortcut('Ctrl+??')
        #exportShapefilesAct.setStatusTip("Export current annotations as shapefiles")
        #exportShapefilesAct.triggered.connect(self.exportAnnAsShapefiles)

        exportTrainingDatasetAct = QAction("Export New Training Dataset", self)
        #exportTrainingDatasetAct.setShortcut('Ctrl+??')
        exportTrainingDatasetAct.setStatusTip("Export a new training dataset based on the current annotations")
        exportTrainingDatasetAct.triggered.connect(self.exportAnnAsTrainingDataset)

        undoAct = QAction("Undo", self)
        undoAct.setShortcut('Ctrl+Z')
        undoAct.setStatusTip("Undo")
        undoAct.triggered.connect(self.undo)

        redoAct = QAction("Redo", self)
        redoAct.setShortcut('Ctrl+Shift+Z')
        redoAct.setStatusTip("Redo")
        redoAct.triggered.connect(self.redo)

        helpAct = QAction("Help", self)
        helpAct.setShortcut('Ctrl+H')
        helpAct.setStatusTip("Help")
        helpAct.triggered.connect(self.help)

        aboutAct = QAction("About", self)
        #exportAct.setShortcut('Ctrl+Q')
        #aboutAct.setStatusTip("About")
        aboutAct.triggered.connect(self.about)

        menubar = QMenuBar()
        menubar.setAutoFillBackground(True)

        styleMenuBar = "QMenuBar::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(255, 255, 255);\
            }"

        styleMenu = "QMenu::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(255, 255, 255);\
            }"

        menubar.setStyleSheet(styleMenuBar)

        filemenu = menubar.addMenu("&File")
        filemenu.setStyleSheet(styleMenu)
        filemenu.addAction(newAct)
        filemenu.addAction(openAct)
        filemenu.addAction(saveAct)
        filemenu.addSeparator()
        filemenu.addAction(loadMapAct)
        filemenu.addSeparator()

        for i in range(self.maxRecentFiles):
            filemenu.addAction(self.recentFileActs[i])
        self.separatorRecentFilesAct = filemenu.addSeparator()
        self.updateRecentFileActions()

        submenuImport = filemenu.addMenu("Import")
        submenuImport.addAction(appendAct)
        submenuImport.addAction(compareAct)
        submenuImport.addAction(importAct)
        filemenu.addSeparator()
        submenuExport = filemenu.addMenu("Export")
        submenuExport.addAction(exportDataTableAct)
        submenuExport.addAction(exportMapAct)
        #submenuExport.addAction(exportShapefilesAct)
        submenuExport.addAction(exportHistogramAct)
        submenuExport.addAction(exportTrainingDatasetAct)

        editmenu = menubar.addMenu("&Edit")
        editmenu.addAction(undoAct)
        editmenu.addAction(redoAct)
        editmenu.addSeparator()

        editmenu.addAction(self.assignAction)
        editmenu.addAction(self.deleteAction)

        editmenu.addSeparator()

        editmenu.addAction(self.mergeAction)
        editmenu.addAction(self.divideAction)
        editmenu.addAction(self.subtractAction)

        editmenu.addSeparator()
        editmenu.addAction(self.refineAction)
        editmenu.addAction(self.refineActionDilate)
        editmenu.addAction(self.refineActionErode)

        editmenu.addAction(self.fillAction)

        helpmenu = menubar.addMenu("&Help")
        helpmenu.setStyleSheet(styleMenu)
        helpmenu.addAction(helpAct)
        helpmenu.addAction(aboutAct)

        return menubar

    def updateRecentFileActions(self):

        settings = QSettings('VCLAB', 'TagLab')
        files = settings.value('recentFileList')

        if files:
            numRecentFiles = min(len(files), self.maxRecentFiles)

            for i in range(numRecentFiles):
                text = "&%d. %s" % (i + 1, QFileInfo(files[i]).fileName())
                self.recentFileActs[i].setText(text)
                self.recentFileActs[i].setData(files[i])
                self.recentFileActs[i].setVisible(True)

            for j in range(numRecentFiles, self.maxRecentFiles):
                self.recentFileActs[j].setVisible(False)

            self.separatorRecentFilesAct.setVisible((numRecentFiles > 0))


    def keyPressEvent(self, event):

        modifiers = QApplication.queryKeyboardModifiers()

        key_pressed = chr(event.key())
        if modifiers == Qt.ControlModifier:
            str = "[KEYPRESS] Key CTRL + '" + key_pressed + "' has been pressed."
        elif modifiers == Qt.ShiftModifier:
            str = "[KEYPRESS] Key SHIFT + '" + key_pressed + "' has been pressed."
        else:
            str = "[KEYPRESS] Key '" + key_pressed + "' has been pressed."

        logfile.info(str)

        if event.key() == Qt.Key_Escape:
            # RESET CURRENT OPERATION
            self.resetSelection()
            if self.tool_used in ["EDITBORDER", "CUT", "FREEHAND"]:
                self.resetEditBorder()
            elif self.tool_used == "RULER":
                self.resetPickPoints()
            elif self.tool_used == "SPLITBLOB":
                self.resetPickPoints()
            elif self.tool_used == "DEEPEXTREME":
                self.resetPickPoints()
            elif self.tool_used == "AUTOCLASS":
                self.corals_classifier.stopProcessing()

            self.tool_used = self.tool_orig

            message = "[TOOL][" + self.tool_used + "] Current operation has been canceled."
            logfile.info(message)

        elif event.key() == Qt.Key_S and modifiers == Qt.ControlModifier:
            self.save(self.project_name)

        elif event.key() == Qt.Key_A:
            # ASSIGN LABEL
            self.assignOperation()

        elif event.key() == Qt.Key_Delete:
            # DELETE SELECTED BLOBS
            self.deleteSelectedBlobs()

        elif event.key() == Qt.Key_M:
            # MERGE OVERLAPPED BLOBS
            self.union()

        elif event.key() == Qt.Key_S:
            # SUBTRACTION BETWEEN TWO BLOBS (A = A / B), THEN BLOB B IS DELETED
            self.subtract()

        elif event.key() == Qt.Key_D:
            # SUBTRACTION BETWEEN TWO BLOBS (A = A / B), BLOB B IS NOT DELETED
            self.divide()

        elif event.key() == Qt.Key_R:
            self.refineBorder()

        elif event.key() == Qt.Key_Plus:
            self.refineBorderDilate()

        elif event.key() == Qt.Key_Minus:
            self.refineBorderErode()

        elif event.key() == Qt.Key_F:
            self.fillBorder()

        # elif event.key() == Qt.Key_G:
        #     self.groupBlobs()

        elif event.key() == Qt.Key_U:
            self.ungroupBlobs()

        elif event.key() == Qt.Key_1:
            # ACTIVATE "MOVE" TOOL
            self.move()

        elif event.key() == Qt.Key_2:
            # ACTIVATE "ASSIGN" TOOL
            self.assign()

        elif event.key() == Qt.Key_3:
            # ACTIVATE "FREEHAND" TOOL
            self.freehandSegmentation()

        elif event.key() == Qt.Key_4:
            # ACTIVATE "EDIT BORDER" TOOL
            self.editBorder()

        elif event.key() == Qt.Key_5:
            # ACTIVATE "CUT SEGMENTATION" TOOL
            self.cut()

        elif event.key() == Qt.Key_6:
            # ACTIVATE "CREATE CRACK" TOOL
            self.createCrack()

        elif event.key() == Qt.Key_7:
            # ACTIVATE "SPLIT BLOB" TOOL
            self.splitBlob()

        elif event.key() == Qt.Key_8:
            # ACTIVATE "RULER" TOOL
            self.ruler()

        elif event.key() == Qt.Key_9:
            # ACTIVATE "4-CLICK" TOOL
            self.deepExtreme()


        # elif event.key() == Qt.Key_H:
        #     # ACTIVATE THE "HOLE" TOOL
        #     self.hole()

        elif event.key() == Qt.Key_4:
            # ACTIVATE "DEEP EXTREME" TOOL
            self.deepExtreme()

        elif event.key() == Qt.Key_P:
            self.drawDeepExtremePoints()
        #
        # elif event.key() == Qt.Key_Y:
        #     self.refineAllBorders()

        elif event.key() == Qt.Key_Space:

            #drawing operations are grouped
            if self.tool_used in ["EDITBORDER", "CUT", "FREEHAND"]:
                if len(self.edit_points) == 0:
                    self.infoWidget.setInfoMessage("You need to draw something for this operation.")
                    return

                if self.tool_used == "FREEHAND":
                    blob = Blob(None, 0, 0, 0)

                    try:
                        flagValid = blob.createFromClosedCurve(self.edit_points)
                    except Exception:
                        self.infoWidget.setInfoMessage("Failed creating area.")
                        logfile.info("[TOOL][FREEHAND] FREEHAND operation not done (invalid snap).")
                        return

                    if flagValid is True:

                        blob.setId(self.annotations.progressive_id)
                        self.annotations.progressive_id += 1

                        self.resetSelection()
                        self.addBlob(blob, selected=True)
                        self.logBlobInfo(blob, "[TOOL][FREEHAND][BLOB-CREATED]")
                        self.saveUndo()

                        logfile.info("[TOOL][FREEHAND] Operation ends.")

                    else:
                        logfile.info("[TOOL][FREEHAND] Operation ends (INVALID SNAP!).")

                #editborder and cut require a selected area
                if self.tool_used in ["EDITBORDER", "CUT"]:
                    if len(self.selected_blobs) != 1:
                        self.infoWidget.setInfoMessage("A single selected area is required.")
                        return

                    selected_blob = self.selected_blobs[0]

                if self.tool_used == "EDITBORDER":
                    blob = selected_blob.copy()

                    self.annotations.editBorder(blob, self.edit_points)

                    self.logBlobInfo(selected_blob, "[TOOL][EDITEDBORDER][BLOB-SELECTED]")
                    self.logBlobInfo(blob, "[TOOL][EDITEDBORDER][BLOB-EDITED]")

                    logfile.info("[TOOL][EDITBORDER] Operation ends.")

                    self.removeBlob(selected_blob)
                    self.addBlob(blob, selected=True)
                    self.saveUndo()

                if self.tool_used == "CUT":
                    created_blobs = self.annotations.cut(selected_blob, self.edit_points)

                    self.logBlobInfo(selected_blob, "[TOOL][CUT][BLOB-SELECTED]")

                    for blob in created_blobs:
                        self.addBlob(blob, selected=True)
                        self.logBlobInfo(blob, "[TOOL][CUT][BLOB-CREATED]")

                    logfile.info("[TOOL][CUT] Operation ends.")

                    self.removeBlob(selected_blob)
                    self.saveUndo()

                self.resetEditBorder()

            # APPLY DEEP EXTREME (IF FOUR POINTS HAVE BEEN SELECTED)
            elif self.tool_used == "DEEPEXTREME" and self.pick_points_number == 4:

                self.segmentWithDeepExtreme()
                self.resetPickPoints()

            elif self.tool_used == "SPLITBLOB" and self.pick_points_number > 1 and len(self.selected_blobs) == 1:

                selected_blob = self.selected_blobs[0]
                points = self.pick_points
                created_blobs = self.annotations.splitBlob(self.img_map,selected_blob, points)

                self.logBlobInfo(selected_blob, "[TOOL][SPLITBLOB][BLOB-SELECTED]")

                for blob in created_blobs:
                    self.addBlob(blob, selected=True)
                    self.logBlobInfo(blob, "[TOOL][SPLITBLOB][BLOB-CREATED]")

                logfile.info("[TOOL][SPLITBLOB] Operation ends.")

                self.removeBlob(selected_blob)
                self.saveUndo()
                self.resetPickPoints()

            self.tool_used = self.tool_orig


    @pyqtSlot()
    def sliderTrasparencyChanged(self):

        # update transparency value
        newvalue = self.sliderTrasparency.value()
        str1 = "Transparency {}%".format(newvalue)
        self.lblSlider.setText(str1)
        self.transparency_value = self.sliderTrasparency.value() / 100.0

        # update transparency of all the blobs
        self.applyTransparency()

    def applyTransparency(self):

        # current annotations
        for blob in self.annotations.seg_blobs:
            blob.qpath_gitem.setOpacity(self.transparency_value)

        # annnotations coming from previous years
        for blob_list in self.annotations.prev_blobs:
            for blob in blob_list:
                blob.qpath_gitem.setOpacity(self.transparency_value)

    @pyqtSlot()
    def updateVisibility(self):

        for blob in self.annotations.seg_blobs:

            visibility = self.labels_widget.isClassVisible(blob.class_name)
            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setVisible(visibility)


    @pyqtSlot()
    def updateViewInfo(self):

        zf = self.viewerplus.zoom_factor * 100.0

        topleft = self.viewerplus.mapToScene(QPoint(0, 0))
        bottomright = self.viewerplus.mapToScene(self.viewerplus.viewport().rect().bottomRight())

        (left, top) = self.clampCoords(topleft.x(), topleft.y())
        (right, bottom) = self.clampCoords(bottomright.x(), bottomright.y())

        text = "| {:6.2f}% | top: {:4d} left: {:4d} bottom: {:4d} right: {:4d}".format(zf, top, left, bottom, right)

        self.map_top = top
        self.map_left = left
        self.map_bottom = bottom
        self.map_right = right

        self.labelViewInfo.setText(text)

    @pyqtSlot(float, float)
    def updateMainView(self, x, y):

        zf = self.viewerplus.zoom_factor

        xmap = float(self.img_map.width()) * x
        ymap = float(self.img_map.height()) * y

        h = self.map_bottom - self.map_top
        w = self.map_right - self.map_left

        posx = xmap - w / 2
        posy = ymap - h / 2

        if posx < 0:
            posx = 0
        if posy < 0:
            posy = 0

        if posx + w/2 > self.img_map.width():
            posx = self.img_map.width() - w / 2 - 1

        if posy + h/2 > self.img_map.height():
            posy = self.img_map.height() - h / 2 - 1

        posx = posx * zf;
        posy = posy * zf;

        self.viewerplus.horizontalScrollBar().setValue(posx)
        self.viewerplus.verticalScrollBar().setValue(posy)

    @pyqtSlot()
    def updateMapViewer(self):

        topleft = self.viewerplus.mapToScene(QPoint(0, 0))
        bottomright = self.viewerplus.mapToScene(self.viewerplus.viewport().rect().bottomRight())

        W = float(self.img_map.width())
        H = float(self.img_map.height())

        top = float(topleft.y()) / H
        left = float(topleft.x()) / W
        bottom = float(bottomright.y()) / H
        right = float(bottomright.x()) / W

        self.mapviewer.drawOverlayImage(top, left, bottom, right)

    def resetAll(self):

        if self.img_map is not None:
            del self.img_map
            self.img_map = None

        if self.img_thumb_map is not None:
            del self.img_thumb_map
            self.img_thumb_map = None

        self.resetSelection()

        if self.annotations:

            for blob in self.annotations.seg_blobs:
                self.undrawBlob(blob)
                del blob

            for blob_list in self.annotations.prev_blobs:
                for blob in blob_list:
                    self.undrawBlob(blob)
                    del blob

            del self.annotations

        # RE-INITIALIZATION

        self.annotations = Annotation(self.labels)

        self.mapWidget = None
        self.project_name = "NONE"
        self.map_image_filename = "map.png"
        self.map_acquisition_date = "YYYY-MM-DD"
        self.map_px_to_mm_factor = 1.0


    def resetToolbar(self):

        self.btnMove.setChecked(False)
        self.btnAssign.setChecked(False)
        self.btnEditBorder.setChecked(False)
        self.btnCut.setChecked(False)
        self.btnFreehand.setChecked(False)
        self.btnRuler.setChecked(False)
        self.btnCreateCrack.setChecked(False)
        self.btnSplitBlob.setChecked(False)
        self.btnDeepExtreme.setChecked(False)

        self.btnAutoClassification.setChecked(False)

    @pyqtSlot()
    def move(self):
        """
        Activate the tool "move".
        """

        self.resetToolbar()
        self.resetTools()

        self.btnMove.setChecked(True)
        self.tool_used = self.tool_orig = "MOVE"

        self.viewerplus.enablePan()
        self.viewerplus.enableZoom()

        self.infoWidget.setInfoMessage("Move Tool is active")
        logfile.info("[TOOL][MOVE] Tool activated")


    @pyqtSlot()
    def createCrack(self):
        """
        Activate the tool "Create Crack".
        """

        self.resetToolbar()
        self.resetTools()

        self.btnCreateCrack.setChecked(True)
        self.tool_used = self.tool_orig = "CREATECRACK"

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        self.infoWidget.setInfoMessage("Crack Tool is active")
        logfile.info("[TOOL][CREATECRACK] Tool activated")

    @pyqtSlot()
    def splitBlob(self):
        """
        Activate the tool "Split Blob".
        """

        self.resetToolbar()
        self.resetTools()

        self.btnSplitBlob.setChecked(True)
        self.tool_used = self.tool_orig = "SPLITBLOB"

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        self.infoWidget.setInfoMessage("Split Blob Tool is active")
        logfile.info("[TOOL][SPLITBLOB] Tool activated")


    @pyqtSlot(float, float)
    def selectOp(self, x, y):
        """
        Selection operation.
        """

        # NOTE: double click selection is disabled with RULER and DEEPEXTREME tools

        logfile.info("[SELECTION][DOUBLE-CLICK] Selection starts..")

        if self.tool_used == "RULER" or self.tool_used == "DEEPEXTREME":
            return

        modifiers = QApplication.queryKeyboardModifiers()
        if not (modifiers & Qt.ShiftModifier):
            self.resetSelection()

        selected_blob = self.annotations.clickedBlob(x, y)

        if selected_blob:

            if selected_blob in self.selected_blobs:
                self.removeFromSelectedList(selected_blob)
            else:
                self.addToSelectedList(selected_blob)
                self.updatePanelInfo(selected_blob)

        logfile.info("[SELECTION][DOUBLE-CLICK] Selection ends.")


    @pyqtSlot()
    def assign(self):
        """
        Activate the tool "Assign" to assign a class to an existing blob.
        """

        self.resetToolbar()
        self.resetTools()

        self.btnAssign.setChecked(True)
        self.tool_used = self.tool_orig = "ASSIGN"

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        self.infoWidget.setInfoMessage("Assign Tool is active")
        logfile.info("[TOOL][ASSIGN] Tool activated")

    @pyqtSlot()
    def editBorder(self):
        """
        Activate the tool "EDITBORDER" for pixel-level editing operations.
        NOTE: it works one blob at a time (!)
        """

        self.resetToolbar()
        self.resetTools()

        if len(self.selected_blobs) > 1:
            self.resetSelection()

        self.btnEditBorder.setChecked(True)
        self.tool_used = self.tool_orig = "EDITBORDER"

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        self.infoWidget.setInfoMessage("Edit Border Tool is active")
        logfile.info("[TOOL][EDITBORDER] Tool activated")

    @pyqtSlot()
    def cut(self):
        """
        CUT
        """
        self.resetToolbar()
        self.resetTools()

        if len(self.selected_blobs) > 1:
            self.resetSelection()

        self.btnCut.setChecked(True)
        self.tool_used = self.tool_orig = "CUT"

        self.edit_qpath_gitem = self.viewerplus.scene.addPath(QPainterPath(), self.border_pen)

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        logfile.info("[TOOL][CUT] Tool activated")

    @pyqtSlot()
    def freehandSegmentation(self):
        """
        Activate the tool "FREEHAND" for manual segmentation.
        """

        self.resetToolbar()
        self.resetTools()
        self.resetSelection()

        self.btnFreehand.setChecked(True)
        self.tool_used = self.tool_orig = "FREEHAND"

        self.edit_qpath_gitem = self.viewerplus.scene.addPath(QPainterPath(), self.border_pen)

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        self.infoWidget.setInfoMessage("Freehand Tool is active")
        logfile.info("[TOOL][FREEHAND] Tool activated")

    @pyqtSlot()
    def ruler(self):
        """
        Activate the "ruler" tool. The tool allows to measure the distance between two points or between two blob centroids.
        """

        self.resetToolbar()
        self.resetTools()

        self.resetSelection()

        self.btnRuler.setChecked(True)
        self.tool_used = self.tool_orig = "RULER"

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        self.infoWidget.setInfoMessage("Ruler Tool is active")
        logfile.info("[TOOL][RULER] Tool activated")

    @pyqtSlot()
    def hole(self):
        pass

    @pyqtSlot()
    def deepExtreme(self):
        """
        Activate the "Deep Extreme" tool. The segmentation is performed by selecting four points at the
        extreme of the corals and confirm the points by pressing SPACE.
        """

        self.resetToolbar()
        self.resetTools()
        self.resetSelection()

        if self.deepextreme_net is None:
            self.resetNetworks()
            self.infoWidget.setInfoMessage("Loading deepextreme network..")
            self.loadingDeepExtremeNetwork()

        self.btnDeepExtreme.setChecked(True)
        self.tool_used = self.tool_orig = "DEEPEXTREME"

        self.viewerplus.showCrossair = True

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        self.infoWidget.setInfoMessage("4-click tool is active")
        logfile.info("[TOOL][DEEPEXTREME] Tool activated")


    def addToSelectedList(self, blob):
        """
        Add the given blob to the list of selected blob.
        """

        if blob in self.selected_blobs:
            logfile.info("[SELECTION] An already selected blob has been added to the current selection.")
        else:
            self.selected_blobs.append(blob)
            str = "[SELECTION] A new blob (" + blob.blob_name + ") has been selected."
            logfile.info(str)

        if not blob.qpath_gitem is None:
            blob.qpath_gitem.setPen(self.border_selected_pen)
        self.viewerplus.scene.invalidate()


    def removeFromSelectedList(self, blob):
        try:
            #safer if iterting over selected_blobs and calling this function.
            self.selected_blobs = [x for x in self.selected_blobs if not x == blob]
            if not blob.qpath_gitem is None:
                blob.qpath_gitem.setPen(self.border_pen)
            self.viewerplus.scene.invalidate()
        except:
            pass


    @pyqtSlot()
    def noteChanged(self):

        if len(self.selected_blobs) > 0:

            for blob in self.selected_blobs:
                blob.note = self.editNote.toPlainText()

    def updatePanelInfo(self, blob):

        self.editId.setText(blob.blob_name)
        self.editInstance.setText(blob.instance_name)
        self.lblClass.setText(blob.class_name)

        scaled_perimeter = blob.perimeter * self.map_px_to_mm_factor / 10
        text1 = "Perimeter (cm): {:8.2f}".format(scaled_perimeter)
        self.lblP.setText(text1)

        scaled_area = blob.area * (self.map_px_to_mm_factor) * (self.map_px_to_mm_factor) / 100
        text2 = "Area (cm<sup>2</sup>): {:8.2f}".format(scaled_area)
        self.lblA.setText(text2)

        self.editNote.setPlainText(blob.note)


    def deleteSelectedBlobs(self):

        for blob in self.selected_blobs:
            self.removeBlob(blob)
        self.saveUndo()

        logfile.info("[OP-DELETE] Selected blobs has been DELETED")

    def isSelected(self, target_blob):
        """
        Check if a blob belongs to the selected blobs.
        """

        blobs_to_check = set()
        for blob in self.selected_blobs:
            if blob.group:
                for blobg in blob.group.blobs:
                    blobs_to_check.add(blobg)
            else:
                blobs_to_check.add(blob)

        for blob in blobs_to_check:
            if blob == target_blob:
                return True

        return False



    def drawGroup(self, group):
        raise Exception('SHOULD NEVER BE CALLED!')
        """
        Draw all the blobs of the group with a darkGray border.
        """
        for blob in group.blobs:
            self.drawBlob(blob, selected=False, group_mode=True)

    def drawSelectedBlobs(self):
        raise Exception('SHOLD NEVER BE CALLED!')
        """
        Draw all the selected blobs with a white border.
        If a selected blob belongs to a group, the group is highlight using darkGray.
        """

        for blob in self.selected_blobs:
            if blob.group is not None:
                self.drawGroup(blob.group)

        for blob in self.selected_blobs:
            self.drawBlob(blob, selected=True)

    def drawBlob(self, blob, prev=False):
        """
        Draw a blob according to the class color. If the blob is selected a white border is used.
        Note that if group_mode == True the blob is drawn in darkGray
        and the selection flag is ignored.
        """

        # if it has just been created remove the current graphics item in order to set it again
        if blob.qpath_gitem is not None:
            self.viewerplus.scene.removeItem(blob.qpath_gitem)
            del blob.qpath_gitem
            blob.qpath_gitem = None

        blob.setupForDrawing()

        if prev is True:
            pen = self.border_pen_for_appended_blobs
        else:
            pen = self.border_selected_pen if blob in self.selected_blobs else self.border_pen

        brush = self.classBrushFromName(blob)

        blob.qpath_gitem = self.viewerplus.scene.addPath(blob.qpath, pen, brush)
        blob.qpath_gitem.setOpacity(self.transparency_value)

    def classBrushFromName(self, blob):
        brush = QBrush()

        if not blob.class_name == "Empty":
            color = self.labels[blob.class_name]
            brush = QBrush(QColor(color[0], color[1], color[2], 200))
        return brush



    def undrawBlob(self, blob):

        self.viewerplus.scene.removeItem(blob.qpath_gitem)
        del blob.qpath
        blob.qpath = None
        del blob.qpath_gitem  # QGraphicsScene does not delete the item
        blob.qpath_gitem = None
        self.viewerplus.scene.invalidate()

    def addPickPoint(self, x, y, style):
        self.pick_points.append(np.array([x, y]))
        self.pick_points_number += 1

        pen = QPen(style['color'])
        pen.setWidth(style['width'])
        pen.setCosmetic(True)

        size = style['size']
        point = self.viewerplus.scene.addEllipse(x, y, 0, 0, pen)
        point = self.viewerplus.scene.addEllipse(x, y, 0, 0, pen)
        #line1 = self.viewerplus.scene.addLine(x - size, y - size, x + size, y + size, pen)
        line1 = self.viewerplus.scene.addLine(- size, -size, +size, +size, pen)
        line1.setPos(QPoint(x, y))
        line1.setParentItem(point)  # self.viewerplus._pxmapitem)
        line1.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        line2 = self.viewerplus.scene.addLine(- size,  + size,  + size,  - size, pen)
        line2.setPos(QPoint(x, y))
        line2.setParentItem(point)  # self.viewerplus._pxmapitem)
        line2.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        #no need to add the lines to the pick_markers, the parent will take care of them
        self.pick_markers.append(point)

    def resetPickPoints(self):
        self.pick_points_number = 0
        self.pick_points.clear()
        for marker in self.pick_markers:
            self.viewerplus.scene.removeItem(marker)
        self.pick_markers.clear()

    def drawRuler(self):
        #warging! this might move the pick points to the centroids of the blobs, redraw!
        measure = self.computeMeasure()
        tmp = self.pick_points.copy()
        self.resetPickPoints()
        self.addPickPoint(tmp[0][0], tmp[0][1], self.ruler_pick_style)
        self.addPickPoint(tmp[1][0], tmp[1][1], self.ruler_pick_style)

        #pick points number is now 2
        pen = QPen(Qt.blue)
        pen.setWidth(2)
        pen.setCosmetic(True)
        start = self.pick_points[0]
        end   = self.pick_points[1]
        line = self.viewerplus.scene.addLine(start[0], start[1], end[0], end[1], pen)
        self.pick_markers.append(line)

        middle_x = (start[0] + end[0]) / 2.0
        middle_y = (start[1] + end[1]) / 2.0

        middle = self.viewerplus.scene.addEllipse(middle_x, middle_y, 0, 0)

        ruler_text = self.viewerplus.scene.addText('%.1f' % measure)
        ruler_text.setFont(QFont("Times", 12, QFont.Bold))
        ruler_text.setDefaultTextColor(Qt.white)
        ruler_text.setPos(middle_x, middle_y)
        ruler_text.setParentItem(middle)
        ruler_text.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        logfile.info("[TOOL][RULER] Measure taken.")

        self.pick_markers.append(middle);


    def assignOperation(self):
        for blob in self.selected_blobs:
            self.setBlobClass(blob, self.labels_widget.getActiveLabelName())
        self.saveUndo()
        self.resetSelection()


    def union(self):
        """
        blob A = blob A U blob B
        """

        if len(self.selected_blobs) > 1:

            message = "[OP-MERGE] MERGE OVERLAPPED LABELS operation begins.. (number of selected blobs: " + str(len(self.selected_blobs)) + ")"
            logfile.info(message)

            #union returns a NEW blob
            union_blob = self.annotations.union(self.selected_blobs)

            if union_blob is None:
                logfile.info("[OP-MERGE] INVALID MERGE OVERLAPPED LABELS -> blobs are separated.")
            else:
                for blob in self.selected_blobs:
                    self.removeBlob(blob)
                    self.logBlobInfo(blob, "[OP-MERGE][BLOB-REMOVED]")

                self.addBlob(union_blob, selected=True)
                self.saveUndo()

                self.logBlobInfo(union_blob, "[OP-MERGE][BLOB-CREATED]")

            logfile.info("[OP-MERGE] MERGE OVERLAPPED LABELS operation ends.")

        else:
            self.infoWidget.setWarningMessage("You need to select at least <em>two</em> blobs for MERGE OVERLAPPED LABELS operation.")


    def subtract(self):
        """
        blob A = blob A / blob B
        """

        if len(self.selected_blobs) == 2:

            message = "[OP-SUBTRACT] SUBTRACT LABELS operation begins.. (number of selected blobs: " + str(len(self.selected_blobs)) + ")"
            logfile.info(message)

            selectedA = self.selected_blobs[0]
            selectedB = self.selected_blobs[1]

            #blobA and will be modified, make a copy!
            blobA = selectedA.copy()

            flag_intersection = self.annotations.subtract(blobA, selectedB, self.viewerplus.scene)

            if flag_intersection:

                self.logBlobInfo(selectedA, "[OP-SUBTRACT][BLOB-SELECTED]")
                self.logBlobInfo(blobA, "[OP-SUBTRACT][BLOB-EDITED]")
                self.logBlobInfo(selectedB, "[OP-SUBTRACT][BLOB-REMOVED]")

                self.removeBlob(selectedA)
                self.removeBlob(selectedB)
                self.addBlob(blobA, selected=True)
                self.saveUndo()

            logfile.info("[OP-SUBTRACT] SUBTRACT LABELS operation ends.")

        else:

            self.infoWidget.setInfoMessage("You need to select <em>two</em> blobs for SUBTRACT operation.")


    def divide(self):
        """
        Separe intersecting blob
        """

        if len(self.selected_blobs) == 2:

            message = "[OP-DIVIDE] DIVIDE LABELS operation begins.. (number of selected blobs: " + str(len(self.selected_blobs)) + ")"
            logfile.info(message)

            selectedA = self.selected_blobs[0]
            selectedB = self.selected_blobs[1]

            #blobA and blobB and will be modified, make a copy!
            blobA = selectedA.copy()
            blobB = selectedB.copy()

            intersects = self.annotations.subtract(blobB, blobA, self.viewerplus.scene)
            if intersects:

                self.logBlobInfo(selectedA, "[OP-DIVIDE][BLOB-SELECTED]")
                self.logBlobInfo(blobA, "[OP-DIVIDE][BLOB-EDITED]")
                self.logBlobInfo(selectedB, "[OP-DIVIDE][BLOB-SELECTED]")
                self.logBlobInfo(blobB, "[OP-DIVIDE][BLOB-EDITED]")

                self.removeBlob(selectedA)
                self.removeBlob(selectedB)
                self.addBlob(blobA, selected=False)
                self.addBlob(blobB, selected=False)
                self.saveUndo()

            logfile.info("[OP-DIVIDE] DIVIDE LABELS operation ends.")

        else:

            self.infoWidget.setInfoMessage("You need to select <em>two</em> blobs for DIVIDE operation.")

    def refineBorderDilate(self):

        logfile.info("[OP-REFINE-BORDER-DILATE] DILATE-BORDER operation begins..")

        self.refine_grow = 15
        self.refineBorder()
        self.refine_grow = 0

        logfile.info("[OP-REFINE-BORDER-DILATE] DILATE-BORDER operation ends.")


    def refineBorderErode(self):

        logfile.info("[OP-REFINE-BORDER-ERODE] ERODE-BORDER operation begins..")

        self.refine_grow = -10
        self.refineBorder()
        self.refine_grow = 0

        logfile.info("[OP-REFINE-BORDER-ERODE] ERODE-BORDER operation ends.")

    def refineBorderOperation(self):

        logfile.info("[OP-REFINE-BORDER] REFINE-BORDER operation begins..")

        self.refineBorder()

        logfile.info("[OP-REFINE-BORDER] REFINE-BORDER operation ends.")

    def refineBorder(self):
        """
        Refine blob border
        """

        # padding mask to allow moving boundary
        padding = 35
        if len(self.selected_blobs) == 1:

            selected = self.selected_blobs[0]
            blob = selected.copy()
            self.logBlobInfo(blob, "[OP-REFINE-BORDER][BLOB-SELECTED]")

            mask = blob.getMask()
            mask = np.pad(mask, (padding, padding), mode='constant', constant_values=(0, 0)).astype(np.ubyte)

            bbox = blob.bbox.copy()
            bbox[0] -= padding; #top
            bbox[1] -= padding; #left
            bbox[2] += 2*padding; #width
            bbox[3] += 2*padding; #height

            img = utils.cropQImage(self.img_map, bbox);
            try:
                from coraline.Coraline import segment
                segment(utils.qimageToNumpyArray(img), mask, 0.0, conservative=0.05, grow=self.refine_grow, radius=30)

            except Exception as e:
                msgBox = QMessageBox()
                msgBox.setText(str(e))
                msgBox.exec()
                return

            try:
                blob.updateUsingMask(bbox, mask.astype(np.int))
                self.removeBlob(selected)
                self.addBlob(blob, selected=True)
                self.saveUndo()

                self.logBlobInfo(blob, "[OP-REFINE-BORDER][BLOB-REFINED]")


            except:
                print("FAILED!")
                pass

        else:
            self.infoWidget.setInfoMessage("You need to select <em>one</em> blob for REFINE operation.")

    def fillLabel(self, blob):

        logfile.info("[OP-FILL] FILL operation starts..")

        if len(self.selected_blobs) == 0:
            return
        count = 0
        for blob in self.selected_blobs:
            if len(blob.inner_contours) == 0:
                continue
            count += 1
            filled = blob.copy()

            self.logBlobInfo(filled, "[OP-FILL][BLOB-SELECTED]")

            self.removeBlob(blob)
            filled.inner_contours.clear()
            filled.createFromClosedCurve([filled.contour])
            self.addBlob(filled, True)

            self.logBlobInfo(filled, "[OP-FILL][BLOB-EDITED]")

        if count:
            self.saveUndo()

        logfile.info("[OP-FILL] FILL operation ends.")

    def addBlob(self, blob, selected = False):
        """
        The only function to add annotations. will take care of undo and QGraphicItems.
        """
        self.undo_operation['remove'].append(blob)
        self.annotations.addBlob(blob)
        self.drawBlob(blob)
        if selected:
            self.addToSelectedList(blob)

    def removeBlob(self, blob):
        """
        The only function to remove annotations.
        """
        self.removeFromSelectedList(blob)
        self.undrawBlob(blob)
        self.undo_operation['add'].append(blob)
        self.annotations.removeBlob(blob)

    def setBlobClass(self, blob, class_name):
        if blob.class_name == class_name:
            return

        self.undo_operation['class'].append((blob, blob.class_name))
        self.undo_operation['newclass'].append((blob,class_name))
        blob.class_name = class_name

        if class_name == "Empty":
            blob.class_color = [255, 255, 255]
        else:
            blob.class_color = self.labels[blob.class_name]

        brush = self.classBrushFromName(blob)
        blob.qpath_gitem.setBrush(brush)

        self.viewerplus.scene.invalidate()

    def saveUndo(self):
        #clip future redo, invalidated by a new change
        self.undo_operations = self.undo_operations[:self.undo_position+1]
        """
        Will mark an undo step using the previously added and removed blobs.
        """
        if len(self.undo_operation['add']) == 0 and len(self.undo_operation['remove']) == 0 and len(self.undo_operation['class']) == 0:
            return

        self.undo_operations.append(self.undo_operation)
        self.undo_operation = { 'remove':[], 'add':[], 'class':[], 'newclass':[] }
        if len(self.undo_operations) > self.max_undo:
            self.undo_operations.pop(0)
        self.undo_position = len(self.undo_operations) -1;

    def undo(self):
        if len(self.undo_operations) is 0:
            return
        if self.undo_position < 0:
            return;

        #operation = self.undo_operations.pop(-1)
        operation = self.undo_operations[self.undo_position]
        self.undo_position -= 1

        for blob in operation['remove']:
            message = "[UNDO][REMOVE] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            logfile.info(message)
            self.removeFromSelectedList(blob)
            self.undrawBlob(blob)
            self.annotations.removeBlob(blob)

        for blob in operation['add']:
            message = "[UNDO][ADD] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            logfile.info(message)
            self.annotations.addBlob(blob)
            self.selected_blobs.append(blob)
            self.drawBlob(blob)

        for (blob, class_name) in operation['class']:
            blob.class_name = class_name
            brush = self.classBrushFromName(blob)
            blob.qpath_gitem.setBrush(brush)

        self.updateVisibility()

    def redo(self):
        if self.undo_position >= len(self.undo_operations) -1:
            return;
        self.undo_position += 1
        operation = self.undo_operations[self.undo_position]
        for blob in operation['add']:
            message = "[REDO][ADD] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            logfile.info(message)
            self.removeFromSelectedList(blob)
            self.undrawBlob(blob)
            self.annotations.removeBlob(blob)

        for blob in operation['remove']:
            message = "[REDO][REMOVE] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            logfile.info(message)
            self.annotations.addBlob(blob)
            self.selected_blobs.append(blob)
            self.drawBlob(blob)

        for (blob, class_name) in operation['newclass']:
            blob.class_name = class_name
            brush = self.classBrushFromName(blob)
            blob.qpath_gitem.setBrush(brush)

        self.updateVisibility()


    def logBlobInfo(self, blob, tag):

        message1 = tag + " BLOBID=" + str(blob.id) + " VERSION=" + str(blob.version) + " name=" + blob.blob_name
        message2 = tag + " top={:.1f} left={:.1f} width={:.1f} height={:.1f}".format(blob.bbox[0], blob.bbox[1], blob.bbox[2], blob.bbox[3])
        message3 = tag + " cx={:.1f} cy={:.1f}".format(blob.centroid[0], blob.centroid[1])
        message4 = tag + " A={:.1f} P={:.1f} ".format(blob.area, blob.perimeter)

        logfile.info(message1)
        logfile.info(message2)
        logfile.info(message3)
        logfile.info(message4)


    def groupBlobs(self):

        if len(self.selected_blobs) > 0:

            group = self.annotations.addGroup(self.selected_blobs)
            self.drawGroup(group)

    def ungroupBlobs(self):

        if len(self.selected_blobs) > 0:

            blob_s = self.selected_blobs[0]

            if blob_s.group != None:

                # de-selection
                for blob in self.selected_blobs:
                    self.drawBlob(blob, selected=False)
                self.selected_blobs.clear()

                self.annotations.removeGroup(blob_s.group)

    def resetSelection(self):

        for blob in self.selected_blobs:
            blob.qpath_gitem.setPen(self.border_pen)

        self.selected_blobs.clear()
        self.viewerplus.scene.invalidate(self.viewerplus.scene.sceneRect())

    def resetEditBorder(self):

        if self.edit_qpath_gitem is not None:
            self.edit_qpath_gitem.setPath(QPainterPath())
        else:
            self.edit_qpath = None

        self.edit_points = []

    def resetCrackTool(self):

        if self.crackWidget is not None:
            self.crackWidget.close()

        self.crackWidget = None

        # panning of the crack preview cause some problems..
        self.viewerplus.setDragMode(QGraphicsView.NoDrag)


    def resetTools(self):

        self.resetEditBorder()
        self.resetCrackTool()
        self.resetPickPoints()

        self.viewerplus.showCrossair = False
        self.viewerplus.scene.invalidate(self.viewerplus.scene.sceneRect())


    @pyqtSlot(float, float)
    def toolsOpsLeftPressed(self, x, y):

        modifiers = QApplication.queryKeyboardModifiers()
        if modifiers & Qt.ControlModifier:
            return

        if modifiers & Qt.ShiftModifier:
            #if self.tool_orig == "FREEHAND":
            #    self.tool_used = "EDITBORDER"
            #else:
            self.dragSelectionStart = [x, y]
            logfile.info("[SELECTION][DRAG] Selection starts..")
            return

        if self.tool_used == "ASSIGN":

            selected_blob = self.annotations.clickedBlob(x, y)

            if selected_blob is not None:
                self.addToSelectedList(selected_blob)
                for blob in self.selected_blobs:
                    self.setBlobClass(blob, self.labels_widget.getActiveLabelName())

                message ="[TOOL][ASSIGN] Blob(s) assigned ({:d}).".format(len(selected_blob))
                logfile.info(message)

                self.saveUndo()
                self.resetSelection()

        elif self.tool_used in ["EDITBORDER", "CUT", "FREEHAND"]:

            if len(self.edit_points) == 0: #first point, initialize
                self.edit_qpath_gitem = self.viewerplus.scene.addPath(QPainterPath(), self.border_pen)
                message = "[TOOL][" + self.tool_used + "] DRAWING starts.."
                logfile.info(message)

            self.edit_points.append(np.array([[x, y]]))

            path = self.edit_qpath_gitem.path()
            path.moveTo(QPointF(x, y))
            self.edit_qpath_gitem.setPath(path)
            self.viewerplus.scene.invalidate()

        elif self.tool_used == "CREATECRACK":

            selected_blob = self.annotations.clickedBlob(x, y)

            if selected_blob is not None:

                self.resetSelection()
                self.addToSelectedList(selected_blob)

                xpos = self.viewerplus.clicked_x
                ypos = self.viewerplus.clicked_y

                if self.crackWidget is None:

                    #copy blob, for undo reasons.
                    blob = selected_blob.copy()
                    self.logBlobInfo(blob, "[TOOL][CREATECRACK][BLOB-SELECTED]")

                    self.crackWidget = QtCrackWidget(self.img_map, self.annotations, blob, x, y, parent=self)
                    self.crackWidget.setWindowModality(Qt.WindowModal)
                    self.crackWidget.btnCancel.clicked.connect(self.crackCancel)
                    self.crackWidget.btnApply.clicked.connect(self.crackApply)
                    self.crackWidget.closeCrackWidget.connect(self.crackCancel)
                    self.crackWidget.show()

        elif self.tool_used == "RULER":

            #first point
            if self.pick_points_number == 0:
                self.addPickPoint(x, y, self.ruler_pick_style)

            #sedcond point
            elif self.pick_points_number == 1:
                self.addPickPoint(x, y, self.ruler_pick_style)
                self.drawRuler()

            else:
                self.resetPickPoints()


        elif self.tool_used == "SPLITBLOB":

            #no selected blobs: select it!
            if len(self.selected_blobs) == 0:
                selected_blob = self.annotations.clickedBlob(x, y)
                if selected_blob is None:
                    self.infoWidget.setInfoMessage("Click on an area to split.")
                    return
                self.addToSelectedList(selected_blob)

            if len(self.selected_blobs) != 1:
                self.infoWidget.setInfoMessage("A single selected area is required.")
                self.resetPickPoints()
                return

            condition = points_in_poly(np.array([[x, y]]), self.selected_blobs[0].contour)
            if condition[0] != True:
                self.infoWidget.setInfoMessage("Click on the selected area to split.")
                return

            self.addPickPoint(x, y, self.split_pick_style)


        elif self.tool_used == "DEEPEXTREME":

            if self.pick_points_number < 4:
                self.addPickPoint(x, y, self.extreme_pick_style)
                message = "[TOOL][DEEPEXTREME] New point picked (" + str(self.pick_points_number) + ")"
                logfile.info(message)
            else:
                self.resetPickPoints()
                message = "[TOOL][DEEPEXTREME] Pick points resetted."
                logfile.info(message)

    @pyqtSlot(float, float)
    def toolsOpsLeftReleased(self, x, y):
        modifiers = QApplication.queryKeyboardModifiers()

        if self.dragSelectionStart:
            if abs(x - self.dragSelectionStart[0]) < 5 and abs(y - self.dragSelectionStart[1]) < 5:
                self.selectOp(x, y)
            else:
                self.dragSelectBlobs(x, y)
                self.dragSelectionStart = None
                if self.dragSelectionRect:
                    self.viewerplus.scene.removeItem(self.dragSelectionRect)
                    del self.dragSelectionRect
                    self.dragSelectionRect = None

                logfile.info("[SELECTION][DRAG] Selection ends.")


    @pyqtSlot(float, float)
    def toolsOpsRightPressed(self, x, y):
        pass

    @pyqtSlot(float, float)
    def toolsOpsMouseMove(self, x, y):

        if self.dragSelectionStart:
            start = self.dragSelectionStart
            if not self.dragSelectionRect:
                self.dragSelectionRect = self.viewerplus.scene.addRect(start[0], start[1], x-start[0], y-start[1], self.dragSelectionStyle)
            self.dragSelectionRect.setRect(start[0], start[1], x - start[0], y - start[1])
            return


        modifiers = QApplication.queryKeyboardModifiers()
        if modifiers & Qt.ControlModifier:
            return

        if self.tool_used in ["EDITBORDER", "CUT", "FREEHAND"]:

            if len(self.edit_points) == 0:
                return
            #check that a move didn't happen before a press
            last_line = self.edit_points[-1]


            last_point = self.edit_points[-1][-1]
            if x != last_point[0] or y != last_point[1]:
                self.edit_points[-1] = np.append(last_line, [[x, y]], axis=0)
                path = self.edit_qpath_gitem.path()
                path.lineTo(QPointF(x, y))
                self.edit_qpath_gitem.setPath(path)
                self.viewerplus.scene.invalidate()


    def dragSelectBlobs(self, x, y):
        sx = self.dragSelectionStart[0]
        sy = self.dragSelectionStart[1]
        self.resetSelection()
        for blob in self.annotations.seg_blobs:
            visible = self.labels_widget.isClassVisible(blob.class_name)
            if not visible:
                continue
            box = blob.bbox

            if sx > box[1] or sy > box[0] or x < box[1] + box[2] or y < box[0] + box[3]:
                continue
            self.addToSelectedList(blob)
        return



    @pyqtSlot()
    def crackCancel(self):

        self.resetCrackTool()

    @pyqtSlot()
    def crackApply(self):

        new_blobs = self.crackWidget.apply()
        self.logBlobInfo(self.selected_blobs[0], "[TOOL][CREATECRACK][BLOB-SELECTED]")
        self.removeBlob(self.selected_blobs[0])
        for blob in new_blobs:
            self.addBlob(blob, selected=True)
            self.logBlobInfo(blob, "[TOOL][CREATECRACK][BLOB-EDITED]")

        self.saveUndo()

        self.resetCrackTool()

    def computeMeasure(self):
        """
        It computes the measure between two points. If this point lies inside two blobs
        the distance between the centroids is computed.
        """

        x1 = self.pick_points[0][0]
        y1 = self.pick_points[0][1]
        x2 = self.pick_points[1][0]
        y2 = self.pick_points[1][1]

        blob1 = self.annotations.clickedBlob(x1, y1)
        blob2 = self.annotations.clickedBlob(x2, y2)

        if blob1 is not None and blob2 is not None and blob1 != blob2:

            x1 = blob1.centroid[0]
            y1 = blob1.centroid[1]
            x2 = blob2.centroid[0]
            y2 = blob2.centroid[1]

            self.pick_points[0][0] = x1
            self.pick_points[0][1] = y1
            self.pick_points[1][0] = x2
            self.pick_points[1][1] = y2

        measurepx = np.sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2))

        # conversion to cm
        measure = measurepx * self.map_px_to_mm_factor / 10

        return measure


    @pyqtSlot()
    def newProject(self):

        self.resetAll()

        self.setProjectTitle("NONE")

        self.infoWidget.setInfoMessage("TagLab has been reset. To continue open an existing project or load a map.")

    @pyqtSlot()
    def setMapToLoad(self):

        if self.mapWidget is None:

            self.mapWidget = QtMapSettingsWidget(parent=self)
            self.mapWidget.setWindowModality(Qt.WindowModal)
            self.mapWidget.btnApply.clicked.connect(self.setMapProperties)

            # transfer current data to widget
            self.mapWidget.editMapFile.setText(self.map_image_filename)
            self.mapWidget.editAcquisitionDate.setText(self.map_acquisition_date)
            self.mapWidget.editScaleFactor.setText(str(self.map_px_to_mm_factor))

            self.mapWidget.show()

        else:

            # show it again
            if self.mapWidget.isHidden():
                self.mapWidget.show()


    @pyqtSlot()
    def setMapProperties(self):

        map_filename = self.mapWidget.editMapFile.text()

        # check if the map file exists
        if not os.path.exists(map_filename):

            self.infoWidget.setWarningMessage("Map file does not exist.")

        else:

            # transfer settings
            self.map_image_filename = self.mapWidget.editMapFile.text()
            self.map_acquisition_date = self.mapWidget.editAcquisitionDate.text()
            self.map_px_to_mm_factor = float(self.mapWidget.editScaleFactor.text())

            # close map settings
            self.mapWidget.close()
            self.mapWidget = None

            self.loadMap()

    def loadMap(self):

        # retrieve image size
        image_reader = QImageReader(self.map_image_filename)
        sizeOfImage = image_reader.size()
        height = sizeOfImage.height()
        width = sizeOfImage.width()

        if width > 32767 or height > 32767:

            self.infoWidget.setInfoMessage("Map is too big (!)")

            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("This map exceeds the image dimension handled by TagLab (the maximum size is 32767 x 32767).")
            msgBox.exec()

        else:

            QApplication.setOverrideCursor(Qt.WaitCursor)

            # load map and set it
            self.infoWidget.setInfoMessage("Map is loading..")

            self.img_map = QImage(self.map_image_filename)

            if self.img_map.isNull():
                msgBox = QMessageBox()
                msgBox.setText("Could not load or find the image: " + self.map_image_filename)
                msgBox.exec()
                return

            self.img_thumb_map = self.img_map.scaled(self.MAP_VIEWER_SIZE, self.MAP_VIEWER_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.viewerplus.setImage(self.img_map)
            self.mapviewer.setImage(self.img_thumb_map)
            self.viewerplus.viewUpdated.connect(self.updateMapViewer)
            self.mapviewer.setOpacity(0.5)

            QApplication.restoreOverrideCursor()

            self.infoWidget.setInfoMessage("The map has been successfully loading.")

    @pyqtSlot()
    def openProject(self):

        filters = "ANNOTATION PROJECT (*.json)"

        filename, _ = QFileDialog.getOpenFileName(self, "Open a project", self.taglab_dir, filters)

        if filename:

            self.load(filename)

    @pyqtSlot()
    def openRecentProject(self):

        action = self.sender()
        if action:
            self.load(action.data())

    @pyqtSlot()
    def saveProject(self):

        filters = "ANNOTATION PROJECT (*.json)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save the project", self.taglab_dir, filters)

        if filename:
            dir = QDir(self.taglab_dir)
            self.project_name = dir.relativeFilePath(filename)
            self.setProjectTitle(self.project_name)
            self.save(filename)

    @pyqtSlot()
    def appendAnnotations(self):
        """
        Opens a previously saved project and append the annotations to the current ones.
        """

        filters = "ANNOTATION PROJECT (*.json)"
        filename, _ = QFileDialog.getOpenFileName(self, "Open a project", self.taglab_dir, filters)
        if filename:
            self.append(filename, append_to_current=True)

    @pyqtSlot()
    def compareAnnotations(self):
        """
        Opens a previously saved project and put the annotations into a different layer for comparison purposes.
        """

        filters = "ANNOTATION PROJECT (*.json)"
        filename, _ = QFileDialog.getOpenFileName(self, "Open a project", self.taglab_dir, filters)
        if filename:
            self.append(filename, append_to_current=False)

    @pyqtSlot()
    def help(self):

        help_widget = QtHelpWidget(self)
        help_widget.setWindowOpacity(0.9)
        help_widget.setWindowModality(Qt.WindowModal)
        help_widget.show()


    @pyqtSlot()
    def about(self):

        lbl1 = QLabel()

        # BIG taglab icon
        pxmap = QPixmap(os.path.join("icons", "taglab100px.png"))
        pxmap = pxmap.scaledToWidth(100)
        lbl1.setPixmap(pxmap)

        lbl2 = QLabel("TagLab was created to support the activity of annotation and extraction of statistical data "
                      "from ortho-maps of benthic communities.\n"
                      "TagLab is an ongoing project of the Visual Computing Lab (http://vcg.isti.cnr.it)")

        lbl2.setWordWrap(True)
        lbl2.setMinimumWidth(330)

        layout = QHBoxLayout()
        layout.addWidget(lbl1)
        layout.addWidget(lbl2)

        widget = QWidget(self)
        widget.setAutoFillBackground(True)
        widget.setStyleSheet("background-color: rgba(60,60,65,100); color: white")
        widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        widget.setMinimumWidth(430)
        widget.setMinimumHeight(110)
        widget.setLayout(layout)
        widget.setWindowTitle("About")
        widget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        widget.show()


    @pyqtSlot()
    def importLabelMap(self):
        """
        Import a label map
        """

        filters = "Image (*.png *.jpg)"
        filename, _ = QFileDialog.getOpenFileName(self, "Input Map File", "", filters)
        if not filename:
            return
        created_blobs = self.annotations.import_label_map(filename, self.img_map)
        for blob in created_blobs:
            self.addBlob(blob, selected=False)
        self.saveUndo()

    @pyqtSlot()
    def exportAnnAsDataTable(self):

        filters = "CSV (*.csv) ;; All Files (*)"
        filename, _ = QFileDialog.getSaveFileName(self, "Output file", "", filters)

        if filename:

            self.annotations.export_data_table_for_Scripps(self.map_px_to_mm_factor,filename)

            msgBox = QMessageBox(self)
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Data table exported successfully!")
            msgBox.exec()
            return

    @pyqtSlot()
    def exportAnnAsMap(self):

        filters = "PNG (*.png) ;; All Files (*)"
        filename, _ = QFileDialog.getSaveFileName(self, "Output file", "", filters)

        if filename:

            self.annotations.export_image_data_for_Scripps(self.img_map, filename)

            msgBox = QMessageBox(self)
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Map exported successfully!")
            msgBox.exec()
            return


    @pyqtSlot()
    def exportHistogramFromAnn(self):

        histo_widget = QtHistogramWidget(self.annotations, self.map_px_to_mm_factor, self.map_acquisition_date, self)
        histo_widget.setWindowModality(Qt.WindowModal)
        histo_widget.show()

    @pyqtSlot()
    def exportAnnAsShapefiles(self):

        pass  # not yet available

    @pyqtSlot()
    def exportAnnAsTrainingDataset(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose Export Folder", "")

        if folderName:

            filename = os.path.join(folderName, "tile")
            self.annotations.export_new_dataset(self.img_map, tile_size=1024, step=256, basename=filename)



    @pyqtSlot(int)
    def hidePrevBlobs(self, index):
        """
        Hide blobs coming from previous years.
        """

        if index > 0:
            blob_list = self.annotations.prev_blobs[index-1]
        else:
            blob_list = self.annotations.seg_blobs

        for blob in blob_list:
            blob.qpath_gitem.setVisible(False)



    @pyqtSlot(int)
    def showPrevBlobs(self, index):
        """
        Show blobs coming from previous years.
        """

        if index > 0:
            blob_list = self.annotations.prev_blobs[index-1]
        else:
            blob_list = self.annotations.seg_blobs

        for blob in blob_list:
            blob.qpath_gitem.setVisible(True)

    def load(self, filename):
        """
        Load a previously saved projects.
        """

        QApplication.setOverrideCursor(Qt.WaitCursor)

        f = open(filename, "r")
        try:
            loaded_dict = json.load(f)
        except json.JSONDecodeError as e:
            msgBox = QMessageBox()
            msgBox.setText("The json project contains an error:\n {0}\n\nPlease contact us.".format(str(e)))
            msgBox.exec()
            return

        self.resetAll()

        dir = QDir(self.taglab_dir)

        self.project_name = loaded_dict["Project Name"]
        self.map_image_filename = dir.relativeFilePath(loaded_dict["Map File"])
        info = QFileInfo(self.map_image_filename)
        if not info.exists():
            (map_image_filename, filter) = QFileDialog.getOpenFileName(self, "Couldn't find the map, please select it:", QFileInfo(filename).dir().path(), "Image Files (*.png *.jpg)")
            self.map_image_filename = dir.relativeFilePath(map_image_filename)

        self.map_acquisition_date = loaded_dict["Acquisition Date"]
        self.map_px_to_mm_factor = float(loaded_dict["Map Scale"])

        f.close()

        for blob_dict in loaded_dict["Segmentation Data"]:

            blob = Blob(None, 0, 0, 0)
            blob.fromDict(blob_dict)
            self.annotations.seg_blobs.append(blob)

        QApplication.restoreOverrideCursor()

        self.loadMap()

        self.setProjectTitle(self.project_name)

        for blob in self.annotations.seg_blobs:
            self.drawBlob(blob)

        if self.timer is None:
            self.activateAutosave()

        self.infoWidget.setInfoMessage("The given project has been successfully open.")

        self.compare_panel.setProject(self.project_name)

    def append(self, filename, append_to_current):
        """
        Append the annotations of a previously saved projects.
        """

        QApplication.setOverrideCursor(Qt.WaitCursor)

        f = open(filename, "r")
        try:
            loaded_dict = json.load(f)
        except json.JSONDecodeError as e:
            msgBox = QMessageBox()
            msgBox.setText("The json project contains an error:\n {0}\n\nPlease contact us.".format(str(e)))
            msgBox.exec()
            return

        f.close()

        if append_to_current:

            for blob_dict in loaded_dict["Segmentation Data"]:
                blob = Blob(None, 0, 0, 0)
                blob.fromDict(blob_dict)
                self.annotations.seg_blobs.append(blob)
                self.drawBlob(blob)
        else:

            self.compare_panel.addProject(filename)

            blob_list = []
            for blob_dict in loaded_dict["Segmentation Data"]:
                blob = Blob(None, 0, 0, 0)
                blob.fromDict(blob_dict)
                blob_list.append(blob)

            self.annotations.prev_blobs.append(blob_list)

            for blob in blob_list:
                self.drawBlob(blob, prev=True)

        QApplication.restoreOverrideCursor()

        self.infoWidget.setInfoMessage("The annotations of the given project has been successfully loaded.")


    def save(self, filename):
        """
        Save the current project.
        """

        QApplication.setOverrideCursor(Qt.WaitCursor)

        dict_to_save = {}

        # update project name
        dir = QDir(self.taglab_dir)

        dict_to_save["Project Name"] = self.project_name
        dict_to_save["Map File"] = dir.relativeFilePath(self.map_image_filename)
        dict_to_save["Acquisition Date"] = self.map_acquisition_date
        dict_to_save["Map Scale"] = self.map_px_to_mm_factor
        dict_to_save["Segmentation Data"] = [] # a list of blobs, each blob is a dictionary

        for blob in self.annotations.seg_blobs:
            dict = blob.toDict()
            dict_to_save["Segmentation Data"].append(dict)

        str = json.dumps(dict_to_save)

        f = open(filename, "w")
        f.write(str)
        f.close()

        QApplication.restoreOverrideCursor()

        if self.timer is None:
            self.activateAutosave()

        self.infoWidget.setInfoMessage("Current project has been successfully saved.")

    def resetNetworks(self):

        torch.cuda.empty_cache()

        if self.deepextreme_net is not None:
            del self.deepextreme_net
            self.deepextreme_net = None

        if self.corals_classifier is not None:
            del self.corals_classifier
            self.corals_classifier = None

    @pyqtSlot()
    def selectClassifier(self):

        if self.available_classifiers == "None":
            self.btnAutoClassification.setChecked(False)
        else:
            self.classifierWidget = QtClassifierWidget(self.available_classifiers, parent=self)
            self.classifierWidget.setAttribute(Qt.WA_DeleteOnClose)
            self.classifierWidget.btnApply.clicked.connect(self.applyClassifier)
            self.classifierWidget.setWindowModality(Qt.WindowModal)
            self.classifierWidget.show()


    @pyqtSlot()
    def applyClassifier(self):

        if self.classifierWidget:

            classifier_selected = self.classifierWidget.selected()

            # free GPU memory
            self.resetNetworks()

            self.classifierWidget.close()
            del self.classifierWidget
            self.classifierWidget = None

            self.tool_used = "AUTOCLASS"

            progress_bar = QtProgressBarCustom(parent=self)
            progress_bar.setWindowFlags(Qt.ToolTip | Qt.CustomizeWindowHint)
            progress_bar.setWindowModality(Qt.NonModal)
            pos = self.viewerplus.pos()
            progress_bar.move(pos.x()+15, pos.y()+30)
            progress_bar.show()

            # setup the desired classifier

            self.infoWidget.setInfoMessage("Setup automatic classification..")

            progress_bar.setMessage("Setup automatic classification..", False)
            QApplication.processEvents()

            message = "[AUTOCLASS] Automatic classification STARTS.. (classifier: )" + classifier_selected['Classifier Name']
            logfile.info(message)

            self.corals_classifier = MapClassifier(classifier_selected, self.labels)
            self.corals_classifier.updateProgress.connect(progress_bar.setProgress)

            # rescaling the map to fit the target scale of the network

            progress_bar.setMessage("Map rescaling..", False)
            QApplication.processEvents()

            target_scale_factor = classifier_selected['Scale']
            scale_factor = target_scale_factor / self.map_px_to_mm_factor

            w = self.img_map.width() * scale_factor
            h = self.img_map.height() * scale_factor

            input_img_map = self.img_map.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

            progress_bar.setMessage("Classification: ", True)
            progress_bar.setProgress(0.0)
            QApplication.processEvents()

            # runs the classifier
            self.infoWidget.setInfoMessage("Automatic classification is running..")

            self.corals_classifier.run(input_img_map, 768, 512, 128)

            if self.corals_classifier.flagStopProcessing is False:

                # import generated label map
                progress_bar.setMessage("Finalizing classification results..", False)
                QApplication.processEvents()

                filename = os.path.join("temp", "labelmap.png")
                created_blobs = self.annotations.import_label_map(filename, self.img_map)
                for blob in created_blobs:
                    self.addBlob(blob, selected=False)

                logfile.info("[AUTOCLASS] Automatic classification ENDS.")

                # free GPU memory
                self.resetNetworks()

                if self.corals_classifier:
                    del self.corals_classifier
                    self.corals_classifier = None

                if progress_bar:
                    progress_bar.close()
                    del progress_bar

                # save and close
                msgBox = QMessageBox()
                msgBox.setWindowTitle(self.TAGLAB_VERSION)
                msgBox.setText(
                    "Automatic classification is finished. TagLab will be close. Please, click ok and save the project.")
                msgBox.exec()

                self.saveProject()

                QApplication.quit()

            else:

                logfile.info("[AUTOCLASS] Automatic classification STOP by the users.")

                # free GPU memory
                self.resetNetworks()

                if self.corals_classifier:
                    del self.corals_classifier
                    self.corals_classifier = None

                if progress_bar:
                    progress_bar.close()
                    del progress_bar

                import gc
                gc.collect()

                self.move()

    def loadingDeepExtremeNetwork(self):

        # Initialization
        modelName = 'dextr_corals'

        #  Create the network and load the weights
        self.deepextreme_net = resnet.resnet101(1, nInputChannels=4, classifier='psp')

        models_dir = "models/"

        # dictionary layers' names - weights
        state_dict_checkpoint = torch.load(os.path.join(models_dir, modelName + '.pth'),
                                           map_location=lambda storage, loc: storage)

        # Remove the prefix .module from the model when it is trained using DataParallel
        if 'module.' in list(state_dict_checkpoint.keys())[0]:
            new_state_dict = OrderedDict()
            for k, v in state_dict_checkpoint.items():
                name = k[7:]  # remove `module.` from multi-gpu training
                new_state_dict[name] = v
        else:
            new_state_dict = state_dict_checkpoint

        self.deepextreme_net.load_state_dict(new_state_dict)
        self.deepextreme_net.eval()
        if not torch.cuda.is_available():
            print("CUDA NOT AVAILABLE!")

    def segmentWithDeepExtreme(self):

        QApplication.setOverrideCursor(Qt.WaitCursor)

        self.infoWidget.setInfoMessage("Segmentation is ongoing..")

        logfile.info("[TOOL][DEEPEXTREME] Segmentation begins..")

        pad = 50
        thres = 0.8
        gpu_id = 0
        device = torch.device("cuda:" + str(gpu_id) if torch.cuda.is_available() else "cpu")
        self.deepextreme_net.to(device)

        extreme_points_to_use = np.asarray(self.pick_points).astype(int)
        pad_extreme = 100
        left_map_pos = extreme_points_to_use[:, 0].min() - pad_extreme
        top_map_pos = extreme_points_to_use[:, 1].min() - pad_extreme

        width_extreme_points = extreme_points_to_use[:, 0].max() - extreme_points_to_use[:, 0].min()
        height_extreme_points = extreme_points_to_use[:, 1].max() - extreme_points_to_use[:, 1].min()
        area_extreme_points = width_extreme_points * height_extreme_points

        (img, extreme_points_new) = utils.prepareForDeepExtreme(self.img_map, extreme_points_to_use, pad_extreme)

        with torch.no_grad():

            extreme_points_ori = extreme_points_new.astype(int)

            #  Crop image to the bounding box from the extreme points and resize
            bbox = helpers.get_bbox(img, points=extreme_points_ori, pad=pad, zero_pad=True)
            crop_image = helpers.crop_from_bbox(img, bbox, zero_pad=True)
            resize_image = helpers.fixed_resize(crop_image, (512, 512)).astype(np.float32)

            #  Generate extreme point heat map normalized to image values
            extreme_points = extreme_points_ori - [np.min(extreme_points_ori[:, 0]),
                                                   np.min(extreme_points_ori[:, 1])] + [pad, pad]

            # remap the input points inside the 512 x 512 cropped box
            extreme_points = (512 * extreme_points * [1 / crop_image.shape[1], 1 / crop_image.shape[0]]).astype(
                np.int)

            # create the heatmap
            extreme_heatmap = helpers.make_gt(resize_image, extreme_points, sigma=10)
            extreme_heatmap = helpers.cstm_normalize(extreme_heatmap, 255)

            #  Concatenate inputs and convert to tensor
            input_dextr = np.concatenate((resize_image, extreme_heatmap[:, :, np.newaxis]), axis=2)
            inputs = torch.from_numpy(input_dextr.transpose((2, 0, 1))[np.newaxis, ...])

            # Run a forward pass
            inputs = inputs.to(device)
            outputs = self.deepextreme_net.forward(inputs)
            outputs = upsample(outputs, size=(512, 512), mode='bilinear', align_corners=True)
            outputs = outputs.to(torch.device('cpu'))

            pred = np.transpose(outputs.data.numpy()[0, ...], (1, 2, 0))
            pred = 1 / (1 + np.exp(-pred))
            pred = np.squeeze(pred)
            result = helpers.crop2fullmask(pred, bbox, im_size=img.shape[:2], zero_pad=True, relax=pad) > thres


            segm_mask = result.astype(int)

            blobs = self.annotations.blobsFromMask(segm_mask, left_map_pos, top_map_pos, area_extreme_points)

            for blob in blobs:
                blob.deep_extreme_points = extreme_points_to_use

            self.resetSelection()
            for blob in blobs:
                self.addBlob(blob, selected=True)
                self.logBlobInfo(blob, "[TOOL][DEEPEXTREME][BLOB-CREATED]")
            self.saveUndo()

            logfile.info("[TOOL][DEEPEXTREME] Segmentation ends.")

            self.infoWidget.setInfoMessage("Segmentation done.")

        QApplication.restoreOverrideCursor()

    def automaticSegmentation(self):

        self.img_overlay = QImage(self.segmentation_map_filename)
        self.viewerplus.setOverlayImage(self.img_overlay)

if __name__ == '__main__':

    # Create the QApplication.
    app = QApplication(sys.argv)

    # set application icon
    app.setWindowIcon(QIcon(os.path.join("icons", "taglab50px.png")))

    slider_style1 = "\
    QSlider::groove::horizontal\
    {\
        border: 1px solid;\
        height: 8px;\
        color: rgb(100,100,100);\
    }"

    slider_style2 = "QSlider::handle::horizontal\
    {\
        background: white;\
        border: 1;\
        width: 18px;\
    }"

    app.setStyleSheet("QLabel {color: white}")
    app.setStyleSheet("QPushButton {background-color: rgb(49,51,53); color: white}")
    app.setStyleSheet(slider_style1)
    app.setStyleSheet(slider_style2)

    app.setStyleSheet("QToolTip {color: white; background-color: rgb(49,51,53); border: none; }")

    # Create the inspection tool
    tool = TagLab()

    # Show the viewer and run the application.
    tool.show()
    sys.exit(app.exec_())
