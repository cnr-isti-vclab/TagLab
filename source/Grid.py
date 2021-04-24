from PyQt5 import QtCore, QtGui
import sys
from pprint import pprint
from PyQt5.QtWidgets import  QWidget,QGridLayout,QApplication

import numpy as np
from PyQt5.QtCore import Qt, QSize, QMargins, QDir, QPoint, QPointF, QRectF, QTimer, pyqtSlot, pyqtSignal, QSettings, QFileInfo, QModelIndex
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QIcon, QKeySequence, QPen

class Grid:

    def __init__(self):

        self.width = 0
        self.height = 0
        self.nrow = 0
        self.ncol = 0
        self.offx = 0
        self.offy = 0

        self.scene = None

        self.cell_values = None
        self.dict_notes = {}

        self.grid_rects = []

    def setScene(self, scene):

        self.scene = scene

    def setGrid(self, width, height, nrow, ncol):

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

    def setGridPosition(self, posx, posy):

        self.offx = posx
        self.offy = posy

        for rect in self.grid_rects:
            rect.setPos(self.offx, self.offy)

    def drawGrid(self):
        
        cell_width = self.width / self.ncol
        cell_height = self.height / self.nrow

        pen_red = QPen(Qt.red, 2, Qt.SolidLine)
        pen_red.setCosmetic(True)
        pen_green = QPen(Qt.green, 2, Qt.SolidLine)
        pen_green.setCosmetic(True)
        pen_blue = QPen(Qt.blue, 2, Qt.SolidLine)
        pen_blue.setCosmetic(True)

        for c in range(0, self.ncol):
            for r in range(0, self.nrow):
                xc = c * cell_width
                yc = r * cell_height

                value = self.cell_values[r, c]

                if value == 0:
                    rect = self.scene.addRect(xc, yc, cell_width-1, cell_height-1, pen=pen_red)
                elif value == 1:
                    rect = self.scene.addRect(xc, yc, cell_width-1, cell_height-1, pen=pen_blue)
                elif value == 2:
                    rect = self.scene.addRect(xc, yc, cell_width-1, cell_height-1, pen=pen_green)

                rect.setPos(self.offx, self.offy)
                self.grid_rects.append(rect)

    def setVisible(self, visible=True):
        for rect in self.grid_rects:
            rect.setVisible(visible)

    def undrawGrid(self):
        for rect in self.grid_rects:
            self.scene.removeItem(rect)
        del self.grid_rects[:]

    def setOpacity(self, opacity):

        for rect in self.grid_rects:
            rect.setOpacity(opacity)

    def changeCellState(self, x, y):

        cell_width = self.width / self.ncol
        cell_height = self.height / self.nrow

        print(x, y)

        c = int(x / cell_width)
        r = int(y / cell_height)

        self.cell_values[r, c] = (self.cell_values[r, c] + 1) % 3

        self.undrawGrid()
        self.drawGrid()

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




