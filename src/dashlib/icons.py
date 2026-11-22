"""Small icon registry, drawn with plain shapes so icons stay crisp on e ink.

Each icon is one function that draws onto a "pen" in unit space: the icon box
is 1.0 high and ASPECT wide. Two pens exist, so one definition gives both
outputs:

    png(name, height_px) -> PIL "L" image (black on white), or None
    svg(name, height_px, title="") -> inline SVG string, or ""

Register more icons with  register(name, draw_fn, aspect).
Built in names: sun, partly_cloudy, cloud, fog, drizzle, rain, snow, thunder,
wind, drop.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from html import escape
from typing import Callable

from PIL import Image, ImageDraw

SUPERSAMPLE = 4          # draw large, then downscale for smooth edges
STROKE = 0.075           # default stroke width as a fraction of icon height
MIN_STROKE_PX = 3        # never thinner than this in the final image


@dataclass(frozen=True)
class Icon:
    name: str
    draw: Callable
    aspect: float  # width / height


_ICONS: dict[str, Icon] = {}


def register(name: str, draw: Callable, aspect: float = 1.0) -> None:
    _ICONS[name] = Icon(name, draw, float(aspect))


def names() -> list[str]:
    return sorted(_ICONS)


def aspect(name: str) -> float | None:
    icon = _ICONS.get(name or "")
    return icon.aspect if icon else None


# ----- pens ----------------------------------------------------------------
class _PilPen:
    def __init__(self, draw: ImageDraw.ImageDraw, scale: float, stroke: float):
        self.d, self.k, self.stroke = draw, scale, stroke

    def _p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def _w(self, w):
        return max(1, round((w or self.stroke) * self.k))

    def line(self, pts, w=None):
        pts, width = self._p(pts), self._w(w)
        self.d.line(pts, fill=0, width=width, joint="curve")
        r = width / 2
        for x, y in (pts[0], pts[-1]):  # round caps
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=0)

    def disc(self, cx, cy, r, white=False):
        k = self.k
        self.d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k],
                       fill=255 if white else 0)

    def ring(self, cx, cy, r, w=None):
        k = self.k
        self.d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k],
                       outline=0, width=self._w(w))

    def arc(self, cx, cy, r, start, end, w=None):
        """Clockwise (screen) arc from start to end degrees, 0 = 3 o'clock."""
        k, width = self.k, self._w(w)
        rr = r + (w or self.stroke) / 2  # Pillow draws the width inward
        self.d.arc([(cx - rr) * k, (cy - rr) * k, (cx + rr) * k, (cy + rr) * k],
                   start, end, fill=0, width=width)
        for a in (start, end):
            x, y = (cx + r * math.cos(math.radians(a))) * k, (cy + r * math.sin(math.radians(a))) * k
            self.d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=0)

    def polygon(self, pts, white=False):
        self.d.polygon(self._p(pts), fill=255 if white else 0)

    def rect(self, x0, y0, x1, y1, white=False):
        k = self.k
        self.d.rectangle([x0 * k, y0 * k, x1 * k, y1 * k], fill=255 if white else 0)


class _SvgPen:
    FG, BG = "var(--fg,#000)", "var(--bg,#fff)"

    def __init__(self, stroke: float):
        self.stroke, self.parts = stroke, []

    @staticmethod
    def _n(v):
        return f"{v:.4f}".rstrip("0").rstrip(".")

    def _sw(self, w):
        return self._n(w or self.stroke)

    def line(self, pts, w=None):
        p = " ".join(f"{self._n(x)},{self._n(y)}" for x, y in pts)
        self.parts.append(f'<polyline points="{p}" fill="none" stroke="{self.FG}" '
                          f'stroke-width="{self._sw(w)}" stroke-linecap="round" stroke-linejoin="round"/>')

    def disc(self, cx, cy, r, white=False):
        self.parts.append(f'<circle cx="{self._n(cx)}" cy="{self._n(cy)}" r="{self._n(r)}" '
                          f'fill="{self.BG if white else self.FG}"/>')

    def ring(self, cx, cy, r, w=None):
        self.parts.append(f'<circle cx="{self._n(cx)}" cy="{self._n(cy)}" r="{self._n(r)}" '
                          f'fill="none" stroke="{self.FG}" stroke-width="{self._sw(w)}"/>')

    def arc(self, cx, cy, r, start, end, w=None):
        a0, a1 = math.radians(start), math.radians(end)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        large = 1 if (end - start) % 360 > 180 else 0
        n = self._n
        self.parts.append(f'<path d="M{n(x0)},{n(y0)} A{n(r)},{n(r)} 0 {large} 1 {n(x1)},{n(y1)}" '
                          f'fill="none" stroke="{self.FG}" stroke-width="{self._sw(w)}" stroke-linecap="round"/>')

    def polygon(self, pts, white=False):
        p = " ".join(f"{self._n(x)},{self._n(y)}" for x, y in pts)
        self.parts.append(f'<polygon points="{p}" fill="{self.BG if white else self.FG}"/>')

    def rect(self, x0, y0, x1, y1, white=False):
        n = self._n
        self.parts.append(f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(x1 - x0)}" height="{n(y1 - y0)}" '
                          f'fill="{self.BG if white else self.FG}"/>')


# ----- rendering -------------------------------------------------------------
def _stroke_for(height_px: float) -> float:
    """Stroke width in unit space (icon height = 1)."""
    return max(STROKE, MIN_STROKE_PX / max(height_px, 1))


@lru_cache(maxsize=64)
def png(name: str, height_px: int) -> Image.Image | None:
    icon = _ICONS.get(name or "")
    if icon is None or height_px <= 0:
        return None
    h = int(height_px)
    w = max(1, round(h * icon.aspect))
    k = h * SUPERSAMPLE
    big = Image.new("L", (w * SUPERSAMPLE, h * SUPERSAMPLE), 255)
    icon.draw(_PilPen(ImageDraw.Draw(big), k, _stroke_for(h)), icon.aspect)
    return big.resize((w, h), Image.LANCZOS)


def svg(name: str, height_px: int, title: str = "") -> str:
    icon = _ICONS.get(name or "")
    if icon is None:
        return ""
    pen = _SvgPen(_stroke_for(height_px))
    icon.draw(pen, icon.aspect)
    w = round(height_px * icon.aspect)
    label = (f' role="img" aria-label="{escape(title)}"><title>{escape(title)}</title>'
             if title else ' aria-hidden="true">')
    return (f'<svg class="icon" width="{w}" height="{int(height_px)}" '
            f'viewBox="0 0 {pen._n(icon.aspect)} 1"{label}{"".join(pen.parts)}</svg>')


# ----- shapes ----------------------------------------------------------------
_CLOUD_PARTS = [(-0.45, 0.15, 0.38), (0.0, -0.1, 0.5), (0.5, 0.15, 0.36)]
_CLOUD_W, _CLOUD_H = 1.69, 1.13  # extent in units of the half width "s"


def _cloud(p, x0, y0, x1, y1):
    """Outlined cloud with a white inside, fitted into the given box."""
    s = min((x1 - x0) / _CLOUD_W, (y1 - y0) / _CLOUD_H)
    cx = (x0 + x1) / 2 - 0.015 * s
    cy = (y0 + y1) / 2 + 0.035 * s
    w = p.stroke
    for ox, oy, r in _CLOUD_PARTS:
        p.disc(cx + ox * s, cy + oy * s, r * s)
    p.rect(cx - 0.45 * s, cy + 0.1 * s, cx + 0.5 * s, cy + 0.53 * s)
    for ox, oy, r in _CLOUD_PARTS:
        p.disc(cx + ox * s, cy + oy * s, r * s - w, white=True)
    p.rect(cx - 0.45 * s, cy + 0.1 * s, cx + 0.5 * s, cy + 0.53 * s - w, white=True)


def _sun_shape(p, cx, cy, r, ray_in, ray_out, w=None):
    p.ring(cx, cy, r, w)
    for i in range(8):
        a = i * math.pi / 4
        c, s = math.cos(a), math.sin(a)
        p.line([(cx + c * ray_in, cy + s * ray_in), (cx + c * ray_out, cy + s * ray_out)], w)


def sun(p, a):
    cx, cy = a / 2, 0.5
    _sun_shape(p, cx, cy, 0.2, 0.32, 0.46)


def cloud(p, a):
    _cloud(p, 0.02, 0.12, a - 0.02, 0.9)


def partly_cloudy(p, a):
    # Sun peeking out behind the upper right of a large cloud.
    _sun_shape(p, a * 0.7, 0.32, 0.16, 0.24, 0.31)
    _cloud(p, 0.0, 0.3, a * 0.9, 1.0)


def _cloud_top(p, a):
    _cloud(p, 0.04, 0.02, a - 0.04, 0.6)


def fog(p, a):
    _cloud_top(p, a)
    p.line([(0.12 * a, 0.75), (0.88 * a, 0.75)])
    p.line([(0.22 * a, 0.92), (0.78 * a, 0.92)])


def _streaks(p, a, length, w=None):
    for x in (0.3, 0.5, 0.7):
        x0 = x * a
        p.line([(x0, 0.7), (x0 - 0.06, 0.7 + length)], w)


def drizzle(p, a):
    _cloud_top(p, a)
    for x, y in ((0.3, 0.74), (0.5, 0.86), (0.7, 0.74), (0.4, 0.96), (0.62, 0.96)):
        p.disc(x * a, y, 0.045)


def rain(p, a):
    _cloud_top(p, a)
    _streaks(p, a, 0.25)


def snow(p, a):
    _cloud_top(p, a)
    for x, y in ((0.3, 0.76), (0.5, 0.9), (0.7, 0.76)):
        r = 0.07
        for ang in (0, 60, 120):
            c, s = math.cos(math.radians(ang)) * r, math.sin(math.radians(ang)) * r
            p.line([(x * a - c, y - s), (x * a + c, y + s)], p.stroke * 0.7)


def thunder(p, a):
    _cloud_top(p, a)
    cx = a / 2
    p.polygon([(cx + 0.06, 0.55), (cx - 0.14, 0.8), (cx - 0.01, 0.8),
               (cx - 0.08, 1.0), (cx + 0.16, 0.72), (cx + 0.03, 0.72), (cx + 0.1, 0.55)])


def wind(p, a):
    w = p.stroke * 1.3
    # (y, length as fraction of width, curl radius, curl up?)
    for y, frac, r, up in ((0.3, 0.6, 0.12, True), (0.53, 0.85, 0.12, True), (0.76, 0.55, 0.1, False)):
        x0, xe = 0.03, frac * a
        p.line([(x0, y), (xe, y)], w)
        # Arcs run clockwise on screen (0 = right, 90 = bottom). The line meets
        # the curl at its bottom (curl up) or top (curl down).
        if up:
            p.arc(xe, y - r, r, 180, 450, w)   # left, top, right, bottom
        else:
            p.arc(xe, y + r, r, 270, 540, w)   # top, right, bottom, left


def drop(p, a):
    # A disc with a point on top; the sides are tangent to the disc.
    k = 2.4                                   # apex distance in radii
    r = min(0.96 / (1 + k), a / 2 * 0.96)
    cx, cc = a / 2, 0.98 - r
    ty, tx = cc - r / k, r * math.sqrt(1 - 1 / k ** 2)
    p.polygon([(cx, cc - k * r), (cx - tx, ty), (cx + tx, ty)])
    p.disc(cx, cc, r)


register("sun", sun, 1.0)
register("cloud", cloud, 1.4)
register("partly_cloudy", partly_cloudy, 1.3)
register("fog", fog, 1.3)
register("drizzle", drizzle, 1.3)
register("rain", rain, 1.3)
register("snow", snow, 1.3)
register("thunder", thunder, 1.3)
register("wind", wind, 1.6)
register("drop", drop, 0.6)
