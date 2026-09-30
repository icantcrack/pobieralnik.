"""Biblioteka utworów — SQLite."""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from .settings import CONFIG_DIR

DB_PATH = CONFIG_DIR / "library.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT DEFAULT '',
    path TEXT NOT NULL UNIQUE,
    cover_path TEXT DEFAULT '',
    duration INTEGER DEFAULT 0,      -- sekundy
    bitrate INTEGER DEFAULT 0,       -- kbps
    size_bytes INTEGER DEFAULT 0,
    downloaded_at INTEGER NOT NULL   -- unix ts
);
"""


@dataclass
class Track:
    title: str
    artist: str
    path: str
    cover_path: str = ""
    duration: int = 0
    bitrate: int = 0
    size_bytes: int = 0
    downloaded_at: int = 0
    id: int | None = None


class Library:
    def __init__(self, db_path: Path = DB_PATH):
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def add(self, track: Track) -> Track:
        cur = self._conn.execute(
            """INSERT OR REPLACE INTO tracks
               (title, artist, path, cover_path, duration, bitrate, size_bytes, downloaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (track.title, track.artist, track.path, track.cover_path,
             track.duration, track.bitrate, track.size_bytes,
             track.downloaded_at or int(time.time())),
        )
        self._conn.commit()
        track.id = cur.lastrowid
        return track

    def remove(self, track_id: int) -> None:
        self._conn.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
        self._conn.commit()

    def update_path(self, track_id: int, new_path: str) -> None:
        self._conn.execute("UPDATE tracks SET path = ? WHERE id = ?",
                           (new_path, track_id))
        self._conn.commit()

    def search(self, query: str = "", order_by: str = "downloaded_at DESC") -> list[Track]:
        allowed = {"downloaded_at DESC", "downloaded_at ASC", "bitrate DESC",
                   "bitrate ASC", "title COLLATE NOCASE ASC", "artist COLLATE NOCASE ASC"}
        order = order_by if order_by in allowed else "downloaded_at DESC"
        rows = self._conn.execute(
            f"SELECT * FROM tracks WHERE title LIKE ? OR artist LIKE ? ORDER BY {order}",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [Track(**dict(r)) for r in rows]
