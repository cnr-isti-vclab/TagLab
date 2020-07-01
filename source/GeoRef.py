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

class GeoRef(object):

    def __init__(self, geotiff):

        self.crs = geotiff.crs              # Coordinate Reference System
        self.transform = geotiff.transform  # Affine transform
        self.bounds = geotiff.bounds        # Bounding box

    def load(self):
        pass

    def save(self):
        return { "crs": self.crs, "transform": self.transform, "bound": self.bounds }
