from source.Channel import Channel
from source.Blob import Blob
from source.Annotation import Annotation
import rasterio as rio

class Image(object):
    def __init__(self, rect = [0.0, 0.0, 0.0, 0.0],
        map_px_to_mm_factor = 1.0, width = None, height = None, channels = [], id = None, name = None,
        acquisition_date = "",
        georef_filename = "", workspace = [], metadata = {}, annotations = {}, working_area = []):

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

        self.id = id                              # internal id used in correspondences it will never changes
        self.name = name                          # a label for an annotated image
        self.workspace = workspace                # a polygon in spatial reference system
        self.working_area = working_area          # this is the working area of data exports for training
        self.acquisition_date = acquisition_date  # acquisition date is mandatory (format YYYY-MM-DD)
        self.georef_filename = georef_filename    # image file (GeoTiff) contained the georeferencing information
        self.metadata = metadata                  # this follows image_metadata_template, do we want to allow freedom to add custome values?


    def pixelSize(self):

        if self.map_px_to_mm_factor == "":
            return 1.0
        else:
            return float(self.map_px_to_mm_factor)

    def loadGeoInfo(self, filename):
        """
        Update the georeferencing information.
        """
        img = rio.open(filename)
        if img.crs is not None:
            # this image contains georeference information
            self.georef_filename = filename


    def addChannel(self, filename, type):
        """
        This image add a channel to this image. The functions update the size (in pixels) and
        the georeferencing information (if the image if georeferenced).
        The image data is loaded when the image channel is used for the first time.
        """

        img = rio.open(filename)
        if img.crs is not None:
            # this image contains georeference information
            self.georef_filename = filename

        # check image size consistency (all the channels muist have the same size)
        if self.width is not None and self.height is not None:
            if self.width != img.width or self.height != img.height:
                raise Exception(
                    "Size of the images is not consistent! It is " + str(img.width) + "x" + str(img.height) + ", should have been: " + str(self.width) + "x" + str(self.height))

        # check image size limits
        if img.width > 32767 or img.height > 32767:
            raise Exception(
                "This map exceeds the image dimension handled by TagLab (the maximum size is 32767 x 32767).")

        self.width = img.width
        self.height = img.height

        self.channels.append(Channel(filename, type))

    def getRGBChannel(self):

        for channel in self.channels:
            if channel.type == "RGB":
                return channel

        return None

    def getDEMChannel(self):

        for channel in self.channels:
            if channel.type == "DEM":
                return channel

        return None

    def save(self):
        data = self.__dict__.copy()
        return data
