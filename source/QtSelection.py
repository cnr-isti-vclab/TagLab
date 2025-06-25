from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox, QLineEdit, QFrame


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
        
        main_layout.addLayout(class_layout)

             
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

        # Set the initial value of the thresholds
        self.areaThreshold = [1000000000.0, -1000000000.0]
        for blob in self.activeviewer.image.annotations.seg_blobs:
            if blob.area < self.areaThreshold[0]:
                self.areaThreshold[0] = blob.area
            if blob.area > self.areaThreshold[1]:
                self.areaThreshold[1] = blob.area
        self.areaThresholdInput0.setText(str(self.areaThreshold[0] / 100.0))  # Convert to square cm
        self.areaThresholdInput1.setText(str(self.areaThreshold[1] / 100.0))  # Convert to square cm
        self.perimeterThreshold = [1000000000.0, -1000000000.0]
        for blob in self.activeviewer.image.annotations.seg_blobs:
            if blob.perimeter < self.perimeterThreshold[0]:
                self.perimeterThreshold[0] = blob.perimeter
            if blob.perimeter > self.perimeterThreshold[1]:
                self.perimeterThreshold[1] = blob.perimeter
        self.perimeterThresholdInput0.setText(str(self.perimeterThreshold[0] / 10)) # Convert to cm
        self.perimeterThresholdInput1.setText(str(self.perimeterThreshold[1] / 10)) # Convert to cm



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
        if not (self.areaCheckBox.isChecked() or self.perimeterCheckBox.isChecked() or self.classCheckBox.isChecked()):
            return
        
        # Get the threshold values from the input fields
        try:
            self.areaThreshold[0] = float(self.areaThresholdInput0.text()) * 100.0  # Convert to square mm
            self.areaThreshold[1] = float(self.areaThresholdInput1.text()) * 100.0  # Convert to square mm
            self.perimeterThreshold[0] = float(self.perimeterThresholdInput0.text()) * 10 # Convert to mm
            self.perimeterThreshold[1] = float(self.perimeterThresholdInput1.text()) * 10 # Convert to mm
        except ValueError:
            print("Invalid input for thresholds")
            return
        if (self.areaThreshold[0] > self.areaThreshold[1]) or (self.perimeterThreshold[0] > self.perimeterThreshold[1]):
            print("Min should be less than or equal to Max")
            return

        for blob in self.activeviewer.image.annotations.seg_blobs:
            isValid = True
            if self.areaCheckBox.isChecked():
                print(f"choosing regions with area thresholds: {self.areaThreshold[0]} - {self.areaThreshold[1]}")
                if blob.area < self.areaThreshold[0] or blob.area > self.areaThreshold[1]:
                    isValid = False
            if self.perimeterCheckBox.isChecked():
                print(f"choosing regions with perimeter thresholds: {self.perimeterThreshold[0]} - {self.perimeterThreshold[1]}")
                if blob.perimeter < self.perimeterThreshold[0] or blob.perimeter > self.perimeterThreshold[1]:
                    isValid = False
            if self.classCheckBox.isChecked():
                print("choosing regions with class filter (not implemented)")
                # Implement class filtering logic here if needed

            # If any of the conditions are not met, skip this blob
            if not isValid: 
                continue
            
            # If we reach here, the blob meets all the conditions
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

    