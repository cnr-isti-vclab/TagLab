# LabelLab                                               
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
import glob
import time
import random
import datetime

import bz2
import numpy as np
import numpy.ma as ma
from skimage import measure

import matplotlib.pyplot as plt

from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, QLineF, QRectF, QTimer, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainterPath, QPainter, QFont, QColor, QPolygonF, QImage, QPixmap, QPainter, QIcon, QKeySequence, \
    QPen, QBrush, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QApplication, QWidget, QMenu, QSizePolicy, QScrollArea, QLabel, QToolButton, QPushButton, QSlider, \
    QMessageBox, QGroupBox, QHBoxLayout, QVBoxLayout, QTextEdit, QLineEdit, QGraphicsView, QAction

# PYTORCH
import torch
from torch.nn.functional import upsample

from collections import OrderedDict
from PIL import Image

# DEEP EXTREME
import models.deeplab_resnet as resnet
from models.dataloaders import helpers as helpers

# CUSTOM
from source.Configuration import Configuration
from source.QtImageViewerPlus import QtImageViewerPlus
from source.QtMapViewer import QtMapViewer
from source.QtCrackWidget import QtCrackWidget
from source.QtExportWidget import QtExportWidget
#from QtInfoWidget import QtInfoWidget
from source.Annotation import Annotation
from source.Labels import Labels, LabelsWidget
from source import utils

# LOGGING
import logging

# configure the logger
now = datetime.datetime.now()
LOG_FILENAME = "tool" + now.strftime("%Y-%m-%d-%H-%M") + ".log"
logging.basicConfig(level=logging.DEBUG, filemode='w', filename=LOG_FILENAME, format = '%(asctime)s %(levelname)-8s %(message)s')
logfile = logging.getLogger("tool-logger")


class LabelLab(QWidget):

    def __init__(self, configuration, parent=None):
        super(LabelLab, self).__init__(parent)

        ##### CUSTOM STYLE #####

        self.setStyleSheet("background-color: rgb(55,55,55); color: white")

        ##### DATA INITIALIZATION AND SETUP #####

        logfile.info("Initizialization begins..")
        self.conf = configuration
        self.conf.createProjectFolder()

        self.image_map_filename = configuration.image_map_filename
        basename = os.path.basename(self.image_map_filename)
        idx = basename.rfind(".")
        self.thumb_map_filename = basename[0:idx] + "_thumb.png"

        # MAP VIEWER preferred size (longest side)
        self.MAP_VIEWER_SIZE = 500
        self.createMapThumbnail()

        # ANNOTATION DATA
        self.annotations = Annotation()

        ##### INTERFACE #####
        #####################

        self.tool_used = "MOVE"        # tool currently used
        self.current_selection = None  # blob currently selected

        ICON_SIZE = 48
        BUTTON_SIZE = 54

        ##### TOP LAYOUT

        top_layout = QHBoxLayout()

        self.scrippsIcon = QLabel()
        pxmap = QPixmap("icons\\vclab.png")
        pxmap = pxmap.scaledToWidth(ICON_SIZE+2)
        self.scrippsIcon.setPixmap(pxmap)

        # LOAD/SAVE BUTTONS

        self.btnLoad = QPushButton()
        self.btnLoad.setEnabled(True)
        self.btnLoad.setMinimumWidth(ICON_SIZE)
        self.btnLoad.setMinimumHeight(ICON_SIZE)
        self.btnLoad.setIcon(QIcon("icons\\download.png"))
        self.btnLoad.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnLoad.setMaximumWidth(BUTTON_SIZE)
        self.btnLoad.setToolTip("Load Annotations")
        self.btnLoad.clicked.connect(self.loadAnnotations)

        self.btnSave = QPushButton()
        self.btnSave.setEnabled(True)
        self.btnSave.setMinimumWidth(ICON_SIZE)
        self.btnSave.setMinimumHeight(ICON_SIZE)
        self.btnSave.setIcon(QIcon("icons\\disc.png"))
        self.btnSave.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnSave.setMaximumWidth(BUTTON_SIZE)
        self.btnSave.setToolTip("Save Annotations")
        self.btnSave.clicked.connect(self.saveAnnotations)

        self.btnExport = QPushButton()
        self.btnExport.setEnabled(True)
        self.btnExport.setMinimumWidth(ICON_SIZE)
        self.btnExport.setMinimumHeight(ICON_SIZE)
        self.btnExport.setIcon(QIcon("icons\\upload.png"))
        self.btnExport.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnExport.setMaximumWidth(BUTTON_SIZE)
        self.btnExport.setToolTip("Export Data")
        self.btnExport.clicked.connect(self.exportData)

        top_layout.addWidget(self.scrippsIcon)
        top_layout.addWidget(self.btnLoad)
        top_layout.addWidget(self.btnSave)
        top_layout.addWidget(self.btnExport)
        top_layout.addStretch()

        ##### LAYOUT EDITING TOOLS (VERTICAL)

        #...TODO...

        flatbuttonstyle1 = "\
        QPushButton:checked\
        {\
            background-color: rgb(100,100,100);\
        }\
        QPushButton:hover\
        {\
            border: 1px solid darkgray;\
        }"

        flatbuttonstyle2 = "\
        QPushButton:checked\
        {\
            background-color: rgb(100,100,100);\
        }\
        QPushButton:hover\
        {\
            border: 1px solid rgb(255,100,100);\
        }"

        layout_tools = QVBoxLayout()

        self.btnMove = QPushButton()
        self.btnMove.setEnabled(True)
        self.btnMove.setCheckable(True)
        self.btnMove.setFlat(True)
        self.btnMove.setStyleSheet(flatbuttonstyle1)
        self.btnMove.setMinimumWidth(ICON_SIZE)
        self.btnMove.setMinimumHeight(ICON_SIZE)
        self.btnMove.setIcon(QIcon("icons\\move.png"))
        self.btnMove.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnMove.setMaximumWidth(BUTTON_SIZE)
        self.btnMove.setToolTip("Move")
        self.btnMove.clicked.connect(self.move)

        self.btnAssign = QPushButton()
        self.btnAssign.setEnabled(True)
        self.btnAssign.setCheckable(True)
        self.btnAssign.setFlat(True)
        self.btnAssign.setStyleSheet(flatbuttonstyle1)
        self.btnAssign.setMinimumWidth(ICON_SIZE)
        self.btnAssign.setMinimumHeight(ICON_SIZE)
        self.btnAssign.setIcon(QIcon("icons\\bucket.png"))
        self.btnAssign.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnAssign.setMaximumWidth(BUTTON_SIZE)
        self.btnAssign.setToolTip("Assign class")
        self.btnAssign.clicked.connect(self.assign)

        self.btnEditBorder = QPushButton()
        self.btnEditBorder.setEnabled(True)
        self.btnEditBorder.setCheckable(True)
        self.btnEditBorder.setFlat(True)
        self.btnEditBorder.setStyleSheet(flatbuttonstyle1)
        self.btnEditBorder.setMinimumWidth(ICON_SIZE)
        self.btnEditBorder.setMinimumHeight(ICON_SIZE)
        self.btnEditBorder.setIcon(QIcon("icons\\edit.png"))
        self.btnEditBorder.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnEditBorder.setMaximumWidth(BUTTON_SIZE)
        self.btnEditBorder.setToolTip("Edit Border")
        self.btnEditBorder.clicked.connect(self.editBorder)

        self.btnCreateCrack = QPushButton()
        self.btnCreateCrack.setEnabled(True)
        self.btnCreateCrack.setCheckable(True)
        self.btnCreateCrack.setFlat(True)
        self.btnCreateCrack.setStyleSheet(flatbuttonstyle1)
        self.btnCreateCrack.setMinimumWidth(ICON_SIZE)
        self.btnCreateCrack.setMinimumHeight(ICON_SIZE)
        self.btnCreateCrack.setIcon(QIcon("icons\\crack.png"))
        self.btnCreateCrack.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnCreateCrack.setMaximumWidth(BUTTON_SIZE)
        self.btnCreateCrack.setToolTip("Create crack")
        self.btnCreateCrack.clicked.connect(self.createCrack)

        self.btnRuler = QPushButton()
        self.btnRuler.setEnabled(True)
        self.btnRuler.setCheckable(True)
        self.btnRuler.setFlat(True)
        self.btnRuler.setStyleSheet(flatbuttonstyle1)
        self.btnRuler.setMinimumWidth(ICON_SIZE)
        self.btnRuler.setMinimumHeight(ICON_SIZE)
        self.btnRuler.setIcon(QIcon("icons\\ruler.png"))
        self.btnRuler.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnRuler.setMaximumWidth(BUTTON_SIZE)
        self.btnRuler.setToolTip("Measure tool")
        self.btnRuler.clicked.connect(self.ruler)



        self.btnDeepExtreme = QPushButton()
        self.btnDeepExtreme.setEnabled(True)
        self.btnDeepExtreme.setCheckable(True)
        self.btnDeepExtreme.setFlat(True)
        self.btnDeepExtreme.setStyleSheet(flatbuttonstyle2)
        self.btnDeepExtreme.setMinimumWidth(ICON_SIZE)
        self.btnDeepExtreme.setMinimumHeight(ICON_SIZE)
        self.btnDeepExtreme.setIcon(QIcon("icons\\dexter.png"))
        self.btnDeepExtreme.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        self.btnDeepExtreme.setMaximumWidth(BUTTON_SIZE)
        self.btnDeepExtreme.setToolTip("Deep Extreme")
        self.btnDeepExtreme.clicked.connect(self.deepExtreme)

        layout_tools.setSpacing(0)
        layout_tools.addWidget(self.btnMove)
        layout_tools.addWidget(self.btnAssign)
        layout_tools.addWidget(self.btnEditBorder)
        layout_tools.addWidget(self.btnCreateCrack)
        layout_tools.addWidget(self.btnRuler)
        #layout_tools.addWidget(self.btnCutter)
        layout_tools.addSpacing(10)
        layout_tools.addWidget(self.btnDeepExtreme)
        #layout_tools.addWidget(self.btnAutomaticSeg)
        layout_tools.addStretch()


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

        layout_viewer.addLayout(layout_slider)
        layout_viewer.addWidget(self.viewerplus)


        ##### LAYOUT - labels + blob info + navigation map

        # LABELS

        self.labels_widget = LabelsWidget()

        scroll_area = QScrollArea()
        scroll_area.setStyleSheet("background-color: rgb(40,40,40); border:none")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setMinimumHeight(200)
        scroll_area.setWidget(self.labels_widget)

        groupbox_labels = QGroupBox("Labels")

        layout_groupbox = QVBoxLayout()
        layout_groupbox.addWidget(scroll_area)
        groupbox_labels.setLayout(layout_groupbox)

        # BLOB INFO
        groupbox_blobpanel = QGroupBox("Segmentation Info")
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
        self.editNote.setMaximumHeight(70)
        self.editNote.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editNote.textChanged.connect(self.noteChanged)
        layout_blobpanel = QVBoxLayout()
        layout_blobpanel.addLayout(blobpanel_layoutH1)
        layout_blobpanel.addLayout(blobpanel_layoutH2)
        layout_blobpanel.addWidget(lblNote)
        layout_blobpanel.addWidget(self.editNote)
        groupbox_blobpanel.setLayout(layout_blobpanel)


        # MAP VIEWER
        self.mapviewer = QtMapViewer(self.MAP_VIEWER_SIZE)

        layout_labels = QVBoxLayout()
        self.mapviewer.setStyleSheet("background-color: rgb(40,40,40); border:none")
        layout_labels.addWidget(groupbox_labels)
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
        main_view_layout.setStretchFactor(layout_labels, 3)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(main_view_layout)

        self.setLayout(main_layout)

        self.setWindowTitle("LabelLab")


        ##### FURTHER INITIALIZAION #####
        #################################

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.openContextMenu)

        self.map_top = 0
        self.map_left = 0
        self.map_bottom = 0
        self.map_right = 0

        # set default opacity
        self.sliderTrasparency.setValue(50)
        self.transparency_value = 0.5

        # load the last saved annotations (if exist)
        self.annotationFileId = 0
        #self.loadAnnotations()

        self.img_map = QImage(self.image_map_filename)
        self.img_thumb_map = QImage(os.path.join(self.conf.project_dir, self.thumb_map_filename))
        self.viewerplus.setImage(self.img_map)
        self.mapviewer.setImage(self.img_thumb_map)
        self.viewerplus.viewUpdated.connect(self.updateMapViewer)
        self.mapviewer.setOpacity(0.5)

        self.img_overlay = QImage(16, 16, QImage.Format_RGB32)

        # LOAD DEEP EXTREME NETWORK
        self.loadingDeepExtremeNetwork()

        # EVENTS
        self.labels_widget.visibilityChanged.connect(self.updateVisibility)

        self.mapviewer.leftMouseButtonPressed.connect(self.updateMainView)
        self.mapviewer.mouseMoveLeftPressed.connect(self.updateMainView)

        self.viewerplus.leftMouseButtonPressed.connect(self.toolsOpsLeftPressed)
        self.viewerplus.leftMouseButtonReleased.connect(self.toolsOpsLeftReleased)
        self.viewerplus.rightMouseButtonPressed.connect(self.toolsOpsRightPressed)
        self.viewerplus.mouseMoveLeftPressed.connect(self.toolsOpsMouseMove)
        self.viewerplus.leftMouseButtonDoubleClicked.connect(self.selectOp)

        self.current_selection = None

        # DRAWING SETTINGS
        self.BLOB_BORDER_WIDTH = 3
        self.CROSS_LINE_WIDTH = 6

        # DATA FOR THE SELECTION
        self.selected_blobs = []
        self.MAX_SELECTED = 5 # maximum number of selected blobs

        # DATA FOR THE EDITBORDER TOOL
        self.editborder_points = np.array(())
        self.editborder_qpath = None
        self.editborder_qpath_gitem = None

        # DATA FOR THE CREATECRACK TOOL
        self.crackWidget = None

        # DATA FOR THE RULER TOOL
        self.ruler_points_number = 0
        self.ruler_points = np.zeros((2, 2))
        self.ruler_lines = []
        self.ruler_text_gi = None

        # DATA FOR THE DEEP EXTREME TOOL
        self.extreme_points_number = 0
        self.extreme_points = np.zeros((4, 2))
        self.extreme_points_lines = []

        logfile.info("Inizialization finished!")

        self.move()

        # AUTOSAVE
        self.flagAutosave = True

        if self.flagAutosave:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.autosave)
            self.timer.start(180000)   # save every 3 minute
        else:
            self.timer = None


    @pyqtSlot()
    def autosave(self):
        print("Save annotations, please ! ")

    # call by pressing right button
    def openContextMenu(self, position):

        menu = QMenu(self)
        menu.setAutoFillBackground(True)

        str = "QMenu::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(110, 110, 120);\
            }"

        menu.setStyleSheet(str)

        assignAction = QAction("Assign Class", self)
        assignAction.setShortcut(QKeySequence("A"))
        assignAction.setShortcutVisibleInContextMenu(True)
        menu.addAction(assignAction)

        deleteAction = QAction("Delete Labels", self)
        deleteAction.setShortcut(QKeySequence("Del"))
        deleteAction.setShortcutVisibleInContextMenu(True)
        menu.addAction(deleteAction)

        menu.addSeparator()

        mergeAction = QAction("Merge Overlapped Labels", self)
        mergeAction.setShortcuts(QKeySequence("M"))
        mergeAction.setShortcutVisibleInContextMenu(True)
        menu.addAction(mergeAction)

        divideAction = QAction("Divide Labels", self)
        divideAction.setShortcut(QKeySequence("D"))
        divideAction.setShortcutVisibleInContextMenu(True)
        menu.addAction(divideAction)

        subtractAction = QAction("Subtract Labels", self)
        subtractAction.setShortcut(QKeySequence("S"))
        subtractAction.setShortcutVisibleInContextMenu(True)
        menu.addAction(subtractAction)



        pt = self.viewerplus.mapToScene(position)

        action = menu.exec_(self.mapToGlobal(position))

        if action == deleteAction:
            self.deleteSelected()
        # elif action == groupAction:
        #     self.group()
        # elif action == ungroupAction:
        #     self.ungroup()
        elif action == mergeAction:
            self.union()
        elif action == divideAction:
            self.divide()
        elif action == subtractAction:
            self.subtract()
        elif action == assignAction:
            self.assign()

    def clampCoords(self, x, y):

        xc = int(x)
        yc = int(y)

        if xc < 0:
            xc = 0

        if yc < 0:
            yc = 0

        if xc > self.img_map.width():
            xc = self.img_map.width()

        if yc > self.img_map.height():
            yc = self.img_map.height()

        return (xc, yc)

    def keyPressEvent(self, event):

        key_pressed = event.text()
        logfile.info("Key %s has been pressed.", key_pressed)

        if event.key() == Qt.Key_Escape:
            # RESET CURRENT OPERATION
            if self.tool_used == "EDITBORDER":
                self.resetEditBorder()
            elif self.tool_used == "RULER":
                self.resetRulerTool()
            elif self.tool_used == "DEEPEXTREME":
                self.resetDeepExtremeTool()
        elif event.key() == Qt.Key_Delete:
            # DELETE SELECTED BLOBS
            self.deleteSelected()
        elif event.key() == Qt.Key_M:
            # MERGE BETWEEN TWO BLOBS
            self.union()
        elif event.key() == Qt.Key_S:
            # SUBTRACTION BETWEEN TWO BLOBS (A = A / B), THEN BLOB B IS DELETED
            self.subtract()
        elif event.key() == Qt.Key_D:
            # SUBTRACTION BETWEEN TWO BLOBS (A = A / B), BLOB B IS NOT DELETED
            self.divide()
        elif event.key() == Qt.Key_G:
            # GROUP TOGETHER THE SELECTED BLOBS
            self.group()
        elif event.key() == Qt.Key_U:
            # UNGROUP THE BLOBS OF A GROUP (ONE BLOB OF THE GROUP SHOULD BE SELECTED)
            self.ungroup()
        elif event.key() == Qt.Key_A:
            # ACTIVATE "ASSIGN" TOOL
            self.assign()
        elif event.key() == Qt.Key_H:
            # ACTIVATE THE "HOLE" TOOL
            self.hole()
        elif event.key() == Qt.Key_4:
            # ACTIVATE "DEEP EXTREME" TOOL
            self.deepExtreme()
        elif event.key() == Qt.Key_P:
            self.drawDeepExtremePoints()
        elif event.key() == Qt.Key_Space:

            # APPLY THE EDITBORDER OPERATION
            if self.tool_used == "EDITBORDER":

                if len(self.selected_blobs) > 0:

                    selected_blob = self.selected_blobs[0]

                    pxs = utils.draw_open_polygon(self.editborder_points[:, 1], self.editborder_points[:, 0])
                    pts = np.asarray(pxs)
                    pts = pts.transpose()
                    pts[:, [1, 0]] = pts[:, [0, 1]]

                    new_points = selected_blob.snapToBorder(pts)

                    if new_points is not None:

                        selected_blob.addToMask(new_points)

                        selected_blob.cutFromMask(new_points)

                    self.drawBlob(selected_blob, selected=True)

                self.resetEditBorder()


            # APPLY DEEP EXTREME (IF FOUR POINTS HAVE BEEN SELECTED)
            elif self.tool_used == "DEEPEXTREME" and self.extreme_points_number == 4:

                self.segmentWithDeepExtreme()
                self.resetDeepExtremeTool()

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

        for blob in self.annotations.seg_blobs:
            blob.qpath_gitem.setOpacity(self.transparency_value)

    @pyqtSlot()
    def updateVisibility(self):

        for blob in self.annotations.seg_blobs:

            visibility = self.labels_widget.isClassVisible(blob.class_name)
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


    def createMapThumbnail(self):

        filename = os.path.join(self.conf.project_dir, self.thumb_map_filename)
        print(filename)
        if not os.path.exists(filename):
            qimg  = QImage(self.image_map_filename)

            qimg_thumb = qimg.scaled(self.MAP_VIEWER_SIZE, self.MAP_VIEWER_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            qimg_thumb.save(filename)

    def resetToolbar(self):

        self.btnMove.setChecked(False)
        self.btnAssign.setChecked(False)
        self.btnEditBorder.setChecked(False)
        self.btnRuler.setChecked(False)
        self.btnCreateCrack.setChecked(False)

        self.btnDeepExtreme.setChecked(False)

    @pyqtSlot()
    def move(self):
        """
        Activate the tool "move".
        """

        self.resetToolbar()
        self.resetTools()

        self.btnMove.setChecked(True)
        self.tool_used = "MOVE"

        self.viewerplus.enablePan()
        self.viewerplus.enableZoom()

        logfile.info("MOVE tool is active")

    @pyqtSlot()
    def createCrack(self):
        """
        Activate the tool "Create Crack".
        """

        self.resetToolbar()
        self.resetTools()

        self.btnCreateCrack.setChecked(True)
        self.tool_used = "CREATECRACK"

        self.viewerplus.enablePan()
        self.viewerplus.enableZoom()

        logfile.info("CREATECRACK tool is active")





    @pyqtSlot(float, float)
    def selectOp(self, x, y):
        """
        Selection operation.
        """

        if not self.tool_used == "DEEPEXTREME":

            selected_blob = self.annotations.clickedBlob(x, y)

            modifiers = QApplication.queryKeyboardModifiers()

            if selected_blob:

                if len(self.selected_blobs) == 0:

                    self.addToSelectedList(selected_blob)

                    self.drawSelectedBlobs()
                    self.updatePanelInfo(selected_blob)

                elif len(self.selected_blobs) > 0:

                    if modifiers != Qt.ShiftModifier:
                        self.resetSelection()

                    self.addToSelectedList(selected_blob)

                    self.drawSelectedBlobs()
                    self.updatePanelInfo(selected_blob)

            else:

                self.resetSelection()


    @pyqtSlot()
    def assign(self):
        """
        Activate the tool "Assign" to assign a class to an existing blob.
        """

        self.resetToolbar()
        self.resetTools()

        self.btnAssign.setChecked(True)
        self.tool_used = "ASSIGN"

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        logfile.info("ASSIGN tool is active")

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
        self.tool_used = "EDITBORDER"

        pen = QPen(Qt.black)
        pen.setWidth(self.BLOB_BORDER_WIDTH)

        self.editborder_qpath = QPainterPath()
        self.editborder_qpath_gitem = self.viewerplus.scene.addPath(self.editborder_qpath, pen, QBrush())

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        logfile.info("EDITBORDER tool is active")


    @pyqtSlot()
    def ruler(self):
        """
        Activate the "ruler" tool. The tool allows to measure the distance between two points or between two blob centroids.
        """

        self.resetToolbar()
        self.resetTools()

        self.btnRuler.setChecked(True)
        self.tool_used = "RULER"

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        logfile.info("RULER tool is active")

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

        self.btnDeepExtreme.setChecked(True)
        self.tool_used = "DEEPEXTREME"

        self.viewerplus.disablePan()
        self.viewerplus.enableZoom()

        logfile.info("DEEPEXTREME tool is active")


    def addToSelectedList(self, blob):
        """
        Add the given blob to the list of selected blob.
        """

        if len(self.selected_blobs) == 0:
            self.selected_blobs.append(blob)
        else:

            if blob in self.selected_blobs:
                pass
            else:
                self.selected_blobs.append(blob)

    @pyqtSlot()
    def noteChanged(self):

        if len(self.selected_blobs) > 0:

            for blob in self.selected_blobs:
                blob.info = self.editNote.toPlainText()

    def updatePanelInfo(self, blob):

        self.editId.setText(blob.blob_name)
        self.editInstance.setText(blob.instace_name)
        self.lblClass.setText(blob.class_name)

        text1 = "Perimeter {:8.2f}".format(blob.perimeter)
        self.lblP.setText(text1)

        text2 = "Area: {:8.2f}".format(blob.area)
        self.lblA.setText(text2)

        self.editNote.setPlainText(blob.info)


    def deleteSelected(self):

        for blob in self.selected_blobs:

            self.viewerplus.scene.removeItem(blob.qpath_gitem)
            blob.qpath_gitem = None

            self.annotations.removeBlob(blob)

        self.selected_blobs.clear()

        logfile.info("Selected blobs has been DELETED")

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


    def drawDeepExtremePoints(self):

        pen = QPen(Qt.blue)
        pen.setWidth(self.CROSS_LINE_WIDTH)
        brush = QBrush(Qt.SolidPattern)
        brush.setColor(Qt.blue)

        X_SIZE = 12

        for blob in self.annotations.seg_blobs:

            ptx = blob.deep_extreme_points[0, 0]
            pty = blob.deep_extreme_points[0, 1]

            line1 = self.viewerplus.scene.addLine(ptx - X_SIZE, pty - X_SIZE, ptx + X_SIZE, pty + X_SIZE, pen)
            line2 = self.viewerplus.scene.addLine(ptx - X_SIZE, pty + X_SIZE, ptx + X_SIZE, pty - X_SIZE, pen)

            ptx = blob.deep_extreme_points[1, 0]
            pty = blob.deep_extreme_points[1, 1]

            line3 = self.viewerplus.scene.addLine(ptx - X_SIZE, pty - X_SIZE, ptx + X_SIZE, pty + X_SIZE, pen)
            line4 = self.viewerplus.scene.addLine(ptx - X_SIZE, pty + X_SIZE, ptx + X_SIZE, pty - X_SIZE, pen)

            ptx = blob.deep_extreme_points[2, 0]
            pty = blob.deep_extreme_points[2, 1]

            line5 = self.viewerplus.scene.addLine(ptx - X_SIZE, pty - X_SIZE, ptx + X_SIZE, pty + X_SIZE, pen)
            line6 = self.viewerplus.scene.addLine(ptx - X_SIZE, pty + X_SIZE, ptx + X_SIZE, pty - X_SIZE, pen)

            ptx = blob.deep_extreme_points[3, 0]
            pty = blob.deep_extreme_points[3, 1]

            line7 = self.viewerplus.scene.addLine(ptx - X_SIZE, pty - X_SIZE, ptx + X_SIZE, pty + X_SIZE, pen)
            line8 = self.viewerplus.scene.addLine(ptx - X_SIZE, pty + X_SIZE, ptx + X_SIZE, pty - X_SIZE, pen)

    def drawGroup(self, group):
        """
        Draw all the blobs of the group with a darkGray border.
        """
        for blob in group.blobs:
            self.drawBlob(blob, selected=False, group_mode=True)

    def drawSelectedBlobs(self):
        """
        Draw all the selected blobs with a white border.
        If a selected blob belongs to a group, the group is highlight using darkGray.
        """

        for blob in self.selected_blobs:
            if blob.group != None:
                self.drawGroup(blob.group)

        for blob in self.selected_blobs:
            self.drawBlob(blob, selected=True)

    def drawBlob(self, blob, selected, group_mode=False):
        """
        Draw a blob according to the class color. If the blob is selected a white border is used.
        Note that if group_mode == True the blob is drawn in darkGray
        and the selection flag is ignored.
        """

        # reset the current graphics item
        if blob.qpath_gitem != None:
            self.viewerplus.scene.removeItem(blob.qpath_gitem)
            blob.qpath_gitem = None

        pen = QPen(Qt.black)
        pen.setWidth(self.BLOB_BORDER_WIDTH)

        if selected == True:

            pen.setColor(Qt.white)

        else:

            if group_mode == True:
                pen.setColor(Qt.lightGray)
            else:
                pen.setColor(Qt.black)

        if blob.class_name == "Empty":

            blob.qpath_gitem = self.viewerplus.scene.addPath(blob.qpath, pen, QBrush())

        else:

            brush = QBrush(Qt.SolidPattern)
            color = self.labels_widget.labels.getColorByName(blob.class_name)
            brush.setColor(QColor(color[0], color[1], color[2], 200))

            blob.qpath_gitem = self.viewerplus.scene.addPath(blob.qpath, pen, brush)
            blob.qpath_gitem.setOpacity(self.transparency_value)

    def drawRuler(self):

        if self.ruler_points_number > 0:

            for line in self.ruler_lines:
                self.viewerplus.scene.removeItem(line)

            if self.ruler_text_gi:
                self.viewerplus.scene.removeItem(self.ruler_text_gi)

            pen = QPen(Qt.blue)
            pen.setWidth(self.CROSS_LINE_WIDTH)
            brush = QBrush(Qt.SolidPattern)
            brush.setColor(Qt.blue)

            X_SIZE = 12

            measure = 0.0
            if self.ruler_points_number == 2:
                measure = self.computeMeasure()

            if self.ruler_points_number == 1:

                x = self.ruler_points[0, 0]
                y = self.ruler_points[0, 1]

                line1 = self.viewerplus.scene.addLine(x - X_SIZE, y - X_SIZE, x + X_SIZE, y + X_SIZE, pen)
                line2 = self.viewerplus.scene.addLine(x - X_SIZE, y + X_SIZE, x + X_SIZE, y - X_SIZE, pen)
                self.ruler_lines.append(line1)
                self.ruler_lines.append(line2)

            if self.ruler_points_number == 2:

                x = self.ruler_points[0, 0]
                y = self.ruler_points[0, 1]

                line1 = self.viewerplus.scene.addLine(x - X_SIZE, y - X_SIZE, x + X_SIZE, y + X_SIZE, pen)
                line2 = self.viewerplus.scene.addLine(x - X_SIZE, y + X_SIZE, x + X_SIZE, y - X_SIZE, pen)
                self.ruler_lines.append(line1)
                self.ruler_lines.append(line2)

                x = self.ruler_points[1, 0]
                y = self.ruler_points[1, 1]

                line3 = self.viewerplus.scene.addLine(x - X_SIZE, y - X_SIZE, x + X_SIZE, y + X_SIZE, pen)
                line4 = self.viewerplus.scene.addLine(x - X_SIZE, y + X_SIZE, x + X_SIZE, y - X_SIZE, pen)
                self.ruler_lines.append(line3)
                self.ruler_lines.append(line4)

                pen.setWidth(4)
                line3 = self.viewerplus.scene.addLine(self.ruler_points[0, 0], self.ruler_points[0, 1],
                                                      self.ruler_points[1, 0],
                                                      self.ruler_points[1, 1], pen)
                self.ruler_lines.append(line3)

                posx = (self.ruler_points[1, 0] + self.ruler_points[0, 0]) / 2.0
                posy = (self.ruler_points[1, 1] + self.ruler_points[0, 1]) / 2.0

                myfont = QFont("Times", 18, QFont.Bold)
                self.ruler_text_gi = self.viewerplus.scene.addText('%.4f' % measure)
                self.ruler_text_gi.setFont(myfont)
                self.ruler_text_gi.setDefaultTextColor(Qt.white)
                self.ruler_text_gi.setPos(posx, posy)


    def union(self):
        """
        blob A = blob A U blob B
        """

        logfile.debug("UNION operation begins..")
        logfile.debug("Number of selected blobs: %d", len(self.selected_blobs))

        if len(self.selected_blobs) == 2:

            logfile.info("UNION operation begins..")

            flag = self.annotations.union(self.selected_blobs)

            if flag:

                blob_to_remove = self.selected_blobs[1]

                self.resetSelection()

                # remove the blob "B"
                self.viewerplus.scene.removeItem(blob_to_remove.qpath_gitem)
                blob_to_remove.qpath_gitem = None
                self.annotations.removeBlob(blob_to_remove)

            else:

                self.resetSelection()

                logfile.debug("Blobs are separated. No union operation done.")

            logfile.info("UNION operations ends.")

        else:

            QMessageBox.information(self, "MERGE OPERATION", "You need to select <em>two</em> blobs for this operation.")


    def subtract(self):
        """
        blob A = blob A / blob B
        """

        if len(self.selected_blobs) == 2:

            blobA = self.selected_blobs[0]
            blobB = self.selected_blobs[1]

            flag_intersection = self.annotations.subtract(blobA, blobB, self.viewerplus.scene)

            self.resetSelection()

            if flag_intersection:

                blob_to_remove = blobB

                # remove the blob "B"
                self.viewerplus.scene.removeItem(blob_to_remove.qpath_gitem)
                blob_to_remove.qpath_gitem = None
                self.annotations.removeBlob(blob_to_remove)

        else:

            QMessageBox.information(self, "SUBTRACT OPERATION", "You need to select <em>two</em> blobs for this operation.")


    def divide(self):
        """
        Separe intersecting blob
        """

        if len(self.selected_blobs) == 2:

            blobA = self.selected_blobs[0]
            blobB = self.selected_blobs[1]

            is_empty = self.annotations.subtract(blobB, blobA, self.viewerplus.scene)

            self.resetSelection()

        else:

            QMessageBox.information(self, "DIVIDE OPERATION", "You need to select <em>two</em> blobs for this operation.")

    def group(self):

        if len(self.selected_blobs) > 0:

            group = self.annotations.addGroup(self.selected_blobs)
            self.drawGroup(group)

    def ungroup(self):

        if len(self.selected_blobs) > 0:

            blob_s = self.selected_blobs[0]

            if blob_s.group != None:

                # de-selection
                for blob in self.selected_blobs:
                    self.drawBlob(blob, selected=False)
                self.selected_blobs.clear()

                self.annotations.removeGroup(blob_s.group)

    def resetSelection(self):

        # if there are selected blobs they should be drawn as de-selected
        blobs_to_deselect = set()
        for blob in self.selected_blobs:
            if blob.group:
                for blobg in blob.group.blobs:
                    blobs_to_deselect.add(blobg)
            else:
                blobs_to_deselect.add(blob)

        for blob in blobs_to_deselect:
            self.drawBlob(blob, selected=False)

        self.selected_blobs.clear()

    def resetEditBorder(self):

        if self.editborder_qpath_gitem != None:
            self.editborder_qpath = QPainterPath()
            self.editborder_qpath_gitem.setPath(self.editborder_qpath)
        else:
            self.editborder_qpath = None

        self.editborder_points = np.array(())

    def resetCrackTool(self):

        if self.crackWidget is not None:
            self.crackWidget.close()

        self.crackWidget = None

        # panning of the crack preview cause some problems..
        self.viewerplus.setDragMode(QGraphicsView.NoDrag)


    def resetRulerTool(self):

        for line in self.ruler_lines:
            self.viewerplus.scene.removeItem(line)

        if self.ruler_text_gi:
            self.viewerplus.scene.removeItem(self.ruler_text_gi)

        self.ruler_points = np.zeros((2, 2))

        self.ruler_points_number = 0
        self.ruler_points = np.zeros((2, 2))


    def resetDeepExtremeTool(self):

        for line in self.extreme_points_lines:
            self.viewerplus.scene.removeItem(line)

        self.extreme_points_lines.clear()
        self.extreme_points_number = 0
        self.extreme_points = np.zeros((4, 2))


    def resetTools(self):

        self.resetEditBorder()
        self.resetCrackTool()
        self.resetRulerTool()
        self.resetDeepExtremeTool()


    @pyqtSlot(float, float)
    def toolsOpsLeftPressed(self, x, y):

        modifiers = QApplication.queryKeyboardModifiers()

        if self.tool_used == "ASSIGN" and modifiers != Qt.ControlModifier:

            selected_blob = self.annotations.clickedBlob(x, y)

            if selected_blob is not None:

                if not self.isSelected(selected_blob):

                    self.resetSelection()
                    self.addToSelectedList(selected_blob)

                for blob in self.selected_blobs:

                    blob.class_name = self.labels_widget.getActiveLabelName()
                    blob.class_color = self.labels_widget.getActiveLabelColor()

                    self.viewerplus.scene.removeItem(blob.qpath_gitem)
                    blob.qpath_gitem = None

                    self.drawBlob(blob, selected=True)

        elif self.tool_used == "EDITBORDER" and modifiers != Qt.ControlModifier:

            if len(self.selected_blobs) == 1:

                logfile.info("EDITBORDER drawing")

                if len(self.editborder_points) == 0:

                    self.editborder_points = np.array([[x, y]])

                    pen = QPen(Qt.black)
                    pen.setJoinStyle(Qt.MiterJoin)
                    pen.setCapStyle(Qt.RoundCap)
                    pen.setWidth(self.BLOB_BORDER_WIDTH)

                    if self.editborder_qpath == None:
                        self.editborder_qpath = QPainterPath()

                    self.editborder_qpath.moveTo(QPointF(x, y))

                    if self.editborder_qpath_gitem == None:
                        self.editborder_qpath_gitem = self.viewerplus.scene.addPath(self.editborder_qpath, pen, QBrush())
                    else:
                        self.editborder_qpath_gitem.setPath(self.editborder_qpath)

                    logfile.debug("Number of EDITBORDER points: %d", self.editborder_points.shape[0])

                else:

                    self.editborder_points = np.append(self.editborder_points, [[x, y]], axis=0)
                    self.editborder_qpath.lineTo(QPointF(x, y))
                    self.editborder_qpath_gitem.setPath(self.editborder_qpath)

                    logfile.debug("Number of EDITBORDER points: %d", self.editborder_points.shape[0])
            else:

                logfile.info("Invalid EDITBORDER drawing (no blob selected) (!)")

        elif self.tool_used == "CREATECRACK":

            selected_blob = self.annotations.clickedBlob(x, y)

            if selected_blob is not None:

                self.resetSelection()
                self.addToSelectedList(selected_blob)

                xpos = self.viewerplus.clicked_x
                ypos = self.viewerplus.clicked_y

                if self.crackWidget is None:
                    self.crackWidget = QtCrackWidget(self.img_map, selected_blob, x, y, parent=self)
                    self.crackWidget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
                    self.crackWidget.setWindowModality(Qt.WindowModal)
                    self.crackWidget.btnCancel.clicked.connect(self.crackCancel)
                    self.crackWidget.btnApply.clicked.connect(self.crackApply)
                    self.crackWidget.closeCrackWidget.connect(self.crackCancel)
                    self.crackWidget.show()

        elif self.tool_used == "RULER" and modifiers != Qt.ControlModifier:

            if self.ruler_points_number < 2:

                ind = self.ruler_points_number
                self.ruler_points[ind, 0] = x
                self.ruler_points[ind, 1] = y
                self.ruler_points_number += 1

                self.drawRuler()

            else:

                self.resetRulerTool()

        elif self.tool_used == "DEEPEXTREME":

            if self.extreme_points_number < 4 and modifiers != Qt.ControlModifier:

                ind = self.extreme_points_number
                self.extreme_points[ind, 0] = x
                self.extreme_points[ind, 1] = y
                self.extreme_points_number += 1

                pen = QPen(Qt.red)
                pen.setWidth(self.CROSS_LINE_WIDTH)
                brush = QBrush(Qt.SolidPattern)
                brush.setColor(Qt.red)

                X_SIZE = 12
                line1 = self.viewerplus.scene.addLine(x - X_SIZE, y - X_SIZE, x + X_SIZE, y + X_SIZE, pen)
                line2 = self.viewerplus.scene.addLine(x - X_SIZE, y + X_SIZE, x + X_SIZE, y - X_SIZE, pen)
                self.extreme_points_lines.append(line1)
                self.extreme_points_lines.append(line2)

            elif self.extreme_points_number > 3:

                self.resetDeepExtremeTool()

    @pyqtSlot(float, float)
    def toolsOpsLeftReleased(self, x, y):
        pass

    @pyqtSlot(float, float)
    def toolsOpsRightPressed(self, x, y):
        pass

    @pyqtSlot(float, float)
    def toolsOpsMouseMove(self, x, y):

        if not (QApplication.keyboardModifiers() & Qt.ControlModifier):

            if self.tool_used == "EDITBORDER":

                logfile.info("EDIBORDER moving")

                if len(self.editborder_points) > 0:

                    self.editborder_points = np.append(self.editborder_points, [[x, y]], axis=0)
                    self.editborder_qpath.lineTo(QPointF(x,y))
                    self.editborder_qpath_gitem.setPath(self.editborder_qpath)

                    logfile.debug("Number of EDITBORDER points: %d", self.editborder_points.shape[0])


    @pyqtSlot()
    def crackCancel(self):

        self.resetCrackTool()

    @pyqtSlot()
    def crackApply(self):

        self.crackWidget.apply()

        self.drawBlob(self.selected_blobs[0], selected=True)

        self.resetCrackTool()

    def computeMeasure(self):
        """
        It computes the measure between two points. If this point lies inside two blobs
        the distance between the centroids is computed.
        """

        x1 = self.ruler_points[0, 0]
        y1 = self.ruler_points[0, 1]
        x2 = self.ruler_points[1, 0]
        y2 = self.ruler_points[1, 1]

        blob1 = self.annotations.clickedBlob(x1, y1)
        blob2 = self.annotations.clickedBlob(x2, y2)

        if blob1 is not None and blob2 is not None and blob1 != blob2:

            x1 = blob1.centroid[0]
            y1 = blob1.centroid[1]
            x2 = blob2.centroid[0]
            y2 = blob2.centroid[1]

            self.ruler_points[0, 0] = x1
            self.ruler_points[0, 1] = y1
            self.ruler_points[1, 0] = x2
            self.ruler_points[1, 1] = y2

        measurepx = np.sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2))

        scale = 1.0 # just to remember to adjust the scale for each map
        measure = measurepx * scale

        return measure

    @pyqtSlot()
    def loadAnnotations(self):

        annotation_files = glob.glob(os.path.join(self.conf.project_dir, "annotations*"))
        nfiles = len(annotation_files)

        if nfiles > 0:

            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.annotationFileId = nfiles - 1

            filename = "annotations{:04d}.dat".format(self.annotationFileId)
            fullname = os.path.join(self.conf.project_dir, filename)
            self.annotations.load(fullname)

            print("Annotations loaded.")

            # draw all blobs loaded
            for blob in self.annotations.seg_blobs:
                self.drawBlob(blob, selected=False)

            QApplication.restoreOverrideCursor()


        else:

            print("No data files (!)")


    @pyqtSlot()
    def saveAnnotations(self):

        QApplication.setOverrideCursor(Qt.WaitCursor)

        annotation_files = glob.glob(os.path.join(self.conf.project_dir, "annotations*"))
        nfiles = len(annotation_files)

        self.annotationFileId = nfiles
        filename = "annotations{:04d}.dat".format(self.annotationFileId)
        fullname = os.path.join(self.conf.project_dir, filename)
        self.annotations.save(fullname)

        print("Annotations saved.")

        QApplication.restoreOverrideCursor()

    @pyqtSlot()
    def exportData(self):

        exportWidget = QtExportWidget(self.img_map, self.annotations, parent=self)
        exportWidget.setWindowFlags(Qt.Window)
        exportWidget.setWindowModality(Qt.WindowModal)
        exportWidget.show()

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


    def segmentWithDeepExtreme(self):

        pad = 50
        thres = 0.8
        gpu_id = 0
        device = torch.device("cuda:" + str(gpu_id) if torch.cuda.is_available() else "cpu")
        self.deepextreme_net.to(device)

        extreme_points_to_use = self.extreme_points.astype(int)
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

            blobs = self.annotations.addBlob(segm_mask, left_map_pos, top_map_pos, area_extreme_points)

            for blob in blobs:
                blob.deep_extreme_points = extreme_points_to_use

            self.resetSelection()
            for blob in blobs:
                self.addToSelectedList(blob)
                self.drawBlob(blob, selected=True)

    def automaticSegmentation(self):

        self.img_overlay = QImage(self.conf.segmentation_map_filename)
        self.viewerplus.setOverlayImage(self.img_overlay)

if __name__ == '__main__':

    # Create the QApplication.
    app = QApplication(sys.argv)

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

    # Read default configuration
    conf = Configuration()

    # Create the inspection tool
    tool = LabelLab(conf)

    # Show the viewer and run the application.
    tool.show()
    sys.exit(app.exec_())
