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
import datetime
import shutil
import json
import numpy as np
import urllib
import platform
import pandas as pd
import importlib

from PyQt5.QtCore import Qt, QSize, QMargins, QDir, QPoint, QPointF, QRectF, QTimer, pyqtSlot, pyqtSignal, QSettings, QFileInfo, QModelIndex
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QIcon, QKeySequence, QPen, QImageReader, QImage
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QFileDialog, QComboBox, QMenuBar, QMenu, QSizePolicy, QScrollArea, \
    QLabel, QToolButton, QPushButton, QSlider, QCheckBox, \
    QMessageBox, QGroupBox, QLayout, QHBoxLayout, QVBoxLayout, QFrame, QDockWidget, QTextEdit, QAction, \
    QDialog

from source.QtExportDXF import QtDXFExportOptions  # Import the options dialog



import pprint
# PYTORCH
from source.QtAlignmentToolWidget import QtAlignmentToolWidget

try:
    import torch
    from torch.nn.functional import upsample
except Exception as e:
    print("Incompatible version between pytorch, cuda and python.\n" +
          "Knowing working version combinations are\n: Cuda 10.0, pytorch 1.0.0, python 3.6.8" + str(e))
   # exit()

# CUSTOM
import csv
import source.Mask as Mask
import source.RasterOps as rasterops
from source.QtImageViewerPlus import QtImageViewerPlus
from source.QtMapViewer import QtMapViewer
from source.QtSettingsWidget import QtSettingsWidget
from source.QtMapSettingsWidget import QtMapSettingsWidget
from source.QtScaleWidget import QtScaleWidget
from source.QtWorkingAreaWidget import QtWorkingAreaWidget
from source.QtCropWidget import QtCropWidget
from source.QtLayersWidget import QtLayersWidget

from source.QtHelpWidget import QtHelpWidget
from source.QtMessages import QtMessageWidget

from source.QtProgressBarCustom import QtProgressBarCustom
from source.QtHistogramWidget import QtHistogramWidget
from source.QtClassifierWidget import QtClassifierWidget
from source.QtNewDatasetWidget import QtNewDatasetWidget
from source.QtSampleWidget import QtSampleWidget
from source.QtTrainingResultsWidget import QtTrainingResultsWidget
from source.QtTYNWidget import QtTYNWidget
from source.QtDatasetManagerWidget import QtDatasetManagerWidget
from source.QtComparePanel import QtComparePanel
from source.QtTablePanel import QtTablePanel
from source.QtExportAnnAsTable import QtExportAnnAsTable
from source.QtTableLabel import QtTableLabel
from source.QtProjectWidget import QtProjectWidget
from source.QtProjectEditor import QtProjectEditor
from source.Project import Project, loadProject
from source.Point import Point
from source.Image import Image
from source.MapClassifier import MapClassifier
from source.NewDataset import NewDataset
from source.QtGridWidget import QtGridWidget
from source.QtDictionaryWidget import QtDictionaryWidget
from source.QtRegionAttributesWidget import QtRegionAttributesWidget
from source.QtShapefileAttributeWidget import QtAttributeWidget
from source.QtGeometricInfoWidget import QtGeometricInfoWidget

from source.QtSelection import QtSelectByPropertiesWidget

# from source.QtDXFfileAttributeWidget import QtDXFExportWidget
import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.entities import Layer
import math

from source.QtPanelInfo import QtPanelInfo
from source.Sampler import Sampler

from source.QtImportViscoreWidget import QtImportViscoreWidget
from source.QtCoralNetToolboxWidget import QtCoralNetToolboxWidget
from source.QtExportCoralNetDataWidget import QtExportCoralNetDataWidget

from source import genutils
from source.Blob import Blob
from source.Shape import Layer, Shape

from source.Tools import Tools

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
            reply = box.question(self, taglab.TAGLAB_VERSION, "Do you want to save changes to " + taglab.project.filename,
                                 QMessageBox.Cancel | QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                taglab.saveProject()

            if reply == QMessageBox.Cancel:
                event.ignore()
                return

        super(MainWindow, self).closeEvent(event)


class TagLab(QMainWindow):
    

    def __init__(self, screen_size, parent=None):
        super(TagLab, self).__init__(parent)

        ##### CUSTOM STYLE #####

        self.setStyleSheet("background-color: rgb(55,55,55); color: white")

        current_version, need_to_update = self.checkNewVersion()
        if need_to_update:
            print("--- THERE IS A NEW VERSION AVAILABLE! ---")
            print("Please, launch update.py")
            print("if updating from the 29/10/2024 version, also launch install.py")
            print("-----------------------------------------")            
            sys.exit(0)

        ##### DATA INITIALIZATION AND SETUP #####

        self.taglab_dir = os.path.dirname(__file__)

        self.TAGLAB_VERSION = "TagLab " + current_version

        print(self.TAGLAB_VERSION)

        # SETTINGS
        self.settings_widget = QtSettingsWidget(self.taglab_dir)

        # LOAD CONFIGURATION FILE

        f = open(os.path.join(self.taglab_dir, "config.json"), "r")
        config_dict = json.load(f)
        self.available_classifiers = config_dict["Available Classifiers"]

        logfile.info("[INFO] Initizialization begins..")

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
        self.projectEditor = None
        self.align_tool_widget = None
        self.edit_project_widget = None
        self.sample_point_widget = None
        self.scale_widget = None
        self.dictionary_widget = None
        self.working_area_widget = None
        self.dataset_train_info = None
        self.region_attributes_widget = None
        self.crop_widget = None
        self.classifierWidget = None
        self.newDatasetWidget = None
        self.help_widget = None
        
        #message widget for help
        self.message_widget = None

        self.trainYourNetworkWidget = None
        self.datasetManagerWidget = None
        self.trainResultsWidget = None
        self.progress_bar = None
        self.gridWidget = None
        self.contextMenuPosition = None

        ##### TOP LAYOUT

        ##### LAYOUT EDITING TOOLS (VERTICAL)

        flatbuttonstyle = """
        QPushButton:checked { background-color: rgb(100,100,100); }
        QPushButton:hover   { border: 1px solid darkgray;         }
        QToolTip { background-color: white; color: rgb(100,100,100); }
        """

        flatbuttonstyle_red = """
        QPushButton:checked { background-color: rgb(100,100,100); }
        QPushButton:hover   { border: 1px solid rgb(255,100,100); }
        QToolTip { background-color: white; color: rgb(100,100,100); }
        """

        self.btnMove               = self.newButton("move.png",     "Pan/Zoom",               flatbuttonstyle, self.move)
        self.btnPoint              = self.newButton("point.png",    "Place annotation point", flatbuttonstyle, self.placeAnnPoint)
        self.btnFreehand           = self.newButton("pencil.png",   "Freehand segmentation",  flatbuttonstyle, self.freehandSegmentation)
        self.btnCreateCrack        = self.newButton("crack.png",    "Create crack",           flatbuttonstyle, self.createCrack)
        self.btnWatershed          = self.newButton("watershed.png",    "Watershed segmentation", flatbuttonstyle, self.watershedSegmentation)
        self.btnBricksSegmentation = self.newButton("brick.png",    "Bricks segmentation",    flatbuttonstyle, self.bricksSegmentation)
        self.btnSamInteractive     = self.newButton("saminteractive2.png", "SAM - positive/negative clicks in an area", flatbuttonstyle, self.saminteractive)
        self.btnSam                = self.newButton("sam.png", "SAM - all instances in an area", flatbuttonstyle, self.sam)
        self.btnFourClicks         = self.newButton("dexter.png",   "4-clicks segmentation",  flatbuttonstyle, self.fourClicks)
        self.btnRitm               = self.newButton("ritm.png",     "Positive/negative clicks segmentation", flatbuttonstyle, self.ritm)
        self.btnRows               = self.newButton("brick.png",     "Rows analysis",      flatbuttonstyle, self.rows)

        self.btnAssign             = self.newButton("bucket.png",   "Assign class to region",   flatbuttonstyle, self.assign)
        self.btnEditBorder         = self.newButton("edit.png",     "Edit region border",       flatbuttonstyle, self.editBorder)
        self.btnCut                = self.newButton("scissors.png", "Cut region",               flatbuttonstyle, self.cut)
        self.btnRuler              = self.newButton("ruler.png",    "Measure tool",           flatbuttonstyle, self.ruler)

        # Split blob operation removed from the toolbar
        # self.btnSplitBlob   = self.newButton("split.png",    "Split Blob",            flatbuttonstyle1, self.splitBlob)

        self.btnAutoClassification = self.newButton("auto.png", "Fully auto semantic segmentation", flatbuttonstyle, self.selectClassifier)
        self.btnCreateGrid         = self.newButton("grid.png", "Create grid",                flatbuttonstyle, self.createGrid)
        self.btnGrid               = self.newButton("grid-edit.png", "Active/disactive grid operations", flatbuttonstyle, self.toggleGrid)
        self.btnSplitScreen        = self.newButton("split.png", "Split screen",              flatbuttonstyle, self.toggleComparison)
        self.btnAutoMatch          = self.newButton("automatch.png", "Compute automatic matches", flatbuttonstyle, self.autoCorrespondences)
        self.btnAutoMatch.setCheckable(False) # WARNING: Automatic matches button is not checkable
        self.btnMatch              = self.newButton("manualmatch.png", "Edit matches ", flatbuttonstyle, self.matchTool)


        # separator
        pxmapSeparator = QPixmap("icons/separator.png")
        labelSeparator1 = QLabel()
        labelSeparator1.setPixmap(pxmapSeparator.scaled(QSize(35, 30)))
        labelSeparator2 = QLabel()
        labelSeparator2.setPixmap(pxmapSeparator.scaled(QSize(35, 30)))
        labelSeparator3 = QLabel()
        labelSeparator3.setPixmap(pxmapSeparator.scaled(QSize(35, 30)))
        labelSeparator4 = QLabel()
        labelSeparator4.setPixmap(pxmapSeparator.scaled(QSize(35, 30)))
        """
        separatorLine = QFrame()
        separatorLine.setFrameShape(QFrame.HLine) 
        separatorLine.setFrameShadow(QFrame.Raised)
        separatorLine.setLineWidth(3)
        """

        #filling the layout
        layout_tools = QVBoxLayout()
        layout_tools.setSpacing(0)
        layout_tools.addWidget(self.btnMove)
        layout_tools.addWidget(self.btnPoint)
        layout_tools.addWidget(self.btnFourClicks)
        layout_tools.addWidget(self.btnRitm)
        layout_tools.addWidget(self.btnFreehand)
        layout_tools.addWidget(self.btnWatershed)
        #layout_tools.addWidget(self.btnBricksSegmentation)
        layout_tools.addWidget(self.btnSam)
        layout_tools.addWidget(self.btnSamInteractive)
        layout_tools.addWidget(self.btnRows)
        layout_tools.addWidget(labelSeparator1) #separator-----------------------------------        
        layout_tools.addWidget(self.btnAssign)        
        layout_tools.addWidget(self.btnEditBorder)
        layout_tools.addWidget(self.btnCut)
        #layout_tools.addWidget(self.btnCreateCrack)
        layout_tools.addWidget(self.btnRuler)
        layout_tools.addWidget(labelSeparator2) #separator-----------------------------------        
        layout_tools.addWidget(self.btnAutoClassification)
        layout_tools.addWidget(labelSeparator3) #separator-----------------------------------
        layout_tools.addWidget(self.btnCreateGrid)
        layout_tools.addWidget(self.btnGrid)
        layout_tools.addWidget(labelSeparator4) #separator-----------------------------------
        layout_tools.addWidget(self.btnSplitScreen)
        layout_tools.addWidget(self.btnAutoMatch)
        layout_tools.addWidget(self.btnMatch)

        layout_tools.addStretch()
        

        # CONTEXT MENU ACTIONS

        self.markEmpty = self.newAction("Mark cell as empty",  "",   self.markEmptyOperation)
        self.markIncomplete = self.newAction("Mark cell as incomplete", "",   self.markIncompleteOperation)
        self.markComplete = self.newAction("Mark cell as complete", "",   self.markCompleteOperation)
        self.addNote = self.newAction("Add/edit note", "",   self.addNoteOperation)

        self.assignAction       = self.newAction("Assign Class to Region",    "A",   self.assignOperation)
        self.deleteAction       = self.newAction("Delete Region",             "Del", self.deleteSelectedBlobs)
        self.mergeAction        = self.newAction("Merge Overlapping Regions", "M",   self.union)
        self.divideAction       = self.newAction("Divide Regions",            "D",   self.divide)
        self.subtractAction     = self.newAction("Subtract Regions",          "S",   self.subtract)
        self.refineAction       = self.newAction("Refine Border",             "R",   self.refineBorderOperation)
        self.refineAllAction    = self.newAction("Refine All Borders",        "",    self.refineBorderAll)
        self.dilateAction       = self.newAction("Dilate Border",             "+",   self.dilate)
        self.erodeAction        = self.newAction("Erode Border",              "-",   self.erode)
        self.attachBoundariesAction = self.newAction("Snap Borders",          "B",   self.attachBoundaries)
        self.fillAction         = self.newAction("Fill Region",               "F",   self.fillLabel)
        self.createNegative = self.newAction("Create a Background Region using the WA", "N", self.createNegative)
        self.computeGeometricInfo = self.newAction("Compute Geometric Info", None, self.computeGeometricInfo)

        # SELECTION ACTIONS
        self.selectAllAction           = self.newAction("Select All",                "Ctrl+A", self.selectAll)
        self.selectNoneAction          = self.newAction("Select None",               "Ctrl+D", self.selectNone)
        self.selectInvertAction        = self.newAction("Invert Selection",          "Ctrl+I", self.selectInvert)
        self.selectByClassAction       = self.newAction("Select by Class",           "",       self.selectByClass)
        self.selectByWorkingAreaAction = self.newAction("Select by Working Area",    "",       self.selectByWorkingArea)
        self.selectByPropertiesAction  = self.newAction("Select by Properties",     "",       self.selectByProperties)

        # VIEWERPLUS

        # main viewer
        self.viewerplus = QtImageViewerPlus(self.taglab_dir)
        self.viewerplus.logfile = logfile
        self.viewerplus.viewUpdated.connect(self.updateViewInfo, type=Qt.UniqueConnection)
        self.viewerplus.activated.connect(self.setActiveViewer)
        self.viewerplus.updateInfoPanel.connect(self.updatePanelInfo)
        self.viewerplus.activeImageChanged[Image].connect(self.setActiveImage)
        self.viewerplus.mouseMoved[float, float].connect(self.updateMousePos)
        self.viewerplus.selectionChanged.connect(self.updateEditActions)
        self.viewerplus.selectionReset.connect(self.resetPanelInfo)

        # secondary viewer in SPLIT MODE
        self.viewerplus2 = QtImageViewerPlus(self.taglab_dir)
        self.viewerplus2.logfile = logfile
        self.viewerplus2.viewUpdated.connect(self.updateViewInfo, type=Qt.UniqueConnection)
        self.viewerplus2.activated.connect(self.setActiveViewer)
        self.viewerplus2.updateInfoPanel.connect(self.updatePanelInfo)
        self.viewerplus2.mouseMoved[float, float].connect(self.updateMousePos)
        self.viewerplus2.selectionChanged.connect(self.updateEditActions)
        self.viewerplus2.selectionReset.connect(self.resetPanelInfo)

        self.viewerplus.newSelection.connect(self.showMatch)
        self.viewerplus2.newSelection.connect(self.showMatch)

        self.viewerplus.newSelection.connect(self.showBlobOnTable)

        self.viewerplus.newSelectionPoint.connect(self.showPointOnTable)

        # SAM-related tool connections
        #self.viewerplus.tools.tools["SAM"].samEnded.connect(self.resetSam)
        #self.viewerplus2.tools.tools["SAM"].samEnded.connect(self.resetSam)
        
        # tool info messages
        # self.viewerplus.tools.tools["SAM"].tool_message.connect(self.message)
        # self.viewerplus.tools.tools["WATERSHED"].tool_message.connect(self.message)
        self.viewerplus.tools.tool_mess.connect(self.message)    

        # last activated viewerplus: redirect here context menu commands and keyboard commands
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
        self.checkBoxFill.setFocusPolicy(Qt.NoFocus)
        self.checkBoxFill.setMinimumWidth(60)
        self.checkBoxFill.stateChanged[int].connect(self.viewerplus.toggleFill)
        self.checkBoxFill.stateChanged[int].connect(self.viewerplus2.toggleFill)
        self.checkBoxFill.stateChanged[int].connect(self.saveGuiPreferences)

        self.checkBoxBorders = QCheckBox("Boundaries")
        self.checkBoxBorders.setChecked(True)
        self.checkBoxBorders.setFocusPolicy(Qt.NoFocus)
        self.checkBoxBorders.setMinimumWidth(120)
        self.checkBoxBorders.stateChanged[int].connect(self.viewerplus.toggleBorders)
        self.checkBoxBorders.stateChanged[int].connect(self.viewerplus2.toggleBorders)
        self.checkBoxBorders.stateChanged[int].connect(self.saveGuiPreferences)

        self.checkBoxIds = QCheckBox("Ids")
        self.checkBoxIds.setChecked(True)
        self.checkBoxIds.setFocusPolicy(Qt.NoFocus)
        self.checkBoxIds.setMinimumWidth(60)
        self.checkBoxIds.stateChanged[int].connect(self.viewerplus.toggleIds)
        self.checkBoxIds.stateChanged[int].connect(self.viewerplus2.toggleIds)
        self.checkBoxIds.stateChanged[int].connect(self.saveGuiPreferences)

        self.checkBoxGrid = QCheckBox("Grid")
        self.checkBoxGrid.setMinimumWidth(60)
        self.checkBoxGrid.setFocusPolicy(Qt.NoFocus)
        self.checkBoxGrid.stateChanged[int].connect(self.viewerplus.toggleGrid)
        self.checkBoxGrid.stateChanged[int].connect(self.viewerplus2.toggleGrid)
        self.checkBoxGrid.stateChanged[int].connect(self.saveGuiPreferences)

        self.labelZoom = QLabel("Zoom:")
        self.labelMouseLeft = QLabel("x:")
        self.labelMouseTop = QLabel("y:")

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
        layout_header.addWidget(self.checkBoxIds)
        layout_header.addWidget(self.checkBoxGrid)
        layout_header.addStretch()
        layout_header.addWidget(self.labelZoom)
        layout_header.addWidget(self.labelZoomInfo)
        layout_header.addWidget(self.labelMouseLeft)
        layout_header.addWidget(self.labelMouseLeftInfo)
        layout_header.addWidget(self.labelMouseTop)
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

        # LAYERS PANEL

        self.layers_widget = QtLayersWidget()
        self.layers_widget.setProject(self.project)
        self.layers_widget.showImage.connect(self.showImage)
        self.layers_widget.toggleLayer.connect(self.toggleLayer)
        self.layers_widget.toggleAnnotations.connect(self.toggleAnnotations)
        self.layers_widget.deleteLayer.connect(self.deleteLayer)


        # LABELS PANEL
        self.labels_widget = QtTableLabel()
        try:
            default_dict = "dictionaries/scripps.json"
            self.default_dictionary = self.settings_widget.settings.value("default-dictionary",
                                                                          defaultValue=default_dict,
                                                                          type=str)
            # Check if previously stored dict actually exists
            if not os.path.exists(self.default_dictionary):
                QMessageBox.warning(self,
                                    "Warning",
                                    f"Previously loaded dictionary {self.default_dictionary} not found! "
                                    f"Attempting to load TagLab default {default_dict} instead.")

                # If not, check for the scripps dictionary
                self.default_dictionary = default_dict
                if not os.path.exists(self.default_dictionary):
                    raise Exception(f"TagLab default dictionary {self.default_dictionary} not found! "
                                    f"Please re-download it.")

            # Re-set the default dictionary
            self.settings_widget.settings.setValue("default-dictionary", self.default_dictionary)
            # Load the dictionary, load the project
            self.project.loadDictionary(self.default_dictionary)
            self.labels_widget.setLabels(self.project, None)

        except Exception as e:
            # If neither exist, then open TagLab w/o a dict, and user can reset within
            QMessageBox.critical(self, "Error", str(e))

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
        layout_groupbox.addWidget(self.labels_widget)
        self.groupbox_labels.setLayout(layout_groupbox)

        # COMPARE PANEL
        self.compare_panel = QtComparePanel()
        self.compare_panel.filterChanged[str].connect(self.updateVisibleMatches)
        self.compare_panel.areaModeChanged[str].connect(self.updateAreaMode)
        self.compare_panel.data_table.clicked.connect(self.showConnectionCluster)

        # SINGLE-VIEW DATA PANEL
        self.data_panel = QtTablePanel()
        self.data_panel.selectionChanged.connect(self.showOnViewer)
        self.data_panel.selectionChanged.connect(self.updatePanelInfoSelected)


        self.groupbox_comparison = QGroupBox()

        layout_groupbox2 = QVBoxLayout()
        # in single view only show the table panel
        layout_groupbox2.addWidget(self.data_panel)
        self.compare_panel.hide()
        layout_groupbox2.addWidget(self.compare_panel)

        layout_groupbox2.setContentsMargins(QMargins(0, 0, 0, 0))
        self.groupbox_comparison.setLayout(layout_groupbox2)

        # # BLOB INFO
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.groupbox_blobpanel = QtPanelInfo(self.project.region_attributes, self.project.labels)

        self.scroll_area.setWidget(self.groupbox_blobpanel)

        self.blob_with_info_displayed = None

        # MAP VIEWER
        self.mapviewer = QtMapViewer(350)
        self.mapviewer.setMinimumHeight(200)
        self.mapviewer.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.MinimumExpanding)

        self.viewerplus.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage, type=Qt.UniqueConnection)
        self.mapviewer.leftMouseButtonPressed[float, float].connect(self.viewerplus.center)
        self.mapviewer.mouseMoveLeftPressed[float, float].connect(self.viewerplus.center)
        self.mapviewer.setStyleSheet("background-color: rgb(40,40,40); border:none")
        self.viewerplus2.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage, type=Qt.UniqueConnection)


        # DOCK
        panels_size = int(screen_size.width() * 0.22)
        if panels_size > 900:
            panels_size = 900
        if panels_size < 500:
            panels_size = 500

        self.layersdock = QDockWidget("Layers", self)
        self.layersdock.setWidget(self.layers_widget)
        self.layers_widget.setMinimumWidth(panels_size)
        self.layers_widget.setStyleSheet("padding: 0px")
        self.layersdock.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        self.labelsdock = QDockWidget("Labels", self)
        self.groupbox_labels.setMinimumWidth(panels_size)
        self.labelsdock.setWidget(self.groupbox_labels)
        self.groupbox_labels.setStyleSheet("padding: 0px")

        self.datadock = QDockWidget("Data Table", self)
        self.groupbox_comparison.setMinimumWidth(panels_size)
        self.datadock.setWidget(self.groupbox_comparison)
        self.groupbox_comparison.setStyleSheet("padding: 0px")

        self.blobdock = QDockWidget("Info and Attributes", self)
        # self.groupbox_blobpanel.setMinimumWidth(panels_size)
        self.scroll_area.setMinimumWidth(panels_size)
        # self.blobdock.setWidget(self.groupbox_blobpanel)
        self.blobdock.setWidget(self.scroll_area)

        self.mapdock = QDockWidget("Map Preview", self)
        self.mapviewer.preferred = panels_size
        self.mapviewer.setMinimumWidth(panels_size)
        self.mapdock.setWidget(self.mapviewer)
        self.mapdock.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.MinimumExpanding)

        for dock in (self.labelsdock, self.layersdock, self.datadock, self.blobdock, self.mapdock):
            dock.setAllowedAreas(Qt.RightDockWidgetArea)
            self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.setDockOptions(self.AnimatedDocks)

        self.compare_panel.setMinimumHeight(200)

        ##### MAIN LAYOUT

        central_widget_layout = QHBoxLayout()
        central_widget_layout.addLayout(layout_tools)
        central_widget_layout.addLayout(layout_main_view)

        # Add message widget to the central layout
        if self.message_widget is not None:
            central_widget_layout.addWidget(self.message_widget)
            # central_widget_layout.addLayout(self.message_widget.layout)

        self.central_widget = QWidget()
        self.central_widget.setLayout(central_widget_layout)
        self.setCentralWidget(self.central_widget)

        self.filemenu = None
        self.submenuWorkingArea = None
        self.submenuExport = None
        self.submenuImport = None
        self.selectmenu = None
        self.regionmenu = None
        self.comparemenu = None
        self.demmenu = None
        self.helpmenu = None

        self.setMenuBar(self.createMenuBar())

        self.setProjectTitle("NONE")

        ##### FURTHER INITIALIZAION #####
        #################################

        # CHECK SEGMENT_ANYTHING AVAILABILITY

        self.SAM_is_available = True
        if not self.viewerplus.tools.SAM_is_available:
            self.SAM_is_available = False
            self.btnSam.setVisible(False)
            self.btnSamInteractive.setVisible(False)

        # set default opacity
        self.sliderTransparency.setValue(50)
        self.transparency_value = 0.5

        # EVENTS-CONNECTIONS

        self.settings_widget.general_settings.researchFieldChanged[str].connect(self.researchFieldChanged)
        # self.settings_widget.general_settings.autosaveInfoChanged[int].connect(self.setAutosave)
        self.settings_widget.general_settings.autosaveInfoChanged[int].connect(self.setAutosave)

        self.settings_widget.drawing_settings.borderPenChanged[str, int].connect(self.viewerplus.setBorderPen)
        self.settings_widget.drawing_settings.selectionPenChanged[str, int].connect(self.viewerplus.setSelectionPen)
        self.settings_widget.drawing_settings.workingAreaPenChanged[str, int].connect(self.viewerplus.setWorkingAreaPen)
        self.settings_widget.drawing_settings.borderPenChanged[str, int].connect(self.viewerplus2.setBorderPen)
        self.settings_widget.drawing_settings.selectionPenChanged[str, int].connect(self.viewerplus2.setSelectionPen)
        self.settings_widget.drawing_settings.workingAreaPenChanged[str, int].connect(self.viewerplus2.setWorkingAreaPen)

        self.connectLabelsPanelWithViewers()

        self.connectProject()

        self.viewerplus.viewHasChanged[float, float, float].connect(self.viewerplus2.setViewParameters, type=Qt.UniqueConnection)
        self.viewerplus2.viewHasChanged[float, float, float].connect(self.viewerplus.setViewParameters, type=Qt.UniqueConnection)

        self.viewerplus.customContextMenuRequested.connect(self.openContextMenu)
        self.viewerplus2.customContextMenuRequested.connect(self.openContextMenu)

        self.settings_widget.loadSettings()

        # SWITCH IMAGES
        self.current_image_index = 0

        # current views parameters
        self.views_parameters = []

        # menu options
        self.mapActionList = []
        self.image2update = None

        # training results
        self.classifier_name = None
        self.network_name = None
        self.dataset_train = None

        # NETWORKS
        self.classifier = None

        # a dirty trick to adjust all the size..
        self.showMinimized()
        self.showMaximized()

        logfile.info("[INFO] Inizialization finished!")

        # autosave timer
        self.timer = QTimer(self)

        self.updateToolStatus()

        self.split_screen_flag = False
        self.update_panels_flag = True
        self.disableSplitScreen()

        self.viewerplus.setObjectName("viewer 1")
        self.viewerplus2.setObjectName("viewer 2")

        self.setPreferences()

        self.move()

    def toggleHeritageButtons(self, show=False):
        """
        Shows or hides segmentation buttons based on the 'show' parameter.
        :param show: If True, buttons will be shown; if False, buttons will be hidden
        """
        self.btnWatershed.setVisible(show)
        self.btnRows.setVisible(show)

        self.importViscorePointsAct.setVisible(not show)
        self.importCoralNetPointsAct.setVisible(not show)
        self.exportCoralNetPointsAct.setVisible(not show)
        self.exportCoralNetDataAct.setVisible(not show)
        self.openCoralNetToolboxAct.setVisible(not show)

    def setPreferences(self):

        settings = QSettings("VCLAB", "TagLab")

        # GOI preferences
        value = settings.value("gui-checkbox-fill", type=bool, defaultValue=True)
        self.checkBoxFill.setChecked(value)
        value = settings.value("gui-checkbox-borders", type=bool, defaultValue=True)
        self.checkBoxBorders.setChecked(value)
        value = settings.value("gui-checkbox-ids", type=bool, defaultValue=True)
        self.checkBoxIds.setChecked(value)
        value = settings.value("gui-checkbox-grid", type=bool, defaultValue=False)
        self.checkBoxGrid.setChecked(value)

        # general preferences
        research_field = settings.value("research-field", defaultValue="Marine Ecology", type=str)
        self.researchFieldChanged(research_field)

        interval = settings.value("autosave-interval", type=int, defaultValue=0)
        self.setAutosave(interval)

        # drawing preferences

        workingarea_pen_color = settings.value("workingarea-pen-color", defaultValue="0-255-0", type=str)
        workingarea_pen_width = settings.value("workingarea-pen-width", defaultValue=3, type=int)
        border_pen_color = settings.value("border-pen-color", defaultValue="0-0-0", type=str)
        border_pen_width = settings.value("border-pen-width", defaultValue=2, type=int)
        selection_pen_color = settings.value("selection-pen-color", defaultValue="255-255-255", type=str)
        selection_pen_width = settings.value("selection-pen-width", defaultValue=2, type=int)
        self.viewerplus.setBorderPen(border_pen_color, border_pen_width)
        self.viewerplus.setSelectionPen(selection_pen_color, selection_pen_width)
        self.viewerplus.setWorkingAreaPen(workingarea_pen_color, workingarea_pen_width)
        self.viewerplus2.setBorderPen(border_pen_color, border_pen_width)
        self.viewerplus2.setSelectionPen(selection_pen_color, selection_pen_width)
        self.viewerplus2.setWorkingAreaPen(workingarea_pen_color, workingarea_pen_width)


    @pyqtSlot()
    def saveGuiPreferences(self):

        settings = QSettings("VCLAB", "TagLab")
        settings.setValue("gui-checkbox-fill", self.checkBoxFill.isChecked())
        settings.setValue("gui-checkbox-borders", self.checkBoxBorders.isChecked())
        settings.setValue("gui-checkbox-ids", self.checkBoxIds.isChecked())
        settings.setValue("gui-checkbox-grid", self.checkBoxGrid.isChecked())

    def checkNewVersion(self):

        github_repo = 'cnr-isti-vclab/TagLab/'
        base_repo = 'https://github.com/' + github_repo
        raw_link = 'https://raw.githubusercontent.com/' + github_repo + 'main/TAGLAB_VERSION'

        # read offline version
        taglab_version_file = os.path.join(os.path.dirname(__file__), "TAGLAB_VERSION")
        f_off_version = open(taglab_version_file, "r")
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

        if shortcut != "":
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
        button.setIcon(QIcon(os.path.join(os.path.join(self.taglab_dir, "icons"), icon)))
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
        if self.contextMenuPosition is not None:
            self.activeviewer.updateCellState(self.contextMenuPosition.x(),self.contextMenuPosition.y(), 0)

    @pyqtSlot()
    def markIncompleteOperation(self):
        if self.contextMenuPosition is not None:
            self.activeviewer.updateCellState(self.contextMenuPosition.x(),self.contextMenuPosition.y(), 1)

    @pyqtSlot()
    def markCompleteOperation(self):
        if self.contextMenuPosition is not None:
            self.activeviewer.updateCellState(self.contextMenuPosition.x(), self.contextMenuPosition.y(), 2)


    @pyqtSlot()
    def addNoteOperation(self):

        if self.contextMenuPosition is not None and self.btnGrid.isChecked():
            self.activeviewer.addNote(self.contextMenuPosition.x(), self.contextMenuPosition.y())

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
        menu.addAction(self.attachBoundariesAction)
        menu.addAction(self.fillAction)

        menu.addSeparator()
        menu.addAction(self.refineAction)
        menu.addAction(self.dilateAction)
        menu.addAction(self.erodeAction)

        viewer = self.sender()
        self.contextMenuPosition = viewer.mapToGlobal(position)
        action = menu.exec_(self.contextMenuPosition)

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
        newAct.setStatusTip("Create A New Project")
        newAct.triggered.connect(self.newProject)

        openAct = QAction("Open Project", self)
        openAct.setShortcut('Ctrl+O')
        openAct.setStatusTip("Open An Existing Project")
        openAct.triggered.connect(self.openProject)

        saveAct = QAction("Save Project", self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.setStatusTip("Save Current Project")
        saveAct.triggered.connect(self.saveProject)

        saveAsAct = QAction("Save As", self)
        saveAsAct.setShortcut('Ctrl+Alt+S')
        saveAsAct.setStatusTip("Save Current Project")
        saveAsAct.triggered.connect(self.saveAsProject)

        for i in range(self.maxRecentFiles):
            self.recentFileActs.append(QAction(self, visible=False, triggered=self.openRecentProject))

        newMapAct = QAction("Add New Map...", self)
        newMapAct.setShortcut('Ctrl+L')
        newMapAct.setStatusTip("Add a new map to the project")
        newMapAct.triggered.connect(self.setMapToLoad)

        projectEditorAct = QAction("Maps Editor...", self)
        projectEditorAct.setShortcut('Ctrl+L')
        projectEditorAct.setStatusTip("Open project editor dialog")
        projectEditorAct.triggered.connect(self.openProjectEditor)

        ### PROJECT

        createDicAct = QAction("Labels Dictionary Editor...", self)
        createDicAct.triggered.connect(self.createDictionary)

        alignToolAct = QAction("Alignment Tool", self)
        alignToolAct.triggered.connect(self.openAlignmentTool)

        regionAttributesAct = QAction("Region Attributes...", self)
        regionAttributesAct.triggered.connect(self.editRegionAttributes)

        setWorkingAreaAct = QAction("Set Working Area", self)
        setWorkingAreaAct.triggered.connect(self.selectWorkingArea)

        ### IMPORT

        appendAct = QAction("Add Another Project", self)
        appendAct.setStatusTip("Add to the current project the annotated images of another project")
        appendAct.triggered.connect(self.importAnnotations)

        importAct = QAction("Import Label Image", self)
        importAct.setStatusTip("Import a label image")
        importAct.triggered.connect(self.importLabelMap)

        importShap = QAction("Import Shapefile", self)
        importShap.setStatusTip("Import a georeferenced shapefile")
        importShap.triggered.connect(self.importShapefile)

        ### EXPORT

        exportDataTableAct = QAction("Export Annotations As Data Table", self)
        #exportDataTableAct.setShortcut('Ctrl+??')
        exportDataTableAct.setStatusTip("Export annotations as CSV table")
        exportDataTableAct.triggered.connect(self.exportAnnAsDataTable)

        exportMapAct = QAction("Export Regions As Labeled Image", self)
        #exportMapAct.setShortcut('Ctrl+??')
        exportMapAct.setStatusTip("Export visibile regions as labeled image")
        exportMapAct.triggered.connect(self.exportAnnAsMap)

        exportHistogramAct = QAction("Export Histogram From Regions", self)
        # exportHistogramAct.setShortcut('Ctrl+??')
        exportHistogramAct.setStatusTip("Export histogram from regions")
        exportHistogramAct.triggered.connect(self.exportHistogramFromAnn)

        exportShapefilesAct = QAction("Export Regions As Shapefile", self)
        # exportShapefilesAct.setShortcut('Ctrl+??')
        exportShapefilesAct.setStatusTip("Export visible regions as shapefile")
        exportShapefilesAct.triggered.connect(self.exportAnnAsShapefiles)

        exportDXFfilesAct = QAction("Export Regions As DXF", self)
        exportDXFfilesAct.setStatusTip("Export visible regions as DXF")
        exportDXFfilesAct.triggered.connect(self.exportAnnAsDXF)

        exportGeoRefLabelMapAct = QAction("Export Regions As A GeoTiff", self)
        exportGeoRefLabelMapAct.setStatusTip("Create a label image and export it as a GeoTiff")
        exportGeoRefLabelMapAct.triggered.connect(self.exportGeoRefLabelMap)

        exportGeoRefImgAct = QAction("Export Orthoimage As A GeoTiff", self)
        exportGeoRefImgAct.setStatusTip("Export visible ortho-image as a GeoTiff")
        exportGeoRefImgAct.triggered.connect(self.exportGeoRefImage)

        exportTrainingDatasetAct = QAction("Export New Training Dataset", self)
        exportTrainingDatasetAct.setStatusTip("Export A new training dataset based on the current annotations")
        exportTrainingDatasetAct.triggered.connect(self.exportAnnAsTrainingDataset)

        filterDatasetAct = QAction("Dataset Manager", self)
        filterDatasetAct.setStatusTip("Filter the tiles of a training dataset")
        filterDatasetAct.triggered.connect(self.openDatasetManager)

        trainYourNetworkAct = QAction("Train Your Network", self)
        trainYourNetworkAct.setStatusTip("Export A new training dataset and, eventually, train your network on it")
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

        goToDocumentationAct = QAction("Learn TagLab", self)
        goToDocumentationAct.setStatusTip("Link to the documentation web page")
        goToDocumentationAct.triggered.connect(self.goToDocumentation)

        repAct = QAction("Report Issues", self)
        repAct.setStatusTip("Report Issues")
        repAct.triggered.connect(self.report)

        aboutAct = QAction("About TagLab", self)
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
        self.submenuExport.addAction(exportDXFfilesAct)
        self.submenuExport.addAction(exportGeoRefLabelMapAct)
        self.submenuExport.addAction(exportGeoRefImgAct)
        self.submenuExport.addAction(exportHistogramAct)
        self.submenuExport.addAction(exportTrainingDatasetAct)
        self.filemenu.addSeparator()
        self.filemenu.addAction(settingsAct)

        #### PROJECT MENU

        self.projectmenu = menubar.addMenu("&Project")
        self.projectmenu.setStyleSheet(styleMenu)
        self.projectmenu.addAction(newMapAct)
        self.projectmenu.addAction(projectEditorAct)
        self.projectmenu.addSeparator()
        self.projectmenu.addAction(setWorkingAreaAct)
        self.projectmenu.addSeparator()
        self.projectmenu.addAction(alignToolAct)
        self.projectmenu.addSeparator()
        self.projectmenu.addAction(createDicAct)
        self.projectmenu.addSeparator()
        self.projectmenu.addAction(regionAttributesAct)

        ###### SELECT MENU
        self.selectmenu = menubar.addMenu("&Select")
        self.selectmenu.setStyleSheet(styleMenu)
        self.selectmenu.addAction(self.selectAllAction)
        self.selectmenu.addAction(self.selectNoneAction)
        self.selectmenu.addAction(self.selectInvertAction)
        self.selectmenu.addSeparator()
        self.selectmenu.addAction(self.selectByClassAction)
        self.selectmenu.addAction(self.selectByWorkingAreaAction)
        self.selectmenu.addAction(self.selectByPropertiesAction)
        self.selectmenu.addSeparator()

        ###### REGIONS MENU

        self.regionmenu = menubar.addMenu("&Regions")
        self.regionmenu.setStyleSheet(styleMenu)
        self.regionmenu.addAction(undoAct)
        self.regionmenu.addAction(redoAct)
        self.regionmenu.addSeparator()
        self.regionmenu.addAction(self.assignAction)
        self.regionmenu.addAction(self.deleteAction)
        self.regionmenu.addSeparator()
        self.regionmenu.addAction(self.mergeAction)
        self.regionmenu.addAction(self.divideAction)
        self.regionmenu.addAction(self.subtractAction)
        self.regionmenu.addAction(self.attachBoundariesAction)
        self.regionmenu.addAction(self.fillAction)
        self.regionmenu.addSeparator()
        self.regionmenu.addAction(self.refineAction)
        self.regionmenu.addAction(self.refineAllAction)
        self.regionmenu.addAction(self.dilateAction)
        self.regionmenu.addAction(self.erodeAction)
        self.regionmenu.addSeparator()
        self.regionmenu.addAction(self.createNegative)
        self.regionmenu.addAction(self.computeGeometricInfo)

        ###### POINT ANNOTATIONS MENU

        samplePointsAct = QAction("Sample Points On This Map", self)
        samplePointsAct.setStatusTip("Sample Points This Map")
        samplePointsAct.triggered.connect(self.chooseSampling)

        self.importViscorePointsAct = QAction("Import Viscore Point Annotations", self)
        self.importViscorePointsAct.setStatusTip("Import Point Annotations From .CSV")
        self.importViscorePointsAct.triggered.connect(self.importViscorePointAnn)
        self.importViscorePointsAct.setVisible(True)

        self.importCoralNetPointsAct = QAction("Import CoralNet Point Annotations", self)
        self.importCoralNetPointsAct.setStatusTip("Import Point Annotations From .CSV")
        self.importCoralNetPointsAct.triggered.connect(self.importCoralNetPointAnn)
        self.importCoralNetPointsAct.setVisible(True)

        self.exportCoralNetPointsAct = QAction("Export CoralNet Point Annotations", self)
        self.exportCoralNetPointsAct.setStatusTip("Export Point Annotations As .CSV")
        self.exportCoralNetPointsAct.triggered.connect(self.exportCoralNetPointAnn)
        self.exportCoralNetPointsAct.setVisible(True)

        self.exportCoralNetDataAct = QAction("Export Tiled Data for CoralNet", self)
        self.exportCoralNetDataAct.setStatusTip("Export Data for CoralNet Model Training")
        self.exportCoralNetDataAct.triggered.connect(self.exportCoralNetPointData)
        self.exportCoralNetDataAct.setVisible(True)

        self.openCoralNetToolboxAct = QAction("Open CoralNet-Toolbox...", self)
        self.openCoralNetToolboxAct.triggered.connect(self.openCoralNetToolbox)
        self.openCoralNetToolboxAct.setVisible(True)

        self.pointmenu = menubar.addMenu("&Points")
        self.pointmenu.setStyleSheet(styleMenu)
        self.pointmenu.addAction(samplePointsAct)
        self.pointmenu.addSeparator()
        self.pointmenu.addAction(self.importViscorePointsAct)
        self.pointmenu.addAction(self.importCoralNetPointsAct)
        self.pointmenu.addAction(self.exportCoralNetPointsAct)
        self.pointmenu.addAction(self.exportCoralNetDataAct)
        self.pointmenu.addSeparator()
        self.pointmenu.addAction(self.openCoralNetToolboxAct)


        ##### DEM MENU

        calculateSurfaceAreaAct = QAction("Calculate Surface Area", self)
        calculateSurfaceAreaAct.setStatusTip("Estimate surface area using slope derived from the DEM")
        calculateSurfaceAreaAct.triggered.connect(self.calculateAreaUsingSlope)

        exportClippedRasterAct = QAction("Export Clipped Raster", self)
        exportClippedRasterAct.setStatusTip("Export a raster clipped using visible annotations")
        exportClippedRasterAct.triggered.connect(self.exportClippedRaster)

        switchAct = QAction("Switch RGB/DEM", self)
        switchAct.setStatusTip("Switch between the image and the DEM")
        switchAct.triggered.connect(self.switch)

        self.demmenu = menubar.addMenu("&DEM")
        self.demmenu.setStyleSheet(styleMenu)
        self.demmenu.addAction(switchAct)
        self.demmenu.addAction(calculateSurfaceAreaAct)
        self.demmenu.addAction(exportClippedRasterAct)


        splitScreenAction = QAction("Enable Split Screen", self)
        splitScreenAction.setShortcut('Alt+S')
        splitScreenAction.setStatusTip("Split screen")
        splitScreenAction.triggered.connect(self.toggleComparison)

        autoMatchLabels = QAction("Compute Automatic Matches", self)
        autoMatchLabels.setStatusTip("Match labels between two maps automatically")
        autoMatchLabels.triggered.connect(self.autoCorrespondences)

        manualMatchLabels = QAction("Edit Manual Matches", self)
        manualMatchLabels.setStatusTip("Edit manual matches")
        manualMatchLabels.triggered.connect(self.matchTool)

        exportMatchLabels = QAction("Export Matches", self)
        exportMatchLabels.setStatusTip("Export the current matches")
        exportMatchLabels.triggered.connect(self.exportMatches)

        clearComparisonTable = QAction("Clear Comparison Table", self)
        clearComparisonTable.setStatusTip("EClear Comparison Table")
        clearComparisonTable.triggered.connect(self.clearComparisonTable)

        exportGenetSVG = QAction("Export Genet Data As Shapes", self)
        exportGenetSVG.setStatusTip("Export genets history of corals in SVG.")
        exportGenetSVG.triggered.connect(self.exportGenetSVG)

        exportGenetCSV = QAction("Export Genet Data as CSV", self)
        exportGenetCSV.setStatusTip("Export genets history of corals in CSV")
        exportGenetCSV.triggered.connect(self.exportGenetCSV)


        ##### TRAIN MENU

        self.trainmenu = menubar.addMenu("&Train")
        self.trainmenu.setStyleSheet(styleMenu)
        self.trainmenu.addAction(exportTrainingDatasetAct)
        self.trainmenu.addAction(filterDatasetAct)
        self.trainmenu.addAction(trainYourNetworkAct)


        ##### COMPARE MENU

        self.comparemenu = menubar.addMenu("&Compare")
        self.comparemenu.setStyleSheet(styleMenu)
        self.comparemenu.addAction(splitScreenAction)
        self.comparemenu.addAction(autoMatchLabels)
        self.comparemenu.addAction(manualMatchLabels)
        self.comparemenu.addAction(exportMatchLabels)
        self.comparemenu.addSeparator()
        self.comparemenu.addAction(exportGenetSVG)
        self.comparemenu.addAction(exportGenetCSV)
        self.comparemenu.addSeparator()
        self.comparemenu.addAction(clearComparisonTable)


        ##### VIEW MENU

        self.viewmenu = menubar.addMenu("&View")
        self.viewmenu.setStyleSheet(styleMenu)
        self.viewmenu.addAction(self.labelsdock.toggleViewAction())
        self.viewmenu.addAction(self.layersdock.toggleViewAction())
        self.viewmenu.addAction(self.blobdock.toggleViewAction())
        self.viewmenu.addAction(self.mapdock.toggleViewAction())
        self.viewmenu.addAction(self.datadock.toggleViewAction())


        ##### HELP MENU

        self.helpmenu = menubar.addMenu("&Help")
        self.helpmenu.setStyleSheet(styleMenu)
        self.helpmenu.addAction(helpAct)
        self.helpmenu.addAction(goToDocumentationAct)
        self.helpmenu.addAction(repAct)
        self.helpmenu.addAction(aboutAct)

        return menubar

    def connectLabelsPanelWithViewers(self):

        self.labels_widget.activeLabelChanged[str].connect(self.viewerplus.setActiveLabel)
        self.labels_widget.activeLabelChanged[str].connect(self.viewerplus2.setActiveLabel)

        self.labels_widget.visibilityChanged.connect(self.viewerplus.updateVisibility)
        self.labels_widget.visibilityChanged.connect(self.viewerplus2.updateVisibility)

        self.labels_widget.doubleClickLabel[str].connect(self.viewerplus.assignClass)
        self.labels_widget.doubleClickLabel[str].connect(self.viewerplus2.assignClass)


    @pyqtSlot()
    def settings(self):

        self.settings_widget.setWindowModality(Qt.WindowModal)
        self.settings_widget.show()

    @pyqtSlot(str)
    def researchFieldChanged(self, index):

        if index == "Digital Heritage":
            self.toggleHeritageButtons(show=True)
        elif index == "Marine Ecology":
            self.toggleHeritageButtons(show=False)
        else:
            # if the research field is not properly defined, the 'Heritage' functionalities are disabled
            self.toggleHeritageButtons(show=False)

    @pyqtSlot(QAction)
    def editMapSettings(self, openMapAction):

        index = self.mapActionList.index(openMapAction)
        image = self.project.images[index]
        self.editMapSettingsImage(image)

    def editMapSettingsImage(self, image):

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

    def cropMapImage(self, img):

        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                if self.crop_widget is None:

                    self.disableSplitScreen()

                    self.crop_widget = QtCropWidget(self.edit_project_widget)
                    self.crop_widget.btnChooseArea.clicked.connect(self.enableAreaSelection)
                    self.crop_widget.closed.connect(self.disableAreaSelection)
                    self.crop_widget.closed.connect(self.deleteCropWidget)
                    self.crop_widget.btnApply.clicked.connect(lambda x, img = img:self.cropImage)
                    selection_tool = self.activeviewer.tools.tools["SELECTAREA"]
                    selection_tool.setAreaStyle("PREVIEW")
                    selection_tool.rectChanged[int, int, int, int].connect(self.crop_widget.updateArea)
                    self.crop_widget.areaChanged[int, int, int, int].connect(selection_tool.setSelectionRectangle)

        self.crop_widget.show()


    def cropImage(self,img):

        x, y, width, height = self.crop_widget.getCropArea()
        if width != 0 and height != 0:

            # Create copy of image
            tag = "_cropped"
            name = img.id + tag
            img_copy = Image(
                rect=img.rect,
                map_px_to_mm_factor=img.map_px_to_mm_factor,
                width=width,
                height=height,
                id=img.id,
                name=name,
                acquisition_date=img.acquisition_date,
                georef_filename=img.georef_filename,
                metadata=img.metadata,
                layers=img.layers,
                grid=img.grid,
                export_dataset_area=img.export_dataset_area
            )

            # copy blobs
            for blob in img.blobs:
                img_copy.annotations.addBlob(blob)

            # copy channels
            for channel in img.channels:
                pass

            # update blobs coordinates
            pass

            # Add image
            self.project.addNewImage(img_copy)

            # delete original image from the project
            self.deleteImage(img)

            # save project with the same name
            self.project.save()

            self.crop_widget.close()
            self.deleteCropWidget()
        else:
            box = QMessageBox(self.crop_widget)
            box.setText("Please, select a valid cropping area")
            box.exec()
            return


        pass

    @pyqtSlot()
    def deleteCropWidget(self):

        del self.crop_widget
        self.crop_widget = None

    def deleteImage(self, img):

        # update project
        self.project.deleteImage(img)
        if len(self.project.images) == 0:
            self.resetAll()
            return

        # update views
        index = max(self.comboboxSourceImage.currentIndex()-1, 0)

        self.disableSplitScreen()
        
        if self.viewerplus.image == img:
            self.showImage(self.project.images[index])

        # update tool buttons according to the current number of images
        self.updateToolStatus()

    def deleteLayer(self, img, layer):
        box = QMessageBox()
        reply = box.question(self.working_area_widget, self.TAGLAB_VERSION, "Are you sure to delete layer: " + layer.name + " ?",
                             QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
            
        if self.viewerplus.image == img:
            self.viewerplus.undrawLayer(layer)

        if self.viewerplus2.image == img:
            self.viewerplus2.undrawLayer(layer)

        img.deleteLayer(layer)
        self.layers_widget.setProject(self.project)

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
    def exportGenetSVG(self):
        filters = "SVG (*.svg)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save genet shapes in SVG", self.taglab_dir, filters)
        if not filename:
            return

        self.project.genet.updateGenets()
        self.project.genet.exportSVG(filename)

        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(self.TAGLAB_VERSION)
        msgBox.setText("Shapes history exported successfully!")
        msgBox.exec()

    @pyqtSlot()
    def exportGenetCSV(self):
        filters = "CSV (*.csv)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save genet data in CSV", self.taglab_dir, filters)
        if not filename:
            return

        self.project.genet.updateGenets()
        self.project.genet.exportCSV(filename)

        msgBox = QMessageBox(self)
        msgBox.setWindowTitle(self.TAGLAB_VERSION)
        msgBox.setText("Genet data table exported successfully!")
        msgBox.exec()


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

        if img_source_index == img_target_index:
            return

        key = self.project.images[img_source_index].id + "-" + self.project.images[img_target_index].id
        corr = self.project.correspondences.get(key)

        if corr is not None and corr.data.empty is False:
            reply = QMessageBox.question(self, self.TAGLAB_VERSION,
                        "Would you like to clean up the table and replace all the existing matches?",
                        QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

        self.project.computeCorrespondences(img_source_index, img_target_index)
        self.compare_panel.setTable(self.project, img_source_index, img_target_index)
        self.setTool("MATCH")

    @pyqtSlot()
    def clearComparisonTable(self):

        if len(self.project.images) < 2:
            return

        if self.split_screen_flag is False:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Please, enable Split Screen and select the source and the target image(!)")
            msgBox.exec()
            return

        img_source_index = self.comboboxSourceImage.currentIndex()
        img_target_index = self.comboboxTargetImage.currentIndex()

        if img_source_index == img_target_index:
            return

        key = self.project.images[img_source_index].id + "-" + self.project.images[img_target_index].id
        self.project.clearComparisonTable(key)
        self.compare_panel.clear()



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
            msg = "[KEYPRESS] Key SHIFT + '" + key_pressed + "' has been pressed."
        elif modifiers == Qt.AltModifier:
            msg = "[KEYPRESS] Key ALT + '" + key_pressed + "' has been pressed."
        else:
            msg = "[KEYPRESS] Key '" + key_pressed + "' has been pressed."

        logfile.info(msg)

        if event.key() == Qt.Key_Escape:
            for viewer in (self.viewerplus, self.viewerplus2):

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

        elif event.key() == Qt.Key_U:

            # update grid cell state
            if self.btnGrid.isChecked():
                pos = self.cursor().pos()
                self.activeviewer.updateCellState(pos.x(), pos.y(), None)

        elif event.key() == Qt.Key_1:
            # ACTIVATE "MOVE" TOOL
            self.move()

        elif event.key() == Qt.Key_2:
            # ACTIVATE "4-CLICK" TOOL
            self.fourClicks()

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

        elif event.key() == Qt.Key_Q:
            # toggle fill
            if self.checkBoxFill.isChecked():
               self.viewerplus.toggleFill(1)
               self.viewerplus2.toggleFill(1)
               self.checkBoxFill.setChecked(False)
            else:
                self.viewerplus.toggleFill(0)
                self.viewerplus2.toggleFill(0)
                self.checkBoxFill.setChecked(True)

        elif event.key() == Qt.Key_W:
            # toggle boundaries
            if self.checkBoxBorders.isChecked():
               self.viewerplus.toggleBorders(1)
               self.viewerplus2.toggleBorders(1)
               self.checkBoxBorders.setChecked(False)
            else:
                self.viewerplus.toggleBorders(0)
                self.viewerplus2.toggleBorders(0)
                self.checkBoxBorders.setChecked(True)

        elif event.key() == Qt.Key_E:
            # toggle regions ids
            if self.checkBoxIds.isChecked():
                self.viewerplus.toggleIds(1)
                self.viewerplus2.toggleIds(1)
                self.checkBoxIds.setChecked(False)
            else:
                self.viewerplus.toggleIds(0)
                self.viewerplus2.toggleIds(0)
                self.checkBoxIds.setChecked(True)

        elif event.key() == Qt.Key_G:
            # toggle grid
            if self.checkBoxGrid.isChecked():
               self.viewerplus.toggleGrid(1)
               self.viewerplus2.toggleGrid(1)
               self.checkBoxGrid.setChecked(False)
            else:
                self.viewerplus.toggleGrid(0)
                self.viewerplus2.toggleGrid(0)
                self.checkBoxGrid.setChecked(True)

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


    def setBlobVisualization(self):

        if self.activeviewer.image is not None:

            if self.checkBoxFill.isChecked():
                self.viewerplus.enableFill()
                self.viewerplus2.enableFill()
            else:
                self.viewerplus.disableFill()
                self.viewerplus2.disableFill()

            if self.checkBoxBorders.isChecked():
                self.viewerplus.enableBorders()
                self.viewerplus2.enableBorders()
            else:
                self.viewerplus.disableBorders()
                self.viewerplus2.disableBorders()

            if self.checkBoxGrid.isChecked():
                self.viewerplus.showGrid()
                self.viewerplus2.showGrid()
            else:
                self.viewerplus.hideGrid()
                self.viewerplus2.hideGrid()

    def disableSplitScreen(self):

        if self.activeviewer is not None:
            if self.activeviewer.tools.tool == "MATCH":
                self.setTool("MOVE")

        self.viewerplus2.hide()

        self.compare_panel.hide()
        self.data_panel.show()
        self.datadock.setWindowTitle("Data table")

        self.comboboxTargetImage.hide()
        self.blobdock.show()

        if self.comparemenu is not None:
            splitScreenAction = self.comparemenu.actions()[0]
            if splitScreenAction is not None:
                splitScreenAction.setText("Enable Split Screen")

        # just in case..
        try:
            self.viewerplus2.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage, Qt.UniqueConnection)
        except:
            pass

        # disconnect viewer 2 slots
        self.viewerplus2.viewUpdated[QRectF].disconnect()

        self.btnSplitScreen.setChecked(False)
        self.split_screen_flag = False

        self.activeviewer = self.viewerplus
        self.updatePanels()

        if self.viewerplus.image is not None:
            # when the split screen is disabled the image should be re-set
            self.viewerplus.setImage(self.viewerplus.image)

    def enableSplitScreen(self):

        if self.working_area_widget is not None:
            self.btnSplitScreen.setChecked(False)
            return

        if len(self.project.images) > 1:

            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.viewerplus.viewChanged()

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

            self.doNotUpdatePanels()
            self.viewerplus.clear()
            self.viewerplus.setProject(self.project)
            self.viewerplus.setImage(self.project.images[index_to_set])
            self.viewerplus2.clear()
            self.viewerplus2.setProject(self.project)
            self.viewerplus2.setImage(self.project.images[index_to_set + 1])
            self.setBlobVisualization()

            self.doUpdatePanels()

            self.comboboxSourceImage.currentIndexChanged.connect(self.sourceImageChanged)
            self.comboboxTargetImage.currentIndexChanged.connect(self.targetImageChanged)

            QApplication.restoreOverrideCursor()

            self.viewerplus2.show()
            self.comboboxTargetImage.show()
            self.viewerplus.viewChanged()

            try:
                self.viewerplus2.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage, type=Qt.UniqueConnection)
            except:
                pass

            if self.comparemenu is not None:
                splitScreenAction = self.comparemenu.actions()[0]
                if splitScreenAction is not None:
                    splitScreenAction.setText("Disable Split Screen")

            self.blobdock.hide()

            self.btnSplitScreen.setChecked(True)
            self.split_screen_flag = True

            self.activeviewer = self.viewerplus

            self.compare_panel.show()
            self.data_panel.hide()
            self.datadock.setWindowTitle("Comparison Table")
            self.updatePanels()

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

            # if the correspondences table does not exist a new one is created
            corr = self.project.getImagePairCorrespondences(img_source_index, img_target_index)
            if corr is None:
                corr = self.project.createCorrespondencesTable(img_source_index, img_target_index)

            self.project.addCorrespondences(corr, sel1, sel2)

            if self.compare_panel.correspondences == corr:
                self.compare_panel.updateTable(corr)
            else:
                self.compare_panel.setTable(self.project, img_source_index, img_target_index)

            # highlight the correspondences just added and show it by scroll
            if len(sel1) > 0:
                self.showCluster(sel1[0].id, is_source=True, center=False)
            elif len(sel2) > 0:
                self.showCluster(sel2[0].id, is_source=False, center=False)


    @pyqtSlot()
    def showOnViewer(self):

        self.viewerplus.resetSelection()

        selected = self.data_panel.data_table.selectionModel().selectedRows()
        #convert proxyf sortfilter indexes to modelindexes which are the same of the .data_table
        indexes = [self.data_panel.sortfilter.mapToSource(self.data_panel.sortfilter.index(index.row(), 0)) for index in selected]

        for index in indexes:
            row = self.data_panel.data.iloc[index.row()]
            id = row['Id']
            type = row['Type']
            if id < 0:
                print("OOOPS!")
                continue

            if type == "R":

                blob = self.viewerplus.annotations.blobById(id)
                self.viewerplus.addToSelectedList(blob)

                box = blob.bbox
                x = box[1] + box[2] / 2
                y = box[0] + box[3] / 2
                self.viewerplus.centerOn(x, y)

            else:

                point = self.viewerplus.annotations.pointById(id)
                self.viewerplus.addToSelectedPointList(point)

                x = point.coordx
                y = point.coordy
                self.viewerplus.centerOn(x, y)

    @pyqtSlot()
    def showBlobOnTable(self):

        if self.activeviewer is None:
            return
        
        selected = self.activeviewer.selected_blobs

        rows = []
        for blob in selected:
            selected_row = self.data_panel.data.index[(self.data_panel.data["Id"] == blob.id)].to_list()
            if selected_row is not None:
                rows += selected_row

        self.data_panel.blockSignals(True)
        self.data_panel.selectRows(rows)
        self.data_panel.blockSignals(False)

    @pyqtSlot()
    def showPointOnTable(self):

        if self.activeviewer is None:
            return

        selected = self.activeviewer.selected_annpoints

        rows = []
        for point in selected:
            selected_row = self.data_panel.data.index[(self.data_panel.data["Id"] == point.id) & (self.data_panel.data["Type"] == 'P')].to_list()
            if selected_row is not None:
                rows += selected_row

        self.data_panel.blockSignals(True)
        self.data_panel.selectRows(rows)
        self.data_panel.blockSignals(False)

    @pyqtSlot()
    def showConnectionCluster(self):
        indexes = self.compare_panel.data_table.selectionModel().selectedRows()
        if len(indexes) == 0:
            return

        img_source_index = self.comboboxSourceImage.currentIndex()
        img_target_index = self.comboboxTargetImage.currentIndex()
        corr = self.project.getImagePairCorrespondences(img_source_index, img_target_index)
        if corr:
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

        selected = self.compare_panel.data_table.selectionModel().selectedRows()
        if len(selected) == 0:
            return

        indexes = [self.compare_panel.sortfilter.mapToSource(index).row() for index in selected]

        img_source_index = self.comboboxSourceImage.currentIndex()
        img_target_index = self.comboboxTargetImage.currentIndex()
        corr = self.project.getImagePairCorrespondences(img_source_index, img_target_index)
        if corr:
            corr.deleteCluster(indexes)
            self.project.updateGenets()

            self.viewerplus.resetSelection()
            self.viewerplus2.resetSelection()

            if self.compare_panel.correspondences is not None:
                self.compare_panel.setTable(self.project, img_source_index, img_target_index)
            else:
                self.compare_panel.updateTable(corr)


    @pyqtSlot()
    def showMatch(self):

        if self.activeviewer is None:
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
          if corr:

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
            if correspondences:
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

            if correspondences:
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

        viewer = self.sender()

        if self.activeviewer != viewer:

            self.activeviewer = viewer

            if self.activeviewer is not self.viewerplus:
                self.inactiveviewer = self.viewerplus
            else:
                self.inactiveviewer = self.viewerplus2

            self.inactiveviewer.resetTools()

            # update panels accordingly
            #self.updatePanels()
            self.updateMapViewer()

    def updateImageSelectionMenu(self):

        # disconnect so that only the combobox are updated
        self.comboboxSourceImage.currentIndexChanged.disconnect()
        self.comboboxTargetImage.currentIndexChanged.disconnect()

        index1 = self.comboboxSourceImage.currentIndex()
        index2 = self.comboboxTargetImage.currentIndex()

        if index1 < 1:
            index1 = 0

        n = len(self.project.images) - 1
        if index1 > n:
            index1 = n

        if index2 < 1:
            index2 = 0

        if index2 > n:
            index2 = n

        # update the image names
        self.comboboxSourceImage.clear()
        self.comboboxTargetImage.clear()
        for image in self.project.images:
            self.comboboxSourceImage.addItem(image.name)
            self.comboboxTargetImage.addItem(image.name)

        self.comboboxSourceImage.setCurrentIndex(index1)
        self.comboboxTargetImage.setCurrentIndex(index2)

        # re-connect
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

    def storeCurrentViewsParameters(self):
        """
        Store the current view parameters (both left and right views).
        """
        posx1 = self.viewerplus.horizontalScrollBar().value()
        posy1 = self.viewerplus.verticalScrollBar().value()
        zoom1 = self.viewerplus.zoom_factor / self.viewerplus.px_to_mm
        posx2 = self.viewerplus2.horizontalScrollBar().value()
        posy2 = self.viewerplus2.verticalScrollBar().value()
        zoom2 = self.viewerplus2.zoom_factor / self.viewerplus2.px_to_mm

        self.views_parameters = []
        self.views_parameters.append((posx1, posy1, zoom1))
        self.views_parameters.append((posx2, posy2, zoom2))

        print(self.views_parameters)

    def resetViewsParameters(self):
        """
        Re-assign the previously stored view parameters.
        """

        view1 = self.views_parameters[0]
        self.viewerplus.setViewParameters(view1[0], view1[1], view1[2])
        view2 = self.views_parameters[1]
        self.viewerplus2.setViewParameters(view2[0], view2[1], view2[2])

    @pyqtSlot(int)
    def sourceImageChanged(self, index1):

        N = len(self.project.images)
        if index1 == -1 or index1 >= N:
            return

        # store view parameters
        self.storeCurrentViewsParameters()

        self.viewerplus.viewHasChanged.disconnect(self.viewerplus2.setViewParameters)
        self.viewerplus2.viewHasChanged.disconnect(self.viewerplus.setViewParameters)

        image = self.project.images[index1]
        self.viewerplus.clear()

        # target and source image cannot be the same !!
        index2 = self.comboboxTargetImage.currentIndex()
        if index1 == index2:
            index2 = (index1 + 1) % N

            self.doNotUpdatePanels()
            self.viewerplus2.clear()
            self.viewerplus2.setProject(self.project)
            self.viewerplus2.setImage(self.project.images[index2])
            self.doUpdatePanels()

            self.updateComboboxTargetImage(index2)

        self.viewerplus.setProject(self.project)
        self.viewerplus.setImage(image)
        self.setBlobVisualization()
        self.updatePanels()
        if self.compare_panel.isVisible():
            self.compare_panel.setTable(self.project, index1, index2)

        # set the view parameters as the stored one before the image change
        self.resetViewsParameters()

        self.viewerplus.viewHasChanged[float, float, float].connect(self.viewerplus2.setViewParameters, type=Qt.UniqueConnection)
        self.viewerplus2.viewHasChanged[float, float, float].connect(self.viewerplus.setViewParameters, type=Qt.UniqueConnection)


    @pyqtSlot(int)
    def targetImageChanged(self, index2):

        N = len(self.project.images)
        if index2 == -1 or index2 >= N:
            return

        # store view parameters
        self.storeCurrentViewsParameters()

        self.viewerplus.viewHasChanged.disconnect(self.viewerplus2.setViewParameters)
        self.viewerplus2.viewHasChanged.disconnect(self.viewerplus.setViewParameters)

        self.viewerplus2.clear()
        self.btnGrid.setChecked(False)

        # target and source image cannot be the same !!
        index1 = self.comboboxSourceImage.currentIndex()
        if index1 == index2:
            index1 = (index2 - 1) % N

            self.doNotUpdatePanels()
            self.viewerplus.clear()
            self.viewerplus.setProject(self.project)
            self.viewerplus.setImage(self.project.images[index1])
            self.doUpdatePanels()

            self.updateComboboxSourceImage(index1)

        self.viewerplus2.setProject(self.project)
        self.viewerplus2.setImage(self.project.images[index2])
        self.setBlobVisualization()
        self.updatePanels()
        if self.compare_panel.isVisible():
            self.compare_panel.setTable(self.project, index1, index2)

        # set the view parameters as the stored one before the image change
        self.resetViewsParameters()

        self.viewerplus.viewHasChanged[float, float, float].connect(self.viewerplus2.setViewParameters, type=Qt.UniqueConnection)
        self.viewerplus2.viewHasChanged[float, float, float].connect(self.viewerplus.setViewParameters, type=Qt.UniqueConnection)

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
        left = "{:5d}".format(int(round(x)))
        top = "{:5d}".format(int(round(y)))

        self.labelZoomInfo.setText(zoom)
        self.labelMouseLeftInfo.setText(left)
        self.labelMouseTopInfo.setText(top)


    def resetAll(self):

        if self.gridWidget is not None:
            self.gridWidget.close()
            self.gridWidget = None

        self.viewerplus.clear()
        self.viewerplus2.clear()
        self.mapviewer.clear()
        self.viewerplus.resetTools()
        self.viewerplus2.resetTools()
        self.resetToolbar()

        self.viewerplus.hideScalebar()

        # RE-INITIALIZATION

        self.help_widget = None
        self.mapWidget = None
        self.working_area_widget = None
        self.region_attributes_widget = None
        self.classifierWidget = None
        self.newDatasetWidget = None
        self.trainYourNetworkWidget = None
        self.datasetManagerWidget = None
        self.trainResultsWidget = None
        self.progress_bar = None
        self.classifier_name = None
        self.network_name = None
        self.dataset_train_info = None
        self.project = Project()
        self.project.loadDictionary(os.path.join(self.taglab_dir, self.default_dictionary))
        self.last_image_loaded = None
        self.activeviewer = None
        self.contextMenuPosition = None
        self.data_panel.clear()
        self.compare_panel.clear()
        self.comboboxSourceImage.clear()
        self.comboboxTargetImage.clear()
        self.resetPanelInfo()
        self.disableSplitScreen()
        self.layers_widget.setProject(self.project)

        # connect project with the panels
        self.connectProject()

    def resetToolbar(self):

        self.btnMove.setChecked(False)
        self.btnPoint.setChecked(False)
        self.btnAssign.setChecked(False)
        self.btnEditBorder.setChecked(False)
        self.btnCut.setChecked(False)
        self.btnFreehand.setChecked(False)
        self.btnWatershed.setChecked(False)
        self.btnBricksSegmentation.setChecked(False)
        self.btnRows.setChecked(False)
        self.btnRuler.setChecked(False)
        self.btnCreateCrack.setChecked(False)
        self.btnFourClicks.setChecked(False)
        self.btnRitm.setChecked(False)
        self.btnSam.setChecked(False)
        self.btnSamInteractive.setChecked(False)
        self.btnCreateGrid.setChecked(False)
        self.btnGrid.setChecked(False)
        self.btnMatch.setChecked(False)
        self.btnAutoClassification.setChecked(False)
        if self.scale_widget is not None:
            self.scale_widget.close()
            self.scale_widget = None

    @pyqtSlot()
    def resetSam(self):
        self.setTool("MOVE")

    def setTool(self, tool):
        tools = {
            "MOVE"         : ["Pan"          , self.btnMove],
            "PLACEANNPOINT": ["Place Annotation Point", self.btnPoint],
            "CREATECRACK"  : ["Crack"        , self.btnCreateCrack],
            "ASSIGN"       : ["Assign"       , self.btnAssign],
            "EDITBORDER"   : ["Edit Border"  , self.btnEditBorder],
            "CUT"          : ["Cut"          , self.btnCut],
            "FREEHAND"     : ["Freehand"     , self.btnFreehand],
            "WATERSHED"    : ["Watershed"    , self.btnWatershed],
            # "BRICKS"       : ["Bricks",        self.btnBricksSegmentation],
            "ROWS"         : ["Rows"         , self.btnRows],
            "RULER"        : ["Ruler"        , self.btnRuler],
            "FOURCLICKS"   : ["4-click"      , self.btnFourClicks],
            "MATCH"        : ["Match"        , self.btnMatch],
            "RITM"         : ["Ritm"         , self.btnRitm],
            "SAM"            : ["Sam", self.btnSam],
            "SAMINTERACTIVE" : ["Saminteractive", self.btnSamInteractive]
            # "SAM_NEW"    : ["Sam New", self.btnSam_new],
        }
        newtool = tools[tool]
        self.resetToolbar()
        self.viewerplus.setTool(tool)
        self.viewerplus2.setTool(tool)
        newtool[1].setChecked(True)
        logfile.info("[TOOL][" + tool + "] Tool activated")
        self.comboboxSourceImage.setEnabled(True)
        self.comboboxTargetImage.setEnabled(True)

        if tool == "MATCH":

            if self.split_screen_flag == False:
                self.enableSplitScreen()

            self.labelsdock.hide()
            self.datadock.show()
        else:
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
    def rows(self):
        """
        Activate the "rows" tool.
        """
        self.setTool("ROWS")

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

            ruler_tool = self.activeviewer.tools.tools["RULER"]
            genutils.disconnectSignal(ruler_tool, "measuretaken", ruler_tool.measuretaken)
            ruler_tool.measuretaken[float].connect(self.scale_widget.setMeasure)

            self.scale_widget.newscale[float].connect(self.updateMapScale)
            self.scale_widget.btnOk.clicked.connect(self.closeScaleWidget)
            self.scale_widget.closewidget.connect(self.closeScaleWidget)
        else:
            self.scale_widget.setScale(self.activeviewer.image.pixelSize())
            self.scale_widget.show()

    @pyqtSlot()
    def closeScaleWidget(self):
        self.scale_widget.close()
        self.scale_widget = None
        self.setTool("MOVE")

    @pyqtSlot()
    def fourClicks(self):
        """
        Activate the "Deep Extreme" tool. The segmentation is performed by selecting four points at the
        extreme of the corals and confirm the points by pressing SPACE.
        """
        self.setTool("FOURCLICKS")

    @pyqtSlot()
    def placeAnnPoint(self):

        self.setTool("PLACEANNPOINT")

    @pyqtSlot()
    def sam(self):
        """
        Activate the "Segmeent Everything" tool.
        """
        self.setTool("SAM")

    @pyqtSlot()
    def saminteractive(self):
        """
        Activate the "Segmeent Everything" tool.
        """
        self.setTool("SAMINTERACTIVE")

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
    #
    @pyqtSlot()
    def updatePanelInfoSelected(self):

        selected = self.data_panel.data_table.selectionModel().selectedRows()
        indexes = [self.data_panel.sortfilter.mapToSource(self.data_panel.sortfilter.index(index.row(), 0)) for index in selected]
        if len(indexes) == 0:
            self.resetPanelInfo()
            return

        index = indexes[0]
        row = self.data_panel.data.iloc[index.row()]
        id = row['Id']
        type = row['Type']
        if id < 0:
            print("OOOPS!")
            return

        if type == 'R':
            blob = self.viewerplus.annotations.blobById(id)
            self.updatePanelInfo(blob)
        else:
            point = self.viewerplus.annotations.pointById(id)
            self.updatePanelInfo(point)

    @pyqtSlot(Image)
    def setActiveImage(self, img):
        self.groupbox_blobpanel.setActiveImage(img, self.project)


    @pyqtSlot(Image, object, object)
    def updatePanelInfoAfterBlobChange(self, img, oldblob, newblob):
        if img == self.activeviewer.image:
            self.updatePanelInfo(newblob)
        else:
            self.resetPanelInfo()

    @pyqtSlot(Image, str, object)
    def updatePanelInfoAfterClassChange(self, img, class_name, blob_or_point):
        if img == self.activeviewer.image:
            self.updatePanelInfo(blob_or_point)
        else:
            self.resetPanelInfo()

    @pyqtSlot(Image, object)
    def updatePanelInfoAfterAddOperation(self, img, blob_or_point):
        if img == self.activeviewer.image:
            self.updatePanelInfo(blob_or_point)
        else:
            self.resetPanelInfo()

    def updatePanelInfo(self, blob_or_point):
        scale_factor = self.activeviewer.image.pixelSize()
        self.groupbox_blobpanel.update(blob_or_point, scale_factor)
        self.blob_with_info_displayed = blob_or_point

    @pyqtSlot()
    def resetPanelInfo(self):
        self.groupbox_blobpanel.clear()
        self.blob_with_info_displayed = None

    def deleteSelectedBlobs(self):
        if self.viewerplus.tools.tool == 'MATCH':
            self.deleteMatch()
        #disable delete blobs while creating new ones
        elif self.viewerplus.tools.tool == 'RITM' and self.viewerplus.tools.tools['RITM'].work_area_bbox[2] > 0:
            return False
        else:
            self.activeviewer.tools.edit_points.reset()
            self.activeviewer.deleteSelectedBlobs()
            logfile.info("[OP-DELETE] Selected blobs has been DELETED")

    #SELECTION
    def selectAll(self):
        """
        Select all blobs in the active viewer.
        """
        view = self.activeviewer
        if view is None:
            return
        view.selectAllBlobs()
        logfile.info("[OP-SELECT] All blobs have been selected.")

    def selectNone(self):
        """
        Deselect all blobs in the active viewer.
        """
        view = self.activeviewer
        if view is None:
            return
        view.selectNoneBlobs()
        logfile.info("[OP-SELECT] All blobs have been deselected.")

    def selectInvert(self):
        """
        Invert the selection of blobs in the active viewer.
        """
        view = self.activeviewer
        if view is None:
            return
        view.selectInverseBlobs()
        logfile.info("[OP-SELECT] Selection has been inverted.")

    def selectByClass(self):
        """
        Select blobs by class.
        """
        view = self.activeviewer
        if view is None:
            return
        label_name = self.labels_widget.getActiveLabelName()
        if label_name is None:
            return
        view.selectByClass(label_name)
        logfile.info("[OP-SELECT] Blobs of class '" + label_name + "' have been selected.")

    def selectByWorkingArea(self):
        """
        Select blobs by working area.
        """
        view = self.activeviewer
        if view is None:
            return
        wa = self.project.working_area
        if wa is None:
            return
        view.selectByWorkingArea(wa)
        logfile.info("[OP-SELECT] Blobs in the working area have been selected.")

    def selectByProperties(self):
        """
        Select blobs by properties.
        """
        view = self.activeviewer
        if view is None:
            return
        if self.project is None or len(self.project.images) == 0:
            return
        
        if not hasattr(self, "selectByProperties_widget"):  # in this way there is only one instance of the widget, that preserve the last values used
            self.selectByProperties_widget = QtSelectByPropertiesWidget(view, parent=self)
        self.selectByProperties_widget.setWindowModality(Qt.NonModal)
        self.selectByProperties_widget.show()
        logfile.info("[OP-SELECT] Blobs have been selected by properties.")

    #OPERATIONS

    def assignOperation(self):
        view = self.activeviewer
        if view is None:
            return
        for blob in view.selected_blobs:
            view.setBlobClass(blob, self.labels_widget.getActiveLabelName())
        for annpoint in view.selected_annpoints:
            view.setAnnPointClass(annpoint, self.labels_widget.getActiveLabelName())

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

            ref_dict = view.selected_blobs[0].data.copy()
            flag_different_attributes = False
            for blob in view.selected_blobs:
                if blob.data != ref_dict:
                    flag_different_attributes = True

            if flag_different_attributes:
                msgBox = QMessageBox()
                msgBox.setWindowTitle(self.TAGLAB_VERSION)
                msgBox.setText("The regions you are merging have different custom attributes. The resulting region will have empty fields.")
                msgBox.exec()
                ref_dict = {}

            #union returns a NEW blob
            union_blob = view.annotations.union(view.selected_blobs)

            if union_blob is None:
                logfile.info("[OP-MERGE] INVALID MERGE OVERLAPPED LABELS -> blobs are separated.")
            else:

                view.project.updateCorrespondences("REPLACE", view.image, [union_blob], view.selected_blobs, "")

                for blob in view.selected_blobs:
                    view.removeBlob(blob)
                    self.logBlobInfo(blob, "[OP-MERGE][BLOB-REMOVED]")

                union_blob.data = ref_dict
                view.addBlob(union_blob, selected=True)
                view.saveUndo()

                self.logBlobInfo(union_blob, "[OP-MERGE][BLOB-CREATED]")

            logfile.info("[OP-MERGE] MERGE OVERLAPPED LABELS operation ends.")

        else:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("You need to select at least <em>two</em> blobs for MERGE OVERLAPPED LABELS operation.")
            msgBox.exec()


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

                view.project.updateCorrespondences("REMOVE", None, selectedB, "")

                view.saveUndo()

            logfile.info("[OP-SUBTRACT] SUBTRACT LABELS operation ends.")

        else:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("You need to select <em>two</em> blobs for SUBTRACT operation.")
            msgBox.exec()

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
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("You need to select <em>two</em> regions for DIVIDE operation.")
            msgBox.exec()

    def createNegative(self):
        """
        create a negative region form selected blobs
        """
        view = self.activeviewer
        wa = self.project.working_area

        if view is None:
            return
        if wa is None:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("You need to set up a working are before using this feature.")
            msgBox.exec()
            return

        message = "[OP-CREATE] CREATE NEGATIVE REGIONS BEGIN operation begins "
        logfile.info(message)

        created_blobs = view.annotations.createNegative(view.selected_blobs,wa)

        if created_blobs:
            view.resetSelection()
            for blob in created_blobs:
                self.logBlobInfo(blob, "[OP-CREATENEGATIVE][BLOB-ADDED]")
                view.addBlob(blob, selected=True)

    def computeGeometricInfo(self):
        """
        Compute geometric information of the selected blobs.
        """
        view = self.activeviewer
        #wa = self.project.working_area

        if view is None:
            return
        
        if len(view.selected_blobs) == 0:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("You need to select at least one region for this operation.")
            msgBox.exec()
            return

        geometricInfo_widget = QtGeometricInfoWidget(view, parent = self)
        geometricInfo_widget.setWindowModality(Qt.ApplicationModal)
        geometricInfo_widget.show()

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
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("You need to select <em>two</em> regions for this operation.")
            msgBox.exec()


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
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("You need to select <em>two</em> regions for this operation.")
            msgBox.exec()


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

    def refineBorderAll(self):

        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                self.activeviewer.resetSelection()

                if len(self.activeviewer.image.annotations.seg_blobs) > 0:

                    self.activeviewer.selectAllBlobs()
                    self.refineBorder()


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
        Refine blob border - all the selected blobs are refined
        """

        view = self.activeviewer
        if view is None:
            return

        # padding mask to allow moving boundary
        padding = 35

        blobs = view.selected_blobs.copy()

        counter = 0
        for blob in blobs:

            if view.refine_original_mask is None:
                view.refine_grow = 0

            if view.refine_grow == 0:
                mask = blob.getMask()
                mask = np.pad(mask, (padding, padding), mode='constant', constant_values=(0, 0)).astype(np.ubyte)
                view.refine_original_blob = blob
                view.refine_original_mask = mask.copy()
                view.refine_original_bbox = blob.bbox.copy()
                bbox = blob.bbox.copy()
            else:
                mask = view.refine_original_mask.copy()
                bbox = view.refine_original_bbox.copy()

            bbox[0] -= padding    # top
            bbox[1] -= padding    # left
            bbox[2] += 2*padding  # width
            bbox[3] += 2*padding  # height

            img = genutils.cropQImage(view.img_map, bbox)
            img = genutils.qimageToNumpyArray(img)

            # USE DEPTH INFORMATION IF AVAILABLE
            # if view.depth_map is not None:
            #     depth = view.depth_map[bbox[0] : bbox[0]+bbox[3], bbox[1] : bbox[1] + bbox[2]]
            #     imgg = genutils.floatmapToQImage((depth - 4)*255)
            #     imgg.save("test.png")
            #
            #     genutils.cropQImage(self.depth_map, bbox)
            #     depth = genutils.qimageToNumpyArray(depth)
            # else:
            #     depth = None

            depth = None

            #try:
            #    from coraline.Coraline import segment
            #    segment(genutils.qimageToNumpyArray(img), mask, 0.0, conservative=0.07, grow=self.refine_grow, radius=30)

            #except Exception as e:
            #    msgBox = QMessageBox()
            #    msgBox.setText(str(e))
            #    msgBox.exec()
            #    return

            if view.tools.tool != 'EDITBORDER':
                view.tools.edit_points.last_editborder_points = None

            try:
                if view.tools.edit_points.last_blob != blob:
                    view.tools.edit_points.last_editborder_points = None

                created_blobs = view.annotations.refineBorder(bbox, blob, img, depth, mask, view.refine_grow, view.tools.edit_points.last_editborder_points)

                # copy attributes
                for created_blob in created_blobs:
                    created_blob.data = blob.data.copy()

                if len(created_blobs) == 0:
                    pass
                elif len(created_blobs) == 1:
                    view.updateBlob(blob, created_blobs[0], True, redraw=False)
                    view.project.updateCorrespondences("UPDATE", created_blobs, blob, "")
                else:
                    view.removeBlob(blob, redraw=False)
                    for created_blob in created_blobs:
                        view.addBlob(created_blob, selected=True, redraw=False)

                    # FIXME: this case can be managed in a better way.
                    view.project.updateCorrespondences("REMOVE", None, blob, "")

                view.saveUndo()

                counter += 1
                print(counter, "of", len(blobs), "refined")

            except Exception as e:
                print("FAILED!", e)
                pass

        view.scene.invalidate()


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


    def connectProject(self):

        # TODO: in the future the Project must be decoupled from the QImageViewerPlus through signals-slots

        ##### connect the project with panels (establishing UNIQUE connections)

        # label panel
        if self.labels_widget is not None:
            try:
                self.project.blobUpdated[Image, Blob, Blob].connect(self.labels_widget.updateBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.blobAdded[Image, Blob].connect(self.labels_widget.addBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.blobRemoved[Image, Blob].connect(self.labels_widget.removeBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.blobClassChanged[Image, str, Blob].connect(self.labels_widget.updateAnnClass, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.pointAdded[Image, Point].connect(self.labels_widget.addBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.pointRemoved[Image, Point].connect(self.labels_widget.removeBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.pointClassChanged[Image, str, Point].connect(self.labels_widget.updateAnnClass, type=Qt.UniqueConnection)
            except:
                pass

        # data panel
        if self.data_panel is not None:
            try:
                self.project.blobUpdated[Image, Blob, Blob].connect(self.data_panel.updateBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.blobAdded[Image, Blob].connect(self.data_panel.addBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.blobRemoved[Image, Blob].connect(self.data_panel.removeBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.blobClassChanged[Image, str, Blob].connect(self.data_panel.updateBlobClass, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.pointAdded[Image, Point].connect(self.data_panel.addBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.pointRemoved[Image, Point].connect(self.data_panel.removeBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.project.pointClassChanged[Image, str, Point].connect(self.data_panel.updatePointClass, type=Qt.UniqueConnection)
            except:
                pass

        # compare panel
        if self.compare_panel is not None:
            try:
                self.project.correspTableChanged.connect(self.compare_panel.updateData)
            except:
                pass

        # information panel
        try:
            self.project.blobUpdated[Image, Blob, Blob].connect(self.updatePanelInfoAfterBlobChange, type=Qt.UniqueConnection)
        except:
            pass

        try:
            self.project.blobAdded[Image, Blob].connect(self.updatePanelInfoAfterAddOperation, type=Qt.UniqueConnection)
        except:
            pass

        try:
            self.project.blobRemoved[Image, Blob].connect(self.resetPanelInfo, type=Qt.UniqueConnection)
        except:
            pass

        try:
            self.project.blobClassChanged[Image, str, Blob].connect(self.updatePanelInfoAfterClassChange, type=Qt.UniqueConnection)
        except:
            pass

        try:
            self.project.pointAdded[Image, Point].connect(self.updatePanelInfoAfterAddOperation, type=Qt.UniqueConnection)
        except:
            pass

        try:
            self.project.pointRemoved[Image, Point].connect(self.resetPanelInfo, type=Qt.UniqueConnection)
        except:
            pass

        try:
            self.project.pointClassChanged[Image, str, Point].connect(self.updatePanelInfoAfterClassChange, type=Qt.UniqueConnection)
        except:
            pass


        # viewerplus
        # NOTE: THIS IS DIRT but the only solution viable at the moment.
        self.project.blobClassChangedByGenet.connect(self.viewerplus.updateBlobClass, type=Qt.UniqueConnection)
        self.project.blobClassChangedByGenet.connect(self.viewerplus2.updateBlobClass, type=Qt.UniqueConnection)


    def updateAfterImport(self):
        """
        Update the viewer and the panels after an import operation.
        """

        # TODO: IMPORT/EXPORT OPERATION MUST BE MOVED FROM Annotation TO Project class. THEN,
        #       THIS METHOD WILL BE NOT NEEDED ANYMORE

        self.data_panel.setTable(self.activeviewer.image)
        self.labels_widget.setLabels(self.project, self.activeviewer.image)
        self.activeviewer.drawAllBlobs()
        self.activeviewer.drawAllPoints()
        self.activeviewer.updateVisibility()

    @pyqtSlot()
    def newProject(self):

        if self.project.filename is not None:

            box = QMessageBox()
            reply = box.question(self, self.TAGLAB_VERSION, "Do you want to save current project to " + self.project.filename,
                                 QMessageBox.Cancel | QMessageBox.Yes | QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.saveProject()

            if reply == QMessageBox.Cancel:
                return

        self.resetAll()
        self.setTool("MOVE")
        self.updateToolStatus()
        self.setProjectTitle("NONE")
        logfile.info("[PROJECT] A new project has been setup.")
        self.groupbox_blobpanel.region_attributes = self.project.region_attributes

    @pyqtSlot()
    def chooseSampling(self):
        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                if self.sample_point_widget is None:
                    self.disableSplitScreen()
                    self.sample_point_widget = QtSampleWidget(active_image=self.activeviewer.image,
                                                              working_area=self.project.working_area,
                                                              parent=self)
                    self.sample_point_widget.setWindowModality(Qt.NonModal)
                    self.sample_point_widget.show()
                    self.sample_point_widget.validchoices.connect(self.samplePointAnn)
                    self.sample_point_widget.closewidget.connect(self.closeSamplingWidget)

                    # NOTE: the disabling of area selection is obtain setting the MOVe tool, so it works also
                    #       if the ruler tool is active.

                    self.sample_point_widget.btn_select_area_SA.clicked.connect(self.enableAreaSelection)
                    self.sample_point_widget.btnCancel.clicked.connect(self.disableAreaSelection)
                    select_area_tool = self.activeviewer.tools.tools["SELECTAREA"]
                    select_area_tool.setAreaStyle("SAMPLING_AREA")

                    genutils.disconnectSignal(select_area_tool, "released", select_area_tool.released)
                    # when the mouse is released the area selection should not be disabled otherwise the selected area is reset.

                    genutils.disconnectSignal(select_area_tool, "rectChanged", select_area_tool.rectChanged)
                    select_area_tool.rectChanged[int, int, int, int].connect(self.sample_point_widget.updateSamplingArea)

                    self.sample_point_widget.btn_select_transect_T.clicked.connect(self.enableLineSelection)
                    ruler_tool = self.activeviewer.tools.tools["RULER"]
                    genutils.disconnectSignal(ruler_tool, "measuretakencoords", ruler_tool.measuretakencoords)
                    ruler_tool.measuretakencoords[float, float, float, float].connect(self.sample_point_widget.setTransect)
                else:
                    self.sample_point_widget.show()

    @pyqtSlot()
    def closeSamplingWidget(self):

        self.sample_point_widget.close()
        self.sample_point_widget = None
        self.setTool("MOVE")

    @pyqtSlot()
    def samplePointAnn(self):

        choosed_method = self.sample_point_widget.combo_method.currentText()
        choosed_point_number = int(self.sample_point_widget.edit_number.text())
        offset = int(float(self.sample_point_widget.edit_offset_px.text()))
        width = int(float(self.sample_point_widget.edit_width_px.text()))
        height = int(float(self.sample_point_widget.edit_height_px.text()))

        if self.project.working_area is not None:
           working_area = self.project.working_area
        else:
           working_area = [0, 0, self.activeviewer.image.width, self.activeviewer.image.height]

        active_image = self.activeviewer.image
        sampler = Sampler(choosed_method, choosed_point_number, offset, width, height)

        if self.sample_point_widget.radio_SA.isChecked():
            top = int(self.sample_point_widget.edit_top_SA.text())
            left = int(self.sample_point_widget.edit_left_SA.text())
            sampler.reset()
            sampler.generate(top, left)

        if self.sample_point_widget.radio_WA.isChecked():
            number_of_areas = int(self.sample_point_widget.edit_number_areas_WA.text())
            sampler.generateInsideWA(working_area, number_of_areas)

        if self.sample_point_widget.radio_T.isChecked():
            number_of_areas = int(self.sample_point_widget.edit_number_areas_T.text())
            transect = self.sample_point_widget.getTransect()
            method = self.sample_point_widget.combo_method_T.currentText()
            if method == "Equi-spaced":
                equi_spaced = True
            else:
                equi_spaced = False

            sampler.generateAlongTransect(transect, number_of_areas, equi_spaced)

        # add to the project the generated points
        for point in sampler.points:
            id = self.activeviewer.annotations.getFreePointId()
            newpoint = Point(int(point[0]), int(point[1]), 'Empty', id)
            self.project.addPoint(active_image, newpoint)

        # add to the project the sampling areas for visualization purposes
        self.project.addSamplingAreas(active_image, sampler.sampling_areas)

        self.activeviewer.drawAllPointsAnn()
        self.activeviewer.drawSamplingAreas()
        self.closeSamplingWidget()

    @pyqtSlot()
    def editProject(self):
        if self.edit_project_widget is None:

            self.edit_project_widget = QtProjectWidget(self.project, parent=self)
            self.edit_project_widget.setWindowModality(Qt.NonModal)
            self.edit_project_widget.show()

        else:
            # show it again
            self.edit_project_widget.project = self.project
            self.edit_project_widget.populateMapList()
            if self.edit_project_widget.isHidden():
                self.edit_project_widget.show()

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
    def closeProjectEditor(self):
        self.projectEditor = None

    @pyqtSlot()
    def openProjectEditor(self):
        if self.projectEditor is None:
            self.projectEditor = QtProjectEditor(self.project, parent=self)

        self.projectEditor.fillMaps()
        self.projectEditor.setWindowModality(Qt.WindowModal)
        self.projectEditor.show()
        self.projectEditor.closed.connect(self.closeProjectEditor)

    @pyqtSlot()
    def closeAlignmentTool(self):
        self.align_tool_widget = None
        self.updateToolStatus()
        self.updateImageSelectionMenu()
        self.updatePanels()

    @pyqtSlot()
    def openAlignmentTool(self):
        if len(self.project.images) < 2:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("At least two map are required to open the alignment tool")
            msgBox.exec()
            return

        if self.align_tool_widget is None:
            self.align_tool_widget = QtAlignmentToolWidget(self.taglab_dir, self.project, parent=self)
            self.align_tool_widget.setWindowModality(Qt.WindowModal)
            self.align_tool_widget.closed.connect(self.closeAlignmentTool)
            self.align_tool_widget.showMaximized()

    @pyqtSlot()
    def createDictionary(self):

        if self.dictionary_widget is None:
            self.dictionary_widget = QtDictionaryWidget(self.taglab_dir, self.project, parent = self)
            self.dictionary_widget.addlabel.connect(self.addLabelDictionary)
            self.dictionary_widget.updatelabel[str,list,str,list].connect(self.updateLabelDictionary)
            self.dictionary_widget.deletelabel[str].connect(self.deleteLabelfromDictionary)
            self.dictionary_widget.closewidget.connect(self.closeDictionaryWidget)
            self.dictionary_widget.show()

    @pyqtSlot()
    def closeDictionaryWidget(self):

        if self.dictionary_widget is not None:
            del self.dictionary_widget
            self.dictionary_widget = None

    @pyqtSlot()
    def editRegionAttributes(self):

        if self.region_attributes_widget is None:
            self.region_attributes_widget = QtRegionAttributesWidget(self.taglab_dir, self.project, parent = self)

        self.region_attributes_widget.show()
        self.region_attributes_widget.setWindowModality(Qt.WindowModal)
        self.region_attributes_widget.closed.connect(self.updateRegionAttributes)

    @pyqtSlot()
    def updateRegionAttributes(self):
        self.groupbox_blobpanel.updateRegionAttributes(self.project.region_attributes)

    @pyqtSlot()
    def addLabelDictionary(self):

        # NOTES:
        #
        #  - at the moment, two different labels can have the same color

        labels_list = self.dictionary_widget.labels

        # set the dictionary in the project
        self.project.setDictionaryFromListOfLabels(labels_list)

        # update labels widget
        self.updatePanels()

        # redraw all blobs
        if self.viewerplus is not None:
            if self.viewerplus.image is not None:
                self.viewerplus.drawAllBlobs()
        if self.viewerplus2 is not None:
            if self.viewerplus2.image is not None:
                self.viewerplus2.drawAllBlobs()

    @pyqtSlot(str,list,str,list)
    def updateLabelDictionary(self,oldname,oldcolor,newname,newcolor):

        labels_list = self.dictionary_widget.labels

        for label in labels_list:
            if label.fill == oldcolor:
                label.fill = newcolor

        # set the dictionary in the project
        self.project.setDictionaryFromListOfLabels(labels_list)

        if oldname == newname:
            # only the color of the label changed
            self.labels_widget.updateColor(newname, newcolor)
        else:
            # all the blobs need to be re-assigned in all the orthoimages
            for orthoimage in self.project.images:
                for blob in orthoimage.annotations.seg_blobs:
                    if blob.class_name == oldname:
                        blob.class_name = newname

                for point in orthoimage.annotations.annpoints:
                    if point.class_name == oldname:
                        point.class_name = newname

            self.activeviewer.drawAllBlobs()
            self.activeviewer.drawAllPoints()
            self.activeviewer.updateVisibility()

        # update labels widget
        self.updatePanels()

        # redraw all blobs
        if self.viewerplus is not None:
            if self.viewerplus.image is not None:
                self.viewerplus.drawAllBlobs()
        if self.viewerplus2 is not None:
            if self.viewerplus2.image is not None:
                self.viewerplus2.drawAllBlobs()

        self.groupbox_blobpanel.updateDictionary(self.project.labels)

    @pyqtSlot(str)
    def deleteLabelfromDictionary(self, labelname):

        labels_list = self.dictionary_widget.labels

        if self.activeviewer.image is not None:
            for blob in self.activeviewer.image.annotations.seg_blobs:
                if blob.class_name == labelname:
                    self.activeviewer.setBlobClass(blob, "Empty")

        # set the dictionary in the project
        self.project.setDictionaryFromListOfLabels(labels_list)

        # update labels widget
        self.updatePanels()

        # redraw all blobs
        if self.viewerplus is not None:
            if self.viewerplus.image is not None:
                self.viewerplus.drawAllBlobs()
        if self.viewerplus2 is not None:
            if self.viewerplus2.image is not None:
                self.viewerplus2.drawAllBlobs()

    def doNotUpdatePanels(self):

        self.update_panels_flag = False

    def doUpdatePanels(self):

        self.update_panels_flag = True

    def updateMapViewer(self):
        if self.mapviewer.isVisible():
            w = self.mapviewer.width()
            if self.activeviewer.thumb is None:
                self.activeviewer.thumb = self.activeviewer.pixmap.scaled(w, w, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.mapviewer.setPixmap(self.activeviewer.thumb)
            self.mapviewer.setOpacity(0.5)

    def updatePanels(self):
        """
        Update panels (labels, layers, data panel, compare panel and map viewer)
        """

        if self.update_panels_flag is False:
            return

        # update labels
        image = None
        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                image = self.activeviewer.image

        self.labels_widget.setLabels(self.project, image)

        # update layers
        if self.split_screen_flag is False:
            self.layers_widget.setProject(self.project)
            self.layers_widget.setImage(image)
        else:
            self.layers_widget.setProject(self.project)
            self.layers_widget.setImage(self.viewerplus.image, self.viewerplus2.image)

        if self.split_screen_flag is True:
            # update compare panel (only if it is visible)
            index1 = self.comboboxSourceImage.currentIndex()
            index2 = self.comboboxTargetImage.currentIndex()
            if self.compare_panel.isVisible():
                self.compare_panel.setTable(self.project, index1, index2)

        # update map viewer
        self.updateMapViewer()

        # update data panel
        self.updateDataPanel()

        self.updateImageSelectionMenu()

    # def moveMessageWindowEvent(self, event):
    #     super(TagLab, self).moveMessageWindowEvent(event)
    #     # Update the position of the message widget
    #     self.message_widget.move(self.x() + 200, self.y() + 200)

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
        self.layers_widget.setProject(self.project)
        self.mapWidget.close()
        self.showImage(image)

    @pyqtSlot()
    def updateToolStatus(self):

        for button in [self.btnMove, self.btnPoint, self.btnAssign, self.btnEditBorder, self.btnCut, self.btnFreehand,
                       self.btnCreateCrack, self.btnWatershed, self.btnBricksSegmentation, self.btnRows, self.btnRuler, self.btnFourClicks,
                       self.btnRitm,self.btnSam, self.btnAutoClassification, self.btnCreateGrid, self.btnGrid]:
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
        flag_image_name_changed = False

        try:
            image = self.image2update

            if image.map_px_to_mm_factor != self.mapWidget.data["px_to_mm"]:
                image.map_px_to_mm_factor = self.mapWidget.data["px_to_mm"]
                flag_pixel_size_changed = True

            if image.name != self.mapWidget.data['name']:
                flag_image_name_changed = True
                image_old_name = image.name

            image.name = self.mapWidget.data['name']
            image.id = self.mapWidget.data['name']
            image.acquisition_date = self.mapWidget.data['acquisition_date']
            rgb_filename = dir.relativeFilePath(self.mapWidget.data['rgb_filename'])
            dem_filename = dir.relativeFilePath(self.mapWidget.data['depth_filename'])

            rgb_channel = image.getChannel("RGB")
            dem_channel = image.getChannel("DEM")
            rgb_changed = rgb_channel.filename != rgb_filename

            if dem_channel is not None:
                dem_changed = dem_channel.filename != dem_filename
            else:
                if len(dem_filename) > 3:
                    dem_changed = True

            if len(rgb_filename) <= 3:
                raise ValueError("You need to specify an RGB map")
            elif rgb_changed:
                image.updateChannel(rgb_filename, "RGB")

            if len(dem_filename) > 3 and dem_changed:
                if dem_channel is None:
                    image.addChannel(dem_filename, "DEM")
                else:
                    image.updateChannel(dem_filename, "DEM")

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
            if rgb_changed:
                channel = image.getChannel(type) or image.getChannel("RGB")
                self.viewerplus.setChannel(channel)
            self.viewerplus.updateImageProperties()
            self.viewerplus.viewChanged()

        # check if the updated image is shown in the right viewer
        if self.viewerplus2.image == image:
            type = self.viewerplus2.channel.type
            if rgb_changed:
                channel = image.getChannel(type) or image.getChannel("RGB")
                self.viewerplus2.setChannel(channel)
            self.viewerplus2.updateImageProperties()
            self.viewerplus2.viewChanged()

        if flag_pixel_size_changed:

            # update area information in the data panel
            image.annotations.table_needs_update = True
            self.data_panel.updateTable(image.create_data_table())

            # update area information in the comparison panel
            area_mode = self.compare_panel.getAreaMode()

            if area_mode == "surface area":
                self.project.updatePixelSizeInCorrespondences(image, True)
            else:
                self.project.updatePixelSizeInCorrespondences(image, False)

            self.compare_panel.updateData()

            # update panel info
            self.updatePanelInfo(self.blob_with_info_displayed)

        if flag_image_name_changed:
            self.layers_widget.updateLayerName(image.name)
            self.project.updateTableKey(image_old_name, image.name)

        # update the comboboxes to select the images
        self.updateImageSelectionMenu()
        self.mapWidget.close()

    @pyqtSlot(Image)
    def showImage(self, image):
        """
        Show the image into the main view and update the map viewer accordingly.
        """

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.doNotUpdatePanels()
            self.viewerplus.clear()
            self.viewerplus.setProject(self.project)
            self.viewerplus.setImage(image)
            self.doUpdatePanels()

            self.last_image_loaded = image

            index = self.project.images.index(image)
            self.updateComboboxSourceImage(index)
            self.updateComboboxSourceImage(index)
            self.disableSplitScreen()
            self.setBlobVisualization()

            QApplication.restoreOverrideCursor()

        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Error loading map:" + str(e))
            msgBox.exec()

    def updateDataPanel(self):

        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                self.data_panel.setTable(self.activeviewer.image)
    
    @pyqtSlot(Layer, bool)
    def toggleLayer(self, layer, enable):
        if enable:
            layer.enable()
            self.viewerplus.drawLayer(layer)
        else:
            layer.disable()
            self.viewerplus.undrawLayer(layer)

    @pyqtSlot(str, Image, bool)
    def toggleAnnotations(self, annotation_type, image, enable):

        if self.viewerplus.image == image:
            self.viewerplus.toggleAnnotations(annotation_type, enable)

        if self.viewerplus2.image == image:
            self.viewerplus2.toggleAnnotations(annotation_type, enable)


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
            if not filename.endswith('.json'):
                filename += '.json'
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
            self.appendProject(filename)

        self.updateImageSelectionMenu()
        self.layers_widget.setProject(self.project)
        self.showImage(self.project.images[-1])


    @pyqtSlot()
    def help(self):

        if self.help_widget is None:
            self.help_widget = QtHelpWidget()

        self.help_widget.setWindowModality(Qt.WindowModal)
        self.help_widget.show()
        self.help_widget.setWindowOpacity(0.7)

    @pyqtSlot()
    def goToDocumentation(self):

        try:
            import webbrowser
            webbrowser.open_new('https://taglab.isti.cnr.it/docs')
        except:
            print("Fail to launch your web browser. Go to the following link: 'https://taglab.isti.cnr.it/docs'")
        
    #slot for the message_widget
    @pyqtSlot(str)
    def message(self, new_message):
                
        if new_message == "":
            if self.message_widget is not None:
                self.message_widget.close()
                self.message_widget = None
                
        else:
            if self.message_widget is not None:
                self.message_widget.close()
                self.message_widget = None


            self.message_widget = QtMessageWidget(self.viewerplus)                        
            # self.setParent(self.viewerplus)
            self.message_widget.show()
            
            self.message_widget.setMessage(new_message)

            #anchor message_widget window to the top left corner of the viewerplus
            viewerplus_position = self.viewerplus.mapToGlobal(QPoint(0, 0))
            self.message_widget.move(viewerplus_position.x(), viewerplus_position.y())


    @pyqtSlot()
    def selectWorkingArea(self):

        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                if self.working_area_widget is None:

                    self.disableSplitScreen()

                    # Add scaling from active image for conversions
                    if self.activeviewer.image.map_px_to_mm_factor:
                        scale = float(self.activeviewer.image.map_px_to_mm_factor)
                    else:
                        scale = None

                    self.working_area_widget = QtWorkingAreaWidget(self, scale=scale)
                    self.working_area_widget.btnChooseArea.clicked.connect(self.enableAreaSelection)
                    self.working_area_widget.closed.connect(self.disableAreaSelection)
                    self.working_area_widget.closed.connect(self.deleteWorkingAreaWidget)
                    self.working_area_widget.btnDelete.clicked.connect(self.deleteWorkingArea)
                    self.working_area_widget.btnApply.clicked.connect(self.setWorkingArea)
                    select_area_tool = self.activeviewer.tools.tools["SELECTAREA"]
                    select_area_tool.setAreaStyle("WORKING")

                    genutils.disconnectSignal(select_area_tool, "rectChanged", select_area_tool.rectChanged)
                    select_area_tool.rectChanged[int, int, int, int].connect(self.working_area_widget.updateArea)

                    self.working_area_widget.areaChanged[int, int, int, int].connect(select_area_tool.setSelectionRectangle)

                    if self.project.working_area is not None:
                        if len(self.project.working_area) == 4:
                            wa = self.project.working_area
                            self.working_area_widget.updateArea(wa[1], wa[0], wa[2], wa[3])

                self.working_area_widget.show()

    @pyqtSlot()
    def deleteWorkingAreaWidget(self):

        del self.working_area_widget
        self.working_area_widget = None

    @pyqtSlot()
    def setWorkingArea(self):
        # assign the working area to the project
        x, y, width, height = self.working_area_widget.getWorkingArea()
        if width != 0 and height != 0:
            # NOTE: working area format in Project is [top, left, width, height]
            self.project.working_area = [y, x, width, height]
            self.viewerplus.setProject(self.project)
            self.viewerplus2.setProject(self.project)

            self.viewerplus.drawWorkingArea()
            self.viewerplus2.drawWorkingArea()

            self.working_area_widget.close()
            self.deleteWorkingAreaWidget()
        else:
            box = QMessageBox(self.working_area_widget)
            box.setText("Please, select a valid working area")
            box.exec()
            return


    @pyqtSlot()
    def deleteWorkingArea(self):
        box = QMessageBox()
        reply = box.question(self.working_area_widget, self.TAGLAB_VERSION, "Are you sure to delete the Working Area?",
                             QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.activeviewer.undrawWorkingArea()
            self.project.working_area = None
            self.working_area_widget.deleteWorkingAreaValues()
            self.setTool("MOVE")

    @pyqtSlot()
    def enableAreaSelection(self):
        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                self.activeviewer.setTool("SELECTAREA")
                image = self.activeviewer.image
                self.activeviewer.tools.tools["SELECTAREA"].setImageSize(image.width, image.height)

    @pyqtSlot()
    def disableAreaSelection(self):
        self.setTool("MOVE")

    @pyqtSlot()
    def enableLineSelection(self):

        # Line selection is not available, the Ruler tool is used.
        self.setTool("RULER")

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

    def deleteDatasetManagerWidget(self):

        if self.datasetManagerWidget:
            self.datasetManagerWidget.close()
            del self.datasetManagerWidget
            self.datasetManagerWidget = None

    @pyqtSlot()
    def report(self):

        content = QLabel()
        content.setTextFormat(Qt.RichText)

        txt = "<b>{:s}</b> <p> If TagLab closes unexpectedly and you can reproduce the incriminated sequence of actions,"\
              " please, send us a report from" \
              "<a href='https://github.com/cnr-isti-vclab/TagLab/issues' style='color: white; font-weight: bold; text-decoration: none'>" \
              " Github</a>.</p>".format(self.TAGLAB_VERSION)

        content.setWordWrap(True)
        content.setMinimumWidth(500)
        content.setText(txt)
        content.setTextInteractionFlags(Qt.TextBrowserInteraction)
        content.setStyleSheet("QLabel {padding: 10px; }");
        content.setOpenExternalLinks(True)

        layout = QHBoxLayout()
        layout.addWidget(content)

        widget = QWidget(self)
        widget.setAutoFillBackground(True)
        widget.setStyleSheet("background-color: rgba(40,40,40,100); color: white")
        widget.setLayout(layout)
        widget.setWindowTitle("Report Issues")
        widget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        widget.show()

    @pyqtSlot()
    def about(self):

        icon = QLabel()

        # BIG taglab icon
        pxmap = QPixmap(os.path.join(os.path.join(self.taglab_dir, "icons"), "taglab240px.png"))
        pxmap = pxmap.scaledToWidth(160)
        icon.setPixmap(pxmap)
        icon.setStyleSheet("QLabel {padding: 5px; }");

        content = QLabel()
        content.setTextFormat(Qt.RichText)

        txt = "<b>{:s}</b> <p><a href='http://taglab.isti.cnr.it' style='color: white; font-weight: bold; text-decoration: none'>" \
              "TagLab</a> is an AI-empowered interactive annotation tool for rapidly labeling and analyzing time-series sets of orthoimages." \
              "TagLab is an ongoing project of " \
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

        filters = "Image (*.png *.jpg *.jpeg)"
        filename, _ = QFileDialog.getOpenFileName(self, "Input Label Map File", "", filters)
        if not filename:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        created_blobs = self.activeviewer.annotations.import_label_map(filename, self.project.labels, offset=[0,0],
                                                                       scale=[1.0, 1.0])
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
        self.shapefile_filename, _ = QFileDialog.getOpenFileName(self, "Import Shapefile", "", filters)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        if not self.shapefile_filename:
            QApplication.restoreOverrideCursor()
            return
        #read only attributes
        data = rasterops.read_attributes(self.shapefile_filename)
        QApplication.restoreOverrideCursor()

        self.attribute_widget = QtAttributeWidget(data)
        self.attribute_widget.show()
        self.attribute_widget.shapefilechoices[str, list, list].connect(self.readShapes)


    @pyqtSlot(str,list,list)
    def readShapes(self, shapetype, attributelist, classes_list):

        gf = self.activeviewer.image.georef_filename

        if shapetype == 'Labeled regions':

            for attribute in attributelist:
                if self.project.region_attributes.has(attribute['name']):
                    continue
                self.project.region_attributes.data.append(attribute)

            blob_list = rasterops.read_regions_geometry(self.shapefile_filename, gf)
            data = rasterops.read_attributes(self.shapefile_filename)
            genutils.setAttributes(self.project, data, blob_list)

            self.groupbox_blobpanel.updateRegionAttributes(self.project.region_attributes)

            for i in range(0, len(blob_list)):
                blob = blob_list[i]
                blob.class_name = classes_list[i]
                self.activeviewer.addBlob(blob, selected=False)
            self.activeviewer.saveUndo()

        elif shapetype == 'Sampling':
            shape_list = rasterops.read_geometry(self.shapefile_filename, gf)
            data = rasterops.read_attributes(self.shapefile_filename)

            layer = Layer("Sampling")
            basename = os.path.basename(self.shapefile_filename)
            layer.name = os.path.splitext(basename)[0]

            layer.shapes = shape_list
            self.activeviewer.image.layers.append(layer)

            #genutils.setAttributes(self.project, data, layer.shapes)

            self.activeviewer.drawAllLayers()

        elif shapetype == 'Other':
            shape_list = rasterops.read_geometry(self.shapefile_filename, gf)
            data = rasterops.read_attributes(self.shapefile_filename)

            layer = Layer("Other")
            basename = os.path.basename(self.shapefile_filename)
            layer.name = os.path.splitext(basename)[0]

            layer.shapes = shape_list
            self.activeviewer.image.layers.append(layer)

            #genutils.setAttributes(self.project, data, layer.shapes)

            self.activeviewer.drawAllLayers()

        self.layers_widget.setProject(self.project)
        self.layers_widget.setImage(self.activeviewer.image)
        self.shapefile_filename = ""


    @pyqtSlot()
    def exportAnnAsDataTable(self):

        if self.activeviewer.image is None:
            box = QMessageBox()
            box.setText("A map is needed to export labels. Load a map or a project.")
            box.exec()
            return

        self.export_widget = QtExportAnnAsTable(self)
        self.export_widget.setWindowModality(Qt.NonModal)
        self.export_widget.show()
        self.export_widget.mode[str].connect(self.exportTableMode)
        self.export_widget.btnOk.clicked.connect(self.closeExportWidget)
        self.export_widget.closewidget.connect(self.closeExportWidget)

    @pyqtSlot(str)
    def exportTableMode(self, choice):

        filters = "CSV (*.csv) ;; All Files (*)"
        filename, _ = QFileDialog.getSaveFileName(self, "Output file", self.activeviewer.image.name + ".csv", filters)
        imagename = os.path.basename(self.activeviewer.channel.filename)
        if filename:
            self.activeviewer.annotations.export_data_table(self.project, self.activeviewer.image, imagename, filename, choice)

            if self.export_widget is not None:
                msgBox = QMessageBox(self.export_widget)
            else:
                msgBox = QMessageBox(self)
            
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Data table exported successfully!")
            msgBox.exec()
            return


    @pyqtSlot()
    def closeExportWidget(self):

        self.export_widget = None
        self.setTool("MOVE")

    def importAnnPointsFromCoralNet(self):
        """
        Import points annotations from Coralnet.
        """

        if self.activeviewer:
            if not self.activeviewer.image:
                box = QMessageBox()
                box.setText("A loaded project is needed to import annotated points.")
                box.exec()
                return

        filters = "CSV (*.csv)"
        filename, _ = QFileDialog.getOpenFileName(self, "Open .CSV file", self.taglab_dir, filters)
        if filename:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.disableSplitScreen()
            self.activeviewer.annotations.openCoralNetCSV(filename, self.activeviewer.image.name)

            self.updateAfterImport()  # update viewer and panels

            QApplication.restoreOverrideCursor()

    def exportAnnPointsForCoralNet(self):
        """
        Export point annotations such that can be uploaded on CoralNet.
        """

        if self.activeviewer:
            if not self.activeviewer.image:
                box = QMessageBox()
                box.setText("A loaded project is needed to export annotated points.")
                box.exec()
                return

            folder_name = QFileDialog.getExistingDirectory(self, "Choose a Folder for the export", "")
            if folder_name:

                working_area = self.project.working_area

                # expand the working area to consider points inside it
                pad = 10

                top = working_area[0] - pad
                left = working_area[1] - pad
                right = left + working_area[2] + pad
                bottom = top + working_area[3] + pad

                orthoimage = self.viewerplus.image.getRGBChannel().qimage

                if top < 0:
                    top = 0

                if left < 0:
                    left = 0

                if right > orthoimage.width():
                    right = orthoimage.width()

                if bottom > orthoimage.height():
                    bottom = orthoimage.height()

                w = right - left
                h = bottom - top

                BASE_SIZE = 1000

                w_step = int(w / BASE_SIZE)
                h_step = int(h / BASE_SIZE)

                w_size = int(w / w_step) + 1
                h_size = int(h / h_step) + 1

                # dataframe containing all the annotated points
                df = None

                # save the tiles
                for j in range(h_step):
                    for i in range(w_step):
                        x1 = left + w_size * i
                        y1 = top + h_size * j
                        bbox = [y1, x1, w_size, h_size]

                        img_tile = genutils.cropQImage(orthoimage, bbox)

                        idx = i + j * w_step
                        filename = os.path.join(folder_name, self.viewerplus.image.name) + "_tile{:04d}_offx={:05d}_offy={:05d}.png".format(idx, x1, y1)
                        img_tile.save(filename)

                        df2 = self.viewerplus.image.annotations.export_annotation_points_inside_an_area(idx, filename, bbox)

                        if df is None:
                            df = df2
                        else:
                            df = pd.concat([df, df2], ignore_index=True)

                # save the metadata (annotated) points)
                filename = os.path.join(folder_name, self.viewerplus.image.name) + ".csv"
                df.to_csv(filename, sep=',', index=False)


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

                QApplication.setOverrideCursor(Qt.WaitCursor)

                size = QSize(self.activeviewer.image.width, self.activeviewer.image.height)
                self.activeviewer.annotations.export_image_data_for_Scripps(size, filename, self.project)

                QApplication.restoreOverrideCursor()

                msgBox = QMessageBox(self)
                msgBox.setWindowTitle(self.TAGLAB_VERSION)
                msgBox.setText("Map exported successfully!")
                msgBox.exec()


    @pyqtSlot()
    def exportHistogramFromAnn(self):

        if self.activeviewer is not None:

            histo_widget = QtHistogramWidget(self.activeviewer.annotations, self.project.labels,
                                             self.activeviewer.image.pixelSize(),
                                             self.activeviewer.image.acquisition_date, self.project.working_area, self)
            histo_widget.setWindowModality(Qt.WindowModal)
            histo_widget.show()

    @pyqtSlot()
    def exportAnnAsShapefiles(self):

        if self.activeviewer is None:
            return

        if self.activeviewer.image is not None:
            if self.activeviewer.image.georef_filename == "":
                box = QMessageBox()
                box.setText("Georeferencing is not available.")
                box.exec()
                return

        filters = "SHP (*.shp)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Save Shapefile as", self.taglab_dir, filters)

        if output_filename:
            blobs = self.activeviewer.annotations.seg_blobs
            gf = self.activeviewer.image.georef_filename
            rasterops.write_shapefile(self.project, self.activeviewer.image, blobs, gf, output_filename)

            msgBox = QMessageBox(self)
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Shapefile exported successfully!")
            msgBox.exec()
            return

    @pyqtSlot()
    def exportAnnAsDXF(self):
        # Check if activeviewer is set and contains necessary data
        if self.activeviewer is None:
            return

        if self.activeviewer.image is not None:
            # Show the DXF export options dialog
            options_dialog = QtDXFExportOptions(self)
            if hasattr(self.activeviewer.image, 'georef_filename') and self.activeviewer.image.georef_filename:
                options_dialog.enable_georeferencing(True)
            if options_dialog.exec_() == QDialog.Accepted:
            # options_dialog.exec_()

                # Retrieve the selected options
                export_all_blobs = options_dialog.blobs_group.checkedButton().text() == "All Regions"
                use_georef = options_dialog.georef_checkbox.isChecked()
                export_grid = options_dialog.grid_checkbox.isChecked()
                use_full_name = options_dialog.class_name_group.checkedButton().text() == "Full Label Names"
                shortened_length = options_dialog.shortened_length_spinbox.value()

                # Open a file dialog to select the output file
                filters = "DXF (*.dxf)"
                output_filename, _ = QFileDialog.getSaveFileName(self, "Save DXF File As", self.taglab_dir, filters)
                if not output_filename.endswith(".dxf"):
                    output_filename = output_filename + ".dxf"
                print(output_filename)

                if output_filename:
                    # Create a new DXF document
                    doc = ezdxf.new()
                    msp = doc.modelspace()

                    try:
                        # Check if georeferencing information is available and process accordingly
                        georef = None
                        text_height_scale = 1.0
                        if use_georef and hasattr(self.activeviewer.image, 'georef_filename') and self.activeviewer.image.georef_filename:
                            georef, transform = rasterops.load_georef(self.activeviewer.image.georef_filename)
                            text_height_scale = max(abs(transform.a), abs(transform.e))

                        # Determine which blobs to export
                        if export_all_blobs:
                            exported_blobs = self.activeviewer.annotations.seg_blobs
                        else:
                            exported_blobs = []
                            for to_export in self.activeviewer.annotations.seg_blobs:
                                if self.viewerplus.project.isLabelVisible(to_export.class_name):
                                    exported_blobs.append(to_export)
                                

                        # Add the outline of the map or working area
                        if self.project.working_area is None:
                            map_outline = [
                                (0, 0),
                                (self.activeviewer.image.width, 0),
                                (self.activeviewer.image.width, self.activeviewer.image.height),
                                (0, self.activeviewer.image.height),
                                (0, 0)
                            ]
                        else:
                            map_outline = [
                                (self.project.working_area[1], self.project.working_area[0]),
                                (self.project.working_area[1] + self.project.working_area[2], self.project.working_area[0]),
                                (self.project.working_area[1] + self.project.working_area[2], self.project.working_area[0] + self.project.working_area[3]),
                                (self.project.working_area[1], self.project.working_area[0] + self.project.working_area[3]),
                                (self.project.working_area[1], self.project.working_area[0])
                            ]

                        if georef:
                            map_outline = [transform * (x, y) for x, y in map_outline]

                        msp.add_lwpolyline(
                            map_outline,
                            close=True,
                            dxfattribs={'layer': '0'}
                        )

                        # Add blobs and grid (if selected)
                        for blob in exported_blobs:
                            # if self.viewerplus.project.isLabelVisible(blob.class_name):
                            layer_name = blob.class_name
                            col = self.project.labels[blob.class_name].fill
                            color_code = ezdxf.colors.rgb2int(col)

                            if not doc.layers.has_entry(layer_name):
                                doc.layers.new(name=layer_name, dxfattribs={'true_color': color_code})

                            if georef:
                                points = [transform * (x, y) for x, y in blob.contour]
                            else:
                                points = [(x, self.activeviewer.image.height - y) for x, y in blob.contour]

                            if points:
                                msp.add_lwpolyline(
                                    points,
                                    close=True,
                                    dxfattribs={'layer': layer_name}
                                )

                            for inner_contour in blob.inner_contours:
                                if georef:
                                    inner_points = [transform * (x, y) for x, y in inner_contour]
                                else:
                                    inner_points = [(x, self.activeviewer.image.height - y) for x, y in inner_contour]

                                if inner_points:
                                    msp.add_lwpolyline(inner_points, close=True, dxfattribs={'layer': layer_name})

                            if blob.class_name and blob.class_name != "Empty":
                                # class_name = blob.class_name[:5] if len(blob.class_name) > 5 else blob.class_name
                                if use_full_name:
                                    class_name = blob.class_name
                                else:
                                    class_name = blob.class_name[:shortened_length]
                                x, y = blob.centroid
                                if georef:
                                    x, y = transform * (x, y)
                                else:
                                    y = self.activeviewer.image.height - y
                                msp.add_text(
                                    class_name, height=text_height_scale * 22.0,
                                    dxfattribs={'layer': layer_name}
                                ).set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)

                        if export_grid:                        
                            if self.activeviewer.image.grid is not None:
                                print("grid present")
                                grid = self.activeviewer.image.grid
                                grid_layer_name = "Grid"
                                
                                # Create a new layer for the grid if it doesn't exist
                                if not doc.layers.has_entry(grid_layer_name):
                                    doc.layers.new(name=grid_layer_name, dxfattribs={'color': 0})  # Black color for the grid
                                
                                # Get grid dimensions
                                cell_width = grid.width / grid.ncol
                                cell_height = grid.height / grid.nrow

                                # Iterate through the grid cells
                                for r in range(grid.nrow):
                                    for c in range(grid.ncol):
                                        value = grid.cell_values[r, c]
                                        if value > 0:  # Only draw cells with a state > 0
                                            x1 = grid.offx + c * cell_width
                                            y1 = grid.offy + r * cell_height
                                            x2 = x1 + cell_width
                                            y2 = y1 + cell_height

                                            if georef:
                                                # Transform the coordinates if georeferenced
                                                p1 = transform * (x1, y1)
                                                p2 = transform * (x2, y1)
                                                p3 = transform * (x2, y2)
                                                p4 = transform * (x1, y2)
                                            else:
                                                # Invert Y-axis if not georeferenced
                                                height = self.activeviewer.image.height
                                                p1 = (x1, height - y1)
                                                p2 = (x2, height - y1)
                                                p3 = (x2, height - y2)
                                                p4 = (x1, height - y2)

                                            # Add the cell as a polyline
                                            msp.add_lwpolyline(
                                                [p1, p2, p3, p4, p1],  # Close the polyline
                                                close=True,
                                                dxfattribs={'layer': grid_layer_name}
                                            )

                                # Add notes to the DXF file
                                for note in grid.notes:
                                    x, y, text = note["x"], note["y"], note["txt"]
                                    if georef:
                                        x, y = transform * (x, y)
                                    else:
                                        y = self.activeviewer.image.height - y
                                    msp.add_text(
                                        text, height=10.0,  # Adjust text height as needed
                                        dxfattribs={'layer': grid_layer_name}
                                    ).set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)
                                
                            else:
                                print("grid NOT present")


                        # Save the DXF file
                        doc.saveas(output_filename)

                        # Show a confirmation message box
                        msgBox = QMessageBox(self)
                        msgBox.setWindowTitle("Export Successful")
                        msgBox.setText("DXF file exported successfully!")
                        msgBox.exec()
                        return
                    except Exception as e:
                        msgBox = QMessageBox(self)
                        msgBox.setWindowTitle("Export Failed")
                        msgBox.setText("Error exporting DXF file: " + str(e))
                        msgBox.exec()
                        return
            else:
                return

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

        filters = "Tiff (*.tif *.tiff) ;; All Files (*)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Output GeoTiff", "", filters)

        if output_filename:

            QApplication.setOverrideCursor(Qt.WaitCursor)

            size = QSize(self.activeviewer.image.width, self.activeviewer.image.height)
            label_map_img = self.activeviewer.annotations.create_label_map(size, self.project.labels, None)
            label_map_np = genutils.qimageToNumpyArray(label_map_img)
            georef_filename = self.activeviewer.image.georef_filename
            outfilename = os.path.splitext(output_filename)[0]
            rasterops.saveGeorefLabelMap(label_map_np, georef_filename, self.project.working_area, outfilename)

            QApplication.restoreOverrideCursor()

            msgBox = QMessageBox(self)
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("GeoTiff exported successfully!")
            msgBox.exec()

    pyqtSlot()
    def exportGeoRefImage(self):

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

        filters = "Tiff (*.tif *.tiff) ;; All Files (*)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Output GeoTiff", "", filters)

        if output_filename:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            myimage_np = genutils.qimageToNumpyArray(self.activeviewer.image.getRGBChannel().qimage)
            georef_filename = self.activeviewer.image.georef_filename
            outfilename = os.path.splitext(output_filename)[0]
            rasterops.saveGeorefLabelMap(myimage_np, georef_filename, self.project.working_area, outfilename)

            QApplication.restoreOverrideCursor()

            msgBox = QMessageBox(self)
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("GeoTiff exported successfully!")
            msgBox.exec()


    @pyqtSlot()
    def exportAnnAsTrainingDataset(self):

        if self.activeviewer is not None:
            if self.activeviewer.image is not None:
                if self.newDatasetWidget is None:

                    if not self.activeviewer.image.export_dataset_area:
                        self.activeviewer.image.export_dataset_area = [0, 0 , self.activeviewer.img_map.width(), self.activeviewer.img_map.height()]

                    annotations = self.activeviewer.annotations
                    self.newDatasetWidget = QtNewDatasetWidget(self.activeviewer.image.export_dataset_area, parent=self)
                    self.newDatasetWidget.setWindowModality(Qt.NonModal)
                    self.newDatasetWidget.btnChooseExportArea.clicked.connect(self.enableAreaSelection)
                    self.newDatasetWidget.btnExport.clicked.connect(self.exportNewDataset)
                    self.newDatasetWidget.btnCancel.clicked.connect(self.disableAreaSelection)
                    self.newDatasetWidget.closed.connect(self.disableAreaSelection)
                    select_area_tool = self.activeviewer.tools.tools["SELECTAREA"]
                    select_area_tool.setAreaStyle("EXPORT_DATASET")
                    genutils.disconnectSignal(select_area_tool, "rectChanged", select_area_tool.rectChanged)
                    select_area_tool.rectChanged[int, int, int, int].connect(self.updateExportDatasetArea)

                self.newDatasetWidget.show()

    @pyqtSlot(int, int, int, int)
    def updateExportDatasetArea(self, x, y, width, height):

        # NOTE: area is in the form of [top, left, width, height]
        self.newDatasetWidget.setAreaToExport(y, x, width, height)


    @pyqtSlot()
    def exportNewDataset(self):

        if self.activeviewer is not None and self.newDatasetWidget is not None:

            if self.newDatasetWidget.getDatasetFolder() == "":
                msgBox = QMessageBox()
                msgBox.setWindowTitle(self.TAGLAB_VERSION)
                msgBox.setText("Please, choose a folder to export the dataset.")
                msgBox.exec()
                return

            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.setupProgressBar()

            self.progress_bar.hidePerc()
            self.progress_bar.setMessage("Export new dataset (setup)..")
            QApplication.processEvents()

            self.activeviewer.image.export_dataset_area = self.newDatasetWidget.getAreaToExport()

            index = self.comboboxSourceImage.currentIndex()
            current_image = self.project.images[index]

            new_dataset = NewDataset(self.activeviewer.img_map, self.project.labels, current_image,
                                     tile_size=1024, step=512, data_format=self.newDatasetWidget.comboDataFormat.currentText())

            target_classes = training.createTargetClasses(self.activeviewer.annotations)

            new_dataset.createLabelImage(self.project.labels)
            new_dataset.convertColorsToLabels(target_classes, self.project.labels)
            new_dataset.computeFrequencies(target_classes)
            target_pixel_size = self.newDatasetWidget.getTargetScale()

            area_to_export = self.activeviewer.image.export_dataset_area.copy()

            check_size = new_dataset.exportAreaCropAndRescale(self.activeviewer.image.pixelSize(), target_pixel_size,
                                                              area_to_export)

            if check_size is False:
                msgBox = QMessageBox()
                msgBox.setWindowTitle(self.TAGLAB_VERSION)
                msgBox.setText("The image to export is too big. Check the target pixel size.")
                msgBox.exec()
                self.deleteProgressBar()
                self.deleteNewDatasetWidget()
                self.disableAreaSelection()
                QApplication.restoreOverrideCursor()
                return

            # create training, validation and test areas

            self.progress_bar.setMessage("Select area and cut tiles (it could take long)..")
            self.progress_bar.setProgress(25.0)
            QApplication.processEvents()

            mode = self.newDatasetWidget.getSplitMode()
            new_dataset.setupAreas(mode.upper(), target_classes)

            # cut the tiles
            #flag_oversampling = self.newDatasetWidget.checkOversampling.isChecked()
            flag_oversampling = False  # disable for now

            self.progress_bar.setProgress(50.0)
            QApplication.processEvents()
            #
            # if flag_oversampling is True:
            #     # FIXME: oversampling requires to be rewritten taking into account that target_classes is a dictionary now.
            #     class_to_sample, radii = new_dataset.computeRadii(target_classes)
            #     new_dataset.cut_tiles(regular=False, oversampling=True, classes_to_sample=class_to_sample, radii=radii)
            # else:
            new_dataset.cut_tiles(regular=True, oversampling=False, classes_to_sample=None, radii=None)

            flag_save = self.newDatasetWidget.checkShowTiles.isChecked()
            if flag_save:
                new_dataset.save_samples("tiles_cutted.png", show_tiles=True, show_areas=True, radii=None)

            # export the tiles
            self.progress_bar.setMessage("Export tiles (it could take long)..")
            self.progress_bar.setProgress(75.0)
            QApplication.processEvents()

            basename = self.newDatasetWidget.getDatasetFolder()
            tilename = os.path.splitext(self.activeviewer.image.name)[0]
            new_dataset.export_tiles(basename=basename, tilename=tilename)

            # save the target pixel size
            target_pixel_size_file = os.path.join(basename, "target-pixel-size.txt")
            fl = open(target_pixel_size_file, "w")
            fl.write(str(target_pixel_size))
            fl.close()

            self.deleteProgressBar()
            self.deleteNewDatasetWidget()

            self.disableAreaSelection()

            QApplication.restoreOverrideCursor()

    @pyqtSlot()
    def trainNewNetwork(self):

        dataset_folder = self.trainYourNetworkWidget.getDatasetFolder()

        self.setupProgressBar()
        self.progress_bar.hidePerc()
        self.progress_bar.setMessage("Dataset setup..")
        QApplication.processEvents()

        # CLASSES TO RECOGNIZE (label name - label code)
        labels_folder = os.path.join(dataset_folder, "training")
        labels_folder = os.path.join(labels_folder, "labels")

        target_classes = self.trainYourNetworkWidget.getTargetClasses()
        num_classes = len(target_classes)

        # GO TRAINING GO...
        nepochs = self.trainYourNetworkWidget.getEpochs()
        nepochs_stage1, nepochs_stage2, nepochs_stage3 = self.trainYourNetworkWidget.getEpochsPerStage()
        training_mode = self.trainYourNetworkWidget.getTrainingMode()
        optimizer_name = self.trainYourNetworkWidget.getOptimizer().upper()
        lr = self.trainYourNetworkWidget.getLR()
        L2 = self.trainYourNetworkWidget.getWeightDecay()
        batch_size = self.trainYourNetworkWidget.getBatchSize()

        if training_mode == "Preset 1":
            freeze_strategy = False
        else:
            freeze_strategy = True

        classifier_name = self.trainYourNetworkWidget.editNetworkName.text()
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
                                                                                          epochs=nepochs, epochs_stage1=nepochs_stage1, epochs_stage2=nepochs_stage2, batch_sz=batch_size, batch_mult=4, validation_frequency=2,
                                                                                          loss_to_use="FOCAL_TVERSKY", epochs_switch=0, epochs_transition=0,
                                                                                          learning_rate=lr, L2_penalty=L2, tversky_alpha=0.6, tversky_gamma=0.75,
                                                                                          optimiz=optimizer_name, freeze_strategy=freeze_strategy, flag_shuffle=True, flag_training_accuracy=False,
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

        metrics = training.testNetwork(images_dir_test, labels_dir_test, labels_dictionary=self.project.labels,
                                       target_classes=dataset_train_info.dict_target, dataset_train=dataset_train_info,
                                       network_filename=network_filename, output_folder=output_folder,
                                       progress=self.progress_bar)

        # info about the classifier created
        self.classifier_name = classifier_name
        self.network_name = network_name
        self.dataset_train_info = dataset_train_info

        self.deleteProgressBar()
        self.deleteTrainYourNetworkWidget()

        self.trainResultsWidget = QtTrainingResultsWidget(dataset_train_info.dict_target,
                                                          metrics, train_loss_values, val_loss_values,
                                                          images_dir_test, labels_dir_test, output_folder,
                                                          parent=self)
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
        new_classifier["Weights"] = self.network_name
        new_classifier["Num. Classes"] = self.dataset_train_info.num_classes
        new_classifier["Classes"] = self.dataset_train_info.dict_target

        # scale
        target_pixel_size_file = os.path.join(self.trainResultsWidget.dataset_folder, "target-pixel-size.txt")
        fl = open(target_pixel_size_file, "r")
        line = fl.readline()
        fl.close()
        target_pixel_size = float(line)
        new_classifier["Scale"] = target_pixel_size

        new_classifier["Average Norm."] = list(self.dataset_train_info.dataset_average)

        # update config file
        self.available_classifiers.append(new_classifier)
        newconfig = dict()
        newconfig["Available Classifiers"] = self.available_classifiers
        str = json.dumps(newconfig)
        newconfig_filename = os.path.join(self.taglab_dir, "config.json")
        f = open(newconfig_filename, "w")
        f.write(str)
        f.close()

        self.trainResultsWidget.close()
        self.trainResultsWidget = None


    @pyqtSlot()
    def trainYourNetwork(self):

        if self.trainYourNetworkWidget is None:
            self.trainYourNetworkWidget = QtTYNWidget(self.project.labels, self.TAGLAB_VERSION, parent=self)
            self.trainYourNetworkWidget.setWindowModality(Qt.WindowModal)
            self.trainYourNetworkWidget.launchTraining.connect(self.trainNewNetwork)
        self.trainYourNetworkWidget.show()


    @pyqtSlot()
    def openDatasetManager(self):

        if self.datasetManagerWidget is None:
            self.datasetManagerWidget = QtDatasetManagerWidget(self.project.labels, self.TAGLAB_VERSION, parent=self)
            self.datasetManagerWidget.setWindowModality(Qt.WindowModal)
            # self.trainYourNetworkWidget.launchTraining.connect(self.trainNewNetwork)
        self.datasetManagerWidget.show()

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

        filters = " TIFF (*.tif *.tiff)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Save raster as", self.taglab_dir, filters)

        if output_filename:

            QApplication.setOverrideCursor(Qt.WaitCursor)

            if self.project.working_area is None:
                blobs = self.activeviewer.annotations.seg_blobs
            else:
                blobs = self.activeviewer.annotations.calculate_inner_blobs(self.project.working_area)

            gf = self.activeviewer.image.georef_filename
            rasterops.saveClippedTiff(input_tiff, blobs, gf, output_filename)

            QApplication.restoreOverrideCursor()

    @pyqtSlot()
    def importViscorePointAnn(self):
        """
        Imports all point annotations to current map from a CSV file in from Viscore format.
        Asks the user for the scale, which should be the same as the orthomosaic...?
        """
        try:
            self.importViscorePoints = QtImportViscoreWidget(self)
            self.importViscorePoints.show()
        except Exception as e:
            print(f"{e}")

    @pyqtSlot()
    def importCoralNetPointAnn(self):
        """
        Imports all point annotations to current map from a CSV file in CoralNet format.
        This will automatically check the Name column and import only point annotations for it
        (either in the original orthomosaic or tile coordinate space). Excess information not
        important to CoralNet or TagLab are not imported (see Annotations.py)
        """
        box = QMessageBox()

        filters = "CSV (*.csv)"
        file_name, _ = QFileDialog.getOpenFileName(self, "Open A .CSV File", self.taglab_dir, filters)

        if os.path.exists(file_name):
            # Turn off split screen
            self.disableSplitScreen()
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)

                # Open the file, and draw all the points on viewer
                imported_points = self.activeviewer.annotations.importCoralNetCSVAnn(file_name,
                                                                                     self.project.labels,
                                                                                     self.activeviewer.image)

                self.labels_widget.setLabels(self.project, self.activeviewer.image)
                self.groupbox_blobpanel.blockSignals(True)

                for point in imported_points:
                    self.project.addPoint(self.activeviewer.image, point, notify=True)

                self.groupbox_blobpanel.blockSignals(False)
                self.activeviewer.drawAllPointsAnn()

                box.setText(f"Point annotations imported successfully!")
                box.exec()

            except Exception as e:
                box.setText(f"File provided not in CoralNet format! {e}")
                box.exec()
        else:
            box.setText("File path provided is not valid!")
            box.exec()

        QApplication.restoreOverrideCursor()

    @pyqtSlot()
    def exportCoralNetPointAnn(self):
        """
        Exports just a CSV in CoralNet format for all the point annotations in the
        user specified work area (or orthomosaic). The CSV will contain all information
        within the point's data attribute.
        """
        box = QMessageBox()

        # Default output folder
        output_dir = os.path.dirname(os.path.realpath(__file__))
        output_dir = f"{output_dir}\\temp"
        os.makedirs(output_dir, exist_ok=True)

        # User specifies output folder
        folder_name = QFileDialog.getExistingDirectory(self, "Choose a Folder for the export", output_dir)

        if not folder_name:
            return

        # Force split screen off
        self.disableSplitScreen()

        # Get the current image, and the points for it
        channel = self.activeviewer.image.getRGBChannel()
        annotations = self.activeviewer.annotations
        # TODO change how the working / sample area is passed
        #  to the export function (maybe via loop?) The export
        #   function expects a bbox, and will tile if larger
        #   than 8000.
        # Get the working area (if none, whole ortho is used)
        working_area = self.project.working_area

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            # Save all the annotations to a CSV file in the directory chosen
            csv_file = self.activeviewer.annotations.exportCoralNetCSVAnn(folder_name,
                                                                          channel,
                                                                          annotations,
                                                                          working_area)

            box.setText(f"Exported data to {os.path.basename(csv_file)}")
            box.exec()

        except Exception as e:
            box.setText(f"Failed to export data to CoralNet format! {e}")
            box.exec()

        QApplication.restoreOverrideCursor()

    @pyqtSlot()
    def exportCoralNetPointData(self):
        """
        Opens the ExportCoralNetDataWidget in a new window.
        """
        try:
            self.exportCoralNetData = QtExportCoralNetDataWidget(self)
            self.exportCoralNetData.show()
        except Exception as e:
            print(f"{e}")

    @pyqtSlot()
    def openCoralNetToolbox(self):
        """
        Opens the CoralNetToolbox Widget in a new window.
        """
        try:
            self.coralNetToolbox = QtCoralNetToolboxWidget(self)
            self.coralNetToolbox.show()
        except Exception as e:
            print(f"{e}")

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
        # TODO check if loadProject actually works!
        try:
            self.project = loadProject(self.taglab_dir, filename, self.default_dictionary)
            self.connectProject()
        except Exception as e:
            box = QMessageBox()
            box.setWindowTitle('Failed loading the project')
            box.setText("Could not load the file " + filename + "\n" + str(e))
            box.exec()
            return

        QApplication.restoreOverrideCursor()

        self.setProjectTitle(self.project.filename)

        self.layers_widget.setProject(self.project)
        self.groupbox_blobpanel.updateRegionAttributes(self.project.region_attributes)

        # show the first map present in project
        if len(self.project.images) > 0:
            image = self.project.images[0]
            self.showImage(image)
            self.move()

        self.updateImageSelectionMenu()

        if self.timer is None:
            self.activateAutosave()

        message = "[PROJECT] The project " + self.project.filename + " has been loaded."
        logfile.info(message)
        self.updateToolStatus()
        self.groupbox_blobpanel.updateDictionary(self.project.labels)


    def appendProject(self, filename):
        """
        Append the annotated images of a previously saved project to the current one.
        """

        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            project_to_append = loadProject(self.taglab_dir, filename, self.project.labels)

        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setText("The json project contains an error:\n {0}\n\nPlease contact us.".format(str(e)))
            msgBox.exec()
            return

        # append the annotated images to the current ones
        for annotated_image in project_to_append.images:
            self.project.addNewImage(annotated_image)

        QApplication.restoreOverrideCursor()

        msgBox = QMessageBox()
        msgBox.setWindowTitle(self.TAGLAB_VERSION)
        msgBox.setText("The annotations of the given project has been successfully loaded.")
        msgBox.exec()

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

        msgBox = QMessageBox()
        msgBox.setWindowTitle(self.TAGLAB_VERSION)
        msgBox.setText("Current project has been successfully saved.")
        msgBox.exec()

        message = "[PROJECT] The project " + self.project.filename + " has been saved."
        logfile.info(message)


    #REFACTOR networks should be moved to a new class
    def resetNetworks(self):

        torch.cuda.empty_cache()

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
            self.resetToolbar()
            self.btnAutoClassification.setChecked(True)

            if self.classifierWidget is None:
                self.classifierWidget = QtClassifierWidget(self.available_classifiers, parent=self)
                self.classifierWidget.setAttribute(Qt.WA_DeleteOnClose)
                self.classifierWidget.btnApply.clicked.connect(self.applyClassifier)
                self.classifierWidget.setWindowModality(Qt.NonModal)
                self.classifierWidget.show()
                self.classifierWidget.btnChooseArea.clicked.connect(self.enableAreaSelection)
                self.classifierWidget.btnCancel.clicked.connect(self.disableAreaSelection)
                self.classifierWidget.btnCancel.clicked.connect(self.deleteClassifierWidget)
                self.classifierWidget.closed.connect(self.disableAreaSelection)
                self.classifierWidget.closed.connect(self.deleteClassifierWidget)
                self.classifierWidget.btnPrev.clicked.connect(self.applyPreview)
                self.classifierWidget.sliderScores.valueChanged.connect(self.showScores)

                select_area_tool = self.activeviewer.tools.tools["SELECTAREA"]
                select_area_tool.setAreaStyle("PREVIEW")

                genutils.disconnectSignal(select_area_tool, "released", select_area_tool.released)
                select_area_tool.released.connect(self.cropPreview)

                genutils.disconnectSignal(select_area_tool, "rectChanged", select_area_tool.rectChanged)
                select_area_tool.rectChanged[int, int, int, int].connect(self.classifierWidget.updatePreviewArea)

            self.classifierWidget.show()
            self.classifierWidget.disableSliders()

    @pyqtSlot()
    def deleteClassifierWidget(self):
        del self.classifierWidget
        self.classifierWidget = None

    @pyqtSlot()
    def cropPreview(self):

        if self.classifierWidget is not None:

            classifier_selected = self.classifierWidget.selected()
            target_pixel_size = classifier_selected['Scale']
            scale_factor = self.activeviewer.image.pixelSize() / target_pixel_size

            x, y, w, h = self.classifierWidget.getPreviewArea()
            width = max(513 * scale_factor, w)
            height = max(513 * scale_factor, h)
            crop_image = self.activeviewer.img_map.copy(int(x), int(y), int(width), int(height))

            self.classifierWidget.setRGBPreview(crop_image)
            self.classifierWidget.chkAutocolor.setChecked(False)
            self.classifierWidget.chkAutolevel.setChecked(False)
            self.disableAreaSelection()

    def applyPreview(self):
        """
        crop selected area and apply preview.
        """

        x, y, w, h = self.classifierWidget.getPreviewArea()

        if w > 0 and h > 0:
            classifier_selected = self.classifierWidget.selected()
            checkColor = self.classifierWidget.chkAutocolor.isChecked()
            checkLevel = self.classifierWidget.chkAutolevel.isChecked()
            pred_thresh = self.classifierWidget.sliderScores.value() / 100.0

            for class_name in classifier_selected['Classes']:
                mylabel = self.project.labels.get(class_name)
                if class_name != 'Background' and mylabel is None:
                    msgBox = QMessageBox()
                    msgBox.setWindowTitle(self.TAGLAB_VERSION)
                    txt = 'The label ' + class_name + ' is missing. Please check your dictionary and try again.'
                    msgBox.setText(txt)
                    msgBox.exec()
                    return

            # free GPU memory
            self.resetNetworks()
            self.setupProgressBar()
            QApplication.processEvents()

            self.classifier = MapClassifier(classifier_selected, self.project.labels)
            self.classifier.updateProgress.connect(self.progress_bar.setProgress)

            self.progress_bar.hidePerc()
            self.progress_bar.setMessage("Initialization..")

            orthoimage = self.activeviewer.img_map
            target_pixel_size = classifier_selected['Scale']
            self.classifier.setup(orthoimage, self.activeviewer.image.pixelSize(), target_pixel_size,
                                  working_area=[y, x, w, h], padding=256)

            self.progress_bar.showPerc()
            self.progress_bar.setMessage("Classification: ")
            self.progress_bar.setProgress(0.0)
            QApplication.processEvents()

            self.classifier.run(1026, 513, 256, prediction_threshold=pred_thresh,
                                save_scores=True,autocolor = checkColor, autolevel = checkLevel)
            self.classifier.loadScores()
            self.showScores()

            self.deleteProgressBar()

    def showScores(self):

        self.classifierWidget.enableSliders()

        pred_thresh = self.classifierWidget.sliderScores.value() / 100.0
        outimg = self.classifier.classify(pred_thresh)
        self.classifierWidget.setLabelPreview(outimg)

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
            checkcolor = self.classifierWidget.chkAutocolor.isChecked()
            checklevel = self.classifierWidget.chkAutolevel.isChecked()
            pred_thresh = self.classifierWidget.sliderScores.value() / 100.0

            for class_name in classifier_selected['Classes']:
                mylabel = self.project.labels.get(class_name)
                if class_name != 'Background' and mylabel is None:
                    msgBox = QMessageBox()
                    msgBox.setWindowTitle(self.TAGLAB_VERSION)
                    txt = 'The label ' + class_name + ' is missing. Please check your dictionary and try again.'
                    msgBox.setText(txt)
                    msgBox.exec()
                    return

            # free GPU memory
            self.resetNetworks()

            self.classifierWidget.close()
            self.deleteClassifierWidget()

            self.setupProgressBar()

            # setup the desired classifier

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
                target_pixel_size = classifier_selected['Scale']
                self.classifier.setup(orthoimage, self.activeviewer.image.pixelSize(), target_pixel_size,
                                      working_area=self.project.working_area, padding=256)

                self.progress_bar.showPerc()
                self.progress_bar.setMessage("Classification: ")
                self.progress_bar.setProgress(0.0)
                QApplication.processEvents()

                # runs the classifier
                self.classifier.run(1026, 513, 256, prediction_threshold=pred_thresh,
                    save_scores=False, autocolor=checkcolor,  autolevel=checklevel)

                if self.classifier.flagStopProcessing is False:

                    # import generated label map
                    self.progress_bar.hidePerc()
                    self.progress_bar.setMessage("Finalizing classification results..")
                    QApplication.processEvents()

                    filename = os.path.join("temp", "labelmap.png")

                    offset = self.classifier.offset
                    scale = [self.classifier.scale_factor, self.classifier.scale_factor]
                    created_blobs = self.activeviewer.annotations.import_label_map(filename, self.project.labels,
                                                                                   offset, scale)
                    for blob in created_blobs:
                        self.viewerplus.addBlob(blob, selected=False)

                    logfile.info("[AUTOCLASS] Automatic classification ENDS.")

                    self.resetAutomaticClassification()

                    # save and close
                    msgBox = QMessageBox()
                    msgBox.setWindowTitle(self.TAGLAB_VERSION)
                    msgBox.setText("Automatic classification is finished. TagLab will be close. "
                                   "Please, click ok and save the project.")
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

    TAGLAB_PATH = os.path.dirname(__file__)
    PATH_ICONS = os.path.join(TAGLAB_PATH, "icons")
    PATH_FONTS = os.path.join(TAGLAB_PATH, "fonts")

    # set application icon
    app.setWindowIcon(QIcon(os.path.join(PATH_ICONS, "taglab50px.png")))

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
        font_id1 = QFD.addApplicationFont(os.path.join(PATH_FONTS, "opensans/OpenSans-Regular.ttf"))
        if font_id1 == -1:
            print("Failed to load OpenSans-Regular font..")

        font_id2 = QFD.addApplicationFont(os.path.join(PATH_FONTS, "roboto/Roboto-Light.ttf"))
        if font_id2 == -1:
            print("Failed to load Roboto-Light font..")

        font_id3 = QFD.addApplicationFont(os.path.join(PATH_FONTS, "roboto/Roboto-Regular.ttf"))
        if font_id3 == -1:
            print("Failed to load Roboto-Regular font..")

        font = QFont('Roboto')
        app.setFont(font)

    # get the scren size
    screen_size = app.primaryScreen().size()

    # Create the inspection tool
    tool = TagLab(screen_size)
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