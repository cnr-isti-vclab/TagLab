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

from source.Blob import Blob

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

        # list of all groups
        self.groups = []
        self.undo_blobs = []


    def addGroup(self, blobs):

        id = len(self.groups)
        group = Group(blobs, id+1)
        self.groups.append(group)
        return group

    def addBlob(self, seg_mask, map_pos_x, map_pos_y, area_mask):

        # create the blobs from the segmentation mask

        last_blobs_added = []

        seg_mask = ndi.binary_fill_holes(seg_mask).astype(int)
        label_image = measure.label(seg_mask)

        area_th = area_mask * 0.2

        for region in measure.regionprops(label_image):

            if region.area > area_th:

                id = len(self.seg_blobs)
                blob = Blob(region, map_pos_x, map_pos_y, id+1)
                self.seg_blobs.append(blob)

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

    def removeBlob(self, blob):

        # remove from the list of the blobs
        index = self.seg_blobs.index(blob)
        del self.seg_blobs[index]


    def as_dict(self, i):

        blob = self.seg_blobs[i]
        return {'coral name': blob.blob_name, 'group name': blob.group, 'class name': blob.class_name, ' centroid ': blob.centroid, 'coral area': blob.area, 'coral perimeter': blob.perimeter}

    def union(self, blobs):
        """
        Create a new blob that is the union of the (two) blobs given
        """

        blobA = blobs[0]
        blobB = blobs[1]

        y1A = blobA.bbox[0]
        x1A = blobA.bbox[1]
        x2A = x1A + blobA.bbox[2]
        y2A = y1A + blobA.bbox[3]

        y1B = blobB.bbox[0]
        x1B = blobB.bbox[1]
        x2B = x1B + blobB.bbox[2]
        y2B = y1B + blobB.bbox[3]

        x_left = min(x1A, x1B)
        y_top = min(y1A, y1B)
        x_right = max(x2A, x2B)
        y_bottom = max(y2A, y2B)

        bbox_union = np.array([y_top, x_left, x_right - x_left, y_bottom - y_top])
        mask_union = np.zeros((bbox_union[3], bbox_union[2]))

        blobA_mask = blobA.getMask()
        blobB_mask = blobB.getMask()

        for y in range(y1A, y2A):
            for x in range(x1A, x2A):

                xA = x - blobA.bbox[1]
                yA = y - blobA.bbox[0]

                xU = x - bbox_union[1]
                yU = y - bbox_union[0]

                if blobA_mask[yA, xA] == 1:
                    mask_union[yU, xU] = 1

        pixels_intersected = 0
        for y in range(y1B, y2B):
            for x in range(x1B, x2B):

                xB = x - blobB.bbox[1]
                yB = y - blobB.bbox[0]

                xU = x - bbox_union[1]
                yU = y - bbox_union[0]

                if blobB_mask[yB, xB] == 1:
                    if mask_union[yU, xU] == 1:
                        pixels_intersected += 1

                    mask_union[yU, xU] = 1

        if pixels_intersected > 0:
            blobA.updateUsingMask(bbox_union, mask_union)

            return True

        else:

            return False


    def subtract(self, blobA, blobB, scene):
        """
        Create a new blob that subtracting the second blob from the first one
        """

        y1A = blobA.bbox[0]
        x1A = blobA.bbox[1]
        x2A = x1A + blobA.bbox[2]
        y2A = y1A + blobA.bbox[3]

        y1B = blobB.bbox[0]
        x1B = blobB.bbox[1]
        x2B = x1B + blobB.bbox[2]
        y2B = y1B + blobB.bbox[3]

        x_left = max(x1A, x1B)
        y_top = max(y1A, y1B)
        x_right = min(x2A, x2B)
        y_bottom = min(y2A, y2B)

        # check if the selection is empty
        if x_right < x_left or y_bottom < y_top:
            return False
        else:

            xinf = x_left - blobA.bbox[1]
            yinf = y_top - blobA.bbox[0]
            xsup = x_right - blobA.bbox[1]
            ysup = y_bottom - blobA.bbox[0]

            blobA_mask = blobA.getMask()
            blobB_mask = blobB.getMask()

            flag = False
            for y in range(yinf, ysup):
                for x in range(xinf, xsup):

                    xB = x + blobA.bbox[1] - blobB.bbox[1]
                    yB = y + blobA.bbox[0] - blobB.bbox[0]

                    if blobB_mask[yB, xB] == 1:
                        blobA_mask[y, x] = 0
                        flag = True  # at least one pixel intersect

            # bbox is the same
            # mask has been updated directly
            if flag:
                blobA.updateUsingMask(blobA.bbox, blobA_mask)
                return True
            else:
                return False


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



    def cut(self, selected, points):
        """
        Given a curve specified as a set of points and a selected blob, the operation cuts it in several separed new blobs
        """

        # enlarge the mask
        y1A = selected.bbox[0]
        x1A = selected.bbox[1]
        x2A = x1A + selected.bbox[2]
        y2A = y1A + selected.bbox[3]

        pt_min = np.amin(points, axis=0)
        xmin = pt_min[0]
        ymin = pt_min[1]
        pt_max = np.amax(points, axis=0)
        xmax = pt_max[0]
        ymax = pt_max[1]

        x1B = int(xmin)
        y1B = int(ymin)
        x2B = int(xmax)
        y2B = int(ymax)

        x_left = min(x1A, x1B) - 2
        y_top = min(y1A, y1B) - 2
        x_right = max(x2A, x2B) + 2
        y_bottom = max(y2A, y2B) + 2

        bbox_union = np.array([y_top, x_left, x_right - x_left, y_bottom - y_top])
        mask_union = np.zeros((bbox_union[3], bbox_union[2]))

        blob_mask = selected.getMask()
        for y in range(blob_mask.shape[0]):
            for x in range(blob_mask.shape[1]):

                yy = y + (selected.bbox[0] - bbox_union[0])
                xx = x + (selected.bbox[1] - bbox_union[1])
                mask_union[yy,xx] = blob_mask[y,x]

        for i in range(points.shape[0]):

            x = points[i, 0]
            y = points[i, 1]

            yy = int(y) - bbox_union[0]
            xx = int(x) - bbox_union[1]

            for offsetx in range(-1, 2):
                for offsety in range(-1, 2):
                    mask_union[yy + offsety, xx + offsetx] = 0

        label_image = measure.label(mask_union)
        area_th = 30
        created_blobs = []
        for region in measure.regionprops(label_image):

            if region.area > area_th:
                id = len(self.seg_blobs)
                blob = Blob(region, x_left, y_top, id + 1)
                blob.class_color = selected.class_color
                blob.class_name = selected.class_name
                self.seg_blobs.append(blob)
                created_blobs.append(blob)

        return created_blobs


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

                    self.seg_blobs.append(blob)


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
