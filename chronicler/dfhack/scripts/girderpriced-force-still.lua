-- girderpriced-force-still.lua — Debug Quickfort code 'ws' and force a Still

print("=== FORCE STILL BUILD ===")

-- Check what workshop_type.Still actually is
print("workshop_type.Still = " .. tostring(df.workshop_type.Still))
print("workshop_type.Siege = " .. tostring(df.workshop_type.Siege))

-- List all workshop types
for i = 0, 25 do
    local ok, name = pcall(function() return tostring(df.workshop_type[i]) end)
    if ok and name then
        print("  " .. i .. " = " .. name)
    end
end

-- Now let's try building a Still using Quickfort with the actual letter
-- In DFHack Quickfort source, the codes are:
-- ws = Still (lowercase s)  -- but we got Siege. Let me check...
-- Actually, checking: the issue might be that 's' maps to Siege in this version
-- Let's try specific codes
print("\n--- Testing Quickfort codes ---")
local qf = reqscript('quickfort')

-- Try 'wl' for Still (maybe the code shifted?)
-- Actually, let me just use constructBuilding with explicit type
-- Find a stone boulder on the ground for material
local stone = nil
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.BOULDER and item.flags.on_ground then
        local ix, iy, iz = dfhack.items.getPosition(item)
        if iz == 134 then
            stone = item
            break
        end
    end
end

if stone then
    print("Found stone: " .. dfhack.items.getDescription(stone, 0))
    local sx, sy, sz = dfhack.items.getPosition(stone)
    print("  at (" .. sx .. "," .. sy .. "," .. sz .. ")")
else
    print("No stone on surface!")
end

-- Try using the buildingplan-placed workshop by converting it
-- Actually, the simplest approach: use 'gui/build' concept
-- But we can't use GUI remotely. Let's try the 'build' command
-- or direct struct manipulation

-- Find any planned (not built) workshops and check their subtype
print("\n--- Planned workshops ---")
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop and not b.flags.exists then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        print("  PLANNED: " .. name .. " subtype=" .. b:getSubtype() ..
              " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ")")

        -- Change it to Still if it's Siege!
        if b:getSubtype() == df.workshop_type.Siege then
            -- Can we change subtype? Probably not safely.
            -- Better to remove and recreate
            print("    -> This is a Siege workshop, will deconstruct")
            dfhack.buildings.deconstruct(b)
        end
    end
end

-- The Quickfort code issue might be version-specific
-- Let's try the DFHack 'build' command instead
-- Or use buildingplan's API
print("\n--- Attempting direct build ---")
-- Use the 'build' DFHack command (if available)
-- build -t Workshop -s Still -p 93,89,134
-- Actually, DFHack doesn't have a CLI 'build' command
-- Let's use constructBuilding more carefully

-- First move a boulder nearby
if stone then
    dfhack.items.moveToGround(stone, xyz2pos(93, 89, 134))
    print("Moved stone to (93,89,134)")

    -- Now try constructBuilding with the material in place
    local result = dfhack.buildings.constructBuilding{
        pos = xyz2pos(93, 89, 134),
        type = df.building_type.Workshop,
        subtype = df.workshop_type.Still,
        width = 3,
        height = 3,
        items = {stone},
    }
    if result then
        print("Still created! ID=" .. result.id)
    else
        print("constructBuilding still returned nil")
    end
end

print("\n=== DONE ===")
