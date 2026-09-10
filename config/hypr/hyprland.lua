-- MIDNIGHT GLASS · Enzo · native Hyprland 0.56 Lua configuration
-- The shell components retain their own JSON, CSS and Hyprlang formats.

require("conf.hardware")
require("conf.appearance")
require("conf.animations")
require("conf.rules")
require("conf.bindings")
require("conf.waybar")

-- Registered again on config reload; executed only when the session starts.
local common = require("conf.common")
hl.on("hyprland.start", function()
    hl.exec_cmd(common.quote(common.root .. "/scripts/session.sh"))
end)

-- Personal overrides are loaded last and preserved by the installer.
require("local")
