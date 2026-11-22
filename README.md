# dashboard

A small, general purpose dashboard system. Each dashboard is a self contained
module that **fetches** plain data, **lays it out** as a list of drawing
instructions, and is **rendered** by a shared library into:

- an 8 bit grayscale PNG, 758 × 1024, no alpha, high contrast, large text, for
  an old Kindle e ink screen, and/or
- a single self contained HTML page (inline CSS, no scripts, no external
  requests) for public websites.

Nothing in the shared code is tied to any data topic.

## Layout

```
run.py                    command line entry point
config.example.yaml       committed template; copy to config.yaml (git ignored)
requirements.txt          Pillow, PyYAML
scripts/setup.sh          rebuild the environment on a fresh machine
deploy/                   user systemd units: Kindle server + 5 minute refresh (see deploy/README.md)
kindle/kindle_run.sh      script that runs on the Kindle (fetches dashboard.png in a loop)
src/dashlib/
  config.py               loads config.yaml (timezone + per dashboard settings)
  registry.py             finds and validates dashboards/*/dashboard.yaml
  runner.py               fetch -> layout -> render, stale fallback, safety checks
  elements/__init__.py    element type registry (type name -> PNG + HTML drawer)
  elements/builtin.py     built in types: title, banner, text, kv, list, table, divider, spacer, stats
  sections.py             helpers for dashboards made of independent sections
  render_png.py           Pillow renderer (Canvas used by PNG drawers)
  render_html.py          HTML page template
  state.py                last good data per dashboard
  timeutil.py             time formatting in the configured timezone
dashboards/<name>/
  dashboard.yaml          name, title, visibility, refresh interval, outputs
  fetch.py                fetch(ctx) -> JSON serializable data
  layout.py               layout(data, ctx) -> list of element dicts
  elements.py             optional: extra element types for this dashboard
  sections/<section>.py   optional: section modules (see "Section based dashboards")
output/<visibility>/<name>/   dashboard.png, index.html   (git ignored)
output/kindle/                dashboard.png, kindle_run.sh (git ignored; the only folder served to the Kindle)
state/<visibility>/<name>/    state.json                  (git ignored)
```

## Running

```bash
.venv/bin/python run.py --list                      # list dashboards
.venv/bin/python run.py sample                      # run one (always runs)
.venv/bin/python run.py --all                       # all dashboards that are due
.venv/bin/python run.py --all --visibility private  # only private ones that are due
.venv/bin/python run.py --all --force               # ignore refresh intervals
```

`--all` skips a dashboard if it last ran less than `refresh_minutes` ago, so
a scheduler can call it often. Naming a dashboard always runs it.
Exit code: `0` all fresh or skipped, `1` something stale or failed, `2` usage or
config error. Use `-v` for full tracebacks.

## Adding a dashboard

1. Create `dashboards/<name>/` (lowercase, digits, `-`, `_`).
2. `dashboard.yaml`:
   ```yaml
   name: <name>            # must match the folder
   title: My Dashboard
   visibility: private     # public | private
   refresh_minutes: 30
   outputs: [png]          # any of: png, html
   kindle_publish: false   # optional, see "Kindle delivery"
   ```
3. `fetch.py` defines `fetch(ctx)` and returns plain JSON data (dicts, lists,
   strings, numbers, bools, None). `ctx.settings` is this dashboard's block
   from `config.yaml`, and `ctx.now` is the run time (aware, UTC). Return times as
   ISO strings. Raise an exception on failure, and the runner handles it.
4. `layout.py` defines `layout(data, ctx)` and returns a list of element dicts,
   or `{"elements": [...], "footer_note": "..."}` to add a note such as a data
   source attribution to the footer.
   Format every time with `ctx.format_time(value, style="datetime"|"date"|"time"|"hour")`
   ("Nov 22, 2:26 pm", "Sun Nov 22", "14:26", "2 pm")
   so it shows in the configured timezone. See `src/dashlib/elements/builtin.py`
   for the built in types and their fields.
5. If it needs settings or secrets, add a blank entry under `dashboards:` in
   `config.example.yaml` and the real values in your local `config.yaml`.
6. Run `.venv/bin/python run.py <name>` and look at `output/<visibility>/<name>/`.

`dashboards/sample/` is a complete example. It uses fake, clearly labeled
SAMPLE DATA and needs no network. Set `simulate_failure: true` for it in
`config.yaml` to see the stale behaviour.

### Section based dashboards

A dashboard can be built from independent sections. The section list in
`config.yaml` picks which ones run and in what order. `dashboards/today/` works this
way. Each section is `dashboards/<name>/sections/<section>.py` with:

```python
FOOTER_NOTE = "Source: example.org"   # optional, added to the footer

def fetch(config):        # the section's own block from config.yaml, plus "timezone"
    return {...}          # plain JSON data

def layout(data, ctx):    # returns a list of element dicts
    return [...]
```

The dashboard's own `fetch.py`/`layout.py` just call
`dashlib.sections.fetch_sections(...)` and `layout_sections(...)` (see
`dashboards/today/`). To add a section (calendar, tasks and so on), drop a new
file into `sections/` and add its name to `sections:` in `config.yaml`. Other
sections stay untouched. If any section's fetch fails, the whole dashboard
shows its last good data with the stale note.

### The `stats` element

A generic row of side by side blocks. Each block has an optional `icon` (a name
from `dashlib.icons`, with `icon_alt` as its text for the HTML page), a big
`value`, an optional `secondary` value shown in parentheses, and optional small
lines under the value: `unit`, `label`, `caption`. `size` sets the value size in
pixels. A block can be `hidden`: hidden blocks are dropped and the visible ones
are spread evenly across the width. If the blocks would not fit, they all
shrink together.

```python
{"type": "stats", "blocks": [
    {"icon": "partly_cloudy", "value": "7°", "secondary": "5°", "size": 92},
    {"icon": "wind", "value": "18", "unit": "km/h", "size": 56},
    {"icon": "drop", "value": "40%", "caption": "by 3 pm", "size": 56, "hidden": False},
]}
```

### Icons

`src/dashlib/icons.py` holds a small icon registry: sun, partly_cloudy, cloud,
fog, drizzle, rain, snow, thunder, wind, drop. Each icon is one function drawn
with plain shapes (thick black strokes, smoothed by drawing large and scaling
down), and the same function also produces inline SVG for HTML pages. Add one
with `icons.register(name, draw_fn, aspect)`.

### Adding element types (charts and so on)

Element types are pluggable. Each type name maps to a PNG drawer and an HTML
drawer:

```python
from dashlib.elements import register

def bars_png(canvas, el):      # draw between canvas.x0..canvas.x1 from canvas.y,
    for v in el["values"]:     # then advance canvas.y
        canvas.draw.rectangle([canvas.x0, canvas.y, canvas.x0 + v * 50, canvas.y + 28], fill=0)
        canvas.y += 38

def bars_html(page, el):       # return an HTML fragment; escape text with page.escape
    return "".join(f'<div style="width:{int(v) * 50}px;height:28px;background:currentColor;margin:6px 0"></div>'
                   for v in el["values"])

register("bars", png=bars_png, html=bars_html)
```

Put the code in `dashboards/<name>/elements.py` for one dashboard (the runner
loads it automatically), or in a new module under `src/dashlib/elements/`
imported from `elements/__init__.py` to share it. The runner and renderers
don't change. An unknown type draws a small placeholder instead of crashing.

## The `today` dashboard

A private screen for the Kindle (refreshes every 15 minutes, `kindle_publish:
true`). It shows a large date line, then its sections (for now only
`weather`), then empty space for future sections, then the footer.

Weather comes from the [Open-Meteo](https://open-meteo.com/) forecast API (free,
no key; credit shown in the footer unless `source_notes: false` is set for a
private screen). It uses only the standard library,
with a 15 second timeout. The band shows up to three blocks:

- **Temperature:** a condition icon (mapped from the WMO weather code), the
  current value and, in parentheses, the value 3 hours later.
- **Wind:** a wind icon, the current speed, and the unit under it.
- **Rain:** a drop icon and the chance, with the hour of the peak under it
  ("by 3 pm"). Shown only when the highest precipitation probability over the
  current hour and the next 3 is at or above `rain_threshold_percent`.
  Otherwise the block is left out and the others use the space.

Settings live under `dashboards.today.weather` in `config.yaml` (see
`config.example.yaml`). Put your real `latitude`/`longitude` only in
`config.yaml`. If they are blank, the screen shows "Weather: set location in
config.yaml". Set `simulate: true` to draw clearly labeled SAMPLE weather
with no network. `simulate_rain_percent` sets the simulated peak rain chance, so
setting it below the threshold previews the dry look.

## Kindle delivery

The Kindle runs `kindle/kindle_run.sh`, which downloads `dashboard.png` from
the Pi every few minutes and redraws it when it changes. On the Pi side:

- One dashboard may set `kindle_publish: true` in its `dashboard.yaml` (now
  `today`). The runner fails with a clear error if more than one does.
- Each time that dashboard renders its PNG, the runner copies it to
  `output/kindle/dashboard.png` and copies `kindle/kindle_run.sh` to
  `output/kindle/kindle_run.sh`. Files are first written to
  `output/.kindle-staging/` and then renamed into place, so the Kindle never
  downloads a half written file and the folder never holds temporary files.
- `output/kindle/` should be the only folder served to the Kindle, and should
  hold only those two files. The script also treats a file named `stop` there
  as a stop switch (create it by hand). The runner warns if anything else
  appears there, but never deletes files.
- This repo does not start a web server. Serving `output/kindle/` (the script
  expects `http://<pi>:8080/dashboard.png`) is set up separately.

## Timezone

`timezone` in `config.yaml` (an IANA name, default `America/Vancouver`) is used
for every time shown on every dashboard, including the "Updated" and "stale"
footers.

## Errors and stale data

If `fetch` or `layout` raises, the runner re-renders the **last good data**
with an inverted footer: `STALE since <time> (update failed)`. If there has
never been good data, it keeps any existing output untouched. If no output
exists either, it draws a simple "No data available yet" screen. Error details
go only to the log and to `state/` (git ignored), never onto a rendered page.
Files are written atomically, so a reader never sees a half written image.

## Secrets and private data

- Secrets (tokens, private calendar links and so on) live only in `config.yaml`,
  which is git ignored. `config.example.yaml` is committed with the same keys
  and blank values. `setup.sh` creates `config.yaml` with mode 600.
- `output/` and `state/` are git ignored.
- Private dashboards write only to `output/private/<name>/`. The runner refuses
  to write a private dashboard anywhere under `output/public/`, and refuses any
  private output or state path that git would not ignore.
- Only `output/public/` is ever meant to be published.
- This repo is public. Never paste real data into `dashboards/*/` files or
  into tests, and keep sample data fake.

## Publishing public dashboards (planned, not set up yet)

There will be a GitHub Actions workflow at `.github/workflows/publish.yml`
(not created yet). Notes for writing it:

- Trigger on a schedule plus `workflow_dispatch`.
- Steps: checkout, set up Python, `pip install -r requirements.txt`, write a
  `config.yaml` from a repository secret if any public dashboard needs keys,
  then run `python run.py --all --visibility public --force` and deploy
  **only** `output/public/` with `actions/upload-pages-artifact` and
  `actions/deploy-pages`.
- Never run private dashboards in Actions. Their config isn't there, and
  Actions logs of a public repo are public.
- `state/` doesn't persist between Actions runs, so a failed fetch there has
  no last good data. Either let that run fail without deploying, or cache
  `state/public` with `actions/cache`.
- Pages URLs would look like `https://<user>.github.io/dashboard/public/<name>/`,
  depending on how the artifact root is chosen.

## Rebuilding on a new Raspberry Pi

```bash
git clone https://github.com/dabingougou/dashboard.git ~/github/dashboard
cd ~/github/dashboard
./scripts/setup.sh                 # creates .venv, installs requirements, creates config.yaml
nano config.yaml                   # fill in timezone and any secrets
.venv/bin/python run.py sample     # check the pipeline
```

`config.yaml` isn't in git, so keep a private backup of it somewhere safe.

### Schedule (example only, not installed)

The runner skips dashboards that aren't due, so one frequent entry is enough.
Example user crontab line (`crontab -e`), shown here for reference only:

```cron
# m   h  dom mon dow  command
# */5 *  *   *   *    cd $HOME/github/dashboard && .venv/bin/python run.py --all >> $HOME/github/dashboard/output/run.log 2>&1
```

See "Kindle delivery" above for how the PNG reaches the Kindle.
