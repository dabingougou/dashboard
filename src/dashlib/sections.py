"""Helpers for dashboards built from independent sections.

A section is a Python file <sections_dir>/<name>.py that defines:

    fetch(config) -> plain JSON data
        config is the section's own block from config.yaml
        (dashboards.<dashboard>.<section>), plus "timezone" (IANA name of the
        configured display timezone) if the block doesn't set one.
    layout(data, ctx) -> list of element dicts
    FOOTER_NOTE = "..."   optional, e.g. a data source attribution

Which sections run, and in which order, comes from the dashboard's
`sections:` list in config.yaml. Sections don't know about each other, so new
ones can be added without touching existing ones.

If any section's fetch raises, the whole fetch fails and the runner shows the
dashboard's last good data with a "stale since" note.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import ModuleType

from .registry import load_file_module

_NAME_RE = re.compile(r"^[a-z0-9_]+$")


def section_names(settings: dict) -> list[str]:
    names = settings.get("sections") or []
    if not isinstance(names, list):
        raise ValueError("'sections' must be a list of section names")
    for n in names:
        if not isinstance(n, str) or not _NAME_RE.match(n):
            raise ValueError(f"invalid section name {n!r}")
    return names


def load_section(sections_dir: Path, name: str) -> ModuleType:
    path = sections_dir / f"{name}.py"
    if not path.is_file():
        raise ValueError(f"unknown section {name!r}: {path} does not exist")
    mod_name = f"dashsection_{sections_dir.parent.name.replace('-', '_')}_{name}"
    return load_file_module(path, mod_name)


def fetch_sections(sections_dir: Path, ctx) -> dict:
    """Run fetch() of every configured section. Returns plain data:
    {"sections": [{"name": str, "data": ...}, ...]}"""
    out = []
    for name in section_names(ctx.settings):
        config = dict(ctx.settings.get(name) or {})
        config.setdefault("timezone", getattr(ctx.tz, "key", "UTC"))
        out.append({"name": name, "data": load_section(sections_dir, name).fetch(config)})
    return {"sections": out}


def layout_sections(sections_dir: Path, data: dict, ctx) -> tuple[list[dict], list[str]]:
    """Run layout() of every section in data. Returns (elements, footer_notes)."""
    elements: list[dict] = []
    notes: list[str] = []
    for sec in data.get("sections") or []:
        mod = load_section(sections_dir, sec["name"])
        elements.extend(mod.layout(sec["data"], ctx))
        note = getattr(mod, "FOOTER_NOTE", "")
        if note and note not in notes:
            notes.append(note)
    return elements, notes
