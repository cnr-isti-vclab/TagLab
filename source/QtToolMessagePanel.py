# TagLab
# A semi-automatic segmentation tool
#
# Copyright(C) 2019
# Visual Computing Lab
# ISTI - Italian National Research Council
# All rights reserved.

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy


class QtToolMessagePanel(QWidget):
    """
    Integrated message panel for displaying tool instructions and status messages.
    Designed to be embedded in the QtImageViewerPlus layout.
    """

    def __init__(self, parent=None):
        super(QtToolMessagePanel, self).__init__(parent)

        # Widget styling
        self.setStyleSheet("background-color: rgba(40, 40, 40, 200); color: white; border-radius: 5px;")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        # Position state - starts at bottom-left
        self.position = 'bottom-left'  # or 'top-left'
        self.margin = 10

        # Message label
        self.message_label = QLabel()
        self.message_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.message_label.setWordWrap(True)
        self.message_label.setTextFormat(Qt.RichText)
        self.message_label.setStyleSheet("padding: 10px;")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.message_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Auto-hide timer
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.clear)

        # Initially hidden
        self.hide()

    def showMessage(self, text, status='info', timeout=None):
        """
        Display a message in the panel.
        
        Args:
            text: HTML-formatted message text
            status: Message type ('info', 'warning', 'error', 'progress') - for future styling
            timeout: Auto-hide after this many milliseconds (None = no auto-hide)
        """
        if not text:
            self.clear()
            return

        self.message_label.setText(text)
        self.show()
        self.raise_()

        # Set up auto-hide if timeout specified
        if timeout is not None and timeout > 0:
            self.auto_hide_timer.start(timeout)
        else:
            self.auto_hide_timer.stop()

    def updateMessage(self, text):
        """
        Update the current message text without changing visibility.
        Useful for progress updates.
        """
        if text:
            self.message_label.setText(text)

    def clear(self):
        """
        Clear the message and hide the panel.
        """
        self.auto_hide_timer.stop()
        self.message_label.clear()
        self.hide()

    def setStatus(self, status):
        """
        Change the visual style based on message type.
        
        Args:
            status: 'info', 'warning', 'error', or 'progress'
        """
        # Color coding for different message types
        colors = {
            'info': 'rgba(40, 40, 40, 200)',
            'warning': 'rgba(200, 150, 0, 200)',
            'error': 'rgba(180, 0, 0, 200)',
            'progress': 'rgba(0, 100, 180, 200)'
        }
        
        bg_color = colors.get(status, colors['info'])
        self.setStyleSheet(f"background-color: {bg_color}; color: white; border-radius: 5px;")

    def enterEvent(self, event):
        """Toggle panel position when mouse enters."""
        if self.position == 'top-left':
            self.position = 'bottom-left'
        else:
            self.position = 'top-left'
        self.updatePosition()
        super(QtToolMessagePanel, self).enterEvent(event)

    def updatePosition(self):
        """Update panel position based on current state."""
        if not self.isVisible() or not self.parent():
            return
        
        viewport = self.parent().viewport()
        if not viewport:
            return
            
        max_width = viewport.width() - 2 * self.margin
        self.setMaximumWidth(max_width)
        self.adjustSize()
        
        if self.position == 'top-left':
            self.move(self.margin, self.margin)
        else:  # bottom-left
            y_pos = viewport.height() - self.height() - self.margin
            self.move(self.margin, y_pos)
        
        self.raise_()
