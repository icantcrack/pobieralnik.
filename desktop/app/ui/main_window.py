"""Okno główne: 3 kolumny (nav 72 px | kolumna robocza | biblioteka/kolejka)."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout, QMainWindow, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from ..core.settings import Settings, set_language, tr
from .theme import qss
from .download_page import DownloadPage
from .library_page import LibraryPage, MIME_TRACK
from .cd_page import CdPage
from .settings_page import SettingsPage

NAV_WIDTH = 72


def app_icon() -> QIcon:
    """Ikona aplikacji — działa w dev i w buildzie PyInstaller."""
    if getattr(sys, "frozen", False):
        p = Path(sys._MEIPASS) / "assets" / "icon.png"  # noqa: SLF001
    else:
        p = Path(__file__).resolve().parents[2] / "assets" / "icon.png"
    return QIcon(str(p)) if p.exists() else QIcon()


class NavDropButton(QToolButton):
    """Przycisk nawigacji przyjmujący upuszczone karty utworów (na płytę CD)."""
    track_dropped = Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_TRACK):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_TRACK):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(MIME_TRACK):
            track_id = int(bytes(event.mimeData().data(MIME_TRACK)).decode())
            self.track_dropped.emit(track_id)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        set_language(settings.language)
        self.setWindowTitle(tr("app_title"))
        self.setWindowIcon(app_icon())
        self.resize(1280, 800)
        self.apply_theme()

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Lewy pasek nawigacji 72 px ---
        nav = QWidget(objectName="navBar")
        nav.setFixedWidth(NAV_WIDTH)
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 12, 0, 12)
        nav_layout.setSpacing(2)

        self.stack = QStackedWidget()
        self.pages = [
            DownloadPage(settings),
            LibraryPage(settings),
            CdPage(settings),
            SettingsPage(settings, on_changed=self.apply_theme),
        ]
        keys = ["nav_download", "nav_library", "nav_cd", "nav_settings"]
        icons = ["⬇", "🎵", "💿", "⚙"]
        self.nav_buttons: list[QToolButton] = []

        for i, (page, key, icon_text) in enumerate(zip(self.pages, keys, icons)):
            self.stack.addWidget(page)
            if i == 2:  # Płyta CD — przyjmuje przeciągane utwory
                btn = NavDropButton(objectName="navBtn", text=f"{icon_text}\n{tr(key)}")
                btn.track_dropped.connect(self._on_track_dropped_on_cd)
                btn.setToolTip("Upuść tutaj utwór z biblioteki, aby dodać go na płytę")
            else:
                btn = QToolButton(objectName="navBtn", text=f"{icon_text}\n{tr(key)}")
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QSize(24, 24))
            btn.clicked.connect(lambda _=False, idx=i: self._switch(idx))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        nav_layout.addStretch(1)

        layout.addWidget(nav)
        layout.addWidget(self.stack, stretch=3)

        # --- integracja: biblioteka → płyta CD ---
        library: LibraryPage = self.pages[1]
        cd_page: CdPage = self.pages[2]
        library.add_tracks_to_cd.connect(self._add_tracks_to_cd)

        self._switch(0)

    def _add_tracks_to_cd(self, tracks) -> None:
        cd_page: CdPage = self.pages[2]
        for t in tracks:
            cd_page.add_track(t)
        self._switch(2)  # pokaż płytę z sumą czasu/miejsca

    def _on_track_dropped_on_cd(self, track_id: int) -> None:
        library: LibraryPage = self.pages[1]
        track = library.get_track(track_id)
        if track:
            self.pages[2].add_track(track)
            self._switch(2)

    def _switch(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == 1:
            self.pages[1].refresh()  # biblioteka zawsze świeża po wejściu
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def apply_theme(self) -> None:
        self.setStyleSheet(qss(self.settings.theme))
