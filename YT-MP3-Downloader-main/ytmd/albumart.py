"""Echtes Albumcover über öffentliche Musikdatenbanken finden.

Nur nötig, wenn der Playlist-Export keine Bild-URL mitliefert. Gesendet werden
ausschließlich Interpret und Albumname – die Dienste brauchen keine Anmeldung.

Zwei Quellen, weil keine allein reicht: iTunes trifft genauer, hat aber Lücken
(Nirvanas "Incesticide" kennt es nicht); Deezer ist vollständiger, liefert aber
auch mal eine Coverversion fremder Künstler ("The Cover Kid" statt Drake).
Deshalb wird bei jedem Treffer geprüft, ob der Interpret überhaupt passt.
"""

import threading

import requests

from ytmd.youtube import normalize

TIMEOUT = 15

_cache = {}
_lock = threading.Lock()


def artist_matches(gesucht, gefunden):
    """Grober Abgleich der Interpretennamen – gegen fremde Coverversionen."""
    a = normalize(gesucht).replace(" ", "")
    b = normalize(gefunden).replace(" ", "")
    if not a or not b:
        return False
    return a in b or b in a


def _itunes(artist, album):
    response = requests.get(
        "https://itunes.apple.com/search",
        params={"term": f"{artist} {album}", "entity": "album", "limit": 1},
        timeout=TIMEOUT)
    treffer = (response.json().get("results") or [None])[0]
    if not treffer:
        return None, ""
    # Die API liefert 100x100; die Größe steckt im Dateinamen.
    url = (treffer.get("artworkUrl100") or "").replace("100x100bb", "600x600bb")
    return url or None, treffer.get("artistName", "")


def _deezer(artist, album):
    response = requests.get(
        "https://api.deezer.com/search/album",
        params={"q": f"{artist} {album}", "limit": 1}, timeout=TIMEOUT)
    treffer = (response.json().get("data") or [None])[0]
    if not treffer:
        return None, ""
    return treffer.get("cover_xl") or treffer.get("cover_big"), \
        treffer.get("artist", {}).get("name", "")


QUELLEN = (_itunes, _deezer)


def find_cover_url(artist, album):
    """URL des Albumcovers oder None. Ergebnis wird je Album gemerkt."""
    if not artist or not album:
        return None

    schluessel = (normalize(artist), normalize(album))
    with _lock:
        if schluessel in _cache:
            return _cache[schluessel]

    url = None
    for quelle in QUELLEN:
        try:
            treffer, gefundener_artist = quelle(artist, album)
        except Exception:
            continue
        if treffer and artist_matches(artist, gefundener_artist):
            url = treffer
            break

    with _lock:
        _cache[schluessel] = url
    return url
