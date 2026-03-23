-- girderpriced-build-workshops.lua — Build critical workshops on clear surface tiles

print("=== BUILDING CRITICAL WORKSHOPS ===")

-- Use Quickfort to place workshops on verified clear tiles
local qf = reqscript('quickfort')

-- Still at (92,88,134) — clear area confirmed
qf.apply_blueprint{mode='build', data='ws', pos={x=92, y=88, z=134}}
print("Still designated at (92,88,134)")

-- Carpenter at (96,88,134)
qf.apply_blueprint{mode='build', data='wc', pos={x=96, y=88, z=134}}
print("Carpenter designated at (96,88,134)")

-- Mason at (92,92,134)
qf.apply_blueprint{mode='build', data='wm', pos={x=92, y=92, z=134}}
print("Mason designated at (92,92,134)")

-- Kitchen at (96,92,134)
qf.apply_blueprint{mode='build', data='wk', pos={x=96, y=92, z=134}}
print("Kitchen designated at (96,92,134)")

-- Check how many construction jobs are now available
-- Enable BUILD_CONSTRUCTION on all citizens so they can build
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        pcall(function() u.status.labors[df.unit_labor.BUILD_CONSTRUCTION] = true end)
        pcall(function() u.status.labors[df.unit_labor.HAUL_ITEM] = true end)
        pcall(function() u.status.labors[df.unit_labor.HAUL_STONE] = true end)
        pcall(function() u.status.labors[df.unit_labor.HAUL_WOOD] = true end)
    end
end
print("Construction labors enabled on all citizens")

-- Also add workorders for barrels and beds (via orders command)
dfhack.run_command("workorder", '{"job":"ConstructBed","amount_total":7}')
print("Ordered: 7 beds")

dfhack.run_command("workorder", '{"job":"MakeCharcoal","amount_total":5}')
print("Ordered: 5 charcoal")

print("\n=== WORKSHOP PLACEMENT COMPLETE ===")
print("Workshops need stone/wood materials to be constructed by dwarves")
print("buildingplan plugin will queue them until materials are hauled")
