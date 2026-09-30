"""Ekran 3 — Przygotuj płytę CD: wizualizacja łuku, lista, limity, wypalanie."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget,
    QProgressBar, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from ..core.cd_manager import CdMode, CdProject, format_over_delta, format_used
from ..core.library import Track
from ..core.settings import Settings, tr
from .theme import PALETTE


class CdWidget(QWidget):
    """Rysowana płyta CD z łukiem zajętego miejsca.

    Fioletowy łuk = Audio CD (minuty), miętowy = MP3 CD (MB).
    """

    def __init__(self):
        super().__init__()
        self.setMinimumSize(280, 280)
        self.fraction = 0.0
        self.mode = CdMode.AUDIO_CD
        self.theme = "dark"

    def set_status(self, fraction: float, mode: CdMode, theme: str = "dark") -> None:
        self.fraction = min(fraction, 1.0)
        self.over = fraction > 1.0
        self.mode = mode
        self.theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        p = PALETTE.get(self.theme, PALETTE["dark"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        side = min(self.width(), self.height()) - 24
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

        # korpus płyty — wyraźnie jaśniejszy od tła, z rowkami
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(p["surface_alt"]))
        painter.drawEllipse(rect)
        painter.setBrush(Qt.NoBrush)
        for inset in (28, 52, 76):
            painter.setPen(QPen(QColor(p["line"]), 1))
            painter.drawEllipse(rect.adjusted(inset, inset, -inset, -inset))
        hole = side * 0.22
        hole_rect = QRectF(rect.center().x() - hole / 2, rect.center().y() - hole / 2,
                           hole, hole)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(p["bg"]))
        painter.drawEllipse(hole_rect)

        # pełny okrąg-tor (tło łuku) — zawsze widoczny, też przy 0%
        accent = p["accent"] if self.mode == CdMode.AUDIO_CD else p["accent_mint"]
        if getattr(self, "over", False):
            accent = p["danger"]
        arc_rect = rect.adjusted(14, 14, -14, -14)
        track_pen = QPen(QColor(p["line"]))
        track_pen.setWidth(14)
        painter.setPen(track_pen)
        painter.drawEllipse(arc_rect)

        # łuk zajętego miejsca (pełne koło = limit)
        if self.fraction > 0:
            pen = QPen(QColor(accent))
            pen.setWidth(14)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(arc_rect, 90 * 16, int(-self.fraction * 360 * 16))

        # podpis procentowy
        painter.setPen(QColor(p["text"]))
        font = painter.font()
        font.setPointSize(16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{int(self.fraction * 100)}%")
        painter.end()


class BurnDialog(QDialog):
    """Dialog wypalania: napęd, prędkość, pasek postępu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("burn"))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Napęd:"))
        self.drive_box = QComboBox()
        layout.addWidget(self.drive_box)
        layout.addWidget(QLabel("Prędkość wypalania:"))
        self.speed_box = QComboBox()
        self.speed_box.addItems(["8x", "16x", "24x", "32x", "48x"])
        self.speed_box.setCurrentIndex(1)
        layout.addWidget(self.speed_box)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def refresh_drives(self) -> None:
        from ..core.burner import list_drives
        try:
            drives = list_drives()
        except Exception:
            drives = []
        self.drive_box.clear()
        self.drive_box.addItems(drives or ["(brak wykrytych napędów)"])


class CdPage(QWidget):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.project = CdProject()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(28)

        # --- lewo: wizualizacja płyty ---
        left = QVBoxLayout()
        left.addStretch(1)
        self.cd_widget = CdWidget()
        self.cd_widget.setMinimumSize(360, 360)
        left.addWidget(self.cd_widget, stretch=4, alignment=Qt.AlignCenter)
        self.audio_radio = QRadioButton(tr("audio_cd"))
        self.mp3_radio = QRadioButton(tr("mp3_cd"))
        self.audio_radio.setChecked(True)
        self.audio_radio.toggled.connect(self._mode_changed)
        left.addWidget(self.audio_radio)
        left.addWidget(self.mp3_radio)
        left.addStretch(1)
        layout.addLayout(left, stretch=2)

        # --- prawo: lista + podsumowanie + wypalanie ---
        right = QVBoxLayout()
        cap = QLabel("UTWORY NA PŁYCIE")
        cap.setProperty("class", "caption")
        right.addWidget(cap)
        self.track_list = QListWidget()
        right.addWidget(self.track_list, stretch=1)

        self.summary = QLabel("0:00 min / 80:00")
        self.summary.setProperty("class", "dim")
        right.addWidget(self.summary)

        self.warning = QLabel("")
        self.warning.setProperty("class", "warning")
        self.warning.setVisible(False)
        right.addWidget(self.warning)

        self.burn_btn = QPushButton(tr("burn"), objectName="burnBtn")
        self.burn_btn.clicked.connect(self._burn)
        right.addWidget(self.burn_btn)
        layout.addLayout(right, stretch=3)

        self._refresh()

    # --- API dla innych ekranów ---
    def add_track(self, track: Track) -> None:
        self.project.add(track)
        self._refresh()

    def _mode_changed(self) -> None:
        self.project.mode = CdMode.AUDIO_CD if self.audio_radio.isChecked() else CdMode.MP3_CD
        self._refresh()

    def _refresh(self) -> None:
        self.track_list.clear()
        for t in self.project.tracks:
            self.track_list.addItem(f"{t.artist} — {t.title}")
        s = self.project.status()
        limit_txt = "80:00" if self.project.mode == CdMode.AUDIO_CD else "700 MB"
        self.summary.setText(f"{format_used(self.project.mode, s.used)} / {limit_txt}")
        self.cd_widget.set_status(s.fraction, self.project.mode, self.settings.theme)

        if s.over_limit:
            delta = format_over_delta(self.project.mode, s.over_delta)
            self.warning.setText(tr("over_limit", delta=delta))
            self.warning.setVisible(True)
        else:
            self.warning.setVisible(False)

        self.burn_btn.setEnabled(self.project.can_burn())

    def _burn(self) -> None:
        dlg = BurnDialog(self)
        dlg.refresh_drives()
        if dlg.exec() == QDialog.Accepted:
            # Integracja: burner.burn(project, drive, speed, on_progress=dlg.progress...)
            dlg.progress.setValue(100)
