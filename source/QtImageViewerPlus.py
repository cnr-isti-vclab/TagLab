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

""" PyQt image viewer widget for a QPixmap in a QGraphicsView scene with mouse zooming and panning.
    The viewer has also drawing capabilities (differently from QTimage viewer).
"""

import os.path
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QLineF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QPen, QColor, QFont, QBrush
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QFileDialog, QGraphicsItem, QGraphicsSimpleTextItem, QPlainTextEdit,QSizePolicy

from source.Undo import Undo
from source.Project import Project
from source.Image import Image
from source.Annotation import Annotation
from source.Point import Point
from source.Annotation import Blob
from source.Tools import Tools
from source.Label import Label

from source.QtImageViewer import QtImageViewer

from source.genutils import distance_point_AABB

import math
import time

#note on ZValue:
# 0: image
# 1: blobs
# 2: blob text
# 3: selected blobs
# 4: selected blob text
# 5: pick points and tools



class TextItem(QGraphicsSimpleTextItem):
    def __init__(self, text, font):
        QGraphicsSimpleTextItem.__init__(self)
        self.setText(text)
        self.setFont(font)

    def paint(self, painter, option, widget):
        painter.translate(self.boundingRect().topLeft())
        super().paint(painter, option, widget)
        painter.translate(-self.boundingRect().topLeft())

    def boundingRect(self):
        b = super().boundingRect()
        return QRectF(b.x()-b.width()/2.0, b.y()-b.height()/2.0, b.width(), b.height())


class NoteWidget(QPlainTextEdit):

    editFinishing = pyqtSignal()

    def __init__(self, parent):
        super(QPlainTextEdit, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setFixedWidth(200)
        self.setFixedHeight(60)
        self.setWordWrapMode(True)
        self.autoFillBackground()
        self.setWindowTitle("Enter note below and press TAB")
        self.setWindowFlags(Qt.ToolTip | Qt.CustomizeWindowHint | Qt.WA_Hover)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            self.editFinishing.emit()
        else:
            QPlainTextEdit.keyPressEvent(self, event)


#TODO: crackwidget uses qimageviewerplus to draw an image.
#circular dependency. create a viewer and a derived class which also deals with the rest.
class QtImageViewerPlus(QtImageViewer):
    """
    PyQt image viewer widget with annotation capabilities.
    QGraphicsView handles a scene composed by an image plus shapes (rectangles, polygons, blobs).
    The input image (it must be a QImage) is internally converted into a QPixmap.
    """

    # Mouse button signals emit image scene (x, y) coordinates.
    leftMouseButtonPressed = pyqtSignal(float, float)
    rightMouseButtonPressed = pyqtSignal(float, float)
    leftMouseButtonReleased = pyqtSignal(float, float)
    rightMouseButtonReleased = pyqtSignal(float, float)
    #leftMouseButtonDoubleClicked = pyqtSignal(float, float)
    rightMouseButtonDoubleClicked = pyqtSignal(float, float)
    mouseMoveLeftPressed = pyqtSignal(float, float)
    mouseMoved = pyqtSignal(float, float)
    selectionChanged = pyqtSignal()
    selectionReset = pyqtSignal()

    # custom signal
    updateInfoPanel = pyqtSignal(object)

    activated = pyqtSignal()
    newSelection = pyqtSignal()
    newSelectionPoint = pyqtSignal()
    activeImageChanged = pyqtSignal(Image)
    
    messageSignal = pyqtSignal(str)

    def __init__(self, taglab_dir):
        QtImageViewer.__init__(self)

        self.logfile = None #MUST be inited in Taglab.py
        self.project = Project()
        self.image = None
        self.channel = None
        self.annotations = Annotation()

        self.layers = []
        self.selected_blobs = []
        self.selected_annpoints = []
        self.selected_sampling_area = None

        self.taglab_dir = taglab_dir
        self.tools = Tools(self)
        self.tools.createTools()

        self.undo_data = Undo()

        self.dragSelectionStart = None
        self.dragSelectionRect = None
        self.dragSelectionStyle = QPen(Qt.white, 1, Qt.DashLine)
        self.dragSelectionStyle.setCosmetic(True)

        # Set scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # DRAWING SETTINGS
        self.fill_enabled = True
        self.border_enabled = True
        self.ids_enable = True

        self.show_grid = False

        self.border_pen = QPen(Qt.black, 3)
        self.border_pen.setCosmetic(True)
        self.border_selected_pen = QPen(Qt.white, 3)
        self.border_selected_pen.setCosmetic(True)

        self.annpoints_pen = QPen(Qt.black, 3)
        self.annpoints_pen.setCosmetic(True)
        self.annpoints_pen_selected = QPen(Qt.white, 3)
        self.annpoints_pen_selected.setCosmetic(True)

        self.sampling_pen = QPen(Qt.yellow, 3)
        self.sampling_pen.setCosmetic(True)
        self.sampling_brush = QBrush(Qt.yellow)
        self.sampling_brush.setStyle(Qt.CrossPattern)

        self.markers_pen = QPen(Qt.cyan, 3)
        self.markers_pen.setCosmetic(True)
        self.markers_brush = QBrush(Qt.cyan)
        self.markers_brush.setStyle(Qt.SolidPattern)

        self.working_area_pen = QPen(Qt.green, 3, Qt.DashLine)
        self.working_area_pen.setCosmetic(True)

        self.sampling_area_pen = QPen(Qt.yellow, 2, Qt.DashLine)
        self.sampling_area_pen.setCosmetic(True)
        self.sampling_area_pen_selected = QPen(Qt.white, 2)
        self.sampling_area_pen_selected.setCosmetic(True)

        self.showCrossair = False
        self.mouseCoords = QPointF(0.0, 0.0)
        self.crackWidget = None
        self.bricksWidget = None
        self.struct_widget = None

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.transparency_value = 0.5

        self.refine_grow = 0.0 #maybe should in in tools
        self.refine_original_mask = None
        self.refine_original_blob = None
        self.active_label = None

        # scale bar
        self.scalebar_text = None
        self.scalebar_line = None
        self.scalebar_line2 = None
        self.scalebar_line3 = None
        self.setupScaleBar()

        # working area
        self.working_area_rect = None

        # sampling areas
        self.sampling_rect_items = []

        # tools - additional initialization
        self.tools.tools["SELECTAREA"].setWorkingAreaStyle(self.working_area_pen)

    def setProject(self, project):

        self.project = project

    def setImage(self, image, channel_idx=0):
        """
        Set the image to visualize. The first channel is visualized unless otherwise specified.
        """

        self.undrawAllLayers()
        self.image = image
        self.annotations = image.annotations
        self.selected_blobs = []
        self.selected_annpoints =[]
        self.selectionChanged.emit()
        #clear existing layers

        # draw all the annotations
        self.drawAllBlobs()
        self.drawAllPoints()
        self.updateVisibility()

        # draw the layers
        self.drawAllLayers()

        # draw the working area (if defined)
        self.drawWorkingArea()

        # draw the sampling areas (if any)
        self.drawSamplingAreas()

        # draw the grid (if defined)
        self.showGrid()

        self.scene.invalidate()
        self.px_to_mm = image.pixelSize()
        self.setChannel(image.channels[channel_idx])

        self.activeImageChanged.emit(self.image)
        self.activated.emit()

    def toggleAnnotations(self, type, enable):

        if type == "regions":
            for blob in self.annotations.seg_blobs:
                if enable:
                    self.drawBlob(blob)
                else:
                    self.undrawBlob(blob)
        else:
            for point in self.annotations.annpoints:
                if enable:
                    self.drawPointAnn(point)
                else:
                    self.undrawAnnPoint(point)

    def updateImageProperties(self):
        """
        The properties of the image have been changed. This function updates the viewer accordingly.
        NOTE: In practice, only the pixel size needs to be updated.
        """
        self.px_to_mm = self.image.pixelSize()


    def setChannel(self, channel, switch=False):
        """
        Set the image channel to visualize. If the channel has not been previously loaded it is loaded and cached.
        """

        if self.image is None:
            raise("Image has not been previously set in ViewerPlus")

        self.channel = channel

        if channel.qimage is not None:
            img = channel.qimage
        else:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            img = channel.loadData(self.taglab_dir)
            QApplication.restoreOverrideCursor()

        if img.isNull():
            (filename, filter) = QFileDialog.getOpenFileName(self, "Couldn't find the map, please select it:",
                                                                       QFileInfo(channel.filename).dir().path(),
                                                                       "Image Files (*.png *.jpg *.jpeg)")
            dir = QDir(self.taglab_dir)
            channel.filename = dir.relativeFilePath(filename)

            QApplication.setOverrideCursor(Qt.WaitCursor)
            img = channel.loadData(self.taglab_dir)
            QApplication.restoreOverrideCursor()

            if img.isNull():
                raise Exception("Could not load or find the image: " + filename)

        if switch:
            self.setChannelImg(img, self.zoom_factor)
        else:
            self.setChannelImg(img)

    def setChannelImg(self, channel_img, zoomf=0.0):
        """
        Set the scene's current image (input image must be a QImage)
        For calculating the zoom factor automatically set it to 0.0.
        """
        self.setImg(channel_img, zoomf)

    def clear(self):

        # clear selection and undo
        self.selected_blobs = []
        self.selected_annpoints = []
        self.selectionChanged.emit()
        self.undo_data = Undo()
        self.undrawAllLayers()

        # undraw all blobs
        for blob in self.annotations.seg_blobs:
            self.undrawBlob(blob)
            del blob

        for annpoint in self.annotations.annpoints:
            self.undrawAnnPoint(annpoint)
            del annpoint

        # clear working area
        self.undrawWorkingArea()

        # clear sampling areas
        self.undrawSamplingAreas()

        if self.image is not None:
            if self.image.grid is not None:
                self.image.grid.undrawGrid()

        self.hideGrid()
        # undraw and clear current image and channel
        QtImageViewer.clear(self)
        self.image = None
        self.channel = None

        # clear annotation data
        self.annotations = Annotation()
        
        # no project is set
        self.project = None

    def setupScaleBar(self):

        LENGTH_IN_PIXEL = 100
        LENGTH_VLINES = 5

        w = self.viewport().width()
        h = self.viewport().height()
        posx = int(w * 0.8)
        posy = int(h * 0.9)

        self.scene_overlay.setSceneRect(0,0,w,h)

        pt1 = QPoint(posx, posy)
        pt2 = QPoint(posx + 100, posy)

        self.scalebar_text = self.scene_overlay.addText('PROVA!')
        self.scalebar_text.setDefaultTextColor(QColor(Qt.white))
        font = self.scalebar_text.font()
        font.setBold(True)
        self.scalebar_text.setFont(font)
        self.scalebar_text.setPos(pt1.x(), pt1.y())
        self.scalebar_text.setZValue(5)
        self.scalebar_text.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        pen = QPen(Qt.white)
        pen.setWidth(3)
        pen.setCosmetic(True)
        self.scalebar_line = self.scene_overlay.addLine(pt1.x(), pt1.y(), pt2.x(), pt2.y(), pen)
        self.scalebar_line.setZValue(5)

        self.scalebar_line2 = self.scene_overlay.addLine(pt1.x(), pt1.y()-LENGTH_VLINES, pt1.x(), pt1.y()+LENGTH_VLINES, pen)
        self.scalebar_line2.setZValue(5)

        self.scalebar_line3 = self.scene_overlay.addLine(pt2.x(), pt2.y()-LENGTH_VLINES, pt2.x(), pt2.y()+LENGTH_VLINES, pen)
        self.scalebar_line3.setZValue(5)

        self.hideScalebar()

    def showScalebar(self):
        self.scalebar_text.show()
        self.scalebar_line.show()
        self.scalebar_line2.show()
        self.scalebar_line3.show()

    def hideScalebar(self):
        self.scalebar_text.hide()
        self.scalebar_line.hide()
        self.scalebar_line2.hide()
        self.scalebar_line3.hide()

    def drawWorkingArea(self):

        wa = self.project.working_area  # top, left, width, height

        if wa is not None:
          if len(wa) == 4 and wa[2] > 0 and wa[3] > 0:
                if self.working_area_rect is None:
                    self.working_area_rect = self.scene.addRect(wa[1], wa[0], wa[2], wa[3], self.working_area_pen)
                    self.working_area_rect.setZValue(6)
                else:
                    self.working_area_rect.setRect(wa[1], wa[0], wa[2], wa[3])

    def undrawWorkingArea(self):

        if self.working_area_rect is not None:
            self.scene.removeItem(self.working_area_rect)
            self.working_area_rect = None

    def showGrid(self):

        if self.image is not None:
            if self.image.grid is not None:
                if not self.image.grid.grid_rects:
                    # the grid has never been drawn
                    self.image.grid.setScene(self.scene)
                    self.image.grid.drawGrid()
                self.image.grid.setVisible(True)
                self.show_grid = True
            else:
                self.show_grid = False

    def hideGrid(self):

        if self.image is not None:
            if self.image.grid is not None:
                self.image.grid.setVisible(False)

        self.show_grid = False

    @pyqtSlot(int)
    def toggleGrid(self, check):

        if check == 0:
            self.hideGrid()
        else:
            self.showGrid()

    def enableFill(self):

        for blob in self.annotations.seg_blobs:
            brush = self.project.classBrushFromName(blob)
            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setBrush(brush)

        self.fill_enabled = True

    def disableFill(self):

        for blob in self.annotations.seg_blobs:
            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setBrush(QBrush(Qt.NoBrush))

        self.fill_enabled = False

    @pyqtSlot(int)
    def toggleFill(self, checked):

        if checked == 0:
            self.disableFill()
        else:
            self.enableFill()

    def enableBorders(self):

        for blob in self.annotations.seg_blobs:
            pen = self.border_selected_pen if blob in self.selected_blobs else self.border_pen
            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setPen(pen)

        self.border_enabled = True

    def disableBorders(self):

        for blob in self.annotations.seg_blobs:
            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setPen(QPen(Qt.NoPen))

        self.border_enabled = False

    @pyqtSlot(int)
    def toggleBorders(self, checked):

        if checked == 0:
            self.disableBorders()
        else:
            self.enableBorders()

    def enableIds(self):

        for blob in self.annotations.seg_blobs:
            if blob.id_item is not None:
                blob.id_item.setVisible(True)

        self.ids_enabled = True

    def disableIds(self):

        for blob in self.annotations.seg_blobs:
            if blob.id_item is not None:
                blob.id_item.setVisible(False)

        self.ids_enabled = False

    @pyqtSlot(int)
    def toggleIds(self, checked):

        if checked == 0:
            self.disableIds()
        else:
            self.enableIds()

    def drawAllLayers(self):
        for layer in self.image.layers:
            if layer.isEnabled():
                self.drawLayer(layer)
            else:
                self.undrawLayer(layer)

    def undrawAllLayers(self):
        if self.image != None:
            for layer in self.image.layers:
                self.undrawLayer(layer)


    def drawLayer(self, layer):
        for shape in layer.shapes:
            self.drawShape(shape, layer.type)

    def undrawLayer(self, layer):
        for shape in layer.shapes:
            self.undrawShape(shape)

    def drawAllPointsAnn(self):

        for annpoint in self.annotations.annpoints:
            self.drawPointAnn(annpoint)

    def drawSamplingAreas(self):

        # undraw the existing sampling area before re-draw them
        self.undrawSamplingAreas()

        for sampling_area in self.image.sampling_areas:
            x = float(sampling_area[1])
            y = float(sampling_area[0])
            w = float(sampling_area[2])
            h = float(sampling_area[3])
            if sampling_area == self.selected_sampling_area:
                rect_item = self.scene.addRect(x, y, w, h, self.sampling_area_pen_selected)
            else:
                rect_item = self.scene.addRect(x, y, w, h, self.sampling_area_pen)

            self.sampling_rect_items.append(rect_item)

    def undrawSamplingAreas(self):

        for rect_item in self.sampling_rect_items:
            self.scene.removeItem(rect_item)

        self.sampling_rect_items = []

    def drawselectedAnnPoints(self):

        for annpoint in self.annotations.annpoints:
            pen = self.annpoints_pen_selected if annpoint in self.selected_annpoints else self.annpoints_pen
            if annpoint.cross1_gitem is not None:

                annpoint.cross1_gitem.setPen(pen)
                annpoint.cross2_gitem.setPen(pen)
                annpoint.ellipse_gitem.setPen(pen)


    def drawPointAnn(self, annpoint):

        # if the graphics item has just been create we remove it to set it again
        if annpoint.cross1_gitem is not None:
            self.scene.removeItem(annpoint.cross1_gitem)
            self.scene.removeItem(annpoint.cross2_gitem)
            self.scene.removeItem(annpoint.ellipse_gitem)
            self.scene.removeItem(annpoint.id_item)

            del annpoint.cross1_gitem
            annpoint.cross1_gitem = None

            del annpoint.cross2_gitem
            annpoint.cross2_gitem = None

            del annpoint.ellipse_gitem
            annpoint.ellipse_gitem = None

        #choose a pen
        pen = self.annpoints_pen_selected if annpoint in self.selected_annpoints else self.annpoints_pen
        brush = self.project.classBrushFromName(annpoint)
        annpoint.ellipse_gitem = self.scene.addEllipse(annpoint.coordx - 10, annpoint.coordy - 10, 20, 20, pen,brush)
        annpoint.cross1_gitem = self.scene.addLine(annpoint.coordx - 1, annpoint.coordy, annpoint.coordx +1, annpoint.coordy, pen )
        annpoint.cross2_gitem = self.scene.addLine(annpoint.coordx, annpoint.coordy-1, annpoint.coordx,
                                                  annpoint.coordy+1, pen)


        annpoint.cross1_gitem.setZValue(1)
        annpoint.cross2_gitem.setZValue(1)
        annpoint.ellipse_gitem.setZValue(1)

        annpoint.cross1_gitem.setOpacity(self.transparency_value)
        annpoint.cross2_gitem.setOpacity(self.transparency_value)
        annpoint.ellipse_gitem.setOpacity(self.transparency_value)


        font_size = min(12, round(6.0 / self.image.pixelSize()))
        annpoint.id_item = TextItem(str(annpoint.id), QFont("Roboto", font_size, QFont.Bold))
        annpoint.id_item.setPos(annpoint.coordx+ 20, annpoint.coordy+ 20)
        annpoint.id_item.setZValue(2)
        annpoint.id_item.setBrush(Qt.white)
        #
        if annpoint in self.selected_annpoints:
            annpoint.id_item.setOpacity(1.0)
        else:
            annpoint.id_item.setOpacity(0.7)

        self.scene.addItem(annpoint.id_item)


    def drawShape(self, shape, layer_type):

        if shape.type == "point":

            # if the graphics item has just been create we remove it to set it again
            if shape.qpath_gitem is not None:
                self.scene.removeItem(shape.point_gitem)
                del shape.point_gitem
                shape.point_gitem = None

            pen = QPen(Qt.white, 3)
            pen.setCosmetic(True)
            brush = QBrush(Qt.red)
            brush.setStyle(Qt.SolidPattern)

            x = shape.outer_contour[0][0]
            y = shape.outer_contour[0][1]
            shape.point_gitem = self.scene.addEllipse(x - 5, y - 5, 10, 10, pen, brush)

        elif shape.type == "polygon":

            # if the graphics item has just been create we remove it to set it again
            if shape.qpath_gitem is not None:
                self.scene.removeItem(shape.qpath_gitem)
                del shape.qpath_gitem
                shape.qpath_gitem = None


            shape.setupForDrawing()

            if layer_type == "Sampling":
                pen = self.sampling_pen
                brush = self.sampling_brush
            else:
                pen = self.markers_pen
                brush = self.markers_brush

            shape.qpath_gitem = self.scene.addPath(shape.qpath, pen, brush)
            shape.qpath_gitem.setZValue(1)
            shape.qpath_gitem.setOpacity(self.transparency_value)

    def undrawShape(self, shape):

        if shape.type == "point":
            if shape.point_gitem is not None:
                self.scene.removeItem(shape.point_gitem)
        elif shape.type == "polygon":
            if shape.qpath_gitem is not None:
                self.scene.removeItem(shape.qpath_gitem)
                shape.qpath = None
                shape.qpath_gitem = None

        self.scene.invalidate()

    def drawBlob(self, blob):

        # if it has just been created remove the current graphics item in order to set it again
        if blob.qpath_gitem is not None:
            self.scene.removeItem(blob.qpath_gitem)
            self.scene.removeItem(blob.id_item)
            del blob.qpath_gitem
            del blob.id_item
            blob.qpath_gitem = None
            blob.id_item = None

        blob.setupForDrawing()
        pen = self.border_selected_pen if blob in self.selected_blobs else self.border_pen

        brush = self.project.classBrushFromName(blob)
        blob.qpath_gitem = self.scene.addPath(blob.qpath, pen, brush)
        blob.qpath_gitem.setZValue(1)
        blob.qpath_gitem.setOpacity(self.transparency_value)

        font_size = min(12, round(8.0 / self.image.pixelSize()))
        blob.id_item = TextItem(str(blob.id),  QFont("Roboto", font_size, QFont.Bold))
        blob.id_item.setPos(blob.centroid[0], blob.centroid[1])
        blob.id_item.setTransformOriginPoint(QPointF(blob.centroid[0] + 14.0, blob.centroid[1] + 14.0))
        blob.id_item.setZValue(2)
        blob.id_item.setBrush(Qt.white)

        if blob in self.selected_blobs:
            blob.id_item.setOpacity(1.0)
        else:
            blob.id_item.setOpacity(0.7)
        self.scene.addItem(blob.id_item)

    def undrawBlob(self, blob, redraw=True):

        self.scene.removeItem(blob.qpath_gitem)
        self.scene.removeItem(blob.id_item)
        blob.qpath = None
        blob.qpath_gitem = None
        blob.id_item = None

        if redraw:
            self.scene.invalidate()

    def undrawAnnPoint(self, annpoint, redraw=True):

        self.scene.removeItem(annpoint.cross1_gitem)
        self.scene.removeItem(annpoint.cross2_gitem)
        self.scene.removeItem(annpoint.ellipse_gitem)
        self.scene.removeItem(annpoint.id_item)
        annpoint.cross1_gitem = None
        annpoint.cross2_gitem = None
        annpoint.ellipse_gitem = None
        annpoint.id_item = None

        if redraw:
            self.scene.invalidate()

    def applyTransparency(self, value):

        self.transparency_value = 1.0 - (value / 100.0)
        # current annotations
        for blob in self.annotations.seg_blobs:
            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setOpacity(self.transparency_value)

        for annpoint in self.annotations.annpoints:
            if annpoint.cross1_gitem is not None:
               annpoint.cross1_gitem.setOpacity(self.transparency_value)
               annpoint.cross2_gitem.setOpacity(self.transparency_value)
               annpoint.ellipse_gitem.setOpacity(self.transparency_value)


    def drawAllBlobs(self):

        for blob in self.annotations.seg_blobs:
            self.drawBlob(blob)

    def drawAllPoints(self):

        for point in self.annotations.annpoints:
            self.drawPointAnn(point)

    #used for crossair cursor
    def drawForeground(self, painter, rect):
        if self.showCrossair:
            painter.setClipRect(rect)
            pen = QPen(Qt.white, 1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLine(QLineF(self.mouseCoords.x(), rect.top(), self.mouseCoords.x(), rect.bottom()))
            painter.drawLine(QLineF(rect.left(), self.mouseCoords.y(), rect.right(), self.mouseCoords.y()))


#TOOLS and SELECTIONS

    def setTool(self, tool):

        if not self.isVisible():
            return

        QApplication.setOverrideCursor(Qt.ArrowCursor)

        self.tools.setTool(tool)

        #calls the toolMessage method to show the tool message window        
        self.tools.toolMessage()

        if tool in ["FREEHAND", "RULER", "FOURCLICKS", "PLACEANNPOINT"] or (tool in ["CUT", "EDITBORDER", "RITM"] and len(self.selected_blobs) > 1):
            self.resetSelection()

        if tool == "RITM" or tool == "SAMINTERACTIVE" or tool == "WATERSHED":
            self.setContextMenuPolicy(Qt.NoContextMenu)
        else:
            self.setContextMenuPolicy(Qt.CustomContextMenu)

        if tool == "SELECTAREA" or tool == "RITM" or tool == "RULER":
            QApplication.setOverrideCursor(Qt.CrossCursor)

        if tool == "WATERSHED":
            self.tools.tools["WATERSHED"].scribbles.setScaleFactor(self.zoom_factor)
            self.tools.tools["WATERSHED"].setActiveLabel(self.project.labels.get(self.active_label if (self.active_label is not None) else "Empty"))

        if tool == "FOURCLICKS" or tool == "PLACEANNPOINT":
            self.showCrossair = True
        else:
            self.showCrossair = False

        # WHEN panning is active or not
        # if tool == "MOVE" or tool == "MATCH" or tool == "FOURCLICKS" or tool == "RITM" or tool == "PLACEANNPOINT":
        #     self.enablePan()
        # else:
        #     self.disablePan()  # in this case, it is possible to PAN only moving the mouse and pressing the CTRL key

        if tool == "SAM":
        #     #QUIRINI: calls methods to set the window cursor for the SAM tool
        #     self.tools.tools["SAM"].setScaleFactor(self.zoom_factor)
        #     self.tools.tools["SAM"].setSize()
        #     # self.tools.tools["SAM"].setCustomCursor()
            # self.disableZoom()
            self.tools.enableSAM()
        else:
            self.tools.disableSAM()

        if tool == "SAMINTERACTIVE":
            self.tools.enableSAMInteractive()
        else:
            self.tools.disableSAMInteractive()

        # if tool == "ROWS":
        #     self.tools.enableRows()
        # else:
        #     self.tools.disableRows()

    def resetTools(self):

        self.tools.resetTools()

        if self.tools.tool == "FOURCLICKS" or self.tools.tool == "PLACEANNPOINT":
            self.showCrossair = True
        else:
            self.showCrossair = False

        self.scene.invalidate(self.scene.sceneRect())
        self.setDragMode(QGraphicsView.NoDrag)

    @pyqtSlot(float, float)
    def selectOp(self, x, y):
        """
        Selection operation. Note that both the areas and the points are selected.

        Note that if multiple objects are clicked one single object is selected according to the following priorities:

        - sampling area + region -> sampling area
        - region + point -> point
        - region + point + sampling area -> point
        """

        self.logfile.info("[SELECTION][DOUBLE-CLICK] Selection starts..")

        if self.tools.tool in ["RULER"]:
            return

        if not (Qt.ShiftModifier & QApplication.queryKeyboardModifiers()):
            self.resetSelection()

        selected_annpoint = self.annotations.clickedPoint(x,y)

        is_visible = False
        if selected_annpoint:
            is_visible = self.project.isLabelVisible(selected_annpoint.class_name)

        if selected_annpoint and is_visible:
            if selected_annpoint in self.selected_annpoints:
                self.removeFromSelectedPointList(selected_annpoint)
            else:
                self.addToSelectedPointList(selected_annpoint)
                self.updateInfoPanel.emit(selected_annpoint)

            self.newSelectionPoint.emit()
        else:

            closest_sampling_area = self.closestSamplingArea(x, y)
            if closest_sampling_area:
                self.selected_sampling_area = closest_sampling_area
                self.drawSamplingAreas()
            else:
                selected_blob = self.annotations.clickedBlob(x, y)

                is_visible = False
                if selected_blob:
                    is_visible = self.project.isLabelVisible(selected_blob.class_name)

                if selected_blob and is_visible:
                    if selected_blob in self.selected_blobs:
                        self.removeFromSelectedList(selected_blob)
                    else:
                        self.addToSelectedList(selected_blob)
                        self.updateInfoPanel.emit(selected_blob)

                    self.newSelection.emit()

        self.logfile.info("[SELECTION][DOUBLE-CLICK] Selection ends.")


    def closestSamplingArea(self, x, y):
        """
        It returns the sampling area closest to the given point.
        If the distance of the point is higher than a threshold None is returned.
        """

        dist_min = 1000000.0
        for sampling_area in self.image.sampling_areas:
            dist = distance_point_AABB(x, y, sampling_area)
            if dist < dist_min:
                dist_min = dist
                SA_closest = sampling_area

        if dist_min < 3.0:
            return SA_closest
        else:
            return None

    def updateCellState(self, x, y, state):

        if self.image.grid is not None and self.show_grid is True:
            pos = self.mapFromGlobal(QPoint(x, y))
            scenePos = self.mapToScene(pos)
            self.image.grid.changeCellState(scenePos.x(), scenePos.y(), state)

    def addNote(self, x, y):
        """
        Insert the node to add.
        """
        if self.image.grid is not None and self.show_grid is True:
            pos = self.mapFromGlobal(QPoint(x, y))
            scenePos = self.mapToScene(pos)
            self.image.grid.addNote(scenePos.x(), scenePos.y(), "Enter note..")

### MOUSE EVENTS

    def mousePressEvent(self, event):
        """ Start mouse pan or zoom mode.
        """
        self.activated.emit()

        scenePos = self.mapToScene(event.pos())

        mods = event.modifiers()

        if event.button() == Qt.LeftButton:
            (x, y) = self.clipScenePos(scenePos)
            self.leftMouseButtonPressed.emit(x, y)

            if mods & Qt.ShiftModifier and (self.tools.tool == "WATERSHED" or self.tools.tool == "FREEHAND" or self.tools.tool == "EDITBORDER"\
                 or self.tools.tool == "RULER" or self.tools.tool == "SAM" or self.tools.tool == "SAMINTERACTIVE"):
                self.tools.leftPressed(x, y, mods)

            elif self.tools.tool == "SELECTAREA":
                self.tools.leftPressed(x, y, mods)

            elif self.tools.tool == "MATCH" or self.tools.tool == "RITM" or self.tools.tool == "FOURCLICKS" or self.tools.tool == "PLACEANNPOINT":
                self.tools.leftPressed(x, y, mods)

            elif (self.tools.tool == "WATERSHED" or self.tools.tool == "SAM" or self.tools.tool == "SAMINTERACTIVE"):
                self.setDragMode(QGraphicsView.ScrollHandDrag)

            #used from area selection and pen drawing,
            elif (self.panEnabled and not (mods & Qt.ShiftModifier)) or (mods & Qt.ControlModifier):
                self.setDragMode(QGraphicsView.ScrollHandDrag)

            elif mods & Qt.ShiftModifier:
                self.dragSelectionStart = [x, y]
                self.logfile.info("[SELECTION][DRAG] Selection starts..")

            else:
                # self.tools.leftPressed(x, y)
                self.setDragMode(QGraphicsView.ScrollHandDrag)

        # PANNING IS ALWAYS POSSIBLE WITH WHEEL BUTTON PRESSED (!)
        # if event.button() == Qt.MiddleButton:
        #     self.setDragMode(QGraphicsView.ScrollHandDrag)

        if event.button() == Qt.RightButton:
            (x, y) = self.clipScenePos(scenePos)
            if self.tools.tool == "RITM" or self.tools.tool == "SAMINTERACTIVE" or self.tools.tool == "WATERSHED":
                self.tools.rightPressed(x, y, mods)

            else:
                self.rightMouseButtonPressed.emit(x, y)

        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """ Stop mouse pan or zoom mode (apply zoom if valid).
        """
        QGraphicsView.mouseReleaseEvent(self, event)

        scenePos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)
            (x, y) = self.clipScenePos(scenePos)

            if self.dragSelectionStart:
                if abs(x - self.dragSelectionStart[0]) < 5 and abs(y - self.dragSelectionStart[1]) < 5:
                    self.selectOp(x, y)
                else:
                    self.dragSelectBlobs(x, y)
                    self.dragSelectionStart = None
                    if self.dragSelectionRect:

                        if self.tools.tool == "ROWS" or self.tools.tool == "SAMAUTOMATIC":
                            self.tools.leftReleased(x,y)
                        
                        self.scene.removeItem(self.dragSelectionRect)
                        del self.dragSelectionRect
                        self.dragSelectionRect = None

                    self.logfile.info("[SELECTION][DRAG] Selection ends.")
            else:
                self.tools.leftReleased(x, y)

        if event.button() == Qt.RightButton:
            (x, y) = self.clipScenePos(scenePos)
            if self.tools.tool == "WATERSHED" :
                self.tools.rightReleased(x,y)

    def mouseMoveEvent(self, event):

        QGraphicsView.mouseMoveEvent(self, event)

        scenePos = self.mapToScene(event.pos())
        self.mouseMoved.emit(scenePos.x(), scenePos.y())

        mods = event.modifiers()

        if self.showCrossair == True:
            self.mouseCoords = scenePos
            self.scene.invalidate(self.sceneRect(), QGraphicsScene.ForegroundLayer)

        if event.buttons() == Qt.LeftButton:
            (x, y) = self.clipScenePos(scenePos)

            if self.dragSelectionStart:
                start = self.dragSelectionStart
                if self.dragSelectionRect is None:
                    self.dragSelectionRect = self.scene.addRect(start[0], start[1], x - start[0],
                                                                           y - start[1], self.dragSelectionStyle)
                self.dragSelectionRect.setRect(start[0], start[1], x - start[0], y - start[1])
                return

            if Qt.ControlModifier & QApplication.queryKeyboardModifiers():
                return
            
            self.tools.mouseMove(x, y, mods)

        elif event.buttons() == Qt.RightButton:
            (x, y) = self.clipScenePos(scenePos)
            if self.tools.tool == "WATERSHED":
                self.tools.mouseMove(x, y, mods)



    def mouseDoubleClickEvent(self, event):

        scenePos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            self.selectOp(scenePos.x(), scenePos.y())

    def keyPressEvent(self, event):

        # keys handling goes here..

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift and self.tools.tool == "RITM":
            QApplication.setOverrideCursor(Qt.ArrowCursor)
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        """ Zoom in/zoom out.
        """

        mods = event.modifiers()

        if self.tools.tool == "WATERSHED" and mods & Qt.ShiftModifier:
            
            self.tools.tools["WATERSHED"].scribbles.setScaleFactor(self.zoom_factor)
            self.tools.wheel(event.angleDelta())
            return

        #added zooming rectangle with shift key
        if self.tools.tool == "SAM" and mods & Qt.ShiftModifier:    
            if not self.tools.tools["SAM"].work_area_set:
                self.tools.tools["SAM"].setSize(event.angleDelta())
                return
            else:
                self.tools.tools["SAM"].increasePoint(event.angleDelta())
                return
        
        if self.tools.tool == "SAMINTERACTIVE" and mods & Qt.ShiftModifier:
            # if not self.tools.tools["SAMINTERACTIVE"].work_area_set:
                self.tools.tools["SAMINTERACTIVE"].setSize(event.angleDelta())
                return
            # else:
                # self.tools.tools["SAMINTERACTIVE"].increasePoint(event.angleDelta())
                # return
        if self.tools.tool == "ROWS" and (mods & Qt.ShiftModifier or mods & Qt.ControlModifier):
            self.tools.tools["ROWS"].setSize(event.angleDelta(), mods)
            return
        
        if self.tools.tool == "SAMAUTOMATIC" and mods & Qt.ShiftModifier:
            if self.tools.tools["SAMAUTOMATIC"].work_area_set:
                self.tools.tools["SAMAUTOMATIC"].increasePoint(event.angleDelta())
                return

        if self.zoomEnabled:

            view_pos = event.pos()
            scene_pos = self.mapToScene(view_pos)

            pt = event.angleDelta()

            # uniform zoom.
            self.zoom_factor = self.zoom_factor*pow(pow(2, 1/2), pt.y()/100)
            if self.zoom_factor < self.ZOOM_FACTOR_MIN:
                self.zoom_factor = self.ZOOM_FACTOR_MIN
            if self.zoom_factor > self.ZOOM_FACTOR_MAX:
                self.zoom_factor = self.ZOOM_FACTOR_MAX
            

            self.resetTransform()
            self.scale(self.zoom_factor, self.zoom_factor)

            delta = self.mapToScene(view_pos) - self.mapToScene(self.viewport().rect().center())
            self.centerOn(scene_pos - delta)

            self.updateScaleBar(self.zoom_factor)

            self.scene_overlay.invalidate()
            self.invalidateScene()

    def updateScaleBar(self, zoom_factor):

        REFERENCE_LENGTH_IN_PIXEL = 100
        LENGTH_VLINES = 5

        w = self.viewport().width()
        h = self.viewport().height()

        length = self.px_to_mm * REFERENCE_LENGTH_IN_PIXEL / zoom_factor

        # make length cute
        n = int(math.log10(length))
        cute_length = round(length / math.pow(10,n)) * math.pow(10,n)

        length_in_pixel = int((cute_length * zoom_factor) / self.px_to_mm)

        if cute_length < 100.0:
            txt = "{:.1f} mm".format(cute_length)
        if 100.0 <= cute_length < 1000.0:
            txt = "{:.1f} cm".format(cute_length / 10.0)
        if cute_length >= 1000.0:
            txt = "{:.1f} m".format(cute_length / 1000.0)


        posx = int(w - length_in_pixel - 20)
        posy = int(h * 0.95)

        self.scene_overlay.setSceneRect(0,0,w,h)

        pt1 = QPoint(posx, posy)
        pt2 = QPoint(posx + length_in_pixel, posy)

        self.scalebar_text.setPlainText(txt)
        rc = self.scalebar_text.boundingRect()

        px = (pt1.x() + pt2.x() - rc.width()) / 2
        py = pt1.y() - rc.height()

        self.scalebar_text.setPos(px, py)

        self.scalebar_line.setLine(pt1.x(), pt1.y(), pt2.x(), pt2.y())
        self.scalebar_line2.setLine(pt1.x(), pt1.y() - LENGTH_VLINES, pt1.x(), pt2.y() + LENGTH_VLINES)
        self.scalebar_line3.setLine(pt2.x(), pt1.y() - LENGTH_VLINES, pt2.x(), pt2.y() + LENGTH_VLINES)


#VISIBILITY AND SELECTION

    def dragSelectBlobs(self, x, y):
        # drag can happen in any direction, if not top-left->bottom-right, we need to adjust the coordinates
        sx = min(x,self.dragSelectionStart[0])
        sy = min(y,self.dragSelectionStart[1])
        ex = max(x,self.dragSelectionStart[0])
        ey = max(y,self.dragSelectionStart[1])
        self.resetSelection()
        # select all blobs that are inside the selection rectangle
        for blob in self.annotations.seg_blobs:
            visible = self.project.isLabelVisible(blob.class_name)
            if not visible:
                continue
            box = blob.bbox
            if sx > box[1] or sy > box[0] or ex < box[1] + box[2] or ey < box[0] + box[3]:
                continue
            self.addToSelectedList(blob)
        # select all points that are inside the selection rectangle
        for annpoint in self.annotations.annpoints:
            visible = self.project.isLabelVisible(annpoint.class_name)
            if not visible:
                continue
            if sx > annpoint.coordx-20 or sy > annpoint.coordy - 20 or ex < annpoint.coordx+20 or ey < annpoint.coordy +20:
                continue
            self.addToSelectedPointList(annpoint)


    @pyqtSlot(str)
    def setActiveLabel(self, label):

        if self.tools.tool == "ASSIGN":
            self.tools.tools["ASSIGN"].setActiveLabel(label)

        if self.tools.tool == "WATERSHED":
            label_info = self.project.labels.get(label)
            if label_info is not None:
                self.tools.tools["WATERSHED"].setActiveLabel(label_info)

        self.active_label = label

    @pyqtSlot(str, int)
    def setBorderPen(self, color, thickness):

        self.border_pen = QPen(Qt.black, thickness)
        self.border_pen.setCosmetic(True)
        color_components = color.split("-")
        if len(color_components) > 2:
            r = int(color_components[0])
            g = int(color_components[1])
            b = int(color_components[2])
            self.border_pen.setColor(QColor(r, g, b))

            for blob in self.annotations.seg_blobs:
                blob.qpath_gitem.setPen(self.border_pen)

    @pyqtSlot(str, int)
    def setSelectionPen(self, color, thickness):

        self.border_selected_pen = QPen(Qt.white, thickness)
        self.border_selected_pen.setCosmetic(True)
        color_components = color.split("-")
        if len(color_components) > 2:
            r = int(color_components[0])
            g = int(color_components[1])
            b = int(color_components[2])
            self.border_selected_pen.setColor(QColor(r, g, b))

            for blob in self.selected_blobs:
                blob.qpath_gitem.setPen(self.border_selected_pen)

    @pyqtSlot(str, int)
    def setWorkingAreaPen(self, color, thickness):

        self.working_area_pen = QPen(Qt.white, thickness, Qt.DashLine)
        self.working_area_pen.setCosmetic(True)
        color_components = color.split("-")
        if len(color_components) > 2:
            r = int(color_components[0])
            g = int(color_components[1])
            b = int(color_components[2])
            self.working_area_pen.setColor(QColor(r, g, b))

            self.tools.tools["SELECTAREA"].setWorkingAreaStyle(self.working_area_pen)

            if self.working_area_rect is not None:
                self.working_area_rect.setPen(self.working_area_pen)

    def setBlobVisible(self, blob, visibility):

        if type(blob) == Blob:

            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setVisible(visibility)
            if blob.id_item is not None:
                blob.id_item.setVisible(visibility)

        #do the same for annotated points

        if type(blob) == Point:
            if blob.cross1_gitem is not None:
                blob.cross1_gitem.setVisible(visibility)
                blob.cross2_gitem.setVisible(visibility)
                blob.ellipse_gitem.setVisible(visibility)
            if blob.id_item is not None:
                blob.id_item.setVisible(visibility)

    def updateVisibility(self):

        for blob in self.annotations.seg_blobs:
            visibility = self.project.isLabelVisible(blob.class_name)
            self.setBlobVisible(blob, visibility)

        for blob in self.annotations.annpoints:
            visibility = self.project.isLabelVisible(blob.class_name)
            self.setBlobVisible(blob, visibility)


#SELECTED BLOBS MANAGEMENT

    def selectAllBlobs(self):

        self.resetSelection()
        for blob in self.image.annotations.seg_blobs:
            self.addToSelectedList(blob, redraw=False)

        self.scene.invalidate()

    def addToSelectedList(self, blob, redraw=True):
        """
        Add the given blob to the list of selected blob.
        """

        if blob in self.selected_blobs:
            self.logfile.info("[SELECTION] An already selected blob has been added to the current selection.")
        else:
            self.selected_blobs.append(blob)
            str = "[SELECTION] A new blob (" + blob.blob_name + ";" + blob.class_name + ") has been selected."
            self.logfile.info(str)

        if blob.qpath_gitem is not None:
            blob.qpath_gitem.setPen(self.border_selected_pen)
            blob.qpath_gitem.setZValue(3)
            blob.id_item.setZValue(4)
            blob.id_item.setOpacity(1.0)
        else:
            print("blob qpath_qitem is None!")

        if redraw:
            self.scene.invalidate()

        self.selectionChanged.emit()


    def addToSelectedPointList(self, annpoint, redraw=True):
        """
        Add the given blob to the list of selected blob.
        """

        if annpoint in self.selected_annpoints:
            self.logfile.info("[SELECTION] An already selected blob has been added to the current selection.")
        else:
            self.selected_annpoints.append(annpoint)
            # str = "[SELECTION] A new blob (" + blob.blob_name + ";" + blob.class_name + ") has been selected."
            # self.logfile.info(str)
        #
        if annpoint.cross1_gitem is not None:
            annpoint.cross1_gitem.setPen(self.annpoints_pen_selected)
            annpoint.cross2_gitem.setPen(self.annpoints_pen_selected)
            annpoint.ellipse_gitem.setPen(self.annpoints_pen_selected)

            annpoint.cross1_gitem.setZValue(3)
            annpoint.cross2_gitem.setZValue(3)
            annpoint.ellipse_gitem.setZValue(3)

            annpoint.id_item.setZValue(4)
            annpoint.id_item.setOpacity(1.0)
        else:
            print("annponint qpath_qitem is None!")

        if redraw:
            self.scene.invalidate()

        self.selectionChanged.emit()


    def removeFromSelectedList(self, blob, redraw=True):
        try:
            # safer if iterating over selected_blobs and calling this function.
            self.selected_blobs = [x for x in self.selected_blobs if not x == blob]

            if blob.qpath_gitem is not None:
                if self.border_enabled is True:
                    blob.qpath_gitem.setPen(self.border_pen)
                else:
                    blob.qpath_gitem.setPen(QPen(Qt.NoPen))

                blob.qpath_gitem.setZValue(1)
                blob.id_item.setZValue(2)
                blob.id_item.setOpacity(0.7)

            if redraw:
                self.scene.invalidate()


        except Exception as e:
            print("Exception: e", e)
            pass
        self.selectionChanged.emit()


    def removeFromSelectedPointList(self, annpoint, redraw=True):

        try:
            self.selected_annpoints = [x for x in self.selected_annpoints if not x == annpoint]

            if annpoint.cross1_gitem is not None:

                annpoint.cross1_gitem.setPen(self.annpoints_pen)
                annpoint.cross2_gitem.setPen(self.annpoints_pen)
                annpoint.ellipse_gitem.setPen(self.annpoints_pen)

                annpoint.cross1_gitem.setZValue(1)
                annpoint.cross2_gitem.setZValue(1)
                annpoint.ellipse_gitem.setZValue(1)

                annpoint.id_item.setZValue(2)
                annpoint.id_item.setOpacity(0.7)

            self.scene.invalidate()
        #
        except Exception as e:
            print("Exception: e", e)
            pass
        self.selectionChanged.emit()

    def resizeEvent(self, event):
        """ Maintain current zoom on resize.
        """
        if self.imgheight:
            self.ZOOM_FACTOR_MIN = min(1.0 * self.width() / self.imgwidth, 1.0 * self.height() / self.imgheight)
        self.updateScaleBar(self.zoom_factor)
        self.updateViewer()

        event.accept()

    def resetSelection(self):

        for blob in self.selected_blobs:
            if blob.qpath_gitem is None:
                print("Selected item with no path!")
            else:
                if self.border_enabled is True:
                    blob.qpath_gitem.setPen(self.border_pen)
                else:
                    blob.qpath_gitem.setPen(QPen(Qt.NoPen))

                blob.qpath_gitem.setZValue(1)
                blob.id_item.setZValue(2)
                blob.id_item.setOpacity(0.7)


        for annpoint in self.selected_annpoints:
            if annpoint.cross1_gitem is not None:
                annpoint.cross1_gitem.setPen(self.annpoints_pen)
                annpoint.cross2_gitem.setPen(self.annpoints_pen)
                annpoint.ellipse_gitem.setPen(self.annpoints_pen)

                annpoint.cross1_gitem.setZValue(1)
                annpoint.cross2_gitem.setZValue(1)
                annpoint.ellipse_gitem.setZValue(1)

                annpoint.id_item.setZValue(2)
                annpoint.id_item.setOpacity(0.7)

        if self.selected_sampling_area:
            self.selected_sampling_area = None
            self.drawSamplingAreas()


        self.selected_blobs.clear()
        self.selected_annpoints.clear()
        self.scene.invalidate(self.scene.sceneRect())
        self.selectionChanged.emit()
        self.selectionReset.emit()


#CREATION and DESTRUCTION of BLOBS
    def addBlob(self, blob_or_point, selected=False, redraw=True):
        """
        The only function to add annotations. will take care of undo and QGraphicItems.
        """

        if type(blob_or_point) == Point:
            self.drawPointAnn(blob_or_point)
            if selected:
                self.addToSelectedPointList(blob_or_point, redraw=False)
                self.project.addPoint(self.image,blob_or_point)

        else:
            self.undo_data.addBlob(blob_or_point)
            self.project.addBlob(self.image, blob_or_point)
            self.drawBlob(blob_or_point)

            if selected:
                self.addToSelectedList(blob_or_point)

            if self.fill_enabled is False:
                blob_or_point.qpath_gitem.setBrush(QBrush(Qt.NoBrush))

            if self.border_enabled is False:
                blob_or_point.qpath_gitem.setPen(QPen(Qt.NoPen))

        if redraw:
            self.scene.invalidate()

    def removeBlobs(self, blobs):

        for blob in blobs:
            self.removeFromSelectedList(blob, redraw=False)
            self.undrawBlob(blob, redraw=False)
            self.undo_data.removeBlob(blob)
            self.project.removeBlob(self.image, blob)

        self.scene.invalidate()

    def removePoints(self, points):

        for point in points:
            self.removeFromSelectedPointList(point, redraw=False)
            self.undrawAnnPoint(point, redraw=False)
            self.project.removePoint(self.image, point)

        self.scene.invalidate()

    def removeBlob(self, blob, redraw=True):
        """
        The only function to remove annotations.
        """
        if type(blob) == Point:

            point = blob

            self.removeFromSelectedPointList(point, redraw=False)
            self.undrawAnnPoint(point, redraw=False)
            #undo is missing
            self.project.removePoint(point)

        else:

            self.removeFromSelectedList(blob, redraw=False)
            self.undrawBlob(blob)
            self.undo_data.removeBlob(blob)
            self.project.removeBlob(self.image, blob)

        if redraw:
            self.scene.invalidate()

    def updateBlob(self, old_blob, new_blob, selected=False, redraw=True):

        self.project.updateBlob(self.image, old_blob, new_blob)

        self.removeFromSelectedList(old_blob, redraw=False)
        self.undrawBlob(old_blob)
        self.undo_data.removeBlob(old_blob)

        self.undo_data.addBlob(new_blob)
        self.drawBlob(new_blob)
        if selected:
            self.addToSelectedList(new_blob, redraw=False)

        if self.fill_enabled is False:
            new_blob.qpath_gitem.setBrush(QBrush(Qt.NoBrush))

        if self.border_enabled is False:
            new_blob.qpath_gitem.setPen(QPen(Qt.NoPen))

        if redraw:
            self.scene.invalidate()

    def deleteSelectedBlobs(self):

        if len(self.selected_blobs) > 0:

            for blob in self.selected_blobs:
                self.project.updateCorrespondences("REMOVE", self.image, None, blob, "")

            self.removeBlobs(self.selected_blobs)

        if len(self.selected_annpoints) > 0:
            self.removePoints(self.selected_annpoints)

        if self.selected_sampling_area:
            self.image.sampling_areas.remove(self.selected_sampling_area)
            self.selected_sampling_area = None
            self.drawSamplingAreas()

        self.saveUndo()

    @pyqtSlot(str)
    def assignClass(self, class_name):
        """
        Assign the given class to the selected blobs.
        """
        for blob in self.selected_blobs:

            self.undo_data.setBlobClass(blob, class_name)
            self.project.setBlobClass(self.image, blob, class_name)
            brush = self.project.classBrushFromName(blob)
            blob.qpath_gitem.setBrush(brush)

        for annpoint in self.selected_annpoints:

            self.project.setPointClass(self.image, annpoint, class_name)
            brush = self.project.classBrushFromName(annpoint)
            annpoint.ellipse_gitem.setBrush(brush)

        self.scene.invalidate()


    def setBlobClass(self, blob, class_name):

        if blob.class_name == class_name:
            return

        self.undo_data.setBlobClass(blob, class_name)
        self.project.setBlobClass(self.image, blob, class_name)

        if blob.qpath_gitem:
            brush = self.project.classBrushFromName(blob)
            blob.qpath_gitem.setBrush(brush)
            self.scene.invalidate()

    def updateBlobClass(self, img, class_name, blob):

        if self.image == img:
            self.undo_data.setBlobClass(blob, class_name)

            if blob.qpath_gitem:
                brush = self.project.classBrushFromName(blob)
                blob.qpath_gitem.setBrush(brush)
                self.scene.invalidate()

    def setAnnPointClass(self, annpoint, class_name):

        if annpoint.class_name == class_name:
            return

        self.project.setPointClass(self.image, annpoint, class_name)

        if annpoint.cross1_gitem:
            brush = self.project.classBrushFromName(annpoint)
            annpoint.ellipse_gitem.setBrush(brush)
            self.scene.invalidate()

###### UNDO STUFF #####

    def saveUndo(self):
        self.undo_data.saveUndo()

    def undo(self):

        if self.tools.tool == "RITM" and self.tools.tools["RITM"].hasPoints():
            self.tools.tools["RITM"].undo_click()
            return
        
        if self.tools.tool == "SAMINTERACTIVE" and self.tools.tools["SAMINTERACTIVE"].hasPoints():
            self.tools.tools["SAMINTERACTIVE"].undo_click()
            return
        
        if self.tools.tool == "FOURCLICKS":
            self.tools.tools["FOURCLICKS"].undo_click()
            return

        if self.tools.tool in ["FREEHAND", "CUT", "EDITBORDER"]:
            if self.tools.tools["EDITBORDER"].edit_points.undo():
                return

        operation = self.undo_data.undo()
        if operation is None:
            return

        for blob in operation['remove']:
            message = "[UNDO][REMOVE] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            self.logfile.info(message)
            self.removeFromSelectedList(blob)
            self.undrawBlob(blob)
            self.project.removeBlob(self.image, blob)

        for blob in operation['add']:
            message = "[UNDO][ADD] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            self.logfile.info(message)
            self.project.addBlob(self.image, blob)
            self.selected_blobs.append(blob)
            self.selectionChanged.emit()
            self.drawBlob(blob)

        for (blob, class_name) in operation['class']:
            self.project.setBlobClass(self.image, blob, class_name)
            brush = self.project.classBrushFromName(blob)
            #this might apply to blobs NOT in this image (or rendered)
            if blob.qpath_gitem:
                blob.qpath_gitem.setBrush(brush)

        self.updateVisibility()

    def redo(self):
        operation = self.undo_data.redo()
        if operation is None:
            return

        for blob in operation['add']:
            message = "[REDO][ADD] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            self.logfile.info(message)
            self.removeFromSelectedList(blob)
            self.undrawBlob(blob)
            self.project.removeBlob(self.image, blob)

        for blob in operation['remove']:
            message = "[REDO][REMOVE] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            self.logfile.info(message)
            self.project.addBlob(self.image, blob)
            self.selected_blobs.append(blob)
            self.selectionChanged.emit()
            self.drawBlob(blob)

        for (blob, class_name) in operation['newclass']:
            self.project.setBlobClass(self.image, blob, class_name)
            brush = self.project.classBrushFromName(blob)
            blob.qpath_gitem.setBrush(brush)

        self.updateVisibility()

    @pyqtSlot(str)
    def logMessage(self, message):

        self.logfile.info(message)

    @pyqtSlot(Blob, str)
    def logBlobInfo(self, blob, msg):

        message1 = msg + " Blob_id={:d} Blob_name={:s} class={:s}".format(blob.id, blob.blob_name, blob.class_name)
        message2 = msg + " top={:.1f} left={:.1f} width={:.1f} height={:.1f}".format(blob.bbox[0], blob.bbox[1], blob.bbox[2], blob.bbox[3])
        message3 = msg + " Area= {:.4f} , Perimeter= {:.4f}".format(blob.area, blob.perimeter)

        self.logfile.info(message1)
        self.logfile.info(message2)
        self.logfile.info(message3)
