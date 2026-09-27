local gw=reqscript('gui/seasonal-wildlife'); local sw=reqscript('seasonal-wildlife')
local function T(n,f) local t0=dfhack.getTickCount(); f(); print(('%-22s %5d ms  heap %d KB'):format(n, dfhack.getTickCount()-t0, math.floor(collectgarbage('count')))) end
print('heap at start KB', math.floor(collectgarbage('count')))
gw.show_gui(); local w=gw.view.subviews[1]
T('live (fresh)', function() w:refreshLive() end)
T('buildPool (fresh)', function() sw.buildPool(sw.loadConfig()) end)
_G.__sw_ballast = {}
for i=1,400000 do _G.__sw_ballast[i]={i,i+1} end
print('heap with ballast KB', math.floor(collectgarbage('count')))
T('live (ballast)', function() w:refreshLive() end)
T('buildPool (ballast)', function() sw.buildPool(sw.loadConfig()) end)
T('loadConfig (ballast)', function() sw.loadConfig() end)
T('vermin (ballast)', function() w:refreshVermin() end)
_G.__sw_ballast=nil; collectgarbage()
gw.view:dismiss()
