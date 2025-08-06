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

from PyQt5.Qt import QDesktopServices
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout, QMessageBox, QGroupBox, QGridLayout, QCheckBox, QSizePolicy, QRadioButton
import os
import glob
from PIL import Image
import numpy as np
import shutil
import sys
import random


import models.training as training
from models.coral_dataset import CoralsDataset
class QtDatasetManagerWidget(QWidget):

    launchTraining = pyqtSignal()

    def __init__(self, labels, taglab_version, parent=None):
        super(QtDatasetManagerWidget, self).__init__(parent)

        self.project_labels = labels
        self.TAGLAB_VERSION = taglab_version

        self.target_classes = None
        self.freq_classes = None

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        TEXT_SPACE = 200

        ###### Labels

        lblDatasetInputFolder = QLabel("Dataset input folder: ")
        lblDatasetInputFolder.setMinimumWidth(TEXT_SPACE)
        lblDatasetInputFolder.setAlignment(Qt.AlignRight)

        lblTargetClasses = QLabel("Classes to recognize: ")
        lblTargetClasses.setMinimumWidth(TEXT_SPACE)
        lblTargetClasses.setAlignment(Qt.AlignRight)

        lblDatasetOutputFolder = QLabel("Dataset Output folder: ")
        lblDatasetOutputFolder.setMinimumWidth(TEXT_SPACE)
        lblDatasetOutputFolder.setAlignment(Qt.AlignRight)

        lblFiltering = QLabel("Filtering options: ")
        lblFiltering.setMinimumWidth(TEXT_SPACE)
        lblFiltering.setAlignment(Qt.AlignRight)

        lblAmount = QLabel("Amount (%): ")
        lblAmount2 = QLabel("Amount (%): ")

        #### Checkboxes

        self.checkRemove = QRadioButton("Remove No data tile")
        self.radio_ThresholdBackground  = QRadioButton("Threshold tiles where the Background class exceeds:")
        self.radio_SubsampleBackground = QRadioButton("Randomly subsamples the background class by:")


        ##### Edits

        LINEWIDTH = 300
        self.editInputDatasetFolder = QLineEdit("")
        self.editInputDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editInputDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.editInputDatasetFolder.setPlaceholderText("Insert here the dataset folder")
        self.editOutputDatasetFolder = QLineEdit("")
        self.editOutputDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editOutputDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.editOutputDatasetFolder.setPlaceholderText("Insert here the dataset folder")
        self.groupbox_classes = self.createClassesToRecognizeWidgets()
        self.editEpochs = QLineEdit("10")
        self.editEpochs.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editEpochs.setMinimumWidth(LINEWIDTH)
        self.editEpochs.setReadOnly(False)
        self.editAmount1 = QLineEdit()
        self.editAmount1.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editAmount1.setReadOnly(False)
        self.editAmount1.setMinimumWidth(LINEWIDTH)
        self.editAmount1.setPlaceholderText("Type an integer between 1 and 100")
        self.editAmount2 = QLineEdit()
        self.editAmount2.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editAmount2.setReadOnly(False)
        self.editAmount2.setMinimumWidth(LINEWIDTH)
        self.editAmount2.setPlaceholderText("Type an integer between 1 and 100")

        ###### Buttons

        self.btnChooseDatasetInputFolder = QPushButton("...")
        self.btnChooseDatasetInputFolder.setMaximumWidth(20)
        self.btnChooseDatasetInputFolder.clicked.connect(self.chooseDatasetInputFolder)


        self.btnChooseDatasetOutputFolder = QPushButton("...")
        self.btnChooseDatasetOutputFolder.setMaximumWidth(20)
        self.btnChooseDatasetOutputFolder.clicked.connect(self.chooseDatasetOutputFolder)

        ###### Layouts

        layoutInputDataset = QHBoxLayout()
        layoutInputDataset.addWidget(lblDatasetInputFolder)
        layoutInputDataset.addWidget(self.editInputDatasetFolder)
        layoutInputDataset.addWidget(self.btnChooseDatasetInputFolder)

        self.layoutClasses = QHBoxLayout()
        self.layoutClasses.addWidget(lblTargetClasses)
        self.layoutClasses.addWidget(self.groupbox_classes)

        layoutOutputDataset = QHBoxLayout()
        layoutOutputDataset.addWidget(lblDatasetOutputFolder)
        layoutOutputDataset.addWidget(self.editOutputDatasetFolder)
        layoutOutputDataset.addWidget(self.btnChooseDatasetOutputFolder)

        layoutAmount1 = QHBoxLayout()
        layoutAmount1.addWidget(lblAmount)
        layoutAmount1.addWidget(self.editAmount1)

        layoutAmount2 = QHBoxLayout()
        layoutAmount2.addWidget(lblAmount2)
        layoutAmount2.addWidget(self.editAmount2)


        layoutOptions = QVBoxLayout()
        layoutOptions.addWidget(self.checkRemove)
        layoutOptions.addWidget(self.radio_ThresholdBackground)
        layoutOptions.addLayout(layoutAmount1)
        layoutOptions.addWidget(self.radio_SubsampleBackground)
        layoutOptions.addLayout(layoutAmount2)


        self.layoutfilters = QHBoxLayout()
        self.layoutfilters.addWidget(lblFiltering)
        self.layoutfilters.addLayout(layoutOptions)


        self.layoutInputs = QVBoxLayout()
        self.layoutInputs.addLayout(layoutInputDataset)
        self.layoutInputs.addLayout(self.layoutClasses)
        self.layoutInputs.addLayout(layoutOutputDataset)
        self.layoutInputs.addSpacing(30)
        self.layoutInputs.addLayout(self.layoutfilters)
        ##### Main layout

        self.layoutMain = QHBoxLayout()
        self.layoutMain.addLayout(self.layoutInputs)

        ###########################################################


        self.btnHelp = QPushButton("Help")
        self.btnHelp.clicked.connect(self.help)
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnFilter = QPushButton("Filter")
        self.btnFilter.clicked.connect(self.filter)

        layoutBottomButtons = QHBoxLayout()
        layoutBottomButtons.setAlignment(Qt.AlignRight)
        layoutBottomButtons.addStretch()
        layoutBottomButtons.addWidget(self.btnHelp)
        layoutBottomButtons.addWidget(self.btnCancel)
        layoutBottomButtons.addWidget(self.btnFilter)

        ###########################################################

        layoutFinal = QVBoxLayout()
        layoutFinal.addLayout(self.layoutMain)
        layoutFinal.addLayout(layoutBottomButtons)
        self.setLayout(layoutFinal)

        self.setWindowTitle("Dataset Manager - Tiles Filtering Options")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.checkboxes = []

    @pyqtSlot()
    def chooseDatasetInputFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose Your Dataset Folder", "")
        if folderName:
            self.editInputDatasetFolder.setText(folderName)

            box = QMessageBox()
            box.setWindowTitle(self.TAGLAB_VERSION)
            box.setText("The dataset will be analyzed. This may take some minutes, please wait.. ")
            box.setStandardButtons(QMessageBox.NoButton)
            box.show()
            QApplication.processEvents()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.analyzeDataset()
            QApplication.restoreOverrideCursor()
            box.close()

            self.layoutClasses.removeWidget(self.groupbox_classes)
            self.groupbox_classes.setParent(None)
            self.groupbox_classes = None
            self.groupbox_classes = self.createClassesToRecognizeWidgets()
            self.layoutClasses.insertWidget(1, self.groupbox_classes)

    @pyqtSlot()
    def chooseDatasetOutputFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose Your Dataset Folder", "")
        if folderName:
            self.editOutputDatasetFolder.setText(folderName)


    @pyqtSlot()
    def help(self):

        url = QUrl("http://taglab.isti.cnr.it/docs")
        QDesktopServices.openUrl(url)

    def getInputDatasetFolder(self):

        return self.editInputDatasetFolder.text()

    def getTargetClasses(self):

        target_classes = self.target_classes.copy()

        for checkbox in self.checkboxes:
            if not checkbox.isChecked():
                key = checkbox.text()
                del target_classes[key]

        del target_classes["Background"]
        count = 1
        for key in target_classes.keys():
            target_classes[key] = count
            count += 1
        target_classes["Background"] = 0

        return target_classes

    def createClassesToRecognizeWidgets(self):

        groupbox = QGroupBox()
        groupbox.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        if self.freq_classes is None:
            lbl = QLabel("No class founds in the dataset.")
            layout = QVBoxLayout()
            layout.addWidget(lbl)
            groupbox.setLayout(layout)
        else:
            grid_layout = QGridLayout()
            groupbox.setLayout(grid_layout)

            self.checkboxes = []
            CLASSES_PER_ROW = 3
            for i, key in enumerate(self.freq_classes.keys()):
                perc = round(self.freq_classes[key] * 100.0, 2)

                checkbox = QCheckBox(key)
                checkbox.setChecked(True)
                lbl_perc = QLabel(" " + str(perc) + "%")
                if perc < 5.0:
                    lbl_perc.setStyleSheet("QLabel { background-color : rgb(40,40,40); color : red; }")
                else:
                    lbl_perc.setStyleSheet("QLabel { background-color : rgb(40,40,40); color : green; }")

                if key == "Background":
                    checkbox.setAttribute(Qt.WA_TransparentForMouseEvents)
                    checkbox.setFocusPolicy(Qt.NoFocus)

                self.checkboxes.append(checkbox)

                btnC = QPushButton("")
                btnC.setFlat(True)

                label = self.project_labels.get(key)
                if label is not None:
                    color = label.fill
                else:
                    color = [0,0,0]

                r = color[0]
                g = color[1]
                b = color[2]
                text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(
                    b) + "); border: none ;}"

                btnC.setStyleSheet(text)
                btnC.setAutoFillBackground(True)
                btnC.setFixedWidth(20)
                btnC.setFixedHeight(20)

                hlayout = QHBoxLayout()
                hlayout.addWidget(btnC)
                hlayout.addWidget(lbl_perc)

                col = i % CLASSES_PER_ROW
                row = int(i / CLASSES_PER_ROW)
                grid_layout.addWidget(checkbox, row, col*2)
                grid_layout.addLayout(hlayout, row, col*2+1)

        return groupbox

    def analyzeDataset(self):

        # check dataset
        dataset_folder = self.editInputDatasetFolder.text()
        check = training.checkDataset(dataset_folder)
        if check > 0:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)

            if check == 1:
                msgBox.setText("Dataset folder does not exists. Please, check.")

            if check == 2:
                msgBox.setText("An error occured with your dataset, a subfolder is missing."
                               "Please, export a new dataset.")

            if check == 3:
                msgBox.setText("An error occured with your dataset, there is a mismatch between files. "
                               "Please, export a new dataset.")

            msgBox.exec()
            return

        # CLASSES TO RECOGNIZE (label name - label code)
        labels_folder = os.path.join(dataset_folder, "training")
        labels_folder = os.path.join(labels_folder, "labels")
        target_classes, freq_classes = CoralsDataset.importClassesFromDataset(labels_folder, self.project_labels)

        self.target_classes = target_classes
        self.freq_classes = freq_classes

    def discard_image_tiles_with_uniform_background(self, TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_TRASH_IMAGES, TRAINING_TRASH_LABELS):

        path = os.path.join(TRAINING_FOLDER_IMAGES)

        images_names = [x for x in glob.glob(os.path.join(path, '*.png'))]
        for image_name in images_names:

            pil_img = Image.open(image_name)
            img = np.array(pil_img)

            red = img[:, :, 0]
            green = img[:, :, 1]
            blue = img[:, :, 2]

            red_nononzero = red[red != 0]
            if len(red_nononzero) > 0:
                red_var = np.var(red_nononzero)
            green_nononzero = green[green != 0]
            if len(green_nononzero) > 0:
                green_var = np.var(green_nononzero)
            blue_nononzero = blue[blue != 0]
            if len(blue_nononzero) > 0:
                blue_var = np.var(blue_nononzero)

            total_var = red_var + green_var + blue_var

            if total_var < 10.0:
                basename = os.path.basename(image_name)
                outimg = os.path.join(TRAINING_TRASH_IMAGES, basename)
                inlabel= os.path.join(TRAINING_FOLDER_LABELS, basename)
                outlabel = os.path.join(TRAINING_TRASH_LABELS, basename)

                shutil.move(image_name, outimg)
                shutil.move(inlabel, outlabel)


    def filter(self):

        #we only filter the training tiles

        input_folder = self.editInputDatasetFolder.text()
        output_folder = self.editOutputDatasetFolder.text()

        if not os.path.exists(input_folder):
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("The Input folder does not exists.")
            msgBox.exec()
            return

        if not os.path.exists(output_folder):
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("The Output folder does not exists.")
            msgBox.exec()
            return

        TRAINING_FOLDER = os.path.join(input_folder, "training")

        if not os.path.exists(TRAINING_FOLDER):
            print("Training folder does not exists (!)")
            sys.exit(-1)


        TRAINING_FOLDER_IMAGES = os.path.join(TRAINING_FOLDER, "images")
        TRAINING_FOLDER_LABELS = os.path.join(TRAINING_FOLDER, "labels")

        TRAINING_TRASH = os.path.join(output_folder, "training")
        TRAINING_TRASH_IMAGES = os.path.join(TRAINING_TRASH, "images")
        TRAINING_TRASH_LABELS = os.path.join(TRAINING_TRASH, "labels")

        # create output folders

        if not os.path.exists(TRAINING_TRASH):
            os.mkdir(TRAINING_TRASH)

        if not os.path.exists(TRAINING_TRASH_IMAGES):
            os.mkdir(TRAINING_TRASH_IMAGES)

        if not os.path.exists(TRAINING_TRASH_LABELS):
            os.mkdir(TRAINING_TRASH_LABELS)

        if self.checkRemove.isChecked():
            self.discard_image_tiles_with_uniform_background(TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_TRASH_IMAGES, TRAINING_TRASH_LABELS)

        if self.radio_ThresholdBackground.isChecked():
            perc = self.editAmount1.text()
            if perc.isdigit():
                value = int(perc)
                if 1 <= value <= 100:
                    self.subsample(TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_TRASH_IMAGES, TRAINING_TRASH_LABELS, flag=1)
                else:
                    box = QMessageBox()
                    box.setWindowTitle(self.TAGLAB_VERSION)
                    box.setText("Please enter a number between 1 and 100r")
                    box.exec()
                    self.editAmount1.clear()
                    return
            else:
                box = QMessageBox()
                box.setWindowTitle(self.TAGLAB_VERSION)
                box.setText("Please enter a positive integer")
                box.exec()
                self.editAmount1.clear()
                return

        if self.radio_SubsampleBackground.isChecked():
            perc = self.editAmount2.text()
            if perc.isdigit():
                value = int(perc)
                if 1 <= value <= 100:
                    self.subsample(TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_TRASH_IMAGES,
                                   TRAINING_TRASH_LABELS, flag=2)
                else:
                    box = QMessageBox()
                    box.setWindowTitle(self.TAGLAB_VERSION)
                    box.setText("Please enter a number between 1 and 100r")
                    box.exec()
                    self.editAmount2.clear()
                    return
            else:
                box = QMessageBox()
                box.setWindowTitle(self.TAGLAB_VERSION)
                box.setText("Please enter a positive integer")
                box.exec()
                self.editAmount2.clear()
                return
        self.updateStatistics()
        self.editAmount1.clear()
        self.editAmount2.clear()


    @pyqtSlot()
    def subsample(self, TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_TRASH_IMAGES, TRAINING_TRASH_LABELS, flag):

        """
        Remove a percentage of the tiles that not contains a specific class.
        If perc=100 all the tiles that not contain a specific class are removed.
        Can be customized, the moment the specific class is set to Background
        """
        target_class_color = [0, 0, 0]
        labels_names = glob.glob(os.path.join(TRAINING_FOLDER_LABELS, '*.png'))
        self.flag= flag

        ##### SHUFFLE LABELS NAMES

        N_tiles = len(labels_names)
        for k in range(10000):
            i = random.randint(0, N_tiles - 1)
            j = random.randint(0, N_tiles - 1)
            temp_name = labels_names[j]
            labels_names[j] = labels_names[i]
            labels_names[i] = temp_name

        for label_path in labels_names:

            pil_img = Image.open(label_path)
            img = np.array(pil_img)

            npixels = img.shape[0] * img.shape[1]

            condition = np.where((img[:, :, 0] == target_class_color[0]) & (img[:, :, 1] == target_class_color[1]) & (
                        img[:, :, 2] == target_class_color[2]))

            pixels = len(list(zip(condition[0], condition[1])))
            p = pixels / npixels
            coin = random.randint(0, 99)

            if self.flag == 1 and p > int(self.editAmount1.text())/100:

                image_filename = os.path.basename(label_path)

                img_src = os.path.join(TRAINING_FOLDER_IMAGES, image_filename)
                img_dest = os.path.join(TRAINING_TRASH_IMAGES , image_filename)

                label_src = os.path.join(TRAINING_FOLDER_LABELS, image_filename)
                label_dest = os.path.join(TRAINING_TRASH_LABELS, image_filename)

                shutil.move(img_src, img_dest)
                shutil.move(label_src, label_dest)


            elif (self.flag == 2) and (p > 0.999) and (coin < int(self.editAmount2.text())):

                image_filename = os.path.basename(label_path)

                img_src = os.path.join(TRAINING_FOLDER_IMAGES, image_filename)
                img_dest = os.path.join(TRAINING_TRASH_IMAGES , image_filename)

                label_src = os.path.join(TRAINING_FOLDER_LABELS, image_filename)
                label_dest = os.path.join(TRAINING_TRASH_LABELS, image_filename)

                shutil.move(img_src, img_dest)
                shutil.move(label_src, label_dest)


    @pyqtSlot()
    def updateStatistics(self):

        folderName = self.editInputDatasetFolder.text()
        if folderName:

            box = QMessageBox()
            box.setWindowTitle(self.TAGLAB_VERSION)
            box.setText("The dataset will be analyzed again. This may take some minutes, please wait.. ")
            box.setStandardButtons(QMessageBox.NoButton)
            box.show()
            QApplication.processEvents()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.analyzeDataset()
            QApplication.restoreOverrideCursor()
            box.close()

            self.layoutClasses.removeWidget(self.groupbox_classes)
            self.groupbox_classes.setParent(None)
            self.groupbox_classes = None
            self.groupbox_classes = self.createClassesToRecognizeWidgets()
            self.layoutClasses.insertWidget(1, self.groupbox_classes)
