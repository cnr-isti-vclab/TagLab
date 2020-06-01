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
from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QSizePolicy, QLabel, QTableView, QPushButton, QHBoxLayout, QVBoxLayout
from pathlib import Path
import os

path = Path(__file__).parent.absolute()
imdir = str(path)
imdir =imdir.replace('source', '')

class QtComparePanel(QWidget):

    hideAnnotations = pyqtSignal(int)
    showAnnotations = pyqtSignal(int)

    def __init__(self, parent=None):
        super(QtComparePanel, self).__init__(parent)

        self.visibility_flags = []
        self.visibility_buttons = []
        self.labels_projects = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(100)

        self.data_table = QTableView()

        layout = QVBoxLayout()
        layout.addWidget(self.data_table)
        self.setLayout(layout)

        self.project = None


    def setProject(self, project):

        self.project = project


