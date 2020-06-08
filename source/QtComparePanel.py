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
from PyQt5.QtCore import Qt, QAbstractTableModel, QItemSelectionModel, QSortFilterProxyModel, QRegExp, QModelIndex, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QSizePolicy, QHeaderView, QComboBox, QLabel, QTableView, \
    QHBoxLayout, QVBoxLayout, QAbstractItemView, QStyleOptionViewItem, QStyledItemDelegate
from PyQt5.QtGui import QColor
from pathlib import Path
import math

path = Path(__file__).parent.absolute()
imdir = str(path)
imdir =imdir.replace('source', '')

class TableModel(QAbstractTableModel):

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):

        if role == Qt.DisplayRole:
            value = self._data.iloc[index.row(), index.column()]
            # if index.column() == 0 or index.column() == 1:
            #     return "" if math.isnan(value) else str(value)
            # format floating point values
            if index.column() == 2 or index.column() == 3:
                txt = "{:.2f}".format(value)
            else:
                txt = str(value)

            return txt

        if role == Qt.BackgroundRole:
            return QColor(40, 40, 40)

    def setData(self, index, value, role):

        if index.isValid() and role == Qt.EditRole:

            self._data.iloc[index.row(), index.column()] = value
        else:
            return False

        # self.dataChanged.emit(index, index)

        return True

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])

            if orientation == Qt.Vertical:
                return str(self._data.index[section])

    def flags(self, index):

        value = self._data.iloc[index.row(), index.column()]

        if value == "dead" and index.column() == 5:
            return QAbstractTableModel.flags(self, index) | Qt.ItemIsEditable
        else:
            return QAbstractTableModel.flags(self, index)


class ComboBoxItemDelegate(QStyledItemDelegate):

    def __init__(self, parent = None):
        super(ComboBoxItemDelegate, self).__init__(parent)

        pass

    def createEditor(self, parent, option, index):

        cb = QComboBox(parent)
        row = index.row()
        cb.addItem("dead")
        cb.addItem("gone")
        return cb

    def setEditorData(self, editor, index):

        cb = editor

        # get the index of the text in the combobox that matches the current
        # value of the item const
        currentText = index.data()
        cbIndex = cb.findText(currentText);
        # if it is valid, adjust the combobox
        if cbIndex >= 0:
            cb.setCurrentIndex(cbIndex)

    def setModelData(self, editor, model, index):

        cb = editor
        model.setData(index, cb.currentText(), Qt.EditRole)


class QtComparePanel(QWidget):

    highlightBlob = pyqtSignal(int)
    filterChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QtComparePanel, self).__init__(parent)

        self.visibility_flags = []
        self.visibility_buttons = []
        self.labels_projects = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(100)

        self.data_table = QTableView()
        self.data_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.data_table.setSelectionMode(QAbstractItemView.MultiSelection);

        self.model = None
        self.data = None

        self.combodelegate = ComboBoxItemDelegate(self.data_table)

        lblFilter = QLabel("Filter: ")
        self.comboboxFilter = QComboBox()
        self.comboboxFilter.setMinimumWidth(80)
        self.comboboxFilter.addItem("All")
        self.comboboxFilter.addItem("Same")
        self.comboboxFilter.addItem("Born")
        self.comboboxFilter.addItem("Dead")
        self.comboboxFilter.addItem("Grow")
        self.comboboxFilter.addItem("Shrink")

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(lblFilter)
        filter_layout.addWidget(self.comboboxFilter)
        filter_layout.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(filter_layout)
        layout.addWidget(self.data_table)
        self.setLayout(layout)

        self.project = None
        self.data = None

        self.comboboxFilter.currentTextChanged.connect(self.changeFilter)
        #self.data_table.doubleClicked.connect(self.getData)


    def setProject(self, project):

        self.project = project

        if project.correspondences is not None:

            self.data = project.correspondences.data

            self.model = TableModel(self.data)
            self.sortfilter = QSortFilterProxyModel(self)
            self.sortfilter.setSourceModel(self.model)
            self.data_table.setModel(self.sortfilter)

            self.data_table.setVisible(False)
            self.data_table.verticalHeader().hide()
            self.data_table.resizeColumnsToContents()
            self.data_table.setVisible(True)

            self.data_table.setItemDelegateForColumn(5, self.combodelegate)
            self.data_table.setEditTriggers(QAbstractItemView.DoubleClicked)

            self.data_table.update()

            self.data_table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40) }")


    def selectRows(self, rows):
        print(rows)
        self.data_table.clearSelection()

        indexes = [self.model.index(r, 0) for r in rows]
        mode = QItemSelectionModel.Select | QItemSelectionModel.Rows
        [self.data_table.selectionModel().select(index, mode) for index in indexes]

    @pyqtSlot(QModelIndex)
    def getData(self, index):
        column = index.column()
        row = index.row()
        if column == 0:
            blobid = self.data_table.model().index(row, column).data()

            try:
                id = int(blobid)
                self.highlightBlob.emit(int(blobid))
            except ValueError:
                print("No valid id")


    @pyqtSlot(str)
    def changeFilter(self, txt):

        if self.data is None:
            return

        if txt == 'All':
            self.sortfilter.setFilterRegExp(QRegExp())
        else:
            self.sortfilter.setFilterKeyColumn(5)
            self.sortfilter.setFilterRegExp(txt.lower())
            self.sortfilter.setFilterRole(Qt.DisplayRole)

        self.filterChanged.emit(txt.lower())



