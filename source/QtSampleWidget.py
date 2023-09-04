from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QSlider,QGroupBox, QMessageBox, QCheckBox,  QWidget, QDialog, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from source.Annotation import Annotation
import numpy as np

class QtSampleWidget(QWidget):


    # choosedSample = pyqtSignal(int)
    closewidget = pyqtSignal()
    validchoices= pyqtSignal()

    def __init__(self, parent=None):
        super(QtSampleWidget, self).__init__(parent)

        self.choosednumber = None
        self.offset = None

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        layoutHM = QHBoxLayout()

        self.lblMethod = QLabel("Sampling Method: ")

        self.comboMethod = QComboBox()
        self.comboMethod.setMinimumWidth(300)
        self.comboMethod.addItem('Grid Sampling')
        self.comboMethod.addItem('Uniform Sampling')


        layoutHM.addWidget(self.lblMethod)
        layoutHM.addWidget(self.comboMethod)


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


        layoutInfo = QVBoxLayout()
        layoutInfo.setAlignment(Qt.AlignLeft)
        layoutInfo.addLayout(layoutHM)
        layoutInfo.addLayout(layoutHN)
        layoutInfo.addLayout(layoutHOFF)


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

        if self.editNumber.text() == "" or self.editNumber.text() == 0 or self.editNumber.text().isnumeric() == False:
            msgBox = QMessageBox()
            msgBox.setText("Please, indicate the number of sampled points.")
            msgBox.exec()
            return
        else:
            self.choosednumber = int(self.editNumber.text())

        if self.editOFF.text() == "" or self.editOFF.text().isnumeric() == False:
            self.offset = 0
        else:
            self.offset = int(self.editOFF.text())

        self.validchoices.emit()


    def closeEvent(self,event):
        self.closewidget.emit()
        super(QtSampleWidget, self).closeEvent(event)

