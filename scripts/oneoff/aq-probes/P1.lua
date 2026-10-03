local ok, err = pcall(function()
  local T = df.global.texture
  _G.AQP = _G.AQP or {}
  local rev, n = {}, 0
  for pi, p in ipairs(T.page) do
    if p.loaded then
      local w = p.page_dim_x
      for i, tp in ipairs(p.texpos) do
        if rev[tp] == nil then rev[tp] = ('%s[%d](%d,%d)'):format(p.token, pi, i % w, i // w) end
        n = n + 1
      end
    end
  end
  _G.AQP.rev = rev
  print('pages', #T.page, 'texpos entries', n, 'raws', #df.global.enabler.textures.raws,
        'init_texture_size', df.global.enabler.textures.init_texture_size)
  for pi, p in ipairs(T.page) do
    local t = p.token
    if t == 'LIQUIDS' or t:find('AQ') or t == 'MULTILEVEL_OVERLAY' or t == 'FLOOR_GLASS'
       or t:find('^FLOWS') or t:find('^FLOWINGWATER') or t == 'RIVER' or t == 'EVENT_FLOWS' or t == 'RAMP_OVERLAY' then
      print(('page[%d] %-18s loaded=%s dim=%dx%d n=%d first=%s file=%s'):format(pi, t, tostring(p.loaded),
        p.page_dim_x, p.page_dim_y, #p.texpos, (#p.texpos > 0) and tostring(p.texpos[0]) or '-', tostring(p.filename)))
    end
  end
  for _, v in ipairs{2566, 15561, 15577, 15657, 34190, 34196, 34850, 34851, 34852, 34853, 34854} do
    print('texpos', v, '=', rev[v] or '(on no page: DF-internal or DFHack tile)')
  end
end)
if not ok then print('P1 FAIL: ' .. tostring(err)) end
