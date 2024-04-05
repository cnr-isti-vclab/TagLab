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


class QtWorkingAreaWidget(QWidget):

    areaChanged = pyqtSignal(int, int, int, int)
    closed = pyqtSignal()

    def __init__(self, parent=None, scale=None):
        super(QtWorkingAreaWidget, self).__init__(parent)

        # Scaling of active image
        self.scale = scale

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        # Create widgets for meters
        label_Top_m = QLabel("Top:")
        label_Top_m.setFixedWidth(70)
        label_Top_m.setAlignment(Qt.AlignLeft)

        label_Left_m = QLabel("Left:")
        label_Left_m.setFixedWidth(70)
        label_Left_m.setAlignment(Qt.AlignLeft)

        label_W_m = QLabel("Width:")
        label_W_m.setFixedWidth(70)
        label_W_m.setAlignment(Qt.AlignLeft)

        label_H_m = QLabel("Height:")
        label_H_m.setFixedWidth(70)
        label_H_m.setAlignment(Qt.AlignLeft)

        self.edit_X_m = QLineEdit()
        self.edit_X_m.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_X_m.setFixedWidth(100)
        self.edit_X_m.setReadOnly(True)

        self.edit_Y_m = QLineEdit()
        self.edit_Y_m.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_Y_m.setFixedWidth(100)
        self.edit_Y_m.setReadOnly(True)

        self.edit_W_m = QLineEdit()
        self.edit_W_m.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_W_m.setFixedWidth(100)
        self.edit_W_m.setReadOnly(True)

        self.edit_H_m = QLineEdit()
        self.edit_H_m.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_H_m.setFixedWidth(100)
        self.edit_H_m.setReadOnly(True)

        # Create layout for meters
        layout_h1_m = QHBoxLayout()
        layout_h1_m.addWidget(label_Top_m)
        layout_h1_m.addWidget(self.edit_Y_m)
        layout_h1_m.addWidget(label_Left_m)
        layout_h1_m.addWidget(self.edit_X_m)

        layout_h2_m = QHBoxLayout()
        layout_h2_m.addWidget(label_W_m)
        layout_h2_m.addWidget(self.edit_W_m)
        layout_h2_m.addWidget(label_H_m)
        layout_h2_m.addWidget(self.edit_H_m)

        layout_edits_m = QVBoxLayout()
        layout_edits_m.addWidget(QLabel("Coordinates (in meters):"))
        layout_edits_m.addSpacing(10)
        layout_edits_m.addLayout(layout_h1_m)
        layout_edits_m.addLayout(layout_h2_m)

        # Create widgets for pixels
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

        # Create layout for pixels
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
        layout_edits.addWidget(QLabel("Coordinates (in pixels):"))
        layout_edits.addSpacing(10)
        layout_edits.addLayout(layout_h1)
        layout_edits.addLayout(layout_h2)

        # Create a vertical layout for both meters and pixels
        layout_main_vert = QVBoxLayout()
        layout_main_vert.addLayout(layout_edits_m)
        layout_main_vert.addLayout(layout_edits)

        self.btnChooseArea = QPushButton()
        self.btnChooseArea.setFixedWidth(32)
        self.btnChooseArea.setFixedHeight(32)
        ChooseAreaIcon = QIcon("icons\\select_area.png")
        self.btnChooseArea.setIcon(ChooseAreaIcon)

        # Cancel / Apply buttons
        buttons_layout = QHBoxLayout()
        self.btnDelete = QPushButton("Delete")
        self.btnCancel = QPushButton("Cancel")
        self.btnApply = QPushButton("Set")
        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnChooseArea)
        buttons_layout.addWidget(self.btnApply)
        buttons_layout.addWidget(self.btnDelete)
        buttons_layout.addWidget(self.btnCancel)
        self.btnCancel.clicked.connect(self.close)

        # Create a final vertical layout for the entire widget
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft)
        layout.addLayout(layout_main_vert)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self.setWindowTitle("Working Area")
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowCloseButtonHint |
                            Qt.WindowTitleHint |
                            Qt.WindowStaysOnTopHint)

    def closeEvent(self, event):

        self.closed.emit()
        super(QtWorkingAreaWidget, self).closeEvent(event)

    def updateMetricValues(self):
        """
        Update the metric read-only boxes as the pixel boxes are updated
        """

        if self.scale is not None:
            # Get pixel values
            pixel_top = int(self.edit_Y.text())
            pixel_left = int(self.edit_X.text())
            pixel_width = int(self.edit_W.text())
            pixel_height = int(self.edit_H.text())

            # Get the scale factor (millimeters per pixel)
            scale_factor_mm_per_px = self.scale * 0.1

            # Convert pixel values to meters using the scale factor
            meter_top = round(pixel_top * scale_factor_mm_per_px / 1000.0, 3)
            meter_left = round(pixel_left * scale_factor_mm_per_px / 1000.0, 3)
            meter_width = round(pixel_width * scale_factor_mm_per_px / 1000.0, 3)
            meter_height = round(pixel_height * scale_factor_mm_per_px / 1000.0, 3)

            # Update metric version values
            self.edit_Y_m.setText(str(meter_top))
            self.edit_X_m.setText(str(meter_left))
            self.edit_W_m.setText(str(meter_width))
            self.edit_H_m.setText(str(meter_height))

    @pyqtSlot(str)
    def notifyAreaChanged(self, txt):
        """

        """
        try:
            x = int(self.edit_X.text())
            y = int(self.edit_Y.text())
            w = int(self.edit_W.text())
            h = int(self.edit_H.text())

            self.areaChanged.emit(x, y, w, h)
            self.updateMetricValues()
        except:
            pass

    @pyqtSlot(int, int, int, int)
    def updateArea(self, x, y, w, h):
        """

        """
        self.edit_X.setText(str(x))
        self.edit_Y.setText(str(y))
        self.edit_W.setText(str(w))
        self.edit_H.setText(str(h))

    def deleteWorkingAreaValues(self):
        """

        """
        self.edit_X.setText("")
        self.edit_Y.setText("")
        self.edit_W.setText("")
        self.edit_H.setText("")

        self.edit_X_m.setText("")
        self.edit_Y_m.setText("")
        self.edit_W_m.setText("")
        self.edit_H_m.setText("")

    def getWorkingArea(self):
        """

        """
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