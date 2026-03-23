-- girderpriced-setup.lua — Phase 1 fortress construction for Girderpriced
-- Deploys to hack/scripts/ on VM, run via: dfhack-run girderpriced-setup

local qf = reqscript('quickfort')

local function dig(data, x, y, z)
    qf.apply_blueprint{mode='dig', data=data, pos={x=x, y=y, z=z}}
    print("DIG z=" .. z .. " " .. data)
end

local function build(data, x, y, z)
    qf.apply_blueprint{mode='build', data=data, pos={x=x, y=y, z=z}}
    print("BUILD z=" .. z .. " " .. data)
end

local function place(data, x, y, z)
    qf.apply_blueprint{mode='place', data=data, pos={x=x, y=y, z=z}}
    print("PLACE z=" .. z .. " " .. data)
end

local function zone(data, x, y, z)
    qf.apply_blueprint{mode='zone', data=data, pos={x=x, y=y, z=z}}
    print("ZONE z=" .. z .. " " .. data)
end

print("=== GIRDERPRICED FORTRESS SETUP ===")
print("Wagon at 96,95,134. Surface z=134, soil z=133, stone z=132+")

-- PHASE 1: Stairwell (3x3 down-stairs from surface to z=130)
print("\n--- Phase 1: Stairwell ---")
for z = 134, 130, -1 do
    dig("j(3x3)", 93, 92, z)
end

-- PHASE 2: Main workshop hall at z=132 (stone layer)
print("\n--- Phase 2: Workshop Hall z=132 ---")
dig("d(20x14)", 84, 84, 132)

-- PHASE 3: Farm room at z=133 (soil layer — no need to muddy)
print("\n--- Phase 3: Farm Room z=133 (soil) ---")
dig("d(14x10)", 84, 84, 133)

-- PHASE 4: Dining hall + meeting area at z=131
print("\n--- Phase 4: Dining Hall z=131 ---")
dig("d(16x16)", 84, 84, 131)

-- PHASE 5: Bedroom corridor + rooms at z=130
print("\n--- Phase 5: Bedrooms z=130 ---")
dig("d(3x22)", 93, 84, 130)  -- main corridor
-- 7 bedrooms (3x3) branching east off corridor
for i = 0, 6 do
    dig("d(4x3)", 97, 84 + i * 3, 130)
end

-- PHASE 6: Place workshops at z=132 (all 3x3)
print("\n--- Phase 6: Workshops z=132 ---")
build("ws", 85, 85, 132)   -- Still (PRIORITY #1)
build("wc", 89, 85, 132)   -- Carpenter
build("wm", 93, 85, 132)   -- Mason
build("wk", 97, 85, 132)   -- Kitchen
build("we", 85, 89, 132)   -- Craftsdwarf
build("wf", 89, 89, 132)   -- Metalsmith Forge
build("wu", 93, 89, 132)   -- Butcher
build("wl", 97, 89, 132)   -- Leather
build("ew", 85, 93, 132)   -- Wood Furnace
build("es", 89, 93, 132)   -- Smelter

-- PHASE 7: Farm plots at z=133 (underground, soil)
print("\n--- Phase 7: Farms z=133 ---")
build("p(5x5)", 85, 85, 133)
build("p(5x5)", 91, 85, 133)
build("p(5x5)", 85, 91, 133)

-- PHASE 8: Surface stockpiles (near wagon at 96,95,134)
print("\n--- Phase 8: Surface Stockpiles ---")
place("f(5x5)", 88, 100, 134)   -- Food
place("w(5x5)", 94, 100, 134)   -- Wood
place("n(5x5)", 100, 100, 134)  -- Stone
place("u(5x5)", 88, 106, 134)   -- Furniture

-- PHASE 9: Underground stockpiles at z=132
print("\n--- Phase 9: Underground Stockpiles ---")
place("f(3x5)", 101, 85, 132)   -- Food (near workshops)
place("b(3x5)", 101, 91, 132)   -- Bars/blocks

-- PHASE 10: Meeting hall zone at z=131
print("\n--- Phase 10: Meeting Hall Zone ---")
zone("m(10x10)", 86, 86, 131)

-- PHASE 11: Trade depot on surface (5x5, needs clear path to map edge)
print("\n--- Phase 11: Trade Depot ---")
build("D", 80, 95, 134)

-- PHASE 12: Beds in bedrooms at z=130
print("\n--- Phase 12: Bedroom Furniture z=130 ---")
for i = 0, 6 do
    build("b", 98, 85 + i * 3, 130)   -- Bed
    build("x", 99, 85 + i * 3, 130)   -- Cabinet
    build("d", 100, 85 + i * 3, 130)  -- Door
end

-- PHASE 13: Dining furniture at z=131
print("\n--- Phase 13: Dining Furniture ---")
for row = 0, 3 do
    for col = 0, 3 do
        build("t", 87 + col * 3, 87 + row * 3, 131)  -- Table
        build("c", 88 + col * 3, 87 + row * 3, 131)  -- Chair
    end
end

print("\n=== SETUP COMPLETE ===")
print("Next: appoint nobles, assign crops, unpause game")
