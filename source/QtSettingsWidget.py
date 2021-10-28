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
    QLabel, QCheckBox, QPushButton, QHBoxLayout, QVBoxLayout
from source import utils
from source.Grid import Grid

class generalSettingsWidget(QWidget):

    def __init__(self, parent=None):
        super(generalSettingsWidget, self).__init__(parent)

        self.autosave_interval = 0  #autosave disabled

        self.checkbox_autosave = QCheckBox("Autosave")
        self.edit_autosave_interval = QLineEdit("300")
        self.lbl_autosave_1 = QLabel("Every ")
        self.lbl_autosave_2 = QLabel(" seconds.")

        self.lbl_research_field = QLabel("Research field :  ")
        self.combo_research_field = QComboBox()
        self.combo_research_field.setFixedWidth(200)
        self.combo_research_field.addItem("Marine Ecology/Biology")
        self.combo_research_field.addItem("Architectural Heritage")
        self.combo_research_field.setCurrentIndex(0)

        layout_H1 = QHBoxLayout()
        layout_H1.addWidget(self.lbl_research_field)
        layout_H1.addWidget(self.combo_research_field)
        layout_H1.addStretch()

        layout_H2 = QHBoxLayout()
        layout_H2.addWidget(self.checkbox_autosave)
        layout_H2.addWidget(self.lbl_autosave_1)
        layout_H2.addWidget(self.edit_autosave_interval)
        layout_H2.addWidget(self.lbl_autosave_2)
        layout_H2.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(layout_H1)
        layout.addLayout(layout_H2)

        self.setLayout(layout)

        self.checkbox_autosave.stateChanged.connect(self.autosaveChanged)

    @pyqtSlot(int)
    def autosaveChanged(self, status):

        if self.checkbox_autosave.isChecked() is False:
            self.lbl_autosave_1.setDisabled(True)
            self.edit_autosave_interval.setDisabled(True)
            self.lbl_autosave_2.setDisabled(True)
        else:
            self.lbl_autosave_1.setEnabled(True)
            self.edit_autosave_interval.setEnabled(True)
            self.lbl_autosave_2.setEnabled(True)

    def setResearchField(self, field):

        if field == "Marine Ecology/Biology":
            self.combo_research_field.setCurrentIndex(0)
        elif field == "Architectural Heritage":
            self.combo_research_field.setCurrentIndex(1)

    def researchField(self):

        return self.comboResearchField.currentText()

    def setAutosaveInterval(self, interval):

        if interval == 0:
            self.checkbox_autosave.setChecked(False)
            self.lbl_autosave_1.setDisabled(True)
            self.edit_autosave_interval.setDisabled(True)
            self.lbl_autosave_2.setDisabled(True)
        else:
            self.checkbox_autosave.setChecked(True)
            self.lbl_autosave_1.setEnabled(True)
            self.edit_autosave_interval.setEnabled(True)
            self.lbl_autosave_2.setEnabled(True)

    def autosaveInterval(self):

        if not self.checkbox_autosave.isChecked():
            return 0
        else:
            return self.edit_autosave_interval.text().toInt()


class drawingSettingsWidget(QWidget):

    def __init__(self, parent=None):
        super(drawingSettingsWidget, self).__init__(parent)

        self.border_pen_color = "255-255-255"
        self.selection_pen_color = "255-255-255"

        self.lbl_border_color = QLabel("Border color :  ")
        self.lbl_selection_color = QLabel("Selection color :  ")

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

        self.lblBorderWidth = QLabel("Border width :  ")
        self.lblSelectionWidth = QLabel("Selection Width :  ")

        self.lineedit_border_width = QLineEdit("3")
        self.lineedit_border_width.setFixedWidth(50)
        self.lineedit_border_width.setValidator(QIntValidator())

        self.lineedit_selection_width = QLineEdit("3")
        self.lineedit_selection_width.setFixedWidth(50)
        self.lineedit_selection_width.setValidator(QIntValidator())

        layout_H1 = QHBoxLayout()
        layout_H1.addWidget(self.lbl_border_color)
        layout_H1.addWidget(self.btn_border_color)

        layout_H2 = QHBoxLayout()
        layout_H2.addWidget(self.lbl_selection_color)
        layout_H2.addWidget(self.btn_selection_color)

        layout_H3 = QHBoxLayout()
        layout_H3.addWidget(self.lblBorderWidth)
        layout_H3.addWidget(self.lineedit_border_width)

        layout_H4 = QHBoxLayout()
        layout_H4.addWidget(self.lblSelectionWidth)
        layout_H4.addWidget(self.lineedit_selection_width)

        layout_V1 = QVBoxLayout()
        layout_V1.addLayout(layout_H1)
        layout_V1.addLayout(layout_H2)

        layout_V2 = QVBoxLayout()
        layout_V2.addLayout(layout_H3)
        layout_V2.addLayout(layout_H4)

        layout_H = QHBoxLayout()
        layout_H.addLayout(layout_V1)
        layout_H.addStretch()
        layout_H.addLayout(layout_V2)

        self.setLayout(layout_H)

        # connections
        self.btn_border_color.clicked.connect(self.chooseBorderColor)
        self.btn_selection_color.clicked.connect(self.chooseSelectionColor)

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

    def setBorderColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"
            self.btn_border_color.setStyleSheet(text)
            self.border_pen_color = color

    def borderColor(self):

        return self.border_pen_color

    def setBorderWidth(self, width):

        self.lineedit_border_width.setText(str(width))

    def borderWidth(self):

        if self.lineedit_border_width.hasAcceptableInput() is True:
            return self.lineedit_border_width.text().toInt()
        else:
            return -1  # invalid

    def setSelectionColor(self, color):

        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"
            self.btn_selection_color.setStyleSheet(text)
            self.selection_pen_color = color

    def selectionColor(self):

        return self.selection_pen_color

    def setSelectionWidth(self, width):

        self.lineedit_selection_width.setText(str(width))

    def selectionWidth(self):

        if self.lineedit_selection_width.hasAcceptableInput() is True:
            return self.lineedit_selection_width.text().toInt()
        else:
            return -1  # invalid

class QtSettingsWidget(QWidget):

    accepted = pyqtSignal()

    def __init__(self, parent=None):
        super(QtSettingsWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        ###### LEFT PART

        self.listwidget = QListWidget()
        self.listwidget.addItem("General")
        self.listwidget.addItem("Drawing")

        ###### CENTRAL PART

        self.generalSettings = generalSettingsWidget()
        self.drawingSettings = drawingSettingsWidget()

        self.stackedwidget = QStackedWidget()
        self.stackedwidget.addWidget(self.generalSettings)
        self.stackedwidget.addWidget(self.drawingSettings)

        layoutH = QHBoxLayout()
        layoutH.addWidget(self.listwidget)
        layoutH.addWidget(self.stackedwidget)

        ###### CANCEL/APPLY

        #self.btnCancel = QPushButton("Cancel")
        #self.btnApply = QPushButton("Apply")

        #layout_buttons = QHBoxLayout()
        #layout_buttons.setAlignment(Qt.AlignRight)
        #layout_buttons.addStretch()
        #layout_buttons.addWidget(self.btnCancel)
        #layout_buttons.addWidget(self.btnApply)

        #self.btnCancel.clicked.connect(self.close)
        #self.btnApply.clicked.connect(self.apply)

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

        self.settings_widget = QtSettingsWidget()

        settings = QSettings("VCLAB", "TagLab")

        # 0: autosave is disabled , >0: the project is saved every N seconds
        self.autosave_interval = settings.value("autosave", type=int)
        self.research_field = settings.value("research-field", type=str)

        self.selection_pen_color = settings.value("selection-pen-color", type=str)
        self.selection_pen_width = settings.value("selection-pen-width", type=int)
        self.border_pen_color = settings.value("border-pen-color", type=str)
        self.border_pen_width = settings.value("border-pen-width", type=int)

        self.generalSettings.setResearchField(self.research_field)
        self.generalSettings.setAutosaveInterval(self.autosave_interval)

        self.drawingSettings.setBorderColor(self.border_pen_color)
        self.drawingSettings.setBorderWidth(self.border_pen_width)
        self.drawingSettings.setSelectionColor(self.selection_pen_color)
        self.drawingSettings.setSelectionWidth(self.selection_pen_width)

    @pyqtSlot(int)
    def display(self, i):
        self.stackedwidget.setCurrentIndex(i)

    @pyqtSlot()
    def apply(self):

        # SAVE SETTINGS
        settings = QSettings("VCLAB", "TagLab")

        # GENERAL settings
        self.research_field = self.generalSettings.researchField()
        self.autosave_interval = self.generalSettings.autosaveInterval()
        settings.setValue("research_field", self.research_field)
        settings.setValue("autosave_interval", self.autosave_interval)

        # DRAWING settings
        self.border_pen_color = self.borderPenColor()
        self.border_pen_width = self.borderPenWidth()
        self.selection_pen_color = self.selectionPenColor()
        self.selection_pen_width = self.selectionPenWidth()

        settings.setValue("border_pen_color", self.border_pen_color)

        if self.border_pen_width > 0:
            settings.setValue("border_pen_width", self.border_pen_width)

        settings.setValue("selection_pen_color", self.selection_pen_color)

        if self.selection_pen_width > 0:
            settings.setValue("selection_pen_width", self.selection_pen_width)

        self.close()


