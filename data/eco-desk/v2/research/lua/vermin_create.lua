-- Create N loose (non-colony) vermin of {RACE} on walkable, dry, outdoor tiles within R of X,Y,Z (same z).
-- Placeholders: {RACE} {N} {R} filled by Python .replace(); {X} {Y} {Z} by eco-run's regex fill.
-- Recipe follows DFHack hack/scripts/colonies.lua (place_vermin): df.vermin:new(), race/caste/amount/visible/pos,
-- insert into world.event.vermin. Loose vermin are NOT inserted into vermin_colonies and do not set is_colony.
local race_id = -1
for k, v in ipairs(df.global.world.raws.creatures.all) do if v.creature_id == '{RACE}' then race_id = k break end end
if race_id < 0 then print('eco vcreate race={RACE} fail=norace') return end
local src = nil
for _, v in ipairs(df.global.world.event.vermin) do
  if v.race == race_id and not v.flags.is_colony then src = v break end
end
if not src then
  for _, v in ipairs(df.global.world.event.vermin) do
    if not v.flags.is_colony and v.category == df.vermin_category.Grounder then src = v break end
  end
end
local x0, y0, z0, r, want = {X}, {Y}, {Z}, {R}, {N}
local made, tries = 0, 0
while made < want and tries < want * 50 do
  tries = tries + 1
  local x, y = x0 + math.random(-r, r), y0 + math.random(-r, r)
  local tt = dfhack.maps.getTileType(x, y, z0)
  local fl = dfhack.maps.getTileFlags(x, y, z0)
  if tt and fl and fl.outside and fl.flow_size == 0 then
    local shape = df.tiletype.attrs[tt].shape
    if df.tiletype_shape.attrs[shape].walkable then
      local v = df.vermin:new()
      v.race = race_id
      v.caste = 0
      v.amount = 1
      v.visible = true
      v.category = df.vermin_category.Grounder
      v.pos.x, v.pos.y, v.pos.z = x, y, z0
      if src then v.population:assign(src.population) end
      df.global.world.event.vermin:insert('#', v)
      made = made + 1
    end
  end
end
print(('eco vcreate race={RACE} made=%d tries=%d popsrc=%s'):format(made, tries, src and 'copied' or 'none'))
