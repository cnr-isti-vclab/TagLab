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
from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout


class QtWorkingAreaWidget(QWidget):

    def __init__(self, parent=None):
        super(QtWorkingAreaWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        label_X = QLabel("X:")
        label_X.setAlignment(Qt.AlignLeft)

        label_Y = QLabel("Y:")
        label_Y.setAlignment(Qt.AlignLeft)

        label_W = QLabel("Width:")
        label_W.setAlignment(Qt.AlignLeft)

        label_H = QLabel("Width:")
        label_H.setAlignment(Qt.AlignLeft)

        self.edit_X = QLineEdit()
        self.edit_X.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_X.setFixedWidth(100)
        self.edit_X.textChanged.connect(self.updateArea)

        self.edit_Y = QLineEdit()
        self.edit_Y.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_Y.setFixedWidth(100)
        self.edit_Y.textChanged.connect(self.updateArea)

        self.edit_W = QLineEdit()
        self.edit_W.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_W.setFixedWidth(100)
        self.edit_W.textChanged.connect(self.updateArea)

        self.edit_H = QLineEdit()
        self.edit_H.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_H.setFixedWidth(100)
        self.edit_H.textChanged.connect(self.updateArea)

        layout_h1 = QHBoxLayout()
        layout_h1.addWidget(self.label_X)
        layout_h1.addWidget(self.edit_X)
        layout_h1.addWidget(self.label_Y)
        layout_h1.addWidget(self.edit_Y)

        layout_h2 = QHBoxLayout()
        layout_h2.addWidget(self.label_X)
        layout_h2.addWidget(self.edit_X)
        layout_h2.addWidget(self.label_Y)
        layout_h2.addWidget(self.edit_Y)

        layout_v = QVBoxLayout()
        layout_v.addLayout(layout_h1)
        layout_v.addLayout(layout_h2)

        self.btnSetArea = QPushButton()
        self.btnSetArea.setIcon(QIcon("icons\\select_area.png"))


        # Cancel / Apply buttons
        buttons_layout = QHBoxLayout()
        self.btnCancel = QPushButton("Cancel")
        self.btnApply = QPushButton("Apply")
        self.btnApply.clicked.connect(self.setWorkingArea)
        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnCancel)
        buttons_layout.addWidget(self.btnApply)

        self.btnCancel.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(area_layout)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self.setWindowTitle("Working area")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)

    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtScaleWidget, self).closeEvent(event)

    @pyqtSlot()
    def updateArea(self):
        pass


