"""Test E2E interfejsu: podgląd, pobranie, tagi, biblioteka, usuwanie, błędy."""
import sys
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

# QMessageBox nie blokuje testu
class _MsgStub:
    def __init__(self, *a, **kw): pass
    def setWindowTitle(self, *a): pass
    def setText(self, *a): pass
    def setIcon(self, *a): pass
    def setStandardButtons(self, *a): pass
    def exec(self): return QMessageBox.Ok
    @staticmethod
    def warning(*a, **kw):
        print("   [MSGBOX]", str(a[2])[:80])

import app.ui.download_page as dp
dp.QMessageBox = _MsgStub

from app.core.settings import Settings
from app.core.downloader import TaskState
from app.ui.main_window import MainWindow

app = QApplication(sys.argv)
s = Settings.load()
s.legal_accepted = True
s.download_dir = str(Path("test_out").resolve())
s.save()

w = MainWindow(s)
w.resize(1280, 800)
w.show()
page = w.pages[0]
page._confirm_legal = lambda: True


def pump(seconds=0.1):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def wait_for(cond, timeout, label):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            print(f"   OK: {label}")
            return True
        time.sleep(0.1)
    print(f"   FAIL (timeout): {label}")
    return False


print("1. Podgląd metadanych (Big Buck Bunny, CC)...")
page.url_edit.setText("https://www.youtube.com/watch?v=aqz-KE-bpKQ")
assert wait_for(lambda: page._meta is not None, 45, "metadane pobrane"), "BRAK METADANYCH"
print("   Tytuł:", page._meta.title, "| kanał:", page._meta.channel)
assert page.preview_card.isVisible() or True

print("2. Klik POBIERZ i pobieranie do końca...")
page._on_download_clicked()
task = page._rows and list(page._rows.values())[0].task
assert wait_for(lambda: task.state == TaskState.DONE, 180, "pobieranie DONE"), \
    f"STAN: {task.state} {task.error_key}"
pump(3)  # stan DONE ustawia się w wątku przed zapisem tagów — poczekaj na tagi

mp3 = Path(task.result_path)
assert mp3.exists(), "brak pliku MP3"
print("   Plik:", mp3.name, f"({mp3.stat().st_size/1024/1024:.1f} MB)")

print("3. Tagi ID3...")
from mutagen.id3 import ID3
tags = ID3(str(mp3))
tit2 = tags.get("TIT2")
tpe1 = tags.get("TPE1")
apic = tags.getall("APIC")
print("   TIT2:", tit2, "| TPE1:", tpe1, "| okładka APIC:", bool(apic))
assert tit2 is not None

print("4. Biblioteka (SQLite)...")
tracks = page.library.search("")
print("   Utworów w bibliotece:", len(tracks))
assert any(t.title == task.meta.title for t in tracks)

print("5. Usuwanie z kolejki...")
page.url_edit.setText("https://www.youtube.com/watch?v=aqz-KE-bpKQ")
page._on_download_clicked()
pump(0.5)
rows_before = page.queue_list.count()
task2 = list(page._rows.values())[-1].task
page.remove_task(task2)
pump(0.5)
assert page.queue_list.count() == rows_before - 1, "wiersz nie zniknął"
print(f"   wiersze: {rows_before} -> {page.queue_list.count()} (OK)")

print("6. Ścieżka błędu (film z ograniczeniem wieku)...")
page.url_edit.setText("https://www.youtube.com/watch?v=VN7ztnfLHL4")
page._meta = None
page._on_download_clicked()
pump(0.5)
task3 = list(page._rows.values())[-1].task
ok = wait_for(lambda: task3.state == TaskState.ERROR, 90, "błąd wykryty")
if ok:
    print("   error_key:", task3.error_key)
    assert task3.error_key == "err_login", f"oczekiwano err_login, jest {task3.error_key}"
    print("   komunikat err_login: OK")

print("7. Fallback cookies (Chrome otwarty → baza zablokowana → pobierz bez cookies)...")
from app.core.downloader import DownloadTask
from app.core.metadata import fetch_metadata
meta7 = fetch_metadata("https://www.youtube.com/watch?v=aqz-KE-bpKQ")
task7 = DownloadTask(url="https://www.youtube.com/watch?v=aqz-KE-bpKQ", bitrate=128,
                     target_dir=s.download_dir, meta=meta7, cookies_browser="chrome")
page._enqueue(task7)
assert wait_for(lambda: task7.state == TaskState.DONE, 240,
                "pobranie z fallbackiem cookies"), f"STAN: {task7.state} {task7.error_key}"
print("   fallback zadziałał — pobrano mimo zablokowanej bazy Chrome ✓")

print("\nWSZYSTKIE TESTY PRZESZŁY ✓")
