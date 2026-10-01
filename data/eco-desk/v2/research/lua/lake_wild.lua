-- LAKEP: every live wild unit in the lake's water layer (population.feature_idx ~= -1, cave_id == -1): its
-- population feature_idx/cave_id, the tool's WILD.layerOf, and the engine's ecoRealm recomputed by hand (ecoRealm
-- is a local in seasonal-wildlife.lua: land for both 'land' and 'water' WILD.layerOf results since v6.9.0, 'cavern:N'
-- for a cavern depth, nil for 'deep'). {TAG} placeholder.
local sw = reqscript('seasonal-wildlife')
local n = 0
for _, u in ipairs(df.global.world.units.active) do
  if dfhack.units.isWildlife(u) and not dfhack.units.isDead(u) then
    local p = u.animal.population
    if p.feature_idx ~= -1 and p.cave_id == -1 then
      local L = sw.WILD.layerOf(u)
      local realm = (L == 'land' or L == 'water') and 'land' or (L == 'cavern' and ('cavern:' .. tostring(p.cave_id)) or 'nil')
      local c = df.creature_raw.find(u.race)
      n = n + 1
      print(('eco lakewild tag={TAG} id=%d race=%s feature_idx=%d cave_id=%d layer=%s realm=%s'):format(
        u.id, c and c.creature_id or '?', p.feature_idx, p.cave_id, L, realm))
    end
  end
end
print(('eco lakewildsum tag={TAG} n=%d'):format(n))
