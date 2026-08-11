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
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.wave import WAVE
    AVAILABLE = True
except ImportError:  # ohne mutagen läuft alles weiter, nur ohne Cover
    AVAILABLE = False

# MP4/M4A speichert das Cover in einem eigenen Feld, nicht als ID3
MP4_ENDUNGEN = (".m4a", ".mp4", ".m4b")

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
        if suffix in MP4_ENDUNGEN:
            return bool(MP4(path).get("covr"))
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


def has_tags(path):
    """Steht schon ein Titel drin? Dann muss nichts erneut geschrieben werden."""
    if not AVAILABLE:
        return False
    try:
        import mutagen
        datei = mutagen.File(path)
        if datei is None or not datei.tags:
            return False
    except Exception:
        return False

    # Jeden Schlüssel einzeln absichern: FLAC wirft bei fremden Namen wie
    # "\xa9nam" eine Ausnahme, statt einfach nichts zu liefern – ein
    # gemeinsames except würde die Prüfung vorzeitig abbrechen.
    for schluessel in ("TIT2", "\xa9nam", "title", "TITLE"):
        try:
            if datei.tags.get(schluessel):
                return True
        except Exception:
            continue
    return False


def write_tags(path, title="", artist="", album="", released="", track_number=None):
    """Titel, Interpret, Album und Datum in die Datei schreiben.

    Ohne das zeigt jeder Player "Unknown". Jedes Format hat dafür eigene
    Feldnamen – ID3 bei MP3 und WAV, eigene Kürzel bei MP4, Klartext bei FLAC.
    """
    if not AVAILABLE or not (title or artist or album):
        return False

    jahr = str(released or "")[:10]
    suffix = os.path.splitext(path)[1].lower()
    try:
        if suffix in MP4_ENDUNGEN:
            audio = MP4(path)
            if title:
                audio["\xa9nam"] = [title]
            if artist:
                audio["\xa9ART"] = [artist]
            if album:
                audio["\xa9alb"] = [album]
            if jahr:
                audio["\xa9day"] = [jahr]
            if track_number:
                audio["trkn"] = [(int(track_number), 0)]
            audio.save()
            return True

        if suffix == ".flac":
            audio = FLAC(path)
            if title:
                audio["title"] = title
            if artist:
                audio["artist"] = artist
            if album:
                audio["album"] = album
            if jahr:
                audio["date"] = jahr
            if track_number:
                audio["tracknumber"] = str(track_number)
            audio.save()
            return True

        # MP3 und WAV teilen sich ID3
        from mutagen.id3 import TALB, TDRC, TIT2, TPE1, TRCK
        if suffix == ".wav":
            audio = WAVE(path)
            if audio.tags is None:
                audio.add_tags()
            marken = audio.tags
        elif suffix == ".mp3":
            try:
                marken = ID3(path)
            except ID3NoHeaderError:
                marken = ID3()
        else:
            return False

        if title:
            marken.setall("TIT2", [TIT2(encoding=3, text=[title])])
        if artist:
            marken.setall("TPE1", [TPE1(encoding=3, text=[artist])])
        if album:
            marken.setall("TALB", [TALB(encoding=3, text=[album])])
        if jahr:
            marken.setall("TDRC", [TDRC(encoding=3, text=[jahr])])
        if track_number:
            marken.setall("TRCK", [TRCK(encoding=3, text=[str(track_number)])])

        if suffix == ".wav":
            audio.save()
        else:
            marken.save(path)
        return True
    except Exception:
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
        if suffix in MP4_ENDUNGEN:
            audio = MP4(path)
            audio["covr"] = [MP4Cover(
                image,
                imageformat=(MP4Cover.FORMAT_PNG if mime == "image/png"
                             else MP4Cover.FORMAT_JPEG))]
            audio.save()
            return True

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
