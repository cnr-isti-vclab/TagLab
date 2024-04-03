
import math
import numpy as np, random


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

        if self.method == 'Grid Sampling':

            area_cell = ((w - (2 * self.offset)) * (h-(2 * self.offset))) / self.number
            side_cell = int(math.sqrt(area_cell))

            ncol= round((w - (2 * self.offset))/side_cell)
            nrow = round((h - (2 * self.offset))/side_cell)

            for c in range(0, ncol):
                for r in range(0, nrow):
                    xc = xstart + c * side_cell
                    yc = ystart + r * side_cell
                    point = (xc + (side_cell/2), yc + (side_cell/2))
                    points.append(point)

        elif self.method == 'Random Sampling':

            counter = 0
            while counter < self.number:
                x = random.randint(xstart, xend)
                y = random.randint(ystart, yend)
                counter += 1
                points.append((x, y))

        elif self.method == 'Stratified Sampling':

            area_cell = ((w - (2 * self.offset)) * (h-(2 * self.offset))) / self.number
            side_cell = int(math.sqrt(area_cell))

            ncol= round((w - (2 * self.offset))/side_cell)
            nrow = round((h - (2 * self.offset))/side_cell)

            for c in range(0, ncol):
                for r in range(0, nrow):
                    x = random.randint(xstart + c * side_cell, xstart + c * side_cell + side_cell)
                    y = random.randint(ystart + r * side_cell, ystart + r * side_cell + side_cell)
                    points.append((x, y))

        return points

