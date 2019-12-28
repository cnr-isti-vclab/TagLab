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
from PyQt5.QtWidgets import QApplication, QWidget, QSizePolicy, QLabel, QToolButton, QPushButton, QHBoxLayout, QVBoxLayout
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

        self.annotations_loaded = 0
        self.max_annotations = 5

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(100)

        self.icon_eyeopen = QIcon(imdir+os.path.join("icons","eye.png"))
        self.icon_eyeclosed = QIcon(imdir+os.path.join("icons","cross.png"))

        labels_layout = QVBoxLayout()
        self.setLayout(labels_layout)

        CLASS_LABELS_HEIGHT = 20
        EYE_ICON_SIZE = 20

        for i in range(self.max_annotations):

            btnV = QPushButton()
            btnV.setFlat(True)
            btnV.setIcon(self.icon_eyeopen)
            btnV.setIconSize(QSize(EYE_ICON_SIZE, EYE_ICON_SIZE))
            btnV.setFixedWidth(CLASS_LABELS_HEIGHT)
            btnV.setFixedHeight(CLASS_LABELS_HEIGHT)
            btnV.clicked.connect(self.toggleVisibility)

            self.visibility_buttons.append(btnV)
            self.visibility_flags.append(True)

            if i == 0:
                label_projects = QLabel("<b>prova</b>")
            else:
                label_projects = QLabel("prova")

            self.labels_projects.append(label_projects)

            btnV.hide()
            label_projects.hide()

            layout = QHBoxLayout()
            layout.addWidget(btnV)
            layout.addWidget(label_projects)
            labels_layout.addLayout(layout)

        labels_layout.setSpacing(2)


    @pyqtSlot()
    def toggleVisibility(self):

        button_clicked = self.sender()

        index = self.visibility_buttons.index(button_clicked)

        if self.visibility_flags[index]:
            button_clicked.setIcon(self.icon_eyeclosed)
            self.visibility_flags[index] = False
            self.hideAnnotations.emit(index)
        else:
            button_clicked.setIcon(self.icon_eyeopen)
            self.visibility_flags[index] = True
            self.showAnnotations.emit(index)

    def setProject(self, project_name):

        project_name = os.path.basename(project_name)
        project_name = project_name.replace('.json', '')

        txt = "<b>" + project_name + "</b>"
        self.labels_projects[0].setText(txt)
        self.visibility_buttons[0].show()
        self.labels_projects[0].show()

        for i in range(1, self.max_annotations):
            self.visibility_buttons[i].hide()
            self.labels_projects[i].hide()

        self.annotations_loaded = 1

    def addProject(self, project_name):

        project_name = os.path.basename(project_name)
        project_name = project_name.replace('.json', '')

        idx = self.annotations_loaded
        self.labels_projects[idx].setText(project_name)
        self.labels_projects[idx].show()
        self.visibility_buttons[idx].show()

        self.annotations_loaded += 1


