"""Pluggable layout element registry.

A layout is a list of dicts, each with a "type" key. Every type name maps to
two drawers:

    png(canvas, element)  -> None   draw onto a render_png.Canvas, advancing canvas.y
    html(page, element)   -> str    return an HTML fragment (escape all text!)

Register new types with:

    from dashlib.elements import register
    register("chart", png=draw_chart_png, html=draw_chart_html)

A dashboard can ship its own types
in dashboards/<name>/elements.py; the runner imports that file automatically
before rendering. Nothing in the runner or renderers needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

PngDrawer = Callable[..., None]
HtmlDrawer = Callable[..., str]


@dataclass(frozen=True)
class ElementType:
    name: str
    png: PngDrawer
    html: HtmlDrawer


_REGISTRY: dict[str, ElementType] = {}


def register(name: str, *, png: PngDrawer, html: HtmlDrawer, replace: bool = False) -> None:
    if not replace and name in _REGISTRY:
        raise ValueError(f"element type {name!r} is already registered")
    _REGISTRY[name] = ElementType(name, png, html)


def get(name: str) -> ElementType | None:
    return _REGISTRY.get(name)


def names() -> list[str]:
    return sorted(_REGISTRY)


# Register the built in types on import.
from . import builtin  # noqa: E402,F401
