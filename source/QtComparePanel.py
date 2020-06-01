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
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QSizePolicy, QComboBox, QLabel, QTableView, QHBoxLayout, QVBoxLayout
from pathlib import Path
import pandas as pd
import os

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
            return value

        #if role == Qt.BackgroundRole:
            #return QColor(40, 40, 40)

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

class QtComparePanel(QWidget):

    highlightBlob = pyqtSignal(int)
    showMatches = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QtComparePanel, self).__init__(parent)

        self.visibility_flags = []
        self.visibility_buttons = []
        self.labels_projects = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(100)

        self.data_table = QTableView()
        self.model = None

        lblFilter = QLabel("Filter: ")
        self.comboboxFilter = QComboBox()
        self.comboboxFilter.setMinimumWidth(80)
        self.comboboxFilter.addItem("All")
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

        self.comboboxFilter.currentTextChanged.connect(self.changeFilter)
        self.data_table.doubleClicked.connect(self.getData)


    def setProject(self, project):

        self.project = project

        correspondences = self.project.correspondences.correspondences
        dead = self.project.correspondences.dead
        born = self.project.correspondences.born

        for elem in correspondences:
            if len(elem) == 4:
                elem.append('No')
            else:
                elem[4] = 'Yes'

        for elem in dead:
            elem.append('No')

        for elem in born:
            elem.append('No')

        data_list = correspondences + born + dead

        self.data = pd.DataFrame(data_list, columns = ['Class', 'Blob 1', 'Blob 2', 'Type', 'Split'])

        columns_titles = ['Blob 1', 'Blob 2', 'Class', 'Type', 'Split']
        self.data = self.data.reindex(columns=columns_titles)

        self.model = TableModel(self.data)
        self.data_table.setModel(self.model)
        self.data_table.resizeColumnsToContents()
        self.data_table.verticalHeader().hide()

        self.data_table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40) }")


    @pyqtSlot(QModelIndex)
    def getData(self, index):
        column = index.column()
        row = index.row()
        if column == 0:
            blobid = self.data_table.model().index(row, column).data()
            self.highlightBlob.emit(int(blobid))


    @pyqtSlot(str)
    def changeFilter(self, txt):

        if txt == 'All':
            data = self.data
        elif txt == 'Grow':
            grow_rows = self.data['Type'] == 'grow'
            data = self.data[grow_rows]
        elif txt == 'Shrink':
            shrink_rows = self.data['Type'] == 'shrink'
            data = self.data[shrink_rows]
        elif txt == 'Dead':
            dead_rows = self.data['Type'] == 'dead'
            data = self.data[dead_rows]
        elif txt == 'Born':
            born_rows = self.data['Type'] == 'born'
            data = self.data[born_rows]

        self.model = TableModel(data)
        self.data_table.setModel(self.model)

        self.showMatches.emit(txt)



