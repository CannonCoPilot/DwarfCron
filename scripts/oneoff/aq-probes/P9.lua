local ok, err = pcall(function()
  local mv = df.global.gps.main_viewport
  local pos = dfhack.gui.getMousePos(); if not pos then print('P9: no cell') return end
  local cx, cy, n = pos.x - df.global.window_x, pos.y - df.global.window_y, 0
  local function step()
    n = n + 1
    local a = (n // 8) % 4
    for dx = -4, 4 do for dy = -4, 4 do
      local x, y = cx + dx, cy + dy
      if x >= 0 and y >= 0 and x < mv.dim_x and y < mv.dim_y then
        local i = x * mv.dim_y + y
        local v = mv.screentexpos_liquid_flag[i]
        if v ~= 0 then mv.screentexpos_liquid_flag[i] = (v & ~3) | a end
      end
    end end
    if n < 240 then dfhack.timeout(1, 'frames', step) else print('P9 done') end
  end
  dfhack.timeout(1, 'frames', step)
end)
if not ok then print('P9 FAIL: ' .. tostring(err)) end
