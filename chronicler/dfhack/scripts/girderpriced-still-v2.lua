-- girderpriced-still-v2.lua — Build Still using Quickfort CSV blueprint file

print("=== STILL v2 — CSV BLUEPRINT ===")

-- Write a CSV blueprint file for a Still
local csv = [[#build
ws
]]

-- Write to a temp file in DF directory
local f = io.open("still-blueprint.csv", "w")
f:write(csv)
f:close()
print("Wrote still-blueprint.csv")

-- Apply it at a known clear location
local qf = reqscript('quickfort')
local pos = {x=86, y=91, z=134}

-- First verify the spot is clear
local clear = true
for dx = 0, 2 do
    for dy = 0, 2 do
        local bld = dfhack.buildings.findAtTile(pos.x + dx, pos.y + dy, pos.z)
        if bld then
            print("  BLOCKED at (" .. (pos.x+dx) .. "," .. (pos.y+dy) .. ") by building " .. bld.id)
            clear = false
        end
        local blk = dfhack.maps.getTileBlock(pos.x + dx, pos.y + dy, pos.z)
        if blk then
            local tt = blk.tiletype[(pos.x+dx) % 16][(pos.y+dy) % 16]
            local shape = df.tiletype.attrs[tt].shape
            if shape == df.tiletype_shape.WALL or shape == df.tiletype_shape.TREE then
                print("  BLOCKED at (" .. (pos.x+dx) .. "," .. (pos.y+dy) .. ") by " ..
                      df.tiletype_shape[shape])
                clear = false
            end
        end
    end
end

if not clear then
    print("Location blocked! Trying alternate...")
    pos = {x=88, y=96, z=134}
end

-- Apply the CSV blueprint
qf.apply_blueprint{mode='build', file='still-blueprint.csv', pos=pos}
print("Applied CSV blueprint at (" .. pos.x .. "," .. pos.y .. "," .. pos.z .. ")")

-- Check what was created
print("\n--- Check results ---")
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        local status = b.flags.exists and "BUILT" or "PLANNED"
        print("  " .. status .. ": " .. name .. " id=" .. b.id ..
              " subtype=" .. b:getSubtype() ..
              " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z .. ")")
    end
end

print("\n=== DONE ===")
