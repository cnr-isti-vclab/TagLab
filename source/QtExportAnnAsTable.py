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

        self.mode = None

        ###########################################################



        layout = QVBoxLayout()
        label = QLabel('Which annotations do you need to export?')
        layout.addWidget(label)

        radiobtn = QRadioButton('Regions')
        radiobtn.setChecked(True)
        radiobtn.mode = "Regions"
        radiobtn.toggled.connect(self.onClicked)
        layout.addWidget(radiobtn)

        radiobtn = QRadioButton('Points')
        radiobtn.mode = "Points"
        radiobtn.toggled.connect(self.onClicked)
        layout.addWidget(radiobtn)

        radiobtn = QRadioButton('Both')
        radiobtn.mode = "Both"
        radiobtn.toggled.connect(self.onClicked)
        layout.addWidget(radiobtn)


        buttons_layout = QHBoxLayout()
        btnOk = QPushButton("OK")
        btnOk.clicked.connect(self.setMode)
        btnCancel = QPushButton("Cancel")

        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(btnOk)
        buttons_layout.addWidget(btnCancel)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.setWindowTitle(".CSV Export Options")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)

    def onClicked(self):
        radiobtn = self.sender()
        if radiobtn.isChecked():
           mode = radiobtn.mode
           self.mode.emit(mode)


    def setMode(self):

        self.mode = None

        radiobtn = self.sender()
        if radiobtn.isChecked():
           self.mode = radiobtn.mode
        #    self.mode.emit(mode)
        self.closeEvent(event)


    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtExportAnnAsTable, self).closeEvent(event)

