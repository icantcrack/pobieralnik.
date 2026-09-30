"""Motyw aplikacji: kolory, czcionki, QSS (ciemny domyślny + jasny)."""
from __future__ import annotations

PALETTE = {
    "dark": {
        "bg": "#15121E",
        "surface": "#1E1A2B",
        "surface_alt": "#262135",
        "line": "#2A2638",
        "accent": "#8B5CF6",       # neonowy fiolet
        "accent_mint": "#2DD4BF",  # mięta
        "text": "#E5E4F0",
        "text_dim": "#9B97AD",
        "danger": "#F87171",
    },
    "light": {
        "bg": "#F4F3FA",
        "surface": "#FFFFFF",
        "surface_alt": "#ECE9F5",
        "line": "#DDD8EC",
        "accent": "#8B5CF6",
        "accent_mint": "#0D9488",
        "text": "#1C1A26",
        "text_dim": "#6B667E",
        "danger": "#DC2626",
    },
}

FONT_FAMILY = "Inter, Satoshi, Segoe UI, sans-serif"


def qss(theme: str = "dark") -> str:
    p = PALETTE.get(theme, PALETTE["dark"])
    return f"""
* {{
    font-family: {FONT_FAMILY};
    color: {p['text']};
    font-size: 14px;
}}
QMainWindow, QWidget#root {{ background: {p['bg']}; }}

/* --- Etykiety wersalikami z szerokim trackingiem --- */
QLabel.caption {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: {p['text_dim']};
}}
QLabel.h1 {{ font-size: 26px; font-weight: 700; }}
QLabel.dim {{ color: {p['text_dim']}; }}

/* --- Nawigacja (lewy pasek 72 px) --- */
QWidget#navBar {{
    background: {p['surface']};
    border-right: 1px solid {p['line']};
}}
QToolButton#navBtn {{
    border: none;
    border-radius: 12px;
    padding: 10px 4px;
    margin: 4px 8px;
    color: {p['text_dim']};
    font-size: 10px;
}}
QToolButton#navBtn:hover {{ background: {p['surface_alt']}; }}
QToolButton#navBtn:checked {{
    background: {p['accent']};
    color: white;
}}

/* --- Pola tekstowe --- */
QLineEdit {{
    background: {p['surface']};
    border: 1px solid {p['line']};
    border-radius: 14px;
    padding: 12px 16px;
    selection-background-color: {p['accent']};
}}
QLineEdit:focus {{ border: 1px solid {p['accent']}; }}
QLineEdit#bigUrl {{ font-size: 16px; min-height: 56px; }}

/* --- Przyciski --- */
QPushButton {{
    background: {p['surface_alt']};
    border: none;
    border-radius: 14px;
    padding: 10px 18px;
}}
QPushButton:hover {{ background: {p['line']}; }}
QPushButton:disabled {{ color: {p['text_dim']}; background: {p['surface']}; }}
QPushButton#accentBtn {{
    background: {p['accent']};
    color: white;
    font-weight: 700;
    letter-spacing: 1px;
}}
QPushButton#accentBtn:hover {{ background: #9D74F8; }}
QPushButton#accentBtn:disabled {{ background: {p['line']}; color: {p['text_dim']}; }}
QPushButton#burnBtn {{
    background: {p['accent']};
    color: white;
    font-size: 16px;
    font-weight: 700;
    min-height: 52px;
    border-radius: 16px;
}}
QPushButton#burnBtn:disabled {{ background: {p['line']}; color: {p['text_dim']}; }}

/* --- Toggle / radio / checkbox --- */
QCheckBox, QRadioButton {{ spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px; height: 18px;
}}
QRadioButton::indicator:checked {{
    background: {p['accent']};
    border: 2px solid {p['accent']};
    border-radius: 9px;
}}

/* --- Segment jakości (128/192/256/320) --- */
QPushButton.segment {{
    background: {p['surface']};
    border-radius: 10px;
    padding: 8px 0;
    color: {p['text_dim']};
}}
QPushButton.segment:checked {{
    background: {p['accent']};
    color: white;
    font-weight: 600;
}}

/* --- Pasek postępu --- */
QProgressBar {{
    background: {p['surface']};
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    font-size: 10px;
    color: {p['text_dim']};
}}
QProgressBar::chunk {{ background: {p['accent']}; border-radius: 6px; }}
QProgressBar#mintChunk::chunk {{ background: {p['accent_mint']}; }}

/* --- Karty / listy --- */
QFrame.card {{
    background: {p['surface']};
    border-radius: 16px;
}}
QListWidget {{
    background: transparent;
    border: none;
}}
QListWidget::item {{
    background: {p['surface']};
    border-radius: 12px;
    margin: 4px 0;
    padding: 8px;
}}
QListWidget::item:selected {{ border: 1px solid {p['accent']}; }}

/* --- Ostrzeżenie --- */
QLabel.warning {{ color: {p['danger']}; font-weight: 600; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QToolTip {{ background: {p['surface_alt']}; color: {p['text']}; border: none; }}
"""
