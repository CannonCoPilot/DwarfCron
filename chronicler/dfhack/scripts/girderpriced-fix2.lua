-- girderpriced-fix2.lua — Force mining priority + trade depot fix

print("=== PHASE 2 FIXES ===")

-- DISABLE autolabor temporarily — it's pulling miners away from critical digging
dfhack.run_command("disable", "autolabor")
print("autolabor DISABLED (miners being pulled to GatherPlants)")

-- Ensure Cerol (Miner) and Melbil (who has mining enabled) focus on mining
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        local name = dfhack.units.getReadableName(u)
        -- Set Cerol and Melbil as dedicated miners
        if name:find("Cerol") or name:find("Melbil") then
            u.status.labors[df.unit_labor.MINE] = true
            -- Disable gathering on miners so they prioritize digging
            pcall(function() u.status.labors[df.unit_labor.PLANT] = false end)
            print("  " .. name .. ": mining=ON, gathering=OFF")
        else
            -- Others: keep gathering enabled, disable mining
            u.status.labors[df.unit_labor.MINE] = false
            print("  " .. name .. ": mining=OFF (gathering duty)")
        end
    end
end

-- The z=133 at (93,92) is the critical bottleneck
-- It's designated (dig=Default) but maybe the miner can't reach it
-- Let's verify it's really accessible by checking the tile above
print("\n--- Critical tile check ---")
local blk134 = dfhack.maps.getTileBlock(93, 92, 134)
local tt134 = blk134.tiletype[93 % 16][92 % 16]
local shape134 = df.tiletype_shape[df.tiletype.attrs[tt134].shape]
print("z=134 (93,92): " .. shape134)

local blk133 = dfhack.maps.getTileBlock(93, 92, 133)
local tt133 = blk133.tiletype[93 % 16][92 % 16]
local shape133 = df.tiletype_shape[df.tiletype.attrs[tt133].shape]
local des133 = blk133.designation[93 % 16][92 % 16]
print("z=133 (93,92): " .. shape133 .. " dig=" .. df.tile_dig_designation[des133.dig] ..
      " hidden=" .. tostring(des133.hidden))

-- If z=134 is STAIR_DOWN and z=133 is WALL with dig=Default, the miner should be able
-- to stand on the stair at z=134 and dig the z=133 tile below.
-- BUT: they need to dig a down-stair at z=133, not just mine. Let me re-designate.
-- Change z=133 designation to DownStair explicitly
des133.dig = df.tile_dig_designation.DownStair
blk133.flags.designated = true
print("z=133 (93,92): re-designated as DownStair")

-- Also do the 3x3 around it for a proper landing
for dx = -1, 1 do
    for dy = -1, 1 do
        if dx ~= 0 or dy ~= 0 then
            local bk = dfhack.maps.getTileBlock(93 + dx, 92 + dy, 133)
            if bk then
                local d = bk.designation[(93 + dx) % 16][(92 + dy) % 16]
                local t = bk.tiletype[(93 + dx) % 16][(92 + dy) % 16]
                local s = df.tiletype.attrs[t].shape
                if s == df.tiletype_shape.WALL then
                    d.dig = df.tile_dig_designation.Default
                    bk.flags.designated = true
                end
            end
        end
    end
end
print("z=133 3x3 landing around (93,92) designated")

-- Also designate z=132 stairs (same center)
local blk132 = dfhack.maps.getTileBlock(93, 92, 132)
if blk132 then
    local des132 = blk132.designation[93 % 16][92 % 16]
    des132.dig = df.tile_dig_designation.DownStair
    blk132.flags.designated = true
    print("z=132 (93,92): designated DownStair")
    -- 3x3 landing
    for dx = -1, 1 do
        for dy = -1, 1 do
            if dx ~= 0 or dy ~= 0 then
                local bk = dfhack.maps.getTileBlock(93 + dx, 92 + dy, 132)
                if bk then
                    local d = bk.designation[(93 + dx) % 16][(92 + dy) % 16]
                    d.dig = df.tile_dig_designation.Default
                    bk.flags.designated = true
                end
            end
        end
    end
    print("z=132 3x3 landing designated")
end

-- TRADE DEPOT: Place on surface with guaranteed 3-wide path to map edge
-- Surface is wide open — any surface location has clear access
-- The depot we placed at (86,94,134) should be fine on the surface
-- But let me verify trees aren't blocking the 3-wide corridor
print("\n--- Trade Depot Path Check ---")
-- Check a 3-wide north-south strip from depot to map edge (y=0)
local blocked = 0
for y = 0, 93 do
    for dx = 0, 2 do
        local bk = dfhack.maps.getTileBlock(86 + dx, y, 134)
        if bk then
            local t = bk.tiletype[(86 + dx) % 16][y % 16]
            local s = df.tiletype.attrs[t].shape
            if s == df.tiletype_shape.WALL or s == df.tiletype_shape.TREE then
                blocked = blocked + 1
            end
        end
    end
end
print("Blocked tiles in 3-wide north path: " .. blocked)
if blocked > 0 then
    print("  (Trees may block — autochop should clear them over time)")
end

-- MEETING HALL: Create on surface temporarily (will move underground once dug)
local qf = reqscript('quickfort')
qf.apply_blueprint{mode='zone', data='m(7x7)', pos={x=93, y=95, z=134}}
print("Surface meeting hall zone placed at (93,95,134)")

print("\n=== PHASE 2 FIXES COMPLETE ===")
print("Key: autolabor OFF, Cerol+Melbil on mining duty, z=133 re-designated")
print("Next: unpause and let miners dig through z=133 → z=132")
