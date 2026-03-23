-- girderpriced-dig-debug.lua — Debug why miners aren't digging

print("=== DIG DEBUG ===")

-- Check each citizen's current job and mining labor
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        local name = dfhack.units.getReadableName(u)
        local has_mine = u.status.labors[df.unit_labor.MINE]
        local job_str = "idle"
        if u.job.current_job then
            job_str = tostring(df.job_type[u.job.current_job.job_type])
        end
        print("  " .. name .. " mine=" .. tostring(has_mine) .. " job=" .. job_str ..
              " pos=" .. u.pos.x .. "," .. u.pos.y .. "," .. u.pos.z)
    end
end

-- Check if picks are available (not forbidden, not in use)
print("\n--- Picks ---")
for _, item in ipairs(df.global.world.items.all) do
    if item:getType() == df.item_type.WEAPON then
        local desc = dfhack.items.getDescription(item, 0)
        if desc and desc:find("[Pp]ick") then
            local owner = dfhack.items.getOwner(item)
            local owner_name = owner and dfhack.units.getReadableName(owner) or "none"
            local pos = "?"
            local ix, iy, iz = dfhack.items.getPosition(item)
            if ix then pos = ix .. "," .. iy .. "," .. iz end
            print("  " .. desc .. " owner=" .. owner_name ..
                  " pos=" .. pos ..
                  " forbid=" .. tostring(item.flags.forbid) ..
                  " dump=" .. tostring(item.flags.dump) ..
                  " ground=" .. tostring(item.flags.on_ground))
        end
    end
end

-- Check the stairwell tiles at new location (95,94)
print("\n--- Stairwell (95,94) ---")
for z = 134, 130, -1 do
    local blk = dfhack.maps.getTileBlock(95, 94, z)
    if blk then
        local tt = blk.tiletype[95 % 16][94 % 16]
        local shape = df.tiletype_shape[df.tiletype.attrs[tt].shape]
        local mat = df.tiletype_material[df.tiletype.attrs[tt].material]
        local des = blk.designation[95 % 16][94 % 16]
        local dig = df.tile_dig_designation[des.dig]
        print("  z=" .. z .. ": " .. shape .. "/" .. mat ..
              " dig=" .. dig .. " hidden=" .. tostring(des.hidden) ..
              " accessible=" .. tostring(not des.hidden))
    end
end

-- Also check old stairwell (93,92)
print("\n--- Old stairwell (93,92) ---")
for z = 134, 130, -1 do
    local blk = dfhack.maps.getTileBlock(93, 92, z)
    if blk then
        local tt = blk.tiletype[93 % 16][92 % 16]
        local shape = df.tiletype_shape[df.tiletype.attrs[tt].shape]
        local des = blk.designation[93 % 16][92 % 16]
        local dig = df.tile_dig_designation[des.dig]
        print("  z=" .. z .. ": " .. shape .. " dig=" .. dig .. " hidden=" .. tostring(des.hidden))
    end
end

-- Check if there are any accessible dig targets
print("\n--- Accessible dig targets ---")
local accessible_digs = 0
local hidden_digs = 0
for z = 130, 134 do
    for x = 80, 110 do
        for y = 80, 110 do
            local blk = dfhack.maps.getTileBlock(x, y, z)
            if blk then
                local des = blk.designation[x % 16][y % 16]
                if des.dig ~= df.tile_dig_designation.No then
                    if des.hidden then
                        hidden_digs = hidden_digs + 1
                    else
                        accessible_digs = accessible_digs + 1
                    end
                end
            end
        end
    end
end
print("  Accessible digs: " .. accessible_digs)
print("  Hidden digs (can't reach): " .. hidden_digs)

print("\n=== DEBUG COMPLETE ===")
