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
--   cx-probe pops [all]            one row per Animal entry on the site's tiles (the draw pool); `all` = every entry
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

local function layer_of(r)
    if r.feature_idx >= 0 then return 'feature' end
    if r.cave_id >= 0 then return 'cavern' end
    return 'surface'
end

local function b(v) return v and 1 or 0 end

local function row(...) print(table.concat({...}, '\t')) end

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
        'flag_src', 'flag_nf', 'dead', 'inactive', 'civ', 'tame', 'wild')
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
                b(u.flags1.inactive), u.civ_id, b(u.flags1.tame), b(wild))
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
        local on_site = r.region_x >= x0 and r.region_x <= x1 and r.region_y >= y0 and r.region_y <= y1
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
    qerror('usage: cx-probe clock|units|pops [all]|tool|provenance|release [surface|all|id..]|setq <idx> <q> [extinct]|countdown <id> <v>|kill <id..>|combat [since-report-id]|roster')
end
