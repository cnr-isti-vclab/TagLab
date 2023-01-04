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
    closed = pyqtSignal()

    def __init__(self, export_area, parent=None):
        super(QtExportAnnAsTable, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        TEXT_SPACE = 150
        LINEWIDTH = 300

        ###########################################################

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel('Which annotations do you need to export?', self)

        self.rb_regions = QRadioButton('Regions')
        self.rb_regions.toggled.connect(self.update)

        self.rb_points = QRadioButton('Points')
        self.rb_points.toggled.connect(self.update)

        self.rb_both = QRadioButton('Both', self)
        self.rb_both.toggled.connect(self.update)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnExport = QPushButton("Export")

        layoutbtn = QHBoxLayout()
        layoutbtn.setAlignment(Qt.AlignRight)
        layoutbtn.addStretch()
        layoutbtn.addWidget(self.btnCancel)
        layoutbtn.addWidget(self.btnExport)


        layout.addWidget(label)
        layout.addWidget(rb_regions)
        layout.addWidget(rb_points)
        layout.addWidget(rb_wind)
        layout.addLayout(layoutbtn)


        # show the window
        self.show()

    def update(self):
        # get the radio button the send the signal
        rb = self.sender()

        # check if the radio button is checked
        if rb.isChecked():
            self.result_label.setText(f'You selected {rb.text()}')