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
    QHBoxLayout, QVBoxLayout, QMessageBox, QGroupBox, QGridLayout, QCheckBox, QSizePolicy

from models.coral_dataset import CoralsDataset
import models.training as training


class QtTYNWidget(QWidget):

    launchTraining = pyqtSignal()

    def __init__(self, labels, taglab_version, parent=None):
        super(QtTYNWidget, self).__init__(parent)

        self.project_labels = labels
        self.TAGLAB_VERSION = taglab_version

        self.target_classes = None
        self.freq_classes = None

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        TEXT_SPACE = 200

        ###### Labels

        self.lblNetworkName = QLabel("Network name:")
        self.lblNetworkName.setMinimumWidth(TEXT_SPACE)
        self.lblNetworkName.setAlignment(Qt.AlignRight)

        self.lblDatasetFolder = QLabel("Dataset folder: ")
        self.lblDatasetFolder.setMinimumWidth(TEXT_SPACE)
        self.lblDatasetFolder.setAlignment(Qt.AlignRight)

        self.lblTargetClasses = QLabel("Classes to recognize: ")
        self.lblTargetClasses.setMinimumWidth(TEXT_SPACE)
        self.lblTargetClasses.setAlignment(Qt.AlignRight)

        self.lblEpochs = QLabel("Number of epochs:")
        self.lblEpochs.setMinimumWidth(TEXT_SPACE)
        self.lblEpochs.setAlignment(Qt.AlignRight)

        self.lblLR = QLabel("Learning Rate: ")
        self.lblLR.setMinimumWidth(TEXT_SPACE)
        self.lblLR.setAlignment(Qt.AlignRight)

        self.lblL2 = QLabel("L2 Regularization: ")
        self.lblL2.setMinimumWidth(TEXT_SPACE)
        self.lblL2.setAlignment(Qt.AlignRight)

        self.lblBS = QLabel("Batch Size: ")
        self.lblBS.setMinimumWidth(TEXT_SPACE)
        self.lblBS.setAlignment(Qt.AlignRight)

        ##### Edits

        LINEWIDTH = 500
        self.editNetworkName = QLineEdit("")
        self.editNetworkName.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editNetworkName.setMinimumWidth(LINEWIDTH)
        self.editNetworkName.setPlaceholderText("Insert here the name of your network")
        self.editNetworkName.setReadOnly(False)
        self.editDatasetFolder = QLineEdit("")
        self.editDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.editDatasetFolder.setPlaceholderText("Insert here the dataset folder")
        self.groupbox_classes = self.createClassesToRecognizeWidgets()
        self.editEpochs = QLineEdit("2")
        self.editEpochs.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editEpochs.setMinimumWidth(LINEWIDTH)
        self.editEpochs.setReadOnly(False)
        self.editLR = QLineEdit("0.00005")
        self.editLR.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editLR.setReadOnly(False)
        self.editLR.setMinimumWidth(LINEWIDTH)
        self.editL2 = QLineEdit("0.0005")
        self.editL2.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editL2.setReadOnly(False)
        self.editL2.setMinimumWidth(LINEWIDTH)
        self.editBatchSize = QLineEdit("4")
        self.editBatchSize.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editBatchSize.setReadOnly(False)
        self.editBatchSize.setMinimumWidth(LINEWIDTH)

        ###### Right button

        self.btnChooseDatasetFolder = QPushButton("...")
        self.btnChooseDatasetFolder.setMaximumWidth(20)
        self.btnChooseDatasetFolder.clicked.connect(self.chooseDatasetFolder)

        layoutH1 = QHBoxLayout()
        layoutH1.addWidget(self.lblNetworkName)
        layoutH1.addWidget(self.editNetworkName)

        layoutH2 = QHBoxLayout()
        layoutH2.addWidget(self.lblDatasetFolder)
        layoutH2.addWidget(self.editDatasetFolder)
        layoutH2.addWidget(self.btnChooseDatasetFolder)

        self.layoutClasses = QHBoxLayout()
        self.layoutClasses.addWidget(self.lblTargetClasses)
        self.layoutClasses.addWidget(self.groupbox_classes)

        layoutH4 = QHBoxLayout()
        layoutH4.addWidget(self.lblEpochs)
        layoutH4.addWidget(self.editEpochs)

        layoutH5 = QHBoxLayout()
        layoutH5.addWidget(self.lblLR)
        layoutH5.addWidget(self.editLR)

        layoutH6 = QHBoxLayout()
        layoutH6.addWidget(self.lblL2)
        layoutH6.addWidget(self.editL2)

        layoutH7 = QHBoxLayout()
        layoutH7.addWidget(self.lblBS)
        layoutH7.addWidget(self.editBatchSize)

        self.layoutInputs = QVBoxLayout()
        self.layoutInputs.addLayout(layoutH1)
        self.layoutInputs.addLayout(layoutH2)
        self.layoutInputs.addLayout(self.layoutClasses)
        self.layoutInputs.addLayout(layoutH4)
        self.layoutInputs.addLayout(layoutH5)
        self.layoutInputs.addLayout(layoutH6)
        self.layoutInputs.addLayout(layoutH7)


        ##### Main layout

        self.layoutMain = QHBoxLayout()
        self.layoutMain.addLayout(self.layoutInputs)

        ###########################################################

        self.btnHelp = QPushButton("Help")
        self.btnHelp.clicked.connect(self.help)
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnTrain = QPushButton("Train")
        self.btnTrain.clicked.connect(self.checkBeforeTraining)

        layoutBottomButtons = QHBoxLayout()
        layoutBottomButtons.setAlignment(Qt.AlignRight)
        layoutBottomButtons.addStretch()
        layoutBottomButtons.addWidget(self.btnHelp)
        layoutBottomButtons.addWidget(self.btnCancel)
        layoutBottomButtons.addWidget(self.btnTrain)

        ###########################################################

        layoutFinal = QVBoxLayout()
        layoutFinal.addLayout(self.layoutMain)
        layoutFinal.addLayout(layoutBottomButtons)
        self.setLayout(layoutFinal)

        self.setWindowTitle("Train Your Network - Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.checkboxes = []

    @pyqtSlot()
    def chooseDatasetFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose a Folder to Export the Dataset", "")
        if folderName:
            self.editDatasetFolder.setText(folderName)

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
    def help(self):

        url = QUrl("http://taglab.isti.cnr.it/docs")
        QDesktopServices.openUrl(url)

    def getDatasetFolder(self):

        return self.editDatasetFolder.text()

    def getEpochs(self):

        return int(self.editEpochs.text())

    def getLR(self):

        return float(self.editLR.text())

    def getWeightDecay(self):

        return float(self.editL2.text())

    def getBatchSize(self):

        return int(self.editBatchSize.text())

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

    @pyqtSlot()
    def checkBeforeTraining(self):

        dataset_Folder = self.editDatasetFolder.text()

        if not os.path.exists(self.editDatasetFolder.text()):
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Dataset folder does not exists.")
            msgBox.exec()
            return

        if self.editNetworkName.text() == "":
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("Please, enter a network name.")
            msgBox.exec()
            return

        if self.getEpochs() < 2:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("The minimum number of epoch is 2.")
            msgBox.exec()
            return

        self.launchTraining.emit()

    def analyzeDataset(self):

        # check dataset
        dataset_folder = self.editDatasetFolder.text()
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

