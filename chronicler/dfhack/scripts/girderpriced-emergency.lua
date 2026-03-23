-- girderpriced-emergency.lua — Emergency food/production setup
-- Surface farms + gathering zone + herbalist labor

print("=== EMERGENCY FOOD INFRASTRUCTURE ===")

local qf = reqscript('quickfort')

-- Place surface farm plots near wagon (soil/grass at z=134)
-- These can grow surface crops immediately
qf.apply_blueprint{mode='build', data='p(5x5)', pos={x=84, y=95, z=134}}
qf.apply_blueprint{mode='build', data='p(5x5)', pos={x=84, y=101, z=134}}
print("Surface farm plots placed")

-- Create gathering zone (large area around embark for herbalism)
qf.apply_blueprint{mode='zone', data='g(30x30)', pos={x=81, y=81, z=134}}
print("Gathering zone placed")

-- Set crop for surface farms
-- Find wheat (surface crop, all seasons)
local wheat_id = -1
for i, p in ipairs(df.global.world.raws.plants.all) do
    if p.id == "SINGLE-GRAIN_WHEAT" then
        wheat_id = i
        break
    end
end

-- Find strawberry
local straw_id = -1
for i, p in ipairs(df.global.world.raws.plants.all) do
    if p.id == "STRAWBERRY" then
        straw_id = i
        break
    end
end

print("Wheat index: " .. wheat_id)
print("Strawberry index: " .. straw_id)

-- Assign crops to surface farms
local farms = 0
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.FarmPlot then
        if farms == 0 and wheat_id >= 0 then
            for s = 0, 3 do b.plant_id[s] = wheat_id end
            print("Farm " .. b.id .. ": Wheat (all seasons)")
        elseif farms == 1 and straw_id >= 0 then
            for s = 0, 3 do b.plant_id[s] = straw_id end
            print("Farm " .. b.id .. ": Strawberry (all seasons)")
        end
        farms = farms + 1
    end
end
print("Surface farms configured: " .. farms)

-- Enable farming and food labors on all citizens
local set = 0
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        -- Use pcall to safely try each labor (names may vary by version)
        pcall(function() u.status.labors[df.unit_labor.PLANT] = true end)
        pcall(function() u.status.labors[df.unit_labor.COOK] = true end)
        pcall(function() u.status.labors[df.unit_labor.BREW] = true end)
        pcall(function() u.status.labors[df.unit_labor.HAUL_FOOD] = true end)
        pcall(function() u.status.labors[df.unit_labor.HAUL_ITEM] = true end)
        set = set + 1
    end
end
print("Food labors enabled on " .. set .. " citizens")

-- Ensure at least 2 miners (need picks)
local miners = 0
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        if u.status.labors[df.unit_labor.MINE] then
            miners = miners + 1
        end
    end
end
if miners < 2 then
    for _, u in ipairs(df.global.world.units.active) do
        if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) and
           not u.status.labors[df.unit_labor.MINE] then
            u.status.labors[df.unit_labor.MINE] = true
            miners = miners + 1
            print("Added miner: " .. dfhack.units.getReadableName(u))
            if miners >= 3 then break end
        end
    end
end
print("Active miners: " .. miners)

-- Place a Still on the surface as emergency (near wagon)
qf.apply_blueprint{mode='build', data='ws', pos={x=103, y=95, z=134}}
print("Emergency surface Still placed")

-- Place a Craftsdwarf workshop on surface for trade goods later
qf.apply_blueprint{mode='build', data='we', pos={x=103, y=99, z=134}}
print("Surface Craftsdwarf workshop placed")

-- Place a Carpenter on surface for barrels/beds
qf.apply_blueprint{mode='build', data='wc', pos={x=103, y=103, z=134}}
print("Surface Carpenter workshop placed")

print("=== EMERGENCY SETUP COMPLETE ===")
