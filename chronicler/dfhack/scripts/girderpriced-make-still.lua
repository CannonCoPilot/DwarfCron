-- girderpriced-make-still.lua — Directly construct a Still from Lua

print("=== DIRECT STILL CONSTRUCTION ===")

-- Find a wood log to use
local log = nil
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.WOOD and item.flags.on_ground
       and not item.flags.forbid then
        log = item
        break
    end
end

if not log then
    print("ERROR: No loose wood log found!")
    return
end

local lx, ly, lz = dfhack.items.getPosition(log)
print("Using log: " .. dfhack.items.getDescription(log, 0) ..
      " at (" .. lx .. "," .. ly .. "," .. lz .. ")")

-- Find a clear 3x3 area at the same z-level
local function find_clear_3x3(z)
    for x = 85, 105 do
        for y = 85, 105 do
            local clear = true
            for dx = 0, 2 do
                for dy = 0, 2 do
                    -- Check tile is floor/passable
                    local blk = dfhack.maps.getTileBlock(x+dx, y+dy, z)
                    if not blk then clear = false break end
                    local tt = blk.tiletype[(x+dx) % 16][(y+dy) % 16]
                    local shape = df.tiletype.attrs[tt].shape
                    if shape ~= df.tiletype_shape.FLOOR and
                       shape ~= df.tiletype_shape.STAIR_DOWN and
                       shape ~= df.tiletype_shape.STAIR_UPDOWN and
                       shape ~= df.tiletype_shape.RAMP then
                        clear = false
                        break
                    end
                    -- Check no building
                    if dfhack.buildings.findAtTile(x+dx, y+dy, z) then
                        clear = false
                        break
                    end
                end
                if not clear then break end
            end
            if clear then
                return x, y
            end
        end
    end
    return nil, nil
end

-- Try the log's z-level first, then surface
local cx, cy
for _, z in ipairs({lz, 134, 133}) do
    cx, cy = find_clear_3x3(z)
    if cx then
        print("Found clear 3x3 at (" .. cx .. "," .. cy .. "," .. z .. ")")
        -- Move log to the build site
        dfhack.items.moveToGround(log, xyz2pos(cx+1, cy+1, z))
        print("Moved log to center of build site")

        -- Build the Still
        local still = dfhack.buildings.constructBuilding{
            pos = xyz2pos(cx+1, cy+1, z),
            type = df.building_type.Workshop,
            subtype = df.workshop_type.Still,
            width = 3,
            height = 3,
            items = {log},
        }
        if still then
            print("STILL BUILT! ID=" .. still.id)
            still.flags.exists = true
        else
            print("constructBuilding returned nil (materials may be insufficient)")
            -- Try without items parameter
            still = dfhack.buildings.constructBuilding{
                pos = xyz2pos(cx+1, cy+1, z),
                type = df.building_type.Workshop,
                subtype = df.workshop_type.Still,
            }
            if still then
                print("STILL BUILT (no items)! ID=" .. still.id)
            else
                print("Still FAILED even without items")
            end
        end
        break
    end
end

if not cx then
    print("ERROR: No clear 3x3 found at any z-level!")
end

-- Show all workshops
print("\n--- All workshops ---")
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        print("  " .. name .. " id=" .. b.id ..
              " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z ..
              ") built=" .. tostring(b.flags.exists))
    end
end

print("\n=== DONE ===")
