"""Built in element types.

Each type has a PNG drawer (canvas, el) and an HTML drawer (page, el).
Element dicts (all text is plain strings; format times in the layout step):

  {"type": "title",   "text": str, "subtitle": str?, "size": int|name?}
  {"type": "banner",  "text": str}                       inverted full width label
  {"type": "text",    "text": str, "size": "small|medium|large"?, "bold": bool?}
  {"type": "kv",      "items": [[label, value], ...]}    label left, big value right
  {"type": "list",    "items": [str, ...]}
  {"type": "table",   "columns": [str, ...], "rows": [[cell, ...], ...],
                      "widths": [fraction, ...]?}
  {"type": "divider"}
  {"type": "spacer",  "height": int?}
  {"type": "stats",   "blocks": [{"value": str, "secondary": str?, "label": str?,
                                  "caption": str?, "hidden": bool?}, ...],
                      "max_size": int?}
      A row of side by side stat blocks: big value, optional secondary value
      shown in parentheses, optional short label, optional small caption.
      Hidden blocks are dropped and the visible ones share the full width.
"""

from __future__ import annotations

from html import escape

from . import register

BLACK, WHITE = 0, 255


def _s(value) -> str:
    return "" if value is None else str(value)


# ----- title ---------------------------------------------------------------
def title_png(c, el):
    c.text_block(_s(el.get("text")), size=el.get("size", "title"), bold=True)
    if el.get("subtitle"):
        c.text_block(_s(el["subtitle"]), size="small")
    c.y += 6
    c.draw.rectangle([c.x0, c.y, c.x1, c.y + 4], fill=BLACK)
    c.y += 4


def title_html(page, el):
    out = f'<h1 class="el-title">{escape(_s(el.get("text")))}</h1>'
    if el.get("subtitle"):
        out += f'<p class="el-subtitle">{escape(_s(el["subtitle"]))}</p>'
    return f'<header class="el">{out}</header>'


# ----- banner --------------------------------------------------------------
def banner_png(c, el):
    font = c.font("medium", bold=True)
    lines = c.wrap(_s(el.get("text")), font, c.width - 24)
    lh = c.line_height(font)
    h = lh * len(lines) + 16
    c.draw.rectangle([c.x0, c.y, c.x1, c.y + h], fill=BLACK)
    y = c.y + 8
    for line in lines:
        x = c.x0 + (c.width - c.text_width(line, font)) / 2
        c.draw.text((x, y), line, font=font, fill=WHITE)
        y += lh
    c.y += h


def banner_html(page, el):
    return f'<div class="el el-banner">{escape(_s(el.get("text")))}</div>'


# ----- text ----------------------------------------------------------------
def text_png(c, el):
    c.text_block(_s(el.get("text")), size=el.get("size", "medium"),
                 bold=bool(el.get("bold")))


def text_html(page, el):
    size = el.get("size", "medium")
    cls = f"el el-text {escape(str(size))}" + (" bold" if el.get("bold") else "")
    body = "<br>".join(escape(line) for line in _s(el.get("text")).split("\n"))
    return f'<p class="{cls}">{body}</p>'


# ----- kv ------------------------------------------------------------------
def kv_png(c, el):
    lfont = c.font("medium")
    vfont = c.font("large", bold=True)
    items = el.get("items") or []
    for i, (label, value) in enumerate(items):
        value = c.ellipsize(_s(value), vfont, c.width * 0.6)
        vw = c.text_width(value, vfont)
        vh = c.line_height(vfont)
        label_lines = c.wrap(_s(label), lfont, c.width - vw - 20)
        lh = c.line_height(lfont)
        row_h = max(vh, lh * len(label_lines))
        # Vertically centre the label against the larger value text.
        ly = c.y + max(0, (vh - lh * len(label_lines)) // 2)
        for line in label_lines:
            c.draw.text((c.x0, ly), line, font=lfont, fill=BLACK)
            ly += lh
        c.draw.text((c.x1 - vw, c.y), value, font=vfont, fill=BLACK)
        c.y += row_h
        if i < len(items) - 1:
            c.y += 4
            c.draw.line([c.x0, c.y, c.x1, c.y], fill=BLACK, width=1)
            c.y += 8


def kv_html(page, el):
    rows = "".join(
        f"<tr><th>{escape(_s(k))}</th><td>{escape(_s(v))}</td></tr>"
        for k, v in (el.get("items") or [])
    )
    return f'<table class="el el-kv">{rows}</table>'


# ----- list ----------------------------------------------------------------
def list_png(c, el):
    font = c.font(el.get("size", "medium"))
    lh = c.line_height(font)
    bullet = "•"
    indent = c.text_width(bullet + "  ", font)
    for item in el.get("items") or []:
        c.draw.text((c.x0, c.y), bullet, font=font, fill=BLACK)
        for line in c.wrap(_s(item), font, c.width - indent):
            c.draw.text((c.x0 + indent, c.y), line, font=font, fill=BLACK)
            c.y += lh
        c.y += 4


def list_html(page, el):
    items = "".join(f"<li>{escape(_s(i))}</li>" for i in (el.get("items") or []))
    return f'<ul class="el el-list">{items}</ul>'


# ----- table ---------------------------------------------------------------
def _col_widths(c, el, ncols):
    widths = el.get("widths")
    if not widths or len(widths) != ncols:
        widths = [1] * ncols
    total = float(sum(widths))
    return [c.width * w / total for w in widths]


def table_png(c, el):
    cols = [_s(x) for x in (el.get("columns") or [])]
    rows = el.get("rows") or []
    ncols = len(cols) or max((len(r) for r in rows), default=0)
    if not ncols:
        return
    widths = _col_widths(c, el, ncols)
    hfont = c.font("small", bold=True)
    font = c.font(el.get("size", "small"))
    pad = 10

    def draw_row(cells, f):
        x = c.x0
        for i in range(ncols):
            text = _s(cells[i]) if i < len(cells) else ""
            c.draw.text((x, c.y), c.ellipsize(text, f, widths[i] - pad), font=f, fill=BLACK)
            x += widths[i]
        c.y += c.line_height(f)

    if cols:
        draw_row(cols, hfont)
        c.draw.rectangle([c.x0, c.y, c.x1, c.y + 2], fill=BLACK)
        c.y += 8
    for r in rows:
        if c.y >= c.bottom:
            break
        draw_row(r, font)
        c.y += 4


def table_html(page, el):
    cols = el.get("columns") or []
    head = "".join(f"<th>{escape(_s(x))}</th>" for x in cols)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(_s(x))}</td>" for x in r) + "</tr>"
        for r in (el.get("rows") or [])
    )
    thead = f"<thead><tr>{head}</tr></thead>" if cols else ""
    return f'<div class="el table-wrap"><table class="el-table">{thead}<tbody>{body}</tbody></table></div>'


# ----- divider / spacer -----------------------------------------------------
def divider_png(c, el):
    c.y += 4
    c.draw.rectangle([c.x0, c.y, c.x1, c.y + 2], fill=BLACK)
    c.y += 6


def divider_html(page, el):
    return '<hr class="el el-divider">'


def spacer_png(c, el):
    c.y += int(el.get("height", 20))


def spacer_html(page, el):
    return f'<div style="height:{int(el.get("height", 20))}px"></div>'


# ----- stats ---------------------------------------------------------------
STATS_MIN_VALUE_PX = 28


def _visible_blocks(el):
    return [b for b in (el.get("blocks") or []) if isinstance(b, dict) and not b.get("hidden")]


def _fit_value(c, value, secondary, width, max_px):
    """Largest value size where 'value (secondary)' fits in width."""
    px = max_px
    while True:
        vf = c.font(px, bold=True)
        sf = c.font(max(22, round(px * 0.5)))
        vw = c.text_width(value, vf)
        sw = (c.text_width(f"({secondary})", sf) + px * 0.2) if secondary else 0
        if vw + sw <= width or px <= STATS_MIN_VALUE_PX:
            return vf, sf, vw, sw
        px -= 2


def _fit_label(c, text, width):
    for px in (34, 30, 27, 24):
        f = c.font(px)
        if c.text_width(text, f) <= width:
            return f, text
    f = c.font(24)
    return f, c.ellipsize(text, f, width)


def stats_png(c, el):
    blocks = _visible_blocks(el)
    if not blocks:
        return
    n = len(blocks)
    bw = c.width / n
    pad = 10
    inner = bw - 2 * pad
    max_px = int(el.get("max_size", 96))

    fitted = []
    for b in blocks:
        value, sec = _s(b.get("value")), _s(b.get("secondary"))
        vf, sf, vw, sw = _fit_value(c, value, sec, inner, max_px)
        label = _fit_label(c, _s(b.get("label")), inner) if b.get("label") else None
        fitted.append((b, value, sec, vf, sf, vw, sw, label))

    # Shared rows so values, labels and captions line up across blocks.
    ascent = max(f[3].getmetrics()[0] for f in fitted)
    descent = max(f[3].getmetrics()[1] for f in fitted)
    baseline = c.y + ascent
    row_y = baseline + descent + 6
    label_h = max((c.line_height(f[7][0]) for f in fitted if f[7]), default=0)
    cfont = c.font("footer")
    caption_h = c.line_height(cfont) if any(f[0].get("caption") for f in fitted) else 0

    for i, (b, value, sec, vf, sf, vw, sw, label) in enumerate(fitted):
        left = c.x0 + i * bw
        cx = left + bw / 2
        x = cx - (vw + sw) / 2
        c.draw.text((x, baseline), value, font=vf, fill=BLACK, anchor="ls")
        if sec:
            c.draw.text((x + vw + (sw - c.text_width(f"({sec})", sf)), baseline),
                        f"({sec})", font=sf, fill=BLACK, anchor="ls")
        y = row_y
        if label:
            c.draw.text((cx, y), label[1], font=label[0], fill=BLACK, anchor="ma")
        y += label_h
        if b.get("caption"):
            cap = c.ellipsize(_s(b["caption"]), cfont, inner)
            c.draw.text((cx, y), cap, font=cfont, fill=BLACK, anchor="ma")
        if i > 0:
            c.draw.line([left, c.y + 4, left, row_y + label_h + caption_h - 4], fill=BLACK, width=2)
    c.y = row_y + label_h + caption_h


def stats_html(page, el):
    parts = []
    for b in _visible_blocks(el):
        inner = f'<div class="v">{escape(_s(b.get("value")))}'
        if b.get("secondary"):
            inner += f' <span class="s">({escape(_s(b["secondary"]))})</span>'
        inner += "</div>"
        if b.get("label"):
            inner += f'<div class="l">{escape(_s(b["label"]))}</div>'
        if b.get("caption"):
            inner += f'<div class="c">{escape(_s(b["caption"]))}</div>'
        parts.append(f'<div class="b">{inner}</div>')
    return f'<div class="el el-stats">{"".join(parts)}</div>' if parts else ""


register("title", png=title_png, html=title_html)
register("banner", png=banner_png, html=banner_html)
register("text", png=text_png, html=text_html)
register("kv", png=kv_png, html=kv_html)
register("list", png=list_png, html=list_html)
register("table", png=table_png, html=table_html)
register("divider", png=divider_png, html=divider_html)
register("spacer", png=spacer_png, html=spacer_html)
register("stats", png=stats_png, html=stats_html)
