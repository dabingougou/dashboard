# Deploy: Kindle server and scheduled refresh

Three user level systemd units. They run as your normal user, need no `sudo`
(except possibly once, for lingering), and restart after a reboot.

| File | What it does |
|------|--------------|
| `dashboard-kindle-server.service` | Python's built in `http.server`, bound to `192.168.0.2:8080` only, serving `output/kindle/` and nothing else. Logs every request to `logs/kindle-server.log`. Restarts on failure and keeps retrying at boot until the LAN address exists. |
| `dashboard-refresh.service` | One pass of `run.py --all --visibility private` (only dashboards that are due). |
| `dashboard-refresh.timer` | Starts the refresh every 5 minutes, and 1 minute after boot. |

The address `192.168.0.2` must match `BASE` in `kindle/dashboard.sh` and
`kindle/kindle_run.sh`. If the Pi's address ever changes, change all three.

All commands below run from the repo folder: `cd ~/github/dashboard`.

## Install

1. Copy the units into your user systemd folder.
   ```
   mkdir -p ~/.config/systemd/user logs
   cp deploy/dashboard-kindle-server.service deploy/dashboard-refresh.service deploy/dashboard-refresh.timer ~/.config/systemd/user/
   ```
   `mkdir -p` creates the folders if missing (`-p`: no error if they exist).
   Copies, not links, so a `git pull` never changes a running service by surprise.

2. Tell systemd to read the new files.
   ```
   systemctl --user daemon-reload
   ```
   `--user`: your own service manager, not the system one.

3. Let your user services run without a login session, including after a reboot.
   ```
   loginctl enable-linger dh
   ```
   If it answers with an authentication or permission error, run it with
   **`sudo`**: `sudo loginctl enable-linger dh`. This is the only step that may
   need `sudo`. Check: `loginctl show-user dh -p Linger` should print `Linger=yes`.

4. Start the refresh timer, and enable it at boot.
   ```
   systemctl --user enable --now dashboard-refresh.timer
   ```
   `enable`: start at boot. `--now`: also start it right away.

5. Switch the Kindle server over (see the order below), then:
   ```
   systemctl --user enable --now dashboard-kindle-server.service
   ```

### Switching the Kindle over without confusing it

If a test server is running and the Kindle loop is fetching from it:

1. `touch output/kindle/stop` (creates the stop file).
2. Wait for a `GET /stop ... 200` line in the test server's output (up to 5 minutes).
3. Stop the test server (Ctrl+C in its terminal).
4. Start the service (install step 5).
5. `rm output/kindle/stop`
6. Tap `dashboard.sh` on the Kindle.

If no server is running, skip 1 to 3 and 5.

## Check

```
systemctl --user status dashboard-kindle-server.service dashboard-refresh.timer
systemctl --user list-timers dashboard-refresh.timer
tail -n 20 logs/kindle-server.log
journalctl --user -u dashboard-refresh.service -n 20
ss -ltn 'sport = :8080'
```

- `status`: whether each unit is running, and its last log lines.
- `list-timers`: when the refresh last ran and runs next.
- `tail -n 20`: the last 20 requests. Expect one `GET /dashboard.png?n=...&bat=...`
  every 5 minutes from the Kindle, plus a 404 for `/stop` (normal).
- `journalctl --user -u ... -n 20`: the last 20 lines from the refresh runs.
- `ss -ltn 'sport = :8080'`: listening sockets on port 8080 (`-l` listening,
  `-t` TCP, `-n` numeric). It must show `192.168.0.2:8080` only, never
  `0.0.0.0:8080` or `*:8080`.

A refresh run that ends stale or failed shows the refresh unit as `failed`. The
timer keeps running and the screen shows the "stale since" bar.

## Stop or remove

```
systemctl --user disable --now dashboard-kindle-server.service dashboard-refresh.timer
rm ~/.config/systemd/user/dashboard-kindle-server.service ~/.config/systemd/user/dashboard-refresh.service ~/.config/systemd/user/dashboard-refresh.timer
systemctl --user daemon-reload
```

`disable --now`: stop now and do not start at boot. Lingering can be turned off
with `loginctl disable-linger dh` (or with **`sudo`** if it was needed to turn
it on), but only if no other user services of yours need it.

## Updating after a change to these files

Repeat install steps 1 and 2, then
`systemctl --user restart dashboard-kindle-server.service`. The timer picks up
a changed refresh unit on its next run.

## Notes

- The server log grows by about one line per 5 minutes (roughly 10 MB a year).
  Empty it any time with `: > logs/kindle-server.log`.
- `http.server` is not meant for the internet. It is acceptable here only because
  it listens on the home network address and serves a folder holding two files.
