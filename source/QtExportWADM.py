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
import datetime


def _contour_to_svg_path(outer, inner_contours, color=None, filled=False):
    """
    Convert blob contour(s) to an SVG path string.
    outer            : numpy array shape (N, 2), columns [x, y]
    inner_contours   : list of numpy arrays, same format
    color            : optional [r, g, b] list for the class color
    filled           : if True, region is filled with color; if False (default),
                       only the outline is drawn with color as stroke

    Returns an SVG <path> element string, or None for degenerate contours.
    If there are holes, fill-rule="evenodd" is used.
    """

    def _ring_to_path(pts):
        pts = np.round(pts).astype(int)
        parts = [f"M {pts[0, 0]} {pts[0, 1]}"]
        for i in range(1, len(pts)):
            parts.append(f"L {pts[i, 0]} {pts[i, 1]}")
        parts.append("Z")
        return " ".join(parts)

    if outer.shape[0] < 3:
        return None

    style_attr = ""
    if color is not None:
        r, g, b = int(color[0]), int(color[1]), int(color[2])
        hex_color = f"#{r:02x}{g:02x}{b:02x}"
        if filled:
            style_attr = f' fill="{hex_color}"'
        else:
            style_attr = f' fill="none" stroke="{hex_color}"'

    if inner_contours:
        d = _ring_to_path(outer)
        for inner in inner_contours:
            d += " " + _ring_to_path(inner)
        return f'<svg><path fill-rule="evenodd"{style_attr} d="{d}"/></svg>'
    else:
        d = _ring_to_path(outer)
        return f'<svg><path{style_attr} d="{d}"/></svg>'


class QtWADMExport(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        # DATA ##########################################################
        self.activeviewer = parent.activeviewer
        self.project = parent.project
        self.taglab_dir = parent.taglab_dir
        self.taglab_version = parent.TAGLAB_VERSION   # e.g. "TagLab 2026.4.1"
        self.options = {
            "export_regions": 0,       # 0 all, 1 visible, 2 selected
            "export_all_maps": False,  # export all project maps
            "include_attributes": False,  # include note and custom data fields
            "filled_regions": False,   # fill regions with class color (default: outline only)
        }
        # ###############################################################

        # GUI ###########################################################
        self.setWindowTitle("WADM Export Options")
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
            "Export annotations from all maps in the project into a single WADM file. "
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
            "Export region notes and custom data fields as additional annotation properties.")
        self.attributes_checkbox.setChecked(self.options["include_attributes"])
        format_layout.addWidget(self.attributes_checkbox)

        self.filled_checkbox = QCheckBox("Draw Filled Regions")
        self.filled_checkbox.setToolTip(
            "Fill regions with the class color. By default only the outline is drawn with the class color.")
        self.filled_checkbox.setChecked(self.options["filled_regions"])
        format_layout.addWidget(self.filled_checkbox)

        main_layout.addLayout(format_layout)

        # --- Separator ---
        line2 = QLabel()
        line2.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line2)

        # --- Info label ---
        info_label = QLabel(
            "Exports regions as W3C Web Annotation Data Model (WADM) JSON-LD. "
            "Each region is encoded as an SVG path selector. "
            "Each map is described by a dedicated annotation. "
            "Custom attributes include region notes and any user-defined data fields.")
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
        self.options["filled_regions"] = self.filled_checkbox.isChecked()

        super().accept()
        self.export_wadm()

    def export_wadm(self):
        filters = "WADM JSON-LD (*.json);;JSON-LD (*.jsonld)"
        output_filename, _ = QFileDialog.getSaveFileName(
            self, "Save WADM Annotations As", self.taglab_dir, filters)
        if not output_filename:
            return
        if not (output_filename.lower().endswith('.json') or
                output_filename.lower().endswith('.jsonld')):
            output_filename += '.json'

        try:
            items = []

            if self.options["export_all_maps"]:
                images_to_export = list(self.project.images)
            else:
                images_to_export = [self.activeviewer.image]

            for image in images_to_export:
                # Resolve the image source filename
                rgb_channel = next((c for c in image.channels if c.type == "RGB"), None)
                if rgb_channel:
                    image_source = os.path.basename(rgb_channel.filename)
                elif image.name:
                    image_source = image.name
                else:
                    image_source = f"image_{image.id}"

                # --- Describing annotation for the map ---
                map_value = {
                    "name": image.name or "",
                    "id": image.id,
                    "acquisition_date": image.acquisition_date if image.acquisition_date else "",
                    "px_to_mm": float(image.map_px_to_mm_factor) if image.map_px_to_mm_factor else 1.0,
                    "width": image.width or 0,
                    "height": image.height or 0,
                }
                if image.georef_filename:
                    map_value["georef_filename"] = os.path.basename(image.georef_filename)
                if image.metadata:
                    map_value["metadata"] = image.metadata

                describing_ann = {
                    "type": "Annotation",
                    "body": {
                        "type": "Dataset",
                        "purpose": "describing",
                        "value": map_value
                    },
                    "target": {"source": image_source}
                }
                items.append(describing_ann)

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

                # --- Region annotations ---
                for blob in exported_blobs:
                    label = self.project.labels.get(blob.class_name)
                    color = label.fill if label else None
                    svg_value = _contour_to_svg_path(
                        blob.contour, blob.inner_contours,
                        color=color, filled=self.options["filled_regions"])
                    if svg_value is None:
                        continue  # skip blobs with degenerate contours

                    ann = {
                        "type": "Annotation",
                        "body": {
                            "type": "TextualBody",
                            "purpose": "classifying",
                            "value": blob.class_name
                        },
                        "target": {
                            "source": image_source,
                            "selector": {
                                "type": "SvgSelector",
                                "value": svg_value
                            }
                        }
                    }

                    if self.options["include_attributes"]:
                        if blob.note and blob.note.strip():
                            ann["note"] = blob.note
                        if blob.data:
                            ann["attributes"] = blob.data.copy()

                    items.append(ann)

            # --- Top-level AnnotationCollection ---
            region_count = sum(1 for it in items
                               if it.get("body", {}).get("purpose") == "classifying")
            project_label = (os.path.basename(self.project.filename)
                             if self.project.filename else "TagLab Export")
            collection = {
                "@context": "http://www.w3.org/ns/anno.jsonld",
                "type": "AnnotationCollection",
                "label": project_label,
                "generator": self.taglab_version,
                "generated": datetime.date.today().isoformat(),
                "total": region_count,
                "items": items
            }

            with open(output_filename, 'w') as f:
                json.dump(collection, f, indent=2)

            # --- Confirmation ---
            maps_count = len(images_to_export)
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Successful")
            maps_str = f"Maps exported: {maps_count}\n" if self.options["export_all_maps"] else ""
            msgBox.setText(
                f"WADM annotations exported successfully!\n\n"
                f"File: {os.path.basename(output_filename)}\n"
                f"{maps_str}"
                f"Regions exported: {region_count}")
            msgBox.exec()

        except Exception as e:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Failed")
            msgBox.setText(f"Error exporting WADM file:\n{str(e)}")
            msgBox.exec()
