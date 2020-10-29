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
import math
import numpy as np
from PyQt5.QtGui import QPainter, QImage, QPen, QBrush, QColor, qRgb
from PyQt5.QtCore import Qt
import random as rnd
from source import utils
from skimage.filters import gaussian
from skimage.segmentation import find_boundaries
from skimage import measure
import glob
import sys


class NewDataset(object):
	"""
	This class handles the functionalities to create a new dataset.
	"""

	def __init__(self, ortho_image, blobs, tile_size, step):

		self.ortho_image = ortho_image  # QImage
		self.blobs = blobs
		self.tile_size = tile_size
		self.step = step

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

		self.crop_size = 513

		self.frequencies = None

		self.radius_map = None

		# normalization factors
		self.sn_min = 0.0
		self.sn_max = 0.0
		self.sc_min = 0.0
		self.sc_max = 0.0
		self.sP_min = 0.0
		self.sP_max = 0.0


	def workingAreaCropAndRescale(self, current_scale, target_scale, working_area):

		x = working_area[1]
		y = working_area[0]
		width = working_area[2]
		height = working_area[3]

		crop_ortho_image = self.ortho_image.copy(x, y, width, height)
		crop_label_image = self.label_image.copy(x, y, width, height)

		scale = target_scale/current_scale
		w = crop_ortho_image.width()*scale
		h = crop_ortho_image.height()*scale

		self.ortho_image = crop_ortho_image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
		self.label_image = crop_label_image.scaled(w, h, Qt.IgnoreAspectRatio, Qt.FastTransformation)


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

		frequencies = []
		for class_name in target_classes:
			area = 0.0
			for blob in self.blobs:
				if blob.class_name == class_name:
					area += blob.area

			freq = area / area_map
			frequencies.append(freq)

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

		coverage_per_class = []
		for i in range(len(target_classes)):
			i = i + 1  # background is skipped
			coverage = float(np.count_nonzero(labelsint == i)) / A
			coverage_per_class.append(coverage)

		return coverage_per_class


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
		for i, class_name in enumerate(target_classes):

			areas = []
			if self.frequencies[i] > 0.0:
				for blob in self.blobs:
					if blob.class_name == class_name and self.checkBlobInside(area, blob, 3.0/4.0):
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

			for i, score in enumerate(scores):
				if math.isnan(score):
					scores[i] = 0.0

			aggregated_score = sum(scores) / len(scores)

			area_info.append((area_bbox, scores, aggregated_score))


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



	def createLabelImage(self, labels_info):
		"""
		It converts the blobs in the label image.
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

				if blob.qpath_gitem.isVisible():

					if blob.class_name == "Empty":
						rgb = qRgb(0, 0, 0)
					else:
						class_color = labels_info[blob.class_name]
						rgb = qRgb(class_color[0], class_color[1], class_color[2])

					painter.setBrush(QBrush(QColor(rgb)))
					painter.drawPath(blob.qpath_gitem.path())

		painter.end()

		self.label_image = labelimg


	def convert_colors_to_labels(self, target_classes, labels_colors):
		"""
		Convert the label image to a numpy array with the labels' values.
		"""

		label_w = self.label_image.width()
		label_h = self.label_image.height()

		imglbl = utils.qimageToNumpyArray(self.label_image)

		num_classes = len(target_classes)

		# class 0 --> background
		self.labels = np.zeros((label_h, label_w), dtype='int64')
		for i, cl in enumerate(target_classes):
			class_colors = labels_colors.get(cl)
			if class_colors is None:
				if cl == "Background":
					class_colors = [0, 0, 0]
				else:
					class_colors = [255, 255, 255]
			idx = np.where((imglbl[:, :, 0] == class_colors[0]) & (imglbl[:, :, 1] == class_colors[1]) & (imglbl[:, :, 2] == class_colors[2]))
			self.labels[idx] = i + 1


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

			area_w = int(math.sqrt(0.15) * map_w)
			area_h = int(math.sqrt(0.15) * map_h)

			for j in range(1000):
				px1 = rnd.randint(0, map_w - area_w - 1)
				py1 = rnd.randint(0, map_h - area_h - 1)
				px2 = rnd.randint(0, map_w - area_w - 1)
				py2 = rnd.randint(0, map_h - area_h - 1)

				area1 = [px1, py1, area_w, area_h]
				area2 = [px2, py2, area_w, area_h]

				intersection = self.bbox_intersection(area1, area2)

				if intersection < 1.0:
					val_area = area1
					test_area = area2

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
				if area > 10.0:
					flag = False
					break

			if flag is True:
				for ttile in self.test_tiles:

					bbox2[0] = ttile[1] - half_size
					bbox2[1] = ttile[0] - half_size
					bbox2[2] = half_size * 2
					bbox2[3] = half_size * 2

					area = self.bbox_intersection(bbox1, bbox2)
					if area > 10.0:
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
				if area > 10.0:
					flag = False

			if flag is True:
				for tile in self.test_tiles:

					bbox2[0] = tile[1] - half_size
					bbox2[1] = tile[0] - half_size
					bbox2[2] = half_size * 2
					bbox2[3] = half_size * 2

					area = self.bbox_intersection(bbox1, bbox2)
					if area > 10.0:
						flag = False

			if flag is True:
				cleaned_tiles.append(vtile)

		return cleaned_tiles


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


	def export_tiles(self, basename, tilename, labels_info):
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

		half_tile_size = self.tile_size / 2

		for i, sample in enumerate(self.validation_tiles):

			cx = sample[0]
			cy = sample[1]
			top = cy - half_tile_size
			left = cx - half_tile_size
			cropimg = utils.cropQImage(self.ortho_image, [top, left, self.tile_size, self.tile_size])
			croplabel = utils.cropQImage(self.label_image, [top, left, self.tile_size, self.tile_size])

			filenameRGB = os.path.join(basenameVim, tilename + str.format("_{0:04d}", (i)) + ".png")
			filenameLabel = os.path.join(basenameVlab, tilename + str.format("_{0:04d}", (i)) + ".png")

			cropimg.save(filenameRGB)
			croplabel.save(filenameLabel)


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

		for i, sample in enumerate(self.test_tiles):

			cx = sample[0]
			cy = sample[1]
			top = cy - half_tile_size
			left = cx - half_tile_size

			cropimg = utils.cropQImage(self.ortho_image, [top, left, self.tile_size, self.tile_size])
			croplabel = utils.cropQImage(self.label_image, [top, left, self.tile_size, self.tile_size])

			filenameRGB = os.path.join(basenameTestIm, tilename + str.format("_{0:04d}", (i)) + ".png")
			filenameLabel = os.path.join(basenameTestLab, tilename + str.format("_{0:04d}", (i)) + ".png")

			cropimg.save(filenameRGB)
			croplabel.save(filenameLabel)

		##### TRAINING AREA = ENTIRE MAP / (VALIDATION AREA U TEST_AREA)

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

		for i, sample in enumerate(self.training_tiles):

			cx = sample[0]
			cy = sample[1]
			top = cy - half_tile_size
			left = cx - half_tile_size

			cropimg = utils.cropQImage(self.ortho_image, [top, left, self.tile_size, self.tile_size])
			croplabel = utils.cropQImage(self.label_image, [top, left, self.tile_size, self.tile_size])

			filenameRGB = os.path.join(basenameTrainIm, tilename + str.format("_{0:04d}", (i)) + ".png")
			filenameLabel = os.path.join(basenameTrainLab, tilename + str.format("_{0:04d}", (i)) + ".png")

			cropimg.save(filenameRGB)
			croplabel.save(filenameLabel)


	##### SERVICE FUNCTIONS

	def classFrequenciesOnTiles(self, target_classes):

		num_classes = len(target_classes)
		delta = int(self.crop_size / 2)
		area = [0, 0, 0, 0]
		coverage = np.zeros(num_classes, dtype='float')
		for tile in self.training_tiles:
			area[0] = int(tile[1] - delta)
			area[1] = int(tile[0] - delta)
			area[2] = self.crop_size
			area[3] = self.crop_size

			cov = self.computeExactCoverage(area, target_classes)
			coverage += np.array(cov)

		coverage = coverage / len(self.training_tiles)
		return coverage


	def classFrequenciesOnDataset(self, labels_dir, target_classes, labels_colors):
		"""
		Returns the frequencies of the target classes on the given dataset.
        """

		num_classes = len(target_classes)

		image_label_names = [x for x in glob.glob(os.path.join(labels_dir, '*.png'))]

		total_pixels = 0
		counters = np.zeros(num_classes, dtype='float')
		for label_name in image_label_names:

			image_label = QImage(label_name)
			# image_label = image_label.convertToFormat(QImage.Format_RGB32)
			label_w = image_label.width()
			label_h = image_label.height()
			total_pixels += label_w * label_h
			imglbl = utils.qimageToNumpyArray(image_label)

			# class 0 --> background
			labelsint = np.zeros((label_h, label_w), dtype='int64')
			for i, cl in enumerate(target_classes):
				class_colors = labels_colors[cl]
				idx = np.where((imglbl[:, :, 0] == class_colors[0]) & (imglbl[:, :, 1] == class_colors[1]) & (
							imglbl[:, :, 2] == class_colors[2]))
				labelsint[idx] = i + 1

			for i in range(len(target_classes)):
				counters[i] += float(np.count_nonzero(labelsint == i + 1))

		freq = counters / float(total_pixels)
		print(freq)

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
			pen.setWidth(5)
			painter.setPen(pen)
			painter.drawRect(self.val_area[1], self.val_area[0], self.val_area[2], self.val_area[3])

			painter.setBrush(Qt.NoBrush)
			pen = QPen(Qt.red)
			pen.setWidth(5)
			painter.setPen(pen)
			painter.drawRect(self.test_area[1], self.test_area[0], self.test_area[2], self.test_area[3])

		painter.end()

		labelimg.save(filename)
