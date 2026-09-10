#!/usr/bin/env python3
"""Desktop actions for Midnight Glass. Standard library only; no shell eval."""
import contextlib
import datetime
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


def run(*args, data=None, check=True):
    return subprocess.run(args, input=data, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=check)


def text(*args, **kwargs):
    return run(*args, **kwargs).stdout.decode("utf-8", "replace").strip()


def dispatch(expression, *, check=True):
    """Hyprland 0.56 native dispatcher expression; caller supplies trusted Lua."""
    return run("hyprctl", "dispatch", expression, check=check)


def set_dim(enabled, *, check=True):
    value = "true" if enabled else "false"
    return run("hyprctl", "eval", f"hl.config({{ decoration = {{ dim_inactive = {value} }} }})", check=check)


def launch(*args):
    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def notify(title, body="", *, value=None, category="midnight", urgency="normal"):
    if not shutil.which("notify-send"):
        return
    args = ["notify-send", "-a", "Midnight", "-u", urgency, "-t", "1800",
            "-h", f"string:x-canonical-private-synchronous:{category}"]
    if value is not None:
        args += ["-h", f"int:value:{max(0, min(100, int(value)))}",
                 "-h", "boolean:transient:true"]
    run(*args, "--", title, body, check=False)


def clean(value):
    return " ".join(str(value).split())


def menu(prompt, lines):
    result = run("wofi", "--dmenu", "--prompt", prompt, "--width", "640",
                 "--height", "420", data=("\n".join(lines) + "\n").encode(), check=False)
    return result.stdout.decode("utf-8", "replace").rstrip("\n") if result.returncode == 0 else ""


def browser():
    for candidate in ("firefox-developer-edition", "firefox"):
        if shutil.which(candidate):
            launch(candidate)
            return
    raise RuntimeError("Firefox is not installed.")


def windows():
    clients = json.loads(text("hyprctl", "-j", "clients"))
    choices = {}
    for i, client in enumerate(clients, 1):
        address = client.get("address", "")
        if not re.fullmatch(r"0x[0-9a-fA-F]+", address):
            continue
        ws = clean(client.get("workspace", {}).get("name", "?"))
        label = f"{i:02d}  [{ws}]  {clean(client.get('class', 'App'))} — {clean(client.get('title', ''))}"
        choices[label] = address
    if not choices:
        notify("No open windows")
        return
    chosen = menu("Jump to a window…", choices)
    if chosen in choices:
        # Addresses are validated above; titles never become Lua or shell code.
        dispatch(f'hl.dsp.focus({{ window = "address:{choices[chosen]}" }})')


def terminal():
    # Serialize quick repeated presses so they cannot create duplicate terminals.
    with action_lock("terminal"):
        clients = json.loads(text("hyprctl", "-j", "clients"))
        pending = runtime() / "terminal-pending"
        exists = any(c.get("class") == "midnight-terminal" for c in clients)
        recently_launched = pending.exists() and time.time() - pending.stat().st_mtime < 5
        if exists:
            pending.unlink(missing_ok=True)
        elif not recently_launched:
            launch("kitty", "--class", "midnight-terminal", "--title", "Terminal",
                   "-o", "background=#181825", "-o", "foreground=#cdd6f4",
                   "-o", "background_opacity=0.92", "-o", "window_padding_width=18")
            pending.touch()
        dispatch('hl.dsp.workspace.toggle_special("terminal")')


def terminal_here():
    # /proc reports the application's cwd. GUI apps may only report your home.
    client = json.loads(text("hyprctl", "-j", "activewindow"))
    try:
        cwd = Path(f"/proc/{int(client['pid'])}/cwd").resolve(strict=True)
    except (KeyError, OSError, ValueError):
        cwd = Path.home()
    launch("kitty", "--directory", str(cwd))


def clipboard():
    history = run("cliphist", "list").stdout
    if not history.strip():
        notify("Clipboard history is empty")
        return
    picked = run("wofi", "--dmenu", "--prompt", "Clipboard…", data=history, check=False)
    if picked.returncode or not picked.stdout.strip():
        return
    decoded = run("cliphist", "decode", data=picked.stdout).stdout
    run("wl-copy", data=decoded)


def screenshot(mode):
    if mode not in ("region", "screen"):
        raise RuntimeError("Screenshot mode must be region or screen.")
    args = ["grim"]
    if mode == "region":
        selection = run("slurp", check=False)
        geometry = selection.stdout.decode().strip()
        if selection.returncode or not geometry:
            return  # Esc cancels: no file and no clipboard replacement.
        args += ["-g", geometry]
    elif mode == "screen":
        monitors = json.loads(text("hyprctl", "-j", "monitors"))
        focused = next((m["name"] for m in monitors if m.get("focused")), None)
        if not focused:
            raise RuntimeError("Could not determine the focused monitor.")
        args += ["-o", focused]
    if shutil.which("xdg-user-dir"):
        pictures = text("xdg-user-dir", "PICTURES")
    else:
        pictures = ""
    destination = Path(pictures or Path.home() / "Pictures") / "Screenshots"
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_")
    fd, filename = tempfile.mkstemp(prefix="shot-" + stamp, suffix=".png", dir=destination)
    os.close(fd)
    path = Path(filename)
    try:
        run(*args, str(path))
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    copy = run("wl-copy", "--type", "image/png", data=path.read_bytes(), check=False)
    suffix = "Copied to clipboard" if copy.returncode == 0 else "Saved; clipboard copy failed"
    notify("Screenshot saved", f"{suffix}\n{path}")


def lock():
    if run("pgrep", "-u", str(os.getuid()), "-x", "hyprlock", check=False).returncode:
        launch("hyprlock")


def power():
    choices = ["Lock", "Suspend", "Log out", "Restart", "Shut down"]
    chosen = menu("Session", choices)
    if chosen == "Lock":
        lock()
    elif chosen == "Suspend":
        # Require the daemon configured to wait for a Wayland lock before sleep.
        if run("pgrep", "-u", str(os.getuid()), "-x", "hypridle", check=False).returncode:
            raise RuntimeError("Start hypridle before using Suspend; see README.md.")
        run("systemctl", "suspend")
    elif chosen in ("Log out", "Restart", "Shut down"):
        if menu(f"{chosen}? Save your work first.", ["Cancel", chosen]) != chosen:
            return
        if chosen == "Log out":
            if shutil.which("uwsm") and run("uwsm", "check", "is-active", check=False).returncode == 0:
                launch("uwsm", "stop")
            elif shutil.which("hyprshutdown"):
                launch("hyprshutdown")
            else:
                dispatch("hl.dsp.exit()")
        else:
            run("systemctl", "reboot" if chosen == "Restart" else "poweroff")


def volume(direction):
    target = "@DEFAULT_AUDIO_SINK@"
    if direction == "mute":
        run("wpctl", "set-mute", target, "toggle")
    elif direction in ("up", "down"):
        run("wpctl", "set-volume", "-l", "1", target, "5%+" if direction == "up" else "5%-")
    else:
        raise RuntimeError("Volume action must be up, down or mute.")
    state = text("wpctl", "get-volume", target)
    value = round(float(state.split()[1]) * 100)
    notify("Muted" if "MUTED" in state else f"Volume {value}%", value=value, category="volume")


def brightness(direction):
    if direction not in ("up", "down"):
        raise RuntimeError("Brightness action must be up or down.")
    run("brightnessctl", "-e4", "-n2", "set", "5%+" if direction == "up" else "5%-")
    value = round(100 * int(text("brightnessctl", "get")) / int(text("brightnessctl", "max")))
    notify(f"Brightness {value}%", value=value, category="brightness")


def runtime():
    base = os.environ.get("XDG_RUNTIME_DIR")
    if not base:
        raise RuntimeError("XDG_RUNTIME_DIR is not set; run this inside your Hyprland session.")
    signature = re.sub(r"[^A-Za-z0-9_.-]", "_", os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "session"))
    folder = Path(base) / ("midnight-glass-" + signature)
    folder.mkdir(mode=0o700, exist_ok=True)
    return folder


@contextlib.contextmanager
def action_lock(name):
    with (runtime() / (name + ".lock")).open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def set_dnd(enabled):
    run("swaync-client", "-dn" if enabled else "-df")


def focus(off=False):
    with action_lock("focus"):
        state_file = runtime() / "focus.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            set_dim(state["dim"])
            set_dnd(state["dnd"])
            state_file.unlink()
            notify("Focus mode off", "Previous dimming and notification settings restored")
        elif not off:
            option = json.loads(text("hyprctl", "-j", "getoption", "decoration:dim_inactive"))
            dnd_value = text("swaync-client", "-D").lower()
            if dnd_value not in ("true", "false"):
                raise RuntimeError("Could not read notification state; focus mode was not changed.")
            dim = option.get("int", option.get("bool"))
            if dim not in (0, 1, False, True):
                raise RuntimeError("Could not read dimming state; focus mode was not changed.")
            state = {"dim": int(dim), "dnd": dnd_value == "true"}
            state_file.write_text(json.dumps(state))
            try:
                set_dim(True)
                set_dnd(True)
            except BaseException:
                set_dim(state["dim"], check=False)
                run("swaync-client", "-dn" if state["dnd"] else "-df", check=False)
                state_file.unlink(missing_ok=True)
                raise
            # DND intentionally suppresses this message; the bar changes its icon.


def reload_config():
    focus(off=True)
    run("hyprctl", "reload")
    errors = text("hyprctl", "configerrors")
    if errors and errors.lower() != "ok":
        raise RuntimeError(errors)
    run("swaync-client", "-R", check=False)
    run("swaync-client", "-rs", check=False)
    # SIGUSR2 reloads Waybar config/style. No global kill-and-relaunch.
    run("pkill", "-USR2", "-u", str(os.getuid()), "-x", "waybar", check=False)
    notify("Desktop reloaded")


def tools_menu():
    chosen = menu("System tools", ["System monitor", "GPU monitor", "Network", "Audio", "Bluetooth"])
    if chosen == "System monitor":
        monitor = next((p for p in ("btop", "htop", "top") if shutil.which(p)), None)
        if monitor:
            launch("kitty", "--class", "midnight-tools", "-e", monitor)
    elif chosen == "GPU monitor":
        if not shutil.which("nvtop"):
            raise RuntimeError("Install nvtop to use the GPU monitor.")
        launch("kitty", "--class", "midnight-tools", "-e", "nvtop")
    elif chosen == "Network":
        launch("kitty", "--class", "midnight-tools", "-e", "nmtui")
    elif chosen == "Audio":
        audio()
    elif chosen == "Bluetooth":
        launch("blueman-manager")


def audio():
    for app in ("pwvucontrol", "pavucontrol"):
        if shutil.which(app):
            launch(app)
            return
    raise RuntimeError("Install pavucontrol or pwvucontrol for the audio mixer.")


def help_menu():
    menu("Midnight Glass · shortcuts", [
        "Super + Space                 Applications",
        "Super + Shift + Space         Search open windows",
        "Super + `                     Drop-down terminal",
        "Super + N                     Control centre",
        "Super + Shift + N             Do Not Disturb",
        "Super + Shift + V             Clipboard history",
        "Super + G                     Focus mode",
        "Super + L                     Lock",
        "Super + M                     Session menu",
        "Print                         Region → file + clipboard",
        "Super + Ctrl + Print          Focused monitor screenshot",
        "Super + Shift + arrows        Move window",
        "Super + Ctrl + arrows         Resize window",
        "Super + Shift + F             Maximise inside the work area",
        "Super + Ctrl + R              Reload desktop",
    ])


def main(args):
    if not args:
        raise RuntimeError("Choose an action; see README.md.")
    actions = {"launcher": lambda: launch("wofi", "--show", "drun"),
               "browser": browser, "windows": windows, "terminal": terminal,
               "terminal-here": terminal_here, "clipboard": clipboard,
               "lock": lock, "power": power, "focus": focus,
               "focus-off": lambda: focus(off=True), "reload": reload_config,
               "tools": tools_menu, "audio": audio, "help": help_menu}
    if args[0] in ("screenshot", "volume", "brightness") and len(args) == 2:
        {"screenshot": screenshot, "volume": volume, "brightness": brightness}[args[0]](args[1])
    elif args[0] in actions and len(args) == 1:
        actions[args[0]]()
    else:
        raise RuntimeError("Unknown action: " + " ".join(args))


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        message = exc.stderr.decode("utf-8", "replace") if isinstance(exc, subprocess.CalledProcessError) else str(exc)
        print(message, file=sys.stderr)
        notify("Midnight Glass", message[:400], urgency="critical")
        sys.exit(1)
