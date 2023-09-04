from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QImage

import cv2

from source.tools.Tool import Tool
from source import genutils

import os
import numpy as np

try:
    import torch
    from torch.nn.functional import interpolate
except Exception as e:
    print("Incompatible version between pytorch, cuda and python.\n" +
          "Knowing working version combinations are\n: Cuda 10.0, pytorch 1.0.0, python 3.6.8" + str(e))

import models.deeplab_resnet as resnet
from models.dataloaders import helpers as helpers
from collections import OrderedDict

import time

class FourClicks(Tool):
    def __init__(self, viewerplus, pick_points):
        super(FourClicks, self).__init__(viewerplus)

        self.pick_points = pick_points

        self.CROSS_LINE_WIDTH = 2
        self.pick_style = {'width': self.CROSS_LINE_WIDTH, 'color': Qt.red,  'size': 6}
        self.deepextreme_net = None
        self.device = None

    def leftPressed(self, x, y, mods):

        points = self.pick_points.points

        if len(points) < 4 and mods == Qt.ShiftModifier:
            self.pick_points.addPoint(x, y, self.pick_style)
            message = "[TOOL][DEEPEXTREME] New point picked (" + str(len(points)) + ")"
            self.log.emit(message)

        # APPLY DEEP EXTREME
        if len(points) == 4:
            self.segmentWithDeepExtreme()
            self.pick_points.reset()

    def prepareForDeepExtreme(self, four_points, pad_max):
        """
        Crop the image map (QImage) and return a NUMPY array containing it.
        It returns also the coordinates of the bounding box on the cropped image.
        """

        left = four_points[:, 0].min() - pad_max
        right = four_points[:, 0].max() + pad_max
        top = four_points[:, 1].min() - pad_max
        bottom = four_points[:, 1].max() + pad_max
        h = bottom - top
        w = right - left

        image_cropped = genutils.cropQImage(self.viewerplus.img_map, [top, left, w, h])

        fmt = image_cropped.format()
        assert (fmt == QImage.Format_RGB32)

        arr = np.zeros((h, w, 3), dtype=np.uint8)

        bits = image_cropped.bits()
        bits.setsize(int(h * w * 4))
        arrtemp = np.frombuffer(bits, np.uint8).copy()
        arrtemp = np.reshape(arrtemp, [h, w, 4])
        arr[:, :, 0] = arrtemp[:, :, 2]
        arr[:, :, 1] = arrtemp[:, :, 1]
        arr[:, :, 2] = arrtemp[:, :, 0]

        # update four point
        four_points_updated = np.zeros((4, 2), dtype=int)
        four_points_updated[:, 0] = four_points[:, 0] - left
        four_points_updated[:, 1] = four_points[:, 1] - top

        return (arr, four_points_updated)

    def segmentWithDeepExtreme(self):

        if not self.viewerplus.img_map:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.infoMessage.emit("Segmentation is ongoing..")
        self.log.emit("[TOOL][DEEPEXTREME] Segmentation begins..")

        # load network if necessary
        self.loadNetwork()

        pad = 50
        thres = 0.8

        extreme_points_to_use = np.asarray(self.pick_points.points).astype(int)
        pad_extreme = 100
        left_map_pos = extreme_points_to_use[:, 0].min() - pad_extreme
        top_map_pos = extreme_points_to_use[:, 1].min() - pad_extreme

        width_extreme_points = extreme_points_to_use[:, 0].max() - extreme_points_to_use[:, 0].min()
        height_extreme_points = extreme_points_to_use[:, 1].max() - extreme_points_to_use[:, 1].min()
        area_extreme_points = width_extreme_points * height_extreme_points

        (img, extreme_points_new) = self.prepareForDeepExtreme(extreme_points_to_use, pad_extreme)

        with torch.no_grad():

            extreme_points_ori = extreme_points_new.astype(int)

            #  Crop image to the bounding box from the extreme points and resize
            bbox = helpers.get_bbox(img, points=extreme_points_ori, pad=pad, zero_pad=True)
            crop_image = helpers.crop_from_bbox(img, bbox, zero_pad=True)
            resize_image = helpers.fixed_resize(crop_image, (512, 512)).astype(np.float32)

            #  Generate extreme point heat map normalized to image values
            extreme_points = extreme_points_ori - [np.min(extreme_points_ori[:, 0]),
                                                   np.min(extreme_points_ori[:, 1])] + [pad, pad]

            # remap the input points inside the 512 x 512 cropped box
            extreme_points = (512 * extreme_points * [1 / crop_image.shape[1], 1 / crop_image.shape[0]]).astype(
                int)

            # create the heatmap
            extreme_heatmap = helpers.make_gt(resize_image, extreme_points, sigma=10)
            extreme_heatmap = helpers.cstm_normalize(extreme_heatmap, 255)

            #  Concatenate inputs and convert to tensor
            input_dextr = np.concatenate((resize_image, extreme_heatmap[:, :, np.newaxis]), axis=2)
            inputs = torch.from_numpy(input_dextr.transpose((2, 0, 1))[np.newaxis, ...])

            # Run a forward pass
            inputs = inputs.to(self.device)
            outputs = self.deepextreme_net.forward(inputs)
            outputs = interpolate(outputs, size=(512, 512), mode='bilinear', align_corners=True)
            outputs = outputs.to(torch.device('cpu'))

            pred = np.transpose(outputs.data.numpy()[0, ...], (1, 2, 0))
            pred = 1 / (1 + np.exp(-pred))
            pred = np.squeeze(pred)

            result = helpers.crop2fullmask(pred, bbox, im_size=img.shape[:2], zero_pad=True, relax=pad) > thres

            segm_mask = result.astype(int)

            #TODO: move this function to blob!!!
            blobs = self.viewerplus.annotations.blobsFromMask(segm_mask, left_map_pos, top_map_pos, area_extreme_points)

            self.viewerplus.resetSelection()
            for blob in blobs:
                self.viewerplus.addBlob(blob, selected=True)
                self.blobInfo.emit(blob, "[TOOL][DEEPEXTREME][BLOB-CREATED]")
            self.viewerplus.saveUndo()

            self.infoMessage.emit("Segmentation done.")

        self.log.emit("[TOOL][DEEPEXTREME] Segmentation ends.")

        QApplication.restoreOverrideCursor()

    def loadNetwork(self):

        models_dir = "models/"

        if self.deepextreme_net is None:

            self.infoMessage.emit("Loading deepextreme network..")

            # Initialization
            modelName = 'dextr_corals'

            #  Create the network and load the weights
            self.deepextreme_net = resnet.resnet101(1, nInputChannels=4, classifier='psp')

            # dictionary layers' names - weights
            state_dict_checkpoint = torch.load(os.path.join(models_dir, modelName + '.pth'),
                                               map_location=lambda storage, loc: storage)

            # Remove the prefix .module from the model when it is trained using DataParallel
            if 'module.' in list(state_dict_checkpoint.keys())[0]:
                new_state_dict = OrderedDict()
                for k, v in state_dict_checkpoint.items():
                    name = k[7:]  # remove `module.` from multi-gpu training
                    new_state_dict[name] = v
            else:
                new_state_dict = state_dict_checkpoint

            self.deepextreme_net.load_state_dict(new_state_dict)
            self.deepextreme_net.eval()

            if not torch.cuda.is_available():
                print("CUDA NOT AVAILABLE!")
            else:
                gpu_id = 0
                device = torch.device("cuda:" + str(gpu_id) if torch.cuda.is_available() else "cpu")
                self.deepextreme_net.to(device)
                self.device = device

    def resetNetwork(self):
        torch.cuda.empty_cache()
        if self.deepextreme_net is not None:
            del self.deepextreme_net
            self.deepextreme_net = None

    def reset(self):
        self.resetNetwork()
        self.pick_points.reset()

