# Midnight Glass

Enzo's Arch Linux desktop: Hyprland with native Lua configuration, a larger glass Waybar with top-edge auto-hide, a matching launcher and control centre, and coordinated everyday applications.

## Install or update

Use **Hyprland 0.56 or newer** and run the installer from a terminal in your graphical session as your desktop user. This repository uses the native 0.56 Lua API; later breaking API changes may need adjustments. Hyprlock and Hypridle retain their own `.conf` formats. [Hyprland 0.56 documentation](https://wiki.hypr.land/0.56.0/Configuring/Start/)

The starting point is a working Arch installation with Hyprland, NetworkManager, Bluetooth and PipeWire configured for your hardware. The installer checks and installs application dependencies; it does not enable system services, change network backends, configure drivers or replace your display manager.

From the repository directory:

```bash
python3 install.py --check
python3 install.py --apply
```

`--check` is also the default when no argument is supplied. It reports missing dependencies, lists configuration and preference changes, detects the backlight, and validates a temporary copy with your Hyprland binary when `--verify-config` is available. It never installs packages or changes live preferences/configuration. Missing dependencies make this check exit with an error; `--apply` can provision them.

`--apply` performs the complete setup:

1. Reject root execution, unsupported config paths and symlink-managed destinations before changing anything.
2. Install missing Arch dependencies with `sudo pacman -Syu --needed …`. This includes a full system upgrade when package installation is needed; pacman's normal confirmation prompts remain enabled. When the dependencies already exist, this step is skipped.
3. Use an existing native or user/system Flatpak pwvucontrol installation. Otherwise add Flathub for your user and install `com.saivert.pwvucontrol`, retaining Flatpak's normal prompts.
4. Check commands, theme/icon assets, fonts, the compositor version, and writable/supported GSettings values. Detect the backlight and verify staged Lua before copying live configs.
5. Back up affected files and the previous values of the appearance preferences, including whether each preference was explicitly set or inherited from its schema.
6. Install the repository's configuration, merge GTK settings and MIME defaults, and apply/verify the appearance preferences through `gsettings`. Preserve existing `hypr/local.lua` and publish the compositor entry point after its dependencies.

The full installer treats this repository's `config/` tree as the source of truth. Commit any live shell customisations you want to keep into that tree before applying. GTK settings and MIME files are merged, retaining unrelated settings; their comments/formatting are normalised. No GTK CSS, cursor settings or GTK4 theme links are generated or removed.

If dependencies are managed separately, use:

```bash
python3 install.py --apply --skip-packages
```

This still checks dependencies and performs the configuration/preference setup. It does not run pacman or install Flatpaks. Keep `desktop_setup.py` beside `install.py`; the installer imports it automatically, so no separate setup command is needed.

**Log out and back in after installation.** Hyprland's reload does not restart the whole session, refresh every application or replace a running compositor after a package upgrade. If your session command explicitly selects `hyprland.conf`, change it to `hyprland.lua` or remove that custom `--config` argument. The legacy `.conf` is retained.

Then run:

```bash
hyprctl configerrors
```

Test Super + E, the Network and Audio controls, opening an image/PDF, and locking/unlocking with Super + L. Session helpers already running are respected. A pre-existing Waybar service must use `~/.config/waybar/config.jsonc` and `~/.config/waybar/style.css`.

## Applications

| Area | Application and integration |
| --- | --- |
| Network | `networkmanager-dmenu` using the existing Wofi theme. Available from Waybar, SwayNC and the system-tools menu. Right-click Waybar's network module for `nm-connection-editor`. Password entry is obscured. |
| Bluetooth | Blueman manager and applet, using the shared GTK appearance. |
| Audio | pwvucontrol, selected in order: native executable, user Flatpak, system Flatpak. pavucontrol remains a runtime fallback if pwvucontrol is subsequently removed. Waybar right-click, SwayNC and the tools menu share this action. |
| Files | Nautilus on Super + E and as the default folder handler. |
| Images | Loupe for JPEG, PNG, WebP, GIF and AVIF. |
| Documents | Papers for PDFs. |
| Browser / terminal | Existing Firefox or Firefox Developer Edition, and Kitty. |

The network connection editor joins the existing centred floating utility rule. Normal file-manager windows continue to tile. Audio and Bluetooth backends remain the existing system services. [Network menu configuration](https://github.com/firecat53/networkmanager-dmenu), [pwvucontrol installation](https://github.com/saivert/pwvucontrol), [Files](https://apps.gnome.org/Nautilus/), [Loupe](https://apps.gnome.org/Loupe/), [Papers](https://apps.gnome.org/Papers/)

## App appearance and defaults

Edit **`config/hypr/app-defaults.json`** in the repository to version the preferences that the installer applies:

| Preference | Default |
| --- | --- |
| GTK3 theme | `adw-gtk3-dark` |
| Colour scheme | `prefer-dark` |
| Icons | `Papirus-Dark` |
| Interface font | `Inter 12` |
| Monospace font | `JetBrainsMono Nerd Font 11` |
| Accent | `purple`, where the toolkit supports it |

Modern libadwaita apps use their native dark appearance. The GTK3 theme approximates that appearance for older apps. If an older installed schema lacks `accent-color`, the installer reports this and skips that one preference. Other missing, locked or invalid preferences stop installation. [adw-gtk3](https://github.com/lassekongo83/adw-gtk3)

`desktop_setup.py` applies the equivalent of the theme/font `gsettings set` commands and writes the selected default-application associations. It merges these files into the existing live configuration:

```text
~/.config/gtk-3.0/settings.ini
~/.config/gtk-4.0/settings.ini
~/.config/mimeapps.list
~/.config/hyprland-mimeapps.list
```

The Hyprland-specific MIME file prevents an older override from keeping Thunar or another viewer as the default. The generic MIME defaults and GSettings preferences are shared by the same user in other sessions, including GNOME. The installer does not reapply them on every login: future changes persist until you run the installer again. `nwg-look` remains available as a GUI for appearance settings; the installer performs targeted merges rather than its broad export operation.

## Dependencies

`desktop_setup.py` is the executable source of the command, asset and font dependency checks. Required commands and packages include:

```text
python bash hyprland waybar wofi swaync hyprlock hypridle swaybg kitty
wl-clipboard cliphist grim slurp libnotify wireplumber playerctl brightnessctl
networkmanager networkmanager-dmenu nm-connection-editor blueman
nautilus loupe papers glib2 dconf gsettings-desktop-schemas
adw-gtk-theme papirus-icon-theme nwg-look xdg-utils fontconfig
inter-font ttf-jetbrains-mono-nerd procps-ng systemd
```

Firefox is installed if neither supported Firefox executable exists. Flatpak is needed when native pwvucontrol is absent; the installer recognises an existing user or system installation instead of downloading a duplicate. Thunar and native pavucontrol are no longer installation requirements. [Arch network menu](https://archlinux.org/packages/extra/any/networkmanager-dmenu/), [Arch theme](https://archlinux.org/packages/extra/any/adw-gtk-theme/)

NetworkManager's Python/GObject/libnm requirements and the GTK/GVfs libraries used by the apps are installed through their Arch package dependencies. Optional existing session helpers are `easyeffects` and `polkit-gnome`; the session script also respects an already-running Hyprpolkitagent. Keep a working authentication agent for operations that need authorisation. `btop`, `htop` and `nvtop` provide richer system monitors; the CPU tools menu falls back to `top`.

## Waybar

The continuous glass bar requests **56px height**, with **17px interface text**, larger icons, active-window titles and media information. CPU, RAM and tray items remain visible while the bar is shown.

After the initial preview, the bar hides about **1.2 seconds** after the pointer leaves. Rest the pointer in the top **3 logical pixels** for about **0.15 seconds** to reveal it. This works during ordinary tiled use and fullscreen use.

| Action | Control |
| --- | --- |
| Pin open / return to auto-hide | Super + B |
| Show briefly | Super + Shift + B |
| Reload bar and timing preferences | Super + Ctrl + R |

The bar overlays windows and reserves no space, including when pinned. Bars belonging to the same Waybar process reveal together. Pin the bar while using tray menus that extend below it. Pinning lasts for the session; the next login returns to auto-hide.

Timing lives in `config/waybar/autohide.json`. If you change the bar height or top margin, update `bar-height` and `margin-top` there as well. Reload just Waybar with:

```bash
python3 ~/.config/hypr/scripts/waybar-control.py reload
```

Other helper actions include `status`, `pin` and `auto`. **SIGUSR2 hides the bar**; it is not the reload signal in this configuration. Logs live in `~/.local/state/midnight-glass/logs/waybar-autohide.log`. If compositor queries fail, the helper attempts to keep the bar visible.

Opacity is in `config/waybar/style.css`, inside `MIDNIGHT WAYBAR PANEL`: the last number of each `rgba(...)` gradient stop is its alpha. The repository currently uses **0.84 at the top and 0.50 at the bottom**. These values and the working SwayNC/Waybar styles are carried through this app integration unchanged. [Waybar configuration](https://github.com/Alexays/Waybar/wiki/Configuration), [Hyprland IPC](https://wiki.hypr.land/IPC/)

## Shortcuts

`Super` is the Windows key.

| Keys | Action |
| --- | --- |
| Super + Space / D / R | Applications |
| Super + Shift + Space | Search open windows |
| Super + grave/backtick | Dedicated drop-down terminal |
| Super + Return / Q | Kitty |
| Super + Shift + Return | Kitty in the active app's reported working directory, falling back to home |
| Super + E / W | Nautilus / Firefox |
| Super + B / Shift + B | Pin Waybar / show briefly |
| Super + N / Shift + N | Control centre / Do Not Disturb |
| Super + Shift + V | Clipboard history |
| Super + G / Shift + G | Toggle focus mode / restore pre-focus settings |
| Super + L | Lock |
| Super + M / Shift + P | Session menu with confirmations |
| Print / Super + Print / Super + Shift + Print | Region screenshot, saved and copied |
| Super + Ctrl + Print | Focused-monitor screenshot, saved and copied |
| Super + arrows | Focus neighbour |
| Super + Shift + arrows | Move window |
| Super + Ctrl + arrows | Resize window |
| Super + F / Shift + F | Fullscreen / maximise within the work area |
| Super + V | Toggle floating |
| Super + T | Toggle group |
| Super + Tab / Shift + Tab | Next/previous grouped window |
| Super + 1…0 | Workspaces 1…10 |
| Super + Shift + 1…0 | Move window to workspace |
| Super + S / Shift + S | Toggle magic workspace / move window into it |
| Super + Z / Shift + Z | Disable/enable focus following the pointer |
| Super + Ctrl + R | Restore focus-mode state and reload Hyprland, SwayNC and Waybar |
| Super + slash | Shortcut list |

## Compositor and session tuning

Use `~/.config/hypr/local.lua` for personal overrides; an existing copy is preserved during installation. Hardware lives in `conf/hardware.lua`, appearance in `conf/appearance.lua`, animations in `conf/animations.lua`, and bindings/rules in their corresponding Lua modules. `conf/common.lua` defines the terminal, file manager and modifier.

The supplied monitor modes, scale 1, GB keyboard and NVIDIA environment values come from Enzo's original setup. Check `hyprctl monitors` and adapt `hardware.lua` for different hardware. The fallback monitor rule uses each additional output's preferred mode. Windows have 16px rounding, lavender/blue focus borders and restrained shadows; normal application content remains opaque.

The wallpaper script reuses `~/Pictures/Wallpapers/backdrop.png`, with a solid midnight fallback. Override the path in `local.lua` and log in again:

```lua
hl.env("MIDNIGHT_WALLPAPER", "/absolute/path/to/wallpaper.png")
```

Clipboard history starts at login. Disable capture with `hl.env("MIDNIGHT_CLIPBOARD_HISTORY", "0")` in `local.lua`, then log in again. Existing history remains until cleared with `cliphist wipe`.

Hypridle locks after five minutes and turns displays off after six; it has no automatic suspend timer. The Waybar keep-awake control inhibits idle. SwayNC uses targeted transparent backdrop rules and its own stylesheet priority, with detected backlight controls and automatic hiding of empty media widgets.

## Rollback

Use the backup path printed by the installer, as your desktop user:

```bash
python3 install.py --restore /path/printed/by/the/installer
```

This restores original files and removes files introduced by that installation. It also restores the saved appearance preferences, using schema defaults again for keys that were previously unset. Later configuration edits are copied into an `after-*` directory; current desktop preferences are saved to an `after-desktop-*.json` file before restoration. Old backups without desktop-preference metadata remain supported.

If copying files or applying preferences fails during installation, the installer attempts to roll back both and prints the recovery backup path. **Arch package upgrades, installed packages/Flatpaks and the Flathub remote are retained**; rollback does not downgrade or uninstall them. A working user D-Bus session is needed to restore appearance preferences. Log out and back in after restoring to restart the original session components.

The uploaded original configs remain in `originals/`. `tiledSessionRestore.json` contains no restored windows or tile groups and is not installed.

## Validation

```bash
python3 tests.py
python3 tests_apps.py
python3 tests_waybar.py
```

The tests exercise existing desktop actions, install/restore round trips, failure rollback, preservation of later edits, symlink rejection, dependency provisioning, native/user/system Flatpak selection, GTK/MIME merging, schema-default restoration, and the read-only check flow. Package managers and desktop preference commands in `tests_apps.py` are mocked; tests do not install software or modify the running desktop.

The Waybar tests cover reveal/hide timing and geometry. The optional standalone-updater test is skipped when that updater is not in the repository; the socket test is skipped in environments that prohibit Unix sockets. These are offline checks, not a claim of live rendering, GPU timing, authentication or hardware compatibility. `install.py --check` uses the installed compositor's verifier when supported, and a real login remains the final integration check.
