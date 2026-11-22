#!/bin/sh
# Launcher: fetch the latest instructions from the Raspberry Pi, then run them.
# This file is a COPY of what is installed on the Kindle at
# /mnt/us/documents/dashboard.sh. Changing it means copying it onto the Kindle
# over USB, so keep it tiny and stable. Put all real behaviour in kindle_run.sh,
# which the Pi serves and the Kindle downloads each time this launcher runs.
BASE="http://192.168.0.2:8080"
RUN=/mnt/us/kindle_run.sh

sleep 2
# Keep the last good copy if the Pi cannot be reached.
if wget -q -T 20 -O "$RUN.new" "$BASE/kindle_run.sh" && [ -s "$RUN.new" ]; then
  mv "$RUN.new" "$RUN"
else
  rm -f "$RUN.new"
fi

if [ -f "$RUN" ]; then
  sh "$RUN"
fi
