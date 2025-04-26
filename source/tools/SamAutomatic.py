import numpy as np
import torch
import matplotlib.pyplot as plt
import cv2
import sys
import os
from skimage import measure
from PyQt5.QtCore import Qt, pyqtSignal
from source.Mask import paintMask, jointBox, jointMask, replaceMask, checkIntersection, intersectMask
from source.genutils import qimageToNumpyArray, cropQImage
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
from segment_anything.utils.amg import build_all_layer_point_grids
import time

class SamAuto(Tool):

    samEnded = pyqtSignal()
    

    def __init__(self, viewerplus, pick_points):
        super(SamAuto, self).__init__(viewerplus)

        # self.viewerplus.mouseMoved.connect(self.handlemouseMove)

        #1024x1024 rect_item size
        self.width = 1024
        self.height = 1024

        self.rect_item = None

        self.seed_nr = 0
        self.not_overlapping = []
        
        message = "<p><i>Automatic segmentation of all instances in a work-area</i></p>"
        message += "<p><b>STEP 1</b>: Choose the work-area:<br/>\
                    - CTRL + LMB: drag on the map to set the area<br/></p>"
        message += "<p><b>STEP 2</b>: Set seeds:<br/>\
                    - SHIFT + WHEEL to change the spacing</p>"
        message += "SPACEBAR to apply segmentation</p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'
       

        """
         Sam parameters: 
            pred_iou_thresh (float): A filtering threshold in [0,1], using the model's predicted mask quality.
            stability_score_thresh (float): A filtering threshold in [0,1], using the stability of the mask under changes to the cutoff used to binarize  the model's mask predictions.
            stability_score_offset (float): The amount to shift the cutoff when calculated the stability score.
            box_nms_thresh (float): The box IoU cutoff used by non-maximal suppression to filter duplicate masks.
        
        """

        #add working area
         # User defined points
        self.pick_points = pick_points

        self.work_area_item = None
        self.work_area_rect = None
        self.work_area_set = False
        self.shadow_item = None

        self.image_cropped = None
        self.image_cropped_np = None
        
        self.work_points = []
        self.num_points = 32

        self.CROSS_LINE_WIDTH = 2
        self.work_pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.cyan, 'size': 8}
        self.pos_pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.green, 'size': 4}
        self.increase = 5

        self.sam_net = None
        self.device = None
        self.created_blobs = []

    def leftReleased(self, x, y):
        try:
            self.rect_item = self.viewerplus.dragSelectionRect

            # if mods == Qt.ShiftModifier:        
            if not self.work_area_set:
                self.setWorkArea()
                self.pick_points.reset()
                self.setWorkPoints(increase = self.increase)
            else:
                self.reset()

        except Exception as e:
            pass

    
    def setWorkArea(self):
        
	    # print("Set the work area based on the location of points")
		
        # Display to GUI

        # print("setWorkArea")
        brush = QBrush(Qt.NoBrush)
        pen = QPen(Qt.DashLine)
        pen.setWidth(2)
        pen.setColor(Qt.white)
        pen.setCosmetic(True)

        # From the current view, crop the image
        # Get the bounding rect of the work area and its position
        rect = self.rect_item.boundingRect()
        self.work_area_rect = self.viewerplus.scene.addRect(rect, pen, brush)

        pos = self.rect_item.pos()      
        # rect.moveTopLeft(pos)
        rect = rect.normalized()
        rect = rect.intersected(self.viewerplus.sceneRect())
        self.work_area_rect.setPos(pos)

        self.work_area_item = rect

        # offset = self.work_area_rect.pos()
        self.offset = [self.rect_item.rect().x(), self.rect_item.rect().y()]
        print(f"offset is {self.offset}")

        image_cropped = self.viewerplus.img_map.copy(rect.toRect())
        
        # Crop the image based on the work area
        self.image_cropped = image_cropped

        # Save the cropped image
        # image_cropped.save("cropped_image.png")
        
        self.image_cropped_np = qimageToNumpyArray(image_cropped)
        # self.viewerplus.scene.removeItem(self.rect_item)

        # Create a semi-transparent overlay
        shadow_brush = QBrush(QColor(0, 0, 0, 75))  # Semi-transparent black
        shadow_path = QPainterPath()
        shadow_path.addRect(self.viewerplus.sceneRect())  # Cover the entire scene
        shadow_path.addRect(rect)  # Add the work area rect

        # Subtract the work area from the overlay
        shadow_path = shadow_path.simplified()

        # Add the overlay to the scene
        self.shadow_item = self.viewerplus.scene.addPath(shadow_path, QPen(Qt.NoPen), shadow_brush)

        self.work_area_set = True

    def divideImage(self, image):
        # Divide the image into chunks of 1024x1024
        chunks = []
        h = image.height()
        w = image.width()
        chunk_size = 1024
        overlap = 200

        try:
            for y in range(0, h, chunk_size - overlap):
                for x in range(0, w, chunk_size - overlap):
                    # Calculate the region of interest
                    rect = QRectF(x, y, chunk_size, chunk_size).intersected(QRectF(0, 0, w, h))
                    # if rect.width() >= 512 and rect.height() >= 512:  # Ensure minimum chunk size
                    chunk = image.copy(rect.toRect())
                    
                    # VISUALIZATION: Save the chunk as a .png file
                    # chunk.save(f"chunk_{x}_{y}.png")
                    
                    chunks.append((chunk, (x, y)))  # Store the chunk and its top-left offset
        except Exception as e:
            print(f"Error dividing image: {e}")
            return

        return chunks
    
    def increasePoint(self, delta):
        #increase value got from delta angle of mouse wheel
        increase = int(delta.y())/100
        # print(f'increase is {increase}')
                
        #set increase or decrease value on  wheel rotation direction
        if 0.0 < increase < 1.0:
            increase = 10
        elif -1.0 < increase < 0.0:
            increase = -10

        self.increase = increase
        print(f'self.increase is {self.increase}')
        self.setWorkPoints(self.increase)

    def setWorkPoints(self, increase = 0):

        # Reset the current points shown
        self.pick_points.reset()

        # Change the number of points to display
        self.num_points += increase
        if self.num_points < 2:
            self.num_points = 2
        elif self.num_points > 64:
            self.num_points = 64

        # Get the updated number of points
        x_pts, y_pts = build_all_layer_point_grids(self.num_points, 0, 1)[0].T

        left = self.work_area_item.left()
        top = self.work_area_item.top()

        # Change coordinates to match viewer
        x_pts = (x_pts * self.image_cropped_np.shape[1]) + left
        y_pts = (y_pts * self.image_cropped_np.shape[0]) + top

        # Add all of them to the list
        for x, y in list(zip(x_pts, y_pts)):
            self.pick_points.addPoint(x, y, self.pos_pick_style)

    def loadNetwork(self):

        if self.sam_net is None:

            self.infoMessage.emit("Loading SAM network..")
            # add choices related to GPU MEMORY

            sam_checkpoint = "sam_vit_h_4b8939.pth"
            model_type = "vit_h"

            models_dir = "models/"
            network_name = os.path.join(models_dir, sam_checkpoint)

            if not torch.cuda.is_available():
                print("CUDA NOT AVAILABLE!")
                device = torch.device("cpu")
            else:
                device = torch.device("cuda")

            self.device = device
            self.sam_net = sam_model_registry[model_type](checkpoint=network_name)
            self.sam_net.to(device=self.device)

        return True       

    #remove blobs on the edge of the rectangle cursor
    def removeGlobalEdgeBlobs(self):

        if self.work_area_rect is None:
            return

        # Get the bounding rect of the rectangle and its position
        rect = self.rect_item.rect()
        # rect.moveTopLeft(self.work_area_rect.pos())
        rect = rect.normalized()

        print(f"rect coordinates are {rect.left(), rect.right(), rect.top(), rect.bottom()}")


        # margin to consider the edge TO FINETUNE!!!!
        margin = 10  
        
        # filtered_blobs = []
        blobs = self.created_blobs.copy()
        for blob in blobs:

            bbox = blob.bbox
            top = bbox[0]
            left = bbox[1]
            right = bbox[1] + bbox[2]
            bottom = bbox[0] + bbox[3]
            
            #remove blobs if they are on the edges
            if  (
                left - rect.left() < margin or
                rect.right() - right < margin or
                top - rect.top() < margin or
                rect.bottom() - bottom < margin
            ):
                self.created_blobs.remove(blob)   
    
    def removeEdgeBlobs(self,blobs,x_offset, y_offset):        
        rect = QRectF(x_offset, y_offset, 1024, 1024)
        rect = rect.normalized()
        
        # VISUALIZATION: Draw only the rectangle on the map in black        
        # pen = QPen(Qt.black)
        # pen.setWidth(2)
        # rect = QRectF(x_offset, y_offset, 1024, 1024)
        # self.viewerplus.scene.addRect(rect, pen)

        print(f"rect coordinates are {rect.left(), rect.right(), rect.top(), rect.bottom()}")

        # margin to consider the edge TO FINETUNE!!!!
        margin = 10  
        
        # filtered_blobs = []
        # blobs = self.created_blobs.copy()
        copied = blobs.copy()
        for blob in copied:

            bbox = blob.bbox
            top = bbox[0]
            left = bbox[1]
            right = bbox[1] + bbox[2]
            bottom = bbox[0] + bbox[3]
            
            #remove blobs if they are on the edges
            if  (
                left - rect.left() < margin or
                rect.right() - right < margin or
                top - rect.top() < margin or
                rect.bottom() - bottom < margin
            ):
                blobs.remove(blob)    

    def reset(self):

        torch.cuda.empty_cache()
        if self.sam_net is not None:
            del self.sam_net
            self.sam_net = None
        
        self.image_cropped = None

        self.work_area_set = False
        self.work_area_item = None
        #  VISUALIZATION: Remove the rectangle on the map
        self.viewerplus.scene.removeItem(self.work_area_rect)
        self.work_area_rect = None
        
        if self.shadow_item is not None:
            self.viewerplus.scene.removeItem(self.shadow_item)
            self.shadow_item = None
        
        self.pick_points.reset()

        # self.viewerplus.scene.addItem(self.rect_item)
        
    def apply(self):
        
        self.viewerplus.resetSelection()

        print(f"number of sam_seed is {self.num_points}")

        image_chunks = self.divideImage(self.image_cropped)

        try:
        # Perform segmentation on the cropped image
            # self.segment(self.image_cropped, self.num_points)
            for chunk, (x_offset, y_offset) in image_chunks:
                print(x_offset, y_offset)
                self.segment(chunk, x_offset, y_offset, self.num_points)
        except Exception as e:
            if not self.work_area_set:
                print("Work area is not set. Please define the work area before segmentation.")
                # box = QMessageBox()
                # box.setIcon(QMessageBox.Critical)
                # box.setText("Working area is not set.\nPlease define the working area before segmentation.")
                # box.setWindowTitle("No Working Area")
                # box.setStandardButtons(QMessageBox.Ok)	
                # box.exec()
                QMessageBox.critical(None, "Error", f"Working area is not set.\nPlease define the working area before segmentation.")
            else:
                print(f"Segmentation failed: {e}")

        # for blob in self.created_blobs:
        #     self.viewerplus.addBlob(blob, selected=True)

        # self.viewerplus.saveUndo()
        # self.created_blobs = []
        # self.samEnded.emit()
        
        self.removeBlobs()
        self.viewerplus.resetTools()

    def segment(self, image, x_off, y_off, seed = 32, save_status=True):

        self.infoMessage.emit("Segmentation is ongoing..")
        self.log.emit("[TOOL][SAM] Segmentation begins..")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        if not self.loadNetwork():
            return

        QApplication.restoreOverrideCursor()

        mask_generator = SamAutomaticMaskGenerator(
            model=self.sam_net,

            # points_per_side = seed,
            points_per_side= seed,
            
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

        print(x_off, y_off)
        global_offx = self.offset[0]
        global_offy = self.offset[1]
        created = []
        for mask in masks:
            bbox = mask["bbox"]
            bbox = [int(value) for value in bbox]
            segm_mask = mask["segmentation"].astype('uint8')*255
            segm_mask_crop = segm_mask[bbox[1]:bbox[1]+bbox[3], bbox[0]:bbox[0]+bbox[2]]
            blob = self.viewerplus.image.annotations.createBlobFromSingleMask(segm_mask_crop, bbox[0] + global_offx + x_off, bbox[1] + global_offy + y_off)
            # self.created_blobs.append(blob)
            created.append(blob)

        print(f"number of blobs created is {len(created)}")

        self.removeEdgeBlobs(created, global_offx+x_off, global_offy+y_off)
        print(f"number of blobs created after removeEdge is {len(created)}")
        self.created_blobs.extend(created)
        print(f"number of appended blobs created is {len(self.created_blobs)}")

    def removeBlobs(self):
        try:
            print(f"self.created_blob len pre is {len(self.created_blobs)}")
            genutils.removeOverlapping(self.created_blobs, self.created_blobs)
            print(f"self.created_blob len post is {len(self.created_blobs)}")
            self.removeGlobalEdgeBlobs()
            print(f"self.created_blob len post removeEdge is {len(self.created_blobs)}")
            print(f"Number of yet annotated blobs is {len(self.viewerplus.image.annotations.seg_blobs)}")

            genutils.removeOverlapping(self.created_blobs, self.viewerplus.image.annotations.seg_blobs, annotated = True)

            print(f"self.created_blob len post annotated is {len(self.created_blobs)}")
        
        except Exception as e:
            print(f"Error removing blobs: {e}")
            # QMessageBox.critical(None, "Error", f"Error removing blobs: {e}")
            return
            
        for blob in self.created_blobs:
            self.viewerplus.addBlob(blob, selected=True)

        self.viewerplus.saveUndo()
        self.created_blobs = []
        self.samEnded.emit()

#####################################################################################

    #removeOverlapping for SAM and other tools
    # def removeOverlap(self, created_first, created_last):
            
    #     blobs = created_first.copy()

    #     widths = []
    #     heights = []
    #     for blob in blobs:
    #         widths.append(blob.bbox[2])
    #         heights.append(blob.bbox[3])

    #     widths = np.asarray(widths)
    #     heights = np.asarray(heights)
    #     medianw = np.median(widths)
    #     medianh = np.median(heights)

    #     # not_overlapping = []
    #     for blob in blobs:

    #         if blob not in created_first:
    #             continue

    #         bbox = blob.bbox
    #         mask = blob.getMask()
    #         npixel = np.count_nonzero(mask)

    #         intersected_blobs = []

    #         for blob2 in created_last:
    #             if blob != blob2 and checkIntersection(bbox, blob2.bbox) is True:
    #                 mask2 = blob2.getMask()
    #                 npixel2 = np.count_nonzero(mask2)
    #                 (imask, ibbox) = intersectMask(mask, bbox, mask2, blob2.bbox)
    #                 npixeli = np.count_nonzero(imask)

    #                 overlap12 = npixeli / npixel
    #                 overlap21 = npixeli / npixel2

    #                 remove created_blob if in overlapping with seg_blobs
    #                 if annotated == True:
    #                     # overlap = overlap12

    #                     if overlap12 > 0.0:
    #                         intersected_blobs.append(blob2)

    #                     num_intersections = len(intersected_blobs)

    #                     if num_intersections > 0:
    #                         intersected_blobs.append(blob)

    #                         for blobO in intersected_blobs:     
    #                             if blobO in created:
    #                                 created.remove(blobO)                    
                    
    #                 #remove created_blobs in overlapping with themselves (bigger is better)
    #                 else:

    #                     overlap = max(overlap12, overlap21)

    #                     if overlap > 0.10:
    #                         intersected_blobs.append(blob2)

    #                     num_intersections = len(intersected_blobs)

    #                     if num_intersections > 0:
    #                         intersected_blobs.append(blob)

    #                         #using inf instead of hard coded value works better
    #                         # diff_min = 10000000
    #                         diff_min = float('inf') 
    #                         blob_to_keep = None
    #                         for blobO in intersected_blobs:
    #                             diff = abs(blobO.bbox[2] - medianw) + abs(blobO.bbox[3] - medianh)
    #                             if diff < diff_min:
    #                                 diff_min = diff
    #                                 blob_to_keep = blobO

                            
    #                         for blobO in intersected_blobs:
    #                             if blobO != blob_to_keep:
    #                                     if blobO in created:
    #                                         created.remove(blobO)
                        
    #                     if overlap12 > 0.0:
    #                         intersected_blobs.append(blob2)
