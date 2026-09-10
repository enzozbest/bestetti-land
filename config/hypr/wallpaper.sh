#!/usr/bin/env bash
set -eu
# Reuses your current wallpaper. No new image is required.
wallpaper_file="${MIDNIGHT_WALLPAPER:-$HOME/Pictures/Wallpapers/backdrop.png}"
if [[ -f "$wallpaper_file" ]]; then
    exec swaybg -i "$wallpaper_file" -m fill
else
    exec swaybg -c '#11111b'
fi
