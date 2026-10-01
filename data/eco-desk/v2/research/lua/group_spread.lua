-- COH: bounding-box spread of every live spawned {TOKEN} (same _G.CX_ECO.spawned membership idiom as leader_dist.lua):
-- member count, x-width, y-depth. {TAG} placeholder.
local xs, ys, n = {}, {}, 0
for id, tok in pairs(_G.CX_ECO.spawned) do if tok == '{TOKEN}' then
  local u = df.unit.find(id)
  if u and not dfhack.units.isDead(u) then xs[#xs + 1] = u.pos.x; ys[#ys + 1] = u.pos.y; n = n + 1 end
end end
local function range(t)
  if #t == 0 then return 0 end
  local lo, hi = t[1], t[1]
  for _, v in ipairs(t) do if v < lo then lo = v end if v > hi then hi = v end end
  return hi - lo
end
print(('eco spread tag={TAG} token={TOKEN} n=%d width=%d depth=%d'):format(n, range(xs), range(ys)))
