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

import math
import bz2
import pickle
import numpy as np

from skimage import measure
from skimage.util import pad
from scipy import ndimage as ndi
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainterPath, QPolygonF, QImage, QPixmap, QBitmap, QPen, QBrush, QColor, QPainter, qRgb, qRgba
from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, QRectF, pyqtSlot, pyqtSignal

from skimage.segmentation import flood
from skimage.morphology import flood
from skimage.measure import points_in_poly
from skimage.draw import polygon_perimeter, polygon
from skimage.filters import gaussian
from skimage import segmentation

from source import utils

import pandas as pd

class Blob(object):
    """
    Blob data. A blob is a group of pixels.
    A blob can be tagged with the class and other information.
    Both the set of pixels and the corresponding vectorized version are stored.
    """

    def __init__(self, region, offset_x, offset_y, id):

        if region == None:

            # AN EMPTY BLOB IS CREATED..

            self.area = 0.0
            self.perimeter = 0.0
            self.centroid = np.zeros((2))
            self.bbox = np.zeros((4))

            # placeholder; empty contour
            self.contour = np.zeros((2, 2))
            self.inner_contours = []
            self.qpath = None
            self.qpath_gitem = None

            self.instance_name = "noname"
            self.blob_name = "noname"
            self.id = 0

        else:

            # extract properties

            self.centroid = np.array(region.centroid)
            cy = self.centroid[0]
            cx = self.centroid[1]
            self.centroid[0] = cx + offset_x
            self.centroid[1] = cy + offset_y

            # Bounding box (min_row, min_col, max_row, max_col).
            # Pixels belonging to the bounding box are in the half-open
            # interval [min_row, max_row) and [min_col, max_col).
            self.bbox = np.array(region.bbox)

            width = self.bbox[3] - self.bbox[1]
            height = self.bbox[2] - self.bbox[0]

            # BBOX ->  TOP, LEFT, WIDTH, HEIGHT
            self.bbox[0] = self.bbox[0] + offset_y
            self.bbox[1] = self.bbox[1] + offset_x
            self.bbox[2] = width
            self.bbox[3] = height

            # QPainterPath associated with the contours
            self.qpath = None

            # QGraphicsItem associated with the QPainterPath
            self.qpath_gitem = None

            # to extract the contour we use the mask cropped according to the bbox
            input_mask = region.image.astype(int)
            self.contour = np.zeros((2, 2))
            self.inner_contours = []
            self.createContourFromMask(input_mask)
            self.setupForDrawing()

            self.calculatePerimeter()
            self.calculateArea(input_mask)

            # a string with a progressive number to identify the instance
            self.instance_name = "coral" + str(id)

            # a string with a progressive number to identify the blob plus its centroid
            xc = int(self.centroid[0])
            yc = int(self.centroid[1])
            self.blob_name = "blob" + str(id) + "-" + str(xc) + "-" + str(yc)
            self.id = id

        # deep extreme points (for fine-tuning)
        self.deep_extreme_points = np.zeros((4, 2))

        # name of the class
        self.class_name = "Empty"

        # color of the class
        self.class_color = [128, 128, 128]

        # note about the coral, i.e. damage type
        self.note = ""

        # QImage corresponding to the current mask
        self.qimg_mask = None

        # QPixmap associated with the mask (for pixel-level editing operations)
        self.pxmap_mask = None

        # QGraphicsItem associated with the pixmap mask
        self.pxmap_mask_gitem = None

        # membership group (if any)
        self.group = None

    def copy(self):

        blob = Blob()

        blob.centroid = self.centroid.copy()
        blob.bbox = self.bbox.copy()

        blob.classname = self.classname
        blob.classcolor = self.classcolor
        blob.instance_name = self.instance_name
        blob.id = self.id
        blob.note = self.note

        return blob

    def getMask(self):
        """
        It creates the mask from the contour and returns it.
        """

        r = self.bbox[3]
        c = self.bbox[2]

        mask = np.zeros((r, c))

        # main polygon
        [rr, cc] = polygon(self.contour[:, 1], self.contour[:, 0])
        rr = rr - int(self.bbox[0])
        cc = cc - int(self.bbox[1])
        mask[rr, cc] = 1

        # holes
        for inner_contour in self.inner_contours:
            [rr, cc] = polygon(inner_contour[:, 1], inner_contour[:, 0])
            rr = rr - int(self.bbox[0])
            cc = cc - int(self.bbox[1])
            mask[rr, cc] = 0

        return mask


    def updateUsingMask(self, new_bbox, new_mask):

        self.bbox = new_bbox

        self.createContourFromMask(new_mask)
        self.setupForDrawing()

        self.calculatePerimeter()
        self.calculateArea(new_mask)
        self.calculateCentroid(new_mask)


    def snapToBorder(self, points):
        """
        Given a curve specified as a set of points, snap the curve on the blob mask:
          1) the initial segments of the curve are removed until they snap
          2) the end segments of the curve are removed until they snap

        """

        contour = self.contour.copy()
        test = points_in_poly(points, contour)
        jump = np.gradient(test.astype(int))
        ind = np.nonzero(jump)
        ind = np.asarray(ind)

        snappoints = None
        if ind.shape[1] > 2:
            first_el = ind[0, 0] + 1
            last_el = ind[0, -1]
            snappoints = points[first_el:last_el, :].copy()

        return snappoints

    def createCrack(self, input_arr, x, y, tolerance, preview=True):

        """
        Given a inner blob point (x,y), the function use it as a seed for a paint butcket tool and create
        a correspondent blob hole
        """

        x_crop = x - self.bbox[1]
        y_crop = y - self.bbox[0]

        input_arr = gaussian(input_arr, 2)
        # input_arr = segmentation.inverse_gaussian_gradient(input_arr, alpha=1, sigma=1)

        blob_mask = self.getMask()

        crack_mask = flood(input_arr, (int(y_crop), int(x_crop)), tolerance=tolerance).astype(int)
        cracked_blob = np.logical_and((blob_mask > 0), (crack_mask < 1))
        cracked_blob = cracked_blob.astype(int)

        if preview:
            return cracked_blob
        else:
            self.updateUsingMask(self.bbox, cracked_blob)
            return cracked_blob


    def addToMask(self, points):
        """
        Given a curve specified as a set of points, the pixels OUTSIDE the blob but inside the handle created
        by the curve are added to the blob.
        """

        # store the original inner contours (i.e. the holes)
        original_inner_contours = []
        for inner_contour in self.inner_contours:
            duplicate_inner_contour = inner_contour.copy()
            original_inner_contours.append(duplicate_inner_contour)

        # enlarge the mask
        y1A = self.bbox[0]
        x1A = self.bbox[1]
        x2A = x1A + self.bbox[2]
        y2A = y1A + self.bbox[3]

        pt_min = np.amin(points, axis=0)
        xmin = pt_min[0]
        ymin = pt_min[1]
        pt_max = np.amax(points, axis=0)
        xmax = pt_max[0]
        ymax = pt_max[1]

        x1B = int(xmin)
        y1B = int(ymin)
        x2B = int(xmax)
        y2B = int(ymax)

        x_left = min(x1A, x1B) - 2
        y_top = min(y1A, y1B) - 2
        x_right = max(x2A, x2B) + 2
        y_bottom = max(y2A, y2B) + 2

        bbox_union = np.array([y_top, x_left, x_right - x_left, y_bottom - y_top])
        mask_union = np.zeros((bbox_union[3], bbox_union[2]))

        blob_mask = self.getMask()
        for y in range(blob_mask.shape[0]):
            for x in range(blob_mask.shape[1]):

                yy = y + (self.bbox[0] - bbox_union[0])
                xx = x + (self.bbox[1] - bbox_union[1])
                mask_union[yy,xx] = blob_mask[y,x]


        for i in range(points.shape[0]):

            x = points[i, 0]
            y = points[i, 1]

            yy = int(y) - bbox_union[0]
            xx = int(x) - bbox_union[1]

            for offsetx in range(-1,2):
                for offsety in range(-1,2):
                    mask_union[yy + offsety, xx + offsetx] = 1

        mask_union = ndi.binary_fill_holes(mask_union).astype(int)

        self.updateUsingMask(bbox_union, mask_union)

        # RE-ADD THE ORIGINAL INNER CONTOURS (I.E. THE HOLES)
        if original_inner_contours:
            self.inner_contours.clear()
            for inner_contour in original_inner_contours:

                # recover inner contour list
                self.inner_contours.append(inner_contour)

            # update qpainterpath
            self.setupForDrawing()


    def cutFromMask(self, points):
        """
        Given a curve specified as a set of points, the pixels INSIDE the blob but "cutted" by the curve
        are removed from the blob.
        """

        # enlarge the mask
        y1A = self.bbox[0]
        x1A = self.bbox[1]
        x2A = x1A + self.bbox[2]
        y2A = y1A + self.bbox[3]

        pt_min = np.amin(points, axis=0)
        xmin = pt_min[0]
        ymin = pt_min[1]
        pt_max = np.amax(points, axis=0)
        xmax = pt_max[0]
        ymax = pt_max[1]

        x1B = int(xmin)
        y1B = int(ymin)
        x2B = int(xmax)
        y2B = int(ymax)

        x_left = min(x1A, x1B) - 2
        y_top = min(y1A, y1B) - 2
        x_right = max(x2A, x2B) + 2
        y_bottom = max(y2A, y2B) + 2

        bbox_union = np.array([y_top, x_left, x_right - x_left, y_bottom - y_top])
        mask_union = np.zeros((bbox_union[3], bbox_union[2]))

        blob_mask = self.getMask()
        for y in range(blob_mask.shape[0]):
            for x in range(blob_mask.shape[1]):

                yy = y + (self.bbox[0] - bbox_union[0])
                xx = x + (self.bbox[1] - bbox_union[1])
                mask_union[yy,xx] = blob_mask[y,x]

        for i in range(points.shape[0]):

            x = points[i, 0]
            y = points[i, 1]

            yy = int(y) - bbox_union[0]
            xx = int(x) - bbox_union[1]

            for offsetx in range(-1,2):
                for offsety in range(-1,2):
                    mask_union[yy + offsety, xx + offsetx] = 0

        label_image = measure.label(mask_union)
        regions = measure.regionprops(label_image)

        if len(regions) > 1:

            # TENERE SOLO QUELLA CON AREA MASSIMA ??

            area_max = 0
            region_to_remove = None
            for region in regions:

                if region.area> area_max:
                   area_max = region.area

            for region in regions:
                if region.area < area_max:
                  for coords in region.coords:
                      mask_union[coords[0], coords[1]] = 0

        self.updateUsingMask(bbox_union, mask_union)


    def createContourFromMask(self, mask):
        """
        It creates the contour (and the corrisponding polygon) from the blob mask.
        """

        # NOTE: The mask is expected to be cropped around its bbox (!!) (see the __init__)

        self.inner_contours.clear()

        # we need to pad the mask to avoid to break the contour that touchs the borders
        PADDED_SIZE = 2
        img_padded = pad(mask, (PADDED_SIZE, PADDED_SIZE), mode="constant", constant_values=(0, 0))

        contours = measure.find_contours(img_padded, 0)

        number_of_contours = len(contours)

        if number_of_contours > 1:

            # search the longest contour
            npoints_max = 0
            index = 0
            for i, contour in enumerate(contours):
                npoints = contour.shape[0]
                if npoints > npoints_max:
                    npoints_max = npoints
                    index = i

            # divide the contours in OUTER contour and INNER contours
            for i, contour in enumerate(contours):
                coords = measure.approximate_polygon(contour, tolerance=1.2)
                if i == index:
                    self.contour = np.array(coords)
                else:
                    coordinates = np.array(coords)
                    self.inner_contours.append(coordinates)

            # adjust the coordinates of the outer contour
            # (NOTE THAT THE COORDINATES OF THE BBOX ARE IN THE GLOBAL MAP COORDINATES SYSTEM)
            for i in range(self.contour.shape[0]):
                ycoor = self.contour[i, 0]
                xcoor = self.contour[i, 1]
                self.contour[i, 0] = xcoor - PADDED_SIZE + self.bbox[1]
                self.contour[i, 1] = ycoor - PADDED_SIZE + self.bbox[0]

            # adjust coordinates of the INNER contours
            for j, contour in enumerate(self.inner_contours):
                for i in range(contour.shape[0]):
                    ycoor = contour[i, 0]
                    xcoor = contour[i, 1]
                    self.inner_contours[j][i, 0] = xcoor - PADDED_SIZE + self.bbox[1]
                    self.inner_contours[j][i, 1] = ycoor - PADDED_SIZE + self.bbox[0]

        elif number_of_contours == 1:

            coords = measure.approximate_polygon(contours[0], tolerance=1.2)
            self.contour = np.array(coords)

            # adjust the coordinates of the outer contour
            # (NOTE THAT THE COORDINATES OF THE BBOX ARE IN THE GLOBAL MAP COORDINATES SYSTEM)
            for i in range(self.contour.shape[0]):
                ycoor = self.contour[i, 0]
                xcoor = self.contour[i, 1]
                self.contour[i, 0] = xcoor - PADDED_SIZE + self.bbox[1]
                self.contour[i, 1] = ycoor - PADDED_SIZE + self.bbox[0]
        else:

            print("ZERO CONTOURS -> THERE ARE SOME PROBLEMS HERE !!!!!!)")

    def setupForDrawing(self):
        """
        Create the QPolygon and the QPainterPath according to the blob's contours.
        """

        # QPolygon to draw the blob
        qpolygon = QPolygonF()
        for i in range(self.contour.shape[0]):
            qpolygon << QPointF(self.contour[i, 0], self.contour[i, 1])

        self.qpath = QPainterPath()
        self.qpath.addPolygon(qpolygon)

        for inner_contour in self.inner_contours:
            qpoly_inner = QPolygonF()
            for i in range(inner_contour.shape[0]):
                qpoly_inner << QPointF(inner_contour[i, 0], inner_contour[i, 1])

            path_inner = QPainterPath()
            path_inner.addPolygon(qpoly_inner)
            self.qpath = self.qpath.subtracted(path_inner)

    def createQPixmapFromMask(self):

        w = self.bbox[2]
        h = self.bbox[3]
        self.qimg_mask = QImage(w, h, QImage.Format_ARGB32)
        self.qimg_mask.fill(qRgba(0, 0, 0, 0))

        if self.class_name == "Empty":
            rgba = qRgba(255, 255, 255, 255)
        else:
            rgba = qRgba(self.class_color[0], self.class_color[1], self.class_color[2], 100)

        blob_mask = self.getMask()
        for x in range(w):
            for y in range(h):
                if mask[y, x] == 1:
                    self.qimg_mask.setPixel(x, y, rgba)

        self.pxmap_mask = QPixmap.fromImage(self.qimg_mask)

    def calculateCentroid(self, mask):

        sumx = 0.0
        sumy = 0.0
        n = 0

        for y in range(mask.shape[0]):
            for x in range(mask.shape[1]):
                if mask[y, x] == 1:
                    sumx += float(x)
                    sumy += float(y)
                    n += 1

        # NOTE: centroid is (x,y), bbox is [width height]
        self.centroid[0] = int(sumx / n) + self.bbox[1]
        self.centroid[1] = int(sumy / n) + self.bbox[0]

        xc = int(self.centroid[0])
        yc = int(self.centroid[1])
        self.instance_name = "coral-" + str(xc) + "-" + str(yc)

    def calculateContourPerimeter(self, contour):

        # perimeter of the outer contour
        px1 = contour[0, 0]
        py1 = contour[0, 1]
        N = contour.shape[0]
        pxlast = contour[N-1, 0]
        pylast = contour[N-1, 1]
        perim = math.sqrt((px1-pxlast)*(px1-pxlast) + (py1-pylast)*(py1-pylast))
        for i in range(1, contour.shape[0]):
            px2 = contour[i, 0]
            py2 = contour[i, 1]

            d = math.sqrt((px1 - px2)*(px1-px2) + (py1-py2)*(py1-py2))
            perim += d

            px1 = px2
            py1 = py2

        return perim

    def calculatePerimeter(self):

        self.perimeter = self.calculateContourPerimeter(self.contour)

        for contour in self.inner_contours:
            self.perimeter += self.calculateContourPerimeter(self.contour)

    def calculateArea(self, mask):

        self.area = 0.0
        for y in range(mask.shape[0]):
            for x in range(mask.shape[1]):
                if mask[y, x] == 1:
                    self.area += 1.0

    def fromDict(self, dict):
        """
        Set the blob information given it represented as a dictionary.
        """

        self.bbox = np.asarray(dict["bbox"])

        self.centroid = np.asarray(dict["centroid"])
        self.area = dict["area"]
        self.perimeter = dict["perimeter"]

        self.contour = np.asarray(dict["contour"])
        inner_contours = dict["inner contours"]
        self.inner_contours = []
        for c in inner_contours:
            self.inner_contours.append(np.asarray(c))

        self.deep_extreme_points = np.asarray(dict["deep_extreme_points"])
        self.class_name = dict["class name"]
        self.class_color = dict["class color"]
        self.instance_name = dict["instance name"]
        self.blob_name = dict["blob name"]
        self.id = dict["id"]
        self.note = dict["note"]

        # finalize blob
        self.setupForDrawing()


    def toDict(self):
        """
        Get the blob information as a dictionary.
        """

        dict = {}

        dict["bbox"] = self.bbox.tolist()

        dict["centroid"] = self.centroid.tolist()
        dict["area"] = self.area
        dict["perimeter"] = self.perimeter

        dict["contour"] = self.contour.tolist()

        dict["inner contours"] = []
        for c in self.inner_contours:
            dict["inner contours"].append(c.tolist())

        dict["deep_extreme_points"] = self.deep_extreme_points.tolist()

        dict["class name"] = self.class_name
        dict["class color"] = self.class_color

        dict["instance name"] = self.instance_name
        dict["blob name"] = self.blob_name
        dict["id"] = self.id
        dict["note"] = self.note

        return dict


class Group(object):

    def __init__(self, blobs, id):

        # list of the blobs that form this group
        self.blobs = []
        for blob in blobs:
            self.blobs.append(blob)

        for blob in blobs:

            blob.group = self

        # centroid of the group
        sumx = 0.0
        sumy = 0.0
        n = 0
        for blob in self.blobs:
            blob_mask = blob.getMask()
            for y in range(blob_mask.shape[0]):
                for x in range(blob_mask.shape[1]):
                    if blob_mask[y, x] == 1:
                        sumx += float(x + blob.bbox[1])
                        sumy += float(y + blob.bbox[0])
                        n += 1

        cx = sumx / n
        cy = sumy / n

        self.centroid = np.zeros((2))
        self.centroid[0] = cx
        self.centroid[1] = cy

        # update instance name for each blob
        for blob in self.blobs:
            blob.instace_name = "coral-group-" + str(id)


class Annotation(object):
    """
        Annotation object contains all the annotations as a list of blobs.
    """

    def __init__(self):

        # list of all blobs
        self.seg_blobs = []

        # list of all groups
        self.groups = []


    def addGroup(self, blobs):

        id = len(self.groups)
        group = Group(blobs, id+1)
        self.groups.append(group)
        return group

    def addBlob(self, seg_mask, map_pos_x, map_pos_y, area_mask):

        # create the blobs from the segmentation mask

        last_blobs_added = []

        seg_mask = ndi.binary_fill_holes(seg_mask).astype(int)
        label_image = measure.label(seg_mask)

        area_th = area_mask * 0.2

        for region in measure.regionprops(label_image):

            if region.area > area_th:

                id = len(self.seg_blobs)
                blob = Blob(region, map_pos_x, map_pos_y, id+1)
                self.seg_blobs.append(blob)

                last_blobs_added.append(blob)

        return last_blobs_added

    def removeGroup(self, group):

        # the blobs no more belong to this group
        for blob in group.blobs:
            blob.group = None
            blob.instace_name = "coral" + str(blob.id)

        # remove from the list of the groups
        index = self.groups.index(group)
        del self.groups[index]

    def removeBlob(self, blob):

        # remove from the list of the blobs
        index = self.seg_blobs.index(blob)
        del self.seg_blobs[index]

    def as_dict(self, i):

        blob = self.seg_blobs[i]
        return {'coral name': blob.blob_name, 'group name': blob.group, 'class name': blob.class_name, ' centroid ': blob.centroid, 'coral area': blob.area, 'coral perimeter': blob.perimeter}

    def union(self, blobs):
        """
        Create a new blob that is the union of the (two) blobs given
        """

        blobA = blobs[0]
        blobB = blobs[1]

        y1A = blobA.bbox[0]
        x1A = blobA.bbox[1]
        x2A = x1A + blobA.bbox[2]
        y2A = y1A + blobA.bbox[3]

        y1B = blobB.bbox[0]
        x1B = blobB.bbox[1]
        x2B = x1B + blobB.bbox[2]
        y2B = y1B + blobB.bbox[3]

        x_left = min(x1A, x1B)
        y_top = min(y1A, y1B)
        x_right = max(x2A, x2B)
        y_bottom = max(y2A, y2B)

        bbox_union = np.array([y_top, x_left, x_right - x_left, y_bottom - y_top])
        mask_union = np.zeros((bbox_union[3], bbox_union[2]))

        blobA_mask = blobA.getMask()
        blobB_mask = blobB.getMask()

        for y in range(y1A, y2A):
            for x in range(x1A, x2A):

                xA = x - blobA.bbox[1]
                yA = y - blobA.bbox[0]

                xU = x - bbox_union[1]
                yU = y - bbox_union[0]

                if blobA_mask[yA, xA] == 1:
                    mask_union[yU, xU] = 1

        pixels_intersected = 0
        for y in range(y1B, y2B):
            for x in range(x1B, x2B):

                xB = x - blobB.bbox[1]
                yB = y - blobB.bbox[0]

                xU = x - bbox_union[1]
                yU = y - bbox_union[0]

                if blobB_mask[yB, xB] == 1:
                    if mask_union[yU, xU] == 1:
                        pixels_intersected += 1

                    mask_union[yU, xU] = 1

        if pixels_intersected > 0:

            blobA.updateUsingMask(bbox_union, mask_union)

            return True

        else:

            return False


    def subtract(self, blobA, blobB, scene):
        """
        Create a new blob that subtracting the second blob from the first one
        """

        y1A = blobA.bbox[0]
        x1A = blobA.bbox[1]
        x2A = x1A + blobA.bbox[2]
        y2A = y1A + blobA.bbox[3]

        y1B = blobB.bbox[0]
        x1B = blobB.bbox[1]
        x2B = x1B + blobB.bbox[2]
        y2B = y1B + blobB.bbox[3]

        x_left = max(x1A, x1B)
        y_top = max(y1A, y1B)
        x_right = min(x2A, x2B)
        y_bottom = min(y2A, y2B)

        # check if the selection is empty
        if x_right < x_left or y_bottom < y_top:
            return False
        else:

            xinf = x_left - blobA.bbox[1]
            yinf = y_top - blobA.bbox[0]
            xsup = x_right - blobA.bbox[1]
            ysup = y_bottom - blobA.bbox[0]

            blobA_mask = blobA.getMask()
            blobB_mask = blobB.getMask()

            flag = False
            for y in range(yinf, ysup):
                for x in range(xinf, xsup):

                    xB = x + blobA.bbox[1] - blobB.bbox[1]
                    yB = y + blobA.bbox[0] - blobB.bbox[0]

                    if blobB_mask[yB, xB] == 1:
                        blobA_mask[y, x] = 0
                        flag = True  # at least one pixel intersect

            # bbox is the same
            # mask has been updated directly
            if flag:
                blobA.updateUsingMask(blobA.bbox, blobA_mask)
                return True
            else:
                return False


    def statistics(self):
        """
        Print some statistics about the current annotations.
        """

        number_of_seg = len(self.seg_blobs)
        dimensions = np.zeros(number_of_seg)
        for i, blob in enumerate(self.seg_blobs):

            dimensions[i] = blob.size()

        print("-------------------------")
        print("Total seg. blobs : %d" % number_of_seg)
        print("Minimum size     : %d" % np.min(dimensions))
        print("Maximum size     : %d" % np.max(dimensions))
        print("Size deviation   : %f" % np.std(dimensions))
        print("-------------------------")

    def clickedBlob(self, x, y):
        """
        It returns the blob clicked with the smallest area (to avoid problems with overlapping blobs).
        """

        blobs_clicked = []

        for blob in self.seg_blobs:

            point = np.array([[x, y]])
            out = measure.points_in_poly(point, blob.contour)
            if out[0] == True:
                blobs_clicked.append(blob)

        area_min = 100000000.0
        selected_blob = None
        for i in range(len(blobs_clicked)):
            blob = blobs_clicked[i]
            if blob.area < area_min:
                area_min = blob.area
                selected_blob = blob

        return selected_blob

    def export_data_table_for_Scripps(self, filename):

        # create a list of properties
        properties = ['Class name', 'Centroid x', 'Centroid y', 'Coral area', 'Coral perimeter', 'Coral maximum diameter', 'Coral note']

        # create a list of instances
        name_list = []
        for blob in self.seg_blobs:
            index = blob.blob_name
            name_list.append(index)

        number_of_seg = len(self.seg_blobs)
        class_name = []
        centroid_x = np.zeros(number_of_seg)
        centroid_y = np.zeros(number_of_seg)
        coral_area = np.zeros(number_of_seg)
        coral_perimeter = np.zeros(number_of_seg)
        coral_maximum_diameter = np.zeros(number_of_seg)
        coral_note = []

        for i, blob in enumerate(self.seg_blobs):
            class_name.append(blob.class_name)
            centroid_x[i] = blob.centroid[0]
            centroid_y[i] = blob.centroid[1]
            coral_area[i] = blob.area
            coral_perimeter[i] = blob.perimeter
            #coral_maximum_diameter[i] = blob.major_axis_length
            coral_note.append(blob.note)


        # create a dictionary
        dic = {
            'Class name': class_name,
            'Centroid x': centroid_x,
            'Centroid y': centroid_y,
            'Coral area': coral_area,
            'Coral perimeter': coral_perimeter,
            'Coral maximum diameter': coral_maximum_diameter,
            'Coral note': coral_note }

        # create dataframe
        df = pd.DataFrame(dic, columns=properties, index=name_list)
        df.to_csv(filename, sep='\t')

    def export_image_data_for_Scripps(self, map, filename):

        # create a black canvas of the same size of your map
        w = map.width()
        h = map.height()

        myPNG = QImage(w, h, QImage.Format_RGB32)
        myPNG.fill(qRgb(0, 0, 0))

        for i, blob in enumerate(self.seg_blobs):

            if blob.class_color == "Empty":
                rgb = qRgb(255, 255, 255)
            else:
                rgb = qRgb(blob.class_color[0], blob.class_color[1], blob.class_color[2])

            blob_mask = blob.getMask()
            for x in range(blob_mask.shape[1]):
                for y in range(blob_mask.shape[0]):

                    if blob_mask[y, x] == 1:
                        myPNG.setPixel(x + blob.bbox[1], y + blob.bbox[0], rgb)

            # draw black border
            [rr, cc] = polygon_perimeter(blob.contour[:, 1], blob.contour[:, 0])
            if rr.size > 0:
                for i in range(len(rr)):
                    myPNG.setPixel(cc[i], rr[i], qRgb(0, 0, 0))

        myPNG.save(filename)


