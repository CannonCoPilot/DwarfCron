local ok, err = pcall(function()
  local g = df.global.gps
  local function hist(vp, tag)
    if not vp or not vp.flag.active then return end
    local lf, n = vp.screentexpos_liquid_flag, vp.dim_x * vp.dim_y
    local anim, typ, edge = {}, {}, 0
    for i = 0, n - 1 do
      local v = lf[i]
      if v ~= 0 then
        anim[v & 3] = (anim[v & 3] or 0) + 1
        typ[(v >> 5) & 15] = (typ[(v >> 5) & 15] or 0) + 1
        if (v >> 9) ~= 0 then edge = edge + 1 end
      end
    end
    local a, t = {}, {}
    for k, c in pairs(anim) do a[#a + 1] = k .. ':' .. c end
    for k, c in pairs(typ) do t[#t + 1] = k .. ':' .. c end
    print(tag, 'anim{' .. table.concat(a, ' ') .. '}', 'type{' .. table.concat(t, ' ') .. '}', 'edged', edge)
  end
  hist(g.main_viewport, 'main')
  for k = 0, 7 do hist(g.lower_viewport[k], 'low' .. k) end
end)
if not ok then print('P8 FAIL: ' .. tostring(err)) end
