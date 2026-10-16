-- cx-cavearrive: can DF send a cavern wave of this species at all? (user 15 Oct 2026, the never-arrive test)
--
-- Over 16 full-year forts, 15 cast cavern species never arrived: every cave animal person, the gremlin, and the plain prey
-- (large and giant rat, giant mole, naked mole dog, drunian). The animal people had one cave entry each (the tool's created
-- one, at FREQUENCY 1); the species that arrived had 10-20 (DF's own stock on many tiles). Two readings: odds (one entry
-- against many) or a bar (DF never sends the species). Setup puts a SUBJECT and a CONTROL that arrives on the same footing:
-- in every cave of one cavern depth, on every draw tile that has a cave Animal entry, each gets exactly one open entry
-- (created from that tile's entry where it has none) at the same quantity and raw FREQUENCY; every other Animal entry there
-- is closed (extinct flag). Each tile x cave keeps two open species, so DF's zero-frequency stall cannot trigger. Every wild
-- cavern animal is vanished at setup and on each collect, so DF's cavern gate stays clear for the next wave. Equal footing
-- gives the subject about half the waves; a bar gives it none.
--
--   cx-cavearrive info                       per cavern depth: caves, draw-tile x cave pairs with Animal entries, open species
--   cx-cavearrive setup DEPTH SUBJ CTRL [F=50] [Q=100]
--                                            DEPTH 1-3; as above; prints SETUP ... (and a WARN if a raw UNDERGROUND_DEPTH
--                                            excludes the depth)
--   cx-cavearrive collect                    WAVE tick race n rx ry depth per new wave (race + source entry in one pass), then
--                                            every wild cavern animal vanishes; COLLECT n
--   cx-cavearrive state DEPTH                the open cave Animal entries at that depth on the draw tiles, by race
-- Run on a fort that is never saved afterwards (the closes and the created entries are not undone).
local args = { ... }
local cmd = args[1] or 'info'
local U = dfhack.units
_G.CXCA = _G.CXCA or { seen = {} }
local S = _G.CXCA

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

local depthCache = {}
local function caveDepth(cave_id)   -- world_underground_region.layer_depth: 0-2 the caverns, 3+ magma sea and below
    if cave_id == nil or cave_id < 0 then return nil end
    if depthCache[cave_id] == nil then
        local r = df.world_underground_region.find(cave_id)
        depthCache[cave_id] = r and r.layer_depth or false
    end
    return depthCache[cave_id] or nil
end

local function caveAnimal(p)
    return p.type == df.world_population_type.Animal and p.population.cave_id >= 0 and p.population.region_x >= 0
end

local function raceIdx(tok)   -- an underscore also stands for a space ('RODENT_MAN' = 'RODENT MAN': the rig's cmd splits words)
    local alt = tostring(tok):gsub('_', ' ')
    for i, cr in ipairs(df.global.world.raws.creatures.all) do if cr.creature_id == tok then return i end end
    for i, cr in ipairs(df.global.world.raws.creatures.all) do if cr.creature_id == alt then return i end end
    qerror('unknown creature ' .. tostring(tok))
end

local function wild(u)
    return not U.isDead(u) and (U.isWildlife(u) or (U.isAnimal(u) and not U.isTame(u) and not U.isDomesticated(u) and not U.isFortControlled(u)))
end

local function vanishCave()
    local n = 0
    for _, u in ipairs(df.global.world.units.active) do
        if wild(u) and u.animal.population.cave_id >= 0 then u.animal.vanish_countdown = 1; n = n + 1 end
    end
    return n
end

if cmd == 'info' then
    local draw = drawTiles()
    local per = {}
    for _, p in ipairs(df.global.world.populations.all) do
        local P = p.population
        if caveAnimal(p) and draw[P.region_x * 65536 + P.region_y] then
            local d = caveDepth(P.cave_id)
            if d then
                per[d] = per[d] or { caves = {}, pairs = {}, open = {} }
                per[d].caves[P.cave_id] = true
                per[d].pairs[P.region_x .. ':' .. P.region_y .. '/' .. P.cave_id] = true
                if not p.flags.extinct and p.quantity > 0 then
                    local r = df.creature_raw.find(p.race).creature_id
                    per[d].open[r] = (per[d].open[r] or 0) + 1
                end
            end
        end
    end
    for d = 0, 7 do
        local x = per[d]
        if x then
            local cv, pr, op = {}, 0, {}
            for c in pairs(x.caves) do cv[#cv + 1] = tostring(c) end
            for _ in pairs(x.pairs) do pr = pr + 1 end
            for r, n in pairs(x.open) do op[#op + 1] = r .. '=' .. n end
            table.sort(cv); table.sort(op)
            print(('DEPTH %d (cavern %d) caves %s; %d tile x cave pairs; open: %s'):format(d + 1, d + 1, table.concat(cv, ','), pr, table.concat(op, ' ')))
        end
    end
    return
end

if cmd == 'setup' then
    local D, SUBJ, CTRL = tonumber(args[2]), args[3], args[4]
    local F, Q = tonumber(args[5]) or 50, tonumber(args[6]) or 100
    if not (D and D >= 1 and D <= 3 and SUBJ and CTRL and SUBJ ~= CTRL) then qerror('usage: cx-cavearrive setup DEPTH SUBJ CTRL [F] [Q]') end
    local ld = D - 1
    local draw = drawTiles()
    local is, ic = raceIdx(SUBJ), raceIdx(CTRL)
    for _, r in ipairs({ is, ic }) do
        local cr = df.creature_raw.find(r)
        local _, lo, hi = pcall(function() return cr.underground_layer_min, cr.underground_layer_max end)
        if lo and hi and (D < lo or D > hi) then print(('WARN %s raw UNDERGROUND_DEPTH %d:%d excludes cavern %d'):format(cr.creature_id, lo, hi, D)) end
    end
    local all = df.global.world.populations.all
    local slots = {}     -- 'rx:ry/cave' -> { tmpl = pop, have = { [race] = true } }
    local closed, opened = 0, 0
    for _, p in ipairs(all) do
        local P = p.population
        if caveAnimal(p) and draw[P.region_x * 65536 + P.region_y] and caveDepth(P.cave_id) == ld then
            local key = P.region_x .. ':' .. P.region_y .. '/' .. P.cave_id
            local s = slots[key]
            if not s then s = { tmpl = p, have = {} }; slots[key] = s end
            if (p.race == is or p.race == ic) and not s.have[p.race] then
                p.flags.extinct = false; p.quantity = Q; p.quantity_max = math.max(p.quantity_max, Q); s.have[p.race] = true; opened = opened + 1
            elseif not p.flags.extinct then p.flags.extinct = true; closed = closed + 1 end
        end
    end
    local created, nslots, failed = 0, 0, 0
    for _, s in pairs(slots) do
        nslots = nslots + 1
        for _, race in ipairs({ is, ic }) do
            if not s.have[race] then
                local t = s.tmpl.population
                local ul = df.world_underground_region.find(t.cave_id)
                local feat = ul and ul.feature_init and ul.feature_init.feature or nil
                if feat then
                    feat.population:insert('#', { new = df.world_population, type = df.world_population_type.Animal, race = race,
                                                  count_min = Q, count_max = Q })
                    all:insert('#', { new = df.local_population, type = df.world_population_type.Animal, race = race,
                                      quantity = Q, quantity_max = Q, breed = -1 })
                    local live = all[#all - 1]
                    local r = live.population
                    r.region_x, r.region_y, r.feature_idx, r.cave_id, r.site_id = t.region_x, t.region_y, t.feature_idx, t.cave_id, t.site_id
                    r.population_idx = #feat.population - 1
                    live.flags.extinct = false
                    s.have[race] = true; created = created + 1
                else
                    failed = failed + 1
                end
            end
        end
    end
    local f0 = { [is] = df.creature_raw.find(is).frequency, [ic] = df.creature_raw.find(ic).frequency }   -- as loaded (the tool's write, if any)
    df.creature_raw.find(is).frequency = F
    df.creature_raw.find(ic).frequency = F
    S.seen, S.depth, S.races = {}, ld, { is, ic }
    local gone = vanishCave()
    for _, u in ipairs(df.global.world.units.active) do if wild(u) and u.animal.population.cave_id >= 0 then S.seen[u.id] = true end end
    for _, r in ipairs({ is, ic }) do
        local cr = df.creature_raw.find(r)
        local fl = {}
        for _, f in ipairs({ 'LARGE_ROAMING', 'AMPHIBIOUS', 'AQUATIC', 'FLIER', 'HAS_ANY_INTELLIGENT_LEARNS', 'HAS_ANY_INTELLIGENT_SPEAKS', 'HAS_ANY_CAN_SWIM',
                             'LARGE_PREDATOR', 'BENIGN', 'EVIL', 'GOOD', 'SAVAGE', 'FANCIFUL', 'HAS_ANY_NOT_LIVING', 'UBIQUITOUS', 'VERMIN_GROUNDER' }) do
            local ok, v = pcall(function() return cr.flags[f] end)
            if ok and v then fl[#fl + 1] = f end
        end
        local _, lo, hi = pcall(function() return cr.underground_layer_min, cr.underground_layer_max end)
        print(('RAW %s freq %d (as loaded) cluster %d-%d depth %s-%s pop %d-%d flags %s'):format(cr.creature_id, f0[r], cr.cluster_number[0], cr.cluster_number[1],
            tostring(lo), tostring(hi), cr.population_number[0], cr.population_number[1], table.concat(fl, ',')))
    end
    print(('SETUP cavern %d: %s and %s each on %d tile x cave pair(s), FREQUENCY %d, quantity %d; %d opened, %d created, %d failed, %d other entries closed; %d wild cavern animal(s) vanished')
        :format(D, SUBJ, CTRL, nslots, F, Q, opened, created, failed, closed, gone))
    return
end

if cmd == 'collect' then
    local t = df.global.cur_year * 403200 + df.global.cur_year_tick
    local waves, order = {}, {}
    for _, u in ipairs(df.global.world.units.active) do
        if wild(u) and u.animal.population.cave_id >= 0 then
            if not S.seen[u.id] then
                S.seen[u.id] = true
                local pr = u.animal.population
                local key = u.race .. ':' .. pr.region_x .. ':' .. pr.region_y .. ':' .. pr.cave_id .. ':' .. pr.population_idx
                if not waves[key] then
                    waves[key] = { race = u.race, n = 0, rx = pr.region_x, ry = pr.region_y, d = (caveDepth(pr.cave_id) or -2) + 1 }
                    order[#order + 1] = key
                end
                waves[key].n = waves[key].n + 1
            end
            u.animal.vanish_countdown = 1   -- every wild cavern animal goes, recorded or not, so nothing holds the gate
        end
    end
    for _, key in ipairs(order) do
        local w = waves[key]
        print(('WAVE %d %s %d %d %d %d'):format(t, df.creature_raw.find(w.race).creature_id:gsub(' ', '_'), w.n, w.rx, w.ry, w.d))
    end
    -- the test pair's stock at the test depth: DF debits a wave's PLANNED size when it plans it, so a debit with no unit
    -- arriving is a drawn wave that could not be placed; no debit is a wave never drawn
    if S.races then
        local q = { [S.races[1]] = 0, [S.races[2]] = 0 }
        for _, p in ipairs(df.global.world.populations.all) do
            if q[p.race] and caveAnimal(p) and not p.flags.extinct and caveDepth(p.population.cave_id) == S.depth then q[p.race] = q[p.race] + p.quantity end
        end
        print(('QTY %d %d'):format(q[S.races[1]], q[S.races[2]]))
    end
    print(('COLLECT %d wave(s) at %d'):format(#order, t))
    return
end

if cmd == 'state' then
    local ld = (tonumber(args[2]) or 1) - 1
    local draw = drawTiles()
    local by = {}
    for _, p in ipairs(df.global.world.populations.all) do
        local P = p.population
        if caveAnimal(p) and draw[P.region_x * 65536 + P.region_y] and caveDepth(P.cave_id) == ld and not p.flags.extinct then
            local r = df.creature_raw.find(p.race).creature_id
            by[r] = by[r] or {}
            table.insert(by[r], P.region_x .. ':' .. P.region_y .. '/' .. P.cave_id .. '=' .. p.quantity)
        end
    end
    for r, l in pairs(by) do print(('OPEN %s f%d %s'):format(r, df.creature_raw.find(raceIdx(r)).frequency, table.concat(l, ' '))) end
    return
end

qerror('usage: cx-cavearrive info | setup DEPTH SUBJ CTRL [F] [Q] | collect | state DEPTH')
