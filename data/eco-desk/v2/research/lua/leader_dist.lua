-- COH: recompute the {HOW} leader for every live spawned {TOKEN} (same rule cx-eco's `lead` verb used in the
-- preceding step) and report each other member's distance to it: mean, max. {HOW}='none' (cohesion off) always
-- reports leader=-1 -- the "no leader" reading the control arm wants. {TAG} placeholder.
local us = {}
for id, tok in pairs(_G.CX_ECO.spawned) do if tok == '{TOKEN}' then
  local u = df.unit.find(id)
  if u and not dfhack.units.isDead(u) then us[#us + 1] = u end
end end
table.sort(us, function(a, b) return a.id < b.id end)
local leader
if '{HOW}' == 'largest-male' then
  for _, u in ipairs(us) do
    if u.sex == 1 and (not leader or u.body.size_info.size_cur > leader.body.size_info.size_cur) then leader = u end
  end
elseif '{HOW}' == 'lowest' then leader = us[1] end
if not leader then
  print(('eco leaderdist tag={TAG} token={TOKEN} leader=-1 members=%d mean=-1 max=-1'):format(#us))
  return
end
local sum, mx, n = 0, 0, 0
for _, u in ipairs(us) do
  if u ~= leader then
    local d = math.sqrt((u.pos.x - leader.pos.x) ^ 2 + (u.pos.y - leader.pos.y) ^ 2)
    sum, n = sum + d, n + 1
    if d > mx then mx = d end
  end
end
print(('eco leaderdist tag={TAG} token={TOKEN} leader=%d members=%d mean=%.1f max=%.1f'):format(leader.id, #us, n > 0 and sum / n or 0, mx))
