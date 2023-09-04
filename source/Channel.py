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
from PyQt5.QtGui import QImageReader
import rasterio as rio
from source import genutils
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
            # reader = QImageReader(self.filename)
            # self.qimage = reader.read()
            # if self.qimage.isNull():
            #     print(reader.errorString())
            # self.qimage = self.qimage.convertToFormat(QImage.Format_RGB32)
            img = rio.open(self.filename).read()
            img = np.moveaxis(img, 0, -1)  # Since Rasterio is channel first shape=(c, h, w)
            self.qimage = genutils.rgbToQImage(img)

        # typically the depth map is stored in a 32-bit Tiff
        if self.type == "DEM":
            dem = rio.open(self.filename)
            self.float_map = dem.read(1).astype(np.float32)
            self.nodata = dem.nodata
            self.qimage = genutils.floatmapToQImage(self.float_map, self.nodata)

        return self.qimage

    def save(self):
        return { "filename": self.filename, "type": self.type }
