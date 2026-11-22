# Handover: current state and next tasks

Written for the Claude Code session on the Pi. Read CLAUDE.md first (rules and
working style), then docs/kindle_setup.md if you need Kindle background.

## Current state

- The dashboard system, the `sample` dashboard and the private `today` dashboard
  (weather section only) are built and pushed. `kindle/kindle_run.sh` and the
  launcher copy `kindle/dashboard.sh` are tracked.
- The Kindle is running the always on loop against a TEST server that serves the
  old folder `output/public/sample/` on the Pi's LAN address, port 8080, started by
  hand in a terminal. It shows the sample dashboard. Nothing is scheduled and
  there is no service yet. The location is not set (`latitude`, `longitude` blank).
- The owner will install tmux himself and then run the server and this session
  inside it.
- Task C is done: location set locally, Pi tzdata updated to 2026f (BC is on
  UTC-7 all year).
- Task D files are in `deploy/` (not installed yet).
- Task B is done (2026-11-22): the weather band uses icons from
  `src/dashlib/icons.py` and the reworked `stats` element.

## Task A: get oriented (do this first)

1. `git pull --rebase`, read CLAUDE.md, README.md and this file.
2. Confirm the `today` dashboard still renders with `simulate: true` in the local
   `config.yaml`. Report the PNG path and size.

## Task B: redesign the weather band (done)

The owner reviewed a mockup and wants this look. The reference drawing code is in
`docs/reference/weather_band_mockup.py` (run it to see the picture; reuse or adapt
its icon helpers, drawn with Pillow primitives so they stay crisp on e ink).

Layout, left to right, in one compact band under a large date line:

1. Temperature block: a condition icon, then the current temperature big, then the
   temperature 3 hours later in smaller text in parentheses, like `7° (5°)`.
   No caption text such as "now (+3h)", and no condition word. The icon carries the
   condition.
2. Wind block: a wind symbol (three curled lines), then the speed big, with a
   small unit under it, like `18` over `km/h`. No word "Wind".
3. Rain block: a raindrop symbol, then the chance big, like `40%`, with a small
   "by 3 pm" under it (the hour of the peak). Shown only when the maximum chance
   over the current hour and the next 3 hours is at or above
   `rain_threshold_percent`. Otherwise hide the block entirely and let the other
   blocks use the space. No placeholder.

Implementation notes:

- Extend the generic `stats` element (or add a sibling) so a block can have an
  `icon` name, a main value, an optional secondary value in parentheses, a small
  unit or caption, and can be hidden. Keep it generic, not weather specific.
- Add a small icon registry keyed by name (sun, partly_cloudy, cloud, fog,
  drizzle, rain, snow, thunder, wind, drop). Map the WMO weather code to an icon in
  the weather section. Draw with thick strokes, black on white. The HTML drawer may
  use simple inline SVG or plain symbols.
- Make it possible to preview both states with simulation: add a config option for
  the simulated rain chance so you can render one image with rain shown and one
  without.
- Check both renders visually (758 x 1024, grayscale), make sure nothing overlaps
  and the blocks do not crowd each other, then commit and push.

## Task C: location

When the owner supplies the place or coordinates, write the latitude and longitude
into the local `config.yaml` only (git ignored). Never commit the real location.
Set `simulate: false` and run `run.py today` once to confirm the real Open-Meteo
request works. Report only the temperature, wind and rain chance it produced, not
the coordinates.

## Task D: serve the Kindle folder and schedule the refresh (files ready in deploy/)

Goal: `output/kindle/` is the only folder served to the Kindle, a refresh runs on
its own, and everything restarts after a reboot, with no terminal window needed.

1. Prepare unit files under `deploy/` for: (a) a service running Python's built in
   `http.server` bound to the Pi's LAN address only (not 0.0.0.0, not IPv6, not any
   VPN or tunnel address), serving `output/kindle/`, writing its log to a file;
   (b) a timer or equivalent that runs `run.py --all --visibility private` about
   every 5 minutes. Prefer user level systemd units if they work without `sudo`.
2. Write `deploy/README.md` with the exact commands to install, check and remove
   them, each with a plain explanation. Mark exactly which commands need `sudo`.
3. Do not install, enable or start anything. Walk the owner through the commands
   one at a time and wait for each result. Before switching the server over, remind
   him that the running test server and the Kindle loop must be handled in order:
   create `output/kindle/stop`, wait for the `GET /stop ... 200` line, stop the
   test server, start the new service, delete the stop file, then he taps the
   launcher on the Kindle.

## Task E: later sections (wait for the owner)

The owner may want a compact calendar section or a compact task list section on the
same screen, if there is room. Each is a new section module. Each needs one secret
(a task service API token, or a private calendar link) that goes only in the local
`config.yaml`. Do not start these until he says so, and ask him which one first.

## Known issues and notes

- The loop on the Kindle does not survive a Kindle reboot. After one, the owner
  taps the launcher again.
- If the Pi is unreachable, the Kindle keeps showing the last image and retries
  silently.
- Light gray text looks faint on this panel. Use bold black for anything important.
- When a run fails and old data exists, the screen shows a "stale since" bar.
  Treat that as the correct behaviour, not a bug.

## Reporting back

After each task, give a short summary: what exists, what you tested, what you were
unsure about. Do not paste long file contents. Ask before anything on the list in
the safety rules.
