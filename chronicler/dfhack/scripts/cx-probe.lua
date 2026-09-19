-- cx-probe.lua -- instrument reads and manipulation primitives for the
-- wilderpop experiment harness (scripts/cx-experiment.py).
--
-- Every read prints ONE TSV table with a header row, so the runner can turn
-- it into long-format records (run, arm, rep, tick, subject, metric, value)
-- without parsing prose. Every write prints a one-line receipt.
--
--   cx-probe clock                 year, tick, season, paused, fps caps and achieved, unit and popup counts
--   cx-probe units                 one row per wild unit in world.units.all (dead and departed included,
--                                  flagged), with its six-field population reference and countdowns
--   cx-probe pops [all]            one row per Animal entry on the site's tiles and their one-tile ring (the draw
--                                  pool incl. block-biome neighbours); `all` = every entry
--   cx-probe tool                  seasonal-wildlife's persisted config and whether its tick is scheduled
--   cx-probe provenance            DF/DFHack versions, world, site, region tiles, seed if readable
--   cx-probe release [surface|all|<id> ...]
--                                  clear BOTH roaming flags on wild units: surface only (default), every
--                                  layer, or the listed unit ids. Prints how many were cleared.
--   cx-probe setq <pop-idx> <quantity> [extinct 0|1]
--                                  write quantity (and optionally the extinct flag) on one pool entry
--   cx-probe countdown <unit-id> <value>
--                                  write leave_countdown on one unit
--   cx-probe kill <unit-id> ...      blood_count = 0, no other accounting (dies on DF's own path)
--   cx-probe rel                     DF's pairwise reaction cache (world.enemy_status_cache.rel_map) between
--                                  every wild LARGE_PREDATOR unit and every other wild unit, tallied by species
--   cx-probe edge                    plotinfo.map_edge surface entry tiles with tiletype and water depth
--   cx-probe relrow                  one row per wild alive unit: id, species, slot, and how many PREDATOR_OR_PREY
--                                  entries its rel_map row and column hold against ANY slot (stale-slot detector)
--   cx-probe lever <opposed|crazed|relmap|agitated> [id ...]
--                                  hostility lever on the listed units, or on every wild LARGE_PREDATOR unit
--   cx-probe spawn <pop-idx> <n> [x y z]
--                                  place n units of the pool entry via modtools/create-unit (locationType Any) at
--                                  x,y,z or at the first watery map_edge surface tile, write the entry's six-field
--                                  population reference onto each unit, debit the entry, countdown 25000, not held
--   cx-probe gather [id ...]         teleport every wild LARGE_PREDATOR unit (or the listed ids) to within 3 tiles of
--                                  the first wild non-predator SURFACE unit, so predator and prey actually meet
--   cx-probe spawn2 <CREATURE_ID> <n> <x> <y> <z> [pop-idx]
--                                  53.x placement through DF's own arena creature UI (the route gui/sandbox
--                                  uses): world.arena + game.main_interface.arena_unit, ARENA_CREATE_CREATURE,
--                                  then SELECT. Optional pop-idx writes that entry's population reference and
--                                  debits it so the unit counts as wildlife. EXPERIMENTAL: keys are guessed.
--   cx-probe combat [since-id]       every wild unit's combat reports with id > since (unit, species, id, text)
--
-- Wild = dfhack.units.isWildlife: population_idx >= 0 and not merchant / forest / fort-controlled.
-- It does NOT key on the roaming flag, so a released resident stays in the table (checked in
-- DFHack Units.cpp, 2026-09-16).
--
-- ⚠️ This runs with the core suspended (RPC). It never waits; the runner sequences steps.

local args = {...}
local cmd = args[1]

local function tok(race)
    local cr = df.creature_raw.find(race)
    return cr and cr.creature_id or ('race' .. tostring(race))
end

local function caste_tok(race, caste)
    local cr = df.creature_raw.find(race)
    if not cr then return '?' end
    local c = cr.caste[caste]
    return c and c.caste_id or '?'
end

local function ref6(r)
    return ('%d,%d,%d,%d,%d,%d'):format(r.region_x, r.region_y, r.feature_idx, r.cave_id, r.site_id, r.population_idx)
end

-- A cave_id is not a cavern. `world_underground_region.layer_depth` reads 0-2 for the three
-- cavern layers, 3 for the MAGMA SEA and 4 for the UNDERWORLD. Until 2026-09-18 this function
-- returned 'cavern' for all five, so every `layer=cavern` row this probe has ever written --
-- units.tsv, the arrival and departure events, pops.tsv -- counted magma crabs and demons as
-- cavern wildlife. That is addendum 51's inflation: it was fixed inside seasonal-wildlife
-- (WILD.caveDepth) and NOT here, so the tool's own counts were right while the harness's data
-- stayed wrong by five to eight units on CTRL. Any threshold or tally calibrated from a
-- `layer=cavern` figure written before this date is too high by that much.
-- Depth per cave never changes while a world is loaded, so it is cached.
local depth_cache = {}
local function cave_depth(cave_id)
    local d = depth_cache[cave_id]
    if d ~= nil then return d end
    local ur = df.global.world.world_data.underground_regions
    local reg = (cave_id >= 0 and cave_id < #ur) and ur[cave_id] or nil
    d = reg and reg.layer_depth or -1
    depth_cache[cave_id] = d
    return d
end

local function layer_of(r)
    if r.feature_idx >= 0 then return 'feature' end
    if r.cave_id >= 0 then
        -- an unknown cave reads as 'cavern', which is the pre-fix behaviour and the safe way
        -- to be wrong: it never hides something that is genuinely in a cavern.
        return cave_depth(r.cave_id) >= 3 and 'deep' or 'cavern'
    end
    return 'surface'
end

local function b(v) return v and 1 or 0 end

local function row(...) print(table.concat({...}, '\t')) end

local function is_pred(u)  -- SURFACE large predators only: cavern troglodytes and cave crocodiles carry the flag too
    local cr = df.creature_raw.find(u.race)
    local c = cr and cr.caste[u.caste]
    return (c and c.flags.LARGE_PREDATOR and layer_of(u.animal.population) == 'surface') or false
end
local function wild_alive()
    local t = {}
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isWildlife(u) and not dfhack.units.isDead(u) then t[#t+1] = u end
    end
    return t
end

-- ------------------------------------------------------------------ clock --
if cmd == 'clock' then
    local e = df.global.enabler
    row('year', 'tick', 'season', 'paused', 'fps_cap', 'fps_achieved', 'gfps_cap', 'units_active', 'popups', 'map')
    row(df.global.cur_year, df.global.cur_year_tick, df.global.cur_season, b(df.global.pause_state),
        e.fps, e.calculated_fps, e.gfps, #df.global.world.units.active, #df.global.world.status.popups,
        b(dfhack.isMapLoaded()))

-- ------------------------------------------------------------------ units --
elseif cmd == 'units' then
    row('id', 'species', 'caste', 'x', 'y', 'z', 'ref6', 'layer', 'countdown', 'vanish',
        'flag_src', 'flag_nf', 'dead', 'inactive', 'civ', 'tame', 'wild', 'mother')
    for _, u in ipairs(df.global.world.units.all) do
        local wild = dfhack.units.isWildlife(u)
        -- keep everything with a population reference; the runner filters on `wild`
        if wild or u.animal.population.population_idx >= 0 then
            local r = u.animal.population
            row(u.id, tok(u.race), caste_tok(u.race, u.caste), u.pos.x, u.pos.y, u.pos.z, ref6(r), layer_of(r),
                u.animal.leave_countdown, u.animal.vanish_countdown,
                b(u.flags2.roaming_wilderness_population_source),
                b(u.flags2.roaming_wilderness_population_source_not_a_map_feature),
                b(dfhack.units.isDead(u)),
                b(u.flags1.inactive), u.civ_id, b(u.flags1.tame), b(wild),
                u.relationship_ids[df.unit_relationship_type.Mother])
        end
    end

-- ------------------------------------------------------------------- pops --
elseif cmd == 'pops' then
    -- ⚠️ world.populations.all holds entries for MANY region tiles, not just the
    -- site's: 8,867 on CTRL (3,299 surface) against 24 animal entries on the
    -- site's own tile. DF draws only from the site's tiles (G4/G5, rev 4), so the
    -- default is the site's tiles and Animal entries; `pops all` prints everything.
    local all = args[2] == 'all'
    local site = df.world_site.find(df.global.plotinfo.site_id)
    local x0, x1, y0, y1 = -1, -1, -1, -1
    if site then
        x0, x1 = math.floor(site.global_min_x / 16), math.floor(site.global_max_x / 16)
        y0, y1 = math.floor(site.global_min_y / 16), math.floor(site.global_max_y / 16)
    end
    row('idx', 'species', 'type', 'layer', 'ref6', 'quantity', 'quantity_max',
        'discovered', 'extinct', 'already_removed', 'need_offload')
    for i, p in ipairs(df.global.world.populations.all) do
        local r = p.population
        -- one-tile ring, not just the site tiles: E9a/E2 showed the block-biome neighbour
        -- (28,19 on CTRL) is a draw source too, and F15's big raven entry lives there
        local on_site = r.region_x >= x0 - 1 and r.region_x <= x1 + 1 and r.region_y >= y0 - 1 and r.region_y <= y1 + 1
        if all or (on_site and p.type == df.world_population_type.Animal) then
            local sp = p.type == df.world_population_type.Animal and tok(p.race) or (df.world_population_type[p.type] .. ':' .. tostring(p.race))
            row(i, sp, df.world_population_type[p.type], layer_of(r), ref6(r),
                p.quantity, p.quantity_max,
                b(p.flags.discovered), b(p.flags.extinct), b(p.flags.already_removed), b(p.flags.need_offload))
        end
    end

-- ------------------------------------------------------------------- tool --
elseif cmd == 'tool' then
    local cfg = dfhack.persistent.getSiteData('seasonal-wildlife/config', nil) or {}
    local groups = cfg.groups or {}
    local ok, ru = pcall(require, 'repeat-util')
    local sched = ok and ru.isScheduled and ru.isScheduled('seasonal-wildlife') or false
    row('enabled', 'groups_enabled', 'scheduled', 'initialized')
    row(b(cfg.enabled), b(groups.enabled), b(sched), b(cfg.initialized))

-- ------------------------------------------------------------- provenance --
elseif cmd == 'provenance' then
    local site = df.world_site.find(df.global.plotinfo.site_id)
    local seed = '?'
    pcall(function() seed = tostring(df.global.world.worldgen.worldgen_parms.seed) end)
    local tiles = '?'
    if site then
        tiles = ('%d..%d,%d..%d'):format(math.floor(site.global_min_x / 16), math.floor(site.global_max_x / 16),
                                          math.floor(site.global_min_y / 16), math.floor(site.global_max_y / 16))
    end
    row('df_version', 'dfhack_version', 'os', 'world', 'site_id', 'site_tiles', 'seed', 'save_dir')
    row(dfhack.getDFVersion(), dfhack.getDFHackVersion(), dfhack.getOSType(),
        dfhack.translation.translateName(df.global.world.world_data.name, true),
        df.global.plotinfo.site_id, tiles, seed, tostring(df.global.world.cur_savegame.save_dir))

-- ---------------------------------------------------------------- release --
elseif cmd == 'release' then
    local mode = args[2] or 'surface'
    local ids = {}
    if mode ~= 'surface' and mode ~= 'all' then
        for i = 2, #args do ids[tonumber(args[i])] = true end
    end
    local n = 0
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isWildlife(u) and not dfhack.units.isDead(u) then
            local want
            if next(ids) then want = ids[u.id]
            elseif mode == 'all' then want = true
            else want = layer_of(u.animal.population) == 'surface' end
            if want and (u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature) then
                u.flags2.roaming_wilderness_population_source = false
                u.flags2.roaming_wilderness_population_source_not_a_map_feature = false
                n = n + 1
            end
        end
    end
    print(('released %d unit(s) [%s]'):format(n, mode))

-- ------------------------------------------------------------------- setq --
elseif cmd == 'setq' then
    local idx, q = tonumber(args[2]), tonumber(args[3])
    local p = df.global.world.populations.all[idx]
    if not p then qerror('no pool entry ' .. tostring(idx)) end
    local before = p.quantity
    p.quantity = q
    if args[4] ~= nil then p.flags.extinct = (tonumber(args[4]) == 1) end
    print(('setq %d %s: quantity %d -> %d extinct=%d'):format(idx, tok(p.race), before, p.quantity, b(p.flags.extinct)))

-- -------------------------------------------------------------- countdown --
elseif cmd == 'countdown' then
    local id, v = tonumber(args[2]), tonumber(args[3])
    local u = df.unit.find(id)
    if not u then qerror('no unit ' .. tostring(id)) end
    local before = u.animal.leave_countdown
    u.animal.leave_countdown = v
    print(('countdown %d %s: %d -> %d'):format(id, tok(u.race), before, u.animal.leave_countdown))

-- -------------------------------------------------------------------- rel --
elseif cmd == 'rel' then
    local cache = df.global.world.enemy_status_cache
    local tally, order = {}, {}
    local ws = wild_alive()
    for _, a in ipairs(ws) do
        if is_pred(a) then
            for _, bu in ipairs(ws) do
                if bu.id ~= a.id then
                    local sa, sb = a.enemy.enemy_status_slot, bu.enemy.enemy_status_slot
                    local ab = (sa >= 0 and sb >= 0) and df.unit_reaction_type[cache.rel_map[sa][sb].ur] or 'NOSLOT'
                    local ba = (sa >= 0 and sb >= 0) and df.unit_reaction_type[cache.rel_map[sb][sa].ur] or 'NOSLOT'
                    local k = table.concat({tok(a.race), tok(bu.race), tostring(ab), tostring(ba)}, '\t')
                    if not tally[k] then tally[k] = 0; order[#order+1] = k end
                    tally[k] = tally[k] + 1
                end
            end
        end
    end
    row('pred', 'other', 'pred_to_other', 'other_to_pred', 'pairs')
    for _, k in ipairs(order) do row(k, tally[k]) end

-- ----------------------------------------------------------------- relrow --
elseif cmd == 'relrow' then
    local cache = df.global.world.enemy_status_cache
    local v = df.unit_reaction_type.PREDATOR_OR_PREY
    local nslots = #cache.rel_map
    row('id', 'species', 'pred', 'slot', 'row_pp', 'col_pp', 'arrived_tick')
    for _, u in ipairs(wild_alive()) do
        local s = u.enemy.enemy_status_slot
        local rp, cp = 0, 0
        if s >= 0 and s < nslots then
            for j = 0, nslots - 1 do
                if cache.rel_map[s][j].ur == v then rp = rp + 1 end
                if cache.rel_map[j][s].ur == v then cp = cp + 1 end
            end
        end
        row(u.id, tok(u.race), b(is_pred(u)), s, rp, cp, u.animal and u.animal.leave_countdown or -1)
    end

-- ------------------------------------------------------------------- edge --
elseif cmd == 'edge' then
    local me = df.global.plotinfo.map_edge
    row('x', 'y', 'z', 'tiletype', 'water', 'liquid')
    for i = 0, #me.surface_x - 1 do
        local x, y, z = me.surface_x[i], me.surface_y[i], me.surface_z[i]
        local tt = dfhack.maps.getTileType(x, y, z)
        local d = dfhack.maps.getTileFlags(x, y, z)
        row(x, y, z, tt and df.tiletype[tt] or '?', d and d.flow_size or '?',
            d and (d.liquid_type and 'magma' or 'water') or '?')
    end

-- ------------------------------------------------------------------ lever --
elseif cmd == 'lever' then
    local which = args[2]
    local ids = {}
    for i = 3, #args do ids[tonumber(args[i])] = true end
    local ws = wild_alive()
    local preds, others = {}, {}
    for _, u in ipairs(ws) do
        if (next(ids) and ids[u.id]) or (not next(ids) and is_pred(u)) then preds[#preds+1] = u
        else others[#others+1] = u end
    end
    local n = 0
    if which == 'opposed' then
        for _, u in ipairs(preds) do u.uwss_add_caste_flag.OPPOSED_TO_LIFE = true; n = n + 1 end
    elseif which == 'crazed' then
        for _, u in ipairs(preds) do u.uwss_add_caste_flag.CRAZED = true; n = n + 1 end
    elseif which == 'agitated' then
        for _, u in ipairs(preds) do u.flags4.agitated_wilderness_creature = true; n = n + 1 end
    elseif which == 'relmap' then
        local cache = df.global.world.enemy_status_cache
        local v = df.unit_reaction_type.PREDATOR_OR_PREY
        local noslot = 0
        for _, a in ipairs(preds) do
            for _, bu in ipairs(others) do
                local sa, sb = a.enemy.enemy_status_slot, bu.enemy.enemy_status_slot
                if sa >= 0 and sb >= 0 then
                    cache.rel_map[sa][sb].ur = v; cache.rel_map[sb][sa].ur = v; n = n + 1
                else noslot = noslot + 1 end
            end
        end
        print(('lever relmap: PREDATOR_OR_PREY written on %d pair(s), %d pair(s) without a slot, %d predator(s) x %d other(s)'):format(n, noslot, #preds, #others))
        return
    else
        qerror('lever: opposed|crazed|relmap|agitated')
    end
    print(('lever %s: set on %d unit(s) of %d predator(s) (%d other wild)'):format(which, n, #preds, #others))

-- ------------------------------------------------------------------ spawn --
elseif cmd == 'spawn' then
    local idx, n = tonumber(args[2]), tonumber(args[3]) or 1
    local p = df.global.world.populations.all[idx]
    if not p then qerror('no pool entry ' .. tostring(idx)) end
    -- ⚠️ BLOCKED UPSTREAM on DFHack 53.16-r1.1: modtools/create-unit.lua:164 reads
    -- df.global.world.arena_spawn, a field this build's df-structures does not define, so
    -- EVERY create-unit call dies there -- nothing to do with the creature or the tile.
    -- Checked 17 September 2026. E14-OCEAN2 made this route unnecessary anyway: aquatic
    -- entries produce ordinary waves when the map has water at its edge.
    if not pcall(function() return df.global.world.arena_spawn end) then
        qerror('spawn: modtools/create-unit is broken on this DFHack build (world.arena_spawn '
            .. 'is missing from df-structures but create-unit.lua:164 reads it). No placement route.')
    end
    local pos
    if args[4] then
        pos = {x = tonumber(args[4]), y = tonumber(args[5]), z = tonumber(args[6])}
    else
        -- map_edge.surface_* lists LAND entry tiles only (measured on LAKE: 127 tiles, all
        -- land), so it is useless for water. Scan the map itself for a submerged tile.
        local m = df.global.world.map
        for x = 0, m.x_count - 1, 4 do
            for y = 0, m.y_count - 1, 4 do
                for z = m.z_count - 1, 0, -1 do
                    local d = dfhack.maps.getTileFlags(x, y, z)
                    if d and d.flow_size >= 4 and not d.liquid_type then pos = {x = x, y = y, z = z}; break end
                    local tt = dfhack.maps.getTileType(x, y, z)
                    if tt then
                        local bs = df.tiletype_shape.attrs[df.tiletype.attrs[tt].shape].basic_shape
                        if bs ~= df.tiletype_shape_basic.Open and bs ~= df.tiletype_shape_basic.None then break end
                    end
                end
                if pos then break end
            end
            if pos then break end
        end
        if not pos then qerror('spawn: no water on this map; give x y z') end
    end
    local cu = reqscript('modtools/create-unit')
    local made = cu.createUnit(tok(p.race), nil, pos, {offset_x = 0, offset_y = 0, offset_z = 0}, 'Any',
        nil, false, nil, nil, nil, nil, nil, n)
    local r = p.population
    local ids = {}
    for _, u in ipairs(made or {}) do
        local ap = u.animal.population
        ap.region_x, ap.region_y = r.region_x, r.region_y
        ap.feature_idx, ap.cave_id, ap.site_id, ap.population_idx = r.feature_idx, r.cave_id, r.site_id, r.population_idx
        u.animal.leave_countdown = 25000
        u.flags2.roaming_wilderness_population_source = false
        u.flags2.roaming_wilderness_population_source_not_a_map_feature = false
        ids[#ids+1] = ('%d:%s'):format(u.id, dfhack.units.isWildlife(u) and 'wild' or 'NOTWILD')
    end
    p.quantity = math.max(0, p.quantity - #ids)
    print(('spawn idx %d %s x%d at %d,%d,%d -> %s; entry quantity now %d'):format(
        idx, tok(p.race), #ids, pos.x, pos.y, pos.z, table.concat(ids, ' '), p.quantity))

-- ----------------------------------------------------------------- gather --
elseif cmd == 'gather' then
    local ids = {}
    for i = 2, #args do ids[tonumber(args[i])] = true end
    local ws = wild_alive()
    local target
    for _, u in ipairs(ws) do
        if not is_pred(u) and layer_of(u.animal.population) == 'surface' and not u.flags1.inactive then target = u; break end
    end
    if not target then qerror('gather: no wild non-predator surface unit to gather at') end
    local n, moved = 0, {}
    for _, u in ipairs(ws) do
        if (next(ids) and ids[u.id]) or (not next(ids) and is_pred(u)) then
            local placed = false
            for r = 2, 6 do
                for dx = -r, r do for dy = -r, r do
                    if not placed and (math.abs(dx) == r or math.abs(dy) == r) then
                        local pos = xyz2pos(target.pos.x + dx, target.pos.y + dy, target.pos.z)
                        if dfhack.maps.isValidTilePos(pos) then
                            local tt = dfhack.maps.getTileType(pos)
                            local occ = dfhack.maps.getTileBlock(pos).occupancy[pos.x % 16][pos.y % 16]
                            if tt and df.tiletype_shape.attrs[df.tiletype.attrs[tt].shape].walkable and not occ.unit then
                                if dfhack.units.teleport(u, pos) then placed = true; n = n + 1; moved[#moved+1] = tostring(u.id) end
                            end
                        end
                    end
                end end
                if placed then break end
            end
        end
    end
    print(('gather: moved %d predator(s) [%s] to within 6 tiles of unit %d %s at %d,%d,%d'):format(
        n, table.concat(moved, ' '), target.id, tok(target.race), target.pos.x, target.pos.y, target.pos.z))

-- ----------------------------------------------------------------- spawn2 --
elseif cmd == 'spawn2' then
    local cid, n = args[2], tonumber(args[3]) or 1
    local pos = {x = tonumber(args[4]), y = tonumber(args[5]), z = tonumber(args[6])}
    local pidx = tonumber(args[7])
    local race
    for i, cr in ipairs(df.global.world.raws.creatures.all) do if cr.creature_id == cid then race = i break end end
    if not race then qerror('spawn2: no creature ' .. tostring(cid)) end
    local gui = require('gui')
    local arena, au = df.global.world.arena, df.global.game.main_interface.arena_unit
    -- one-entry lists, as sandbox's init_arena builds them but for our race only
    arena.race:resize(0); arena.caste:resize(0); arena.creature_cnt:resize(0)
    local cr = df.creature_raw.find(race)
    arena.creature_cnt:insert('#', 0)
    for c = 0, #cr.caste - 1 do arena.race:insert('#', race); arena.caste:insert('#', c) end
    arena.last_race, arena.last_caste = -1, -1
    arena.tame = false; arena.interaction = -1
    au.race = 0; au.caste = 0; au.filter = ''; au.editing_filter = false
    au.races_filtered:resize(0); au.races_all:resize(0); au.castes_filtered:resize(0); au.castes_all:resize(0)
    local first = df.global.unit_next_id
    local vs = dfhack.gui.getCurViewscreen(true)
    local old_gt, old_cursor = df.global.gametype, copyall(df.global.cursor)
    df.global.cursor.x, df.global.cursor.y, df.global.cursor.z = pos.x, pos.y, pos.z
    df.global.gametype = df.game_type.DWARF_ARENA
    local ok, err = pcall(function()
        for i = 1, n do
            au.open = false
            gui.simulateInput(vs, 'ARENA_CREATE_CREATURE')
            au.race = 0; au.caste = 0
            gui.simulateInput(vs, 'SELECT')
        end
    end)
    df.global.gametype = old_gt
    df.global.cursor:assign(old_cursor)
    au.open = false
    local made = {}
    for id = first, df.global.unit_next_id - 1 do local u = df.unit.find(id); if u then made[#made+1] = u end end
    local p = pidx and df.global.world.populations.all[pidx]
    local ids = {}
    for _, u in ipairs(made) do
        if p then
            local r, ap = p.population, u.animal.population
            ap.region_x, ap.region_y = r.region_x, r.region_y
            ap.feature_idx, ap.cave_id, ap.site_id, ap.population_idx = r.feature_idx, r.cave_id, r.site_id, r.population_idx
        end
        u.animal.leave_countdown = 25000
        u.flags2.roaming_wilderness_population_source = false
        u.flags2.roaming_wilderness_population_source_not_a_map_feature = false
        ids[#ids+1] = ('%d:%s@%d,%d,%d'):format(u.id, dfhack.units.isWildlife(u) and 'wild' or 'NOTWILD', u.pos.x, u.pos.y, u.pos.z)
    end
    if p then p.quantity = math.max(0, p.quantity - #made) end
    print(('spawn2 %s x%d requested at %d,%d,%d -> made %d [%s]%s'):format(cid, n, pos.x, pos.y, pos.z, #made,
        table.concat(ids, ' '), ok and '' or (' ERROR ' .. tostring(err))))

-- ------------------------------------------------------------------- kill --
-- Kill with no accounting of our own: blood to zero, the way DFHack's
-- exterminate destroyUnit does, but WITHOUT its vanish_countdown failsafe, so
-- the unit dies on DF's own death path rather than being removed by the timer.
elseif cmd == 'kill' then
    local n = 0
    for i = 2, #args do
        local u = df.unit.find(tonumber(args[i]))
        if not u then qerror('no unit ' .. tostring(args[i])) end
        u.body.blood_count = 0
        n = n + 1
    end
    print(('kill: blood_count=0 on %d unit(s)'):format(n))

-- ----------------------------------------------------------------- combat --
-- Every wild unit's own combat log (unit.reports.log.Combat holds report ids),
-- for reports with id > since. One row per (unit, report).
elseif cmd == 'combat' then
    local since = tonumber(args[2]) or -1
    row('unit', 'species', 'report', 'year', 'time', 'text')
    for _, u in ipairs(df.global.world.units.all) do
        if u.animal.population.population_idx >= 0 then
            local log = u.reports.log[df.unit_report_type.Combat]
            for _, rid in ipairs(log) do
                if rid > since then
                    local r = df.report.find(rid)
                    if r then
                        row(u.id, tok(u.race), rid, r.year, r.time, (r.text:gsub('[\t\r\n]', ' ')))
                    end
                end
            end
        end
    end

-- ----------------------------------------------------------------- roster --
-- seasonal-wildlife's persisted roster: one row per assigned token with its seasons
-- (0 spring, 1 summer, 2 autumn, 3 winter) and whether it is allowed.
elseif cmd == 'roster' then
    local cfg = dfhack.persistent.getSiteData('seasonal-wildlife/config', nil) or {}
    row('token', 'seasons', 'allowed')
    for tokn, arr in pairs(cfg.assign or {}) do
        if type(arr) == 'table' and #arr > 0 then
            local ss = {}
            for _, v in ipairs(arr) do ss[#ss+1] = tostring(v) end
            table.sort(ss)
            local allowed = cfg.allow and cfg.allow[tokn]
            row(tokn, table.concat(ss, ','), allowed == nil and '?' or b(allowed))
        end
    end

else
    qerror('usage: cx-probe clock|units|pops [all]|tool|provenance|release [surface|all|id..]|setq <idx> <q> [extinct]|countdown <id> <v>|kill <id..>|combat [since-report-id]|roster|rel|edge|lever <opposed|crazed|relmap|agitated> [id..]|spawn <idx> <n> [x y z]|spawn2 <CREATURE_ID> <n> <x> <y> <z> [pop-idx]|gather [id..]')
end
