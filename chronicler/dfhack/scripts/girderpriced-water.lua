-- girderpriced-water.lua — Find surface water and designate water source zone

print("=== WATER SOURCE SEARCH ===")

-- Scan surface z-level for water tiles (brooks, streams, ponds)
local water_tiles = {}
for x = 0, 191 do
    for y = 0, 191 do
        -- Check z=134 (surface) and z=135 (sometimes brooks are on higher z)
        for _, z in ipairs({134, 135, 133}) do
            local blk = dfhack.maps.getTileBlock(x, y, z)
            if blk then
                local des = blk.designation[x % 16][y % 16]
                if des.flow_size > 0 and not des.hidden then
                    table.insert(water_tiles, {x=x, y=y, z=z, flow=des.flow_size,
                                               is_magma=des.liquid_type})
                end
            end
        end
    end
end

print("Surface water tiles found: " .. #water_tiles)

if #water_tiles > 0 then
    -- Find the cluster nearest to the fortress (wagon was at 96,95)
    local best = nil
    local best_dist = 99999
    for _, wt in ipairs(water_tiles) do
        if not wt.is_magma then
            local dist = math.abs(wt.x - 96) + math.abs(wt.y - 95)
            if dist < best_dist then
                best = wt
                best_dist = dist
            end
        end
    end

    if best then
        print("Nearest water: (" .. best.x .. "," .. best.y .. "," .. best.z ..
              ") flow=" .. best.flow .. " dist=" .. best_dist)

        -- Place water source zone around it (5x5 centered)
        local qf = reqscript('quickfort')
        qf.apply_blueprint{mode='zone', data='w(5x5)',
                          pos={x=best.x-2, y=best.y-2, z=best.z}}
        print("Water source zone placed at (" .. (best.x-2) .. "," .. (best.y-2) ..
              "," .. best.z .. ")")

        -- Also show a few more water tiles for context
        print("\nSample water tiles:")
        for i = 1, math.min(10, #water_tiles) do
            local wt = water_tiles[i]
            print("  (" .. wt.x .. "," .. wt.y .. "," .. wt.z ..
                  ") flow=" .. wt.flow)
        end
    else
        print("No non-magma water found!")
    end
else
    print("No surface water found! Dwarves will need a well or muddied area.")
end

-- Check which workshop was built (the 1 workshop we saw)
print("\n--- Built Workshop Identification ---")
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop and b.flags.exists then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        print("  Workshop: " .. name .. " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ")")
    end
end

print("\n=== WATER SEARCH COMPLETE ===")
