from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QPen, QBrush

from source.tools.Tool import Tool
from source.Mask import paintMask, jointBox, jointMask, replaceMask, checkIntersection, intersectMask
from source.genutils import qimageToNumpyArray
from source.genutils import cropQImage, maskToQImage, floatmapToQImage

import os
import numpy as np

import torch

from models.isegm.inference import clicker
from models.isegm.inference.predictors import get_predictor
from models.isegm.inference import utils as ritmutils

from source.tools import utils

class Ritm(Tool):

    def __init__(self, viewerplus, corrective_points):
        super(Ritm, self).__init__(viewerplus)

        self.points = corrective_points
        self.ritm_net = None
        self.MAX_POINTS = 10

        self.clicker = clicker.Clicker() #handles clicked point (original code of ritm)
        self.predictor = None
        self.predictor_params = {'brs_mode': 'NoBRS'}
        self.init_mask = None
        self.device = None
        self.current_blobs = []
        self.blob_to_correct = None  # selected blob
        self.work_area_bbox = [0, 0, 0, 0]
        self.work_area_mask = None   # to not overlap old segmented regions
        self.work_area_item = None
        self.states = []


    def checkPointPosition(self, x, y):

        if self.work_area_bbox[2]==0 and self.work_area_bbox[3]==0:
            return True
        if x <= self.work_area_bbox[1] or x>= self.work_area_bbox[1]+self.work_area_bbox[2]:
            return False
        if y <= self.work_area_bbox[0] or y>= self.work_area_bbox[0] + self.work_area_bbox[3]:
            return False

        return True


    def leftPressed(self, x, y, mods):

        points = self.points.positive_points
        if len(points) < self.MAX_POINTS and self.checkPointPosition(x,y) is True and mods == Qt.ShiftModifier:
            self.points.addPoint(x, y, positive=True)
            message = "[TOOL][RITM] New positive point added (" + str(len(points)) + ")"
            self.log.emit(message)

            # apply segmentation
            self.segment()


    def rightPressed(self, x, y, mods):

        points = self.points.negative_points
        if len(points) < self.MAX_POINTS and self.checkPointPosition(x,y) is True and mods == Qt.ShiftModifier:
            self.points.addPoint(x, y, positive=False)
            message = "[TOOL][RITM] New negative point added (" + str(len(points)) + ")"
            self.log.emit(message)

            # apply segmentation
            self.segment()

    def hasPoints(self):
        return self.points.nclicks() > 0

    def undo_click(self):
        self.points.removeLastPoint()
        nclicks = self.points.nclicks()
        if nclicks == 0:
            # reset ALL
            self.reset()
        else:
            prev_state = self.states.pop()
            self.predictor.set_states(prev_state)
            self.segment(save_status=False)


    def initializeWorkArea(self):
        # if image_crop is too big it must be rescaled otherwise the image is too big and the ritm goes out of memory

        rect_map = self.viewerplus.viewportToScene()
        self.work_area_bbox = [round(rect_map.top()), round(rect_map.left()),
                               round(rect_map.width()), round(rect_map.height())]


        image_crop = cropQImage(self.viewerplus.img_map, self.work_area_bbox)
        input_image = qimageToNumpyArray(image_crop)

        # check CUDA memory to prevent crash
        oom = False
        try:
            self.predictor.set_input_image(input_image)
        except RuntimeError:  # Out of memory
            oom = True

        if oom:
            box = QMessageBox()
            box.setText("CUDA out of memory. Try to reduce the viewing area by zooming in.")
            box.exec()
            return False

        # check size of the input image to prevent stuck of the PC (for CPU version)
        if torch.cuda.is_available() is False:
            megapixels = (input_image.shape[0] * input_image.shape[1]) / (1024.0*1024.0)
            if megapixels > 9.0:
                box = QMessageBox()
                box.setText("The input image is too big. Try to reduce the viewing area by zooming in.")
                box.exec()
                return False

        self.createWorkAreaMask()
        brush = QBrush(Qt.NoBrush)
        pen = QPen(Qt.DashLine)
        pen.setWidth(2)
        pen.setColor(Qt.white)
        pen.setCosmetic(True)
        x = self.work_area_bbox[1]
        y = self.work_area_bbox[0]
        w = self.work_area_bbox[2]
        h = self.work_area_bbox[3]
        self.work_area_item = self.viewerplus.scene.addRect(x, y, w, h, pen, brush)
        self.work_area_item.setZValue(3)
        #self.workingAreaIsActive.emit()

        return True

    def createWorkAreaMask(self):

        w = self.work_area_bbox[2]
        h = self.work_area_bbox[3]
        self.work_area_mask = np.zeros((h,w), dtype=np.int32)
        for blob in self.viewerplus.image.annotations.seg_blobs:
            if checkIntersection(self.work_area_bbox, blob.bbox):
                mask = blob.getMask()
                paintMask(self.work_area_mask, self.work_area_bbox, mask, blob.bbox, 1)

    def intersectionWithExistingBlobs(self, blob):
        bigmask = self.work_area_mask.copy()
        pixels_before = np.count_nonzero(bigmask)
        mask = blob.getMask()
        pixels = np.count_nonzero(mask)
        paintMask(bigmask, self.work_area_bbox, mask, blob.bbox, 0)
        pixels_after = np.count_nonzero(bigmask)
        perc_intersect = ((pixels_before - pixels_after) * 100.0) / pixels

        return perc_intersect

    def prepareInput(self):

        nclicks = self.points.nclicks()
        validArea = True

        if nclicks == 1 and self.work_area_bbox[2] == 0 and self.work_area_bbox[3] == 0:
            # the work area is assigned as the input image of the network
            validArea = self.initializeWorkArea()

        # init mask
        if nclicks == 1 and len(self.viewerplus.selected_blobs) > 0:
            if self.blob_to_correct is None:
                self.blob_to_correct = self.viewerplus.selected_blobs[0]
                self.viewerplus.resetSelection()
                self.viewerplus.undrawBlob(self.blob_to_correct) #removeBlob(self.blob_to_correct)
                if self.work_area_mask is not None:
                    paintMask(self.work_area_mask, self.work_area_bbox, self.blob_to_correct.getMask(),
                            self.blob_to_correct.bbox, 0)

            mask = self.blob_to_correct.getMask()

            self.init_mask = np.zeros((self.work_area_bbox[3], self.work_area_bbox[2]), dtype=np.int32)
            paintMask(self.init_mask, self.work_area_bbox, mask, self.blob_to_correct.bbox, 1)
            self.init_mask = self.init_mask.astype(np.float32)
            self.init_mask = torch.from_numpy(self.init_mask).unsqueeze(0).unsqueeze(0)
            self.init_mask = self.init_mask.to(self.device)
        else:
            self.init_mask = None

        # create clicks
        self.clicker.reset_clicks()
        for point in self.points.positive_points:
            x = point[0] - self.work_area_bbox[1]
            y = point[1] - self.work_area_bbox[0]
            click = clicker.Click(is_positive=True, coords=(y, x))
            self.clicker.add_click(click)

        for point in self.points.negative_points:
            x = point[0] - self.work_area_bbox[1]
            y = point[1] - self.work_area_bbox[0]
            click = clicker.Click(is_positive=False, coords=(y, x))
            self.clicker.add_click(click)

        return validArea

    def segment(self, save_status=True):

        self.infoMessage.emit("Segmentation is ongoing..")
        self.log.emit("[TOOL][RITM] Segmentation begins..")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        if not self.loadNetwork():
            return

        QApplication.restoreOverrideCursor()

        if self.prepareInput() is True:

            if save_status:
                self.states.append(self.predictor.get_states())

            oom = False
            try:
                pred = self.predictor.get_prediction(self.clicker, prev_mask=self.init_mask)
            except RuntimeError:  # Out of memory
                oom = True

            if oom:
                self.reset()
                box = QMessageBox()
                box.setText("CUDA out of memory. Try to reduce the viewing area by zooming in.")
                box.exec()
            else:
                segm_mask = pred > 0.5
                segm_mask = segm_mask.astype(np.int32)
                offsetx= self.work_area_bbox[1]
                offsety=self.work_area_bbox[0]

                # this handle corrections by fusing the new segm_mask with the one of the object to correct
                if self.blob_to_correct is not None:
                    bbox_to_correct = self.blob_to_correct.bbox
                    mask_to_correct = self.blob_to_correct.getMask()
                    joint_mask = jointMask(bbox_to_correct, self.work_area_bbox)
                    paintMask(joint_mask[0], joint_mask[1], mask_to_correct, bbox_to_correct, 1)
                    replaceMask(joint_mask[0], joint_mask[1], segm_mask, self.work_area_bbox)
                    offsetx= joint_mask[1][1]
                    offsety= joint_mask[1][0]
                    segm_mask = joint_mask[0]

                segm_mask = segm_mask*255
                torch.cuda.empty_cache()

                utils.undrawAllBlobs(self.current_blobs, self.viewerplus.scene)
                self.current_blobs = []

                blobs = self.viewerplus.annotations.blobsFromMask(segm_mask, offsetx, offsety, 1000)

                for blob in blobs:
                    if self.intersectionWithExistingBlobs(blob) < 90.0:
                       self.current_blobs.append(blob)

                if self.blob_to_correct is not None:
                    mask_to_correct = self.blob_to_correct.getMask()
                    box_to_correct = self.blob_to_correct.bbox
                    biggest_blob = None
                    biggest_intersection = -1.0

                    for blob in self.current_blobs:
                        intersection = intersectMask(mask_to_correct, box_to_correct , blob.getMask(), blob.bbox)
                        if intersection is None:
                           intersecting_pixels = 0
                        else:
                           intersecting_pixels = np.count_nonzero(intersection[0])

                        if intersecting_pixels > biggest_intersection:
                           biggest_intersection = intersecting_pixels
                           biggest_blob = blob

                    self.current_blobs = [biggest_blob]

                for blob in self.current_blobs:
                    self.drawBlob(blob)

                self.infoMessage.emit("Segmentation done.")

        else:
            self.reset()

        self.log.emit("[TOOL][RITM] Segmentation ends.")

    def loadNetwork(self):

        if self.ritm_net is None:

            self.infoMessage.emit("Loading RITM network..")

            model_name = 'ritm_corals.pth'
            model_path = os.path.join("models", model_name)

            if not torch.cuda.is_available():
                print("CUDA NOT AVAILABLE!")
                device = torch.device("cpu")
            else:
                device = torch.device("cuda:0")

            self.device = device

            try:
                self.ritm_net = ritmutils.load_is_model(model_path, device, cpu_dist_maps=False)
                self.ritm_net.to(device)
                # initialize predictor
                self.predictor = get_predictor(self.ritm_net, device=device, **self.predictor_params)

            except Exception as e:
                box = QMessageBox()
                box.setText("Could not load the Ritm network. You might need to run update.py.")
                box.exec()
                return False

        return True

    def resetNetwork(self):

        torch.cuda.empty_cache()
        if self.ritm_net is not None:
            del self.ritm_net
            self.ritm_net = None

    def apply(self):
        """
        Confirm the result and allow to segment another object.
        """

        # finalize created blobs
        message = "[TOOL][RITM][BLOB-CREATED]"
        for blob in self.current_blobs:
            
            if self.blob_to_correct is not None:
                self.viewerplus.removeBlob(self.blob_to_correct)
                blob.id = self.blob_to_correct.id
                blob.class_name = self.blob_to_correct.class_name
                message = "[TOOL][RITM][BLOB-EDITED]"

            # order is important: first add then setblob class!
            utils.undrawBlob(blob, self.viewerplus.scene, redraw=False)
            self.viewerplus.addBlob(blob, selected=True)
            #if self.blob_to_correct is not None:
            #    self.viewerplus.setBlobClass(blob, self.blob_to_correct.class_name)

            self.blobInfo.emit(blob, message)

        self.viewerplus.saveUndo()
        self.viewerplus.resetSelection()

        self.init_mask = None
        self.blob_to_correct = None
        self.current_blobs = []
        self.clicker.reset_clicks()
        self.points.reset()
        self.resetWorkArea()

    def resetWorkArea(self):
        """
        The reset of the working area causes also the re-initialization of the RITM.
        """
        self.work_area_bbox = [0, 0, 0, 0]
        self.work_area_mask = None
        if self.work_area_item is not None:
            self.viewerplus.scene.removeItem(self.work_area_item)
            self.work_area_item = None

    def reset(self):
        """
        Reset all the information. Called when ESCAPE is pressed.
        """

        self.resetNetwork()

        # re-add the blob removed
        if self.blob_to_correct is not None:
            #self.viewerplus.addBlob(self.blob_to_correct)
            self.viewerplus.drawBlob(self.blob_to_correct)
            self.blob_to_correct = None

        self.init_mask = None
        utils.undrawAllBlobs(self.current_blobs, self.viewerplus.scene)
        self.current_blobs = []
        self.clicker.reset_clicks()
        self.points.reset()
        self.resetWorkArea()

    def drawBlob(self, blob):

        scene = self.viewerplus.scene

        # create the suitable brush
        if self.blob_to_correct is None:
            brush = QBrush(Qt.SolidPattern)
            brush.setColor(Qt.white)
        else:
            brush = self.viewerplus.project.classBrushFromName(self.blob_to_correct)

        utils.drawBlob(blob, brush, scene, self.viewerplus.transparency_value, redraw=False)


