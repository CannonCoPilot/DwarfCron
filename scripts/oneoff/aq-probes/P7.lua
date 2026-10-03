local ok, err = pcall(function()
  local g = df.global.gps
  local mv, lv = g.main_viewport, g.lower_viewport[0]
  local pos = dfhack.gui.getMousePos(); if not pos then print('P7: no cell') return end
  local idx = (pos.x - df.global.window_x) * mv.dim_y + (pos.y - df.global.window_y)
  local F = {'screentexpos_background', 'screentexpos_background_two', 'screentexpos_high_flow',
             'screentexpos_liquid_flag', 'screentexpos_interface'}
  local rev = (_G.AQP or {}).rev or {}
  local hist, n, ph0 = {}, 0, df.global.map_renderer.tick_phase
  local function rec(tag, vp)
    if not vp or not vp.flag.active then return end
    for _, f in ipairs(F) do
      local o, v = pcall(function() return vp[f][idx] end)
      if o then local k = tag .. '.' .. f; hist[k] = hist[k] or {}; hist[k][v] = (hist[k][v] or 0) + 1 end
    end
  end
  local function step()
    n = n + 1; rec('main', mv); rec('low0', lv)
    if n < 120 then dfhack.timeout(1, 'frames', step) return end
    for k, t in pairs(hist) do
      local s = {}
      for v, c in pairs(t) do s[#s + 1] = ('%d%s x%d'):format(v, rev[v] and ('<' .. rev[v] .. '>') or '', c) end
      print(k, table.concat(s, ' | '))
    end
    print('tick_phase', ph0, '->', df.global.map_renderer.tick_phase, 'cur_tick_count', df.global.map_renderer.cur_tick_count)
  end
  dfhack.timeout(1, 'frames', step)
end)
if not ok then print('P7 FAIL: ' .. tostring(err)) end
