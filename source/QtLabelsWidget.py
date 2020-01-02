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
from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QSizePolicy, QLabel, QToolButton, QPushButton, QHBoxLayout, \
    QVBoxLayout
from pathlib import Path
import os

path = Path(__file__).parent.absolute()
imdir = str(path)
imdir = imdir.replace('source', '')


class ClickableLabel(QLabel):

    # signals
    clicked = pyqtSignal()

    def __init__(self, label_text, parent=None):
        super(QLabel, self).__init__(parent)

        # identify the label clicked
        self.label_text = label_text  # store the label text without decoration

    def mousePressEvent(self, event):
        self.clicked.emit()


class QtLabelsWidget(QWidget):

    visibilityChanged = pyqtSignal()

    def __init__(self, class_labels, parent=None):
        super(QtLabelsWidget, self).__init__(parent)

        self.labels = class_labels

        self.btnVisible = []
        self.visibility_flags = []
        self.btnClass = []
        self.lblClass = []

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

        lbl = ClickableLabel("Empty")
        lbl.setStyleSheet("QLabel {color : lightgray;}")
        lbl.setText("Empty")
        lbl.setFixedHeight(CLASS_LABELS_HEIGHT)

        self.btnVisible.append(btnV)
        self.visibility_flags.append(True)
        self.btnClass.append(btnC)
        self.lblClass.append(lbl)

        btnV.clicked.connect(self.toggleVisibility)
        lbl.clicked.connect(self.highlightSelectedLabel)

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

            lbl = ClickableLabel(label_name)
            lbl.setStyleSheet("QLabel {color : lightgray;}")
            lbl.setText(label_name)
            lbl.setFixedHeight(CLASS_LABELS_HEIGHT)

            self.btnVisible.append(btnV)
            self.visibility_flags.append(True)
            self.btnClass.append(btnC)
            self.lblClass.append(lbl)

            btnV.clicked.connect(self.toggleVisibility)
            lbl.clicked.connect(self.highlightSelectedLabel)

            layout = QHBoxLayout()
            layout.addWidget(btnV)
            layout.addWidget(btnC)
            layout.addWidget(lbl)
            labels_layout.addLayout(layout)

        labels_layout.setSpacing(2)

        ### FURTHER INITIALIZATION
        txt = "<b>" + self.lblClass[0].label_text + "</b>"
        self.lblClass[0].setText(txt)
        self.lblClass[0].setStyleSheet("QLabel { color : white; background : light gray}")

        self.active_label_name = self.lblClass[0].label_text

    def setAllVisible(self):

        for i in range(len(self.visibility_flags)):
            self.btnVisible[i].setIcon(self.icon_eyeopen)
            self.visibility_flags[i] = True

    def setAllNotVisible(self):

        for i in range(len(self.visibility_flags)):
            self.btnVisible[i].setIcon(self.icon_eyeclosed)
            self.visibility_flags[i] = False


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

    @pyqtSlot()
    def highlightSelectedLabel(self):

        # reset the text of all the clickable labels
        for lbl in self.lblClass:
            lbl.setText(lbl.label_text)
            lbl.setStyleSheet("QLabel { color : lightgray; }")

        lbl_clicked = self.sender()

        txt = "<b>" + lbl_clicked.label_text + "</b>"
        lbl_clicked.setText(txt)
        lbl_clicked.setStyleSheet("QLabel { color : white; background : light gray}")

        self.active_label_name = lbl_clicked.label_text

    def isClassVisible(self, class_name):

        for label_name in self.labels.keys():
            if label_name == class_name:
                return self.visibility_flags[i]

        return False

    def getActiveLabelName(self):

        return self.active_label_name

