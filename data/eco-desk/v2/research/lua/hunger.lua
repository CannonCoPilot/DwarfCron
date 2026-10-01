-- hunger_timer / thirst_timer of live {P} units (does gobbling feed a wild unit?).
local t = {}
for _, u in ipairs(df.global.world.units.active) do
  local c = df.creature_raw.find(u.race)
  if c and c.creature_id == '{P}' and not dfhack.units.isDead(u) then
    t[#t + 1] = u.counters2.hunger_timer .. '/' .. u.counters2.thirst_timer
  end
end
print(('eco hunger tag={TAG} token={P} n=%d ht=%s'):format(#t, table.concat(t, ',')))
