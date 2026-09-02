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


from PyQt5.Qt import QDesktopServices
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QUrl
from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QLineEdit, QLabel, QPushButton, QProgressDialog,\
    QHBoxLayout, QVBoxLayout, QMessageBox, QGroupBox, QGridLayout, QSizePolicy, QRadioButton, QCheckBox, QLayout, QTextEdit, QStackedWidget
import os
import glob
import time
import io
import contextlib
import traceback
from PIL import Image
import numpy as np
import shutil
import random
import yaml
import models.training as training
from models.coral_dataset import CoralsDataset
from source.QtProgressBarCustom import QtProgressBarCustom
import tempfile
from collections import Counter, defaultdict

from PyQt5.QtWidgets import QDialog

class QtDatasetManagerWidget(QDialog):

    def __init__(self, labels, taglab_version, parent=None):
        super(QtDatasetManagerWidget, self).__init__(parent)

        self.project_labels = labels
        self.TAGLAB_VERSION = taglab_version

        self.target_classes = None
        self.freq_classes = None
        self.pipeline_dataset = None

        self.classes_dirty = False
        self.last_applied_classes = None

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        TEXT_SPACE = 240

        ###### Labels

        lblDatasetInputFolder = QLabel("Dataset input folder: ")
        lblDatasetInputFolder.setMinimumWidth(TEXT_SPACE)
        lblDatasetInputFolder.setAlignment(Qt.AlignRight)

        lblTargetClasses = QLabel("Target classes: ")
        lblTargetClasses.setMinimumWidth(TEXT_SPACE)
        lblTargetClasses.setAlignment(Qt.AlignRight)

        lblFiltering = QLabel("Filtering options: ")
        lblFiltering.setMinimumWidth(TEXT_SPACE)
        lblFiltering.setAlignment(Qt.AlignLeft)

        lblAmount = QLabel("Amount (%): ")
        lblAmount2 = QLabel("Amount (%): ")


        #### Checkboxes

        self.checkRemoveNoData = QRadioButton("Remove 'no data' tiles")
        self.checkRemoveNoData.setStyleSheet("QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }")
        self.checkRemoveNoData.setToolTip("The <em>no data</em> tiles are tiles with flat colors (poor RGB information).")
        self.checkRemoveNoLabels = QRadioButton("Remove tiles without target classes")
        self.checkRemoveNoLabels.setStyleSheet("QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }")
        self.checkRemoveNoLabels.setToolTip("The <em>target classes</em>: are the class recognized by the classifier, i.e. the selected ones plus the Background class.")
        self.radio_ThresholdBackground  = QRadioButton("Remove tiles where the background classes exceeds:")
        self.radio_ThresholdBackground.setStyleSheet("QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }")
        self.radio_ThresholdBackground.setToolTip("The <em>background classes</em> are the non-selected classes plus the 'Background' class.")
        self.radio_SubsampleBackground = QRadioButton("Randomly subsamples the background classes by:")
        self.radio_SubsampleBackground.setStyleSheet("QToolTip { background-color: rgb(80,80,80); color: white; border: 1px solid rgb(100,100,100); }")
        self.radio_SubsampleBackground.setToolTip("The <em>background classes</em> are the non-selected classes plus the 'Background' class.")


        ##### Edits

        LINEWIDTH = 300
        self.editInputDatasetFolder = QLineEdit("")
        self.editInputDatasetFolder.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editInputDatasetFolder.setMinimumWidth(LINEWIDTH)
        self.editInputDatasetFolder.setReadOnly(True)
        self.editInputDatasetFolder.setPlaceholderText("Select the path of the input dataset")
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

        self.btnExportDataset_DL = QPushButton("Export dataset")
        self.btnExportDataset_DL.clicked.connect(self.filter)

        ####FILTERING OPTIONS (DeepLab)

        self.checkRemoveNoData = QRadioButton("Remove 'no data' tiles")
        self.checkRemoveNoLabels = QRadioButton("Remove tiles without target classes")
        self.radio_ThresholdBackground = QRadioButton("Remove tiles where the background exceeds:")
        self.radio_SubsampleBackground = QRadioButton("Randomly subsample the background by:")

        layoutAmount1 = QHBoxLayout()
        layoutAmount1.addWidget(lblAmount)
        layoutAmount1.addWidget(self.editAmount1)
        layoutAmount1.addStretch()

        layoutAmount2 = QHBoxLayout()
        layoutAmount2.addWidget(lblAmount2)
        layoutAmount2.addWidget(self.editAmount2)
        layoutAmount2.addStretch()

        layoutOptions = QVBoxLayout()
        layoutOptions.addWidget(self.checkRemoveNoData)
        layoutOptions.addWidget(self.checkRemoveNoLabels)
        layoutOptions.addWidget(self.radio_ThresholdBackground)
        layoutOptions.addLayout(layoutAmount1)
        layoutOptions.addWidget(self.radio_SubsampleBackground)
        layoutOptions.addLayout(layoutAmount2)

        self.groupboxFiltering_DL = QGroupBox("Filtering Options")
        self.groupboxFiltering_DL.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Maximum
        )

        layoutButtonsDL = QHBoxLayout()
        layoutButtonsDL.addStretch()
        layoutButtonsDL.addWidget(self.btnExportDataset_DL)

        layoutOptions.setAlignment(Qt.AlignLeft)
        layoutOptions.addLayout(layoutButtonsDL)
        self.groupboxFiltering_DL.setLayout(layoutOptions)

        # GROUPBOX DEEPLAB

        self.groupbox_target_DL, _ = self.createTargetClassesGroupBox()
        self.groupbox_classes_DL = None

        self.groupboxDeeplab = QGroupBox("Segmentation Masks for DeepLab-V3+")
        layoutDeeplab = QVBoxLayout()
        layoutDeeplab.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        layoutDeeplab.addWidget(self.groupbox_target_DL)
        layoutDeeplab.addWidget(self.groupboxFiltering_DL)

        self.groupboxDeeplab.setLayout(layoutDeeplab)

        # GROUPBOX YOLO

        self.groupbox_target_YOLO, _ = self.createTargetClassesGroupBox()
        self.groupbox_classes_YL = None
        self.groupboxYolo = QGroupBox("Yolo-V5 annotations for Yolo-V11")

        for i in reversed(range(self.groupbox_target_YOLO.layout().count())):
            item = self.groupbox_target_YOLO.layout().itemAt(i)
            if item.widget():
                item.widget().deleteLater()

        layoutYolo = QVBoxLayout()
        layoutYolo.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # PIPELINE CHECKBOX

        self.chkOversample = QCheckBox("Oversample imbalanced classes")
        self.chkBackground = QCheckBox("Oversample background")

        self.chkOversample.stateChanged.connect(self.onPipelineChanged)
        self.chkBackground.stateChanged.connect(self.onPipelineChanged)

        # RE-MAP BUTTON

        self.btnRemap = QPushButton("Re-map classes")
        self.btnRemap.setEnabled(False)
        self.updateRemapButtonStyle()
        self.btnRemap.clicked.connect(self.onRemapClicked)

        # EXPORT BUTTON
        self.btnExportDataset = QPushButton("Export dataset")
        self.btnExportDataset.clicked.connect(self.exportDataset)

        self.logWindow = QTextEdit()
        self.logWindow.setReadOnly(True)
        self.logWindow.setMinimumHeight(120)
        self.logWindow.setPlaceholderText("Yolo tuning suggestions will appear here.")

        self.btnExportParams = QPushButton("Export training parameters")
        self.btnExportParams.clicked.connect(self.onExportYoloParams)
        self.btnExportParams.setEnabled(False)

        layoutExport = QHBoxLayout()
        layoutExport.addStretch()
        layoutExport.addWidget(self.btnExportParams)

        layoutRemap = QHBoxLayout()
        layoutRemap.addStretch()
        layoutRemap.addWidget(self.btnRemap)

        layoutYolo = QVBoxLayout()
        layoutYolo.addWidget(self.groupbox_target_YOLO)
        layoutYolo.addLayout(layoutRemap)

        layoutPipeline = QVBoxLayout()
        layoutPipeline.addWidget(self.chkOversample)
        layoutPipeline.addWidget(self.chkBackground)
        layoutPipeline.addWidget(self.btnExportDataset)

        layoutYolo.addLayout(layoutPipeline)
        layoutYolo.addWidget(self.logWindow)
        layoutYolo.addLayout(layoutExport)

        self.groupboxYolo.setLayout(layoutYolo)

        self._modelSpacer = QWidget()
        self._modelSpacer.setFixedHeight(0)
        self._modelSpacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.modelPlaceholder = QWidget()
        self.modelLayout = QVBoxLayout()
        self.modelLayout.addWidget(self._modelSpacer)
        self.modelLayout.setContentsMargins(0, 0, 0, 0)
        self.modelPlaceholder.setLayout(self.modelLayout)

        ###### Stack

        self.modelStack = QStackedWidget()
        self.modelStack.addWidget(QWidget())  # index 0 -> empty
        self.modelStack.addWidget(self.groupboxDeeplab)  # index 1
        self.modelStack.addWidget(self.groupboxYolo)  # index 2

        self.modelStack.setCurrentIndex(0)

        self.yolo_recommended_params = None

        ###### Layouts

        layoutIO = QGridLayout()

        layoutIO.addWidget(lblDatasetInputFolder, 0, 0)
        layoutIO.addWidget(self.editInputDatasetFolder, 0, 1)
        layoutIO.addWidget(self.btnChooseDatasetInputFolder, 0, 2)

        self.layoutMain = QVBoxLayout()
        self.layoutMain.addLayout(layoutIO)

        self.btnHelp = QPushButton("Help")
        self.btnHelp.clicked.connect(self.help)
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)

        layoutBottomButtons = QHBoxLayout()
        layoutBottomButtons.setAlignment(Qt.AlignRight)
        layoutBottomButtons.addStretch()
        layoutBottomButtons.addWidget(self.btnHelp)
        layoutBottomButtons.addWidget(self.btnCancel)

        # FINAL LAYOUT

        layoutFinal = QVBoxLayout()
        layoutFinal.setSizeConstraint(QLayout.SetMinimumSize)
        layoutFinal.addLayout(self.layoutMain)
        layoutFinal.addWidget(self.modelStack)
        layoutFinal.addLayout(layoutBottomButtons)


        self.setLayout(layoutFinal)

        self.setWindowTitle("Dataset Manager - Tiles Filtering Options")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.progress_bar = QtProgressBarCustom(parent=self)
        self.progress_bar.setWindowFlags(Qt.ToolTip | Qt.CustomizeWindowHint)
        self.progress_bar.setWindowModality(Qt.NonModal)
        self.progress_bar.hide()

        self.checkboxes = []

    def buildPipeline(self):

        steps = []

        if self.chkOversample.isChecked():
            steps.append("oversample")

        if self.chkBackground.isChecked():
            steps.append("background")

        return steps

    def createWorkingDataset(self):

        temp_dir = tempfile.mkdtemp(prefix="taglab_pipeline_")

        # copy yaml
        shutil.copy(
            os.path.join(self.original_input_folder, "dataset.yaml"),
            os.path.join(temp_dir, "dataset.yaml")
        )

        # copy labels
        for split in ["train", "val"]:

            src = os.path.join(self.original_input_folder, "labels", split)
            dst = os.path.join(temp_dir, "labels", split)

            if os.path.exists(src):
                os.makedirs(dst, exist_ok=True)

                for fname in os.listdir(src):
                    if fname.endswith(".txt"):
                        shutil.copy2(
                            os.path.join(src, fname),
                            os.path.join(dst, fname)
                        )

        return temp_dir

    def updateModelAvailability(self):
        if getattr(self, "input_folder", None):
            self.autoDetectModel()
        else:
            self.resetModelState()

    def onPipelineChanged(self):

        sender = self.sender()

        # first remap
        if self.classes_dirty:

            self.logWindow.append("⚠️ Please apply 'Re-map' before continuing.\n")

            if sender:
                sender.blockSignals(True)
                sender.setChecked(False)
                sender.blockSignals(False)

            return

        # then run pipeline
        self.runPipelinePreview()

    def runPipelinePreview(self):

        if not self.original_input_folder:
            return

        steps = self.buildPipeline()

        self.logWindow.clear()
        self.logWindow.append("\n──────── NEW PIPELINE RUN ────────\n")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            # USE THE ORIGINAL FOLDER

            working_dir = self.createWorkingDataset()
            current_dir = working_dir

            selected_classes = self.getSelectedYoloClasses()

            if selected_classes:
                self.applyRemap(current_dir)

            for i, step in enumerate(steps):

                self.logWindow.append(f"\n▶ STEP {i + 1}: {step}\n")

                if step == "oversample":
                    self.oversample_imbalanced_classes(current_dir)

                elif step == "background":
                    self.oversample_background(current_dir)

            self.pipeline_dataset = current_dir
            self.input_folder = current_dir

            self.updateYoloUIFromFolder(current_dir)
            self.onGetYoloTrainingSuggestionsFromFolder(current_dir)

            self.logWindow.append("\n✅ Pipeline completed.\n")

        finally:
            QApplication.restoreOverrideCursor()
    def getDatasetStatsFast(self, folder):


        temp_input = self.input_folder
        self.input_folder = folder

        count_classes = self.analyzeYoloDataset()

        self.input_folder = temp_input

        annotations = sum(count_classes.values())

        images = 0
        for split in ["train", "val"]:
            lbl_dir = os.path.join(folder, "labels", split)
            if os.path.exists(lbl_dir):
                images += len([
                    f for f in os.listdir(lbl_dir)
                    if f.endswith(".txt")
                ])

        return images, annotations

    def updateYoloUIFromFolder(self, folder):

        # current state
        prev_state = {}
        for cb in getattr(self, "checkboxes_YL", []):
            prev_state[cb.text()] = cb.isChecked()

        # analyze dataset
        temp_input = self.input_folder
        self.input_folder = folder

        count_classes = self.analyzeYoloDataset()

        self.input_folder = temp_input

        # inizialize
        if not hasattr(self, "yolo_class_list") or self.yolo_class_list is None:
            self.yolo_class_list = [
                name for name, count in count_classes.items() if count > 0
            ]

        stable_counts = {
            cls: count_classes.get(cls, 0)
            for cls in self.yolo_class_list
        }

        if self.groupbox_classes_YL is not None:
            self.groupbox_target_YOLO.layout().removeWidget(self.groupbox_classes_YL)
            self.groupbox_classes_YL.deleteLater()
            self.groupbox_classes_YL = None

        self.groupbox_classes_YL = self.createClassesToRecognizeWidgetYolo(
            stable_counts,
            folder
        )

        self.groupbox_target_YOLO.layout().addWidget(self.groupbox_classes_YL)
        first_run = len(prev_state) == 0

        for cb in self.checkboxes_YL:
            cb.blockSignals(True)

            if first_run:
                cb.setChecked(True)

            elif cb.text() in prev_state:
                cb.setChecked(prev_state[cb.text()])

            else:
                cb.setChecked(True)

            cb.blockSignals(False)

        self.updateCheckboxStyle()

    def applyRemap(self, folder):

        import os, yaml

        selected_classes = self.getSelectedYoloClasses()

        if not selected_classes:
            self.logWindow.append("⚠️ No classes selected for remapping.\n")
            return

        #LOAD ORIGINAL YAML
        yaml_path_original = os.path.join(self.original_input_folder, "dataset.yaml")

        if not os.path.exists(yaml_path_original):
            self.logWindow.append("❌ Original dataset.yaml not found.\n")
            return

        with open(yaml_path_original, "r") as f:
            original_data = yaml.safe_load(f)

        original_names = original_data.get("names", {})
        name_to_old_id = {v: k for k, v in original_names.items()}

        # SKIP REMAP if all classes are checked
        if set(selected_classes) == set(original_names.values()):
            self.logWindow.append("ℹ️ Remap skipped (all classes selected)\n")
            return

        self.logWindow.append("🔁 Applying remap...\n")

        # mapping
        mapping = {}
        new_names = {}
        new_id = 0

        for cls_name in selected_classes:
            if cls_name not in name_to_old_id:
                continue

            old_id = name_to_old_id[cls_name]
            mapping[old_id] = new_id
            new_names[new_id] = cls_name
            new_id += 1

        removed_classes = set(original_names.keys()) - set(mapping.keys())

        # remapping
        for split in ["train", "val"]:

            label_dir = os.path.join(folder, "labels", split)

            if not os.path.exists(label_dir):
                continue

            for fname in os.listdir(label_dir):

                if not fname.endswith(".txt"):
                    continue

                path = os.path.join(label_dir, fname)

                new_lines = []

                with open(path, "r") as f:
                    for line in f:

                        parts = line.strip().split()
                        if not parts:
                            continue

                        old_cls = int(parts[0])

                        # skip classes
                        if old_cls not in mapping:
                            continue

                        parts[0] = str(mapping[old_cls])
                        new_lines.append(" ".join(parts))

                with open(path, "w") as f:
                    f.write("\n".join(new_lines))

        # WRITE new YAML

        new_yaml = {
            "path": self.original_input_folder,
            "train": "images/train",
            "val": "images/val",
            "names": new_names
        }

        yaml_out = os.path.join(folder, "dataset.yaml")

        with open(yaml_out, "w") as f:
            yaml.safe_dump(new_yaml, f, sort_keys=False)

        # LOG
        removed_names = [
            original_names[k] for k in removed_classes
            if k in original_names
        ]

        if removed_names:
            self.logWindow.append(f"🗑️ Removed classes: {removed_names}\n")

        self.logWindow.append("✅ Remap applied.\n")


    def exportDataset(self):

        if not self.pipeline_dataset:
            QMessageBox.warning(
                self,
                self.TAGLAB_VERSION,
                "No dataset to export."
            )
            return

        dst = QFileDialog.getExistingDirectory(
            self,
            "Select output folder",
            ""
        )

        if not dst:
            return

        dst_dataset = dst

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:

            for split in ["train", "val"]:
                os.makedirs(os.path.join(dst_dataset, "images", split), exist_ok=True)
                os.makedirs(os.path.join(dst_dataset, "labels", split), exist_ok=True)

            # copy labels
            for split in ["train", "val"]:
                src_lbl = os.path.join(self.pipeline_dataset, "labels", split)
                dst_lbl = os.path.join(dst_dataset, "labels", split)

                if not os.path.exists(src_lbl):
                    continue

                for fname in os.listdir(src_lbl):
                    if fname.endswith(".txt"):
                        shutil.copy2(
                            os.path.join(src_lbl, fname),
                            os.path.join(dst_lbl, fname)
                        )

            for split in ["train", "val"]:
                src_img = os.path.join(self.original_input_folder, "images", split)
                dst_img = os.path.join(dst_dataset, "images", split)

                if not os.path.exists(src_img):
                    continue

                label_files = os.listdir(os.path.join(dst_dataset, "labels", split))

                needed_images = set(f.replace(".txt", "") for f in label_files)

                for fname in os.listdir(src_img):
                    name, ext = os.path.splitext(fname)

                    if name in needed_images:
                        shutil.copy2(
                            os.path.join(src_img, fname),
                            os.path.join(dst_img, fname)
                        )

            # copy yaml updating path
            yaml_src = os.path.join(self.pipeline_dataset, "dataset.yaml")
            yaml_dst = os.path.join(dst_dataset, "dataset.yaml")

            with open(yaml_src, "r") as f:
                data = yaml.safe_load(f)

            data["path"] = dst_dataset

            with open(yaml_dst, "w") as f:
                yaml.safe_dump(data, f, sort_keys=False)

        except Exception as e:
            QMessageBox.critical(
                self,
                self.TAGLAB_VERSION,
                f"Export failed:\n{str(e)}"
            )
            return

        finally:
            QApplication.restoreOverrideCursor()

        QMessageBox.information(
            self,
            self.TAGLAB_VERSION,
            "Dataset exported successfully."
        )

    def createTargetClassesGroupBox(self):
        box = QGroupBox("Target classes")
        box.setAlignment(Qt.AlignLeft)

        layout = QVBoxLayout(box)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        return box, None

    def isValidDeepLabDataset(self, folder):
        if not folder or not os.path.exists(folder):
            return False

        training_dir = os.path.join(folder, "training")
        images_dir = os.path.join(training_dir, "images")
        labels_dir = os.path.join(training_dir, "labels")

        required_paths = [training_dir, images_dir, labels_dir]

        for path in required_paths:
            if not os.path.exists(path):
                return False

        return True

    def isValidYoloDataset(self, folder, require_split=True):

        if not folder or not os.path.exists(folder):
            return False

        yaml_path = os.path.join(folder, "dataset.yaml")
        images_dir = os.path.join(folder, "images")
        labels_dir = os.path.join(folder, "labels")

        if not os.path.exists(yaml_path):
            return False

        if not os.path.isdir(images_dir) or not os.path.isdir(labels_dir):
            return False

        if require_split:
            if not os.path.exists(os.path.join(images_dir, "train")):
                return False
            if not os.path.exists(os.path.join(labels_dir, "train")):
                return False

        try:
            with open(yaml_path, "r") as f:
                data = yaml.safe_load(f)
            if "names" not in data or not isinstance(data["names"], dict):
                return False
        except Exception:
            return False

        return True

    def getSafeWorkingFolder(self):

        if self.input_folder != self.output_folder:
            return self.output_folder, False

        temp_folder = tempfile.mkdtemp(prefix="taglab_tmp_")

        return temp_folder, True

    def chooseDatasetInputFolder(self):
        folderName = QFileDialog.getExistingDirectory(self, "Choose Your Dataset Folder", "")

        if folderName:
            self.resetModelState()
            self.input_folder = folderName
            self.original_input_folder = folderName
            self.editInputDatasetFolder.setText(folderName)

            self.autoDetectModel()

    def closeEvent(self, event):
        self.resetModelState()
        super().closeEvent(event)

    @pyqtSlot()
    def chooseDatasetOutputFolder(self):

        folderName = QFileDialog.getExistingDirectory(self, "Choose Your Dataset Folder", "")

        if folderName:
            self.output_folder = folderName
            self.editOutputDatasetFolder.setText(folderName)
            self.updateModelAvailability()

    def runDeeplabAnalysis(self):

        if not self.isValidDeepLabDataset(self.input_folder):
            QMessageBox.critical(
                self,
                self.TAGLAB_VERSION,
                "The input folder does not seem to contain a valid dataset.\n"
                "Please select a valid dataset."
            )

            self.resetModelState()
            self.modelStack.setCurrentIndex(0)

            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            self.analyzeDeepLabDataset()
        finally:
            QApplication.restoreOverrideCursor()

        if self.groupbox_classes_DL is not None:
            self.groupbox_target_DL.layout().removeWidget(self.groupbox_classes_DL)
            self.groupbox_classes_DL.deleteLater()
            self.groupbox_classes_DL = None

        self.groupbox_classes_DL = self.createClassesToRecognizeWidgets()
        self.groupbox_target_DL.layout().addWidget(self.groupbox_classes_DL)

    def runYoloAnalysis(self):

        if not self.isValidYoloDataset(self.input_folder, require_split=True):
            QMessageBox.critical(
                self,
                self.TAGLAB_VERSION,
                "The input folder does not seem to contain a valid dataset.\nPlease select a valid dataset."
            )

            self.resetModelState()
            self.modelStack.setCurrentIndex(0)
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            count_classes = self.analyzeYoloDataset()
        finally:
            QApplication.restoreOverrideCursor()

        self.yolo_class_list = [
            name for name, count in count_classes.items() if count > 0
        ]

        stable_counts = {
            cls: count_classes.get(cls, 0)
            for cls in self.yolo_class_list
        }

        if self.groupbox_classes_YL is not None:
            self.groupbox_target_YOLO.layout().removeWidget(self.groupbox_classes_YL)
            self.groupbox_classes_YL.deleteLater()
            self.groupbox_classes_YL = None

        self.groupbox_classes_YL = self.createClassesToRecognizeWidgetYolo(
            stable_counts,
            self.input_folder
        )

        self.groupbox_target_YOLO.layout().addWidget(self.groupbox_classes_YL)
        for cb in self.checkboxes_YL:
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)


        self.updateCheckboxStyle()
        self.onGetYoloTrainingSuggestionsFromFolder(self.input_folder)
        self.last_applied_classes = self.getSelectedYoloClasses()
        self.classes_dirty = False
        self.btnRemap.setEnabled(False)
        self.updateRemapButtonStyle()

    def prepareOutputFolder(self):

        if not self.output_folder:
            QMessageBox.warning(
                self,
                self.TAGLAB_VERSION,
                "Please select an output folder."
            )
            return None

        if not self.isValidYoloDataset(self.output_folder, require_split=False):
            return self.output_folder

        msg = QMessageBox(self)
        msg.setWindowTitle(self.TAGLAB_VERSION)
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "The selected output folder already contains a YOLO dataset.\n"
            "How do you want to proceed?"
        )
        btn_overwrite = msg.addButton("Overwrite", QMessageBox.DestructiveRole)
        btn_new = msg.addButton("Create New Folder", QMessageBox.AcceptRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_cancel)

        msg.exec()

        if msg.clickedButton() == btn_cancel:
            return None

        if msg.clickedButton() == btn_overwrite:
            try:
                shutil.rmtree(self.output_folder)
                os.makedirs(self.output_folder)
            except Exception as e:
                QMessageBox.critical(self, self.TAGLAB_VERSION, str(e))
                return None
            return self.output_folder

        if msg.clickedButton() == btn_new:
            new_folder = QFileDialog.getExistingDirectory(
                self,
                "Select new output folder"
            )
            return new_folder if new_folder else None

    def onRemapYoloDataset(self):

        self.clearLog()

        msg = QMessageBox(self)
        msg.setWindowTitle(self.TAGLAB_VERSION)
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "Clicking 'Continue' will create a new Yolo dataset in the output folder.\n"
            "Do you wish to proceed?"
        )

        btn_continue = msg.addButton("Continue", QMessageBox.AcceptRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_cancel)

        msg.exec()

        if msg.clickedButton() is not btn_continue:
            return

        self.btnRemapDataset.setEnabled(False)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            selected_classes = self.getSelectedYoloClasses()
            if not selected_classes:
                QMessageBox.warning(
                    self,
                    self.TAGLAB_VERSION,
                    "No classes selected for remapping."
                )
                return

            mapping, removed, new_names = self.buildYoloClassMapping(selected_classes)

            base_folder = self.prepareOutputFolder()
            if base_folder is None:
                return

            self.output_folder = base_folder

            target_folder, is_temp = self.getSafeWorkingFolder()

            shutil.copytree(self.original_input_folder, target_folder, dirs_exist_ok=True)


            self.output_folder = target_folder

            # PROCESSING
            self.remapYoloLabels(mapping, removed)
            self.writeNewYoloYaml(new_names)

            # finalize
            if is_temp:
                if os.path.exists(target_folder):
                    shutil.rmtree(base_folder)
                    shutil.move(target_folder, base_folder)
                    self.output_folder = base_folder
                else:
                    print(" Temporary folder missing, operation aborted.")
                    return

            self.input_folder = self.output_folder
            self.editInputDatasetFolder.setText(self.output_folder)

            self.runYoloAnalysis()

            QMessageBox.information(
                self,
                self.TAGLAB_VERSION,
                "Yolo dataset successfully re-mapped.\n"
                "The new dataset is now set as input."
            )

        finally:
            QApplication.restoreOverrideCursor()
            self.btnRemapDataset.setEnabled(True)

    def oversample_background(
            self,
            myfolder,
            base_ratio=0.10,
            max_ratio=0.20,
            max_dup_per_image=2):

        import os, shutil, random

        splits = ["train", "val"]
        found_any = False
        total_created = 0

        print("\n[BACKGROUND OVERSAMPLING - HEALTH AWARE]")

        # GET BACKGROUND HEALTH
        try:
            bg_health = self.yolo_recommended_params["notes"]["background_health"]
        except Exception:
            print("⚠️ No background health available, fallback to static ratio.")
            bg_health = 50.0

        # normalize
        bg_health = max(0.0, min(100.0, bg_health))

        # how good
        priority = 1.0 - (bg_health / 100.0)

        target_ratio = base_ratio + (max_ratio - base_ratio) * priority

        print(f"Background health: {bg_health:.1f}")
        print(f"Priority: {priority:.2f}")
        print(f"Target ratio: {target_ratio:.2%}")

        for split in splits:

            images_dir = os.path.join(myfolder, "images", split)
            labels_dir = os.path.join(myfolder, "labels", split)

            if not os.path.isdir(labels_dir) or not os.path.isdir(images_dir):
                print(f"[{split}] ❌ Missing folders")
                continue

            found_any = True

            background_labels = []
            all_labels = []

            # SCAN dataset
            for fname in os.listdir(labels_dir):

                if not fname.endswith(".txt"):
                    continue

                path = os.path.join(labels_dir, fname)

                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                all_labels.append(fname)

                if size == 0:
                    background_labels.append(fname)

            n_total = len(all_labels)
            n_bg = len(background_labels)

            if n_total == 0:
                print(f"[{split}] ❌ Empty dataset")
                continue

            current_ratio = n_bg / n_total

            print(f"\n[{split}]")
            print(f"Total: {n_total}")
            print(f"Background: {n_bg} ({current_ratio:.2%})")

            if current_ratio >= target_ratio:
                print(f"[{split}] ✅ Already sufficient")
                continue

            target_bg = int(target_ratio * n_total)
            needed = target_bg - n_bg

            print(f"[{split}] Need: {needed}")

            created = 0

            # duplication
            for label_file in background_labels:

                if created >= needed:
                    break

                base = os.path.splitext(label_file)[0]
                img_path = None
                for ext in [".jpg", ".jpeg", ".png"]:
                    candidate = os.path.join(images_dir, base + ext)
                    if os.path.exists(candidate):
                        img_path = candidate
                        img_ext = ext
                        break

                if img_path is None:
                    continue

                label_path = os.path.join(labels_dir, label_file)

                # duplicate according to priority
                dynamic_max_dup = max(
                    1,
                    min(
                        max_dup_per_image,
                        int(max_dup_per_image * (0.5 + priority))
                    )
                )

                for i in range(1, dynamic_max_dup + 1):

                    if created >= needed:
                        break

                    new_base = f"{base}_bgdup{i}"

                    new_img_path = os.path.join(images_dir, new_base + img_ext)
                    new_lbl_path = os.path.join(labels_dir, new_base + ".txt")

                    # collision
                    if os.path.exists(new_img_path) or os.path.exists(new_lbl_path):
                        new_base = f"{base}_bgdup{i}_{random.randint(0, 9999)}"
                        new_img_path = os.path.join(images_dir, new_base + img_ext)
                        new_lbl_path = os.path.join(labels_dir, new_base + ".txt")

                    try:

                        os.link(img_path, new_img_path)
                        shutil.copy2(label_path, new_lbl_path)
                    except Exception as e:
                        print(f"[{split}] ⚠️ Copy failed: {e}")
                        continue

                    created += 1
                    total_created += 1

            print(f"[{split}] ✅ Created: {created}")

        if not found_any:
            print("❌ No label folders found.")
            return

        if total_created == 0:
            print("⚠️ No background samples added.")
        else:
            print(f"\n✅ Done. Created {total_created} samples.")

    def onRemapClicked(self):

        self.chkOversample.blockSignals(True)
        self.chkBackground.blockSignals(True)

        self.chkOversample.setChecked(False)
        self.chkBackground.setChecked(False)

        self.chkOversample.blockSignals(False)
        self.chkBackground.blockSignals(False)

        if not self.input_folder:
            return

        selected = self.getSelectedYoloClasses()

        if not selected:
            self.logWindow.append("⚠️ No classes selected.\n")
            return

        self.logWindow.clear()
        self.logWindow.append("\n──────── REMAP ────────\n")

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            working_dir = self.createWorkingDataset()

            self.applyRemap(working_dir)

            self.pipeline_dataset = working_dir

            self.input_folder = working_dir

            self.updateYoloUIFromFolder(working_dir)
            self.onGetYoloTrainingSuggestionsFromFolder(working_dir)

            self.last_applied_classes = selected
            self.classes_dirty = False

            self.btnRemap.setEnabled(False)
            self.updateRemapButtonStyle()

            if self.chkOversample.isChecked() or self.chkBackground.isChecked():
                self.runPipelinePreview()


        finally:
            QApplication.restoreOverrideCursor()
    def oversample_background(
            self,
            myfolder,
            base_ratio=0.10,
            max_ratio=0.20,
            max_dup_per_image=2):

        import os, shutil, random

        splits = ["train", "val"]
        total_created = 0

        print("\n[BACKGROUND OVERSAMPLING - ZERO COPY]")

        try:
            bg_health = self.yolo_recommended_params["notes"]["background_health"]
        except:
            bg_health = 50.0

        bg_health = max(0.0, min(100.0, bg_health))
        priority = 1.0 - (bg_health / 100.0)
        target_ratio = base_ratio + (max_ratio - base_ratio) * priority

        for split in splits:

            images_dir = os.path.join(self.original_input_folder, "images", split)
            labels_dir = os.path.join(myfolder, "labels", split)

            if not os.path.isdir(labels_dir):
                continue

            background_labels = []
            all_labels = []

            for fname in os.listdir(labels_dir):

                if not fname.endswith(".txt"):
                    continue

                path = os.path.join(labels_dir, fname)

                all_labels.append(fname)

                if os.path.getsize(path) == 0:
                    background_labels.append(fname)

            n_total = len(all_labels)
            n_bg = len(background_labels)

            if n_total == 0:
                continue

            current_ratio = n_bg / n_total

            print(f"\n[{split}] {n_bg}/{n_total} ({current_ratio:.2%})")

            if current_ratio >= target_ratio:
                print("✅ Already sufficient")
                continue

            target_bg = int(target_ratio * n_total)
            needed = target_bg - n_bg

            created = 0

            for label_file in background_labels:

                if created >= needed:
                    break

                base = os.path.splitext(label_file)[0]

                img_path = None
                for ext in [".jpg", ".jpeg", ".png"]:
                    candidate = os.path.join(images_dir, base + ext)
                    if os.path.exists(candidate):
                        img_path = candidate
                        img_ext = ext
                        break

                if img_path is None:
                    continue

                label_path = os.path.join(labels_dir, label_file)

                dynamic_max_dup = max(
                    1,
                    min(
                        max_dup_per_image,
                        int(max_dup_per_image * (0.5 + priority))
                    )
                )

                for i in range(1, dynamic_max_dup + 1):

                    if created >= needed:
                        break

                    new_base = f"{base}_bgdup{i}"

                    new_lbl_path = os.path.join(labels_dir, new_base + ".txt")
                    new_img_path = os.path.join(images_dir, new_base + img_ext)

                    # ✅ copia label
                    shutil.copy2(label_path, new_lbl_path)

                    # ✅ hardlink immagine
                    try:
                        if not os.path.exists(new_img_path):
                            os.link(img_path, new_img_path)
                    except:
                        shutil.copy2(img_path, new_img_path)

                    created += 1
                    total_created += 1

            print(f"[{split}] ✅ Created: {created}")

        if total_created == 0:
            print("⚠️ No background samples added.")
        else:
            print(f"\n✅ Done. Created {total_created} samples.")

    def oversample_imbalanced_classes(
            self,
            myfolder,
            duplication_factor=2):

        split = "train"

        #  temp labels
        labels_dir = os.path.join(myfolder, "labels", split)
        # original images
        images_dir = os.path.join(self.original_input_folder, "images", split)

        yaml_path = os.path.join(myfolder, "dataset.yaml")

        if not os.path.exists(labels_dir) or not os.path.exists(yaml_path):
            return

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        names = data.get("names", {})
        id_to_name = {k: v for k, v in names.items()}

        class_stats = (
            self.yolo_recommended_params["notes"]
            ["class_stats"]
        )

        target_classes = set()

        for cls_id, cls_name in id_to_name.items():

            stats = class_stats.get(cls_name)

            if stats is None:
                continue

            if (
                    stats["oversampling_score"] > 0.50
                    and
                    stats["img_count"] >= 20
            ):
                target_classes.add(cls_id)


        print(f"\n🎯 Target classes: {[id_to_name[i] for i in target_classes]}")
        for cls_id in target_classes:
            cls_name = id_to_name[cls_id]

            print(
                f"   {cls_name}: "
                f"{class_stats[cls_name]['oversampling_score']:.2f}"
            )

        dup_per_class = defaultdict(int)
        img_per_class = defaultdict(int)

        image_info = {}

        # BUILD IMAGE INFO
        for label_file in os.listdir(labels_dir):

            if not label_file.endswith(".txt"):
                continue

            if "_dup" in label_file:
                continue

            path = os.path.join(labels_dir, label_file)

            classes = []

            with open(path) as f:
                for line in f:
                    parts = line.strip().split()
                    if not parts:
                        continue

                    try:
                        cls_id = int(float(parts[0]))
                    except:
                        continue

                    classes.append(cls_id)

            if classes:
                image_info[label_file] = classes

                for c in set(classes):
                    img_per_class[id_to_name[c]] += 1

        if not image_info:
            print("❌ No valid annotations found.")
            return

        #  FILTER CANDIDATES
        candidates = []

        min_area_threshold = 0.002

        for label_file, classes in image_info.items():

            total = len(classes)
            if total == 0:
                continue

            counts = Counter(classes)

            target_count = sum(counts[c] for c in counts if c in target_classes)
            if target_count == 0:
                continue

            minority_ratio = target_count / total

            if minority_ratio < 0.1:
                continue

            max_majority_frac = max(counts.values()) / total
            if max_majority_frac > 0.9:
                continue

            # AREA FILTER
            label_path = os.path.join(labels_dir, label_file)

            valid_minority = False

            with open(label_path) as f:
                for line in f:

                    parts = list(map(float, line.split()))
                    cls_id = int(parts[0])

                    if cls_id not in target_classes:
                        continue

                    if len(parts) == 5:
                        _, _, w, h = parts[1:]
                        area = w * h
                    else:
                        coords = np.array(parts[1:]).reshape(-1, 2)
                        w = coords[:, 0].max() - coords[:, 0].min()
                        h = coords[:, 1].max() - coords[:, 1].min()
                        area = w * h

                    if area > min_area_threshold:
                        valid_minority = True
                        break

            if not valid_minority:
                continue


            scores = [
                class_stats[
                    id_to_name[c]
                ]["oversampling_score"]

                for c in counts
                if c in target_classes
            ]

            if not scores:
                continue

            avg_score = sum(scores) / len(scores)

            if avg_score > 0.75:

                rarity_boost = 0.50

            elif avg_score > 0.40:

                rarity_boost = 0.25

            else:

                rarity_boost = 0.0

            priority = avg_score + rarity_boost

            candidates.append((label_file, priority, minority_ratio, classes))

        if not candidates:
            print("❌ No valid candidates after filtering.")
            return

        candidates.sort(key=lambda x: x[1], reverse=True)

        print(f"\n📷 Candidates after filtering: {len(candidates)}")

        total_created = 0

        # DUPLICATION
        for label_file, priority, ratio, classes in candidates:

            base = os.path.splitext(label_file)[0]

            # original images
            img_path = None
            for ext in [".jpg", ".jpeg", ".png"]:
                p = os.path.join(images_dir, base + ext)
                if os.path.exists(p):
                    img_path = p
                    img_ext = ext
                    break

            if img_path is None:
                continue

            label_path = os.path.join(labels_dir, label_file)

            max_dup = int(priority * duplication_factor)

            if max_dup == 0 and priority > 0.2:
                max_dup = 1

            if priority > 0.6:
                max_dup = max(max_dup, 2)

            max_dup = min(max_dup, 3)

            if max_dup == 0:
                continue

            for dup_idx in range(1, max_dup + 1):

                new_base = f"{base}_dup{dup_idx}"

                new_lbl_path = os.path.join(labels_dir, new_base + ".txt")
                new_img_path = os.path.join(images_dir, new_base + img_ext)

                # copy label
                shutil.copy2(label_path, new_lbl_path)

                try:
                    if not os.path.exists(new_img_path):
                        os.link(img_path, new_img_path)
                except:
                    shutil.copy2(img_path, new_img_path)

                total_created += 1

                for c in set(classes):
                    if c in target_classes:
                        dup_per_class[id_to_name[c]] += 1

            print(
                f"{label_file} → priority {priority:.2f} "
                f"| ratio {ratio:.2f} → dup {max_dup}"
            )

        # FINAL LOG
        print("\n📊 IMAGE DISTRIBUTION (per class):")
        for cls, count in img_per_class.items():
            print(f"{cls}: {count} images")

        print("\n📈 DUPLICATIONS (target classes):")
        for cls, count in dup_per_class.items():
            print(f"{cls}: +{count}")

        print("\n✅ Oversampling completed.")
        print(f"📈 Created samples: {total_created}")


    def clearLog(self):
        if hasattr(self, "logWindow"):
            self.logWindow.clear()

    def onGetYoloTrainingSuggestionsFromFolder(self, folder):

        temp_input = self.input_folder
        self.input_folder = folder

        buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(buffer):
                training_support_index, recommended_params = self.analyzeInstances()
                self.yolo_recommended_params = recommended_params
                self.training_support_index= training_support_index



        except Exception:
            error_msg = traceback.format_exc()
            self.logWindow.append("❌ ERROR during YOLO training analysis:\n")
            self.logWindow.append(error_msg)

        output = buffer.getvalue()

        if output.strip():
            self.logWindow.append(output)
        else:
            self.logWindow.append("⚠️ No output produced.")

        self.input_folder = temp_input


    def clearYoloCache(self):

        cache_names = {
            "train.cache",
            "val.cache",
            "yolo_cache.json"
        }

        search_dirs = [
            self.input_folder,
            os.path.join(self.input_folder, "labels"),
            os.path.expanduser(r"~\AppData\Local\Ultralytics"),
        ]

        for base_dir in search_dirs:
            if not base_dir or not os.path.exists(base_dir):
                continue

            for root, _, files in os.walk(base_dir):
                for fname in files:
                    if fname in cache_names:
                        path = os.path.join(root, fname)
                        try:
                            os.remove(path)
                            time.sleep(0.05)
                        except Exception:
                            pass
    def onExportYoloParams(self):

        if not self.yolo_recommended_params:
            QMessageBox.warning(
                self,
                self.TAGLAB_VERSION,
                "No training parameters available.\n"
                "Please run 'Get training suggestions' first."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export YOLO training parameters",
            "yolo_training_params.yaml",
            "YAML files (*.yaml *.yml)"
        )

        if not file_path:
            return

        try:
            params = self.yolo_recommended_params.copy()
            params.pop("notes", None)

            with open(file_path, "w") as f:
                yaml.safe_dump(
                    params,
                    f,
                    sort_keys=False,
                    default_flow_style=False
                )

            QMessageBox.information(
                self,
                self.TAGLAB_VERSION,
                f"Training parameters exported successfully:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                self.TAGLAB_VERSION,
                f"Failed to export training parameters:\n{e}"
            )

    def analyzeInstances(self):

        # ----------------------------------------------------
        # LOAD YAML
        # ----------------------------------------------------

        yaml_path = os.path.join(
            self.input_folder,
            "dataset.yaml"
        )

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        names = data.get("names", {})

        dataset_root = getattr(
            self,
            "original_input_folder",
            self.input_folder
        )

        image_dir = os.path.join(
            dataset_root,
            "images",
            "train"
        )

        imgsz = 640

        if os.path.exists(image_dir):

            imgs = [
                f for f in os.listdir(image_dir)
                if f.lower().endswith(
                    (".jpg", ".jpeg", ".png")
                )
            ]

            if imgs:
                with Image.open(
                        os.path.join(image_dir, imgs[0])
                ) as im:
                    imgsz = im.size[0]

        else:

            print(
                f"⚠ Training images folder not found:\n"
                f"{image_dir}\n"
                f"Using fallback imgsz={imgsz}"
            )

        # ----------------------------------------------------
        # PARSING
        # ----------------------------------------------------

        label_dirs = [
            os.path.join(self.input_folder, "labels", "train"),
            os.path.join(self.input_folder, "labels", "val")
        ]

        areas = {}
        aspect_ratios = {}
        pixel_sizes = {}
        images_per_class = {}

        total_txt = 0
        background_images = 0

        for label_dir in label_dirs:

            if not os.path.exists(label_dir):
                continue

            for fname in os.listdir(label_dir):

                if not fname.endswith(".txt"):
                    continue

                total_txt += 1

                path = os.path.join(
                    label_dir,
                    fname
                )

                with open(path) as f:
                    lines = f.readlines()

                if len(lines) == 0:
                    background_images += 1
                    continue

                seen_classes = set()

                for line in lines:

                    parts = list(
                        map(float, line.split())
                    )

                    cls = names[int(parts[0])]

                    if len(parts) > 5:

                        coords = np.array(
                            parts[1:]
                        ).reshape(-1, 2)

                        x = coords[:, 0]
                        y = coords[:, 1]

                        area = 0.5 * abs(
                            np.dot(x, np.roll(y, 1))
                            -
                            np.dot(y, np.roll(x, 1))
                        )

                        w = x.max() - x.min()
                        h = y.max() - y.min()

                    else:

                        _, _, w, h = parts[1:]
                        area = w * h

                    if h <= 0:
                        continue

                    ar = w / h

                    side_px = np.sqrt(area) * imgsz

                    areas.setdefault(
                        cls, []
                    ).append(area)

                    aspect_ratios.setdefault(
                        cls, []
                    ).append(ar)

                    pixel_sizes.setdefault(
                        cls, []
                    ).append(side_px)

                    seen_classes.add(cls)

                for cls in seen_classes:
                    images_per_class[cls] = (
                            images_per_class.get(cls, 0)
                            + 1
                    )

        if not areas:
            raise RuntimeError(
                "No annotations found."
            )

        # ----------------------------------------------------
        # BUILD STATS
        # ----------------------------------------------------

        stats = {}

        max_instances = max(
            len(v)
            for v in areas.values()
        )

        for cls in areas:
            arr_area = np.array(
                areas[cls]
            )

            arr_ar = np.array(
                aspect_ratios[cls]
            )

            arr_px = np.array(
                pixel_sizes[cls]
            )

            n = len(arr_area)

            img_count = images_per_class.get(
                cls, 0
            )


            fragmentation = (
                    n / max(1, img_count)
            )

            ar_mean = max(
                np.mean(arr_ar),
                1e-6
            )

            scarcity_score = (
                    1.0
                    -
                    n / max_instances
            )

            image_penalty = (
                    1.0
                    -
                    min(
                        img_count / 100.0,
                        1.0
                    )
            )

            oversampling_score = (
                    0.6 * scarcity_score
                    +
                    0.4 * image_penalty
            )

            stats[cls] = {

                "n": n,

                "img_count": img_count,

                "fragmentation": fragmentation,

                "scarcity_score": scarcity_score,

                "oversampling_score":
                    oversampling_score,

                "area_median":
                    float(np.median(arr_area)),

                "area_p10":
                    float(np.percentile(arr_area, 10)),

                "side_median_px":
                    float(np.median(arr_px)),

                "side_p10_px":
                    float(np.percentile(arr_px, 10)),

                "micro_ratio":
                    float(np.mean(arr_px < 10)),

                "ar_median":
                    float(np.median(arr_ar)),

                "ar_cv":
                    float(
                        np.std(arr_ar)
                        / ar_mean
                    )
            }

        # ----------------------------------------------------
        # DATASET LEVEL STATS
        # ----------------------------------------------------

        n_images = total_txt

        total_instances = sum(
            s["n"]
            for s in stats.values()
        )

        density_global = (
                total_instances
                /
                max(1, n_images)
        )

        bg_ratio = (
                background_images
                /
                max(1, n_images)
        )

        instance_counts = [
            s["n"]
            for s in stats.values()
        ]

        imbalance_ratio = (
                max(instance_counts)
                /
                max(1, min(instance_counts))
        )



        # ----------------------------------------------------
        # OVERVIEW
        # ----------------------------------------------------

        print("\n[DATASET OVERVIEW]\n")

        print(f"Images: {n_images}")
        print(f"Instances: {total_instances}")
        print(f"Average object density: {density_global:.2f}")
        print(
            f"Background images: "
            f"{background_images} "
            f"({bg_ratio:.1%})"
        )

        if n_images < 150:
            print("Dataset is very small: high overfitting risk.")
        elif n_images < 300:
            print("Dataset is limited: training may be unstable.")
        else:
            print("Dataset size is adequate.")

        print("\n[CLASS IMBALANCE ANALYSIS]\n")

        print(f"Max/min ratio: {imbalance_ratio:.1f}:1")

        if imbalance_ratio > 50:
            print("Extreme imbalance detected.")
        elif imbalance_ratio > 20:
            print("Severe imbalance detected.")
        elif imbalance_ratio > 10:
            print("Moderate imbalance detected.")
        else:
            print("Class balance is acceptable.")

        # ----------------------------------------------------
        # CLASS TABLE
        # ----------------------------------------------------

        print("\n[CLASS STATISTICS]\n")

        print(
            f"{'Class':20}"
            f"{'Inst':>8}"
            f"{'Images':>8}"
            f"{'Frag':>8}"
            f"{'Scar':>8}"
            f"{'OverS':>8}"
            f"{'MedPx':>10}"
            f"{'Micro%':>10}"
        )

        for cls, s in stats.items():
            print(
                f"{cls:20}"
                f"{s['n']:8d}"
                f"{s['img_count']:8d}"
                f"{s['fragmentation']:8.1f}"
                f"{s['scarcity_score']:8.2f}"
                f"{s['oversampling_score']:8.2f}"
                f"{s['side_median_px']:10.1f}"
                f"{100 * s['micro_ratio']:10.1f}"
            )

        # ----------------------------------------------------
        # TRAINING SUPPORT INDEX
        # ----------------------------------------------------

        print("\n[TRAINING SUPPORT INDEX]\n")

        training_support_index = {}

        limiting_class = None
        lowest_support = 999

        for cls, s in stats.items():

            scale_score = min(
                1.0,
                s["side_median_px"] / 40.0
            )

            coverage_score = min(
                1.0,
                s["img_count"] / 100.0
            )

            rarity_support = (
                    1.0
                    -
                    s["scarcity_score"]
            )

            geometry_score = min(
                1.0,
                s["ar_cv"] / 0.5
            )

            tsi = (

                          0.40 * scale_score

                          +

                          0.30 * coverage_score

                          +

                          0.20 * rarity_support

                          +

                          0.10 * geometry_score

                  ) * 100.0

            training_support_index[cls] = tsi

            if tsi < lowest_support:
                lowest_support = tsi
                limiting_class = cls

            print(
                f"{cls}: "
                f"{tsi:.1f}/100"
            )

        # ----------------------------------------------------
        # EFFECTIVE IMAGES ANALYSIS
        # ----------------------------------------------------

        for cls, s in stats.items():

            if s["img_count"] < 20:
                print(
                    f"⚠ {cls}: "
                    f"only {s['img_count']} images contain this class."
                )

        # ----------------------------------------------------
        # FRAGMENTATION ANALYSIS
        # ----------------------------------------------------

        print("\n[FRAGMENTATION ANALYSIS]\n")

        for cls, s in stats.items():

            frag = s["fragmentation"]

            print(
                f"{cls}: "
                f"{frag:.1f} instances/image"
            )

            if frag > 50:

                print(
                    "  Very concentrated class. "
                    "Many instances come from few images."
                )

            elif frag > 20:

                print(
                    "  Moderately concentrated class."
                )

        # ----------------------------------------------------
        # MICRO OBJECTS ANALYSIS
        # ----------------------------------------------------

        print("\n[MICRO OBJECT ANALYSIS]\n")

        worst_micro = 0

        for cls, s in stats.items():
            micro = s["micro_ratio"]

            worst_micro = max(
                worst_micro,
                micro
            )

            print(
                f"{cls}: "
                f"{micro:.1%} below 10 px"
            )

        # ----------------------------------------------------
        # BACKGROUND ANALYSIS
        # ----------------------------------------------------

        print("\n[BACKGROUND ANALYSIS]\n")

        bg_ratio = background_images / max(1, n_images)

        score_bg = min(1.0, bg_ratio / 0.1)
        score_density_bg = max(0.0, 1.0 - density_global / 8.0)

        background_health = (0.6 * score_bg + 0.4 * score_density_bg) * 100

        print(f"Background images: {background_images}/{n_images} ({bg_ratio:.1%})")
        print(f"Background Health Score: {background_health:.1f}/100")


        print("\n[RECOMMENDED YOLO PARAMETERS]\n")

        max_scarcity = max(
            s["scarcity_score"]
            for s in stats.values()
        )

        rare_classes = [
            cls
            for cls, s in stats.items()
            if s["scarcity_score"] > 0.90
        ]

        low_coverage_classes = [
            cls
            for cls, s in stats.items()
            if s["img_count"] < 30
        ]

        max_micro_ratio = max(
            s["micro_ratio"]
            for s in stats.values()
        )

        # ----------------------------------------------------
        # COPY PASTE
        # ----------------------------------------------------

        if max_scarcity > 0.98:

            copy_paste = 0.50

        elif max_scarcity > 0.95:

            copy_paste = 0.30

        elif max_scarcity > 0.80:

            copy_paste = 0.15

        else:

            copy_paste = 0.0

        # ----------------------------------------------------
        # EXTRA EPOCHS
        # ----------------------------------------------------

        if len(rare_classes) >= 2:

            extra_epochs = 0.50

        elif len(rare_classes) == 1:

            extra_epochs = 0.25

        else:

            extra_epochs = 0.0

        # ----------------------------------------------------
        # MOSAIC
        # ----------------------------------------------------

        if max_micro_ratio > 0.20:

            close_mosaic = 40

        elif max_micro_ratio > 0.10:

            close_mosaic = 20

        else:

            close_mosaic = 0

        # ----------------------------------------------------
        # BOX / DFL
        # ----------------------------------------------------

        smallest_side = min(
            s["side_median_px"]
            for s in stats.values()
        )

        if smallest_side < 20:

            box = 18.0
            dfl = 2.5

        elif smallest_side < 35:

            box = 12.0
            dfl = 2.0

        else:

            box = 7.5
            dfl = 1.5

        # ----------------------------------------------------
        # SCALE AUGMENTATION
        # ----------------------------------------------------

        if max_micro_ratio > 0.10:

            scale_min = 0.8

        else:

            scale_min = 0.5

        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        print(f"copy_paste   = {copy_paste}")
        print(f"extra epochs = +{int(extra_epochs * 100)}%")
        print(f"box loss     = {box}")
        print(f"DFL          = {dfl}")
        print(f"scale        = [{scale_min}, 1.5]")
        print(f"close_mosaic = {close_mosaic}")

        print("\n[TRAINING NOTES]\n")

        # if rare_classes:
        #     print(
        #         "Rare classes detected: "
        #         + ", ".join(rare_classes)
        #     )

        if low_coverage_classes:
            print(
                "Limited image coverage: "
                + ", ".join(low_coverage_classes)
            )

        if max_micro_ratio > 0.10:
            print(
                "High micro-object ratio detected."
            )

        if background_health < 40:
            print(
                "Background coverage is limited."
            )

        oversampling_scores = {
            cls: s["oversampling_score"]
            for cls, s in stats.items()
        }

        return oversampling_scores, {

            "copy_paste": copy_paste,

            "extra_epochs_factor":
                extra_epochs,

            "box": box,

            "dfl": dfl,

            "scale":
                (scale_min, 1.5),

            "close_mosaic":
                close_mosaic,

            "notes": {

                "limiting_class":
                    limiting_class,

                "lowest_training_support":
                    lowest_support,

                "background_health":
                    background_health,

                "dataset_density":
                    density_global,

                "imbalance_ratio":
                    imbalance_ratio,

                "micro_ratio":
                    max(
                        s["micro_ratio"]
                        for s in stats.values()
                    ),

                "class_stats":
                    stats,

                "training_support":
                    training_support_index,

                "image_size":
                    imgsz
            }
        }

    def analyzeYoloDataset(self):
        if not self.input_folder:
            raise RuntimeError("Input folder not set")

        yaml_path = os.path.join(self.input_folder, "dataset.yaml")
        if not os.path.exists(yaml_path):
            raise RuntimeError("dataset.yaml not found")

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        names_dict = data.get("names")
        if not isinstance(names_dict, dict):
            raise RuntimeError("Invalid dataset.yaml: missing 'names'")

        label_dirs = [
            os.path.join(self.input_folder, "labels", "train"),
            os.path.join(self.input_folder, "labels", "val"),
        ]

        counts = {}

        for label_dir in label_dirs:
            if not os.path.isdir(label_dir):
                continue

            for fname in os.listdir(label_dir):
                if not fname.endswith(".txt"):
                    continue

                path = os.path.join(label_dir, fname)
                with open(path, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if not parts:
                            continue
                        cls_id = int(parts[0])
                        counts[cls_id] = counts.get(cls_id, 0) + 1

        count_classes = {
            names_dict[k]: counts.get(k, 0)
            for k in names_dict.keys()
        }

        return count_classes

    def getSelectedYoloClasses(self):
        return [cb.text() for cb in self.checkboxes_YL if cb.isChecked()]

    def buildYoloClassMapping(self, selected_classes):
        yaml_path = os.path.join(self.input_folder, "dataset.yaml")
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        names = data["names"]
        name_to_old_id = {v: k for k, v in names.items()}

        mapping = {}
        new_names = {}
        new_id = 0

        for cls_name in selected_classes:
            if cls_name not in name_to_old_id:
                continue

            old_id = name_to_old_id[cls_name]
            mapping[old_id] = new_id
            new_names[new_id] = cls_name
            new_id += 1

        removed_classes = set(names.keys()) - set(mapping.keys())

        return mapping, removed_classes, new_names

    def copyYoloImages(self):
        for split in ["train", "val"]:
            src = os.path.join(self.input_folder, "images", split)
            dst = os.path.join(self.output_folder, "images", split)
            if os.path.exists(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)

    def remapYoloLabels(self, mapping, removed_classes):
        label_dirs = [
            os.path.join(self.input_folder, "labels", "train"),
            os.path.join(self.input_folder, "labels", "val"),
        ]

        out_label_dirs = [
            os.path.join(self.output_folder, "labels", "train"),
            os.path.join(self.output_folder, "labels", "val"),
        ]

        for src_dir, dst_dir in zip(label_dirs, out_label_dirs):
            if not os.path.exists(src_dir):
                continue

            os.makedirs(dst_dir, exist_ok=True)

            for fname in os.listdir(src_dir):
                if not fname.endswith(".txt"):
                    continue

                src_path = os.path.join(src_dir, fname)
                dst_path = os.path.join(dst_dir, fname)

                new_lines = []

                with open(src_path, "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        old_cls = int(parts[0])

                        if old_cls in removed_classes:
                            continue

                        if old_cls in mapping:
                            parts[0] = str(mapping[old_cls])
                            new_lines.append(" ".join(parts))

                with open(dst_path, "w") as f:
                    f.write("\n".join(new_lines))

    def writeNewYoloYaml(self, new_names):

        new_yaml = {
            "path": self.original_input_folder,  # original images
            "val": "images/val",
            "names": new_names
        }

        out_path = os.path.join(self.output_folder, "dataset.yaml")
        with open(out_path, "w") as f:
            yaml.safe_dump(new_yaml, f, sort_keys=False)

    def updateCheckboxStyle(self):
        for cb in self.checkboxes_YL:

            if cb.isChecked():
                cb.setStyleSheet("color: white;")
            else:
                cb.setStyleSheet("color: gray;")

    def createClassesToRecognizeWidgetYolo(self, count_classes, folder):

        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        grid = QGridLayout(widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        all_classes = []
        for name in sorted(count_classes.keys()):
            label = self.project_labels.get(name)
            color = label.fill if label else (0, 0, 0)
            count = count_classes.get(name, 0)
            all_classes.append((name, color, count))


        filtered_classes = all_classes

        self.checkboxes_YL = []
        CLASSES_PER_ROW = 3

        if not filtered_classes:
            grid.addWidget(QLabel("No classes found."), 0, 0)
            return widget

        for i, (name, color, count) in enumerate(filtered_classes):

            checkbox = QCheckBox(name)
            checkbox.stateChanged.connect(self.onClassesChanged)
            checkbox.stateChanged.connect(self.updateCheckboxStyle)
            self.checkboxes_YL.append(checkbox)

            btn_color = QPushButton()
            btn_color.setFixedSize(20, 20)
            btn_color.setFlat(True)
            btn_color.setStyleSheet(
                f"QPushButton {{ background-color: rgb({color[0]}, {color[1]}, {color[2]}); border: none; }}"
            )

            lbl_count = QLabel(str(count))

            if count == 0:
                lbl_count.setStyleSheet("QLabel { color: gray; min-width: 40px; }")
            elif count < 300:
                lbl_count.setStyleSheet("QLabel { color: red; min-width: 40px; }")
            else:
                lbl_count.setStyleSheet("QLabel { color: green; min-width: 40px; }")

            hlayout = QHBoxLayout()
            hlayout.setContentsMargins(0, 0, 0, 0)
            hlayout.setSpacing(6)
            hlayout.addWidget(btn_color)
            hlayout.addWidget(lbl_count)

            row = i // CLASSES_PER_ROW
            col = (i % CLASSES_PER_ROW) * 2

            grid.addWidget(checkbox, row, col)
            grid.addLayout(hlayout, row, col + 1)


        background_images = 0

        for split in ["train", "val"]:
            label_dir = os.path.join(folder, "labels", split)

            if not os.path.exists(label_dir):
                continue

            for fname in os.listdir(label_dir):
                if fname.endswith(".txt"):
                    path = os.path.join(label_dir, fname)
                    if os.path.getsize(path) == 0:
                        background_images += 1

        row = (len(filtered_classes) // CLASSES_PER_ROW) + 1

        lbl_bg_title = QLabel("Background tiles:")
        lbl_bg_value = QLabel(str(background_images))

        hlayout_bg = QHBoxLayout()
        hlayout_bg.addWidget(lbl_bg_title)
        hlayout_bg.addWidget(lbl_bg_value)

        grid.addLayout(hlayout_bg, row, 0, 1, 2)

        return widget

    def onClassesChanged(self):

        self.updateCheckboxStyle()

        current = self.getSelectedYoloClasses()

        # current differs form last state
        if current != self.last_applied_classes:

            if not self.classes_dirty:
                self.logWindow.append("ℹ️ Class selection changed. Press 'Re-map' to apply.\n")

            self.classes_dirty = True
            self.btnRemap.setEnabled(True)
            self.updateRemapButtonStyle()

        else:

            self.classes_dirty = False
            self.btnRemap.setEnabled(False)
            self.updateRemapButtonStyle()

    def createClassesToRecognizeWidgets(self):

        content = QWidget()
        content.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        content.lblTotalBackgroundValue = None

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)

        # no useful classes
        if not self.freq_classes or all(v == 0 for v in self.freq_classes.values()):
            lbl = QLabel("No classes found in the dataset.")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)
            return content

        # create grid
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(12)
        grid_layout.setVerticalSpacing(6)

        self.checkboxes = []
        CLASSES_PER_ROW = 3

        for i, key in enumerate(self.freq_classes.keys()):

            perc = round(self.freq_classes[key] * 100.0, 2)

            checkbox = QCheckBox(key)
            checkbox.setChecked(True)

            lbl_perc = QLabel(f"{perc}%")

            if perc < 5.0:
                lbl_perc.setStyleSheet("color: red;")
            else:
                lbl_perc.setStyleSheet("color: lightgreen;")

            if key == "Background":
                checkbox.setAttribute(Qt.WA_TransparentForMouseEvents)
                checkbox.setFocusPolicy(Qt.NoFocus)

                lbl_bg = QLabel(f"{perc}%")
                lbl_bg.setStyleSheet("color: white;")
                content.lblTotalBackgroundValue = lbl_bg

            checkbox.stateChanged.connect(self.updateCumulativeBackground)
            self.checkboxes.append(checkbox)

            btn_color = QPushButton()
            btn_color.setFixedSize(20, 20)
            btn_color.setFlat(True)

            label = self.project_labels.get(key)
            color = label.fill if label else (0, 0, 0)

            r, g, b = color
            btn_color.setStyleSheet(
                f"background-color: rgb({r},{g},{b}); border: none;"
            )

            hlayout = QHBoxLayout()
            hlayout.setContentsMargins(0, 0, 0, 0)
            hlayout.setSpacing(6)
            hlayout.addWidget(btn_color)
            hlayout.addWidget(lbl_perc)

            row = i // CLASSES_PER_ROW
            col = (i % CLASSES_PER_ROW) * 2

            grid_layout.addWidget(checkbox, row, col)
            grid_layout.addLayout(hlayout, row, col + 1)

        # cumulative background
        last_row = (len(self.freq_classes) - 1) // CLASSES_PER_ROW + 1

        if content.lblTotalBackgroundValue is not None:
            grid_layout.addWidget(QLabel("Cumulative background:"), last_row, 0)
            grid_layout.addWidget(content.lblTotalBackgroundValue, last_row, 1)

        layout.addLayout(grid_layout)

        return content

    @pyqtSlot()
    def help(self):

        url = QUrl("http://taglab.isti.cnr.it/docs")
        QDesktopServices.openUrl(url)

    def getInputDatasetFolder(self):

        return self.editInputDatasetFolder.text()

    def updateCumulativeBackground(self):

        if self.groupbox_classes_DL is None:
            return

        widget = self.groupbox_classes_DL

        if not hasattr(widget, "lblTotalBackgroundValue"):
            return

        perc = 0.0
        for checkbox in self.checkboxes:
            if not checkbox.isChecked():
                perc += 100.0 * self.freq_classes[checkbox.text()]

        perc = perc + 100.0 * self.freq_classes["Background"]
        perc = round(perc, 2)

        widget.lblTotalBackgroundValue.setText(str(perc) + "%")

    def analyzeDeepLabDataset(self):

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

        tiles_discarded = 0

        input_folder = self.editInputDatasetFolder.text()

        if not os.path.exists(input_folder):
            QMessageBox.warning(self, self.TAGLAB_VERSION, "Input folder does not exist.")
            return

        output_folder = QFileDialog.getExistingDirectory(self, "Select output folder", "")
        if not output_folder:
            return

        TRAINING_FOLDER = os.path.join(input_folder, "training")

        if not os.path.exists(TRAINING_FOLDER):
            QMessageBox.critical(self, self.TAGLAB_VERSION, "Training folder not found.")
            return

        TRAINING_FOLDER_IMAGES = os.path.join(TRAINING_FOLDER, "images")
        TRAINING_FOLDER_LABELS = os.path.join(TRAINING_FOLDER, "labels")

        TRAINING_OUTPUT = os.path.join(output_folder, "training")
        TRAINING_OUTPUT_IMAGES = os.path.join(TRAINING_OUTPUT, "images")
        TRAINING_OUTPUT_LABELS = os.path.join(TRAINING_OUTPUT, "labels")

        os.makedirs(TRAINING_OUTPUT_IMAGES, exist_ok=True)
        os.makedirs(TRAINING_OUTPUT_LABELS, exist_ok=True)

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:

            pos_x = self.pos().x() + self.btnHelp.pos().x() - 80
            pos_y = self.pos().y() + self.radio_ThresholdBackground.pos().y() + self.radio_ThresholdBackground.height()

            self.progress_bar.move(int(pos_x), int(pos_y))
            self.progress_bar.setMessage("Initializing..")
            self.progress_bar.hidePerc()
            self.progress_bar.show()

            # ========= FILTERS ========= #

            if self.checkRemoveNoData.isChecked():
                self.progress_bar.showPerc()
                self.progress_bar.setMessage("Removing no data tiles..")
                QApplication.processEvents()

                tiles_discarded += self.discard_image_tiles_with_uniform_colors(
                    TRAINING_FOLDER_IMAGES,
                    TRAINING_FOLDER_LABELS,
                    TRAINING_OUTPUT_IMAGES,
                    TRAINING_OUTPUT_LABELS
                )

            if self.checkRemoveNoLabels.isChecked():
                self.progress_bar.setMessage("Removing tiles with no labels..")
                QApplication.processEvents()

                tiles_discarded += self.subsample(
                    TRAINING_FOLDER_IMAGES,
                    TRAINING_FOLDER_LABELS,
                    TRAINING_OUTPUT_IMAGES,
                    TRAINING_OUTPUT_LABELS,
                    flag=1
                )

            def validate_percent(edit_widget):
                text = edit_widget.text().strip()
                if not text.isdigit():
                    raise ValueError("Please enter a positive integer.")
                value = int(text)
                if not (1 <= value <= 100):
                    raise ValueError("Please enter a number between 1 and 100.")
                return value

            if self.radio_ThresholdBackground.isChecked():
                try:
                    validate_percent(self.editAmount1)
                    tiles_discarded += self.subsample(
                        TRAINING_FOLDER_IMAGES,
                        TRAINING_FOLDER_LABELS,
                        TRAINING_OUTPUT_IMAGES,
                        TRAINING_OUTPUT_LABELS,
                        flag=2
                    )
                except ValueError as e:
                    QMessageBox.warning(self, self.TAGLAB_VERSION, str(e))
                    self.editAmount1.clear()
                    return

            if self.radio_SubsampleBackground.isChecked():
                try:
                    validate_percent(self.editAmount2)
                    tiles_discarded += self.subsample(
                        TRAINING_FOLDER_IMAGES,
                        TRAINING_FOLDER_LABELS,
                        TRAINING_OUTPUT_IMAGES,
                        TRAINING_OUTPUT_LABELS,
                        flag=3
                    )
                except ValueError as e:
                    QMessageBox.warning(self, self.TAGLAB_VERSION, str(e))
                    self.editAmount2.clear()
                    return

            # ========= COPY EXTRA ========= #

            if tiles_discarded > 0:

                self.progress_bar.hidePerc()
                self.progress_bar.setMessage("Copying validation/test..")

                shutil.copytree(
                    os.path.join(input_folder, "validation"),
                    os.path.join(output_folder, "validation"),
                    dirs_exist_ok=True
                )

                shutil.copytree(
                    os.path.join(input_folder, "test"),
                    os.path.join(output_folder, "test"),
                    dirs_exist_ok=True
                )

                pixel_file = os.path.join(input_folder, "target-pixel-size.txt")
                if os.path.exists(pixel_file):
                    shutil.copy(pixel_file, output_folder)


                self.input_folder = output_folder
                self.editInputDatasetFolder.setText(output_folder)


                QMessageBox.information(
                    self,
                    self.TAGLAB_VERSION,
                    f"Filtering completed.\nTiles removed: {tiles_discarded}"
                )

            else:
                QMessageBox.information(
                    self,
                    self.TAGLAB_VERSION,
                    "No tiles were discarded. Dataset unchanged."
                )

        finally:
            QApplication.restoreOverrideCursor()
            self.progress_bar.hide()

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
            if checkbox.isChecked():
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
        if self.flag == 2:
            self.progress_bar.setMessage("Removing tiles..")

        if self.flag == 3:
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

            flag_copy = True

            threshold = 0.0
            if self.flag == 1:
                threshold = 0.9999
            elif flag == 2:
                # given threshold (option 2)
                threshold = int(self.editAmount1.text()) / 100.0

            if (self.flag == 1 or self.flag == 2) and p > threshold:
                tiles_removed += 1
                flag_copy = False  # this tile will not be copy in the new dataset
            else:
                if (self.flag == 3) and (p > 0.9999) and (coin < int(self.editAmount2.text())):
                    tiles_removed += 1
                    flag_copy = False  # this tile will not be copy in the new dataset

            if flag_copy:

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

    def updateRemapButtonStyle(self):

        if self.btnRemap.isEnabled():
            self.btnRemap.setStyleSheet("""
                QPushButton {
                    color: white;
                    border: 1px solid white;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: rgb(80,80,80);
                }
            """)
        else:
            self.btnRemap.setStyleSheet("""
                QPushButton {
                    color: gray;
                    border: 1px solid gray;
                    padding: 4px 12px;
                }
            """)
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
            self.analyzeDeepLabDataset()
            QApplication.restoreOverrideCursor()
            box.close()

            self.layoutClasses.removeWidget(self.groupbox_classes)
            self.groupbox_classes.setParent(None)
            self.groupbox_classes = None
            self.groupbox_classes = self.createClassesToRecognizeWidgets()
            self.layoutClasses.insertWidget(0, self.groupbox_classes)

    def autoDetectModel(self):

        self.resetModelState()


        if self.isValidYoloDataset(self.input_folder, require_split=True):
            self.modelStack.setCurrentIndex(2)
            self.runYoloAnalysis()
            return

        if self.isValidDeepLabDataset(self.input_folder):
            self.modelStack.setCurrentIndex(1)
            self.runDeeplabAnalysis()
            return

        QMessageBox.critical(
            self,
            self.TAGLAB_VERSION,
            "The selected folder is not a valid YOLO or DeepLab dataset."
        )

        self.modelStack.setCurrentIndex(0)

        if self.modelStack.currentIndex() == 2:
            self.setWindowTitle(f"{self.TAGLAB_VERSION} - YOLO dataset detected")
        elif self.modelStack.currentIndex() == 1:
            self.setWindowTitle(f"{self.TAGLAB_VERSION} - DeepLab dataset detected")

        self.yolo_class_list = None

    def resetModelState(self):

        self.safeRestoreCursor()

        # reset UI stack
        self.modelStack.setCurrentIndex(0)

        # delete yolo widget
        if self.groupbox_classes_YL is not None:
            self.groupbox_target_YOLO.layout().removeWidget(self.groupbox_classes_YL)
            self.groupbox_classes_YL.deleteLater()
            self.groupbox_classes_YL = None

        # delete DeepLab widget
        if self.groupbox_classes_DL is not None:
            self.groupbox_target_DL.layout().removeWidget(self.groupbox_classes_DL)
            self.groupbox_classes_DL.deleteLater()
            self.groupbox_classes_DL = None

        # reset data
        self.freq_classes = None
        self.target_classes = None
        self.yolo_class_list = None

        # reset checkboxes
        self.checkboxes = []
        self.checkboxes_YL = []

        # reset pipeline
        self.chkOversample.setChecked(False)
        self.chkBackground.setChecked(False)

        # reset dataset pipeline
        self.pipeline_dataset = None

        #  reset log
        self.clearLog()

        #  reset export
        self.btnExportParams.setEnabled(False)
        self.yolo_recommended_params = None

    def safeRestoreCursor(self):
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()

    def resetAll(self):

        # Folder
        self.input_folder = None
        self.output_folder = None

        self.editInputDatasetFolder.clear()
        self.editOutputDatasetFolder.clear()

        self.modelStack.setCurrentIndex(0)

        # Widgets
        if self.groupbox_classes_DL is not None:
            self.groupbox_classes_DL.setParent(None)
            self.groupbox_classes_DL.deleteLater()
            self.groupbox_classes_DL = None

        if self.groupbox_classes_YL is not None:
            self.groupbox_classes_YL.setParent(None)
            self.groupbox_classes_YL.deleteLater()
            self.groupbox_classes_YL = None

        # Data
        self.freq_classes = None
