"""Loading config.yaml (git ignored) with safe defaults."""

from __future__ import annotations

import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

log = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "America/Vancouver"


class Config:
    def __init__(self, raw: dict | None, path: Path | None):
        raw = raw or {}
        self.path = path
        self.timezone_name = raw.get("timezone") or DEFAULT_TIMEZONE
        self.tz = ZoneInfo(self.timezone_name)
        self._dashboards = raw.get("dashboards") or {}

    def for_dashboard(self, name: str) -> dict:
        """Settings block for one dashboard (only its own keys)."""
        block = self._dashboards.get(name) or {}
        if not isinstance(block, dict):
            raise ValueError(f"config: dashboards.{name} must be a mapping")
        return dict(block)


def load_config(path: Path) -> Config:
    if not path.exists():
        log.warning("config file %s not found; using defaults (timezone %s)",
                    path, DEFAULT_TIMEZONE)
        return Config(None, None)
    with path.open() as f:
        raw = yaml.safe_load(f)
    if raw is not None and not isinstance(raw, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return Config(raw, path)
