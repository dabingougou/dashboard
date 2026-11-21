"""Discover and validate dashboards under dashboards/<name>/."""

from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import yaml

VISIBILITIES = ("public", "private")
OUTPUT_KINDS = ("png", "html")
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True)
class Dashboard:
    name: str
    title: str
    visibility: str
    refresh_minutes: int
    outputs: tuple[str, ...]
    path: Path

    @property
    def is_private(self) -> bool:
        return self.visibility == "private"


def load_dashboard(folder: Path) -> Dashboard:
    spec_file = folder / "dashboard.yaml"
    with spec_file.open() as f:
        raw = yaml.safe_load(f) or {}
    where = str(spec_file)

    name = raw.get("name")
    if name != folder.name:
        raise ValueError(f"{where}: name {name!r} must match folder name {folder.name!r}")
    if not _NAME_RE.match(name):
        raise ValueError(f"{where}: name must be lowercase letters, digits, '-' or '_'")

    visibility = raw.get("visibility")
    if visibility not in VISIBILITIES:
        raise ValueError(f"{where}: visibility must be one of {VISIBILITIES}")

    refresh = raw.get("refresh_minutes")
    if not isinstance(refresh, int) or refresh <= 0:
        raise ValueError(f"{where}: refresh_minutes must be a positive integer")

    outputs = raw.get("outputs") or []
    if not outputs or any(o not in OUTPUT_KINDS for o in outputs):
        raise ValueError(f"{where}: outputs must be a non empty list from {OUTPUT_KINDS}")

    for required in ("fetch.py", "layout.py"):
        if not (folder / required).is_file():
            raise ValueError(f"{folder}: missing {required}")

    return Dashboard(
        name=name,
        title=str(raw.get("title") or name),
        visibility=visibility,
        refresh_minutes=refresh,
        outputs=tuple(dict.fromkeys(outputs)),
        path=folder,
    )


def discover(dashboards_dir: Path) -> dict[str, Dashboard]:
    found: dict[str, Dashboard] = {}
    for folder in sorted(p for p in dashboards_dir.iterdir() if p.is_dir()):
        if (folder / "dashboard.yaml").is_file():
            d = load_dashboard(folder)
            found[d.name] = d
    return found


def load_module(dash: Dashboard, filename: str) -> ModuleType | None:
    """Import dashboards/<name>/<filename> by path (None if it doesn't exist)."""
    path = dash.path / filename
    if not path.is_file():
        return None
    mod_name = f"dashboards_{dash.name.replace('-', '_')}_{path.stem}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module
