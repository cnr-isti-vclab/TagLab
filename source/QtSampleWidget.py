from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QSlider,QGroupBox, QMessageBox, QCheckBox,  QWidget, QDialog, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source.Annotation import Annotation
import numpy as np

from source import utils

class QtSampleWidget(QWidget):


    # choosedSample = pyqtSignal(int)
    closewidget = pyqtSignal()

    def __init__(self, parent=None):
        super(QtSampleWidget, self).__init__(parent)

        self.choosednumber = None
        self.myoffset = None

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        layoutHM = QHBoxLayout()

        self.lblMethod = QLabel("Sampling Method: ")

        self.comboMethod = QComboBox()
        self.comboMethod.setMinimumWidth(300)
        self.comboMethod.addItem('Grid Sampling')
        self.comboMethod.addItem('Uniform Sampling')
        # self.comboMethod.addItem('Stratified Sampling')

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

        layoutHN.addWidget(self.lblNumber)
        layoutHN.addWidget(self.editNumber)

        layoutHOFF = QHBoxLayout()
        self.lblOFF = QLabel("Offset (px): ")
        self.editOFF = QLineEdit()
        self.editOFF.setPlaceholderText("Type pixels of offset")

        layoutHOFF.addWidget(self.lblOFF)
        layoutHOFF.addWidget(self.editOFF)

        # layoutHN.setAlignment(Qt.AlignLeft)
        # layoutHN.addStretch()
        # layoutHM.addStretch()

        #self.checkWA = QCheckBox("Use Current Working Area")

        layoutInfo = QVBoxLayout()
        layoutInfo.setAlignment(Qt.AlignLeft)
        layoutInfo.addLayout(layoutHM)
        layoutInfo.addLayout(layoutHN)
        layoutInfo.addLayout(layoutHOFF)

        #layoutInfo.addWidget(self.checkWA)

        layoutHB = QHBoxLayout()

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnOK = QPushButton("Apply")
        self.btnOK.clicked.connect(self.apply)
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

    @pyqtSlot()
    def apply(self):

        self.choosednumber = None
        self.myoffset = 0

        if self.editNumber.text().isnumeric() == True and self.editOFF.text().isnumeric() == True:
            self.choosednumber = int(self.editNumber.text())
            self.myoffset = int(self.editOFF.text())

        else:
            msgBox = QMessageBox()
            msgBox.setText("Please, enter an integer number.")
            msgBox.exec()
            return


    def closeEvent(self,event):
        self.closewidget.emit()
        super(QtSampleWidget, self).closeEvent(event)

