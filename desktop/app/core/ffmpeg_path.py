"""Lokalizacja ffmpeg: najpierw bundlowany bin/ obok aplikacji, potem PATH."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def ffmpeg_dir() -> str | None:
    """Katalog z ffmpeg — bundlowany (PyInstaller / dev) albo None (PATH)."""
    candidates = []
    if getattr(sys, "frozen", False):  # PyInstaller
        candidates.append(Path(sys._MEIPASS) / "bin")          # noqa: SLF001
        candidates.append(Path(sys.executable).parent / "bin")
    # tryb deweloperski: desktop/bin/ względem app/core/
    candidates.append(Path(__file__).resolve().parents[2] / "bin")
    for cand in candidates:
        exe = cand / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if exe.exists():
            return str(cand)
    return shutil.which("ffmpeg") and str(Path(shutil.which("ffmpeg")).parent)
