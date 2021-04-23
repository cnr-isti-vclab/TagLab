from PyQt5 import QtCore, QtGui
import sys
from pprint import pprint
from PyQt5.QtWidgets import  QWidget,QGridLayout,QApplication

import numpy as np
from PyQt5.QtCore import Qt, QSize, QMargins, QDir, QPoint, QPointF, QRectF, QTimer, pyqtSlot, pyqtSignal, QSettings, QFileInfo, QModelIndex
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QIcon, QKeySequence, QPen

class Grid:

    def __init__(self, viewerplus):

        self.width = 0
        self.height = 0
        self.nrow = 0
        self.ncol = 0
        self.scene = viewerplus.scene
        self.cell_values = None
        self.dict_notes = {}

        self.grid_lines = []



    def setGrid(self, width, height, nrow, ncol):

        if self.grid_lines:
           self.delete_grid()
           self.grid_lines = []

        self.width = width
        self.height = height
        self.nrow = nrow
        self.ncol = ncol

        # cells values
        self.cell_values = np.zeros((self.nrow, self.ncol))
        # cells dictionary notes
        self.dict_notes = {}

        positions = [(i, j) for i in range(self.nrow) for j in range(self.ncol)]
        for k in positions:
            self.dict_notes[k] = ""

        self.draw_grid()


    def draw_grid(self):
        
        cell_width = self.height / self.nrow
        cell_height = self.width / self.ncol

        pen = QPen(Qt.red, 2, Qt.SolidLine)
        pen.setCosmetic(True)

        for x in range(0, self.nrow + 1):
            xc = x * cell_width
            self.grid_lines.append(self.scene.addLine(xc, 0, xc, self.height, pen))

        for y in range(0, self.ncol + 1):
            yc = y * cell_height
            self.grid_lines.append(self.scene.addLine(0, yc, self.width, yc, pen))



    def set_visible(self, visible=True):
        for line in self.grid_lines:
            line.setVisible(visible)

    def delete_grid(self):
        for line in self.grid_lines:
            self.scene.removeItem(line)
        del self.grid_lines[:]

    def set_opacity(self, opacity):

        for line in self.grid_lines:
            line.setOpacity(opacity)

    def cellState(self):
        # mark cell as unseen, uncomplete, complete

        positions = [(i, j) for i in range(self.nrow) for j in range(self.ncol)]
        for position, value in zip(positions, self.cell_values):
            if value == 0:
                pass
            if value == 1:
                pass
            if value == 2:
                pass

    def noteState(self):
        positions = [(i, j) for i in range(self.nrow) for j in range(self.ncol)]
        for k in positions:
            self.dict_notes[k] = ""


    def cellColor(self):
        pass




