# TubeCutter — aplikacja do pobierania audio z YouTube (MP3) z biblioteką i przygotowaniem płyty CD

Dokumentacja projektowa + implementacja szkieletu. Wersja 1.0.

> **Nota prawna (obowiązkowa część produktu):** pobieranie treści chronionych
> prawem autorskim bez zgody właściciela jest nielegalne i zabronione
> regulaminem YouTube. Aplikacja wyświetla ten komunikat przy pierwszym
> uruchomieniu i przed każdym pobraniem. Dozwolone jest pobieranie wyłącznie
> treści własnych, objętych licencją Creative Commons lub za zgodą autora.

---

## 1. Architektura aplikacji

### 1.1. Stack technologiczny

| Warstwa | Desktop (Windows / macOS / Linux) | Mobile (Android) |
|---|---|---|
| UI | **PySide6 (Qt 6)** — Widgets + QSS | **Flutter** (Material 3, własny motyw) |
| Silnik pobierania | **yt-dlp** (API Python) | yt-dlp przez `python` (Chaquopy) **lub** NewPipeExtractor |
| Transkodowanie | **ffmpeg** (FFmpegExtractAudio / subprocess) | ffmpeg-kit (`ffmpeg-kit-flutter`) |
| Tagi ID3 + okładka | **mutagen** | `audiotagger` (plugin) |
| Baza biblioteki | **SQLite** (stdlib `sqlite3`) | **sqflite** / drift |
| Ustawienia | JSON (`settings.json`) | shared_preferences |
| Wypalanie CD | Windows: IMAPI2 (PowerShell/COM); Linux: `wodim`/`cdrdao`; macOS: `drutil`/`hdiutil` | brak — „Eksportuj na komputer" (Wi‑Fi: serwer HTTP / share sheet / USB) |

### 1.2. Podział warstw (desktop — odzwierciedlony w `desktop/`)

```
┌────────────────────────────────────────────────────────────┐
│ UI (PySide6)                                               │
│  main_window.py   – 3 kolumny: nav 72px | robocza | prawa  │
│  download_page.py / library_page.py / cd_page.py /         │
│  settings_page.py / theme.py (QSS, motywy, Inter)          │
├────────────────────────────────────────────────────────────┤
│ Core (logika, bez Qt — testowalna)                         │
│  downloader.py  – kolejka zadań, yt-dlp worker, wznawianie │
│  metadata.py    – metadane i lista strumieni (DASH)        │
│  tagger.py      – ID3v2.3 + APIC (mutagen)                 │
│  library.py     – biblioteka w SQLite                      │
│  cd_manager.py  – tryb Audio CD (80 min) / MP3 CD (700 MB) │
│  burner.py      – wypalanie (per-platforma)                │
│  settings.py    – ustawienia, szablon nazw, i18n PL/EN     │
│  legal.py       – zgoda prawna (pierwszy start + pobranie) │
├────────────────────────────────────────────────────────────┤
│ Usługi zewnętrzne: yt-dlp · ffmpeg · napęd CD              │
└────────────────────────────────────────────────────────────┘
```

Zasady:
- **Core nie importuje Qt** — komunikacja z UI przez sygnały emitowane
  przez cienkie klasy-adaptery (`QObject`) w warstwie UI lub przez
  callbacki; umożliwia testy jednostkowe i ponowne użycie logiki.
- **Kolejka pobierania** to osobny wątek roboczy (`QThread`) z semaforem
  ograniczającym liczbę równoczesnych pobrań (ustawienie, domyślnie 2).
- **Atomowość zapisu:** plik zapisywany jako `*.part`, tagowanie po
  zakończeniu transkodowania, wpis do SQLite dopiero po sukcesie.

### 1.3. Mobile (Flutter) — `mobile/`

- Ten sam model domenowy (Track, CdProject) przeniesiony 1:1 na Dart.
- 4 zakładki w dolnym pasku; zamiast „Wypal płytę" → „EKSPORTUJ NA
  KOMPUTER": lokalny serwer HTTP w sieci Wi‑Fi (QR z adresem), share
  sheet (ZIP) lub zapis do chmury (intent SAF/Drive), plus ekran
  instrukcji wypalania na PC.

---

## 2. Opis ekranów (zgodnie ze specyfikacją wyglądu)

**Styl ogólny (implementacja: `ui/theme.py`):**
- Tło `#15121E`, akcenty fiolet `#8B5CF6` i mięta `#2DD4BF`, tekst `#E5E4F0`.
- Ciemny domyślny + przełącznik jasny (motyw jasny: tło `#F4F3FA`,
  tekst `#1C1A26`, te same akcenty).
- Czcionka Inter; nagłówki 22–28 px waga 700; etykiety 11 px WERSALIKAMI,
  letter-spacing 1.5 px. Rogi 12–16 px, cienie `0 4px 24px rgba(0,0,0,.35)`,
  sekcje oddzielane odstępami i liniami `1px #2A2638` — bez obramowań kart.

### Ekran 1 — POBIERANIE (domyślny)
- Góra kolumny środkowej: duże pole wklejania URL (wys. 56 px) + przycisk
  **POBIERZ** (160 px, fiolet, radius 14 px).
- Pod spodem w rzędzie: toggle **Playlista**, pionowy segment jakości
  **128 / 192 / 256 / 320 kbps**, pole **Folder docelowy** z ikoną folderu.
- Po wklejeniu URL: karta podglądu — miniaturka 120×68 (radius 8 px),
  tytuł, kanał, długość; pod nią pasek postępu z % i prędkością.
- Lista kolejki: wiersze z okładką 40×40, tytułem, paskiem postępu,
  przyciskami pauza / anuluj / otwórz folder.

### Ekran 2 — BIBLIOTEKA
- Góra: wyszukiwarka + filtry (data pobrania, bitrate, alfabet).
- Siatka 3×N kart: okładka 160×160, tytuł, wykonawca; hover → odtwórz /
  szczegóły / dodaj do płyty. Checkboxy multi-select + dolny pasek akcji:
  „Eksportuj", „Przenieś do folderu", „Dodaj do płyty".

### Ekran 3 — PRZYGOTUJ PŁYTĘ CD
- Lewo: rysowana płyta CD (`CdWidget.paintEvent`) — łuk zajętego miejsca:
  **fioletowy** dla Audio CD (minuty, limit 80:00), **miętowy** dla MP3 CD
  (MB, limit 700).
- Prawo: lista utworów, sumaryczny czas/rozmiar, ostrzeżenie
  „Przekroczono o 4:32 — usuń utwory".
- Radio: „Audio CD (odtwarzacze CD, max 80 min)" / „MP3 CD (pliki MP3,
  ~10 godz. muzyki)".
- Dół: **WYPAL PŁYTĘ** — disabled gdy lista pusta lub limit przekroczony;
  dialog: napęd, prędkość, pasek postępu.
- Mobile: osobna zakładka + „EKSPORTUJ NA KOMPUTER" z instrukcją.

### Ekran 4 — USTAWIENIA
Język (PL/EN), folder domyślny, szablon nazw plików
(`{artist} – {title}.mp3`), auto-okładka, auto-tagi ID3, limit równoczesnych
pobrań, przełącznik motywu.

### Nawigacja
Desktop: lewy pasek 72 px (ikony: Pobieranie, Biblioteka, Płyta CD,
Ustawienia). Mobile: dolny pasek z 4 zakładkami.

---

## 3. Schemat przepływu danych

```
Użytkownik wkleja URL
        │
        ▼
[metadata.py] yt-dlp extract_info(download=False)
   → tytuł, kanał, długość, miniaturka, lista formatów DASH (audio: opus/m4a)
   → UI: karta podglądu                          ┌─ błąd → komunikat
        │ zatwierdzenie POBIERZ                  │   (film usunięty /
        ▼                                        │   brak strumienia audio)
[legal.py] zgoda prawna (każde pobranie) ────────┘
        ▼
[downloader.py] DownloadTask → kolejka (semafor N)
   → yt-dlp pobiera TYLKO strumień audio (bestaudio), plik *.part
   → progress hook → sygnały: %, prędkość, ETA
   → utrata połączenia: retry z backoffem, wznawianie od *.part
        ▼
[ffmpeg] transkodowanie → MP3 (bitrate 128/192/256/320)
        ▼
[tagger.py] ID3v2.3: TIT2, TPE1, TALB + APIC (okładka)
   → nazwa pliku wg szablonu, normalizacja znaków diakrytycznych (NFC),
     usunięcie znaków zakazanych w FS
        ▼
[library.py] INSERT do SQLite (tracks) → UI biblioteki się odświeża
        ▼
[cd_manager.py] użytkownik dodaje utwory → walidacja limitów
        ▼
[burner.py] Audio CD: dekodowanie do WAV 44.1 kHz/16-bit → IMAPI2/wodim/drutil
            MP3 CD:  kopia plików → nagranie ISO danych
```

Obsługa błędów: mapowanie wyjątków yt-dlp na komunikaty PL
(`DownloadError` → „film usunięty/niedostępny", brak formatu audio →
„brak strumienia audio", `OSError ENOSPC` → „brak miejsca na dysku").

---

## 4. MVP vs pełna wersja

| Funkcja | MVP | Pełna wersja |
|---|---|---|
| Wklejenie URL, podgląd metadanych | ✅ | ✅ |
| Pobieranie audio + MP3 (bitrate) | ✅ (jeden bitrate naraz) | ✅ + równoległe z limitem |
| Kolejka: pauza / anuluj / wznawianie | anuluj + wznawianie po restarcie | ✅ pełna |
| Biblioteka: siatka, wyszukiwarka | ✅ | ✅ + filtry, multi-select, eksport |
| Tagi ID3 + okładka | ✅ | ✅ |
| Płyta CD: wizualizacja, limity, walidacja | ✅ | ✅ |
| Wypalanie | MP3 CD (pliki) | ✅ + Audio CD (WAV→CDDA) |
| Playlisty | ❌ (tylko pojedyncze filmy) | ✅ |
| i18n PL/EN, motywy | PL, ciemny | ✅ PL/EN, jasny/ciemny |
| Aplikacja Android | ❌ | ✅ + eksport na komputer |
| Komunikat prawny | ✅ | ✅ |

---

## 5. Plan implementacji krok po kroku

1. **Fundament** — repo, `requirements.txt`, pobieranie ffmpeg (statyczny
   build w `bin/`), moduł `settings.py` + `legal.py` (zgoda prawna).
2. **Core: metadata + downloader** — yt-dlp worker, hooki postępu,
   wznawianie `*.part`, mapowanie błędów; testy na URL-ach testowych.
3. **Core: tagger + library** — mutagen, szablon nazw, SQLite, migracja
   schematu.
4. **UI: theme + main_window** — QSS, 3-kolumnowy layout, pasek nav 72 px.
5. **UI: download_page** — pole URL, podgląd, kolejka, jakość, folder.
6. **UI: library_page** — siatka okładek, wyszukiwarka, multi-select.
7. **UI: cd_page** — `CdWidget` (QPainter), walidacja limitów, dialog
   wypalania.
8. **Wypalanie** — `burner.py`: Windows IMAPI2 przez PowerShell,
   Linux `wodim`, macOS `drutil`; test na nagrywarce / obrazie ISO.
9. **Ustawienia + i18n + motyw jasny.**
10. **Mobile (Flutter)** — 4 zakładki, pobieranie przez ffmpeg-kit,
    eksport Wi‑Fi; instrukcja wypalania.
11. **Pakowanie** — PyInstaller (one-folder) z bundlowanym ffmpeg;
    podpis binarek; APK/AAB dla Androida.

### Przykładowy kod kluczowych modułów
Kompletna, sprawdzona składniowo implementacja szkieletu znajduje się w
repozytorium:

- `desktop/app/core/downloader.py` — kolejka + worker yt-dlp (fragment poniżej)
- `desktop/app/core/tagger.py`, `library.py`, `cd_manager.py`, `burner.py`
- `desktop/app/ui/*` — wszystkie 4 ekrany + motyw
- `mobile/lib/main.dart` — motyw, 4 zakładki, ekran CD z łukiem (CustomPainter)

Rdzeń workera pobierania (skrót — pełna wersja w pliku):

```python
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": str(tmp_path),                 # *.part → wznawianie
    "continuedl": True,
    "retries": 5,
    "progress_hooks": [self._on_progress],    # %, prędkość, ETA
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": str(task.bitrate),
    }],
    "noplaylist": not task.playlist,
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([task.url])
```
