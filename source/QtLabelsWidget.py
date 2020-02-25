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

path = Path(__file__).parent.absolute()
imdir = str(path)
imdir = imdir.replace('source', '')


class QtLabelsWidget(QWidget):

    visibilityChanged = pyqtSignal()

    def __init__(self, class_labels, parent=None):
        super(QtLabelsWidget, self).__init__(parent)

        self.labels = class_labels

        self.btnVisible = []
        self.visibility_flags = []
        self.btnClass = []
        self.lineeditClass = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.setMinimumWidth(400)
        self.setMinimumHeight(200)

        self.icon_eyeopen = QIcon(imdir+os.path.join("icons","eye.png"))
        self.icon_eyeclosed = QIcon(imdir+os.path.join("icons","cross.png"))

        labels_layout = QVBoxLayout()
        self.setLayout(labels_layout)

        CLASS_LABELS_HEIGHT = 20
        EYE_ICON_SIZE = 20

        # ADD VISIBILITY BUTTON-CLICKABLE LABEL FOR EMPTY CLASS
        btnV = QPushButton()
        btnV.setFlat(True)
        btnV.setIcon(self.icon_eyeopen)
        btnV.setIconSize(QSize(EYE_ICON_SIZE, EYE_ICON_SIZE))
        btnV.setFixedWidth(CLASS_LABELS_HEIGHT)
        btnV.setFixedHeight(CLASS_LABELS_HEIGHT)

        btnC = QPushButton("")
        btnC.setFlat(True)
        btnC.setStyleSheet("QPushButton:flat {background-color: rgba(0,0,0,0); border: 1px dashed white;}")
        btnC.setAutoFillBackground(True)
        btnC.setFixedWidth(CLASS_LABELS_HEIGHT)
        btnC.setFixedHeight(CLASS_LABELS_HEIGHT)

        lbl = QLineEdit("Empty")
        lbl.setStyleSheet("QLineEdit { border: none; color : lightgray;}")
        lbl.setFixedHeight(CLASS_LABELS_HEIGHT)
        lbl.setReadOnly(True)
        lbl.installEventFilter(self)

        self.btnVisible.append(btnV)
        self.visibility_flags.append(True)
        self.btnClass.append(btnC)
        self.lineeditClass.append(lbl)

        btnV.clicked.connect(self.toggleVisibility)
        lbl.editingFinished.connect(self.editingFinished)

        layout = QHBoxLayout()
        layout.addWidget(btnV)
        layout.addWidget(btnC)
        layout.addWidget(lbl)
        labels_layout.addLayout(layout)

        # ADD VISIBILITY BUTTON-CLICKABLE LABELS FOR ALL THE CLASSES
        for label_name in sorted(self.labels.keys()):

            btnV = QPushButton()
            btnV.setFlat(True)
            btnV.setIcon(self.icon_eyeopen)
            btnV.setIconSize(QSize(EYE_ICON_SIZE, EYE_ICON_SIZE))
            btnV.setFixedWidth(CLASS_LABELS_HEIGHT)
            btnV.setFixedHeight(CLASS_LABELS_HEIGHT)

            btnC = QPushButton("")
            btnC.setFlat(True)

            color = self.labels[label_name]
            r = color[0]
            g = color[1]
            b = color[2]
            text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"

            btnC.setStyleSheet(text)
            btnC.setAutoFillBackground(True)
            btnC.setFixedWidth(CLASS_LABELS_HEIGHT)
            btnC.setFixedHeight(CLASS_LABELS_HEIGHT)

            lbl = QLineEdit(label_name)
            lbl.setStyleSheet("QLineEdit { border: none; color : lightgray;}")
            lbl.setFixedHeight(CLASS_LABELS_HEIGHT)
            lbl.setReadOnly(True)
            lbl.installEventFilter(self)

            self.btnVisible.append(btnV)
            self.visibility_flags.append(True)
            self.btnClass.append(btnC)
            self.lineeditClass.append(lbl)

            #btnC.clicked.connect(self.editColor)
            btnV.clicked.connect(self.toggleVisibility)
            lbl.editingFinished.connect(self.editingFinished)

            layout = QHBoxLayout()
            layout.addWidget(btnV)
            layout.addWidget(btnC)
            layout.addWidget(lbl)
            labels_layout.addLayout(layout)

        labels_layout.setSpacing(2)

        ### FURTHER INITIALIZATION
        txt = self.lineeditClass[0].text()
        self.lineeditClass[0].setText(txt)
        self.lineeditClass[0].setStyleSheet("QLineEdit { border: 1px; font-weight: bold; color : white;}")

        self.active_label_name = self.lineeditClass[0].text()


    def eventFilter(self, object, event):

        if type(object) == QLineEdit and event.type() == QEvent.FocusIn :

            self.highlightSelectedLabel(object)

            return False

        if type(object) == QLineEdit and event.type() == QEvent.MouseButtonDblClick :

            self.renameSelectedLabel(object)

        return False

    def setAllVisible(self):

        for i in range(len(self.visibility_flags)):
            self.btnVisible[i].setIcon(self.icon_eyeopen)
            self.visibility_flags[i] = True

    def setAllNotVisible(self):

        for i in range(len(self.visibility_flags)):
            self.btnVisible[i].setIcon(self.icon_eyeclosed)
            self.visibility_flags[i] = False

    @pyqtSlot()
    def editingFinished(self):

        lineedit = self.sender()
        lineedit.setReadOnly(True)

    @pyqtSlot()
    def editColor(self):

        button_clicked = self.sender()

        index = self.btnClass.index(button_clicked)
        label_name = self.lblClass[index].text()

        color_dlg = QColorDialog(self)

        color = self.labels[label_name]
        r = color[0]
        g = color[1]
        b = color[2]
        current_color = QColor(r, g, b, 255)
        color_dlg.setCustomColor(0, current_color)

        selected_color = color_dlg.getColor()
        r = selected_color.red()
        g = selected_color.green()
        b = selected_color.blue()

        self.labels[label_name] = [r, g, b]

        style_text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"
        button_clicked.setStyleSheet(style_text)

    @pyqtSlot()
    def toggleVisibility(self):

        button_clicked = self.sender()

        index = self.btnVisible.index(button_clicked)

        if QApplication.keyboardModifiers() == Qt.ControlModifier:

            self.setAllNotVisible()
            button_clicked.setIcon(self.icon_eyeopen)
            self.visibility_flags[index] = True

        elif QApplication.keyboardModifiers() == Qt.ShiftModifier:

            self.setAllVisible()
            button_clicked.setIcon(self.icon_eyeclosed)
            self.visibility_flags[index] = False

        else:

            if self.visibility_flags[index]:
                button_clicked.setIcon(self.icon_eyeclosed)
                self.visibility_flags[index] = False
            else:
                button_clicked.setIcon(self.icon_eyeopen)
                self.visibility_flags[index] = True

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

        self.active_label_name = lbl_clicked.text()

    def renameSelectedLabel(self, lbl_clicked):

        # reset the text of all the clickable labels
        for lbl in self.lineeditClass:
            lbl.setText(lbl.text())
            lbl.setStyleSheet("QLineEdit { border: none; font-weight: normal; color : lightgray;}")
            lbl.setReadOnly(True)

        txt = lbl_clicked.text()
        lbl_clicked.setText(txt)
        #lbl_clicked.setReadOnly(False)
        lbl.setReadOnly(False)
        lbl_clicked.setStyleSheet("QLineEdit { border: 1 px; font-weight: bold; color : white;}")
        lbl_clicked.setFocusPolicy(Qt.StrongFocus)
        lbl_clicked.setFocus()

    def isClassVisible(self, class_name):

        for i in range(len(self.lblClass)):
            if self.lblClass[i].label_text == class_name:
                return self.visibility_flags[i]

        return False

    def getActiveLabelName(self):

        return self.active_label_name

