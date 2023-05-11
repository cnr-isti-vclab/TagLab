from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QImage, QPen


import cv2

from source.tools.Tool import Tool
from source.tools.PickPoints import PickPoints
from source import utils

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

import time

class SamInteractive(Tool):
    def __init__(self, viewerplus, pick_points):
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
        # variables for bbox

        self.picked_points = pick_points
        self.picked_bbox_points = PickPoints(None)
        self.scene = viewerplus.scene
        self.selected_area_rect = None
        self.image_width = 0
        self.image_height = 0



        self.sam_net = None
        self.network_used = "SAM"
        self.predictor = None
        self.device = None


    def leftPressed(self, x, y, mods):

        points = self.picked_bbox_points

        # first point
        if len(points.points) != 0:
            self.picked_bbox_points.reset()
            self.selected_area_rect = None

        self.picked_bbox_points.points.append(np.array([x, y]))
        self.picked_bbox_points.points.append(np.array([x, y]))

    def leftReleased(self, x, y):

        self.segment()


    def fromPointsToArea(self):
        """
        It transforms the picked points into the selected area.
        """

        p1 = self.picked_bbox_points.points[0]
        p2 = self.picked_bbox_points.points[1]

        x = min(p1[0], p2[0])
        y = min(p1[1], p2[1])
        w = abs(p2[0] - p1[0])
        h = abs(p2[1] - p1[1])

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x + w > self.image_width:
            w = self.image_width - x
        if y + h > self.image_height:
            h = self.image_height - y

        return x, y, w, h

    #
    # def setWorkingAreaStyle(self, pen):
    #
    #     self.working_area_style = pen
    #
    # def setAreaStyle(self):
    #
    #     self.area_style = QPen(Qt.white, 3, Qt.DashLine)
    #     self.area_style.setCosmetic(True)

    def drawArea(self):

        x, y, w, h = self.fromPointsToArea()

        self.area_style = QPen(Qt.white, 3, Qt.DashLine)
        self.area_style.setCosmetic(True)

        if self.selected_area_rect is None:
            self.selected_area_rect = self.scene.addRect(x, y, w, h, self.area_style)
            self.selected_area_rect.setZValue(6)
            self.selected_area_rect.setVisible(True)

            self.picked_bbox_points.markers.append(self.selected_area_rect)
        else:
            self.selected_area_rect.setRect(x, y, w, h)


    def mouseMove(self, x, y):

        if len(self.picked_bbox_points.points) > 0:
            self.picked_bbox_points.points[1][0] = x
            self.picked_bbox_points.points[1][1] = y
            # draw the selected area
            self.drawArea()


    def reset(self):
        self.picked_bbox_points.reset()
        self.selected_area_rect = None


    def loadNetwork(self):

        """"""
        # DECIDIAMO DI CARICARE I MODELLI PIù LIGHT? NON VAN BENISSIMO, DA PROVARE

        models_dir = "models/"
        sam_checkpoint = "sam_vit_h_4b8939.pth"
        model_type = "vit_h"
        network_name = os.path.join(models_dir, sam_checkpoint)

        if torch.cuda.is_available() > 7.0:
            (total_gpu_memory, global_free_gpu_memory) = torch.cuda.mem_get_info()
            GPU_MEMORY_GIGABYTES = total_gpu_memory/(1024*1024*1024)
            if GPU_MEMORY_GIGABYTES > 7.0:
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



    # def leftPressed(self, x, y, mods):
    #
    #     points = self.pick_points.points
    #
    #     if len(points) < 4 and mods == Qt.ShiftModifier:
    #         self.pick_points.addPoint(x, y, self.pick_style)
    #         message = "[TOOL][DEEPEXTREME] New point picked (" + str(len(points)) + ")"
    #         self.log.emit(message)
    #
    #     # APPLY DEEP EXTREME
    #     if len(points) == 4:
    #
    #         if self.network_used == "SAM":
    #             self.segmentWithSAM()
    #         else:
    #             self.segmentWithDeepExtreme()
    #
    #         self.pick_points.reset()
    #
    def segment(self):

        # load network if necessary
        self.loadNetwork()
        points = self.picked_bbox_points.points
        x = []
        y = []
        for point in points:
            x.append(point[0])
            y.append(point[1])

        x1 = min(x)
        x2 = max(x)
        y1 = min(y)
        y2 = max(y)

        if (x2-x1) > 1024 or (y2-y1) > 1024:
            crop_image = utils.cropQImage(self.viewerplus.img_map, [y1, x1, x2-x1, y2-y1])
            input_box = np.array([0, 0, x2-x1, y2-y1])
            offx = x1
            offy = y1

        else:
            xc = int((x1 + x2) / 2)
            yc = int((y1 + y2) / 2)
            crop_image = utils.cropQImage(self.viewerplus.img_map, [yc-512, xc-512, 1024, 1024])
            input_box = np.array([x1 - xc + 512, y1 - yc + 512, x2 - xc + 512, y2 - yc + 512])
            offx = xc - 512
            offy = yc - 512

        crop_image.save("crop.png")
        input_image = utils.qimageToNumpyArray(crop_image)

        self.predictor.set_image(input_image, "RGB")

        masks, _, _ = self.predictor.predict(
            point_coords=None,
            point_labels=None,
            box=input_box[None, :],
            multimask_output=False
        )

        area_extreme_points = (x2-x1) * (y2-y1)

        from PIL import Image
        self.viewerplus.resetSelection()
        for i in range(masks.shape[0]):
            mask = masks[i,:,:]
            segm_mask = mask.astype('uint8')*255

            pil_img = Image.fromarray(segm_mask, "L")
            filename = "mask " + str(i) + ".png"
            pil_img.save(filename)

            blobs = self.viewerplus.annotations.blobsFromMask(segm_mask, offx, offy, area_extreme_points)

            for blob in blobs:
                self.viewerplus.addBlob(blob, selected=True)
                self.blobInfo.emit(blob, "[TOOL][DEEPEXTREME][BLOB-CREATED]")

        self.viewerplus.saveUndo()
        self.infoMessage.emit("Segmentation done.")



    def resetNetwork(self):

        torch.cuda.empty_cache()

        if self.sam_net is not None:
            del self.sam_net
            self.sam_net = None
            del self.predictor
            self.predictor = None

    def reset(self):
        self.resetNetwork()
        self.picked_bbox_points.reset()

