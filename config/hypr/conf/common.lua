local M = {}
local config = os.getenv("XDG_CONFIG_HOME")
if not config or config == "" then
    config = assert(os.getenv("HOME"), "HOME is not set") .. "/.config"
end
M.root = config .. "/hypr"
M.terminal = "kitty"
M.files = "thunar"
M.mod = "SUPER"

function M.quote(value)
    return "'" .. value:gsub("'", "'\\''") .. "'"
end

function M.command(action)
    return M.quote(M.root .. "/scripts/midnight.py") .. " " .. action
end

return M
