-- worldgen-bridge.lua — DFHack worldgen monitor for Chronicler
--
-- Polls df.global.world.worldgen_status every 30 frames (~0.5s) during
-- world generation. Writes JSON snapshots to worldgen-status.json for
-- Chronicler's Python ingester to poll via HTTP.
--
-- Auto-registers via dfhack.onStateChange; no manual setup needed if
-- this script is in hack/scripts/ and loaded once.
--
-- Usage:
--   1. Copy to hack/scripts/
--   2. Run once: worldgen-bridge
--   3. Monitors automatically on next worldgen start
--
-- Manual control:
--   worldgen-bridge start    — Force start monitoring
--   worldgen-bridge stop     — Force stop monitoring
--   worldgen-bridge status   — Print current state
--   worldgen-bridge snapshot — Write one snapshot and exit

local json = require('json')
local repeatUtil = require('repeat-util')

local OUTPUT_PATH = 'worldgen-status.json'
local POLL_INTERVAL = 30  -- frames (~0.5s at 60fps)
local JOB_NAME = 'worldgen-monitor'

-- ── Worldgen state enum names ──────────────────────────────────────

local STATE_NAMES = {
    [-1] = 'None',
    [0]  = 'Initializing',
    [1]  = 'PreparingElevation',
    [2]  = 'SettingTemperature',
    [3]  = 'RunningRivers',
    [4]  = 'FormingLakesAndMinerals',
    [5]  = 'GrowingVegetation',
    [6]  = 'VerifyingTerrain',
    [7]  = 'ImportingWildlife',
    [8]  = 'RecountingLegends',
    [9]  = 'Finalizing',
    [10] = 'Done',
}

-- Estimated phase weights for progress calculation (cumulative effort)
local PHASE_PROGRESS = {
    [-1] = 0,
    [0]  = 2,   -- Initializing
    [1]  = 8,   -- PreparingElevation
    [2]  = 12,  -- SettingTemperature
    [3]  = 22,  -- RunningRivers (slow)
    [4]  = 30,  -- FormingLakesAndMinerals
    [5]  = 38,  -- GrowingVegetation
    [6]  = 42,  -- VerifyingTerrain
    [7]  = 50,  -- ImportingWildlife
    [8]  = 90,  -- RecountingLegends (very slow — simulates history)
    [9]  = 98,  -- Finalizing
    [10] = 100, -- Done
}

-- ── Snapshot extraction ────────────────────────────────────────────

local function get_worldgen_snapshot()
    local wgs = df.global.world.worldgen_status
    if not wgs then return nil end

    local state_val = wgs.state
    local state_name = STATE_NAMES[state_val] or tostring(state_val)
    local base_progress = PHASE_PROGRESS[state_val] or 0

    local snapshot = {
        state = state_name,
        state_id = state_val,
        progress_pct = base_progress,
        timestamp = os.time(),
        num_rejects = wgs.num_rejects,
    }

    -- River progress (during RunningRivers phase)
    pcall(function()
        snapshot.rivers_cur = wgs.rivers_cur
        snapshot.rivers_total = wgs.rivers_total
        if state_val == 3 and wgs.rivers_total > 0 then
            -- Interpolate progress within river phase
            local river_pct = wgs.rivers_cur / wgs.rivers_total
            snapshot.progress_pct = PHASE_PROGRESS[2] +
                (PHASE_PROGRESS[3] - PHASE_PROGRESS[2]) * river_pct
        end
    end)

    -- Finalization sub-progress
    pcall(function()
        snapshot.finalized_civ_mats = wgs.finalized_civ_mats
        snapshot.finalized_art = wgs.finalized_art
        snapshot.finalized_uniforms = wgs.finalized_uniforms
        snapshot.finalized_sites = wgs.finalized_sites
    end)

    -- Prehistory flags
    pcall(function()
        snapshot.placed_caves = wgs.placed_caves
        snapshot.placed_good_evil = wgs.placed_good_evil
        snapshot.placed_megabeasts = wgs.placed_megabeasts
        snapshot.placed_other_beasts = wgs.placed_other_beasts
        snapshot.finished_prehistory = wgs.finished_prehistory
    end)

    -- Civ placement
    pcall(function()
        snapshot.civ_count = wgs.civ_count
        snapshot.civs_left_to_place = wgs.civs_left_to_place
    end)

    -- Entity counts from the world being generated
    pcall(function()
        snapshot.figure_count = #df.global.world.history.figures
        snapshot.event_count = #df.global.world.history.events
        snapshot.site_count = #df.global.world.world_data.sites
        snapshot.entity_count = #df.global.world.entities.all
        snapshot.region_count = #df.global.world.world_data.regions
    end)

    -- World dimensions
    pcall(function()
        snapshot.world_width = df.global.world.world_data.world_width
        snapshot.world_height = df.global.world.world_data.world_height
    end)

    -- Capture cur_year during history simulation (states 8 and 9)
    -- DF reports state 9 ("Finalizing") during active history simulation
    if state_val == 8 or state_val == 9 then
        pcall(function()
            local cur_year = df.global.cur_year
            if cur_year and cur_year > 0 then
                snapshot.cur_year = cur_year
                snapshot.cur_year_tick = df.global.cur_year_tick
                -- Estimate sub-progress within history simulation
                -- Target varies by settings (250 short, 550 medium, 1050 long)
                local year_pct = math.min(1.0, cur_year / 250)
                local base = PHASE_PROGRESS[7]  -- 50
                local top = PHASE_PROGRESS[9]   -- 98
                snapshot.progress_pct = base + (top - base) * year_pct
            end
        end)
    end

    return snapshot
end

-- ── File output ────────────────────────────────────────────────────

local function write_snapshot()
    local snapshot = get_worldgen_snapshot()
    if not snapshot then return false end

    local ok, err = pcall(function()
        json.encode_file(snapshot, OUTPUT_PATH)
    end)

    if not ok then
        dfhack.printerr('[Worldgen] Write failed: ' .. tostring(err))
    end
    return ok
end

-- ── Monitoring lifecycle ───────────────────────────────────────────

local function start_monitoring()
    if repeatUtil.isScheduled(JOB_NAME) then
        print('[Worldgen] Already monitoring')
        return
    end

    repeatUtil.scheduleEvery(JOB_NAME, POLL_INTERVAL, 'frames', write_snapshot)
    print('[Worldgen] Monitoring started (every ' .. POLL_INTERVAL .. ' frames)')
end

local function stop_monitoring()
    if repeatUtil.isScheduled(JOB_NAME) then
        repeatUtil.cancel(JOB_NAME)
        print('[Worldgen] Monitoring stopped')
    else
        print('[Worldgen] Not currently monitoring')
    end
end

local function print_status()
    local monitoring = repeatUtil.isScheduled(JOB_NAME)
    print('[Worldgen] Monitoring: ' .. (monitoring and 'ACTIVE' or 'INACTIVE'))

    local snapshot = get_worldgen_snapshot()
    if snapshot then
        print('[Worldgen] State: ' .. snapshot.state ..
              ' (' .. string.format('%.1f', snapshot.progress_pct) .. '%)')
        if snapshot.figure_count then
            print('[Worldgen] Figures: ' .. snapshot.figure_count ..
                  ', Events: ' .. snapshot.event_count ..
                  ', Sites: ' .. snapshot.site_count ..
                  ', Entities: ' .. snapshot.entity_count)
        end
        if snapshot.cur_year then
            print('[Worldgen] Year: ' .. snapshot.cur_year)
        end
    else
        print('[Worldgen] No worldgen data available')
    end
end

-- ── Auto-start via onStateChange ───────────────────────────────────

dfhack.onStateChange.worldgen_monitor = function(code)
    if code == SC_WORLD_LOADED then
        -- Worldgen: world loaded but no map yet
        if not dfhack.isMapLoaded() then
            local wgs = df.global.world.worldgen_status
            if wgs and wgs.state >= 0 and wgs.state <= 9 then
                print('[Worldgen] World generation detected — starting monitor')
                start_monitoring()
            end
        end
    elseif code == SC_WORLD_UNLOADED then
        -- Write final snapshot before stopping
        write_snapshot()
        stop_monitoring()
    end
end

-- ── CLI dispatch ───────────────────────────────────────────────────

local args = { ... }
local cmd = args[1] or 'register'

if cmd == 'start' then
    start_monitoring()
elseif cmd == 'stop' then
    stop_monitoring()
elseif cmd == 'status' then
    print_status()
elseif cmd == 'snapshot' then
    if write_snapshot() then
        print('[Worldgen] Snapshot written to ' .. OUTPUT_PATH)
    end
elseif cmd == 'register' then
    -- Default: just register the onStateChange handler
    print('[Worldgen] Registered auto-start handler (onStateChange)')
    -- If worldgen is actively in progress, start immediately.
    -- During worldgen: world is loaded but map is NOT loaded.
    -- In fortress mode: both world and map are loaded, so skip.
    if dfhack.isWorldLoaded() and not dfhack.isMapLoaded() then
        local wgs = df.global.world.worldgen_status
        if wgs and wgs.state >= 0 and wgs.state <= 9 then
            start_monitoring()
        end
    end
else
    print('Usage: worldgen-bridge [start|stop|status|snapshot|register]')
end
