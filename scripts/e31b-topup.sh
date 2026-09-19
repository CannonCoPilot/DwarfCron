#!/bin/bash
# =========================================================================
# E31b — does the post-load top-up cover a feature debit the TOOL made?
# =========================================================================
# Addendum 30 measured DF's own behaviour on LAKE: an embark unit's feature
# debit is undone TWICE — once by a post-load top-up, once by a refund on the
# unit's departure tick — so the entry ends ABOVE its max. It left one check
# open: a unit the TOOL placed also carries a feature reference, so does the
# post-load top-up refund that debit too?
#
# It matters for the water job's budget. If the top-up refunds tool placements,
# stocking a lake is free across a save/reload and the ledger must not double
# count. If it does not, every placement is a permanent draw on a finite pool
# and the job must budget for exhaustion.
#
# This CANNOT be a manifest: the harness's manipulations are Lua and probes
# only, and this needs a real save and a real reload between two reads. So it
# is a scripted by-hand procedure, in the manner of addendum 47.
#
#   ./scripts/e31b-topup.sh [N]      N = animals to place (default 5)
#
# LAKE is backed up first and restored at the end; the throwaway save copy is
# deleted. Run it only when the rig is idle.
# =========================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
N="${1:-5}"
CX=./scripts/cx-lifecycle.sh
TEST_SAVE="E31B"
OUT="data/experiments/E31b/$(date +%Y%m%d-%H%M%S)"

# Wait for the rig rather than refusing outright: a just-SIGTERMed harness can still be in the
# process table for a moment, and an immediate refusal made this script skip itself in a chain.
wait_for_rig() {
    local waited=0 limit=${RIG_WAIT:-1800}
    while pgrep -f "[Pp]ython[^ ]* scripts/cx-experiment.py run" > /dev/null; do
        if [ "$waited" -ge "$limit" ]; then
            echo "GIVING UP: an experiment has been running for ${limit}s." >&2; exit 1
        fi
        [ "$waited" = 0 ] && echo "an experiment is running; waiting for the rig (limit ${limit}s)..."
        sleep 15; waited=$((waited + 15))
    done
    [ "$waited" -gt 0 ] && echo "rig free after ${waited}s"
    return 0
}
wait_for_rig
mkdir -p "$OUT"
exec > >(tee "$OUT/log.txt") 2>&1
echo "== E31b: post-load top-up for tool-placed feature debits, N=$N, $(date +%H:%M:%S)"

# Every stocked FEATURE entry, as token=qty, so a debit and any refund are attributable per entry.
READ='local sw=reqscript("seasonal-wildlife"); local rs=sw.getEmbarkRegions(); local out={}
for i,pop in ipairs(df.global.world.populations.all) do
  local r=pop.population
  if r.feature_idx>=0 and sw.managedPop(pop, rs, {water=true}) and pop.quantity>0 and pop.quantity<10000001 then
    local c=df.creature_raw.find(pop.race)
    out[#out+1]=("%d:%s=%d/%d"):format(i, c and c.creature_id or "?", pop.quantity, pop.quantity_max)
  end
end
table.sort(out); print("e31b-entries: "..table.concat(out," "))'

snap() { echo "--- $1"; $CX lua "$READ" | tee "$OUT/entries-$2.txt"; }

echo "== backing LAKE up"
$CX save-backup LAKE e31b-pre
echo "== loading LAKE"
$CX load LAKE
snap "BEFORE placement" before

echo "== placing $N from the largest stocked feature entry"
$CX lua "local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); local rs=sw.getEmbarkRegions();
local best,bi=nil,-1
for i,pop in ipairs(df.global.world.populations.all) do
  local r=pop.population
  if r.feature_idx>=0 and sw.managedPop(pop, rs, {water=true}) and pop.quantity>0 and pop.quantity<10000001 then
    if not best or pop.quantity>best.quantity then best,bi=pop,i end
  end
end
if not best then print('e31b: NO STOCKED FEATURE ENTRY — wrong fort?') return end
local c=df.creature_raw.find(best.race)
local before=best.quantity
local ids,err=sw.placeFromEntry(cfg,best,$N,nil)
print(('e31b-placed: idx=%d %s qty %d -> %d, placed %d ids=%s err=%s'):format(
  bi, c and c.creature_id or '?', before, best.quantity, #ids, table.concat(ids,','), tostring(err)))" \
  | tee "$OUT/placed.txt"

snap "AFTER placement (the debit)" after-place
echo "== stepping 2000 ticks so the placement settles"
$CX step 2000 120 || true
snap "AFTER 2000 ticks" after-step

echo "== saving a throwaway copy and reloading it — this is the top-up moment"
$CX save "$TEST_SAVE"
$CX load "$TEST_SAVE"
snap "AFTER save+reload" after-reload

echo "== back to title; restoring LAKE and deleting the throwaway"
$CX title || true
# NOTE the asymmetry: save-backup takes TWO args (NAME tag) and save-restore takes ONE
# (NAME.tag). Calling restore with the backup form makes it look for a backup named "LAKE".
$CX save-restore LAKE.e31b-pre
SAVE_DIR="$HOME/Library/Application Support/CrossOver/Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save"
[ -d "$SAVE_DIR/$TEST_SAVE" ] && rm -rf "$SAVE_DIR/$TEST_SAVE" && echo "deleted throwaway save $TEST_SAVE"

echo
echo "== READ IT LIKE THIS"
echo "  the placed entry's quantity at each stage: before -> after-place (down by $N)"
echo "  -> after-reload.  Back UP by $N means the post-load top-up DOES cover tool-placed"
echo "  debits, and stocking is free across a reload.  Still down means every placement is a"
echo "  permanent draw and the water job must budget for pool exhaustion."
diff -y --width 150 "$OUT/entries-after-place.txt" "$OUT/entries-after-reload.txt" || true
