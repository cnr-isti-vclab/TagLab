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
    QHBoxLayout, QVBoxLayout, QTextEdit, QFrame
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

    addlabel = pyqtSignal()
    deletelabel= pyqtSignal(str)
    updatelabel = pyqtSignal(str,list,str,list)

    def __init__(self, dir, project, parent=None):
        super(QtDictionaryWidget, self).__init__(parent)

        # DICTIONRY RULES:
        #
        #   - duplicate label names (key) are not allowed
        #   - labels in use cannot be removed
        #   - same colors are allowed

        self.taglab_dir = dir
        self.project = project

        self.labels = []
        self.label_color = []
        self.label_name  = []

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        self.button_new = QPushButton("New")
        self.button_new.clicked.connect(self.newDictionary)

        #self.button_current = QPushButton("Use current")
        #self.button_current.clicked.connect(self.currentDictionary)

        self.button_load = QPushButton("Load")
        self.button_load.clicked.connect(self.chooseDictionary)

        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.saveDictionary)

        lbl_dname = QLabel("Dictionary name:")
        lbl_dname.setFixedWidth(160)

        lbl_load = QLabel("Dictionary path:")
        lbl_load.setFixedWidth(160)

        lbl_description = QLabel("Description:")
        lbl_description.setFixedWidth(160)
        lbl_description.setAlignment(Qt.AlignTop)

        self.edit_dname = QLineEdit()
        self.edit_dname.setPlaceholderText("Name of the dictionary")
        self.edit_dname.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_dname.setFixedWidth(350)
        self.edit_dname.setText(project.dictionary_name)

        self.edit_load = QLineEdit()
        self.edit_load.setPlaceholderText("Path of the dictionary")
        self.edit_load.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_load.setFixedWidth(350)
        self.edit_load.setReadOnly(True)

        self.edit_description = QTextEdit()
        self.edit_description.setPlaceholderText("Type a description of your dictionary")
        self.edit_description.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.edit_description.setFixedWidth(350)
        self.edit_description.setMaximumHeight(100)
        self.edit_description.setText(project.dictionary_description)

        self.labels_layout = QVBoxLayout()
        self.labels_widget = QWidget()

        self.labels_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.labels_widget.setMinimumWidth(400)
        self.labels_widget.setMinimumHeight(220)
        self.labels_widget.setLayout(self.labels_layout)

        self.scroll = QScrollArea()
        self.scroll.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.scroll.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setMaximumHeight(200)
        self.scroll.setWidget(self.labels_widget)

        self.btnRemove = QPushButton("Delete")
        self.btnAdd = QPushButton("Add")
        self.btnAdd.setStyleSheet("background-color: rgb(55,55,55);")
        self.btnUpdate = QPushButton("Update")
        self.btnRemove.clicked.connect(self.removeLabel)
        self.btnAdd.clicked.connect(self.addLabel)
        self.btnUpdate.clicked.connect(self.editLabel)

        buttons_layout = QVBoxLayout()
        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnUpdate)
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
        self.editR = QLineEdit()
        self.editR.setFixedWidth(40)
        self.editR.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.editG = QLineEdit()
        self.editG.setFixedWidth(40)
        self.editG.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.editB = QLineEdit()
        self.editB.setFixedWidth(40)
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

        self.btn_ok = QPushButton("Ok")
        self.btn_ok.setMinimumWidth(150)
        self.btn_ok.clicked.connect(self.close)

        layout_zerorow = QHBoxLayout()
        layout_zerorow.addWidget(self.button_new)
        #layout_zerorow.addWidget(self.button_current)
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
        layout_setColor = QHBoxLayout()
        layout_setColor.addWidget(self.btn_selection_color)
        layout_setColor.addLayout(self.channels_layout)
        layout_setColor.addWidget(self.editLabel)
        layout_setColor.addWidget(self.btnAdd)

        # #6 row
        bottom = QHBoxLayout()
        bottom.setAlignment(Qt.AlignCenter)
        bottom.addWidget(self.btn_ok)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        layout = QVBoxLayout()
        layout.addLayout(layout_zerorow)
        layout.addLayout(layout_firstrow)
        layout.addLayout(layout_secondrow)
        layout.addLayout(layout_thirdrow)
        layout.addLayout(layout_addremove)
        layout.addLayout(layout_setColor)
        #layout.addSpacing(10)
        layout.addWidget(line)
        layout.addLayout(bottom)

        self.setLayout(layout)

        self.setWindowTitle("Labels Dictionary Editor")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.selection_index = -1

        self.populateLabelsFromProjectDictionary()

        # it returns the list of the labels currently used by the annotations
        self.labels_in_use = self.project.labelsInUse()


    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtDictionaryWidget, self).closeEvent(event)

    @pyqtSlot()
    def newDictionary(self):

        self.edit_description.setText("")
        self.edit_load.setText("")
        self.edit_dname.setText("")

        self.removeAllLabels()
        self.displayLabels()

    def removeAllLabels(self):
        """
        It removes all the labels but not the ones in use.
        """

        current_labels = self.labels.copy()

        self.labels_in_use = self.project.labelsInUse()

        oldname = ""
        for label in current_labels:
            if label.name in self.labels_in_use:
                pass
            else:
                oldname = label.name
                self.labels.remove(label)

        # only one notification is sufficient to update all the removed labels
        if oldname != "":
            self.deletelabel.emit(oldname)

    @pyqtSlot()
    def chooseDictionary(self):

        filters = "DICTIONARY (*.json)"
        fileName, _ = QFileDialog.getOpenFileName(self, "Dictionary", "", filters)

        if fileName:

            flag_replace = False
            if self.labels:
                box = QMessageBox()
                box.setIcon(QMessageBox.Question)
                box.setWindowTitle('TagLab')
                box.setText('Do you want to append or replace the current dictionary?')
                box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                buttonY = box.button(QMessageBox.Yes)
                buttonY.setText('Append')
                buttonN = box.button(QMessageBox.No)
                buttonN.setText('Replace')
                box.exec()
                if box.clickedButton() == buttonN:
                    flag_replace = True
                else:
                    flag_replace = False

            self.edit_load.setText(fileName)

            f = open(fileName, "r")
            dict = json.load(f)
            self.edit_dname.setText(dict["Name"])
            self.edit_description.document().setPlainText(dict["Description"])
            ALLlabels = dict["Labels"]

            labels_loaded = []
            for label in ALLlabels:
               name= label['name']
               id = label['name']
               fill = label['fill']
               mylabel = Label(id=id, name=name, fill=fill)
               labels_loaded.append(mylabel)

            if flag_replace is True:
                # REPLACE CURRENT DICTIONARY WITH THE LOADED ONE
                self.removeAllLabels()

            # create a dictionary to speed up the search of the existing labels
            labels_dict = {}
            for label in self.labels:
                labels_dict[label.name] = label
            labels_names = list(labels_dict.keys())

            # add or update the loaded label
            for label in labels_loaded:
                if label.name in labels_names:
                    # update the label
                    oldname = labels_dict[label.name].name
                    oldcolor = labels_dict[label.name].fill
                    newname = label.name
                    newcolor = label.fill

                    if oldcolor == newcolor and oldname == newname:
                        pass
                    else:
                        labels_dict[label.name].fill = newcolor
                        self.updatelabel.emit(oldname, oldcolor, newname, newcolor)

                else:
                    # add a new label
                    self.labels.append(label)

            # only one notification is sufficient to update all the modified labels
            self.addlabel.emit()

            self.displayLabels()


    @pyqtSlot()
    def saveDictionary(self):

        name = self.edit_dname.text()
        description = self.edit_description.document().toPlainText()
        dir = os.path.join(self.taglab_dir, name + '.json')
        filters = "DICTIONARY (*.json)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save dictionary", dir, filters)

        if filename:
            dict={'Name': name, 'Description': description, 'Labels': self.labels}
            text = json.dumps(dict, cls = DictionaryEncoder, indent = 2)
            f = open(filename, "w")
            f.write(text)
            f.close()
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle('TagLab')
            msgBox.setText("Dictionary successfully exported!")
            msgBox.exec()
        else:
            box = QMessageBox()
            box.setWindowTitle('TagLab')
            box.setText("Please enter a dictionary name")
            box.exec()
            pass

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

        tempWidget = QWidget()
        tempWidget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        tempWidget.setMinimumWidth(400)
        tempWidget.setMinimumHeight(220)
        tempWidget.setLayout(self.labels_layout)
        self.scroll.setWidget(tempWidget)

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

    def populateLabelsFromProjectDictionary(self):

        for key in self.project.labels.keys():
            label = self.project.labels[key]
            if label.name != "Empty":  # empty is a special tag, it is always present in the dictionary, and it cannot be edited
                lbl = Label(id=label.id, name=label.name, fill=label.fill)
                self.labels.append(lbl)

        self.displayLabels()

    def displayLabels(self):

        self.labels_layout = QVBoxLayout()
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

            self.labels_layout.addLayout(self.label_layout)

        # update the scroll area
        tempWidget = QWidget()
        tempWidget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        tempWidget.setMinimumWidth(400)
        tempWidget.setMinimumHeight(220)
        tempWidget.setLayout(self.labels_layout)
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
    def editLabel(self):

        if self.selection_index >= 0:

            label = self.labels[self.selection_index]
            oldname = label.name
            oldcolor = label.fill

            newname = self.editLabel.text()

            r, g, b = self.getRGB()
            newcolor = [r, g, b]

            if oldcolor == newcolor and oldname == newname:
                return

            # note that TWO labels with the same name should exist, because if you update the color and not the name
            # the label exists..
            if self.countExistingLabel(newname) > 1:
                box = QMessageBox()
                box.setText("A label with the same name just exists (!) Please, change it!")
                box.exec()
                return

            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:

                label.id = newname
                label.name = newname
                label.fill = [r, g, b]

                self.displayLabels()
                lbl_selected = self.label_name[self.selection_index]
                lbl_selected.setStyleSheet("border: 1 px; font-weight: bold; color: white;")
                self.updatelabel.emit(oldname, oldcolor, label.name, label.fill)

                self.editR.blockSignals(True)
                self.editG.blockSignals(True)
                self.editB.blockSignals(True)

                self.editLabel.setText('')
                self.editR.setText('')
                self.editG.setText('')
                self.editB.setText('')

                text = "QPushButton:flat {background-color: rgb(255,255,255); border: none;}"
                self.btn_selection_color.setStyleSheet(text)

                self.editR.blockSignals(False)
                self.editG.blockSignals(False)
                self.editB.blockSignals(False)

            else:
                box = QMessageBox()
                box.setText("Please, set a valid color")
                box.exec()

        else:
            box = QMessageBox()
            box.setText("Please, select a label to modify")
            box.exec()

    def removeLabel(self):

        if self.selection_index >= 0:
            label = self.labels[self.selection_index]
            oldname = label.name

            delete_ok = True
            if label.name in self.labels_in_use:

                box = QMessageBox()
                box.setIcon(QMessageBox.Question)
                box.setWindowTitle('TagLab')
                box.setText('Pay attention, this label is in use. If you delete it, '
                            'the Empty class will be assigned to the existing objects.')
                box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                buttonY = box.button(QMessageBox.Yes)
                buttonY.setText('Yes')
                buttonC = box.button(QMessageBox.No)
                buttonC.setText('Cancel')
                box.exec()

                if box.clickedButton() == buttonY:
                    delete_ok = True
                else:
                    delete_ok = False

            if delete_ok is True:
                self.labels.remove(label)
                self.displayLabels()
                self.selection_index = -1

                self.editR.blockSignals(True)
                self.editG.blockSignals(True)
                self.editB.blockSignals(True)

                self.editLabel.setText('')
                self.editR.setText('')
                self.editG.setText('')
                self.editB.setText('')

                text = "QPushButton:flat {background-color: rgb(255,255,255); border: none;}"
                self.btn_selection_color.setStyleSheet(text)

                self.editR.blockSignals(False)
                self.editG.blockSignals(False)
                self.editB.blockSignals(False)

                self.deletelabel.emit(oldname)

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

    def countExistingLabel(self, label_name):

        count = 0
        for label in self.labels:
            if label.name == label_name:
                count += 1

        return count

    @pyqtSlot()
    def addLabel(self):

        red, green, blue = self.getRGB()

        if 0 <= red <= 255 and 0 <= green <= 255 and 0 <= blue <= 255 and self.editLabel.text() != '':

            label_name = self.editLabel.text()
            if self.countExistingLabel(label_name) > 0:
                box = QMessageBox()
                box.setText("A label with the same name just exists (!) Please, change it!")
                box.exec()
                return

            self.editR.blockSignals(True)
            self.editG.blockSignals(True)
            self.editB.blockSignals(True)

            self.createLabel(red, green, blue, self.editLabel.text())

            self.editR.blockSignals(False)
            self.editG.blockSignals(False)
            self.editB.blockSignals(False)

            self.addlabel.emit()

        else:
            box = QMessageBox()
            box.setText("Please chose a valid color and type a label name")
            box.exec()

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
        self.editLabel.setText(txt)

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



