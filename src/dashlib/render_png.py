"""PNG renderer for old Kindle e ink screens.

Output: 758 x 1024, 8 bit grayscale (Pillow mode "L"), no alpha, black on
white, large text. Drawing of each element is delegated to the element
registry (dashlib.elements), so this file never needs to know element types.
"""

from __future__ import annotations

import logging
import os
from datetime import tzinfo
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import elements

log = logging.getLogger(__name__)

WIDTH = 758
HEIGHT = 1024
MARGIN = 32
FOOTER_HEIGHT = 46
GAP = 18
BLACK = 0
WHITE = 255

# Named text sizes in pixels. Element dicts may use these names or an int.
SIZES = {"title": 60, "large": 46, "medium": 34, "small": 27, "footer": 24}

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/usr/share/fonts/TTF",
    "/Library/Fonts",
]


@lru_cache(maxsize=None)
def _font_path(bold: bool) -> str | None:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in _FONT_DIRS:
        p = Path(d) / name
        if p.exists():
            return str(p)
    return None


@lru_cache(maxsize=None)
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = _font_path(bold) or _font_path(False)
    if path:
        return ImageFont.truetype(path, size)
    # Pillow >= 10.1 ships a scalable built in font.
    log.debug("DejaVu Sans not found; using Pillow built in font")
    return ImageFont.load_default(size=size)


class Canvas:
    """Drawing surface handed to element PNG drawers.

    Drawers draw between x0 and x1 starting at y, then advance y.
    """

    def __init__(self, tz: tzinfo):
        self.image = Image.new("L", (WIDTH, HEIGHT), WHITE)
        self.draw = ImageDraw.Draw(self.image)
        self.tz = tz
        self.x0 = MARGIN
        self.x1 = WIDTH - MARGIN
        self.y = MARGIN
        self.bottom = HEIGHT - MARGIN - FOOTER_HEIGHT

    # ----- helpers for drawers -------------------------------------------
    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def remaining(self) -> int:
        return self.bottom - self.y

    def font(self, size: str | int = "medium", bold: bool = False):
        px = SIZES.get(size, SIZES["medium"]) if isinstance(size, str) else int(size)
        return get_font(px, bold)

    @staticmethod
    def line_height(font) -> int:
        ascent, descent = font.getmetrics()
        return int((ascent + descent) * 1.12)

    def text_width(self, text: str, font) -> float:
        return self.draw.textlength(text, font=font)

    def wrap(self, text: str, font, max_width: float) -> list[str]:
        """Greedy word wrap; very long words are split by character."""
        lines: list[str] = []
        for para in str(text).split("\n"):
            words = para.split()
            if not words:
                lines.append("")
                continue
            cur = ""
            for word in words:
                trial = f"{cur} {word}".strip()
                if self.text_width(trial, font) <= max_width:
                    cur = trial
                    continue
                if cur:
                    lines.append(cur)
                while self.text_width(word, font) > max_width and len(word) > 1:
                    cut = len(word)
                    while cut > 1 and self.text_width(word[:cut], font) > max_width:
                        cut -= 1
                    lines.append(word[:cut])
                    word = word[cut:]
                cur = word
            lines.append(cur)
        return lines

    def ellipsize(self, text: str, font, max_width: float) -> str:
        text = str(text)
        if self.text_width(text, font) <= max_width:
            return text
        while text and self.text_width(text + "…", font) > max_width:
            text = text[:-1]
        return text + "…"

    def text_block(self, text: str, size="medium", bold=False, x=None,
                   max_width=None, fill=BLACK, align="left") -> None:
        """Draw wrapped text at the cursor and advance y."""
        font = self.font(size, bold)
        x = self.x0 if x is None else x
        max_width = (self.x1 - x) if max_width is None else max_width
        lh = self.line_height(font)
        for line in self.wrap(text, font, max_width):
            lx = x
            if align == "center":
                lx = x + (max_width - self.text_width(line, font)) / 2
            elif align == "right":
                lx = x + max_width - self.text_width(line, font)
            self.draw.text((lx, self.y), line, font=font, fill=fill)
            self.y += lh

    def gap(self, px: int = GAP) -> None:
        self.y += px


def _draw_footer(canvas: Canvas, footer: dict, truncated: bool) -> None:
    d = canvas.draw
    top = HEIGHT - MARGIN - FOOTER_HEIGHT
    # Clear anything an oversized element drew into the footer zone.
    d.rectangle([0, top, WIDTH, HEIGHT], fill=WHITE)
    d.line([canvas.x0, top + 4, canvas.x1, top + 4], fill=BLACK, width=2)
    font = canvas.font("footer", bold=footer.get("stale", False))
    ty = top + 14
    text = footer.get("text", "")
    if truncated:
        text += "  (more not shown)"
    text = canvas.ellipsize(text, font, canvas.width - 16)
    if footer.get("stale"):
        # Inverted box so the stale note is unmistakable on e ink.
        w = canvas.text_width(text, font)
        lh = canvas.line_height(font)
        d.rectangle([canvas.x0, ty - 4, canvas.x0 + w + 16, ty + lh], fill=BLACK)
        d.text((canvas.x0 + 8, ty), text, font=font, fill=WHITE)
    else:
        d.text((canvas.x0, ty), text, font=font, fill=BLACK)


def render(layout: list[dict], footer: dict, tz: tzinfo) -> Image.Image:
    canvas = Canvas(tz)
    truncated = False
    for el in layout:
        if canvas.y >= canvas.bottom:
            truncated = True
            break
        etype = elements.get(el.get("type", ""))
        if etype is None:
            log.warning("unknown element type %r; drawing placeholder", el.get("type"))
            canvas.text_block(f"[unknown element: {el.get('type')}]", size="small")
        else:
            etype.png(canvas, el)
        canvas.gap()
    if canvas.y - GAP > canvas.bottom:
        truncated = True
    if truncated:
        log.warning("layout taller than the screen; content was cut off")
    _draw_footer(canvas, footer, truncated)
    return canvas.image


def write_png(image: Image.Image, path: Path) -> None:
    """Write atomically so a reader never sees a half written file."""
    assert image.mode == "L" and image.size == (WIDTH, HEIGHT)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".png.tmp")
    image.save(tmp, format="PNG", optimize=True)
    os.replace(tmp, path)
