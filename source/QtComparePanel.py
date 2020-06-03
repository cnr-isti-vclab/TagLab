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
from PyQt5.QtCore import Qt, QAbstractTableModel, QSortFilterProxyModel, QRegExp, QModelIndex, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QSizePolicy, QHeaderView, QComboBox, QLabel, QTableView, QHBoxLayout, QVBoxLayout
from pathlib import Path

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

            # format floating point values
            if index.column() == 2 or index.column() == 3:
                txt = "{:.2f}".format(value/100.0) #convert to cm^2
            else:
                txt = str(value)

            return txt

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
        self.data_table.doubleClicked.connect(self.getData)


    def setProject(self, project):

        self.project = project

        correspondences = self.project.correspondences.correspondences
        dead = self.project.correspondences.dead
        born = self.project.correspondences.born

        factor1 = self.project.correspondences.source.map_px_to_mm_factor * \
                  self.project.correspondences.source.map_px_to_mm_factor / 100.0
        factor2 = self.project.correspondences.target.map_px_to_mm_factor * \
                  self.project.correspondences.target.map_px_to_mm_factor / 100.0

        for elem in dead:
            elem.append('none')

        for elem in born:
            elem.append('none')

        data_list = correspondences + born + dead

        for elem in data_list:
            elem[2] = float(elem[2]) * factor1
            elem[3] = float(elem[3]) * factor2

        self.data = project.correspondences.data #pd.DataFrame(data_list, columns=['Class', 'Blob 1', 'Blob 2', 'Area1', 'Area2', 'Action', 'Split\Fuse'])

        self.model = TableModel(self.data)
        self.sortfilter = QSortFilterProxyModel(self)
        self.sortfilter.setSourceModel(self.model)
        self.data_table.setModel(self.sortfilter)

        self.data_table.setVisible(False)
        self.data_table.verticalHeader().hide()

        #self.data_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        #self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        #self.data_table.setMinimumWidth(600)
        self.data_table.resizeColumnsToContents()
        self.data_table.setVisible(True)

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

        if self.data is None:
            return

        if txt == 'All':
            self.sortfilter.setFilterRegExp(QRegExp())
        else:
            self.sortfilter.setFilterKeyColumn(5)
            self.sortfilter.setFilterRegExp(txt.lower())
            self.sortfilter.setFilterRole(Qt.DisplayRole)

        self.showMatches.emit(txt)



