-- wild-breed follow-up: real wild population references vs plain units, adjacent F+M pairs
-- GW giant sponge, true ref (its own region population) | GP giant sponge plain | SP sponge plain
-- MW mink, true ref | MP mink plain   (plain = no population ref, no civ, not tame)
local function race(tok) for i,c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id==tok then return i end end end
local function caste(r, id) for i,c in ipairs(df.creature_raw.find(r).caste) do if c.caste_id==id then return i end end end
local function refFor(r) for _,p in ipairs(df.global.world.populations.all) do local q=p.population
  if p.type==0 and p.race==r and q.region_x==9 and q.region_y==22 and p.quantity>0 then return q, p end end end
local function water(x,y,z) local b=dfhack.maps.getTileBlock(x,y,z); if not b then return false end
  local d=b.designation[x%16][y%16]; local o=b.occupancy[x%16][y%16]
  return d.flow_size==7 and not d.liquid_type and not d.hidden and not o.unit and not o.unit_grounded end
local function land(x,y,z) local b=dfhack.maps.getTileBlock(x,y,z); if not b then return false end
  local d=b.designation[x%16][y%16]; local o=b.occupancy[x%16][y%16]
  local tt=b.tiletype[x%16][y%16]; local sh=df.tiletype.attrs[tt].shape
  return d.flow_size==0 and d.outside and not d.hidden and sh==df.tiletype_shape.FLOOR and not o.unit and not o.unit_grounded and o.building==df.tile_building_occ.None end
local function bestZ(fn) local zs={} for _,b in ipairs(df.global.world.map.map_blocks) do local z=b.map_pos.z
  for lx=0,15,3 do for ly=0,15,3 do if fn(b.map_pos.x+lx,b.map_pos.y+ly,z) then zs[z]=(zs[z] or 0)+1 end end end end
  local bz,bn=-1,0 for z,n in pairs(zs) do if n>bn then bz,bn=z,n end end return bz end
local taken={}
local function clear(x,y) for _,t in ipairs(taken) do if math.max(math.abs(t[1]-x),math.abs(t[2]-y))<3 then return false end end return true end
local function findPairs(fn, z, n)
  local out={} local mx,my=df.global.world.map.x_count-2, df.global.world.map.y_count-2
  for y=1,my do for x=1,mx do if #out>=n then return out end
    if fn(x,y,z) and clear(x,y) then
      local p
      if fn(x+1,y,z) and clear(x+1,y) then p={x,y,x+1,y} elseif fn(x,y+1,z) and clear(x,y+1) then p={x,y,x,y+1} end
      if p then out[#out+1]=p taken[#taken+1]={p[1],p[2]} taken[#taken+1]={p[3],p[4]} end
    end end end
  return out
end
local function put(r, cid, pos, ref)
  local u=dfhack.units.create(r, caste(r,cid))
  if ref then local p=u.animal.population
    p.region_x,p.region_y,p.feature_idx,p.cave_id,p.site_id,p.population_idx=ref.region_x,ref.region_y,ref.feature_idx,ref.cave_id,ref.site_id,ref.population_idx
    u.animal.leave_countdown=2000000 end
  u.flags2.roaming_wilderness_population_source=false
  u.flags2.roaming_wilderness_population_source_not_a_map_feature=false
  u.pos:assign(pos); u.idle_area:assign(pos)
  df.global.world.units.active:insert('#', u)
  dfhack.maps.getTileBlock(pos).occupancy[pos.x%16][pos.y%16].unit=true
  u.flags1.inactive=false
  u.birth_year=df.global.cur_year-3
  return u
end
local rg, rs, rm = race("GIANT_SPONGE"), race("SPONGE"), race("MINK")
local gref, gpop = refFor(rg)
local mref, mpop = refFor(rm)
if not gref or not mref then qerror("no population ref: giant sponge "..tostring(gref).." mink "..tostring(mref)) end
print("refs: giant sponge pop q="..gpop.quantity.." feat="..gref.feature_idx.." idx="..gref.population_idx, "mink q="..mpop.quantity.." feat="..mref.feature_idx.." idx="..mref.population_idx)
local wz, lz = bestZ(water), bestZ(land)
local wp = findPairs(water, wz, 15)
local lp = findPairs(land, lz, 10)
if #wp<15 or #lp<10 then qerror(("pairs: water %d at z%d, land %d at z%d"):format(#wp,wz,#lp,lz)) end
local plan={}
for i=1,15 do plan[#plan+1]={({"GW","GP","SP"})[(i-1)%3+1], wp[i], wz} end
for i=1,10 do plan[#plan+1]={({"MW","MP"})[(i-1)%2+1], lp[i], lz} end
for _,e in ipairs(plan) do
  local arm,p,z=e[1],e[2],e[3]
  local r=(arm:sub(1,1)=="G") and rg or ((arm=="SP") and rs or rm)
  local ref=(arm=="GW") and gref or ((arm=="MW") and mref or nil)
  local f=put(r,"FEMALE",xyz2pos(p[1],p[2],z),ref); local m=put(r,"MALE",xyz2pos(p[3],p[4],z),ref)
  print(arm, f.id, m.id, p[1], p[2], p[3], p[4], z, "wild", dfhack.units.isWildlife(f), "civ", f.civ_id, "tame", f.flags1.tame)
end
