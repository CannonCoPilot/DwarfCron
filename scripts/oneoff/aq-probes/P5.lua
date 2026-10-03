-- Edit ARR/IDX from P2's output. NEW defaults to the mod's UNDERWATER_7. Set RESTORE=true to undo.
local ARR, IDX, NEW, RESTORE = 'texture_indices3', 0, nil, false
local ok, err = pcall(function()
  local g = df.global.gps
  _G.AQ_SLOT = _G.AQ_SLOT or {}
  local key = ARR .. ':' .. IDX
  if RESTORE then
    local old = _G.AQ_SLOT[key]
    if old then g[ARR][IDX] = old; _G.AQ_SLOT[key] = nil; print('P5 restored', key, old) else print('P5 nothing saved', key) end
  else
    NEW = NEW or dfhack.screen.findGraphicsTile('SW_AQ_LIQUIDS', 0, 0)
    if _G.AQ_SLOT[key] == nil then _G.AQ_SLOT[key] = g[ARR][IDX] end
    g[ARR][IDX] = NEW
    print('P5 set', key, 'from', _G.AQ_SLOT[key], 'to', NEW)
  end
  if g.force_full_display_count < 2 then g.force_full_display_count = 2 end
end)
if not ok then print('P5 FAIL: ' .. tostring(err)) end
