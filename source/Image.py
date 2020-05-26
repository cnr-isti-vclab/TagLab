import numpy as np
from source.Channel import Channel
from source.Blob import Blob
from source.Annotation import Annotation

class Image(object):
    def __init__(self, rect = [0.0, 0.0, 0.0, 0.0],
        map_px_to_mm_factor = 1.0, width = None, height = None, channels = [], id = None, name = None,
        workspace = [], metadata = {}, annotations = {}):

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

        self.id = id                           #internal id used in correspondences it will never changes
        self.name = name                         #a label for an annotated image
        self.workspace = workspace        #a polygon in spatial reference system
        #self.map_acquisition_date = None        #this should be suggested in project creation in image_metadata_template
        self.metadata = metadata                            #this follows image_metadata_template, do we want to allow freedom to add custome values?

    def save(self):
        data = self.__dict__
        return data
