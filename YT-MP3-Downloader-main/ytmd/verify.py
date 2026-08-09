"""Erkennen, ob eine Audiodatei vollständig ist.

Wird der Download hart abgebrochen – Stromausfall, Task-Manager, auf Android das
Beenden der App durch das System –, bleibt eine halbe Datei liegen. Ohne diese
Prüfung gilt sie beim nächsten Lauf als fertig und wird nie wieder angefasst.

Die Verfahren unterscheiden sich je Format (nachgemessen):
  WAV   Der RIFF-Kopf nennt die Gesamtlänge. Ist sie größer als die Datei, wurde
        abgeschnitten. Pythons `wave`-Modul hilft hier nicht: Es liest nur den
        Kopf und meldet auch für eine halbe Datei die volle Bildanzahl.
  FLAC  Eine abgeschnittene Datei lässt sich nicht mehr einlesen.
  MP3   Die gemeldete Spieldauer stammt aus dem Kopf und bleibt auch bei einer
        halben Datei gleich – hier hilft nur der Vergleich mit der Dateigröße.
"""

import os
import struct

try:
    import mutagen
    MUTAGEN = True
except ImportError:
    MUTAGEN = False

# Nur als Schutz gegen leere Reste. Bewusst niedrig: Verlustfreie Formate
# schrumpfen bei leisem Material stark, eine gültige FLAC kann wenige Kilobyte
# groß sein.
MIN_BYTES = 4 * 1024
# Anteil der erwarteten Größe, ab dem eine Datei als vollständig gilt. Nicht zu
# streng, weil die Bitrate bei variabler Kodierung nur ein Mittelwert ist.
MIN_SIZE_RATIO = 0.75
# Nur bei verlustbehafteten Formaten sagt die Bitrate etwas über die Dateigröße.
# Bei FLAC hängt sie vom Material ab und taugt nicht als Maßstab.
SIZE_CHECKED = (".mp3", ".m4a", ".aac", ".opus", ".ogg")


def _wav_complete(path, size):
    try:
        with open(path, "rb") as f:
            kopf = f.read(12)
        if len(kopf) < 12 or kopf[:4] != b"RIFF" or kopf[8:12] != b"WAVE":
            return False
        riff = struct.unpack("<I", kopf[4:8])[0]
        # 0 und 0xFFFFFFFF stehen für "unbekannt" (Datenstrom) – dann nichts sagen
        if riff in (0, 0xFFFFFFFF):
            return True
        return riff + 8 <= size
    except OSError:
        return False


def _tagged_complete(path, size):
    if not MUTAGEN:
        return True  # ohne mutagen lieber annehmen als fälschlich neu laden
    try:
        datei = mutagen.File(path)
    except Exception:
        return False  # nicht mehr lesbar -> abgebrochen
    if datei is None or not getattr(datei, "info", None):
        return True

    if not path.lower().endswith(SIZE_CHECKED):
        return True  # eingelesen, also nicht abgeschnitten

    laenge = getattr(datei.info, "length", 0) or 0
    bitrate = getattr(datei.info, "bitrate", 0) or 0
    if laenge <= 0 or bitrate <= 0:
        return True  # keine Grundlage für einen Vergleich
    erwartet = laenge * bitrate / 8
    return size >= erwartet * MIN_SIZE_RATIO


def is_complete(path):
    """Sieht die Datei nach einem abgeschlossenen Download aus?"""
    try:
        size = os.path.getsize(path)
    except OSError:
        return False
    if size < MIN_BYTES:
        return False
    if path.lower().endswith(".wav"):
        return _wav_complete(path, size)
    return _tagged_complete(path, size)
