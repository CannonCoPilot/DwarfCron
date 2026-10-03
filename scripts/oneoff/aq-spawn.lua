-- Test-only spawner for the aquarium look tests (3 Oct 2026; not product code). Puts swimmers at EVERY water level in
-- view of the fort: for each z with water of the asked kind, N_PER_Z units at random cells with flow >= 4, cycling a
-- species list. Prepend `ARGS = { salt = true|false, per_z = 12, species = { 'FISH_HAKE', ... }, zmin = 0, zmax = 999 }`.
-- Placement = dfhack.units.create + the documented writes (memory: headless-unit-placement); no population ref (these
-- are props for screenshots, not managed wildlife).
local ok, err = pcall(function()
    local A = ARGS or {}
    local per = A.per_z or 12
    local races = {}
    for _, tok in ipairs(A.species or {}) do
        for i, c in ipairs(df.global.world.raws.creatures.all) do
            if c.creature_id == tok then races[#races + 1] = { i = i, tok = tok, n = #c.caste }; break end
        end
    end
    if #races == 0 then print('no species found'); return end
    -- water cells by z, from the map blocks (one pass)
    local cells = {}
    for _, b in ipairs(df.global.world.map.map_blocks) do
        local z = b.map_pos.z
        if z >= (A.zmin or 0) and z <= (A.zmax or 999) then
            for x = 0, 15 do for y = 0, 15 do
                local d = b.designation[x][y]
                if d.flow_size >= 4 and not d.liquid_type and (A.salt == nil or d.water_salt == A.salt) and not b.occupancy[x][y].unit then
                    local t = cells[z] or {}; cells[z] = t
                    t[#t + 1] = { b.map_pos.x + x, b.map_pos.y + y, z, b, x, y }
                end
            end end
        end
    end
    local made, k = 0, 0
    local zs = {}; for z in pairs(cells) do zs[#zs + 1] = z end; table.sort(zs, function(a, b) return a > b end)
    for _, z in ipairs(zs) do
        local t = cells[z]
        local n = math.min(per, #t)
        local got = 0
        for _ = 1, n do
            local c = table.remove(t, math.random(#t))
            k = k + 1
            local R = races[(k - 1) % #races + 1]
            local u = dfhack.units.create(R.i, math.random(0, R.n - 1))
            if u then
                u.animal.leave_countdown = 400000
                u.pos:assign(xyz2pos(c[1], c[2], c[3])); u.idle_area:assign(u.pos)
                df.global.world.units.active:insert('#', u)
                c[4].occupancy[c[5]][c[6]].unit = true
                u.flags1.inactive = false
                made = made + 1; got = got + 1
            end
        end
        print(('z %d: %d of %d water cells got a swimmer'):format(z, got, #t + got))
    end
    print('spawned', made, 'species', #races)
end)
if not ok then print('ERR', err) end
