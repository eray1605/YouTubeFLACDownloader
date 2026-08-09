"""Eigene Tkinter-Widgets."""

import math
import tkinter as tk

from PIL import Image, ImageDraw, ImageTk


class AnimatedThemeToggle(tk.Canvas):
    TRACK_W = 56
    TRACK_H = 28
    KNOB_R = 10
    PAD = 4
    ANIM_MS = 12
    ANIM_STEPS = 14

    # Colors: (dark_track, light_track, knob)
    DARK_TRACK = "#2a2a4a"
    LIGHT_TRACK = "#87CEEB"
    KNOB_COLOR = "#ffffff"

    def __init__(self, parent, command=None, **kwargs):
        super().__init__(parent, width=self.TRACK_W, height=self.TRACK_H,
                         highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self._command = command
        self._is_light = False
        self._progress = 0.0  # 0=dark, 1=light
        self._animating = False

        # Pre-render icon images
        self._sun_img = self._create_sun_icon()
        self._moon_img = self._create_moon_icon()

        self._draw()
        self.bind("<ButtonPress-1>", self._on_click)

    def _create_moon_icon(self):
        size = 16
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Crescent moon
        draw.ellipse([1, 1, size - 2, size - 2], fill="#FFD700")
        draw.ellipse([4, 0, size + 2, size - 4], fill=(0, 0, 0, 0))
        return ImageTk.PhotoImage(img)

    def _create_sun_icon(self):
        size = 16
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        cx, cy = size // 2, size // 2
        # Rays
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + int(5 * math.cos(rad))
            y1 = cy + int(5 * math.sin(rad))
            x2 = cx + int(7 * math.cos(rad))
            y2 = cy + int(7 * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill="#FFA500", width=1)
        # Center circle
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill="#FFA500")
        return ImageTk.PhotoImage(img)

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _draw(self):
        self.delete("all")
        w, h = self.TRACK_W, self.TRACK_H
        r = h // 2
        p = self._progress

        # Interpolate track color
        dark_rgb = (42, 42, 74)
        light_rgb = (135, 206, 235)
        tr = int(dark_rgb[0] + (light_rgb[0] - dark_rgb[0]) * p)
        tg = int(dark_rgb[1] + (light_rgb[1] - dark_rgb[1]) * p)
        tb = int(dark_rgb[2] + (light_rgb[2] - dark_rgb[2]) * p)
        track_color = f"#{tr:02x}{tg:02x}{tb:02x}"

        # Track (pill shape)
        self.create_oval(0, 0, h, h, fill=track_color, outline=track_color)
        self.create_oval(w - h, 0, w, h, fill=track_color, outline=track_color)
        self.create_rectangle(r, 0, w - r, h, fill=track_color, outline=track_color)

        # Knob position
        knob_x0 = self.PAD + p * (w - 2 * self.PAD - 2 * self.KNOB_R)
        knob_cx = knob_x0 + self.KNOB_R
        knob_cy = h // 2

        # Knob shadow
        self.create_oval(knob_cx - self.KNOB_R, knob_cy - self.KNOB_R + 1,
                         knob_cx + self.KNOB_R, knob_cy + self.KNOB_R + 1,
                         fill="#888888", outline="")
        # Knob
        self.create_oval(knob_cx - self.KNOB_R, knob_cy - self.KNOB_R,
                         knob_cx + self.KNOB_R, knob_cy + self.KNOB_R,
                         fill=self.KNOB_COLOR, outline="#e0e0e0")

        # Icons (moon on left when dark, sun on right when light)
        icon_offset = 8
        # Moon icon (visible in dark mode, fades out)
        moon_alpha = 1.0 - p
        if moon_alpha > 0.1:
            self.create_image(w - icon_offset - 6, h // 2, image=self._moon_img, anchor="center")
        # Sun icon (visible in light mode, fades in)
        sun_alpha = p
        if sun_alpha > 0.1:
            self.create_image(icon_offset + 6, h // 2, image=self._sun_img, anchor="center")

    def _on_click(self, e):
        if self._animating:
            return
        self._is_light = not self._is_light
        self._animate(0)

    def _animate(self, step):
        if step > self.ANIM_STEPS:
            self._animating = False
            self._progress = 1.0 if self._is_light else 0.0
            self._draw()
            if self._command:
                self._command(self._is_light)
            return

        self._animating = True
        t = step / self.ANIM_STEPS
        eased = self._ease_in_out(t)

        if self._is_light:
            self._progress = eased
        else:
            self._progress = 1.0 - eased

        self._draw()
        self.after(self.ANIM_MS, lambda: self._animate(step + 1))

    def update_bg(self, bg):
        self.configure(bg=bg)
