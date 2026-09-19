#!/bin/bash
# =========================================================================
# E23b diagnostic — why did maxed cavern irritation fire no invasion?
# =========================================================================
# E23b pinned all three cavern features at 100,000 (the documented maximum,
# "divide by 10k for attack chance") and held them there for TWO SEASONS with
# no decay at all — irritation_sum sat at exactly 300,000 across 65 samples —
# and `invaders` never left zero.
#
# The likeliest missing precondition is that THE FORT HAS NEVER OPENED THE
# CAVERNS. df-structures carries plotinfo.flags.did_first_cavern_announcement,
# "required for CAVERNS_OPENED", and CTRL is a seven-dwarf fort that has almost
# certainly never dug that deep. If DF only sends cavern dwellers at a fort
# that has breached their layer, then irritation is necessary and not
# sufficient, and addendum 49's invasion exclusion cannot be exercised on CTRL
# at all — it needs a fort with an open cavern.
#
# Reads only; changes nothing. Run when the rig is idle.
# =========================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
CX=./scripts/cx-lifecycle.sh
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
$CX load CTRL
$CX lua 'local pi=df.global.plotinfo
local function flag(n) local ok,v=pcall(function() return pi.flags[n] end); return ok and tostring(v) or "ABSENT" end
print(("e23b-diag: did_first_cavern_announcement=%s  did_first_caravan_announcement=%s"):format(
  flag("did_first_cavern_announcement"), flag("did_first_caravan_announcement")))
local mf=df.global.world.features.map_features
local n,parts=0,{}
for i,f in ipairs(mf) do
  if df.feature_init_subterranean_from_layerst:is_instance(f) then
    n=n+1
    local ok,fl=pcall(function() return f.flags.whole end); parts[#parts+1]=("depth%d irr=%d flags=%s"):format(f.start_depth, f.feature.irritation_level, ok and tostring(fl) or "n/a")
  end
end
print(("e23b-diag: %d cavern features | %s"):format(n, table.concat(parts, " | ")))
local cd=pi.main.custom_difficulty
print(("e23b-diag: cavern_dweller_max_attackers=%d cavern_dweller_scale=%d wild_irritate_min=%d wild_sens=%d"):format(
  cd.cavern_dweller_max_attackers, cd.cavern_dweller_scale, cd.wild_irritate_min, cd.wild_sens))
local q=0
for _,ev in ipairs(df.global.timed_events) do
  if df.timed_event_type[ev.type]=="FeatureAttack" then q=q+1 end
end
print(("e23b-diag: %d FeatureAttack events currently queued; %d timed events total"):format(q, #df.global.timed_events))'
$CX title || true
echo
echo "== READ IT LIKE THIS"
echo "  did_first_cavern_announcement=false -> the fort has never opened the caverns, which is the"
echo "     likeliest reason no FeatureAttack is ever queued. Irritation is necessary, not sufficient,"
echo "     and E23b must be re-run on a fort with a breached cavern (or the cavern dug open first)."
echo "  =true with zero queued events -> irritation genuinely does not drive the roll and the"
echo "     trigger is something else again."
