from PyQt5.QtCore import Qt, QSize, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QSizePolicy, QLabel, QToolButton, QPushButton, QHBoxLayout, QVBoxLayout

# CLASS COLORS - DEFAULT
class Labels:

    def __init__(self):

        self.LABELS_LIST = [("Corallimorph/Urchin", [255, 0, 10]),
                            ("Sea Star", [113, 39, 43]),
                            ("Sea Cucumber", [55, 5, 8]),
                            ("Cavularia", [158, 11, 15]),
                            ("Zooanthid", [121, 0, 0]),
                            ("Sinularia", [117, 76, 36]),
                            ("Sarcophyton", [96, 57, 19]),
                            ("Cryptodendrum", [140, 98, 57]),
                            ("Pocillopora", [240, 110, 170]),
                            ("Pocillopora_damicornis", [231, 70, 170]),
                            ("Pocillopora_zelli", [240, 171, 203]),
                            ("Pocillopora_eydouxi", [102, 45, 145]),
                            ("Stylophora", [146, 39, 143]),
                            ("Acropora_branching", [158, 0, 93]),
                            ("Acropora_corymbose", [133, 96, 168]),
                            ("Montipora_capitata", [119, 255, 198]),
                            ("Pavona_cactus", [23, 146, 144]),
                            ("Porites_branching", [0, 169, 157]),
                            ("Favites_crust", [255, 247, 153]),
                            ("Montipora_crust/patula", [171, 160, 0]),
                            ("Pavona_varians", [255, 255, 0]),
                            ("Porites_superfusa", [251, 175, 93]),
                            ("Hydnophora_pilosa", [253, 198, 137]),
                            ("Leptastrea", [255, 245, 104]),
                            ("Psammocora", [163, 211, 156]),
                            ("Leptoseris", [130, 123, 0]),
                            ("Fungia_single", [242, 101, 34]),
                            ("Fungia_multiple", [247, 148, 29]),
                            ("Porite_massive", [109, 207, 246]),
                            ("Porites_rus", [81, 191, 223]),
                            ("Flavia_matthai", [122, 204, 200]),
                            ("Hydnophora_microconos", [131, 147, 202]),
                            ("Montastrea", [0, 174, 239]),
                            ("Cyphastrea", [140, 187, 184]),
                            ("Lobophyllia", [0, 84, 166]),
                            ("Platgyra", [0, 91, 127]),
                            ("Favia_submassive", [125, 167, 217]),
                            ("Favites_submassive", [27, 20, 100]),
                            ("Pavona_submassive", [46, 49, 146]),
                            ("Goniastrea_pectinata", [86, 116, 185]),
                            ("Astreopora", [0, 52, 113]),
                            ("Acropora_table", [0, 94, 32]),
                            ("Montipora_plate/flabellata", [89, 133, 39]),
                            ("Hydnophora_exesa", [0, 166, 81]),
                            ("Tubinaria", [141, 198, 63]),
                            ("Tubastrea", [170, 202, 174]),
                            ("CCA", [254, 207, 5]),
                            ("Halimeda", [0, 255, 0]),
                            ("Dictyophaeria", [64, 102, 24]),
                            ("Lobophora", [233, 5, 254]),
                            ("Peysonnelia", [35, 177, 233]),
                            ("CCA Other", [7, 55, 210]),
                            ("30/70 CCA + Turf", [7, 210, 17]),
                            ("70/30 CCA + Turf", [254, 5, 81]),
                            ("50/50 CCA + Turf", [122, 7, 210]),
                            ("Turf", [36, 124, 77]),
                            ("Caulerpa", [133, 170, 81]),
                            ("Avrainvillea", [19, 41, 23]),
                            ("Galaxaura", [157, 29, 31]),
                            ("Halimeda opuntia", [161, 239, 24]),
                            ("Halimeda fragilis", [98, 151, 103]),
                            ("Halimeda taenicola", [20, 114, 20]),
                            ("Diplosoma", [89, 252, 100]),
                            ("Unknow", [225, 225, 225]),
                            ("Unknow_submassive", [183, 183, 183]),
                            ("Unknow_massive", [149, 149, 149]),
                            ("Unknow_crust", [85, 85, 85]),
                            ("Other", [54, 54, 54])]

        self.NCLASSES = len(self.LABELS_LIST) + 1

        self.LABELS_LIST.sort(key=lambda tup : tup[0])
        self.LABELS_LIST.insert(0, ("Empty", [0, 0, 0]))

    def getClassName(self, index):

        return self.LABELS_LIST[index][0]

    def getColorByIndex(self, index):

        return self.LABELS_LIST[index][1]

    def getColorByName(self, class_name):

        for label in self.LABELS_LIST:
            if label[0] == class_name:
                return label[1]

        return [0, 0, 0]


class ClickableLabel(QLabel):

    # signals
    clicked = pyqtSignal(int)

    def __init__(self, id, parent=None):
        super(QLabel, self).__init__(parent)

        # identify the label clicked
        self.id = id

    def mousePressEvent(self, event):
        self.clicked.emit(self.id)


class LabelsWidget(QWidget):

    visibilityChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(LabelsWidget, self).__init__(parent)

        self.labels = Labels()

        self.btnVisible = []
        self.visibility_flags = []
        self.btnClass = []
        self.lblClass = []

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.setMinimumWidth(400)
        self.setMinimumHeight(200)


        self.icon_eyeopen = QIcon("eye.png")
        self.icon_eyeclosed = QIcon("cross.png")

        labels_layout = QVBoxLayout()
        self.setLayout(labels_layout)


        CLASS_LABELS_HEIGHT = 20
        EYE_ICON_SIZE = 20

        for i in range(self.labels.NCLASSES):

            btnV = QPushButton()
            btnV.setFlat(True)
            btnV.setIcon(self.icon_eyeopen)
            btnV.setIconSize(QSize(EYE_ICON_SIZE, EYE_ICON_SIZE))
            btnV.setFixedWidth(CLASS_LABELS_HEIGHT)
            btnV.setFixedHeight(CLASS_LABELS_HEIGHT)

            btnC = QPushButton("")
            btnC.setFlat(True)

            text = ""
            if i == 0:
                text = "QPushButton:flat {background-color: rgba(0,0,0,0); border: 1px dashed white;}"
            else:
                color = self.labels.getColorByIndex(i)
                r = color[0]
                g = color[1]
                b = color[2]
                text = "QPushButton:flat {background-color: rgb(" + str(r) + "," + str(g) + "," + str(b) + "); border: none ;}"

            btnC.setStyleSheet(text)
            btnC.setAutoFillBackground(True)
            btnC.setFixedWidth(CLASS_LABELS_HEIGHT)
            btnC.setFixedHeight(CLASS_LABELS_HEIGHT)

            lbl = ClickableLabel(i)
            lbl.setStyleSheet("QLabel {color : lightgray;}")
            lbl.setText(self.labels.getClassName(i))
            lbl.setFixedHeight(CLASS_LABELS_HEIGHT)

            self.btnVisible.append(btnV)
            self.visibility_flags.append(True)
            self.btnClass.append(btnC)
            self.lblClass.append(lbl)

            btnV.clicked.connect(self.toggleVisibility)
            lbl.clicked.connect(self.highlightSelectedLabel)

            layout = QHBoxLayout()
            layout.addWidget(btnV)
            layout.addWidget(btnC)
            layout.addWidget(lbl)
            labels_layout.addLayout(layout)

        labels_layout.setSpacing(2)

        ### FURTHER INITIALIZATION
        self.active_label_index = 0
        self.highlightSelectedLabel(0)

    def setAllVisible(self):

        for i in range(len(self.visibility_flags)):
            self.btnVisible[i].setIcon(self.icon_eyeopen)
            self.visibility_flags[i] = True

    def setAllNotVisible(self):

        for i in range(len(self.visibility_flags)):
            self.btnVisible[i].setIcon(self.icon_eyeclosed)
            self.visibility_flags[i] = False


    @pyqtSlot()
    def toggleVisibility(self):
        button_clicked = self.sender()

        index = self.btnVisible.index(button_clicked)

        if QApplication.keyboardModifiers() == Qt.ControlModifier:

            self.setAllNotVisible()
            button_clicked.setIcon(self.icon_eyeopen)
            self.visibility_flags[index] = True

        elif QApplication.keyboardModifiers() == Qt.ShiftModifier:

            self.setAllVisible()
            button_clicked.setIcon(self.icon_eyeclosed)
            self.visibility_flags[index] = False

        else:

            if self.visibility_flags[index]:
                button_clicked.setIcon(self.icon_eyeclosed)
                self.visibility_flags[index] = False
            else:
                button_clicked.setIcon(self.icon_eyeopen)
                self.visibility_flags[index] = True

        self.visibilityChanged.emit()

    @pyqtSlot(int)
    def highlightSelectedLabel(self, index):

        for i in range(self.labels.NCLASSES):
            self.lblClass[i].setText(self.labels.getClassName(i))
            self.lblClass[i].setStyleSheet("QLabel { color : lightgray; }")

        str = "<b>" + self.labels.getClassName(index) + "</b>"
        self.lblClass[index].setText(str)
        self.lblClass[index].setStyleSheet("QLabel { color : white; background : light gray}")

        self.active_label_index = index

    def isClassVisible(self, class_name):
        for i in range(self.labels.NCLASSES):
            if self.labels.getClassName(i) == class_name:
                return self.visibility_flags[i]

        return False

    def getActiveLabelColor(self):

        return self.labels.getColorByIndex(self.active_label_index)

    def getActiveLabelName(self):

        return self.labels.getClassName(self.active_label_index)
