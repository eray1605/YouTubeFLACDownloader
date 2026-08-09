# Android-Portierung — Plan

Ziel: dieselbe Playlist-Funktion auf Android, ohne die Logik ein zweites Mal zu
schreiben.

## Ausgangslage

Die Aufteilung in `ytmd/` zahlt sich hier aus:

| Teil | Zeilen | Android |
|------|-------:|---------|
| `config`, `utils`, `playlist`, `youtube`, `downloader`, `covers`, `albumart`, `tags` | 1502 | **unverändert übernehmen** |
| `app`, `widgets`, `images` (Tkinter) | 1033 | neu bauen |

Nachgewiesen: Der Kern lässt sich mit gesperrtem `tkinter`/`customtkinter`
importieren und ein vollständiger Playlist-Lauf funktioniert (siehe
`ytmd/headless.py`).

## Phase 1 — Kern entkoppeln ✅

- `utils.set_download_folder()` / `utils.set_ffmpeg_path()`: Auf dem Desktop
  werden die Pfade hergeleitet, auf Android reicht die App sie herein — dort
  gibt es weder `/home` noch `sys._MEIPASS`.
- `ytmd/headless.py`: Playlist-Lauf ohne Oberfläche, Fortschritt per Callback.
  Genau diese Funktion ruft später Kotlin auf. Auf dem Desktop nutzbar als

      python -m ytmd.headless playlist.csv --format mp3 --workers 2

## Phase 2 — FFmpeg auf Android (offen, entscheidet alles Weitere)

Ohne FFmpeg gibt es kein WAV/FLAC/MP3, sondern nur die rohe Tonspur von YouTube.

Lage: **FFmpegKit wurde am 01.04.2025 zurückgezogen**, die Binaries sind aus
Maven Central, CocoaPods und npm entfernt. Ein eindeutiger Nachfolger hat sich
nicht durchgesetzt.

Zu prüfen, in dieser Reihenfolge:

1. `FFmpegKitNext` oder ein anderer gepflegter Fork
2. FFmpeg-Binary selbst für `arm64-v8a` bauen und als Asset mitliefern
3. Notfalls ohne Umwandlung: `bestaudio` als `.m4a`/`.webm` speichern —
   funktioniert, aber ohne Formatwahl und ohne WAV

Erst wenn hier ein Weg feststeht, lohnt Phase 3.

## Phase 3 — App-Hülle (Chaquopy)

Chaquopy führt den unveränderten Python-Kern in einer Kotlin-App aus.

- Oberfläche in Kotlin/Compose: Playlist wählen, Format, Gleichzeitigkeit,
  Fortschrittsliste
- **Foreground Service** mit Dauerbenachrichtigung — Android beendet lange
  Hintergrundläufe sonst; ein Lauf über tausende Songs dauert Stunden
- Datei-Auswahl über den Storage Access Framework, Zielordner an
  `utils.set_download_folder()` durchreichen
- FFmpeg-Pfad an `utils.set_ffmpeg_path()` durchreichen

## Phase 4 — Feinschliff

- APK signieren, Sideload-Anleitung
- Sinnvolle Voreinstellungen fürs Telefon: MP3 statt WAV (3000 Songs sind als
  WAV ~105 GB, als MP3 ~24 GB), `workers = 2`
- Akku- und Netzwerkhinweise (nur über WLAN laden)

## Was nicht geht

**Google Play scheidet aus.** Die *Device and Network Abuse*-Richtlinie
verbietet Apps, die unautorisiert Inhalte herunterladen. Bleibt: Sideload per
APK oder F-Droid.

## Risiken

| Risiko | Auswirkung |
|--------|-----------|
| FFmpeg nicht lauffähig | keine Formatwahl, nur Rohton |
| Android beendet den Lauf | Foreground Service ist Pflicht, nicht optional |
| Speicherplatz auf dem Telefon | Format-Voreinstellung MP3 |
| YouTube-Sperre (wie am Desktop) | dieselben Gegenmittel: langsam, Cookies |
