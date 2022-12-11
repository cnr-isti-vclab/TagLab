
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
from source import utils

import time
from source.Point import Point

class Sampler(object):
    """
    """
    def __init__(self, image, area, method, number):

        self.image = image
        self.area = area
        self.method = method
        self.number = number

    def generate(self):

        top = self.area[0]
        left = self.area[1]
        w = self.area[2]
        h = self.area[3]


        if self.method =='Grid Sampling':

            # this area must be squared?

            k = np.sqrt(self.number)
            x = np.linspace(0, w, k)
            y = np.linspace(0, h, k)
            x_1, y_1 = np.meshgrid(x, y)


        elif self.method =='Uniform Sampling':
            pass


        else:
            pass

        return x_1,y_1

    def sampleSubAreaWImportanceSampling(self, area, current_samples):
        """
        Sample the given area using the Poisson Disk sampling according to the given radius map.
        The area is stored as (top, left, width, height).
        """

        top = area[0]
        left = area[1]
        w = area[2]
        h = area[3]

        for i in range(30):
            px = rnd.randint(left, left + w - 1)
            py = rnd.randint(top, top + h - 1)

            r1 = self.radius_map[py, px]

            flag = True
            for sample in current_samples:
                r2 = self.radius_map[sample[1], sample[0]]
                d = math.sqrt((sample[0] - px) * (sample[0] - px) + (sample[1] - py) * (sample[1] - py))
                if d < (r1 + r2) / 2.0:
                    flag = False
                    break

            if flag is True:
                current_samples.append((px, py))

        return current_samples