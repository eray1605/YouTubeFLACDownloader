"""Thumbnails laden und für die Ergebniskarten aufbereiten."""

import io

import customtkinter as ctk
import requests
from PIL import Image, ImageDraw

THUMBNAIL_SIZE = (140, 79)
CORNER_RADIUS = 8


def round_image_corners(img, radius):
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    img = img.convert("RGBA")
    img.putalpha(mask)
    return img


def load_thumbnail(thumbnail_url):
    try:
        response = requests.get(thumbnail_url, timeout=5)
        img = Image.open(io.BytesIO(response.content)).resize(THUMBNAIL_SIZE, Image.LANCZOS)
        img = round_image_corners(img, CORNER_RADIUS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=THUMBNAIL_SIZE)
    except Exception:
        return None
