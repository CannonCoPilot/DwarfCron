-- sw-t1-recorder: animal activity on a fort, recorded in game (no RPC polling), for test item 1 (PLAN R5, 7 Oct 2026).
--
--   sw-t1-recorder start DIR [EVERY=100] [POPS]   record into DIR (relative to the DF folder) every EVERY ticks;
--                                          POPS: population indices (comma-separated) to watch in pops.tsv
--   sw-t1-recorder stop                    flush and stop
--   sw-t1-recorder status                  one line: samples, units known, events, reports
--
-- DIR/events.tsv   tick, event (ARRIVE | LEAVE | RETURN | DIE | TAME | SAMPLE_START), unit id, race, caste, kind
--                  (wild | wild-group | pet/livestock | visitor | merchant | invader | other), x, y, z, layer, detail
--                  (DIE: the incident's cause and killer, when DF recorded one)
-- DIR/positions.tsv every unit above every 1,000 ticks: tick, id, race, kind, x, y, z, layer, alive
-- DIR/reports.tsv  every new announcement report: tick, report id, type, text (combat, hunting, deaths, arrivals ...)
-- DIR/samples.tsv  tick, wild units on the map, of them in the tool's groups, pets/livestock, dead this sample, fps
-- DIR/pops.tsv     (with POPS) tick, population index, race, quantity, extinct -- a row at start and on every change
--                  (a refund that lifts a held entry between the tool's daily holds shows as a 0 -> n row)
-- DIR/ledger.tsv   every seasonal-wildlife ledger entry as it is written: abs tick, kind, layer, text (the tool keeps
--                  only its newest 300, and a season writes ~900: V73_WATERFALL's dump began 33 days into the run)
-- Citizens and residents are not recorded (they are the fort, not its animals); every other creature is.
-- luacheck: globals SWT1
local args = { ... }
local TICKS_PER_YEAR = 403200

SWT1 = SWT1 or {}
local S = SWT1

local function now()
    return df.global.cur_year * TICKS_PER_YEAR + df.global.cur_year_tick
end

local function open(name, header)
    local p = S.dir .. '/' .. name
    local exists = io.open(p, 'r')
    if exists then exists:close() end
    local f = assert(io.open(p, 'a'))
    if not exists then f:write(header, '\n') end
    return f
end

local function raceName(r)
    local cr = df.creature_raw.find(r)
    return cr and cr.creature_id or tostring(r)
end
local function casteName(r, c)
    local cr = df.creature_raw.find(r)
    local ca = cr and cr.caste[c]
    return ca and ca.caste_id or tostring(c)
end

-- the tool's tracked group members (its groups record), read once per sample: id -> the group's layer
local function groupIds()
    local ids = {}
    local ok, sw = pcall(reqscript, 'seasonal-wildlife')
    if not ok then return ids end
    local okG, g = pcall(function() return sw.loadGroups() end)
    if okG and type(g) == 'table' then
        for _, grp in ipairs(g.groups or {}) do for _, id in ipairs(grp.ids or {}) do ids[id] = grp.layer or 'land' end end
    end
    return ids
end

local function kindOf(u, groups)
    local U = dfhack.units
    if U.isCitizen(u) or U.isResident(u) then return nil end
    if U.isMerchant(u) then return 'merchant' end
    if U.isInvader(u) then return 'invader' end
    if U.isVisitor(u) then return 'visitor' end
    if U.isAnimal(u) and (U.isTame(u) or U.isDomesticated(u) or U.isFortControlled(u)) then return 'pet/livestock' end
    if U.isWildlife(u) or U.isAnimal(u) then return groups[u.id] and 'wild-group' or 'wild' end
    return 'other'
end

-- the layer: a wild animal takes Seasonal Wildlife's own (land, water, cavern, deep: from its population source, as the tool
-- manages it); any other unit is surface or underground by its tile. (7 Oct: the old tile test never returned 'water'.)
local SW = nil
local function layerOf(u)
    local x, y, z = dfhack.units.getPosition(u)
    if not x then return '?', -1, -1, -1 end
    -- a group member: the tool's own layer for it (8 Oct, V73_OCEAN2: ocean life has no feature index, so the population
    -- test files the water layer's orcas and sharks as land)
    local gl = S.grpLayer and S.grpLayer[u.id]
    if type(gl) == 'string' then return gl, x, y, z end
    if SW == nil then local ok, m = pcall(reqscript, 'seasonal-wildlife'); SW = ok and m or false end
    if SW and SW.WILD and (dfhack.units.isWildlife(u) or dfhack.units.isAnimal(u)) and u.animal.population.region_x >= 0 then
        local ok, L = pcall(SW.WILD.layerOf, u)
        if ok and L then return L, x, y, z end
    end
    local b = dfhack.maps.getTileBlock(x, y, z)
    local layer = (b and b.designation[x % 16][y % 16].subterranean) and 'underground' or 'surface'
    return layer, x, y, z
end
local function managed(L) return L == 'land' or L == 'water' or L == 'cavern' end

local function deathDetail(u)
    local inc = u.counters.death_id >= 0 and df.incident.find(u.counters.death_id) or nil
    if not inc then return 'no incident' end
    local killer = inc.criminal >= 0 and df.unit.find(inc.criminal) or nil
    return ('cause %s; killer %s%s'):format(df.death_type[inc.death_cause] or tostring(inc.death_cause),
        inc.criminal_race >= 0 and raceName(inc.criminal_race) or 'none',
        inc.criminal >= 0 and (' #' .. inc.criminal .. (killer and dfhack.units.isCitizen(killer) and ' (citizen)' or '')) or '')
end

local function event(t, ev, u, kind, detail)
    local layer, x, y, z = layerOf(u)
    S.ev:write(table.concat({ t, ev, u.id, raceName(u.race), casteName(u.race, u.caste), kind, x, y, z, layer, detail or '' }, '\t'), '\n')
    S.nev = S.nev + 1
end

-- ARRIVE detail (8 Oct, V73_WREN): how old the unit is, its mother if DF recorded one, and whether it stands on the map
-- edge -- a hatchling or newborn is days old and inside the map; a wave walks in at an edge. Births count as arrivals.
local function arriveDetail(u, t)
    local age = t - (u.birth_year * TICKS_PER_YEAR + u.birth_time)
    local m = df.global.world.map
    local edge = u.pos.x <= 1 or u.pos.y <= 1 or u.pos.x >= m.x_count - 2 or u.pos.y >= m.y_count - 2
    local mom = u.relationship_ids.Mother
    return ('age %d; %s%s'):format(age, edge and 'edge' or 'inside', (mom and mom >= 0) and ('; mother #' .. mom) or '')
end

local function sample()
    if not S.on then return end
    if not dfhack.isMapLoaded() then S.on = false; return end
    local t = now()
    local groups = groupIds()
    S.grpLayer = groups
    local present = {}
    local nWild, nGroup, nPet, nDead, nManaged, nDeep = 0, 0, 0, 0, 0, 0
    local snap = t - (S.lastSnap or -1e9) >= 1000
    for _, u in ipairs(df.global.world.units.all) do
        local kind = kindOf(u, groups)
        if kind then
            local id = u.id
            local dead = dfhack.units.isDead(u)
            local active = dfhack.units.isActive(u) and not u.flags1.inactive
            local k = S.known[id]
            if not k then
                if active and not dead then
                    S.known[id] = { state = 'here', kind = kind }
                    event(t, S.first and 'PRESENT' or 'ARRIVE', u, kind, (not S.first) and arriveDetail(u, t) or nil)
                end
            else
                if dead and k.state ~= 'dead' then
                    k.state = 'dead'; nDead = nDead + 1
                    event(t, 'DIE', u, kind, deathDetail(u))
                elseif not dead and not active and k.state == 'here' then
                    k.state = 'gone'; event(t, 'LEAVE', u, kind)
                elseif not dead and active and k.state == 'gone' then
                    k.state = 'here'; event(t, 'RETURN', u, kind)
                end
                if kind ~= k.kind and not dead then
                    event(t, 'KIND', u, kind, k.kind .. ' -> ' .. kind); k.kind = kind
                end
            end
            if active and not dead then
                present[id] = true
                if kind == 'wild' or kind == 'wild-group' then
                    nWild = nWild + 1
                    if managed((layerOf(u))) then nManaged = nManaged + 1 else nDeep = nDeep + 1 end
                end
                if kind == 'wild-group' then nGroup = nGroup + 1 end
                if kind == 'pet/livestock' then nPet = nPet + 1 end
                if snap then
                    local layer, x, y, z = layerOf(u)
                    S.pos:write(table.concat({ t, id, raceName(u.race), kind, x, y, z, layer, 1 }, '\t'), '\n')
                end
            end
        end
    end
    -- a unit DF dropped from the vector entirely while we thought it here: it left
    for id, k in pairs(S.known) do
        if k.state == 'here' and not present[id] and not df.unit.find(id) then
            k.state = 'gone'
            S.ev:write(table.concat({ t, 'LEAVE', id, '?', '?', k.kind, -1, -1, -1, '?', 'removed from the unit vector' }, '\t'), '\n')
        end
    end
    if snap then S.lastSnap = t end
    -- new reports (announcements): their text is the readable record of hunts, fights and deaths
    local reps = df.global.world.status.reports
    for i = #reps - 1, 0, -1 do
        local r = reps[i]
        if r.id <= S.lastReport then break end
        S.newReps[#S.newReps + 1] = r
    end
    for i = #S.newReps, 1, -1 do
        local r = S.newReps[i]
        S.rep:write(table.concat({ t, r.id, df.announcement_type[r.type] or tostring(r.type), (r.text:gsub('[\t\n]', ' ')) }, '\t'), '\n')
        S.nrep = S.nrep + 1
        if r.id > S.lastReport then S.lastReport = r.id end
    end
    S.newReps = {}
    S.smp:write(table.concat({ t, nWild, nGroup, nPet, nDead, df.global.enabler.calculated_fps, nManaged, nDeep }, '\t'), '\n')
    local L = rawget(_G, '__seasonal_wildlife_cache')
    L = L and L.ledger
    if L and L.count and S.ledCount and L.count > S.ledCount then
        local new, es = L.count - S.ledCount, L.entries
        if new > #es then S.led:write(table.concat({ t, 'GAP', '', (new - #es) .. ' entries lost' }, '\t'), '\n'); new = #es end
        for i = #es - new + 1, #es do
            local e = es[i]
            S.led:write(table.concat({ e.t, e.k, e.l, (tostring(e.s):gsub('[\t\n]', ' ')) }, '\t'), '\n')
        end
    end
    if L and L.count then S.ledCount = L.count end
    if S.pops then
        local all = df.global.world.populations.all
        for _, i in ipairs(S.pops) do
            local p = all[i]
            local v = p and (p.quantity .. '\t' .. tostring(p.flags.extinct)) or 'gone\t-'
            if S.popLast[i] ~= v then
                local cr = p and df.creature_raw.find(p.race)
                S.pop:write(table.concat({ t, i, cr and cr.creature_id or '?', v }, '\t'), '\n')
                S.popLast[i] = v
            end
        end
    end
    S.n = S.n + 1
    S.first = false
    if S.n % 20 == 0 then S.ev:flush(); S.pos:flush(); S.rep:flush(); S.smp:flush(); if S.pop then S.pop:flush() end; S.led:flush() end
    dfhack.timeout(S.every, 'ticks', sample)
end

local cmd = args[1]
if cmd == 'start' then
    if S.on then print('sw-t1-recorder: already recording into ' .. S.dir); return end
    if not dfhack.isMapLoaded() then qerror('no map loaded') end
    S.dir = assert(args[2], 'usage: sw-t1-recorder start DIR [EVERY]')
    dfhack.filesystem.mkdir_recursive(S.dir)
    S.every = tonumber(args[3] or '') or 100
    S.ev = open('events.tsv', 'tick\tevent\tid\trace\tcaste\tkind\tx\ty\tz\tlayer\tdetail')
    S.pos = open('positions.tsv', 'tick\tid\trace\tkind\tx\ty\tz\tlayer\talive')
    S.rep = open('reports.tsv', 'tick\treport_id\ttype\ttext')
    S.smp = open('samples.tsv', 'tick\twild\twild_in_groups\tpets_livestock\tdied\tfps\twild_managed\twild_deep')
    S.pops, S.pop, S.popLast = nil, nil, {}
    S.led, S.ledCount = open('ledger.tsv', 'tick\tkind\tlayer\ttext'), nil
    if args[4] then
        S.pops = {}
        for i in args[4]:gmatch('%d+') do S.pops[#S.pops + 1] = tonumber(i) end
        S.pop = open('pops.tsv', 'tick\tpop\trace\tquantity\textinct')
    end
    S.known, S.newReps, S.n, S.nev, S.nrep, S.first, S.lastSnap = {}, {}, 0, 0, 0, true, nil
    local reps = df.global.world.status.reports
    S.lastReport = #reps > 0 and reps[#reps - 1].id or -1
    S.ev:write(table.concat({ now(), 'SAMPLE_START', -1, '', '', '', -1, -1, -1, '', 'every ' .. S.every .. ' ticks' }, '\t'), '\n')
    S.on = true
    sample()
    print(('sw-t1-recorder: recording into %s every %d ticks (%d units present at start)'):format(S.dir, S.every, S.nev))
elseif cmd == 'stop' then
    if not S.on and not S.ev then print('sw-t1-recorder: not recording'); return end
    S.on = false
    for _, f in ipairs({ S.ev, S.pos, S.rep, S.smp, S.pop, S.led }) do pcall(function() f:flush(); f:close() end) end
    S.pop, S.pops, S.led = nil, nil, nil
    S.ev = nil
    print(('sw-t1-recorder: stopped; %d samples, %d events, %d reports in %s'):format(S.n or 0, S.nev or 0, S.nrep or 0, tostring(S.dir)))
else
    print(('sw-t1-recorder: %s; %s samples, %s events, %s reports, %s units known, dir %s'):format(S.on and 'recording' or 'stopped',
        tostring(S.n), tostring(S.nev), tostring(S.nrep), tostring(S.known and #(function() local t = {} for k in pairs(S.known) do t[#t+1] = k end return t end)() or 0), tostring(S.dir)))
end
