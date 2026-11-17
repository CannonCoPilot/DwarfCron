-- data/pacing/probe.lua -- one checkpoint of seasonal-wildlife's pacing, per layer (v8.1 pacing plan step 1, 16 Nov 2026).
-- Read-only. Prints one JSON line:
--   t, year, season, day           absolute tick, calendar
--   layers[]  {lk, n, cap, pause, next}           the tool's own layer state (V7.UI.state), as the window shows it
--   groups[]  {id, tok, lk, arr, src, tag, n}     every non-seeded group the tool tracks; src = df | draw | place |
--                                                 irruption | adopt | native (id = the group's lowest unit id)
--   gated     {surface, cavern}                   units still flagged roaming_wilderness_population_source (DF's gate)
--   wild      {<layer>: n}                        wild units on the map by the tool's own layer reading (raw walk)
--   casts     {<layer>: [tokens]}                 this season's cast members per layer (castsView), hidden layers out
local json = require('json')
local sw = reqscript('seasonal-wildlife')
local cfg = sw.loadConfig()
local out = { t = df.global.cur_year * 403200 + df.global.cur_year_tick, year = df.global.cur_year,
              season = df.global.cur_season, day = math.floor((df.global.cur_year_tick % 100800) / 1200) + 1 }
out.layers = {}
local ok, st = pcall(sw.V7.UI.state, cfg)
if ok and st then
    for _, r in ipairs(st.layers or {}) do
        out.layers[#out.layers + 1] = { lk = r.lk, n = r.n, cap = r.cap, pause = r.pause and r.pause.on or false, next = r.next }
    end
end
out.groups = {}
local g = sw.loadGroups()
for _, grp in ipairs(g.groups or {}) do
    if not grp.seeded then
        local src = grp.irruption and 'irruption' or grp.drawn and 'draw' or grp.placed and 'place' or grp.adopted and 'adopt'
                    or grp.native and 'native' or 'df'
        local id = math.huge
        for _, i in ipairs(grp.ids or {}) do if i < id then id = i end end
        out.groups[#out.groups + 1] = { id = id, tok = grp.token, lk = sw.V7.GRP.lk(grp) or '?', arr = grp.arrived or -1, src = src,
                                        tag = grp.tag, n = #(grp.ids or {}) }
    end
end
out.gated, out.wild = { surface = 0, cavern = 0 }, {}
for _, u in ipairs(df.global.world.units.active) do
    if not dfhack.units.isDead(u) and dfhack.units.isActive(u) then
        if u.flags2.roaming_wilderness_population_source then
            local cave = u.animal.population.cave_id
            if cave == -1 then out.gated.surface = out.gated.surface + 1 else out.gated.cavern = out.gated.cavern + 1 end
        end
        if dfhack.units.isWildlife(u) then
            local okL, L = pcall(sw.WILD.layerOf, u)
            L = okL and L or '?'
            out.wild[L] = (out.wild[L] or 0) + 1
        end
    end
end
-- B2 (17 Nov 2026): the casts once per season (castsView live is the probe's heaviest read; B1's evil fort froze 3 times
-- under the probe and not without it). Kept in _G across calls, keyed by year and season.
local ck = df.global.cur_year * 4 + df.global.cur_season
local C = rawget(_G, '__pacing_probe_casts')
if C and C.k == ck then out.casts = C.casts; print(json.encode(out)); return end
out.casts = {}
local okV, v = pcall(sw.ROSTER.castsView, cfg, { live = true })
if okV and v then
    for _, c in ipairs(v.casts or {}) do
        if c.season == df.global.cur_season and not c.hidden then
            local m = {}
            for _, x in ipairs(c.members or {}) do m[#m + 1] = x.t end
            out.casts[c.layer] = m
        end
    end
end
rawset(_G, '__pacing_probe_casts', { k = ck, casts = out.casts })
print(json.encode(out))
