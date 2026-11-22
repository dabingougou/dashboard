"""Fetch every section listed in config (dashboards.today.sections)."""

from pathlib import Path

from dashlib.sections import fetch_sections

SECTIONS = Path(__file__).resolve().parent / "sections"


def fetch(ctx):
    return fetch_sections(SECTIONS, ctx)
