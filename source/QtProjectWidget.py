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
# GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.


from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import  QWidget,  QLabel,  QPushButton, QVBoxLayout, QListWidget, QMessageBox

class QtProjectWidget(QWidget):

    projectChanged = pyqtSignal()    #signal emitted when a map is added/removed
    mapChanged = pyqtSignal(map)     #signal emitted when a map is edited

    def __init__(self, project, parent=None):
        super(QtProjectWidget, self).__init__(parent)

        self.project = project
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignRight)
        layout.addWidget(QLabel("Project structure:"))

        newImage = QPushButton("New map...")
        newImage.clicked.connect(self.newImage)
        layout.addWidget(newImage)

        editImage = QPushButton("Edit map...")
        editImage.clicked.connect(self.editImage)
        layout.addWidget(editImage)

        deleteImage = QPushButton("Delete map...")
        deleteImage.clicked.connect(self.deleteImage)
        layout.addWidget(deleteImage)



        self.mapList = QListWidget()
        self.populateMapList()

        layout.addWidget(self.mapList)

        self.setLayout(layout)
        self.setWindowTitle("Project Structure")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


    def populateMapList(self):
        #clear all items
        self.mapList.clear()

        row = 0
        for img in self.project.images:
            self.mapList.addItem(img.name + " " + img.acquisition_date + " "  + str(img.map_px_to_mm_factor))

    @pyqtSlot()
    def newImage(self):
        print("new")
        pass

    @pyqtSlot()
    def editImage(self):
        print("edit")
        pass

    @pyqtSlot()
    def deleteImage(self):
        imgs = self.mapList.selectionModel().selectedIndexes()
        if len(imgs) == 0:
            return
        img = self.project.images[imgs[0].row()]
        reply = QMessageBox.question(self, "Deleting map",
                                     "About to delete map: " + img.name + ". Are you sure?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self.project.deleteImage(img)
        self.populateMapList()