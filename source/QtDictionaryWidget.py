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
from source.Label import Label
import json
import os

class DictionaryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Label):
            return obj.save()
        return json.JSONEncoder.default(self, obj)

class QtDictionaryWidget(QWidget):

    closewidget = pyqtSignal()
    def __init__(self, dir, parent=None):
        super(QtDictionaryWidget, self).__init__(parent)

        self.taglab_dir = dir

        self.labels = []

        self.label_color = []
        self.label_name  = []

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        lbl_dname = QLabel("Dictionary name:")
        lbl_dname.setFixedWidth(160)

        lbl_load = QLabel("Load dictionary:")
        lbl_load.setFixedWidth(160)

        lbl_description = QLabel("Description:")
        lbl_description.setFixedWidth(160)
        lbl_description.setAlignment(Qt.AlignTop)
      #  self.groupbox_labels.setAlignment(Qt.AlignLeft)

        self.edit_dname = QLineEdit()
        self.edit_dname.setPlaceholderText("Name of the dictionary")
        self.edit_dname.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_dname.setFixedWidth(350)
        self.edit_dname.textChanged.connect(self.nameAssigned)

        button_load = QPushButton("...")
        button_load.setMaximumWidth(20)
        button_load.clicked.connect(self.chooseDictionary)

        self.edit_load = QLineEdit()
        self.edit_load.setPlaceholderText("Path of the dictionary")
        self.edit_load.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_load.setFixedWidth(350)


        self.edit_description = QTextEdit()
        self.edit_description.setPlaceholderText("Type a description of your dictionary")
        self.edit_description.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_description.setFixedWidth(350)
        self.edit_description.setMaximumHeight(100)


        self.edit_load.setReadOnly(True)
        self.labels_layout = QVBoxLayout()
        self.labels_widget = QWidget()

        self.labels_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.labels_widget.setMinimumWidth(400)
        self.labels_widget.setMinimumHeight(100)
        self.labels_widget.setLayout(self.labels_layout)


        self.scroll = QScrollArea()
        self.scroll.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.scroll.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setMinimumHeight(200)
        self.scroll.setWidget(self.labels_widget)

        groupbox_style = "QGroupBox\
                  {\
                      border: 2px solid rgb(40,40,40);\
                      border-radius: 0px;\
                      margin-top: 10px;\
                      margin-left: 0px;\
                      margin-right: 0px;\
                      padding-top: 5px;\
                      padding-left: 0px;\
                      padding-bottom: 0px;\
                      padding-right: 0px;\
                  }\
                  \
                  QGroupBox::title\
                  {\
                      subcontrol-origin: margin;\
                      subcontrol-position: top center;\
                      padding: 0 0px;\
                  }"


        self.btnRemove = QPushButton("Remove")
        self.btnAdd = QPushButton("Add")
        self.btnRemove.clicked.connect(self.removeLabel)
        self.btnAdd.clicked.connect(self.addLabel)

        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignRight)
        # buttons_layout.setAlignment(Qt.AlignTop)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnAdd)
        buttons_layout.addWidget(self.btnRemove)


        COLOR_SIZE = 20

        text = "QPushButton:flat {background-color: rgb(255,255,255); border: 1px ;}"

        self.btn_selection_color = QPushButton()
        self.btn_selection_color.setFlat(True)
        self.btn_selection_color.setStyleSheet(text)
        self.btn_selection_color.setAutoFillBackground(True)
        self.btn_selection_color.setFixedWidth(COLOR_SIZE)
        self.btn_selection_color.setFixedHeight(COLOR_SIZE)
        self.btn_selection_color.clicked.connect(self.chooseLabelColor)

        rgblbl = QLabel("RGB:")
        rgblbl.setFixedWidth(50)
        self.editR = QLineEdit()
        self.editR.setFixedWidth(50)
        self.editR.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.editG = QLineEdit()
        self.editG.setFixedWidth(50)
        self.editG.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.editB = QLineEdit()
        self.editB.setFixedWidth(50)
        self.editB.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.editR.textChanged.connect(self.updatelabelColor)
        self.editG.textChanged.connect(self.updatelabelColor)
        self.editB.textChanged.connect(self.updatelabelColor)

        self.channels_layout = QHBoxLayout()
        self.channels_layout.addWidget(rgblbl)
        self.channels_layout.addWidget(self.editR)
        self.channels_layout.addWidget(self.editG)
        self.channels_layout.addWidget(self.editB)

        self.editLabel = QLineEdit()
        self.editLabel.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.editLabel.setPlaceholderText("Label name")


        # self.btnCancel = QPushButton("Cancel")
        # self.btnCancel.clicked.connect(self.closeEvent(event))

        self.btnSave = QPushButton("Save")
        self.btnSave.clicked.connect(self.saveDictionary)

        layout_firstrow = QHBoxLayout()
        layout_firstrow.setAlignment(Qt.AlignLeft)
        layout_firstrow.addWidget(lbl_dname)
        layout_firstrow.addWidget(self.edit_dname)
        layout_firstrow.addStretch()

        layout_secondrow = QHBoxLayout()
        layout_secondrow.setAlignment(Qt.AlignLeft)
        layout_secondrow.addWidget(lbl_load)
        layout_secondrow.addWidget(self.edit_load)
        layout_secondrow.addWidget(button_load)

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
        layout_setColor = QHBoxLayout()
        layout_setColor.addWidget(self.btn_selection_color)
        layout_setColor.addLayout(self.channels_layout)
        layout_setColor.addWidget(self.editLabel)

        #6 row
        bottom = QHBoxLayout()
        bottom.setAlignment(Qt.AlignRight)
        bottom.addStretch()
        #bottom.addWidget(self.btnCancel)
        bottom.addWidget(self.btnSave)

        layout = QVBoxLayout()
        layout.addLayout(layout_firstrow)
        layout.addLayout(layout_secondrow)
        layout.addLayout(layout_thirdrow)
        layout.addLayout(layout_addremove)
        layout.addLayout(layout_setColor)
        layout.addLayout(bottom)

        self.setLayout(layout)

        self.setWindowTitle("Create/edit dictionary")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtDictionaryWidget, self).closeEvent(event)


    def nameAssigned(self):
        pass

    def chooseDictionary(self):

        filters = "DICTIONARY (*.json)"
        fileName, _ = QFileDialog.getOpenFileName(self, "Dictionary", "", filters)

        self.edit_load.setText(fileName)
        self.labels_layout = QVBoxLayout()


        if fileName:
           f = open(fileName, "r")
           dict = json.load(f)
           self.edit_dname.setText(dict["Name"])
           self.edit_description.document().setPlainText(dict["Description"])
           ALLlabels = dict["Labels"]
           self.labels = []
           for label in ALLlabels:
               name= label['name']
               id = label['name']
               fill = label['fill']
               mylabel = Label(id=id, name=name, fill=fill)
               self.labels.append(mylabel)
               COLOR_SIZE = 20
               text = "QPushButton:flat {background-color: rgb(" + str(mylabel.fill[0]) + "," + str(mylabel.fill[1]) + "," + str(mylabel.fill[2]) + "); border: none ;}"
               self.btn_color = QPushButton()
               self.btn_color.setFlat(True)
               self.btn_color.setStyleSheet(text)
               self.btn_color.setAutoFillBackground(True)
               self.btn_color.setFixedWidth(COLOR_SIZE)
               self.btn_color.setFixedHeight(COLOR_SIZE)

               self.lbl_name = QLabel(mylabel.name)
               self.lbl_name.setStyleSheet("border: none; color: lightgray;")
               self.lbl_name.setFixedHeight(20)

               self.label_layout = QHBoxLayout()
               self.label_layout.addWidget(self.btn_color)
               self.label_layout.addWidget(self.lbl_name)

               self.labels_layout.addLayout(self.label_layout)

           tempWidget = QWidget()
           tempWidget.setLayout(self.labels_widget.layout())
           self.labels_widget.setLayout(self.labels_layout)


    def setDictionary (self):
        pass


    def removeLabel (self):
        pass

    @pyqtSlot()
    def saveDictionary(self):

        name = self.edit_dname.text()
        description = self.edit_description.document().toPlainText()
        if name!= '':
            dir = os.path.join(self.taglab_dir, name + '.json')
            filters = "DICTIONARY (*.json)"
            filename, _ = QFileDialog.getSaveFileName(self, "Save dictionary", dir, filters)
            dict={'Name': name, 'Description': description, 'Labels': self.labels}
            text = json.dumps(dict, cls = DictionaryEncoder, indent = 2)
            f = open(filename, "w")
            f.write(text)
            f.close()
        else:
            box = QMessageBox()
            box.setWindowTitle('TagLab')
            box.setText("Please enter a dictionary name")
            box.exec()
            pass

        msgBox = QMessageBox(self)
        msgBox.setWindowTitle('TagLab')
        msgBox.setText("Dictionary successfully exported!")
        msgBox.exec()


    @pyqtSlot(int,int,int,str)
    def createLabel(self, r, g, b, name):

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

        self.labels_layout.addLayout(self.label_layout)

        label = Label(id =name , name =name , fill= [r,g,b])
        self.labels.append(label)

        self.label_color.append(btn_color)
        self.label_name.append(lbl_name)

        self.editLabel.setText('')
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


    @pyqtSlot()
    def updatelabelColor(self):

        try: r = int(self.editR.text())
        except:
            r = -1
        try : g = int(self.editG.text())
        except:
            g = - 1
        try : b = int(self.editB.text())
        except:
            b = - 1

        if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
            text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"
            self.btn_selection_color.setStyleSheet(text)
        else:
            self.editR.blockSignals(True)
            self.editG.blockSignals(True)
            self.editB.blockSignals(True)
            self.editLabel.setText('')
            self.editR.setText('')
            self.editG.setText('')
            self.editB.setText('')
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



    def addLabel(self):

        self.editR.blockSignals(True)
        self.editG.blockSignals(True)
        self.editB.blockSignals(True)

        try:
            red = int(self.editR.text())
            green = int(self.editG.text())
            blue = int(self.editB.text())
        except:
            red = -1
            green = - 1
            blue = - 1

        if 0 <= red <= 255 and 0 <= green <= 255 and 0 <= blue <= 255 and self.editLabel.text() != '':
            self.createLabel(red, green, blue, self.editLabel.text())

        else:
            box = QMessageBox()
            box.setText("Please chose a valid color and type a label name")
            box.exec()

        self.editR.blockSignals(False)
        self.editG.blockSignals(False)
        self.editB.blockSignals(False)


    def eventFilter(self, object, event):


        if type(object) == QLabel and event.type() == QEvent.FocusIn:
            self.highlightSelectedLabel(object)
            return False


    def highlightSelectedLabel(self, lbl_clicked):

        # reset the text of all the clickable labels
        for lbl in self.label_name:
            lbl.setStyleSheet("QLineEdit { border: none; font-weight: normal; color : lightgray;}")

        txt = lbl_clicked.text()
        lbl_clicked.setStyleSheet("QLineEdit { border: 1 px; font-weight: bold; color : white;}")

        index = self.label_name.index(lbl_clicked)
        btn_clicked = self.btn_color[index]
        self.editLabel.setText(txt)

        textcolor = "QPushButton:flat {background-color: rgb(" + str(self.labels[index].fill[0])+ "," + str(self.labels[index].fill[1]) + "," +    str(self.labels[index].fill[2]) + "); border: none ;}"
        self.btn_selection_color.setStyleSheet(textcolor)

