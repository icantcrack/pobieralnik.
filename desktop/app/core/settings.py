"""Ustawienia aplikacji + i18n (PL/EN)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "pobieralnik.lol"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DEFAULT_DOWNLOAD_DIR = Path.home() / "Music" / "TubeCutter"


@dataclass
class Settings:
    language: str = "pl"                      # "pl" | "en"
    theme: str = "dark"                       # "dark" | "light"
    download_dir: str = str(DEFAULT_DOWNLOAD_DIR)
    filename_template: str = "{artist} - {title}"
    auto_tags: bool = True
    max_concurrent: int = 2
    default_bitrate: int = 320
    cookies_browser: str = ""                 # "" | chrome | edge | firefox | brave
    legal_accepted: bool = False              # zgoda przy pierwszym starcie

    @classmethod
    def load(cls) -> "Settings":
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
                return cls(**known)
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self) -> None:
        SETTINGS_FILE.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


TRANSLATIONS = {
    "pl": {
        "app_title": "pobieralnik.lol",
        "nav_download": "Pobieranie",
        "nav_library": "Biblioteka",
        "nav_cd": "Płyta CD",
        "nav_settings": "Ustawienia",
        "paste_url": "Wklej link do filmu lub playlisty YouTube…",
        "download": "POBIERZ",
        "playlist": "Playlista",
        "quality": "JAKOŚĆ MP3",
        "target_folder": "Folder docelowy",
        "burn": "WYPAL PŁYTĘ",
        "export_pc": "EKSPORTUJ NA KOMPUTER",
        "audio_cd": "Audio CD (odtwarzacze CD, max 80 min)",
        "mp3_cd": "MP3 CD (pliki MP3, ~10 godz. muzyki)",
        "over_limit": "Przekroczono o {delta} — usuń utwory",
        "legal_title": "Informacja prawna",
        "legal_text": (
            "Pobieranie treści chronionych prawem autorskim bez zgody "
            "właściciela jest nielegalne i zabronione regulaminem YouTube.\n\n"
            "Pobieranie jest dozwolone wyłącznie dla treści własnych, "
            "objętych licencją Creative Commons lub pobieranych za zgodą autora."
        ),
        "err_removed": "Film został usunięty lub jest niedostępny.",
        "err_login": "Film wymaga zalogowania na YouTube.",
        "err_cookies": "Zamknij przeglądarkę — nie mogę odczytać cookies",
        "err_no_audio": "Brak strumienia audio dla tego filmu.",
        "err_no_space": "Brak miejsca na dysku.",
        "err_network": "Utracono połączenie — ponawiam…",
    },
    "en": {
        "app_title": "pobieralnik.lol",
        "nav_download": "Download",
        "nav_library": "Library",
        "nav_cd": "CD disc",
        "nav_settings": "Settings",
        "paste_url": "Paste a YouTube video or playlist link…",
        "download": "DOWNLOAD",
        "playlist": "Playlist",
        "quality": "MP3 QUALITY",
        "target_folder": "Target folder",
        "burn": "BURN DISC",
        "export_pc": "EXPORT TO COMPUTER",
        "audio_cd": "Audio CD (CD players, max 80 min)",
        "mp3_cd": "MP3 CD (MP3 files, ~10 h of music)",
        "over_limit": "Over by {delta} — remove tracks",
        "legal_title": "Legal notice",
        "legal_text": (
            "Downloading copyrighted content without the owner's consent is "
            "illegal and forbidden by the YouTube Terms of Service.\n\n"
            "Only download your own content, Creative Commons content, or "
            "content you have the author's permission to download."
        ),
        "err_removed": "The video was removed or is unavailable.",
        "err_login": "This video requires YouTube sign-in.",
        "err_cookies": "Close the browser — cannot read cookies",
        "err_no_audio": "No audio stream for this video.",
        "err_no_space": "Not enough disk space.",
        "err_network": "Connection lost — retrying…",
    },
}

_lang = "pl"


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in TRANSLATIONS else "pl"


def tr(key: str, **kwargs) -> str:
    text = TRANSLATIONS.get(_lang, TRANSLATIONS["pl"]).get(key, key)
    return text.format(**kwargs) if kwargs else text
