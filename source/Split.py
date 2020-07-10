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

import numpy as np

def isFullyInsideBBox(bbox1, bbox2):
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


def bbox_intersection(bbox1, bbox2):
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


def calculateMetrics(blobs, target_classes, map_w, map_h):
	"""
	Given a list of blobs calculate the spatial/ecological metrics.
	"""

	number = []
	coverage = []
	PSVC = []
	for class_name in target_classes:

		areas = []
		for blob in blobs:
			if blob.class_name == class_name:
				areas.append(blob.area)

		# number of entities
		number.append(len(areas))

		if len(areas) > 0:

			# Patch Size Coefficient of Variation (PSCV)
			mean_areas = mean(areas)
			std_areas = std(areas)
			PSCV.append((100.0 * std_areas) / mean_areas)

			# Coverage, related to the density
			coverage.append(sum(areas) / (map_w * map_h))

		else:

			PSCV.append(0.0)
			coverage.append(0.0)

	return number, coverage, PSCV


def calculateScore(area_number, area_coverage, area_PSCV, landscape_number, landscape_coverage, landscape_PSCV):
	"""
	The score is close to one if
	"""

	s1 = abs((area_number / landscape_number) * 100.0 - 15.0)
	s2 = abs((area_coverage - landscape_coverage) * 100.0)
	s3 = abs(area_PSCV - landscape_PSCV)

	score = 1.5 * s1 + s2 + s3

	return score

def findAreas(blobs):

	pass