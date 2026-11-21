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
src/dashlib/
  config.py               loads config.yaml (timezone + per dashboard settings)
  registry.py             finds and validates dashboards/*/dashboard.yaml
  runner.py               fetch -> layout -> render, stale fallback, safety checks
  elements/__init__.py    element type registry (type name -> PNG + HTML drawer)
  elements/builtin.py     built in types: title, banner, text, kv, list, table, divider, spacer
  render_png.py           Pillow renderer (Canvas used by PNG drawers)
  render_html.py          HTML page template
  state.py                last good data per dashboard
  timeutil.py             time formatting in the configured timezone
dashboards/<name>/
  dashboard.yaml          name, title, visibility, refresh interval, outputs
  fetch.py                fetch(ctx) -> JSON serializable data
  layout.py               layout(data, ctx) -> list of element dicts
  elements.py             optional: extra element types for this dashboard
output/<visibility>/<name>/   dashboard.png, index.html   (git ignored)
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
   ```
3. `fetch.py` defines `fetch(ctx)` and returns plain JSON data (dicts, lists,
   strings, numbers, bools, None). `ctx.settings` is this dashboard's block
   from `config.yaml`, and `ctx.now` is the run time (aware, UTC). Return times as
   ISO strings. Raise an exception on failure, and the runner handles it.
4. `layout.py` defines `layout(data, ctx)` and returns a list of element dicts.
   Format every time with `ctx.format_time(value, style="datetime"|"date"|"time")`
   so it shows in the configured timezone. See `src/dashlib/elements/builtin.py`
   for the built in types and their fields.
5. If it needs settings or secrets, add a blank entry under `dashboards:` in
   `config.example.yaml` and the real values in your local `config.yaml`.
6. Run `.venv/bin/python run.py <name>` and look at `output/<visibility>/<name>/`.

`dashboards/sample/` is a complete example. It uses fake, clearly labeled
SAMPLE DATA and needs no network. Set `simulate_failure: true` for it in
`config.yaml` to see the stale behaviour.

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

How the Kindle picks up `output/<visibility>/<name>/dashboard.png` (for example
a local web server or file sync) is outside this repo and still to be decided.
