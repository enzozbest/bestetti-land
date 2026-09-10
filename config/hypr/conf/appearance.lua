hl.config({
    general = {
        gaps_in = 5,
        gaps_out = 12,
        border_size = 2,
        col = {
            active_border = { colors = { "rgba(b4befee6)", "rgba(89b4fac0)" }, angle = 45 },
            inactive_border = "rgba(45475a70)",
        },
        resize_on_border = true,
        allow_tearing = false,
        layout = "dwindle",
    },
    decoration = {
        rounding = 16,
        rounding_power = 2,
        active_opacity = 1.0,
        inactive_opacity = 1.0,
        fullscreen_opacity = 1.0,
        dim_inactive = false,
        dim_strength = 0.12,
        shadow = {
            enabled = true,
            range = 22,
            render_power = 3,
            color = "rgba(00000050)",
        },
        blur = {
            enabled = true,
            size = 8,
            passes = 3,
            new_optimizations = true,
            ignore_opacity = true,
            noise = 0.015,
            contrast = 0.95,
            brightness = 1.0,
        },
    },
    dwindle = { preserve_split = true },
    misc = {
        force_default_wallpaper = 0,
        disable_hyprland_logo = true,
        focus_on_activate = true,
    },
})

hl.workspace_rule({ workspace = "w[tv1]", gaps_out = 6, gaps_in = 0 })
hl.workspace_rule({ workspace = "special:terminal", gaps_out = 48, gaps_in = 0 })
