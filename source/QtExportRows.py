from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog, QComboBox
# from PyQt5.QtCore import Qt
import ezdxf 
import numpy as np
import source.RasterOps as rasterops

class ExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Options")
        self.setModal(True)
        self.setMinimumWidth(400)

        # Layouts
        layout = QVBoxLayout()

        # Path selection
        path_layout = QHBoxLayout()
        self.path_label = QLabel("Export Path:")
        self.path_input = QLineEdit(self)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browseFile)
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        layout.addLayout(path_layout)

        # Format selection
        format_layout = QHBoxLayout()
        self.format_label = QLabel("File Format:")
        self.format_combo = QComboBox(self)
        self.format_combo.addItems([".dxf", ".png"])
        format_layout.addWidget(self.format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)
        self.format_label.hide()
        self.format_combo.hide()
        format_layout.setSpacing(10)
        
        # Export options
        self.angle_checkbox = QCheckBox("Export Angles")
        
        self.mask_checkbox = QCheckBox("Export Mask")

        self.blob_checkbox = QCheckBox("Export Blobs")
        
        self.skeleton_checkbox = QCheckBox("Export Skeleton")
        
        self.branch_points_checkbox = QCheckBox("Export Branch Points")
        
        self.edges_checkbox = QCheckBox("Export Edges")

        layout.addWidget(self.angle_checkbox)
        layout.addWidget(self.mask_checkbox)
        layout.addWidget(self.blob_checkbox)
        layout.addWidget(self.skeleton_checkbox)
        layout.addWidget(self.branch_points_checkbox)
        layout.addWidget(self.edges_checkbox)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def DXFExport(self, file_path, skel, branch, edges, blobs, georef, offset = [0, 0], img_size = (0,0)):
        # Export skeleton, branch points, and edges to a DXF file, each in a different layer.
        offset_x, offset_y = offset
        img_width, img_height = img_size

        text_height_scale = 1.0
        transform = None
        if georef is not None:
            georef_data, transform = rasterops.load_georef(georef)
            text_height_scale = max(abs(transform.a), abs(transform.e))

        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()

        map_outline = [
            (0, 0),
            (img_width, 0),
            (img_width, img_height),
            (0, img_height),
            (0, 0)
        ]

        if transform is not None:
            map_outline = [transform * (x, y) for x, y in map_outline]
        
        msp.add_lwpolyline(
            map_outline,
            close=True,
            dxfattribs={'layer': '0', 'color': 0}  # 0 is black in DXF color index
        )

        # Skeleton layer
        if skel and self.skeleton is not None :
            doc.layers.add("Skeleton", color=1)
        
            skeleton = self.skeleton
            h, w = skeleton.shape
            for y, x in zip(*np.where(skeleton)):
                x_global = x + offset_x
                y_global = y + offset_y
                y_flipped = img_height - y_global
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx_ = y + dy, x + dx
                        nx_global = nx_ + offset_x
                        ny_global = ny + offset_y
                        if 0 <= ny < h and 0 <= nx_ < w and skeleton[ny, nx_]:
                            # To avoid duplicate lines, only draw if neighbor is "after" current
                            if (ny > y) or (ny == y and nx_ > x):
                                if transform is not None:
                                    p1 = transform * (x_global, y_global)
                                    p2 = transform * (nx_global, ny_global)
                                else:
                                    p1 = (x_global, img_height - y_global)
                                    p2 = (nx_global, img_height - ny_global)
                                    # ny_flipped = img_height - ny_global
                                msp.add_line(p1, p2, dxfattribs={"layer": "Skeleton"})

        # Branch points layer
        if branch:
            doc.layers.add("BranchPoints", color=2)
        
            # #Draw ALL the branch points
            # for (y, x) in self.branch_points:
            #     x_global = x + offset_x
            #     y_global = y + offset_y
            #     y_flipped = img_height - y_global
            #     msp.add_circle((x_global, y_flipped), radius=1, dxfattribs={"layer": "BranchPoints"})
            
            # Draw branch points, if points are closer than 2 pixels, draw only one at the median position
            remaining_points = list(self.branch_points)
            drawn_points = []
            while remaining_points:
                (y, x) = remaining_points.pop(0)
                close_points = [(y, x)]
                to_remove = []
                for idx, (yy, xx) in enumerate(remaining_points):
                    if np.hypot(x - xx, y - yy) < 10:
                        close_points.append((yy, xx))
                        to_remove.append(idx)
                # Remove close points from remaining_points
                for idx in reversed(to_remove):
                    remaining_points.pop(idx)
                # Compute median position
                ys, xs = zip(*close_points)
                median_y = int(np.median(ys))
                median_x = int(np.median(xs))
                # Apply offset and flip y
                median_x_global = median_x + offset_x
                median_y_global = median_y + offset_y
                # median_y_flipped = img_height - median_y_global
                # # Empty circle
                # msp.add_circle((median_x_global, median_y_flipped), radius=1, dxfattribs={"layer": "BranchPoints"})
                # drawn_points.append((median_y_global, median_x_global))

                # msp.add_circle((median_x, median_y), radius=1, dxfattribs={"layer": "BranchPoints"})
                # drawn_points.append((median_y, median_x))

                if transform is not None:
                    center = transform * (median_x_global, median_y_global)
                    radius = 1 * text_height_scale
                else:
                    center = (median_x_global, img_height - median_y_global)
                    radius = 1
                msp.add_circle(center, radius=radius, dxfattribs={"layer": "BranchPoints"})


        # Edges layer
        if edges:
            doc.layers.add("Edges", color=3)
            for start, end, color, _, _ in self.edges:
                # msp.add_line((start[0], start[1]), (end[0], end[1]), dxfattribs={"layer": "Edges"})
                start_x_global = start[0] + offset_x
                start_y_global = start[1] + offset_y
                end_x_global = end[0] + offset_x
                end_y_global = end[1] + offset_y
                # start_y_flipped = img_height - start_y_global
                # end_y_flipped = img_height - end_y_global
                # msp.add_line((start_x_global, start_y_flipped), (end_x_global, end_y_flipped), dxfattribs={"layer": "Edges"})
                if transform is not None:
                    p1 = transform * (start_x_global, start_y_global)
                    p2 = transform * (end_x_global, end_y_global)
                else:
                    p1 = (start_x_global, img_height - start_y_global)
                    p2 = (end_x_global, img_height - end_y_global)
                msp.add_line(p1, p2, dxfattribs={"layer": "Edges"})
                
                # # Use truecolor for each edge if color is provided as RGB
                # if isinstance(color, (tuple, list)) and len(color) == 3:
                #     color_code = ezdxf.colors.rgb2int(tuple(int(max(0, min(255, v))) for v in color))
                #     msp.add_line(p1, p2, dxfattribs={"layer": "Edges", "true_color": color_code})
                # # elif isinstance(color, int) and 1 <= color <= 256:
                # #     msp.add_line(p1, p2, dxfattribs={"layer": "Edges", "color": color})
                # else:
                #     msp.add_line(p1, p2, dxfattribs={"layer": "Edges"})


        # Blobs layer
        if blobs:
            doc.layers.add("Blobs", color=4)
            for blob in self.blobs:
                if transform is not None:
                    points = [transform * (float(x), float(y)) for x, y in blob.contour]
                else:
                    points = [(float(x), float(img_height - y)) for x, y in blob.contour]
                # Optionally close the polyline if the contour is closed
                is_closed = np.allclose(points[0], points[-1])
                msp.add_lwpolyline(points, close=is_closed, dxfattribs={"layer": "Blobs"})

        doc.saveas(file_path)
        print(f"DXF exported to {file_path}")


    def browseFile(self):
        # Open a file save dialog.
        file_path, _ = QFileDialog.getSaveFileName(self, "Select File", "", "All Files (*)")
        if file_path:
            self.path_input.setText(file_path)

    def getExportOptions(self):
        #Return the selected export options.
        return {
            "path": self.path_input.text(),
            "format": self.format_combo.currentText(),
            "export_angles": self.angle_checkbox.isChecked(),
            "export_mask": self.mask_checkbox.isChecked(),
            "export_blobs": self.blob_checkbox.isChecked(),
            "export_skeleton": self.skeleton_checkbox.isChecked(),
            "export_branch_points": self.branch_points_checkbox.isChecked(),
            "export_edges": self.edges_checkbox.isChecked(),
        }