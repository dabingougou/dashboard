"""HTML renderer: one self contained page (inline CSS, no scripts, no external
requests). Element fragments come from the element registry."""

from __future__ import annotations

import logging
import os
from datetime import tzinfo
from html import escape
from pathlib import Path
from string import Template

from . import elements

log = logging.getLogger(__name__)

CSS = """
:root { color-scheme: light dark; --fg: #111; --bg: #fff; --muted: #555; --rule: #111; }
@media (prefers-color-scheme: dark) { :root { --fg: #eee; --bg: #121212; --muted: #aaa; --rule: #eee; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
  font: 18px/1.45 system-ui, -apple-system, "Segoe UI", "DejaVu Sans", sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 24px 16px 8px; }
footer { max-width: 760px; margin: 0 auto; padding: 12px 16px 32px; color: var(--muted);
  font-size: 15px; border-top: 1px solid var(--rule); }
footer.stale { color: var(--bg); background: var(--fg); font-weight: 700; border: 0; }
.el { margin: 0 0 18px; }
h1.el-title { font-size: 2.1em; line-height: 1.15; margin: 0 0 4px;
  padding-bottom: 6px; border-bottom: 4px solid var(--rule); }
h1.el-title .tags { float: right; list-style: none; margin: 0; padding: 0;
  font-size: .4em; line-height: 1.3; text-align: right; }
.el-subtitle { color: var(--muted); margin: 4px 0 0; }
.el-banner { background: var(--fg); color: var(--bg); font-weight: 700; text-align: center;
  padding: 8px 12px; letter-spacing: .05em; }
.el-text.small { font-size: .85em; } .el-text.large { font-size: 1.4em; } .el-text.bold { font-weight: 700; }
.el-kv { width: 100%; border-collapse: collapse; }
.el-kv th { text-align: left; font-weight: 400; padding: 6px 0; }
.el-kv td { text-align: right; font-weight: 700; font-size: 1.3em; padding: 6px 0; }
.el-kv tr + tr { border-top: 1px solid var(--muted); }
ul.el-list { padding-left: 1.2em; } ul.el-list li { margin: 4px 0; }
.table-wrap { overflow-x: auto; }
table.el-table { width: 100%; border-collapse: collapse; }
table.el-table th { text-align: left; border-bottom: 2px solid var(--rule); padding: 4px 8px 4px 0; }
table.el-table td { padding: 4px 8px 4px 0; border-bottom: 1px solid var(--muted); }
hr.el-divider { border: 0; border-top: 2px solid var(--rule); }
.el-stats { display: flex; flex-wrap: wrap; justify-content: space-around; align-items: flex-start; gap: 12px 24px; }
.el-stats .b { display: flex; align-items: flex-start; gap: .35em; }
.el-stats .icon { flex: none; margin-top: .15em; }
.el-stats .v { font-weight: 700; line-height: 1.05; }
.el-stats .s { font-size: .56em; font-weight: 400; }
.el-stats .u, .el-stats .c { font-size: .85em; } .el-stats .l { font-size: 1em; }
.el-unknown { color: var(--muted); font-style: italic; }
"""

PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>$css</style>
</head>
<body>
<main>
$body
</main>
<footer class="$footer_class">$footer</footer>
</body>
</html>
""")


class Page:
    """Context handed to element HTML drawers."""

    def __init__(self, tz: tzinfo):
        self.tz = tz
        self.escape = escape


def render(layout: list[dict], footer: dict, tz: tzinfo, title: str) -> str:
    page = Page(tz)
    parts = []
    for el in layout:
        etype = elements.get(el.get("type", ""))
        if etype is None:
            log.warning("unknown element type %r in HTML", el.get("type"))
            parts.append(f'<p class="el el-unknown">[unknown element: {escape(str(el.get("type")))}]</p>')
        else:
            parts.append(etype.html(page, el))
    return PAGE.substitute(
        title=escape(title),
        css=CSS,
        body="\n".join(parts),
        footer_class="stale" if footer.get("stale") else "",
        footer=escape(" · ".join(t for t in (footer.get("text", ""), footer.get("note", "")) if t)),
    )


def write_html(html: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".html.tmp")
    tmp.write_text(html, encoding="utf-8")
    os.replace(tmp, path)
