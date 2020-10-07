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

    def leftPressed(self, x, y, mods):
        if self.scribbles.startDrawing(x, y):
            self.log.emit("[TOOL][FREEHAND] DRAWING starts..")

    def mouseMove(self, x, y):
        self.scribbles.move(x, y)

    def wheel(self, delta):
        increase = float(delta.y()) / 10.0
        if 0.0 < increase < 1.0:
            increase = 1
        elif -1.0 < increase < 0.0:
            increase = -1
        self.scribbles.setSize(int(increase))

    def apply(self):
        if len(self.scribbles.points) == 0:
            self.infoMessage.emit("You need to draw something for this operation.")
            return

        bboxes =[]
        for i, curve in enumerate(self.scribbles.points):
            bbox= Mask.pointsBox(curve, int(self.scribbles.size[i]/2))
            bboxes.append(bbox)
        working_area = Mask.jointBox(bboxes)

        if working_area[0] < 0:
           working_area[0] = 0

        if working_area[1] < 0:
           working_area[1] = 0

        if working_area[0] + working_area[3] > self.viewerplus.img_map.height():
           working_area[3] = self.viewerplus.img_map.height() - working_area[0]

        if working_area[1] + working_area[2] > self.viewerplus.img_map.width():
           working_area[2] = self.viewerplus.img_map.width() - working_area[1]


        crop_img = utils.cropQImage(self.viewerplus.img_map, working_area)
        crop_imgnp = utils.qimageToNumpyArray(crop_img)
        #edges = sobel(crop_imgnp)

        # x,y
        mask = np.zeros((working_area[3], working_area[2], 3), dtype=np.int32)

        # Green color in BGR
        for i, curve in enumerate(self.scribbles.points):
            color = (self.scribbles.color[i].blue(), self.scribbles.color[i].green(), self.scribbles.color[i].red())
            curve = np.int32(curve)

            curve[:, 0] = curve[:, 0] - working_area[1]
            curve[:, 1] = curve[:, 1] - working_area[0]

            curve = curve.reshape((-1, 1, 2))
            mask = cv2.polylines(mask, [curve], False, color, thickness=self.scribbles.size[i], lineType=cv2.LINE_4)

        mask=np.uint8(mask)

       # mask = cv2.imread('C:\\Users\\Gaia\\Desktop\\mura\\crop_mask.png')

        markers = np.int32(255*rgb2gray(mask))
        # markersprint = 255*rgb2gray(mask)
        # cv2.imwrite('mask.png', markersprint)
        # ret, markers = cv2.connectedComponents(mask)
       # image = utils.qimageToNumpyArray(self.viewerplus.img_map)
        segmentation = cv2.watershed(crop_imgnp, markers)
        segmentation = segmentation + 1


        for region in measure.regionprops(segmentation):
            blob = Blob(region, working_area[1], working_area[0], self.viewerplus.annotations.getFreeId())
           # blob = Blob(region, 0, 0, self.viewerplus.annotations.getFreeId())
            self.viewerplus.addBlob(blob)
            
        self.viewerplus.resetTools()
