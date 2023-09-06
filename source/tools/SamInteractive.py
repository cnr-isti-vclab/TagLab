from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPen, QBrush

import cv2

from source.tools.Tool import Tool
from source.tools.PickPoints import PickPoints
from source import genutils
from source.tools import utils

from skimage.transform import rescale

import os
import numpy as np

try:
    import torch
    from torch.nn.functional import interpolate
except Exception as e:
    print("Incompatible version between pytorch, cuda and python.\n" +
          "Knowing working version combinations are\n: Cuda 10.0, pytorch 1.0.0, python 3.6.8" + str(e))


from models.dataloaders import helpers as helpers
from collections import OrderedDict
from segment_anything import sam_model_registry, SamPredictor

from PIL import Image

import time

class SamInteractive(Tool):
    def __init__(self, viewerplus, corrective_points):
        super(SamInteractive, self).__init__(viewerplus)

        """
        
        Points are placed by pressing shift
        
        Bbox annotation:
        
       The box is provided in xyxy format.
        
        Point annotation:
        
        - Points are input to the model in (x,y) format and come with labels 1 (foreground point) or 0 (background point).
        - With multimask_output=True (the default setting), SAM outputs 3 masks, where scores gives the model's own estimation of the quality of these masks.
        When False, it will return a single mask. For ambiguous prompts such as a single point, it is recommended to use multimask_output=True even if only a 
        single mask is desired; The best single mask can be chosen by picking the one with the highest score returned in scores. 
         
         """

        self.pos_neg_points = corrective_points
        self.bbox_points = PickPoints(None)
        self.scene = viewerplus.scene
        self.selected_area_rect = None

        self.sam_net = None
        self.network_used = "SAM"
        self.predictor = None
        self.device = None
        self.masks = None
        self.area_bbox = 0
        self.blobs = None


    def leftPressed(self, x, y, mods):

        if mods == Qt.ShiftModifier:
            self.pos_neg_points.addPoint(x, y, positive=True)
            self.segment()
        else:
            points = self.bbox_points

            # first point
            if len(points.points) != 0 and mods != Qt.ShiftModifier:
                self.bbox_points.reset()
                self.undrawAll()

            self.bbox_points.points.append(np.array([x, y]))
            self.bbox_points.points.append(np.array([x, y]))

    def rightPressed(self, x, y, mods = None):

        if mods == Qt.ShiftModifier:
            self.pos_neg_points.addPoint(x, y, positive=False)
            self.segment()

    def leftReleased(self, x, y):

        # if the bbox is valid the segmentation is launched
        if len(self.bbox_points.points) == 2:
            x, y, w, h = self.fromPointsToArea()
            if w > 20 and h > 20:
                self.segment()

    def fromPointsToArea(self):
        """
        It transforms the bbox points into the selected area.
        """

        p1 = self.bbox_points.points[0]
        p2 = self.bbox_points.points[1]

        x = min(p1[0], p2[0])
        y = min(p1[1], p2[1])
        w = abs(p2[0] - p1[0])
        h = abs(p2[1] - p1[1])

        return x, y, w, h

    def drawArea(self):

        x, y, w, h = self.fromPointsToArea()

        area_style = QPen(Qt.white, 3, Qt.DashLine)
        area_style.setCosmetic(True)

        if self.selected_area_rect is None:
            self.selected_area_rect = self.scene.addRect(x, y, w, h, area_style)
            self.selected_area_rect.setZValue(6)
            self.selected_area_rect.setVisible(True)
        else:
            self.selected_area_rect.setRect(x, y, w, h)

    def mouseMove(self, x, y):

        if len(self.bbox_points.points) > 0:
            self.bbox_points.points[1][0] = x
            self.bbox_points.points[1][1] = y

            # draw the selected area
            self.drawArea()

    def loadNetwork(self):

        # DECIDIAMO DI CARICARE I MODELLI PIù LIGHT? NON VAN BENISSIMO, DA PROVARE

        if self.sam_net is None:

            models_dir = "models/"
            sam_checkpoint = "sam_vit_h_4b8939.pth"
            model_type = "vit_h"
            network_name = os.path.join(models_dir, sam_checkpoint)

            if torch.cuda.is_available():
                (total_gpu_memory, global_free_gpu_memory) = torch.cuda.mem_get_info()
                GPU_MEMORY_GIGABYTES = total_gpu_memory/(1024*1024*1024)
                print(GPU_MEMORY_GIGABYTES)
                if GPU_MEMORY_GIGABYTES > 6.0:
                    self.device = "cuda"
                else:
                    print("NOT ENOUGH CUDA MEMORY, SWITCH TO CPU")
                    self.device = "cpu"
            else:
                print("CUDA NOT AVAILABLE!")
                self.device = "cpu"

            self.sam_net = sam_model_registry[model_type](checkpoint=network_name)
            self.sam_net.to(device=self.device)
            self.predictor = SamPredictor(self.sam_net)

    def segment(self):

        if len(self.bbox_points.points) < 2:
            return

        points = self.bbox_points.points
        x = []
        y = []
        for point in points:
            x.append(point[0])
            y.append(point[1])

        x1 = min(x)
        x2 = max(x)
        y1 = min(y)
        y2 = max(y)

        xc = int((x1 + x2) / 2)
        yc = int((y1 + y2) / 2)

        if (x2-x1) < 10 or (y2-y1) < 10:
            return

        print(x2-x1, y2-y1)

        scale_factor = 1.0
        if (x2-x1) > 1024 and (y2-y1) <= 1024:

            scale_factor = 1024.0 / float(x2-x1)
            hprime = int(1024.0 / scale_factor)

            crop_image = genutils.cropQImage(self.viewerplus.img_map, [yc-int(hprime/2), x1, x2-x1, hprime])
            scaled_image = crop_image.scaled(1024, 1024, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            input_box = np.array([0, y1 - yc+int(hprime/2), 1024, int((y2-y1)*scale_factor)])
            self.offx = x1
            self.offy = yc-int(hprime/2)

            input_image = genutils.qimageToNumpyArray(scaled_image)

        elif (x2-x1) <= 1024 and (y2-y1) > 1024:

            scale_factor = 1024.0 / float(y2-y1)
            wprime = int(1024.0 / scale_factor)

            crop_image = genutils.cropQImage(self.viewerplus.img_map, [y1, xc-int(wprime/2), wprime, y2-y1])
            scaled_image = crop_image.scaled(1024, 1024, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            input_box = np.array([x1 - xc+int(wprime/2), 0, int((x2-x1)*scale_factor), 1024])
            self.offx = xc-int(wprime/2)
            self.offy = y1

            input_image = genutils.qimageToNumpyArray(scaled_image)

        elif (x2-x1) > 1024 and (y2-y1) > 1024:

            scale_factor = 1024.0 / float(max((y2-y1), (x2-x1)))
            hprime = int((y2-y1) * scale_factor)
            wprime = int((x2-x1) * scale_factor)

            crop_image = genutils.cropQImage(self.viewerplus.img_map, [y1, x1, x2-x1, y2-y1])
            scaled_image = crop_image.scaled(wprime, hprime, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            input_box = np.array([0, 0, wprime, hprime])
            self.offx = x1
            self.offy = y1

            input_image = genutils.qimageToNumpyArray(scaled_image)

        else:
            # bbox is small -> input image is centered on the center of the bbox
            crop_image = genutils.cropQImage(self.viewerplus.img_map, [yc-512, xc-512, 1024, 1024])
            input_box = np.array([x1 - xc + 512, y1 - yc + 512, x2 - xc + 512, y2 - yc + 512])
            self.offx = xc - 512
            self.offy = yc - 512
            input_image = genutils.qimageToNumpyArray(crop_image)

        QApplication.setOverrideCursor(Qt.WaitCursor)

        # load network if necessary
        self.loadNetwork()

        Image.fromarray(input_image).save("input.png")

        self.predictor.set_image(input_image, "RGB")

        if len(self.pos_neg_points.positive_points) > 0 or len(self.pos_neg_points.negative_points) > 0:

            nclicks = self.pos_neg_points.nclicks()

            points_coords = np.zeros((nclicks,2))
            points_labels = np.zeros((nclicks))

            i = 0
            for point in self.pos_neg_points.positive_points:
                points_coords[i][0] = point[0] - self.offx
                points_coords[i][1] = point[1] - self.offy
                points_labels[i] = 1
                i = i + 1

            for point in self.pos_neg_points.negative_points:
                points_coords[i][0] = point[0] - self.offx
                points_coords[i][1] = point[1] - self.offy
                points_labels[i] = 0
                i = i + 1
        else:

            points_coords = None
            points_labels = None

        self.masks, _, _ = self.predictor.predict(
            point_coords=points_coords,
            point_labels=points_labels,
            box=input_box[None, :],
            multimask_output=False
        )

        self.area_bbox = (x2-x1) * (y2-y1)

        self.viewerplus.resetSelection()
        for i in range(self.masks.shape[0]):
            mask = self.masks[i,:,:]
            segm_mask = mask.astype('uint8')*255

            filename = "mask" + str(i) + ".png"
            Image.fromarray(segm_mask).save(filename)

            segm_mask = rescale(segm_mask, scale_factor)

            self.blobs = self.viewerplus.annotations.blobsFromMask(segm_mask, self.offx, self.offy, self.area_bbox)

            scene = self.viewerplus.scene
            brush = QBrush(Qt.SolidPattern)
            brush.setColor(Qt.white)
            for blob in self.blobs:
                utils.drawBlob(blob, brush, scene, self.viewerplus.transparency_value, redraw=False)
            scene.invalidate()

        QApplication.restoreOverrideCursor()

    def apply(self):
        """
        Confirm the results of the segmentation.
        """

        self.viewerplus.resetSelection()
        for blob in self.blobs:
            utils.undrawBlob(blob, self.viewerplus.scene, redraw=False)
            self.viewerplus.addBlob(blob, selected=True)
            self.blobInfo.emit(blob, "[TOOL][DEEPEXTREME][BLOB-CREATED]")

        self.viewerplus.saveUndo()
        self.infoMessage.emit("Segmentation done.")

        if self.selected_area_rect:
            self.scene.removeItem(self.selected_area_rect)
            self.selected_area_rect = None
        self.bbox_points.reset()
        self.pos_neg_points.reset()
        self.blobs = None

        self.viewerplus.scene.invalidate()

    def resetNetwork(self):

        torch.cuda.empty_cache()

        if self.sam_net is not None:
            del self.sam_net
            self.sam_net = None
            del self.predictor
            self.predictor = None

    def undrawAll(self):

        utils.undrawAllBlobs(self.blobs, self.scene)

        self.scene.removeItem(self.selected_area_rect)
        self.selected_area_rect = None

    def reset(self):

        self.resetNetwork()
        self.undrawAll()
        self.bbox_points.reset()
        self.pos_neg_points.reset()

