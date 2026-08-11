"""Kleine Helfer für Pfade, Dateinamen und Zeitangaben."""

import os
import re
import shutil
import subprocess
import sys


# Von der Umgebung gesetzte Pfade. Auf dem Desktop werden sie hergeleitet, auf
# Android reicht die App sie herein (dort gibt es weder /home noch sys._MEIPASS).
_download_folder = None
_ffmpeg_path = None


def set_download_folder(path):
    """Zielordner fest vorgeben statt ihn zu erraten."""
    global _download_folder
    _download_folder = path or None


def set_ffmpeg_path(path):
    """Ordner mit den FFmpeg-Programmen vorgeben."""
    global _ffmpeg_path
    _ffmpeg_path = path or None


def get_download_folder():
    """Get the user's download folder cross-platform."""
    if _download_folder:
        return _download_folder

    # Try XDG user dirs (Linux with localized folder names)
    try:
        result = subprocess.run(
            ["xdg-user-dir", "DOWNLOAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip()
            if os.path.isdir(path):
                return path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: common folder names
    home = os.path.expanduser("~")
    for name in ["Downloads", "İndirilenler", "Téléchargements", "Descargas", "Загрузки"]:
        candidate = os.path.join(home, name)
        if os.path.isdir(candidate):
            return candidate

    # Last fallback: home directory
    return home


# Übliche Installationsorte unter Windows, falls der PATH nichts hergibt
FFMPEG_ORTE = (
    r"C:\ffmpeg",
    r"C:\Program Files\ffmpeg",
    r"C:\ProgramData\chocolatey\bin",
    os.path.expanduser(r"~\scoop\shims"),
)


_ffmpeg_geprueft = {}


def ffmpeg_laeuft(ordner):
    """Läuft das ffmpeg in diesem Ordner wirklich?

    Im Paket kann ein Platzhalter stecken, der nur auf dem Build-Rechner
    funktioniert – etwa die Startprogramme von Chocolatey, die auf einen
    Ordner verweisen, den es woanders nicht gibt. Vorhandensein der Datei
    sagt also nichts; nur ein Aufruf klärt es.
    """
    if not ordner:
        return False
    if ordner in _ffmpeg_geprueft:
        return _ffmpeg_geprueft[ordner]

    ergebnis = False
    for name in ("ffmpeg.exe", "ffmpeg"):
        pfad = os.path.join(ordner, name)
        if not os.path.exists(pfad):
            continue
        try:
            # Ohne das blitzt unter Windows ein Konsolenfenster auf
            ohne_fenster = 0x08000000 if sys.platform == "win32" else 0
            fertig = subprocess.run([pfad, "-version"], capture_output=True,
                                    timeout=20, creationflags=ohne_fenster)
            ergebnis = fertig.returncode == 0
        except Exception:
            ergebnis = False
        break

    _ffmpeg_geprueft[ordner] = ergebnis
    return ergebnis


def _ffmpeg_suchen():
    """Ordner mit ffmpeg finden – erst über den PATH, dann an bekannten Orten.

    yt-dlp sucht sonst selbst im PATH des laufenden Prozesses. Startet die App
    aus einer Umgebung ohne den Eintrag, scheitert die Umwandlung, obwohl
    ffmpeg installiert ist. Deshalb wird der Pfad hier bestimmt und
    ausdrücklich übergeben.
    """
    gefunden = shutil.which("ffmpeg")
    if gefunden:
        return os.path.dirname(gefunden)

    for ort in FFMPEG_ORTE:
        if not os.path.isdir(ort):
            continue
        for wurzel, _, dateien in os.walk(ort):
            if any(d.lower() in ("ffmpeg.exe", "ffmpeg") for d in dateien):
                return wurzel
    return None


def get_ffmpeg_path():
    """Ordner mit den FFmpeg-Programmen – im Paket mitgeliefert oder im System.

    Im gepackten Programm liegen die Beigaben im Wurzelverzeichnis des
    entpackten Pakets, nicht in einem Unterordner "ffmpeg". Unter Linux und
    macOS heißt die Datei dort schlicht "ffmpeg", weshalb der falsche Pfad
    zufällig die Datei selbst traf; unter Windows heißt sie "ffmpeg.exe" und
    der Pfad zeigte ins Leere.
    """
    if _ffmpeg_path:
        return _ffmpeg_path
    if getattr(sys, 'frozen', False):
        paket = getattr(sys, '_MEIPASS', None)
        # Nur nehmen, wenn es dort auch wirklich startet – sonst wie bei der
        # Quellfassung im System suchen.
        if ffmpeg_laeuft(paket):
            return paket
    return _ffmpeg_suchen()


def ffmpeg_available():
    """Ist FFmpeg wirklich benutzbar? Ohne es geht nur "Original"."""
    ordner = get_ffmpeg_path()
    if ordner:
        return ffmpeg_laeuft(ordner)
    return shutil.which("ffmpeg") is not None


def audio_datei(folder, filename_base, codec=None):
    """Pfad einer vorhandenen Tonspur zu diesem Namen – oder None.

    Ohne Umwandlung steht die Endung nicht vorher fest, deshalb werden alle
    gängigen durchprobiert.
    """
    if codec:
        pfad = os.path.join(folder, f"{filename_base}.{codec}")
        return pfad if os.path.exists(pfad) else None
    from ytmd import config
    for endung in config.AUDIO_EXTENSIONS:
        pfad = os.path.join(folder, filename_base + endung)
        if os.path.exists(pfad):
            return pfad
    return None


def resource_dir():
    """Ordner mit den mitgelieferten Dateien (Icons) – im EXE oder im Quellbaum."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    # Eine Ebene über diesem Paket liegt main.py mit den Icon-Dateien.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sanitize_filename(name):
    """Strip characters that Windows/macOS/Linux reject in file names.

    Das Kürzen muss vor dem letzten Aufräumen passieren: Endet der gekürzte Name
    auf Leerzeichen oder Punkt, entfernt Windows das beim Speichern still. Der
    erwartete Name wiche dann vom tatsächlichen ab und fertige Songs würden bei
    jedem Lauf erneut geladen.
    """
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(name))
    name = re.sub(r"\s+", " ", name).strip()
    return name[:120].strip(" .") or "Unbenannt"


def free_bytes(path):
    """Freier Platz auf dem Laufwerk von `path` – auch wenn der Ordner noch fehlt."""
    while path and not os.path.isdir(path):
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return 0


def format_size(num_bytes):
    """Bytes als lesbare Größe, z. B. '112 GB' oder '1,4 GB'."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            break
        value /= 1024
    text = f"{value:.0f}" if value >= 10 or unit == "B" else f"{value:.1f}"
    return f"{text.replace('.', ',')} {unit}"


def format_duration(seconds):
    if not seconds:
        return ""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"
