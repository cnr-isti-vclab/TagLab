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

# THIS FILE CONTAINS UTILITY FUNCTION USED BY DIFFERENT TOOLS

import io
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QBrush, QPen, qRgb, qRgba
import numpy as np
import cv2
from skimage.draw import line
import datetime

def drawBlob(blob, brush, scene, transparency_value, redraw=True):
    """
    Draw the given blob on the scene. Typically, it is used to draw regions for preview purposes (the draw of
    confirmed regions is managed by the main viewer).
    """

    # remove the current graphics item in order to set it again
    if blob.qpath_gitem is not None:
        scene.removeItem(blob.qpath_gitem)
        del blob.qpath_gitem
        blob.qpath_gitem = None

    blob.setupForDrawing()

    pen = QPen(Qt.white)
    pen.setWidth(2)
    pen.setCosmetic(True)

    brush.setStyle(Qt.Dense4Pattern)  # Dense4pattern is forced for this type of regions

    blob.qpath_gitem = scene.addPath(blob.qpath, pen, brush)
    blob.qpath_gitem.setZValue(1)
    blob.qpath_gitem.setOpacity(transparency_value)

    if redraw:
        scene.invalidate()

def undrawBlob(blob, scene, redraw=True):
    """
    Undraw a given blob from the scene. Used to undraw non-confirmed regions.
    """

    if blob.qpath_gitem is not None:
        scene.removeItem(blob.qpath_gitem)
        del blob.qpath_gitem
        blob.qpath_gitem = None

    blob.qpath = None

    if redraw:
        scene.invalidate()

def undrawAllBlobs(blobs, scene):
    """
    Undraw the region in the blobs list from the given scene. Used to undraw all the non-confirmed regions.
    """

    if blobs is not None:
        for blob in blobs:
            undrawBlob(blob, scene, redraw=False)

    scene.invalidate()