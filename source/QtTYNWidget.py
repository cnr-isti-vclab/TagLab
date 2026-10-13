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
    QHBoxLayout, QVBoxLayout, QMessageBox, QGroupBox, QGridLayout, QComboBox, QCheckBox, QSizePolicy, QStackedWidget, QPlainTextEdit
from models.coral_dataset import CoralsDataset
import models.training as training
import yaml


class QtTYNWidget(QWidget):


    launchTraining = pyqtSignal()


    def __init__(self, labels, taglab_version, parent=None):
        super(QtTYNWidget, self).__init__(parent)

        self.project_labels = labels
        self.TAGLAB_VERSION = taglab_version

        self.target_classes = None
        self.freq_classes = None

        self.yolo_params = None

        self.last_applied_classes = None
        self.classes_dirty = False

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

        self.lblYoloModel = QLabel("YOLO model:")
        self.lblYoloModel.setFixedWidth(TEXT_SPACE)
        self.lblYoloModel.setAlignment(Qt.AlignRight)

        self.lblYoloVersion = QLabel("YOLO version:")
        self.lblYoloVersion.setFixedWidth(TEXT_SPACE)
        self.lblYoloVersion.setAlignment(Qt.AlignRight)

        self.lblEpochsYL = QLabel("Epochs:")
        self.lblEpochsYL.setFixedWidth(TEXT_SPACE)
        self.lblEpochsYL.setAlignment(Qt.AlignRight)

        self.lblBatchYL = QLabel("Batch Size:")
        self.lblBatchYL.setFixedWidth(TEXT_SPACE)
        self.lblBatchYL.setAlignment(Qt.AlignRight)

        self.lblMaskRatio = QLabel("Mask Ratio:")
        self.lblMaskRatio.setFixedWidth(TEXT_SPACE)
        self.lblMaskRatio.setAlignment(Qt.AlignRight)

        self.lblYoloConfig = QLabel("YOLO config:")
        self.lblYoloConfig.setFixedWidth(TEXT_SPACE)
        self.lblYoloConfig.setAlignment(Qt.AlignRight)

        self.yoloLog = QPlainTextEdit()
        self.yoloLog.setReadOnly(True)
        self.yoloLog.setMinimumHeight(250)

        self.yoloLog.setStyleSheet("""
        QPlainTextEdit {
            background-color: rgb(25,25,25);
            color: rgb(220,220,220);
            border: 1px solid rgb(90,90,90);
            font-family: Consolas;
        }
        """)

        ##### Edits

        LINEWIDTH = 500
        self.editNetworkName = QLineEdit("")
        self.editNetworkName.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editNetworkName.setMinimumWidth(LINEWIDTH)
        self.editNetworkName.setPlaceholderText("Insert here the name of your network")
        self.editNetworkName.setReadOnly(False)
        self.editInputDatasetFolder = QLineEdit("")
        self.editInputDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editInputDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.editInputDatasetFolder.setPlaceholderText("Insert here the dataset folder")
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


        self.editEpochsYL = QLineEdit("50")
        self.editEpochsYL.setStyleSheet(
            "background-color: rgb(55,55,55); "
            "border: 1px solid rgb(90,90,90)"
        )

        self.editBatchSizeYL = QLineEdit("4")
        self.editBatchSizeYL.setStyleSheet(
            "background-color: rgb(55,55,55); "
            "border: 1px solid rgb(90,90,90)"
        )
        self.editMaskRatio = QLineEdit("2")
        self.editMaskRatio.setStyleSheet(
            "background-color: rgb(55,55,55); "
            "border: 1px solid rgb(90,90,90)"
        )

        self.editYoloConfig = QLineEdit()
        self.editYoloConfig.setReadOnly(True)

        self.btnChooseYoloConfig = QPushButton("...")
        self.btnChooseYoloConfig.clicked.connect(
            self.chooseYoloConfig
        )

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

        self.comboYoloModel = QComboBox()
        self.comboYoloModel.setStyleSheet(
            "background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)"
        )

        self.comboYoloModel.addItem("YOLO Nano")
        self.comboYoloModel.addItem("YOLO Small")
        self.comboYoloModel.addItem("YOLO Medium")
        self.comboYoloModel.addItem("YOLO Large")
        self.comboYoloModel.addItem("YOLO Extra Large")

        self.comboYoloVersion = QComboBox()
        self.comboYoloVersion.setStyleSheet(
            "background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)"
        )

        self.comboYoloVersion.addItem("YOLO11")
        self.comboYoloVersion.addItem("YOLO26")

        # default
        self.comboYoloVersion.setCurrentText("YOLO11")

        # default
        self.comboYoloModel.setCurrentText("YOLO Medium")

        ###### buttons

        self.btnChooseDatasetFolder = QPushButton("...")
        self.btnChooseDatasetFolder.setMaximumWidth(20)
        self.btnChooseDatasetFolder.clicked.connect(self.chooseDatasetInputFolder)


        # Checkbox

        self.chkClearYoloCache = QCheckBox("Clear YOLO cache before training")
        self.chkClearYoloCache.setChecked(False)

        self.groupbox_classes_DL = QWidget()
        self.groupbox_classes_YL = QWidget()

        # ================= DEEPLAB =================

        self.groupboxTargetClassesDL = QGroupBox("Target classes")
        self.groupbox_classes_DL = QWidget()

        layoutTargetDL = QVBoxLayout()
        self.layoutTargetDL = layoutTargetDL
        layoutTargetDL.addWidget(self.groupbox_classes_DL)

        self.groupboxTargetClassesDL.setLayout( layoutTargetDL)
        self.groupboxDeeplab = QGroupBox("DeepLab-V3+ Settings")

        layoutDLGroup = QVBoxLayout()
        layoutDLGroup.addWidget( self.groupboxTargetClassesDL)

        self.groupboxDeeplab.setLayout(layoutDLGroup)

        layoutTraining = QHBoxLayout()
        layoutTraining.addWidget(self.lblTraining)
        layoutTraining.addWidget(self.comboTraining)

        layoutOptimizer = QHBoxLayout()
        layoutOptimizer.addWidget(self.lblOptimizer)
        layoutOptimizer.addWidget(self.comboOptimizer)

        layoutEpochs = QHBoxLayout()
        layoutEpochs.addWidget(self.lblEpochs)
        layoutEpochs.addWidget(self.editEpochs)

        layoutLR = QHBoxLayout()
        layoutLR.addWidget(self.lblLR)
        layoutLR.addWidget(self.editLR)

        layoutL2 = QHBoxLayout()
        layoutL2.addWidget(self.lblL2)
        layoutL2.addWidget(self.editL2)

        layoutBS = QHBoxLayout()
        layoutBS.addWidget(self.lblBS)
        layoutBS.addWidget(self.editBatchSize)

        self.layoutEpochsPerStage = QHBoxLayout()
        self.layoutEpochsPerStage.addWidget(self.lblEpochsPerStage)
        self.layoutEpochsPerStage.addWidget(self.editEpochsStage1)
        self.layoutEpochsPerStage.addWidget(self.editEpochsStage2)
        self.layoutEpochsPerStage.addWidget(self.editEpochsStage3)


        self.pageDeepLab = QWidget()

        layoutDeepLabPage = QVBoxLayout()

        layoutDeepLabPage.addWidget( self.groupboxDeeplab)

        layoutDeepLabPage.addLayout(layoutTraining)
        layoutDeepLabPage.addLayout(layoutOptimizer)
        layoutDeepLabPage.addLayout( layoutEpochs)
        layoutDeepLabPage.addLayout( self.layoutEpochsPerStage)
        layoutDeepLabPage.addLayout( layoutLR)
        layoutDeepLabPage.addLayout(layoutL2)
        layoutDeepLabPage.addLayout(layoutBS)

        layoutDeepLabPage.addStretch()

        self.pageDeepLab.setLayout(
            layoutDeepLabPage
        )
        # ================= YOLO =================

        # GROUPBOX CLASSES
        self.groupboxYoloClasses = QGroupBox(
            "Target classes")

        self.layoutTargetYL = QVBoxLayout()
        self.layoutTargetYL.addWidget(self.groupbox_classes_YL)
        self.groupboxYoloClasses.setLayout(self.layoutTargetYL)

        # TRAINING OPTIONS

        layoutVersionYL = QHBoxLayout()
        layoutVersionYL.addWidget(self.lblYoloVersion)
        layoutVersionYL.addWidget(self.comboYoloVersion)

        layoutModelYL = QHBoxLayout()
        layoutModelYL.addWidget(self.lblYoloModel)
        layoutModelYL.addWidget(self.comboYoloModel)

        layoutEpochsYL = QHBoxLayout()
        layoutEpochsYL.addWidget(self.lblEpochsYL)
        layoutEpochsYL.addWidget(self.editEpochsYL)

        layoutBatchYL = QHBoxLayout()
        layoutBatchYL.addWidget( self.lblBatchYL)
        layoutBatchYL.addWidget(self.editBatchSizeYL)

        layoutMaskRatioYL = QHBoxLayout()
        layoutMaskRatioYL.addWidget(self.lblMaskRatio)
        layoutMaskRatioYL.addWidget(self.editMaskRatio)

        layoutYamlYL = QHBoxLayout()
        layoutYamlYL.addWidget(self.lblYoloConfig)
        layoutYamlYL.addWidget(self.editYoloConfig)
        layoutYamlYL.addWidget(self.btnChooseYoloConfig)

        self.groupboxYoloTraining = QGroupBox(
            "YOLO-V11 Training Settings"
        )

        layoutYoloTraining = QVBoxLayout()
        layoutYoloTraining.addLayout(layoutVersionYL)
        layoutYoloTraining.addLayout(layoutModelYL)
        layoutYoloTraining.addLayout(layoutEpochsYL)
        layoutYoloTraining.addLayout(layoutBatchYL)
        layoutYoloTraining.addLayout(layoutMaskRatioYL)
        layoutYoloTraining.addLayout(layoutYamlYL)
        layoutYoloTraining.addWidget(self.chkClearYoloCache)

        self.groupboxYoloTraining.setLayout(layoutYoloTraining)

        layoutYoloPage = QVBoxLayout()
        layoutYoloPage.addWidget(self.groupboxYoloClasses)
        layoutYoloPage.addWidget( self.groupboxYoloTraining)

        layoutYoloPage.addWidget(QLabel("Training Log"))
        layoutYoloPage.addWidget(self.yoloLog,stretch=1)

        self.pageYolo = QWidget()
        self.pageYolo.setLayout(layoutYoloPage)

        # ================= STACK =================

        self.modelStack = QStackedWidget()
        self.modelStack.addWidget(QWidget())  # index 0
        self.modelStack.addWidget(self.pageDeepLab)
        self.modelStack.addWidget(self.pageYolo)
        # MAIN

        self.layoutMain = QVBoxLayout()

        layoutNetwork = QHBoxLayout()
        layoutNetwork.addWidget(self.lblNetworkName)
        layoutNetwork.addWidget(self.editNetworkName)
        self.layoutMain.addLayout(layoutNetwork)

        layoutDataset = QHBoxLayout()
        layoutDataset.addWidget(self.lblDatasetFolder)
        layoutDataset.addWidget(self.editInputDatasetFolder)
        layoutDataset.addWidget(self.btnChooseDatasetFolder)
        self.layoutMain.addLayout(layoutDataset)

        self.layoutMain.addWidget(self.modelStack)

        # BOTTOM

        self.btnHelp = QPushButton("Help")
        self.btnHelp.clicked.connect(self.help)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)

        self.btnTrain = QPushButton("Train")
        self.btnTrain.clicked.connect(self.checkBeforeTraining)

        layoutBottom = QHBoxLayout()
        layoutBottom.addStretch()
        layoutBottom.addWidget(self.btnHelp)
        layoutBottom.addWidget(self.btnCancel)
        layoutBottom.addWidget(self.btnTrain)

        # ================= FINAL =================

        layoutFinal = QVBoxLayout()
        layoutFinal.addLayout(self.layoutMain)
        layoutFinal.addLayout(layoutBottom)
        self.setLayout(layoutFinal)

        # ================= STATE =================

        self.modelStack.setCurrentIndex(0)
        self.checkboxes = []
        self.updateTrainingParameters("Preset 1")


        self.setWindowTitle("Train Your Network - Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


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

    def chooseYoloConfig(self):

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select YOLO configuration",
            "",
            "Yaml (*.yaml *.yml)"
        )

        if not filename:
            return

        self.editYoloConfig.setText(filename)

        try:
            with open(filename, "r") as f:
                self.yolo_params = yaml.safe_load(f)

        except Exception as e:

            QMessageBox.warning(
                self,
                self.TAGLAB_VERSION,
                f"Cannot read yaml file:\n{e}"
            )

            self.yolo_params = None

    def getDefaultYoloPreset(self):

        return {

            "degrees": 30.0,
            "translate": 0.1,
            "scale": 0.5,
            "shear": 0.0,
            "perspective": 0.0,

            "flipud": 0.5,
            "fliplr": 0.5,

            "hsv_h": 0.015,
            "hsv_s": 0.5,
            "hsv_v": 0.4,

            "copy_paste": 0.0,
            "mosaic": 1.0,

            "box": 7.5,
            "dfl": 1.5,
            "cls": 1.0,

            "close_mosaic": 0.0,
            "dropout": 0.1,
            "warmup_epochs": 3,

            "label_smoothing": 0.1,
            "cos_lr": True,

            "patience": 15,
            "workers": 0,

            "amp": True,
            "imgsz": 1024,
            "overlap_mask": True
        }

    def getYoloTrainingParams(self):

        params = self.getDefaultYoloPreset()

        family_map = {
            "YOLO11": "yolo11",
            "YOLO26": "yolo26"
        }
        model_map = {
            "YOLO Nano": "n",
            "YOLO Small": "s",
            "YOLO Medium": "m",
            "YOLO Large": "l",
            "YOLO Extra Large": "x"
        }

        if self.yolo_params:
            params.update(self.yolo_params)

        params["model_family"] = family_map[self.comboYoloVersion.currentText()]
        params["name"] = (self.editNetworkName.text())
        params["selected_classes"] = (self.getSelectedYoloClasses())
        params["model_size"] = model_map[self.comboYoloModel.currentText()]
        params["model_name"] = (self.comboYoloModel.currentText())
        params["dataset_yaml"] = os.path.join(self.editInputDatasetFolder.text(),"dataset.yaml")
        params["config_yaml"] = (self.editYoloConfig.text().strip())

        params["epochs"] = int(self.editEpochsYL.text())
        params["batch"] = int(self.editBatchSizeYL.text())
        params["mask_ratio"] = int(self.editMaskRatio.text())
        params["config_yaml"] = (self.editYoloConfig.text().strip())
        params["clear_cache"] = ( self.chkClearYoloCache.isChecked())


        return params



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

    def chooseDatasetInputFolder(self):

        folderName = QFileDialog.getExistingDirectory(
            self,
            "Choose Your Dataset Folder",
            ""
        )

        if not folderName:
            return

        self.resetModelState()

        self.input_folder = folderName
        self.original_input_folder = folderName

        self.editInputDatasetFolder.setText(
            folderName
        )

        box = QMessageBox()
        box.setWindowTitle(self.TAGLAB_VERSION)
        box.setText(
            "Analyzing dataset...\nPlease wait."
        )
        box.setStandardButtons(
            QMessageBox.NoButton
        )

        box.show()

        QApplication.processEvents()
        QApplication.setOverrideCursor(
            Qt.WaitCursor
        )

        try:
            self.autoDetectModel()

        finally:
            QApplication.restoreOverrideCursor()
            box.close()

    def appendYoloLog(self, text):

        self.yoloLog.appendPlainText(str(text))

        sb = self.yoloLog.verticalScrollBar()
        sb.setValue(sb.maximum())

        QApplication.processEvents()

    def autoDetectModel(self):


        if self.isValidYoloDataset(self.editInputDatasetFolder.text()):
            self.modelStack.setCurrentIndex(2)
            self.runYoloAnalysis()
            return

        if self.isValidDeepLabDataset(self.editInputDatasetFolder.text()):
            self.modelStack.setCurrentIndex(1)
            self.runDeepLabAnalysis()
            return

        QMessageBox.warning(
            self,
            self.TAGLAB_VERSION,
            "The selected folder is not a valid YOLO or DeepLab dataset."
        )

        self.modelStack.setCurrentIndex(0)

    def resetModelState(self):

        self.modelStack.setCurrentIndex(0)

        if self.groupbox_classes_YL is not None:
            old = self.groupbox_classes_YL

            self.groupbox_classes_YL = QWidget()
            self.layoutTargetYL.replaceWidget(old, self.groupbox_classes_YL)

            old.deleteLater()

        if self.groupbox_classes_DL is not None:
            old = self.groupbox_classes_DL
            self.groupbox_classes_DL = QWidget()

            self.layoutTargetDL.replaceWidget(old,self.groupbox_classes_DL)
            old.deleteLater()

        self.checkboxes = []
        self.checkboxes_YL = []

        self.freq_classes = None
        self.target_classes = None

    @pyqtSlot()
    def help(self):

        url = QUrl("http://taglab.isti.cnr.it/docs")
        QDesktopServices.openUrl(url)

    def getDatasetFolder(self):

        return self.editInputDatasetFolder.text()

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

        content = QWidget()
        content.setSizePolicy(
            QSizePolicy.MinimumExpanding,
            QSizePolicy.MinimumExpanding
        )

        content.lblTotalBackgroundValue = None

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        if not self.freq_classes:
            lbl = QLabel("No classes found in the dataset.")
            layout.addWidget(lbl)

            return content

        grid_layout = QGridLayout()
        layout.addLayout(grid_layout)

        self.checkboxes = []

        CLASSES_PER_ROW = 3

        for i, key in enumerate(self.freq_classes.keys()):

            perc = round(
                self.freq_classes[key] * 100.0,
                2
            )

            checkbox = QCheckBox(key)
            checkbox.setChecked(True)

            lbl_perc = QLabel(f"{perc}%")

            if perc < 5:
                lbl_perc.setStyleSheet("color:red;")
            else:
                lbl_perc.setStyleSheet("color:lightgreen;")

            if key == "Background":
                checkbox.setAttribute(
                    Qt.WA_TransparentForMouseEvents
                )

                checkbox.setFocusPolicy(
                    Qt.NoFocus
                )

                bg_label = QLabel(f"{perc}%")

                content.lblTotalBackgroundValue = bg_label

            checkbox.stateChanged.connect(
                self.updateCumulativeBackground
            )

            self.checkboxes.append(checkbox)

            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setFlat(True)

            label = self.project_labels.get(key)

            color = label.fill if label else (0, 0, 0)

            btn.setStyleSheet(
                f"background-color: rgb({color[0]},"
                f"{color[1]},"
                f"{color[2]});"
                f"border:none;"
            )

            hl = QHBoxLayout()
            hl.addWidget(btn)
            hl.addWidget(lbl_perc)

            row = i // CLASSES_PER_ROW
            col = (i % CLASSES_PER_ROW) * 2

            grid_layout.addWidget(
                checkbox,
                row,
                col
            )

            grid_layout.addLayout(
                hl,
                row,
                col + 1
            )

        last_row = (
                           (len(self.freq_classes) - 1)
                           // CLASSES_PER_ROW
                   ) + 1

        if content.lblTotalBackgroundValue:
            grid_layout.addWidget(
                QLabel("Cumulative background:"),
                last_row,
                0
            )

            grid_layout.addWidget(
                content.lblTotalBackgroundValue,
                last_row,
                1
            )

        return content

    def closeEvent(self, event):

        print("QtTYNWidget CLOSE EVENT")

        self.editNetworkName.clear()
        self.editInputDatasetFolder.clear()

        self.editYoloConfig.clear()

        self.yolo_params = None

        self.checkboxes_YL = []

        self.target_classes = None
        self.freq_classes = None

        self.modelStack.setCurrentIndex(0)

        super().closeEvent(event)



    def isValidDeepLabDataset(self, folder):

        if not folder or not os.path.exists(folder):
            return False

        training_dir = os.path.join(folder, "training")
        images_dir = os.path.join(training_dir, "images")
        labels_dir = os.path.join(training_dir, "labels")

        return (
                os.path.isdir(training_dir)
                and os.path.isdir(images_dir)
                and os.path.isdir(labels_dir)
        )

    def isValidYoloDataset(self, folder):

        if not folder or not os.path.exists(folder):
            return False

        yaml_path = os.path.join(folder, "dataset.yaml")

        if not os.path.isfile(yaml_path):
            return False

        if not os.path.isdir(os.path.join(folder, "images")):
            return False

        if not os.path.isdir(os.path.join(folder, "labels")):
            return False

        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)

            return (
                    "names" in data
                    and isinstance(data["names"], dict)
            )

        except Exception:
            return False

    @pyqtSlot()
    def updateCumulativeBackground(self):

        if self.groupbox_classes_DL is None:
            return

        widget = self.groupbox_classes_DL

        if not hasattr(widget,
                       "lblTotalBackgroundValue"):
            return

        if widget.lblTotalBackgroundValue is None:
            return

        perc = 0.0

        for checkbox in self.checkboxes:

            if not checkbox.isChecked():
                perc += (
                        100.0 *
                        self.freq_classes[
                            checkbox.text()
                        ]
                )

        perc += (
                100.0 *
                self.freq_classes["Background"]
        )

        widget.lblTotalBackgroundValue.setText(
            f"{round(perc, 2)}%"
        )


    def runDeepLabAnalysis(self):

        self.analyzeDataset()

        old_widget = self.groupbox_classes_DL

        self.groupbox_classes_DL = (
            self.createClassesToRecognizeWidgets()
        )

        self.layoutTargetDL.replaceWidget(
            old_widget,
            self.groupbox_classes_DL
        )

        old_widget.deleteLater()

    def runYoloAnalysis(self):

        count_classes = self.countYoloInstances(
            self.editInputDatasetFolder.text()
        )

        old_widget = self.groupbox_classes_YL

        self.groupbox_classes_YL = (
            self.createClassesToRecognizeWidgetsYolo(
                count_classes
            )
        )

        self.layoutTargetYL.replaceWidget(
            old_widget,
            self.groupbox_classes_YL
        )

        old_widget.deleteLater()
    def countYoloInstances(self, folder):

        yaml_path = os.path.join(folder, "dataset.yaml")

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        names = data.get("names", {})

        counts = {v: 0 for v in names.values()}

        label_dirs = [
            os.path.join(folder, "labels", "train"),
            os.path.join(folder, "labels", "val")
        ]

        for d in label_dirs:
            if not os.path.exists(d):
                continue

            for fname in os.listdir(d):
                if not fname.endswith(".txt"):
                    continue

                with open(os.path.join(d, fname)) as f:
                    for line in f:
                        if line.strip():
                            cls_id = int(line.split()[0])
                            cls_name = names[cls_id]
                            counts[cls_name] += 1

        return counts

    def createClassesToRecognizeWidgetsYolo(self, count_classes):

        widget = QWidget()
        grid = QGridLayout(widget)

        CLASSES_PER_ROW = 3
        self.checkboxes_YL = []


        for i, (name, count) in enumerate(count_classes.items()):

            checkbox = QCheckBox(name)
            checkbox.setChecked(True)
            self.checkboxes_YL.append(checkbox)

            lbl_count = QLabel(str(count))

            if count == 0:
                lbl_count.setStyleSheet("color: gray;")
            elif count < 300:
                lbl_count.setStyleSheet("color: red;")
            else:
                lbl_count.setStyleSheet("color: green;")

            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setFlat(True)

            label = self.project_labels.get(name)
            color = label.fill if label else (0, 0, 0)

            btn.setStyleSheet(
                f"background-color: rgb({color[0]},{color[1]},{color[2]}); border:none;"
            )

            hl = QHBoxLayout()
            hl.addWidget(btn)
            hl.addWidget(lbl_count)

            row = i // CLASSES_PER_ROW
            col = (i % CLASSES_PER_ROW) * 2

            grid.addWidget(checkbox, row, col)
            grid.addLayout(hl, row, col + 1)

        return widget

    def getSelectedYoloClasses(self):

        if not hasattr(self, "checkboxes_YL"):
            return None

        selected = {
            cb.text()
            for cb in self.checkboxes_YL
            if cb.isChecked()
        }

        return selected



    @pyqtSlot()
    def checkBeforeTraining(self):

        dataset_Folder = self.editInputDatasetFolder.text()

        if not os.path.exists(self.editInputDatasetFolder.text()):
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

        # DeepLab

        if self.modelStack.currentIndex() == 1:
            try:
                epochs = self.getEpochs()
                if epochs < 2:
                    QMessageBox.warning(self, self.TAGLAB_VERSION, "The minimum number of epochs is 2.")
                    return

                self.launchTraining.emit()

            except Exception as e:
                QMessageBox.warning(self, self.TAGLAB_VERSION,
                                    f"Invalid DeepLab settings:\n{e}"
                                    )

            return

        # YOLO
        if self.modelStack.currentIndex() == 2:
            try:
                epochs = int(self.editEpochsYL.text())
                if epochs < 2:
                    QMessageBox.warning(self,self.TAGLAB_VERSION,"The minimum number of epochs is 2.")
                    return

                self.yolo_training_params = (self.getYoloTrainingParams())
                if hasattr(self, "yoloLog"):
                    self.yoloLog.clear()
                self.launchTraining.emit()

            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.TAGLAB_VERSION,
                    f"Invalid YOLO settings:\n{e}"
                )
            return


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

