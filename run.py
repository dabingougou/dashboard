#!/usr/bin/env python3
"""Command line entry point.

  python run.py sample                      run one dashboard (always runs)
  python run.py sample other                run several
  python run.py --all                       run every dashboard that is due
  python run.py --all --visibility public   only public (or private) ones
  python run.py --all --force               ignore refresh intervals
  python run.py --list                      list dashboards

Exit code: 0 if everything was fresh or skipped, 1 if any dashboard is stale
or failed, 2 for usage/config errors.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from dashlib.config import load_config  # noqa: E402
from dashlib.registry import VISIBILITIES, discover  # noqa: E402
from dashlib.runner import SafetyError, run_dashboard  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch and render dashboards.")
    ap.add_argument("names", nargs="*", help="dashboard names (folders under dashboards/)")
    ap.add_argument("--all", action="store_true", help="run all dashboards that are due")
    ap.add_argument("--visibility", choices=VISIBILITIES, help="with --all: only this visibility")
    ap.add_argument("--force", action="store_true", help="with --all: ignore refresh intervals")
    ap.add_argument("--list", action="store_true", help="list dashboards and exit")
    ap.add_argument("--config", type=Path, default=ROOT / "config.yaml", help="config file (default: config.yaml)")
    ap.add_argument("--output", type=Path, default=ROOT / "output", help="output root (default: output/)")
    ap.add_argument("--state", type=Path, default=ROOT / "state", help="state root (default: state/)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("run")

    try:
        dashboards = discover(ROOT / "dashboards")
        config = load_config(args.config)
    except Exception as exc:  # noqa: BLE001
        log.error("setup failed: %s", exc)
        return 2

    if args.list:
        for d in dashboards.values():
            print(f"{d.name:20} {d.visibility:8} every {d.refresh_minutes:>4} min  {','.join(d.outputs)}")
        return 0

    if args.all == bool(args.names):
        ap.error("give dashboard names or --all (not both)")
    if args.visibility and not args.all:
        ap.error("--visibility only applies with --all")

    if args.all:
        selected = [d for d in dashboards.values()
                    if not args.visibility or d.visibility == args.visibility]
        force = args.force
    else:
        unknown = [n for n in args.names if n not in dashboards]
        if unknown:
            log.error("unknown dashboard(s): %s (have: %s)", ", ".join(unknown), ", ".join(dashboards))
            return 2
        selected = [dashboards[n] for n in args.names]
        force = True

    worst = 0
    for dash in selected:
        try:
            r = run_dashboard(dash, config, output_root=args.output,
                              state_root=args.state, force=force)
        except SafetyError as exc:
            log.error("%s: SAFETY: %s", dash.name, exc)
            worst = 1
            continue
        except Exception:  # noqa: BLE001 - keep going with other dashboards
            log.exception("%s: render failed", dash.name)
            worst = 1
            continue
        files = " ".join(str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f) for f in r.files)
        log.info("%s: %s %s %s", r.name, r.status.upper(), r.message, files)
        if r.status in ("stale", "failed"):
            worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
