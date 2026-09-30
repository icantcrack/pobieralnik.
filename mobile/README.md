# TubeCutter Mobile (Android — Flutter)

Kompaktowa wersja logiki desktopu: dolny pasek z 4 zakładkami
(Pobieranie, Biblioteka, Płyta CD, Ustawienia). Na mobile ekran CD zamiast
wypalania pokazuje **„EKSPORTUJ NA KOMPUTER"** (Wi‑Fi / kabel / chmura)
z instrukcją, jak wypalić płytę na PC.

## Budowa

```bash
flutter create . --org dev.tubecutter
# podmień lib/main.dart na załączony
flutter pub add ffmpeg_kit_flutter_new_min shared_preferences sqflite audiotagger http
flutter run        # lub: flutter build apk --release
```

## Pobieranie audio na Androidzie

Dwie ścieżki (obie wspierane przez architekturę):

1. **yt-dlp przez Chaquopy** — pełna zgodność z desktopem (ten sam Python core),
   większy rozmiar APK (~+40 MB).
2. **NewPipeExtractor (natywnie)** — lekka, wymaga portu logiki na Kotlin/Javę.

Transkodowanie do MP3: `ffmpeg_kit_flutter_new_min`
(`-vn -b:a 320k out.mp3`). Tagi: `audiotagger`.

## Eksport na komputer

- **Wi‑Fi:** wbudowany serwer HTTP (pakiet `shelf`) udostępnia ZIP z utworami
  w sieci lokalnej; ekran pokazuje kod QR z adresem.
- **Kabel USB:** pliki trafiają do `Music/TubeCutter` — widoczne po MTP.
- **Chmura:** share sheet (ZIP) → Dysk Google / Dropbox.

Ekran eksportu zawiera instrukcję wypalenia na PC (Windows: Eksplorator
→ „Wypal na dysku"; lub aplikacja desktopowa TubeCutter).
