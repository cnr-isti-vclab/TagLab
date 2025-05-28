from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog, QComboBox
from PyQt5.QtCore import Qt
import ezdxf 
import numpy as np

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

    def DXFExport(self, file_path, skel, branch, edges):
        # Export skeleton, branch points, and edges to a DXF file, each in a different layer.
        
        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()

        # Skeleton layer
        if skel:
            doc.layers.add("Skeleton", color=1)
        
            skeleton = self.skeleton
            h, w = skeleton.shape
            for y, x in zip(*np.where(skeleton)):
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx_ = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx_ < w and skeleton[ny, nx_]:
                            # To avoid duplicate lines, only draw if neighbor is "after" current
                            if (ny > y) or (ny == y and nx_ > x):
                                msp.add_line((x, y), (nx_, ny), dxfattribs={"layer": "Skeleton"})


        # Branch points layer
        if branch:
            doc.layers.add("BranchPoints", color=2)
        
            # #Draw ALL the branch points
            # for (y, x) in self.branch_points:
            #     msp.add_circle((x, y), radius=1, dxfattribs={"layer": "BranchPoints"})
            
            # Draw branch points, if points are closer than 10 pixels, draw only one at the median position
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
                # Empty circle
                msp.add_circle((median_x, median_y), radius=1, dxfattribs={"layer": "BranchPoints"})
                drawn_points.append((median_y, median_x))

        # Edges layer
        if edges:
            doc.layers.add("Edges", color=3)
            for start, end, color, angle in self.edges:
                msp.add_line((start[0], start[1]), (end[0], end[1]), dxfattribs={"layer": "Edges"})

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