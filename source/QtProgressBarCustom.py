from PyQt5.QtCore import Qt, QMargins, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QBrush, QPixmap, QIcon, qRgb, qRed, qGreen, qBlue, QFont
from PyQt5.QtWidgets import QWidget, QGroupBox, QSizePolicy, QSlider, QLabel, QHBoxLayout, QVBoxLayout

class QtProgressBarCustom(QWidget):

    def __init__(self, parent=None):
        super(QtProgressBarCustom, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(400)
        self.setMinimumHeight(40)

        self.bar_width = 400

        self.pxmapBar = QPixmap(self.bar_width, 30)
        self.pxmapBar.fill(Qt.darkBlue)
        self.lblBar = QLabel()
        self.lblBar.setPixmap(self.pxmapBar)

        fnt = QFont("Times", 11)
        self.lblProgress = QLabel("0.00 %")
        self.lblProgress.setAlignment(Qt.AlignLeft)
        self.lblProgress.setMaximumHeight(30)
        self.lblProgress.setFont(fnt)
        self.lblProgress.setStyleSheet("color: rgb(255,255,255)")

        layoutH = QHBoxLayout()
        layoutH.addWidget(QLabel("Classification: "))
        layoutH.addWidget(self.lblBar)
        layoutH.addWidget(self.lblProgress)
        layoutH.setContentsMargins(QMargins(0, 0, 0, 0))
        self.setLayout(layoutH)

        self.setAutoFillBackground(True)


    @pyqtSlot(float)
    def setProgress(self, progress):
        """
        Set the current progress of the processing. The value goes from 0.0 to 100.0
        """

        txt = "{:.2f} %".format(progress)
        self.lblProgress.setText(txt)

        w = (self.bar_width * progress) / 100.0

        brush = QBrush(Qt.blue)
        painter = QPainter(self.pxmapBar)
        painter.setBrush(brush)
        painter .drawRect(0, 0, int(w), 30)
        painter.end()

        self.lblBar.setPixmap(self.pxmapBar)

        self.update()

