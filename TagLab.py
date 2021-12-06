#!/usr/bin/python3
# # TagLab
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
import shutil
import json
import math
import numpy as np
import urllib
import platform

from PyQt5.QtCore import Qt, QSize, QMargins, QDir, QPoint, QPointF, QRectF, QTimer, pyqtSlot, pyqtSignal, QSettings, QFileInfo, QModelIndex
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QIcon, QKeySequence, QPen, QImageReader, QImage
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QFileDialog, QComboBox, QMenuBar, QMenu, QSizePolicy, QScrollArea, \
    QLabel, QToolButton, QPushButton, QSlider, QCheckBox, \
    QMessageBox, QGroupBox, QLayout, QHBoxLayout, QVBoxLayout, QFrame, QDockWidget, QTextEdit, QAction

# PYTORCH
try:
    import torch
    from torch.nn.functional import upsample
except Exception as e:
    print("Incompatible version between pytorch, cuda and python.\n" +
          "Knowing working version combinations are\n: Cuda 10.0, pytorch 1.0.0, python 3.6.8" + str(e))
   # exit()

# CUSTOM
import source.Mask as Mask
import source.RasterOps as rasterops
from source.QtImageViewerPlus import QtImageViewerPlus
from source.QtMapViewer import QtMapViewer
from source.QtSettingsWidget import QtSettingsWidget
from source.QtMapSettingsWidget import QtMapSettingsWidget
from source.QtScaleWidget import QtScaleWidget
from source.QtLabelsWidget import QtLabelsWidget
from source.QtInfoWidget import QtInfoWidget
from source.QtHelpWidget import QtHelpWidget
from source.QtProgressBarCustom import QtProgressBarCustom
from source.QtHistogramWidget import QtHistogramWidget
from source.QtClassifierWidget import QtClassifierWidget
from source.QtNewDatasetWidget import QtNewDatasetWidget
from source.QtTrainingResultsWidget import QtTrainingResultsWidget
from source.QtTYNWidget import QtTYNWidget
from source.QtComparePanel import QtComparePanel
from source.QtProjectWidget import QtProjectWidget
from source.Project import Project, loadProject
from source.Image import Image
from source.MapClassifier import MapClassifier
from source.NewDataset import NewDataset
from source.QtGridWidget import QtGridWidget
from source.QtDictionaryWidget import QtDictionaryWidget
from source.QtCustomDataWidget import QtCustomDataWidget
from source.QtShapefileAttributeWidget import QtAttributeWidget
from source.QtPanelInfo import QtPanelInfo


from source import utils

# training modules
from models.coral_dataset import CoralsDataset
import models.training as training


# LOGGING
import logging

# configure the logger
now = datetime.datetime.now()
#LOG_FILENAME = "tool" + now.strftime("%Y-%m-%d-%H-%M") + ".log"
LOG_FILENAME = "TagLab.log"
logging.basicConfig(level=logging.DEBUG, filemode='w', filename=LOG_FILENAME, format = '%(asctime)s %(levelname)-8s %(message)s')
logfile = logging.getLogger("tool-logger")

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        pass
    def closeEvent(self, event):
        taglab = self.centralWidget()
        if taglab.project.filename is not None:
            box = QMessageBox()
            reply = box.question(self, taglab.TAGLAB_VERSION, "Do you want to save changes to" + taglab.project.filename, QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
               taglab.saveProject()
        super(MainWindow, self).closeEvent(event)

class TagLab(QMainWindow):

    def __init__(self, parent=None):
        super(TagLab, self).__init__(parent)

        ##### CUSTOM STYLE #####

        self.setStyleSheet("background-color: rgb(55,55,55); color: white")

        current_version, need_to_update = self.checkNewVersion()
        if need_to_update:
            print("New version available. Please, launch update.py")
            sys.exit(0)

        ##### DATA INITIALIZATION AND SETUP #####

        self.TAGLAB_VERSION = "TagLab " + current_version

        print(self.TAGLAB_VERSION)

        # SETTINGS
        self.settings_widget = QtSettingsWidget()

        # LOAD CONFIGURATION FILE

        f = open("config.json", "r")
        config_dict = json.load(f)
        self.available_classifiers = config_dict["Available Classifiers"]

        # filename of the default dictionary
        self.default_dictionary = "dictionaries/scripps.json"

        logfile.info("[INFO] Initizialization begins..")

        self.taglab_dir = os.getcwd()
        self.project = Project()         # current project
        self.last_image_loaded = None

        self.map_3D_filename = None    #refactor THIS!
        self.map_image_filename = None #"map.png"  #REFACTOR to project.map_filename
        self.map_acquisition_date = None #"YYYY-MM-DD"

        self.recentFileActs = []  #refactor to self.maxRecentProjects
        self.maxRecentFiles = 4   #refactor to maxRecentProjects
        self.separatorRecentFilesAct = None    #refactor to separatorRecentFiles

        ##### INTERFACE #####
        #####################

        self.mapWidget = None
        self.scale_widget = None
        self.classifierWidget = None
        self.newDatasetWidget = None
        self.editProjectWidget = None
        self.trainYourNetworkWidget = None
        self.trainResultsWidget = None
        self.progress_bar = None
        self.gridWidget = None


        ##### TOP LAYOUT

        ##### LAYOUT EDITING TOOLS (VERTICAL)

        flatbuttonstyle1 = """
        QPushButton:checked { background-color: rgb(100,100,100); }
        QPushButton:hover   { border: 1px solid darkgray;         }
        QToolTip { background-color: white; color: rgb(100,100,100); }
        """

        flatbuttonstyle2 = """
        QPushButton:checked { background-color: rgb(100,100,100); }
        QPushButton:hover   { border: 1px solid rgb(255,100,100); }
        QToolTip { background-color: white; color: rgb(100,100,100); }
        """


        self.btnMove               = self.newButton("move.png",     "Move",                   flatbuttonstyle1, self.move)
        self.btnAssign             = self.newButton("bucket.png",   "Assign class",           flatbuttonstyle1, self.assign)
        self.btnEditBorder         = self.newButton("edit.png",     "Edit border",            flatbuttonstyle1, self.editBorder)
        self.btnCut                = self.newButton("scissors.png", "Cut segmentation",       flatbuttonstyle1, self.cut)
        self.btnFreehand           = self.newButton("pencil.png",   "Freehand segmentation",  flatbuttonstyle1, self.freehandSegmentation)
        self.btnCreateCrack        = self.newButton("crack.png",    "Create crack",           flatbuttonstyle1, self.createCrack)
        self.btnWatershed          = self.newButton("brush.png",    "Watershed segmentation", flatbuttonstyle1, self.watershedSegmentation)
        self.btnBricksSegmentation = self.newButton("brick.png",    "Bricks segmentation",    flatbuttonstyle2, self.bricksSegmentation)

        # Split blob operation removed from the toolbar
        # self.btnSplitBlob   = self.newButton("split.png",    "Split Blob",            flatbuttonstyle1, self.splitBlob)

        self.btnRuler         = self.newButton("ruler.png",    "Measure tool",           flatbuttonstyle1, self.ruler)
        self.btnDeepExtreme   = self.newButton("dexter.png",   "4-clicks segmentation",  flatbuttonstyle2, self.deepExtreme)
        self.btnRitm          = self.newButton("ritm.png",     "Positive/negative clicks segmentation", flatbuttonstyle2, self.ritm)
        self.btnAutoClassification = self.newButton("auto.png", "Fully automatic classification", flatbuttonstyle2, self.selectClassifier)

        # Split Screen operation removed from the toolbar
        self.pxmapSeparator = QPixmap("icons/separator.png")
        self.labelSeparator = QLabel()
        self.labelSeparator.setPixmap(self.pxmapSeparator.scaled(QSize(35, 30)))
        self.btnCreateGrid = self.newButton("grid.png", "Create grid",  flatbuttonstyle1, self.createGrid)
        self.btnGrid = self.newButton("grid-edit.png", "Active/disactive grid operations", flatbuttonstyle1, self.toggleGrid)
        self.pxmapSeparator2 = QPixmap("icons/separator.png")
        self.labelSeparator2 = QLabel()
        self.labelSeparator2.setPixmap(self.pxmapSeparator2.scaled(QSize(35, 30)))

        self.btnSplitScreen = self.newButton("split.png", "Split screen", flatbuttonstyle1, self.toggleComparison)
        self.btnAutoMatch = self.newButton("automatch.png", "Compute automatic matches", flatbuttonstyle1, self.autoCorrespondences)
        self.btnMatch = self.newButton("manualmatch.png", "Add manual matches ", flatbuttonstyle1, self.matchTool)

        # NOTE: Automatic matches button is not checkable
        self.btnAutoMatch.setCheckable(False)

        layout_tools = QVBoxLayout()
        layout_tools.setSpacing(0)
        layout_tools.addWidget(self.btnMove)
        layout_tools.addWidget(self.btnDeepExtreme)
        layout_tools.addWidget(self.btnRitm)
        layout_tools.addWidget(self.btnFreehand)
        layout_tools.addWidget(self.btnAssign)
        #layout_tools.addWidget(self.btnWatershed)
        #layout_tools.addWidget(self.btnBricksSegmentation)
        layout_tools.addWidget(self.btnEditBorder)
        layout_tools.addWidget(self.btnCut)
        layout_tools.addWidget(self.btnCreateCrack)
        #layout_tools.addWidget(self.btnSplitBlob)
        layout_tools.addWidget(self.btnRuler)
        layout_tools.addWidget(self.btnAutoClassification)
        layout_tools.addSpacing(3)
        layout_tools.addWidget(self.labelSeparator)
        layout_tools.addSpacing(3)
        layout_tools.addWidget(self.btnCreateGrid)
        layout_tools.addWidget(self.btnGrid)
        layout_tools.addSpacing(3)
        layout_tools.addWidget(self.labelSeparator2)
        layout_tools.addSpacing(3)
        layout_tools.addWidget(self.btnSplitScreen)
        layout_tools.addWidget(self.btnAutoMatch)
        layout_tools.addWidget(self.btnMatch)

        layout_tools.addStretch()

        # CONTEXT MENU ACTIONS

        self.markEmpty = self.newAction("Mark cell as empty",  "",   self.markEmptyOperation)
        self.markIncomplete = self.newAction("Mark cell as incomplete", "",   self.markIncompleteOperation)
        self.markComplete = self.newAction("Mark cell as complete", "",   self.markCompleteOperation)
        self.addNote = self.newAction("Add/edit note", "",   self.addNoteOperation)

        self.assignAction       = self.newAction("Assign Class",            "A",   self.assignOperation)
        self.deleteAction       = self.newAction("Delete Labels",           "Del", self.deleteSelectedBlobs)
        self.mergeAction        = self.newAction("Merge Overlapped Labels", "M",   self.union)
        self.divideAction       = self.newAction("Divide Labels",           "D",   self.divide)
        self.subtractAction     = self.newAction("Subtract Labels",         "S",   self.subtract)
        self.refineAction       = self.newAction("Refine Border",           "R",   self.refineBorderOperation)
        self.dilateAction       = self.newAction("Dilate Border",           "+",   self.dilate)
        self.erodeAction        = self.newAction("Erode Border",            "-",   self.erode)
        self.attachBoundariesAction = self.newAction("Attach Boundaries",   "B",   self.attachBoundaries)
        self.fillAction         = self.newAction("Fill Label",              "F",   self.fillLabel)


        # VIEWERPLUS

        # main viewer
        self.viewerplus = QtImageViewerPlus(self.taglab_dir)
        self.viewerplus.logfile = logfile
        self.viewerplus.viewUpdated.connect(self.updateViewInfo)
        self.viewerplus.activated.connect(self.setActiveViewer)
        self.viewerplus.updateInfoPanel.connect(self.updatePanelInfo)
        self.viewerplus.mouseMoved[float, float].connect(self.updateMousePos)
        self.viewerplus.selectionChanged.connect(self.updateEditActions)
        self.viewerplus.selectionReset.connect(self.resetPanelInfo)

        # secondary viewer in SPLIT MODE
        self.viewerplus2 = QtImageViewerPlus(self.taglab_dir)
        self.viewerplus2.logfile = logfile
        self.viewerplus2.viewUpdated.connect(self.updateViewInfo)
        self.viewerplus2.activated.connect(self.setActiveViewer)
        self.viewerplus2.updateInfoPanel.connect(self.updatePanelInfo)
        self.viewerplus2.mouseMoved[float, float].connect(self.updateMousePos)
        self.viewerplus2.selectionChanged.connect(self.updateEditActions)
        self.viewerplus2.selectionReset.connect(self.resetPanelInfo)

        self.viewerplus.newSelection.connect(self.showMatch)
        self.viewerplus2.newSelection.connect(self.showMatch)
        #when updating classes
        self.viewerplus.externalAnnotationsChanged.connect(self.viewerplus2.scene.invalidate)
        self.viewerplus2.externalAnnotationsChanged.connect(self.viewerplus.scene.invalidate)


        #last activated viewerplus: redirect here context menu commands and keyboard commands
        self.activeviewer = None
        self.inactiveviewer = None

        ###### LAYOUT MAIN VIEW

        self.comboboxSourceImage = QComboBox()
        self.comboboxSourceImage.setMinimumWidth(200)
        self.comboboxTargetImage = QComboBox()
        self.comboboxTargetImage.setMinimumWidth(200)

        self.comboboxSourceImage.currentIndexChanged.connect(self.sourceImageChanged)
        self.comboboxTargetImage.currentIndexChanged.connect(self.targetImageChanged)

        self.lblSlider = QLabel("Transparency: 0%")
        self.sliderTransparency = QSlider(Qt.Horizontal)
        self.sliderTransparency.setFocusPolicy(Qt.StrongFocus)
        self.sliderTransparency.setMinimumWidth(200)
        self.sliderTransparency.setStyleSheet(slider_style2)
        self.sliderTransparency.setMinimum(0)
        self.sliderTransparency.setMaximum(100)
        self.sliderTransparency.setValue(0)
        self.sliderTransparency.setTickInterval(10)
        self.sliderTransparency.valueChanged[int].connect(self.sliderTransparencyChanged)

        self.checkBoxFill = QCheckBox("Fill")
        self.checkBoxFill.setChecked(True)
        self.checkBoxFill.setMinimumWidth(20)
        self.checkBoxFill.stateChanged[int].connect(self.viewerplus.toggleFill)
        self.checkBoxFill.stateChanged[int].connect(self.viewerplus2.toggleFill)

        self.checkBoxBorders = QCheckBox("Borders")
        self.checkBoxBorders.setChecked(True)
        self.checkBoxBorders.setMinimumWidth(20)
        self.checkBoxBorders.stateChanged[int].connect(self.viewerplus.toggleBorders)
        self.checkBoxBorders.stateChanged[int].connect(self.viewerplus2.toggleBorders)

        self.checkBoxGrid = QCheckBox("Grid")
        self.checkBoxGrid.setMinimumWidth(20)
        self.checkBoxGrid.stateChanged[int].connect(self.viewerplus.toggleGrid)
        self.checkBoxGrid.stateChanged[int].connect(self.viewerplus2.toggleGrid)

        self.labelZoomInfo = QLabel("100%")
        self.labelMouseLeftInfo = QLabel("0")
        self.labelMouseTopInfo = QLabel("0")
        self.labelZoomInfo.setMinimumWidth(70)
        self.labelMouseLeftInfo.setMinimumWidth(70)
        self.labelMouseTopInfo.setMinimumWidth(70)

        layout_header = QHBoxLayout()
        layout_header.addWidget(QLabel("Map:  "))
        layout_header.addWidget(self.comboboxSourceImage)
        layout_header.addWidget(self.comboboxTargetImage)
        layout_header.addStretch()
        layout_header.addWidget(self.lblSlider)
        layout_header.addWidget(self.sliderTransparency)
        layout_header.addStretch()
        layout_header.addWidget(self.checkBoxFill)
        layout_header.addWidget(self.checkBoxBorders)
        layout_header.addWidget(self.checkBoxGrid)
        layout_header.addStretch()
        layout_header.addWidget(self.labelZoomInfo)
        layout_header.addWidget(self.labelMouseLeftInfo)
        layout_header.addWidget(self.labelMouseTopInfo)


        layout_viewers = QHBoxLayout()
        layout_viewers.addWidget(self.viewerplus)
        layout_viewers.addWidget(self.viewerplus2)
        layout_viewers.setStretchFactor(self.viewerplus, 1)
        layout_viewers.setStretchFactor(self.viewerplus2, 1)

        layout_main_view = QVBoxLayout()
        layout_main_view.setSpacing(1)
        layout_main_view.addLayout(layout_header)
        layout_main_view.addLayout(layout_viewers)

        ##### LAYOUT - labels + blob info + navigation map

        # LABELS PANEL
        self.labels_widget = QtLabelsWidget()
        self.project.loadDictionary(self.default_dictionary)
        self.labels_widget.setLabels(self.project)

        self.scroll_area_labels_panel = QScrollArea()
        self.scroll_area_labels_panel.setStyleSheet("background-color: rgb(40,40,40); border:none")
        self.scroll_area_labels_panel.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area_labels_panel.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area_labels_panel.setMinimumHeight(200)
        self.scroll_area_labels_panel.setWidget(self.labels_widget)

        groupbox_style = "QGroupBox\
          {\
              border: 2px solid rgb(40,40,40);\
              border-radius: 0px;\
              margin-top: 10px;\
              margin-left: 0px;\
              margin-right: 0px;\
              padding-top: 5px;\
              padding-left: 5px;\
              padding-bottom: 5px;\
              padding-right: 5px;\
          }\
          \
          QGroupBox::title\
          {\
              subcontrol-origin: margin;\
              subcontrol-position: top center;\
              padding: 0 0px;\
          }"

        self.groupbox_labels = QGroupBox()
        self.groupbox_labels.setStyleSheet("border: 2px solid rgb(255,40,40); padding: 0px;")

        layout_groupbox = QVBoxLayout()
        layout_groupbox.addWidget(self.scroll_area_labels_panel)
        self.groupbox_labels.setLayout(layout_groupbox)

        # COMPARE PANEL
        self.compare_panel = QtComparePanel()
        self.compare_panel.filterChanged[str].connect(self.updateVisibleMatches)
        self.compare_panel.areaModeChanged[str].connect(self.updateAreaMode)
        self.compare_panel.data_table.clicked.connect(self.showConnectionCluster)

        self.groupbox_comparison = QGroupBox()
       # self.groupbox_comparison.setStyleSheet(groupbox_style)

        layout_groupbox2 = QVBoxLayout()
        layout_groupbox2.addWidget(self.compare_panel)
        layout_groupbox2.setContentsMargins(QMargins(0, 0, 0, 0))
        self.groupbox_comparison.setLayout(layout_groupbox2)

        # BLOB INFO
        self.groupbox_blobpanel = QtPanelInfo(self.project.custom_data)


        # INFO WIDGET
        self.infoWidget = QtInfoWidget(self)

        # MAP VIEWER
        self.mapviewer = QtMapViewer(350)

        self.viewerplus.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage)
        self.mapviewer.leftMouseButtonPressed[float, float].connect(self.viewerplus.center)
        self.mapviewer.mouseMoveLeftPressed[float, float].connect(self.viewerplus.center)
        self.mapviewer.setStyleSheet("background-color: rgb(40,40,40); border:none")
        self.viewerplus2.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage)


        #DOCK
        self.infodock = QDockWidget("Info", self)
        self.infodock.setWidget(self.infoWidget)
        self.infoWidget.setStyleSheet("padding: 0px")

        self.labelsdock = QDockWidget("Labels", self)
        self.labelsdock.setWidget(self.groupbox_labels)
        self.groupbox_labels.setStyleSheet("padding: 0px")

        self.comparisondock = QDockWidget("Comparison", self)
        self.comparisondock.setWidget(self.groupbox_comparison)
        self.groupbox_comparison.setStyleSheet("padding: 0px")


        self.blobdock = QDockWidget("Region Info", self)
        self.blobdock.setWidget(QWidget())
        self.blobdock.setTitleBarWidget(self.groupbox_blobpanel)
        self.blobdock.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        self.groupbox_blobpanel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)


        self.mapdock = QDockWidget("Map", self)
        self.mapdock.setWidget(self.mapviewer)

        for dock in (self.infodock, self.labelsdock, self.comparisondock, self.blobdock, self.mapdock):
            dock.setAllowedAreas(Qt.RightDockWidgetArea)
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.setDockOptions(self.AnimatedDocks)
        #layout_labels.setAlignment(self.mapviewer, Qt.AlignHCenter)

        self.comparisondock.hide()

        self.infodock.hide()
        self.compare_panel.setMinimumHeight(600)

        ##### MAIN LAYOUT

        central_widget_layout = QHBoxLayout()
        central_widget_layout.addLayout(layout_tools)
        central_widget_layout.addLayout(layout_main_view)

        #main_view_splitter = QSplitter()
        central_widget = QWidget()
        central_widget.setLayout(central_widget_layout)
        self.setCentralWidget(central_widget)

        self.filemenu = None
        self.submenuEdit = None
        self.submenuExport = None
        self.submenuImport = None
        self.editmenu = None
        self.comparemenu = None
        self.demmenu = None
        self.helpmenu = None

        self.setMenuBar(self.createMenuBar())

        viewMenu = self.menuBar().addMenu("&View");
        
        viewMenu.addAction(self.labelsdock.toggleViewAction())
        #viewMenu.addAction(self.infodock.toggleViewAction())
        viewMenu.addAction(self.blobdock.toggleViewAction())
        viewMenu.addAction(self.mapdock.toggleViewAction())
        viewMenu.addAction(self.comparisondock.toggleViewAction())


        self.setProjectTitle("NONE")

        ##### FURTHER INITIALIZAION #####
        #################################

        # set default opacity
        self.sliderTransparency.setValue(50)
        self.transparency_value = 0.5

        # EVENTS-CONNECTIONS

        self.settings_widget.general_settings.researchFieldChanged[str].connect(self.researchFieldChanged)
        self.settings_widget.general_settings.autosaveInfoChanged[int].connect(self.setAutosave)

        self.settings_widget.drawing_settings.borderPenChanged[str, int].connect(self.viewerplus.setBorderPen)
        self.settings_widget.drawing_settings.selectionPenChanged[str, int].connect(self.viewerplus.setSelectionPen)
        self.settings_widget.drawing_settings.borderPenChanged[str, int].connect(self.viewerplus2.setBorderPen)
        self.settings_widget.drawing_settings.selectionPenChanged[str, int].connect(self.viewerplus2.setSelectionPen)

        self.labels_widget.activeLabelChanged.connect(self.viewerplus.setActiveLabel)
        self.labels_widget.activeLabelChanged.connect(self.viewerplus2.setActiveLabel)

        self.labels_widget.visibilityChanged.connect(self.viewerplus.updateVisibility)
        self.labels_widget.visibilityChanged.connect(self.viewerplus2.updateVisibility)

        self.labels_widget.doubleClickLabel[str].connect(self.viewerplus.assignClass)
        self.labels_widget.doubleClickLabel[str].connect(self.viewerplus2.assignClass)

        self.viewerplus.viewHasChanged[float, float, float].connect(self.viewerplus2.setViewParameters)
        self.viewerplus2.viewHasChanged[float, float, float].connect(self.viewerplus.setViewParameters)

        self.viewerplus.customContextMenuRequested.connect(self.openContextMenu)
        self.viewerplus2.customContextMenuRequested.connect(self.openContextMenu)

        self.settings_widget.loadSettings()

        # SWITCH IMAGES
        self.current_image_index = 0

        # Graphics Item of the working area
        self.working_area_rect = None

        # Graphis Item of the prev area
        self.prev_area_rect = None
        self.prev_area = None

        # menu options
        self.mapActionList = []
        self.image2update = None

        # training results
        self.classifier_name = None
        self.dataset_train = None

        # NETWORKS
        self.deepextreme_net = None
        self.classifier = None

        # a dirty trick to adjust all the size..
        self.showMinimized()
        self.showMaximized()

        logfile.info("[INFO] Inizialization finished!")

        # autosave timer
        self.timer = QTimer(self)

        self.updateToolStatus()
        self.disableSplitScreen()

        self.move()

    def checkNewVersion(self):

        github_repo = 'cnr-isti-vclab/TagLab/'
        base_repo = 'https://github.com/' + github_repo
        raw_link = 'https://raw.githubusercontent.com/' + github_repo + 'main/TAGLAB_VERSION'

        # read offline version
        f_off_version = open("TAGLAB_VERSION", "r")
        taglab_offline_version = f_off_version.read()

        #print('Raw link: ' + raw_link)
        try:
            f_online_version = urllib.request.urlopen(raw_link)
        except:
            return taglab_offline_version, False
            
        taglab_online_version = f_online_version.read().decode('utf-8')

        offline_spl_version = taglab_offline_version.split('.')
        online_spl_version = taglab_online_version.split('.')

        #print('offline: ' + str(offline_spl_version))
        #print('online: ' + str(online_spl_version))

        # Check if I need to update TagLab
        need_to_update = False
        i = 0
        while i < len(online_spl_version) and not need_to_update:
            if (not (i < len(offline_spl_version))):
                need_to_update = True
            else:
                if (int(online_spl_version[i]) > int(offline_spl_version[i])):
                    need_to_update = True
                elif (int(online_spl_version[i]) < int(offline_spl_version[i])):
                    need_to_update = False
                    break
            i = i + 1

        return taglab_offline_version, need_to_update


    #just to make the code less verbose
    def newAction(self, text, shortcut, callback):
        action  = QAction(text, self)
        action.setShortcut(QKeySequence(shortcut))
        #compatibility with Qt < 5.10
        if hasattr(action, 'setShortcutVisibleInContextMenu'):
            action.setShortcutVisibleInContextMenu(True)
        action.triggered.connect(callback)
        return action


    def newButton(self, icon, tooltip, style, callback):
        #ICON_SIZE = 48
        ICON_SIZE = 35
        BUTTON_SIZE = 35

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

    @pyqtSlot()
    def updateEditActions(self):

        if self.btnGrid.isChecked():
            self.markEmpty.setVisible(True)
            self.markComplete.setVisible(True)
            self.markIncomplete.setVisible(True)
            self.addNote.setVisible(True)
        else:
            self.markEmpty.setVisible(False)
            self.markComplete.setVisible(False)
            self.markIncomplete.setVisible(False)
            self.addNote.setVisible(False)

        nSelected = len(self.viewerplus.selected_blobs) + len(self.viewerplus2.selected_blobs)
        self.assignAction.setEnabled(nSelected > 0)
        self.deleteAction.setEnabled(nSelected > 0)
        self.mergeAction.setEnabled(nSelected > 1)
        self.divideAction.setEnabled(nSelected > 1)
        self.subtractAction.setEnabled(nSelected > 1)
        self.refineAction.setEnabled(nSelected == 1)
        self.dilateAction.setEnabled(nSelected > 0)
        self.erodeAction.setEnabled(nSelected > 0)
        self.attachBoundariesAction.setEnabled(nSelected == 2)
        self.fillAction.setEnabled(nSelected > 0)


    @pyqtSlot()
    def markEmptyOperation(self):
        self.activeviewer.updateCellState(0)

    @pyqtSlot()
    def markIncompleteOperation(self):
        self.activeviewer.updateCellState(1)

    @pyqtSlot()
    def markCompleteOperation(self):
        self.activeviewer.updateCellState(2)


    @pyqtSlot()
    def addNoteOperation(self):

        if self.btnGrid.isChecked():
            self.activeviewer.addNote()

    def setAutosave(self, interval):
        """
        Set autosave interval. Interval is in minutes. If interval is zero or negative the autosave is disabled.
        """

        if interval > 0:

            # disconnect, just in case..
            try:
                self.timer.timeout.disconnect()
            except:
                pass

            self.timer.timeout.connect(self.autosave)
            self.timer.start(interval * 60 * 1000)   # interval is in seconds
        else:
            self.timer.stop()

    @pyqtSlot()
    def autosave(self):
        filename, file_extension = os.path.splitext(self.project.filename)
        self.project.save(filename + "_autosave.json")

    # call by pressing right button
    def openContextMenu(self, position):

        if len(self.project.images) == 0:
            return

        menu = QMenu(self)
        menu.setAutoFillBackground(True)

        str = "QMenu::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(255, 255, 255);\
            } QMenu::item:disabled { color:rgb(150, 150, 150); }"

        menu.setStyleSheet(str)

        menu.addAction(self.markEmpty)
        menu.addAction(self.markIncomplete)
        menu.addAction(self.markComplete)
        menu.addAction(self.addNote)

        menu.addSeparator()

        menu.addAction(self.assignAction)
        menu.addAction(self.deleteAction)

        menu.addSeparator()

        menu.addAction(self.mergeAction)
        menu.addAction(self.divideAction)
        menu.addAction(self.subtractAction)

        menu.addSeparator()
        menu.addAction(self.refineAction)
        menu.addAction(self.dilateAction)
        menu.addAction(self.erodeAction)
        menu.addAction(self.attachBoundariesAction)
        #menu.addAction(self.refineActionDilate)
        #menu.addAction(self.refineActionErode)
        menu.addAction(self.fillAction)

        viewer = self.sender()
        action = menu.exec_(viewer.mapToGlobal(position))

    def setProjectTitle(self, project_name):

        title = self.TAGLAB_VERSION + " [Project: " + project_name + "]"
        if self.parent() is not None:
            self.parent().setWindowTitle(title)
        else:
            self.setWindowTitle(title)

        if project_name != "NONE":

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

        editAct = QAction("Edit Project...", self)
        editAct.setShortcut('Ctrl+E')
        editAct.setStatusTip("Edit current project")
        editAct.triggered.connect(self.editProject)

        saveAct = QAction("Save Project", self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.setStatusTip("Save current project")
        saveAct.triggered.connect(self.saveProject)

        saveAsAct = QAction("Save As..", self)
        saveAsAct.setShortcut('Ctrl+Alt+S')
        saveAsAct.setStatusTip("Save current project")
        saveAsAct.triggered.connect(self.saveAsProject)

        for i in range(self.maxRecentFiles):
            self.recentFileActs.append(QAction(self, visible=False, triggered=self.openRecentProject))

        newMapAct = QAction("Add New Map..", self)
        newMapAct.setShortcut('Ctrl+L')
        newMapAct.setStatusTip("Add a new map to the project")
        newMapAct.triggered.connect(self.setMapToLoad)

        ### Project
        createDicAct = QAction("Dictionary Editor", self)
        createDicAct.triggered.connect(self.createDictionary)

        customDataAct = QAction("Custom data", self)
        customDataAct.triggered.connect(self.editCustomData)


        ### IMPORT

        appendAct = QAction("Add Another Project", self)
        appendAct.setStatusTip("Add to the current project the annotated images of another project")
        appendAct.triggered.connect(self.importAnnotations)

        importAct = QAction("Import Label Image", self)
        importAct.setStatusTip("Import a Label Image")
        importAct.triggered.connect(self.importLabelMap)

        importShap = QAction("Import Shapefile", self)
        importShap.setStatusTip("Import a Georeferenced Shapefile")
        importShap.triggered.connect(self.importShapefile)

        ### EXPORT

        exportDataTableAct = QAction("Export Annotations as Data Table", self)
        #exportDataTableAct.setShortcut('Ctrl+??')
        exportDataTableAct.setStatusTip("Export current annotations as CSV table")
        exportDataTableAct.triggered.connect(self.exportAnnAsDataTable)

        exportMapAct = QAction("Export Annotations as a Label Image", self)
        #exportMapAct.setShortcut('Ctrl+??')
        exportMapAct.setStatusTip("Export current annotations as a Label Image")
        exportMapAct.triggered.connect(self.exportAnnAsMap)

        exportHistogramAct = QAction("Export Histogram", self)
        # exportHistogramAct.setShortcut('Ctrl+??')
        exportHistogramAct.setStatusTip("Export Histogram")
        exportHistogramAct.triggered.connect(self.exportHistogramFromAnn)

        exportShapefilesAct = QAction("Export as Shapefile", self)
        # exportShapefilesAct.setShortcut('Ctrl+??')
        exportShapefilesAct.setStatusTip("Export current annotations as shapefile")
        exportShapefilesAct.triggered.connect(self.exportAnnAsShapefiles)

        exportGeoRefLabelMapAct = QAction("Export Annotations as a GeoTiff", self)
        # exportShapefilesAct.setShortcut('Ctrl+??')
        exportGeoRefLabelMapAct.setStatusTip("Create a label image and export it as a GeoTiff")
        exportGeoRefLabelMapAct.triggered.connect(self.exportGeoRefLabelMap)

        exportTrainingDatasetAct = QAction("Export New Training Dataset", self)
        #exportTrainingDatasetAct.setShortcut('Ctrl+??')
        exportTrainingDatasetAct.setStatusTip("Export a new training dataset based on the current annotations")
        exportTrainingDatasetAct.triggered.connect(self.exportAnnAsTrainingDataset)

        trainYourNetworkAct = QAction("Train Your Network", self)
        #exportTrainingDatasetAct.setShortcut('Ctrl+??')
        trainYourNetworkAct.setStatusTip("Export a new training dataset and, eventually, train your network on it")
        trainYourNetworkAct.triggered.connect(self.trainYourNetwork)

        settingsAct = QAction("Settings..", self)
        settingsAct.setStatusTip("")
        settingsAct.triggered.connect(self.settings)

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

        menubar = QMenuBar(self)
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

        self.filemenu = menubar.addMenu("&File")
        self.filemenu.setStyleSheet(styleMenu)
        self.filemenu.addAction(newAct)
        self.filemenu.addAction(openAct)
        #self.filemenu.addAction(editAct)
        self.filemenu.addAction(saveAct)
        self.filemenu.addAction(saveAsAct)
        self.filemenu.addSeparator()
        
        for i in range(self.maxRecentFiles):
            self.filemenu.addAction(self.recentFileActs[i])
        self.separatorRecentFilesAct = self.filemenu.addSeparator()
        self.updateRecentFileActions()

        self.submenuImport = self.filemenu.addMenu("Import")
        self.submenuImport.addAction(importAct)
        self.submenuImport.addAction(importShap)
        self.submenuImport.addAction(appendAct)
        self.filemenu.addSeparator()
        self.submenuExport = self.filemenu.addMenu("Export")
        self.submenuExport.addAction(exportDataTableAct)
        self.submenuExport.addAction(exportMapAct)
        self.submenuExport.addAction(exportShapefilesAct)
        self.submenuExport.addAction(exportGeoRefLabelMapAct)
        self.submenuExport.addAction(exportHistogramAct)
        self.submenuExport.addAction(exportTrainingDatasetAct)
        self.filemenu.addSeparator()
        self.filemenu.addAction(trainYourNetworkAct)
        self.filemenu.addSeparator()
        self.filemenu.addAction(settingsAct)

        #### PROJECT MENU

        self.projectmenu = menubar.addMenu("&Project")
        self.projectmenu.addAction(createDicAct)
        self.projectmenu.addAction(customDataAct)
        self.projectmenu.addAction(newMapAct)
        self.submenuEdit = self.filemenu.addMenu("Edit Maps info")
        self.submenuEdit.setEnabled(False)
        #self.projectmenu.addSeparator()


        ###### DEM MENU

        calculateSurfaceAreaAct = QAction("Calculate Surface Area", self)
        calculateSurfaceAreaAct.setStatusTip("Estimate surface area using slope derived from the DEM")
        calculateSurfaceAreaAct.triggered.connect(self.calculateAreaUsingSlope)

        exportClippedRasterAct = QAction("Export Clipped Raster", self)
        # exportShapefilesAct.setShortcut('Ctrl+??')
        exportClippedRasterAct.setStatusTip("Export a raster clipped using visible annotations")
        exportClippedRasterAct.triggered.connect(self.exportClippedRaster)

        switchAct = QAction("Switch RGB/DEM", self)
        # exportShapefilesAct.setShortcut('Ctrl+??')
        switchAct.setStatusTip("Switch between the image and the DEM")
        switchAct.triggered.connect(self.switch)

        self.demmenu = menubar.addMenu("&DEM")
        self.demmenu.setStyleSheet(styleMenu)
        self.demmenu.addAction(switchAct)
        self.demmenu.addAction(calculateSurfaceAreaAct)
        self.demmenu.addAction(exportClippedRasterAct)

        self.editmenu = menubar.addMenu("&Edit")
        self.editmenu.setStyleSheet(styleMenu)
        self.editmenu.addAction(undoAct)
        self.editmenu.addAction(redoAct)
        self.editmenu.addSeparator()
        self.editmenu.addAction(self.assignAction)
        self.editmenu.addAction(self.deleteAction)
        self.editmenu.addSeparator()
        self.editmenu.addAction(self.mergeAction)
        self.editmenu.addAction(self.divideAction)
        self.editmenu.addAction(self.subtractAction)
        self.editmenu.addSeparator()
        self.editmenu.addAction(self.refineAction)
        self.editmenu.addAction(self.dilateAction)
        self.editmenu.addAction(self.erodeAction)
        self.editmenu.addAction(self.attachBoundariesAction)
        self.editmenu.addAction(self.fillAction)

        splitScreenAction = QAction("Enable Split Screen", self)
        splitScreenAction.setShortcut('Alt+S')
        splitScreenAction.setStatusTip("Split screen")
        splitScreenAction.triggered.connect(self.toggleComparison)

        autoMatchLabels = QAction("Compute automatic matches", self)
        autoMatchLabels.setStatusTip("Match labels between two maps automatically")
        autoMatchLabels.triggered.connect(self.autoCorrespondences)

        manualMatchLabels = QAction("Add manual matches", self)
        manualMatchLabels.setStatusTip("Add manual matches")
        manualMatchLabels.triggered.connect(self.matchTool)

        exportMatchLabels = QAction("Export matches", self)
        exportMatchLabels.setStatusTip("Export the current matches")
        exportMatchLabels.triggered.connect(self.exportMatches)

        computeGenets = QAction("Compute genets", self)
        computeGenets.setStatusTip("Compute genet information.")
        computeGenets.triggered.connect(self.computeGenets)

        exportGenetSVG = QAction("Export genet shapes", self)
        exportGenetSVG.setStatusTip("Export genets history of corals in SVG.")
        exportGenetSVG.triggered.connect(self.exportGenetSVG)

        exportGenetCSV = QAction("Export genet data", self)
        exportGenetCSV.setStatusTip("Export genets history of corals in CSV")
        exportGenetCSV.triggered.connect(self.exportGenetCSV)


        self.comparemenu = menubar.addMenu("&Comparison")
        self.comparemenu.setStyleSheet(styleMenu)
        self.comparemenu.addAction(splitScreenAction)
        self.comparemenu.addAction(autoMatchLabels)
        self.comparemenu.addAction(manualMatchLabels)
        self.comparemenu.addAction(exportMatchLabels)

        self.comparemenu.addSeparator()
        self.comparemenu.addAction(computeGenets);
        self.comparemenu.addAction(exportGenetSVG)
        self.comparemenu.addAction(exportGenetCSV)

        self.helpmenu = menubar.addMenu("&Help")
        self.helpmenu.setStyleSheet(styleMenu)
        self.helpmenu.addAction(helpAct)
        self.helpmenu.addAction(aboutAct)

        return menubar

    def updateEditSubMenu(self):

        for action in self.mapActionList:
            self.submenuEdit.removeAction(action)

        self.mapActionList = []

        if not self.project.images:
            self.submenuEdit.setEnabled(False)
        else:
            self.submenuEdit.setEnabled(True)
            for image in self.project.images:
                editMap = QAction(image.name)
                self.submenuEdit.addAction(editMap)
                self.submenuEdit.triggered[QAction].connect(self.editMapSettings)
                self.mapActionList.append(editMap)

    @pyqtSlot()
    def settings(self):

        self.settings_widget.setWindowModality(Qt.WindowModal)
        self.settings_widget.show()

    @pyqtSlot(str)
    def researchFieldChanged(self, str):
        pass

    @pyqtSlot(QAction)
    def editMapSettings(self, openMapAction):

        index = self.mapActionList.index(openMapAction)
        image = self.project.images[index]

        if self.mapWidget is None:
            self.mapWidget = QtMapSettingsWidget(parent=self)
            self.mapWidget.setWindowModality(Qt.WindowModal)
            self.mapWidget.accepted.connect(self.updateMapProperties)

        self.mapWidget.fields["name"]["edit"].setText(image.name)

        rgb_channel = image.getRGBChannel()
        dem_channel = image.getDEMChannel()

        self.mapWidget.fields["rgb_filename"]["edit"].setText(rgb_channel.filename)
        if dem_channel is not None:
            self.mapWidget.fields["depth_filename"]["edit"].setText(dem_channel.filename)
        else:
            self.mapWidget.fields["depth_filename"]["edit"].setText("")

        self.mapWidget.fields["acquisition_date"]["edit"].setText(image.acquisition_date)
        self.mapWidget.fields["px_to_mm"]["edit"].setText(str(image.map_px_to_mm_factor))
        self.mapWidget.enableRGBloading()
        self.image2update = image
        self.mapWidget.accepted.disconnect()
        self.mapWidget.accepted.connect(self.updateMapProperties)
        self.mapWidget.show()

    def toggleRGBDEM(self, viewer):
        """
        Ask to the given viewer to switch between RGB channel and DEM channel.
        """
        if viewer.channel is not None:
            if viewer.channel.type != "DEM":
                channel = viewer.image.getDEMChannel()
                if channel is None:
                   box = QMessageBox()
                   box.setText("DEM not found!")
                   box.exec()
                   return

                viewer.setChannel(channel, switch=True)
            else:
                channel = viewer.image.getRGBChannel()
                if channel is None:
                    box = QMessageBox()
                    box.setText("RGB not found!")
                    box.exec()
                    return
                viewer.setChannel(channel, switch=True)

    @pyqtSlot()
    def switch(self):
        """
        Switch between the RGB and the DEM channel.
        """

        self.toggleRGBDEM(self.viewerplus)
        if self.split_screen_flag:
            self.toggleRGBDEM(self.viewerplus2)

    @pyqtSlot()
    def computeGenets(self):

        img_source_index = self.comboboxSourceImage.currentIndex()
        img_target_index = self.comboboxTargetImage.currentIndex()
        updated_corresp = self.project.updateGenets(img_source_index, img_target_index)
        if self.compare_panel.correspondences is None:
            self.compare_panel.setTable(self.project, img_source_index, img_target_index)
        else:
            self.compare_panel.updateTable(updated_corresp)

    @pyqtSlot()
    def exportGenetSVG(self):
        filters = "SVG (*.svg)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save genet shapes in SVG", self.taglab_dir, filters)
        if not filename:
            return

        self.project.genet.updateGenets()
        self.project.genet.exportSVG(filename)

    @pyqtSlot()
    def exportGenetCSV(self):
        filters = "CSV (*.csv)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save genet data in CSV", self.taglab_dir, filters)
        if not filename:
            return

        self.project.genet.updateGenets()
        self.project.genet.exportCSV(filename)


    @pyqtSlot()
    def autoCorrespondences(self):

        if len(self.project.images) < 2:
            return

        if self.split_screen_flag is False:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Please, enable Split Screen and select the source and the target image (!)")
            msgBox.exec()
            return

        img_source_index = self.comboboxSourceImage.currentIndex()
        img_target_index = self.comboboxTargetImage.currentIndex()

        if img_source_index != img_target_index:

            key = self.project.images[img_source_index].id + "-" + self.project.images[img_target_index].id
            corr = self.project.correspondences.get(key)

            flag_compute = False
            if corr is not None:
                if corr.data.empty is False:
                    reply = QMessageBox.question(self, self.TAGLAB_VERSION,
                                                 "Would you like to clean up the table and replace all the existing matches?",
                                                 QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        flag_compute = True
                else:
                    flag_compute = True
            else:
                flag_compute = True

            if flag_compute is True:
                self.project.computeCorrespondences(img_source_index, img_target_index)
                self.compare_panel.setTable(self.project, img_source_index, img_target_index)
                self.setTool("MATCH")


    @pyqtSlot()
    def exportMatches(self):

        filters = "CSV (*.csv)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save the current matches", self.taglab_dir, filters)

        if filename:
            if self.project.correspondences is not None:
                for key,corr in self.project.correspondences.items():
                    filename = filename.replace('.csv','')
                    corr.data.to_csv(filename + '_' + key + '.csv', index=False)

    @pyqtSlot()
    def toggleGrid(self):

        if self.btnGrid.isChecked():
            self.activeviewer.showGrid()
            self.checkBoxGrid.setChecked(True)

        self.updateEditActions()

    @pyqtSlot()
    def createGrid(self):
        """
        Create a new grid. This special grid is used to better supervise the annotation work.
        """

        if len(self.project.images) < 1:
            self.btnCreateGrid.setChecked(False)
            return

        if self.activeviewer.image.grid is not None:

            reply = QMessageBox.question(self, self.TAGLAB_VERSION,
                                     "Would you like to remove the existing <em>grid</em> and create a new one?",
                                     QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                self.btnCreateGrid.setChecked(False)
                return
            else:
                self.activeviewer.image.grid.undrawGrid()
                self.activeviewer.hideGrid()
                self.btnGrid.setChecked(False)

        if self.gridWidget is None:
            self.gridWidget = QtGridWidget(self.activeviewer, self)
            self.gridWidget.setWindowModality(Qt.NonModal)
            self.gridWidget.show()
            self.gridWidget.accepted.connect(self.assignGrid)
            self.gridWidget.btnCancel.clicked.connect(self.cancelGrid)


    @pyqtSlot()
    def cancelGrid(self):
        self.gridWidget.grid.undrawGrid()
        self.gridWidget.close()
        self.gridWidget = None
        self.resetToolbar()


    @pyqtSlot()
    def assignGrid(self):
        """
        Assign the grid created to the corresponding image.
        """
        self.activeviewer.image.grid = self.gridWidget.grid
        self.resetToolbar()
        self.activeviewer.showGrid()
        self.checkBoxGrid.setChecked(True)
        self.gridWidget = None

    @pyqtSlot()
    def toggleComparison(self):
        if self.split_screen_flag is True:
            self.disableSplitScreen()
        else:
            self.enableSplitScreen()

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
        if self.activeviewer:
            active_annotations = self.activeviewer.annotations
        else:
            active_annotations = self.viewerplus.annotations

        if event.key() == Qt.Key_Escape:
            key_pressed = 'ESC'
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            key_pressed = 'ENTER'
        else:
            if event.key() < 0xfffff:
                key_pressed = chr(event.key())
            else:
                key_pressed = event.text()

        if modifiers == Qt.ControlModifier:
            msg = "[KEYPRESS] Key CTRL + '" + key_pressed + "' has been pressed."
        elif modifiers == Qt.ShiftModifier:
            msg = "[KEYPRESS] Key ALT + '" + key_pressed + "' has been pressed."
        elif modifiers == Qt.AltModifier:
            msg = "[KEYPRESS] Key SHIFT + '" + key_pressed + "' has been pressed."
        else:
            msg = "[KEYPRESS] Key '" + key_pressed + "' has been pressed."

        logfile.info(msg)

        if event.key() == Qt.Key_Escape:
            for viewer in (self.viewerplus, self.viewerplus2):
            #if self.activeviewer is not None:
            # RESET CURRENT OPERATION
                viewer.resetSelection()
                viewer.resetTools()

                message = "[TOOL][" + viewer.tools.tool + "] Current operation has been canceled."
                logfile.info(message)

        elif event.key() == Qt.Key_S and modifiers & Qt.ControlModifier:
            self.save()

        elif event.key() == Qt.Key_S and modifiers & Qt.AltModifier:

            if self.split_screen_flag is True:
                self.disableSplitScreen()
            else:
                self.enableSplitScreen()

        elif event.key() == Qt.Key_A:
            self.assignOperation()

        elif event.key() == Qt.Key_Delete:
            self.deleteSelectedBlobs()

        elif event.key() == Qt.Key_X:
            pass

        elif event.key() == Qt.Key_B:
            self.attachBoundaries()

        elif event.key() == Qt.Key_M:
            # MERGE OVERLAPPED BLOBS
            self.union()

        elif event.key() == Qt.Key_C:
            # TOGGLE RGB/DEPTH CHANNELS
            self.switch()

        elif event.key() == Qt.Key_S:
            # SUBTRACTION BETWEEN TWO BLOBS (A = A / B), THEN BLOB B IS DELETED
            self.subtract()

        elif event.key() == Qt.Key_D:
            # SUBTRACTION BETWEEN TWO BLOBS (A = A / B), BLOB B IS NOT DELETED
            self.divide()

        elif event.key() == Qt.Key_R:
            self.refineBorder()

        elif event.key() == Qt.Key_Plus:
            self.dilate()
            # self.refineBorderDilate()

        elif event.key() == Qt.Key_Minus:
            self.erode()
            # self.refineBorderDilate()

        elif event.key() == Qt.Key_F:
            self.fillLabel()

        elif event.key() == Qt.Key_G:

            if self.btnGrid.isChecked():
                self.activeviewer.updateCellState(None)

        elif event.key() == Qt.Key_1:
            # ACTIVATE "MOVE" TOOL
            self.move()

        elif event.key() == Qt.Key_2:
            # ACTIVATE "4-CLICK" TOOL
            self.deepExtreme()

        elif event.key() == Qt.Key_3:
            # ACTIVATE "POSITIVE/NEGATIVE CLICK" TOOL
            self.ritm()

        elif event.key() == Qt.Key_4:
            # ACTIVATE "FREEHAND" TOOL
            self.freehandSegmentation()

        elif event.key() == Qt.Key_5:
            # ACTIVATE "ASSIGN" TOOL
            self.assign()

        elif event.key() == Qt.Key_6:
            # ACTIVATE "EDIT BORDER" TOOL
            self.editBorder()

        elif event.key() == Qt.Key_7:
            # ACTIVATE "CUT SEGMENTATION" TOOL
            self.cut()

        elif event.key() == Qt.Key_8:
            # ACTIVATE "CREATE CRACK" TOOL
            self.createCrack()

        elif event.key() == Qt.Key_9:
            # ACTIVATE "RULER" TOOL
            self.ruler()

        elif event.key() == Qt.Key_0:
            # FULLY AUTOMATIC SEGMENTATION
            self.selectClassifier()

        #elif event.key() == Qt.Key_P:
        #    self.drawDeepExtremePoints()
        #
        # elif event.key() == Qt.Key_Y:
        #     self.refineAllBorders()

        elif event.key() == Qt.Key_Home:
            # ASSIGN LABEL
            active_annotations.refine_depth_weight += 0.1;
            if active_annotations.refine_depth_weight > 1.0:
                active_annotations.refine_depth_weight = 1.0;
            print("Depth weight: " + str(active_annotations.refine_depth_weight))

        elif event.key() == Qt.Key_End:
            # ASSIGN LABEL
            active_annotations.refine_depth_weight -= 0.1;
            if active_annotations.refine_depth_weight < 0.0:
                active_annotations.refine_depth_weight = 0.0;
            print("Depth weight: " + str(active_annotations.refine_depth_weight))


        elif event.key() == Qt.Key_BracketLeft:
            active_annotations.refine_conservative *= 0.9
            print("Conservative: " + str(active_annotations.refine_conservative))

        elif event.key() == Qt.Key_BracketRight:
            active_annotations.refine_conservative *= 1.1
            print("Conservative: " + str(active_annotations.refine_conservative))

        elif event.key() == Qt.Key_Space:
            if self.activeviewer.tools.tool == "MATCH":
                self.createMatch()
            else:
                self.activeviewer.tools.applyTool()


    def disableSplitScreen(self):

        if self.activeviewer is not None:
            if self.activeviewer.tools.tool == "MATCH":
                self.setTool("MOVE")

        self.viewerplus2.hide()
        self.comboboxTargetImage.hide()
        self.blobdock.show()

        if self.comparemenu is not None:
            splitScreenAction = self.comparemenu.actions()[0]
            if splitScreenAction is not None:
                splitScreenAction.setText("Enable Split Screen")

        # just inb case..
        self.viewerplus2.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage)

        # disconnect all slots
        self.viewerplus2.viewUpdated[QRectF].disconnect()

        self.btnSplitScreen.setChecked(False)
        self.split_screen_flag = False


    def enableSplitScreen(self):

        self.viewerplus.viewChanged()

        if len(self.project.images) > 1:

            QApplication.setOverrideCursor(Qt.WaitCursor)

            index = self.comboboxSourceImage.currentIndex()
            if index < 0:
                index = 0

            if index <= len(self.project.images) - 2:
                index_to_set = index
            else:
                index_to_set = index-1

            self.comboboxSourceImage.currentIndexChanged.disconnect()
            self.comboboxTargetImage.currentIndexChanged.disconnect()

            self.comboboxSourceImage.setCurrentIndex(index_to_set)
            self.comboboxTargetImage.setCurrentIndex(index_to_set + 1)

            self.viewerplus.clear()
            self.viewerplus2.clear()
            self.viewerplus.setProject(self.project)
            self.viewerplus2.setProject(self.project)
            self.viewerplus.setImage(self.project.images[index_to_set])
            self.viewerplus2.setImage(self.project.images[index_to_set + 1])

            self.comboboxSourceImage.currentIndexChanged.connect(self.sourceImageChanged)
            self.comboboxTargetImage.currentIndexChanged.connect(self.targetImageChanged)

            QApplication.restoreOverrideCursor()

        self.viewerplus2.show()
        self.comboboxTargetImage.show()
        self.viewerplus.viewChanged()

        self.viewerplus2.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage)

        if self.comparemenu is not None:
            splitScreenAction = self.comparemenu.actions()[0]
            if splitScreenAction is not None:
                splitScreenAction.setText("Disable Split Screen")

        self.blobdock.hide()

        self.btnSplitScreen.setChecked(True)
        self.split_screen_flag = True

    def createMatch(self):
        """
        Create a new match and add it to the correspondences table.
        """

        if self.split_screen_flag is True:
            sel1 = self.viewerplus.selected_blobs
            sel2 = self.viewerplus2.selected_blobs

            # this should not happen at all
            #if len(sel1) > 1 and len(sel2) > 1:
            #    return

            if len(sel1) == 0 and len(sel2) == 0:
                return

            img_source_index = self.comboboxSourceImage.currentIndex()
            img_target_index = self.comboboxTargetImage.currentIndex()
            self.project.addCorrespondence(img_source_index, img_target_index, sel1, sel2)

            if self.compare_panel.correspondences is None:
                self.setTable(self.project, img_source_index, img_target_index)
            else:
                corr = self.project.getImagePairCorrespondences(img_source_index, img_target_index)
                self.compare_panel.updateTable(corr)

            # highlight the correspondences just added and show it by scroll
            if len(sel1) > 0:
                self.showCluster(sel1[0].id, is_source=True, center=False)
            elif len(sel2) > 0:
                self.showCluster(sel2[0].id, is_source=False, center=False)


    @pyqtSlot()
    def showConnectionCluster(self):
        indexes = self.compare_panel.data_table.selectionModel().selectedRows()
        if len(indexes) == 0:
            return

        img_source_index = self.comboboxSourceImage.currentIndex()
        img_target_index = self.comboboxTargetImage.currentIndex()
        corr = self.project.getImagePairCorrespondences(img_source_index, img_target_index)
        index = self.compare_panel.sortfilter.mapToSource(indexes[0]);
        row = corr.data.iloc[index.row()]
        blob1id = row['Blob1']
        blob2id = row['Blob2']

        if blob1id >= 0:
            self.showCluster(blob1id, is_source=True, center=True)
        else:
            self.showCluster(blob2id, is_source=False, center=True)


    @pyqtSlot()
    def deleteMatch(self):

        if self.activeviewer is None or self.inactiveviewer is None:
            return

        indexes = self.compare_panel.data_table.selectionModel().selectedRows()
        if len(indexes) == 0:
            return
        indexes = [a.row() for a in indexes]

        img_source_index = self.comboboxSourceImage.currentIndex()
        img_target_index = self.comboboxTargetImage.currentIndex()
        corr = self.project.getImagePairCorrespondences(img_source_index, img_target_index)
        corr.deleteCluster(indexes)

        self.viewerplus.resetSelection()
        self.viewerplus2.resetSelection()

        if self.compare_panel.correspondences is not None:
            self.compare_panel.setTable(self.project, img_source_index, img_target_index)
        else:
            self.compare_panel.updateTable(corr)


    @pyqtSlot()
    def showMatch(self):

        if self.activeviewer is None or self.inactiveviewer is None:
            return

        if self.activeviewer.tools.tool != "MATCH":
            return

        selected = self.activeviewer.selected_blobs
        if len(selected) == 0:
            self.inactiveviewer.resetSelection()
            return
        if len(selected) > 1:
            box = QMessageBox()
            box.setText("Huston we have a problem!")
            box.exec()
            return

        blob = selected[0]
        if self.activeviewer == self.viewerplus:
            self.showCluster(blob.id, is_source=True, center=False)   # this blob is a source
        else:
            self.showCluster(blob.id, is_source=False, center=False)  # this blob is a target


    def showCluster(self, blobid, is_source, center):

        corr = self.project.getImagePairCorrespondences(self.comboboxSourceImage.currentIndex(),
                                                        self.comboboxTargetImage.currentIndex())
        sourcecluster, targetcluster, rows = corr.findCluster(blobid, is_source)

        self.viewerplus.resetSelection()

        sourceboxes = []
        for id in sourcecluster:
            blob = self.viewerplus.annotations.blobById(id)
            sourceboxes.append(blob.bbox)
            self.viewerplus.addToSelectedList(blob)

        scale = self.viewerplus.px_to_mm
        if center is True and len(sourceboxes) > 0:
            box = Mask.jointBox(sourceboxes)
            x = box[1] + box[2] / 2
            y = box[0] + box[3] / 2
            self.viewerplus.centerOn(x, y)

        self.viewerplus2.resetSelection()

        targetboxes = []
        for id in targetcluster:
            blob = self.viewerplus2.annotations.blobById(id)
            targetboxes.append(blob.bbox)
            self.viewerplus2.addToSelectedList(blob)

        scale = self.viewerplus2.px_to_mm
        if center is True and len(targetboxes) > 0:
            box = Mask.jointBox(sourceboxes + targetboxes)
            x = box[1] + box[2] / 2
            y = box[0] + box[3] / 2
            self.viewerplus2.centerOn(x, y)


        self.compare_panel.selectRows(rows)

    @pyqtSlot(str)
    def updateVisibleMatches(self, type):

        if self.activeviewer.tools.tool == "MATCH":

            if type == 'all':
                for b in self.viewerplus.annotations.seg_blobs:
                    self.viewerplus.setBlobVisible(b, True)
                for b in self.viewerplus2.annotations.seg_blobs:
                    self.viewerplus2.setBlobVisible(b, True)
                return

            img_source_index = self.comboboxSourceImage.currentIndex()
            img_target_index = self.comboboxTargetImage.currentIndex()
            correspondences = self.project.getImagePairCorrespondences(img_source_index, img_target_index)
            data = correspondences.data
            selection = data.loc[data["Action"] == type]
            sourceblobs = selection['Blob1'].tolist()
            targetblobs = selection['Blob2'].tolist()
            for b in self.viewerplus.annotations.seg_blobs:
                self.viewerplus.setBlobVisible(b, b.id in sourceblobs)
            for b in self.viewerplus2.annotations.seg_blobs:
                self.viewerplus2.setBlobVisible(b, b.id in targetblobs)

    @pyqtSlot(str)
    def updateAreaMode(self, type):
        """
        Update the area values of the current correspondence table.
        If area mode is 'surface area' the surface values are shown in the current correspondences table,
        otherwise the standard area values.
        """

        if self.activeviewer.tools.tool == "MATCH":
            img_source_index = self.comboboxSourceImage.currentIndex()
            img_target_index = self.comboboxTargetImage.currentIndex()
            correspondences = self.project.getImagePairCorrespondences(img_source_index, img_target_index)

            if type == "surface area":
                correspondences.updateAreas(use_surface_area=True)
            else:
                correspondences.updateAreas(use_surface_area=False)

            self.compare_panel.data_table.update()


    @pyqtSlot()
    def undo(self):
        if self.activeviewer:
            self.activeviewer.undo()

    @pyqtSlot()
    def redo(self):
        if self.activeviewer:
            self.activeviewer.redo()

    @pyqtSlot()
    def setActiveViewer(self):
        self.activeviewer = self.sender()
        if self.activeviewer is not self.viewerplus:
            self.inactiveviewer = self.viewerplus
        else:
            self.inactiveviewer = self.viewerplus2

        self.inactiveviewer.resetTools()

    def updateImageSelectionMenu(self):

        self.comboboxSourceImage.currentIndexChanged.disconnect()
        self.comboboxTargetImage.currentIndexChanged.disconnect()

        index1 = self.comboboxSourceImage.currentIndex()
        index2 = self.comboboxTargetImage.currentIndex()

        if index1 < 1:
            index1 = 0

        if index2 < 1:
            index2 = 0

        # update the image names
        self.comboboxSourceImage.clear()
        self.comboboxTargetImage.clear()
        for image in self.project.images:
            self.comboboxSourceImage.addItem(image.name)
            self.comboboxTargetImage.addItem(image.name)

        self.comboboxSourceImage.setCurrentIndex(index1)
        self.comboboxTargetImage.setCurrentIndex(index2)

        self.comboboxSourceImage.currentIndexChanged.connect(self.sourceImageChanged)
        self.comboboxTargetImage.currentIndexChanged.connect(self.targetImageChanged)

    def updateComboboxSourceImage(self, index):
        """
        Update the combobox without changing the source image.
        """
        self.comboboxSourceImage.disconnect()
        self.comboboxSourceImage.setCurrentIndex(index)
        self.comboboxSourceImage.currentIndexChanged.connect(self.sourceImageChanged)

    def updateComboboxTargetImage(self, index):
        """
        Update the combobox without changing the target image.
        """
        self.comboboxTargetImage.disconnect()
        self.comboboxTargetImage.setCurrentIndex(index)
        self.comboboxTargetImage.currentIndexChanged.connect(self.targetImageChanged)

    @pyqtSlot(int)
    def sourceImageChanged(self, index1):

        N = len(self.project.images)
        if index1 == -1 or index1 >= N:
            return

        self.viewerplus.clear()
        self.btnGrid.setChecked(False)

        # target and source image cannot be the same !!
        index2 = self.comboboxTargetImage.currentIndex()
        if index1 == index2:
            index2 = (index1 + 1) % N
            self.viewerplus2.clear()
            self.viewerplus2.setProject(self.project)
            self.viewerplus2.setImage(self.project.images[index2])
            self.updateComboboxTargetImage(index2)

        self.viewerplus.setProject(self.project)
        self.viewerplus.setImage(self.project.images[index1])

        if self.compare_panel.isVisible():
            self.compare_panel.setTable(self.project, index1, index2)

    @pyqtSlot(int)
    def targetImageChanged(self, index2):

        N = len(self.project.images)
        if index2 == -1 or index2 >= N:
            return

        self.viewerplus2.clear()
        self.btnGrid.setChecked(False)

        # target and source image cannot be the same !!
        index1 = self.comboboxSourceImage.currentIndex()
        if index1 == index2:
            index1 = (index2 - 1) % N
            self.viewerplus.clear()
            self.viewerplus.setProject(self.project)
            self.viewerplus.setImage(self.project.images[index1])
            self.updateComboboxSourceImage(index1)

        self.viewerplus2.setProject(self.project)
        self.viewerplus2.setImage(self.project.images[index2])

        if self.compare_panel.isVisible():
            self.compare_panel.setTable(self.project, index1, index2)


    @pyqtSlot()
    def sliderTransparencyChanged(self):
        #TODO should be (self, value) as the signal is supposed to send a value!
        value = self.sender().value()
        # update transparency value
        str1 = "Transparency {}%".format(value)
        self.lblSlider.setText(str1)
        self.viewerplus.applyTransparency(value)

        if self.viewerplus2.isVisible():
            self.viewerplus2.applyTransparency(value)


    @pyqtSlot()
    def updateViewInfo(self):


        topleft = self.viewerplus.mapToScene(QPoint(0, 0))
        bottomright = self.viewerplus.mapToScene(self.viewerplus.viewport().rect().bottomRight())

        (left, top) = self.viewerplus.clampCoords(topleft.x(), topleft.y())
        (right, bottom) = self.viewerplus.clampCoords(bottomright.x(), bottomright.y())
        self.updateMousePos(0, 0) #todo we should separate zoom from coords
        zf = self.viewerplus.zoom_factor * 100.0
        zoom = "{:6.0f}%".format(zf)
        self.labelZoomInfo.setText(zoom)


        self.map_top = top
        self.map_left = left
        self.map_bottom = bottom
        self.map_right = right

    @pyqtSlot(float, float)
    def updateMousePos(self, x, y):
        zf = self.viewerplus.zoom_factor * 100.0
        zoom = "{:6.0f}%".format(zf)
        left = "x: {:5d}".format(int(round(x)))
        top = "y: {:5d}".format(int(round(y)))

        self.labelZoomInfo.setText(zoom)
        self.labelMouseLeftInfo.setText(left)
        self.labelMouseTopInfo.setText(top)
        #text = "| " + zoom.ljust(8) + " | " + left.ljust(5, '&nbsp;') + ", " + right.ljust(5)
        #self.labelViewInfo.setText(text)


    def resetAll(self):

        if self.gridWidget is not None:
            self.gridWidget.beforeClose()
            self.gridWidget = None

        self.viewerplus.clear()
        self.viewerplus2.clear()
        self.mapviewer.clear()
        self.viewerplus.resetTools()
        self.viewerplus2.resetTools()
        self.resetToolbar()

        self.viewerplus.hideScalebar()

        # RE-INITIALIZATION

        self.mapWidget = None
        self.classifierWidget = None
        self.newDatasetWidget = None
        self.trainYourNetworkWidget = None
        self.trainResultsWidget = None
        self.progress_bar = None
        self.classifier_name = None
        self.dataset_train_info = None
        self.project = Project()
        self.project.loadDictionary(self.default_dictionary)
        self.last_image_loaded = None
        self.activeviewer = None
        self.compare_panel.clear()
        self.comboboxSourceImage.clear()
        self.comboboxTargetImage.clear()
        self.resetPanelInfo()
        self.disableSplitScreen()
        self.updateEditSubMenu()

    def resetToolbar(self):

        self.btnMove.setChecked(False)
        self.btnAssign.setChecked(False)
        self.btnEditBorder.setChecked(False)
        self.btnCut.setChecked(False)
        self.btnFreehand.setChecked(False)
        self.btnWatershed.setChecked(False)
        self.btnBricksSegmentation.setChecked(False)
        self.btnRuler.setChecked(False)
        self.btnCreateCrack.setChecked(False)
        #self.btnSplitBlob.setChecked(False)
        self.btnDeepExtreme.setChecked(False)
        self.btnRitm.setChecked(False)
        self.btnCreateGrid.setChecked(False)
        #self.viewerplus.hideGrid()
        #self.viewerplus2.hideGrid()
        self.btnGrid.setChecked(False)
        self.btnMatch.setChecked(False)
        self.btnAutoClassification.setChecked(False)
        if self.scale_widget is not None:
            self.scale_widget.close()
            self.scale_widget = None

    def setTool(self, tool):
        tools = {
            "MOVE"         : ["Pan"          , self.btnMove],
            "CREATECRACK"  : ["Crack"        , self.btnCreateCrack],
            #"SPLITBLOB"   : ["Split Blob"   , self.btnSplitBlob],
            "ASSIGN"       : ["Assign"       , self.btnAssign],
            "EDITBORDER"   : ["Edit Border"  , self.btnEditBorder],
            "CUT"          : ["Cut"          , self.btnCut],
            "FREEHAND"     : ["Freehand"     , self.btnFreehand],
            "WATERSHED"    : ["Watershed"    , self.btnWatershed],
            "BRICKS":        ["Bricks",        self.btnBricksSegmentation],
            "RULER"        : ["Ruler"        , self.btnRuler],
            "DEEPEXTREME"  : ["4-click"      , self.btnDeepExtreme],
            "MATCH"        : ["Match"        , self.btnMatch],
            "RITM"         : ["Ritm"         , self.btnRitm]
        }
        newtool = tools[tool]
        self.resetToolbar()
        self.viewerplus.setTool(tool)
        self.viewerplus2.setTool(tool)
        newtool[1].setChecked(True)
        logfile.info("[TOOL][" + tool + "] Tool activated")
        self.infoWidget.setInfoMessage(newtool[0] + " Tool is active")
        self.comboboxSourceImage.setEnabled(True)
        self.comboboxTargetImage.setEnabled(True)

        if tool == "MATCH":

            if self.split_screen_flag == False:
                self.enableSplitScreen()

            self.labelsdock.hide()
            self.comparisondock.show()
        else:
            # settings when MATCH tool is disactive

            self.comparisondock.hide()
            self.labelsdock.show()


    @pyqtSlot()
    def move(self):
        """
        Activate the tool "move".
        """
        self.setTool("MOVE")


    @pyqtSlot()
    def createCrack(self):
        """
        Activate the tool "Create Crack".
        """
        self.setTool("CREATECRACK")


    # @pyqtSlot()
    # def splitBlob(self):
    #     """
    #     Activate the tool "Split Blob".
    #     """
    #     self.setTool("SPLITBLOB")

    @pyqtSlot()
    def assign(self):
        """
        Activate the tool "Assign" to assign a class to an existing blob.
        """
        self.setTool("ASSIGN")

    @pyqtSlot()
    def editBorder(self):
        """
        Activate the tool "EDITBORDER" for pixel-level editing operations.
        NOTE: it works one blob at a time (!)
        """
        self.setTool("EDITBORDER")

    @pyqtSlot()
    def cut(self):
        """
        CUT
        """
        self.setTool("CUT")

    @pyqtSlot()
    def freehandSegmentation(self):
        """
        Activate the tool "FREEHAND" for manual segmentation.
        """
        self.setTool("FREEHAND")

    @pyqtSlot()
    def watershedSegmentation(self):
        """
        Activate the tool "Brush" for large area segmentation.
        """
        self.setTool("WATERSHED")

    @pyqtSlot()
    def bricksSegmentation(self):
        """
        Activate the tool to segment single bricks element.
        """
        self.setTool("BRICKS")

    @pyqtSlot()
    def ruler(self):
        """
        Activate the "ruler" tool. The tool allows to measure the distance between two points or between two blob centroids.
        """
        self.setTool("RULER")
        if self.scale_widget is None:
            self.scale_widget = QtScaleWidget(parent=self)
            self.scale_widget.setWindowModality(Qt.NonModal)
            self.scale_widget.setScale(self.activeviewer.image.pixelSize())
            self.scale_widget.show()
            self.activeviewer.tools.tools["RULER"].measuretaken[float].connect(self.scale_widget.setMeasure)
            self.scale_widget.newscale[float].connect(self.updateMapScale)
            self.scale_widget.btnOk.clicked.connect(self.closeScaleWidget)
            self.scale_widget.closewidget.connect(self.closeScaleWidget)

    @pyqtSlot()
    def closeScaleWidget(self):
        self.scale_widget.close()
        self.scale_widget = None
        self.setTool("MOVE")

    @pyqtSlot()
    def deepExtreme(self):
        """
        Activate the "Deep Extreme" tool. The segmentation is performed by selecting four points at the
        extreme of the corals and confirm the points by pressing SPACE.
        """
        self.setTool("DEEPEXTREME")

    @pyqtSlot()
    def ritm(self):
        """
        Activate the "Interactive click-based segmentation" tool.
        The segmentation is performed by adding positive or negative clicks.
        """
        self.setTool("RITM")

    @pyqtSlot()
    def matchTool(self):
        """
        Activate the "Match" tool
        """
        if len(self.project.images) < 2:
            box = QMessageBox()
            box.setText("This project has only a single map.")
            box.exec()
            self.move()
            return

        if self.split_screen_flag is False:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Please, enable Split Screen and select the source and the target image (!)")
            msgBox.exec()
            self.move()
            return

        if self.btnMatch.isChecked() is False:
            self.setTool("MOVE")
        else:
            self.setTool("MATCH")
            img_source_index = self.comboboxSourceImage.currentIndex()
            img_target_index = self.comboboxTargetImage.currentIndex()
            self.compare_panel.setTable(self.project, img_source_index, img_target_index)

    @pyqtSlot()
    def noteChanged(self):

        if len(self.activeviewer.selected_blobs) > 0:
            for blob in self.activeviewer.selected_blobs:
                blob.note = self.editNote.toPlainText()

    def updatePanelInfo(self, blob):
        self.groupbox_blobpanel.update(blob)

    @pyqtSlot()
    def resetPanelInfo(self):
        self.groupbox_blobpanel.clear()


    def deleteSelectedBlobs(self):
        if self.viewerplus.tools.tool == 'MATCH':
            self.deleteMatch()
        #disable delete blobs while creating new ones
        elif self.viewerplus.tools.tool == 'RITM' and self.viewerplus.tools.tools['RITM'].work_area_bbox[2] > 0:
             return False
        else:
            self.activeviewer.deleteSelectedBlobs()
            logfile.info("[OP-DELETE] Selected blobs has been DELETED")

#OPERATIONS

    def assignOperation(self):
        view = self.activeviewer
        if view is None:
            return
        for blob in view.selected_blobs:
            view.setBlobClass(blob, self.labels_widget.getActiveLabelName())
        view.saveUndo()
        view.resetSelection()


    def union(self):
        """
        blob A = blob A U blob B
        """
        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) > 1:

            message = "[OP-MERGE] MERGE OVERLAPPED LABELS operation begins.. (number of selected blobs: " + str(len(view.selected_blobs)) + ")"
            logfile.info(message)

            #union returns a NEW blob
            union_blob = view.annotations.union(view.selected_blobs)

            if union_blob is None:
                logfile.info("[OP-MERGE] INVALID MERGE OVERLAPPED LABELS -> blobs are separated.")
            else:
                for blob in view.selected_blobs:
                    view.removeBlob(blob)
                    self.logBlobInfo(blob, "[OP-MERGE][BLOB-REMOVED]")

                view.addBlob(union_blob, selected=True)
                view.saveUndo()

                self.logBlobInfo(union_blob, "[OP-MERGE][BLOB-CREATED]")

            logfile.info("[OP-MERGE] MERGE OVERLAPPED LABELS operation ends.")

        else:
            self.infoWidget.setWarningMessage("You need to select at least <em>two</em> blobs for MERGE OVERLAPPED LABELS operation.")


    def subtract(self):
        """
        blob A = blob A / blob B
        """
        view = self.activeviewer
        if view is None:
            return


        if len(view.selected_blobs) == 2:

            message = "[OP-SUBTRACT] SUBTRACT LABELS operation begins.. (number of selected blobs: " + str(len(view.selected_blobs)) + ")"
            logfile.info(message)

            selectedA = view.selected_blobs[0]
            selectedB = view.selected_blobs[1]

            #blobA and will be modified, make a copy!
            blobA = selectedA.copy()

            flag_intersection = view.annotations.subtract(blobA, selectedB)

            if flag_intersection:

                self.logBlobInfo(selectedA, "[OP-SUBTRACT][BLOB-SELECTED]")
                self.logBlobInfo(blobA, "[OP-SUBTRACT][BLOB-EDITED]")
                self.logBlobInfo(selectedB, "[OP-SUBTRACT][BLOB-REMOVED]")

                view.removeBlob(selectedA)
                view.removeBlob(selectedB)
                view.addBlob(blobA, selected=True)
                view.saveUndo()

            logfile.info("[OP-SUBTRACT] SUBTRACT LABELS operation ends.")

        else:

            self.infoWidget.setInfoMessage("You need to select <em>two</em> blobs for SUBTRACT operation.")

    def divide(self):
        """
        Separe intersecting blob
        """
        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) == 2:

            message = "[OP-DIVIDE] DIVIDE LABELS operation begins.. (number of selected blobs: " + str(len(view.selected_blobs)) + ")"
            logfile.info(message)

            selectedA = view.selected_blobs[0]
            selectedB = view.selected_blobs[1]

            #blobA and blobB and will be modified, make a copy!
            blobA = selectedA.copy()
            blobB = selectedB.copy()

            intersects = view.annotations.subtract(blobB, blobA)

            if not intersects: #this means one blob B is inside blob A
                intersects = view.annotations.subtract(blobA, blobB)

            if intersects:
                self.logBlobInfo(selectedA, "[OP-DIVIDE][BLOB-SELECTED]")
                self.logBlobInfo(blobA, "[OP-DIVIDE][BLOB-EDITED]")
                self.logBlobInfo(selectedB, "[OP-DIVIDE][BLOB-SELECTED]")
                self.logBlobInfo(blobB, "[OP-DIVIDE][BLOB-EDITED]")

                view.updateBlob(selectedA, blobA, selected=False)
                view.updateBlob(selectedB, blobB, selected=False)
                view.saveUndo()

            logfile.info("[OP-DIVIDE] DIVIDE LABELS operation ends.")

        else:

            self.infoWidget.setInfoMessage("You need to select <em>two</em> blobs for DIVIDE operation.")

    def dilate(self):
        """
        Dilate the selected blobs.
        """
        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) > 0:

            blobs = view.selected_blobs
            for blob in blobs:
                blob_dilated = blob.copy()
                blob_dilated.dilate(size=3)
                view.updateBlob(blob, blob_dilated, selected=True)

            view.saveUndo()

    def erode(self):
        """
        Erode the selected blobs.
        """
        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) > 0:

            blobs = view.selected_blobs
            for blob in blobs:
                blob_eroded = blob.copy()
                blob_eroded.erode(size=3)
                view.updateBlob(blob, blob_eroded, selected=True)

            view.saveUndo()

    def attachBoundaries(self):
        """
        Two adjacent blobs are dilated and then divided.
        """
        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) == 2:

            selectedA = view.selected_blobs[0]
            selectedB = view.selected_blobs[1]

            #blobA and blobB and will be modified, make a copy!
            blobA = selectedA.copy()
            blobB = selectedB.copy()

            blobA.dilate(size=4)
            blobB.dilate(size=4)

            intersects = view.annotations.subtract(blobA, blobB)

            self.logBlobInfo(selectedA, "[OP-DIVIDE][BLOB-SELECTED]")
            self.logBlobInfo(blobA, "[OP-DIVIDE][BLOB-EDITED]")
            self.logBlobInfo(selectedB, "[OP-DIVIDE][BLOB-SELECTED]")
            self.logBlobInfo(blobB, "[OP-DIVIDE][BLOB-EDITED]")

            view.updateBlob(selectedA, blobA, selected=False)
            view.updateBlob(selectedB, blobB, selected=False)
            view.saveUndo()

        else:

            self.infoWidget.setInfoMessage("You need to select <em>two</em> blobs for this operation.")

    def attachBoundaries2(self):
        """
        Two adjacent blobs are dilated and then divided. Note that only the close part is dilated.
        """
        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) == 2:

            selectedA = view.selected_blobs[0]
            selectedB = view.selected_blobs[1]

            #blobA and blobB and will be modified, make a copy!
            blobA = selectedA.copy()
            blobB = selectedB.copy()
            blobAs = selectedA.copy()
            blobAb = selectedA.copy()
            blobBs = selectedB.copy()
            blobBb = selectedB.copy()

            blobAb.dilate(size=9)
            blobBb.dilate(size=9)
            blobAs.dilate(size=5)
            blobBs.dilate(size=5)

            # A = A U (B intersect C)
            view.annotations.addingIntersection(blobA, blobAs, blobBb)
            view.annotations.addingIntersection(blobB, blobBs, blobAb)

            intersects = view.annotations.subtract(blobB, blobA)
            if not intersects: #this means one blob B is inside blob A
                intersects = view.annotations.subtract(blobA, blobB)

            self.logBlobInfo(selectedA, "[OP-DIVIDE][BLOB-SELECTED]")
            self.logBlobInfo(blobAs, "[OP-DIVIDE][BLOB-EDITED]")
            self.logBlobInfo(selectedB, "[OP-DIVIDE][BLOB-SELECTED]")
            self.logBlobInfo(blobBs, "[OP-DIVIDE][BLOB-EDITED]")

            view.updateBlob(selectedA, blobA, selected=False)
            view.updateBlob(selectedB, blobB, selected=False)
            view.saveUndo()

        else:

            self.infoWidget.setInfoMessage("You need to select <em>two</em> blobs for this operation.")

    def refineBorderDilate(self):

        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) == 1:
            selected = view.selected_blobs[0]
            if view.refine_original_blob is None or view.refine_original_blob.id != selected.id:
                view.refine_grow = 0
                view.refine_original_mask = None

        logfile.info("[OP-REFINE-BORDER-DILATE] DILATE-BORDER operation begins..")

        view.refine_grow += 2
        self.refineBorder()

        logfile.info("[OP-REFINE-BORDER-DILATE] DILATE-BORDER operation ends.")


    def refineBorderErode(self):

        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) == 1:
            selected = view.selected_blobs[0]
            if view.refine_original_blob is None or view.refine_original_blob.id != selected.id:
                view.refine_grow = 0
                view.refine_original_mask = None

        logfile.info("[OP-REFINE-BORDER-ERODE] ERODE-BORDER operation begins..")

        view.refine_grow -= 2
        self.refineBorder()

        logfile.info("[OP-REFINE-BORDER-ERODE] ERODE-BORDER operation ends.")

    def refineBorderOperation(self):

        view = self.activeviewer
        if view is None:
            return

        if len(view.selected_blobs) == 1:
            selected = view.selected_blobs[0]
            if view.refine_original_blob is None or view.refine_original_blob.id != selected.id:
                view.refine_grow = 0
                view.refine_original_mask = None

        logfile.info("[OP-REFINE-BORDER] REFINE-BORDER operation begins..")

        view.refine_grow = 0
        self.refineBorder()

        logfile.info("[OP-REFINE-BORDER] REFINE-BORDER operation ends.")

    def refineBorder(self):
        """
        Refine blob border
        """

        view = self.activeviewer
        if view is None:
            return

        # padding mask to allow moving boundary
        padding = 35
        if len(view.selected_blobs) == 1:

            selected = view.selected_blobs[0]

            if view.refine_original_mask is None:
                view.refine_grow = 0
            #blob = selected.copy()
            self.logBlobInfo(selected, "[OP-REFINE-BORDER][BLOB-SELECTED]")

            if view.refine_grow == 0:
                mask = selected.getMask()
                mask = np.pad(mask, (padding, padding), mode='constant', constant_values=(0, 0)).astype(np.ubyte)
                view.refine_original_blob = selected
                view.refine_original_mask = mask.copy()
                view.refine_original_bbox = selected.bbox.copy()
                bbox = selected.bbox.copy()
            else:
                mask = view.refine_original_mask.copy()
                bbox = view.refine_original_bbox.copy()

            bbox[0] -= padding    # top
            bbox[1] -= padding    # left
            bbox[2] += 2*padding  # width
            bbox[3] += 2*padding  # height

            img = utils.cropQImage(view.img_map, bbox)
            img = utils.qimageToNumpyArray(img)

            # USE DEPTH INFORMATION IF AVAILABLE
            # if view.depth_map is not None:
            #     depth = view.depth_map[bbox[0] : bbox[0]+bbox[3], bbox[1] : bbox[1] + bbox[2]]
            #     imgg = utils.floatmapToQImage((depth - 4)*255)
            #     imgg.save("test.png")
            #
            #     utils.cropQImage(self.depth_map, bbox)
            #     depth = utils.qimageToNumpyArray(depth)
            # else:
            #     depth = None

            depth = None

            #try:
            #    from coraline.Coraline import segment
            #    segment(utils.qimageToNumpyArray(img), mask, 0.0, conservative=0.07, grow=self.refine_grow, radius=30)

            #except Exception as e:
            #    msgBox = QMessageBox()
            #    msgBox.setText(str(e))
            #    msgBox.exec()
            #    return

            if view.tools.tool != 'EDITBORDER':
                view.tools.edit_points.last_editborder_points = None

            try:
                if view.tools.edit_points.last_blob != selected:
                    view.tools.edit_points.last_editborder_points = None
                created_blobs = view.annotations.refineBorder(bbox, selected, img, depth, mask, view.refine_grow, view.tools.edit_points.last_editborder_points)

                if len(created_blobs) == 0:
                    pass
                if len(created_blobs) == 1:
                    view.updateBlob(selected, created_blobs[0])
                    self.logBlobInfo(created_blobs[0], "[OP-REFINE-BORDER][BLOB-CREATED]")
                    self.logBlobInfo(created_blobs[0], "[OP-REFINE-BORDER][BLOB-REFINED]")
                else:
                    view.removeBlob(selected)
                    for blob in created_blobs:
                        view.addBlob(blob, selected=True)
                        #NOTE: they are not CREATED! they are refined! Leaving it here because some logging software might depend on it.
                        self.logBlobInfo(blob, "[OP-REFINE-BORDER][BLOB-CREATED]")
                        self.logBlobInfo(blob, "[OP-REFINE-BORDER][BLOB-REFINED]")

                view.saveUndo()

            except Exception as e:
                print("FAILED!", e)
                pass

        else:
            self.infoWidget.setInfoMessage("You need to select <em>one</em> blob for REFINE operation.")


    def fillLabel(self):

        view = self.activeviewer
        if view is None:
            return

        logfile.info("[OP-FILL] FILL operation starts..")

        if len(view.selected_blobs) == 0:
            return
        count = 0
        for blob in view.selected_blobs:
            if len(blob.inner_contours) == 0:
                continue
            count += 1
            filled = blob.copy()

            self.logBlobInfo(filled, "[OP-FILL][BLOB-SELECTED]")

            filled.inner_contours.clear()
            filled.createFromClosedCurve([filled.contour])
            view.updateBlob(blob, filled, True)

            self.logBlobInfo(filled, "[OP-FILL][BLOB-EDITED]")

        if count:
            view.saveUndo()

        logfile.info("[OP-FILL] FILL operation ends.")




    def logBlobInfo(self, blob, tag):

        message1 = tag + " BLOBID=" + str(blob.id) + " VERSION=" + str(blob.version) + " CLASS=" + blob.class_name
        message2 = tag + " top={:.1f} left={:.1f} width={:.1f} height={:.1f}".format(blob.bbox[0], blob.bbox[1], blob.bbox[2], blob.bbox[3])
        message3 = tag + " cx={:.1f} cy={:.1f}".format(blob.centroid[0], blob.centroid[1])
        message4 = tag + " A={:.1f} P={:.1f} ".format(blob.area, blob.perimeter)

        logfile.info(message1)
        logfile.info(message2)
        logfile.info(message3)
        logfile.info(message4)




#REFACTOR call create a new project and treplace the old one.

    @pyqtSlot()
    def newProject(self):

        self.resetAll()
        self.setTool("MOVE")
        self.updateToolStatus();
        self.setProjectTitle("NONE")
        self.infoWidget.setInfoMessage("TagLab has been reset. To continue open an existing project or load a map.")
        logfile.info("[PROJECT] A new project has been setup.")
        self.groupbox_blobpanel.custom_data = self.project.custom_data

        

    @pyqtSlot()
    def editProject(self):
        if self.editProjectWidget is None:

            self.editProjectWidget = QtProjectWidget(self.project, parent=self)
            self.editProjectWidget.setWindowModality(Qt.WindowModal)
            self.editProjectWidget.show()

        else:
            # show it again
            self.editProjectWidget.project = self.project
            self.editProjectWidget.populateMapList()
            if self.editProjectWidget.isHidden():
                self.editProjectWidget.show()

 # REFACTOR load project properties
    @pyqtSlot()
    def setMapToLoad(self):

        if self.mapWidget is None:

            self.mapWidget = QtMapSettingsWidget(parent=self)
            self.mapWidget.setWindowModality(Qt.WindowModal)
            self.mapWidget.accepted.connect(self.setMapProperties)
            self.mapWidget.show()

        else:

            # show it again
            self.mapWidget.enableRGBloading()
            self.mapWidget.accepted.disconnect()
            self.mapWidget.accepted.connect(self.setMapProperties)
            if self.mapWidget.isHidden():
                self.mapWidget.show()

    @pyqtSlot()
    def createDictionary(self):

        self.create_dictionary = QtDictionaryWidget(self.taglab_dir, self.project, parent = self)
        self.create_dictionary.btn_set.clicked.connect(self.setDictionary)
        self.create_dictionary.show()

    @pyqtSlot()
    def editCustomData(self):

        self.edit_customData = QtCustomDataWidget(self.taglab_dir, self.project, parent = self)
        self.edit_customData.show()



    @pyqtSlot()
    def setDictionary(self):

        # NOTES:
        #
        #  - same keys in use may have different colors -> recoloring of the annotations is needed
        #  - at the moment, two different labels can have the same color

        labels_list = self.create_dictionary.labels

        if len(set(labels_list)) < len(labels_list):
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("There are duplicated class names !! Please, remove the duplicates.")
            msgBox.exec()
            return

        # set the dictionary in the project
        self.project.setDictionaryFromListOfLabels(labels_list)

        # update labels widget
        self.updateLabelsPanel()

        # redraw all blobs
        if self.viewerplus is not None:
            if self.viewerplus.image is not None:
                self.viewerplus.redrawAllBlobs()

        if self.viewerplus2 is not None:
            if self.viewerplus2.image is not None:
                self.viewerplus2.redrawAllBlobs()

    def updateLabelsPanel(self):
        """
        Update labels widget re-creating it to ensure correct size inside the scroll area
        """

        self.labels_widget = QtLabelsWidget()
        self.labels_widget.setLabels(self.project)
        self.scroll_area_labels_panel.setWidget(self.labels_widget)


#REFACTOR
    @pyqtSlot()
    def setMapProperties(self):

        dir = QDir(self.taglab_dir)

        try:

            image = Image(
                            map_px_to_mm_factor = self.mapWidget.data["px_to_mm"],
                            id = self.mapWidget.data['name'],
                            name = self.mapWidget.data['name'],
                            acquisition_date=self.mapWidget.data['acquisition_date']
                          )

            # set RGB map
            rgb_filename = dir.relativeFilePath(self.mapWidget.data['rgb_filename'])
            depth_filename = dir.relativeFilePath(self.mapWidget.data['depth_filename'])

            image.addChannel(rgb_filename, "RGB")

            if len(depth_filename) > 3:
                image.addChannel(depth_filename, "DEM")

        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Error creating map:" + str(e))
            msgBox.exec()
            return

        # add an image and its annotation to the project
        self.project.addNewImage(image)
        self.updateToolStatus()
        self.updateImageSelectionMenu()
        self.updateEditSubMenu()
        self.mapWidget.close()
        self.showImage(image)

    @pyqtSlot()
    def updateToolStatus(self):

        for button in [self.btnMove, self.btnAssign, self.btnEditBorder, self.btnCut, self.btnFreehand,
            self.btnCreateCrack, self.btnWatershed, self.btnBricksSegmentation, self.btnRuler, self.btnDeepExtreme,
            self.btnRitm, self.btnAutoClassification, self.btnCreateGrid, self.btnGrid]:
            button.setEnabled(len(self.project.images) > 0)
        
        for button in [self.btnSplitScreen, self.btnAutoMatch, self.btnMatch]:
            button.setEnabled(len(self.project.images) > 1)

        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                self.activeviewer.showScalebar()
            else:
                self.activeviewer.hideScalebar()

    @pyqtSlot(float)
    def updateMapScale(self, value):
        # this should only operate on the active image
        self.activeviewer.image.map_px_to_mm_factor = round(value, 3)
        self.activeviewer.px_to_mm = round(value, 3)
    @pyqtSlot()
    def updateMapProperties(self):

        dir = QDir(self.taglab_dir)

        flag_pixel_size_changed = False

        try:
            image = self.image2update

            if image.map_px_to_mm_factor != self.mapWidget.data["px_to_mm"]:
                image.map_px_to_mm_factor = self.mapWidget.data["px_to_mm"]
                flag_pixel_size_changed = True


            image.name = self.mapWidget.data['name']
            image.id = self.mapWidget.data['name']
            image.acquisition_date = self.mapWidget.data['acquisition_date']
            rgb_filename = dir.relativeFilePath(self.mapWidget.data['rgb_filename'])
            depth_filename = dir.relativeFilePath(self.mapWidget.data['depth_filename'])


            if len(rgb_filename) <= 3:
                raise ValueError("You need to specify an RGB map")
            else:
                image.updateChannel(rgb_filename, "RGB")

            if len(depth_filename) > 3:
                image.updateChannel(depth_filename, "DEM")

        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Error creating map:" + str(e))
            msgBox.exec()
            return

        # update the image order in case the acquisition date has been changed
        self.project.orderImagesByAcquisitionDate()

        # check if the updated image is shown in the left viewer
        if self.viewerplus.image == image:
            type = self.viewerplus.channel.type
            channel = image.getChannel(type) or image.getChannel("RGB")
            self.viewerplus.setChannel(channel)
            self.viewerplus.updateImageProperties()
            self.viewerplus.viewChanged()

        # check if the updated image is shown in the right viewer
        if self.viewerplus2.image == image:
            type = self.viewerplus2.channel.type
            channel = image.getChannel(type) or image.getChannel("RGB")
            self.viewerplus2.setChannel(channel)
            self.viewerplus2.updateImageProperties()
            self.viewerplus2.viewChanged()

        if flag_pixel_size_changed:
            area_mode = self.compare_panel.getAreaMode()
            if area_mode == "surface area":
                self.project.updatePixelSizeInCorrespondences(image, True)
            else:
                self.project.updatePixelSizeInCorrespondences(image, False)

            self.compare_panel.updateData()

        # update the comboboxes to select the images
        self.updateImageSelectionMenu()

        # update the edit map info submenu
        self.updateEditSubMenu()

        self.mapWidget.close()

#    def resizeEvent(self, event):
#        pass
        #w = self.groupbox_labels.width()
        #self.mapviewer.setNewWidth(w)

    def showImage(self, image):

        """
        Show the image into the main view and update the map viewer accordingly.
        """
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.infoWidget.setInfoMessage("Map is loading..")
            self.viewerplus.setProject(self.project)
            self.viewerplus.clear()
            self.viewerplus.setImage(image)
            self.last_image_loaded = image

            index = self.project.images.index(image)
            self.updateComboboxSourceImage(index)

            w = self.mapviewer.width()
            thumb = self.viewerplus.pixmap.scaled(w, w, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.mapviewer.setPixmap(thumb)
            self.mapviewer.setOpacity(0.5)

            self.disableSplitScreen()

            self.infoWidget.setInfoMessage("The map has been successfully loading.")

            QApplication.restoreOverrideCursor()

        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Error loading map:" + str(e))
            msgBox.exec()


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

    # REFACTOR use project methods
    @pyqtSlot()
    def saveProject(self):
        if self.project.filename is None:
            self.saveAsProject()
        else:
            self.save()

    # REFACTOR use project methods
    @pyqtSlot()
    def saveAsProject(self):

        filters = "ANNOTATION PROJECT (*.json)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save project", self.taglab_dir, filters)

        if filename:
            dir = QDir(self.taglab_dir)
            self.project.filename = dir.relativeFilePath(filename)
            self.setProjectTitle(self.project.filename)
            self.save()


    @pyqtSlot()
    def importAnnotations(self):
        """
        Opens a previously saved project and append the annotated images to the current ones.
        """

        filters = "ANNOTATION PROJECT (*.json)"
        filename, _ = QFileDialog.getOpenFileName(self, "Open a project", self.taglab_dir, filters)
        if filename:
            self.disableSplitScreen()
            self.append(filename)

        self.updateImageSelectionMenu()
        self.updateEditSubMenu()
        self.showImage(self.project.images[-1])


    @pyqtSlot()
    def help(self):

        help_widget = QtHelpWidget(self)
        help_widget.setWindowOpacity(0.9)
        help_widget.setWindowModality(Qt.WindowModal)
        help_widget.show()

    def setupProgressBar(self):

        self.progress_bar = QtProgressBarCustom(parent=self)
        self.progress_bar.setWindowFlags(Qt.ToolTip | Qt.CustomizeWindowHint)
        self.progress_bar.setWindowModality(Qt.NonModal)
        pos = self.viewerplus.pos()
        self.progress_bar.move(pos.x() + 15, pos.y() + 30)
        self.progress_bar.show()

    def deleteProgressBar(self):

        if self.progress_bar:
            self.progress_bar.close()
            del self.progress_bar
            self.progress_bar = None

    def deleteNewDatasetWidget(self):

        if self.newDatasetWidget:
            self.newDatasetWidget.close()
            del self.newDatasetWidget
            self.newDatasetWidget = None

    def deleteTrainYourNetworkWidget(self):

        if self.trainYourNetworkWidget:
            self.trainYourNetworkWidget.close()
            del self.trainYourNetworkWidget
            self.trainYourNetworkWidget = None

    @pyqtSlot()
    def about(self):

        icon = QLabel()

        # BIG taglab icon
        pxmap = QPixmap(os.path.join("icons", "taglab240px.png"))
        pxmap = pxmap.scaledToWidth(160)
        icon.setPixmap(pxmap)
        icon.setStyleSheet("QLabel {padding: 5px; }");



        content = QLabel()
        content.setTextFormat(Qt.RichText)

        txt = "<b>{:s}</b> <p><a href='http://taglab.isti.cnr.it' style='color: white; font-weight: bold; text-decoration: none'>" \
              "TagLab</a> was created to support the activity of annotation and extraction of statistical data "\
              "from ortho-images of benthic communities. TagLab is an ongoing project of the " \
              "<a href='http://vcg.isti.cnr.it' style='color: white; font-weight: bold; text-decoration: none'>" \
              "Visual Computing Lab</a>.</p>".format(self.TAGLAB_VERSION)

        content.setWordWrap(True)
        content.setMinimumWidth(500)
        content.setText(txt)
        content.setTextInteractionFlags(Qt.TextBrowserInteraction)
        content.setStyleSheet("QLabel {padding: 10px; }");
        content.setOpenExternalLinks(True)

        layout = QHBoxLayout()
        layout.addWidget(icon)
        layout.addWidget(content)

        widget = QWidget(self)
        widget.setAutoFillBackground(True)
        widget.setStyleSheet("background-color: rgba(40,40,40,100); color: white")
        widget.setLayout(layout)
        widget.setWindowTitle("About")
        widget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        widget.show()


    @pyqtSlot()
    def importLabelMap(self):
        """
        Import a label map
        """
        if self.last_image_loaded is None:
            box = QMessageBox()
            box.setText("A map is needed to import labels. Load a map or a project.")
            box.exec()
            return

        filters = "Image (*.png *.jpg)"
        filename, _ = QFileDialog.getOpenFileName(self, "Input Label Map File", "", filters)
        if not filename:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        # -1, -1 means that the label map imported must not be rescaled
        created_blobs = self.activeviewer.annotations.import_label_map(filename, self.project.labels, self.activeviewer.img_map.width(),
                                                                       self.activeviewer.img_map.height())
        for blob in created_blobs:
            self.activeviewer.addBlob(blob, selected=False)
        self.activeviewer.saveUndo()

        QApplication.restoreOverrideCursor()

    @pyqtSlot()
    def importShapefile(self):
        """
        Import a ortho
        """
        if self.activeviewer is None:
            box = QMessageBox()
            box.setText("Load a georeferenced orthoimage.")
            box.exec()
            return

        if self.activeviewer.image is not None:
            if self.activeviewer.image.georef_filename == "":
                box = QMessageBox()
                box.setText("Georeferencing is not available; please load a georeferenced ortho image.")
                box.exec()
                return
        else:
            box = QMessageBox()
            box.setText("Load a georeferenced orthoimage.")
            box.exec()
            return

        filters = "Shapefile (*.shp)"
        filename, _ = QFileDialog.getOpenFileName(self, "Import Shapefile", "", filters)
        if not filename:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        gf = self.activeviewer.image.georef_filename
        blobList, data = rasterops.open_shapefile(filename, gf)

        for blob in blobList:
            self.activeviewer.addBlob(blob, selected=False)
        self.activeviewer.saveUndo()

        QApplication.restoreOverrideCursor()

        if  data.empty:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle('TagLab')
            msgBox.setText("This shapefile has no attributes")
            msgBox.exec()
        else:
            self.attribute_widget = QtAttributeWidget(data)
            self.attribute_widget.show()


    @pyqtSlot()
    def exportAnnAsDataTable(self):

        if self.activeviewer.image is None:
            box = QMessageBox()
            box.setText("A map is needed to export labels. Load a map or a project.")
            box.exec()
            return

        filters = "CSV (*.csv) ;; All Files (*)"
        filename, _ = QFileDialog.getSaveFileName(self, "Output file", self.activeviewer.image.name + ".csv", filters)

        if filename:

            self.activeviewer.annotations.export_data_table_for_Scripps(self.activeviewer.image.pixelSize(), filename)

            msgBox = QMessageBox(self)
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Data table exported successfully!")
            msgBox.exec()
            return

    @pyqtSlot()
    def exportAnnAsMap(self):

        if self.activeviewer:
            if not self.activeviewer.image:
                box = QMessageBox()
                box.setText("A map is needed to export labels. Load a map or a project.")
                box.exec()
                return

            filters = "PNG (*.png) ;; All Files (*)"
            filename, _ = QFileDialog.getSaveFileName(self, "Output file", "", filters)

            if filename:
                if not filename.endswith('.png'):
                    filename += '.png'

                size = QSize(self.activeviewer.image.width, self.activeviewer.image.height)
                self.activeviewer.annotations.export_image_data_for_Scripps(size, filename, self.project.labels)

                msgBox = QMessageBox(self)
                msgBox.setWindowTitle(self.TAGLAB_VERSION)
                msgBox.setText("Map exported successfully!")
                msgBox.exec()
                return


    @pyqtSlot()
    def exportHistogramFromAnn(self):

        if self.activeviewer is not None:

            histo_widget = QtHistogramWidget(self.activeviewer.annotations, self.project.labels,
                                             self.activeviewer.image.pixelSize(),
                                             self.activeviewer.image.acquisition_date, self)
            histo_widget.setWindowModality(Qt.WindowModal)
            histo_widget.show()

    @pyqtSlot()
    def exportAnnAsShapefiles(self):

        if self.activeviewer is None:
            return

        if self.activeviewer.image is not None:
            if self.activeviewer.image.georef_filename == "":
                box = QMessageBox()
                box.setText("Georeference information are not available.")
                box.exec()
                return

        filters = "SHP (*.shp)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Save Shapefile as", self.taglab_dir, filters)

        if output_filename:
            blobs = self.activeviewer.annotations.seg_blobs
            gf = self.activeviewer.image.georef_filename
            rasterops.write_shapefile(self.project, blobs, gf, output_filename)

    @pyqtSlot()
    def exportGeoRefLabelMap(self):

        if self.activeviewer is None:
            return

        if self.activeviewer.image is None:
            box = QMessageBox()
            box.setText("A map is needed to import labels. Load a map or a project.")
            box.exec()
            return

        if self.activeviewer.image.georef_filename == "":
            box = QMessageBox()
            box.setText("Georeference information are not available.")
            box.exec()
            return

        filters = "Tiff (*.tif) ;; All Files (*)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Output GeoTiff", "", filters)

        if output_filename:
            size = QSize(self.activeviewer.image.width, self.activeviewer.image.height)
            label_map_img = self.activeviewer.annotations.create_label_map(size, self.project.labels)
            label_map_np = utils.qimageToNumpyArray(label_map_img)
            georef_filename = self.activeviewer.image.georef_filename
            outfilename = os.path.splitext(output_filename)[0]
            rasterops.saveGeorefLabelMap(label_map_np, georef_filename, outfilename)

            msgBox = QMessageBox(self)
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Map exported successfully!")
            msgBox.exec()
            return


    @pyqtSlot()
    def exportAnnAsTrainingDataset(self):

        if self.activeviewer is not None:
            if self.newDatasetWidget is None:

                if not self.activeviewer.image.working_area :
                    self.activeviewer.image.working_area = [0, 0 , self.activeviewer.img_map.width(), self.activeviewer.img_map.height()]

                annotations = self.activeviewer.annotations
                self.newDatasetWidget = QtNewDatasetWidget(self.activeviewer.image.working_area, parent=self)
                self.newDatasetWidget.setWindowModality(Qt.NonModal)
                self.newDatasetWidget.btnChooseWorkingArea.clicked.connect(self.enableWorkingArea)
                self.newDatasetWidget.btnExport.clicked.connect(self.exportNewDataset)
                self.newDatasetWidget.btnCancel.clicked.connect(self.disableWorkingArea)
                self.newDatasetWidget.closed.connect(self.disableWorkingArea)
                self.activeviewer.tools.tools["WORKINGAREA"].rectChanged.connect(self.updateWorkingArea)

            self.showWorkingArea()
            self.newDatasetWidget.show()

    def showWorkingArea(self):
        """
        Show the working area of the current image.
        """
        working_area = self.activeviewer.image.working_area

        if working_area is not None:
            workingAreaStyle = QPen(Qt.magenta, 5, Qt.DashLine)
            workingAreaStyle.setCosmetic(True)

            x = working_area[1]
            y = working_area[0]
            w = working_area[2]
            h = working_area[3]

            if self.working_area_rect is None:
                self.working_area_rect = self.activeviewer.scene.addRect(x, y, w, h, workingAreaStyle)
                self.working_area_rect.setZValue(5)
            else:
                self.working_area_rect.setVisible(True)
                self.working_area_rect.setRect(x, y, w, h)

    def hideWorkingArea(self):
        self.working_area_rect.setVisible(False)

    @pyqtSlot(int, int, int, int)
    def updateWorkingArea(self, x, y, width, height):
        txt = self.newDatasetWidget.formatWorkingArea(y, x, width, height)
        self.newDatasetWidget.editWorkingArea.setText(txt)
        self.activeviewer.image.working_area = [y, x, width, height]
        self.showWorkingArea()

    @pyqtSlot()
    def enableWorkingArea(self):
        self.activeviewer.setTool("WORKINGAREA")

    @pyqtSlot()
    def disableWorkingArea(self):
        self.activeviewer.setTool("MOVE")
        self.hideWorkingArea()

    @pyqtSlot()
    def exportNewDataset(self):

        if self.activeviewer is not None and self.newDatasetWidget is not None:

            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.setupProgressBar()

            self.progress_bar.hidePerc()
            self.progress_bar.setMessage("Export new dataset (setup)..")
            QApplication.processEvents()

            new_dataset = NewDataset(self.activeviewer.img_map, self.activeviewer.annotations.seg_blobs, tile_size=1026, step=513)

            target_classes = training.createTargetClasses(self.activeviewer.annotations)
            target_classes = list(target_classes.keys())

            new_dataset.createLabelImage(self.project.labels)
            new_dataset.convert_colors_to_labels(target_classes, self.project.labels)
            new_dataset.computeFrequencies(target_classes)
            target_scale_factor = self.newDatasetWidget.getTargetScale()
            new_dataset.workingAreaCropAndRescale(self.activeviewer.image.pixelSize(), target_scale_factor,self.activeviewer.image.working_area)

            # create training, validation and test areas

            self.progress_bar.setMessage("Export new dataset (create train/val/test areas)..")
            self.progress_bar.setProgress(25.0)
            QApplication.processEvents()

            mode = self.newDatasetWidget.getSplitMode()
            new_dataset.setupAreas(mode.upper(), target_classes)

            # cut the tiles
            flag_oversampling = self.newDatasetWidget.checkOversampling.isChecked()

            self.progress_bar.setMessage("Export new dataset (cut tiles)..")
            self.progress_bar.setProgress(50.0)
            QApplication.processEvents()

            if flag_oversampling is True:
                class_to_sample, radii = new_dataset.computeRadii()
                new_dataset.cut_tiles(regular=False, oversampling=True, classes_to_sample=class_to_sample, radii=radii)
            else:
                new_dataset.cut_tiles(regular=True, oversampling=False, classes_to_sample=None, radii=None)

            flag_save = self.newDatasetWidget.checkTiles.isChecked()
            if flag_save:
                new_dataset.save_samples("tiles_cutted.png", show_tiles=True, show_areas=True, radii=None)

            # export the tiles
            self.progress_bar.setMessage("Export new dataset (export tiles)..")
            self.progress_bar.setProgress(75.0)
            QApplication.processEvents()

            basename = self.newDatasetWidget.getDatasetFolder()
            tilename = os.path.splitext(self.activeviewer.image.name)[0]
            new_dataset.export_tiles(basename=basename, tilename=tilename, labels_info=self.project.labels)

            # save the target scale factor
            target_scale_factor_file = os.path.join(basename, "target-scale-factor.txt")
            fl = open(target_scale_factor_file, "w")
            fl.write(str(target_scale_factor))
            fl.close()

            self.deleteProgressBar()
            self.deleteNewDatasetWidget()

            self.disableWorkingArea()
            QApplication.restoreOverrideCursor()

    @pyqtSlot()
    def trainNewNetwork(self):

        dataset_folder = self.trainYourNetworkWidget.getDatasetFolder()

        # check dataset
        check = training.checkDataset(dataset_folder)
        if check == 1:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("An error occured with your dataset, there is a mismatch between files. Please, export a new dataset.")
            msgBox.exec()
            return

        self.setupProgressBar()
        self.progress_bar.hidePerc()
        self.progress_bar.setMessage("Dataset setup..")
        QApplication.processEvents()

        # CLASSES TO RECOGNIZE (label name - label code)
        labels_folder = os.path.join(dataset_folder, "training")
        labels_folder = os.path.join(labels_folder, "labels")
        target_classes = CoralsDataset.importClassesFromDataset(labels_folder, self.project.labels)
        num_classes = len(target_classes)

        # GO TRAINING GO...
        nepochs = self.trainYourNetworkWidget.getEpochs()
        lr = self.trainYourNetworkWidget.getLR()
        L2 = self.trainYourNetworkWidget.getWeightDecay()
        batch_size = self.trainYourNetworkWidget.getBatchSize()

        classifier_name = self.trainYourNetworkWidget.editClassifierName.text()
        network_name = self.trainYourNetworkWidget.editNetworkName.text() + ".net"
        network_filename = os.path.join(os.path.join(self.taglab_dir, "models"), network_name)

        # training folders
        train_folder = os.path.join(dataset_folder, "training")
        images_dir_train = os.path.join(train_folder, "images")
        labels_dir_train = os.path.join(train_folder, "labels")

        val_folder = os.path.join(dataset_folder, "validation")
        images_dir_val = os.path.join(val_folder, "images")
        labels_dir_val = os.path.join(val_folder, "labels")

        dataset_train_info, train_loss_values, val_loss_values = training.trainingNetwork(images_dir_train, labels_dir_train,
                        images_dir_val, labels_dir_val,
                        self.project.labels, target_classes, num_classes,
                        save_network_as=network_filename, classifier_name=classifier_name,
                        epochs=nepochs, batch_sz=batch_size, batch_mult=4, validation_frequency=2,
                        loss_to_use="FOCAL_TVERSKY", epochs_switch=0, epochs_transition=0,
                        learning_rate=lr, L2_penalty=L2, tversky_alpha=0.6, tversky_gamma=0.75,
                        optimiz="ADAM", flag_shuffle=True, flag_training_accuracy=False,
                        progress=self.progress_bar)

        ##### TEST

        test_folder = os.path.join(dataset_folder, "test")
        images_dir_test = os.path.join(test_folder, "images")
        labels_dir_test = os.path.join(test_folder, "labels")

        output_folder = os.path.join(dataset_folder, "predictions")
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder, ignore_errors=True)

        os.mkdir(output_folder)

        self.progress_bar.hidePerc()
        self.progress_bar.setMessage("Test network..")
        QApplication.processEvents()

        metrics = training.testNetwork(images_dir_test, labels_dir_test, dictionary=self.project.labels,
                                       target_classes=target_classes, dataset_train=dataset_train_info,
                                       network_filename=network_filename, output_folder=output_folder)

        #info about the classifier created
        self.classifier_name = classifier_name
        self.dataset_train_info = dataset_train_info

        self.deleteProgressBar()
        self.deleteTrainYourNetworkWidget()

        self.trainResultsWidget = QtTrainingResultsWidget(metrics, train_loss_values, val_loss_values, images_dir_test, labels_dir_test, output_folder)
        self.trainResultsWidget.btnConfirm.clicked.connect(self.confirmTraining)
        self.trainResultsWidget.setAttribute(Qt.WA_DeleteOnClose)
        self.trainResultsWidget.setWindowModality(Qt.WindowModal)
        self.trainResultsWidget.show()

    @pyqtSlot()
    def confirmTraining(self):
        """
        It saves the classifier created with the Train-Your-Network feature.
        """

        new_classifier = dict()
        new_classifier["Classifier Name"] = self.classifier_name
        new_classifier["Average Norm."] = list(self.dataset_train_info.dataset_average)
        new_classifier["Num. Classes"] = self.dataset_train_info.num_classes
        new_classifier["Classes"] = list(self.dataset_train_info.dict_target)

        # read the target scale factor
        target_scale_factor_file = os.path.join(self.trainResultsWidget.dataset_folder, "target-scale-factor.txt")
        fl = open(target_scale_factor_file, "r")
        line = fl.readline()
        fl.close()
        target_scale_factor = float(line)

        new_classifier["Scale"] = target_scale_factor
        self.available_classifiers.append(new_classifier)
        newconfig = dict()
        newconfig["Available Classifiers"] = self.available_classifiers
        newconfig["Labels"] = self.project.labels
        str = json.dumps(newconfig)
        newconfig_filename = os.path.join(self.taglab_dir, "newconfig.json")
        f = open(newconfig_filename, "w")
        f.write(str)
        f.close()

        self.trainResultsWidget.close()
        self.trainResultsWidget = None


    @pyqtSlot()
    def trainYourNetwork(self):

        if self.trainYourNetworkWidget is None:
            self.trainYourNetworkWidget = QtTYNWidget(annotations=None, parent=self)
            self.trainYourNetworkWidget.setWindowModality(Qt.WindowModal)
            self.trainYourNetworkWidget.btnTrain.clicked.connect(self.trainNewNetwork)
        self.trainYourNetworkWidget.show()

    @pyqtSlot()
    def exportClippedRaster(self):

        if self.activeviewer is None:
            return

        # the depth is clipped - get the file name of the GeoTiff which stores it
        input_tiff = ""
        if self.activeviewer.image is not None:
            for channel in self.activeviewer.image.channels:
                if channel.type == "DEM":
                    input_tiff = channel.filename

        if input_tiff == "":
            box = QMessageBox()
            box.setText("DEM not found! You need to load a DEM to export a clipped version of it.")
            box.exec()
            return

        filters = " TIFF (*.tif)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Save raster as", self.taglab_dir, filters)

        if output_filename:
            blobs = self.activeviewer.annotations.seg_blobs
            gf = self.activeviewer.image.georef_filename
            rasterops.saveClippedTiff(input_tiff, blobs, gf, output_filename)

    @pyqtSlot()
    def calculateAreaUsingSlope(self):

        if self.activeviewer is None:
            return

        # get the file name of the Tiff which stores the depth
        input_tiff = ""
        if self.activeviewer.image is not None:
            for channel in self.activeviewer.image.channels:
                if channel.type == "DEM":
                    input_tiff = channel.filename

        if input_tiff == "":
            box = QMessageBox()
            box.setText("DEM not found! You need a DEM to compute the surface area.")
            box.exec()
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        georef_filename = self.activeviewer.image.georef_filename
        blobs = self.activeviewer.annotations.seg_blobs
        rasterops.calculateAreaUsingSlope(input_tiff, blobs)

        QApplication.restoreOverrideCursor()

        current_area_mode = self.compare_panel.comboboxAreaMode.currentText()
        self.updateAreaMode(current_area_mode.lower())

    def load(self, filename):
        """
        Load a previously saved projects.
        """

        self.resetAll()

        QApplication.setOverrideCursor(Qt.WaitCursor)

#        try:
        self.project = loadProject(self.taglab_dir, filename, self.default_dictionary)
#        except Exception as e:
#            msgBox = QMessageBox()
#            msgBox.setText("The json project contains an error:\n {0}\n\nPlease contact us.".format(str(e)))
#            msgBox.exec()
#            return

        QApplication.restoreOverrideCursor()

        self.setProjectTitle(self.project.filename)

        # show the first map present in project
        if len(self.project.images) > 0:
            self.showImage(self.project.images[0])

        self.groupbox_blobpanel.custom_data = self.project.custom_data
        self.groupbox_blobpanel.clear()
        self.updateLabelsPanel()

        self.updateImageSelectionMenu()
        self.updateEditSubMenu()

        if self.timer is None:
            self.activateAutosave()

        self.infoWidget.setInfoMessage("The project: " + self.project.filename + " has been successfully open.")

        message = "[PROJECT] The project " + self.project.filename + " has been loaded."
        logfile.info(message)
        self.updateToolStatus()


    def append(self, filename):
        """
        Append the annotated images of a previously saved project to the current one.
        """

        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            project_to_append = loadProject(self.taglab_dir, filename, self.labels_dictionary)
        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setText("The json project contains an error:\n {0}\n\nPlease contact us.".format(str(e)))
            msgBox.exec()
            return

        # append the annotated images to the current ones
        for annotated_image in project_to_append.images:
            self.project.addNewImage(annotated_image)

        QApplication.restoreOverrideCursor()

        self.infoWidget.setInfoMessage("The annotations of the given project has been successfully loaded.")

    # REFACTOR move to a project method
    def save(self):
        """
        Save the current project.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.project.save()
        QApplication.restoreOverrideCursor()

        if self.timer is None:
            self.activateAutosave()

        self.infoWidget.setInfoMessage("Current project has been successfully saved.")

        message = "[PROJECT] The project " + self.project.filename + " has been saved."
        logfile.info(message)


    #REFACTOR networks should be moved to a new class
    def resetNetworks(self):

        torch.cuda.empty_cache()

        if self.deepextreme_net is not None:
            del self.deepextreme_net
            self.deepextreme_net = None

        if self.classifier is not None:
            del self.classifier
            self.classifier = None

    @pyqtSlot()
    def selectClassifier(self):
        """
        Select the classifier to use between the available classifiers.
        """

        if self.activeviewer is None:
            self.move()
            return

        if self.activeviewer.image is None:
            self.move()
            return

        if self.available_classifiers == "None":
            self.btnAutoClassification.setChecked(False)
        else:

            if self.classifierWidget is None:
                self.classifierWidget = QtClassifierWidget(self.available_classifiers, parent=self)
                self.classifierWidget.setAttribute(Qt.WA_DeleteOnClose)
                self.classifierWidget.btnApply.clicked.connect(self.applyClassifier)
                self.classifierWidget.setWindowModality(Qt.NonModal)
                self.classifierWidget.show()
                self.classifierWidget.btnChooseArea.clicked.connect(self.enablePrevArea)
                self.classifierWidget.btnCancel.clicked.connect(self.disablePrevArea)
                self.classifierWidget.closed.connect(self.disablePrevArea)
                self.classifierWidget.btnPrev.clicked.connect(self.applyPrev)
                self.classifierWidget.sliderScores.valueChanged.connect(self.showScores)
                self.prev_area = None


        self.showPrevArea()
        self.classifierWidget.show()
        self.classifierWidget.disableSliders()

    @pyqtSlot()
    def cropPrev(self):

        classifier_selected = self.classifierWidget.selected()
        target_scale_factor = classifier_selected['Scale']
        scale_factor = target_scale_factor / self.activeviewer.image.pixelSize()

        prev_area = self.prev_area
        width = max(513 * scale_factor, prev_area[2])
        height = max(513 * scale_factor, prev_area[3])
        crop_image = self.activeviewer.img_map.copy(prev_area[1], prev_area[0], width, height)

        self.classifierWidget.setRGBPreview(crop_image)

        WA_tool = self.activeviewer.tools.tools["WORKINGAREA"]
        if WA_tool.receivers(WA_tool.released) > 0:
            WA_tool.released.disconnect()
        if WA_tool.receivers(WA_tool.rectChanged) > 0:
            WA_tool.rectChanged.disconnect()

        QApplication.setOverrideCursor(Qt.ArrowCursor)

    def applyPrev(self):
        """
        crop selected area and apply preview.
        """

        if self.prev_area is not None:
            classifier_selected = self.classifierWidget.selected()
            target_scale_factor = classifier_selected['Scale']

            # free GPU memory
            self.resetNetworks()
            self.setupProgressBar()

            QApplication.processEvents()

            self.classifier = MapClassifier(classifier_selected, self.project.labels)
            self.classifier.updateProgress.connect(self.progress_bar.setProgress)

            self.progress_bar.hidePerc()
            self.progress_bar.setMessage("Initialization..")

            self.classifier.setup(self.activeviewer.img_map, self.activeviewer.image.pixelSize(), target_scale_factor,
                                  working_area=self.prev_area, padding=256)

            self.progress_bar.showPerc()
            self.progress_bar.setMessage("Classification: ")
            self.progress_bar.setProgress(0.0)
            QApplication.processEvents()

            self.classifier.run(1026, 513, 256, save_scores=True)
            self.classifier.loadScores()
            self.showScores()

            self.deleteProgressBar()

    def showScores(self):

        self.classifierWidget.enableSliders()

        tresh = self.classifierWidget.sliderScores.value()/100.0
        outimg = self.classifier.classify(tresh)
        self.classifierWidget.setLabelPreview(outimg)


    def showPrevArea(self):
        """
       Show the working area of the current image.
        """

        prev_area = self.prev_area

        if prev_area is not None:
            workingAreaStyle = QPen(Qt.white, 2, Qt.DashLine)
            workingAreaStyle.setCosmetic(True)

            x = prev_area[1]
            y = prev_area[0]
            w = prev_area[2]
            h = prev_area[3]

            if self.prev_area_rect is None:
                self.prev_area_rect = self.activeviewer.scene.addRect(x, y, w, h, workingAreaStyle)
                self.prev_area_rect.setZValue(5)
            else:
                self.prev_area_rect.setRect(x, y, w, h)


    @pyqtSlot(int, int, int, int)
    def updatePrevArea(self, x, y, width, height):

        width = min(2048, width)
        height = min(2048, height)
        self.prev_area = [y, x, width, height]
        self.showPrevArea()

    @pyqtSlot()
    def enablePrevArea(self):
        self.activeviewer.setTool("WORKINGAREA")
        self.activeviewer.tools.tools["WORKINGAREA"].released.connect(self.cropPrev)
        self.activeviewer.tools.tools["WORKINGAREA"].rectChanged.connect(self.updatePrevArea)

    @pyqtSlot()
    def disablePrevArea(self):
        self.prev_area = None

        WA_tool = self.activeviewer.tools.tools["WORKINGAREA"]
        if WA_tool.receivers(WA_tool.released) > 0:
            WA_tool.released.disconnect()
        if WA_tool.receivers(WA_tool.rectChanged) > 0:
            WA_tool.rectChanged.disconnect()

        if self.prev_area_rect is not None:
            self.activeviewer.scene.removeItem(self.prev_area_rect)
            self.prev_area_rect = None

        self.setTool("MOVE")
        self.classifierWidget = None


    def resetAutomaticClassification(self):
        """
        Reset the automatic classification.
        """

        # free GPU memory
        self.resetNetworks()

        # delete classifier
        if self.classifier:
            del self.classifier
            self.classifier = None

        # delete progress bar
        self.deleteProgressBar()


    @pyqtSlot()
    def applyClassifier(self):
        """
        Apply the chosen classifier to the active image.
        """

        if self.classifierWidget:

            classifier_selected = self.classifierWidget.selected()

            # free GPU memory
            self.resetNetworks()

            self.classifierWidget.close()
            del self.classifierWidget
            self.classifierWidget = None

            self.setupProgressBar()

            # setup the desired classifier

            self.infoWidget.setInfoMessage("Setup automatic classification..")

            self.progress_bar.hidePerc()
            self.progress_bar.setMessage("Setup automatic classification..")

            QApplication.processEvents()

            message = "[AUTOCLASS] Automatic classification STARTS.. (classifier: )" + classifier_selected['Classifier Name']
            logfile.info(message)

            self.classifier = MapClassifier(classifier_selected, self.project.labels)
            self.classifier.updateProgress.connect(self.progress_bar.setProgress)

            if self.activeviewer is None:
                self.resetAutomaticClassification()
            else:
                # rescaling the map to fit the target scale of the network

                self.progress_bar.setMessage("Map rescaling..")
                QApplication.processEvents()

                orthoimage = self.activeviewer.img_map
                target_scale_factor = classifier_selected['Scale']
                self.classifier.setup(orthoimage, self.activeviewer.image.pixelSize(),
                                      target_scale_factor,
                                      working_area=[], padding=256)

                self.progress_bar.showPerc()
                self.progress_bar.setMessage("Classification: ")
                self.progress_bar.setProgress(0.0)
                QApplication.processEvents()

                # runs the classifier
                self.infoWidget.setInfoMessage("Automatic classification is running..")

                self.classifier.run(1026, 513, 256)

                if self.classifier.flagStopProcessing is False:

                    # import generated label map
                    self.progress_bar.hidePerc()
                    self.progress_bar.setMessage("Finalizing classification results..")
                    QApplication.processEvents()

                    filename = os.path.join("temp", "labelmap.png")

                    created_blobs = self.activeviewer.annotations.import_label_map(filename, self.project.labels,
                                                                                   orthoimage.width(), orthoimage.height())
                    for blob in created_blobs:
                        self.viewerplus.addBlob(blob, selected=False)

                    logfile.info("[AUTOCLASS] Automatic classification ENDS.")

                    self.resetAutomaticClassification()

                    # save and close
                    msgBox = QMessageBox()
                    msgBox.setWindowTitle(self.TAGLAB_VERSION)
                    msgBox.setText(
                    "Automatic classification is finished. TagLab will be close. Please, click ok and save the project.")
                    msgBox.exec()

                    self.saveAsProject()

                    QApplication.quit()

                else:

                    logfile.info("[AUTOCLASS] Automatic classification STOP by the users.")

                    self.resetAutomaticClassification()

                    import gc
                    gc.collect()

                    self.move()


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

    app.setStyleSheet("QMainWindow::separator { width:5px; height:5px; color: red; }" + 
        "QMainWindow::separator:hover { background: #888; }" + 
        "QDockWidget::close-button, QDockWidget::float-button { background:#fff; }")

    # set the application font
    if platform.system() != "Darwin":
        QFD = QFontDatabase()
        font_id1 = QFD.addApplicationFont("fonts/opensans/OpenSans-Regular.ttf")
        if font_id1 == -1:
            print("Failed to load application font..")
            sys.exit(-2)

        font_id2 = QFD.addApplicationFont("fonts/roboto/Roboto-Light.ttf")
        if font_id2 == -1:
            print("Failed to load application font..")
            sys.exit(-2)

        font_id3 = QFD.addApplicationFont("fonts/roboto/Roboto-Regular.ttf")
        if font_id3 == -1:
            print("Failed to load application font..")
            sys.exit(-2)

        font = QFont('Roboto')
        app.setFont(font)

    # Create the inspection tool
    tool = TagLab()
    # create the main window - TagLab widget is the central widget
    mw = MainWindow()
    title = tool.TAGLAB_VERSION
    mw.setWindowTitle(title)
    mw.setCentralWidget(tool)
    mw.setStyleSheet("background-color: rgb(55,55,55); color: white")
    mw.showMaximized()

    # Show the viewer and run the application.
    mw.show()

    sys.exit(app.exec_())
