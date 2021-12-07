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
from PyQt5.QtWidgets import QWidget, QScrollArea,QGroupBox, QColorDialog, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout, QTextEdit
import json
import os

class QtCustomDataWidget(QWidget):

    closewidget = pyqtSignal()

    def __init__(self, dir, project, parent=None):
        super(QtCustomDataWidget, self).__init__(parent)

        self.taglab_dir = dir
        self.project = project

        self.fields = []

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        self.button_new = QPushButton("New")
        self.button_new.clicked.connect(self.newCustomData)

        self.button_load = QPushButton("Load")
        self.button_load.clicked.connect(self.loadCustomData)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.saveCustomData)



        lbl_dname = QLabel("Custom data name:")
        lbl_dname.setFixedWidth(160)

        lbl_load = QLabel("Custom data path:")
        lbl_load.setFixedWidth(160)

        lbl_description = QLabel("Description:")
        lbl_description.setFixedWidth(160)
        lbl_description.setAlignment(Qt.AlignTop)

        self.edit_dname = QLineEdit()
        self.edit_dname.setPlaceholderText("Name of the custom data")
        self.edit_dname.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_dname.setFixedWidth(350)
        self.edit_dname.setText(project.custom_data.name)

        self.edit_load = QLineEdit()
        self.edit_load.setPlaceholderText("Path of the custom data")
        self.edit_load.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_load.setFixedWidth(350)
        self.edit_load.setReadOnly(True)

        self.edit_description = QTextEdit()
        self.edit_description.setPlaceholderText("Type a description of your custom data")
        self.edit_description.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_description.setFixedWidth(350)
        self.edit_description.setMaximumHeight(100)
        self.edit_description.setText(project.custom_data.description)

        self.fields_layout = QVBoxLayout()
        self.fields_widget = QWidget()

        self.fields_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.fields_widget.setMinimumWidth(400)
        self.fields_widget.setMinimumHeight(220)
        self.fields_widget.setLayout(self.fields_layout)

        self.scroll = QScrollArea()
        self.scroll.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.scroll.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setMaximumHeight(200)
        self.scroll.setWidget(self.fields_widget)

        self.btnRemove = QPushButton("Delete")
        self.btnAdd = QPushButton("Add")
        self.btnAdd.setStyleSheet("background-color: rgb(55,55,55);")
        self.btnOk = QPushButton("Update")
        self.btnRemove.clicked.connect(self.removeField)
        self.btnAdd.clicked.connect(self.addField)
        self.btnOk.clicked.connect(self.editField)

        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignRight)
        # buttons_layout.setAlignment(Qt.AlignTop)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnOk)
        buttons_layout.addWidget(self.btnRemove)


        COLOR_SIZE = 20

        text = "QPushButton:flat {background-color: rgb(255,255,255); border: 1px ;}"

        

        self.editName = QLineEdit()
        self.editName.setPlaceholderText("Name")
#        self.editName.setFixedWidth(40)
        self.eeditNameditR.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.editType = QComboBox()
        #self.editType.setFixedWidth(40)
        self.editType.addItems('string', 'boolean', 'number', 'enum');
        self.editG.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.editValues = QLineEdit()
        #self.editB.setFixedWidth(40)
        self.editValues.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.editType.activated[str].connect(self.updateFieldType)




        self.btn_set = QPushButton("Close")
#        self.btn_set.setMinimumWidth(360)
#        self.btn_set.setMinimumHeight(40)
#        self.btn_set.setStyleSheet("font-weight: bold;")

        layout_zerorow = QHBoxLayout()
        layout_zerorow.addWidget(self.button_new)
        layout_zerorow.addWidget(self.button_load)
        layout_zerorow.addWidget(self.btn_save)

        layout_firstrow = QHBoxLayout()
        layout_firstrow.setAlignment(Qt.AlignLeft)
        layout_firstrow.addWidget(lbl_dname)
        layout_firstrow.addWidget(self.edit_dname)
        layout_firstrow.addStretch()

        layout_secondrow = QHBoxLayout()
        layout_secondrow.setAlignment(Qt.AlignLeft)
        layout_secondrow.addWidget(lbl_load)
        layout_secondrow.addWidget(self.edit_load)

        layout_thirdrow = QHBoxLayout()
        layout_thirdrow.setAlignment(Qt.AlignLeft)
        layout_thirdrow.addWidget(lbl_description)
        layout_thirdrow.addWidget(self.edit_description)

        #4 row
        layout_addremove = QHBoxLayout()
        layout_addremove.addWidget(self.scroll)
        layout_addremove.addStretch()
        layout_addremove.addLayout(buttons_layout)

        #5 row
        layout_setField = QHBoxLayout()
        
        layout_setField.addWidget(self.editName)
        layout_setField.addWidget(self.btnAdd)

        #6 row
        bottom = QHBoxLayout()
        bottom.setAlignment(Qt.AlignHCenter)
        bottom.addWidget(self.btn_set)

        layout = QVBoxLayout()
        layout.addLayout(layout_zerorow)
        layout.addLayout(layout_firstrow)
        layout.addLayout(layout_secondrow)
        layout.addLayout(layout_thirdrow)
        layout.addLayout(layout_addremove)
        layout.addLayout(layout_setField)
        layout.addLayout(bottom)

        self.setLayout(layout)

        self.setWindowTitle("Edit Custom Data")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.selection_index = -1

        self.populateFieldsFromProject()


    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtCustomDataWidget, self).closeEvent(event)

    @pyqtSlot()
    def newCustomData(self):

        self.labels = []
        self.createAllLabels()

    @pyqtSlot()
    def loadCustomData(self):

        filters = "Custom Data (*.json)"
        fileName, _ = QFileDialog.getOpenFileName(self, "Custom data", "", filters)

        if fileName:

            if self.labels:

                box = QMessageBox()
                box.setIcon(QMessageBox.Question)
                box.setWindowTitle('TagLab')
                box.setText('Do you want to append or replace the current custom data?')
                box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                buttonY = box.button(QMessageBox.Yes)
                buttonY.setText('Append')
                buttonN = box.button(QMessageBox.No)
                buttonN.setText('Replace')
                box.exec()
                if box.clickedButton() == buttonN:
                    self.labels = []

            self.edit_load.setText(fileName)

            f = open(fileName, "r")
            dict = json.load(f)
            self.edit_dname.setText(dict["name"])
            self.edit_description.document().setPlainText(dict["description"])
            fields = dict["fields"]

            for field in fields:
               name= field['name']
               type = field['type']
               values = field['value']
               mylabel = Label(id=id, name=name, fill=fill)
               self.labels.append(mylabel)

            self.createFields()


    def checkConsistency (self):
        pass

    @pyqtSlot()
    def saveCustomData(self):

        name = self.edit_dname.text()
        description = self.edit_description.document().toPlainText()
        if name!= '':
            dir = os.path.join(self.taglab_dir, name + '.json')
            filters = "Custom Data (*.json)"
            filename, _ = QFileDialog.getSaveFileName(self, "Save Custom Data", dir, filters)
            dict={'Name': name, 'Description': description, 'Fields': self.fields}
            text = json.dumps(dict, indent = 2)
            f = open(filename, "w")
            f.write(text)
            f.close()
        else:
            box = QMessageBox()
            box.setWindowTitle('TagLab')
            box.setText("Please enter a custom data name")
            box.exec()
            pass

        msgBox = QMessageBox(self)
        msgBox.setWindowTitle('TagLab')
        msgBox.setText("Custom data successfully exported!")
        msgBox.exec()


    @pyqtSlot(int,int,int,str)
    def createField(self, r, g, b, name):

        COLOR_SIZE= 20
        text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"
        btn_color = QPushButton()
        btn_color.setFlat(True)
        btn_color.setStyleSheet(text)
        btn_color.setAutoFillBackground(True)
        btn_color.setFixedWidth(COLOR_SIZE)
        btn_color.setFixedHeight(COLOR_SIZE)

        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("border: none; color: lightgray;")
        lbl_name.setFixedHeight(20)
        lbl_name.installEventFilter(self)

        self.label_layout = QHBoxLayout()
        self.label_layout.addWidget(btn_color)
        self.label_layout.addWidget(lbl_name)

        self.fields_layout.addLayout(self.label_layout)

        tempWidget = QWidget()
        tempWidget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        tempWidget.setMinimumWidth(400)
        tempWidget.setMinimumHeight(220)
        tempWidget.setLayout(self.fields_layout)
        self.scroll.setWidget(tempWidget)

        label = Label(id =name , name =name , fill= [r,g,b])
        self.labels.append(label)

        self.label_color.append(btn_color)
        self.label_name.append(lbl_name)

        self.editFieldName.setText('')
        self.editR.setText('')
        self.editG.setText('')
        self.editB.setText('')

        text = "QPushButton:flat {background-color: rgb(255,255,255); border: none;}"
        self.btn_selection_color.setStyleSheet(text)


    @pyqtSlot()
    def chooseLabelColor(self):
        self.editR.blockSignals(True)
        self.editG.blockSignals(True)
        self.editB.blockSignals(True)
        color = QColorDialog.getColor()
        # convert to string RR-GG-BB
        newcolor = "{:d}-{:d}-{:d}".format(color.red(), color.green(), color.blue())
        newcolortext= self.setlabelColor(newcolor)
        self.editR.blockSignals(False)
        self.editG.blockSignals(False)
        self.editB.blockSignals(False)

    def populateLabelsFromProject(self):

        for key in self.project.data.keys():
            label = self.project.labels[key]
            lbl = Label(id=label.id, name=label.name, fill=label.fill)
            self.labels.append(lbl)

        self.createFields()

    def createFields(self):

        self.fields_layout = QVBoxLayout()
        self.label_color = []
        self.label_name = []
        for label in self.labels:

            COLOR_SIZE = 20
            text = "QPushButton:flat {background-color: rgb(" + str(label.fill[0]) + "," + str(
                label.fill[1]) + "," + str(label.fill[2]) + "); border: none ;}"
            btn_color = QPushButton()
            btn_color.setFlat(True)
            btn_color.setStyleSheet(text)
            btn_color.setAutoFillBackground(True)
            btn_color.setFixedWidth(COLOR_SIZE)
            btn_color.setFixedHeight(COLOR_SIZE)
            self.label_color.append(btn_color)

            lbl_name = QLabel(label.name)
            lbl_name.setStyleSheet("border: none; color: lightgray;")
            lbl_name.setFixedHeight(20)
            lbl_name.installEventFilter(self)
            self.label_name.append(lbl_name)

            self.label_layout = QHBoxLayout()
            self.label_layout.addWidget(btn_color)
            self.label_layout.addWidget(lbl_name)

            self.fields_layout.addLayout(self.label_layout)

        # update the scroll area
        tempWidget = QWidget()
        tempWidget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        tempWidget.setMinimumWidth(400)
        tempWidget.setMinimumHeight(220)
        tempWidget.setLayout(self.fields_layout)
        self.scroll.setWidget(tempWidget)


    @pyqtSlot()
    def updatelabelColor(self):

        r, g, b = self.getRGB()

        if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
            text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"
            self.btn_selection_color.setStyleSheet(text)
        else:
            self.editR.blockSignals(True)
            self.editG.blockSignals(True)
            self.editB.blockSignals(True)
            text = "QPushButton:flat {background-color: rgb(255,255,255); border: none;}"
            self.btn_selection_color.setStyleSheet(text)
            box = QMessageBox()
            box.setText("Please enter a number between 0 and 255")
            box.exec()
            self.editR.blockSignals(False)
            self.editG.blockSignals(False)
            self.editB.blockSignals(False)

    @pyqtSlot()
    def setlabelColor(self, color):
        color_components = color.split("-")
        if len(color_components) > 2:
            r = color_components[0]
            g = color_components[1]
            b = color_components[2]
            self.editR.setText(r)
            self.editG.setText(g)
            self.editB.setText(b)
            text = "QPushButton:flat {background-color: rgb(" + r + "," + g + "," + b + "); border: none ;}"
            self.btn_selection_color.setStyleSheet(text)

    @pyqtSlot()
    def editFieldName(self):

        if self.selection_index > 0:
            label = self.labels[self.selection_index]
            label.id = self.editFieldName.text()
            label.name = self.editFieldName.text()
            r, g, b = self.getRGB()

            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                label.fill = [r, g, b]
                self.createAllLabels()
                lbl_selected = self.label_name[self.selection_index]
                lbl_selected.setStyleSheet("border: 1 px; font-weight: bold; color: white;")
            else:
                box = QMessageBox()
                box.setText("Please, set a valid color")
                box.exec()

        else:
            box = QMessageBox()
            box.setText("Please, select a label to modify")
            box.exec()

    def removeLabel (self):

        if self.selection_index > 0:
            label = self.labels[self.selection_index]
            self.labels.remove(label)
            self.createAllLabels()
            self.selection_index = -1
        else:
            box = QMessageBox()
            box.setText("Please, select a label to delete")
            box.exec()

    def getRGB(self):

        try:
            red = int(self.editR.text())
            green = int(self.editG.text())
            blue = int(self.editB.text())
        except:
            red = -1
            green = - 1
            blue = - 1

        return red, green, blue

    @pyqtSlot()
    def addLabel(self):

        self.editR.blockSignals(True)
        self.editG.blockSignals(True)
        self.editB.blockSignals(True)

        red, green, blue = self.getRGB()

        if 0 <= red <= 255 and 0 <= green <= 255 and 0 <= blue <= 255 and self.editFieldName.text() != '':
            self.createLabel(red, green, blue, self.editFieldName.text())
        else:
            box = QMessageBox()
            box.setText("Please chose a valid color and type a label name")
            box.exec()

        self.editR.blockSignals(False)
        self.editG.blockSignals(False)
        self.editB.blockSignals(False)


    def eventFilter(self, object, event):

        if type(object) == QLabel and event.type() == QEvent.MouseButtonDblClick:
            self.highlightSelectedLabel(object)
            return False

        return False

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

        color = self.labels[index].fill
        textcolor = "QPushButton:flat {background-color: rgb(" + str(color[0]) + "," + str(color[1]) + "," + \
                    str(color[2]) + "); border: none ;}"
        self.btn_selection_color.setStyleSheet(textcolor)

        self.editR.blockSignals(True)
        self.editG.blockSignals(True)
        self.editB.blockSignals(True)
        self.editR.setText(str(color[0]))
        self.editG.setText(str(color[1]))
        self.editB.setText(str(color[2]))
        self.editR.blockSignals(False)
        self.editG.blockSignals(False)
        self.editB.blockSignals(False)

        self.selection_index = index



