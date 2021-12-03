from PyQt5.QtWidgets import QGridLayout, QWidget, QScrollArea,QGroupBox, QColorDialog, QMessageBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, \
    QHBoxLayout, QVBoxLayout, QTextEdit, QTableWidget, QTableWidgetItem, QFrame

class QtPanelInfo(QGroupBox):

    def __init__(self, custom_data, parent=None):
        super(QtPanelInfo, self).__init__(parent)


        self.custom_data = custom_data
        self.lblIdValue = QLabel(" ")
        self.lblClass = QLabel("Empty")
        self.lblGenetValue = QLabel("")

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Genet: "))
        layout.addWidget(self.lblGenetValue)
        layout.addWidget(QLabel("  Id: "))
        layout.addWidget(self.lblIdValue)
        layout.addWidget(QLabel("  Class: "))
        layout.addWidget(self.lblClass)


        self.lblPerimeter = QLabel("  Perimeter: ")
        self.lblPerimeterValue = QLabel(" ")
        self.lblArea = QLabel("Area: ")
        self.lblAreaValue = QLabel(" ")
        self.lblSurfaceArea = QLabel("  Surf. area: ")
        self.lblSurfaceAreaValue = QLabel(" ")
        self.lblCentroid = QLabel("Centroid (px): ")
        self.lblCentroidValue = QLabel(" ")

        blobpanel_layoutH2 = QHBoxLayout()
        blobpanel_layoutH2.setSpacing(6)
        blobpanel_layoutH2.addWidget(self.lblCentroid)
        blobpanel_layoutH2.addWidget(self.lblCentroidValue)
        blobpanel_layoutH2.addWidget(self.lblPerimeter)
        blobpanel_layoutH2.addWidget(self.lblPerimeterValue)
        blobpanel_layoutH2.addStretch()

        blobpanel_layoutH3 = QHBoxLayout()
        blobpanel_layoutH3.addWidget(self.lblArea)
        blobpanel_layoutH3.addWidget(self.lblAreaValue)
        blobpanel_layoutH3.addWidget(self.lblSurfaceArea)
        blobpanel_layoutH3.addWidget(self.lblSurfaceAreaValue)
        blobpanel_layoutH3.addStretch()

        lblNote = QLabel("Note:")
        self.editNote = QTextEdit()
        self.editNote.setMinimumWidth(100)
        self.editNote.setMaximumHeight(50)
        self.editNote.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        #self.editNote.textChanged.connect(self.noteChanged)

        layout_blobpanel = QVBoxLayout()
        #layout_blobpanel.setSizeConstraint(QVBoxLayout.SetFixedSize)
        layout_blobpanel.addLayout(layout)
        layout_blobpanel.addLayout(blobpanel_layoutH2)
        layout_blobpanel.addLayout(blobpanel_layoutH3)
        layout_blobpanel.addWidget(lblNote)
        layout_blobpanel.addWidget(self.editNote)

        self.setLayout(layout_blobpanel)
        self.setMaximumHeight(200)


    def clear(self):
        self.blob = None
        self.lblIdValue.setText("")
        self.lblClass.setText("")
        self.lblGenetValue.setText("")
        txt = " "
        self.lblCentroidValue.setText(txt)
        txtP = "  Perimeter (cm):"
        self.lblPerimeter.setText(txtP)
        self.lblPerimeterValue.setText(txt)
        txtA = "Area (cm<sup>2</sup>):"
        self.lblArea.setText(txtA)
        self.lblAreaValue.setText(txt)
        txtS = "  Surf. area (cm<sup>2</sup>):"
        self.lblSurfaceArea.setText(txtS)
        self.lblSurfaceAreaValue.setText(txt)


    def update(self, blob):
        self.blob = blob
        self.lblIdValue.setText(str(blob.id))
        self.lblIdValue.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lblClass.setText(blob.class_name)
        self.lblClass.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lblGenetValue.setText("n.a." if blob.genet == None else str(blob.genet))
        self.lblGenetValue.setTextInteractionFlags(Qt.TextSelectableByMouse)

        if self.activeviewer.image.map_px_to_mm_factor == "":
            txt_perimeter = "  Perimeter (px):"
            txt_area = "Area (px<sup>2</sup>):"
            txt_surface_area = "  Surf. area (px<sup>2</sup>):"
            factor = 1.0
            scaled_perimeter = blob.perimeter
            scaled_area = blob.area
        else:
            txt_perimeter = "  Perimeter (cm):"
            txt_area = "Area (cm<sup>2</sup>):"
            txt_surface_area = "  Surf. area (cm<sup>2</sup>):"
            factor = float(self.activeviewer.image.map_px_to_mm_factor)
            scaled_perimeter = blob.perimeter * factor / 10.0
            scaled_area = blob.area * factor * factor / 100.0

        cx = blob.centroid[0]
        cy = blob.centroid[1]
        txt = "({:6.2f},{:6.2f})".format(cx, cy)
        self.lblCentroidValue.setText(txt)
        self.lblCentroidValue.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # perimeter
        self.lblPerimeter.setText(txt_perimeter)
        txt = "{:6.2f}".format(scaled_perimeter)
        self.lblPerimeterValue.setText(txt)
        self.lblPerimeterValue.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # area
        self.lblArea.setText(txt_area)
        txt = "{:6.2f}".format(scaled_area)
        self.lblAreaValue.setText(txt)
        self.lblAreaValue.setTextInteractionFlags(Qt.TextSelectableByMouse)

        # surface area
        self.lblSurfaceArea.setText(txt_surface_area)
        if self.activeviewer:
            if self.activeviewer.image.hasDEM():
                scaled_area = blob.surface_area * factor * factor / 100.0
                txt = "{:6.2f}".format(scaled_area)
                self.lblSurfaceAreaValue.setText(txt)
                self.lblSurfaceAreaValue.setTextInteractionFlags(Qt.TextSelectableByMouse)
            else:
                self.lblSurfaceAreaValue.setText("n.a.")
        # note
        self.editNote.setPlainText(blob.note)