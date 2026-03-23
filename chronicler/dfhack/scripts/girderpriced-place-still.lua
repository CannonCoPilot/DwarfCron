-- girderpriced-place-still.lua — Place Still with correct code 'wl'

local qf = reqscript('quickfort')

-- Still at clear spot (86,91,134)
qf.apply_blueprint{mode='build', data='wl', pos={x=86, y=91, z=134}}
print("Still (wl) placed at (86,91,134)")

-- Kitchen — need to find the code. Testing remaining codes:
-- wp, wq, wr, wt, wu, wv, ww
for _, code in ipairs({"wp", "wq", "wr", "wt", "wu", "wv", "ww"}) do
    qf.apply_blueprint{mode='build', data=code, pos={x=50, y=54, z=134}}
    local bld = dfhack.buildings.findAtTile(51, 55, 134)
    if bld and bld:getType() == df.building_type.Workshop then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[bld:getSubtype()]) end)
        print("  " .. code .. " => " .. name)
        dfhack.buildings.deconstruct(bld)
        if bld:getSubtype() == df.workshop_type.Kitchen then
            -- Found Kitchen code — place it for real
            qf.apply_blueprint{mode='build', data=code, pos={x=86, y=95, z=134}}
            print("  Kitchen placed at (86,95,134)")
        end
    elseif bld then
        dfhack.buildings.deconstruct(bld)
    end
end

-- Verify workshops
print("\n--- Workshops ---")
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        print("  " .. name .. " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z ..
              ") built=" .. tostring(b.flags.exists))
    end
end
