"""Kolejka pobierania: yt-dlp worker, postęp, pauza/anuluj, wznawianie, błędy.

Warstwa core nie zależy od Qt — komunikacja przez callbacki.
"""
from __future__ import annotations

import enum
import os
import shutil
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue, Empty

from .metadata import VideoMeta
from .ffmpeg_path import ffmpeg_dir


class TaskState(enum.Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    CONVERTING = "converting"
    DONE = "done"
    CANCELLED = "cancelled"
    ERROR = "error"


class DownloadError(Exception):
    """Błąd z przyjaznym kluczem komunikatu (err_removed / err_no_audio / ...)."""
    def __init__(self, message_key: str, detail: str = ""):
        super().__init__(message_key)
        self.message_key = message_key
        self.detail = detail


def classify_error(message: str) -> str:
    """Mapuje surowy błąd yt-dlp/systemu na klucz przyjaznego komunikatu."""
    msg = message.lower()
    # najpierw logowanie/wiek (YouTube dokleja wskazówkę o cookies — kolejność ważna)
    if any(k in msg for k in ("sign in", "confirm your age", "not a bot",
                              "login required")):
        return "err_login"
    # potem problemy z odczytem cookies (zablokowana baza Chrome itp.)
    if any(k in msg for k in ("could not copy", "cookie database", "cookie",
                              "failed to decrypt")):
        return "err_cookies"
    if any(k in msg for k in ("removed", "unavailable", "private", "404")):
        return "err_removed"
    if "no space" in msg or "errno 28" in msg:
        return "err_no_space"
    return "err_network"


@dataclass
class DownloadTask:
    url: str
    bitrate: int = 320
    playlist: bool = False
    target_dir: str = ""
    filename_template: str = "{artist} - {title}"
    cookies_browser: str = ""       # "" | "chrome" | "edge" | "firefox" | "brave"
    meta: VideoMeta | None = None
    state: TaskState = TaskState.QUEUED
    progress: float = 0.0          # 0..100
    speed: float = 0.0             # B/s
    eta: int = 0                   # s
    error_key: str = ""
    error_detail: str = ""          # surowy fragment błędu (diagnostyka, tooltip)
    result_path: str = ""


def sanitize_filename(name: str) -> str:
    """Zachowuje polskie znaki diakrytyczne (NFC), usuwa znaki zakazane w FS."""
    name = unicodedata.normalize("NFC", name).strip()
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "_")
    return name.rstrip(". ") or "utwor"


def ensure_disk_space(directory: Path, needed_bytes: int) -> None:
    free = shutil.disk_usage(directory).free
    if free < needed_bytes * 1.1:  # 10% zapasu na plik tymczasowy
        raise DownloadError("err_no_space", f"free={free} needed={needed_bytes}")


class DownloadWorker(threading.Thread):
    """Pojedynczy wątek pobierający — jeden na zadanie; kolejką zarządza QueueManager."""

    MAX_RETRIES = 5
    RETRY_BACKOFF = (2, 5, 10, 20, 30)  # sekundy

    def __init__(self, task: DownloadTask, on_event):
        super().__init__(daemon=True)
        self.task = task
        self.on_event = on_event  # callback(task, event_name: str)
        self._cancel = threading.Event()
        self._pause = threading.Event()

    # --- sterowanie ---
    def cancel(self):
        self._cancel.set()

    def pause(self):
        self._pause.set()

    def resume(self):
        self._pause.clear()

    # --- hooki yt-dlp ---
    def _progress_hook(self, d: dict) -> None:
        if self._cancel.is_set():
            raise DownloadError("cancelled")
        while self._pause.is_set() and not self._cancel.is_set():
            time.sleep(0.2)
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            self.task.progress = (downloaded / total * 100) if total else 0.0
            self.task.speed = d.get("speed") or 0.0
            self.task.eta = d.get("eta") or 0
            self.on_event(self.task, "progress")
        elif d.get("status") == "finished":
            self.task.state = TaskState.CONVERTING
            self.on_event(self.task, "converting")

    def _ydl_options(self, tmp_path: Path, cookies_browser: str = "") -> dict:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(tmp_path),
            "continuedl": True,               # wznawianie od *.part
            "retries": 0,                     # retry obsługujemy sami (backoff)
            "fragment_retries": 10,
            "progress_hooks": [self._progress_hook],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(self.task.bitrate),
            }],
            "noplaylist": not self.task.playlist,
            "quiet": True,
            "no_warnings": True,
        }
        ff = ffmpeg_dir()
        if ff:
            opts["ffmpeg_location"] = ff
        if cookies_browser:
            opts["cookiesfrombrowser"] = (cookies_browser,)
        return opts

    # --- główna pętla ---
    def run(self) -> None:
        import yt_dlp

        t = self.task
        t.state = TaskState.DOWNLOADING
        self.on_event(t, "state")

        # brak metadanych (podgląd nie zdążył się pobrać) → dociągnij tutaj
        if t.meta is None:
            try:
                from .metadata import fetch_metadata
                t.meta = fetch_metadata(t.url, cookies_browser=t.cookies_browser)
                self.on_event(t, "meta")
            except Exception as exc:
                key = classify_error(str(exc))
                t.error_detail = str(exc).splitlines()[0][:200] if str(exc) else ""
                # zablokowana baza cookies → próbuj bez cookies
                if key == "err_cookies" and t.cookies_browser:
                    t.cookies_browser = ""
                    try:
                        t.meta = fetch_metadata(t.url)
                        self.on_event(t, "meta")
                        key = ""
                    except Exception as exc2:
                        key = classify_error(str(exc2))
                        t.error_detail = str(exc2).splitlines()[0][:200] if str(exc2) else ""
                if key:
                    t.state, t.error_key = TaskState.ERROR, key
                    self.on_event(t, "error")
                    return

        target_dir = Path(t.target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        meta = t.meta
        base = sanitize_filename(
            t.filename_template.format(artist=meta.channel or "unknown", title=meta.title)
        )
        tmp_path = target_dir / (base + ".%(ext)s")

        ensure_disk_space(target_dir, needed_bytes=64 * 1024 * 1024)

        cookies = t.cookies_browser
        attempt = 0
        while attempt <= self.MAX_RETRIES:
            try:
                with yt_dlp.YoutubeDL(self._ydl_options(tmp_path, cookies)) as ydl:
                    ydl.download([t.url])
                break
            except DownloadError:
                t.state = TaskState.CANCELLED
                self.on_event(t, "state")
                return
            except yt_dlp.utils.DownloadError as exc:
                key = classify_error(str(exc))
                t.error_detail = str(exc).splitlines()[0][:200] if str(exc) else ""
                # zablokowana baza cookies (np. otwarty Chrome) → fallback bez cookies
                if key == "err_cookies" and cookies:
                    cookies = ""
                    self.on_event(t, "cookie_fallback")
                    continue  # nie liczymy tej próby
                if key in ("err_removed", "err_login", "err_cookies"):
                    t.state, t.error_key = TaskState.ERROR, key
                    self.on_event(t, "error")
                    return
                if attempt < self.MAX_RETRIES:
                    self.on_event(t, "retry")
                    time.sleep(self.RETRY_BACKOFF[min(attempt, len(self.RETRY_BACKOFF) - 1)])
                    attempt += 1
                    continue  # continuedl=True → wznowi od *.part
                t.state, t.error_key = TaskState.ERROR, "err_network"
                self.on_event(t, "error")
                return
            except OSError as exc:
                t.state = TaskState.ERROR
                t.error_key = "err_no_space" if exc.errno == 28 else "err_network"
                t.error_detail = str(exc)[:200]
                self.on_event(t, "error")
                return
            except Exception as exc:  # noqa: BLE001 — ostatnia linia obrony
                t.state, t.error_key = TaskState.ERROR, "err_no_audio"
                t.error_detail = str(exc)[:200]
                self.on_event(t, "error")
                return

        mp3 = target_dir / (base + ".mp3")
        if not mp3.exists():  # yt-dlp mógł dołożyć sufiks
            candidates = sorted(target_dir.glob(base + "*.mp3"))
            if candidates:
                mp3 = candidates[0]
            else:
                t.state, t.error_key = TaskState.ERROR, "err_no_audio"
                self.on_event(t, "error")
                return

        t.result_path = str(mp3)
        t.state = TaskState.DONE
        t.progress = 100.0
        self.on_event(t, "done")


class QueueManager:
    """Kolejka z semaforem ograniczającym liczbę równoczesnych pobrań."""

    def __init__(self, max_concurrent: int = 2, on_event=lambda task, event: None):
        self._sem = threading.Semaphore(max_concurrent)
        self._queue: "Queue[tuple[DownloadTask, dict]]" = Queue()
        self._workers: list[DownloadWorker] = []
        self._on_event = on_event
        self._dispatcher = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._dispatcher.start()

    def set_max_concurrent(self, n: int) -> None:
        self._sem = threading.Semaphore(max(1, n))

    def enqueue(self, task: DownloadTask, tag_options: dict | None = None) -> None:
        self._queue.put((task, tag_options or {}))

    def _dispatch_loop(self) -> None:
        while True:
            try:
                task, tag_opts = self._queue.get(timeout=0.5)
            except Empty:
                continue
            self._sem.acquire()
            if task.state == TaskState.CANCELLED:
                self._sem.release()
                continue
            worker = DownloadWorker(task, self._wrap_event(tag_opts))
            self._workers.append(worker)
            worker.start()

    def _wrap_event(self, tag_opts: dict):
        def cb(task: DownloadTask, event: str):
            if event == "done" and tag_opts:
                try:
                    from .tagger import tag_file
                    meta = task.meta
                    tag_file(
                        Path(task.result_path),
                        title=meta.title if meta else "",
                        artist=meta.channel if meta else "",
                    )
                except Exception:
                    pass  # tagi są opcjonalne — plik MP3 i tak powstał
                if tag_opts.get("library"):
                    try:
                        from .library import Library, Track
                        dur = task.meta.duration if task.meta else 0
                        size = os.path.getsize(task.result_path)
                        tag_opts["library"].add(Track(
                            title=task.meta.title if task.meta else Path(task.result_path).stem,
                            artist=task.meta.channel if task.meta else "",
                            path=task.result_path,
                            duration=dur,
                            bitrate=task.bitrate,
                            size_bytes=size,
                        ))
                    except Exception:
                        pass
            self._on_event(task, event)
            if event in ("done", "error", "state") and task.state in (
                TaskState.DONE, TaskState.ERROR, TaskState.CANCELLED
            ):
                self._sem.release()
        return cb

    def pause(self, task: DownloadTask) -> None:
        for w in self._workers:
            if w.task is task:
                w.pause()
                task.state = TaskState.PAUSED

    def resume(self, task: DownloadTask) -> None:
        for w in self._workers:
            if w.task is task:
                w.resume()
                task.state = TaskState.DOWNLOADING

    def cancel(self, task: DownloadTask) -> None:
        task.state = TaskState.CANCELLED
        for w in self._workers:
            if w.task is task:
                w.cancel()
