from source.tools.Tool import Tool
from source.Blob import Blob
from source import Mask
from source import utils
import numpy as np
from skimage import measure, filters
from skimage.morphology import disk
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

        # compute bbox of scribbles (working area)
        bboxes =[]
        for i, curve in enumerate(self.scribbles.points):
            bbox= Mask.pointsBox(curve, int(self.scribbles.size[i]/2))
            bboxes.append(bbox)
        working_area = Mask.jointBox(bboxes)

        if working_area[0] < 0:
           working_area[0] = 0

        if working_area[1] < 0:
           working_area[1] = 0

        if working_area[0] + working_area[3] > self.viewerplus.img_map.height() - 1:
           working_area[3] = self.viewerplus.img_map.height() - 1 - working_area[0]

        if working_area[1] + working_area[2] > self.viewerplus.img_map.width() - 1:
           working_area[2] = self.viewerplus.img_map.width() - 1 - working_area[1]

        crop_img = utils.cropQImage(self.viewerplus.img_map, working_area)
        crop_imgnp = utils.qimageToNumpyArray(crop_img)

        # create markers
        mask = np.zeros((working_area[3], working_area[2], 3), dtype=np.int32)

        color_codes = dict()
        counter = 1
        for i, curve in enumerate(self.scribbles.points):

            b = self.scribbles.color[i].blue()
            g = self.scribbles.color[i].green()
            r = self.scribbles.color[i].red()
            color = (b, g, r)

            color_code = b + 256 * g + 65536 * r
            color_key = str(color_code)
            if color_codes.get(color_key) is None:
                color_codes[color_key] = counter
                counter = counter + 1

            curve = np.int32(curve)

            curve[:, 0] = curve[:, 0] - working_area[1]
            curve[:, 1] = curve[:, 1] - working_area[0]

            curve = curve.reshape((-1, 1, 2))
            mask = cv2.polylines(mask, pts=[curve], isClosed=False, color=color,
                                 thickness=self.scribbles.size[i], lineType=cv2.LINE_8)

        mask = np.uint8(mask)

        labelsint = np.zeros((working_area[3], working_area[2]), dtype='int32')
        for color in self.scribbles.color:
            b = color.blue()
            g = color.green()
            r = color.red()
            color_code = b + 256 * g + 65536 * r
            color_key = str(color_code)

            idx = np.where((mask[:, :, 0] == b) & (mask[:, :, 1] == g) & (mask[:, :, 2] == r))
            labelsint[idx] = color_codes[color_key]

        # markers = np.int32(255*rgb2gray(mask))
        # markersprint = 255*rgb2gray(mask)
        markersprint = labelsint
        cv2.imwrite('mask.png', markersprint)

        # watershed segmentation
        segmentation = cv2.watershed(crop_imgnp, labelsint)
        segmentation = filters.median(segmentation, disk(5), mode="mirror")
        cv2.imwrite('segmentation.png', segmentation)

        # the result of the segmentation must be converted into labels again
        lbls = measure.label(segmentation)

        for region in measure.regionprops(lbls):
            blob = Blob(region, working_area[1], working_area[0], self.viewerplus.annotations.getFreeId())
            self.viewerplus.addBlob(blob)
            
        self.viewerplus.resetTools()
