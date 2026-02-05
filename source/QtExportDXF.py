from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QVBoxLayout, QHBoxLayout, QComboBox, QCheckBox, QLabel, QPushButton, QSpinBox, QMessageBox
import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.entities import Layer

class QtDXFExport(QDialog):  # Change QWidget to QDialog

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
        self.setWindowTitle("DXF Export Options")
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
        self.workspace_checkbox.setToolTip("Export the image workspace as a rectangle in the DXF file.")
        self.workspace_checkbox.setChecked(self.options["export_workspace"])
        elements_layout.addWidget(self.workspace_checkbox)
        self.workingarea_checkbox = QCheckBox("Working Area")
        self.workingarea_checkbox.setToolTip("Export the working area as a rectangle in the DXF file.")
        self.workingarea_checkbox.setChecked(self.options["export_workingarea"])
        self.workingarea_checkbox.setEnabled(False)  # Initially greyed out
        elements_layout.addWidget(self.workingarea_checkbox)
        self.grid_checkbox = QCheckBox("Grid")
        self.grid_checkbox.setToolTip("Export the grid as lines in the DXF file.")
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
        # Proceed with DXF export
        self.export_dxf()


    # Function to perform the DXF export based on selected options
    def export_dxf(self):
        # Open a file dialog to select the output file
        filters = "DXF (*.dxf)"
        output_filename, _ = QFileDialog.getSaveFileName(self, "Save DXF File As", self.taglab_dir, filters)
        if not output_filename: return # no file selected, abort
        if not output_filename.lower().endswith('.dxf'):
            output_filename += '.dxf'
        
        # Create a new DXF document
        doc = ezdxf.new()
        msp = doc.modelspace()
        # Remove the default "defpoints" layer if it exists, as we are not using it
        if doc.layers.has_entry("defpoints"):
            doc.layers.remove("defpoints")
        
        # Register application for XDATA
        if 'TAGLAB' not in doc.appids:
            doc.appids.new('TAGLAB')

        georef = None # Initialize georef to None
        text_height_scale = 1.0 # Default text height scale

        try:
            # Check if georeferencing information is available and process accordingly

            if self.options["use_georef"] and hasattr(self.activeviewer.image, 'georef_filename') and self.activeviewer.image.georef_filename:
                georef, transform = rasterops.load_georef(self.activeviewer.image.georef_filename)
                text_height_scale = max(abs(transform.a), abs(transform.e))

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
                    (0, self.activeviewer.image.height),
                    (0, 0)
                ]
                if georef:
                    map_outline = [transform * (x, y) for x, y in map_outline]
                msp.add_lwpolyline(
                    map_outline,
                    close=True,
                    dxfattribs={'layer': '0', 'linetype': 'SOLID', 'color': 7, 'lineweight': 3}
                )
            # Add working area outline if selected
            if self.options["export_workingarea"] and self.project.working_area is not None:
                map_outline = [
                    (self.project.working_area[1], self.project.working_area[0]),
                    (self.project.working_area[1] + self.project.working_area[2], self.project.working_area[0]),
                    (self.project.working_area[1] + self.project.working_area[2], self.project.working_area[0] + self.project.working_area[3]),
                    (self.project.working_area[1], self.project.working_area[0] + self.project.working_area[3]),
                    (self.project.working_area[1], self.project.working_area[0])
                ]
                if georef:
                    map_outline = [transform * (x, y) for x, y in map_outline]
                else:
                    map_outline = [(x, self.activeviewer.image.height - y) for x, y in map_outline] # Invert Y-axis
                msp.add_lwpolyline(
                    map_outline,
                    close=True,
                    dxfattribs={'layer': '0', 'linetype': 'DASHED', 'color': 3, 'lineweight': 3 }
                )

            # Add blobs
            for blob in exported_blobs:
                layer_name = blob.class_name
                col = self.project.labels[blob.class_name].fill
                color_code = ezdxf.colors.rgb2int(col)

                if not doc.layers.has_entry(layer_name):
                    doc.layers.new(name=layer_name, dxfattribs={'true_color': color_code})

                if georef:
                    points = [transform * (x, y) for x, y in blob.contour]
                else:
                    points = [(x, self.activeviewer.image.height - y) for x, y in blob.contour] # Invert Y-axis

                if points:
                    polyline = msp.add_lwpolyline(
                        points,
                        close=True,
                        dxfattribs={'layer': layer_name}
                    )
                    
                    # Add XDATA with notes and custom attributes
                    xdata = [(1001, 'TAGLAB'), (1000, f'region_id:{blob.id}')]
                    
                    # Add note if it exists
                    if blob.note and blob.note.strip():
                        xdata.append((1000, f'note:{blob.note}'))
                    
                    # Add custom attributes from blob.data
                    if blob.data:
                        for key, value in blob.data.items():
                            xdata.append((1000, f'{key}:{value}'))
                    
                    polyline.set_xdata('TAGLAB', xdata)

                for inner_contour in blob.inner_contours:
                    if georef:
                        inner_points = [transform * (x, y) for x, y in inner_contour]
                    else:
                        inner_points = [(x, self.activeviewer.image.height - y) for x, y in inner_contour] # Invert Y-axis

                    if inner_points:
                        msp.add_lwpolyline(inner_points, close=True, dxfattribs={'layer': layer_name})

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
                    if georef:
                        x, y = transform * (x, y)
                    else:
                        y = self.activeviewer.image.height - y # Invert Y-axis
                    msp.add_text(
                        label, height=text_height_scale * 22.0,
                        dxfattribs={'layer': layer_name}
                    ).set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)

            # Add grid if selected
            if self.options["export_grid"]:
                if self.activeviewer.image.grid is not None:
                    grid = self.activeviewer.image.grid
                    grid_layer_name = "Grid"
                    
                    # Create a new layer for the grid if it doesn't exist
                    if not doc.layers.has_entry(grid_layer_name):
                        doc.layers.new(name=grid_layer_name, dxfattribs={'color': 8})  # light gray color for the grid
                    
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

                                if georef:
                                    # Transform the coordinates if georeferenced
                                    p1 = transform * (x1, y1)
                                    p2 = transform * (x2, y1)
                                    p3 = transform * (x2, y2)
                                    p4 = transform * (x1, y2)
                                else:
                                    # Invert Y-axis if not georeferenced
                                    height = self.activeviewer.image.height
                                    p1 = (x1, height - y1)
                                    p2 = (x2, height - y1)
                                    p3 = (x2, height - y2)
                                    p4 = (x1, height - y2)

                                # Add the cell as a polyline
                                msp.add_lwpolyline(
                                    [p1, p2, p3, p4, p1],  # Close the polyline
                                    close=True,
                                    dxfattribs={'layer': grid_layer_name}
                                )

                    # Add notes to the DXF file
                    for note in grid.notes:
                        x, y, text = note["x"], note["y"], note["txt"]
                        if georef:
                            x, y = transform * (x, y)
                        else:
                            y = self.activeviewer.image.height - y
                        msp.add_text(
                            text, height=10.0,  # Adjust text height as needed
                            dxfattribs={'layer': grid_layer_name}
                        ).set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)
                    
            # Save the DXF file
            doc.saveas(output_filename)

            # Show a confirmation message box
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Successful")
            msgBox.setText("DXF file exported successfully!")
            msgBox.exec()
            return

        except Exception as e:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Export Failed")
            msgBox.setText("Error exporting DXF file: " + str(e))
            msgBox.exec()
            return
    