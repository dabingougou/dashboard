"""Per dashboard run state (git ignored, under state/<visibility>/<name>/).

Holds the last good fetched data so a failed fetch can re-render the previous
content with a "stale since" note, plus the last attempt time used to decide
whether a dashboard is due for refresh.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class State:
    last_good_at: str | None = None      # ISO UTC time of the last successful fetch
    last_good_data: dict | list | None = None
    last_attempt_at: str | None = None   # ISO UTC time of the last run (ok or not)
    last_error: str | None = None        # short local diagnostic, never rendered
    extra: dict = field(default_factory=dict)


def load(path: Path) -> State:
    if not path.exists():
        return State()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return State()
    known = {k: raw.get(k) for k in State.__dataclass_fields__ if k in raw}
    return State(**known)


def save(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(state), indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
