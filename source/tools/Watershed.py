from source.tools.Tool import Tool
from source.Blob import Blob
from source import Mask
from source import utils
import numpy as np
from skimage import measure
from skimage.color import rgb2gray
from skimage.filters import sobel
import cv2


class Watershed(Tool):
    def __init__(self, viewerplus, scribbles):
        super(Watershed, self).__init__(viewerplus)
        self.viewerplus = viewerplus
        self.scribbles = scribbles

    def setActiveLabel(self, label):
        self.scribbles.setColor(label.fill)
        self.active_label = label

    def leftPressed(self, x, y, mods):
        if self.scribbles.startDrawing(x, y):
            self.log.emit("[TOOL][FREEHAND] DRAWING starts..")

    def mouseMove(self, x, y):
        self.scribbles.move(x, y)

    def apply(self):
        if len(self.scribbles.points) == 0:
            self.infoMessage.emit("You need to draw something for this operation.")
            return

        # tiro fuori il bbox unione di tutti gli scribble disegnati che diventa l'area di lavoro
        bboxes =[]
        for curve in self.scribbles.points:
            bbox= Mask.pointsBox(curve, 100)
            bboxes.append(bbox)
        working_area = Mask.jointBox(bboxes)
        crop_img = utils.cropQImage(self.viewerplus.img_map,working_area)
        crop_imgnp = utils.qimageToNumpyArray(crop_img)
        #edges = sobel(crop_imgnp)

        # x,y
        markers = np.zeros((working_area[3], working_area[2]), dtype=np.int32)

        # Green color in BGR
        for i, curve in enumerate(self.scribbles.points):
            color = (self.scribbles.color[i].blue(), self.scribbles.color[i].green(), self.scribbles.color[i].red())
            curve = np.int32(curve)
            curve[:, 0] = curve[:, 0] - working_area[1]
            curve[:,1] = curve[:, 1] - working_area[0]
            curve = curve.reshape((-1, 1, 2))
            markers = cv2.polylines(markers, [curve], False, color, self.scribbles.size[i])

        markers= np.uint8(markers)
        ret, markers = cv2.connectedComponents(markers)
        segmentation = cv2.watershed(crop_imgnp, markers)
        segmentation = segmentation + 1


        for region in measure.regionprops(segmentation):
            blob = Blob(region, working_area[1], working_area[0], self.viewerplus.annotations.getFreeId())
            self.viewerplus.addBlob(blob)
            
        self.viewerplus.resetTools()