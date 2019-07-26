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

import math
import numpy as np
import pickle
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainter, QBrush, QPen, QColor, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene


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

        self.setStyleSheet("color: rgb(49,51,53)")



        MIN_SIZE = 300
        MAX_SIZE = 500

        self.THUMB_SIZE = preferred_size

        if self.THUMB_SIZE > MAX_SIZE:
            self.THUMB_SIZE = MAX_SIZE

        if self.THUMB_SIZE < MIN_SIZE:
            self.THUMB_SIZE = MIN_SIZE

        self.BORDER_SIZE = 2

        # Image is displayed as a QPixmap in a QGraphicsScene attached to this QGraphicsView.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Store a local handle to the scene's current image pixmap.
        self._pxmapitem = None

        # Image aspect ratio mode.
        self.aspectRatioMode = Qt.KeepAspectRatio

        # Set scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Panning is enabled if and only if the image is greater than the viewport.
        self.panEnabled = False

        # zoom is always active
        self.zoom_factor = 1.0

        # transparency
        self.opacity = 1.0

        self.pixmap = QPixmap(MIN_SIZE, MIN_SIZE)

        self.HIGHLIGHT_RECT_WIDTH = 10
        self.HIGHLIGHT_RECT_HEIGHT = 10
        self.HIGHLIGHT_COLOR = QColor(200, 200, 200)
        self.overlay_image = QImage(self.HIGHLIGHT_RECT_WIDTH, self.HIGHLIGHT_RECT_HEIGHT, QImage.Format_ARGB32)
        self.overlay_image.fill(self.HIGHLIGHT_COLOR)

        self.viewport().setMinimumWidth(MIN_SIZE)
        self.viewport().setMinimumHeight(MIN_SIZE)
        self.setMaximumWidth(self.THUMB_SIZE + self.BORDER_SIZE)
        self.setMaximumHeight(self.THUMB_SIZE + self.BORDER_SIZE)

    def image(self):
        """ Returns the scene's current image as a QImage.
        """
        if self.hasImage():
            return self._pxmapitem.pixmap().toImage()
        return None

    def hasImage(self):
        """ Returns whether or not the scene contains an image pixmap.
        """
        return self._pxmapitem is not None

    def setImage(self, image):
        """ Set the scene's current image (input image must be a QImage)
        """
        if type(image) is QImage:
            imageARGB32 = image.convertToFormat(QImage.Format_ARGB32)
            self.pixmap = QPixmap.fromImage(imageARGB32)
            self.imgwidth = image.width()
            self.imgheight = image.height()
        else:
            raise RuntimeError("Argument must be a QImage.")

        if self.hasImage():
            self._pxmapitem.setPixmap(self.pixmap)
        else:
            self._pxmapitem = self.scene.addPixmap(self.pixmap)

        # Set scene size to image size (!)
        aspectratio = self.imgheight / self.imgwidth
        h = (int)(aspectratio * self.width())
        self.setMaximumHeight(h)
        self.setSceneRect(QRectF(self.pixmap.rect()))

        # calculate zoom factor
        pixels_of_border = 10
        zf1 = (self.geometry().width() - pixels_of_border) / self.imgwidth
        zf2 = (self.geometry().height() - pixels_of_border) / self.imgheight

        zf = min(zf1, zf2)
        if zf > 1.0:
            zf = 1.0

        self.zoom_factor = zf

        self.updateViewer()

    def setOpacity(self, opacity):
        self.opacity = opacity

    def loadImageFromFile(self, fileName=""):
        """ Load an image from file.
        """
        image = QImage(fileName)
        self.setImage(image)

    def drawOverlayImage(self, top, left, bottom, right):

        W = self.pixmap.width()
        H = self.pixmap.height()

        self.HIGHLIGHT_RECT_WIDTH = (right-left) * W
        self.HIGHLIGHT_RECT_HEIGHT = (bottom-top) * H
        self.HIGHLIGHT_RECT_POSX = left * W
        self.HIGHLIGHT_RECT_POSY = top * H
        self.overlay_image = QImage(self.HIGHLIGHT_RECT_WIDTH, self.HIGHLIGHT_RECT_HEIGHT, QImage.Format_ARGB32)
        self.overlay_image.fill(self.HIGHLIGHT_COLOR)

        if self.overlay_image.width() > 1:
            pxmap = self.pixmap.copy()
            p = QPainter()
            p.begin(pxmap)
            p.setOpacity(self.opacity)
            p.drawImage(self.HIGHLIGHT_RECT_POSX, self.HIGHLIGHT_RECT_POSY, self.overlay_image)
            p.end()

            self._pxmapitem.setPixmap(pxmap)

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        if not self.hasImage():
            return

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
        """ Maintain current zoom on resize.
        """

        pixels_of_border = 10
        zf1 = (self.geometry().width() - pixels_of_border) / self.imgwidth
        zf2 = (self.geometry().height() - pixels_of_border) / self.imgheight
        zf = min(zf1, zf2)
        if zf > 1.0:
            zf = 1.0

        self.zoom_factor = zf

        self.updateViewer()

    def mousePressEvent(self, event):

        scenePos = self.mapToScene(event.pos())
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

        if event.buttons() == Qt.LeftButton:

            clippedCoords = self.clipScenePos(scenePos)

            clippedCoords[0] = clippedCoords[0] / self.imgwidth
            clippedCoords[1] = clippedCoords[1] / self.imgheight

            self.mouseMoveLeftPressed.emit(clippedCoords[0], clippedCoords[1])


    def mouseDoubleClickEvent(self, event):

        QGraphicsView.mouseDoubleClickEvent(self, event)


