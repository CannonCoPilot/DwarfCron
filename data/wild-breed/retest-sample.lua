local arms={FIX={{157,158},{159,160},{162,161},{163,164},{167,165}}, OLD={{169,170},{171,172},{173,174},{175,176},{177,178}}}
local out={}
for _,name in ipairs({"FIX","OLD"}) do local preg,adj,alive=0,0,0
  for _,pr in ipairs(arms[name]) do local f,m=df.unit.find(pr[1]),df.unit.find(pr[2])
    if f and m and not dfhack.units.isDead(f) then alive=alive+1
      if math.max(math.abs(f.pos.x-m.pos.x),math.abs(f.pos.y-m.pos.y))==1 and f.pos.z==m.pos.z then adj=adj+1 end
      if f.pregnancy_timer>0 then preg=preg+1 end end end
  out[#out+1]=("%s pregnant %d/%d (adjacent %d)"):format(name,preg,alive,adj) end
local births=0 for _,u in ipairs(df.global.world.units.all) do if u.id>178 and df.creature_raw.find(u.race).creature_id=="SPONGE" then births=births+1 end end
print(df.global.cur_year, df.global.cur_year_tick, table.concat(out," | "), "births", births)
