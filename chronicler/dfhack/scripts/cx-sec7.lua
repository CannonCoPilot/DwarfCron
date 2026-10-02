-- cx-sec7.lua -- the in-game half of the Alpha Four section 7 checks (experiments/ALPHA4-SECTION7.md, 1 Oct 2026).
--
-- Alpha Four's section 7 lists what a walkthrough cannot see: unit internals, counts over time, vermin, the cost of
-- the code, and a real screen. Every verb here reads one of those from DF's own structures or the tool's own state and
-- prints "eco <kind> key=value ..." lines, so eco-run.py's lua: steps keep them, check them (H2) and write them to the
-- block's TSV. Placement still goes through cx-eco (its state, _G.CX_ECO, is shared: `at` runs cx-eco in-process).
--
--   cx-sec7 facts                         what the loaded fort offers: map, tick, ticks to the next season, region
--                                         savagery/evilness, water bodies, cavern bands with civ/predator/animal-people
--                                         entries, extinct setting and in-embark extinct rows, DFHack r2 features
--   cx-sec7 spot SPOT                     print the spot SPOT resolves to (cached per map)
--   cx-sec7 at SPOT VERB ARGS...          resolve SPOT, substitute <X> <Y> <Z> (and <X+N>...) in ARGS, run cx-eco VERB
--                                         (angle brackets: eco-run fills {X} with the block's own spot before Lua runs)
--        SPOT: land | shore | water (cx-eco's spot) | lake | river | ocean | pool, each [:shore|:water]
--              | cav1 | cav2 | cav3 (an open floor in that cavern band) | fort (a citizen's tile)
--   cx-sec7 mark TAG                      remember the id of every unit on the map now (pre/post arrival split)
--   cx-sec7 skills TOKEN SKILL TAG [MARK] every on-map TOKEN unit: rating, nominal, floor (natural_skill_lvl), rust
--                                         counters, pre (in MARK) or new; then the tool's own readback rows
--   cx-sec7 rustpush TOKEN SKILL N        add N to unused/rust/demotion counters of SKILL on every on-map TOKEN unit
--                                         (the rust shortcut: DF's next skill pass rusts what would rust in ~N ticks)
--   cx-sec7 nofloor TOKEN SKILL           natural_skill_lvl 0 on those units (the rust test's positive control)
--   cx-sec7 grp TOKEN TAG                 the tool group holding the spawned TOKEN: leader, lost, panic, spread
--   cx-sec7 killleader TOKEN              that group's leader dies (blood drained, corpse kept), as exterminate does
--   cx-sec7 nat TAG                       one natural-arrivals sample: groups per layer against the cap, per cavern
--                                         and per water body, the cavern hold, apex presence, H/C/A unit shares on land,
--                                         extinct arrivals, water species shares (MIX1)
--   cx-sec7 trim TAG                      units the cavern gate trimmed: still on the map or gone
--   cx-sec7 civs D TAG                    every civ-race unit in cavern band D (1-3): position, origin, distances to
--                                         the nearest citizen and the access, hidden, items, goal, its event tokens
--   cx-sec7 irr D TAG                     cavern D's irruption: phase, waves, subjects and every written field read back
--   cx-sec7 native D TOKEN TAG            a native TOKEN unit in cavern D outside the event: its cache flags (M3)
--   cx-sec7 resid TAG                     irruption writes left on any unit (masks, cache bits beyond the caste's own)
--   cx-sec7 scav TAG                      scavenging: per species visits/kg/finished/walks/hops/wet, remains left
--   cx-sec7 wat TAG                       water: per body units, groups, species; guard counters; aquatic units dry
--   cx-sec7 breath TAG                    units.all not breathing FINE (getBreathingState, r2), by dead/inactive/active
--   cx-sec7 occ TAG                       tiles marked occupied with no standing unit, tiles with two standing units
--   cx-sec7 perf TAG                      FUSE per job (runs, ms, worst, KB, deferred), worst tick, wall-clock t/s
--   cx-sec7 bench N                       `seasonal-wildlife perf bench N`, one line per target
--   cx-sec7 ledger KIND TAG [MARK]        ledger entries of KIND since MARK (a mark tick), and the newest one
--   cx-sec7 tool WORDS...                 a seasonal-wildlife verb, its first reply line as a receipt
--   cx-sec7 pin CAVERN                    pin the cavern's pressure at the threshold (`irruption pin`), read back
--   cx-sec7 citizens D N [above|knock]    N citizens moved into cavern band D (T-PR); 'above' one level over it;
--                                         'knock' also knocks them out so they stay where they are put
--   cx-sec7 dig D N                       N dig designations on rock beside cavern D's floor (T-PR's dig source)
--   cx-sec7 toolall WORDS...              every reply line of a verb ('eco toolline' rows)
--   cx-sec7 cfgset PATH VALUE ...         write config paths as the verbs do (loadConfig, set, saveConfig)
--   cx-sec7 adj A B TAG                   spawned A and B standing adjacent (pairs), and their closest distance
--   cx-sec7 swim TOKEN TAG                spawned TOKEN units: alive, on a wet tile, not breathing FINE, dead, gone
--   cx-sec7 corpses TOKEN                 every spawned TOKEN dies where it stands (blood drained; corpse kept)
--   cx-sec7 gsize TOKEN TAG               live members of every tool group of TOKEN ('i' marks an irruption group)
--   cx-sec7 subjects D goal|kill          a harness write on every live subject of cavern D's event (M6, T-END)
--   cx-sec7 packs TOKEN TAG               R41 pack recognition over the spawned TOKEN (V7.H.packSizes, CACHE.packStat)
--   cx-sec7 ap1 N                         AP1's desk half: N in-memory land builds at ap_pick 0.1 and 1, AP seats
--
-- ⚠️ qerror() over RPC never replies (cx-eco's note): errors print 'eco error ...' and the verb returns.

_G.CX_SEC7 = _G.CX_SEC7 or { spots = {}, marks = {}, perf = nil, map = nil }
local S7 = _G.CX_SEC7
local args = { ... }
local cmd = args[1]

local function out(kind, t)
    local parts = { 'eco', kind }
    for _, kv in ipairs(t) do
        local v = kv[2]
        if type(v) == 'number' and v ~= math.floor(v) then v = ('%.3f'):format(v) end
        parts[#parts + 1] = kv[1] .. '=' .. tostring(v):gsub('[%s=]+', '_')
    end
    print(table.concat(parts, ' '))
end
local function fail(msg) print('eco error ' .. tostring(msg):gsub('\n', ' ')) end
local function tool()
    local ok, sw = pcall(reqscript, 'seasonal-wildlife')
    if ok and type(sw) == 'table' then return sw end
end
local function tick() return df.global.cur_year * 403200 + df.global.cur_year_tick end
local function tokOf(u) local c = df.creature_raw.find(u.race); return c and c.creature_id or '?' end
local function alive(u) return u and not dfhack.units.isDead(u) and not u.flags1.inactive and u.pos.x >= 0 end
local function citizens()
    local t = {}
    for _, u in ipairs(df.global.world.units.active) do if dfhack.units.isCitizen(u) and alive(u) then t[#t + 1] = u end end
    return t
end
local function cheb(a, b) return math.max(math.abs(a.x - b.x), math.abs(a.y - b.y)) + 2 * math.abs(a.z - b.z) end
local function nearest(u, list)
    local best
    for _, c in ipairs(list) do if c ~= u then local d = cheb(u.pos, c.pos); if not best or d < best then best = d end end end
    return best or -1
end
local function ensureMap()
    local key = df.global.plotinfo.site_id .. ':' .. df.global.world.map.x_count .. 'x' .. df.global.world.map.y_count
    if S7.map ~= key then S7.map, S7.spots, S7.marks, S7.perf = key, {}, {}, nil end
end

-- ------------------------------------------------------------------ tiles ----
local function tflags(x, y, z) return dfhack.maps.getTileFlags(x, y, z) end
local function walk(x, y, z, under)
    local t = dfhack.maps.getTileType(x, y, z); if not t then return false end
    local sa = df.tiletype_shape.attrs[df.tiletype.attrs[t].shape]
    if not sa.walkable then return false end
    if sa.basic_shape ~= df.tiletype_shape_basic.Floor and sa.basic_shape ~= df.tiletype_shape_basic.Ramp then return false end
    local d = tflags(x, y, z)
    if not d or d.flow_size >= 4 then return false end
    if under then return d.subterranean and not d.outside end
    return d.outside
end
local function wet(x, y, z)
    local d = tflags(x, y, z)
    return d and d.flow_size >= 4 and not d.liquid_type
end

-- SPOT -> x, y, z (cached per map so every step of a cell uses the same place)
local function resolve(spot)
    ensureMap()
    if S7.spots[spot] then return table.unpack(S7.spots[spot]) end
    local base, mode = spot:match('^([%w]+):?(%w*)$')
    mode = (mode ~= '' and mode) or 'shore'
    local X, Y, Z = dfhack.maps.getTileSize()
    local res
    if base == 'land' or base == 'shore' or base == 'water' then
        -- cx-eco's own spot finder, read off its receipt
        local lines = {}
        local oldprint = print
        print = function(s) lines[#lines + 1] = tostring(s) end
        local ok = pcall(dfhack.run_script, 'cx-eco', 'spot', base)
        print = oldprint
        for _, l in ipairs(lines) do
            local x, y, z = l:match('x=(%d+) y=(%d+) z=(%d+)')
            if ok and x then res = { tonumber(x), tonumber(y), tonumber(z) } end
        end
    elseif base == 'fort' then
        local c = citizens()[1]
        if c then res = { c.pos.x, c.pos.y, c.pos.z } end
    elseif base:match('^cav%d$') then
        local sw = tool()
        local d = tonumber(base:sub(4)) - 1
        local b = sw and sw.CAVE and sw.CAVE.band(d)
        if b then
            local best, bs
            local zs, mid = {}, (b.zlo + b.zhi) // 2   -- the band's middle first, then outward; stop at a good floor
            for k = 0, b.zhi - b.zlo do
                local z1, z2 = mid - k, mid + k
                if z1 >= b.zlo then zs[#zs + 1] = z1 end
                if k > 0 and z2 <= b.zhi then zs[#zs + 1] = z2 end
            end
            for _, z in ipairs(zs) do
                if bs and bs >= 60 then break end
                for y = 6, Y - 7, 6 do for x = 6, X - 7, 6 do
                    if walk(x, y, z, true) then
                        local n, w = 0, 0
                        for dy = -4, 4 do for dx = -4, 4 do
                            if walk(x + dx, y + dy, z, true) then n = n + 1 elseif wet(x + dx, y + dy, z) then w = w + 1 end
                        end end
                        local score = (mode == 'pool') and ((n >= 20 and w >= 12) and n + w or -1) or ((w == 0) and n or -1)
                        if score >= 40 and (not bs or score > bs) then best, bs = { x, y, z }, score end
                    end
                end end
            end
            res = best
        end
    else   -- a water body by the tool's own survey (ENGINE.waterTiles: ocean / lake / river / pool)
        local sw = tool()
        local wt = sw and sw.ENGINE and sw.ENGINE.waterTiles()
        if wt then
            local tiles, cx, cy, n = {}, 0, 0, 0
            for _, t in ipairs(wt.tiles or {}) do
                if t.body == base then tiles[#tiles + 1] = t; cx, cy, n = cx + t.x, cy + t.y, n + 1 end
            end
            if n > 0 then
                cx, cy = cx / n, cy / n
                local best, bs
                local step = math.max(1, #tiles // 300)   -- ~300 samples: well inside the 15 s lua deadline
                for i = 1, #tiles, step do
                    local t = tiles[i]
                    if mode == 'water' then
                        local w = 0
                        for dy = -3, 3 do for dx = -3, 3 do if wet(t.x + dx, t.y + dy, t.z) then w = w + 1 end end end
                        local score = w * 4 - (math.abs(t.x - cx) + math.abs(t.y - cy)) / 8
                        if w >= 30 and (not bs or score > bs) then best, bs = { t.x, t.y, t.z }, score end
                    else   -- shore: a walkable outside tile beside this water, on its level or one up
                        local done = false
                        for _, dz in ipairs({ 0, 1 }) do for dy = -1, 1 do for dx = -1, 1 do
                            local x, y, z = t.x + dx, t.y + dy, t.z + dz
                            if not done and walk(x, y, z, false) then
                                done = true
                                local w = 0
                                for yy = -2, 2 do for xx = -2, 2 do if walk(x + xx, y + yy, z, false) then w = w + 1 end end end
                                local score = w - (math.abs(x - cx) + math.abs(y - cy)) / 16
                                if w >= 12 and (not bs or score > bs) then best, bs = { x, y, z }, score end
                            end
                        end end end
                    end
                end
                res = best
            end
        end
    end
    if res then S7.spots[spot] = res; return table.unpack(res) end
    return nil
end

local function fill(s, x, y, z)
    return (tostring(s):gsub('<([XYZ])([+-]?%d*)>', function(c, off)
        local v = (c == 'X' and x) or (c == 'Y' and y) or z
        return tostring(v + (tonumber(off) or 0))
    end))
end

-- the tool group (g.groups) holding most of the spawned TOKEN
local function groupOf(sw, token)
    local spawned = (_G.CX_ECO or {}).spawned or {}
    local mine = {}
    for id, tok in pairs(spawned) do if tok == token then mine[id] = true end end
    local g = sw.loadGroups()
    local best, bn, bi
    for i, grp in ipairs(g.groups or {}) do
        local n = 0
        for _, id in ipairs(grp.ids or {}) do if mine[id] then n = n + 1 end end
        if n > 0 and (not bn or n > bn) then best, bn, bi = grp, n, i end
    end
    return best, g, bi
end

local function season_ticks()
    local yt = df.global.cur_year_tick
    local sl = 403200 // 4
    return sl - (yt % sl), (yt // sl)
end

-- ------------------------------------------------------------------ verbs ----
-- the whole dispatch runs under pcall: a Lua error over RPC never comes back (it lands in stderr.log and the call
-- waits out its deadline), so it is printed as 'eco error' and the H2 check that wanted a receipt fails at once
local function main()
ensureMap()
if cmd == 'facts' then
    local sw = tool()
    local X, Y, Z = dfhack.maps.getTileSize()
    local to_season, season = season_ticks()
    local cit = #citizens()
    local sav, evil = -1, -1
    -- the embark's own region tile (a 1x1 or 8x8 can draw from neighbours: memory df-region-draw-tiles; the tool's
    -- calm/savage cut reads this same tile)
    pcall(function()
        local site = df.world_site.find(df.global.plotinfo.site_id)
        local rx, ry = site.pos.x, site.pos.y
        local wd = df.global.world.world_data
        local rme
        local ok = pcall(function() rme = dfhack.maps.getRegionBiome(rx, ry) end)
        if not ok or not rme then rme = wd.region_map[rx]:_displace(ry) end
        sav, evil = rme.savagery, rme.evilness
    end)
    local rwe1, rwe2 = 'na', 'na'
    pcall(function() rwe1 = df.global.world.worldgen.worldgen_parms.real_world_extinct end)
    pcall(function() rwe2 = df.global.world.object_loader.param_real_world_extinct end)
    local r2 = dfhack.units.getBreathingState ~= nil
    local fet = dfhack.maps.forEachTile ~= nil
    local ver = 'na'; pcall(function() ver = dfhack.getDFHackVersion() end)
    out('facts', { { 'map', X .. 'x' .. Y .. 'x' .. Z }, { 'tick', tick() }, { 'year_tick', df.global.cur_year_tick },
        { 'season', season }, { 'to_season', to_season }, { 'citizens', cit }, { 'savagery', sav }, { 'evilness', evil },
        { 'rwe_param', rwe1 }, { 'rwe_loader', rwe2 }, { 'r2', tostring(r2) }, { 'forEachTile', tostring(fet) },
        { 'dfhack', ver }, { 'tool', sw and 'loaded' or 'missing' } })
    if not sw then return end
    local cfg = sw.loadConfig()
    -- water bodies, by the tool's own survey
    local ok, wt = pcall(sw.ENGINE.waterTiles, true)
    if ok and wt then
        for body, n in pairs(wt.sum or {}) do
            if body ~= 'salt' and body ~= 'fresh' then
                out('factbody', { { 'body', body }, { 'tiles', n }, { 'maxdepth', (wt.maxDepth or {})[body] or 0 } })
            end
        end
    end
    -- cavern bands: civ races (irruption candidates), predators (the fallback), animal people (R35), on the map now
    for d = 0, 2 do
        local b = sw.CAVE.band(d)
        local civ, pred, ap, units = 0, 0, {}, 0
        if b then
            local okc, c = pcall(sw.IRRUPT.candidates, cfg, d, true); if okc then civ = #c end
            local okp, p = pcall(sw.IRRUPT.candidates, cfg, d, false); if okp then pred = #p end
            pcall(function()
                for t, s in pairs(sw.V7.GRP.species(cfg)) do if s.person and s.natural and s.d and s.d[d] then ap[#ap + 1] = t end end
            end)
            for _, u in ipairs(df.global.world.units.active) do
                if alive(u) and u.pos.z >= b.zlo and u.pos.z <= b.zhi and dfhack.units.isWildlife(u) then units = units + 1 end
            end
        end
        local civtok = '-'
        pcall(function() local c = sw.IRRUPT.candidates(cfg, d, true); if c[1] then civtok = c[1].token end end)
        out('factcav', { { 'cavern', d + 1 }, { 'band', b and (b.zlo .. '-' .. b.zhi) or 'none' }, { 'civ', civ }, { 'civtok', civtok },
            { 'pred', pred }, { 'ap', #ap > 0 and table.concat(ap, ',') or '-' }, { 'wild_units', units } })
    end
    -- extinct: rows of the correction table whose species can arrive here (the R24 precondition)
    local inEmb, apex = {}, {}
    pcall(function()
        for _, e in ipairs(sw.buildPool(cfg)) do
            if e.inEmbark and sw.V7.EXTINCT.TAGS[e.token] then
                inEmb[#inEmb + 1] = e.token
                if (sw.classify(df.creature_raw.find(e.race or -1) or sw.MODEL.rawOf(e.token)).guild or '') == 'AL' then apex[#apex + 1] = e.token end
            end
        end
    end)
    out('factext', { { 'in_embark', #inEmb }, { 'apex', #apex }, { 'tokens', #inEmb > 0 and table.concat(inEmb, ',', 1, math.min(#inEmb, 12)) or '-' } })
    -- stocked entries the checks place from or need
    local want = { 'WOLF', 'DEER', 'WATER_BUFFALO', 'RABBIT', 'BIRD_EAGLE', 'BEAR_GRIZZLY', 'FISH_PIKE', 'RACCOON', 'JACKAL',
                   'CENOZOIC_SMILODON', 'MAGMA_CRAB' }
    local inpool = {}
    pcall(function() for _, e in ipairs(sw.buildPool(cfg)) do if e.inEmbark then inpool[e.token] = (e.quantity or 0) end end end)
    local parts = {}
    for _, t in ipairs(want) do parts[#parts + 1] = { t, inpool[t] or 'no' } end
    out('factpool', parts)

elseif cmd == 'spot' then
    local x, y, z = resolve(args[2] or 'land')
    if not x then return fail('no ' .. tostring(args[2]) .. ' spot on this map') end
    out('spot7', { { 'spot', args[2] }, { 'x', x }, { 'y', y }, { 'z', z } })

elseif cmd == 'at' then
    local x, y, z = resolve(args[2] or 'land')
    if not x then return fail('no ' .. tostring(args[2]) .. ' spot on this map') end
    local rest = {}
    for i = 3, #args do rest[#rest + 1] = fill(args[i], x, y, z) end
    local ok, err = pcall(dfhack.run_script, 'cx-eco', table.unpack(rest))
    if not ok then return fail('cx-eco ' .. tostring(rest[1]) .. ': ' .. tostring(err)) end

elseif cmd == 'mark' then
    local ids = {}
    for _, u in ipairs(df.global.world.units.active) do if alive(u) then ids[u.id] = true end end
    S7.marks[args[2] or 'm'] = { ids = ids, tick = tick() }
    out('mark', { { 'tag', args[2] or 'm' }, { 'tick', tick() } })

elseif cmd == 'skills' then
    local token, skn, tag, mk = args[2], args[3] or 'SNEAK', args[4] or '-', S7.marks[args[5] or 'pre']
    local sk = df.job_skill[skn]
    if not sk then return fail('no skill ' .. tostring(skn)) end
    local n, pre, new, atfloor = 0, 0, 0, 0
    for _, u in ipairs(df.global.world.units.active) do
        if alive(u) and tokOf(u) == token then
            n = n + 1
            local was = mk and mk.ids[u.id] and 'pre' or 'new'
            if was == 'pre' then pre = pre + 1 else new = new + 1 end
            local r = { rating = -1, floor = -1, rusty = -1, unused = -1, rust = -1, demo = -1 }
            pcall(function()
                for _, s in ipairs(u.status.current_soul.skills) do
                    if s.id == sk then
                        r = { rating = s.rating, floor = s.natural_skill_lvl, rusty = s.rusty, unused = s.unused_counter,
                              rust = s.rust_counter, demo = s.demotion_counter }
                    end
                end
            end)
            local okN, nom = pcall(dfhack.units.getNominalSkill, u, sk, true)
            if r.floor >= 0 and r.rating >= r.floor and r.floor > 0 then atfloor = atfloor + 1 end
            out('sk', { { 'tag', tag }, { 'id', u.id }, { 'token', token }, { 'was', was }, { 'rating', r.rating },
                { 'nominal', okN and nom or -1 }, { 'floor', r.floor }, { 'rusty', r.rusty }, { 'unused', r.unused },
                { 'rust', r.rust }, { 'demo', r.demo }, { 'soul', u.status.current_soul and 1 or 0 } })
        end
    end
    -- the caste half (NATURAL_SKILL in the raws) and the tool's own readback
    local sw, casteLv = tool(), {}
    pcall(function()
        for i, c in ipairs(df.global.world.raws.creatures.all) do
            if c.creature_id == token then
                for ci, cs in ipairs(c.caste) do casteLv[#casteLv + 1] = sw.V7.H.casteSkill(cs, sk) end
            end
        end
    end)
    out('skillsum', { { 'tag', tag }, { 'token', token }, { 'units', n }, { 'pre', pre }, { 'new', new }, { 'with_floor', atfloor },
        { 'caste_lv', #casteLv > 0 and table.concat(casteLv, ',') or '-' } })
    if sw then
        pcall(function()
            for _, r in ipairs(sw.V7.H.readback()) do
                if r.token == token then
                    out('readback', { { 'tag', tag }, { 'token', r.token }, { 'profile', r.profile }, { 'sneak', r.sneak },
                        { 'caste_ok', r.casteOk }, { 'castes', r.castes }, { 'unit_ok', r.unitOk }, { 'units', r.units }, { 'souls', r.souls } })
                end
            end
        end)
    end

elseif cmd == 'rustpush' or cmd == 'nofloor' then
    local token, sk, add = args[2], df.job_skill[args[3] or 'SNEAK'], tonumber(args[4]) or 200000
    local n = 0
    for _, u in ipairs(df.global.world.units.active) do
        if alive(u) and tokOf(u) == token then
            pcall(function()
                for _, s in ipairs(u.status.current_soul.skills) do
                    if s.id == sk then
                        if cmd == 'rustpush' then
                            s.unused_counter = s.unused_counter + add; s.rust_counter = s.rust_counter + add
                            s.demotion_counter = s.demotion_counter + add
                        else s.natural_skill_lvl = 0 end
                        n = n + 1
                    end
                end
            end)
        end
    end
    out(cmd, { { 'token', token }, { 'units', n } })

elseif cmd == 'grp' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local grp, g, gi = groupOf(sw, args[2])
    if not grp then
        out('grp', { { 'tag', args[3] or '-' }, { 'token', args[2] }, { 'found', 0 } }); return
    end
    local mem, cx, cy = {}, 0, 0
    for _, id in ipairs(grp.ids or {}) do local u = df.unit.find(id); if alive(u) then mem[#mem + 1] = u; cx, cy = cx + u.pos.x, cy + u.pos.y end end
    local n = #mem
    local maxd, meand, pair = 0, 0, 0
    if n > 0 then
        cx, cy = cx / n, cy / n
        for _, u in ipairs(mem) do
            local d = math.sqrt((u.pos.x - cx) ^ 2 + (u.pos.y - cy) ^ 2)
            meand = meand + d; if d > maxd then maxd = d end
        end
        meand = meand / n
        local np = 0
        for i = 1, n do for j = i + 1, n do pair = pair + math.max(math.abs(mem[i].pos.x - mem[j].pos.x), math.abs(mem[i].pos.y - mem[j].pos.y)); np = np + 1 end end
        if np > 0 then pair = pair / np end
    end
    local lu = grp.leader and df.unit.find(grp.leader)
    local male = lu and pcall(function() return lu.sex end) and lu.sex == 1 and 1 or 0
    local foll = 0
    for _, u in ipairs(mem) do if u.following and lu and u.following.id == lu.id then foll = foll + 1 end end
    out('grp', { { 'tag', args[3] or '-' }, { 'token', args[2] }, { 'found', 1 }, { 'gi', gi }, { 'label', grp.label or '-' },
        { 'leader', grp.leader or -1 }, { 'leader_alive', alive(lu) and 1 or 0 }, { 'leader_male', male },
        { 'lost', grp.leader_lost and grp.leader_lost.why or '-' }, { 'panic', grp.panic and 1 or 0 },
        { 'panic_moves', grp.panic and grp.panic.moves or 0 }, { 'members', n }, { 'following', foll },
        { 'spread_max', maxd }, { 'spread_mean', meand }, { 'pair_mean', pair }, { 'unled', grp.unled or '-' },
        { 'g_panics', g.panics or 0 }, { 'g_lost', g.leaders_lost or 0 } })

elseif cmd == 'killleader' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local grp = groupOf(sw, args[2])
    local lu = grp and grp.leader and df.unit.find(grp.leader)
    if not alive(lu) then out('kill', { { 'token', args[2] }, { 'killed', 0 }, { 'why', grp and 'no live leader' or 'no group' } }); return end
    lu.body.blood_count = 0
    out('kill', { { 'token', args[2] }, { 'killed', 1 }, { 'id', lu.id }, { 'x', lu.pos.x }, { 'y', lu.pos.y }, { 'z', lu.pos.z } })

elseif cmd == 'nat' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local tag = args[2] or '-'
    local cfg, g = sw.loadConfig(), sw.loadGroups()
    local L = { land = 0, water = 0, cavern = 0 }
    local cav, body = { [0] = 0, 0, 0 }, {}
    local apexLive = 0
    for _, grp in ipairs(g.groups or {}) do
        local live = 0
        for _, id in ipairs(grp.ids or {}) do if alive(df.unit.find(id)) then live = live + 1 end end
        if live > 0 then
            local k = grp.layer or 'land'
            L[k] = (L[k] or 0) + 1
            if k == 'cavern' and grp.depth and cav[grp.depth] then cav[grp.depth] = cav[grp.depth] + 1 end
            if k == 'water' then local b = grp.body or 'none'; body[b] = (body[b] or 0) + 1 end
            if grp.tag == 'apex' then apexLive = apexLive + 1 end
        end
    end
    -- natives the tool may not track: wild cavern units per band by population entry (one entry = one group, as H5)
    local nat = { [0] = {}, {}, {} }
    local lvl = { H = 0, C = 0, A = 0, x = 0 }
    local ext, drawnLand = 0, 0
    for _, u in ipairs(df.global.world.units.active) do
        if alive(u) and sw.WILD.onMap(u) then
            local lay = sw.WILD.layerOf(u)
            local p = u.animal.population
            if lay == 'cavern' then
                local d = sw.WILD.caveDepth(p.cave_id)
                if nat[d] then nat[d][p.cave_id .. ':' .. p.population_idx .. ':' .. u.race] = true end
            elseif lay == 'land' then
                local cr = df.creature_raw.find(u.race)
                local okc, cl = pcall(sw.classify, cr)
                local lv = okc and cl and sw.ROSTER.LEVEL[cl.guild or ''] or 'x'
                lvl[lv] = (lvl[lv] or 0) + 1
                if u.flags2.roaming_wilderness_population_source or u.flags2.roaming_wilderness_population_source_not_a_map_feature then
                    drawnLand = drawnLand + 1
                    if cr and sw.V7.EXTINCT.TAGS[cr.creature_id] then ext = ext + 1 end
                end
            end
        end
    end
    local function cnt(t) local n = 0; for _ in pairs(t) do n = n + 1 end; return n end
    local held = 0; for _ in pairs(sw.CACHE.capHeld or {}) do held = held + 1 end
    local ra = (g.rapex or {})['apex:land'] or {}
    local tot = lvl.H + lvl.C + lvl.A
    out('nat', { { 'tag', tag }, { 'tick', tick() }, { 'season', df.global.cur_season },
        { 'land', L.land }, { 'land_cap', sw.QUOTA.groupsFor(cfg, 'land') }, { 'water', L.water },
        { 'water_cap', sw.QUOTA.groupsFor(cfg, 'water') }, { 'cavern', L.cavern }, { 'cav_cap', sw.QUOTA.groupsFor(cfg, 'cavern') },
        { 'c1', cav[0] }, { 'c2', cav[1] }, { 'c3', cav[2] }, { 'n1', cnt(nat[0]) }, { 'n2', cnt(nat[1]) }, { 'n3', cnt(nat[2]) },
        { 'held', held }, { 'apex_live', apexLive }, { 'apex_seen', ra.seen or 0 }, { 'apex_total', ra.total or 0 },
        { 'H', lvl.H }, { 'C', lvl.C }, { 'A', lvl.A }, { 'carn_share', tot > 0 and (lvl.C + lvl.A) / tot or -1 },
        { 'drawn_land', drawnLand }, { 'extinct_drawn', ext } })
    for b, n in pairs(body) do out('natbody', { { 'tag', tag }, { 'body', b }, { 'groups', n } }) end
    -- the census per body: units per species (MIX1 drift against base weights is a desk step on these rows)
    pcall(function()
        for b, B in pairs(sw.V7.WAT.census(cfg, g)) do
            out('natwat', { { 'tag', tag }, { 'body', b }, { 'units', B.units }, { 'groups', B.groups }, { 'H', B.lv.H }, { 'C', B.lv.C },
                { 'A', B.lv.A }, { 'apex_groups', B.apexGroups }, { 'seeded', B.src.seeded }, { 'drawn', B.src.drawn } })
            for tok, s in pairs(B.sp) do out('natsp', { { 'tag', tag }, { 'body', b }, { 'token', tok }, { 'n', s.n }, { 'groups', s.groups } }) end
        end
    end)
    -- the cavern gate's hold: held species' raws should read FREQUENCY 1 (R44 manipulation check)
    local bad = 0
    for tok in pairs(sw.CACHE.capHeld or {}) do
        local okr, cr = pcall(sw.MODEL.rawOf, tok)
        if okr and cr and cr.frequency ~= 1 then bad = bad + 1 end
    end
    out('hold', { { 'tag', tag }, { 'held', held }, { 'held_not_1', bad }, { 'trim_undo', cnt(g.trim_undo or {}) } })

elseif cmd == 'trim' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local g = sw.loadGroups()
    S7.trim = S7.trim or {}
    for key in pairs(g.trim_undo or {}) do S7.trim[tonumber(key) or key] = true end   -- remember: trim_undo drops the gone
    local on, gone, n = 0, 0, 0
    for id in pairs(S7.trim) do
        n = n + 1
        local u = df.unit.find(tonumber(id) or -1)
        if alive(u) then on = on + 1 else gone = gone + 1 end
    end
    out('trim', { { 'tag', args[2] or '-' }, { 'trimmed', n }, { 'on_map', on }, { 'gone', gone } })

elseif cmd == 'civs' or cmd == 'irr' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local d = (tonumber(args[2]) or 1) - 1
    local tag = args[3] or '-'
    local cfg, g = sw.loadConfig(), sw.loadGroups()
    local s = sw.IRRUPT.state(g)
    local L = s.layers['c' .. d] or {}
    local ev = L.ev
    local cits = citizens()
    local acc = L.access
    if cmd == 'irr' then
        local alivec, dead, gone = 0, 0, 0
        for _, rec in pairs(ev and ev.units or {}) do
            local u = df.unit.find(rec.id)
            if alive(u) then alivec = alivec + 1 elseif u and dfhack.units.isDead(u) then dead = dead + 1 else gone = gone + 1 end
        end
        out('irr', { { 'tag', tag }, { 'cavern', d + 1 }, { 'phase', L.phase or '-' }, { 'pressure', sw.IRRUPT.pressure(g, d) },
            { 'waves', ev and ev.waves or 0 }, { 'alive', alivec }, { 'dead', dead }, { 'gone', gone },
            { 'agit', ev and ev.agit and #ev.agit or 0 }, { 'reasserted', ev and ev.reasserted or 0 }, { 'walks', ev and ev.walks or 0 },
            { 'citizens', #cits }, { 'events', s.stats.events or 0 } })
    end
    -- per unit: every civ-race unit in the band (irr: only the event's subjects), with each write read back
    local b = sw.CAVE.band(d)
    local civRace = {}
    pcall(function() for _, e in ipairs(sw.IRRUPT.candidates(cfg, d, true)) do civRace[e.craw.creature_id] = true end end)
    for _, u in ipairs(df.global.world.units.active) do
        local rec = ev and ev.units and ev.units[tostring(u.id)]
        local inBand = b and u.pos.z >= b.zlo and u.pos.z <= b.zhi
        if alive(u) and ((cmd == 'irr' and rec) or (cmd == 'civs' and (rec or (inBand and civRace[tokOf(u)])))) then
            local mask, cache = {}, {}
            for f in pairs((rec and rec.mask) or {}) do
                local ok, v = pcall(function() return u.uwss_add_caste_flag[f] end); mask[#mask + 1] = f .. ':' .. (ok and (v and 1 or 0) or 'na')
            end
            for f in pairs((rec and rec.cache) or {}) do
                local ok, v = pcall(function() return u.enemy.caste_flags[f] end); cache[#cache + 1] = f .. ':' .. (ok and (v and 1 or 0) or 'na')
            end
            local goal = df.unit_path_goal[u.path.goal] or tostring(u.path.goal)
            out(cmd == 'irr' and 'irru' or 'civ', { { 'tag', tag }, { 'id', u.id }, { 'token', tokOf(u) }, { 'x', u.pos.x }, { 'y', u.pos.y },
                { 'z', u.pos.z }, { 'subject', rec and 1 or 0 }, { 'tags', rec and table.concat(rec.tags or {}, ',') or '-' },
                { 'champ', rec and rec.champ and 1 or 0 }, { 'mask', #mask > 0 and table.concat(mask, ',') or '-' },
                { 'cache', #cache > 0 and table.concat(cache, ',') or '-' }, { 'hidden', u.flags1.hidden_in_ambush and 1 or 0 },
                { 'goal', goal }, { 'items', #u.inventory }, { 'mood', u.counters.soldier_mood }, { 'dcit', nearest(u, cits) },
                { 'dacc', acc and cheb(u.pos, { x = acc.x, y = acc.y, z = acc.z or u.pos.z }) or -1 },
                { 'leave', u.animal.leave_countdown } })
        end
    end

elseif cmd == 'native' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local d, token, tag = (tonumber(args[2]) or 1) - 1, args[3], args[4] or '-'
    local s = sw.IRRUPT.state(sw.loadGroups())
    local ev = (s.layers['c' .. d] or {}).ev
    local FL = { 'CURIOUS_BEAST', 'CURIOUS_BEAST_ITEM', 'MEANDERER', 'AMBUSHPREDATOR' }
    local n = 0
    for _, u in ipairs(df.global.world.units.active) do
        if alive(u) and (token == nil or token == '*' or tokOf(u) == token) and not (ev and ev.units and ev.units[tostring(u.id)]) then
            local cr = df.creature_raw.find(u.race)
            local okc, isCiv = pcall(sw.IRRUPT.isCiv, u.race)
            if okc and isCiv then
                local parts = { { 'tag', tag }, { 'id', u.id }, { 'token', tokOf(u) } }
                for _, f in ipairs(FL) do
                    local ok1, v1 = pcall(function() return u.enemy.caste_flags[f] end)
                    local ok2, v2 = pcall(function() return cr.caste[u.caste].flags[f] end)
                    parts[#parts + 1] = { f, (ok1 and (v1 and 1 or 0) or 'na') .. '/' .. (ok2 and (v2 and 1 or 0) or 'na') }
                end
                out('native', parts)
                n = n + 1
                if n >= 3 then break end
            end
        end
    end
    if n == 0 then out('native', { { 'tag', tag }, { 'id', -1 }, { 'why', 'no native civ unit outside the event' } }) end

elseif cmd == 'resid' then
    local MASK = { 'CRAZED', 'MISCHIEVOUS', 'NOFEAR', 'TRANCES' }
    local CF = { 'CURIOUS_BEAST', 'CURIOUS_BEAST_ITEM', 'MEANDERER', 'AMBUSHPREDATOR' }
    local m, c, enr, units = 0, 0, 0, 0
    for _, u in ipairs(df.global.world.units.active) do
        if alive(u) then
            local any = false
            for _, f in ipairs(MASK) do
                local ok, v = pcall(function() return u.uwss_add_caste_flag[f] end)
                if ok and v then m = m + 1; any = true end
            end
            local cr = df.creature_raw.find(u.race)
            for _, f in ipairs(CF) do
                local ok1, v1 = pcall(function() return u.enemy.caste_flags[f] end)
                local ok2, v2 = pcall(function() return cr.caste[u.caste].flags[f] end)
                if ok1 and ok2 and v1 and not v2 then c = c + 1; any = true end
            end
            if any then units = units + 1 end
        end
    end
    local sw = tool()
    local active = 0
    if sw then pcall(function() for _, L in pairs(sw.IRRUPT.state(sw.loadGroups()).layers) do if L.phase == 'active' then active = active + 1 end end end) end
    out('resid', { { 'tag', args[2] or '-' }, { 'mask', m }, { 'cache', c }, { 'units', units }, { 'active_events', active } })

elseif cmd == 'scav' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local tag = args[2] or '-'
    local st = sw.SCAV.state()
    for tok, b in pairs(st.stats.by or {}) do
        out('scavby', { { 'tag', tag }, { 'token', tok }, { 'visits', b.visits }, { 'kg', b.kg }, { 'finished', b.finished },
            { 'walks', b.walks }, { 'hops', b.hops }, { 'wet', b.wet } })
    end
    local n, kg, first = 0, 0, nil
    for _, r in pairs(st.rem or {}) do
        n = n + 1
        local okl, left = pcall(function() return r.left or r.kg or r.mass end)
        kg = kg + ((okl and tonumber(left)) or 0)
        local okf, f = pcall(function() return r.found or r.found_at end)
        if okf and tonumber(f) and (not first or f < first) then first = f end
    end
    local l = sw.CACHE.scavLast or {}
    out('scav', { { 'tag', tag }, { 'tick', tick() }, { 'remains', n }, { 'left_kg', kg }, { 'first_found', first or -1 },
        { 'moves', st.moves }, { 'hops', st.hops }, { 'pass', st.pass }, { 'last_units', l.units or -1 }, { 'last_eaten', l.eaten or -1 } })

elseif cmd == 'wat' or cmd == 'breath' then
    local tag = args[2] or '-'
    local f = dfhack.units.getBreathingState
    local nf = { dead = 0, inactive = 0, active = 0, total = 0 }
    local dry = 0
    local sw = tool()
    for _, u in ipairs(df.global.world.units.all) do
        if f then
            local ok, st = pcall(f, u)
            if ok and st ~= 2 then
                nf.total = nf.total + 1
                if dfhack.units.isDead(u) then nf.dead = nf.dead + 1 elseif u.flags1.inactive then nf.inactive = nf.inactive + 1 else nf.active = nf.active + 1 end
            end
        end
        if sw and alive(u) and sw.WILD.onMap(u) then
            local okc, cl = pcall(sw.classify, df.creature_raw.find(u.race))
            if okc and cl and cl.habitat == 'aquatic' and not sw.V7.GRP.wetAt(u.pos.x, u.pos.y, u.pos.z) then dry = dry + 1 end
        end
    end
    out(cmd == 'wat' and 'watguard' or 'breath', { { 'tag', tag }, { 'r2', f and 1 or 0 }, { 'not_fine', nf.total }, { 'nf_dead', nf.dead },
        { 'nf_inactive', nf.inactive }, { 'nf_active', nf.active }, { 'aquatic_dry', dry },
        { 'rescued', sw and (sw.CACHE.watGuard or {}).rescued or 0 }, { 'failed', sw and (sw.CACHE.watGuard or {}).failed or 0 },
        { 'rechecked', sw and (sw.CACHE.watGuard or {}).rechecked or 0 } })

elseif cmd == 'occ' then
    -- r2 changed teleport's occupancy bookkeeping (dfhack-r2 REPORT 1.1): a tile marked occupied with no standing unit,
    -- or two standing units on one tile, is the new readout trap. Checked on every tile an active unit stands on, and
    -- on the 5x5 around each spawned unit (where placement and the nudge teleport).
    local stand, pos = {}, {}
    for _, u in ipairs(df.global.world.units.active) do
        if alive(u) and not u.flags1.on_ground then
            local k = u.pos.x .. ',' .. u.pos.y .. ',' .. u.pos.z
            stand[k] = (stand[k] or 0) + 1
        end
    end
    local double = 0
    for _, n in pairs(stand) do if n >= 2 then double = double + 1 end end
    local ghost, seen = 0, 0
    local checked = {}
    for id in pairs((_G.CX_ECO or {}).spawned or {}) do
        local u = df.unit.find(id)
        if u and u.pos.x >= 0 then
            for dy = -2, 2 do for dx = -2, 2 do
                local x, y, z = u.pos.x + dx, u.pos.y + dy, u.pos.z
                local k = x .. ',' .. y .. ',' .. z
                if not checked[k] then
                    checked[k] = true
                    local b = dfhack.maps.getTileBlock(x, y, z)
                    if b then
                        seen = seen + 1
                        if b.occupancy[x % 16][y % 16].unit and not stand[k] then ghost = ghost + 1 end
                    end
                end
            end end
        end
    end
    out('occ', { { 'tag', args[2] or '-' }, { 'tiles', seen }, { 'ghost', ghost }, { 'double', double } })

elseif cmd == 'perf' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local tag = args[2] or '-'
    local now, ms = tick(), dfhack.getTickCount()
    local tps = -1
    if S7.perf and ms > S7.perf.ms then tps = (now - S7.perf.tick) * 1000 / (ms - S7.perf.ms) end
    S7.perf = { tick = now, ms = ms }
    local okf, stats = pcall(function() return sw.FUSE and sw.FUSE.stats end)
    if not okf or not stats then
        -- FUSE is not exported in every build: read it through fuseStatus' table if present
        okf, stats = pcall(function() return sw.CACHE.fuseStats end)
    end
    for name, st in pairs((okf and stats) or {}) do
        out('perfjob', { { 'tag', tag }, { 'job', name }, { 'runs', st.runs or 0 }, { 'ms_sum', st.ms_sum or 0 }, { 'worst', st.worst or 0 },
            { 'over', st.over or 0 }, { 'kb', st.kb or st.kb_last or -1 }, { 'deferred', st.deferred or 0 } })
    end
    local W = sw.CACHE.perfTickWorst or {}
    local e = df.global.enabler
    out('perf', { { 'tag', tag }, { 'tick', now }, { 'wall_ms', ms }, { 'tps', tps }, { 'worst_tick_ms', W.ms or -1 },
        { 'worst_jobs', W.jobs or '-' }, { 'fps_calc', e.calculated_fps }, { 'units', #df.global.world.units.active } })

elseif cmd == 'bench' then
    local ok, o = pcall(dfhack.run_command_silent, 'seasonal-wildlife', 'perf', 'bench', args[2] or '20')
    local i = 0
    for line in tostring(o):gmatch('[^\n]+') do
        i = i + 1
        out('benchraw', { { 'n', i }, { 'text', line:sub(1, 160) } })
    end
    out('bench', { { 'ok', ok and 1 or 0 }, { 'lines', i }, { 'failed', select(2, tostring(o):gsub('failed', '')) } })

elseif cmd == 'ledger' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local kind, tag = args[2], args[3] or '-'
    local since = S7.marks[args[4] or 'pre'] and S7.marks[args[4] or 'pre'].tick or 0
    local l = sw.LEDGER.load()
    local n, last = 0, '-'
    for _, e in ipairs(l.entries or {}) do
        if (kind == '*' or e.k == kind) and e.t >= since then n = n + 1; last = e.s end
    end
    out('ledger', { { 'tag', tag }, { 'kind', kind }, { 'n', n }, { 'last', last:sub(1, 120) } })

elseif cmd == 'tool' then
    local words = {}
    for i = 2, #args do words[#words + 1] = args[i] end
    local ok, o = pcall(dfhack.run_command_silent, 'seasonal-wildlife', table.unpack(words))
    local first = tostring(o):match('[^\n]+') or ''
    out('tool', { { 'verb', table.concat(words, '_') }, { 'ok', ok and 1 or 0 }, { 'out', first:sub(1, 120) } })

elseif cmd == 'pin' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local cav = tonumber(args[2]) or 1
    local cfg = sw.loadConfig()
    local ok = pcall(dfhack.run_command_silent, 'seasonal-wildlife', 'irruption', 'pin', tostring(cav), tostring(cfg.irruption.threshold))
    out('pin', { { 'cavern', cav }, { 'ok', ok and 1 or 0 }, { 'pressure', sw.IRRUPT.pressure(sw.loadGroups(), cav - 1) },
        { 'threshold', cfg.irruption.threshold } })

elseif cmd == 'citizens' then
    -- T-PR's pressure sources: citizens put in (or just above) a cavern band; 'knock' keeps them there
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local d, n, mode = (tonumber(args[2]) or 1) - 1, tonumber(args[3]) or 3, args[4] or 'in'
    local x, y, z = resolve('cav' .. (d + 1))
    if not x then return fail('no floor in cavern ' .. (d + 1)) end
    if mode == 'above' then z = (sw.CAVE.band(d).zhi or z) + 1 end
    local moved = 0
    for _, u in ipairs(citizens()) do
        if moved >= n then break end
        local tx, ty = x + moved, y
        if dfhack.units.teleport(u, xyz2pos(tx, ty, z)) then
            moved = moved + 1
            if mode == 'knock' or args[5] == 'knock' then u.counters.unconscious = 60000 end
        end
    end
    out('citizens', { { 'cavern', d + 1 }, { 'moved', moved }, { 'z', z }, { 'mode', mode } })

elseif cmd == 'dig' then
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local d, n = (tonumber(args[2]) or 1) - 1, tonumber(args[3]) or 10
    local x, y, z = resolve('cav' .. (d + 1))
    if not x then return fail('no floor in cavern ' .. (d + 1)) end
    local marked = 0
    for r = 1, 12 do
        for dy = -r, r do for dx = -r, r do
            if marked < n and (math.abs(dx) == r or math.abs(dy) == r) then
                local tx, ty = x + dx, y + dy
                local t = dfhack.maps.getTileType(tx, ty, z)
                local b = dfhack.maps.getTileBlock(tx, ty, z)
                if t and b and df.tiletype.attrs[t].shape == df.tiletype_shape.WALL and df.tiletype.attrs[t].material ~= df.tiletype_material.CONSTRUCTION then
                    b.designation[tx % 16][ty % 16].dig = df.tile_dig_designation.Default
                    b.flags.designated = true
                    marked = marked + 1
                end
            end
        end end
    end
    out('dig', { { 'cavern', d + 1 }, { 'marked', marked } })

elseif cmd == 'toolall' then
    -- every reply line of a verb (status tables: `hunters status`, `vermin eats`, `water depth full`, `perf`)
    local words = {}
    for i = 2, #args do words[#words + 1] = args[i] end
    local ok, o = pcall(dfhack.run_command_silent, 'seasonal-wildlife', table.unpack(words))
    local i = 0
    for line in tostring(o):gmatch('[^\n]+') do
        i = i + 1
        if i <= 60 then out('toolline', { { 'verb', table.concat(words, '_') }, { 'n', i }, { 'text', line:sub(1, 160) } }) end
    end
    out('tool', { { 'verb', table.concat(words, '_') }, { 'ok', ok and 1 or 0 }, { 'lines', i } })

elseif cmd == 'cfgset' then
    -- cfgset PATH VALUE [PATH VALUE ...]: write the tool's config the way its verbs do (loadConfig, set, saveConfig);
    -- 'true'/'false' are booleans, numbers are numbers. The H2 read-back is cx-eco cfg, not this echo.
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local c = sw.loadConfig()
    local n = 0
    for i = 2, #args - 1, 2 do
        local path, raw = args[i], args[i + 1]
        local v = (raw == 'true' and true) or (raw == 'false' and false) or tonumber(raw) or raw
        local t, keys = c, {}
        for k in path:gmatch('[^.]+') do keys[#keys + 1] = tonumber(k) or k end
        local ok = true
        for j = 1, #keys - 1 do
            if type(t[keys[j]]) ~= 'table' then ok = false; break end
            t = t[keys[j]]
        end
        if ok then t[keys[#keys]] = v; n = n + 1 else fail('cfgset: no table at ' .. path) end
    end
    sw.saveConfig(c)
    pcall(function() sw.CACHE.cfg = nil end)
    out('cfgset', { { 'written', n } })

elseif cmd == 'adj' then
    -- adj A B TAG: pairs of spawned A and B standing adjacent (Chebyshev 1, same level or one apart): FSH3's
    -- bear-fish adjacency ticks, one sample
    local spawned = (_G.CX_ECO or {}).spawned or {}
    local A, B = {}, {}
    for id, tok in pairs(spawned) do
        local u = df.unit.find(id)
        if alive(u) then if tok == args[2] then A[#A + 1] = u elseif tok == args[3] then B[#B + 1] = u end end
    end
    local pairs_, dmin = 0, -1
    for _, a in ipairs(A) do for _, b in ipairs(B) do
        local d = math.max(math.abs(a.pos.x - b.pos.x), math.abs(a.pos.y - b.pos.y))
        if math.abs(a.pos.z - b.pos.z) <= 1 and d <= 1 then pairs_ = pairs_ + 1 end
        local dd = d + 2 * math.abs(a.pos.z - b.pos.z)
        if dmin < 0 or dd < dmin then dmin = dd end
    end end
    out('adj', { { 'tag', args[4] or '-' }, { 'a', args[2] }, { 'b', args[3] }, { 'na', #A }, { 'nb', #B }, { 'pairs', pairs_ }, { 'dmin', dmin } })

elseif cmd == 'swim' then
    -- swim TOKEN TAG: each spawned TOKEN unit: wet tile, breathing state (r2), level; and how many are gone/dead
    local sw = tool()
    local f = dfhack.units.getBreathingState
    local n, wetn, bad, dead, gone = 0, 0, 0, 0, 0
    for id, tok in pairs(((_G.CX_ECO or {}).spawned) or {}) do
        if tok == args[2] then
            local u = df.unit.find(id)
            if not u or u.pos.x < 0 or u.flags1.inactive then gone = gone + 1
            elseif dfhack.units.isDead(u) then dead = dead + 1
            else
                n = n + 1
                local w = sw and sw.V7.GRP.wetAt(u.pos.x, u.pos.y, u.pos.z) or wet(u.pos.x, u.pos.y, u.pos.z)
                if w then wetn = wetn + 1 end
                if f then local ok, st = pcall(f, u); if ok and st ~= 2 then bad = bad + 1 end end
            end
        end
    end
    out('swim', { { 'tag', args[3] or '-' }, { 'token', args[2] }, { 'alive', n }, { 'wet', wetn }, { 'not_fine', bad },
        { 'dead', dead }, { 'gone', gone } })

elseif cmd == 'corpses' then
    -- corpses TOKEN: every spawned TOKEN dies where it stands (blood drained, corpse kept), as cx-eco corpse does by id
    local S = (_G.CX_ECO or {}).spawned or {}
    local n = 0
    for id, tok in pairs(S) do
        if tok == args[2] then
            local u = df.unit.find(id)
            if u then u.body.blood_count = 0; n = n + 1 end
            S[id] = nil
        end
    end
    out('corpse', { { 'token', args[2] }, { 'drained', n } })

elseif cmd == 'gsize' then
    -- gsize TOKEN TAG: live members of every tool group of TOKEN (T-R35: animal-people wave sizes)
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local sizes = {}
    for _, grp in ipairs(sw.loadGroups().groups or {}) do
        if grp.token == args[2] then
            local live = 0
            for _, id in ipairs(grp.ids or {}) do if alive(df.unit.find(id)) then live = live + 1 end end
            sizes[#sizes + 1] = live .. (grp.irruption and 'i' or '')
        end
    end
    out('gsize', { { 'tag', args[3] or '-' }, { 'token', args[2] }, { 'groups', #sizes }, { 'sizes', #sizes > 0 and table.concat(sizes, ',') or '-' } })

elseif cmd == 'subjects' then
    -- subjects D goal|kill: a harness write on every live subject of cavern D's event. goal: the steal goal alone
    -- (M6: theft by goal without the caste or cache writes); kill: blood drained (T-END's repel, standing in for a squad)
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local d = (tonumber(args[2]) or 1) - 1
    local ev = (sw.IRRUPT.state(sw.loadGroups()).layers['c' .. d] or {}).ev
    local n = 0
    for _, rec in pairs(ev and ev.units or {}) do
        local u = df.unit.find(rec.id)
        if alive(u) then
            if args[3] == 'kill' then u.body.blood_count = 0
            else pcall(function() u.path.goal = df.unit_path_goal.WildernessCuriousStealTarget end) end
            n = n + 1
        end
    end
    out('subjects', { { 'cavern', d + 1 }, { 'write', args[3] or 'goal' }, { 'units', n } })

elseif cmd == 'packs' then
    -- packs TOKEN TAG: R41's pack recognition over the spawned TOKEN hunters (V7.H.packSizes), no group adopted
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local preds = {}
    for id, tok in pairs(((_G.CX_ECO or {}).spawned) or {}) do
        local u = df.unit.find(id)
        if tok == args[2] and alive(u) then preds[#preds + 1] = u end
    end
    local ok, sizes = pcall(sw.V7.H.packSizes, sw.loadConfig(), sw.loadGroups(), preds)
    local st = sw.CACHE.packStat   -- packSizes leaves its tally here (tracked, inferred, largest, units)
    local largest = 0
    if ok and type(sizes) == 'table' then for _, s in pairs(sizes) do if s > largest then largest = s end end end
    out('packs', { { 'tag', args[3] or '-' }, { 'token', args[2] }, { 'units', #preds }, { 'ok', ok and 1 or 0 }, { 'largest', largest },
        { 'inferred', type(st) == 'table' and st.inferred or -1 }, { 'tracked', type(st) == 'table' and st.tracked or -1 } })

elseif cmd == 'ap1' then
    -- ap1 N: AP1's desk half (roster.md): N in-memory land builds at ap_pick 0.1 and at 1 (a deep copy of the config,
    -- never saved), counting animal people (*_MAN, or a person by the groups stream's root test) and giants seated.
    -- Run over `cmd` (CX_RPC_TIMEOUT 300): a build walks the pool, too slow for the 15 s lua deadline at N > 2.
    local sw = tool(); if not sw then return fail('tool not loaded') end
    local utils = require('utils')
    local N = tonumber(args[2]) or 10
    for _, pick in ipairs({ 0.1, 1 }) do
        local seats, ap, giant, fails = 0, 0, 0, 0
        for i = 1, N do
            local c = utils.clone(sw.loadConfig(), true)
            c.roster.ap_pick = pick
            local ok, r = pcall(sw.ROSTER.build, c, 'land')
            if ok and type(r) == 'table' and r.ok then
                for k in pairs(r.ladder or {}) do
                    local tok = tostring(k):match('([^:]+)$') or tostring(k)
                    seats = seats + 1
                    if tok:match('_MAN$') then ap = ap + 1 end
                    if tok:match('^GIANT_') then giant = giant + 1 end
                end
            else fails = fails + 1 end
        end
        out('ap1', { { 'ap_pick', pick }, { 'builds', N }, { 'fails', fails }, { 'seats', seats }, { 'ap', ap },
            { 'ap_share', seats > 0 and ap / seats or -1 }, { 'giant', giant } })
    end

else
    fail('unknown verb ' .. tostring(cmd) .. ' (see the header of cx-sec7.lua)')
end
end

local ok, err = pcall(main)
if not ok then fail(tostring(cmd) .. ': ' .. tostring(err)) end
