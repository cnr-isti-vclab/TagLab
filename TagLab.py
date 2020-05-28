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

#import rasterio as rio

from PyQt5.QtCore import Qt, QSize, QDir, QPoint, QPointF, QRectF, QTimer, pyqtSlot, pyqtSignal, QSettings, QFileInfo
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


# DEEP EXTREME
# import models.deeplab_resnet as resnet
# from models.dataloaders import helpers as helpers
import cv2

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
from source.Project import Project, loadProject
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
        self.project = Project()        #current project
        self.image = None               #current image
        self.annotations = Annotation()  #REFACTOR we might want to move under project (or not?)

        self.map_3D_filename = None    #refactor THIS!
        self.map_image_filename = None #"map.png"  #REFACTOR to project.map_filename
        self.map_acquisition_date = None #"YYYY-MM-DD"
        self.map_px_to_mm_factor = 1.0

        self.recentFileActs = []  #refactor to self.maxRecentProjects
        self.maxRecentFiles = 4   #refactor to maxRecentProjects
        self.separatorRecentFilesAct = None    #refactor to separatorRecentFiles


        ##### INTERFACE #####
        #####################

        self.mapWidget = None
        self.classifierWidget = None

#        self.tool_used = "MOVE"        # tool currently used
#        self.tool_orig = "MOVE"        # tool originally used when a shift key changes the current tool
        #self.refine_grow = 0.0


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
        self.fillAction         = self.newAction("Fill Label",              "F",   self.fillLabel)


        #VIEWERPLUS
        self.viewerplus = QtImageViewerPlus()
        self.viewerplus.logfile = logfile
        self.viewerplus.viewUpdated.connect(self.updateViewInfo)
        self.viewerplus.updateInfoPanel.connect(self.updatePanelInfo)

        # MAP VIEWER
        self.mapviewer = QtMapViewer(self.MAP_VIEWER_SIZE)
        self.mapviewer.setPixmap(None)

        self.viewerplus.viewUpdated[QRectF].connect(self.mapviewer.drawOverlayImage)
        self.mapviewer.leftMouseButtonPressed[float, float].connect(self.viewerplus.center)
        self.mapviewer.mouseMoveLeftPressed[float, float].connect(self.viewerplus.center)

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
        self.sliderTrasparency.valueChanged[int].connect(self.sliderTrasparencyChanged)

        self.labelViewInfo = QLabel("100% | top:0 left:0 right:0 bottom:0         ")

        layout_slider = QHBoxLayout()
        layout_slider.addWidget(self.lblSlider)
        layout_slider.addWidget(self.sliderTrasparency)
        layout_slider.addWidget(self.labelViewInfo)



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

#        self.map_top = 0   #REFACTOR to project.map_top
#        self.map_left = 0
#        self.map_bottom = 0
#        self.map_right = 0

        # set default opacity
        self.sliderTrasparency.setValue(50)
        self.transparency_value = 0.5

#        self.img_map = None
#        self.img_thumb_map = None
#        self.img_overlay = QImage(16, 16, QImage.Format_RGB32)

        # EVENTS
        self.labels_widget.visibilityChanged.connect(self.updateVisibility)

        self.compare_panel.hideAnnotations.connect(self.hidePrevBlobs)
        self.compare_panel.showAnnotations.connect(self.showPrevBlobs)


        #self.viewerplus.leftMouseButtonPressed.connect(self.toolsOpsLeftPressed)
        #self.viewerplus.leftMouseButtonReleased.connect(self.toolsOpsLeftReleased)
        #self.viewerplus.rightMouseButtonPressed.connect(self.toolsOpsRightPressed)
        #self.viewerplus.mouseMoveLeftPressed.connect(self.toolsOpsMouseMove)
        #self.viewerplus.leftMouseButtonDoubleClicked.connect(self.selectOp)

        self.viewerplus.customContextMenuRequested.connect(self.openContextMenu)



        # NETWORKS
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
        filename, file_extension = os.path.splitext(self.project.filename)
        self.project.save(filename + "_autosave.json")

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
        saveAct.setShortcut('Ctrl+S')
        saveAct.setStatusTip("Save current project")
        saveAct.triggered.connect(self.saveProject)

        saveAsAct = QAction("Save As..", self)
        saveAsAct.setShortcut('Ctrl+Alt+S')
        saveAsAct.setStatusTip("Save current project")
        saveAsAct.triggered.connect(self.saveAsProject)

        for i in range(self.maxRecentFiles):
            self.recentFileActs.append(QAction(self, visible=False, triggered=self.openRecentProject))

        # THIS WILL BECOME "ADD MAP" TO ADD MULTIPLE MAPS (e.g. depth, different years)
        newMapAct = QAction("New Map..", self)
        newMapAct.setShortcut('Ctrl+L')
        newMapAct.setStatusTip("Add a new map to the project and load it")
        newMapAct.triggered.connect(self.setMapToLoad)

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
        undoAct.triggered.connect(self.viewerplus.undo)

        redoAct = QAction("Redo", self)
        redoAct.setShortcut('Ctrl+Shift+Z')
        redoAct.setStatusTip("Redo")
        redoAct.triggered.connect(self.viewerplus.redo)

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
        filemenu.addAction(saveAsAct)
        filemenu.addSeparator()
        filemenu.addAction(newMapAct)
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
            # RESET CURRENT OPERATION
            self.viewerplus.resetSelection()
            self.viewerplus.resetTools()

            message = "[TOOL][" + self.viewerplus.tools.tool + "] Current operation has been canceled."
            logfile.info(message)

        elif event.key() == Qt.Key_S and modifiers & Qt.ControlModifier:
            self.save()

        elif event.key() == Qt.Key_A:
            self.assignOperation()

        elif event.key() == Qt.Key_Delete:
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
        #     self.hole()            # APPLY DEEP EXTREME (IF FOUR POINTS HAVE BEEN SELECTED)
        #             elif self.tool_used == "DEEPEXTREME" and self.pick_points_number == 4:
        #
        #                 self.segmentWithDeepExtreme()
        #                 self.resetPickPoints()

        elif event.key() == Qt.Key_4:
            # ACTIVATE "DEEP EXTREME" TOOL
            self.deepExtreme()

        elif event.key() == Qt.Key_P:
            self.drawDeepExtremePoints()
        #
        # elif event.key() == Qt.Key_Y:
        #     self.refineAllBorders()

        elif event.key() == Qt.Key_Home:
            # ASSIGN LABEL
            self.annotations.refine_depth_weight += 0.1;
            if self.annotations.refine_depth_weight > 1.0:
                self.annotations.refine_depth_weight = 1.0;
            print("Depth weight: " + str(self.annotations.refine_depth_weight))

        elif event.key() == Qt.Key_End:
            # ASSIGN LABEL
            self.annotations.refine_depth_weight -= 0.1;
            if self.annotations.refine_depth_weight < 0.0:
                self.annotations.refine_depth_weight = 0.0;
            print("Depth weight: " + str(self.annotations.refine_depth_weight))


        elif event.key() == Qt.Key_BracketLeft:
            self.annotations.refine_conservative *= 0.9
            print("Conservative: " + str(self.annotations.refine_conservative))

        elif event.key() == Qt.Key_BracketRight:
            self.annotations.refine_conservative *= 1.1
            print("Conservative: " + str(self.annotations.refine_conservative))


        elif event.key() == Qt.Key_Space:
            print("apply!")
            self.viewerplus.tools.applyTool()

    @pyqtSlot()
    def sliderTrasparencyChanged(self):
        #TODO should be (self, value) as the signal is supposed to send a value!
        value = self.sender().value()
        # update transparency value
        str1 = "Transparency {}%".format(value)
        self.lblSlider.setText(str1)
        self.viewerplus.applyTransparency(value)

    @pyqtSlot()
    def updateVisibility(self):
        self.viewerplus.updateVisibility()


    @pyqtSlot()
    def updateViewInfo(self):

        zf = self.viewerplus.zoom_factor * 100.0

        topleft = self.viewerplus.mapToScene(QPoint(0, 0))
        bottomright = self.viewerplus.mapToScene(self.viewerplus.viewport().rect().bottomRight())

        (left, top) = self.viewerplus.clampCoords(topleft.x(), topleft.y())
        (right, bottom) = self.viewerplus.clampCoords(bottomright.x(), bottomright.y())

        text = "| {:6.2f}% | top: {:4d} left: {:4d} bottom: {:4d} right: {:4d}".format(zf, top, left, bottom, right)

        self.map_top = top
        self.map_left = left
        self.map_bottom = bottom
        self.map_right = right

        self.labelViewInfo.setText(text)

    # @pyqtSlot(float, float)
    # def updateMainView(self, x, y):
    #
    #     zf = self.viewerplus.zoom_factor
    #
    #     xmap = float(self.img_map.width()) * x
    #     ymap = float(self.img_map.height()) * y
    #
    #     h = self.map_bottom - self.map_top
    #     w = self.map_right - self.map_left
    #
    #     posx = xmap - w / 2
    #     posy = ymap - h / 2
    #
    #     if posx < 0:
    #         posx = 0
    #     if posy < 0:
    #         posy = 0
    #
    #     if posx + w/2 > self.img_map.width():
    #         posx = self.img_map.width() - w / 2 - 1
    #
    #     if posy + h/2 > self.img_map.height():
    #         posy = self.img_map.height() - h / 2 - 1
    #
    #     posx = posx * zf;
    #     posy = posy * zf;
    #
    #     self.viewerplus.horizontalScrollBar().setValue(posx)
    #     self.viewerplus.verticalScrollBar().setValue(posy)



    def resetAll(self):
        self.viewerplus.clear()
        self.mapviewer.clear()
        # RE-INITIALIZATION

        self.mapWidget = None
        self.project = Project()


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

    def setTool(self, tool):
        tools = {
            "MOVE"       : ["Move"       , self.btnMove],
            "CREATECRACK": ["Crack"      , self.btnCreateCrack],
            "SPLITBLOB"  : ["Split Blob" , self.btnSplitBlob],
            "ASSIGN"     : ["Assign"     , self.btnAssign],
            "EDITBORDER" : ["Edit Border", self.btnEditBorder],
            "CUT"        : ["Cut"        , self.btnCut],
            "FREEHAND"   : ["Freehand"   , self.btnFreehand],
            "RULER"      : ["Ruler"      , self.btnRuler],
            "DEEPEXTREME": ["4-click"    , self.btnDeepExtreme]
        }
        newtool = tools[tool]
        self.resetToolbar()
        self.viewerplus.setTool(tool)
        newtool[1].setChecked(True)
        logfile.info("[TOOL][" + tool + "] Tool activated")
        self.infoWidget.setInfoMessage(newtool[0] + " Tool is active")


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
    def splitBlob(self):
        """
        Activate the tool "Split Blob".
        """
        self.setTool("SPLITBLOB")

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
    def ruler(self):
        """
        Activate the "ruler" tool. The tool allows to measure the distance between two points or between two blob centroids.
        """
        self.setTool("RULER")

    @pyqtSlot()
    def deepExtreme(self):
        """
        Activate the "Deep Extreme" tool. The segmentation is performed by selecting four points at the
        extreme of the corals and confirm the points by pressing SPACE.
        """
        self.setTool("DEEPEXTREME")

    @pyqtSlot()
    def noteChanged(self):
        if len(self.viewerplus.selected_blobs) > 0:

            for blob in self.viewerplus.selected_blobs:
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
        self.viewerplus.deleteSelectedBlobs()
        logfile.info("[OP-DELETE] Selected blobs has been DELETED")



#OPERATIONS

    def assignOperation(self):
        view = self.viewerplus
        for blob in view.selected_blobs:
            view.setBlobClass(blob, self.labels_widget.getActiveLabelName())
        view.saveUndo()
        view.resetSelection()


    def union(self):
        """
        blob A = blob A U blob B
        """
        view = self.viewerplus
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
        view = self.viewerplus

        if len(view.selected_blobs) == 2:

            message = "[OP-SUBTRACT] SUBTRACT LABELS operation begins.. (number of selected blobs: " + str(len(view.selected_blobs)) + ")"
            logfile.info(message)

            selectedA = view.selected_blobs[0]
            selectedB = view.selected_blobs[1]

            #blobA and will be modified, make a copy!
            blobA = selectedA.copy()

            flag_intersection = view.annotations.subtract(blobA, selectedB, view.scene)

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
        view = self.viewerplus
        if len(view.selected_blobs) == 2:

            message = "[OP-DIVIDE] DIVIDE LABELS operation begins.. (number of selected blobs: " + str(len(view.selected_blobs)) + ")"
            logfile.info(message)

            selectedA = view.selected_blobs[0]
            selectedB = view.selected_blobs[1]

            #blobA and blobB and will be modified, make a copy!
            blobA = selectedA.copy()
            blobB = selectedB.copy()

            intersects = view.annotations.subtract(blobB, blobA, view.scene)
            if intersects:

                self.logBlobInfo(selectedA, "[OP-DIVIDE][BLOB-SELECTED]")
                self.logBlobInfo(blobA, "[OP-DIVIDE][BLOB-EDITED]")
                self.logBlobInfo(selectedB, "[OP-DIVIDE][BLOB-SELECTED]")
                self.logBlobInfo(blobB, "[OP-DIVIDE][BLOB-EDITED]")

                view.removeBlob(selectedA)
                view.removeBlob(selectedB)
                view.addBlob(blobA, selected=False)
                view.addBlob(blobB, selected=False)
                view.saveUndo()

            logfile.info("[OP-DIVIDE] DIVIDE LABELS operation ends.")

        else:

            self.infoWidget.setInfoMessage("You need to select <em>two</em> blobs for DIVIDE operation.")

    def refineBorderDilate(self):
        view = self.viewerplus

        logfile.info("[OP-REFINE-BORDER-DILATE] DILATE-BORDER operation begins..")

        view.refine_grow += 2
        self.refineBorder()
        #self.refine_grow = 0

        logfile.info("[OP-REFINE-BORDER-DILATE] DILATE-BORDER operation ends.")


    def refineBorderErode(self):

        logfile.info("[OP-REFINE-BORDER-ERODE] ERODE-BORDER operation begins..")
        view = self.viewerplus

        view.refine_grow -= 2
        self.refineBorder()
        #self.refine_grow = 0

        logfile.info("[OP-REFINE-BORDER-ERODE] ERODE-BORDER operation ends.")

    def refineBorderOperation(self):

        logfile.info("[OP-REFINE-BORDER] REFINE-BORDER operation begins..")
        view = self.viewerplus

        view.refine_grow = 0
        self.refineBorder()

        logfile.info("[OP-REFINE-BORDER] REFINE-BORDER operation ends.")

    def refineBorder(self):
        """
        Refine blob border
        """
        view = self.viewerplus

        if view.refine_grow != 0 and view.refine_original_mask is None:
            return


        # padding mask to allow moving boundary
        padding = 35
        if len(view.selected_blobs) == 1:

            selected = view.selected_blobs[0]
            #blob = selected.copy()
            self.logBlobInfo(selected, "[OP-REFINE-BORDER][BLOB-SELECTED]")

            if view.refine_grow == 0:
                mask = selected.getMask()
                mask = np.pad(mask, (padding, padding), mode='constant', constant_values=(0, 0)).astype(np.ubyte)
                view.refine_original_mask = mask.copy()
                view.refine_original_bbox = selected.bbox.copy()
                bbox = selected.bbox.copy()
            else:
                mask = view.refine_original_mask.copy()
                bbox = view.refine_original_bbox.copy()


            bbox[0] -= padding; #top
            bbox[1] -= padding; #left
            bbox[2] += 2*padding; #width
            bbox[3] += 2*padding; #height

            img = utils.cropQImage(view.img_map, bbox)
            img = utils.qimageToNumpyArray(img)

            if view.depth_map is not None:
                depth = view.depth_map[bbox[0] : bbox[0]+bbox[3], bbox[1] : bbox[1] + bbox[2]]
#                imgg = utils.floatmapToQImage((depth - 4)*255)
#                imgg.save("test.png")

                # #utils.cropQImage(self.depth_map, bbox)
                #depth = utils.qimageToNumpyArray(depth)
            else:
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
                #    blob.updateUsingMask(bbox, mask.astype(np.int))
                created_blobs = view.annotations.refineBorder(bbox, selected, img, depth, mask, view.refine_grow, view.tools.edit_points.last_editborder_points)

                view.removeBlob(selected)

                for blob in created_blobs:
                    view.addBlob(blob, selected=True)
                    self.logBlobInfo(blob, "[OP-REFINE-BORDER][BLOB-CREATED]")

                view.saveUndo()

                self.logBlobInfo(blob, "[OP-REFINE-BORDER][BLOB-REFINED]")

            except Exception as e:
                print("FAILED!", e)
                pass

        else:
            self.infoWidget.setInfoMessage("You need to select <em>one</em> blob for REFINE operation.")

    def fillLabel(self, blob):
        view = self.viewerplus

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

            view.removeBlob(blob)
            filled.inner_contours.clear()
            filled.createFromClosedCurve([filled.contour])
            view.addBlob(filled, True)

            self.logBlobInfo(filled, "[OP-FILL][BLOB-EDITED]")

        if count:
            view.saveUndo()

        logfile.info("[OP-FILL] FILL operation ends.")




    def logBlobInfo(self, blob, tag):

        message1 = tag + " BLOBID=" + str(blob.id) + " VERSION=" + str(blob.version) + " NAME=" + blob.blob_name + " CLASS=" + blob.class_name
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

        self.setProjectTitle("NONE")

        self.infoWidget.setInfoMessage("TagLab has been reset. To continue open an existing project or load a map.")
        logfile.info("[PROJECT] A new project has been setup.")

 # REFACTOR load project properties
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


#REFACTOR
    @pyqtSlot()
    def setMapProperties(self):

        map_filename = self.mapWidget.editMapFile.text()

        # check if the map file exists
        if not os.path.exists(map_filename):

            self.infoWidget.setWarningMessage("Map file does not exist.")

        else:

            # transfer settings
            self.map_image_filename = self.mapWidget.editMapFile.text()
            self.map_3D_filename = self.mapWidget.edit3DMapFile.text()
            self.map_acquisition_date = self.mapWidget.editAcquisitionDate.text()
            self.map_px_to_mm_factor = float(self.mapWidget.editScaleFactor.text())

            # close map settings
            self.mapWidget.close()
            self.mapWidget = None

            self.loadMap()

 # REFACTOR
    def loadMap(self, image):

        self.image = image
        self.annotations = image.annotations
        self.channel = image.channels[0]

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.infoWidget.setInfoMessage("Map is loading..")
            self.viewerplus.setProject(self.project)
            self.viewerplus.setImage(image)
            self.viewerplus.setChannel(self.channel)

            self.img_thumb_map = self.viewerplus.pixmap.scaled(self.MAP_VIEWER_SIZE, self.MAP_VIEWER_SIZE, Qt.KeepAspectRatio,
                                                 Qt.SmoothTransformation)
            self.mapviewer.setPixmap(self.img_thumb_map)
            self.mapviewer.setOpacity(0.5)

            self.infoWidget.setInfoMessage("The map has been successfully loading.")

        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Error loading map:" + str(e))
            msgBox.exec()

        QApplication.restoreOverrideCursor()


    @pyqtSlot()
    def openProject(self):


        filters = "ANNOTATION PROJECT (*.json)"
        #dir = '/home/ponchio/devel/TagLab/map'
        #filename = dir + '/test.json'
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
        self.save()

    # REFACTOR use project methods
    @pyqtSlot()
    def saveAsProject(self):

        filters = "ANNOTATION PROJECT (*.json)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save the project", self.taglab_dir, filters)

        if filename:
            dir = QDir(self.taglab_dir)
            self.project.filename = dir.relativeFilePath(filename)
            self.setProjectTitle(self.project.filename)
            self.save()

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
        created_blobs = self.annotations.import_label_map(filename, self.img_map, self.labels)
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

            self.annotations.export_image_data_for_Scripps(self.img_map, filename, self.labels)

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
            self.annotations.export_new_dataset(self.img_map, tile_size=1024, step=256, basename=filename, labels_info = self.labels)



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

    # REFACTOR use project methods

    def load(self, filename):
        """
        Load a previously saved projects.
        """

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.resetAll()

        try:
            self.project = loadProject(filename)
        except Exception as e:
            msgBox = QMessageBox()
            msgBox.setText("The json project contains an error:\n {0}\n\nPlease contact us.".format(str(e)))
            msgBox.exec()
            print(self.project)
            return

        QApplication.restoreOverrideCursor()
        self.setProjectTitle(self.project.filename)

        #load the first map if present in project
        if len(self.project.images):
            self.loadMap(self.project.images[0])

        if self.timer is None:
            self.activateAutosave()

        self.infoWidget.setInfoMessage("The project: " + self.project.filename + " has been successfully open.")

        message = "[PROJECT] The project " + self.project.filename + " has been loaded."
        logfile.info(message)


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

                self.saveAsProject()

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
