from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QWidget, QTabWidget, QSpinBox, QLineEdit, QDoubleSpinBox, \
    QCheckBox, QComboBox, QTableWidget, QTableWidgetItem, QGroupBox, QLabel, QHBoxLayout, QVBoxLayout, QTextEdit

import numpy as np

from source.Blob import Blob
from source.Point import Point

class QtPanelInfo(QTabWidget):

    def __init__(self, region_attributes, parent=None):
        super(QtPanelInfo, self).__init__(parent)

        self.region_attributes = region_attributes
        self.fields = {}
        self.attributes = []
        #self.setMaximumHeight(200)

        self.addTab(self.regionInfo(), "Properties")
        self.addTab(self.customInfo(), "Attributes")

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

        
    def updateRegionAttributes(self, region_attributes):

        self.clear()
        self.region_attributes = region_attributes
        self.removeTab(1)
        self.addTab(self.customInfo(), "Attributes")

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
        layout.setColumnStretch(0, 1);
        layout.setColumnStretch(1, 1);
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


            # elif attribute['type'] == 'boolean':
            #     input = QCheckBox()
            #     input.toggled.connect(lambda checked, name = name: self.assign(checked, name))

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

                value = ""
                if field == 'id' or field == 'class_name' or field == "note":
                    value = getattr(ann, field)
                    if type(value) == int:
                        value = str(value)

                self.fields[field].setText(value)


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

        