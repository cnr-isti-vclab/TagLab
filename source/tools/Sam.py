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

        #QUIRINO: 1024x1024 windows size for SAM segmentation
        self.window_size = 1024

        # scale factor of the cursor
        self.scale_factor = 1.0

        self.setCustomCursor()

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

    def setCustomCursor(self):

        # window_size = 1024
        # window_size = 100
        #QUIRINO: rescaled to scale_factor of windows_size
        resized_window_size = int(self.window_size * self.scale_factor)

        #QUIRINO: if window_size is > cursor_size(10) create a QPixmap of window_size dimension
        
        pxmap = QPixmap(resized_window_size, resized_window_size)
        # pxmap = QPixmap(self.current_size, self.current_size)
    
        pxmap.fill(QColor("transparent"))
        painter = QPainter(pxmap)
        # color = self.current_label.fill
        
        print(f"self.current_size is {self.window_size}")
        print(f"window_size is {resized_window_size}")   

        
        window = QPen(QColor(0,0,0),5, Qt.DotLine)
        painter.setPen(window)
        painter.drawRect(0, 0, resized_window_size, resized_window_size)

        #QUIRINO: brush in the middle of the window
        center_size = 8
        center = QBrush(QColor(0,0, 200))
        painter.setBrush(center)
        painter.drawEllipse(resized_window_size/2-4, resized_window_size/2-4, center_size, center_size)
    
        painter.end()
        custom_cursor = QCursor(pxmap)
        QApplication.setOverrideCursor(custom_cursor)

    def setScaleFactor(self, scale_factor):

        self.scale_factor = scale_factor

    def setSize(self, delta_size = 0):

        new_size = self.window_size + delta_size

        self.window_size = new_size
        self.setCustomCursor()
    
    
    def leftPressed(self, x, y, mods):
        # QUIRINO: Get the coordinates of the custom cursor area
        cursor_x = x - self.window_size // 2
        cursor_y = y - self.window_size // 2

        # QUIRINO: Crop the image inside the custom cursor area, always 1024x1024 px image
        cursor_image = self.viewerplus.img_map.copy(cursor_x, cursor_y, 1024, 1024)

        # QUIRINO: Save the cropped image as crop.png
        cursor_image.save("crop_SAM.png")

        self.segment(cursor_image)
        
        # self.segment()
        # fa schifo così, pensare a widget?

    def segment(self, cursor_image, save_status=True):

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

        image = genutils.qimageToNumpyArray(cursor_image)
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
