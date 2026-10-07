-- seasonal-wildlife-aquarium.lua -- the Aquarium: see the life of your seas, lakes and rivers. v7.1 (aquarium stream;
-- docs/v7.1/aquarium.md, 2 Oct 2026). Built at the desk; not yet run in Dwarf Fortress (rig plan: aquarium.md section 9).
--
-- Two DFHack overlays (overlay framework, script-only, graphics mode):
--   seasonal-wildlife-aquarium.view    paints, in this order: the BED (the floor under each water cell of the view level,
--                                      written into DF's background layer: DF draws none there, so translucent water
--                                      showed only a dark fill), the veil (experimental), the LENS (creatures below the level
--                                      you look at, through up to 8 levels of water, depth-faded, schools bracketed,
--                                      leaders ringed) and the WAVES (v7.1-waves v2: subtle crest lines on DF's ocean wave
--                                      fronts and flows, DF's own mist tiles where they run up the dry shore, a faint
--                                      wash at the waterline; graphics mode draws none of them)
--   seasonal-wildlife-aquarium.legend  a small movable panel: what is swimming below the view, per species
-- and the runtime half of `seasonal-wildlife aquarium ...`: install / restore / uninstall of the translucent-water
-- graphics mod (built by seasonal-wildlife-aquarium-gfx from the player's own vanilla sheets), status, probe, rearm.
-- The switches live in the tool's config (`aquarium.*`, engine V7.AQ), so the console, the Panel and the browser
-- companion set them; the overlays read them from the tool's shared cache once per scan.
--
-- Fail fast (fail-fast mandate): scans run a few times a second with hard caps and a deadline; a frame paints only from
-- the last scan; each layer measures its paint time and its fuse trips (stops that layer for the session, one console
-- line, one ledger line) when the average stays over budget or anything raises. No unit, raw or save is written. The
-- bed and the veil write DF's viewport buffers, inside the viewport (bounds-checked); the veil is off by default, the
-- bed on where the world loaded the aquarium mod.
-- Never touches enabler.fps or calculated_fps.
--@ module = true
--[====[

seasonal-wildlife-aquarium
==========================

Tags: fort | graphics | animals

The Aquarium view of seasonal-wildlife: an overlay that shows the creatures in the water below the level you are
looking at, a legend of what is swimming there, animated ocean waves and foam, and the installer of a translucent-water
graphics mod built from your own vanilla sheets.

Usage::

    seasonal-wildlife aquarium [status]     everything below goes through the tool's console verb
    seasonal-wildlife-aquarium status       the same status, straight from this script
    seasonal-wildlife-aquarium probe        one scan now: wave fronts, wave/foam/mist flows, wave makers, water life

Overlays: ``seasonal-wildlife-aquarium.view`` and ``seasonal-wildlife-aquarium.legend`` (``gui/overlay`` moves the
legend). See ``help seasonal-wildlife`` for every ``aquarium`` option.

]====]

-- luacheck: globals AquariumView AquariumLegend OVERLAY_WIDGETS scanLens legendRows wavesOn scanWaves scanFlowFx scanVeil scanBed bedOn bedChoice bedVariant bedTexture AQ_installDir AQ_baseDir install uninstall statusLines probe verb installedCopies
local overlay = require('plugins.overlay')
local widgets = require('gui.widgets')

local RELEASE = '7.1.0-aq15'   -- aq10: rivers as mud and the shallow fix (the lift plan's new fields, river tiles); aq9: waves v2.1 (DF's mist tiles drawn as they are, sprite making paced per row; new state fields); aq8: the bed baked into the mod (run.below in map coordinates, the lift plan state); aq7: waves v2 (crests + DF mist on the shore); aq6: bed v1 (sand/mud, optics below the surface, creatures below); aq2: the bed layer; aq3: the waves redesign; aq4: river streaks and shimmer (new state fields);
-- aq5: sprites byte-swapped for DF (a new key drops every texture cached under the old, wrong pixel order)
-- one state for every copy of this script (the overlay's, the console's, the window's): textures, fuses, the last scans
local AQ = rawget(_G, '__sw_aquarium')
if not AQ or AQ.release ~= RELEASE then
    AQ = { release = RELEASE, tex = {}, texN = 0, masks = {}, race = {}, fuse = {}, stat = {}, lens = nil, waves = nil,
           veil = nil, legend = nil, coast = nil, veilTex = nil,
           bed = nil, bedBuild = nil, bedTex = {}, bedTexN = 0, bedSheets = {}, bedMat = {}, bedGeo = {}, bedLayer = {},
           bedMap = nil, bedAct = nil, bedOwn = {}, bedFrame = nil,
           wtex = {}, wtexN = 0, wfam = {}, wterr = {}, wterrMap = nil, wterrAge = 0, wdom = {}, wavesFrame = nil,
           ffam = {}, fpart = {}, ftexN = 0, flowBuild = nil, flowCells = nil, flowfx = nil, flowFrame = nil, flowOwn = {} }
    rawset(_G, '__sw_aquarium', AQ)
end

-- the defaults, also the fallback when the engine predates the aquarium keys (engine V7.AQ.DEF is the source of truth)
local DEF = { enabled = true, lens = false, depth = 4, fade = 0.7, schools = true, color = 'level', legend = false,
              legend_rows = 8, waves = 'auto', surf = true, foam = true, veil = false, scan_hz = 4, budget_ms = 2,
              trip_frames = 30, marks = 400, preset = 'aquarium', alpha = { 150, 140, 130, 120, 110, 100, 90 },
              bed = 'auto', bed_depth = 8, bed_tint = 0.6, bed_river = 'pebbles', bed_lift = true, bed_absorb = 1, bed_material = 'sand-mud', bed_below = true, bed_river_mud = true,
              streaks = false, streaks_layer = 'top', shimmer = false, shimmer_depth = 2 }   -- v3 (user 2 Oct): off by default
_ENV.DEF = DEF
-- bed_tex: the bed's own texture cap (families x variants x colours x depth steps x air), apart from the lens's 700 so
-- neither starves the other; bed_cells: most water cells one bed scan keeps (a zoomed-out view); bed_rebuild: scans
-- between rebuilds of an unchanged view (water moves); bed_act_ms: how long `auto` trusts its read of the world's mods
-- wave_tex: the waves' own texture cap; wave_gen_ms: texture making per scan (apart from the scan's own time, so a
-- warm-up never counts as a slow scan); wave_fronts: fronts read per scan; orphans: world.orphaned_flows read per scan;
-- wave_terrain_scans / wave_terrain_cells: the water/land cache is dropped after this many scans or cells
local LIMIT = { units = 2000, blocks = 400, scan_ms = 8, slow_scans = 10, tex = 700, veil_cells = 3000,
                bed_tex = 640, bed_cells = 16000, bed_rebuild = 20, bed_act_ms = 30000, bed_slice_ms = 4, below_cells = 900, bed_build_hz = 16,
                wave_tex = 400, wave_gen_ms = 6, wave_fronts = 4000, orphans = 2000, wave_terrain_scans = 40,
                wave_terrain_cells = 200000, flow_tex = 400, flow_gen_ms = 5, flow_cells = 2500, flow_rebuild = 20,
                wave_lift = 2, wave_slice_ms = 4, wave_build_scans = 240 }
-- wave_slice_ms: one waves scan's time slice (the build resumes next scan; at any zoom no scan runs long);
-- wave_build_scans: a build that has not finished by then starts again (the sea has moved on)
-- wave_lift: how far below an open cell the waves look for the sea (rig 2 Oct 23:20: DF puts every wave front and
-- OceanWave flow on the open level just above the sea's water, so from the beach level the sea is one level down)
-- bed_slice_ms: one bed scan's time slice (cells, textures, sheet decode); under scan_ms, so a long first build that
-- runs to its deadline scan after scan is not counted as slow scans (which would trip the fuse)
-- flow_*: the moving-water layer's own texture cap, sprite making per scan, most cells a frame paints (a zoomed-out view
-- is thinned evenly past it), scans before an unchanged view is read again
local LAYERS = { 'lens', 'waves', 'veil', 'bed', 'flow' }
local activeInWorld   -- defined with the runtime verbs below; the bed's `auto` asks it (cached)
local worldBake       -- likewise: does the loaded world's copy of the mod carry the baked bed (stamp bed_bake=sand)

--========================================================================================
-- the tool: config, groups, engine helpers (read once per scan, never per frame)
--========================================================================================
local function swCache() return rawget(_G, '__seasonal_wildlife_cache') end
local SW, swAt
local function engine()
    local now = dfhack.getTickCount()
    if not SW or now - (swAt or 0) > 5000 then
        local ok, m = pcall(reqscript, 'seasonal-wildlife')
        SW = ok and m or SW; swAt = now
    end
    return SW
end
-- the aquarium config: the tool's cfg.aquarium over the defaults
local function config()
    local C = swCache()
    local cfg = C and C.cfg
    if not cfg and dfhack.isMapLoaded() then
        local sw = engine()
        if sw then local ok, c = pcall(sw.loadConfig); if ok then cfg = c end end
    end
    local a = (cfg and type(cfg.aquarium) == 'table') and cfg.aquarium or {}
    local out = {}
    for k, v in pairs(DEF) do if a[k] == nil then out[k] = v else out[k] = a[k] end end
    return out, cfg
end
_ENV.config = config

--========================================================================================
-- fuses (one per layer)
--========================================================================================
local function fuse(layer)
    local f = AQ.fuse[layer]
    if not f then
        f = { tripped = false, why = nil, frames = 0, over = 0, ema = 0, worst = 0, scans = 0, scanWorst = 0, slow = 0,
              marks = 0, scanMs = 0, note = '', degrade = 0 }
        AQ.fuse[layer] = f
    end
    return f
end
local function trip(layer, why)
    local f = fuse(layer)
    if f.tripped then return end
    f.tripped, f.why, f.at = true, why, dfhack.getTickCount()
    dfhack.printerr(('seasonal-wildlife aquarium: %s stopped for this session (%s). `seasonal-wildlife aquarium rearm` starts it again.')
        :format(layer, tostring(why)))
    local sw = SW
    if sw and sw.LEDGER then pcall(sw.LEDGER.add, 'fuse', 'water', 'aquarium %s stopped: %s', layer, tostring(why)) end
end
local function rearm(layer)
    local n = 0
    for _, l in ipairs(layer and { layer } or LAYERS) do
        local f = fuse(l)
        if f.tripped then n = n + 1 end
        f.tripped, f.why, f.over, f.ema, f.slow = false, nil, 0, 0, 0
        if (f.degrade or 0) > 0 then n = n + 1 end
        f.degrade, f.degradeWhy = 0, nil
    end
    return n
end
_ENV.rearm = rearm
-- fail soft: a layer may register a degrade step (DEGRADE[layer]() -> what it gave up, or nil when it has nothing left
-- to give up). Over budget for trip_frames frames in a row first takes the next step and starts counting again; only a
-- layer with no step left trips. A bed that silently goes away for the session is the worst outcome (rig 2 Oct).
local DEGRADE = {}
-- the frame's paint time into the layer's average; over budget for trip_frames frames in a row degrades, then trips
local function frameDone(layer, ms, c)
    local f = fuse(layer)
    f.frames = f.frames + 1
    f.ema = f.ema * 0.9 + ms * 0.1
    if ms > f.worst then f.worst = ms end
    if f.ema > c.budget_ms then
        f.over = f.over + 1
        if f.over >= c.trip_frames then
            local step = DEGRADE[layer]
            local what = step and step(f)
            if what then
                f.over = 0
                dfhack.printerr(('seasonal-wildlife aquarium: %s over its paint budget (%.1f ms > %s ms): %s. `seasonal-wildlife aquarium rearm` restores it.')
                    :format(layer, f.ema, c.budget_ms, what))
            else
                trip(layer, ('paint averaged %.1f ms over %d frames, budget %s ms%s'):format(f.ema, f.over, c.budget_ms,
                    (f.degrade or 0) > 0 and (' after degrading (' .. tostring(f.degradeWhy) .. ')') or ''))
            end
        end
    else f.over = 0 end
end
local function scanDone(layer, ms, marks, note)
    local f = fuse(layer)
    f.scans, f.scanMs, f.marks, f.note = f.scans + 1, ms, marks or 0, note or ''
    if ms > f.scanWorst then f.scanWorst = ms end
    if ms > LIMIT.scan_ms then
        f.slow = f.slow + 1
        if f.slow >= LIMIT.slow_scans then trip(layer, ('%d scans in a row over %d ms (last %d ms)'):format(f.slow, LIMIT.scan_ms, ms)) end
    else f.slow = 0 end
end

--========================================================================================
-- sprites, drawn in code (no image ships): coverage masks per shape, tinted and faded per use
--========================================================================================
local function pack(r, g, b, a) return ((r & 255) << 24) | ((g & 255) << 16) | ((b & 255) << 8) | (a & 255) end
_ENV.pack = pack
-- DF's tile: DFHack builds the surface as SDL_PIXELFORMAT_RGBA32 (R at the LOWEST address), so on a little-endian host
-- a pixel uint32 is 0xAABBGGRR. Every sprite here is made as 0xRRGGBBAA (pack, the gfx module, the previews), so each
-- one is byte-swapped on its way to DF (rig 2 Oct: unswapped, a pale crest at alpha 60 drew as opaque cyan).
local function toDF(px)
    local out = {}
    for i = 1, #px do
        local v = px[i]
        out[i] = ((v >> 24) & 255) | (((v >> 16) & 255) << 8) | (((v >> 8) & 255) << 16) | ((v & 255) << 24)
    end
    return out
end
local function makeTile(px, w, h) return dfhack.textures.createTile(toDF(px), w, h) end
_ENV.toDF, _ENV.makeTile = toDF, makeTile
local function ell(x, y, cx, cy, rx, ry) local dx, dy = (x - cx) / rx, (y - cy) / ry; return dx * dx + dy * dy <= 1 end
local function tri(x, y, ax, ay, bx, by, cx, cy)
    local d1 = (x - bx) * (ay - by) - (ax - bx) * (y - by)
    local d2 = (x - cx) * (by - cy) - (bx - cx) * (y - cy)
    local d3 = (x - ax) * (cy - ay) - (cx - ax) * (y - ay)
    local neg, pos = (d1 < 0) or (d2 < 0) or (d3 < 0), (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (neg and pos)
end
local function seg(x, y, ax, ay, bx, by, r)   -- capsule
    local vx, vy, wx, wy = bx - ax, by - ay, x - ax, y - ay
    local t = math.max(0, math.min(1, (wx * vx + wy * vy) / (vx * vx + vy * vy)))
    local dx, dy = x - (ax + t * vx), y - (ay + t * vy)
    return dx * dx + dy * dy <= r * r
end
local SHAPES = {
    fish = function(x, y)
        if ell(x, y, 9.5, 14.5, 1.3, 1.3) then return false end   -- the eye
        return ell(x, y, 14, 16, 9, 5) or tri(x, y, 21, 16, 29, 9, 29, 23)
    end,
    shark = function(x, y)
        return ell(x, y, 15, 17, 12, 4) or tri(x, y, 12, 14, 18, 14, 15, 6) or tri(x, y, 25, 17, 31, 9, 31, 22)
            or tri(x, y, 11, 19, 16, 19, 10, 24)
    end,
    eel = function(x, y)
        if x < 3 or x > 29 then return false end
        local y0 = 16 + 4 * math.sin((x - 3) / 26 * 2 * math.pi)
        return math.abs(y - y0) <= 2.4 - (x - 3) / 26 * 1.2
    end,
    turtle = function(x, y)
        return ell(x, y, 16, 17, 8, 7) or ell(x, y, 16, 7, 3, 3) or ell(x, y, 8, 11, 3.5, 2) or ell(x, y, 24, 11, 3.5, 2)
            or ell(x, y, 9, 24, 3, 2) or ell(x, y, 23, 24, 3, 2)
    end,
    crab = function(x, y)
        return ell(x, y, 16, 18, 8, 5) or ell(x, y, 6, 9, 3.5, 3) or ell(x, y, 26, 9, 3.5, 3)
            or seg(x, y, 10, 15, 6, 10, 1.2) or seg(x, y, 22, 15, 26, 10, 1.2)
            or seg(x, y, 9, 20, 4, 25, 0.9) or seg(x, y, 11, 22, 7, 28, 0.9) or seg(x, y, 23, 20, 28, 25, 0.9) or seg(x, y, 21, 22, 25, 28, 0.9)
    end,
    jelly = function(x, y)
        if y <= 14 and ell(x, y, 16, 14, 9, 8) then return true end
        if y < 14 or y > 29 then return false end
        for _, tx in ipairs({ 10, 14, 18, 22 }) do
            if math.abs(x - (tx + 1.5 * math.sin((y - 14) / 4))) <= 0.8 then return true end
        end
        return false
    end,
    mammal = function(x, y)
        return ell(x, y, 14, 17, 11, 5.5) or tri(x, y, 24, 17, 31, 10, 31, 24) or ell(x, y, 12, 22, 3, 1.5)
    end,
    sponge = function(x, y)
        return seg(x, y, 10, 28, 9, 13, 2.5) or seg(x, y, 16, 28, 16, 7, 2.8) or seg(x, y, 22, 28, 23, 14, 2.5) or ell(x, y, 16, 28, 9, 2.5)
    end,
    other = function(x, y) return math.abs(x - 16) + math.abs(y - 16) <= 9 end,
    ring = function(x, y) local d = math.sqrt((x - 16) ^ 2 + (y - 16) ^ 2); return d >= 13.6 and d <= 15.2 end,
    bNW = function(x, y) return (x >= 2 and x <= 13 and y >= 2 and y <= 4.5) or (x >= 2 and x <= 4.5 and y >= 2 and y <= 13) end,
    bNE = function(x, y) return (x >= 19 and x <= 30 and y >= 2 and y <= 4.5) or (x >= 27.5 and x <= 30 and y >= 2 and y <= 13) end,
    bSW = function(x, y) return (x >= 2 and x <= 13 and y >= 27.5 and y <= 30) or (x >= 2 and x <= 4.5 and y >= 19 and y <= 30) end,
    bSE = function(x, y) return (x >= 19 and x <= 30 and y >= 27.5 and y <= 30) or (x >= 27.5 and x <= 30 and y >= 19 and y <= 30) end,
}
-- coverage 0..4 (2x2 supersampling) and a one-pixel outline ring, per shape, cached
local function mask(shape)
    local m = AQ.masks[shape]
    if m then return m end
    local fn = SHAPES[shape] or SHAPES.other
    local cov, out = {}, {}
    for y = 0, 31 do
        for x = 0, 31 do
            local n = 0
            for sy = 0, 1 do for sx = 0, 1 do if fn(x + 0.25 + sx * 0.5, y + 0.25 + sy * 0.5) then n = n + 1 end end end
            cov[y * 32 + x + 1] = n
        end
    end
    for y = 0, 31 do
        for x = 0, 31 do
            local i = y * 32 + x + 1
            local o = 0
            if cov[i] == 0 then
                for dy = -1, 1 do for dx = -1, 1 do
                    local xx, yy = x + dx, y + dy
                    if xx >= 0 and xx < 32 and yy >= 0 and yy < 32 and cov[yy * 32 + xx + 1] >= 2 then o = 1 end
                end end
            end
            out[i] = o
        end
    end
    m = { cov = cov, out = out }
    AQ.masks[shape] = m
    return m
end
_ENV.mask = mask
-- the packed pixels of shape(s) in colour rgb at alpha a; extra = a second shape drawn in the same colour (the leader ring)
local function pixels(shape, rgb, a, extra, outline)
    local m = mask(shape)
    local e = extra and mask(extra)
    local px = {}
    local r, g, b = rgb[1], rgb[2], rgb[3]
    for i = 1, 1024 do
        local c = m.cov[i]
        if e and e.cov[i] > c then c = e.cov[i] end
        if c > 0 then px[i] = pack(r, g, b, (a * c) // 4)
        elseif outline and (m.out[i] == 1 or (e and e.out[i] == 1)) then px[i] = pack(8, 18, 36, (a * 3) // 5)
        else px[i] = 0 end
    end
    return px
end
_ENV.pixels = pixels
-- a texture handle for this look, made on first use (at scan time, never in a frame); nil when the cap is reached
local function texture(key, shape, rgb, a, extra, outline)
    local h = AQ.tex[key]
    if h ~= nil then return h or nil end
    if AQ.texN >= LIMIT.tex then return nil end
    local ok, handle = pcall(makeTile, pixels(shape, rgb, a, extra, outline), 32, 32)
    AQ.tex[key] = ok and handle or false
    if ok then AQ.texN = AQ.texN + 1 end
    return ok and handle or nil
end
_ENV.texture = texture

--========================================================================================
-- who is down there: kind, level, name (cached per race)
--========================================================================================
local KIND_WORDS = {
    { 'sponge', { 'SPONGE' } },
    { 'jelly', { 'JELLYFISH', 'MAN_O_WAR', 'MAN-O-WAR', 'JELLY' } },
    { 'crab', { 'CRAB', 'LOBSTER', 'SHRIMP', 'CRAYFISH', 'CRAWFISH', 'KRILL', 'BARNACLE', 'MUSSEL', 'OYSTER', 'CLAM', 'SNAIL', 'OCTOPUS', 'SQUID', 'NAUTILUS', 'STARFISH', 'URCHIN' } },
    { 'turtle', { 'TURTLE', 'TERRAPIN', 'TORTOISE', 'ALLIGATOR', 'CROCODILE', 'CAIMAN', 'GHARIAL', 'IGUANA', 'NEWT', 'SALAMANDER', 'FROG', 'TOAD', 'AXOLOTL', 'OLM' } },
    { 'mammal', { 'WHALE', 'DOLPHIN', 'PORPOISE', 'ORCA', 'NARWHAL', 'BELUGA', 'SEAL', 'WALRUS', 'SEA LION', 'SEA_LION', 'OTTER', 'MANATEE', 'DUGONG', 'PLATYPUS', 'BEAVER', 'HIPPO', 'CAPYBARA', 'MINK', 'MUSKRAT' } },
    { 'shark', { 'SHARK', 'SAWFISH', 'SWORDFISH', 'MARLIN', 'BARRACUDA', 'TUNA', 'MANTA', 'STINGRAY', 'RAY' } },
    { 'eel', { 'EEL', 'LAMPREY', 'SERPENT', 'HAGFISH', 'SNAKE', 'NAGA' } },
}
_ENV.KIND_WORDS = KIND_WORDS
local function kindOf(token, immobile)
    local t = tostring(token):upper()
    for _, kw in ipairs(KIND_WORDS) do
        for _, w in ipairs(kw[2]) do if t:find(w, 1, true) then return kw[1] end end
    end
    if immobile then return 'sponge' end
    return 'fish'
end
_ENV.kindOf = kindOf
local function hasFlag(craw, name)
    local ok, v = pcall(function() return craw.flags[name] end)
    if ok and v then return true end
    local ok2, cs = pcall(function() return craw.caste[0] end)
    if ok2 and cs then local ok3, v3 = pcall(function() return cs.flags[name] end); return ok3 and v3 and true or false end
    return false
end
local function raceInfo(race, cfg)
    local ri = AQ.race[race]
    if ri then return ri end
    local craw = df.creature_raw.find(race)
    local token = craw and craw.creature_id or ('#' .. tostring(race))
    local immobile = craw and (hasFlag(craw, 'IMMOBILE') or hasFlag(craw, 'IMMOBILE_LAND')) or false
    local kind = kindOf(token, immobile)
    local level = 'H'
    local sw = engine()
    if craw and sw then
        local okR, role = pcall(sw.MODEL.role, craw)
        local cat = okR and role or 'prey'
        local okL, lv = pcall(sw.V7.WAT.levelOf, cfg, { token = token, cat = cat })
        if okL and lv then level = lv elseif cat == 'predator' then level = 'C' end
    elseif craw and (hasFlag(craw, 'CARNIVORE') or hasFlag(craw, 'LARGE_PREDATOR')) then
        level = hasFlag(craw, 'LARGE_PREDATOR') and 'A' or 'C'
    end
    if kind == 'sponge' then level = 'S' end
    local okN, name = pcall(dfhack.units.getRaceReadableNameById, race)
    local okP, plural = pcall(dfhack.units.getRaceNamePluralById, race)
    ri = { token = token, kind = kind, level = level, name = okN and name or token, plural = okP and plural or token }
    AQ.race[race] = ri
    return ri
end
_ENV.raceInfo = raceInfo

local COLORS = {
    level = { H = { 90, 225, 205 }, C = { 255, 192, 72 }, A = { 255, 84, 84 }, S = { 200, 140, 255 } },
    kind = { fish = { 90, 225, 205 }, shark = { 255, 84, 84 }, eel = { 190, 205, 90 }, turtle = { 110, 220, 110 },
             crab = { 255, 150, 70 }, jelly = { 255, 140, 210 }, mammal = { 150, 180, 255 }, sponge = { 200, 140, 255 },
             other = { 230, 230, 230 } },
    group = { { 255, 214, 92 }, { 120, 220, 255 }, { 255, 128, 180 }, { 140, 255, 140 }, { 255, 160, 90 },
              { 190, 150, 255 }, { 90, 255, 220 }, { 255, 255, 255 } },
}
local LEVEL_PEN = { H = COLOR_LIGHTCYAN, C = COLOR_YELLOW, A = COLOR_LIGHTRED, S = COLOR_LIGHTMAGENTA }
local function alphaFor(d, fade)
    local a = math.floor(230 * fade ^ (d - 1) + 0.5)
    a = math.max(40, a)
    return (a // 12) * 12   -- quantised: fewer distinct textures
end
_ENV.alphaFor = alphaFor

--========================================================================================
-- map helpers
--========================================================================================
local OPEN
local function isOpen(x, y, z)
    local tt = dfhack.maps.getTileType(x, y, z)
    if not tt then return false end
    if not OPEN then OPEN = df.tiletype_shape_basic.Open end
    local shape = df.tiletype.attrs[tt].shape
    return df.tiletype_shape.attrs[shape].basic_shape == OPEN
end
_ENV.isOpen = isOpen
local function waterAt(x, y, z)
    local des = dfhack.maps.getTileFlags(x, y, z)
    if not des or des.flow_size < 1 then return 0 end
    if des.liquid_type == true or des.liquid_type == 1 or des.liquid_type == df.tile_liquid.Magma then return 0 end
    return des.flow_size
end
_ENV.waterAt = waterAt
-- the map's identity: the bed's material caches and the waves' terrain cache are per map
local function mapId()
    local ok, id = pcall(function()
        local m = df.global.world.map
        return ('%s,%s,%s,%s'):format(m.region_x, m.region_y, m.region_z, m.x_count)
    end)
    return ok and id or '?'
end
-- the map rectangle the main viewport shows, and its size in cells
local function view()
    local mv = df.global.gps.main_viewport
    local W, H = mv.dim_x, mv.dim_y
    local x1, y1, z = df.global.window_x, df.global.window_y, df.global.window_z
    return x1, y1, x1 + W - 1, y1 + H - 1, z, W, H
end
_ENV.view = view

--========================================================================================
-- the lens scan
--========================================================================================
local function groupIndex()
    local C = swCache()
    local g = C and C.groups
    if not g then local sw = engine(); if sw then local ok, gg = pcall(sw.loadGroups); if ok then g = gg end end end
    local of, sponge = {}, {}
    if not g then return of, sponge, {} end
    local list = g.groups or {}
    for gi, grp in ipairs(list) do
        for _, id in ipairs(grp.ids or {}) do of[id] = gi end
    end
    for _, id in ipairs((g.sponges or {}).ids or {}) do sponge[id] = true end
    return of, sponge, list
end
local function originOf(grp)
    if not grp then return 'DF' end
    return grp.irruption and 'irruption' or grp.tag and 'apex' or grp.placed and 'placed' or grp.drawn and 'drawn'
        or grp.native and 'native' or grp.seeded and 'seeded' or grp.resident and 'resident' or 'DF wave'
end

function scanLens(c, cfg)
    local t0 = dfhack.getTickCount()
    local deadline = t0 + LIMIT.scan_ms
    local x1, y1, x2, y2, z = view()
    local zlo = math.max(0, z - c.depth)
    local run = { z = z, n = 0, x = {}, y = {}, h = {}, d = {}, brackets = {}, species = {}, total = 0, stopped = false }
    if z <= 0 or zlo > z - 1 then AQ.lens = run; scanDone('lens', 0, 0, 'no level below'); return run end
    local units = dfhack.units.getUnitsInBox(x1, y1, zlo, x2, y2, z - 1)
    if #units == 0 then AQ.lens = run; scanDone('lens', dfhack.getTickCount() - t0, 0, 'nothing below'); return run end
    local of, sponge, groups = groupIndex()
    local best = {}       -- cell key -> slot
    local seenGroup = {}  -- group index -> { minx, miny, maxx, maxy, dsum, n, gi }
    local openCache = {}
    local function openAt(x, y, zz)
        local k = (zz * 4096 + y) * 4096 + x
        local v = openCache[k]
        if v == nil then v = isOpen(x, y, zz); openCache[k] = v end
        return v
    end
    local considered = 0
    for _, u in ipairs(units) do
        considered = considered + 1
        if considered > LIMIT.units or run.n >= c.marks then run.stopped = 'cap'; break end
        if considered % 64 == 0 and dfhack.getTickCount() > deadline then run.stopped = 'deadline'; break end
        if not dfhack.units.isDead(u) then
            local x, y, uz = dfhack.units.getPosition(u)
            if x and uz < z and dfhack.maps.isTileVisible(x, y, uz) and waterAt(x, y, uz) > 0 then
                local clear = true
                for zz = uz + 1, z do if not openAt(x, y, zz) then clear = false; break end end
                if clear then
                    local d = z - uz
                    local ri = raceInfo(u.race, cfg)
                    local gi = of[u.id]
                    local grp = gi and groups[gi]
                    local kind = sponge[u.id] and 'sponge' or ri.kind
                    local key = (y - y1) * 4096 + (x - x1)
                    local slot = best[key]
                    local isLeader = grp and grp.leader == u.id and c.schools
                    if not slot or run.d[slot] > d then
                        local rgb
                        if c.color == 'kind' then rgb = COLORS.kind[kind] or COLORS.kind.other
                        elseif c.color == 'group' and gi then rgb = COLORS.group[(gi - 1) % #COLORS.group + 1]
                        else rgb = COLORS.level[kind == 'sponge' and 'S' or ri.level] or COLORS.level.H end
                        local a = alphaFor(d, c.fade)
                        local ck = (c.color == 'group' and gi) and ('g' .. tostring(gi))
                            or (c.color == 'kind' and kind or (kind == 'sponge' and 'S' or ri.level))   -- the key names the colour used
                        local h = texture(('L|%s|%s|%d|%s'):format(kind, ck, a, isLeader and 'r' or ''), kind, rgb, a,
                                          isLeader and 'ring' or nil, true)
                        if h then
                            if not slot then run.n = run.n + 1; slot = run.n; best[key] = slot end
                            run.x[slot], run.y[slot], run.h[slot], run.d[slot] = x, y, h, d
                        end
                    end
                    -- legend and brackets
                    run.total = run.total + 1
                    local sp = run.species[u.race]
                    if not sp then
                        sp = { race = u.race, info = ri, n = 0, dmin = d, dmax = d, groups = {}, led = false, panic = false, origin = {} }
                        run.species[u.race] = sp
                    end
                    sp.n = sp.n + 1
                    if d < sp.dmin then sp.dmin = d end
                    if d > sp.dmax then sp.dmax = d end
                    sp.origin[originOf(grp)] = true
                    if grp then
                        sp.groups[gi] = grp.label or 'group'
                        if grp.leader == u.id then sp.led = true end
                        if grp.panic then sp.panic = true end
                        if c.schools then
                            local b = seenGroup[gi]
                            if not b then b = { minx = x, miny = y, maxx = x, maxy = y, dsum = 0, n = 0, gi = gi }; seenGroup[gi] = b end
                            if x < b.minx then b.minx = x end
                            if y < b.miny then b.miny = y end
                            if x > b.maxx then b.maxx = x end
                            if y > b.maxy then b.maxy = y end
                            b.dsum, b.n = b.dsum + d, b.n + 1
                        end
                    end
                end
            end
        end
    end
    -- brackets: the corners of each school or pod box, a cell outside it, where no creature is marked
    for gi, b in pairs(seenGroup) do
        if b.n >= 2 then
            local rgb = c.color == 'group' and COLORS.group[(gi - 1) % #COLORS.group + 1] or { 235, 245, 255 }
            local a = alphaFor(math.floor(b.dsum / b.n + 0.5), c.fade)
            for _, corner in ipairs({ { 'bNW', b.minx - 1, b.miny - 1 }, { 'bNE', b.maxx + 1, b.miny - 1 },
                                      { 'bSW', b.minx - 1, b.maxy + 1 }, { 'bSE', b.maxx + 1, b.maxy + 1 } }) do
                local key = (corner[3] - y1) * 4096 + (corner[2] - x1)
                if not best[key] then
                    local h = texture(('B|%s|%d|%d|%d|%d'):format(corner[1], rgb[1], rgb[2], rgb[3], a), corner[1], rgb, a, nil, true)
                    if h then run.brackets[#run.brackets + 1] = { corner[2], corner[3], h } end
                end
            end
        end
    end
    AQ.lens = run
    scanDone('lens', dfhack.getTickCount() - t0, run.n, run.stopped and ('stopped: ' .. run.stopped) or ('%d below'):format(run.total))
    return run
end

-- the legend's rows from the last lens scan
function legendRows(c)
    local run = AQ.lens
    if not run or run.total == 0 then return {} end
    local list = {}
    for _, sp in pairs(run.species) do list[#list + 1] = sp end
    table.sort(list, function(a, b) if a.n ~= b.n then return a.n > b.n end; return a.info.name < b.info.name end)
    local rows = {}
    for i = 1, math.min(#list, c.legend_rows) do
        local sp = list[i]
        local ngroups, label = 0, nil
        for _, l in pairs(sp.groups) do ngroups = ngroups + 1; label = l end
        local tags = {}
        if ngroups > 0 then
            tags[#tags + 1] = (ngroups > 1 and (ngroups .. ' ') or '') .. tostring(label or 'group') .. (ngroups > 1 and 's' or '')
            tags[#tags + 1] = sp.led and 'led' or 'no leader'
        end
        if sp.panic then tags[#tags + 1] = 'PANIC' end
        local src = {}
        for o in pairs(sp.origin) do src[#src + 1] = o end
        table.sort(src)
        rows[#rows + 1] = { race = sp.race, kind = sp.info.kind, level = sp.info.level, n = sp.n,
                            name = sp.n > 1 and sp.info.plural or sp.info.name,
                            depth = sp.dmin == sp.dmax and ('-' .. sp.dmin) or ('-%d..-%d'):format(sp.dmin, sp.dmax),
                            tags = table.concat(tags, ' '), origin = table.concat(src, ',') }
    end
    rows.more = #list - #rows
    return rows
end

--========================================================================================
-- the waves (v7.1-waves; docs/v7.1/aquarium.md section 4.3). DF simulates ocean waves in graphics mode (rig, 2 Oct
-- 23:05, AQUA_SHORE16: 24 makers, up to 1,137 fronts and 8,129 OceanWave/SeaFoam flows at once) but draws nothing
-- for them. The overlay draws from DF's own footprint, the OceanWave and SeaFoam flows of the view level, and uses the
-- fronts (cur -> dest) only to orient: a crest is a soft line ACROSS the direction of travel (a front reads as a line
-- across the sea, not a column of marks). Every painted cell is a water cell (designation flow_size > 0, not magma);
-- a flow on dry land (DF's waves run up the beach) lights the water cells beside it as surf, never the land.
--========================================================================================
-- the eight directions of travel, screen axes (y grows south); index 1 = N, clockwise
local WDIR = { { 0, -1, 'N' }, { 1, -1, 'NE' }, { 1, 0, 'E' }, { 1, 1, 'SE' }, { 0, 1, 'S' }, { -1, 1, 'SW' }, { -1, 0, 'W' }, { -1, -1, 'NW' } }
_ENV.WDIR = WDIR
local function dirOf(dx, dy)
    if dx == 0 and dy == 0 then return nil end
    return math.floor(math.atan(dx, -dy) / (math.pi / 4) + 0.5) % 8 + 1
end
_ENV.dirOf = dirOf
-- frames per sprite family and ms per frame; the crest's peak alpha (one strength: one clean family); the surf's peak
-- alpha. The mist is DF's own tiles (FLOW_WATER_MIST 1..4 = page rows 0..3, dense -> thin spray), drawn as they are:
-- the density shows in which rows a cell cycles through (MIST_SEQ, 6 frames) and, for the thinnest, in every other cell
-- left bare (MIST_SKIP) -- no pixel is re-made. Tiers 1..4 by density (<25, <50, <75, >=75) on the beach; 5, 6 (light,
-- dense) for the spray over the water beside it.
local WAVE = { NF = { crest = 4, surf = 4, mist = 6 }, MS = { crest = 220, surf = 220, mist = 180 },
               CREST = { 95 }, SURF = 105,
               MIST_SEQ = { { 3, 3, 2, 3, 3, 3 }, { 2, 3, 2, 3, 3, 2 }, { 1, 2, 1, 2, 3, 2 }, { 0, 1, 0, 1, 2, 1 },
                            { 3, 3, 3, 2, 3, 3 }, { 2, 3, 3, 2, 3, 3 } },
               MIST_SKIP = { [1] = true, [5] = true },
               PRIO = { shore = 7, front = 6, cap = 5, crest = 4, mist = 3 } }   -- cap < front: abreast fronts join unbroken
_ENV.WAVE = WAVE

--========================================================================================
-- wave sprites: soft translucent highlights with feathered alpha, made at run time (dfhack.textures.createTile)
--========================================================================================
local function gauss(d, s) return math.exp(-(d * d) / (2 * s * s)) end
local function smooth(e0, e1, x)
    local t = (x - e0) / (e1 - e0)
    if t < 0 then t = 0 elseif t > 1 then t = 1 end
    return t * t * (3 - 2 * t)
end
-- a pixel from up to three layers (colour + coverage 0..1), composited over each other: alpha 1 - prod(1 - a), colour
-- the coverage-weighted mean; alpha capped at `cap`
local function layered(a1, c1, a2, c2, a3, c3, cap)
    local keep, w, r, g, b = 1, 0, 0, 0, 0
    if a1 > 0.002 then keep = keep * (1 - a1); w = w + a1; r, g, b = r + a1 * c1[1], g + a1 * c1[2], b + a1 * c1[3] end
    if a2 > 0.002 then keep = keep * (1 - a2); w = w + a2; r, g, b = r + a2 * c2[1], g + a2 * c2[2], b + a2 * c2[3] end
    if a3 and a3 > 0.002 then keep = keep * (1 - a3); w = w + a3; r, g, b = r + a3 * c3[1], g + a3 * c3[2], b + a3 * c3[3] end
    if w == 0 then return 0 end
    local a = math.floor(math.min(cap, (1 - keep) * 255) + 0.5)
    if a <= 0 then return 0 end
    return pack(math.floor(r / w + 0.5), math.floor(g / w + 0.5), math.floor(b / w + 0.5), a)
end
-- top over bottom, both 0xRRGGBBAA
local function over(top, bot)
    local ta = top & 255
    if ta == 0 then return bot end
    local ba = bot & 255
    if ba == 0 or ta == 255 then return top end
    local at, ab = ta / 255, (ba / 255) * (1 - ta / 255)
    local ao = at + ab
    local function ch(sh) return math.floor((((top >> sh) & 255) * at + ((bot >> sh) & 255) * ab) / ao + 0.5) end
    return pack(ch(24), ch(16), ch(8), math.floor(ao * 255 + 0.5))
end
_ENV.over = over
local C_CORE, C_BACK, C_SURF, C_HAZE = { 236, 250, 255 }, { 170, 226, 236 }, { 240, 251, 255 }, { 196, 234, 242 }
-- a small deterministic generator (sprite layouts per variant)
local function lcg(seed)
    local st = seed & 0x7fffffff
    return function() st = (st * 1103515245 + 12345) & 0x7fffffff; return st / 0x7fffffff end
end

-- crest (d = direction of travel, f = frame, peak alpha, cap = nil | 1 | -1: fades out toward +p / -p, the end of a
-- line | 2: both ends fade, a crest with no crest beside it). One clean line ACROSS the travel: a soft bright core a
-- little ahead of the centre, sharper on the leading side, and the lit back of the wave fading over ~10 px behind.
-- The line runs through the whole cell along p (periodic in the cell: 32 px cardinal; 64 lattice units diagonal, the
-- distance between diagonal neighbours), so cells side by side join into one line. Frames: the core breathes a pixel
-- forward and back and a gentle wobble runs along it.
local function crestPixels(d, f, peak, cap)
    local tx, ty = WDIR[d][1], WDIR[d][2]
    local diag = tx ~= 0 and ty ~= 0
    local nrm = diag and (1 / math.sqrt(2)) or 1
    local pxv, pyv = -ty, tx
    local L = diag and 64 or 32
    local ph = 2 * math.pi * f / WAVE.NF.crest
    local s0 = 3 + 0.9 * math.sin(ph)
    local A = (peak / 255) * (0.92 + 0.08 * math.cos(ph))
    local out = {}
    local rowHook = AQ.wrow   -- set while a build runs: yields at the slice's end, so a sprite is made across scans
    for y = 0, 31 do
        if rowHook then rowHook() end
        for x = 0, 31 do
            local dx, dy = x + 0.5 - 16, y + 0.5 - 16
            local s = (dx * tx + dy * ty) * nrm          -- ahead of the centre (+), behind (-), in px
            local uq = dx * pxv + dy * pyv               -- along the line, lattice units
            local u = uq * nrm                           -- along the line, px
            local sp = s - s0 - 0.7 * math.sin(2 * math.pi * uq / L + ph)
            local core = sp >= 0 and gauss(sp, 1.2) or gauss(sp, 1.9)
            local back = sp < 0 and 0.26 * smooth(-12, -1.5, sp) or 0
            local taper = 1
            if cap == 2 then taper = 1 - smooth(4, 14, math.abs(u))      -- a short crest: both ends fade
            elseif cap then taper = 1 - smooth(-12, 10, cap * u) end
            local k = A * taper
            out[y * 32 + x + 1] = layered(k * core, C_CORE, k * back, C_BACK, nil, nil, 200)
        end
    end
    return out
end
-- surf: the waterline wash on a sea cell beside the shore. lm = which neighbours are land (bits N 1, E 2, S 4, W 8; a
-- corner NE 16, SE 32, SW 64, NW 128 only when neither side beside it is land). Each pixel's distance to the nearest
-- land (a side's edge or a corner's point) sets the profile, so straight shores and corners join up: a soft band laps
-- toward the shore and back over the frames, a faint line at the water's edge. Clearly translucent (peak WAVE.SURF).
local SURF_SIDES = { { 1, 'N' }, { 2, 'E' }, { 4, 'S' }, { 8, 'W' } }
local function surfPixels(lm, f)
    local lap = 0.5 - 0.5 * math.cos(2 * math.pi * f / WAVE.NF.surf)   -- 0 out, 1 at the shore
    local eb = 2.5 + 6.5 * (1 - lap)
    local A = WAVE.SURF / 255
    local phl = 2 * math.pi * f / WAVE.NF.surf
    local out = {}
    local rowHook = AQ.wrow
    for y = 0, 31 do
        if rowHook then rowHook() end
        for x = 0, 31 do
            local px, py = x + 0.5, y + 0.5
            local e = 99
            for _, sd in ipairs(SURF_SIDES) do
                if lm & sd[1] ~= 0 then
                    local v = (sd[2] == 'N' and py) or (sd[2] == 'S' and 32 - py) or (sd[2] == 'W' and px) or (32 - px)
                    if v < e then e = v end
                end
            end
            if lm & 16 ~= 0 then e = math.min(e, math.sqrt((32 - px) ^ 2 + py ^ 2)) end
            if lm & 32 ~= 0 then e = math.min(e, math.sqrt((32 - px) ^ 2 + (32 - py) ^ 2)) end
            if lm & 64 ~= 0 then e = math.min(e, math.sqrt(px ^ 2 + (32 - py) ^ 2)) end
            if lm & 128 ~= 0 then e = math.min(e, math.sqrt(px ^ 2 + py ^ 2)) end
            local n1 = 0.5 + 0.5 * math.sin(2 * math.pi * (px + py) / 32 + 0.6 + phl)
            local lace = 0.45 + 0.55 * n1
            local band = 0.65 * gauss(e - eb, 1.7 + 1.2 * (1 - lap)) * lace
            local line = 0.25 * gauss(e - 0.7, 1.1)
            local haze = (e < eb) and 0.06 * smooth(-0.5, 1.5, e) * smooth(eb + 0.5, eb - 2, e) or 0
            out[y * 32 + x + 1] = layered(A * band, C_SURF, A * line, C_SURF, A * haze, C_HAZE, 120)
        end
    end
    return out
end
-- the pixels of one generated wave texture. crest: d = direction, tier = strength, cap. surf: d = the land mask
local function wavePixels(kind, d, tier, f, cap)
    if kind == 'crest' then return crestPixels(d, f, WAVE.CREST[tier] or WAVE.CREST[1], cap)
    elseif kind == 'surf' then return surfPixels(d, f) end
    error('no wave sprite ' .. tostring(kind), 0)
end
_ENV.wavePixels = wavePixels
-- DF's own mist tiles, as loaded: the aquarium mod's SW_AQ_MIST page (column 0, rows 0..3: DF's art, alpha scaled and
-- tinted by the preset) when the world has it, else vanilla EVENT_FLOWS column 2 rows 0..3. Nothing is decoded or
-- made. false when neither is loaded (status says so)
local function mistTiles()
    if AQ.wmistRaw ~= nil then return AQ.wmistRaw end
    local found = false
    for _, src in ipairs({ { 'SW_AQ_MIST', 0 }, { 'EVENT_FLOWS', 2 } }) do
        local raw = {}
        for r = 0, 3 do
            local ok, tp = pcall(dfhack.screen.findGraphicsTile, src[1], src[2], r)
            if ok and tp then raw[r] = tp end
        end
        if raw[0] and raw[3] then raw.page = src[1]; found = raw; break end
    end
    AQ.wmistRaw = found
    return found
end
_ENV.mistTiles = mistTiles
-- a family's frames, made on first use. crest, surf: generated textures (handles); the pixel loops yield at the slice's
-- end a row at a time (AQ.wrow), so making a sprite never runs a scan long, however slow the Lua. mist: DF's own tiles
-- in the tier's row sequence (fam.raw: texposes; nothing made). nil at the cap or when it cannot be made
local function waveFamily(kind, d, tier, cap, pace, run, want)
    local key = ('%s|%d|%d|%s'):format(kind, d, tier, cap and tostring(cap) or '')
    local fam = AQ.wfam[key]
    if fam ~= nil then return fam or nil end
    if kind == 'mist' then
        local raw = mistTiles()
        if not raw then AQ.wfam[key] = false; return nil end
        fam = { raw = true }
        for f, row in ipairs(WAVE.MIST_SEQ[tier] or WAVE.MIST_SEQ[1]) do fam[f] = raw[row] end
        AQ.wfam[key] = fam
        return fam
    end
    if want then   -- not made yet: queued (with the cells waiting for it), made after the run is published
        local w = want[key]
        if not w then w = { kind, d, tier, cap, cells = {} }; want[key] = w; want.order[#want.order + 1] = key end
        w.cells[#w.cells + 1] = want.cell
        run.warming = run.warming + 1
        return nil
    end
    local hs = {}
    for f = 0, WAVE.NF[kind] - 1 do
        pace()
        if AQ.wtexN >= LIMIT.wave_tex then run.capped = run.capped + 1; return nil end
        local px = wavePixels(kind, d, tier, f, cap)
        local ok, h = pcall(makeTile, px, 32, 32)
        run.made = run.made + 1
        if not ok or not h then AQ.wfam[key] = false; return nil end
        AQ.wtexN = AQ.wtexN + 1
        hs[#hs + 1] = h
    end
    AQ.wfam[key] = hs
    return hs
end
_ENV.waveFamily = waveFamily

--========================================================================================
-- the waves scan
--========================================================================================
function wavesOn(c)
    if c.waves == 'off' then return false, 'off' end
    local ok, n = pcall(function() return #df.global.world.event.ocean_wave_makers end)
    n = ok and n or 0
    if c.waves == 'on' then return true, ('on (%d wave makers)'):format(n) end
    return n > 0, n > 0 and ('auto: ocean (%d wave makers)'):format(n) or 'auto: no ocean on this map'
end
-- the levels DF draws below the view (number_of_lower_elevations_shown, 0..8)
local function lowerShown()
    local K = 0
    pcall(function() K = df.global.d_init.display.number_of_lower_elevations_shown end)
    return math.max(0, math.min(8, tonumber(K) or 0))
end
_ENV.lowerShown = lowerShown
-- what a cell of the view level is, cached per map for wave_terrain_scans builds: 'w' water at this level (visible,
-- not magma); 's1' / 's2' the SEA SEEN BELOW: open air whose open column reaches visible water 1 or 2 levels down
-- (within the levels DF draws below; the bed's lift test) -- the beach-level view of the sea, where DF keeps its wave
-- fronts and flows; 'l' land (anything not open: floor, ramp, wall, ...), 'o' open air with no water near below,
-- 'h' hidden
local SEA = { w = 0, s1 = 1, s2 = 2 }
_ENV.SEA = SEA
local function terrainReset()
    local id = mapId()
    local K = math.min(LIMIT.wave_lift, lowerShown())
    AQ.wterrAge = (AQ.wterrAge or 0) + 1
    if AQ.wterrMap ~= id or AQ.wterrK ~= K or AQ.wterrAge > LIMIT.wave_terrain_scans or (AQ.wterrN or 0) > LIMIT.wave_terrain_cells then
        AQ.wterr, AQ.wterrMap, AQ.wterrAge, AQ.wterrN, AQ.wterrK = {}, id, 0, 0, K
    end
end
local function terrain(x, y, z)
    local k = (z * 4096 + y) * 4096 + x
    local T = AQ.wterr
    local v = T[k]
    if v then return v end
    if not dfhack.maps.isTileVisible(x, y, z) then v = 'h'
    elseif waterAt(x, y, z) > 0 then v = 'w'
    elseif dfhack.maps.getTileType(x, y, z) == nil then v = 'o'
    elseif not isOpen(x, y, z) then v = 'l'
    else
        v = 'o'
        for d = 1, AQ.wterrK or 0 do
            local zz = z - d
            if zz < 0 then break end
            if waterAt(x, y, zz) > 0 then
                if dfhack.maps.isTileVisible(x, y, zz) then v = (d == 1) and 's1' or 's2' end
                break
            end
            if not isOpen(x, y, zz) then break end
        end
    end
    T[k] = v
    AQ.wterrN = (AQ.wterrN or 0) + 1
    return v
end
_ENV.terrain = terrain
local function isSea(x, y, z) return SEA[terrain(x, y, z)] ~= nil end
_ENV.isSea = isSea
-- which neighbours of a water cell are land, as surfPixels reads it (0: none); a corner counts only when neither
-- side beside it is land
local function landMask(x, y, z)
    local function L(ox, oy) return terrain(x + ox, y + oy, z) == 'l' end
    local n, e, s_, w = L(0, -1), L(1, 0), L(0, 1), L(-1, 0)
    local m = (n and 1 or 0) | (e and 2 or 0) | (s_ and 4 or 0) | (w and 8 or 0)
    if not n and not e and L(1, -1) then m = m | 16 end
    if not s_ and not e and L(1, 1) then m = m | 32 end
    if not s_ and not w and L(-1, 1) then m = m | 64 end
    if not n and not w and L(-1, -1) then m = m | 128 end
    return m
end
_ENV.landMask = landMask
local function wcell(x, y) return y * 4096 + x end
-- flowing river water (DF's perm_flow_dir set: anything but inactive or none), read from the cell's block
local function riverAt(x, y, z)
    local lift = SEA[terrain(x, y, z)]
    if lift then z = z - lift end
    local blk = dfhack.maps.getTileBlock(x, y, z)
    local lfw = blk and blk.liquid_flow
    if not lfw then return false end
    local d = lfw[x % 16][y % 16].perm_flow_dir
    return d ~= 0 and d ~= 9
end
_ENV.riverAt = riverAt
local function hash2(x, y) return ((x * 73856093) ~ (y * 19349663)) & 0x7fffffff end

-- the build: one pass over the view, run as a coroutine that yields whenever the scan's slice (wave_slice_ms) is spent
-- and resumes there at the next scan, so no scan runs long at any zoom (rig 2 Oct: a 120x68 view ran 17 ms a scan and
-- tripped the fuse). The last finished run keeps painting meanwhile. Nothing DF owns is held across a yield except a
-- map block and DF's vectors, read by index (ipairs reads each element afresh).
local function buildWaves(c, B)
    local x1, y1, x2, y2, z = B.x1, B.y1, B.x2, B.y2, B.z
    local function pace(force)
        if force or dfhack.getTickCount() > AQ.wdeadline then coroutine.yield() end
    end
    B.rowPace = function()
        if AQ.wrowCost then AQ.wrowCost() end   -- tests only: a sprite row's cost on DF's Lua (rig 3 Oct: ~6 ms a sprite)
        pace()
    end
    local run = { z = z, n = 0, x = {}, y = {}, fam = {}, ph = {}, kind = {}, lift = {}, lifted = 0, dry = 0, why = B.why,
                  capped = 0, made = 0, scans = 0, warming = 0, fronts = 0, frontsShown = 0, frontsMerged = 0, flows = 0, foamFlows = 0,
                  onLand = 0, cnt = { spray = 0, surf = 0, crest = 0, mist = 0 }, nearest = {} }
    B.run = run
    -- 1. fronts on the view level and the levels beside it (DF keeps the sea's fronts on the open level over its water),
    -- vis_duration > 0 (DF stops showing a front at 0); bucketed 8x8 for the flows' direction lookup
    local fronts, bucket, dsum, nearW = {}, {}, {}, {}
    local i = 0
    for _, w in ipairs(df.global.world.event.ocean_waves) do
        i = i + 1
        if i > LIMIT.wave_fronts then break end
        if i % 64 == 0 then pace() end
        if w.z >= z - 1 and w.z <= z + 1 and (w.vis_duration or 0) > 0 then
            local cur, dst = w.cur, w.dest
            local x, y = cur.x, cur.y
            if x >= x1 - 48 and x <= x2 + 48 and y >= y1 - 48 and y <= y2 + 48 then
                local d = dirOf(dst.x - x, dst.y - y)
                if d then
                    local gap = math.max(x1 - x, x - x2, y1 - y, y - y2, 0)   -- cells outside the view (0: in it)
                    if gap > 0 and (#nearW < 3 or gap < nearW[3][1]) then
                        if #nearW == 3 then table.remove(nearW) end
                        nearW[#nearW + 1] = { gap, x, y, w.z, w.vis_duration }
                        table.sort(nearW, function(a, b) return a[1] < b[1] end)
                    end
                    run.fronts = run.fronts + 1
                    dsum[d] = (dsum[d] or 0) + 1
                    if x >= x1 - 2 and x <= x2 + 2 and y >= y1 - 2 and y <= y2 + 2 then
                        local fr = { x = x, y = y, d = d, vis = w.vis_duration, lead = x * WDIR[d][1] + y * WDIR[d][2] }
                        fronts[#fronts + 1] = fr
                        local bk = (y // 8) * 4096 + (x // 8)
                        local b = bucket[bk]
                        if not b then b = {}; bucket[bk] = b end
                        b[#b + 1] = fr
                    end
                end
            end
        end
    end
    for _, nw in ipairs(nearW) do   -- the probe's answer to "fronts near, none drawn": where they are
        run.nearest[#run.nearest + 1] = ('(%d,%d,%d) %d cells out, vis %d, %s'):format(nw[2], nw[3], nw[4], nw[1], nw[5],
            ({ w = 'water', s1 = 'sea below', s2 = 'sea 2 below', l = 'land', o = 'air', h = 'hidden' })[terrain(nw[2], nw[3], z)] or '?')
    end
    local dom, domN = nil, 0
    for d, n in pairs(dsum) do if n > domN or (n == domN and d < dom) then dom, domN = d, n end end
    if dom then AQ.wdom[z] = dom else dom = AQ.wdom[z] end   -- no front near: the last direction seen on this level
    local function nearestFront(x, y)
        local best, bd = nil, 1e9
        local bx, by = x // 8, y // 8
        for oy = -1, 1 do
            for ox = -1, 1 do
                local b = bucket[(by + oy) * 4096 + (bx + ox)]
                if b then
                    for _, fr in ipairs(b) do
                        local dd = (fr.x - x) ^ 2 + (fr.y - y) ^ 2
                        if dd < bd then best, bd = fr.d, dd end
                    end
                end
            end
        end
        return best
    end
    -- 2. OceanWave and SeaFoam flows of the view's blocks on z - 1 .. z + 1, and world.orphaned_flows (copied out:
    -- position, density, direction; no flow is held across a yield)
    local FT = df.flow_type
    local OW, SF = FT.OceanWave, FT.SeaFoam
    local wave, foam, hint, here = {}, {}, {}, {}   -- here: flows on the view level itself (a beach there gets mist)
    local function take(fl)
        local t = fl.type
        if (t ~= OW and t ~= SF) or fl.density <= 0 then return end
        local fg = fl.flags
        if fg and fg.DEAD then return end
        local p = fl.pos
        local x, y = p.x, p.y
        if p.z < z - 1 or p.z > z + 1 or x < x1 - 1 or x > x2 + 1 or y < y1 - 1 or y > y2 + 1 then return end
        local k = wcell(x, y)
        if p.z == z and (here[k] or 0) < fl.density then here[k] = fl.density end
        if t == OW then
            run.flows = run.flows + 1
            if (wave[k] or 0) < fl.density then wave[k] = fl.density end
            local g = fl.dest
            if g and g.z == p.z and (g.x ~= x or g.y ~= y) and math.abs(g.x - x) < 64 and math.abs(g.y - y) < 64 then
                hint[k] = dirOf(g.x - x, g.y - y)
            end
        else
            run.foamFlows = run.foamFlows + 1
            if (foam[k] or 0) < fl.density then foam[k] = fl.density end
        end
    end
    local nb = 0
    for fz = z + 1, math.max(0, z - 1), -1 do
        for bx = (x1 - 1) // 16, (x2 + 1) // 16 do
            for by = (y1 - 1) // 16, (y2 + 1) // 16 do
                nb = nb + 1
                if nb > LIMIT.blocks * 3 then run.blockCap = true; break end
                pace()
                local blk = dfhack.maps.getTileBlock(bx * 16, by * 16, fz)
                if blk then
                    local nf = 0
                    for _, fl in ipairs(blk.flows) do
                        nf = nf + 1
                        if nf % 64 == 0 then pace() end
                        take(fl)
                    end
                end
            end
        end
    end
    local okO, orphans = pcall(function() return df.global.world.orphaned_flows end)
    if okO and orphans then
        local n = 0
        for _, fl in ipairs(orphans) do
            n = n + 1
            if n > LIMIT.orphans then break end
            if n % 64 == 0 then pace() end
            take(fl)
        end
    end
    -- 3. the cells: one sprite per cell, the highest priority wins
    local best = {}   -- cell -> { prio, kind, d, tier, cap, ph, x, y, lift }
    local nput = 0
    local function put(x, y, prio, kind, d, tier, cap, ph, lift, line)
        if x < x1 or x > x2 or y < y1 or y > y2 then return false end
        nput = nput + 1
        if nput % 8 == 0 then pace() end
        local k = wcell(x, y)
        local b = best[k]
        if b and b[1] >= prio then return true end
        best[k] = { prio, kind, d, tier, cap, ph, x, y, lift, line }
        return true
    end
    local function sea(x, y) return SEA[terrain(x, y, z)] end   -- the lift (0, 1, 2) of a sea cell, nil otherwise
    local function phaseAlong(x, y, d, nf) return (x * WDIR[d][1] + y * WDIR[d][2]) % nf end
    -- 3a. the fronts, the most advanced first: each draws a line across its travel (itself, one cell each side at its
    -- strength, a fading end beyond), and claims the two cells behind its line, so a train of fronts one behind the
    -- other draws a crest every third cell, not a stacked column
    table.sort(fronts, function(a, b)
        if a.d ~= b.d then return a.d < b.d end
        if a.lead ~= b.lead then return a.lead > b.lead end
        if a.x ~= b.x then return a.x < b.x end
        return a.y < b.y
    end)
    local claimed = {}
    local NFc = WAVE.NF.crest
    for _, fr in ipairs(fronts) do
        pace()
        local x, y, d = fr.x, fr.y, fr.d
        local lift = sea(x, y)
        if claimed[wcell(x, y)] or not lift then
            run.frontsMerged = run.frontsMerged + 1
        else
            local tx, ty = WDIR[d][1], WDIR[d][2]
            local px, py = -ty, tx
            local tier = 1
            local ph = phaseAlong(x, y, d, NFc)
            local id = hash2(x, y)   -- the line's identity: thinned whole (4.)
            put(x, y, WAVE.PRIO.front, 'crest', d, tier, nil, ph, lift, id)
            run.frontsShown = run.frontsShown + 1
            local reach = { [1] = 0, [-1] = 0 }
            for _, side in ipairs({ 1, -1 }) do
                for k = 1, 2 do
                    local cx, cy = x + side * k * px, y + side * k * py
                    local cl = sea(cx, cy)
                    if not cl then break end          -- a crest does not run onto land
                    put(cx, cy, k == 2 and WAVE.PRIO.cap or WAVE.PRIO.front, 'crest', d, tier, k == 2 and side or nil, ph, cl, id)
                    reach[side] = k
                end
            end
            for l = -reach[-1], reach[1] do
                for b = 0, 2 do claimed[wcell(x + l * px - b * tx, y + l * py - b * ty)] = true end
            end
        end
    end
    -- 3b. OceanWave flows over the sea: the leading cell of a run (no wave flow ahead of it, not just behind a front's
    -- line) is a crest; the rest of the run draws nothing. Direction: the flow's own dest, else the nearest front, else
    -- the level's usual direction. Flows on the beach (dry land) are counted for the mist (3c)
    local landAt, mistAt = {}, {}   -- land cell -> density of DF's waves or foam on it; of those on the view level itself
    local function onBeach(x, y, dens)
        run.onLand = run.onLand + 1
        if terrain(x, y, z) ~= 'l' then return end
        local k = wcell(x, y)
        if (landAt[k] or 0) < dens then landAt[k] = dens end
        local h = here[k]
        if h and (mistAt[k] or 0) < h then mistAt[k] = h end   -- a beach at the view level (not a cliff under a beach above)
    end
    local nk = 0
    for k, dens in pairs(wave) do
        nk = nk + 1
        if nk % 8 == 0 then pace() end
        local x, y = k % 4096, k // 4096
        local lift = sea(x, y)
        if lift then
            local d = hint[k] or nearestFront(x, y) or dom
            if d and not claimed[k] then
                local tx, ty = WDIR[d][1], WDIR[d][2]
                if not wave[wcell(x + tx, y + ty)] then
                    put(x, y, WAVE.PRIO.crest, 'crest', d, 1, nil, phaseAlong(x, y, d, NFc), lift)
                end
            end
        else
            onBeach(x, y, dens)
        end
    end
    local seaFoam = {}   -- sea cell -> density: SeaFoam over the sea (spray at the waterline when it lies beside land)
    for k, dens in pairs(foam) do
        nk = nk + 1
        if nk % 8 == 0 then pace() end
        local x, y = k % 4096, k // 4096
        if sea(x, y) then seaFoam[k] = dens else onBeach(x, y, dens) end
    end
    -- 3c. the shore. A beach cell of the view level that DF's waves or foam reach gets DF's mist art (foam on), its
    -- alpha by the flow's density. The sea cells beside any land DF's waves reach get the waterline: the surf (surf on),
    -- with the mist drifting over it where the beach beside it is misty (foam on), one sprite. SeaFoam on a sea cell
    -- beside land counts as spray there too. Never on a river's own water.
    if c.foam then
        for k, dens in pairs(mistAt) do
            nk = nk + 1
            if nk % 8 == 0 then pace() end
            local x, y = k % 4096, k // 4096
            local tier = dens >= 75 and 4 or (dens >= 50 and 3 or (dens >= 25 and 2 or 1))
            if not WAVE.MIST_SKIP[tier] or hash2(x, y) % 2 == 0 then
                put(x, y, WAVE.PRIO.mist, 'mist', 0, tier, nil, (x + y) % WAVE.NF.mist, -1)
            end
        end
    end
    local shoreAt, sprayAt = {}, {}   -- sea cell -> strongest wave beside it; strongest mist (or SeaFoam) beside it
    for k, dens in pairs(landAt) do
        pace()   -- eight neighbour reads an item
        local x, y = k % 4096, k // 4096
        local md = mistAt[k]
        for oy = -1, 1 do
            for ox = -1, 1 do
                if (ox ~= 0 or oy ~= 0) and sea(x + ox, y + oy) then
                    local sk = wcell(x + ox, y + oy)
                    if (shoreAt[sk] or 0) < dens then shoreAt[sk] = dens end
                    if md and (sprayAt[sk] or 0) < md then sprayAt[sk] = md end
                end
            end
        end
    end
    for k, dens in pairs(seaFoam) do
        pace()
        local x, y = k % 4096, k // 4096
        if landMask(x, y, z) ~= 0 then
            if (shoreAt[k] or 0) < dens then shoreAt[k] = dens end
            if (sprayAt[k] or 0) < dens then sprayAt[k] = dens end
        end
    end
    for k in pairs(shoreAt) do
        pace()
        local x, y = k % 4096, k // 4096
        if not riverAt(x, y, z) then
            local m = c.surf and landMask(x, y, z) or 0
            local lift = sea(x, y)
            local sp = c.foam and sprayAt[k]
            local tier = sp and (sp >= 50 and 6 or 5)
            if sp and (not WAVE.MIST_SKIP[tier] or hash2(x, y) % 2 == 0) then
                put(x, y, WAVE.PRIO.shore, 'mist', 0, tier, nil, (x + y) % WAVE.NF.mist, lift)   -- the spray over the water
            elseif m ~= 0 then
                put(x, y, WAVE.PRIO.shore, 'surf', m, 1, nil, 0, lift)
            end
        end
    end
    -- 3d. a flow crest's ends: where no crest of the same direction lies beside it along the line, that end fades
    for _, b in pairs(best) do
        if b[2] == 'crest' and b[1] == WAVE.PRIO.crest then
            local tx, ty = WDIR[b[3]][1], WDIR[b[3]][2]
            local function line(ox, oy) local nb2 = best[wcell(b[7] + ox, b[8] + oy)]; return nb2 and nb2[2] == 'crest' and nb2[3] == b[3] end
            local r, l = line(-ty, tx), line(ty, -tx)
            b[5] = (not r and not l) and 2 or (not r and 1) or (not l and -1) or nil
        end
    end
    -- 4. at most `marks` cells, every kind keeping its share: the fronts' lines get their share of the cap (kept or
    -- dropped a whole line at a time: a broken line reads as noise), the rest -- crests, the shore, the mist -- is thinned
    -- evenly by a position hash (no sort: a big view's thousands of cells; no edge of the view left bare; stable)
    local lines, others, total = {}, {}, 0
    for _, b in pairs(best) do
        total = total + 1
        if b[10] then lines[#lines + 1] = b else others[#others + 1] = b end
        if total % 64 == 0 then pace() end
    end
    local room = c.marks
    local take2 = {}
    if total > room and #lines > 0 then
        local share = math.floor(room * #lines / total + 0.5)
        local keep = math.floor(share * 1000 / #lines)
        local kept = 0
        for _, b in ipairs(lines) do
            if b[10] % 1000 < keep and kept < share then take2[#take2 + 1] = b; kept = kept + 1 end
        end
        room = room - kept
        lines = {}
    end
    local function thin(L)
        if #L <= room then
            for _, b in ipairs(L) do take2[#take2 + 1] = b end
            room = room - #L
            return
        end
        local keep = math.floor(room * 1000 / #L)
        local rest = {}
        for _, b in ipairs(L) do
            if room > 0 and hash2(b[7], b[8]) % 1000 < keep then take2[#take2 + 1] = b; room = room - 1
            else rest[#rest + 1] = b end
        end
        for _, b in ipairs(rest) do if room == 0 then break end; take2[#take2 + 1] = b; room = room - 1 end
    end
    thin(lines)
    thin(others)
    run.overCap = total - #take2
    -- 5. the run, from the sprite families already made; the missing ones are queued, the run is published at once
    -- (the sea shows while the rest are made), then they are made, paced, and the next build draws them
    local want = { order = {} }
    local function add(b, fam)
        local kind = b[2]
        run.n = run.n + 1
        local n = run.n
        run.x[n], run.y[n], run.fam[n], run.kind[n] = b[7], b[8], fam, (fam.raw and 'mist') or kind
        run.ph[n] = b[6] % #fam
        run.lift[n] = b[9] or 0   -- -1: a dry beach cell; 0: water at the view level; 1, 2: the sea seen that far below
        if (b[9] or 0) > 0 then run.lifted = run.lifted + 1 elseif b[9] == -1 then run.dry = run.dry + 1 end
        local ck = (kind == 'mist' and (b[9] or 0) >= 0) and 'spray' or kind   -- the mist over the water: the spray
        run.cnt[ck] = (run.cnt[ck] or 0) + 1
    end
    for _, b in ipairs(take2) do
        want.cell = b
        local fam = waveFamily(b[2], b[3], b[4], b[5], pace, run, want)
        if fam then add(b, fam) end
    end
    if #want.order > 0 then
        -- published now, and grown in place: each family, once made, brings its waiting cells into the run (the paint
        -- reads run.n each frame), so a cold view fills in sprite by sprite instead of showing nothing until the end
        AQ.waves = run
        B.published = true
        for _, key in ipairs(want.order) do
            local w = want[key]
            local fam = waveFamily(w[1], w[2], w[3], w[4], pace, run)
            if fam then for _, b in ipairs(w.cells) do add(b, fam) end end
            run.warming = run.warming - #w.cells
        end
    end
    return run
end

function scanWaves(c)
    local t0 = dfhack.getTickCount()
    local on, why = wavesOn(c)
    if not on then AQ.waves, AQ.wbuild = { n = 0, why = why }, nil; scanDone('waves', 0, 0, why); return AQ.waves end
    local x1, y1, x2, y2, z, W, H = view()
    local key = ('%d,%d,%d,%d,%d,%s,%s,%d,%d'):format(z, x1, y1, W, H, tostring(c.surf), tostring(c.foam), c.marks, lowerShown())
    local B = AQ.wbuild
    if B and (B.key ~= key or B.scans >= LIMIT.wave_build_scans) then B = nil end   -- the view moved: start again
    if not B then
        terrainReset()   -- per build, never mid-build: a big view's build spans scans and must keep what it has read
        B = { key = key, x1 = x1, y1 = y1, x2 = x2, y2 = y2, z = z, why = why, scans = 0 }
        B.co = coroutine.create(function() return buildWaves(c, B) end)
        AQ.wbuild = B
    end
    B.scans = B.scans + 1
    AQ.wdeadline = t0 + LIMIT.wave_slice_ms
    AQ.wrow = B.rowPace   -- the sprite pixel loops yield here a row at a time (only while this build runs)
    local ok, res = coroutine.resume(B.co)
    AQ.wrow = nil
    local done = coroutine.status(B.co) == 'dead'
    if not ok then AQ.wbuild = nil; error(res, 0) end
    if done then
        res.scans = B.scans
        AQ.waves, AQ.wbuild = res, nil
    end
    local r = AQ.waves
    local ms = dfhack.getTickCount() - t0
    if not r or not r.cnt then
        scanDone('waves', ms, 0, ('%s; building the first run (scan %d)'):format(why, B.scans))
        return r
    end
    scanDone('waves', ms, r.n, ('%s%s; fronts %d near (%d drawn as lines, %d merged into the line ahead); flows %d wave + %d foam in view (%d on the beach: mist there, never water marks); cells %d (crest %d, mist %d on the beach, spray %d over the water, surf %d; %d on the sea seen below, %d on the dry beach)%s%s%s; textures %d/%d; the run took %d scans and made %d sprites%s')
        :format(done and '' or (B.published and ('making sprites: scan ' .. B.scans .. ', ' .. r.warming .. ' cells wait for theirs; ')
                                or ('building: scan ' .. B.scans .. ', showing the last run; ')), why, r.fronts, r.frontsShown, r.frontsMerged,
                r.flows, r.foamFlows, r.onLand, r.n, r.cnt.crest or 0, r.cnt.mist or 0, r.cnt.spray or 0, r.cnt.surf or 0, r.lifted, r.dry,
                (r.overCap or 0) > 0 and ('; ' .. r.overCap .. ' thinned out (over the marks cap)') or '',
                r.blockCap and '; block cap reached' or '',
                AQ.wmistRaw == false and '; mist: DF\'s mist tiles not found (neither SW_AQ_MIST nor EVENT_FLOWS loaded)'
                    or (AQ.wmistRaw and ('; mist: ' .. AQ.wmistRaw.page) or ''),
                AQ.wtexN, LIMIT.wave_tex, r.scans or 0, r.made,
                (#r.nearest > 0 and r.frontsShown + r.frontsMerged == 0) and ('; no front in view, the nearest: ' .. table.concat(r.nearest, ', ')) or ''))
    return r
end

--========================================================================================
-- moving water (v7.1-waves, phase 2; docs/v7.1/aquarium.md section 4.7): river STREAKS and shallow-water SHIMMER.
-- Rig, 2 Oct 23:45: DF 53.16 draws no motion on flowing water in fortress mode (vanilla too): river cells with
-- perm_flow_dir ~= 0 (~40,000 on AQUA_LAKE) carry liquid flag 0x3c and six frames 0.25 s apart change no pixel. So the
-- motion is ours: soft dashes travelling along DF's own flow direction, and a faint caustic net on still shallows.
--========================================================================================
-- DF's perm_flow_dir (tile_liquid_flow_dir: 0 inactive, 1 S, 2 E, 3 NE, 4 W, 5 NW, 6 SE, 7 SW, 8 down, 9 none, 10 N)
-- -> WDIR index; down (a sink or a fall) and none draw no streak
local PERM_DIR = { [1] = 5, [2] = 3, [3] = 2, [4] = 7, [5] = 8, [6] = 4, [7] = 6, [10] = 1 }
_ENV.PERM_DIR = PERM_DIR
-- frames, ms per frame; streak peak alpha; shimmer peak alpha by column depth 1 / 2+
local FLOWFX = { NF = { streak = 12, shimmer = 8 }, MS = { streak = 85, shimmer = 170 }, STREAK = 72, SHIMMER = { 42, 20 },
                 VARIANTS = 3 }
_ENV.FLOWFX = FLOWFX
local C_STREAK, C_SHIM = { 205, 242, 250 }, { 228, 250, 238 }

-- a streak sprite: three soft dashes lying along the flow (d), each born, carried 16 px downstream and gone again
-- within the cell (alpha envelope sin^1.5 over its trip), staggered in time, so motion never crosses a cell edge and
-- cells need not match; a slight meander, a longer tail than head. v = layout variant 1..3
local function streakPixels(d, v, f)
    local tx, ty = WDIR[d][1], WDIR[d][2]
    local diag = tx ~= 0 and ty ~= 0
    local nrm = diag and (1 / math.sqrt(2)) or 1
    local pxv, pyv = -ty, tx
    local rnd = lcg(d * 131 + v * 7907 + 3)
    local NF = FLOWFX.NF.streak
    local A = FLOWFX.STREAK / 255
    local dash = {}
    for k = 1, 3 do
        dash[k] = { u = -10 + 10 * (k - 1) + (rnd() - 0.5) * 5, off = (k - 1) / 3 + rnd() * 0.2, hl = 3 + rnd() * 2.5,
                    a = 0.65 + rnd() * 0.35, w = 0.9 + rnd() * 0.4, m = rnd() * 2 * math.pi }
    end
    local out = {}
    for y = 0, 31 do
        for x = 0, 31 do
            local dx, dy = x + 0.5 - 16, y + 0.5 - 16
            local s = (dx * tx + dy * ty) * nrm
            local u = (dx * pxv + dy * pyv) * nrm
            local best = 0
            for k = 1, 3 do
                local q = dash[k]
                local ph = (f / NF + q.off) % 1
                local env = math.sin(math.pi * ph) ^ 1.5
                if env > 0.01 then
                    local ds = s - (-8 + 16 * ph)
                    local du = u - q.u - 0.8 * math.sin(2 * math.pi * ph + q.m)
                    local reach = ds < 0 and q.hl * 1.4 or q.hl
                    local a = q.a * env * (1 - smooth(reach - 2, reach + 0.5, math.abs(ds))) * gauss(du, q.w)
                    if a > best then best = a end
                end
            end
            out[y * 32 + x + 1] = layered(A * best, C_STREAK, 0, nil, nil, nil, 110)
        end
    end
    return out
end
-- a shimmer sprite: the caustic net of sunlight on a shallow floor -- the zero lines of four travelling waves with
-- whole-number wave vectors on a 64 px (2x2-cell) period, so every shallow cell takes the quadrant (x % 2, y % 2) and the
-- net runs on seamlessly across any patch; each term's phase turns a whole number of times per loop, so the 8 frames
-- loop without a jump. tier 1 = one level of water, 2 = two
local function shimmerPixels(q, tier, f)
    local qx, qy = (q - 1) % 2, (q - 1) // 2
    local k = 2 * math.pi / 64
    local ph = 2 * math.pi * f / FLOWFX.NF.shimmer
    local A = (FLOWFX.SHIMMER[tier] or FLOWFX.SHIMMER[2]) / 255
    local out = {}
    for y = 0, 31 do
        for x = 0, 31 do
            local X, Y = qx * 32 + x + 0.5, qy * 32 + y + 0.5
            local sum = math.sin(k * (2 * X + Y) + ph) + math.sin(k * (-X + 2 * Y) - ph + 1.7)
                + math.sin(k * (3 * X - 2 * Y) + 2 * ph + 0.6) + math.sin(k * (X + 3 * Y) - 2 * ph + 2.4)
            local net = math.exp(-(sum * sum) / (2 * 0.42 * 0.42))
            local m = 0.65 + 0.35 * math.sin(k * (X - Y) + ph)
            out[y * 32 + x + 1] = layered(A * net * m, C_SHIM, 0, nil, nil, nil, 80)
        end
    end
    return out
end
local function flowPixels(kind, d, tier, f)
    if kind == 'streak' then return streakPixels(d, tier, f) end
    if kind == 'shimmer' then return shimmerPixels(d, tier, f) end
    error('no flow sprite ' .. tostring(kind), 0)
end
_ENV.flowPixels = flowPixels
-- a family's frames, made on first use inside a budget (own store and cap, apart from the waves' and the lens's)
local function flowFamily(kind, d, tier, genDeadline, run)
    local key = ('%s|%d|%d'):format(kind, d, tier)
    local fam = AQ.ffam[key]
    if fam ~= nil then return fam or nil end
    local nf = FLOWFX.NF[kind]
    local hs = AQ.fpart[key] or {}
    for f = #hs, nf - 1 do
        if dfhack.getTickCount() > genDeadline then AQ.fpart[key] = hs; run.warming = run.warming + 1; return nil end
        if AQ.ftexN >= LIMIT.flow_tex then run.capped = run.capped + 1; return nil end
        local ok, h = pcall(makeTile, flowPixels(kind, d, tier, f), 32, 32)
        if not ok or not h then AQ.ffam[key] = false; return nil end
        AQ.ftexN = AQ.ftexN + 1
        hs[#hs + 1] = h
    end
    AQ.fpart[key] = nil
    AQ.ffam[key] = hs
    return hs
end
_ENV.flowFamily = flowFamily

-- one cell of the view: the water DF shows there -- this level's, or, for an open cell, the first water down its open
-- column within the K levels DF draws below (number_of_lower_elevations_shown, at most 8: the same search as the bed's
-- lift, which copies that water's liquid flag into the main viewport). A lifted cell is painted where liftedShown says
-- water is drawn there this frame (the lift's flag, or DF's own lower viewport). Returns its flow direction (WDIR index or 0) and column depth (contiguous
-- water down from its surface, up to 4).
local function flowCell(b, c, x, y, z, bcache, K)
    local cz, lifted = z, false
    if waterAt(x, y, z) == 0 then
        if K < 1 or not isOpen(x, y, z) then return end
        cz = nil
        for k = 1, K do
            local zz = z - k
            if zz < 0 then break end
            if waterAt(x, y, zz) > 0 then cz = zz; break end
            if not isOpen(x, y, zz) then break end
        end
        if not cz then return end
        lifted = true
    end
    if not dfhack.maps.isTileVisible(x, y, cz) then return end
    local bk = (cz * 1024 + y // 16) * 1024 + x // 16
    local blk = bcache[bk]
    if blk == nil then blk = dfhack.maps.getTileBlock(x, y, cz) or false; bcache[bk] = blk end
    local d = 0
    local lfw = blk and blk.liquid_flow
    if lfw then d = PERM_DIR[lfw[x % 16][y % 16].perm_flow_dir] or 0 end
    local depth = 0
    if d == 0 or not c.streaks then
        depth = 1
        for zz = cz - 1, math.max(0, cz - 3), -1 do
            if waterAt(x, y, zz) == 0 then break end
            depth = depth + 1
        end
    end
    if d == 0 and (not c.shimmer or depth > c.shimmer_depth) then return end   -- still and deep: nothing to draw
    b.n = b.n + 1
    b.x[b.n], b.y[b.n], b.d[b.n], b.dep[b.n], b.lift[b.n] = x, y, d, depth, z - cz   -- lift: levels below the view (0: here)
    if d ~= 0 then b.flowing = b.flowing + 1 end
    if lifted then b.lifted = b.lifted + 1 end
end
-- the scan: the view's cells (resumable under a deadline, kept until the view moves or flow_rebuild scans pass: rivers
-- do not move), then the run: a family per cell, made inside flow_gen_ms; a zoomed-out view past flow_cells is thinned
-- evenly (every k-th cell), never cut off at one edge
function scanFlowFx(c)
    local t0 = dfhack.getTickCount()
    local deadline = t0 + LIMIT.scan_ms * 2
    local x1, y1, x2, y2, z, W, H = view()
    local K = lowerShown()
    local key = ('%d,%d,%d,%d,%d,%s,%s,%d,%d'):format(z, x1, y1, W, H, tostring(c.streaks), tostring(c.shimmer), c.shimmer_depth, K)
    local b = AQ.flowBuild
    local fresh = false
    if b and b.key == key and b.done then
        b.age = b.age + 1
        if b.age >= LIMIT.flow_rebuild then b = nil end
    end
    if not b or b.key ~= key then
        b = { key = key, z = z, n = 0, x = {}, y = {}, d = {}, dep = {}, lift = {}, nextY = y1, done = false, age = 0,
              flowing = 0, lifted = 0, id = (AQ.flowBuildId or 0) + 1 }
        AQ.flowBuildId = b.id
        AQ.flowBuild = b
    end
    local stopped
    if not b.done then
        local bcache = {}
        for y = b.nextY, y2 do
            if dfhack.getTickCount() > deadline then stopped = 'deadline'; b.nextY = y; break end
            for x = x1, x2 do flowCell(b, c, x, y, z, bcache, K) end
            b.nextY = y + 1
        end
        if not stopped then b.done = true; fresh = true end
    end
    local cells = b.done and b or AQ.flowCells
    if b.done then AQ.flowCells = b end
    local scanMs = dfhack.getTickCount() - t0
    local run = AQ.flowfx
    if cells and cells.z == z and (fresh or not run or run.cells ~= cells.id or run.warming > 0) then
        run = { z = z, cells = cells.id, n = 0, x = {}, y = {}, fam = {}, ph = {}, kind = {}, lift = {}, warming = 0, capped = 0,
                streaks = 0, shimmer = 0, lifted = 0 }
        local stride = math.max(1, math.ceil(cells.n / LIMIT.flow_cells))
        local genDeadline = dfhack.getTickCount() + LIMIT.flow_gen_ms
        for i = 1, cells.n, stride do
            local x, y, d = cells.x[i], cells.y[i], cells.d[i]
            local kind, fd, tier
            if d ~= 0 and c.streaks then kind, fd, tier = 'streak', d, hash2(x, y) % FLOWFX.VARIANTS + 1
            elseif c.shimmer and cells.dep[i] >= 1 and cells.dep[i] <= c.shimmer_depth then
                kind, fd, tier = 'shimmer', (x % 2) + 2 * (y % 2) + 1, cells.dep[i] == 1 and 1 or 2
            end
            if kind then
                local fam = flowFamily(kind, fd, tier, genDeadline, run)
                if fam then
                    run.n = run.n + 1
                    run.x[run.n], run.y[run.n], run.fam[run.n], run.kind[run.n], run.lift[run.n] = x, y, fam, kind, cells.lift[i] or 0
                    run.ph[run.n] = kind == 'streak' and (hash2(y, x) % #fam) or 0   -- the shimmer must stay in step to join
                    run[kind == 'streak' and 'streaks' or 'shimmer'] = run[kind == 'streak' and 'streaks' or 'shimmer'] + 1
                    if (cells.lift[i] or 0) > 0 then run.lifted = run.lifted + 1 end
                end
            end
        end
        run.stride = stride
        AQ.flowfx = run
    end
    local r = AQ.flowfx or { n = 0, streaks = 0, shimmer = 0, lifted = 0, warming = 0 }
    scanDone('flow', scanMs, r.n, ('%s%d water cells to draw (%d flowing, %d seen one level down)%s; streaks %d, shimmer %d%s%s; textures %d/%d')
        :format(stopped and ('stopped: ' .. stopped .. ', resumes next scan; ') or '', cells and cells.n or 0, cells and cells.flowing or 0,
                cells and cells.lifted or 0, (r.stride or 1) > 1 and (' (every ' .. r.stride .. 'th: over flow_cells)') or '',
                r.streaks, r.shimmer, r.warming > 0 and ('; ' .. r.warming .. ' sprite families still being made') or '',
                (r.capped or 0) > 0 and ('; ' .. r.capped .. ' at the texture cap') or '', AQ.ftexN, LIMIT.flow_tex))
    return r
end

--========================================================================================
-- the veil (experimental): water cells of the view level, painted per frame into background_two
--========================================================================================
local function veilTextures(c)
    if AQ.veilTex and AQ.veilTex.preset == c.preset then return AQ.veilTex end
    local okG, gfx = pcall(reqscript, 'seasonal-wildlife-aquarium-gfx')
    if not okG then error('the gfx module is missing: ' .. tostring(gfx), 0) end
    local G = gfx.GFX
    local dir = G.join(G.join(G.join(G.join(G.join(G.join(AQ_installDir(), 'data'), 'vanilla'), 'vanilla_environment'), 'graphics'), 'images'), 'liquids.png')
    local f = io.open(dir, 'rb')
    if not f then error('cannot read ' .. dir, 0) end
    local data = f:read('a'); f:close()
    local page = G.liquidsPage(G.decode(data), G.preset(c.preset == 'vanilla' and 'aquarium' or c.preset, c.alpha))
    local tiles = G.waterTiles(page)
    local h = {}
    for level = 1, 7 do h[level] = makeTile(tiles[level], 32, 32) end
    AQ.veilTex = { preset = c.preset, h = h }
    return AQ.veilTex
end
function scanVeil(c)
    local t0 = dfhack.getTickCount()
    local deadline = t0 + LIMIT.scan_ms * 2
    local run = { n = 0, x = {}, y = {}, z = nil }
    if not c.veil then AQ.veil = run; return run end
    veilTextures(c)
    local x1, y1, x2, y2, z = view()
    run.z = z
    local stopped
    for y = y1, y2 do
        if dfhack.getTickCount() > deadline then stopped = 'deadline'; break end
        for x = x1, x2 do
            if run.n >= LIMIT.veil_cells then stopped = 'cap'; break end
            if waterAt(x, y, z) > 0 then run.n = run.n + 1; run.x[run.n], run.y[run.n] = x, y end
        end
    end
    run.stopped = stopped
    AQ.veil = run
    scanDone('veil', dfhack.getTickCount() - t0, run.n, stopped and ('stopped: ' .. stopped) or ('%d water cells'):format(run.n))
    return run
end

--========================================================================================
-- the bed (docs/v7.1/aquarium.md section 4.6): DF draws no floor under a water cell, so translucent water shows DF's
-- generic dark fill (rig, 2 Oct 2026: a shallow river cell's screentexpos_background held 2566, the same texpos as a
-- soil wall). The scan picks, per water cell of the view level, the floor that lies under it (this level's, or the
-- first floor down an open column, darkened by depth) and its sprite; each frame writes that sprite into the background
-- layer of the cells DF drew water on. Proven on the rig with a hand-written FLOOR_SAND write under the clear preset.
--========================================================================================
local function gfxMod()
    local okG, gfx = pcall(reqscript, 'seasonal-wildlife-aquarium-gfx')
    if not okG then error('the gfx module is missing: ' .. tostring(gfx), 0) end
    return gfx.GFX
end
local function bedReset()
    local id = mapId()
    if AQ.bedMap ~= id then
        AQ.bedMap, AQ.bedGeo, AQ.bedLayer, AQ.bedMat, AQ.bedAct, AQ.bedBuild, AQ.bed = id, {}, {}, {}, nil, nil, nil
    end
end
-- `auto`: on when the loaded world uses the aquarium mod (its water is translucent) or the veil is on
function bedOn(c)
    if c.bed == 'off' then return false, 'off' end
    if c.bed == 'on' then return true, 'on' end
    if c.veil then return true, 'auto: with the veil' end
    local now = dfhack.getTickCount()
    local a = AQ.bedAct
    if not a or now - a.at > LIMIT.bed_act_ms then
        local ok, act = pcall(activeInWorld)
        a = { at = now, v = ok and act or false }
        AQ.bedAct = a
    end
    if a.v then return true, 'auto: this world loaded the aquarium mod' end
    return false, 'auto: idle, this world has no aquarium mod (`aquarium bed on` forces it)'
end

-- shapes and materials
local SHAPEB
local function basicShape(tt)
    if not SHAPEB then
        local B = df.tiletype_shape_basic
        SHAPEB = { [B.Open] = 'open', [B.Floor] = 'floor', [B.Ramp] = 'floor', [B.Wall] = 'wall', [B.Stair] = 'floor' }
    end
    local shape = df.tiletype.attrs[tt].shape
    return SHAPEB[df.tiletype_shape.attrs[shape].basic_shape] or 'other'
end
-- an inorganic material's colour: the material's solid STATE_COLOR (a descriptor colour: world.raws.descriptors.colors,
-- red/green/blue 0..1, e.g. CLAY BRASS, LOAM SILVER, SAND_TAN TAN), else its console colour (material.basic_color
-- fg + 8 x bright through enabler.ccolor), else nil (no tint)
local function matColour(mat)
    local ok, rgb = pcall(function()
        local ci = mat.state_color[df.matter_state.Solid]
        local dc = ci and ci >= 0 and df.descriptor_color.find(ci)
        if dc then return { math.floor(dc.red * 255 + 0.5), math.floor(dc.green * 255 + 0.5), math.floor(dc.blue * 255 + 0.5) } end
        return nil
    end)
    if ok and rgb then return rgb end
    ok, rgb = pcall(function()
        local k = mat.basic_color[0] + 8 * (mat.basic_color[1] ~= 0 and 1 or 0)
        local cc = df.global.enabler.ccolor[k]
        return { math.floor(cc[0] * 255 + 0.5), math.floor(cc[1] * 255 + 0.5), math.floor(cc[2] * 255 + 0.5) }
    end)
    return ok and rgb or nil
end
-- inorganic index -> { cls = 'sand' | 'soil' | 'stone', rgb, token } (inorganic flags SOIL_SAND; SOIL_ANY / SOIL /
-- SOIL_OCEAN; anything else is stone), cached per map
local function matInfo(idx)
    if not idx or idx < 0 then return nil end
    local mi = AQ.bedMat[idx]
    if mi ~= nil then return mi or nil end
    local ok, r = pcall(function()
        local inorg = df.inorganic_raw.find(idx)
        if not inorg then return false end
        local fl = inorg.flags
        local cls = fl.SOIL_SAND and 'sand' or ((fl.SOIL_ANY or fl.SOIL or fl.SOIL_OCEAN) and 'soil') or 'stone'
        return { cls = cls, rgb = matColour(inorg.material), token = inorg.id, idx = idx }
    end)
    AQ.bedMat[idx] = ok and r or false
    return ok and r or nil
end
_ENV.matInfo = matInfo
-- the geological layer's inorganic at (x, y, z), as DFHack's tile-material GetLayerMat reads it (region biome ->
-- world_geo_biome -> layers[geolayer_index].mat_index), cached per block column, biome and layer
local function layerMat(x, y, z)
    local blk = dfhack.maps.getTileBlock(x, y, z)
    if not blk then return nil end
    local des = blk.designation[x % 16][y % 16]
    local gk = ((z * 1024 + x // 16) * 1024 + y // 16) * 16 + (des.biome or 0)
    local geo = AQ.bedGeo[gk]
    if geo == nil then
        local ok, g = pcall(function()
            local rx, ry = dfhack.maps.getTileBiomeRgn(x, y, z)
            return dfhack.maps.getRegionBiome(rx, ry).geo_index
        end)
        geo = ok and g or false
        AQ.bedGeo[gk] = geo
    end
    if not geo then return nil end
    local lk = geo * 256 + des.geolayer_index
    local m = AQ.bedLayer[lk]
    if m == nil then
        local ok, idx = pcall(function() return df.world_geo_biome.find(geo).layers[des.geolayer_index].mat_index end)
        m = ok and idx or false
        AQ.bedLayer[lk] = m
    end
    return m or nil
end
local function veinMat(x, y, z)
    local ok, mi = pcall(function() return require('tile-material').GetVeinMat(x, y, z) end)
    return ok and mi and mi.index or nil
end
local LAVA_RGB = { 44, 40, 52 }   -- obsidian-dark for lava stone (its material is the region's, not the layer's)
-- the bed's material at (x, y, z) for tiletype material ttmat: veins for MINERAL, the layer for the rest
local function bedMaterial(x, y, z, ttmat)
    local TM = df.tiletype_material
    if ttmat == TM.CONSTRUCTION or ttmat == TM.FEATURE then return nil end
    if ttmat == TM.LAVA_STONE then return { cls = 'stone', rgb = LAVA_RGB, token = 'LAVA_STONE' } end
    if ttmat == TM.MINERAL then
        local v = veinMat(x, y, z)
        if v then return matInfo(v) end
    end
    return matInfo(layerMat(x, y, z))
end

-- the family for a bed cell: returns family key (GFX.BED), tint rgb or nil, tint strength.
--   river/brook tiletypes: `bed_river` pebbles (gravel, lightly tinted by the layer), floor (the layer's family), df
--   (DF's own RIVER_BED/BROOK_BED: teal water-over-bed pictures); sand -> the sand row of its colour (sprites already
--   coloured, no tint); soil (clay, silt, loam, peat, ocean oozes) -> dirt tinted; stone, veins -> stone tinted;
--   unknown (constructions, features) -> stone untinted
function bedChoice(ttmat, mi, c, GFX)
    local TM = df.tiletype_material
    local tint = c.bed_tint or 0.6
    if ttmat == TM.RIVER or ttmat == TM.BROOK then
        if c.bed_river == 'df' then return ttmat == TM.RIVER and 'river' or 'brook', nil, 0 end
        if c.bed_river ~= 'floor' then return 'pebbles', mi and mi.rgb, tint * 0.5 end
    end
    if not mi then return 'stone', nil, 0 end
    if mi.cls == 'sand' then return 'sand' .. GFX.sandRow(mi.token, mi.rgb), nil, 0 end
    if mi.cls == 'soil' then return 'dirt', mi.rgb, tint end
    return 'stone', mi.rgb, tint
end
-- the variant (1..n) for a map position (GFX.bedVariant: a mixing hash, so the bed is not a repeated stamp)
function bedVariant(x, y, z, n) return gfxMod().bedVariant(x, y, z, n) end
-- a millisecond clock finer than getTickCount where Lua's os.clock exists (a texture's cost is under a tick)
local function cpuMs()
    if os and os.clock then return os.clock() * 1000 end
    return dfhack.getTickCount()
end
local DEFER = {}   -- bedTexture's "not now": the sheet is still loading, or the scan's deadline passed

-- the vanilla sheets, decoded in slices: a sheet a texture needs is queued; scanBed runs the decode in a coroutine
-- whose GFX.pace hook yields at the scan's deadline, so a 100+ ms decode spreads over several scans (rig, 2 Oct: the
-- first bed scan took 167 ms in one go). Decoded once per process; a sheet that cannot be read is false (its variants
-- fall back to the family's first; with none the cells are skipped and status names it).
local function sheetPath(file) return AQ_installDir() .. 'data/vanilla/vanilla_environment/graphics/images/' .. file end
local function loadSheet(GFX, file)
    local f = io.open(sheetPath(file), 'rb')
    if not f then AQ.bedSheets[file] = false; AQ.bedSheetErr = ('%s: cannot read %s'):format(file, sheetPath(file)); return end
    local data = f:read('a'); f:close()
    local img = (file:match('%.bmp$') and GFX.decodeBMP or GFX.decode)(data)
    AQ.bedSheets[file] = img
end
local function loaderRun(GFX, deadline)
    AQ.bedWant = AQ.bedWant or {}
    while dfhack.getTickCount() <= deadline do
        local L = AQ.bedLoader
        if not L then
            local file = next(AQ.bedWant)
            if not file then return true end
            if AQ.bedSheets[file] ~= nil then AQ.bedWant[file] = nil
            else
                L = { file = file }
                L.co = coroutine.create(function() loadSheet(GFX, file) end)
                AQ.bedLoader = L
            end
        end
        if L then
            GFX.pace = function()
                if coroutine.running() == L.co and dfhack.getTickCount() > deadline then coroutine.yield() end
            end
            local ok, err = coroutine.resume(L.co)
            GFX.pace = nil
            if not ok then
                AQ.bedSheets[L.file] = false
                AQ.bedSheetErr = ('%s: %s'):format(L.file, tostring(err))
            end
            if not ok or coroutine.status(L.co) == 'dead' then AQ.bedWant[L.file] = nil; AQ.bedLoader = nil end
        end
    end
    return next(AQ.bedWant) == nil and not AQ.bedLoader
end
-- a decoded sheet, or nil (missing / failed), or DEFER (queued: still loading)
local function bedSheet(file)
    local s = AQ.bedSheets[file]
    if s ~= nil then return s or nil end
    AQ.bedWant = AQ.bedWant or {}
    AQ.bedWant[file] = true
    return DEFER
end
-- the texture for (family, variant, colour, strength, water depth dw, air levels, absorb), made once at scan time from
-- the sheet's cell; nil at the cap or when the sheet is missing (the cell is skipped, never an error); DEFER when the
-- sheet is still loading or the scan's deadline has passed (the scan resumes there next time)
function bedTexture(GFX, fam, v, rgb, strength, dw, air, absorb, deadline)
    local q = rgb and { (rgb[1] // 8) * 8, (rgb[2] // 8) * 8, (rgb[3] // 8) * 8 } or nil
    air = math.min(4, air or 0)
    if air <= 1 then air = 0 end
    absorb = absorb or 1
    local key = ('%s|%d|%s|%d|%d|%d|%d'):format(fam, v, q and (q[1] .. ',' .. q[2] .. ',' .. q[3]) or '-',
        math.floor((strength or 0) * 100 + 0.5), math.floor((dw or 0.5) * 4 + 0.5), air, math.floor(absorb * 100 + 0.5))
    local h = AQ.bedTex[key]
    if h ~= nil then return h or nil end
    if AQ.bedTexN >= LIMIT.bed_tex then return nil end
    if deadline then
        -- start a texture only when it fits the slice (its measured cost); the slice's first may start any time before
        -- the deadline (progress), so a slow texture never runs a scan past the slow-scan line (rig 2 Oct, 120x68: 10 scans > 8 ms)
        local now = dfhack.getTickCount()
        local first = (AQ.bedSliceTex or 0) == 0
        if now > deadline or (not first and now + math.max(1, AQ.bedTexMs or 1) > deadline) then return DEFER end
    end
    local list = GFX.BED[fam]
    if not list then return nil end
    local src = list[v] or list[1]
    local img = bedSheet(src[1])
    if img == DEFER then return DEFER end
    if not img and src ~= list[1] then
        src = list[1]; img = bedSheet(src[1])
        if img == DEFER then return DEFER end
    end
    local cell = img and GFX.cell(img, src[2], src[3])
    if not cell then AQ.bedTex[key] = false; return nil end
    local c0 = cpuMs()
    local ok, handle = pcall(makeTile, GFX.bedPixels(cell, { tint = q, strength = strength, dw = dw, air = air,
        absorb = absorb, contrast = fam == 'mud' and GFX.MUD.contrast or nil }), 32, 32)
    AQ.bedTex[key] = ok and handle or false
    if ok then AQ.bedTexN = AQ.bedTexN + 1 end
    local spent = cpuMs() - c0
    AQ.bedTexMs = AQ.bedTexMs and (AQ.bedTexMs * 0.7 + spent * 0.3) or spent
    AQ.bedSliceTex = (AQ.bedSliceTex or 0) + 1
    return ok and handle or nil
end

-- the liquid at a cell: flow_size (0 = dry) and whether it is magma
local function liquidAt(x, y, z)
    local des = dfhack.maps.getTileFlags(x, y, z)
    if not des or des.flow_size < 1 then return 0, false end
    local mag = des.liquid_type == true or des.liquid_type == 1 or des.liquid_type == df.tile_liquid.Magma
    return des.flow_size, mag, des.water_salt and true or false
end
-- one water cell whose surface is at zs (k levels below the view: 0 = the view level itself; 1+ = lifted): find its
-- bed, its family and colour; append to the run (the texture is made in the texture pass)
local function bedCell(run, c, GFX, x, y, zs, k, salt)
    local tt = dfhack.maps.getTileType(x, y, zs)
    if not tt then return end
    local sh = basicShape(tt)
    local bz, tier = zs, 0
    if sh == 'open' then
        bz = nil
        for zz = zs - 1, math.max(0, zs - c.bed_depth), -1 do
            local t2 = dfhack.maps.getTileType(x, y, zz)
            if not t2 then break end
            local s2 = basicShape(t2)
            if s2 ~= 'open' then
                if not dfhack.maps.isTileVisible(x, y, zz) then run.hidden = run.hidden + 1; return end
                if s2 == 'floor' then bz, tier, tt = zz, zs - zz, t2
                elseif s2 == 'wall' then bz, tier, tt = zz, zs - zz - 1, t2   -- the top of a wall is the floor of the level above it
                end
                break
            end
        end
        if not bz then run.beyond = run.beyond + 1; return end   -- deeper than bed_depth (or a hole): DF's fill stays
        if tier > 0 then run.deep = run.deep + 1 end
    elseif sh ~= 'floor' then
        return
    end
    local fam, rgb, strength
    if c.bed_material ~= 'auto' then
        -- v1 (sand-mud): salt water lies on sand, fresh water (rivers, brooks, lakes, pools, cavern water) on mud; the
        -- surface cell's water_salt flag decides; no geology read
        if salt then fam, strength = GFX.SEA_BED, 0
        else fam, rgb, strength = 'mud', GFX.MUD.rgb, GFX.MUD.strength end
        if fam == 'mud' then run.fresh = run.fresh + 1 else run.salt = run.salt + 1 end
    else
        local ttmat = df.tiletype.attrs[tt].material
        local mi = bedMaterial(x, y, bz, ttmat)
        fam, rgb, strength = bedChoice(ttmat, mi, c, GFX)
    end
    if not GFX.BED[fam] then return end
    local n = run.n + 1
    run.n = n
    run.x[n], run.y[n], run.k[n], run.t[n], run.bz[n], run.cf[n], run.rgb[n], run.st[n] = x, y, k, tier, bz, fam, rgb, strength
    run.tierAt[(y - run.y1) * 4096 + (x - run.x1)] = tier
    run.cellAt[(y - run.y1) * 4096 + (x - run.x1)] = n
    if k > 0 then
        run.lifted = run.lifted + 1
        run.liftAt[(y - run.y1) * 4096 + (x - run.x1)] = n
        -- an item at the lifted surface (its block's occupancy): its layer is copied up each frame (items stay put). The
        -- block is read once per scan: most blocks hold no item, and their cells cost no call.
        local bk = ((zs * 1024 + (y >> 4)) * 1024) + (x >> 4)
        local b = run.blocks[bk]
        if b == nil then
            local okB, blk = pcall(function()
                local bb = dfhack.maps.getTileBlock(x, y, zs)
                return bb and bb.items and #bb.items > 0 and bb or false
            end)
            b = okB and blk or false
            run.blocks[bk] = b
        end
        if b then
            local okI, item = pcall(function() local occ = b.occupancy[x & 15][y & 15]; return occ and occ.item end)
            if okI and item then run.items[#run.items + 1] = n end
        end
    end
end

-- the cells pass: every visible water cell of the view level, and (lift) every open cell of the view level whose
-- column holds water within the levels DF draws below (number_of_lower_elevations_shown, at most 8): DF draws that
-- water through gps.lower_viewport[k-1] with the vanilla opaque sprite (the mod's tokens do not reach lower
-- viewports; rig 2 Oct), so the bed lifts it to the view level, where DF draws the mod's translucent water over the bed
local function cellsPass(run, c, GFX, deadline)
    local x2, y2, z = run.x1 + run.W - 1, run.y1 + run.H - 1, run.z
    local K = c.bed_lift and run.lower or 0
    local y = run.nextY
    local did = 0   -- progress: a few cells a call whatever the clock says
    while y <= y2 do
        local x = (y == run.nextY) and run.nextX or run.x1
        while x <= x2 do
            if run.n >= LIMIT.bed_cells then return 'cap' end
            did = did + 1
            if did > 4 and (x & 3) == 0 and dfhack.getTickCount() > deadline then run.nextY, run.nextX = y, x; return 'deadline' end
            local w, mag, salt = liquidAt(x, y, z)
            if w > 0 then
                if not mag and dfhack.maps.isTileVisible(x, y, z) then bedCell(run, c, GFX, x, y, z, 0, salt) end
            elseif K > 0 then
                local tt = dfhack.maps.getTileType(x, y, z)
                if tt and basicShape(tt) == 'open' then
                    for k = 1, K do
                        local zz = z - k
                        if zz < 0 then break end
                        local w2, mag2, salt2 = liquidAt(x, y, zz)
                        if w2 > 0 then
                            if not mag2 and dfhack.maps.isTileVisible(x, y, zz) then bedCell(run, c, GFX, x, y, zz, k, salt2) end
                            break
                        end
                        local t2 = dfhack.maps.getTileType(x, y, zz)
                        if not t2 or basicShape(t2) ~= 'open' then break end
                    end
                end
            end
            x = x + 1
        end
        y = y + 1
        run.nextY, run.nextX = y, run.x1
    end
    return nil
end
-- the texture pass: per cell, its water depth smoothed over its water neighbours (GFX.bedDepth), the family after
-- gravel patches and the variant (GFX.bedMix), the texture; resumable at the cell it stopped on
local function texPass(run, c, GFX, deadline)
    local tierAt = function(xx, yy) return run.tierAt[(yy - run.y1) * 4096 + (xx - run.x1)] end
    local first = run.ti
    for i = run.ti, run.n do
        if i > first and (i & 7) == 0 and dfhack.getTickCount() > deadline then run.ti = i; return 'deadline' end
        local x, y = run.x[i], run.y[i]
        local dw = GFX.bedDepth(tierAt, x, y)
        local fam, v = GFX.bedMix(run.cf[i], x, y, run.bz[i], dw)
        local st = run.st[i]
        if fam ~= run.cf[i] then st = st * 0.5 end   -- gravel patches take half the ground's tint
        local h = bedTexture(GFX, fam, v, run.rgb[i], st, dw, run.k[i], c.bed_absorb, deadline)
        if h == DEFER then run.ti = i; return 'deadline' end
        run.h[i] = h or false
        if h then run.fams[fam] = (run.fams[fam] or 0) + 1 else run.capped = run.capped + 1 end
    end
    run.ti = run.n + 1
    return nil
end

-- Rivers (round 6, rig 3 Oct, AQUA_LAKE z55): river cells carry the standing-water liquid flag, so DF draws the
-- sand-baked UNDERWATER tile on them and RIVER_BED_* never shows under water. The user's spec: rivers are MUD. So for a
-- river cell in the current view (at the view level, or lifted from the bank) the frame clears the main liquid flag (DF
-- draws no water tile there) and writes the mod's own mud-under-water tile (sw_aq_river.png, loaded with
-- dfhack.textures.loadTileset from the world's copy: row 7 - level, a mirrored variant) into the background; the
-- creature, item and flow layers are not touched. River = DF's perm_flow_dir set (not 0 inactive, not 9 none), read once
-- per map block and cached for the map (perm_flow_dir does not change); the scan prefetches the blocks around the view.
local function riverBlockRead(bx, by, z)
    local t = false
    pcall(function()
        local b = dfhack.maps.getTileBlock(bx * 16, by * 16, z)
        local lfw = b and b.liquid_flow
        if not lfw then return end
        t = {}
        for lx = 0, 15 do
            local col = lfw[lx]
            for ly = 0, 15 do
                local d = col[ly].perm_flow_dir
                if d ~= 0 and d ~= 9 then t[lx * 16 + ly] = true end
            end
        end
    end)
    return t
end
local function riverCache()
    local id = mapId()
    local R = AQ.rivers
    if not R or R.map ~= id then R = { map = id, b = {}, n = 0 }; AQ.rivers = R end
    return R
end
-- true / false, or nil when the block is not read and `read` is false
local function isRiver(R, x, y, z, read)
    if x < 0 or y < 0 or z < 0 then return false end
    local k = (z * 4096 + (y >> 4)) * 4096 + (x >> 4)
    local t = R.b[k]
    if t == nil then
        if not read then return nil end
        t = riverBlockRead(x >> 4, y >> 4, z)
        R.b[k], R.n = t, R.n + 1
    end
    return t and t[(x & 15) * 16 + (y & 15)] or false
end
_ENV.isRiver, _ENV.riverCache = isRiver, riverCache
-- the blocks of the view and a block around it, at the view level and the lower levels DF draws (scan time, sliced)
local function riverPrefetch(run, deadline)
    local R = riverCache()
    for z = run.z, math.max(0, run.z - run.lower), -1 do
        for by = math.max(0, run.y1 - 16) >> 4, (run.y1 + run.H + 15) >> 4 do
            for bx = math.max(0, run.x1 - 16) >> 4, (run.x1 + run.W + 15) >> 4 do
                if R.b[(z * 4096 + by) * 4096 + bx] == nil then
                    if dfhack.getTickCount() > deadline then return false end
                    isRiver(R, bx * 16, by * 16, z, true)
                end
            end
        end
    end
    return true
end

-- creatures below the view (v1, user 2 Oct: "visibility of aquatic creatures at z-levels below the camera view ...
-- shaded with an increasing grey or blue alpha tint"): one fog tile per level k (1..8), alpha 40 + 25 k (at most 200),
-- painted over the creature DF drew in lower_viewport[k-1] once it is copied into the main viewport
local BELOW_FOG = { 58, 84, 106 }
local function belowTex()
    local T = AQ.belowTex
    if T then return T end
    T = { h = {}, a = {} }
    for k = 1, 8 do
        local a = math.min(200, 40 + 25 * k)
        local px = {}
        for p = 1, 1024 do px[p] = pack(BELOW_FOG[1], BELOW_FOG[2], BELOW_FOG[3], a) end
        local ok, h = pcall(makeTile, px, 32, 32)
        T.h[k], T.a[k] = ok and h or false, a
    end
    AQ.belowTex = T
    return T
end
_ENV.belowTex = belowTex
-- what the frame copies up, refreshed every scan (units move; the bed's cells do not). No DF call per unit: a unit
-- counts when its column is one of the bed's water columns (water seen from the view: the view level's own, or lifted)
-- and it is in that water (at or above the bed, below the view), at most DF's lower levels down.
--   run.below = { x, y, k, ... } in map coordinates (the frame indexes them by the CURRENT view: no stale index after
--     a scroll): the unit's cell and its water neighbours (it may move a cell before the next scan); the frame copies DF's creature sprite from lower_viewport[k-1] where it drew one, and fogs it for k;
--   run.swim = { cell, 2, ... }: lifted cells holding an item (the cells pass): their item layer is copied up.
-- (Rig 2 Oct: reading five lower layers under every lifted cell each frame was most of a 2.4 ms paint.)
local function bedSwim(run, c)
    if not run or not run.on or not run.cellAt or (fuse('bed').degrade or 0) >= 1 then
        if run then run.swim, run.below = nil, nil end
        return
    end
    local list = {}
    for _, i in ipairs(run.items) do list[#list + 1] = i; list[#list + 1] = 2 end
    run.swim = list
    if c and c.bed_below == false or run.lower < 1 then run.below = nil; return end
    belowTex()
    local below, best, n = {}, {}, 0
    local ok, units = pcall(dfhack.units.getUnitsInBox, run.x1, run.y1, math.max(0, run.z - run.lower),
        run.x1 + run.W - 1, run.y1 + run.H - 1, run.z - 1)
    if ok and units then
        for m, u in ipairs(units) do
            if m > LIMIT.units or n >= LIMIT.below_cells then run.belowCap = true; break end
            if not dfhack.units.isDead(u) then
                local ux, uy, uz = dfhack.units.getPosition(u)
                local k = run.z - uz
                local i = run.cellAt[(uy - run.y1) * 4096 + (ux - run.x1)]
                if i and k >= 1 and k <= run.lower and uz >= run.bz[i] then
                    for dy = -1, 1 do
                        for dx = -1, 1 do
                            local x, y = ux + dx, uy + dy
                            local j = run.cellAt[(y - run.y1) * 4096 + (x - run.x1)]
                            if j and uz >= run.bz[j] then
                                local cell = y * 65536 + x
                                local at = best[cell]
                                if not at then
                                    n = n + 1
                                    below[#below + 1] = x; below[#below + 1] = y; below[#below + 1] = k
                                    best[cell] = #below
                                elseif k < below[at] then below[at] = k end   -- the shallower creature shows
                            end
                        end
                    end
                end
            end
        end
    end
    run.below = below
end

function scanBed(c)
    local t0 = dfhack.getTickCount()
    local deadline = t0 + LIMIT.bed_slice_ms
    AQ.bedSliceTex = 0
    local on, why = bedOn(c)
    if not on then
        AQ.bed, AQ.bedBuild = { n = 0, why = why, on = false }, nil
        scanDone('bed', 0, 0, why)
        return AQ.bed
    end
    bedReset()
    local GFX = gfxMod()
    local x1, y1, _, _, z, W, H = view()
    local lower = 0
    pcall(function() lower = df.global.d_init.display.number_of_lower_elevations_shown end)
    lower = math.max(0, math.min(8, tonumber(lower) or 0))
    local okB, baked = pcall(worldBake)
    baked = okB and baked or false
    local key = ('%d,%d,%d,%d,%d,%s,%s,%s,%s,%s,%d,%s,%s'):format(z, x1, y1, W, H, c.bed_depth, c.bed_tint, c.bed_river,
        tostring(c.bed_lift), c.bed_absorb, lower, tostring(c.bed_material), tostring(baked))
    local run = AQ.bedBuild
    if run and run.key == key and run.done then
        run.age = run.age + 1
        -- a big view's build takes many scans: rebuild no sooner than 4x that (water seldom moves; the bed is not
        -- rebuilding all the time)
        if run.age < math.max(LIMIT.bed_rebuild, 4 * (run.scans or 0)) then AQ.bed.why = why; bedSwim(AQ.bed, c); return AQ.bed end   -- the view has not moved: the last scan stands
    end
    if not run or run.key ~= key or run.done then
        local moved = not run or run.key ~= key
        run = { key = key, z = z, x1 = x1, y1 = y1, W = W, H = H, lower = lower, n = 0, ti = 1,
                x = {}, y = {}, k = {}, t = {}, bz = {}, cf = {}, rgb = {}, st = {}, h = {}, tierAt = {}, fams = {},
                liftAt = {}, cellAt = {}, items = {}, blocks = {}, salt = 0, fresh = 0,
                nextY = y1, nextX = x1, cellsDone = false, done = false, age = 0, deep = 0, beyond = 0, capped = 0,
                hidden = 0, lifted = 0, why = why, on = true, scans = 0, baked = baked }
        AQ.bedBuild = run
        if moved then AQ.bed = run end   -- a moved view paints the new scan as it fills; a rebuild swaps in when done
    end
    run.scans, run.why = run.scans + 1, why
    local stopped
    if run.baked then
        -- the bed is in the mod's art: the scan only finds the water columns (creatures below, the lift's open cells)
        -- and reads the river blocks around the view (the frame's river override)
        if not run.riversDone then run.riversDone = riverPrefetch(run, deadline) end
        if not run.cellsDone then
            local s1 = cellsPass(run, c, GFX, deadline)
            if s1 == 'deadline' then stopped = 'deadline (cells)' else run.cellsDone, run.cap = true, s1 == 'cap' end
        end
        if run.cellsDone then run.done = true; AQ.bed = run; if run.cap then stopped = 'cell cap' end end
    elseif not loaderRun(GFX, deadline) then stopped = 'loading sheets'
    else
        if not run.cellsDone then
            local s1 = cellsPass(run, c, GFX, deadline)
            if s1 == 'deadline' then stopped = 'deadline (cells)' else run.cellsDone, run.cap = true, s1 == 'cap' end
        end
        if run.cellsDone then
            if texPass(run, c, GFX, deadline) then
                stopped = next(AQ.bedWant or {}) and 'loading sheets' or 'deadline (textures)'
            else
                run.done = true; AQ.bed = run
                if run.cap then stopped = 'cell cap' end
            end
        end
    end
    run.stopped = stopped
    bedSwim(AQ.bed, c)
    local fams = {}
    for f, n in pairs(run.fams) do fams[#fams + 1] = ('%s %d'):format(f, n) end
    table.sort(fams)
    scanDone('bed', dfhack.getTickCount() - t0, run.n, ('%s%s; %d cells (%d lifted from below; %s), %d deep, %d deeper than %d, %d hidden, %d over the texture cap; scan %d of this view')
        :format(stopped and ('in progress: ' .. stopped .. '; ') or '', why, run.n, run.lifted, table.concat(fams, ', '), run.deep,
                run.beyond, c.bed_depth, run.hidden, run.capped, run.scans))
    return run
end

--========================================================================================
-- paths (the mods folder, the install)
--========================================================================================
local function slash(p) p = tostring(p or ''); if p ~= '' and not p:match('[/\\]$') then p = p .. '/' end; return p end
function AQ_installDir()
    local ok, p = pcall(function() return dfhack.filesystem.getInstallDir() end)
    if ok and p and p ~= '' then return slash(p) end
    return slash(dfhack.getDFPath())
end
function AQ_baseDir()
    local ok, p = pcall(function() return dfhack.filesystem.getBaseDir() end)
    if ok and p and p ~= '' then return slash(p) end
    return slash(dfhack.getDFPath())
end

--========================================================================================
-- the overlays
--========================================================================================
local PEN
local function pen()
    if not PEN then PEN = dfhack.pen.parse({ ch = 32, fg = COLOR_WHITE, bg = COLOR_BLACK }) end
    return PEN
end
local texposCache = {}
local function texpos(h)
    local t = texposCache[h]
    if t == nil then t = dfhack.textures.getTexposByHandle(h) or false; texposCache[h] = t end
    return t
end

AquariumView = defclass(AquariumView, overlay.OverlayWidget)
AquariumView.ATTRS{
    desc = 'seasonal-wildlife Aquarium: creatures below the view through the water, ocean waves and foam.',
    default_pos = { x = 1, y = 1 }, viewscreens = 'dwarfmode', default_enabled = true, fullscreen = true,
    frame = { w = 1, h = 1 }, overlay_onupdate_max_freq_seconds = 0.25, version = 1,
}
-- every layer's last scan dropped (the master switch went off): nothing is painted from a stale run
local function dropRuns() AQ.lens, AQ.waves, AQ.veil, AQ.bed, AQ.bedBuild, AQ.flowfx = nil, nil, nil, nil, nil, nil end
_ENV.dropRuns = dropRuns
-- the layers other than the bed, at scan_hz
local function scanOthers(c, cfg)
    if c.lens and not fuse('lens').tripped then
        local ok, err = pcall(scanLens, c, cfg); if not ok then trip('lens', 'scan error: ' .. tostring(err)) end
    end
    if c.waves == 'off' then AQ.waves = nil   -- v7.1-waves: `waves off` drops the run (it used to paint on from it)
    elseif not fuse('waves').tripped then
        local ok, err = pcall(scanWaves, c); if not ok then AQ.waves = nil; trip('waves', 'scan error: ' .. tostring(err)) end
    end
    if c.veil and not fuse('veil').tripped then
        local ok, err = pcall(scanVeil, c); if not ok then trip('veil', 'scan error: ' .. tostring(err)) end
    end
    if not c.streaks and not c.shimmer then AQ.flowfx, AQ.flowBuild, AQ.flowCells = nil, nil, nil
    elseif not fuse('flow').tripped then
        local ok, err = pcall(scanFlowFx, c); if not ok then AQ.flowfx = nil; trip('flow', 'scan error: ' .. tostring(err)) end
    end
end
-- the native `aquarium` plugin (sw aquarium-plugin) draws the bed, depth, creatures below and the surf itself: while it
-- is enabled every Lua layer stands down (two painters on one buffer fight; the Lua bed undid the plugin's fill swap).
-- Asked once a second through the plugin's own isEnabled (open_plugin raises when it is not loaded: false).
local function pluginOn()
    local now = dfhack.getTickCount()
    if AQ.pluginAt and now - AQ.pluginAt < 1000 then return AQ.pluginOn end
    local t, on = {}, false
    if pcall(dfhack.open_plugin, t, 'aquarium') and t.isEnabled then
        local ok, v = pcall(t.isEnabled); on = ok and v == true
    end
    AQ.pluginAt, AQ.pluginOn = now, on
    return on
end
_ENV.pluginOn = pluginOn
function AquariumView:overlay_onupdate()
    self.c = nil
    if not dfhack.isMapLoaded() or not dfhack.screen.inGraphicsMode() then return end
    if pluginOn() then dropRuns(); return end
    local c, cfg = config()
    local period = 1 / math.max(1, math.min(10, c.scan_hz or 4))
    -- a moved view's bed fills in at bed_build_hz (16) while it builds (5 ms slices); the other layers keep scan_hz
    local b = AQ.bedBuild
    local building = c.bed ~= 'off' and b and not b.done and AQ.bed == b and not fuse('bed').tripped
    self.overlay_onupdate_max_freq_seconds = building and math.min(period, 1 / LIMIT.bed_build_hz) or period
    if not c.enabled then dropRuns(); return end
    self.c = c
    local now = dfhack.getTickCount()
    local others = not building or now - (AQ.othersAt or -1e9) >= period * 1000 - 1
    if others then AQ.othersAt = now end
    if others then scanOthers(c, cfg) end
    if c.bed == 'off' then AQ.bed, AQ.bedBuild = nil, nil
    elseif not fuse('bed').tripped then
        local ok, err = pcall(scanBed, c); if not ok then trip('bed', 'scan error: ' .. tostring(err)) end
    end
end
-- the bed, per frame. Cells of the view level's own water (k = 0): under every one DF drew water on this frame (liquid
-- flag set), write the bed's texpos into the background layer; the liquid flag is never touched. DF's generic fill is
-- learned once per scan, on its first frame, as the most common non-zero background under those cells (the rig read
-- 2566 there, the same id as a soil wall: DF draws no floor under water; a wall sample would be fooled by a smoothed or
-- engraved wall). A cell whose background holds something other than empty (0), that fill or one of our bed sprites
-- is DF drawing something real there: left alone and counted. Never learned (every background 0 or ours), every water
-- cell is written, as on the rig.
-- Lifted cells (k >= 1: the view cell is open space, the water k levels down; rig 2 Oct, 776 cells): where the main
-- viewport drew no liquid and DF drew water in lower_viewport[k-1] at the same index, copy that liquid flag into the
-- main viewport (DF then draws the mod's translucent water at the view level), write the bed into the main background
-- (open space there: 15561, or a shore variant whose floor_flag edge bits are KEPT: only background and the liquid flag
-- are written), and copy the lower cell's creature / item / vermin layers into the main viewport where the main layer
-- is empty, so swimmers at that surface stay visible over the lifted water.
local LIFT_LAYERS = { 'screentexpos_item', 'screentexpos_vermin', 'screentexpos_left_creature', 'screentexpos',
                      'screentexpos_right_creature' }
_ENV.LIFT_LAYERS = LIFT_LAYERS
local function learnFill(run, lf, bg, wx, wy, W, H, own)
    local count, best, bn = {}, nil, 0
    for i = 1, run.n do
        if run.k[i] == 0 then
            local sx, sy = run.x[i] - wx, run.y[i] - wy
            if sx >= 0 and sy >= 0 and sx < W and sy < H then
                local idx = sx * H + sy
                if lf[idx] ~= 0 then
                    local v = bg[idx]
                    if v ~= 0 and not own[v] then
                        local k = (count[v] or 0) + 1
                        count[v] = k
                        if k > bn then best, bn = v, k end
                    end
                end
            end
        end
    end
    run.fillTries = (run.fillTries or 0) + 1
    if best or run.fillTries >= 10 then run.fill = best or false end
end
-- lower_viewport[k-1] for this frame, when DF drew that level at the main viewport's size; false otherwise. Its layers
-- are fetched only when a swimmer is copied.
local function lowerView(lowers, k, W, H)
    local lv = lowers[k]
    if lv ~= nil then return lv end
    lv = false
    local ok, v = pcall(function() return df.global.gps.lower_viewport[k - 1] end)
    if ok and v and v.dim_x == W and v.dim_y == H then lv = { v = v, lf = v.screentexpos_liquid_flag, layers = {} } end
    lowers[k] = lv
    return lv
end
local function lowerLayer(lv, li)
    local a = lv.layers[li]
    if not a then a = lv.v[LIFT_LAYERS[li]]; lv.layers[li] = a end
    return a
end
-- fail soft (DEGRADE): what the bed gives up, step by step, before its fuse trips; the share of lifted cells kept
local BED_STEPS = { 'creatures below and items no longer copied up', 'lifted water thinned to the half nearest the view centre',
                    'lifted water thinned to the quarter nearest the view centre', 'lift off: the bed only under water at your level' }
local LIFT_KEEP = { [0] = 1, 1, 0.5, 0.25, 0 }
DEGRADE.bed = function(f)
    local run = AQ.bed
    if not run then return nil end
    local step = (f.degrade or 0) + 1
    -- nothing lifted: only the first step (creatures below) gives anything up
    local liftedAny = (run.lifted or 0) > 0 or (AQ.lift and AQ.lift.cur.n > 0)
    if not liftedAny and (step > 1 or not (run.below and #run.below > 0)) then return nil end
    if not BED_STEPS[step] then return nil end
    f.degrade, f.degradeWhy = step, BED_STEPS[step]
    if step == 1 then run.swim, run.below = nil, nil end
    return BED_STEPS[step]
end
-- the paint plan, made once per scan (and when the view, the scan's progress or the degrade step changes): viewport
-- indices and texposes, own-level cells apart, lifted cells grouped by k with their lower liquid flags (read whole on
-- the plan's first frame, then 1/LIFT_REFRESH of them a frame) and three sentinel cells
local LIFT_REFRESH = 16
local function bedPlan(run, wx, wy, W, H, step)
    local stamp = ('%d,%d,%d,%d,%d,%d,%d'):format(run.n, run.ti or 0, wx, wy, W, H, step)
    local P = run.plan
    if P and P.stamp == stamp then return P end
    local own = AQ.bedOwn
    local tps = {}
    P = { stamp = stamp, oi = {}, otp = {}, on = 0, groups = {}, gOf = {}, jOf = {}, liftN = 0, thinned = 0 }
    local limit = W * H
    local lifted, idxOf, tpOf = {}, {}, {}
    for i = 1, run.n do
        local h = run.h[i]
        if h then
            local sx, sy = run.x[i] - wx, run.y[i] - wy
            if sx >= 0 and sy >= 0 and sx < W and sy < H and sx * H + sy < limit then
                local tp = tps[h]
                if tp == nil then
                    tp = dfhack.textures.getTexposByHandle(h) or false
                    tps[h] = tp
                    if tp then own[tp] = true end
                end
                if tp then
                    local idx = sx * H + sy
                    if run.k[i] == 0 then P.on = P.on + 1; P.oi[P.on], P.otp[P.on] = idx, tp
                    else lifted[#lifted + 1] = i; idxOf[i], tpOf[i] = idx, tp end
                end
            end
        end
    end
    local keep = math.floor(#lifted * LIFT_KEEP[math.min(step, 4)] + 0.5)
    if keep < #lifted then
        local cx, cy = wx + W / 2, wy + H / 2
        local d = {}
        for _, i in ipairs(lifted) do local dx, dy = run.x[i] - cx, run.y[i] - cy; d[i] = dx * dx + dy * dy end
        table.sort(lifted, function(a, b) if d[a] ~= d[b] then return d[a] < d[b] end; return a < b end)
        P.thinned = #lifted - keep
        for j = #lifted, keep + 1, -1 do lifted[j] = nil end
    end
    for _, i in ipairs(lifted) do
        local k = run.k[i]
        local g = P.groups[k]
        if not g then g = { k = k, n = 0, idx = {}, tp = {}, flag = {}, primed = false, slice = 1, sent = {}, dry = 0 }; P.groups[k] = g end
        g.n = g.n + 1
        g.idx[g.n], g.tp[g.n] = idxOf[i], tpOf[i]
        P.gOf[i], P.jOf[i] = g, g.n
    end
    P.liftN = #lifted
    run.plan = P
    return P
end
-- three sentinels among a group's cells with water below (first, middle, last)
local function pickSentinels(g)
    local wet = {}
    for j = 1, g.n do if g.flag[j] ~= 0 then wet[#wet + 1] = j end end
    g.sent = {}
    if #wet > 0 then
        g.sent[1] = wet[1]
        if #wet > 2 then g.sent[#g.sent + 1] = wet[(#wet + 1) // 2] end
        if #wet > 1 then g.sent[#g.sent + 1] = wet[#wet] end
    end
end
-- ========== baked worlds (round 5: the bed is in the mod's art) ==========
-- User 3 Oct: "when I scroll with wasd the water clips in and out" -- a per-view plan built by the sliced map scan lags
-- a scroll by seconds. With the bed baked into UNDERWATER_1..7 the frame needs no bed sprite: lifting a cell is ONE
-- write (the lower liquid flag into the main viewport; DF then draws the mod's baked tile there). The plan comes from
-- DF's own buffers, keyed by the CURRENT view (window x/y/z, viewport size): a view change rebuilds it in that frame
-- (up to LIFT_BUILD_READS*2 buffer reads; a huge zoom finishes over the next frames, painting only what is built --
-- never an old plan's indices on a new view). A cell lifts where the main viewport drew no liquid, its background is
-- open space (values learned from the map scan's lifted cells: 15561 and the shore variants on the rig) and a lower
-- viewport k drew liquid (through open space at the levels between).
local LIFT_BUILD_READS, LIFT_REBUILD_FRAMES, OPEN_MAX = 6000, 90, 64
-- the world's river tiles (28 handles), or nil and why
local function riverTiles()
    local B = AQ.bedBake
    if not B or not B.v or not B.path then return nil, 'no baked world' end
    local T = AQ.riverTex
    -- a failure is retried every 10 s (the page may be written by an install after the first try)
    if T and T.path == B.path and (T.h or dfhack.getTickCount() < (T.retry or 0)) then return T.h or nil, T.why end
    -- B.path ends with '/': a doubled slash makes DFHack's loadTileset return no tiles (rig 3 Oct)
    local file = B.path:gsub('[/\\]+$', '') .. '/graphics/images/sw_aq_river.png'
    local ok, h = pcall(dfhack.textures.loadTileset, file, 32, 32)
    local why
    if not ok then why = 'cannot load ' .. file .. ': ' .. tostring(h); h = nil
    elseif type(h) ~= 'table' or #h < 28 then why = ('%s holds %s tiles (a mod built before round 6? run install again)'):format(file, type(h) == 'table' and #h or 0); h = nil end
    AQ.riverTex = { path = B.path, h = h or false, why = why, retry = dfhack.getTickCount() + 10000 }
    return h, why
end
local LIFT_AREA = { [0] = 1, 1, 0.7071, 0.5, 0 }   -- the side of the centred box kept at each degrade step (area 1, .5, .25)
local function learnOpen(run, bg, wx, wy, W, H)
    local O = AQ.openBg
    if not O then O = { n = 0, set = {}, gen = 0 }; AQ.openBg = O end
    if O.n >= OPEN_MAX or not run or not run.k or run.learnDone or run.n == 0 then return O end
    local i0 = run.learnAt or 1
    local last = math.min(run.n, i0 + 255)
    for i = i0, last do
        if run.k[i] > 0 then
            local sx, sy = run.x[i] - wx, run.y[i] - wy
            if sx >= 0 and sy >= 0 and sx < W and sy < H then
                local v = bg[sx * H + sy]
                if v and not O.set[v] then O.set[v] = true; O.n = O.n + 1; O.gen = O.gen + 1 end
            end
        end
    end
    if last >= run.n then
        run.learnAt = 1
        if run.done then run.learnDone = true end
    else run.learnAt = last + 1 end
    return O
end
local function newLiftPlan()
    return { sx = 0, n = 0, idx = {}, k = {}, flag = {}, set = {}, done = false, slice = 1,
             rn = 0, ri = {}, rl = {}, rv = {}, rset = {},   -- river cells: index, water level, variant
             fn = 0, fi = {}, fset = {} }                     -- shallow view-level water over water: index
end
local function lowerBg(lv) local b = lv.bg; if not b then b = lv.v.screentexpos_background or {}; lv.bg = b end; return b end
local function liftBuild(P, lf, bg, W, H, K, lowers, budget, open, side, old, wx, wy, z, rivers)
    local reads = 0
    local cx, cy, rx, ry = W / 2, H / 2, W * side / 2, H * side / 2
    local n = P.n
    local R = rivers and riverCache()
    local function river(x, y, zz)
        if not R then return false end
        local key = (zz * 4096 + (y >> 4)) * 4096 + (x >> 4)
        if R.b[key] == nil then reads = reads + 600 end   -- a block read: ~530 accesses
        return isRiver(R, x, y, zz, true)
    end
    local function addRiver(idx, level, x, y)
        local m = P.rn + 1
        P.rn = m
        P.ri[m], P.rl[m], P.rv[m] = idx, math.max(1, math.min(7, level)), ((x * 73856093) ~ (y * 19349663)) & 3
        P.rset[idx] = P.rl[m]
    end
    local function addFix(idx) local m = P.fn + 1; P.fn = m; P.fi[m] = idx; P.fset[idx] = true end
    while P.sx < W and reads < budget do
        local sx = P.sx
        if side >= 1 or math.abs(sx + 0.5 - cx) <= rx then
            for sy = 0, H - 1 do
                if side >= 1 or math.abs(sy + 0.5 - cy) <= ry then
                    local idx = sx * H + sy
                    local x, y = wx + sx, wy + sy
                    reads = reads + 1
                    local f0 = lf[idx]
                    if old and old.rset[idx] then
                        addRiver(idx, old.rset[idx], x, y)   -- ours from the last frame (DF kept it): keep it
                    elseif old and old.fset[idx] then
                        addFix(idx)
                    elseif f0 == 0 or (old and old.set[idx]) then
                        reads = reads + 1
                        local isOpen = open[bg[idx]]
                        if not isOpen then
                            -- a ramp top over a river ramp (rig 3 Oct: the pale squares on the bank) draws its own
                            -- background, never a learned open-space value: ask the map (plan builds only)
                            reads = reads + 3
                            local tt = dfhack.maps.getTileType(x, y, z)
                            local sh = tt and df.tiletype.attrs[tt].shape
                            isOpen = sh == df.tiletype_shape.RAMP_TOP or sh == df.tiletype_shape.EMPTY
                        end
                        if isOpen then
                            for k = 1, K do
                                local lv = lowerView(lowers, k, W, H)
                                if not lv then break end
                                reads = reads + 1
                                local f = lv.lf[idx]
                                if f ~= 0 then
                                    if river(x, y, z - k) then addRiver(idx, (f >> 2) & 7, x, y)
                                    else
                                        n = n + 1
                                        P.idx[n], P.k[n], P.flag[n] = idx, k, f
                                        P.set[idx] = n
                                    end
                                    break
                                end
                                if k == K then break end
                                reads = reads + 1
                                if not open[lowerBg(lv)[idx]] then break end   -- land below: nothing deeper shows
                            end
                        end
                    elseif river(x, y, z) then
                        -- a river cell at the view level; a little water there over the river below (a ramp top, a
                        -- spill: rig 3 Oct, the pale squares on the bank) draws as the full river like its neighbours
                        local lvl = (f0 >> 2) & 7
                        local tt = lvl < 7 and dfhack.maps.getTileType(x, y, z)
                        local sh = tt and df.tiletype.attrs[tt].shape
                        if tt then reads = reads + 3 end
                        -- only water standing in open space or a ramp top sits over the river; a shallow river cell
                        -- on its own bed (a floor) keeps its level
                        if lvl < 7 and z > 0 and (sh == df.tiletype_shape.RAMP_TOP or sh == df.tiletype_shape.EMPTY) then
                            local below = false
                            local lv = K > 0 and lowerView(lowers, 1, W, H)
                            if lv then reads = reads + 1; below = lv.lf[idx] ~= 0 end
                            if not below then
                                reads = reads + 4
                                local fl = dfhack.maps.getTileFlags(x, y, z - 1)
                                below = fl and fl.flow_size > 0 or false
                            end
                            if below then lvl = 7 end
                        end
                        addRiver(idx, lvl, x, y)
                    elseif ((f0 >> 2) & 7) < 7 and z > 0 and K > 0 then
                        -- defect 1 (rig 3 Oct): a little water at the view level (a wave's or a flow's spill) over water in
                        -- the cell below draws as the baked UNDERWATER_1..3 = almost bare sand among its lifted
                        -- neighbours: draw it as full water (level 7) like them; over a river, as the river
                        local below = false
                        local lv = lowerView(lowers, 1, W, H)
                        if lv then reads = reads + 1; below = lv.lf[idx] ~= 0 end
                        if not below then
                            reads = reads + 4
                            local fl = dfhack.maps.getTileFlags(x, y, z - 1)
                            below = fl and fl.flow_size > 0 and not (fl.liquid_type == true or fl.liquid_type == 1) or false
                        end
                        if below then
                            if river(x, y, z - 1) then addRiver(idx, 7, x, y) else addFix(idx) end
                        end
                    end
                end
            end
        end
        P.sx = sx + 1
    end
    P.n = n
    P.done = P.sx >= W
    return reads
end
local function paintBaked(run, c, wx, wy, z, W, H, fr)
    local mv = df.global.gps.main_viewport
    local lf, bg = mv.screentexpos_liquid_flag, mv.screentexpos_background
    local step = fuse('bed').degrade or 0
    local O = learnOpen(run, bg, wx, wy, W, H)
    local K = (c.bed_lift ~= false) and (run.lower or 0) or 0
    local side = LIFT_AREA[math.min(step, 4)]
    if side <= 0 then K = 0 end
    local lowers = {}
    local RT, rtWhy = riverTiles()
    if c.bed_river_mud == false then RT, rtWhy = nil, 'off (aquarium bed river-mud off)' end
    local vkey = ('%d,%d,%d,%d,%d,%d,%d,%s'):format(wx, wy, z, W, H, K, step, RT and 'mud' or '-')
    local L = AQ.lift
    local budget = LIFT_BUILD_READS
    if not L or L.vkey ~= vkey then
        L = { vkey = vkey, cur = newLiftPlan(), gen = O.gen, age = 0, views = (L and L.views or 0) + 1 }
        AQ.lift = L
        budget = LIFT_BUILD_READS * 2   -- the view changed: as much of the new plan as one frame allows, now
    elseif O.gen ~= L.gen and not L.next then
        L.next, L.gen = newLiftPlan(), O.gen   -- a new open-space value: rebuild in the background (same view)
    end
    L.age = L.age + 1
    if L.age >= LIFT_REBUILD_FRAMES and not L.next and L.cur.done then L.next, L.age = newLiftPlan(), 0 end
    local reads = 0
    if (K > 0 and O.n > 0) or RT then
        if not L.cur.done then reads = liftBuild(L.cur, lf, bg, W, H, K, lowers, budget, O.set, side, nil, wx, wy, z, RT)
        elseif L.next then
            -- the background rebuild (same view: the current plan stays valid) at a quarter of the budget a frame
            reads = liftBuild(L.next, lf, bg, W, H, K, lowers, budget // 4, O.set, side, L.cur, wx, wy, z, RT)
            if L.next.done then L.cur, L.next = L.next, nil end
        end
    end
    local P = L.cur
    local lifted, kept, dry = 0, 0, 0
    if P.n > 0 then
        local pi, pk, pf = P.idx, P.k, P.flag
        -- sentinels: first, middle, last
        local sent = { 1, (P.n + 1) // 2, P.n }
        local any, intact = false, true
        for _, j in ipairs(sent) do
            local lv = lowerView(lowers, pk[j], W, H)
            if lv and lv.lf[pi[j]] ~= 0 then any = true end
            if lf[pi[j]] ~= pf[j] then intact = false end
        end
        if not any then dry = P.n   -- DF drew no liquid below this frame (a menu, a skipped level): leave it
        elseif intact and P.done then kept = P.n   -- DF left the main viewport as we wrote it
        else
            local s0 = P.slice
            for j = s0, P.n, LIFT_REFRESH do
                local lv = lowerView(lowers, pk[j], W, H)
                if lv then pf[j] = lv.lf[pi[j]] end
            end
            P.slice = s0 % LIFT_REFRESH + 1
            -- DF draws a ramp/shore sprite in background_two over some lifted cells (rig 3 Oct, AQUA_SHORE16: ramp tops
            -- under the beach level, bg2 34850..34854 = pale squares on the sea): clear it so the water shows
            local bg2 = mv.screentexpos_background_two
            for j = 1, P.n do
                local f = pf[j]
                if f ~= 0 then
                    local i = pi[j]
                    lf[i] = f; lifted = lifted + 1   -- luacheck: ignore 122 (the lift writes the main viewport's liquid flag)
                    if bg2[i] ~= 0 then bg2[i] = 0 end   -- luacheck: ignore 122
                end
            end
        end
    end
    -- rivers: no DF water tile; the mod's mud-under-water tile in the background (creatures, items, flows draw on top)
    local rivers, fixed = 0, 0
    if RT and P.rn > 0 then
        local ri, rl, rv = P.ri, P.rl, P.rv
        -- DF also draws the (mod's) river bed sprite in background_two on some river cells -- open space and ramp
        -- tops over the river (rig 3 Oct: the pale khaki squares on the bank): clear it so the water shows
        local bg2 = mv.screentexpos_background_two
        for j = 1, P.rn do
            local tp = texpos(RT[(7 - rl[j]) * 4 + rv[j] + 1])
            if tp then
                local idx = ri[j]
                lf[idx] = 0     -- luacheck: ignore 122
                bg[idx] = tp    -- luacheck: ignore 122
                if bg2[idx] ~= 0 then bg2[idx] = 0 end   -- luacheck: ignore 122
                rivers = rivers + 1
            end
        end
    end
    AQ.riverShown = P.rn > 0 and P.rset or nil
    -- shallow view-level water over water: drawn at level 7 like its lifted neighbours
    for j = 1, P.fn do
        local idx = P.fi[j]
        local f = lf[idx]
        if f ~= 0 and (f & 0x1c) ~= 0x1c then lf[idx] = f | 0x1c; fixed = fixed + 1 end   -- luacheck: ignore 122
    end
    -- creatures below and items over lifted water, by map coordinates against the current view
    local copied, shown, notDrawn = 0, 0, 0
    local below = step < 1 and c.bed_below ~= false and run.below
    local mainC
    local function mainLayer(li)
        mainC = mainC or {}
        local ml = mainC[li]
        if not ml then ml = mv[LIFT_LAYERS[li]]; mainC[li] = ml end
        return ml
    end
    if below and #below > 0 then
        local T = AQ.belowTex
        local P0 = pen()
        local paint = dfhack.screen.paintTile
        for p = 1, #below, 3 do
            local bsx, bsy, k = below[p] - wx, below[p + 1] - wy, below[p + 2]
            if bsx >= 0 and bsy >= 0 and bsx < W and bsy < H then
                local idx = bsx * H + bsy
                local lv = lowerView(lowers, k, W, H)
                if lv then
                    local v = lowerLayer(lv, 4)[idx]
                    if v ~= 0 then
                        for li = 3, 5 do
                            local lvv = li == 4 and v or lowerLayer(lv, li)[idx]
                            if lvv ~= 0 then
                                local ml = mainLayer(li)
                                if ml[idx] == 0 then ml[idx] = lvv; copied = copied + 1 end   -- luacheck: ignore 122
                            end
                        end
                        local tp = T and T.h[k] and texpos(T.h[k])
                        if tp then paint(P0, bsx, bsy, nil, tp, true) end
                        shown = shown + 1
                    else notDrawn = notDrawn + 1 end
                end
            end
        end
    end
    local swim = step < 1 and run.swim
    local items = 0
    if swim then
        for p = 1, #swim, 2 do
            local i = swim[p]
            local sx, sy = run.x[i] - wx, run.y[i] - wy
            if sx >= 0 and sy >= 0 and sx < W and sy < H then
                local idx = sx * H + sy
                local j = P.set[idx]
                if j and P.flag[j] ~= 0 then
                    local lv = lowerView(lowers, P.k[j], W, H)
                    local v = lv and lowerLayer(lv, 1)[idx]
                    if v and v ~= 0 then
                        local ml = mainLayer(1)
                        if ml[idx] == 0 then ml[idx] = v; copied = copied + 1 end   -- luacheck: ignore 122
                    end
                    items = items + 1
                end
            end
        end
    end
    fr.baked, fr.wrote, fr.foreign, fr.zero, fr.fill = true, 0, 0, 0, nil
    fr.lifted, fr.kept, fr.dry, fr.liftN, fr.thinned, fr.noLower = lifted, kept, dry, P.n, 0, 0
    fr.planCols, fr.planW, fr.built, fr.open, fr.views = P.sx, W, reads, O.n, L.views
    fr.copied, fr.marked = copied, items
    fr.rivers, fr.riverN, fr.fixed, fr.fixN, fr.riverWhy = rivers, P.rn, fixed, P.fn, RT and nil or rtWhy
    fr.riverBlocks = AQ.rivers and AQ.rivers.n or 0
    fr.belowWatched, fr.belowShown, fr.belowNotDrawn = below and (#below // 3) or 0, shown, notDrawn
end
_ENV.paintBaked = paintBaked

local function paintBed(c, wx, wy, z, W, H)
    local run = AQ.bed
    AQ.riverShown = nil
    if run and run.on and run.baked then
        local fr = AQ.bedFrame or {}
        AQ.bedFrame = fr
        return paintBaked(run, c, wx, wy, z, W, H, fr)
    end
    if not run or not run.on or run.n == 0 or run.z ~= z then return end
    local mv = df.global.gps.main_viewport
    local lf, bg = mv.screentexpos_liquid_flag, mv.screentexpos_background
    local fr = AQ.bedFrame or {}
    AQ.bedFrame = fr
    local own = AQ.bedOwn
    local step = fuse('bed').degrade or 0
    local P = bedPlan(run, wx, wy, W, H, step)
    if run.fill == nil then learnFill(run, lf, bg, wx, wy, W, H, own) end
    local fill = run.fill or nil
    fr.fill = fill
    -- the water's own level: under every cell DF drew water on this frame (3 viewport reads/writes a cell)
    local wrote, foreign, zero = 0, 0, 0
    local oi, otp = P.oi, P.otp
    for j = 1, P.on do
        local idx = oi[j]
        if lf[idx] ~= 0 then
            local cur = bg[idx]
            if cur == 0 or cur == fill or own[cur] or not fill then
                if cur == 0 then zero = zero + 1 end
                bg[idx] = otp[j]   -- luacheck: ignore 122 (the bed writes the viewport's background layer on purpose)
                wrote = wrote + 1
            else
                foreign = foreign + 1
            end
        end
    end
    -- lifted: two writes a cell; the lower flags come from the plan's cache
    local lowers = {}
    local lifted, noLower, dry, kept = 0, 0, 0, 0
    for _, g in pairs(P.groups) do
        g.live = false
        local lv = lowerView(lowers, g.k, W, H)
        if not lv then noLower = noLower + g.n
        else
            local llf, gi, gf, gtp = lv.lf, g.idx, g.flag, g.tp
            local go = true
            if not g.primed or g.dry > LIFT_REFRESH then
                for j = 1, g.n do gf[j] = llf[gi[j]] end
                g.primed, g.dry, g.slice = true, 0, 1
                pickSentinels(g)
            else
                -- did DF draw liquid below this frame? (the sentinels; none drawn: a menu, a level DF skipped)
                local any = #g.sent == 0
                for _, j in ipairs(g.sent) do if llf[gi[j]] ~= 0 then any = true; break end end
                if not any then go = false; g.dry = g.dry + 1; dry = dry + g.n
                else
                    g.dry = 0
                    local s = g.slice
                    for j = s, g.n, LIFT_REFRESH do gf[j] = llf[gi[j]] end
                    g.slice = s % LIFT_REFRESH + 1
                    if g.slice == 1 then pickSentinels(g) end
                end
            end
            if go then
                g.live = true
                -- did DF leave the main viewport as we wrote it last frame? (the sentinels hold our flag and bed)
                local intact = #g.sent > 0
                for _, j in ipairs(g.sent) do
                    local idx = gi[j]
                    if lf[idx] ~= gf[j] or bg[idx] ~= gtp[j] then intact = false; break end
                end
                if intact then
                    kept = kept + g.n
                else
                    for j = 1, g.n do
                        local f = gf[j]
                        if f ~= 0 then
                            local idx = gi[j]
                            lf[idx] = f        -- luacheck: ignore 122
                            bg[idx] = gtp[j]   -- luacheck: ignore 122
                            lifted = lifted + 1
                        end
                    end
                end
            end
        end
    end
    -- creatures below the view (bedSwim): DF's own sprite from lower_viewport[k-1], copied up where the main viewport
    -- has none, then the level's fog tile over it; 1 read a watched cell, ~8 more where a creature is
    local copied, shown, notDrawn = 0, 0, 0
    local below = step < 1 and run.below
    if below and #below > 0 then
        local T = AQ.belowTex
        local P0 = pen()
        local paint = dfhack.screen.paintTile
        local mainC
        for p = 1, #below, 3 do
            local bsx, bsy, k = below[p] - wx, below[p + 1] - wy, below[p + 2]
            local idx = bsx * H + bsy
            local lv = (bsx >= 0 and bsy >= 0 and bsx < W and bsy < H) and lowerView(lowers, k, W, H)
            if lv then
                local v = lowerLayer(lv, 4)[idx]
                if v ~= 0 then
                    mainC = mainC or {}
                    for li = 3, 5 do
                        local lvv = li == 4 and v or lowerLayer(lv, li)[idx]
                        if lvv ~= 0 then
                            local ml = mainC[li]
                            if not ml then ml = mv[LIFT_LAYERS[li]]; mainC[li] = ml end
                            if ml[idx] == 0 then ml[idx] = lvv; copied = copied + 1 end   -- luacheck: ignore 122
                        end
                    end
                    local tp = T and T.h[k] and texpos(T.h[k])
                    if tp then paint(P0, bsx, bsy, nil, tp, true) end
                    shown = shown + 1
                else notDrawn = notDrawn + 1 end
            elseif bsx >= 0 and bsy >= 0 and bsx < W and bsy < H then noLower = noLower + 1 end
        end
    end
    -- items over lifted water: only the cells the scan marked (bedSwim)
    local swim = step < 1 and run.swim
    if swim and P.liftN > 0 then
        local main = {}
        for p = 1, #swim, 2 do
            local i, bits = swim[p], swim[p + 1]
            local g = P.gOf[i]
            if g and g.live and g.flag[P.jOf[i]] ~= 0 then
                local lv = lowers[g.k]
                local idx = g.idx[P.jOf[i]]
                for li = (bits & 2 ~= 0) and 1 or 3, (bits & 1 ~= 0) and #LIFT_LAYERS or 1 do
                    if li ~= 2 then   -- vermin are not tracked by the scan
                        local v = lowerLayer(lv, li)[idx]
                        if v ~= 0 then
                            local ml = main[li]
                            if not ml then ml = mv[LIFT_LAYERS[li]]; main[li] = ml end
                            if ml[idx] == 0 then ml[idx] = v; copied = copied + 1 end   -- luacheck: ignore 122
                        end
                    end
                end
            end
        end
    end
    fr.wrote, fr.foreign, fr.zero, fr.lifted, fr.noLower, fr.copied = wrote, foreign, zero, lifted, noLower, copied
    fr.dry, fr.kept, fr.thinned, fr.liftN, fr.marked = dry, kept, P.thinned, P.liftN, swim and (#swim // 2) or 0
    fr.belowWatched, fr.belowShown, fr.belowNotDrawn = below and (#below // 3) or 0, shown, notDrawn
end
_ENV.paintBed = paintBed
-- the veil also covers lifted cells (their liquid flag was set by the bed this frame): a world without the mod gets its
-- translucent water at the view level too
local function veilCells(run, z)
    if not run or not run.on or run.z ~= z or not run.lifted then return nil end
    return run
end
local function paintVeil(_, wx, wy, z, W, H)
    local run = AQ.veil
    local bed = veilCells(AQ.bed, z)
    if not run or run.z ~= z or not AQ.veilTex or (run.n == 0 and not (bed and bed.lifted > 0)) then return end
    local mv = df.global.gps.main_viewport
    local lf, bg2 = mv.screentexpos_liquid_flag, mv.screentexpos_background_two
    local h = AQ.veilTex.h
    local tp = {}
    for level = 1, 7 do tp[level] = dfhack.textures.getTexposByHandle(h[level]) end
    local limit = W * H
    local function veilAt(px, py)
        local sx, sy = px - wx, py - wy
        if sx >= 0 and sy >= 0 and sx < W and sy < H then
            local idx = sx * H + sy
            if idx < limit then
                local flag = lf[idx]
                if flag ~= 0 and bg2[idx] == 0 then
                    local level = (flag >> 2) & 7
                    if level >= 1 and tp[level] then lf[idx] = 0; bg2[idx] = tp[level] end   -- luacheck: ignore 122 (the veil writes the viewport buffers on purpose)
                end
            end
        end
    end
    for i = 1, run.n do veilAt(run.x[i], run.y[i]) end
    if bed then for i = 1, bed.n do if bed.k[i] > 0 and bed.h[i] then veilAt(bed.x[i], bed.y[i]) end end end
end
local function paintCells(run, wx, wy, W, H, tileOf)
    local P = pen()
    local paint = dfhack.screen.paintTile
    for i = 1, run.n do
        local sx, sy = run.x[i] - wx, run.y[i] - wy
        if sx >= 0 and sy >= 0 and sx < W and sy < H then
            local tp = tileOf(i)
            if tp then paint(P, sx, sy, nil, tp, true) end
        end
    end
end
-- a cell whose water is k levels below the view (the sea seen from the beach level, a river from its bank): is water
-- drawn there this frame? Yes when the main viewport's liquid flag is set (the bed's lift copied it up) or DF drew
-- water at that index in lower_viewport[k-1]; when the lower viewport cannot be read (another size, missing), the scan's
-- word stands and it is drawn. Never gated by the main flag alone: with the lift off or fused, DF draws that water only
-- in the lower viewport, and the waves and streaks must still show over it.
local function liftedShown(lf, idx, k, lowers, W, H)
    if lf and lf[idx] ~= 0 then return true end
    local lv = lowerView(lowers, k, W, H)
    if not lv or not lv.lf then return true end
    return lv.lf[idx] ~= 0
end
_ENV.liftedShown = liftedShown
-- the waves, per frame: each cell's family frame by its own clock and phase. The scan put only sea cells and (the
-- mist) dry beach cells in the run; a beach cell is painted as it is (DF drew no water there to ask about). For the
-- sea the frame also asks DF's own buffers. A cell with water at the view level needs its liquid flag
-- this frame; a cell over the sea seen below needs liftedShown. If DF flags none of the view-level cells for ten frames
-- (not seen on the rig, but a buffer that is not filled would hide every wave), that check is off for the session and
-- status says so; it never touches the cells seen below. With the veil on (it blanks the flags) the flags are not read.
local function paintWaves(c, wx, wy, z, W, H)
    local run = AQ.waves
    local fr = AQ.wavesFrame or {}
    AQ.wavesFrame = fr
    fr.painted, fr.gated, fr.lifted = 0, 0, 0
    if not run or run.n == 0 or run.z ~= z then return end
    local now = dfhack.getTickCount()
    local tq = { crest = now // WAVE.MS.crest, surf = now // WAVE.MS.surf, mist = now // WAVE.MS.mist }
    local mv = df.global.gps.main_viewport
    local lfAll = (not c.veil) and mv.screentexpos_liquid_flag or nil
    local lf = (AQ.wavesGate ~= false) and lfAll or nil
    local lowers = {}
    local P = pen()
    local paint = dfhack.screen.paintTile
    local limit = W * H
    local painted, gated, inView, gatedHere, lifted = 0, 0, 0, 0, 0
    for i = 1, run.n do
        local sx, sy = run.x[i] - wx, run.y[i] - wy
        if sx >= 0 and sy >= 0 and sx < W and sy < H then
            local idx = sx * H + sy
            local k = run.lift[i] or 0
            local ok
            if k < 0 then ok = true                       -- the dry beach: DF's mist art over the sand
            elseif k > 0 then ok = (not lfAll) or idx >= limit or liftedShown(lfAll, idx, k, lowers, W, H)
            else
                inView = inView + 1
                ok = not (lf and idx < limit and lf[idx] == 0)
                if not ok then gatedHere = gatedHere + 1 end
            end
            if not ok then
                gated = gated + 1
            else
                local fam = run.fam[i]
                local h = fam[(tq[run.kind[i]] + run.ph[i]) % #fam + 1]
                local tp = fam.raw and h or texpos(h)
                if tp then
                    paint(P, sx, sy, nil, tp, true); painted = painted + 1
                    if k > 0 then lifted = lifted + 1 end
                end
            end
        end
    end
    if lf and gatedHere >= 8 and gatedHere == inView then
        fr.noFlag = (fr.noFlag or 0) + 1
        if fr.noFlag >= 10 then AQ.wavesGate = false end   -- ten frames with no water flagged under any view-level wave cell
    elseif inView > gatedHere then fr.noFlag = 0 end
    fr.painted, fr.gated, fr.lifted = painted, gated, lifted
end
_ENV.paintWaves = paintWaves
-- moving water, per frame. A cell with water at the view level needs DF's liquid flag set this frame; a cell whose
-- water is k levels below needs liftedShown (the lift's flag, or DF's own water in lower_viewport[k-1], or a lower
-- viewport that cannot be read): a river seen from its bank keeps its streaks with the bed's lift off or fused. The same
-- safety valve as the waves: ten frames with no flag under any of this level's cells turn the check off for them
-- (status says so); with the veil on (it blanks the flags) the flags are not read. streaks_layer `under` (experimental) writes the streak into background_two, between the bed and DF's water
-- sprite, where nothing else is (0 or our own), so the translucent water tints it; it falls back to `top` with the veil.
local function paintFlowFx(wx, wy, z, W, H, sOn, hOn, layer, veil)
    local run = AQ.flowfx
    local fr = AQ.flowFrame or {}
    AQ.flowFrame = fr
    fr.painted, fr.under, fr.gated = 0, 0, 0
    if not run or run.n == 0 or run.z ~= z then return end
    local now = dfhack.getTickCount()
    local tq = { streak = now // FLOWFX.MS.streak, shimmer = now // FLOWFX.MS.shimmer }
    local mv = df.global.gps.main_viewport
    local lf = (not veil) and mv.screentexpos_liquid_flag or nil
    local gateOff = AQ.flowGate == false
    local under = layer == 'under' and not veil
    local bg2 = under and mv.screentexpos_background_two or nil
    local own = AQ.flowOwn
    local P = pen()
    local paint = dfhack.screen.paintTile
    local limit = W * H
    local painted, nunder, gated, inView, gatedHere = 0, 0, 0, 0, 0
    local lowers = {}
    for i = 1, run.n do
        local kind = run.kind[i]
        if (kind == 'streak' and sOn) or (kind == 'shimmer' and hOn) then
            local sx, sy = run.x[i] - wx, run.y[i] - wy
            if sx >= 0 and sy >= 0 and sx < W and sy < H then
                local idx = sx * H + sy
                local k = run.lift[i] or 0
                local ok
                if k > 0 then ok = (not lf) or idx >= limit or liftedShown(lf, idx, k, lowers, W, H)
                else
                    inView = inView + 1
                    ok = (not lf) or gateOff or idx >= limit or lf[idx] ~= 0
                    if not ok then gatedHere = gatedHere + 1 end
                end
                if not ok then gated = gated + 1
                else
                    local fam = run.fam[i]
                    local tp = texpos(fam[(tq[kind] + run.ph[i]) % #fam + 1])
                    if tp then
                        if bg2 and kind == 'streak' then
                            local cur = bg2[idx]
                            if cur == 0 or own[cur] then bg2[idx] = tp; own[tp] = true; nunder = nunder + 1 end   -- luacheck: ignore 122
                        else
                            paint(P, sx, sy, nil, tp, true); painted = painted + 1
                        end
                    end
                end
            end
        end
    end
    if lf and not gateOff and inView >= 8 and gatedHere >= inView then
        fr.noFlag = (fr.noFlag or 0) + 1
        if fr.noFlag >= 10 then AQ.flowGate = false end
    elseif inView > gatedHere then fr.noFlag = 0 end
    fr.painted, fr.under, fr.gated = painted, nunder, gated
end
_ENV.paintFlowFx = paintFlowFx
-- the switches as they are now: the console, Panel and browser write the tool's cached config at once, so a frame reads
-- them there (no copy) and stops a layer the moment it is switched off, without waiting for the next scan
local function liveAq()
    local C = swCache()
    local a = C and C.cfg and C.cfg.aquarium
    return type(a) == 'table' and a or nil
end
function AquariumView:onRenderFrame(dc, rect) -- luacheck: ignore 212
    local c = self.c
    if not c then return end
    local live = liveAq()
    if live then
        if live.enabled == false then self.c = nil; dropRuns(); return end
        if live.waves == 'off' then AQ.waves = nil end
        if live.lens == false then AQ.lens = nil end
        if live.veil == false and c.veil then AQ.veil = nil end
        if live.bed == 'off' then AQ.bed, AQ.bedBuild = nil, nil end
        if live.streaks == false and live.shimmer == false then AQ.flowfx = nil end
    end
    local function on(k) local v = live and live[k]; if v == nil then return c[k] end; return v end
    local wx, wy, z, W, H
    do local mv = df.global.gps.main_viewport; W, H = mv.dim_x, mv.dim_y end
    wx, wy, z = df.global.window_x, df.global.window_y, df.global.window_z
    texposCache = {}
    -- the bed first: it needs the liquid flags the veil blanks, and the veil's water sprite (background_two) sits over it
    if c.bed ~= 'off' and AQ.bed and AQ.bed.on and not fuse('bed').tripped then
        local t0 = dfhack.getTickCount()
        local ok, err = pcall(paintBed, c, wx, wy, z, W, H)
        if not ok then trip('bed', 'paint error: ' .. tostring(err)) else frameDone('bed', dfhack.getTickCount() - t0, c) end
    end
    if c.veil and AQ.veil and not fuse('veil').tripped then
        local t0 = dfhack.getTickCount()
        local ok, err = pcall(paintVeil, c, wx, wy, z, W, H)
        if not ok then trip('veil', 'paint error: ' .. tostring(err)) else frameDone('veil', dfhack.getTickCount() - t0, c) end
    end
    -- moving water before the lens and the waves: one sprite per cell in the interface layer, the later paint wins, and a
    -- creature or a crest matters more than a streak
    if AQ.flowfx and AQ.flowfx.n > 0 and not fuse('flow').tripped then
        local t0 = dfhack.getTickCount()
        local ok, err = pcall(paintFlowFx, wx, wy, z, W, H, on('streaks'), on('shimmer'), on('streaks_layer'), on('veil'))
        if not ok then AQ.flowfx = nil; trip('flow', 'paint error: ' .. tostring(err)) else frameDone('flow', dfhack.getTickCount() - t0, c) end
    end
    local lens = AQ.lens
    if c.lens and lens and lens.z == z and (lens.n > 0 or #lens.brackets > 0) and not fuse('lens').tripped then
        local t0 = dfhack.getTickCount()
        local ok, err = pcall(function()
            paintCells(lens, wx, wy, W, H, function(i) return texpos(lens.h[i]) end)
            local P = pen()
            for _, b in ipairs(lens.brackets) do
                local sx, sy = b[1] - wx, b[2] - wy
                if sx >= 0 and sy >= 0 and sx < W and sy < H then
                    local tp = texpos(b[3]); if tp then dfhack.screen.paintTile(P, sx, sy, nil, tp, true) end
                end
            end
        end)
        if not ok then trip('lens', 'paint error: ' .. tostring(err)) else frameDone('lens', dfhack.getTickCount() - t0, c) end
    end
    local waves = AQ.waves
    if waves and waves.n > 0 and waves.z == z and not fuse('waves').tripped then
        local t0 = dfhack.getTickCount()
        local ok, err = pcall(paintWaves, c, wx, wy, z, W, H)
        if not ok then AQ.waves = nil; trip('waves', 'paint error: ' .. tostring(err)) else frameDone('waves', dfhack.getTickCount() - t0, c) end
    end
end

-- the legend panel
AquariumLegend = defclass(AquariumLegend, overlay.OverlayWidget)
AquariumLegend.ATTRS{
    desc = 'seasonal-wildlife Aquarium: what is swimming below the view, per species.',
    default_pos = { x = -3, y = 8 }, viewscreens = 'dwarfmode', default_enabled = true,
    frame = { w = 40, h = 5 }, frame_style = require('gui').FRAME_PANEL, frame_background = require('gui').CLEAR_PEN,
    frame_title = 'Aquarium', overlay_onupdate_max_freq_seconds = 0.5, version = 1,
}
function AquariumLegend:init()
    self.rows = {}
    self:addviews{ widgets.Label{ view_id = 'text', frame = { t = 0, l = 0 }, text = {} } }
    self.visible = function() return self.show and true or false end
end
function AquariumLegend:overlay_onupdate()
    self.show = false
    if not dfhack.isMapLoaded() or not dfhack.screen.inGraphicsMode() then return end
    local c = config()
    if not (c.enabled and c.lens and c.legend) or fuse('lens').tripped then return end
    local run = AQ.lens
    if not run or run.total == 0 then return end
    local rows = legendRows(c)
    local text = {}
    local nsp = 0
    for _ in pairs(run.species) do nsp = nsp + 1 end
    local schools = 0
    for _, r in ipairs(rows) do if r.tags ~= '' and not r.tags:find('PANIC', 1, true) then schools = schools + 1 end end
    text[#text + 1] = { text = ('Below: %d in %d species, to -%d'):format(run.total, nsp, c.depth), pen = COLOR_WHITE }
    text[#text + 1] = NEWLINE
    for _, r in ipairs(rows) do
        local rgb = c.color == 'kind' and (COLORS.kind[r.kind] or COLORS.kind.other) or COLORS.level[r.level] or COLORS.level.H
        local h = texture(('L|%s|%s|230|'):format(r.kind, c.color == 'kind' and r.kind or r.level), r.kind, rgb, 230, nil, true)
        local tp = h and dfhack.textures.getTexposByHandle(h)
        if tp then text[#text + 1] = { tile = tp } else text[#text + 1] = { text = '*', pen = LEVEL_PEN[r.level] or COLOR_WHITE } end
        local line = (' %-16s x%-3d %-7s %s'):format(r.name:sub(1, 16), r.n, r.depth, r.tags)
        text[#text + 1] = { text = line:sub(1, 36), pen = LEVEL_PEN[r.level] or COLOR_WHITE }
        text[#text + 1] = NEWLINE
    end
    if rows.more and rows.more > 0 then text[#text + 1] = { text = ('  and %d more species'):format(rows.more), pen = COLOR_GREY }; text[#text + 1] = NEWLINE end
    self.subviews.text:setText(text)
    local h = #rows + 2 + ((rows.more or 0) > 0 and 1 or 0) + 1
    if self.frame.h ~= h then self.frame.h = h; self:updateLayout() end
    self.show = true
end

OVERLAY_WIDGETS = { view = AquariumView, legend = AquariumLegend }

--========================================================================================
-- runtime verbs (the engine's `aquarium` verb calls these for install, restore, uninstall, status, probe, rearm)
--========================================================================================
local function gfx()
    local ok, m = pcall(reqscript, 'seasonal-wildlife-aquarium-gfx')
    if not ok then error('seasonal-wildlife-aquarium-gfx.lua is missing from the scripts folder: ' .. tostring(m), 0) end
    return m.GFX
end
local function modDir() return AQ_baseDir() .. 'mods/' .. 'seasonal_wildlife_aquarium' end
_ENV.modDir = modDir
local function readFile(p) local f = io.open(p, 'rb'); if not f then return nil end; local d = f:read('a'); f:close(); return d end
-- true (and the folder DF loaded it from) when the loaded world lists the mod; false when it does not; nil with no world
activeInWorld = function()
    if not dfhack.isWorldLoaded() then return nil end
    local ok, mods = pcall(function() return require('script-manager').get_active_mods() end)
    if not ok then return nil end
    for _, m in ipairs(mods) do
        if m.id == 'seasonal_wildlife_aquarium' then
            local p = m.path and tostring(m.path) or nil
            if p and not p:match('^/') and not p:match('^%a:[/\\]') then p = AQ_baseDir() .. p end
            return true, p
        end
    end
    return false
end
-- DF does not load a world's mods from mods/: at world creation it copies each one into
-- data/installed_mods/<id> (<numeric version>)/ and loads that copy ever after (DFHack's script-manager reads the active
-- mods' src_dir there). A preset written only to mods/ never reaches a world made with the mod, so install, restore and
-- custom alphas refresh every installed copy of THIS mod as well (found 2 Oct 2026 on the rig's region10: the copy was
-- made at 14:24, four minutes after the mod).
local MOD_COPY_PREFIX = 'seasonal_wildlife_aquarium ('
local function installedCopies()
    local root = AQ_baseDir() .. 'data/installed_mods/'
    local ok, names = pcall(dfhack.filesystem.listdir, root)
    local out = {}
    if not ok or type(names) ~= 'table' then return out end
    for _, n in ipairs(names) do
        n = tostring(n):gsub('[/\\]$', '')
        if n:sub(1, #MOD_COPY_PREFIX) == MOD_COPY_PREFIX then
            local info = readFile(root .. n .. '/info.txt')
            if info and info:find('[ID:seasonal_wildlife_aquarium]', 1, true) then out[#out + 1] = root .. n end
        end
    end
    table.sort(out)
    return out
end
_ENV.installedCopies = installedCopies
_ENV.activeInWorld = activeInWorld
-- the bed baked into the world's mod (round 5): its loaded copy's stamp says bed_bake=sand. Cached like `auto`.
worldBake = function()
    local now = dfhack.getTickCount()
    local a = AQ.bedBake
    if a and now - a.at <= LIMIT.bed_act_ms then return a.v end
    local v = false
    local ok, act, path = pcall(activeInWorld)
    if ok and act and path then
        local okG, G = pcall(gfx)
        local t = okG and readFile(G.join(path, G.STAMP))
        local st = t and G.parseStamp(t)
        v = st and st.bed_bake == 'sand' or false
    end
    AQ.bedBake = { at = now, v = v, path = v and path or nil }
    return v
end
_ENV.worldBake = worldBake
local function stamp()
    local G = gfx()
    local text = readFile(G.join(modDir(), G.STAMP))
    return text and G.parseStamp(text) or nil
end

function install(presetName, alphas)
    local G = gfx()
    local out = modDir()
    local info = readFile(G.join(out, 'info.txt'))
    if info and not info:find('[ID:' .. G.MOD_ID .. ']', 1, true) then
        return false, ('%s holds another mod (its info.txt has a different ID); nothing written'):format(out)
    end
    local src = AQ_installDir() .. 'data/vanilla/vanilla_environment/graphics/images'
    local fs = {
        read = readFile,
        write = function(p, d) local f = io.open(p, 'wb'); if not f then return false end; f:write(d); f:close(); return true end,
        mkdir = function(p) return dfhack.filesystem.mkdir_recursive(p) end,
        list = function(p) local ok, t = pcall(dfhack.filesystem.listdir, p); return ok and t or {} end,
    }
    local ok, res = pcall(G.build, { fs = fs, src = src, out = out, preset = presetName, alphas = alphas, generator = 'lua (in game)',
                                     clock = function() return dfhack.getTickCount() / 1000 end })
    if not ok then return false, 'install failed: ' .. tostring(res) end
    local a = table.concat(res.preset.alpha, ' ')
    local lines = { ('Aquarium mod written: %s'):format(out),
                    ('  preset %s (alpha %s for tile water level 7..1; flows x%.2f; mist x%.2f), bed baked %s, %d files in %.1f s')
                        :format(res.preset.name, a, res.preset.flows, res.preset.mist, tostring(res.bake), #res.files, res.seconds) }
    -- the copies DF loads for worlds already made with the mod (data/installed_mods): the same files, byte for byte
    for _, copy in ipairs(installedCopies()) do
        local n, bad = 0, nil
        for _, f in ipairs(G.files()) do
            local data = readFile(G.join(out, f))
            local dst = G.join(copy, f)
            fs.mkdir((dst:gsub('[/\\][^/\\]*$', '')))
            if data and fs.write(dst, data) then n = n + 1 else bad = bad or f end
        end
        lines[#lines + 1] = bad and ('  WARNING: the copy worlds load, %s, could not take %s: worlds made with the mod keep their old look'):format(copy, bad)
            or ('  refreshed the copy worlds made with the mod load: %s (%d files)'):format(copy, n)
    end
    local act = activeInWorld()
    if act then
        lines[#lines + 1] = '  This world already uses the mod: save, quit to the title and load it again to see the new look.'
    else
        lines[#lines + 1] = '  NEW world: Create new world -> Mods -> tick "Seasonal Wildlife - Aquarium".'
        lines[#lines + 1] = '  A world made without it cannot add it (DF fixes a world\'s mods at creation). The lens, legend'
        lines[#lines + 1] = '  and waves need no mod; `seasonal-wildlife aquarium veil on` is the experimental stand-in.'
    end
    return true, table.concat(lines, '\n')
end

function uninstall(force)
    local G = gfx()
    if activeInWorld() and not force then
        return false, 'this world uses the Aquarium mod: removing it would stop the world loading. Use `aquarium restore` (vanilla look, mod kept), or `aquarium uninstall force`.'
    end
    local out = modDir()
    if not readFile(G.join(out, 'info.txt')) then return false, 'nothing installed at ' .. out end
    local n = 0
    for _, f in ipairs(G.files()) do if os.remove(G.join(out, f)) then n = n + 1 end end
    for _, d in ipairs({ 'graphics/images', 'graphics', '' }) do pcall(dfhack.filesystem.rmdir, d == '' and out or G.join(out, d)) end
    return true, ('removed %d files from %s'):format(n, out)
end

function statusLines()
    local c = config()
    local out = {}
    local gm = dfhack.screen.inGraphicsMode()
    local lower = '?'
    pcall(function() lower = tostring(df.global.d_init.display.number_of_lower_elevations_shown) end)
    out[#out + 1] = ('aquarium: %s; graphics mode %s; DF shows %s lower level(s) (Settings: lower elevations shown)')
        :format(c.enabled and 'on' or 'OFF', gm and 'yes' or 'NO (the overlays paint only in graphics mode)', lower)
    if pluginOn() then
        out[#out + 1] = '  STANDING DOWN: the native aquarium plugin is enabled and draws the water (`disable aquarium` hands it back)'
    end
    local function layerLine(name, on, extra)
        local f = fuse(name)
        local state = f.tripped and ('STOPPED: ' .. tostring(f.why)) or (on == 'idle' and 'idle' or (on and 'on' or 'off'))
        if not f.tripped and (f.degrade or 0) > 0 then
            state = state .. (' (DEGRADED step %d: %s; `aquarium rearm` restores)'):format(f.degrade, tostring(f.degradeWhy))
        end
        out[#out + 1] = ('  %-6s %s%s'):format(name, state, extra or '')
        if f.frames > 0 or f.scans > 0 then
            out[#out + 1] = ('         frames %d, paint avg %.2f ms, worst %d ms; scans %d, last %d ms (worst %d), %d marks; %s')
                :format(f.frames, f.ema, f.worst, f.scans, f.scanMs, f.scanWorst, f.marks, f.note)
        end
    end
    layerLine('lens', c.lens, ('  depth %d, fade %.2f, colour %s, schools %s, legend %s (%d rows)'):format(c.depth, c.fade, c.color,
        c.schools and 'on' or 'off', c.legend and 'on' or 'off', c.legend_rows))
    local okW, onW, whyW = pcall(wavesOn, c)
    local wf = AQ.wavesFrame or {}
    layerLine('waves', c.waves ~= 'off' and (okW and not onW and 'idle' or true), ('  %s; surf %s, shore mist %s; last frame painted %s cells (%s over the sea seen below; %s skipped: DF drew no water there)%s')
        :format(okW and whyW or '?', c.surf and 'on' or 'off', c.foam and 'on' or 'off', tostring(wf.painted or '-'), tostring(wf.lifted or '-'), tostring(wf.gated or '-'),
                AQ.wavesGate == false and '; the water-flag check is OFF (DF flagged no water under any wave cell)' or ''))
    layerLine('veil', c.veil, '  (experimental run-time translucency)')
    local okB, onB, whyB = pcall(bedOn, c)
    local fr = AQ.bedFrame or {}
    local okK, bakedW = pcall(worldBake)
    if okK and bakedW then
        layerLine('bed', c.bed ~= 'off' and (okB and not onB and 'idle' or true),
            ('  %s; bed: baked in the mod (sand under standing water, mud under rivers and brooks; the script paints no bed); lift %s: last frame %s cells lifted of %s planned (%s/%s columns built, %s buffer reads), %s left as DF kept them, %s with no water drawn below; open-space backgrounds learned %s; views %s; creatures below %s, watched %s, shown %s, not drawn by DF below %s; items %s, layers copied %s')
                :format(okB and whyB or '?', c.bed_lift and 'on' or 'off', tostring(fr.lifted or '-'), tostring(fr.liftN or '-'),
                        tostring(fr.planCols or '-'), tostring(fr.planW or '-'), tostring(fr.built or '-'), tostring(fr.kept or '-'),
                        tostring(fr.dry or '-'), tostring(fr.open or '-'), tostring(fr.views or '-'), c.bed_below == false and 'off' or 'on',
                        tostring(fr.belowWatched or '-'), tostring(fr.belowShown or '-'), tostring(fr.belowNotDrawn or '-'),
                        tostring(fr.marked or '-'), tostring(fr.copied or '-')))
    else
    layerLine('bed', c.bed ~= 'off' and (okB and not onB and 'idle' or true),
        ('  %s; to %d levels down, tint %.2f, absorb %.2f, river beds %s, lift %s; textures %d/%d%s; last frame wrote %s, left %s (DF drew something), fill texpos %s; lifted %s (no lower view %s), swimmers copied %s%s')
            :format(okB and whyB or ('?' .. tostring(onB)), c.bed_depth, c.bed_tint, c.bed_absorb, c.bed_river, c.bed_lift and 'on' or 'off',
                    AQ.bedTexN or 0, LIMIT.bed_tex, AQ.bedTexN and AQ.bedTexN >= LIMIT.bed_tex and ' (CAP)' or '', tostring(fr.wrote or '-'),
                    tostring(fr.foreign or '-'), tostring(fr.fill or 'not seen'), tostring(fr.lifted or '-'), tostring(fr.noLower or '-'),
                    tostring(fr.copied or '-'), AQ.bedSheetErr and ('; sheet error ' .. AQ.bedSheetErr) or '')
            .. ('; lift plan %s cells (%s thinned), %s left as DF kept them, %s with no water drawn below, %s item cells watched; floor %s; creatures below %s, watched cells %s, shown %s, not drawn by DF below %s')
                :format(tostring(fr.liftN or '-'), tostring(fr.thinned or '-'), tostring(fr.kept or '-'), tostring(fr.dry or '-'), tostring(fr.marked or '-'),
                        c.bed_material == 'auto' and 'auto (the ground)' or 'sand under salt water, mud under fresh', c.bed_below == false and 'off' or 'on',
                        tostring(fr.belowWatched or '-'), tostring(fr.belowShown or '-'), tostring(fr.belowNotDrawn or '-')))
    end
    local ff = AQ.flowFrame or {}
    layerLine('flow', (c.streaks or c.shimmer) and true or false, ('  river streaks %s (%s), shimmer %s (shallows to %d levels); last frame painted %s, under the water %s, %s skipped (no water flag)%s')
        :format(c.streaks and 'on' or 'off', c.streaks_layer, c.shimmer and 'on' or 'off', c.shimmer_depth, tostring(ff.painted or '-'),
                tostring(ff.under or '-'), tostring(ff.gated or '-'), AQ.flowGate == false and '; the water-flag check is OFF (DF flagged none of these cells)' or ''))
    out[#out + 1] = ('  budget %s ms a frame, fuse after %d frames over, %d marks at most, %d scans a second'):format(c.budget_ms, c.trip_frames, c.marks, c.scan_hz)
    local okS, st = pcall(stamp)
    local act, actPath = activeInWorld()
    if okS and st then
        out[#out + 1] = ('  mod: installed at %s, preset %s (alpha %s), bed baked %s, by %s; %s'):format(modDir(), tostring(st.preset), tostring(st.alpha),
            tostring(st.bed_bake or 'off (built before round 5)'), tostring(st.generator), act == nil and 'no world loaded' or (act and 'ACTIVE in this world' or 'not in this world\'s mod list (new worlds only)'))
        if act and actPath then   -- what the loaded world actually drew its pages from (its installed copy)
            local okG, G = pcall(gfx)
            local cs = okG and readFile(G.join(actPath, G.STAMP))
            local cp = cs and G.parseStamp(cs) or {}
            out[#out + 1] = ('  this world loaded %s: preset %s (alpha %s), bed baked %s%s'):format(actPath, tostring(cp.preset), tostring(cp.alpha),
                tostring(cp.bed_bake or 'off'),
                (cp.alpha and st.alpha and cp.alpha ~= st.alpha) and '; DIFFERS from mods/: run install again, then reload' or '')
        end
    else
        out[#out + 1] = ('  mod: not installed (%s); `seasonal-wildlife aquarium install` builds it from your vanilla sheets; preset to use: %s')
            :format(modDir(), c.preset)
    end
    return out
end

function probe()
    local out = {}
    if not dfhack.isMapLoaded() then return { 'no map loaded' } end
    local ev = df.global.world.event
    local FT = df.flow_type
    local counts = { [FT.OceanWave] = 0, [FT.SeaFoam] = 0, [FT.Mist] = 0 }
    local blocks = 0
    for _, blk in ipairs(df.global.world.map.map_blocks) do
        blocks = blocks + 1
        for _, fl in ipairs(blk.flows) do if counts[fl.type] and fl.density > 0 then counts[fl.type] = counts[fl.type] + 1 end end
    end
    local zs = {}
    for _, w in ipairs(ev.ocean_waves) do zs[w.z] = (zs[w.z] or 0) + 1 end
    local zl = {}
    for zz, n in pairs(zs) do zl[#zl + 1] = ('z%d:%d'):format(zz, n) end
    table.sort(zl)
    local coastN = 0
    local ok = pcall(function() for _, m in ipairs(ev.ocean_wave_makers) do coastN = coastN + #m.coastline.x end end)
    out[#out + 1] = ('waves: %d wave makers (%s coastline points), %d wave fronts [%s]; flows on the map (%d blocks): OceanWave %d, SeaFoam %d, waterfall Mist %d')
        :format(#ev.ocean_wave_makers, ok and tostring(coastN) or '?', #ev.ocean_waves, table.concat(zl, ' '), blocks,
                counts[FT.OceanWave], counts[FT.SeaFoam], counts[FT.Mist])
    local c, cfg = config()
    -- the waves on the view level: one scan now (its note: fronts, flows on water and on land, cells by kind)
    local okW, wr = pcall(scanWaves, c)
    out[#out + 1] = okW and ('waves at z %s: %s'):format(tostring(wr.z or '-'), fuse('waves').note) or ('waves scan failed: ' .. tostring(wr))
    local okF, frr = pcall(scanFlowFx, c)
    out[#out + 1] = okF and ('moving water at z %s: %s'):format(tostring(frr.z or '-'), fuse('flow').note) or ('moving-water scan failed: ' .. tostring(frr))
    local saveLens = AQ.lens
    local okL, run = pcall(scanLens, c, cfg)
    if okL then
        out[#out + 1] = ('lens at z %d, depth %d: %d creatures below in view, %d cells marked, %d school brackets%s')
            :format(run.z, c.depth, run.total, run.n, #run.brackets, run.stopped and (' (stopped: ' .. run.stopped .. ')') or '')
        for _, r in ipairs(legendRows(c)) do
            out[#out + 1] = ('  %-24s x%-3d %-8s %-22s %s'):format(r.name, r.n, r.depth, r.tags, r.origin)
        end
    else
        out[#out + 1] = 'lens scan failed: ' .. tostring(run)
        AQ.lens = saveLens
    end
    return out
end

-- the engine's `aquarium` verb hands the runtime words here; returns lines to print
function verb(words, c)
    local w = words[1]
    if w == 'install' or w == 'restore' then
        local name = w == 'restore' and 'vanilla' or (words[2] or (c and c.preset) or 'aquarium')
        local ok, msg = install(name, c and c.alpha)
        return { msg }, ok
    elseif w == 'uninstall' then
        local ok, msg = uninstall(words[2] == 'force')
        return { msg }, ok
    elseif w == 'rearm' then
        return { ('re-armed %d stopped aquarium layer(s)'):format(rearm()) }, true
    elseif w == 'probe' then
        return probe(), true
    end
    return statusLines(), true
end

if dfhack_flags and dfhack_flags.module then return end

local args = { ... }
local lines = verb(args, (config()))
for _, l in ipairs(lines) do print(l) end
