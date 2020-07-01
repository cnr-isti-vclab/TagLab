# TagLab
# A semi-automatic segmentation tool
#
# Copyright(C) 2020
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

from PyQt5.QtGui import QImage
import rasterio as rio
from source import utils
import numpy as np

class Channel(object):
    def __init__(self, filename = None, type = None):

        self.filename = filename      # path relative to the TagLab directory
        self.type = type              # RGB | DEM
        self.qimage = None            # cached QImage (to speed up visualization)
        self.float_map = None         # map of 32-bit floating point (e.g. to store high precision depth values)
        self.nodata = None            # invalid value

    def loadData(self):
        """
        Load the image data. The QImage is cached to speed up visualization.
        """

        if self.type == "RGB":
            self.qimage = QImage(self.filename)

        # typically the depth map is stored in a 32-bit Tiff..
        if self.type == "DEM":
            dem = rio.open(self.filename)
            self.float_map = dem.read(1).astype(np.float32)
            self.nodata = dem.nodata
            self.qimage = utils.floatmapToQImage(self.float_map, self.nodata)

        return self.qimage

    def save(self):
        return { "filename": self.filename, "type": self.type }
