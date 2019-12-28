# TagLab                                               
# A semi-automatic segmentation tool                                    
#
# Copyright(C) 2019                                         
# Visual Computing Lab                                           
# ISTI - Italian National Research Council                              
# All rights reserved.                                                      
                                                                          
# This program is free software; you can redistribute it and/or modify      
# it under the terms of the GNU General Public License as published by      
# the Free Software Foundation; either version 2 of the License, or         
# (at your option) any later version.                                       
                                                                           
# This program is distributed in the hope that it will be useful,           
# but WITHOUT ANY WARRANTY; without even the implied warranty of            
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             
#GNU General Public License (http://www.gnu.org/licenses/gpl.txt)          
# for more details.                                               

import os
import math
import numpy as np

import time

# PYTORCH
import torch

# DEEP EXTREME
import models.deeplab_resnet as resnet
from models.dataloaders import helpers as helpers

# DEEPLAB V3+
from models.deeplab import DeepLab

from PyQt5.QtCore import QCoreApplication, Qt, QObject, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QImage, QColor, QPixmap, qRgb, qRed, qGreen, qBlue

from source.Labels import Labels
from source import utils

class MapClassifier(QObject):
    """
    Given the name of the classifier, the MapClassifier loads and creates it. T
    The interface is common to all the classifier, a map is subdivide into overlapping tiles,
    the tiles are classified, the scores aggregated and put together to form the final
    classification map.
    """

    # custom signal
    updateProgress = pyqtSignal(float)

    def __init__(self, classifier_info, parent=None):
        super(QObject, self).__init__(parent)

        self.label_colors = []

        self.classifier_name = classifier_info['Classifier Name']
        self.nclasses = classifier_info['Num. Classes']
        self.label_names = classifier_info['Classes']

        labels_info = Labels()
        for label_name in self.label_names:
            color = labels_info.getColorByName(label_name)
            self.label_colors.append(color)

        self.average_norm = classifier_info['Average Norm.']
        self.net = self._load_classifier(classifier_info['Weights'])

        self.flagStopProcessing = False
        self.processing_step = 0
        self.total_processing_steps = 0


    def _load_classifier(self, modelName):

        models_dir = "models/"

        network_name = os.path.join(models_dir, modelName)

        classifier_pocillopora = DeepLab(backbone='resnet', output_stride=16, num_classes=self.nclasses)
        classifier_pocillopora.load_state_dict(torch.load(network_name))

        classifier_pocillopora.eval()

        return classifier_pocillopora


    def run(self, img_map, TILE_SIZE, AGGREGATION_WINDOW_SIZE, AGGREGATION_STEP):
        """

        :param TILE_SIZE: Base tile. This corresponds to the INPUT SIZE of the network.
        :param AGGREGATION_WINDOW_SIZE: Size of the sub-windows to consider for the aggregation.
        :param AGGREGATION_STEP: Step, in pixels, to calculate the different scores.
        :return:
        """

        # create a temporary folder to store the processing
        temp_dir = "temp"
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)

        # prepare for running..
        STEP_SIZE = AGGREGATION_WINDOW_SIZE

        W = img_map.width()
        H = img_map.height()

        DSZ = TILE_SIZE - AGGREGATION_WINDOW_SIZE

        tile_cols = int((W-DSZ) / AGGREGATION_WINDOW_SIZE)
        tile_rows = int((H-DSZ) / AGGREGATION_WINDOW_SIZE)

        if torch.cuda.is_available():
            device = torch.device("cuda")
            self.net.to(device)
            torch.cuda.synchronize()

        self.net.eval()

        # classification (per-tiles)
        tiles_number = tile_rows * tile_cols

        self.processing_step = 0
        self.total_processing_steps = 19 * tiles_number

        for row in range(tile_rows):

            if self.flagStopProcessing is True:
                break

            for col in range(tile_cols):

                if self.flagStopProcessing is True:
                    break

                scores = np.zeros((9, self.nclasses, TILE_SIZE, TILE_SIZE))

                k = 0
                for i in range(-1,2):
                    for j in range(-1,2):

                        top = row * STEP_SIZE + i * AGGREGATION_STEP
                        left = col * STEP_SIZE + j * AGGREGATION_STEP
                        cropimg = utils.cropQImage(img_map, [top, left, TILE_SIZE, TILE_SIZE])
                        img_np = utils.qimageToNumpyArray(cropimg)

                        img_np = img_np.astype(np.float32)
                        img_np = img_np / 255.0

                        # H x W x C --> C x H x W
                        img_np = img_np.transpose(2, 0, 1)

                        # Normalization (average subtraction)
                        img_np[0] = img_np[0] - self.average_norm[0]
                        img_np[1] = img_np[1] - self.average_norm[1]
                        img_np[2] = img_np[2] - self.average_norm[2]

                        with torch.no_grad():

                            img_tensor = torch.from_numpy(img_np)
                            input = img_tensor.unsqueeze(0)

                            if torch.cuda.is_available():
                                input = input.to(device)

                            outputs = self.net(input)

                            scores[k] = outputs[0].cpu().numpy()
                            k = k + 1

                            self.processing_step += 1
                            self.updateProgress.emit( (100.0 * self.processing_step) / self.total_processing_steps )
                            QCoreApplication.processEvents()


                if self.flagStopProcessing is True:
                    break

                start = time.time()

                preds_avg, preds_bayesian = self.aggregateScores(scores, tile_sz=TILE_SIZE,
                                                    center_window_size=AGGREGATION_WINDOW_SIZE, step=AGGREGATION_STEP)

                end = time.time()

                print(end-start)

                values_t, predictions_t = torch.max(torch.from_numpy(preds_avg), 0)
                preds = predictions_t.cpu().numpy()

                resimg = np.zeros((preds.shape[0], preds.shape[1], 3), dtype='uint8')

                for label_index in range(self.nclasses):
                    resimg[preds == label_index, :] = self.label_colors[label_index]

                tilename = str(row) + "_" + str(col) + ".png"
                filename = os.path.join(temp_dir, tilename)
                utils.rgbToQImage(resimg).save(filename)

                self.processing_step += 1
                self.updateProgress.emit( (100.0 * self.processing_step) / self.total_processing_steps )
                QCoreApplication.processEvents()

        # put tiles together
        qimglabel = QImage(W, H, QImage.Format_RGB32)

        DW = int(DSZ/2)
        DH = int(DSZ/2)

        xoffset = 0
        yoffset = 0

        painter = QPainter(qimglabel)

        for r in range(tile_rows):
            for c in range(tile_cols):
                tilename = str(r) + "_" + str(c) + ".png"
                filename = os.path.join(temp_dir, tilename)
                qimg = QImage(filename)

                print(".")

                xoffset = DW + c * AGGREGATION_WINDOW_SIZE
                yoffset = DH + r * AGGREGATION_WINDOW_SIZE

                painter.drawImage(xoffset, yoffset, qimg)

        # detach the qimglabel otherwise the Qt EXPLODES when memory is free
        painter.end()

        labelfile = os.path.join(temp_dir, "labelmap.png")
        qimglabel.save(labelfile)

        torch.cuda.empty_cache()
        del self.net
        self.net = None

    def stopProcessing(self):

        self.flagStopProcessing = True

    def aggregateScores(self, scores, tile_sz, center_window_size, step):
        """
        Calcute the classification scores using a Bayesian fusion aggregation.
        """""

        nscores = scores.shape[0]
        nclasses = scores.shape[1]

        classification_scores = np.zeros((nscores, nclasses, center_window_size, center_window_size))
        scores_counter = np.zeros((center_window_size, center_window_size), dtype=np.int8)

        # aggregation limits
        top = int((tile_sz - center_window_size) / 2)
        left = int((tile_sz - center_window_size) / 2)

        k = 0
        for i in range(-1,2):
            for j in range(-1,2):

                x1dest = j * step - left
                y1dest = i * step - top

                x2dest = x1dest + tile_sz-1
                y2dest = y1dest + tile_sz-1

                x1src = 0
                if x1dest < 0:
                    x1src = -x1dest
                    x1dest = 0

                y1src = 0
                if y1dest < 0:
                    y1src = -y1dest
                    y1dest = 0

                if x2dest > center_window_size:
                    x2dest = center_window_size

                if y2dest > center_window_size:
                    y2dest = center_window_size

                x2src = x1src + x2dest - x1dest
                y2src = y1src + y2dest - y1dest

                classification_scores[k, :, y1dest:y2dest, x1dest:x2dest] = scores[k, :, y1src:y2src, x1src:x2src]
                scores_counter[y1dest:y2dest, x1dest:x2dest] += 1

                k = k + 1

                self.processing_step += 1
                self.updateProgress.emit( (100.0 * self.processing_step) / self.total_processing_steps )
                QCoreApplication.processEvents()

        #####   AGGREGATE SCORES BY AVERAGING THEM   ##################################################

        # NOTE: SOME APPROACHES AVERAGE THE SCORES DIRECTLY, OTHER ONES AVERAGE THE OUTPUT OF THE SOFTMAX
        #       HERE, WE AVERAGE THE OUTPUT OF THE SOFTMAX

        softmax = torch.nn.Softmax(dim=0)

        classification_scores_avg = np.zeros((nclasses, center_window_size, center_window_size))
        for i in range(nscores):
            prob = softmax(torch.from_numpy(classification_scores[i]))
            classification_scores_avg = classification_scores_avg + prob.numpy()

        classification_scores_avg = classification_scores_avg / nscores

        #####   AGGREGATE SCORES USING BAYESIAN FUSION   #############################################

        # NOTE THAT:
        #                                              _____
        #                                               | |
        #               p(y|s_N , s_N-1 , s_0) =  p(y)  | |  p(s_i | y)
        #                                             i=0..N
        # CORRESPONDS TO:
        #                                                          __
        #                                                      (   \                )
        #               p(y|s_N , s_N-1 , s_0) =  p(y) SOFTMAX (   /   p(s_i | y))  )
        #                                                      (   ==               )
        #                                                        i=0..N
        #
        # THIS AVOID NUMERICAL PROBLEMS FOR PRODUCTS WITH MANY TERMS.

        # bayesian aggregation
        classification_scores_bayes = np.zeros((nclasses, center_window_size, center_window_size))

        for i in range(nscores):
            classification_scores_bayes = classification_scores_bayes + classification_scores[i]

        classification_scores_bayesian = np.zeros((nclasses, center_window_size, center_window_size))

        res = softmax(torch.from_numpy(classification_scores_bayes))

        # PRIOR probabilities
        prior = [0.7, 0.1, 0.1, 0.1]

        for i in range(nclasses):
            classification_scores_bayesian[i] = prior[i] * res[i].numpy()

        return classification_scores_avg, classification_scores_bayesian

