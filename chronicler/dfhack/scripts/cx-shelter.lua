-- cx-shelter: find a spot for an underground shelter beside the wagon (user 13 Oct 2026: evil-weather forts lose every dwarf
-- caught outdoors -- infernal ash turned V75_EVIL's and V75_EVIL50's citizens into zombies). Prints the quickfort cursor.
--   cx-shelter find [depth=4] [half=4]  a stair column within 12 tiles of the wagon whose room (2*half+1 square, 9x9 by default;
--                               15x15 for a 100-dwarf fort) `depth` levels down, and the shaft
--                               above it, are solid ground with no liquid and no cavern; clears water_table (aquifer) there.
--                               Prints: SHELTER x y z zb  (z = surface floor of the stair, zb = room level)
--   cx-shelter wagon            deconstruct the embark wagon (its load drops; the all-items stockpile takes it in)
-- The dig/place/zone blueprints are quickfort files written by cx-lifecycle `shelter`; dig-now digs them at once.
local args = { ... }
local cmd = args[1] or 'find'

local function wagon()
    for _, b in ipairs(df.global.world.buildings.all) do
        if b:getType() == df.building_type.Wagon then return b end
    end
end

local function solid(x, y, z)
    local tt = dfhack.maps.getTileType(x, y, z)
    if not tt then return false end
    local a = df.tiletype.attrs[tt]
    if a.shape ~= df.tiletype_shape.WALL then return false end
    local d = dfhack.maps.getTileFlags(x, y, z)
    if d.flow_size > 0 or d.subterranean == false and d.outside then return false end
    local m = a.material
    return m == df.tiletype_material.SOIL or m == df.tiletype_material.STONE or m == df.tiletype_material.MINERAL
end

local function floorAt(x, y, z)
    local tt = dfhack.maps.getTileType(x, y, z)
    if not tt then return false end
    local sh = df.tiletype_shape.attrs[df.tiletype.attrs[tt].shape]
    local d = dfhack.maps.getTileFlags(x, y, z)
    return sh.walkable and d.flow_size == 0
end

if cmd == 'wagon' then
    local w = wagon()
    if not w then print('no wagon'); return end
    local ok = dfhack.buildings.deconstruct(w)
    print(('wagon %d at %d,%d,%d deconstructed: %s'):format(w.id, w.centerx, w.centery, w.z, tostring(ok)))
    return
end

if cmd ~= 'find' then qerror('usage: cx-shelter find [depth] [half] | wagon') end
local depth = tonumber(args[2]) or 4
local half = tonumber(args[3]) or 4
local w = wagon()
if not w then qerror('no wagon on this map') end
local wx, wy, wz = w.centerx, w.centery, w.z
local best
for r = 3, 12 + half - 4 do
    for dx = -r, r do
        for dy = -r, r do
            if not best and (math.abs(dx) == r or math.abs(dy) == r) then
                local sx, sy = wx + dx, wy + dy
                if floorAt(sx, sy, wz) then
                    local ok = true
                    for k = 1, depth - 1 do if not solid(sx, sy, wz - k) then ok = false; break end end
                    local zb = wz - depth
                    for x = sx - half, sx + half do
                        for y = sy - half, sy + half do
                            if ok and not solid(x, y, zb) then ok = false end
                            if ok and not (solid(x, y, zb - 1)) then ok = false end   -- a floor under the room
                        end
                    end
                    if ok then best = { sx, sy, wz, zb } end
                end
            end
        end
    end
    if best then break end
end
if not best then qerror(('no solid %dx%d room %d levels under the ground within %d tiles of the wagon at %d,%d,%d'):format(2 * half + 1, 2 * half + 1, depth, 12 + half - 4, wx, wy, wz)) end
local sx, sy, sz, zb = best[1], best[2], best[3], best[4]
local cleared = 0
for z = zb - 1, sz do
    for x = sx - half - 1, sx + half + 1 do
        for y = sy - half - 1, sy + half + 1 do
            local d = dfhack.maps.getTileFlags(x, y, z)
            if d and d.water_table then d.water_table = false; cleared = cleared + 1 end
        end
    end
end
print(('SHELTER %d %d %d %d (wagon %d,%d,%d; %d aquifer tile(s) cleared)'):format(sx, sy, sz, zb, wx, wy, wz, cleared))
