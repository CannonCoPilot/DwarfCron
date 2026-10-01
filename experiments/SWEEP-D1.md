# D1: x3 pack bonus desk check (SWEEP-design.md row i)

**Status:** desk only, 30 Sep 2026. No rig run. Files-only: imports `data/eco-desk/v2/guilds/{roster2,run2}.py`
(`build`, `components`, `derive`, `V1_EMBARKS`, `V22`) from a standalone script; neither file is modified on disk (both
already carry unrelated in-progress edits in this worktree, per `git status`).

**What this answers:** does the builder's roster change at all when the pack-bonus pick-weight multiplier
(`Cfg.pack_pref`, `pack_pred_only=True` under v2.2) is set to 1, 2, 3 (current) or 5 -- design row i's rule: *"Goes
to the rig (SW7) only if CTRL's roster changes."*

## Method

- Base config: `run2.V22` (the builder's current config, `pack_pref=3.0` already -- confirmed `== 3.0` before the
  sweep ran), varied only by `pack_pref in {1.0, 2.0, 3.0, 5.0}`.
- Scope: the design's 7 embarks (`run2.V1_EMBARKS`, the first 7 of `roster2.EMBARKS`) x 4 seasons x 20 seeds
  (`range(1, 21)`), matching `run2.py`'s own sweep convention.
- Layers: `land, flying, ocean, lake, river` (surface, over the 7 embarks) and `cav1, cav2, cav3, cavw1, cavw2,
  cavw3, deep` (caverns/deep, embark-independent `'UNDER'` jobs in `run2.jobs()`, so one set of builds covers every
  fort with caverns).
- **CTRL** = `('TEMP_GRASS_FOREST', 'land')` -- `roster2.py`'s own `__main__` default embark/layer, the plain
  temperate grass+forest land embark, first of the 7, matching the land arena every CTRL-fort ECO block uses.
- **BOATS's water** = `('OCEAN_SHORE', 'ocean')` + `('LAKE_RIVER', 'lake')` + `('LAKE_RIVER', 'river')`. The one
  embark `roster2.py` comments "like BOATS" (`TROP_OCEAN_SALTRIVER`) is an *extra*, outside the design's 7-embark
  scope, so it is not used; these three are the nearest water-layer stand-ins for BOATS's water within the 7, stated
  here rather than assumed silently.
- **BOATS's caverns** = `cav1, cav2, cav3` (embark-independent; the same rosters eco-run.py's `BOATS_CAVES` 1/2/3
  would see).
- "Roster changes" = the exact species-id set returned for a given `(embark, layer, season, seed)` differs at all
  from the `pack_pref=3` (current) build at the same key -- not a summary-statistic threshold.

## Results: summary metrics, 7 embarks x 4 seasons x 20 seeds

### Surface (land/flying/ocean/lake/river, V1 embarks)

| pack bonus | rosters built | mean size | isolated/split | pack hunts | herd hunted | pack AND herd | DF-actable edges | DF-actable + untested | predator share of arrivals |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2,800 (1,360 non-empty) | 9.59 | 0.0% | 56.8% | 93.8% | 56.5% | 35.7% | 53.3% | 0.175 |
| 2 | 2,800 (1,360) | 9.59 | 0.1% | 67.4% | 93.8% | 67.1% | 36.1% | 53.4% | 0.174 |
| **3 (current)** | 2,800 (1,360) | 9.59 | 0.1% | 72.8% | 93.9% | 72.6% | 36.2% | 53.5% | 0.174 |
| 5 | 2,800 (1,360) | 9.59 | 0.0% | 76.7% | 93.5% | 76.1% | 36.4% | 53.6% | 0.174 |

### Caverns + deep (cav1-3, cavw1-3, deep; embark-independent)

| pack bonus | rosters built | mean size | isolated/split | pack hunts | herd hunted | pack AND herd | DF-actable edges | DF-actable + untested | predator share of arrivals |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 560 (480 non-empty) | 7.01 | 0.0% | 46.5% | 97.7% | 46.5% | 60.6% | 79.4% | 0.225 |
| 2 | 560 (480) | 7.01 | 0.0% | 50.6% | 97.7% | 50.6% | 60.7% | 79.6% | 0.226 |
| **3 (current)** | 560 (480) | 7.01 | 0.0% | 56.9% | 98.3% | 56.9% | 60.2% | 79.5% | 0.229 |
| 5 | 560 (480) | 7.00 | 0.0% | 61.9% | 99.4% | 61.9% | 60.2% | 79.6% | 0.230 |

**Reading:** isolation, DF-actable-edge share and arrival (FREQUENCY) predator share are flat across all four levels
(within noise) -- the lever does not change what gets *written*, only what gets *picked*. Pack-hunt presence is not
flat: it rises monotonically and substantially with the bonus, both surface (56.8% to 76.7%, +19.9 points land 1 to
5) and underground (46.5% to 61.9%, +15.4 points). "Pack AND herd" tracks pack share almost exactly, since herd
presence is already near-ceiling (93-99%) at every level.

## Results: exact roster identity vs the current level (pack_pref = 3)

For every `(embark/proxy, layer, season, seed)` key, is the built roster (species-id set) byte-identical to the
pack_pref=3 build at that same key?

| subject | keys compared | changed at level 1 | changed at level 2 | changed at level 5 |
|---|---|---|---|---|
| CTRL (`TEMP_GRASS_FOREST`/land) | 80 (4 seasons x 20 seeds) | 80 (100%) | 80 (100%) | 80 (100%) |
| BOATS water proxy (`OCEAN_SHORE`/ocean, `LAKE_RIVER`/lake+river) | 240 | 240 (100%) | 240 (100%) | 240 (100%) |
| BOATS cavern (cav1-3, embark-independent) | 240 | 240 (100%) | 238 (99.2%) | 239 (99.6%) |

Every subject's roster changes at essentially every seed once the bonus moves off 3, in either direction -- this is
not seed noise or a border effect at one level; it holds at 1, 2 and 5 alike, and the pack-hunt-presence trend above
moves monotonically with it.

## Verdict (design row i: "Goes to the rig (SW7) only if CTRL's roster changes")

CTRL's roster changes at every level tested (1, 2, 5) against the current value (3): 100% of the 80 embark/season/seed keys differ, and pack-hunt presence moves monotonically from 56.8% (level 1) to 76.7% (level 5), a 19.9-point swing.
BOATS's roster changes the same way, in both its water proxy (100% of 240 keys) and its caverns (99.2-99.6% of 240 keys), so the effect is not CTRL-specific.
**SW7 BUILDER is needed**: build `scripts/oneoff/chain-night3.sh` runs it (pack bonus 1 / 3 / 5 rosters applied, CTRL natural, 50,400 t, per design section 3 row 7, ~38 min) right after SW4-SW6.
