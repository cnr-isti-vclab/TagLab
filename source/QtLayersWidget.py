from PyQt5.QtCore import Qt,QSize, QEvent, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QWidget, QSizePolicy
from pathlib import Path
import os
from source.Project import Project
from source.Image import Image
from source.Shape import Layer


path = Path(__file__).parent.absolute()
imdir = str(path)
imdir = imdir.replace('source', '')

class QtLayersWidget(QTreeWidget):
    showImage = pyqtSignal(Image)
    showLayer = pyqtSignal(Layer)
    hideLayer = pyqtSignal(Layer)

    def __init__(self, parent=None):
        super(QtLayersWidget, self).__init__(parent)

        self.setHeaderHidden(True)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.setMinimumWidth(400)
        self.setMinimumHeight(100)

        self.icon_eyeopen = QIcon(imdir+os.path.join("icons", "eye.png"))
        self.icon_eyeclosed = QIcon(imdir+os.path.join("icons", "cross.png"))
        self.itemChanged.connect(self.itemChecked)


    def itemChecked(self, item):
        print(item)

    def setProject(self, project):
        self.blockSignals(True)
        self.clear()
        self.setColumnCount(1);

        items = []
        for image in project.images:
            item = QTreeWidgetItem()
            item.setText(0, image.name)
            item.setIcon(0, self.icon_eyeclosed)
            item.setCheckState(0, Qt.Unchecked)
            item.type = 'image'
            item.target = image

            for layer in image.layers:
                child = QTreeWidgetItem()
                child.setText(0, "Layer")
                if layer.isEnabled():
                    child.setCheckState(0, Qt.Checked)
                else:
                    child.setCheckState(0, Qt.Unhecked)
                child.type = 'layer'
                child.target = layer
                item.addChild(child)

            items.append(item)
            
            
        self.insertTopLevelItems(0, items);
        self.blockSignals(False)

    def setImage(self, image):
        self.blockSignals(True)
        it = QTreeWidgetItemIterator(self)
        while it.value():
            item = it.value()
            if item.type == 'image':
                if item.target == image:
                    item.setIcon(0, self.icon_eyeopen)
                    item.setCheckState(0, Qt.Checked)
                    item.setExpanded(True)
                else:
                    item.setIcon(0, self.icon_eyeclosed)
                    item.setCheckState(0, Qt.Unchecked)
                    item.setExpanded(False)

                for i in range(item.childCount()):
                        child = item.child(i)
                        if item.target == image:
                            child.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                        else:
                            child.setFlags(Qt.NoItemFlags) #Qt.ItemIsEnabled)

            it += 1
        
        self.blockSignals(False)


    def itemChecked(self, item):
        if item.type == 'image':
            self.setImage(item.target)
            self.showImage.emit(item.target)
        elif item.type == 'layer':
            if item.checkState(0) == Qt.Checked:
                self.showLayer.emit(item.target)
            else:
                self.hideLayer.emit(item.target)
