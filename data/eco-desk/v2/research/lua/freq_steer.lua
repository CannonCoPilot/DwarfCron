-- Steer DF's own wave pick toward {SUBJECT}: its raw FREQUENCY set to 100, every other {LAYER}-layer species'
-- FREQUENCY set to 1 (the ECO-F1 pattern). {LAYER} is a seasonal-wildlife LAYER_SET key (land/water/cavern/deep).
-- Originals saved in _G for freq_restore.lua; call this ONCE per cell (a second call would snapshot the already-
-- steered values as "original").
local sw = reqscript('seasonal-wildlife')
local rs = sw.getEmbarkRegions()
local S = rawget(_G, '__eco_freq') or {}
rawset(_G, '__eco_freq', S)
local layerSpecies = {}
for _, pop in ipairs(df.global.world.populations.all) do
  if sw.managedPop(pop, rs, sw.LAYER_SET.{LAYER}) and df.world_population_type[pop.type] == 'Animal' then
    local cr = df.creature_raw.find(pop.race)
    if cr then layerSpecies[cr.creature_id] = true end
  end
end
local n, o = 0, 0
for _, cr in ipairs(df.global.world.raws.creatures.all) do
  if cr.creature_id == '{SUBJECT}' then
    if S[cr.creature_id] == nil then S[cr.creature_id] = cr.frequency end
    cr.frequency = 100; n = n + 1
  elseif layerSpecies[cr.creature_id] then
    if S[cr.creature_id] == nil then S[cr.creature_id] = cr.frequency end
    cr.frequency = 1; o = o + 1
  end
end
print(('eco freq subject={SUBJECT} layer={LAYER} named=%d others=%d'):format(n, o))
