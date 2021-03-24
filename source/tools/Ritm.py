from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPen, QBrush

from source.tools.Tool import Tool
from source.Mask import paintMask
from source.utils import qimageToNumpyArray
from source.utils import cropQImage, floatmapToQImage

import os
import numpy as np

import torch

from models.isegm.inference import clicker
from models.isegm.inference.predictors import get_predictor
from models.isegm.inference import utils

class Ritm(Tool):
    def __init__(self, viewerplus, corrective_points):
        super(Ritm, self).__init__(viewerplus)
        self.points = corrective_points
        self.ritm_net = None
        self.MAX_POINTS = 10

        self.clicker = clicker.Clicker()
        self.predictor = None
        self.predictor_params = {'brs_mode': 'NoBRS'}
        self.init_mask = None
        self.device = None
        self.current_blobs = []
        self.blob_to_correct = None
        self.work_area_bbox = [0, 0, 0, 0]
        self.work_area_item = None
        self.states = []

    def leftPressed(self, x, y, mods):

        if mods & Qt.ShiftModifier:
            points = self.points.positive_points
            if len(points) < self.MAX_POINTS:
                self.points.addPoint(x, y, positive=True)
                message = "[TOOL][RITM] New positive point added (" + str(len(points)) + ")"
                self.log.emit(message)

                # apply segmentation
                self.segment()

                self.last_click = "positive"

    def rightPressed(self, x, y, mods):

        if mods & Qt.ShiftModifier:
            points = self.points.negative_points
            if len(points) < self.MAX_POINTS:
                self.points.addPoint(x, y, positive=False)
                message = "[TOOL][RITM] New negative point added (" + str(len(points)) + ")"
                self.log.emit(message)

                # apply segmentation
                self.segment()

                self.last_click = "negative"

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

    def prepareInput(self):

        nclicks = self.points.nclicks()

        if nclicks == 1 and self.work_area_bbox[2] == 0 and self.work_area_bbox[3] == 0:
            # input image
            rect_map = self.viewerplus.viewportToScene()
            self.work_area_bbox = [round(rect_map.top()), round(rect_map.left()),
                             round(rect_map.width()), round(rect_map.height())]
            image_crop = cropQImage(self.viewerplus.img_map, self.work_area_bbox)
            input_image = qimageToNumpyArray(image_crop)
            self.predictor.set_input_image(input_image)
            image_crop.save("C:\\temp\\crop.png")

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

        # prev mask
        if nclicks == 1 and len(self.viewerplus.selected_blobs) > 0:
            if self.blob_to_correct is None:
                self.blob_to_correct = self.viewerplus.selected_blobs[0]
                self.viewerplus.resetSelection()
                self.viewerplus.removeBlob(self.blob_to_correct)

            mask = self.blob_to_correct.getMask()

            self.init_mask = np.zeros((input_image.shape[0], input_image.shape[1]), dtype=np.int32)

            paintMask(self.init_mask, self.work_area_bbox, mask, self.blob_to_correct.bbox, 1)
            self.init_mask = self.init_mask.astype(np.float32)

            qimg = floatmapToQImage(self.init_mask.astype(np.float32))
            qimg.save("C:\\temp\\initmask.png")

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

    def segment(self, save_status=True):

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.infoMessage.emit("Segmentation is ongoing..")
        self.log.emit("[TOOL][DEEPEXTREME] Segmentation begins..")

        self.loadNetwork()

        self.prepareInput()

        if save_status:
            self.states.append(self.predictor.get_states())
        pred = self.predictor.get_prediction(self.clicker, prev_mask=self.init_mask)

        qimg = floatmapToQImage(pred)
        qimg.save("C:\\temp\\predictions.png")

        segm_mask = pred > 0.5
        segm_mask = 255 * segm_mask.astype(np.int32)

        torch.cuda.empty_cache()

        self.undrawAllBlobs()

        blobs = self.viewerplus.annotations.blobsFromMask(segm_mask, self.work_area_bbox[1], self.work_area_bbox[0], 1000)

        for blob in blobs:
            self.drawBlob(blob)

        self.current_blobs = blobs

        self.infoMessage.emit("Segmentation done.")
        self.log.emit("[TOOL][RITM] Segmentation ends.")

        QApplication.restoreOverrideCursor()

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

            self.ritm_net = utils.load_is_model(model_path, device, cpu_dist_maps=False)
            self.ritm_net.to(device)

            # initialize predictor
            self.predictor = get_predictor(self.ritm_net, device=device, **self.predictor_params)

    def resetNetwork(self):

        torch.cuda.empty_cache()
        if self.ritm_net is not None:
            del self.ritm_net
            self.ritm_net = None

    def apply(self):
        """
        Confirm the result and allows to segment another object.
        """

        # finalize created blobs
        for blob in self.current_blobs:
            self.viewerplus.addBlob(blob, selected=True)
            self.blobInfo.emit(blob, "[TOOL][RITM][BLOB-CREATED]")
        self.viewerplus.saveUndo()
        self.viewerplus.resetSelection()

        self.current_blobs = []
        self.clicker.reset_clicks()
        self.points.reset()
        self.resetWorkArea()

    def resetWorkArea(self):
        """
        The reset of the working area causes also the re-initialization of the RITM.
        """
        self.work_area_bbox = [0, 0, 0, 0]
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
            self.viewerplus.addBlob(self.blob_to_correct)

        self.undrawAllBlobs()
        self.clicker.reset_clicks()
        self.points.reset()
        self.resetWorkArea()

    def drawBlob(self, blob):

        # get the scene
        scene = self.viewerplus.scene

        # if it has just been created remove the current graphics item in order to set it again
        if blob.qpath_gitem is not None:
            scene.removeItem(blob.qpath_gitem)
            del blob.qpath_gitem
            blob.qpath_gitem = None

        blob.setupForDrawing()

        pen = QPen(Qt.lightGray)
        pen.setWidth(2)
        pen.setCosmetic(True)

        brush = QBrush(Qt.NoBrush)

        blob.qpath_gitem = scene.addPath(blob.qpath, pen, brush)
        blob.qpath_gitem.setZValue(1)

    def undrawBlob(self, blob):
        # get the scene
        scene = self.viewerplus.scene
        # undraw
        scene.removeItem(blob.qpath_gitem)
        blob.qpath = None
        blob.qpath_gitem = None
        scene.invalidate()

    def undrawAllBlobs(self):

        if len(self.current_blobs) > 0:
            for blob in self.current_blobs:
                self.undrawBlob(blob)
        self.current_blobs = []
