from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QWidget, QFileDialog, QApplication
from PyQt5.QtWidgets import QComboBox, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

import os


class QtExportCoralNetDataWidget(QWidget):
    closewidget = pyqtSignal()
    validchoices = pyqtSignal()

    def __init__(self, parent=None):
        super(QtExportCoralNetDataWidget, self).__init__(parent)

        # Parameters
        self.output_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.output_dir = f"{self.output_dir}\\temp"
        self.tile_size = 4096

        # Style for the widget
        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        # Directory Path
        layout_dir = QHBoxLayout()
        self.lblDir = QLabel("Output Directory: ")
        self.editDir = QLineEdit()
        self.editDir.setText(f"{self.output_dir}")
        self.btnBrowseDir = QPushButton("Browse")
        self.btnBrowseDir.clicked.connect(self.get_directory)
        layout_dir.addWidget(self.lblDir)
        layout_dir.addWidget(self.editDir)
        layout_dir.addWidget(self.btnBrowseDir)

        # Tile Size
        layout_tile = QHBoxLayout()
        self.lblTileSize = QLabel("Tile Size (px): ")
        self.editTileSize = QLineEdit()
        self.editTileSize.setText(f"{self.tile_size}")
        layout_tile.addWidget(self.lblTileSize)
        layout_tile.addWidget(self.editTileSize)

        layout_info = QVBoxLayout()
        layout_info.setAlignment(Qt.AlignLeft)
        layout_info.addLayout(layout_dir)
        layout_info.addLayout(layout_tile)

        # Buttons
        layout_buttons = QHBoxLayout()
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnOK = QPushButton("Apply")
        self.btnOK.clicked.connect(self.apply)
        layout_buttons.setAlignment(Qt.AlignRight)
        layout_buttons.addStretch()
        layout_buttons.addWidget(self.btnCancel)
        layout_buttons.addWidget(self.btnOK)

        # Final layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout_info)
        main_layout.addSpacing(20)
        main_layout.addLayout(layout_buttons)
        self.setLayout(main_layout)

        self.setWindowTitle("Export CoralNet Data")
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowCloseButtonHint |
                            Qt.WindowTitleHint)

    @pyqtSlot()
    def get_directory(self):
        """

        """
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.editDir.setText(directory)

    @pyqtSlot()
    def apply(self):
        """

        """
        box = QMessageBox()
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            tile_size = int(self.editTileSize.text())

            # Check that tile sizes are correct
            if tile_size < 224 or tile_size > 8000:
                raise Exception("Tile size must be within [224 - 8000]")

            self.tile_size = tile_size
            self.output_dir = self.editDir.text()

        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

        try:
            # Get the channel and annotations
            channel = self.parent().activeviewer.image.getRGBChannel()
            annotations = self.parent().activeviewer.annotations

            # Get the working area (if none, whole ortho is used)
            working_area = self.parent().project.working_area

            # Export the data
            output_dir, csv_file = self.parent().activeviewer.annotations.exportCoralNetData(self.output_dir,
                                                                                             channel,
                                                                                             annotations,
                                                                                             working_area)

            self.close()
            box.setText(f"Exported data to {os.path.basename(output_dir)}")

        except Exception as e:
            box.setText(f"Failed to export data to CoralNet format! {e}")

        box.exec()
        QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        """

        """
        super().closeEvent(event)
