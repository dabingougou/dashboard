"""Built in element types.

Each type has a PNG drawer (canvas, el) and an HTML drawer (page, el).
Element dicts (all text is plain strings; format times in the layout step):

  {"type": "title",   "text": str, "subtitle": str?, "size": int|name?, "tags": [str]?,
                      "tags_layout": "stack"|"row"?, "tags_label": str?}
      tags: short bold words at the right end of the title line, stacked
      (bottom aligned, default) or in one row on the title's baseline. The
      title shrinks if it would come too close to them. tags_label: a small
      word above a row of tags (e.g. "Tomorrow").
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
                                "unit": str?, "prefix": str?, "size": int?, "bold": bool?,
                                "parts": [{"prefix"?, "icon"?, "value", "secondary"?, "unit"?}, ...]?}, ...]}
      One very large value (default 170 px) with an icon on its left, an
      optional small note under the icon, and a stack of rows on its right.
  {"type": "hourly",  "points": [{"label": str, "value": number?, "bar": number?}, ...],
                      "value_suffix": str?, "mark_every": int?, "bar_max": number?,
                      "bar_threshold": number?}
      A strip over time: a line through the values (with the value written at
      every mark_every-th point, default 4, and the last one), bars under it
      (0..bar_max, default 100; solid black at or above bar_threshold, gray
      below), and the point labels along the bottom.
  {"type": "days",    "columns": [{"title": str, "events": [{"time": str, "text": str}, ...],
                                   "tasks": [str, ...], "tasks_more": bool?}, ...],
                      "max_tasks": int?, "event_lines": int?, "task_lines": int?}
      Side by side day columns that fill the rest of the screen: a bold
      underlined heading, the events (time, then the bold title, wrapped), and
      at the bottom of every column the tasks (at most max_tasks, default 2)
      with "…" when there are more. Titles take at most event_lines and
      task_lines lines (default 1 each) and end with "…" when cut. Events that do not
      fit end with "+N more". An empty column stays blank.
      A side row is one item, or several side by side when it has "parts"
      (each part takes the same keys as a row; size and bold come from the row).
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
TITLE_TAG_LABEL_PX = 20


def _title_with_tags(c, text, size, tags, row=False, label=""):
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
        if label:
            lf = c.font(TITLE_TAG_LABEL_PX)
            ty = baseline - tf.getmetrics()[0] - 4
            c.draw.text((c.x1 - c.text_width(label, lf), ty), label, font=lf, fill=BLACK, anchor="ls")
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
                         row=el.get("tags_layout") == "row", label=_s(el.get("tags_label")))
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
        label = f'<li class="label">{escape(_s(el["tags_label"]))}</li>' if el.get("tags_label") else ""
        tag_html = (f'<ul class="tags {"row" if el.get("tags_layout") == "row" else ""}">' + label
                    + "".join(f"<li>{escape(t)}</li>" for t in tags) + "</ul>")
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
HERO_PART_GAP = 30       # px between parts of one side row


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

    # Side rows; each row is one or more parts drawn side by side.
    rows = []
    for r in el.get("side") or []:
        if not isinstance(r, dict):
            continue
        parts = r.get("parts") if isinstance(r.get("parts"), list) else [r]
        parts = [q for q in parts if isinstance(q, dict) and q.get("value")]
        if not parts:
            continue
        rpx = r.get("size") or 52
        f = c.font(round(rpx * k), bold=r.get("bold", True))
        sf = c.font(round(rpx * 0.65 * k))
        uf = c.font(max(18, round(rpx * 0.46 * k)))
        pf = c.font(max(18, round(rpx * 0.6 * k)))
        ih = round(rpx * 0.77 * k)
        w = 0
        for q in parts:
            q_w = c.text_width(_s(q["value"]), f)
            if q.get("prefix"):
                q_w += c.text_width(_s(q["prefix"]), pf) + round(8 * k)
            iw = _icon_w(q.get("icon"), ih)
            if iw:
                q_w += iw + round(10 * k)
            if q.get("secondary"):
                q_w += round(6 * k) + c.text_width(f"({_s(q['secondary'])})", sf)
            if q.get("unit"):
                q_w += round(8 * k) + c.text_width(_s(q["unit"]), uf)
            w += q_w
        w += HERO_PART_GAP * k * (len(parts) - 1)
        rows.append({"parts": parts, "f": f, "sf": sf, "uf": uf, "pf": pf, "ih": ih, "w": w,
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
        yc = y + row["h"] / 2
        cap = -row["f"].getbbox("0", anchor="ls")[1]
        base = yc + cap / 2
        rx = x
        for i, q in enumerate(row["parts"]):
            if i:
                rx += HERO_PART_GAP * k
            if q.get("prefix"):
                c.draw.text((rx, base), _s(q["prefix"]), font=row["pf"], fill=BLACK, anchor="ls")
                rx += c.text_width(_s(q["prefix"]), row["pf"]) + round(8 * k)
            iw = _icon_w(q.get("icon"), row["ih"])
            if iw:
                _paste_icon(c, q["icon"], row["ih"], rx, yc - row["ih"] / 2)
                rx += iw + round(10 * k)
            c.draw.text((rx, base), _s(q["value"]), font=row["f"], fill=BLACK, anchor="ls")
            rx += c.text_width(_s(q["value"]), row["f"])
            if q.get("secondary"):
                rx += round(6 * k)
                sec = f"({_s(q['secondary'])})"
                c.draw.text((rx, base), sec, font=row["sf"], fill=BLACK, anchor="ls")
                rx += c.text_width(sec, row["sf"])
            if q.get("unit"):
                rx += round(8 * k)
                c.draw.text((rx, base), _s(q["unit"]), font=row["uf"], fill=BLACK, anchor="ls")
                rx += c.text_width(_s(q["unit"]), row["uf"])
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
        if not isinstance(r, dict):
            continue
        parts = r.get("parts") if isinstance(r.get("parts"), list) else [r]
        html = []
        for q in parts:
            if not isinstance(q, dict) or not q.get("value"):
                continue
            v = escape(_s(q["value"]))
            html.append((f'<span class="p">{escape(_s(q["prefix"]))}</span> ' if q.get("prefix") else "")
                        + icons.svg(q.get("icon"), 30)
                        + (f"<b>{v}</b>" if r.get("bold", True) else v)
                        + (f' <span class="s">({escape(_s(q["secondary"]))})</span>' if q.get("secondary") else "")
                        + (f' <span class="u">{escape(_s(q["unit"]))}</span>' if q.get("unit") else ""))
        if html:
            rows += f'<div class="r">{"&emsp;".join(html)}</div>'
    return (f'<div class="el el-hero"><div class="col">{col}</div>'
            f'<div class="v">{escape(_s(el.get("value")))}</div><div class="side">{rows}</div></div>')


# ----- days ----------------------------------------------------------------
DAYS_HEAD_PX = 28
DAYS_TIME_PX = 19
DAYS_EVENT_PX = 22
DAYS_TASK_PX = 20
DAYS_PAD = 14            # space between a column rule and its text
DAYS_ITEM_GAP = 14


def _clip_lines(c, text, font, width, max_lines):
    lines = c.wrap(text, font, width)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [c.ellipsize(" ".join(lines[max_lines - 1:]), font, width)]
    return lines


def days_png(c, el):
    cols = [col for col in (el.get("columns") or []) if isinstance(col, dict)]
    if not cols:
        return
    n = len(cols)
    cw = c.width / n
    hf, tf = c.font(DAYS_HEAD_PX, bold=True), c.font(DAYS_TIME_PX)
    ef, kf = c.font(DAYS_EVENT_PX, bold=True), c.font(DAYS_TASK_PX, bold=True)
    elh, klh, tlh = c.line_height(ef) * 0.92, c.line_height(kf) * 0.92, c.line_height(tf)
    max_tasks = max(1, int(el.get("max_tasks") or 2))
    event_lines = max(1, int(el.get("event_lines") or 1))
    task_lines = max(1, int(el.get("task_lines") or 1))
    top, bottom = c.y + 4, c.bottom - 4

    def inner(i):
        x = c.x0 + i * cw
        left = x + (DAYS_PAD if i else 0)
        right = x + cw - (DAYS_PAD if i < n - 1 else 0)
        return left, right - left

    # Tasks zone at the bottom, as tall as the fullest column needs.
    task_plan, zone_h = [], 0
    for i, col in enumerate(cols):
        _, w = inner(i)
        tasks = [_s(t) for t in (col.get("tasks") or []) if t]
        more = bool(col.get("tasks_more")) or len(tasks) > max_tasks
        blocks = [_clip_lines(c, t, kf, w, task_lines) for t in tasks[:max_tasks]]
        h = sum(len(b) * klh + DAYS_ITEM_GAP for b in blocks) + (klh if more else 0)
        task_plan.append((blocks, more))
        zone_h = max(zone_h, h)
    tasks_top = bottom - zone_h if zone_h else bottom

    for i, col in enumerate(cols):
        x = c.x0 + i * cw
        left, w = inner(i)
        if i:
            c.draw.line([x, top, x, bottom], fill=BLACK, width=1)
        c.draw.text((left, top), c.ellipsize(_s(col.get("title")), hf, w), font=hf, fill=BLACK)
        y = top + c.line_height(hf) + 2
        c.draw.rectangle([left, y, left + w, y + 2], fill=BLACK)
        y += 14
        limit = tasks_top - (16 if zone_h else 0)
        events = [e for e in (col.get("events") or []) if isinstance(e, dict)]
        for k, e in enumerate(events):
            lines = _clip_lines(c, _s(e.get("text")), ef, w, event_lines)
            need = (tlh if e.get("time") else 0) + len(lines) * elh
            rest = len(events) - k
            room_for_more = tlh if rest > 1 else 0
            if y + need + room_for_more > limit:
                c.draw.text((left, y), f"+{rest} more", font=tf, fill=BLACK)
                break
            if e.get("time"):
                c.draw.text((left, y), _s(e["time"]), font=tf, fill=BLACK)
                y += tlh
            for ln in lines:
                c.draw.text((left, y), ln, font=ef, fill=BLACK)
                y += elh
            y += DAYS_ITEM_GAP
        blocks, more = task_plan[i]
        if zone_h:
            c.draw.line([left, tasks_top - 10, left + w, tasks_top - 10], fill=BLACK, width=1)
            y = tasks_top
            for b in blocks:
                for ln in b:
                    c.draw.text((left, y), ln, font=kf, fill=BLACK)
                    y += klh
                y += DAYS_ITEM_GAP
            if more:
                c.draw.text((left, y - DAYS_ITEM_GAP * 0.6), "…", font=c.font(30, bold=True), fill=BLACK)
    c.y = bottom


def days_html(page, el):
    cols = [col for col in (el.get("columns") or []) if isinstance(col, dict)]
    if not cols:
        return ""
    max_tasks = max(1, int(el.get("max_tasks") or 2))
    out = []
    for col in cols:
        ev = "".join(f'<li>{"<small>" + escape(_s(e.get("time"))) + "</small><br>" if e.get("time") else ""}'
                     f'<b>{escape(_s(e.get("text")))}</b></li>'
                     for e in (col.get("events") or []) if isinstance(e, dict))
        tasks = [t for t in (col.get("tasks") or []) if t]
        tk = "".join(f"<li>{escape(_s(t))}</li>" for t in tasks[:max_tasks])
        if col.get("tasks_more") or len(tasks) > max_tasks:
            tk += "<li>…</li>"
        out.append(f'<div class="d"><h3>{escape(_s(col.get("title")))}</h3><ul class="ev">{ev}</ul>'
                   + (f'<ul class="tk">{tk}</ul>' if tk else "") + "</div>")
    return f'<div class="el el-days">{"".join(out)}</div>'


# ----- dayrows -------------------------------------------------------------
# One horizontal band per day, sized to its events, then a list (for example
# today's to-dos) in whatever space is left. The list is left out when fewer
# than `min_list_lines` lines fit.
DAYROWS_LABEL_PX = 26
DAYROWS_NUM_PX = 34
DAYROWS_TIME_PX = 19
DAYROWS_EVENT_PX = 22
DAYROWS_ITEM_PX = 20
DAYROWS_LABEL_W = 104     # day name column
DAYROWS_TIME_W = 106      # event time column
DAYROWS_PAD = 14          # space between a rule and the text under it
DAYROWS_LIST_INDENT = 16


def dayrows_png(c, el):
    rows = [r for r in (el.get("rows") or []) if isinstance(r, dict)]
    lf, nf, tf = c.font(DAYROWS_LABEL_PX, bold=True), c.font(DAYROWS_NUM_PX, bold=True), c.font(DAYROWS_TIME_PX)
    ef, kf, hf = c.font(DAYROWS_EVENT_PX, bold=True), c.font(DAYROWS_ITEM_PX, bold=True), c.font(DAYROWS_TIME_PX, bold=True)
    elh, klh = c.line_height(ef) * 1.12, c.line_height(kf) * 1.15
    max_lines = max(1, int(el.get("max_lines") or 5))
    ev_x = c.x0 + DAYROWS_LABEL_W
    title_x = ev_x + DAYROWS_TIME_W
    bottom = c.bottom - 4
    y = c.y + 4
    if el.get("rule_top", True):
        c.draw.rectangle([c.x0, y, c.x1, y + 2], fill=BLACK)
        y += 3
    for i, r in enumerate(rows):
        if i:
            c.draw.line([c.x0, y, c.x1, y], fill=BLACK, width=2)
        evs = [e for e in (r.get("events") or []) if isinstance(e, dict)]
        if not evs:   # one short line: "Wed 25   No events"
            c.draw.text((c.x0, y + DAYROWS_PAD - 6), _s(r.get("short") or r.get("label")), font=lf, fill=BLACK)
            c.draw.text((title_x, y + DAYROWS_PAD - 1), _s(el.get("empty_text", "No events")), font=tf, fill=BLACK)
            y += c.line_height(lf) + DAYROWS_PAD + 4
            continue
        shown = evs if len(evs) <= max_lines else evs[:max_lines - 1]
        c.draw.text((c.x0, y + DAYROWS_PAD - 4), _s(r.get("label")), font=lf, fill=BLACK)
        if r.get("sub"):
            c.draw.text((c.x0, y + DAYROWS_PAD - 4 + c.line_height(lf)), _s(r["sub"]), font=nf, fill=BLACK)
        ly = y + DAYROWS_PAD - 2
        for e in shown:
            c.draw.text((ev_x, ly + 3), _s(e.get("time")), font=tf, fill=BLACK)
            c.draw.text((title_x, ly), c.ellipsize(_s(e.get("text")), ef, c.x1 - title_x), font=ef, fill=BLACK)
            ly += elh
        if len(shown) < len(evs):
            c.draw.text((title_x, ly + 3), f"+{len(evs) - len(shown)} more", font=tf, fill=BLACK)
            ly += elh
        label_h = DAYROWS_PAD - 4 + c.line_height(lf) + (c.line_height(nf) if r.get("sub") else 0) + 6
        y = max(ly + 8, y + label_h)

    items = [_s(t) for t in (el.get("list") or []) if t]
    head_h = c.line_height(hf) + 15
    fit = int((bottom - (y + 15) - head_h) // klh)
    if items and fit >= max(1, int(el.get("min_list_lines") or 2)):
        c.draw.line([c.x0, y, c.x1, y], fill=BLACK, width=2)          # double rule
        c.draw.line([c.x0, y + 5, c.x1, y + 5], fill=BLACK, width=2)
        y += 13
        x = c.x0 + DAYROWS_LIST_INDENT
        lh = c.line_height(hf)
        c.draw.rectangle([c.x0, y + 2, c.x0 + 1, y + lh - 2], fill=BLACK)      # double bar by the heading
        c.draw.rectangle([c.x0 + 5, y + 2, c.x0 + 6, y + lh - 2], fill=BLACK)
        c.draw.text((x, y), _s(el.get("list_title")), font=hf, fill=BLACK)
        y += head_h
        show = items if len(items) <= fit else items[:fit - 1] + [None]
        for k, t in enumerate(show):
            ty = y + k * klh
            if t is None:
                c.draw.text((x, ty + 2), f"+{len(items) - fit + 1} more", font=tf, fill=BLACK)
            else:
                c.draw.text((x, ty), c.ellipsize(t, kf, c.x1 - x), font=kf, fill=BLACK)
        c.draw.rectangle([c.x0, y + 2, c.x0 + 1, y + len(show) * klh - 6], fill=BLACK)  # single bar by the items
    c.y = bottom


def dayrows_html(page, el):
    max_lines = max(1, int(el.get("max_lines") or 5))
    out = []
    for r in (el.get("rows") or []):
        if not isinstance(r, dict):
            continue
        evs = [e for e in (r.get("events") or []) if isinstance(e, dict)]
        shown = evs if len(evs) <= max_lines else evs[:max_lines - 1]
        li = "".join(f'<li><small>{escape(_s(e.get("time")))}</small> <b>{escape(_s(e.get("text")))}</b></li>'
                     for e in shown)
        if len(shown) < len(evs):
            li += f"<li><small>+{len(evs) - len(shown)} more</small></li>"
        if not evs:
            li = f'<li><small>{escape(_s(el.get("empty_text", "No events")))}</small></li>'
        label = escape(_s(r.get("label"))) + (f' {escape(_s(r["sub"]))}' if r.get("sub") else "")
        out.append(f'<div class="r"><h3>{label}</h3><ul>{li}</ul></div>')
    items = [t for t in (el.get("list") or []) if t]
    if items:
        out.append(f'<div class="ls"><h4>{escape(_s(el.get("list_title")))}</h4><ul>'
                   + "".join(f"<li>{escape(_s(t))}</li>" for t in items) + "</ul></div>")
    return f'<div class="el el-dayrows">{"".join(out)}</div>'


# ----- hourly --------------------------------------------------------------
HOURLY_VALUE_PX = 22
HOURLY_LABEL_PX = 20
HOURLY_LINE_H = 36       # vertical travel of the value line
HOURLY_BAR_H = 32        # height of a full bar
HOURLY_BAR_GRAY = 140


def _hourly_points(el):
    pts = [q for q in (el.get("points") or []) if isinstance(q, dict)]
    return pts if len(pts) >= 2 else []


def _num_or_none(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _hourly_marks(n, every, vals=()):
    """Indices whose value is written: the first and last, the lowest and
    highest, then every `every`-th point, skipping any next to one already taken."""
    every = max(1, int(every or 4))
    known = [(v, i) for i, v in enumerate(vals) if v is not None]
    wanted = [0, n - 1]
    if known:
        wanted += [min(known)[1], max(known)[1]]
    wanted += list(range(0, n, every))
    marks: list[int] = []
    for i in wanted:
        if all(abs(i - m) > 1 for m in marks) or i in marks:
            if i not in marks:
                marks.append(i)
    return set(marks)


def _fmt_value(v, suffix):
    return f"{int(v + 0.5) if v >= 0 else -int(-v + 0.5)}{suffix}"


def hourly_png(c, el):
    pts = _hourly_points(el)
    if not pts:
        return
    n = len(pts)
    vf, lf = c.font(HOURLY_VALUE_PX, bold=True), c.font(HOURLY_LABEL_PX)
    bar_w = max(6, min(24, c.width / n * 0.45))
    edge = max(bar_w / 2, c.text_width(_s(pts[0].get("label")), lf) / 2, 14)
    x0, x1 = c.x0 + edge, c.x1 - edge
    step = (x1 - x0) / (n - 1)
    xs = [x0 + i * step for i in range(n)]
    suffix = _s(el.get("value_suffix"))

    top = c.y + 8
    line_top = top + c.line_height(vf) + 4
    vals = [_num_or_none(q.get("value")) for q in pts]
    known = [v for v in vals if v is not None]
    if known:
        lo, hi = min(known), max(known)
        span = (hi - lo) or 1
        ys = [None if v is None else line_top + HOURLY_LINE_H - (v - lo) / span * HOURLY_LINE_H for v in vals]
        seg = []
        for x, y in zip(xs, ys):
            if y is None:
                if len(seg) > 1:
                    c.draw.line(seg, fill=BLACK, width=4, joint="curve")
                seg = []
            else:
                seg.append((x, y))
        if len(seg) > 1:
            c.draw.line(seg, fill=BLACK, width=4, joint="curve")
        for i in _hourly_marks(n, el.get("mark_every"), vals):
            if ys[i] is None:
                continue
            x, y = xs[i], ys[i]
            c.draw.ellipse([x - 6, y - 6, x + 6, y + 6], fill=BLACK)
            t = _fmt_value(vals[i], suffix)
            tw = c.text_width(t, vf)
            tx = min(max(x - tw / 2, c.x0), c.x1 - tw)
            c.draw.text((tx, y - 10), t, font=vf, fill=BLACK, anchor="ls")

    base = line_top + HOURLY_LINE_H + 8 + HOURLY_BAR_H
    bar_max = _num_or_none(el.get("bar_max")) or 100
    threshold = _num_or_none(el.get("bar_threshold"))
    for x, q in zip(xs, pts):
        b = _num_or_none(q.get("bar"))
        if b is None or b <= 0:
            continue
        h = max(2, min(1, b / bar_max) * HOURLY_BAR_H)
        solid = threshold is None or b >= threshold
        c.draw.rectangle([x - bar_w / 2, base - h, x + bar_w / 2, base],
                         fill=BLACK if solid else HOURLY_BAR_GRAY)
    c.draw.line([c.x0, base, c.x1, base], fill=BLACK, width=1)
    for x, q in zip(xs, pts):
        t = _s(q.get("label"))
        c.draw.text((x - c.text_width(t, lf) / 2, base + 6), t, font=lf, fill=BLACK)
    c.y = round(base + 6 + c.line_height(lf))


def hourly_html(page, el):
    pts = _hourly_points(el)
    if not pts:
        return ""
    n, W, H = len(pts), 700, 150
    xs = [20 + i * (W - 40) / (n - 1) for i in range(n)]
    vals = [_num_or_none(q.get("value")) for q in pts]
    known = [v for v in vals if v is not None]
    parts = []
    if known:
        lo, hi = min(known), max(known)
        span = (hi - lo) or 1
        ys = [None if v is None else 30 + 44 - (v - lo) / span * 44 for v in vals]
        line = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys) if y is not None)
        parts.append(f'<polyline points="{line}" fill="none" stroke="var(--fg,#000)" stroke-width="3"/>')
        for i in _hourly_marks(n, el.get("mark_every"), vals):
            if ys[i] is not None:
                parts.append(f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="4" fill="var(--fg,#000)"/>'
                             f'<text x="{xs[i]:.1f}" y="{ys[i] - 9:.1f}" text-anchor="middle" font-size="16" '
                             f'font-weight="700" fill="var(--fg,#000)">{escape(_fmt_value(vals[i], _s(el.get("value_suffix"))))}</text>')
    bar_max = _num_or_none(el.get("bar_max")) or 100
    threshold = _num_or_none(el.get("bar_threshold"))
    for x, q in zip(xs, pts):
        b = _num_or_none(q.get("bar"))
        if b and b > 0:
            h = max(2, min(1, b / bar_max) * 36)
            op = "1" if threshold is None or b >= threshold else ".45"
            parts.append(f'<rect x="{x - 8:.1f}" y="{122 - h:.1f}" width="16" height="{h:.1f}" '
                         f'fill="var(--fg,#000)" opacity="{op}"/>')
        parts.append(f'<text x="{x:.1f}" y="142" text-anchor="middle" font-size="14" '
                     f'fill="var(--fg,#000)">{escape(_s(q.get("label")))}</text>')
    parts.append('<line x1="0" y1="122" x2="700" y2="122" stroke="var(--fg,#000)" stroke-width="1"/>')
    return (f'<div class="el el-hourly"><svg viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="hourly forecast">{"".join(parts)}</svg></div>')


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
register("hourly", png=hourly_png, html=hourly_html)
register("days", png=days_png, html=days_html)
register("dayrows", png=dayrows_png, html=dayrows_html)
