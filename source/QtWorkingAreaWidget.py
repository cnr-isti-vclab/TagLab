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
        self.edit_X_m.textEdited[str].connect(self.notifyAreaChangedM)

        self.edit_Y_m = QLineEdit()
        self.edit_Y_m.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_Y_m.setFixedWidth(100)
        self.edit_Y_m.textEdited[str].connect(self.notifyAreaChangedM)

        self.edit_W_m = QLineEdit()
        self.edit_W_m.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_W_m.setFixedWidth(100)
        self.edit_W_m.textEdited[str].connect(self.notifyAreaChangedM)

        self.edit_H_m = QLineEdit()
        self.edit_H_m.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_H_m.setFixedWidth(100)
        self.edit_H_m.textEdited[str].connect(self.notifyAreaChangedM)

        # If no scale is provided, disable the editing of metric boxes
        if self.scale is None:
            self.edit_X_m.setReadOnly(True)
            self.edit_Y_m.setReadOnly(True)
            self.edit_W_m.setReadOnly(True)
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
        layout_edits_m.addWidget(QLabel("Coordinates (meters):"))
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
        self.edit_X.textEdited[str].connect(self.notifyAreaChanged)

        self.edit_Y = QLineEdit()
        self.edit_Y.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_Y.setFixedWidth(100)
        self.edit_Y.textEdited[str].connect(self.notifyAreaChanged)

        self.edit_W = QLineEdit()
        self.edit_W.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_W.setFixedWidth(100)
        self.edit_W.textEdited[str].connect(self.notifyAreaChanged)

        self.edit_H = QLineEdit()
        self.edit_H.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_H.setFixedWidth(100)
        self.edit_H.textEdited[str].connect(self.notifyAreaChanged)

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
        layout_edits.addWidget(QLabel("Coordinates (pixels):"))
        layout_edits.addLayout(layout_h1)
        layout_edits.addLayout(layout_h2)


        # add label with extent
        self.label_extent = QLabel("WA extent:")

        # Create a vertical layout for both meters and pixels
        layout_main_vert = QVBoxLayout()
        
        layout_main_vert.addLayout(layout_edits_m)
        separator1 = QLabel()
        separator1.setStyleSheet("QLabel { border-bottom: 1px solid rgb(80,80,80); padding: 1px; margin: 1px; }")
        layout_main_vert.addWidget(separator1)

        layout_main_vert.addLayout(layout_edits)
        separator2 = QLabel()
        separator2.setStyleSheet("QLabel { border-bottom: 1px solid rgb(80,80,80); padding: 1px; margin: 1px; }")
        layout_main_vert.addWidget(separator2)

        layout_main_vert.addWidget(self.label_extent)
        separator3 = QLabel()
        separator3.setStyleSheet("QLabel { border-bottom: 1px solid rgb(80,80,80); padding: 1px; margin: 1px; }")
        layout_main_vert.addWidget(separator3)


        # choose / Cancel / Apply buttons
        buttons_layout = QHBoxLayout()
        self.btnChooseArea = QPushButton()
        self.btnChooseArea.setFixedWidth(32)
        self.btnChooseArea.setFixedHeight(32)
        ChooseAreaIcon = QIcon("icons\\select_area.png")
        self.btnChooseArea.setIcon(ChooseAreaIcon)
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

    def updateAreaValues(self, x, y, w, h):
        """
        Update the metric read-only boxes as the pixel boxes are updated
        """
        # Update pixel values
        self.edit_X.setText(str(x))
        self.edit_Y.setText(str(y))
        self.edit_W.setText(str(w))
        self.edit_H.setText(str(h))

        # Update metric values
        if self.scale is not None:
            # Get the scale factor (meters per pixel)
            scale_factor_m_per_px = self.scale / 1000.0
            # Update metric version values using the scale factor
            self.edit_X_m.setText(str(round(x * scale_factor_m_per_px, 3)))
            self.edit_Y_m.setText(str(round(y * scale_factor_m_per_px, 3)))
            self.edit_W_m.setText(str(round(w * scale_factor_m_per_px, 3)))
            self.edit_H_m.setText(str(round(h * scale_factor_m_per_px, 3)))
        else:
            self.edit_Y_m.setText("")
            self.edit_X_m.setText("")
            self.edit_W_m.setText("")
            self.edit_H_m.setText("")

        extent_text = f"WA extent: {round(w * h, 0)} (pix^2)   {round((w * scale_factor_m_per_px) * (h * scale_factor_m_per_px), 3)} (m^2)"
        self.label_extent.setText(extent_text)

    @pyqtSlot(str)
    def notifyAreaChanged(self, txt):
        """
        manual change of the working area in pixels
        """
        try:
            x = int(self.edit_X.text())
            y = int(self.edit_Y.text())
            w = int(self.edit_W.text())
            h = int(self.edit_H.text())

            self.areaChanged.emit(x, y, w, h)
            self.updateAreaValues(x, y, w, h)
        except:
            pass

    @pyqtSlot(str)
    def notifyAreaChangedM(self, txt):
        """
        manual change of the working area in meters
        """
        try:
            # Get the scale factor (meters per pixel)
            scale_factor_m_per_px = self.scale / 1000.0
            # Convert metric values to pixels using the scale factor
            x = int(float(self.edit_X_m.text()) / scale_factor_m_per_px)
            y = int(float(self.edit_Y_m.text()) / scale_factor_m_per_px)
            w = int(float(self.edit_W_m.text()) / scale_factor_m_per_px)
            h = int(float(self.edit_H_m.text()) / scale_factor_m_per_px)

            self.areaChanged.emit(x, y, w, h)
            self.updateAreaValues(x, y, w, h)
        except:
            pass

    @pyqtSlot(int, int, int, int)
    def updateArea(self, x, y, w, h):
        """
        area has been updated: update the values
        """    
        self.updateAreaValues(x, y, w, h)

    def deleteWorkingAreaValues(self):
        """
        area has been deleted, clear all the working area values
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