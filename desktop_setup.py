"""Dependency provisioning and reversible app defaults, used by install.py.

No commands run on import. Package installation is separate from the reversible
configuration transaction; pacman and Flatpak retain their normal prompts.
"""
import ast
import configparser
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

SCHEMA = "org.gnome.desktop.interface"
DCONF_ROOT = "/org/gnome/desktop/interface/"
AUDIO_APP = "com.saivert.pwvucontrol"
INTERFACE_KEYS = {
    "gtk-theme", "color-scheme", "icon-theme", "font-name",
    "monospace-font-name", "accent-color",
}
GENERATED_FILES = (
    "gtk-3.0/settings.ini", "gtk-4.0/settings.ini",
    "mimeapps.list", "hyprland-mimeapps.list",
)
COMMAND_PACKAGES = {
    "bash": "bash", "hyprctl": "hyprland", "waybar": "waybar",
    "wofi": "wofi", "swaync": "swaync", "swaync-client": "swaync",
    "hyprlock": "hyprlock", "hypridle": "hypridle", "swaybg": "swaybg",
    "kitty": "kitty", "wl-copy": "wl-clipboard", "wl-paste": "wl-clipboard",
    "cliphist": "cliphist", "grim": "grim", "slurp": "slurp",
    "notify-send": "libnotify", "wpctl": "wireplumber",
    "playerctl": "playerctl", "brightnessctl": "brightnessctl",
    "nmcli": "networkmanager", "networkmanager_dmenu": "networkmanager-dmenu",
    "nm-connection-editor": "nm-connection-editor",
    "blueman-manager": "blueman", "blueman-applet": "blueman",
    "nautilus": "nautilus", "loupe": "loupe", "papers": "papers",
    "gsettings": "glib2", "gdbus": "glib2", "dconf": "dconf",
    "nwg-look": "nwg-look", "xdg-mime": "xdg-utils", "fc-match": "fontconfig",
    "pgrep": "procps-ng", "pkill": "procps-ng", "pidof": "procps-ng",
    "loginctl": "systemd", "systemctl": "systemd",
}
ASSET_PACKAGES = {
    "/usr/share/themes/adw-gtk3-dark/gtk-3.0/gtk.css": "adw-gtk-theme",
    "/usr/share/icons/Papirus-Dark/index.theme": "papirus-icon-theme",
    "/usr/share/glib-2.0/schemas/org.gnome.desktop.interface.gschema.xml": "gsettings-desktop-schemas",
    "/usr/share/applications/org.gnome.Nautilus.desktop": "nautilus",
    "/usr/share/applications/org.gnome.Loupe.desktop": "loupe",
    "/usr/share/applications/org.gnome.Papers.desktop": "papers",
}
FONT_PACKAGES = {"Inter": "inter-font", "JetBrainsMono Nerd Font": "ttf-jetbrains-mono-nerd"}


def query(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=15)


def checked(*args):
    result = query(*args)
    if result.returncode:
        raise RuntimeError(f"{shlex.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def run_visible(*args):
    print("RUN:", shlex.join(args), flush=True)
    subprocess.run(args, check=True)


def audio_installation():
    if shutil.which("pwvucontrol"):
        return "native"
    if shutil.which("flatpak"):
        for scope in ("--user", "--system"):
            if query("flatpak", "info", scope, AUDIO_APP).returncode == 0:
                return scope
    return None


def font_matches(family):
    if not shutil.which("fc-match"):
        return False
    result = query("fc-match", "-f", "%{family}", family)
    wanted = family.replace(" ", "").casefold()
    names = [name.replace(" ", "").casefold() for name in result.stdout.split(",")]
    return result.returncode == 0 and wanted in names


def missing_packages():
    missing = {package for command, package in COMMAND_PACKAGES.items() if not shutil.which(command)}
    missing.update(package for path, package in ASSET_PACKAGES.items() if not Path(path).is_file())
    missing.update(package for font, package in FONT_PACKAGES.items() if not font_matches(font))
    binary = shutil.which("Hyprland") or shutil.which("hyprland")
    if not binary:
        missing.add("hyprland")
    else:
        result = query(binary, "--version")
        version = re.search(r"Hyprland\s+v?(\d+)\.(\d+)", result.stdout, re.I)
        if version and tuple(map(int, version.groups())) < (0, 56):
            missing.add("hyprland")
    if not any(shutil.which(app) for app in ("firefox-developer-edition", "firefox")):
        missing.add("firefox")
    # Keep a native pwvucontrol installation; otherwise provision the supported Flatpak.
    if not shutil.which("pwvucontrol") and not shutil.which("flatpak"):
        missing.add("flatpak")
    return sorted(missing)


def require_session():
    if os.geteuid() == 0:
        raise RuntimeError("Run as your desktop user, without sudo.")
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        raise RuntimeError("Run --apply from a terminal in your graphical session.")
    if os.environ.get("GSETTINGS_BACKEND", "dconf") != "dconf":
        raise RuntimeError("This installer needs the persistent dconf GSettings backend.")
    checked("gdbus", "call", "--session", "--dest", "org.freedesktop.DBus",
            "--object-path", "/org/freedesktop/DBus", "--method", "org.freedesktop.DBus.ListNames")


def ensure_dependencies():
    missing = missing_packages()
    if missing:
        if not shutil.which("pacman") or not shutil.which("sudo"):
            raise RuntimeError("Automatic package installation requires Arch Linux, pacman and sudo. "
                               "Missing packages: " + " ".join(missing))
        # -Syu avoids an unsupported partial Arch upgrade. No --noconfirm.
        run_visible("sudo", "pacman", "-Syu", "--needed", *missing)
    if not audio_installation():
        if not shutil.which("flatpak"):
            raise RuntimeError("Flatpak is unavailable after package installation.")
        run_visible("flatpak", "remote-add", "--user", "--if-not-exists", "flathub",
                    "https://flathub.org/repo/flathub.flatpakrepo")
        run_visible("flatpak", "install", "--user", "flathub", AUDIO_APP)
        if not audio_installation():
            raise RuntimeError("pwvucontrol was not installed; desktop configuration has not been applied.")


def load_defaults(path):
    defaults = json.loads(path.read_text())
    interface, mime = defaults.get("interface"), defaults.get("mime")
    if not isinstance(interface, dict) or set(interface) != INTERFACE_KEYS:
        raise ValueError("app-defaults.json must define the six supported interface settings.")
    if not all(isinstance(value, str) and value for value in interface.values()):
        raise ValueError("Interface preferences must be nonempty strings.")
    if not isinstance(mime, dict) or not mime:
        raise ValueError("app-defaults.json must define MIME defaults.")
    for kind, app in mime.items():
        if not re.fullmatch(r"[\w.+-]+/[\w.+-]+", kind) or not isinstance(app, str) or not re.fullmatch(r"[\w.+-]+\.desktop", app):
            raise ValueError("Invalid MIME type or desktop file in app-defaults.json.")
    return defaults


def supported_settings(defaults):
    available = set(checked("gsettings", "list-keys", SCHEMA).splitlines())
    settings = {}
    for key, value in defaults["interface"].items():
        if key == "accent-color" and key not in available:
            print("NOTE: this schema has no accent-color key; keeping the toolkit's accent.")
            continue
        if key not in available:
            raise RuntimeError(f"Missing GSettings key {SCHEMA}.{key}; update gsettings-desktop-schemas.")
        if checked("gsettings", "writable", SCHEMA, key) != "true":
            raise RuntimeError(f"GSettings key {SCHEMA}.{key} is locked.")
        # Validate enum values before making any live changes.
        value_range = checked("gsettings", "range", SCHEMA, key).splitlines()
        if value_range and value_range[0] == "enum":
            allowed = [ast.literal_eval(item) for item in value_range[1:]]
            if value not in allowed:
                raise RuntimeError(f"Unsupported {key}: {value!r}; choose one of {allowed}.")
        settings[key] = value
    return settings


def read_ini(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if path.exists():
        with path.open() as source:
            parser.read_file(source)
    return parser


def merge_ini(source, destination, sections):
    parser = read_ini(source)
    for name, values in sections.items():
        if not parser.has_section(name):
            parser.add_section(name)
        parser[name].update(values)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w") as output:
        parser.write(output)
    destination.chmod(source.stat().st_mode & 0o777 if source.exists() else 0o644)


def stage_defaults(target, stage, defaults):
    interface = defaults["interface"]
    settings = {
        "gtk-icon-theme-name": interface["icon-theme"],
        "gtk-font-name": interface["font-name"],
        "gtk-application-prefer-dark-theme": "1" if interface["color-scheme"] == "prefer-dark" else "0",
    }
    merge_ini(target / GENERATED_FILES[0], stage / GENERATED_FILES[0],
              {"Settings": {**settings, "gtk-theme-name": interface["gtk-theme"]}})
    merge_ini(target / GENERATED_FILES[1], stage / GENERATED_FILES[1], {"Settings": settings})
    associations = {kind: app + ";" for kind, app in defaults["mime"].items()}
    for relative in GENERATED_FILES[2:]:
        merge_ini(target / relative, stage / relative, {"Default Applications": associations})


def snapshot_settings(settings):
    # Preserve the distinction between an explicit value and a schema default.
    return {key: checked("dconf", "read", DCONF_ROOT + key) or None for key in settings}


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or not set(snapshot).issubset(INTERFACE_KEYS):
        raise ValueError("Invalid desktop settings backup.")
    if any(value is not None and not isinstance(value, str) for value in snapshot.values()):
        raise ValueError("Invalid value in desktop settings backup.")


def apply_settings(settings):
    for key, value in settings.items():
        checked("gsettings", "set", SCHEMA, key, json.dumps(value))
        actual = ast.literal_eval(checked("gsettings", "get", SCHEMA, key))
        if actual != value:
            raise RuntimeError(f"{key} did not persist: expected {value!r}, got {actual!r}.")


def restore_settings(snapshot):
    validate_snapshot(snapshot)
    errors = []
    for key, value in snapshot.items():
        try:
            if value is None:
                checked("gsettings", "reset", SCHEMA, key)
            else:
                checked("gsettings", "set", SCHEMA, key, value)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            errors.append(str(exc))
    return errors


def verify_defaults(defaults):
    # Higher-priority desktop-specific associations or stale session state can
    # explain a mismatch; don't silently report a completely configured desktop.
    for kind, app in defaults["mime"].items():
        try:
            actual = checked("xdg-mime", "query", "default", kind)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f"NOTE: installed the default for {kind}, but could not verify it: {exc}")
            continue
        if actual != app:
            print(f"NOTE: {kind} currently resolves to {actual or '(none)'}, expected {app}. "
                  "Log back into Hyprland and check the MIME associations.")
