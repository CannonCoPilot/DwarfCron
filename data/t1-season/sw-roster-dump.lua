-- sw-roster-dump: print the loaded fort's Seasonal Wildlife roster as TSV (layer token seasons weight allow), one row per assigned species.
-- Usage (rig): cx-lifecycle.sh lua-file sw-roster-dump.lua  (or `sw-roster-dump` once deployed to dfhack-config/scripts)
local sw = reqscript('seasonal-wildlife')
local c = sw.loadConfig()
local names = { [0] = 'Sp', 'Su', 'Au', 'Wi' }
local rows = {}
for key, arr in pairs(c.assign or {}) do
    local layer, token = key:match('^(%w+):(.+)$')
    if not layer then layer, token = 'land', key end
    local s = {}
    for _, v in ipairs(arr) do s[#s + 1] = names[v] or tostring(v) end
    local seasons = table.concat(s)
    if seasons == '' then seasons = '-' end
    local allow = c.allow[key]
    rows[#rows + 1] = { layer, token, seasons, c.weight[key] and tostring(c.weight[key]) or '', allow == nil and 'true' or tostring(allow) }
end
table.sort(rows, function(a, b) if a[1] ~= b[1] then return a[1] < b[1] end return a[2] < b[2] end)
print('layer\ttoken\tseasons\tweight\tallow')
for _, r in ipairs(rows) do print(table.concat(r, '\t')) end
