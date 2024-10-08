#QUIRINO: This is the code for the message widget                                               

import os

from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QGroupBox, QGridLayout, QSizePolicy, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

from source.Annotation import Annotation
    

class QtMessageWidget(QWidget):

    def __init__(self, parent=None):
        super(QtMessageWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgba(40,40,40); color: white")

        

        self.setAutoFillBackground(False)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)

        #QUIRINO: NonModal to let click on map
        self.setWindowModality(Qt.NonModal)
        self.setWindowOpacity(0.5) 
        
        self.message = None
        
        self.message_box = QLabel()
        
        # self.message_box.setMaximumWidth(550)
        # self.message_box.setMaximumHeight(350)
        
        # self.message_box.setMinimumWidth(250)
        # self.message_box.setMinimumHeight(150)

        self.message_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.message_box.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.message_box.setWordWrap(False)
        
        self.message_box.setStyleSheet("background-color: rgba(0, 0, 0, 0.5); color: white;")
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.message_box)
        self.setLayout(self.layout)      
 
    def setMessage(self, message):
        self.message_box.setText(message)

    def move(self, x, y):
        super(QtMessageWidget, self).move(x, y)
