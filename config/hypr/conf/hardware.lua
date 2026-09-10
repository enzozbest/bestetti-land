-- Your existing monitor modes, keyboard, pointer and driver settings.
hl.monitor({ output = "eDP-1", mode = "2560x1600@240", position = "0x0", scale = 1 })
hl.monitor({ output = "HDMI-A-1", mode = "2560x1440@144", position = "auto", scale = 1 })
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

local environment = {
    XCURSOR_SIZE = "24",
    HYPRCURSOR_SIZE = "24",
    LIBVA_DRIVER_NAME = "nvidia",
    XDG_SESSION_TYPE = "wayland",
    GBM_BACKEND = "nvidia-drm",
    __GLX_VENDOR_LIBRARY_NAME = "nvidia",
    NVD_BACKEND = "direct",
}
for name, value in pairs(environment) do
    hl.env(name, value)
end

hl.config({
    input = {
        kb_layout = "gb",
        follow_mouse = 1,
        sensitivity = 0,
        touchpad = {
            natural_scroll = true,
            tap_to_click = true,
            disable_while_typing = true,
        },
    },
})

hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })
