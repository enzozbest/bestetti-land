hl.window_rule({
    name = "midnight-suppress-maximize",
    match = { class = ".*" },
    suppress_event = "maximize",
})

hl.window_rule({
    name = "midnight-xwayland-drag",
    match = { class = "^$", title = "^$", xwayland = true, float = true, fullscreen = false, pin = false },
    no_focus = true,
})

-- New Lua rules use vectors for sizes. Expressions preserve monitor-relative sizing.
hl.window_rule({
    name = "midnight-utilities",
    match = { class = "^(pavucontrol|org.pulseaudio.pavucontrol|pwvucontrol|com.saivert.pwvucontrol|blueman-manager|nm-connection-editor|midnight-tools)$" },
    float = true,
    center = true,
    size = { "monitor_w*0.48", "monitor_h*0.60" },
})

hl.window_rule({
    name = "midnight-file-dialogs",
    match = { title = "^(Open File|Open Files|Save File|Save As|Choose Files|File Upload)$" },
    float = true,
    center = true,
    size = { "monitor_w*0.54", "monitor_h*0.65" },
})

hl.window_rule({
    name = "midnight-jetbrains-dialogs",
    match = {
        class = "^(jetbrains-.*|idea|clion|pycharm|webstorm|goland|rustrover)$",
        title = "^(Settings|Preferences|Project Structure)$",
    },
    float = true,
    center = true,
    size = { "monitor_w*0.60", "monitor_h*0.72" },
})

hl.window_rule({
    name = "midnight-picture-in-picture",
    match = { title = "^(Picture-in-Picture|PiP)$" },
    float = true,
    pin = true,
    size = { 640, 360 },
    keep_aspect_ratio = true,
})

hl.window_rule({
    name = "midnight-drop-terminal",
    match = { class = "^midnight-terminal$" },
    workspace = "special:terminal silent",
    float = true,
    center = true,
    size = { "monitor_w*0.72", "monitor_h*0.65" },
})

local layers = {
    { name = "midnight-bar-glass", namespace = "^waybar$" },
    { name = "midnight-launcher-glass", namespace = "^wofi$" },
    { name = "midnight-control-center-glass", namespace = "^swaync-control-center$", xray = false },
    { name = "midnight-notification-glass", namespace = "^swaync-notification-window$", xray = false },
}
for _, layer in ipairs(layers) do
    hl.layer_rule({
        name = layer.name,
        match = { namespace = layer.namespace },
        blur = true,
        ignore_alpha = 0.05,
        xray = layer.xray,
    })
end
