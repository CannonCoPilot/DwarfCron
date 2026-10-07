--@ module = true
--[====[
gui/seasonal-wildlife
=====================

Tags: fort | gameplay | animals | interface

The Seasonal Wildlife window: choose which wild animals may come to your fort, in which seasons, on
every layer (the surface, its rivers, lakes and sea, and the caverns), and watch what is on the map.
Every species is either active, with one or more seasons, or inactive and never appears.

Tabs: Overview (what the map holds now) - Panel (every switch, the background jobs, all on / all off) -
Roster (each species: active, seasons, targets) - Seasons - Food web - Live (groups on the map) -
Layers (per-layer settings) - Vermin - Ledger (every change the tool made, with undo).

Keys that work on every tab: Alt+L cycles the layer shown; Alt+P opens the Panel; Esc closes.
On the Roster: Enter makes a species active or inactive; S U A W add or remove a season (the last one
stays: make the species inactive instead); E cycles its seasons; i opens its detail page; Alt+R resets
(the roster, or everything) after asking; Alt+F fills the category shown to a number.

Usage::

    gui/seasonal-wildlife

The console verbs are `seasonal-wildlife` (`help seasonal-wildlife`).
]====]
-- gui/seasonal-wildlife.lua — the Seasonal Wildlife window.
-- v5.9.8: the window's code lives here; the engine (seasonal-wildlife.lua) exports what it reads.
-- Console verb `seasonal-wildlife gui` and this script's own command both open it.
--
-- ⚠️ Bug 11 (2026-09-16): an earlier launcher called show_gui() at the top level with no module
-- guard. DFHack's script-manager reqscripts EVERY module script on world load to build the
-- enabled map and find overlay widgets, so the scan itself opened the window. The guard at the
-- bottom is what keeps that from recurring; nothing above it may open a window.
local gui        = require('gui')
local widgets    = require('gui.widgets')
local dialogs    = require('gui.dialogs')
local sw         = reqscript('seasonal-wildlife')
local LEDGER     = sw.LEDGER
local VERMIN     = sw.VERMIN
local PATTERN    = sw.PATTERN
local loadGroups = sw.loadGroups
local whyFor = sw.whyFor
-- v5.10.8: the Roster's why column has 17 cells at the window's right edge, and the shortest dated
-- reason ('you: allowed @ y2 Spring 23') is 27 -- the rig showed 'you: allowed @ y2' with the date
-- cut off. The Roster carries the compact form, who and when ('you Sp23', 'fill Su4', 'matrix Sp23');
-- the species detail page (i) shows the full reason.
local SEASON_SHORT = { Spring='Sp', Summer='Su', Autumn='Au', Winter='Wi' }
local WHY_SHORT = { ['default: in embark']='default: embark', ['default: apex or night creature']='default: apex',
                    ['not on this embark']='not on embark', ['set before v5.10.5']='before v5.10.5' }
local function whyShort(w)
    local who, season, day = w:match('^(.-)%s+@%s+y%d+%s+(%a+)%s+(%d+)$')
    if who then return ('%s %s%s'):format(who:match('^([^:%s]+)') or who, SEASON_SHORT[season] or season:sub(1, 2), day) end
    if WHY_SHORT[w] then return WHY_SHORT[w] end
    local cls = w:match('^class (%S+) %(opt%-in%)$')
    if cls then return 'class '..cls end
    return w
end
local speciesDetail = sw.speciesDetail
local absTick    = sw.absTick
local TICKS_PER_DAY, TICKS_PER_YEAR = sw.TICKS_PER_DAY, sw.TICKS_PER_YEAR
local setAssign  = sw.setAssign
-- the engine surface, aliased so the window's code reads as it did when the two shared a file
local CATEGORIES      = sw.CATEGORIES
local CAVE            = sw.CAVE
local CAVERN          = sw.CAVERN
local FUSE            = sw.FUSE
local QUOTA           = sw.QUOTA
local SEASON          = sw.SEASON
local SEASON_PEN      = sw.SEASON_PEN
local STOCK           = sw.STOCK
local WILD            = sw.WILD
local abbrevBiome     = sw.abbrevBiome
local addNewSpecies   = sw.addNewSpecies
local announce        = sw.announce
local applyLive       = sw.applyLive
local assignFromMatrix= sw.assignFromMatrix
local buildPool       = sw.buildPool
local captureDefault  = sw.captureDefault
local coAlignSeasons  = sw.coAlignSeasons
local countsFor       = sw.countsFor
local cycleSeason     = sw.cycleSeason
local disableGroups   = sw.disableGroups
local disableSched    = sw.disableSched
local ecologyStatus   = sw.ecologyStatus
local enableGroups    = sw.enableGroups
local enableSched     = sw.enableSched
local enabledLayers   = sw.enabledLayers
local fillCategory    = sw.fillCategory
local fillPartners    = sw.fillPartners
local getEmbarkRegions= sw.getEmbarkRegions
local groupsStatus    = sw.groupsStatus
local inSeason        = sw.inSeason
local isAllowed       = sw.isAllowed
local keyFor          = sw.keyFor
local loadConfig      = sw.loadConfig
local managedPop      = sw.managedPop
local matchPredators  = sw.matchPredators
local matchPrey       = sw.matchPrey
local saveConfig      = sw.saveConfig
local toggleSeason    = sw.toggleSeason
local RESERVE         = sw.RESERVE   -- v6.5.0
local ODDS            = sw.ODDS
local ENGINE          = sw.ENGINE
local seasonLabel     = sw.seasonLabel
local ecoLivePairs    = sw.ecoLivePairs
local saveGroups      = sw.saveGroups
local holdGroup       = sw.holdGroup
local dismissGroup    = sw.dismissGroup
local cohesionLabel   = sw.cohesionLabel
local cavernsFound    = sw.cavernsFound
local applyPreset     = sw.applyPreset
local presetName      = sw.presetName
local WATER           = sw.WATER
local UNDO            = sw.UNDO
local IRRUPT          = sw.IRRUPT
local ROSTER          = sw.ROSTER      -- v6.3.0
local PANEL           = sw.PANEL
local LAYER_SET       = sw.LAYER_SET
-- v7.1 (ui stream; R52, R5, R7): the Panel renders every control from the shared registry (seasonal-wildlife-controls,
-- the web stream's module). Its set path checks the value, runs the tool's own console verb and reads the value back,
-- so the window, the web page and the console change the game the same way. W: the columns the window's text keeps to
-- (86; a wider window shows the same lines), LW: the Panel's section list.
local PNL = { W = 86, LW = 19 }
do
    local ok, m = pcall(reqscript, 'seasonal-wildlife-controls')
    if ok and type(m) == 'table' and m.set then PNL.ctl = m else PNL.err = tostring(m) end
end


local function fmtStock(n)   -- v6.5.0: 5,191 -> '5.2k', 935,388 -> '935k'
    if n >= 1e6 then return ('%.1fM'):format(n / 1e6) elseif n >= 1e4 then return ('%dk'):format(n // 1000)
    elseif n >= 1e3 then return ('%.1fk'):format(n / 1e3) end
    return tostring(math.floor(n))
end
local CAT_ICON = { predator='!', prey='v', bird='^', vermin='.', apex='*', other='-' }

-- The creature's own sprite, as a texpos the Label widget can paint in place of a
-- glyph. Verified live on 53.15 (2026-09-16): the icon sheet
-- (creature_texture_sheet_icon_texpos) is all zeros for ordinary animals -- modern DF
-- draws them through graphics_layer_set[].graphics_layer[].texpos, and a few
-- (toad) only carry creature_small_texpos. So walk those in turn and take the first
-- positive texpos. A raw without graphics at all (elk on this install, or text mode)
-- simply gets no icon; every read is guarded.
local spriteCache = {}
local function firstPositive(v, depth)
    depth = depth or 0
    if type(v) == 'number' then return v > 0 and v or nil end
    if type(v) ~= 'userdata' or depth > 5 then return nil end
    local ok, n = pcall(function() return #v end)
    if not ok then return nil end
    for i = 0, n - 1 do
        local ok2, item = pcall(function() return v[i] end)
        if ok2 then local r = firstPositive(item, depth + 1); if r then return r end end
    end
    return nil
end
local function spriteOf(idx)
    if spriteCache[idx] ~= nil then return spriteCache[idx] or nil end
    local tp = false
    if dfhack.screen.inGraphicsMode() then
        local craw = df.creature_raw.find(idx)
        local g = craw and craw.graphics
        if g then
            local ok, v = pcall(function()
                return firstPositive(g.creature_texture_sheet_icon_texpos)
                    or (#g.graphics_layer_set > 0 and #g.graphics_layer_set[0].graphics_layer > 0
                        and firstPositive(g.graphics_layer_set[0].graphics_layer[0].texpos))
                    or firstPositive(g.creature_texture_texpos)
                    or firstPositive(g.creature_small_texpos)
            end)
            if ok and v then tp = v end
        end
    end
    spriteCache[idx] = tp
    return tp or nil
end
local function iconToken(e)
    local tp = spriteOf(e.idx)
    if tp then return { tile=tp, text=' ', width=1 } end
    return { text=CAT_ICON[e.cat] or '?', width=1 }
end
-- One centred row of creatures for the pyramid. Returns a TOKEN LIST rather than a
-- string, because a creature's sprite is a token carrying `tile=` and a concatenated
-- string can only ever hold the fallback glyph -- which is why the pyramid was still
-- drawing category glyphs while the roster rows had the real animals.
local function iconRow(entries, width, pen)
    local toks, vis = {}, 0
    for i, e in ipairs(entries) do
        if i > 1 then toks[#toks+1] = { text='   ' }; vis = vis + 3 end
        local ic = iconToken(e)
        toks[#toks+1] = ic; vis = vis + (ic.width or 1)
        toks[#toks+1] = { text=' '..e.token, pen=pen }; vis = vis + #e.token + 1
    end
    local pad = math.max(0, math.floor((width - vis) / 2))
    if pad > 0 then table.insert(toks, 1, { text=(' '):rep(pad) }) end
    return toks
end

local TARGET_CATS = { 'prey', 'predator', 'vermin' }   -- v6.4.0: birds are predators or prey that fly
-- v6.3.0 (W1, alpha 1 step 3.3): 0 = not set; F leaves a category alone until its target is set, and the
-- targets are kept per layer in the config (they were window-only and one set spanned every layer)
local TARGET_DEFAULT = { prey=0, predator=0, vermin=0 }
local TARGET_OPTS = {}
for i = 0, 8 do TARGET_OPTS[#TARGET_OPTS+1] = { label=tostring(i), value=i } end
local Win = defclass(Win, widgets.Window)
Win.ATTRS{ frame_title='Seasonal Wildlife', frame={ w=90, h=34 }, resizable=true, resize_min={ w=72, h=26 } }   -- v6.1.1: 90 so the eight tabs fit one line (at 86 the eighth wrapped under the pages)

-- v6.2.0: the layer selector on every tab. Alt+L cycles all / land / water / cavern; the window's title
-- names it, with the reason when that layer is off or dormant; every tab's rows follow it (the Overview
-- keeps all layers). The reason lives in the title because DFHack's TabBar has no room for a fourth label.
local LAYER_CYCLE = { 'all', 'land', 'water', 'cavern', 'deep' }   -- v6.5.0: the deep layer (D7)
function Win:layerOk(l) return self.layer == 'all' or (l or 'land') == self.layer end
function Win:layerTitle()
    local l = self.layer
    if l == 'all' then return 'Seasonal Wildlife . All layers (Alt+L)' end
    local why = ''
    if not self.cfg.layers[l] then why = ' (layer off)'
    elseif l == 'water' then
        local st = WATER.status(self.cfg)
        local d = st:match('dormant %-%- ([^(]+)')
        if d then why = ' (dormant: ' .. d:gsub('%s+$', '') .. ')' end
    elseif l == 'deep' then
        why = ' (magma sea, by frequency)'
    elseif l == 'cavern' then
        local f, n = cavernsFound(), 0
        for _, v in pairs(f) do if v then n = n + 1 end end
        why = (' (%d found)'):format(n)
    end
    return ('Seasonal Wildlife . %s%s (Alt+L)'):format(l:sub(1, 1):upper() .. l:sub(2), why)
end
-- v7.1 (fixes2): the Ledger's K filter offers every kind the engine writes (LEDGER.KINDS: panic, lead, bodies, extinct,
-- adopt, call, size, eco were missing, and a roster build is 'build'); an older engine gives the v7.0 list
local function ledgerKindOptions()
    local kinds = LEDGER.KINDS or { 'edit', 'season', 'wave', 'arrive', 'coupling', 'ecology', 'hold', 'dismiss', 'sweep', 'place',
                                    'cavern', 'fuse', 'build', 'undo', 'irruption' }
    local opts = { { label='all', value='all' } }
    for _, k in ipairs(kinds) do opts[#opts+1] = { label=k, value=k } end
    return opts
end
-- v6.6.0 (W11, alpha 1: "every question in this trial answerable from inside the window"): Alt+H on any tab.
-- The words are the same on every layer and in the guide and the ledger.
local HELP = {
    Words = {
        'active / inactive  whether a species may arrive on this map at all. An active species has one or more seasons;',
        '                   the only way to keep one away is to make it inactive.',
        'seasons            when an active species may arrive. Activating gives exactly one, from its climate.',
        'stock              how many remain in the region to arrive; each arrival takes one, each departure gives one back.',
        '                   It does not change how often a species is chosen: that is its odds.',
        'odds               how likely it is chosen when its layer gets a wave, shown as a share of the layer.',
        'group size         how many arrive together (the raw\'s range unless you set one; DF may add one).',
        'groups at once     how many wild groups a layer holds at once.   ceiling  the most wild animals of a layer at once.',
        'gap, pattern       days between waves; steady, burst, trickle, dawn or follow.',
        'cohesion           a group keeps behind a leader: herd, pack, flock or school.',
        'coupling           a prey arrival calls its predators next, on its own layer.',
        'ecology, nudge     predators and prey related in DF\'s own table; a far predator moved nearer, within its habitat.',
        'hold, send off, call  keep a group longer; make it leave now; ask for a wave of one species.',
        'seasonal rotation  at each season change the season\'s roster takes effect; out-of-season species are held daily.',
        'Add invasive       bring in a species the embark\'s regions do not have.',
        'agitated           DF\'s word for wildlife that attacks what it meets: an irruption does it to a cavern group.',
        'special creatures  demons, megabeasts, titans, forgotten beasts, night creatures, mythic: DF\'s own, not managed.',
    },
    -- v7.1 (fixes2): the words v7.1 added (USAGE.md's word table and the v7.1 sections say the same)
    Words71 = {
        'group cap          (was groups at once) the groups a layer, each water body or each cavern holds at once.',
        'release clock      (was gap) when the next group is let in. It learns how long groups stay and aims at a target',
        '                   just under the cap: faster while below it, paused at it. Layers tab and Live show each clock.',
        'leader, panic      a group follows its largest adult male. If he dies or leaves, the group panics: it scatters',
        '                   for a couple of days (panic_days, 2), then stays unled.',
        'apex, presence     the top predator of a roster layer. The tool places apex groups from stock toward a presence',
        '                   target, the share of each season with one on the map (land 25%, water 20%, caverns 70%).',
        'pyramid            the herbivore / carnivore / apex shares (H/C/A) a roster layer or water body is steered toward.',
        'irruption          a cavern\'s surge, standing in for DF\'s disabled cavern invasions. Dwarves in and near a',
        '                   cavern raise its pressure; past the threshold the phases run quiet, STIRRING (a warning),',
        '                   IRRUPTING (waves of its own dwellers), then cooldown.',
        'irruption tokens   behaviours a share of each wave carries: crazed, rage, thief, sneak, wander, meander, linger,',
        '                   mischief, nofear, ambush (trance is off). Panel > Irruptions sets each one and its share.',
        'spill              a water body with fewer than 3 species drawable this season borrows the season for suitable',
        '                   water species; given back at the season change, on disable and on `water spill off`.',
        'column depth       how many water tiles are stacked in one column (a 4-level sea has columns of depth 4).',
        'tile water level   how full one tile is, 1-7 (DF\'s flow); a tile counts as water at 4/7. Not column depth.',
        'curious thief      a curious beast (bear, raccoon, monkey...) that steals. It steals first; when DF sends it',
        '                   off, the tool keeps that one animal on as wildlife and drops the loot where it stands.',
        'foraging           each day a few wild vermin eaters walk to real vermin their gobble tokens match, and eat.',
        'scavenging         remains are found after a delay that falls with their size, then eaten at a natural pace.',
    },
    Overview = { 'What the map holds now on each layer, groups against their limits, when each gate reopens, who is in season',
                 'and who arrives or leaves at the next boundary, and the ledger\'s last lines. R refreshes. A stopped job shows here.' },
    Panel = { 'Every control the tool has (the registry the web page and console share), by section: S and Shift+S',
              'or a click pick the section, Alt+S finds a control by words. Each section opens with its readouts.',
              'Enter: a switch flips, a choice moves on, a number asks; Left/Right or - + step (Shift: ten steps);',
              'D puts the default back. Every set runs the console verb and reads the value back (bottom lines).',
              'Switches & jobs: the jobs, their times and fuses; Enter on a tripped job re-arms. A: all on. X: all off',
              '(every job stops, every raw the tool wrote is put back). Irruptions: each cavern\'s pressure and phase,',
              'its waves and tokens, and every token, share and message as a control. Limits: the group cap per layer.' },
    Roster = { 'One row per species. ROLE predator/prey/vermin; SIZE small/medium/large by adult volume; HAB land, fly, wbird,',
               'semi, aqua; STOCK its reserve; ODDS its share of its layer. Enter: active/inactive. S U A W add or remove a season',
               '(the last stays). E cycles seasons. i: the species page (call, group size, odds, stock, habitat and role). Ctrl+W',
               'stock, Alt+O odds. M the climate matrix, O co-align, F Y D fills: each asks first. Alt+R resets, Alt+F fills a category.' },
    Seasons = { 'Every active species under its level across the four seasons: + arrives, - leaves after, X stays. Select a row;',
                'S U A W edit its seasons, as on the Roster.' },
    ['Food web'] = { 'Who eats whom among the active species: G cycles pyramid, graph, by season, by layer; N the season.',
                     'A pair is kept only where the habitats meet: a lion takes no shark, an eagle no sea fish.' },
    Live = { 'Every wild animal on the map by where it came from, the tracked groups (select one: Enter centres, F follows,',
             'Q holds, X sends off), W sends off the gated land groups so the next wave comes, P coupling, K pack size.' },
    Layers = { 'The same controls on every layer: land and caverns drawn by DF, water by the tool, the deep layer by frequency.',
               'L picks the column the keys act on. C the group cap (one fixed cap on every layer, or auto: the map-size',
               'formula), Q ceiling, D gap, T pattern, O the layer on or off, I irruptions (details on the Panel).' },
    Vermin = { 'Vermin by family: Enter makes the family (or an opened species) active or inactive; S U A W seasons; E opens',
               'a family to its species; Shift+W stock; D the family defaults. Vermin are not units: no groups, no ecology.' },
    Ledger = { 'Every write the tool made and why, newest last. K filters by kind, L by layer; Z undoes the last edit (fifty deep).' },
}
-- v6.3.0: the tabs by name, so adding the Panel did not renumber every refresh
local TABS = { { 'Overview', 'refreshOverview' }, { 'Panel', 'refreshPanel' }, { 'Roster', 'refresh' }, { 'Seasons', 'refreshSeasons' },
               { 'Food web', 'refreshWeb' }, { 'Live', 'refreshLive' }, { 'Layers', 'refreshLayers' }, { 'Vermin', 'refreshVermin' },
               { 'Ledger', 'refreshLedger' } }
Win.PNL = PNL   -- v7.1 (ui): the Panel's tables, for tests/gui/harness.lua
-- v7.1-forcefix: the Live tab drawn while the load-time survey ran is refreshed once it has ended (v7.1-perf2: and Layers)
function Win:onRenderFrame(dc, rect)
    Win.super.onRenderFrame(self, dc, rect)
    if self._warmWait then
        local P = sw.V7 and sw.V7.PERF
        if not (P and P.warming and P.warming()) then
            self._warmWait = nil
            local t = TABS[self.subviews.pages:getSelected()]
            if t and (t[1] == 'Live' or t[1] == 'Layers') then self:refreshTab() end   -- v7.1-perf2: Layers too
        end
    end
end
function Win:refreshTab(i)
    local t = TABS[i or self.subviews.pages:getSelected()]
    if t then self[t[2]](self) end
end
function Win:setLayer(l)
    self.layer = l
    self.frame_title = self:layerTitle()
    if self.subviews.led_layer then self.subviews.led_layer:setOption(l, false) end
    if self.subviews.lay_sel and l ~= 'all' then self.subviews.lay_sel:setOption(l, false) end
    self:syncTargets()
    self:refreshTab()
end
function Win:onInput(keys)
    if keys.CUSTOM_ALT_H then
        local t = TABS[self.subviews.pages:getSelected()]
        local lines = {}
        for _, l in ipairs(HELP[t and t[1] or 'Overview'] or {}) do lines[#lines+1] = l end
        lines[#lines+1] = ''
        lines[#lines+1] = 'The words, the same on every tab and layer:'
        for _, l in ipairs(HELP.Words) do lines[#lines+1] = '  ' .. l end
        -- v7.1 (fixes2): the v7.1 words follow; on a screen too short for both, they get a second page (shown on close)
        local more = { 'The words v7.1 added:' }
        for _, l in ipairs(HELP.Words71) do more[#more+1] = '  ' .. l end
        local okS, _, sh = pcall(function() return dfhack.screen.getWindowSize() end)
        local title = 'Help: ' .. (t and t[1] or '')
        if okS and type(sh) == 'number' and #lines + #more + 1 > sh - 8 then
            dialogs.showMessage(title, table.concat(lines, '\n'), nil, function()
                dialogs.showMessage(title .. ' (v7.1 words)', table.concat(more, '\n'))
            end)
        else
            lines[#lines+1] = ''
            for _, l in ipairs(more) do lines[#lines+1] = l end
            dialogs.showMessage(title, table.concat(lines, '\n'))
        end
        return true
    end
    if keys.CUSTOM_ALT_P then   -- v6.3.0: the Panel from any tab
        self.subviews.pages:setSelected(2); self:refreshPanel()   -- the TabBar reads the page back
        return true
    end
    -- v7.1 (ui): on the Panel, Left/Right and - + step the selected control (Shift+Left/Right ten steps); no list uses them
    if self.subviews.pages:getSelected() == 2 then
        local dir = (keys.KEYBOARD_CURSOR_RIGHT or keys.KEYBOARD_CURSOR_RIGHT_FAST or keys.STRING_A043) and 1
                 or ((keys.KEYBOARD_CURSOR_LEFT or keys.KEYBOARD_CURSOR_LEFT_FAST or keys.STRING_A045) and -1)
        if dir then self:act_panel_step(dir, keys.KEYBOARD_CURSOR_RIGHT_FAST or keys.KEYBOARD_CURSOR_LEFT_FAST); return true end
    end
    if keys.CUSTOM_ALT_L then
        local cur = 1
        for i, v in ipairs(LAYER_CYCLE) do if v == self.layer then cur = i end end
        self:setLayer(LAYER_CYCLE[cur % #LAYER_CYCLE + 1])
        return true
    end
    return Win.super.onInput(self, keys)
end
function Win:init()
    -- v7.1-perf2: the open's parts as FUSE laps ('gui:open.*', read by `seasonal-wildlife perf`). validate-full
    -- 20261002-231032 timed the open at 318 ms on a fort whose save had the tool never enabled: the open is then the
    -- first run (cold region and class memos, the default snapshot, the preset, enableSched), which the laps name.
    local lap = (FUSE and FUSE.lap) or function() return dfhack.getTickCount() end
    local t = dfhack.getTickCount()
    self.layer = 'all'
    self.cfg = loadConfig()
    self:rebuildData()
    t = lap('gui:open.pool', t)
    local firstRun = not self.cfg.initialized
    captureDefault(self.cfg); saveConfig(self.cfg)
    t = lap('gui:open.default', t)
    self._firstRun = firstRun   -- v5.11.3: the preset is applied once the pool is built (init, below)
    self._counts = self:computeCounts()
    self._hint = ''

    local biomeOpts = { { label='All biomes', value='all' } }
    -- v7.1 (ui): the short biome code (as the BIOME column), so a long biome name no longer runs under Season:
    for id in pairs(self.biomeSet) do biomeOpts[#biomeOpts+1] = { label=abbrevBiome(id) or df.biome_type[id] or ('#'..id), value=id } end
    local catOpts = { { label='All', value='all' } }
    for _, c in ipairs(CATEGORIES) do catOpts[#catOpts+1] = { label=c, value=c } end
    for _, h in ipairs(sw.MODEL.HABITATS) do catOpts[#catOpts+1] = { label=sw.MODEL.SHORT[h] or h, value='hab:' .. h } end   -- v6.4.0: habitats, orthogonal to role (v7.1: the HAB column's word)
    local seasonOpts = { { label='All', value='all' }, { label='Spring', value=0 }, { label='Summer', value=1 },
                         { label='Autumn', value=2 }, { label='Winter', value=3 } }

    self:addviews{
        -- v7.1 (ui): nine tabs need 92 columns; below that DFHack's TabBar wrapped its last tab under the pages (screen-check
        -- trap 4). wrap=false scrolls the bar instead (Ctrl+T / Ctrl+Y and the edge arrows reach every tab). No tenth tab:
        -- the Panel hosts the registry's sections.
        widgets.TabBar{ view_id='tabs', frame={ t=0, l=0 }, wrap=false, labels={ 'Overview', 'Panel', 'Roster', 'Seasons', 'Food web', 'Live', 'Layers', 'Vermin', 'Ledger' },
            -- the design's eight tabs (§11a) and, since v6.3.0, the Panel (W8) second
            on_select=function(i)
                self.subviews.pages:setSelected(i)
                self:refreshTab(i)
            end,
            get_cur_page=function() return self.subviews.pages:getSelected() end },
        widgets.Pages{ view_id='pages', frame={ t=2, l=0, r=0, b=0 }, subviews={
            -- Overview (v5.10.1): what the map holds now, the next boundary, the recent ledger
            widgets.Panel{ subviews={
                widgets.HotkeyLabel{ frame={ t=0, l=0 }, key='CUSTOM_R', label='Refresh', on_activate=self:callback('refreshOverview') },
                widgets.List{ view_id='overview', frame={ t=1, l=0, r=0, b=0 }, row_height=1 },
            } },
            -- Panel (v6.3.0, W8; alpha 1 steps 4.3 and 12.2): every switch the tool has but the creatures
            -- v7.1 (ui; R52): the sections of the control registry on the left (S / Shift+S or a click), the selected
            -- section's readouts and controls on the right, the selected control's help, the verb that ran and the value
            -- read back below
            widgets.Panel{ subviews={
                widgets.Label{ frame={ t=0, l=0 }, text={ { pen=COLOR_GREY,
                    text='Every control, by section. Enter sets; Left/Right steps (Shift: x10); * = not default.' } } },
                widgets.HotkeyLabel{ frame={ t=1, l=0 },  key='CUSTOM_A', label='All on', on_activate=self:callback('act_panel_all', true) },
                widgets.HotkeyLabel{ frame={ t=1, l=11 }, key='CUSTOM_X', label='All off', on_activate=self:callback('act_panel_all', false) },
                widgets.HotkeyLabel{ frame={ t=1, l=23 }, key='CUSTOM_R', label='Refresh', on_activate=self:callback('refreshPanel') },
                widgets.HotkeyLabel{ frame={ t=1, l=35 }, key='CUSTOM_S', label='Section', on_activate=function() self:panelSection(1) end },
                widgets.HotkeyLabel{ frame={ t=1, l=47 }, key='CUSTOM_SHIFT_S', label='back', on_activate=function() self:panelSection(-1) end },
                widgets.HotkeyLabel{ frame={ t=1, l=56 }, key='CUSTOM_D', label='Default', on_activate=self:callback('act_panel_default') },
                widgets.HotkeyLabel{ frame={ t=1, l=68 }, key='CUSTOM_ALT_S', label='Find', on_activate=self:callback('act_panel_find') },
                widgets.Label{ view_id='panel_fps', frame={ t=2, l=0, h=1 }, auto_height=false, text='' },
                widgets.List{ view_id='panel_secs', frame={ t=3, l=0, w=PNL.LW, b=5 }, row_height=1, scroll_keys={},
                    on_submit=function(i) self:panelSection(nil, i) end },
                widgets.List{ view_id='panel', frame={ t=3, l=PNL.LW + 1, r=0, b=5 }, row_height=1, on_select=self:callback('panelHelp'),
                    on_submit=self:callback('act_panel_toggle'), on_submit2=function() self:act_panel_step(-1) end },
                widgets.Label{ view_id='panel_help', frame={ b=2, l=0, r=0, h=3 }, auto_height=false, text='' },
                widgets.Label{ view_id='panel_cmd', frame={ b=1, l=0, h=1 }, auto_height=false, text='' },
                widgets.Label{ view_id='panel_status', frame={ b=0, l=0, h=1 }, auto_height=false, text='' },
            } },
            widgets.Panel{ subviews={
                widgets.Label{ frame={ t=0, l=0 }, text={
                    { text=function() return self:hdr1() end }, NEWLINE,
                    { text=function() return self:hdr2() end, pen=COLOR_GREY }, NEWLINE,
                    { text=function() return self:hdr3() end, pen=COLOR_YELLOW } } },
                widgets.Panel{ frame={ t=4, l=0, r=0, h=1 }, subviews={
                    widgets.CycleHotkeyLabel{ view_id='viewmode', frame={ t=0, l=0 }, key='CUSTOM_V',
                        label='View:', options={ { label='Current', value='cur' }, { label='Default', value='def' },
                        { label='Add invasive', value='add' } }, on_change=self:callback('refresh') },   -- v6.6.0 (W11): the vocabulary
                    -- v5.8.4: initial_option by NAME. DFHack resolves the default (1) as a VALUE before an
                    -- index, and 1 is Summer on the season list: the window opened filtered to Summer and
                    -- showed 'No matches' on a fort with nothing assigned there.
                    widgets.CycleHotkeyLabel{ view_id='category', frame={ t=0, l=22 }, key='CUSTOM_C',
                        label='Cat:', options=catOpts, initial_option='all', on_change=self:callback('refresh') },
                    widgets.CycleHotkeyLabel{ view_id='biome', frame={ t=0, l=41 }, key='CUSTOM_B',
                        label='Biome:', options=biomeOpts, initial_option='all', on_change=self:callback('refresh') },
                    widgets.CycleHotkeyLabel{ view_id='season', frame={ t=0, l=63 }, key='CUSTOM_N',
                        label='Season:', options=seasonOpts, initial_option='all', on_change=self:callback('refresh') } } },
                -- v5.10.7: declared before the list so the key reaches it and not the filter box
                widgets.HotkeyLabel{ frame={ t=5, l=0 }, key='CUSTOM_I', label='Species detail', on_activate=self:callback('act_detail') },
                widgets.Label{ frame={ t=5, l=22 }, text={ { pen=COLOR_GREY, text='Enter: active/inactive  E: cycle seasons  ODDS: share of layer' } } },
                -- v7.1 (ui): the header is drawn with the rows' widths (the WHY column fits the window; see whyWidth)
                widgets.Label{ view_id='roster_hdr', frame={ t=6, l=0, h=1 }, auto_height=false, text={ { pen=COLOR_LIGHTGREEN,
                    text=('%-18s %-8s %-6s %-5s %-9s %-7s %-6s %-5s %-3s %s'):format('CREATURE','ROLE','SIZE','HAB','BIOME','SEASON','STOCK','ODDS','act','WHY') } } },
                widgets.FilteredList{ view_id='list', frame={ t=7, l=0, r=0, b=8 }, row_height=1,
                    -- v5.11.0: the filter box takes focus only on Alt+S (DFHack's own convention) and gives it
                    -- back on Enter or Esc, so plain letters are action keys on this page: S U A W seasons,
                    -- F Y D fills, M matrix, O co-align, i detail. Nothing changes until you press one.
                    edit_key='CUSTOM_ALT_S',
                    -- v5.8.4: the filter box (a DFHack TextArea) has focus whenever this tab is shown and
                    -- binds Ctrl+A (select all), Ctrl+W (delete word) and Ctrl+X (cut) as editor keys, so
                    -- the three action labels below never saw them from the keyboard. Told to ignore them,
                    -- it lets them through to the labels. Found by the 19 September playtest.
                    edit_ignore_keys={ 'CUSTOM_CTRL_A', 'CUSTOM_CTRL_W', 'CUSTOM_CTRL_X' },
                    on_select=self:callback('on_row_select'),
                    on_submit=self:callback('act_toggle'), on_submit2=self:callback('act_cycle') },
                widgets.Divider{ frame={ b=7, h=1, l=0, r=0 }, frame_style=gui.FRAME_THIN,
                    frame_style_l=false, frame_style_r=false },
                -- v5.11.0: the Set roster tab's keys live here now (Enter allow/block and Shift-Enter cycle stay on the list)
                widgets.Panel{ frame={ b=0, l=0, r=0, h=7 }, subviews={
                    widgets.HotkeyLabel{ frame={ t=0, l=0 },  key='CUSTOM_S', label='Spring', on_activate=self:callback('act_season', 0) },
                    widgets.HotkeyLabel{ frame={ t=0, l=11 }, key='CUSTOM_U', label='Summer', on_activate=self:callback('act_season', 1) },
                    widgets.HotkeyLabel{ frame={ t=0, l=22 }, key='CUSTOM_A', label='Autumn', on_activate=self:callback('act_season', 2) },
                    widgets.HotkeyLabel{ frame={ t=0, l=33 }, key='CUSTOM_W', label='Winter', on_activate=self:callback('act_season', 3) },
                    widgets.HotkeyLabel{ frame={ t=0, l=46 }, key='CUSTOM_M', label='Matrix assign', on_activate=self:callback('act_assign_matrix') },
                    widgets.HotkeyLabel{ frame={ t=0, l=66 }, key='CUSTOM_O', label='Co-align', on_activate=self:callback('act_coalign') },
                    widgets.HotkeyLabel{ frame={ t=0, l=78 }, key='CUSTOM_E', label='Cycle', on_activate=self:callback('act_cycle') },   -- v6.3.0: a season key without Shift (alpha 1 step 2.4)
                    widgets.HotkeyLabel{ frame={ t=1, l=0 },  key='CUSTOM_CTRL_A', label='Apply now', on_activate=self:callback('act_apply') },
                    -- v7.1 (ui; Alpha Three 2.1): 'Ctrl+f: Send off + next' is 23 cells and ran under Ctrl+d at 41; the
                    -- Ctrl+w and Ctrl+g labels below ran under their neighbours too. Spaced by their drawn widths.
                    widgets.HotkeyLabel{ frame={ t=1, l=19 }, key='CUSTOM_CTRL_F', label='Send off + next', on_activate=self:callback('act_force') },
                    widgets.HotkeyLabel{ frame={ t=1, l=44 }, key='CUSTOM_CTRL_D', label='Dry-run', on_activate=self:callback('act_dryrun') },
                    widgets.HotkeyLabel{ frame={ t=1, l=61 }, key='CUSTOM_CTRL_E', label=function() return self.cfg.enabled and 'Rotation off' or 'Rotation on' end, on_activate=self:callback('act_enable') },
                    widgets.HotkeyLabel{ frame={ t=2, l=0 },  key='CUSTOM_CTRL_W', label='Stock (row)', on_activate=self:callback('act_weight') },   -- v6.5.0: abundance is stock
                    widgets.HotkeyLabel{ frame={ t=2, l=21 }, key='CUSTOM_CTRL_G', label='Stock (filter)', on_activate=self:callback('act_weight_filter') },
                    widgets.HotkeyLabel{ frame={ t=2, l=45 }, key='CUSTOM_ALT_O', label='Odds (row)', on_activate=self:callback('act_odds') },
                    widgets.HotkeyLabel{ frame={ t=2, l=64 }, key='CUSTOM_CTRL_X', label='Add invasive', on_activate=self:callback('act_addnew') },
                    -- v6.3.0 (W9): Ctrl+R and Ctrl+L are DF's macro keys (RECORD_MACRO, LOAD_MACRO) and never reached the window
                    widgets.HotkeyLabel{ frame={ t=3, l=0 },  key='CUSTOM_ALT_R', label='Reset (asks: roster or everything)', on_activate=self:callback('act_reset') },
                    widgets.HotkeyLabel{ frame={ t=3, l=45 }, key='CUSTOM_ALT_F', label='Fill cat to N', on_activate=self:callback('act_fill') },
                    widgets.CycleHotkeyLabel{ view_id='tgt_prey', frame={ t=4, l=0 }, key='CUSTOM_SHIFT_P',
                        label='prey:', options=TARGET_OPTS, initial_option=TARGET_DEFAULT.prey, on_change=function(v) self:setTarget('prey', v) end },
                    widgets.CycleHotkeyLabel{ view_id='tgt_predator', frame={ t=4, l=18 }, key='CUSTOM_SHIFT_R',
                        label='predator:', options=TARGET_OPTS, initial_option=TARGET_DEFAULT.predator, on_change=function(v) self:setTarget('predator', v) end },
                    widgets.CycleHotkeyLabel{ view_id='tgt_vermin', frame={ t=4, l=40 }, key='CUSTOM_SHIFT_V',
                        label='vermin:', options=TARGET_OPTS, initial_option=TARGET_DEFAULT.vermin, on_change=function(v) self:setTarget('vermin', v) end },
                    widgets.Label{ view_id='tgt_layer', frame={ t=4, l=58, h=1 }, auto_height=false, text='' },
                    widgets.HotkeyLabel{ frame={ t=5, l=0 },  key='CUSTOM_F', label='Fill to targets', on_activate=self:callback('act_fill_targets') },
                    widgets.HotkeyLabel{ frame={ t=5, l=20 }, key='CUSTOM_Y', label='Fill natural prey', on_activate=self:callback('act_fill_prey') },
                    widgets.HotkeyLabel{ frame={ t=5, l=42 }, key='CUSTOM_D', label='Fill natural predators', on_activate=self:callback('act_fill_predators') },
                    -- v5.8.4: a Label created with text='' is laid out ZERO rows high (auto_height counts
                    -- its lines, and '' has none) and setText never re-lays it out, so every receipt this
                    -- row was given was drawn into a zero-height frame. Fixed height, no auto sizing.
                    widgets.Label{ view_id='status', frame={ t=6, l=0, h=1 }, auto_height=false, text='' } } },
            } },
            -- Seasons: the four pyramids side by side, arrivals and departures marked
            widgets.Panel{ subviews={
                widgets.Label{ frame={ t=0, l=0 }, text={ { pen=COLOR_GREY,
                    text='Each level across the seasons. + arrives, - leaves after it. S U A W edit the row.' } } },
                -- v6.6.0 (W12, alpha 1 step 5.1): the Seasons tab edits too; each edit is one undo entry
                widgets.HotkeyLabel{ frame={ t=1, l=0 },  key='CUSTOM_S', label='Spring', on_activate=function() self:act_seasons_tab(0) end },
                widgets.HotkeyLabel{ frame={ t=1, l=12 }, key='CUSTOM_U', label='Summer', on_activate=function() self:act_seasons_tab(1) end },
                widgets.HotkeyLabel{ frame={ t=1, l=24 }, key='CUSTOM_A', label='Autumn', on_activate=function() self:act_seasons_tab(2) end },
                widgets.HotkeyLabel{ frame={ t=1, l=36 }, key='CUSTOM_W', label='Winter', on_activate=function() self:act_seasons_tab(3) end },
                widgets.Label{ view_id='seasons_status', frame={ t=1, l=50, h=1 }, auto_height=false, text='' },
                widgets.List{ view_id='seasons', frame={ t=3, l=0, r=0, b=0 }, row_height=1 },
            } },
            widgets.Panel{ subviews={
                widgets.Label{ frame={ t=0, l=0 }, text={ { pen=COLOR_GREY,
                    text='Food web of the active roster. G: mode, N: season, L: the layers side by side.' } } },
                -- v5.11.1: one tab, four modes
                widgets.CycleHotkeyLabel{ view_id='web_mode', frame={ t=1, l=0 }, key='CUSTOM_G', label='Mode:',
                    options={ { label='Pyramid', value='pyramid' }, { label='Graph', value='graph' },
                              { label='By season', value='byseason' }, { label='By layer', value='bylayer' } },
                    initial_option='pyramid', on_change=self:callback('refreshWeb') },
                widgets.CycleHotkeyLabel{ view_id='web_season', frame={ t=1, l=20 }, key='CUSTOM_N',
                    label='Season:', options=seasonOpts, on_change=self:callback('refreshWeb') },
                widgets.HotkeyLabel{ frame={ t=1, l=42 }, key='CUSTOM_L', label='Layers side by side',
                    on_activate=function() self.subviews.web_mode:setOption('bylayer', false); self:refreshWeb() end },
                widgets.List{ view_id='web', frame={ t=3, l=0, r=0, b=0 }, row_height=1 },
            } },
            -- Live: what is on the map and in the region RIGHT NOW, as biomass per level
            widgets.Panel{ subviews={
                widgets.Label{ frame={ t=0, l=0 }, text={ { pen=COLOR_GREY,
                    text='Now: tracked groups (select one), herds and packs, regional biomass per level.' } } },
                widgets.HotkeyLabel{ frame={ t=1, l=0 },  key='CUSTOM_R', label='Refresh', on_activate=self:callback('refreshLive') },
                widgets.HotkeyLabel{ frame={ t=1, l=12 }, key='CUSTOM_G', label='Groups on/off', on_activate=self:callback('act_groups') },
                -- v5.11.2: the design's Live keys. P K W act on the settings; Q X F and Enter on the selected group.
                widgets.HotkeyLabel{ frame={ t=1, l=38 }, key='CUSTOM_P', label=function() return 'Coupling ' .. (self.cfg.groups.coupling and 'on' or 'off') end, on_activate=self:callback('act_live_coupling') },
                widgets.HotkeyLabel{ frame={ t=1, l=56 }, key='CUSTOM_K', label=function() return 'Pack ' .. (self.cfg.groups.pack > 0 and tostring(self.cfg.groups.pack) or 'raw') end, on_activate=self:callback('act_live_pack') },
                widgets.HotkeyLabel{ frame={ t=1, l=68 }, key='CUSTOM_W', label='Send off + next', on_activate=self:callback('act_live_nextwave') },
                widgets.HotkeyLabel{ frame={ t=2, l=0 },  key='CUSTOM_Q', label='Hold 30 days', on_activate=self:callback('act_live_hold') },
                widgets.HotkeyLabel{ frame={ t=2, l=18 }, key='CUSTOM_X', label='Send off', on_activate=self:callback('act_live_dismiss') },
                widgets.HotkeyLabel{ frame={ t=2, l=31 }, key='CUSTOM_F', label='Follow on map', on_activate=self:callback('act_live_follow') },
                widgets.Label{ frame={ t=2, l=50 }, text={ { pen=COLOR_GREY, text='Enter: centre the map on the group' } } },
                widgets.List{ view_id='live', frame={ t=4, l=0, r=0, b=1 }, row_height=1, on_submit=self:callback('act_live_centre') },
                widgets.Label{ view_id='live_status', frame={ b=0, l=0, h=1 }, auto_height=false, text='' },
            } },
            -- Layers (v5.11.3): patterns & quotas and the caverns, one column per layer
            widgets.Panel{ subviews={
                widgets.Label{ frame={ t=0, l=0 }, text={ { pen=COLOR_GREY,
                    text='Per layer: caps, patterns, ecology, water, each cavern. L: the column keys act on.' } } },
                widgets.CycleHotkeyLabel{ view_id='lay_sel', frame={ t=1, l=0 }, key='CUSTOM_L', label='Layer:',
                    options={ { label='land', value='land' }, { label='water', value='water' }, { label='cavern', value='cavern' }, { label='deep', value='deep' } },
                    initial_option='land', on_change=self:callback('refreshLayers') },
                widgets.HotkeyLabel{ frame={ t=1, l=16 }, key='CUSTOM_O', label='Layer on/off', on_activate=self:callback('act_lay_onoff') },
                widgets.HotkeyLabel{ frame={ t=1, l=34 }, key='CUSTOM_T', label='Pattern', on_activate=self:callback('act_lay_pattern') },
                widgets.HotkeyLabel{ frame={ t=1, l=47 }, key='CUSTOM_Q', label='Ceiling', on_activate=self:callback('act_lay_quota') },
                widgets.HotkeyLabel{ frame={ t=1, l=60 }, key='CUSTOM_C', label='Group cap (R7)', on_activate=self:callback('act_lay_concurrent') },
                widgets.HotkeyLabel{ frame={ t=2, l=0 },  key='CUSTOM_D', label='Gap days', on_activate=self:callback('act_lay_gap') },
                widgets.HotkeyLabel{ frame={ t=2, l=14 }, key='CUSTOM_E', label=function() return 'Ecology ' .. (self.cfg.ecology.enabled and 'on' or 'off') end, on_activate=self:callback('act_lay_ecology') },
                widgets.HotkeyLabel{ frame={ t=2, l=31 }, key='CUSTOM_N', label='Nudge', on_activate=self:callback('act_lay_nudge') },
                widgets.HotkeyLabel{ frame={ t=2, l=42 }, key='CUSTOM_P', label=function() return 'Coupling ' .. (self.cfg.groups.coupling and 'on' or 'off') end, on_activate=self:callback('act_live_coupling') },
                widgets.HotkeyLabel{ frame={ t=2, l=60 }, key='CUSTOM_K', label=function() return 'Pack ' .. (self.cfg.groups.pack > 0 and tostring(self.cfg.groups.pack) or 'raw') end, on_activate=self:callback('act_live_pack') },
                widgets.HotkeyLabel{ frame={ t=3, l=0 },  key='CUSTOM_R', label='Re-apply preset', on_activate=self:callback('act_lay_preset') },
                widgets.HotkeyLabel{ frame={ t=3, l=22 }, key='CUSTOM_I', label=function() return 'Irruptions ' .. (self.cfg.irruption.enabled and 'on' or 'off') end, on_activate=self:callback('act_lay_irruption') },
                widgets.List{ view_id='layers', frame={ t=5, l=0, r=0, b=1 }, row_height=1 },
                widgets.Label{ view_id='layers_status', frame={ b=0, l=0, h=1 }, auto_height=false, text='' },
            } },
            -- Vermin (v5.9.10): the vermin roster by family
            widgets.Panel{ subviews={
                widgets.Label{ frame={ t=0, l=0 }, text={ { pen=COLOR_GREY,
                    text='Vermin by family. Enter: active/inactive; S U A W seasons; E opens a family.' } } },
                widgets.HotkeyLabel{ frame={ t=1, l=0 },  key='CUSTOM_S', label='Spring', on_activate=function() self:act_vermin_season(0) end },
                widgets.HotkeyLabel{ frame={ t=1, l=10 }, key='CUSTOM_U', label='Summer', on_activate=function() self:act_vermin_season(1) end },
                widgets.HotkeyLabel{ frame={ t=1, l=20 }, key='CUSTOM_A', label='Autumn', on_activate=function() self:act_vermin_season(2) end },
                widgets.HotkeyLabel{ frame={ t=1, l=30 }, key='CUSTOM_W', label='Winter', on_activate=function() self:act_vermin_season(3) end },
                widgets.HotkeyLabel{ frame={ t=1, l=40 }, key='CUSTOM_SHIFT_W', label='Stock', on_activate=self:callback('act_vermin_weight') },
                widgets.HotkeyLabel{ frame={ t=1, l=50 }, key='CUSTOM_D', label='Defaults', on_activate=self:callback('act_vermin_defaults') },
                -- v7.1 (ui): at 78 'e: Open family' ended at column 92, past the 86 the window keeps to
                widgets.HotkeyLabel{ frame={ t=1, l=63 }, key='CUSTOM_E', label='Open family', on_activate=self:callback('act_vermin_expand') },   -- v6.6.0 (W12)
                widgets.Label{ frame={ t=3, l=0 }, text={ { pen=COLOR_LIGHTGREEN,
                    text=('%-9s %-26s %3s %7s  %-6s %-7s %s'):format('FAMILY', '', 'n', 'active', 'SEASON', 'stock', 'LAYERS') } } },
                widgets.List{ view_id='vermin', frame={ t=4, l=0, r=0, b=2 }, row_height=1, on_submit=self:callback('act_vermin_toggle') },
                widgets.Label{ view_id='vermin_status', frame={ b=0, l=0, h=1 }, auto_height=false, text='' },
            } },
            -- Ledger (v5.11.4): every write and why, with undo
            widgets.Panel{ subviews={
                widgets.Label{ frame={ t=0, l=0 }, text={ { pen=COLOR_GREY,
                    text='Every write the tool made, and why. K kind, L layer, R refresh; Z undoes (fifty deep).' } } },
                widgets.CycleHotkeyLabel{ view_id='led_kind', frame={ t=1, l=0 }, key='CUSTOM_K', label='Kind:',
                    options=ledgerKindOptions(),   -- v7.1 (fixes2): every kind the engine writes (LEDGER.KINDS)
                    initial_option='all', on_change=self:callback('refreshLedger') },
                widgets.CycleHotkeyLabel{ view_id='led_layer', frame={ t=1, l=20 }, key='CUSTOM_L', label='Layer:',
                    options={ { label='all', value='all' }, { label='land', value='land' }, { label='water', value='water' }, { label='cavern', value='cavern' } },
                    initial_option='all', on_change=self:callback('refreshLedger') },
                widgets.HotkeyLabel{ frame={ t=1, l=40 }, key='CUSTOM_R', label='Refresh', on_activate=self:callback('refreshLedger') },
                widgets.HotkeyLabel{ frame={ t=1, l=54 }, key='CUSTOM_Z', label=function() return ('Undo last edit (%d)'):format(UNDO.depth()) end, on_activate=self:callback('act_undo') },
                widgets.Label{ view_id='ledger_hdr', frame={ t=2, l=0, h=1 }, auto_height=false, text='' },   -- v6.1.2: the counts above the list, which opens scrolled to the newest line
                widgets.List{ view_id='ledger', frame={ t=3, l=0, r=0, b=1 }, row_height=1 },
                widgets.Label{ view_id='ledger_status', frame={ b=0, l=0, h=1 }, auto_height=false, text='' },
            } },
        } },
    }
    t = lap('gui:open.widgets', t)
    if self._firstRun then   -- v5.11.3: a fort's first run gets the biome preset, and says so
        -- v6.3.0 (D3): the preset turns on every layer the map has and seasonal rotation
        -- v7.1 (Alpha Four 3.8, 2 Oct): under pcall. init saved initialized = true before the preset (captureDefault
        -- above), so a preset that raised (82f0c6d's buildPool crash) left the fort initialized with none of D3's layers
        -- on and was never tried again: the cavern layer stayed off and the caverns ran on DF's own odds. A failure now
        -- puts initialized back, so the next open retries the preset.
        local ok, name, allowed, _, layerNote = pcall(applyPreset, self.cfg, self.pool, self.biomeSet)
        if ok then
            saveConfig(self.cfg)
            enableSched(); self.cfg = loadConfig()
            self:rebuildData()
            -- v7.1 (validate-full 20261002-020031): the status row is one line and clips at the window's edge, and a
            -- multi-biome fort's preset name (five biomes on RinghatchetsReady) pushed the outcome off it; the
            -- outcome goes first, the biome names last
            self._firstRunMsg = ('First run: preset applied, %d species active with one season each; %s; rotation on. Biomes: %s.'):format(allowed, layerNote, name)
        else
            dfhack.printerr('seasonal-wildlife: the first-run preset failed: ' .. tostring(name))
            self.cfg = loadConfig(); self.cfg.initialized = false; saveConfig(self.cfg)
            self._firstRunMsg = ('First-run preset FAILED (%s); it runs again at the next open.'):format(tostring(name))
        end
    else
        -- v6.3.0 (W1): the roster is made whole on open -- every active species seasoned, every inactive one not
        local _, seasoned, cleared = ROSTER.normalize(self.cfg, self.pool)
        if seasoned + cleared > 0 then saveConfig(self.cfg); self._firstRunMsg = ('Roster made whole: %d active species given one season, %d inactive cleared.'):format(seasoned, cleared) end
    end
    t = lap(self._firstRun and 'gui:open.firstrun' or 'gui:open.normalize', t)
    self:syncTargets()
    self:refresh()
    t = lap('gui:open.roster', t)
    self:refreshOverview()
    lap('gui:open.overview', t)
end
-- v6.3.0: the target row shows the layer the selector names (land when it names all layers)
function Win:targetLayer() return (self.layer == 'all') and 'land' or self.layer end
function Win:syncTargets()
    local t = (self.cfg.targets or {})[self:targetLayer()] or {}
    for _, cat in ipairs(TARGET_CATS) do
        local w = self.subviews['tgt_' .. cat]
        if w then w:setOption(t[cat] or 0, false) end
    end
    if self.subviews.tgt_layer then self.subviews.tgt_layer:setText({ { text='(' .. self:targetLayer() .. ')', pen=COLOR_GREY } }) end
end
function Win:setTarget(cat, v)
    self._lastAction = 'target'
    local l = self:targetLayer()
    self.cfg.targets = self.cfg.targets or {}
    self.cfg.targets[l] = self.cfg.targets[l] or {}
    self.cfg.targets[l][cat] = v
    self:save()
end

-- v5.11.4: every write the window makes goes through here -- the state before it is pushed on the undo
-- ring, then the config is saved and the 'before' copy refreshed. deepcopy is the engine's (via UNDO).
function Win:save(label)
    if self._before then UNDO.push(self._before, label or (self._lastAction or 'edit')) end
    saveConfig(self.cfg)
    self._before = loadConfig()
end
function Win:rebuildData()
    self.poolByKey = {}
    self.pool, self.biomeSet, self.regionSet = buildPool(self.cfg)
    self._before = loadConfig()   -- v5.11.4: the undo ring's 'before' copy
    for _, e in ipairs(self.pool) do self.poolByKey[e.key] = e end
    self.marsupialEmbark = false
    for _, e in ipairs(self.pool) do
        if e.inEmbark and e.clade == 'marsupial' then self.marsupialEmbark = true; break end
    end
end
function Win:setStatus(msg) self.subviews.status:setText({ { text=msg, pen=COLOR_LIGHTCYAN } }) end

-- v6.6.0 (W9): wrap a list's rows to its width. A row is a list of tokens; one wider than the list is broken
-- at the last space before the edge, and the rest continues on the next row, indented two.
-- v7.1 (ui): at most the window's 86 columns (less the list's left edge), and a row of several tokens whose last is
-- plain text wraps that last token under itself (the Live tab's origin rows ran off the edge).
local function tokW(t)
    if type(t) ~= 'table' then return #tostring(t) end
    local txt = type(t.text) == 'string' and t.text or ''
    return (t.gap or 0) + (t.width or #txt)
end
function Win:wrap(lines, view)
    local width = (view and view.frame_body and view.frame_body.width) or ((self.frame and self.frame.w or 100) - 4)
    width = math.min(width, PNL.W - ((view and view.frame and view.frame.l) or 0))
    local out = {}
    for _, ch in ipairs(lines) do
        local toks = type(ch.text) == 'table' and ch.text or { { text=tostring(ch.text or '') } }
        local total = 0
        for _, t in ipairs(toks) do total = total + tokW(t) end
        local last = toks[#toks]
        if total > width and #toks > 1 and type(last) == 'table' and type(last.text) == 'string' and not last.width and not last.tile then
            local pre = total - tokW(last)
            if pre < width - 10 then
                local rest, first = last.text, true
                while #rest > 0 do
                    local room = width - pre
                    local cut = #rest <= room and #rest or (rest:sub(1, room):match('^.*() ') or room)
                    local piece = rest:sub(1, cut):gsub('%s+$', '')
                    local row = {}
                    for k, v in pairs(ch) do row[k] = v end
                    if first then
                        row.text = {}
                        for i = 1, #toks - 1 do row.text[i] = toks[i] end
                        row.text[#toks] = { text=piece, pen=last.pen, gap=last.gap }
                    else row.text = { { text=(' '):rep(pre) .. piece, pen=last.pen } } end
                    out[#out+1] = row
                    rest = rest:sub(cut + 1):gsub('^%s+', '')
                    first = false
                end
            else out[#out+1] = ch end
        elseif total <= width or #toks ~= 1 or type(toks[1]) ~= 'table' or type(toks[1].text) ~= 'string' then out[#out+1] = ch
        else
            local rest, pen, first = toks[1].text, toks[1].pen, true
            while #rest > 0 do
                local room = first and width or (width - 2)
                local cut = #rest <= room and #rest or (rest:sub(1, room):match('^.*() ') or room)
                local piece = rest:sub(1, cut):gsub('%s+$', '')
                local row = {}
                for k, v in pairs(ch) do row[k] = v end
                row.text = { { text=(first and '' or '  ') .. piece, pen=pen } }
                out[#out+1] = row
                rest = rest:sub(cut + 1):gsub('^%s+', '')
                first = false
            end
        end
    end
    return out
end
-- Count the CURRENT view's candidate set so toggling in Add-new moves the tallies too.
function Win:computeCounts()
    local vmode = self.subviews.viewmode and self.subviews.viewmode:getOptionValue() or 'cur'
    return countsFor(self.cfg, self.pool, vmode == 'add')
end
function Win:hdr1()
    local names = {}; for id in pairs(self.biomeSet) do names[#names+1] = df.biome_type[id] or ('#'..id) end
    table.sort(names)
    local s = 'Biomes: ' .. table.concat(names, ', ')
    return #s > PNL.W and (s:sub(1, PNL.W - 3) .. '...') or s   -- v7.1 (ui): a many-biome embark ran past the edge
end
function Win:hdr2()
    local c = self._counts or {}
    local special = 0
    for _, e in ipairs(self.pool or {}) do if e.inEmbark and e.locked then special = special + 1 end end
    return ('Active  prey=%d pred=%d bird=%d vermin=%d other=%d  %s  rotation %s  %d special (DF)')
        :format(c.prey or 0, c.predator or 0, c.bird or 0, c.vermin or 0, c.other or 0,
                dfhack.isMapLoaded() and SEASON[df.global.cur_season] or '?', self.cfg.enabled and 'ON' or 'off', special)
end
-- Per-category target: the Roster's target row when built, else the stock default.
function Win:targetFor(cat)
    local w = self.subviews['tgt_' .. cat]
    return w and w:getOptionValue() or TARGET_DEFAULT[cat]
end
function Win:hdr3()
    local c, gaps = self._counts or {}, {}
    for _, cat in ipairs(TARGET_CATS) do
        local tgt = self:targetFor(cat)
        if tgt > 0 and (c[cat] or 0) < tgt then gaps[#gaps+1] = ('%s(%d/%d)'):format(cat, c[cat] or 0, tgt) end
    end
    local msg = (#gaps > 0) and ('Thin: ' .. table.concat(gaps, ' ')) or 'Ecosystem balanced.'
    if self._hint ~= '' then msg = msg .. '   ' .. self._hint end
    return #msg > PNL.W and msg:sub(1, PNL.W) or msg
end
function Win:on_row_select(_, choice)
    if not (choice and choice.entry) then self._hint = ''; return end
    local e = choice.entry
    local prey = matchPrey(self.cfg, e, self.pool, true)
    local pred = matchPredators(self.cfg, e, self.pool, true)
    local hint = {}
    if #prey > 0 then hint[#hint+1] = 'eats ' .. prey[1].token .. (prey[2] and ',...' or '') end
    if #pred > 0 then hint[#hint+1] = 'eaten by ' .. pred[1].token .. (pred[2] and ',...' or '') end
    self._hint = (#hint > 0) and ('[' .. e.token .. ': ' .. table.concat(hint, '; ') .. ']') or ''
end

function Win:filteredEntries()
    local vmode  = self.subviews.viewmode:getOptionValue()
    local cat    = self.subviews.category:getOptionValue()
    local biome  = self.subviews.biome:getOptionValue()
    local season = self.subviews.season:getOptionValue()
    local out = {}
    for _, e in ipairs(self.pool) do
        -- v6.3.0 (W1, alpha 1 step 3.7): Default is the embark as first found -- the species the worldgen snapshot
        -- holds -- where it used to repeat Current
        local viewOk = (vmode == 'add' and e.eligible and not e.inEmbark) or (vmode == 'cur' and e.inEmbark)
                    or (vmode == 'def' and self.cfg.default_snapshot[e.key] ~= nil)
        local catOk  = (cat == 'all') or (e.cat == cat) or (cat == 'hab:' .. tostring(e.habitat))
        local biomeOk= (biome == 'all') or (e.biomes[biome] == true)
        local seaOk  = (season == 'all') or inSeason(self.cfg, e.key, season)
        -- v6.3.0 (D8): special creatures (demons, megabeasts, night creatures, mythic) are DF's; not listed
        if viewOk and catOk and biomeOk and seaOk and self:layerOk(e.viewLayer or e.layer) and not e.locked then out[#out+1] = e end
    end
    return out
end
function Win:makeChoice(e)
    local codes = {}; for id in pairs(e.biomes) do codes[#codes+1] = abbrevBiome(id) end
    table.sort(codes)
    local bstr = (codes[1] or '-') .. (#codes > 1 and ('+'..(#codes-1)) or '')
    local def = self.subviews.viewmode and self.subviews.viewmode:getOptionValue() == 'def'
    local allowed = def and sw.defaultAllow(e) or (not def and isAllowed(self.cfg, e))
    local tag = ''
    if e.mega then tag = 'M' elseif e.night then tag = 'N' end
    if e.locked then tag = tag..'L' end            -- L = locked ecology class
    if e.aquatic then tag = tag..'w' end            -- w = aquatic
    if e.clade == 'marsupial' then tag = tag..'~' end -- ~ = marsupial/monotreme
    if tag ~= '' then tag = ' '..tag end
    local skey = e.token..' '..e.cat..(e.aquatic and ' aquatic' or '')..(e.clade == 'marsupial' and ' marsupial' or '')
    return { search_key=skey, entry=e, text={
        iconToken(e), { text=' '..e.token..tag, width=17, pad_char=' ' },
        { gap=1, text=e.cat, width=8 }, { gap=1, text=e.size, width=6 },
        { gap=1, text=sw.MODEL.SHORT[e.habitat] or '?', width=5 },   -- v6.4.0 (W2): habitat
        { gap=1, text=bstr, width=9 }, { gap=1, text=def and '-' or seasonLabel(self.cfg, e.key), width=7 },
        { gap=1, text=def and fmtStock(self.cfg.default_snapshot[e.key] or 0) or fmtStock(self:stockOf(e.key)), width=6 },   -- v6.5.0 (W5)
        { gap=1, text=def and '-' or self:oddsOf(e), width=5 },   -- v6.7.0: '(12%)' out of season
        { gap=1, text=allowed and 'Y' or '-', width=3, pen=allowed and COLOR_GREEN or COLOR_RED },
        { gap=1, text=def and ('found: ' .. tostring(self.cfg.default_snapshot[e.key] or 0)) or whyShort(whyFor(self.cfg, e)), width=self:whyWidth(), pen=COLOR_DARKGREY } } }   -- v5.10.5 the why column; v5.10.8 compact; v7.1 fitted
end
-- v7.1 (ui): the WHY column takes what is left of the window's 86 columns after the other ten (76), 17 at most; the
-- species page (i) keeps the full reason
function Win:whyWidth()
    local v = self.subviews.list
    local w = (v and v.frame_body and v.frame_body.width) or ((self.frame and self.frame.w or 90) - 4)
    return math.max(6, math.min(17, math.min(w, PNL.W) - 76))
end
-- v6.5.0 (W5): stock and odds for every row, computed once per refresh rather than per row
function Win:stockOf(key)
    local t = self._stock
    return t and t[key] or 0
end
function Win:oddsOf(e)
    if not isAllowed(self.cfg, e) or e.cat == 'vermin' then return '-' end
    local tot = (self._oddsTotal or {})[e.layer] or 0
    local w = ODDS.weight(self.cfg, e.key, e.token)
    if inSeason(self.cfg, e.key, df.global.cur_season) then
        return tot > 0 and ('%d%%'):format(math.floor(100 * w / tot + 0.5)) or '-'
    end
    -- v6.7.0 (alpha 2, step 4.3): out of season, the share it would have in season, in brackets (ODDS.share's rule)
    return (tot + w) > 0 and ('(%d%%)'):format(math.floor(100 * w / (tot + w) + 0.5)) or '-'
end
function Win:tallyStockOdds()
    local stock, all = {}, df.global.world.populations.all
    for _, r in ipairs(sw.CACHE.managedPops()) do
        local pop = all[r.i]
        if pop and pop.race == r.race then stock[r.key] = (stock[r.key] or 0) + pop.quantity end
    end
    local tot, season = {}, df.global.cur_season
    for _, e in ipairs(self.pool) do
        if e.inEmbark and not e.locked and e.cat ~= 'vermin' and isAllowed(self.cfg, e) and inSeason(self.cfg, e.key, season) then
            tot[e.layer] = (tot[e.layer] or 0) + ODDS.weight(self.cfg, e.key, e.token)
        end
    end
    self._stock, self._oddsTotal = stock, tot
end
function Win:refresh()
    self:tallyStockOdds()
    self._counts = self:computeCounts()
    local list = self.subviews.list
    local filt = list:getFilter()
    local ch = {}
    for _, e in ipairs(self:filteredEntries()) do ch[#ch+1] = self:makeChoice(e) end
    list:setChoices(ch)
    if self.subviews.roster_hdr then
        self.subviews.roster_hdr:setText({ { pen=COLOR_LIGHTGREEN, text=('%-18s %-8s %-6s %-5s %-9s %-7s %-6s %-5s %-3s %s'):format('CREATURE','ROLE','SIZE','HAB','BIOME','SEASON','STOCK','ODDS','act',
            ('WHY'):sub(1, self:whyWidth())) } })
    end
    if filt and filt ~= '' then list:setFilter(filt) end
end

-- Food web rendering. Season 'All' = flat predator->prey chain list for every season;
-- a specific season = ASCII trophic pyramid (terrestrial levels) + aquatic mini-web.
local PYRAMID_W = 74
local function centerText(s, w)
    local pad = math.max(0, math.floor((w - #s) / 2))
    return (' '):rep(pad) .. s
end
local PYRAMID_LEVELS = {
    { name='apex',      pen=COLOR_RED,      match=function(e) return e.cat == 'predator' and e.size ~= 'small' end },   -- v6.4.0: by role and band
    { name='predators', pen=COLOR_YELLOW,   match=function(e) return e.cat == 'predator' and e.size == 'small' end },
    { name='prey',      pen=COLOR_GREEN,    match=function(e) return e.cat == 'prey' end },
    { name='vermin',    pen=COLOR_DARKGREY, match=function(e) return e.cat == 'vermin' end },
}
function Win:buildPyramid(s, lines)
    local land, aqua = {}, {}
    for _, e in ipairs(self.pool) do
        if e.inEmbark and isAllowed(self.cfg, e) and inSeason(self.cfg, e.key, s) and self:layerOk(e.viewLayer or e.layer) then
            if e.aquatic then aqua[#aqua+1] = e else land[#land+1] = e end
        end
    end
    lines[#lines+1] = { text={ { text=SEASON[s]..' -- trophic pyramid (terrestrial; prey feeds upward ^)', pen=SEASON_PEN[s] } } }
    local prevHad = false
    for _, lv in ipairs(PYRAMID_LEVELS) do
        local members = {}
        for _, e in ipairs(land) do
            if lv.match(e) then members[#members+1] = e end
        end
        if #members > 0 then
            if prevHad then lines[#lines+1] = { text={ { text=centerText('^     ^     ^', PYRAMID_W), pen=COLOR_DARKGREY } } } end
            lines[#lines+1] = { text=iconRow(members, PYRAMID_W, lv.pen) }
            prevHad = true
        end
    end
    if not prevHad then lines[#lines+1] = { text={ { text='  (no terrestrial creatures this season)', pen=COLOR_DARKGREY } } } end
    lines[#lines+1] = { text='' }
    lines[#lines+1] = { text={ { text=SEASON[s]..' -- aquatic chain', pen=SEASON_PEN[s] } } }
    local anyA, linked = false, {}
    for _, e in ipairs(aqua) do
        local prey = {}
        for _, p in ipairs(matchPrey(self.cfg, e, self.pool, true)) do
            if inSeason(self.cfg, p.key, s) then prey[#prey+1] = p; linked[p.token] = true end
        end
        if #prey > 0 then
            anyA = true; linked[e.token] = true
            local row = { { text='  ' }, iconToken(e), { text=' '..e.token..' ----> ', pen=COLOR_LIGHTCYAN } }
            for i, p in ipairs(prey) do
                if i > 1 then row[#row+1] = { text=', ' } end
                row[#row+1] = iconToken(p); row[#row+1] = { text=' '..p.token }
            end
            lines[#lines+1] = { text=row }
        end
    end
    local loose = {}
    for _, e in ipairs(aqua) do
        if not linked[e.token] then loose[#loose+1] = e end
    end
    if #loose > 0 then
        anyA = true
        local row = { { text='  (unlinked) ', pen=COLOR_DARKGREY } }
        for i, e in ipairs(loose) do
            if i > 1 then row[#row+1] = { text=', ', pen=COLOR_DARKGREY } end
            row[#row+1] = iconToken(e); row[#row+1] = { text=' '..e.token, pen=COLOR_DARKGREY }
        end
        lines[#lines+1] = { text=row }
    end
    if not anyA then lines[#lines+1] = { text={ { text='  (no aquatic creatures this season)', pen=COLOR_DARKGREY } } } end
end
-- the trophic levels the Live tab and the web's by-season / by-layer modes share (moved ahead of the web in v5.11.1)
local LEVELS = {
    { name='large predators',      pen=COLOR_LIGHTRED,  match=function(e) return e.cat=='predator' and e.size~='small' end },   -- v6.4.0: medium and large bands
    { name='small predators',      pen=COLOR_RED,       match=function(e) return e.cat=='predator' and e.size=='small' end },
    { name='prey',                 pen=COLOR_GREEN,     match=function(e) return e.cat=='prey' end },
    { name='vermin',               pen=COLOR_DARKGREY,  match=function(e) return e.cat=='vermin' end },
}
-- v5.11.1: the graph -- every configured predator -> prey edge, with the pairs DF's reaction table
-- holds right now marked live (ecoLivePairs reads the same cells ecoWrite writes). ASCII arrows on
-- purpose: the text grid drops non-ASCII glyphs, and so does the rig's screen reader.
function Win:buildGraph(sel, lines)
    local live = ecoLivePairs()
    local onMap = {}
    for _, u in ipairs(df.global.world.units.active) do
        if WILD.onMap(u) then local t = df.creature_raw.find(u.race).creature_id; onMap[t] = (onMap[t] or 0) + 1 end
    end
    lines[#lines+1] = { text={ { text=('Food web as a graph, %s: predator --> prey.   ==> live pair (related in DF\'s table now)   --> configured edge')
        :format(sel == 'all' and 'all seasons' or SEASON[sel]), pen=COLOR_GREY } } }
    local nEdge, nLive, linked = 0, 0, {}
    local function inSel(key) return sel == 'all' or inSeason(self.cfg, key, sel) end
    for _, e in ipairs(self.pool) do
        if e.inEmbark and e.cat == 'predator' and isAllowed(self.cfg, e) and inSel(e.key) and self:layerOk(e.viewLayer or e.layer) then
            local prey = {}
            for _, p in ipairs(matchPrey(self.cfg, e, self.pool, true)) do if inSel(p.key) then prey[#prey+1] = p end end
            if #prey > 0 then
                linked[e.token] = true
                local head = { iconToken(e), { text=(' %s%s'):format(e.token, onMap[e.token] and (' x' .. onMap[e.token]) or ''), pen=COLOR_YELLOW } }
                local row, per = head, 0
                for _, p in ipairs(prey) do
                    local k = e.token < p.token and (e.token .. '|' .. p.token) or (p.token .. '|' .. e.token)
                    local n = live[k]
                    if per == 3 then lines[#lines+1] = { text=row }; row = { { text=('%' .. (#e.token + 3) .. 's'):format('') } }; per = 0 end
                    row[#row+1] = { text=n and ' ==> ' or ' --> ', pen=n and COLOR_LIGHTRED or COLOR_DARKGREY }
                    row[#row+1] = { text=p.token .. (onMap[p.token] and (' x' .. onMap[p.token]) or '') .. (n and (' (' .. n .. ' related)') or ''),
                                    pen=n and COLOR_WHITE or COLOR_GREY }
                    linked[p.token] = true; nEdge = nEdge + 1; if n then nLive = nLive + 1 end; per = per + 1
                end
                lines[#lines+1] = { text=row }
            end
        end
    end
    local loose = {}
    for _, e in ipairs(self.pool) do
        if e.inEmbark and isAllowed(self.cfg, e) and e.cat ~= 'vermin' and not linked[e.token] and inSel(e.key) then loose[#loose+1] = e.token end
    end
    table.sort(loose)
    lines[#lines+1] = { text='' }
    lines[#lines+1] = { text={ { text=('%d edges, %d live pairs on the map now'):format(nEdge, nLive), pen=COLOR_WHITE } } }
    if #loose > 0 then lines[#lines+1] = { text={ { text='unlinked: ' .. table.concat(loose, ' '), pen=COLOR_DARKGREY } } } end
end
-- v5.11.1: by season -- four columns, species per level, the adult-mass ratio, arrivals and departures
function Win:buildBySeason(lines)
    local colW = 15
    local present, mass = {}, {}
    for sn = 0, 3 do
        present[sn] = {}; mass[sn] = { pred=0, prey=0 }
        for _, e in ipairs(self.pool) do
            if e.inEmbark and not e.aquatic and isAllowed(self.cfg, e) and inSeason(self.cfg, e.key, sn) and self:layerOk(e.viewLayer or e.layer) then
                present[sn][e.token] = e
                if e.cat == 'predator' then mass[sn].pred = mass[sn].pred + (e.mass or 0)
                elseif e.cat == 'prey' then mass[sn].prey = mass[sn].prey + (e.mass or 0) end
            end
        end
    end
    local hdr = { { text=('%-22s'):format('by season (land)') } }
    for sn = 0, 3 do hdr[#hdr+1] = { text=('%-' .. colW .. 's'):format(SEASON[sn]), pen=SEASON_PEN[sn] } end
    lines[#lines+1] = { text=hdr }
    for _, lv in ipairs(LEVELS) do
        local row = { { text=('  %-20s'):format(lv.name), pen=lv.pen } }
        for sn = 0, 3 do
            local n = 0
            for _, e in pairs(present[sn]) do if lv.match(e) then n = n + 1 end end
            row[#row+1] = { text=('%-' .. colW .. 's'):format(n > 0 and (n .. ' species') or '-'), pen=n > 0 and lv.pen or COLOR_DARKGREY }
        end
        lines[#lines+1] = { text=row }
    end
    local row = { { text=('  %-20s'):format('mass ratio prey:pred'), pen=COLOR_WHITE } }
    for sn = 0, 3 do
        local m = mass[sn]
        local txt, pen
        if m.pred == 0 then txt, pen = (m.prey > 0 and 'no predator' or '-'), COLOR_DARKGREY
        else local r = m.prey / m.pred; txt = ('%.1f %s'):format(r, r >= 8 and 'ok' or (r >= 3 and 'thin' or 'low')); pen = r >= 8 and COLOR_LIGHTGREEN or (r >= 3 and COLOR_YELLOW or COLOR_LIGHTRED) end
        row[#row+1] = { text=('%-' .. colW .. 's'):format(txt), pen=pen }
    end
    lines[#lines+1] = { text=row }
    for _, kind in ipairs({ { 'arrive', 1, COLOR_LIGHTGREEN, '+' }, { 'leave', -1, COLOR_YELLOW, '-' } }) do
        local name, dir, pen, mark = kind[1], kind[2], kind[3], kind[4]
        local row2 = { { text=('  %-20s'):format(name), pen=pen } }
        local extra = {}
        for sn = 0, 3 do
            local other = dir == 1 and (sn + 3) % 4 or (sn + 1) % 4
            local toks = {}
            for t in pairs(present[sn]) do if not present[other][t] then toks[#toks+1] = t end end
            table.sort(toks)
            row2[#row2+1] = { text=('%-' .. colW .. 's'):format(#toks > 0 and (mark .. #toks .. ' ' .. toks[1]:sub(1, colW - 4)) or '-'), pen=#toks > 0 and pen or COLOR_DARKGREY }
            if #toks > 1 then extra[#extra+1] = SEASON[sn] .. ' ' .. mark .. table.concat(toks, ' ' .. mark) end
        end
        lines[#lines+1] = { text=row2 }
        for _, x in ipairs(extra) do lines[#lines+1] = { text={ { text='      ' .. x, pen=COLOR_DARKGREY } } } end
    end
end
-- v5.11.1: by layer -- the enabled layers side by side for one season, with the bridge edges (a predator
-- whose prey is in another layer: the riparian and boundary workers matchPrey already admits)
function Win:buildByLayer(sel, lines)
    local sn = sel == 'all' and df.global.cur_season or sel
    local layers = { 'land' }
    for _, l in ipairs({ 'water', 'cavern' }) do if enabledLayers(self.cfg)[l] then layers[#layers+1] = l end end
    local colW = math.floor(70 / #layers)
    local hdr = { { text=('%-10s'):format(SEASON[sn]), pen=SEASON_PEN[sn] } }
    for _, l in ipairs(layers) do hdr[#hdr+1] = { text=('%-' .. colW .. 's'):format(l:upper()), pen=COLOR_WHITE } end
    lines[#lines+1] = { text=hdr }
    local inLayer = {}
    for _, l in ipairs(layers) do inLayer[l] = {} end
    for _, e in ipairs(self.pool) do
        if e.inEmbark and inLayer[e.layer] and isAllowed(self.cfg, e) and inSeason(self.cfg, e.key, sn) then inLayer[e.layer][#inLayer[e.layer]+1] = e end
    end
    for _, lv in ipairs(LEVELS) do
        local cols, more = {}, 0
        for i, l in ipairs(layers) do
            local toks = {}
            for _, e in ipairs(inLayer[l]) do if lv.match(e) then toks[#toks+1] = e.token end end
            table.sort(toks)
            local chunks, cur = {}, ''
            for _, t in ipairs(toks) do
                if #cur > 0 and #cur + 1 + #t > colW - 1 then chunks[#chunks+1] = cur; cur = t else cur = (#cur > 0) and (cur .. ' ' .. t) or t end
            end
            if #cur > 0 then chunks[#chunks+1] = cur end
            cols[i] = chunks; if #chunks > more then more = #chunks end
        end
        if more == 0 then more = 1 end
        for r = 1, math.min(more, 4) do
            local row = { { text=('%-10s'):format(r == 1 and lv.name:sub(1, 10) or ''), pen=lv.pen } }
            for i in ipairs(layers) do row[#row+1] = { text=('%-' .. colW .. 's'):format(cols[i][r] or (r == 1 and '-' or '')), pen=cols[i][r] and lv.pen or COLOR_DARKGREY } end
            lines[#lines+1] = { text=row }
        end
    end
    local bridges = {}
    for _, l in ipairs(layers) do
        for _, e in ipairs(inLayer[l]) do
            if e.cat == 'predator' then
                for _, p in ipairs(matchPrey(self.cfg, e, self.pool, true)) do
                    if p.layer ~= e.layer and inLayer[p.layer] and inSeason(self.cfg, p.key, sn) then bridges[#bridges+1] = ('%s -> %s (%s -> %s)'):format(e.token, p.token, e.layer, p.layer) end
                end
            end
        end
    end
    lines[#lines+1] = { text='' }
    lines[#lines+1] = { text={ { text='bridge edges across layers: ' .. (#bridges > 0 and table.concat(bridges, ', ') or 'none'), pen=COLOR_LIGHTCYAN } } }
end
function Win:refreshWeb()
    local sel = self.subviews.web_season and self.subviews.web_season:getOptionValue() or 'all'
    local mode = self.subviews.web_mode and self.subviews.web_mode:getOptionValue() or 'pyramid'
    local lines = {}
    if self.cfg.ecology.enabled then
        lines[#lines+1] = { text={ { text='Ecology ON: a predator beside prey is related to it in DF\'s own table and will attack; predators far from prey are moved closer. A caravan\'s animals are at risk while they are on the map; your livestock is ' .. (self.cfg.ecology.livestock and 'a target too' or 'safe') .. '. (seasonal-wildlife groups ecology off)', pen=COLOR_LIGHTRED } } }
    else
        lines[#lines+1] = { text={ { text='Ecology off: predators and prey share the map and meet only by chance. (seasonal-wildlife groups ecology on)', pen=COLOR_DARKGREY } } }
    end
    lines[#lines+1] = { text='' }
    if mode == 'graph' then self:buildGraph(sel, lines)
    elseif mode == 'byseason' then self:buildBySeason(lines)
    elseif mode == 'bylayer' then self:buildByLayer(sel, lines)
    elseif sel == 'all' then
        for s = 0, 3 do
            local pen = SEASON_PEN[s]
            lines[#lines+1] = { text={ { text=SEASON[s], pen=pen } } }
            local any = false
            for _, e in ipairs(self.pool) do
                if e.cat == 'predator' and inSeason(self.cfg, e.key, s) and isAllowed(self.cfg, e) and self:layerOk(e.viewLayer or e.layer) then
                    local prey = {}
                    for _, p in ipairs(matchPrey(self.cfg, e, self.pool, true)) do
                        if inSeason(self.cfg, p.key, s) then prey[#prey+1] = p.token end
                    end
                    if #prey > 0 then
                        any = true
                        lines[#lines+1] = { text={ { text='  '..CAT_ICON[e.cat]..' '..e.token..'  -> ', pen=pen },
                            { text=table.concat(prey, ', ') } } }
                    end
                end
            end
            if not any then lines[#lines+1] = { text={ { text='  (no chains this season)', pen=COLOR_DARKGREY } } } end
            lines[#lines+1] = { text='' }
        end
    else
        self:buildPyramid(sel, lines)
    end
    self.subviews.web:setChoices(self:wrap(lines, self.subviews.web))
end

--========================================================================================
-- Live tab: biomass now, groups now
--========================================================================================

local function fmtBig(n)
    if n >= 1e6 then return ('%.1fM'):format(n/1e6) elseif n >= 1e3 then return ('%.0fk'):format(n/1e3) end
    return tostring(math.floor(n))
end
local function bar(frac, w)
    local n = math.max(0, math.min(w, math.floor(frac * w + 0.5)))
    return string.rep('#', n) .. string.rep('.', w - n)
end
function Win:refreshLive()
    local lines = {}
    local season = df.global.cur_season
    -- v6.1.0: the status lines first, so they stay above the fold however many groups are tracked
    local rows, g = groupsStatus()
    -- v7.1 (validation r2): the Groups header and the per-layer rows lead the tab. Below the Herds & packs block they
    -- fell under the fold once a fort tracked a dozen species (validate-full 20261001-224525, gui.tab.live).
    -- v7.1 (fixes2): the release clock is adaptive (R31): the header names the clock, and one line per layer gives its
    -- target, the groups there and the next release (V7.GRP.layerRows), not v7.0's fixed 'gap 5-20 days'
    local gc = self.cfg.groups
    local clock = gc.adaptive and ('adaptive, gap %g-%d d'):format(gc.gap_floor_days, gc.gap_max_days) or ('fixed %d-%d days'):format(gc.gap_min_days, gc.gap_max_days)
    lines[#lines+1] = { text={ { text=('Groups: %s   land cap %d   release clock %s   released %d   departed %d')
        :format(gc.enabled and 'ON' or 'off', sw.QUOTA.land(self.cfg), clock, g.detached, g.departed or 0), pen=COLOR_YELLOW } } }
    local GRP = sw.V7 and sw.V7.GRP
    if GRP and GRP.layerRows and dfhack.isMapLoaded() then
        local okR, lrows = pcall(GRP.layerRows, self.cfg, g, true, true)   -- v7.1-forcefix: nowait, never the load-time survey
        if okR then for _, r in ipairs(lrows) do if self:layerOk(GRP.parent(r:match('^%s*(%S+)'))) then lines[#lines+1] = { text={ { text=r, pen=COLOR_GREY } } } end end end
    end
    -- v7.1-forcefix (validate-full 20261002-220014): while the load-time survey runs the water and cavern rows wait for
    -- it; the tab says so and refreshes itself when it ends (onRenderFrame)
    local P = sw.V7 and sw.V7.PERF
    self._warmWait = (P and P.warming and P.warming()) or nil
    if self._warmWait then lines[#lines+1] = { text={ { text='  (map survey running: water and cavern rows follow in a moment)', pen=COLOR_DARKGREY } } } end
    lines[#lines+1] = { text={ { text=PATTERN.status(self.cfg), pen=COLOR_GREY } } }
    lines[#lines+1] = { text={ { text=IRRUPT.status(self.cfg, g), pen=self.cfg.irruption.enabled and COLOR_LIGHTRED or COLOR_DARKGREY } } }   -- v6.1.0
    lines[#lines+1] = { text={ { text=ecologyStatus(self.cfg, g), pen=self.cfg.ecology.enabled and COLOR_LIGHTRED or COLOR_DARKGREY } } }
    -- untracked wild units by race (cavern and water sources included, labelled)
    local wild = {}
    for _, u in ipairs(df.global.world.units.active) do
        if WILD.onMap(u) and self:layerOk(WILD.layerOf(u)) then
            local k = df.creature_raw.find(u.race).creature_id .. ' (' .. WILD.layerOf(u) .. ')'
            wild[k] = (wild[k] or 0) + 1
        end
    end
    local wk = {}; for k in pairs(wild) do wk[#wk+1] = k end; table.sort(wk)
    local parts = {}; for _, k in ipairs(wk) do parts[#parts+1] = k .. ' x' .. wild[k] end
    lines[#lines+1] = { text='' }
    lines[#lines+1] = { text={ { text='Wild on map: ' .. (#parts > 0 and table.concat(parts, ', ') or 'none'), pen=COLOR_WHITE } } }
    -- v6.5.0 (W10, alpha 1 steps 6.1, 11.3): every wild animal on the map, by where it came from
    local tracked = {}
    for _, grp in ipairs(g.groups) do for _, id in ipairs(grp.ids) do tracked[id] = grp end end
    local byOrigin = {}
    for _, u in ipairs(df.global.world.units.active) do
        if WILD.onMap(u) and self:layerOk(WILD.layerOf(u)) then
            local o = WILD.origin(u, tracked)
            local t = df.creature_raw.find(u.race).creature_id
            byOrigin[o] = byOrigin[o] or {}
            byOrigin[o][t] = (byOrigin[o][t] or 0) + 1
        end
    end
    for _, o in ipairs({ 'DF wave', 'tool-drawn', 'resident', 'born here', 'untracked', 'deep' }) do
        local m = byOrigin[o]
        if m then
            local ks, n = {}, 0
            for t, c in pairs(m) do ks[#ks+1] = t .. ' x' .. c; n = n + c end
            table.sort(ks)
            lines[#lines+1] = { text={ { text=('  %-11s %3d  '):format(o, n), pen=COLOR_YELLOW }, { text=table.concat(ks, ', '), pen=COLOR_GREY } } }
        end
    end
    lines[#lines+1] = { text={ { text=QUOTA.status(self.cfg), pen=COLOR_GREY } } }
    lines[#lines+1] = { text={ { text=CAVE.status(true), pen=COLOR_GREY } } }   -- v7.1-forcefix: nowait
    lines[#lines+1] = { text={ { text=STOCK.status(self.cfg), pen=COLOR_GREY } } }
    local fuse = FUSE.status()
    lines[#lines+1] = { text={ { text=fuse, pen=fuse:find('TRIPPED') and COLOR_LIGHTRED or COLOR_DARKGREY } } }
    -- The cavern ceiling's lag is the one thing a player will read as a bug (addendum 57): the
    -- layer sits over its ceiling for as long as DF's leave countdowns take, because holding
    -- frequencies stops arrivals and culls nothing. Say so on the Live tab, where they are
    -- looking at the number that is not coming down.
    if self.cfg.layers.cavern then
        lines[#lines+1] = { text={ { text=CAVERN.status(self.cfg), pen=COLOR_GREY } } }
    end
    -- v5.11.2: Herds & packs (v6.1.1: ahead of the group rows, which can run past the fold) -- the cohesion lever and, per tracked species, its label, the raw reason, the override
    lines[#lines+1] = { text={ { text=('Herds & packs: cohesion %s (lever: leader + followers, E28)   radius herd %d  pack %d  flock %d   coupling pack size %s')
        :format(self.cfg.groups.cohesion and 'on' or 'off', self.cfg.groups.follow_herd, self.cfg.groups.follow_pack, self.cfg.groups.follow_flock,
                self.cfg.groups.pack > 0 and tostring(self.cfg.groups.pack) or 'raw'), pen=COLOR_YELLOW } } }
    local seen = {}
    for _, grp in ipairs(g.groups) do
        if not seen[grp.token] then
            seen[grp.token] = true
            local label = grp.label or cohesionLabel(grp.race)
            -- v7.1: a diet predator in a group is a pack too (fixes.md section 4); reasons kept to 36 columns so a row fits
            local reason = ({ flock='FLIER in the raws', pack='a predator (LARGE_PREDATOR or diet)', herd='no FLIER, no LARGE_PREDATOR (grazer)', school='swims: a water group', solitary='no raw' })[label] or '?'
            local e = self.poolByKey[keyFor(grp.layer or 'land', grp.token)]
            -- v7.1 (validation r2): the cluster range from the raw (the pool entry carries none, so every row read
            -- 'cluster ?' and wrapped onto a second line)
            local cr = grp.race and df.creature_raw.find(grp.race)
            local cl = cr and ('  cluster %d-%d'):format(cr.cluster_number[1], cr.cluster_number[0]) or ''
            local over = (label == 'pack' and self.cfg.groups.pack > 0) and ('pack size ' .. self.cfg.groups.pack) or ('raw' .. cl)
            lines[#lines+1] = { text={ { text=('  %-18s %-9s %-36s %s'):format(grp.token:sub(1, 18), label, reason, over), pen=COLOR_GREY } } }
        end
    end
    if not next(seen) then lines[#lines+1] = { text={ { text='  (no tracked species)', pen=COLOR_DARKGREY } } } end
    lines[#lines+1] = { text='' }
    -- groups (after the status lines since v6.1.0; the Groups header itself is the tab's first line since v7.1)
    lines[#lines+1] = { text={ { text=('Tracked groups (%d):'):format(#rows), pen=COLOR_YELLOW } } }
    if #rows == 0 then lines[#lines+1] = { text={ { text='  (no tracked groups on the map)', pen=COLOR_DARKGREY } } } end
    self._liveG = g   -- v5.11.2: the group records behind the rows, for Q X F and Enter
    for i, r in ipairs(rows) do lines[#lines+1] = { text='  ' .. r, grp=g.groups[i] } end
    -- biomass per level, per layer, in-season
    local rs = getEmbarkRegions()
    local layers = enabledLayers(self.cfg)
    for layer in pairs(layers) do if self:layerOk(layer) then
        local byLevel, total = {}, 0
        for i in ipairs(LEVELS) do byLevel[i] = 0 end
        local P = sw.V7 and sw.V7.PERF
        if P and not P.on('legacy_live') then   -- v7.1 (perf, P6): the managed-entry index, not every population per layer
            local all = df.global.world.populations.all
            for _, r in ipairs(sw.CACHE.managedPops()) do
                local pop = r.layer == layer and all[r.i] or nil
                local e = pop and pop.race == r.race and self.poolByKey[r.key]
                if e and pop.quantity > 0 then
                    local bm = pop.quantity * e.mass
                    for i, lv in ipairs(LEVELS) do if lv.match(e) then byLevel[i] = byLevel[i] + bm; total = total + bm; break end end
                end
            end
        else
        for _, pop in ipairs(df.global.world.populations.all) do
            if managedPop(pop, rs, LAYER_SET[layer]) then
                local craw = df.creature_raw.find(pop.race)
                local e = craw and self.poolByKey[keyFor(layer, craw.creature_id)]
                if e and pop.quantity > 0 then
                    local bm = pop.quantity * e.mass
                    for i, lv in ipairs(LEVELS) do if lv.match(e) then byLevel[i] = byLevel[i] + bm; total = total + bm; break end end
                end
            end
        end
        end
        lines[#lines+1] = { text='' }
        lines[#lines+1] = { text={ { text=('%s biomass, %s (regional quantities x adult volume)'):format(layer:upper(), SEASON[season]), pen=SEASON_PEN[season] } } }
        for i, lv in ipairs(LEVELS) do
            local frac = total > 0 and byLevel[i] / total or 0
            lines[#lines+1] = { text={ { text=('  %-22s '):format(lv.name), pen=lv.pen },
                { text=bar(frac, 30), pen=lv.pen }, { text=('  %6s  %3d%%'):format(fmtBig(byLevel[i]), math.floor(frac*100+0.5)) } } }
        end
        local pred, prey = byLevel[1] + byLevel[2], byLevel[4]
        if pred > 0 then
            local ratio = prey / pred
            local pen = ratio >= 8 and COLOR_LIGHTGREEN or (ratio >= 3 and COLOR_YELLOW or COLOR_LIGHTRED)
            lines[#lines+1] = { text={ { text=('  prey:predator biomass %.1f : 1   %s'):format(ratio,
                ratio >= 8 and 'healthy' or (ratio >= 3 and 'thin' or 'NOT ENOUGH TO EAT')), pen=pen } } }
        end
    end end
    self.subviews.live:setChoices(self:wrap(lines, self.subviews.live))
end
-- v5.11.2: the Live keys
local function setField(t, k, v) t[k] = v end   -- luacheck marks df.global.* read-only; DF's follow field is not
function Win:setLiveStatus(msg) self.subviews.live_status:setText({ { text=msg, pen=COLOR_LIGHTCYAN } }) end
function Win:curGroup()
    local _, c = self.subviews.live:getSelected()
    return c and c.grp
end
local function firstLive(grp)
    for _, id in ipairs(grp.ids) do
        local u = df.unit.find(id)
        if u and not dfhack.units.isDead(u) then
            if grp.leader and u.id ~= grp.leader then
                local l = df.unit.find(grp.leader)
                if l and not dfhack.units.isDead(l) then return l end
            end
            return u
        end
    end
end
function Win:act_live_centre()
    local grp = self:curGroup(); if not grp then self:setLiveStatus('Select a tracked group row first.') return end
    local u = firstLive(grp); if not u then self:setLiveStatus(grp.token .. ': no live member to centre on.') return end
    dfhack.gui.revealInDwarfmodeMap(u.pos, true, true)
    self:setLiveStatus(('Centred on %s x%d at %d,%d,%d.'):format(grp.token, #grp.ids, u.pos.x, u.pos.y, u.pos.z))
end
function Win:act_live_follow()
    local grp = self:curGroup(); if not grp then self:setLiveStatus('Select a tracked group row first.') return end
    local u = firstLive(grp); if not u then self:setLiveStatus(grp.token .. ': no live member to follow.') return end
    dfhack.gui.revealInDwarfmodeMap(u.pos, true, true)   -- first: DFHack's recentre clears the follow fields
    setField(df.global.plotinfo, 'follow_item', -1)
    setField(df.global.plotinfo, 'follow_unit', u.id)     -- DF's own camera follow, the way gui/sitemap does it
    self:setLiveStatus(('Following %s #%d (%s). Esc in the map view stops following.'):format(grp.token, u.id, grp.leader == u.id and 'leader' or 'member'))
end
function Win:act_live_hold()
    local grp = self:curGroup(); if not grp then self:setLiveStatus('Select a tracked group row first.') return end
    local n = holdGroup(grp, 30); saveGroups(self._liveG); self:refreshLive()
    self:setLiveStatus(('Held %s x%d for 30 days: %d countdown(s) raised.'):format(grp.token, #grp.ids, n))
end
function Win:act_live_dismiss()
    local grp = self:curGroup(); if not grp then self:setLiveStatus('Select a tracked group row first.') return end
    local n = dismissGroup(grp); saveGroups(self._liveG); self:refreshLive()
    self:setLiveStatus(('Dismissed %s x%d: %d countdown(s) zeroed; DF refunds the entry when they leave.'):format(grp.token, #grp.ids, n))
end
function Win:act_live_coupling()
    self._lastAction = 'coupling'
    self.cfg.groups.coupling = not self.cfg.groups.coupling; self:save()
    LEDGER.add('edit', '', 'migratory coupling %s', self.cfg.groups.coupling and 'on' or 'off')
    self:refreshLive(); self:setLiveStatus('Migratory coupling ' .. (self.cfg.groups.coupling and 'ON.' or 'off.'))
end
local PACK_STEPS = { 0, 3, 5, 8, 12 }
function Win:act_live_pack()
    self._lastAction = 'pack size'
    local cur, nxt = self.cfg.groups.pack or 0, PACK_STEPS[1]
    for i, v in ipairs(PACK_STEPS) do if v == cur then nxt = PACK_STEPS[i + 1] or PACK_STEPS[1] end end
    self.cfg.groups.pack = nxt; self:save()
    LEDGER.add('edit', '', 'coupling pack size %s', nxt > 0 and tostring(nxt) or 'raw')
    self:refreshLive(); self:setLiveStatus('Coupling pack size: ' .. (nxt > 0 and tostring(nxt) or 'raw default') .. '.')
end
function Win:act_live_nextwave()
    self:act_force()   -- v6.5.0: the Roster's Ctrl+F -- send off the gated groups, then the next
    self:refreshLive()
    self:setLiveStatus('Sent off the gated land groups; the next wave comes within a day of play.')
end
-- v5.11.4: the Ledger tab
local KIND_PEN = { edit=COLOR_WHITE, season=COLOR_LIGHTGREEN, wave=COLOR_LIGHTCYAN, arrive=COLOR_CYAN, coupling=COLOR_LIGHTRED, ecology=COLOR_RED,
                   hold=COLOR_YELLOW, dismiss=COLOR_YELLOW, sweep=COLOR_GREY, place=COLOR_LIGHTBLUE, cavern=COLOR_BROWN, fuse=COLOR_LIGHTMAGENTA,
                   build=COLOR_LIGHTGREEN, undo=COLOR_MAGENTA, irruption=COLOR_LIGHTRED,
                   -- v7.1 (fixes2): the kinds the v7.1 streams added
                   roster=COLOR_LIGHTGREEN, adopt=COLOR_CYAN, call=COLOR_LIGHTCYAN, size=COLOR_GREY, eco=COLOR_RED, lead=COLOR_YELLOW,
                   panic=COLOR_LIGHTRED, bodies=COLOR_LIGHTBLUE, extinct=COLOR_BROWN }   -- v7.1-place: 'strand' went with the guard
function Win:setLedgerStatus(msg) self.subviews.ledger_status:setText({ { text=msg, pen=COLOR_LIGHTCYAN } }) end
function Win:refreshLedger()
    local kind = self.subviews.led_kind and self.subviews.led_kind:getOptionValue() or 'all'
    local layer = self.subviews.led_layer and self.subviews.led_layer:getOptionValue() or 'all'
    local ll, total = LEDGER.lines(200, kind ~= 'all' and kind or nil, layer ~= 'all' and layer or nil)
    local lines = {}
    self.subviews.ledger_hdr:setText({ { text=('%d of %d recorded%s%s   (newest last)'):format(#ll, total, kind ~= 'all' and ('  kind=' .. kind) or '', layer ~= 'all' and ('  layer=' .. layer) or ''), pen=COLOR_YELLOW } })
    for _, l in ipairs(ll) do
        local k = l:match('^%S+ %S+ %d+%s+(%S+)')
        lines[#lines+1] = { text={ { text=l, pen=KIND_PEN[k] or COLOR_GREY } } }
    end
    if #ll == 0 then lines[#lines+1] = { text={ { text='  (nothing recorded under this filter)', pen=COLOR_DARKGREY } } } end
    lines = self:wrap(lines, self.subviews.ledger)   -- v7.1 (ui): a long ledger line wraps instead of running off the edge
    self.subviews.ledger:setChoices(lines)
    self.subviews.ledger:setSelected(#lines)
end
function Win:act_undo()
    local label, left = UNDO.pop(self.cfg)
    if not label then self:setLedgerStatus('Nothing to undo.') return end
    saveConfig(self.cfg)
    if UNDO.after then UNDO.after(self.cfg) end   -- v7.1 (Alpha Four 6.8): raws and jobs follow the restored config
    self.cfg = loadConfig(); self._before = loadConfig()
    self:rebuildData(); self:refresh(); self:refreshLedger()
    self:setLedgerStatus(('Undid: %s. %d more to undo.'):format(label, left))
end
-- v5.11.3: the Layers tab
function Win:setLayersStatus(msg) self.subviews.layers_status:setText({ { text=msg, pen=COLOR_LIGHTCYAN } }) end
function Win:curLayer() return self.subviews.lay_sel and self.subviews.lay_sel:getOptionValue() or 'land' end
function Win:refreshLayers()
    local cfg, lines = self.cfg, {}
    local colW, cols = 17, { 'land', 'water', 'cavern', 'deep' }   -- v6.5.0: the deep layer; v7.1 (ui): 18 + 4 x 17 = 86 columns (was 96)
    local function row(label, vals, pen)
        local r = { { text=('%-18s'):format(label:sub(1, 17)), pen=COLOR_WHITE } }
        for i, l in ipairs(cols) do
            local v = vals[i] or ''
            r[#r+1] = { text=('%-' .. colW .. 's'):format(tostring(v):sub(1, colW - 1)), pen=(l == self:curLayer()) and (pen or COLOR_LIGHTGREEN) or (pen or COLOR_GREY) }
        end
        lines[#lines+1] = { text=r }
    end
    local hdr = { { text=('%-18s'):format('') } }
    for _, l in ipairs(cols) do hdr[#hdr+1] = { text=('%-' .. colW .. 's'):format(l:upper() .. (l == self:curLayer() and ' <' or '')), pen=l == self:curLayer() and COLOR_YELLOW or COLOR_WHITE } end
    lines[#lines+1] = { text=hdr }
    -- v6.5.0 (W4, Q6): one set of controls on every layer; which driver serves a layer is a note, not a difference
    local L = cfg.limits
    local function ceil(n) return n > 0 and tostring(n) or 'none' end
    row('layer', { cfg.layers.land and 'on' or 'off', cfg.layers.water and 'on' or 'off', cfg.layers.cavern and 'on' or 'off', cfg.layers.deep and 'on' or 'off' })
    row('drawn by', { 'DF (gated)', 'the tool', 'DF (gated)', 'DF (frequency)' })
    -- v7.1 (ui; R7, Alpha Three 11.3/11.4): the caps the engine uses (QUOTA.groupsFor), not the stored per-layer number
    -- v7.1 retired; water's is per body, a cavern's per cavern. C sets the one fixed cap or goes back to the formula.
    local fixed = L.mode == 'fixed'
    local how = fixed and 'fixed' or 'map size'
    row('group cap', { ('%d (%s)'):format(QUOTA.groupsFor(cfg, 'land'), how), ('%d/body, %s'):format(QUOTA.groupsFor(cfg, 'water'), how),
        cfg.groups.cavern and ('%d/cavern'):format(QUOTA.groupsFor(cfg, 'cavern')) or 'DF\'s own', '-' })
    row('ceiling', { ceil(L.land.ceiling), ceil(L.water.ceiling), ceil(L.cavern.ceiling), '-' })
    local gc = cfg.groups
    local clock = gc.adaptive and ('adapt %g-%dd'):format(gc.gap_floor_days, gc.gap_max_days) or ('%d-%d days'):format(gc.gap_min_days, gc.gap_max_days)
    row('release clock', { clock, clock, clock, '-' })
    row('pattern', { PATTERN.name(cfg, 'land'), PATTERN.name(cfg, 'water'), PATTERN.name(cfg, 'cavern'), '-' })
    row('coupling', { cfg.groups.coupling and 'on' or 'off', cfg.groups.coupling and 'on' or 'off', cfg.groups.coupling and 'on' or 'off', '-' })
    row('cohesion', { cfg.groups.cohesion and 'herd/pack/flock' or 'off', cfg.groups.cohesion and 'school' or 'off', cfg.groups.cohesion and 'herd/pack/flock' or 'off', '-' })
    row('ecology switch', { cfg.ecology.enabled and 'on' or 'off', cfg.ecology.enabled and 'on' or 'off', cfg.ecology.enabled and 'on' or 'off', '-' })
    row('nudge after', { ('%d t, %d tiles'):format(cfg.ecology.far_ticks, cfg.ecology.far_tiles), 'through water', 'in the cavern', '-' })
    row('pack size', { cfg.groups.pack > 0 and cfg.groups.pack or 'raw', cfg.groups.pack > 0 and cfg.groups.pack or 'raw', cfg.groups.pack > 0 and cfg.groups.pack or 'raw', '-' })
    local _, gg = groupsStatus()
    row('irruptions', { '-', '-', cfg.irruption.enabled and ('on, at %.2f'):format(cfg.irruption.threshold) or 'off (I)' }, cfg.irruption.enabled and COLOR_LIGHTRED or COLOR_DARKGREY)
    row('cavern pressure', { '-', '-', cfg.irruption.enabled and ('%.2f %.2f %.2f'):format(IRRUPT.pressure(gg, 0), IRRUPT.pressure(gg, 1), IRRUPT.pressure(gg, 2)) or '-' }, cfg.irruption.enabled and COLOR_LIGHTRED or COLOR_DARKGREY)
    lines[#lines+1] = { text='' }
    -- v7.1-perf2 (validate-full 20261002-231032, --only w0: refreshLayers 233 ms, the water line finishing the load-time
    -- survey): nowait; while the survey runs the line says so and onRenderFrame refreshes the tab when it ends
    local P = sw.V7 and sw.V7.PERF
    if P and P.warming and P.warming() then self._warmWait = true end
    lines[#lines+1] = { text={ { text=WATER.status(cfg, true), pen=cfg.layers.water and COLOR_LIGHTCYAN or COLOR_DARKGREY } } }
    -- the caverns: found or hidden, their roster and their groups
    local found = cavernsFound()
    local _, g = groupsStatus()
    local nRoster = 0
    for _, e in ipairs(self.pool) do if e.inEmbark and e.layer == 'cavern' and isAllowed(cfg, e) then nRoster = nRoster + 1 end end
    lines[#lines+1] = { text={ { text=('Caverns: layer %s   %d cavern species in the roster   %s'):format(cfg.layers.cavern and 'on' or 'off', nRoster, CAVERN.status(cfg)), pen=COLOR_YELLOW } } }
    for d = 0, 2 do
        local f = found[d]
        local ng = 0
        for _, grp in ipairs(g.groups) do if grp.layer == 'cavern' and grp.depth == d then ng = ng + 1 end end
        local txt
        if f == nil then txt = ('  Cavern %d   not on this map'):format(d + 1)
        -- v7.1 (ui; fixes.md section 6): the phase is IRRUPT v2's per cavern (g.armed is never set since v7.1)
        elseif f then txt = ('  Cavern %d   found   %s   %d group(s) on the map   pressure %s'):format(d + 1, cfg.layers.cavern and 'managed' or 'layer off', ng,
            cfg.irruption.enabled and (('%.2f  '):format(IRRUPT.pressure(g, d)) .. IRRUPT.phaseText(cfg, g, d, false)) or '- (irruptions off)')
        else txt = ('  Cavern %d   not yet found  (nothing shown until your dwarves reach it)'):format(d + 1) end
        lines[#lines+1] = { text={ { text=txt, pen=f and COLOR_GREY or COLOR_DARKGREY } } }
    end
    lines[#lines+1] = { text='' }
    lines[#lines+1] = { text={ { text=('preset: %s   (R re-applies it: natural species allowed, matrix seasons, co-aligned, vermin defaults)'):format(presetName(self.biomeSet)), pen=COLOR_GREY } } }
    self.subviews.layers:setChoices(self:wrap(lines, self.subviews.layers))
    if self._firstRunMsg then self:setLayersStatus(self._firstRunMsg) end
end
local PATTERN_ORDER = { 'steady', 'burst', 'trickle', 'dawn', 'follow' }
function Win:act_lay_pattern()
    self._lastAction = 'pattern'
    local l = self:curLayer()
    if l == 'deep' then self:setLayersStatus('The deep layer has no gate, so no pattern.') return end
    local cur, nxt = PATTERN.name(self.cfg, l), PATTERN_ORDER[1]
    for i, v in ipairs(PATTERN_ORDER) do if v == cur then nxt = PATTERN_ORDER[i + 1] or PATTERN_ORDER[1] end end
    self.cfg.patterns[l] = nxt; self:save(); LEDGER.add('edit', l, 'pattern %s', nxt)
    if l == 'land' then PATTERN.trickleApply(self.cfg, true) end
    self:refreshLayers(); self:setLayersStatus(('%s pattern: %s%s'):format(l, nxt, (l == 'cavern' and nxt ~= 'steady') and ' (the cavern gate takes steady until v6.1)' or ''))
end
-- v6.5.0 (W4, Q6): the ceiling and groups at once, the same two limits on every layer
function Win:act_lay_quota()
    self._lastAction = 'ceiling'
    local l = self:curLayer()
    if l == 'deep' then self:setLayersStatus('The deep layer is steered by frequency alone: no ceiling there.') return end
    dialogs.showInputPrompt('Ceiling', ('The most wild animals of the %s layer on the map at once (0 = none):'):format(l), COLOR_WHITE, tostring(self.cfg.limits[l].ceiling),
        function(txt) local n = tonumber(txt); if n and n >= 0 then sw.QUOTA.set(self.cfg, l, 'ceiling', n); self:save(); LEDGER.add('edit', l, '%s ceiling %d', l, self.cfg.limits[l].ceiling); self:refreshLayers(); self:setLayersStatus(('%s ceiling: %s.'):format(l, n > 0 and tostring(math.floor(n)) or 'none')) end end)
end
function Win:act_lay_onoff()
    self._lastAction = 'layer on/off'
    local l = self:curLayer()
    self.cfg.layers[l] = not self.cfg.layers[l]; self:save(); LEDGER.add('edit', l, 'layer %s', self.cfg.layers[l] and 'on' or 'off')
    self:rebuildData(); self:refreshLayers(); self:setLayersStatus(('%s layer %s.'):format(l, self.cfg.layers[l] and 'ON' or 'off'))
end
-- v7.1 (ui; R7, Alpha Three 11.4): one cap for every layer or the map-size formula. The per-layer prompt stored a
-- number the engine no longer reads (and never turned auto off). Through the registry, so the console verb runs.
function Win:act_lay_concurrent()
    self._lastAction = 'group cap'
    local cur = self.cfg.limits.mode == 'fixed' and tostring(self.cfg.limits.fixed or 3) or 'auto'
    dialogs.showInputPrompt('Group cap (every layer)', 'A number: one fixed cap on every layer (for slower computers).\nauto: the map-size formula (each layer its own; caverns keep theirs).',
        COLOR_WHITE, cur, function(txt)
            txt = (txt or ''):gsub('%s', '')
            local id, v = 'limits.fixed', txt
            if txt == '' or txt == 'auto' or txt == 'formula' then id, v = 'limits.mode', 'formula' end
            local _, out = self:ctlSet(id, v)
            self:refreshLayers(); self:setLayersStatus(out)
        end)
end
-- One registry set from any tab: the verb runs, the window reloads the config it wrote, the result is one line.
function Win:ctlSet(id, v, tok)
    local C = PNL.ctl
    if not C then return false, 'The control registry did not load: ' .. tostring(PNL.err) end
    local r = C.find(id)
    local ok, out, cmd, now = C.set(id, tostring(v), tok)
    self.cfg = loadConfig(); self._before = loadConfig()
    local msg = ok and ('%s: %s (read back)'):format(r and r.label or id, PNL.valText(r, now)) or ('Refused: ' .. PNL.firstLine(out))
    return ok, msg, cmd
end
function Win:act_lay_gap()
    self._lastAction = 'gap days'
    dialogs.showInputPrompt('Gap between waves', 'land: min and max days between releases (e.g. 5 20):', COLOR_WHITE, ('%d %d'):format(self.cfg.groups.gap_min_days, self.cfg.groups.gap_max_days),
        function(txt) local a, b = txt:match('^%s*(%d+)%s+(%d+)%s*$'); a, b = tonumber(a), tonumber(b)
            if a and b and a >= 1 and b >= a then self.cfg.groups.gap_min_days, self.cfg.groups.gap_max_days = a, b; self:save(); LEDGER.add('edit', 'land', 'gap %d-%d days', a, b); self:refreshLayers(); self:setLayersStatus(('land gap: %d-%d days.'):format(a, b)) end end)
end
function Win:act_lay_ecology()
    self._lastAction = 'ecology switch'
    self.cfg.ecology.enabled = not self.cfg.ecology.enabled; self:save()
    if self.cfg.groups.enabled and self.cfg.enabled then enableGroups() end   -- reschedules the ecology job on or off
    LEDGER.add('edit', '', 'ecology %s', self.cfg.ecology.enabled and 'on' or 'off')
    self:refreshLayers(); self:setLayersStatus('Ecology switch ' .. (self.cfg.ecology.enabled and 'ON.' or 'off.'))
end
function Win:act_lay_nudge()
    self._lastAction = 'nudge'
    dialogs.showInputPrompt('Nudge', 'tiles ticks radius (e.g. 40 3000 6):', COLOR_WHITE, ('%d %d %d'):format(self.cfg.ecology.far_tiles, self.cfg.ecology.far_ticks, self.cfg.ecology.radius),
        function(txt) local a, b, c = txt:match('^%s*(%d+)%s+(%d+)%s+(%d+)%s*$'); a, b, c = tonumber(a), tonumber(b), tonumber(c)
            if a and b and c then self.cfg.ecology.far_tiles, self.cfg.ecology.far_ticks, self.cfg.ecology.radius = a, b, c; self:save(); LEDGER.add('edit', '', 'nudge after %d tiles / %d t to within %d', a, b, c); self:refreshLayers(); self:setLayersStatus(('nudge: after %d ticks more than %d tiles apart, to within %d.'):format(b, a, c)) end end)
end
-- v7.1 (ui; fixes.md section 6): through `irruption on|off`, whose off undoes every IRRUPT v2 write at once
-- (IRRUPT.restoreAll); the old toggle undid only a v7.0 g.armed group, which v7.1 never sets.
function Win:act_lay_irruption()
    self._lastAction = 'irruptions'
    local on = not self.cfg.irruption.enabled
    local ok, out = self:ctlSet('irruption.enabled', on and 'on' or 'off')
    self:refreshLayers()
    self:setLayersStatus(not ok and out or (on and ('Irruptions ON: cavern pressure from your dwarves; past %.2f a warning, then waves (Panel: Irruptions).'):format(self.cfg.irruption.threshold)
        or 'Irruptions off; every irruption write undone.'))
end
function Win:act_lay_preset()
    self:confirm('Re-apply the preset', 'Rewrite the whole roster: every natural species on the embark active\nwith one season from the climate matrix, every present layer on, rotation on.\nZ on the Ledger undoes it. Go ahead?', function()
        self._lastAction = 'preset'
        local name, allowed, _, layerNote = applyPreset(self.cfg, self.pool, self.biomeSet); self:save()
        enableSched(); self.cfg = loadConfig(); self._before = loadConfig()
        self:rebuildData(); self:refresh(); self:refreshLayers()
        self:setLayersStatus(('Preset re-applied: %d active, one season each; rotation on; %s. Biomes: %s.'):format(allowed, layerNote, name))   -- outcome first: the row clips (see _firstRunMsg)
    end)
end
function Win:act_groups()
    if self.cfg.groups.enabled then disableGroups() else enableGroups() end
    self.cfg = loadConfig()
    self:refreshLive()
end

--========================================================================================
-- Seasons tab: four columns, arrivals and departures marked
--========================================================================================
function Win:refreshSeasons()
    local lines = {}
    local colW = 15   -- v5.8.5: 22 + 4x18 = 94 columns overran the 86-wide window and clipped 'Winter' to 'Wint'
    local hdr = { { text=('%-22s'):format('') } }
    for sn = 0, 3 do hdr[#hdr+1] = { text=('%-' .. colW .. 's'):format(SEASON[sn]), pen=SEASON_PEN[sn] } end
    lines[#lines+1] = { text=hdr }
    for _, lv in ipairs(LEVELS) do
        -- tokens present per season at this level
        local present, ent = {}, {}
        for sn = 0, 3 do
            present[sn] = {}
            for _, e in ipairs(self.pool) do
                if e.inEmbark and lv.match(e) and isAllowed(self.cfg, e) and inSeason(self.cfg, e.key, sn) and self:layerOk(e.viewLayer or e.layer) then present[sn][e.token] = true; ent[e.token] = ent[e.token] or e end
            end
        end
        -- one row per token that appears in any season
        local toks = {}
        for sn = 0, 3 do for t in pairs(present[sn]) do toks[t] = true end end
        local sorted = {}; for t in pairs(toks) do sorted[#sorted+1] = t end; table.sort(sorted)
        if #sorted > 0 then
            lines[#lines+1] = { text={ { text=lv.name, pen=lv.pen } } }
            for _, t in ipairs(sorted) do
                local row = { { text=('  %-20s'):format(t:sub(1, 20)) } }
                for sn = 0, 3 do
                    local here, prev, nxt = present[sn][t], present[(sn+3)%4][t], present[(sn+1)%4][t]
                    local mark = here and ((not prev) and '+' or ((not nxt) and '-' or 'X')) or '.'
                    local pen = here and ((not prev) and COLOR_LIGHTGREEN or ((not nxt) and COLOR_YELLOW or SEASON_PEN[sn])) or COLOR_DARKGREY
                    row[#row+1] = { text=('%-' .. colW .. 's'):format(mark), pen=pen }
                end
                lines[#lines+1] = { text=row, entry=ent[t] }
            end
        end
    end
    local sel = self.subviews.seasons:getSelected()
    self.subviews.seasons:setChoices(lines)
    if sel then self.subviews.seasons:setSelected(math.min(sel, #lines)) end
end

function Win:act_seasons_tab(sn)
    local _, c = self.subviews.seasons:getSelected()
    local e = c and c.entry
    if not e then self.subviews.seasons_status:setText({ { text='Select a species row first.', pen=COLOR_YELLOW } }) return end
    self._lastAction = 'season toggle'
    local ok, why = toggleSeason(self.cfg, e.key, sn)
    if ok then self:save(); self:refreshSeasons(); self:refresh() end
    self.subviews.seasons_status:setText({ { text=ok and ('%s: %s'):format(e.token, seasonLabel(self.cfg, e.key)) or ('%s: %s'):format(e.token, why), pen=ok and COLOR_LIGHTCYAN or COLOR_YELLOW } })
end

--========================================================================================
-- Roster-shaping actions (v4.0 Set roster tab; on the Roster since v5.11.0): targets, fills, matrix, co-align
--========================================================================================

-- v6.3.0 (W9, alpha 1 step 7.6): every action that rewrites many species asks first
function Win:confirm(title, text, fn)
    dialogs.showYesNoPrompt(title, text, COLOR_YELLOW, fn)
end
function Win:act_season(sn)   -- v5.11.0: S/U/A/W flip one season on the selected Roster row (was the Set roster grid)
    self._lastAction = 'season toggle'
    local e = self:curEntry(); if not e then return end
    local ok, why = toggleSeason(self.cfg, e.key, sn)
    if not ok then self:setStatus(('%s: %s.'):format(e.token, why)) return end
    self:save(); self:refresh()
    self:setStatus(('%s: %s'):format(e.token, seasonLabel(self.cfg, e.key)))
end
function Win:act_fill_targets()
    local l, parts = self:targetLayer(), {}
    for _, cat in ipairs(TARGET_CATS) do if self:targetFor(cat) > 0 then parts[#parts+1] = ('%s %d'):format(cat, self:targetFor(cat)) end end
    if #parts == 0 then self:setStatus(('No target set on the %s layer: Shift-P/R/V set one; F leaves unset categories alone.'):format(l)) return end
    self:confirm('Fill to targets', ('On the %s layer, make species active or inactive at random until\n  %s\nCategories without a target are left alone. Go ahead?'):format(l, table.concat(parts, ', ')), function()
        self._lastAction = 'fill to targets'
        local total, out = 0, {}
        for _, cat in ipairs(TARGET_CATS) do
            local n, how = fillCategory(self.cfg, self.pool, cat, self:targetFor(cat), self.marsupialEmbark, l)
            if n > 0 then total = total + n; out[#out+1] = ('%s %d %s'):format(how, n, cat) end
        end
        self:save(); self:refresh()
        self:setStatus(total > 0 and table.concat(out, ', ') or 'Targets already met.')
    end)
end
function Win:act_fill_prey()
    self:confirm('Fill natural prey', 'For every active predator with no active prey, make one natural prey\nactive (one season each). Go ahead?', function()
        self._lastAction = 'fill natural prey'
        local n = fillPartners(self.cfg, self.pool, 'prey')
        self:save(); self:refresh()
        self:setStatus(('Made %d natural prey active.'):format(n))
    end)
end
function Win:act_fill_predators()
    self:confirm('Fill natural predators', 'For every active prey with no active predator, make one natural predator\nactive (one season each). Go ahead?', function()
        self._lastAction = 'fill natural predators'
        local n = fillPartners(self.cfg, self.pool, 'predators')
        self:save(); self:refresh()
        self:setStatus(('Made %d natural predators active.'):format(n))
    end)
end
function Win:act_assign_matrix()
    self:confirm('Matrix assign', 'Give EVERY active species exactly one season from the climate matrix,\nreplacing the seasons it has now. Z on the Ledger undoes it. Go ahead?', function()
        self._lastAction = 'matrix assign'
        local n = assignFromMatrix(self.cfg, self.pool)
        self:save(); self:refresh()
        self:setStatus(('One season each for %d active species.'):format(n))
    end)
end
function Win:act_coalign()
    self:confirm('Co-align', 'Give each predator or prey that shares no season with a partner ONE\nextra season next to one it has. Go ahead?', function()
        self._lastAction = 'co-align'
        local n = coAlignSeasons(self.cfg, self.pool)
        self:save(); self:refresh()
        self:setStatus(('Co-align: %d partner(s) given one adjacent season.'):format(n))
    end)
end

function Win:curEntry() local _, c = self.subviews.list:getSelected(); return c and c.entry end
function Win:act_toggle()
    self._lastAction = 'active/inactive'
    local e = self:curEntry(); if not e then return end
    local on = not isAllowed(self.cfg, e)
    ROSTER.setActive(self.cfg, self.pool, e, on)   -- v6.3.0 (D2): activation gives exactly one season
    self:save(); self:refresh()
    LEDGER.add('edit', e.layer, '%s %s%s', e.key, on and 'active' or 'inactive', on and (', ' .. seasonLabel(self.cfg, e.key)) or '')
    self:setStatus(on and ('%s active: %s.'):format(e.token, seasonLabel(self.cfg, e.key)) or ('%s inactive: it will not appear.'):format(e.token))
end
function Win:act_cycle()
    self._lastAction = 'cycle seasons'
    local e = self:curEntry(); if not e then return end
    cycleSeason(self.cfg, e.key); self:save(); self:refresh()   -- cycleSeason records 'you: seasons'
    self:setStatus(('%s: %s'):format(e.token, seasonLabel(self.cfg, e.key)))
end
function Win:act_apply()
    if not dfhack.isMapLoaded() then return end
    local n = applyLive(self.cfg, df.global.cur_season)
    self:rebuildData(); self:refresh()
    self:setStatus(('Applied %s live: %d active.'):format(SEASON[df.global.cur_season], n))
    announce(('%s wildlife applied (%d active).'):format(SEASON[df.global.cur_season], n), COLOR_LIGHTGREEN)
end
-- v6.5.0 (W10, alpha 1 steps 4.2 and 7.2): send off, then the next. Force wave used to run fix/wildlife and
-- `force Wildlife`; the group on the map stayed and the next came on top of it -- the trial's pile-up. Now
-- every gated land group gets a zero leave countdown and its gate cleared; DF sends the next within ~450 ticks.
function Win:act_force()
    local g = loadGroups()
    local n = ENGINE.sendOff(g, 'land'); saveGroups(g)
    LEDGER.add('dismiss', 'land', 'sent off %d gated group(s); the gate is open for the next', n)
    self:setStatus(('Sent off %d group(s); the gate is open -- the next wave comes within a day of play.'):format(n))
end
function Win:act_dryrun()
    -- allowed, in-embark creatures sorted by category then token
    local rows = {}
    for _, e in ipairs(self.pool) do if e.inEmbark and isAllowed(self.cfg, e) then rows[#rows+1] = e end end
    table.sort(rows, function(a, b) if a.cat ~= b.cat then return a.cat < b.cat end return a.token < b.token end)
    local choices = { { text={ { text=('%-20s'):format('CREATURE'), pen=COLOR_GREY },
        { text='Sp Su Au Wi', pen=COLOR_GREY, gap=1 } } } }
    for _, e in ipairs(rows) do
        local toks = { { text=(CAT_ICON[e.cat] or '?')..' '..e.token, width=20, pad_char=' ' } }
        for s = 0, 3 do
            local on = inSeason(self.cfg, e.key, s)
            toks[#toks+1] = { gap=1, text=on and 'X ' or '- ', width=2, rjustify=false,
                              pen=on and SEASON_PEN[s] or COLOR_DARKGREY }
        end
        choices[#choices+1] = { text=toks, search_key=e.cat..' '..e.token }
    end
    dialogs.ListBox{ frame_title='Dry-run -- season table (by type)', with_filter=true, choices=choices }:show()
end
-- v6.5.0 (W5, Q3): STOCK -- the reserve in the region, debited one per arrival, refunded as animals leave, 0 meaning
-- none left to come. It is not a proportion lever (E3: DF's pick ignores it; E24: it does not size a wave): that
-- is ODDS, a separate control.
function Win:act_weight()
    self._lastAction = 'stock'
    local e = self:curEntry(); if not e then return end
    dialogs.showInputPrompt('Stock for '..e.token,
        'How many remain in the region to arrive (0 = none left). Blank = the region\'s own.\n'..
        'Stock does not change how often it is chosen: that is its odds (Alt+O).', COLOR_WHITE,
        tostring(self.cfg.stock[e.key] or self:stockOf(e.key)),
        function(txt)
            local n = tonumber(txt)
            if txt == '' then self.cfg.stock[e.key] = nil
            elseif n and n >= 0 then self.cfg.stock[e.key] = math.floor(n) else return end
            if self.cfg.stock[e.key] and ROSTER.wants(self.cfg, e.key, df.global.cur_season) then RESERVE.set(e.key, self.cfg.stock[e.key]) end
            LEDGER.add('edit', e.layer, '%s stock %s', e.key, self.cfg.stock[e.key] and tostring(self.cfg.stock[e.key]) or 'back to the region\'s own')
            self:save(); self:refresh()
            self:setStatus(('%s stock: %s.'):format(e.token, self.cfg.stock[e.key] and tostring(self.cfg.stock[e.key]) or 'the region\'s own'))
        end)
end
function Win:act_weight_filter()
    self._lastAction = 'stock (filter)'
    local vis = self:filteredEntries()
    dialogs.showInputPrompt(('Stock for %d filtered species'):format(#vis),
        'Every row shown (View/Cat/Biome/Season filter) gets this stock; blank = the region\'s own.', COLOR_WHITE, '',
        function(txt)
            local n = tonumber(txt)
            if txt ~= '' and not (n and n >= 0) then return end
            for _, e in ipairs(vis) do
                self.cfg.stock[e.key] = (txt ~= '') and math.floor(n) or nil
                if self.cfg.stock[e.key] and ROSTER.wants(self.cfg, e.key, df.global.cur_season) then RESERVE.set(e.key, self.cfg.stock[e.key]) end
            end
            self:save(); self:refresh(); self:setStatus(('Set %d stocks to %s.'):format(#vis, txt ~= '' and txt or 'the region\'s own'))
            LEDGER.add('edit', '', '%d stock(s) set to %s', #vis, txt ~= '' and txt or 'their own')
        end)
end
-- v6.5.0 (W5, Q3): ODDS -- the species' weight when its layer gets a wave (the raw's FREQUENCY), shown as a share
function Win:act_odds()
    self._lastAction = 'odds'
    local e = self:curEntry(); if not e then return end
    local w, share = ODDS.share(self.cfg, self.pool, e)
    dialogs.showInputPrompt('Odds for '..e.token,
        ('Its weight when the %s layer gets a wave; now %d, %.0f%% of the layer. At least 1.\nBlank = the raw\'s own. Stock is separate (Ctrl+W).'):format(e.layer, w, share), COLOR_WHITE,
        tostring(self.cfg.odds[e.key] or w),
        function(txt)
            local n = tonumber(txt)
            if txt == '' then self.cfg.odds[e.key] = nil elseif n and n >= 1 then self.cfg.odds[e.key] = math.floor(n) else return end
            self:save()
            if self.cfg.enabled then sw.CAVERN.apply(self.cfg, df.global.cur_season) end
            LEDGER.add('edit', e.layer, '%s odds %s', e.key, self.cfg.odds[e.key] and tostring(self.cfg.odds[e.key]) or 'back to the raw\'s')
            self:refresh()
            local w2, share2 = ODDS.share(self.cfg, self.pool, e)
            self:setStatus(('%s odds: weight %d, %.0f%% of the %s layer.'):format(e.token, w2, share2, e.layer))
        end)
end
function Win:act_enable()
    self._lastAction = 'auto rotation'
    if self.cfg.enabled then disableSched() else enableSched() end
    self.cfg = loadConfig(); self:refresh(); self:setStatus(self.cfg.enabled and 'Seasonal rotation ON.' or 'Seasonal rotation off.')
end
function Win:act_addnew()
    self._lastAction = 'add-new'
    if self.subviews.viewmode:getOptionValue() ~= 'add' then
        self:setStatus("Switch View: to 'Add invasive' and pick a creature the regions do not have first."); return
    end
    local e = self:curEntry(); if not e then return end
    dialogs.showInputPrompt('Add '..e.token..' to region wildlife',
        'Worldgen population as min-max (default 50-100).', COLOR_WHITE, '50-100',
        function(txt)
            local a, b = txt:match('^%s*(%d+)%s*-%s*(%d+)%s*$')
            if not a then a = txt:match('^%s*(%d+)%s*$'); b = a end
            local cmin, cmax = tonumber(a) or 50, tonumber(b) or 100
            if cmax < cmin then cmin, cmax = cmax, cmin end
            local n, why = addNewSpecies(self.cfg, e.token, cmin, cmax)
            if n > 0 then
                self:rebuildData()
                -- v6.7.0 (alpha 2, step 8.1): the roster is made whole at once, so the new species is active with one
                -- season (or inactive) the moment it exists, not at the next window open or load
                ROSTER.normalize(self.cfg, self.pool)
                self:save()
                self:refresh()
                local got = self.cfg.assign[e.key]
                self:setStatus(('%s added to %d region(s) (%d-%d), live: %s%s. Enter makes it inactive.')
                    :format(e.token, n, cmin, cmax, self.cfg.allow[e.key] and 'active' or 'inactive', got and #got > 0 and (', ' .. seasonLabel(self.cfg, e.key)) or ''))
                announce(e.token..' added to the embark wildlife.', COLOR_LIGHTCYAN)
            else
                self:setStatus('Could not add '..e.token..': '..(why or 'no matching region'))
            end
        end)
end
function Win:act_fill()
    self._lastAction = 'fill cat to N'
    local cat = self.subviews.category:getOptionValue()
    if cat == 'all' or tostring(cat):sub(1, 4) == 'hab:' then
        self:setStatus('Pick a specific Cat (predator/prey/vermin) first, then Fill.'); return
    end
    dialogs.showInputPrompt(('Fill %s to N'):format(cat),
        'Target count. Makes eligible '..cat..' active or inactive at random to reach it'
        ..(self.marsupialEmbark and ' (marsupials preferred).' or '.'),
        COLOR_WHITE, '3',
        function(txt)
            local n = tonumber(txt)
            if not n then return end
            local changed, how = fillCategory(self.cfg, self.pool, cat, math.max(0, math.floor(n)), self.marsupialEmbark, self.layer)
            self:save(); self:refresh()
            self:setStatus(('%s %d %s to reach %d (%s layer).'):format(how, changed, cat, n, self.layer))
        end)
end
-- v6.3.0 (W1, W9): reset in two levels, chosen in a dialog; each asks again before it writes
function Win:act_reset()
    dialogs.ListBox{
        frame_title='Reset',
        text='What to reset? Z on the Ledger undoes either.',
        choices={
            { text='The roster: every species as first found (active natural species, one season each); stock and settings kept', level='roster' },
            { text='Everything: the roster, the stock (worldgen snapshot) and every setting back to its default', level='all' },
        },
        on_select=function(_, choice)
            if choice.level == 'roster' then
                self:confirm('Reset the roster', 'Every species back to the embark as first found: natural species active,\none season each; abundances and reasons cleared. Go ahead?', function()
                    self._lastAction = 'reset roster'
                    ROSTER.resetRoster(self.cfg, self.pool); self:save(); self:rebuildData(); self:refresh()
                    self:setStatus('Roster reset to the embark as first found.')
                end)
            else
                self:confirm('Reset everything', 'The roster, every stock back to its worldgen snapshot, and every setting\n(layers, groups, patterns, quotas, ecology, targets) back to its default. Go ahead?', function()
                    self._lastAction = 'reset everything'
                    ROSTER.resetAll(self.cfg); self:save(); self:rebuildData(); self:syncTargets(); self:refresh()
                    self:setStatus('Everything reset: roster, stock and settings.')
                end)
            end
        end,
    }:show()
end


-- Vermin tab (v5.9.10): one row per family; every action is family-wide and writes the ledger
function Win:refreshVermin()
    self.pool, self.biomeSet, self.regionSet = buildPool(self.cfg)
    self._vexp = self._vexp or {}
    local rows, choices = VERMIN.rows(self.cfg, self.pool), {}
    for _, r in ipairs(rows) do
        local txt = VERMIN.rowText(r)
        if self.layer == 'all' or txt:find(self.layer, 1, true) then   -- v6.2.0: the LAYERS column names the family's layers
            local pen = r.allowed == 0 and COLOR_DARKGREY or (r.allowed == r.n and COLOR_WHITE or COLOR_YELLOW)
            choices[#choices+1] = { text={ { text=(self._vexp[r.family] and '- ' or '+ ') .. txt, pen=pen } }, row=r }
            -- v6.6.0 (W12, alpha 1 step 8.1): the family opened to its species, each with its own controls
            if self._vexp[r.family] then
                for _, e in ipairs(r.entries) do
                    local act = isAllowed(self.cfg, e)
                    local live, held = RESERVE.of(e.key)
                    choices[#choices+1] = { text={ { text=('     %-32s %-8s %-6s %-7s %s'):format(e.key:sub(1, 32), act and 'active' or 'inactive', seasonLabel(self.cfg, e.key),
                        fmtStock(live + held), e.layer), pen=act and COLOR_GREY or COLOR_DARKGREY } }, row=r, entry=e }
                end
            end
        end
    end
    if #choices == 0 then choices[1] = { text={ { text='(no vermin managed on this embark -- are the layers on?)', pen=COLOR_DARKGREY } } } end
    self.subviews.vermin:setChoices(choices)
    local note = VERMIN.coldEmbark(self.biomeSet) and 'cold embark: D gives land insects summer-autumn'
                 or 'D: land insects spring-autumn; mammals, fish, caverns, water all year'
    self.subviews.vermin_status:setText({ { text=note .. ' . not units', pen=COLOR_GREY } })   -- v7.1 (ui): within 86 columns
end
function Win:vermin_entry()
    local _, choice = self.subviews.vermin:getSelected()
    return choice and choice.entry
end
function Win:act_vermin_expand()
    local r = self:vermin_row(); if not r then return end
    self._vexp = self._vexp or {}
    self._vexp[r.family] = not self._vexp[r.family]
    self:refreshVermin()
end
function Win:vermin_row()
    local _, choice = self.subviews.vermin:getSelected()
    return choice and choice.row
end
function Win:act_vermin_toggle()
    self._lastAction = 'vermin active/inactive'
    local one = self:vermin_entry()
    if one then   -- v6.6.0 (W12): a species row acts on that species alone
        local on = not isAllowed(self.cfg, one)
        ROSTER.setActive(self.cfg, self.pool, one, on); self:save(); self:refreshVermin(); self:refresh()
        self.subviews.vermin_status:setText({ { text=('%s %s.'):format(one.key, on and ('active: ' .. seasonLabel(self.cfg, one.key)) or 'inactive'), pen=COLOR_LIGHTCYAN } })
        return
    end
    local r = self:vermin_row(); if not r then return end
    local on = r.allowed < r.n   -- any blocked -> allow the family; all allowed -> block it
    VERMIN.setAllow(self.cfg, r, on, self.pool); self:save(); self:refreshVermin(); self:refresh()
    self.subviews.vermin_status:setText({ { text=('%s: %d species %s.'):format(r.label, r.n, on and 'active, one season each' or 'inactive'), pen=COLOR_LIGHTCYAN } })
end
function Win:act_vermin_season(s)
    self._lastAction = 'vermin seasons'
    local one = self:vermin_entry()
    if one then
        local ok, why = toggleSeason(self.cfg, one.key, s)
        if ok then self:save(); self:refreshVermin() end
        self.subviews.vermin_status:setText({ { text=ok and ('%s: %s.'):format(one.key, seasonLabel(self.cfg, one.key)) or ('%s: %s.'):format(one.key, why), pen=ok and COLOR_LIGHTCYAN or COLOR_YELLOW } })
        return
    end
    local r = self:vermin_row(); if not r then return end
    local all = true
    for _, e in ipairs(r.entries) do
        local has = false
        for _, x in ipairs(self.cfg.assign[e.key] or {}) do if x == s then has = true end end
        if not has then all = false end
    end
    local kept = 0
    for _, e in ipairs(r.entries) do
        local set = {}
        for _, x in ipairs(self.cfg.assign[e.key] or {}) do set[x] = true end
        set[s] = (not all) or nil
        local arr = {}; for x in pairs(set) do arr[#arr+1] = x end
        if #arr == 0 then kept = kept + 1   -- v6.3.0 (D2): the last season stays; inactive is Enter
        else setAssign(self.cfg, e.key, arr); self.cfg.allow[e.key] = true end
    end
    LEDGER.add('edit', '', 'vermin %s: %s %s for %d species', r.family, SEASON[s], all and 'removed' or 'added', r.n - kept)
    self:save(); self:refreshVermin()
    self.subviews.vermin_status:setText({ { text=('%s: %s %s for %d species.%s'):format(r.label, SEASON[s], all and 'removed' or 'added', r.n - kept,
        kept > 0 and (' %d kept their last season (Enter makes the family inactive).'):format(kept) or ''), pen=kept > 0 and COLOR_YELLOW or COLOR_LIGHTCYAN } })
end
function Win:act_vermin_weight()   -- v6.6.0 (W11): stock, per species or for the whole family
    self._lastAction = 'vermin stock'
    local one, r = self:vermin_entry(), self:vermin_row(); if not r then return end
    local list = one and { one } or r.entries
    dialogs.showInputPrompt('Stock for ' .. (one and one.key or r.label), ('How many of each of %d species remain in the region (blank = the region\'s own).'):format(#list), COLOR_WHITE, '',
        function(txt)
            local n = tonumber(txt)
            if txt ~= '' and not (n and n >= 0) then return end
            for _, e in ipairs(list) do
                self.cfg.stock[e.key] = (txt ~= '') and math.floor(n) or nil
                if self.cfg.stock[e.key] and ROSTER.wants(self.cfg, e.key, df.global.cur_season) then RESERVE.set(e.key, self.cfg.stock[e.key]) end
            end
            self:save(); self:refreshVermin()
            self.subviews.vermin_status:setText({ { text=('%s: stock %s on %d species.'):format(one and one.key or r.label, txt ~= '' and txt or 'the region\'s own', #list), pen=COLOR_LIGHTCYAN } })
        end)
end
function Win:act_vermin_defaults()
    self._lastAction = 'vermin defaults'
    local n, cold = VERMIN.applyDefaults(self.cfg, self.pool, self.biomeSet); self:save(); self:refreshVermin()
    self.subviews.vermin_status:setText({ { text=('Seasonal defaults set on %d species%s.'):format(n, cold and ' (cold embark)' or ''), pen=COLOR_LIGHTCYAN } })
end


-- Panel tab (v6.3.0, W8): every switch with its indicator; the jobs with cadence, last and worst time, fuse
function Win:setPanelStatus(msg, pen) self.subviews.panel_status:setText({ { text=PNL.fit(PNL.ascii(msg), PNL.W), pen=pen or COLOR_LIGHTCYAN } }) end
local function overlayOn()
    local ok, on = pcall(function()
        local st = require('plugins.overlay').get_state()
        return st and st.config and st.config['seasonal-wildlife.groups'] and st.config['seasonal-wildlife.groups'].enabled
    end)
    return ok and on or false
end

--========================================================================================
-- v7.1 (ui stream; R52 R5 R7): the Panel renders the shared control registry
--========================================================================================
-- Sections on the left: the registry's twelve (switches and jobs first), then every control at once, then a search.
-- Each section opens with its readouts (one status block, cheap reads of state the engine already keeps), then its
-- controls in the registry's groups, then its actions (Enter runs; some ask first) and readouts (Enter shows the
-- console's own output). A set goes through PNL.ctl.set: checked against the row's type and range, sent as the tool's
-- console verb, and the value read back from the config the verb wrote.
PNL.SECTIONS = {
    { id='switches', label='Switches & jobs' }, { id='limits', label='Limits & groups' }, { id='caverns', label='Cavern gate' },
    { id='leaders', label='Leaders & panic' }, { id='roster', label='Roster & apexes' }, { id='ecology', label='Ecology, hunters' },
    { id='water', label='Water' }, { id='aquarium', label='Aquarium' }, { id='scavenging', label='Scavenging' }, { id='vermin', label='Vermin eating' },
    { id='extinct', label='Extinct' }, { id='v7', label='v7 switches' }, { id='irruption', label='Irruptions' },
    { id='all', label='All controls' },
}
function PNL.ascii(s) return (tostring(s or ''):gsub('[\128-\255]', '?'):gsub('[%c]', ' ')) end
function PNL.fit(s, w) s = tostring(s or ''); return #s > w and s:sub(1, math.max(0, w - 1)) .. '~' or s end
function PNL.firstLine(s) return PNL.ascii((tostring(s or ''):gsub('^%s+', ''):match('^[^\n]*') or '')) end
-- words to lines of at most w columns; a word longer than w is cut
function PNL.wrapText(s, w, indent)
    local out, line = {}, ''
    indent = indent or ''
    local a = PNL.ascii(s):gsub('%s+$', '')
    if #a <= w then return { a } end   -- a line that fits keeps its spacing (the readout tables are columns)
    for wd in PNL.ascii(s):gmatch('%S+') do
        local word = wd
        while #word > w do
            if line ~= '' then out[#out+1] = line; line = indent end
            out[#out+1] = word:sub(1, w); word = indent .. word:sub(w + 1)
        end
        if line == '' or line == indent then line = (line == indent and #out > 0) and (indent .. word) or (line .. word)
        elseif #line + 1 + #word <= w then line = line .. ' ' .. word
        else out[#out+1] = line; line = indent .. word end
    end
    if line ~= '' and line ~= indent then out[#out+1] = line end
    if #out == 0 then out[1] = '' end
    return out
end
local function num(v)
    if type(v) ~= 'number' then return tostring(v) end
    if v == math.floor(v) and math.abs(v) < 1e15 then return ('%d'):format(v) end
    return (('%.4f'):format(v):gsub('0+$', ''):gsub('%.$', ''))
end
PNL.num = num
-- the value as the row shows it: [ON]/[off] (or the row's own words), a number with its unit, a choice, 'n/a'
function PNL.valText(r, v)
    if v == nil and r and r.type == 'bool' then v = false end   -- an absent switch is off (the engine reads it so)
    if v == nil then return '-' end
    if not r then return PNL.ascii(tostring(v)) end
    if r.type == 'bool' then
        if type(v) ~= 'boolean' then return tostring(v) end
        local w = r.words
        return w and ('[' .. (v and w[1] or w[2]) .. ']') or (v and '[ON]' or '[off]')
    elseif r.type == 'int' or r.type == 'float' then
        if type(v) ~= 'number' then return tostring(v) end
        local u = r.unit
        return u and ((u == '%') and (num(v) .. '%') or (num(v) .. ' ' .. u)) or num(v)
    elseif r.type == 'enum' then
        local l = r.labels and r.labels[tostring(v)]
        return '<' .. tostring(l or v) .. '>'
    elseif r.type == 'seasons' then return v == '' and 'none' or tostring(v) end
    return PNL.ascii(tostring(v))
end
-- an eight-cell slider of a number within its range (log scale where the range spans three decades or more)
function PNL.slider(r, v)
    local lo, hi = tonumber(r.min), tonumber(r.max)
    if type(v) ~= 'number' or not lo or not hi or hi <= lo then return '' end
    local f
    if lo >= 0 and hi / math.max(lo, 1) >= 1000 then f = math.log(1 + v - lo) / math.log(1 + hi - lo)
    else f = (v - lo) / (hi - lo) end
    local n = math.max(0, math.min(8, math.floor(f * 8 + 0.5)))
    return '[' .. ('#'):rep(n) .. ('-'):rep(8 - n) .. ']'
end
function PNL.value(win, r, tok)   -- (a false is a value: `ok and v or nil` read every off switch as unset)
    local ok, v = pcall(PNL.ctl.valueOf, r, win.cfg, tok)
    if ok then return v end
    return nil
end
function PNL.same(a, b)
    if type(a) == 'number' and type(b) == 'number' then return math.abs(a - b) < 1e-6 end
    return tostring(a) == tostring(b)
end
-- the registry rows a species' detail page offers (SPECIES rows whose `when` fits the species)
function PNL.speciesRows(e)
    local C, out = PNL.ctl, {}
    if not C or not e or e.cat == 'vermin' then return out end
    local pred = e.cat == 'predator'
    local ext = sw.V7 and sw.V7.EXTINCT and sw.V7.EXTINCT.TAGS and sw.V7.EXTINCT.TAGS[e.token]
    for _, r in ipairs(C.SPECIES or {}) do
        local w = r.when
        local fits = (w == 'all') or (w == 'pred' and pred) or (w == 'raptor' and pred and e.guild == 'RP')
            or (w == 'aquatic' and pred and (e.habitat == 'aquatic' or e.habitat == 'semiaquatic' or e.aquatic)) or (w == 'extinct' and ext)
            -- v7.1-place: the water body types a species may enter (any water species, prey too)
            or (w == 'water' and (e.layer == 'water' or e.habitat == 'aquatic' or (e.waters and e.waters.bodies and next(e.waters.bodies) ~= nil)))
        if fits and C.available(r) then out[#out+1] = r end
    end
    return out
end

-- ---- readouts: each section's status block, as { text, pen } lines (wrapped to the pane by the caller) ----
local function L_(out, text, pen) out[#out+1] = { text, pen or COLOR_GREY } end
PNL.TOP = {}
-- R7: per layer key, the cap (formula or fixed), groups now, the controller's target L, W, the next release, leaders
-- and panics, from the registry's own group map (the web's Groups tab reads the same)
PNL.TOP.limits = function(_, cfg, g)
    local out, L = {}, cfg.limits
    L_(out, ('Group cap: %s'):format(L.mode == 'fixed' and ('ONE FIXED CAP of %d on every layer (caverns: the smaller of it and their own)'):format(L.fixed or 3)
        or ('MAP-SIZE FORMULA: sqrt(embark tiles) + 1 = %s on land and each water body; caverns %d each'):format(tostring(sw.QUOTA.autoGroups and sw.QUOTA.autoGroups() or '?'),
            QUOTA.groupsFor(cfg, 'cavern'))), COLOR_WHITE)
    if not dfhack.isMapLoaded() then return out end
    L_(out, ('%-12s %3s %-5s %3s %6s %5s %-10s %4s %5s'):format('layer', 'cap', 'by', 'now', 'target', 'W d', 'next', 'led', 'panic'), COLOR_LIGHTGREEN)
    for _, k in ipairs(PNL.ctl.groupMap(cfg, g)) do
        local led, panic = 0, 0
        for _, x in ipairs(k.groups) do if x.panic then panic = panic + 1 elseif x.leader then led = led + 1 end end
        local nxt = k.n >= k.cap and 'at cap' or (k.next_days > 0 and ('in %.1f d'):format(k.next_days) or 'due')
        local by = k.parent == 'cavern' and 'cave' or (L.mode == 'fixed' and 'fixed' or 'map')
        L_(out, ('%-12s %3d %-5s %3d %6s %5.1f %-10s %4d %5d'):format(k.key:sub(1, 12), k.cap, by, k.n, k.target and ('%.1f'):format(k.target) or '-',
            k.w_days or 0, nxt, led, panic), k.n >= k.cap and COLOR_YELLOW or COLOR_GREY)
    end
    return out
end
local function grpLines(prefix)
    return function(_, cfg, g)
        local out = {}
        for _, l in ipairs(sw.GRP.status(cfg, g)) do if l:find(prefix, 1, true) == 1 then L_(out, l) end end
        return out
    end
end
PNL.TOP.caverns = grpLines('cavern gate')
PNL.TOP.leaders = function(win, cfg, g)
    local out = grpLines('leaders')(win, cfg, g)
    for _, l in ipairs(grpLines('animal-people')(win, cfg, g)) do out[#out+1] = l end
    return out
end
-- apex presence against its target per layer, and the H/C/A pyramid of the active roster in season (unit shares:
-- odds x mean group size, what the ladder sets, R59) against the roster's targets
PNL.TOP.roster = function(win, cfg, g)
    local out, R = {}, sw.ROSTER
    L_(out, R.statusLine(cfg))
    local RC = R.cfg(cfg)
    local ks = {}
    for k, st in pairs(g.rapex or {}) do if type(st) == 'table' then ks[#ks+1] = k end end
    table.sort(ks)
    for _, k in ipairs(ks) do
        local st = g.rapex[k]
        -- v7.1 (Alpha Four 1.4): the scheduler keys its state 'apex:<layer>' and 'invasive:<TOKEN>' (ROSTER.apexTick);
        -- the row printed 'apex apex:lan' and looked the target up under the whole key, so every layer read target 0%
        local tag, name = tostring(k):match('^(%a+):(.+)$')
        name = name or tostring(k)
        local tgt = (tag == 'invasive' and RC.apex.invasive_presence) or RC.apex.presence[name] or 0
        local pres = (st.total or 0) > 0 and 100 * st.seen / st.total or 0
        L_(out, ('%-8s %-12s present %3.0f%% (target %2d%%)  groups %d  placed %d'):format(tag == 'invasive' and 'invasive' or 'apex', name:sub(1, 12), pres, tgt, st.groups or 0, st.placed or 0),
            pres + 0.5 >= tgt and COLOR_GREEN or COLOR_YELLOW)
    end
    if #ks == 0 then L_(out, 'apex scheduler: no decision yet (it acts after `roster build` seats apexes)', COLOR_DARKGREY) end
    local season = dfhack.isMapLoaded() and df.global.cur_season or 0
    for _, part in ipairs({ 'land', 'flying', 'water', 'cavern' }) do
        local u, n = { H = 0, C = 0, A = 0 }, 0
        for _, e in ipairs(win.pool or {}) do
            if e.inEmbark and not e.locked and e.cat ~= 'vermin' and isAllowed(cfg, e) and inSeason(cfg, e.key, season) then
                local okP, inp = pcall(R.inPart, cfg, e, part)
                if okP and inp then
                    local okS, slot = pcall(R.slotOf, cfg, e, part)
                    local lv = okS and R.LEVEL[slot] or 'H'
                    local okM, gm = pcall(ENGINE.groupMean, cfg, e.key, df.creature_raw.find(e.idx))
                    u[lv] = (u[lv] or 0) + ODDS.weight(cfg, e.key, e.token) * ((okM and tonumber(gm)) or 1)
                    n = n + 1
                end
            end
        end
        local tot = u.H + u.C + u.A
        local key = part == 'water' and 'ocean' or part
        local T = RC.pyramid and RC.pyramid[key]
        local tH, tC = T and T.H, T and T.C
        local function pc(x) return tot > 0 and math.floor(100 * x / tot + 0.5) or 0 end
        L_(out, ('pyramid %-6s %2d/%2d/%2d%% H/C/A, target %s, %d species'):format(part, pc(u.H), pc(u.C), pc(u.A),
            (tH and tC) and ('%d/%d/%d'):format(tH, tC, math.max(0, 100 - tH - tC)) or '-', n), n > 0 and COLOR_GREY or COLOR_DARKGREY)
    end
    return out
end
-- the hunters' skill readback (R58): per profiled species, the SNEAK level its castes and the units on the map carry
PNL.TOP.ecology = function(_, cfg, g)
    local out = {}
    L_(out, ecologyStatus(cfg, g))
    local rows = sw.V7.H.readback()
    L_(out, ('%-20s %-8s %5s %7s %9s %s'):format('hunter', 'profile', 'SNEAK', 'castes', 'on map', 'skill now'), COLOR_LIGHTGREEN)
    for i, r in ipairs(rows) do
        if i > 10 then L_(out, ('  (%d more: the readout `hunters readback`)'):format(#rows - 10), COLOR_DARKGREY) break end
        L_(out, ('%-20s %-8s %5s %3d/%-3d %4d/%-4d %s'):format(r.token:sub(1, 20), tostring(r.profile or '-'):sub(1, 8), tostring(r.sneak or '-'), r.casteOk, r.castes,
            r.unitOk, r.units, r.lo and (r.lo == r.hi and tostring(r.lo) or (r.lo .. '-' .. r.hi)) or '-'), (r.units > 0 and r.unitOk < r.units) and COLOR_YELLOW or COLOR_GREY)
    end
    if #rows == 0 then L_(out, '  no hunter profiled yet (the solitary and pack packages write on apply)', COLOR_DARKGREY) end
    return out
end
-- the water mix (R62): per body, what is swimming by level against the body's pyramid, apex groups against the limit
PNL.TOP.water = function(_, cfg, g)
    local out = {}
    L_(out, sw.V7.WAT.layerLine(cfg))
    if not dfhack.isMapLoaded() then return out end
    local cen = sw.V7.WAT.census(cfg, g)
    local wt = ENGINE.waterTiles()
    for _, b in ipairs(sw.V7.GRP.BODIES) do
        if (wt.sum[b] or 0) > 0 then
            local B, T = cen[b], sw.V7.WAT.pyramid(cfg, b)
            local n = 0
            for _, grp in ipairs(g.groups) do if grp.layer == 'water' and grp.body == b and not grp.seeded then n = n + 1 end end
            local u = B and B.units or 0
            local function pc(x) return u > 0 and math.floor(100 * x / u + 0.5) or 0 end
            L_(out, ('%-5s groups %d of %d  units %d  H/C/A %d/%d/%d%%  target %d/%d/%d  apex groups %d of %s'):format(b, n, QUOTA.groupsFor(cfg, 'water:' .. b), u,
                pc(B and B.lv.H or 0), pc(B and B.lv.C or 0), pc(B and B.lv.A or 0), T.H or 0, T.C or 0, T.A or 0, B and B.apexGroups or 0,
                cfg.water.mix.apex_max > 0 and tostring(cfg.water.mix.apex_max) or 'any'))
        end
    end
    return out
end
-- scavenging per species (R16-R18, R42), most eaten first
PNL.TOP.scavenging = function(_, cfg)
    local out = {}
    local sc = cfg.scavenge
    L_(out, ('scavenging %s%s; curious thieves %s'):format((cfg.enabled and sc.enabled) and 'ON' or 'off', sc.natural ~= false and ' (natural cadence)' or ' (v7.0 sweep)',
        (cfg.curious or {}).reform and 'stay after a theft' or 'leave as DF has them'), COLOR_WHITE)
    local st = sw.SCAV.stats()
    local toks = {}
    for tok in pairs(st.by or {}) do toks[#toks+1] = tok end
    table.sort(toks, function(a, b) return (st.by[a].kg or 0) > (st.by[b].kg or 0) end)
    if #toks > 0 then L_(out, ('%-22s %6s %8s %8s %6s %5s'):format('scavenger', 'visits', 'ate kg', 'finished', 'walks', 'hops'), COLOR_LIGHTGREEN) end
    for i, tok in ipairs(toks) do
        if i > 8 then L_(out, ('  (%d more: the readout `scavenge stats`)'):format(#toks - 8), COLOR_DARKGREY) break end
        local b = st.by[tok]
        L_(out, ('%-22s %6d %8.0f %8d %6d %5d'):format(tok:sub(1, 22), b.visits or 0, b.kg or 0, b.finished or 0, b.walks or 0, b.hops or 0))
    end
    if #toks == 0 then L_(out, '  no scavenger has eaten yet', COLOR_DARKGREY) end
    return out
end
PNL.TOP.vermin = function(_, cfg)
    return { { sw.VERMIN.gobbleStatus(cfg), COLOR_GREY }, { sw.VERMIN.forageStatus(cfg), COLOR_GREY }, { sw.HUNT.status(cfg), COLOR_GREY } }
end
PNL.TOP.extinct = function(_, cfg) return { { sw.V7.EXTINCT.statusLine(cfg), COLOR_GREY } } end
-- v7.1 (aquarium stream): the switches, the overlays' fuses and paint times, the mod (installed? preset? in this world?)
PNL.TOP.aquarium = function(_, cfg, g)
    local out = {}
    for _, l in ipairs(PNL.ctl.status('aquarium', cfg, g).lines or {}) do L_(out, l) end
    return out
end
PNL.TOP.v7 = function(_, cfg, g)
    local out = {}
    for _, l in ipairs(PNL.ctl.status('v7', cfg, g).lines or {}) do L_(out, l) end
    return out
end
-- R5, R6, R10: per cavern its pressure against the threshold, the phase (quiet, stirring, irrupting, cooldown), this
-- pass's sources, and while an event runs its waves, the units placed, alive and dead, the agitated animals and how
-- many units carry each behaviour token
PNL.TOP.irruption = function(_, cfg, g)
    local out, ir = {}, cfg.irruption
    L_(out, ('Irruptions %s   threshold %.2f   at most %d cavern(s) at once   %d wave(s) of up to %d'):format(ir.enabled and 'ON' or 'off', ir.threshold,
        ir.max_active or 0, ir.waves or 0, ir.size_cap or 0), ir.enabled and COLOR_LIGHTRED or COLOR_DARKGREY)
    if not dfhack.isMapLoaded() then return out end
    local st = IRRUPT.state(g)
    local found = cavernsFound()
    for _, d in ipairs(IRRUPT.DEPTHS) do
        local L = st.layers['c' .. d] or {}
        local p, thr = IRRUPT.pressure(g, d), math.max(ir.threshold or 1, 1e-6)
        local ph = L.phase or 'idle'
        local pin = g.pressure_pin and g.pressure_pin['c' .. d]
        local where = found[d] == nil and 'not on map' or (found[d] and 'found' or 'not found yet')
        local n = math.max(0, math.min(10, math.floor(10 * p / thr + 0.5)))
        L_(out, ('Cavern %d  %-13s pressure %5.2f of %.2f [%s%s]%s'):format(d + 1, where, p, thr, ('#'):rep(n), ('-'):rep(10 - n), pin and ' pinned' or ''),
            (ph == 'active' and COLOR_LIGHTRED) or (ph == 'warning' and COLOR_YELLOW) or (ph == 'cooldown' and COLOR_LIGHTBLUE) or COLOR_WHITE)
        L_(out, '  ' .. IRRUPT.phaseText(cfg, g, d, false), (ph == 'active' and COLOR_LIGHTRED) or (ph == 'warning' and COLOR_YELLOW) or COLOR_GREY)
        local src = L.src
        if src and ir.enabled then
            L_(out, ('  this pass: citizens %d  near %d  dig %d  scarcity %.2f  season x%.2f  fort x%.2f  gain %+.3f'):format(src.cit or 0, src.near or 0, src.dig or 0,
                src.scar or 0, src.season or 1, src.fort or 1, src.gain or 0), COLOR_DARKGREY)
        end
        local ev = (ph == 'active') and L.ev
        if ev then
            local now = absTick()
            L_(out, ('  waves %d of %d%s  placed %d  alive %d  dead %d  left %d  agitated %d'):format(ev.done or 0, ev.waves or 0,
                (ev.done or 0) < (ev.waves or 0) and ('  next in %.1f d'):format(math.max(0, (ev.next_wave or now) - now) / TICKS_PER_DAY) or '',
                ev.placed or 0, ev.alive or 0, ev.dead or 0, ev.left or 0, ev.agitated or 0), COLOR_LIGHTRED)
            local per, champ = {}, 0
            for _, rec in pairs(ev.units or {}) do
                if not rec.dead and not rec.left then
                    for _, t in ipairs(rec.tags or {}) do per[t] = (per[t] or 0) + 1 end
                    if rec.champ then champ = champ + 1 end
                end
            end
            local parts = {}
            for _, t in ipairs(IRRUPT.TOKENS or {}) do if per[t.id] then parts[#parts+1] = ('%s %d'):format(t.id, per[t.id]) end end
            L_(out, '  tokens on living units: ' .. (#parts > 0 and table.concat(parts, ', ') or 'none (an animal wave carries none)') .. (champ > 0 and ('; champion %d'):format(champ) or ''))
        end
    end
    local S = st.stats or {}
    L_(out, ('So far: %d event(s), %d wave(s), %d unit(s) placed%s'):format(S.events or 0, S.waves or 0, S.placed or 0,
        st.last and ('; last: cavern %d %s, %s'):format((st.last.d or 0) + 1, tostring(st.last.token or '?'), tostring(st.last.why or '?')) or ''))
    return out
end

-- ---- the rows of one section ----
function PNL.ctlRow(win, r, W)
    local C = PNL.ctl
    local avail = C.available(r)
    local v   -- v7.1 (and-or audit): `avail and PNL.value(...) or nil` turned a false into nil, so an off switch whose
    if avail then v = PNL.value(win, r) end   -- default is on never carried the non-default '*'
    local d = avail and C.defaultOf(r)
    local changed = avail and d ~= nil and v ~= nil and not PNL.same(v, d)
    local lw = math.max(12, math.min(30, W - 29))
    local val, pen
    if not avail then val, pen = 'n/a', COLOR_DARKGREY
    else
        val = PNL.valText(r, v)
        pen = (r.type == 'bool') and (v and COLOR_LIGHTGREEN or COLOR_GREY) or COLOR_WHITE
    end
    local sl = (avail and (r.type == 'int' or r.type == 'float')) and PNL.slider(r, v) or ''
    return { text={ { text=(changed and '*' or ' ') .. PNL.fit(PNL.ascii(r.label), lw), width=lw + 1, pen=avail and COLOR_WHITE or COLOR_DARKGREY },
                    { gap=1, text=PNL.fit(val, 16), width=16, pen=pen }, { gap=1, text=sl, pen=COLOR_DARKGREY } }, data={ ctl=r } }
end
function PNL.matches(r, words)
    local hay = (tostring(r.label) .. ' ' .. tostring(r.id) .. ' ' .. tostring(r.help or '') .. ' ' .. tostring(r.grp or '') .. ' ' .. tostring(r.verb or '')):lower()
    for _, w in ipairs(words) do if not hay:find(w, 1, true) then return false end end
    return true
end
function PNL.sections(win)
    local out = {}
    for _, s in ipairs(PNL.SECTIONS) do out[#out+1] = s end
    if win._pfind and win._pfind ~= '' then out[#out+1] = { id='find', label='Find: ' .. win._pfind } end
    return out
end
function PNL.build(win, sec, W)
    local C, rows = PNL.ctl, {}
    local function text(s, pen, indent) for _, l in ipairs(PNL.wrapText(s, W, indent)) do rows[#rows+1] = { text={ { text=l, pen=pen or COLOR_GREY } } } end end
    if not C then
        text('The control registry (seasonal-wildlife-controls) did not load, so only the switches and jobs are here: ' .. tostring(PNL.err), COLOR_LIGHTRED)
        rows[#rows+1] = { text='' }
        for _, swt in ipairs(PANEL.SWITCHES) do
            rows[#rows+1] = { text={ { text=(swt.get(win.cfg) and '[ON] ' or '[off]') .. ' ' .. PNL.fit(swt.label, W - 6), pen=swt.get(win.cfg) and COLOR_LIGHTGREEN or COLOR_GREY } }, data={ switch=swt } }
        end
        PNL.jobRows(win, rows, W)
        return rows
    end
    local cfg = win.cfg
    local g = dfhack.isMapLoaded() and loadGroups() or { groups = {} }
    local S = C.sectionOf(sec.id)
    if S and S.note then text(S.note, COLOR_GREY) end
    if sec.id == 'all' then text(('Every control the tool has (%d). Alt+S finds by words in a label, id or help.'):format(#C.CONTROLS + #C.panelRows()), COLOR_GREY) end
    if sec.id == 'find' then text(('Controls matching "%s". Alt+S searches again; an empty search closes this.'):format(win._pfind), COLOR_GREY) end
    local top = PNL.TOP[sec.id]
    if top then
        local ok, lines = pcall(top, win, cfg, g, W)
        rows[#rows+1] = { text='' }
        if ok then for _, l in ipairs(lines) do text(l[1], l[2], '  ') end
        else text('This readout failed: ' .. tostring(lines), COLOR_LIGHTRED) end
    end
    local list = {}
    if sec.id == 'switches' or sec.id == 'all' then for _, r in ipairs(C.panelRows()) do list[#list+1] = r end end
    local words = {}
    if sec.id == 'find' then for w in tostring(win._pfind):lower():gmatch('%S+') do words[#words+1] = w end; list = {}
        for _, r in ipairs(C.panelRows()) do if PNL.matches(r, words) then list[#list+1] = r end end end
    for _, r in ipairs(C.CONTROLS) do
        if (sec.id == 'all') or (r.sec == sec.id) or (sec.id == 'find' and PNL.matches(r, words)) then list[#list+1] = r end
    end
    local last
    for _, r in ipairs(list) do
        local head = (sec.id == 'all' or sec.id == 'find') and ((C.sectionOf(r.sec) or {}).label or r.sec) or r.grp or (r.sec == 'switches' and 'Switches') or nil
        if head and head ~= last then rows[#rows+1] = { text='' }; text(head:upper(), COLOR_YELLOW); last = head end
        rows[#rows+1] = PNL.ctlRow(win, r, W)
    end
    if sec.id == 'find' and #list == 0 then text('  nothing matches', COLOR_DARKGREY) end
    if sec.id == 'switches' then
        local on, lw = overlayOn(), math.max(12, math.min(30, W - 29))
        rows[#rows+1] = { text={ { text=' ' .. PNL.fit('Map overlay (markers, links)', lw), width=lw + 1, pen=COLOR_WHITE },
            { gap=1, text=on and '[ON]' or '[off]', width=16, pen=on and COLOR_LIGHTGREEN or COLOR_GREY } }, data={ overlay=true } }
    end
    if sec.id ~= 'all' and sec.id ~= 'find' then
        local acts, reads = {}, {}
        for _, a in ipairs(C.ACTIONS) do if a.sec == sec.id then acts[#acts+1] = a end end
        for _, r in ipairs(C.READOUTS) do if r.sec == sec.id then reads[#reads+1] = r end end
        if #acts > 0 then
            rows[#rows+1] = { text='' }; text('ACTIONS (Enter runs)', COLOR_YELLOW)
            for _, a in ipairs(acts) do
                local ok = C.available(a)
                rows[#rows+1] = { text={ { text=PNL.fit(' > ' .. a.label .. (a.arg and ' (choose)' or '') .. (a.confirm and ' (asks)' or '') .. (ok and '' or ' n/a'), W),
                    pen=ok and COLOR_LIGHTCYAN or COLOR_DARKGREY } }, data={ act=a } }
            end
        end
        if #reads > 0 then
            rows[#rows+1] = { text='' }; text('READOUTS (Enter shows the console output)', COLOR_YELLOW)
            for _, r in ipairs(reads) do
                local ok = C.available(r)
                rows[#rows+1] = { text={ { text=PNL.fit(' ? ' .. r.label .. (ok and '' or ' n/a'), W), pen=ok and COLOR_CYAN or COLOR_DARKGREY } }, data={ read=r } }
            end
        end
    end
    if sec.id == 'switches' then PNL.jobRows(win, rows, W) end
    return rows
end
-- the jobs: cadence, last and worst time, runs, passes over budget, fuse (Enter on a tripped job re-arms every job)
function PNL.jobRows(win, rows, W)
    rows[#rows+1] = { text='' }
    rows[#rows+1] = { text={ { text=PNL.fit(('JOBS  %-18s %7s %6s %6s %5s %4s %s'):format('', 'every', 'last', 'worst', 'runs', 'over', 'fuse'), W), pen=COLOR_YELLOW } } }
    local trips = FUSE.trips()
    for _, j in ipairs(PANEL.jobs(win.cfg)) do
        local st, trip = FUSE.stats[j.name] or {}, trips[j.name]
        rows[#rows+1] = { text={ { text=j.on and '[ON] ' or '[off]', pen=j.on and COLOR_LIGHTGREEN or COLOR_DARKGREY },
            { text=PNL.fit((' %-18s %7s %6s %6s %5s %4s '):format(PNL.fit(j.label, 18), PNL.fit(tostring(j.cadence) .. ' t', 7), st.last and (st.last .. 'ms') or '-',
                st.worst and (st.worst .. 'ms') or '-', tostring(st.runs or 0), tostring(st.over or 0)), W - 10),
                pen=(st.worst or 0) > FUSE.BUDGET_MS and COLOR_YELLOW or COLOR_WHITE },
            { text=trip and 'TRIP' or 'ok', pen=trip and COLOR_LIGHTRED or COLOR_GREY } }, data={ job=j, trip=trip } }
    end
    for _, l in ipairs(PNL.wrapText(('budget %d ms a pass; "over" counts passes above it. Enter on a tripped job re-arms every job.'):format(FUSE.BUDGET_MS), W)) do
        rows[#rows+1] = { text={ { text=l, pen=COLOR_DARKGREY } } }
    end
end
-- the help for a control: what it does, its range or choices, its default, the console verb
function PNL.helpText(r)
    local C = PNL.ctl
    local parts = { PNL.ascii(r.label) .. ':' }
    local help = r.help
    if r.labelFrom then local okL, l = pcall(function() local t = sw; for p in r.labelFrom:gmatch('[^%.]+') do t = t[p] end; return t end); if okL and type(l) == 'string' then help = l end end
    if help and help ~= '' then parts[#parts+1] = PNL.ascii(help) end
    if not C.available(r) then parts[#parts+1] = '(not in this version of the tool)' end
    if r.type == 'int' or r.type == 'float' then
        parts[#parts+1] = ('Range %s..%s%s, step %s.'):format(num(r.min or 0), num(r.max or 0), r.unit and (' ' .. r.unit) or '', num(r.step or (r.type == 'int' and 1 or 0.1)))
    elseif r.type == 'enum' then
        local o = {}; for _, x in ipairs(C.optsOf(r) or {}) do o[#o+1] = tostring(x) end
        parts[#parts+1] = 'Choices: ' .. table.concat(o, ', ') .. '.'
    elseif r.type == 'seasons' then parts[#parts+1] = 'Season codes SpSuAuWi, or none.' end
    local d = C.defaultOf(r)
    if d ~= nil then parts[#parts+1] = 'Default ' .. PNL.valText(r, d) .. '.' end
    local verb = r.verb and ('seasonal-wildlife ' .. r.verb:gsub('%$', 'VALUE'):gsub('@[%w_%.]+', 'N')) or (r.vmap and 'its own verb per choice') or (r.panel and 'the Panel switch')
        or (r.direct and 'config only (undo step + ledger)') or nil
    if verb then parts[#parts+1] = 'Console: ' .. verb .. '.' end
    return table.concat(parts, ' ')
end
-- the width the pane's text keeps to: the list's own, within the window's 86 columns
function Win:paneWidth(view)
    local l = (view.frame and view.frame.l) or 0
    local w = (view.frame_body and view.frame_body.width) or ((self.frame and self.frame.w or 90) - 4 - l)
    return math.max(20, math.min(w, PNL.W - l))
end
-- v7.1 (Alpha Four 1.5, 6.3): the identity of a Panel row's control, action, readout or job, so a redraw whose
-- readouts wrapped to a different number of lines puts the cursor back on the same control, not the same row number
function PNL.rowId(d)
    if type(d) ~= 'table' then return nil end
    local x = d.ctl or d.act or d.read or d.switch
    if x then return (d.ctl and 'c:' or d.act and 'a:' or d.read and 'r:' or 's:') .. tostring(x.id or x.label) end
    if d.job then return 'j:' .. tostring(d.job.label) end
    if d.overlay then return 'o:' end
    if d.trip then return 't:' end
    return nil
end
function Win:refreshPanel()
    -- v7.1 (Alpha Four 6.19): a set from the browser or the console (another copy of the scripts) saved a newer config;
    -- the Panel drew the copy the window loaded earlier ('Fixed cap 3' after a web set to 4, even after R)
    if sw.CACHE and self._cfgVer ~= sw.CACHE.ver then
        self.cfg = loadConfig(); self._before = loadConfig(); self._cfgVer = sw.CACHE.ver
    end
    local secs = PNL.sections(self)
    self._psec = math.max(1, math.min(self._psec or 1, #secs))
    local sec = secs[self._psec]
    local sl = {}
    for i, s in ipairs(secs) do
        sl[#sl+1] = { text={ { text=PNL.fit((i == self._psec and '>' or ' ') .. s.label, PNL.LW - 1), pen=i == self._psec and COLOR_YELLOW or COLOR_GREY } } }
    end
    self.subviews.panel_secs:setChoices(sl)
    self.subviews.panel_secs:setSelected(self._psec)
    local list = self.subviews.panel
    local keep = (self._psecShown == sec.id) and list:getSelected() or nil
    local keepId
    if keep then local _, kc = list:getSelected(); keepId = PNL.rowId(kc and kc.data) end
    local rows = PNL.build(self, sec, self:paneWidth(list))
    list:setChoices(rows)
    local pick = keep
    if keepId then
        -- v7.1 (Alpha Four 1.5): keep the control, not the row number. A set that changed a readout's wrapped height
        -- moved every row below it; the second Enter on Grazers then flipped Roles, the next row down
        for i, r in ipairs(rows) do if PNL.rowId(r.data) == keepId then pick = i; break end end
    end
    if not pick or not (rows[pick] and rows[pick].data) then
        pick = nil
        for i, r in ipairs(rows) do if r.data then pick = i; break end end
    end
    if pick then list:setSelected(pick) end
    self._psecShown = sec.id
    self:panelHelp()
    local okF, fps, cap = pcall(PANEL.fps)
    fps, cap = okF and tonumber(fps) or nil, okF and tonumber(cap) or nil
    local n = 0; for _, r in ipairs(rows) do if r.data and r.data.ctl then n = n + 1 end end
    self.subviews.panel_fps:setText({ { text=PNL.fit(('%s: %d control(s)'):format(sec.label, n), 44), pen=COLOR_YELLOW },
        { text=fps and ('   frame rate %d (cap %d)'):format(fps, cap or 0) or '', pen=COLOR_GREY } })
end
function Win:panelSection(dir, idx)
    local n = #PNL.sections(self)
    if idx then self._psec = idx else self._psec = ((self._psec or 1) - 1 + dir) % n + 1 end
    self:refreshPanel()
end
function Win:panelRow()
    local _, c = self.subviews.panel:getSelected()
    return c and c.data
end
function Win:panelHelp()
    local d = self:panelRow()
    local txt
    if not d then txt = 'Select a row with the arrows. Enter sets it; Left/Right or - + step it; D puts its default back.'
    elseif d.ctl then txt = PNL.helpText(d.ctl)
    elseif d.act then
        txt = ('%s: %s Enter runs it%s. Console: seasonal-wildlife %s.'):format(d.act.label, d.act.help or '', d.act.confirm and ' after asking' or '',
            d.act.verb:match('^panel:') and '(the Panel)' or d.act.verb:gsub('%$', d.act.arg and ('[' .. table.concat(d.act.arg.opts, '|') .. ']') or ''))
    elseif d.read then txt = ('%s: Enter shows the console output of: seasonal-wildlife %s'):format(d.read.label, d.read.verb)
    elseif d.job then txt = ('%s: every %s ticks; %s.%s'):format(d.job.label, tostring(d.job.cadence), d.job.on and 'running' or 'off',
        d.trip and (' Stopped by its fuse: ' .. tostring(d.trip.why) .. '. Enter re-arms every job.') or '')
    elseif d.overlay then txt = 'Map overlay: group markers and predator-prey links drawn on the map. Enter turns it on or off.'
    elseif d.switch then txt = d.switch.label .. ': ' .. tostring(d.switch.note or '') end
    local lines = PNL.wrapText(txt, PNL.W)
    local toks = {}
    for i = 1, math.min(3, #lines) do
        if i > 1 then toks[#toks+1] = NEWLINE end
        toks[#toks+1] = { text=(i == 3 and #lines > 3) and PNL.fit(lines[i] .. ' ...', PNL.W) or lines[i], pen=COLOR_GREY }
    end
    self.subviews.panel_help:setText(toks)
end
function Win:panelReport(ok, out, cmd)
    self.subviews.panel_cmd:setText({ { text=PNL.fit(cmd and ('ran: ' .. PNL.ascii(cmd)) or '', PNL.W), pen=COLOR_DARKGREY } })
    self:setPanelStatus(out, ok and COLOR_LIGHTCYAN or COLOR_YELLOW)
end
-- one set from the Panel: the registry's path, then the window reloads what the verb wrote and redraws
function Win:panelSet(r, v)
    local ok, msg, cmd = self:ctlSet(r.id, PNL.ctlWord(v))
    local id = tostring(r.id)
    if id:match('^switch%.') or id == 'water.layer_mode' or id == 'water.enabled' then self:rebuildData() end
    self:refreshPanel()
    self:panelReport(ok, msg, cmd)
end
function PNL.ctlWord(v)
    if type(v) == 'boolean' then return v and 'on' or 'off' end
    if type(v) == 'number' then return num(math.floor(v * 1e6 + 0.5) / 1e6) end
    return tostring(v)
end
function Win:act_panel_toggle(_, choice)
    local d = choice and choice.data
    if not d then return end
    if d.ctl then
        local r = d.ctl
        local C = PNL.ctl
        if not C.available(r) then self:panelReport(false, r.label .. ': not in this version of the tool.') return end
        local v = PNL.value(self, r)
        if r.type == 'bool' then self:panelSet(r, not v)
        elseif r.type == 'enum' then self:act_panel_step(1)
        else
            local hint = (r.type == 'int' or r.type == 'float') and ('%s..%s%s'):format(num(r.min or 0), num(r.max or 0), r.nilv and (' or ' .. r.nilv) or '')
                or (r.type == 'seasons' and 'SpSuAuWi, or none') or 'a value'
            dialogs.showInputPrompt(r.label, ('%s (%s):'):format(r.label, hint), COLOR_WHITE, v == nil and '' or (type(v) == 'number' and num(v) or tostring(v)),
                function(txt) self:panelSet(r, (txt or ''):gsub('^%s+', ''):gsub('%s+$', '')) end)
        end
    elseif d.act then self:panelAct(d.act)
    elseif d.read then
        local ok, out, cmd = PNL.ctl.readout(d.read.id)
        self:panelReport(ok, ok and (d.read.label .. ': shown.') or ('Refused: ' .. PNL.firstLine(out)), cmd)
        if ok then PNL.showText(d.read.label, out) end
    elseif d.overlay then
        local on = not overlayOn()
        dfhack.run_command_silent('overlay', on and 'enable' or 'disable', 'seasonal-wildlife.groups')
        self:refreshPanel(); self:setPanelStatus('Map overlay ' .. (on and 'ON.' or 'off.'))
    elseif d.trip then
        if PNL.ctl then PNL.ctl.act('rearm') else FUSE.reset(); enableSched() end
        self.cfg = loadConfig(); self._before = loadConfig()
        self:refreshPanel(); self:setPanelStatus('Every job re-armed.')
    elseif d.switch then   -- the fallback when the registry did not load: the Panel's own path, as in v6.3
        self._lastAction = 'switch ' .. d.switch.id
        local v = not d.switch.get(self.cfg)
        d.switch.set(self.cfg, v)
        if d.switch.id == 'irruption' and not v and IRRUPT.restoreAll then saveConfig(self.cfg); IRRUPT.restoreAll('irruptions off') end
        if d.switch.id == 'land' or d.switch.id == 'water' or d.switch.id == 'cavern' then
            self.pool = buildPool(self.cfg); ROSTER.normalize(self.cfg, self.pool)   -- a layer's species join the roster whole
        end
        LEDGER.add('edit', '', '%s %s', d.switch.label, v and 'on' or 'off')
        self:save()
        if self.cfg.enabled then enableSched() else disableSched() end
        self.cfg = loadConfig(); self._before = loadConfig(); self:rebuildData(); self:refreshPanel()
        self:setPanelStatus(('%s %s.'):format(d.switch.label, v and 'ON' or 'off'))
    end
end
-- a readout's or an action's console output, in a scrolling list (wrapped to the window)
function PNL.showText(title, out)
    local choices = {}
    for line in (tostring(out or '') .. '\n'):gmatch('([^\n]*)\n') do
        for _, l in ipairs(PNL.wrapText(line, PNL.W - 6, '    ')) do choices[#choices+1] = { text=l } end
    end
    if #choices == 0 then choices[1] = { text='(no output)' } end
    dialogs.ListBox{ frame_title=PNL.ascii(title), with_filter=true, choices=choices }:show()
end
function Win:panelAct(a)
    local C = PNL.ctl
    if not C.available(a) then self:panelReport(false, a.label .. ': not in this version of the tool.') return end
    local function run(arg)
        local function go()
            local ok, out, cmd = C.act(a.id, arg)
            self.cfg = loadConfig(); self._before = loadConfig()
            if a.id == 'all_on' or a.id == 'all_off' or a.id == 'roster_build' then self:rebuildData() end
            self:refreshPanel()
            self:panelReport(ok, ok and (a.label .. ': ' .. PNL.firstLine(out ~= '' and out or 'done')) or ('Refused: ' .. PNL.firstLine(out)), cmd)
            if ok and tostring(out):find('\n', 1, true) then PNL.showText(a.label, out) end
        end
        if a.confirm then self:confirm(a.label, PNL.ascii(a.help or a.label) .. '\nGo ahead?', go) else go() end
    end
    if a.arg then
        local choices = {}
        for _, o in ipairs(a.arg.opts) do choices[#choices+1] = { text=tostring(o), value=o } end
        dialogs.ListBox{ frame_title=a.label .. ': which?', choices=choices, on_select=function(_, c) run(c.value) end }:show()
    else run(nil) end
end
-- Left/Right (Shift: x10), - and +, Shift+Enter: one step of the selected number, the next or previous choice, on/off
function Win:act_panel_step(dir, big)
    local d = self:panelRow()
    local r = d and d.ctl
    if not r then return end
    if not PNL.ctl.available(r) then self:panelReport(false, r.label .. ': not in this version of the tool.') return end
    local v = PNL.value(self, r)
    if r.type == 'bool' then
        if (dir > 0) ~= (v == true) then self:panelSet(r, dir > 0) end
    elseif r.type == 'enum' then
        local o = PNL.ctl.optsOf(r) or {}
        local i = 1
        for k, x in ipairs(o) do if tostring(x) == tostring(v) then i = k end end
        if #o > 0 then self:panelSet(r, o[(i - 1 + dir) % #o + 1]) end
    elseif r.type == 'int' or r.type == 'float' then
        local cur = tonumber(v) or tonumber(PNL.ctl.defaultOf(r)) or tonumber(r.min) or 0
        local step = (tonumber(r.step) or (r.type == 'int' and 1 or 0.1)) * (big and 10 or 1)
        local nv = math.max(tonumber(r.min) or -math.huge, math.min(tonumber(r.max) or math.huge, cur + dir * step))
        if r.type == 'int' then nv = math.floor(nv + 0.5) end
        if PNL.same(nv, cur) then self:panelReport(true, ('%s: %s is the end of its range.'):format(r.label, PNL.valText(r, cur))) return end
        self:panelSet(r, nv)
    else
        self:panelReport(true, r.label .. ': Enter to type a value.')
    end
end
function Win:act_panel_default()
    local d = self:panelRow()
    local r = d and d.ctl
    if not r then self:setPanelStatus('Select a control first.') return end
    local def = PNL.ctl.defaultOf(r)
    if def == nil then self:panelReport(true, r.label .. ': no default to put back.') return end
    self:panelSet(r, def)
end
function Win:act_panel_find()
    dialogs.showInputPrompt('Find a control', 'Words in its label, id or help (empty closes the search):', COLOR_WHITE, self._pfind or '', function(txt)
        self._pfind = (txt or ''):gsub('^%s+', ''):gsub('%s+$', '')
        self._psec = (self._pfind ~= '') and (#PNL.SECTIONS + 1) or 1
        self:refreshPanel()
    end)
end
function Win:act_panel_all(on)
    self:confirm(on and 'All on' or 'All off', on and 'Turn the switches back on (as they were before All off, or the usual set)\nand start every job. Go ahead?'
        or 'Stop every job and put back everything the tool wrote into the game\n(cavern frequencies, cluster sizes, a coupling, an irruption). Go ahead?', function()
        self._lastAction = on and 'all on' or 'all off'
        if PNL.ctl then
            local ok, out, cmd = PNL.ctl.act(on and 'all_on' or 'all_off')
            self.cfg = loadConfig(); self._before = loadConfig(); self:rebuildData(); self:refreshPanel()
            self:panelReport(ok, PNL.firstLine(out), cmd)
        elseif on then
            PANEL.allOn(self.cfg); self:save(); enableSched(); self.cfg = loadConfig(); self._before = loadConfig(); self:rebuildData(); self:refreshPanel()
            self:setPanelStatus('All on: every job running.')
        else
            local restored = PANEL.allOff(self.cfg); self:save(); disableSched(); self.cfg = loadConfig(); self._before = loadConfig(); self:rebuildData(); self:refreshPanel()
            self:setPanelStatus('All off: every job stopped; restored ' .. tostring(restored) .. '.')
        end
    end)
end
-- v6.3.0 (W7): a tripped fuse is shown on the Overview, not only on the Live tab, with the way back
function Win:fuseBanner()
    local trips, names = FUSE.trips(), {}
    for n, v in pairs(trips) do names[#names+1] = ('%s (%s)'):format(n:gsub('^seasonal%-wildlife/?', ''), v.why or '?') end
    if #names == 0 then return nil end
    table.sort(names)
    return 'JOB STOPPED: ' .. table.concat(names, ', ') .. ' -- Alt+P, Enter on the job re-arms it'
end

-- Overview tab (v5.10.1): what the map holds now, the next boundary, the recent ledger
function Win:refreshOverview()
    local cfg, lines = self.cfg, {}
    local function add(text, pen) lines[#lines+1] = { text={ { text=text, pen=pen or COLOR_WHITE } } } end
    local yt, sl, season = df.global.cur_year_tick, TICKS_PER_YEAR / 4, df.global.cur_season
    local day = math.floor((yt % sl) / TICKS_PER_DAY) + 1
    local part = day <= 9 and 'Early' or (day <= 18 and 'Mid' or 'Late')
    add(('%s %s, day %d, year %d     tool %s . groups %s . coupling %s . ecology %s'):format(part, SEASON[season], day, df.global.cur_year,
        cfg.enabled and 'on' or 'OFF', cfg.groups.enabled and 'on' or 'off', cfg.groups.coupling and 'on' or 'off', cfg.ecology.enabled and 'on' or 'off'), COLOR_YELLOW)
    add(PATTERN.status(cfg), COLOR_GREY)
    if cfg.irruption.enabled then add(IRRUPT.status(cfg), COLOR_LIGHTRED) end   -- v7.1 (ui): each cavern's pressure and phase
    local banner = self:fuseBanner()
    if banner then add(banner, COLOR_LIGHTRED) end
    add('')
    local by, g = WILD.countByLayer(), loadGroups()
    -- v7.1 (ui; fixes.md section 6, R7): every layer key has its own cap (QUOTA.groupsFor): land one, each water body
    -- and each cavern their own. The water cell read the animal ceiling ('of 0 target') and the cavern cell v6's 2.
    local nLand, nWater, nCave = 0, 0, 0
    for _, grp in ipairs(g.groups) do
        local l = grp.layer or 'land'
        if l == 'cavern' then nCave = nCave + 1 elseif l == 'water' then if not grp.seeded then nWater = nWater + 1 end else nLand = nLand + 1 end
    end
    local F = '%-20s %-16s %-16s %-16s'
    add(F:format('On the map', 'land', 'water', 'caverns'), COLOR_LIGHTGREEN)
    add(F:format('  wild animals', tostring(by.land), tostring(by.water), tostring(by.cavern)))
    add(F:format('  groups', ('%d of %d'):format(nLand, QUOTA.groupsFor(cfg, 'land')), ('%d, cap %d each'):format(nWater, QUOTA.groupsFor(cfg, 'water')),
        ('%d, cap %d each'):format(nCave, QUOTA.groupsFor(cfg, 'cavern'))))
    local nw, nc = (g.next_wave_tick or 0) - absTick(), (g.next_cavern_tick or 0) - absTick()
    add(F:format('  gate reopens', nw > 0 and ('in %.1f days'):format(nw / TICKS_PER_DAY) or 'open',
        cfg.layers.water and (cfg.water.enabled and 'water job on' or 'water job off') or 'layer off',
        cfg.layers.cavern and (nc > 0 and ('in %.1f days'):format(nc / TICKS_PER_DAY) or 'open') or 'layer off'))
    -- v5.10.3: a busy fort tracks fifteen groups; six lines here, the rest on the Live tab, so the blocks
    -- below stay inside the window's 34 rows (validate-full 144859 lost 'In season now' off the bottom)
    local rows = groupsStatus()
    for i, r in ipairs(rows) do if i <= 6 then add('  ' .. r) end end
    if #rows > 6 then add(('  (%d more tracked groups on the Live tab)'):format(#rows - 6), COLOR_DARKGREY) end
    if #rows == 0 then add('  (no tracked groups on the map)', COLOR_DARKGREY) end
    local prey, pred = PATTERN.biomassOnMap()
    add(('  land mass on the map  prey : predator  %s'):format(pred > 0 and ('%.1f : 1'):format(prey / pred) or (prey > 0 and 'prey only' or 'none')), COLOR_GREY)
    add('')
    if not self.pool then self.pool, self.biomeSet, self.regionSet = buildPool(cfg) end
    local nxt = (season + 1) % 4
    local now, plus, minus = { land=0, water=0, cavern=0 }, {}, {}
    for _, e in ipairs(self.pool) do
        if e.inEmbark and isAllowed(cfg, e) then
            local a, b = inSeason(cfg, e.key, season), inSeason(cfg, e.key, nxt)
            if a then now[e.layer] = (now[e.layer] or 0) + 1 end
            if b and not a then plus[#plus+1] = e.token elseif a and not b then minus[#minus+1] = e.token end
        end
    end
    add(F:format('In season now', now.land .. ' species', now.water .. ' species', now.cavern .. ' species'), COLOR_LIGHTGREEN)
    table.sort(plus); table.sort(minus)
    local function few(list, sign)
        local o = {}
        for i = 1, math.min(4, #list) do o[#o+1] = sign .. list[i] end
        if #list > 4 then o[#o+1] = ('(%d more)'):format(#list - 4) end
        return #o > 0 and table.concat(o, ' ') or (sign == '+' and 'nobody arrives' or 'nobody leaves')
    end
    local daysLeft = math.ceil((sl - (yt % sl)) / TICKS_PER_DAY)
    add(('Next boundary        %s in %d days: %s . %s'):format(SEASON[nxt], daysLeft, few(plus, '+'), few(minus, '-')))
    add('')
    local ll, total = LEDGER.lines(5)
    add(('Recent (the ledger: %d recorded)'):format(total), COLOR_LIGHTGREEN)
    for _, l in ipairs(ll) do add('  ' .. l, COLOR_GREY) end
    if #ll == 0 then add('  (nothing yet)', COLOR_DARKGREY) end
    add(STOCK.status(cfg), COLOR_GREY)
    self.subviews.overview:setChoices(self:wrap(lines, self.subviews.overview))
end


-- Species detail (v5.10.7): one animal, every fact and control, over the window
function Win:act_detail()
    local e = self:curEntry(); if not e then return end
    DetailScreen{ win=self, entry=e }:show()
end

local Detail = defclass(Detail, widgets.Window)
Detail.ATTRS{ frame_title='Species detail', frame={ w=84, h=26 }, resizable=true, win=DEFAULT_NIL, entry=DEFAULT_NIL }
function Detail:init()
    self.frame_title = 'Species detail: ' .. self.entry.token
    self:addviews{
        widgets.List{ view_id='facts', frame={ t=0, l=0, r=0, b=4 }, row_height=1 },
        -- v7.1 (ui; Alpha Three 3.1): 'Enter: active/inactive' is 22 cells and ran under Sp at 20; 'k: stock' at 77 ended
        -- at 85, past the 82-column frame. Every label spaced by its drawn width.
        widgets.HotkeyLabel{ frame={ b=1, l=0 },  key='SELECT',   label='active/inactive', on_activate=self:callback('act_allow') },
        widgets.HotkeyLabel{ frame={ b=1, l=24 }, key='CUSTOM_S', label='Sp', on_activate=function() self:act_season(0) end },
        widgets.HotkeyLabel{ frame={ b=1, l=30 }, key='CUSTOM_U', label='Su', on_activate=function() self:act_season(1) end },
        widgets.HotkeyLabel{ frame={ b=1, l=36 }, key='CUSTOM_A', label='Au', on_activate=function() self:act_season(2) end },
        widgets.HotkeyLabel{ frame={ b=1, l=42 }, key='CUSTOM_W', label='Wi', on_activate=function() self:act_season(3) end },
        widgets.HotkeyLabel{ frame={ b=1, l=48 }, key='CUSTOM_Q', label='hold 30 days', on_activate=function() self:act_group('hold') end },
        widgets.HotkeyLabel{ frame={ b=1, l=65 }, key='CUSTOM_X', label='dismiss', on_activate=function() self:act_group('dismiss') end },
        -- v6.4.0 (W2): the model's readings can be overridden per species
        widgets.HotkeyLabel{ frame={ b=2, l=0 },  key='CUSTOM_H', label='habitat (cycle)', on_activate=function() self:act_override('habitat') end },
        widgets.HotkeyLabel{ frame={ b=2, l=19 }, key='CUSTOM_R', label='role (cycle)', on_activate=function() self:act_override('role') end },
        -- v6.5.0 (W4, W5, W10): call a wave of this species; its group size, odds and stock
        widgets.HotkeyLabel{ frame={ b=2, l=35 }, key='CUSTOM_C', label='call', on_activate=self:callback('act_call') },
        widgets.HotkeyLabel{ frame={ b=2, l=43 }, key='CUSTOM_G', label='group size', on_activate=function() self:act_number('size') end },
        widgets.HotkeyLabel{ frame={ b=2, l=57 }, key='CUSTOM_O', label='odds', on_activate=function() self:act_number('odds') end },
        widgets.HotkeyLabel{ frame={ b=2, l=65 }, key='CUSTOM_K', label='stock', on_activate=function() self:act_number('stock') end },
        -- v7.1 (ui; R52): this species' v7 settings (skill level, stoop, fishing, swimmer scavenger, cohesion, water apex, extinct)
        widgets.HotkeyLabel{ frame={ b=2, l=74 }, key='CUSTOM_V', label='v7', on_activate=self:callback('act_v7') },
        widgets.Label{ view_id='status', frame={ b=0, l=0, h=1 }, auto_height=false, text='' },
    }
    self:refresh()
end
function Detail:refresh()
    local L = speciesDetail(self.win.cfg, self.win.pool, self.entry)
    local choices = {}
    for _, l in ipairs(L) do choices[#choices+1] = { text=l } end
    -- v7.1 (ui; R52): the species' v7 rows from the registry, read only here (V sets them)
    local parts = {}
    for _, r in ipairs(PNL.speciesRows(self.entry)) do
        parts[#parts+1] = ('%s %s'):format(r.label:lower(), PNL.valText(r, PNL.value(self.win, r, self.entry.token)))
    end
    if #parts > 0 then
        -- v7.1 (Alpha Four 1.2): above 'eats', not after the history. A predator's eats and eaten-by lists wrap to a
        -- dozen rows, so the v7 line sat below the page's fold (BARK_SCORPION_MAN: not on the screen at all)
        local at = #choices + 1
        for i, l in ipairs(L) do if l:match('^eats ') then at = i; break end end
        table.insert(choices, at, { text=('%-11s %s'):format('v7:', table.concat(parts, ', ')) })
    end
    self.subviews.facts:setChoices(self.win:wrap(choices, self.subviews.facts))
end
-- v7.1 (ui; R52): the per-species v7 rows in a list; Enter toggles or cycles the selected one through its console verb
function Detail:act_v7()
    local rows = PNL.speciesRows(self.entry)
    if #rows == 0 then self:say(self.entry.token .. ': no v7 setting applies to this species.') return end
    local choices = {}
    for _, r in ipairs(rows) do
        local v = PNL.value(self.win, r, self.entry.token)
        choices[#choices+1] = { text=('%-22s %s'):format(r.label, PNL.valText(r, v)), row=r, value=v }
    end
    dialogs.ListBox{ frame_title='v7: ' .. self.entry.token, with_filter=false, choices=choices,
        on_select=function(_, c)
            local r, v = c.row, c.value
            local nv
            if r.type == 'bool' then nv = not v
            elseif r.type == 'enum' then
                local o = r.opts or {}
                for i, x in ipairs(o) do if tostring(x) == tostring(v) then nv = o[i % #o + 1] end end
                nv = nv or o[1]
            end
            if nv == nil then
                dialogs.showInputPrompt(r.label, ('%s (%s..%s; %s = the profile):'):format(r.label, tostring(r.min), tostring(r.max), tostring(r.nilv or '-')), COLOR_WHITE,
                    tostring(v or ''), function(txt) local _, msg = self.win:ctlSet(r.id, txt, self.entry.token); self:refresh(); self:say(msg) end)
                return
            end
            local _, msg = self.win:ctlSet(r.id, tostring(nv), self.entry.token)
            self:refresh(); self:say(msg)
        end }:show()
end
function Detail:say(msg) self.subviews.status:setText({ { text=msg:sub(1, 80), pen=COLOR_LIGHTCYAN } }) end
function Detail:act_allow()
    local e, cfg = self.entry, self.win.cfg
    local on = not isAllowed(cfg, e)
    ROSTER.setActive(cfg, self.win.pool, e, on); self.win:save()
    LEDGER.add('edit', e.layer, '%s %s', e.key, on and 'active' or 'inactive')
    self:refresh(); self.win:refresh()
    self:say(('%s %s.'):format(e.token, on and ('active: ' .. seasonLabel(cfg, e.key)) or 'inactive'))
end
function Detail:act_season(s)
    local e, cfg = self.entry, self.win.cfg
    local ok, why = toggleSeason(cfg, e.key, s)
    if not ok then self:say(('%s: %s.'):format(e.token, why)) return end
    self.win:save(); self:refresh(); self.win:refresh()
    self:say(('%s seasons: %s.'):format(e.token, seasonLabel(cfg, e.key)))
end
-- v6.4.0: raws -> each habitat (or role) in turn -> back to the raws; the pool is rebuilt so every tab agrees
function Detail:act_override(which)
    local cfg, e = self.win.cfg, self.entry
    local field = which .. '_override'
    cfg[field] = cfg[field] or {}
    local cycle = (which == 'habitat') and sw.MODEL.HABITATS or { 'predator', 'prey' }
    local cur, nxt = cfg[field][e.token], nil
    if cur == nil then nxt = cycle[1]
    else for i, v in ipairs(cycle) do if v == cur then nxt = cycle[i + 1] end end end
    cfg[field][e.token] = nxt
    self.win._lastAction = which .. ' override'
    self.win:save()
    LEDGER.add('edit', e.layer, '%s %s: %s', e.token, which, nxt and ('set to ' .. nxt) or 'back to the raws')
    self.win:rebuildData()
    self.entry = self.win.poolByKey[e.key] or e
    self:refresh(); self.win:refresh()
    self:say(('%s %s: %s.'):format(e.token, which, nxt or 'the raws\' reading'))
end
function Detail:act_call()
    local g = loadGroups()
    local ok, why = ENGINE.call(self.win.cfg, g, self.entry); saveGroups(g)
    self:refresh(); self.win:refreshLive()
    self:say((ok and 'Called: %s' or 'Cannot call: %s'):format(why))
end
function Detail:act_number(which)
    local e, cfg = self.entry, self.win.cfg
    local field = (which == 'size') and 'group_size' or which
    local prompt = ({ size = 'Animals per group (blank = the raw\'s cluster range):', odds = 'Weight when its layer gets a wave, at least 1 (blank = the raw\'s):',
                      stock = 'How many remain in the region to arrive (blank = the region\'s own):' })[which]
    dialogs.showInputPrompt(e.token .. ': ' .. which, prompt, COLOR_WHITE, tostring(cfg[field][e.key] or ''),
        function(txt)
            local n = tonumber(txt)
            if txt == '' then cfg[field][e.key] = nil
            elseif n and n >= (which == 'stock' and 0 or 1) then cfg[field][e.key] = math.floor(n) else return end
            self.win._lastAction = which
            self.win:save()
            if which == 'stock' and cfg.stock[e.key] and sw.ROSTER.wants(cfg, e.key, df.global.cur_season) then RESERVE.set(e.key, cfg.stock[e.key]) end
            if which == 'odds' and cfg.enabled then sw.CAVERN.apply(cfg, df.global.cur_season) end
            if which == 'size' and cfg.enabled then PATTERN.sizeApply(cfg) end
            LEDGER.add('edit', e.layer, '%s %s %s', e.key, which, cfg[field][e.key] and tostring(cfg[field][e.key]) or 'back to the raws')
            self:refresh(); self.win:refresh()
            self:say(('%s %s: %s.'):format(e.token, which, cfg[field][e.key] and tostring(cfg[field][e.key]) or 'the raw\'s'))
        end)
end
function Detail:act_group(what)
    local args = { 'seasonal-wildlife', 'groups', what, self.entry.token }
    if what == 'hold' then args[#args+1] = '30' end
    local ok, out = pcall(dfhack.run_command_silent, table.unpack(args))
    self:refresh(); self.win:refreshLive()
    self:say(ok and ((out or ''):gsub('\n', ' ')) or 'failed')
end
DetailScreen = defclass(DetailScreen, gui.ZScreen)
DetailScreen.ATTRS{ focus_path='seasonal-wildlife/detail', win=DEFAULT_NIL, entry=DEFAULT_NIL }
function DetailScreen:init() self:addviews{ Detail{ win=self.win, entry=self.entry } } end

local Screen = defclass(Screen, gui.ZScreen)
Screen.ATTRS{ focus_path='seasonal-wildlife' }
-- v6.3.0: the window opens as wide as the screen allows, up to 130 columns; at 90 the Panel pushed the ninth
-- tab (Ledger) onto a second row under the pages, out of reach (alpha 1 step 1.3 asked for a larger window).
-- The height stays 34 for now; v6.6 fits it to the screen with the layout work.
-- v6.6.0 (W9, alpha 1 step 1.3): the height too -- up to 60 rows, the screen less a margin -- and long lines wrap
-- to the window (Win:wrap) instead of running off its edge.
function Screen:init()
    local scrW, scrH = dfhack.screen.getWindowSize()
    self:addviews{ Win{ frame={ w=math.max(100, math.min((scrW or 104) - 4, 140)), h=math.max(34, math.min((scrH or 38) - 4, 60)) } } }
end
-- Bug 10 (2026-09-16): this used to save the window's config on close. Every action that
-- changes the config already saves it, so the only thing a save here could do is write a
-- STALE copy over settings changed elsewhere while the window was open -- which it did:
-- a window left open across a console reconfigure wiped the roster on dismiss.
Screen.onDismiss = function() view = nil end

view = view or nil
function show_gui()
    if not dfhack.isMapLoaded() then qerror('Load a fort first.') end
    view = view and view:raise() or Screen{}:show()
end

if dfhack_flags and dfhack_flags.module then return end
show_gui()
