-- Restore the creature_class vector saved by class_write.lua for {P}.
local S = rawget(_G, '__eco_class') or {}
local n = 0
for _, c in ipairs(df.global.world.raws.creatures.all) do
  if c.creature_id == '{P}' then
    for ci, ca in ipairs(c.caste) do
      local o = S['{P}:' .. ci]
      if o then
        local vec = ca.creature_class
        for i = #vec - 1, 0, -1 do vec:erase(i) end
        for _, s in ipairs(o) do vec:insert('#', { new = true, value = s }) end
        S['{P}:' .. ci] = nil
        n = n + 1
      end
    end
  end
end
print(('eco class token={P} restored=%d'):format(n))
