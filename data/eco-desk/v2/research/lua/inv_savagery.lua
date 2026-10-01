-- INV: read this embark's Savage-Calm axis so INV's "savage map" premise is checked, not assumed. No CLI/tool reader
-- exists for savagery (V7.alignment() only reads evilness -- confirmed by grep, zero other call sites). Same
-- per-region-tile loop as V7.alignment(), reading region_map_entry.savagery (the paired field next to evilness in
-- DF's own structure) via dfhack.maps.getRegionBiome. {TAG} placeholder.
local sw = reqscript('seasonal-wildlife')
local rs = sw.getEmbarkRegions()
local tiles, savage, calm = 0, 0, 0
for key in pairs(rs) do
  local rx, ry = key:match('(%d+):(%d+)')
  local ok, ent = pcall(dfhack.maps.getRegionBiome, tonumber(rx), tonumber(ry))
  if ok and ent then
    tiles = tiles + 1
    local okS, sv = pcall(function() return ent.savagery end)
    if okS and type(sv) == 'number' then
      if sv >= 66 then savage = savage + 1 elseif sv < 33 then calm = calm + 1 end
    end
  end
end
print(('eco savagery tag={TAG} tiles=%d savage_tiles=%d calm_tiles=%d'):format(tiles, savage, calm))
