from PyQt5.QtCore import Qt,QSize, QEvent, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QWidget, QSizePolicy, QPushButton, QHeaderView
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
    toggleAnnotations = pyqtSignal(str, Image, bool)
    deleteLayer = pyqtSignal(Image, Layer)

    def __init__(self, parent=None):
        super(QtLayersWidget, self).__init__(parent)

        self.setHeaderHidden(True)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        self.setMinimumWidth(300)
        self.setMinimumHeight(60)

        self.trash = QIcon(imdir+os.path.join("icons", "trash.png"))
        self.icon_eyeopen = QIcon(imdir+os.path.join("icons", "eye.png"))
        self.icon_eyeclosed = QIcon(imdir+os.path.join("icons", "cross.png"))
        self.itemChanged.connect(self.itemChecked)

        self.setColumnCount(2)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.header().setStretchLastSection(False)
        self.setColumnWidth(1, 24)

        self.current_images = None

    def setProject(self, project):

        if self.current_images == project.images:
            return

        self.current_images = project.images.copy()

        self.blockSignals(True)
        self.clear()

        #items = []
        for image in project.images:
            item = QTreeWidgetItem()
            item.setText(0, image.name)
            item.setIcon(0, self.icon_eyeclosed)
            item.setCheckState(0, Qt.Unchecked)
            item.setExpanded(True)

            item.type = 'image'
            item.image = image

            child = QTreeWidgetItem()
            child.setText(0, "Annotations")
            child.setCheckState(0, Qt.Checked)
            child.setFlags(Qt.NoItemFlags)
            child.type = 'annotations'
            child.image = image
            item.addChild(child)

            subchild = QTreeWidgetItem()
            subchild.setText(0, "Regions")
            subchild.setCheckState(0, Qt.Checked)
            subchild.setFlags(Qt.NoItemFlags)
            subchild.type = 'ann-regions'
            subchild.image = image
            child.addChild(subchild)

            subchild = QTreeWidgetItem()
            subchild.setText(0, "Points")
            subchild.setCheckState(0, Qt.Checked)
            subchild.setFlags(Qt.NoItemFlags)
            subchild.type = 'ann-points'
            subchild.image = image
            child.addChild(subchild)

            for layer in image.layers:
                child = QTreeWidgetItem()
                child.setText(0, layer.name)
                if layer.isEnabled():
                    child.setCheckState(0, Qt.Checked)
                else:
                    child.setCheckState(0, Qt.Unchecked)
                child.setFlags(Qt.NoItemFlags)
                child.type = 'layer'
                child.layer = layer
                child.image = image
                

                item.addChild(child)
                # ui->treeWidget->setItemWidget(items.value(1),0,new QPushButton("Click Me")); // Solution for your problem 

            #items.append(item)
            self.addTopLevelItem(item);

        it = QTreeWidgetItemIterator(self)
        while it.value():
            item = it.value()
            if item.type == 'layer':
                image = item.image
                layer = item.layer
                type = item.type
                button = QPushButton()
                button.setIcon(self.trash)
                #button.setFixedWidth(100)
                button.clicked.connect(lambda x: self.deleteLayer.emit(image, layer))
                self.setItemWidget(item, 1, button)
            it += 1

        self.blockSignals(False)

    def setImage(self, image1, image2 = None):

        self.blockSignals(True)
        it = QTreeWidgetItemIterator(self)
        while it.value():
            item = it.value()
            if item.type == 'image':
                if item.image == image1 or item.image == image2:
                    item.setIcon(0, self.icon_eyeopen)
                    item.setCheckState(0, Qt.Checked)
                    if len(item.image.layers):
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
                    if item.image == image1 or item.image == image2:
                        child.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    else:
                        child.setFlags(Qt.NoItemFlags)

                    for j in range(child.childCount()):
                        subchild = child.child(j)

                        if item.image == image1 or item.image == image2:
                            subchild.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                        else:
                            subchild.setFlags(Qt.NoItemFlags)

            it += 1
        
        self.blockSignals(False)


    def itemChecked(self, item):

        checked = item.checkState(0) == Qt.Checked
        if item.type == 'image':
            self.setImage(item.image)
            self.showImage.emit(item.image)

        elif item.type == 'layer':
            self.toggleLayer.emit(item.layer, checked)

        elif item.type == 'annotations':
            self.toggleAnnotations.emit("regions", item.image, checked)
            self.toggleAnnotations.emit("points", item.image, checked)

        elif item.type == 'ann-regions':
            self.toggleAnnotations.emit("regions", item.image, checked)

        elif item.type == 'ann-points':
            self.toggleAnnotations.emit("points", item.image, checked)

