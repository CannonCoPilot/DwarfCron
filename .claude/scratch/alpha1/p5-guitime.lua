local gw = reqscript('gui/seasonal-wildlife')
local function T(name, f) local t0 = dfhack.getTickCount(); local ok, r = pcall(f); print(('%-26s %6d ms  %s'):format(name, dfhack.getTickCount() - t0, ok and '' or ('ERR ' .. tostring(r):sub(1,160)))) return r end
T('show_gui (open window)', function() gw.show_gui() end)
local scr = gw.view
local w = scr and scr.subviews and scr.subviews[1]
print('win found: ' .. tostring(w ~= nil))
if w then
  T('rebuildData', function() w:rebuildData() end)
  T('computeCounts', function() return w:computeCounts() end)
  T('refresh (roster)', function() w:refresh() end)
  for _, m in ipairs({'refreshOverview','refreshSeasons','refreshWeb','refreshLive','refreshLayers','refreshVermin','refreshLedger'}) do
    if w[m] then T(m, function() w[m](w) end) end
  end
end
T('dismiss', function() scr:dismiss() end)
