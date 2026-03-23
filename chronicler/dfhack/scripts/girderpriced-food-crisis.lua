-- girderpriced-food-crisis.lua — Resolve the food/drink crisis

print("=== FOOD CRISIS RESOLUTION ===")

-- Check buildings
print("\n--- Buildings ---")
for _, b in ipairs(df.global.world.buildings.all) do
    local btype = tostring(b:getType())
    local name = "?"
    pcall(function()
        if b:getType() == df.building_type.Workshop then
            name = tostring(df.workshop_type[b:getSubtype()])
        elseif b:getType() == df.building_type.Furnace then
            name = tostring(df.furnace_type[b:getSubtype()])
        else
            name = btype
        end
    end)
    print("  id=" .. b.id .. " type=" .. btype .. "/" .. name ..
          " pos=" .. b.centerx .. "," .. b.centery .. "," .. b.z ..
          " constructed=" .. tostring(b.flags.exists))
end

-- Check hunger/thirst of citizens
print("\n--- Citizen Health ---")
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        print("  " .. dfhack.units.getReadableName(u) ..
              " hunger=" .. u.counters2.hunger_timer ..
              " thirst=" .. u.counters2.thirst_timer ..
              " stress=" .. u.status.current_soul.personality.stress)
    end
end

-- Check what items are available for brewing
print("\n--- Brewable Items ---")
local brewable = 0
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.PLANT and not item.flags.forbid then
        brewable = brewable + 1
    end
end
print("Brewable plants: " .. brewable)

-- Check barrels and pots (needed for brewing)
local barrels = 0
local pots = 0
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.BARREL then barrels = barrels + 1 end
    if item:getType() == df.item_type.TOOL then
        -- Large pots are tools
        local desc = dfhack.items.getDescription(item, 0)
        if desc and desc:find("[Pp]ot") then pots = pots + 1 end
    end
end
print("Barrels: " .. barrels .. " Pots: " .. pots)

-- Check if the surface workshops actually exist/are built
local still_exists = false
local carpenter_exists = false
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop then
        if b:getSubtype() == df.workshop_type.Still then still_exists = true end
        if b:getSubtype() == df.workshop_type.Carpenters then carpenter_exists = true end
    end
end
print("\nStill built: " .. tostring(still_exists))
print("Carpenter built: " .. tostring(carpenter_exists))

-- If no still exists, that's the #1 problem. The surface still was DESIGNATED
-- but may not have been built because trees are blocking.
-- Let's check what's at the surface still location (103,95,134)
print("\n--- Surface Still Location (103,95,134) ---")
local bk = dfhack.maps.getTileBlock(103, 95, 134)
if bk then
    local tt = bk.tiletype[103 % 16][95 % 16]
    local shape = df.tiletype_shape[df.tiletype.attrs[tt].shape]
    local mat = df.tiletype_material[df.tiletype.attrs[tt].material]
    print("  Tile: " .. shape .. "/" .. mat)

    local bld = dfhack.buildings.findAtTile(103, 95, 134)
    if bld then
        print("  Building at tile: " .. tostring(bld:getType()))
    else
        print("  No building at tile")
    end
end

-- If workshops aren't built, we need to find a clear 3x3 area on the surface
-- and place workshops there, then manually ensure building materials are available
print("\n--- Finding clear 3x3 areas on surface ---")
local found = 0
for x = 88, 104, 4 do
    for y = 88, 104, 4 do
        local clear = true
        for dx = 0, 2 do
            for dy = 0, 2 do
                local bk = dfhack.maps.getTileBlock(x+dx, y+dy, 134)
                if bk then
                    local tt = bk.tiletype[(x+dx) % 16][(y+dy) % 16]
                    local s = df.tiletype.attrs[tt].shape
                    if s == df.tiletype_shape.WALL or s == df.tiletype_shape.TREE then
                        clear = false
                        break
                    end
                    -- Also check for existing buildings
                    if dfhack.buildings.findAtTile(x+dx, y+dy, 134) then
                        clear = false
                        break
                    end
                end
            end
            if not clear then break end
        end
        if clear then
            print("  Clear 3x3 at (" .. x .. "," .. y .. ",134)")
            found = found + 1
            if found >= 5 then break end
        end
    end
    if found >= 5 then break end
end

print("\n=== FOOD CRISIS DIAGNOSIS COMPLETE ===")
