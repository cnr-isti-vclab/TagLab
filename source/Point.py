import math
import copy
import numpy as np
import csv
import sys

from skimage import measure
from scipy import ndimage as ndi
from PyQt5.QtGui import QPainterPath, QPolygonF
from PyQt5.QtCore import QPointF

from skimage.morphology import square, binary_dilation, binary_erosion
from skimage.measure import points_in_poly

from cv2 import fillPoly

import source.Mask as Mask
from source import utils

import time

class Point(object):
    """
    Per point annotation.
    Point annotation can be sampled or can be imported.
    They cannot be edited, individually removed, or manually added.
    The only available actions are selection and class assignment.
    The visualization can change from settings widget.
    """

    def __init__(self, coordx, coordy, classname, id):

        self.version = 0
        self.id = int(id)
        self.id_item = None
        self.class_name = classname
        self.note = ""
        #data are commonly called attributes in TagLab interface
        self.data = {}
        self.coordx= coordx
        self.coordy= coordy

        self.cross1_gitem = None
        self.cross2_gitem = None
        self.ellipse_gitem = None



    def toDict(self):
        """
        Get the point information as a dictionary.
        """
        dict = {}
        dict["Id"] = self.id
        dict["X"] = self.coordx
        dict["Y"] = self.coordy
        dict["Class"] = self.class_name
        dict["Note"] = self.note

        return dict


    def save(self):
        return self.toDict()


