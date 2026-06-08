# TagLab
# A semi-automatic segmentation tool
#
# Copyright(C) 2019
# Visual Computing Lab
# ISTI - Italian National Research Council
# All rights reserved.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License (http://www.gnu.org/licenses/gpl.txt)
# for more details.

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QRadioButton, QCheckBox, QSpinBox, QComboBox,
    QLabel, QPushButton, QFrame
)
from PyQt5.QtCore import Qt


class QtExportRegionsWidget(QDialog):
    """
    Dialog for exporting selected annotation regions as individual cropped PNG images.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Selected Regions as Images")
        self.setModal(True)
        self.setMinimumWidth(380)
        self._setupUI()

    def _setupUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # ── Transparency ──────────────────────────────────────────────────
        self.chkTransparent = QCheckBox("Transparent background (PNG alpha channel)")
        self.chkTransparent.setChecked(True)
        self.chkTransparent.stateChanged.connect(self._onTransparencyChanged)
        layout.addWidget(self.chkTransparent)

        # ── Background color (used even with transparency for RGB data) ───
        self.bgGroup = QGroupBox("Background Color")
        bg_layout = QHBoxLayout()
        self.radioBlack = QRadioButton("Black")
        self.radioWhite = QRadioButton("White")
        self.radioBlack.setChecked(True)
        bg_layout.addWidget(self.radioBlack)
        bg_layout.addWidget(self.radioWhite)
        bg_layout.addStretch()
        self.bgGroup.setLayout(bg_layout)
        layout.addWidget(self.bgGroup)

        # ── Separator ─────────────────────────────────────────────────────
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep1)

        # ── Resize ────────────────────────────────────────────────────────
        resize_layout = QHBoxLayout()
        resize_label = QLabel("Resize output:")
        self.comboSize = QComboBox()
        self.comboSize.addItems(["Native", "Native (squared)", "1024x1024", "512x512", "256x256", "128x128"])
        resize_layout.addWidget(resize_label)
        resize_layout.addStretch()
        resize_layout.addWidget(self.comboSize)
        layout.addLayout(resize_layout)

        # ── Padding ───────────────────────────────────────────────────────
        padding_layout = QHBoxLayout()
        padding_label = QLabel("Final padding around region (pixels):")
        self.spinPadding = QSpinBox()
        self.spinPadding.setMinimum(0)
        self.spinPadding.setMaximum(2000)
        self.spinPadding.setValue(0)
        self.spinPadding.setSuffix(" px")
        padding_layout.addWidget(padding_label)
        padding_layout.addStretch()
        padding_layout.addWidget(self.spinPadding)
        layout.addLayout(padding_layout)

        # ── Separator ─────────────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep2)

        # ── WhatsApp sticker ──────────────────────────────────────────────
        self.chkWhatsapp = QCheckBox("Export as WhatsApp Sticker")
        self.chkWhatsapp.setChecked(False)
        self.chkWhatsapp.stateChanged.connect(self._onWhatsappChanged)
        layout.addWidget(self.chkWhatsapp)

        self.lblWhatsappInfo = QLabel(
            "  512×512 px, transparent background, PNG format.\n"
            "  Region is centred; keep file size under 500 KB."
        )
        self.lblWhatsappInfo.setStyleSheet("color: rgb(160,160,160); font-size: 11px;")
        self.lblWhatsappInfo.setVisible(False)
        layout.addWidget(self.lblWhatsappInfo)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self.btnExport = QPushButton("Choose Folder && Export")
        self.btnCancel = QPushButton("Cancel")
        self.btnExport.clicked.connect(self.accept)
        self.btnCancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btnExport)
        btn_layout.addWidget(self.btnCancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # ── Slots ──────────────────────────────────────────────────────────────

    def _onTransparencyChanged(self, state):
        # Keep background controls enabled even with alpha export.
        _ = state

    def _onWhatsappChanged(self, state):
        is_whatsapp = (state == Qt.Checked)
        self.lblWhatsappInfo.setVisible(is_whatsapp)
        if is_whatsapp:
            # Stickers must be transparent PNG at 512×512
            self.chkTransparent.setChecked(True)
            self.chkTransparent.setEnabled(False)
            idx = self.comboSize.findText("512x512")
            self.comboSize.setCurrentIndex(idx)
            self.comboSize.setEnabled(False)
        else:
            self.chkTransparent.setEnabled(True)
            self.comboSize.setEnabled(True)

    # ── Public API ─────────────────────────────────────────────────────────

    def getOptions(self):
        """Return a dict with all chosen export options."""
        size_text = self.comboSize.currentText()
        if size_text == "Native":
            target_size = None
            native_square = False
        elif size_text == "Native (squared)":
            target_size = None
            native_square = True
        else:
            target_size = int(size_text.split("x")[0])   # 1024 or 512
            native_square = False

        return {
            "transparent": self.chkTransparent.isChecked(),
            "background":  "white" if self.radioWhite.isChecked() else "black",
            "target_size": target_size,              # None = native
            "native_square": native_square,
            "padding":     self.spinPadding.value(),
            "whatsapp":    self.chkWhatsapp.isChecked(),
        }
