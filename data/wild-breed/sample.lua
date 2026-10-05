-- per arm: females pregnant / alive, births since placement (units newer than the placed ids)
local first, last = 157, 196
local arm_of = {}
local n=0
for id=first,last,2 do n=n+1 arm_of[id]=({"A","B","C","D"})[(n-1)%4+1] arm_of[id+1]=arm_of[id] end
local res={A={0,0,0},B={0,0,0},C={0,0,0},D={0,0,0}}
for id,arm in pairs(arm_of) do local u=df.unit.find(id)
  if u and u.sex==0 then if not dfhack.units.isDead(u) then res[arm][2]=res[arm][2]+1 end if u.pregnancy_timer>0 then res[arm][1]=res[arm][1]+1 end end
end
local births={}
for _,u in ipairs(df.global.world.units.all) do if u.id>last and df.creature_raw.find(u.race).creature_id=="SPONGE" then
  local mom=u.relationship_ids.Mother births[#births+1]=u.id..":mother"..mom..":"..(arm_of[mom] or "?") end end
print(df.global.cur_year, df.global.cur_year_tick, ("A tame+own preg %d/%d | B wild %d/%d | C own %d/%d | D tame %d/%d"):format(res.A[1],res.A[2],res.B[1],res.B[2],res.C[1],res.C[2],res.D[1],res.D[2]), "births", #births, table.concat(births," "))
