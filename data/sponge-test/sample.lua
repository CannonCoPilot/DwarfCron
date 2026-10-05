local out={}
for id=157,168 do
  local u=df.unit.find(id)
  if not u then out[#out+1]=id..":gone" else
    out[#out+1]=("%d:%s/%s%s%s%s preg=%d"):format(id, df.creature_raw.find(u.race).creature_id:sub(1,6), u.sex==0 and "F" or (u.sex==1 and "M" or "?"),
      u.flags1.tame and " tame" or " wild", dfhack.units.isDead(u) and " DEAD" or "", u.flags1.inactive and " inact" or "", u.pregnancy_timer)
  end
end
local born=0
for _,u in ipairs(df.global.world.units.all) do if u.id>168 and (df.creature_raw.find(u.race).creature_id=="SPONGE" or df.creature_raw.find(u.race).creature_id=="HORSESHOE_CRAB") then born=born+1 end end
print(df.global.cur_year, df.global.cur_year_tick, "newborn sponge/crab units", born)
print(table.concat(out,"  "))
