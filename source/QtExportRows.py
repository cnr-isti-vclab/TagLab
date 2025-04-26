from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog
from PyQt5.QtCore import Qt


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
        self.browse_button.clicked.connect(self.browseDirectory)
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        layout.addLayout(path_layout)

        # File name
        name_layout = QHBoxLayout()
        self.name_label = QLabel("File Name:")
        self.name_input = QLineEdit(self)
        name_layout.addWidget(self.name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

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

    def browseDirectory(self):
        """Open a directory selection dialog."""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.path_input.setText(directory)

    def getExportOptions(self):
        """Return the selected export options."""
        return {
            "path": self.path_input.text(),
            "name": self.name_input.text(),
            "export_angles": self.angle_checkbox.isChecked(),
            "export_mask": self.mask_checkbox.isChecked(),
            "export_blobs": self.blob_checkbox.isChecked(),
            "export_skeleton": self.skeleton_checkbox.isChecked(),
            "export_branch_points": self.branch_points_checkbox.isChecked(),
            "export_edges": self.edges_checkbox.isChecked(),
        }