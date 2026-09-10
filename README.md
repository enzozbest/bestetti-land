**MIDNIGHT GLASS — Enzo's Hyprland refresh**

A coordinated dark desktop built from your supplied configuration: floating Waybar sections, lavender focus accents, Inter typography, restrained glass, a matching Wofi launcher, a SwayNC control centre and a quieter lock screen. The wallpaper script reuses `~/Pictures/Wallpapers/backdrop.png`; the interactive concept uses an illustrative background because the actual image was not attached.

**Compatibility comes first**

This edition targets the **Hyprland 0.53 / 0.54 Hyprlang syntax** used by your uploaded configuration. Your installed version was not supplied. Hyprland 0.55 introduced Lua configuration, so the installer deliberately stops on newer or unrecognised versions and when `hyprland.lua` exists. Check your version after any Arch update; a Lua edition needs adapting before installation. [Hyprland configuration documentation](https://wiki.hypr.land/Configuring/Start/)

The installer uses the standard `~/.config` location and expects regular files. If you manage dotfiles through symlinks or use a custom `XDG_CONFIG_HOME`, merge the files through that workflow. The font names are `Inter` and `JetBrainsMono Nerd Font`.

**Get started**

Extract the archive, open a terminal in the `midnight-glass` directory, and run:

```bash
python3 install.py --check
```

This lists every destination, checks your installed compositor version and required commands, reports font matches, and detects the backlight device. If your Hyprland binary advertises `--verify-config`, it also asks that binary to validate a staged copy. It does not install files or packages.

The configured components use these Arch packages; `--check` identifies what is missing:

```text
python hyprland waybar wofi swaync hyprlock hypridle swaybg kitty
wl-clipboard cliphist grim slurp libnotify wireplumber playerctl
brightnessctl networkmanager thunar blueman procps-ng
inter-font ttf-jetbrains-mono-nerd
```

Also keep `firefox-developer-edition` or `firefox`, and `pavucontrol` or `pwvucontrol`. The installer does not alter your existing PipeWire, NVIDIA drivers, display manager or portal setup. Optional existing helpers are `easyeffects` and `polkit-gnome`; `btop`, `htop` and `nvtop` provide richer system monitors. A `top` fallback works without btop/htop. Arch provides [Inter](https://archlinux.org/packages/extra/any/inter-font/) and [JetBrains Mono Nerd Font](https://archlinux.org/packages/extra/any/ttf-jetbrains-mono-nerd/) under the package names above.

After the checks pass, install as your desktop user:

```bash
python3 install.py --apply
hyprctl configerrors
```

The installer makes a timestamped backup of affected live files and prints its path. It preserves an existing `hypr/local.conf`, detects the backlight device for SwayNC, and writes the main compositor config after its dependencies. Hyprland may automatically pick up the change. If `configerrors` reports an error, use the printed rollback command before logging out.

Once the config has no errors, **log out and back in** to start the new session helpers. Then test `Super + L` and successfully unlock before relying on idle locking. A config reload alone does not rerun `exec-once` or restart Hypridle. Helpers already running through your session manager are respected. If a pre-existing Waybar service explicitly loads another configuration path, point it at `~/.config/waybar/config.jsonc` and `~/.config/waybar/style.css`.

**What changed**

| Area | Result |
| --- | --- |
| Bar | App launcher, numbered workspaces and active app on the left; clock in the centre; compact controls on the right. Hover the chip icon for CPU, RAM and tray; click it for system tools. |
| Typography | Inter for interface text; Nerd Font for symbols and code. |
| Windows | 16px corners, lavender/blue active border, restrained shadows, 5px inner gaps and 12px outer gaps. A lone tiled window keeps a 6px frame. |
| Animation | Roughly 200–420ms timings with short exits and subtle entrance scaling. No constantly spinning border. |
| Transparency | Opaque normal apps for readable text; translucency concentrated in shell surfaces and the drop-down terminal. Blur reduced from size 18 / 4 passes to size 8 / 3 passes. This is a tuning choice, not a measured performance claim. |
| Launcher | A matching Wofi theme, application search and a searchable open-window list. |
| Control centre | Notifications, DND, four quick actions, media, volume and detected backlight controls. |
| Terminal | A dedicated terminal on `special:terminal`; toggling it preserves the terminal process. The old `special:magic` workspace still works. |
| Focus mode | Dims inactive windows and enables DND; the next toggle restores the previous states. |
| Screenshots | Region or focused-monitor capture, a unique file in Pictures/Screenshots, and clipboard copy. Esc during region selection cancels cleanly. |
| Session actions | A themed menu. Shutdown, restart and logout have a second confirmation. |
| Idle | Lock after 5 minutes, display off after 6, display on at activity. No automatic suspend timer. Waybar's keep-awake button inhibits idle. |

Your two supplied monitor modes, scale 1, GB keyboard layout, NVIDIA environment variables, three-finger workspace gesture and most familiar shortcuts are carried over. NVIDIA variables were preserved rather than inferred from an unseen driver setup. Your Firefox shortcut remains; the menu falls back to regular Firefox if the developer edition is unavailable.

**Shortcut reference**

`Super` means the Windows key.

| Keys | Action |
| --- | --- |
| Super + Space / D / R | Applications |
| Super + Shift + Space | Search open windows |
| Super + grave/backtick | Show or hide the dedicated terminal |
| Super + Return / Q | Kitty |
| Super + Shift + Return | Kitty at the active application's reported working directory, falling back to home |
| Super + E / W | Files / Firefox |
| Super + N | Control centre |
| Super + Shift + N | Toggle Do Not Disturb |
| Super + Shift + V | Clipboard history |
| Super + G | Toggle focus mode |
| Super + Shift + G | Restore pre-focus settings |
| Super + L | Lock |
| Super + M / Shift + P | Session menu |
| Print / Super + Print / Super + Shift + Print | Region screenshot, saved and copied |
| Super + Ctrl + Print | Focused-monitor screenshot, saved and copied |
| Super + arrows | Focus neighbour |
| Super + Shift + arrows | Move window |
| Super + Ctrl + arrows | Resize window |
| Super + F / Shift + F | Fullscreen / maximise within the work area |
| Super + V | Float/unfloat |
| Super + T | Group/ungroup |
| Super + Tab / Shift + Tab | Next/previous window in group |
| Super + 1…0 | Workspaces 1…10 |
| Super + Shift + 1…0 | Move window to workspace |
| Super + S / Shift + S | Toggle magic workspace / move window into it |
| Super + Z / Shift + Z | Disable/enable focus following the pointer |
| Super + Ctrl + R | Restore focus-mode state and reload compositor, SwayNC and Waybar |
| Super + slash | Shortcut list |

Deliberate remaps: Super + grave now summons a terminal instead of opening Wofi's run mode; Super + G is a real focus-mode toggle instead of setting gaps to zero. All screenshot shortcuts save and copy, instead of some silently overwriting a fixed filename. Super + M opens the session menu before logout.

**Tuning**

Edit `~/.config/hypr/local.conf` for compositor overrides. Examples are already commented in that file. Hardware lives in `conf/hardware.conf`, styling in `conf/appearance.conf`, motion in `conf/animations.conf`, and shortcuts and matching rules have their own files.

For a denser display or different laptop, check `hyprctl monitors` and adapt `hardware.conf` before applying. The fallback monitor rule handles additional outputs at their preferred mode. The supplied explicit modes assume the monitors in your original file.

To use another wallpaper, set this in `local.conf` and log in again:

```ini
env = MIDNIGHT_WALLPAPER,/absolute/path/to/wallpaper.png
```

If no wallpaper file exists, the background falls back to solid midnight. Your wallpaper itself was not included in the uploads. Normal Kitty and IDE themes remain yours; only the dedicated drop-down terminal gets colour and opacity overrides. The example editor and browser content in the concept preview is illustrative.

Text and image clipboard history are now captured at login to make your existing history shortcut useful. To disable capture, put `env = MIDNIGHT_CLIPBOARD_HISTORY,0` in `local.conf` and log in again. Existing stored history remains until you clear it with `cliphist wipe`.

**Rollback**

Use the exact backup directory printed by the installer:

```bash
python3 install.py --restore /path/printed/by/the/installer
```

This restores the original files and removes files newly introduced by that installation. It first saves any edits made since installation into an `after-*` directory inside the backup. Unrelated files are left alone. Log out and back in to restore the original session processes. Your uploaded originals are also included in `originals/`; `tiledSessionRestore.json` contained no windows or tile groups and is not installed or changed.

**What was verified**

Eight offline regression tests passed: cancellation of screenshots and shutdown, duplicate terminal launch suppression, focus-mode restoration with both previous DND states, handling untrusted window titles as data, install/restore round trips, rollback after a simulated installation failure, and rejecting symlink-managed destinations before writing. Run them with `python3 tests.py`.

Python syntax, Bash syntax, JSON parsing, source-file references, rule-name and keybinding uniqueness, and named-colour references were checked. All three stylesheets also loaded successfully through the real GTK 3 CSS parser. This is not a substitute for rendering with the installed applications; GTK 4 was not available. Hyprland, Waybar, SwayNC and Hyprlock are not available in the build environment, so no live session, GPU timing, lock authentication, GTK rendering or hotplug test is claimed. The final spacing and hardware behaviour need checking on your monitors.

**Why these fixes matter**

The original notification backgrounds used roughly 0.3 alpha while `ignore_alpha` was 0.5; the latter excludes those pixels from blur. The new threshold is 0.05. Duplicate rule names were consolidated, broad dialog matches narrowed, and the old sample mouse device removed. [Hyprland window and layer rules](https://wiki.hypr.land/0.54.0/Configuring/Window-Rules/)

The old SwayNC CSS included `color: @define-color (text)` and broad descendant resets that could override card styling. The replacement uses named colours correctly and targeted selectors. Its widget ID is `notifications`; `widget-notifications` is the CSS class, not the widget ID. [SwayNC configuration manual](https://github.com/ErikReider/SwayNotificationCenter/blob/main/man/swaync.5.scd)

Hypridle now connects loginctl lock requests and suspend preparation to Hyprlock. The old Hyprlock grace/fade settings were removed, and the Esc hint correctly says it clears the password input. [Hypridle](https://wiki.hypr.land/Hypr-Ecosystem/hypridle/), [Hyprlock](https://wiki.hypr.land/Hypr-Ecosystem/hyprlock/)

The stats drawer uses Waybar's built-in grouping. NVIDIA monitoring is available on demand through nvtop rather than a five-second `nvidia-smi` loop. [Waybar groups](https://github.com/Alexays/Waybar/wiki/Module:-Group)
