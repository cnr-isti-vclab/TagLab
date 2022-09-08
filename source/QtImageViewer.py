import os.path
from PyQt5.QtCore import Qt, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QImageReader, QMouseEvent
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

class QtImageViewer(QGraphicsView):
    """
    Basic PyQt image viewer with pan and zoom capabilities.
    The input image (it must be a QImage) is internally converted into a QPixmap.
    """

    viewUpdated = pyqtSignal(QRectF)                  # region visible in percentage
    viewHasChanged = pyqtSignal(float, float, float)  # posx, posy, posz

    mouseDown = pyqtSignal(QMouseEvent)
    mouseMove = pyqtSignal(QMouseEvent)
    mouseUp = pyqtSignal(QMouseEvent)

    mouseOut = pyqtSignal()

    def __init__(self):
        QGraphicsView.__init__(self)

        self.setStyleSheet("background-color: rgb(40,40,40)")

        # MAIN SCENE
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # local handle to the scene's current image pixmap.
        self.pixmapitem = QGraphicsPixmapItem()
        self.pixmapitem.setZValue(0)
        self.scene.addItem(self.pixmapitem)

        # OVERLAY
        self.scene_overlay = QGraphicsScene()

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
        self.ZOOM_FACTOR_MIN = 0.5
        self.ZOOM_FACTOR_MAX = 16.0

        self.px_to_mm = 1.0

        # transparency
        self.opacity = 1.0

        MIN_SIZE = 250
        self.pixmap = QPixmap(MIN_SIZE, MIN_SIZE)
        self.thumb = None
        self.overlay_image = QImage(1, 1, QImage.Format_ARGB32)

        self.viewport().setMinimumWidth(MIN_SIZE)
        self.viewport().setMinimumHeight(MIN_SIZE)

        self.resetTransform()
        self.setMouseTracking(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def setImg(self, img, zoomf=0.0):
        """
        Set the scene's current image (input image must be a QImage)
        For calculating the zoom factor automatically set it to 0.0.
        """

        self.img_map = img
        if type(img) is QImage:
            imageARGB32 = img.convertToFormat(QImage.Format_ARGB32)
            self.pixmap = QPixmap.fromImage(imageARGB32)
            self.thumb = None
            self.imgwidth = img.width()
            self.imgheight = img.height()
            if self.imgheight:
                self.ZOOM_FACTOR_MIN = min(1.0 * self.width() / self.imgwidth, 1.0 * self.height() / self.imgheight)
        else:
            raise RuntimeError("Argument must be a QImage.")

        self.pixmapitem.setPixmap(self.pixmap)

        if zoomf < 0.0000001:

            # calculate zoom factor

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
        if not self.imgwidth:
            return
        rect = self.viewportToScenePercent()
        self.viewUpdated.emit(rect)
        posx = self.horizontalScrollBar().value() 
        posy = self.verticalScrollBar().value() 
        zoom = self.zoom_factor / self.px_to_mm
        self.viewHasChanged.emit(posx, posy, zoom)

    def setViewParameters(self, posx, posy, zoomfactor):
        if not self.isVisible():
            return
        self.blockSignals(True)
        self.horizontalScrollBar().setValue(posx)
        self.verticalScrollBar().setValue(posy)
        self.zoom_factor = zoomfactor * self.px_to_mm
        self.updateViewer()
        self.blockSignals(False)

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
        if self.imgheight:
            self.ZOOM_FACTOR_MIN = min(1.0 * self.width() / self.imgwidth, 1.0 * self.height() / self.imgheight)
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

    def mouseMoveEvent(self, event):
        self.mouseMove.emit(event)
        QGraphicsView.mouseMoveEvent(self, event)

    def mousePressEvent(self, event):
        """
        Begin panning (if enable)
        """
        if event.button() == Qt.LeftButton:
            if self.panEnabled:
                self.setDragMode(QGraphicsView.ScrollHandDrag)

        self.mouseDown.emit(event)
        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        Stop mouse pan.
        """
        self.mouseUp.emit(event)
        QGraphicsView.mouseReleaseEvent(self, event)
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)

    def leaveEvent(self, event) -> None:
        self.mouseOut.emit()

    def wheelEvent(self, event):
        """
        Zoom in/zoom out.
        """
        if self.zoomEnabled:

            view_pos = event.pos()
            scene_pos = self.mapToScene(view_pos)
            self.centerOn(scene_pos)

            pt = event.angleDelta()

            self.zoom_factor = self.zoom_factor*pow(pow(2, 1/2), pt.y()/100)
            if self.zoom_factor < self.ZOOM_FACTOR_MIN * 0.5:
                self.zoom_factor = self.ZOOM_FACTOR_MIN * 0.5
            if self.zoom_factor > self.ZOOM_FACTOR_MAX:
                self.zoom_factor = self.ZOOM_FACTOR_MAX

            self.resetTransform()
            self.scale(self.zoom_factor, self.zoom_factor)

            delta = self.mapToScene(view_pos) - self.mapToScene(self.viewport().rect().center())
            self.centerOn(scene_pos - delta)

            self.invalidateScene()

    def paintEvent(self, event):

        # render the main scene (self.scene)
        super(QtImageViewer, self).paintEvent(event)

        # render the overlay
        p = QPainter(self.viewport())
        p.setRenderHints(self.renderHints())
        self.scene_overlay.render(p, QRectF(self.viewport().rect()))

