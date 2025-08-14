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
    QHBoxLayout, QVBoxLayout, QMessageBox, QGroupBox, QGridLayout, QSizePolicy, QRadioButton, QCheckBox
import os
import glob
from PIL import Image
import numpy as np
import shutil
import sys
import random


import models.training as training
from models.coral_dataset import CoralsDataset
from source.QtProgressBarCustom import QtProgressBarCustom


class QtDatasetManagerWidget(QWidget):

    launchTraining = pyqtSignal()

    def __init__(self, labels, taglab_version, parent=None):
        super(QtDatasetManagerWidget, self).__init__(parent)

        self.project_labels = labels
        self.TAGLAB_VERSION = taglab_version

        self.target_classes = None
        self.freq_classes = None

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        TEXT_SPACE = 240

        ###### Labels

        lblDatasetInputFolder = QLabel("Dataset input folder: ")
        lblDatasetInputFolder.setMinimumWidth(TEXT_SPACE)
        lblDatasetInputFolder.setAlignment(Qt.AlignRight)

        lblTargetClasses = QLabel("Target classes: ")
        lblTargetClasses.setMinimumWidth(TEXT_SPACE)
        lblTargetClasses.setAlignment(Qt.AlignRight)

        lblDatasetOutputFolder = QLabel("Dataset output folder: ")
        lblDatasetOutputFolder.setMinimumWidth(TEXT_SPACE)
        lblDatasetOutputFolder.setAlignment(Qt.AlignRight)

        lblFiltering = QLabel("Filtering options: ")
        lblFiltering.setMinimumWidth(TEXT_SPACE)
        lblFiltering.setAlignment(Qt.AlignRight)

        lblAmount = QLabel("Amount (%): ")
        lblAmount2 = QLabel("Amount (%): ")

        #### Checkboxes

        self.checkRemove = QRadioButton("Remove No data tile")
        self.radio_ThresholdBackground  = QRadioButton("Remove tiles where the background classes exceeds:")
        self.radio_ThresholdBackground.setStyleSheet("QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }")
        self.radio_ThresholdBackground.setToolTip("The background classes are all the non-selected classes.")
        self.radio_SubsampleBackground = QRadioButton("Randomly subsamples the background classes by:")
        self.radio_SubsampleBackground.setStyleSheet("QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }")
        self.radio_SubsampleBackground.setToolTip("The background classes are all the non-selected classes.")


        ##### Edits

        LINEWIDTH = 300
        self.editInputDatasetFolder = QLineEdit("")
        self.editInputDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editInputDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.editInputDatasetFolder.setReadOnly(True)
        self.editInputDatasetFolder.setPlaceholderText("Select the path of the input dataset")
        self.editOutputDatasetFolder = QLineEdit("")
        self.editOutputDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editOutputDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.editOutputDatasetFolder.setPlaceholderText("Select the path of the filtered dataset")
        self.editOutputDatasetFolder.setReadOnly(True)
        self.groupbox_classes = self.createClassesToRecognizeWidgets()
        self.editAmount1 = QLineEdit()
        self.editAmount1.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editAmount1.setReadOnly(False)
        self.editAmount1.setMinimumWidth(LINEWIDTH)
        self.editAmount1.setMaximumWidth(LINEWIDTH+150)
        self.editAmount1.setPlaceholderText("Type an integer between 1 and 100")
        self.editAmount2 = QLineEdit()
        self.editAmount2.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editAmount2.setReadOnly(False)
        self.editAmount2.setMinimumWidth(LINEWIDTH)
        self.editAmount2.setMaximumWidth(LINEWIDTH+150)
        self.editAmount2.setPlaceholderText("Type an integer between 1 and 100")

        ###### Buttons

        self.btnChooseDatasetInputFolder = QPushButton("...")
        self.btnChooseDatasetInputFolder.setMaximumWidth(20)
        self.btnChooseDatasetInputFolder.clicked.connect(self.chooseDatasetInputFolder)


        self.btnChooseDatasetOutputFolder = QPushButton("...")
        self.btnChooseDatasetOutputFolder.setMaximumWidth(20)
        self.btnChooseDatasetOutputFolder.clicked.connect(self.chooseDatasetOutputFolder)

        ###### Layouts

        layoutLbls = QVBoxLayout()
        layoutLbls.addWidget(lblDatasetInputFolder)
        layoutLbls.addStretch()
        layoutLbls.addWidget(lblTargetClasses)
        layoutLbls.addStretch()
        layoutLbls.addWidget(lblDatasetOutputFolder)

        layoutEdits = QVBoxLayout()
        layoutEdits.addWidget(self.editInputDatasetFolder)
        self.layoutClasses = QHBoxLayout()
        self.layoutClasses.addWidget(self.groupbox_classes)
        layoutEdits.addLayout(self.layoutClasses)
        layoutEdits.addWidget(self.editOutputDatasetFolder)

        layoutBtns = QVBoxLayout()
        spaceButton = QPushButton(" ")
        spaceButton.hide()
        layoutBtns.addWidget(self.btnChooseDatasetInputFolder)
        layoutBtns.addStretch()
        layoutBtns.addWidget(self.btnChooseDatasetOutputFolder)

        self.layoutIO = QHBoxLayout()
        self.layoutIO.addLayout(layoutLbls)
        self.layoutIO.addLayout(layoutEdits)
        self.layoutIO.addLayout(layoutBtns)

        # filtering options

        layoutAmount1 = QHBoxLayout()
        layoutAmount1.addWidget(lblAmount)
        layoutAmount1.addWidget(self.editAmount1)
        layoutAmount1.addStretch()

        layoutAmount2 = QHBoxLayout()
        layoutAmount2.addWidget(lblAmount2)
        layoutAmount2.addWidget(self.editAmount2)
        layoutAmount2.addStretch()


        layoutOptions = QVBoxLayout()
        layoutOptions.setAlignment(Qt.AlignLeft)
        layoutOptions.addWidget(self.checkRemove)
        layoutOptions.addWidget(self.radio_ThresholdBackground)
        layoutOptions.addLayout(layoutAmount1)
        layoutOptions.addWidget(self.radio_SubsampleBackground)
        layoutOptions.addLayout(layoutAmount2)

        self.layoutFilters = QHBoxLayout()
        self.layoutFilters.addWidget(lblFiltering)
        self.layoutFilters.addLayout(layoutOptions)

        self.layoutMain = QVBoxLayout()
        self.layoutMain.addLayout(self.layoutIO)
        self.layoutMain.addSpacing(12)
        self.layoutMain.addLayout(self.layoutFilters)


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
        layoutFinal.addSpacing(6)
        layoutFinal.addLayout(layoutBottomButtons)
        self.setLayout(layoutFinal)

        self.setWindowTitle("Dataset Manager - Tiles Filtering Options")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.progress_bar = QtProgressBarCustom(parent=self)
        self.progress_bar.setWindowFlags(Qt.ToolTip | Qt.CustomizeWindowHint)
        self.progress_bar.setWindowModality(Qt.NonModal)
        self.progress_bar.hide()

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
            self.layoutClasses.insertWidget(0,self.groupbox_classes)

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

    def discard_image_tiles_with_uniform_colors(self, TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_OUTPUT_IMAGES, TRAINING_OUTPUT_LABELS):
        """
        Discard "flat" RGB images.
        """

        tiles_removed = 0

        path = os.path.join(TRAINING_FOLDER_IMAGES)

        images_names = [x for x in glob.glob(os.path.join(path, '*.png'))]
        N_tiles = len(images_names)

        i = 0
        for image_name in images_names:

            pil_img = Image.open(image_name)
            img = np.array(pil_img)

            red = img[:, :, 0]
            green = img[:, :, 1]
            blue = img[:, :, 2]

            red_var = np.var(red)
            green_var = np.var(green)
            blue_var = np.var(blue)

            total_var = red_var + green_var + blue_var

            if total_var < 100.0:
                tiles_removed += 1  # tiles not copied in the new dataset
            else:
                # copy in new training dataset
                basename = os.path.basename(image_name)
                outimg = os.path.join(TRAINING_OUTPUT_IMAGES, basename)
                inlabel= os.path.join(TRAINING_FOLDER_LABELS, basename)
                outlabel = os.path.join(TRAINING_OUTPUT_LABELS, basename)

                shutil.copy(image_name, outimg)
                shutil.copy(inlabel, outlabel)

            i = i + 1
            if i % 10 == 0:
                perc = (i * 100.0) / N_tiles
                self.progress_bar.setProgress(perc)
                QApplication.processEvents()

        return tiles_removed

    def filter(self):

        # we only filter the training tiles (test and validation are copied in the filtered dataset)

        tiles_discarded = 0

        # set up progress bar
        pos_x = self.pos().x() + self.btnHelp.pos().x() - 80
        pos_y = self.pos().y() + self.editAmount1.pos().y() + self.editAmount1.height()

        self.progress_bar.move(int(pos_x), int(pos_y))
        self.progress_bar.setMessage("Initializing..")
        self.progress_bar.hidePerc()
        self.progress_bar.show()
        QApplication.processEvents()

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

        TRAINING_OUTPUT = os.path.join(output_folder, "training")
        TRAINING_OUTPUT_IMAGES = os.path.join(TRAINING_OUTPUT, "images")
        TRAINING_OUTPUT_LABELS = os.path.join(TRAINING_OUTPUT, "labels")

        # create output folders

        if not os.path.exists(TRAINING_OUTPUT):
            os.mkdir(TRAINING_OUTPUT)

        if not os.path.exists(TRAINING_OUTPUT_IMAGES):
            os.mkdir(TRAINING_OUTPUT_IMAGES)

        if not os.path.exists(TRAINING_OUTPUT_LABELS):
            os.mkdir(TRAINING_OUTPUT_LABELS)

        if self.checkRemove.isChecked():
            self.progress_bar.showPerc()
            self.progress_bar.setMessage("Removing no data tiles..")
            QApplication.processEvents()
            tiles_discarded += self.discard_image_tiles_with_uniform_colors(TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_OUTPUT_IMAGES, TRAINING_OUTPUT_LABELS)

        if self.radio_ThresholdBackground.isChecked():
            perc = self.editAmount1.text()
            if perc.isdigit():
                value = int(perc)
                if 1 <= value <= 100:
                    tiles_discarded += self.subsample(TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_OUTPUT_IMAGES, TRAINING_OUTPUT_LABELS, flag=1)
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
                    self.subsample(TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_OUTPUT_IMAGES,
                                   TRAINING_OUTPUT_LABELS, flag=2)
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

        if tiles_discarded > 0:
            # the input dataset becomes the new dataset
            self.editInputDatasetFolder.setText(self.editOutputDatasetFolder.text())
            self.editOutputDatasetFolder.setText("")

            self.progress_bar.hidePerc()
            self.progress_bar.setMessage("Copying tiles..")

            VALIDATION_FOLDER = os.path.join(input_folder, "validation")
            VALIDATION_OUTPUT_FOLDER = os.path.join(output_folder, "validation")
            shutil.copytree(VALIDATION_FOLDER, VALIDATION_OUTPUT_FOLDER, dirs_exist_ok=True)

            TEST_FOLDER = os.path.join(input_folder, "test")
            TEST_OUTPUT_FOLDER = os.path.join(output_folder, "test")
            shutil.copytree(TEST_FOLDER, TEST_OUTPUT_FOLDER, dirs_exist_ok=True)

            PIXEL_SIZE_FILE = os.path.join(input_folder, "target-pixel-size.txt")
            shutil.copy(PIXEL_SIZE_FILE, output_folder)

            self.updateStatistics()
        else:
            box = QMessageBox()
            box.setWindowTitle(self.TAGLAB_VERSION)
            box.setText("WARNING! No tiles have been discarded. The new dataset is equal to the original one.")
            box.exec()

        self.editAmount1.clear()
        self.editAmount2.clear()


    @pyqtSlot()
    def subsample(self, TRAINING_FOLDER_IMAGES, TRAINING_FOLDER_LABELS, TRAINING_OUTPUT_IMAGES, TRAINING_OUTPUT_LABELS, flag):

        """
        Remove a percentage of the tiles that not contains a specific class.
        If perc=100 all the tiles that not contain a specific class are removed.
        Can be customized, the moment the specific class is set to Background
        """

        tiles_removed = 0

        background_classes = self.target_classes.copy()
        for checkbox in self.checkboxes:
            if not checkbox.isChecked():
                key = checkbox.text()
                del background_classes[key]

        # re-add Background
        background_classes["Background"] = [0,0,0]

        background_classes_color = []
        for key in background_classes:
            if key == "Background":
                color = [0,0,0]
            else:
                label = self.project_labels[key]
                color = label.fill
            background_classes_color.append(color)

        labels_names = glob.glob(os.path.join(TRAINING_FOLDER_LABELS, '*.png'))
        self.flag = flag

        self.progress_bar.showPerc()
        if self.flag == 1:
            self.progress_bar.setMessage("Removing tiles..")

        if self.flag == 2:
            self.progress_bar.setMessage("Subsampling background tiles..")

        QApplication.processEvents()

        ##### SHUFFLE LABELS NAMES

        N_tiles = len(labels_names)
        for k in range(10000):
            i = random.randint(0, N_tiles - 1)
            j = random.randint(0, N_tiles - 1)
            temp_name = labels_names[j]
            labels_names[j] = labels_names[i]
            labels_names[i] = temp_name

        i = 0
        for label_path in labels_names:

            pil_img = Image.open(label_path)
            img = np.array(pil_img)

            npixels = img.shape[0] * img.shape[1]

            background_pixels = 0
            for color in background_classes_color:
                M = (img[:, :, 0] == color[0]) & (img[:, :, 1] == color[1]) & (img[:, :, 2] == color[2])
                background_pixels += np.count_nonzero(M)

            p = background_pixels / npixels
            coin = random.randint(0, 9999) / 100

            if self.flag == 1 and p > int(self.editAmount1.text()) / 100.0:
                tiles_removed += 1  # tile not copied in the new dataset
            else:

                image_filename = os.path.basename(label_path)

                img_src = os.path.join(TRAINING_FOLDER_IMAGES, image_filename)
                img_dest = os.path.join(TRAINING_OUTPUT_IMAGES , image_filename)

                label_src = os.path.join(TRAINING_FOLDER_LABELS, image_filename)
                label_dest = os.path.join(TRAINING_OUTPUT_LABELS, image_filename)

                shutil.copy(img_src, img_dest)
                shutil.copy(label_src, label_dest)

            if (self.flag == 2) and (p > 0.999) and (coin < int(self.editAmount2.text())):
                tiles_removed += 1  # tile not copied in the new dataset
            else:

                image_filename = os.path.basename(label_path)

                img_src = os.path.join(TRAINING_FOLDER_IMAGES, image_filename)
                img_dest = os.path.join(TRAINING_OUTPUT_IMAGES , image_filename)

                label_src = os.path.join(TRAINING_FOLDER_LABELS, image_filename)
                label_dest = os.path.join(TRAINING_OUTPUT_LABELS, image_filename)

                shutil.copy(img_src, img_dest)
                shutil.copy(label_src, label_dest)

            i = i + 1
            if i % 10 == 0:
                perc = (i * 100.0) / N_tiles
                self.progress_bar.setProgress(perc)
                QApplication.processEvents()

        self.progress_bar.hide()
        QApplication.processEvents()

        return tiles_removed

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
            self.layoutClasses.insertWidget(0, self.groupbox_classes)
