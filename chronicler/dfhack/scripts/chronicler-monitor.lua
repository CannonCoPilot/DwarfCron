-- chronicler-monitor.lua
-- Quick fortress status check + auto popup dismissal
-- Run periodically to monitor ongoing events

local json = require('json')
local result = {}

-- Auto-dismiss popups (capture text first)
local popup_texts = {}
if #df.global.world.status.popups > 0 then
    for i = 0, #df.global.world.status.popups - 1 do
        local p = df.global.world.status.popups[i]
        table.insert(popup_texts, dfhack.df2utf(p.text))
    end
    df.global.world.status.popups:resize(0)
end
result.popups_dismissed = popup_texts

-- Game time
result.year = df.global.cur_year
result.tick = df.global.cur_year_tick
result.paused = df.global.pause_state
local ticks_per_year = 403200
local season = math.floor(result.tick / (ticks_per_year / 4))
local season_names = {'Spring', 'Summer', 'Autumn', 'Winter'}
result.season = season_names[season + 1] or '?'

-- Unit counts
local alive_citizens = 0
local alive_dwarves = 0
local friendly_undead = {}
local hostile_undead = 0
local hostile_alive = 0
local ghosts = {}
local all_alive = 0

for _, u in ipairs(df.global.world.units.active) do
    local race = df.creature_raw.find(u.race).creature_id

    if dfhack.units.isAlive(u) then
        all_alive = all_alive + 1
        if dfhack.units.isCitizen(u) then
            alive_citizens = alive_citizens + 1
        end
        if race == 'DWARF' then
            alive_dwarves = alive_dwarves + 1
        end
        if dfhack.units.isInvader(u) then
            hostile_alive = hostile_alive + 1
        end
    end

    if dfhack.units.isUndead(u) and not dfhack.units.isDead(u) then
        if dfhack.units.isFortControlled(u) then
            table.insert(friendly_undead, {
                name = u.name.first_name or 'unnamed',
                race = race,
                prof = df.profession[u.profession],
            })
        else
            hostile_undead = hostile_undead + 1
        end
    end

    if dfhack.units.isGhost(u) then
        table.insert(ghosts, u.name.first_name or 'unnamed')
    end
end

result.alive_citizens = alive_citizens
result.alive_dwarves = alive_dwarves
result.friendly_undead = friendly_undead
result.hostile_undead = hostile_undead
result.hostile_alive = hostile_alive
result.ghosts = ghosts
result.total_alive = all_alive

-- Recent announcements (last 5)
local ann_count = #df.global.world.status.announcements
local recent_ann = {}
for i = math.max(0, ann_count - 5), ann_count - 1 do
    local ann = df.global.world.status.announcements[i]
    if ann then
        table.insert(recent_ann, {
            text = dfhack.df2utf(ann.text),
            type = ann.type,
            year = ann.year,
            time = ann.time,
        })
    end
end
result.recent_announcements = recent_ann

-- Print summary
print(string.format('=== Y%d %s (tick %d) paused=%s ===',
    result.year, result.season, result.tick, tostring(result.paused)))
print(string.format('Citizens: %d | Alive dwarves: %d | Total alive: %d',
    alive_citizens, alive_dwarves, all_alive))
print(string.format('Friendly undead: %d | Hostile undead: %d | Hostile alive: %d',
    #friendly_undead, hostile_undead, hostile_alive))

if #friendly_undead > 0 then
    print('  Dastot\'s army:')
    for _, fu in ipairs(friendly_undead) do
        print(string.format('    %s (%s, %s)', fu.name, fu.race, fu.prof))
    end
end

if #ghosts > 0 then
    print('  Ghosts: ' .. table.concat(ghosts, ', '))
end

if #popup_texts > 0 then
    print('  Auto-dismissed popups:')
    for _, t in ipairs(popup_texts) do
        print('    ' .. t)
    end
end

print('  Recent:')
for _, a in ipairs(recent_ann) do
    print(string.format('    [%d] %s', a.type, a.text:sub(1, 100)))
end

-- Write JSON state
local function sanitize(obj, depth)
    depth = depth or 0
    if depth > 5 then return 'MAX_DEPTH' end
    local t = type(obj)
    if t == 'table' then
        local out = {}
        for k, v in pairs(obj) do
            out[tostring(k)] = sanitize(v, depth + 1)
        end
        return out
    elseif t == 'string' or t == 'number' or t == 'boolean' then
        return obj
    else
        return tostring(obj)
    end
end

local f = io.open('chronicler-monitor-output.json', 'w')
f:write(json.encode(sanitize(result)))
f:close()
