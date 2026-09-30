"""Ekran 1 — Pobieranie: pole URL, podgląd, jakość, folder, kolejka z przyciskami."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from ..core.downloader import DownloadTask, QueueManager, TaskState, classify_error
from ..core.metadata import VideoMeta, fetch_metadata, format_duration
from ..core.settings import Settings, tr
from ..core.library import Library

BITRATES = [128, 192, 256, 320]


class _MetaWorker(QThread):
    """Pobiera metadane bez blokowania UI."""
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, url: str, playlist: bool, cookies_browser: str = ""):
        super().__init__()
        self.url, self.playlist, self.cookies = url, playlist, cookies_browser

    def run(self):
        try:
            self.done.emit(fetch_metadata(self.url, self.playlist, self.cookies))
        except Exception as exc:
            self.failed.emit(str(exc))


class _EventBridge(QObject):
    """Most: callbacki wątków core → sygnały Qt (bezpieczne dla UI)."""
    event = Signal(object, str)


class QueueRow(QWidget):
    """Wiersz kolejki: okładka 40×40, tytuł, pasek postępu, przyciski."""

    def __init__(self, task: DownloadTask, page: "DownloadPage"):
        super().__init__()
        self.task = task
        self.page = page

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(10)

        cover = QLabel("🎵")
        cover.setFixedSize(40, 40)
        cover.setAlignment(Qt.AlignCenter)
        cover.setStyleSheet("border-radius: 8px; background: #262135; font-size: 18px;")
        layout.addWidget(cover)

        mid = QVBoxLayout()
        mid.setSpacing(4)
        title = task.meta.title if task.meta else task.url
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: 600;")
        self.progress = QProgressBar()
        self.progress.setFixedHeight(14)
        self.progress.setValue(0)
        mid.addWidget(self.title_lbl)
        mid.addWidget(self.progress)
        layout.addLayout(mid, stretch=1)

        self.info_lbl = QLabel("0% · 0.0 MB/s")
        self.info_lbl.setProperty("class", "dim")
        self.info_lbl.setFixedWidth(200)
        layout.addWidget(self.info_lbl)

        from PySide6.QtWidgets import QStyle
        style = self.style()

        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(style.standardIcon(QStyle.SP_MediaPause))
        self._icon_pause = style.standardIcon(QStyle.SP_MediaPause)
        self._icon_play = style.standardIcon(QStyle.SP_MediaPlay)
        self.pause_btn.setFixedSize(34, 34)
        self.pause_btn.setToolTip("Pauza / Wznów")
        self.pause_btn.clicked.connect(self._toggle_pause)

        self.cancel_btn = QPushButton()
        self.cancel_btn.setIcon(style.standardIcon(QStyle.SP_BrowserStop))
        self.cancel_btn.setFixedSize(34, 34)
        self.cancel_btn.setToolTip("Anuluj pobieranie")
        self.cancel_btn.clicked.connect(self._cancel)

        self.folder_btn = QPushButton()
        self.folder_btn.setIcon(style.standardIcon(QStyle.SP_DirOpenIcon))
        self.folder_btn.setFixedSize(34, 34)
        self.folder_btn.setToolTip("Otwórz folder")
        self.folder_btn.setEnabled(False)
        self.folder_btn.clicked.connect(self._open_folder)

        self.remove_btn = QPushButton()
        self.remove_btn.setIcon(style.standardIcon(QStyle.SP_TrashIcon))
        self.remove_btn.setFixedSize(34, 34)
        self.remove_btn.setToolTip("Usuń z kolejki")
        self.remove_btn.clicked.connect(lambda: page.remove_task(task))

        for b in (self.pause_btn, self.cancel_btn, self.folder_btn, self.remove_btn):
            b.setStyleSheet(
                "QPushButton { background: #332D4A; border-radius: 10px; font-size: 14px; }"
                "QPushButton:hover { background: #8B5CF6; color: white; }"
                "QPushButton:disabled { background: #262135; color: #9B97AD; }"
            )
            layout.addWidget(b)

    # --- przyciski ---
    def _toggle_pause(self):
        if self.task.state == TaskState.PAUSED:
            self.page.queue.resume(self.task)
            self.pause_btn.setIcon(self._icon_pause)
        elif self.task.state in (TaskState.DOWNLOADING, TaskState.QUEUED, TaskState.CONVERTING):
            self.page.queue.pause(self.task)
            self.pause_btn.setIcon(self._icon_play)

    def _cancel(self):
        self.page.queue.cancel(self.task)
        self.refresh()

    def _open_folder(self):
        if self.task.result_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.task.result_path).parent)))
        elif self.task.target_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.task.target_dir))

    # --- aktualizacja ---
    def refresh(self):
        t = self.task
        if t.meta:
            self.title_lbl.setText(t.meta.title)
        self.progress.setValue(int(t.progress))
        speed_mb = t.speed / 1024 / 1024
        state_pl = {
            TaskState.QUEUED: "w kolejce", TaskState.DOWNLOADING: "pobieranie",
            TaskState.PAUSED: "pauza", TaskState.CONVERTING: "konwersja",
        }.get(t.state, t.state.value)
        self.info_lbl.setText(f"{t.progress:.0f}% · {speed_mb:.1f} MB/s · {state_pl}")
        if t.state == TaskState.DONE:
            self.info_lbl.setText("100% · gotowe ✓")
            self.folder_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
        elif t.state == TaskState.ERROR:
            self.info_lbl.setText(tr(t.error_key))
            self.info_lbl.setStyleSheet("color: #F87171;")
            if t.error_detail:
                self.info_lbl.setToolTip(t.error_detail)
                self.title_lbl.setToolTip(t.error_detail)
            self.pause_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
        elif t.state == TaskState.CANCELLED:
            self.info_lbl.setText("anulowano")
            self.pause_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)


class DownloadPage(QWidget):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.library = Library()
        self._bridge = _EventBridge()
        self._bridge.event.connect(self._on_task_event)
        self.queue = QueueManager(
            max_concurrent=settings.max_concurrent,
            on_event=self._bridge.event.emit,
        )
        self._rows: dict[int, QueueRow] = {}   # id(task) -> row widget
        self._meta: VideoMeta | None = None
        self._meta_worker: _MetaWorker | None = None
        self._last_meta_url = ""

        # debounce dla podglądu (nie odpytuj przy każdej literze)
        self._meta_timer = QTimer(self)
        self._meta_timer.setSingleShot(True)
        self._meta_timer.setInterval(600)
        self._meta_timer.timeout.connect(self._fetch_meta_now)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # --- Góra: duże pole URL + POBIERZ (160 px) ---
        top = QHBoxLayout()
        self.url_edit = QLineEdit(objectName="bigUrl", placeholderText=tr("paste_url"))
        self.url_edit.textChanged.connect(self._on_url_changed)
        self.download_btn = QPushButton(tr("download"), objectName="accentBtn")
        self.download_btn.setFixedWidth(160)
        self.download_btn.setMinimumHeight(56)
        self.download_btn.clicked.connect(self._on_download_clicked)
        top.addWidget(self.url_edit, stretch=1)
        top.addWidget(self.download_btn)
        layout.addLayout(top)

        # inline komunikat o błędzie (bez wyskakujących okien)
        self.url_error = QLabel("")
        self.url_error.setProperty("class", "warning")
        self.url_error.setVisible(False)
        layout.addWidget(self.url_error)

        # --- Opcje: toggle playlisty / jakość / folder ---
        opts = QHBoxLayout()
        playlist_col = QVBoxLayout()
        playlist_col.addStretch(1)
        self.playlist_toggle = QCheckBox(tr("playlist"))
        playlist_col.addWidget(self.playlist_toggle)
        playlist_col.addStretch(1)
        opts.addLayout(playlist_col)

        quality_box = QVBoxLayout()
        cap = QLabel(tr("quality"))
        cap.setProperty("class", "caption")
        self.quality_group = QButtonGroup(self)
        qrow = QHBoxLayout()
        for br in BITRATES:
            btn = QPushButton(f"{br}", checkable=True)
            btn.setProperty("class", "segment")
            btn.setFixedWidth(56)
            self.quality_group.addButton(btn, br)
            qrow.addWidget(btn)
            if br == settings.default_bitrate:
                btn.setChecked(True)
        quality_box.addWidget(cap)
        quality_box.addLayout(qrow)
        opts.addLayout(quality_box)
        opts.addStretch(1)

        folder_col = QVBoxLayout()
        folder_cap = QLabel(tr("target_folder"))
        folder_cap.setProperty("class", "caption")
        self.folder_btn = QPushButton(f"📁  {settings.download_dir}")
        self.folder_btn.clicked.connect(self._pick_folder)
        folder_col.addWidget(folder_cap)
        folder_col.addWidget(self.folder_btn)
        opts.addLayout(folder_col)
        layout.addLayout(opts)

        # --- Karta podglądu ---
        self.preview_card = QFrame()
        self.preview_card.setProperty("class", "card")
        self.preview_card.setVisible(False)
        pc = QHBoxLayout(self.preview_card)
        pc.setContentsMargins(16, 16, 16, 16)
        self.thumb = QLabel()
        self.thumb.setFixedSize(120, 68)
        self.thumb.setStyleSheet("border-radius: 8px; background: #262135;")
        pc.addWidget(self.thumb)
        info_col = QVBoxLayout()
        self.preview_title = QLabel("—")
        self.preview_title.setProperty("class", "h1")
        self.preview_sub = QLabel("")
        self.preview_sub.setProperty("class", "dim")
        info_col.addWidget(self.preview_title)
        info_col.addWidget(self.preview_sub)
        pc.addLayout(info_col, stretch=1)
        layout.addWidget(self.preview_card)

        # --- Kolejka ---
        queue_cap = QLabel("KOLEJKA")
        queue_cap.setProperty("class", "caption")
        layout.addWidget(queue_cap)
        self.queue_list = QListWidget()
        layout.addWidget(self.queue_list, stretch=1)

    # --- metadane ---
    def _on_url_changed(self, text: str) -> None:
        url = text.strip()
        self.url_error.setVisible(False)
        looks_like_url = url.startswith(("http://", "https://")) and (
            "watch?v=" in url or "youtu.be/" in url or "playlist" in url
        )
        if not looks_like_url:
            self.preview_card.setVisible(False)
            self._meta = None
            return
        if url != self._last_meta_url:
            self._meta_timer.start()  # debounce 600 ms

    def _fetch_meta_now(self) -> None:
        url = self.url_edit.text().strip()
        if self._meta_worker and self._meta_worker.isRunning():
            self._meta_timer.start()  # spróbuj ponownie za chwilę
            return
        self._last_meta_url = url
        self._meta_worker = _MetaWorker(url, self.playlist_toggle.isChecked(),
                                        self.settings.cookies_browser)
        self._meta_worker.done.connect(self._show_preview)
        self._meta_worker.failed.connect(self._show_meta_error)
        self._meta_worker.start()

    def _show_meta_error(self, msg: str) -> None:
        key = classify_error(msg)
        self.url_error.setText("⚠  " + tr(key))
        self.url_error.setVisible(True)

    def _show_preview(self, meta: VideoMeta) -> None:
        self._meta = meta
        self.url_error.setVisible(False)
        self.preview_title.setText(meta.title)
        n = f" · playlista: {len(meta.entries)} utworów" if meta.is_playlist else ""
        self.preview_sub.setText(f"{meta.channel} · {format_duration(meta.duration)}{n}")
        self.preview_card.setVisible(True)

    # --- pobieranie ---
    def _on_download_clicked(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            return
        base_kwargs = dict(
            bitrate=self.quality_group.checkedId() or 320,
            target_dir=self.settings.download_dir,
            filename_template=self.settings.filename_template,
            cookies_browser=self.settings.cookies_browser,
        )
        if self.playlist_toggle.isChecked() and self._meta and self._meta.is_playlist:
            for entry in self._meta.entries:
                self._enqueue(DownloadTask(url=entry.url, playlist=False,
                                           meta=entry, **base_kwargs))
        else:
            self._enqueue(DownloadTask(url=url, playlist=self.playlist_toggle.isChecked(),
                                       meta=self._meta, **base_kwargs))
        # po dodaniu do kolejki wyczyść pole URL i podgląd
        self.url_edit.clear()
        self.preview_card.setVisible(False)
        self._meta = None
        self._last_meta_url = ""

    def _enqueue(self, task: DownloadTask) -> None:
        self._add_queue_row(task)
        self.queue.enqueue(task, tag_options={
            "auto_tags": self.settings.auto_tags,
            "library": self.library,
        })

    # --- wiersze kolejki ---
    def _add_queue_row(self, task: DownloadTask) -> None:
        row = QueueRow(task, self)
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 76))
        self.queue_list.addItem(item)
        self.queue_list.setItemWidget(item, row)
        self._rows[id(task)] = row

    def remove_task(self, task: DownloadTask) -> None:
        """Usuwa zadanie z kolejki (anuluje, jeśli trwa)."""
        self.queue.cancel(task)
        row = self._rows.pop(id(task), None)
        if row:
            for i in range(self.queue_list.count()):
                item = self.queue_list.item(i)
                if self.queue_list.itemWidget(item) is row:
                    self.queue_list.takeItem(i)
                    break
            row.deleteLater()

    def _on_task_event(self, task: DownloadTask, event: str) -> None:
        row = self._rows.get(id(task))
        if row:
            row.refresh()
        # błędy widoczne inline w wierszu — bez wyskakujących okien

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("target_folder"),
                                                  self.settings.download_dir)
        if folder:
            self.settings.download_dir = folder
            self.settings.save()
            self.folder_btn.setText(f"📁  {folder}")
