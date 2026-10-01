-- Write CREATURE_CLASS:{CLS} on every caste of vermin species {V} (a class written at *runtime*, not a native
-- one), and GOBBLE_VERMIN_CLASS:{CLS} + VERMIN_GOBBLER on every caste of consumer {P}. This is the open question
-- from seasonal-wildlife's VERMIN.gobbleApply (v7.0.0, vermin-gobble branch): does DF match a runtime-written
-- CREATURE_CLASS the same way it matches a native one (vanilla's only example, EDIBLE_GROUND_BUG, was already
-- compiled into the raws when VRM2 proved the mechanism). {V} should be a vermin species that does NOT already
-- carry {CLS} or EDIBLE_GROUND_BUG natively (e.g. GRASSHOPPER, which is VERMIN_GROUNDER only), so any predation
-- seen on it can only be explained by the written class actually matching.
-- Control arm: run this script, then immediately run gobble_class_restore.lua before the observation window
-- (or simply never run this script) for an unmodified {P}/{V} pair -- the same "on vs off" shape as
-- gobble_write.lua / gobble_restore.lua. Originals saved in _G under a key separate from gobble_write.lua's,
-- so the two pairs never collide if both are loaded in the same session.
local S = rawget(_G, '__eco_gobble_class') or {}
rawset(_G, '__eco_gobble_class', S)
local nV, nP = 0, 0
for _, c in ipairs(df.global.world.raws.creatures.all) do
  if c.creature_id == '{V}' then
    for ci, ca in ipairs(c.caste) do
      local key = 'V:{V}:' .. ci
      if not S[key] then
        local cls = {}
        for _, s in ipairs(ca.creature_class) do cls[#cls + 1] = s.value end
        S[key] = { cls = cls }
      end
      ca.creature_class:insert('#', { new = true, value = '{CLS}' })
      nV = nV + 1
    end
  elseif c.creature_id == '{P}' then
    for ci, ca in ipairs(c.caste) do
      local key = 'P:{P}:' .. ci
      if not S[key] then
        local cls = {}
        for _, s in ipairs(ca.gobble_vermin_class) do cls[#cls + 1] = s.value end
        S[key] = { cls = cls, flag = ca.flags.VERMIN_GOBBLER }
      end
      ca.gobble_vermin_class:insert('#', { new = true, value = '{CLS}' })
      ca.flags.VERMIN_GOBBLER = true
      nP = nP + 1
    end
  end
end
print(('eco gobble-class vermin={V} consumer={P} class={CLS} v-castes=%d p-castes=%d'):format(nV, nP))
