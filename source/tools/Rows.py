from source.tools.Tool import Tool
import numpy as np

import matplotlib.pyplot as plt
from scipy.ndimage import binary_dilation

from PyQt5.QtCore import Qt, pyqtSlot, QRect, QRectF, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import  QPainterPath, QPen, QBrush, QColor

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from source.QtRowsWidget import RowsWidget
from scipy.ndimage import binary_erosion

class Rows(Tool):
        
    def __init__(self, viewerplus):
        super(Rows, self).__init__(viewerplus)

        # dialog for the rows tool
        self.struct_widget = None

        # area of the image that is selected for processing
        self.work_area_set = False
        self.work_area = None
        self.offset = [0, 0]
        # regions to be processed
        self.blobs_inside_work_area = []
        # cropped image (for drawing in dialog)
        self.image_cropped = None
        # working mask 
        self.work_mask = None
        # rectangle and shadow for the work area to display the work area in the viewer
        self.work_area_rect = None
        self.work_area_shadow = None

        # display startup instructions for the tool
        message = "<p><i>ROWS TOOL </i></p>"
        message += "<p>Choose the work-area:<br/>\
                    - SHIFT + LMB: drag on the map to set the working area<br/></p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'

    def leftReleased(self, x, y):
        if self.work_area_set == True:
            return  # If the work area is already set, do nothing
        if self.viewerplus.dragSelectionRect is None:
            return  # If there is no drag selection rectangle, do nothing
        
        try:
            self.setWorkArea(self.viewerplus.dragSelectionRect)

        except Exception as e:
            print(f"Error in leftReleased: {e}")
            self.reset()
            self.viewerplus.resetSelection()
            pass


    def reset(self):
        self.work_area_set = False
        self.work_area = None
        self.offset = [0, 0]
        self.image_cropped = None
        self.work_mask = None
        self.blobs_inside_work_area = []
        if self.work_area_rect is not None:
            self.viewerplus.scene.removeItem(self.work_area_rect)
            self.work_area_rect = None
        if self.work_area_shadow is not None:
            self.viewerplus.scene.removeItem(self.work_area_shadow)
            self.work_area_shadow = None
        if self.viewerplus.struct_widget is not None:
            self.viewerplus.struct_widget.close()
            self.viewerplus.struct_widget = None


    def setWorkArea(self, dragSelectionRect):
        """
        Set the work area based on the location of points
        """
        # pos is the position of the dragged selection rectangle in the scene
        pos = dragSelectionRect.pos()
        # Get the bounding rect of the dragged selection rectangle
        # and normalize it to ensure it is within the scene rect
        self.work_area = dragSelectionRect.boundingRect()
        self.work_area = QRectF(self.work_area.toRect())  # snap to integral coordinates by converting to QRect then back to QRectF
        self.work_area = self.work_area.normalized()
        self.work_area = self.work_area.intersected(self.viewerplus.sceneRect())
        offset = pos
        self.offset = [offset.x(), offset.y()]

        # add the blobs inside the original selection rectangle
        self.addBlobsInsideWorkArea(self.work_area)
        # If no blobs are inside the work area, do not proceed
        if len(self.blobs_inside_work_area) == 0:
            print("No blobs inside the work area. Please select a different area.")
            self.reset()
            self.viewerplus.resetSelection()
            return

        # now, we enlarge the selection rectangle by 20 pixels
        # to ensure we have a margin around the blobs and to avoid cropping the dilated mask at the edges
        self.work_area.adjust(-20, -20, 20, 20)
        # Ensure the rectangle is still within the scene rect
        self.work_area = self.work_area.normalized()
        self.work_area = self.work_area.intersected(self.viewerplus.sceneRect())

        #area is now set
        self.work_area_set = True

        # Display the selected area in the window
        brush = QBrush(Qt.NoBrush)
        pen = QPen(Qt.DashLine)
        pen.setWidth(2)
        pen.setColor(Qt.white)
        pen.setCosmetic(True)
        self.work_area_rect = self.viewerplus.scene.addRect(self.work_area, pen, brush)
        self.work_area_rect.setPos(pos)
        # Create a semi-transparent overlay
        shadow_brush = QBrush(QColor(0, 0, 0, 75))  # Semi-transparent black
        shadow_path = QPainterPath()
        shadow_path.addRect(self.viewerplus.sceneRect())  # Cover the entire scene
        shadow_path.addRect(self.work_area)  # Add the work area rect
        shadow_path = shadow_path.simplified()  # Simplify the path to avoid overlaps
        self.work_area_shadow = self.viewerplus.scene.addPath(shadow_path, QPen(Qt.NoPen), shadow_brush)
        
        # From the current view, crop the image 
        self.image_cropped = self.viewerplus.img_map.copy(self.work_area.toRect())
        # DEBUG Save the cropped image
        # self.image_cropped.save("cropped_image.png")

        # Create a mask for the work area, initialized with zeros. The mask will be the same size as the work area rectangle
        self.work_mask = np.zeros((int(self.work_area.height()), int(self.work_area.width())), dtype=np.uint8)       
        for blob in self.blobs_inside_work_area:
            bbox = blob.bbox
            top = bbox[0]
            left = bbox[1]
            right = bbox[1] + bbox[2]
            bottom = bbox[0] + bbox[3]

            blob_mask = blob.getMask()
            blob_mask = binary_erosion(blob_mask, structure=np.ones((3, 3)), border_value=0)

            self.work_mask[top - int(self.work_area.top()):bottom - int(self.work_area.top()), left - int(self.work_area.left()):right - int(self.work_area.left())] |= blob_mask


        # Save the work_mask as a matplotlib figure
        # plt.figure(figsize=(10, 10))
        # plt.imshow(self.work_mask, cmap='gray')
        # plt.axis('off')
        # plt.savefig("work_mask.png", bbox_inches='tight', pad_inches=0)
        # plt.close()

        # self.work_mask[self.work_mask == 0] = 255
        # self.work_mask[self.work_mask == 1] = 0
        #GROW DEI BLOB, LA MALTA È QUELLA CHE DISTA x PIXEL DAL BLOB
        # rect_mask_grow = self.work_mask.copy()

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

        # self.work_mask = rect_mask_grow

        self.structWidget(self.image_cropped, self.work_mask, self.blobs_inside_work_area, self.work_area_rect)


    def addBlobsInsideWorkArea(self, rect):
        # Save the blobs inside the work area to a variable.
        
        self.blobs_inside_work_area = []
        if self.viewerplus.annotations.seg_blobs is None:
            return  # No blobs to check

        for blob in self.viewerplus.annotations.seg_blobs:
            # Check if a blob is inside the work area.
            bbox = blob.bbox
            if bbox[1] >= rect.left() and (bbox[1] + bbox[2]) <= rect.right() and bbox[0] >= rect.top() and (bbox[0] + bbox[3]) <= rect.bottom():
                self.blobs_inside_work_area.append(blob)

        print(f"Number of blobs inside work area: {len(self.blobs_inside_work_area)}")


    def structWidget(self, cropped, mask, blob_list, rect):
        
        if self.viewerplus.struct_widget is None:
            screen_size = QApplication.primaryScreen().size()

            struct_widget = RowsWidget(cropped, mask, blob_list, rect, parent= self.viewerplus, screen_size=screen_size)
            struct_widget.setWindowModality(Qt.NonModal)
            struct_widget.closeRowsWidget.connect(self.rowsClose)
            struct_widget.show()
            self.viewerplus.struct_widget = struct_widget

    @pyqtSlot()
    def rowsClose(self):
        self.viewerplus.resetTools()
        self.viewerplus.resetSelection()






