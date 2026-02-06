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
from PyQt5.QtWidgets import QWidget, QGroupBox, QComboBox, QRadioButton, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout, QGridLayout, QMessageBox
from osgeo import osr
import rasterio as rio

class QtGeoreferencingWidget(QWidget):

    pointsToPickChanged = pyqtSignal(int)
    validchoices = pyqtSignal()
    closewidget = pyqtSignal()

    def __init__(self, project, parent=None):
        super(QtGeoreferencingWidget, self).__init__(parent)

        main_layout = QVBoxLayout()

        self.project = project

        # global style
        self.setStyleSheet(":enabled {background-color: rgb(40,40,40); color: white} :disabled {color: rgb(110,110,110)}")

        # line edit style
        self.lineedit_style = ":enabled {background-color: rgb(55,55,55); color: rgb(255,255,255); border: 1px solid rgb(90,90,90)} " \
                              ":disabled {background-color: rgb(35,35,35); color: rgb(110,110,110); border: 1px solid rgb(70,70,70)}"

        # --- 1. Top Radio Buttons (No GroupBox for this) ---
        self.radio_layout = QHBoxLayout()
        self.radio_layout.setSpacing(20)

        self.radio_maps = QRadioButton("Get from maps")
        self.radio_one_gcp = QRadioButton("Indicate one point")
        self.radio_two_gcp = QRadioButton("Indicate two points")
        self.radio_choose = QRadioButton("Choose a location")
        self.radio_maps.setChecked(True)

        self.radio_layout.addWidget(self.radio_maps)
        self.radio_layout.addWidget(self.radio_one_gcp)
        self.radio_layout.addWidget(self.radio_two_gcp)
        self.radio_layout.addWidget(self.radio_choose)
        main_layout.addLayout(self.radio_layout)

        # --- 2. GroupBox: Transfer from map Section ---
        self.map_group = QGroupBox("Transfer from map")
        map_layout = QHBoxLayout(self.map_group)

        self.lbl_map_to_use = QLabel("Map to use:")
        map_layout.addWidget(self.lbl_map_to_use)
        self.combobox_map_input = QComboBox()
        self.combobox_map_input.setFixedWidth(200)
        map_layout.addWidget(self.combobox_map_input)

        map_layout.addStretch()
        map_layout.addWidget(QLabel("CRS:"))

        self.lbl_crs_info = QLabel("CRS information are reported here\nCRS information are reported here")
        map_layout.addWidget(self.lbl_crs_info)
        map_layout.addStretch()
        main_layout.addWidget(self.map_group)

        # --- 3. GroupBox: Indicate known points Section ---
        self.coord_group = QGroupBox("Indicate known points")
        coord_grid = QGridLayout(self.coord_group)
        coord_grid.setContentsMargins(15, 15, 15, 15)
        coord_grid.setSpacing(10)


        area_icon = QIcon("icons\\select_area.png")
        self.btn_pick_point_1 = QPushButton("")
        self.btn_pick_point_1.setIcon(area_icon)
        self.btn_pick_point_1.setMinimumWidth(30)
        self.btn_pick_point_2 = QPushButton("")
        self.btn_pick_point_2.setIcon(area_icon)
        self.btn_pick_point_2.setMinimumWidth(30)

        # Row 1
        coord_grid.addWidget(self.btn_pick_point_1, 0, 0)
        self.lbl_WGS84_1 = QLabel("WGS 84 (Lat/Long): ")
        self.edit_coord_pixel_x_1 = QLineEdit()
        self.edit_coord_pixel_x_1.setPlaceholderText("x coord.")
        self.edit_coord_pixel_x_1.setStyleSheet(self.lineedit_style)
        self.edit_coord_pixel_y_1 = QLineEdit()
        self.edit_coord_pixel_y_1.setPlaceholderText("y coord.")
        self.edit_coord_pixel_y_1.setStyleSheet(self.lineedit_style)
        coord_grid.addWidget(self.edit_coord_pixel_x_1, 0, 1)
        coord_grid.addWidget(self.edit_coord_pixel_y_1, 0, 2)
        coord_grid.addWidget(self.lbl_WGS84_1, 0, 3)
        self.edit_coord_wgs84_lat_1 = QLineEdit()
        self.edit_coord_wgs84_lat_1.setPlaceholderText("latitude")
        self.edit_coord_wgs84_lat_1.setStyleSheet(self.lineedit_style)
        self.edit_coord_wgs84_lon_1 = QLineEdit()
        self.edit_coord_wgs84_lon_1.setPlaceholderText("longitude")
        self.edit_coord_wgs84_lon_1.setStyleSheet(self.lineedit_style)
        coord_grid.addWidget(self.edit_coord_wgs84_lat_1, 0, 4)
        coord_grid.addWidget(self.edit_coord_wgs84_lon_1, 0, 5)

        # Row 2
        coord_grid.addWidget(self.btn_pick_point_2, 1, 0)
        self.lbl_WGS84_2 = QLabel("WGS 84 (Lat/Long):")
        self.edit_coord_pixel_x_2 = QLineEdit()
        self.edit_coord_pixel_x_2.setPlaceholderText("x coord.")
        self.edit_coord_pixel_x_2.setStyleSheet(self.lineedit_style)
        self.edit_coord_pixel_y_2 = QLineEdit()
        self.edit_coord_pixel_y_2.setPlaceholderText("y coord.")
        self.edit_coord_pixel_y_2.setStyleSheet(self.lineedit_style)
        coord_grid.addWidget(self.edit_coord_pixel_x_2, 1, 1)
        coord_grid.addWidget(self.edit_coord_pixel_y_2, 1, 2)
        coord_grid.addWidget(self.lbl_WGS84_2, 1, 3)
        self.edit_coord_wgs84_lat_2 = QLineEdit()
        self.edit_coord_wgs84_lat_2.setPlaceholderText("latitude")
        self.edit_coord_wgs84_lat_2.setStyleSheet(self.lineedit_style)
        self.edit_coord_wgs84_lon_2 = QLineEdit()
        self.edit_coord_wgs84_lon_2.setPlaceholderText("longitude")
        self.edit_coord_wgs84_lon_2.setStyleSheet(self.lineedit_style)
        coord_grid.addWidget(self.edit_coord_wgs84_lat_2, 1, 4)
        coord_grid.addWidget(self.edit_coord_wgs84_lon_2, 1, 5)

        coord_grid.setColumnStretch(3, 1)
        main_layout.addWidget(self.coord_group)

        # --- 4. GroupBox: Choose a location Section ---
        self.pl_group = QGroupBox()
        pl_layout = QHBoxLayout(self.pl_group)
        pl_layout.setContentsMargins(15, 5, 15, 5)

        self.lbl_gps_coordinates = QLabel("GPS Coordinates:")
        pl_layout.addWidget(self.lbl_gps_coordinates)
        self.edit_gps_coordinates = QLineEdit()
        self.edit_gps_coordinates.setPlaceholderText("Copy and paste GPS coordinates here")
        pl_layout.addWidget(self.edit_gps_coordinates)

        pl_layout.addStretch()

        self.google_btn = QPushButton("Open\nGoogle\nMaps")
        self.google_btn.setFixedSize(100, 75)
        self.google_btn.setStyleSheet("font-weight: bold; border: 1px solid black;")
        pl_layout.addWidget(self.google_btn)

        main_layout.addWidget(self.pl_group)

        # --- 5. Bottom Buttons ---
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedSize(120, 35)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setFixedSize(120, 35)

        bottom_layout.addWidget(self.cancel_btn)
        bottom_layout.addWidget(self.apply_btn)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

        # ----- signals-slots connections -----
        self.radio_maps.clicked.connect(self.enableMaps)
        self.radio_one_gcp.clicked.connect(self.enableOnePoint)
        self.radio_two_gcp.clicked.connect(self.enableTwoPoints)
        self.radio_choose.clicked.connect(self.enableChoose)

        self.combobox_map_input.editTextChanged[str].connect(self.mapChanged)

        self.google_btn.clicked.connect(self.openGoogleMaps)

        self.cancel_btn.clicked.connect(self.close)
        self.apply_btn.clicked.connect(self.apply)

        self.points_count = 0
        self.points_to_pick = 0

        self.setWindowTitle("Georeferencing Tool")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.fillMaps()

        self.enableMaps()

    def fillMaps(self):

        for image in self.project.images:
            self.combobox_map_input.addItem(image.name)

    @pyqtSlot(str)
    def mapChanged(self, map_name):

        for image in self.project.images:
            if map_name == image.name:
                if image.georef_filename == "":
                    self.lbl_crs_info.setText("Non georeferenced.")
                else:
                    img = rio.open(image.georef_filename)
                    srs = osr.SpatialReference()
                    srs.ImportFromWkt(img.crs.to_wkt())
                    pretty_wkt = srs.ExportToPrettyWkt()
                    self.lbl_crs_info.setText(pretty_wkt)

    def disableAll(self):

        self.map_group.setEnabled(False)
        self.lbl_map_to_use.setEnabled(False)
        self.combobox_map_input.setEnabled(False)

        self.coord_group.setEnabled(False)
        self.btn_pick_point_1.setEnabled(False)
        self.edit_coord_pixel_x_1.setEnabled(False)
        self.edit_coord_pixel_y_1.setEnabled(False)
        self.lbl_WGS84_1.setEnabled(False)
        self.edit_coord_wgs84_lat_1.setEnabled(False)
        self.edit_coord_wgs84_lon_1.setEnabled(False)
        self.btn_pick_point_2.setEnabled(False)
        self.edit_coord_pixel_x_2.setEnabled(False)
        self.edit_coord_pixel_y_2.setEnabled(False)
        self.lbl_WGS84_2.setEnabled(False)
        self.edit_coord_wgs84_lat_2.setEnabled(False)
        self.edit_coord_wgs84_lon_2.setEnabled(False)

        self.pl_group.setEnabled(False)
        self.lbl_gps_coordinates.setEnabled(False)
        self.edit_gps_coordinates.setEnabled(False)
        self.google_btn.setEnabled(False)

    @pyqtSlot()
    def enableMaps(self):

        self.disableAll()

        self.map_group.setEnabled(True)
        self.lbl_map_to_use.setEnabled(True)
        self.combobox_map_input.setEnabled(True)

        self.points_to_pick = 0
        self.pointsToPickChanged.emit(0)

    @pyqtSlot()
    def enableOnePoint(self):

        self.disableAll()

        self.coord_group.setEnabled(True)
        self.btn_pick_point_1.setEnabled(True)
        self.edit_coord_pixel_x_1.setEnabled(True)
        self.edit_coord_pixel_y_1.setEnabled(True)
        self.lbl_WGS84_1.setEnabled(True)
        self.edit_coord_wgs84_lat_1.setEnabled(True)
        self.edit_coord_wgs84_lon_1.setEnabled(True)

        self.points_to_pick = 1
        self.pointsToPickChanged.emit(1)

    @pyqtSlot()
    def enableTwoPoints(self):

        self.disableAll()

        self.coord_group.setEnabled(True)
        self.btn_pick_point_1.setEnabled(True)
        self.edit_coord_pixel_x_1.setEnabled(True)
        self.edit_coord_pixel_y_1.setEnabled(True)
        self.lbl_WGS84_1.setEnabled(True)
        self.edit_coord_wgs84_lat_1.setEnabled(True)
        self.edit_coord_wgs84_lon_1.setEnabled(True)
        self.btn_pick_point_2.setEnabled(True)
        self.edit_coord_pixel_x_2.setEnabled(True)
        self.edit_coord_pixel_y_2.setEnabled(True)
        self.lbl_WGS84_2.setEnabled(True)
        self.edit_coord_wgs84_lat_2.setEnabled(True)
        self.edit_coord_wgs84_lon_2.setEnabled(True)

        self.points_to_pick = 2
        self.pointsToPickChanged.emit(2)

    @pyqtSlot()
    def enableChoose(self):

        self.disableAll()

        self.pl_group.setEnabled(True)
        self.lbl_gps_coordinates.setEnabled(True)
        self.edit_gps_coordinates.setEnabled(True)
        self.google_btn.setEnabled(True)

        self.points_to_pick = 0
        self.pointsToPickChanged.emit(0)

    @pyqtSlot()
    def openGoogleMaps(self):
        import webbrowser

        # The URL for the Google Maps webapp
        url = "https://www.google.com/maps"

        # Open the URL in a new tab, if possible
        webbrowser.open_new_tab(url)

    @pyqtSlot(float, float)
    def updatePointsPicked(self, x, y):

        if self.points_to_pick == 1:
            self.edit_coord_pixel_x_1.setText(str(x))
            self.edit_coord_pixel_y_1.setText(str(y))
        else:
            if self.points_count == 0:
                self.edit_coord_pixel_x_1.setText(str(x))
                self.edit_coord_pixel_y_1.setText(str(y))
            else:
                self.edit_coord_pixel_x_2.setText(str(x))
                self.edit_coord_pixel_y_2.setText(str(y))

        self.points_count += 1
        self.points_count = self.points_count % 2

    def validate_pixel_coordinates(self, x_str, y_str):

        try:
            x_str = float(x_str)
            y_str = float(y_str)

            return True, ""

        except ValueError:

            return False, "Invalid pixel coordinates. Please, check."

    def validate_lat_long(self, str_lat, str_lon):
        """
        Validates if two strings can be converted to floating-point numbers.
        Returns a tuple: (is_valid, float_values or error_message)
        """
        try:
            # Attempt to convert both strings
            lat_value = float(str_lat)
            lon_value = float(str_lon)

            if not (-90.0 <= lat_value <= 90.0):
                return False, "Latitude is out of range. Please, check."

            if not (-180.0 <= lon_value <= 180.0):
                return False, "Longitude is out of range. Please, check."

            return True, ""

        except ValueError:
            return False, "Please, indicate valid floating point numbers in the georeferencing coordinates."

    @pyqtSlot()
    def apply(self):

        msgBox = QMessageBox(parent=self)
        msgBox.setWindowTitle("Georeferencing Tool")

        # check if the values provided are valid
        if self.radio_one_gcp.isChecked():
            # georeferencing using one known point
            x_txt = self.edit_coord_pixel_x_1.text()
            y_txt = self.edit_coord_pixel_y_1.text()
            valid, msg = self.validate_pixel_coordinates(x_txt, y_txt)
            if not valid:
                msgBox.setText(msg)
                msgBox.exec()
                return

            lat_txt = self.edit_coord_wgs84_lat_1.text()
            lon_txt = self.edit_coord_wgs84_lon_1.text()
            valid, msg = self.validate_lat_long(lat_txt, lon_txt)
            if not valid:
                msgBox.setText(msg)
                msgBox.exec()
                return

        elif self.radio_two_gcp.isChecked():
            # georeferencing using two known points
            x1_txt = self.edit_coord_pixel_x_1.text()
            y1_txt = self.edit_coord_pixel_y_1.text()
            valid, msg = self.validate_pixel_coordinates(x1_txt, y1_txt)
            if not valid:
                msgBox.setText(msg)
                msgBox.exec()
                return

            lat_txt1 = self.edit_coord_wgs84_lat_1.text()
            lon_txt1 = self.edit_coord_wgs84_lon_1.text()
            valid, msg = self.validate_lat_long(lat_txt1, lon_txt1)
            if not self.validate_floats(msg):
                msgBox.setText(msg)
                msgBox.exec()
                return

            x2_txt = self.edit_coord_pixel_x_2.text()
            y2_txt = self.edit_coord_pixel_y_2.text()
            valid, msg = self.validate_pixel_coordinates(x2_txt, y2_txt)
            if not valid:
                msgBox.setText(msg)
                msgBox.exec()
                return

            lat_txt2 = self.edit_coord_wgs84_lat_1.text()
            lon_txt2 = self.edit_coord_wgs84_lon_1.text()
            valid, msg = self.validate_lat_long(lat_txt2, lon_txt2)
            if not valid:
                msgBox.setText(msg)
                msgBox.exec()
                return

        elif self.radio_choose.isChecked():
            # georeferencing using the GPS coordinates of a location

            gps_coord_txt = self.edit_gps_coordinates.text()
            lat_txt = gps_coord_txt.split(",")[0]
            lon_txt = gps_coord_txt.split(",")[1]
            lat_txt = lat_txt.strip()
            lon_txt = lon_txt.strip()
            valid, msg = self.validate_lat_long(lat_txt, lon_txt)
            if not valid:
                msgBox.setText(msg)
                msgBox.exec()
                return
        else:
            print("Georeferencing tool - Unknown option")

        self.validchoices.emit()

    def closeEvent(self,event):

        self.closewidget.emit()
        super(QtGeoreferencingWidget, self).closeEvent(event)




