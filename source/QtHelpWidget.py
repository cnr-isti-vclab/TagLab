# TagLab                                               
# A semi-automatic segmentation tool                                    
#
# Copyright(C) 2019                                         
# Visual Computing Lab                                           
# ISTI - Italian National Research Council                              
# All rights reserved.                                                      
                                                                          
# This program is free software; you can redistribute it and/or modify      
# it under the terms of the GNU General Public License as published by      
# the Free Software Foundation; either version 2 of the License, or         
# (at your option) any later version.                                       
                                                                           
# This program is distributed in the hope that it will be useful,           
# but WITHOUT ANY WARRANTY; without even the implied warranty of            
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             
#GNU General Public License (http://www.gnu.org/licenses/gpl.txt)          
# for more details.                                               

import os

from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QGroupBox, QGridLayout, QSizePolicy, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

from source.Annotation import Annotation

class QtHelpWidget(QWidget):

    def __init__(self, parent=None):
        super(QtHelpWidget, self).__init__(parent)

        self.setStyleSheet("background-color: rgba(40,40,40,100); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(440)
        self.setMinimumHeight(440)
        self.setAutoFillBackground(False)


        self.groupbox_proj = QGroupBox("Projects")
        self.gridlayout1 = QGridLayout()
        self.gridlayout1.setHorizontalSpacing(20)
        self.gridlayout1.addWidget(QLabel("New Project"), 0,0)
        self.gridlayout1.addWidget(QLabel("Open Project"), 1,0)
        self.gridlayout1.addWidget(QLabel("Save Project"), 2,0)
        self.gridlayout1.addWidget(QLabel("Save As.."), 3, 0)
        self.gridlayout1.addWidget(QLabel("Load Map"), 4,0)
        self.gridlayout1.addWidget(QLabel("<b>Ctrl+N</b>"), 0,1)
        self.gridlayout1.addWidget(QLabel("<b>Ctrl+O</b>"), 1,1)
        self.gridlayout1.addWidget(QLabel("<b>Ctrl+S</b>"), 2,1)
        self.gridlayout1.addWidget(QLabel("<b>Ctrl+Alt+S</b>"), 3,1)
        self.gridlayout1.addWidget(QLabel("<b>Ctrl+L</b>"), 4,1)
        self.groupbox_proj.setLayout(self.gridlayout1)

        # self.groupbox_tool = QGroupBox("Tools")
        # self.gridlayout2 = QGridLayout()
        # self.gridlayout2.setHorizontalSpacing(20)
        # self.gridlayout2.addWidget(QLabel("Active Pan Tool"), 0, 0)
        # self.gridlayout2.addWidget(QLabel("Active 4-clicks Tool"), 1,0)
        # self.gridlayout2.addWidget(QLabel("Active Positive/negative clicks Tool"), 2, 0)
        # self.gridlayout2.addWidget(QLabel("Active Freehand Tool"), 3, 0)
        # self.gridlayout2.addWidget(QLabel("Active Assign Tool"), 4, 0)
        # self.gridlayout2.addWidget(QLabel("Active Edit Border Tool"), 5, 0)
        # self.gridlayout2.addWidget(QLabel("Active Cut Tool"), 6, 0)
        # self.gridlayout2.addWidget(QLabel("Active Crack Tool"), 7, 0)
        # self.gridlayout2.addWidget(QLabel("Active Ruler Tool"), 8, 0)
        # self.gridlayout2.addWidget(QLabel("<b>1</b>"), 0, 1)
        # self.gridlayout2.addWidget(QLabel("<b>2</b>"), 1, 1)
        # self.gridlayout2.addWidget(QLabel("<b>3</b>"), 2, 1)
        # self.gridlayout2.addWidget(QLabel("<b>4</b>"), 3, 1)
        # self.gridlayout2.addWidget(QLabel("<b>5</b>"), 4, 1)
        # self.gridlayout2.addWidget(QLabel("<b>6</b>"), 5, 1)
        # self.gridlayout2.addWidget(QLabel("<b>7</b>"), 6, 1)
        # self.gridlayout2.addWidget(QLabel("<b>8</b>"), 7, 1)
        # self.gridlayout2.addWidget(QLabel("<b>9</b>"), 8, 1)

        # self.groupbox_tool.setLayout(self.gridlayout2)

        self.groupbox_labels = QGroupBox("Labels Operations")
        self.gridlayout3 = QGridLayout()
        self.gridlayout3.setHorizontalSpacing(20)
        self.gridlayout3.addWidget(QLabel("Assign"), 0, 0)
        self.gridlayout3.addWidget(QLabel("Fill"), 1, 0)
        self.gridlayout3.addWidget(QLabel("Delete"), 2, 0)
        self.gridlayout3.addWidget(QLabel("Merge"), 3, 0)
        self.gridlayout3.addWidget(QLabel("Divide"), 4, 0)
        self.gridlayout3.addWidget(QLabel("Subtract"), 5, 0)
        self.gridlayout3.addWidget(QLabel("Attach Borders"), 6, 0)
        self.gridlayout3.addWidget(QLabel("Refine Border"), 7,0)
        self.gridlayout3.addWidget(QLabel("Dilate Border"), 8, 0)
        self.gridlayout3.addWidget(QLabel("Erode Border"), 9, 0)
        self.gridlayout3.addWidget(QLabel("<b>A</b>"), 0, 1)
        self.gridlayout3.addWidget(QLabel("<b>F</b>"), 1, 1)
        self.gridlayout3.addWidget(QLabel("<b>DEL</b>"), 2, 1)
        self.gridlayout3.addWidget(QLabel("<b>M</b>"), 3, 1)
        self.gridlayout3.addWidget(QLabel("<b>D</b>"), 4, 1)
        self.gridlayout3.addWidget(QLabel("<b>S</b>"), 5, 1)
        self.gridlayout3.addWidget(QLabel("<b>B</b>"), 6, 1)
        self.gridlayout3.addWidget(QLabel("<b>R</b>"), 7, 1)
        self.gridlayout3.addWidget(QLabel("<b>+</b>"), 8, 1)
        self.gridlayout3.addWidget(QLabel("<b>-</b>"), 9, 1)
        self.groupbox_labels.setLayout(self.gridlayout3)

        self.groupbox_commands = QGroupBox("Commands")
        self.gridlayout4 = QGridLayout()
        self.gridlayout4.setHorizontalSpacing(20)
        self.gridlayout4.addWidget(QLabel("Select label"), 0, 0)
        self.gridlayout4.addWidget(QLabel("Multiple selection"), 1, 0)
        self.gridlayout4.addWidget(QLabel("Confirm Operation"), 2, 0)
        self.gridlayout4.addWidget(QLabel("Reset Operation"), 3, 0)
        self.gridlayout4.addWidget(QLabel("Undo Operation"), 4, 0)
        self.gridlayout4.addWidget(QLabel("Redo Operation"), 5, 0)
        self.gridlayout4.addWidget(QLabel("Toggle Fill"), 6, 0)
        self.gridlayout4.addWidget(QLabel("Toggle Boundaries"), 7, 0)
        self.gridlayout4.addWidget(QLabel("Toggle Ids"), 8, 0)
        self.gridlayout4.addWidget(QLabel("Toggle Grid"), 9, 0)
        self.gridlayout4.addWidget(QLabel("<b>Click</b>"), 0, 1)
        self.gridlayout4.addWidget(QLabel("<b>Click + Shift</b>"), 1, 1)
        self.gridlayout4.addWidget(QLabel("<b>SPACE</b>"), 2, 1)
        self.gridlayout4.addWidget(QLabel("<b>ESC</b>"), 3, 1)
        self.gridlayout4.addWidget(QLabel("<b>Ctrl+Z</b>"), 4, 1)
        self.gridlayout4.addWidget(QLabel("<b>Ctrl+Shift+Z</b>"), 5, 1)
        self.gridlayout4.addWidget(QLabel("<b>Q</b>"), 6, 1)
        self.gridlayout4.addWidget(QLabel("<b>W</b>"), 7, 1)
        self.gridlayout4.addWidget(QLabel("<b>E</b>"), 8, 1)
        self.gridlayout4.addWidget(QLabel("<b>G</b>"), 9, 1)

        self.groupbox_commands.setLayout(self.gridlayout4)

        layout_V1 = QVBoxLayout()
        layout_V1.addWidget(self.groupbox_proj)
        layout_V1.addWidget(self.groupbox_commands)

        main_layout = QHBoxLayout()
        main_layout.setAlignment(Qt.AlignRight)
        main_layout.addLayout(layout_V1)
        #main_layout.addWidget(self.groupbox_tool)
        main_layout.addWidget(self.groupbox_labels)

        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.close)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnClose)

        layoutF = QVBoxLayout()
        layoutF.addLayout(main_layout)
        layoutF.addLayout(buttons_layout)
        layoutF.setSpacing(3)
        self.setLayout(layoutF)

        self.setWindowTitle("Help")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

