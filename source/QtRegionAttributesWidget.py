# TagLab
# A semi-automatic segmentation tool
#
# Copyright(C) 2021
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
import os, json, re
from source.RegionAttributes import RegionAttributes
from copy import deepcopy

class QtRegionAttributesWidget(QWidget):

    closed = pyqtSignal()

    def __init__(self, dir, project, parent=None):
        super(QtRegionAttributesWidget, self).__init__(parent)

        self.taglab_dir = dir
        self.project = project

        self.region_attributes = deepcopy(project.region_attributes)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        #top toolbar
        toolbar_layout = QHBoxLayout()

        button_new = QPushButton("New")
        button_new.clicked.connect(self.newRegionAttributes)
        toolbar_layout.addWidget(button_new)

        button_load = QPushButton("Load")
        button_load.clicked.connect(self.loadRegionAttributes)
        toolbar_layout.addWidget(button_load)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.saveRegionAttributes)
        toolbar_layout.addWidget(btn_save)

        layout.addLayout(toolbar_layout)


        #name & description

        name_layout = QGridLayout()
        name_layout.addWidget(QLabel("Attribute name:"), 0, 0)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Name of the attribute set")
        self.edit_name.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_name.setFixedWidth(350)
        self.edit_name.setText(self.region_attributes.name)
        name_layout.addWidget(self.edit_name, 0, 1, 1, 2)


        name_layout.addWidget(QLabel("Description:"), 1, 0)

        self.edit_description = QTextEdit()
        self.edit_description.setPlaceholderText("Type a description of your attributes")
        self.edit_description.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_description.setFixedWidth(350)
        self.edit_description.setMaximumHeight(100)
        self.edit_description.setText(self.region_attributes.description)

        name_layout.addWidget(self.edit_description, 1, 1, 1, 2) 

        layout.addLayout(name_layout)


        left_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Min", "Max", "Keywords"])
        self.table.cellActivated.connect(self.selectRow)
        self.table.cellClicked.connect(self.selectRow)
        self.table.currentCellChanged.connect(self.selectRow)
        self.table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40); }")

        left_layout.addWidget(self.table)


        #edit fields
        edit_layout = QHBoxLayout()

        self.editName = QLineEdit()
        self.editName.setPlaceholderText("Name")
        self.editName.setMaxLength(10)
        self.editName.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_layout.addWidget(self.editName)


        self.editType = QComboBox()
        # self.editType.addItems(['string', 'boolean', 'number', 'keyword']);
        self.editType.addItems(['string', 'number', 'keyword']);
        self.editType.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editType.activated[str].connect(self.updateFieldType)
        edit_layout.addWidget(self.editType)


        self.editMin = QLineEdit()
        self.editMin.setPlaceholderText("Min")
        self.editMin.setFixedWidth(80)
        self.editMin.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_layout.addWidget(self.editMin)


        self.editMax = QLineEdit()
        self.editMax.setPlaceholderText("Max")
        self.editMax.setFixedWidth(80)
        self.editMax.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_layout.addWidget(self.editMax)

        self.editValues = QLineEdit()
        self.editValues.setPlaceholderText("List of keywords")
        self.editValues.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        edit_layout.addWidget(self.editValues, 1)

        left_layout.addLayout(edit_layout)


        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignBottom)


        btnRemove = QPushButton("Delete")
        btnRemove.clicked.connect(self.removeField)
        right_layout.addWidget(btnRemove)

        btnAdd = QPushButton("Add")
        btnAdd.clicked.connect(self.addField)
        right_layout.addWidget(btnAdd)

        btnUpdate = QPushButton("Update")
        btnUpdate.clicked.connect(self.updateField)
        right_layout.addWidget(btnUpdate)


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
        self.region_attributes.name = self.edit_name.text()
        self.region_attributes.description = self.edit_description.document().toPlainText()

        self.project.region_attributes = deepcopy(self.region_attributes)
        self.close()

    def cancel(self):
        self.close()

    def closeEvent(self, event):
        self.closed.emit()
        super(QtRegionAttributesWidget, self).closeEvent(event)


    @pyqtSlot()
    def newRegionAttributes(self):
        self.labels = RegionAttributes()

    @pyqtSlot()
    def loadRegionAttributes(self):

        filters = "Region attributes (*.json)"
        filename, filter = QFileDialog.getOpenFileName(self, "Region attributes", "", filters)
        if filename == '':
            return

        #self.edit_load.setText(filename)

        data = RegionAttributes()
        data.loadFromFile(filename)

        self.edit_name.setText(data.name)
        self.edit_description.document().setPlainText(data.description)

        self.region_attributes = data
        self.createFields()

    @pyqtSlot()
    def saveRegionAttributes(self):

        self.region_attributes.name = self.edit_name.text()
        self.region_attributes.description = self.edit_description.document().toPlainText()
        if self.region_attributes.name == '':
            box = QMessageBox()
            box.setWindowTitle('TagLab')
            box.setText("Please enter a name for this region attributes set")
            box.exec()
            return

        dir = os.path.join(self.taglab_dir, self.region_attributes.name + '.json')
        filters = "Region attributes (*.json)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save region attributes", dir, filters)
        if filename == '':
            return
        self.region_attributes.saveToFile(filename)




    def createFields(self):
        self.table.clearContents()
        for field in self.region_attributes.data:
            self.appendField(field)

    def appendField(self, field):
        rowcount = self.table.rowCount()
        self.table.setRowCount(rowcount+1)
        self.setField(rowcount, field)

    def setField(self, row, field):
        self.table.setItem(row, 0, QTableWidgetItem(field['name']))
        self.table.setItem(row, 1, QTableWidgetItem(field['type']))
        min = ''
        if 'min' in field.keys() and field['min'] != None:
            min = str(field['min'])
        self.table.setItem(row, 2, QTableWidgetItem(min))
        max = ''
        if 'max' in field.keys() and field['max'] != None:
            max = str(field['max'])
        self.table.setItem(row, 3, QTableWidgetItem(max))
        if not 'keywords' in field or field['keywords'] == None:
            field['keywords'] = []
        self.table.setItem(row, 4, QTableWidgetItem(', '.join(field['keywords'])))

    @pyqtSlot(int, int)
    def selectRow(self, row, column):
        self.clearField()

        if row < 0:
            return

        self.table.selectRow(row)
        field = self.region_attributes.data[row]

        self.editName.setText(field['name'])
        self.editType.setCurrentText(field['type'])
        self.updateFieldType()

        min = ''
        if 'min' in field.keys() and field['min'] != None:
            min = str(field['min'])
        self.editMin.setText(min)
        max = ''
        if 'max' in field.keys() and field['max'] != None:
            max = str(field['max'])
        self.editMax.setText(max)
        self.editValues.setText(' '.join(field['keywords']))

    def clearField(self):
        self.editName.setText("")
        self.editType.setCurrentText("string")
        self.editMin.setText("")
        self.editMax.setText("")
        self.editValues.setText("")
        self.updateFieldType()

    def validateField(self):
        name = self.editName.text()
        if name == '':
            self.message("Please choose a field name")
            return False

        field = {}
        field['name'] = name
        field['type'] = self.editType.currentText()
        min = None
        if self.editMin.text() != '':
            try:
                min = float(self.editMin.text())
            except ValueError:
                self.message("Min value is not a number")
                return False
        field['min'] = min

        max = None
        if self.editMax.text() != '':
            try:
                max = int(self.editMax.text())
            except ValueError:
                self.message("Max value is not a number")
                return False
        field['max'] = max

        
        keywords =  self.editValues.text();
        if keywords != '':
            keywords = re.split(' |,|:|;|\t', keywords)
        else:
            keywords = []

        if field['type'] == 'keyword' and len(keywords) < 2:
            self.message("Insert at least two keywords separated by commas or spaces.")
            return False

        field['keywords'] = keywords
        return field

    @pyqtSlot()
    def addField(self):
        #validate text
        field = self.validateField()
        if field == False:
            return

        if self.region_attributes.has(field['name']):
            self.message("Duplicated field name...")
            return


        self.region_attributes.data.append(field)
        self.appendField(field)
        self.clearField()


    @pyqtSlot()
    def updateField(self):
        row = self.selectedRow()

        if row < 0:
            return self.message("Please, select a label to modify")

        field = self.validateField()
        if field == False:
            return

        self.region_attributes.data[row] = field
        self.setField(row, field)
        if len(self.region_attributes.data) > 0:
            self.selectRow(row, 0)

    @pyqtSlot()
    def removeField (self):
        row = self.selectedRow()

        if row < 0:
            return self.message("Please, select a label to delete")

        self.clearField()
        del self.region_attributes.data[row]
        self.table.removeRow(row)

    @pyqtSlot()
    def updateFieldType(self):
        type = self.editType.currentText()

        self.editMin.clear()
        self.editMax.clear()
        self.editValues.clear()

        
        self.editMin.setEnabled(type == "number")
        self.editMax.setEnabled(type == "number")        
        self.editValues.setEnabled(type == "keyword")


#    def eventFilter(self, object, event):

#        if type(object) == QLabel and event.type() == QEvent.MouseButtonDblClick:
#            self.highlightSelectedLabel(object)
#            return False

#        return False




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