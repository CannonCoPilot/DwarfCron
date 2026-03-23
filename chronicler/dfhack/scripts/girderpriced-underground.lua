-- girderpriced-underground.lua — Check z=133 for dug space and place workshops there

print("=== UNDERGROUND WORKSHOP PLACEMENT ===")

-- Count floor tiles at z=133 (soil layer — this is where digging happened)
local floors = {}
for x = 84, 103 do
    for y = 84, 97 do
        local blk = dfhack.maps.getTileBlock(x, y, 133)
        if blk then
            local tt = blk.tiletype[x % 16][y % 16]
            local shape = df.tiletype.attrs[tt].shape
            if shape == df.tiletype_shape.FLOOR or
               shape == df.tiletype_shape.STAIR_DOWN or
               shape == df.tiletype_shape.STAIR_UP or
               shape == df.tiletype_shape.STAIR_UPDOWN or
               shape == df.tiletype_shape.RAMP then
                table.insert(floors, {x=x, y=y})
            end
        end
    end
end
print("z=133 floor tiles: " .. #floors)

-- Count floor tiles at z=132
local floors132 = 0
for x = 84, 103 do
    for y = 84, 97 do
        local blk = dfhack.maps.getTileBlock(x, y, 132)
        if blk then
            local tt = blk.tiletype[x % 16][y % 16]
            local shape = df.tiletype.attrs[tt].shape
            if shape == df.tiletype_shape.FLOOR then
                floors132 = floors132 + 1
            end
        end
    end
end
print("z=132 floor tiles: " .. floors132)

-- Find clear 3x3 areas at z=133 (no buildings, all floor)
print("\n--- Clear 3x3 at z=133 ---")
local clear_spots = {}
for x = 84, 100 do
    for y = 84, 94 do
        local all_floor = true
        for dx = 0, 2 do
            for dy = 0, 2 do
                local blk = dfhack.maps.getTileBlock(x+dx, y+dy, 133)
                if not blk then all_floor = false break end
                local tt = blk.tiletype[(x+dx) % 16][(y+dy) % 16]
                local shape = df.tiletype.attrs[tt].shape
                if shape ~= df.tiletype_shape.FLOOR then
                    all_floor = false
                    break
                end
                -- Also check no building
                if dfhack.buildings.findAtTile(x+dx, y+dy, 133) then
                    all_floor = false
                    break
                end
            end
            if not all_floor then break end
        end
        if all_floor then
            table.insert(clear_spots, {x=x, y=y})
        end
    end
end
print("Clear 3x3 spots at z=133: " .. #clear_spots)

-- Place workshops at z=133 if we have clear spots
if #clear_spots >= 2 then
    local qf = reqscript('quickfort')
    local spot1 = clear_spots[1]
    local spot2 = clear_spots[2]

    -- Still (most critical)
    qf.apply_blueprint{mode='build', data='ws', pos={x=spot1.x, y=spot1.y, z=133}}
    print("Still placed at (" .. spot1.x .. "," .. spot1.y .. ",133)")

    -- Kitchen
    if #clear_spots >= 3 then
        local spot3 = clear_spots[3]
        qf.apply_blueprint{mode='build', data='wk', pos={x=spot3.x, y=spot3.y, z=133}}
        print("Kitchen placed at (" .. spot3.x .. "," .. spot3.y .. ",133)")
    end

    -- Mason
    qf.apply_blueprint{mode='build', data='wm', pos={x=spot2.x, y=spot2.y, z=133}}
    print("Mason placed at (" .. spot2.x .. "," .. spot2.y .. ",133)")
else
    print("Not enough clear space at z=133 yet — need more digging")
end

-- Check boulders at z=133 (building materials)
local boulders = 0
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.BOULDER then
        local ix, iy, iz = dfhack.items.getPosition(item)
        if iz == 133 then boulders = boulders + 1 end
    end
end
print("\nBoulders at z=133: " .. boulders)

-- Enable stone hauling to bring boulders to surface
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        pcall(function() u.status.labors[df.unit_labor.HAUL_STONE] = true end)
    end
end
print("Stone hauling enabled on all citizens")

-- Re-enable autolabor now that we have 15 citizens
dfhack.run_command("enable", "autolabor")
print("autolabor RE-ENABLED (15 citizens should have enough for all jobs)")

print("\n=== UNDERGROUND PLACEMENT COMPLETE ===")
