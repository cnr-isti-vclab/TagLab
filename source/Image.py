import numpy as np
from source.Undo import Undo

class Image(object):
    def __init__(self):
        #we have to select a standanrd enforced!
        #in image standard (x, y, width height)
        #in numpy standard (y, x, height, width) #no the mixed format we use now I REFUSE to use it.
        #in range np format: (top, left, bottom, right)
        #in GIS standard (bottom, left, top, right)
        self.rect = np.array([0.0, 0.0, 0.0, 0.0])        #coordinates of the image. (in the spatial reference system)
        self.map_px_to_mm_factor = 1.0           #if we have a references system we should be able to recover this numner
                                                # otherwise we need to specify it.
        self.width = None
        self.height = None                        #in pixels!

        self.channels  = []                      # list of rgb, dem images, we assume same width heigth and rect. Transform if not when loaded.

        self.id = None                           #internal id used in correspondences it will never changes
        self.name = None                         #a label for an annotated image
        self.workspace = np.array((0, 2))        #a polygon in spatial reference system
        #self.map_acquisition_date = None        #this should be suggested in project creation in image_metadata_template
        self.metadata                            #this follows image_metadata_template, do we want to allow freedom to add custome values?
