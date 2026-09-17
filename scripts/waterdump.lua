-- dump every surface-water tile (flow_size>=1, not magma) as x,y,z,depth,tiletype, straight from the block arrays
local m = df.global.world.map
local W, H, Z = m.x_count, m.y_count, m.z_count
local out = {}
local n = 0
for _, b in ipairs(m.map_blocks) do
  local bx, by, bz = b.map_pos.x, b.map_pos.y, b.map_pos.z
  for i = 0, 15 do for j = 0, 15 do
    local d = b.designation[i][j]
    if d.flow_size >= 1 and not d.liquid_type then
      n = n + 1
      out[#out+1] = (bx+i)..','..(by+j)..','..bz..','..d.flow_size..','..b.tiletype[i][j]
    end
  end end
end
print('#dims '..W..','..H..','..Z..' water_tiles '..n)
-- print in chunks to keep lines short
for k = 1, #out, 40 do print(table.concat(out, ';', k, math.min(k+39, #out))) end
