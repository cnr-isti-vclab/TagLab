
import random, os
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import ConfusionMatrixDisplay
from PyQt5.QtCore import Qt, QSize, QFile, QIODevice, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue
from PyQt5.QtWidgets import QWidget, QDialog, QGroupBox, QFileDialog, QComboBox, QSizePolicy, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

from source import utils

class QtTrainingResultsWidget(QWidget):

    def __init__(self, metrics, train_loss_data, val_loss_data, image_folder, label_folder, prediction_folder, parent=None):
        super(QtTrainingResultsWidget, self).__init__(parent)

        self.image_folder = image_folder
        self.label_folder=label_folder
        self.prediction_folder = prediction_folder

        self.train_loss_data = train_loss_data
        self.val_loss_data = val_loss_data
        self.metrics = metrics

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.LINEWIDTH = 100

        self.TG_WIDTH = 520
        self.TG_HEIGHT = 360

        self.LABEL_SIZE = 256


        ########################################################### TEST RESULTS

        self.lblAccuracy = QLabel("Accuracy:")
        self.lblmIoU= QLabel("mIoU:")

        self.editAccuracy = QLineEdit(str(metrics["Accuracy"]))
        self.editAccuracy.setStyleSheet("background-color: rgb(40,40,40); border: 1px solid rgb(90,90,90)")
        self.editAccuracy.setReadOnly(True)
        self.editAccuracy.setFixedWidth(self.LINEWIDTH)
        self.editmIoU = QLineEdit(str(metrics["JaccardScore"]))
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

        group_results = QGroupBox("Test Results", self)
        group_results.setLayout(layoutMetrics)


        ##################################################################################### GRAPHS

        self.QlabelTG = QLabel()
        self.QlabelTG.setMinimumWidth(self.TG_WIDTH)
        self.QlabelTG.setMinimumHeight(self.TG_HEIGHT)
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

        layoutTiles = QHBoxLayout()
        layoutTiles.setAlignment(Qt.AlignTop)
        layoutTiles.addStretch()
        layoutTiles.addWidget(self.QlabelRGB)
        layoutTiles.addWidget(self.QlabelLB)
        layoutTiles.addWidget(self.QlabelPred)
        layoutTiles.addStretch()

        layoutSelect = QHBoxLayout()
        layoutSelect.addWidget(self.btnSelect)
        layoutSelect.addStretch()

        layoutPredictions = QVBoxLayout()
        layoutPredictions.setAlignment(Qt.AlignLeft)
        layoutPredictions.addLayout(layoutSelect)
        layoutPredictions.addLayout(layoutTiles)

        group_pred = QGroupBox("Predictions", self)
        group_pred.setLayout(layoutPredictions)

        ############################################################### FINAL LAYOUT

        layoutFirstRow = QHBoxLayout()
        layoutFirstRow.addWidget(group_results)
        layoutFirstRow.addWidget(group_graphs)
        layoutFirstRow.addStretch()

        layoutFinal = QVBoxLayout()
        layoutFinal.addLayout(layoutFirstRow)
        layoutFinal.addWidget(group_pred)

        self.setLayout(layoutFinal)

        self.setWindowTitle("Training Results")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint)

        self.adjustSize()

        self.pxmapCM = None
        self.last_file = None

    @pyqtSlot()
    def displayCM(self):

        np.set_printoptions(precision=2)

        #display_labels = class_names
        disp = ConfusionMatrixDisplay(confusion_matrix=self.metrics["NormConfMatrix"], display_labels=None)

        disp.plot(include_values=True,
                  cmap=plt.cm.Blues, xticks_rotation='horizontal',
                  values_format='.3g')

        disp.ax_.set_title("Normalized Confusion Matrix")

        fig = disp.figure_
        fig.set_size_inches(8.0, 8.0)

        self.pxmapCM = utils.figureToQPixmap(fig, dpi=180, width=800, height=800)

        widget = QWidget(parent=self)
        widget.setFixedWidth(800)
        widget.setFixedHeight(800)
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
            self.pxmapCM.save(file, "PNG")

    @pyqtSlot()
    def SaveTG(self):

        filters = "PNG (*.png)"
        filename, _ = QFileDialog.getSaveFileName(self, "Save the Training Graphs", None, filters)

        if filename:
            file = QFile(filename)
            file.open(QIODevice.WriteOnly)
            self.pxmapCM.save(file, "PNG")

    @pyqtSlot()
    def SelectTile(self):

        filters = "PNG (*.png)"
        filename, _ = QFileDialog.getOpenFileName(self, "Select tile", self.image_folder, filters)

        self.last_folder = os.path.dirname(filename)
        self.last_file = os.path.basename(filename)
        self.updateTiles(filename)

    def keyPressEvent(self, event):

        if self.last_file is not None and self.last_folder is not None:

            print(event.key())

            if event.key() == Qt.Key_Z:
                filelist = os.listdir(self.last_folder)
                index = filelist.index(self.last_file)
                if index < len(filelist) - 1:
                    index = index + 1
                filename = filelist[index]
                self.updateTiles(filename)
            elif event.key() == Qt.Key_X:
                filelist = os.listdir(self.last_folder)
                index = filelist.index(self.last_file)
                if index > 0:
                    index = index - 1
                filename = filelist[index]
                self.updateTiles(filename)

    def updateTiles(self, filename):

        if filename:

            size = self.LABEL_SIZE

            # RGB tile
            img = QImage(filename)
            img = img.copy(256, 256, 513, 513)
            pxmap = QPixmap.fromImage(img)
            self.QlabelRGB.setPixmap(pxmap.scaled(QSize(size, size)))

            # GT tile
            filename = filename.replace('images', 'labels')
            print(filename)
            img2 = QImage(filename)
            img2 = img2.copy(256, 256, 513, 513)
            pxmapGT = QPixmap.fromImage(img2)
            self.QlabelLB.setPixmap(pxmapGT.scaled(QSize(size, size)))

            # prediction tile
            base_name = os.path.basename(filename)
            newfilename = os.path.join(self.prediction_folder, base_name)
            img3 = QImage(newfilename)
            pxmapPred = QPixmap.fromImage(img3)
            self.QlabelPred.setPixmap(pxmapPred.scaled(QSize(size, size)))


    def setTrainingGraphs(self):

        n_epochs = len(self.train_loss_data)

        # make the values of training and validation comparable
        validation_loss_values = []
        for i in range(n_epochs):

            if i % 2 == 0:
                validation_loss_values.append(self.val_loss_data[int(i/2)])
            else:
                avg = (self.val_loss_data[int(i/2)] + self.val_loss_data[int(i/2)+1]) / 2.0
                validation_loss_values.append(avg)

        fig = plt.figure()
        fig.set_size_inches(10, 6.0)
        plt.grid(axis="x")
        plt.xticks(np.arange(0, n_epochs, 5))

        x = np.arange(0, n_epochs)
        plt.plot(x, validation_loss_values, label='Validation Loss')
        plt.plot(x, self.train_loss_data, label='Training Loss')

        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()

        self.pxmapTG = utils.figureToQPixmap(fig, dpi=180, width=self.TG_WIDTH, height=self.TG_HEIGHT)



