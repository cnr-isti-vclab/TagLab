
import random, os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay
from PyQt5.QtCore import Qt, QSize, QFile, QIODevice, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QSlider, QWidget, QDialog, QGroupBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

from source import genutils

class QtTrainingResultsWidget(QWidget):

    def __init__(self, dict_target, metrics, train_loss_data, val_loss_data, image_folder, label_folder, prediction_folder, parent=None):
        super(QtTrainingResultsWidget, self).__init__(parent)

        self.dict_target_classes = dict_target
        self.dataset_folder = os.path.dirname(prediction_folder)
        self.image_folder = image_folder
        self.label_folder=label_folder
        self.prediction_folder = prediction_folder

        self.train_loss_data = train_loss_data
        self.val_loss_data = val_loss_data
        self.metrics = metrics

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.LINEWIDTH = 100

        self.TG_WIDTH = 640
        self.TG_HEIGHT = 640 / 1.77777777

        self.LABEL_SIZE = 256


        ########################################################### TEST RESULTS

        self.lblAccuracy = QLabel("Accuracy:")
        self.lblmIoU= QLabel("mIoU:")

        txt = "{:.3f}".format(metrics['Accuracy'])
        self.editAccuracy = QLineEdit(txt)
        self.editAccuracy.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editAccuracy.setReadOnly(True)
        self.editAccuracy.setFixedWidth(self.LINEWIDTH)
        txt = "{:.3f}".format(metrics['JaccardScore'])
        self.editmIoU = QLineEdit(txt)
        self.editmIoU.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editmIoU.setReadOnly(True)
        self.editmIoU.setFixedWidth(self.LINEWIDTH)

        self.btnCM = QPushButton("Display Confusion Matrix")
        self.btnCM.setFixedWidth(230)
        self.btnCM.setFixedHeight(30)
        self.btnCM.clicked.connect(self.displayCM)

        layoutAccuracy = QHBoxLayout()
        layoutAccuracy.setAlignment(Qt.AlignLeft)
        layoutAccuracy.addWidget(self.lblAccuracy)
        layoutAccuracy.addWidget(self.editAccuracy)

        layoutmIoU = QHBoxLayout()
        layoutmIoU.setAlignment(Qt.AlignLeft)
        layoutmIoU.addWidget(self.lblmIoU)
        layoutmIoU.addWidget(self.editmIoU)

        layoutButtonCM = QHBoxLayout()
        layoutButtonCM.setAlignment(Qt.AlignLeft)
        layoutButtonCM.addStretch()
        layoutButtonCM.addWidget(self.btnCM)
        layoutButtonCM.addStretch()

        self.btnSaveCM = QPushButton("Save As")
        self.btnSaveCM.setFixedWidth(230)
        self.btnSaveCM.setFixedHeight(30)
        self.btnSaveCM.clicked.connect(self.SaveCM)

        layoutButtonSaveAs = QHBoxLayout()
        layoutButtonSaveAs.setAlignment(Qt.AlignLeft)
        layoutButtonSaveAs.addStretch()
        layoutButtonSaveAs.addWidget(self.btnSaveCM)
        layoutButtonSaveAs.addStretch()

        layoutMetrics = QVBoxLayout()
        layoutMetrics.addLayout(layoutAccuracy)
        layoutMetrics.addLayout(layoutmIoU)
        layoutMetrics.addLayout(layoutButtonCM)
        layoutMetrics.addLayout(layoutButtonSaveAs)
        layoutMetrics.addStretch()

        groupbox_style = "QGroupBox\
        {\
            border: 1px solid rgb(90,90,90);\
            border-radius: 10px;\
            margin-top: 10px;\
            margin-left: 0px;\
            margin-right: 0px;\
            padding-top: 5px;\
            padding-left: 5px;\
            padding-bottom: 5px;\
            padding-right: 5px;\
        }\
        \
        QGroupBox::title\
        {\
            subcontrol-origin: margin;\
            subcontrol-position: top center;\
            padding: 0 0px;\
        }"

        group_results = QGroupBox("Test Results", self)
        group_results.setStyleSheet(groupbox_style)
        group_results.setLayout(layoutMetrics)


        ##################################################################################### GRAPHS

        self.QlabelTG = QLabel()
        self.QlabelTG.setMinimumWidth(self.TG_WIDTH)
        self.QlabelTG.setMinimumHeight(self.TG_HEIGHT)
        self.figureTG = None
        self.pxmapTG = None
        self.setTrainingGraphs()
        self.QlabelTG.setPixmap(self.pxmapTG)

        self.btnSaveTG = QPushButton("Save As")
        self.btnSaveTG.clicked.connect(self.SaveTG)

        layoutSaveTG = QHBoxLayout()
        layoutSaveTG.addStretch()
        layoutSaveTG.addWidget(self.btnSaveTG)

        layoutGraphs = QVBoxLayout()
        layoutGraphs.setAlignment(Qt.AlignLeft)
        layoutGraphs.addWidget(self.QlabelTG)
        layoutGraphs.addLayout(layoutSaveTG)

        group_graphs = QGroupBox("Training Graphs", self)
        group_graphs.setStyleSheet(groupbox_style)
        group_graphs.setLayout(layoutGraphs)

        #################################################################################### PREVIEW

        self.btnSelect = QPushButton("Select")
        self.btnSelect.clicked.connect(self.SelectTile)

        self.QlabelRGB= QLabel("")
        self.QPixmapRGB = QPixmap(self.LABEL_SIZE, self.LABEL_SIZE)
        self.QPixmapRGB.fill(Qt.black)
        self.QlabelRGB.setPixmap(self.QPixmapRGB)

        self.QlabelLB = QLabel("")
        self.QPixmapLB = QPixmap(self.LABEL_SIZE, self.LABEL_SIZE)
        self.QPixmapLB.fill(Qt.black)
        self.QlabelLB.setPixmap(self.QPixmapLB)

        self.QlabelPred = QLabel("")
        self.QPixmapPred = QPixmap(self.LABEL_SIZE, self.LABEL_SIZE)
        self.QPixmapPred.fill(Qt.black)
        self.QlabelPred.setPixmap(self.QPixmapPred)

        layoutTileInput = QVBoxLayout()
        layoutTileInput.addWidget(self.QlabelRGB, alignment=Qt.AlignCenter)
        layoutTileInput.addWidget(QLabel("Input"), alignment=Qt.AlignCenter)

        layoutTileGT = QVBoxLayout()
        layoutTileGT.addWidget(self.QlabelLB, alignment=Qt.AlignCenter)
        layoutTileGT.addWidget(QLabel("Ground Truth"), alignment=Qt.AlignCenter)

        layoutTilePred = QVBoxLayout()
        layoutTilePred.addWidget(self.QlabelPred, alignment=Qt.AlignCenter)
        layoutTilePred.addWidget(QLabel("Prediction"), alignment=Qt.AlignCenter)

        layoutTiles = QHBoxLayout()
        layoutTiles.setAlignment(Qt.AlignTop)
        layoutTiles.addStretch()
        layoutTiles.addLayout(layoutTileInput)
        layoutTiles.addLayout(layoutTileGT)
        layoutTiles.addLayout(layoutTilePred)
        layoutTiles.addStretch()

        layoutSelect = QHBoxLayout()
        layoutSelect.addWidget(self.btnSelect)
        layoutSelect.addStretch()

        layoutPredictions = QVBoxLayout()
        layoutPredictions.setAlignment(Qt.AlignLeft)
        layoutPredictions.addLayout(layoutSelect)
        layoutPredictions.addLayout(layoutTiles)

        group_pred = QGroupBox("Predictions", self)
        group_pred.setStyleSheet(groupbox_style)
        group_pred.setLayout(layoutPredictions)

        ############################################################### BUTTONS LAYOUT

        buttons_layout = QHBoxLayout()
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.close)
        self.btnConfirm = QPushButton("Confirm")
        buttons_layout.setAlignment(Qt.AlignRight)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btnCancel)
        buttons_layout.addWidget(self.btnConfirm)

        ############################################################### FINAL LAYOUT

        layoutFirstRow = QHBoxLayout()
        layoutFirstRow.addWidget(group_results)
        layoutFirstRow.addWidget(group_graphs)
        layoutFirstRow.addStretch()

        layoutFinal = QVBoxLayout()
        layoutFinal.addLayout(layoutFirstRow)
        layoutFinal.addWidget(group_pred)
        layoutFinal.addLayout(buttons_layout)
        self.setLayout(layoutFinal)

        self.setWindowTitle("Training Results")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.adjustSize()

        self.figureCM = None
        self.pxmapCM = None
        self.last_tile_selected = None

    @pyqtSlot()
    def displayCM(self):

        np.set_printoptions(precision=2)

        dict_ordered_by_value = {k: v for k, v in sorted(self.dict_target_classes.items(), key=lambda item: item[1])}

        class_names = []
        max_characters = 12
        for item in dict_ordered_by_value.items():
            name = item[0]
            if len(name) > max_characters:
                name = name[:max_characters-2] + ".."
            class_names.append(name)
        disp = ConfusionMatrixDisplay(confusion_matrix=self.metrics["NormConfMatrix"], display_labels=class_names)

        disp.plot(include_values=True,
                  cmap=plt.cm.Blues, xticks_rotation=45,
                  values_format='.3g')

        disp.ax_.set_title("Normalized Confusion Matrix")

        fig = disp.figure_
        fig.set_size_inches(6.0, 6.0)

        plt.tight_layout()

        self.figureCM = fig
        self.pxmapCM = genutils.figureToQPixmap(fig, dpi=300, width=800, height=800)

        widget = QWidget(parent=self)
        widget.setFixedWidth(840)
        widget.setFixedHeight(840)
        lblCentral = QLabel("")
        lblCentral.setPixmap(self.pxmapCM)
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(lblCentral)
        widget.setLayout(layout)
        widget.setWindowModality(Qt.WindowModal)
        widget.setWindowTitle("TagLab")
        widget.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
        widget.show()

    @pyqtSlot()
    def SaveCM(self):

        filters = "PNG (*.png)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save the Normalized Confusion Matrix", None, filters)

        if filename:
            file = QFile(filename)
            file.open(QIODevice.WriteOnly)
            plt.savefig(file, format="png", dpi=300)

    @pyqtSlot()
    def SaveTG(self):

        filters = "PNG (*.png)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save the Training Graphs", None, filters)

        if filename:
            file = QFile(filename)
            file.open(QIODevice.WriteOnly)
            plt.savefig(file, format="png", dpi=300)

    @pyqtSlot()
    def SelectTile(self):

        filters = "PNG (*.png)"
        filename, _ = QFileDialog.getOpenFileName(self, "Select tile", self.image_folder, filters)

        self.last_tile_selected = filename
        self.updateTiles(filename)

    def keyPressEvent(self, event):

        if self.last_tile_selected is not None:

            folder = os.path.dirname(self.last_tile_selected)
            filename = os.path.basename(self.last_tile_selected)

            if event.key() == Qt.Key_X:
                filelist = os.listdir(folder)
                index = filelist.index(filename)
                if index < len(filelist) - 1:
                    index = index + 1
                    nextfile = filelist[index]
                    self.updateTiles(os.path.join(folder, nextfile))
                    self.last_tile_selected = os.path.join(folder, nextfile)
            elif event.key() == Qt.Key_Z:
                filelist = os.listdir(folder)
                index = filelist.index(filename)
                if index > 0:
                    index = index - 1
                    prevfile = filelist[index]
                    self.updateTiles(os.path.join(folder, prevfile))
                    self.last_tile_selected = os.path.join(folder, prevfile)

    def updateTiles(self, filename):

        if filename:

            size = self.LABEL_SIZE

            # RGB tile
            img = QImage(filename)
            img = img.copy(256, 256, 513, 513)
            pxmap = QPixmap.fromImage(img)
            self.QlabelRGB.setPixmap(pxmap.scaled(QSize(size, size)))

            # GT label
            filename = filename.replace('images', 'labels')
            img2 = QImage(filename)
            img2 = img2.copy(256, 256, 513, 513)
            pxmapGT = QPixmap.fromImage(img2)
            self.QlabelLB.setPixmap(pxmapGT.scaled(QSize(size, size)))

            # prediction tile
            base_name = os.path.basename(filename)
            newfilename = os.path.join(self.prediction_folder, base_name)
            img3 = QImage(newfilename)
            img3 = img3.copy(256, 256, 513, 513)
            pxmapPred = QPixmap.fromImage(img3)
            self.QlabelPred.setPixmap(pxmapPred.scaled(QSize(size, size)))


    def setTrainingGraphs(self):

        n_epochs = len(self.train_loss_data)

        fig = plt.figure()
        fig.set_size_inches(6.3, 6.3 / 1.7777)
        plt.grid(axis="x")
        plt.xticks(np.arange(0, n_epochs, 5))

        x = np.arange(1, n_epochs, 2)
        plt.plot(x, self.val_loss_data, label='Validation Loss')

        x = np.arange(0, n_epochs)
        plt.plot(x, self.train_loss_data, label='Training Loss')

        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()

        self.figureTG = fig
        self.pxmapTG = genutils.figureToQPixmap(fig, dpi=300, width=self.TG_WIDTH, height=self.TG_HEIGHT)
