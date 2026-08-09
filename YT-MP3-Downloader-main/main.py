"""YouTube Music Downloader – Startpunkt.

Der eigentliche Code liegt im Paket `ytmd` (siehe ytmd/__init__.py).
"""

import os
import sys

import customtkinter as ctk

# Beim Start als Skript aus einem anderen Arbeitsverzeichnis heraus muss der
# Ordner mit dem Paket `ytmd` im Suchpfad liegen.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ytmd.app import App  # noqa: E402  (erst nach dem sys.path-Eintrag möglich)


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    App().mainloop()


if __name__ == "__main__":
    main()
