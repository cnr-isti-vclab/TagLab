from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtWidgets import QSizePolicy, QCheckBox, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QRadioButton, QButtonGroup, QGroupBox, QMessageBox,  QWidget, QComboBox
from source import genutils

class QtSampleWidget(QWidget):

    # choosedSample = pyqtSignal(int)
    closewidget = pyqtSignal()
    validchoices= pyqtSignal()

    def __init__(self, active_image, working_area, parent=None):
        super(QtSampleWidget, self).__init__(parent)

        self.choosednumber = None
        self.working_area = working_area

        self.setStyleSheet(":enabled {background-color: rgb(40,40,40); color: white} :disabled {color: rgb(110,110,110)}")
        self.lineedit_style = ":enabled {background-color: rgb(55,55,55); color: rgb(255,255,255); border: 1px solid rgb(90,90,90)} " \
                              ":disabled {background-color: rgb(35,35,35); color: rgb(110,110,110); border: 1px solid rgb(70,70,70)}"

        MAXIMUM_WIDTH_EDIT = 160

        # sampling single area (manual)
        self.group_SA = QGroupBox()
        self.radio_SA = QRadioButton("Add a single sampling area")

        area_icon = QIcon("icons\\select_area.png")
        self.btn_select_area_SA = QPushButton("")
        self.btn_select_area_SA.setIcon(area_icon)
        self.btn_select_area_SA.setMinimumWidth(30)

        self.lbl_top_SA = QLabel("Top: ")
        self.lbl_left_SA = QLabel("Left: ")
        self.edit_top_SA = QLineEdit()
        self.edit_top_SA.setStyleSheet(self.lineedit_style)
        self.edit_top_SA.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.edit_left_SA = QLineEdit()
        self.edit_left_SA.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.edit_left_SA.setStyleSheet(self.lineedit_style)
        self.lbl_top_px_SA = QLabel("px")
        self.lbl_left_px_SA = QLabel("px")

        self.layoutH1 = QHBoxLayout()
        self.layoutH1.addWidget(self.btn_select_area_SA)
        self.layoutH1.addWidget(self.lbl_top_SA)
        self.layoutH1.addWidget(self.edit_top_SA)
        self.layoutH1.addWidget(self.lbl_top_px_SA)
        self.layoutH1.addWidget(self.lbl_left_SA)
        self.layoutH1.addWidget(self.edit_left_SA)
        self.layoutH1.addWidget(self.lbl_left_px_SA)
        self.layoutH1.addStretch()

        self.layoutV1 = QVBoxLayout()
        self.layoutV1.addWidget(self.radio_SA)
        self.layoutV1.addLayout(self.layoutH1)
        self.group_SA.setLayout(self.layoutV1)

        # sampling Working Area (randomly)
        self.group_WA = QGroupBox()
        self.radio_WA = QRadioButton("Sampling the Working Area with multiple random areas")

        #self.checkbox_overlap_areas_WA = QCheckBox("Overlap")
        #self.checkbox_overlap_areas_WA.setChecked(False)

        self.lbl_areas_WA = QLabel("# areas:")
        self.edit_number_areas_WA = QLineEdit()
        self.edit_number_areas_WA.setStyleSheet(self.lineedit_style)
        self.edit_number_areas_WA.setMaximumWidth(MAXIMUM_WIDTH_EDIT)

        self.layoutH2 = QHBoxLayout()
        self.layoutH2.addWidget(self.lbl_areas_WA)
        self.layoutH2.addWidget(self.edit_number_areas_WA)
        #self.layoutH2.addWidget(self.checkbox_overlap_areas_WA)
        self.layoutH2.addStretch()

        self.layoutV2 = QVBoxLayout()
        self.layoutV2.addWidget(self.radio_WA)
        self.layoutV2.addLayout(self.layoutH2)
        self.group_WA.setLayout(self.layoutV2)

        # sampling transect (with equi-spaced or randomly positioned areas)
        self.group_T = QGroupBox()
        self.radio_T = QRadioButton("Sampling a transect with multiple sampling areas")

        self.lbl_areas_T = QLabel("# areas:")
        self.edit_number_areas_T = QLineEdit()
        self.edit_number_areas_T.setStyleSheet(self.lineedit_style)
        self.edit_number_areas_T.setMaximumWidth(MAXIMUM_WIDTH_EDIT)

        #self.checkbox_overlap_areas_T = QCheckBox("Overlap")
        #self.checkbox_overlap_areas_T.setChecked(True)

        self.lbl_method_T = QLabel("Method:")
        self.combo_method_T = QComboBox()
        self.combo_method_T.setMinimumWidth(180)
        self.combo_method_T.addItem('Equi-spaced')
        self.combo_method_T.addItem('Random')

        line_icon = QIcon("icons\\select_line.png")
        self.btn_select_transect_T = QPushButton("")
        self.btn_select_transect_T.setIcon(line_icon)
        self.btn_select_transect_T.setMinimumWidth(30)

        self.lbl_x1 = QLabel("x1:")
        self.edit_x1 = QLineEdit()
        self.edit_x1.setStyleSheet(self.lineedit_style)
        self.edit_x1.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.lbl_x1_px = QLabel("px")
        self.lbl_y1 = QLabel("y1:")
        self.edit_y1 = QLineEdit()
        self.edit_y1.setStyleSheet(self.lineedit_style)
        self.edit_y1.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.lbl_y1_px = QLabel("px")
        self.lbl_x2 = QLabel("x2:")
        self.edit_x2 = QLineEdit()
        self.edit_x2.setStyleSheet(self.lineedit_style)
        self.edit_x2.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.lbl_x2_px = QLabel("px")
        self.lbl_y2 = QLabel("y2:")
        self.edit_y2 = QLineEdit()
        self.edit_y2.setStyleSheet(self.lineedit_style)
        self.edit_y2.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.lbl_y2_px = QLabel("px")

        self.layoutH3 = QHBoxLayout()
        self.layoutH3.addWidget(self.lbl_areas_T)
        self.layoutH3.addWidget(self.edit_number_areas_T)
        self.layoutH3.addWidget(self.lbl_method_T)
        self.layoutH3.addWidget(self.combo_method_T)
        #self.layoutH3.addWidget(self.checkbox_overlap_areas_T)
        self.layoutH3.addStretch()

        self.layoutH4 = QHBoxLayout()
        self.layoutH4.addWidget(self.btn_select_transect_T)
        self.layoutH4.addWidget(self.lbl_x1)
        self.layoutH4.addWidget(self.edit_x1)
        self.layoutH4.addWidget(self.lbl_x1_px)
        self.layoutH4.addWidget(self.lbl_y1)
        self.layoutH4.addWidget(self.edit_y1)
        self.layoutH4.addWidget(self.lbl_y1_px)
        self.layoutH4.addWidget(self.lbl_x2)
        self.layoutH4.addWidget(self.edit_x2)
        self.layoutH4.addWidget(self.lbl_x2_px)
        self.layoutH4.addWidget(self.lbl_y2)
        self.layoutH4.addWidget(self.edit_y2)
        self.layoutH4.addWidget(self.lbl_y2_px)
        self.layoutH4.addStretch()

        self.layoutV3 = QVBoxLayout()
        self.layoutV3.addWidget(self.radio_T)
        self.layoutV3.addLayout(self.layoutH3)
        self.layoutV3.addLayout(self.layoutH4)
        self.group_T.setLayout(self.layoutV3)

        # sampling settings
        self.group_settings = QGroupBox()
        self.group_settings.setTitle("Sampling area")

        self.lbl_method = QLabel("Method:")

        self.combo_method = QComboBox()
        self.combo_method.setMinimumWidth(300)
        self.combo_method.addItem("Grid")
        self.combo_method.addItem("Random")
        self.combo_method.addItem("Stratified")

        self.lbl_number = QLabel("# Points:")
        self.edit_number = QLineEdit()
        self.edit_number.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")

        self.lbl_offset = QLabel("Offset: ")
        self.edit_offset_px = QLineEdit()
        self.edit_offset_px.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.lbl_offset_px = QLabel("px")
        self.edit_offset_cm = QLineEdit()
        self.edit_offset_cm.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.lbl_offset_cm = QLabel("cm")

        self.lbl_width = QLabel("Width: ")
        self.edit_width_px = QLineEdit()
        self.edit_width_px.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.lbl_width_px = QLabel("px")
        self.edit_width_cm = QLineEdit()
        self.edit_width_cm.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.lbl_width_cm = QLabel("cm")

        self.lbl_height = QLabel("Height: ")
        self.edit_height_px = QLineEdit()
        self.edit_height_px.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.lbl_height_px = QLabel("px")
        self.edit_height_cm = QLineEdit()
        self.edit_height_cm.setStyleSheet("background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)")
        self.lbl_height_cm = QLabel("cm")

        self.edit_offset_px.setText("0")
        self.edit_offset_cm.setText("0.0")

        self.layoutVP1 = QVBoxLayout()
        self.layoutVP1.setAlignment(Qt.AlignRight)
        self.layoutVP1.addWidget(self.lbl_method)
        self.layoutVP1.addWidget(self.lbl_number)
        self.layoutVP1.addWidget(self.lbl_offset)
        self.layoutVP1.addWidget(self.lbl_width)
        self.layoutVP1.addWidget(self.lbl_height)

        self.layout_width = QHBoxLayout()
        self.layout_width.addWidget(self.edit_width_px)
        self.layout_width.addWidget(self.lbl_width_px)
        self.layout_width.addWidget(self.edit_width_cm)
        self.layout_width.addWidget(self.lbl_width_cm)

        self.layout_height = QHBoxLayout()
        self.layout_height.addWidget(self.edit_height_px)
        self.layout_height.addWidget(self.lbl_height_px)
        self.layout_height.addWidget(self.edit_height_cm)
        self.layout_height.addWidget(self.lbl_height_cm)

        self.layout_method = QHBoxLayout()
        self.layout_method.addWidget(self.combo_method)
        self.layout_method.addStretch()

        self.layout_number = QHBoxLayout()
        self.layout_number.addWidget(self.edit_number)
        self.layout_number.addStretch()

        self.layout_offset = QHBoxLayout()
        self.layout_offset.addWidget(self.edit_offset_px)
        self.layout_offset.addWidget(self.lbl_offset_px)
        self.layout_offset.addWidget(self.edit_offset_cm)
        self.layout_offset.addWidget(self.lbl_offset_cm)
        self.layout_offset.addStretch()

        self.layoutVP2 = QVBoxLayout()
        self.layoutVP2.addLayout(self.layout_method)
        self.layoutVP2.addLayout(self.layout_number)
        self.layoutVP2.addLayout(self.layout_offset)
        self.layoutVP2.addLayout(self.layout_width)
        self.layoutVP2.addLayout(self.layout_height)

        self.layoutHP2 = QHBoxLayout()
        self.layoutHP2.addLayout(self.layoutVP1)
        self.layoutHP2.addLayout(self.layoutVP2)
        self.group_settings.setLayout(self.layoutHP2)

        self.layout_buttons = QHBoxLayout()

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.setMinimumHeight(40)
        self.btnCancel.clicked.connect(self.close)
        self.btnOK = QPushButton("Generate")
        self.btnOK.setMinimumHeight(40)
        self.btnOK.clicked.connect(self.apply)
        self.layout_buttons.addWidget(self.btnCancel)
        self.layout_buttons.addWidget(self.btnOK)

        self.layout_sampling = QVBoxLayout()
        self.layout_sampling.addWidget(self.group_SA)
        self.layout_sampling.addWidget(self.group_WA)
        self.layout_sampling.addWidget(self.group_T)

        self.layout_props = QVBoxLayout()
        self.layout_props.addWidget(self.group_settings)
        self.layout_props.addLayout(self.layout_buttons)
        self.layout_props.addStretch()

        self.main_layout = QHBoxLayout()
        self.main_layout.addLayout(self.layout_sampling)
        self.main_layout.addLayout(self.layout_props)
        self.setLayout(self.main_layout)

        self.radio_buttons = QButtonGroup()
        self.radio_buttons.addButton(self.radio_SA)
        self.radio_buttons.addButton(self.radio_WA)
        self.radio_buttons.addButton(self.radio_T)
        self.radio_SA.setChecked(True)

        self.enableSAGroup()

        # signal-slot connections
        self.radio_SA.clicked.connect(self.enableSAGroup)
        self.radio_WA.clicked.connect(self.enableWAGroup)
        self.radio_T.clicked.connect(self.enableTransectGroup)

        self.edit_offset_px.textChanged.connect(self.updateSAOffsetInCm)
        self.edit_offset_cm.textChanged.connect(self.updateSAOffsetInPx)

        self.edit_width_cm.textChanged.connect(self.updateSAWidthInPixel)
        self.edit_height_cm.textChanged.connect(self.updateSAHeightInPixel)

        self.edit_width_px.textChanged.connect(self.updateSAWidthInCm)
        self.edit_height_px.textChanged.connect(self.updateSAHeightInCm)

        self.setWindowTitle("Sampling Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.active_image = active_image

    @pyqtSlot(int, int, int, int)
    def updateSamplingArea(self, x, y, width, height):

        self.edit_top_SA.setText(str(y))
        self.edit_left_SA.setText(str(x))

        self.edit_width_px.setText(str(width))
        self.edit_height_px.setText(str(height))

    @pyqtSlot(float, float, float, float)
    def setTransect(self, x1, y1, x2, y2):

        self.edit_x1.setText(str(round(x1)))
        self.edit_y1.setText(str(round(y1)))
        self.edit_x2.setText(str(round(x2)))
        self.edit_y2.setText(str(round(y2)))

    @pyqtSlot()
    def updateSAOffsetInCm(self):

        txt = self.edit_offset_px.text()
        self.edit_offset_cm.blockSignals(True)

        try:
            value = float(txt)
            value = round(value * self.active_image.pixelSize(), 2)
            self.edit_offset_cm.setText(str(value))
        except:
            self.edit_offset_cm.setText("")

        self.edit_offset_cm.blockSignals(False)

    @pyqtSlot()
    def updateSAOffsetInPx(self):

        txt = self.edit_offset_cm.text()
        self.edit_offset_px.blockSignals(True)

        try:
            value = float(txt)
            value = round(value * self.active_image.pixelSize(), 2)
            self.edit_offset_px.setText(str(value))
        except:
            self.edit_offset_px.setText("")

        self.edit_offset_px.blockSignals(False)

    @pyqtSlot()
    def updateSAWidthInCm(self):

        txt = self.edit_width_px.text()
        self.edit_width_cm.blockSignals(True)

        try:
            value = float(txt)
            value = round(value * self.active_image.pixelSize(), 2)
            self.edit_width_cm.setText(str(value))
        except:
            self.edit_width_cm.setText("")

        self.edit_width_cm.blockSignals(False)

    @pyqtSlot()
    def updateSAHeightInCm(self):

        txt = self.edit_height_px.text()
        self.edit_height_cm.blockSignals(True)

        try:
            value = float(txt)
            value = round(value * self.active_image.pixelSize(), 2)
            self.edit_height_cm.setText(str(value))
        except:
            self.edit_height_cm.setText("")

        self.edit_height_cm.blockSignals(False)

    @pyqtSlot()
    def updateSAWidthInPixel(self):

        txt = self.edit_width_cm.text()
        self.edit_width_px.blockSignals(True)

        try:
            value = float(txt)
            value = round(value / self.active_image.pixelSize(), 0)
            self.edit_width_px.setText(str(value))
        except:
            self.edit_width_px.setText("")

        self.edit_width_px.blockSignals(False)

    @pyqtSlot()
    def updateSAHeightInPixel(self):

        txt = self.edit_height_cm.text()
        self.edit_height_px.blockSignals(True)

        try:
            value = float(txt)
            value = round(value / self.active_image.pixelSize(), 0)
            self.edit_height_px.setText(str(value))
        except:
            self.edit_height_px.setText("")

        self.edit_height_px.blockSignals(False)


    @pyqtSlot()
    def enableSAGroup(self):

        self.radio_SA.setStyleSheet("color: white")
        self.lbl_top_SA.setEnabled(True)
        self.edit_top_SA.setEnabled(True)
        self.lbl_left_SA.setEnabled(True)
        self.edit_left_SA.setEnabled(True)
        self.lbl_left_px_SA.setEnabled(True)
        self.lbl_top_px_SA.setEnabled(True)
        self.btn_select_area_SA.setEnabled(True)

        self.disableWAGroup()
        self.disableTransectGroup()

    @pyqtSlot()
    def enableWAGroup(self):

        if self.working_area:
            if len(self.working_area) == 4:

                self.radio_WA.setStyleSheet("color: white")
                self.lbl_areas_WA.setEnabled(True)
                self.edit_number_areas_WA.setEnabled(True)
                #self.checkbox_overlap_areas_WA.setEnabled(True)

                self.disableSAGroup()
                self.disableTransectGroup()
        else:
            self.radio_SA.setChecked(True)
            self.enableSAGroup()

            msgBox = QMessageBox(parent=self)
            msgBox.setWindowTitle("Sampling Settings")
            msgBox.setText("The Working Area is not defined. If you want to sample a Working Area you need to previously define it.")
            msgBox.exec()


    @pyqtSlot()
    def enableTransectGroup(self):

        self.radio_T.setStyleSheet("color: white")
        self.lbl_areas_T.setEnabled(True)
        self.edit_number_areas_T.setEnabled(True)
        #self.checkbox_overlap_areas_T.setEnabled(True)
        self.lbl_method_T.setStyleSheet("color: white")
        self.combo_method_T.setStyleSheet("color: white")
        self.lbl_x1.setEnabled(True)
        self.edit_x1.setEnabled(True)
        self.lbl_x1_px.setEnabled(True)
        self.lbl_y1.setEnabled(True)
        self.edit_y1.setEnabled(True)
        self.lbl_y1_px.setEnabled(True)
        self.lbl_x2.setEnabled(True)
        self.edit_x2.setEnabled(True)
        self.lbl_x2_px.setEnabled(True)
        self.lbl_y2.setEnabled(True)
        self.edit_y2.setEnabled(True)
        self.lbl_y2_px.setEnabled(True)

        self.btn_select_transect_T.setEnabled(True)

        self.disableSAGroup()
        self.disableWAGroup()

    def disableSAGroup(self):

        self.radio_SA.setStyleSheet("color: rgb(90,90,90)")
        self.lbl_top_SA.setEnabled(False)
        self.edit_top_SA.setEnabled(False)
        self.lbl_left_SA.setEnabled(False)
        self.edit_left_SA.setEnabled(False)
        self.lbl_left_px_SA.setEnabled(False)
        self.lbl_top_px_SA.setEnabled(False)
        self.btn_select_area_SA.setEnabled(False)

    def disableWAGroup(self):

        self.radio_WA.setStyleSheet("color: rgb(90,90,90)")
        self.lbl_areas_WA.setEnabled(False)
        self.edit_number_areas_WA.setEnabled(False)
        #self.checkbox_overlap_areas_WA.setEnabled(False)

    def disableTransectGroup(self):

        self.radio_T.setStyleSheet("color: rgb(90,90,90)")
        self.lbl_areas_T.setEnabled(False)
        self.edit_number_areas_T.setEnabled(False)
        #self.checkbox_overlap_areas_T.setEnabled(False)
        self.lbl_method_T.setStyleSheet("color: rgb(90,90,90)")
        self.combo_method_T.setStyleSheet("color: rgb(90,90,90)")
        self.lbl_x1.setEnabled(False)
        self.edit_x1.setEnabled(False)
        self.lbl_x1_px.setEnabled(False)
        self.lbl_y1.setEnabled(False)
        self.edit_y1.setEnabled(False)
        self.lbl_y1_px.setEnabled(False)
        self.lbl_x2.setEnabled(False)
        self.edit_x2.setEnabled(False)
        self.lbl_x2_px.setEnabled(False)
        self.lbl_y2.setEnabled(False)
        self.edit_y2.setEnabled(False)
        self.lbl_y2_px.setEnabled(False)
        self.btn_select_transect_T.setEnabled(False)

    def getTransect(self):

        x1 = int(self.edit_x1.text())
        y1 = int(self.edit_y1.text())
        x2 = int(self.edit_x2.text())
        y2 = int(self.edit_y2.text())

        return [x1, y1, x2, y2]

    def apply(self):
        """
        Check the parameters, and then it generates the samples.
        """
        msgBox = QMessageBox(parent=self)
        msgBox.setWindowTitle("Sampling Settings")
        if self.edit_number.text() == "" or self.edit_number.text().isnumeric() == False:
            msgBox.setText("Please, indicate the number of sampled points.")
            msgBox.exec()
            return

        if (self.edit_width_px.text() == "" or genutils.isfloat(self.edit_width_px.text()) == False or
                self.edit_height_px == "" or genutils.isfloat(self.edit_height_px.text()) == False):
            msgBox.setText("Please, indicate the size of the sampling area.")
            msgBox.exec()
            return

        if self.edit_offset_px.text() == "" or genutils.isfloat(self.edit_offset_px.text()) == False:
            msgBox.setText("Please, indicate an offset or put 0 for no offset.")
            msgBox.exec()
            return

        if float(self.edit_number.text()) <= 0.0:
            msgBox.setText("Please, indicate a number of samples greater than zero.")
            msgBox.exec()
            return

        if float(self.edit_width_px.text()) <= 0.0:
            msgBox.setText("Please, indicate a sampling area width greater than zero.")
            msgBox.exec()
            return

        if float(self.edit_height_px.text()) <= 0.0:
            msgBox.setText("Please, indicate a sampling area height greater than zero.")
            msgBox.exec()
            return

        if self.radio_SA.isChecked():
            if (self.edit_top_SA.text() == "" or self.edit_top_SA.text().isnumeric() == False or
                    self.edit_left_SA == "" or self.edit_left_SA.text().isnumeric() == False):
                msgBox.setText("Please, indicate the (top,left) corner of the sampling area.")
                msgBox.exec()
                return

        if self.radio_WA.isChecked():
            if self.edit_number_areas_WA.text() == "" or self.edit_number_areas_WA.text().isnumeric() == False:
                msgBox.setText("Please, indicate the number of areas inside the Working Area.")
                msgBox.exec()
                return

        if self.radio_T.isChecked():
            if self.edit_number_areas_T.text() == "" or self.edit_number_areas_T.text().isnumeric() == False:
                msgBox.setText("Please, indicate the number of areas along the transect.")
                msgBox.exec()
                return

            if (self.edit_x1.text() == "" or genutils.isfloat(self.edit_x1.text()) == False or
                    self.edit_y1.text() == "" or genutils.isfloat(self.edit_y1.text()) == False or
                    self.edit_x2.text() == "" or genutils.isfloat(self.edit_x2.text()) == False or
                    self.edit_y2.text() == "" or genutils.isfloat(self.edit_y2.text()) == False):
                msgBox.setText("The transect is not well defined.")
                msgBox.exec()
                return

        self.validchoices.emit()

    def closeEvent(self,event):
        """

        """
        self.closewidget.emit()
        super(QtSampleWidget, self).closeEvent(event)

