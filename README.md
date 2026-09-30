# pobieralnik.lol

Desktopowa aplikacja do pobierania muzyki z YouTube do MP3 — z biblioteką,
wbudowanym odtwarzaczem (głośność, pętla) i przygotowaniem płyty CD
(Audio CD / MP3 CD). Windows (exe), macOS (DMG) i Android (APK).

## Pobierz gotową aplikację

Najprościej: zakładka **[Releases](https://github.com/icantcrack/pobieralnik./releases)**
— stamtąd każdy pobierze wersję na swój komputer lub telefon.

Repozytorium ma zautomatyzowany build (`.github/workflows/build.yml`).
Każdy tag `v*` (np. `git tag v1.0.0 && git push --tags`) buduje i publikuje:

| Plik | Platforma | Instalacja |
|---|---|---|
| `pobieralnik-windows.zip` | Windows 10/11 64-bit | wersja portable — rozpakuj i uruchom `pobieralnik.exe` |
| `pobieralnik-macos.dmg` | macOS | otwórz DMG, przeciągnij aplikację do Applications |
| `app-release.apk` | Android | pobierz na telefon, zezwól na instalację z nieznanych źródeł |

### Wydanie nowej wersji
```bash
git tag v1.0.0 && git push --tags     # uruchamia build
```
Po ~10–15 min w zakładce Releases pojawią się wszystkie pliki.

## Budowa ręczna

### Windows (desktop)
```powershell
cd desktop
pip install -r requirements.txt pyinstaller
powershell -ExecutionPolicy Bypass -File build_windows.ps1
```
Skrypt buduje exe (ikona nutki w środku), podmienia DLL-e OpenSSL,
uruchamia selftest sieciowy i pakuje `dist\pobieralnik-windows.zip`.

### macOS
```bash
cd desktop
pip install -r requirements.txt pyinstaller
# binarny ffmpeg skopiuj do desktop/bin/
python -m PyInstaller --noconfirm --windowed --onedir --name pobieralnik --add-data "bin:bin" main.py
```

### Android (APK)
```bash
cd mobile
flutter pub get
flutter build apk --release
# plik: mobile/build/app/outputs/flutter-apk/app-release.apk
```

### Uwaga o iPhone (iOS)
Wersja na iOS wymaga komputera Mac, konta Apple Developer (99 USD/rok)
i podpisywania kodu — jej nie da się zbudować na Windows. Aplikacja
desktopowa dla Apple to wersja **macOS** (DMG powyżej).

## Testy
```bash
cd desktop
python test_ui_integration.py   # UI: biblioteka, odtwarzacz, eksport, płyta CD
python test_login.py            # ekran logowania
python test_playback.py         # odtwarzanie prawdziwego MP3
```
