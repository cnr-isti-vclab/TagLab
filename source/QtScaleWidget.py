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



class QtScaleWidget(QWidget):

    newscale = pyqtSignal(float)
    closewidget = pyqtSignal()

    def __init__(self, parent=None):
        super(QtScaleWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        label_px = QLabel("px")
        label_px.setAlignment(Qt.AlignLeft)

        label_mm = QLabel("mm")
        label_mm.setAlignment(Qt.AlignLeft)

        label_scale = QLabel("Pixel size (mm)")
        label_scale.setAlignment(Qt.AlignLeft)

        self.edit_mm = QLineEdit()
        self.edit_mm.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_mm.setFixedWidth(100)
        self.edit_mm.textEdited.connect(self.computeScale)

        self.edit_px = QLineEdit()
        self.edit_px.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_px.setFixedWidth(100)
        self.edit_px.setReadOnly(True)

        self.edit_scale = QLineEdit()
        self.edit_scale.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_scale.setFixedWidth(100)
        self.edit_scale.textEdited.connect(self.editScale)

        layout_mm = QHBoxLayout()
        layout_mm.setAlignment(Qt.AlignLeft)
        layout_mm.addWidget(self.edit_mm)
        layout_mm.addWidget(label_mm)

        layout_px = QHBoxLayout()
        layout_px.setAlignment(Qt.AlignLeft)
        layout_px.addWidget(self.edit_px)
        layout_px.addWidget(label_px)

        layout_scale = QHBoxLayout()
        layout_scale.setAlignment(Qt.AlignLeft)
        layout_scale.addWidget(self.edit_scale)
        layout_scale.addWidget(label_scale)

        layout_first_row = QHBoxLayout()
        layout_first_row.addLayout(layout_mm)
        layout_first_row.addStretch()
        layout_first_row.addLayout(layout_px)


        label_current_scale = QLabel("Current map pixel size (mm): ")
        self.label_current_scale_value = QLabel(" ")
        layout_current_scale = QHBoxLayout()
        layout_current_scale.addWidget(label_current_scale)
        layout_current_scale.addWidget(self.label_current_scale_value)


        layout_measures = QVBoxLayout()
        layout_measures.setAlignment(Qt.AlignLeft)
        layout_measures.addLayout(layout_first_row)
        layout_measures.addLayout(layout_scale)
        layout_measures.addLayout(layout_current_scale)


        buttons_layout = QHBoxLayout()

        self.btnOk = QPushButton("Ok")
        self.btnApply = QPushButton("Set new pixel size")
        self.btnApply.clicked.connect(self.setNewScale)


        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnApply)
        buttons_layout.addWidget(self.btnOk)

        ###########################################################
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(layout_measures)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        self.setWindowTitle("Measure And Set Scale")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)


    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtScaleWidget, self).closeEvent(event)


    @pyqtSlot(float)
    def setMeasure(self, value):
        #NOTE! THE VALUE RETURNED FROM MEASURE (in ruler) IS IN CM
        conversion = (value*10) / float(self.edit_scale.text())
        self.edit_px.setText("{:.1f}".format(conversion))
        self.edit_mm.setText("{:.1f}".format(value*10))

    # def getScale(self, value):
    #    self.label_current_scale_value.setText(("{:.3f}".format(value)))

    # setScale is called from TagLab to fill in the current scale value
    def setScale(self, value):
        self.label_current_scale_value.setText(("{:.3f}".format(value)))
        self.edit_scale.setText(("{:.3f}".format(value)))

    @pyqtSlot(str)
    def computeScale(self, text):
        try:
            val = float(text)/float(self.edit_px.text())
            self.edit_scale.setText("{:.3f}".format(val))
        except:
            pass

    @pyqtSlot(str)
    def editScale(self, text):
        try:
            val = float(text)*float(self.edit_px.text())
            self.edit_mm.setText("{:.1f}".format(val)) 
        except:
            pass

    @pyqtSlot()
    def setNewScale(self):
        try:        
            new_scale = float(self.edit_scale.text())
            if new_scale > 0: # must be a positive value
                self.setScale(new_scale)
                self.newscale.emit(new_scale)
        except:
            pass



