-- seasonal-wildlife-web.lua -- the browser companion's server: the tool's state as JSON, its control registry, and its
-- console verbs over HTTP on this machine only. v6.8.0 (29 Sep 2026; the user asked for a browser GUI layer);
-- v7.1 (web stream, R54, 1 Oct 2026): controls every v7.0+ feature through seasonal-wildlife-controls.
--@ module = true
--[====[

seasonal-wildlife-web
=====================

Serve the seasonal-wildlife companion page to a browser on this machine.

Usage::

    seasonal-wildlife-web start [port]   serve on 127.0.0.1 (default port 8642) and print the page's address
    seasonal-wildlife-web stop           stop serving
    seasonal-wildlife-web status         the address, requests served, and what each costs the game
    seasonal-wildlife-web snapshot       print the state the page reads, as JSON

Open the printed address (it carries a token) in any browser on this machine. The page reads the fort's wildlife
state every two seconds, the control registry when the config changes, and each subsystem's status lines every few
seconds while its section is open. Every change goes through the control registry (seasonal-wildlife-controls):
checked against the control's type and range, then sent as the tool's own console verb, so everything the page does
can also be typed. Only 127.0.0.1 is served, only the tool's own verbs are accepted (never Lua), and every request
but the page itself needs the token.

]====]

local sw = reqscript('seasonal-wildlife')
local C = reqscript('seasonal-wildlife-controls')
local json = require('json')
local repeatUtil = require('repeat-util')

-- One server per DF process, whichever copy of this script is running (a verb and a job run separate copies):
-- the socket, the token and the cached state live in _G.
local W = _G.SW_WEB or { port = 8642 }
_G.SW_WEB = W
W.stats = W.stats or {}
for _, k in ipairs({ 'requests', 'commands', 'errors', 'last_ms', 'worst_ms', 'snap_ms', 'snap_worst', 'rejected',
                     'sets', 'status_ms', 'status_worst', 'static_ms', 'stalled', 'deferred', 'req_worst' }) do W.stats[k] = W.stats[k] or 0 end

local TIMER = 'seasonal-wildlife-web'
local POLL_FRAMES = 5          -- about ten polls a second at 50 fps; an idle poll is one non-blocking accept
local SNAP_TTL_MS = 2000       -- the page polls every 2 s; a snapshot is built at most this often
local STATUS_TTL_MS = 5000     -- a status section is rebuilt at most this often (the engine's own status readers)
local CONTROLS_TTL_MS = 10000  -- the registry is rebuilt on a config change, or this often (feature probes)
local MAX_ACCEPTS = 4          -- requests handled per poll, so a burst cannot stall a frame
local POLL_BUDGET_MS = 50      -- no further request is taken in a poll once this much of the frame is spent (fail fast)
local READ_LINE_MS = 100       -- the socket's per-receive wait; loopback sends a request at once
local READ_BUDGET_MS = 300     -- a request's line and headers must arrive within this, or the client is dropped
local ERROR_LIMIT = 20         -- polls in a row whose every request failed before the server stops itself (fail fast)

local SEASONS = { [0] = 'Spring', 'Summer', 'Autumn', 'Winter' }
local MONTHS = { [0] = 'Granite', 'Slate', 'Felsite', 'Hematite', 'Malachite', 'Galena', 'Limestone', 'Sandstone',
                 'Timber', 'Moonstone', 'Opal', 'Obsidian' }

local function nowMs() return dfhack.getTickCount() end

--========================================================================================
-- the snapshot
--========================================================================================
-- Vermin are not units and never hunt; DF's vermin hunters are the species HUNT gives a flag to (v6.6: predatory
-- and water birds dive, small land and semiaquatic predators hunt). Which vermin family each can take, by habitat:
local VERMIN_EATEN_BY = {
    waterbird   = { fish = true, fliers = true, crawlers = true },
    flier       = { fliers = true, mammals = true, crawlers = true },
    land        = { mammals = true, crawlers = true, soil = true, fliers = true },
    semiaquatic = { mammals = true, crawlers = true, fish = true },
}
local function huntsVermin(p, v, famOf)
    if not sw.HUNT.wants(p) then return false end
    if (p.layer == 'cavern') ~= (v.layer == 'cavern') then return false end   -- one realm, as the food web
    local can = VERMIN_EATEN_BY[p.habitat or 'land']
    return can and can[famOf(v)] or false
end

-- The pool, its food web and every pool-derived species field change only when the config does (CACHE.ver) or the
-- embark's regions do; they are the expensive part (buildPool ~50 ms on a big fort, the pairs O(n^2)), so they are
-- kept until the config moves or 30 s pass. Guild, slot, pyramid level and roster part are the builder's reading of
-- each entry (ROSTER.slotOf / LEVEL / inPart); scavenger and gobble classes are SCAV.is and the edge table.
local PARTS = { 'land', 'flying', 'water', 'cavern' }
local function poolAndPairs(cfg)
    local c = W.poolCache
    if c and c.ver == sw.CACHE.ver and nowMs() - c.at < 30000 then return c.pool, c.pairs, c.derived end
    local pool = sw.buildPool(cfg)
    local famByToken = {}
    local function famOf(e)
        if e.cat ~= 'vermin' then return nil end
        if famByToken[e.token] == nil then
            local cr = df.creature_raw.find(e.idx)
            famByToken[e.token] = cr and sw.VERMIN.family(cr) or 'crawlers'
        end
        return famByToken[e.token]
    end
    -- the builder's vermin edge table, by consumer token (empty until `roster build` or `roster gobble` has run)
    local gob = {}
    for _, t in pairs(sw.CACHE.gobbleEdges or {}) do
        for _, ed in ipairs((type(t) == 'table' and t.edges) or {}) do
            if ed.consumer and ed.vclass then
                gob[ed.consumer] = gob[ed.consumer] or {}
                gob[ed.consumer][ed.vclass] = true
            end
        end
    end
    local R = sw.ROSTER
    local managed, derived = {}, {}
    for _, e in ipairs(pool) do
        if e.inEmbark and not e.locked then
            managed[#managed + 1] = e
            local d = { family = famOf(e) }
            if e.cat ~= 'vermin' then
                pcall(function()
                    for _, p in ipairs(PARTS) do if R.inPart(cfg, e, p) then d.part = p; break end end
                    local slot = R.slotOf(cfg, e, d.part or e.layer)
                    d.guild, d.slot, d.level, d.tier = e.guild, slot, R.LEVEL[slot] or 'H', R.TIER[slot] or 1
                end)
                local cr = df.creature_raw.find(e.idx)
                if cr then local ok, s = pcall(sw.SCAV.is, cr, cfg); d.scav = ok and s and true or false end
                if gob[e.token] then local l = {}; for k in pairs(gob[e.token]) do l[#l + 1] = k end; table.sort(l); d.gobble = l end
                d.ap, d.giant, d.sentient = e.animalPerson or e.ap or false, e.giant or false, e.sentient or false
                d.extinct = (sw.V7.EXTINCT and sw.V7.EXTINCT.TAGS and sw.V7.EXTINCT.TAGS[e.token]) and true or false
            end
            derived[e.key] = d
        end
    end
    local pairs_ = {}
    for _, p in ipairs(managed) do
        if p.cat == 'predator' then
            for _, q in ipairs(managed) do
                if q ~= p then
                    if q.cat == 'vermin' then
                        if huntsVermin(p, q, famOf) then pairs_[#pairs_ + 1] = { p.key, q.key, 'v' } end
                    elseif sw.eats(p, q) then pairs_[#pairs_ + 1] = { p.key, q.key } end
                end
            end
        end
    end
    W.poolCache = { ver = sw.CACHE.ver, at = nowMs(), pool = managed, pairs = pairs_, derived = derived }
    return managed, pairs_, derived
end


--========================================================================================
-- creature tiles: DF's Steam sprites (graphics raws) and its ASCII glyph (font + palette)
--========================================================================================
-- Read once per DF install, at `start`: every TILE_PAGE (file, tile size, sheet size) and, per creature, the image
-- DF draws for it -- DEFAULT, else VERMIN, else the DEFAULT layer set's BODY layer, else ANIMATED -- and its
-- LIST_ICON. Paths are relative to DF's directory (DFHack's working directory). Only vanilla's graphics are read.
local function listdir(p) local ok, t = pcall(dfhack.filesystem.listdir, p); return ok and t or {} end
local function readAll(p) local f = io.open(p, 'rb'); if not f then return nil end; local t = f:read('*a'); f:close(); return t end
local function split(t) local o = {}; for x in (t .. ':'):gmatch('([^:]*):') do o[#o + 1] = x end; return o end
local function pngSize(p)   -- width, height from the IHDR chunk
    local b = readAll(p); if not b or #b < 24 then return nil end
    local function u32(i) local a, c, d, e = b:byte(i, i + 3); return ((a * 256 + c) * 256 + d) * 256 + e end
    return u32(17), u32(21)
end
local function loadGfx()
    local t0 = nowMs()
    local G = { pages = {}, tiles = {}, dirs = {} }
    for _, mod in ipairs(listdir('data/vanilla')) do
        if tostring(mod):match('_graphics$') then G.dirs[#G.dirs + 1] = 'data/vanilla/' .. mod .. '/graphics' end
    end
    local RANK = { DEFAULT = 0, VERMIN = 1, BODY = 2, ANIMATED = 3 }
    local function rect(p, i)
        if p[i + 1] == 'LARGE_IMAGE' and tonumber(p[i + 5]) then return { p[i], tonumber(p[i + 2]), tonumber(p[i + 3]), tonumber(p[i + 4]), tonumber(p[i + 5]) } end
        if tonumber(p[i + 1]) and tonumber(p[i + 2]) then return { p[i], tonumber(p[i + 1]), tonumber(p[i + 2]), tonumber(p[i + 1]), tonumber(p[i + 2]) } end
    end
    for _, dir in ipairs(G.dirs) do
        for _, f in ipairs(listdir(dir)) do
            f = tostring(f)
            local text = f:match('%.txt$') and readAll(dir .. '/' .. f)
            if text and f:match('^tile_page_') then
                local cur
                for tag in text:gmatch('%[([^%]]+)%]') do
                    local p = split(tag)
                    if p[1] == 'TILE_PAGE' then cur = { name = p[2], dir = dir }; G.pages[p[2]] = cur
                    elseif cur and p[1] == 'FILE' then cur.file = dir .. '/' .. p[2]
                    elseif cur and p[1] == 'TILE_DIM' then cur.tw, cur.th = tonumber(p[2]), tonumber(p[3])
                    elseif cur and p[1] == 'PAGE_DIM_PIXELS' then cur.w, cur.h = tonumber(p[2]), tonumber(p[3]) end
                end
            elseif text and f:match('^graphics_creatures') and not f:match('statue') and not f:match('portrait') then
                local cur, layerset
                for tag in text:gmatch('%[([^%]]+)%]') do
                    local p = split(tag)
                    local k = p[1]
                    if k == 'CREATURE_GRAPHICS' or k == 'CREATURE_CASTE_GRAPHICS' then
                        cur = G.tiles[p[2]] or {}; G.tiles[p[2]] = cur; layerset = nil
                    elseif k:match('CREATURE_GRAPHICS$') then cur = nil
                    elseif cur then
                        if k == 'LAYER_SET' then layerset = p[2]
                        elseif k == 'LIST_ICON' and tonumber(p[3]) then cur.ip, cur.ix, cur.iy = p[2], tonumber(p[3]), tonumber(p[4])
                        else
                            local kind = ((k == 'DEFAULT' or k == 'VERMIN' or k == 'ANIMATED') and not layerset and k)
                                      or (k == 'LAYER' and p[2] == 'BODY' and layerset == 'DEFAULT' and 'BODY') or nil
                            local r = kind and rect(p, kind == 'BODY' and 3 or 2)
                            if r and RANK[kind] < (cur.rank or 9) then
                                cur.rank, cur.p, cur.x, cur.y, cur.w, cur.h = RANK[kind], r[1], r[2], r[3], r[4] - r[2] + 1, r[5] - r[3] + 1
                            end
                        end
                    end
                end
            end
        end
    end
    local init = readAll('prefs/init.txt') or ''
    G.fontFile = 'data/art/' .. (init:match('%[FONT:([^%]]+)%]') or 'curses_640x300.png')
    local fw, fh = pngSize(G.fontFile)
    G.font = { url = '/gfx/font', gw = fw and fw // 16 or 8, gh = fh and fh // 16 or 12 }
    G.palette = {}
    local ok = pcall(function()
        for i = 0, 15 do
            local c = df.global.enabler.ccolor[i]
            G.palette[i + 1] = ('#%02x%02x%02x'):format(math.floor(c[0] * 255 + 0.5), math.floor(c[1] * 255 + 0.5), math.floor(c[2] * 255 + 0.5))
        end
    end)
    if not ok or #G.palette < 16 then   -- the install's colors.txt, in DF's colour order
        G.palette = {}
        local txt = readAll('data/init/colors.txt') or ''
        for _, c in ipairs({ 'BLACK', 'BLUE', 'GREEN', 'CYAN', 'RED', 'MAGENTA', 'BROWN', 'LGRAY', 'DGRAY', 'LBLUE', 'LGREEN', 'LCYAN', 'LRED', 'LMAGENTA', 'YELLOW', 'WHITE' }) do
            local r, g, b = txt:match('%[' .. c .. '_R:(%d+)%]'), txt:match('%[' .. c .. '_G:(%d+)%]'), txt:match('%[' .. c .. '_B:(%d+)%]')
            G.palette[#G.palette + 1] = r and ('#%02x%02x%02x'):format(tonumber(r), tonumber(g), tonumber(b)) or '#c0c0c0'
        end
    end
    G.pagesOut = {}
    for name, pg in pairs(G.pages) do
        if pg.file and pg.w then G.pagesOut[name] = { url = '/gfx/p/' .. name, w = pg.w, h = pg.h, tw = pg.tw or 32, th = pg.th or 32 } end
    end
    local n = 0; for _ in pairs(G.tiles) do n = n + 1 end
    G.ms, G.count = nowMs() - t0, n
    return G
end
local function gfx()
    if not W.gfx then W.gfx = loadGfx() end
    return W.gfx
end

local function seasonsOf(cfg, key)
    local out = {}
    for _, s in ipairs(cfg.assign[key] or {}) do out[#out + 1] = s end
    return out
end

local function fortName(site)
    if not site then return '?' end
    for _, f in ipairs({ function() return dfhack.translation.translateName(site.name, true) end,   -- DFHack 51+
                         function() return dfhack.TranslateName(site.name, true) end }) do
        local ok, v = pcall(f)
        if ok and type(v) == 'string' and v ~= '' then return v end
    end
    return '?'
end

-- P12 (perf analysis): a species' static fields (name, ASCII glyph, diet flags, sprite) never change within a loaded
-- world, so they are read once per creature per world, not every 2 s. The world is told apart by its creature count
-- and site; a reload of another world drops the table.
local function staticFor(idx, token, G)
    local wkey = ('%d:%d'):format(#df.global.world.raws.creatures.all, df.global.plotinfo.site_id)
    if W.staticKey ~= wkey then W.static, W.staticKey = {}, wkey end
    local s = W.static[idx]
    if s then return s end
    local t0 = nowMs()
    s = {}
    local cr = df.creature_raw.find(idx)
    if cr then
        s.name = cr.name[0]
        pcall(function() s.ascii = { ch = cr.creature_tile, fg = cr.color[0], bg = cr.color[1], br = cr.color[2] } end)
        s.diet = { carnivore = sw.hasCasteFlag(cr, 'CARNIVORE') and true or false, bonecarn = sw.hasCasteFlag(cr, 'BONECARN') and true or false,
                   grazer = sw.hasCasteFlag(cr, 'GRAZER') and true or false }
    end
    local t = G.tiles[token]
    if t and t.p then s.gfx = { p = t.p, x = t.x, y = t.y, w = t.w, h = t.h, ip = t.ip, ix = t.ix, iy = t.iy } end
    W.static[idx] = s
    W.stats.static_ms = W.stats.static_ms + (nowMs() - t0)
    return s
end

-- opts.live_only (web2: the offline harness's fake world, which has no population table or raws to pool): the
-- moving part only -- date, groups, limits, wild counts, jobs, ledger -- with no species, pairs or sprites
local function snapshot(opts)
    local t0 = nowMs()
    if not dfhack.isMapLoaded() then return { tool = 'seasonal-wildlife', web = 2, loaded = false } end
    local liveOnly = opts and opts.live_only
    local cfg = C.cfgRO()                         -- P7: the shared config, read-only; never mutated here
    local tp = nowMs()
    local pool, pairs_, derived
    if liveOnly then pool, pairs_, derived = {}, {}, {} else pool, pairs_, derived = poolAndPairs(cfg) end
    tp = nowMs() - tp
    local tc = nowMs()
    local season = df.global.cur_season
    -- stock: every managed population entry on the site's regions, summed per key (the Roster's rule)
    local stock, all = {}, df.global.world.populations.all
    for _, r in ipairs(liveOnly and {} or sw.CACHE.managedPops()) do
        local pop = all[r.i]
        if pop and pop.race == r.race then stock[r.key] = (stock[r.key] or 0) + pop.quantity end
    end
    -- who is on the map, and in which tracked group
    local g = sw.loadGroups()
    local tracked = {}
    for _, grp in ipairs(g.groups) do for _, id in ipairs(grp.ids) do tracked[id] = grp end end
    local onMap, wild = {}, { land = 0, water = 0, cavern = 0, deep = 0 }
    local untracked = {}
    for _, u in ipairs(df.global.world.units.active) do
        if sw.WILD.onMap(u) then
            local l = sw.WILD.layerOf(u)
            wild[l] = (wild[l] or 0) + 1
            local cr = df.creature_raw.find(u.race)
            local key = sw.keyFor(l, cr and cr.creature_id or '?')
            onMap[key] = (onMap[key] or 0) + 1
            if not tracked[u.id] and l ~= 'deep' then
                local o = sw.WILD.origin(u, tracked)
                local k = key .. '|' .. o
                untracked[k] = untracked[k] or { key = key, n = 0, origin = o }
                untracked[k].n = untracked[k].n + 1
            end
        end
    end
    tc = nowMs() - tc
    local tg = nowMs()
    local species, G = {}, liveOnly and { pagesOut = {}, font = {}, palette = {} } or gfx()
    tg = nowMs() - tg
    local tsp = nowMs()
    for _, e in ipairs(pool) do
        local st = staticFor(e.idx, e.token, G)
        local d = derived[e.key] or {}
        local cr = df.creature_raw.find(e.idx)
        local gs = (cfg.group_size or {})[e.key]
        -- cluster_number is {MAX, MIN}: the engine reads [0] as the most and [1] as the fewest (engine classify, 1525);
        -- web 1 had them the other way round (web-cluster-order bug). Ordered here whatever a mod wrote.
        local c0, c1 = cr and cr.cluster_number[0] or 1, cr and cr.cluster_number[1] or 1
        local sp = {
            key = e.key, token = e.token, name = st.name or e.token, layer = e.layer, habitat = e.habitat or 'land',
            role = e.cat, band = e.size, active = sw.isAllowed(cfg, e) and true or false, seasons = seasonsOf(cfg, e.key),
            stock = stock[e.key] or 0, freq = e.cat ~= 'vermin' and sw.ODDS.weight(cfg, e.key, e.token) or 0,
            odds_set = cfg.odds[e.key] ~= nil, stock_set = cfg.stock[e.key] ~= nil,
            gmin = gs or math.max(1, math.min(c0, c1)), gmax = gs or math.max(1, c0, c1), gsize_set = gs ~= nil,
            family = d.family, on_map = onMap[e.key] or 0, why = sw.whyFor(cfg, e),
            animal_person = e.animalPerson or false,
            guild = d.guild, slot = d.slot, level = d.level, tier = d.tier, part = d.part, scav = d.scav, gobble = d.gobble,
            ap = d.ap, giant = d.giant, sentient = d.sentient, extinct = d.extinct,
            ascii = st.ascii, diet = st.diet, gfx = st.gfx,
        }
        species[#species + 1] = sp
    end
    -- web2: the creatures the page shows that are not on the managed roster (cavern natives this fort does not manage,
    -- the deep, citizens and pets a predator killed, raw ids a ledger line names): name, ASCII glyph and sprite, by token,
    -- so a chip never draws an empty box. Static per raw (staticFor's cache); the token set is the map's, the history's
    -- and the last ledger lines'.
    local others, inPool, want = {}, {}, {}
    for _, e in ipairs(pool) do inPool[e.token] = true end
    for key in pairs(onMap) do want[(key:gsub('^%a+:', ''))] = true end
    if W.hist then
        for _, ev in ipairs(W.hist.events) do
            if ev.key then want[(tostring(ev.key):gsub('^%a+:', ''))] = true end
            if ev.by then want[(tostring(ev.by):gsub('^%a+:', ''))] = true end
        end
    end
    local LE = sw.LEDGER.load().entries
    for i = math.max(1, #LE - 59), #LE do for t in tostring(LE[i].s):gmatch('[%u][%u%d_]+') do if #t > 2 then want[t] = true end end end
    for tok in pairs(want) do
        if not inPool[tok] and not liveOnly then
            local idx = sw.raceIndex(tok)
            if idx and idx >= 0 then
                local st = staticFor(idx, tok, G)
                others[tok] = { name = st.name or tok, ascii = st.ascii, gfx = st.gfx }
            end
        end
    end
    tsp = nowMs() - tsp
    -- the tracked groups, then wild animals the tool is not tracking, so the page shows everything on the map
    local live = {}
    for _, grp in ipairs(g.groups) do
        local n, least = 0, nil
        for _, id in ipairs(grp.ids) do
            local u = df.unit.find(id)
            if u and not dfhack.units.isDead(u) then
                n = n + 1
                local cd = u.animal.leave_countdown
                if cd and cd > 0 and (not least or cd < least) then least = cd end
            end
        end
        if n > 0 then
            local layer = grp.layer or 'land'
            live[#live + 1] = { key = sw.keyFor(layer, grp.token), token = grp.token, layer = layer, n = n,
                                lk = sw.GRP.lk(grp), leader = grp.leader, panic = grp.panic and true or false,
                                origin = grp.irruption and 'irruption' or grp.tag and 'apex' or grp.drawn and 'tool-drawn'
                                         or grp.native and 'native' or grp.seeded and 'seeded' or (grp.resident and 'resident' or 'DF wave'),
                                leaves = least and (least / sw.TICKS_PER_DAY) or nil, tracked = true, depth = grp.depth, body = grp.body,
                                gid = ('%s@%s@%s'):format(tostring(grp.token), tostring(grp.arrived or 0), tostring(grp.src or '')),
                                days_here = (sw.absTick() - (grp.arrived or sw.absTick())) / sw.TICKS_PER_DAY }
        end
    end
    for _, r in pairs(untracked) do live[#live + 1] = { key = r.key, n = r.n, origin = r.origin, tracked = false } end
    table.sort(live, function(a, b) return a.key < b.key end)
    -- v7.1 (R7): one cap per layer from the formula or the fixed number (QUOTA.groupsFor), not limits[l].groups
    local limits = {}
    for _, l in ipairs({ 'land', 'water', 'cavern' }) do
        local L = cfg.limits[l] or {}
        local okc, cap = pcall(sw.QUOTA.groupsFor, cfg, l)
        limits[l] = { groups = okc and cap or (L.groups or 0), ceiling = L.ceiling or 0, wild = wild[l] or 0, groups_now = sw.ENGINE.count(g, l),
                      pattern = cfg.patterns[l] or 'steady', on = cfg.layers[l] and true or false }
    end
    limits.mode, limits.fixed = cfg.limits.mode or 'formula', cfg.limits.fixed
    local gate = (g.next_wave_tick or 0) - sw.absTick()
    limits.land.gate_days = gate > 0 and gate / sw.TICKS_PER_DAY or 0
    local jobs = {}
    for name, st in pairs(sw.FUSE.stats or {}) do
        jobs[#jobs + 1] = { name = name, last = st.last or 0, worst = st.worst or 0, runs = st.runs or 0, over = st.over or 0 }
    end
    table.sort(jobs, function(a, b) return a.name < b.name end)
    local ledger = {}
    local L = sw.LEDGER.load()
    for i = #L.entries, math.max(1, #L.entries - 59), -1 do
        local x = L.entries[i]
        ledger[#ledger + 1] = { t = sw.LEDGER.stamp(x.t), k = x.k, l = x.l, s = x.s }
    end
    local tick = df.global.cur_year_tick
    local day = tick // sw.TICKS_PER_DAY          -- day of the year, 0..335
    local site = df.world_site.find(df.global.plotinfo.site_id)
    local out = {
        tool = 'seasonal-wildlife', web = 2, loaded = true, release = sw.CACHE.release, cfg_ver = sw.CACHE.ver,
        fort = fortName(site),
        date = { year = df.global.cur_year, season = season, season_name = SEASONS[season], day_of_season = day - season * 84,
                 days_to_next = (season + 1) * 84 - day, day_of_month = day % 28 + 1, month = MONTHS[day // 28],
                 abs_day = df.global.cur_year * 336 + day + (tick % sw.TICKS_PER_DAY) / sw.TICKS_PER_DAY },
        enabled = cfg.enabled and true or false, hunting = (cfg.hunting and cfg.hunting.enabled) and true or false,
        fuse = sw.FUSE.status(), budget = sw.FUSE.BUDGET_MS, undo_depth = sw.UNDO.depth(),
        limits = limits, wild = wild, species = species, pairs = pairs_, live = live, jobs = jobs, ledger = ledger, others = others,
        gfx = { pages = G.pagesOut, font = G.font, palette = G.palette },
        -- web2: what else moved, so the page fetches the history, the ledger feed and the terrain only when they did
        hist_seq = W.hist and W.hist.seq or 0, ledger_seq = L.count or #L.entries,
        df = W.dfVer, dfhack = W.dfhackVer, save = W.saveDir,
        map_tv = W.scans and W.scans.surface and W.scans.surface.tv or 0,
    }
    local ms = nowMs() - t0
    out.ms = ms
    W.stats.snap_ms = ms
    if ms > W.stats.snap_worst then
        -- v7.1 (web-live: snapshot worst 835 ms): what the worst one spent it on -- pool+pairs (rebuilt when the config
        -- moved), the stock/unit census, the sprite sheets (read once per world), the species rows (static fields once per
        -- creature), the rest (groups, limits, ledger)
        W.stats.snap_worst = ms
        W.stats.snap_worst_parts = ('pool %d, census %d, gfx %d, species %d, rest %d ms'):format(tp, tc, tg, tsp, ms - tp - tc - tg - tsp)
    end
    return out
end

-- web2: an ETag that moves only when the state does (the build time `ms` aside), so a page that already holds it gets
-- a 304 with no body instead of ~100 KB every two seconds while the game is paused
-- the build and the save this state comes from, read once per server start (the page stamps its header with them)
local function readBuild()
    local function try(f) local ok, v = pcall(f); return ok and type(v) == 'string' and v ~= '' and v or nil end
    W.dfVer = try(function() return dfhack.getDFVersion() end)
    W.dfhackVer = try(function() return dfhack.getDFHackVersion() end) or try(function() return dfhack.getDFHackRelease() end)
    W.saveDir = try(function() return df.global.world.cur_savegame.save_dir end)
end
local function snapshotJson()
    if W.snapText and nowMs() - (W.snapAt or 0) < SNAP_TTL_MS then return W.snapText, W.snapTag end
    local text = json.encode(snapshot(), { pretty = false })
    local body = text:gsub('"ms":[%d%.eE%+%-]+,?', '')
    if body ~= W.snapBody then W.snapSeq = (W.snapSeq or 0) + 1; W.snapBody = body end
    W.snapText, W.snapAt, W.snapTag = text, nowMs(), ('"s%d-%s"'):format(W.snapSeq or 0, tostring(W.token or ''):sub(1, 6))
    return W.snapText, W.snapTag
end

-- the control registry with current values: rebuilt when the config moves (CACHE.ver), else at most every 10 s
local function controlsJson()
    if W.ctlText and W.ctlVer == sw.CACHE.ver and nowMs() - (W.ctlAt or 0) < CONTROLS_TTL_MS then return W.ctlText end
    W.ctlText = json.encode(C.registry(), { pretty = false })
    W.ctlVer, W.ctlAt = sw.CACHE.ver, nowMs()
    return W.ctlText
end

-- status sections: the engine's own status lines per subsystem, each cached STATUS_TTL_MS; 'groupmap' is the
-- structured groups per layer key. Only the sections asked for are built (the page asks for the open one).
local function statusJson(want)
    W.statusCache = W.statusCache or {}
    local ids = {}
    if want and want ~= '' then for id in want:gmatch('[%w_]+') do ids[#ids + 1] = id end
    else for id in pairs(C.STATUS) do ids[#ids + 1] = id end; ids[#ids + 1] = 'groupmap' end
    local out, cfg, g = { sections = {} }, nil, nil
    local t0 = nowMs()
    for _, id in ipairs(ids) do
        local c = W.statusCache[id]
        if not (c and c.ver == sw.CACHE.ver and nowMs() - c.at < STATUS_TTL_MS) then
            cfg = cfg or C.cfgRO()
            g = g or sw.loadGroups()
            local r
            if id == 'groupmap' then
                local s0 = nowMs()
                local ok, m = pcall(C.groupMap, cfg, g)
                r = ok and { layers = m, ms = nowMs() - s0 } or { error = tostring(m), layers = {} }
            elseif C.STATUS[id] then r = C.status(id, cfg, g)
            else r = { error = 'no such section', lines = {} } end
            c = { ver = sw.CACHE.ver, at = nowMs(), r = r }
            W.statusCache[id] = c
        end
        out.sections[id] = c.r
    end
    local ms = nowMs() - t0
    W.stats.status_ms = ms; if ms > W.stats.status_worst then W.stats.status_worst = ms end
    out.ms = ms
    return json.encode(out, { pretty = false })
end

local function changed()   -- after any write: the next read sees it
    W.snapText, W.ctlText, W.statusCache, W.poolCache = nil, nil, nil, nil
    W.mapLive, W.webCache, W.watersCache = nil, nil, nil
end

--========================================================================================
-- web2 (v7.1, 2 Oct 2026): the map, the history, the ledger feed, the live web, the waters (docs/v7.1/web2-design.md)
--========================================================================================
-- Every builder here runs inside DF's frame from a request (or, the sampler, from the poll timer), so each one is
-- bounded: the terrain is scanned a few milliseconds per request and resumed by the next, the O(n^2) relation read is
-- refused over a unit cap, everything else is cached for a second or more. Nothing here writes to the game or the
-- tool's store; the history lives in _G (W.hist) for as long as DF runs, keyed by the site, and is lost at a restart.
local V2 = {
    SAMPLE_TICKS = 300,          -- a history sample every quarter of a game day (1,200 ticks)
    HIST_CAP = 1344,             -- one game year of samples
    EVENT_CAP = 600,
    MAP_TTL_MS = 1500, WEB_TTL_MS = 15000, WATERS_TTL_MS = 3000,
    TERRAIN_SLICE_MS = 8,        -- terrain scanning per request; the page asks again until it is done
    MAX_CELLS = 160,             -- the terrain grid's longest side, in sampled columns
    MAX_UNITS = 2500,            -- units sent per map
    LINK_UNITS = 300, LINKS = 400,
    KILL_DAYS = 3,               -- kills shown on the map (game days)
}
local LCODE = { land = 0, water = 1, cavern = 2, deep = 3 }

local function siteKey()
    local m = df.global.world.map
    return ('%d:%d:%d:%d'):format(df.global.plotinfo.site_id, m.x_count, m.y_count, m.z_count)
end
local function tokenOf(race)
    local cr = df.creature_raw.find(race)
    return cr and cr.creature_id or '?'
end
-- the wild units on the map and their layers: the engine's census (one walk per tick), else the same filter here
local function wildUnits()
    local ok, cen = pcall(function() return sw.V7.PERF.census() end)
    if ok and type(cen) == 'table' and type(cen.wild) == 'table' and type(cen.layer) == 'table' then return cen.wild, cen.layer end
    local wild, layer = {}, {}
    for _, u in ipairs(df.global.world.units.active) do
        if sw.WILD.onMap(u) then wild[#wild+1] = u; layer[#wild] = sw.WILD.layerOf(u) end
    end
    return wild, layer
end
-- a group's id on the page: stable while the record lives (token, arrival tick, population source)
local function gidOf(grp) return ('%s@%s@%s'):format(tostring(grp.token), tostring(grp.arrived or 0), tostring(grp.src or '')) end
local function originOf(grp)
    return grp.irruption and 'irruption' or grp.tag and ('apex ' .. tostring(grp.tag)) or grp.placed and 'placed'
        or grp.drawn and 'tool-drawn' or grp.native and 'native' or grp.seeded and 'seeded' or grp.resident and 'resident' or 'DF wave'
end
-- the argument the groups verbs take for this group: a cavern group is scoped to its depth (`groups hold cavern1:TOKEN`)
local function verbArg(grp)
    local tok = tostring(grp.token or '?'):gsub('[%s,]+', '_')
    if grp.layer == 'cavern' and grp.depth then return ('cavern%d:%s'):format(grp.depth, tok) end
    return tok
end

-------------------------------------------------------------------------------- history
local function histState()
    local key = siteKey()
    local H = W.hist
    if not H or H.key ~= key then
        H = { key = key, samples = {}, events = {}, seq = 0, next = 0, last = nil, seen = nil, gids = nil, backfilled = false }
        W.hist = H
    end
    return H
end
local function pushEvent(H, ev)
    H.seq = H.seq + 1; ev.q = H.seq
    H.events[#H.events+1] = ev
    while #H.events > V2.EVENT_CAP do table.remove(H.events, 1) end
end
-- the ledger's arrivals before the server started, once, so the timeline does not begin empty
local function backfill(H)
    H.backfilled = true
    local L = sw.LEDGER.load()
    for _, x in ipairs(L.entries) do
        if x.k == 'arrive' or x.k == 'wave' or x.k == 'place' or (x.k == 'irruption' and tostring(x.s):match('wave')) then
            pushEvent(H, { k = 'arrive', t = x.t / sw.TICKS_PER_DAY, l = x.l, s = x.s, src = 'ledger',
                           token = tostring(x.s):match('^([%u_][%u%d_ ,]*%u) x%d') })
        end
    end
end
-- one sample: wild animals per layer, groups per layer key, units per species; arrivals and departures (group records
-- that appeared or went since the last sample) and kills (a wild unit seen last time and now dead, with the killer DF's
-- death incident names). Called from the poll timer; acts only when game time has crossed the next quarter day.
local function sampleHistory(force)
    if not dfhack.isMapLoaded() then return false end
    local H = histState()
    local now = sw.absTick()
    if H.last and now < H.last then W.hist = nil; H = histState() end   -- time went backwards: another save
    if not force and now < H.next then return false end
    local t0 = nowMs()
    if not H.backfilled then pcall(backfill, H) end
    H.next = now - now % V2.SAMPLE_TICKS + V2.SAMPLE_TICKS
    H.last = now
    local day = now / sw.TICKS_PER_DAY
    local wild, layers = wildUnits()
    local w, sp, alive = { land = 0, water = 0, cavern = 0, deep = 0 }, {}, {}
    for i, u in ipairs(wild) do
        local L = layers[i] or sw.WILD.layerOf(u)
        w[L] = (w[L] or 0) + 1
        local key = sw.keyFor(L, tokenOf(u.race))
        sp[key] = (sp[key] or 0) + 1
        alive[u.id] = { key, u.pos.x, u.pos.y, u.pos.z, L }
    end
    if H.seen then
        for id, rec in pairs(H.seen) do
            if not alive[id] then
                local u = df.unit.find(id)
                if u and dfhack.units.isDead(u) then
                    local ev = { k = 'died', t = day, key = rec[1], l = rec[5], x = rec[2], y = rec[3], z = rec[4], id = id }
                    pcall(function()
                        local inc = u.counters.death_id >= 0 and df.incident.find(u.counters.death_id) or nil
                        if inc then
                            ev.cause = df.death_type[inc.death_cause] or tostring(inc.death_cause)
                            if inc.criminal >= 0 then
                                ev.k, ev.by_id = 'kill', inc.criminal
                                local killer = df.unit.find(inc.criminal)
                                local kl = killer and sw.WILD.layerOf(killer) or rec[5]
                                ev.by = sw.keyFor(kl, tokenOf(inc.criminal_race >= 0 and inc.criminal_race or (killer and killer.race) or -1))
                                ev.by_wild = killer and dfhack.units.isWildlife(killer) and true or false
                            end
                        end
                    end)
                    pushEvent(H, ev)
                end
            end
        end
    end
    H.seen = alive
    local g = sw.loadGroups()
    local gl, gids = { land = 0, water = 0, cavern = 0 }, {}
    for _, grp in ipairs(g.groups) do
        local l = grp.layer or 'land'
        gl[l] = (gl[l] or 0) + 1
        local id = gidOf(grp)
        gids[id] = { token = grp.token, lk = sw.GRP.lk(grp), n = #grp.ids, l = l, origin = originOf(grp) }
        if H.gids and not H.gids[id] then
            pushEvent(H, { k = 'arrive', t = day, gid = id, token = grp.token, key = sw.keyFor(l, grp.token), l = l, lk = gids[id].lk,
                           n = #grp.ids, origin = gids[id].origin })
        end
    end
    if H.gids then
        for id, r in pairs(H.gids) do
            if not gids[id] then pushEvent(H, { k = 'leave', t = day, gid = id, token = r.token, key = sw.keyFor(r.l, r.token), l = r.l, lk = r.lk, n = r.n }) end
        end
    end
    H.gids = gids
    H.seq = H.seq + 1
    H.samples[#H.samples+1] = { q = H.seq, t = day, w = w, g = gl, sp = sp }
    while #H.samples > V2.HIST_CAP do table.remove(H.samples, 1) end
    local ms = nowMs() - t0
    W.stats.hist_ms = ms; if ms > (W.stats.hist_worst or 0) then W.stats.hist_worst = ms end
    return true
end
local function historyJson(since)
    local t0 = nowMs()
    local H = histState()
    if #H.samples == 0 then pcall(sampleHistory, true) end
    since = tonumber(since) or 0
    local s, e = {}, {}
    for _, x in ipairs(H.samples) do if x.q > since then s[#s+1] = x end end
    for _, x in ipairs(H.events) do if x.q > since then e[#e+1] = x end end
    return json.encode({ seq = H.seq, since = since, period_days = V2.SAMPLE_TICKS / sw.TICKS_PER_DAY, samples = s, events = e,
                         first = H.samples[1] and H.samples[1].t or nil, cap = V2.HIST_CAP, ms = nowMs() - t0 }, { pretty = false })
end

-------------------------------------------------------------------------------- ledger feed
local function eventsJson(since, n)
    local t0 = nowMs()
    local L = sw.LEDGER.load()
    since, n = tonumber(since) or 0, math.min(300, tonumber(n) or 300)
    local base = (L.count or #L.entries) - #L.entries
    local out = {}
    for i = math.max(1, #L.entries - n + 1), #L.entries do
        local seq = base + i
        if seq > since then
            local x = L.entries[i]
            out[#out+1] = { q = seq, t = x.t, d = x.t / sw.TICKS_PER_DAY, ts = sw.LEDGER.stamp(x.t), k = x.k, l = x.l, s = x.s }
        end
    end
    return json.encode({ count = L.count or #L.entries, since = since, entries = out, kinds = sw.LEDGER.KINDS, ms = nowMs() - t0 }, { pretty = false })
end

-------------------------------------------------------------------------------- terrain (incremental)
-- One cell per sampled column (stride 2-16, so the grid is at most MAX_CELLS a side): the class of the topmost tile
-- that is not open space and its level. A column's walk starts at its neighbour's level, so a hillside costs a few
-- reads a column, not a walk down from the sky. Unallocated blocks and columns not reached yet are '?'.
local TCLS
local function tclasses()
    if TCLS then return TCLS end
    local B, M = df.tiletype_shape_basic, df.tiletype_material
    TCLS = { open = B.Open, wall = B.Wall, ramp = B.Ramp, mat = {} }
    for name, c in pairs({ TREE = 'T', MUSHROOM = 'T', ROOT = 'T', GRASS_LIGHT = 'g', GRASS_DARK = 'g', GRASS_DRY = 'y', GRASS_DEAD = 'y',
                           SOIL = 's', FROZEN_LIQUID = 'i', CONSTRUCTION = 'c', PLANT = 'g', DRIFTWOOD = 's', POOL = 's', RIVER = 's', BROOK = 's',
                           MAGMA = 'm', LAVA_STONE = '.', STONE = '.', MINERAL = '.', FEATURE = '.' }) do
        local v = M[name]; if v ~= nil then TCLS.mat[v] = c end
    end
    return TCLS
end
local B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
local function b64(i) i = math.max(0, math.min(63, i)); return B64:sub(i + 1, i + 1) end

local function newScan(kind, depth)
    local m = df.global.world.map
    local Wd, Hd = m.x_count, m.y_count
    local s = 2
    while (Wd / s > V2.MAX_CELLS or Hd / s > V2.MAX_CELLS) and s < 16 do s = s * 2 end
    W.tvSeq = (W.tvSeq or 0) + 1
    local S = { kind = kind, depth = depth, key = siteKey(), stride = s, cw = (Wd + s - 1) // s, ch = (Hd + s - 1) // s,
                nbx = (Wd + 15) // 16, nby = (Hd + 15) // 16, cur = 0, done = false, cls = {}, z = {}, tv = W.tvSeq, ms = 0, reads = 0 }
    if kind == 'surface' then
        local ok, surf = pcall(sw.PLACE.surface)
        S.guess = (ok and tonumber(surf)) or (m.z_count // 2)
    else
        local band
        local c = sw.CACHE.cave or dfhack.persistent.getSiteData(sw.CAVE.KEY, nil)
        for _, b in ipairs((c and c.bands) or {}) do if b.depth == depth then band = b end end
        if not band then S.done, S.none = true, 'the cavern survey has not found this cavern at the map edge' end
        S.zlo, S.zhi = band and band.zlo or 0, band and band.zhi or -1
    end
    return S
end
-- scan one block column of S; returns tile reads made
local function scanBlockColumn(S, bx, by)
    local T = tclasses()
    local tattrs, sattrs = df.tiletype.attrs, df.tiletype_shape.attrs
    local s, m = S.stride, df.global.world.map
    local Wd, Hd, Z = m.x_count, m.y_count, m.z_count
    local off = s >= 16 and 8 or 0
    local blocks = {}
    local function at(x, y, z)
        local b = blocks[z]
        if b == nil then b = dfhack.maps.getTileBlock(x, y, z) or false; blocks[z] = b end
        if not b then return nil end
        S.reads = S.reads + 1
        local lx, ly = x % 16, y % 16
        return b.designation[lx][ly], b.tiletype[lx][ly]
    end
    local function isOpen(d, tt)
        if d.flow_size > 0 then return false end
        local a = tattrs[tt]
        return a and sattrs[a.shape].basic_shape == T.open
    end
    local function classify(d, tt)
        if d.flow_size > 0 then return d.liquid_type and 'm' or '~' end
        local a = tattrs[tt]
        if not a then return '?' end
        local mc = T.mat[a.material]
        if mc == 'T' then return 'T' end
        local basic = sattrs[a.shape].basic_shape
        if basic == T.wall then return '#' end
        if basic == T.ramp then return 'r' end
        return mc or '.'
    end
    for lx = off, 15, s do
        local x = bx * 16 + lx
        if x < Wd then
            for ly = off, 15, s do
                local y = by * 16 + ly
                if y < Hd then
                    local ci = (y // s) * S.cw + (x // s) + 1
                    if S.kind == 'surface' then
                        local z = math.max(0, math.min(Z - 1, S.lastz or S.guess))
                        local d, tt = at(x, y, z)
                        local found
                        if d then
                            if isOpen(d, tt) then
                                for zz = z - 1, 0, -1 do
                                    local d2, t2 = at(x, y, zz)
                                    if not d2 then break end
                                    if not isOpen(d2, t2) then found = zz; S.cls[ci] = classify(d2, t2); break end
                                end
                            else
                                found = z
                                local cd, ct = d, tt
                                for zz = z + 1, Z - 1 do
                                    local d2, t2 = at(x, y, zz)
                                    if not d2 or isOpen(d2, t2) then break end
                                    found, cd, ct = zz, d2, t2
                                end
                                S.cls[ci] = classify(cd, ct)
                            end
                        end
                        if found then S.z[ci] = found; S.lastz = found else S.cls[ci] = '?' end
                    else
                        local c = ' '
                        for zz = S.zhi, S.zlo, -1 do
                            local d, tt = at(x, y, zz)
                            if d and d.subterranean and not d.outside then
                                if d.flow_size >= 4 then c = d.liquid_type and 'm' or '~'; S.z[ci] = zz; break end
                                local a = tattrs[tt]
                                local basic = a and sattrs[a.shape].basic_shape
                                if basic and basic ~= T.open and basic ~= T.wall then
                                    c = (T.mat[a.material] == 'g' and 'g') or (T.mat[a.material] == 'T' and 'T') or '.'
                                    S.z[ci] = zz; break
                                end
                            end
                        end
                        S.cls[ci] = c
                    end
                end
            end
        end
    end
end
local function advance(S, budgetMs)
    if S.done then return end
    local t0 = nowMs()
    local total = S.nbx * S.nby
    while S.cur < total do
        local bx, by = S.cur % S.nbx, S.cur // S.nbx
        if by % 2 == 1 then bx = S.nbx - 1 - bx end   -- serpentine: the next column's start level is a neighbour's
        scanBlockColumn(S, bx, by)
        S.cur = S.cur + 1
        if nowMs() - t0 >= budgetMs then break end
    end
    S.ms = S.ms + (nowMs() - t0)
    if S.cur >= total then S.done = true; S.enc = nil end
end
local function encodeScan(S)
    if S.enc and S.done then return S.enc end
    local n = S.cw * S.ch
    local zlo, zhi = math.huge, -math.huge
    for i = 1, n do local z = S.z[i]; if z then if z < zlo then zlo = z end; if z > zhi then zhi = z end end end
    if zlo == math.huge then zlo, zhi = 0, 0 end
    local span = math.max(1, zhi - zlo)
    local k = span > 63 and 63 / span or 1
    local cls, el = {}, {}
    for i = 1, n do
        cls[i] = S.cls[i] or '?'
        local z = S.z[i]
        el[i] = z and b64(math.floor((z - zlo) * k + 0.5)) or 'A'
    end
    local e = { tv = S.tv, kind = S.kind, depth = S.depth, stride = S.stride, cw = S.cw, ch = S.ch, done = S.done, none = S.none,
                pct = math.floor(100 * S.cur / math.max(1, S.nbx * S.nby)), zlo = zlo, zhi = zhi, zstep = 1 / k,
                cls = table.concat(cls), elev = table.concat(el), ms = S.ms, reads = S.reads }
    if S.done then S.enc = e end
    return e
end
local function scanFor(kind, depth)
    W.scans = W.scans or {}
    local id = kind .. (depth or '')
    local S = W.scans[id]
    if not S or S.key ~= siteKey() then S = newScan(kind, depth); W.scans[id] = S end
    return S
end
-- the engine's own water scan (ENGINE.waterTiles), on the terrain grid: body letter and column depth per cell. Never
-- forces a scan: before the water job's first survey there is none.
local function waterOnGrid(S)
    local wt = sw.CACHE.wtiles
    if not wt or not wt.cols then return nil end
    local c = W.waterGrid
    if c and c.src == wt and c.stride == S.stride and c.cw == S.cw then return c.out end
    local ws = wt.stride or 2
    local body, depth = {}, {}
    local any = false
    for cy = 0, S.ch - 1 do
        for cx = 0, S.cw - 1 do
            local i = cy * S.cw + cx + 1
            local x, y = cx * S.stride, cy * S.stride
            local col = wt.cols[(x - x % ws) * 65536 + (y - y % ws)]
            if col then body[i] = (col.body or 'r'):sub(1, 1); depth[i] = tostring(math.min(9, col.n or 1)); any = true
            else body[i] = ' '; depth[i] = '0' end
        end
    end
    W.wvSeq = (W.wvSeq or 0) + 1
    local out = any and { wv = W.wvSeq, body = table.concat(body), depth = table.concat(depth), sum = wt.sum, stride = ws, ms = wt.ms } or { wv = W.wvSeq, none = true }
    W.waterGrid = { src = wt, stride = S.stride, cw = S.cw, out = out }
    return out
end

-------------------------------------------------------------------------------- map
local function irruptRows(cfg, g)
    local out = {}
    if not (cfg.irruption and sw.IRRUPT) then return out end
    for _, d in ipairs(sw.IRRUPT.DEPTHS or { 0, 1, 2 }) do
        local L = (type(g.irr2) == 'table' and type(g.irr2.layers) == 'table') and g.irr2.layers['c' .. d] or nil
        local r = { depth = d, phase = L and L.phase or 'idle', on = cfg.irruption.enabled and true or false }
        if cfg.irruption.enabled then
            local ok, t = pcall(sw.IRRUPT.phaseText, cfg, g, d, false); if ok then r.text = t end
            local okp, p = pcall(sw.IRRUPT.pressure, g, d); if okp then r.pressure = p end
            r.pinned = (g.pressure_pin and g.pressure_pin['c' .. d]) and true or false
        end
        if L and L.ev then r.token, r.wave, r.waves = L.ev.token, L.ev.done, L.ev.waves end
        out[#out+1] = r
    end
    return out
end
local function caveBands()
    local c = sw.CACHE.cave or dfhack.persistent.getSiteData(sw.CAVE.KEY, nil)
    local out = {}
    for _, b in ipairs((c and c.bands) or {}) do
        out[#out+1] = { depth = b.depth, cave_id = b.cave_id, zlo = b.zlo, zhi = b.zhi, water = b.water, open = b.open }
    end
    return out
end
local function linksNow(nwild)
    local c = W.linkCache
    if c and nowMs() - c.at < V2.WEB_TTL_MS then return c.links, c.skipped end
    local links, skipped = {}, nil
    if nwild > V2.LINK_UNITS then skipped = ('%d wild units on the map: the relation read is skipped over %d'):format(nwild, V2.LINK_UNITS)
    else
        local ok, ps = pcall(sw.ecoLivePairUnits, V2.LINKS)
        if ok and type(ps) == 'table' then
            for _, p in ipairs(ps) do links[#links+1] = { p.a, p.b, p.apos.x, p.apos.y, p.apos.z, p.bpos.x, p.bpos.y, p.bpos.z } end
        else skipped = 'relation read failed: ' .. tostring(ps) end
    end
    W.linkCache = { at = nowMs(), links = links, skipped = skipped }
    return links, skipped
end
-- the moving part of the map: units, groups, cavern and irruption state, recent kills (cached MAP_TTL_MS)
local function mapLive()
    local c = W.mapLive
    if c and nowMs() - c.at < V2.MAP_TTL_MS and c.key == siteKey() then return c.out end
    local t0 = nowMs()
    local cfg = C.cfgRO()
    local g = sw.loadGroups()
    local member = {}
    for i, grp in ipairs(g.groups) do for _, id in ipairs(grp.ids) do member[id] = i end end
    local wild, layers = wildUnits()
    local keys, kidx, units = {}, {}, {}
    local truncated = 0
    for i, u in ipairs(wild) do
        if #units >= V2.MAX_UNITS then truncated = truncated + 1
        else
            local L = layers[i] or sw.WILD.layerOf(u)
            local key = sw.keyFor(L, tokenOf(u.race))
            local k = kidx[key]
            if not k then keys[#keys+1] = key; k = #keys - 1; kidx[key] = k end
            local m = member[u.id]
            units[#units+1] = { u.id, u.pos.x, u.pos.y, u.pos.z, k, LCODE[L] or 0, m and (m - 1) or -1 }
        end
    end
    local now, TPD = sw.absTick(), sw.TICKS_PER_DAY
    local groups = {}
    for _, grp in ipairs(g.groups) do
        local n, sx, sy, sz, x0, y0, x1, y1, least = 0, 0, 0, 0, math.huge, math.huge, -math.huge, -math.huge, nil
        local lpos
        local alive = {}
        for _, id in ipairs(grp.ids) do
            local u = df.unit.find(id)
            if u and not dfhack.units.isDead(u) then
                n = n + 1; alive[#alive+1] = id
                local p = u.pos
                sx, sy, sz = sx + p.x, sy + p.y, sz + p.z
                if p.x < x0 then x0 = p.x end; if p.x > x1 then x1 = p.x end
                if p.y < y0 then y0 = p.y end; if p.y > y1 then y1 = p.y end
                if id == grp.leader then lpos = { p.x, p.y, p.z } end
                local cd = u.animal.leave_countdown
                if cd and cd > 0 and (not least or cd < least) then least = cd end
            end
        end
        local l = grp.layer or 'land'
        groups[#groups+1] = {
            gid = gidOf(grp), token = grp.token, key = sw.keyFor(l, grp.token), layer = l, lk = sw.GRP.lk(grp), depth = grp.depth, body = grp.body,
            n = n, size = #grp.ids, ids = alive, leader = grp.leader, lpos = lpos,
            c = n > 0 and { sx / n, sy / n, sz / n } or nil, box = n > 0 and { x0, y0, x1, y1 } or nil,
            origin = originOf(grp), label = grp.label, panic = grp.panic and true or false, seeded = grp.seeded and true or false,
            days_here = (now - (grp.arrived or now)) / TPD, leaves = least and least / TPD or nil,
            held = (grp.held_until and grp.held_until > now) and (grp.held_until - now) / TPD or nil, act = verbArg(grp),
        }
    end
    local H = histState()
    local kills, since = {}, now / TPD - V2.KILL_DAYS
    for i = #H.events, 1, -1 do
        local e = H.events[i]
        if e.t < since then break end
        if e.k == 'kill' or e.k == 'died' then kills[#kills+1] = e end
    end
    local out = { tick = now, day = now / TPD, keys = keys, units = units, groups = groups, truncated = truncated,
                  caves = caveBands(), irrupt = irruptRows(cfg, g), kills = kills, nwild = #wild }
    out.ms = nowMs() - t0
    W.mapLive = { at = nowMs(), key = siteKey(), out = out }
    return out
end
-- GET /map.json?tv=N[&cave=D][&links=1]: the terrain when the page's version is stale (and a slice more of it while it
-- is being scanned), the water on the same grid, and the live part
local function mapJson(q)
    if not dfhack.isMapLoaded() then return json.encode({ loaded = false }, { pretty = false }) end
    local t0 = nowMs()
    local m = df.global.world.map
    local S = scanFor('surface')
    advance(S, V2.TERRAIN_SLICE_MS)
    local out = { loaded = true, w = m.x_count, h = m.y_count, zc = m.z_count, tv = S.tv, tdone = S.done }
    if tostring(S.tv) ~= tostring(q.tv) or not S.done then out.terrain = encodeScan(S) end
    local wg = waterOnGrid(S)
    if wg and tostring(wg.wv) ~= tostring(q.wv) then out.water = wg end
    out.wv = wg and wg.wv or nil
    local d = tonumber(q.cave)
    if d and d >= 0 and d <= 2 then
        local CS = scanFor('cavern', d)
        if nowMs() - t0 < V2.TERRAIN_SLICE_MS then advance(CS, V2.TERRAIN_SLICE_MS - (nowMs() - t0)) end
        if tostring(CS.tv) ~= tostring(q.cv) or not CS.done then out.cave = encodeScan(CS) end
        out.cv = CS.tv
    end
    out.live = mapLive()
    if q.links == '1' then out.links, out.links_skipped = linksNow(out.live.nwild or 0) end
    out.ms = nowMs() - t0
    W.stats.map_ms = out.ms; if out.ms > (W.stats.map_worst or 0) then W.stats.map_worst = out.ms end
    return json.encode(out, { pretty = false })
end

-------------------------------------------------------------------------------- the live web, the waters, one species
local function webJson()
    local c = W.webCache
    if c and nowMs() - c.at < V2.WEB_TTL_MS then return c.text end
    local t0 = nowMs()
    local wild = wildUnits()
    local rel, skipped = {}, nil
    if #wild > V2.LINK_UNITS then skipped = ('%d wild units: over %d, the relation read is skipped'):format(#wild, V2.LINK_UNITS)
    else
        local ok, p = pcall(sw.ecoLivePairs)
        if ok and type(p) == 'table' then for k, n in pairs(p) do local a, b = k:match('^(.-)|(.*)$'); rel[#rel+1] = { a, b, n } end
        else skipped = 'relation read failed: ' .. tostring(p) end
    end
    local g = sw.loadGroups()
    local eco = g.ecology and g.ecology.last or nil
    local H = histState()
    local kills, k = {}, {}
    for _, e in ipairs(H.events) do
        if e.k == 'kill' and e.by then local id = e.by .. '>' .. e.key; k[id] = (k[id] or 0) + 1 end
    end
    for id, n in pairs(k) do local a, b = id:match('^(.-)>(.*)$'); kills[#kills+1] = { a, b, n } end
    local cfg = C.cfgRO()
    local out = { relations = rel, skipped = skipped, kills = kills, nwild = #wild, hunting = (cfg.hunting and cfg.hunting.enabled) and true or false,
                  ecology = eco and { tick = eco.tick, day = eco.tick and eco.tick / sw.TICKS_PER_DAY, preds = eco.preds, targets = eco.targets, pairs = eco.pairs,
                                      slotted = eco.slotted, nudged = eco.nudged, stooped = eco.stooped, lured = eco.lured } or nil,
                  writes = g.ecology and g.ecology.writes or 0, eco_on = (cfg.ecology and cfg.ecology.enabled ~= false) and true or false }
    out.ms = nowMs() - t0
    local text = json.encode(out, { pretty = false })
    W.webCache = { at = nowMs(), text = text }
    return text
end
local function watersJson()
    local c = W.watersCache
    if c and nowMs() - c.at < V2.WATERS_TTL_MS then return c.text end
    local t0 = nowMs()
    local cfg, g = C.cfgRO(), sw.loadGroups()
    local out = { scanned = sw.CACHE.wtiles ~= nil, bodies = {}, caves = caveBands(), irrupt = irruptRows(cfg, g) }
    local wt = sw.CACHE.wtiles
    if wt then
        out.water = { sum = wt.sum, ncols = wt.ncols, maxDepth = wt.maxDepth, stride = wt.stride, ms = wt.ms, stopped = wt.stopped, hist = wt.hist }
        local ok, data = pcall(sw.V7.WAT.census, cfg, g)
        if ok and type(data) == 'table' then
            for body, B in pairs(data) do
                local sp = {}
                for tok, s in pairs(B.sp) do sp[#sp+1] = { token = tok, n = s.n, groups = s.groups, lvl = s.lvl, mass = s.mass } end
                table.sort(sp, function(a, b) return a.n > b.n end)
                out.bodies[#out.bodies+1] = { body = body, units = B.units, groups = B.groups, lv = B.lv, apex = B.apexGroups, src = B.src, sp = sp }
            end
        elseif not ok then out.census_error = tostring(data) end
    end
    local okm, gm = pcall(C.groupMap, cfg, g)
    if okm then out.groupmap = gm end
    out.ms = nowMs() - t0
    local text = json.encode(out, { pretty = false })
    W.watersCache = { at = nowMs(), text = text }
    return text
end
local function speciesJson(key)
    key = tostring(key or '')
    local cfg = C.cfgRO()
    local pool = poolAndPairs(cfg)
    local e
    for _, x in ipairs(pool) do if x.key == key then e = x; break end end
    if not e then return 400, json.encode({ error = 'no managed species ' .. key }, { pretty = false }) end
    local out = { key = key, token = e.token }
    local ok, L = pcall(sw.speciesDetail, cfg, pool, e)
    out.detail = ok and L or { 'detail unavailable: ' .. tostring(L) }
    local led = {}
    for _, x in ipairs(sw.LEDGER.load().entries) do
        if tostring(x.s):find(e.token, 1, true) then led[#led+1] = { t = x.t, ts = sw.LEDGER.stamp(x.t), k = x.k, l = x.l, s = x.s } end
    end
    out.ledger = led
    return 200, json.encode(out, { pretty = false })
end

--========================================================================================
-- HTTP on 127.0.0.1
--========================================================================================
local function pagePath()
    local me = dfhack.findScript('seasonal-wildlife-web')
    return me and me:gsub('%.lua$', '.html') or nil
end

local function respond(c, code, ctype, body, cache, etag)
    local reason = ({ [200] = 'OK', [304] = 'Not Modified', [400] = 'Bad Request', [403] = 'Forbidden', [404] = 'Not Found', [405] = 'Method Not Allowed', [500] = 'Internal Server Error' })[code] or 'OK'
    c:send(('HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nCache-Control: %s\r\n%s'
            .. 'X-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\nConnection: close\r\n\r\n'):format(code, reason, ctype, #body, cache or 'no-store',
            etag and ('ETag: ' .. etag .. '\r\n') or '') .. body)
end
local function jsonReply(c, code, t) respond(c, code, 'application/json; charset=utf-8', json.encode(t, { pretty = false })) end

local function parseQuery(q)
    local out = { a = {} }
    for k, v in (q or ''):gmatch('([^&=]+)=([^&]*)') do
        v = v:gsub('%+', ' '):gsub('%%(%x%x)', function(h) return string.char(tonumber(h, 16)) end)
        if k == 'a' then out.a[#out.a + 1] = v else out[k] = v end
    end
    return out
end

-- a command from the page: the registry's whitelist and argument check, then the console verb itself
local function runCommand(args)
    local ok, out = C.runVerb(args)
    if ok then changed() end
    return ok, out
end

local function handle(c)
    local t0 = nowMs()
    c:setBlocking(); c:setTimeout(0, READ_LINE_MS)     -- a request line and headers from loopback arrive at once
    local line = c:receive('*l')
    if not line then W.stats.stalled = W.stats.stalled + 1; return end   -- a browser's spare (preconnect) socket: nothing sent
    local method, target = line:gsub('\r$', ''):match('^(%u+) (%S+) HTTP/1%.[01]$')
    W.cur = ('%s %s'):format(tostring(method), tostring(target):gsub('t=%x+', 't=TOKEN'):sub(1, 120))
    local host, inm
    for _ = 1, 60 do
        -- v7.1 (fail fast): a client that trickles its headers is dropped, not waited on line by line (each receive can
        -- wait READ_LINE_MS, sixty of them six seconds of DF's frame)
        if nowMs() - t0 > READ_BUDGET_MS then W.stats.stalled = W.stats.stalled + 1; return end
        local h = c:receive('*l')
        if not h then break end
        h = h:gsub('\r$', '')
        if h == '' then break end
        local k, v = h:match('^([^:]+):%s*(.*)$')
        if k and k:lower() == 'host' then host = v end
        if k and k:lower() == 'if-none-match' then inm = v end
    end
    W.stats.requests = W.stats.requests + 1
    if not method then return respond(c, 400, 'text/plain', 'bad request') end
    -- DNS rebinding: a page from elsewhere that resolves a name to 127.0.0.1 still sends its own Host
    local okHost = host == ('127.0.0.1:%d'):format(W.port) or host == ('localhost:%d'):format(W.port)
    if not okHost then W.stats.rejected = W.stats.rejected + 1; return respond(c, 403, 'text/plain', 'wrong host') end
    local path, query = target:match('^([^?]*)%??(.*)$')
    local q = parseQuery(query)
    if path == '/' or path == '/index.html' then
        if method ~= 'GET' then return respond(c, 405, 'text/plain', 'GET only') end
        local p = pagePath()
        local f = p and io.open(p, 'rb')
        if not f then return respond(c, 500, 'text/plain', 'the companion page is not installed next to the script: ' .. tostring(p)) end
        local body = f:read('*a'); f:close()
        return respond(c, 200, 'text/html; charset=utf-8', body)
    end
    -- everything below needs the token
    if q.t ~= W.token then
        W.stats.rejected = W.stats.rejected + 1
        if path:match('^/gfx/') then return respond(c, 403, 'text/plain', 'token') end
        return jsonReply(c, 403, { error = 'token' })
    end
    if path == '/state.json' then
        local text, tag = snapshotJson()
        if inm and tag and inm == tag then W.stats.not_modified = (W.stats.not_modified or 0) + 1; return respond(c, 304, 'application/json; charset=utf-8', '', nil, tag) end
        return respond(c, 200, 'application/json; charset=utf-8', text, nil, tag)
    elseif path == '/map.json' then
        return respond(c, 200, 'application/json; charset=utf-8', mapJson(q))
    elseif path == '/history.json' then
        return respond(c, 200, 'application/json; charset=utf-8', historyJson(q.since))
    elseif path == '/events.json' then
        return respond(c, 200, 'application/json; charset=utf-8', eventsJson(q.since, q.n))
    elseif path == '/web.json' then
        return respond(c, 200, 'application/json; charset=utf-8', webJson())
    elseif path == '/waters.json' then
        return respond(c, 200, 'application/json; charset=utf-8', watersJson())
    elseif path == '/species.json' then
        local code, text = speciesJson(q.key)
        return respond(c, code, 'application/json; charset=utf-8', text)
    elseif path == '/controls.json' then
        return respond(c, 200, 'application/json; charset=utf-8', controlsJson())
    elseif path == '/status.json' then
        return respond(c, 200, 'application/json; charset=utf-8', statusJson(q.s))
    elseif path:match('^/gfx/') then
        -- DF's own sprite sheets and font, by name from the graphics raws only (no path from the request reaches io.open)
        local G = gfx()
        local file = path == '/gfx/font' and G.fontFile or (G.pages[path:match('^/gfx/p/([%w_]+)$') or ''] or {}).file
        local body = file and readAll(file)
        if not body then return respond(c, 404, 'text/plain', 'no such sheet') end
        return respond(c, 200, 'image/png', body, 'private, max-age=86400')
    end
    -- the writes: POST only
    if path == '/cmd' or path == '/set' or path == '/act' or path == '/read' then
        if method ~= 'POST' then return respond(c, 405, 'text/plain', 'POST only') end
        W.stats.commands = W.stats.commands + 1
        if path == '/cmd' then
            local ok, out = runCommand(q.a)
            return jsonReply(c, ok and 200 or 400, { ok = ok, out = out, cmd = 'seasonal-wildlife ' .. table.concat(q.a, ' ') })
        elseif path == '/set' then
            -- one control, checked against the registry (type, range, choices), then its verb or Panel path
            W.stats.sets = W.stats.sets + 1
            local ok, out, cmd, value = C.set(q.id or '', q.v, q.tok)
            changed()
            return jsonReply(c, ok and 200 or 400, { ok = ok, out = out, cmd = cmd, id = q.id, value = value })
        elseif path == '/act' then
            local ok, out, cmd = C.act(q.id or '', q.arg)
            changed()
            return jsonReply(c, ok and 200 or 400, { ok = ok, out = out, cmd = cmd, id = q.id })
        else
            local ok, out, cmd = C.readout(q.id or '')
            return jsonReply(c, ok and 200 or 400, { ok = ok, out = out, cmd = cmd, id = q.id })
        end
    end
    return respond(c, 404, 'text/plain', 'not found')
end

local function poll()
    if not W.server then repeatUtil.cancel(TIMER) return end
    local t0 = nowMs()
    local handled, failed = 0, 0
    local ok, err = pcall(function()
        for i = 1, MAX_ACCEPTS do
            if i > 1 and nowMs() - t0 >= POLL_BUDGET_MS then W.stats.deferred = W.stats.deferred + 1; break end   -- the rest wait a poll
            local c = W.server:accept()
            -- v7.1 (web-live end.server_errors: 'errors 400246' of 1,885 requests): DFHack's luasocket accept() returns a
            -- client object for id 0 when nobody is waiting (lua_server_accept returns 0, and the wrapper tests ~= nil).
            -- handle() then failed on setBlocking with 'Client does with this id not exist' -- MAX_ACCEPTS errors on every
            -- idle poll, never a real request. Id 0 is never a client (ids start at 1): no client, no more this poll.
            if not c or (tonumber(c.client_id) or 0) <= 0 then break end
            local r0 = nowMs()
            W.cur = nil
            local hok, herr = pcall(handle, c)
            handled = handled + 1
            if not hok then failed = failed + 1; W.stats.errors = W.stats.errors + 1; W.lastError = tostring(herr) end
            pcall(function() c:close() end)
            local rms = nowMs() - r0
            if rms > W.stats.req_worst then W.stats.req_worst, W.stats.req_worst_what = rms, W.cur or '(no request line)' end
        end
    end)
    -- web2: the history sample, when game time has crossed the next quarter day (a no-op check otherwise); it is the
    -- server's own memory, so it runs whether or not a page is open
    if nowMs() - t0 < POLL_BUDGET_MS then
        local hok, herr = pcall(sampleHistory)
        if not hok then W.stats.hist_errors = (W.stats.hist_errors or 0) + 1; W.lastHistError = tostring(herr) end
    end
    local ms = nowMs() - t0
    W.stats.last_ms = ms; if ms > W.stats.worst_ms then W.stats.worst_ms = ms end
    -- fail fast on a server that only fails: an accept error, or a poll whose every request failed; an idle poll or a
    -- poll with one good request clears the count
    if ok and failed == 0 then if handled > 0 then W.failing = 0 end return end
    if ok and failed < handled then W.failing = 0 return end
    W.failing = (W.failing or 0) + 1; W.lastError = ok and W.lastError or tostring(err)
    if W.failing >= ERROR_LIMIT then
        dfhack.printerr(('seasonal-wildlife-web: stopped after %d failed polls in a row: %s'):format(W.failing, W.lastError))
        pcall(function() W.server:close() end); W.server = nil; repeatUtil.cancel(TIMER)
    end
end

local function newToken()
    math.randomseed(os.time() + dfhack.getTickCount())
    local t = {}
    for i = 1, 20 do t[i] = ('%x'):format(math.random(0, 15)) end
    return table.concat(t)
end

local function url() return ('http://127.0.0.1:%d/?t=%s'):format(W.port, W.token or '') end

local function start(port)
    -- the socket lives in _G and survives a map reload, but repeat-util drops the poll timer at unload: a second start
    -- re-arms it (full validation 124923 -> 125545: 'already serving' while nothing answered on the port)
    if W.server then repeatUtil.scheduleEvery(TIMER, POLL_FRAMES, 'frames', poll); return ('already serving: %s'):format(url()) end
    local okp, luasocket = pcall(require, 'plugins.luasocket')
    if not okp then qerror('the luasocket plugin is not available in this DFHack: ' .. tostring(luasocket)) end
    W.port = port or W.port
    -- 127.0.0.1 only: the loopback interface, never 0.0.0.0 or a LAN address
    local okb, srv = pcall(function() return luasocket.tcp:bind('127.0.0.1', W.port) end)
    if not okb or not srv then qerror(('could not listen on 127.0.0.1:%d: %s'):format(W.port, tostring(srv))) end
    srv:setNonblocking()
    W.server, W.token, W.failing = srv, W.token or newToken(), 0
    pcall(readBuild)
    changed()
    local G = gfx()
    repeatUtil.scheduleEvery(TIMER, POLL_FRAMES, 'frames', poll)
    local copied = pcall(dfhack.internal.setClipboardTextCp437, url())
    return ('serving the companion at %s%s  [tiles: %d creatures, %d sheets, read in %d ms]'):format(url(), copied and '  (copied to the clipboard)' or '',
        G.count or 0, (function() local n = 0; for _ in pairs(G.pagesOut) do n = n + 1 end; return n end)(), G.ms or 0)
end

local function stop()
    repeatUtil.cancel(TIMER)
    if not W.server then return 'not serving' end
    pcall(function() W.server:close() end)
    W.server = nil
    changed()
    return 'stopped'
end

local function status()
    local s = W.stats
    return ('%s  requests %d (commands %d, sets %d, refused %d, errors %d, dropped silent/slow clients %d, deferred to the next poll %d); poll last %d ms, worst %d ms; slowest request %d ms (%s); snapshot last %d ms, worst %d ms%s; status last %d ms, worst %d ms; static species fields %d ms in all; web2: map last %d ms, worst %d ms; history sample last %d ms, worst %d ms (%d samples, %d events%s); 304s %d%s')
        :format(W.server and ('serving ' .. url()) or 'not serving', s.requests, s.commands, s.sets, s.rejected, s.errors,
                s.stalled, s.deferred, s.last_ms, s.worst_ms, s.req_worst, s.req_worst_what or '-', s.snap_ms, s.snap_worst,
                s.snap_worst_parts and (' [' .. s.snap_worst_parts .. ']') or '', s.status_ms, s.status_worst, s.static_ms,
                s.map_ms or 0, s.map_worst or 0, s.hist_ms or 0, s.hist_worst or 0, W.hist and #W.hist.samples or 0, W.hist and #W.hist.events or 0,
                s.hist_errors and (', ' .. s.hist_errors .. ' failed: ' .. tostring(W.lastHistError)) or '', s.not_modified or 0,
                W.lastError and ('; last error: ' .. W.lastError) or '')
end

-- exported for probes (the validator) and for a copy loaded with reqscript
_ENV.snapshot, _ENV.runCommand, _ENV.start, _ENV.stop, _ENV.status, _ENV.url = snapshot, runCommand, start, stop, status, url
_ENV.statusJson, _ENV.controlsJson = statusJson, controlsJson
_ENV.mapJson, _ENV.historyJson, _ENV.eventsJson, _ENV.webJson, _ENV.watersJson, _ENV.speciesJson = mapJson, historyJson, eventsJson, webJson, watersJson, speciesJson
_ENV.sampleHistory, _ENV.snapshotJson, _ENV.V2 = sampleHistory, snapshotJson, V2

if dfhack_flags and dfhack_flags.module then return end

local args = { ... }
local cmd = args[1] or 'status'
if cmd == 'start' then print(start(tonumber(args[2])))
elseif cmd == 'stop' then print(stop())
elseif cmd == 'status' then print(status())
elseif cmd == 'snapshot' then print(json.encode(snapshot(), { pretty = false }))
else print('usage: seasonal-wildlife-web start [port] | stop | status | snapshot') end
