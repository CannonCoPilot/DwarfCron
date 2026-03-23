-- girderpriced-woodwork.lua — Use wood to build workshops

print("=== WOODWORKING SOLUTION ===")

-- Count available wood logs
local logs = 0
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.WOOD and not item.flags.forbid
       and not item.flags.dump and not item.flags.trader then
        logs = logs + 1
    end
end
print("Available wood logs: " .. logs)

-- Enable woodcutting on someone
local cutters = 0
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        if u.status.labors[df.unit_labor.CUTWOOD] then
            cutters = cutters + 1
        end
    end
end
print("Active woodcutters: " .. cutters)

-- Enable autochop and ensure someone can cut
dfhack.run_command("enable", "autochop")
print("autochop enabled")

-- Check for axes (woodcutters need battle axe or great axe)
local axes = 0
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.WEAPON then
        local desc = dfhack.items.getDescription(item, 0)
        if desc and desc:find("[Aa]xe") then
            axes = axes + 1
        end
    end
end
print("Axes found: " .. axes)

-- If we have logs but Still isn't built, the buildingplan should use them
-- The issue is the Quickfort 'ws' code mapping to Siege instead of Still
-- Let me try explicit build with different Quickfort codes

local qf = reqscript('quickfort')

-- Try direct placement using single-char codes from verified reference
-- ws = Still is correct per the reference doc
-- The Siege workshop that got built was probably from a different placement

-- Let me remove ALL planned (unbuilt) workshops first
local removed = 0
for i = #df.global.world.buildings.all - 1, 0, -1 do
    local b = df.global.world.buildings.all[i]
    if b:getType() == df.building_type.Workshop and not b.flags.exists then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        print("Removing planned: " .. name .. " at (" ..
              b.centerx .. "," .. b.centery .. "," .. b.z .. ")")
        dfhack.buildings.deconstruct(b)
        removed = removed + 1
    end
end
print("Removed " .. removed .. " planned workshops")

-- Now place a Still on the surface where Carpenter is (near 96,88)
-- Use a location we KNOW is clear
-- Place at (92,96,134) — verified clear earlier
qf.apply_blueprint{mode='build', data='ws', pos={x=92, y=96, z=134}}

-- Verify what type was created
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop and not b.flags.exists then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        print("JUST CREATED: " .. name .. " subtype=" .. b:getSubtype() ..
              " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ")")

        -- If it's wrong type (Siege = 9), change it to Still (15)
        if b:getSubtype() ~= df.workshop_type.Still then
            print("  WRONG TYPE! Attempting to change to Still...")
            -- Direct struct modification
            b.type = df.workshop_type.Still
            print("  Set type to: " .. tostring(df.workshop_type[b:getSubtype()]))
        end
    end
end

print("\n=== DONE ===")
