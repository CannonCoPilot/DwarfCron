-- Item 6: on a good or evil fort, what the tool reads and manages. Prints the embark alignment (V7.alignment), every
-- GOOD/EVIL wildlife species in the pool with its class, lock state and layer, then (tag {TAG}) the GOOD/EVIL wild units
-- on the map and whether each is a managed (natural, unlocked) species.
local sw = reqscript('seasonal-wildlife'); local cfg = sw.loadConfig()
local ok, a = pcall(sw.V7.alignment)
print(('eco align tag={TAG} ok=%s good=%s evil=%s tiles=%s'):format(tostring(ok), tostring(ok and a and a.good), tostring(ok and a and a.evil), tostring(ok and a and a.tiles)))
local by = {}
for _, e in ipairs(sw.buildPool(cfg)) do by[e.token] = e end
local n, m = 0, 0
for tok, e in pairs(by) do
  local cr = df.creature_raw.find(e.idx or -1)
  if not cr then for _, c in ipairs(df.global.world.raws.creatures.all) do if c.creature_id == tok then cr = c break end end end
  if cr and (cr.flags.GOOD or cr.flags.EVIL) then
    n = n + 1; local cls = sw.ecoOf(cfg, cr); if cls == 'natural' and not e.locked then m = m + 1 end
    if '{TAG}' == 'pre' then print(('eco alignsp tok=%s good=%s evil=%s class=%s locked=%s layer=%s inEmbark=%s'):format(tok, tostring(cr.flags.GOOD), tostring(cr.flags.EVIL), tostring(cls), tostring(e.locked), tostring(e.layer), tostring(e.inEmbark))) end
  end
end
local onmap, managed = 0, 0
for _, u in ipairs(df.global.world.units.active) do
  if sw.WILD.onMap(u) then local cr = df.creature_raw.find(u.race); if cr and (cr.flags.GOOD or cr.flags.EVIL) then
    onmap = onmap + 1; local e = by[cr.creature_id]; if e and not e.locked and sw.ecoOf(cfg, cr) == 'natural' then managed = managed + 1 end
    print(('eco alignunit tag={TAG} tok=%s managed=%s'):format(cr.creature_id, tostring(e and not e.locked and sw.ecoOf(cfg, cr) == 'natural'))) end end
end
print(('eco alignsum tag={TAG} pool_aligned=%d pool_managed=%d onmap_aligned=%d onmap_managed=%d'):format(n, m, onmap, managed))
