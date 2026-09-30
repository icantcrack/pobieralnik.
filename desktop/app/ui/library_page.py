"""Ekran 2 — Biblioteka: siatka okładek 3×N, wyszukiwarka, filtry, multi-select,
odtwarzanie (głośność, zapętlenie), eksport/przenoszenie, drag&drop na Płytę CD."""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QMimeData, QUrl
from PySide6.QtGui import QDrag
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QSlider, QStyle,
    QVBoxLayout, QWidget,
)

from ..core.library import Library, Track
from ..core.settings import Settings, tr

COLUMNS = 3
MIME_TRACK = "application/x-pobieralnik-track"


def fmt_time(ms: int) -> str:
    s = max(0, ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


class TrackCard(QFrame):
    """Karta utworu: okładka 160×160 + tytuł/wykonawca + PLAY + dodaj do płyty.
    Kartę można przeciągnąć na zakładkę „Płyta CD"."""
    add_to_cd = Signal(object)

    def __init__(self, track: Track):
        super().__init__()
        self.track = track
        self._drag_start = None
        self.setProperty("class", "card")
        self.setFixedSize(196, 288)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Przeciągnij na zakładkę „Płyta CD” lub użyj przycisku CD")

        style = self.style()
        self.icon_play = style.standardIcon(QStyle.SP_MediaPlay)
        self.icon_pause = style.standardIcon(QStyle.SP_MediaPause)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        self.checkbox = QCheckBox()
        layout.addWidget(self.checkbox)

        cover = QLabel("🎵")
        cover.setFixedSize(160, 160)
        cover.setAlignment(Qt.AlignCenter)
        cover.setStyleSheet("border-radius: 12px; background: #262135; font-size: 40px;")
        layout.addWidget(cover, alignment=Qt.AlignHCenter)

        title = QLabel(track.title)
        title.setWordWrap(True)
        title.setMaximumHeight(38)
        title.setStyleSheet("font-weight: 600;")
        artist = QLabel(track.artist or "—")
        artist.setProperty("class", "dim")
        layout.addWidget(title)
        layout.addWidget(artist)

        actions = QHBoxLayout()
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.icon_play)
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setToolTip("Odtwórz / Pauza")
        self.play_btn.setStyleSheet(
            "QPushButton { background: #8B5CF6; border-radius: 18px; }"
            "QPushButton:hover { background: #9D74F8; }"
        )
        cd_btn = QPushButton()
        cd_btn.setIcon(style.standardIcon(QStyle.SP_DriveCDIcon))
        cd_btn.setFixedSize(36, 36)
        cd_btn.setToolTip("Dodaj do płyty CD")
        cd_btn.clicked.connect(lambda: self.add_to_cd.emit(self.track))
        actions.addWidget(self.play_btn)
        actions.addStretch(1)
        actions.addWidget(cd_btn)
        layout.addLayout(actions)

    # --- drag & drop ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._drag_start is not None and event.buttons() & Qt.LeftButton
                and (event.position().toPoint() - self._drag_start).manhattanLength() > 12):
            self._drag_start = None
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData(MIME_TRACK, str(self.track.id).encode())
            mime.setText(self.track.title)
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)
            return
        super().mouseMoveEvent(event)


class LibraryPage(QWidget):
    add_tracks_to_cd = Signal(list)  # list[Track]

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.library = Library()
        self.cards: list[TrackCard] = []

        # --- odtwarzacz ---
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.audio_out.setVolume(0.8)
        self.playing_track_id: int | None = None
        self.loop_enabled = False
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_media_status)

        style = self.style()
        self.icon_play = style.standardIcon(QStyle.SP_MediaPlay)
        self.icon_pause = style.standardIcon(QStyle.SP_MediaPause)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # --- wyszukiwarka + filtry ---
        bar = QHBoxLayout()
        self.search = QLineEdit(placeholderText="🔍  Szukaj…")
        self.search.textChanged.connect(self.refresh)
        self.sort_box = QComboBox()
        self.sort_box.addItems([
            "Data pobrania ↓", "Data pobrania ↑", "Bitrate ↓", "Bitrate ↑", "Alfabetycznie",
        ])
        self.sort_box.currentIndexChanged.connect(self.refresh)
        bar.addWidget(self.search, stretch=1)
        bar.addWidget(self.sort_box)
        layout.addLayout(bar)

        # --- siatka ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(16)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.grid_host)
        layout.addWidget(scroll, stretch=1)

        # --- pasek odtwarzania ---
        self.player_bar = QFrame()
        self.player_bar.setProperty("class", "card")
        self.player_bar.setVisible(False)
        pb = QHBoxLayout(self.player_bar)
        pb.setContentsMargins(16, 8, 16, 8)
        pb.setSpacing(10)

        self.bar_play_btn = QPushButton()
        self.bar_play_btn.setIcon(self.icon_pause)
        self.bar_play_btn.setFixedSize(36, 36)
        self.bar_play_btn.clicked.connect(self.toggle_current)

        self.bar_title = QLabel("—")
        self.bar_title.setStyleSheet("font-weight: 600;")

        self.bar_slider = QSlider(Qt.Horizontal)
        self.bar_slider.sliderMoved.connect(self.player.setPosition)

        self.bar_time = QLabel("0:00 / 0:00")
        self.bar_time.setProperty("class", "dim")

        # zapętlenie
        self.loop_btn = QPushButton()
        self.loop_btn.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        self.loop_btn.setFixedSize(36, 36)
        self.loop_btn.setCheckable(True)
        self.loop_btn.setToolTip("Odtwarzaj w pętli")
        self.loop_btn.toggled.connect(self._toggle_loop)

        # głośność
        vol_icon = QLabel()
        vol_icon.setPixmap(style.standardIcon(QStyle.SP_MediaVolume).pixmap(20, 20))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(110)
        self.volume_slider.setToolTip("Głośność")
        self.volume_slider.valueChanged.connect(
            lambda v: self.audio_out.setVolume(v / 100))

        bar_stop = QPushButton()
        bar_stop.setIcon(style.standardIcon(QStyle.SP_MediaStop))
        bar_stop.setFixedSize(36, 36)
        bar_stop.setToolTip("Zatrzymaj")
        bar_stop.clicked.connect(self.stop_playback)

        pb.addWidget(self.bar_play_btn)
        pb.addWidget(self.bar_title, stretch=2)
        pb.addWidget(self.bar_slider, stretch=3)
        pb.addWidget(self.bar_time)
        pb.addWidget(self.loop_btn)
        pb.addWidget(vol_icon)
        pb.addWidget(self.volume_slider)
        pb.addWidget(bar_stop)
        layout.addWidget(self.player_bar)

        # --- pasek akcji multi-select ---
        self.action_bar = QFrame()
        self.action_bar.setProperty("class", "card")
        ab = QHBoxLayout(self.action_bar)
        ab.setContentsMargins(16, 8, 16, 8)
        self.sel_label = QLabel("0 zaznaczonych")
        ab.addWidget(self.sel_label)
        ab.addStretch(1)
        self.export_btn = QPushButton("Eksportuj")
        self.export_btn.clicked.connect(self.export_selected)
        self.move_btn = QPushButton("Przenieś do folderu")
        self.move_btn.clicked.connect(self.move_selected)
        self.add_cd_btn = QPushButton("Dodaj do płyty")
        self.add_cd_btn.clicked.connect(self._emit_selected_to_cd)
        for b in (self.export_btn, self.move_btn, self.add_cd_btn):
            ab.addWidget(b)
        layout.addWidget(self.action_bar)

        self.refresh()

    # --- biblioteka ---
    def _order_clause(self) -> str:
        return [
            "downloaded_at DESC", "downloaded_at ASC",
            "bitrate DESC", "bitrate ASC", "title COLLATE NOCASE ASC",
        ][self.sort_box.currentIndex()]

    def refresh(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()
        tracks = self.library.search(self.search.text(), self._order_clause())
        if not tracks:
            empty = QLabel("Biblioteka jest pusta — pobierz pierwszy utwór w zakładce Pobieranie 🎵")
            empty.setProperty("class", "dim")
            empty.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(empty, 0, 0, 1, COLUMNS)
        for i, track in enumerate(tracks):
            card = TrackCard(track)
            card.checkbox.stateChanged.connect(self._update_selection)
            card.add_to_cd.connect(lambda t: self.add_tracks_to_cd.emit([t]))
            card.play_btn.clicked.connect(lambda _=False, t=track: self.toggle_play(t))
            self.grid.addWidget(card, i // COLUMNS + 1, i % COLUMNS)
            self.cards.append(card)
        self._update_selection()
        self._refresh_play_icons()

    def _update_selection(self) -> None:
        n = sum(1 for c in self.cards if c.checkbox.isChecked())
        self.sel_label.setText(f"{n} zaznaczonych")

    def selected_tracks(self) -> list[Track]:
        return [c.track for c in self.cards if c.checkbox.isChecked()]

    def get_track(self, track_id: int) -> Track | None:
        for t in self.library.search(""):
            if t.id == track_id:
                return t
        return None

    # --- eksport / przenoszenie ---
    def export_selected(self) -> None:
        """Kopiuje zaznaczone MP3 do wybranego folderu (oryginały zostają)."""
        tracks = self.selected_tracks()
        if not tracks:
            self._info("Zaznacz najpierw utwory checkboxami na kartach.")
            return
        dest = QFileDialog.getExistingDirectory(self, "Eksportuj do folderu")
        if not dest:
            return
        ok = 0
        for t in tracks:
            try:
                shutil.copy2(t.path, Path(dest) / Path(t.path).name)
                ok += 1
            except OSError:
                pass
        self._info(f"Wyeksportowano {ok}/{len(tracks)} utworów do:\n{dest}")

    def move_selected(self) -> None:
        """Przenosi zaznaczone MP3 do wybranego folderu i aktualizuje bibliotekę."""
        tracks = self.selected_tracks()
        if not tracks:
            self._info("Zaznacz najpierw utwory checkboxami na kartach.")
            return
        dest = QFileDialog.getExistingDirectory(self, "Przenieś do folderu")
        if not dest:
            return
        ok = 0
        for t in tracks:
            try:
                new_path = str(Path(dest) / Path(t.path).name)
                shutil.move(t.path, new_path)
                self.library.update_path(t.id, new_path)
                ok += 1
            except OSError:
                pass
        self.refresh()
        self._info(f"Przeniesiono {ok}/{len(tracks)} utworów do:\n{dest}")

    def _info(self, text: str) -> None:
        QMessageBox.information(self, tr("app_title"), text)

    def _emit_selected_to_cd(self) -> None:
        tracks = self.selected_tracks()
        if not tracks:
            self._info("Zaznacz najpierw utwory checkboxami na kartach.")
            return
        self.add_tracks_to_cd.emit(tracks)

    # --- odtwarzanie ---
    def toggle_play(self, track: Track) -> None:
        if self.playing_track_id == track.id and \
                self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.playing_track_id == track.id:
            self.player.play()
        else:
            self.player.setSource(QUrl.fromLocalFile(track.path))
            self.playing_track_id = track.id
            self.bar_title.setText(f"{track.artist} — {track.title}")
            self.player_bar.setVisible(True)
            self.player.play()
        self._refresh_play_icons()

    def toggle_current(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop_playback(self) -> None:
        self.player.stop()
        self.playing_track_id = None
        self.player_bar.setVisible(False)
        self._refresh_play_icons()

    def _toggle_loop(self, checked: bool) -> None:
        self.loop_enabled = checked
        self.loop_btn.setStyleSheet(
            "QPushButton { background: #8B5CF6; border-radius: 10px; }" if checked else "")

    def _refresh_play_icons(self) -> None:
        playing = self.player.playbackState() == QMediaPlayer.PlayingState
        self.bar_play_btn.setIcon(self.icon_pause if playing else self.icon_play)
        for card in self.cards:
            is_current = card.track.id == self.playing_track_id
            card.play_btn.setIcon(card.icon_pause if (is_current and playing)
                                  else card.icon_play)
            card.setStyleSheet("border: 1px solid #8B5CF6; border-radius: 16px;"
                               if is_current else "")

    def _on_position(self, pos: int) -> None:
        if not self.bar_slider.isSliderDown():
            self.bar_slider.setValue(pos)
        self.bar_time.setText(f"{fmt_time(pos)} / {fmt_time(self.player.duration())}")

    def _on_duration(self, dur: int) -> None:
        self.bar_slider.setRange(0, dur)

    def _on_state(self, state) -> None:
        self._refresh_play_icons()

    def _on_media_status(self, status) -> None:
        if status == QMediaPlayer.EndOfMedia:
            if self.loop_enabled and self.playing_track_id is not None:
                self.player.setPosition(0)
                self.player.play()
            else:
                self.stop_playback()
