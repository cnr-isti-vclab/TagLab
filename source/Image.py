import math

from source.Channel import Channel
from source.Blob import Blob
from source.Point import Point
from source.Shape import Layer, Shape
from source.Annotation import Annotation
from source.Grid import Grid
from skimage.transform import warp, AffineTransform
import rasterio as rio
import pandas as pd
import numpy as np
import os
import cv2


class Image(object):
    def __init__(self, rect=[0.0, 0.0, 0.0, 0.0],
                 map_px_to_mm_factor=1.0, width=None, height=None, channels=[], id=None, name=None,
                 acquisition_date="",
                 georef_filename="", workspace=[], metadata={}, annotations={}, layers=[],
                 grid={}, export_dataset_area=[]):

        # we have to select a standanrd enforced!
        # in image standard (x, y, width height)
        # in numpy standard (y, x, height, width) #no the mixed format we use now I REFUSE to use it.
        # in range np format: (top, left, bottom, right)
        # in GIS standard (bottom, left, top, right)

        self.rect = rect  # coordinates of the image. (in the spatial reference system)
        self.map_px_to_mm_factor = map_px_to_mm_factor  # if we have a references system we should be able to recover this numner
        # otherwise we need to specify it.
        self.width = width
        self.height = height  # in pixels!

        self.annotations = Annotation()

        if annotations is not None:

            if type(annotations) == list:
                for data in annotations:
                    blob = Blob(None, 0, 0, 0)
                    blob.fromDict(data)
                    self.annotations.addBlob(blob)
            else:
                regions = annotations.get("regions")
                if regions is not None:
                    for data in regions:
                        blob = Blob(None, 0, 0, 0)
                        blob.fromDict(data)
                        self.annotations.addBlob(blob)

                points = annotations.get("points")
                if points is not None:
                    for data in points:
                        point = Point(0, 0, "Empty", 0)
                        point.fromDict(data)
                        self.annotations.addPoint(point)



        self.layers = []
        for layer_data in layers:
            layer = Layer(layer_data["type"])
            layer.name = layer_data["name"]
            for data in layer_data["shapes"]:
                shape = Shape(None, None)
                shape.fromDict(data)
                layer.shapes.append(shape)
            self.layers.append(layer)

        self.channels = list(map(lambda c: Channel(**c), channels))

        self.id = id  # internal id used in correspondences it will never changes
        self.name = name  # a label for an annotated image
        self.workspace = workspace  # a polygon in spatial reference system (reserved for future uses)
        self.export_dataset_area = export_dataset_area  # this is the region exported for training
        self.acquisition_date = acquisition_date  # acquisition date is mandatory (format YYYY-MM-DD)
        self.georef_filename = georef_filename  # image file (GeoTiff) contained the georeferencing information
        self.metadata = metadata  # this follows image_metadata_template, do we want to allow freedom to add custome values?

        if grid:
            self.grid = Grid()
            self.grid.fromDict(grid)
        else:
            self.grid = None

        self.cache_data_table = None
        self.cache_labels_table = None

    def deleteLayer(self, layer):
        self.layers.remove(layer)

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

        # check image size consistency (all the channels must have the same size)
        if self.width is not None and self.height is not None:
            if self.width != img.width or self.height != img.height:
                raise Exception("Size of the images is not consistent! It is " + str(img.width) + "x" +
                                str(img.height) + ", should have been: " + str(self.width) + "x" + str(self.height))
                return

        # check image size limits
        if img.width > 32767 or img.height > 32767:
            raise Exception(
                "This map exceeds the image dimension handled by TagLab (the maximum size is 32767 x 32767).")
            return

        if img.crs is not None:
            # this image contains georeference information
            self.georef_filename = filename

        self.width = img.width
        self.height = img.height

        self.channels.append(Channel(filename, type))

    def create_labels_table(self, labels):
        '''
        Creates a data table for the label panel
        '''

        if self.annotations.table_needs_update is False:
            return self.cache_labels_table
        else:
            dict = {
                'Visibility': np.zeros(len(labels), dtype=int),
                'Color': [],
                'Class': [],
                '#R': np.zeros(len(labels), dtype=int),
                '#P': np.zeros(len(labels), dtype=int),
                'Coverage': np.zeros(len(labels),dtype=np.float)
            }

            for i, label in enumerate(labels):
                dict['Visibility'][i] = int(label.visible)
                dict['Color'].append(str(label.fill))
                dict['Class'].append(label.name)
                count, new_area = self.annotations.calculate_perclass_blobs_value(label, self.map_px_to_mm_factor)
                countP = self.annotations.countPoints(label)
                dict['#R'][i] = count
                dict['#P'][i] = countP
                dict['Coverage'][i] = new_area


            # create dataframe
            df = pd.DataFrame(dict, columns=['Visibility', 'Color', 'Class', '#R', '#P','Coverage'])
            self.cache_labels_table = df
            self.annotations.table_needs_update = False
            return df

    def create_data_table(self):
        '''
        This create a data table only for the data panel view
        '''

        if self.annotations.table_needs_update is False:
            return self.cache_data_table
        else:
            scale_factor = self.pixelSize()

            # create a list of instances
            name_list = []
            visible_blobs = []
            # select ONLY visible blobs
            for blob in self.annotations.seg_blobs:
                if blob.qpath_gitem is not None:
                    if blob.qpath_gitem.isVisible():
                        index = blob.blob_name
                        name_list.append(index)
                        visible_blobs.append(blob)

            number_of_seg = len(visible_blobs)

            annpoint_list = []
            visible_annpoints = []
            for annpoint in self.annotations.annpoints:
                if annpoint.cross1_gitem is not None:
                    if annpoint.cross1_gitem.isVisible():
                        index = annpoint.id
                        annpoint_list.append(index)
                        visible_annpoints.append(annpoint)

            number_of_points = len(visible_annpoints)

            dict = {
                'Id': np.zeros(number_of_seg + number_of_points, dtype=int),
                'Type': [],
                'Class': [],
                'Area': np.zeros(number_of_seg + number_of_points),
                #'Surf. area': np.zeros(number_of_seg)
            }

            for i, blob in enumerate(visible_blobs):
                dict['Id'][i] = blob.id
                dict['Type'].append('R')
                dict['Class'].append(blob.class_name)
                dict['Area'][i] = round(blob.area * (scale_factor) * (scale_factor) / 100, 2)
            #            if blob.surface_area > 0.0:
            #                dict['Surf. area'][i] = round(blob.surface_area * (scale_factor) * (scale_factor) / 100, 2)

            for i, annpoint in enumerate(visible_annpoints):
                dict['Id'][i + number_of_seg] = annpoint.id
                dict['Type'].append('P')
                dict['Class'].append(annpoint.class_name)
                dict['Area'][i + number_of_seg] = 0.0


            df = pd.DataFrame(dict, columns=['Id','Type', 'Class', 'Area'])
            self.cache_data_table = df
            self.annotations.table_needs_update = False

            return df

    def updateChannel(self, filename, type):
        img = rio.open(filename)

        # check image size consistency (all the channels must have the same size)
        if self.width is not None and self.height is not None:
            if self.width != img.width or self.height != img.height:
                raise Exception("Size of the images is not consistent! It is " + str(img.width) + "x" +
                                str(img.height) + ", should have been: " + str(self.width) + "x" + str(self.height))
                return

        if img.crs is not None:
            # this image contains georeference information
            self.georef_filename = filename

        for index, channel in enumerate(self.channels):
            if channel.type == type:
                self.channels[index] = Channel(filename, type)

    def hasDEM(self):
        """
        It returns True if the image has a DEM channel, False otherwise.
        """
        for channel in self.channels:
            if channel.type == "DEM":
                return True

        return False

    def getChannel(self, type):
        for channel in self.channels:
            if channel.type == type:
                return channel
        return None

    def getChannelIndex(self, channel):
        try:
            index = self.channels.index(channel)
            return index
        except:
            return -1

    def getRGBChannel(self):
        """
        It returns the RGB channel (if exists).
        """
        return self.getChannel("RGB")

    def getDEMChannel(self):
        """
        It returns the DEM channel (if exists).
        """
        return self.getChannel("DEM")

    def save(self):
        data = self.__dict__.copy()

        # cached tables MUST NOT be saved
        del data["cache_data_table"]
        del data["cache_labels_table"]

        return data

    def copyTransform(self, tag, rot, tra, borders, geoTransform=None, geoRef=None):
        """
        Create a new Image applying an affine transformation and adding borders
        :param: name the new name for the image (functioning also as id)
        :param: rot the rotation component in degrees
        :param: tra the translation component
        :param: borders of the new image (positive offset) [left, right, top, bottom]
        :param: geoTransform the transformation of the geo-reference
        :param: geoRef the geo-reference of the new image
        :returns: the newly created image
        """
        [leftB, rightB, topB, bottomB] = borders
        # Create a copy
        cpy = Image(
            rect=self.rect,
            map_px_to_mm_factor=self.map_px_to_mm_factor,
            width=0,
            height=0,
            # channels=self.channels,
            id=self.id + tag,
            name=self.id + tag,
            acquisition_date=self.acquisition_date,
            georef_filename=self.georef_filename,
            workspace=self.workspace,
            metadata=self.metadata,
            # annotations=self.annotations,
            layers=self.layers,
            grid=self.grid,
            export_dataset_area=self.export_dataset_area
        )
        # TODO: Remove
        R = cv2.getRotationMatrix2D((0, 0), -rot, 1.0)[::, :2]
        T = np.array([tra[0] + leftB, tra[1] + topB])
        # Add blobs
        new_blobs = self.annotations.computeBlobsAffineTransform(R, T)
        for blob in new_blobs:
            cpy.annotations.addBlob(blob, notify=False)
        # Add channels
        for ch in self.channels:
            newFilename, w, h = self.__updateChannel(ch, tag, -rot, tra, borders, geoTransform, geoRef)
            # Update dimensions
            cpy.width = w
            cpy.height = h
            # Add transformed channel
            cpy.addChannel(newFilename, ch.type)
        # Result
        return cpy

    def __updateChannel(self, channel, tag, rot, tra, borders, geoTransform=None, geoRef=None):
        """
        Create a new image applying a transformation to a channel
        :param: channel the channel to transform
        :param: tag the string to add to filename when creating the new one
        :param: rot the rotation degrees
        :param: tra the translation vector
        :param: borders the borders in order [left, right, top, bottom]
        :param: geoTransform the transformation of the geo-reference
        :param: geoRef the geo-reference of the new image
        :returns: newFilename, width, height of the new image
        """
        # Retrieve borders
        leftB, rightB, topB, bottomB = borders
        # Create new filename
        filename, _ = os.path.splitext(channel.filename)
        ext = ".png" if channel.type == "RGB" and geoRef is None else ".tiff"
        # [CV2] newFilename = filename + tag + ext
        newFilename = filename + tag + ext  # TODO: always '.tiff' / '.png' (for color channel with no geo-ref)
        # Read "reference" image
        # [CV2] img = cv2.imread(channel.filename, cv2.IMREAD_COLOR)
        imgData = rio.open(channel.filename).read()
        img = np.moveaxis(imgData, 0, -1)  # Since rasterio is channel-first
        # Add border
        # [CV2] img = cv2.copyMakeBorder(img, topB, bottomB, leftB, rightB, cv2.BORDER_CONSTANT, None, [0, 0, 0])
        padding = channel.nodata if channel.nodata is not None else 0
        img = np.pad(img, ((topB, bottomB), (leftB, rightB), (0, 0)), constant_values=[padding])
        # [CV2] # Transform: Borders
        # [CV2] RTMat = cv2.getRotationMatrix2D((leftB, topB), rot, 1.0)
        # [CV2] RTMat[0, 2] += tra[0]
        # [CV2] RTMat[1, 2] += tra[1]
        # Transform: Rot + Tra
        # [CV2] img = cv2.warpAffine(img, RTMat, (w, h))
        transformation = AffineTransform(scale=1.0, rotation=0, translation=(-leftB, -topB))
        img = warp(img, transformation.inverse, preserve_range=True)
        transformation = AffineTransform(scale=1.0, rotation=math.radians(-rot), translation=(tra[0] + leftB, tra[1] + topB))
        img = warp(img, transformation.inverse, preserve_range=True)
        # Save with newly created filename
        # [CV2] cv2.imwrite(newFilename, img)
        img = np.moveaxis(img, -1, 0)  # Since rasterio is channel-first
        # Update sizes
        (c, h, w) = img.shape
        # For geo-references
        # mat1 = rio.transform.Affine.rotation(rot)
        # mat2 = rio.transform.Affine.translation(tra[0], tra[1])
        # geoMat = mat2 * mat1
        geoMat = rio.transform.Affine.translation(-leftB + rightB, -topB + bottomB)
        img = img.astype(imgData.dtype)
        if ext == ".png":
            with rio.open(newFilename, "w", driver='PNG', width=w, height=h, dtype=img.dtype, count=c) as dest:
                dest.write(img)
        else:
            with rio.open(newFilename, "w", driver='GTiff', width=w, height=h, dtype=img.dtype, count=c) as dest:
                dest.write(img)
                if geoRef is not None:
                    dest.nodata = channel.nodata
                    dest.crs = geoRef
                    dest.transform = geoTransform * geoMat
        # Return (resource path, width, height)
        return newFilename, w, h
