#!/bin/sh
# Silence all output: the Kindle would otherwise draw it on top of the dashboard.
exec >/dev/null 2>&1

BASE="http://192.168.0.2:8080"
IMG=/mnt/us/dashboard.png
TMP=/mnt/us/dashboard.png.new
PIDFILE=/mnt/us/dashboard.pid
# Fetch every PERIOD seconds, OFFSET seconds after each multiple of PERIOD on
# the clock (for example 10:05:40, 10:10:40), so each fetch comes just after
# the Pi's refresh at 10:05, 10:10 and the time in the footer is current.
PERIOD=300
OFFSET=40

# Only one loop at a time: the newest one wins. Each loop writes its process
# id here; an older loop that finds a different id exits at its next wake up.
echo $$ > "$PIDFILE"

FB=$(which fbink 2>/dev/null)
[ -z "$FB" ] && [ -x /mnt/us/libkh/bin/fbink ] && FB=/mnt/us/libkh/bin/fbink

draw() {
  if [ -n "$FB" ]; then
    "$FB" -q -f -g file="$IMG" >/dev/null 2>&1 || "$FB" -q -g file="$IMG" >/dev/null 2>&1
  else
    eips -g "$IMG" >/dev/null 2>&1
  fi
}

lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null
cleanup() {
  # Only the loop that owns the pid file gives the screensaver back.
  if [ "$(cat "$PIDFILE" 2>/dev/null)" = "$$" ]; then
    lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
    rm -f "$PIDFILE"
  fi
}
trap cleanup EXIT

n=1
while true; do
  # A newer loop has started: leave it to that one.
  [ "$(cat "$PIDFILE" 2>/dev/null)" = "$$" ] || exit 0

  # Stop switch: if the Pi serves a file named "stop", end the loop.
  if wget -q -T 10 -O /dev/null "$BASE/stop"; then
    exit 0
  fi

  BAT=$(lipc-get-prop com.lab126.powerd battLevel 2>/dev/null)
  changed=0
  # t= is the Kindle's clock, so the server log shows whether it is right.
  if wget -q -T 20 -O "$TMP" "$BASE/dashboard.png?n=$n&bat=$BAT&t=$(date +%s)" && [ -s "$TMP" ]; then
    if [ ! -f "$IMG" ] || ! cmp -s "$TMP" "$IMG"; then
      changed=1
    fi
    mv "$TMP" "$IMG"
  else
    rm -f "$TMP"
  fi

  # Redraw when the image changed, and also about once an hour to keep the screen clean.
  if [ -f "$IMG" ]; then
    if [ "$changed" = 1 ] || [ $((n % 12)) -eq 1 ]; then
      draw
    fi
  fi

  n=$((n+1))
  # Sleep until the next fetch time on the clock (never less than 30 seconds).
  now=$(date +%s)
  wait=$(( PERIOD - (now - OFFSET) % PERIOD ))
  [ "$wait" -lt 30 ] && wait=$((wait + PERIOD))
  sleep "$wait"
done
