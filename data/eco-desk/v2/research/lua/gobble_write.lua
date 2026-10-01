-- Write GOBBLE_VERMIN_CLASS:{CLS} (kind=class) or GOBBLE_VERMIN_CREATURE:{CLS}:ALL (kind=creature) on every caste of {P},
-- and set the derived caste flag VERMIN_GOBBLER. Originals saved in _G for gobble_restore.lua.
local S = rawget(_G, '__eco_gobble') or {}
rawset(_G, '__eco_gobble', S)
local n = 0
for _, c in ipairs(df.global.world.raws.creatures.all) do
  if c.creature_id == '{P}' then
    for ci, ca in ipairs(c.caste) do
      local key = '{P}:' .. ci
      if not S[key] then
        local cls, cre, cas = {}, {}, {}
        for _, s in ipairs(ca.gobble_vermin_class) do cls[#cls + 1] = s.value end
        for _, s in ipairs(ca.gobble_vermin_creature) do cre[#cre + 1] = s.value end
        for _, s in ipairs(ca.gobble_vermin_caste) do cas[#cas + 1] = s.value end
        S[key] = { cls = cls, cre = cre, cas = cas, flag = ca.flags.VERMIN_GOBBLER }
      end
      if '{KIND}' == 'class' then
        ca.gobble_vermin_class:insert('#', { new = true, value = '{CLS}' })
      else
        ca.gobble_vermin_creature:insert('#', { new = true, value = '{CLS}' })
        ca.gobble_vermin_caste:insert('#', { new = true, value = 'ALL' })
      end
      ca.flags.VERMIN_GOBBLER = true
      n = n + 1
    end
  end
end
print(('eco gobble token={P} kind={KIND} value={CLS} castes=%d'):format(n))
