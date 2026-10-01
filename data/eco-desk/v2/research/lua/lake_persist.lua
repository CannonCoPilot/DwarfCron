-- LAKEP: does the explicit PREDATOR_OR_PREY write between {A} ({AIDS}) and {B} ({BIDS}) survive over time? Reads
-- enemy_status_cache.rel_map for every slotted pair across the two groups: how many of them still read ur==PREDATOR_OR_PREY
-- vs how many pairs exist at all. {TAG} placeholder. Same gmatch-over-ids idiom as dom_bring.lua/dom_sample.lua.
local c = df.global.world.enemy_status_cache
local n = #c.rel_map
local P = df.unit_reaction_type.PREDATOR_OR_PREY
local A, B = {}, {}
for id in ('{AIDS}'):gmatch('%d+') do
  local u = df.unit.find(tonumber(id))
  if u and not dfhack.units.isDead(u) then A[#A + 1] = u end
end
for id in ('{BIDS}'):gmatch('%d+') do
  local u = df.unit.find(tonumber(id))
  if u and not dfhack.units.isDead(u) then B[#B + 1] = u end
end
local held, total = 0, 0
for _, a in ipairs(A) do
  local sa = a.enemy.enemy_status_slot
  for _, bb in ipairs(B) do
    local sb = bb.enemy.enemy_status_slot
    if sa >= 0 and sb >= 0 and sa < n and sb < n then
      total = total + 1
      if c.rel_map[sa][sb].ur == P then held = held + 1 end
    end
  end
end
print(('eco lakerel tag={TAG} a={A} b={B} alive_a=%d alive_b=%d held=%d total=%d'):format(#A, #B, held, total))
