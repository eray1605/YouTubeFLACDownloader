"""Cover in die Audiodatei einbetten.

WAV kennt von Haus aus kein Coverfeld. Es lässt sich aber ein ID3-Block anhängen –
nachgemessen: die Datei bleibt danach eine gültige WAV (Pythons `wave`-Modul und
ffprobe lesen sie unverändert), nur die Dateigröße wächst um das Bild. Nicht jeder
Player zeigt Cover aus WAV an; MP3 und FLAC sind dafür der zuverlässigere Weg.
"""

import os

try:
    from mutagen.flac import FLAC, Picture
    from mutagen.id3 import APIC, ID3, ID3NoHeaderError
    from mutagen.wave import WAVE
    AVAILABLE = True
except ImportError:  # ohne mutagen läuft alles weiter, nur ohne Cover
    AVAILABLE = False

COVER_FRONT = 3  # ID3-Bildtyp "Cover (front)"


def guess_mime(image):
    if image[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return ""


def has_cover(path):
    """Steckt schon ein Bild in der Datei? Spart Arbeit beim erneuten Lauf."""
    if not AVAILABLE:
        return False
    suffix = os.path.splitext(path)[1].lower()
    try:
        if suffix == ".flac":
            return bool(FLAC(path).pictures)
        if suffix == ".wav":
            tags = WAVE(path).tags
            return bool(tags and tags.getall("APIC"))
        if suffix == ".mp3":
            return bool(ID3(path).getall("APIC"))
    except Exception:
        return False
    return False


def embed_cover(path, image):
    """Bild als Cover in die Audiodatei schreiben. True bei Erfolg."""
    if not AVAILABLE or not image:
        return False
    mime = guess_mime(image)
    if not mime:
        return False

    suffix = os.path.splitext(path)[1].lower()
    try:
        if suffix == ".flac":
            audio = FLAC(path)
            audio.clear_pictures()
            picture = Picture()
            picture.type = COVER_FRONT
            picture.mime = mime
            picture.data = image
            audio.add_picture(picture)
            audio.save()
            return True

        if suffix == ".wav":
            audio = WAVE(path)
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags
        elif suffix == ".mp3":
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()
        else:
            return False

        tags.delall("APIC")
        tags.add(APIC(encoding=0, mime=mime, type=COVER_FRONT, desc="Cover", data=image))
        if suffix == ".wav":
            audio.save()
        else:
            tags.save(path)
        return True
    except Exception:
        return False
