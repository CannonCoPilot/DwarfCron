-- girderpriced-surface-water.lua — Find SURFACE water specifically

print("=== SURFACE WATER (z=134-135 only) ===")

local surface_water = {}
for x = 0, 191 do
    for y = 0, 191 do
        for z = 134, 140 do
            local blk = dfhack.maps.getTileBlock(x, y, z)
            if blk then
                local des = blk.designation[x % 16][y % 16]
                if des.flow_size > 0 and not des.hidden and not des.liquid_type then
                    -- Also check if tile is outside
                    if des.outside then
                        table.insert(surface_water, {x=x, y=y, z=z, flow=des.flow_size})
                    end
                end
            end
        end
    end
end
print("Outdoor surface water tiles: " .. #surface_water)

-- Also check for brook tiles (special tiletype)
local brooks = 0
for x = 0, 191 do
    for y = 0, 191 do
        local blk = dfhack.maps.getTileBlock(x, y, 134)
        if blk then
            local tt = blk.tiletype[x % 16][y % 16]
            local special = df.tiletype.attrs[tt].special
            if special == df.tiletype_special.RIVER_SOURCE or
               special == df.tiletype_special.BROOK then
                brooks = brooks + 1
                if brooks <= 5 then
                    print("  Brook tile at (" .. x .. "," .. y .. ",134)")
                end
            end
        end
    end
end
print("Brook tiles: " .. brooks)

if #surface_water > 0 then
    -- Place water source zone at nearest
    local best = nil
    local best_dist = 99999
    for _, wt in ipairs(surface_water) do
        local dist = math.abs(wt.x - 96) + math.abs(wt.y - 95)
        if dist < best_dist then
            best = wt
            best_dist = dist
        end
    end
    if best then
        print("Nearest surface water: (" .. best.x .. "," .. best.y .. "," .. best.z ..
              ") dist=" .. best_dist)
        local qf = reqscript('quickfort')
        qf.apply_blueprint{mode='zone', data='w(7x3)',
                          pos={x=best.x-3, y=best.y-1, z=best.z}}
        print("Water source zone placed")
    end
else
    -- No surface water — check the nearest underground water that's accessible
    print("No outdoor surface water. Checking accessible underground...")
    -- The underground water at z=133 near (104,70) requires digging to reach
    -- For now, dwarves can drink from the embark drinks
    -- Once the still is built, brewing will provide drink
end

-- Check Still build status — is it even designated?
print("\n--- Still Status ---")
local still_count = 0
local still_built = false
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop then
        if b:getSubtype() == df.workshop_type.Still then
            still_count = still_count + 1
            if b.flags.exists then
                still_built = true
                print("Still BUILT at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ")")
            else
                print("Still PLANNED at (" .. b.centerx .. "," .. b.centery .. "," .. b.z ..
                      ") waiting for construction")
            end
        end
    end
end
if still_count == 0 then
    print("NO Still designated! Placing one now...")
    local qf = reqscript('quickfort')
    -- Place at (100,88,134) — should be clear
    qf.apply_blueprint{mode='build', data='ws', pos={x=100, y=88, z=134}}
    print("Still placed at (100,88,134)")
end

print("\n=== DONE ===")
