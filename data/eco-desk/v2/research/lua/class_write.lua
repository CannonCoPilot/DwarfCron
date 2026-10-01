-- Write CREATURE_CLASS:{CLS} on every caste of {P} (the raw-level token, distinct from GOBBLE_VERMIN_CLASS which
-- reads a predator's caste looking for this value on the prey -- see gobble_write.lua). Originals saved in _G for
-- class_restore.lua. Same insert-vector recipe as gobble_write.lua, targeting ca.creature_class instead.
local S = rawget(_G, '__eco_class') or {}
rawset(_G, '__eco_class', S)
local n = 0
for _, c in ipairs(df.global.world.raws.creatures.all) do
  if c.creature_id == '{P}' then
    for ci, ca in ipairs(c.caste) do
      local key = '{P}:' .. ci
      if not S[key] then
        local cls = {}
        for _, s in ipairs(ca.creature_class) do cls[#cls + 1] = s.value end
        S[key] = cls
      end
      ca.creature_class:insert('#', { new = true, value = '{CLS}' })
      n = n + 1
    end
  end
end
print(('eco class token={P} value={CLS} castes=%d'):format(n))
