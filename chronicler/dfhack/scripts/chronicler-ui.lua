-- chronicler-ui.lua — drive Dwarf Fortress's UI by what is on the screen
--
-- Why this exists: an autonomous dev-test cycle has to be able to load a save,
-- and DF v50's menus are widget/mouse driven. Three other routes were tried
-- and rejected against DF 53.15:
--
--   * `gui.simulateInput(title, 'SELECT')` does nothing -- the title screen
--     does not handle interface keys.
--   * DFHack's own `load-save` prints "UNTESTED WARNING" and then fails: it
--     sets `viewscreen_titlest.sel_menu_line` and reads
--     `viewscreen_loadgamest.saves`/`sel_idx`, none of which exist in 53.15.
--   * Poking viewscreen fields directly is undocumented reverse-engineering
--     and breaks on the next DF release, which is how `load-save` got here.
--
-- ⚠️ So this addresses controls by their RENDERED TEXT instead. `Export XML`
-- is a string DF has to draw for a human to click; a field name is an internal
-- detail with no such guarantee. Reading the screen buffer and clicking what
-- it says survives the structure renames that break the alternatives.
--
-- Usage:
--   chronicler-ui screen              dump the screen as text, with row numbers
--   chronicler-ui find <text>         print "x,y" of the centre of <text>
--   chronicler-ui click <text>        click the centre of <text>
--   chronicler-ui focus               print the current focus string
--
-- All matching is plain-text (not Lua patterns) and returns the FIRST match,
-- scanning top to bottom.

local gui = require('gui')

local gps = df.global.gps

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

local function screen_lines()
    local lines = {}
    for y = 0, gps.dimy - 1 do
        lines[y] = read_row(y)
    end
    return lines
end

-- Centre of `needle`, or nil. Plain find: menu labels contain '(', '"' and
-- ',', which Lua patterns would treat as syntax.
local function find_text(needle)
    for y = 0, gps.dimy - 1 do
        local s, e = read_row(y):find(needle, 1, true)
        if s then
            return math.floor((s + e) / 2) - 1, y
        end
    end
    return nil
end

local function click_at(x, y)
    gps.mouse_x, gps.mouse_y = x, y
    -- Widget hit-testing uses the precise (pixel) position, so setting only
    -- the tile position leaves the click landing at the top-left corner.
    gps.precise_mouse_x = x * gps.tile_pixel_x
    gps.precise_mouse_y = y * gps.tile_pixel_y
    gui.simulateInput(dfhack.gui.getCurViewscreen(), '_MOUSE_L')
end

local cmd, arg = ({...})[1], table.concat({select(2, ...)}, ' ')

if cmd == 'screen' then
    local lines = screen_lines()
    for y = 0, gps.dimy - 1 do
        local trimmed = lines[y]:gsub('%s+$', '')
        if #trimmed > 0 then
            print(string.format('%3d|%s', y, trimmed))
        end
    end
elseif cmd == 'find' then
    local x, y = find_text(arg)
    print(x and (x .. ',' .. y) or 'NOT FOUND')
elseif cmd == 'click' then
    local x, y = find_text(arg)
    if not x then
        print('NOT FOUND: ' .. arg)
        return
    end
    click_at(x, y)
    print('clicked ' .. x .. ',' .. y .. ' -- ' .. arg)
elseif cmd == 'focus' then
    print(dfhack.gui.getCurFocus(true)[1])
else
    print('usage: chronicler-ui screen|find <text>|click <text>|focus')
end
