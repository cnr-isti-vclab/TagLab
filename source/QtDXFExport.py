from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QCheckBox, QLabel, QPushButton, QButtonGroup, QSpinBox
from PyQt5.QtCore import Qt

class QtDXFExportOptions(QDialog):  # Change QWidget to QDialog
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DXF Export Options")
        self.setFixedSize(300, 500)

        # Main layout
        main_layout = QVBoxLayout()

        # Export blobs options
        blobs_label = QLabel("Export Blobs:")
        main_layout.addWidget(blobs_label)

        self.blobs_group = QButtonGroup(self)
        all_blobs_radio = QRadioButton("All Blobs")
        visible_blobs_radio = QRadioButton("Only Visible Blobs")
        all_blobs_radio.setChecked(True)
        self.blobs_group.addButton(all_blobs_radio)
        self.blobs_group.addButton(visible_blobs_radio)

        blobs_layout = QVBoxLayout()
        blobs_layout.addWidget(all_blobs_radio)
        blobs_layout.addWidget(visible_blobs_radio)
        main_layout.addLayout(blobs_layout)

        # Georeferencing option
        self.georef_checkbox = QCheckBox("Use Georeferencing (if available)")
        self.georef_checkbox.setEnabled(False)  # Initially greyed out
        main_layout.addWidget(self.georef_checkbox)

        # Export grid option
        self.grid_checkbox = QCheckBox("Export Grid")
        main_layout.addWidget(self.grid_checkbox)

        # Export class name options
        class_name_label = QLabel("Export Class Names:")
        main_layout.addWidget(class_name_label)

        self.class_name_group = QButtonGroup(self)
        full_name_radio = QRadioButton("Full Class Names")
        shortened_name_radio = QRadioButton("Shortened Class Names")
        full_name_radio.setChecked(True)
        self.class_name_group.addButton(full_name_radio)
        self.class_name_group.addButton(shortened_name_radio)

        class_name_layout = QVBoxLayout()
        class_name_layout.addWidget(full_name_radio)
        class_name_layout.addWidget(shortened_name_radio)
        main_layout.addLayout(class_name_layout)

        # Shortened class name length option
        self.shortened_length_label = QLabel("Initial characters:")
        self.shortened_length_label.setEnabled(False)
        self.shortened_length_spinbox = QSpinBox()
        self.shortened_length_spinbox.setRange(1, 10)
        self.shortened_length_spinbox.setValue(5)
        self.shortened_length_spinbox.setEnabled(False)

        shortened_length_layout = QHBoxLayout()
        shortened_length_layout.addWidget(self.shortened_length_label)
        shortened_length_layout.addWidget(self.shortened_length_spinbox)
        main_layout.addLayout(shortened_length_layout)

        # Enable/disable shortened name length based on selection
        shortened_name_radio.toggled.connect(self.toggleShortenedNameLength)

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

    def enable_georeferencing(self, enabled):
        """Enable or disable the georeferencing checkbox."""
        self.georef_checkbox.setEnabled(enabled)

    def toggleShortenedNameLength(self, checked):
        """Enable or disable the shortened name length spinbox."""
        self.shortened_length_label.setEnabled(checked)
        self.shortened_length_spinbox.setEnabled(checked)