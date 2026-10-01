-- Restore every FREQUENCY changed by freq_steer.lua in this cell.
local S = rawget(_G, '__eco_freq') or {}
local n = 0
for _, cr in ipairs(df.global.world.raws.creatures.all) do
  local o = S[cr.creature_id]
  if o ~= nil then cr.frequency = o; n = n + 1 end
end
rawset(_G, '__eco_freq', {})
print(('eco freq restored=%d'):format(n))
