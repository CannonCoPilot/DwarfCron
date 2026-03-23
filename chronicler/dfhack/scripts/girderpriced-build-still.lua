-- girderpriced-build-still.lua — Force-build a Still workshop

print("=== BUILDING STILL ===")

-- First, check what's at (92,88,134) — should be clear
local bld = dfhack.buildings.findAtTile(93, 89, 134)
if bld then
    print("Building already at (93,89,134): " .. tostring(bld:getType()))
else
    print("(93,89,134) is clear")
end

-- Try constructBuilding for a Still
-- workshop_type.Still = 15
local result = dfhack.buildings.constructBuilding{
    pos = xyz2pos(93, 89, 134),
    type = df.building_type.Workshop,
    subtype = df.workshop_type.Still,
    width = 3,
    height = 3,
}
if result then
    print("Still construction started! ID=" .. result.id)
else
    print("constructBuilding returned nil — trying Quickfort...")
    -- Quickfort: lower-case 's' in 'ws' should be Still
    local qf = reqscript('quickfort')
    -- Use explicit Still placement with lowercase
    qf.apply_blueprint{mode='build', data='ws', pos={x=93, y=89, z=134}}
    print("Quickfort 'ws' placed at (93,89,134)")
end

-- Also check what workshops exist now
print("\n--- All Workshops ---")
for _, b in ipairs(df.global.world.buildings.all) do
    if b:getType() == df.building_type.Workshop then
        local name = "?"
        pcall(function() name = tostring(df.workshop_type[b:getSubtype()]) end)
        print("  " .. name .. " at (" .. b.centerx .. "," .. b.centery .. "," .. b.z ..
              ") built=" .. tostring(b.flags.exists))
    end
end

-- Also place more food infrastructure now that we have 200 dug tiles
-- Check if z=132 has space for workshops
print("\n--- z=132 Status ---")
local floor_tiles = 0
for x = 84, 103 do
    for y = 84, 97 do
        local blk = dfhack.maps.getTileBlock(x, y, 132)
        if blk then
            local tt = blk.tiletype[x % 16][y % 16]
            local shape = df.tiletype.attrs[tt].shape
            if shape == df.tiletype_shape.FLOOR then
                floor_tiles = floor_tiles + 1
            end
        end
    end
end
print("z=132 floor tiles: " .. floor_tiles)

if floor_tiles >= 9 then
    -- Place underground workshops in the dug-out area
    local qf = reqscript('quickfort')
    -- Still underground (priority!)
    qf.apply_blueprint{mode='build', data='ws', pos={x=85, y=85, z=132}}
    print("Underground Still placed at (85,85,132)")
    -- Kitchen underground
    qf.apply_blueprint{mode='build', data='wk', pos={x=89, y=85, z=132}}
    print("Underground Kitchen placed at (89,85,132)")
end

print("\n=== DONE ===")
