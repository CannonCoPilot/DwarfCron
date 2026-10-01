-- Who stands by the placed vermin: every live unit within {R} tiles (same z +-1) of a loose ROACH_LARGE or GRASSHOPPER,
-- with its race, kind (citizen / tame = the fort's own animal / wild / other) and its nearest distance. VRM3 control.
local V = {}
for _, v in ipairs(df.global.world.event.vermin) do
  local c = df.creature_raw.find(v.race)
  if c and (c.creature_id == 'ROACH_LARGE' or c.creature_id == 'GRASSHOPPER') and not v.flags.is_colony and not v.flags.already_deleting then V[#V+1] = v.pos end
end
local n = 0
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and not u.flags1.inactive then
    local best = 99
    for _, p in ipairs(V) do
      if math.abs(p.z - u.pos.z) <= 1 then local d = math.max(math.abs(p.x - u.pos.x), math.abs(p.y - u.pos.y)); if d < best then best = d end end
    end
    if best <= {R} then
      n = n + 1
      local kind = dfhack.units.isCitizen(u) and 'citizen' or (dfhack.units.isWildlife(u) and 'wild') or (dfhack.units.isOwnCiv(u) and dfhack.units.isTame(u) and 'tame') or 'other'
      local c = df.creature_raw.find(u.race)
      print(('eco near tag={TAG} unit=%d race=%s kind=%s d=%d'):format(u.id, c and c.creature_id or '?', kind, best))
    end
  end
end
print(('eco nearsum tag={TAG} units=%d vermin=%d'):format(n, #V))
