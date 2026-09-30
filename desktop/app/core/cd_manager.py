"""Logika przygotowania płyty CD: tryby, limity, walidacja."""
from __future__ import annotations

import enum
from dataclasses import dataclass

from .library import Track


class CdMode(enum.Enum):
    AUDIO_CD = "audio"   # limit czasu: 80 min
    MP3_CD = "mp3"       # limit danych: 700 MB


LIMITS = {
    CdMode.AUDIO_CD: 80 * 60,                # 4800 s
    CdMode.MP3_CD: 700 * 1024 * 1024,        # 734 003 200 B
}


@dataclass
class CdStatus:
    used: float          # sekundy lub bajty zależnie od trybu
    limit: float
    over_limit: bool
    fraction: float      # 0..1 (do rysowania łuku; przy przekroczeniu >1)

    @property
    def over_delta(self) -> float:
        return max(0.0, self.used - self.limit)


class CdProject:
    """Lista utworów na płytę + walidacja limitu."""

    def __init__(self, mode: CdMode = CdMode.AUDIO_CD):
        self.mode = mode
        self.tracks: list[Track] = []

    def add(self, track: Track) -> None:
        # bez duplikatów — porównujemy po id (obiekt z bazy może mieć inne pola)
        if track.id is not None:
            if any(x.id == track.id for x in self.tracks):
                return
        elif track in self.tracks:
            return
        self.tracks.append(track)

    def remove(self, track: Track) -> None:
        if track in self.tracks:
            self.tracks.remove(track)

    def clear(self) -> None:
        self.tracks.clear()

    def status(self) -> CdStatus:
        if self.mode == CdMode.AUDIO_CD:
            used = float(sum(t.duration for t in self.tracks))
        else:
            used = float(sum(t.size_bytes for t in self.tracks))
        limit = float(LIMITS[self.mode])
        return CdStatus(
            used=used, limit=limit,
            over_limit=used > limit,
            fraction=used / limit if limit else 0.0,
        )

    def can_burn(self) -> bool:
        s = self.status()
        return bool(self.tracks) and not s.over_limit


def format_used(mode: CdMode, used: float) -> str:
    if mode == CdMode.AUDIO_CD:
        m, s = divmod(int(used), 60)
        return f"{m}:{s:02d} min"
    return f"{used / 1024 / 1024:.0f} MB"


def format_over_delta(mode: CdMode, delta: float) -> str:
    """'4:32' lub '37 MB' — do komunikatu 'Przekroczono o …'."""
    if mode == CdMode.AUDIO_CD:
        m, s = divmod(int(delta), 60)
        return f"{m}:{s:02d}"
    return f"{delta / 1024 / 1024:.0f} MB"
