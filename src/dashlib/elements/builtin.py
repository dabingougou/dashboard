"""Built in element types.

Each type has a PNG drawer (canvas, el) and an HTML drawer (page, el).
Element dicts (all text is plain strings; format times in the layout step):

  {"type": "title",   "text": str, "subtitle": str?, "size": int|name?, "tags": [str]?,
                      "tags_layout": "stack"|"row"?}
      tags: short bold words at the right end of the title line, stacked
      (bottom aligned, default) or in one row on the title's baseline. The
      title shrinks if it would come too close to them.
  {"type": "banner",  "text": str}                       inverted full width label
  {"type": "text",    "text": str, "size": "small|medium|large"?, "bold": bool?}
  {"type": "kv",      "items": [[label, value], ...]}    label left, big value right
  {"type": "list",    "items": [str, ...]}
  {"type": "table",   "columns": [str, ...], "rows": [[cell, ...], ...],
                      "widths": [fraction, ...]?}
  {"type": "divider"}
  {"type": "spacer",  "height": int?}
  {"type": "stats",   "blocks": [{"value": str, "secondary": str?, "icon": str?,
                                  "icon_alt": str?, "unit": str?, "label": str?,
                                  "caption": str?, "size": int?, "hidden": bool?}, ...],
                      "max_size": int?}
      A row of side by side stat blocks. Each block: an optional icon (a name
      from dashlib.icons), then a big value with an optional secondary value in
      parentheses, then optional small lines under the value (unit, label,
      caption). "size" is the value size in px (default max_size, else 72).
      Hidden blocks are dropped; the visible ones are spread evenly across the
      width and shrink together if they would not fit.
  {"type": "hero",    "value": str, "size": int?, "icon": str?, "icon_alt": str?,
                      "note": {"icon": str?, "value": str, "caption": str?}?,
                      "side": [{"icon": str?, "value": str, "secondary": str?,
                                "unit": str?, "size": int?, "bold": bool?}, ...]}
      One very large value (default 170 px) with an icon on its left, an
      optional small note under the icon, and a stack of rows on its right.
      Everything shrinks together if it would not fit the width.
"""

from __future__ import annotations

from html import escape

from PIL import ImageOps

from .. import icons
from . import register

BLACK, WHITE = 0, 255


def _s(value) -> str:
    return "" if value is None else str(value)


# ----- title ---------------------------------------------------------------
TITLE_TAG_PX = 24
TITLE_TAG_GAP = 24          # minimum space between the title and its tags
TITLE_MIN_SCALE = 0.7


TITLE_TAG_ROW_GAP = 18


def _title_with_tags(c, text, size, tags, row=False):
    tf = c.font(TITLE_TAG_PX, bold=True)
    if row:
        tag_w = sum(c.text_width(t, tf) for t in tags) + TITLE_TAG_ROW_GAP * (len(tags) - 1)
    else:
        tag_w = max(c.text_width(t, tf) for t in tags)
    room = c.width - tag_w - TITLE_TAG_GAP
    f0 = c.font(size, bold=True)
    px0 = f0.size
    font = f0
    px = px0
    while c.text_width(text, font) > room and px > px0 * TITLE_MIN_SCALE:
        px -= 2
        font = c.font(px, bold=True)
    text = c.ellipsize(text, font, room)
    top, lh0 = c.y, c.line_height(f0)
    baseline = top + f0.getmetrics()[0]  # keep the baseline where a full size title has it
    c.draw.text((c.x0, baseline), text, font=font, fill=BLACK, anchor="ls")
    if row:
        x = c.x1
        for t in reversed(tags):
            x -= c.text_width(t, tf)
            c.draw.text((x, baseline), t, font=tf, fill=BLACK, anchor="ls")
            x -= TITLE_TAG_ROW_GAP
        c.y = top + lh0
        return
    tlh = c.line_height(tf)
    y = max(top, top + lh0 - tlh * len(tags))
    for t in tags:
        c.draw.text((c.x1 - c.text_width(t, tf), y), t, font=tf, fill=BLACK)
        y += tlh
    c.y = top + lh0


def title_png(c, el):
    tags = [_s(t) for t in (el.get("tags") or []) if t]
    if tags:
        _title_with_tags(c, _s(el.get("text")), el.get("size", "title"), tags,
                         row=el.get("tags_layout") == "row")
    else:
        c.text_block(_s(el.get("text")), size=el.get("size", "title"), bold=True)
    if el.get("subtitle"):
        c.text_block(_s(el["subtitle"]), size="small")
    c.y += 6
    c.draw.rectangle([c.x0, c.y, c.x1, c.y + 4], fill=BLACK)
    c.y += 4


def title_html(page, el):
    tags = [_s(t) for t in (el.get("tags") or []) if t]
    tag_html = ""
    if tags:
        tag_html = f'<ul class="tags {"row" if el.get("tags_layout") == "row" else ""}">' + "".join(f"<li>{escape(t)}</li>" for t in tags) + "</ul>"
    out = f'<h1 class="el-title">{tag_html}{escape(_s(el.get("text")))}</h1>'
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
STATS_DEFAULT_PX = 72       # value size when a block gives no "size"
STATS_MIN_SCALE = 0.5       # shrink at most to half size before giving up
STATS_MIN_GAP = 44          # minimum space between blocks
STATS_EDGE = 0.25           # outer margin, as a fraction of the gap between blocks


def _visible_blocks(el):
    return [b for b in (el.get("blocks") or []) if isinstance(b, dict) and not b.get("hidden")]


def _block_px(b, el) -> int:
    try:
        return int(b.get("size") or el.get("max_size") or STATS_DEFAULT_PX)
    except (TypeError, ValueError):
        return STATS_DEFAULT_PX


def _measure_block(c, b, px):
    """Sizes and fonts for one block at value size px."""
    m = {"value": _s(b.get("value")), "sec": _s(b.get("secondary"))}
    m["vf"] = c.font(px, bold=True)
    m["sf"] = c.font(max(18, round(px * 0.56)))
    m["vw"] = c.text_width(m["value"], m["vf"])
    m["sw"] = (px * 0.1 + c.text_width(f"({m['sec']})", m["sf"])) if m["sec"] else 0
    top = m["vf"].getbbox(m["value"] or "0", anchor="ls")[1]
    m["cap"] = max(1, -top)  # height of the value above its baseline

    # Small lines under the value: unit, then label, then caption.
    small_px = max(18, round(px * 0.42))
    m["under"] = []
    for key, f in (("unit", c.font(small_px)), ("label", c.font(max(20, round(px * 0.5)))),
                   ("caption", c.font(small_px))):
        if b.get(key):
            m["under"].append((_s(b[key]), f))
    m["under_gap"] = round(px * 0.14)
    m["under_h"] = sum(c.line_height(f) for _, f in m["under"])

    m["icon"] = None
    ratio = icons.aspect(b.get("icon"))
    if ratio:
        ih = max(12, round(px * 0.85))
        m["icon"] = (b["icon"], ih, round(ih * ratio))
        m["icon_gap"] = round(px * 0.18)
    text_w = max([m["vw"] + m["sw"]] + [c.text_width(t, f) for t, f in m["under"]])
    m["text_w"] = text_w
    m["w"] = text_w + ((m["icon"][2] + m["icon_gap"]) if m["icon"] else 0)
    # Extent above and below the value's visual centre line.
    half_icon = m["icon"][1] / 2 if m["icon"] else 0
    m["above"] = max(m["cap"] / 2, half_icon)
    below_text = m["cap"] / 2 + (m["under_gap"] + m["under_h"] if m["under"] else 0)
    m["below"] = max(below_text, half_icon)
    return m


def _layout_stats(c, el, blocks):
    n = len(blocks)
    scale = 1.0
    while True:
        ms = [_measure_block(c, b, max(12, round(_block_px(b, el) * scale))) for b in blocks]
        need = sum(m["w"] for m in ms) + STATS_MIN_GAP * (n - 1 + 2 * STATS_EDGE)
        if need <= c.width or scale <= STATS_MIN_SCALE:
            return ms
        scale -= 0.04


def stats_png(c, el):
    blocks = _visible_blocks(el)
    if not blocks:
        return
    ms = _layout_stats(c, el, blocks)
    n = len(ms)
    # Equal gaps between blocks and a smaller margin at both ends.
    free = max(0, c.width - sum(m["w"] for m in ms))
    g = free / (n - 1 + 2 * STATS_EDGE)
    centre = c.y + max(m["above"] for m in ms)
    x = c.x0 + g * STATS_EDGE
    for m in ms:
        tx = x
        if m["icon"]:
            name, ih, iw = m["icon"]
            img = icons.png(name, ih)
            if img is not None:
                top = round(centre - ih / 2)
                # Use the icon as a mask so it never paints white over anything.
                c.image.paste(BLACK, (round(x), top, round(x) + img.width, top + img.height),
                              mask=ImageOps.invert(img))
            tx = x + iw + m["icon_gap"]
        baseline = centre + m["cap"] / 2
        c.draw.text((tx, baseline), m["value"], font=m["vf"], fill=BLACK, anchor="ls")
        if m["sec"]:
            c.draw.text((tx + m["vw"] + m["sw"] - c.text_width(f"({m['sec']})", m["sf"]), baseline),
                        f"({m['sec']})", font=m["sf"], fill=BLACK, anchor="ls")
        y = baseline + m["under_gap"]
        for text, f in m["under"]:
            c.draw.text((tx, y), text, font=f, fill=BLACK)
            y += c.line_height(f)
        x += m["w"] + g
    c.y = round(centre + max(m["below"] for m in ms))


def stats_html(page, el):
    parts = []
    for b in _visible_blocks(el):
        px = max(12, round(_block_px(b, el) * 0.6))
        icon = icons.svg(b.get("icon"), round(px * 0.85), _s(b.get("icon_alt")))
        inner = f'<div class="v" style="font-size:{px}px">{escape(_s(b.get("value")))}'
        if b.get("secondary"):
            inner += f' <span class="s">({escape(_s(b["secondary"]))})</span>'
        inner += "</div>"
        for key, cls in (("unit", "u"), ("label", "l"), ("caption", "c")):
            if b.get(key):
                inner += f'<div class="{cls}">{escape(_s(b[key]))}</div>'
        parts.append(f'<div class="b">{icon}<div class="t">{inner}</div></div>')
    return f'<div class="el el-stats">{"".join(parts)}</div>' if parts else ""


# ----- hero ----------------------------------------------------------------
HERO_DEFAULT_PX = 170
HERO_MIN_SCALE = 0.5


def _paste_icon(c, name, height, x, y):
    """Draw icon `name` with its top left at (x, y); returns its width (0 if unknown)."""
    img = icons.png(name, max(8, round(height)))
    if img is None:
        return 0
    x, y = round(x), round(y)
    c.image.paste(BLACK, (x, y, x + img.width, y + img.height), mask=ImageOps.invert(img))
    return img.width


def _icon_w(name, height):
    ratio = icons.aspect(name)
    return round(max(8, round(height)) * ratio) if ratio else 0


def _hero_plan(c, el, k):
    """Fonts and sizes for the hero at scale k."""
    p = {"k": k}
    px = el.get("size") or HERO_DEFAULT_PX
    p["vf"] = c.font(round(px * k), bold=True)
    p["value"] = _s(el.get("value"))
    p["vw"] = c.text_width(p["value"], p["vf"])
    p["cap"] = max(1, -p["vf"].getbbox("0", anchor="ls")[1])

    # Icon column: icon, then an optional note (icon + value, caption).
    p["ih"] = round(90 * k) if icons.aspect(el.get("icon")) else 0
    col_w = _icon_w(el.get("icon"), p["ih"])
    note = el.get("note") if isinstance(el.get("note"), dict) else None
    p["note"] = note
    col_h = p["ih"]
    if note:
        p["nf"] = c.font(max(20, round(34 * k)), bold=True)
        p["cf"] = c.font(max(18, round(22 * k)))
        p["nih"] = round(30 * k)
        niw = _icon_w(note.get("icon"), p["nih"])
        p["niw"] = niw
        line1 = (niw + 8 if niw else 0) + c.text_width(_s(note.get("value")), p["nf"])
        line2 = c.text_width(_s(note.get("caption")), p["cf"]) if note.get("caption") else 0
        col_w = max(col_w, line1, line2)
        p["note_h"] = round(36 * k) + (c.line_height(p["cf"]) if note.get("caption") else 0)
        col_h += round(8 * k) + p["note_h"]
    p["col_w"], p["col_h"] = col_w, col_h
    p["gap1"] = round(18 * k) if col_w else 0

    # Side rows.
    rows = []
    for r in el.get("side") or []:
        if not isinstance(r, dict) or not r.get("value"):
            continue
        rpx = r.get("size") or 52
        f = c.font(round(rpx * k), bold=r.get("bold", True))
        sf = c.font(round(rpx * 0.65 * k))
        uf = c.font(max(18, round(rpx * 0.46 * k)))
        ih = round(rpx * 0.77 * k)
        iw = _icon_w(r.get("icon"), ih)
        w = (iw + round(10 * k) if iw else 0) + c.text_width(_s(r["value"]), f)
        if r.get("secondary"):
            w += round(6 * k) + c.text_width(f"({_s(r['secondary'])})", sf)
        if r.get("unit"):
            w += round(8 * k) + c.text_width(_s(r["unit"]), uf)
        rows.append({"r": r, "f": f, "sf": sf, "uf": uf, "ih": ih, "iw": iw, "w": w,
                     "h": round(rpx * 1.2 * k)})
    p["rows"] = rows
    p["side_w"] = max((r["w"] for r in rows), default=0)
    p["side_h"] = sum(r["h"] for r in rows)
    p["gap2"] = round(26 * k) if rows else 0
    p["w"] = p["col_w"] + p["gap1"] + p["vw"] + p["gap2"] + p["side_w"]
    return p


def hero_png(c, el):
    k = 1.0
    while True:
        p = _hero_plan(c, el, k)
        if p["w"] <= c.width or k <= HERO_MIN_SCALE:
            break
        k -= 0.03
    top = c.y + 10
    height = max(p["cap"], p["col_h"], p["side_h"])
    cy = top + height / 2

    # Icon column, centred on the row.
    x = c.x0
    if p["col_w"]:
        y = cy - p["col_h"] / 2
        if p["ih"]:
            _paste_icon(c, el["icon"], p["ih"], x + (p["col_w"] - _icon_w(el["icon"], p["ih"])) / 2, y)
            y += p["ih"] + round(8 * k)
        note = p["note"]
        if note:
            tx = x
            if p["niw"]:
                _paste_icon(c, note["icon"], p["nih"], x, y + round(3 * k))
                tx += p["niw"] + 8
            c.draw.text((tx, y + round(32 * k)), _s(note.get("value")), font=p["nf"], fill=BLACK, anchor="ls")
            if note.get("caption"):
                c.draw.text((x, y + round(36 * k)), _s(note["caption"]), font=p["cf"], fill=BLACK)
        x += p["col_w"] + p["gap1"]

    # The big value.
    c.draw.text((x, cy + p["cap"] / 2), p["value"], font=p["vf"], fill=BLACK, anchor="ls")
    x += p["vw"] + p["gap2"]

    # Side rows, stacked and centred on the row.
    y = cy - p["side_h"] / 2
    for row in p["rows"]:
        r, yc = row["r"], y + row["h"] / 2
        rx = x
        if row["iw"]:
            _paste_icon(c, r["icon"], row["ih"], rx, yc - row["ih"] / 2)
            rx += row["iw"] + round(10 * k)
        cap = -row["f"].getbbox("0", anchor="ls")[1]
        base = yc + cap / 2
        c.draw.text((rx, base), _s(r["value"]), font=row["f"], fill=BLACK, anchor="ls")
        rx += c.text_width(_s(r["value"]), row["f"])
        if r.get("secondary"):
            rx += round(6 * k)
            sec = f"({_s(r['secondary'])})"
            c.draw.text((rx, base), sec, font=row["sf"], fill=BLACK, anchor="ls")
            rx += c.text_width(sec, row["sf"])
        if r.get("unit"):
            rx += round(8 * k)
            c.draw.text((rx, base), _s(r["unit"]), font=row["uf"], fill=BLACK, anchor="ls")
        y += row["h"]
    c.y = round(top + height)


def hero_html(page, el):
    icon = icons.svg(el.get("icon"), 64, _s(el.get("icon_alt")))
    note = el.get("note") if isinstance(el.get("note"), dict) else None
    col = icon
    if note:
        col += (f'<div class="n">{icons.svg(note.get("icon"), 22)} <b>{escape(_s(note.get("value")))}</b>'
                + (f'<br><small>{escape(_s(note["caption"]))}</small>' if note.get("caption") else "")
                + "</div>")
    rows = ""
    for r in el.get("side") or []:
        if not isinstance(r, dict) or not r.get("value"):
            continue
        v = escape(_s(r["value"]))
        rows += (f'<div class="r">{icons.svg(r.get("icon"), 30)}'
                 + (f"<b>{v}</b>" if r.get("bold", True) else v)
                 + (f' <span class="s">({escape(_s(r["secondary"]))})</span>' if r.get("secondary") else "")
                 + (f' <span class="u">{escape(_s(r["unit"]))}</span>' if r.get("unit") else "")
                 + "</div>")
    return (f'<div class="el el-hero"><div class="col">{col}</div>'
            f'<div class="v">{escape(_s(el.get("value")))}</div><div class="side">{rows}</div></div>')


register("title", png=title_png, html=title_html)
register("banner", png=banner_png, html=banner_html)
register("text", png=text_png, html=text_html)
register("kv", png=kv_png, html=kv_html)
register("list", png=list_png, html=list_html)
register("table", png=table_png, html=table_html)
register("divider", png=divider_png, html=divider_html)
register("spacer", png=spacer_png, html=spacer_html)
register("stats", png=stats_png, html=stats_html)
register("hero", png=hero_png, html=hero_html)
