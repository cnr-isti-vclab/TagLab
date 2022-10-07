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


from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QMessageBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout


class QtCropWidget(QWidget):

    areaChanged = pyqtSignal(int, int, int, int)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super(QtCropWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        label_Top = QLabel("Top:")
        label_Top.setFixedWidth(70)
        label_Top.setAlignment(Qt.AlignLeft)

        label_Left = QLabel("Left:")
        label_Left.setFixedWidth(70)
        label_Left.setAlignment(Qt.AlignLeft)

        label_W = QLabel("Width:")
        label_W.setFixedWidth(70)
        label_W.setAlignment(Qt.AlignLeft)

        label_H = QLabel("Height:")
        label_H.setFixedWidth(70)
        label_H.setAlignment(Qt.AlignLeft)

        self.edit_X = QLineEdit()
        self.edit_X.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_X.setFixedWidth(100)
        self.edit_X.textChanged[str].connect(self.notifyAreaChanged)

        self.edit_Y = QLineEdit()
        self.edit_Y.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_Y.setFixedWidth(100)
        self.edit_Y.textChanged[str].connect(self.notifyAreaChanged)

        self.edit_W = QLineEdit()
        self.edit_W.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_W.setFixedWidth(100)
        self.edit_W.textChanged[str].connect(self.notifyAreaChanged)

        self.edit_H = QLineEdit()
        self.edit_H.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_H.setFixedWidth(100)
        self.edit_H.textChanged[str].connect(self.notifyAreaChanged)

        layout_h1 = QHBoxLayout()
        layout_h1.addWidget(label_Top)
        layout_h1.addWidget(self.edit_Y)
        layout_h1.addWidget(label_Left)
        layout_h1.addWidget(self.edit_X)

        layout_h2 = QHBoxLayout()
        layout_h2.addWidget(label_W)
        layout_h2.addWidget(self.edit_W)
        layout_h2.addWidget(label_H)
        layout_h2.addWidget(self.edit_H)

        layout_edits = QVBoxLayout()
        layout_edits.addWidget(QLabel("Coordinates (in pixel):"))
        layout_edits.addSpacing(10)
        layout_edits.addLayout(layout_h1)
        layout_edits.addLayout(layout_h2)

        self.btnChooseArea = QPushButton()
        self.btnChooseArea.setFixedWidth(32)
        self.btnChooseArea.setFixedHeight(32)
        ChooseAreaIcon = QIcon("icons\\select_area.png")
        self.btnChooseArea.setIcon(ChooseAreaIcon)

        layout_main_horiz = QHBoxLayout()
        layout_main_horiz.setAlignment(Qt.AlignTop)
        layout_main_horiz.addLayout(layout_edits)

        # Cancel / Apply buttons
        buttons_layout = QHBoxLayout()
        self.btnCancel = QPushButton("Cancel")
        self.btnApply = QPushButton("Apply")
        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnChooseArea)
        buttons_layout.addWidget(self.btnApply)
        buttons_layout.addWidget(self.btnCancel)
        self.btnCancel.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(layout_main_horiz)
        layout.addLayout(layout_main_horiz)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self.setWindowTitle("Crop area")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)

    def closeEvent(self, event):

        self.closed.emit()
        super(QtCropWidget, self).closeEvent(event)

    @pyqtSlot(str)
    def notifyAreaChanged(self, txt):

        try:
            x = int(self.edit_X.text())
            y = int(self.edit_Y.text())
            w = int(self.edit_W.text())
            h = int(self.edit_H.text())

            self.areaChanged.emit(x, y, w, h)
        except:
            pass


    @pyqtSlot(int, int, int, int)
    def updateArea(self, x, y, w, h):

        self.edit_X.setText(str(x))
        self.edit_Y.setText(str(y))
        self.edit_W.setText(str(w))
        self.edit_H.setText(str(h))


    def getCropArea(self):

        x = 0
        y = 0
        w = 0
        h = 0

        try:
            x = int(self.edit_X.text())
            y = int(self.edit_Y.text())
            w = int(self.edit_W.text())
            h = int(self.edit_H.text())
        except:
            print("CONVERSION ERROR")

        return x, y, w, h


