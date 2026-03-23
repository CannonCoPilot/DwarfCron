-- girderpriced-brew.lua — Emergency brewing setup

print("=== EMERGENCY BREWING ===")

-- Enable brewing-related labors on ALL citizens (use pcall for unknown names)
local brew_count = 0
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        -- Try various possible labor names for brewing
        for _, labor_name in ipairs({"BREW", "BREWER", "COOK", "PLANT", "HAUL_FOOD", "HAUL_ITEM"}) do
            pcall(function() u.status.labors[df.unit_labor[labor_name]] = true end)
        end
        brew_count = brew_count + 1
    end
end
print("Brewing labors enabled on " .. brew_count .. " citizens")

-- List all available labors to find the right name
print("\n--- Available labors (searching for brew) ---")
for i = 0, 100 do
    local ok, name = pcall(function() return tostring(df.unit_labor[i]) end)
    if ok and name and name:lower():find("brew") then
        print("  " .. i .. " = " .. name)
    end
end

-- Check barrels and containers
local barrels, pots, buckets = 0, 0, 0
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.BARREL then
        barrels = barrels + 1
    elseif item:getType() == df.item_type.BUCKET then
        buckets = buckets + 1
    end
end
print("Barrels: " .. barrels .. " Buckets: " .. buckets)

-- Check manager orders for brewing
print("\n--- Manager Orders ---")
local orders = df.global.world.manager_orders.all
print("Total orders: " .. #orders)
for _, o in ipairs(orders) do
    local jname = "?"
    pcall(function() jname = tostring(df.job_type[o.job_type]) end)
    if jname:find("[Bb]rew") or jname:find("[Cc]ook") or jname:find("[Pp]repare") then
        print("  " .. jname .. " amount=" .. o.amount_total .. " freq=" .. o.frequency)
    end
end

-- Check if Still has jobs queued
print("\n--- Still Status ---")
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop and
       b:getSubtype() == df.workshop_type.Still and b.flags.exists then
        print("Still id=" .. b.id .. " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ")")
        -- Check jobs at this building
        local jobs = b.jobs
        print("  Jobs: " .. #jobs)
        for _, j in ipairs(jobs) do
            local jt = "?"
            pcall(function() jt = tostring(df.job_type[j.job_type]) end)
            print("    " .. jt)
        end
    end
end

-- Manually order brewing
dfhack.run_command("workorder", '{"job":"CustomReaction","reaction":"BREW_DRINK_FROM_PLANT_DRINK","amount_total":10}')
print("\nOrdered: 10x CustomReaction BREW_DRINK_FROM_PLANT_DRINK")

-- Also try direct workorder
dfhack.run_command("workorder", '{"job":"CustomReaction","reaction":"BREW_DRINK_FROM_PLANT","amount_total":10}')
print("Ordered: 10x CustomReaction BREW_DRINK_FROM_PLANT")

-- Check available plants for brewing (need to not be in a container)
local loose_plants = 0
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.PLANT and item.flags.on_ground
       and not item.flags.forbid then
        loose_plants = loose_plants + 1
    end
end
print("\nLoose plants on ground: " .. loose_plants)

-- Who's dead?
print("\n--- Dead Citizens ---")
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and not dfhack.units.isAlive(u) then
        local cause = "?"
        if u.counters.death_cause >= 0 then
            pcall(function() cause = tostring(df.death_type[u.counters.death_cause]) end)
        end
        print("  DEAD: " .. dfhack.units.getReadableName(u) .. " cause=" .. cause)
    end
end

print("\n=== BREW SETUP DONE ===")
