"""Einlesen exportierter Playlists (Spotify-API, Exportify & Co.) als JSON oder CSV.

Die Exportwerkzeuge benutzen alle eigene Feldnamen; hier wird das auf ein
einheitliches `Track`-Objekt heruntergebrochen.
"""

import csv
import json
import os
import re
from dataclasses import dataclass
from typing import Optional

TITLE_KEYS = ("track name", "title", "name", "song", "track_name", "trackname", "track")
ARTIST_KEYS = ("artist name(s)", "artist names", "artist name", "artists", "artist",
               "album artist", "artist_name", "artistname")
ALBUM_KEYS = ("album name", "album", "album_name")
DURATION_KEYS = ("track duration (ms)", "duration (ms)", "duration_ms", "duration ms",
                 "durationms", "track duration", "duration", "length", "time")
IMAGE_KEYS = ("album image url", "image url", "cover url", "artwork url",
              "images", "image", "cover", "artwork", "thumbnail")
DATE_KEYS = ("album release date", "release date", "released", "year",
             "release_date", "date")

# Schlüssel, unter denen die Trackliste in einer JSON-Datei stecken kann
LIST_KEYS = ("items", "tracks", "songs", "playlist", "entries", "data")
NAME_KEYS = ("name", "playlist_name", "playlistName", "title")

# "(feat. Monk, Big Pat)" – auf YouTube steht das selten mit im Titel
FEAT_SUFFIX = re.compile(r"\s*[\(\[]\s*(feat|ft|with)\b[^)\]]*[\)\]]", re.I)
# Dieselbe Angabe ohne Klammern: "... lol - feat. Rio Santana, Judah"
FEAT_DASH = re.compile(r"\s+[-–]\s+(feat|ft|with)\b.*$", re.I)
# "- Remastered 2009", "- Single Version", "- Radio Edit", ...
VERSION_SUFFIX = re.compile(
    r"\s+-\s+(\d{4}\s+)?(remaster|remastered|remaster\s+\d{4}|single version|"
    r"album version|radio edit|mono version|stereo version|bonus\s?track|"
    r"deluxe( edition)?|extended( version)?|edit|version)\b.*$", re.I)


@dataclass
class Track:
    """Ein Song aus der Playlist – unabhängig vom Ursprungsformat."""

    title: str
    artist: str = ""
    album: str = ""
    duration: Optional[float] = None  # Sekunden
    image_url: str = ""               # Cover aus dem Export
    released: str = ""                # Erscheinungsdatum, z. B. "1991-09-24"

    @property
    def label(self):
        """Anzeigename für Statuszeile und Dateiname.

        Bewusst der ungekürzte Originalname: Er bildet den Dateinamen, und der
        muss über Läufe hinweg gleich bleiben, damit fertige Songs wiedererkannt
        werden.
        """
        return f"{self.artist} - {self.title}" if self.artist else self.title

    @property
    def artist_names(self):
        """Alle beteiligten Interpreten einzeln – zum Abgleich mit dem Treffer."""
        names = re.split(r"[;,]|\s&\s|\sfeat\.?\s|\sft\.?\s", self.artist, flags=re.I)
        return [n.strip() for n in names if n.strip()]

    @property
    def primary_artist(self):
        """Haupt-Interpret. Bei "BHZ;Monk;Big Pat" ist die volle Liste als
        Suchbegriff unbrauchbar."""
        parts = [p.strip() for p in self.artist.split(";") if p.strip()]
        return parts[0] if parts else self.artist

    @property
    def clean_title(self):
        """Titel ohne Spotify-Zusätze wie "- Remastered 2009" oder "(feat. X)"."""
        title = FEAT_SUFFIX.sub("", self.title)
        title = FEAT_DASH.sub("", title)
        title = VERSION_SUFFIX.sub("", title)
        return title.strip() or self.title

    @property
    def search_query(self):
        return f"{self.primary_artist} {self.clean_title}".strip()


def _lower_keys(d):
    return {str(k).strip().lower(): v for k, v in d.items()}


def _first_value(d, keys):
    for k in keys:
        value = d.get(k)
        if value not in (None, "", [], {}):
            return k, value
    return None, None


def _names_to_text(value):
    """Spotify stores artists as list of dicts, exports as plain string."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("name", "")).strip()
    if isinstance(value, list):
        names = [_names_to_text(v) for v in value]
        return ", ".join(n for n in names if n)
    return ""


def _parse_duration(key, value):
    """Return seconds, or None. Key name decides if a number means ms."""
    if isinstance(value, str):
        value = value.strip()
        if re.fullmatch(r"\d+:\d{1,2}(:\d{1,2})?", value):
            parts = [int(p) for p in value.split(":")]
            seconds = 0
            for p in parts:
                seconds = seconds * 60 + p
            return seconds
        try:
            value = float(value)
        except ValueError:
            return None
    if not isinstance(value, (int, float)):
        return None
    if "ms" in key or value > 3600:  # ms-Feld oder unrealistisch lang für Sekunden
        value = value / 1000.0
    return value if value > 0 else None


def _largest_image(images):
    """Aus Spotifys [{"url":..., "width":...}, ...] das größte Bild wählen."""
    best, best_width = "", -1
    for image in images:
        if isinstance(image, str) and image.startswith("http"):
            return image
        if isinstance(image, dict):
            url = image.get("url", "")
            width = image.get("width") or 0
            if url and width > best_width:
                best, best_width = url, width
    return best


def _find_duration(d):
    """Dauer-Feld suchen. Die Exportwerkzeuge benennen es unterschiedlich
    ("Duration (ms)", "Track Duration (ms)", ...), deshalb zur Not über den
    Namensbestandteil statt über eine feste Liste."""
    key, value = _first_value(d, DURATION_KEYS)
    if key:
        return key, value
    for key, value in d.items():
        if ("duration" in key or "length" in key) and value not in (None, "", [], {}):
            return key, value
    return None, None


def _extract_image(d):
    """Cover-URL finden – Exportify liefert sie flach, die API verschachtelt."""
    _, value = _first_value(d, IMAGE_KEYS)
    if isinstance(value, str) and value.startswith("http"):
        return value
    if isinstance(value, list):
        return _largest_image(value)

    album = d.get("album")
    if isinstance(album, dict) and isinstance(album.get("images"), list):
        return _largest_image(album["images"])
    return ""


def _extract_track(obj):
    """Turn one entry of an arbitrary playlist export into a Track."""
    if isinstance(obj, str):
        return Track(title=obj.strip()) if obj.strip() else None
    if not isinstance(obj, dict):
        return None

    # Spotify-API-Wrapper: {"track": {...}}
    if isinstance(obj.get("track"), dict):
        obj = obj["track"]

    d = _lower_keys(obj)

    _, title = _first_value(d, TITLE_KEYS)
    title = title.strip() if isinstance(title, str) else _names_to_text(title)
    if not title:
        return None

    _, artist = _first_value(d, ARTIST_KEYS)
    _, album = _first_value(d, ALBUM_KEYS)
    dur_key, dur_value = _find_duration(d)

    return Track(
        title=title,
        artist=_names_to_text(artist),
        album=_names_to_text(album),
        duration=_parse_duration(dur_key, dur_value) if dur_key else None,
        image_url=_extract_image(d),
        released=str(_first_value(d, DATE_KEYS)[1] or "").strip(),
    )


def _find_entries(data):
    """Find the track list inside the various export shapes."""
    if isinstance(data, list):
        return "", data
    if not isinstance(data, dict):
        return "", []

    name = ""
    for key in NAME_KEYS:
        if isinstance(data.get(key), str):
            name = data[key]
            break

    for key in LIST_KEYS:
        value = data.get(key)
        if isinstance(value, list):
            return name, value
        if isinstance(value, dict):
            sub_name, entries = _find_entries(value)
            if entries:
                return name or sub_name, entries
    return name, []


def parse_playlist_file(path):
    """Read a Spotify export (JSON or CSV) -> (playlist name, [Track])."""
    fallback_name = os.path.splitext(os.path.basename(path))[0]

    if os.path.splitext(path)[1].lower() == ".csv":
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            entries = list(csv.DictReader(f))
        name = fallback_name
    else:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        name, entries = _find_entries(data)
        name = name or fallback_name

    tracks = []
    for entry in entries:
        track = _extract_track(entry)
        if track:
            tracks.append(track)
    return name, tracks
