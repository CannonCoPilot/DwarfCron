-- chronicler-bridge.lua v6 — DFHack bridge for Chronicler
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
--   unit_summary: fortress dwarves with stress/profession/flags/mood
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
--   zones: fortress civzones with types and assignments (v6)
--   event_collections: active wars/battles/sieges (v6)
--   squads: military squads with members and orders (v6)
--   mandates: noble mandates with items and timeouts (v6)
--   incidents: crimes and incidents with victims/criminals (v6)

local json = require('json')

-- ── Persistent state (survives across repeat ticks) ─────────────────
-- These globals track cursors so we never miss events between ticks.
chronicler_state = chronicler_state or {}
chronicler_state.last_report_id = chronicler_state.last_report_id or -1
chronicler_state.last_event_id = chronicler_state.last_event_id or -1

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

    -- Cap at 50 to keep JSON size reasonable
    local limit = math.min(count, 50)
    for i = 0, limit - 1 do
        local a = armies[i]
        table.insert(list, {
            id = a.id,
            pos_x = a.pos.x,
            pos_y = a.pos.y,
            member_count = #a.members,
            controller_id = a.controller_id,
        })
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
    local limit = math.min(count, 50)

    for i = 0, limit - 1 do
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
        listed = #list,
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

-- ── Main: assemble and write ─────────────────────────────────────────

local function write_state()
    local state = get_game_time()
    state.creature_raws = get_creature_raws()
    state.creature_count = #df.global.world.raws.creatures.all
    state.timestamp = os.time()
    state.bridge_version = 6

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
    safe_add('zones', get_zones)
    safe_add('event_collections', get_event_collections)
    safe_add('squads', get_squads)
    safe_add('mandates', get_mandates)
    safe_add('incidents', get_incidents)

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
