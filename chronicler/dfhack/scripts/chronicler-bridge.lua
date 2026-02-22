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
--   diplomacy: player civ diplomatic relations
--   history: figure/event counts + recent events
--   world_info: world name, fortress name, civ/site IDs
--   entities: nearby civilizations with names and types
--   dwarf_skills: per-dwarf full skill lists (for skill tracking)

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
        return { civ_id = civ_id, error = 'player civ not found' }
    end

    local relations = {}
    -- Guard: resources.diplomacy may not exist in all DF versions
    local res_ok, res = pcall(function() return civ.resources end)
    if res_ok and res then
        -- Try diplomacy.state (may not exist in DF 53.10)
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

-- ── World Info ────────────────────────────────────────────────────────

local function get_world_info()
    local result = {
        civ_id = df.global.plotinfo.civ_id,
        race_id = df.global.plotinfo.race_id,
        site_id = -1,
    }

    -- World name (DF-language + English)
    if df.global.world.world_data and df.global.world.world_data.name then
        local wn = df.global.world.world_data.name
        result.world_name = dfhack.df2utf(dfhack.translation.translateName(wn))
        result.world_name_english = dfhack.df2utf(dfhack.translation.translateName(wn, true))
    end

    -- Fortress name + site ID
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

    -- Include player civ first, then fill up to 100
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
        -- Stop once we have 100 + player
        if #list >= 100 and player_found then break end
    end

    return {
        total = count,
        listed = #list,
        player_civ_id = player_civ,
        entities = list,
    }
end

-- ── Dwarf Skills (per-unit skill lists) ───────────────────────────────

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

-- ── Main: assemble and write ───────────────────────────────────────────

local function write_state()
    local state = get_game_time()
    state.creature_raws = get_creature_raws()
    state.creature_count = #df.global.world.raws.creatures.all
    state.timestamp = os.time()

    -- Expanded data sections (each wrapped in pcall for safety)
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
