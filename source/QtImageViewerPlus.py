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
    The viewer has also drawing capabilities.
"""

import os.path
from PyQt5.QtCore import Qt,  QRect, QPoint, QPointF, QRectF, QFileInfo, QDir, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QImageReader
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

from source.Project import Project
from source.Image import Image
from source.Annotation import Annotation

class QtImageViewerPlus(QGraphicsView):
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
    leftMouseButtonDoubleClicked = pyqtSignal(float, float)
    rightMouseButtonDoubleClicked = pyqtSignal(float, float)
    mouseMoveLeftPressed = pyqtSignal(float, float)

    # custom signal
    viewUpdated = pyqtSignal()

    def __init__(self):
        QGraphicsView.__init__(self)

        self.setStyleSheet("background-color: rgb(40,40,40)")

        # Image is displayed as a QPixmap in a QGraphicsScene attached to this QGraphicsView.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Store a local handle to the scene's current image pixmap.
        self.pixmapitem = QGraphicsPixmapItem()
        self.pixmapitem.setZValue(0)
        self.scene.addItem(self.pixmapitem)

        # current image size
        self.imgwidth = 0
        self.imgheight = 0

        self.project = Project()
        self.image = Image()
        self.annotations = Annotation()
        self.selected_blobs = []

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


        # DATA FOR THE EDITBORDER , CUT and FREEHAND TOOLS
        self.edit_points = []
        self.edit_qpath_gitem = self.scene.addPath(QPainterPath(), self.border_pen)
        self.last_editborder_points = []      #last editing operation stored here for local refinement

        # DATA FOR THE RULER, DEEP EXTREME and SPLIT TOOLS
        self.pick_points_number = 0
        self.pick_points = []
        self.pick_markers = []

        self.CROSS_LINE_WIDTH = 2
        self.split_pick_style   = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}
        self.ruler_pick_style   = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}
        self.extreme_pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.red,  'size': 6}


        # DATA FOR THE CREATECRACK TOOL
        self.crackWidget = None

        self.tool = None

        # UNDO DATA
        self.undo_operations = []
        self.undo_position = -1
        """Temporary variable to hold the added and removed of the last operation."""
        self.undo_operation = { 'remove':[], 'add':[], 'class':[], 'newclass':[] }
        """Max number  of undo operations"""
        self.max_undo = 100


        # Image aspect ratio mode.
        self.aspectRatioMode = Qt.KeepAspectRatio

        # Set scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.verticalScrollBar().valueChanged.connect(self.viewUpdated)
        self.horizontalScrollBar().valueChanged.connect(self.viewUpdated)



        # Panning is enabled if and only if the image is greater than the viewport.
        self.panEnabled = True
        self.zoomEnabled = True
        self.showCrossair = False
        self.mouseCoords = QPointF(0, 0)

        self.clicked_x = 0
        self.clicked_y = 0

        # zoom is always active
        self.zoom_factor = 1.0
        self.ZOOM_FACTOR_MIN = 0.02
        self.ZOOM_FACTOR_MAX = 10.0

        # transparency
        self.opacity = 1.0

        MIN_SIZE = 250
        self.pixmap = QPixmap(MIN_SIZE, MIN_SIZE)
        self.overlay_image = QImage(1, 1, QImage.Format_ARGB32)

        self.viewport().setMinimumWidth(MIN_SIZE)
        self.viewport().setMinimumHeight(MIN_SIZE)

        self.resetTransform()
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.setContextMenuPolicy(Qt.CustomContextMenu)


    def setProject(self, project):
        self.project = project

    def setImage(self, image):
        self.image = image
        self.annotations = image.annotations
        self.selected_blobs = []

        for blob in self.annotations.seg_blobs:
            self.drawBlob(blob)

        self.scene.invalidate()

    def setChannel(self, channel):
        self.channel = channel

        # retrieve image size
        image_reader = QImageReader(channel.filename)
        size = image_reader.size()
        if self.image.width is None:
            self.image.width = size.width()
            self.image.height = size.height()

        if size.width() != self.image.width or size.height() != self.image.height:
            raise Exception("Size of the image changed! Should have been: " + str(self.image.width) + "x" + str(self.image.height))

        if size.width() > 32767 or size.height() > 32767:
            raise Exception(
                "This map exceeds the image dimension handled by TagLab (the maximum size is 32767 x 32767).")

        img = QImage(channel.filename)
        if img.isNull():
            (channel.filename, filter) = QFileDialog.getOpenFileName(self, "Couldn't find the map, please select it:",
                                                                       QFileInfo(channel.filename).dir().path(),
                                                                       "Image Files (*.png *.jpg)")
            dir = QDir(os.getcwd())
            self.map_image_filename = dir.relativeFilePath(channel.filename)
            img = QImage(channel.filename)
            if img.isNull():
                raise Exception("Could not load or find the image: " + channel.filename)
        self.setChannelImg(img)

    def drawBlob(self, blob, prev=False):

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
        brush = self.project.classBrushFromName(blob)

        blob.qpath_gitem = self.scene.addPath(blob.qpath, pen, brush)
        blob.qpath_gitem.setZValue(1)
        #blob.qpath_gitem.setOpacity(self.transparency_value)



    def applyTransparency(self, value):
        self.transparency_value = value / 100.0
        # current annotations
        for blob in self.annotations.seg_blobs:
            blob.qpath_gitem.setOpacity(self.transparency_value)


    def disableScrollBars(self):

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def enablePan(self):
        self.panEnabled = True

    def disablePan(self):
        self.panEnabled = False

    def enableZoom(self):
        self.zoomEnabled = True

    def disableZoom(self):
        self.zoomEnabled = False

    def setChannelImg(self, channel_img, zoomf=0.0):
        """
        Set the scene's current image (input image must be a QImage)
        For calculating the zoom factor automatically set it to 0.0.
        """
        if type(channel_img) is QImage:
            imageARGB32 = channel_img.convertToFormat(QImage.Format_ARGB32)
            self.pixmap = QPixmap.fromImage(imageARGB32)
            self.imgwidth = channel_img.width()
            self.imgheight = channel_img.height()
        else:
            raise RuntimeError("Argument must be a QImage.")

        self.pixmapitem.setPixmap(self.pixmap)

        # Set scene size to image size (!)
        self.setSceneRect(QRectF(self.pixmap.rect()))

        # calculate zoom factor
        pixels_of_border = 10
        zf1 = (self.viewport().width() - pixels_of_border) / self.imgwidth
        zf2 = (self.viewport().height() - pixels_of_border) / self.imgheight

        zf = min(zf1, zf2)
        self.zoom_factor = zf

        self.updateViewer()

    def viewportToScene(self):
        #check
        topleft = self.mapToScene(self.viewport().rect().topLeft())
        bottomright = self.mapToScene(self.viewport().rect().bottomRight())
        return QRectF(topleft, bottomright)

    def viewportToScenePercent(self):
        view = self.viewportToScene()
        view.setCoords(view.left()/self.imgwidth, view.top()/self.imgheight,
                    view.right()/self.imgwidth, view.bottom()/self.imgheight)
        return view




    #UNUSED
    def setOpacity(self, opacity):
        self.opacity = opacity

    def setOverlayImage(self, image):
        self.overlay_image = image.convertToFormat(QImage.Format_ARGB32)
        self.drawOverlayImage()

    def drawOverlayImage(self):

        if self.overlay_image.width() > 1:
            pxmap = self.pixmap.copy()
            p = QPainter()
            p.begin(pxmap)
            p.setOpacity(self.opacity)
            p.drawImage(0, 0, self.overlay_image)
            p.end()

            self.pixmapitem.setPixmap(pxmap)

    #used for crossair cursor
    def drawForeground(self, painter, rect):
        if self.showCrossair:
            painter.setClipRect(rect)
            painter.setPen(QPen(Qt.white, 1))
            painter.drawLine(self.mouseCoords.x(), rect.top(), self.mouseCoords.x(), rect.bottom())
            painter.drawLine(rect.left(), self.mouseCoords.y(), rect.right(), self.mouseCoords.y())

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """

        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)

        self.invalidateScene()
        #painter = QPainter(self)
        #self.scene.render(painter)

        # notify that the view has been updated
        #self.viewUpdated.emit()

    def setViewParameters(self, posx, posy, zoomfactor):
        self.horizontalScrollBar().setValue(posx)
        self.verticalScrollBar().setValue(posy)
        self.zoom_factor = zoomfactor
        self.updateViewer()

    def clipScenePos(self, scenePosition):
        posx = scenePosition.x()
        posy = scenePosition.y()
        if posx < 0:
            posx = 0
        if posy < 0:
            posy = 0
        if posx > self.imgwidth:
            posx = self.imgwidth
        if posy > self.imgheight:
            posy = self.imgheight

        return [round(posx), round(posy)]

    def resizeEvent(self, event):
        """ Maintain current zoom on resize.
        """
        self.updateViewer()

#TOOLS and SELECTIONS

    def setTool(self, tool):
        self.resetTools()
        if tool in ["FREEHAND", "RULER", "DEEPEXTREME"] or (tool in ["CUT", "EDITBORDER"] and len(self.selected_blobs) > 1):
            self.resetSelection()
        self.tool = tool
        self.disablePan()
        self.enableZoom()

    def resetSelection(self):
        for blob in self.selected_blobs:
            if blob.qpath_gitem is None:
                print("Selected item with no path!")
            else:
                blob.qpath_gitem.setPen(self.border_pen)
        self.selected_blobs.clear()
        self.scene.invalidate(self.scene.sceneRect())

    def resetTools(self):
        self.edit_qpath_gitem.setPath(QPainterPath())
        self.edit_points = []

        self.showCrossair = False
        self.scene.invalidate(self.scene.sceneRect())

        if self.crackWidget is not None:
            self.crackWidget.close()
        self.crackWidget = None
        self.setDragMode(QGraphicsView.NoDrag)

    def resetPickPoints(self):
        self.pick_points_number = 0
        self.pick_points.clear()
        for marker in self.pick_markers:
            self.scene.removeItem(marker)
        self.pick_markers.clear()



    def mousePressEvent(self, event):
        """ Start mouse pan or zoom mode.
        """
        scenePos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            clippedCoords = self.clipScenePos(scenePos)
            mods = event.modifiers()
            #used from area selection and pen drawing,
            if (self.panEnabled and not (mods & Qt.ShiftModifier)) or (mods & Qt.ControlModifier):
                self.setDragMode(QGraphicsView.ScrollHandDrag)
            else:
                self.leftMouseButtonPressed.emit(clippedCoords[0], clippedCoords[1])


        # PANNING IS ALWAYS POSSIBLE WITH WHEEL BUTTON PRESSED (!)
        # if event.button() == Qt.MiddleButton:
        #     self.setDragMode(QGraphicsView.ScrollHandDrag)

        if event.button() == Qt.RightButton:
            clippedCoords = self.clipScenePos(scenePos)
            self.rightMouseButtonPressed.emit(clippedCoords[0], clippedCoords[1])

        self.clicked_x = event.pos().x()
        self.clicked_y = event.pos().y()

        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """ Stop mouse pan or zoom mode (apply zoom if valid).
        """
        QGraphicsView.mouseReleaseEvent(self, event)

        scenePos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)
            clippedCoords = self.clipScenePos(scenePos)
            self.leftMouseButtonReleased.emit(clippedCoords[0], clippedCoords[1])


    def mouseMoveEvent(self, event):

        QGraphicsView.mouseMoveEvent(self, event)

        scenePos = self.mapToScene(event.pos())

        if event.buttons() == Qt.LeftButton:
            clippedCoords = self.clipScenePos(scenePos)
            self.mouseMoveLeftPressed.emit(clippedCoords[0], clippedCoords[1])

        if self.showCrossair == True:
            self.mouseCoords = scenePos
            self.scene.invalidate(self.sceneRect(), QGraphicsScene.ForegroundLayer)


    def mouseDoubleClickEvent(self, event):

        scenePos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            self.leftMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())

        # QGraphicsView.mouseDoubleClickEvent(self, event)

    def wheelEvent(self, event):
        """ Zoom in/zoom out.
        """

        if self.zoomEnabled:

            pt = event.angleDelta()

            #self.zoom_factor = self.zoom_factor + pt.y() / 2400.0
            #uniform zoom.
            self.zoom_factor = self.zoom_factor*pow(pow(2, 1/2), pt.y()/100);
            if self.zoom_factor < self.ZOOM_FACTOR_MIN:
                self.zoom_factor = self.ZOOM_FACTOR_MIN
            if self.zoom_factor > self.ZOOM_FACTOR_MAX:
                self.zoom_factor = self.ZOOM_FACTOR_MAX

            self.updateViewer()


        # PAY ATTENTION; THE WHEEL INTERACT ALSO WITH THE SCROLL BAR (!!)
        #QGraphicsView.wheelEvent(self, event)


#UNFDO AND OTHER THINGS
    def updateVisibility(self):
        for blob in self.annotations.seg_blobs:

            visibility = self.labels_widget.isClassVisible(blob.class_name)
            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setVisible(visibility)

    def addToSelectedList(self, blob):
        """
        Add the given blob to the list of selected blob.
        """

        if blob in self.selected_blobs:
            self.logfile.info("[SELECTION] An already selected blob has been added to the current selection.")
        else:
            self.selected_blobs.append(blob)
            str = "[SELECTION] A new blob (" + blob.blob_name + ";" + blob.class_name + ") has been selected."
            self.logfile.info(str)

        if not blob.qpath_gitem is None:
            blob.qpath_gitem.setPen(self.border_selected_pen)
        else:
            print("blob qpath_qitem is None!")
        self.scene.invalidate()

    def removeFromSelectedList(self, blob):
        try:
            # safer if iterating over selected_blobs and calling this function.
            self.selected_blobs = [x for x in self.selected_blobs if not x == blob]
            if not blob.qpath_gitem is None:
                blob.qpath_gitem.setPen(self.border_pen)
            self.scene.invalidate()
        except Exception as e:
            print("Exception: e", e)
            pass

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

        self.scene.invalidate()

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
            self.logfile.info(message)
            self.removeFromSelectedList(blob)
            self.undrawBlob(blob)
            self.annotations.removeBlob(blob)

        for blob in operation['add']:
            message = "[UNDO][ADD] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            self.logfile.info(message)
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

