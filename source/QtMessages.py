#QUIRINO: This is the code for the message widget                                               

import os

from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QGroupBox, QGridLayout, QSizePolicy, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

from source.Annotation import Annotation

class MessageSignal(QObject):
    messageChanged = pyqtSignal(str)
    

class QtMessageWidget(QWidget):

    def __init__(self, parent=None):
        super(QtMessageWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgba(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(250)
        self.setMinimumHeight(150)
        self.setMaximumWidth(800)
        self.setMaximumHeight(600)
        self.setAutoFillBackground(False)
        
        self.message = ""
        
        self.message_box = QLabel()
        self.message_box.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.message_box.setWordWrap(True)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        self.message_box.setText(self.message)
        
        self.message_box.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); color: white; padding: 5px;")
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.message_box)
        self.setLayout(self.layout)
        
        # Align the window to the top left corner
        self.move(50, 110)
        