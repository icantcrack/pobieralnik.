"""Test ekranu logowania (offscreen): puste pola -> błąd, dowolne dane -> przechodzi."""
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="pobieralnik_login_")
os.environ["APPDATA"] = _tmp
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402
from app.ui.login_dialog import LoginDialog  # noqa: E402

SHOTS = Path(__file__).parent.parent / "screenshots"
SHOTS.mkdir(exist_ok=True)

app = QApplication([])

dlg = LoginDialog(theme="dark")
dlg.show()
app.processEvents()

# puste pola -> nie przepuszcza
dlg._try_login()
app.processEvents()
assert dlg.result() != QDialog.Accepted, "puste pola przeszły!"
assert dlg.error_label.isVisible()
print("OK 1: puste pola odrzucone z komunikatem")

# dowolne dane -> przechodzi
dlg.login_edit.setText("admin")
dlg.password_edit.setText("cokolwiek123")
dlg.grab().save(str(SHOTS / "ui_login.png"))
dlg._try_login()
app.processEvents()
assert dlg.result() == QDialog.Accepted, "dowolne dane nie przeszły!"
print("OK 2: dowolny login/hasło przechodzi")

# wersja jasna też się rysuje
dlg2 = LoginDialog(theme="light")
dlg2.show()
app.processEvents()
dlg2.grab().save(str(SHOTS / "ui_login_light.png"))
print("OK 3: zrzuty ui_login.png + ui_login_light.png")

print("\nTEST LOGOWANIA OK")
