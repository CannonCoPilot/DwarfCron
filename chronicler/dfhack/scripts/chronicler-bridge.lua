-- chronicler-bridge.lua v9 — DFHack bridge for Chronicler
--
-- Writes comprehensive game state to a JSON file that Chronicler reads
-- over HTTP. Runs as a `repeat` job on the console thread (where CoreSuspend works).
--
-- Setup:
--   1. Copy this file to a dir listed in script-paths.txt
--   2. Start the repeat job:
--      repeat --name chronicler --time 100 --timeUnits ticks --command [ chronicler-bridge ]
--   3. Start PowerShell HTTP server on port 8888 serving DF directory
--   4. Run: chronicler watch --bridge-host <windows-ip>
--
-- Output: chronicler-state.json in the DF root directory
--
-- Data sections (all from df.global):
--   game_time: year, tick, season
--   creature_raws: race_id -> creature_id mapping (934+ entries)
--   unit_summary: fortress dwarves with stress/profession/flags/mood/bio/relationships/family (v8)
--   armies: count + positions
--   buildings: count by type
--   artifacts: named artifact list
--   announcements: cursor-based game reports (lossless)
--   diplomacy: player civ diplomatic relations
--   history: cursor-based events with payloads (lossless)
--   world_info: world name, fortress name, civ/site IDs
--   entities: nearby civilizations with names and types
--   dwarf_skills: per-dwarf full skill lists
--   dwarf_emotions: per-dwarf emotion/thought vectors (v6)
--   dwarf_personality: per-dwarf traits, values, needs, dreams, attributes (v7)
--   zones: fortress civzones with types and assignments (v6)
--   event_collections: active wars/battles/sieges (v6)
--   squads: military squads with members and orders (v6)
--   mandates: noble mandates with items and timeouts (v6)
--   incidents: crimes and incidents with victims/criminals (v6)
--   reactive_events: buffered eventful callbacks — deaths, items, jobs, invasions, syndromes (v8)
--   skill_changes: per-dwarf skill rating deltas since last cycle (v8)
--   belief_systems: religious belief systems with deity worship (v9, memory-only)
--   cultural_identities: ethics/values per cultural identity (v9, memory-only)
--   occupations: tavern keepers, scholars, performers (v9, memory-only)
--   interaction_instances: active curses/syndromes (v9, memory-only)
--   fortress_state: fortress progression snapshot (v9, once/season)
--   daily_events: births, marriages, coming-of-age (v9, fortress mode)

local json = require('json')

-- ── Persistent state (survives across repeat ticks) ─────────────────
-- These globals track cursors so we never miss events between ticks.
chronicler_state = chronicler_state or {}
chronicler_state.last_report_id = chronicler_state.last_report_id or -1
chronicler_state.last_event_id = chronicler_state.last_event_id or -1

-- ── v8: Eventful subscription buffers ───────────────────────────────
-- Events accumulate between bridge cycles via DFHack eventful callbacks.
-- Flushed (swapped) each time write_state() runs.

chronicler_state.pending_events = chronicler_state.pending_events or {
    unit_deaths = {},
    new_units = {},
    items_created = {},
    jobs_completed = {},
    syndromes = {},
    invasions = {},
}

-- v8: Skill snapshot for delta tracking (unit_id -> {skill_id -> rating})
chronicler_state.skill_snapshots = chronicler_state.skill_snapshots or {}

-- v8: Eventful initialization flag
chronicler_state.eventful_init = chronicler_state.eventful_init or false

-- Helper: safely convert DF CP437 string to UTF-8
local function to_utf8(s)
    if s and #s > 0 then
        return dfhack.df2utf(s) or s
    end
    return nil
end

-- Helper: translate a language_name to UTF-8 string
local function translate_name(name, english)
    if name and name.has_name then
        return dfhack.df2utf(dfhack.translation.translateName(name, english or false))
    end
    return nil
end

-- ══════════════════════════════════════════════════════════════════════
-- v8: EVENTFUL SUBSCRIPTIONS + ENRICHMENT FUNCTIONS
-- ══════════════════════════════════════════════════════════════════════

-- ── Death Cause Enrichment ──────────────────────────────────────────
-- Searches recent incidents for a matching death, returning cause + killer info.

local function get_death_cause(unit_id)
    local inc_ok, incidents = pcall(function()
        return df.global.world.incidents.all
    end)
    if not inc_ok or not incidents then return nil end

    -- Search backwards through recent incidents (deaths are near the end)
    for i = #incidents - 1, math.max(0, #incidents - 100), -1 do
        local incident = incidents[i]
        if incident.victim == unit_id then
            local result = {
                death_cause_id = incident.death_cause,
            }
            -- Resolve enum name
            local dc_ok, dc_name = pcall(function()
                return df.death_type[incident.death_cause]
            end)
            if dc_ok and dc_name then
                result.death_cause = dc_name
            else
                result.death_cause = tostring(incident.death_cause)
            end
            -- Killer info
            if incident.criminal and incident.criminal >= 0 then
                local killer = df.unit.find(incident.criminal)
                if killer then
                    result.killer_unit_id = incident.criminal
                    result.killer_race = killer.race
                    result.killer_hf_id = killer.hist_figure_id
                    if killer.name and killer.name.has_name then
                        result.killer_name = dfhack.df2utf(dfhack.translation.translateName(killer.name))
                    end
                end
            end
            return result
        end
    end
    return nil
end

-- ── Family Chain Extraction ─────────────────────────────────────────
-- Extracts parent/spouse/children HF IDs from a unit's relationships.

local function get_family_chain(unit)
    local family = {}

    -- Direct relationship IDs (Mother, Father, Spouse)
    local rel_ok, _ = pcall(function()
        if unit.relationship_ids.Mother >= 0 then
            family.mother_hf_id = unit.relationship_ids.Mother
        end
        if unit.relationship_ids.Father >= 0 then
            family.father_hf_id = unit.relationship_ids.Father
        end
        if unit.relationship_ids.Spouse >= 0 then
            family.spouse_hf_id = unit.relationship_ids.Spouse
        end
    end)

    -- Children via historical figure links
    if unit.hist_figure_id >= 0 then
        local hf_ok, _ = pcall(function()
            local hf = df.historical_figure.find(unit.hist_figure_id)
            if hf then
                local children = {}
                for _, link in ipairs(hf.histfig_links) do
                    if link._type == df.histfig_hf_link_childst then
                        table.insert(children, link.target_hf)
                    end
                end
                if #children > 0 then
                    family.children_hf_ids = children
                end
            end
        end)
    end

    if next(family) then
        return family
    end
    return nil
end

-- ── Book Detection ──────────────────────────────────────────────────
-- Extracts book title from an item (for written works).

local function get_book_title(item)
    local ok, title = pcall(function()
        return dfhack.items.getBookTitle(item)
    end)
    if ok and title and title ~= '' then
        return dfhack.df2utf(title)
    end
    return nil
end

-- ── Eventful Initialization ─────────────────────────────────────────
-- Subscribe to DFHack eventful callbacks (once per session).

local function init_eventful()
    if chronicler_state.eventful_init then return end

    local ev_ok, eventful = pcall(function()
        return require('plugins.eventful')
    end)
    if not ev_ok or not eventful then
        dfhack.printerr('[Chronicler] eventful plugin not available — reactive events disabled')
        return
    end

    -- UNIT_DEATH: enrich with death cause immediately
    eventful.onUnitDeath['chronicler'] = function(unit_id)
        local entry = {
            unit_id = unit_id,
            tick = dfhack.world.ReadCurrentTick(),
        }
        -- Enrich with death cause from incidents
        local cause = get_death_cause(unit_id)
        if cause then
            entry.death_cause = cause.death_cause
            entry.death_cause_id = cause.death_cause_id
            entry.killer_unit_id = cause.killer_unit_id
            entry.killer_name = cause.killer_name
            entry.killer_race = cause.killer_race
            entry.killer_hf_id = cause.killer_hf_id
        end
        -- Unit name for immediate identification
        local unit = df.unit.find(unit_id)
        if unit and unit.name and unit.name.has_name then
            entry.name = dfhack.df2utf(dfhack.translation.translateName(unit.name))
            entry.race = unit.race
            entry.hf_id = unit.hist_figure_id
        end
        table.insert(chronicler_state.pending_events.unit_deaths, entry)
    end

    -- UNIT_NEW_ACTIVE: new unit appeared in active list
    eventful.onUnitNewActive['chronicler'] = function(unit_id)
        local entry = {
            unit_id = unit_id,
            tick = dfhack.world.ReadCurrentTick(),
        }
        local unit = df.unit.find(unit_id)
        if unit then
            entry.race = unit.race
            entry.civ_id = unit.civ_id
            if unit.name and unit.name.has_name then
                entry.name = dfhack.df2utf(dfhack.translation.translateName(unit.name))
            end
        end
        table.insert(chronicler_state.pending_events.new_units, entry)
    end

    -- ITEM_CREATED: detect books and notable items
    eventful.onItemCreated['chronicler'] = function(item_id)
        local item = df.item.find(item_id)
        if not item then return end
        local entry = {
            item_id = item_id,
            tick = dfhack.world.ReadCurrentTick(),
            item_type = item:getType(),
        }
        -- Check for book title
        local title = get_book_title(item)
        if title then
            entry.book_title = title
        end
        table.insert(chronicler_state.pending_events.items_created, entry)
    end

    -- JOB_COMPLETED
    eventful.onJobCompleted['chronicler'] = function(job)
        table.insert(chronicler_state.pending_events.jobs_completed, {
            job_type = tostring(job.job_type),
            pos = {x = job.pos.x, y = job.pos.y, z = job.pos.z},
            tick = dfhack.world.ReadCurrentTick(),
        })
    end

    -- SYNDROME: tracks syndrome onset (injuries, illnesses, curses)
    eventful.onSyndrome['chronicler'] = function(unit_id, syndrome_index)
        table.insert(chronicler_state.pending_events.syndromes, {
            unit_id = unit_id,
            syndrome_index = syndrome_index,
            tick = dfhack.world.ReadCurrentTick(),
        })
    end

    -- INVASION — enrich with army controller composition data
    eventful.onInvasion['chronicler'] = function(invasion_id)
        local entry = {
            invasion_id = invasion_id,
            tick = dfhack.world.ReadCurrentTick(),
        }
        -- Look up army controller for composition data
        local ok, _ = pcall(function()
            local controllers = df.global.world.army_controllers.all
            for i = 0, #controllers - 1 do
                local ac = controllers[i]
                if ac.id == invasion_id then
                    entry.entity_id = ac.entity_id
                    entry.target_site_id = ac.site_id
                    entry.master_hf_id = ac.master_hf
                    -- Resolve entity name and race
                    if ac.entity_id >= 0 then
                        local ent = df.historical_entity.find(ac.entity_id)
                        if ent then
                            entry.entity_name = dfhack.TranslateName(ent.name)
                            entry.entity_race_id = ent.race
                            if ent.race >= 0 then
                                local cr = df.creature_raw.find(ent.race)
                                if cr then
                                    entry.race = cr.name[0]
                                end
                            end
                        end
                    end
                    -- Count total army members across controlled armies
                    local total_members = 0
                    local squad_count = 0
                    for j = 0, #df.global.world.armies.all - 1 do
                        local army = df.global.world.armies.all[j]
                        if army.controller_id == ac.id then
                            total_members = total_members + #army.members
                            squad_count = squad_count + #army.squads
                        end
                    end
                    entry.total_members = total_members
                    entry.squad_count = squad_count
                    break
                end
            end
        end)
        table.insert(chronicler_state.pending_events.invasions, entry)
    end

    -- Enable event checking (0 = every tick for immediate capture)
    eventful.enableEvent(eventful.eventType.UNIT_DEATH, 0)
    eventful.enableEvent(eventful.eventType.UNIT_NEW_ACTIVE, 0)
    eventful.enableEvent(eventful.eventType.ITEM_CREATED, 0)
    eventful.enableEvent(eventful.eventType.JOB_COMPLETED, 0)
    eventful.enableEvent(eventful.eventType.SYNDROME, 0)
    eventful.enableEvent(eventful.eventType.INVASION, 0)

    chronicler_state.eventful_init = true
    print('[Chronicler] v8 eventful subscriptions active')
end

-- ── Flush Event Buffers ─────────────────────────────────────────────
-- Atomically swap buffers and return accumulated events since last cycle.

local function flush_events()
    local events = chronicler_state.pending_events
    chronicler_state.pending_events = {
        unit_deaths = {},
        new_units = {},
        items_created = {},
        jobs_completed = {},
        syndromes = {},
        invasions = {},
    }
    -- Count total events
    local total = 0
    for _, buf in pairs(events) do
        total = total + #buf
    end
    events.total_count = total
    return events
end

-- ── Skill Delta Tracking ────────────────────────────────────────────
-- Compares current skill ratings against stored snapshot; returns changes.

local function get_skill_changes()
    local units = df.global.world.units.active
    local player_race = df.global.plotinfo.race_id
    local player_civ = df.global.plotinfo.civ_id
    local changes = {}
    local new_snapshots = {}

    for i = 0, #units - 1 do
        local u = units[i]
        if u.race == player_race and u.civ_id == player_civ
           and not dfhack.units.isDead(u)
           and u.status and u.status.current_soul then

            local uid = u.id
            local prev = chronicler_state.skill_snapshots[uid] or {}
            local curr = {}
            local unit_changes = {}

            local soul_skills = u.status.current_soul.skills
            for j = 0, #soul_skills - 1 do
                local sk = soul_skills[j]
                local sid = sk.id
                curr[sid] = sk.rating
                local old_rating = prev[sid] or 0
                if sk.rating > old_rating then
                    table.insert(unit_changes, {
                        skill_id = sid,
                        skill_name = df.job_skill[sid] or tostring(sid),
                        old_rating = old_rating,
                        new_rating = sk.rating,
                    })
                end
            end

            new_snapshots[uid] = curr
            if #unit_changes > 0 then
                local entry = {
                    unit_id = uid,
                    changes = unit_changes,
                }
                if u.name and u.name.has_name then
                    entry.first_name = to_utf8(u.name.first_name)
                end
                table.insert(changes, entry)
            end
        end
    end

    chronicler_state.skill_snapshots = new_snapshots
    return {
        dwarf_count = #changes,
        dwarves = changes,
    }
end

-- ── Game Time ──────────────────────────────────────────────────────────

local function get_game_time()
    return {
        cur_year = df.global.cur_year,
        cur_year_tick = df.global.cur_year_tick,
        cur_season = df.global.cur_season,
    }
end

-- ── Creature Raws ──────────────────────────────────────────────────────

local function get_creature_raws()
    local raws = {}
    local creatures = df.global.world.raws.creatures.all
    for i = 0, #creatures - 1 do
        local cr = creatures[i]
        raws[tostring(i)] = to_utf8(cr.creature_id) or cr.creature_id
    end
    return raws
end

-- ── Unit Summary (enriched with flags/mood in v6) ────────────────────

local function get_unit_summary()
    local units = df.global.world.units.active
    local total = #units
    local by_race = {}
    local dwarves = {}
    local player_race = df.global.plotinfo.race_id

    for i = 0, total - 1 do
        local u = units[i]
        -- Count by race
        local rid = u.race
        by_race[rid] = (by_race[rid] or 0) + 1

        -- Capture fortress dwarves (player race + civ match)
        if rid == player_race and u.civ_id == df.global.plotinfo.civ_id then
            local entry = {
                id = u.id,
                hist_fig_id = u.hist_figure_id,
                pos_x = u.pos.x,
                pos_y = u.pos.y,
                pos_z = u.pos.z,
            }
            -- Name: full translated name + first name
            if u.name and u.name.has_name then
                entry.name = dfhack.df2utf(dfhack.translation.translateName(u.name))
                entry.first_name = to_utf8(u.name.first_name)
            end
            -- Profession
            entry.profession = u.profession
            -- Alive check
            entry.is_alive = not dfhack.units.isDead(u)
            -- Stress from personality
            if u.status and u.status.current_soul then
                local pers = u.status.current_soul.personality
                entry.stress = pers.stress
                entry.focus = pers.current_focus
                entry.longterm_stress = pers.longterm_stress
                entry.combat_hardened = pers.combat_hardened
            end
            -- Squad
            if u.military and u.military.squad_id >= 0 then
                entry.squad_id = u.military.squad_id
            end

            -- v6: enriched flags
            entry.has_mood = u.flags1.has_mood
            entry.had_mood = u.flags1.had_mood
            entry.active_invader = u.flags1.active_invader
            entry.ghostly = u.flags3.ghostly

            -- Mood enum (None=-1, Fey=0..Traumatized=9)
            entry.mood = u.mood

            -- Tantrum via soldier_mood (not in flags)
            local sm_ok, sm = pcall(function()
                return u.body.physical.soldier_mood
            end)
            if sm_ok then
                entry.soldier_mood = sm
            end

            -- Pregnancy
            entry.pregnancy_timer = u.pregnancy_timer
            if u.pregnancy_timer > 0 then
                entry.pregnancy_spouse = u.pregnancy_spouse
            end

            -- v7: Biographical data
            entry.birth_year = u.birth_year
            entry.birth_time = u.birth_time
            entry.old_year = u.old_year
            entry.sex = u.sex
            entry.caste = u.caste

            -- v7: Death cause (for dead units still in list)
            if dfhack.units.isDead(u) then
                local dc_ok, dc = pcall(function() return u.counters.death_cause end)
                if dc_ok and dc then
                    entry.death_cause = dc
                end
            end

            -- v7: Cultural identity
            local ci_ok, ci = pcall(function() return u.cultural_identity end)
            if ci_ok and ci and ci >= 0 then
                entry.cultural_identity = ci
            end

            -- v7: Relationships (9 slots — histfig IDs)
            local rel_ok, _ = pcall(function()
                local rels = {}
                local rel_types = {'PetOwner','Spouse','Mother','Father','LastAttacker','GroupLeader','Draggee','Dragger','RiderMount'}
                for j, rtype in ipairs(rel_types) do
                    local hfid = u.relationship_ids[j-1]  -- 0-indexed
                    if hfid and hfid > -1 then
                        rels[rtype] = hfid
                    end
                end
                if next(rels) then
                    entry.relationships = rels
                end
            end)

            -- v8: Family chain (parent/spouse/children HF IDs)
            local family = get_family_chain(u)
            if family then
                entry.family = family
            end

            table.insert(dwarves, entry)
        end
    end

    -- Convert by_race to string keys for JSON
    local race_counts = {}
    for rid, count in pairs(by_race) do
        race_counts[tostring(rid)] = count
    end

    return {
        total_active = total,
        race_counts = race_counts,
        fortress_units = dwarves,
        fortress_count = #dwarves,
    }
end

-- ── Armies ─────────────────────────────────────────────────────────────

local function get_armies()
    local armies = df.global.world.armies.all
    local count = #armies
    local list = {}

    -- Build controller lookup for enrichment
    local controller_cache = {}
    pcall(function()
        local controllers = df.global.world.army_controllers.all
        for i = 0, #controllers - 1 do
            local ac = controllers[i]
            local info = {
                entity_id = ac.entity_id,
                site_id = ac.site_id,
                master_hf_id = ac.master_hf,
            }
            -- Resolve entity name + race
            if ac.entity_id >= 0 then
                local ent = df.historical_entity.find(ac.entity_id)
                if ent then
                    info.entity_name = dfhack.TranslateName(ent.name)
                    info.entity_race_id = ent.race
                    if ent.race >= 0 then
                        local cr = df.creature_raw.find(ent.race)
                        if cr then info.race = cr.name[0] end
                    end
                end
            end
            controller_cache[ac.id] = info
        end
    end)

    -- Cap at 50 to keep JSON size reasonable
    local limit = math.min(count, 50)
    for i = 0, limit - 1 do
        local a = armies[i]
        local entry = {
            id = a.id,
            pos_x = a.pos.x,
            pos_y = a.pos.y,
            member_count = #a.members,
            squad_count = #a.squads,
            controller_id = a.controller_id,
        }
        -- Attach controller enrichment if available
        local ci = controller_cache[a.controller_id]
        if ci then
            entry.entity_id = ci.entity_id
            entry.entity_name = ci.entity_name
            entry.race = ci.race
            entry.target_site_id = ci.site_id
        end
        table.insert(list, entry)
    end

    return {
        count = count,
        armies = list,
    }
end

-- ── Buildings ──────────────────────────────────────────────────────────

local function get_buildings()
    local buildings = df.global.world.buildings.all
    local count = #buildings
    local by_type = {}

    for i = 0, count - 1 do
        local b = buildings[i]
        local bt = b:getType()
        by_type[bt] = (by_type[bt] or 0) + 1
    end

    -- Convert to string keys
    local type_counts = {}
    for bt, cnt in pairs(by_type) do
        type_counts[tostring(bt)] = cnt
    end

    return {
        total = count,
        by_type = type_counts,
    }
end

-- ── Artifacts ──────────────────────────────────────────────────────────

local function get_artifacts()
    local artifacts = df.global.world.artifacts.all
    local count = #artifacts
    local named = {}

    for i = 0, count - 1 do
        local a = artifacts[i]
        if a.name and a.name.has_name then
            local entry = {
                id = a.id,
                name = dfhack.df2utf(dfhack.translation.translateName(a.name)),
                name_english = dfhack.df2utf(dfhack.translation.translateName(a.name, true)),
                site_id = a.site,
            }
            if a.item then
                entry.item_type = a.item:getType()
            end
            table.insert(named, entry)
        end
        if #named >= 200 then break end
    end

    return {
        total = count,
        named_count = #named,
        artifacts = named,
    }
end

-- ── Announcements (cursor-based — lossless in v6) ────────────────────

local function get_announcements()
    local reports = df.global.world.status.reports
    local count = #reports
    local list = {}
    local cursor = chronicler_state.last_report_id

    -- Find starting index: scan from end to find first report after cursor
    local start_idx = count  -- default: nothing new
    if cursor < 0 then
        -- First run: grab last 50 reports for initial context
        start_idx = math.max(0, count - 50)
    else
        -- Scan backwards to find cursor position efficiently
        for i = count - 1, 0, -1 do
            if reports[i].id <= cursor then
                start_idx = i + 1
                break
            end
            if i == 0 then start_idx = 0 end
        end
    end

    -- Cap at 200 per tick to prevent JSON bloat during event bursts
    local cap = math.min(count, start_idx + 200)
    for i = start_idx, cap - 1 do
        local r = reports[i]
        table.insert(list, {
            id = r.id,
            text = dfhack.df2utf(r.text) or '',
            year = r.year,
            time = r.time,
            type = r.type,
        })
    end

    -- Update cursor to highest seen ID
    if #list > 0 then
        chronicler_state.last_report_id = list[#list].id
    end

    return {
        total = count,
        cursor = chronicler_state.last_report_id,
        new_count = #list,
        recent = list,
    }
end

-- ── Diplomacy (per-entity, not world-level) ──────────────────────────

local function get_diplomacy()
    local civ_id = df.global.plotinfo.civ_id
    local civ = df.historical_entity.find(civ_id)
    if not civ then
        return { civ_id = civ_id, error = 'player civ not found' }
    end

    local relations = {}
    local res_ok, res = pcall(function() return civ.resources end)
    if res_ok and res then
        local dip_ok, dip = pcall(function() return res.diplomacy end)
        if dip_ok and dip then
            local state_ok, states = pcall(function() return dip.state end)
            if state_ok and states then
                for i = 0, #states - 1 do
                    local s = states[i]
                    table.insert(relations, {
                        entity_id = s.group_id,
                        relation = s.relation,
                    })
                end
            end
        end
    end

    return {
        civ_id = civ_id,
        civ_name = dfhack.df2utf(dfhack.translation.translateName(civ.name)),
        relation_count = #relations,
        relations = relations,
    }
end

-- ── History (cursor-based with payloads in v6) ───────────────────────

local function get_history_summary()
    local figures = df.global.world.history.figures
    local events = df.global.world.history.events
    local count = #events
    local cursor = chronicler_state.last_event_id

    -- Find starting index via cursor
    local start_idx = count
    if cursor < 0 then
        -- First run: grab last 50 events
        start_idx = math.max(0, count - 50)
    else
        for i = count - 1, 0, -1 do
            if events[i].id <= cursor then
                start_idx = i + 1
                break
            end
            if i == 0 then start_idx = 0 end
        end
    end

    -- Cap at 100 per tick
    local recent = {}
    local cap = math.min(count, start_idx + 100)
    for i = start_idx, cap - 1 do
        local ev = events[i]
        local entry = {
            id = ev.id,
            type = ev:getType(),
            year = ev.year,
            seconds = ev.seconds,
        }

        -- Extract common payload fields via pcall (structure varies by type)
        local payload_ok, _ = pcall(function()
            -- Try common fields that many event types share
            if ev.hfid then entry.hfid = ev.hfid end
            if ev.site then entry.site_id = ev.site end
            if ev.subregion then entry.subregion_id = ev.subregion end

            -- Death events
            if ev.victim_hf then entry.victim_hf = ev.victim_hf end
            if ev.slayer_hf then entry.slayer_hf = ev.slayer_hf end
            if ev.death_cause then entry.death_cause = ev.death_cause end

            -- Entity link events
            if ev.civ then entry.civ_id = ev.civ end
            if ev.histfig then entry.histfig_id = ev.histfig end
            if ev.link_type then entry.link_type = ev.link_type end

            -- Artifact events
            if ev.artifact_id then entry.artifact_id = ev.artifact_id end

            -- State change events
            if ev.state then entry.state = ev.state end
            if ev.reason then entry.reason = ev.reason end
        end)

        table.insert(recent, entry)
    end

    -- Update cursor
    if #recent > 0 then
        chronicler_state.last_event_id = recent[#recent].id
    end

    return {
        figure_count = #figures,
        event_count = count,
        cursor = chronicler_state.last_event_id,
        new_count = #recent,
        recent_events = recent,
    }
end

-- ── World Info ────────────────────────────────────────────────────────

local function get_world_info()
    local result = {
        civ_id = df.global.plotinfo.civ_id,
        race_id = df.global.plotinfo.race_id,
        site_id = -1,
    }

    -- Save directory (needed by legends export automation)
    local sd_ok, sd = pcall(function() return df.global.world.cur_savegame.save_dir end)
    if sd_ok and sd then
        result.save_dir = to_utf8(sd)
    end

    if df.global.world.world_data and df.global.world.world_data.name then
        local wn = df.global.world.world_data.name
        result.world_name = dfhack.df2utf(dfhack.translation.translateName(wn))
        result.world_name_english = dfhack.df2utf(dfhack.translation.translateName(wn, true))
    end

    if df.global.plotinfo.main and df.global.plotinfo.main.fortress_site then
        local site = df.global.plotinfo.main.fortress_site
        result.site_id = site.id
        if site.name and site.name.has_name then
            result.fortress_name = dfhack.df2utf(dfhack.translation.translateName(site.name))
            result.fortress_name_english = dfhack.df2utf(dfhack.translation.translateName(site.name, true))
        end
    end

    return result
end

-- ── Entities (nearby civilizations) ───────────────────────────────────

local function get_entities()
    local entities = df.global.world.entities.all
    local count = #entities
    local list = {}
    local player_civ = df.global.plotinfo.civ_id
    local player_found = false

    for i = 0, count - 1 do
        local e = entities[i]
        local is_player = (e.id == player_civ)
        if is_player or #list < 100 then
            local entry = {
                id = e.id,
                type = e.type,
                race = e.race,
                is_player = is_player,
            }
            if e.name and e.name.has_name then
                entry.name = dfhack.df2utf(dfhack.translation.translateName(e.name))
                entry.name_english = dfhack.df2utf(dfhack.translation.translateName(e.name, true))
            end
            table.insert(list, entry)
            if is_player then player_found = true end
        end
        if #list >= 100 and player_found then break end
    end

    return {
        total = count,
        listed = #list,
        player_civ_id = player_civ,
        entities = list,
    }
end

-- ── Dwarf Skills (per-unit skill lists) ──────────────────────────────

local function get_dwarf_skills()
    local units = df.global.world.units.active
    local player_race = df.global.plotinfo.race_id
    local player_civ = df.global.plotinfo.civ_id
    local dwarves = {}

    for i = 0, #units - 1 do
        local u = units[i]
        if u.race == player_race and u.civ_id == player_civ
           and u.status and u.status.current_soul then
            local skills = {}
            local soul_skills = u.status.current_soul.skills
            for j = 0, #soul_skills - 1 do
                local sk = soul_skills[j]
                table.insert(skills, {
                    id = sk.id,
                    rating = sk.rating,
                    experience = sk.experience,
                })
            end
            local entry = {
                id = u.id,
                skill_count = #skills,
                skills = skills,
            }
            if u.name and u.name.has_name then
                entry.first_name = to_utf8(u.name.first_name)
            end
            table.insert(dwarves, entry)
        end
    end

    return {
        dwarf_count = #dwarves,
        dwarves = dwarves,
    }
end

-- ══════════════════════════════════════════════════════════════════════
-- v6 NEW SECTIONS
-- ══════════════════════════════════════════════════════════════════════

-- ── Dwarf Emotions (per-dwarf emotion vectors) ──────────────────────

local function get_dwarf_emotions()
    local units = df.global.world.units.active
    local player_race = df.global.plotinfo.race_id
    local player_civ = df.global.plotinfo.civ_id
    local dwarves = {}

    for i = 0, #units - 1 do
        local u = units[i]
        if u.race == player_race and u.civ_id == player_civ
           and not dfhack.units.isDead(u)
           and u.status and u.status.current_soul then
            local emotions = {}
            local emo_list = u.status.current_soul.personality.emotions

            -- Cap at 10 most recent per dwarf (list is chronological)
            local emo_count = #emo_list
            local emo_start = math.max(0, emo_count - 10)
            for j = emo_start, emo_count - 1 do
                local em = emo_list[j]
                table.insert(emotions, {
                    type = em.type,
                    thought = em.thought,
                    subthought = em.subthought,
                    strength = em.strength,
                    severity = em.severity,
                    year = em.year,
                    year_tick = em.year_tick,
                })
            end

            if #emotions > 0 then
                local entry = {
                    id = u.id,
                    emotion_count = #emotions,
                    emotions = emotions,
                }
                if u.name and u.name.has_name then
                    entry.first_name = to_utf8(u.name.first_name)
                end
                table.insert(dwarves, entry)
            end
        end
    end

    return {
        dwarf_count = #dwarves,
        dwarves = dwarves,
    }
end

-- ── Dwarf Personality (traits, values, needs, dreams, attributes — v7)

local function get_dwarf_personality()
    local units = df.global.world.units.active
    local player_race = df.global.plotinfo.race_id
    local player_civ = df.global.plotinfo.civ_id
    local dwarves = {}

    for i = 0, #units - 1 do
        local u = units[i]
        if u.race == player_race and u.civ_id == player_civ
           and not dfhack.units.isDead(u)
           and u.status and u.status.current_soul then
            local soul = u.status.current_soul
            local p = soul.personality
            local entry = { id = u.id }

            -- Traits (50 facets, each 0-100 internally)
            local traits = {}
            local trait_ok, _ = pcall(function()
                for j = 0, 49 do
                    local tname = df.personality_facet_type[j]
                    if tname then
                        traits[tname] = p.traits[j]
                    end
                end
            end)
            if trait_ok and next(traits) then
                entry.traits = traits
            end

            -- Values
            local values = {}
            local val_ok, _ = pcall(function()
                for j = 0, #p.values - 1 do
                    local v = p.values[j]
                    table.insert(values, {type=df.value_type[v.type], strength=v.strength})
                end
            end)
            if val_ok and #values > 0 then
                entry.values = values
            end

            -- Needs with focus level
            local needs = {}
            local need_ok, _ = pcall(function()
                for j = 0, #p.needs - 1 do
                    local n = p.needs[j]
                    table.insert(needs, {type=df.need_type[n.id], focus=n.focus_level, level=n.need_level})
                end
            end)
            if need_ok and #needs > 0 then
                entry.needs = needs
            end

            -- Dreams/goals
            local dreams = {}
            local dream_ok, _ = pcall(function()
                for j = 0, #p.dreams - 1 do
                    local d = p.dreams[j]
                    table.insert(dreams, {type=df.goal_type[d.type], accomplished=d.flags.accomplished})
                end
            end)
            if dream_ok and #dreams > 0 then
                entry.dreams = dreams
            end

            -- Physical attributes (6)
            local phys = {}
            local phys_ok, _ = pcall(function()
                for j = 0, 5 do
                    local attr = u.body.physical_attrs[j]
                    phys[df.physical_attribute_type[j]] = {value=attr.value, max=attr.max_value}
                end
            end)
            if phys_ok and next(phys) then
                entry.physical_attrs = phys
            end

            -- Mental attributes (12)
            local ment = {}
            local ment_ok, _ = pcall(function()
                for j = 0, 12 do
                    local attr = soul.mental_attrs[j]
                    if attr then
                        ment[df.mental_attribute_type[j]] = {value=attr.value, max=attr.max_value}
                    end
                end
            end)
            if ment_ok and next(ment) then
                entry.mental_attrs = ment
            end

            if entry.traits or entry.values or entry.needs or entry.dreams
               or entry.physical_attrs or entry.mental_attrs then
                if u.name and u.name.has_name then
                    entry.first_name = to_utf8(u.name.first_name)
                end
                table.insert(dwarves, entry)
            end
        end
    end

    return {
        dwarf_count = #dwarves,
        dwarves = dwarves,
    }
end

-- ── Zones (fortress civzones) ────────────────────────────────────────

local function get_zones()
    -- Use the pre-filtered ANY_ZONE vector for efficiency
    local zones_ok, zone_vec = pcall(function()
        return df.global.world.buildings.other.ANY_ZONE
    end)
    if not zones_ok or not zone_vec then
        return { total = 0, zones = {}, error = 'ANY_ZONE not available' }
    end

    local count = #zone_vec
    local list = {}
    local limit = math.min(count, 200)

    for i = 0, limit - 1 do
        local z = zone_vec[i]
        local entry = {
            id = z.id,
            type = z.type,
            x1 = z.x1,
            y1 = z.y1,
            x2 = z.x2,
            y2 = z.y2,
            z = z.z,
            assigned_unit_count = #z.assigned_units,
        }

        -- Zone active status
        local active_ok, active = pcall(function()
            return z.spec_sub_flag.active
        end)
        if active_ok then
            entry.is_active = active
        end

        -- Zone name (if building has a custom name)
        if z.name and z.name.has_name then
            entry.name = translate_name(z.name)
        end

        -- Single assigned owner (bedrooms, offices, etc.)
        if z.assigned_unit_id and z.assigned_unit_id >= 0 then
            entry.owner_unit_id = z.assigned_unit_id
        end

        table.insert(list, entry)
    end

    return {
        total = count,
        listed = #list,
        zones = list,
    }
end

-- ── Event Collections (wars, battles, sieges) ────────────────────────

local function get_event_collections()
    local ec_ok, ec_all = pcall(function()
        return df.global.world.history.event_collections.all
    end)
    if not ec_ok or not ec_all then
        return { total = 0, collections = {}, error = 'event_collections not available' }
    end

    local count = #ec_all
    local list = {}

    -- Get the most recent 50 collections (they're appended chronologically)
    local start_idx = math.max(0, count - 50)
    for i = start_idx, count - 1 do
        local ec = ec_all[i]
        local entry = {
            id = ec.id,
            type = ec:getType(),
            start_year = ec.start_year,
            end_year = ec.end_year,
            event_count = #ec.events,
            child_collection_count = #ec.collections,
        }

        -- Try to get name (only on certain subtypes like WAR, BATTLE)
        local name_ok, name_val = pcall(function()
            if ec.name and ec.name.has_name then
                return translate_name(ec.name)
            end
            return nil
        end)
        if name_ok and name_val then
            entry.name = name_val
        end

        -- Try to get attacker/defender civs (WAR and BATTLE subtypes)
        local civ_ok, _ = pcall(function()
            if ec.attacker_civ and #ec.attacker_civ > 0 then
                entry.attacker_civ = ec.attacker_civ[0]
            end
            if ec.defender_civ and #ec.defender_civ > 0 then
                entry.defender_civ = ec.defender_civ[0]
            end
            if ec.site then
                entry.site_id = ec.site
            end
        end)

        -- Try to resolve entity names for attacker/defender
        if entry.attacker_civ then
            local ae = df.historical_entity.find(entry.attacker_civ)
            if ae then
                entry.attacker_name = translate_name(ae.name)
            end
        end
        if entry.defender_civ then
            local de = df.historical_entity.find(entry.defender_civ)
            if de then
                entry.defender_name = translate_name(de.name)
            end
        end

        table.insert(list, entry)
    end

    return {
        total = count,
        listed = #list,
        collections = list,
    }
end

-- ── Squads (military organization) ───────────────────────────────────

local function get_squads()
    local sq_ok, sq_all = pcall(function()
        return df.global.world.squads.all
    end)
    if not sq_ok or not sq_all then
        return { total = 0, squads = {}, error = 'squads not available' }
    end

    local count = #sq_all
    local list = {}

    for i = 0, count - 1 do
        local sq = sq_all[i]
        local entry = {
            id = sq.id,
            entity_id = sq.entity_id,
        }

        -- Squad name
        if sq.name and sq.name.has_name then
            entry.name = translate_name(sq.name)
            entry.name_english = translate_name(sq.name, true)
        end
        -- Alias overrides name
        if sq.alias and #sq.alias > 0 then
            entry.alias = to_utf8(sq.alias)
        end

        -- Members from positions
        local members = {}
        if sq.positions then
            for j = 0, #sq.positions - 1 do
                local pos = sq.positions[j]
                if pos.occupant >= 0 then
                    table.insert(members, {
                        position = j,
                        histfig_id = pos.occupant,
                    })
                end
            end
        end
        entry.members = members
        entry.member_count = #members
        entry.position_count = sq.positions and #sq.positions or 0

        -- Current orders count
        if sq.orders then
            entry.order_count = #sq.orders
        end

        table.insert(list, entry)
    end

    return {
        total = count,
        squads = list,
    }
end

-- ── Mandates (noble mandates) ────────────────────────────────────────

local function get_mandates()
    local md_ok, md_all = pcall(function()
        return df.global.world.mandates.all
    end)
    if not md_ok or not md_all then
        return { total = 0, mandates = {}, error = 'mandates not available' }
    end

    local count = #md_all
    local list = {}
    local limit = math.min(count, 50)

    for i = 0, limit - 1 do
        local m = md_all[i]
        local entry = {
            mode = m.mode,
            item_type = m.item_type,
            item_subtype = m.item_subtype,
            mat_type = m.mat_type,
            mat_index = m.mat_index,
            amount_total = m.amount_total,
            amount_remaining = m.amount_remaining,
            timeout_counter = m.timeout_counter,
            timeout_limit = m.timeout_limit,
        }

        -- Issuing noble (unit pointer)
        if m.unit then
            entry.unit_id = m.unit.id
            if m.unit.name and m.unit.name.has_name then
                entry.unit_name = translate_name(m.unit.name)
            end
        end

        table.insert(list, entry)
    end

    return {
        total = count,
        listed = #list,
        mandates = list,
    }
end

-- ── Incidents (crimes and events) ────────────────────────────────────

local function get_incidents()
    local inc_ok, inc_all = pcall(function()
        return df.global.world.incidents.all
    end)
    if not inc_ok or not inc_all then
        return { total = 0, incidents = {}, error = 'incidents not available' }
    end

    local count = #inc_all
    local list = {}

    -- Get most recent 50 incidents
    local start_idx = math.max(0, count - 50)
    for i = start_idx, count - 1 do
        local inc = inc_all[i]
        local entry = {
            id = inc.id,
            type = inc.type,
            event_year = inc.event_year,
            event_time = inc.event_time,
            victim = inc.victim,
            criminal = inc.criminal,
            site = inc.site,
        }

        -- Death cause (if applicable)
        local dc_ok, dc = pcall(function() return inc.death_cause end)
        if dc_ok then
            entry.death_cause = dc
        end

        -- Conflict level
        local cl_ok, cl = pcall(function() return inc.conflict_level end)
        if cl_ok then
            entry.conflict_level = cl
        end

        -- Flags
        local fl_ok, _ = pcall(function()
            entry.announced_missing = inc.flags.announced_missing
            entry.discovered = inc.flags.discovered
            entry.stale = inc.flags.stale
        end)

        table.insert(list, entry)
    end

    return {
        total = count,
        listed = #list,
        incidents = list,
    }
end

-- ── v9: Memory-Only Structure Extraction ────────────────────────────

local function get_belief_systems()
    local bs_ok, bs_all = pcall(function()
        return df.global.world.belief_systems.all
    end)
    if not bs_ok or not bs_all then
        return { total = 0, systems = {} }
    end

    local count = #bs_all
    local list = {}

    for i = 0, count - 1 do
        local bs = bs_all[i]
        local entry = { id = bs.id }

        -- Deity HF IDs and worship levels
        local deities = {}
        local worship = {}
        pcall(function()
            for j = 0, #bs.deities - 1 do
                table.insert(deities, bs.deities[j])
                if bs.worship_levels and j < #bs.worship_levels then
                    table.insert(worship, bs.worship_levels[j])
                end
            end
        end)
        entry.deities = deities
        entry.worship_levels = worship

        -- Cultural value weights
        local values = {}
        pcall(function()
            for j = 0, #bs.value - 1 do
                values[j] = bs.value[j]
            end
        end)
        if next(values) then
            entry.cultural_values = values
        end

        table.insert(list, entry)
    end

    return { total = count, systems = list }
end


local function get_cultural_identities()
    local ci_ok, ci_all = pcall(function()
        return df.global.world.cultural_identities.all
    end)
    if not ci_ok or not ci_all then
        return { total = 0, identities = {} }
    end

    local count = #ci_all
    local list = {}

    for i = 0, count - 1 do
        local ci = ci_all[i]
        local entry = {
            id = ci.id,
        }

        pcall(function() entry.site_id = ci.site_id end)
        pcall(function() entry.civ_id = ci.civ_id end)

        -- Ethics array (ethic_type -> response)
        local ethics = {}
        pcall(function()
            for j = 0, #ci.ethic - 1 do
                ethics[j] = ci.ethic[j]
            end
        end)
        if next(ethics) then
            entry.ethics = ethics
        end

        -- Cultural values
        local values = {}
        pcall(function()
            for j = 0, #ci.values - 1 do
                values[j] = ci.values[j]
            end
        end)
        if next(values) then
            entry.cultural_values = values
        end

        table.insert(list, entry)
    end

    return { total = count, identities = list }
end


local function get_occupations()
    local occ_ok, occ_all = pcall(function()
        return df.global.world.occupations.all
    end)
    if not occ_ok or not occ_all then
        return { total = 0, occupations = {} }
    end

    local count = #occ_all
    local list = {}

    for i = 0, count - 1 do
        local occ = occ_all[i]
        local entry = { id = occ.id }

        pcall(function() entry.occupation_type = tostring(occ.type) end)
        pcall(function() entry.hf_id = occ.histfig_id end)
        pcall(function() entry.unit_id = occ.unit_id end)
        pcall(function() entry.site_id = occ.site_id end)
        pcall(function() entry.location_id = occ.location_id end)
        pcall(function() entry.entity_id = occ.group_id end)

        table.insert(list, entry)
    end

    return { total = count, occupations = list }
end


local function get_interaction_instances()
    local ii_ok, ii_all = pcall(function()
        return df.global.world.interaction_instances.all
    end)
    if not ii_ok or not ii_all then
        return { total = 0, instances = {} }
    end

    local count = #ii_all
    local list = {}

    for i = 0, count - 1 do
        local inst = ii_all[i]
        local entry = { id = inst.id }

        pcall(function() entry.interaction_type = tostring(inst.interaction_id) end)

        -- Source context
        pcall(function()
            if inst.source_context then
                entry.source_hf_id = inst.source_context.histfig_id
            end
        end)

        -- Affected units
        local affected = {}
        pcall(function()
            for j = 0, #inst.affected_units - 1 do
                table.insert(affected, inst.affected_units[j])
            end
        end)
        entry.affected_units = affected

        table.insert(list, entry)
    end

    return { total = count, instances = list }
end


local function get_noble_positions()
    -- Read position assignments from the fortress entity.
    -- DF stores these in entity.positions.assignments (entity_position_assignmentst).
    -- Each assignment has: id, position_id, histfig (HF ID), squad_id.
    -- We read from the fortress entity (plotinfo.main.fortress_entity)
    -- and include the site government entity if different.
    local pi_ok, pi = pcall(function() return df.global.plotinfo end)
    if not pi_ok or not pi then
        return nil
    end

    local result = {}
    local function read_entity_positions(ent, label)
        if not ent or not ent.positions then return end
        local assignments = {}
        pcall(function()
            local asn = ent.positions.assignments
            for i = 0, #asn - 1 do
                local a = asn[i]
                local entry = {}
                pcall(function() entry.assignment_id = a.id end)
                pcall(function() entry.position_id = a.position_id end)
                pcall(function() entry.histfig_id = a.histfig end)
                pcall(function() entry.squad_id = a.squad_id end)
                -- Only include assignments with an actual HF
                if entry.histfig_id and entry.histfig_id >= 0 then
                    table.insert(assignments, entry)
                end
            end
        end)
        result[label] = {
            entity_id = ent.id,
            count = #assignments,
            assignments = assignments,
        }
    end

    -- Fortress entity (the civilization)
    pcall(function()
        read_entity_positions(pi.main.fortress_entity, 'fortress_entity')
    end)

    -- Site government (may have additional noble positions)
    pcall(function()
        local sg = df.global.world.entities.all[pi.group_id]
        if sg and sg.id ~= pi.main.fortress_entity.id then
            read_entity_positions(sg, 'site_government')
        end
    end)

    return result
end


local function get_fortress_state()
    -- Only meaningful in fortress mode
    local pi_ok, pi = pcall(function() return df.global.plotinfo end)
    if not pi_ok or not pi then
        return nil
    end

    local state = {}

    pcall(function() state.site_id = pi.site_id end)
    pcall(function() state.fortress_age = pi.fortress_age end)
    pcall(function() state.fortress_rank = pi.fortress_rank end)
    pcall(function() state.king_arrived = pi.king_arrived end)

    -- Population count (fortress citizens only, excludes visitors/merchants)
    pcall(function()
        state.population = #dfhack.units.getCitizens()
    end)

    -- Infiltrators (known vampire/werebeast HF IDs)
    local infiltrators = {}
    pcall(function()
        for j = 0, #pi.infiltrator_histfigs - 1 do
            table.insert(infiltrators, pi.infiltrator_histfigs[j])
        end
    end)
    state.infiltrators = infiltrators

    -- Invasion count
    pcall(function()
        state.invasion_count = pi.invasions.next_id or 0
    end)

    -- Wealth metrics (DF 53.10 field names)
    pcall(function()
        local w = pi.tasks.wealth
        state.wealth_total = w.total
        state.wealth_imported = w.imported
        state.wealth_exported = w.exported
        state.wealth_architecture = w.architecture
        state.wealth_displayed = w.displayed
    end)

    -- Food & drink stocks (Stage 3.5 — fortress_state_snapshots)
    pcall(function()
        local food = pi.tasks.food
        state.food_stocks = food.total or 0
        state.drink_stocks = food.drink or 0
    end)

    -- Fortress entity IDs (for filtering squads to fortress-only)
    pcall(function()
        state.group_id = pi.group_id
        state.civ_id = pi.civ_id
    end)

    -- Fortress depth: difference between surface z and lowest dug z
    pcall(function()
        local map = df.global.world.map
        state.fortress_depth = map.z_count_current or 0
    end)

    -- Current temperature at fort (approximation from weather)
    pcall(function()
        local weather = df.global.current_weather
        if weather then
            -- Weather is a 5x5 grid; average the center
            state.weather_type = weather[2][2]
        end
    end)

    return state
end


local function get_daily_events()
    -- Scheduled yearly events: world.daily_events (world_yearly_schedulest)
    -- 336-element static arrays, one per ~4-day period
    -- Each slot holds vectors of nemesis_record IDs
    local de_ok, de = pcall(function() return df.global.world.daily_events end)
    if not de_ok or not de then
        return nil
    end

    -- Calculate current day index (0-335) from game time
    local cur_tick = df.global.cur_year_tick or 0
    local day_index = math.floor(cur_tick / 1200) -- ~1200 ticks per DF day, 336 per year

    -- Extract only upcoming events (current day + next 30 days) to keep JSON small
    local result = { day_index = day_index }

    local function extract_window(arr, start_idx, window)
        local events = {}
        for offset = 0, window - 1 do
            local idx = (start_idx + offset) % 336
            local vec = arr[idx]
            if vec and #vec > 0 then
                local ids = {}
                for j = 0, #vec - 1 do
                    table.insert(ids, vec[j])
                end
                events[tostring(idx)] = ids
            end
        end
        return events
    end

    pcall(function() result.deaths = extract_window(de.deaths, day_index, 30) end)
    pcall(function() result.pregnancies = extract_window(de.pregnancies, day_index, 30) end)
    pcall(function() result.births = extract_window(de.births, day_index, 30) end)
    pcall(function() result.grown_up = extract_window(de.grown_up, day_index, 30) end)
    pcall(function() result.marriages_1 = extract_window(de.marriage_1, day_index, 30) end)
    pcall(function() result.marriages_2 = extract_window(de.marriage_2, day_index, 30) end)

    return result
end


-- ── Biome/terrain data extraction (one-time, static post-worldgen) ───
-- Writes comprehensive per-tile terrain data to chronicler-biome-data.json.
-- Called on demand (not every bridge cycle) since world terrain never changes.

local function extract_biome_data()
    local wd = df.global.world.world_data
    if not wd then return nil end

    local width = wd.world_width
    local height = wd.world_height
    local rm = wd.region_map

    -- Build region type lookup: region_id -> {type, type_name}
    local region_types = {}
    local regions = wd.regions
    for i = 0, #regions - 1 do
        local r = regions[i]
        region_types[r.index] = {
            type = r.type,
            type_name = df.world_region_type[r.type] or tostring(r.type),
        }
    end

    -- Extract per-tile arrays (flat, row-major: tile[x * height + y])
    local elevation = {}
    local rainfall = {}
    local vegetation = {}
    local temperature = {}
    local evilness = {}
    local drainage = {}
    local volcanism = {}
    local savagery = {}
    local salinity = {}
    local region_id = {}
    local landmass_id = {}

    for x = 0, width - 1 do
        local col = rm[x]
        for y = 0, height - 1 do
            local tile = col:_displace(y)
            local idx = x * height + y + 1  -- Lua 1-indexed
            elevation[idx] = tile.elevation
            rainfall[idx] = tile.rainfall
            vegetation[idx] = tile.vegetation
            temperature[idx] = tile.temperature
            evilness[idx] = tile.evilness
            drainage[idx] = tile.drainage
            volcanism[idx] = tile.volcanism
            savagery[idx] = tile.savagery
            salinity[idx] = tile.salinity
            region_id[idx] = tile.region_id
            landmass_id[idx] = tile.landmass_id
        end
    end

    return {
        width = width,
        height = height,
        region_types = region_types,
        elevation = elevation,
        rainfall = rainfall,
        vegetation = vegetation,
        temperature = temperature,
        evilness = evilness,
        drainage = drainage,
        volcanism = volcanism,
        savagery = savagery,
        salinity = salinity,
        region_id = region_id,
        landmass_id = landmass_id,
        extracted_at = os.time(),
    }
end

local function write_biome_data()
    local data = extract_biome_data()
    if not data then
        dfhack.printerr('[Chronicler] No world data available for biome extraction')
        return false
    end
    local ok, err = pcall(function()
        json.encode_file(data, 'chronicler-biome-data.json')
    end)
    if ok then
        print('[Chronicler] Biome data extracted: ' .. data.width .. 'x' .. data.height
              .. ' (' .. (data.width * data.height) .. ' tiles) -> chronicler-biome-data.json')
    else
        dfhack.printerr('[Chronicler] Biome write failed: ' .. tostring(err))
    end
    return ok
end

-- ── Main: assemble and write ─────────────────────────────────────────

-- ── v9.1: Auto-dismiss game popups ─────────────────────────────────
-- DF53+ uses world.status.popups for events like caravan arrivals,
-- season changes, migrant waves, and diplomat visits. These block the
-- simulation loop even when pause_state=false. Dismiss them automatically
-- during bridge cycles so the game keeps running.

local function dismiss_popups()
    local popups = df.global.world.status.popups
    local count = #popups
    if count == 0 then return 0 end
    -- Log each popup before dismissing
    for i = 0, count - 1 do
        local text = popups[i].text or ''
        if #text > 0 then
            local safe = dfhack.df2utf(text) or text
            dfhack.println('[chronicler] Dismissing popup: ' .. safe:sub(1, 80))
        end
    end
    -- Erase all popups (erase from end to avoid index shifting)
    for i = count - 1, 0, -1 do
        popups:erase(i)
    end
    return count
end


local function write_state()
    -- v9.1: Auto-dismiss any blocking popups before data capture
    dismiss_popups()

    -- v8: Initialize eventful subscriptions on first run
    init_eventful()

    local state = get_game_time()
    state.creature_raws = get_creature_raws()
    state.creature_count = #df.global.world.raws.creatures.all
    state.timestamp = os.time()
    state.bridge_version = 9

    -- Data sections (each wrapped in pcall for safety)
    local ok, result
    local errors = {}

    local function safe_add(name, fn)
        ok, result = pcall(fn)
        if ok then
            state[name] = result
        else
            errors[name] = tostring(result)
        end
    end

    -- Original sections
    safe_add('unit_summary', get_unit_summary)
    safe_add('armies', get_armies)
    safe_add('buildings', get_buildings)
    safe_add('artifacts', get_artifacts)
    safe_add('announcements', get_announcements)
    safe_add('diplomacy', get_diplomacy)
    safe_add('history', get_history_summary)
    safe_add('world_info', get_world_info)
    safe_add('entities', get_entities)
    safe_add('dwarf_skills', get_dwarf_skills)

    -- v6 new sections
    safe_add('dwarf_emotions', get_dwarf_emotions)
    -- v7 new sections
    safe_add('dwarf_personality', get_dwarf_personality)
    safe_add('zones', get_zones)
    safe_add('event_collections', get_event_collections)
    safe_add('squads', get_squads)
    safe_add('mandates', get_mandates)
    safe_add('incidents', get_incidents)

    -- v8: Reactive events (flushed from eventful buffers)
    safe_add('reactive_events', flush_events)
    -- v8: Skill delta tracking
    safe_add('skill_changes', get_skill_changes)

    -- v9: Memory-only structures (not available in legends XML)
    safe_add('belief_systems', get_belief_systems)
    safe_add('cultural_identities', get_cultural_identities)
    safe_add('occupations', get_occupations)
    safe_add('interaction_instances', get_interaction_instances)
    safe_add('noble_positions', get_noble_positions)
    safe_add('fortress_state', get_fortress_state)
    safe_add('daily_events', get_daily_events)

    if next(errors) then
        state.errors = errors
    end

    local write_ok, write_err = pcall(function()
        json.encode_file(state, 'chronicler-state.json')
    end)

    if not write_ok then
        dfhack.printerr('chronicler-bridge: ' .. tostring(write_err))
    end
end

write_state()

-- One-time biome extraction (only if not already extracted this session)
if not chronicler_state.biome_extracted then
    local biome_ok = write_biome_data()
    if biome_ok then
        chronicler_state.biome_extracted = true
    end
end
