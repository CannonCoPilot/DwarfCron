local ok, err = pcall(function()
  local g = df.global.gps
  local pos = dfhack.gui.getMousePos()
  if not pos then print('P3: no map cell under mouse') return end
  local mv = g.main_viewport
  local x, y = pos.x - df.global.window_x, pos.y - df.global.window_y
  local idx = x * mv.dim_y + y
  local rev = (_G.AQP or {}).rev or {}
  local L = {'screentexpos_background', 'screentexpos_background_two', 'screentexpos_building_one',
             'screentexpos_item', 'screentexpos', 'screentexpos_building_two', 'screentexpos_high_flow',
             'screentexpos_top_shadow', 'screentexpos_signpost', 'screentexpos_up_creature',
             'screentexpos_designation', 'screentexpos_interface'}
  local function liq(v) return ('anim=%d lvl=%d type=%d edge n%d s%d w%d e%d'):format(v & 3, (v >> 2) & 7,
    (v >> 5) & 15, (v >> 9) & 15, (v >> 13) & 15, (v >> 17) & 15, (v >> 21) & 15) end
  local function get(vp, f) local o, v = pcall(function() return vp[f][idx] end) return o and v or nil end
  local function dump(tag, vp)
    if not vp then print(tag, 'nil') return end
    if not vp.flag.active then print(tag, 'inactive') return end
    local out = {}
    for _, f in ipairs(L) do
      local v = get(vp, f)
      local nm = (f == 'screentexpos') and 'creature' or (f:gsub('screentexpos_', ''))
      if v and v ~= 0 then out[#out + 1] = ('%s=%d%s'):format(nm, v,
        rev[v] and ('<' .. rev[v] .. '>') or '') end
    end
    local lf, rf, ff = get(vp, 'screentexpos_liquid_flag'), get(vp, 'screentexpos_ramp_flag'),
                       get(vp, 'screentexpos_floor_flag')
    if lf and lf ~= 0 then out[#out + 1] = 'liq[' .. liq(lf) .. ']' end
    if rf and rf ~= 0 then out[#out + 1] = ('ramp=0x%x type=%d'):format(rf, rf & 255) end
    if ff and ff ~= 0 then out[#out + 1] = ('floorflag=0x%x'):format(ff) end
    print(tag, #out > 0 and table.concat(out, ' ') or '(all zero)')
  end
  print(('cell map=(%d,%d,%d) vp=(%d,%d) idx=%d dims=%dx%d'):format(pos.x, pos.y, pos.z, x, y, idx, mv.dim_x, mv.dim_y))
  dump('main  ', mv)
  for k = 0, 7 do dump('lower' .. k, g.lower_viewport[k]) end
  local wv = df.global.world.viewport
  print('world.viewport under_limit start/dx/dy', wv.under_limit_start, wv.under_limit_dx, wv.under_limit_dy)
  if x >= 0 and y >= 0 and x < wv.under_limit_dx and y < wv.under_limit_dy then
    local o, v = pcall(function() return wv.under_limit[x * wv.under_limit_dy + y] end)
    print('under_limit[cell] (layout guessed x*dy+y)', o and v or 'unreadable')
  end
  print('z_levels_to_show', df.global.d_init.display.number_of_lower_elevations_shown)
end)
if not ok then print('P3 FAIL: ' .. tostring(err)) end
