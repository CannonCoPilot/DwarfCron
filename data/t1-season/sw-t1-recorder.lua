-- sw-t1-recorder: animal activity on a fort, recorded in game (no RPC polling), for test item 1 (PLAN R5, 7 Oct 2026).
--
--   sw-t1-recorder start DIR [EVERY=100]   record into DIR (relative to the DF folder) every EVERY ticks
--   sw-t1-recorder stop                    flush and stop
--   sw-t1-recorder status                  one line: samples, units known, events, reports
--
-- DIR/events.tsv   tick, event (ARRIVE | LEAVE | RETURN | DIE | TAME | SAMPLE_START), unit id, race, caste, kind
--                  (wild | wild-group | pet/livestock | visitor | merchant | invader | other), x, y, z, layer, detail
--                  (DIE: the incident's cause and killer, when DF recorded one)
-- DIR/positions.tsv every unit above every 1,000 ticks: tick, id, race, kind, x, y, z, layer, alive
-- DIR/reports.tsv  every new announcement report: tick, report id, type, text (combat, hunting, deaths, arrivals ...)
-- DIR/samples.tsv  tick, wild units on the map, of them in the tool's groups, pets/livestock, dead this sample, fps
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

-- the tool's tracked group members (its groups record), read once per sample
local function groupIds()
    local ids = {}
    local ok, sw = pcall(reqscript, 'seasonal-wildlife')
    if not ok then return ids end
    local okG, g = pcall(function() return sw.loadGroups() end)
    if okG and type(g) == 'table' then
        for _, grp in ipairs(g.groups or {}) do for _, id in ipairs(grp.ids or {}) do ids[id] = true end end
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

-- surface, water (in or over water), cavern (below the first cavern ceiling seen), magma depth: a coarse layer by z
local function layerOf(u)
    local x, y, z = dfhack.units.getPosition(u)
    if not x then return '?', -1, -1, -1 end
    local layer = 'surface'
    local b = dfhack.maps.getTileBlock(x, y, z)
    if b then
        local d = b.designation[x % 16][y % 16]
        if d.liquid_type == df.tile_liquid.Water and d.flow_size > 0 then layer = 'water' end
        if d.subterranean then layer = (d.liquid_type == df.tile_liquid.Magma and d.flow_size > 0) and 'magma' or 'underground' end
    end
    return layer, x, y, z
end

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

local function sample()
    if not S.on then return end
    if not dfhack.isMapLoaded() then S.on = false; return end
    local t = now()
    local groups = groupIds()
    local present = {}
    local nWild, nGroup, nPet, nDead = 0, 0, 0, 0
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
                    event(t, S.first and 'PRESENT' or 'ARRIVE', u, kind)
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
                if kind == 'wild' or kind == 'wild-group' then nWild = nWild + 1 end
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
    S.smp:write(table.concat({ t, nWild, nGroup, nPet, nDead, df.global.enabler.calculated_fps }, '\t'), '\n')
    S.n = S.n + 1
    S.first = false
    if S.n % 20 == 0 then S.ev:flush(); S.pos:flush(); S.rep:flush(); S.smp:flush() end
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
    S.smp = open('samples.tsv', 'tick\twild\twild_in_groups\tpets_livestock\tdied\tfps')
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
    for _, f in ipairs({ S.ev, S.pos, S.rep, S.smp }) do pcall(function() f:flush(); f:close() end) end
    S.ev = nil
    print(('sw-t1-recorder: stopped; %d samples, %d events, %d reports in %s'):format(S.n or 0, S.nev or 0, S.nrep or 0, tostring(S.dir)))
else
    print(('sw-t1-recorder: %s; %s samples, %s events, %s reports, %s units known, dir %s'):format(S.on and 'recording' or 'stopped',
        tostring(S.n), tostring(S.nev), tostring(S.nrep), tostring(S.known and #(function() local t = {} for k in pairs(S.known) do t[#t+1] = k end return t end)() or 0), tostring(S.dir)))
end
