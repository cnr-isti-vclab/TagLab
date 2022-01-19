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
from PyQt5.QtCore import Qt, QAbstractTableModel, QItemSelectionModel, QSortFilterProxyModel, QRegExp, QModelIndex, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QSizePolicy, QComboBox, QLabel, QTableView, QHeaderView, \
    QHBoxLayout, QVBoxLayout, QAbstractItemView, QStyledItemDelegate, QAction, QMenu, QToolButton, QGridLayout, QLineEdit
from PyQt5.QtGui import QColor
import pandas as pd
from source.Blob import Blob

class TableModel(QAbstractTableModel):

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data
        self.surface_area_mode_enabled = False

    # def enableSurfaceAreaMode(self):
    #
    #     self.surface_area_mode_enabled = True
    #
    # def disableSurfaceAreaMode(self):
    #
    #     self.surface_area_mode_enabled = False

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
            if index.column() == 2 or index.column() == 3:
                txt = "{:.1f}".format(value) if value > 0 else ""
            else:
                txt = str(value)

            return txt
        
        # if role == Qt.UserRole:
        #     if index.column() < 5:
        #         return float(value)
        #     return str(value)



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

    # def flags(self, index):
    #
    #     value = self._data.iloc[index.row(), index.column()]
    #
    #     if index.column() == 6 or index.column() == 7:
    #         return QAbstractTableModel.flags(self, index) | Qt.ItemIsEditable
    #     else:
    #         return QAbstractTableModel.flags(self, index)


# class ComboBoxItemDelegate(QStyledItemDelegate):
#
#     def __init__(self, parent = None):
#         super(ComboBoxItemDelegate, self).__init__(parent)
#
#         pass
#
#     # def createEditor(self, parent, option, index):
#     #
#     #     cb = QComboBox(parent)
#     #     column = index.column()
#     #
#     #     if column == 6:
#     #         cb.addItem("born")
#     #         cb.addItem("gone")
#     #         cb.addItem("grow")
#     #         cb.addItem("same")
#     #         cb.addItem("shrink")
#     #         cb.addItem("n/s")
#     #     elif column == 7:
#     #         cb.addItem("none")
#     #         cb.addItem("fuse")
#     #         cb.addItem("split")
#     #         cb.addItem("n/s")
#     #
#     #     return cb
#
#     def setEditorData(self, editor, index):
#
#         cb = editor
#
#         # get the index of the text in the combobox that matches the current
#         # value of the item const
#         currentText = index.data()
#         cbIndex = cb.findText(currentText)
#         # if it is valid, adjust the combobox
#         if cbIndex >= 0:
#             cb.setCurrentIndex(cbIndex)
#
#     def setModelData(self, editor, model, index):
#
#         cb = editor
#         model.setData(index, cb.currentText(), Qt.EditRole)


class QtTablePanel(QWidget):

    filterChanged = pyqtSignal(str)
    # areaModeChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QtTablePanel, self).__init__(parent)

        self.visibility_flags = []
        self.visibility_buttons = []
        self.labels_projects = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(100)

        self.data_table = QTableView()
        self.data_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.data_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSortingEnabled(True)

        self.model = None
        self.data = None

        # self.combodelegate1 = ComboBoxItemDelegate(self.data_table)
        # self.combodelegate2 = ComboBoxItemDelegate(self.data_table)
        # #

        # DON'T NEED FILTER HERE - ONLY ONE SEARCH


        # self.comboboxFilter = QComboBox()
        # self.comboboxFilter.setMinimumWidth(80)
        # self.comboboxFilter.addItem("All")
        # self.comboboxFilter.addItem("Same")
        # self.comboboxFilter.addItem("Born")
        # self.comboboxFilter.addItem("Dead")
        # self.comboboxFilter.addItem("Grow")
        # self.comboboxFilter.addItem("Shrink")

        # self.comboboxAreaMode = QComboBox()
        # self.comboboxAreaMode.setMinimumWidth(80)
        # self.comboboxAreaMode.addItem("Area")
        # self.comboboxAreaMode.addItem("Surface Area")

        self.searchId = QLineEdit()
        self.searchId.textChanged.connect(lambda text: self.selectById(text, True))

        # self.searchId2 = QLineEdit()
        # self.searchId2.textChanged.connect(lambda text: self.selectById(text, False))

#https://stackoverflow.com/questions/32476006/how-to-make-an-expandable-collapsable-section-widget-in-qt
        
        filter_layout = QGridLayout()
        filter_layout.addWidget(QLabel("Search Id: "), 0, 0)
        filter_layout.addWidget(self.searchId, 0, 1)

        self.searchWidget =QWidget()
        self.searchWidget.hide()
        self.searchWidget.setLayout(filter_layout)

        searchButton = QToolButton(self)
        searchButton.setStyleSheet("QToolButton { border: none; }")
        searchButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        searchButton.setArrowType(Qt.ArrowType.RightArrow)
        searchButton.setText("Search")
        searchButton.setCheckable(True)
        searchButton.setChecked(False)

        def animate(checked):
            arrow_type = Qt.DownArrow if checked else Qt.RightArrow
            searchButton.setArrowType(arrow_type)
            self.searchWidget.setVisible(checked)

        searchButton.clicked.connect(animate)
        
        layout = QVBoxLayout()
        layout.addWidget(searchButton)
        layout.addWidget(self.searchWidget)
        layout.addWidget(self.data_table)
        self.setLayout(layout)

        self.data = None
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.areasAction = QAction("Area", self)
        self.areasAction.setCheckable(True)
        self.areasAction.setChecked(True)
        self.areasAction.triggered.connect(
            lambda checked:
                self.data_table.horizontalHeader().setSectionHidden(2, not checked))

        self.classAction = QAction("Class", self)
        self.classAction.setCheckable(True)
        self.classAction.setChecked(True)
        self.classAction.triggered.connect(
            lambda checked: self.data_table.horizontalHeader().setSectionHidden(1, not checked))

        self.sourceImg = None
        self.targetImg = None
        self.sortfilter = None

    def openContextMenu(self, position):

        menu = QMenu(self)
        menu.setAutoFillBackground(True)

        str = "QMenu::item:selected{\
            background-color: rgb(110, 110, 120);\
            color: rgb(255, 255, 255);\
            } QMenu::item:disabled { color:rgb(150, 150, 150); }"

        menu.setStyleSheet(str)
        menu.addAction(self.areasAction)
        menu.addAction(self.classAction)

        viewer = self.sender()
        action = menu.exec_(viewer.mapToGlobal(position))

    def setTable(self, project, img):

        self.project = project
        self.activeImg = img

        n_receivers = self.activeImg.annotations.receivers(self.activeImg.annotations.blobUpdated)
        if n_receivers > 1:
            self.activeImg.annotations.blobUpdated.disconnect()

        self.activeImg.annotations.blobUpdated.connect(self.updateBlob)
        self.activeImg.annotations.blobAdded.connect(self.addBlob)
        self.activeImg.annotations.blobRemoved.connect(self.removeBlob)

        self.data = self.activeImg.create_data_table()

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

    @pyqtSlot(Blob)
    def addBlob(self, blob):

        scale_factor = self.activeImg.pixelSize()
        area = round(blob.area * (scale_factor) * (scale_factor) / 100, 2)
        new_row = {'Id': blob.id, 'Class': blob.class_name, 'Area':  area }
        self.data = self.data.append(new_row, ignore_index=True)
        self.data.sort_values(by='Id', inplace=True)
        self.data.reset_index(drop=True, inplace=True)
        self.updateTable(self.data)

    @pyqtSlot(Blob)
    def removeBlob(self, blob):

        index = self.data.index[self.data["Id"] == blob.id]
        self.data = self.data.drop(index=index)

        self.data.sort_values(by='Id', inplace=True)
        self.data.reset_index(drop=True, inplace=True)
        self.updateTable(self.data)

    @pyqtSlot(Blob)
    def updateBlob(self, blob):

        for i, row in self.data.iterrows():
            if row[0] == blob.id:
                scale_factor = self.activeImg.pixelSize()
                self.data.loc[i, 'Area'] = round(blob.area * (scale_factor) * (scale_factor) / 100, 2)
                #self.data.loc[i, 'Surf. Area'] = round(blob.surface_area * (scale_factor) * (scale_factor) / 100, 2)
                self.data.loc[i, 'Class'] = blob.class_name

        self.data_table.update()

    def clear(self):

        self.model = None
        self.data = None

        self.data_table.setModel(self.model)
        self.data_table.update()

    def updateData(self):

        self.data_table.update()

    def updateTable(self, data_table):

        # if corr is None or self.model is None:
        #     return

        # self.correspondences = corr
        self.sortfilter.beginResetModel()
        self.model.beginResetModel()

        self.model._data = data_table
        #
        # self.sortfilter.endResetModel()
        self.model.endResetModel()

        self.data_table.horizontalHeader().showSection(0)
        self.data_table.update()

    def selectById(self, text):
        try:
            blobid = int(text)
        except:
            return
        #
        # corr = self.project.getImagePairCorrespondences(self.img1idx, self.img2idx)
        # sourcecluster, targetcluster, rows = corr.findCluster(blobid, isSource)
        self.selectRows(rows)


    def selectById(self, text):

        try:
            blobid = int(text)
        except:
            return

        # FARE UN FOR SU TABELLA
        #  self.data_table.loc[i, 'Area']
        # self.selectRows(row)

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

    @pyqtSlot(QModelIndex)
    def getData(self, index):

        pass
        #column = index.column()
        #row = index.row()
        #self.data_table.model().index(row, column).data()





