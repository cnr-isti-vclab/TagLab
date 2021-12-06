from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QWidget, QTabWidget, QSpinBox, QLineEdit, QCheckBox, QComboBox, QTableWidget, QTableWidgetItem, QGroupBox, QLabel, QHBoxLayout, QVBoxLayout, QTextEdit

class QtPanelInfo(QTabWidget):

    def __init__(self, region_attributes, parent=None):
        super(QtPanelInfo, self).__init__(parent)

        self.region_attributes = region_attributes
        #self.setMaximumHeight(200)

        self.addTab(self.regionInfo(), "Region Info")
        self.addTab(self.customInfo(), "Attributes")
        self.fields = []
        
    def updateRegionAttributes(self, region_attributes):
        self.clear()
        self.region_attributes = region_attributes
        self.removeTab(1)
        self.addTab(self.customInfo(), "Attributes")

    def regionInfo(self):

        layout = QGridLayout()

        fields = { 'id': 'Id:', 'class_name': 'Class:', 'genet': 'Genet:', 
            'perimeter': 'Perimenter:', 'area': 'Area:', 'surface_area': 'Surf. area:' }

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
        layout.addWidget(QLabel("Notes:"), row, 0)
        note = self.fields['note'] = QTextEdit()
        note.setMaximumHeight(100)
        note.textChanged.connect(self.updateNotes)
        layout.addWidget(note, row+1, 0, 1, 4)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def customInfo(self):
        self.fields = []
        layout = QGridLayout()
        widget = QWidget()
        widget.setLayout(layout)

        if len(self.region_attributes.data) == 0:
            layout.addWidget(QLabel("See project -> Region attributes... to configure additional attributes"))
            return widget

        row = 0
        for field in self.region_attributes.data:
            layout.addWidget(QLabel(field['name']), row, 0)
            if field['type'] == 'string':
                input = QLineEdit()
            elif field['type'] == 'number':
                input = QSpinBox()
                input.setMaximum(field['max'])
                input.setMinimum(field['min'])
            elif field['type'] == 'boolean':
                input = QCheckBox()
            elif field['type'] == 'keyword':
                input = QComboBox()
                input.addItems(field['keywords'])

            layout.addWidget(input)
            self.fields.append(input)

        return widget
        



    def updateNotes(self):
        if self.blob is None:
            return
        self.blob.note = self.fields['note'].document().toPlainText()


    def clear(self):
        self.blob = None
        for field in self.fields:
            self.fields[field].setText("")

    def update(self, blob):
        self.blob = blob

        for field in self.fields:
            value = getattr(blob, field)
            if type(value) == float:
                value = "{:6.1f}".format(value)
            if type(value) == int:
                value = str(value)
            
            self.fields[field].setText(value)
        