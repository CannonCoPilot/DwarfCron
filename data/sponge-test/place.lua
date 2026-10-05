-- sponge breeding test: place tame sponges (A), wild sponges (B), tame horseshoe crabs (C), 2F+2M each, in open ocean
local function race(tok) for i,c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id==tok then return i end end end
local function caste(r, id) for i,c in ipairs(df.creature_raw.find(r).caste) do if c.caste_id==id then return i end end end
local rs, rh = race("SPONGE"), race("HORSESHOE_CRAB")
local crabref
for _,p in ipairs(df.global.world.populations.all) do if p.race==rh and p.quantity>0 then crabref=p.population break end end
-- open salt water at flow 7, z98, not hidden, unoccupied, with water 1 tile around
local function ok(x,y,z)
  local b=dfhack.maps.getTileBlock(x,y,z); if not b then return false end
  local d=b.designation[x%16][y%16]; local o=b.occupancy[x%16][y%16]
  return d.flow_size==7 and d.water_salt and not d.hidden and not o.unit and not o.unit_grounded
end
local z=98
local spots={}
for y=300,700,2 do for x=100,700,2 do
  if #spots>=3 then break end
  local good=true
  for dx=0,3 do if not ok(x+dx,y,z) then good=false break end end
  if good then
    local far=true for _,s in ipairs(spots) do if math.abs(s[2]-y)<20 and math.abs(s[1]-x)<20 then far=false end end
    if far then spots[#spots+1]={x,y} end
  end
end end
if #spots<3 then qerror("found only "..#spots.." spots") end
local placed={}
local function put(r, cid, pos, tame, ref)
  local u=dfhack.units.create(r, cid)
  if ref then
    local p=u.animal.population
    p.region_x,p.region_y,p.feature_idx,p.cave_id,p.site_id,p.population_idx=ref.region_x,ref.region_y,ref.feature_idx,ref.cave_id,ref.site_id,ref.population_idx
    u.animal.leave_countdown=2000000
  end
  u.flags2.roaming_wilderness_population_source=false
  u.flags2.roaming_wilderness_population_source_not_a_map_feature=false
  u.pos:assign(pos); u.idle_area:assign(pos)
  df.global.world.units.active:insert('#', u)
  local b=dfhack.maps.getTileBlock(pos); b.occupancy[pos.x%16][pos.y%16].unit=true
  u.flags1.inactive=false
  u.birth_year=df.global.cur_year-3
  if tame then
    dfhack.units.makeown(u)
    u.flags1.tame=true
    u.training_level=df.animal_training_level.Domesticated
  end
  return u
end
local groups={{"A",rs,true,nil},{"B",rs,false,crabref},{"C",rh,true,nil}}
for gi,g in ipairs(groups) do
  local sx,sy=spots[gi][1],spots[gi][2]
  local ids={}
  for k,cid in ipairs({"FEMALE","FEMALE","MALE","MALE"}) do
    local u=put(g[2], caste(g[2],cid), xyz2pos(sx+k-1,sy,z), g[3], g[4])
    ids[#ids+1]=u.id
  end
  print(g[1], df.creature_raw.find(g[2]).creature_id, "at", sx, sy, z, "ids", table.concat(ids," "))
end
