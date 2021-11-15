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

import os
import numpy as np
from cv2 import fillPoly

from skimage import measure

from skimage.filters import sobel
from scipy import ndimage as ndi
from PyQt5.QtGui import QPainter, QImage, QPen, QBrush, QColor, qRgb
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from skimage.color import rgb2gray
from skimage.draw import polygon_perimeter

from source import utils

import pandas as pd
from scipy import ndimage as ndi
from skimage.morphology import watershed, binary_dilation, binary_erosion
from source.Blob import Blob
import source.Mask as Mask

#refactor: change name to annotationS
class Annotation(QObject):
    """
        Annotation object contains all the annotations as a list of blobs.
    """
    blobUpdated = pyqtSignal(Blob)

    def __init__(self):
        super(QObject, self).__init__()

        #refactor: rename this to blobs.
        # list of all blobs
        self.seg_blobs = []

        #relative weight of depth map for refine borders
        #refactor: this is to be saved and loaded in qsettings
        self.refine_depth_weight = 0.0
        self.refine_conservative = 0.1

#        self.undo = Undo()                       #not saved

    def addBlob(self, blob):
        used = [blob.id for blob in self.seg_blobs]
        if blob.id in used:
            blob.id = self.getFreeId()
        self.seg_blobs.append(blob)

    def removeBlob(self, blob):
        index = self.seg_blobs.index(blob)
        del self.seg_blobs[index]

    #just
    def updateBlob(self, old_blob, new_blob):
        new_blob.id = old_blob.id;
        self.removeBlob(old_blob)
        self.addBlob(new_blob)
        self.blobUpdated.emit(new_blob)


    def blobById(self, id):
        for blob in self.seg_blobs:
            if blob.id == id:
                return blob
        return None

    def blobByGenet(self, genet):
        return [blob for blob in self.seg_blobs if blob.genet == genet]

    def save(self):
        return self.seg_blobs
        #data = []
        #for blob in self.seg_blobs:
        #    data.append(blob.toDict())
        #return data

    #move to BLOB!
    def blobsFromMask(self, seg_mask, map_pos_x, map_pos_y, area_mask):
        # create the blobs from the segmentation mask

        last_blobs_added = []

        seg_mask = ndi.binary_fill_holes(seg_mask).astype(int)
        label_image = measure.label(seg_mask)

        area_th = area_mask * 0.2

        for region in measure.regionprops(label_image):

            if region.area > area_th:

                blob = Blob(region, map_pos_x, map_pos_y, self.getFreeId())

                last_blobs_added.append(blob)

        return last_blobs_added

    def getFreeId(self):
        used = []
        for blob  in self.seg_blobs:
            used.append(blob.id)
        for id in range(len(used)):
            if id not in used:
                return id
        return len(used)

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

    def subtract(self, blobA, blobB):
        """
        Update the blobA subtracting the blobB from it
        """
        (mask, box) = Mask.subtract(blobA.getMask(), blobA.bbox, blobB.getMask(), blobB.bbox)

        if mask.any():
            # measure is brutally slower with non int types (factor 4), while byte&bool would be faster by 25%, conversion is fast.
            blobA.updateUsingMask(box, mask.astype(int))
            return True
        return False

    def addingIntersection(self, blobA, blobB, blobC):
        """
        Update the blobA by adding to it the intersection between the blobB and the blobC
        """
        mask_intersect, bbox_intersect = Mask.intersectMask(blobB.getMask(), blobB.bbox, blobC.getMask(), blobC.bbox)

        bbox = Mask.jointBox([blobA.bbox, bbox_intersect])
        (mask, bbox) = Mask.jointMask(bbox, bbox)

        Mask.paintMask(mask, bbox, blobA.getMask(), blobA.bbox, 1)
        Mask.paintMask(mask, bbox, mask_intersect, bbox_intersect, 1)

        if mask.any():
            blobA.updateUsingMask(bbox, mask.astype(int))

    def cut(self, blob, lines):
        """
        Given a curve specified as a set of points and a selected blob, the operation cuts it in several separed new blobs
        """
        points = blob.lineToPoints(lines, snap=False)

        mask = blob.getMask()
        original = mask.copy()
        box = blob.bbox
        #box is y, x, w, h
        Mask.paintPoints(mask, box, points, 0)

        label_image = measure.label(mask, connectivity=1)
        for point in points:
            x = point[0] - box[1]
            y = point[1] - box[0]

            if x <= 0 or y <= 0 or x >= box[2] -1 or y >= box[3] -1:
                continue

            if original[y][x] == 0:
                continue
            #the point in points were painted with zeros and we need to assign to some label (we pick the largest of the neighbors
            largest = 0
            largest = max(label_image[y+1][x], largest)
            largest = max(label_image[y-1][x], largest)
            largest = max(label_image[y][x+1], largest)
            largest = max(label_image[y][x-1], largest)
            label_image[y][x] = largest

        area_th = 30
        created_blobs = []
        first = True
        for region in measure.regionprops(label_image):

            if region.area > area_th:
                b = Blob(region, box[1], box[0], self.getFreeId())
                b.class_name = blob.class_name
                created_blobs.append(b)

        return created_blobs


    #expect numpy img and mask
    def refineBorder(self, box, blob, img, depth, mask, grow, lastedit):
        clippoints = None

        if lastedit is not None:
            points = [blob.drawLine(line) for line in lastedit]
            if points is not None and len(points) > 0:
                clippoints = np.empty(shape=(0, 2), dtype=int)
                for arc in points:
                    clippoints = np.append(clippoints, arc, axis=0)
                origin = np.array([box[1], box[0]])
                clippoints = clippoints - origin
        try:
            from coraline.Coraline import segment, mutual
            #rgb_weights = [0.2989, 0.5870, 0.1140]
            #gray = np.dot(img[...,:3], rgb_weights).astype(np.uint8)
            #mutual(gray)
            #a = utils.floatmapToQImage(gray.astype(float))
            #a.save("test.png")
            segment(img, depth, mask, clippoints, 0.0, conservative=self.refine_conservative, grow=grow, radius=30, depth_weight = self.refine_depth_weight)

        except Exception as e:
            print(e, flush=True)
            #msgBox = QMessageBox()
            #msgBox.setText(str(e))
            #msgBox.exec()
#            return

        #TODO this should be moved to a function!
        area_th = 500
        created_blobs = []
        first = True
        label_image = measure.label(mask, connectivity=1)
        for region in measure.regionprops(label_image):
            if region.area > area_th:
                b = Blob(region, box[1], box[0], self.getFreeId())
                b.class_name = blob.class_name
                created_blobs.append(b)
        return created_blobs

    def splitBlob(self,map, blob, seeds):

        seeds = np.asarray(seeds)
        seeds = seeds.astype(int)
        mask = blob.getMask()
        box = blob.bbox
        cropimg = utils.cropQImage(map, box)
        cropimgnp = rgb2gray(utils.qimageToNumpyArray(cropimg))

        edges = sobel(cropimgnp)

        # x,y
        seeds_matrix = np.zeros_like(mask)

        size = 40
        #
        for i in range(0, seeds.shape[0]):
        #y,x
            seeds_matrix[seeds[i, 1] - box[0] - (size - 1): seeds[i, 1] - box[0] + (size - 1),
            seeds[i, 0] - box[1] - (size - 1): seeds[i, 0] - box[1] + (size - 1)] = 1

        distance = ndi.distance_transform_edt(mask)
        # distance = ndi.distance_transform_edt(cropimg)
        seeds_matrix = seeds_matrix > 0.5
        markers = ndi.label(seeds_matrix)[0]
        # labels = watershed(-distance, markers, mask=mask)
        labels = watershed((-distance+100*edges)/2, markers, mask=mask)
        created_blobs = []
        for region in measure.regionprops(labels):
                b = Blob(region, box[1], box[0], self.getFreeId())
                b.class_name = blob.class_name
                created_blobs.append(b)

        return created_blobs


    def editBorder(self, blob, lines):
        points = [blob.drawLine(line) for line in lines]

        if points is None or len(points) == 0 or all(len(p) == 0 for p in points):
            return

        # compute the box for the outer contour
        intersected = False
        (mask, box, intersected) = self.editBorderContour(blob, blob.contour, points)

        pointIntersectsContours = intersected
        for contour in blob.inner_contours:
            (inner_mask, inner_box, intersected) = self.editBorderContour(blob, contour, points)
            pointIntersectsContours = pointIntersectsContours or intersected
            Mask.paintMask(mask, box, inner_mask, inner_box, 0)

        if not pointIntersectsContours:
            #probably a hole, draw the points fill the hole and subtract from mask
            allpoints = np.empty(shape=(0, 2), dtype=int)
            for arc in points:
                allpoints = np.append(allpoints, arc, axis =0)
            points_box = Mask.pointsBox(allpoints, 4)
            (points_mask, points_box) = Mask.jointMask(points_box, points_box)
            Mask.paintPoints(points_mask, points_box, allpoints, 1)
            origin = np.array([points_box[1], points_box[0]])
            Mask.paintPoints(points_mask, points_box, allpoints - origin, 1)
            points_mask = ndi.binary_fill_holes(points_mask)
            points_mask = binary_erosion(points_mask)
            Mask.paintMask(mask, box, points_mask, points_box, 0)


        blob.updateUsingMask(box, mask)


    def editBorderContour(self, blob, contour, points):
        snapped_points = np.empty(shape=(0, 2), dtype=int)
        for arc in points:
            snapped = blob.snapToContour(arc, contour)
            if snapped is not None:
                snapped_points = np.append(snapped_points, snapped, axis = 0)

        contour_box = Mask.pointsBox(contour, 4)

        #if the countour did not intersect with the outer contour, get the mask of the outer contour
        if snapped_points is None or len(snapped_points) == 0:
            # not very elegant repeated code...
            (mask, box) = Mask.jointMask(contour_box, contour_box)
            origin = np.array([box[1], box[0]])
            contour_points = contour.round().astype(int)
            fillPoly(mask, pts=[contour_points - origin], color=(1))
            return (mask, box, False)

        points_box = Mask.pointsBox(snapped_points, 4)

        # create a mask large enough to accomodate the points and the contour and paint.
        (mask, box) = Mask.jointMask(contour_box, points_box)

        origin = np.array([box[1], box[0]])
        contour_points = contour.round().astype(int)
        fillPoly(mask, pts=[contour_points - origin], color=(1, 1, 1))

        Mask.paintPoints(mask, box, snapped_points, 1)

        mask = ndi.binary_fill_holes(mask)

        # now draw in black the part of the points inside the contour
        Mask.paintPoints(mask, box, snapped_points, 0)

        # now we label all the parts and keep the larges only
        regions = measure.regionprops(measure.label(mask, connectivity=1))

        largest = max(regions, key=lambda region: region.area)

        # adjust the image bounding box (relative to the region mask) to directly use area.image mask
        box = np.array([box[0] + largest.bbox[0], box[1] + largest.bbox[1], largest.bbox[3] - largest.bbox[1],
                        largest.bbox[2] - largest.bbox[0]])
        return (largest.image, box, True)

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

    def create_label_map(self, size, labels_info):
        """
        Create a label map as a QImage and returns it.
        """

        # create a black canvas of the same size of your map
        w = size.width()
        h = size.height()

        imagebox = [0, 0, h, w]
        image = np.zeros([h, w, 3], np.uint8)

        for i, blob in enumerate(self.seg_blobs):
            if not blob.qpath_gitem.isVisible():
                continue

            if blob.class_name == "Empty":
                rgb = [255, 255, 255]
            else:
                rgb = labels_info[blob.class_name]

            mask = blob.getMask().astype(bool)  #bool is required for bitmask indexing
            box = blob.bbox
            (box[2], box[3]) = (box[3] + box[0], box[2] + box[1])
            #box is now startx,starty,endx,endy

            #range is the interection of box and imagebox
            range = [max(box[0], imagebox[0]), max(box[1], imagebox[1]), min(box[2], imagebox[2]), min(box[3], imagebox[3])]
            subimage = image[range[0] - imagebox[0]:range[2] - imagebox[0], range[1] - imagebox[1]:range[3] - imagebox[1]]
            submask = mask[range[0] - box[0]:range[2] - box[0], range[1] - box[1]:range[3] - box[1]]

            #use the binary mask to assign a color
            subimage[submask] = rgb

            #create 1px border: dilate then subtract the mask.
            border = binary_dilation(submask) & ~submask

            #select only the border over blobs of the same color and draw the border
            samecolor = np.all(subimage == rgb, axis=-1)
            subimage[border & samecolor] = [0, 0, 0]

        labelimg = utils.rgbToQImage(image)
        return labelimg

    def import_label_map(self, filename, labels_info, w_target, h_target, create_holes=False):
        """
        It imports a label map and create the corresponding blobs.
        The label map is rescaled such that it coincides with the reference map.
        """

        qimg_label_map = QImage(filename)
        qimg_label_map = qimg_label_map.convertToFormat(QImage.Format_RGB32)

        if w_target > 0 and h_target > 0:
            qimg_label_map = qimg_label_map.scaled(w_target, h_target, Qt.IgnoreAspectRatio, Qt.FastTransformation)

        label_map = utils.qimageToNumpyArray(qimg_label_map)
        label_map = label_map.astype(np.int32)

        # RGB -> label code association (ok, it is a dirty trick but it saves time..)
        label_coded = label_map[:, :, 0] + (label_map[:, :, 1] << 8) + (label_map[:, :, 2] << 16)

        labels = measure.label(label_coded, connectivity=1)

        too_much_small_area = 50
        region_big = None

        created_blobs = []
        for region in measure.regionprops(labels):
            if region.area > too_much_small_area:
                id = len(self.seg_blobs)
                blob = Blob(region, 0, 0, self.getFreeId())

                # assign class
                row = region.coords[0, 0]
                col = region.coords[0, 1]
                color = label_map[row, col]

                for label_name in labels_info.keys():
                    c = labels_info[label_name]
                    if c[0] == color[0] and c[1] == color[1] and c[2] == color[2]:
                        blob.class_name = label_name
                        break
                if create_holes or blob.class_name is not 'Empty':
                    created_blobs.append(blob)

        return created_blobs


    def export_data_table_for_Scripps(self, scale_factor, filename):

        # create a list of properties
        properties = ['Blob id','Class name', 'Centroid x', 'Centroid y', 'Coral area', 'Coral surf area', 'Genet id', 'Coral perimeter', 'Coral note']

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
        blob_id = np.zeros(number_of_seg, int)
        genet_id = np.zeros(number_of_seg, int)
        centroid_x = np.zeros(number_of_seg)
        centroid_y = np.zeros(number_of_seg)
        coral_area = np.zeros(number_of_seg)
        coral_surf_area = np.zeros(number_of_seg)
        coral_perimeter = np.zeros(number_of_seg)
        coral_note = []

        for i, blob in enumerate(visible_blobs):

            blob_id[i] = blob.id
            class_name.append(blob.class_name)
            centroid_x[i] = round(blob.centroid[0], 1)
            centroid_y[i] = round(blob.centroid[1], 1)
            coral_area[i] = round(blob.area * (scale_factor) * (scale_factor)/ 100,2)
            coral_perimeter[i] = round(blob.perimeter*scale_factor / 10,1)
            coral_note.append(blob.note)

            if blob.surface_area > 0.0:
               coral_surf_area[i] = round(blob.surface_area * (scale_factor) * (scale_factor) / 100, 2)

            if blob.genet is not None:
               genet_id[i] = blob.genet

        # create a dictionary
        dic = {
            'Blob id' : blob_id,
            'Class name': class_name,
            'Genet id': genet_id,
            'Centroid x': centroid_x,
            'Centroid y': centroid_y,
            'Coral area': coral_area,
            'Coral surf area': coral_surf_area,
            'Coral perimeter': coral_perimeter,
            'Coral note': coral_note}

        # create dataframe
        df = pd.DataFrame(dic, columns=properties)
        df.to_csv(filename, sep=',', index=False)


    def export_image_data_for_Scripps(self, size, filename, labels_info):
        label_map = self.create_label_map(size, labels_info)
        label_map.save(filename, 'png')
