"""Big date line, then each section in config order. The rest of the screen
stays empty for future sections."""

from pathlib import Path

from dashlib.sections import layout_sections

SECTIONS = Path(__file__).resolve().parent / "sections"


def layout(data, ctx):
    elements, notes = layout_sections(SECTIONS, data, ctx)
    date = {"type": "title", "text": ctx.format_time(ctx.now, "date"), "size": 84}
    return {"elements": [date, *elements], "footer_note": " · ".join(notes)}
