-- sw-native-probe: for every wild unit standing in water, or of a water-pool species, print where its population came from,
-- the wave flag, the tile, the layer Seasonal Wildlife gives it and whether it is in a group. One-shot read, no writes.
local sw = reqscript('seasonal-wildlife')
local ids = {}
local okG, g = pcall(function() return sw.loadGroups() end)
if okG and g then for _, grp in ipairs(g.groups or {}) do for _, id in ipairs(grp.ids or {}) do ids[id] = grp end end end
local function ftype(r)
    if r.feature_idx == -1 then return '-' end
    local ok, t = pcall(function()
        local wd = df.global.world.world_data
        local fm = wd.feature_map[r.region_x // 16]:_displace(r.region_y // 16)
        local fi = fm.features.feature_init[r.region_x % 16][r.region_y % 16][r.feature_idx]
        return df.feature_type[fi:getType()]
    end)
    return ok and t or ('?' .. tostring(t):sub(1, 40))
end
local function regionBiome(x, y)
    local ok, t = pcall(function()
        local reg = df.global.world.world_data.region_map[x]:_displace(y)
        return df.world_region_type[df.global.world.world_data.regions[reg.region_id].type]
    end)
    return ok and t or '?'
end
print('race\tid\tsrc_region\tbiome\tfeature_idx\tfeature_type\tcave_id\twave_flag\ttile\tliquid\tdepth\tsw_layer\tgrouped')
local n = 0
for _, u in ipairs(df.global.world.units.active) do
    if dfhack.units.isActive(u) and not dfhack.units.isDead(u) and (dfhack.units.isWildlife(u)) then
        local r = u.animal.population
        local x, y, z = dfhack.units.getPosition(u)
        local des = x and dfhack.maps.getTileFlags(x, y, z)
        local tt = x and dfhack.maps.getTileType(x, y, z)
        local inwater = des and des.liquid_type == df.tile_liquid.Water and des.flow_size > 0
        local layer = '?'
        pcall(function() layer = sw.WILD and sw.WILD.layerOf(u) or (r.cave_id ~= -1 and 'cave' or (r.feature_idx ~= -1 and 'water' or 'land')) end)
        if inwater or r.feature_idx ~= -1 then
            n = n + 1
            local cr = df.creature_raw.find(u.race)
            print(table.concat({ cr and cr.creature_id or '?', u.id, r.region_x .. ',' .. r.region_y, regionBiome(r.region_x, r.region_y), r.feature_idx,
                ftype(r), r.cave_id, tostring(u.flags2.roaming_wilderness_population_source), tt and df.tiletype[tt] or '?',
                tostring(inwater), des and des.flow_size or -1, layer, ids[u.id] and ('yes:' .. (ids[u.id].layer or '?')) or 'no' }, '\t'))
        end
    end
end
print('# units listed', n)
