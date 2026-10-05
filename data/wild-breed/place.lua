-- wild-breed: 4 arms x 5 adjacent FEMALE+MALE sponge pairs in open water (sponges are IMMOBILE: adjacency is fixed)
-- A tame+owned (makeown, tame, Domesticated)   B wild (population ref borrowed: no sponge population in region15)
-- C owned only (civ_id = fort civ; not tame)     D tame flag only (tame + Domesticated; civ -1)
local function race(tok) for i,c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id==tok then return i end end end
local function caste(r, id) for i,c in ipairs(df.creature_raw.find(r).caste) do if c.caste_id==id then return i end end end
local rs = race("SPONGE")
local ref
for _,p in ipairs(df.global.world.populations.all) do if p.quantity>0 and p.population.region_x>=0 then ref=p.population break end end
local function ok(x,y,z)
  local b=dfhack.maps.getTileBlock(x,y,z); if not b then return false end
  local d=b.designation[x%16][y%16]; local o=b.occupancy[x%16][y%16]
  return d.flow_size==7 and not d.liquid_type and not d.hidden and not o.unit and not o.unit_grounded
end
local zs={} for _,b in ipairs(df.global.world.map.map_blocks) do for lx=0,15 do for ly=0,15 do local d=b.designation[lx][ly] if d.flow_size==7 and not d.liquid_type and not d.hidden then zs[b.map_pos.z]=(zs[b.map_pos.z] or 0)+1 end end end end
local z,best=-1,0 for zz,n in pairs(zs) do if n>best then z,best=zz,n end end
local pairs_={}
local function clear(x,y) for _,p in ipairs(pairs_) do for _,t in ipairs({{p[1],p[2]},{p[3],p[4]}}) do if math.max(math.abs(t[1]-x),math.abs(t[2]-y))<3 then return false end end end return true end
local mx,my=df.global.world.map.x_count-2, df.global.world.map.y_count-2
for y=1,my do for x=1,mx do
  if #pairs_>=20 then break end
  if ok(x,y,z) and clear(x,y) then
    if ok(x+1,y,z) and clear(x+1,y) then pairs_[#pairs_+1]={x,y,x+1,y}
    elseif ok(x,y+1,z) and clear(x,y+1) then pairs_[#pairs_+1]={x,y,x,y+1} end
  end
end end
if #pairs_<20 then qerror("only "..#pairs_.." pairs at z "..z) end
local function put(cid, pos, arm)
  local u=dfhack.units.create(rs, caste(rs,cid))
  if arm=="B" then
    local p=u.animal.population
    p.region_x,p.region_y,p.feature_idx,p.cave_id,p.site_id,p.population_idx=ref.region_x,ref.region_y,ref.feature_idx,ref.cave_id,ref.site_id,ref.population_idx
    u.animal.leave_countdown=2000000
  end
  u.flags2.roaming_wilderness_population_source=false
  u.flags2.roaming_wilderness_population_source_not_a_map_feature=false
  u.pos:assign(pos); u.idle_area:assign(pos)
  df.global.world.units.active:insert('#', u)
  dfhack.maps.getTileBlock(pos).occupancy[pos.x%16][pos.y%16].unit=true
  u.flags1.inactive=false
  u.birth_year=df.global.cur_year-3
  if arm=="A" then dfhack.units.makeown(u) u.flags1.tame=true u.training_level=df.animal_training_level.Domesticated end
  if arm=="C" then u.civ_id=df.global.plotinfo.civ_id end
  if arm=="D" then u.flags1.tame=true u.training_level=df.animal_training_level.Domesticated end
  return u
end
local arms={"A","B","C","D"}
for i,p in ipairs(pairs_) do
  local arm=arms[(i-1)%4+1]   -- interleaved so no arm owns one stretch of water
  local f=put("FEMALE", xyz2pos(p[1],p[2],z), arm)
  local m=put("MALE", xyz2pos(p[3],p[4],z), arm)
  print(arm, f.id, m.id, p[1], p[2], p[3], p[4], z, "civ", f.civ_id, "tame", f.flags1.tame, "wild", dfhack.units.isWildlife(f))
end
