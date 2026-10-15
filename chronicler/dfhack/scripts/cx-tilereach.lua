-- cx-tilereach: does a flier's number of source tiles change how often DF draws it? (user 15 Oct 2026, the tile-reach test)
--
-- Measured before: DF sends a WALKING surface wave only from the fort's own region tile(s) and a FLYING wave from any tile
-- the map's blocks name (up to 9); DF picks a wave's species by FREQUENCY and ignores stock. Open: whether a species with
-- entries on more tiles is picked more often. Setup: every surface Animal entry on the draw tiles is closed (extinct
-- flag) except two fliers at the same FREQUENCY and stock, one open on the site tile only, the other on every draw tile.
-- Each arrival is recorded with its source tile and vanished, so DF's surface gate reopens for the next wave.
--
--   cx-tilereach info                 the draw tiles (the union of every block's region_offset), the site tile(s), their
--                                     biomes, and the solitary all-season fliers that can live on the site tile and at least
--                                     one more (each with how many draw tiles its BIOME flags allow)
--   cx-tilereach setup A B ONE [F=50] [Q=200]
--                                     close every surface Animal entry on the draw tiles; open A and B at quantity Q and raw
--                                     FREQUENCY F; ONE (A or B) on the site tile(s) only, the other on every draw tile
--                                     (creating entries where it has none); vanish every wild surface animal on the map
--   cx-tilereach collect              one line per new wave (same race and source entry in one pass):
--                                     WAVE tick race n rx ry site|neighbour; every wild surface animal then vanishes
--   cx-tilereach state                the open surface Animal entries on the draw tiles, by race and tile
-- Run on a fort that is never saved afterwards (the closes and the created entries are not undone).
local args = { ... }
local cmd = args[1] or 'info'
local U = dfhack.units
_G.CXTR = _G.CXTR or { seen = {} }
local S = _G.CXTR

local function drawTiles()
    local wd = df.global.world.world_data
    local WW, WH = wd.world_width, wd.world_height
    local t = {}
    for _, block in ipairs(df.global.world.map.map_blocks) do
        local ro, bx, by = block.region_offset, block.region_pos.x, block.region_pos.y
        for o = 0, 8 do
            local off = ro[o]
            local rx = math.max(0, math.min(WW - 1, bx + (off % 3) - 1))
            local ry = math.max(0, math.min(WH - 1, by + (off // 3) - 1))
            t[rx * 65536 + ry] = true
        end
    end
    return t
end

local function siteTiles()
    local out = {}
    local site = df.world_site.find(df.global.plotinfo.site_id)
    if site then
        for rx = math.floor(site.global_min_x / 16), math.floor(site.global_max_x / 16) do
            for ry = math.floor(site.global_min_y / 16), math.floor(site.global_max_y / 16) do out[rx * 65536 + ry] = true end
        end
    end
    return out
end

local function tileName(k) return (k // 65536) .. ':' .. (k % 65536) end

local function surfaceAnimal(p)
    return p.type == df.world_population_type.Animal and p.population.feature_idx == -1 and p.population.cave_id == -1
end

local function raceIdx(tok)
    for i, cr in ipairs(df.global.world.raws.creatures.all) do if cr.creature_id == tok then return i end end
    qerror('unknown creature ' .. tostring(tok))
end

local function biomeOf(k)
    local ok, id = pcall(dfhack.maps.getBiomeType, k // 65536, k % 65536)
    return ok and id and df.biome_type[id] or nil
end

if cmd == 'info' then
    local draw, site = drawTiles(), siteTiles()
    local names, biomes = {}, {}
    for k in pairs(draw) do
        local b = biomeOf(k)
        names[#names + 1] = tileName(k) .. (site[k] and '*' or '') .. '=' .. tostring(b)
        if b then biomes[b] = true end
    end
    table.sort(names)
    print('DRAW ' .. table.concat(names, ' ') .. '   (* = site tile)')
    local cands = {}
    for _, cr in ipairs(df.global.world.raws.creatures.all) do
        local f = cr.flags
        if f.HAS_ANY_FLIER and not f.HAS_ANY_NOT_FLIER and f.LARGE_ROAMING and not f.VERMIN_SOIL and not f.VERMIN_GROUNDER
           and not f.VERMIN_EATER and not f.VERMIN_FISH and not f.VERMIN_ROTTER and not f.VERMIN_SOIL_COLONY and not f.UBIQUITOUS
           and not f.HAS_ANY_MEGABEAST and not f.HAS_ANY_SEMIMEGABEAST and not f.HAS_ANY_NIGHT_CREATURE and not f.HAS_ANY_FEATURE_BEAST
           and not f.HAS_ANY_DEMON and not f.HAS_ANY_TITAN and not f.HAS_ANY_INTELLIGENT_SPEAKS and not f.HAS_ANY_NOT_LIVING
           and cr.cluster_number[0] == 1 and cr.frequency > 0 then
            local fit, siteOk = 0, false
            for k in pairs(draw) do
                local bk = biomeOf(k)
                if bk and f['BIOME_' .. bk] then fit = fit + 1; if site[k] then siteOk = true end end
            end
            local all = siteOk and fit >= 2
            local seasons = true
            for _, ca in ipairs(cr.caste) do
                if ca.flags.NO_SPRING or ca.flags.NO_SUMMER or ca.flags.NO_AUTUMN or ca.flags.NO_WINTER then seasons = false end
            end
            if all and seasons then cands[#cands + 1] = cr.creature_id .. '(' .. fit .. ' tiles, f' .. cr.frequency .. ')' end
        end
    end
    print('FLIERS ' .. table.concat(cands, ' '))
    return
end

if cmd == 'setup' then
    local A, B, ONE = args[2], args[3], args[4]
    local F, Q = tonumber(args[5]) or 50, tonumber(args[6]) or 200
    if not (A and B and (ONE == A or ONE == B)) then qerror('usage: cx-tilereach setup A B ONE [F] [Q]') end
    local draw, site = drawTiles(), siteTiles()
    local ia, ib = raceIdx(A), raceIdx(B)
    local wantTiles = { [ia] = {}, [ib] = {} }
    local function lives(race, k)
        local bk = biomeOf(k)
        return bk ~= nil and df.creature_raw.find(race).flags['BIOME_' .. bk]
    end
    -- only tiles the species' raws allow, as DF stocks them: the many-tile species on every such draw tile, the one-tile
    -- species on exactly one site tile (the lowest-numbered it can live on; a straddling embark has several site tiles)
    local rOne, rMany = ONE == A and ia or ib, ONE == A and ib or ia
    local keys = {}
    for k in pairs(draw) do keys[#keys + 1] = k end
    table.sort(keys)
    for _, k in ipairs(keys) do
        if lives(rMany, k) then wantTiles[rMany][k] = true end
        if site[k] and lives(rOne, k) and next(wantTiles[rOne]) == nil then wantTiles[rOne][k] = true end
    end
    if next(wantTiles[rOne]) == nil then qerror(ONE .. ' cannot live on any site tile') end
    local all = df.global.world.populations.all
    local closed, opened, have = 0, 0, { [ia] = {}, [ib] = {} }
    for _, p in ipairs(all) do
        local k = p.population.region_x * 65536 + p.population.region_y
        if p.population.region_x >= 0 and draw[k] and surfaceAnimal(p) then
            if (p.race == ia or p.race == ib) and wantTiles[p.race][k] and not have[p.race][k] then
                p.flags.extinct = false; p.quantity = Q; have[p.race][k] = true; opened = opened + 1
            elseif not p.flags.extinct then p.flags.extinct = true; closed = closed + 1 end
        end
    end
    local created = 0
    for race, tiles in pairs(wantTiles) do
        for k in pairs(tiles) do
            if not have[race][k] then
                local rx, ry = k // 65536, k % 65536
                -- dfhack.maps.getRegionBiome, never region_map[x][y] (the engine's note: Lua hands back region_map[x] dereferenced)
                local entry = dfhack.maps.getRegionBiome(rx, ry)
                local rgn = entry and df.world_region.find(entry.region_id)
                if rgn then
                    rgn.population:insert('#', { new = df.world_population, type = df.world_population_type.Animal, race = race,
                                                 count_min = Q, count_max = Q })
                    all:insert('#', { new = df.local_population, type = df.world_population_type.Animal, race = race,
                                      quantity = Q, quantity_max = Q, breed = -1 })
                    local live = all[#all - 1]
                    live.population.region_x, live.population.region_y = rx, ry
                    live.population.feature_idx, live.population.cave_id, live.population.site_id = -1, -1, -1
                    live.population.population_idx = #rgn.population - 1
                    live.flags.extinct = false
                    have[race][k] = true; created = created + 1
                end
            end
        end
    end
    df.creature_raw.find(ia).frequency = F
    df.creature_raw.find(ib).frequency = F
    -- TR1 (15 Oct): the seen set outlived the reload between replicates; a reloaded save hands out the same unit ids, so later
    -- arrivals read as seen, were never vanished, and held DF's surface gate shut (5 waves in 90,000 ticks, then none)
    S.seen = {}
    local gone = 0
    for _, u in ipairs(df.global.world.units.active) do
        if not U.isDead(u) and (U.isWildlife(u) or (U.isAnimal(u) and not U.isTame(u) and not U.isDomesticated(u) and not U.isFortControlled(u)))
           and u.animal.population.cave_id == -1 then
            u.animal.vanish_countdown = 1; S.seen[u.id] = true; gone = gone + 1
        end
    end
    local na, nb = 0, 0
    for _ in pairs(have[ia]) do na = na + 1 end
    for _ in pairs(have[ib]) do nb = nb + 1 end
    print(('SETUP %s on %d tile(s), %s on %d tile(s) (ONE=%s), FREQUENCY %d, quantity %d; %d opened, %d created, %d other surface entries closed; %d wild surface animal(s) vanished')
        :format(A, na, B, nb, ONE, F, Q, opened, created, closed, gone))
    return
end

if cmd == 'collect' then
    local site = siteTiles()
    local t = df.global.cur_year * 403200 + df.global.cur_year_tick
    local waves, order = {}, {}
    for _, u in ipairs(df.global.world.units.active) do
        if not U.isDead(u) and u.animal.population.cave_id == -1
           and (U.isWildlife(u) or (U.isAnimal(u) and not U.isTame(u) and not U.isDomesticated(u) and not U.isFortControlled(u))) then
            u.animal.vanish_countdown = 1   -- every wild surface animal goes, recorded or not, so nothing holds the gate
        end
        if not S.seen[u.id] and not U.isDead(u) and u.animal.population.cave_id == -1
           and (U.isWildlife(u) or (U.isAnimal(u) and not U.isTame(u) and not U.isDomesticated(u) and not U.isFortControlled(u))) then
            S.seen[u.id] = true
            local pr = u.animal.population
            local key = u.race .. ':' .. pr.region_x .. ':' .. pr.region_y .. ':' .. pr.population_idx
            if not waves[key] then waves[key] = { race = u.race, n = 0, rx = pr.region_x, ry = pr.region_y }; order[#order + 1] = key end
            waves[key].n = waves[key].n + 1
            u.animal.vanish_countdown = 1
        end
    end
    for _, key in ipairs(order) do
        local w = waves[key]
        local k = w.rx * 65536 + w.ry
        print(('WAVE %d %s %d %d %d %s'):format(t, df.creature_raw.find(w.race).creature_id, w.n, w.rx, w.ry,
            w.rx < 0 and 'none' or (site[k] and 'site' or 'neighbour')))
    end
    print(('COLLECT %d wave(s) at %d'):format(#order, t))
    return
end

if cmd == 'state' then
    local draw = drawTiles()
    local by = {}
    for _, p in ipairs(df.global.world.populations.all) do
        local k = p.population.region_x * 65536 + p.population.region_y
        if p.population.region_x >= 0 and draw[k] and surfaceAnimal(p) and not p.flags.extinct then
            local r = df.creature_raw.find(p.race).creature_id
            by[r] = by[r] or {}
            table.insert(by[r], tileName(k) .. '=' .. p.quantity)
        end
    end
    for r, l in pairs(by) do print(('OPEN %s %s'):format(r, table.concat(l, ' '))) end
    return
end

qerror('usage: cx-tilereach info | setup A B ONE [F] [Q] | collect | state')
