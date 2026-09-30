"""Punkt wejścia aplikacji desktopowej pobieralnik.lol."""
from __future__ import annotations

import os
import sys

# naprawa certyfikatów SSL w buildzie PyInstaller (frozen)
try:
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except Exception:
    pass


def _selftest(url: str) -> int:
    """Tryb diagnostyczny: pobiera URL bez GUI i pisze log obok exe / w CWD."""
    import time
    import traceback
    from pathlib import Path

    log_path = Path("selftest_log.txt").resolve()

    def log(msg: str) -> None:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    log_path.write_text("", encoding="utf-8")
    log(f"SELFTEST start: {url}")
    try:
        from app.core.metadata import fetch_metadata
        meta = fetch_metadata(url)
        log(f"META OK: {meta.title} | {meta.channel} | {meta.duration}s")
    except Exception:
        log("META FAIL:\n" + traceback.format_exc())
        return 1

    try:
        from app.core.downloader import DownloadTask, DownloadWorker, TaskState
        target = Path("selftest_out").resolve()
        task = DownloadTask(url=url, bitrate=192, target_dir=str(target), meta=meta)
        worker = DownloadWorker(
            task, lambda t, ev: log(f"EVENT {ev}: {t.state.value} {t.progress:.0f}% {t.error_key}"))
        worker.run()
        log(f"KONIEC: {task.state.value} | {task.error_key or '-'} | {task.result_path}")
        if task.state == TaskState.DONE:
            from mutagen.id3 import ID3
            tags = ID3(task.result_path)
            log(f"TAGI: TIT2={tags.get('TIT2')} APIC={bool(tags.getall('APIC'))}")
            return 0
        return 2
    except Exception:
        log("WORKER FAIL:\n" + traceback.format_exc())
        return 3


def _selftest_player(mp3_path: str) -> int:
    """Sprawdza, czy w buildzie frozen działa odtwarzanie audio (QtMultimedia)."""
    import time
    from pathlib import Path
    from PySide6.QtCore import QCoreApplication, QUrl
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

    log_path = Path("selftest_player_log.txt").resolve()
    app = QCoreApplication([])
    player = QMediaPlayer()
    out = QAudioOutput()
    player.setAudioOutput(out)
    logs: list[str] = []
    player.errorOccurred.connect(
        lambda err, msg: logs.append(f"ERROR {err}: {msg}"))
    player.mediaStatusChanged.connect(lambda st: logs.append(f"status={st}"))
    player.setSource(QUrl.fromLocalFile(str(Path(mp3_path).resolve())))
    player.play()
    end = time.time() + 4
    while time.time() < end:
        app.processEvents()
        time.sleep(0.05)
    pos = player.position()
    state = player.playbackState()
    logs.append(f"state={state} position={pos}ms")
    log_path.write_text("\n".join(logs) + "\n", encoding="utf-8")
    player.stop()
    return 0 if pos > 500 else 4


def main() -> int:
    if "--selftest" in sys.argv:
        idx = sys.argv.index("--selftest")
        url = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        return _selftest(url)
    if "--selftest-player" in sys.argv:
        idx = sys.argv.index("--selftest-player")
        path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        return _selftest_player(path)

    from PySide6.QtWidgets import QApplication, QDialog

    from app.core.settings import Settings
    from app.ui.main_window import MainWindow, app_icon
    from app.ui.login_dialog import LoginDialog

    app = QApplication(sys.argv)
    app.setApplicationName("pobieralnik.lol")

    settings = Settings.load()

    login = LoginDialog(theme=settings.theme)
    login.setWindowIcon(app_icon())
    if login.exec() != QDialog.Accepted:
        return 0  # zamknięto krzyżykiem — kończymy bez okna głównego

    window = MainWindow(settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
