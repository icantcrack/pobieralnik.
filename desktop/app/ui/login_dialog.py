"""Ekran logowania — karta w kolorach aplikacji. Na razie przyjmuje dowolne dane."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from ..core.settings import tr
from .theme import PALETTE


class LoginDialog(QDialog):
    """Modalne okno logowania pokazywane przed głównym oknem.

    Każda niepusta para login/hasło przechodzi (backend dojdzie później).
    """

    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        p = PALETTE.get(theme, PALETTE["dark"])

        self.setWindowTitle(f'{tr("app_title")} — logowanie')
        self.setModal(True)
        self.setFixedSize(400, 420)
        self.setStyleSheet(f"QDialog {{ background: {p['bg']}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {p['surface']}; border-radius: 20px; }}")
        form = QVBoxLayout(card)
        form.setContentsMargins(32, 28, 32, 28)
        form.setSpacing(14)

        logo = QLabel("🎵")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 44px; background: transparent;")
        form.addWidget(logo)

        title = QLabel(tr("app_title"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            f"color: {p['text']}; font-size: 22px; font-weight: 700; "
            "background: transparent;")
        form.addWidget(title)

        subtitle = QLabel("Zaloguj się, aby kontynuować")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(
            f"color: {p['text_dim']}; font-size: 12px; background: transparent;")
        form.addWidget(subtitle)
        form.addSpacing(8)

        field_style = (
            f"QLineEdit {{ background: {p['surface_alt']}; color: {p['text']}; "
            f"border: 1px solid {p['line']}; border-radius: 10px; "
            "padding: 10px 12px; font-size: 14px; }"
            f"QLineEdit:focus {{ border: 1px solid {p['accent']}; }}"
        )

        self.login_edit = QLineEdit()
        self.login_edit.setPlaceholderText("Login:")
        self.login_edit.setStyleSheet(field_style)
        form.addWidget(self.login_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Password:")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet(field_style)
        self.password_edit.returnPressed.connect(self._try_login)
        form.addWidget(self.password_edit)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet(
            f"color: {p['danger']}; font-size: 12px; background: transparent;")
        self.error_label.setVisible(False)
        form.addWidget(self.error_label)

        form.addSpacing(4)
        login_btn = QPushButton("ZALOGUJ")
        login_btn.setCursor(Qt.PointingHandCursor)
        login_btn.setDefault(True)
        login_btn.setStyleSheet(
            f"QPushButton {{ background: {p['accent']}; color: white; "
            "border: none; border-radius: 12px; padding: 12px; "
            "font-size: 14px; font-weight: 700; letter-spacing: 1px; }"
            "QPushButton:hover { background: #9D74F8; }"
            "QPushButton:pressed { background: #7A4DE0; }"
        )
        login_btn.clicked.connect(self._try_login)
        form.addWidget(login_btn)

        root.addWidget(card)
        self.login_edit.setFocus()

    def _try_login(self) -> None:
        # Na razie: dowolne niepuste dane przechodzą.
        if not self.login_edit.text().strip() or not self.password_edit.text():
            self.error_label.setText("Wpisz login i hasło")
            self.error_label.setVisible(True)
            return
        self.accept()
