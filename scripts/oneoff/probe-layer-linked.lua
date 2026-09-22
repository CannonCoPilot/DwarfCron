-- E23d follow-up probe: which civilisations in this world are layer-linked (cavern dwellers) and how far their sites are from the fort.
local out = {}
local fort = df.global.plotinfo.site_id
local fs; for _, s in ipairs(df.global.world.world_data.sites) do if s.id == fort then fs = s end end
local fx, fy = fs and fs.pos.x or -1, fs and fs.pos.y or -1
local n_ll, n_civ = 0, 0
for _, e in ipairs(df.global.world.entities.all) do
  if e.type == df.historical_entity_type.Civilization then
    n_civ = n_civ + 1
    local raw = e.entity_raw
    local okf, ll = pcall(function() return raw.flags.LAYER_LINKED end)
    if not okf then local names = {}; pcall(function() for k in pairs(raw.flags) do names[#names+1] = tostring(k) end end); print('e23d-probe: no LAYER_LINKED flag; entity_raw.flags has: ' .. table.concat(names, ',')); return end
    if ll then
      n_ll = n_ll + 1
      local best, cnt = 1e9, 0
      for _, sid in ipairs(e.site_links) do
        local tgt = sid.target or sid.id
        for _, s in ipairs(df.global.world.world_data.sites) do
          if s.id == tgt then cnt = cnt + 1; local d = math.max(math.abs(s.pos.x - fx), math.abs(s.pos.y - fy)); if d < best then best = d end end
        end
      end
      out[#out+1] = ('%s(%s) race=%s sites=%d nearest=%s'):format(raw.code, e.id, tostring(e.race), cnt, best < 1e9 and tostring(best) or '-')
    end
  end
end
print(('e23d-probe: fort site %s at %d,%d; civs=%d layer_linked=%d; %s'):format(tostring(fort), fx, fy, n_civ, n_ll, #out > 0 and table.concat(out, ' | ') or 'NONE'))
