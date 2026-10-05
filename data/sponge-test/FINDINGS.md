# Sponge rig test (5 Oct 2026)

Branch under test: seasonal-wildlife `v7.1-sponge` (d5a98fe + 04ef25a). Rig: DF 53.16 / DFHack 53.16-r2 (CrossOver).
World region15 (seed 717171, SMALLER REGION, aquarium mod v2 ticked); forts SPONGE (16x16, abandoned: embark size
inherited 16x16) and SPONGE2 (4x4 at tile 9,22 off 6,14, CX_EMBARK_SIZE=4). Saves and the v2 installed copy are parked
in ~/Library/Application Support/CrossOver/df-snapshots/sponge-test-0510/ (not in the save dir).

## Results
1. **Castes.** With `[SELECT_CREATURE:SPONGE][CASTE:FEMALE][FEMALE][CASTE:MALE][MALE][SELECT_CASTE:ALL]` the world's
   SPONGE has exactly FEMALE:0 MALE:1 (no leftover DEFAULT), the same layout as vanilla HORSESHOE_CRAB.
   GIANT_SPONGE (COPY_TAGS_FROM:SPONGE) kept one DEFAULT caste: the copy happens before the mod's edit. Fixed in
   04ef25a with its own SELECT_CREATURE pair. SPONGE_MAN left as is.
2. **DF re-reads a world's installed mod copy at every load.** Editing only data/installed_mods/<mod> (2) and
   reloading the SPONGE save changed GIANT_SPONGE's castes on the spot. So an install that refreshes every
   installed copy (as the tool did) would change creature raws under existing worlds. 04ef25a: creature raws go
   only into the copy of the current version; the mod is version 2 with EARLIEST_COMPATIBLE 2.
3. **Breeding (SPONGE2, brook at z99: no salt water inside the 4x4).** Placed 2F+2M per group (place.lua):
   A tame sponges 157-160 (makeown + Domesticated), B wild sponges 161-164, C tame horseshoe crabs 165-168.
   - Tame sponge 158 conceived within 20k ticks in two independent runs (run 2, run 3), gestation ~176k ticks.
   - **Birth: unit 338, SPONGE, caste MALE, mother 158, born year 5 tick 218,060, alive, tame.** 158 conceived again
     at once (timer 199,382).
   - Wild sponges never conceived (0 of 2 females over ~200k ticks). **This was NOT "DF breeds tame animals only"**
     (withdrawn after the user challenged it): their population ref was borrowed from ANOTHER species' entry.
     data/wild-breed/: wild giant sponges with their own population ref 5/5 pregnant, wild mink 2/5, plain/owned
     units bred too; only the borrowed-ref arm stayed 0/5 (twice). Wild animals breed on the map.
   - Control: both tame crab females conceived; the crabs died repeatedly in fresh water (salt-water species placed
     in a brook), so the control shows conception only.
4. **Predation**: code-level only (MODEL.NEVER_PREY, V7.sweep); not exercised on the rig.

## Rig defect found (open)
Fast stepping (fps 1000) hung DF four times, 2-5 min in, at low CPU (blocked, not spinning), no crash log: the
last stderr line is an RPC "Client connection established." that never returns (the step's `chronicler-ui state`
poll). Not the aquarium plugin (run 3, plugin disabled) and not seasonal-wildlife (run 4, both off); not a fixed
tick (run 5 passed the same ranges). Workaround used: save every 20k-tick chunk (run5.sh), resume after a hang.
Earlier rig runs (1 Oct, r2) stepped 300k ticks without this. Logs: run2-run5.log.
