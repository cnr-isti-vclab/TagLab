from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import (QRadioButton, QButtonGroup, QGroupBox, QMessageBox,  QWidget, QComboBox, QSizePolicy,
                             QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout)
from source.Annotation import Annotation
import numpy as np

class QtSampleWidget(QWidget):


    # choosedSample = pyqtSignal(int)
    closewidget = pyqtSignal()
    validchoices= pyqtSignal()

    def __init__(self, parent=None):
        super(QtSampleWidget, self).__init__(parent)

        self.choosednumber = None
        self.offset = None

        self.setStyleSheet(":enabled {background-color: rgb(40,40,40); color: white} :disabled {color: rgb(110,110,110)}")

        self.lineedit_style = ":enabled {background-color: rgb(55,55,55); color: rgb(255,255,255); border: 1px solid rgb(90,90,90)} " \
                              ":disabled {background-color: rgb(35,35,35); color: rgb(110,110,110); border: 1px solid rgb(70,70,70)}"

        MAXIMUM_WIDTH_EDIT = 160

        # sampling single area (manual)

        self.group_SA = QGroupBox()

        self.radio_SA = QRadioButton("Add a single sampling area")

        area_icon = QIcon("icons\\select_area.png")
        self.btn_SA = QPushButton("")
        self.btn_SA.setIcon(area_icon)
        self.btn_SA.setMinimumWidth(20)

        self.lbl_top_SA = QLabel("Top: ")
        self.lbl_left_SA = QLabel("Left: ")
        self.edit_top_SA = QLineEdit()
        self.edit_top_SA.setStyleSheet(self.lineedit_style)
        self.edit_top_SA.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.edit_left_SA = QLineEdit()
        self.edit_left_SA.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.edit_left_SA.setStyleSheet(self.lineedit_style)

        self.layoutH1 = QHBoxLayout()
        self.layoutH1.addWidget(self.btn_SA)
        self.layoutH1.addWidget(self.lbl_top_SA)
        self.layoutH1.addWidget(self.edit_top_SA)
        self.layoutH1.addWidget(self.lbl_left_SA)
        self.layoutH1.addWidget(self.edit_left_SA)
        self.layoutH1.addStretch()

        self.layoutV1 = QVBoxLayout()
        self.layoutV1.addWidget(self.radio_SA)
        self.layoutV1.addLayout(self.layoutH1)
        self.group_SA.setLayout(self.layoutV1)

        # sampling Working Area (randomly)

        self.group_WA = QGroupBox()

        self.radio_WA = QRadioButton("Sampling the Working Area with multiple random areas")

        self.lbl_areas_WA = QLabel("# areas:")
        self.edit_number_areas_WA = QLineEdit()
        self.edit_number_areas_WA.setStyleSheet(self.lineedit_style)
        self.edit_number_areas_WA.setMaximumWidth(MAXIMUM_WIDTH_EDIT)

        self.layoutH2 = QHBoxLayout()
        self.layoutH2.addWidget(self.lbl_areas_WA)
        self.layoutH2.addWidget(self.edit_number_areas_WA)
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


        self.lbl_method_T = QLabel("Method:")
        self.combo_method_T = QComboBox()
        self.combo_method_T.setMinimumWidth(180)
        self.combo_method_T.addItem('Equi-spaced')
        self.combo_method_T.addItem('Random')

        self.lbl_x1 = QLabel("x1:")
        self.edit_x1 = QLineEdit()
        self.edit_x1.setStyleSheet(self.lineedit_style)
        self.edit_x1.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.lbl_y1 = QLabel("y1:")
        self.edit_y1 = QLineEdit()
        self.edit_y1.setStyleSheet(self.lineedit_style)
        self.edit_y1.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.lbl_x2 = QLabel("x2:")
        self.edit_x2 = QLineEdit()
        self.edit_x2.setStyleSheet(self.lineedit_style)
        self.edit_x2.setMaximumWidth(MAXIMUM_WIDTH_EDIT)
        self.lbl_y2 = QLabel("y2:")
        self.edit_y2 = QLineEdit()
        self.edit_y2.setStyleSheet(self.lineedit_style)
        self.edit_y2.setMaximumWidth(MAXIMUM_WIDTH_EDIT)

        self.layoutH3 = QHBoxLayout()
        self.layoutH3.addWidget(self.lbl_areas_T)
        self.layoutH3.addWidget(self.edit_number_areas_T)
        self.layoutH3.addWidget(self.lbl_method_T)
        self.layoutH3.addWidget(self.combo_method_T)
        self.layoutH3.addStretch()

        self.layoutH4 = QHBoxLayout()
        self.layoutH4.addWidget(self.lbl_x1)
        self.layoutH4.addWidget(self.edit_x1)
        self.layoutH4.addWidget(self.lbl_y1)
        self.layoutH4.addWidget(self.edit_y1)
        self.layoutH4.addWidget(self.lbl_x2)
        self.layoutH4.addWidget(self.edit_x2)
        self.layoutH4.addWidget(self.lbl_y2)
        self.layoutH4.addWidget(self.edit_y2)
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
        self.edit_offset_px.setStyleSheet("{background-color: rgb(55,55,55); border: 1px solid rgb(90,90,90)}")
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

        self.setWindowTitle("Sampling Settings")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

    @pyqtSlot()
    def enableSAGroup(self):

        self.radio_SA.setStyleSheet("color: white")
        self.lbl_top_SA.setEnabled(True)
        self.edit_top_SA.setEnabled(True)
        self.lbl_left_SA.setEnabled(True)
        self.edit_left_SA.setEnabled(True)

        self.disableWAGroup()
        self.disableTransectGroup()

    @pyqtSlot()
    def enableWAGroup(self):

        self.radio_WA.setStyleSheet("color: white")
        self.lbl_areas_WA.setEnabled(True)
        self.edit_number_areas_WA.setEnabled(True)

        self.disableSAGroup()
        self.disableTransectGroup()

    @pyqtSlot()
    def enableTransectGroup(self):

        self.radio_T.setStyleSheet("color: white")
        self.lbl_areas_T.setEnabled(True)
        self.edit_number_areas_T.setEnabled(True)
        self.lbl_method_T.setStyleSheet("color: white")
        self.lbl_x1.setEnabled(True)
        self.edit_x1.setEnabled(True)
        self.lbl_y1.setEnabled(True)
        self.edit_y1.setEnabled(True)
        self.lbl_x2.setEnabled(True)
        self.edit_x2.setEnabled(True)
        self.lbl_y2.setEnabled(True)
        self.edit_y2.setEnabled(True)

        self.disableSAGroup()
        self.disableWAGroup()

    def disableSAGroup(self):

        self.radio_SA.setStyleSheet("color: rgb(90,90,90)")
        self.lbl_top_SA.setEnabled(False)
        self.edit_top_SA.setEnabled(False)
        self.lbl_left_SA.setEnabled(False)
        self.edit_left_SA.setEnabled(False)

    def disableWAGroup(self):

        self.radio_WA.setStyleSheet("color: rgb(90,90,90)")
        self.lbl_areas_WA.setEnabled(False)
        self.edit_number_areas_WA.setEnabled(False)
    def disableTransectGroup(self):

        self.radio_T.setStyleSheet("color: rgb(90,90,90)")
        self.lbl_areas_T.setEnabled(False)
        self.edit_number_areas_T.setEnabled(False)
        self.lbl_method_T.setStyleSheet("color: rgb(90,90,90)")
        self.lbl_x1.setEnabled(False)
        self.edit_x1.setEnabled(False)
        self.lbl_y1.setEnabled(False)
        self.edit_y1.setEnabled(False)
        self.lbl_x2.setEnabled(False)
        self.edit_x2.setEnabled(False)
        self.lbl_y2.setEnabled(False)
        self.edit_y2.setEnabled(False)

    def apply(self):

        if self.editNumber.text() == "" or self.editNumber.text() == 0 or self.editNumber.text().isnumeric() == False:
            msgBox = QMessageBox()
            msgBox.setText("Please, indicate the number of sampled points.")
            msgBox.exec()
            return
        else:
            self.choosednumber = int(self.editNumber.text())

        if self.editOFF.text() == "" or self.editOFF.text().isnumeric() == False:
            self.offset = 0
        else:
            self.offset = int(self.editOFF.text())

        self.validchoices.emit()


    def closeEvent(self,event):
        self.closewidget.emit()
        super(QtSampleWidget, self).closeEvent(event)

