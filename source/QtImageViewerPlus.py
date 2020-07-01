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
from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QImageReader, QFont
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

from source.Undo import Undo
from source.Project import Project
from source.Image import Image
from source.Annotation import Annotation
from source.Annotation import Blob
from source.Tools import Tools

from source.QtImageViewer import QtImageViewer

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

    # custom signal
    updateInfoPanel = pyqtSignal(Blob)

    activated = pyqtSignal()
    newSelection = pyqtSignal()

    def __init__(self):
        QtImageViewer.__init__(self)

        self.logfile = None #MUST be inited in Taglab.py
        self.project = Project()
        self.image = None
        self.channel = None
        self.annotations = Annotation()
        self.selected_blobs = []

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
        self.border_pen = QPen(Qt.black, 3)
        #        pen.setJoinStyle(Qt.MiterJoin)
        #        pen.setCapStyle(Qt.RoundCap)
        self.border_pen.setCosmetic(True)
        self.border_selected_pen = QPen(Qt.white, 3)
        self.border_selected_pen.setCosmetic(True)

        self.showCrossair = False
        self.mouseCoords = QPointF(0, 0)
        self.crackWidget = None

        self.setContextMenuPolicy(Qt.CustomContextMenu)


    def setProject(self, project):

        self.project = project


    def setImage(self, image, channel_idx=0):
        """
        Set the image to visualize. The first channel is visualized unless otherwise specified.
        """

        self.clear()

        self.image = image
        self.annotations = image.annotations
        self.selected_blobs = []

        for blob in self.annotations.seg_blobs:
            self.drawBlob(blob)

        self.scene.invalidate()
        self.tools.tools['RULER'].setPxToMM(image.map_px_to_mm_factor)
        self.px_to_mm = image.map_px_to_mm_factor

        self.setChannel(image.channels[channel_idx])

        self.activated.emit()


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
            img = channel.loadData()

        if img.isNull():
            (channel.filename, filter) = QFileDialog.getOpenFileName(self, "Couldn't find the map, please select it:",
                                                                       QFileInfo(channel.filename).dir().path(),
                                                                       "Image Files (*.png *.jpg)")
            dir = QDir(os.getcwd())
            self.map_image_filename = dir.relativeFilePath(channel.filename)
            img = QImage(channel.filename)
            if img.isNull():
                raise Exception("Could not load or find the image: " + channel.filename)

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

        QtImageViewer.clear(self)
        self.selected_blobs = []
        self.undo_data = Undo()

        for blob in self.annotations.seg_blobs:
            self.undrawBlob(blob)
            del blob

        self.annotations = Annotation()


    def drawBlob(self, blob, prev=False):

        # if it has just been created remove the current graphics item in order to set it again
        if blob.qpath_gitem is not None:
            self.scene.removeItem(blob.qpath_gitem)
            self.scene.removeItem(blob.id_item)
            del blob.qpath_gitem
            del blob.id_item
            blob.qpath_gitem = None
            blob.id_item = None

        blob.setupForDrawing()

        if prev is True:
            pen = self.border_pen_for_appended_blobs
        else:
            pen = self.border_selected_pen if blob in self.selected_blobs else self.border_pen
        brush = self.project.classBrushFromName(blob)

        blob.qpath_gitem = self.scene.addPath(blob.qpath, pen, brush)
        blob.qpath_gitem.setZValue(1)
        blob.id_item = self.scene.addText(str(blob.id), QFont("Times", 30, QFont.Bold))
        blob.id_item.setPos(blob.centroid[0], blob.centroid[1])
        blob.id_item.setZValue(2)
        blob.id_item.setDefaultTextColor(Qt.white)
        #blob.qpath_gitem.setOpacity(self.transparency_value)


    def undrawBlob(self, blob):
        self.scene.removeItem(blob.qpath_gitem)
        self.scene.removeItem(blob.id_item)
        blob.qpath = None
        blob.qpath_gitem = None
        blob.id_item = None
        self.scene.invalidate()


    def applyTransparency(self, value):
        self.transparency_value = value / 100.0
        # current annotations
        for blob in self.annotations.seg_blobs:
            blob.qpath_gitem.setOpacity(self.transparency_value)

    #used for crossair cursor
    def drawForeground(self, painter, rect):
        if self.showCrossair:
            painter.setClipRect(rect)
            painter.setPen(QPen(Qt.white, 1))
            painter.drawLine(self.mouseCoords.x(), rect.top(), self.mouseCoords.x(), rect.bottom())
            painter.drawLine(rect.left(), self.mouseCoords.y(), rect.right(), self.mouseCoords.y())


#TOOLS and SELECTIONS

    def setTool(self, tool):

        self.tools.setTool(tool)

        if tool in ["FREEHAND", "RULER", "DEEPEXTREME"] or (tool in ["CUT", "EDITBORDER"] and len(self.selected_blobs) > 1):
            self.resetSelection()
        if tool == "DEEPEXTREME":
            self.showCrossair = True
        else:
            self.showCrossair = False

        if tool == "MOVE":
            self.enablePan()
        else:
            self.disablePan()

    def resetTools(self):
        self.tools.resetTools()
        self.showCrossair = False
        self.scene.invalidate(self.scene.sceneRect())
        self.setDragMode(QGraphicsView.NoDrag)


#TODO not necessarily a slot
    @pyqtSlot(float, float)
    def selectOp(self, x, y):
        """
        Selection operation.
        """

        self.logfile.info("[SELECTION][DOUBLE-CLICK] Selection starts..")

        if self.tools.tool in ["RULER", "DEEPEXTREME"]:
            return

        if not (Qt.ShiftModifier & QApplication.queryKeyboardModifiers()):
            self.resetSelection()

        selected_blob = self.annotations.clickedBlob(x, y)

        if selected_blob:
            if selected_blob in self.selected_blobs:
                self.removeFromSelectedList(selected_blob)
            else:
                self.addToSelectedList(selected_blob)
                self.updateInfoPanel.emit(selected_blob)

        if len(self.selected_blobs) == 1:
            self.newSelection.emit()
        self.logfile.info("[SELECTION][DOUBLE-CLICK] Selection ends.")


#MOUSE EVENTS

    def mousePressEvent(self, event):
        """ Start mouse pan or zoom mode.
        """
        self.activated.emit()

        scenePos = self.mapToScene(event.pos())

        mods = event.modifiers()

        if event.button() == Qt.LeftButton:
            (x, y) = self.clipScenePos(scenePos)
            #used from area selection and pen drawing,

            if (self.panEnabled and not (mods & Qt.ShiftModifier)) or (mods & Qt.ControlModifier):
                self.setDragMode(QGraphicsView.ScrollHandDrag)
            elif self.tools.tool == "MATCH":
                self.tools.leftPressed(x, y, mods)

            elif mods & Qt.ShiftModifier:
                self.dragSelectionStart = [x, y]
                self.logfile.info("[SELECTION][DRAG] Selection starts..")

            else:
                self.tools.leftPressed(x, y)
                #self.leftMouseButtonPressed.emit(clippedCoords[0], clippedCoords[1])


        # PANNING IS ALWAYS POSSIBLE WITH WHEEL BUTTON PRESSED (!)
        # if event.button() == Qt.MiddleButton:
        #     self.setDragMode(QGraphicsView.ScrollHandDrag)

        if event.button() == Qt.RightButton:
            clippedCoords = self.clipScenePos(scenePos)
            self.rightMouseButtonPressed.emit(clippedCoords[0], clippedCoords[1])

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
                        self.scene.removeItem(self.dragSelectionRect)
                        del self.dragSelectionRect
                        self.dragSelectionRect = None

                    self.logfile.info("[SELECTION][DRAG] Selection ends.")
            else:
                self.tools.leftReleased(x, y)

    def mouseMoveEvent(self, event):

        QGraphicsView.mouseMoveEvent(self, event)

        scenePos = self.mapToScene(event.pos())

        if self.showCrossair == True:
            self.mouseCoords = scenePos
            self.scene.invalidate(self.sceneRect(), QGraphicsScene.ForegroundLayer)

        if event.buttons() == Qt.LeftButton:
            (x, y) = self.clipScenePos(scenePos)

            if self.dragSelectionStart:
                start = self.dragSelectionStart
                if not self.dragSelectionRect:
                    self.dragSelectionRect = self.scene.addRect(start[0], start[1], x - start[0],
                                                                           y - start[1], self.dragSelectionStyle)
                self.dragSelectionRect.setRect(start[0], start[1], x - start[0], y - start[1])
                return

            if Qt.ControlModifier & QApplication.queryKeyboardModifiers():
                return

            self.tools.mouseMove(x, y)


    def mouseDoubleClickEvent(self, event):

        scenePos = self.mapToScene(event.pos())

        if event.button() == Qt.LeftButton:
            self.selectOp(scenePos.x(), scenePos.y())


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

        # PAY ATTENTION !! THE WHEEL INTERACT ALSO WITH THE SCROLL BAR !!
        #QGraphicsView.wheelEvent(self, event)

#VISIBILITY AND SELECTION

    def dragSelectBlobs(self, x, y):
        sx = self.dragSelectionStart[0]
        sy = self.dragSelectionStart[1]
        self.resetSelection()
        for blob in self.annotations.seg_blobs:
            visible = self.project.isLabelVisible(blob.class_name)
            if not visible:
                continue
            box = blob.bbox

            if sx > box[1] or sy > box[0] or x < box[1] + box[2] or y < box[0] + box[3]:
                continue
            self.addToSelectedList(blob)

    @pyqtSlot(str)
    def setActiveLabel(self, label):

        self.tools.tools["ASSIGN"].setActiveLabel(label)


    def updateVisibility(self):

        for blob in self.annotations.seg_blobs:
            visibility = self.project.isLabelVisible(blob.class_name)
            if blob.qpath_gitem is not None:
                blob.qpath_gitem.setVisible(visibility)



#SELECTED BLOBS MANAGEMENT

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

    def resetSelection(self):
        for blob in self.selected_blobs:
            if blob.qpath_gitem is None:
                print("Selected item with no path!")
            else:
                blob.qpath_gitem.setPen(self.border_pen)
        self.selected_blobs.clear()
        self.scene.invalidate(self.scene.sceneRect())



#CREATION and DESTRUCTION of BLOBS
    def addBlob(self, blob, selected = False):
        """
        The only function to add annotations. will take care of undo and QGraphicItems.
        """
        self.undo_data.addBlob(blob)
        #self.undo_data_operation['remove'].append(blob)
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
        self.undo_data.removeBlob(blob)
        self.annotations.removeBlob(blob)


    def deleteSelectedBlobs(self):

        for blob in self.selected_blobs:
            self.removeBlob(blob)
        self.saveUndo()


    def setBlobClass(self, blob, class_name):

        if blob.class_name == class_name:
            return

        self.undo_data.setBlobClass(blob, class_name)

        blob.class_name = class_name
        if class_name == "Empty":
            blob.class_color = [255, 255, 255]
        else:
            blob.class_color = self.project.labels[blob.class_name].fill

        brush = self.project.classBrushFromName(blob)
        blob.qpath_gitem.setBrush(brush)

        self.scene.invalidate()


#UNDO STUFF
#UNDO STUFF

    def saveUndo(self):
        self.undo_data.saveUndo()

    def undo(self):
        operation = self.undo_data.undo()
        if operation is None:
            return

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
            brush = self.project.classBrushFromName(blob)
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
            self.annotations.removeBlob(blob)

        for blob in operation['remove']:
            message = "[REDO][REMOVE] BLOBID={:d} VERSION={:d}".format(blob.id, blob.version)
            self.logfile.info(message)
            self.annotations.addBlob(blob)
            self.selected_blobs.append(blob)
            self.drawBlob(blob)

        for (blob, class_name) in operation['newclass']:
            blob.class_name = class_name
            brush = self.classBrushFromName(blob)
            blob.qpath_gitem.setBrush(brush)

        self.updateVisibility()

