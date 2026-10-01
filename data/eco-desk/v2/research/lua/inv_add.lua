-- INV: add {TOKEN} as an invasive species via the live addNewSpecies path. addNewSpecies has ZERO call sites inside
-- seasonal-wildlife.lua itself and is reachable only from the GUI's "add invasive" handler (act_addnew in
-- scripts/gui/seasonal-wildlife.lua); this calls the exported function directly. opts.force bypasses the
-- cfg.classes[eco] ~= true refusal gate (confirmed by reading the full function body) -- needed because a SAVAGE
-- species is very likely to fall outside whatever classes this fort's cfg has enabled. {CMIN} {CMAX} placeholders.
local sw = reqscript('seasonal-wildlife')
local cfg = sw.loadConfig()
local n, reason = sw.addNewSpecies(cfg, '{TOKEN}', {CMIN}, {CMAX}, { force = true })
sw.saveConfig(cfg)
print(('eco invadd token={TOKEN} added=%d reason=%s'):format(n, tostring(reason)))
