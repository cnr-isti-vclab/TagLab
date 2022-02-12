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
# GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

import os

from PyQt5.QtCore import Qt, QSettings, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QWidget, QColorDialog, QListWidget, QStackedWidget, QComboBox, QSizePolicy, QLineEdit, \
    QLabel, QSpinBox, QCheckBox, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog

class generalSettingsWidget(QWidget):

    researchFieldChanged = pyqtSignal(str)
    autosaveInfoChanged = pyqtSignal(int)

    def __init__(self, settings, taglab_dir, parent=None):
        super(generalSettingsWidget, self).__init__(parent)

        self.taglab_dir = taglab_dir

        self.settings = settings

        self.autosave_interval = 0  #autosave disabled

        self.checkbox_autosave = QCheckBox("Autosave")
        self.spinbox_autosave_interval = QSpinBox()
        self.spinbox_autosave_interval.setRange(5, 15)
        self.lbl_autosave_1 = QLabel("Every ")
        self.lbl_autosave_2 = QLabel(" minutes.")

        self.lbl_research_field = QLabel("Research field: ")
        self.combo_research_field = QComboBox()
        self.combo_research_field.setFixedWidth(240)
        self.combo_research_field.addItem("Marine Ecology/Biology")
        # self.combo_research_field.addItem("Architectural Heritage")
        self.combo_research_field.setCurrentIndex(0)

        self.lbl_default_dict = QLabel("Default dictionary: ")
        self.edit_default_dict = QLineEdit("dictionaries/scripps.json")
        self.btn_default_dict = QPushButton("...")
        self.btn_default_dict.setFixedWidth(20)
        self.btn_default_dict.clicked.connect(self.chooseDict)

        layout_H1 = QHBoxLayout()
        layout_H1.addWidget(self.lbl_research_field)
        layout_H1.addWidget(self.combo_research_field)
        layout_H1.addStretch()

        layout_H2 = QHBoxLayout()
        layout_H2.addWidget(self.checkbox_autosave)
        layout_H2.addWidget(self.lbl_autosave_1)
        layout_H2.addWidget(self.spinbox_autosave_interval)
        layout_H2.addWidget(self.lbl_autosave_2)
        layout_H2.addStretch()

        layout_H3 = QHBoxLayout()
        layout_H3.addWidget(self.lbl_default_dict)
        layout_H3.addWidget(self.edit_default_dict)
        layout_H3.addWidget(self.btn_default_dict)

        layout = QVBoxLayout()
        layout.addLayout(layout_H1)
        layout.addLayout(layout_H2)
        layout.addLayout(layout_H3)

        self.setLayout(layout)

        self.combo_research_field.currentTextChanged.connect(self.setResearchField)
        self.checkbox_autosave.stateChanged.connect(self.autosaveChanged)
        self.spinbox_autosave_interval.valueChanged.connect(self.autosaveIntervalChanged)

    @pyqtSlot()
    def chooseDict(self):

        filters = "JSON (*.json)"
        file_name, _ = QFileDialog.getOpenFileName(self, "Default Dictionary File", "", filters)
        if file_name:
            default_dict = os.path.relpath(file_name, start=self.taglab_dir)
            self.edit_default_dict.setText(default_dict)
            self.settings.setValue("default-dictionary", default_dict)


    @pyqtSlot(int)
    def autosaveChanged(self, status):

        if self.checkbox_autosave.isChecked() is False:
            self.lbl_autosave_1.setDisabled(True)
            self.spinbox_autosave_interval.setDisabled(True)
            self.lbl_autosave_2.setDisabled(True)

            self.settings.setValue("autosave-interval", 0)

            self.autosaveInfoChanged.emit(0)  # 0 means that the autosave should be disabled
        else:
            self.lbl_autosave_1.setEnabled(True)
            self.spinbox_autosave_interval.setEnabled(True)
            self.lbl_autosave_2.setEnabled(True)

            self.settings.setValue("autosave-interval", self.spinbox_autosave_interval.value())

            self.autosaveInfoChanged.emit(self.spinbox_autosave_interval.value())

    @pyqtSlot(int)
    def autosaveIntervalChanged(self, value):

        self.settings.setValue("autosave-interval", self.spinbox_autosave_interval.value())

        self.autosaveInfoChanged.emit(value)

    def setResearchField(self, field):

        if field == "Marine Ecology/Biology":
            self.combo_research_field.setCurrentIndex(0)
            self.settings.setValue("research-field", self.combo_research_field.currentText())
            self.researchFieldChanged.emit(self.combo_research_field.currentText())
        elif field == "Architectural Heritage":
            self.combo_research_field.setCurrentIndex(1)
            self.settings.setValue("research-field", self.combo_research_field.currentText())
            self.researchFieldChanged.emit(self.combo_research_field.currentText())

    def researchField(self):

        return self.comboResearchField.currentText()

    def setAutosaveInterval(self, interval):

        if interval == 0:
            self.checkbox_autosave.setChecked(False)
            self.lbl_autosave_1.setDisabled(True)
            self.spinbox_autosave_interval.setDisabled(True)
            self.lbl_autosave_2.setDisabled(True)
        else:
            self.checkbox_autosave.setChecked(True)
            self.lbl_autosave_1.setEnabled(True)
            self.spinbxo_autosave_interval.setEnabled(True)
            self.lbl_autosave_2.setEnabled(True)

        self.settings.setValue("autosave-interval", interval)

    def autosaveInterval(self):

        if not self.checkbox_autosave.isChecked():
            return 0
        else:
            return self.edit_autosave_interval.text().toInt()


class drawingSettingsWidget(QWidget):

    borderPenChanged = pyqtSignal(str, int)
    selectionPenChanged = pyqtSignal(str, int)
    workingAreaPenChanged = pyqtSignal(str, int)

    def __init__(self, settings, parent=None):
        super(drawingSettingsWidget, self).__init__(parent)

        self.settings = settings

        self.border_pen_color = "0-0-0"
        self.selection_pen_color = "255-255-255"
        self.workingarea_pen_color = "255-255-255"

        self.lbl_border_color = QLabel("Border color :  ")
        self.lbl_selection_color = QLabel("Selection color :  ")
        self.lbl_workingarea_color = QLabel("Working area color :  ")

        COLOR_SIZE = 40

        text = "QPushButton:flat {background-color: rgb(255,255,255); border: 1px ;}"
        self.btn_border_color = QPushButton()
        self.btn_border_color.setFlat(True)
        self.btn_border_color.setStyleSheet(text)
        self.btn_border_color.setAutoFillBackground(True)
        self.btn_border_color.setFixedWidth(COLOR_SIZE)
        self.btn_border_color.setFixedHeight(COLOR_SIZE)

        self.btn_selection_color = QPushButton()
        self.btn_selection_color.setFlat(True)
        self.btn_selection_color.setStyleSheet(text)
        self.btn_selection_color.setAutoFillBackground(True)
        self.btn_selection_color.setFixedWidth(COLOR_SIZE)
        self.btn_selection_color.setFixedHeight(COLOR_SIZE)

        self.btn_workingarea_color = QPushButton()
        self.btn_workingarea_color.setFlat(True)
        self.btn_workingarea_color.setStyleSheet(text)
        self.btn_workingarea_color.setAutoFillBackground(True)
        self.btn_workingarea_color.setFixedWidth(COLOR_SIZE)
        self.btn_workingarea_color.setFixedHeight(COLOR_SIZE)

        self.lblBorderWidth = QLabel("Border width :  ")
        self.lblSelectionWidth = QLabel("Selection width :  ")
        self.lblWorkingAreaWidth = QLabel("Working width :  ")

        self.spinbox_border_width = QSpinBox()
        self.spinbox_border_width.setFixedWidth(50)
        self.spinbox_border_width.setRange(2, 6)
        self.spinbox_border_width.setValue(3)

        self.spinbox_selection_width = QSpinBox()
        self.spinbox_selection_width.setFixedWidth(50)
        self.spinbox_selection_width.setRange(2, 6)
        self.spinbox_selection_width.setValue(3)

        self.spinbox_workingarea_width = QSpinBox()
        self.spinbox_workingarea_width.setFixedWidth(50)
        self.spinbox_workingarea_width.setRange(2, 6)
        self.spinbox_workingarea_width.setValue(3)

        layout_H1 = QHBoxLayout()
        layout_H1.addWidget(self.lbl_border_color)
        layout_H1.addWidget(self.btn_border_color)

        layout_H2 = QHBoxLayout()
        layout_H2.addWidget(self.lbl_selection_color)
        layout_H2.addWidget(self.btn_selection_color)

        layout_H3 = QHBoxLayout()
        layout_H3.addWidget(self.lbl_workingarea_color)
        layout_H3.addWidget(self.btn_workingarea_color)

        layout_H4 = QHBoxLayout()
        layout_H4.addWidget(self.lblBorderWidth)
        layout_H4.addWidget(self.spinbox_border_width)

        layout_H5 = QHBoxLayout()
        layout_H5.addWidget(self.lblSelectionWidth)
        layout_H5.addWidget(self.spinbox_selection_width)

        layout_H6 = QHBoxLayout()
        layout_H6.addWidget(self.lblWorkingAreaWidth)
        layout_H6.addWidget(self.spinbox_workingarea_width)

        layout_V1 = QVBoxLayout()
        layout_V1.addLayout(layout_H1)
        layout_V1.addLayout(layout_H2)
        layout_V1.addLayout(layout_H3)

        layout_V2 = QVBoxLayout()
        layout_V2.addLayout(layout_H4)
        layout_V2.addLayout(layout_H5)
        layout_V2.addLayout(layout_H6)

        layout_H = QHBoxLayout()
        layout_H.addLayout(layout_V1)
        layout_H.addStretch()
        layout_H.addLayout(layout_V2)

        self.setLayout(layout_H)

        # connections
        self.btn_border_color.clicked.connect(self.chooseBorderColor)
        self.spinbox_border_width.valueChanged.connect(self.borderWidthChanged)
        self.btn_selection_color.clicked.connect(self.chooseSelectionColor)
        self.spinbox_selection_width.valueChanged.connect(self.selectionWidthChanged)
        self.btn_workingarea_color.clicked.connect(self.chooseWorkingAreaColor)
        self.spinbox_workingarea_width.valueChanged.connect(self.workingAreaWidthChanged)

    @pyqtSlot()
    def chooseBorderColor(self):

        color = QColorDialog.getColor()

        # convert to string RR-GG-BB
        newcolor = "{:d}-{:d}-{:d}".format(color.red(), color.green(), color.blue())
        self.setBorderColor(newcolor)

    @pyqtSlot()
    def chooseSelectionColor(self):

        color = QColorDialog.getColor()

        # convert to string RR-GG-BB
        newcolor = "{:d}-{:d}-{:d}".format(color.red(), color.green(), color.blue())
        self.setSelectionColor(newcolor)

    @pyqtSlot()
    def chooseWorkingAreaColor(self):

        color = QColorDialog.getColor()

        # convert to string RR-GG-BB
        newcolor = "{:d}-{:d}-{:d}".format(color.red(), color.green(), color.blue())
        self.setWorkingAreaColor(newcolor)

    @pyqtSlot(int)
    def borderWidthChanged(self, value):
        self.setBorderWidth(value)

    @pyqtSlot(int)
    def selectionWidthChanged(self, value):
        self.setSelectionWidth(value)

    @pyqtSlot(int)
    def workingAreaWidthChanged(self, value):
        self.setWorkingAreaWidth(value)

    def setBorderColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + r + "," + g + "," + b + "); border: none ;}"
            self.btn_border_color.setStyleSheet(text)
            self.border_pen_color = color

            self.settings.setValue("border-pen-color", self.border_pen_color)

            border_pen_width = self.spinbox_border_width.value()
            self.borderPenChanged.emit(self.border_pen_color, border_pen_width)

    def borderColor(self):

        return self.border_pen_color

    def setBorderWidth(self, width):

        if self.spinbox_border_width.minimum() <= width <= self.spinbox_border_width.maximum():
            self.spinbox_border_width.setValue(width)
            self.settings.setValue("border-pen-width", width)

            self.borderPenChanged.emit(self.border_pen_color, width)

    def borderWidth(self):

        return self.spinbox_border_width.value()

    def setSelectionColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + r + "," + g + "," + b + "); border: none ;}"
            self.btn_selection_color.setStyleSheet(text)
            self.selection_pen_color = color

            self.settings.setValue("selection-pen-color", self.selection_pen_color)

            selection_pen_width = self.spinbox_selection_width.value()
            self.selectionPenChanged.emit(self.selection_pen_color, selection_pen_width)

    def selectionColor(self):

        return self.selection_pen_color

    def setSelectionWidth(self, width):

        if self.spinbox_selection_width.minimum() <= width <= self.spinbox_selection_width.maximum():
            self.spinbox_selection_width.setValue(width)
            self.settings.setValue("selection-pen-width", width)

            self.selectionPenChanged.emit(self.selection_pen_color, width)

    def selectionWidth(self):

        return self.spinbox_selection_width.value()

    def setWorkingAreaColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + r + "," + g + "," + b + "); border: none ;}"
            self.btn_workingarea_color.setStyleSheet(text)
            self.workingarea_pen_color = color

            self.settings.setValue("workingarea-pen-color", self.workingarea_pen_color)

            workingarea_pen_width = self.spinbox_workingarea_width.value()
            self.workingAreaPenChanged.emit(self.workingarea_pen_color, workingarea_pen_width)

    def workingAreaColor(self):

        return self.workingarea_pen_color

    def setWorkingAreaWidth(self, width):

        if self.spinbox_workingarea_width.minimum() <= width <= self.spinbox_workingarea_width.maximum():
            self.spinbox_workingarea_width.setValue(width)
            self.settings.setValue("workingarea-pen-width", width)

            self.workingAreaPenChanged.emit(self.workingarea_pen_color, width)

    def workingAreaWidth(self):

        return self.spinbox_workingarea_width.value()


class QtSettingsWidget(QWidget):

    accepted = pyqtSignal()

    def __init__(self, taglab_dir, parent=None):
        super(QtSettingsWidget, self).__init__(parent)

        self.settings = QSettings("VCLAB", "TagLab")

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        ###### LEFT PART

        self.listwidget = QListWidget()
        self.listwidget.setMaximumWidth(100)
        self.listwidget.addItem("General")
        self.listwidget.addItem("Drawing")

        ###### CENTRAL PART

        self.general_settings = generalSettingsWidget(self.settings, taglab_dir)
        self.drawing_settings = drawingSettingsWidget(self.settings)

        self.stackedwidget = QStackedWidget()
        self.stackedwidget.addWidget(self.general_settings)
        self.stackedwidget.addWidget(self.drawing_settings)

        layoutH = QHBoxLayout()
        layoutH.addWidget(self.listwidget)
        layoutH.addWidget(self.stackedwidget)

        ###########################################################

        # OK button - to simplify exit from the settings

        self.btnOk = QPushButton("Ok")
        self.btnOk.clicked.connect(self.close)

        ###########################################################

        layout_buttons = QHBoxLayout()
        layout_buttons.setAlignment(Qt.AlignRight)
        layout_buttons.addWidget(self.btnOk)

        layout = QVBoxLayout()
        layout.addLayout(layoutH)
        layout.addLayout(layout_buttons)

        self.setLayout(layout)

        # connections
        self.listwidget.currentRowChanged.connect(self.display)

        self.setWindowTitle("Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


    def loadSettings(self):

        # 0: autosave is disabled , >0: the project is saved every N seconds
        self.autosave_interval = self.settings.value("autosave", defaultValue=0, type=int)
        self.research_field = self.settings.value("research-field", defaultValue="Marine Ecology/Biology", type=str)
        self.default_dictionary = self.settings.value("default-dictionary", defaultValue="dictionaries/scripps.json", type=str)

        self.selection_pen_color = self.settings.value("selection-pen-color", defaultValue="255-255-255", type=str)
        self.selection_pen_width = self.settings.value("selection-pen-width", defaultValue=2, type=int)
        self.border_pen_color = self.settings.value("border-pen-color", defaultValue="0-0-0", type=str)
        self.border_pen_width = self.settings.value("border-pen-width", defaultValue=2, type=int)
        self.workingarea_pen_color = self.settings.value("workingarea-pen-color", defaultValue="0-255-0", type=str)
        self.workingarea_pen_width = self.settings.value("workingarea-pen-width", defaultValue=3, type=int)

        self.general_settings.setResearchField(self.research_field)
        self.general_settings.setAutosaveInterval(self.autosave_interval)

        self.drawing_settings.setBorderColor(self.border_pen_color)
        self.drawing_settings.setBorderWidth(self.border_pen_width)
        self.drawing_settings.setSelectionColor(self.selection_pen_color)
        self.drawing_settings.setSelectionWidth(self.selection_pen_width)
        self.drawing_settings.setWorkingAreaColor(self.workingarea_pen_color)
        self.drawing_settings.setWorkingAreaWidth(self.workingarea_pen_width)

    @pyqtSlot(int)
    def display(self, i):
        self.stackedwidget.setCurrentIndex(i)




