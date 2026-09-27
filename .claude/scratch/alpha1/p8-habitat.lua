local want = {'SHARK_GREAT_WHITE','FISH_TUNA_BLUEFIN','GIANT_CUTTLEFISH','SEA_MONSTER','SEA_SERPENT','GIGANTIC SQUID','GIANT_NAUTILUS','CRAB','GIANT_CRAB','HORSESHOE_CRAB','CROCODILE_CAVE','POND_GRABBER','HIPPO','GIANT_HIPPO','HIPPO_MAN','RIVER OTTER','GIANT_OTTER','OTTER_MAN','PLATYPUS','CROCODILE_SALTWATER','ALLIGATOR','BEAVER','CAPYBARA','TOAD','BIRD_ALBATROSS','BIRD_OSPREY','BIRD_PELICAN','BIRD_PENGUIN','BIRD_HERON','BIRD_EAGLE','BIRD_KESTREL','WALRUS','HARP_SEAL','SEA OTTER','OLM','FISH_CAVE','DINGO','WOLF'}
local F = {'CANNOT_BREATHE_AIR','CAN_BREATHE_WATER','AQUATIC_UNDERSWIM','IMMOBILE_LAND','CAN_SWIM_INNATE','SWIMS_INNATE','FLIER','NO_DRINK','HUNTS_VERMIN','DIVE_HUNTS_VERMIN','CARNIVORE','BONECARN','LARGE_PREDATOR','BENIGN','VERMIN_FISH_FLAG?'}
local have = {}
for i = df.caste_raw_flags._first_item, df.caste_raw_flags._last_item do local n = df.caste_raw_flags[i]; if n then have[n] = true end end
print('flag names exist: HUNTS_VERMIN=' .. tostring(have.HUNTS_VERMIN) .. ' DIVE_HUNTS_VERMIN=' .. tostring(have.DIVE_HUNTS_VERMIN) .. ' SWIMS_INNATE=' .. tostring(have.SWIMS_INNATE) .. ' SWIMS_LEARNED=' .. tostring(have.SWIMS_LEARNED))
local idx = {}
for _, c in ipairs(df.global.world.raws.creatures.all) do idx[c.creature_id] = c end
for _, t in ipairs(want) do
  local c = idx[t]
  if c then
    local fl = {}
    for _, f in ipairs(F) do if have[f] then for _, ca in ipairs(c.caste) do if ca.flags[f] then fl[#fl+1] = f; break end end end end
    local w, l = {}, 0
    for i = df.biome_type._first_item, df.biome_type._last_item do local nm = df.biome_type[i]; if nm then local ok, v = pcall(function() return c.flags['BIOME_' .. nm] end); if ok and v then if nm:find('^OCEAN') or nm:find('^RIVER') or nm:find('^LAKE') or nm:find('^POOL') or nm:find('SUBTERRANEAN_WATER') then w[#w+1] = nm:gsub('_TEMPERATE',''):gsub('_TROPICAL',''):gsub('WATER$','') else l = l + 1 end end end end
    local ws = {}; local seen = {}; for _, x in ipairs(w) do if not seen[x] then seen[x] = true; ws[#ws+1] = x end end
    print(('%-20s %s | water:%s | land-biomes:%d | ug:%d-%d'):format(t, table.concat(fl, ','), table.concat(ws, '/'), l, c.underground_layer_min, c.underground_layer_max))
  else print(t .. ' (not in this world)') end
end
