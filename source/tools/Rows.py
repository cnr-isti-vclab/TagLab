from source.tools.Tool import Tool

import numpy as np


from source.genutils import qimageToNumpyArray


import matplotlib.pyplot as plt
from scipy.ndimage import binary_dilation

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import  QPainterPath, QPen, QBrush, QColor

from PyQt5.QtWidgets import QSlider, QVBoxLayout, QLabel,QWidget
from PyQt5.QtCore import Qt

from source.QtRowsWidget import RowsWidget
from scipy.ndimage import binary_erosion

class Rows(Tool):
        
    def __init__(self, viewerplus):
        super(Rows, self).__init__(viewerplus)

        # self.viewerplus.mouseMoved.connect(self.handlemouseMove)
        
        self.struct_widget = None

        self.offset = [0, 0]

        self.rect_item = None
        self.blobs_inside_work_area = []

        self.work_area_item = None
        self.work_area_rect = None
        self.work_area_set = False
        self.shadow_item = None

        self.image_cropped = None
        self.image_cropped_np = None

        message = "<p><i>ROWS TOOL </i></p>"
        message += "<p>Choose the work-area:<br/>\
                    - CTRL + LMB: drag on the map to set the working area<br/></p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'

    def leftReleased(self, x, y):
        try:
            self.rect_item = self.viewerplus.dragSelectionRect

            self.setWorkArea()

        except Exception as e:
            pass
            
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
            blob_mask = binary_erosion(blob_mask, structure=np.ones((3, 3)), border_value=0)
            
            # rect_mask[top - int(rect.top()):bottom - int(rect.top()), left - int(rect.left()):right - int(rect.left())] = blob_mask
            rect_mask[top - int(rect.top()):bottom - int(rect.top()), left - int(rect.left()):right - int(rect.left())] |= blob_mask


        # Save the rect_mask as a matplotlib figure
        plt.figure(figsize=(10, 10))
        plt.imshow(rect_mask, cmap='gray')
        plt.axis('off')
        plt.savefig("rect_mask.png", bbox_inches='tight', pad_inches=0)
        plt.close()

        # rect_mask[rect_mask == 0] = 255
        # rect_mask[rect_mask == 1] = 0
        #GROW DEI BLOB, LA MALTA È QUELLA CHE DISTA x PIXEL DAL BLOB
        # rect_mask_grow = rect_mask.copy()

        # # Create a structuring element that defines the neighborhood
        # # 21x21 to cover 10 positions around each 1 (10 positions
        # # structuring_element = np.ones((21, 21), dtype=np.uint8)
        # structuring_element = np.ones((self.structuring_element_size, self.structuring_element_size), dtype=np.uint8)
        # print(f"Structuring element size: {self.structuring_element_size}")
        # rect_mask_grow = binary_dilation(rect_mask, structure=structuring_element)

        # rect_mask_grow = rect_mask_grow - rect_mask

        # # Save the rect_mask_grow as a matplotlib figure
        # plt.figure(figsize=(10, 10))
        # plt.imshow(rect_mask_grow, cmap='gray')
        # plt.axis('off')
        # plt.savefig("rect_mask_grow.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        # rect_mask = rect_mask_grow
        
        self.structWidget(image_cropped, rect_mask, self.blobs_inside_work_area, self.work_area_rect)

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

    def saveBlobsInsideWorkArea(self):
        # Save the blobs inside the work area to a variable.
        
        self.blobs_inside_work_area = []
        if self.viewerplus.annotations.seg_blobs is None:
            return

        for blob in self.viewerplus.annotations.seg_blobs:
            if self.isBlobInsideWorkArea(blob):
                self.blobs_inside_work_area.append(blob)

        print(f"Number of blobs inside work area: {len(self.blobs_inside_work_area)}")


    def structWidget(self, cropped, mask, blob_list, rect):
        
        if self.viewerplus.struct_widget is None:
            
            struct_widget = RowsWidget(cropped, mask, blob_list, rect, parent= self.viewerplus)
            struct_widget.setWindowModality(Qt.NonModal)
            struct_widget.closeRowsWidget.connect(self.rowsClose)
            struct_widget.show()
            self.viewerplus.struct_widget = struct_widget

    @pyqtSlot()
    def rowsClose(self):
        self.viewerplus.resetTools()
        self.viewerplus.resetSelection()






