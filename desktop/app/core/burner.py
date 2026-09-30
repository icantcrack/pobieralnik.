"""Wypalanie płyty CD — warstwa per-platforma.

- Audio CD: dekodowanie MP3 → WAV 44.1 kHz/16-bit stereo (ffmpeg), potem CDDA.
- MP3 CD: nagranie plików jako płyty danych (ISO).
Windows: IMAPI2 przez PowerShell/COM. Linux: wodim. macOS: drutil/hdiutil.
"""
from __future__ import annotations

import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from .cd_manager import CdMode, CdProject


class BurnError(Exception):
    pass


def list_drives() -> list[str]:
    """Zwraca listę napędów CD/DVD w systemie."""
    system = platform.system()
    if system == "Windows":
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_CDROMDrive | Select-Object -ExpandProperty Drive"],
            capture_output=True, text=True, timeout=15,
        )
        return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    if system == "Linux":
        return [str(p) for p in Path("/dev").glob("sr*")]
    if system == "Darwin":
        out = subprocess.run(["drutil", "status"], capture_output=True, text=True, timeout=15)
        return ["default"] if out.returncode == 0 else []
    return []


def decode_to_wav(mp3_path: Path, wav_path: Path) -> None:
    from .ffmpeg_path import ffmpeg_dir
    ff_dir = ffmpeg_dir()
    exe = str(Path(ff_dir) / ("ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg")) \
        if ff_dir else "ffmpeg"
    cmd = [exe, "-y", "-i", str(mp3_path),
           "-ar", "44100", "-ac", "2", "-sample_fmt", "s16", str(wav_path)]
    if subprocess.run(cmd, capture_output=True).returncode != 0:
        raise BurnError(f"ffmpeg decode failed: {mp3_path}")


def burn(project: CdProject, drive: str = "", speed: int = 16,
         on_progress: Callable[[float, str], None] = lambda p, s: None) -> None:
    """Wypala projekt. on_progress(0..100, opis_etapu)."""
    system = platform.system()
    with tempfile.TemporaryDirectory(prefix="tubecutter_cd_") as tmp:
        tmpdir = Path(tmp)
        if project.mode == CdMode.AUDIO_CD:
            wavs = []
            for i, track in enumerate(project.tracks, 1):
                wav = tmpdir / f"{i:02d}.wav"
                decode_to_wav(Path(track.path), wav)
                wavs.append(wav)
                on_progress(i / (len(project.tracks) + 1) * 50, f"Dekodowanie {i}/{len(project.tracks)}")
            _burn_audio(system, wavs, drive, speed, on_progress)
        else:
            for i, track in enumerate(project.tracks, 1):
                dest = tmpdir / Path(track.path).name
                dest.write_bytes(Path(track.path).read_bytes())
                on_progress(i / (len(project.tracks) + 1) * 50, f"Kopiowanie {i}/{len(project.tracks)}")
            _burn_data(system, tmpdir, drive, speed, on_progress)
    on_progress(100.0, "Zakończono")


def _burn_audio(system: str, wavs: list[Path], drive: str, speed: int,
                on_progress) -> None:
    if system == "Linux":
        cmd = ["wodim", "-audio", "-pad", f"speed={speed}"] + [str(w) for w in wavs]
        if drive:
            cmd.insert(1, f"dev={drive}")
        _run_with_progress(cmd, on_progress, base=50.0)
    elif system == "Darwin":
        cmd = ["drutil", "burn", "-audio", "-speed", str(speed)] + [str(w) for w in wavs]
        _run_with_progress(cmd, on_progress, base=50.0)
    else:  # Windows — IMAPI2 przez PowerShell (skrypt generowany dynamicznie)
        _burn_windows_imapi([str(w) for w in wavs], drive, speed, audio=True,
                            on_progress=on_progress)


def _burn_data(system: str, folder: Path, drive: str, speed: int, on_progress) -> None:
    iso = folder.parent / "disc.iso"
    if system == "Linux":
        subprocess.run(["mkisofs", "-o", str(iso), "-J", "-R", str(folder)],
                       capture_output=True, check=True)
        cmd = ["wodim", f"speed={speed}", str(iso)]
        if drive:
            cmd.insert(1, f"dev={drive}")
        _run_with_progress(cmd, on_progress, base=50.0)
    elif system == "Darwin":
        subprocess.run(["hdiutil", "makehybrid", "-o", str(iso), str(folder)],
                       capture_output=True, check=True)
        _run_with_progress(["drutil", "burn", "-speed", str(speed), str(iso)],
                           on_progress, base=50.0)
    else:
        _burn_windows_imapi([str(folder)], drive, speed, audio=False,
                            on_progress=on_progress)


def _burn_windows_imapi(items: list[str], drive: str, speed: int, audio: bool,
                        on_progress) -> None:
    """Szkielet wypalania przez IMAPI2 (COM) — wymaga pywin32 lub skryptu PS."""
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise BurnError("Windows: wymagany pakiet pywin32 (IMAPI2/COM)") from exc

    on_progress(55.0, "Inicjalizacja IMAPI2…")
    disc_master = win32com.client.Dispatch("IMAPI2.MsftDiscMaster2")
    recorder_id = disc_master.Item(0) if not drive else drive
    recorder = win32com.client.Dispatch("IMAPI2.MsftDiscRecorder2")
    recorder.InitializeDiscRecorder(recorder_id)
    # Pełna implementacja: MsftDiscFormat2TrackAtOnce (audio) /
    # MsftDiscFormat2Data + IFileSystemImage (dane), zdarzenia Update → on_progress.
    on_progress(90.0, "Wypalanie…")
    raise BurnError("IMAPI2: do ukończenia w kroku 8 planu — interfejs COM podpięty")


def _run_with_progress(cmd: list[str], on_progress, base: float = 0.0) -> None:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        on_progress(base, line.strip())
    proc.wait()
    if proc.returncode != 0:
        raise BurnError(f"Polecenie nie powiodło się: {' '.join(cmd)}")
