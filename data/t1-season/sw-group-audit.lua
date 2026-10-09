-- sw-group-audit: one JSON line listing the tool's tracked groups against this season's cast (9 Oct 2026; run X2).
--
--   cx-lifecycle.sh lua "<this file>"   (scripts/season-run.py sends it as code; it takes no arguments)
--
-- {"ok":true,"tick":..,"season":..,"cast_on":..,"groups":[[layer, token, members on the map, in the cast]],
--  "offcast":N,"offcast_units":N}  -- an off-cast group is a tracked land/water/cavern group whose species is in
-- neither the members nor the vermin of its layer's cast for the current season. Every read is inside one pcall, so a
-- failure prints {"ok":false,"error":..} and is never read as "no groups" (readout traps 14 and 24).
local TPY = 403200

local function enc(v)
    local t = type(v)
    if t == 'boolean' then return v and 'true' or 'false' end
    if t == 'number' then return tostring(math.floor(v) == v and math.floor(v) or v) end
    if t == 'string' then return '"' .. v:gsub('[%c"\\]', function(c) return ('\\u%04x'):format(c:byte()) end) .. '"' end
    if t ~= 'table' then return 'null' end
    local out = {}
    if #v > 0 or next(v) == nil then
        for i = 1, #v do out[i] = enc(v[i]) end
        return '[' .. table.concat(out, ',') .. ']'
    end
    local keys = {}
    for k in pairs(v) do keys[#keys + 1] = k end
    table.sort(keys)
    for _, k in ipairs(keys) do out[#out + 1] = enc(tostring(k)) .. ':' .. enc(v[k]) end
    return '{' .. table.concat(out, ',') .. '}'
end

local function audit()
    if not dfhack.isMapLoaded() then error('no map loaded') end
    local sw = reqscript('seasonal-wildlife')
    local cfg = sw.loadConfig()
    local g = sw.loadGroups()
    local s = df.global.cur_season
    local castOn = type(cfg.cast) == 'table' and cfg.cast.enabled == true and type(cfg.casts) == 'table'
    local function tok(k) return (k:match(':(.+)$') or k) end
    local inCast = {}
    for _, layer in ipairs({ 'land', 'water', 'cavern' }) do
        inCast[layer] = {}
        local x = castOn and ((cfg.casts.layers or {})[layer] or {})[s + 1] or nil
        for _, k in ipairs(x and x.members or {}) do inCast[layer][tok(k)] = true end
        for _, k in ipairs(x and x.vermin or {}) do inCast[layer][tok(k)] = true end
    end
    local rows, off, offUnits = {}, 0, 0
    for _, grp in ipairs(g.groups or {}) do
        local layer = grp.layer or 'land'
        local n = 0
        for _, id in ipairs(grp.ids or {}) do
            local u = df.unit.find(id)
            if u and not dfhack.units.isDead(u) and dfhack.units.isActive(u) then n = n + 1 end
        end
        local managed = inCast[layer] ~= nil
        local ok = (not castOn) or (not managed) or inCast[layer][grp.token or ''] == true
        rows[#rows + 1] = { layer, grp.token or '?', n, ok }
        if managed and not ok and n > 0 then off = off + 1; offUnits = offUnits + n end
    end
    return { ok = true, tick = df.global.cur_year * TPY + df.global.cur_year_tick, season = s, cast_on = castOn,
             groups = rows, offcast = off, offcast_units = offUnits }
end

local ok, res = pcall(audit)
if ok then print(enc(res)) else print(enc({ ok = false, error = tostring(res) })) end
