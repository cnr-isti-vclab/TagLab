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
    QHBoxLayout, QVBoxLayout, QMessageBox, QGroupBox, QGridLayout, QComboBox, QCheckBox, QSizePolicy

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

        TEXT_SPACE = 240

        ###### Labels

        self.lblNetworkName = QLabel("Network name:")
        self.lblNetworkName.setFixedWidth(TEXT_SPACE)
        self.lblNetworkName.setAlignment(Qt.AlignRight)

        self.lblDatasetFolder = QLabel("Dataset folder: ")
        self.lblDatasetFolder.setFixedWidth(TEXT_SPACE)
        self.lblDatasetFolder.setAlignment(Qt.AlignRight)

        self.lblTargetClasses = QLabel("Classes to recognize: ")
        self.lblTargetClasses.setFixedWidth(TEXT_SPACE)
        self.lblTargetClasses.setAlignment(Qt.AlignRight)

        self.lblTraining = QLabel("Training:")
        self.lblTraining.setFixedWidth(TEXT_SPACE)
        self.lblTraining.setAlignment(Qt.AlignRight)

        self.lblOptimizer = QLabel("Optimizer:")
        self.lblOptimizer.setFixedWidth(TEXT_SPACE)
        self.lblOptimizer.setAlignment(Qt.AlignRight)

        self.lblEpochs = QLabel("Number of epochs:")
        self.lblEpochs.setFixedWidth(TEXT_SPACE)
        self.lblEpochs.setAlignment(Qt.AlignRight)

        self.lblEpochsPerStage = QLabel("N. of epochs (per-stage):")
        self.lblEpochsPerStage.setFixedWidth(TEXT_SPACE)
        self.lblEpochsPerStage.setAlignment(Qt.AlignRight)

        self.lblLR = QLabel("Learning rate: ")
        self.lblLR.setFixedWidth(TEXT_SPACE)
        self.lblLR.setAlignment(Qt.AlignRight)

        self.lblL2 = QLabel("L2 regularization: ")
        self.lblL2.setFixedWidth(TEXT_SPACE)
        self.lblL2.setAlignment(Qt.AlignRight)

        self.lblBS = QLabel("Batch Size: ")
        self.lblBS.setFixedWidth(TEXT_SPACE)
        self.lblBS.setAlignment(Qt.AlignRight)

        self.lblTotalBackground = QLabel("Cumulative background: ")
        self.lblTotalBackground.setStyleSheet("QLabel { background-color : rgb(40,40,40); color : white; }")
        self.lblTotalBackgroundValue = QLabel("")
        self.lblTotalBackgroundValue.setStyleSheet("QLabel { background-color : rgb(40,40,40); color : white; }")

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
        self.editEpochs = QLineEdit("10")
        self.editEpochs.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editEpochs.setMinimumWidth(LINEWIDTH)
        self.editEpochs.setReadOnly(False)
        self.editEpochs.textEdited.connect(self.epochsChanged)
        self.editEpochsStage1 = QLineEdit("20")
        self.editEpochsStage1.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editEpochsStage1.setMinimumWidth(int(LINEWIDTH/3))
        self.editEpochsStage1.setReadOnly(False)
        self.editEpochsStage1.setToolTip("Number of epochs of the 1st phase of the fine-tuning (last layer is unfrozen).")
        self.editEpochsStage1.textEdited.connect(self.epochsStagesChanged)
        self.editEpochsStage2 = QLineEdit("20")
        self.editEpochsStage2.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editEpochsStage2.setMinimumWidth(int(LINEWIDTH/3))
        self.editEpochsStage2.setReadOnly(False)
        self.editEpochsStage2.setToolTip("Number of epochs of the 2nd phase of the fine-tuning (decoder is unfrozen, encoder is frozen).")
        self.editEpochsStage2.textEdited.connect(self.epochsStagesChanged)
        self.editEpochsStage3 = QLineEdit("20")
        self.editEpochsStage3.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editEpochsStage3.setMinimumWidth(int(LINEWIDTH/3))
        self.editEpochsStage3.setReadOnly(False)
        self.editEpochsStage3.setToolTip("Number of epochs of the 3rd phase of the fine-tuning (all the weights are update).")
        self.editEpochsStage3.textEdited.connect(self.epochsStagesChanged)
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


        self.comboTraining = QComboBox()
        self.comboTraining.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.comboTraining.addItem('Preset 1')
        self.comboTraining.addItem('Preset 2')
        self.comboTraining.setToolTip("In 'Preset 1' the training makes slight adjustments to all the weights of a DeepLab V3+ model.\n"
                                      "It is advised to use the recommended learning rate or a lower one.\n"
                                      "In 'Preset 2' the training unfreezes the weights of the final layer first, then the decoder layers, and finally the entire encoder.\n" 
                                      "This approach helps to prevent overfitting.\n" 
                                      "For more details, please refer to the documentation on the TagLab website."
                                      )
        self.comboTraining.currentTextChanged.connect(self.updateTrainingParameters)

        self.comboOptimizer = QComboBox()
        self.comboOptimizer.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.comboOptimizer.addItem('Adam')
        self.comboOptimizer.addItem('QHAdam')
        self.comboOptimizer.setToolTip("'Adam' is the typical solution, 'QHAdam' is a variant of the Adam optmizer\n"
                                       "that may provide better performance in some cases.")

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

        self.layoutTraining = QHBoxLayout()
        self.layoutTraining.addWidget(self.lblTraining)
        self.layoutTraining.addWidget(self.comboTraining)

        layoutOptimizer = QHBoxLayout()
        layoutOptimizer.addWidget(self.lblOptimizer)
        layoutOptimizer.addWidget(self.comboOptimizer)

        layoutEpochs = QHBoxLayout()
        layoutEpochs.addWidget(self.lblEpochs)
        layoutEpochs.addWidget(self.editEpochs)

        self.layoutEpochsPerStage = QHBoxLayout()
        self.layoutEpochsPerStage.addWidget(self.lblEpochsPerStage)
        self.layoutEpochsPerStage.addWidget(self.editEpochsStage1)
        self.layoutEpochsPerStage.addWidget(self.editEpochsStage2)
        self.layoutEpochsPerStage.addWidget(self.editEpochsStage3)

        layoutLR = QHBoxLayout()
        layoutLR.addWidget(self.lblLR)
        layoutLR.addWidget(self.editLR)

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
        self.layoutInputs.addLayout(self.layoutTraining)
        self.layoutInputs.addLayout(layoutOptimizer)
        self.layoutInputs.addLayout(layoutEpochs)
        self.layoutInputs.addLayout(self.layoutEpochsPerStage)
        self.layoutInputs.addLayout(layoutLR)
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

        self.updateTrainingParameters("Preset 1")

    @pyqtSlot(str)
    def epochsChanged(self, text):

        if text == "":
            return

        try:
            number_of_epochs = int(text)

            epochs1 = int(number_of_epochs / 3)
            epochs2 = int(number_of_epochs / 3)
            epochs3 = int(number_of_epochs / 3)

            if epochs1 + epochs2 + epochs3 < number_of_epochs:
                epochs2 += number_of_epochs - epochs1 - epochs2 - epochs3

            self.blockSignals(True)
            self.editEpochsStage1.setText(str(epochs1))
            self.editEpochsStage2.setText(str(epochs2))
            self.editEpochsStage3.setText(str(epochs3))
            self.blockSignals(False)
        except:
            pass

    @pyqtSlot(str)
    def epochsStagesChanged(self, text):

        if text == "":
            return

        try:
            number_of_epochs = int(text)

            epochs1 = int(self.editEpochsStage1.text())
            epochs2 = int(self.editEpochsStage2.text())
            epochs3 = int(self.editEpochsStage3.text())
            total_epochs = epochs1 + epochs2 + epochs3

            self.blockSignals(True)
            self.editEpochs.setText(str(total_epochs))
            self.blockSignals(False)
        except:
            pass

    @pyqtSlot(str)
    def updateTrainingParameters(self, mode):

        if mode == "Preset 1":
            self.lblLR.show()
            self.editLR.show()

            for i in range(self.layoutEpochsPerStage.count()):
                item = self.layoutEpochsPerStage.itemAt(i)
                widget = item.widget()
                if widget is not None:
                    widget.hide()

            self.lblEpochs.setText("Number of epochs:")
        else:
            for i in range(self.layoutEpochsPerStage.count()):
                item = self.layoutEpochsPerStage.itemAt(i)
                widget = item.widget()
                if widget is not None:
                    widget.show()

            self.lblLR.hide()
            self.editLR.hide()

            self.lblEpochs.setText("Total epochs:")

            self.epochsChanged(self.editEpochs.text())


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

    def getTrainingMode(self):

        return self.comboTraining.currentText()

    def getOptimizer(self):

        return self.comboOptimizer.currentText()

    def getEpochs(self):

        return int(self.editEpochs.text())

    def getEpochsPerStage(self):

        return int(self.editEpochsStage1.text()), int(self.editEpochsStage2.text()), int(self.editEpochsStage3.text())

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
                    self.lblTotalBackgroundValue.setText(str(perc) + "%")

                checkbox.stateChanged.connect(self.updateCumulativeBackground)
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

            row = int((len(self.freq_classes.keys())-1) / CLASSES_PER_ROW) + 1
            grid_layout.addWidget(self.lblTotalBackground, row, 0)
            grid_layout.addWidget(self.lblTotalBackgroundValue, row, 1)

        return groupbox

    @pyqtSlot()
    def updateCumulativeBackground(self):

        perc = 0.0
        for checkbox in self.checkboxes:
            if not checkbox.isChecked():
                perc += 100.0 * self.freq_classes[checkbox.text()]

        perc = perc + 100.0 * self.freq_classes["Background"]
        perc = round(perc, 2)
        self.lblTotalBackgroundValue.setText(str(perc) + "%")

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

        nepochs = self.getEpochs()
        if nepochs < 2:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("The minimum number of epoch is 2.")
            msgBox.exec()
            return

        e1,e2,e3 = self.getEpochsPerStage()

        if e1+e2+e3 != nepochs:
            msgBox = QMessageBox()
            msgBox.setWindowTitle(self.TAGLAB_VERSION)
            msgBox.setText("The total number of epochs should corresponds with the sum of the number of epochs of different stages.\nThere is something wrong, please check.")
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

