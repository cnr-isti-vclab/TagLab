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

from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QCheckBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout,  QRadioButton, QLayout


class QtExportAnnAsTable(QWidget):

    closewidget = pyqtSignal()
    mode = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QtExportAnnAsTable, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        TEXT_SPACE = 150
        LINEWIDTH = 300

        ###########################################################

        layout = QVBoxLayout()
        label = QLabel('Which annotations do you need to export?')
        layout.addWidget(label)

        self.radiobtnR = QRadioButton('Regions')
        self.radiobtnR.setChecked(True)
        self.radiobtnR.mode = "Regions"
        # self.radiobtn.toggled.connect(self.onClicked)
        layout.addWidget(self.radiobtnR)

        self.radiobtnP = QRadioButton('Points')
        self.radiobtnP.mode = "Points"
        # self.radiobtn.toggled.connect(self.onClicked)
        layout.addWidget(self.radiobtnP)

        self.radiobtnB = QRadioButton('Both')
        self.radiobtnB.mode = "Both"
        # self.radiobtn.toggled.connect(self.onClicked)
        layout.addWidget(self.radiobtnB)


        buttons_layout = QHBoxLayout()
        self.btnOk = QPushButton("OK")
        self.btnOk.clicked.connect(self.setMode)
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)

        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnOk)
        buttons_layout.addWidget(self.btnCancel)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.setWindowTitle(".CSV Export Options")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)


    def setMode(self):

        if self.radiobtnR.isChecked():
           mode = self.radiobtnR.mode
           self.mode.emit(mode)

        elif self.radiobtnP.isChecked():
           mode = self.radiobtnP.mode
           self.mode.emit(mode)

        else:
            mode = self.radiobtnB.mode
            self.mode.emit(mode)

        self.close()

    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtExportAnnAsTable, self).closeEvent(event)

