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

# THIS FILE CONTAINS UTILITY FUNCTIONS, E.G. CONVERSION BETWEEN DATA TYPES, BASIC OPERATIONS, ETC.

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, qRgb, qRgba
import numpy as np
import math
from skimage.draw import line

def clampCoords(x, y, W, H):

    if x < 0:
        x = 0
    if y < 0:
        y = 0
    if x > W:
        x = W
    if y > H:
        y = H

    return (x, y)


def draw_open_polygon(r, c):
    r = np.round(r).astype(int)
    c = np.round(c).astype(int)

    # Construct line segments
    rr, cc = [], []
    for i in range(len(r) - 1):
        line_r, line_c = line(r[i], c[i], r[i + 1], c[i + 1])
        rr.extend(line_r)
        cc.extend(line_c)

    rr = np.asarray(rr)
    cc = np.asarray(cc)

    return rr, cc


def showMaskAndCurve(mask, bbox, curve, fig_number):
    import matplotlib.pyplot as plt
    
    arr = mask.copy()

    if curve is not None:
        for i in range(curve.shape[0]):
            xx = curve[i, 0] - bbox[1]
            yy = curve[i, 1] - bbox[0]
            if xx >= 0 and yy >= 0 and xx < bbox[2] and yy < bbox[3]:
                arr[yy, xx] = 2

    plt.figure(fig_number)
    plt.imshow(arr)
    plt.show()

def maskToQImage(mask):

    h = mask.shape[0]
    w = mask.shape[1]
    qimg = QImage(w, h, QImage.Format_RGB32)
    qimg.fill(qRgb(0, 0, 0))

    for y in range(h):
        for x in range(w):

            if mask[y, x] == 1:
                qimg.setPixel(x, y, qRgb(255, 255, 255))

    return qimg

def labelsToQImage(mask):

    h = mask.shape[0]
    w = mask.shape[1]
    qimg = QImage(w, h, QImage.Format_RGB32)
    qimg.fill(qRgb(0, 0, 0))

    for y in range(h):
        for x in range(w):
            c = mask[y, x]
            qimg.setPixel(x, y, qRgb(c*17, c*163, c*211))

    return qimg

def floatmapToQImage(floatmap):

    h = floatmap.shape[0]
    w = floatmap.shape[1]
    qimg = QImage(w, h, QImage.Format_RGB32)

    qimg.fill(qRgb(0,0,0))

    for y in range(h):
        for x in range(w):
            gray = int(floatmap[y,x])
            qimg.setPixel(x,y,qRgb(gray,gray,gray))

    return qimg

def rgbToQImage(image):

    h = image.shape[0]
    w = image.shape[1]
    ch = image.shape[2]

    imgdata = np.zeros([h, w, 4], dtype=np.uint8)

    if ch == 3:
        imgdata[:, :, 2] = image[:, :, 0]
        imgdata[:, :, 1] = image[:, :, 1]
        imgdata[:, :, 0] = image[:, :, 2]
        imgdata[:, :, 3] = 255
        qimg = QImage(imgdata.data, w, h, QImage.Format_RGB32)

    elif ch == 4:
        imgdata[:, :, 3] = image[:, :, 0]
        imgdata[:, :, 2] = image[:, :, 1]
        imgdata[:, :, 1] = image[:, :, 2]
        imgdata[:, :, 0] = image[:, :, 3]
        qimg = QImage(imgdata.data, w, h, QImage.Format_ARGB32)

    return qimg.copy()

def prepareForDeepExtreme(qimage_map, four_points, pad_max):
    """
    Crop the image map (QImage) and return a NUMPY array containing it.
    It returns also the coordinates of the bounding box on the cropped image.
    """

    left = four_points[:, 0].min() - pad_max
    right = four_points[:, 0].max() + pad_max
    top = four_points[:, 1].min() - pad_max
    bottom = four_points[:, 1].max() + pad_max

    (xmin, ymin) = clampCoords(left, top, qimage_map.width(), qimage_map.height())
    (xmax, ymax) = clampCoords(right, bottom, qimage_map.width(), qimage_map.height())

    w = xmax - xmin
    h = ymax - ymin
    qimage_cropped = qimage_map.copy(xmin, ymin, w, h)

    fmt = qimage_cropped.format()
    assert(fmt == QImage.Format_RGB32)

    arr = np.zeros((h, w, 3), dtype=np.uint8)

    bits = qimage_cropped.bits()
    bits.setsize(int(h*w*4))
    arrtemp = np.frombuffer(bits, np.uint8).copy()
    arrtemp = np.reshape(arrtemp, [h, w, 4])
    arr[:, :, 0] = arrtemp[:, :, 2]
    arr[:, :, 1] = arrtemp[:, :, 1]
    arr[:, :, 2] = arrtemp[:, :, 0]

    # update four point
    four_points_updated = np.zeros((4,2), dtype=np.int)
    four_points_updated[:, 0] = four_points[:, 0] - xmin
    four_points_updated[:, 1] = four_points[:, 1] - ymin

    return (arr, four_points_updated)


def cropQImage(qimage_map, bbox):

    left = bbox[1]
    top = bbox[0]
    h = bbox[3]
    w = bbox[2]

    qimage_cropped = qimage_map.copy(left, top, w, h)

    return qimage_cropped


def qimageToNumpyArray(qimg):

    w = qimg.width()
    h = qimg.height()

    fmt = qimg.format()
    assert (fmt == QImage.Format_RGB32)

    arr = np.zeros((h, w, 3), dtype=np.uint8)

    bits = qimg.bits()
    bits.setsize(int(h * w * 4))
    arrtemp = np.frombuffer(bits, np.uint8).copy()
    arrtemp = np.reshape(arrtemp, [h, w, 4])
    arr[:, :, 0] = arrtemp[:, :, 2]
    arr[:, :, 1] = arrtemp[:, :, 1]
    arr[:, :, 2] = arrtemp[:, :, 0]

    return arr

def prepareLabelForDeepExtreme(qimage_map, four_points, pad_max):
    """
    Crop the image map (QImage) and return a NUMPY array containing it.
    It returns also the coordinates of the bounding box on the cropped image.
    """

    left = four_points[:, 0].min() - pad_max
    right = four_points[:, 0].max() + pad_max
    top = four_points[:, 1].min() - pad_max
    bottom = four_points[:, 1].max() + pad_max

    (xmin, ymin) = clampCoords(left, top, qimage_map.width(), qimage_map.height())
    (xmax, ymax) = clampCoords(right, bottom, qimage_map.width(), qimage_map.height())

    w = xmax - xmin
    h = ymax - ymin
    qimage_cropped = qimage_map.copy(xmin, ymin, w, h)

    fmt = qimage_cropped.format()
    assert(fmt == QImage.Format_RGB32)

    arr = np.zeros((h, w, 1), dtype=np.uint8)

    bits = qimage_cropped.bits()
    bits.setsize(int(h*w*4))
    arrtemp = np.frombuffer(bits, np.uint8).copy()
    arrtemp = np.reshape(arrtemp, [h, w, 4])

    for y in range(h):
        for x in range(w):
            if arrtemp[y, x, 2] != 0 or arrtemp[y, x, 1] != 0 or arrtemp[y, x, 0] != 0:
                arr[y, x] = 1

    # update four point
    four_points_updated = np.zeros((4,2), dtype=np.int)
    four_points_updated[:, 0] = four_points[:, 0] - xmin
    four_points_updated[:, 1] = four_points[:, 1] - ymin

    return (arr, four_points_updated)