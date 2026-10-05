-- retest: FIX = sponges placed by `roster depth place` (own SPONGE entry), moved into adjacent F+M pairs;
-- OLD = new sponges on the old borrowed reference (the cave's first Animal entry: another species), adjacent F+M pairs
local all=df.global.world.populations.all
local rs; for i,c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id=="SPONGE" then rs=i end end
local function caste(id) for i,c in ipairs(df.creature_raw.find(rs).caste) do if c.caste_id==id then return i end end end
local F,M,zs={}, {}, {}
for _,u in ipairs(df.global.world.units.active) do if u.race==rs and not dfhack.units.isDead(u) and u.animal.population.cave_id==4 then
  if u.sex==0 then F[#F+1]=u else M[#M+1]=u end; zs[u.pos.z]=true end end
local z; for zz in pairs(zs) do z=zz end
local borrow; for _,p in ipairs(all) do if p.population.cave_id==4 and df.world_population_type[p.type]=="Animal" and p.race~=rs then borrow=p break end end
print("fix sponges F", #F, "M", #M, "z", z, "old ref borrowed from", df.creature_raw.find(borrow.race).creature_id)
local function free(x,y) local b=dfhack.maps.getTileBlock(x,y,z); if not b then return false end
  local d=b.designation[x%16][y%16]; local o=b.occupancy[x%16][y%16]
  return d.flow_size>=4 and not d.liquid_type and d.subterranean and not o.unit and not o.unit_grounded end
local taken={}
for _,u in ipairs(df.global.world.units.active) do if u.race==rs then taken[#taken+1]={u.pos.x,u.pos.y} end end
local function clear(x,y) for _,t in ipairs(taken) do if math.max(math.abs(t[1]-x),math.abs(t[2]-y))<3 then return false end end return true end
local pairs_={}
for y=1,df.global.world.map.y_count-2 do for x=1,df.global.world.map.x_count-2 do
  if #pairs_>=10 then break end
  if free(x,y) and clear(x,y) then local p
    if free(x+1,y) and clear(x+1,y) then p={x,y,x+1,y} elseif free(x,y+1) and clear(x,y+1) then p={x,y,x,y+1} end
    if p then pairs_[#pairs_+1]=p taken[#taken+1]={p[1],p[2]} taken[#taken+1]={p[3],p[4]} end
  end end end
print("pair sites", #pairs_)
local function move(u, x, y)
  local ok=dfhack.units.teleport(u, xyz2pos(x,y,z)) return ok end
local nfix=math.min(#F,#M,5)
local out={}
for i=1,nfix do local p=pairs_[i]
  move(F[i],p[1],p[2]) move(M[i],p[3],p[4]) out[#out+1]=("FIX F%d M%d at %d,%d"):format(F[i].id,M[i].id,p[1],p[2]) end
-- park the unpaired fix sponges far from every pair (they share the fix arm, never counted)
local function put(cid, pos)
  local u=dfhack.units.create(rs, caste(cid))
  local r, ap = borrow.population, u.animal.population
  ap.region_x, ap.region_y = r.region_x, r.region_y
  ap.feature_idx, ap.cave_id, ap.site_id, ap.population_idx = r.feature_idx, r.cave_id, r.site_id, r.population_idx
  u.animal.leave_countdown=2000000
  u.flags2.roaming_wilderness_population_source=false
  u.flags2.roaming_wilderness_population_source_not_a_map_feature=false
  u.pos:assign(pos); u.idle_area:assign(pos)
  df.global.world.units.active:insert('#', u)
  dfhack.maps.getTileBlock(pos).occupancy[pos.x%16][pos.y%16].unit=true
  u.flags1.inactive=false
  u.birth_year=df.global.cur_year-3
  return u
end
for i=nfix+1, math.min(nfix+5, #pairs_) do local p=pairs_[i]
  local f=put("FEMALE", xyz2pos(p[1],p[2],z)); local m=put("MALE", xyz2pos(p[3],p[4],z))
  out[#out+1]=("OLD F%d M%d at %d,%d"):format(f.id,m.id,p[1],p[2]) end
for _,l in ipairs(out) do print(l) end
