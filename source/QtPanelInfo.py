from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QAbstractTableModel, QItemSelectionModel, QSortFilterProxyModel, QRegExp, QRectF, QRect,QSize, QModelIndex,pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QGridLayout, QWidget, QTableView, QTabWidget, QSpinBox, QLineEdit, QDoubleSpinBox, QStyledItemDelegate, QHeaderView,QAbstractItemView,QSizePolicy,QStyleOptionProgressBar,\
    QCheckBox, QComboBox, QApplication, QTableWidget, QTableWidgetItem, QPushButton, QGroupBox, QLabel, QHBoxLayout, QVBoxLayout, QTextEdit, QStyle
from PyQt5.QtGui import QColor, QPixmap, QPainter, QPainterPath, QBrush, QLinearGradient
import numpy as np
from source.Blob import Blob
import pandas as pd
from collections import OrderedDict


class TableModel(QAbstractTableModel):

    def __init__(self, coralnet_pred):
        super(TableModel, self).__init__()
        self._data = coralnet_pred

    def data(self, index, role):

        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter

        if role == Qt.BackgroundRole:
            return QColor(40, 40, 40)

        value = self._data.iloc[index.row(), index.column()]

        if role == Qt.DecorationRole:

            # PROBLEMA, LA PIXMAP ha una dimensione insensata e non resiza con la cella, in teoria viene più bellino perchè ha i bordi arrotondati

            if index.column() == 1:
                value = value[1:-1]
                value = value.split(",")
                pxmap = QPixmap(150, 20)
                bar_progress_color = QColor(int(value[0]), int(value[1]), int(value[2]))
                percent = int(self._data.iloc[index.row(), 2])
                border_radius = 1
                bar_color = Qt.gray
                painter = QPainter(pxmap)
                painter.setRenderHint(QPainter.HighQualityAntialiasing)
                path = QPainterPath()
                path.addRoundedRect(QRectF(pxmap.rect()), border_radius, border_radius)
                painter.setClipPath(path)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(bar_color))
                painter.drawRect(pxmap.rect())

                if percent > 0:
                    painter.setBrush(bar_progress_color)
                    percent = percent / 100
                    percent_rect = QRect(0, 0, pxmap.width() * percent, pxmap.height())
                    painter.drawRect(percent_rect)

                painter.end()
                return pxmap


        if role == Qt.SizeHintRole and index.column()==1:

                return QSize(150,20)

        # SECONDO METODO COLORO DIRETTAMENTE BACKGROUND CELLA MA MI SA CHE LO STILESHEET SOVRASCRIVE IL QCOLOR SENZA UN ITEM DELEGATE

        # if role == Qt.BackgroundRole:
        #
        #     if index.column == 1:
        #
        #         #COLUMN_WIDTH = self.parent().columnWidth(index.column())
        #         COLUMN_WIDTH = 300
        #         value = value[1:-1]
        #         value = value.split(",")
        #         bar_progress_color = QColor(int(value[0]), int(value[1]), int(value[2]))
        #         percent = int(self._data.iloc[index.row(), 2])
        #         percent = percent / 100
        #         gradient = QLinearGradient(0, 0, COLUMN_WIDTH, 0)
        #         gradient.setColorAt(percent, bar_progress_color)
        #         gradient.setColorAt(percent + 0.0001, Qt.gray)
        #         brush = QBrush(gradient)
        #
        #         return brush
        #
        #     else:
        #         return QColor(40, 40, 40)


        if role == Qt.DisplayRole:

            if index.column() == 1:
                return ""

            elif index.column() == 2:
                txt = str(int(value)) + '%'

            else:
                txt = str(value)

            return txt



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
                if "Color" in head:
                    return " "
                return head

            if orientation == Qt.Vertical:
                return str(self._data.index[section])


class QtTablePred(QWidget):

    def __init__(self, parent=None):
        super(QtTablePred, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(150)
        self.pred_table = QTableView()
        self.pred_table.setMinimumWidth(400)
        self.pred_table.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.pred_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.pred_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pred_table.setSortingEnabled(False)
        #remove buttons on top and bottom of the scrollbar
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
        self.data_table = None
        layout = QVBoxLayout()
        layout.addWidget(self.pred_table)
        self.setLayout(layout)
        self.active_label_name = "Empty"



    def setPred(self, coralnet_sugg):


        self.coralnet_sugg = coralnet_sugg

        if self.coralnet_sugg is not None:

            self.data_table = pd.DataFrame(self.coralnet_sugg)
            # self.data_table = pd.DataFrame.from_dict(self.coralnet_sugg)

        if self.model is None:

            # Getting the Model
            self.model = TableModel(self.data_table)
            self.sortfilter = QSortFilterProxyModel(self)
            self.sortfilter.setSourceModel(self.model)
            self.sortfilter.setSortRole(Qt.UserRole)
            self.pred_table.setModel(self.sortfilter)
            self.pred_table.setVisible(False)
            self.pred_table.verticalHeader().hide()
            self.pred_table.setVisible(True)
            self.pred_table.setEditTriggers(QAbstractItemView.DoubleClicked)

            self.pred_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.pred_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.pred_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

            self.pred_table.setStyleSheet("QHeaderView::section { background-color: rgb(40,40,40) }")



class QtPanelInfo(QTabWidget):

    def __init__(self, region_attributes, labels, parent=None):
        super(QtPanelInfo, self).__init__(parent)

        self.region_attributes = region_attributes
        self.fields = {}
        self.attributes = []
        self.labels = labels
        self.active_image = None
        self.selected_point = None

        self.coralnet_sugg = {}
        self.sorted_coralnet_sugg = {}


        self.insertTab(0, self.regionInfo(), "Properties")
        self.insertTab(1, self.customInfo(), "Attributes")
        self.insertTab(2, QWidget(), "AI Suggestions")


        self.setAutoFillBackground(True)

        self.setStyleSheet("QTabWidget::pane {border: 1px solid white; padding: 4px}"
                           "QTabBar::tab:!selected {background: rgb(49,51,53); border: 0px solid #AAAAAA; "
                           "border-bottom-color: #C2C7CB; border-top-left-radius: 4px; "
                           "border-top-right-radius: 4px;"
                           "min-width: 8ex; padding: 2px;}"
                           "QTabBar::tab:selected {background: rgb(90,90,90); border: 0px solid #AAAAAA; "
                           "border-bottom-color: #C2C7CB; border-top-left-radius: 4px; "
                           "border-top-right-radius: 4px;"
                           "min-width: 8ex; padding: 2px;}")


    def setActiveImage(self, img, project):
        self.project = project
        self.active_image = img

    def updateDictionary(self, newdict):

        self.labels = {}
        self.labels = newdict


    @pyqtSlot(QModelIndex)
    def doubleClickedCell(self, index):

        if index.column() == 0 or index.column() == 1:
           oldindex = self.sugg_table.sortfilter.mapToSource(index)
           self.active_label_name = self.sugg_table.data_table['Class'][oldindex.row()]
           self.project.setPointClass(self.active_image, self.ann, self.active_label_name)


    def updateRegionAttributes(self, region_attributes):

        self.clear()
        self.region_attributes = region_attributes
        self.removeTab(1)
        self.insertTab(1, self.customInfo(), "Attributes")

    def regionInfo(self):

        layout = QGridLayout()

        fields = { 'id': 'Id:', 'class_name': 'Class:', 'genet': 'Genet:', 
            'perimeter': 'Perimeter:', 'area': 'Area:', 'surface_area': 'Surf. area:' }

        self.fields = {}
        row = 0
        col = 0
        for field in fields:
            label = QLabel(fields[field])
            layout.addWidget(label, row, col)
            value = self.fields[field] = QLabel('')
            layout.addWidget(value, row, col+1)
            col += 2
            if col == 4:
                row += 1
                col = 0

        layout.setRowStretch(layout.rowCount(), 1)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def customInfo(self):

        self.attributes = []
        layout = QGridLayout()
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        widget = QWidget()
        widget.setLayout(layout)

        row = 0
        for attribute in self.region_attributes.data:
            name = attribute['name']
            layout.addWidget(QLabel(name), row, 0)
            

            if attribute['type'] == 'string':
                input = QLineEdit()
                input.textChanged.connect(lambda text, name = name: self.assign(text, name))
            elif attribute['type'] == 'integer number':
                input = QSpinBox()
                max = attribute['max'] if 'max' in attribute.keys() else 2147483647
                if max is None:
                     max = 2147483647
                input.setMaximum(int(max))
                min = attribute['min'] if 'min' in attribute.keys() else -2147483647
                if min is None:
                     min = -2147483647
                input.setMinimum(int(min))
                input.valueChanged.connect(lambda value, name = name: self.assign(value, name))

            elif attribute['type'] == 'decimal number':
                input = QDoubleSpinBox()
                max = attribute['max'] if 'max' in attribute.keys() else 1e20
                if max is None:
                    max = 1e20
                input.setMaximum(max)
                min = attribute['min'] if 'min' in attribute.keys() else -1e20
                if min is None:
                    min = -1e20
                input.setMinimum(min)
                input.valueChanged.connect(lambda value, name=name: self.assign(value, name))

            elif attribute['type'] == 'keyword':
                input = QComboBox()
                input.addItem('')
                input.addItems(attribute['keywords'])
                input.currentTextChanged.connect(lambda text, name = name: self.assign(text, name))

            layout.addWidget(input, row, 1)
            row += 1
            self.attributes.append(input)

        layout.addWidget(QLabel("Notes:"), row, 0)
        note = self.fields['note'] = QTextEdit()
        note.setMaximumHeight(50)
        note.textChanged.connect(self.updateNotes)
        layout.addWidget(note, row+1, 0, 1, 2)
        return widget





    def updateMachineSuggestionsInfo(self, sugg_table):


        self.sugg_table = sugg_table
        self.removeTab(2)
        self.insertTab(2, self.sugg_table, "AI Suggestions")


    def assign(self, text, name):

        if self.ann == None:
            return

        self.ann.data[name] = text

    def updateNotes(self):

        if self.ann is None:
            return

        self.ann.note = self.fields['note'].document().toPlainText()


    def clear(self):

        self.ann = None

        for field in self.fields:
            self.fields[field].setText("")

        for input, attribute in zip(self.attributes, self.region_attributes.data):
            if attribute['type'] == 'string':
                input.setText('')
            elif attribute['type'] == 'integer number':
                input.clear()
            elif attribute['type'] == 'decimal number':
                input.clear()
            # elif attribute['type'] == 'boolean':
            #     input.setChecked(False)
            elif attribute['type'] == 'keyword':
                input.setCurrentText('')

        self.removeTab(2)
        self.insertTab(2, QWidget(), "AI Suggestions")
        self.selected_point = None


    def update(self, ann, scale_factor):

        self.clear()

        self.ann = ann

        if type(ann) == Blob:
            for field in self.fields:
                value = getattr(ann, field)
                if field == 'area':
                    value = round(value * (scale_factor) * (scale_factor) / 100, 2)
                if field ==  'surface_area':
                    value = round(value * (scale_factor) * (scale_factor) / 100, 2)
                if field ==  'perimeter':
                    value = round(value * scale_factor / 10, 1)
                if type(value) == float or type(value) == np.float64 or type(value) == np.float32:
                    value = "{:6.1f}".format(value)
                if type(value) == int:
                    value = str(value)

                self.fields[field].setText(value)


        else:

            for field in self.fields:
                value = ''
                if field == 'id' or field == 'class_name' or field == "note":
                    value = getattr(ann, field)
                    if type(value) == int:
                        value = str(value)

                self.fields[field].setText(value)

            if 'Machine suggestion 1' in ann.data.keys():


                coralnet_sugg = {}
                coralnet_conf = {}
                coralnet_colors = []
                self.sorted_coralnet_sugg = {}

                for key in ann.data.keys():
                    if "suggestion" in key:
                        coralnet_sugg[key] = ann.data[key]
                    elif "confidence" in key:
                        coralnet_conf[key] = ann.data[key]

                for classname in list(coralnet_sugg.values()):
                    color = str(self.labels[classname].fill)
                    coralnet_colors.append(color)

                self.sorted_coralnet_sugg = {"Class": list(coralnet_sugg.values()),
                                             "Color": coralnet_colors,
                                             "Confidence": list(coralnet_conf.values())}

                if len(self.sorted_coralnet_sugg) != 0:
                    sugg_table = QtTablePred()
                    sugg_table.setPred(self.sorted_coralnet_sugg)
                    sugg_table.pred_table.doubleClicked.connect(self.doubleClickedCell)
                    self.updateMachineSuggestionsInfo(sugg_table)




        for input, attribute in zip(self.attributes, self.region_attributes.data):
            key = attribute['name']
            if not key in ann.data:
                continue
            value = ann.data[key]
            if value is None:
                continue;
            if attribute['type'] == 'string':
                input.setText(value)
            elif attribute['type'] == 'integer number':
                 input.setValue(value)
            elif attribute['type'] == 'decimal number':
                input.setValue(value)
            # elif attribute['type'] == 'boolean':
            #      input.setChecked(value)
            elif attribute['type'] == 'keyword':
                input.setCurrentText(value)

        