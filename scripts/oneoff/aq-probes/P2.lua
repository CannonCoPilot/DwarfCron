local ok, err = pcall(function()
  local g, T = df.global.gps, df.global.texture
  local want = {}
  local toks = {LIQUIDS=1, SW_AQ_LIQUIDS=1, FLOWS=1, FLOWS2=1, FLOWS3=1, FLOWS4=1, SW_AQ_FLOWS1=1,
                RIVER=1, BROOK=1, MULTILEVEL_OVERLAY=1, EVENT_FLOWS=1, FLOOR_SAND=1}
  for pi, p in ipairs(T.page) do
    if p.loaded and toks[p.token] then
      local w = p.page_dim_x
      for i, tp in ipairs(p.texpos) do want[tp] = ('%s[%d](%d,%d)'):format(p.token, pi, i % w, i // w) end
    end
  end
  want[2566] = want[2566] or 'FILL_2566'
  local sizes = {136, 11346, 20192, 4508, 60, 128, 458, 8340, 101, 276, 6845}
  local hits, t0 = 0, os.clock()
  for k, n in ipairs(sizes) do
    local arr = g['texture_indices' .. k]
    for i = 0, n - 1 do
      local v = arr[i]
      if want[v] then
        hits = hits + 1
        if hits <= 500 then print(('texture_indices%d[%d] = %d  %s'):format(k, i, v, want[v])) end
      end
    end
  end
  print(('hits=%d scan=%.1f ms black_background_texpos=%d'):format(hits, (os.clock() - t0) * 1000,
        g.black_background_texpos[0]))
end)
if not ok then print('P2 FAIL: ' .. tostring(err)) end
