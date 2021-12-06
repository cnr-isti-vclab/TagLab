from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QWidget, QTabWidget, QTableWidget, QTableWidgetItem, QGroupBox, QLabel, QHBoxLayout, QVBoxLayout, QTextEdit

class QtPanelInfo(QTabWidget):

    def __init__(self, custom_data, parent=None):
        super(QtPanelInfo, self).__init__(parent)

        self.custom_data = custom_data
        self.setMaximumHeight(200)

        self.addTab(self.regionInfo(), "Region Info")
        

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
        note.textChanged.connect(self.updateNotes)
        layout.addWidget(note, row+1, 0, 1, 4)

        widget = QWidget()
        widget.setLayout(layout)
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
                value = "{:6.2f}".format(value)
            if type(value) == int:
                value = str(value)
            
            self.fields[field].setText(value)
        # self.lblIdValue.setText(str(blob.id))
        # self.lblIdValue.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # self.lblClass.setText(blob.class_name)
        # self.lblClass.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # self.lblGenetValue.setText("n.a." if blob.genet == None else str(blob.genet))
        # self.lblGenetValue.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # if self.activeviewer.image.map_px_to_mm_factor == "":
        #     txt_perimeter = "  Perimeter (px):"
        #     txt_area = "Area (px<sup>2</sup>):"
        #     txt_surface_area = "  Surf. area (px<sup>2</sup>):"
        #     factor = 1.0
        #     scaled_perimeter = blob.perimeter
        #     scaled_area = blob.area
        # else:
        #     txt_perimeter = "  Perimeter (cm):"
        #     txt_area = "Area (cm<sup>2</sup>):"
        #     txt_surface_area = "  Surf. area (cm<sup>2</sup>):"
        #     factor = float(self.activeviewer.image.map_px_to_mm_factor)
        #     scaled_perimeter = blob.perimeter * factor / 10.0
        #     scaled_area = blob.area * factor * factor / 100.0

        # cx = blob.centroid[0]
        # cy = blob.centroid[1]
        # txt = "({:6.2f},{:6.2f})".format(cx, cy)
        # self.lblCentroidValue.setText(txt)
        # self.lblCentroidValue.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # # perimeter
        # self.lblPerimeter.setText(txt_perimeter)
        # txt = "{:6.2f}".format(scaled_perimeter)
        # self.lblPerimeterValue.setText(txt)
        # self.lblPerimeterValue.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # # area
        # self.lblArea.setText(txt_area)
        # txt = "{:6.2f}".format(scaled_area)
        # self.lblAreaValue.setText(txt)
        # self.lblAreaValue.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # # surface area
        # self.lblSurfaceArea.setText(txt_surface_area)
        # if self.activeviewer:
        #     if self.activeviewer.image.hasDEM():
        #         scaled_area = blob.surface_area * factor * factor / 100.0
        #         txt = "{:6.2f}".format(scaled_area)
        #         self.lblSurfaceAreaValue.setText(txt)
        #         self.lblSurfaceAreaValue.setTextInteractionFlags(Qt.TextSelectableByMouse)
        #     else:
        #         self.lblSurfaceAreaValue.setText("n.a.")
        # # note
        # self.editNote.setPlainText(blob.note)