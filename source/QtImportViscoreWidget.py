from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QWidget, QFileDialog, QApplication
from PyQt5.QtWidgets import QComboBox, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

from source.Point import Point

import os
import numpy as np
import pandas as pd


class QtImportViscoreWidget(QWidget):
    closewidget = pyqtSignal()
    validchoices = pyqtSignal()

    def __init__(self, parent=None):
        super(QtImportViscoreWidget, self).__init__(parent)

        # Parameters
        self.csv_file = None
        self.scale_mm_px = None

        # Style for the widget
        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        # CSV File Path
        layoutHF = QHBoxLayout()

        self.lblCSV = QLabel("CSV File: ")
        self.editCSV = QLineEdit()
        self.btnBrowse = QPushButton("Browse")
        self.btnBrowse.clicked.connect(self.get_file)

        layoutHF.addWidget(self.lblCSV)
        layoutHF.addWidget(self.editCSV)
        layoutHF.addWidget(self.btnBrowse)

        # Scale (mm / px)
        layoutHS = QHBoxLayout()

        self.lblScale = QLabel("Scale (mm/px): ")
        self.editScale = QLineEdit()
        self.editScale.setText("5")

        layoutHS.addWidget(self.lblScale)
        layoutHS.addWidget(self.editScale)

        layoutInfo = QVBoxLayout()
        layoutInfo.setAlignment(Qt.AlignLeft)
        layoutInfo.addLayout(layoutHF)
        layoutInfo.addLayout(layoutHS)

        # Buttons
        layoutHB = QHBoxLayout()

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnOK = QPushButton("Apply")
        self.btnOK.clicked.connect(self.apply)
        layoutHB.setAlignment(Qt.AlignRight)
        layoutHB.addStretch()
        layoutHB.addWidget(self.btnCancel)
        layoutHB.addWidget(self.btnOK)

        # Final layout
        layout = QVBoxLayout()
        layout.addLayout(layoutInfo)
        layout.addSpacing(20)
        layout.addLayout(layoutHB)
        self.setLayout(layout)

        self.setWindowTitle("Import Viscore Points")
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowCloseButtonHint |
                            Qt.WindowTitleHint)

    def get_file(self):
        """

        """
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.editCSV.setText(file_path)

    @pyqtSlot()
    def apply(self):
        """

        """
        box = QMessageBox()
        QApplication.setOverrideCursor(Qt.WaitCursor)

        try:
            # Get the scale
            m_to_px = float(self.editScale.text()) / 10000

            # Get the current orthomosaic
            channel = self.parent().activeviewer.image.getRGBChannel()
            width = channel.qimage.width()
            height = channel.qimage.height()

            # Get the path and basename
            image_file = channel.filename
            _, image_name = os.path.split(image_file)
            basename = os.path.basename(image_name).split('.')[0]

            # Read in the csv file
            csv_file = self.editCSV.text()

            if not os.path.exists(csv_file):
                raise Exception("Provided file does not exist")

            points = pd.read_csv(csv_file, sep=",", header=0)
            points = points.loc[:, ~points.columns.str.contains('^Unnamed')]

            # Check to see if the csv file has the expected columns
            assert 'X' in points.columns, "'X' not in file!"
            assert 'Y' in points.columns, "'Y' not in file!"
            assert 'Label' in points.columns, "'Label' not in file!"

            # Subset to get just the points
            points = points[['X', 'Y', 'Label']]
            x = points.X.values
            y = points.Y.values

            # Transform points
            points['Column'] = (x / m_to_px).round().astype(int)
            points['Row'] = np.abs(height - (y / m_to_px).round().astype(int))

            if not all(0 <= points['Column'] <= width) or not all(0 <= points['Row'] <= height):
                raise Exception("Points fall outside of orthomosaic")

            for i, r in points.iterrows():

                coordx = int(r['Column'])
                coordy = int(r['Row'])
                class_name = r['Label']

                point_ann = Point(coordx, coordy, class_name, self.parent().activeviewer.annotations.getFreePointId())
                self.parent().activeviewer.annotations.addPoint(point_ann)

            # Close if successful
            self.close()
            box.setText(f"Imported Viscore points successfully!")

        except Exception as e:
            box.setText(f"Failed to import Viscore points! {e}")

        box.exec()
        QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        """

        """
        super().closeEvent(event)


