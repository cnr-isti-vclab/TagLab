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


from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal, QEvent
from PyQt5.QtWidgets import QGridLayout, QWidget, QScrollArea,QGroupBox, QColorDialog, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout, QTextEdit, QTableWidget, QTableWidgetItem, QFrame
import json
import os
from source.CustomData import CustomData
from copy import deepcopy

class QtCustomDataWidget(QWidget):

    closewidget = pyqtSignal()

    def __init__(self, dir, project, parent=None):
        super(QtCustomDataWidget, self).__init__(parent)

        self.taglab_dir = dir
        self.project = project

        self.custom_data = deepcopy(project.custom_data)

#        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        #top toolbar
        toolbar_layout = QHBoxLayout()

        button_new = QPushButton("New")
        button_new.clicked.connect(self.newCustomData)
        toolbar_layout.addWidget(button_new)

        button_load = QPushButton("Load")
        button_load.clicked.connect(self.loadCustomData)
        toolbar_layout.addWidget(button_load)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.saveCustomData)
        toolbar_layout.addWidget(btn_save)

        layout.addLayout(toolbar_layout)


        #name & description

        name_layout = QGridLayout()
        name_layout.addWidget(QLabel("Custom data name:"), 0, 0)

        edit_name = QLineEdit()
        edit_name.setPlaceholderText("Name of the custom data")
        edit_name.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_name.setFixedWidth(350)
        edit_name.setText(self.custom_data.name)
        name_layout.addWidget(edit_name, 0, 1, 2, 1)


        name_layout.addWidget(QLabel("Description:"), 1, 0)

        edit_description = QTextEdit()
        edit_description.setPlaceholderText("Type a description of your custom data")
        edit_description.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_description.setFixedWidth(350)
        edit_description.setMaximumHeight(100)
        edit_description.setText(self.custom_data.description)

        name_layout.addWidget(edit_description, 1, 1, 2, 1)

        layout.addLayout(name_layout)


        left_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Min", "Max", "Values"])
        left_layout.addWidget(self.table)


        #edit fields
        edit_layout = QHBoxLayout()

        self.editName = QLineEdit()
        self.editName.setPlaceholderText("Name")
        self.editName.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_layout.addWidget(self.editName)


        self.editType = QComboBox()
        self.editType.addItems(['string', 'boolean', 'number', 'keyword']);
        self.editType.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editType.activated[str].connect(self.updateFieldType)
        edit_layout.addWidget(self.editType)


        self.editMin = QLineEdit()
        self.editMin.setPlaceholderText("Min")

        #self.editB.setFixedWidth(40)
        self.editMin.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_layout.addWidget(self.editMin)


        self.editMax = QLineEdit()
        self.editMax.setPlaceholderText("Max")

        #self.editB.setFixedWidth(40)
        self.editMax.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_layout.addWidget(self.editMax)

        self.editValues = QLineEdit()
        self.editMax.setPlaceholderText("List of keywords")
        self.editValues.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_layout.addWidget(self.editValues, 1)




        edit_layout.addWidget(self.editName)

        left_layout.addLayout(edit_layout)


        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignBottom)


        btnRemove = QPushButton("Delete")
        btnRemove.clicked.connect(self.removeField)
        right_layout.addWidget(btnRemove)

        btnAdd = QPushButton("Add")
        btnAdd.setStyleSheet("background-color: rgb(55,55,55);")
        btnAdd.clicked.connect(self.addField)
        right_layout.addWidget(btnAdd)


        btnOk = QPushButton("Update")
        btnOk.clicked.connect(self.editField)
        right_layout.addWidget(btnOk)


        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(left_layout);
        bottom_layout.addLayout(right_layout);

        layout.addLayout(bottom_layout)


        line = QFrame()

        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken);
        line.setLineWidth(1)
        layout.addWidget(line)


        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)
        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self.apply)
        buttons_layout.addWidget(btn_apply)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.apply)
        buttons_layout.addWidget(btn_cancel)

        layout.addLayout(buttons_layout)

#
        self.setLayout(layout)

        self.setWindowTitle("Edit Custom Data")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.selection_index = -1

        self.createFields()

    @pyqtSlot()
    def apply(self):
        self.project.custom_data = deepcopy(self.custom_data)
        self.close()

    def cancel(self):
        self.close()

    #def closeEvent(self, event):
    #    self.closewidget.emit()
    #    super(QtCustomDataWidget, self).closeEvent(event)


    @pyqtSlot()
    def newCustomData(self):
        self.labels = CustomData()

    @pyqtSlot()
    def loadCustomData(self):

        filters = "Custom Data (*.json)"
        filename, _ = QFileDialog.getOpenFileName(self, "Custom data", "", filters)
        if filename is None:
            return

        self.edit_load.setText(filename)

        data = CustomData()
        data.loadFromFile(filename)

        self.edit_dname.setText(data["name"])
        self.edit_description.document().setPlainText(data["description"])

        self.custom_data = data
        self.createFields()

#            for field in fields:
#               name= field['name']
#               type = field['type']
#               values = field['value']
#               mylabel = Label(id=id, name=name, fill=fill)
#               self.labels.append(mylabel)


    @pyqtSlot()
    def saveCustomData(self):

        #name = self.edit_dname.text()
        #description = self.edit_description.document().toPlainText()
        if self.custom_data.name == '':
            box = QMessageBox()
            box.setWindowTitle('TagLab')
            box.setText("Please enter a custom data name")
            box.exec()
            return

        dir = os.path.join(self.taglab_dir, self.custom_data.name + '.json')
        filters = "Custom Data (*.json)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save Custom Data", dir, filters)
        if filename is null:
            return

        self.custom_data.saveToFile(filename)




    def createFields(self):
        self.table.clearContents()
        self.table.setRowCount(len(self.custom_data.data))
        row = 0
        for field in self.custom_data.data:
            self.table.setItem(row, 0, QTableWidgetItem(field.name))



    @pyqtSlot()
    def addField(self):
        #validate text
        name = self.editFieldName.text()
        if name == '':
            return self.message("Please choose a field name")
        if self.custom_data.has(name):
            return self.message("Duplicated field name...")

        type = self.edit

    @pyqtSlot()
    def editField(self):
        row = self.selectedRow()

        if row < 0:
            return self.message("Please, select a label to modify")

#        field = self.
#            label = self.labels[self.selection_index]
#            label.name = self.editFieldName.text()


    @pyqtSlot()
    def removeField (self):
        row = self.selectedRow()

        if row < 0:
            return self.message("Please, select a label to delete")


        label = self.labels[self.selection_index]
        self.labels.remove(label)
        self.createAllLabels()
        self.selection_index = -1



    @pyqtSlot()
    def updateFieldType(self):
        type = self.editType.currentText()

        self.editMin.clear()
        self.editMax.clear()
        self.editValues.clear()

        self.editMin.setEnabled(type == "float")
        self.editMax.setEnabled(type == "float")
        
        self.editValues.setEnabled(type == "keywod")


#    def eventFilter(self, object, event):

#        if type(object) == QLabel and event.type() == QEvent.MouseButtonDblClick:
#            self.highlightSelectedLabel(object)
#            return False

#        return False

    def highlightSelectedLabel(self, lbl_clicked):

        # reset the text of all the labels
        for lbl in self.label_name:
            lbl.setStyleSheet("border: none; color: lightgray;")

        # highlight the selected label
        txt = lbl_clicked.text()
        lbl_clicked.setStyleSheet("border: 1 px; font-weight: bold; color: white;")

        # pick corresponding color button
        index = self.label_name.index(lbl_clicked)
        btn_clicked = self.label_color[index]

        # update visualization
        self.editFieldName.setText(txt)


        self.selection_index = index



#    @pyqtSlot(int,int,int,str)
#    def createField(self, entry):

        # lbl_name = QLabel(entry.name)
        # lbl_name.setStyleSheet("border: none; color: lightgray;")
        # lbl_name.setFixedHeight(20)
        # #lbl_name.installEventFilter(self)

        # self.label_layout = QHBoxLayout()
        # self.label_layout.addWidget(lbl_name)

        # self.fields_layout.addLayout(self.label_layout)

        # self.editFieldName.setText('')

        # text = "QPushButton:flat {background-color: rgb(255,255,255); border: none;}"
        # self.btn_selection_color.setStyleSheet(text)

    def selectedRow(self):
        selected = self.table.selectedRanges()
        if len(selected) == 0:
            return -1
        return selected[0].topRow()

    def message(self, text):
        box = QMessageBox()
        box.setText(text)
        box.exec()