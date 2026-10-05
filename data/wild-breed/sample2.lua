local arm={[161]="GW", [163]="GP", [165]="SP", [167]="GW", [169]="GP", [171]="SP", [173]="GW", [175]="GP", [177]="SP", [179]="GW", [181]="GP", [183]="SP", [185]="GW", [187]="GP", [189]="SP", [191]="MW", [193]="MP", [195]="MW", [197]="MP", [199]="MW", [201]="MP", [203]="MW", [205]="MP", [207]="MW", [209]="MP"}
local order={"GW","GP","SP","MW","MP"}
local res={} for _,a in ipairs(order) do res[a]={0,0} end
for id,a in pairs(arm) do local u=df.unit.find(id)
  if u and not dfhack.units.isDead(u) then res[a][2]=res[a][2]+1 if u.pregnancy_timer>0 then res[a][1]=res[a][1]+1 end end end
local births=0
for _,u in ipairs(df.global.world.units.all) do if u.id>210 and u.relationship_ids.Mother>0 and arm[u.relationship_ids.Mother] then births=births+1 end end
local s={} for _,a in ipairs(order) do s[#s+1]=("%s %d/%d"):format(a,res[a][1],res[a][2]) end
print(df.global.cur_year, df.global.cur_year_tick, "pregnant/alive females: "..table.concat(s," | "), "births", births)
