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

from pycocotools import mask as maskcoco
import cv2
import os
import math
import numpy as np
from PyQt5.QtGui import QPainter, QImage, QPen, QBrush, QColor, qRgb, qRed, qGreen, qBlue
from PyQt5.QtCore import Qt
import random as rnd
from source import Image
from source import utils
from skimage.filters import gaussian
from skimage.segmentation import find_boundaries
from skimage import measure
import glob
import sys
import json
from cv2 import fillPoly
import datetime
from skimage.measure import label, regionprops
from source import Mask


class NewDataset(object):
	"""
	This class handles the functionalities to create a new dataset.
	"""

	def __init__(self, ortho_image, labels, image_info, tile_size, step, flag_coco):

		self.ortho_image = ortho_image  # QImage
		self.blobs = image_info.annotations.seg_blobs
		self.tile_size = tile_size
		self.step = step
		self.labels_dict = labels
		self.image_info = image_info

		# stored as (top, left, width, height)
		self.val_area = [0, 0, 0, 0]
		self.test_area = [0, 0, 0, 0]
		# the training area is given by the entire map minus the validation and the test area

		# stored as a list of (x,y) coordinates
		self.training_tiles = []
		self.validation_tiles = []
		self.test_tiles = []

		self.label_image = None
		self.labels = None
		self.flag_coco = flag_coco

		self.crop_size = 513
		#self.idmap = None
		self.id_image = None

		self.frequencies = None

		self.radius_map = None

		# normalization factors
		self.sn_min = 0.0
		self.sn_max = 0.0
		self.sc_min = 0.0
		self.sc_max = 0.0
		self.sP_min = 0.0
		self.sP_max = 0.0


	def workingAreaCropAndRescale(self, current_pixel_size, target_pixel_size, working_area):

		x = working_area[1]
		y = working_area[0]
		width = working_area[2]
		height = working_area[3]

		crop_ortho_image = self.ortho_image.copy(x, y, width, height)
		crop_label_image = self.label_image.copy(x, y, width, height)
		#crop_id_image = np.copy(self.idmap)
		#crop_id_image= crop_id_image[y: y+height, x: x+width]

		scale = float(current_pixel_size / target_pixel_size)
		w = int(crop_ortho_image.width() * scale)
		h = int(crop_ortho_image.height() * scale)

		if w >= 32767 or h >= 32767:
			self.ortho_image = None
			self.label_image = None
			self.id_image = None
			return False
		else:
			self.ortho_image = crop_ortho_image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
			self.label_image = crop_label_image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.FastTransformation)
			#self.idmap = cv2.resize(crop_id_image, dsize=(h, w), interpolation=cv2.INTER_NEAREST) this is for a numpy
			if self.flag_coco:
				self.crop_id_image = self.id_image.copy(x, y, width, height)
				self.id_image = self.crop_id_image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.FastTransformation)

			return True


	def isFullyInsideBBox(self, bbox1, bbox2):
		"""
		Check if bbox1 is inside bbox2.
		The bounding boxes are stored as [top, left, width, height].
		"""

		top1 = bbox1[0]
		left1 = bbox1[1]
		w1 = bbox1[2]
		h1 = bbox1[3]

		top2 = bbox2[0]
		left2 = bbox2[1]
		w2 = bbox2[2]
		h2 = bbox2[3]

		inside = False
		if top1 >= top2 and left1 >= left2 and top1 + h1 < top2 + h2 and left1 + w1 < left2 + w2:
			inside = True

		return inside


	def bbox_intersection(self, bbox1, bbox2):
		"""
		Calculate the Intersection of two bounding boxes.

		bbox1 and bbox2 are stored as (top, left, width, height)
		"""

		# determine the coordinates of the intersection rectangle
		# bb1 and bb2 wants the format (x1, y1, x2, y2) where (x1, y1) position is at the top left corner,
		#  (x2, y2) position is at the bottom right corner

		bb1 = [0, 0, 0, 0]
		bb2 = [0, 0, 0, 0]

		bb1[0] = bbox1[1]
		bb1[1] = bbox1[0]
		bb1[2] = bbox1[1] + bbox1[2]
		bb1[3] = bbox1[0] + bbox1[3]

		bb2[0] = bbox2[1]
		bb2[1] = bbox2[0]
		bb2[2] = bbox2[1] + bbox2[2]
		bb2[3] = bbox2[0] + bbox2[3]

		x_left = max(bb1[0], bb2[0])
		y_top = max(bb1[1], bb2[1])
		x_right = min(bb1[2], bb2[2])
		y_bottom = min(bb1[3], bb2[3])

		if x_right < x_left or y_bottom < y_top:
			return 0.0

		intersection_area = (x_right - x_left) * (y_bottom - y_top)

		return intersection_area


	def checkBlobInside(self, area, blob, threshold):
		"""
		Given an area and a blob this function returns True if the blob is inside the given area
		(according to a given threshold), False otherwise.
		The area is stored as (top, left, width, height).
		"""

		intersection = self.bbox_intersection(area, blob.bbox)
		perc_inside = intersection / (blob.bbox[2] * blob.bbox[3])
		if perc_inside > threshold:
			return True
		else:
			return False


	def computeFrequencies(self, target_classes):
		"""
		Compute the frequencies of the target classes on the entire map.
		"""

		map_w = self.ortho_image.width()
		map_h = self.ortho_image.height()
		area_map = map_w * map_h

		frequencies = {}
		for key in target_classes.keys():

			area = 0.0
			if key != "Background":
				for blob in self.blobs:
					if blob.class_name == key:
						area += blob.area

			freq = area / area_map
			frequencies[key] = freq

		self.frequencies = frequencies


	def computeExactCoverage(self, area, target_classes):
		"""
		Compute the coverage of the target classes inside the given area.
		The area is stored as (top, left, width, height).
		"""

		top = area[0]
		left = area[1]
		right = left + area[2]
		bottom = top + area[3]
		labelsint = self.labels[top:bottom, left:right].copy()

		A = float(area[2] * area[3])

		# background is skipped
		coverage_per_class = {}
		for key in target_classes.keys():
			if key != "Background":
				label_code = target_classes[key]
				coverage = float(np.count_nonzero(labelsint == label_code)) / A
				coverage_per_class[key] = coverage

		return coverage_per_class


	# FIXME: This function is no more valid and it must be reimplemented
	def computeRadii(self, target_classes):

		class_sample_info = []
		for i, freq in enumerate(self.frequencies):
			if freq > 0.0005:
				K = max(self.frequencies) / freq
				#K = 0.25 / freq
				K = math.pow(K, 1.3)
				if K < 1.5:
					radius = 256.0
				else:
					radius = 256.0 / math.sqrt(K * 1.5)

				if radius < 20.0:
					radius = 20.0
			else:
				radius = 0.0

			class_sample_info.append((target_classes[i], radius))

		class_sample_info.sort(key=lambda x: x[1])

		class_to_sample = []
		radii = []
		for info in class_sample_info:
			if info[1] > 5.0:
				class_to_sample.append(info[0])
				radii.append(info[1])

		return class_to_sample, radii


	def calculateMetrics(self, area, target_classes):
		"""
		Given an area it calculates the spatial/ecological metrics.
		The area is stored as (top, left, width, height).
		"""

		number = []
		PSCV = []

		# a coral is counted if and only if it is inside the given area for 3/4
		for key in enumerate(target_classes.keys()):

			if key != "Background":

				areas = []
				if self.frequencies[key] > 0.0:
					for blob in self.blobs:
						if blob.class_name == key and self.checkBlobInside(area, blob, 3.0/4.0):
							areas.append(blob.area)

				# number of entities
				number.append(len(areas))

				if len(areas) > 0:
					# Patch Size Coefficient of Variation (PSCV)
					mean_areas = np.mean(areas)
					std_areas = np.std(areas)
					PSCV.append((100.0 * std_areas) / mean_areas)
				else:
					PSCV.append(0.0)

		# coverage evaluation
		coverage = self.computeExactCoverage(area, target_classes)

		return number, coverage, PSCV


	def rangeScore(self, area_number, area_coverage, area_PSCV, landscape_number, landscape_coverage, landscape_PSCV):

		s1 = []
		s2 = []
		s3 = []
		for i in range(len(area_number)):

			score = 0.0
			if landscape_number[i] > 0:

				s1.append(abs((area_number[i] / landscape_number[i]) * 100.0 - 15.0))
				s2.append(abs((area_coverage[i] - landscape_coverage[i]) * 100.0))
				s3.append(abs(area_PSCV[i] - landscape_PSCV[i]))

			else:

				s1.append(0.0)
				s2.append(0.0)
				s3.append(0.0)

		return s1, s2, s3


	def calculateScore(self, area_number, area_coverage, area_PSCV, landscape_number, landscape_coverage, landscape_PSCV):
		"""
		The score is the distance (in percentage) w.r.t the landscape metrics used.
		"""

		scores = []
		for i in range(len(area_number)):

			score = 0.0
			if landscape_number[i] > 0:

				s1 = abs((area_number[i] / landscape_number[i]) * 100.0 - 15.0)
				s2 = abs((area_coverage[i] - landscape_coverage[i]) * 100.0)
				s3 = abs(area_PSCV[i] - landscape_PSCV[i])

				score = s1 + s2 + s3

			scores.append(score)

		return scores


	def calculateNormalizedScore(self, area_number, area_coverage, area_PSCV, landscape_number, landscape_coverage, landscape_PSCV):
		"""
		The score is the distance (in percentage) w.r.t the landscape metrics used.
		"""

		scores = []
		for i in range(len(area_number)):

			score = 0.0
			if landscape_number[i] > 0:

				s1 = abs((area_number[i] / landscape_number[i]) * 100.0 - 15.0)
				s2 = abs((area_coverage[i] - landscape_coverage[i]) * 100.0)
				s3 = abs(area_PSCV[i] - landscape_PSCV[i])

				sn = (s1 - self.sn_min[i]) / (self.sn_max[i] - self.sn_min[i])
				sc = (s2 - self.sc_min[i]) / (self.sc_max[i] - self.sc_min[i])
				sP = (s3 - self.sP_min[i]) / (self.sP_max[i] - self.sP_min[i])

				score = (sn + sc + sP) / 3.0

			scores.append(score)

		return scores


	def findAreas(self, target_classes):
		"""
		Find the validation and test areas with landscape metrics similar to the ones of the entire map.
		"""

		area_info = []

		map_w = self.ortho_image.width()
		map_h = self.ortho_image.height()

		area_w = int(math.sqrt(0.15) * map_w)
		area_h = int(math.sqrt(0.15) * map_h)

		landscape_number, landscape_coverage, landscape_PSCV = self.calculateMetrics([0, 0, map_w, map_h], target_classes)

		# calculate normalization factor
		numbers = []
		coverages = []
		PSCVs = []
		sn = []
		sc = []
		sP = []
		for i in range(5000):

			aspect_ratio_factor = factor = rnd.uniform(0.4, 2.5)
			w = int(area_w / aspect_ratio_factor)
			h = int(area_h * aspect_ratio_factor)
			px = rnd.randint(0, map_w - w - 1)
			py = rnd.randint(0, map_h - h - 1)

			area_bbox = [py, px, w, h]
			area_number, area_coverage, area_PSCV = self.calculateMetrics(area_bbox, target_classes)
			s1, s2, s3 = self.rangeScore(area_number, area_coverage, area_PSCV, landscape_number, landscape_coverage, landscape_PSCV)

			numbers.append(area_number)
			coverages.append(area_coverage)
			PSCVs.append(area_PSCV)

			sn.append(s1)
			sc.append(s2)
			sP.append(s3)

			if i % 50 == 0:
				sys.stdout.write("\rFinding biologically representative areas (pass 1/2)... %.2f %%" % ((i * 100.0) / 5000.0))

		sn = np.array(sn)
		sc = np.array(sc)
		sP = np.array(sP)
		self.sn_min = np.min(sn, axis=0)
		self.sn_max = np.max(sn, axis=0)
		self.sc_min = np.min(sc, axis=0)
		self.sc_max = np.max(sc, axis=0)
		self.sP_min = np.min(sP, axis=0)
		self.sP_max = np.max(sP, axis=0)

		for i in range(10000):

			aspect_ratio_factor = factor = rnd.uniform(0.4, 2.5)
			w = int(area_w / aspect_ratio_factor)
			h = int(area_h * aspect_ratio_factor)

			px = rnd.randint(0, map_w - w - 1)
			py = rnd.randint(0, map_h - h - 1)

			area_bbox = [py, px, w, h]

			area_number, area_coverage, area_PSCV = self.calculateMetrics(area_bbox, target_classes)
			scores = self.calculateNormalizedScore(area_number, area_coverage, area_PSCV, landscape_number, landscape_coverage, landscape_PSCV)

			for jj, score in enumerate(scores):
				if math.isnan(score):
					scores[jj] = 0.0

			aggregated_score = sum(scores) / len(scores)

			area_info.append((area_bbox, scores, aggregated_score))

			if i % 50 == 0:
				sys.stdout.write("\rFinding biologically representative areas (pass 2/2)... %.2f %%" % ((i * 100.0) / 10000.0))


		area_info.sort(key=lambda x:x[2])
		val_area = area_info[0][0]

		print("*** VALIDATION AREA ***")
		area_number, area_coverage, area_PSCV = self.calculateMetrics(val_area, target_classes)
		scoresNorm = self.calculateNormalizedScore(area_number, area_coverage, area_PSCV, landscape_number,
											   landscape_coverage, landscape_PSCV)
		lc = [value * 100.0 for value in landscape_coverage]
		ac = [value * 100.0 for value in area_coverage]

		for i, score in enumerate(scoresNorm):
			if math.isnan(score):
				scoresNorm[i] = 0.0
		print(scoresNorm)
		print("Normalized score:", sum(scoresNorm) / len(scoresNorm))
		print("Number of corals per class (landscape):", landscape_number)
		print("Coverage of corals per class (landscape):", lc)
		print("PSCV per class (landscape): ", landscape_PSCV)
		print("Number of corals per class (selected area):", area_number)
		print("Coverage of corals per class (selected area):", ac)
		print("PSCV of corals per class (selected area):", area_PSCV)

		for i in range(len(area_info)):
			intersection = self.bbox_intersection(val_area, area_info[i][0])
			if intersection < 10.0:
				test_area = area_info[i][0]
				break

		print("*** TEST AREA ***")
		area_number, area_coverage, area_PSCV = self.calculateMetrics(test_area, target_classes)
		scoresNorm = self.calculateNormalizedScore(area_number, area_coverage, area_PSCV, landscape_number,
											   landscape_coverage, landscape_PSCV)
		lc = [value * 100.0 for value in landscape_coverage]
		ac = [value * 100.0 for value in area_coverage]

		for i, score in enumerate(scoresNorm):
			if math.isnan(score):
				scoresNorm[i] = 0.0
		print(scoresNorm)
		print("Normalized score:", sum(scoresNorm) / len(scoresNorm))
		print("Number of corals per class (landscape):", landscape_number)
		print("Coverage of corals per class (landscape):", lc)
		print("PSCV per class (landscape): ", landscape_PSCV)
		print("Number of corals per class (selected area):", area_number)
		print("Coverage of corals per class (selected area):", ac)
		print("PSCV of corals per class (selected area):", area_PSCV)

		return val_area, test_area


	def createLabelImage(self, labels_dictionary):
		"""
		Creates a large labeled image of the entire annotated area using class-colored blobs
		"""

		# create a black canvas of the same size of your map
		w = self.ortho_image.width()
		h = self.ortho_image.height()

		labelimg = QImage(w, h, QImage.Format_RGB32)
		labelimg.fill(qRgb(0, 0, 0))

		painter = QPainter(labelimg)

		# CREATE LABEL IMAGE
		for i, blob in enumerate(self.blobs):

			if blob.qpath_gitem.isVisible():

				if blob.class_name == "Empty":
					rgb = qRgb(0, 0, 0)
				else:
					class_color = labels_dictionary[blob.class_name].fill
					rgb = qRgb(class_color[0], class_color[1], class_color[2])

				painter.setBrush(QBrush(QColor(rgb)))
				painter.drawPath(blob.qpath_gitem.path())

		painter.end()
		self.label_image = labelimg

		if self.flag_coco:
			self.id_image = np.zeros((h, w), dtype=int)

			for i, blob in enumerate(self.blobs):

				if blob.qpath_gitem.isVisible():
					if blob.class_name != "Empty":
						points = blob.contour.round().astype(int)
						fillPoly(self.id_image, pts=[points], color = blob.id)
						for inner_contour in blob.inner_contours:
							points = inner_contour.round().astype(int)
							fillPoly(self.id_image, pts=[points], color=0)

			self.id_image = utils.floatmapToQImage(self.id_image)

	def convertColorsToLabels(self, target_classes, labels_colors):
		"""
		Convert the label image to a numpy array with the labels' values.
		NOTE: target_classes is a dictionary. The key is the label name which maps to the label code.
		"""

		label_w = self.label_image.width()
		label_h = self.label_image.height()

		imglbl = utils.qimageToNumpyArray(self.label_image)

		# classes with unknown color (color not present in the given dictionary) are assigned to white
		self.labels = np.zeros((label_h, label_w), dtype='int64')
		for key in target_classes.keys():
			label = labels_colors.get(key)
			label_code = target_classes[key]

			if label is None:
				class_colors = [255, 255, 255]
			else:
				class_colors = label.fill

			idx = np.where((imglbl[:, :, 0] == class_colors[0]) & (imglbl[:, :, 1] == class_colors[1]) & (imglbl[:, :, 2] == class_colors[2]))
			self.labels[idx] = label_code


	def setupAreas(self, mode, target_classes=None):
		"""
		mode:

			"UNIFORM (VERTICAL)    : the map is subdivided vertically (70 / 15 / 15)
			"UNIFORM (HORIZONTAL)  : the map is subdivided horizontally (70 / 15 / 15)
			"RANDOM"               : the map is subdivided randomly into three non-overlapping part
			"BIOLOGICALLY-INSPIRED": the map is subdivided according to the spatial distribution of the classes
		"""

		# size of the each area is 15% of the entire map
		map_w = self.ortho_image.width()
		map_h = self.ortho_image.height()

		val_area = [0, 0, 0, 0]
		test_area = [0, 0, 0, 0]
		# the train area is represented by the entire map minus the validation and test areas

		if mode == "UNIFORM (VERTICAL)":

			delta = int(self.crop_size / 2)
			ww_val = map_w - delta*2
			hh_val = (map_h - delta*2) * 0.15 - delta
			ww_test = ww_val
			hh_test = (map_h - delta*2) * 0.15 - delta
			val_area = [delta + (map_h - delta * 2) * 0.7, delta, ww_val, hh_val]
			test_area = [2*delta + (map_h - delta*2) * 0.85, delta, ww_test, hh_test]

		elif mode == "UNIFORM (HORIZONTAL)":

			delta = int(self.crop_size / 2)
			ww_val = (map_w - delta*2) * 0.15 - delta
			hh_val = map_h - delta*2
			ww_test = (map_w - delta*2) * 0.15 - delta
			hh_test = hh_val
			val_area = [delta, delta + (map_w - delta*2) * 0.7, ww_val, hh_val]
			test_area = [delta, 2* delta + (map_w - delta*2) * 0.85, ww_test, hh_test]

		elif mode == "RANDOM":

			ncrops_w = int((float)(map_w - self.crop_size*2) / float(self.crop_size))
			ncrops_h = int((float)(map_h - self.crop_size*2) / float(self.crop_size))
			ncrops_ref = round(ncrops_w * ncrops_h * 0.12)

			valid_comb = []
			for j in range(1, ncrops_w):
				for k in range(1, ncrops_h):
					if j * k == ncrops_ref:
						valid_comb.append([j,k])

			delta = int(self.crop_size/2)
			min_intersection = map_w * map_h
			# initialize the random number generator using the system time
			rnd.seed()
			for j in range(30000):

				comb = valid_comb[rnd.randint(0, len(valid_comb)-1)]
				area_w1 = int(comb[0] * self.crop_size)
				area_h1 = int(comb[1] * self.crop_size)
				px1 = rnd.randint(delta, map_w - delta - area_w1 - 1)
				py1 = rnd.randint(delta, map_h - delta - area_h1 - 1)

				comb = valid_comb[rnd.randint(0, len(valid_comb)-1)]
				area_w2 = int(comb[0] * self.crop_size)
				area_h2 = int(comb[1] * self.crop_size)
				px2 = rnd.randint(delta, map_w - delta - area_w2 - 1)
				py2 = rnd.randint(delta, map_h - delta - area_h2 - 1)

				area1 = [py1, px1, area_w1, area_h1]
				area2 = [py2, px2, area_w2, area_h2]

				intersection = self.bbox_intersection(area1, area2)

				if intersection < min_intersection:
					val_area = area1
					test_area = area2
					min_intersection = intersection

		elif mode == "BIOLOGICALLY-INSPIRED":

			val_area, test_area = self.findAreas(target_classes=target_classes)

			print(val_area)
			print(test_area)

		self.val_area = val_area
		self.test_area = test_area


	def sampleAreaUniformly(self, area, tile_size, step):
		"""
		Sample the given area uniformly according to the tile_size and the step size.
		The tiles are fully inside the given area. The area is stored as (top, left, width, height).
		The functions returns a list of (x,y) coordinates.
		"""
		samples = []

		area_W = area[2]
		area_H = area[3]

		tile_cols = 1 + int(area_W / step)
		tile_rows = 1 + int(area_H / step)

		deltaW = (area_W - tile_cols * step) / 2.0
		deltaH = (area_H - tile_rows * step) / 2.0
		deltaW = int(deltaW)
		deltaH = int(deltaH)

		area_top = area[0] + deltaH - int((tile_size - self.crop_size) / 2)
		area_left = area[1] + deltaW - int((tile_size - self.crop_size) / 2)

		for row in range(tile_rows):
			for col in range(tile_cols):
				top = area_top + row * step
				left = area_left + col * step

				cy = top + tile_size / 2
				cx = left + tile_size / 2

				samples.append((cx, cy))

		return samples


	def cleanTrainingTiles(self, training_tiles):
		"""
		If a training tile intersect a validation or a test tile it is removed.
		"""

		cleaned_tiles = []
		bbox1 = [0, 0, 0, 0]
		bbox2 = [0, 0, 0, 0]
		size = self.crop_size + 4
		half_size = int(size / 2)

		for tile in training_tiles:

			bbox1[0] = tile[1] - half_size
			bbox1[1] = tile[0] - half_size
			bbox1[2] = half_size * 2
			bbox1[3] = half_size * 2

			flag = True
			for vtile in self.validation_tiles:

				bbox2[0] = vtile[1] - half_size
				bbox2[1] = vtile[0] - half_size
				bbox2[2] = half_size * 2
				bbox2[3] = half_size * 2

				area = self.bbox_intersection(bbox1, bbox2)
				area_perc = (100.0*area) / float(bbox1[2] * bbox1[3])
				if area_perc > 10.0:
					flag = False
					break

			if flag is True:
				for ttile in self.test_tiles:

					bbox2[0] = ttile[1] - half_size
					bbox2[1] = ttile[0] - half_size
					bbox2[2] = half_size * 2
					bbox2[3] = half_size * 2

					area = self.bbox_intersection(bbox1, bbox2)
					area_perc = (100.0 * area) / float(bbox1[2] * bbox1[3])
					if area_perc > 10.0:
						flag = False
						break

			if flag is True:
				cleaned_tiles.append(tile)

		return cleaned_tiles


	def cleaningValidationTiles(self, validation_tiles):
		"""
		It can be required by the oversampling.
		"""

		cleaned_tiles = []
		bbox1 = [0, 0, 0, 0]
		bbox2 = [0, 0, 0, 0]
		size = self.crop_size + 4
		half_size = size / 2

		for vtile in validation_tiles:

			bbox1[0] = vtile[1] - half_size
			bbox1[1] = vtile[0] - half_size
			bbox1[2] = half_size * 2
			bbox1[3] = half_size * 2

			flag = True
			for ttile in self.training_tiles:

				bbox2[0] = ttile[1] - half_size
				bbox2[1] = ttile[0] - half_size
				bbox2[2] = half_size * 2
				bbox2[3] = half_size * 2

				area = self.bbox_intersection(bbox1, bbox2)
				area_perc = (100.0*area) / float(bbox1[2] * bbox1[3])
				if area_perc > 10.0:
					flag = False

			if flag is True:
				for tile in self.test_tiles:

					bbox2[0] = tile[1] - half_size
					bbox2[1] = tile[0] - half_size
					bbox2[2] = half_size * 2
					bbox2[3] = half_size * 2

					area = self.bbox_intersection(bbox1, bbox2)
					area_perc = (100.0 * area) / float(bbox1[2] * bbox1[3])
					if area_perc > 10.0:
						flag = False

			if flag is True:
				cleaned_tiles.append(vtile)

		return cleaned_tiles


	# FIXME: This function is no more valid and it must be reimplemented
	def computeRadiusMap(self, radius_min, radius_max):

		h = self.labels.shape[0]
		w = self.labels.shape[1]

		radius = np.zeros(len(self.frequencies) + 1)
		radius[0] = sum(self.frequencies)
		for i in range(len(self.frequencies)):
			radius[i+1] = self.frequencies[i]

		f_min = np.min(radius, axis=0)
		f_max = np.max(radius, axis=0)

		radius = radius - f_min
		radius = radius / (f_max - f_min)
		radius = (radius * (radius_max - radius_min)) + radius_min

		self.radius_map = np.zeros((h, w), dtype='float')
		for i, r in enumerate(radius):
			self.radius_map[self.labels == i] = r

		self.radius_map = gaussian(self.radius_map, sigma=60.0, mode='reflect')


	def sampleBlobWimportanceSampling(self, blob, current_samples):

		offset_x = blob.bbox[1]
		offset_y = blob.bbox[0]
		w = blob.bbox[2]
		h = blob.bbox[3]

		# NOTE: MASK HAS HOLES (!) DO WE WANT TO SAMPLE INSIDE THEM ??
		mask = blob.getMask()

		for i in range(30):
			px = rnd.randint(1, w - 1)
			py = rnd.randint(1, h - 1)

			if mask[py, px] == 1:

				px = px + offset_x
				py = py + offset_y

				r1 = self.radius_map[py, px]

				flag = True
				for sample in current_samples:
					r2 = self.radius_map[sample[1], sample[0]]
					d = math.sqrt((sample[0] - px) * (sample[0] - px) + (sample[1] - py) * (sample[1] - py))
					if d < (r1 + r2) / 2.0:
						flag = False
						break

				if flag is True:
					current_samples.append((px, py))

		return current_samples


	def sampleSubAreaWImportanceSampling(self, area, current_samples):
		"""
		Sample the given area using the Poisson Disk sampling according to the given radius map.
		The area is stored as (top, left, width, height).
		"""

		top = area[0]
		left = area[1]
		w = area[2]
		h = area[3]

		for i in range(30):
			px = rnd.randint(left, left + w - 1)
			py = rnd.randint(top, top + h - 1)

			r1 = self.radius_map[py, px]

			flag = True
			for sample in current_samples:
				r2 = self.radius_map[sample[1], sample[0]]
				d = math.sqrt((sample[0] - px) * (sample[0] - px) + (sample[1] - py) * (sample[1] - py))
				if d < (r1+r2)/2.0:
					flag = False
					break

			if flag is True:
				current_samples.append((px, py))

		return current_samples


	def sampleBlobWPoissonDisk(self, blob, current_samples, r):

		map_w = self.ortho_image.width()
		map_h = self.ortho_image.height()

		offset_x = blob.bbox[1]
		offset_y = blob.bbox[0]
		w = blob.bbox[2]
		h = blob.bbox[3]

		# NOTE: MASK HAS HOLES (!) DO WE WANT TO SAMPLE INSIDE THEM ??
		mask = blob.getMask()

		for i in range(500):
			px = rnd.randint(1, w - 1)
			py = rnd.randint(1, h - 1)

			if mask[py, px] == 1:

				px = px + offset_x
				py = py + offset_y

				if px > self.crop_size and px < map_w - self.crop_size and py > self.crop_size and py < map_h - self.crop_size:

					flag = True
					for sample in current_samples:
						d = math.sqrt((sample[0] - px) * (sample[0] - px) + (sample[1] - py) * (sample[1] - py))
						if d < 2.0*r:
							flag = False
							break

					if flag is True:
						current_samples.append((px, py))

		return current_samples


	def sampleBackgroundWPoissonDisk(self, area, current_samples, r):

		offset_x = int(area[1])
		offset_y = int(area[0])
		w = int(area[2])
		h = int(area[3])

		for i in range(10000):
			px = rnd.randint(1, w - 1)
			py = rnd.randint(1, h - 1)

			if self.labels[py, px] == 0:

				px = px + offset_x
				py = py + offset_y

				flag = True
				for sample in current_samples:
					d = math.sqrt((sample[0] - px) * (sample[0] - px) + (sample[1] - py) * (sample[1] - py))
					if d < 2.0*r:
						flag = False
						break

				if flag is True:
					current_samples.append((px, py))

		return current_samples


	def oversamplingBlobsWPoissonDisk(self, area, classes_to_sample, radii):
		"""
		Sample the blobs of the map using Poisson Disk sampling with the given radii.
		Only the given classes are sampled.
		The functions returns a list of (x,y) coordinates.
		"""

		# minority classes are sampled before majority classes
		samples = []
		for i, class_name in enumerate(classes_to_sample):
			radius = radii[i]
			for blob in self.blobs:
				if blob.class_name == class_name:
					samples = self.sampleBlobWPoissonDisk(blob, samples, radius)
					txt = str(len(samples)) + "\r"
					sys.stdout.write(txt)

		samples = self.sampleBackgroundWPoissonDisk(area=area, current_samples=samples, r=280.0)

		return samples


	def oversamplingBlobsWImportanceSampling(self, area, classes_to_sample, radii):
		"""
		Sample the blobs of the map using Importance Sampling according to the precomputed radius map.
		Only the given classes are sampled.
		The functions returns a list of (x,y) coordinates.
		"""

		# minority classes are sampled before majority classes
		samples = []
		for class_name in classes_to_sample:
			for blob in self.blobs:
				if blob.class_name == class_name:
					samples = self.sampleBlobWimportanceSampling(blob, samples)
					txt = str(len(samples)) + "\r"
					sys.stdout.write(txt)

		tile_size = 1024
		step = 256

		tile_cols = 1 + int(area[2] / step)
		tile_rows = 1 + int(area[3] / step)

		for row in range(tile_rows):
			for col in range(tile_cols):

				top = area[0] + row * step
				left = area[1] + col * step

				if left + tile_size > area[1] + area[2] - 1:
					left = area[2] - tile_size - 1

				if top + tile_size > area[0] + area[3] - 1:
					top = area[3] - tile_size - 1

				sub_area = [top, left, tile_size, tile_size]

				samples = self.sampleSubAreaWImportanceSampling(sub_area, samples)

		return samples


	def cut_tiles(self, regular=True, oversampling=False, classes_to_sample=None, radii=None):
		"""
		Cut the ortho into tiles.
		The cutting can be regular or depending on the area and shape of the corals (oversampling).
		"""

		w = self.ortho_image.width()
		h = self.ortho_image.height()

		delta = int(self.crop_size / 2)

		if regular is True:
			self.validation_tiles = self.sampleAreaUniformly(self.val_area, self.tile_size, self.step)
			self.test_tiles = self.sampleAreaUniformly(self.test_area, self.tile_size, self.step)
			self.training_tiles = self.sampleAreaUniformly([delta, delta, w-delta*2, h-delta*2], self.tile_size, self.step)

		if oversampling is True:

			validation_oversampled = False

			if validation_oversampled is False:
				self.validation_tiles = self.sampleAreaUniformly(self.val_area, self.tile_size, self.step)
				self.test_tiles = self.sampleAreaUniformly(self.test_area, self.tile_size, self.step)
				self.training_tiles = self.oversamplingBlobsWPoissonDisk([delta, delta, w-delta*2,  h-delta*2],
																	 classes_to_sample, radii)
			else:
				self.test_tiles = self.sampleAreaUniformly(self.test_area, self.tile_size, self.step)
				tiles = self.oversamplingBlobsWPoissonDisk([delta, delta, w-delta*2,  h-delta*2],
																	 classes_to_sample, radii)

				bbox = [0, 0, 0, 0]
				half_size = int(self.crop_size + 4) / 2
				self.validation_tiles = []
				self.training_tiles = []
				for tile in tiles:
					bbox[0] = tile[1] - half_size
					bbox[1] = tile[0] - half_size
					bbox[2] = half_size * 2
					bbox[3] = half_size * 2
					perc = (100.0 * self.bbox_intersection(self.val_area, bbox)) / float(half_size * half_size * 4)
					if perc > 95.0:
						self.validation_tiles.append(tile)
					else:
						self.training_tiles.append(tile)

		self.training_tiles = self.cleanTrainingTiles(self.training_tiles)

		if oversampling is True:
			self.validation_tiles = self.cleaningValidationTiles(self.validation_tiles)


	def export_tiles(self, basename, tilename):
		"""
		Exports the tiles INSIDE the given areas (val_area and test_area are stored as (top, left, width, height))
		The training tiles are the ones of the entire map minus the ones inside the test validation and test area.
		"""

		##### VALIDATION AREA

		basenameVim = os.path.join(basename, os.path.join("validation", "images"))
		try:
			os.makedirs(basenameVim)
		except:
			pass

		basenameVlab = os.path.join(basename, os.path.join("validation", "labels"))
		try:
			os.makedirs(basenameVlab)
		except:
			pass

		self.cropAndSaveTiles(self.validation_tiles, tilename, basenameVim, basenameVlab)

		##### TEST AREA

		basenameTestIm = os.path.join(basename, os.path.join("test", "images"))
		try:
			os.makedirs(basenameTestIm)
		except:
			pass

		basenameTestLab = os.path.join(basename, os.path.join("test", "labels"))
		try:
			os.makedirs(basenameTestLab)
		except:
			pass

		self.cropAndSaveTiles(self.test_tiles, tilename, basenameTestIm, basenameTestLab)

		basenameTrainIm = os.path.join(basename, os.path.join("training", "images"))
		try:
			os.makedirs(basenameTrainIm)
		except:
			pass

		basenameTrainLab = os.path.join(basename, os.path.join("training", "labels"))
		try:
			os.makedirs(basenameTrainLab)
		except:
			pass

		self.cropAndSaveTiles(self.training_tiles, tilename, basenameTrainIm, basenameTrainLab)



	def cropAndSaveTiles(self, tiles, tilename, basenameim, basenamelab):
		"""
		Given a list of tiles save them by cutting the RGB orthoimage and hte label image.
		COCO annotations is also saved (optionally).
		"""

		imagecount_id = 0
		segcount_id = 0

		imageList = []
		segmentationList = []

		if self.flag_coco:

			##### info dataset

			info = dict.fromkeys(['description', 'url', 'version', 'year', 'contributor', 'date_created'])

			info["contributor"] = ""
			info["description"] = "Dataset created by TagLab"
			info["url"] = ""
			info["version"] = "1.0"
			info["date_created"] = datetime.date.today().isoformat()
			info["year"] = str(datetime.date.today().year)

			##### CATEGORIES

            # a list of dictionaries for classes
			categorieslist = []

			list_keys = list(self.labels_dict.keys())
			list_keys.sort()

			# used later to retrieve the category id
			color_to_category_id = {}

			for i, key in enumerate(list_keys):

				color = self.labels_dict[key].fill
				color_key = str(color[0]) + "-" + str(color[1]) + "-" + str(color[2])

				labeldict = {
						"supercategory": "coral",
						"color": color,
						"id": i,
						"name": key}

				categorieslist.append(labeldict)

				color_to_category_id[color_key] = i

			output_folder = os.path.dirname(basenameim)
			annotations_filename = os.path.join(output_folder, 'annotations.json')

			# if an annotation file just exists the information need to be updated
			# NOTE THAT THE DICTIONARY MUST BE THE SAME TO MERGE TWO DATASET (!!)
			if os.path.exists(annotations_filename):
				f = open(annotations_filename, 'r')
				ann = json.load(f)
				max_id = 0
				for image in ann["images"]:
					max_id = max(max_id, image["id"])
					imageList.append(image)
				imagecount_id = max_id + 1

				max_id = 0
				for annotation in ann["annotations"]:
					max_id = max(max_id, annotation["id"])
					segmentationList.append(annotation)
				segcount_id = max_id + 1

			jsondata = {'info': info, 'categories': categorieslist}

		half_tile_size = self.tile_size / 2

		for i, sample in enumerate(tiles):

			cx = sample[0]
			cy = sample[1]
			top = cy - half_tile_size
			left = cx - half_tile_size

			cropimg = utils.cropQImage(self.ortho_image, [top, left, self.tile_size, self.tile_size])
			croplabel = utils.cropQImage(self.label_image, [top, left, self.tile_size, self.tile_size])

			filenameRGB = os.path.join(basenameim, tilename + str.format("_{0:04d}", (i)) + ".png")
			filenameLabel = os.path.join(basenamelab, tilename + str.format("_{0:04d}", (i)) + ".png")

			cropimg.save(filenameRGB)
			croplabel.save(filenameLabel)

			if self.flag_coco:

				image_dict = {"license": 2,
						 "file_name": tilename + str.format("_{0:04d}", (i)) + ".png",
						 "coco_url": filenameRGB,
						 "height": self.tile_size,
						 "width": self.tile_size,
						 "date_captured": self.image_info.acquisition_date,
						 "id": imagecount_id }

				cropidlabel = utils.cropQImage(self.id_image, [top, left, self.tile_size, self.tile_size])
				cropidlabel = utils.qimageToNumpyArray(cropidlabel)
				cropIdBinary = (cropidlabel[:,:,0] > 0).astype(int)
				regions = measure.regionprops(measure.label(cropIdBinary, connectivity=1))

				for region in regions:

					tilemask = np.zeros_like(cropIdBinary).astype(np.uint8)
					tilemask[region.coords[:, 1], region.coords[:, 0]] = 1
					#segmentation = utils.binaryMaskToRle(tilemask)
					segmentation = maskcoco.encode(np.asfortranarray(np.transpose(tilemask)))

					segmentation["counts"] = segmentation["counts"].decode("utf-8")

					category_id = -1
					for jj in range(10):
						N = int((jj * region.coords.shape[0]) / 10)
						rgb = croplabel.pixel(region.coords[N, 1], region.coords[N, 0])
						color_key = str(qRed(rgb)) + "-" + str(qGreen(rgb)) + "-" + str(qBlue(rgb))
						if color_key != "0-0-0":
							category_id = color_to_category_id[color_key]

					# COCO format for BBOX -> [x,y,width,height]
					bbox = [region.bbox[1], region.bbox[0], region.bbox[3] - region.bbox[1], region.bbox[2] - region.bbox[0]]

					infos = {'segmentation': {}, 'area' : int(region.area), 'iscrowd' : 0,'image_id': imagecount_id, 'bbox': bbox, 'category_id': category_id, "id": segcount_id}

					segcount_id = segcount_id + 1

					infos["segmentation"] = segmentation

					if category_id >= 0:
						segmentationList.append(infos)

				imageList.append(image_dict)

				imagecount_id = imagecount_id + 1


		if self.flag_coco:

			jsondata["images"] = imageList
			jsondata["annotations"] = segmentationList

			with open(annotations_filename, 'w') as f:
				json.dump(jsondata, f)


	##### VISUALIZATION FUNCTIONS - FOR DEBUG PURPOSES

	def save_samples(self, filename, show_tiles=False, show_areas=True, radii=None):
		"""
        Save a figure to show the samples in the different areas.
        """

		labelimg = self.label_image.copy()

		painter = QPainter(labelimg)

		half_tile_size = self.tile_size / 2

		SAMPLE_SIZE = 20
		HALF_SAMPLE_SIZE = SAMPLE_SIZE / 2

		# TRAINING
		brush = QBrush(Qt.SolidPattern)
		brush.setColor(Qt.green)
		painter.setBrush(brush)
		pen = QPen(Qt.white)
		pen.setWidth(5)
		painter.setPen(pen)
		for sample in self.training_tiles:
			cx = sample[0] - HALF_SAMPLE_SIZE
			cy = sample[1] - HALF_SAMPLE_SIZE
			painter.drawEllipse(cx, cy, SAMPLE_SIZE, SAMPLE_SIZE)

		# brush = QBrush(Qt.NoBrush)
		# brush.setColor(Qt.green)
		# painter.setBrush(brush)
		# pen = QPen(Qt.white)
		# pen.setWidth(3)
		# painter.setPen(pen)
		# for sample in self.training_tiles:
		# 	cx = sample[0]
		# 	cy = sample[1]
		# 	r = int(radii[self.labels[cy,cx]])
		# 	if r < 61.0:
		# 		painter.drawEllipse(cx - r, cy - r, r*2, r*2)

		# VALIDATION
		brush = QBrush(Qt.SolidPattern)
		brush.setColor(Qt.blue)
		painter.setBrush(brush)
		for sample in self.validation_tiles:
			cx = sample[0] - HALF_SAMPLE_SIZE
			cy = sample[1] - HALF_SAMPLE_SIZE
			painter.drawEllipse(cx, cy, SAMPLE_SIZE, SAMPLE_SIZE)

		# TEST
		brush = QBrush(Qt.SolidPattern)
		brush.setColor(Qt.red)
		painter.setBrush(brush)
		for sample in self.test_tiles:
			cx = sample[0] - HALF_SAMPLE_SIZE
			cy = sample[1] - HALF_SAMPLE_SIZE
			painter.drawEllipse(cx, cy, SAMPLE_SIZE, SAMPLE_SIZE)

		if show_tiles is True:

			size = self.crop_size
			half_size = int(size / 2)

			PEN_WIDTH = 20

			painter.setBrush(Qt.NoBrush)
			pen = QPen(Qt.green)
			pen.setWidth(PEN_WIDTH)
			painter.setPen(pen)
			for sample in self.training_tiles:
				cx = sample[0]
				cy = sample[1]
				top = cy - half_size
				left = cx - half_size
				painter.drawRect(left, top, size, size)

			pen = QPen(Qt.blue)
			pen.setWidth(PEN_WIDTH)
			painter.setPen(pen)
			for sample in self.validation_tiles:
				cx = sample[0]
				cy = sample[1]
				top = cy - half_size
				left = cx - half_size
				painter.drawRect(left, top, size, size)

			pen = QPen(Qt.red)
			pen.setWidth(PEN_WIDTH)
			painter.setPen(pen)
			for sample in self.test_tiles:
				cx = sample[0]
				cy = sample[1]
				top = cy - half_size
				left = cx - half_size
				painter.drawRect(left, top, size, size)

		if show_areas is True:

			pen_width = int(min(self.label_image.width(), self.label_image.height()) / 200.0)

			painter.setBrush(Qt.NoBrush)
			pen = QPen(Qt.blue)
			pen.setWidth(pen_width)
			pen.setStyle(Qt.DashDotLine)
			painter.setPen(pen)
			painter.drawRect(self.val_area[1], self.val_area[0], self.val_area[2], self.val_area[3])

			painter.setBrush(Qt.NoBrush)
			pen = QPen(Qt.red)
			pen.setWidth(pen_width)
			pen.setStyle(Qt.DashDotLine)
			painter.setPen(pen)
			painter.drawRect(self.test_area[1], self.test_area[0], self.test_area[2], self.test_area[3])

		painter.end()

		labelimg.save(filename)
