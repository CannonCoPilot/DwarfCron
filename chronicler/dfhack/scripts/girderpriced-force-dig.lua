-- girderpriced-force-dig.lua — Force dig designations and verify

print("=== FORCE DIG ===")

-- Force-designate the old stairwell at (93,92) z=133 and z=132
-- z=134 is already STAIR_DOWN (dug)

-- z=133: needs to be dug as a DownStair
local b133 = dfhack.maps.getTileBlock(93, 92, 133)
local d133 = b133.designation[93 % 16][92 % 16]
d133.dig = df.tile_dig_designation.DownStair
b133.flags.designated = true
print("z=133 center: designated DownStair")

-- 3x3 landing at z=133
local count133 = 0
for dx = -1, 1 do
    for dy = -1, 1 do
        if dx ~= 0 or dy ~= 0 then
            local bk = dfhack.maps.getTileBlock(93 + dx, 92 + dy, 133)
            if bk then
                local d = bk.designation[(93 + dx) % 16][(92 + dy) % 16]
                local t = bk.tiletype[(93 + dx) % 16][(92 + dy) % 16]
                local s = df.tiletype.attrs[t].shape
                if s == df.tiletype_shape.WALL then
                    d.dig = df.tile_dig_designation.Default
                    bk.flags.designated = true
                    count133 = count133 + 1
                end
            end
        end
    end
end
print("z=133 landing: " .. count133 .. " tiles designated")

-- Verify the designation stuck
local verify = b133.designation[93 % 16][92 % 16]
print("z=133 verify: dig=" .. tostring(verify.dig) .. " hidden=" .. tostring(verify.hidden))

-- Check if the down-stair at z=134 provides access to z=133
-- In DF, STAIR_DOWN at z=134 means you can walk down to z=133
-- But z=133 must be passable (FLOOR/STAIR) to actually stand on
-- Since z=133 is WALL, the miner should be able to dig it from z=134

-- Also try placing an up-stair at z=133 (center) and a landing
-- Actually, the issue might be that we need an UP_STAIR or UP_DOWN_STAIR
-- at z=133 to connect to the DOWN_STAIR at z=134

-- Let me designate it as UpDownStair instead
d133.dig = df.tile_dig_designation.UpDownStair
b133.flags.designated = true
print("z=133 center: changed to UpDownStair designation")

-- Also try the DFHack dig command directly
-- This should force-designate using the game's own logic
local qf = reqscript('quickfort')
qf.apply_blueprint{mode='dig', data='i', pos={x=93, y=92, z=133}}
print("Quickfort: designated i (up/down stair) at (93,92,133)")

-- And 3x3 mine-out around it
qf.apply_blueprint{mode='dig', data='d(3x3)', pos={x=92, y=91, z=133}}
print("Quickfort: 3x3 mine-out at z=133")

-- For z=132, designate stairs too
qf.apply_blueprint{mode='dig', data='i', pos={x=93, y=92, z=132}}
qf.apply_blueprint{mode='dig', data='d(5x5)', pos={x=91, y=90, z=132}}
print("Quickfort: stairs + 5x5 room at z=132")

-- z=131
qf.apply_blueprint{mode='dig', data='i', pos={x=93, y=92, z=131}}
print("Quickfort: stairs at z=131")

-- Now verify accessible digs
local accessible = 0
local hidden = 0
for z = 130, 134 do
    for x = 88, 98 do
        for y = 88, 96 do
            local bk = dfhack.maps.getTileBlock(x, y, z)
            if bk then
                local d = bk.designation[x % 16][y % 16]
                if d.dig ~= df.tile_dig_designation.No then
                    if d.hidden then hidden = hidden + 1
                    else accessible = accessible + 1 end
                end
            end
        end
    end
end
print("Stairwell area: " .. accessible .. " accessible, " .. hidden .. " hidden")

-- Force miners to equip picks by cancelling their current jobs
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        if u.status.labors[df.unit_labor.MINE] then
            if u.job.current_job then
                -- Cancel current job
                local job = u.job.current_job
                print("Cancelling " .. dfhack.units.getReadableName(u) ..
                      " job: " .. tostring(df.job_type[job.job_type]))
                dfhack.job.removeJob(job)
            end
        end
    end
end

print("\n=== FORCE DIG COMPLETE ===")
