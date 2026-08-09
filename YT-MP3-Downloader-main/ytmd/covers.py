"""Cover-Bilder besorgen.

Bevorzugt das Bild aus dem Spotify-Export, sonst das Vorschaubild des YouTube-
Treffers. Eingebettet wird es dann von `tags.py`.
"""

import io
import threading

import requests
from PIL import Image

TIMEOUT = 15
MAX_BYTES = 4 * 1024 * 1024  # Cover sind klein; alles Größere ist verdächtig

# In Cover-Feldern von ID3/FLAC sind praktisch nur diese beiden Formate brauchbar
SUPPORTED = ("JPEG", "PNG")

_cache = {}
_lock = threading.Lock()


def to_supported(data):
    """Nicht-JPEG/PNG nach JPEG wandeln.

    YouTube liefert unter ".jpg"-Adressen oft WebP aus. Das lässt sich zwar
    speichern, aber kaum ein Player zeigt WebP-Cover an – deshalb umwandeln.
    Gibt None zurück, wenn es gar kein lesbares Bild ist.
    """
    try:
        image = Image.open(io.BytesIO(data))
        if image.format in SUPPORTED:
            return data
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, "JPEG", quality=90)
        return buffer.getvalue()
    except Exception:
        return None


def fetch_cover(url):
    """Bilddaten laden. None, wenn es nicht klappt.

    Songs desselben Albums teilen sich die URL, deshalb wird gemerkt, was schon
    geholt wurde – das spart bei einer langen Playlist hunderte Abrufe.
    """
    if not url:
        return None

    with _lock:
        if url in _cache:
            return _cache[url]

    image = None
    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.content
        if data and len(data) <= MAX_BYTES:
            image = to_supported(data)
    except Exception:
        image = None

    with _lock:
        _cache[url] = image
    return image
