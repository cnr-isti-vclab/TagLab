from PyQt5.QtCore import Qt, QMargins, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue, QFont
from PyQt5.QtWidgets import QWidget, QGroupBox, QSizePolicy, QSlider, QLabel, QHBoxLayout, QVBoxLayout

class QtInfoWidget(QWidget):

    def __init__(self, parent=None):
        super(QtInfoWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        fnt = QFont("Calibri")
        self.lblMessage = QLabel("To begin, open an existing project or load a map.")
        self.lblMessage.setAlignment(Qt.AlignLeft)
        self.lblMessage.setMaximumHeight(50)
        self.lblMessage.setFont(fnt)
        self.lblMessage.setWordWrap(True)
        self.lblMessage.setStyleSheet("color: rgb(255,255,255)")

        layoutV = QVBoxLayout()
        layoutV.addWidget(self.lblMessage)

        self.groupBox = QGroupBox("Information/Warnings")
        self.groupBox.setFont(fnt)
        self.groupBox.setLayout(layoutV)

        layout = QVBoxLayout()
        layout.addWidget(self.groupBox)
        layout.setContentsMargins(QMargins(0, 0, 0, 0))
        self.setLayout(layout)

        self.setAutoFillBackground(True)

    def setInfoMessage(self, msg):

        self.lblMessage.setStyleSheet("color: rgb(255,255,255)")
        self.lblMessage.setText(msg)
        self.repaint()

    def setWarningMessage(self, msg):

        self.lblMessage.setStyleSheet("color: rgb(255,0,0)")
        self.lblMessage.setText(msg)
        self.repaint()

    def setReady(self):

        self.lineEdit.setStyleSheet("color: rgb(255,255,255)")
        self.lblMessage.setText("Ready.")

