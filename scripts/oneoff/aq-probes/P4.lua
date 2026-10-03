local ok, err = pcall(function()
  local mv = df.global.gps.main_viewport
  local pos = dfhack.gui.getMousePos(); if not pos then print('P4: no cell') return end
  local idx = (pos.x - df.global.window_x) * mv.dim_y + (pos.y - df.global.window_y)
  local marker = dfhack.screen.findGraphicsTile('FLOOR_SAND', 0, 0)
  local orig = mv.screentexpos_background[idx]
  mv.screentexpos_background[idx] = marker
  local seen, n = {}, 0
  local function step()
    n = n + 1
    local v = mv.screentexpos_background[idx]
    seen[#seen + 1] = (v == marker) and 'M' or tostring(v)
    if n < 60 then dfhack.timeout(1, 'frames', step)
    else print('P4 orig', orig, 'marker', marker, 'per-frame:', table.concat(seen, ' ')) end
  end
  dfhack.timeout(1, 'frames', step)
end)
if not ok then print('P4 FAIL: ' .. tostring(err)) end
