hl.config({ animations = { enabled = true } })

local curves = {
    settle = { { 0.16, 1 }, { 0.30, 1 } },
    glide = { { 0.22, 1 }, { 0.36, 1 } },
    leave = { { 0.40, 0 }, { 1, 1 } },
    linear = { { 0, 0 }, { 1, 1 } },
}
for name, points in pairs(curves) do
    hl.curve(name, { type = "bezier", points = points })
end

-- Speed remains measured in tenths of a second.
local animations = {
    { "windowsIn", 3.8, "settle", "popin 96%" },
    { "windowsOut", 2, "leave", "popin 97%" },
    { "windowsMove", 3.5, "glide" },
    { "border", 3, "linear" },
    { "fadeIn", 2.8, "settle" },
    { "fadeOut", 2, "leave" },
    { "layersIn", 3, "settle", "fade" },
    { "layersOut", 1.8, "leave", "fade" },
    { "workspaces", 4.2, "glide", "slidefade 12%" },
    { "specialWorkspace", 3.5, "settle", "slidefadevert 8%" },
}
for _, spec in ipairs(animations) do
    hl.animation({ leaf = spec[1], enabled = true, speed = spec[2], bezier = spec[3], style = spec[4] })
end
