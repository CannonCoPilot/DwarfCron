-- chronicler-info-survey.lua
-- Comprehensive survey of ALL DF information systems available via DFHack
-- Purpose: Identify every extractable data source for Chronicler CDM design

local json = require('json')
local result = {}

-- Helper: safe field access (returns nil on error)
local function safe(fn)
    local ok, val = pcall(fn)
    if ok then return val else return nil end
end

-- Helper: run a section with error capture
local function section(name, fn)
    local ok, err = pcall(fn)
    if not ok then
        result[name] = { error = tostring(err) }
    end
end

-- Helper: safe name from language_name struct
local function getName(name_obj)
    if not name_obj then return '' end
    local first = name_obj.first_name or ''
    local nick = name_obj.nickname or ''
    if first ~= '' and nick ~= '' then return first .. ' "' .. nick .. '"' end
    if first ~= '' then return first end
    if nick ~= '' then return nick end
    return ''
end

-- ============================================================
-- 1. GAME TIME & STATE
-- ============================================================
result.game_state = {
    cur_year = df.global.cur_year,
    cur_year_tick = df.global.cur_year_tick,
    pause_state = df.global.pause_state,
    gamemode = df.global.gamemode,
    gametype = df.global.gametype,
    save_dir = df.global.world.cur_savegame.save_dir,
}

-- ============================================================
-- 2. UNITS (living + dead + missing)
-- ============================================================
local unit_counts = { total=0, alive=0, dead=0, by_race={}, citizens=0, visitors=0, invaders=0, animals=0 }
local citizens_list = {}
for _, unit in ipairs(df.global.world.units.active) do
    unit_counts.total = unit_counts.total + 1
    if dfhack.units.isDead(unit) then
        unit_counts.dead = unit_counts.dead + 1
    else
        unit_counts.alive = unit_counts.alive + 1
    end
    local race_name = df.creature_raw.find(unit.race).creature_id
    unit_counts.by_race[race_name] = (unit_counts.by_race[race_name] or 0) + 1

    if dfhack.units.isCitizen(unit) then
        unit_counts.citizens = unit_counts.citizens + 1
        table.insert(citizens_list, {
            id = unit.id,
            name = getName(unit.name),
            name_en = dfhack.units.getReadableName(unit),
            race = race_name,
            profession = df.profession[unit.profession],
            stress = unit.status.current_soul and unit.status.current_soul.personality.stress or -1,
            pos = {x=unit.pos.x, y=unit.pos.y, z=unit.pos.z},
            hist_figure_id = unit.hist_figure_id,
        })
    end
end
result.units = unit_counts
result.citizens = citizens_list

-- ============================================================
-- 3. REPORTS (announcements/combat/etc)
-- ============================================================
local report_counts = {}
local report_samples = {}
local sample_limit = 3
for i, report in ipairs(df.global.world.status.reports) do
    local t = report.type
    local tname = tostring(t)
    report_counts[tname] = (report_counts[tname] or 0) + 1
    -- Grab samples of each type
    if not report_samples[tname] then report_samples[tname] = {} end
    if #report_samples[tname] < sample_limit then
        table.insert(report_samples[tname], {
            id = report.id,
            year = report.year,
            time = report.time,
            text = dfhack.df2utf(report.text),
            type = t,
            color = report.color,
            bright = report.bright,
            duration = report.duration,
            -- speaker_id removed: unk_v50_2 not in this version
            flags_raw = tostring(report.flags),
        })
    end
end
result.reports = { counts = report_counts, samples = report_samples, total = #df.global.world.status.reports }

-- ============================================================
-- 4. ANNOUNCEMENTS (distinct from reports)
-- ============================================================
local ann_count = #df.global.world.status.announcements
local ann_samples = {}
for i = math.max(0, ann_count - 20), ann_count - 1 do
    local ann = df.global.world.status.announcements[i]
    if ann then
        table.insert(ann_samples, {
            id = ann.id,
            year = ann.year,
            time = ann.time,
            text = dfhack.df2utf(ann.text),
            type = ann.type,
            color = ann.color,
            bright = ann.bright,
            pos = {x=ann.pos.x, y=ann.pos.y, z=ann.pos.z},
            -- flags accessed via pcall for version safety
            flags_raw = tostring(ann.flags),
        })
    end
end
result.announcements = { total = ann_count, recent_20 = ann_samples }

-- ============================================================
-- 5. INCIDENTS (crimes, conflicts, etc)
-- ============================================================
local incidents = {}
local inc_type_counts = {}
for _, inc in ipairs(df.global.world.incidents.all) do
    local tname = tostring(inc.type)
    inc_type_counts[tname] = (inc_type_counts[tname] or 0) + 1
end
-- Sample first 5 of each type
local inc_samples = {}
for _, inc in ipairs(df.global.world.incidents.all) do
    local tname = tostring(inc.type)
    if not inc_samples[tname] then inc_samples[tname] = {} end
    if #inc_samples[tname] < 3 then
        local s = {
            id = inc.id,
            type = inc.type,
            year = inc.event_year,
            time = inc.event_time,
            site_id = inc.site,
            flags = {},
            victim_id = -1,
            criminal_id = -1,
        }
        -- Try common fields
        pcall(function() s.victim_id = inc.victim end)
        pcall(function() s.criminal_id = inc.criminal end)
        table.insert(inc_samples[tname], s)
    end
end
result.incidents = { type_counts = inc_type_counts, samples = inc_samples, total = #df.global.world.incidents.all }

-- ============================================================
-- 6. ACTIVITIES (current tasks dwarves are doing)
-- ============================================================
local act_type_counts = {}
local act_total = 0
for _, act in ipairs(df.global.world.activities.all) do
    act_total = act_total + 1
    for _, evt in ipairs(act.events) do
        local cname = evt:getType()
        act_type_counts[tostring(cname)] = (act_type_counts[tostring(cname)] or 0) + 1
    end
end
result.activities = { total = act_total, event_type_counts = act_type_counts }

-- ============================================================
-- 7. JOBS (current workshop/task queue)
-- ============================================================
local job_type_counts = {}
local job_total = 0
for _, job in ipairs(df.global.world.jobs.list) do
    job_total = job_total + 1
    local jname = tostring(df.job_type[job.job_type])
    job_type_counts[jname] = (job_type_counts[jname] or 0) + 1
end
result.jobs = { total = job_total, type_counts = job_type_counts }

-- ============================================================
-- 8. BUILDINGS (workshops, stockpiles, etc)
-- ============================================================
local bld_type_counts = {}
local bld_total = 0
for _, bld in ipairs(df.global.world.buildings.all) do
    bld_total = bld_total + 1
    local btype = bld:getType()
    local key = tostring(btype)
    bld_type_counts[key] = (bld_type_counts[key] or 0) + 1
end
result.buildings = { total = bld_total, type_counts = bld_type_counts }

-- ============================================================
-- 9. STOCKPILES
-- ============================================================
local stockpile_count = 0
local stockpile_info = {}
for _, bld in ipairs(df.global.world.buildings.all) do
    if df.building_stockpilest:is_instance(bld) then
        stockpile_count = stockpile_count + 1
        if stockpile_count <= 10 then
            table.insert(stockpile_info, {
                id = bld.id,
                x1 = bld.x1, y1 = bld.y1, z = bld.z,
                x2 = bld.x2, y2 = bld.y2,
                stockpile_number = bld.stockpile_number,
            })
        end
    end
end
result.stockpiles = { total = stockpile_count, samples = stockpile_info }

-- ============================================================
-- 10. ITEMS (total counts by type)
-- ============================================================
local item_type_counts = {}
local item_total = 0
for _, item in ipairs(df.global.world.items.all) do
    item_total = item_total + 1
    local itype = item:getType()
    local key = tostring(itype)
    item_type_counts[key] = (item_type_counts[key] or 0) + 1
end
result.items = { total = item_total, type_counts = item_type_counts }

-- ============================================================
-- 11. HISTORY EVENTS (fortress-era only: since embark year)
-- ============================================================
local he_type_counts = {}
local he_total = 0
local he_fortress = 0
local embark_year = 250
for _, evt in ipairs(df.global.world.history.events) do
    he_total = he_total + 1
    if evt.year >= embark_year then
        he_fortress = he_fortress + 1
        local etype = tostring(evt:getType())
        he_type_counts[etype] = (he_type_counts[etype] or 0) + 1
    end
end
result.history_events = { total = he_total, since_embark = he_fortress, type_counts = he_type_counts }

-- ============================================================
-- 12. HISTORY EVENT COLLECTIONS
-- ============================================================
local hec_type_counts = {}
local hec_total = 0
for _, coll in ipairs(df.global.world.history.event_collections) do
    hec_total = hec_total + 1
    local ctype = tostring(coll:getType())
    hec_type_counts[ctype] = (hec_type_counts[ctype] or 0) + 1
end
result.history_event_collections = { total = hec_total, type_counts = hec_type_counts }

-- ============================================================
-- 13. SQUADS & MILITARY
-- ============================================================
local fortress_squads = {}
local plotinfo = df.global.plotinfo
for _, sq in ipairs(df.global.world.squads.all) do
    if sq.entity_id == plotinfo.group_id then
        local members = {}
        for i, pos in ipairs(sq.positions) do
            if pos.occupant >= 0 then
                table.insert(members, pos.occupant)
            end
        end
        table.insert(fortress_squads, {
            id = sq.id,
            name = getName(sq.name),
            alias = sq.alias,
            member_count = #members,
            member_hist_ids = members,
        })
    end
end
result.military = { fortress_squad_count = #fortress_squads, squads = fortress_squads }

-- ============================================================
-- 14. ZONES (taverns, temples, libraries, etc)
-- ============================================================
local zone_type_counts = {}
local zone_total = 0
local zone_samples = {}
for _, zone in ipairs(df.global.world.buildings.all) do
    if df.building_civzonest:is_instance(zone) then
        zone_total = zone_total + 1
        local zt = zone.type
        zone_type_counts[tostring(zt)] = (zone_type_counts[tostring(zt)] or 0) + 1
        if zone_total <= 10 then
            table.insert(zone_samples, {
                id = zone.id,
                type = zt,
                name = safe(function() return zone.name end) or '',
                x1 = zone.x1, y1 = zone.y1, z = zone.z,
            })
        end
    end
end
result.zones = { total = zone_total, type_counts = zone_type_counts, samples = zone_samples }

-- ============================================================
-- 15. WEATHER
-- ============================================================
result.weather = {
    rain = safe(function() return df.global.cur_rain end),
    snow = safe(function() return df.global.cur_snow end),
    fog_count = safe(function() return df.global.fog_count end),
}

-- ============================================================
-- 16. GAMELOG.TXT (last 20 lines)
-- ============================================================
local gamelog_lines = {}
local f = io.open('gamelog.txt', 'r')
if f then
    local all_lines = {}
    for line in f:lines() do
        table.insert(all_lines, line)
    end
    f:close()
    local start = math.max(1, #all_lines - 19)
    for i = start, #all_lines do
        table.insert(gamelog_lines, all_lines[i])
    end
end
result.gamelog = { total_lines = #gamelog_lines > 0 and 'available' or 'empty', last_20 = gamelog_lines }

-- ============================================================
-- 17. PLOTINFO (fortress-specific globals)
-- ============================================================
result.plotinfo = {
    group_id = safe(function() return plotinfo.group_id end),
    race_id = safe(function() return plotinfo.race_id end),
    civ_id = safe(function() return plotinfo.civ_id end),
    site_id = safe(function() return plotinfo.site_id end),
    fortress_age = safe(function() return plotinfo.fortress_age end),
    wealth_total = safe(function() return plotinfo.tasks.total_created_wealth end),
    tasks_num = safe(function() return #plotinfo.tasks.manager_orders end),
    num_artifacts = safe(function() return #plotinfo.artifacts end),
}

-- ============================================================
-- 18. MANAGER ORDERS (work orders)
-- ============================================================
local orders = {}
-- Manager orders location varies by version; try multiple paths
local mgr_list = safe(function() return plotinfo.tasks.manager_orders end)
    or safe(function() return df.global.world.manager_orders.all end)
    or safe(function() return df.global.world.manager_orders end)
if mgr_list and type(mgr_list) ~= 'number' then
    for _, order in ipairs(mgr_list) do
        local ok, entry = pcall(function()
            return {
                id = order.id,
                job_type = tostring(df.job_type[order.job_type]),
                amount_left = order.amount_left,
                amount_total = order.amount_total,
            }
        end)
        if ok then table.insert(orders, entry) end
    end
end
result.manager_orders = { total = #orders, orders = orders }

-- ============================================================
-- 19. POPULATIONS (world populations visible from fortress)
-- ============================================================
local pop_total = safe(function() return #df.global.world.populations end) or 0
result.populations = { total = pop_total }

-- ============================================================
-- 20. EMOTIONS & THOUGHTS (sample from citizens)
-- ============================================================
local thought_samples = {}
for i, unit in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(unit) and unit.status.current_soul then
        local thoughts = {}
        for _, thought in ipairs(unit.status.current_soul.personality.emotions) do
            table.insert(thoughts, {
                type = thought.type,
                thought = thought.thought,
                strength = thought.strength,
                year = thought.year,
                year_tick = thought.year_tick,
            })
        end
        if #thoughts > 0 then
            table.insert(thought_samples, {
                unit_id = unit.id,
                name = dfhack.units.getReadableName(unit),
                thought_count = #thoughts,
                recent_5 = {table.unpack(thoughts, math.max(1, #thoughts - 4), #thoughts)},
            })
        end
        if #thought_samples >= 3 then break end
    end
end
result.emotions = { samples = thought_samples }

-- ============================================================
-- 21. SYNDROME TRACKING (curses, diseases, etc)
-- ============================================================
local syndrome_info = {}
for _, unit in ipairs(df.global.world.units.active) do
    if #unit.syndromes.active > 0 and dfhack.units.isCitizen(unit) then
        local syns = {}
        for _, syn in ipairs(unit.syndromes.active) do
            local raw = safe(function() return df.syndrome.find(syn.type) end)
            table.insert(syns, {
                type_id = syn.type,
                name = safe(function() return raw and dfhack.df2utf(raw.syn_name) end) or 'unknown',
                year = safe(function() return syn.year end),
                year_time = safe(function() return syn.year_time end),
                ticks = safe(function() return syn.ticks end),
            })
        end
        table.insert(syndrome_info, {
            unit_id = unit.id,
            name = dfhack.units.getReadableName(unit),
            syndromes = syns,
        })
    end
end
result.syndromes = { affected_citizens = #syndrome_info, details = syndrome_info }

-- ============================================================
-- OUTPUT (with safe serialization — strip userdata)
-- ============================================================
local function sanitize(obj, depth)
    depth = depth or 0
    if depth > 10 then return 'MAX_DEPTH' end
    local t = type(obj)
    if t == 'table' then
        local out = {}
        for k, v in pairs(obj) do
            local sk = tostring(k)
            out[sk] = sanitize(v, depth + 1)
        end
        return out
    elseif t == 'string' or t == 'number' or t == 'boolean' then
        return obj
    elseif t == 'nil' then
        return nil
    else
        return tostring(obj)  -- convert userdata/function/thread to string
    end
end

local safe_result = sanitize(result)
local out = json.encode(safe_result)
local f = io.open('chronicler-info-survey-output.json', 'w')
f:write(out)
f:close()
print('SURVEY_COMPLETE:' .. tostring(#out) .. '_bytes')
