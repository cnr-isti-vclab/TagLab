import numpy as np
from source.Channel import Channel
from source.Blob import Blob
from source.Annotation import Annotation
from source.GeoRef import GeoRef
import rasterio as rio

class Image(object):
    def __init__(self, rect = [0.0, 0.0, 0.0, 0.0],
        map_px_to_mm_factor = 1.0, width = None, height = None, channels = [], id = None, name = None,
        georef = None, workspace = [], metadata = {}, annotations = {}):

        #we have to select a standanrd enforced!
        #in image standard (x, y, width height)
        #in numpy standard (y, x, height, width) #no the mixed format we use now I REFUSE to use it.
        #in range np format: (top, left, bottom, right)
        #in GIS standard (bottom, left, top, right)
        self.rect = rect       #coordinates of the image. (in the spatial reference system)
        self.map_px_to_mm_factor = map_px_to_mm_factor           #if we have a references system we should be able to recover this numner
                                                # otherwise we need to specify it.
        self.width = width
        self.height = height                        #in pixels!

        self.annotations = Annotation()
        for data in annotations:
            blob = Blob(None, 0, 0, 0)
            blob.fromDict(data)
            self.annotations.addBlob(blob)

        self.channels = list(map(lambda c: Channel(**c), channels))

        self.id = id                        # internal id used in correspondences it will never changes
        self.name = name                    # a label for an annotated image
        self.workspace = workspace          # a polygon in spatial reference system
        #self.map_acquisition_date = None   # this should be suggested in project creation in image_metadata_template
        self.georef = georef
        self.metadata = metadata            # this follows image_metadata_template, do we want to allow freedom to add custome values?



    def addChannel(self, filename, type):
        """
        This image add a channel to this image. The functions update the size (in pixels) and
        the Coordinate Reference System (if the image if georeferenced).
        The image data is loaded when the image channel is used for the first time.
        """

        img = rio.open(filename)
        if img.crs is not None:
            # this image georeferenced
            geoinfo = GeoRef(img)
            self.georef = geoinfo

        # check image size consistency (all the channels muist have the same size)
        if self.width is not None and self.height is not None:
            if self.width != img.width or self.height != img.height:
                raise Exception(
                    "Size of the image changed! Should have been: " + str(self.image.width) + "x" + str(self.image.height))

        # check image size limits
        if img.width > 32767 or img.height > 32767:
            raise Exception(
                "This map exceeds the image dimension handled by TagLab (the maximum size is 32767 x 32767).")

        self.width = img.width
        self.height = img.height

        self.channels.append(Channel(filename, type))


    def save(self):
        data = self.__dict__
        return data
