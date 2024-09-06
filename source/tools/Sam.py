import numpy as np
import torch
import matplotlib.pyplot as plt
import cv2
import sys
import os
from skimage import measure
from PyQt5.QtCore import Qt, pyqtSignal
from source.Mask import paintMask, jointBox, jointMask, replaceMask, checkIntersection, intersectMask
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QPen, QBrush
from source import genutils
from source.tools.Tool import Tool
from source.Blob import Blob

from PyQt5.QtCore import Qt, QObject, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QBrush, QCursor, QColor
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsItem, QGraphicsScene, QFileDialog, QGraphicsPixmapItem


sys.path.append("..")
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor
import time

class Sam(Tool):

    samEnded = pyqtSignal()

    def __init__(self, viewerplus):
        super(Sam, self).__init__(viewerplus)

        self.viewerplus.mouseMoved.connect(self.handlemouseMove)

        
        #QUIRINO: 1024x1024 rect_item size
        self.width = 1024
        self.height = 1024
        
        self.rect_item = None
        # self.rect_item = viewerplus.scene.addRect(0, 0, 2048, 2048, QPen(Qt.black, 5, Qt.DotLine)) 
        # self.center_item = viewerplus.scene.addEllipse(0, 0, 10,10, QPen(Qt.black), QBrush(Qt.red))
       

        """
         Sam parameters: 
            pred_iou_thresh (float): A filtering threshold in [0,1], using the model's predicted mask quality.
            stability_score_thresh (float): A filtering threshold in [0,1], using the stability of the mask under changes to the cutoff used to binarize  the model's mask predictions.
            stability_score_offset (float): The amount to shift the cutoff when calculated the stability score.
            box_nms_thresh (float): The box IoU cutoff used by non-maximal suppression to filter duplicate masks.
            
        IDEA: SE ZOOM LEVEL 0 ALLORA FA TUTTA IMMAGINE 
              SE ZOOM LEVEL E' X >>  1024 AVVISA CHE è GROSSA
              SE ZOMM LEVEL +- 1024 allora prende 1024
              se zoom level << 1024 sovracampiona a 1024 (lo fa lui già mi sA) E CONTA 
            
        
        """

        #add working area
        self.sam_net = None
        self.device = None
        self.created_blobs = []

    def loadNetwork(self):

        if self.sam_net is None:

            self.infoMessage.emit("Loading SAM network..")
            # add choices related to GPU MEMORY

            # sam_checkpoint = "sam_vit_b_01ec64.pth"
            # model_type = "vit_b"

            # sam_checkpoint = "sam_vit_l_0b3195.pth"
            # model_type = "vit_l"

            sam_checkpoint = "sam_vit_b_01ec64.pth"
            model_type = "vit_b"

            models_dir = "models/"
            network_name = os.path.join(models_dir, sam_checkpoint)

            #
            # if not torch.cuda.is_available():
            #     print("CUDA NOT AVAILABLE!")
            #     device = torch.device("cpu")
            # else:
            #     device = torch.device("cuda:0")

            self.device = "cuda"
            self.sam_net = sam_model_registry[model_type](checkpoint=network_name)
            self.sam_net.to(device=self.device)

            # CAPIRE DIFFERENZE DA DEMO   !!!!!!!!!!!

            # # try:
            # #     self.sam_net = genutils.load_is_model(model_path, device, cpu_dist_maps=False)
            #     self.sam_net = sam_model_registry[model_type](checkpoint=model_name)
            #     self.sam_net.to(device=self.device)


            # except Exception as e:
            #     box = QMessageBox()
            #     box.setText("Could not load Sam network. You might need to run update.py.")
            #     box.exec()
            #     return False

        return True

    # def reset(self):
    #     """
    #     Reset net, tools and wa
    #     """
    #
    #     self.resetNetwork()
    #     #self.viewerplus.resetTools()
    #     ##self.resetWorkArea()

    def reset(self):

        torch.cuda.empty_cache()
        if self.sam_net is not None:
            del self.sam_net
            self.sam_net = None
        #     #self.viewerplus.resetTools()
        #     ##self.resetWorkArea()

    def setSize(self, delta):
        #QUIRINO: increase value got from delta angle of mouse wheel
        increase = float(delta.y()) / 10.0
        
        #QUIRINO: set increase or decrease value on  wheel rotation direction
        if 0.0 < increase < 1.0:
            increase = 100
        elif -1.0 < increase < 0.0:
            increase = -100

        #QUIRINO: rescale rect_item on zoom factor from wheel event
        # added *2 to mantain rectangle inside the map
        new_width = self.width + (increase)
        new_height = self.height + (increase)
        
        #QUIRINO: limit the rectangle to 512x512 for SAM segmentation
        if new_width < 512 or new_height < 512:
            new_width = 512
            new_height = 512

        # QUIRINO: limit the rectangle to 2048x2048 for SAM segmentation
        if new_width > 2048 or new_height > 2048:
            new_width = 2048
            new_height = 2048
  
        # print(f"rect_item width and height are {new_width, new_height}")
        if self.rect_item is not None:
            self.rect_item.setRect(0, 0, new_width, new_height)

        self.width = new_width
        self.height = new_height
        
    def handlemouseMove(self, x, y):
        # print(f"Mouse moved to ({x}, {y})")
        if self.rect_item is not None:
            # self.center_item.setPos(x, y)
            self.rect_item.setPos(x- self.width//2, y - self.height//2)
            
    def leftPressed(self, x, y, mods):
        
        # QUIRINO: Crop the part of the map inside the self.rect_item area
        rect = self.rect_item.boundingRect()
        rect.moveTopLeft(self.rect_item.pos())
        rect = rect.normalized()
        rect = rect.intersected(self.viewerplus.sceneRect())
        cropped_image = self.viewerplus.img_map.copy(rect.toRect())

        cropped_image.save("crop_rect.png")
        # Perform segmentation on the cropped image
        self.segment(cropped_image)
        # pass
        
        # self.segment()
        # fa schifo così, pensare a widget?

    def segment(self, image, save_status=True):

        self.infoMessage.emit("Segmentation is ongoing..")
        self.log.emit("[TOOL][SAM] Segmentation begins..")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        if not self.loadNetwork():
            return

        QApplication.restoreOverrideCursor()

        mask_generator = SamAutomaticMaskGenerator(
            model=self.sam_net,
            points_per_side=32,
            points_per_batch=64,
            crop_n_layers = 0,
            pred_iou_thresh = 0.88,
            stability_score_thresh=  0.95,
            stability_score_offset = 1.0,
            box_nms_thresh = 0.7,
            crop_nms_thresh = 0.7,
            min_mask_region_area = 1000,
            crop_overlap_ratio = 0.34333,
            crop_n_points_downscale_factor = 1,
            output_mode = "binary_mask"
        )

        image = genutils.qimageToNumpyArray(image)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        start = time.time()

        masks = mask_generator.generate(image)

        end = time.time()

        print(end-start)

        for mask in masks:
            bbox = mask["bbox"]
            bbox = [int(value) for value in bbox]
            segm_mask = mask["segmentation"].astype('uint8')*255
            segm_mask_crop = segm_mask[bbox[1]:bbox[1]+bbox[3], bbox[0]:bbox[0]+bbox[2]]
            blob = self.viewerplus.image.annotations.createBlobFromSingleMask(segm_mask_crop, bbox[0], bbox[1])
            self.created_blobs.append(blob)
            self.viewerplus.addBlob(blob, selected=True)

        self.viewerplus.assignClass("Pocillopora")

        self.samEnded.emit()

    
    #QUIRINO: method to display the rectangle on the map
    def enable(self, enable = False):
        if enable == True:
            self.rect_item = self.viewerplus.scene.addRect(0, 0, self.width, self.height, QPen(Qt.black, 20, Qt.DotLine)) 
            # self.center_item.setVisible(True)
        else:
            if self.rect_item is not None:
                self.viewerplus.scene.removeItem(self.rect_item)
            self.rect_item = None
            # self.center_item.setVisible(False)

    #
    #
    # def drawBlobs(self):
    #
    #     for blob in self.created_blobs:
    #         self.viewerplus.addBlob(blob, selected=False)



            # # if it has just been created remove the current graphics item in order to set it again
            # if blob.qpath_gitem is not None:
            #     scene.removeItem(blob.qpath_gitem)
            #     del blob.qpath_gitem
            #     blob.qpath_gitem = None
            #
            # # custom drawing for created blobs
            #
            # blob.setupForDrawing()
            # pen = QPen(Qt.white)
            # pen.setWidth(2)
            # pen.setCosmetic(True)
            # brush = QBrush(Qt.SolidPattern)
            # brush.setColor(Qt.white)
            # brush.setStyle(Qt.Dense4Pattern)
            # blob.qpath_gitem = scene.addPath(blob.qpath, pen, brush)
            # blob.qpath_gitem.setZValue(1)
            # blob.qpath_gitem.setOpacity(self.viewerplus.transparency_value)
