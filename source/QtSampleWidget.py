from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QSlider,QGroupBox, QCheckBox,  QWidget, QDialog, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source.Annotation import Annotation
import numpy as np

from source import utils

class QtSampleWidget(QWidget):

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super(QtSampleWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        layoutHM = QHBoxLayout()

        self.lblMethod = QLabel("Sampling Method: ")

        self.comboMethod = QComboBox()
        self.comboMethod.setMinimumWidth(300)
        self.comboMethod.addItem('Grid Sampling')
        self.comboMethod.addItem('Uniform Sampling')
        self.comboMethod.addItem('Stratified Sampling')

        # self.comboMethod.currentIndexChanged.connect(self.)

        # layoutHM.setAlignment(Qt.AlignLeft)
        # layoutHM.addStretch()
        layoutHM.addWidget(self.lblMethod)
        layoutHM.addWidget(self.comboMethod)
        # layoutHM.addStretch()

        layoutHN = QHBoxLayout()
        self.lblNumber = QLabel("Number Of Points: ")
        self.editNumber = QLineEdit()
        self.editNumber.setPlaceholderText("Type Number Of Point")

        # layoutHN.setAlignment(Qt.AlignLeft)
        # layoutHN.addStretch()
        layoutHN.addWidget(self.lblNumber)
        layoutHN.addWidget(self.editNumber)
        # layoutHM.addStretch()

        #self.checkWA = QCheckBox("Use Current Working Area")

        layoutInfo = QVBoxLayout()
        layoutInfo.setAlignment(Qt.AlignLeft)
        layoutInfo.addLayout(layoutHM)
        layoutInfo.addLayout(layoutHN)
        #layoutInfo.addWidget(self.checkWA)


        layoutHB = QHBoxLayout()

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnOK = QPushButton("Apply")
        layoutHB.setAlignment(Qt.AlignRight)
        layoutHB.addStretch()
        layoutHB.addWidget(self.btnCancel)
        layoutHB.addWidget(self.btnOK)

        layout = QVBoxLayout()
        layout.addLayout(layoutInfo)
        layout.addLayout(layoutHB)
        self.setLayout(layout)

        self.setWindowTitle("Sampling Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)




    def closeEvent(self, event):
        self.closed.emit()

