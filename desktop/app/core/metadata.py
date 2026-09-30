"""Metadane filmu / playlisty oraz lista strumieni audio (DASH)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AudioStream:
    format_id: str
    ext: str              # "opus" | "m4a" | ...
    abr: float | None     # kbps
    filesize: int | None


@dataclass
class VideoMeta:
    url: str
    title: str
    channel: str
    duration: int          # sekundy
    thumbnail_url: str
    is_playlist: bool = False
    entries: list["VideoMeta"] = field(default_factory=list)
    streams: list[AudioStream] = field(default_factory=list)


def _to_meta(info: dict) -> VideoMeta:
    streams = [
        AudioStream(
            format_id=f.get("format_id", ""),
            ext=f.get("ext", ""),
            abr=f.get("abr"),
            filesize=f.get("filesize") or f.get("filesize_approx"),
        )
        for f in (info.get("formats") or [])
        if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")
    ]
    return VideoMeta(
        url=info.get("webpage_url", ""),
        title=info.get("title", "—"),
        channel=info.get("channel") or info.get("uploader") or "—",
        duration=int(info.get("duration") or 0),
        thumbnail_url=info.get("thumbnail", ""),
        streams=streams,
    )


def fetch_metadata(url: str, playlist: bool = False, cookies_browser: str = "") -> VideoMeta:
    """Pobiera metadane bez pobierania pliku. Rzuca DownloadError przy błędzie."""
    import yt_dlp  # import leniwy — szybszy start aplikacji

    opts = {"quiet": True, "no_warnings": True, "noplaylist": not playlist,
            "extract_flat": "in_playlist" if playlist else False}
    if cookies_browser:
        opts["cookiesfrombrowser"] = (cookies_browser,)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        # zablokowana baza cookies (np. otwarty Chrome) → próbuj bez cookies
        if cookies_browser and "cookie" in str(exc).lower():
            opts.pop("cookiesfrombrowser", None)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        else:
            raise

    if playlist and info.get("entries") is not None:
        entries = [_to_meta(e) for e in info["entries"] if e]
        first = entries[0] if entries else _to_meta(info)
        first.is_playlist = True
        first.entries = entries
        first.title = info.get("title", first.title)
        return first
    return _to_meta(info)


def format_duration(seconds: int) -> str:
    m, s = divmod(max(0, seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
