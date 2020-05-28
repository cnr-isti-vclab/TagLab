import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPen, QFont
from PyQt5.QtWidgets import QGraphicsItem
from source.tools.Tool import Tool

class Ruler(Tool):
    def __init__(self, viewerplus, pick_points ):
        super(Ruler, self).__init__(viewerplus)
        self.pick_points = pick_points
        self.scene = viewerplus.scene

        self.CROSS_LINE_WIDTH = 2
        self.pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}
        self.map_px_to_mm_factor = None

    def setPxToMM(self, factor):
        self.map_px_to_mm_factor = factor

    def leftPressed(self, x, y):
        points = self.pick_points.points
        # first point
        if len(points) == 0:
            self.pick_points.addPoint(x, y, self.pick_style)

        # sedcond point
        elif len(points) == 1:
            self.pick_points.addPoint(x, y, self.pick_style)
            self.drawRuler(self.viewerplus.annotations)

        else:
            self.pick_points.reset()



    def drawRuler(self, annotations):
        # warging! this might move the pick points to the centroids of the blobs, redraw!
        measure = self.computeMeasure(annotations)
        tmp = self.pick_points.points.copy()
        self.pick_points.reset()
        self.pick_points.addPoint(tmp[0][0], tmp[0][1], self.pick_style)
        self.pick_points.addPoint(tmp[1][0], tmp[1][1], self.pick_style)

        # pick points number is now 2
        pen = QPen(Qt.blue)
        pen.setWidth(2)
        pen.setCosmetic(True)
        start = self.pick_points.points[0]
        end = self.pick_points.points[1]
        line = self.scene.addLine(start[0], start[1], end[0], end[1], pen)
        self.pick_markers.append(line)

        middle_x = (start[0] + end[0]) / 2.0
        middle_y = (start[1] + end[1]) / 2.0

        middle = self.scene.addEllipse(middle_x, middle_y, 0, 0)

        ruler_text = self.scene.addText('%.1f' % measure)
        ruler_text.setFont(QFont("Times", 12, QFont.Bold))
        ruler_text.setDefaultTextColor(Qt.white)
        ruler_text.setPos(middle_x, middle_y)
        ruler_text.setParentItem(middle)
        ruler_text.setFlag(QGraphicsItem.ItemIgnoresTransformations)

        self.logfile.info("[TOOL][RULER] Measure taken.")

        self.pick_markers.append(middle);

    def computeMeasure(self, annotations):
        """
        It computes the measure between two points. If this point lies inside two blobs
        the distance between the centroids is computed.
        """
        points = self.pick_points.points
        x1 = points[0][0]
        y1 = points[0][1]
        x2 = points[1][0]
        y2 = points[1][1]

        blob1 = annotations.clickedBlob(x1, y1)
        blob2 = annotations.clickedBlob(x2, y2)

        if blob1 is not None and blob2 is not None and blob1 != blob2:

            x1 = blob1.centroid[0]
            y1 = blob1.centroid[1]
            x2 = blob2.centroid[0]
            y2 = blob2.centroid[1]

            points[0][0] = x1
            points[1][0] = x2
            points[1][0] = y1
            points[1][1] = y2

        measurepx = np.sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2))

        if self.map_px_to_mm_factor is None:
            raise Exception("map_px to mm factor in ruler needs to be explicitly set")
        # conversion to cm
        measure = measurepx * self.map_px_to_mm_factor / 10
        return measure
