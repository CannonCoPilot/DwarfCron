-- Loose vermin of {RACE} within R of X,Y,Z (z-1..z+1) and on the whole map; colonies and objects being deleted excluded.
local near, map, objs = 0, 0, 0
for _, v in ipairs(df.global.world.event.vermin) do
  local c = df.creature_raw.find(v.race)
  if c and c.creature_id == '{RACE}' and not v.flags.is_colony and not v.flags.already_deleting then
    map = map + (v.amount or 1)
    objs = objs + 1
    if math.abs(v.pos.x - {X}) <= {R} and math.abs(v.pos.y - {Y}) <= {R} and math.abs(v.pos.z - {Z}) <= 1 then near = near + (v.amount or 1) end
  end
end
print(('eco vcount tag={TAG} race={RACE} near=%d map=%d objs=%d'):format(near, map, objs))
