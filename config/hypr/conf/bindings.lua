local common = require("conf.common")
local mod, dsp = common.mod, hl.dsp

local function bind(key, action, options)
    return hl.bind(mod .. " + " .. key, action, options)
end
local function action(key, command)
    bind(key, dsp.exec_cmd(common.command(command)))
end

bind("Q", dsp.exec_cmd(common.terminal))
bind("Return", dsp.exec_cmd(common.terminal))
action("SHIFT + Return", "terminal-here")
bind("C", dsp.window.close())
bind("E", dsp.exec_cmd(common.files))
action("W", "browser")
hl.bind("CTRL + ALT + W", dsp.exec_cmd(common.command("browser")))

for _, key in ipairs({ "R", "D", "SPACE" }) do action(key, "launcher") end
action("grave", "terminal")
action("SHIFT + SPACE", "windows")
action("SHIFT + V", "clipboard")
bind("N", dsp.exec_cmd("swaync-client -t"))
bind("SHIFT + N", dsp.exec_cmd("swaync-client -d"))
action("slash", "help")
action("L", "lock")
action("ALT + L", "lock")
action("M", "power")
action("SHIFT + P", "power")
action("CTRL + R", "reload")

bind("V", dsp.window.float({ action = "toggle" }))
bind("F", dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }))
bind("SHIFT + F", dsp.window.fullscreen({ mode = "maximized", action = "toggle" }))
bind("P", dsp.window.pseudo({ action = "toggle" }))
bind("J", dsp.layout("togglesplit"))
bind("T", dsp.group.toggle())
bind("SHIFT + T", dsp.group.lock_active({ action = "toggle" }))
bind("Tab", dsp.group.next())
bind("SHIFT + Tab", dsp.group.prev())

-- These callbacks only update compositor state and never block on subprocesses.
bind("Z", function() hl.config({ input = { follow_mouse = 0 } }) end)
bind("SHIFT + Z", function() hl.config({ input = { follow_mouse = 1 } }) end)
action("G", "focus")
action("SHIFT + G", "focus-off")

for _, spec in ipairs({
    { "left", -30, 0 }, { "right", 30, 0 }, { "up", 0, -30 }, { "down", 0, 30 },
}) do
    local direction = spec[1]
    bind(direction, dsp.focus({ direction = direction }))
    bind("SHIFT + " .. direction, dsp.window.move({ direction = direction }))
    bind("CTRL + " .. direction, dsp.window.resize({ x = spec[2], y = spec[3], relative = true }), { repeating = true })
end

for workspace = 1, 10 do
    local key = tostring(workspace % 10)
    bind(key, dsp.focus({ workspace = workspace }))
    bind("SHIFT + " .. key, dsp.window.move({ workspace = workspace, follow = true }))
end
bind("S", dsp.workspace.toggle_special("magic"))
bind("SHIFT + S", dsp.window.move({ workspace = "special:magic", follow = true }))
bind("mouse_down", dsp.focus({ workspace = "e+1" }))
bind("mouse_up", dsp.focus({ workspace = "e-1" }))
bind("mouse:272", dsp.window.drag(), { mouse = true })
bind("mouse:273", dsp.window.resize(), { mouse = true })

hl.bind("Print", dsp.exec_cmd(common.command("screenshot region")))
action("Print", "screenshot region")
action("SHIFT + Print", "screenshot region")
action("CTRL + Print", "screenshot screen")

local media_keys = {
    XF86AudioRaiseVolume = common.command("volume up"),
    XF86AudioLowerVolume = common.command("volume down"),
    XF86MonBrightnessUp = common.command("brightness up"),
    XF86MonBrightnessDown = common.command("brightness down"),
}
for key, command in pairs(media_keys) do
    hl.bind(key, dsp.exec_cmd(command), { locked = true, repeating = true })
end
-- Toggle actions fire once per press; holding mute no longer toggles repeatedly.
hl.bind("XF86AudioMute", dsp.exec_cmd(common.command("volume mute")), { locked = true })
hl.bind("XF86AudioMicMute", dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle"), { locked = true })
for key, command in pairs({
    XF86AudioNext = "next", XF86AudioPause = "play-pause", XF86AudioPlay = "play-pause", XF86AudioPrev = "previous",
}) do
    hl.bind(key, dsp.exec_cmd("playerctl " .. command), { locked = true })
end
