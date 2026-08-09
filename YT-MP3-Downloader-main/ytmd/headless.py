"""Playlist-Download ohne Oberfläche.

Dies ist die Naht für andere Plattformen: Android ruft `run_playlist` aus Kotlin
heraus auf (über Chaquopy) und bekommt den Fortschritt per Callback zurück – die
Oberfläche wird dort nativ gebaut, die Logik bleibt diese hier.

Auf dem Desktop lässt sich dieselbe Funktion über die Kommandozeile nutzen:

    python -m ytmd.headless meine_playlist.csv --format mp3 --workers 2
"""

import argparse
import sys

from ytmd import config, utils
from ytmd.downloader import PlaylistDownloader
from ytmd.playlist import parse_playlist_file


def format_by_name(name):
    """Zielformat über einen kurzen Namen wählen ("mp3", "wav", "flac")."""
    if not name:
        return config.DEFAULT_FORMAT
    gesucht = name.strip().lower()
    for audio_format in config.AUDIO_FORMATS:
        if audio_format.codec == gesucht or audio_format.label.lower() == gesucht:
            return audio_format
    erlaubt = ", ".join(sorted({f.codec for f in config.AUDIO_FORMATS}))
    raise ValueError(f"Unbekanntes Format {name!r}. Möglich: {erlaubt}")


def run_playlist(playlist_file, target_folder=None, audio_format=None, workers=None,
                 cookies_from_browser=None, save_covers=True, ffmpeg_path=None,
                 on_status=None, on_progress=None):
    """Playlist einlesen und herunterladen. Gibt ein PlaylistResult zurück.

    Blockiert bis zum Ende – der Aufrufer sorgt für den Hintergrund-Thread
    (auf Android der Foreground Service).
    """
    if ffmpeg_path:
        utils.set_ffmpeg_path(ffmpeg_path)

    name, tracks = parse_playlist_file(playlist_file)
    if not tracks:
        raise ValueError(f"Keine Songs in {playlist_file} erkannt")

    job = PlaylistDownloader(
        tracks, name,
        audio_format=format_by_name(audio_format) if isinstance(audio_format, str)
        else audio_format,
        target_root=target_folder,
        workers=workers,
        cookies_from_browser=cookies_from_browser,
        save_covers=save_covers,
        on_status=on_status,
        on_progress=on_progress,
    )
    return job.run()


def _cli(argv=None):
    parser = argparse.ArgumentParser(
        prog="ytmd.headless",
        description="Spotify-Playlist-Export herunterladen – ohne Oberfläche.")
    parser.add_argument("playlist", help="Exportierte Playlist (JSON oder CSV)")
    parser.add_argument("--target", help="Zielordner (Standard: Download-Ordner)")
    parser.add_argument("--format", default="wav", help="wav, flac oder mp3")
    parser.add_argument("--workers", type=int, default=config.DEFAULT_WORKERS,
                        help="gleichzeitige Downloads")
    parser.add_argument("--cookies", help="Browser für Cookies, z. B. chrome")
    parser.add_argument("--no-covers", action="store_true", help="keine Cover einbetten")
    parser.add_argument("--ffmpeg", help="Ordner mit den FFmpeg-Programmen")
    args = parser.parse_args(argv)

    gesamt = {"total": 0}

    def status(index, state, detail=None):
        if state in ("done", "skipped", "failed", "no_space"):
            grund = f"  ({detail[0]})" if isinstance(detail, tuple) else ""
            print(f"[{index + 1}] {state}{grund}", flush=True)

    def progress(done, total):
        gesamt["total"] = total
        print(f"  ... {done}/{total}", flush=True)

    ergebnis = run_playlist(
        args.playlist, target_folder=args.target, audio_format=args.format,
        workers=args.workers, cookies_from_browser=args.cookies,
        save_covers=not args.no_covers, ffmpeg_path=args.ffmpeg,
        on_status=status, on_progress=progress)

    print(f"\nGeladen: {ergebnis.downloaded} | Übersprungen: {ergebnis.skipped} | "
          f"Fehler: {len(ergebnis.failed)} | Cover: {ergebnis.covers}")
    print(f"Ordner: {ergebnis.folder}")
    if ergebnis.stopped_reason:
        print(f"Vorzeitig gestoppt: {ergebnis.stopped_reason} "
              f"({ergebnis.remaining} Songs offen)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
