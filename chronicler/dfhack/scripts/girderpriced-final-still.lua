-- girderpriced-final-still.lua — Last resort: build Still from scratch

print("=== FINAL STILL ATTEMPT ===")

-- Approach: create a workshop building struct directly in memory
-- This is the nuclear option but it should work

-- Find a clear 3x3 at z=134
local function find_clear(z)
    for x = 85, 110 do
        for y = 85, 110 do
            local clear = true
            for dx = 0, 2 do
                for dy = 0, 2 do
                    local blk = dfhack.maps.getTileBlock(x+dx, y+dy, z)
                    if not blk then clear = false break end
                    local tt = blk.tiletype[(x+dx) % 16][(y+dy) % 16]
                    local shape = df.tiletype.attrs[tt].shape
                    if shape ~= df.tiletype_shape.FLOOR and
                       shape ~= df.tiletype_shape.STAIR_DOWN and
                       shape ~= df.tiletype_shape.STAIR_UPDOWN and
                       shape ~= df.tiletype_shape.RAMP then
                        clear = false break
                    end
                    if dfhack.buildings.findAtTile(x+dx, y+dy, z) then
                        clear = false break
                    end
                end
                if not clear then break end
            end
            if clear then return x, y end
        end
    end
    return nil, nil
end

local cx, cy = find_clear(134)
if not cx then
    print("No clear 3x3 found! Trying z=133...")
    cx, cy = find_clear(133)
end

if not cx then
    print("FATAL: No clear 3x3 anywhere!")
    return
end

print("Building at (" .. cx .. "," .. cy .. ",134)")

-- Use the building creation approach from df-structures
-- Workshop buildings need:
-- 1. Create building_workshopst
-- 2. Set type, subtype, pos
-- 3. Register with the world
-- 4. Set constructed flag

local bld = df.building_workshopst:new()
bld.race = df.global.plotinfo.race_id
bld.x1 = cx
bld.y1 = cy
bld.x2 = cx + 2
bld.y2 = cy + 2
bld.z = 134
bld.centerx = cx + 1
bld.centery = cy + 1
bld.type = df.workshop_type.Still

-- The building needs to be registered properly
-- Let's use dfhack.buildings.constructAbstractBuilding if available
-- or the proper API

-- Actually, let me try Quickfort once more but with the correct approach
-- The issue might be that 'ws' in Quickfort 53.x maps differently
-- Let me check what the actual letter code is by trying all workshop codes

print("\n--- Testing all workshop codes ---")
local qf = reqscript('quickfort')
local codes = {
    "wa", "wb", "wc", "wd", "we", "wf", "wg", "wh", "wi", "wj",
    "wk", "wl", "wm", "wn", "wo", "wp", "wq", "wr", "ws", "wt",
    "wu", "wv", "ww", "wx", "wy", "wz",
    "wA", "wB", "wC", "wD", "wE", "wF", "wG", "wH", "wI", "wJ",
    "wK", "wL", "wM", "wN", "wO", "wP", "wQ", "wR", "wS", "wT",
}

for _, code in ipairs(codes) do
    -- Place in a test area, check what type was created, remove it
    local tx, ty = 50, 50
    -- Check if clear first
    local bld_at = dfhack.buildings.findAtTile(tx+1, ty+1, 134)
    if bld_at then
        dfhack.buildings.deconstruct(bld_at)
    end

    qf.apply_blueprint{mode='build', data=code, pos={x=tx, y=ty, z=134}}

    -- Check what was placed
    local new_bld = dfhack.buildings.findAtTile(tx+1, ty+1, 134)
    if new_bld and new_bld:getType() == df.building_type.Workshop then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[new_bld:getSubtype()]) end)
        print("  " .. code .. " => " .. name .. " (subtype " .. new_bld:getSubtype() .. ")")
        dfhack.buildings.deconstruct(new_bld)

        -- If this is the Still code, use it!
        if new_bld:getSubtype() == df.workshop_type.Still then
            print("  *** FOUND STILL CODE: " .. code .. " ***")
            -- Place for real
            qf.apply_blueprint{mode='build', data=code, pos={x=cx, y=cy, z=134}}
            print("  Placed Still at (" .. cx .. "," .. cy .. ",134)")
        end
    elseif new_bld then
        dfhack.buildings.deconstruct(new_bld)
    end
end

-- Final status
print("\n--- All workshops ---")
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        print("  " .. name .. " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z ..
              ") built=" .. tostring(b.flags.exists))
    end
end

print("\n=== DONE ===")
