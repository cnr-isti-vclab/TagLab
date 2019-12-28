# TagLab                                               
# A semi-automatic segmentation tool                                    
#
# Copyright(C) 2019                                         
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

import numpy as np

from skimage import measure
from scipy import ndimage as ndi
from PyQt5.QtGui import QImage, qRgb
from PyQt5.QtCore import Qt

from skimage.draw import polygon_perimeter

from source import utils
from source.Labels import Labels

import pandas as pd
from scipy import ndimage as ndi
from skimage.morphology import watershed
from source.Blob import Blob
import source.Mask as Mask

import time


class Group(object):

    def __init__(self, blobs, id):

        # list of the blobs that form this group
        self.blobs = []
        for blob in blobs:
            self.blobs.append(blob)

        for blob in blobs:

            blob.group = self

        # centroid of the group
        sumx = 0.0
        sumy = 0.0
        n = 0
        for blob in self.blobs:
            blob_mask = blob.getMask()
            for y in range(blob_mask.shape[0]):
                for x in range(blob_mask.shape[1]):
                    if blob_mask[y, x] == 1:
                        sumx += float(x + blob.bbox[1])
                        sumy += float(y + blob.bbox[0])
                        n += 1

        cx = sumx / n
        cy = sumy / n

        self.centroid = np.zeros((2))
        self.centroid[0] = cx
        self.centroid[1] = cy

        # update instance name for each blob
        for blob in self.blobs:
            blob.instace_name = "coral-group-" + str(id)


class Annotation(object):
    """
        Annotation object contains all the annotations as a list of blobs.
    """

    def __init__(self):

        # list of all blobs
        self.seg_blobs = []

        # annotations coming from previous years (for comparison, no editing is possible)
        self.prev_blobs = []

        # list of all groups
        self.groups = []

    def addGroup(self, blobs):

        id = len(self.groups)
        group = Group(blobs, id+1)
        self.groups.append(group)
        return group

    def addBlob(self, blob):
        self.seg_blobs.append(blob)

    def removeBlob(self, blob):
        index = self.seg_blobs.index(blob)
        del self.seg_blobs[index]


    def blobsFromMask(self, seg_mask, map_pos_x, map_pos_y, area_mask):
        # create the blobs from the segmentation mask

        last_blobs_added = []

        seg_mask = ndi.binary_fill_holes(seg_mask).astype(int)
        label_image = measure.label(seg_mask)

        area_th = area_mask * 0.2

        for region in measure.regionprops(label_image):

            if region.area > area_th:

                id = len(self.seg_blobs)
                blob = Blob(region, map_pos_x, map_pos_y, id+1)
                #self.seg_blobs.append(blob)

                last_blobs_added.append(blob)

        return last_blobs_added

    def removeGroup(self, group):

        # the blobs no more belong to this group
        for blob in group.blobs:
            blob.group = None
            blob.instace_name = "coral" + str(blob.id)

        # remove from the list of the groups
        index = self.groups.index(group)
        del self.groups[index]




    def as_dict(self, i):

        blob = self.seg_blobs[i]
        return {'coral name': blob.blob_name, 'group name': blob.group, 'class name': blob.class_name, ' centroid ': blob.centroid, 'coral area': blob.area, 'coral perimeter': blob.perimeter}

    def union(self, blobs):
        """
        Create a new blob that is the union of the (two) blobs given
        """
        #boxs are in image space, masks invert x and y.
        boxes = []
        for blob in blobs:
            boxes.append(blob.bbox)
        box = Mask.jointBox(boxes)
        (mask, box) = Mask.jointMask(box, box)

        for blob in blobs:
            Mask.paintMask(mask, box, blob.getMask(), blob.bbox, 1)

        if mask.any():
            # measure is brutally slower with non int types (factor 4), while byte&bool would be faster by 25%, conversion is fast.
            blob = blobs[0].copy()
            blob.updateUsingMask(box, mask.astype(int))
            return blob
        return None


    def subtract(self, blobA, blobB, scene):
        """
        Create a new blob that subtracting the second blob from the first one
        """

        (mask, box) = Mask.subtract(blobA.getMask(), blobA.bbox, blobB.getMask(), blobB.bbox)
        if mask.any():
            # measure is brutally slower with non int types (factor 4), while byte&bool would be faster by 25%, conversion is fast.
            blobA.updateUsingMask(box, mask.astype(int))
            return True
        return False



    def cut(self, blob, lines):
        """
        Given a curve specified as a set of points and a selected blob, the operation cuts it in several separed new blobs
        """
        points = blob.lineToPoints(lines)

        mask = blob.getMask()
        box = blob.bbox
        Mask.paintPoints(mask, box, points, 0)

        label_image = measure.label(mask)
        area_th = 30
        created_blobs = []
        for region in measure.regionprops(label_image):

            if region.area > area_th:
                id = len(self.seg_blobs)
                b = Blob(region, box[1], box[0], id + 1)
                b.class_color = blob.class_color
                b.class_name = blob.class_name
                created_blobs.append(b)

        return created_blobs


    def splitBlob(self, blob, seeds):

        seeds = np.asarray(seeds)
        seeds = seeds.astype(int)
        mask = blob.getMask()
        box = blob.bbox
        # x,y
        seeds_matrix = np.zeros_like(mask)
        # it would be useful add a slider to regulate this size parameter?
        size = 40
        #
        for i in range(0, seeds.shape[0]):
        #y,x
            seeds_matrix[seeds[i, 1] - box[0] - (size - 1): seeds[i, 1] - box[0] + (size - 1),
            seeds[i, 0] - box[1] - (size - 1): seeds[i, 0] - box[1] + (size - 1)] = 1

        distance = ndi.distance_transform_edt(mask)
        seeds_matrix = seeds_matrix > 0.5
        markers = ndi.label(seeds_matrix)[0]
        labels = watershed(-distance, markers, mask=mask)
        created_blobs = []
        for region in measure.regionprops(labels):
                idx = len(self.seg_blobs)
                b = Blob(region, box[1], box[0], idx + 1)
                b.class_color = blob.class_color
                b.class_name = blob.class_name
                created_blobs.append(b)

        return created_blobs






    def editBorder(self, blob, lines):
        #need padding

        #would be lovely to be able do edit holes too.
        #the main problem is snapping to the external contour

        points = blob.lineToPoints(lines, snap = True)

        if points is None:
            return
        
        if len(points) == 0:
            return

        pointsbox = Mask.pointsBox(points, 3)
        blobmask = blob.getMask()

        #add to mask painting the points as 1 and filling the holes.
        (mask, box) = Mask.jointMask(blob.bbox, pointsbox)
        Mask.paintMask(mask, box, blobmask, blob.bbox, 1)

        #save holes
        full = ndi.binary_fill_holes(mask.astype(int))
        holes = full & ~mask

        #cut from mask
        Mask.paintPoints(mask, box, points, 1)
        mask = ndi.binary_fill_holes(mask.astype(int))

        #erase the points to carve to remove the internal parts.
        Mask.paintPoints(mask, box, points, 0)

        #add back holes
        mask = mask & ~holes

        regions = measure.regionprops(measure.label(mask))

        if len(regions):
            largest = regions[0]
            for region in regions:
                if region.area > largest.area:
                    largest = region

            #adjust the image bounding box (relative to the region mask) to directly use area.image mask
            #image box is standard (minx, miny, maxx, maxy)
            box = np.array([ box[0] + largest.bbox[0], box[1] + largest.bbox[1], largest.bbox[3], largest.bbox[2] ])
            try:
                blob.updateUsingMask(box, largest.image.astype(int))
            except:
                pass



    def statistics(self):
        """
        Print some statistics about the current annotations.
        """

        number_of_seg = len(self.seg_blobs)
        dimensions = np.zeros(number_of_seg)
        for i, blob in enumerate(self.seg_blobs):

            dimensions[i] = blob.size()

        print("-------------------------")
        print("Total seg. blobs : %d" % number_of_seg)
        print("Minimum size     : %d" % np.min(dimensions))
        print("Maximum size     : %d" % np.max(dimensions))
        print("Size deviation   : %f" % np.std(dimensions))
        print("-------------------------")

    def clickedBlob(self, x, y):
        """
        It returns the blob clicked with the smallest area (to avoid problems with overlapping blobs).
        """

        blobs_clicked = []

        for blob in self.seg_blobs:

            point = np.array([[x, y]])
            out = measure.points_in_poly(point, blob.contour)
            if out[0] == True:
                blobs_clicked.append(blob)

        area_min = 100000000.0
        selected_blob = None
        for i in range(len(blobs_clicked)):
            blob = blobs_clicked[i]
            if blob.area < area_min:
                area_min = blob.area
                selected_blob = blob

        return selected_blob





    ###########################################################################
    ### IMPORT / EXPORT

    def import_label_map(self, filename, reference_map):
        """
        It imports a label map and create the corresponding blobs.
        The label map is rescaled such that it coincides with the reference map.
        """

        qimg_label_map = QImage(filename)
        qimg_label_map = qimg_label_map.convertToFormat(QImage.Format_RGB32)

        w = reference_map.width()
        h = reference_map.height()
        qimg_label_map = qimg_label_map.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        label_map = utils.qimageToNumpyArray(qimg_label_map)
        label_map = label_map.astype(np.int32)

        # RGB -> label code association (ok, it is a dirty trick but it saves time..)
        label_coded = label_map[:, :, 0] + (label_map[:, :, 1] << 8) + (label_map[:, :, 2] << 16)

        labels = measure.label(label_coded, connectivity=1)

        label_info = Labels()

        too_much_small_area = 10
        region_big = None

        created_blobs = []
        for region in measure.regionprops(labels):
            if region.area > too_much_small_area:
                id = len(self.seg_blobs)
                blob = Blob(region, 0, 0, id+1)

                # assign class
                row = region.coords[0,0]
                col = region.coords[0,1]
                color = label_map[row, col]

                index = label_info.searchColor(color)

                if index >= 0:

                    blob.class_name = label_info.getClassName(index)
                    blob.class_color = label_info.getColorByIndex(index)

                    created_blobs.append(blob)

        return created_blobs


    def export_data_table_for_Scripps(self, filename):

        # create a list of properties
        properties = ['Class name', 'Centroid x', 'Centroid y', 'Coral area', 'Coral perimeter', 'Coral maximum diameter', 'Coral note']

        # create a list of instances
        name_list = []
        visible_blobs = []
        for blob in self.seg_blobs:

            if blob.qpath_gitem.isVisible():
                index = blob.blob_name
                name_list.append(index)
                visible_blobs.append(blob)

        number_of_seg = len(name_list)
        class_name = []
        centroid_x = np.zeros(number_of_seg)
        centroid_y = np.zeros(number_of_seg)
        coral_area = np.zeros(number_of_seg)
        coral_perimeter = np.zeros(number_of_seg)
        coral_maximum_diameter = np.zeros(number_of_seg)
        coral_note = []

        for i, blob in enumerate(visible_blobs):

            class_name.append(blob.class_name)
            centroid_x[i] = blob.centroid[0]
            centroid_y[i] = blob.centroid[1]
            coral_area[i] = blob.area
            coral_perimeter[i] = blob.perimeter
            #coral_maximum_diameter[i] = blob.major_axis_length
            coral_note.append(blob.note)


        # create a dictionary
        dic = {
            'Class name': class_name,
            'Centroid x': centroid_x,
            'Centroid y': centroid_y,
            'Coral area': coral_area,
            'Coral perimeter': coral_perimeter,
            'Coral maximum diameter': coral_maximum_diameter,
            'Coral note': coral_note }

        # create dataframe
        df = pd.DataFrame(dic, columns=properties, index=name_list)
        df.to_csv(filename, sep='\t')


    def export_image_data_for_Scripps(self, map, filename):

        # create a black canvas of the same size of your map
        w = map.width()
        h = map.height()

        myPNG = QImage(w, h, QImage.Format_RGB32)
        myPNG.fill(qRgb(0, 0, 0))

        for i, blob in enumerate(self.seg_blobs):

            if blob.qpath_gitem.isVisible():

                if blob.class_color == "Empty":
                    rgb = qRgb(255, 255, 255)
                else:
                    rgb = qRgb(blob.class_color[0], blob.class_color[1], blob.class_color[2])

                blob_mask = blob.getMask()
                for x in range(blob_mask.shape[1]):
                    for y in range(blob_mask.shape[0]):

                        if blob_mask[y, x] == 1:
                            myPNG.setPixel(x + blob.bbox[1], y + blob.bbox[0], rgb)

                # draw black border
                [rr, cc] = polygon_perimeter(blob.contour[:, 1], blob.contour[:, 0])
                if rr.size > 0:
                    for i in range(len(rr)):
                        myPNG.setPixel(cc[i], rr[i], qRgb(0, 0, 0))

        myPNG.save(filename)


    def export_new_dataset(self, map, tile_size, step, basename):

        # create a black canvas of the same size of your map
        w = map.width()
        h = map.height()

        labelimg = QImage(w, h, QImage.Format_RGB32)
        labelimg.fill(qRgb(0, 0, 0))

        # CREATE LABEL IMAGE
        for i, blob in enumerate(self.seg_blobs):

            if blob.qpath_gitem.isVisible():

                if blob.class_color == "Empty":
                    rgb = qRgb(255, 255, 255)
                else:
                    rgb = qRgb(blob.class_color[0], blob.class_color[1], blob.class_color[2])

                blob_mask = blob.getMask()
                for x in range(blob_mask.shape[1]):
                    for y in range(blob_mask.shape[0]):

                        if blob_mask[y, x] == 1:
                            labelimg.setPixel(x + blob.bbox[1], y + blob.bbox[0], rgb)

        tile_cols = int((w - tile_size) / step)
        tile_rows = int((h - tile_size) / step)

        deltaW = int(tile_size / 2) + 1
        deltaH = int(tile_size / 2) + 1

        for row in range(tile_rows):
            for col in range(tile_cols):

                top = deltaH + row * step
                left = deltaW + col * step
                cropimg = utils.cropQImage(map, [top, left, tile_size, tile_size])
                croplabel = utils.cropQImage(labelimg, [top, left, tile_size, tile_size])

                filenameRGB = basename + "_RGB_" + str.format("{0:02d}", (row)) + "_" + str.format("{0:02d}", (col)) + ".png"
                filenameLabel = basename + "_L_" + str.format("{0:02d}", (row)) + "_" + str.format("{0:02d}", (col)) + ".png"

                cropimg.save(filenameRGB)
                croplabel.save(filenameLabel)
