# CLAUDE.md

Standing instructions for any Claude Code session in this repo. Read this first,
then docs/HANDOVER.md for the current task list.

## What this project is

A small, general purpose dashboard system running on a Raspberry Pi at home. Each
dashboard is a module that fetches data, lays it out, and is rendered by a shared
library into a grayscale PNG (for an old jailbroken Kindle e ink screen) and/or an
HTML page (for public sites). See README.md for the layout and commands.

Keep every design general. When the owner names a few example topics, treat them
as illustrations only and do not fit the code to them.

## Safety rules (highest priority)

1. Work only inside this repo (`~/github/dashboard`). Never read, edit or run
   anything in `~/github/scripts` or any network or VPN configuration. This Pi also
   runs important home services that other people depend on.
2. Do not use `sudo`, install system packages, edit crontab, or create or change
   systemd units unless the owner asks for it in that session. Prepare the files
   and the exact commands; the owner runs anything that needs `sudo`.
3. Do not start, stop or restart any server or the Kindle loop unless asked. Never
   open or forward network ports. Any web server must bind to the LAN address only
   and serve only `output/kindle/`.
4. This repo is public. Never commit secrets, tokens, private links, personal data
   or output from private dashboards. Secrets live in the git ignored
   `config.yaml`; `config.example.yaml` holds blank placeholders only. Private
   output stays under `output/private/` and `output/kindle/` (both git ignored).
5. Use the repo local git identity already configured. Do not change git config.
   Make small commits with clear messages and push to `main` after each logical
   step. Run `git pull --rebase` before pushing; if there is a conflict, stop and
   ask.
6. Use a Python virtual environment inside the repo (`.venv`, git ignored).

## Working style with the owner

- The owner dictates most messages by voice, so odd wording is usually a
  transcription error. Read for the likely meaning.
- Do not use dashes (em dashes, en dashes, or hyphens) as punctuation in prose.
  Use commas, periods, parentheses or colons. Hyphens inside code, file names and
  command flags are fine.
- When you give a terminal command for the owner to run, say what it does and what
  each flag means. Give one step at a time for anything that needs the owner's
  hands, and wait for the result before the next step.
- Prefer one concrete recommendation over a list of options. No filler.
- Be honest about what you cannot do or have not tested. Never claim a result you
  did not check. If something fails twice, stop and report instead of retrying.
- The owner dislikes shuffling text between tools. Do the work in this session,
  and keep the repo the single source of truth. Anything that must be pasted
  somewhere else should be a short, copy ready block.

## The Kindle side (facts, because you cannot reach the Kindle)

- Device: Kindle Paperwhite 2 (2013), firmware 5.12.2.2, jailbroken. Screen
  758 x 1024, 8 bit grayscale. You have no shell on it. Only the owner can touch it.
- Any `.sh` file in the Kindle's `documents` folder shows up as a book in the
  library and runs when tapped (from the Universal Hotfix). Anything the script
  prints is drawn on the screen by the runner, so scripts must silence their output
  (`exec >/dev/null 2>&1`), otherwise error text overprints the dashboard.
- `kindle/dashboard.sh` is a tiny launcher installed on the Kindle over USB. It
  downloads `kindle_run.sh` from the Pi and runs it. Changing the launcher needs a
  USB copy, so do not change it unless unavoidable.
- `kindle/kindle_run.sh` holds the real behaviour. The Pi serves it from
  `output/kindle/`, and the Kindle downloads a fresh copy each time the launcher
  runs. So behaviour changes go here, with no cable. The running loop keeps the old
  copy until it is restarted (stop file, then the owner taps the launcher again).
- The loop: keeps the screensaver off, every 300 seconds fetches
  `dashboard.png?n=<count>&bat=<battery>`, redraws with fbink only when the image
  changed (and once an hour), and exits if `/stop` exists on the server. The
  server log therefore shows one request per cycle with a battery reading, which
  is the only monitoring we have. A 404 on `/stop` is normal.
- Tools on the Kindle: `/mnt/us/libkh/bin/fbink`, `eips`, busybox `wget`
  (no HTTPS), `lipc-set-prop`, `lipc-get-prop`. Files live under `/mnt/us`.
- The Kindle's user storage is deliberately filled so only about 50 MB is free.
  This blocks over the air firmware updates that could remove the jailbreak. Do
  not suggest writing large files to the Kindle. See docs/kindle_setup.md.
- The Kindle reaches the Pi over plain HTTP at the Pi's LAN address on port 8080.
  That is acceptable only on the home network. Nothing private may be served
  anywhere else.
- Known cosmetic quirk: light gray text in the right hand table column looks
  faint on this panel. Prefer bold and solid black for anything important.
