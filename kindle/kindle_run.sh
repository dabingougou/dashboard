#!/bin/sh
# Silence all output: the Kindle would otherwise draw it on top of the dashboard.
exec >/dev/null 2>&1

BASE="http://192.168.0.2:8080"
IMG=/mnt/us/dashboard.png
TMP=/mnt/us/dashboard.png.new
WAIT=300

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
trap 'lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null' EXIT

n=1
while true; do
  # Stop switch: if the Pi serves a file named "stop", end the loop.
  if wget -q -T 10 -O /dev/null "$BASE/stop"; then
    exit 0
  fi

  BAT=$(lipc-get-prop com.lab126.powerd battLevel 2>/dev/null)
  changed=0
  if wget -q -T 20 -O "$TMP" "$BASE/dashboard.png?n=$n&bat=$BAT" && [ -s "$TMP" ]; then
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
  sleep "$WAIT"
done
