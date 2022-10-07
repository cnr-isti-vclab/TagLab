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

import io
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, qRgb, qRgba
import numpy as np
import cv2
from skimage.draw import line
import datetime

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


def isValidDate(txt):
    """
    Check if a date in the ISO format YYYY-MM-DD is valid.
    """

    valid = True
    try:
        datetime.datetime.strptime(txt, '%Y-%m-%d')
#        datetime.date.fromisoformat(txt)
    except:
        valid = False

    return valid

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

    maskrgb = np.zeros((mask.shape[0], mask.shape[1], 3))
    maskrgb[:,:,0] = mask
    maskrgb[:,:,1] = mask
    maskrgb[:,:,2] = mask
    maskrgb = maskrgb * 255
    maskrgb = maskrgb.astype(np.uint8)

    qimg = rgbToQImage(maskrgb)
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


def binaryMaskToRle(mask):
    rle = {'counts': [], 'size': list(mask.shape)}
    counts = rle.get('counts')

    last_elem = 0
    running_length = 0

    for i, elem in enumerate(mask.ravel(order='F')):
        if elem == last_elem:
            pass
        else:
            counts.append(running_length)
            running_length = 0
            last_elem = elem
        running_length += 1

    counts.append(running_length)

    return rle


def floatmapToQImage(floatmap, nodata = float('NaN')):

    h = floatmap.shape[0]
    w = floatmap.shape[1]

    fmap = floatmap.copy()
    max_value = np.max(fmap)
    fmap[fmap == nodata] = max_value
    min_value = np.min(fmap)

    fmap = (fmap - min_value) / (max_value - min_value)
    fmap = 255.0 * fmap
    fmap = fmap.astype(np.uint8)

    img = np.zeros([h, w, 3], dtype=np.uint8)
    img[:,:,0] = fmap
    img[:,:,1] = fmap
    img[:,:,2] = fmap

    qimg = rgbToQImage(img)

    del fmap

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

def figureToQPixmap(fig, dpi, width, height):

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    buf.seek(0)
    img_arr = np.frombuffer(buf.getvalue(), dtype=np.uint8)
    buf.close()
    im = cv2.imdecode(img_arr, 1)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

    # numpy array to QPixmap
    qimg = rgbToQImage(im)
    qimg = qimg.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    pxmap = QPixmap.fromImage(qimg)

    return pxmap

def cropQImage(qimage_map, bbox):

    left = bbox[1]
    top = bbox[0]
    h = bbox[3]
    w = bbox[2]

    qimage_cropped = qimage_map.copy(left, top, w, h)

    return qimage_cropped

def cropImage(img, bbox):
    """
    Copy the given mask inside the box used to crop the plot.
    Both joint_box and bbox are n map coordinates.
    """

    w_img = img.shape[1]
    h_img = img.shape[0]

    w = bbox[2]
    h = bbox[3]
    crop = np.zeros((h, w, 3), dtype=np.uint8)

    dest_offx = 0
    dest_offy = 0
    source_offx = bbox[1]
    source_offy = bbox[0]
    source_w = w
    source_h = h

    if bbox[0] < 0:
        source_offy = 0
        dest_offy = -bbox[0]
        source_h = h - dest_offy

    if bbox[1] < 0:
        source_offx = 0
        dest_offx = -bbox[1]
        source_w = w - dest_offx

    if bbox[1] + bbox[2] >= w_img:
        dest_offx = 0
        source_w = w_img - source_offx

    if bbox[0] + bbox[3] >= h_img:
        dest_offy = 0
        source_h = h_img - source_offy

    crop[dest_offy:dest_offy+source_h, dest_offx:dest_offx+source_w, :] = \
        img[source_offy:source_offy+source_h, source_offx:source_offx+source_w, :]

    return crop

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

def autolevel(img, percent):

    '''
       Determine the histogram for each RGB channel and find the quantiles that correspond to our desired saturation level
       Cut off the outlying values by saturating a certain percentage of the pixels to black and white
       Scale the saturated histogram to span the full 0-255 range
    '''

    out_channels = []
    # mask background (it can be black or white)
    maskblack = ~ (np.any(img == [0, 0, 0], axis=-1))
    maskwhite = ~ (np.any(img == [255, 255, 255], axis=-1))
    mask = ((maskblack & maskwhite)).astype(np.uint8) * 255
    numpx= cv2.countNonZero(mask)
    cumstops = (
       numpx * percent / 200.0,
       numpx * (1 - percent / 200.0)
    )

    for channel in cv2.split(img):
        cumhist = np.cumsum(cv2.calcHist([channel], [0], mask, [256], (0, 256)))
        # find indices about where insert cumstops in cumhist mantaining the order
        low_cut, high_cut = np.searchsorted(cumhist, cumstops)
        high_cut = min(high_cut,255)
        # saturate below the low percentile and above the high percentile, lut apply a color mapping to the image
        lut = np.concatenate((
            np.zeros(low_cut),
            np.around(np.linspace(0, 255, high_cut - low_cut + 1)),
            255 * np.ones(255 - high_cut)
        ))
        #apply the colormap for each channel
        out_channels.append(cv2.LUT(channel, lut.astype('uint8')))

    return cv2.merge(out_channels)


def whiteblance(img):
    """  Dynamic threshold algorithm ---- white point detection and white point adjustment
         Note, this algoritm only handles white backgrounds png images.  If you have a white background in a jpg image the algorithm might fail to estimate
         valid correction values"""
    #  Read image
    b, g, r = cv2.split(img)

    # mask white pixels
    whitemask = (b > 254) & (g > 254) & (r > 254)

    #  Mean is three-channel
    h, w, c = img.shape

    def con_num(x):
        if x > 0:
            return 1
        if x < 0:
            return -1
        if x == 0:
            return 0

    yuv_img = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    #  YUV space
    (y, u, v) = cv2.split(yuv_img)

    y_masked = y.copy()
    y_masked[whitemask] = 0
    max_y = np.max(y_masked.flatten())

    sum_u, sum_v = np.sum(u), np.sum(v)
    avl_u, avl_v = sum_u / (h * w), sum_v / (h * w)
    du, dv = np.sum(np.abs(u - avl_u)), np.sum(np.abs(v - avl_v))
    avl_du, avl_dv = du / (h * w), dv / (h * w)
    radio = 0.5  #  If the value is too small, the color temperature develops to the pole
    valuekey = np.where((np.abs(u - (avl_u + avl_du * con_num(avl_u))) < radio * avl_du)
                         | (np.abs(v - (avl_v + avl_dv * con_num(avl_v))) < radio * avl_dv)
                         & ~whitemask)
    num_y, yhistogram = np.zeros((h, w)), np.zeros(256)
    num_y[valuekey] = np.uint8(y[valuekey])
    yhistogram = np.bincount(np.uint8(num_y[valuekey].flatten()), minlength=256)
    ysum = len(valuekey[0])
    Y = 255
    num, key = 0, 0
    while Y >= 0:
        num += yhistogram[Y]
        if num > 0.001 * ysum:  #  Take the first 0.1% highlights as the calculated value,
            key = Y
            break
        Y = Y - 1

    sumkey = np.where(num_y >= key)
    sum_b, sum_g, sum_r = np.sum(b[sumkey]), np.sum(g[sumkey]), np.sum(r[sumkey])
    num_rgb = len(sumkey[0])

    b0 = np.double(b) * int(max_y) / (sum_b / num_rgb)
    g0 = np.double(g) * int(max_y) / (sum_g / num_rgb)
    r0 = np.double(r) * int(max_y) / (sum_r / num_rgb)

    output_img = cv2.merge([b0, g0, r0])
    output_img[whitemask] = [255, 255, 255]

    return output_img

def setAttributes(project, data, object_list):

    count = 0
    for obj in object_list:
        row = data.iloc[count]
        count += 1
        for field in data.columns:
            if project.region_attributes.has(field):
                if row[field] is None:
                    continue
                if data.dtypes[field] == 'int64':
                    obj.data[field] = int(row[field])
                else:
                    obj.data[field] = row[field]

