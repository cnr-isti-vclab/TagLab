
import math
import numpy as np
import random
from source.Mask import checkIntersection


class Sampler(object):
    """
    """
    def __init__(self, method, number, offset, width, height):

        # sampling area parameters
        self.method = method
        self.number = number
        self.offset = int(offset)
        self.width = int(width)
        self.height = int(height)
        self.sampling_areas = []
        self.points = []

    def generate(self, top, left):
        """
        Generate samples inside a sampling area.
        """

        w = self.width
        h = self.height
        xstart = left + self.offset
        xend = left + w - self.offset
        ystart = top + self.offset
        yend = top + h - self.offset

        if self.method == 'Grid':

            area_cell = ((w - (2 * self.offset)) * (h-(2 * self.offset))) / self.number
            side_cell = int(math.sqrt(area_cell))

            ncol= round((w - (2 * self.offset))/side_cell)
            nrow = round((h - (2 * self.offset))/side_cell)

            for c in range(0, ncol):
                for r in range(0, nrow):
                    xc = xstart + c * side_cell
                    yc = ystart + r * side_cell
                    point = (xc + (side_cell/2), yc + (side_cell/2))
                    self.points.append(point)

        elif self.method == 'Random':

            counter = 0
            while counter < self.number:
                x = random.randint(xstart, xend)
                y = random.randint(ystart, yend)
                counter += 1
                self.points.append((x, y))

        elif self.method == 'Stratified':

            area_cell = ((w - (2 * self.offset)) * (h-(2 * self.offset))) / self.number
            side_cell = int(math.sqrt(area_cell))

            ncol= round((w - (2 * self.offset))/side_cell)
            nrow = round((h - (2 * self.offset))/side_cell)

            for c in range(0, ncol):
                for r in range(0, nrow):
                    x = random.randint(xstart + c * side_cell, xstart + c * side_cell + side_cell)
                    y = random.randint(ystart + r * side_cell, ystart + r * side_cell + side_cell)
                    self.points.append((x, y))

    def overlap(self, sampling_area):
        """
        Check if the given sampling area overlaps with the existing ones.
        """

        for sa in self.sampling_areas:
            if checkIntersection(sampling_area, sa):
                return True

        return False

    def generateInsideWA(self, working_area, number_of_areas, overlap=False):
        """
        Generate samples inside a working area.
        """

        self.reset()

        w = self.width
        h = self.height

        if overlap:
            for i in range(number_of_areas):
                offx = random.randint(0, working_area[2] - w - 1)
                offy = random.randint(0, working_area[3] - h - 1)
                self.sampling_areas.append([offy, offx, w, h])
        else:
            for i in range(1000):
                offx = random.randint(0, working_area[2] - w - 1)
                offy = random.randint(0, working_area[3] - h - 1)
                sampling_area = [offy, offx, w, h]
                if not self.overlap(sampling_area):
                    self.sampling_areas.append(sampling_area)

                if len(self.sampling_areas) >= number_of_areas:
                    break

        # generate samples
        for sampling_area in self.sampling_areas:
            top = sampling_area[0] + working_area[0]
            left = sampling_area[1] + working_area[1]
            self.generate(top, left)

    def generateAlongTransect(self, transect, number_of_areas, equi_spaced=True, overlap=False):
        """
        Generate samples along a transect (the sampling areas are equally spaced or in a randomly positioned
        along the transect according to the regular flag).
        The transect is specified in the following format: [x1, y1, x2, y2]
        """

        self.reset()

        x1 = transect[0]
        y1 = transect[1]
        x2 = transect[2]
        y2 = transect[3]

        dx = x2-x1
        dy = y2-y1

        if equi_spaced:
            step = 1.0 / (number_of_areas-1)
            for i in range(number_of_areas):
                pos = step * i
                posx = x1 + dx * pos - self.width/2
                posy = y1 + dy * pos - self.height/2
                sampling_area = [posy, posx, self.width, self.height]
                self.sampling_areas.append(sampling_area)
                self.generate(posy, posx)
        else:
            # generate sampling areas
            for i in range(1000):
                alpha = random.random()
                posx = x1 + dx * alpha - self.width/2
                posy = y1 + dy * alpha - self.height/2
                sampling_area = [posy, posx, self.width, self.height]
                if not self.overlap(sampling_area):
                    self.sampling_areas.append(sampling_area)

                if len(self.sampling_areas) >= number_of_areas:
                    break

            # generate samples
            for sampling_area in self.sampling_areas:
                self.generate(sampling_area[0], sampling_area[1])

    def reset(self):
        """
        Reset the samples generator.
        """
        self.sampling_areas = []
        self.points = []

