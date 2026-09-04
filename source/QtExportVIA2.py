# TagLab
# A semi-automatic segmentation tool
#
# Copyright(C) 2020
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

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QFileDialog, QVBoxLayout, QHBoxLayout,
                             QComboBox, QCheckBox, QLabel, QPushButton, QMessageBox)
import numpy as np
import json
import os


class QtVIA2Export(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        # DATA ##########################################################
        self.activeviewer = parent.activeviewer
        self.project = parent.project
        self.taglab_dir = parent.taglab_dir
        self.options = {
            "export_regions": 0,       # 0 all, 1 visible, 2 selected
            "export_all_maps": False,  # export all project maps
            "include_attributes": False,  # include note and custom data fields
        }
        # ###############################################################

        # GUI ###########################################################
        self.setWindowTitle("VIA2 Export Options")
        self.adjustSize()
        self.setSizeGripEnabled(True)

        self.setStyleSheet("""
            QToolTip {
                background-color: #f0f0f0;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 3px;
                border-radius: 2px;
            }
        """)

        main_layout = QVBoxLayout()

        # --- Region selection ---
        blobs_layout = QVBoxLayout()
        blobs_label = QLabel("Export Regions:")
        blobs_layout.addWidget(blobs_label)

        self.exportRegions = QComboBox()
        self.exportRegions.addItem("All Regions")
        self.exportRegions.addItem("Visible Regions")
        self.exportRegions.addItem("Selected Regions")
        self.exportRegions.setCurrentIndex(self.options["export_regions"])
        blobs_layout.addWidget(self.exportRegions)

        self.export_all_maps_checkbox = QCheckBox("Export All Maps")
        self.export_all_maps_checkbox.setToolTip(
            "Export annotations from all maps in the project into a single VIA2 file. "
            "Always exports all annotations regardless of visibility or selection.")
        self.export_all_maps_checkbox.setChecked(self.options["export_all_maps"])
        self.export_all_maps_checkbox.toggled.connect(self._on_export_all_maps_toggled)
        blobs_layout.addWidget(self.export_all_maps_checkbox)

        main_layout.addLayout(blobs_layout)

        # --- Separator ---
        line = QLabel()
        line.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line)

        # --- Additional options ---
        format_layout = QVBoxLayout()
        format_label = QLabel("Annotation Options:")
        format_layout.addWidget(format_label)

        self.attributes_checkbox = QCheckBox("Include Custom Attributes")
        self.attributes_checkbox.setToolTip(
            "Export region notes and custom data fields as additional region attributes.")
        self.attributes_checkbox.setChecked(self.options["include_attributes"])
        format_layout.addWidget(self.attributes_checkbox)

        main_layout.addLayout(format_layout)

        # --- Separator ---
        line2 = QLabel()
        line2.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line2)

        # --- Info label ---
        info_label = QLabel(
            "Exports regions as VGG Image Annotator v2 (VIA2) JSON format. "
            "Each region is encoded as a polygon. "
            "Note: VIA2 does not support holes in polygons; only the outer contour "
            "is exported. Regions with holes will be flagged in region attributes.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 9pt;")
        main_layout.addWidget(info_label)

        # --- Buttons ---
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)
        # ###############################################################

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _on_export_all_maps_toggled(self, checked):
        self.exportRegions.setEnabled(not checked)

    def accept(self):
        self.options["export_regions"] = self.exportRegions.currentIndex()
        self.options["export_all_maps"] = self.export_all_maps_checkbox.isChecked()
        self.options["include_attributes"] = self.attributes_checkbox.isChecked()

        super().accept()
        self.export_via2()

    def export_via2(self):
        filters = "VIA2 JSON (*.json)"
        output_filename, _ = QFileDialog.getSaveFileName(
            self, "Save VIA2 Annotations As", self.taglab_dir, filters)
        if not output_filename:
            return
        if not output_filename.lower().endswith('.json'):
            output_filename += '.json'

        try:
            via_data = {}
            region_count = 0
            holes_count = 0  # number of regions where inner contours were dropped

            if self.options["export_all_maps"]:
                images_to_export = list(self.project.images)
            else:
                images_to_export = [self.activeviewer.image]

            for image in images_to_export:
                # Resolve the image filename and size
                rgb_channel = next((c for c in image.channels if c.type == "RGB"), None)
                if rgb_channel:
                    image_filename = os.path.basename(rgb_channel.filename)
                    try:
                        image_size = os.path.getsize(rgb_channel.filename)
                    except OSError:
                        image_size = 0
                elif image.name:
                    image_filename = image.name
                    image_size = 0
                else:
                    image_filename = f"image_{image.id}"
                    image_size = 0

                # VIA2 top-level key is filename + filesize (as string)
                via_key = image_filename + str(image_size)

                # --- Determine which blobs to export ---
                if self.options["export_all_maps"]:
                    exported_blobs = image.annotations.seg_blobs
                elif self.options["export_regions"] == 1:   # Visible
                    exported_blobs = [b for b in self.activeviewer.annotations.seg_blobs
                                      if self.project.isLabelVisible(b.class_name)]
                elif self.options["export_regions"] == 2:   # Selected
                    exported_blobs = self.activeviewer.selected_blobs
                else:   # All (default)
                    exported_blobs = self.activeviewer.annotations.seg_blobs

                # --- Build regions list ---
                regions = []
                for blob in exported_blobs:
                    contour = blob.contour
                    if contour.shape[0] < 3:
                        continue  # skip degenerate contours

                    has_holes = len(blob.inner_contours) > 0
                    if has_holes:
                        holes_count += 1

                    pts = np.round(contour).astype(int)
                    all_points_x = pts[:, 0].tolist()
                    all_points_y = pts[:, 1].tolist()

                    region_attributes = {
                        "class": blob.class_name
                    }
                    if has_holes:
                        region_attributes["has_holes"] = True

                    if self.options["include_attributes"]:
                        if blob.note and blob.note.strip():
                            region_attributes["note"] = blob.note
                        if blob.data:
                            region_attributes["attributes"] = blob.data.copy()

                    regions.append({
                        "shape_attributes": {
                            "name": "polygon",
                            "all_points_x": all_points_x,
                            "all_points_y": all_points_y
                        },
                        "region_attributes": region_attributes
                    })
                    region_count += 1

                via_data[via_key] = {
                    "filename": image_filename,
                    "size": image_size,
                    "regions": regions,
                    "file_attributes": {
                        "acquisition_date": image.acquisition_date if image.acquisition_date else "",
                        "px_to_mm": float(image.map_px_to_mm_factor) if image.map_px_to_mm_factor else 1.0
                    }
                }

            with open(output_filename, 'w') as f:
                json.dump(via_data, f, indent=2)

            # --- Confirmation message ---
            maps_count = len(images_to_export)
            maps_str = f"Maps exported: {maps_count}\n" if self.options["export_all_maps"] else ""
            msg = (f"VIA2 annotations exported successfully!\n\n"
                   f"File: {os.path.basename(output_filename)}\n"
                   f"{maps_str}"
                   f"Regions exported: {region_count}")

            msgBox = QMessageBox(self)
            if holes_count > 0:
                msgBox.setWindowTitle("Export Completed with Warnings")
                msgBox.setIcon(QMessageBox.Warning)
                msg += (f"\n\nWarning: {holes_count} region(s) had holes (inner contours) "
                        f"that could not be represented in VIA2 format. "
                        f"Only the outer contour was exported for those regions; "
                        f"they are flagged with \"has_holes\": true in region_attributes.\n"
                        f"Use WADM export for full-fidelity export of regions with holes.")
            else:
                msgBox.setWindowTitle("Export Successful")
                msgBox.setIcon(QMessageBox.Information)

            msgBox.setText(msg)
            msgBox.exec()

        except Exception as e:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Failed")
            msgBox.setText(f"Error exporting VIA2 file:\n{str(e)}")
            msgBox.exec()
