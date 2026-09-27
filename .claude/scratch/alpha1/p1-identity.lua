local site = dfhack.world.getCurrentSite()
local name = site and dfhack.translation.translateName(site.name, true) or '?'
local sw = reqscript('seasonal-wildlife')
local cfg = sw.loadConfig()
local n_allow, n_block, n_assign, n_noseason = 0, 0, 0, 0
for k, v in pairs(cfg.allow or {}) do if v then n_allow = n_allow + 1 else n_block = n_block + 1 end end
for k, v in pairs(cfg.assign or {}) do n_assign = n_assign + 1 end
local lay = {}
for k, v in pairs(cfg.layers or {}) do lay[#lay+1] = k .. '=' .. tostring(v) end
local pats = {}
for k, v in pairs(cfg.patterns or {}) do pats[#pats+1] = k .. '=' .. tostring(v) end
print(('site=%s  year=%d tick=%d season=%d paused=%s'):format(name, df.global.cur_year, df.global.cur_year_tick, df.global.cur_season, tostring(df.global.pause_state)))
print(('cfg: enabled=%s initialized=%s version=%s layers{%s} patterns{%s}'):format(tostring(cfg.enabled), tostring(cfg.initialized), tostring(cfg.version), table.concat(lay, ' '), table.concat(pats, ' ')))
print(('allow true=%d false=%d  assign entries=%d'):format(n_allow, n_block, n_assign))
local g = cfg.groups or {}
print(('groups: enabled=%s coupling=%s cohesion=%s cavern=%s cavern_max=%s max_concurrent=%s pack=%s gap=%s-%s'):format(tostring(g.enabled), tostring(g.coupling), tostring(g.cohesion), tostring(g.cavern), tostring(g.cavern_max), tostring(g.max_concurrent), tostring(g.pack), tostring(g.gap_min), tostring(g.gap_max)))
local e = cfg.ecology or {}
print(('ecology: enabled=%s cadence=%s far_tiles=%s far_ticks=%s radius=%s livestock=%s'):format(tostring(e.enabled), tostring(e.cadence), tostring(e.far_tiles), tostring(e.far_ticks), tostring(e.radius), tostring(e.livestock)))
local ir = cfg.irruption or {}
print(('irruption: enabled=%s threshold=%s'):format(tostring(ir.enabled), tostring(ir.threshold)))
print('fuse: ' .. tostring(sw.fuseStatus and sw.fuseStatus() or '-'))
print('undo depth: ' .. tostring(sw.UNDO.depth()))
local L = sw.LEDGER.load(); local kinds = {}
for _, en in ipairs(L.entries or {}) do kinds[en.k] = (kinds[en.k] or 0) + 1 end
local ks = {}; for k, v in pairs(kinds) do ks[#ks+1] = k .. '=' .. v end; table.sort(ks)
print(('ledger: %d entries held, %d ever; kinds %s'):format(#(L.entries or {}), L.count or -1, table.concat(ks, ' ')))
print('water: ' .. tostring(sw.WATER and sw.WATER.status and sw.WATER.status() or '-'))
print('caverns found: ' .. tostring(sw.cavernsFound and select(1, sw.cavernsFound()) or '-'))
