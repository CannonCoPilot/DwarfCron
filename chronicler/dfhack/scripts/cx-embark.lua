-- cx-embark.lua — the in-game half of world generation and embarking for the rig.
--
-- Every command is ONE atomic step (a Lua script over RPC runs with the core
-- suspended, so nothing here can wait for the screen to change). The shell in
-- cx-lifecycle.sh sequences them: genworld and embark are flows, this file is
-- the reads and pokes they are built from. Learned 2026-09-16 on DF 53.16.
--
--   cx-embark presets                 on new_region: list worldgen presets
--   cx-embark params <i> <title> <seed> <end_year>
--                                     on new_region/Advanced: copy preset i into
--                                     slot 0 and set seeds/title/end year there
--   cx-embark survey [filter]         on choose_start_site: one row per region tile
--   cx-embark center <rx> <ry>        on choose_start_site: zoom the view onto a tile
--   cx-embark read                    on choose_start_site: the location + state line
--   cx-embark worlds                  on the title: WORLD rows DF knows about
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
-- ⚠️ What this file deliberately does NOT do: click the map. DF decides which
-- map tile a click hit from the hover it computed on the PREVIOUS rendered
-- frame, and it overwrites gps.mouse from SDL every frame, so an in-script
-- click always lands where the physical pointer is. Map clicks are real
-- pointer events, driven by cx-mouse.py from the shell.

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
    if not idx or not title or not seed then qerror('usage: cx-embark params <preset-index> <title> <seed> [end_year]') end
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
        return {
            biome = (ok2 and bt and df.biome_type[bt]) or '?',
            river = flag(e, 'has_river') or flag(e, 'is_brook') or flag(e, 'temp_river'),
            lake = flag(e, 'is_lake') or flag(e, 'new_lake'),
            site = flag(e, 'has_site'), peak = flag(e, 'is_peak'),
            sav = e.savagery, evil = e.evilness, elev = e.elevation, volc = e.volcanism,
        }
    end
    -- TSV, one row per tile: x y biome river lake site sav evil elev volc same8 nbr_river nbr_ocean
    -- volcanoes: world_data.mountain_peaks carries every peak with an is_volcano flag
    local volcano = {}
    for _, pk in ipairs(wd.mountain_peaks) do
        if flag(pk, 'is_volcano') then volcano[pk.pos.x .. ',' .. pk.pos.y] = true end
    end
    print('x\ty\tbiome\triver\tlake\tsite\tsav\tevil\telev\tvolc\tsame8\tnbr_river\tnbr_ocean\tvolcano')
    for y = 0, H - 1 do
        for x = 0, W - 1 do
            local t = info(x, y)
            if t and (not filter or t.biome:find(filter, 1, true)) then
                local same, riv, ocean = 0, 0, 0
                for dy = -1, 1 do for dx = -1, 1 do
                    if dx ~= 0 or dy ~= 0 then
                        local n = info(x + dx, y + dy)
                        if n then
                            if n.biome == t.biome then same = same + 1 end
                            if n.river then riv = riv + 1 end
                            if n.biome:find('OCEAN', 1, true) then ocean = ocean + 1 end
                        end
                    end
                end end
                print(('%d\t%d\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d'):format(
                    x, y, t.biome, t.river and 1 or 0, t.lake and 1 or 0, t.site and 1 or 0,
                    t.sav, t.evil, t.elev, t.volc, same, riv, ocean, volcano[x .. ',' .. y] and 1 or 0))
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
    print([[usage: cx-embark presets | params <i> <title> <seed> [end_year] | survey [filter] | center <rx> <ry> | read | worlds | facts]])
end
