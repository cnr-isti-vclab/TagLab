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
from source.genutils import qimageToNumpyArray

from source.Mask import paintMask, jointBox, jointMask, replaceMask, checkIntersection, intersectMask
from PIL import Image


import matplotlib.pyplot as plt
from scipy.ndimage import binary_dilation

from PyQt5.QtCore import Qt, QObject, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QBrush, QCursor, QColor

# from source.Label import Label

from source.QtRowsWidget import RowsWidget

class Rows(Tool):
        
    def __init__(self, viewerplus):
        super(Rows, self).__init__(viewerplus)

        # self.viewerplus.mouseMoved.connect(self.handlemouseMove)
        
        self.struct_widget = None

        #1024x1024 rect_item size
        # self.width = 1024
        # self.height = 1024

        self.offset = [0, 0]

        self.rect_item = None
        self.blobs_inside_work_area = []

        self.work_area_item = None
        self.work_area_rect = None
        self.work_area_set = False
        self.shadow_item = None

        self.image_cropped = None
        self.image_cropped_np = None

        
    # def handlemouseMove(self, x, y, mods=None):
    #     # print(f"Mouse moved to ({x}, {y})")
    #     if self.rect_item is not None:
    #         self.rect_item.setPos(x- self.width//2, y - self.height//2)

    # def setSize(self, delta, mods):
    #     #increase value got from delta angle of mouse wheel
    #     increase = float(delta.y()) / 10.0
        
    #     #set increase or decrease value on  wheel rotation direction
    #     if 0.0 < increase < 1.0:
    #         increase = 100
    #     elif -1.0 < increase < 0.0:
    #         increase = -100

    #     #rescale rect_item on zoom factor from wheel event
    #     # added *2 to mantain rectangle inside the map
    #     if mods & Qt.ShiftModifier:
    #         new_width = self.width + (increase)
    #         self.width = new_width
    #     elif mods & Qt.ControlModifier:
    #         new_height = self.height + (increase)
    #         self.height = new_height
        
    #     # #limit the rectangle to 512x512 for SAM segmentation
    #     # if new_width < 512 or new_height < 512:
    #     #     new_width = 512
    #     #     new_height = 512

    #     # # limit the rectangle to 2048x2048 for SAM segmentation
    #     # if new_width > 2048 or new_height > 2048:
    #     #     new_width = 2048
    #     #     new_height = 2048
  
    #     # print(f"rect_item width and height are {new_width, new_height}")
    #     if self.rect_item is not None:
    #         self.rect_item.setRect(0, 0, self.width, self.height)

    # def leftPressed(self, x, y, mods=None):
    #     if not self.work_area_set:
    #             self.setWorkArea()
    #     else:
    #         self.reset()    

    #method to display the rectangle on the map
    # def enable(self, enable = False):
    #     if enable == True:
    #         self.rect_item = self.viewerplus.scene.addRect(0, 0, self.width, self.height, QPen(Qt.black, 5, Qt.DotLine)) 
    #     else:
    #         if self.rect_item is not None:
    #             self.viewerplus.scene.removeItem(self.rect_item)
    #         self.rect_item = None
            # self.center_item.setVisible(False)

    def leftReleased(self, x, y):
        self.rect_item = self.viewerplus.dragSelectionRect
        
        # rect = self.rect_item.rect()
        # rect = rect.intersected(self.viewerplus.sceneRect())
        # image = self.viewerplus.img_map.copy(rect.toRect())
        # image.save("rows_area.png")
        # print(f"left released at ({x}, {y})")

        self.setWorkArea()
        
    def reset(self):
        
        self.image_cropped = None

        self.viewerplus.scene.removeItem(self.work_area_rect)
        self.work_area_set = False
        self.work_area_item = None
        self.work_area_rect = None
        self.rect_item = None
        
        if self.shadow_item is not None:
            self.viewerplus.scene.removeItem(self.shadow_item)
            self.shadow_item = None

        self.viewerplus.struct_widget = None
        # self.viewerplus.scene.addItem(self.rect_item)

    def setWorkArea(self):
        """
        Set the work area based on the location of points
        """
        # Display to GUI
        brush = QBrush(Qt.NoBrush)
        pen = QPen(Qt.DashLine)
        pen.setWidth(2)
        pen.setColor(Qt.white)
        pen.setCosmetic(True)
        # From the current view, crop the image
        # Get the bounding rect of the work area and its position
        rect = self.rect_item.boundingRect()
        

        pos = self.rect_item.pos()
        # rect.moveTopLeft(pos)
        rect = rect.normalized()
        rect = rect.intersected(self.viewerplus.sceneRect())
        self.work_area_rect = self.viewerplus.scene.addRect(rect, pen, brush)
        self.work_area_rect.setPos(pos)
        
        # work_area_bbox = (rect.top(), rect.left(), rect.width(), rect.height())

        self.work_area_item = rect

        offset = self.work_area_rect.pos()
        self.offset = [offset.x(), offset.y()]

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

        rect_bbox = (0, 0, int(rect.width()), int(rect.height()))
        rect_mask = np.zeros((int(rect.height()), int(rect.width())), dtype=np.uint8)       
        
        self.saveBlobsInsideWorkArea()

        for blob in self.blobs_inside_work_area:
            bbox = blob.bbox
            top = bbox[0]
            # print(f"blob_bbox top is {top}")
            left = bbox[1]
            # print(f"blob_bbox left is {left}")
            right = bbox[1] + bbox[2]
            bottom = bbox[0] + bbox[3]

            blob_mask = blob.getMask()
            
            rect_mask[top - int(rect.top()):bottom - int(rect.top()), left - int(rect.left()):right - int(rect.left())] = blob_mask

        # Save the rect_mask as a matplotlib figure
        # plt.figure(figsize=(10, 10))
        # plt.imshow(rect_mask, cmap='gray')
        # plt.axis('off')
        # plt.savefig("rect_mask.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        # rect_mask[rect_mask == 0] = 255
        # rect_mask[rect_mask == 1] = 0
        #GROW DEI BLOB, LA MALTA È QUELLA CHE DISTA x PIXEL DAL BLOB
        rect_mask_grow = rect_mask.copy()


        # Create a structuring element that defines the neighborhood
        # 21x21 to cover 10 positions around each 1 (10 positions
        structuring_element = np.ones((21, 21), dtype=np.uint8)
        rect_mask_grow = binary_dilation(rect_mask, structure=structuring_element)

        rect_mask_grow = rect_mask_grow - rect_mask

        # Save the rect_mask_grow as a matplotlib figure
        plt.figure(figsize=(10, 10))
        plt.imshow(rect_mask_grow, cmap='gray')
        plt.axis('off')
        plt.savefig("rect_mask_grow.png", bbox_inches='tight', pad_inches=0)
        plt.close()

        rect_mask = rect_mask_grow
        
        # Convert rect_mask to a QImage
        height, width = rect_mask.shape
        bytes_per_line = rect_mask.strides[0]
        qImg = QImage(rect_mask.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        qImg.save("rect_mask_qimage.png")

        # self.structWidget(self.image_cropped, self.blobs_inside_work_area)
        self.structWidget(qImg, image_cropped, rect_mask, self.blobs_inside_work_area, self.work_area_rect)

    def isBlobInsideWorkArea(self, blob):
       
        #Check if a blob is inside the work area.
       
        if self.work_area_rect is None:
            return False

        rect = self.work_area_rect.boundingRect()
        # rect.moveTopLeft(self.work_area_rect.pos())
        rect = rect.normalized()

        bbox = blob.bbox
        top = bbox[0]
        left = bbox[1]
        right = bbox[1] + bbox[2]
        bottom = bbox[0] + bbox[3]

        if left >= rect.left() and right <= rect.right() and top >= rect.top() and bottom <= rect.bottom():
            return blob
        
    # def blobCentroid(self, blob):
    #     """
    #     Calculate and return the centroid of a blob relative to the self.work_area_rect.
    #     """
    #     mask = blob.getMask()
    #     region_props = measure.regionprops(mask.astype(int))
    #     rect = self.work_area_rect.boundingRect()
    #     if region_props:
    #         centroid = region_props[0].centroid
    #         # Convert centroid coordinates to be relative to the self.work_area_rect
    #         bbox = blob.bbox
    #         relative_centroid_x = bbox[1] + centroid[1]# - rect.top()
    #         relative_centroid_y = (bbox[0] + centroid[0])
    #         print(f"Relative centroid: ({relative_centroid_x}, {relative_centroid_y})")
    #         return (relative_centroid_x, relative_centroid_y)  # (x, y) format
    #     return None

    def saveBlobsInsideWorkArea(self):
        """
        Save the blobs inside the work area to a variable.
        """
        self.blobs_inside_work_area = []
        if self.viewerplus.annotations.seg_blobs is None:
            return

        for blob in self.viewerplus.annotations.seg_blobs:
            if self.isBlobInsideWorkArea(blob):
                print(blob.id)
                self.blobs_inside_work_area.append(blob)

        print(f"Number of blobs inside work area: {len(self.blobs_inside_work_area)}")


    def structWidget(self, image, cropped, mask, blob_list, rect):
        
        if self.viewerplus.struct_widget is None:
            
            struct_widget = RowsWidget(image, cropped, mask, blob_list, rect, parent= self.viewerplus)
            struct_widget.setWindowModality(Qt.NonModal)
            # struct_widget.btnCancel.clicked.connect(self.bricksCancel)
            # struct_widget.btnApply.clicked.connect(self.bricksApply)
            struct_widget.closeRowsWidget.connect(self.rowsClose)
            struct_widget.show()
            self.viewerplus.struct_widget = struct_widget

    @pyqtSlot()
    def rowsClose(self):
        self.viewerplus.resetTools()






