from source.tools.Tool import Tool
from source.Blob import Blob

import numpy as np
import cv2

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPen, QColor, QImage, QPixmap, QBrush
from PyQt5.QtWidgets import QMessageBox


class BrushTool(Tool):
    """
    Paint-brush tool for creating new regions and editing existing ones at the
    pixel level.

    Usage:
      - No selection: SHIFT + LMB drag to paint a new region in the viewport.
      - With a blob selected: SHIFT + LMB/RMB drag to add/remove pixels.
      - SHIFT + wheel to resize the brush.
      - SPACEBAR to commit.  ESC / switch tool to cancel.
    """

    MIN_PADDING = 50    # minimum margin in image pixels (covers at least one default brush radius)
    PAD_FRACTION = 0.25  # margin as a fraction of the blob's own width/height

    def __init__(self, viewerplus):
        super(BrushTool, self).__init__(viewerplus)

        self.brush_size = 30          # radius in image pixels

        # state
        self.original_blob  = None    # blob as it was when editing started
        self.working_mask   = None    # numpy uint8 (h, w) – the live pixel buffer
        self.working_bbox   = None    # [top, left, width, height] in image coords

        # scene items
        self.pixmap_item    = None    # QGraphicsPixmapItem showing the live mask
        self.cursor_item    = None    # QGraphicsEllipseItem brush-size ring
        self.work_area_item = None    # QGraphicsRectItem dashed border (creation mode only)

        # painting bookkeeping
        self.paint_mode     = 'add'   # 'add' | 'remove'
        self.is_painting    = False
        self._rgba_buf      = None    # kept alive to avoid GC while QImage uses it

        message  = "<p><i>Paint to create a new region or edit an existing one</i></p>"
        message += "<p>Select a region to edit it, or deselect all to create a new one</p>"
        message += "<p>- SHIFT + LMB drag &rarr; ADD pixels</p>"
        message += "<p>- SHIFT + RMB drag &rarr; REMOVE pixels</p>"
        message += "<p>- SHIFT + wheel &rarr; change brush size</p>"
        message += "<p>SPACEBAR to confirm &nbsp;|&nbsp; ESC to cancel</p>"
        self.tool_message = f'<div style="text-align: left;">{message}</div>'

    # ------------------------------------------------------------------
    # Tool lifecycle
    # ------------------------------------------------------------------

    def activate(self):
        self.viewerplus.showMessage(self.tool_message)
        self.viewerplus.selectionChanged.connect(self._onSelectionChanged)
        # If a blob is already selected when the tool is activated, use it.
        self._tryInitFromSelection()

    def deactivate(self):
        self.viewerplus.clearMessage()
        try:
            self.viewerplus.selectionChanged.disconnect(self._onSelectionChanged)
        except RuntimeError:
            pass
        self._cancelEditing()

    def reset(self):
        self._cancelEditing()

    def _onSelectionChanged(self):
        """Cancel any in-progress edit/creation when the selection changes."""
        if self.working_mask is None:
            return  # no active state
        if self.original_blob is None:
            # Creation mode: cancel if the user selects any blob.
            if len(self.viewerplus.selected_blobs) > 0:
                self._cancelEditing()
        else:
            # Edit mode: cancel if the user switches to a different blob.
            selected = self.viewerplus.selected_blobs
            if len(selected) != 1 or selected[0] is not self.original_blob:
                self._cancelEditing()

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def leftPressed(self, x, y, mods=None):
        if not (mods and mods & Qt.ShiftModifier):
            return
        if not self._ensureReady():
            return
        self.paint_mode  = 'add'
        self.is_painting = True
        self._paintAt(x, y)
        self.log.emit("[TOOL][BRUSH] Paint ADD started.")

    def rightPressed(self, x, y, mods=None):
        if not (mods and mods & Qt.ShiftModifier):
            return
        if not self._ensureReady():
            return
        self.paint_mode  = 'remove'
        self.is_painting = True
        self._paintAt(x, y)
        self.log.emit("[TOOL][BRUSH] Paint REMOVE started.")

    def mouseMove(self, x, y, mods=None):
        self._moveCursor(x, y)
        if self.is_painting:
            self._paintAt(x, y)

    def leftReleased(self, x, y):
        self.is_painting = False

    def rightReleased(self, x, y):
        self.is_painting = False

    def wheel(self, delta, mods=None):
        # Multiplicative scaling: each standard notch (delta=120) changes
        # the radius by ~10%, giving smooth steps at any brush size.
        factor = 1.1 ** (delta.y() / 120.0)
        self.brush_size = max(2, min(500, round(self.brush_size * factor)))
        self._resizeCursor()

    def apply(self):
        """SPACEBAR: commit the painted mask back to a blob and finish."""
        if self.working_mask is None:
            self.viewerplus.resetTools()
            return

        # Empty mask: delete the blob (edit) or cancel silently (creation).
        if not self.working_mask.any():
            if self.original_blob is not None:
                # Edit mode: all pixels removed → delete the blob.
                # No need to restore the fill; the blob is about to be removed.
                self._removeSceneItems()
                blob_to_delete     = self.original_blob
                self.original_blob = None
                self.working_mask  = None
                self.working_bbox  = None
                self.is_painting   = False
                self.viewerplus.project.updateCorrespondences("REMOVE", self.viewerplus.image, None, blob_to_delete, "")
                self.viewerplus.removeBlobs([blob_to_delete])
                self.viewerplus.saveUndo()
                self.log.emit("[TOOL][BRUSH] Region deleted (all pixels removed).")
            else:
                # Creation mode: nothing painted → cancel silently.
                self._cancelEditing()
            self.viewerplus.resetTools()
            return

        if self.original_blob is None:
            # --- CREATION MODE: commit a new blob ---
            new_blob = Blob(None, 0, 0, 0)
            try:
                new_blob.updateUsingMask(self.working_bbox, self.working_mask.astype(int))
            except Exception as e:
                self.log.emit(f"[TOOL][BRUSH] updateUsingMask failed: {e}")
                self.infoMessage.emit("Brush: failed to create region.")
                self._cancelEditing()
                self.viewerplus.resetTools()
                return

            new_blob.setId(self.viewerplus.annotations.getFreeId())
            new_blob.class_name = self.viewerplus.active_label or "Empty"
            self.blobInfo.emit(new_blob, "[TOOL][BRUSH][BLOB-CREATED]")
            self.log.emit("[TOOL][BRUSH] New region created.")

            # Clear state before addBlob so selectionChanged is a no-op.
            self._removeSceneItems()
            self.working_mask = None
            self.working_bbox = None
            self.is_painting  = False

            self.viewerplus.resetSelection()
            self.viewerplus.addBlob(new_blob, selected=True)
            self.viewerplus.project.updateCorrespondences("ADD", self.viewerplus.image, [new_blob], None, "")
            self.viewerplus.saveUndo()
            self.viewerplus.resetTools()
            return

        # --- EDIT MODE: rebuild existing blob ---
        new_blob = self.original_blob.copy()
        try:
            new_blob.updateUsingMask(self.working_bbox, self.working_mask.astype(int))
        except Exception as e:
            self.log.emit(f"[TOOL][BRUSH] updateUsingMask failed: {e}")
            self.infoMessage.emit("Brush: failed to rebuild region (result may be empty).")
            self._cancelEditing()
            self.viewerplus.resetTools()
            return

        self.blobInfo.emit(self.original_blob, "[TOOL][BRUSH][BLOB-BEFORE]")
        self.blobInfo.emit(new_blob,            "[TOOL][BRUSH][BLOB-AFTER]")
        self.log.emit("[TOOL][BRUSH] Applying changes.")

        # Restore the old blob's fill and remove the overlay BEFORE calling
        # updateBlob.  updateBlob emits selectionChanged (twice: once when
        # removing old_blob from selection, once when adding new_blob).  If
        # original_blob were still set at that point, _onSelectionChanged would
        # call _cancelEditing() mid-flight, touching the blob's gitem at an
        # unsafe moment.  Clearing state first makes _onSelectionChanged a no-op.
        self._restoreBlobFill()
        self._removeSceneItems()
        blob_to_update     = self.original_blob
        self.original_blob = None
        self.working_mask  = None
        self.working_bbox  = None
        self.is_painting   = False

        self.viewerplus.updateBlob(blob_to_update, new_blob, selected=True)
        self.viewerplus.saveUndo()

        self.log.emit("[TOOL][BRUSH] Done.")
        self.viewerplus.resetTools()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensureReady(self):
        """Return True if we have a valid working state (init if needed)."""
        n = len(self.viewerplus.selected_blobs)
        if n > 1:
            self.infoMessage.emit("Select a single region to edit, or deselect all to create a new one.")
            return False
        if n == 1:
            blob = self.viewerplus.selected_blobs[0]
            if self.original_blob is None or blob is not self.original_blob:
                self._initWorkingState(blob)
            return self.working_mask is not None
        # n == 0 → creation mode
        if self.working_mask is None:
            return self._initCreationState()
        return True

    def _tryInitFromSelection(self):
        if len(self.viewerplus.selected_blobs) == 1:
            self._initWorkingState(self.viewerplus.selected_blobs[0])

    def _initCreationState(self):
        """Set up an empty working_mask over the current viewport for creating a new blob."""
        self._cancelEditing()   # clean up any previous state

        rect  = self.viewerplus.viewportToScene()
        img_w = self.viewerplus.image.width  if self.viewerplus.image else 100_000
        img_h = self.viewerplus.image.height if self.viewerplus.image else 100_000

        left = max(0,     int(rect.left()))
        top  = max(0,     int(rect.top()))
        rgt  = min(img_w, int(rect.right()))
        bot  = min(img_h, int(rect.bottom()))
        w = rgt - left
        h = bot - top

        if w <= 0 or h <= 0:
            self.infoMessage.emit("Could not determine work area. Try panning the view first.")
            return False

        megapixels = (w * h) / 1_000_000.0
        if megapixels > 50.0:
            box = QMessageBox()
            box.setText(
                f"The work area is too large ({megapixels:.1f} MP).\n"
                "Zoom in to reduce the area and try again.")
            box.exec()
            return False

        self.working_bbox = [top, left, w, h]
        self.working_mask = np.zeros((h, w), dtype=np.uint8)
        # original_blob stays None → signals creation mode throughout

        # Dashed border so the user can see the editable area (same style as RITM).
        pen = QPen(Qt.DashLine)
        pen.setWidth(2)
        pen.setColor(Qt.white)
        pen.setCosmetic(True)
        self.work_area_item = self.viewerplus.scene.addRect(
            left, top, w, h, pen, QBrush(Qt.NoBrush))
        self.work_area_item.setZValue(3)

        self._updatePixmap()
        return True

    def _initWorkingState(self, blob):
        """Set up working_mask and pixmap overlay for *blob*."""
        self._cancelEditing()   # clean up any previous state

        img_w = self.viewerplus.image.width  if self.viewerplus.image else 100_000
        img_h = self.viewerplus.image.height if self.viewerplus.image else 100_000

        pad_y = max(self.MIN_PADDING, int(self.PAD_FRACTION * blob.bbox[3]))
        pad_x = max(self.MIN_PADDING, int(self.PAD_FRACTION * blob.bbox[2]))
        top  = max(0,     int(blob.bbox[0]) - pad_y)
        left = max(0,     int(blob.bbox[1]) - pad_x)
        bot  = min(img_h, int(blob.bbox[0]) + int(blob.bbox[3]) + pad_y)
        rgt  = min(img_w, int(blob.bbox[1]) + int(blob.bbox[2]) + pad_x)

        w = rgt - left
        h = bot - top
        self.working_bbox = [top, left, w, h]

        # Build working mask from the blob
        self.working_mask = np.zeros((h, w), dtype=np.uint8)
        blob_mask = blob.getMask()             # shape (blob_h, blob_w)
        bm_top  = int(blob.bbox[0])
        bm_left = int(blob.bbox[1])
        bm_h, bm_w = blob_mask.shape

        # Clamp paste region to working area
        dst_r0 = bm_top  - top
        dst_c0 = bm_left - left
        dst_r1 = dst_r0 + bm_h
        dst_c1 = dst_c0 + bm_w
        # Clip to valid range (should always be valid given the padding)
        dst_r0 = max(dst_r0, 0);  dst_r1 = min(dst_r1, h)
        dst_c0 = max(dst_c0, 0);  dst_c1 = min(dst_c1, w)
        src_r0 = dst_r0 - (bm_top  - top)
        src_c0 = dst_c0 - (bm_left - left)
        self.working_mask[dst_r0:dst_r1, dst_c0:dst_c1] = \
            blob_mask[src_r0:src_r0 + (dst_r1 - dst_r0),
                      src_c0:src_c0 + (dst_c1 - dst_c0)]

        self.original_blob = blob

        # Temporarily hide the blob fill so the pixmap is the only visual.
        if blob.qpath_gitem is not None:
            blob.qpath_gitem.setBrush(QBrush(Qt.NoBrush))

        # Create pixmap overlay and brush cursor
        self._updatePixmap()
        cx = left + w // 2
        cy = top  + h // 2
        self._createCursor(cx, cy)

    # ------------------------------------------------------------------
    # Painting
    # ------------------------------------------------------------------

    def _paintAt(self, x, y):
        """Apply circular brush at image coordinate (x, y)."""
        if self.working_mask is None:
            return
        top, left, w, h = self.working_bbox
        col = int(round(x)) - left
        row = int(round(y)) - top
        value = 1 if self.paint_mode == 'add' else 0
        cv2.circle(self.working_mask, (col, row), self.brush_size, value, -1)
        self._updatePixmap()

    # ------------------------------------------------------------------
    # Pixmap overlay
    # ------------------------------------------------------------------

    def _blobColor(self):
        blob = self.original_blob
        if blob is None:
            # Creation mode: use the active label's color.
            label_name = self.viewerplus.active_label
            if label_name:
                labels = self.viewerplus.project.labels
                if label_name in labels:
                    c = labels[label_name].fill
                    return (c[0], c[1], c[2])
            return (200, 200, 200)
        if blob.class_name == "Empty":
            return (200, 200, 200)
        labels = self.viewerplus.project.labels
        if blob.class_name in labels:
            c = labels[blob.class_name].fill
            return (c[0], c[1], c[2])
        return (255, 0, 0)

    def _updatePixmap(self):
        h, w = self.working_mask.shape
        r, g, b = self._blobColor()

        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        filled = self.working_mask > 0
        rgba[filled, 0] = r
        rgba[filled, 1] = g
        rgba[filled, 2] = b
        rgba[filled, 3] = 210

        # Keep bytes object alive so QImage doesn't read freed memory.
        self._rgba_buf   = rgba.tobytes()
        qimg   = QImage(self._rgba_buf, w, h, 4 * w, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimg)

        top  = self.working_bbox[0]
        left = self.working_bbox[1]

        if self.pixmap_item is None:
            self.pixmap_item = self.viewerplus.scene.addPixmap(pixmap)
            self.pixmap_item.setPos(left, top)
            self.pixmap_item.setZValue(3)
        else:
            self.pixmap_item.setPixmap(pixmap)
        # Always sync to the current transparency so the overlay follows the slider.
        self.pixmap_item.setOpacity(self.viewerplus.transparency_value)

    # ------------------------------------------------------------------
    # Brush-size cursor
    # ------------------------------------------------------------------

    def _createCursor(self, x, y):
        r   = self.brush_size
        pen = QPen(QColor(255, 255, 255, 220), 2)
        pen.setCosmetic(True)
        self.cursor_item = self.viewerplus.scene.addEllipse(
            x - r, y - r, 2 * r, 2 * r, pen)
        self.cursor_item.setZValue(10)

    def _moveCursor(self, x, y):
        if self.cursor_item is None:
            # Always create the cursor on first hover — gives brush-size preview
            # in all modes (creation, edit, or idle) as soon as the mouse enters.
            self._createCursor(x, y)
            return
        r = self.brush_size
        self.cursor_item.setRect(QRectF(x - r, y - r, 2 * r, 2 * r))

    def _resizeCursor(self):
        if self.cursor_item is None:
            return
        rect = self.cursor_item.rect()
        cx   = rect.center().x()
        cy   = rect.center().y()
        r    = self.brush_size
        self.cursor_item.setRect(QRectF(cx - r, cy - r, 2 * r, 2 * r))

    # ------------------------------------------------------------------
    # Cleanup helpers
    # ------------------------------------------------------------------

    def _removeSceneItems(self):
        if self.pixmap_item is not None:
            self.viewerplus.scene.removeItem(self.pixmap_item)
            self.pixmap_item = None
        if self.cursor_item is not None:
            self.viewerplus.scene.removeItem(self.cursor_item)
            self.cursor_item = None
        if self.work_area_item is not None:
            self.viewerplus.scene.removeItem(self.work_area_item)
            self.work_area_item = None
        self._rgba_buf = None

    def _restoreBlobFill(self):
        """Restore the original blob's fill brush (undone by the overlay)."""
        blob = self.original_blob
        if blob is not None and blob.qpath_gitem is not None:
            brush = self.viewerplus.project.classBrushFromName(blob)
            blob.qpath_gitem.setBrush(brush)

    def _cancelEditing(self):
        """Discard all changes and restore the original blob."""
        self._restoreBlobFill()
        self._removeSceneItems()
        self.original_blob = None
        self.working_mask  = None
        self.working_bbox  = None
        self.is_painting   = False
