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
import copy
import numpy as np

from skimage import measure
from scipy import ndimage as ndi
from PyQt5.QtGui import QPainterPath, QPolygonF
from PyQt5.QtCore import QPointF

from skimage.morphology import square, binary_dilation, binary_erosion
from skimage.measure import points_in_poly

from cv2 import fillPoly

import source.Mask as Mask
from source import genutils

import time

class Blob(object):
    """
    Blob data. A blob is a group of pixels.
    It can be tagged with the class and other information.
    It is stored as an outer contour (the border) plus a list of inner contours (holes).
    """

    def __init__(self, region, offset_x, offset_y, id):
        self.version = 0
        self.id = int(id)
        self.id_item = None
        self.instance_name = "noname"
        self.blob_name = "noname"
        self.class_name = "Empty"

        self.genet = None
        # note about the coral, i.e. damage type
        self.note = ""
        self.data = {}

        self.area = 0.0
        self.surface_area = 0.0
        self.perimeter = 0.0
        self.centroid = np.zeros((2))
        self.bbox = np.zeros((4))

        # placeholder; empty contour
        self.contour = np.zeros((2, 2))
        self.inner_contours = []
        self.qpath = None
        self.qpath_gitem = None


        if region:

            # extract properties

            self.centroid = np.array(region.centroid)
            self.centroid[0] += offset_x
            self.centroid[1] += offset_y

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

            # to extract the contour we use the mask cropped according to the bbox
            input_mask = region.image.astype(int)
            self.contour = np.zeros((2, 2))
            self.inner_contours = []
            self.updateUsingMask(self.bbox, input_mask)

            # a string with a progressive number to identify the instance
            self.instance_name = "coral" + str(id)

            # a string with a number to identify the blob plus its centroid
            xc = self.centroid[0]
            yc = self.centroid[1]
            self.blob_name = "c-{:d}-{:.1f}x-{:.1f}y".format(self.id, xc, yc)

       

    def copy(self):
        blob = Blob(None, 0, 0, 0)

        blob.instance_name = blob.instance_name
        blob.blob_name = self.blob_name
        blob.id = self.id
        blob.version = self.version + 1

        blob.genet = self.genet
        blob.class_name = self.class_name

        blob.note = self.note

        blob.area = self.area
        blob.surface_area = self.surface_area
        blob.perimeter = self.perimeter
        blob.centroid = self.centroid
        blob.bbox = self.bbox
        blob.data = self.data.copy()

        blob.contour = self.contour.copy()
        for inner in self.inner_contours:
            blob.inner_contours.append(inner.copy())

        blob.qpath_gitem = None
        blob.qpath = None

        return blob

    def __deepcopy__(self, memo):
        #avoid recursion!
        deepcopy_method = self.__deepcopy__
        self.__deepcopy__ = None
        #save and later restore qobjects
        path = self.qpath
        pathitem = self.qpath_gitem
        #no deep copy for qobjects
        self.qpath = None
        self.qpath_gitem = None

        blob = copy.deepcopy(self)
        blob.contour = self.contour.copy()
        blob.inner_contours.clear()
        for inner in self.inner_contours:
            blob.inner_contours.append(inner.copy())

        blob.qpath = None
        blob.qpath_gitem = None
        self.qpath = path
        self.qpath_gitem = pathitem
        #restore deepcopy (also to the newly created Blob!
        blob.__deepcopy__ = self.__deepcopy__ = deepcopy_method
        return blob

    def setId(self, id):
        # a string with a number to identify the blob plus its centroid
        xc = self.centroid[0]
        yc = self.centroid[1]
        self.id = id
        self.blob_name = "c-{:d}-{:.1f}x-{:.1f}y".format(self.id, xc, yc)

    def getMask(self):
        """
        It creates the mask from the contour and returns it.
        """

        r = self.bbox[3]
        c = self.bbox[2]
        origin = np.array([int(self.bbox[1]), int(self.bbox[0])])

        mask = np.zeros((r, c), np.uint8)
        points = self.contour.round().astype(int)
        fillPoly(mask, pts=[points - origin], color=(1))

        # holes
        for inner_contour in self.inner_contours:
            points = inner_contour.round().astype(int)
            fillPoly(mask, pts=[points - origin], color=(0, 0, 0))

        return mask


    def updateUsingMask(self, bbox, mask):
        self.createContourFromMask(mask, bbox)
        self.calculatePerimeter()
        self.calculateCentroid(mask, bbox)
        self.calculateArea(mask)
        self.bbox = Mask.pointsBox(self.contour,4)

    def createFromClosedCurve(self, lines, erode = True):
        """
        It creates a blob starting from a closed curve. If the curve is not closed False is returned.
        If the curve intersect itself many times the first segmented region is created.
        """
        points = self.lineToPoints(lines)
        box = Mask.pointsBox(points, 4)

        (mask, box) = Mask.jointMask(box, box)
        Mask.paintPoints(mask, box, points, 1)
        before = np.count_nonzero(mask)
        mask = ndi.binary_fill_holes(mask)
        after = np.count_nonzero(mask)

        if before == after:
            return False

        selem = np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]])
        if erode:
            mask = binary_erosion(mask, selem)
        self.updateUsingMask(box, mask)
        return True


    def createContourFromMask(self, mask, bbox):
        """
        It creates the contour (and the corrisponding polygon) from the blob mask.
        """

        # NOTE: The mask is expected to be cropped around its bbox (!!) (see the __init__)

        self.inner_contours.clear()

        # we need to pad the mask to avoid to break the contour that touches the borders
        PADDED_SIZE = 4

        img_padded = np.pad(mask, (PADDED_SIZE, PADDED_SIZE), mode="constant", constant_values=(0, 0))

        contours = measure.find_contours(img_padded, 0.6)
        inner_contours = measure.find_contours(img_padded, 0.4)
        number_of_contours = len(contours)

        threshold = 20 #min number of points in a small hole

        if number_of_contours > 1:

            # search the contour with the largest bounding box (area)
            max_area = 0
            longest = 0
            for i, contour in enumerate(contours):
                cbox = Mask.pointsBox(contour, 0)
                area = cbox[2]*cbox[3]
                if area > max_area:
                    max_area = area
                    longest = i

            max_area = 0
            inner_longest = 0
            for i, contour in enumerate(inner_contours):
                cbox = Mask.pointsBox(contour, 0)
                area = cbox[2]*cbox[3]
                if area > max_area:
                    max_area = area
                    inner_longest = i

            # divide the contours in OUTER contour and INNER contours
            for i, contour in enumerate(contours):
                if i == longest:
                    self.contour = np.array(contour)

            for i, contour in enumerate(inner_contours):
                if i != inner_longest:
                    if contour.shape[0] > threshold:
                        coordinates = np.array(contour)
                        self.inner_contours.append(coordinates)

            # adjust the coordinates of the outer contour
            # (NOTE THAT THE COORDINATES OF THE BBOX ARE IN THE GLOBAL MAP COORDINATES SYSTEM)
            for i in range(self.contour.shape[0]):
                ycoor = self.contour[i, 0]
                xcoor = self.contour[i, 1]
                self.contour[i, 0] = xcoor - PADDED_SIZE + bbox[1]
                self.contour[i, 1] = ycoor - PADDED_SIZE + bbox[0]

            # adjust coordinates of the INNER contours
            for j, contour in enumerate(self.inner_contours):
                for i in range(contour.shape[0]):
                    ycoor = contour[i, 0]
                    xcoor = contour[i, 1]
                    self.inner_contours[j][i, 0] = xcoor - PADDED_SIZE + bbox[1]
                    self.inner_contours[j][i, 1] = ycoor - PADDED_SIZE + bbox[0]
        elif number_of_contours == 1:

            coords = measure.approximate_polygon(contours[0], tolerance=0.2)
            self.contour = np.array(coords)

            # adjust the coordinates of the outer contour
            # (NOTE THAT THE COORDINATES OF THE BBOX ARE IN THE GLOBAL MAP COORDINATES SYSTEM)
            for i in range(self.contour.shape[0]):
                ycoor = self.contour[i, 0]
                xcoor = self.contour[i, 1]
                self.contour[i, 0] = xcoor - PADDED_SIZE + bbox[1]
                self.contour[i, 1] = ycoor - PADDED_SIZE + bbox[0]
        else:
            raise Exception("Empty contour")
        #TODO optimize the bbox
        self.bbox = bbox

    def lineToPoints(self, lines, snap = False):
        points = np.empty(shape=(0, 2), dtype=int)

        for line in lines:
            p = self.drawLine(line)
            if p.shape[0] == 0:
                continue
            if snap:
                p = self.snapToBorder(p)
            if p is None:
                continue
            points = np.append(points, p, axis=0)
        return points

    def dilate(self, size=1):
        """Dilate the blob"""

        mask = self.getMask()
        dilated_mask = binary_dilation(mask, square(size))
        self.updateUsingMask(self.bbox, dilated_mask)

    def erode(self, size=1):
        """Erode the blob"""

        mask = self.getMask()
        eroded_mask = binary_erosion(mask, square(size))
        self.updateUsingMask(self.bbox, eroded_mask)

    def drawLine(self, line):
        (x, y) = genutils.draw_open_polygon(line[:, 1], line[:, 0])
        points = np.asarray([x, y]).astype(int)
        points = points.transpose()
        points[:, [1, 0]] = points[:, [0, 1]]
        return points

    def snapToBorder(self, points):
        return self.snapToContour(points, self.contour)

    def snapToContour(self, points, contour):
        """
        Given a curve specified as a set of points, snap the curve on the blob mask:
          1) the initial segments of the curve are removed until they snap
          2) the end segments of the curve are removed until they snap

        """
        test = points_in_poly(points, contour)
        if test is None or test.shape[0] <= 3:
            return None
        jump = np.gradient(test.astype(int))
        ind = np.nonzero(jump)
        ind = np.asarray(ind)

        snappoints = None
        if ind.shape[1] > 2:
            first_el = ind[0, 0]
            last_el = ind[0, -1]
            snappoints = points[first_el:last_el + 1, :].copy()

        return snappoints

    def snapToInternalBorders(self, points):
        if not self.inner_contours:
            return None
        snappoints = np.zeros(shape=(0, 2))
        for contour in self.inner_contours:
            snappoints = np.append(snappoints, self.snapToContour(points, contour))
        return snappoints



    def setupForDrawing(self):
        """
        Create the QPolygon and the QPainterPath according to the blob's contours.
        """

        # QPolygon to draw the blob
        #working with mask the center of the pixels is in 0, 0
        #if drawing the center of the pixel is 0.5, 0.5
        qpolygon = QPolygonF()
        for i in range(self.contour.shape[0]):
            qpolygon << QPointF(self.contour[i, 0] + 0.5, self.contour[i, 1] + 0.5)

        self.qpath = QPainterPath()
        self.qpath.addPolygon(qpolygon)

        for inner_contour in self.inner_contours:
            qpoly_inner = QPolygonF()
            for i in range(inner_contour.shape[0]):
                qpoly_inner << QPointF(inner_contour[i, 0] + 0.5, inner_contour[i, 1] + 0.5)

            path_inner = QPainterPath()
            path_inner.addPolygon(qpoly_inner)
            self.qpath = self.qpath.subtracted(path_inner)

    #bbox is used to place the mask!
    def calculateCentroid(self, mask, bbox):
        m = measure.moments(mask)
        c = np.array((m[0, 1] / m[0, 0], m[1, 0] / m[0, 0]))

        #centroid is (x, y) while measure returns (y,x and bbox is yx)
        self.centroid  = np.array((c[0] + bbox[1], c[1]+ bbox[0]))
        self.blob_name = "c-{:d}-{:.1f}x-{:.1f}y".format(self.id, self.centroid[0], self.centroid[1])

    def calculateContourPerimeter(self, contour):

        #self.perimeter = measure.perimeter(mask) instead?


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
        #tole = 2
        #simplified = measure.approximate_polygon(self.contour, tolerance=tole)
        self.perimeter = self.calculateContourPerimeter(self.contour)

        for contour in self.inner_contours:
            #simplified = measure.approximate_polygon(contour, tolerance=tole)
            self.perimeter += self.calculateContourPerimeter(contour)

    def calculateArea(self, mask):
        self.area = mask.sum().astype(float)



    def fromDict(self, dict):
        """
        Set the blob information given it represented as a dictionary.
        """

        self.bbox = np.asarray(dict["bbox"])

        self.centroid = np.asarray(dict["centroid"])
        self.area = dict["area"]
        self.perimeter = dict["perimeter"]


        #inner_contours = dict["inner contours"]
        self.contour = self.toContour(dict["contour"])
        inner_contours = dict["inner contours"]
        self.inner_contours = []
        for c in inner_contours:
            #self.inner_contours.append(np.asarray(c))
            self.inner_contours.append(self.toContour(c))


        #for the moment we just update genets on load.
#        if "genet" in dict:
#            self.genet = dict["genet"]
        self.class_name = dict["class name"]
        self.instance_name = dict["instance name"]
        self.blob_name = dict["blob name"]
        self.id = int(dict["id"])
        self.note = dict["note"]
        if 'data' in dict:
            self.data = dict["data"].copy()
        else:
            self.data = {}

    def save(self):
        return self.toDict()

    def toPoints(self, c):

        #return c.tolist()
        d = (c * 10).astype(int)
        d = np.diff(d, axis=0, prepend=[[0, 0]])
        d = np.reshape(d, -1)
        d = np.char.mod('%d', d)
        # combine to a string
        d = " ".join(d)
        return d

    def toContour(self, p):

        if type(p) is str:
            p = map(int, p.split(' '))
            c = np.fromiter(p, dtype=int)
        else:
            c = np.asarray(p)

        if len(c.shape) == 2:
            return c

        c = np.reshape(c, (-1, 2))
        c = np.cumsum(c, axis=0)
        c = c / 10.0
        return c


    def toDict(self):
        """
        Get the blob information as a dictionary.
        """

        dict = {}

        dict["bbox"] = self.bbox.tolist()

        dict["centroid"] = [math.trunc(10 * v) / 10 for v in self.centroid.tolist()]
        dict["area"] = self.area
        dict["perimeter"] = math.trunc(10 *self.perimeter)/10;

        #dict["contour"] = self.contour.tolist()
        dict["contour"] = self.toPoints(self.contour)

        dict["inner contours"] = []
        for c in self.inner_contours:
            #dict["inner contours"].append(c.tolist())
            dict["inner contours"].append(self.toPoints(c))

#        dict["genet"] = self.genet
        dict["class name"] = self.class_name

        dict["instance name"] = self.instance_name
        dict["blob name"] = self.blob_name
        dict["id"] = self.id
        dict["note"] = self.note
        dict["data"] = self.data.copy()

        return dict

