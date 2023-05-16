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
from PyQt5.QtCore import Qt, QAbstractTableModel, QItemSelectionModel, QSortFilterProxyModel, QRegExp, QModelIndex, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QSizePolicy, QCheckBox, QComboBox, QLabel, QTableView, QHeaderView, \
    QHBoxLayout, QVBoxLayout, QAbstractItemView, QStyledItemDelegate, QAction, QMenu, QToolButton, QGridLayout, QLineEdit
from PyQt5.QtGui import QColor
import pandas as pd
from source.Blob import Blob
from source.Point import Point

class TableModel(QAbstractTableModel):
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data
        self.surface_area_mode_enabled = False

    def data(self, index, role):
        if role == Qt.TextAlignmentRole:
            if index.column() < 5:
                return Qt.AlignRight | Qt.AlignVCenter

        if role == Qt.BackgroundRole:
            return QColor(40, 40, 40)

        value = self._data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:

            if index.column() == 0:
                if int(value) < 0:
                    return ""

            # format floating point values
            if index.column() == 3 or index.column() == 4:
                txt = "{:.1f}".format(value) if value > 0 else ""
            else:
                txt = str(value)

            return txt
        
        if role == Qt.UserRole:
            if index.column() == 2 or index.column() == 1:
                return str(value)

            return float(value)

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
                head = str(self._data.columns[section])
                if head == "Blob":
                    return "Id"
                if head == "Area" and self.surface_area_mode_enabled:
                    return "S. Area"

                return head

            if orientation == Qt.Vertical:
                return str(self._data.index[section])

class QtTablePanel(QWidget):
    selectionChanged = pyqtSignal()
    filterChanged = pyqtSignal(str)
    stateChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super(QtTablePanel, self).__init__(parent)

        self.visibility_flags = []
        self.visibility_buttons = []
        self.labels_projects = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(150)
        self.data_table = QTableView()
        self.data_table.setMinimumWidth(400)
        self.data_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.data_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSortingEnabled(True)
        self.setStyleSheet("""
        QScrollBar::add-line:vertical {
        height: 0px;
        }
        
        QScrollBar::sub-line:vertical {
        height: 0px;
        }
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        height: 0px;
        }
        
        """);
        self.model = None
        self.data = None

        self.searchId = QLineEdit("")
        self.searchId.textChanged[str].connect(self.selectById)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Search Id: "))
        filter_layout.addWidget(self.searchId)

        self.checkBoxRegions = QCheckBox("Regions")
        self.checkBoxRegions.setChecked(True)
        self.checkBoxRegions.setMinimumWidth(40)
        self.checkBoxRegions.stateChanged[int].connect(self.displayDataByType)

        self.checkBoxPoints = QCheckBox("Points")
        self.checkBoxPoints.setChecked(True)
        self.checkBoxPoints.setMinimumWidth(40)
        self.checkBoxPoints.stateChanged[int].connect(self.displayDataByType)

        layoutCheckbox = QHBoxLayout()
        layoutCheckbox.addWidget(self.checkBoxRegions)
        layoutCheckbox.addWidget(self.checkBoxPoints)

        layout = QVBoxLayout()
        layout.addLayout(filter_layout)
        layout.addLayout(layoutCheckbox)
        layout.addWidget(self.data_table)

        self.setLayout(layout)

        self.project = None
        self.activeImg = None

    def displayDataByType(self):

        if self.data is None:
            return

        regions = False
        points = False

        if self.checkBoxRegions.isChecked():
            regions = True

        if self.checkBoxPoints.isChecked():
            points = True

        if regions == True and points == True:
            self.sortfilter.setFilterRegExp(QRegExp())
        else:
            self.sortfilter.setFilterKeyColumn(1)

            if regions == True:
                self.sortfilter.setFilterRegExp('R')
            else:
                self.sortfilter.setFilterRegExp('P')

            self.sortfilter.setFilterRole(Qt.DisplayRole)

        self.selectById(self.searchId.text())


    def setTable(self, project, img):

        if self.project == project and self.activeImg == img:
            return

        self.project = project
        self.activeImg = img

        # establish UNIQUE connections, otherwise the slots will be called MORE THAN ONE TIME
        # when the signal is emitted

        if self.activeImg is not None:

            try:
                self.activeImg.annotations.blobUpdated[Blob,Blob].connect(self.updateBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.activeImg.annotations.blobAdded[object].connect(self.addBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.activeImg.annotations.blobRemoved[object].connect(self.removeBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.activeImg.annotations.blobClassChanged[str,object].connect(self.updateBlobClass, type=Qt.UniqueConnection)
            except:
                pass

            # do the same for point annotation

            try:
                self.activeImg.annotations.pointAdded[object].connect(self.addBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.activeImg.annotations.pointRemoved[object].connect(self.removeBlob, type=Qt.UniqueConnection)
            except:
                pass

            try:
                self.activeImg.annotations.annPointClassChanged[str,object].connect(self.updateBlobClass, type=Qt.UniqueConnection)
            except:
                pass

            self.data = self.activeImg.create_data_table()

        if self.model is None:
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
            self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
            self.data_table.setColumnWidth(1, 40)
            self.data_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.data_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
            self.data_table.horizontalHeader().showSection(0)
            self.data_table.update()

            self.data_table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40) }")
            self.data_table.selectionModel().selectionChanged.connect(lambda x: self.selectionChanged.emit())
        else:
            self.updateTable(self.data)

    @pyqtSlot(object)
    def addBlob(self, blob):

        if type(blob) == Point:
           new_row = {'Id': blob.id, 'Type': 'P', 'Class': blob.class_name, 'Area': 0}

        else:
            scale_factor = self.activeImg.pixelSize()
            area = round(blob.area * (scale_factor) * (scale_factor) / 100, 2)
            new_row = {'Id': blob.id, 'Type': 'R', 'Class': blob.class_name, 'Area': area}

        df = pd.DataFrame([new_row])
        self.data = pd.concat([self.data, df])

        # index is recalculated so that index i corresponds to row i
        self.data.reset_index(drop=True, inplace=True)

        self.updateTable(self.data)

    @pyqtSlot(object)
    def removeBlob(self, blob):

        index = self.data.index[self.data["Id"] == blob.id]
        self.data = self.data.drop(index=index)

        # index is recalculated so that index i corresponds to row i
        self.data.reset_index(drop=True, inplace=True)

        self.updateTable(self.data)

    @pyqtSlot(Blob,Blob)
    def updateBlob(self, oldblob, newblob):

        for i, row in self.data.iterrows():
            if row[0] == newblob.id:
                scale_factor = self.activeImg.pixelSize()
                self.data.loc[i, 'Area'] = round(newblob.area * (scale_factor) * (scale_factor) / 100, 2)
                self.data.loc[i, 'Class'] = newblob.class_name

        self.data_table.update()

    @pyqtSlot(str,object)
    def updateBlobClass(self, old_class_name, newblob):

        for i, row in self.data.iterrows():
            if row[0] == newblob.id:
                self.data.loc[i, 'Class'] = newblob.class_name

        self.data_table.update()

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

    @pyqtSlot(str)
    def selectById(self, text):

        try:
            blobid = int(text)
        except:
            return
        if blobid > 0:
            row = self.data.index[self.data["Id"] == blobid].to_list()
            self.selectRows(row)

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




