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
# GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

import os
import re
import csv
import sys
from datetime import datetime

from cv2 import fillPoly

from skimage import measure
from skimage.filters import sobel
from PyQt5.QtGui import QPainter, QImage, QPen, QBrush, QColor, qRgb
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QRectF
from skimage.color import rgb2gray
from skimage.draw import polygon_perimeter

from source import genutils

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage.morphology import binary_dilation, binary_erosion
from skimage.segmentation import watershed
from source.Blob import Blob
from source.Point import Point
import source.Mask as Mask
from source.Label import Label
from coraline.Coraline import segment, mutual


# from PIL import Image as Img  #for debug

# refactor: change name to annotationS
class Annotation(object):
    """
        Annotation object contains all the annotations, a list of blobs and a list of annotation points
        Annotation point can't be manually edited or removed, only classified
    """

    def __init__(self):

        # refactor: rename this to blobs.
        # list of all blobs
        self.seg_blobs = []
        self.annpoints = []
        self.annotationsDict = {}

        # relative weight of depth map for refine borders
        # refactor: this is to be saved and loaded in qsettings
        self.refine_depth_weight = 0.0
        self.refine_conservative = 0.1

        # cache
        self.table_needs_update = True


    def addPoint(self, point):


        used = [point.id for point in self.annpoints]
        if point.id in used:
            point.id = self.getFreePointId()
        self.annpoints.append(point)

        self.table_needs_update = True


    def addBlob(self, blob):

        used = [blob.id for blob in self.seg_blobs]
        if blob.id in used:
            blob.id = self.getFreeId()
        self.seg_blobs.append(blob)

        self.table_needs_update = True

    def removeAnn(self, blob_or_point):

        """ removes both regions and points (they are both called blob)"""

        if type(blob_or_point) == Point:
            point = blob_or_point
            try:
                index = self.annpoints.index(point)
            except:
                index = -1

            if index < 0:
                print("WARNING!! point to be removed not found !")
            else:
                del self.annpoints[index]
                self.table_needs_update = True
        else:
            blob = blob_or_point
            try:
                index = self.seg_blobs.index(blob)
            except:
                index = -1

            if index < 0:
                print("WARNING!! region to be removed not found !")
            else:
                del self.seg_blobs[index]
                self.table_needs_update = True

    def updateBlob(self, old_blob, new_blob):

        new_blob.id = old_blob.id
        self.removeAnn(old_blob)
        self.addBlob(new_blob)
        self.table_needs_update = True

    def setBlobClass(self, blob, class_name):

        blob.class_name = class_name
        self.table_needs_update = True

    def setPointClass(self, point, class_name):

        if point.class_name == class_name:
            return
        else:
            old_class_name = point.class_name
            point.class_name = class_name

    def blobById(self, id):
        for blob in self.seg_blobs:
            if blob.id == id:
                return blob
        return None

    def pointById(self, id):
        for point in self.annpoints:
            if point.id == id:
                return point
        return None

    def blobByGenet(self, genet):
        return [blob for blob in self.seg_blobs if blob.genet == genet]

    def save(self):

        self.annotationsDict = { "regions": self.seg_blobs, "points": self.annpoints }

        return self.annotationsDict

    # move to BLOB!
    def blobsFromMask(self, seg_mask, map_pos_x, map_pos_y, area_mask):
        # create the blobs from the segmentation mask

        last_blobs_added = []

        #seg_mask = ndi.binary_fill_holes(seg_mask).astype(int)
        label_image = measure.label(seg_mask)

        area_th = area_mask * 0.05

        for region in measure.regionprops(label_image):

            if region.area > area_th:
                blob = Blob(region, map_pos_x, map_pos_y, self.getFreeId())

                last_blobs_added.append(blob)

        return last_blobs_added

    def getFreeId(self):
        used = []
        for blob in self.seg_blobs:
            used.append(blob.id)
        for id in range(len(used)):
            if id not in used:
                return id
        return len(used)

    def getFreePointId(self):
        used = []
        for annpoint in self.annpoints:
            used.append(annpoint.id)
        for id in range(len(used)):
            if id not in used:
                return id
        return len(used)

    def union(self, blobs):
        """
        Create a new blob that is the union of the (two) blobs given
        """
        # boxs are in image space, masks invert x and y.
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

    def createNegative(self, blobs, wa):

        inner_blobs = self.calculate_inner_blobs(wa)
        boxes = []
        for blob in blobs:
            boxes.append(blob.bbox)

        wamask = np.zeros((wa[3], wa[2])).astype(np.uint8)
        mask = wamask.copy()
        box = wa.copy()

        for blob in inner_blobs:
            Mask.paintMask(mask, box, blob.getMask().astype(np.uint8), blob.bbox, 1)

        inversemask = 1 - mask
        area_min = 0.0
        created_blobs = self.blobsFromMask(inversemask, box[1], box[0], area_min)

        return created_blobs

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
        # box is y, x, w, h
        Mask.paintPoints(mask, box, points, 0)

        label_image = measure.label(mask, connectivity=1)
        for point in points:
            x = point[0] - box[1]
            y = point[1] - box[0]

            if x <= 0 or y <= 0 or x >= box[2] - 1 or y >= box[3] - 1:
                continue

            if original[y][x] == 0:
                continue
            # the point in points were painted with zeros and we need to assign to some label (we pick the largest of the neighbors
            largest = 0
            largest = max(label_image[y + 1][x], largest)
            largest = max(label_image[y - 1][x], largest)
            largest = max(label_image[y][x + 1], largest)
            largest = max(label_image[y][x - 1], largest)
            label_image[y][x] = largest

        area_th = 30
        created_blobs = []
        for region in measure.regionprops(label_image):

            if region.area > area_th:
                b = Blob(region, box[1], box[0], self.getFreeId())
                b.class_name = blob.class_name
                created_blobs.append(b)

        return created_blobs

    # expect numpy img and mask
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
            # rgb_weights = [0.2989, 0.5870, 0.1140]
            # gray = np.dot(img[...,:3], rgb_weights).astype(np.uint8)
            # mutual(gray)
            # a = genutils.floatmapToQImage(gray.astype(float))
            # a.save("test.png")
            segment(img, depth, mask, clippoints, 0.0, conservative=self.refine_conservative, grow=grow, radius=30,
                    depth_weight=self.refine_depth_weight)

        except Exception as e:
            print(e, flush=True)
            # msgBox = QMessageBox()
            # msgBox.setText(str(e))
            # msgBox.exec()
        #            return

        # TODO this should be moved to a function!
        area_th = 50
        created_blobs = []
        label_image = measure.label(mask, connectivity=1)
        for region in measure.regionprops(label_image):
            if region.area > area_th:
                b = Blob(region, box[1], box[0], self.getFreeId())
                b.class_name = blob.class_name
                created_blobs.append(b)
        return created_blobs

    def createBlobFromSingleMask(self, mask, offset_x, offset_y):

        label_image = measure.label(mask, connectivity=1)
        blob = None
        for region in measure.regionprops(label_image):
            blob = Blob(region, offset_x, offset_y, self.getFreeId())
        return blob


    def splitBlob(self, map, blob, seeds):

        seeds = np.asarray(seeds)
        seeds = seeds.astype(int)
        mask = blob.getMask()
        box = blob.bbox
        cropimg = genutils.cropQImage(map, box)
        cropimgnp = rgb2gray(genutils.qimageToNumpyArray(cropimg))

        edges = sobel(cropimgnp)

        # x,y
        seeds_matrix = np.zeros_like(mask)

        size = 40
        #
        for i in range(0, seeds.shape[0]):
            # y,x
            seeds_matrix[seeds[i, 1] - box[0] - (size - 1): seeds[i, 1] - box[0] + (size - 1),
            seeds[i, 0] - box[1] - (size - 1): seeds[i, 0] - box[1] + (size - 1)] = 1

        distance = ndi.distance_transform_edt(mask)
        # distance = ndi.distance_transform_edt(cropimg)
        seeds_matrix = seeds_matrix > 0.5
        markers = ndi.label(seeds_matrix)[0]
        # labels = watershed(-distance, markers, mask=mask)
        labels = watershed((-distance + 100 * edges) / 2, markers, mask=mask)
        created_blobs = []
        for region in measure.regionprops(labels):
            b = Blob(region, box[1], box[0], self.getFreeId())
            b.class_name = blob.class_name
            created_blobs.append(b)

        return created_blobs

    def editBorder(self, blob, lines):
        points = blob.lineToPoints(lines, snap=False)
        if points is None or len(points) == 0 or all(len(p) == 0 for p in points):
            return

        # get the bounding box of the points (we need to enlarge the mask box)
        points_box = Mask.pointsBox(points, 8)

        blob_mask = blob.getMask()
        blob_box = blob.bbox
        (mask, box) = Mask.jointMask(blob_box, points_box)

        # 2 is foregraound, 1 is background, 3 is the points
        Mask.paintMask(mask, box, blob_mask, blob_box, 1)

        #        in case we need to debug.
        #        im = Img.fromarray(mask)
        #        im.save("0_start.png")

        mask[mask == 1] = 2
        mask[mask == 0] = 1  # paint background, as points will be zero.

        # label image should at least mantain 1 as backround and 2 as foreground (save for the internal holes)
        original_label = measure.label(mask, connectivity=1)

        # draw the points to separate the areas
        Mask.paintPoints(mask, box, points, 3)

        label_image = measure.label(mask, connectivity=1)

        # reassing the rendered points bottom right area so the partitioning is properly done.
        for point in points:
            x = point[0] - box[1]
            y = point[1] - box[0]

            largest = 0
            if mask[y + 1][x + 1] != 3:
                largest = max(label_image[y + 1][x + 1], largest)
            elif mask[y][x + 1] != 3:
                largest = max(label_image[y][x + 1], largest)
            elif mask[y + 1][x] != 3:
                largest = max(label_image[y + 1][x], largest)
            label_image[y][x] = largest

        regions = measure.regionprops(label_image)

        # for each region we find which original label intersects the most
        for region in regions:
            (labels, counts) = np.unique(original_label[tuple(region.coords.T)], return_counts=True)
            n = np.argmax(counts)
            region.original_area = counts[n]
            region.original_label = labels[n]

        final_mask = np.zeros((box[3], box[2])).astype(np.uint8)

        # if 2 is the label for the original foreground
        # if a region is the largest area with the its original label, keep it foreground (2, so paint 1) or background (not 2, paint 0)
        # otherwise it's a small region which we need to flip.
        for region in regions:
            largest = max(regions, key=lambda aregion,
                                              label=region.original_label: aregion.original_area if aregion.original_label == label else 0)
            if region.original_label == 2 and largest == region or region.original_label != 2 and largest != region:
                final_mask[tuple(region.coords.T)] = 1
            else:
                final_mask[tuple(region.coords.T)] = 0

        blob.updateUsingMask(box, final_mask)

    def editBorder1(self, blob, lines):
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
            # probably a hole, draw the points fill the hole and subtract from mask
            allpoints = np.empty(shape=(0, 2), dtype=int)
            for arc in points:
                allpoints = np.append(allpoints, arc, axis=0)
            points_box = Mask.pointsBox(allpoints, 4)
            (points_mask, points_box) = Mask.jointMask(points_box, points_box)
            Mask.paintPoints(points_mask, points_box, allpoints, 1)
            origin = np.array([points_box[1], points_box[0]])
            Mask.paintPoints(points_mask, points_box, allpoints - origin, 1)
            points_mask = ndi.binary_fill_holes(points_mask)
            selem = np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]])
            points_mask = binary_erosion(points_mask, selem)
            Mask.paintMask(mask, box, points_mask, points_box, 0)

        blob.updateUsingMask(box, mask)

    def editBorderContour(self, blob, contour, points):
        snapped_points = np.empty(shape=(0, 2), dtype=int)
        for arc in points:
            snapped = blob.snapToContour(arc, contour)
            if snapped is not None:
                snapped_points = np.append(snapped_points, snapped, axis=0)

        contour_box = Mask.pointsBox(contour, 4)

        # if the countour did not intersect with the outer contour, get the mask of the outer contour
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

        mask1 = ndi.binary_fill_holes(mask)
        selem = np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]])
        mask = binary_erosion(mask1, selem) | mask

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

    def clickedPoint(self, x, y):

        # annpoints_clicked = []
        point = np.array([[x, y]])

        selected_annpoint = None
        for annpoint in self.annpoints:
            cx = annpoint.coordx
            cy = annpoint.coordy
            c = np.array([[cx, cy]])
            dist = np.linalg.norm(point - c)

            # for i in range(len(annpoints_clicked)):
            #     point = annpoints_clicked[i]
            if dist < 11:
                selected_annpoint = annpoint

        return selected_annpoint

    ###########################################################################
    ### IMPORT / EXPORT

    def create_label_map(self, size, labels_dictionary, working_area):
        """
        Create a label map as a QImage and returns it.
        """

        # create a black canvas of the same size of your map
        w = size.width()
        h = size.height()

        imagebox = [0, 0, h, w]
        image = np.zeros([h, w, 3], np.uint8)

        for i, blob in enumerate(self.seg_blobs):

            if blob.qpath_gitem is not None:
                if not blob.qpath_gitem.isVisible():
                    continue

            if blob.class_name == "Empty":
                rgb = [255, 255, 255]
            else:
                rgb = labels_dictionary[blob.class_name].fill

            mask = blob.getMask().astype(bool)  # bool is required for bitmask indexing
            box = blob.bbox.copy()  # blob.bbox is top, left, width, height
            (box[2], box[3]) = (box[3] + box[0], box[2] + box[1])  # box is now startx, starty, endx, endy

            # range is the interection of box and imagebox
            range = [max(box[0], imagebox[0]), max(box[1], imagebox[1]), min(box[2], imagebox[2]),
                     min(box[3], imagebox[3])]
            subimage = image[range[0] - imagebox[0]:range[2] - imagebox[0],
                       range[1] - imagebox[1]:range[3] - imagebox[1]]
            submask = mask[range[0] - box[0]:range[2] - box[0], range[1] - box[1]:range[3] - box[1]]

            # use the binary mask to assign a color
            subimage[submask] = rgb

            # create 1px border: dilate then subtract the mask.
            border = binary_dilation(submask) & ~submask

            # select only the border over blobs of the same color and draw the border
            samecolor = np.all(subimage == rgb, axis=-1)
            subimage[border & samecolor] = [0, 0, 0]

        labelimg = genutils.rgbToQImage(image)

        if working_area is not None:
            # FIXME: this is inefficient! The working_area should be used during the drawing.
            labelimg_cropped = genutils.cropQImage(labelimg, working_area)
            return labelimg_cropped
        else:
            return labelimg

    def calculate_inner_blobs(self, working_area):
        """
        This consider only blobs falling ENTIRELY in the working area"
        """

        selected_blobs = self.seg_blobs
        inner_blobs = []
        for blob in selected_blobs:
            if Mask.insideBox(working_area, blob.bbox):
                inner_blobs.append(blob)

        return inner_blobs


    def calculate_inner_points(self, working_area):
        """
        This consider only points having center inside the working area"
        """

        selected_annpoints = self.annpoints
        inner_annpoints = []
        for annpoint in selected_annpoints:
            if (annpoint.coordy > working_area[0]) and (annpoint.coordy < working_area[0] + working_area[3]):
                if (annpoint.coordx > working_area[1]) and (annpoint.coordx < working_area[1] + working_area[2]):
                    inner_annpoints.append(annpoint)


        return inner_annpoints


    def calculate_perclass_blobs_value(self, label, pixel_size):
        """
        This consider all the existing blobs, inside and outside the working area.
        It returns number of blobs and coverage.
        """
        count = 0
        tot_area = 0.0
        for blob in self.seg_blobs:
            if blob.class_name == label.name:
                count = count + 1
                tot_area = tot_area + blob.area
        tot_area = round((tot_area * pixel_size * pixel_size) / 100.0, 2)

        return count, tot_area

    def countPoints(self, label):

        """
        This consider all the existing points, inside and outside the working area.
        It returns number of points per label
        """
        count = 0
        tot_area = 0.0
        for annpoint in self.annpoints:
            if annpoint.class_name == label.name:
                count = count + 1
        return count


    def import_label_map(self, filename, labels_dictionary, offset, scale, create_holes=False):
        """
        It imports a label map and create the corresponding blobs.
        The offset is stored as a [top, left] coordinates and scale are the scale factors of X and Y axis respectively.
        """

        qimg_label_map = QImage(filename)
        qimg_label_map = qimg_label_map.convertToFormat(QImage.Format_RGB32)

        # label map rescaling (if necessary)
        w_rescaled = round(qimg_label_map.width() * scale[0])
        h_rescaled = round(qimg_label_map.height() * scale[1])
        qimg_label_map = qimg_label_map.scaled(w_rescaled, h_rescaled, Qt.IgnoreAspectRatio, Qt.FastTransformation)

        label_map = genutils.qimageToNumpyArray(qimg_label_map)
        label_map = label_map.astype(np.int32)

        # RGB -> label code association (ok, it is a dirty trick but it saves time..)
        label_coded = label_map[:, :, 0] + (label_map[:, :, 1] << 8) + (label_map[:, :, 2] << 16)

        labels = measure.label(label_coded, connectivity=1)

        too_much_small_area = 50
        region_big = None

        offset_x = offset[1]
        offset_y = offset[0]
        created_blobs = []
        for region in measure.regionprops(labels):
            if region.area > too_much_small_area:
                id = len(self.seg_blobs)

                blob = Blob(region, offset_x, offset_y, self.getFreeId())

                # assign class
                row = region.coords[0, 0]
                col = region.coords[0, 1]
                color = label_map[row, col]

                for key in labels_dictionary.keys():
                    c = labels_dictionary[key].fill
                    if c[0] == color[0] and c[1] == color[1] and c[2] == color[2]:
                        blob.class_name = labels_dictionary[key].name
                        break
                if create_holes or blob.class_name != 'Empty':
                    created_blobs.append(blob)

        return created_blobs

    def export_data_table(self, project, image, imagename, filename, choice):

        working_area = project.working_area
        scale_factor = image.pixelSize()
        date = image.acquisition_date

        # create a list of instances

        blobindexlist = []
        pointindexlist = []

        # check visibility and working area of both
        if working_area is None:
            # all the blobs are considered
            self.blobs = self.seg_blobs

        else:
            # only blobs and points inside the working area are considered
            self.blobs = self.calculate_inner_blobs(working_area)
            self.annpoints = self.calculate_inner_points(working_area)

        visible_blobs = []

        for blob in self.blobs:
            if blob.qpath_gitem.isVisible():
                index = blob.blob_name
                blobindexlist.append(index)
                visible_blobs.append(blob)

        visible_points = []

        for annpoint in self.annpoints:
            if annpoint.cross1_gitem.isVisible():
                point_id = annpoint.id
                pointindexlist.append(point_id)
                visible_points.append(annpoint)

        if choice == 'Regions':
            visible_points = []

        if choice == 'Points':
            visible_blobs = []

        number_of_rows = len(visible_blobs) + len(visible_points)

        # create a common dictionary

        dict = {
            'Image name': [],
            'TagLab Id': np.zeros(number_of_rows, dtype=np.int64),
            'TagLab Type': [],
            'TagLab Date': [],
            'TagLab Class name': [],
            'TagLab Genet Id': np.zeros(number_of_rows, dtype=np.int64),
            'TagLab Centroid x': np.zeros(number_of_rows),
            'TagLab Centroid y': np.zeros(number_of_rows),
            'TagLab Area': np.zeros(number_of_rows),
            'TagLab Surf. area': np.zeros(number_of_rows),
            'TagLab Perimeter': np.zeros(number_of_rows),
            'TagLab Note': []}

        # Are attributes named the same? Check
        for attribute in project.region_attributes.data:
            key = attribute["name"]
            if attribute['type'] in ['string', 'keyword']:
                dict[key] = []
            elif attribute['type'] in ['integer number']:
                dict[key] = np.zeros(number_of_rows, dtype=np.int64)
            elif attribute['type'] in ['decimal number']:
                dict[key] = np.zeros(number_of_rows, dtype=np.float64)
            else:
                # unknown attribute type, not saved
                pass

        # fill it
        i = 0

        for blob in visible_blobs:
            dict['Image name'].append(imagename)
            dict['TagLab Id'][i] = blob.id
            dict['TagLab Type'].append('Region')
            dict['TagLab Date'].append(date)
            dict['TagLab Class name'].append(blob.class_name)
            dict['TagLab Centroid x'][i] = round(blob.centroid[0], 1)
            dict['TagLab Centroid y'][i] = round(blob.centroid[1], 1)
            dict['TagLab Area'][i] = round(blob.area * scale_factor * scale_factor / 100, 2)
            if blob.surface_area > 0.0:

                dict['TagLab Surf. area'][i] = round(blob.surface_area * scale_factor * scale_factor / 100, 2)

            dict['TagLab Perimeter'][i] = round(blob.perimeter * scale_factor / 10, 1)

            if blob.genet is not None:
                dict['TagLab Genet Id'][i] = blob.genet

            dict['TagLab Note'].append(blob.note)

            for attribute in project.region_attributes.data:

                key = attribute["name"]

                try:
                    value = blob.data[key]
                except:
                    value = None

                if attribute['type'] == 'integer number':

                    if value is not None:
                        dict[key][i] = value
                    else:
                        dict[key][i] = 0

                elif attribute['type'] == 'decimal number':

                    if value is not None:
                        dict[key][i] = value
                    else:
                        dict[key][i] = np.NaN

                else:
                    if value is not None:
                        dict[key].append(value)
                    else:
                        dict[key].append('')

            i = i + 1

        j = len(visible_blobs)
        for annpoint in visible_points:
            dict['Image name'].append(imagename)
            dict['TagLab Id'][j] = annpoint.id
            dict['TagLab Type'].append('Points')
            dict['TagLab Date'].append(date)
            dict['TagLab Class name'].append(annpoint.class_name)
            dict['TagLab Centroid x'][j] = round(annpoint.coordx, 1)
            dict['TagLab Centroid y'][j] = round(annpoint.coordy, 1)
            dict['TagLab Area'][j] = int(0)
            dict['TagLab Surf. area'][j] = int(0)
            dict['TagLab Perimeter'][j] = int(0)
            dict['TagLab Genet Id'][j] = int(0)
            dict['TagLab Note'].append(annpoint.note)

            for attribute in project.region_attributes.data:

                key = attribute["name"]

                try:
                    value = annpoint.data[key]
                except:
                    value = None

                if attribute['type'] == 'integer number':

                    if value is not None:
                        dict[key][j] = value
                    else:
                        dict[key][j] = 0

                elif attribute['type'] == 'decimal number':

                    if value is not None:
                        dict[key][j] = value
                    else:
                        dict[key][j] = np.NaN

                else:
                    if value is not None:
                        dict[key].append(value)
                    else:
                        dict[key].append('')

            j = j+1

        # create dataframe
        df = pd.DataFrame(dict, columns=list(dict.keys()))
        df.to_csv(filename, sep=',', index=False)

    def export_annotation_points_inside_an_area(self, plot_number, filename, bbox):

        top = bbox[0]
        left = bbox[1]
        bottom = top + bbox[3]
        right = left + bbox[2]

        x_coords = []
        y_coords = []
        labels = []
        for point in self.annpoints:
            x = point.coordx
            y = point.coordy
            if x >= left and x < right and y >= top and y < bottom:
                x_coords.append(x)
                y_coords.append(y)
                labels.append(point.class_name)

        number_of_points = len(labels)
        dict = {
            "Plot number": np.zeros(number_of_points, dtype=np.int64),
            "Name": [],
            "Row": np.zeros(number_of_points, dtype=np.int64),
            "Column": np.zeros(number_of_points, dtype=np.int64),
            "Label": []
        }

        # fill the table
        image_name = os.path.basename(filename)
        for i in range(number_of_points):
            dict["Plot number"][i] = plot_number
            dict["Name"].append(image_name)
            dict["Row"][i] = y_coords[i] - top
            dict["Column"][i] = x_coords[i] - left
            dict["Label"].append(labels[i])

        # create dataframe
        df = pd.DataFrame(dict, columns=list(dict.keys()))

        return df

    def export_image_data_for_Scripps(self, size, filename, project):
        label_map = self.create_label_map(size, labels_dictionary=project.labels, working_area=project.working_area)
        label_map.save(filename, 'png')

    def computeBBoxWithAffineTransform(self, rot, tra) -> QRectF:
        """
        Compute the bbox that contains the blob list, after applying an affine
        transformation to each blob
        :param: rot the rotation component (2x2 matrix)
        :param: tra the transaltion component (2d vector)
        :returns: a QRectF that identifies the bbox
        """
        # Get transformed internal blobs
        blobs = self.computeBlobsAffineTransform(rot, tra)
        # Min-Max bboxes of blobs
        minX, minY = 1_000_000_000, 1_000_000_000
        maxX, maxY = 0, 0
        for blob in blobs:
            minY = min(minY, blob.bbox[0])
            minX = min(minX, blob.bbox[1])
            maxY = max(maxY, blob.bbox[0] + blob.bbox[3])
            maxX = max(maxX, blob.bbox[1] + blob.bbox[2])
        # Return BBox as rect
        return QRectF(minX, minY, (maxX - minX), (maxY - minY))

    def computeBlobsAffineTransform(self, rot, tra):
        """
        Transform the seg_blobs list
        :param: rot the rotation matrix (2x2)
        :param: tra the translation vector (2D)
        :returns: a transformed list of blobs (copied)
        """
        # Update Blobs
        transformedBlobs = []
        for blob in self.seg_blobs:
            tmpBlob = blob.copy()
            # Contour
            tmpBlob.contour = np.array([rot @ p + tra for p in tmpBlob.contour])
            # Inner contours
            for (i, contour) in enumerate(tmpBlob.inner_contours):
                tmpBlob.inner_contours[i] = np.array([rot @ p + tra for p in contour])
            # Centroid
            tmpBlob.centroid = rot @ tmpBlob.centroid + tra
            # BBox
            tmpBlob.bbox = self.__transformBBox(tmpBlob.bbox, rot, tra)
            # Update internally
            tmpBlob.setupForDrawing()
            # Add blob
            transformedBlobs.append(tmpBlob)
        # Result
        return transformedBlobs

    def __transformBBox(self, bbox, rot, tra):
        """
        Apply an affine transformation to a bbox [top, left, width, height]
        :param: bbox the bounding box to transform
        :param: rot the rotation as matrix (2x2)
        :param: tra the translation as 2d vector
        :returns: the transformed bbox as [top, left, width, height]
        """
        # Construct points
        t, l, w, h = bbox[0], bbox[1], bbox[2], bbox[3]
        points = np.array([[l, t], [l, t + h], [l + w, t + h], [l + w, t]])
        # Transform points
        points = [rot @ p + tra for p in points]
        # Extract components
        pointsX = [p[0] for p in points]
        pointsY = [p[1] for p in points]
        # Compute bbox
        top = min(pointsY)
        left = min(pointsX)
        height = max(pointsY) - top
        width = max(pointsX) - left
        # Result
        return np.array([int(top), int(left), int(width) + 1, int(height) + 1])


    # from here, everything is about annotation point not Blob (a.k.a annotation regions) anymore

    # ------------------
    # Point Annotations
    # ------------------

    # def setPointClass(self, annpoint, class_name):
    #     """
    #
    #     """
    #     if annpoint.class_name == class_name:
    #         return
    #     else:
    #         old_class_name = annpoint.class_name
    #         annpoint.class_name = class_name
    #         # notify that the class name of 'point' has changed
    #         self.pointClassChanged.emit(old_class_name, annpoint)
    #
    #     self.table_needs_update = True

    def importCoralNetCSVAnn(self, file_name, labels, active_image):
        """
        Opens a CoralNet format CSV file, expecting at a minimum: Name, Row, Column, Label.
        Additional fields include the Machine confidence N (float), and Machine Suggestion N (str).
        If the CSV file contains TagLab exported Tiles, it will modify the coordinates accordingly.
        """

        imported_points = list()

        label_id = len(labels) + 1

        channel = active_image.getRGBChannel()
        # Get the image basename
        _, image_name = os.path.split(channel.filename)
        basename = os.path.basename(image_name).split(".")[0]

        # Get the dimensions
        width = channel.qimage.width()
        height = channel.qimage.height()

        # Read in the csv file
        points = pd.read_csv(file_name, sep=",", header=0)
        points = points.loc[:, ~points.columns.str.contains('^Unnamed')]

        # Check to see if the csv file has the expected columns
        assert 'Name' in points.columns, "'Name' not in file!"
        assert 'Row' in points.columns, "'Row' not in file!"
        assert 'Column' in points.columns, "'Column' not in file!"

        # Subset to get just the basename points
        points = points[points['Name'].str.contains(basename)]
        assert len(points) > 0, f"No point annotations found for '{image_name}'!"

        # Pattern for finding tiles (if imported from CoralNet Toolbox)
        pattern = r'_tile(\d{4})_offx=(\d{5})_offy=(\d{5})\.(png|jpg)'

        # Loop through the dataframe
        for i, r in points.iterrows():

            pidx = None
            note = ""
            point_data = {}
            coralnet_data = {}

            # Includes these columns, not just the machine predictions.
            # All information will be available to user, but needs to
            # be shown to them via UI, it's just stored in the point.
            # Also, apparently point.data doesn't persist between sessions...
            for key in r.keys():
                if "Machine" in key:
                    coralnet_data[key] = r[key]
                elif key in ['Name', 'Id', 'Class Name', 'Row', 'Column', 'Label', 'Note', 'TagLab_PID']:
                    point_data[key] = r[key]

            # Modify values as needed
            name = str(point_data['Name'])
            coordx = int(point_data['Column'])
            coordy = int(point_data['Row'])

            if 'Label' in point_data:
                label = point_data['Label']
            else:
                label = 'Empty'

            if 'Note' in point_data:
                note = point_data['Note']
                note = note if type(note) == str else ""

            # This point was in TagLab previously
            if "TagLab_PID" in point_data:
                # Search for the offset
                pidx = point_data['TagLab_PID']
                match = re.search(pattern, name)

                if match:
                    # Get the tile coordinates
                    offx = int(match.group(2))
                    offy = int(match.group(3))
                    # Adjust to ortho coordinates
                    coordx += offx
                    coordy += offy

            # If the coordinates don't fall within the image, don't add
            if coordx < 0 or coordx > width or coordy < 0 or coordy > height:
                continue

            point_data['Name'] = image_name
            point_data['Column'] = coordx
            point_data['Row'] = coordy
            point_data['Note'] = note
            point_data['Label'] = point_data['Class'] = label

            # Look for an existing point
            if pidx in [a.id for a in self.annpoints]:
                idx = [a.id for a in self.annpoints].index(pidx)
                point_ann = self.annpoints[idx]
                # If the label name changed, update it
                point_ann.class_name = label
                point_ann.data.update(point_data)
                point_ann.data.update(coralnet_data)
                self.annpoints[idx] = point_ann
            else:
                # Create a new point, don't add any additional information
                point_ann = Point(coordx, coordy, label, self.getFreePointId())
                # Make sure not to carry over incorrect data to a new point
                point_data['Id'] = point_data['TagLab_ID'] = point_ann.id
                # Update new point with correct data
                point_ann.data.update(point_data)
                point_ann.data.update(coralnet_data)
                imported_points.append(point_ann)

                # update dictionary
                label_info = labels.get(label)
                if label_info is None:
                    labels[label] = Label(label_id, name=label)
                    label_id = label_id + 1

        return imported_points

    def exportCoralNetCSVAnn(self, output_dir, channel, annotations, working_area):
        """
        The function exports a CoralNet formatted CSV file (Name, Row, Column, Label) for all points
        in user specified work area. No tiles are made, and point locations are based on the current map
        coordinates. See exportCoralNetData for tile handling.
        """
        # Get the image basename
        _, image_name = os.path.split(channel.filename)
        basename = os.path.basename(image_name).split('.')[0]

        # Output CSV file
        csv_file = f"{output_dir}/{basename}_exported_points.csv"

        # Selected working area
        if working_area:
            top = working_area[0]
            left = working_area[1]
            right = left + working_area[2]
            bottom = top + working_area[3]
        else:
            top = 0
            left = 0
            bottom = channel.qimage.height()
            right = channel.qimage.width()

        # Loop through point annotations, find those inside the box
        points = []

        for point in annotations.annpoints:

            point_dict = point.toDict()
            x = point_dict['X']
            y = point_dict['Y']

            # If inside the box, add to subset
            if left <= x <= right and top <= y <= bottom:
                # Add the additional attributes
                point_dict['Label'] = point.class_name
                point_dict['Row'] = y
                point_dict['Column'] = x
                # Overwrite old data with new data
                point_data = point.data.copy()
                point_data.update(point_dict)
                point_data['Name'] = os.path.basename(image_name)
                point_data['TagLab_PID'] = point_data['Id']
                # Add to list of points to export
                points.append(point_data)

        if points:
            points = pd.DataFrame(points)
            points.to_csv(csv_file)
        else:
            raise Exception("No points found in sampling area.")

        return csv_file

    def exportCoralNetData(self, output_dir, channel, annotations, working_area, tile_size=2048, max_size=8000):
        """
        The function exports a CoralNet formatted CSV file (Name, Row, Column, Label) for all points
        in the user-specified work area. Tiles are made, and point locations are based on the tile
        coordinates. See exportCoralNetCSVAnn for non-tiled points.
        """

        # Get the image basename
        _, image_name = os.path.split(channel.filename)
        basename = os.path.basename(image_name).split('.')[0]
        img_width, img_height = channel.qimage.width(), channel.qimage.height()

        # Create the output directory to be based on ortho name
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join(output_dir, now)
        tiles_dir = os.path.join(output_dir, "tiles")
        os.makedirs(tiles_dir, exist_ok=True)

        # Output CSV file
        csv_file = os.path.join(output_dir, "exported_points.csv")

        # Selected working area
        if working_area:
            top, left, width, height = working_area
            bottom = top + height
            right = left + width
        else:
            top, left, width, height = 0, 0, img_width, img_height
            bottom = top + height
            right = left + width

        # Ensure that working area is within image
        top = 0 if top < 0 else top
        left = 0 if left < 0 else left
        bottom = bottom if bottom < img_height else img_height
        right = right if right < img_width else img_width

        # Update width and height
        width = right - left
        height = bottom - top

        # To hold all the tiled point annotations
        points = []

        # If it's an area smaller than max_size, no need to tile
        if width < max_size and height < max_size:

            # Working area
            xoff, yoff = left, top
            bbox = [top, left, width, height]

            # Cropping the tile from original ortho
            img_tile = genutils.cropQImage(channel.qimage, bbox)

            # Naming convention
            plot_idx = 0
            tile_name = f"{basename}_tile{plot_idx:04d}_offx={xoff:05d}_offy={yoff:05d}.jpg"
            tile_path = os.path.join(tiles_dir, tile_name)

            # Find all point annotations within the tile bounding box
            ann_points_in_box = annotations.getAnnPointsWithinBox(tile_name, bbox, xoff, yoff)

            # If there are point annotations, save the image and add to the dataframe
            if ann_points_in_box:
                img_tile.save(tile_path)
                points = ann_points_in_box

        else:
            # The area is too big, so tile
            w_step = int(width / tile_size)
            h_step = int(height / tile_size)

            w_size = int(width / w_step) + 1
            h_size = int(height / h_step) + 1

            # Loop through the tiles
            for j in range(h_step):
                for i in range(w_step):
                    # Calculate the offset and box for the tile
                    xoff = left + w_size * i
                    yoff = top + h_size * j
                    bbox = [yoff, xoff, w_size, h_size]

                    # Cropping the tile from original ortho
                    img_tile = genutils.cropQImage(channel.qimage, bbox)

                    # Naming convention
                    plot_idx = i + j * w_step
                    tile_name = f"{basename}_tile{plot_idx:04d}_offx={xoff:05d}_offy={yoff:05d}.jpg"
                    tile_path = os.path.join(tiles_dir, tile_name)

                    # Find all point annotations within the tile bounding box
                    ann_points_in_box = annotations.getAnnPointsWithinBox(tile_name, bbox, xoff, yoff)

                    # If there are point annotations, save the tile and extend the points list
                    if ann_points_in_box:
                        img_tile.save(tile_path)
                        points.extend(ann_points_in_box)

        if points:
            points = pd.DataFrame(points)
            points.to_csv(csv_file)
        else:
            raise Exception("No points found in the specified working area.")

        return output_dir, csv_file

    def getAnnPointsWithinBox(self, tile_name, box, xoff, yoff):
        """
        Simple function to get the point annotations within a work area for CoralNet.
        """
        # Get the dimensions of the box
        top = box[0]
        left = box[1]
        bottom = top + box[3]
        right = left + box[2]

        # Loop through point annotations, find those inside the box
        ann_points_in_box = []

        for point in self.annpoints:

            # Get all the information from point
            point_dict = point.toDict()
            x = point_dict['X']
            y = point_dict['Y']

            # If inside the box, add to subset
            if left <= x <= right and top <= y <= bottom:
                # Add the additional attributes
                point_dict['Name'] = tile_name
                point_dict['Label'] = point.class_name
                # Tile space coordinates
                point_dict['Row'] = y - yoff
                point_dict['Column'] = x - xoff
                # Overwrite old data with new data
                point_data = point.data.copy()
                point_data.update(point_dict)
                point_data['TagLab_PID'] = point_data['Id']

                # Add dict to list
                ann_points_in_box.append(point_data)

        return ann_points_in_box