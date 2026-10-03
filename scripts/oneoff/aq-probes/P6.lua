-- Exchanges raws[A] <-> raws[B]. Both must be DF-loaded raws tiles; never a DFHack loadTileset/createTile handle.
-- Run again to swap back. Swap back before unloading the world.
local A, B = nil, nil
local ok, err = pcall(function()
  local T, tex = df.global.texture, df.global.enabler.textures
  if not A then for _, p in ipairs(T.page) do if p.token == 'LIQUIDS' and p.loaded then A = p.texpos[0]; break end end end
  B = B or dfhack.screen.findGraphicsTile('SW_AQ_LIQUIDS', 0, 0)
  print('A', A, 'B', B, 'raws', #tex.raws, 'init_texture_size', tex.init_texture_size)
  local pa, pb = tex.raws[A], tex.raws[B]
  print('before', tostring(pa), tostring(pb))
  tex.raws[A], tex.raws[B] = pb, pa
  print('after ', tostring(tex.raws[A]), tostring(tex.raws[B]))
  df.global.gps.do_clean_tile_cache = true
  df.global.gps.force_full_display_count = 2
  _G.AQ_SWAPPED = not _G.AQ_SWAPPED
  print('P6 swapped state', _G.AQ_SWAPPED)
end)
if not ok then print('P6 FAIL: ' .. tostring(err)) end
