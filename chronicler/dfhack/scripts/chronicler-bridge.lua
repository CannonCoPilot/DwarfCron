-- chronicler-bridge.lua — DFHack bridge for Chronicler
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
--   unit_summary: count by race, list of fortress dwarves with stress/profession
--   armies: count + positions
--   buildings: count by type
--   artifacts: named artifact list
--   announcements: last 20 game reports
--   fortress: population, wealth stats

local json = require('json')

-- Helper: safely convert DF CP437 string to UTF-8
local function to_utf8(s)
    if s and #s > 0 then
        return dfhack.df2utf(s) or s
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

-- ── Unit Summary ───────────────────────────────────────────────────────

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
            -- Alive check (flags1 bit 1 = dead)
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

    -- Only include named artifacts (far more useful than unnamed worldgen items)
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
        -- Cap at 200 named artifacts
        if #named >= 200 then break end
    end

    return {
        total = count,
        named_count = #named,
        artifacts = named,
    }
end

-- ── Announcements (recent reports) ─────────────────────────────────────

local function get_announcements()
    local reports = df.global.world.status.reports
    local count = #reports
    local list = {}

    -- Last 20 reports
    local start = math.max(0, count - 20)
    for i = start, count - 1 do
        local r = reports[i]
        table.insert(list, {
            id = r.id,
            text = dfhack.df2utf(r.text) or '',
            year = r.year,
            time = r.time,
            type = r.type,
        })
    end

    return {
        total = count,
        recent = list,
    }
end

-- ── Diplomacy (per-entity, not world-level) ────────────────────────────

local function get_diplomacy()
    -- Diplomacy is per-entity. Get player civ's diplomatic relations.
    local civ_id = df.global.plotinfo.civ_id
    local civ = df.historical_entity.find(civ_id)
    if not civ then
        return { error = 'player civ not found' }
    end

    local relations = {}
    if civ.resources and civ.resources.diplomacy then
        local states = civ.resources.diplomacy.state
        for i = 0, #states - 1 do
            local s = states[i]
            table.insert(relations, {
                entity_id = s.group_id,
                relation = s.relation,
            })
        end
    end

    return {
        civ_id = civ_id,
        relation_count = #relations,
        relations = relations,
    }
end

-- ── Historical Figures (count + notable) ───────────────────────────────

local function get_history_summary()
    local figures = df.global.world.history.figures
    local events = df.global.world.history.events
    local count = #events

    -- Last 50 events (type + year for trend tracking)
    local recent = {}
    local start = math.max(0, count - 50)
    for i = start, count - 1 do
        local ev = events[i]
        table.insert(recent, {
            id = ev.id,
            type = ev:getType(),
            year = ev.year,
        })
    end

    return {
        figure_count = #figures,
        event_count = count,
        recent_events = recent,
    }
end

-- ── Main: assemble and write ───────────────────────────────────────────

local function write_state()
    local state = get_game_time()
    state.creature_raws = get_creature_raws()
    state.creature_count = #df.global.world.raws.creatures.all
    state.timestamp = os.time()

    -- Expanded data sections (each wrapped in pcall for safety)
    local ok, result

    ok, result = pcall(get_unit_summary)
    if ok then state.unit_summary = result end

    ok, result = pcall(get_armies)
    if ok then state.armies = result end

    ok, result = pcall(get_buildings)
    if ok then state.buildings = result end

    ok, result = pcall(get_artifacts)
    if ok then state.artifacts = result end

    ok, result = pcall(get_announcements)
    if ok then state.announcements = result end

    ok, result = pcall(get_diplomacy)
    if ok then state.diplomacy = result end

    ok, result = pcall(get_history_summary)
    if ok then state.history = result end

    local write_ok, write_err = pcall(function()
        json.encode_file(state, 'chronicler-state.json')
    end)

    if not write_ok then
        dfhack.printerr('chronicler-bridge: ' .. tostring(write_err))
    end
end

write_state()
