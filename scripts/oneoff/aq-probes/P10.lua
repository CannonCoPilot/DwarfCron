local ok, err = pcall(function()
  local t0 = os.clock()
  local wx, wy, wz = df.global.window_x, df.global.window_y, df.global.window_z
  local mv = df.global.gps.main_viewport
  local inview, wet = 0, 0
  for _, u in ipairs(df.global.world.units.active) do
    local p = u.pos
    local x, y = p.x - wx, p.y - wy
    if x >= 0 and y >= 0 and x < mv.dim_x and y < mv.dim_y and p.z <= wz and p.z >= wz - 8 then
      inview = inview + 1
      local f = dfhack.maps.getTileFlags(p)
      if f and f.flow_size > 0 and f.liquid_type == df.tile_liquid.Water then wet = wet + 1 end
    end
  end
  print(('P10 active=%d in-view=%d underwater=%d scan=%.2f ms'):format(#df.global.world.units.active, inview, wet,
        (os.clock() - t0) * 1000))
end)
if not ok then print('P10 FAIL: ' .. tostring(err)) end
