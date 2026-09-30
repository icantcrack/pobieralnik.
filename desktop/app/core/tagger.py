"""Tagi ID3v2.3 (mutagen) — tytuł, wykonawca, album. Bez okładek."""
from __future__ import annotations

from pathlib import Path


def tag_file(mp3_path: Path, title: str = "", artist: str = "", album: str = "") -> None:
    from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB

    try:
        tags = ID3(str(mp3_path))
    except ID3NoHeaderError:
        tags = ID3()

    if title:
        tags.setall("TIT2", [TIT2(encoding=3, text=title)])
    if artist:
        tags.setall("TPE1", [TPE1(encoding=3, text=artist)])
    if album:
        tags.setall("TALB", [TALB(encoding=3, text=album)])

    tags.save(str(mp3_path), v2_version=3)  # v2.3 — kompatybilność z odtwarzaczami CD/car
