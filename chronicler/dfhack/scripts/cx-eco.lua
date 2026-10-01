-- cx-eco.lua — the in-game half of the ecology behaviour suite (ECO, 30 Sep 2026).
--
-- Every command is ONE atomic step over RPC (the core is suspended while it runs); eco-run.py sequences
-- them into cells: place groups at a chosen spot, watch, step, read, clear. State lives in _G.CX_ECO so it
-- survives between calls (each RPC call runs a fresh copy of this file).
--
--   cx-eco spot land|shore|water [minfree]   a surface spot: open ground / land beside deep water / deep water
--   cx-eco spawn TOKEN N X Y Z [radius=3] [land|water] [male|female|any] [countdown=200000]
--                                            N wild units of TOKEN clustered around X,Y,Z (headless placement,
--                                            the six writes + an enemy slot; see memory headless-unit-placement)
--   cx-eco rel A B                           write PREDATOR_OR_PREY between every spawned A and B (both ways)
--   cx-eco watch                             start logging attacks (eventful UNIT_ATTACK) and deaths (incidents)
--   cx-eco read [tag]                        one TSV block: groups, attacks by pair, deaths by pair, alerts
--   cx-eco clear                             vanish every spawned unit (no corpse) and forget them
--   cx-eco flag TOKEN FLAG on|off            set a caste flag (all castes) or creature flag in memory; snapshots
--   cx-eco restore                           put every flag this file changed back
--   cx-eco lead TOKEN lowest|largest-male|none   make one member lead the rest (following / PACK_LEADER)
--   cx-eco alerts drop-wild on|off           drop COMBAT alerts whose units are all non-fort (prototype filter)
--
-- v7.1 harness (1 Oct 2026; Part 1 plan H2-H6, review R15). Classes: an ANIMAL is a live on-map unit that is not
-- fort-side (citizen/resident, livestock/pet/fort-controlled), not a guest (merchant, diplomat, visitor, invader, any
-- other civ's member), not non-natural (megabeast, FB, titan, demon, night creature, undead, GENERATED: fb_safe) and
-- not on the deep layers (magma sea, underworld: R60). Its ORIGIN is placed (spawned by this file), drawn (carries
-- DF's roaming flag: DF brought it) or released (no flag and not ours: released by the tool or cx-probe, or placed
-- by the tool).
--   cx-eco wipe [livestock] [close]          vanish every animal on the map (no corpse, gone next tick) BEFORE a cell
--                                            places its groups (R15); livestock only when asked; close = also close
--                                            the site's Animal pool entries (no new natives). Receipt by origin.
--   cx-eco wipecheck [livestock]             animals still on the map (remaining) and still vanishing (pending)
--   cx-eco spawn ... [countdown] [roam]      11th arg 'roam' KEEPS DF's roaming flag, so DF treats the unit as wild
--                                            (isolates DF's own aiming of non-wild units, H4); default clears it
--   cx-eco watch [bout_gap=100] [wildpred]   as before, plus a timestamped attack log (attacker/defender origin) and
--                                            hidden_in_ambush/hidden_ambusher sampled every 10 t on placed units and
--                                            recent attackers (wildpred: every wild carnivore too) (H6)
--   cx-eco read [tag]                        as before, plus attacks_o (pair by origin), atk (each attack), bout /
--                                            bouts (attacks with gaps < bout_gap; per hunter-day) and hidden rows
--   cx-eco groups3 base|reset|[tag]          ONE group definition, three sources (H5): live animals sharing species +
--                                            population entry (ref6) + arrival sample, against the tool's group record
--                                            and the entries' debits since `base`
--   cx-eco adopt TOKEN...                    seasonal-wildlife `groups adopt <ids>` on every spawned TOKEN (one group
--                                            per token, H3); the receipt reads the tool's own record
--   cx-eco cfg PATH...                       the tool's persisted config value at each dotted path (H2 receipts)
--   cx-eco skill TOKEN SKILL                 on-map TOKEN units, how many hold SKILL, the highest rating (H2)
--   cx-eco relcount A B                      PREDATOR_OR_PREY cells now standing between live spawned A and B (H2)
--   cx-eco ecostate                          the tool's group and ecology counters (groups by layer, pairs, nudges)
--
-- Output lines are "eco <kind> key=value ..." so the driver can parse them without guessing.

local eventful = require('plugins.eventful')

_G.CX_ECO = _G.CX_ECO or { spawned = {}, flags = {}, attacks = {}, inc0 = nil, watch = false, dropped = 0 }
local S = _G.CX_ECO
local args = { ... }
local cmd = args[1]

-- ⚠️ qerror() from a script run over `cx-rpc --cmd` never replies: the client waits out its whole deadline
-- (30 Sep 2026, 180 s per failed spawn). Errors are printed as 'eco error ...' and the verb returns.
local function fail(msg) print('eco error ' .. msg) end

local function out(kind, t)
    local parts = { 'eco', kind }
    for _, kv in ipairs(t) do parts[#parts + 1] = kv[1] .. '=' .. tostring(kv[2]) end
    print(table.concat(parts, ' '))
end

local function race_of(u) local c = df.creature_raw.find(u.race); return c and c.creature_id or '?' end
local function raw_of(token)
    for i, c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id == token then return c, i end end
end
local function tick() return df.global.cur_year * 403200 + df.global.cur_year_tick end

-- ------------------------------------------------------------------ tiles ----
local function tt(x, y, z) return dfhack.maps.getTileType(x, y, z) end
local function walkable(x, y, z)
    -- open-air floor or ramp, not in deep water
    local t = tt(x, y, z); if not t then return false end
    local sa = df.tiletype_shape.attrs[df.tiletype.attrs[t].shape]
    if not sa.walkable then return false end
    if sa.basic_shape ~= df.tiletype_shape_basic.Floor and sa.basic_shape ~= df.tiletype_shape_basic.Ramp then return false end
    local d = dfhack.maps.getTileFlags(x, y, z)
    return d ~= nil and d.flow_size < 4 and d.outside
end
local function deep(x, y, z)
    local d = dfhack.maps.getTileFlags(x, y, z)
    return d and d.flow_size >= 4 and not d.liquid_type and d.outside
end
-- cavern variants: the same tests, but under the ground (subterranean, not outside)
local function cwalk(x, y, z)
    local t = tt(x, y, z); if not t then return false end
    local sa = df.tiletype_shape.attrs[df.tiletype.attrs[t].shape]
    if not sa.walkable then return false end
    if sa.basic_shape ~= df.tiletype_shape_basic.Floor and sa.basic_shape ~= df.tiletype_shape_basic.Ramp then return false end
    local d = dfhack.maps.getTileFlags(x, y, z)
    return d ~= nil and d.flow_size < 4 and d.subterranean and not d.outside
end
local function cdeep(x, y, z)
    local d = dfhack.maps.getTileFlags(x, y, z)
    return d and d.flow_size >= 4 and not d.liquid_type and d.subterranean and not d.outside
end
local function free(x, y, z)
    local b = dfhack.maps.getTileBlock(x, y, z)
    return b and not b.occupancy[x % 16][y % 16].unit
end
local function surface_z(x, y)
    local _, _, zmax = dfhack.maps.getTileSize()
    for z = zmax - 1, 0, -1 do
        if walkable(x, y, z) or deep(x, y, z) then return z end
        local t = tt(x, y, z)
        if t and df.tiletype.attrs[t].shape ~= df.tiletype_shape.EMPTY and df.tiletype.attrs[t].shape ~= df.tiletype_shape.RAMP_TOP then return nil end
    end
end

local function column(x, y)
    -- the top water level and how many levels of water (flow >= 4) stand below it, or nil when the column is dry
    local _, _, zmax = dfhack.maps.getTileSize()
    for z = zmax - 1, 0, -1 do
        if deep(x, y, z) then
            local n = 0
            while z - n >= 0 do
                local d = dfhack.maps.getTileFlags(x, y, z - n)
                if not (d and d.flow_size >= 4 and not d.liquid_type) then break end
                n = n + 1
            end
            return z, n
        end
        local t = tt(x, y, z)
        if t and df.tiletype.attrs[t].shape ~= df.tiletype_shape.EMPTY then return nil end
    end
end

-- ------------------------------------------------------- unit classes (v7.1) ----
-- One place for who a unit is, so wipe, wipecheck, the watch's origin split and groups3 all read the same classes.
local function ucall(name, u)
    local f = dfhack.units[name]
    if not f then return false end
    local ok, v = pcall(f, u)
    return ok and v or false
end
local function uflag(t, k)
    local ok, v = pcall(function() return t[k] end)
    return ok and v or false
end
-- layer_depth 0-2 are the caverns, 3 the magma sea, 4 the underworld (cx-probe cave_depth, 18 Sep 2026)
local depth_cache = {}
local function cave_depth(cid)
    if depth_cache[cid] == nil then
        local ur = df.global.world.world_data.underground_regions
        local reg = (cid >= 0 and cid < #ur) and ur[cid] or nil
        depth_cache[cid] = reg and reg.layer_depth or -1
    end
    return depth_cache[cid]
end
local function ulayer(u)
    local r = u.animal.population
    if r.feature_idx >= 0 then return 'feature' end
    if r.cave_id >= 0 then return cave_depth(r.cave_id) >= 3 and 'deep' or 'cavern' end
    if r.population_idx < 0 then
        local d = dfhack.maps.getTileFlags(u.pos)
        return (d and d.outside) and 'surface' or 'underground'
    end
    return 'surface'
end
local function ref6(r)
    return ('%d,%d,%d,%d,%d,%d'):format(r.region_x, r.region_y, r.feature_idx, r.cave_id, r.site_id, r.population_idx)
end
-- fb_safe: the tool never writes a non-natural unit, and neither does the harness's wipe (R60: demons untouched)
local function nonnatural(u)
    for _, f in ipairs({ 'isMegabeast', 'isSemiMegabeast', 'isTitan', 'isDemon', 'isNightCreature', 'isUndead', 'isForgottenBeast' }) do
        if ucall(f, u) then return f end
    end
    local c = df.creature_raw.find(u.race)
    if c then
        if uflag(c.flags, 'GENERATED') then return 'GENERATED' end
        local cs = c.caste[u.caste]
        if cs then
            for _, k in ipairs({ 'MEGABEAST', 'SEMIMEGABEAST', 'FEATURE_BEAST', 'TITAN', 'DEMON', 'UNIQUE_DEMON', 'NIGHT_CREATURE_ANY' }) do
                if uflag(cs.flags, k) then return k end
            end
        end
    end
    return nil
end
-- R23: DF's invasions are off in this build; the test is a guard (mirrors the tool's WILD.onMap, addendum 49)
local function is_invader(u)
    local ok, v = pcall(function() return u.invasion_id end)
    if ok and type(v) == 'number' and v >= 0 then return true end
    return uflag(u.flags1, 'active_invader') or uflag(u.flags1, 'invader_origin')
end
-- 'citizen' | 'guest' | 'livestock' | nil (nil = an animal: drawn, placed or released)
local function side(u)
    if ucall('isCitizen', u) or ucall('isResident', u) then return 'citizen' end
    if is_invader(u) or uflag(u.flags1, 'merchant') or uflag(u.flags1, 'diplomat') or uflag(u.flags1, 'forest')
        or ucall('isVisitor', u) then return 'guest' end
    if uflag(u.flags1, 'tame') or ucall('isPet', u) or ucall('isFortControlled', u) or ucall('isOwnCiv', u) then return 'livestock' end
    if u.civ_id >= 0 then return 'guest' end
    return nil
end
local function origin(u)
    if not u then return '?' end
    if S.spawned[u.id] then return 'placed' end
    if u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature then return 'drawn' end
    if side(u) then return side(u) end
    return 'released'
end
local function onmap(u) return not dfhack.units.isDead(u) and not u.flags1.inactive and u.pos.x >= 0 end
-- an animal the wipe may take: on the map, not fort-side (livestock only when asked), natural, not deep
local function wipeable(u, livestock)
    if not onmap(u) then return false, 'off' end
    local sd = side(u)
    if sd == 'citizen' or sd == 'guest' then return false, sd end
    if sd == 'livestock' and not livestock then return false, 'livestock' end
    if nonnatural(u) then return false, 'nonnatural' end
    if ulayer(u) == 'deep' then return false, 'deep' end
    return true, sd == 'livestock' and 'livestock' or origin(u)
end
-- every Animal entry the site's map can draw from: its region tiles and their ring, every layer (cx-load sitePools)
local function closePools()
    local site = df.world_site.find(df.global.plotinfo.site_id)
    if not site then return 0 end
    local x0, x1 = site.global_min_x // 16, site.global_max_x // 16
    local y0, y1 = site.global_min_y // 16, site.global_max_y // 16
    local n = 0
    for _, p in ipairs(df.global.world.populations.all) do
        local r = p.population
        if p.type == df.world_population_type.Animal and r.region_x >= x0 - 1 and r.region_x <= x1 + 1
            and r.region_y >= y0 - 1 and r.region_y <= y1 + 1 then p.quantity = 0; p.flags.extinct = true; n = n + 1 end
    end
    return n
end
local function tool()
    local ok, sw = pcall(reqscript, 'seasonal-wildlife')
    if ok and type(sw) == 'table' then return sw end
end
local function word(s) return (tostring(s or ''):gsub('[%s=]+', '_')):sub(1, 80) end

-- ------------------------------------------------------------------ verbs ----
if cmd == 'spot' then
    -- the open spot nearest the map centre: every tile within 4 walkable (land), or a walkable tile with deep
    -- water within 2 (shore), or a deep-water tile with deep water all round (water)
    local kind, need = args[2] or 'land', tonumber(args[3]) or 40
    local X, Y = dfhack.maps.getTileSize()
    local cx, cy, best, bd = X // 2, Y // 2, nil, 1e9
    local cit = {}   -- keep 30 tiles from every citizen: spawned predators must not find the fort
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(u) and not dfhack.units.isDead(u) then cit[#cit + 1] = { u.pos.x, u.pos.y } end
    end
    local function nearFort(x, y)
        for _, c in ipairs(cit) do if math.abs(c[1] - x) + math.abs(c[2] - y) < 30 then return true end end
        return false
    end
    for y = 6, Y - 7, 3 do for x = 6, X - 7, 3 do
        local z = surface_z(x, y)
        if z then
            local nw, nd = 0, 0
            for dy = -4, 4 do for dx = -4, 4 do
                -- water often stands one level below its bank (ECO W1L, LAKE: 'no shore spot' on the same level)
                if walkable(x + dx, y + dy, z) then nw = nw + 1
                elseif deep(x + dx, y + dy, z) or deep(x + dx, y + dy, z - 1) then nd = nd + 1 end
            end end
            local depthOK = true
            if kind == 'shallow' or kind == 'deepwater' then
                local _, n = column(x, y)
                depthOK = n ~= nil and ((kind == 'shallow' and n == 1) or (kind == 'deepwater' and n >= 3))
            end
            local ok = (kind == 'land' and nw >= need and nd == 0 and walkable(x, y, z))
                or ((kind == 'shallow' or kind == 'deepwater') and depthOK and deep(x, y, z) and nd >= 40)
                or (kind == 'shore' and walkable(x, y, z) and nd >= 12 and nw >= 20)
                or (kind == 'water' and deep(x, y, z) and nd >= 60)
            local d = math.abs(x - cx) + math.abs(y - cy)
            if ok and (kind ~= 'land' or not nearFort(x, y)) and d < bd then best, bd = { x, y, z, nw, nd }, d end
        end
    end end
    if not best then do return fail('no ' .. kind .. ' spot on this map') end end
    out('spot', { { 'kind', kind }, { 'x', best[1] }, { 'y', best[2] }, { 'z', best[3] }, { 'walk81', best[4] }, { 'deep81', best[5] } })

elseif cmd == 'cavespot' then
    -- cavespot cavern|cavepool [skip]: an open cavern floor (>= 50 of 81 tiles cavern floor) or a cavern pool edge
    -- (floor with >= 12 of 81 tiles of cavern water on its level or one below); the nth (skip) match from the top
    local kind, skip = args[2] or 'cavern', tonumber(args[3]) or 0
    local X, Y, Z = dfhack.maps.getTileSize()
    local zhi, zlo = tonumber(args[4]) or (Z - 1), tonumber(args[5]) or 0   -- a cavern layer's band (`seasonal-wildlife caverns`)
    local found = 0
    for z = zhi, zlo, -1 do
        for y = 6, Y - 7, 4 do for x = 6, X - 7, 4 do
            if cwalk(x, y, z) then
                local nw, nd = 0, 0
                for dy = -4, 4 do for dx = -4, 4 do
                    if cwalk(x + dx, y + dy, z) then nw = nw + 1
                    elseif cdeep(x + dx, y + dy, z) or cdeep(x + dx, y + dy, z - 1) then nd = nd + 1 end
                end end
                if (kind == 'cavern' and nw >= 50 and nd == 0) or (kind == 'cavepool' and nw >= 20 and nd >= 12) then
                    if found == skip then
                        out('spot', { { 'kind', kind }, { 'x', x }, { 'y', y }, { 'z', z }, { 'walk81', nw }, { 'deep81', nd } }); return
                    end
                    found = found + 1
                end
            end
        end end
    end
    do return fail('no ' .. kind .. ' spot on this map') end

elseif cmd == 'where' then
    -- where TOKEN: every spawned TOKEN still known: id, position, and the state that could explain a departure
    for id, tok in pairs(S.spawned) do if tok == args[2] then
        local u = df.unit.find(id)
        if not u then out('where', { { 'id', id }, { 'state', 'removed' } })
        else
            local j = u.job.current_job
            out('where', { { 'id', id }, { 'x', u.pos.x }, { 'y', u.pos.y }, { 'z', u.pos.z }, { 'inactive', tostring(u.flags1.inactive) },
                { 'dead', tostring(dfhack.units.isDead(u)) }, { 'leave', u.animal.leave_countdown }, { 'vanish', u.animal.vanish_countdown },
                { 'job', j and df.job_type[j.job_type] or '-' }, { 'goal', df.unit_path_goal[u.path.goal] or u.path.goal },
                { 'dest', u.path.dest.x .. ',' .. u.path.dest.y .. ',' .. u.path.dest.z }, { 'items', #u.inventory },
                { 'wild', tostring(dfhack.units.isWildlife(u)) }, { 'merchant', tostring(u.flags1.merchant) },
                { 'forest', tostring(u.flags1.forest) }, { 'marauder', tostring(u.flags2.visitor_uninvited or false) } })
        end
    end end

elseif cmd == 'misc' then
    -- misc TOKEN FIELD VALUE: set a caste misc value (prone_to_rage, viewrange, vision_arc_min/max, grazer, ...)
    -- on every caste, snapshotted for `restore`
    local craw = raw_of(args[2] or '')
    if not craw then do return fail('no creature ' .. tostring(args[2])) end end
    local field, v = args[3], tonumber(args[4])
    for ci, cst in ipairs(craw.caste) do
        local key = args[2] .. ':' .. ci .. ':misc.' .. field
        if S.flags[key] == nil then S.flags[key] = cst.misc[field] end
        cst.misc[field] = v
    end
    out('misc', { { 'token', args[2] }, { 'field', field }, { 'value', v } })

elseif cmd == 'vermin' then
    -- vermin X Y Z R [tag]: vermin (not units) within R of X,Y,Z on levels z-1..z+1, by species
    local x0, y0, z0, r = tonumber(args[2]), tonumber(args[3]), tonumber(args[4]), tonumber(args[5]) or 10
    local by, n = {}, 0
    for _, v in ipairs(df.vermin.get_vector()) do
        if v.visible ~= false and math.abs(v.pos.x - x0) <= r and math.abs(v.pos.y - y0) <= r and math.abs(v.pos.z - z0) <= 1 then
            local c = df.creature_raw.find(v.race); local k = c and c.creature_id or '?'
            by[k] = (by[k] or 0) + (v.amount or 1); n = n + (v.amount or 1)
        end
    end
    local parts = { { 'tag', args[6] or '-' }, { 'total', n } }
    for k, c in pairs(by) do parts[#parts + 1] = { k, c } end
    out('vermin', parts)

elseif cmd == 'vspot' then
    -- vspot [surface|cavern]: the densest 10x10 cluster of live vermin (by amount), on the surface (outside) or below
    local want = args[2] or 'surface'
    local bins, best, bk = {}, 0, nil
    for _, v in ipairs(df.vermin.get_vector()) do
        local d = dfhack.maps.getTileFlags(v.pos)
        if d and ((want == 'surface') == (d.outside == true)) then
            local k = (v.pos.x // 10) .. ',' .. (v.pos.y // 10) .. ',' .. v.pos.z
            bins[k] = (bins[k] or 0) + (v.amount or 1)
            if bins[k] > best then best, bk = bins[k], { v.pos.x, v.pos.y, v.pos.z } end
        end
    end
    if not bk then do return fail('no ' .. want .. ' vermin on this map') end end
    out('spot', { { 'kind', 'vermin' }, { 'x', bk[1] }, { 'y', bk[2] }, { 'z', bk[3] }, { 'vermin', best } })

elseif cmd == 'fortspot' then
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(u) and not dfhack.units.isDead(u) then
            out('spot', { { 'kind', 'fort' }, { 'x', u.pos.x }, { 'y', u.pos.y }, { 'z', u.pos.z } }); return
        end
    end
    do return fail('no citizen') end

elseif cmd == 'depth' then
    -- depth [tag]: histogram of water-column depth over every surface water column of the map
    local X, Y = dfhack.maps.getTileSize()
    local h, cols = {}, 0
    for y = 0, Y - 1 do for x = 0, X - 1 do
        local _, n = column(x, y)
        if n then cols = cols + 1; local k = math.min(n, 10); h[k] = (h[k] or 0) + 1 end
    end end
    local parts = { { 'tag', args[2] or '-' }, { 'columns', cols }, { 'map', X .. 'x' .. Y } }
    for k = 1, 10 do parts[#parts + 1] = { 'd' .. k, h[k] or 0 } end
    out('depth', parts)

elseif cmd == 'relfort' then
    -- relfort TOKEN: PREDATOR_OR_PREY between every spawned TOKEN and every citizen (test only; never saved)
    local cache, v, n = df.global.world.enemy_status_cache, df.unit_reaction_type.PREDATOR_OR_PREY, 0
    for id, tok in pairs(S.spawned) do if tok == args[2] then
        local a = df.unit.find(id); local sa = a and a.enemy.enemy_status_slot or -1
        for _, u in ipairs(df.global.world.units.active) do
            local sb = u.enemy.enemy_status_slot
            if dfhack.units.isCitizen(u) and sa >= 0 and sb >= 0 then cache.rel_map[sa][sb].ur = v; cache.rel_map[sb][sa].ur = v; n = n + 1 end
        end
    end end
    out('relfort', { { 'token', args[2] }, { 'pairs', n } })

elseif cmd == 'seek' then
    -- seek TOKEN X Y Z [goal]: point every spawned TOKEN's path at X,Y,Z (the tool-driven walk for scavenging)
    local pos, goal, n = xyz2pos(tonumber(args[3]), tonumber(args[4]), tonumber(args[5])), args[6], 0
    for id, tok in pairs(S.spawned) do if tok == args[2] then
        local u = df.unit.find(id)
        if u and not dfhack.units.isDead(u) then
            u.path.dest:assign(pos); u.path.path.x:resize(0); u.path.path.y:resize(0); u.path.path.z:resize(0)
            if goal and df.unit_path_goal[goal] then u.path.goal = df.unit_path_goal[goal] end
            n = n + 1
        end
    end end
    out('seek', { { 'token', args[2] }, { 'units', n }, { 'goal', goal or '-' } })

elseif cmd == 'walkto' then
    -- walkto TOKEN X Y Z: give every spawned TOKEN a full path (a straight line of tiles on its level) to X,Y,Z;
    -- DF units step along unit.path.path, and `seek` (dest alone) moved nobody (ECO S2, 30 Sep)
    local tx, ty, tz, n = tonumber(args[3]), tonumber(args[4]), tonumber(args[5]), 0
    for id, tok in pairs(S.spawned) do if tok == args[2] then
        local u = df.unit.find(id)
        if u and not dfhack.units.isDead(u) and u.pos.z == tz then
            local p = u.path.path
            p.x:resize(0); p.y:resize(0); p.z:resize(0)
            local x, y = u.pos.x, u.pos.y
            while x ~= tx or y ~= ty do
                if x ~= tx then x = x + (tx > x and 1 or -1) end
                if y ~= ty then y = y + (ty > y and 1 or -1) end
                p.x:insert('#', x); p.y:insert('#', y); p.z:insert('#', tz)
            end
            u.path.dest:assign(xyz2pos(tx, ty, tz))
            u.path.goal = df.unit_path_goal.SeekStation
            n = n + 1
        end
    end end
    out('walkto', { { 'token', args[2] }, { 'units', n } })

elseif cmd == 'tp' then
    -- tp TOKEN X Y Z: teleport every spawned TOKEN to X,Y,Z (the tool's nudge does this already)
    local n = 0
    for id, tok in pairs(S.spawned) do if tok == args[2] then
        local u = df.unit.find(id)
        if u and not dfhack.units.isDead(u) and dfhack.units.teleport(u, xyz2pos(tonumber(args[3]), tonumber(args[4]), tonumber(args[5]))) then n = n + 1 end
    end end
    out('tp', { { 'token', args[2] }, { 'units', n } })

elseif cmd == 'near' then
    -- near TOKEN X Y Z [r=2]: how many spawned TOKEN stand within r of X,Y,Z
    local r, n, tot = tonumber(args[6]) or 2, 0, 0
    for id, tok in pairs(S.spawned) do if tok == args[2] then
        local u = df.unit.find(id)
        if u and not dfhack.units.isDead(u) then
            tot = tot + 1
            if u.pos.z == tonumber(args[5]) and math.abs(u.pos.x - tonumber(args[3])) <= r and math.abs(u.pos.y - tonumber(args[4])) <= r then n = n + 1 end
        end
    end end
    out('near', { { 'token', args[2] }, { 'near', n }, { 'of', tot } })

elseif cmd == 'eat' then
    -- eat TOKEN [reach=1]: every corpse item within reach of a spawned TOKEN is removed (the tool's "eating")
    local reach, eaten, near = tonumber(args[3]) or 1, 0, 0
    local us = {}
    for id, tok in pairs(S.spawned) do if tok == args[2] then
        local u = df.unit.find(id); if u and not dfhack.units.isDead(u) then us[#us + 1] = u end
    end end
    local doomed = {}
    for _, it in ipairs(df.global.world.items.all) do
        local t = df.item_type[it:getType()]
        if (t == 'CORPSE' or t == 'CORPSEPIECE' or t == 'REMAINS') and not it.flags.in_inventory then
            local px, py, pz = dfhack.items.getPosition(it)
            if px then for _, u in ipairs(us) do
                if u.pos.z == pz and math.abs(u.pos.x - px) <= reach and math.abs(u.pos.y - py) <= reach then doomed[#doomed + 1] = it; break end
            end end
        end
    end
    for _, it in ipairs(doomed) do if dfhack.items.remove(it) then eaten = eaten + 1 end end
    out('eat', { { 'token', args[2] }, { 'units', #us }, { 'eaten', eaten } })

elseif cmd == 'spawn' then
    local token, n = args[2], tonumber(args[3]) or 1
    local x0, y0, z0 = tonumber(args[4]), tonumber(args[5]), tonumber(args[6])
    local radius, medium, sex = tonumber(args[7]) or 3, args[8] or 'land', args[9] or 'any'
    local countdown = tonumber(args[10]) or 200000
    -- 'roam' keeps DF's roaming flag: DF then treats the unit as wild (it is not aimed at newcomers as a fort-side
    -- unit, and it counts toward DF's surface gate). Default clears it, as every block before v7.1 did (H4).
    local roam = args[11] == 'roam'
    local craw, ridx = raw_of(token or '')
    if not craw then do return fail('no creature ' .. tostring(token)) end end
    -- a population reference: the species' own site entry when it has one, else any Animal entry (borrowed:
    -- only the refund target on departure changes; runs are short and never saved)
    local ref, borrowed
    for _, p in ipairs(df.global.world.populations.all) do
        if p.type == df.world_population_type.Animal and p.race == ridx then ref = p; break end
    end
    if not ref then
        for _, p in ipairs(df.global.world.populations.all) do
            if p.type == df.world_population_type.Animal and p.population.feature_idx == -1 and p.population.cave_id == -1 then ref, borrowed = p, true; break end
        end
    end
    if not ref then do return fail('no Animal population entry to reference') end end
    local castes = {}
    for ci, cst in ipairs(craw.caste) do
        if sex == 'any' or (sex == 'male' and cst.sex == 1) or (sex == 'female' and cst.sex == 0) then castes[#castes + 1] = ci end
    end
    if #castes == 0 then do return fail('no ' .. sex .. ' caste in ' .. token) end end
    local tiles = {}
    for dy = -radius, radius do for dx = -radius, radius do
        local x, y = x0 + dx, y0 + dy
        if medium == 'water' or medium == 'cavewater' then
            local test = medium == 'water' and deep or cdeep
            for _, z in ipairs({ z0, z0 - 1 }) do
                if test(x, y, z) and free(x, y, z) then tiles[#tiles + 1] = xyz2pos(x, y, z); break end
            end
        elseif medium == 'cave' then
            if cwalk(x, y, z0) and free(x, y, z0) then tiles[#tiles + 1] = xyz2pos(x, y, z0) end
        elseif walkable(x, y, z0) and free(x, y, z0) then tiles[#tiles + 1] = xyz2pos(x, y, z0) end
    end end
    local ids = {}
    for _ = 1, n do
        if #tiles == 0 then break end
        local pos = table.remove(tiles, math.random(1, #tiles))
        local u = dfhack.units.create(ridx, castes[math.random(1, #castes)])
        if u then
            local r, ap = ref.population, u.animal.population
            ap.region_x, ap.region_y = r.region_x, r.region_y
            ap.feature_idx, ap.cave_id, ap.site_id, ap.population_idx = r.feature_idx, r.cave_id, r.site_id, r.population_idx
            u.animal.leave_countdown = countdown
            u.flags2.roaming_wilderness_population_source = roam
            u.flags2.roaming_wilderness_population_source_not_a_map_feature = roam
            u.pos:assign(pos); u.idle_area:assign(pos)
            df.global.world.units.active:insert('#', u)
            local blk = dfhack.maps.getTileBlock(pos)
            if blk then blk.occupancy[pos.x % 16][pos.y % 16].unit = true end
            u.flags1.inactive = false
            -- an enemy-status slot, the way DF allocates one (DF never slots a unit made this way; v5.9.3)
            local cache = df.global.world.enemy_status_cache
            for i = 0, #cache.slot_used - 1 do
                if not cache.slot_used[i] then
                    cache.slot_used[i] = true
                    for j = 0, #cache.slot_used - 1 do cache.rel_map[i][j].ur = 0; cache.rel_map[j][i].ur = 0 end
                    u.enemy.enemy_status_slot = i
                    if cache.next_slot <= i then cache.next_slot = i + 1 end
                    break
                end
            end
            ids[#ids + 1] = u.id
            S.spawned[u.id] = token
        end
    end
    out('spawn', { { 'token', token }, { 'asked', n }, { 'placed', #ids }, { 'medium', medium }, { 'at', x0 .. ',' .. y0 .. ',' .. z0 },
        { 'borrowed_ref', borrowed and 1 or 0 }, { 'roam', roam and 1 or 0 }, { 'ids', table.concat(ids, ',') } })

elseif cmd == 'corpse' then
    -- corpse IDS: every listed spawned unit dies on the spot (blood drained, as exterminate's destroy does) and
    -- leaves its corpse; the units are dropped from the spawned set so `clear` and `read` ignore them
    local n = 0
    for id in tostring(args[2] or ''):gmatch('%d+') do
        local u = df.unit.find(tonumber(id))
        if u then u.body.blood_count = 0; S.spawned[u.id] = nil; n = n + 1 end
    end
    out('corpse', { { 'drained', n } })

elseif cmd == 'items' then
    -- items X Y Z R: corpses and remains within R of X,Y,Z -- count, and how many are held by a unit
    local x0, y0, z0, r = tonumber(args[2]), tonumber(args[3]), tonumber(args[4]), tonumber(args[5]) or 6
    local n, held, gone = 0, 0, 0
    for _, it in ipairs(df.global.world.items.other.ANY_CORPSE or df.global.world.items.all) do
        local t = df.item_type[it:getType()]
        if t == 'CORPSE' or t == 'CORPSEPIECE' or t == 'REMAINS' then
            local px, py, pz = dfhack.items.getPosition(it)
            if px and px >= 0 and math.abs(px - x0) <= r and math.abs(py - y0) <= r and math.abs(pz - z0) <= 1 then
                n = n + 1
                if it.flags.in_inventory then held = held + 1 end
            end
        end
    end
    out('items', { { 'tag', args[6] or '-' }, { 'corpses', n }, { 'held', held } })

elseif cmd == 'rel' then
    local a, b = args[2], args[3]
    local cache, v = df.global.world.enemy_status_cache, df.unit_reaction_type.PREDATOR_OR_PREY
    local n = 0
    for ida, ta in pairs(S.spawned) do if ta == a then
        local ua = df.unit.find(ida)
        for idb, tb in pairs(S.spawned) do if tb == b then
            local ub = df.unit.find(idb)
            local sa, sb = ua and ua.enemy.enemy_status_slot or -1, ub and ub.enemy.enemy_status_slot or -1
            if sa >= 0 and sb >= 0 then cache.rel_map[sa][sb].ur = v; cache.rel_map[sb][sa].ur = v; n = n + 1 end
        end end
    end end
    out('rel', { { 'a', a }, { 'b', b }, { 'pairs', n } })

elseif cmd == 'watch' then
    S.attacks, S.inc0, S.watch, S.t0, S.dropped = {}, #df.global.world.incidents.all, true, tick(), 0
    -- H6: every attack with its tick and both sides' origin; hidden flags sampled every 10 t on the subjects
    S.attacks_o, S.atk, S.atk_over, S.ring, S.hstat, S.lastatk = {}, {}, 0, {}, {}, {}
    S.bout_gap = tonumber(args[2]) or 100
    S.wildpred = args[3] == 'wildpred' or args[2] == 'wildpred'
    S.watchn = {}
    for id, tok in pairs(S.spawned) do
        local u = df.unit.find(id)
        if u and not dfhack.units.isDead(u) then S.watchn[tok] = (S.watchn[tok] or 0) + 1 end
    end
    eventful.enableEvent(eventful.eventType.UNIT_ATTACK, 1)
    eventful.onUnitAttack.cx_eco = function(att, def)
        local E = _G.CX_ECO
        if not E.watch then return end
        local ua, ud = df.unit.find(att), df.unit.find(def)
        local ra, rd = ua and race_of(ua) or '?', ud and race_of(ud) or '?'
        local k = ra .. '>' .. rd
        E.attacks[k] = (E.attacks[k] or 0) + 1
        local ao, dor = origin(ua), origin(ud)
        local ko = ra .. '(' .. ao .. ')>' .. rd .. '(' .. dor .. ')'
        E.attacks_o[ko] = (E.attacks_o[ko] or 0) + 1
        local t = df.global.cur_year * 403200 + df.global.cur_year_tick
        -- the attacker's approach: hidden samples in the 300 t before this attack
        local hn, hh = 0, 0
        for _, smp in ipairs(E.ring[att] or {}) do if t - smp[1] <= 300 then hn = hn + 1; hh = hh + smp[2] end end
        E.lastatk[att] = t
        if #E.atk < 5000 then
            E.atk[#E.atk + 1] = { t - (E.t0 or t), att, ra, ao, def, rd, dor, hh, hn }
        else E.atk_over = E.atk_over + 1 end
    end
    local repeatUtil = require('repeat-util')
    repeatUtil.scheduleEvery('cx_eco_hidden', 10, 'ticks', function()
        local E = _G.CX_ECO
        if not E.watch then return end
        local t = df.global.cur_year * 403200 + df.global.cur_year_tick
        local ids = {}
        for id in pairs(E.spawned) do ids[id] = true end
        for id, lt in pairs(E.lastatk) do if t - lt <= 300 then ids[id] = true end end
        if E.wildpred then
            for _, u in ipairs(df.global.world.units.active) do
                if u.flags2.roaming_wilderness_population_source and not dfhack.units.isDead(u) then
                    local c = df.creature_raw.find(u.race); local cs = c and c.caste[u.caste]
                    if cs and (cs.flags.CARNIVORE or cs.flags.LARGE_PREDATOR) then ids[u.id] = true end
                end
            end
        end
        for id in pairs(ids) do
            local u = df.unit.find(id)
            if u and not dfhack.units.isDead(u) then
                local h = (uflag(u.flags1, 'hidden_in_ambush') or uflag(u.flags1, 'hidden_ambusher')) and 1 or 0
                local r = E.ring[id] or {}; E.ring[id] = r
                r[#r + 1] = { t, h }; if #r > 30 then table.remove(r, 1) end
                local st = E.hstat[id] or { n = 0, h = 0, nn = 0, nh = 0, tok = race_of(u) }; E.hstat[id] = st
                st.n = st.n + 1; st.h = st.h + h
                local lt = E.lastatk[id]
                if lt and t - lt <= 100 then st.nn = st.nn + 1; st.nh = st.nh + h end
            end
        end
    end)
    out('watch', { { 'incidents0', S.inc0 }, { 't0', S.t0 }, { 'bout_gap', S.bout_gap }, { 'hidden_every', 10 },
        { 'wildpred', S.wildpred and 1 or 0 } })

elseif cmd == 'read' then
    local tag = args[2] or '-'
    -- groups: per spawned token alive / dead / on map, mean distance to own centroid, share standing in water
    local g = {}
    for id, tok in pairs(S.spawned) do
        local u = df.unit.find(id)
        local r = g[tok] or { alive = 0, dead = 0, gone = 0, xs = {}, wet = 0, inact = 0, off = 0 }
        g[tok] = r
        if not u then r.gone = r.gone + 1
        elseif dfhack.units.isDead(u) then r.dead = r.dead + 1
        elseif u.flags1.inactive or u.pos.x < 0 then
            r.gone = r.gone + 1
            if u.flags1.inactive then r.inact = r.inact + 1 end
            if u.pos.x < 0 then r.off = r.off + 1 end
        else
            r.alive = r.alive + 1; r.xs[#r.xs + 1] = { u.pos.x, u.pos.y, u.pos.z }
            local d = dfhack.maps.getTileFlags(u.pos)
            if d and d.flow_size >= 4 then r.wet = r.wet + 1 end
        end
    end
    for tok, r in pairs(g) do
        local sx, sy, sd = 0, 0, 0
        for _, p in ipairs(r.xs) do sx, sy = sx + p[1], sy + p[2] end
        local n = math.max(1, #r.xs); sx, sy = sx / n, sy / n
        for _, p in ipairs(r.xs) do sd = sd + math.sqrt((p[1] - sx) ^ 2 + (p[2] - sy) ^ 2) end
        out('group', { { 'tag', tag }, { 'token', tok }, { 'alive', r.alive }, { 'dead', r.dead }, { 'gone', r.gone }, { 'inactive', r.inact }, { 'offmap', r.off },
            { 'spread', ('%.1f'):format(sd / n) }, { 'wet', r.wet }, { 'cx', ('%.0f'):format(sx) }, { 'cy', ('%.0f'):format(sy) } })
    end
    for k, c in pairs(S.attacks or {}) do out('attacks', { { 'tag', tag }, { 'pair', k }, { 'n', c } }) end
    local inc = df.global.world.incidents.all
    for i = (S.inc0 or #inc), #inc - 1 do
        local it = inc[i]
        if it.type == df.incident_type.Death and df.death_type[it.death_cause] ~= 'VANISH' then
            local v, k = df.unit.find(it.victim), df.unit.find(it.criminal)
            out('death', { { 'tag', tag }, { 'victim', v and race_of(v) or it.victim }, { 'killer', k and race_of(k) or it.criminal },
                { 'cause', df.death_type[it.death_cause] or it.death_cause }, { 'victim_spawned', S.spawned[it.victim] and 1 or 0 },
                { 'killer_spawned', S.spawned[it.criminal] and 1 or 0 },
                -- ticks from the watch to the death (ECO CAL, 30 Sep: kill rates over a long cell need the time of each kill)
                { 'dt', (function() local ok, v = pcall(function() return it.event_year * 403200 + it.event_time - (S.t0 or 0) end); return ok and v or -1 end)() } })
        end
    end
    -- H6: attacks by origin, each attack, bouts (attacks with gaps < bout_gap) and hidden samples
    for k, c in pairs(S.attacks_o or {}) do out('attacks_o', { { 'tag', tag }, { 'pair', k }, { 'n', c } }) end
    local per = {}
    for _, a in ipairs(S.atk or {}) do
        out('atk', { { 'tag', tag }, { 't', a[1] }, { 'a', a[2] }, { 'atok', a[3] }, { 'aor', a[4] }, { 'd', a[5] }, { 'dtok', a[6] },
            { 'dor', a[7] }, { 'hid', a[8] }, { 'hn', a[9] } })
        local p = per[a[2]] or { tok = a[3], aor = a[4], ts = {} }; per[a[2]] = p
        p.ts[#p.ts + 1] = a[1]
    end
    if (S.atk_over or 0) > 0 then out('atk_over', { { 'tag', tag }, { 'dropped', S.atk_over } }) end
    local gap, ticks = S.bout_gap or 100, tick() - (S.t0 or tick())
    local bt = {}
    for id, p in pairs(per) do
        table.sort(p.ts)
        local b = 0
        for i, t in ipairs(p.ts) do if i == 1 or t - p.ts[i - 1] >= gap then b = b + 1 end end
        out('bout', { { 'tag', tag }, { 'a', id }, { 'atok', p.tok }, { 'aor', p.aor }, { 'attacks', #p.ts }, { 'bouts', b },
            { 'first', p.ts[1] }, { 'last', p.ts[#p.ts] } })
        local s2 = bt[p.tok] or { attackers = 0, attacks = 0, bouts = 0 }; bt[p.tok] = s2
        s2.attackers = s2.attackers + 1; s2.attacks = s2.attacks + #p.ts; s2.bouts = s2.bouts + b
    end
    for tok, s2 in pairs(bt) do
        local hunters = (S.watchn or {})[tok] or s2.attackers
        local days = math.max(ticks, 1) / 1200
        out('bouts', { { 'tag', tag }, { 'atok', tok }, { 'hunters', hunters }, { 'attackers', s2.attackers }, { 'attacks', s2.attacks },
            { 'bouts', s2.bouts }, { 'ticks', ticks }, { 'per_hunter_day', ('%.3f'):format(s2.bouts / (math.max(hunters, 1) * days)) } })
    end
    for id, st in pairs(S.hstat or {}) do
        out('hidden', { { 'tag', tag }, { 'id', id }, { 'token', st.tok }, { 'samples', st.n }, { 'hidden', st.h },
            { 'near', st.nn }, { 'near_hidden', st.nh } })
    end
    local al = 0
    for _, a in ipairs(df.global.world.status.announcement_alert) do if a.type == df.announcement_alert_type.COMBAT then al = al + 1 end end
    out('alerts', { { 'tag', tag }, { 'combat', al }, { 'dropped', S.dropped or 0 }, { 'ticks', tick() - (S.t0 or tick()) } })

elseif cmd == 'clear' then
    local n = 0
    for id in pairs(S.spawned) do
        local u = df.unit.find(id)
        if u and not dfhack.units.isDead(u) then u.animal.vanish_countdown = 2; n = n + 1 end
    end
    S.spawned, S.watch = {}, false
    eventful.onUnitAttack.cx_eco = nil
    require('repeat-util').cancel('cx_eco_hidden')
    out('clear', { { 'vanished', n } })

elseif cmd == 'flag' then
    local token, flag, on = args[2], args[3], args[4] ~= 'off'
    local craw = raw_of(token or '')
    if not craw then do return fail('no creature ' .. tostring(token)) end end
    local where
    if df.caste_raw_flags[flag] ~= nil then
        for ci, cst in ipairs(craw.caste) do
            local key = token .. ':' .. ci .. ':' .. flag
            if S.flags[key] == nil then S.flags[key] = cst.flags[flag] end
            cst.flags[flag] = on
        end
        where = 'caste'
    elseif df.creature_raw_flags[flag] ~= nil then
        local key = token .. ':-:' .. flag
        if S.flags[key] == nil then S.flags[key] = craw.flags[flag] end
        craw.flags[flag] = on
        where = 'creature'
    else do return fail('no caste or creature flag ' .. tostring(flag)) end end
    out('flag', { { 'token', token }, { 'flag', flag }, { 'on', on }, { 'level', where } })

elseif cmd == 'restore' then
    local n = 0
    for key, v in pairs(S.flags) do
        local token, ci, flag = key:match('^([^:]+):([^:]+):(.+)$')
        local craw = raw_of(token)
        if craw then
            if ci == '-' then craw.flags[flag] = v
            elseif flag:sub(1, 5) == 'misc.' then craw.caste[tonumber(ci)].misc[flag:sub(6)] = v
            else craw.caste[tonumber(ci)].flags[flag] = v end
            n = n + 1
        end
    end
    S.flags = {}
    out('restore', { { 'flags', n } })

elseif cmd == 'lead' then
    local token, how = args[2], args[3] or 'lowest'
    local us = {}
    for id, tok in pairs(S.spawned) do
        local u = df.unit.find(id)
        if tok == token and u and not dfhack.units.isDead(u) then us[#us + 1] = u end
    end
    table.sort(us, function(a, b) return a.id < b.id end)
    local leader
    if how == 'largest-male' then
        for _, u in ipairs(us) do
            if u.sex == 1 and (not leader or u.body.size_info.size_cur > leader.body.size_info.size_cur) then leader = u end
        end
    elseif how == 'lowest' then leader = us[1] end
    for _, u in ipairs(us) do
        if how == 'none' or u == leader then u.following = nil
        elseif leader then u.following = leader end
    end
    out('lead', { { 'token', token }, { 'how', how }, { 'leader', leader and leader.id or -1 },
        { 'leader_size', leader and leader.body.size_info.size_cur or 0 }, { 'members', #us } })

elseif cmd == 'alerts' then
    -- prototype: every tick, drop COMBAT alerts in which no unit belongs to the fort (citizens, their pets,
    -- visitors stay). Runs on eventful's TICK-free path: repeat-util.
    -- alerts drop-wild on|off [humanoid]: 'humanoid' also keeps any alert with a humanoid in it -- a creature some
    -- entity (civilisation) is made of, or an animal person (creature class ANIMAL_PERSON, or an id ending MAN) --
    -- so custom entities (gnomes...) always alert; only non-humanoid wildlife fights are dropped (user, 30 Sep)
    local on, mode = args[3] ~= 'off', args[4] or 'fort'
    if mode == 'humanoid' then
        local h, n = {}, 0
        for _, e in ipairs(df.global.world.raws.entities) do
            for _, cid in ipairs(e.creature_ids) do if not h[cid] then h[cid] = true; n = n + 1 end end
        end
        for i, c in ipairs(df.global.world.raws.creatures.all) do
            local ap = false
            for _, cl in ipairs(c.caste[0].creature_class) do if cl.value == 'ANIMAL_PERSON' then ap = true end end
            if ap or c.creature_id:match('MAN$') then if not h[i] then h[i] = true; n = n + 1 end end
        end
        _G.CX_ECO.humanoid = h
        out('humanoid', { { 'races', n } })
    end
    local repeatUtil = require('repeat-util')
    if on then
        repeatUtil.scheduleEvery('cx_eco_alerts', 1, 'ticks', function()
            local al = df.global.world.status.announcement_alert
            for i = #al - 1, 0, -1 do
                local a = al[i]
                if a.type == df.announcement_alert_type.COMBAT then
                    local fort = false
                    for j = 0, #a.report_unid - 1 do
                        local u = df.unit.find(a.report_unid[j])
                        if u and (dfhack.units.isCitizen(u) or dfhack.units.isOwnCiv(u) or dfhack.units.isFortControlled(u)
                            or (mode == 'humanoid' and _G.CX_ECO.humanoid[u.race])) then fort = true end
                    end
                    if not fort then al:erase(i); _G.CX_ECO.dropped = (_G.CX_ECO.dropped or 0) + 1 end
                end
            end
        end)
    else repeatUtil.cancel('cx_eco_alerts') end
    out('alerts_filter', { { 'on', on }, { 'mode', mode } })

elseif cmd == 'wipe' then
    -- R15 (user, 1 Oct 2026): every cell rep starts with NO animals on the map -- drawn, placed or released -- before
    -- the experiment places its groups, so natives and earlier cells' units cannot pile into a later cell (SW1R).
    -- Exterminate's method: vanish_countdown 1, gone on the next tick, no corpse. Citizens, guests, non-natural and
    -- deep-layer units are never touched; livestock only with the 'livestock' word.
    local opt = {}
    for i = 2, #args do opt[args[i]] = true end
    local C = { drawn = 0, placed = 0, released = 0, livestock = 0 }
    local K = { citizen = 0, guest = 0, livestock = 0, nonnatural = 0, deep = 0 }
    local marked = 0
    for _, u in ipairs(df.global.world.units.active) do
        local ok, why = wipeable(u, opt.livestock)
        if ok then
            C[why] = (C[why] or 0) + 1
            u.animal.vanish_countdown = 1
            S.spawned[u.id] = nil
            marked = marked + 1
        elseif K[why] then K[why] = K[why] + 1 end
    end
    local closed = opt.close and closePools() or -1
    S.wiped = (S.wiped or 0) + marked
    out('wipe', { { 'marked', marked }, { 'drawn', C.drawn }, { 'placed', C.placed }, { 'released', C.released },
        { 'livestock', C.livestock }, { 'kept_citizen', K.citizen }, { 'kept_guest', K.guest }, { 'kept_livestock', K.livestock },
        { 'kept_nonnatural', K.nonnatural }, { 'kept_deep', K.deep }, { 'pools_closed', closed } })

elseif cmd == 'wipecheck' then
    local livestock = args[2] == 'livestock'
    local rem, pend, by = 0, 0, {}
    for _, u in ipairs(df.global.world.units.active) do
        if wipeable(u, livestock) then
            if u.animal.vanish_countdown > 0 then pend = pend + 1
            else rem = rem + 1; local k = race_of(u); by[k] = (by[k] or 0) + 1 end
        end
    end
    local parts = { { 'remaining', rem }, { 'pending', pend } }
    local ks = {}
    for k in pairs(by) do ks[#ks + 1] = k end
    table.sort(ks)
    for i = 1, math.min(8, #ks) do parts[#parts + 1] = { ks[i], by[ks[i]] } end
    out('wipecheck', parts)

elseif cmd == 'groups3' then
    -- H5: ONE definition of a group, checked three ways. A group is the live, on-map animals that share species,
    -- population entry (ref6) and arrival sample (the first groups3 call that saw them; units on the map at `base`
    -- share that sample). Against it: (2) the tool's record (sw.loadGroups: which canonical groups each tool group's
    -- live members fall in) and (3) DF's population entries (quantity now against the reading at `base`; a net
    -- figure: debits, refunds and regrowth all move it -- trap 16).
    local tag = args[2] or '-'
    if tag == 'reset' then S.g3seen, S.g3pop0 = nil, nil; out('g3', { { 'tag', 'reset' } }); return end
    local t = tick()
    S.g3seen = S.g3seen or {}
    if tag == 'base' or not S.g3pop0 then
        S.g3pop0 = {}
        for _, p in ipairs(df.global.world.populations.all) do
            if p.type == df.world_population_type.Animal then S.g3pop0[p.race .. '|' .. ref6(p.population)] = p.quantity end
        end
    end
    local live, unitKey = {}, {}
    for _, u in ipairs(df.global.world.units.active) do
        if onmap(u) and not side(u) and not nonnatural(u) then
            local L = ulayer(u)
            if L ~= 'deep' then
                local seen = S.g3seen[u.id]
                if not seen then seen = t; S.g3seen[u.id] = t end
                local rf = ref6(u.animal.population)
                local k = race_of(u) .. '|' .. rf .. '|' .. seen
                local g = live[k]
                if not g then g = { tok = race_of(u), race = u.race, ref = rf, seen = seen, layer = L, n = 0, o = {} }; live[k] = g end
                g.n = g.n + 1
                local o = origin(u); g.o[o] = (g.o[o] or 0) + 1
                unitKey[u.id] = k
            end
        end
    end
    local pop = {}
    for _, p in ipairs(df.global.world.populations.all) do
        if p.type == df.world_population_type.Animal then pop[p.race .. '|' .. ref6(p.population)] = p end
    end
    local sw, groups = tool(), nil
    if sw and sw.loadGroups then
        local ok, g = pcall(sw.loadGroups)
        if ok and type(g) == 'table' then groups = g.groups end
    end
    local toolOf, sum = {}, {}
    local function S3(L) sum[L] = sum[L] or { live = 0, tool = 0, match = 0, untracked = 0, split = 0, merged = 0, stale = 0, nopop = 0, debited = 0 }; return sum[L] end
    for gi, grp in ipairs(groups or {}) do
        local keys, nk, nlive = {}, 0, 0
        for _, id in ipairs(grp.ids or {}) do
            local k = unitKey[id]
            if k then
                nlive = nlive + 1
                if not keys[k] then keys[k] = true; nk = nk + 1 end
                toolOf[k] = toolOf[k] or {}; toolOf[k][gi] = true
            end
        end
        local v = nlive == 0 and 'stale' or (nk > 1 and 'merged' or 'ok')
        local L = grp.layer or 'land'
        local st = S3('tool:' .. L); st.tool = st.tool + 1
        if v ~= 'ok' then st[v] = st[v] + 1 end
        out('g3tool', { { 'tag', tag }, { 'gid', grp.id or gi }, { 'token', grp.token or '?' }, { 'layer', L },
            { 'members', #(grp.ids or {}) }, { 'live', nlive }, { 'groups', nk }, { 'verdict', v } })
    end
    for k, g in pairs(live) do
        local tg = 0
        for _ in pairs(toolOf[k] or {}) do tg = tg + 1 end
        local pk = g.race .. '|' .. g.ref
        local p = pop[pk]
        local q = p and p.quantity or -1
        local debit = (p and S.g3pop0[pk]) and (S.g3pop0[pk] - q) or 0
        local v = (not groups) and 'notool' or (tg == 0 and 'untracked' or (tg > 1 and 'split' or 'match'))
        local st = S3(g.layer)
        st.live = st.live + 1
        if st[v] then st[v] = st[v] + 1 end
        if not p then st.nopop = st.nopop + 1 end
        if debit ~= 0 then st.debited = st.debited + 1 end
        out('g3', { { 'tag', tag }, { 'layer', g.layer }, { 'token', g.tok }, { 'ref6', g.ref }, { 'arrived', g.seen - (S.t0 or g.seen) },
            { 'live', g.n }, { 'drawn', g.o.drawn or 0 }, { 'placed', g.o.placed or 0 }, { 'released', g.o.released or 0 },
            { 'tool_groups', tg }, { 'pop_q', q }, { 'debit', debit }, { 'verdict', v } })
    end
    for L, st in pairs(sum) do
        out('g3sum', { { 'tag', tag }, { 'layer', L }, { 'live_groups', st.live }, { 'tool_groups', st.tool }, { 'match', st.match },
            { 'untracked', st.untracked }, { 'split', st.split }, { 'merged', st.merged }, { 'stale', st.stale },
            { 'nopop', st.nopop }, { 'debited', st.debited }, { 'tool', groups and 1 or 0 } })
    end

elseif cmd == 'adopt' then
    -- H3: a placed pack must be ONE tracked group to the tool (SW2's floor and sneak weighed one wolf: cx-eco spawn
    -- clears the roaming flag and the tool's discoverGroups only adopts flagged units). v7.1's `groups adopt <ids>`
    -- takes them by id whatever the flag; the receipt is read from the tool's own record, not from its reply.
    for i = 2, #args do
        local tok, ids, roam = args[i], {}, 0
        for id, t in pairs(S.spawned) do
            if t == tok then
                local u = df.unit.find(id)
                if u and not dfhack.units.isDead(u) then
                    ids[#ids + 1] = id
                    if u.flags2.roaming_wilderness_population_source then roam = roam + 1 end
                end
            end
        end
        table.sort(ids)
        local reply = 'none'
        if #ids > 0 then
            local sargs = {}
            for j, id in ipairs(ids) do sargs[j] = tostring(id) end
            local ok, o = pcall(dfhack.run_command_silent, 'seasonal-wildlife', 'groups', 'adopt', table.unpack(sargs))
            reply = ok and tostring(o or '') or ('error ' .. tostring(o))
            reply = reply:match('^[^\n]*') or reply
        end
        local groups, members = 0, 0
        local sw = tool()
        if sw and sw.loadGroups and #ids > 0 then
            local want = {}
            for _, id in ipairs(ids) do want[id] = true end
            local ok, g = pcall(sw.loadGroups)
            if ok and type(g) == 'table' then
                for _, grp in ipairs(g.groups or {}) do
                    local hit = 0
                    for _, id in ipairs(grp.ids or {}) do if want[id] then hit = hit + 1 end end
                    if hit > 0 then groups = groups + 1; members = members + hit end
                end
            end
        end
        out('adopt', { { 'token', tok }, { 'asked', #ids }, { 'groups', groups }, { 'members', members },
            { 'adopted', (#ids > 0 and groups == 1 and members == #ids) and 1 or 0 }, { 'roam', roam }, { 'reply', word(reply) } })
    end

elseif cmd == 'cfg' then
    local sw = tool()
    if not (sw and sw.loadConfig) then do return fail('seasonal-wildlife is not loadable') end end
    local c = sw.loadConfig()
    for i = 2, #args do
        local v = c
        for part in args[i]:gmatch('[^.]+') do if type(v) == 'table' then v = v[part] else v = nil end end
        out('cfg', { { 'path', args[i] }, { 'value', type(v) == 'table' and 'table' or word(v) } })
    end

elseif cmd == 'skill' then
    local tok, sk = args[2], df.job_skill[args[3] or 'SNEAK']
    if not sk then do return fail('no skill ' .. tostring(args[3])) end end
    local n, with, max = 0, 0, 0
    for _, u in ipairs(df.global.world.units.active) do
        if onmap(u) and race_of(u) == tok then
            n = n + 1
            local soul = u.status.current_soul
            if soul then
                for _, s in ipairs(soul.skills) do
                    if s.id == sk then with = with + 1; if s.rating > max then max = s.rating end end
                end
            end
        end
    end
    out('skill', { { 'token', tok }, { 'skill', args[3] or 'SNEAK' }, { 'units', n }, { 'with', with }, { 'max', max } })

elseif cmd == 'relcount' then
    local a, b = args[2], args[3]
    local cache, v, n, cells = df.global.world.enemy_status_cache, df.unit_reaction_type.PREDATOR_OR_PREY, 0, 0
    for ida, ta in pairs(S.spawned) do if ta == a then
        local ua = df.unit.find(ida)
        for idb, tb in pairs(S.spawned) do if tb == b then
            local ub = df.unit.find(idb)
            local sa, sb = ua and ua.enemy.enemy_status_slot or -1, ub and ub.enemy.enemy_status_slot or -1
            if sa >= 0 and sb >= 0 and not dfhack.units.isDead(ua) and not dfhack.units.isDead(ub) then
                n = n + 1
                if cache.rel_map[sa][sb].ur == v then cells = cells + 1 end
            end
        end end
    end end
    out('relcount', { { 'a', a }, { 'b', b }, { 'pairs', n }, { 'written', cells } })

elseif cmd == 'ecostate' then
    local sw = tool()
    if not (sw and sw.loadGroups) then do return fail('seasonal-wildlife is not loadable') end end
    local g = sw.loadGroups()
    local L = { land = 0, cavern = 0, water = 0 }
    for _, grp in ipairs(g.groups or {}) do local k = grp.layer or 'land'; L[k] = (L[k] or 0) + 1 end
    local e = g.ecology or {}
    local last = e.last or {}
    out('ecostate', { { 'groups', #(g.groups or {}) }, { 'land', L.land }, { 'cavern', L.cavern }, { 'water', L.water },
        { 'pairs', last.pairs or 0 }, { 'nudges_total', e.nudges or 0 }, { 'last_nudged', last.nudged or 0 },
        { 'last_slotted', last.slotted or 0 } })

else
    do return fail('usage: cx-eco spot|spawn|rel|watch|read|clear|flag|restore|lead|alerts|wipe|wipecheck|groups3|adopt|cfg|skill|relcount|ecostate ...') end
end
