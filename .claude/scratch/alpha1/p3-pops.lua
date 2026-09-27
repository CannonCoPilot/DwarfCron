local sw = reqscript('seasonal-wildlife')
local want = { CAVY=1, BIRD_KESTREL=1, GIANT_RHINOCEROS=1, GIANT_JACKAL=1, ELEPHANT=1, RIVER_OTTER=1, ['RIVER OTTER']=1 }
local regions = sw.getEmbarkRegions()
local inEmb = {}
for _, r in ipairs(regions or {}) do inEmb[r] = true end
print('embark regions: ' .. #(regions or {}))
for i, p in ipairs(df.global.world.populations.all) do
  local ok, cr = pcall(function() return df.creature_raw.find(p.race) end)
  local tok = ok and cr and cr.creature_id or '?'
  if want[tok] then
    local reg = p.region and (p.region.region_id or -1) or -1
    print(('idx=%d %s type=%s qty=%d/%d ref6=%s,%s,%s,%s,%s,%s ext=%s disc=%s'):format(i, tok, df.world_population_type[p.type], p.quantity, p.quantity2 or -1,
      p.region.region_x, p.region.region_y, p.region.feature_idx, p.region.cave_id, p.region.site_id, p.region.population_idx, tostring(p.flags.extinct), tostring(p.flags.discovered)))
  end
end
