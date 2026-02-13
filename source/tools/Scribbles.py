import numpy as np

from PyQt5.QtCore import Qt, QObject, QPointF, QRectF, QFileInfo, QDir, pyqtSlot, pyqtSignal, QT_VERSION_STR
from PyQt5.QtGui import QImage, QPixmap, QPainter, QPainterPath, QPen, QBrush, QCursor, QColor
from PyQt5.QtWidgets import QApplication, QGraphicsView, QGraphicsItem, QGraphicsScene, QFileDialog, QGraphicsPixmapItem

from source.Label import Label

class Scribbles(QObject):
    log = pyqtSignal(str)

    def __init__(self, scene):
        super(Scribbles, self).__init__()

        self.scene = scene
        self.points = []
        self.label = []
        self.size = []
        self.current_size = 30

        self.border_pen = QPen(Qt.black, self.current_size)
        self.border_pen.setCapStyle(Qt.RoundCap)
        self.border_pen.setCosmetic(False)

        self.current_label = Label("Background", "Background", description=None, fill=[0, 0, 0])
        self.previous_label = Label("Background", "Background", description=None, fill=[0, 0, 0])

        self.qpath_gitem = None
        self.qpath_list = []

        # scale factor of the cursor
        self.scale_factor = 1.0

        self.setCustomCursor()

    def reset(self):

        for qpath_gitem in self.qpath_list:
            self.scene.removeItem(qpath_gitem)

        self.qpath_list = []
        self.points = []
        self.label = []
        self.size = []
        self.scene.invalidate()

    def deleteLastScribble(self):
        """Delete the most recently drawn scribble."""
        if len(self.points) > 0:
            # Remove the visual representation from the scene
            last_qpath = self.qpath_list[-1]
            if last_qpath.scene() is not None:
                self.scene.removeItem(last_qpath)
            
            # Remove from all lists
            self.points.pop()
            self.label.pop()
            self.size.pop()
            self.qpath_list.pop()
            
            self.scene.invalidate()
            self.scene.update()
            return True
        return False

    def deleteScribbleByIndex(self, index):
        """Delete a specific scribble by its index."""
        if 0 <= index < len(self.points):
            # Remove the visual representation from the scene
            qpath = self.qpath_list[index]
            if qpath.scene() is not None:
                self.scene.removeItem(qpath)
            
            # Remove from all lists
            del self.points[index]
            del self.label[index]
            del self.size[index]
            del self.qpath_list[index]
            
            self.scene.invalidate()
            self.scene.update()
            return True
        return False

    def findScribbleNear(self, x, y, tolerance=20):
        """Find the index of a scribble near the given coordinates.
        Returns the index of the nearest scribble within tolerance, or -1 if none found."""
        min_distance = float('inf')
        nearest_index = -1
        
        for i, curve in enumerate(self.points):
            # Calculate minimum distance from point to any point in the curve
            distances = np.sqrt((curve[:, 0] - x)**2 + (curve[:, 1] - y)**2)
            min_dist_to_curve = np.min(distances)
            
            if min_dist_to_curve < min_distance and min_dist_to_curve <= tolerance:
                min_distance = min_dist_to_curve
                nearest_index = i
        
        return nearest_index

    def createScribblePen(self, color, size):
        """Create a pen with checkerboard pattern for better visibility."""
        # For very light colors (like white), use a checkerboard pattern
        rgb_sum = color[0] + color[1] + color[2]
        
        if rgb_sum > 650:  # Very light color (near white)
            # Create a custom black & white checkerboard pattern
            pattern_size = 4
            pixmap = QPixmap(pattern_size, pattern_size)
            pixmap.fill(Qt.white)
            painter = QPainter(pixmap)
            painter.fillRect(0, 0, pattern_size // 2, pattern_size // 2, Qt.black)
            painter.fillRect(pattern_size // 2, pattern_size // 2, pattern_size // 2, pattern_size // 2, Qt.black)
            painter.end()
            
            pattern_brush = QBrush(pixmap)
            pen = QPen(pattern_brush, size)
            pen.setCapStyle(Qt.RoundCap)
            pen.setCosmetic(False)
        elif rgb_sum < 100:  # Very dark color (near black)
            # Create a custom white & black checkerboard pattern (inverted)
            pattern_size = 4
            pixmap = QPixmap(pattern_size, pattern_size)
            pixmap.fill(Qt.black)
            painter = QPainter(pixmap)
            painter.fillRect(0, 0, pattern_size // 2, pattern_size // 2, Qt.white)
            painter.fillRect(pattern_size // 2, pattern_size // 2, pattern_size // 2, pattern_size // 2, Qt.white)
            painter.end()
            
            pattern_brush = QBrush(pixmap)
            pen = QPen(pattern_brush, size)
            pen.setCapStyle(Qt.RoundCap)
            pen.setCosmetic(False)
        else:
            # Normal solid pen for mid-tone colors
            pen = QPen(QColor(color[0], color[1], color[2]), size)
            pen.setCapStyle(Qt.RoundCap)
            pen.setCosmetic(False)
        
        return pen

    def saveState(self):
        """Save the current scribbles state for later restoration."""
        import copy
        saved_state = {
            'points': copy.deepcopy(self.points),
            'label': copy.deepcopy(self.label),
            'size': copy.deepcopy(self.size)
        }
        return saved_state

    def restoreState(self, saved_state):
        """Restore scribbles from a saved state."""
        import copy
        # First clear current scribbles
        self.reset()
        
        # Restore the data
        self.points = copy.deepcopy(saved_state['points'])
        self.label = copy.deepcopy(saved_state['label'])
        self.size = copy.deepcopy(saved_state['size'])
        
        # Recreate the visual representations
        for i in range(len(self.points)):
            curve = self.points[i]
            label = self.label[i]
            size = self.size[i]
            
            # Create pen with pattern for this scribble
            color = label.fill
            pen = self.createScribblePen(color, size)
            
            # Create path
            path = QPainterPath()
            path.moveTo(QPointF(curve[0][0], curve[0][1]))
            for point in curve[1:]:
                path.lineTo(QPointF(point[0], point[1]))
            
            # Add to scene
            qpath_gitem = self.scene.addPath(path, pen)
            qpath_gitem.setZValue(5)
            self.qpath_list.append(qpath_gitem)
        
        self.scene.invalidate()

    def setCustomCursor(self):

        cursor_size = 10
        #for QPen object and pixmap if QPen active
        pen_size = int(self.current_size * self.scale_factor)

        #if pen_size is > cursor_size(10) create a QPixmap of pen_size dimension
        if pen_size > cursor_size:
            pxmap = QPixmap(pen_size, pen_size)
        else:
            pxmap = QPixmap(cursor_size, cursor_size)
        pxmap.fill(QColor("transparent"))
        painter = QPainter(pxmap)
        color = self.current_label.fill
        
        #add a QPen if the size of the pxmap is > 10 (cursor/brush fixed size)
        #pen same color of the class, brush always black
        if pen_size > cursor_size:
            pen = QPen(QColor(color[0], color[1], color[2]), 3, Qt.DotLine)
            painter.setPen(pen)
            painter.drawEllipse(0, 0, pen_size, pen_size)
            # painter.drawRect(0, 0, pen_size, pen_size)

        #brush always black and 10 px dimension
        # brush = QBrush(QColor(0, 0, 0))
        brush = QBrush(QColor(color[0], color[1], color[2]))
        painter.setBrush(brush)
        
        #if pen_size is too small the brush fills all the pxmap
        if pen_size < cursor_size:
            painter.drawEllipse(0, 0, cursor_size, cursor_size)
        #if pen_size is > 10 the brush is put in the middle of the pxmap
        # -5 needed to have the center of the brush circle and not the top-left corner in the middle
        else:
            painter.drawEllipse( int(pen_size/2-5), int(pen_size/2-5), cursor_size, cursor_size)

        painter.end()
        custom_cursor = QCursor(pxmap)
        QApplication.setOverrideCursor(custom_cursor)

    def setLabel(self, label):

        # if self.current_label.id != "pippo":
        #     self.previous_label = self.current_label
        
        self.current_label = label

        # new cursor color and pen with pattern
        color = label.fill
        self.border_pen = self.createScribblePen(color, self.current_size)

        self.setCustomCursor()

    def setScaleFactor(self, scale_factor):

        self.scale_factor = scale_factor

    def setSize(self, delta_size):

        new_size = self.current_size + delta_size

        if new_size < 10:
            new_size = 10
        elif new_size > 200:
            new_size = 200

        self.current_size = new_size
        # Recreate pen with new size
        color = self.current_label.fill
        self.border_pen = self.createScribblePen(color, self.current_size)

        self.setCustomCursor()

    # return true if the first points for a tool
    def startDrawing(self, x, y):
        first_start = False
        if len(self.points) == 0:  # first point, initialize
            first_start = True
            message = "[TOOL] DRAWING starts.."
            self.log.emit(message)

        self.points.append(np.array([[x, y]]))
        self.label.append(self.current_label)
        self.size.append(self.current_size)

        self.qpath_gitem = self.scene.addPath(QPainterPath(), self.border_pen)
        self.qpath_gitem.setZValue(5)

        path = self.qpath_gitem.path()
        path.moveTo(QPointF(x, y))
        self.qpath_list.append(self.qpath_gitem)

        self.qpath_gitem.setPath(path)
        self.scene.invalidate()

        return first_start

    def move(self, x, y):
 
        if len(self.points) == 0:
            return

        # check that a move didn't happen before a press
        last_line = self.points[-1]

        last_point = self.points[-1][-1]
        if x != last_point[0] or y != last_point[1]:
            self.points[-1] = np.append(last_line, [[x, y]], axis=0)
            path = self.qpath_list[-1].path()
            path.lineTo(QPointF(x, y))
            self.qpath_gitem.setPath(path)
            self.qpath_gitem.setPen(self.border_pen)
            self.scene.invalidate()
