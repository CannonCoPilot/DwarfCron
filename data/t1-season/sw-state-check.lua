-- sw-state-check: one JSON line describing the world state the switch round trip (run X1) must put back (9 Oct 2026).
--
--   sw-state-check [all]     (deployed)  or, from the run kit:  cx-lifecycle.sh lua "<this file>"  with
--                            `local SWSC_ARGS = {'all'}` prepended (scripts/season-run.py does this)
--
-- Prints exactly one line, {"ok":true, ...} or {"ok":false,"error":"..."}; everything is read inside one pcall so an
-- error is never read as an empty world (readout traps 14 and 24). It reads only: it loads no seasonal-wildlife code
-- (its site data is read directly), so it is safe on a fort where the tool is off or absent.
--
--   tick, season, site     the absolute tick, the season index, the save folder DF has loaded
--   tool                   from the tool's own site data: config present, enabled, casts on, initialized
--   pops                   [index, race token, layer key, quantity, extinct, type] per world.populations.all entry whose
--                          world tile is within one tile of the embark (DF draws from all nine neighbours; `all`: every
--                          creature entry in the world); the layer key is the tool's config key (TOKEN, water:TOKEN,
--                          cave:TOKEN -- a cave entry's cavern/deep split needs the tool's depth table, so it is left as cave)
--   snapshot               the tool's worldgen snapshot, {config key: quantity}
--   reserve                the tool's held reserve, {population index: quantity}
--   raws                   per race in pops: FREQUENCY, CLUSTER_NUMBER max/min, POPULATION_NUMBER max/min, and the
--                          NO_SPRING/NO_SUMMER/NO_AUTUMN/NO_WINTER flags held by every caste (a 4-letter mask, '-' = clear)
--   rel                    PREDATOR_OR_PREY cells in DF's relation table among active units with a slot: cells with a
--                          wild unit on either side, wild x wild, wild x other, and the units read
-- luacheck: globals SWSC_ARGS
local args = (SWSC_ARGS ~= nil) and SWSC_ARGS or { ... }
local TPY = 403200

local function enc(v)
    local t = type(v)
    if t == 'nil' then return 'null' end
    if t == 'boolean' then return v and 'true' or 'false' end
    if t == 'number' then
        if v ~= v or v == math.huge or v == -math.huge then return 'null' end
        return (math.type and math.type(v) == 'integer') and tostring(v) or (v == math.floor(v) and ('%d'):format(v) or tostring(v))
    end
    if t == 'string' then
        return '"' .. v:gsub('[%c"\\]', function(c)
            local m = { ['"'] = '\\"', ['\\'] = '\\\\', ['\n'] = '\\n', ['\t'] = '\\t', ['\r'] = '\\r' }
            return m[c] or ('\\u%04x'):format(c:byte())
        end) .. '"'
    end
    -- a table: an array when its keys are 1..n, else an object (keys as strings, sorted so two dumps diff line by line)
    local n = #v
    local isArr = n > 0 or next(v) == nil
    if isArr then for k in pairs(v) do if type(k) ~= 'number' or k > n then isArr = false break end end end
    local out = {}
    if isArr then
        for i = 1, n do out[i] = enc(v[i]) end
        return '[' .. table.concat(out, ',') .. ']'
    end
    local keys = {}
    for k in pairs(v) do keys[#keys + 1] = tostring(k) end
    table.sort(keys)
    for _, k in ipairs(keys) do
        local x = v[k]; if x == nil then x = v[tonumber(k)] end
        out[#out + 1] = enc(k) .. ':' .. enc(x)
    end
    return '{' .. table.concat(out, ',') .. '}'
end

local function isWild(u)
    local U = dfhack.units
    if U.isCitizen(u) or U.isResident(u) or U.isMerchant(u) or U.isInvader(u) or U.isVisitor(u) then return false end
    if U.isAnimal(u) and (U.isTame(u) or U.isDomesticated(u) or U.isFortControlled(u)) then return false end
    return U.isWildlife(u) or U.isAnimal(u)
end

local function allCastes(craw, flag)
    if #craw.caste == 0 then return false end
    for _, c in ipairs(craw.caste) do
        local ok, v = pcall(function() return c.flags[flag] end)
        if not ok or not v then return false end
    end
    return true
end

local function check()
    if not dfhack.isMapLoaded() then error('no map loaded') end
    local all = args[1] == 'all'
    local out = { ok = true, tick = df.global.cur_year * TPY + df.global.cur_year_tick, season = df.global.cur_season,
                  site = df.global.world.cur_savegame.save_dir, scope = all and 'all' or 'embark+1' }

    -- the tool's own records, read from site data (no tool code runs)
    local cfg = dfhack.persistent.getSiteData('seasonal-wildlife/config', nil)
    out.tool = { config = cfg ~= nil }
    if type(cfg) == 'table' then
        out.tool.enabled = cfg.enabled == true
        out.tool.initialized = cfg.initialized == true
        out.tool.cast_enabled = type(cfg.cast) == 'table' and cfg.cast.enabled == true
        out.tool.casts_year = type(cfg.casts) == 'table' and cfg.casts.year or nil
    end
    out.snapshot = (type(cfg) == 'table' and type(cfg.default_snapshot) == 'table') and cfg.default_snapshot or {}
    local res = dfhack.persistent.getSiteData('seasonal-wildlife/reserve', nil)
    out.reserve = type(res) == 'table' and res or {}

    -- the embark's world tiles: map.region_x/y count mid-level tiles (16 per world tile), 48 map tiles each
    local m = df.global.world.map
    local x0, y0 = m.region_x // 16, m.region_y // 16
    local x1, y1 = (m.region_x + m.x_count // 48 - 1) // 16, (m.region_y + m.y_count // 48 - 1) // 16
    local SKIP = { Tree = true, Grass = true, Bush = true }
    local pops, races = {}, {}
    for i, p in ipairs(df.global.world.populations.all) do
        local tname = df.world_population_type[p.type] or tostring(p.type)
        local r = p.population
        local near = all or (r.region_x >= x0 - 1 and r.region_x <= x1 + 1 and r.region_y >= y0 - 1 and r.region_y <= y1 + 1)
        local craw = (not SKIP[tname]) and near and df.creature_raw.find(p.race) or nil
        if craw then
            local tok = craw.creature_id
            local key = r.cave_id ~= -1 and ('cave:' .. tok) or (r.feature_idx ~= -1 and ('water:' .. tok) or tok)
            pops[#pops + 1] = { i, tok, key, p.quantity, p.flags.extinct == true, tname }
            races[p.race] = craw
        end
    end
    out.pops = pops

    local raws = {}
    for _, craw in pairs(races) do
        local mask = ''
        for j, f in ipairs({ 'NO_SPRING', 'NO_SUMMER', 'NO_AUTUMN', 'NO_WINTER' }) do
            mask = mask .. (allCastes(craw, f) and ('SpSuAuWi'):sub(2 * j - 1, 2 * j - 1) or '-')
        end
        raws[craw.creature_id] = { craw.frequency, craw.cluster_number[0], craw.cluster_number[1],
                                   craw.population_number[0], craw.population_number[1], mask }
    end
    out.raws = raws

    -- relation cells (the tool's ecology writes PREDATOR_OR_PREY into enemy_status_cache.rel_map)
    local cache = df.global.world.enemy_status_cache
    local n = #cache.rel_map
    local PP = df.unit_reaction_type.PREDATOR_OR_PREY
    local us = {}
    for _, u in ipairs(df.global.world.units.active) do
        local sl = u.enemy.enemy_status_slot
        if sl >= 0 and sl < n and not dfhack.units.isDead(u) then us[#us + 1] = { sl = sl, wild = isWild(u) } end
    end
    local rel = { units = #us, slots = n, wild_any = 0, wild_wild = 0, wild_other = 0, other_other = 0 }
    if #us <= 3000 then
        for a = 1, #us do
            local A = us[a]
            local row = cache.rel_map[A.sl]
            for b = 1, #us do
                if a ~= b and row[us[b].sl].ur == PP then
                    local B = us[b]
                    if A.wild and B.wild then rel.wild_wild = rel.wild_wild + 1
                    elseif A.wild or B.wild then rel.wild_other = rel.wild_other + 1
                    else rel.other_other = rel.other_other + 1 end
                end
            end
        end
        rel.wild_any = rel.wild_wild + rel.wild_other
    else
        rel.skipped = 'over 3000 units with a slot'
    end
    out.rel = rel
    return out
end

local ok, res = pcall(check)
if ok then print(enc(res)) else print(enc({ ok = false, error = tostring(res) })) end
