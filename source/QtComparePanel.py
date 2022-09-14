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
from pathlib import Path

path = Path(__file__).parent.absolute()
imdir = str(path)
imdir =imdir.replace('source', '')

class TableModel(QAbstractTableModel):

    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data
        self.surface_area_mode_enabled = False

    def enableSurfaceAreaMode(self):

        self.surface_area_mode_enabled = True

    def disableSurfaceAreaMode(self):

        self.surface_area_mode_enabled = False

    def data(self, index, role):
        if role == Qt.TextAlignmentRole:
            if index.column() < 5:
                return Qt.AlignRight | Qt.AlignVCenter

        if role == Qt.BackgroundRole:
            return QColor(40, 40, 40)

        value = self._data.iloc[index.row(), index.column()]

        if role == Qt.DisplayRole:
            # if index.column() == 0 or index.column() == 1:
            #     return "" if math.isnan(value) else str(value)

            if index.column() == 0 or index.column() == 1 or index.column() == 2:
                if value < 0:
                    return ""

            # format floating point values
            if index.column() == 3 or index.column() == 4:
                txt = "{:.1f}".format(value) if value > 0 else ""
            else:
                txt = str(value)

            return txt
        
        if role == Qt.UserRole:
            if index.column() < 5:
                return float(value)
            return str(value)



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
                if head == "Blob1":
                    return "Id1"
                if head == "Blob2":
                    return "Id2"

                if head == "Area1" and self.surface_area_mode_enabled:
                    return "S. Area1"

                if head == "Area2" and self.surface_area_mode_enabled:
                    return "S. Area2"

                return head

            if orientation == Qt.Vertical:
                return str(self._data.index[section])

    def flags(self, index):

        value = self._data.iloc[index.row(), index.column()]

        if index.column() == 6 or index.column() == 7:
            return QAbstractTableModel.flags(self, index) | Qt.ItemIsEditable
        else:
            return QAbstractTableModel.flags(self, index)


class ComboBoxItemDelegate(QStyledItemDelegate):

    def __init__(self, parent = None):
        super(ComboBoxItemDelegate, self).__init__(parent)

        pass

    def createEditor(self, parent, option, index):

        cb = QComboBox(parent)
        column = index.column()

        if column == 6:
            cb.addItem("born")
            cb.addItem("gone")
            cb.addItem("grow")
            cb.addItem("same")
            cb.addItem("shrink")
            cb.addItem("n/s")
        elif column == 7:
            cb.addItem("none")
            cb.addItem("fuse")
            cb.addItem("split")
            cb.addItem("n/s")

        return cb

    def setEditorData(self, editor, index):

        cb = editor

        # get the index of the text in the combobox that matches the current
        # value of the item const
        currentText = index.data()
        cbIndex = cb.findText(currentText)
        # if it is valid, adjust the combobox
        if cbIndex >= 0:
            cb.setCurrentIndex(cbIndex)

    def setModelData(self, editor, model, index):

        cb = editor
        model.setData(index, cb.currentText(), Qt.EditRole)


class QtComparePanel(QWidget):

    filterChanged = pyqtSignal(str)
    areaModeChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super(QtComparePanel, self).__init__(parent)

        self.visibility_flags = []
        self.visibility_buttons = []
        self.labels_projects = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(150)

        self.data_table = QTableView()
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

        self.combodelegate1 = ComboBoxItemDelegate(self.data_table)
        self.combodelegate2 = ComboBoxItemDelegate(self.data_table)

        self.comboboxFilter = QComboBox()
        self.comboboxFilter.setMinimumWidth(80)
        self.comboboxFilter.addItem("All")
        self.comboboxFilter.addItem("Same")
        self.comboboxFilter.addItem("Born")
        self.comboboxFilter.addItem("Dead")
        self.comboboxFilter.addItem("Grow")
        self.comboboxFilter.addItem("Shrink")

        self.comboboxAreaMode = QComboBox()
        self.comboboxAreaMode.setMinimumWidth(80)
        self.comboboxAreaMode.addItem("Area")
        self.comboboxAreaMode.addItem("Surface Area")

        self.searchId1 = QLineEdit()
        self.searchId1.textChanged.connect(lambda text: self.selectById(text, True))
        self.searchId2 = QLineEdit()
        self.searchId2.textChanged.connect(lambda text: self.selectById(text, False))

#https://stackoverflow.com/questions/32476006/how-to-make-an-expandable-collapsable-section-widget-in-qt
        
        filter_layout = QGridLayout()
        filter_layout.addWidget(QLabel("Filter: "), 0, 0, Qt.AlignRight)
        filter_layout.addWidget(self.comboboxFilter, 0, 1)
        filter_layout.addWidget(QLabel("Compare: "), 0, 2)
        filter_layout.addWidget(self.comboboxAreaMode, 0, 3)
        filter_layout.addWidget(QLabel("Search Id1: "), 1, 0)
        filter_layout.addWidget(self.searchId1, 1, 1)
        filter_layout.addWidget(QLabel("Search Id2: "), 1, 2)
        filter_layout.addWidget(self.searchId2, 1, 3)


        self.searchWidget =QWidget()
        self.searchWidget.hide()
        #self.searchWidget.setStyleSheet("QLabel { text-align: right; }")
        self.searchWidget.setLayout(filter_layout)
        
        searchButton = QToolButton(self)
        searchButton.setStyleSheet("QToolButton { border: none; }")
        searchButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        searchButton.setArrowType(Qt.ArrowType.RightArrow)
        searchButton.setText("Search and filter")
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

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.genetAction = QAction("Genet", self)
        self.genetAction.setCheckable(True)
        self.genetAction.setChecked(True)
        self.genetAction.triggered.connect(
            lambda checked: self.data_table.horizontalHeader().setSectionHidden(0, not checked))

        self.areasAction = QAction("Area", self)
        self.areasAction.setCheckable(True)
        self.areasAction.setChecked(True)
        self.areasAction.triggered.connect(
            lambda checked:
                (self.data_table.horizontalHeader().setSectionHidden(3, not checked),
                self.data_table.horizontalHeader().setSectionHidden(4, not checked)))

        self.classAction = QAction("Class", self)
        self.classAction.setCheckable(True)
        self.classAction.setChecked(True)
        self.classAction.triggered.connect(
            lambda checked: self.data_table.horizontalHeader().setSectionHidden(5, not checked))

        self.actionAction = QAction("Action", self)
        self.actionAction.setCheckable(True)
        self.actionAction.setChecked(True)
        self.actionAction.triggered.connect(
            lambda checked: self.data_table.horizontalHeader().setSectionHidden(6, not checked))


        self.fuseAction = QAction("Split/Fuse", self)
        self.fuseAction.setCheckable(True)
        self.fuseAction.setChecked(True)
        self.fuseAction.triggered.connect(
            lambda checked: self.data_table.horizontalHeader().setSectionHidden(7, not checked))


        self.customContextMenuRequested.connect(self.openContextMenu)

        self.comboboxFilter.currentTextChanged.connect(self.changeFilter)
        self.comboboxAreaMode.currentTextChanged.connect(self.changeAreaMode)

        self.project = None
        self.correspondences = None
        self.img1idx = -1
        self.img2idx = -1
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
        menu.addAction(self.genetAction)
        menu.addAction(self.areasAction)
        menu.addAction(self.classAction)
        menu.addAction(self.actionAction)
        menu.addAction(self.fuseAction)

        viewer = self.sender()
        action = menu.exec_(viewer.mapToGlobal(position))

    def setTable(self, project, img1idx, img2idx):

        self.project = project
        self.img1idx = img1idx
        self.img2idx = img2idx
        self.sourceImg = project.images[img1idx]
        self.targetImg = project.images[img2idx]

        self.correspondences = project.getImagePairCorrespondences(img1idx, img2idx)
        #FIXME this is pretty expensive, can we avoid it?
        self.correspondences.updateAreas()
        self.data = self.correspondences.data

        try:
            self.sourceImg.annotations.blobUpdated.connect(self.sourceBlobUpdated, type=Qt.UniqueConnection)
        except:
            pass

        try:
            self.targetImg.annotations.blobUpdated.connect(self.targetBlobUpdated, type=Qt.UniqueConnection)
        except:
            pass

        if self.model is None:

            self.model = TableModel(self.data)
            self.sortfilter = QSortFilterProxyModel(self)
            self.sortfilter.setSourceModel(self.model)
            self.sortfilter.setSortRole(Qt.UserRole)
            self.data_table.setModel(self.sortfilter)

            self.data_table.setVisible(False)
            self.data_table.verticalHeader().hide()
            self.data_table.resizeColumnsToContents()
            self.data_table.setVisible(True)

            self.data_table.setItemDelegateForColumn(5, self.combodelegate1)
            self.data_table.setItemDelegateForColumn(6, self.combodelegate2)
            self.data_table.setEditTriggers(QAbstractItemView.DoubleClicked)

            self.data_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.data_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.data_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
            self.data_table.setColumnWidth(3, 80)
            self.data_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
            self.data_table.setColumnWidth(4, 80)
            self.data_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
            self.data_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
            self.data_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Fixed)
            self.data_table.setColumnWidth(7, 100)

            self.data_table.horizontalHeader().showSection(0)
            self.data_table.update()

            self.data_table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40) }")
        else:
            self.updateTable(self.correspondences)

    def sourceBlobUpdated(self, blob):
        for i, row in self.data.iterrows():
            if row[0] == blob.id:
                self.data.loc[i, 'Area1'] = self.correspondences.area_in_sq_cm(blob.area, True)

    def targetBlobUpdated(self, blob):
        for i, row in self.data.iterrows():
            if row[1] == blob.id:
                self.data.loc[i, 'Area2'] =  self.correspondences.area_in_sq_cm(blob.area, False)

    def clear(self):

        self.model = None
        self.data = None

        self.data_table.setModel(self.model)
        self.data_table.update()

    def updateData(self):

        self.data_table.update()

    def updateTable(self, corr):

        if corr is None or self.model is None:
            return

        self.correspondences = corr
        self.sortfilter.beginResetModel()
        self.model.beginResetModel()
        self.model._data = corr.data
        self.sortfilter.endResetModel()
        self.model.endResetModel()

        self.data_table.horizontalHeader().showSection(0)
        self.data_table.update()

    def selectById(self, text, isSource):
        try:
            blobid = int(text)
        except:
            return

        corr = self.project.getImagePairCorrespondences(self.img1idx, self.img2idx)
        sourcecluster, targetcluster, rows = corr.findCluster(blobid, isSource)
        self.selectRows(rows)

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

    def getAreaMode(self):

        return self.comboboxAreaMode.currentText().lower()

    @pyqtSlot(QModelIndex)
    def getData(self, index):

        pass
        #column = index.column()
        #row = index.row()
        #self.data_table.model().index(row, column).data()


    @pyqtSlot(str)
    def changeAreaMode(self, txt):

        if txt == "Area":
            self.model.disableSurfaceAreaMode()
        else:
            self.model.enableSurfaceAreaMode()

        self.data_table.resizeColumnsToContents()
        self.data_table.update()

        self.areaModeChanged.emit(txt.lower())

    @pyqtSlot(str)
    def changeFilter(self, txt):

        if self.data is None:
            return

        if txt == 'All':
            self.sortfilter.setFilterRegExp(QRegExp())
        else:
            self.sortfilter.setFilterKeyColumn(6)
            self.sortfilter.setFilterRegExp(txt.lower())
            self.sortfilter.setFilterRole(Qt.DisplayRole)

        self.filterChanged.emit(txt.lower())



