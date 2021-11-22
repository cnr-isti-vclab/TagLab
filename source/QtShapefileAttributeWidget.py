from PyQt5.QtCore import Qt, QAbstractTableModel, QItemSelectionModel, QSortFilterProxyModel, QRegExp, QModelIndex, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QSizePolicy, QComboBox, QLabel, QTableView, QHeaderView, \
    QHBoxLayout, QVBoxLayout, QAbstractItemView, QStyledItemDelegate, QAction, QMenu, QToolButton, QGridLayout, QLineEdit
from PyQt5.QtGui import QColor
from pathlib import Path

class PandasModelShape(QAbstractTableModel):
    def __init__(self, data, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = data
        print('bu')

    def headerData(self, section, orientation, role):

        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                head = str(self._data.columns[section])
                return head
            if orientation == Qt.Vertical:
                return str(self._data.index[section])


    def rowCount(self, parent=None):
        return len(self._data.values)

    def columnCount(self, parent=None):
        return self._data.columns.size

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                element = str(self._data.iloc[index.row(),index.column()])
                print(element)
                return element
        return ""

class QtAttributeWidget(QWidget):

    # Data.dtypes - returns fields types
    # Data.columns - returns fields names
    # Data.pop('class') - returns column 'class'

    filterChanged = pyqtSignal(str)
    areaModeChanged = pyqtSignal(str)

    def __init__(self, data, parent=None):
        super(QtAttributeWidget, self).__init__(parent)

        self.data = data

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        layout = QVBoxLayout()

        self.data_table = QTableView()
        self.data_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.data_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSortingEnabled(True)
        self.data_table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40) }")


        self.model = PandasModelShape(data)
        self.data_table.setModel(self.model)
        self.data_table.setMinimumWidth(500)
        self.data_table.setMinimumHeight(100)

        self.data_table.setVisible(False)
        self.data_table.verticalHeader().hide()
        self.data_table.resizeColumnsToContents()
        self.data_table.setVisible(True)

        self.data_table.horizontalHeader().showSection(0)
        self.data_table.update()

        # self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.data_table.update()
        # self.data_table.resizeColumnsToContents()
        self.data_table.horizontalHeader().setStretchLastSection(False)

        layout.addWidget(self.data_table)
        self.setLayout(layout)
        self.setWindowTitle("Shapefile Attribute Editor")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)




