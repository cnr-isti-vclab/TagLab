from PyQt5.QtCore import Qt, QMargins, QRect, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QBrush, QPixmap, QPen, QColor, QIcon, qRgb, qRed, qGreen, qBlue, QFont
from PyQt5.QtWidgets import QWidget, QGroupBox, QSizePolicy, QSlider, QLabel, QHBoxLayout, QVBoxLayout

class QtProgressBarCustom(QWidget):

    def __init__(self, parent=None):
        super(QtProgressBarCustom, self).__init__(parent)

        self.setStyleSheet("background-color: rgb(40,40,40); color: white")

        self.bar_width = 400
        self.bar_height = 30

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.setMinimumWidth(self.bar_width)
        self.setMinimumHeight(self.bar_height+10)

        self.pxmapBar = QPixmap(self.bar_width, self.bar_height)
        self.pxmapBar.fill(Qt.darkBlue)
        self.lblBar = QLabel()
        self.lblBar.setPixmap(self.pxmapBar)

        layoutH = QHBoxLayout()
        layoutH.addWidget(self.lblBar)
        layoutH.setContentsMargins(QMargins(0, 0, 0, 0))
        self.setLayout(layoutH)

        self.setAutoFillBackground(True)

        self.current_progress = 0.0
        self.message = "Classification"
        self.flag_perc = True


    def showPerc(self):

        self.flag_perc = True


    def hidePerc(self):

        self.flag_perc = False


    def setMessage(self, text):
        """
        Update the message displayed by the progress bar. The current progress can be displayed together with the message, or not.
        """

        self.message = text

        if self.flag_perc is True:
            txt = self.message + "{:.2f} %".format(self.current_progress)
        else:
            txt = self.message

        self.drawBar(txt)


    @pyqtSlot(float)
    def setProgress(self, progress):
        """
        Set the current progress of the processing. The value goes from 0.0 to 100.0
        """

        txt = self.message + "{:.2f} %".format(progress)

        if self.flag_perc is True:
            txt = self.message + "{:.2f} %".format(self.current_progress)
        else:
            txt = self.message

        self.current_progress = progress

        self.drawBar(txt)


    def drawBar(self, txt):
        """
        Visualize the current progress.
        """

        w = (self.bar_width * self.current_progress) / 100.0

        painter = QPainter(self.pxmapBar)
        painter.setBrush(QBrush(QColor(qRgb(60, 60, 60))))
        painter.drawRect(0, 0, self.bar_width, 30)
        painter.setBrush(QBrush(QColor(qRgb(0, 201, 209))))
        painter.drawRect(0, 0, int(w), 30)
        painter.setPen(QPen(Qt.white))
        painter.setFont(QFont("Roboto", 12, QFont.Bold));
        painter.drawText(QRect(0, 0, self.bar_width, 30), Qt.AlignCenter, txt)

        painter.end()

        self.lblBar.setPixmap(self.pxmapBar)

        self.update()

