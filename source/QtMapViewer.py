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

""" PyQt map viewer widget.
"""

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QPainter, QBrush, QPen, QPalette, QColor, qRgb, qRgba, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QSizePolicy


class QtMapViewer(QGraphicsView):
    """
    PyQt map viewer widget.
    """

    # Mouse button signals emit image scene (x, y) coordinates.
    leftMouseButtonPressed = pyqtSignal(float, float)
    mouseMoveLeftPressed = pyqtSignal(float, float)

    # custom signal
    viewUpdated = pyqtSignal()

    def __init__(self, preferred_size):
        QGraphicsView.__init__(self)

        self.setStyleSheet("background-color: rgb(40,40,40); border:none")
        self.BORDER = 10

        # Image is displayed as a QPixmap in a QGraphicsScene attached to this QGraphicsView.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Image aspect ratio mode.
        self.aspectRatioMode = Qt.KeepAspectRatio

        # Set scrollbar
        #self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Panning is enabled if and only if the image is greater than the viewport.
        self.panEnabled = False

        # zoom is always active
        self.zoom_factor = 1.0

        # transparency
        self.opacity = 1.0

        self.HIGHLIGHT_RECT_WIDTH = 10
        self.HIGHLIGHT_RECT_HEIGHT = 10
        self.HIGHLIGHT_COLOR = QColor(200, 200, 200)
        self.overlay_image = QImage(self.HIGHLIGHT_RECT_WIDTH, self.HIGHLIGHT_RECT_HEIGHT, QImage.Format_ARGB32)
        self.overlay_image.fill(self.HIGHLIGHT_COLOR)

        self.pixmapitem = None

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #self.setMinimumHeight(100)
        #self.setMaximumHeight(350)
        #self.setMinimumWidth(100)
        #self.setMaximumWidth(600)

        #self.setFixedWidth(preferred_size)
        #self.setFixedHeight(preferred_size)

        self.imgwidth = 0
        self.imgheight = 0
        self.PREFERRED_SIZE = preferred_size
        
    def clear(self):

        if self.pixmapitem is not None:
            self.scene.removeItem(self.pixmapitem)
            self.pixmapitem = None

    def setNewWidth(self, width):

        self.setFixedWidth(width)

    def setPixmap(self, pixmap):

        self.pixmap = pixmap
        self.imgwidth = self.pixmap.width()
        self.imgheight = self.pixmap.height()

        if self.pixmapitem is None:
            self.pixmapitem = self.scene.addPixmap(self.pixmap)
        else:
            self.pixmapitem.setPixmap(self.pixmap)

        self.setSceneRect(QRectF(self.pixmap.rect()))

        if self.imgwidth > self.imgheight:
            aspectratio = self.imgheight / self.imgwidth
            h = (int)(aspectratio * self.geometry().width())
            if h > self.PREFERRED_SIZE:
                h = self.PREFERRED_SIZE
            #self.setFixedHeight(h)


        # calculate zoom factor
        pixels_of_border = self.BORDER
        zf1 = (self.geometry().width() - pixels_of_border) / self.imgwidth
        zf2 = (self.geometry().height() - pixels_of_border) / self.imgheight

        zf = min(zf1, zf2)
        if zf > 1.0:
            zf = 1.0

        self.zoom_factor = zf
        self.updateViewer()

    def setOpacity(self, opacity):
        self.opacity = opacity

    @pyqtSlot(QRectF)
    def drawOverlayImage(self, rect):

        if self.pixmapitem is not None:

            W = self.pixmap.width()
            H = self.pixmap.height()

            self.HIGHLIGHT_RECT_WIDTH = int(rect.width() * W)
            self.HIGHLIGHT_RECT_HEIGHT = int(rect.height() * H)
            self.HIGHLIGHT_RECT_POSX = int(rect.left() * W)
            self.HIGHLIGHT_RECT_POSY = int(rect.top() * H)
            self.overlay_image = QImage(self.HIGHLIGHT_RECT_WIDTH, self.HIGHLIGHT_RECT_HEIGHT, QImage.Format_ARGB32)
            self.overlay_image.fill(self.HIGHLIGHT_COLOR)

            if self.overlay_image.width() > 1:
                pxmap = self.pixmap.copy()
                p = QPainter()
                p.begin(pxmap)
                p.setOpacity(self.opacity)
                p.drawImage(self.HIGHLIGHT_RECT_POSX, self.HIGHLIGHT_RECT_POSY, self.overlay_image)
                p.end()

                self.pixmapitem.setPixmap(pxmap)

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        self.resetTransform()
        self.setTransformationAnchor(self.AnchorViewCenter)
        self.scale(self.zoom_factor, self.zoom_factor)

        #self.fitInView(self.sceneRect(), self.aspectRatioMode)

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

        return [posx, posy]

    def resizeEvent(self, event):
        """ Maintain current zoom on resize."""

        if self.imgwidth > 0 and self.imgheight > 0:
            pixels_of_border = self.BORDER
            zf1 = (self.geometry().width() - pixels_of_border) / self.imgwidth
            zf2 = (self.geometry().height() - pixels_of_border) / self.imgheight
            zf = min(zf1, zf2)
            if zf > 1.0:
                zf = 1.0

            self.zoom_factor = zf
            self.updateViewer()

    def mousePressEvent(self, event):

        scenePos = self.mapToScene(event.pos())
        if self.imgwidth == 0 or self.imgheight == 0:
            return

        if event.button() == Qt.LeftButton:
            if self.panEnabled:
                self.setDragMode(QGraphicsView.ScrollHandDrag)


            clippedCoords = self.clipScenePos(scenePos)
            clippedCoords[0] = clippedCoords[0] / self.imgwidth
            clippedCoords[1] = clippedCoords[1] / self.imgheight
            self.leftMouseButtonPressed.emit(clippedCoords[0], clippedCoords[1])

    def mouseMoveEvent(self, event):

        QGraphicsView.mouseMoveEvent(self, event)
        scenePos = self.mapToScene(event.pos())

        if self.imgwidth == 0 or self.imgheight == 0:
            return
        if event.buttons() == Qt.LeftButton:
            clippedCoords = self.clipScenePos(scenePos)
            clippedCoords[0] = clippedCoords[0] / self.imgwidth
            clippedCoords[1] = clippedCoords[1] / self.imgheight
            self.mouseMoveLeftPressed.emit(clippedCoords[0], clippedCoords[1])


    def mouseDoubleClickEvent(self, event):

        QGraphicsView.mouseDoubleClickEvent(self, event)


