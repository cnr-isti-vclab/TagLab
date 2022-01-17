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
    toggleLayer = pyqtSignal(Layer, bool)
    toggleAnnotations = pyqtSignal(Image, bool)

    def __init__(self, parent=None):
        super(QtLayersWidget, self).__init__(parent)

        self.setHeaderHidden(True)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        self.setMinimumWidth(300)
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


            child = QTreeWidgetItem()
            child.setText(0, "Annotations")
            child.setCheckState(0, Qt.Checked)
            child.setFlags(Qt.NoItemFlags)
            child.type = 'annotations'
            child.target = image
            item.addChild(child)


            for layer in image.layers:
                child = QTreeWidgetItem()
                child.setText(0, layer.name)
                if layer.isEnabled():
                    child.setCheckState(0, Qt.Checked)
                else:
                    child.setCheckState(0, Qt.Unhecked)
                child.setFlags(Qt.NoItemFlags)
                child.type = 'layer'
                child.target = layer
                item.addChild(child)

            items.append(item)
            
            
        self.insertTopLevelItems(0, items);
        self.blockSignals(False)

    def setImage(self, image1, image2 = None):
        self.blockSignals(True)
        it = QTreeWidgetItemIterator(self)
        while it.value():
            item = it.value()
            if item.type == 'image':
                if item.target == image1 or item.target == image2:
                    item.setIcon(0, self.icon_eyeopen)
                    item.setCheckState(0, Qt.Checked)
                    if len(item.target.layers):
                        item.setExpanded(True)
                else:
                    item.setIcon(0, self.icon_eyeclosed)
                    item.setCheckState(0, Qt.Unchecked)
                    item.setExpanded(False)

                if image2 == None:
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                else:
                    item.setFlags( Qt.ItemIsEnabled)

                for i in range(item.childCount()):
                    child = item.child(i)
                    if item.target == image1 or item.target == image2:
                        child.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    else:
                        child.setFlags(Qt.NoItemFlags) #Qt.ItemIsEnabled)

            it += 1
        
        self.blockSignals(False)


    def itemChecked(self, item):
        checked = item.checkState(0) == Qt.Checked
        if item.type == 'image':
            self.setImage(item.target)
            self.showImage.emit(item.target)

        elif item.type == 'layer':
            self.toggleLayer.emit(item.target, checked)

        elif item.type == 'annotations':
            self.toggleAnnotations.emit(item.target, checked)
