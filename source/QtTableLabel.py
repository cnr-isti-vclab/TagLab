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
from PyQt5.QtCore import Qt, QAbstractTableModel, QItemSelectionModel, QSortFilterProxyModel, QRegExp, QModelIndex,  QSize, \
    pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QSizePolicy, QComboBox, QLabel, QTableView, QHeaderView, \
    QHBoxLayout, QVBoxLayout, QAbstractItemView, QStyledItemDelegate, QAction, QMenu, QToolButton, QGridLayout, \
    QLineEdit, QApplication, QLineEdit, QWidget, QSizePolicy, QPushButton
from PyQt5.QtGui import QColor
import pandas as pd
from source.Blob import Blob


class TableModel(QAbstractTableModel):
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.TextAlignmentRole:
            if index.column() < 5:
                return Qt.AlignRight | Qt.AlignVCenter

        if role == Qt.BackgroundRole:
            return QColor(40, 40, 40)

        value = self._data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:

            # Non ho idea cosa mettere in colonna zero un widget??
            if index.column() == 2:
               txt = int(value)

            # format floating point values
            elif index.column() == 3:
                txt = "{:.1f}".format(value) if value > 0 else ""
            else:
                txt = str(value)

            return txt

        if role == Qt.UserRole:
            if index.column() == 1:
                return str(value)

            return float(value)

    def setData(self, index, value, role):

        if index.isValid() and role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
        else:
            return False

        return True

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):

        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                head = str(self._data.columns[section])
                if head == "Visibility" or "Color":
                    return " "

                return head

            if orientation == Qt.Vertical:
                return str(self._data.index[section])

class QtTableLabel(QWidget):
    selectionChanged = pyqtSignal()


    def __init__(self, parent=None):
        super(QtTableLabel, self).__init__(parent)

        self.visibility_flags = []
        self.visibility_buttons = []
        self.labels_projects = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(150)

        self.data_table = QTableView()
        self.data_table.setMinimumWidth(400)
        # self.data_table.setMinimumHeight(100)
        self.data_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.data_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSortingEnabled(True)

        self.model = None
        self.data = None

        layout = QVBoxLayout()
        layout.addWidget(self.data_table)

        self.setLayout(layout)

    def setTable(self, project, img):

        self.project = project
        self.activeImg = img

        n_receivers = self.activeImg.annotations.receivers(self.activeImg.annotations.blobUpdated)
        if n_receivers > 1:
            self.activeImg.annotations.blobUpdated.disconnect()

        self.activeImg.annotations.blobUpdated.connect(self.updateBlob)
        self.activeImg.annotations.blobAdded.connect(self.addBlob)
        self.activeImg.annotations.blobRemoved.connect(self.removeBlob)

        self.data = self.annotations.create_label_table()

        self.model = TableModel(self.data)
        self.sortfilter = QSortFilterProxyModel(self)
        self.sortfilter.setSourceModel(self.model)
        self.sortfilter.setSortRole(Qt.UserRole)
        self.data_table.setModel(self.sortfilter)

        self.data_table.setVisible(False)
        self.data_table.verticalHeader().hide()
        self.data_table.setVisible(True)
        self.data_table.setEditTriggers(QAbstractItemView.DoubleClicked)

        self.data_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.data_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.data_table.horizontalHeader().showSection(0)
        self.data_table.update()

        self.data_table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40) }")
        self.data_table.selectionModel().selectionChanged.connect(lambda x: self.selectionChanged.emit())


    def clear(self):

        self.model = None
        self.data = None

        self.data_table.setModel(self.model)
        self.data_table.update()

    def updateData(self):

        self.data_table.update()

    def updateTable(self, data_table):

        if self.model is None:
            return

        self.sortfilter.beginResetModel()
        self.model.beginResetModel()

        self.model._data = data_table

        self.sortfilter.endResetModel()
        self.model.endResetModel()

        self.data_table.horizontalHeader().showSection(0)
        self.data_table.update()


    def selectRows(self, rows):
        self.data_table.clearSelection()

        indexes = [self.sortfilter.mapFromSource(self.model.index(r, 0)) for r in rows]
        mode = QItemSelectionModel.Select | QItemSelectionModel.Rows
        for index in indexes:
            self.data_table.selectionModel().select(index, mode)

        if len(rows) > 0:
            value = self.data_table.horizontalScrollBar().value()
            column = self.data_table.columnAt(value)
            self.data_table.scrollTo(self.data_table.model().index(indexes[0].row(), column))


    def addLabel(self, key, name):

        btnV = QPushButton()
        btnV.setProperty('key', key)
        btnV.setFlat(True)
        btnV.setIcon(self.icon_eyeopen)
        btnV.setIconSize(QSize(self.EYE_ICON_SIZE, self.EYE_ICON_SIZE))
        btnV.setFixedWidth(self.CLASS_LABELS_HEIGHT)
        btnV.setFixedHeight(self.CLASS_LABELS_HEIGHT)

        btnC = QPushButton("")
        btnV.setProperty('key', key)
        btnC.setFlat(True)

        color = self.labels[key].fill
        r = color[0]
        g = color[1]
        b = color[2]
        text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"

        btnC.setStyleSheet(text)
        btnC.setAutoFillBackground(True)
        btnC.setFixedWidth(self.CLASS_LABELS_HEIGHT)
        btnC.setFixedHeight(self.CLASS_LABELS_HEIGHT)

        lbl = QLineEdit(name)
        lbl.setProperty('key', key)
        lbl.setStyleSheet("QLineEdit { border: none; color : lightgray;}")
        lbl.setFixedHeight(self.CLASS_LABELS_HEIGHT)
        lbl.setReadOnly(True)
        lbl.installEventFilter(self)

        self.btnVisible.append(btnV)
        #self.visibility_flags.append(True)
        self.btnClass.append(btnC)
        self.lineeditClass.append(lbl)

        btnV.clicked.connect(self.toggleVisibility)
        lbl.editingFinished.connect(self.editingFinished)

        layout = QHBoxLayout()
        layout.addWidget(btnV)
        layout.addWidget(btnC)
        layout.addWidget(lbl)

        self.labels_layout.addLayout(layout)

    def setLabels(self, project):
        """
        Labels are set according to the current project.
        """

        self.labels = project.labels

        self.btnVisible = []
        #self.visibility_flags = []
        self.btnClass = []
        self.lineeditClass = []

        self.labels_layout = QVBoxLayout()
        self.labels_layout.setSpacing(2)

        # ADD VISIBILITY BUTTON-CLICKABLE LABELS FOR ALL THE CLASSES
        #for label_name in sorted(self.labels.keys()):

        for key in self.labels.keys():
            label = self.labels[key]
            self.addLabel(key, label.name)

        # to replace a layout with another one you MUST reparent it..
        tempwidget = QWidget()
        tempwidget.setLayout(self.layout())
        self.setLayout(self.labels_layout)

        ### SET ACTIVE LABEL
        txt = self.lineeditClass[0].text()
        self.lineeditClass[0].setText(txt)
        self.lineeditClass[0].setStyleSheet("QLineEdit { border: 1px; font-weight: bold; color : white;}")
        self.active_label_name = self.lineeditClass[0].text()

    def eventFilter(self, object, event):

        if type(object) == QLineEdit and event.type() == QEvent.FocusIn :

            self.highlightSelectedLabel(object)

            return False

        if type(object) == QLineEdit and event.type() == QEvent.MouseButtonDblClick :

            label_name = object.text()
            self.doubleClickLabel.emit(label_name)

        return False


    def setAllVisible(self):
        for label in self.labels.values():
            label.visible = True
        for btn in self.btnVisible:
            btn.setIcon(self.icon_eyeopen)

    def setAllNotVisible(self):
        for label in self.labels.values():
            label.visible = False
        for btn in self.btnVisible:
            btn.setIcon(self.icon_eyeclosed)


    @pyqtSlot()
    def toggleVisibility(self):

        button_clicked = self.sender()
        key = button_clicked.property('key')
        label = self.labels[key]

        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.setAllNotVisible()
            label.visible = True

        elif QApplication.keyboardModifiers() == Qt.ShiftModifier:
            self.setAllVisible()
            label.visible = False

        else:
            label.visible = not label.visible

        button_clicked.setIcon(self.icon_eyeopen if label.visible is True else self.icon_eyeclosed)

        self.visibilityChanged.emit()

    def highlightSelectedLabel(self, lbl_clicked):

        # reset the text of all the clickable labels
        for lbl in self.lineeditClass:
            lbl.setText(lbl.text())
            lbl.setStyleSheet("QLineEdit { border: none; font-weight: normal; color : lightgray;}")
            lbl.setReadOnly(True)

        txt = lbl_clicked.text()
        lbl_clicked.setText(txt)
        lbl_clicked.setReadOnly(True)
        lbl_clicked.setStyleSheet("QLineEdit { border: 1 px; font-weight: bold; color : white;}")

        self.active_label_name = lbl_clicked.property('key')
        self.activeLabelChanged.emit(self.active_label_name)

    def isClassVisible(self, key):

        return self.labels[key].visible

    def getActiveLabelName(self):

        return self.active_label_name






