from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QLabel, QPushButton, QSpinBox, QMessageBox
import xml.etree.ElementTree as ET
from xml.dom import minidom

class QtSVGExport(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        # DATA ##########################################################
        self.activeviewer = parent.activeviewer
        self.project = parent.project
        self.taglab_dir = parent.taglab_dir
        self.options = {
            "export_workspace": True,
            "export_workingarea": False,
            "export_grid": False,
            "export_regions": 0,  # 0 all, 1 visible, 2 selected
            "export_labels": 1,    # 0 None, 1 Class Name, 2 Region ID
            "export_shorten": False,
            "export_shorten_length": 5,
            "use_georef": False
        }
        # ###############################################################

        # GUI ###########################################################
        self.setWindowTitle("SVG Export Options")
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
        main_layout.addLayout(blobs_layout)

        # layout to choose label naming
        labels_layout = QVBoxLayout()
        labels_label = QLabel("Export Labels:")
        labels_layout.addWidget(labels_label)
        self.exportLabels = QComboBox()
        self.exportLabels.addItem("None")
        self.exportLabels.addItem("Class Name")
        self.exportLabels.addItem("Region ID")
        self.exportLabels.setCurrentIndex(self.options["export_labels"])
        labels_layout.addWidget(self.exportLabels)
        shorten_layout = QHBoxLayout()
        self.shorten_checkbox = QCheckBox("Shorten to:")
        self.shorten_checkbox.setToolTip("Shorten CLASS labels to a specified number of characters.")
        shorten_layout.addWidget(self.shorten_checkbox)
        self.shorten_spinbox = QSpinBox()
        self.shorten_spinbox.setRange(1, 10)
        self.shorten_spinbox.setValue(5)
        shorten_layout.addWidget(self.shorten_spinbox)
        labels_layout.addLayout(shorten_layout)
        main_layout.addLayout(labels_layout)

        # add horizontal line
        line = QLabel()
        line.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line)

        # Layout for choosing elements
        elements_layout = QVBoxLayout()
        elements_label = QLabel("Reference Elements:")
        elements_layout.addWidget(elements_label)
        self.workspace_checkbox = QCheckBox("Image Workspace")
        self.workspace_checkbox.setToolTip("Export the image workspace as a rectangle in the SVG file.")
        self.workspace_checkbox.setChecked(self.options["export_workspace"])
        elements_layout.addWidget(self.workspace_checkbox)
        self.workingarea_checkbox = QCheckBox("Working Area")
        self.workingarea_checkbox.setToolTip("Export the working area as a rectangle in the SVG file.")
        self.workingarea_checkbox.setChecked(self.options["export_workingarea"])
        self.workingarea_checkbox.setEnabled(False)  # Initially greyed out
        elements_layout.addWidget(self.workingarea_checkbox)
        self.grid_checkbox = QCheckBox("Grid")
        self.grid_checkbox.setToolTip("Export the grid as lines in the SVG file.")
        self.grid_checkbox.setChecked(self.options["export_grid"])
        self.grid_checkbox.setEnabled(False)  # Initially greyed out        
        elements_layout.addWidget(self.grid_checkbox)
        main_layout.addLayout(elements_layout)

        # add horizontal line
        line2 = QLabel()
        line2.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line2)

        # Others options layout
        others_layout = QVBoxLayout()
        # Georeferencing option
        self.georef_checkbox = QCheckBox("Use Georeferencing")
        self.georef_checkbox.setToolTip("Use georeferencing information from the image if available.")
        self.georef_checkbox.setChecked(self.options["use_georef"])
        self.georef_checkbox.setEnabled(False)  # Initially greyed out
        others_layout.addWidget(self.georef_checkbox)

        main_layout.addLayout(others_layout)

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

        # Enable/disable checkboxes based on viewer state
        if self.activeviewer.image.georef_filename:
            self.georef_checkbox.setEnabled(True)      
        if self.project.working_area is not None:
            self.workingarea_checkbox.setEnabled(True)
        if self.activeviewer.image.grid is not None:
            self.grid_checkbox.setEnabled(True)


    # Accept the dialog and update options
    def accept(self):
        # Update options based on user selections
        self.options["export_workspace"] = self.workspace_checkbox.isChecked()
        self.options["export_workingarea"] = self.workingarea_checkbox.isChecked()
        self.options["export_grid"] = self.grid_checkbox.isChecked()
        self.options["export_regions"] = self.exportRegions.currentIndex()
        self.options["export_labels"] = self.exportLabels.currentIndex()
        self.options["export_shorten"] = self.shorten_checkbox.isChecked()
        self.options["export_shorten_length"] = self.shorten_spinbox.value()
        self.options["use_georef"] = self.georef_checkbox.isChecked()

        super().accept()    # Call the base class accept method to close the dialog
        # Proceed with SVG export
        self.export_svg()


    def rgb_to_hex(self, rgb):
        """Convert RGB list/tuple to hex color string."""
        return '#%02x%02x%02x' % tuple(rgb)


    # Function to perform the SVG export based on selected options
    def export_svg(self):
        # Open a file dialog to select the output file
        filters = "SVG (*.svg)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Save SVG File As", self.taglab_dir, filters)
        if not output_filename: return # no file selected, abort
        if not output_filename.lower().endswith('.svg'):
            output_filename += '.svg'
        
        georef = None # Initialize georef to None
        transform = None
        text_height_scale = 1.0 # Default text height scale

        try:
            # Check if georeferencing information is available and process accordingly
            if self.options["use_georef"] and hasattr(self.activeviewer.image, 'georef_filename') and self.activeviewer.image.georef_filename:
                from source import rasterops
                georef, transform = rasterops.load_georef(self.activeviewer.image.georef_filename)
                text_height_scale = max(abs(transform.a), abs(transform.e))

            # Determine SVG dimensions
            if georef and transform:
                # Calculate transformed bounds
                corners = [
                    transform * (0, 0),
                    transform * (self.activeviewer.image.width, 0),
                    transform * (self.activeviewer.image.width, self.activeviewer.image.height),
                    transform * (0, self.activeviewer.image.height)
                ]
                min_x = min(c[0] for c in corners)
                max_x = max(c[0] for c in corners)
                min_y = min(c[1] for c in corners)
                max_y = max(c[1] for c in corners)
                viewbox_width = max_x - min_x
                viewbox_height = max_y - min_y
                viewbox = f"{min_x} {min_y} {viewbox_width} {viewbox_height}"
            else:
                viewbox_width = self.activeviewer.image.width
                viewbox_height = self.activeviewer.image.height
                viewbox = f"0 0 {viewbox_width} {viewbox_height}"

            # Create SVG root element
            svg = ET.Element('svg', {
                'xmlns': 'http://www.w3.org/2000/svg',
                'version': '1.1',
                'viewBox': viewbox,
                'width': str(viewbox_width),
                'height': str(viewbox_height)
            })

            # Add a group for each layer type
            workspace_group = ET.SubElement(svg, 'g', {'id': 'workspace'})
            workingarea_group = ET.SubElement(svg, 'g', {'id': 'working_area'})
            grid_group = ET.SubElement(svg, 'g', {'id': 'grid'})
            regions_group = ET.SubElement(svg, 'g', {'id': 'regions'})

            # Determine which blobs to export
            if self.options["export_regions"] == 0:  # All Regions
                exported_blobs = self.activeviewer.annotations.seg_blobs
            elif self.options["export_regions"] == 1:  # Visible Regions
                exported_blobs = []
                for to_export in self.activeviewer.annotations.seg_blobs:
                    if self.project.isLabelVisible(to_export.class_name):
                        exported_blobs.append(to_export)
            elif self.options["export_regions"] == 2:  # Selected Regions
                exported_blobs = self.activeviewer.selected_blobs

            # Add workspace outline if selected
            if self.options["export_workspace"]:
                map_outline = [
                    (0, 0),
                    (self.activeviewer.image.width, 0),
                    (self.activeviewer.image.width, self.activeviewer.image.height),
                    (0, self.activeviewer.image.height)
                ]
                if georef and transform:
                    map_outline = [transform * (x, y) for x, y in map_outline]
                
                points_str = ' '.join([f"{x},{y}" for x, y in map_outline])
                ET.SubElement(workspace_group, 'polygon', {
                    'points': points_str,
                    'fill': 'none',
                    'stroke': '#888888',
                    'stroke-width': '3'
                })

            # Add working area outline if selected
            if self.options["export_workingarea"] and self.project.working_area is not None:
                map_outline = [
                    (self.project.working_area[1], self.project.working_area[0]),
                    (self.project.working_area[1] + self.project.working_area[2], self.project.working_area[0]),
                    (self.project.working_area[1] + self.project.working_area[2], self.project.working_area[0] + self.project.working_area[3]),
                    (self.project.working_area[1], self.project.working_area[0] + self.project.working_area[3])
                ]
                if georef and transform:
                    map_outline = [transform * (x, y) for x, y in map_outline]
                
                points_str = ' '.join([f"{x},{y}" for x, y in map_outline])
                ET.SubElement(workingarea_group, 'polygon', {
                    'points': points_str,
                    'fill': 'none',
                    'stroke': '#00ff00',
                    'stroke-width': '3',
                    'stroke-dasharray': '10,5'
                })

            # Add blobs
            for blob in exported_blobs:
                layer_name = blob.class_name
                col = self.project.labels[blob.class_name].fill
                color_hex = self.rgb_to_hex(col)

                # Create a group for this blob
                blob_group = ET.SubElement(regions_group, 'g', {
                    'class': layer_name,
                    'id': f'blob_{blob.id}'
                })

                if georef and transform:
                    points = [transform * (x, y) for x, y in blob.contour]
                else:
                    points = list(blob.contour)

                if len(points) > 0:
                    points_str = ' '.join([f"{x},{y}" for x, y in points])
                    ET.SubElement(blob_group, 'polygon', {
                        'points': points_str,
                        'fill': color_hex,
                        'fill-opacity': '0.6',
                        'stroke': color_hex,
                        'stroke-width': '2'
                    })

                # Add inner contours (holes)
                for inner_contour in blob.inner_contours:
                    if georef and transform:
                        inner_points = [transform * (x, y) for x, y in inner_contour]
                    else:
                        inner_points = list(inner_contour)

                    if len(inner_points) > 0:
                        inner_points_str = ' '.join([f"{x},{y}" for x, y in inner_points])
                        ET.SubElement(blob_group, 'polygon', {
                            'points': inner_points_str,
                            'fill': 'white',
                            'stroke': color_hex,
                            'stroke-width': '2'
                        })

                # Add labels if selected
                if self.options["export_labels"] > 0:
                    label = ""
                    if self.options["export_labels"] == 1:  # Class Name
                        label = blob.class_name
                        # Shorten label if needed
                        if self.options["export_shorten"] and len(label) > self.options["export_shorten_length"]:
                            label = label[:self.options["export_shorten_length"]]
                    elif self.options["export_labels"] == 2:  # Region ID
                        label = blob.id
                        
                    x, y = blob.centroid
                    if georef and transform:
                        x, y = transform * (x, y)
                    
                    text_elem = ET.SubElement(blob_group, 'text', {
                        'x': str(x),
                        'y': str(y),
                        'text-anchor': 'middle',
                        'dominant-baseline': 'middle',
                        'font-size': str(text_height_scale * 22.0),
                        'fill': '#000000',
                        'stroke': '#ffffff',
                        'stroke-width': '0.5'
                    })
                    text_elem.text = str(label)

            # Add grid if selected
            if self.options["export_grid"]:
                if self.activeviewer.image.grid is not None:
                    grid = self.activeviewer.image.grid
                    
                    # Get grid dimensions
                    cell_width = grid.width / grid.ncol
                    cell_height = grid.height / grid.nrow

                    # Iterate through the grid cells
                    for r in range(grid.nrow):
                        for c in range(grid.ncol):
                            value = grid.cell_values[r, c]
                            if value > 0:  # Only draw cells with a state > 0
                                x1 = grid.offx + c * cell_width
                                y1 = grid.offy + r * cell_height
                                x2 = x1 + cell_width
                                y2 = y1 + cell_height

                                if georef and transform:
                                    p1 = transform * (x1, y1)
                                    p2 = transform * (x2, y1)
                                    p3 = transform * (x2, y2)
                                    p4 = transform * (x1, y2)
                                else:
                                    p1 = (x1, y1)
                                    p2 = (x2, y1)
                                    p3 = (x2, y2)
                                    p4 = (x1, y2)

                                points_str = f"{p1[0]},{p1[1]} {p2[0]},{p2[1]} {p3[0]},{p3[1]} {p4[0]},{p4[1]}"
                                ET.SubElement(grid_group, 'polygon', {
                                    'points': points_str,
                                    'fill': 'none',
                                    'stroke': '#cccccc',
                                    'stroke-width': '1'
                                })

                    # Add notes to the SVG file
                    for note in grid.notes:
                        x, y, text = note["x"], note["y"], note["txt"]
                        if georef and transform:
                            x, y = transform * (x, y)
                        
                        text_elem = ET.SubElement(grid_group, 'text', {
                            'x': str(x),
                            'y': str(y),
                            'text-anchor': 'middle',
                            'dominant-baseline': 'middle',
                            'font-size': '10',
                            'fill': '#000000'
                        })
                        text_elem.text = text

            # Convert to pretty-printed string and save
            rough_string = ET.tostring(svg, encoding='unicode')
            reparsed = minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ")
            
            # Remove extra blank lines
            pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
            
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)

            # Show a confirmation message box
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Successful")
            msgBox.setText("SVG file exported successfully!")
            msgBox.exec()
            return

        except Exception as e:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Failed")
            msgBox.setText("Error exporting SVG file: " + str(e))
            msgBox.exec()
            return
