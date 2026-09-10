**MIDNIGHT GLASS — Enzo's Hyprland refresh · Lua edition**

A coordinated dark desktop built from your supplied configuration: floating Waybar sections, lavender focus accents, Inter typography, restrained glass, a matching Wofi launcher, a SwayNC control centre and a quieter lock screen. The wallpaper script reuses `~/Pictures/Wallpapers/backdrop.png`; the interactive concept uses an illustrative background because the actual image was not attached.

**Compatibility comes first**

This edition targets **Hyprland 0.56 or newer**, using native Lua and the documented 0.56 API. Arch's package was 0.56.2-2 when checked on 10 September 2026. The installer checks your installed version and stops below 0.56 or if it cannot recognise the version. Future API changes may still require adjustments. [Arch package](https://archlinux.org/packages/extra/x86_64/hyprland/), [Hyprland 0.56 configuration](https://wiki.hypr.land/0.56.0/Configuring/Start/)

The compositor entry point is now `hypr/hyprland.lua`, with separate Lua modules for hardware, appearance, motion, rules and bindings. **Hyprlock and Hypridle keep their own `.conf` format**; Waybar, Wofi and SwayNC keep their existing formats.

The installer uses the standard `~/.config` location and expects regular files. If you manage dotfiles through symlinks or use a custom `XDG_CONFIG_HOME`, merge the files through that workflow. The font names are `Inter` and `JetBrainsMono Nerd Font`.

**Get started**

Upgrade Arch and Hyprland together:

```bash
sudo pacman -Syu hyprland
```

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
```

The installer makes a timestamped backup of affected live files and prints its path. It preserves an existing `hypr/local.lua`, detects the backlight device for SwayNC, and writes the main compositor config after its dependencies. Old compositor `.conf` files are retained, but the default config lookup in modern Hyprland prefers `hyprland.lua`. If `local.conf` contains active personal overrides and no `local.lua` exists, the check asks you to translate those overrides into `local.lua` first.

**Log out and back in after installation** to start the upgraded compositor, load the Lua entry point and start the new session helpers. If your session command explicitly selects `hyprland.conf` with `--config`, change that path to `hyprland.lua` or remove the custom flag. Then run:

```bash
hyprctl configerrors
```

Once the config has no errors, test `Super + L` and successfully unlock before relying on idle locking. A config reload alone does not replace a running compositor with the upgraded binary, rerun the session-start callback or restart Hypridle. Helpers already running through your session manager are respected. If a pre-existing Waybar service explicitly loads another configuration path, point it at `~/.config/waybar/config.jsonc` and `~/.config/waybar/style.css`. The printed rollback command is also usable from a text console if the graphical session cannot start.

**What the Lua migration changes**

Most settings translate directly. Actions and lifecycle handling need explicit API changes:

| Before | Lua edition |
| --- | --- |
| Category blocks such as `general { ... }` | Nested tables passed to `hl.config({ ... })` |
| `source = ...` | `require("conf.appearance")` and other modules |
| Repeated workspace bindings | A loop generates the same keys for workspaces 1–10 |
| Dispatcher strings in bindings | `hl.bind(...)` with structured `hl.dsp` actions |
| `exec-once` | `hl.on("hyprland.start", function() ... end)` |
| Window and layer rules | `hl.window_rule(...)` and `hl.layer_rule(...)`, including vector sizes |
| Runtime `hyprctl keyword` updates | `hyprctl eval 'hl.config(...)'` |
| Legacy CLI dispatcher arguments | Native `hyprctl dispatch 'hl.dsp.…(...)'` expressions |

Window selection, the special terminal, logout, focus mode and idle display power commands have been converted together with the main config. External programs still run asynchronously through exec actions. Mute keys now toggle once per press; holding them no longer repeatedly flips mute. The desktop's visual design and remaining shortcuts are carried over. [Lua dispatchers](https://wiki.hypr.land/0.56.0/Configuring/Basics/Dispatchers/), [hyprctl](https://wiki.hypr.land/Configuring/Advanced-and-Cool/Using-hyprctl/)

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

Edit `~/.config/hypr/local.lua` for compositor overrides. Examples are already commented in that file. Hardware lives in `conf/hardware.lua`, styling in `conf/appearance.lua`, motion in `conf/animations.lua`, and shortcuts and matching rules have their own files. `conf/common.lua` contains the modifier, default applications and shared command helpers. The included Lua language-server settings point to Hyprland's installed stubs under `/usr/share/hypr/stubs` for editor completion.

For a denser display or different laptop, check `hyprctl monitors` and adapt `hardware.lua` before applying. The fallback monitor rule handles additional outputs at their preferred mode. The supplied explicit modes assume the monitors in your original file.

To use another wallpaper, set this in `local.lua` and log in again:

```lua
hl.env("MIDNIGHT_WALLPAPER", "/absolute/path/to/wallpaper.png")
```

If no wallpaper file exists, the background falls back to solid midnight. Your wallpaper itself was not included in the uploads. Normal Kitty and IDE themes remain yours; only the dedicated drop-down terminal gets colour and opacity overrides. The example editor and browser content in the concept preview is illustrative.

Text and image clipboard history are now captured at login to make your existing history shortcut useful. To disable capture, put `hl.env("MIDNIGHT_CLIPBOARD_HISTORY", "0")` in `local.lua` and log in again. Existing stored history remains until you clear it with `cliphist wipe`.

**Rollback**

Use the exact backup directory printed by the installer:

```bash
python3 install.py --restore /path/printed/by/the/installer
```

This restores the original files and removes files newly introduced by that installation. It first saves any edits made since installation into an `after-*` directory inside the backup. Unrelated files are left alone. If this installation introduced `hyprland.lua`, rollback removes it and leaves the previous `.conf` entry point available. Restore an explicit session `--config` path yourself if you changed it. Log out and back in to restore the original session processes. Rollback restores configuration files; it does not downgrade Arch packages. Your uploaded originals are also included in `originals/`; `tiledSessionRestore.json` contained no windows or tile groups and is not installed or changed.

**What was verified**

Ten offline regression tests passed: cancellation of screenshots and shutdown, duplicate terminal launch suppression, focus-mode restoration with both previous DND states, handling untrusted window titles as data, install/restore round trips, rollback after a simulated installation failure, rejecting symlink-managed destinations before writing, migration that retains the old entry point and installs Lua last, and native Lua dimming commands. Run them with `python3 tests.py`.

All eight Lua files passed the Lua 5.4 parser. An offline stub of the documented `hl` API loaded the modules and checked 86 unique bindings, 11 unique window/layer rules, three monitor rules, ten animation entries, workspace mappings, callback behaviour and shell quoting. It also checked that loading the config does not start applications before the session-start event. This exercises Lua evaluation; it is not validation by the actual compositor.

Python syntax, Bash syntax, JSON parsing, source-file references and named-colour references were checked. The unchanged stylesheets previously loaded successfully through the real GTK 3 CSS parser. Hyprland, Waybar, SwayNC and Hyprlock are not available in the build environment, so no live session, GPU timing, lock authentication, GTK rendering or hotplug test is claimed. The final spacing and hardware behaviour need checking on your monitors; the installer invokes your binary's config verifier when it is available.

**Why these fixes matter**

The original notification backgrounds used roughly 0.3 alpha while `ignore_alpha` was 0.5; the latter excludes those pixels from blur. The new threshold is 0.05. Duplicate rule names were consolidated, broad dialog matches narrowed, and the old sample mouse device removed. [Hyprland window and layer rules](https://wiki.hypr.land/0.56.0/Configuring/Basics/Window-Rules/)

The old SwayNC CSS included `color: @define-color (text)` and broad descendant resets that could override card styling. The replacement uses named colours correctly and targeted selectors. Its widget ID is `notifications`; `widget-notifications` is the CSS class, not the widget ID. [SwayNC configuration manual](https://github.com/ErikReider/SwayNotificationCenter/blob/main/man/swaync.5.scd)

Hypridle now connects loginctl lock requests and suspend preparation to Hyprlock. The old Hyprlock grace/fade settings were removed, and the Esc hint correctly says it clears the password input. [Hypridle](https://wiki.hypr.land/Hypr-Ecosystem/hypridle/), [Hyprlock](https://wiki.hypr.land/Hypr-Ecosystem/hyprlock/)

The stats drawer uses Waybar's built-in grouping. NVIDIA monitoring is available on demand through nvtop rather than a five-second `nvidia-smi` loop. [Waybar groups](https://github.com/Alexays/Waybar/wiki/Module:-Group)
