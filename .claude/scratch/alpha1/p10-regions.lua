local sw=reqscript('seasonal-wildlife')
local rs=sw.getEmbarkRegions(); local k={}; for key in pairs(rs) do k[#k+1]=key end; table.sort(k); print('tool set: '..table.concat(k,' '))
local site=df.world_site.find(df.global.plotinfo.site_id)
print(('site record: x %d..%d y %d..%d (mid-level tiles); /16 -> %d..%d, %d..%d'):format(site.global_min_x, site.global_max_x, site.global_min_y, site.global_max_y, site.global_min_x//16, site.global_max_x//16, site.global_min_y//16, site.global_max_y//16))
local wd=df.global.world.world_data; local WW,WH=wd.world_width,wd.world_height
local pos, used, full = {}, {}, {}
local t0=dfhack.getTickCount(); local n=0
for _, blk in ipairs(df.global.world.map.map_blocks) do
  local rx0, ry0 = blk.region_pos.x, blk.region_pos.y
  pos[rx0..':'..ry0]=true
  for o=0,8 do local off=blk.region_offset[o]; local rx=math.max(0,math.min(WW-1,rx0+(off%3)-1)); local ry=math.max(0,math.min(WH-1,ry0+(off//3)-1)); full[rx..':'..ry]=true end
  if blk.map_pos.z % 4 == 0 then
    for lx=0,15,3 do for ly=0,15,3 do local off=blk.region_offset[blk.designation[lx][ly].biome]; local rx=math.max(0,math.min(WW-1,rx0+(off%3)-1)); local ry=math.max(0,math.min(WH-1,ry0+(off//3)-1)); used[rx..':'..ry]=true; n=n+1 end end
  end
end
local function list(t) local o={} for key in pairs(t) do o[#o+1]=key end table.sort(o) return table.concat(o,' ') end
print('block region_pos: '..list(pos)); print('tiles used (sampled): '..list(used)..'  ['..n..' reads, '..(dfhack.getTickCount()-t0)..' ms]'); print('3x3 of region_offset: '..list(full))
local srcs={}
for _,pop in ipairs(df.global.world.populations.all) do local cr=df.creature_raw.find(pop.race); if cr and cr.creature_id=='CAVY' then srcs[#srcs+1]=pop.population.region_x..','..pop.population.region_y..'='..pop.quantity end end
print('CAVY entries: '..table.concat(srcs,' '))
