"""Bereits geladene Dateien nachträglich umwandeln.

Gedacht für Songs, die ohne Umwandlung gespeichert wurden – etwa vom Telefon,
wo kein FFmpeg zur Verfügung steht. Am Rechner lässt sich das nachholen.

Reines Python reicht dafür nicht: WebM enthält meist Opus, und dafür gibt es
keinen Dekoder in der Standardbibliothek. Also wird FFmpeg aufgerufen.
"""

import os
import subprocess
import sys

from ytmd import config, tags, verify
from ytmd.utils import get_ffmpeg_path

# Diese Formate sind bereits das Ziel und werden nicht angefasst
ZIELFORMATE = ("wav", "flac", "mp3")


def ffmpeg_programm():
    """Aufrufbarer Pfad zu ffmpeg – oder None."""
    ordner = get_ffmpeg_path()
    if ordner:
        for name in ("ffmpeg.exe", "ffmpeg"):
            pfad = os.path.join(ordner, name)
            if os.path.exists(pfad):
                return pfad
    import shutil
    return shutil.which("ffmpeg")


def convert_file(quelle, audio_format, entfernen=True):
    """Eine Datei umwandeln. Gibt den neuen Pfad zurück oder None.

    Das Cover wird anschließend wieder eingebettet – FFmpeg überträgt es bei
    diesen Formaten nicht zuverlässig.
    """
    programm = ffmpeg_programm()
    if not programm:
        return None

    ziel = os.path.splitext(quelle)[0] + "." + audio_format.codec
    if os.path.abspath(ziel) == os.path.abspath(quelle):
        return quelle
    if os.path.exists(ziel) and verify.is_complete(ziel):
        return ziel

    # Cover vorher sichern, damit es die Umwandlung übersteht
    bild = None
    try:
        from mutagen import File as MutagenFile
        datei = MutagenFile(quelle)
        if datei is not None:
            for schluessel in ("APIC:", "covr"):
                wert = getattr(datei, "tags", None) and datei.tags.get(schluessel)
                if wert:
                    bild = wert.data if hasattr(wert, "data") else bytes(wert[0])
                    break
    except Exception:
        bild = None

    befehl = [programm, "-y", "-i", quelle, "-vn"]
    if audio_format.quality:
        befehl += ["-b:a", audio_format.quality + "k"]
    befehl += list(audio_format.args) + [ziel]

    try:
        ergebnis = subprocess.run(befehl, capture_output=True, timeout=600)
    except Exception:
        return None
    if ergebnis.returncode != 0 or not os.path.exists(ziel):
        return None

    if bild:
        tags.embed_cover(ziel, bild)
    if entfernen:
        try:
            os.remove(quelle)
        except OSError:
            pass
    return ziel


def convert_folder(ordner, audio_format, entfernen=True, on_file=None):
    """Alle noch nicht umgewandelten Dateien eines Ordners bearbeiten.

    Liefert (umgewandelt, fehlgeschlagen, übersprungen).
    """
    if not ffmpeg_programm():
        raise RuntimeError("FFmpeg wurde nicht gefunden – ohne das geht es nicht.")

    umgewandelt = fehler = uebersprungen = 0
    for name in sorted(os.listdir(ordner)):
        endung = os.path.splitext(name)[1].lower()
        if endung not in config.AUDIO_EXTENSIONS:
            continue
        if endung.lstrip(".") == audio_format.codec:
            uebersprungen += 1
            continue

        quelle = os.path.join(ordner, name)
        neu = convert_file(quelle, audio_format, entfernen=entfernen)
        if neu:
            umgewandelt += 1
        else:
            fehler += 1
        if on_file:
            on_file(name, bool(neu))
    return umgewandelt, fehler, uebersprungen


def _cli(argv=None):
    import argparse

    from ytmd.headless import format_by_name

    parser = argparse.ArgumentParser(
        prog="ytmd.convert",
        description="Bereits geladene Songs nachträglich umwandeln.")
    parser.add_argument("ordner", help="Ordner mit den Audiodateien")
    parser.add_argument("--format", default="wav", help="wav, flac oder mp3")
    parser.add_argument("--behalten", action="store_true",
                        help="Ursprungsdateien nicht löschen")
    args = parser.parse_args(argv)

    ziel = format_by_name(args.format)
    if not ziel.codec:
        parser.error("Zum Umwandeln ein echtes Format angeben (wav, flac, mp3).")

    def melden(name, ok):
        print(("OK      " if ok else "FEHLER  ") + name, flush=True)

    umgewandelt, fehler, uebersprungen = convert_folder(
        args.ordner, ziel, entfernen=not args.behalten, on_file=melden)
    print(f"\nUmgewandelt: {umgewandelt} · Fehlgeschlagen: {fehler} · "
          f"Schon im Zielformat: {uebersprungen}")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(_cli())
