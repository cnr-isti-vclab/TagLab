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
from PyQt5.QtCore import Qt, QSize, QEvent, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QApplication, QLineEdit, QWidget, QColorDialog, QSizePolicy, QLabel, QToolButton, QPushButton, QHBoxLayout, \
    QVBoxLayout
from pathlib import Path
import os
from source.Project import Project
from source.Label import Label

path = Path(__file__).parent.absolute()
imdir = str(path)
imdir = imdir.replace('source', '')


class QtLabelsWidget(QWidget):

    # custom signals
    visibilityChanged = pyqtSignal()
    activeLabelChanged = pyqtSignal(str)
    doubleClickLabel = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QtLabelsWidget, self).__init__(parent)

        # labels information are set according to the current project
        self.labels = None

        self.btnVisible = []
        #self.visibility_flags = []
        self.btnClass = []
        self.lineeditClass = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.setMinimumWidth(400)
        self.setMinimumHeight(100)

        self.icon_eyeopen = QIcon(imdir+os.path.join("icons", "eye.png"))
        self.icon_eyeclosed = QIcon(imdir+os.path.join("icons", "cross.png"))

        self.CLASS_LABELS_HEIGHT = 20
        self.EYE_ICON_SIZE = 20

        self.labels_layout = QVBoxLayout()
        self.labels_layout.setSpacing(2)

        self.setLayout(self.labels_layout)


    def addLabel(self, key, name):

        btnV = QPushButton()
        btnV.setProperty('key', key)
        btnV.setFlat(True)
        btnV.setIcon(self.icon_eyeopen)
        btnV.setIconSize(QSize(self.EYE_ICON_SIZE, self.EYE_ICON_SIZE))
        btnV.setFixedWidth(self.CLASS_LABELS_HEIGHT)
        btnV.setFixedHeight(self.CLASS_LABELS_HEIGHT)

        btnC = QPushButton("")
        btnV.setProperty('key', key)
        btnC.setFlat(True)

        color = self.labels[key].fill
        r = color[0]
        g = color[1]
        b = color[2]
        text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"

        btnC.setStyleSheet(text)
        btnC.setAutoFillBackground(True)
        btnC.setFixedWidth(self.CLASS_LABELS_HEIGHT)
        btnC.setFixedHeight(self.CLASS_LABELS_HEIGHT)

        lbl = QLineEdit(name)
        lbl.setProperty('key', key)
        lbl.setStyleSheet("QLineEdit { border: none; color : lightgray;}")
        lbl.setFixedHeight(self.CLASS_LABELS_HEIGHT)
        lbl.setReadOnly(True)
        lbl.installEventFilter(self)

        self.btnVisible.append(btnV)
        #self.visibility_flags.append(True)
        self.btnClass.append(btnC)
        self.lineeditClass.append(lbl)

        btnV.clicked.connect(self.toggleVisibility)
        lbl.editingFinished.connect(self.editingFinished)

        layout = QHBoxLayout()
        layout.addWidget(btnV)
        layout.addWidget(btnC)
        layout.addWidget(lbl)

        self.labels_layout.addLayout(layout)

    def setLabels(self, project):
        """
        Labels are set according to the current project.
        """

        self.labels = project.labels

        self.btnVisible = []
        #self.visibility_flags = []
        self.btnClass = []
        self.lineeditClass = []

        self.labels_layout = QVBoxLayout()
        self.labels_layout.setSpacing(2)

        # ADD VISIBILITY BUTTON-CLICKABLE LABELS FOR ALL THE CLASSES
        #for label_name in sorted(self.labels.keys()):

        for key in self.labels.keys():
            label = self.labels[key]
            self.addLabel(key, label.name)

        # to replace a layout with another one you MUST reparent it..
        tempwidget = QWidget()
        tempwidget.setLayout(self.layout())
        self.setLayout(self.labels_layout)

        ### SET ACTIVE LABEL
        txt = self.lineeditClass[0].text()
        self.lineeditClass[0].setText(txt)
        self.lineeditClass[0].setStyleSheet("QLineEdit { border: 1px; font-weight: bold; color : white;}")
        self.active_label_name = self.lineeditClass[0].text()

    def eventFilter(self, object, event):

        if type(object) == QLineEdit and event.type() == QEvent.FocusIn :

            self.highlightSelectedLabel(object)

            return False

        if type(object) == QLineEdit and event.type() == QEvent.MouseButtonDblClick :

            label_name = object.text()
            self.doubleClickLabel.emit(label_name)

        return False


    def setAllVisible(self):
        for label in self.labels.values():
            label.visible = True
        for btn in self.btnVisible:
            btn.setIcon(self.icon_eyeopen)

    def setAllNotVisible(self):
        for label in self.labels.values():
            label.visible = False
        for btn in self.btnVisible:
            btn.setIcon(self.icon_eyeclosed)

    @pyqtSlot()
    def editingFinished(self):

        lineedit = self.sender()
        lineedit.setReadOnly(True)

    @pyqtSlot()
    def toggleVisibility(self):

        button_clicked = self.sender()
        key = button_clicked.property('key')
        label = self.labels[key]

        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.setAllNotVisible()
            label.visible = True

        elif QApplication.keyboardModifiers() == Qt.ShiftModifier:
            self.setAllVisible()
            label.visible = False
        else:
            label.visible = not label.visible

        button_clicked.setIcon(self.icon_eyeopen if label.visible is True else self.icon_eyeclosed)

        self.visibilityChanged.emit()

    def highlightSelectedLabel(self, lbl_clicked):

        # reset the text of all the clickable labels
        for lbl in self.lineeditClass:
            lbl.setText(lbl.text())
            lbl.setStyleSheet("QLineEdit { border: none; font-weight: normal; color : lightgray;}")
            lbl.setReadOnly(True)

        txt = lbl_clicked.text()
        lbl_clicked.setText(txt)
        lbl_clicked.setReadOnly(True)
        lbl_clicked.setStyleSheet("QLineEdit { border: 1 px; font-weight: bold; color : white;}")

        self.active_label_name = lbl_clicked.property('key')
        self.activeLabelChanged.emit(self.active_label_name)

    def isClassVisible(self, key):

        return self.labels[key].visible
        #for i in range(len(self.lineeditClass)):
        #    if self.lineeditClass[i].text() == class_name:
        #        return self.visibility_flags[i]

        #return False

    def getActiveLabelName(self):

        return self.active_label_name

