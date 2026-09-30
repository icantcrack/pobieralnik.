"""Test odtwarzania na prawdziwym MP3 przez stronę biblioteki (bez pokazywania okna)."""
import os
import sys
import tempfile
import time
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="pobieralnik_play_")
os.environ["APPDATA"] = _tmp  # izolacja biblioteki

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication  # noqa: E402
from app.core.settings import Settings  # noqa: E402
from app.core.library import Track  # noqa: E402
from app.ui.library_page import LibraryPage  # noqa: E402

MP3 = r"C:\Users\jeste\Music\TubeCutter\HEY - Hey - Moja i Twoja Nadzieja.mp3"

app = QApplication([])
page = LibraryPage(Settings())  # bez show() — nic nie miga na ekranie

t = page.library.add(Track(title="Moja i Twoja Nadzieja", artist="HEY", path=MP3,
                           duration=237, bitrate=320,
                           size_bytes=os.path.getsize(MP3)))
page.refresh()

page.toggle_play(t)
t0 = time.time()
while time.time() - t0 < 3.0:
    app.processEvents()
    time.sleep(0.05)
pos = page.player.position()
dur = page.player.duration()
state = page.player.playbackState()
print("POZYCJA:", pos, "ms / DŁUGOŚĆ:", dur, "ms / STAN:", state)
assert pos > 500, f"odtwarzanie nie ruszyło (position={pos})"
assert dur > 60000, f"bad duration {dur}"

# głośność w trakcie odtwarzania
page.volume_slider.setValue(20)
app.processEvents()
assert abs(page.audio_out.volume() - 0.20) < 0.01
print("GŁOŚNOŚĆ w trakcie grania ->", page.audio_out.volume())

# zapętlenie: przewiń prawie do końca i czekaj na EndOfMedia
page.loop_btn.setChecked(True)
page.player.setPosition(dur - 400)
t0 = time.time()
while time.time() - t0 < 3.0:
    app.processEvents()
    time.sleep(0.05)
pos2 = page.player.position()
print("PO PĘTLI pozycja:", pos2, "ms, stan:", page.player.playbackState(),
      "playing_id:", page.playing_track_id)
assert page.playing_track_id == t.id, "pętla przerwała odtwarzanie"
assert pos2 < dur - 400 + 3000, "nie wróciło na początek"
print("PĘTLA OK — utwór zaczął grać od nowa")

page.stop_playback()
print("TEST ODTWARZANIA OK")
