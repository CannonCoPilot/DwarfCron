local sw = reqscript('seasonal-wildlife')
local cfg = sw.loadConfig()
local pool = sw.buildPool(cfg)
local CF = {'CARNIVORE','LARGE_PREDATOR','BONECARN','AMBUSHPREDATOR','GRAZER','BENIGN','FLIER','AMPHIBIOUS','AQUATIC_UNDERSWIM','IMMOBILE','IMMOBILE_LAND','SWIMS_INNATE','CAN_SWIM_INNATE','VERMIN_HATEABLE','LAYS_EGGS','CURIOUS_BEAST_EATER','CURIOUS_BEAST_GUZZLER','MEANDERER','NO_EAT','NO_DRINK','PREY?'}
local seen = {}
for _, e in ipairs(pool) do if not seen[e.token] then seen[e.token] = true
  local craw = df.creature_raw.find(e.idx)
  local fl = {}
  for _, f in ipairs(CF) do local ok, v = pcall(function() for _, c in ipairs(craw.caste) do if c.flags[f] then return true end end return false end); if ok and v then fl[#fl+1] = f end end
  for _, f in ipairs({'LARGE_ROAMING','VERMIN_FISH','VERMIN_GROUNDER','VERMIN_SOIL','VERMIN_EATER','VERMIN_ROTTER','UBIQUITOUS','EVIL','GOOD','SAVAGE','HAS_ANY_NIGHT_CREATURE','HAS_ANY_MEGABEAST','HAS_ANY_DEMON'}) do local ok, v = pcall(function() return craw.flags[f] end); if ok and v then fl[#fl+1] = f end end
  local bio = {}
  for i = df.biome_type._first_item, df.biome_type._last_item do local nm = df.biome_type[i]; if nm then local ok, v = pcall(function() return craw.flags['BIOME_' .. nm] end); if ok and v then bio[#bio+1] = nm end end end
  print(e.token .. '\t' .. table.concat(fl, ',') .. '\t' .. table.concat(bio, ',') .. '\t' .. craw.cluster_number[0] .. '-' .. craw.cluster_number[1] .. '\t' .. craw.population_number[0] .. '-' .. craw.population_number[1] .. '\t' .. tostring(craw.frequency))
end end
