-- seasonal-wildlife-controls.lua -- one registry of every control the tool has, and the one code path that reads,
-- checks and sets them. v7.1 (web stream, R54; 1 Oct 2026). The browser companion (seasonal-wildlife-web) renders its
-- Controls tab from this table, and the in-game Panel is meant to render from the same table (the GUI wave), so a
-- control added here appears in both, and both change the game the same way the console does.
--@ module = true
--[====[

seasonal-wildlife-controls
==========================

The control registry of seasonal-wildlife: every switch, slider and choice the tool has, with its config path, type,
range, default, help and the console verb that sets it.

Usage::

    seasonal-wildlife-controls                 the sections and how many controls each holds
    seasonal-wildlife-controls list [SECTION]  every control: id, value, default, range, verb
    seasonal-wildlife-controls get ID          one control's value
    seasonal-wildlife-controls set ID VALUE    set it, through the same verb a player would type
    seasonal-wildlife-controls json            the registry with current values, as the web page reads it

A set is checked against the registry (type and range) before anything runs, then goes through the tool's own console
verb (or, for a Panel switch with no verb, the Panel's own path; for the few config-only keys, one config write with an
undo step and a ledger line). Nothing here evaluates Lua from outside.

]====]

local sw = reqscript('seasonal-wildlife')

--========================================================================================
-- the registry
--========================================================================================
-- A row: { id, sec, grp, label, path, type, min, max, step, unit, opts, verb, help, ... }
--   type   bool | int | float | enum | seasons | text
--   path   dotted path into the config ('hunters.stoop.cooldown'; '{T}' is a creature token on species rows;
--          a number part indexes an array, 'irruption.season_mult.4')
--   verb   the console words after `seasonal-wildlife`, space-separated: '$' is the new value, '@a.b' the current
--          value at that config path (for verbs that take two numbers at once), '{T}' the token
--   words  bool words for '$' (default on/off); invert: the switch shows the opposite of the stored boolean
--   vmap   enum value -> its own verb (when each choice is a different verb)
--   zero / empty / nilv   the word sent for 0 / for '' / the value shown when the key is absent
--   direct the key has no verb: one config write (undo step + ledger line), as the Panel would make it
--   panel  set through PANEL.SWITCHES[panel] (the Panel's own path), for a switch with no on/off verb
--   req    dotted path into the engine module that must exist (a feature from a later merge); absent = unavailable
-- Defaults are read from the engine's defaultConfig() by path; `def` is only the fallback.
SECTIONS, CONTROLS, SPECIES, ACTIONS, READOUTS = {}, {}, {}, {}, {}
local BY, SEC_BY = {}, {}
local cur, curGrp

local function section(id, label, note, x)
    x = x or {}
    cur, curGrp = id, nil
    local s = { id = id, label = label, note = note, status = x.status or id, req = x.req }
    SECTIONS[#SECTIONS+1] = s; SEC_BY[id] = s
end
local function group(name) curGrp = name end
local function add(t)
    t.sec = t.sec or cur; t.grp = t.grp or curGrp; t.id = t.id or t.path
    if BY[t.id] then error('seasonal-wildlife-controls: duplicate control id ' .. t.id) end
    BY[t.id] = t; CONTROLS[#CONTROLS+1] = t
    return t
end
local function merge(t, x) if x then for k, v in pairs(x) do t[k] = v end end; return t end
local function B(path, label, verb, help, x) return add(merge({ type = 'bool', path = path, label = label, verb = verb, help = help }, x)) end
local function I(path, label, min, max, verb, help, x) return add(merge({ type = 'int', path = path, label = label, min = min, max = max, verb = verb, help = help }, x)) end
local function F(path, label, min, max, verb, help, x) return add(merge({ type = 'float', path = path, label = label, min = min, max = max, verb = verb, help = help }, x)) end
local function E(path, label, opts, verb, help, x) return add(merge({ type = 'enum', path = path, label = label, opts = opts, verb = verb, help = help }, x)) end
local function S(t) t.id = t.id or t.path; SPECIES[#SPECIES+1] = t; return t end
local function A(id, label, verb, help, x) ACTIONS[#ACTIONS+1] = merge({ id = id, sec = cur, label = label, verb = verb, help = help }, x) end
local function R(id, label, verb, help, x) READOUTS[#READOUTS+1] = merge({ id = id, sec = cur, label = label, verb = verb, help = help }, x) end

-- ---- the Panel's switches (rows built from PANEL.SWITCHES at run time; see panelRows) ----
section('switches', 'Switches', 'The Panel\'s switches: every on/off the tool has apart from single creatures. All off stops every job and puts back every write; all on restores the switches as they were.',
        { status = 'jobs' })
A('all_on', 'All on', 'panel:allOn', 'The switches as they were before All off, or the usual set; every job starts.', { confirm = true })
A('all_off', 'All off', 'panel:allOff', 'Every job stops and everything the tool wrote into the game is put back.', { confirm = true })
A('rearm', 'Re-arm stopped jobs', 'panel:rearm', 'A job its fuse stopped starts again.')
-- the console verb for each Panel switch; a switch not listed here (or added later) goes through the Panel's own path
SWITCH_VERB = { rotation = { vmap = { [true] = 'enable', [false] = 'disable' } },
    land = 'layer land $', water = 'layer water $', cavern = 'layer cavern $', deep = 'layer deep $',
    groups = 'groups $', cavegate = 'groups cavern $', cohesion = 'groups cohesion $', ecology = 'groups ecology $',
    waterjob = 'water $', coupling = 'groups coupling $', livestock = 'groups livestock $', exhaust = 'exhaust $',
    scavenge = 'scavenge $', curiousreform = 'curious reform $', quietfights = 'alerts $', hunting = 'hunting $',
    irruption = 'irruption $', forage = 'vermin forage $', extinct = 'extinct $' }

-- ---- limits and the release clock (groups stream, R7 R31) ----
section('limits', 'Limits and release clock', 'How many groups each layer holds at once (the map-size formula or one fixed cap, R7), the animal ceilings, and the adaptive release clock that paces new groups (R31).',
        { status = 'groups' })
group('Limits')
E('limits.mode', 'Group cap', { 'formula', 'fixed' }, nil, 'formula: the square root of the embark\'s tiles + 1 on every layer; fixed: one cap on every layer (for slower computers). Caverns keep their own cap.',
  { vmap = { formula = 'limits formula', fixed = 'limits fixed @limits.fixed' }, labels = { formula = 'map-size formula', fixed = 'single fixed cap' } })
I('limits.fixed', 'Fixed cap', 1, 20, 'limits fixed $', 'The one cap on every layer. Setting it switches the cap to fixed.')
I('limits.land.ceiling', 'Land animal ceiling', 0, 400, 'limits land ceiling $', 'The most wild land animals on the map; 0 is none.')
I('limits.water.ceiling', 'Water animal ceiling', 0, 400, 'limits water ceiling $', 'The most wild water animals on the map; 0 is none (R45).')
I('limits.cavern.ceiling', 'Cavern animal ceiling', 0, 400, 'limits cavern ceiling $', 'Holds new cavern arrivals while the caverns are over it; it removes nothing already there.')
group('Arrival pattern')
local PATTERNS = { 'steady', 'burst', 'trickle', 'dawn', 'follow' }
E('patterns.land', 'Land pattern', PATTERNS, 'pattern land $', 'steady: the gate as is; burst: 2-3 releases then a quiet gap; trickle: small draws; dawn: birds and vermin first each season; follow: predators follow prey.')
E('patterns.water', 'Water pattern', PATTERNS, 'pattern water $')
E('patterns.cavern', 'Cavern pattern', PATTERNS, 'pattern cavern $', 'Cavern waves are DF\'s own; the cavern gate takes steady.')
group('Release clock')
B('groups.adaptive', 'Adaptive release clock', 'groups clock $', 'Little\'s law: the gap between releases shortens when a layer is under its target (R31). Off: fixed jitter days.')
F('groups.target_band', 'Target band', 0, 5, 'groups clock band $', 'The layer aims for a count in [cap - band, cap].', { step = 0.1 })
F('groups.catchup', 'Catch-up', 0, 5, 'groups clock catchup $', 'How hard a deficit shortens the gap.', { step = 0.1 })
F('groups.gap_jitter', 'Jitter', 0, 0.9, 'groups clock jitter $', 'Random spread on each release gap.', { step = 0.05 })
F('groups.gap_floor_days', 'Shortest gap', 0.1, 10, 'groups clock floor $', nil, { step = 0.1, unit = 'days' })
I('groups.gap_max_days', 'Longest gap', 1, 60, 'groups clock max $', nil, { unit = 'days' })
F('groups.w_alpha', 'W weight', 0.01, 1, 'groups clock alpha $', 'The exponential weight on the measured stay W.', { step = 0.01 })
I('groups.w_prior_land', 'W prior, land', 1, 200000, 'groups clock prior land $', 'The stay assumed before any group has left.', { unit = 't', step = 500 })
I('groups.w_prior_water', 'W prior, water', 1, 200000, 'groups clock prior water $', nil, { unit = 't', step = 500 })
I('groups.w_prior_cavern', 'W prior, caverns', 1, 200000, 'groups clock prior cavern $', nil, { unit = 't', step = 500 })
B('groups.sync_countdown', 'Groups leave with their leader', nil, 'Drawn and placed groups take their leader\'s leave countdown.', { direct = true })
A('sendoff_land', 'Send off every land group', 'sendoff land', 'Every gated land group walks off; the gate opens.', { confirm = true })
A('sendoff_cavern', 'Send off every cavern group', 'sendoff cavern', 'Every gated cavern group walks off.', { confirm = true })
R('groups_layers', 'Per-layer lines', 'groups layers')

-- ---- the cavern gate (R44) and natives ----
section('caverns', 'Cavern gate and natives', 'Caverns are gated on their own count, five groups per cavern by default (R44); natives can be adopted and counted; animal people are capped in the caverns (R35).',
        { status = 'groups' })
B('groups.cavern', 'Cavern gate', 'groups cavern $', 'Cavern groups gated on their own count and clock.')
I('groups.cavern_cap', 'Cavern cap', 1, 20, 'groups cavern cap $', 'Groups at once per cavern.')
E('groups.cavern_hold', 'Frequency hold', { 'any', 'all', 'off' }, 'groups cavern hold $', 'Over the cap, hold species down: any cavern full, all full, or never.')
B('groups.cavern_hold_mix', 'Keep the season\'s mix', 'groups cavern mix $', 'While held, in-season species keep a tenth of their weight (at least 2) and the rest sit at 1, so the season still decides who comes. Off: every species at 1.')
B('groups.cavern_hold_shared', 'Hold shared species too', 'groups cavern shared $', 'Also hold species that live on the surface.')
B('groups.cavern_trim', 'Trim over the cap', 'groups cavern trim $', 'Send off groups over the cap.')
I('groups.cavern_trim_days', 'Trim every', 1, 30, 'groups cavern trim_days $', nil, { unit = 'days' })
B('groups.cavern_trim_gated', 'Trim DF waves too', 'groups cavern trim_gated $', 'With no resident group to send off, the oldest gated DF wave goes (default on).')
B('groups.natives_cavern', 'Count cavern natives', 'groups natives cavern $', 'Adopt cavern natives as groups and count them against the cap.')
B('groups.natives_land', 'Count surface natives', 'groups natives land $')
B('groups.seeded_water', 'Lead seeded schools', 'groups natives water $', 'DF\'s seeded water schools are led, never counted.')
I('groups.apcap', 'Animal-people cap', 0, 20, 'groups apcap $', 'Animal-people group size in the caverns, lifted while an irruption is on their cavern; 0 is off (R35).', { zero = 'off' })
A('natives_now', 'Adopt natives now', 'groups natives now')

-- ---- leaders, panic, cohesion (R32) ----
section('leaders', 'Leaders, panic and cohesion', 'A group follows its largest adult male; when he dies the group panics and scatters (R32). Cohesion keeps followers within a distance of the leader.',
        { status = 'groups' })
B('groups.panic', 'Panic', 'groups panic $', 'A group whose leader dies flees.')
I('groups.panic_days', 'Panic days', 1, 10, 'groups panic days $', nil, { unit = 'days' })
I('groups.panic_tiles', 'Flight radius', 4, 40, 'groups panic tiles $', nil, { unit = 'tiles' })
E('groups.panic_mode', 'Flight', { 'scatter', 'edge' }, 'groups panic mode $')
B('groups.panic_flocks', 'Flocks panic too', 'groups panic flocks $')
B('groups.reelect_after_panic', 'Re-elect after panic', 'groups panic reelect $', 'A new male may lead once the panic ends.')
B('v7.leader_male', 'Leader: largest adult male', 'groups panic leader $', 'Off: the lowest unit id leads (v6, experiments only).', { words = { 'male', 'lowest' } })
B('groups.cohesion', 'Cohesion', 'groups cohesion $', 'Followers keep near the leader: herd, pack, flock.')
I('groups.follow_herd', 'Herd distance', 1, 30, 'groups cohesion herd $', nil, { unit = 'tiles' })
I('groups.follow_pack', 'Pack distance', 1, 30, 'groups cohesion pack $', nil, { unit = 'tiles' })
I('groups.follow_flock', 'Flock distance', 1, 30, 'groups cohesion flock $', nil, { unit = 'tiles' })
I('groups.follow_school', 'School distance', 1, 30, 'groups cohesion school $', nil, { unit = 'tiles' })
I('groups.follow_pod', 'Pod distance', 1, 20, 'groups cohesion pod $', 'Cetacean pods.', { unit = 'tiles' })

-- ---- roster builder and apex scheduler (roster stream) ----
section('roster', 'Roster builder and apexes', 'The guild roster builder\'s ladder and pyramid, the R13/R26 pick and frequency multipliers, and the apex scheduler that keeps an apex group on the map a share of each season.',
        { status = 'roster' })
group('Apex scheduler')
B('roster.apex.enabled', 'Apex scheduler', 'roster apex $', 'Places apex groups to hold each layer\'s presence target. It acts only after `roster build` seats apexes.')
for _, l in ipairs({ 'land', 'flying', 'water', 'cavern' }) do
    I('roster.apex.presence.' .. l, 'Presence, ' .. l, 0, 95, 'roster apex target ' .. l .. ' $', l == 'land' and 'Percent of the season with an apex group on the map.' or nil, { unit = '%' })
end
I('roster.apex.cap_calm', 'Apex groups at once (calm)', 0, 3, 'roster apex cap $ @roster.apex.cap_savage')
I('roster.apex.cap_savage', 'Apex groups at once (savage)', 0, 3, 'roster apex cap @roster.apex.cap_calm $')
I('roster.apex.residence', 'Apex residence', 1200, 200000, 'roster apex residence $', 'Ticks a placed apex group stays (leave countdown +-20%).', { unit = 't', step = 100 })
group('Ladder and pyramid')
B('roster.units', 'Ladder in units', 'roster set units $', 'On: FREQUENCY / mean group size, so shares are unit shares (R59). Off: wave shares.')
for _, l in ipairs({ 'land', 'flying', 'ocean', 'lake', 'cavern' }) do
    I('roster.pyramid.' .. l .. '.H', 'Pyramid ' .. l .. ': herbivores', 0, 100, 'roster set pyramid ' .. l .. ' $ @roster.pyramid.' .. l .. '.C', nil, { unit = '%' })
    I('roster.pyramid.' .. l .. '.C', 'Pyramid ' .. l .. ': carnivores', 0, 100, 'roster set pyramid ' .. l .. ' @roster.pyramid.' .. l .. '.H $', nil, { unit = '%' })
end
F('roster.biomass_guard', 'Biomass guard', 0, 1, 'roster set biomass_guard $', 'Carnivore biomass at most guard x herbivore biomass on land and in caverns; 0 is off.', { step = 0.05 })
group('Picks and frequencies')
F('roster.ap_pick', 'Animal-people pick', 0, 1, 'roster set ap_pick $', 'R13: pick-weight multiplier.', { step = 0.05 })
F('roster.ap_freq', 'Animal-people frequency', 0, 1, 'roster set ap_freq $', 'R26: FREQUENCY multiplier once seated.', { step = 0.05 })
I('roster.ap_freq_floor', 'Animal-people frequency floor', 0, 100, 'roster set ap_freq_floor $', 'R61: written when the raw\'s FREQUENCY is 0; 0 is off.')
I('roster.ap_vermin_mass', 'Vermin-root animal-people mass', 0, 10000000, 'roster set ap_vermin_mass $', 'R25 in cm3; 0 is its own size.', { unit = 'cm3' })
F('roster.giant_pick', 'Giant pick', 0, 1, 'roster set giant_pick $', nil, { step = 0.05 })
F('roster.giant_freq', 'Giant frequency', 0, 1, 'roster set giant_freq $', nil, { step = 0.05 })
I('roster.pack_bonus', 'Pack bonus', 1, 5, 'roster set pack_bonus $', 'R41: pick multiplier for a group hunter.')
I('roster.apex_odds', 'Apex FREQUENCY', 0, 100, 'roster set apex_odds $', 'R34: 0 keeps the raw\'s own (capped below); N writes N.')
I('roster.apex_raw_cap', 'Apex raw FREQUENCY cap', 0, 100, 'roster set apex_raw_cap $')
B('roster.sn_slots', 'Sentient slots', 'roster set sn_slots $', 'v2.2 SN/SNP slots; off: R13\'s x0.1 in the trophic slots.')
B('roster.giant_boost', 'Giant boost', 'roster set giant_boost $', 'A predator-guild GIANT_* variant is an apex whatever its mass.')
I('roster.fly_apex_min', 'Flying apex mass floor', 0, 1000000, 'roster set fly_apex_min $', nil, { unit = 'cm3', step = 100 })
B('roster.depth_near', 'Depth-near', 'roster set depth_near $', 'R28: a cavern species may sit one layer outside its raw depth range.')
I('roster.gobble_max', 'Vermin per class', 0, 10, 'roster set gobble_max $', 'R51: vermin drawn per class per layer for the edge table.')
group('Predation model (R53)')
for _, k in ipairs({ 'ideal', 'sigma', 'pack_exp', 'k_large', 'need_solo', 'need_herd' }) do
    F('roster.pred.' .. k, 'pred ' .. k, 0.01, 10, 'roster set pred ' .. k .. ' $', nil, { step = 0.05 })
end
A('roster_build', 'Build the roster', 'roster build $', 'Seat every guild by the ladder (one undo step).', { confirm = true, arg = { opts = { 'all', 'land', 'flying', 'water', 'cavern' }, all = '' } })
A('apex_now', 'Apex decision now', 'roster apex now $', 'Run the apex scheduler at once, past the day gate and the target; the group cap holds (console: roster apex now LAYER force).', { arg = { opts = { 'all', 'land', 'flying', 'water', 'cavern', 'invasive' }, all = '' } })
R('roster_summary', 'Roster summary', 'roster')
R('roster_apex', 'Apex scheduler', 'roster apex status')
R('roster_gobble', 'Gobble edges', 'roster gobble')
R('roster_outgun', 'Outgun warnings', 'roster outgun')
R('roster_depth', 'Cavern depths', 'roster depth')
R('roster_aquatic', 'Curated water apexes', 'roster aquatic')
R('realm_table', 'Realm table', 'realm table')

-- ---- ecology and hunters (ecology stream) ----
section('ecology', 'Ecology and hunters', 'Predators and prey related in DF\'s table; per-species skill profiles (solitary, pack), raptor stoops, bears that fish, swimmer scavengers.',
        { status = 'ecology' })
group('Ecology')
I('ecology.cadence', 'Ecology cadence', 500, 12000, 'groups ecology cadence $', 'Ticks between ecology passes (R37).', { unit = 't', step = 100 })
B('ecology.nudge', 'Nudge', nil, 'A predator far from prey for a while is moved nearer (R38: off by default).', { panel = 'nudge' })
B('ecology.livestock', 'Livestock as prey', 'groups livestock $', 'Your own animals become targets.')
B('v7.domestic', 'Domestic prey', 'v7 domestic $', 'The fort\'s livestock and pets are prey of land apexes, mesocarnivores and cavern predators (opt-in).')
group('Solitary and pack')
B('v7.solo', 'Solitary package', 'v7 solo $', 'Solitary hunters get the solitary skill profile.')
B('hunters.pack_on', 'Pack profile', 'hunters pack $', 'Pack hunters get the pack profile; packs are inferred on the map.')
I('hunters.pack_radius', 'Pack radius', 1, 60, 'hunters packradius $', nil, { unit = 'tiles' })
F('v7.pack_floor', 'Pack floor', 0, 1, 'v7 pack_floor $', 'A pair is dropped when the hunting group weighs under this share of the prey.', { step = 0.01 })
F('v7.pack_sneak', 'Pack SNEAK share', 0, 1, 'v7 pack_sneak $', 'Share at which the pack SNEAK bonus applies.', { step = 0.05 })
I('hunters.skills.solo_apex', 'Skill: solitary apex', 0, 20, 'hunters skills solo_apex $', '0-20; 15 Legendary.')
I('hunters.skills.solo_meso', 'Skill: solitary', 0, 20, 'hunters skills solo_meso $')
I('hunters.skills.pack', 'Skill: pack combat', 0, 20, 'hunters skills pack $')
I('hunters.skills.pack_sneak', 'Skill: pack SNEAK', 0, 20, 'hunters skills pack_sneak $')
I('hunters.skills.pack_bonus', 'Skill: pack SNEAK bonus', 0, 20, 'hunters skills pack_bonus $')
group('Raptors')
B('hunters.raptors', 'Raptors armed', 'hunters raptors $', 'BENIGN cleared on raptors so they take land prey (R47).')
B('hunters.stoop.enabled', 'Stoop', 'hunters stoop $', 'A circling raptor dives on prey within range.')
I('hunters.stoop.cooldown', 'Stoop cooldown', 100, 100000, 'hunters stoop cooldown $', nil, { unit = 't', step = 100 })
I('hunters.stoop.range', 'Stoop range', 2, 200, 'hunters stoop range $', nil, { unit = 'tiles' })
I('hunters.stoop.max', 'Stoops per pass', 0, 50, 'hunters stoop max $')
I('hunters.stoop.chance', 'Stoop chance', 0, 100, 'hunters stoop chance $', nil, { unit = '%' })
F('hunters.stoop.prey_ratio', 'Prey size ratio', 0.1, 50, 'hunters stoop ratio $', 'Prey mass at most ratio x the raptor\'s.', { step = 0.1 })
group('Fishers')
B('v7.fishers', 'Fishers', 'v7 fishers $', 'Land predators that fish (bears by default, R33).')
add({ type = 'seasons', path = 'hunters.fish.run', label = 'Fish run seasons', verb = 'hunters fish run $', empty = 'none', help = 'In the run: cooldown halved, lure +1.' })
I('hunters.fish.cooldown', 'Fish cooldown', 100, 100000, 'hunters fish cooldown $', nil, { unit = 't', step = 100 })
I('hunters.fish.range', 'Fish range', 2, 200, 'hunters fish range $', nil, { unit = 'tiles' })
I('hunters.fish.spot', 'Shore search', 1, 20, 'hunters fish spot $', nil, { unit = 'tiles' })
I('hunters.fish.lure', 'Fish lured per action', 0, 10, 'hunters fish lure $')
I('hunters.fish.wait', 'Pathing grace before a hop', 0, 100000, 'hunters fish wait $', nil, { unit = 't', step = 100 })
B('hunters.fish.polar', 'Polar bears swim', 'hunters fish polar $')
B('v7.fish_breathe', 'Fishers breathe water', 'v7 fish_breathe $')
group('Swimmer scavengers')
B('hunters.swim_scav', 'Swimmer scavengers', 'hunters swimscav $', 'Carnivorous swimmers (sharks) scavenge (R42).')
A('ecology_now', 'Ecology pass now', 'groups ecology now')
R('hunters_status', 'Hunters', 'hunters status')
R('hunters_readback', 'Skill readback', 'hunters readback')
R('hunters_cohesion', 'Cohesion table', 'hunters cohesion list')
R('hunters_swimscav', 'Swimmer scavengers', 'hunters swimscav list')

-- ---- water (water stream) ----
section('water', 'Water', 'The tool draws river, lake and sea groups (DF sends none in play), weighted by what is already swimming (R62) and by prey present (R14). Every swimmer enters a registered water body at the map edge, or nearest the centroid of an enclosed lake or pool.',
        { status = 'water' })
group('Draws')
B('water.enabled', 'Water draws', 'water $', 'Turning it on also turns the water layer on.')
I('water.column_levels', 'Deep = column depth of', 1, 20, 'water levels $', 'Stacked water tiles that count as deep.')
B('water.land_aquatic', 'Draw land-listed ocean life', 'water aquatic $', 'R45: AQUATIC species listed on land-layer entries.')
-- v7.1 (ui stream): the fixes stream's water layer and season spill (docs/v7.1/fixes.md section 6)
E('water.layer_mode', 'Water layer', { 'auto', 'on', 'off' }, nil, 'auto: on wherever the map has water (the default); on or off: set by the player and kept.',
  { id = 'water.layer_mode', def = 'auto', vmap = { auto = 'water layer auto', on = 'water layer on', off = 'water layer off' },
    get = function(c) local w = c.water or {}; if not w.layer_set then return 'auto' end; return (c.layers or {}).water and 'on' or 'off' end })
B('water.spill.enabled', 'Season spill', 'water spill $', 'A body with fewer than the minimum drawable species this season borrows the season for active water species (given back at the change).')
I('water.spill.min', 'Spill minimum', 1, 10, 'water spill min $', 'Drawable in-season species a body needs before it borrows.')
I('water.survey_ms', 'Survey budget', 100, 1900, 'water budget $', nil, { unit = 'ms', step = 50 })
E('water.survey_stride', 'Survey sampling', { 1, 2 }, 'water budget @water.survey_ms stride $', '1: every tile; 2: every second x and y.', { labels = { ['1'] = 'every tile', ['2'] = 'every 2nd' } })
F('water.retry_days', 'Retry after an empty draw', 0.1, 30, 'water retry $', nil, { unit = 'days', step = 0.1 })
I('water.pelagic_ref', 'Pelagic size line', 0, 100000000, nil, 'cm3', { direct = true, unit = 'cm3', step = 10000 })
F('water.pelagic_floor', 'Pelagic shallow floor', 0, 1, nil, 'Draw weight floor for a pelagic species on a shallow map.', { direct = true, step = 0.05 })
group('Mix (R62)')
B('water.mix.enabled', 'Weigh by what is swimming', 'water mix $')
F('water.mix.balance', 'Balance strength', 0, 4, 'water mix balance $', nil, { step = 0.1 })
F('water.mix.balance_cap', 'Balance clamp', 1, 20, 'water mix balance_cap $', nil, { step = 0.5 })
F('water.mix.feed', 'Feed predators\' prey', 0, 10, 'water mix feed $', nil, { step = 0.1 })
F('water.mix.pyramid', 'Pyramid steering', 0, 4, 'water mix pyramid $', nil, { step = 0.1 })
I('water.mix.apex_max', 'Apex groups per body', 0, 10, 'water mix apex_max $', '0 is none.')
F('water.mix.cap', 'Mix clamp', 1, 100, 'water mix cap $', nil, { step = 1 })
group('Pull (R14)')
B('water.pull.enabled', 'Prey pulls predators', 'water pull $')
F('water.pull.k', 'Pull gain', 0, 10, 'water pull k $', nil, { step = 0.1 })
F('water.pull.min', 'Pull minimum', 1, 20, 'water pull min $', nil, { step = 0.1 })
F('water.pull.cap', 'Pull ceiling', 1, 20, 'water pull cap $', nil, { step = 0.5 })
B('water.pull.lift_floor', 'Lift shallow floor with prey', 'water pull lift_floor $')
-- v7.1-place (user 2 Oct 2026): the seed by the prey and the stranding guard are removed; the water body registry and
-- the edge/centroid entry replace them
group('Water bodies')
I('water.bodies.min_tiles', 'Smallest body', 1, 1000, 'water bodies min $', 'Water tiles a body needs; smaller is a puddle. Read by the next scan.', { unit = 'tiles' })
I('water.bodies.pool_max', 'Pool under', 0, 100000, 'water bodies pool_max $', 'An enclosed body under this many columns is a pool. Read by the next scan.', { unit = 'columns' })
I('water.bodies.scan_ms', 'Scan slice', 1, 50, 'water bodies slice $', 'CPU a rescan uses per tick; the old registry is used until it is done.', { unit = 'ms' })
A('water_scan', 'Re-scan the water bodies', 'water scan', 'Also runs each season, at load and when a cavern is found.')
R('water_bodies', 'Water bodies', 'water bodies')
A('water_now', 'Draw now', 'water now $', 'One draw at once, using that body\'s community weights.', { arg = { opts = { 'any', 'ocean', 'lake', 'river', 'pool' }, all = '' } })
A('water_survey', 'Re-read the water', 'water survey')
R('water_mix', 'Mix (dry run)', 'water mix')
R('water_depth', 'Column depths', 'water depth')

-- ---- the Aquarium (aquarium stream; docs/v7.1/aquarium.md): see the life of the waters ----
section('aquarium', 'Aquarium', 'See the life of your seas, lakes and rivers: a lens shows the creatures below the level you look at through the water, depth-faded, schools bracketed and leaders ringed, with a legend; ocean waves and foam are drawn; a translucent-water graphics mod is built from your own vanilla sheets.',
        { status = 'aquarium', req = 'V7.AQ' })
group('Lens and legend')
B('aquarium.enabled', 'Aquarium overlays', 'aquarium $', 'Master switch for the lens, legend, waves and veil (graphics mode).')
B('aquarium.lens', 'Lens: life below the view', 'aquarium lens $', 'Creatures in the water below the level you look at, through up to 8 levels of water.')
I('aquarium.depth', 'Lens depth', 1, 8, 'aquarium depth $', 'Levels below the view the lens looks through (DF draws at most 8 lower levels).', { unit = 'levels' })
F('aquarium.fade', 'Fade per level', 0.3, 1, 'aquarium fade $', 'Each level deeper keeps this share of the mark\'s alpha.', { step = 0.05 })
B('aquarium.schools', 'School brackets, leader ring', 'aquarium schools $', 'Corner brackets around each school or pod in view; a ring on its leader.')
E('aquarium.color', 'Lens colours', { 'level', 'kind', 'group' }, 'aquarium color $', 'level: grazer teal, mesopredator amber, apex red (the food pyramid); kind: fish, shark, turtle, crab...; group: one colour per group.',
  { labels = { level = 'food pyramid', kind = 'by kind', group = 'by group' } })
B('aquarium.legend', 'Legend panel', 'aquarium legend $', 'A movable panel listing what swims below the view (gui/overlay moves it).')
I('aquarium.legend_rows', 'Legend rows', 3, 16, 'aquarium rows $')
group('Waves')
E('aquarium.waves', 'Ocean waves', { 'auto', 'on', 'off' }, 'aquarium waves $', 'auto: drawn where the map has an ocean. DF simulates ocean waves but graphics mode draws nothing for them: soft crest lines on its wave fronts, DF\'s own mist where they run up the beach.')
B('aquarium.surf', 'Surf at the waterline', 'aquarium surf $', 'A faint translucent wash on the water at the beach where DF\'s waves run up it.')
B('aquarium.foam', 'Mist on the shore', 'aquarium foam $', 'DF\'s own water-mist art, animated, on the dry beach where its waves and foam run up it (and the water beside); stronger waves, denser mist.')
group('Moving water')
B('aquarium.streaks', 'River streaks', 'aquarium streaks $', 'DF draws no motion on flowing water: soft streaks drift along each river cell\'s flow direction.')
E('aquarium.streaks_layer', 'Streaks: drawn', { 'top', 'under' }, 'aquarium streaks layer $', 'top: over the water (safe, always visible); under: beneath the water sprite, tinted by translucent water (experimental; needs the mod).',
  { labels = { top = 'over the water', under = 'under the water (experimental)' } })
B('aquarium.shimmer', 'Shimmer on shallows', 'aquarium shimmer $', 'A faint moving net of light on still, shallow water.')
I('aquarium.shimmer_depth', 'Shimmer: deepest water', 1, 3, 'aquarium shimmer depth $', 'Shimmer only where the water is this many levels deep or less.', { unit = 'levels' })
group('Translucent water')
E('aquarium.preset', 'Water look (mod preset)', { 'vanilla', 'subtle', 'aquarium', 'clear', 'shallows', 'custom' }, 'aquarium preset $',
  'The graphics mod\'s alpha per water level; applied by Install. shallows keeps full tiles opaque (use it if deep ocean shows black).')
B('aquarium.veil', 'Veil (experimental)', 'aquarium veil $', 'Run-time translucent water for a world created without the mod. Unproven; off by default.')
E('aquarium.bed', 'Bed under the water', { 'auto', 'on', 'off' }, 'aquarium bed $', 'DF draws no floor under water, so translucent water shows a dark fill; the bed draws the sand, soil or stone beneath. auto: on where this world has the mod (or with the veil).')
I('aquarium.bed_depth', 'Bed: levels down', 1, 16, 'aquarium bed depth $', 'Deep water: how far down an open column to look for the floor; deeper beds are darkened, beyond this DF\'s fill stays.', { unit = 'levels' })
F('aquarium.bed_tint', 'Bed: material tint', 0, 1, 'aquarium bed tint $', 'How strongly soil and stone beds take the colour of their material (clay, loam, granite...).', { step = 0.05 })
F('aquarium.bed_absorb', 'Bed: water colour by depth', 0, 2, 'aquarium bed absorb $', 'How fast the bed takes the water\'s colour with depth (red goes first, then green): 0 none, 1 natural, 2 a deep-water body.', { step = 0.1 })
B('aquarium.bed_lift', 'Bed: water below the view', 'aquarium bed lift $', 'Looking down at water a level or more below (a beach, a cliff): DF draws it opaque; lift draws it translucent at your level, with the bed and the swimmers.')
E('aquarium.bed_material', 'Bed: floor', { 'sand-mud', 'auto' }, 'aquarium bed material $', 'sand-mud: sand under salt water, mud under rivers, lakes and pools; auto: the ground\'s own sand, soil or stone.')
B('aquarium.bed_river_mud', 'Bed: rivers as mud', 'aquarium bed river-mud $', 'In a world with the baked mod, rivers and brooks are drawn as water over mud (DF would draw the sea\'s sand there).')
B('aquarium.bed_below', 'Bed: creatures below', 'aquarium bed below $', 'Creatures in the water below your level are shown, greyer and bluer the deeper they are (as DF shows lower levels).')
E('aquarium.bed_river', 'Bed: rivers and brooks', { 'pebbles', 'floor', 'df' }, 'aquarium bed river $', 'pebbles: a gravel bed; floor: the ground\'s own sand, soil or stone; df: DF\'s own river-bed picture (teal).')
group('Budget')
I('aquarium.scan_hz', 'Scans a second', 1, 10, 'aquarium hz $')
F('aquarium.budget_ms', 'Paint budget a frame', 1, 20, 'aquarium budget $', 'Average paint time a layer may take before its fuse counts.', { step = 0.5, unit = 'ms' })
I('aquarium.trip_frames', 'Frames over budget to stop', 5, 600, 'aquarium trip $')
I('aquarium.marks', 'Most marks a frame', 50, 3000, 'aquarium marks $', nil, { step = 50 })
A('aq_install', 'Install or update the mod', 'aquarium install', 'Builds the translucent-water mod from your vanilla sheets into the mods folder, with the preset above. New worlds: tick it in the mod list.', { confirm = true })
A('aq_restore', 'Restore the vanilla look', 'aquarium restore', 'Rewrites the mod with vanilla alpha; worlds that use it still load.', { confirm = true })
A('aq_uninstall', 'Uninstall the mod', 'aquarium uninstall', 'Deletes the generated mod folder (refused while this world uses it).', { confirm = true })
A('aq_rearm', 'Re-arm stopped layers', 'aquarium rearm')
R('aq_status', 'Aquarium status', 'aquarium status')
R('aq_probe', 'Probe: waves and life below', 'aquarium probe')

-- ---- scavenging and curious beasts (scav stream) ----
section('scavenging', 'Scavenging and curious beasts', 'Bone-eaters and carnivorous swimmers find remains after a natural delay, walk to them and eat over visits (R16-R18, R42). Curious thieves steal, then stay (R30).',
        { status = 'scavenging' })
group('Scavenging')
B('scavenge.enabled', 'Scavenging', 'scavenge $', 'Opt-in.')
B('scavenge.natural', 'Natural cadence', 'scavenge natural $', 'Off: the v7.0 sweep.')
B('scavenge.swimmers', 'Swimmers scavenge', 'scavenge swimmers $')
B('scavenge.defer_larger', 'Smaller waits for larger', 'scavenge defer $')
I('scavenge.radius', 'Radius', 3, 200, 'scavenge radius $', 'Caps perception when map-wide is off.', { unit = 'tiles' })
I('scavenge.cadence', 'Pass cadence', 50, 2400, 'scavenge set cadence $', nil, { unit = 't', step = 50 })
group('Discovery')
for _, k in ipairs({ 'small', 'medium', 'large' }) do
    F('scavenge.discover_' .. k .. '_h', 'Found after (' .. k .. ' remains)', 0, 480, 'scavenge set discover_' .. k .. '_h $', k == 'small' and 'Median delay before remains are found.' or nil, { unit = 'h', step = 1 })
end
F('scavenge.discover_sigma', 'Discovery spread', 0, 3, 'scavenge set discover_sigma $', nil, { step = 0.1 })
F('scavenge.discover_min_h', 'Discovery at least', 0, 480, 'scavenge set discover_min_h $', nil, { unit = 'h', step = 1 })
F('scavenge.discover_max_h', 'Discovery at most', 0, 960, 'scavenge set discover_max_h $', nil, { unit = 'h', step = 1 })
I('scavenge.scent_ticks', 'Scent per tile', 0, 600, 'scavenge set scent_ticks $', nil, { unit = 't' })
for _, k in ipairs({ 'land', 'flier', 'swim' }) do
    I('scavenge.perceive_' .. k, 'Perception (' .. k .. ')', 1, 200, 'scavenge set perceive_' .. k .. ' $', nil, { unit = 'tiles' })
end
group('Feeding')
I('scavenge.feeders', 'Feeders at once', 1, 20, 'scavenge set feeders $')
F('scavenge.eat_rate', 'Eat rate', 0.001, 2, 'scavenge set eat_rate $', 'Own mass per hour.', { step = 0.01 })
F('scavenge.gorge', 'Gorge per visit', 0.01, 5, 'scavenge set gorge $', 'Own mass.', { step = 0.05 })
F('scavenge.sated_h', 'Sated for', 0, 480, 'scavenge set sated_h $', nil, { unit = 'h', step = 1 })
I('scavenge.near_tiles', 'Visit range', 1, 20, 'scavenge set near_tiles $', nil, { unit = 'tiles' })
F('scavenge.piece_share', 'Corpse piece share', 0.01, 1, 'scavenge set piece_share $', nil, { step = 0.01 })
F('scavenge.swim_min_kg', 'Smallest scavenging swimmer', 0, 100000, 'scavenge set swim_min_kg $', nil, { unit = 'kg', step = 1 })
group('Movement budget')
I('scavenge.moves_pass', 'Moves per pass', 0, 200, 'scavenge set moves_pass $')
I('scavenge.moves_day', 'Moves per day', 0, 5000, 'scavenge set moves_day $')
I('scavenge.reissue_ticks', 'Walk re-issue', 0, 12000, 'scavenge set reissue_ticks $', nil, { unit = 't', step = 50 })
I('scavenge.hop_tiles', 'Hop length', 1, 50, 'scavenge set hop_tiles $', nil, { unit = 'tiles' })
I('scavenge.hop_wait', 'Hop wait', 0, 24000, 'scavenge set hop_wait $', nil, { unit = 't', step = 50 })
I('scavenge.hop_max', 'No hop from farther than', 0, 200, 'scavenge set hop_max $', nil, { unit = 'tiles' })
I('scavenge.hops_day', 'Hops per day', 0, 1000, 'scavenge set hops_day $')
group('Curious beasts (R30)')
B('curious.reform', 'Curious thieves stay', 'curious reform $', 'A curious beast steals, then that animal loses the habit and stays.')
I('curious.cadence', 'Curious job cadence', 10, 1200, 'curious set cadence $', nil, { unit = 't' })
I('curious.stay_min', 'Stay after theft, at least', 100, 400000, 'curious set stay_min $', nil, { unit = 't', step = 100 })
I('curious.stay_max', 'Stay after theft, at most', 100, 400000, 'curious set stay_max $', nil, { unit = 't', step = 100 })
E('curious.loot', 'Loot', { 'drop', 'keep' }, 'curious loot $')
I('curious.max_rezero', 'Re-zero undo limit', 0, 1000, 'curious set max_rezero $')
B('curious.restore_exit', 'On restore, send them off', nil, 'On disable the countdown goes back to 0 (DF\'s exit).', { direct = true })
B('curious.need_theft', 'Need a theft sign', nil, 'Require a theft sign besides a zero countdown.', { direct = true })
A('scavenge_now', 'Scavenging pass now', 'scavenge now')
A('curious_now', 'Reform pass now', 'curious reform now')
A('scavenge_stats_reset', 'Reset who-ate-what', 'scavenge stats reset', nil, { confirm = true })
R('scavenge_stats', 'Who ate what', 'scavenge stats')
R('scavenge_keys', 'Every scavenging key', 'scavenge keys')
R('curious_status', 'Curious beasts', 'curious status')

-- ---- vermin (vermin stream) ----
section('vermin', 'Vermin eating', 'Gobble wiring writes which vermin classes each consumer eats (R51); foraging walks vermin eaters to real loose vermin on the map (R21); vermin hunting gives DF\'s hunting flag.',
        { status = 'vermin' })
group('Wiring')
B('v7.gobble', 'Gobble wiring', 'v7 gobble $', 'GOBBLE_VERMIN_CLASS written by guild on each matched consumer.')
I('v7.gobble_creature_fallback', 'Short-class fallback', 0, 10, 'v7 gobble_creature_fallback $', 'A class with this many members or fewer also gets a per-creature token; 0 is off.')
E('vermin_eat.source', 'Edge source', { 'rules', 'edges', 'both' }, 'vermin edges $', 'Who eats what: the gobble rules, the builder\'s edge table, or both.')
B('hunting.enabled', 'Vermin hunting', 'hunting $', 'Predatory and water birds dive for vermin; small predators hunt them.')
group('Classes')
for _, c in ipairs({ 'SWV_GROUND_BUG', 'SWV_SOIL', 'SWV_COLONY', 'SWV_FLYING_INSECT', 'SWV_SMALL_BIRD', 'SWV_BAT',
                     'SWV_SMALL_MAMMAL', 'SWV_HERP', 'SWV_SMALL_FISH', 'SWV_OTHER' }) do
    B('vermin_eat.classes.' .. c, c:sub(5):lower():gsub('_', ' '), 'vermin class ' .. c .. ' $', nil, { labelFrom = 'VERMIN.SWV_LABEL.' .. c })
end
group('Foraging (R21)')
B('vermin_eat.forage', 'Vermin foraging', 'vermin forage $')
I('vermin_eat.cadence', 'Forage cadence', 200, 50000, 'vermin forage cadence $', nil, { unit = 't', step = 100 })
I('vermin_eat.radius', 'Forage radius', 3, 60, 'vermin forage radius $', nil, { unit = 'tiles' })
I('vermin_eat.budget', 'Eaters per pass', 1, 64, 'vermin forage budget $')
F('vermin_eat.chance', 'Draw chance', 0, 1, 'vermin forage chance $', nil, { step = 0.05 })
I('vermin_eat.cooldown', 'Per-unit cooldown', 0, 100000, 'vermin forage cooldown $', nil, { unit = 't', step = 100 })
F('vermin_eat.colony', 'Colony pull', 0, 1, 'vermin forage colony $', nil, { step = 0.05 })
F('vermin_eat.diversity', 'Diversity', 0, 10, 'vermin forage diversity $', nil, { step = 0.1 })
B('vermin_eat.log', 'Log likely eats', 'vermin forage log $')
A('forage_now', 'Forage pass now', 'vermin forage now')
R('vermin_census', 'Vermin on the map', 'vermin census')
R('vermin_eats', 'Forage outcomes', 'vermin eats')
R('vermin_edges', 'Edge table', 'vermin edges')
R('vermin_classes', 'SWV classes', 'vermin classes')

-- ---- extinct corrections (extinct stream, R24) ----
section('extinct', 'Extinct corrections', 'Apex odds, grazers, roles, group sizes and fossil realms of DF\'s extinct animals, corrected on load and restored on unload (R24).',
        { status = 'extinct' })
B('extinct.fix', 'Extinct corrections', 'extinct $')
for _, k in ipairs({ { 'freq', 'Apex FREQUENCY' }, { 'grazer', 'Grazers' }, { 'roles', 'Roles' }, { 'cluster', 'Group sizes' },
                     { 'realms', 'Fossil realms' }, { 'units', 'Units on the map' }, { 'stand_down', 'Stand down for mods' } }) do
    B('extinct.' .. k[1], k[2], 'extinct set ' .. k[1] .. ' $')
end
I('extinct.grazer_g', 'Grazer G', 1, 1000, 'extinct set grazer_g $', 'G in the STANDARD_GRAZER formula.')
R('extinct_list', 'Rows', 'extinct list')
R('extinct_mods', 'Mods', 'extinct mods')

-- ---- the v7 switches not shown in another section ----
section('v7', 'v7 switches', 'Each v7.0 behaviour behind its own switch (`v7 KEY on|off|N`). Every change re-applies the v7 raws at once.',
        { status = 'v7' })
B('v7.builder', 'Roster builder', 'v7 builder $', 'Off keeps the matrix and manual roster the only path.')
B('v7.aligned', 'Aligned surface wildlife', 'v7 aligned $', 'Surface GOOD/EVIL wildlife managed where the region matches.')
B('v7.cave_aligned', 'Aligned cavern wildlife', 'v7 cave_aligned $')
B('v7.fanciful', 'Fanciful creatures', 'v7 fanciful $', 'FANCIFUL no longer locks (yeti, sasquatch).')
B('v7.seasons_own', 'Seasons override NO_<season>', 'v7 seasons_own $')
B('v7.scav_mapwide', 'Scavengers map-wide', 'v7 scav_mapwide $')
B('v7.scav_ext', 'Scavengers wade/swim/fallback', 'v7 scav_ext $')
B('v7.civ_hunt', 'Cavern civilisations hunt', 'v7 civ_hunt $')
B('v7.civ_prey', 'Cavern civilisations are prey', 'v7 civ_prey $')
B('v7.fb_safe', 'Never write non-natural units', 'v7 fb_safe $', 'The safety switch: forgotten beasts, megabeasts, titans, demons, night creatures and undead are never written.')
B('v7.sweep', 'Sweep', 'v7 sweep $')
B('v7.sponges', 'Sponges', 'v7 sponges $', 'SPONGE ribbons on the ocean floor.')
B('v7.gate_drain', 'Gate drain', 'v7 gate_drain $')
F('v7.outgun', 'Outgun factor', 0, 10, 'v7 outgun $', 'A prey\'s hunting-group mass over its predator\'s by this factor warns.', { step = 0.1 })
B('v7.outgun_cap', 'Outgun cap', 'v7 outgun_cap $', 'Also caps that prey\'s group size.')
B('v7.realms', 'Realms', 'v7 realms $', 'The builder will not co-seat species of disjoint realms.')
E('realm', 'Realm', { 'off', 'auto' }, 'realm $', 'The embark\'s realm for the geography filter: auto picks one from the embark\'s own species (`realm table`).',
  { optsFrom = 'V7.REALM_ORDER', emptyv = 'off', nilv = 'off' })
A('v7_apply', 'Re-apply v7 raws', 'v7 apply')
R('v7_list', 'Every v7 value', 'v7')

-- ---- irruptions (IRRUPT v2, irruption stream, R4-R6 R10; docs/v7.1/irruption.md sections 6, 7 and 9) ----
-- IRRUPT v2 is merged into v7.1 at 24e8152; every key is set with `irruption set PATH VALUE` (IRRUPT.setKey checks the
-- type and IRRUPT.RANGE). On an engine without it the rows report unavailable (req) rather than sending a verb that
-- would fail; the on/off switch and the v6.1 keys work on both.
section('irruption', 'Cavern irruptions', 'Dwarves in and near a cavern raise its pressure; past the threshold a warning, then waves of the cavern\'s own civ races with behaviour tokens, and agitated cavern animals (R4-R6, R10). Opt-in.',
        { status = 'irruption' })
local V2 = { req = 'IRRUPT.setKey' }
local function irr(t) return merge(merge({}, V2), t) end
local function IB(k, label, help, x) return B('irruption.' .. k, label, 'irruption set ' .. k .. ' $', help, irr(x)) end
local function IN(k, label, min, max, help, x) return (x and x.float and F or I)('irruption.' .. k, label, min, max, 'irruption set ' .. k .. ' $', help, irr(x)) end
local function IF(k, label, min, max, help, x) x = x or {}; x.float = true; x.step = x.step or 0.01; return IN(k, label, min, max, help, x) end
group('Trigger')
B('irruption.enabled', 'Irruptions', 'irruption $', 'Off undoes every write at once.')
IF('threshold', 'Threshold', 0.05, 100, 'Pressure that starts a warning.')
IF('decay', 'Decay per pass', 0, 0.5, nil, { step = 0.001 })
IF('pmax', 'Pressure cap (x threshold)', 1, 20, nil, { step = 0.5 })
IF('src.citizens', 'Per citizen in the band', 0, 10, nil, { step = 0.001 })
IF('src.near', 'Per citizen near', 0, 10, nil, { step = 0.001 })
IN('src.near_z', 'Near: levels above', 0, 50)
IF('src.dig', 'Per dig job', 0, 10, nil, { step = 0.001 })
IF('src.breach', 'Breach (once)', 0, 100, nil, { step = 0.05 })
IF('src.scarcity', 'Scarcity', 0, 10, nil, { step = 0.001 })
IN('src.scar_ref', 'Scarcity: full at', 1, 1000, 'Wild units on the layer that count as full.', { float = true, step = 1 })
IF('src.random', 'Random', 0, 10, nil, { step = 0.001 })
IF('fort.wealth_k', 'Fort wealth weight', 0, 10)
IN('fort.wealth_ref', 'Fort wealth reference', 1, 1000000000, nil, { float = true, step = 1000 })
IF('fort.pop_k', 'Fort population weight', 0, 10)
IN('fort.pop_ref', 'Fort population reference', 1, 1000, nil, { float = true, step = 1 })
for i, s in ipairs({ 'Spring', 'Summer', 'Autumn', 'Winter' }) do IF('season_mult.' .. i, 'Season x ' .. s, 0, 10, nil, { step = 0.05 }) end
IB('need_breach', 'Need a breach', 'No event on a cavern the fort has not reached.')
IB('gap_halve', 'Halve the cavern gap', nil)
IF('gap_share', 'Gap share', 0, 1)
IB('strict_band', 'Strict band', 'Count a citizen in only on a cavern-feature tile.')
IF('warn_min_days', 'Warning at least', 0, 60, nil, { unit = 'days', step = 0.5 })
IF('warn_max_days', 'Warning at most', 0, 60, nil, { unit = 'days', step = 0.5 })
IF('lapse_share', 'Warning lapses below', 0, 1, 'x threshold.')
group('Event')
IN('waves', 'Waves', 1, 20)
IF('size_mult', 'Wave size x cluster max', 0.1, 20, nil, { step = 0.1 })
IN('size_min', 'Wave size at least', 1, 100)
IN('size_cap', 'Wave size at most', 1, 200)
IN('unit_cap', 'Irruption units alive at once', 1, 500)
IF('spacing_min_days', 'Between waves, at least', 0, 60, nil, { unit = 'days', step = 0.5 })
IF('spacing_max_days', 'Between waves, at most', 0, 60, nil, { unit = 'days', step = 0.5 })
IF('stay_days', 'Wave units stay', 1, 200, nil, { unit = 'days', step = 1 })
IN('edge_tiles', 'Entry from the map edge within', 0, 200, nil, { unit = 'tiles' })
IB('lead', 'Waves led', 'Each wave led (R32).')
IB('surge', 'Surge', 'Each wave\'s leader walks toward the access.')
IN('max_active', 'Caverns irrupting at once', 1, 3)
add(irr({ type = 'text', path = 'irruption.species', label = 'Species', verb = 'irruption set species $', pattern = '^[%u%d_]+$', allow = { auto = true }, help = 'auto, or a creature token.' }))
E('irruption.fallback', 'No civ race there', { 'animals', 'none' }, 'irruption set fallback $', nil, irr())
E('irruption.roster', 'Admission', { 'allowed', 'season', 'any' }, 'irruption set roster $', nil, irr())
IB('mix', 'Mix species', 'Each wave picks its species anew.')
group('End and cooldown')
IF('duration_days', 'Longest event', 1, 336, nil, { unit = 'days', step = 1 })
IF('settle_days', 'Settle after the last wave', 0, 60, nil, { unit = 'days', step = 0.5 })
IF('calm_share', 'Calm below', 0, 1, 'No more waves below calm_share x threshold.')
IF('wave_spend', 'Each wave spends', 0, 1, 'x threshold.')
IF('repel_share', 'Repelled at share dead', 0, 1)
IN('repel_dead', 'Repelled at dead', 0, 1000, 'Wins when above 0; both 0 is off.')
IF('cooldown_days', 'Cooldown', 0, 672, nil, { unit = 'days', step = 1 })
E('irruption.end_mode', 'At the end', { 'leave', 'stay' }, 'irruption set end_mode $', nil, irr())
IF('leave_min_days', 'Leave within, at least', 0, 60, nil, { unit = 'days', step = 0.5 })
IF('leave_max_days', 'Leave within, at most', 0, 60, nil, { unit = 'days', step = 0.5 })
group('Behaviour tokens (R10)')
IB('champion', 'Champion', 'One unit per wave carries every enabled token.')
for _, t in ipairs({ { 'crazed', 'CRAZED' }, { 'rage', 'Rage' }, { 'thief', 'Thief' }, { 'sneak', 'Sneak' }, { 'wander', 'Wandering' },
                     { 'meander', 'Meandering' }, { 'linger', 'Lingering' }, { 'mischief', 'MISCHIEVOUS' }, { 'nofear', 'NOFEAR' },
                     { 'ambush', 'AMBUSHPREDATOR' }, { 'trance', 'TRANCES' } }) do
    IB('tokens.' .. t[1] .. '.on', 'Token: ' .. t[2])
    IN('tokens.' .. t[1] .. '.pct', 'Token: ' .. t[2] .. ' share', 0, 100, nil, { unit = '%' })
end
IN('rage_value', 'Rage value', 0, 100)
IN('rage_ticks', 'Rage ticks', 0, 100000, nil, { unit = 't', step = 100 })
IB('rage_hold', 'Rage hold')
IN('sneak_skill', 'Sneak skill', 0, 20)
IF('linger_days', 'Lingering countdown', 1, 336, nil, { unit = 'days', step = 1 })
IN('wander_ticks', 'Wander cadence', 100, 100000, nil, { unit = 't', step = 100 })
IN('wander_steps', 'Wander reach', 2, 200)
IN('meander_ticks', 'Meander cadence', 100, 100000, nil, { unit = 't', step = 100 })
IN('meander_tiles', 'Meander radius', 1, 50, nil, { unit = 'tiles' })
IB('reassert', 'Re-assert the caste cache each pass')
E('irruption.mask_lever', 'Curse masks carried by', { 'wound', 'syndrome' }, 'irruption set mask_lever $', 'wound: saved with the unit; syndrome: DF\'s own route, re-made at each load.', irr())
IB('rehide', 'Re-hide a revealed sneak')
group('Agitation (R5)')
IB('agitate', 'Agitate cavern animals')
IN('agitate_cap', 'Agitated at most', 0, 500)
IB('agitate_benign', 'Agitate benign animals')
IB('agitate_wave', 'Agitate on fallback waves')
group('Messages (R6)')
for _, k in ipairs({ 'warn', 'lapse', 'start', 'wave', 'finish', 'ready' }) do IB('msg.' .. k, 'Announce: ' .. k) end
for _, k in ipairs({ 'warn', 'start', 'wave', 'finish' }) do IB('pause.' .. k, 'Pause on: ' .. k) end
IB('popup', 'Popup at the start')
IB('zoom', 'Zoom to the access')
local CAVERNS = { opts = { '1', '2', '3' } }
A('irr_now', 'Start now', 'irruption now $', 'Start at once in that cavern: no warning, no calm.', merge({ confirm = true, arg = CAVERNS }, V2))
A('irr_stir', 'Stir', 'irruption stir $', 'A forced warning in that cavern.', merge({ arg = CAVERNS }, V2))
A('irr_end', 'End every event', 'irruption end all', 'Writes undone, cooldown starts.', merge({ confirm = true }, V2))
A('irr_cool', 'Clear every cooldown', 'irruption cool all', nil, V2)
A('irr_unpin', 'Unpin pressure', 'irruption unpin')
R('irr_status', 'Irruptions', 'irruption')
R('irr_keys', 'Every irruption key', 'irruption keys', nil, V2)
R('irr_tokens', 'Tokens and levers', 'irruption tokens', nil, V2)

-- ---- per-species rows (the Species page) ----
-- when: which species the row applies to -- pred (non-vermin predator), raptor (guild RP), aquatic (aquatic or
-- semiaquatic predator), extinct (in the extinct table), all (every non-vermin species)
S({ path = 'hunters.skills.species.{T}', label = 'Skill level', type = 'int', min = 0, max = 20, nilv = 'auto', when = 'pred',
    verb = 'hunters skills {T} $', help = '0-20 overriding the profile; auto is the profile (0 = no package).' })
S({ path = 'hunters.stoop.skip.{T}', label = 'Never stoops', type = 'bool', when = 'raptor', verb = 'hunters stoop skip {T} $' })
S({ path = 'v7.fisher_list.{T}', label = 'Fishes', type = 'bool', when = 'pred', verb = 'hunters fish {T} $' })
S({ path = 'hunters.swim_scav_list.{T}', label = 'Swimmer scavenger', type = 'enum', opts = { 'auto', 'on', 'off' }, nilv = 'auto', bool3 = true,
    when = 'aquatic', verb = 'hunters swimscav {T} $' })
S({ path = 'hunters.cohesion.{T}', label = 'Cohesion', type = 'enum', opts = { 'auto', 'solitary', 'pack', 'herd', 'flock', 'school' }, nilv = 'auto',
    when = 'all', verb = 'hunters cohesion {T} $' })
S({ path = 'roster.aquatic_apex.{T}', label = 'Water apex', type = 'enum', opts = { 'off', 'apex', 'pelagic', 'fisher' }, nilv = 'off',
    when = 'pred', verb = 'roster aquatic {T} $', help = 'R43/R49: the curated water apexes.' })
S({ path = 'extinct.skip.{T}', label = 'Extinct correction', type = 'bool', invert = true, when = 'extinct', verb = 'extinct {T} $' })
-- v7.1-place (user 2 Oct 2026): the water body types a species may enter (default: its raws)
S({ path = 'water.bodies_for.{T}', label = 'Water bodies', type = 'enum', nilv = 'default', when = 'water', verb = 'roster water {T} bodies $',
    opts = { 'default', 'ocean', 'lake', 'river', 'pool', 'cavern_pool', 'lake,river', 'lake,pool', 'river,pool', 'lake,river,pool', 'ocean,lake', 'ocean,river',
             'ocean,lake,river,pool' },
    help = 'Body types it may enter; default: its raws (biomes and salinity). Any list from the console: roster water TOKEN bodies TYPES.' })

--========================================================================================
-- reading
--========================================================================================
local function split(path)
    local parts = {}
    for p in tostring(path):gmatch('[^%.]+') do parts[#parts+1] = tonumber(p) or p end
    return parts
end
local function walk(t, path)
    for _, p in ipairs(split(path)) do
        if type(t) ~= 'table' then return nil end
        t = t[p]
    end
    return t
end
local function modField(path)   -- a dotted path into the engine module ('IRRUPT.setKey'), nil when absent
    local ok, v = pcall(walk, sw, path)
    return ok and v or nil
end
local function cfgRO()           -- the shared config, read-only (P7): never mutate it
    if not sw.CACHE.cfg then sw.loadConfig() end
    return sw.CACHE.cfg
end
local DEF
local function defaults()
    if not DEF then local ok, d = pcall(sw.defaultConfig); DEF = ok and d or {} end
    return DEF
end
local function subst(path, tok) return tok and (path:gsub('{T}', tok)) or path end

local function available(row)
    if row.req and not modField(row.req) then return false end
    local s = SEC_BY[row.sec or '']
    if s and s.req and not modField(s.req) then return false end
    return true
end

-- the displayed value of a row (bool, number, string), from cfg (default: the shared config)
local function valueOf(row, cfg, tok)
    if row.get then return row.get(cfg or cfgRO()) end
    local v = walk(cfg or cfgRO(), subst(row.path, tok))
    if v == nil then
        if row.nilv ~= nil then return row.nilv end
        if row.type == 'bool' and row.invert then return true end
        return nil
    end
    if row.emptyv ~= nil and v == '' then return row.emptyv end
    if row.bool3 then return v and 'on' or 'off' end
    if row.invert then return not v end
    return v
end
_ENV.valueOf = valueOf

local function defaultOf(row)
    if row.def ~= nil then return row.def end
    if not row.path or row.path:find('{T}', 1, true) then return nil end
    local v = walk(defaults(), row.path)
    if row.invert and type(v) == 'boolean' then return not v end
    return v
end

--========================================================================================
-- the Panel's switches as rows
--========================================================================================
local function panelRows()
    local out = {}
    for _, swt in ipairs((sw.PANEL or {}).SWITCHES or {}) do
        local v = SWITCH_VERB[swt.id]
        local r = { id = 'switch.' .. swt.id, sec = 'switches', label = swt.label, help = swt.note, type = 'bool', optin = swt.optin or false,
                    get = function(c) return swt.get(c) and true or false end, switch = swt }
        if type(v) == 'table' then r.vmap = v.vmap elseif v then r.verb = v else r.panel = swt.id end
        out[#out+1] = r
    end
    return out
end
local function find(id)
    if BY[id] then return BY[id] end
    if tostring(id):match('^switch%.') then
        for _, r in ipairs(panelRows()) do if r.id == id then return r end end
    end
    for _, r in ipairs(SPECIES) do if r.id == id then return r end end
    return nil
end
_ENV.find = find

--========================================================================================
-- checking a value
--========================================================================================
local function asBool(raw)
    if raw == true or raw == 'on' or raw == 'true' or raw == '1' or raw == 1 then return true end
    if raw == false or raw == 'off' or raw == 'false' or raw == '0' or raw == 0 then return false end
    return nil
end
-- an enum's choices: its own, plus a list read from the engine (optsFrom) when the row names one
local function optsOf(row)
    if not row.optsFrom then return row.opts end
    local o = {}
    for _, x in ipairs(row.opts or {}) do o[#o+1] = x end
    local more = modField(row.optsFrom)
    if type(more) == 'table' then for _, x in ipairs(more) do o[#o+1] = x end end
    return o
end
-- Returns the checked value (the displayed form), or nil and why.
local function validate(row, raw)
    local t = row.type
    if t == 'bool' then
        local b = asBool(raw)
        if b == nil then return nil, 'on or off' end
        return b
    elseif t == 'int' or t == 'float' then
        if row.nilv ~= nil and raw == row.nilv then return row.nilv end
        local n = tonumber(raw)
        if not n or n ~= n or n == math.huge or n == -math.huge then return nil, 'a number' end
        if t == 'int' then
            if n ~= math.floor(n) then return nil, 'a whole number' end
            n = math.floor(n)
        end
        if t == 'float' then n = math.floor(n * 1e6 + 0.5) / 1e6 end   -- what the verb's six decimals carry
        if row.min and n < row.min then return nil, ('at least %s'):format(row.min) end
        if row.max and n > row.max then return nil, ('at most %s'):format(row.max) end
        return n
    elseif t == 'enum' then
        local opts = optsOf(row)
        for _, o in ipairs(opts) do if tostring(o) == tostring(raw) then return o end end
        local names = {}; for _, o in ipairs(opts) do names[#names+1] = tostring(o) end
        return nil, 'one of ' .. table.concat(names, ', ')
    elseif t == 'seasons' then
        local s = tostring(raw or '')
        if s == '' or s == 'none' then return '' end
        if #s > 8 or s:gsub('Sp', ''):gsub('Su', ''):gsub('Au', ''):gsub('Wi', '') ~= '' then return nil, 'season codes: SpSuAuWi, or none' end
        return s
    elseif t == 'text' then
        local s = tostring(raw or '')
        if row.allow and row.allow[s] then return s end
        if #s == 0 or #s > 64 or not s:match(row.pattern or '^[%w_]+$') then return nil, 'a token (letters, digits, _)' end
        return s
    end
    return nil, 'not settable'
end
_ENV.validate = validate

--========================================================================================
-- running a verb (the console's own path)
--========================================================================================
-- The verbs the page may send. Anything else is refused before it reaches the console: `preset` (it replaces the
-- roster), `gui`, `place`, `class(es)` and the debug verbs stay console-only.
VERBS = { roster = true, seasons = true, stock = true, odds = true, size = true, call = true, sendoff = true,
          limits = true, pattern = true, undo = true, layer = true, now = true, water = true, hunting = true,
          groups = true, status = true, ledger = true, hunters = true, scavenge = true, curious = true, vermin = true,
          extinct = true, v7 = true, irruption = true, exhaust = true, alerts = true, realm = true, enable = true,
          disable = true, caverns = true, aquarium = true }
-- `groups` with these subverbs only (adopt, the old nudge and pack stay console-only)
GROUP_SUBS = { hold = true, dismiss = true, layers = true, limits = true, clock = true, adaptive = true, cavern = true,
               panic = true, natives = true, apcap = true, ecology = true, cohesion = true, coupling = true,
               livestock = true, on = true, off = true }
local ARG = '^[%w_:,%.%-]+$'   -- keys, numbers and season codes; no spaces, quotes or separators

local function checkVerb(args)
    if #args == 0 or not VERBS[args[1]] then return false, 'not a verb the page may send: ' .. tostring(args[1]) end
    if args[1] == 'groups' and args[2] and not GROUP_SUBS[args[2]] then return false, 'not a groups subverb the page may send: ' .. tostring(args[2]) end
    if #args > 12 then return false, 'too many words' end
    for _, a in ipairs(args) do
        if type(a) ~= 'string' or #a > 64 or not a:match(ARG) then return false, 'refused an argument: ' .. tostring(a) end
    end
    return true
end
_ENV.checkVerb = checkVerb

local function runVerb(args)
    local ok, why = checkVerb(args)
    if not ok then return false, why end
    local rok, out = pcall(dfhack.run_command_silent, 'seasonal-wildlife', table.unpack(args))
    if not rok then return false, tostring(out) end
    return true, out or ''
end
_ENV.runVerb = runVerb

local function word(v)
    if type(v) == 'number' then
        if v == math.floor(v) and math.abs(v) < 1e15 then return ('%d'):format(v) end
        local s = ('%.6f'):format(v):gsub('0+$', ''):gsub('%.$', '')
        return s
    end
    return tostring(v)
end
-- The console words for setting `row` to `v` (displayed form), or nil when the row has no verb.
local function buildArgs(row, v, tok, cfg)
    local tmpl
    if row.vmap then tmpl = row.vmap[v] end
    tmpl = tmpl or row.verb
    if not tmpl then return nil end
    local w
    if row.type == 'bool' then
        local words = row.words or { 'on', 'off' }
        w = v and words[1] or words[2]
    elseif row.type == 'seasons' and v == '' then w = row.empty or 'none'
    elseif row.zero and v == 0 then w = row.zero
    else w = word(v) end
    local args = {}
    for part in tmpl:gmatch('%S+') do
        if part == '$' then args[#args+1] = w
        elseif part:sub(1, 1) == '@' then
            local cv = walk(cfg, part:sub(2))
            if cv == nil then cv = walk(defaults(), part:sub(2)) end
            args[#args+1] = word(cv)
        else args[#args+1] = subst(part, tok) end
    end
    -- an action's optional argument: '' drops the word
    local out = {}
    for _, a in ipairs(args) do if a ~= '' then out[#out+1] = a end end
    return out
end
_ENV.buildArgs = buildArgs

--========================================================================================
-- the Panel's path and the config-only path
--========================================================================================
local function reschedule(c)
    if c.enabled then sw.enableSched() else sw.disableSched() end
end
local function panelSet(swt, v)
    local before, c = sw.loadConfig(), sw.loadConfig()
    swt.set(c, v)
    -- v7.1 (ui stream): IRRUPT v2 never sets g.armed; every irruption write is undone at once (fixes.md section 6)
    if swt.id == 'irruption' and not v and sw.IRRUPT then
        if sw.IRRUPT.restoreAll then pcall(sw.IRRUPT.restoreAll, 'irruptions off')
        elseif sw.IRRUPT.disarm then local g = sw.loadGroups(); if g.armed then sw.IRRUPT.disarm(c, g, 'irruptions off'); sw.saveGroups(g) end end
    end
    if (swt.id == 'land' or swt.id == 'water' or swt.id == 'cavern') and dfhack.isMapLoaded() then sw.ROSTER.normalize(c, sw.buildPool(c)) end
    sw.UNDO.push(before, 'switch ' .. swt.id)
    sw.saveConfig(c)
    sw.LEDGER.add('edit', '', '%s %s (web)', swt.label, v and 'on' or 'off')
    reschedule(sw.loadConfig())
    return ('%s %s'):format(swt.label, v and 'ON' or 'off')
end
local function directSet(row, v, tok)
    local before, c = sw.loadConfig(), sw.loadConfig()
    local parts = split(subst(row.path, tok))
    local t = c
    for i = 1, #parts - 1 do
        if type(t[parts[i]]) ~= 'table' then return nil, 'no such key ' .. row.path end
        t = t[parts[i]]
    end
    local store = v
    if row.invert then store = not v end
    t[parts[#parts]] = store
    sw.UNDO.push(before, 'web ' .. row.id)
    sw.saveConfig(c)
    sw.LEDGER.add('edit', '', '%s = %s (web)', row.id, tostring(store))
    return ('%s: %s'):format(row.label, tostring(v))
end

--========================================================================================
-- setting a control: check, then the one path
--========================================================================================
-- Returns ok, out (the game's reply), cmd (what ran), value (read back).
local function set(id, raw, tok)
    local row = find(id)
    if not row then return false, 'no such control: ' .. tostring(id) end
    if not available(row) then return false, row.label .. ': not in this version of the tool' end
    if row.path and row.path:find('{T}', 1, true) then
        if not (tok and tok:match('^[%u%d_]+$') and #tok <= 64) then return false, 'a creature token is needed' end
    end
    local v, why = validate(row, raw)
    if v == nil then return false, ('%s: %s'):format(row.label, why) end
    local cfg = cfgRO()
    local args = buildArgs(row, v, tok, cfg)
    local ok, out, cmd
    -- v7.1 (Alpha Four 6.8, 6.13, 6.19): one set, one undo step. A console verb does not push one (only the window,
    -- `roster` edits and the Panel/config paths below did), so a Panel, browser or registry set could not be undone and
    -- Z or `undo` took back an OLDER edit instead. The config before the verb is kept, and pushed after it unless the
    -- verb pushed its own (the ring's newest entry moved).
    local before, ringN, ringTop
    if args and dfhack.isMapLoaded() then
        before = sw.loadConfig()
        local ring = sw.UNDO.load().ring
        local top = ring[#ring]
        ringN, ringTop = #ring, top and (tostring(top.t) .. '|' .. tostring(top.label)) or ''
    end
    if args then
        cmd = 'seasonal-wildlife ' .. table.concat(args, ' ')
        ok, out = runVerb(args)
        if not ok then return false, out, cmd end
    elseif row.panel then
        local swt
        for _, s in ipairs((sw.PANEL or {}).SWITCHES or {}) do if s.id == row.panel then swt = s end end
        if not swt then return false, 'no Panel switch ' .. row.panel end
        cmd = 'Panel: ' .. swt.label
        local pok, res = pcall(panelSet, swt, v)
        if not pok then return false, tostring(res), cmd end
        ok, out = true, res
    elseif row.direct then
        cmd = 'config: ' .. subst(row.path, tok) .. ' = ' .. word(v)
        local pok, res, err = pcall(directSet, row, v, tok)
        if not pok or not res then return false, tostring(err or res), cmd end
        ok, out = true, res
    else
        return false, row.label .. ': no way to set it'
    end
    -- read back: a verb that printed its usage changed nothing; say so instead of reporting success
    local now = valueOf(row, cfgRO(), tok)
    local same = (type(now) == 'number' and type(v) == 'number') and math.abs(now - v) < 1e-6 or tostring(now) == tostring(v)
    if row.type ~= 'seasons' and now ~= nil and not same and not row.vmap then
        return false, ('%s did not change (it reads %s). The game said: %s'):format(row.label, tostring(now), tostring(out):gsub('%s+$', '')), cmd, now
    end
    if before then
        local ring = sw.UNDO.load().ring
        local top = ring[#ring]
        local pushed = #ring ~= ringN or (top and (tostring(top.t) .. '|' .. tostring(top.label)) or '') ~= ringTop
        local was = valueOf(row, before, tok)
        if not pushed and tostring(was) ~= tostring(now) then sw.UNDO.push(before, ('%s %s'):format(row.label, word(v))) end
    end
    return ok, out, cmd, now
end
_ENV.set = set

-- An action: its verb, with its one optional argument checked against its choices.
local function act(id, arg)
    local a
    for _, x in ipairs(ACTIONS) do if x.id == id then a = x end end
    if not a then return false, 'no such action: ' .. tostring(id) end
    if not available(a) then return false, a.label .. ': not in this version of the tool' end
    local w = ''
    if a.arg then
        local okArg = false
        for _, o in ipairs(a.arg.opts) do if tostring(o) == tostring(arg) then okArg = true end end
        if not okArg then return false, a.label .. ': choose one of ' .. table.concat(a.arg.opts, ', ') end
        w = (a.arg.all ~= nil and (arg == 'all' or arg == 'any')) and a.arg.all or tostring(arg)
    end
    if a.verb:match('^panel:') then
        local what = a.verb:sub(7)
        local before, c = sw.loadConfig(), sw.loadConfig()
        local ok, res = pcall(function()
            if what == 'allOn' then
                sw.PANEL.allOn(c); sw.UNDO.push(before, 'all on'); sw.saveConfig(c); reschedule(sw.loadConfig()); return 'All on: every job running.'
            elseif what == 'allOff' then
                local restored = sw.PANEL.allOff(c); sw.UNDO.push(before, 'all off'); sw.saveConfig(c); reschedule(sw.loadConfig())
                return 'All off: every job stopped; restored ' .. tostring(restored) .. '.'
            elseif what == 'rearm' then
                sw.FUSE.reset(); sw.enableSched(); sw.LEDGER.add('fuse', '', 'jobs re-armed from the web'); return 'Every job re-armed.'
            end
            error('unknown panel action ' .. what)
        end)
        return ok, tostring(res), 'Panel: ' .. a.label
    end
    local args = {}
    for part in a.verb:gmatch('%S+') do
        if part == '$' then if w ~= '' then args[#args+1] = w end else args[#args+1] = part end
    end
    local ok, out = runVerb(args)
    return ok, out, 'seasonal-wildlife ' .. table.concat(args, ' ')
end
_ENV.act = act

local function readout(id)
    for _, r in ipairs(READOUTS) do
        if r.id == id then
            if not available(r) then return false, r.label .. ': not in this version of the tool' end
            local args = {}
            for part in r.verb:gmatch('%S+') do args[#args+1] = part end
            local ok, out = runVerb(args)
            return ok, out, 'seasonal-wildlife ' .. r.verb
        end
    end
    return false, 'no such readout: ' .. tostring(id)
end
_ENV.readout = readout

--========================================================================================
-- status sections (shared with the Panel): each a list of lines, read from the engine's own status functions
--========================================================================================
local function lines(x) if type(x) == 'table' then return x elseif x == nil then return {} end; return { tostring(x) } end
local function needMap() if not dfhack.isMapLoaded() then error('no map loaded', 0) end end
STATUS = {
    jobs = function(cfg)
        local out = { tostring(sw.FUSE.status()) }
        for _, j in ipairs(sw.PANEL.jobs(cfg)) do
            local st = (sw.FUSE.stats or {})[j.name] or {}
            out[#out+1] = ('%-16s %s  every %s t  last %d ms, worst %d ms, %d runs'):format(j.label, j.on and 'on ' or 'off', tostring(j.cadence),
                st.last or 0, st.worst or 0, st.runs or 0)
        end
        return out
    end,
    groups = function(cfg, g) needMap(); return lines(sw.GRP.status(cfg, g)) end,
    roster = function(cfg)
        local out = { sw.ROSTER.statusLine(cfg) }
        for _, l in ipairs(lines(sw.ROSTER.apexStatus(cfg))) do out[#out+1] = l end
        for tok, key in pairs((cfg.roster or {}).invasive or {}) do out[#out+1] = ('invasive %s (%s)'):format(tok, key) end
        return out
    end,
    ecology = function(cfg, g)
        needMap()
        local out = lines(sw.ecologyStatus(cfg, g))
        for _, l in ipairs(lines(sw.V7.H.status(cfg, g))) do out[#out+1] = l end
        return out
    end,
    water = function(cfg, g) needMap(); return lines(sw.V7.WAT.statusLines(cfg, g)) end,
    scavenging = function(cfg) return { sw.SCAV.status(cfg), sw.CURIOUS.status(cfg) } end,
    vermin = function(cfg) return { sw.VERMIN.gobbleStatus(cfg), sw.VERMIN.forageStatus(cfg), sw.HUNT.status(cfg) } end,
    extinct = function(cfg) return { sw.V7.EXTINCT.statusLine(cfg) } end,
    aquarium = function(cfg)   -- v7.1 (aquarium stream): the switches, then the overlays' fuses and the mod
        local out = { sw.V7.AQ.statusLine(cfg) }
        local ok, m = pcall(reqscript, 'seasonal-wildlife-aquarium')
        local f = ok and type(m) == 'table' and rawget(m, 'statusLines')
        if f then for i, l in ipairs(f()) do if i > 1 then out[#out+1] = l end end end
        return out
    end,
    v7 = function()
        local ok, a = pcall(sw.V7.alignment)
        return { ok and a and ('embark alignment: %s%s (%d region tiles read)'):format(a.good and 'good' or '', a.evil and ' evil' or (a.good and '' or 'neutral'), a.tiles or 0) or 'embark alignment: not read' }
    end,
    irruption = function(cfg, g)
        if sw.IRRUPT.statusLines then return lines(sw.IRRUPT.statusLines(cfg, g)) end
        return { sw.IRRUPT.status(cfg, g) }
    end,
}
-- One section's lines, timed; never raises (a broken reader is reported as its own line).
local function status(id, cfg, g)
    local f = STATUS[id]
    if not f then return { lines = {}, ms = 0 } end
    local t0 = dfhack.getTickCount()
    local ok, res = pcall(f, cfg, g)
    local ms = dfhack.getTickCount() - t0
    if not ok then return { lines = {}, error = tostring(res), ms = ms } end
    local out = {}
    for _, l in ipairs(res) do out[#out+1] = tostring(l) end
    return { lines = out, ms = ms }
end
_ENV.status = status

--========================================================================================
-- the groups on the map, per layer key (land, water:<body>, cavern:<depth>): the web's group map
--========================================================================================
local function groupMap(cfg, g)
    needMap()
    local now, TPD = sw.absTick(), sw.TICKS_PER_DAY
    local byKey, order = {}, {}
    local function slot(lk)
        if not byKey[lk] then
            local p = sw.GRP.parent(lk)
            local ok, cap = pcall(sw.QUOTA.groupsFor, cfg, lk)
            local c = (g.ctl or {})[lk]
            local due
            if p == 'land' then due = g.next_wave_tick
            elseif p == 'water' then due = (g.next_water_body or {})[lk:sub(7)]
            else due = (g.next_cavern_depth or {})[lk:sub(8)] end
            byKey[lk] = { key = lk, parent = p, cap = ok and cap or 0, target = c and c.target or nil,
                          w_days = ((c and c.W) or cfg.groups['w_prior_' .. tostring(p)] or 0) / TPD,
                          next_days = (due and due > now) and (due - now) / TPD or 0, n = 0, groups = {} }
            order[#order+1] = lk
        end
        return byKey[lk]
    end
    slot('land')
    for _, grp in ipairs(g.groups or {}) do
        local lk = sw.GRP.lk(grp)
        if lk then
            local L = slot(lk)
            local alive, least = 0, nil
            for _, id in ipairs(grp.ids or {}) do
                local u = df.unit.find(id)
                if u and not dfhack.units.isDead(u) then
                    alive = alive + 1
                    local cd = u.animal.leave_countdown
                    if cd and cd > 0 and (not least or cd < least) then least = cd end
                end
            end
            if not grp.seeded then L.n = L.n + 1 end
            L.groups[#L.groups+1] = { token = grp.token, n = alive, leader = grp.leader, panic = grp.panic and true or false,
                native = grp.native and true or false, seeded = grp.seeded and true or false, label = grp.label,
                origin = grp.irruption and 'irruption' or grp.tag and ('apex ' .. tostring(grp.tag)) or grp.placed and 'placed'
                         or grp.drawn and 'tool-drawn' or grp.native and 'native' or grp.seeded and 'seeded' or grp.resident and 'resident' or 'DF wave',
                leaves = least and least / TPD or nil, days_here = (now - (grp.arrived or now)) / TPD }
        end
    end
    local out = {}
    for _, lk in ipairs(order) do out[#out+1] = byKey[lk] end
    return out
end
_ENV.groupMap = groupMap

--========================================================================================
-- the registry as the page reads it: sections, rows with value / default / availability, species rows, actions
--========================================================================================
local function rowOut(r, cfg)
    local o = { id = r.id, sec = r.sec, grp = r.grp, label = r.label, type = r.type, min = r.min, max = r.max, step = r.step,
                unit = r.unit, opts = optsOf(r), help = r.help, optin = r.optin, labels = r.labels, nilv = r.nilv, when = r.when,
                path = r.path, available = available(r) }
    if r.labelFrom then local l = modField(r.labelFrom); if type(l) == 'string' then o.help = l end end
    o.verb = r.verb or (r.vmap and 'by choice') or (r.panel and 'Panel switch') or (r.direct and 'config only') or nil
    if o.available and not (r.path and r.path:find('{T}', 1, true)) then
        local ok, v = pcall(valueOf, r, cfg); if ok then o.value = v end   -- a false is a value (`ok and v or nil` dropped every off switch)
        o.default = defaultOf(r)
    end
    return o
end
local function registry(cfg)
    cfg = cfg or cfgRO()
    local secs = {}
    for _, s in ipairs(SECTIONS) do secs[#secs+1] = { id = s.id, label = s.label, note = s.note, status = s.status, available = (not s.req) or modField(s.req) ~= nil } end
    local rows = {}
    for _, r in ipairs(panelRows()) do rows[#rows+1] = rowOut(r, cfg) end
    for _, r in ipairs(CONTROLS) do rows[#rows+1] = rowOut(r, cfg) end
    local sp = {}
    for _, r in ipairs(SPECIES) do sp[#sp+1] = rowOut(r, cfg) end
    local acts = {}
    for _, a in ipairs(ACTIONS) do acts[#acts+1] = { id = a.id, sec = a.sec, label = a.label, help = a.help, confirm = a.confirm, arg = a.arg and a.arg.opts, available = available(a) } end
    local reads = {}
    for _, r in ipairs(READOUTS) do reads[#reads+1] = { id = r.id, sec = r.sec, label = r.label, verb = r.verb, available = available(r) } end
    -- the per-species maps, so the Species page can show each species' current setting without a request per species
    local maps = {}
    for _, r in ipairs(SPECIES) do maps[r.id] = walk(cfg, (r.path:gsub('%.{T}$', ''))) or {} end
    return { rev = 1, cfg_ver = sw.CACHE.ver, sections = secs, controls = rows, species = sp, actions = acts, readouts = reads, maps = maps }
end
_ENV.registry = registry
_ENV.defaultOf = defaultOf   -- v7.1 (ui stream): the in-game Panel reads these too
_ENV.optsOf = optsOf
_ENV.sectionOf = function(id) return SEC_BY[id] end
_ENV.cfgRO = cfgRO
_ENV.available = available
_ENV.panelRows = panelRows

if dfhack_flags and dfhack_flags.module then return end

--========================================================================================
-- console
--========================================================================================
local args = { ... }
local cmd = args[1]
local function show(v) if v == nil then return '-' end; return tostring(v) end
if not cmd then
    local n = {}
    for _, r in ipairs(CONTROLS) do n[r.sec] = (n[r.sec] or 0) + 1 end
    n.switches = (n.switches or 0) + #panelRows()
    for _, s in ipairs(SECTIONS) do print(('%-12s %3d  %s'):format(s.id, n[s.id] or 0, s.label)) end
    print(('%d species rows, %d actions, %d readouts'):format(#SPECIES, #ACTIONS, #READOUTS))
elseif cmd == 'list' then
    local cfg = cfgRO()
    local all = panelRows()
    for _, r in ipairs(CONTROLS) do all[#all+1] = r end
    for _, r in ipairs(all) do
        if not args[2] or r.sec == args[2] then
            local range = (r.min or r.max) and ('%s..%s'):format(show(r.min), show(r.max)) or (r.opts and table.concat((function() local t = {}; for _, o in ipairs(r.opts) do t[#t+1] = tostring(o) end; return t end)(), '|')) or r.type
            -- v7.1 (web-live ctl.console_list_false): `available and valueOf or 'n/a'` printed n/a for every false value
            -- (36 off switches and false settings); a false is a value, n/a is only a row this engine lacks
            local val = 'n/a'
            if available(r) then val = show(valueOf(r, cfg)) end
            print(('%-38s %-8s %-10s default %-10s %-14s %s%s'):format(r.id, val, r.type, show(defaultOf(r)), range,
                r.verb or (r.vmap and '(by choice)') or (r.panel and '(Panel)') or (r.direct and '(config)') or '', available(r) and '' or '  [not in this version]'))
        end
    end
elseif cmd == 'get' and args[2] then
    local r = find(args[2])
    if not r then qerror('no such control: ' .. args[2]) end
    print(show(valueOf(r, cfgRO(), args[3])))
elseif cmd == 'set' and args[2] and args[3] then
    local ok, out, ran = set(args[2], args[3], args[4])
    if ran then print(ran) end
    print((ok and '' or 'refused: ') .. tostring(out))
elseif cmd == 'json' then
    print(require('json').encode(registry(), { pretty = false }))
else
    print('usage: seasonal-wildlife-controls [list [SECTION] | get ID [TOKEN] | set ID VALUE [TOKEN] | json]')
end
