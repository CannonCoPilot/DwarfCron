-- chronicler-ui.lua — in-game half of the DF rig: read the screen, drive the UI, report state
--
-- Why this exists: an autonomous dev-test cycle has to load saves, save, pause,
-- step time, and get back to the title screen -- and DF v50+'s menus are
-- widget/mouse driven. Three other routes were tried and rejected against DF 53.15:
--
--   * `gui.simulateInput(title, 'SELECT')` does nothing -- the title screen
--     does not handle interface keys.
--   * DFHack's own `load-save` prints "UNTESTED WARNING" and then fails: it
--     sets `viewscreen_titlest.sel_menu_line` and reads
--     `viewscreen_loadgamest.saves`/`sel_idx`, none of which exist in 53.15.
--   * Poking viewscreen fields to NAVIGATE is undocumented reverse-engineering
--     and breaks on the next DF release, which is how `load-save` got here.
--
-- So the rule is: READ from DFHack structures wherever they answer the question
-- (which saves exist, which world owns a folder, is the map loaded, is the game
-- paused), and CLICK by rendered text. `Export XML` is a string DF has to draw
-- for a human to click; a field name carries no such guarantee.
--
-- ⚠️ Every command here is ONE atomic step. A Lua script run over RPC executes
-- with the core suspended, so a loop that waits for the screen to change can
-- never see it change -- the next frame is not drawn until the script returns.
-- Multi-step flows (load a save, name a manual save) are sequenced from the
-- shell in cx-lifecycle.sh, one call per step, polling between calls. This is
-- also why `fort/gen-world embark` could not work: it tried to click through
-- five screens inside one script.
--
-- Usage:
--   chronicler-ui state                  one line: screen, focus, map, paused, year, tick, modal
--   chronicler-ui screen [y0 [y1]]       dump rows of the screen as text
--   chronicler-ui find <text>            "x,y" of the first match, or NOT FOUND
--   chronicler-ui findlast <text>        same, scanning from the bottom
--   chronicler-ui click <text>           click the first match
--   chronicler-ui clicklast <text>       click the last match
--   chronicler-ui clickxy <x> <y>         click a screen tile coordinate (map clicks)
--   chronicler-ui clickrel <anchor> <dy> <text>
--                                        find <anchor>, go <dy> rows, click <text> on THAT row
--   chronicler-ui key <KEY> [KEY ...]    feed interface keys (SELECT, OPTIONS, LEAVESCREEN, ...)
--   chronicler-ui type <text>            type printable text (STRING_A### keys)
--   chronicler-ui modal                  dismiss the first-run Welcome panel if it is up
--   chronicler-ui saves                  title screen only: every save DF knows, from structure
--   chronicler-ui pause|unpause          set df.global.pause_state
--   chronicler-ui focus                  the focus string (⚠️ a DFHack window on top replaces it)
--
-- All matching is plain-text (not Lua patterns) and non-ASCII bytes on both
-- sides are treated as a single space, because that is what the screen reader
-- produces for accented letters in world names.

local gui = require('gui')
local gps = df.global.gps

-- ---------------------------------------------------------------- screen ----

-- Read one row of the rendered screen as a plain string.
--
-- ⚠️ Non-printable and box-drawing tiles become spaces rather than being
-- skipped, so a character's column index in this string is its real screen
-- column. Dropping them would shift every subsequent match left and the click
-- would land somewhere else on the row.
local function read_row(y)
    local row = {}
    for x = 0, gps.dimx - 1 do
        local ok, pen = pcall(dfhack.screen.readTile, x, y)
        local ch = (ok and pen and pen.ch) or 0
        row[#row + 1] = (ch >= 32 and ch < 127) and string.char(ch) or ' '
    end
    return table.concat(row)
end

-- Non-ASCII bytes in a DF string render as something read_row turns into a
-- space, so normalise the needle the same way before a plain find.
local function ascii(s)
    return (s:gsub('[\128-\255]', ' '))
end

-- Centre of `needle` on row y, or nil.
local function find_on_row(y, needle)
    local s, e = read_row(y):find(needle, 1, true)
    if s then return math.floor((s + e) / 2) - 1 end
end

-- First (or last) row containing `needle`. Plain find: menu labels contain
-- '(', '"' and ',', which Lua patterns would treat as syntax.
local function find_text(needle, from_bottom)
    needle = ascii(needle)
    local y0, y1, step = 0, gps.dimy - 1, 1
    if from_bottom then y0, y1, step = gps.dimy - 1, 0, -1 end
    for y = y0, y1, step do
        local x = find_on_row(y, needle)
        if x then return x, y end
    end
    return nil
end

local function click_at(x, y)
    gps.mouse_x, gps.mouse_y = x, y
    -- ⚠️ Widget hit-testing uses the precise (pixel) position, so setting only
    -- the tile position leaves the click landing at the top-left corner.
    gps.precise_mouse_x = x * gps.tile_pixel_x
    gps.precise_mouse_y = y * gps.tile_pixel_y
    gui.simulateInput(dfhack.gui.getCurViewscreen(true), '_MOUSE_L')
end

local function modal_row()
    local _, y = find_text('Welcome to Dwarf Fortress')
    return y
end

-- ----------------------------------------------------------------- state ----

local function state_line()
    local vs = dfhack.gui.getCurViewscreen(true)
    local focus = dfhack.gui.getCurFocus(true)[1] or '?'
    local map = dfhack.isMapLoaded()
    local parts = {
        'screen=' .. tostring(vs._type):gsub('<type: ', ''):gsub('>', ''),
        'focus=' .. focus,
        'world=' .. tostring(dfhack.isWorldLoaded()),
        'map=' .. tostring(map),
        'paused=' .. tostring(df.global.pause_state),
        'modal=' .. tostring(modal_row() ~= nil),
    }
    if map then
        parts[#parts + 1] = 'year=' .. df.global.cur_year
        parts[#parts + 1] = 'tick=' .. df.global.cur_year_tick
        parts[#parts + 1] = 'season=' .. df.global.cur_season
        parts[#parts + 1] = 'units=' .. #df.global.world.units.active
    end
    if df.viewscreen_titlest:is_instance(vs) then
        parts[#parts + 1] = 'titlemode=' .. df.title_mode_type[vs.mode]
    end
    return table.concat(parts, ' ')
end

-- --------------------------------------------------------------- dispatch ----

local args = {...}
local cmd = args[1]
local arg = table.concat({select(2, ...)}, ' ')

if cmd == 'state' then
    print(state_line())

elseif cmd == 'screen' then
    local y0 = tonumber(args[2]) or 0
    local y1 = tonumber(args[3]) or (gps.dimy - 1)
    for y = y0, y1 do
        local trimmed = read_row(y):gsub('%s+$', '')
        if #trimmed > 0 then print(string.format('%3d|%s', y, trimmed)) end
    end

elseif cmd == 'find' or cmd == 'findlast' then
    local x, y = find_text(arg, cmd == 'findlast')
    print(x and (x .. ',' .. y) or 'NOT FOUND')

elseif cmd == 'click' or cmd == 'clicklast' then
    local x, y = find_text(arg, cmd == 'clicklast')
    if not x then print('NOT FOUND: ' .. arg) return end
    click_at(x, y)
    print('clicked ' .. x .. ',' .. y .. ' -- ' .. arg)

elseif cmd == 'clickxy' then
    -- click a screen TILE coordinate. Needed where the target is not text:
    -- the world map on the embark screen (DF v50 places the embark rectangle
    -- by a map click and has no interface key for it). Added 2026-09-16.
    local x, y = tonumber(args[2]), tonumber(args[3])
    if not x or not y then qerror('usage: chronicler-ui clickxy <x> <y>') end
    click_at(x, y)
    print(('clicked %d,%d'):format(x, y))
elseif cmd == 'clickrel' then
    -- clickrel <anchor> <dy> <text>: the save list draws each entry as two rows
    -- ("Fort, Fortress" above "Folder: name"), so selecting a FOLDER means
    -- clicking the row above its label. A plain click on "Fortress" picks the
    -- first entry in the list, whichever folder that is.
    local anchor, dy, text = args[2], tonumber(args[3]), table.concat({select(4, ...)}, ' ')
    if not anchor or not dy then print('usage: clickrel <anchor> <dy> <text>') return end
    local _, ay = find_text(anchor)
    if not ay then print('NOT FOUND: ' .. anchor) return end
    local y = ay + dy
    local x = find_on_row(y, ascii(text))
    if not x then print(('NOT FOUND: %q on row %d (anchor %q at row %d)'):format(text, y, anchor, ay)) return end
    click_at(x, y)
    print(('clicked %d,%d -- %s (row %+d from %s)'):format(x, y, text, dy, anchor))

elseif cmd == 'key' then
    local vs = dfhack.gui.getCurViewscreen(true)
    for i = 2, #args do
        if not df.interface_key[args[i]] then print('UNKNOWN KEY: ' .. args[i]) return end
        gui.simulateInput(vs, args[i])
    end
    print('sent ' .. table.concat({select(2, ...)}, ' '))

elseif cmd == 'type' then
    local vs = dfhack.gui.getCurViewscreen(true)
    local n = 0
    for ch in arg:gmatch('.') do
        local b = ch:byte()
        if b >= 32 and b < 127 then gui.simulateInput(vs, ('STRING_A%03d'):format(b)); n = n + 1 end
    end
    print('typed ' .. n .. ' chars')

elseif cmd == 'modal' then
    -- ⚠️ The first-run "Welcome to Dwarf Fortress" panel is modal and hides the
    -- title menu behind it, but the focus string still says title/Default, so
    -- only the screen text reveals it. gen-world's docs say nothing dismisses it
    -- programmatically; that was a misdiagnosis of the pixel-coordinate bug --
    -- with precise_mouse set, its Okay button takes a fed click first time.
    if not modal_row() then print('NONE') return end
    local x, y = find_text('Okay')
    if not x then print('MODAL UP BUT NO OKAY BUTTON') return end
    click_at(x, y)
    print('DISMISSED')

elseif cmd == 'saves' then
    -- Read from structure, not from the screen. The screen groups saves under a
    -- world row that only says "Three saves" until expanded; the headers here
    -- say exactly which folder belongs to which world.
    local vs = dfhack.gui.getCurViewscreen(true)
    if not df.viewscreen_titlest:is_instance(vs) then print('NOT ON TITLE SCREEN') return end
    for i = 0, #vs.savegame_header - 1 do
        local h = vs.savegame_header[i]
        print(('SAVE\t%s\t%s\t%s\t%d'):format(h.filename_noext, ascii(h.world_name), ascii(h.fort_name), h.year))
    end
    for i = 0, #vs.region_choice - 1 do
        local r = vs.region_choice[i]
        print(('WORLD\t%s\t%s'):format(r.filename_noext, ascii(r.display_name)))
    end

elseif cmd == 'pause' then
    df.global.pause_state = true; print('paused=true tick=' .. df.global.cur_year_tick)
elseif cmd == 'unpause' then
    df.global.pause_state = false; print('paused=false tick=' .. df.global.cur_year_tick)

elseif cmd == 'focus' then
    print(dfhack.gui.getCurFocus(true)[1])

else
    print('usage: chronicler-ui state|screen|find|findlast|click|clicklast|clickrel|key|type|modal|saves|pause|unpause|focus')
end
