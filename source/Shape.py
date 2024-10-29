# TagLab
# A semi-automatic segmentation tool
#
# Copyright(C) 2021
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

import copy
import numpy as np
from PyQt5.QtGui import QPainterPath, QPolygonF
from PyQt5.QtCore import QPointF

class Layer(object):
    """
    Each shapefile is put inside a different layer. In this way the information coming from different
    imports can be enabled or disabled. Such information CANNOT be edited.
    """

    def __init__(self, type):

        self.shapes = []
        self.enabled = True
        self.type = type
        self.name = ""

    def add(self, shape):
        """
        Add a shape.
        """

        self.shapes.append(shape)

    def enable(self):
        """
        A layer enabled show all its shape.
        """

        self.enabled = True

    def disable(self):
        """
        A layer disable hides all its shapes.
        """

        self.enabled = False

    def isEnabled(self):

        return self.enabled

    def save(self):
        dict = {}
        dict["name"] = self.name
        dict["type"] = self.type
        dict["shapes"] = self.shapes
        return dict


class Shape(object):
    """
    A shape is imported from a shapefile. It may be a polygon or a point.
    It cannot be edited by the user.
    """

    def __init__(self, outer_contour, inner_contours):

        self.type = "invalid"

        if outer_contour is not None:
            n = len(outer_contour)
            if n == 0:
                self.type = "empty"
            elif n == 1:
                self.type = "point"
            elif n > 1:
                self.type = "polygon"
            else:
                pass
        else:
            self.type = "empty"

        # geometry
        self.outer_contour = outer_contour
        self.inner_contours = inner_contours

         # data attributes
        self.data = {}

        # visualization stuffs
        self.point_gitem = None
        self.qpath = None
        self.qpath_gitem = None

    def copy(self):

        shape = Shape(None, None)

        shape.type = self.type
        shape.data = self.data.copy()

        shape.outer_contour = self.outer_contour.copy()
        shape.inner_contours = []
        for inner in self.inner_contours:
            shape.inner_contours.append(inner.copy())

        shape.point_gitem = None
        shape.qpath = None
        shape.qpath_gitem = None

        return shape

    def __deepcopy__(self, memo):

        # avoid recursion!
        deepcopy_method = self.__deepcopy__
        self.__deepcopy__ = None

        #save and later restore qobjects
        pointitem = self.point_gitem
        path = self.qpath
        pathitem = self.qpath_gitem

        # no deep copy for qobjects
        self.point_gitem = None
        self.qpath = None
        self.qpath_gitem = None

        shape = copy.deepcopy(self)
        shape.outer_contour = self.outer_contour.copy()
        shape.inner_contours.clear()
        shape.inner_contours = []
        for inner in self.inner_contours:
            shape.inner_contours.append(inner.copy())

        shape.point_gitem = None
        shape.qpath = None
        shape.qpath_gitem = None

        self.point_gitem = pointitem
        self.qpath = path
        self.qpath_gitem = pathitem

        # restore deepcopy (also to the newly created Blob!
        shape.__deepcopy__ = self.__deepcopy__ = deepcopy_method

        return shape

    def setupForDrawing(self):
        """
        Create the QPolygon and the QPainterPath according to the blob's contours.
        """

        if self.type == "point":
            pass

        elif self.type == "polygon":

            # QPolygon to draw the blob
            # the center of the pixel is 0.5, 0.5

            qpolygon = QPolygonF()
            for i in range(self.outer_contour.shape[0]):
                qpolygon << QPointF(self.outer_contour[i, 0] + 0.5, self.outer_contour[i, 1] + 0.5)

            self.qpath = QPainterPath()
            self.qpath.addPolygon(qpolygon)

            for inner_contour in self.inner_contours:
                qpoly_inner = QPolygonF()
                for i in range(inner_contour.shape[0]):
                    qpoly_inner << QPointF(inner_contour[i, 0] + 0.5, inner_contour[i, 1] + 0.5)

                path_inner = QPainterPath()
                path_inner.addPolygon(qpoly_inner)
                self.qpath = self.qpath.subtracted(path_inner)

    def save(self):
        return self.toDict()

    def toPoints(self, c):

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
        Get the shape information as a dictionary.
        """

        dict = {}

        dict["type"] = self.type

        dict["contour"] = self.toPoints(self.outer_contour)

        dict["inner contours"] = []
        if self.inner_contours is not None:
            for c in self.inner_contours:
                dict["inner contours"].append(self.toPoints(c))

        dict["data"] = self.data.copy()

        return dict

    def fromDict(self, dict):
        """
        Set the shape information given it as a dictionary.
        """

        self.type = dict["type"]

        self.outer_contour = self.toContour(dict["contour"])

        inner_contours = dict["inner contours"]
        self.inner_contours = []
        for c in inner_contours:
            self.inner_contours.append(self.toContour(c))

        if 'data' in dict:
            self.data = dict["data"].copy()
        else:
            self.data = {}
