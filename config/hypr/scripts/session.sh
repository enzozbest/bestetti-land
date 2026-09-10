#!/usr/bin/env bash
# Start session helpers once per user. Existing running helpers are respected.
set -eu
log_dir="${XDG_STATE_HOME:-$HOME/.local/state}/midnight-glass/logs"
mkdir -p "$log_dir"
start() {
    local process_name="$1"
    shift
    if command -v "$1" >/dev/null 2>&1 && ! pgrep -u "$(id -u)" -x "$process_name" >/dev/null; then
        "$@" >>"$log_dir/$process_name.log" 2>&1 &
    fi
}

start swaync swaync
start waybar waybar -c "$HOME/.config/waybar/config.jsonc" -s "$HOME/.config/waybar/style.css"
start hypridle hypridle
start blueman-applet blueman-applet
start easyeffects easyeffects --gapplication-service

if ! pgrep -u "$(id -u)" -f '[p]olkit-.*authentication-agent|[h]yprpolkitagent' >/dev/null; then
    if [[ -x /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 ]]; then
        /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 >>"$log_dir/polkit.log" 2>&1 &
    fi
fi

if ! pgrep -u "$(id -u)" -x swaybg >/dev/null; then
    "$HOME/.config/hypr/wallpaper.sh" >>"$log_dir/wallpaper.log" 2>&1 &
fi

# Enables your existing clipboard-history shortcut. Set this env var to 0 in
# local.lua before logging in to disable capture. Existing history is retained.
if [[ "${MIDNIGHT_CLIPBOARD_HISTORY:-1}" == 1 ]] && command -v cliphist >/dev/null 2>&1; then
    for clip_type in text image; do
        if ! pgrep -u "$(id -u)" -f "^wl-paste --type $clip_type --watch cliphist store$" >/dev/null; then
            wl-paste --type "$clip_type" --watch cliphist store >>"$log_dir/clipboard.log" 2>&1 &
        fi
    done
fi
