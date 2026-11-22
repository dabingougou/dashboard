"""Compact date line (with any section header tags), then each section in config order. The rest of the screen
stays empty for future sections.

Setting (dashboards.today in config.yaml):
    source_notes   false -> leave the sections' data source credits out of the
                   footer (default true; keep them on for anything public)
"""

from pathlib import Path

from dashlib.sections import header_tags_sections, layout_sections

SECTIONS = Path(__file__).resolve().parent / "sections"


def layout(data, ctx):
    elements, notes = layout_sections(SECTIONS, data, ctx)
    date = {"type": "title", "text": ctx.format_time(ctx.now, "date"), "size": 46,
            "tags": header_tags_sections(SECTIONS, data, ctx), "tags_layout": "row"}
    if ctx.settings.get("source_notes", True) is False:
        notes = []
    return {"elements": [date, *elements], "footer_note": " · ".join(notes)}
