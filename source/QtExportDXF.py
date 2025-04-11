from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QCheckBox, QLabel, QPushButton, QButtonGroup, QSpinBox
from PyQt5.QtCore import Qt

class QtDXFExportOptions(QDialog):  # Change QWidget to QDialog
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DXF Export Options")
        self.adjustSize()
        self.setSizeGripEnabled(True)

        # self.setFixedSize(300, 500)

        # Main layout
        main_layout = QVBoxLayout()
        
        # Create blobs layout
        blobs_layout = QVBoxLayout()
        blobs_layout.setSpacing(5)
        # Export blobs options
        blobs_label = QLabel("Export")
        blobs_layout.addWidget(blobs_label)
        

        self.blobs_group = QButtonGroup(self)
        all_blobs_radio = QRadioButton("All Regions")
        visible_blobs_radio = QRadioButton("Only Visible Regions")
        all_blobs_radio.setChecked(True)
        self.blobs_group.addButton(all_blobs_radio)
        self.blobs_group.addButton(visible_blobs_radio)
        
        blobs_layout.addWidget(all_blobs_radio)
        blobs_layout.addWidget(visible_blobs_radio)
        main_layout.addLayout(blobs_layout)

        main_layout.setSpacing(20)
        
        # Export class name options
        class_layout = QVBoxLayout()
        class_layout.setSpacing(5)
        class_name_label = QLabel("Export Labels")
        class_layout.addWidget(class_name_label)
        class_layout.setSpacing(5)


        self.class_name_group = QButtonGroup(self)
        full_name_radio = QRadioButton("Full Label Names")
        shortened_name_radio = QRadioButton("Shortened Label Names")
        full_name_radio.setChecked(True)
        self.class_name_group.addButton(full_name_radio)
        self.class_name_group.addButton(shortened_name_radio)

        class_layout.addWidget(full_name_radio)
        class_layout.addWidget(shortened_name_radio)
        class_layout.setSpacing(5)

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
        class_layout.addLayout(shortened_length_layout)

        # Enable/disable shortened name length based on selection
        shortened_name_radio.toggled.connect(self.toggleShortenedNameLength)

        main_layout.addLayout(class_layout)

        # Others options layout
        others_layout = QVBoxLayout()
        others_layout.setSpacing(10)

        # Georeferencing option
        self.georef_checkbox = QCheckBox("Use Georeferencing")
        self.georef_checkbox.setEnabled(False)  # Initially greyed out
        others_layout.addWidget(self.georef_checkbox)

        # Export grid option
        self.grid_checkbox = QCheckBox("Export Grid")
        others_layout.addWidget(self.grid_checkbox)

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

    def enable_georeferencing(self, enabled):
        """Enable or disable the georeferencing checkbox."""
        self.georef_checkbox.setEnabled(enabled)

    def toggleShortenedNameLength(self, checked):
        """Enable or disable the shortened name length spinbox."""
        self.shortened_length_label.setEnabled(checked)
        self.shortened_length_spinbox.setEnabled(checked)