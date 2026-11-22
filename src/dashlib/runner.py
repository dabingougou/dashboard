"""Run one dashboard: fetch -> layout -> render, with stale fallback.

Rules enforced here:
  * Output goes to output/<visibility>/<name>/. Only output/public/ is ever
    meant to be published; private dashboards can never land there.
  * Private output must be git ignored; the runner refuses otherwise.
  * A failed fetch (or layout) never blanks the screen: the last good data is
    re-rendered with a "STALE since <time>" footer. Error details go to the
    log and to the git ignored state file, never onto a rendered page.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from pathlib import Path

from . import render_html, render_png, state as state_mod
from .config import Config
from .registry import Dashboard, load_module
from .timeutil import format_time, to_datetime, utc_now

log = logging.getLogger(__name__)

# A dashboard counts as due slightly early so scheduler jitter doesn't make
# it skip a whole cycle.
DUE_SLACK = timedelta(seconds=60)

# File written for each output kind inside output/<visibility>/<name>/.
OUTPUT_FILES = {"png": "dashboard.png", "html": "index.html"}

# Kindle delivery: output/kindle/ is the only folder served to the Kindle and
# holds exactly these files (plus an optional "stop" file you create by hand,
# which kindle_run.sh treats as a stop switch). Temporary files are staged in a
# sibling folder so the served folder never contains partial files.
KINDLE_DIR = "kindle"
KINDLE_STAGING_DIR = ".kindle-staging"
KINDLE_FILES = ("dashboard.png", "kindle_run.sh")
KINDLE_ALLOWED_EXTRA = ("stop",)


@dataclass
class RunContext:
    """Passed to a dashboard's fetch(ctx) and layout(data, ctx)."""

    name: str
    settings: dict      # this dashboard's block from config.yaml
    tz: tzinfo          # configured display timezone
    now: datetime       # aware UTC time of this run

    def format_time(self, value, style: str = "datetime") -> str:
        """Format a datetime or ISO string in the configured timezone."""
        return format_time(value, self.tz, style)


@dataclass
class Result:
    name: str
    status: str         # ok | stale | failed | skipped
    message: str = ""
    files: tuple[Path, ...] = ()


class SafetyError(RuntimeError):
    pass


def output_dir(output_root: Path, dash: Dashboard) -> Path:
    base = (output_root / dash.visibility).resolve()
    out = (base / dash.name).resolve()
    if base not in out.parents:
        raise SafetyError(f"{dash.name}: output path escapes {base}")
    public = (output_root / "public").resolve()
    if dash.is_private and (out == public or public in out.parents):
        raise SafetyError(f"{dash.name}: private dashboard may not write under {public}")
    return out


def _ensure_git_ignored(path: Path) -> None:
    """Refuse to write private output to a path git would track."""
    anchor = path
    while not anchor.exists():  # check before creating anything
        anchor = anchor.parent
    try:
        r = subprocess.run(["git", "check-ignore", "-q", "--no-index", str(path)],
                           cwd=anchor, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        log.warning("git not available; cannot verify %s is ignored", path)
        return
    if r.returncode == 1:
        raise SafetyError(f"refusing to write private output to {path}: not git ignored")
    if r.returncode not in (0, 1):
        log.debug("git check-ignore inconclusive for %s (rc=%s)", path, r.returncode)


def _is_due(st: state_mod.State, dash: Dashboard, now: datetime) -> bool:
    if not st.last_attempt_at:
        return True
    last = to_datetime(st.last_attempt_at)
    return now - last + DUE_SLACK >= timedelta(minutes=dash.refresh_minutes)


def _check_layout(result) -> tuple[list[dict], str]:
    """layout() returns either a list of elements, or
    {"elements": [...], "footer_note": "..."} to add a note (for example a
    data source attribution) to the footer."""
    note = ""
    items = result
    if isinstance(result, dict):
        items = result.get("elements")
        note = str(result.get("footer_note") or "")
    if not isinstance(items, list) or not all(isinstance(i, dict) and "type" in i for i in items):
        raise TypeError("layout() must return a list of dicts that each have a 'type'")
    return items, note


def kindle_publish(png_path: Path, output_root: Path, kindle_script: Path | None) -> Path:
    """Copy the PNG (and the Kindle script) into output/kindle/ atomically."""
    serve = (output_root / KINDLE_DIR).resolve()
    public = (output_root / "public").resolve()
    if serve == public or public in serve.parents:
        raise SafetyError(f"kindle folder {serve} may not be inside {public}")
    staging = (output_root / KINDLE_STAGING_DIR).resolve()
    _ensure_git_ignored(serve)
    _ensure_git_ignored(staging)
    serve.mkdir(parents=True, exist_ok=True)
    staging.mkdir(parents=True, exist_ok=True)

    sources = {"dashboard.png": png_path}
    if kindle_script is not None and kindle_script.is_file():
        sources["kindle_run.sh"] = kindle_script
    else:
        log.warning("kindle script %s not found; only the PNG was published", kindle_script)
    for name, src in sources.items():
        tmp = staging / name
        shutil.copyfile(src, tmp)
        os.replace(tmp, serve / name)  # same filesystem: atomic rename

    extra = sorted(p.name for p in serve.iterdir()
                   if p.name not in KINDLE_FILES + KINDLE_ALLOWED_EXTRA)
    if extra:
        log.warning("unexpected files in %s (served to the Kindle!): %s", serve, ", ".join(extra))
    return serve / "dashboard.png"


def run_dashboard(dash: Dashboard, config: Config, *, output_root: Path,
                  state_root: Path, force: bool = True,
                  kindle_script: Path | None = None) -> Result:
    now = utc_now()
    ctx = RunContext(name=dash.name, settings=config.for_dashboard(dash.name),
                     tz=config.tz, now=now)
    out_dir = output_dir(output_root, dash)
    state_path = state_root / dash.visibility / dash.name / "state.json"
    st = state_mod.load(state_path)

    if not force and not _is_due(st, dash, now):
        return Result(dash.name, "skipped", "not due yet")

    if dash.is_private:
        _ensure_git_ignored(out_dir)
        _ensure_git_ignored(state_path.parent.resolve())

    # Optional dashboard specific element types register themselves here.
    load_module(dash, "elements.py")
    fetch_mod = load_module(dash, "fetch.py")
    layout_mod = load_module(dash, "layout.py")

    st.last_attempt_at = now.isoformat()
    items = footer = None
    note = ""
    status, message = "ok", ""

    try:
        data = fetch_mod.fetch(ctx)
        data = json.loads(json.dumps(data))  # enforce plain JSON data
        items, note = _check_layout(layout_mod.layout(data, ctx))
        st.last_good_at, st.last_good_data, st.last_error = now.isoformat(), data, None
        footer = {"text": f"Updated {ctx.format_time(now)}", "stale": False}
    except Exception as exc:  # noqa: BLE001 - any dashboard failure is handled the same way
        log.error("%s: fetch/layout failed: %s", dash.name, exc, exc_info=log.isEnabledFor(logging.DEBUG))
        st.last_error = f"{now.isoformat()} {type(exc).__name__}: {exc}"[:500]
        items = None
        if st.last_good_data is not None:
            try:
                items, note = _check_layout(layout_mod.layout(st.last_good_data, ctx))
                since = ctx.format_time(st.last_good_at)
                footer = {"text": f"STALE since {since} (update failed)", "stale": True}
                status, message = "stale", f"showing data from {since}"
            except Exception as exc2:  # noqa: BLE001
                log.error("%s: layout of last good data failed: %s", dash.name, exc2)
                items = None

    if items is None:
        existing = [out_dir / OUTPUT_FILES[k] for k in dash.outputs if (out_dir / OUTPUT_FILES[k]).exists()]
        if existing:
            state_mod.save(state_path, st)
            return Result(dash.name, "failed", "no usable data; kept existing output", tuple(existing))
        items = [
            {"type": "title", "text": dash.title},
            {"type": "text", "text": "No data available yet.", "size": "large", "bold": True},
            {"type": "text", "text": "The first update failed. It will be retried automatically.", "size": "small"},
        ]
        footer = {"text": f"STALE: no data, last try {ctx.format_time(now)}", "stale": True}
        status, message = "failed", "no data yet; drew placeholder"

    footer["note"] = note
    files = []
    if "png" in dash.outputs:
        p = out_dir / OUTPUT_FILES["png"]
        render_png.write_png(render_png.render(items, footer, config.tz), p)
        files.append(p)
        if dash.kindle_publish:
            files.append(kindle_publish(p, output_root, kindle_script))
    if "html" in dash.outputs:
        p = out_dir / OUTPUT_FILES["html"]
        render_html.write_html(render_html.render(items, footer, config.tz, dash.title), p)
        files.append(p)

    state_mod.save(state_path, st)
    return Result(dash.name, status, message, tuple(files))
