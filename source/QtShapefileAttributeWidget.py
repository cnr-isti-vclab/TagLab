from PyQt5.QtCore import Qt, QAbstractTableModel, QItemSelectionModel, QSortFilterProxyModel, QRegExp, QModelIndex, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QSizePolicy,QCheckBox, QPushButton,QRadioButton, QComboBox, QLabel, QTableView, QHeaderView, QMessageBox,\
    QHBoxLayout, QVBoxLayout, QAbstractItemView, QStyledItemDelegate, QAction, QMenu, QToolButton, QGridLayout, QLineEdit
from PyQt5.QtGui import QColor
from pathlib import Path

class PandasModelShape(QAbstractTableModel):
    def __init__(self, data, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = data

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
                element = str(self._data.iloc[index.row(), index.column()])
                return element

class QtAttributeWidget(QWidget):

    # Data.dtypes - returns fields types
    # Data.columns - returns fields names
    # Data.pop('class') - returns column 'class'

    shapefilechoices = pyqtSignal(str, list)

    def __init__(self, data, parent=None):
        super(QtAttributeWidget, self).__init__(parent)

        self.data = data
        self.checkBoxes = []
        self.setStyleSheet("background-color: rgb(40,40,40); color: white")
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(300)
        self.setMinimumHeight(100)

        layout = QVBoxLayout()

        self.data_table = QTableView()
        self.data_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.data_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectColumns)
        self.data_table.setSortingEnabled(True)
        self.data_table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40) }")

        self.model = PandasModelShape(data)


        self.data_table.setModel(self.model)
        self.data_table.setMinimumWidth(500)
        self.data_table.setMinimumHeight(300)

        self.data_table.setVisible(False)
        self.data_table.verticalHeader().hide()
        self.data_table.resizeColumnsToContents()
        self.data_table.setVisible(True)

        self.data_table.horizontalHeader().showSection(0)
        self.data_table.update()

        # user variables
        self.shape = None
        self.fieldslist = []


        FIELDS_FOR_ROW = 6

        lbltype = QLabel("Shapefile type:")

        self.types_layout = QHBoxLayout()
        self.chkBoxlabel = QRadioButton("Labels")
        self.chkBoxlabel.setChecked(True)
        # self.chkBoxlabel.toggled.connect(lambda: self.btnstate(self.chkBoxlabel))
        self.chkBoxsampling = QRadioButton("Sampling")
        # self.chkBoxlabel.toggled.connect(lambda: self.btnstate(self.chkBoxsampling))
        # chkBoxsampling.QRadioButton(False)
        self.chkBoxother = QRadioButton("Other")
        # self.chkBoxlabel.toggled.connect(lambda: self.btnstate(self.chkBoxother))
        # self.chkBoxother.setChecked(False)
        self.types_layout.addWidget(self.chkBoxlabel)
        self.types_layout.addWidget(self.chkBoxother)
        self.types_layout.addWidget(self.chkBoxsampling)

        self.choice_layout = QVBoxLayout()
        self.choice_layout.addWidget(lbltype)
        self.choice_layout.addLayout(self.types_layout)

        lbl = QLabel("Fields to import:")

        self.fields_layout = QVBoxLayout()
        self.fields = None

        for i in range(0, len(self.data.columns)):
            field = self.data.columns[i]
            chkBox = QCheckBox(field)
            chkBox.setChecked(True)

            if i % FIELDS_FOR_ROW == 0:
                if self.fields is not None:
                    self.fields.addStretch()
                self.fields = QHBoxLayout()
                self.fields.setAlignment(Qt.AlignLeft)
                self.fields_layout.addLayout(self.fields)

            self.checkBoxes.append(chkBox)
            self.fields.addWidget(chkBox)
            self.fields.addStretch()

            #need of vertical space?
            if i % FIELDS_FOR_ROW  < FIELDS_FOR_ROW - 1 and i < len(self.data.columns) - 1:
                self.fields_layout.addSpacing(5)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.cancel)

        self.btnOk = QPushButton("Ok")
        self.btnOk.clicked.connect(self.accept)

        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnCancel)
        buttons_layout.addWidget(self.btnOk)


        layout.addLayout(self.choice_layout)
        layout.addSpacing(30)
        layout.addWidget(self.data_table)
        layout.addSpacing(30)
        layout.addWidget(lbl)
        layout.addLayout(self.fields_layout)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)
        self.setWindowTitle("Shapefile Attribute Editor")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)


    @pyqtSlot()
    def cancel(self):
        #clean up everything before closing
        self.model = None
        self.data = None
        self.data_table.setModel(self.model)
        self.data_table.update()
        self.close()

    # questo mi deve tornare la lista di fields selezionati

    @pyqtSlot()
    def addfields(self):

        for checkbox in self.checkBoxes:
            if checkbox.isChecked():
                # print(checkbox.text())
                self.fieldslist.append(self.data[str(checkbox.text())])
                # self.data[str(checkbox.text())][i] returns i element
                print(self.fieldslist)

    # questo mi deve tornare il tipo di shape


    def accept(self):

        if self.chkBoxlabel.isChecked():
           self.shape = 'Label'

        elif self.chkBoxsampling.isChecked():
             self.shape = 'Sampling'

        else:
           self.shape = 'Other'

        self.fieldlist =[]
        for checkbox in self.checkBoxes:
            if checkbox.isChecked():
                self.fieldlist.append(checkbox.text())
                # self.fieldslist.append(self.data[str(checkbox.text())])
                # self.data[str(checkbox.text())][i] returns i element
                # print(self.fieldslist)
        self.shapefilechoices.emit(self.shape, self.fieldlist)
