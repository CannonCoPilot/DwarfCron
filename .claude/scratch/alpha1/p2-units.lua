local sw = reqscript('seasonal-wildlife')
local cfg = sw.loadConfig()
local g = sw.loadGroups()
local tracked = {}
for _, grp in ipairs(g.groups) do for _, id in ipairs(grp.ids) do tracked[id] = grp.token .. (grp.resident and '/res' or '/gated') end end
local by = {}
for _, u in ipairs(df.global.world.units.active) do
  if sw.WILD.onMap(u) then
    local tok = df.creature_raw.find(u.race).creature_id
    local lay = sw.WILD.layerOf(u) or '?'
    local key = sw.keyFor(lay == 'surface' and 'land' or lay, tok)
    local k = lay .. ' ' .. tok
    local b = by[k] or { n = 0, tr = 0, flagged = 0, key = key }
    b.n = b.n + 1
    if tracked[u.id] then b.tr = b.tr + 1 end
    if u.flags2.roaming_wilderness_population_source then b.flagged = b.flagged + 1 end
    by[k] = b
  end
end
local ks = {}; for k in pairs(by) do ks[#ks+1] = k end; table.sort(ks)
local tot, ttr = 0, 0
for _, k in ipairs(ks) do
  local b = by[k]; tot = tot + b.n; ttr = ttr + b.tr
  local a = cfg.allow[b.key]; local s = cfg.assign[b.key]
  print(('%-40s n=%-3d tracked=%-3d src_flag=%-3d allow=%-5s seasons=%s'):format(k, b.n, b.tr, b.flagged, tostring(a), s and table.concat(s, '') or '-'))
end
print(('TOTAL wild on map %d, tracked %d; groups tracked %d'):format(tot, ttr, #g.groups))
for _, t in ipairs({'GIANT_RHINOCEROS','RHINOCEROS','GIANT_JACKAL','JACKAL','RHINOCEROS_MAN','AARDVARK','BIRD_EAGLE'}) do
  print(t .. ': allow=' .. tostring(cfg.allow[t]) .. ' seasons=' .. (cfg.assign[t] and table.concat(cfg.assign[t], '') or '-'))
end
