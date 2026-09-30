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
            u.flags2.roaming_wilderness_population_source = false
            u.flags2.roaming_wilderness_population_source_not_a_map_feature = false
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
        { 'borrowed_ref', borrowed and 1 or 0 }, { 'ids', table.concat(ids, ',') } })

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
    eventful.enableEvent(eventful.eventType.UNIT_ATTACK, 1)
    eventful.onUnitAttack.cx_eco = function(att, def)
        if not _G.CX_ECO.watch then return end
        local ua, ud = df.unit.find(att), df.unit.find(def)
        local k = (ua and race_of(ua) or '?') .. '>' .. (ud and race_of(ud) or '?')
        _G.CX_ECO.attacks[k] = (_G.CX_ECO.attacks[k] or 0) + 1
    end
    out('watch', { { 'incidents0', S.inc0 }, { 't0', S.t0 } })

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

else
    do return fail('usage: cx-eco spot|spawn|rel|watch|read|clear|flag|restore|lead|alerts ...') end
end
