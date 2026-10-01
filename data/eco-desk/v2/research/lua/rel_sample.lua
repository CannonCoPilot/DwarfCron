-- Sample enemy_status_cache: every slotted live-unit pair with ur in {PREDATOR_OR_PREY, DANGEROUS_ANIMAL, BENIGN_ANIMAL}.
-- New entries (first seen since the cell's reset) are printed with both units' species, class, key flags, size and
-- Chebyshev distance at this sample. _G.__eco_rel holds pairs already seen; tag 'reset' clears it.
local K = rawget(_G, '__eco_rel') or {}
rawset(_G, '__eco_rel', K)
if '{TAG}' == 'reset' then for k in pairs(K) do K[k] = nil end print('eco rel tag=reset ok=1') return end
local want = { PREDATOR_OR_PREY = true, DANGEROUS_ANIMAL = true, BENIGN_ANIMAL = true }
local c = df.global.world.enemy_status_cache
local L = {}
for _, u in ipairs(df.global.world.units.active) do
  if not dfhack.units.isDead(u) and u.enemy.enemy_status_slot >= 0 then L[#L + 1] = u end
end
local function desc(u)
  local r = df.creature_raw.find(u.race)
  local ca = r and r.caste[u.caste]
  local cls = dfhack.units.isCitizen(u) and 'cit' or (u.flags2.roaming_wilderness_population_source and 'wild') or (dfhack.units.isTame(u) and 'tame') or 'other'
  local fl = ''
  if ca then
    if ca.flags.LARGE_PREDATOR then fl = fl .. 'L' end
    if ca.flags.BENIGN then fl = fl .. 'B' end
    if ca.flags.CARNIVORE then fl = fl .. 'C' end
    if ca.flags.BONECARN then fl = fl .. 'O' end
    if ca.flags.AMBUSHPREDATOR then fl = fl .. 'A' end
  end
  return (r and r.creature_id or '?'):gsub(' ', '_') .. ':' .. cls .. ':' .. (fl ~= '' and fl or '-') .. ':' .. (ca and ca.misc.adult_size or 0)
end
local new, tot = 0, 0
for i = 1, #L do
  local a = L[i]
  for j = 1, #L do
    if i ~= j then
      local b = L[j]
      local v = c.rel_map[a.enemy.enemy_status_slot][b.enemy.enemy_status_slot].ur
      local nm = df.unit_reaction_type[v]
      if nm and want[nm] then
        tot = tot + 1
        local key = a.id .. '>' .. b.id .. '=' .. nm
        if not K[key] then
          K[key] = true
          new = new + 1
          local d = math.max(math.abs(a.pos.x - b.pos.x), math.abs(a.pos.y - b.pos.y), math.abs(a.pos.z - b.pos.z))
          print(('eco rel tag={TAG} a=%s b=%s ur=%s d=%d ids=%d>%d'):format(desc(a), desc(b), nm, d, a.id, b.id))
        end
      end
    end
  end
end
print(('eco relsum tag={TAG} slotted=%d entries=%d new=%d tick=%d'):format(#L, tot, new, df.global.cur_year_tick))
