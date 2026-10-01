-- DOM: move the placed wolves ({IDS}) onto the fort animal nearest the spot, so the test is the relation, not the walk.
local sw = reqscript('seasonal-wildlife'); local best, bd
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and not u.flags1.inactive and dfhack.units.isAnimal(u) and sw.V7.isDomestic(u) then
    local d = math.max(math.abs(u.pos.x - {X}), math.abs(u.pos.y - {Y})) + 10 * math.abs(u.pos.z - {Z})
    if not bd or d < bd then best, bd = u, d end end end
local moved = 0
if best then for id in ('{IDS}'):gmatch('%d+') do local w = df.unit.find(tonumber(id)); if w and dfhack.units.teleport(w, best.pos) then moved = moved + 1 end end end
local cr = best and df.creature_raw.find(best.race)
print(('eco dombring moved=%d near=%s at=%s'):format(moved, cr and cr.creature_id or 'none', best and (best.pos.x .. ',' .. best.pos.y .. ',' .. best.pos.z) or '-'))
