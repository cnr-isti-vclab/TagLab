import os.path
from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QImageReader
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

class QtImageViewer(QGraphicsView):
    """
    PyQt image viewer widget w
    QGraphicsView handles a scene composed by an image plus shapes (rectangles, polygons, blobs).
    The input image (it must be a QImage) is internally converted into a QPixmap.
    """
    viewUpdated = pyqtSignal(QRectF)       #region visible in percentage

    def __init__(self):
        QGraphicsView.__init__(self)

        self.setStyleSheet("background-color: rgb(40,40,40)")
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Store a local handle to the scene's current image pixmap.
        self.pixmapitem = QGraphicsPixmapItem()
        self.pixmapitem.setZValue(0)
        self.scene.addItem(self.pixmapitem)

        self.img_map = None
        # current image size
        self.imgwidth = 0
        self.imgheight = 0

        # Image aspect ratio mode.
        self.aspectRatioMode = Qt.KeepAspectRatio

        # Set scrollbar
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.verticalScrollBar().valueChanged.connect(self.viewChanged)
        self.horizontalScrollBar().valueChanged.connect(self.viewChanged)

        # Panning is enabled if and only if the image is greater than the viewport.
        self.panEnabled = True
        self.zoomEnabled = True

        # zoom is always active
        self.zoom_factor = 1.0
        self.ZOOM_FACTOR_MIN = 0.02
        self.ZOOM_FACTOR_MAX = 10.0

        # transparency
        self.opacity = 1.0

        MIN_SIZE = 250
        self.pixmap = QPixmap(MIN_SIZE, MIN_SIZE)
        self.overlay_image = QImage(1, 1, QImage.Format_ARGB32)

        self.viewport().setMinimumWidth(MIN_SIZE)
        self.viewport().setMinimumHeight(MIN_SIZE)

        self.resetTransform()
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        #self.setContextMenuPolicy(Qt.CustomContextMenu)

    def setImg(self, img, zoomf=0.0):
        """
        Set the scene's current image (input image must be a QImage)
        For calculating the zoom factor automatically set it to 0.0.
        """

        self.img_map = img
        if type(img) is QImage:
            imageARGB32 = img.convertToFormat(QImage.Format_ARGB32)
            self.pixmap = QPixmap.fromImage(imageARGB32)
            self.imgwidth = img.width()
            self.imgheight = img.height()
        else:
            raise RuntimeError("Argument must be a QImage.")

        self.pixmapitem.setPixmap(self.pixmap)

        # Set scene size to image size (!)
        self.setSceneRect(QRectF(self.pixmap.rect()))

        # calculate zoom factor
        pixels_of_border = 10
        zf1 = (self.viewport().width() - pixels_of_border) / self.imgwidth
        zf2 = (self.viewport().height() - pixels_of_border) / self.imgheight

        zf = min(zf1, zf2)
        self.zoom_factor = zf

        self.updateViewer()
    @pyqtSlot()
    def viewChanged(self):
        rect = self.viewportToScenePercent()
        self.viewUpdated.emit(rect)

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        self.resetTransform()
        self.scale(self.zoom_factor, self.zoom_factor)

        self.invalidateScene()

    def clear(self):
        self.pixmapitem.setPixmap(QPixmap())
        self.img_map = None

    def disableScrollBars(self):

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def enablePan(self):
        self.panEnabled = True

    def disablePan(self):
        self.panEnabled = False

    def enableZoom(self):
        self.zoomEnabled = True

    def disableZoom(self):
        self.zoomEnabled = False


    def viewportToScene(self):
        #check
        topleft = self.mapToScene(self.viewport().rect().topLeft())
        bottomright = self.mapToScene(self.viewport().rect().bottomRight())
        return QRectF(topleft, bottomright)

    def viewportToScenePercent(self):
        view = self.viewportToScene()
        view.setCoords(view.left()/self.imgwidth, view.top()/self.imgheight,
                    view.right()/self.imgwidth, view.bottom()/self.imgheight)
        return view

    def clampCoords(self, x, y):

        if self.img_map is not None:
            xc = max(0, min(int(x), self.img_map.width()))
            yc = max(0, min(int(y), self.img_map.height()))
        else:
            xc = 0
            yc = 0

        return (xc, yc)

        # UNUSED
    def setOpacity(self, opacity):
        self.opacity = opacity

    def setOverlayImage(self, image):
        self.overlay_image = image.convertToFormat(QImage.Format_ARGB32)
        self.drawOverlayImage()

    def drawOverlayImage(self):

        if self.overlay_image.width() <= 1:
            return

        pxmap = self.pixmap.copy()
        p = QPainter()
        p.begin(pxmap)
        p.setOpacity(self.opacity)
        p.drawImage(0, 0, self.overlay_image)
        p.end()

        self.pixmapitem.setPixmap(pxmap)


    def setViewParameters(self, posx, posy, zoomfactor):
        self.horizontalScrollBar().setValue(posx)
        self.verticalScrollBar().setValue(posy)
        self.zoom_factor = zoomfactor
        self.updateViewer()

    def clipScenePos(self, scenePosition):
        posx = scenePosition.x()
        posy = scenePosition.y()
        if posx < 0:
            posx = 0
        if posy < 0:
            posy = 0
        if posx > self.imgwidth:
            posx = self.imgwidth
        if posy > self.imgheight:
            posy = self.imgheight

        return [round(posx), round(posy)]

    def resizeEvent(self, event):
        """ Maintain current zoom on resize.
        """
        self.updateViewer()

    @pyqtSlot(float, float)
    def center(self, x, y):

        zf = self.zoom_factor

        xmap = float(self.img_map.width()) * x
        ymap = float(self.img_map.height()) * y

        view = self.viewportToScene()
        (w, h) = (view.width(), view.height())

        posx = max(0, xmap - w / 2)
        posy = max(0, ymap - h / 2)

        posx = min(posx, self.img_map.width() - w / 2)
        posy = min(posy, self.img_map.height() - h / 2)

        self.horizontalScrollBar().setValue(posx * zf)
        self.verticalScrollBar().setValue(posy * zf)
