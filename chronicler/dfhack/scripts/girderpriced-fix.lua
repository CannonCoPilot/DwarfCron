-- girderpriced-fix.lua — Fix digging issues + wagon deconstruct + trade depot

print("=== DIAGNOSTIC + FIXES ===")

-- Check picks availability
local picks = 0
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.WEAPON then
        local subtype = item:getSubtype()
        -- Pick is subtype depends on raws; check item description
        local desc = dfhack.items.getDescription(item, 0)
        if desc and desc:find("[Pp]ick") then
            picks = picks + 1
        end
    end
end
print("Picks found: " .. picks)

-- Check current designations
local pending_dig = 0
for z = 128, 134 do
    for x = 80, 110 do
        for y = 80, 110 do
            local blk = dfhack.maps.getTileBlock(x, y, z)
            if blk then
                local des = blk.designation[x % 16][y % 16]
                if des.dig ~= df.tile_dig_designation.No then
                    pending_dig = pending_dig + 1
                end
            end
        end
    end
end
print("Pending dig designations: " .. pending_dig)

-- Check tile at stairwell position (93,92,134) — is it diggable?
local function check_tile(x, y, z)
    local blk = dfhack.maps.getTileBlock(x, y, z)
    if not blk then return "no_block" end
    local tt = blk.tiletype[x % 16][y % 16]
    local shape = df.tiletype_shape[df.tiletype.attrs[tt].shape]
    local mat = df.tiletype_material[df.tiletype.attrs[tt].material]
    local des = blk.designation[x % 16][y % 16]
    local dig = df.tile_dig_designation[des.dig]
    return shape .. "/" .. mat .. " dig=" .. dig .. " hidden=" .. tostring(des.hidden)
end

print("Stairwell (93,92):")
for z = 134, 130, -1 do
    print("  z=" .. z .. ": " .. check_tile(93, 92, z))
end

-- DECONSTRUCT WAGON (user request)
print("\n--- Deconstructing Wagon ---")
local wagon_decon = 0
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Wagon then
        dfhack.buildings.deconstruct(b)
        wagon_decon = wagon_decon + 1
        print("Wagon at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ") deconstructed")
        break  -- only one wagon
    end
end
if wagon_decon == 0 then
    print("No wagon found (already deconstructed?)")
end

-- Re-designate stairwell at wagon location (96,95) which was blocked by wagon
print("\n--- Re-designating stairwell at (96,95) ---")
local qf = reqscript('quickfort')
for z = 134, 130, -1 do
    qf.apply_blueprint{mode='dig', data='j(3x3)', pos={x=95, y=94, z=z}}
    print("  Stairwell z=" .. z .. " designated")
end

-- Dig workshop room wider area at z=132
qf.apply_blueprint{mode='dig', data='d(16x12)', pos={x=88, y=88, z=132}}
print("Workshop hall re-designated at z=132")

-- Farm room at z=133 (soil)
qf.apply_blueprint{mode='dig', data='d(12x10)', pos={x=88, y=88, z=133}}
print("Farm room re-designated at z=133")

-- TRADE DEPOT (user request) — place near surface entrance
print("\n--- Trade Depot ---")
qf.apply_blueprint{mode='build', data='D', pos={x=86, y=94, z=134}}
print("Trade Depot designated at (86,94,134)")

-- BROKER already appointed (Lorbam). Verify:
local site_gov = df.global.plotinfo.main.fortress_entity
for _, a in ipairs(site_gov.positions.assignments) do
    for _, p in ipairs(site_gov.positions.own) do
        if p.id == a.position_id and p.code == "BROKER" and a.histfig >= 0 then
            -- Find the HF name
            for _, u in ipairs(df.global.world.units.active) do
                if u.hist_figure_id == a.histfig then
                    print("Broker: " .. dfhack.units.getReadableName(u))
                end
            end
        end
    end
end

-- Ensure all citizens have HAUL_STONE enabled for construction
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        pcall(function() u.status.labors[df.unit_labor.HAUL_STONE] = true end)
        pcall(function() u.status.labors[df.unit_labor.HAUL_WOOD] = true end)
        pcall(function() u.status.labors[df.unit_labor.BUILD_CONSTRUCTION] = true end)
        pcall(function() u.status.labors[df.unit_labor.CARPENTER] = true end)
        pcall(function() u.status.labors[df.unit_labor.MASON] = true end)
    end
end
print("Construction labors enabled on all citizens")

print("\n=== FIXES COMPLETE ===")
