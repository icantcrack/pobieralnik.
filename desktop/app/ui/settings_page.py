"""Ekran 4 — Ustawienia: język, folder, szablon nazw, tagi, limity, motyw."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from ..core.settings import Settings, set_language, tr


class SettingsPage(QWidget):
    def __init__(self, settings: Settings, on_changed=None):
        super().__init__()
        self.settings = settings
        self._on_changed = on_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel(tr("nav_settings"))
        title.setProperty("class", "h1")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(14)

        self.lang_box = QComboBox()
        self.lang_box.addItems(["Polski", "English"])
        self.lang_box.setCurrentIndex(0 if settings.language == "pl" else 1)
        form.addRow("Język / Language", self.lang_box)

        self.theme_box = QComboBox()
        self.theme_box.addItems(["Ciemny / Dark", "Jasny / Light"])
        self.theme_box.setCurrentIndex(0 if settings.theme == "dark" else 1)
        form.addRow("Motyw / Theme", self.theme_box)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(settings.download_dir)
        folder_btn = QPushButton("📁")
        folder_btn.setFixedWidth(48)
        folder_btn.clicked.connect(self._pick_folder)
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(folder_btn)
        form.addRow("Folder domyślny", folder_row)

        self.template_edit = QLineEdit(settings.filename_template)
        self.template_edit.setPlaceholderText("{artist} - {title}")
        form.addRow("Szablon nazw plików", self.template_edit)

        self.tags_check = QCheckBox("Automatycznie zapisuj tagi ID3")
        self.tags_check.setChecked(settings.auto_tags)
        form.addRow(self.tags_check)

        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 8)
        self.concurrent_spin.setValue(settings.max_concurrent)
        form.addRow("Limit równoczesnych pobrań", self.concurrent_spin)

        self.cookies_box = QComboBox()
        self.cookies_box.addItems(["Wyłączone", "Chrome", "Edge", "Firefox", "Brave"])
        idx = ["", "chrome", "edge", "firefox", "brave"].index(settings.cookies_browser) \
            if settings.cookies_browser in ("chrome", "edge", "firefox", "brave") else 0
        self.cookies_box.setCurrentIndex(idx)
        form.addRow("Cookies z przeglądarki (filmy 18+/login)", self.cookies_box)

        layout.addLayout(form)
        layout.addStretch(1)

        save_btn = QPushButton("ZAPISZ", objectName="accentBtn")
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Folder domyślny",
                                                  self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)

    def _save(self) -> None:
        s = self.settings
        s.language = "pl" if self.lang_box.currentIndex() == 0 else "en"
        s.theme = "dark" if self.theme_box.currentIndex() == 0 else "light"
        s.download_dir = self.folder_edit.text()
        s.filename_template = self.template_edit.text() or "{artist} - {title}"
        s.auto_tags = self.tags_check.isChecked()
        s.max_concurrent = self.concurrent_spin.value()
        s.cookies_browser = ["", "chrome", "edge", "firefox", "brave"][self.cookies_box.currentIndex()]
        s.save()
        set_language(s.language)
        if self._on_changed:
            self._on_changed()
