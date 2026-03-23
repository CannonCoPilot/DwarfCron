-- girderpriced-industry.lua — Set up food processing industry

print("=== FOOD PROCESSING INDUSTRY ===")

local qf = reqscript('quickfort')

-- Place Fishery workshop (processes raw fish)
qf.apply_blueprint{mode='build', data='wh', pos={x=100, y=92, z=134}}
print("Fishery workshop placed at (100,92,134)")

-- Place Kitchen (cooks prepared meals from raw ingredients)
qf.apply_blueprint{mode='build', data='wk', pos={x=104, y=88, z=134}}
print("Kitchen placed at (104,88,134)")

-- Place Butcher shop (processes animals)
qf.apply_blueprint{mode='build', data='wu', pos={x=104, y=92, z=134}}
print("Butcher shop placed at (104,92,134)")

-- Check Still status again
local still_found = false
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop then
        local sub = b:getSubtype()
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[sub]) end)
        if sub == df.workshop_type.Still then
            still_found = true
            if b.flags.exists then
                print("Still BUILT at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ")")
            else
                print("Still PLANNED at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ")")
            end
        end
    end
end
if not still_found then
    -- Try another location
    qf.apply_blueprint{mode='build', data='ws', pos={x=104, y=96, z=134}}
    print("Still placed at (104,96,134) — retry location")
end

-- Enable food processing labors on relevant citizens
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        pcall(function() u.status.labors[df.unit_labor.COOK] = true end)
        pcall(function() u.status.labors[df.unit_labor.BREW] = true end)
        pcall(function() u.status.labors[df.unit_labor.FISH] = true end)
        pcall(function() u.status.labors[df.unit_labor.CLEAN_FISH] = true end)
        pcall(function() u.status.labors[df.unit_labor.DISSECT_FISH] = true end)
        pcall(function() u.status.labors[df.unit_labor.BUTCHER] = true end)
    end
end
print("Food processing labors enabled on all citizens")

-- Import furnace and smelting orders for when we get underground
dfhack.run_command("orders", "import", "library/furnace")
dfhack.run_command("orders", "import", "library/smelting")
print("Imported furnace + smelting order libraries")

print("\n=== INDUSTRY SETUP COMPLETE ===")
