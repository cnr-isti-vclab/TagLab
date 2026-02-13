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

from source.Mask import paintMask, jointBox, jointMask, replaceMask, checkIntersection, intersectMask
from PIL import Image


import matplotlib.pyplot as plt

from PyQt5.QtCore import Qt, QObject, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR

from source.Label import Label

class Watershed(Tool):
        
    def __init__(self, viewerplus, scribbles):
        super(Watershed, self).__init__(viewerplus)
        self.viewerplus = viewerplus
        self.scribbles = scribbles
        self.current_blobs = []
        self.currentLabel = None

        self.dummy_bounding_box = None
        self.work_area_mask = None
        
        # State for undo segmentation feature
        self.just_segmented = False
        self.last_segmented_blobs = []
        self.saved_scribbles_state = None
        
        message = "<p><i>Draw scribbles inside and around an instance</i></p>"
        message += "<p>Select a class and draw positive scribbles INSIDE the instance,<br/>\
                    Then draw negative scribbles OUTSIDE the instance.<br/>\
                    The tool needs both positive and negative scribbles to work.</p>"
        message += "<p>- SHIFT + LMB + drag to draw a positive scribble<br/>\
                    - SHIFT + RMB + drag to draw a negative scribble<br/>\
                    - CTRL + Z to remove the last scribble or undo segmentation<br/>\
                    - ALT + LMB to delete a specific scribble</p>"
        message += "<p>- SHIFT + wheel to set brush size</p>"
        message += "<p>SPACEBAR to apply segmentation (press CTRL+Z to undo and refine)</p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'

    def activate(self):
        self.viewerplus.showMessage(self.tool_message)

    def deactivate(self):
        self.viewerplus.clearMessage()
    
    def setActiveLabel(self, label):
        # print(f"ActiveLabel id is {label.id}\n\
        #       ActiveLabel name is {label.name}\n")
        self.currentLabel = label
        self.scribbles.setLabel(self.currentLabel)

    def leftPressed(self, x, y, mods=None):
        if mods and (mods & Qt.AltModifier):
            # Delete scribble near click
            index = self.scribbles.findScribbleNear(x, y)
            if index >= 0:
                self.scribbles.deleteScribbleByIndex(index)
                self.log.emit(f"[TOOL][WATERSHED] Scribble deleted (index: {index})")
            else:
                self.log.emit("[TOOL][WATERSHED] No scribble found near click")
        elif mods and (mods & Qt.ShiftModifier):
            # If we just segmented, clear old scribbles and start fresh
            if self.just_segmented:
                self.just_segmented = False
                self.last_segmented_blobs = []
                self.scribbles.reset()
                self.log.emit("[TOOL][WATERSHED] Starting new scribbles")
            
            self.scribbles.setLabel(self.currentLabel)
            if self.scribbles.startDrawing(x, y):
                self.log.emit("[TOOL][WATERSHED] DRAWING POSITIVE starts..")

    def rightPressed(self, x, y, mods=None):
        if mods and (mods & Qt.ShiftModifier):
            # If we just segmented, clear old scribbles and start fresh
            if self.just_segmented:
                self.just_segmented = False
                self.last_segmented_blobs = []
                self.scribbles.reset()
                self.log.emit("[TOOL][WATERSHED] Starting new scribbles")
            
            fakeLabel = Label("Dummy", "Dummy", fill=[255, 255, 255], border=[0, 0, 0]) 
            self.scribbles.setLabel(fakeLabel)
            if self.scribbles.startDrawing(x, y):
                self.log.emit("[TOOL][WATERSHED] DRAWING NEGATIVE starts..")


    def mouseMove(self, x, y, mods=None):
        if mods &  Qt.ShiftModifier:
            self.scribbles.move(x, y)

    def wheel(self, delta, mods=None):
        increase = float(delta.y()) / 10.0
        if 0.0 < increase < 1.0:
            increase = 1
        elif -1.0 < increase < 0.0:
            increase = -1
        self.scribbles.setSize(int(increase))

    def hasPoints(self):
        """Check if there are any scribbles or if we just segmented."""
        return len(self.scribbles.points) > 0 or self.just_segmented

    def undo_click(self):
        """Remove the last scribble or undo segmentation (called by CTRL+Z)."""
        if self.just_segmented:
            # Undo the segmentation - remove all created blobs and restore scribbles
            for blob in self.last_segmented_blobs:
                self.viewerplus.removeBlob(blob)
            self.just_segmented = False
            self.last_segmented_blobs = []
            # Restore the scribbles from saved state
            if self.saved_scribbles_state:
                self.scribbles.restoreState(self.saved_scribbles_state)
                self.saved_scribbles_state = None
            self.log.emit("[TOOL][WATERSHED] Segmentation undone, scribbles restored")
        elif self.scribbles.deleteLastScribble():
            self.log.emit("[TOOL][WATERSHED] Last scribble deleted")

############################################################################################################################################################################   


    def snapBlobBorders(self, blob):
        # Define the working area using blob.bbox
        bbox = blob.bbox
        w = bbox[2]
        h = bbox[3]
        working_area_mask = np.zeros((h, w), dtype=np.int32)

        # Get the mask of the blob and place it in the working area
        blob_mask = blob.getMask()
        working_area_mask[:blob_mask.shape[0], :blob_mask.shape[1]] = blob_mask

        # Iterate over the existing blobs and remove intersections
        for existing_blob in self.viewerplus.image.annotations.seg_blobs:
            if existing_blob != blob and checkIntersection(bbox, existing_blob.bbox):
                existing_mask = existing_blob.getMask()
                paintMask(working_area_mask, bbox, existing_mask, existing_blob.bbox, 0)

        # # Convert the mask to a PIL image
        # isolated_blob_image = Image.fromarray(working_area_mask.astype(np.uint8) * 255)
        # # Save the image
        # isolated_blob_image.save("isolated_blob.png")
        
        # Update the new blob's mask
        blob.updateUsingMask(bbox, working_area_mask)

        return blob       


###########################################################################################################################################################################   


    def segmentation(self):

        # compute bbox of scribbles (working area)
        bboxes = []
        for i, curve in enumerate(self.scribbles.points):
            bbox = Mask.pointsBox(curve, int(self.scribbles.size[i] / 2))
            bboxes.append(bbox)
        
        # print(f"bboxes number is {len(bboxes)}")
        working_area = Mask.jointBox(bboxes)
        # print(f"working_area is {working_area}")

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

        #cv2.imwrite('crop_img.png', crop_imgnp)

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
            # print(f"color_code in dict is {color_code}")
            color_key = str(color_code)
            # print(f"color_key in dict is {color_key}")
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

        # print(f"color codes is {color_codes}")
        mask = np.uint8(mask)
       
        # print(f"mask.shape is {mask.shape}")
       # cv2.imwrite('mask.png', mask)

        markers = np.zeros((working_area[3], working_area[2]), dtype='int32')
        for label in self.scribbles.label:
            # print(f'label type is {type(label)}')
            # print(f'label is {label}')
            
            col = label.fill
            # print(f"col is {col}")
            
            b = col[2]
            # print(f"b is {b}")
            g = col[1]
            # print(f"g is {g}")
            r = col[0]
            # print(f"r is {r}")

            idx = np.where((mask[:, :, 0] == b) & (mask[:, :, 1] == g) & (mask[:, :, 2] == r))
        
            color_code = b + 256 * g + 65536 * r
            # print(f"color_code is {color_code}")
            
            color_key = str(color_code)
            # print(f"color_key is {color_key}")

            (value, name) = color_codes[color_key]
            # print(f"value, name is {value, name}")
            markers[idx] = value


        #plt.imshow(markers)
        # plt.savefig('markers.png')
        # cv2.imwrite('markers.png', markersprint)

        # watershed segmentation
        segmentation = cv2.watershed(crop_imgnp, markers)
        segmentation = filters.median(segmentation, disk(5), mode="mirror")

        #plt.imshow(segmentation)
        #plt.savefig('segmentation.png')

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
            # blob.class_name = "Empty"

            blobs.append(blob)

        return blobs

    def rightReleased(self, x, y):
        self.scribbles.setLabel(self.currentLabel)
        # pass

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

        # If we're applying again after a previous segmentation, clear that state
        if self.just_segmented:
            self.just_segmented = False
            self.last_segmented_blobs = []
            self.saved_scribbles_state = None

        # Save the scribble state before clearing
        self.saved_scribbles_state = self.scribbles.saveState()

        blobs = self.segmentation()
        
        created_blobs = []
        for blob in blobs:
            if blob.class_name != "Dummy":
                try:
                    self.snapBlobBorders(blob)
                    self.viewerplus.addBlob(blob)
                    created_blobs.append(blob)
                except Exception as e:
                    if "Empty contour" in str(e):
                        # Blob overlaps with existing annotations, subtract and retry
                        self.log.emit("[TOOL][WATERSHED] Blob overlaps with existing annotation, adjusting boundaries")
                        segmented = self.viewerplus.annotations.seg_blobs
                        for seg in segmented:
                            if checkIntersection(blob.bbox, seg.bbox):
                                self.viewerplus.annotations.subtract(seg, blob)
                        self.viewerplus.addBlob(blob)
                        created_blobs.append(blob)
                    else:
                        self.log.emit(f"[TOOL][WATERSHED] Exception during blob creation: {e}")
        
        # Store the created blobs and set the state
        self.last_segmented_blobs = created_blobs
        self.just_segmented = True
        
        # Clear scribbles visually after segmentation
        self.scribbles.reset()
        
        self.log.emit("[TOOL][WATERSHED] Segmentation applied. Press CTRL+Z to undo or draw new scribbles to continue.")
        
        # Don't reset tools yet - keep scribbles data for potential undo
        # self.viewerplus.resetTools()

    def reset(self):
        self.scribbles.reset()
        self.current_blobs = []
        self.just_segmented = False
        self.last_segmented_blobs = []
        self.saved_scribbles_state = None
