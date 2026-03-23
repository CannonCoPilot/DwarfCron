-- girderpriced-nobles.lua — Appoint nobles and assign crops

print("=== NOBLE APPOINTMENTS ===")

local site_gov = df.global.plotinfo.main.fortress_entity
local citizens = {}
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        table.insert(citizens, u)
    end
end
print("Citizens: " .. #citizens)

-- Appoint nobles: Manager, Bookkeeper, Broker, Chief Medical Dwarf
local ROLES = {"MANAGER", "BOOKKEEPER", "BROKER", "CHIEF_MEDICAL_DWARF"}
local appointed = 0

for _, role in ipairs(ROLES) do
    for _, a in ipairs(site_gov.positions.assignments) do
        if a.histfig >= 0 then goto next_assign end  -- already filled
        for _, p in ipairs(site_gov.positions.own) do
            if p.id == a.position_id and p.code == role then
                -- Find an unappointed citizen
                for _, u in ipairs(citizens) do
                    -- Check if this citizen already holds a position
                    local already = false
                    for _, a2 in ipairs(site_gov.positions.assignments) do
                        if a2.histfig == u.hist_figure_id then
                            already = true
                            break
                        end
                    end
                    if not already then
                        a.histfig = u.hist_figure_id
                        print("  " .. role .. " => " .. dfhack.units.getReadableName(u))
                        appointed = appointed + 1
                        goto next_role
                    end
                end
            end
        end
        ::next_assign::
    end
    ::next_role::
end
print("Appointed: " .. appointed .. " nobles")

-- Assign crops to farm plots (plump helmets for all seasons underground)
print("\n=== CROP ASSIGNMENT ===")
local plump_id = -1
for i, p in ipairs(df.global.world.raws.plants.all) do
    if p.id == "MUSHROOM_HELMET_PLUMP" then
        plump_id = i
        break
    end
end
print("Plump Helmet plant index: " .. plump_id)

-- Also find sweet pod (good for brewing)
local sweet_id = -1
for i, p in ipairs(df.global.world.raws.plants.all) do
    if p.id == "POD_SWEET" then
        sweet_id = i
        break
    end
end
print("Sweet Pod plant index: " .. sweet_id)

-- Find pig tail (thread for cloth)
local pigtail_id = -1
for i, p in ipairs(df.global.world.raws.plants.all) do
    if p.id == "GRASS_TAIL_PIG" then
        pigtail_id = i
        break
    end
end
print("Pig Tail plant index: " .. pigtail_id)

local farms_set = 0
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.FarmPlot then
        if farms_set == 0 then
            -- Farm 1: plump helmets all seasons
            for s = 0, 3 do b.plant_id[s] = plump_id end
            print("Farm " .. b.id .. ": Plump Helmets (all seasons)")
        elseif farms_set == 1 then
            -- Farm 2: sweet pods spring/summer, plump helmets autumn/winter
            b.plant_id[0] = sweet_id   -- spring
            b.plant_id[1] = sweet_id   -- summer
            b.plant_id[2] = plump_id   -- autumn
            b.plant_id[3] = plump_id   -- winter
            print("Farm " .. b.id .. ": Sweet Pod Sp/Su, Plump Helmet Au/Wi")
        elseif farms_set == 2 then
            -- Farm 3: pig tail (thread)
            b.plant_id[0] = pigtail_id
            b.plant_id[1] = pigtail_id
            b.plant_id[2] = plump_id
            b.plant_id[3] = plump_id
            print("Farm " .. b.id .. ": Pig Tail Sp/Su, Plump Helmet Au/Wi")
        end
        farms_set = farms_set + 1
    end
end
print("Farm plots configured: " .. farms_set)

-- Enable autofarm
dfhack.run_command("enable", "autofarm")
print("\nautofarm enabled")

-- Enable autochop (lumber management)
dfhack.run_command("enable", "autochop")
print("autochop enabled")

-- Create a military squad for defense
print("\n=== MILITARY SETUP ===")
local fort_id = df.global.plotinfo.group_id
local mc_assign = nil
for _, a in ipairs(site_gov.positions.assignments) do
    for _, p in ipairs(site_gov.positions.own) do
        if p.id == a.position_id and p.code == "MILITIA_COMMANDER" then
            mc_assign = a
            break
        end
    end
    if mc_assign then break end
end

if mc_assign then
    -- Check if squad already exists
    local fort_squads = 0
    for _, sq in ipairs(df.global.world.squads.all) do
        if sq.entity_id == fort_id then
            fort_squads = fort_squads + 1
        end
    end

    if fort_squads == 0 then
        local squad = dfhack.military.makeSquad(mc_assign.id)
        if squad then
            squad.alias = "Stone Guard"
            print("Created squad: Stone Guard (id=" .. squad.id .. ")")

            -- Assign strongest citizen as commander
            local best = nil
            local best_tough = -1
            for _, u in ipairs(citizens) do
                local tough = u.body.physical_attrs.TOUGHNESS.value
                if tough > best_tough then
                    best = u
                    best_tough = tough
                end
            end
            if best then
                dfhack.military.addToSquad(best.id, squad.id, 0)
                print("  Commander: " .. dfhack.units.getReadableName(best))
            end
        end
    else
        print("Fort already has " .. fort_squads .. " squad(s)")
    end
else
    print("No MILITIA_COMMANDER assignment found")
end

print("\n=== NOBLES/CROPS/MILITARY COMPLETE ===")
