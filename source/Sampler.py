
import math
import copy
import numpy as np, random

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
    def __init__(self, image, area, method, number, offset):

        self.image = image
        self.area = area
        self.method = method
        self.number = number
        self.offset = int(offset)

    def generate(self):

        top = self.area[0]
        left = self.area[1]
        w = self.area[2]
        h = self.area[3]
        xstart = left + self.offset
        xend = left + w - self.offset
        ystart = top + self.offset
        yend = top + h - self.offset

        points = []

        if self.method =='Grid Sampling':

            k = np.sqrt(self.number)
            x = np.linspace(xstart, xend, int(k))
            y = np.linspace(ystart, yend, int(k))

            for x1 in x:
                for y1 in y:
                    point = (x1,y1)
                    points.append(point)

        elif self.method =='Uniform Sampling':

            radius = 1
            rangeX = (xstart, xend)
            rangeY = (ystart, yend)
            qty = self.number

            deltas = set()
            for x in range(-radius, radius + 1):
                for y in range(-radius, radius + 1):
                    if x * x + y * y <= radius * radius:
                        deltas.add((x, y))
            points = []
            excluded = set()
            i = 0
            while i < qty:
                x = random.randrange(*rangeX)
                y = random.randrange(*rangeY)
                if (x, y) in excluded: continue
                points.append((x, y))
                i += 1
                excluded.update((x + dx, y + dy) for (dx, dy) in deltas)

        return points

    # def sampleSubAreaWImportanceSampling(self, area, current_samples):
    #     """
    #     Sample the given area using the Poisson Disk sampling according to the given radius map.
    #     The area is stored as (top, left, width, height).
    #     """
    #     offset = 200
    #
    #     top = area[0]
    #     left = area[1]
    #     w = area[2]
    #     h = area[3]
    #
    #     for i in range(30):
    #         px = rnd.randint(left, left + w - 1)
    #         py = rnd.randint(top, top + h - 1)
    #
    #         r1 = self.radius_map[py, px]
    #
    #         flag = True
    #         for sample in current_samples:
    #             r2 = self.radius_map[sample[1], sample[0]]
    #             d = math.sqrt((sample[0] - px) * (sample[0] - px) + (sample[1] - py) * (sample[1] - py))
    #             if d < (r1 + r2) / 2.0:
    #                 flag = False
    #                 break
    #
    #         if flag is True:
    #             current_samples.append((px, py))
    #
    #     return current_samples