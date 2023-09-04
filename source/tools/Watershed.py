from source.tools.Tool import Tool
from source.Blob import Blob
from source import Mask
from source import genutils
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
        self.current_blobs = []

    def setActiveLabel(self, label):
        self.scribbles.setLabel(label)

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

    def segmentation(self):

        # compute bbox of scribbles (working area)
        bboxes = []
        for i, curve in enumerate(self.scribbles.points):
            bbox = Mask.pointsBox(curve, int(self.scribbles.size[i] / 2))
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

        crop_img = genutils.cropQImage(self.viewerplus.img_map, working_area)
        crop_imgnp = genutils.qimageToNumpyArray(crop_img)

        # create markers
        mask = np.zeros((working_area[3], working_area[2], 3), dtype=np.int32)

        color_codes = dict()
        counter = 1
        for i, curve in enumerate(self.scribbles.points):

            col = self.scribbles.label[i].fill
            b = col[2]
            g = col[1]
            r = col[0]
            color = (b, g, r)

            color_code = b + 256 * g + 65536 * r
            color_key = str(color_code)
            if color_codes.get(color_key) is None:
                name = self.scribbles.label[i].name
                color_codes[color_key] = (counter, name)
                counter = counter + 1

            curve = np.int32(curve)

            curve[:, 0] = curve[:, 0] - working_area[1]
            curve[:, 1] = curve[:, 1] - working_area[0]

            curve = curve.reshape((-1, 1, 2))
            mask = cv2.polylines(mask, pts=[curve], isClosed=False, color=color,
                                 thickness=self.scribbles.size[i], lineType=cv2.LINE_8)

        mask = np.uint8(mask)

        markers = np.zeros((working_area[3], working_area[2]), dtype='int32')
        for label in self.scribbles.label:
            col = label.fill
            b = col[2]
            g = col[1]
            r = col[0]
            color_code = b + 256 * g + 65536 * r
            color_key = str(color_code)

            idx = np.where((mask[:, :, 0] == b) & (mask[:, :, 1] == g) & (mask[:, :, 2] == r))
            (value, name) = color_codes[color_key]
            markers[idx] = value

        # markers = np.int32(255*rgb2gray(mask))
        # markersprint = 255*rgb2gray(mask)
        markersprint = markers
        cv2.imwrite('mask.png', markersprint)

        # watershed segmentation
        segmentation = cv2.watershed(crop_imgnp, markers)
        segmentation = filters.median(segmentation, disk(5), mode="mirror")
        cv2.imwrite('segmentation.png', segmentation)

        # the result of the segmentation must be converted into labels again
        lbls = measure.label(segmentation)

        blobs = []
        for region in measure.regionprops(lbls):
            blob = Blob(region, working_area[1], working_area[0], self.viewerplus.annotations.getFreeId())
            color_index = segmentation[region.coords[0][0], region.coords[0][1]]
            data = list(color_codes.items())
            index = 0
            for i in range(len(data)):
                (color_code, t) = data[i]
                if t[0] == color_index:
                    color_code = int(color_code)
                    r = int(color_code / 65536)
                    g = int(int(color_code - r * 65536) / 256)
                    b = int(color_code - r * 65536 - g * 256)
                    color = [r, g, b]
                    name = t[1]
                    break

            blob.class_name = name

            blobs.append(blob)

        return blobs

    def leftReleased(self, x, y):
        pass

        # for blob in self.current_blobs:
        #     self.viewerplus.removeBlob(blob)
        #
        # self.current_blobs = self.segmentation()
        #
        # for blob in self.current_blobs:
        #     self.viewerplus.addBlob(blob)

    def apply(self):

        if len(self.scribbles.points) == 0:
            self.infoMessage.emit("You need to draw something for this operation.")
            return

        blobs = self.segmentation()

        for blob in blobs:
            self.viewerplus.addBlob(blob)
            
        self.viewerplus.resetTools()
