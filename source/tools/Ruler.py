import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPen, QFont
from PyQt5.QtWidgets import QGraphicsItem
from source.tools.Tool import Tool

class Ruler(Tool):
    measuretaken = pyqtSignal(float)
    def __init__(self, viewerplus, pick_points ):
        super(Ruler, self).__init__(viewerplus)
        self.pick_points = pick_points
        self.viewerplus = viewerplus

        self.CROSS_LINE_WIDTH = 2
        self.pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 6}


    def leftPressed(self, x, y, mods):
        points = self.pick_points.points
        # first point
        if len(points) == 0:
            self.pick_points.addPoint(x, y, self.pick_style)

        # second point
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
        line = self.viewerplus.scene.addLine(start[0], start[1], end[0], end[1], pen)
        line.setZValue(5)


        self.pick_points.markers.append(line)

        middle_x = (start[0] + end[0]) / 2.0
        middle_y = (start[1] + end[1]) / 2.0

        middle = self.viewerplus.scene.addEllipse(middle_x, middle_y, 0, 0)
        middle.setZValue(5)

        ruler_text = self.viewerplus.scene.addText('%.1f cm' % measure)
        ruler_text.setFont(QFont("Calibri", 12, QFont.Bold))
        ruler_text.setDefaultTextColor(Qt.white)
        ruler_text.setPos(middle_x, middle_y)
        ruler_text.setParentItem(middle)
        ruler_text.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        ruler_text.setZValue(5)
        self.pick_points.markers.append(ruler_text);
        self.pick_points.markers.append(middle);


        self.log.emit("[TOOL][RULER] Measure taken.")
        self.measuretaken.emit(measure)


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

        if blob1 is not None and blob2 is not None and blob1 is not blob2:

            x1 = blob1.centroid[0]
            y1 = blob1.centroid[1]
            x2 = blob2.centroid[0]
            y2 = blob2.centroid[1]

            points[0][0] = x1
            points[0][1] = y1
            points[1][0] = x2
            points[1][1] = y2

        measurepx = np.sqrt(((x2 - x1) ** 2) + ((y2 - y1) ** 2))

        # conversion to cm
        measure = measurepx * self.viewerplus.image.pixelSize() / 10
        return measure
