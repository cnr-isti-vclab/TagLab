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
from PyQt5.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QLabel, QPushButton, QMessageBox
from pycocotools import mask as maskcoco
import numpy as np
import json
import os
import datetime
from skimage import measure
from source import genutils

class QtCOCOExport(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        # DATA ##########################################################
        self.activeviewer = parent.activeviewer
        self.project = parent.project
        self.taglab_dir = parent.taglab_dir
        self.options = {
            "export_regions": 0,  # 0 all, 1 visible, 2 selected
            "export_all_maps": False,  # Export all project maps (always all annotations)
            "include_segmentation": True,  # Include full polygon/mask segmentation
            "include_attributes": False,  # Include custom attributes (note, data)
        }
        # ###############################################################

        # GUI ###########################################################
        self.setWindowTitle("COCO Export Options")
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

        # Main layout
        main_layout = QVBoxLayout()

        # Layout to choose blobs to export
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
        self.export_all_maps_checkbox.setToolTip("Export annotations from all maps in the project into a single COCO file. Always exports all annotations regardless of visibility or selection.")
        self.export_all_maps_checkbox.setChecked(self.options["export_all_maps"])
        self.export_all_maps_checkbox.toggled.connect(self._on_export_all_maps_toggled)
        blobs_layout.addWidget(self.export_all_maps_checkbox)

        main_layout.addLayout(blobs_layout)

        # add horizontal line
        line = QLabel()
        line.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line)

        # Layout for annotation format options
        format_layout = QVBoxLayout()
        format_label = QLabel("Annotation Format:")
        format_layout.addWidget(format_label)
        
        self.segmentation_checkbox = QCheckBox("Include Segmentation (Polygons/RLE)")
        self.segmentation_checkbox.setToolTip("Export full polygon segmentation masks in RLE format (for instance segmentation tasks).")
        self.segmentation_checkbox.setChecked(self.options["include_segmentation"])
        format_layout.addWidget(self.segmentation_checkbox)

        self.attributes_checkbox = QCheckBox("Include Custom Attributes")
        self.attributes_checkbox.setToolTip("Export region notes and custom data fields as additional annotation properties.")
        self.attributes_checkbox.setChecked(self.options["include_attributes"])
        format_layout.addWidget(self.attributes_checkbox)
        
        main_layout.addLayout(format_layout)

        # add horizontal line
        line2 = QLabel()
        line2.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line2)

        # Info label
        info_label = QLabel("Segmentation masks are optional and used for instance segmentation tasks. "
                            "Custom attributes include region notes and any user-defined data fields.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 9pt;")
        main_layout.addWidget(info_label)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(self.cancel_button)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)
        # ###############################################################

        # Connect signals
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)


    def _on_export_all_maps_toggled(self, checked):
        # Disable region selection when exporting all maps
        self.exportRegions.setEnabled(not checked)


    # Accept the dialog and update options
    def accept(self):
        # Update options based on user selections
        self.options["export_regions"] = self.exportRegions.currentIndex()
        self.options["export_all_maps"] = self.export_all_maps_checkbox.isChecked()
        self.options["include_segmentation"] = self.segmentation_checkbox.isChecked()
        self.options["include_attributes"] = self.attributes_checkbox.isChecked()

        super().accept()    # Call the base class accept method to close the dialog
        # Proceed with COCO export
        self.export_coco()


    # Function to perform the COCO export based on selected options
    def export_coco(self):
        # Open a file dialog to select the output file
        filters = "JSON (*.json)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Save COCO Annotations As", self.taglab_dir, filters)
        if not output_filename:
            return  # no file selected, abort
        if not output_filename.lower().endswith('.json'):
            output_filename += '.json'

        try:
            # Build COCO structure
            coco_data = {}

            # INFO section
            info = {
                "description": "Dataset exported from TagLab",
                "url": "",
                "version": "1.0",
                "year": str(datetime.date.today().year),
                "contributor": "",
                "date_created": datetime.date.today().isoformat()
            }
            coco_data["info"] = info

            # LICENSES section (optional)
            coco_data["licenses"] = []

            # CATEGORIES section
            categories = []
            category_map = {}  # Map class_name to category_id
            
            # Get unique classes from labels
            for idx, (label_name, label_obj) in enumerate(sorted(self.project.labels.items())):
                category = {
                    "id": idx,
                    "name": label_name,
                    "supercategory": "object",
                    "color": label_obj.fill
                }
                categories.append(category)
                category_map[label_name] = idx
            
            coco_data["categories"] = categories

            images = []
            annotations = []
            ann_id = 0

            if self.options["export_all_maps"]:
                # Export all maps in the project
                images_to_export = [(img_id, img) for img_id, img in enumerate(self.project.images)]
            else:
                images_to_export = [(0, self.activeviewer.image)]

            for img_id, image in images_to_export:

                # IMAGES section entry
                rgb_channel = next((c for c in image.channels if c.type == "RGB"), None)
                image_filename = os.path.basename(rgb_channel.filename) if rgb_channel else image.name
                image_data = {
                    "id": img_id,
                    "file_name": image_filename,
                    "width": image.width,
                    "height": image.height,
                    "date_captured": image.acquisition_date if hasattr(image, 'acquisition_date') else "",
                    "license": 0
                }
                images.append(image_data)

                # Determine which blobs to export for this image
                if self.options["export_all_maps"]:
                    exported_blobs = image.annotations.seg_blobs
                elif self.options["export_regions"] == 0:  # All Regions
                    exported_blobs = self.activeviewer.annotations.seg_blobs
                elif self.options["export_regions"] == 1:  # Visible Regions
                    exported_blobs = [b for b in self.activeviewer.annotations.seg_blobs
                                      if self.project.isLabelVisible(b.class_name)]
                elif self.options["export_regions"] == 2:  # Selected Regions
                    exported_blobs = self.activeviewer.selected_blobs

                # ANNOTATIONS section
                for blob in exported_blobs:
                    annotation = {
                        "id": ann_id,
                        "image_id": img_id,
                        "category_id": category_map.get(blob.class_name, 0),
                        "iscrowd": 0
                    }

                    # Add segmentation if requested
                    if self.options["include_segmentation"]:
                        # Create binary mask from blob
                        mask = np.zeros((image.height, image.width), dtype=np.uint8)

                        contour_int = blob.contour.astype(np.int32)
                        if len(contour_int) > 0:
                            from cv2 import fillPoly
                            fillPoly(mask, [contour_int], 1)
                            for inner_contour in blob.inner_contours:
                                inner_contour_int = inner_contour.astype(np.int32)
                                if len(inner_contour_int) > 0:
                                    fillPoly(mask, [inner_contour_int], 0)

                        rle = maskcoco.encode(np.asfortranarray(mask.T))
                        rle["counts"] = rle["counts"].decode("utf-8")
                        annotation["segmentation"] = rle
                        annotation["area"] = int(np.sum(mask))
                    else:
                        annotation["area"] = int(blob.area)

                    # Always add bounding box (required by COCO format)
                    # COCO format: [x, y, width, height]; blob.bbox is [top, left, width, height]
                    annotation["bbox"] = [float(blob.bbox[1]), float(blob.bbox[0]),
                                          float(blob.bbox[2]), float(blob.bbox[3])]

                    # Optionally add custom attributes (note and data fields)
                    if self.options["include_attributes"]:
                        if blob.note and blob.note.strip():
                            annotation["note"] = blob.note
                        if blob.data:
                            annotation["attributes"] = blob.data.copy()

                    annotations.append(annotation)
                    ann_id += 1

            coco_data["images"] = images
            coco_data["annotations"] = annotations

            # Save to file
            with open(output_filename, 'w') as f:
                json.dump(coco_data, f, indent=2)

            # Show confirmation message
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Successful")
            maps_str = f"Maps exported: {len(images)}\n" if self.options["export_all_maps"] else ""
            msgBox.setText(f"COCO annotations exported successfully!\n\nFile: {os.path.basename(output_filename)}\n{maps_str}Regions exported: {len(annotations)}")
            msgBox.exec()

        except Exception as e:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Failed")
            msgBox.setText(f"Error exporting COCO file:\n{str(e)}")
            msgBox.exec()
