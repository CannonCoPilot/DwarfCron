-- Restore the gobble vectors and VERMIN_GOBBLER flag saved by gobble_write.lua for {P}.
local S = rawget(_G, '__eco_gobble') or {}
local n = 0
for _, c in ipairs(df.global.world.raws.creatures.all) do
  if c.creature_id == '{P}' then
    for ci, ca in ipairs(c.caste) do
      local o = S['{P}:' .. ci]
      if o then
        for _, f in ipairs({ 'gobble_vermin_class', 'gobble_vermin_creature', 'gobble_vermin_caste' }) do
          local vec = ca[f]
          for i = #vec - 1, 0, -1 do vec:erase(i) end
          local src = (f == 'gobble_vermin_class' and o.cls) or (f == 'gobble_vermin_creature' and o.cre) or o.cas
          for _, s in ipairs(src) do vec:insert('#', { new = true, value = s }) end
        end
        ca.flags.VERMIN_GOBBLER = o.flag
        S['{P}:' .. ci] = nil
        n = n + 1
      end
    end
  end
end
print(('eco gobble token={P} restored=%d'):format(n))
