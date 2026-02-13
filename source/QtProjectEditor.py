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


from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal, QEvent, QDate
from PyQt5.QtWidgets import QGridLayout, QWidget, QScrollArea, QGroupBox, QColorDialog, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout, QTextEdit, QTableWidget, QTableWidgetItem, QFrame, QHeaderView, QAbstractItemView
from PyQt5.QtGui import QFont
import rasterio as rio
import os, json, re
from source.RegionAttributes import RegionAttributes
from copy import deepcopy

class QtProjectEditor(QWidget):
    closed = pyqtSignal()
    def __init__(self, project, parent=None):
        super(QtProjectEditor, self).__init__(parent)
        self.project = project

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)

        # Create table for maps overview
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(['Map Name', 'Date', 'Size (px)', 'Pixel Size (mm)', 'Georef', 'DEM', 'Annotations', 'Actions'])
        
        # Set column resize modes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Map Name - stretch
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Date
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Size
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Pixel Size
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Georef
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # DEM
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Annotations
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # Actions
        header.resizeSection(7, 140)  # Set fixed width for Actions column
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.itemSelectionChanged.connect(self.onMapSelected)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: rgb(40,40,40);
                color: white;
                gridline-color: #505050;
            }
            QTableWidget::item {
                color: white;
                padding: 5px;
                border: none;
            }
            QTableWidget::item:alternate {
                background-color: rgb(50,50,50);
            }
            QTableWidget::item:selected {
                background-color: rgb(70,70,70);
                border: 1px solid rgb(100,100,100);
            }
            QHeaderView::section {
                background-color: rgb(60,60,60);
                color: white;
                padding: 5px;
                border: 1px solid #505050;
                font-weight: bold;
            }
        """)
        
        # Create details panel
        details_label = QLabel("<b>Map Details</b>")
        details_label.setStyleSheet("QLabel { color: white; }")
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(180)
        self.details_text.setPlaceholderText("Select a map to view detailed information...")
        self.details_text.setStyleSheet("QTextEdit { background-color: rgb(40,40,40); color: white; }")
        
        # Project summary label
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("QLabel { background-color: rgb(50,50,50); color: white; padding: 5px; border: 1px solid #505050; }")
        
        # Buttons
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(btn_close)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.summary_label)
        layout.addWidget(self.table)
        layout.addWidget(details_label)
        layout.addWidget(self.details_text)
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)

        self.setWindowTitle("Maps Editor")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.fillMaps()

    @pyqtSlot()
    def fillMaps(self):
        """Fill the table with map information"""
        
        self.table.setRowCount(len(self.project.images))
        
        total_annotations = 0
        date_list = []
        
        for row, img in enumerate(self.project.images):
            # Map Name
            name_item = QTableWidgetItem(img.name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 0, name_item)
            
            # Date
            date = self.convertDate(img.acquisition_date)
            date_item = QTableWidgetItem(date.toString('dd MMM yyyy'))
            date_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 1, date_item)
            date_list.append(date)
            
            # Size
            size_item = QTableWidgetItem(f"{img.width} × {img.height}")
            size_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 2, size_item)
            
            # Pixel Size
            pixel_size_item = QTableWidgetItem(str(img.map_px_to_mm_factor))
            pixel_size_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 3, pixel_size_item)
            
            # Georef
            georef_item = QTableWidgetItem("Yes" if img.georef_filename else "No")
            georef_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 4, georef_item)
            
            # DEM
            dem_item = QTableWidgetItem("Yes" if len(img.channels) > 1 else "No")
            dem_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 5, dem_item)
            
            # Annotations count
            ann_count = len(img.annotations.seg_blobs) + len(img.annotations.annpoints)
            total_annotations += ann_count
            ann_item = QTableWidgetItem(str(ann_count))
            ann_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row, 6, ann_item)
            
            # Actions (Edit/Delete buttons)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setMaximumWidth(60)
            edit_btn.clicked.connect(lambda checked, img=img: self.editMap(img))
            
            delete_btn = QPushButton("Delete")
            delete_btn.setMaximumWidth(60)
            delete_btn.clicked.connect(lambda checked, img=img: self.deleteMap(img))
            
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch()
            
            self.table.setCellWidget(row, 7, actions_widget)
        
        # Update project summary
        if date_list:
            min_date = min(date_list).toString('dd MMM yyyy')
            max_date = max(date_list).toString('dd MMM yyyy')
            date_range = f"{min_date} to {max_date}" if min_date != max_date else min_date
        else:
            date_range = "N/A"
            
        summary_text = f"<b>Project Summary:</b> {len(self.project.images)} map(s) | {total_annotations} annotation(s) | Date range: {date_range}"
        self.summary_label.setText(summary_text)
        
    @pyqtSlot()
    def onMapSelected(self):
        """Display detailed information when a map is selected"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.details_text.clear()
            return
            
        row = selected_rows[0].row()
        img = self.project.images[row]
        
        date = self.convertDate(img.acquisition_date)
        day = date.day()
        year = date.year()
        
        details = f"<b>Map Name:</b> {img.name}<br>"
        details += f"<b>Acquisition Date:</b> {day} {date.longMonthName(date.month())} {year}<br>"
        details += f"<b>Map Size (pixels):</b> {img.width} × {img.height}<br>"
        details += f"<b>Pixel Size (mm):</b> {img.map_px_to_mm_factor}<br>"
        details += f"<b>RGB Channel:</b> {img.channels[0].filename if img.channels else 'None'}<br>"
        
        if img.georef_filename:
            georef_info = self.georefAvailable(img.georef_filename)
            details += f"<b>Georeference Information:</b><br><pre>{georef_info}</pre>"
        else:
            details += f"<b>Georeference Information:</b> None<br>"
        
        details += f"<b>DEM Availability:</b> {self.boolToWord(len(img.channels) > 1)}<br>"
        
        region_count = len(img.annotations.seg_blobs)
        point_count = len(img.annotations.annpoints)
        details += f"<b>Annotations:</b> {region_count} region(s), {point_count} point(s)"
        
        self.details_text.setHtml(details)


    def editMap(self, img):
        self.parent().editMapSettingsImage(img)

        # mapWidget actually disconnects everything before show
        self.parent().mapWidget.accepted.connect(self.fillMaps)

    def cropMap(self, img):

        self.parent().cropMapImage(img)

    def deleteMap(self, img):

        reply = QMessageBox.question(self, "Deleting map",
                                     "About to delete map: " + img.name + ". Are you sure?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self.parent().deleteImage(img)
        self.fillMaps()

    def closeEvent(self, event):
        self.closed.emit()


    def georefAvailable(self, path):

        if path == "":
            return "None"
        else:
            img = rio.open(path)
            geoinfo = img.crs

            from osgeo import osr
            srs = osr.SpatialReference()
            srs.ImportFromWkt(geoinfo.to_wkt())
            pretty_wkt = srs.ExportToPrettyWkt()
            return pretty_wkt

    def boolToWord(self, bool):

        if bool == True:
            return "Yes"
        else:
            return "No"

    def convertDate(self, str):
        myDate = QDate.fromString(str, 'yyyy-MM-dd')
        return myDate


