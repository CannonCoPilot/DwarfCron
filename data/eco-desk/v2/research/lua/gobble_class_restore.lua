-- Restore the creature_class vector on {V} and the gobble_vermin_class vector + VERMIN_GOBBLER flag on {P}
-- saved by gobble_class_write.lua.
local S = rawget(_G, '__eco_gobble_class') or {}
local nV, nP = 0, 0
for _, c in ipairs(df.global.world.raws.creatures.all) do
  if c.creature_id == '{V}' then
    for ci, ca in ipairs(c.caste) do
      local o = S['V:{V}:' .. ci]
      if o then
        local vec = ca.creature_class
        for i = #vec - 1, 0, -1 do vec:erase(i) end
        for _, s in ipairs(o.cls) do vec:insert('#', { new = true, value = s }) end
        S['V:{V}:' .. ci] = nil
        nV = nV + 1
      end
    end
  elseif c.creature_id == '{P}' then
    for ci, ca in ipairs(c.caste) do
      local o = S['P:{P}:' .. ci]
      if o then
        local vec = ca.gobble_vermin_class
        for i = #vec - 1, 0, -1 do vec:erase(i) end
        for _, s in ipairs(o.cls) do vec:insert('#', { new = true, value = s }) end
        ca.flags.VERMIN_GOBBLER = o.flag
        S['P:{P}:' .. ci] = nil
        nP = nP + 1
      end
    end
  end
end
print(('eco gobble-class restored vermin={V} consumer={P} v-castes=%d p-castes=%d'):format(nV, nP))
