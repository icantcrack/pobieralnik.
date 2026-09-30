"""Test integracyjny UI (offscreen): biblioteka, odtwarzacz, eksport/move, płyta CD."""
import os
import sys
import tempfile
from pathlib import Path

# Izolacja: nie ruszamy prawdziwej biblioteki użytkownika
_tmp = tempfile.mkdtemp(prefix="pobieralnik_test_")
os.environ["APPDATA"] = _tmp
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QFileDialog  # noqa: E402
from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402

from app.core.settings import Settings  # noqa: E402
from app.core.library import Track  # noqa: E402
from app.core.cd_manager import CdMode  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402

SHOTS = Path(__file__).parent.parent / "screenshots"
SHOTS.mkdir(exist_ok=True)

# QMessageBox.information jest modalny — podmieniamy na zbieracz komunikatów
import app.ui.library_page as lp  # noqa: E402
_msgs: list[str] = []
lp.QMessageBox.information = staticmethod(lambda *a, **k: _msgs.append(str(a[-1])) or 0)

app = QApplication([])
settings = Settings()
w = MainWindow(settings)
w.resize(1100, 760)
w.show()
app.processEvents()

library = w.pages[1]
cd_page = w.pages[2]

# --- 1. Dodaj 3 testowe utwory (prawdziwe pliki, by export/move działał) ---
media_dir = Path(_tmp) / "media"
media_dir.mkdir()
tracks = []
for i, (title, artist) in enumerate([
    ("Mniej niż zero", "Lady Pank"),
    ("Test Track 2", "Artysta B"),
    ("Test Track 3", "Artysta C"),
]):
    p = media_dir / f"{artist} - {title}.mp3"
    p.write_bytes(b"\xff\xfb" + b"\x00" * 4096)  # atrapa MP3
    t = library.library.add(Track(
        title=title, artist=artist, path=str(p),
        duration=200 + i * 10, bitrate=320, size_bytes=p.stat().st_size))
    tracks.append(t)
library.refresh()
app.processEvents()
assert len(library.cards) == 3, f"kart: {len(library.cards)}"
print("OK 1: karty utworzone:", len(library.cards))

# --- 2. Przyciski Play na kartach ---
card = library.cards[0]
assert not card.play_btn.icon().isNull(), "ikona Play pusta!"
print("OK 2: przycisk Play ma ikonę:", not card.play_btn.icon().isNull())

# --- 3. toggle_play: pasek odtwarzania widoczny ---
w._switch(1)  # biblioteka musi być bieżącą stroną (QStackedWidget ukrywa resztę)
app.processEvents()
library.toggle_play(tracks[0])
app.processEvents()
assert library.player_bar.isVisible(), "player_bar niewidoczny"
assert library.playing_track_id == tracks[0].id
print("OK 3: pasek odtwarzania widoczny, tytuł:", library.bar_title.text())

# pauza/wznowienie przez kartę
library.toggle_play(tracks[0])  # pause (jeśli gra) lub play
app.processEvents()
library.toggle_current()
app.processEvents()
print("OK 4: toggle_play/toggle_current bez wyjątków")

# --- 4. Zapętlenie ---
library.loop_btn.setChecked(True)
assert library.loop_enabled is True
# symulacja EndOfMedia
library._on_media_status(QMediaPlayer.EndOfMedia)
app.processEvents()
assert library.playing_track_id is not None, "pętla nie zadziałała (stop)"
print("OK 5: zapętlenie przy EndOfMedia działa")
library.loop_btn.setChecked(False)
library._on_media_status(QMediaPlayer.EndOfMedia)
app.processEvents()
assert library.playing_track_id is None, "stop po EndOfMedia nie zadziałał"
print("OK 6: bez pętli -> stop po EndOfMedia")

# --- 5. Głośność ---
library.volume_slider.setValue(35)
app.processEvents()
assert abs(library.audio_out.volume() - 0.35) < 0.01, library.audio_out.volume()
print("OK 7: suwak głośności ->", round(library.audio_out.volume(), 2))

# --- 6. Eksport (zmonkeypatchowany dialog) ---
dest_exp = Path(_tmp) / "export"
dest_exp.mkdir()
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: str(dest_exp))
for c in library.cards[:2]:
    c.checkbox.setChecked(True)
library._update_selection()
library.export_selected()
app.processEvents()
exported = list(dest_exp.glob("*.mp3"))
assert len(exported) == 2, f"wyeksportowano {len(exported)}"
print("OK 8: eksport ->", len(exported), "plików;", _msgs[-1].splitlines()[0] if _msgs else "")

# --- 7. Przeniesienie do folderu ---
dest_mov = Path(_tmp) / "moved"
dest_mov.mkdir()
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: str(dest_mov))
library.cards[0].checkbox.setChecked(True)
library.cards[1].checkbox.setChecked(False)
moved_id = library.cards[0].track.id
moved_name = Path(library.cards[0].track.path).name
library.move_selected()
app.processEvents()
assert (dest_mov / moved_name).exists(), "plik nie przeniesiony"
assert not (media_dir / moved_name).exists(), "oryginał nadal istnieje"
t_after = library.get_track(moved_id)
assert t_after and t_after.path == str(dest_mov / moved_name), t_after
print("OK 9: przeniesienie + update ścieżki w bazie")

# --- 8. Eksport bez zaznaczenia (komunikat zamiast ciszy) ---
for c in library.cards:
    c.checkbox.setChecked(False)
library._update_selection()
n_msgs = len(_msgs)
library.export_selected()
assert len(_msgs) > n_msgs and "Zaznacz" in _msgs[-1]
print("OK 10: komunikat przy braku zaznaczenia:", _msgs[-1][:40])

# --- 9. Zrzuty ekranu: biblioteka ---
library.refresh()
app.processEvents()
w._switch(1)
app.processEvents()
library.toggle_play(library.get_track(moved_id) or library.cards[0].track)
app.processEvents()
w.grab().save(str(SHOTS / "ui_library.png"))
print("OK 11: zrzut biblioteki")

# --- 10. Zrzuty CD: audio z utworami, MP3 pusta i z utworami ---
for t in [library.get_track(moved_id)] + [c.track for c in library.cards]:
    if t:
        cd_page.add_track(t)
w._switch(2)
app.processEvents()
w.grab().save(str(SHOTS / "ui_cd_audio.png"))
cd_page.mp3_radio.setChecked(True)
app.processEvents()
w.grab().save(str(SHOTS / "ui_cd_mp3.png"))
cd_page.project.tracks.clear()
cd_page._refresh()
app.processEvents()
w.grab().save(str(SHOTS / "ui_cd_mp3_empty.png"))
print("OK 12: zrzuty płyty CD (audio/mp3/pusta)")

print("\nWSZYSTKIE TESTY UI PRZESZŁY")
