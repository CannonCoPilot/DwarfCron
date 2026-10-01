-- DOM: run one ecology pass, then count PREDATOR_OR_PREY cells from the placed wolves ({IDS}) to the fort's own animals,
-- the fort animals alive, and each wolf's distance to the nearest of them.
local sw = reqscript('seasonal-wildlife'); dfhack.run_command_silent('seasonal-wildlife', 'groups', 'ecology', 'now')
local c = df.global.world.enemy_status_cache; local n = #c.rel_map; local P = df.unit_reaction_type.PREDATOR_OR_PREY
local D = {}
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and not u.flags1.inactive and dfhack.units.isAnimal(u) and sw.V7.isDomestic(u) then D[#D+1] = u end end
local rel, pairs_, near = 0, 0, {}
for id in ('{IDS}'):gmatch('%d+') do
  local w = df.unit.find(tonumber(id))
  if w and not dfhack.units.isDead(w) then
    local sa, md = w.enemy.enemy_status_slot, 999
    for _, d in ipairs(D) do
      local sb = d.enemy.enemy_status_slot
      if sa >= 0 and sb >= 0 and sa < n and sb < n then pairs_ = pairs_ + 1; if c.rel_map[sa][sb].ur == P then rel = rel + 1 end end
      if d.pos.z == w.pos.z then md = math.min(md, math.max(math.abs(d.pos.x - w.pos.x), math.abs(d.pos.y - w.pos.y))) end
    end
    near[#near+1] = md end end
print(('eco dom tag={TAG} rel=%d slotted_pairs=%d domestic_alive=%d wolf_dist=%s'):format(rel, pairs_, #D, table.concat(near, ',')))
