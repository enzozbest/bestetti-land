#!/usr/bin/env python3
"""Review, install, and roll back Midnight Glass for Hyprland 0.56+ (Lua)."""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
PRESERVE = {"hypr/local.lua"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".midnight-", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def paths(root=ROOT):
    result = [p.relative_to(root / "config") for p in (root / "config").rglob("*")
              if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    # The compositor watches this file: publish it after all its dependencies.
    return sorted(result, key=lambda p: (p.as_posix() == "hypr/hyprland.lua", p.as_posix()))


def check_destination(target, relative):
    destination = target / relative
    for component in (destination, *destination.parents):
        if component.is_symlink():
            raise RuntimeError(f"Symlink-managed config: {component}. Merge the supplied files through your dotfile manager.")
        if component == target:
            break
    if destination.exists() and not destination.is_file():
        raise RuntimeError(f"Expected a file at {destination}.")


def describe(target, root=ROOT):
    for relative in paths(root):
        path = target / relative
        action = "KEEP" if relative.as_posix() in PRESERVE and path.exists() else "REPLACE" if path.exists() else "CREATE"
        print(f"{action:7} {path}")


def command_output(*args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
    return p.returncode, p.stdout.strip()


def preflight(target):
    errors = []
    if target != Path.home() / ".config":
        errors.append("This kit uses ~/.config paths. A custom XDG_CONFIG_HOME needs the paths adapted first.")
    legacy_personal = target / "hypr/local.conf"
    if legacy_personal.is_file() and not (target / "hypr/local.lua").exists():
        active_lines = [line for line in legacy_personal.read_text().splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
        if active_lines:
            errors.append("Found personal overrides in hypr/local.conf. Translate them into hypr/local.lua first; it will be preserved and loaded last.")
    binary = shutil.which("Hyprland") or shutil.which("hyprland")
    if not binary:
        errors.append("Hyprland is not installed in this environment.")
    else:
        _, version = command_output(binary, "--version")
        print("Hyprland:", version.splitlines()[0] if version else "unknown")
        match = re.search(r"Hyprland\s+v?(\d+)\.(\d+)", version, re.I)
        if not match or (int(match[1]), int(match[2])) < (0, 56):
            errors.append("This Lua edition requires Hyprland 0.56 or newer. Upgrade the complete Arch system with `sudo pacman -Syu hyprland` first.")
    required = {
        "hyprctl": "hyprland", "waybar": "waybar", "wofi": "wofi",
        "swaync": "swaync", "swaync-client": "swaync", "hyprlock": "hyprlock",
        "hypridle": "hypridle", "swaybg": "swaybg", "kitty": "kitty",
        "wl-copy": "wl-clipboard", "wl-paste": "wl-clipboard", "cliphist": "cliphist",
        "grim": "grim", "slurp": "slurp", "notify-send": "libnotify",
        "wpctl": "wireplumber", "playerctl": "playerctl", "brightnessctl": "brightnessctl",
        "nmtui": "networkmanager", "thunar": "thunar", "blueman-manager": "blueman",
        "pgrep": "procps-ng", "pkill": "procps-ng", "pidof": "procps-ng",
    }
    missing = sorted({package for cmd, package in required.items() if not shutil.which(cmd)})
    if missing:
        errors.append("Missing packages providing configured commands: " + " ".join(missing))
    if not any(shutil.which(app) for app in ("pavucontrol", "pwvucontrol")):
        errors.append("Install an audio mixer: pavucontrol or pwvucontrol.")
    if not any(shutil.which(app) for app in ("firefox-developer-edition", "firefox")):
        errors.append("Install firefox-developer-edition or firefox, or adapt the browser action.")
    for cmd in ("waybar", "swaync", "hyprlock", "hypridle", "wofi"):
        if shutil.which(cmd):
            _, output = command_output(cmd, "--version")
            print(f"{cmd}: {output.splitlines()[0] if output else 'version not reported'}")
    if shutil.which("fc-match"):
        for family in ("Inter", "JetBrainsMono Nerd Font"):
            _, matched = command_output("fc-match", "-f", "%{family}", family)
            print(f"Font {family}: {matched}")
            if family.split()[0].lower() not in matched.replace(" ", "").lower():
                errors.append(f"Font missing or substituted: {family}. See the font packages in README.md.")
    for relative in paths():
        check_destination(target, relative)
    for error in errors:
        print("CHECK:", error)
    return not errors


@contextlib.contextmanager
def staged_config(target):
    with tempfile.TemporaryDirectory(prefix="midnight-stage-") as folder:
        root = Path(folder)
        shutil.copytree(ROOT / "config", root / "config", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        config_path = root / "config/swaync/config.json"
        config = json.loads(config_path.read_text())
        _, output = command_output("brightnessctl", "--machine-readable", "info")
        fields = output.splitlines()[0].split(",") if output else []
        if len(fields) >= 2 and fields[1] == "backlight":
            config["widget-config"]["backlight"]["device"] = fields[0]
            print("Backlight device:", fields[0])
        else:
            config["widgets"].remove("backlight")
            config["widget-config"].pop("backlight", None)
            print("No backlight device detected; the control-centre slider will be omitted.")
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
        yield root


def verify_compositor(target, root):
    binary = shutil.which("Hyprland") or shutil.which("hyprland")
    _, help_text = command_output(binary, "--help")
    if "--verify-config" not in help_text:
        print("This Hyprland build has no --verify-config option; runtime parser validation remains necessary after installation.")
        return
    with tempfile.TemporaryDirectory(prefix="midnight-verify-") as folder:
        stage = Path(folder) / "config"
        shutil.copytree(root / "config", stage)
        personal = target / "hypr/local.lua"
        if personal.exists():
            shutil.copy2(personal, stage / "hypr/local.lua")
        code, output = command_output(binary, "--verify-config", "--config", str(stage / "hypr/hyprland.lua"))
        if code:
            raise RuntimeError("Hyprland rejected the staged configuration:\n" + output)
        print("Hyprland accepted the staged configuration.")


def install_tree(target, backup_root, root=ROOT):
    files = paths(root)
    files = [p for p in files if not (p.as_posix() in PRESERVE and (target / p).exists())]
    for relative in files:
        check_destination(target, relative)
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-")
    backup = Path(tempfile.mkdtemp(prefix=stamp, dir=backup_root))
    records = []
    # Finish every backup before replacing any live file.
    for relative in files:
        destination = target / relative
        previous = destination.exists()
        if previous:
            saved = backup / "before" / relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, saved)
        records.append({"path": relative.as_posix(), "existed": previous,
                        "installed_sha256": digest(root / "config" / relative)})
    manifest = {"target": str(target.absolute()), "files": records, "format": 1}
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    attempted = []
    try:
        for record in records:
            attempted.append(record)
            atomic_copy(root / "config" / record["path"], target / record["path"])
    except BaseException:
        # Restore only files whose installation began; originals are still saved.
        for record in reversed(attempted):
            destination = target / record["path"]
            if record["existed"]:
                atomic_copy(backup / "before" / record["path"], destination)
            else:
                destination.unlink(missing_ok=True)
        raise
    return backup


def restore_tree(backup, expected_target):
    manifest = json.loads((backup / "manifest.json").read_text())
    target = Path(manifest["target"])
    if target != expected_target.absolute() or manifest.get("format") != 1:
        raise RuntimeError("This backup belongs to another config directory or format.")
    records = manifest["files"]
    changed = []
    for record in records:
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("Invalid path in backup manifest.")
        check_destination(target, relative)
        destination = target / relative
        if record["existed"] and not (backup / "before" / relative).is_file():
            raise RuntimeError(f"Missing backup: {relative}")
        if not destination.exists() or digest(destination) != record["installed_sha256"]:
            changed.append(relative)
    # Preserve work done since installation instead of silently discarding it.
    if changed:
        stash = backup / ("after-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        stash.mkdir(mode=0o700)
        for relative in changed:
            current = target / relative
            if current.is_file():
                saved = stash / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, saved)
        (stash / "changed-paths.json").write_text(json.dumps([str(p) for p in changed], indent=2))
        print("Saved edits made since installation:", stash)
    # Restore the main config last, after its dependencies have been restored.
    records = sorted(records, key=lambda r: r["path"] in {"hypr/hyprland.conf", "hypr/hyprland.lua"})
    for record in records:
        destination = target / record["path"]
        if record["existed"]:
            atomic_copy(backup / "before" / record["path"], destination)
        else:
            destination.unlink(missing_ok=True)
    print("Restored config files. Log out and back in to restore session processes.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Show changes and check local compatibility (default)")
    group.add_argument("--apply", action="store_true", help="Back up and install after local checks")
    group.add_argument("--restore", type=Path, metavar="BACKUP", help="Restore an installation backup")
    args = parser.parse_args()
    target = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))).absolute()
    if args.restore:
        restore_tree(args.restore.expanduser().absolute(), target)
        return
    describe(target)
    valid = preflight(target)
    if not valid:
        raise RuntimeError("No files changed. Resolve the checks above before applying.")
    with staged_config(target) as root:
        verify_compositor(target, root)
        if not args.apply:
            print("Checks complete. To install: python3 install.py --apply")
            return
        if os.geteuid() == 0:
            raise RuntimeError("Run as your desktop user, without sudo.")
        state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        backup = install_tree(target, state / "midnight-glass/backups", root=root)
    print("Installed. Backup:", backup)
    print("Next: log out and back in so Hyprland loads hyprland.lua; then run `hyprctl configerrors`.")
    print("If your session command explicitly selects hyprland.conf, change it to hyprland.lua (or remove the custom --config flag).")
    print("Rollback: python3 install.py --restore", str(backup))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
