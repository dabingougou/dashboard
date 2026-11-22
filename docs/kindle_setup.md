# Kindle setup record

How the current Kindle was prepared, so the process can be repeated or fixed.
The jailbreak itself is per device and depends on model and firmware. Check the
Kindle Modding wiki (https://kindlemodding.org) for the current method before
repeating any step on a different Kindle.

## Device

Kindle Paperwhite 2 (2013, 6th generation), Wi Fi only, firmware 5.12.2.2.

## What was done, in order

1. Jailbreak with WinterBreak v1.7.0 (Mesquito launcher). The Kindle was in
   Airplane Mode for this. The log file `winterbreak.log` on the Kindle shows
   "Finished installing jailbreak" on success.
2. Install the Universal Hotfix (KindleModding/Hotfix): copy the
   `Update_hotfix_universal.bin` file to the Kindle root, then Settings, three
   dots, Update Your Kindle, then run the "Run Hotfix" book. This adds the feature
   that runs any `.sh` file from the `documents` folder when it is tapped.
   Note: the package manager (`;kpm`) did not work on this model, and KUAL is
   obsolete per the wiki, so neither is used.
3. Block firmware updates by filling the free space (the wiki's general method):
   run `Filler.sh` from https://github.com/iiroak/Kindle-Filler-Disk on a Mac with
   the Kindle mounted. Run it with `bash`, not `sh` (macOS `sh` rejects it). Choose
   mode 1 (fill) and leave 50 MB free. The script was reviewed before use: it
   writes only a `fill_disk` folder on the Kindle volume and asks for confirmation.
   The reviewed file had sha256
   `81fc6bf4f41638584b53041d41139984be13c6391ba0e949c9b93bec5b04ee0c`.
   To undo, run the script again with mode 2 (remove), or delete the `fill_disk`
   folder. The "Update Your Kindle" menu item is grayed out afterwards.
4. Copy `kindle/dashboard.sh` into the Kindle's `documents` folder over USB.
5. Turn Airplane Mode off and connect to the home Wi Fi. The Pi must be serving
   `output/kindle/` on its LAN address, port 8080.
6. Tap `dashboard.sh` in the library. The dashboard appears and the loop runs.

## Stopping and restarting the loop

- Stop: create an empty file named `stop` inside `output/kindle/` on the Pi. The
  Kindle sees it within one cycle (up to 5 minutes) and ends the loop. Delete the
  file afterwards or the next start will exit immediately.
- Restart: tap `dashboard.sh` on the Kindle. It downloads the latest
  `kindle_run.sh` first.
- If the Kindle seems stuck, hold the power button for about 40 seconds to restart.

## Repeating this on another Kindle (outline)

One USB session to copy the jailbreak files, the hotfix and `dashboard.sh`, the
taps on the Kindle itself, then a second USB session for the storage fill. The Pi
side does not change. A Kindle with a different screen resolution needs its own
image size.
