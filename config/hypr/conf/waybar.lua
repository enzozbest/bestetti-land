-- Larger Waybar with top-edge reveal; pin it while using tray menus.
local common = require("conf.common")
local command = "python3 " .. common.quote(common.root .. "/scripts/waybar-control.py")
hl.bind(common.mod .. " + B", hl.dsp.exec_cmd(command .. " toggle-pin"))
hl.bind(common.mod .. " + SHIFT + B", hl.dsp.exec_cmd(command .. " peek"))
hl.on("hyprland.start", function()
    hl.exec_cmd(command .. " ensure")
end)
