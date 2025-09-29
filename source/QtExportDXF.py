from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QComboBox, QCheckBox, QLabel, QPushButton, QButtonGroup, QSpinBox
from PyQt5.QtCore import Qt

class QtDXFExport(QDialog):  # Change QWidget to QDialog
    def __init__(self, parent=None):
        super().__init__(parent)
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
        
        # Layout for choosing elements
        elements_layout = QVBoxLayout()
        self.workspace_checkbox = QCheckBox("Image Workspace")
        self.workspace_checkbox.setToolTip("Export the image workspace as a rectangle in the DXF file.")
        self.workspace_checkbox.setChecked(True)
        elements_layout.addWidget(self.workspace_checkbox)
        self.workingarea_checkbox = QCheckBox("Working Area")
        self.workingarea_checkbox.setToolTip("Export the working area as a rectangle in the DXF file.")
        self.workingarea_checkbox.setChecked(False)
        self.workingarea_checkbox.setEnabled(False)  # Initially greyed out
        elements_layout.addWidget(self.workingarea_checkbox)
        self.grid_checkbox = QCheckBox("Grid")
        self.grid_checkbox.setToolTip("Export the grid as lines in the DXF file.")
        self.grid_checkbox.setChecked(False)        
        self.grid_checkbox.setEnabled(False)  # Initially greyed out        
        elements_layout.addWidget(self.grid_checkbox)
        main_layout.addLayout(elements_layout)

        # add horizontal line
        line = QLabel()
        line.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line)

        # Layout to choose blobs to export
        blobs_layout = QVBoxLayout()
        blobs_label = QLabel("Export Regions:")
        blobs_layout.addWidget(blobs_label)
        self.exportRegions = QComboBox()
        self.exportRegions.addItem("All Regions")
        self.exportRegions.addItem("Visible Regions")
        self.exportRegions.addItem("Selected Regions")
        self.exportRegions.setCurrentIndex(0)  # Default to "All Regions"
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
        self.exportLabels.setCurrentIndex(1)  # Default to "Class Name"
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
        line2 = QLabel()
        line2.setFrameStyle(QLabel.HLine | QLabel.Sunken)
        main_layout.addWidget(line2)

        # Others options layout
        others_layout = QVBoxLayout()
        # Georeferencing option
        self.georef_checkbox = QCheckBox("Use Georeferencing")
        self.georef_checkbox.setToolTip("Use georeferencing information from the image if available.")
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

        # Connect signals
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

