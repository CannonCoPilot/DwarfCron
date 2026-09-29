-- cx-load.lua -- load levers and the load reading for the FPS experiments (experiments/FPS2.json).
--
-- Each lever puts real simulation load on a loaded fort the way play would, and prints a one-line receipt.
--
--   cx-load line                     one line: citizens, active units, wild units, items, map size, fps/gfps achieved
--   cx-load wild <n> [species] [prey] place n wild land animals (prey: prey species only) on the surface through seasonal-wildlife's `place`,
--                                    spread over up to <species> (default 6) of the fort's surface land entries;
--                                    each entry is topped up first so the stock never limits the count
--   cx-load clearwild                vaporize every wild unit on every layer (exterminate's method: vanish_countdown 1,
--                                    gone on the next tick, no corpse) and close every Animal pool entry on the site's
--                                    9 region tiles and its caverns (quantity 0, extinct) -- in memory only, never saved
--   cx-load constwild <n>            FPS5: clearwild, then place n PREY land animals, close the pools again, and set every
--                                    wild unit's leave countdown to 10,000,000 -- the same wild load on any map, held
--   cx-load hold                     every wild unit's leave countdown to 10,000,000 (nobody leaves)
--   cx-load sustain                  every living citizen's thirst and hunger timers to 0 (FPS5b: fresh embarks at
--                                    region4 29,20 have no water; in the first year-long session all 20 dwarves died
--                                    of THIRST and the settlement withered). Dwarves then never walk to eat or drink.
--   cx-load citizens <n>             n new dwarves at existing citizens' tiles, made citizens with makeown
--                                    (a histfig, the civ and the site government), each given a working
--                                    citizen's labors so they take jobs rather than idle
--   cx-load work [side]              the fort's hauling: one stockpile accepting everything (DFHack's library/all)
--                                    on the flattest reachable side x side patch (default 30) at the citizens' level,
--                                    so every loose item becomes a hauling job (BOATS: 0 stockpiles, 745 loose items,
--                                    29 of 29 citizens haul, 0 jobs before)
--   cx-load rework [side]            remove the last stockpile and lay the next >= 50 tiles away (sustained hauling)
--   cx-load breach <zlo-zhi,...> [n] [dry]
--                                    dig one up/down stair shaft from a surface floor the citizens reach down to
--                                    the first n cavern bands (default all listed), through rock only, sealing
--                                    any aquifer on the 3x3 around it; marks the caves discovered and proves a
--                                    citizen can walk to a floor in each band. Bands come from
--                                    `seasonal-wildlife caverns` (BOATS: 64-72,59-63,38-46).
--
-- Verified on BOATS (28 Sep 2026): a created dwarf + make_own is a citizen with histfig, own group and fort
-- control, alive and moving 1,800 ticks later; the breach finds a column in 1.6 s, and one tick after the dig
-- the fort's walkable group reaches all three bands with no water in the shaft.

local args = { ... }
local cmd = args[1]
local w = df.global.world

local function line()
    local e = df.global.enabler
    local cit, wild, busy, cav = 0, 0, 0, 0
    for _, u in ipairs(w.units.active) do
        if not dfhack.units.isDead(u) then
            if dfhack.units.isCitizen(u) then cit = cit + 1; if u.job.current_job then busy = busy + 1 end end
            if dfhack.units.isWildlife(u) then
                wild = wild + 1
                local ap = u.animal.population
                if ap.feature_idx >= 0 or ap.cave_id >= 0 then cav = cav + 1 end
            end
        end
    end
    local dead = 0
    for _, u in ipairs(w.units.all) do
        if u.civ_id == df.global.plotinfo.civ_id and dfhack.units.isDead(u)
           and df.creature_raw.find(u.race).creature_id == 'DWARF' then dead = dead + 1 end
    end
    local jobs, link = 0, w.jobs.list.next
    while link do jobs = jobs + 1; link = link.next end
    -- the map/fps fields keep FPS2's order (fps2-tally.py's regex); working citizens and jobs trail
    return ('citizens %d units %d wild %d items %d map %dx%dx%d fps %s gfps %s working %d jobs %d cavwild %d dead %d'):format(cit, #w.units.active, wild,
        #w.items.other.IN_PLAY, w.map.x_count, w.map.y_count, w.map.z_count, tostring(e.calculated_fps), tostring(e.calculated_gfps), busy, jobs, cav, dead)
end

local function flag(t, k)   -- a flag name this DF build lacks reads false, not an error
    local ok, v = pcall(function() return t[k] end)
    return ok and v or false
end

local function citizens()
    local out = {}
    for _, u in ipairs(w.units.active) do
        if dfhack.units.isCitizen(u) and not dfhack.units.isDead(u) and not u.flags1.inactive then out[#out + 1] = u end
    end
    return out
end

local function sitePools(fn)
    -- every Animal entry the site's map can draw from: its region tiles and their ring, every layer
    local site = df.world_site.find(df.global.plotinfo.site_id)
    local x0, x1 = site.global_min_x // 16, site.global_max_x // 16
    local y0, y1 = site.global_min_y // 16, site.global_max_y // 16
    local n = 0
    for _, p in ipairs(w.populations.all) do
        local r = p.population
        if p.type == df.world_population_type.Animal and r.region_x >= x0 - 1 and r.region_x <= x1 + 1
           and r.region_y >= y0 - 1 and r.region_y <= y1 + 1 then fn(p); n = n + 1 end
    end
    return n
end

local function closePools()
    return sitePools(function(p) p.quantity = 0; p.flags.extinct = true end)
end

local function holdWild()
    local n = 0
    for _, u in ipairs(w.units.active) do
        if dfhack.units.isWildlife(u) and not dfhack.units.isDead(u) then u.animal.leave_countdown = 10000000; n = n + 1 end
    end
    return n
end

if cmd == 'line' then
    print('load: ' .. line())

elseif cmd == 'clearwild' then
    local v = 0
    for _, u in ipairs(w.units.active) do
        if dfhack.units.isWildlife(u) and not dfhack.units.isDead(u) then u.animal.vanish_countdown = 1; v = v + 1 end
    end
    print(('clearwild: %d wild unit(s) set to vanish next tick; %d pool entries closed'):format(v, closePools()))

elseif cmd == 'sustain' then
    local n = 0
    for _, u in ipairs(citizens()) do u.counters2.thirst_timer = 0; u.counters2.hunger_timer = 0; n = n + 1 end
    print(('sustain: %d citizen(s) watered and fed'):format(n))

elseif cmd == 'hold' then
    print(('hold: %d wild unit(s) will not leave'):format(holdWild()))

elseif cmd == 'constwild' then
    -- the caller has already run clearwild and let one tick pass (the vanished units must be gone before placing)
    local n = tonumber(args[2]) or 30
    local out = dfhack.run_command_silent('cx-load', 'wild', tostring(n), '6', 'prey') or ''
    local closed = closePools()
    print(('constwild: %s; pools closed %d; held %d'):format(out:gsub('%s+$', ''), closed, holdWild()))

elseif cmd == 'wild' then
    local n, nsp = tonumber(args[2]) or 0, tonumber(args[3]) or 6
    local site = df.world_site.find(df.global.plotinfo.site_id)
    local x0, x1 = site.global_min_x // 16, site.global_max_x // 16
    local y0, y1 = site.global_min_y // 16, site.global_max_y // 16
    -- which species walk: seasonal-wildlife's own model (habitat land, not vermin, not a megabeast), in the embark's pool
    local sw = reqscript('seasonal-wildlife')
    local walker = {}
    for _, e in ipairs(sw.buildPool(sw.loadConfig())) do
        if e.inEmbark and e.layer == 'land' and e.habitat == 'land' and e.cat ~= 'vermin' and not e.mega and not e.locked
           and (args[4] ~= 'prey' or e.role == 'prey') then walker[e.token] = true end
    end
    -- their surface entries on the site's tiles, biggest first; one per species
    local cand, seen = {}, {}
    for _, p in ipairs(w.populations.all) do
        local r = p.population
        if p.type == df.world_population_type.Animal and r.feature_idx < 0 and r.cave_id < 0
           and r.region_x >= x0 - 1 and r.region_x <= x1 + 1 and r.region_y >= y0 - 1 and r.region_y <= y1 + 1 then   -- DF draws from all 9 neighbours
            local cr = df.creature_raw.find(p.race)
            if cr and walker[cr.creature_id] and not seen[cr.creature_id] then
                seen[cr.creature_id] = true; cand[#cand + 1] = { tok = cr.creature_id, p = p }
            end
        end
    end
    table.sort(cand, function(a, b) return a.p.quantity_max > b.p.quantity_max end)
    local k = math.min(nsp, #cand)
    if k == 0 then print('wild: no surface land entry on this site'); return end
    local placed, parts = 0, {}
    for i = 1, k do
        local want = (n // k) + ((i <= n % k) and 1 or 0)
        if want > 0 then
            local p = cand[i].p
            if p.quantity < want + 5 then p.quantity = want + 5 end
            p.flags.extinct = false
            local out = dfhack.run_command_silent('seasonal-wildlife', 'place', cand[i].tok, tostring(want), 'land') or ''
            local got = tonumber(out:match('placed (%d+)')) or 0
            placed = placed + got; parts[#parts + 1] = ('%s %d/%d'):format(cand[i].tok, got, want)
        end
    end
    print(('wild: placed %d of %d (%s)'):format(placed, n, table.concat(parts, ', ')))

elseif cmd == 'citizens' then
    local n = tonumber(args[2]) or 0
    local cits = citizens()
    if #cits == 0 then print('citizens: no citizen to copy'); return end
    -- the labor template: the citizen with the most labors enabled
    local tmpl, most = cits[1], -1
    for _, u in ipairs(cits) do
        local c = 0
        for i = 0, #u.status.labors - 1 do if u.status.labors[i] then c = c + 1 end end
        if c > most then tmpl, most = u, c end
    end
    local mo = reqscript('makeown')
    local made, failed = 0, 0
    for i = 1, n do
        local at = cits[(i - 1) % #cits + 1]
        local u = dfhack.units.create(at.race, math.random(0, #df.creature_raw.find(at.race).caste - 1))
        if u then
            u.pos:assign(at.pos); u.idle_area:assign(at.pos)
            w.units.active:insert('#', u)
            local blk = dfhack.maps.getTileBlock(at.pos)
            if blk then blk.occupancy[at.pos.x % 16][at.pos.y % 16].unit = true end
            u.flags1.inactive = false
            local ok = pcall(mo.make_own, u)
            if ok and dfhack.units.isCitizen(u) then
                for j = 0, #u.status.labors - 1 do u.status.labors[j] = tmpl.status.labors[j] end
                made = made + 1
            else failed = failed + 1 end
        else failed = failed + 1 end
    end
    print(('citizens: made %d of %d (%d failed; labors from %d, %d enabled); now %d citizens'):format(made, n, failed, tmpl.id, most, #citizens()))

elseif cmd == 'work' or cmd == 'rework' then
    -- rework (FPS3 run 202403: one stockpile beside the loose items was filled in ~1,000 ticks, 28 working -> 6): remove
    -- the last stockpile and lay the next one at least 50 tiles from it, so everything it held is hauled across the map
    -- again; called at every sample, the fort never runs out of hauling
    local side = tonumber(args[2]) or 30
    local last = _G.CX_LOAD_PILE
    if cmd == 'rework' and last then
        local old = df.building.find(last.id)
        if old then dfhack.buildings.deconstruct(old) end
    end
    local cits = citizens()
    if #cits == 0 then print('work: no citizen'); return end
    local lv, z, best = {}, nil, 0
    for _, u in ipairs(cits) do lv[u.pos.z] = (lv[u.pos.z] or 0) + 1 end
    for zz, c in pairs(lv) do if c > best then z, best = zz, c end end
    local cx, cy, n = 0, 0, 0
    for _, u in ipairs(cits) do if u.pos.z == z then cx, cy, n = cx + u.pos.x, cy + u.pos.y, n + 1 end end
    cx, cy = cx // n, cy // n
    local from
    for _, u in ipairs(cits) do if u.pos.z == z then from = u.pos; break end end
    local T = df.tiletype
    local function ok(x, y)
        local tt = dfhack.maps.getTileType(x, y, z)
        if not tt or T.attrs[tt].shape ~= df.tiletype_shape.FLOOR then return false end
        local d = dfhack.maps.getTileFlags(x, y, z)
        return d and d.flow_size == 0 and not dfhack.buildings.findAtTile(x, y, z)
    end
    -- the flattest patch within 80 tiles of the citizens' centre whose corner the fort can walk to
    local X, Y = w.map.x_count, w.map.y_count
    local bx, by, bn = nil, nil, -1
    for x0 = math.max(1, cx - 80), math.min(X - side - 1, cx + 80 - side), 5 do
        for y0 = math.max(1, cy - 80), math.min(Y - side - 1, cy + 80 - side), 5 do
            local c = 0
            for x = x0, x0 + side - 1, 3 do for y = y0, y0 + side - 1, 3 do if ok(x, y) then c = c + 1 end end end
            local far = not (cmd == 'rework' and last) or math.max(math.abs(x0 - last.x), math.abs(y0 - last.y)) >= 50
            if far and c > bn and dfhack.maps.canWalkBetween(from, xyz2pos(x0 + side // 2, y0 + side // 2, z)) then bx, by, bn = x0, y0, c end
        end
    end
    if not bx then print('work: no reachable patch'); return end
    local ext, good = {}, 0
    for i = 0, side - 1 do for j = 0, side - 1 do
        local v = ok(bx + i, by + j); ext[i * side + j + 1] = v and 1 or 0; if v then good = good + 1 end
    end end
    local bld, err = dfhack.buildings.constructBuilding{ type = df.building_type.Stockpile, abstract = true,
        pos = xyz2pos(bx, by, z), width = side, height = side }
    if not bld then print('work: stockpile refused: ' .. tostring(err)); return end
    _G.CX_LOAD_PILE = { id = bld.id, x = bx, y = by }
    local out = dfhack.run_command_silent('stockpiles', 'import', 'library/all', '-s', tostring(bld.id)) or ''
    local loose = 0
    for _, it in ipairs(w.items.other.IN_PLAY) do if it.flags.on_ground and not it.flags.forbid then loose = loose + 1 end end
    print(('work: stockpile %d at %d,%d,%d %dx%d (%d usable tiles), settings library/all%s; %d loose items to haul')
        :format(bld.id, bx, by, z, side, side, good, out:find('rror') and (' FAILED: ' .. out:gsub('%s+', ' ')) or '', loose))

elseif cmd == 'breach' then
    local BANDS = {}
    for lo, hi in (args[2] or ''):gmatch('(%d+)-(%d+)') do BANDS[#BANDS + 1] = { tonumber(lo), tonumber(hi) } end
    if #BANDS == 0 then qerror('usage: cx-load breach <zlo-zhi,...> [n] [dry]') end
    local want = math.min(tonumber(args[3]) or #BANDS, #BANDS)
    local dry = args[4] == 'dry' or args[3] == 'dry'
    local T = df.tiletype
    local function solid(x, y, z)
        local tt = dfhack.maps.getTileType(x, y, z)
        if not tt then return false end
        local a = T.attrs[tt]
        if a.shape ~= df.tiletype_shape.WALL then return false end
        local m = a.material
        if m ~= df.tiletype_material.STONE and m ~= df.tiletype_material.MINERAL and m ~= df.tiletype_material.SOIL
           and m ~= df.tiletype_material.LAVA_STONE then return false end
        local d = dfhack.maps.getTileFlags(x, y, z)
        return d and d.flow_size == 0   -- an aquifer tile is fine: the dig seals the 3x3 around the shaft
    end
    local function floorAt(x, y, z)
        local tt = dfhack.maps.getTileType(x, y, z)
        local d = dfhack.maps.getTileFlags(x, y, z)
        return tt and T.attrs[tt].shape == df.tiletype_shape.FLOOR and d and d.flow_size == 0
    end
    -- the fort's level: where most citizens stand; walk from one of them
    local lv, ztop, best, cit = {}, nil, 0, nil
    for _, u in ipairs(citizens()) do lv[u.pos.z] = (lv[u.pos.z] or 0) + 1 end
    for z, c in pairs(lv) do if c > best then ztop, best = z, c end end
    for _, u in ipairs(citizens()) do if u.pos.z == ztop then cit = u; break end end
    if not cit then print('breach: no citizen'); return end
    local X, Y = w.map.x_count, w.map.y_count
    local N8 = { {-1,-1},{0,-1},{1,-1},{-1,0},{1,0},{-1,1},{0,1},{1,1} }
    local function touches(x, y, z)
        for _, d in ipairs(N8) do
            local nx, ny = x + d[1], y + d[2]
            if nx >= 0 and ny >= 0 and nx < X and ny < Y and floorAt(nx, ny, z) then return nx, ny end
        end
    end
    local t0 = os.clock()
    local found
    local function try(x, y)
        if x <= 1 or y <= 1 or x >= X - 2 or y >= Y - 2 then return end
        if not floorAt(x, y, ztop) or dfhack.buildings.findAtTile(x, y, ztop) then return end
        if not dfhack.maps.canWalkBetween(cit.pos, xyz2pos(x, y, ztop)) then return end
        for z = ztop - 1, BANDS[want][1], -1 do if not solid(x, y, z) then return end end
        local contact = {}
        for i = 1, want do
            for z = BANDS[i][2], BANDS[i][1], -1 do
                local nx, ny = touches(x, y, z)
                if nx then contact[i] = { x = nx, y = ny, z = z }; break end
            end
            if not contact[i] then return end
        end
        found = { x = x, y = y, contact = contact }
    end
    for r = 0, 140, 2 do   -- rings out from the citizen, stride 2, 20 s budget
        for dx = -r, r, 2 do
            for dy = -r, r, 2 do
                if math.max(math.abs(dx), math.abs(dy)) == r then try(cit.pos.x + dx, cit.pos.y + dy) end
                if found or os.clock() - t0 > 20 then break end
            end
            if found or os.clock() - t0 > 20 then break end
        end
        if found or os.clock() - t0 > 20 then break end
    end
    if not found then print(('breach: no column for %d band(s) within %.1f s (fort z %d)'):format(want, os.clock() - t0, ztop)); return end
    local zbot = found.contact[want].z
    local cs = {}
    for i, c in ipairs(found.contact) do cs[#cs + 1] = ('%d:%d,%d,%d'):format(i, c.x, c.y, c.z) end
    print(('breach: column %d,%d z%d..z%d (%d levels) in %.1f s; contacts %s'):format(found.x, found.y, ztop, zbot,
        ztop - zbot + 1, os.clock() - t0, table.concat(cs, ' ')))
    if dry then return end
    local sealed = 0
    for z = ztop, zbot, -1 do
        for ax = -1, 1 do for ay = -1, 1 do
            local a = dfhack.maps.getTileFlags(found.x + ax, found.y + ay, z)
            if a and a.water_table then a.water_table = false; sealed = sealed + 1 end
        end end
        local d = dfhack.maps.getTileFlags(found.x, found.y, z)
        d.dig = (z == ztop) and df.tile_dig_designation.DownStair
            or ((z == zbot) and df.tile_dig_designation.UpStair or df.tile_dig_designation.UpDownStair)
        dfhack.maps.getTileBlock(found.x, found.y, z).flags.designated = true
    end
    dfhack.run_command_silent('dig-now', ('%d,%d,%d'):format(found.x, found.y, zbot), ('%d,%d,%d'):format(found.x, found.y, ztop), '--clean')
    local disc = 0
    for _, f in ipairs(w.features.map_features) do
        if f:getType() == df.feature_type.subterranean_from_layer and not f.flags.Discovered then f.flags.Discovered = true; disc = disc + 1 end
    end
    -- DF rebuilds the walkable groups on its next tick; the manifest's next step proves the path (cx-load walk)
    _G.CX_LOAD_BREACH = { cit = cit.id, top = { x = found.x, y = found.y, z = ztop }, contact = found.contact }
    print(('breach: dug %d levels, sealed %d aquifer tiles, marked %d cave(s) discovered'):format(ztop - zbot + 1, sealed, disc))

elseif cmd == 'walk' then
    -- after at least one tick: can a citizen walk to each breached band's floor?
    local b = _G.CX_LOAD_BREACH
    if not b then print('walk: no breach this session'); return end
    -- from the shaft's top tile, not from a citizen: a dwarf who steps into a room the fort cannot path to reads false
    -- while the shaft is whole (FPS2 run 155935: band 1 read true, false, true, true, false for one dwarf)
    local from = xyz2pos(b.top.x, b.top.y, b.top.z)
    local s = {}
    for i, c in ipairs(b.contact) do s[#s + 1] = ('%d=%s'):format(i, tostring(dfhack.maps.canWalkBetween(from, xyz2pos(c.x, c.y, c.z)))) end
    print('walk: shaft top reaches band ' .. table.concat(s, ' '))

else
    print('usage: cx-load line | sustain | clearwild | constwild <n> | hold | wild <n> [species] [prey] | citizens <n> | work [side] | breach <zlo-zhi,...> [n] [dry] | walk')
end
