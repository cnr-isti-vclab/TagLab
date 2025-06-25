from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox, QLineEdit, QFrame, QComboBox, QMessageBox, QRadioButton

class QtSelectByPropertiesWidget(QWidget):

    closewidget = pyqtSignal()

    def __init__(self, wiew, parent=None):
        super(QtSelectByPropertiesWidget, self).__init__(parent)

        self.parent = parent
        self.activeviewer = wiew

        ###########################################################
        self.setStyleSheet("background-color: rgb(40,40,40); color: white;")
        ###########################################################
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # by area
        area_layout = QHBoxLayout()
        self.areaCheckBox = QCheckBox("AREA")
        area_layout.addWidget(self.areaCheckBox)
        area_layout.addStretch()
        # add an input field for the threshold value
        self.areaThresholdInput0 = QLineEdit()
        area_layout.addWidget(self.areaThresholdInput0)
        self.areaThresholdInput1 = QLineEdit()
        area_layout.addWidget(self.areaThresholdInput1)
        main_layout.addLayout(area_layout)

        # by perimeter
        perimeter_layout = QHBoxLayout()
        perimeter_layout.setAlignment(Qt.AlignLeft)
        self.perimeterCheckBox = QCheckBox("PERIMETER")
        perimeter_layout.addWidget(self.perimeterCheckBox)
        perimeter_layout.addStretch()
        # add an input field for the threshold value
        self.perimeterThresholdInput0 = QLineEdit()
        perimeter_layout.addWidget(self.perimeterThresholdInput0)
        self.perimeterThresholdInput1 = QLineEdit()
        perimeter_layout.addWidget(self.perimeterThresholdInput1)        
        main_layout.addLayout(perimeter_layout)

        # by class
        class_layout = QHBoxLayout()
        class_layout.setAlignment(Qt.AlignLeft)
        self.classCheckBox = QCheckBox("CLASS")
        class_layout.addWidget(self.classCheckBox)
        class_layout.addStretch()
        # add a dropdown field for the class name
        self.classNameInput = QComboBox()
        classList = ["-- CURRENT --"]
        # add all labels in the dictionary of the parent labels widget
        for label in self.parent.project.labels:
            classList.append(label)
        self.classNameInput.addItems(classList)
        class_layout.addWidget(self.classNameInput)
        main_layout.addLayout(class_layout)

        # by position
        position_layout = QVBoxLayout()
        pr1l = QHBoxLayout()
        pr1l.setAlignment(Qt.AlignLeft)
        self.positionCheckBox = QCheckBox("POSITION")
        self.positionMinXInput = QLineEdit()
        self.positionMaxXInput = QLineEdit()
        pr1l.addWidget(self.positionCheckBox)
        pr1l.addStretch()
        pr1l.addWidget(QLabel("X:"))
        pr1l.addWidget(self.positionMinXInput)
        pr1l.addWidget(self.positionMaxXInput)
        pr2l = QHBoxLayout()
        pr2l.setAlignment(Qt.AlignLeft)
        self.positionMinYInput = QLineEdit()
        self.positionMaxYInput = QLineEdit()
        pr2l.addStretch()
        pr2l.addWidget(QLabel("Y:"))
        pr2l.addWidget(self.positionMinYInput)
        pr2l.addWidget(self.positionMaxYInput)
        pr3l = QHBoxLayout()
        pr3l.setAlignment(Qt.AlignLeft)        
        self.positionCheck = QComboBox()
        self.positionCheck.addItems(["Centroid", "Bounding Box"])
        pr3l.addStretch()
        pr3l.addWidget(QLabel("Check:"))        
        pr3l.addWidget(self.positionCheck)
        position_layout.addLayout(pr1l)
        position_layout.addLayout(pr2l)
        position_layout.addLayout(pr3l)
        main_layout.addLayout(position_layout)

        # add horizontal line separator to main layout
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator1)

        # add/remove buttons
        actions_layout = QHBoxLayout()
        actions_layout.setAlignment(Qt.AlignCenter)
        self.btnAdd = QPushButton("Add")
        self.btnAdd.clicked.connect(lambda: self.addRemove(add=True))
        self.btnRemove = QPushButton("Remove")
        self.btnRemove.clicked.connect(lambda: self.addRemove(add=False))
        self.btnAll = QPushButton("All")
        self.btnAll.clicked.connect(self.all)
        self.btnNone = QPushButton("None")
        self.btnNone.clicked.connect(self.none)
        self.btnInvert = QPushButton("Invert")
        self.btnInvert.clicked.connect(self.invert)
        actions_layout.addWidget(self.btnAdd)
        actions_layout.addWidget(self.btnRemove)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btnAll)
        actions_layout.addWidget(self.btnNone)
        actions_layout.addWidget(self.btnInvert)
        main_layout.addLayout(actions_layout)

        # add horizontal line separator to main layout
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Raised)
        main_layout.addWidget(separator2) 

        # bottom row buttons
        bottom_layout = QHBoxLayout()
        self.btnClose = QPushButton("Close")
        self.btnClose.clicked.connect(self.close)
        bottom_layout.setAlignment(Qt.AlignRight)
        self.selectedCount = QLabel("---")
        bottom_layout.addWidget(self.selectedCount)
        self.updateSelectedLabel()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btnClose)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)
        self.setWindowTitle("Select Regions by properties")
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(500)

        # Set the initial value of the thresholds based on the current blobs
        pxmm = self.parent.activeviewer.px_to_mm
        pxmm2 = pxmm * pxmm
        thresholdMin = 1000000000.0
        thresholdMax = -1000000000.0
        for blob in self.activeviewer.image.annotations.seg_blobs:
            if blob.area < thresholdMin:
                thresholdMin = blob.area
            if blob.area > thresholdMax:
                thresholdMax = blob.area
        self.areaThresholdInput0.setText(str(thresholdMin * pxmm2 / 100.0))  # Convert to square cm
        self.areaThresholdInput1.setText(str(thresholdMax * pxmm2 / 100.0))  # Convert to square cm
        thresholdMin = 1000000000.0
        thresholdMax = -1000000000.0
        for blob in self.activeviewer.image.annotations.seg_blobs:
            if blob.perimeter < thresholdMin:
                thresholdMin = blob.perimeter
            if blob.perimeter > thresholdMax:
                thresholdMax = blob.perimeter
        self.perimeterThresholdInput0.setText(str(thresholdMin * pxmm / 10)) # Convert to cm
        self.perimeterThresholdInput1.setText(str(thresholdMax * pxmm / 10)) # Convert to cm

        # Set the initial value of the position inputs based on the current image size
        self.positionMinXInput.setText("0")
        self.positionMinYInput.setText("0")
        self.positionMaxXInput.setText(str(self.parent.activeviewer.image.width))
        self.positionMaxYInput.setText(str(self.parent.activeviewer.image.height))


    # close the widget
    def closeEvent(self, event):
        self.closewidget.emit()
        super(QtSelectByPropertiesWidget, self).closeEvent(event)


    # Update the label with the number of selected blobs
    def updateSelectedLabel(self):
        self.selectedCount.setText(f"Total: {len(self.activeviewer.image.annotations.seg_blobs)} Selected: {len(self.activeviewer.selected_blobs)}")
        self.selectedCount.adjustSize()


    # Methods for the all/none/invert buttons
    def all(self):
        self.activeviewer.selectAllBlobs()
        self.updateSelectedLabel()
    def none(self):
        self.activeviewer.selectNoneBlobs()
        self.updateSelectedLabel()
    def invert(self):
        self.activeviewer.selectInverseBlobs()
        self.updateSelectedLabel()


    # Method to add or remove blobs based on the selected checkboxes and thresholds
    def addRemove(self, add=True):
        #if all checkboxes are unchecked, do nothing
        if not (self.areaCheckBox.isChecked() or self.perimeterCheckBox.isChecked() or self.classCheckBox.isChecked() or self.positionCheckBox.isChecked()):
            return

        # scale factors
        pxmm = self.parent.activeviewer.px_to_mm
        pxmm2 = pxmm * pxmm
        # get thresholds
        try:
            areaMin = float(self.areaThresholdInput0.text()) * 100.0 / pxmm2 # Convert to square mm
            areaMax = float(self.areaThresholdInput1.text()) * 100.0 / pxmm2 # Convert to square mm
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid input for area limits.")
            return
        if (areaMin > areaMax):
            QMessageBox.critical(self, "Error", "Area minimum limit should be less than or equal to maximum limit.")
            return
        # print(f"area thresholds: {areaMin} - {areaMax}")
        try:
            perimeterMin = float(self.perimeterThresholdInput0.text()) * 10 / pxmm # Convert to mm
            perimeterMax = float(self.perimeterThresholdInput1.text()) * 10 / pxmm # Convert to mm
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid input for perimeter limits.")
            return
        if (perimeterMin > perimeterMax):
            QMessageBox.critical(self, "Error", "Perimeter minimum limit should be less than or equal to maximum limit.")
            return
        # print(f"perimeter thresholds: {perimeterMin} - {perimeterMax}")
        try:
            posMinX = float(self.positionMinXInput.text())
            posMinY = float(self.positionMinYInput.text())
            posMaxX = float(self.positionMaxXInput.text())
            posMaxY = float(self.positionMaxYInput.text())
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid input for position.")
            return
        if (posMinX > posMaxX or posMinY > posMaxY):
            QMessageBox.critical(self, "Error", "Position minimum values should be less than or equal to maximum values.")
            return
        # print(f"position thresholds: {posMinX} - {posMaxX}, {posMinY} - {posMaxY}")

        for blob in self.activeviewer.image.annotations.seg_blobs:
            if self.areaCheckBox.isChecked():
                if blob.area < areaMin or blob.area > areaMax:
                    continue
            if self.perimeterCheckBox.isChecked():
                if blob.perimeter < perimeterMin or blob.perimeter > perimeterMax:
                    continue
            if self.classCheckBox.isChecked():
                if self.classNameInput.currentText() == "-- CURRENT --": # Use the currently active label
                    if (self.parent.labels_widget.getActiveLabelName() != blob.class_name):
                        continue
                else: # Use the selected class from the dropdown
                    if (self.classNameInput.currentText() != blob.class_name):
                        continue
            if self.positionCheckBox.isChecked():
                if self.positionCheck.currentText() == "Centroid":
                    if (blob.centroid[0] < posMinX or blob.centroid[0] > posMaxX or blob.centroid[1] < posMinY or blob.centroid[1] > posMaxY):
                        continue
                elif self.positionCheck.currentText() == "Bounding Box":  #warning: bbox is in (min_row, min_col, max_row, max_col) format
                    if (blob.bbox[0] < posMinY or blob.bbox[2] > posMaxY or
                        blob.bbox[1] < posMinX or blob.bbox[3] > posMaxX):
                        #print(f"Blob {blob.id} does not meet the bounding box position criteria.")
                        #print(f"Blob bbox: ({blob.bbox[1]}, {blob.bbox[0]}), ({blob.bbox[3]}, {blob.bbox[2]})")
                        continue

            # If we reach here, the blob meets all the conditions. Add or remove the blob from the selected blobs list depending on the add parameter
            if add:
                if blob not in self.activeviewer.selected_blobs:
                    self.activeviewer.selected_blobs.append(blob)
                    self.activeviewer.updateBlobQPath(blob, True)
            else:
                if blob in self.activeviewer.selected_blobs:
                    self.activeviewer.selected_blobs.remove(blob)
                    self.activeviewer.updateBlobQPath(blob, False)
        
        # Update the selected count label
        self.updateSelectedLabel()

    