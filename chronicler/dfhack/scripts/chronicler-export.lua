-- chronicler-export.lua — Automated legends export with manifest
--
-- Wraps DFHack's `exportlegends` and writes a manifest file so the
-- Mac-side transfer/ingest command knows which files were produced.
--
-- Usage (from DFHack console, in Legends mode):
--   chronicler-export
--
-- Output:
--   - Runs exportlegends all (XML + maps)
--   - Writes chronicler-export-manifest.json with file paths and metadata
--
-- The manifest enables automated transfer: the Mac-side script reads it
-- via HTTP, downloads the XML files, and runs `chronicler ingest`.

local json = require('json')

-- Check we're in legends mode
local gview = df.global.gview
local vs = cycleType and cycleType or nil

-- DFHack viewscreen check
local scr = dfhack.gui.getCurViewscreen()
local scr_name = scr._type and tostring(scr._type) or 'unknown'

if not string.find(scr_name, 'legends') and not string.find(scr_name, 'Legend') then
    -- Also check game mode
    local mode = df.global.gametype
    -- mode 3 = LEGENDS in some versions
    if mode ~= 3 then
        dfhack.printerr('chronicler-export: Not in Legends mode (screen: ' .. scr_name .. ', gametype: ' .. tostring(mode) .. ')')
        dfhack.printerr('  Enter Legends mode first (retire fort -> legends), then run this command.')
        return
    end
end

print('[chronicler] Starting legends export...')

-- Get world/save info for manifest
local save_dir = df.global.world.cur_savegame and df.global.world.cur_savegame.save_dir or 'unknown'
local cur_year = df.global.cur_year
local world_name = ''
if df.global.world.world_data and df.global.world.world_data.name then
    world_name = dfhack.df2utf(dfhack.translation.translateName(df.global.world.world_data.name, true))
end

print('[chronicler] World: ' .. world_name .. ' | Save: ' .. save_dir .. ' | Year: ' .. tostring(cur_year))

-- Run the export
print('[chronicler] Running exportlegends all...')
dfhack.run_command('exportlegends', 'all')
print('[chronicler] Export complete.')

-- Construct expected file names
-- DFHack exportlegends produces: <save_dir>-<YYYYY>-<MM>-<DD>-legends.xml
-- The date is the in-game date at export time
local year_str = string.format('%05d', cur_year)
local month = math.floor(df.global.cur_year_tick / 33600) + 1
local day = math.floor((df.global.cur_year_tick % 33600) / 1200) + 1
local month_str = string.format('%02d', month)
local day_str = string.format('%02d', day)

local base = save_dir .. '-' .. year_str .. '-' .. month_str .. '-' .. day_str
local legends_file = base .. '-legends.xml'
local legends_plus_file = base .. '-legends_plus.xml'

-- Write manifest
local manifest = {
    export_time = os.time(),
    world_name = world_name,
    save_dir = save_dir,
    cur_year = cur_year,
    base_name = base,
    files = {
        legends = legends_file,
        legends_plus = legends_plus_file,
    },
}

local write_ok, write_err = pcall(function()
    json.encode_file(manifest, 'chronicler-export-manifest.json')
end)

if write_ok then
    print('[chronicler] Manifest written: chronicler-export-manifest.json')
    print('[chronicler] Files:')
    print('  ' .. legends_file)
    print('  ' .. legends_plus_file)
    print('')
    print('[chronicler] Transfer from Mac:')
    print('  deploy-homeserver.sh legends')
else
    dfhack.printerr('[chronicler] Failed to write manifest: ' .. tostring(write_err))
    dfhack.printerr('[chronicler] Files should be: ' .. legends_file .. ' and ' .. legends_plus_file)
end
