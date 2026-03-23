-- girderpriced-fix-stairs.lua — Fix the stairwell designation issue

print("=== FIX STAIRWELL ===")

-- The problem: z=133 is designated as Default (mine floor) but the miner
-- can't reach z=133 because it's solid wall. They're standing on STAIR_DOWN
-- at z=134 above. To dig downward, the z=133 tile needs to be designated
-- as a DOWN_STAIR or UP_DOWN_STAIR.

-- Check current state of ALL stairwell tiles
print("\n--- Stairwell state at (93,92) ---")
for z = 134, 130, -1 do
    local blk = dfhack.maps.getTileBlock(93, 92, z)
    if blk then
        local tt = blk.tiletype[93 % 16][92 % 16]
        local shape = df.tiletype_shape[df.tiletype.attrs[tt].shape]
        local mat = df.tiletype_material[df.tiletype.attrs[tt].material]
        local des = blk.designation[93 % 16][92 % 16]
        local dig = df.tile_dig_designation[des.dig]
        print("  z=" .. z .. ": " .. shape .. "/" .. mat .. " dig=" .. dig)
    end
end

-- FIX: Use channel designation from z=134 to break through to z=133
-- Channel from above creates a hole + ramp below — then we can designate stairs
print("\n--- Channeling z=134 tiles to reach z=133 ---")
-- Channel 3x3 at z=134 (around 94,93 - adjacent to existing stair)
-- Actually, let's channel just ONE tile at (94,92,134) to break through
-- and create a ramp at z=133 that miners can walk on
local qf = reqscript('quickfort')
qf.apply_blueprint{mode='dig', data='h', pos={x=94, y=92, z=134}}
print("Channel designated at (94,92,134) — will create ramp at z=133")

-- Also channel (93,93,134) for second access point
qf.apply_blueprint{mode='dig', data='h', pos={x=93, y=93, z=134}}
print("Channel designated at (93,93,134)")

-- Now at z=133, designate the center as up/down stair
local b133 = dfhack.maps.getTileBlock(93, 92, 133)
local d133 = b133.designation[93 % 16][92 % 16]
d133.dig = df.tile_dig_designation.UpDownStair
b133.flags.designated = true
print("z=133 (93,92): designated UpDownStair")

-- Also designate surrounding tiles at z=133 as Default (mine floor)
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
print("z=133 3x3 landing re-designated")

-- Verify accessible digs now
local access = 0
for z = 133, 134 do
    for x = 91, 95 do
        for y = 90, 94 do
            local bk = dfhack.maps.getTileBlock(x, y, z)
            if bk then
                local d = bk.designation[x % 16][y % 16]
                if d.dig ~= df.tile_dig_designation.No and not d.hidden then
                    access = access + 1
                    print("  Accessible: (" .. x .. "," .. y .. "," .. z ..
                          ") dig=" .. df.tile_dig_designation[d.dig])
                end
            end
        end
    end
end
print("Total accessible digs in stairwell area: " .. access)

print("\n=== STAIRWELL FIX COMPLETE ===")
print("Channels at z=134 will create ramps at z=133, giving miners access")
