import numpy as np
import matplotlib.pyplot as plt
from skimage.data import data_dir
from skimage.util import img_as_ubyte
from skimage import io, measure
from source.Annotation import Annotation, Blob

import math
from source import utils
import json

from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, QLineF, QRectF, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainterPath, QPainter, QFont, QColor, QPolygonF, QImage, QPixmap, QPainter, QIcon, QPen, QBrush, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QApplication

from skimage.segmentation import clear_border
from skimage.measure import label, regionprops

from source.Project import Project, loadProject
import os
import sys

import models.deeplab_resnet as resnet
from models.dataloaders import helpers as helpers
from collections import OrderedDict

import torch
from torch.nn.functional import upsample

def createSubfolders(base_folder):

    image_dir = os.path.join(base_folder, "image")
    if not os.path.exists(image_dir):
        os.mkdir(image_dir)

    label_dir = os.path.join(base_folder, "label")
    if not os.path.exists(label_dir):
        os.mkdir(label_dir)

    mask_dir = os.path.join(base_folder, "mask")
    if not os.path.exists(mask_dir):
        os.mkdir(mask_dir)

    return image_dir, label_dir, mask_dir

def createExtremePoints(blob):

    index_left = np.argmin(blob.contour[:, 0])
    index_right = np.argmax(blob.contour[:, 0])
    index_top = np.argmin(blob.contour[:, 1])
    index_bottom = np.argmax(blob.contour[:, 1])

    extreme_points = np.zeros((4, 2), dtype=np.int32)

    extreme_points[0, 0] = blob.contour[index_top, 0]
    extreme_points[0, 1] = blob.contour[index_top, 1]

    extreme_points[1, 0] = blob.contour[index_left, 0]
    extreme_points[1, 1] = blob.contour[index_left, 1]

    extreme_points[2, 0] = blob.contour[index_right, 0]
    extreme_points[2, 1] = blob.contour[index_right, 1]

    extreme_points[3, 0] = blob.contour[index_bottom, 0]
    extreme_points[3, 1] = blob.contour[index_bottom, 1]

    width = blob.bbox[2]
    height = blob.bbox[3]

    # Random Pixel Offset
    RPO = 6

    extreme_points2 = np.zeros((4, 2), dtype=np.int32)
    extreme_points2[0, 0] = extreme_points[0, 0] + np.random.randint(-RPO, RPO)
    extreme_points2[1, 0] = extreme_points[1, 0] + np.random.randint(-RPO, RPO)
    extreme_points2[2, 0] = extreme_points[2, 0] + np.random.randint(-RPO, RPO)
    extreme_points2[3, 0] = extreme_points[3, 0] + np.random.randint(-RPO, RPO)
    extreme_points2[0, 1] = extreme_points[0, 1] + np.random.randint(-RPO, RPO)
    extreme_points2[1, 1] = extreme_points[1, 1] + np.random.randint(-RPO, RPO)
    extreme_points2[2, 1] = extreme_points[2, 1] + np.random.randint(-RPO, RPO)
    extreme_points2[3, 1] = extreme_points[3, 1] + np.random.randint(-RPO, RPO)

    return extreme_points2


def segmentWithDeepExtreme(img_map, extreme_points_to_use, deepextreme_net, annotations):

    pad = 50
    thres = 0.8
    gpu_id = 0
    device = torch.device("cuda:" + str(gpu_id) if torch.cuda.is_available() else "cpu")
    deepextreme_net.to(device)

    pad_extreme = 100
    left_map_pos = extreme_points_to_use[:, 0].min() - pad_extreme
    top_map_pos = extreme_points_to_use[:, 1].min() - pad_extreme

    width_extreme_points = extreme_points_to_use[:, 0].max() - extreme_points_to_use[:, 0].min()
    height_extreme_points = extreme_points_to_use[:, 1].max() - extreme_points_to_use[:, 1].min()
    area_extreme_points = width_extreme_points * height_extreme_points

    (img, extreme_points_new) = utils.prepareForDeepExtreme(img_map, extreme_points_to_use, pad_extreme)

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
            np.int)

        # create the heatmap
        extreme_heatmap = helpers.make_gt(resize_image, extreme_points, sigma=10)
        extreme_heatmap = helpers.cstm_normalize(extreme_heatmap, 255)

        #  Concatenate inputs and convert to tensor
        input_dextr = np.concatenate((resize_image, extreme_heatmap[:, :, np.newaxis]), axis=2)
        inputs = torch.from_numpy(input_dextr.transpose((2, 0, 1))[np.newaxis, ...])

        # Run a forward pass
        inputs = inputs.to(device)
        outputs = deepextreme_net.forward(inputs)
        outputs = upsample(outputs, size=(512, 512), mode='bilinear', align_corners=True)
        outputs = outputs.to(torch.device('cpu'))

        pred = np.transpose(outputs.data.numpy()[0, ...], (1, 2, 0))
        pred = 1 / (1 + np.exp(-pred))
        pred = np.squeeze(pred)
        img_test = utils.floatmapToQImage(pred*255.0)
        img_test.save("prediction.png")
        result = helpers.crop2fullmask(pred, bbox, im_size=img.shape[:2], zero_pad=True, relax=pad) > thres

        segm_mask = result.astype(int)

        return top_map_pos, left_map_pos, segm_mask

        # blobs = annotations.blobsFromMask(segm_mask, left_map_pos, top_map_pos, area_extreme_points)
        # for blob in blobs:
        #     annotations.seg_blobs.append(blob)

def loadDEXTER():

    # Initialization
    modelName = 'dextr_corals'

    #  Create the network and load the weights
    deepextreme_net = resnet.resnet101(1, nInputChannels=4, classifier='psp')

    models_dir = "models/"

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

    deepextreme_net.load_state_dict(new_state_dict)
    deepextreme_net.eval()
    if not torch.cuda.is_available():
        print("CUDA NOT AVAILABLE!")

    return deepextreme_net


def createDatasetRITM(project_filename, output_folder):

    taglab_dir= os.getcwd()

    f = open("config.json", "r")
    config_dict = json.load(f)
    labels_dictionary = config_dict["Labels"]

    project = loadProject(taglab_dir, project_filename, labels_dictionary)

    train_dir = os.path.join(output_folder, "train")
    val_dir = os.path.join(output_folder, "val")
    test_dir = os.path.join(output_folder, "test")

    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    if not os.path.exists(train_dir):
        os.mkdir(train_dir)

    if not os.path.exists(val_dir):
        os.mkdir(val_dir)

    if not os.path.exists(test_dir):
        os.mkdir(test_dir)

    train_image_dir, train_label_dir, train_mask_dir = createSubfolders(train_dir)
    val_image_dir, val_label_dir, val_mask_dir = createSubfolders(val_dir)
    test_image_dir, test_label_dir, test_mask_dir = createSubfolders(test_dir)

    # load Deep Extreme network
    deepextreme_net = loadDEXTER()

    # iterate on blobs
    plot = project.images[0]
    channel = plot.getRGBChannel()
    plot_RGB = channel.loadData()

    annotations = Annotation()
    i = 0
    for blob in plot.annotations.seg_blobs:

        maskgt = blob.getMask()
        filename = os.path.join(train_label_dir, "maskGT" + str(i) + ".png")
        maskgtimg = utils.maskToQImage(maskgt)
        maskgtimg.save(filename)

        extreme_points_to_use = createExtremePoints(blob)

        top, left, mask = segmentWithDeepExtreme(plot_RGB, extreme_points_to_use, deepextreme_net, annotations)

        maskimg = utils.maskToQImage(mask)
        filename = os.path.join(train_mask_dir, "mask" + str(i) + ".png")
        maskimg.save(filename)

        i = i + 1

        print(i)

if __name__ == '__main__':

    # Create the QApplication.
    app = QApplication(sys.argv)

    # taglab project to load the annotations
    project_filename = "D:\\SCRIPPS MAPS\\rescaled\\MAI_2016\\MAI_2016.json"
    output_folder = "D:\\temp"

    createDatasetRITM(project_filename, output_folder)


