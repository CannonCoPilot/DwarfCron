local sw = reqscript('seasonal-wildlife')
local gw = reqscript('gui/seasonal-wildlife')
local function T(name, f) local t0 = dfhack.getTickCount(); local ok, r = pcall(f); print(('%-34s %6d ms  %s'):format(name, dfhack.getTickCount() - t0, ok and '' or ('ERR ' .. tostring(r):sub(1,160)))) return r end
local cfg = sw.loadConfig()
local rs = T('getEmbarkRegions', function() return sw.getEmbarkRegions() end)
for _, layer in ipairs({'land','water','cavern'}) do
  T('managedPop x all pops ['..layer..']', function() local n=0; for _, pop in ipairs(df.global.world.populations.all) do if sw.managedPop(pop, rs, {[layer]=true}) then n=n+1 end end; print('   managed '..n) end)
end
T('managedPop x all pops [3 layers]', function() local n=0; local L={land=true,water=true,cavern=true}; for _, pop in ipairs(df.global.world.populations.all) do if sw.managedPop(pop, rs, L) then n=n+1 end end; print('   managed '..n) end)
T('units loop onMap/layerOf', function() local n=0; for _, u in ipairs(df.global.world.units.active) do if sw.WILD.onMap(u) then local l=sw.WILD.layerOf(u); n=n+1 end end; print('   wild '..n) end)
gw.show_gui(); local scr = gw.view; local w = scr.subviews[1]
w.subviews.pages:setSelected(4)
for _, mode in ipairs({'pyramid','graph','byseason','bylayer'}) do
  for _, s in ipairs({'all', 1}) do
    T('web '..mode..' season '..tostring(s), function() w.subviews.web_mode:setOption(mode, false); w.subviews.web_season:setOption(s, false); w:refreshWeb() end)
  end
end
w.subviews.pages:setSelected(5)
T('refreshLive (page shown)', function() w:refreshLive() end)
scr:dismiss()
