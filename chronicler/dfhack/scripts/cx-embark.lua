-- cx-embark.lua — the in-game half of world generation and embarking for the rig.
--
-- Every command is ONE atomic step (a Lua script over RPC runs with the core
-- suspended, so nothing here can wait for the screen to change). The shell in
-- cx-lifecycle.sh sequences them: genworld and embark are flows, this file is
-- the reads and pokes they are built from. Learned 2026-09-16 on DF 53.16.
--
--   cx-embark presets                 on new_region: list worldgen presets
--   cx-embark params <i|PRESET_TITLE> <title> <seed> <end_year>
--                                     on new_region/Advanced: copy preset i into
--                                     slot 0 and set seeds/title/end year there
--   cx-embark pset k=v ...            on new_region: set slot-0 fields verbatim (string seeds, any param)
--   cx-embark pdump [world]           slot 0 (or the loaded world's params) as key<TAB>value lines
--   cx-embark mods                    on new_region: the new world's mod load order
--   cx-embark modadd <id> [ver]       on new_region: tick a mod (append to the load order)
--   cx-embark survey [filter]         on choose_start_site: one row per region tile
--   cx-embark center <rx> <ry>        on choose_start_site: zoom the view onto a tile
--   cx-embark read                    on choose_start_site: the location + state line
--   cx-embark worlds                  on the title: WORLD rows DF knows about
--   cx-embark place <mm_x> <mm_y>     on choose_start_site in placement mode: put the
--                                     square's top-left on that mid-level tile and click
--   cx-embark site                    on a loaded fort: the site's mid-level min corner
--   cx-embark cells                   on a loaded fort: region_details around it, per mid-level cell
--                                     "direction:elevation" (numpad, 5 = own tile), one RD row per tile
--
-- ⚠️ Why the params command edits preset 0 and not the one you picked: the
-- Advanced screen's editable rows (`member[]`) are pointers bound to whichever
-- preset was current when the screen opened, which is always preset 0, and
-- `sel_param` only moves the header. Editing any other slot changes the header
-- and nothing else, and the world generates from the bound one. So the flow
-- copies the wanted preset INTO slot 0, field by field, and edits there.
--
-- ⚠️ Why `center` pokes zoom_cent: on choose_start_site the zoomed map is
-- centred on `zoom_cent_{x,y}`, which is in MID-LEVEL TILE units (16 per
-- region tile), not region units. Poking it with region units puts the view
-- near the world origin -- which is what the first attempt did.
--
-- ⚠️ Map clicks: DF decides which map tile a click hit from the hover it
-- computed on the PREVIOUS rendered frame (neighbor_hover_* on the site screen)
-- and overwrites gps.mouse from SDL every frame, so a bare in-script click lands
-- where the physical pointer is. `place` writes the hover fields AND clicks in
-- the same suspended call, before any frame can recompute them (29 Sep 2026):
-- the embark needs no pointer, no frontmost window, and cannot fight a person
-- using the Mac -- which is what broke the pointer-driven FPS6 pilot twice.

local args = {...}
local cmd = args[1]

local function cur() return dfhack.gui.getCurViewscreen(true) end

local function need(t, name)
    local vs = cur()
    if not t:is_instance(vs) then qerror(('need the %s screen, have %s'):format(name, tostring(vs._type))) end
    return vs
end

local function flag(e, n)
    local ok, v = pcall(function() return e.flags[n] end)
    return ok and v or false
end

if cmd == 'presets' then
    local vs = need(df.viewscreen_new_regionst, 'new_region')
    for i = 0, #vs.worldgen_presets - 1 do
        local p = vs.worldgen_presets[i]
        print(('%d\t%s\t%dx%d\tend_year=%d'):format(i, p.title, p.dim_x, p.dim_y, p.end_year))
    end

elseif cmd == 'params' then
    local vs = need(df.viewscreen_new_regionst, 'new_region')
    local idx, title, seed, end_year = tonumber(args[2]), args[3], args[4], tonumber(args[5])
    if not idx and args[2] then
        -- a preset by title, spaces as underscores (FPS6: SMALLER_REGION, SMALL_REGION, MEDIUM_REGION, LARGE_REGION);
        -- the list's order is DF's, so an index is only safe once read off `presets` on this build
        local want = args[2]:gsub('_', ' '):upper()
        for i = 0, #vs.worldgen_presets - 1 do
            if vs.worldgen_presets[i].title:upper() == want then idx = i; break end
        end
        if not idx then qerror('no preset titled ' .. want) end
    end
    if not idx or not title or not seed then qerror('usage: cx-embark params <preset-index|PRESET_TITLE> <title> <seed> [end_year]') end
    local src, dst = vs.worldgen_presets[idx], vs.worldgen_presets[0]
    if not src then qerror('no preset ' .. idx) end
    local copied = 0
    for k, v in pairs(src) do
        local t = type(v)
        if t == 'number' or t == 'boolean' or t == 'string' then dst[k] = v; copied = copied + 1
        elseif t == 'userdata' then
            local ok = pcall(function()
                for i = 0, #v - 1 do
                    local e = v[i]
                    if type(e) == 'userdata' then for j = 0, #e - 1 do dst[k][i][j] = e[j] end
                    else dst[k][i] = e end
                end
            end)
            if ok then copied = copied + 1 end
        end
    end
    dst.title = title
    for _, f in ipairs{ 'seed', 'history_seed', 'name_seed', 'creature_seed' } do dst[f] = seed end
    for _, f in ipairs{ 'has_seed', 'has_history_seed', 'has_name_seed', 'has_creature_seed' } do dst[f] = true end
    if end_year then dst.end_year = end_year; dst.beast_end_year = math.max(2, math.min(end_year, dst.beast_end_year)) end
    vs.sel_param = 0
    print(('params: slot 0 <- preset %d (%s), %d fields, %dx%d, seed=%s, end_year=%d'):format(
        idx, src.title, copied, dst.dim_x, dst.dim_y, seed, dst.end_year))

elseif cmd == 'pset' or cmd == 'pdump' then
    -- pset key=value ...   write fields of preset slot 0 (the one the Advanced screen and Create world use), typed by
    --                      the field's current value: number, boolean (true/false/1/0), string VERBATIM (DF's own random
    --                      seeds are 20-character strings, e.g. zmXW9kyBfsKzQKIIoi0A), or a flat array as a,b,c.
    --                      Nested arrays (ranges, region_counts) are refused: copy them with `params` from a preset.
    -- pdump [world]        print slot 0 (or, with `world`, the loaded world's worldgen_parms) one field per line,
    --                      key<TAB>value, in the format pset reads -- a dump of one world replays onto slot 0.
    -- 2 Oct 2026: written to regenerate region9 (four different string seeds) with the aquarium mod ticked.
    local p
    if cmd == 'pdump' and args[2] == 'world' then p = df.global.world.worldgen.worldgen_parms
    else p = need(df.viewscreen_new_regionst, 'new_region').worldgen_presets[0] end
    local function flat(v)
        local ok, n = pcall(function() return #v end)
        if not ok then return nil end
        local parts = {}
        for i = 0, n - 1 do
            local e = v[i]
            if type(e) == 'userdata' then
                local sub, ok2, m = {}, pcall(function() return #e end)
                if ok2 then for j = 0, m - 1 do sub[#sub + 1] = tostring(e[j]) end end
                parts[#parts + 1] = '[' .. table.concat(sub, ',') .. ']'
            else parts[#parts + 1] = tostring(e) end
        end
        return table.concat(parts, ',')
    end
    if cmd == 'pdump' then
        local out = {}
        for k, v in pairs(p) do
            local t = type(v)
            if t == 'userdata' then out[#out + 1] = k .. '\t' .. (flat(v) or '<userdata>')
            else out[#out + 1] = k .. '\t' .. tostring(v) end
        end
        table.sort(out)
        for _, l in ipairs(out) do print(l) end
    else
        local set, bad = 0, {}
        for i = 2, #args do
            local k, v = args[i]:match('^([%w_]+)=(.*)$')
            if not k then bad[#bad + 1] = args[i] .. '(not key=value)'
            else
                local ok, cur = pcall(function() return p[k] end)
                local t = ok and type(cur) or nil
                local wok, werr = pcall(function()
                    if t == 'number' then p[k] = math.tointeger(tonumber(v)) or tonumber(v)
                    elseif t == 'boolean' then p[k] = (v == 'true' or v == '1')
                    elseif t == 'string' then p[k] = v
                    elseif t == 'userdata' then
                        local j = 0
                        for x in (v .. ','):gmatch('([^,]*),') do
                            if x:find('[%[%]]') then error('nested array') end
                            local e = cur[j]
                            cur[j] = type(e) == 'boolean' and (x == 'true' or x == '1') or math.tointeger(tonumber(x)) or tonumber(x)
                            j = j + 1
                        end
                    else error('no such field') end
                end)
                if wok then set = set + 1 else bad[#bad + 1] = k .. '(' .. tostring(werr):gsub('^.-: ', '') .. ')' end
            end
        end
        print(('pset: %d set, %d refused%s'):format(set, #bad, #bad > 0 and (': ' .. table.concat(bad, ' ')) or ''))
    end

elseif cmd == 'mods' then
    -- the new world's mod load order (what Create world will use), id@numeric_version, in order
    local vs = need(df.viewscreen_new_regionst, 'new_region')
    local m = {}
    for i, v in ipairs(vs.object_load_order_id) do m[#m + 1] = v.value .. '@' .. vs.object_load_order_numeric_version[i] end
    print(('mods %d: %s'):format(#m, table.concat(m, ' ')))

elseif cmd == 'modadd' then
    -- modadd <id> [numeric_version]: tick a mod for the new world -- append it to the load order (last, so a graphics
    -- override wins over vanilla) and drop it from the available column, as the Mods screen and DFHack's
    -- gui/mod-manager do (copy_mod_entry). DF lists only the mods it found in <user dir>/mods/ when it STARTED: a mod
    -- folder added later needs a restart before it appears here (2 Oct 2026).
    local vs = need(df.viewscreen_new_regionst, 'new_region')
    local id, ver = args[2], tonumber(args[3])
    if not id then qerror('usage: cx-embark modadd <id> [numeric_version]') end
    for _, v in ipairs(vs.object_load_order_id) do
        if v.value == id then print('modadd: ' .. id .. ' already in the load order'); return end
    end
    local function fields(kind)
        return { id = vs[kind .. '_id'], numeric_version = vs[kind .. '_numeric_version'],
            earliest_compat_numeric_version = vs[kind .. '_earliest_compat_numeric_version'], src_dir = vs[kind .. '_src_dir'],
            name = vs[kind .. '_name'], displayed_version = vs[kind .. '_displayed_version'], mod_header = vs[kind .. '_mod_header'] }
    end
    local from, to, avail = fields('base_available'), fields('object_load_order'), fields('available')
    local at
    for i, v in ipairs(from.id) do
        if v.value == id and (not ver or from.numeric_version[i] == ver) then at = i; break end
    end
    if not at then qerror('modadd: DF lists no mod ' .. id .. (ver and ('@' .. ver) or '') .. ' (restart DF after adding a mod folder)') end
    for k, vec in pairs(to) do
        local e = from[k][at]
        if type(e) == 'userdata' then vec:insert('#', e:new()) else vec:insert('#', e) end
    end
    for i = #avail.id - 1, 0, -1 do
        if avail.id[i].value == id then for _, vec in pairs(avail) do vec:erase(i) end end
    end
    print(('modadd: %s@%d (%s, %s) is #%d of %d in the load order'):format(id, from.numeric_version[at],
        from.name[at].value, from.src_dir[at], #to.id, #to.id))

elseif cmd == 'rivers' then
    -- one row per river tile: x y biome sav elev up down left right through (through = enters one side and leaves the opposite)
    need(df.viewscreen_choose_start_sitest, 'choose_start_site')
    local wd = df.global.world.world_data
    local W, H = wd.world_width, wd.world_height
    print('x\ty\tbiome\tsav\telev\tup\tdown\tleft\tright\tthrough\tsite')
    for y = 0, H - 1 do
        for x = 0, W - 1 do
            local ok, e = pcall(dfhack.maps.getRegionBiome, x, y)
            if ok and e and (flag(e, 'has_river') or flag(e, 'is_brook') or flag(e, 'temp_river')) then
                local u, d, l, r = flag(e, 'river_up'), flag(e, 'river_down'), flag(e, 'river_left'), flag(e, 'river_right')
                local through = (u and d) and 'NS' or ((l and r) and 'EW' or '')
                local ok2, bt = pcall(dfhack.maps.getBiomeType, x, y)
                print(('%d\t%d\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%s\t%d'):format(x, y, (ok2 and bt and df.biome_type[bt]) or '?', e.savagery, e.elevation,
                    u and 1 or 0, d and 1 or 0, l and 1 or 0, r and 1 or 0, through, flag(e, 'has_site') and 1 or 0))
            end
        end
    end

elseif cmd == 'survey' then
    local vs = need(df.viewscreen_choose_start_sitest, 'choose_start_site')
    local filter = args[2]
    local wd = df.global.world.world_data
    local W, H = wd.world_width, wd.world_height
    local function info(x, y)
        if x < 0 or y < 0 or x >= W or y >= H then return nil end
        local ok, e = pcall(dfhack.maps.getRegionBiome, x, y)
        if not ok or not e then return nil end
        local ok2, bt = pcall(dfhack.maps.getBiomeType, x, y)
        local out = {
            biome = (ok2 and bt and df.biome_type[bt]) or '?',
            river = flag(e, 'has_river') or flag(e, 'is_brook') or flag(e, 'temp_river'),
            brook = flag(e, 'is_brook'), major = flag(e, 'has_river') and not flag(e, 'is_brook'),
            lake = flag(e, 'is_lake') or flag(e, 'new_lake'),
            site = flag(e, 'has_site'), peak = flag(e, 'is_peak'),
            sav = e.savagery, evil = e.evilness, elev = e.elevation, volc = e.volcanism,
            -- 12 Oct 2026: the world region's own flags; DF places GOOD/EVIL wildlife by these, and a tile's evilness can
            -- read 95 inside a region that is neither (seasonal-wildlife d7b7d46)
            rid = e.region_id, rgood = false, revil = false,
        }
        local reg = df.world_region.find(e.region_id)
        if reg then out.rgood, out.revil = reg.good == true, reg.evil == true end
        return out
    end
    -- TSV, one row per tile: x y biome river lake site sav evil elev volc same8 nbr_river nbr_ocean volcano brook major nbr_major
    -- (brook/major/nbr_major added 29 Sep 2026 for FPS6's site rule: on a SMALLER world 485 of 493 temperate tiles had
    -- the combined river flag, so 'no river' left no site; a brook and a major river are told apart)
    -- volcanoes: world_data.mountain_peaks carries every peak with an is_volcano flag
    local volcano = {}
    for _, pk in ipairs(wd.mountain_peaks) do
        if flag(pk, 'is_volcano') then volcano[pk.pos.x .. ',' .. pk.pos.y] = true end
    end
    print('x\ty\tbiome\triver\tlake\tsite\tsav\tevil\telev\tvolc\tsame8\tnbr_river\tnbr_ocean\tvolcano\tbrook\tmajor\tnbr_major\tregion\trgood\trevil')
    for y = 0, H - 1 do
        for x = 0, W - 1 do
            local t = info(x, y)
            if t and (not filter or t.biome:find(filter, 1, true)) then
                local same, riv, ocean, maj = 0, 0, 0, 0
                for dy = -1, 1 do for dx = -1, 1 do
                    if dx ~= 0 or dy ~= 0 then
                        local n = info(x + dx, y + dy)
                        if n then
                            if n.biome == t.biome then same = same + 1 end
                            if n.river then riv = riv + 1 end
                            if n.major then maj = maj + 1 end
                            if n.biome:find('OCEAN', 1, true) then ocean = ocean + 1 end
                        end
                    end
                end end
                print(('%d\t%d\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d'):format(
                    x, y, t.biome, t.river and 1 or 0, t.lake and 1 or 0, t.site and 1 or 0,
                    t.sav, t.evil, t.elev, t.volc, same, riv, ocean, volcano[x .. ',' .. y] and 1 or 0,
                    t.brook and 1 or 0, t.major and 1 or 0, maj, t.rid, t.rgood and 1 or 0, t.revil and 1 or 0))
            end
        end
    end

elseif cmd == 'center' then
    local vs = need(df.viewscreen_choose_start_sitest, 'choose_start_site')
    local rx, ry = tonumber(args[2]), tonumber(args[3])
    if not rx or not ry then qerror('usage: cx-embark center <region-x> <region-y>') end
    vs.zoomed_in = true
    vs.zoom_cent_x = rx * 16 + 8
    vs.zoom_cent_y = ry * 16 + 8
    print(('centered on region %d,%d (mm %d,%d)'):format(rx, ry, vs.zoom_cent_x, vs.zoom_cent_y))

elseif cmd == 'read' then
    local vs = need(df.viewscreen_choose_start_sitest, 'choose_start_site')
    local l = vs.location
    local confirm = false
    -- the warnings dialog draws "Confirm" and "Abort"; report it so the shell
    -- need not scan the screen separately
    local gps = df.global.gps
    for y = 0, math.min(12, gps.dimy - 1) do
        local row = {}
        for x = 0, math.min(80, gps.dimx - 1) do
            local ok, pen = pcall(dfhack.screen.readTile, x, y)
            local ch = (ok and pen and pen.ch) or 0
            row[#row + 1] = (ch >= 32 and ch < 127) and string.char(ch) or ' '
        end
        if table.concat(row):find('Confirm', 1, true) then confirm = true; break end
    end
    print(('mm_min=%d,%d mm_max=%d,%d region=%d,%d choosing=%s zoomed=%s zoom_cent=%d,%d confirm=%s'):format(
        l.embark_pos_min.x, l.embark_pos_min.y, l.embark_pos_max.x, l.embark_pos_max.y,
        l.region_pos.x, l.region_pos.y, tostring(vs.choosing_embark), tostring(vs.zoomed_in),
        vs.zoom_cent_x, vs.zoom_cent_y, tostring(confirm)))

elseif cmd == 'place' then
    -- the click embarks wherever the hover says the square is: the warnings dialog (warn_mm_* = the area) when the
    -- area has warnings, else straight to preparation
    local vs = need(df.viewscreen_choose_start_sitest, 'choose_start_site')
    if not vs.choosing_embark then qerror('place needs placement mode (click Embark first)') end
    local sx, sy = tonumber(args[2]), tonumber(args[3])
    if not sx or not sy then qerror('usage: cx-embark place <mm_x> <mm_y>') end
    local ex, ey = sx + vs.embark_dx - 1, sy + vs.embark_dy - 1
    vs.neighbor_hover_ax, vs.neighbor_hover_ay = sx // 16, sy // 16
    vs.neighbor_hover_mm_sx, vs.neighbor_hover_mm_sy, vs.neighbor_hover_mm_ex, vs.neighbor_hover_mm_ey = sx, sy, ex, ey
    local l = vs.location
    l.region_pos.x, l.region_pos.y = sx // 16, sy // 16
    l.embark_pos_min.x, l.embark_pos_min.y, l.embark_pos_max.x, l.embark_pos_max.y = sx, sy, ex, ey
    -- the click must hit the map pane, not the sidebar: the screen centre is always map
    local gps = df.global.gps
    gps.mouse_x, gps.mouse_y = gps.dimx // 4, gps.dimy // 2
    gps.precise_mouse_x, gps.precise_mouse_y = gps.mouse_x * gps.tile_pixel_x, gps.mouse_y * gps.tile_pixel_y
    require('gui').simulateInput(vs, '_MOUSE_L')
    print(('placed %d,%d..%d,%d warn=%d,%d..%d,%d'):format(sx, sy, ex, ey,
        vs.warn_mm_startx, vs.warn_mm_starty, vs.warn_mm_endx, vs.warn_mm_endy))

elseif cmd == 'site' then
    if not dfhack.isMapLoaded() then qerror('site needs a loaded fort') end
    local site = df.world_site.find(df.global.plotinfo.site_id)
    print(('site mm_min=%d,%d mm_max=%d,%d'):format(site.global_min_x, site.global_min_y, site.global_max_x, site.global_max_y))

elseif cmd == 'cells' then
    -- 12 Oct 2026: where a square's water really is. A cell takes its biome from the tile its direction names, but holds
    -- water only if it lies low (ocean below 100, a lake at its tile's elevation); cells borrowing a water biome at land
    -- height are dry. Inside an embarked square DF stores the direction as an ASCII digit ('5' = 53); both are printed 1-9.
    -- scripts/embark-place.py reads this.
    for _, rd in ipairs(df.global.world.world_data.midmap_data.region_details) do
        local rows = {}
        for y = 0, 15 do
            local r = {}
            for x = 0, 15 do
                local d = rd.biome[x][y]
                if d >= 48 then d = d - 48 end
                r[#r+1] = d .. ':' .. rd.elevation[x][y]
            end
            rows[#rows+1] = table.concat(r, ',')
        end
        print(('RD %d %d %s'):format(rd.pos.x, rd.pos.y, table.concat(rows, '/')))
    end

elseif cmd == 'size' then
    -- embark square side in mid-level tiles (1..16), written in placement mode before the click; DF 53 has no resize
    -- keys, and the square follows embark_dx/dy (verified 28 Sep 2026: 6 -> mm_max - mm_min = 5)
    local vs = need(df.viewscreen_choose_start_sitest, 'choose_start_site')
    local n = tonumber(args[2]) or 4
    vs.embark_dx, vs.embark_dy = n, tonumber(args[3]) or n
    print(('embark size %dx%d'):format(vs.embark_dx, vs.embark_dy))

elseif cmd == 'worlds' then
    -- Same source chronicler-ui `saves` reads, restricted to world folders that
    -- carry no fort yet (the ones "Start new game in existing world" lists).
    local vs = need(df.viewscreen_titlest, 'title')
    for i = 0, #vs.region_choice - 1 do
        local r = vs.region_choice[i]
        print(('%s\t%s'):format(r.filename_noext, (r.display_name:gsub('[\128-\255]', ' '))))
    end

elseif cmd == 'facts' then
    -- Everything a fort manifest needs, read from the loaded fort's own records.
    if not dfhack.isMapLoaded() then qerror('facts needs a loaded fort') end
    local site = df.world_site.find(df.global.plotinfo.site_id)
    local x0, x1 = math.floor(site.global_min_x / 16), math.floor(site.global_max_x / 16)
    local y0, y1 = math.floor(site.global_min_y / 16), math.floor(site.global_max_y / 16)
    local tiles = {}
    for rx = x0, x1 do for ry = y0, y1 do
        local ok, bt = pcall(dfhack.maps.getBiomeType, rx, ry)
        local ok2, e = pcall(dfhack.maps.getRegionBiome, rx, ry)
        tiles[#tiles+1] = ('%d,%d %s sav=%s evil=%s'):format(rx, ry, ok and bt and df.biome_type[bt] or '?',
            ok2 and e and e.savagery or '?', ok2 and e and e.evilness or '?')
    end end
    print('site\t' .. site.id .. '\tpos ' .. site.pos.x .. ',' .. site.pos.y .. '\tmm ' .. site.global_min_x .. '..' .. site.global_max_x .. ' x ' .. site.global_min_y .. '..' .. site.global_max_y)
    print('tiles\t' .. table.concat(tiles, ' | '))
    -- edge ownership: each mid-level column/row of the site is 48 map tiles; a
    -- map edge is owned by whichever region tile its mid-level tiles fall in
    local edge = {}
    local function own(mmx, mmy) local k = math.floor(mmx / 16) .. ',' .. math.floor(mmy / 16); edge[k] = (edge[k] or 0) + 1 end
    for mmx = site.global_min_x, site.global_max_x do own(mmx, site.global_min_y); own(mmx, site.global_max_y) end
    for mmy = site.global_min_y, site.global_max_y do own(site.global_min_x, mmy); own(site.global_max_x, mmy) end
    local el = {}; for k, n in pairs(edge) do el[#el+1] = k .. '=' .. n end; table.sort(el)
    print('edge_mm\t' .. table.concat(el, ' '))
    local feats = {}
    for _, f in ipairs(df.global.world.features.map_features) do local t = tostring(f._type):gsub('<type: feature_init_', ''):gsub('st>', ''); feats[t] = (feats[t] or 0) + 1 end
    local fl = {}; for k, v in pairs(feats) do fl[#fl+1] = k .. 'x' .. v end; table.sort(fl)
    print('features\t' .. (#fl > 0 and table.concat(fl, ' ') or 'none'))
    local land, water, cave, innum = 0, 0, 0, 0
    for _, p in ipairs(df.global.world.populations.all) do
        local r = p.population
        if r.region_x >= x0 and r.region_x <= x1 and r.region_y >= y0 and r.region_y <= y1 then
            if p.quantity >= 10000001 then innum = innum + 1
            elseif r.feature_idx >= 0 then water = water + 1 elseif r.cave_id >= 0 then cave = cave + 1 else land = land + 1 end
        end
    end
    print(('populations\tsurface=%d feature=%d cavern=%d innumerable=%d'):format(land, water, cave, innum))
    local wild = 0
    for _, u in ipairs(df.global.world.units.active) do if u.flags2.roaming_wilderness_population_source then wild = wild + 1 end end
    print(('units\tactive=%d wild_gated=%d'):format(#df.global.world.units.active, wild))
    print(('clock\tyear=%d tick=%d season=%d'):format(df.global.cur_year, df.global.cur_year_tick, df.global.cur_season))

else
    print([[usage: cx-embark presets | params <i> <title> <seed> [end_year] | pset k=v.. | pdump [world] | mods | modadd <id> [ver] | survey [filter] | center <rx> <ry> | read | worlds | facts]])
end
