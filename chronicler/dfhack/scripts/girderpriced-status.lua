-- girderpriced-status.lua — Quick fortress status probe

local year = dfhack.world.ReadCurrentYear()
local tick = dfhack.world.ReadCurrentTick()
local season_names = {"Spring", "Summer", "Autumn", "Winter"}
local season = season_names[math.floor(tick / 100800) + 1] or "?"

-- Citizens
local citizens = 0
local stressed = 0
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isCitizen(u) and dfhack.units.isAlive(u) then
        citizens = citizens + 1
        if u.status.current_soul and u.status.current_soul.personality.stress > 50000 then
            stressed = stressed + 1
        end
    end
end

-- Buildings
local bcount = 0
local workshops = 0
for _, b in ipairs(df.global.world.buildings.all) do
    bcount = bcount + 1
    if b:getType() == df.building_type.Workshop or b:getType() == df.building_type.Furnace then
        workshops = workshops + 1
    end
end

-- Food / Drink — count using stack sizes to match in-game totals
local food, drink, plants, seeds = 0, 0, 0, 0
for _, item in ipairs(df.global.world.items.all) do
    if not item.flags.forbid and not item.flags.dump and not item.flags.trader
       and not item.flags.removed and not item.flags.garbage_collect then
        local t = item:getType()
        local qty = item.stack_size or 1
        -- Edible items (all count towards the kitchen's "Food" counter)
        if t == df.item_type.FOOD then food = food + qty       -- prepared meals
        elseif t == df.item_type.FISH then food = food + qty
        elseif t == df.item_type.FISH_RAW then food = food + qty
        elseif t == df.item_type.MEAT then food = food + qty
        elseif t == df.item_type.CHEESE then food = food + qty
        elseif t == df.item_type.EGG then food = food + qty
        elseif t == df.item_type.PLANT then
            plants = plants + qty
            food = food + qty
        elseif t == df.item_type.LEAVES then food = food + qty
        elseif t == df.item_type.PLANT_GROWTH then food = food + qty
        -- Drink (use stack_size for actual servings)
        elseif t == df.item_type.DRINK then drink = drink + qty
        -- Seeds
        elseif t == df.item_type.SEEDS then seeds = seeds + qty
        end
    end
end

-- Squads
local fort_id = df.global.plotinfo.group_id
local squads = 0
for _, sq in ipairs(df.global.world.squads.all) do
    if sq.entity_id == fort_id then squads = squads + 1 end
end

print("STATUS Y" .. year .. " T" .. tick .. " " .. season)
print("citizens=" .. citizens .. " stressed=" .. stressed)
print("buildings=" .. bcount .. " workshops=" .. workshops)
print("food=" .. food .. " drink=" .. drink .. " plants=" .. plants .. " seeds=" .. seeds)
print("squads=" .. squads)
print("paused=" .. tostring(df.global.pause_state))

-- Check digging progress
local dug = 0
for z = 130, 133 do
    for x = 84, 103 do
        for y = 84, 105 do
            local blk = dfhack.maps.getTileBlock(x, y, z)
            if blk then
                local tt = blk.tiletype[x % 16][y % 16]
                local shape = df.tiletype.attrs[tt].shape
                if shape == df.tiletype_shape.FLOOR or shape == df.tiletype_shape.STAIR_DOWN
                   or shape == df.tiletype_shape.STAIR_UP or shape == df.tiletype_shape.STAIR_UPDOWN then
                    dug = dug + 1
                end
            end
        end
    end
end
print("dug_tiles=" .. dug)
