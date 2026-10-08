#!/bin/bash
# run-season.sh NAME: step the loaded fort to 2,000 ticks past its next season change, in 10k chunks, no mid-run save; logs to data/t1-season/NAME/run.log
set -uo pipefail
name="$1"; cd ~/Claude/Projects/DwarfCron
out=data/t1-season/$name; mkdir -p "$out"; log="$out/run.log"
L() { echo "$(date +%H:%M:%S) $*" | tee -a "$log"; }
q() { CX_PORT=5555 timeout 60 scripts/cx-lifecycle.sh lua "$1" 2>/dev/null | tr -d '\r' | tail -1; }
s0=$(q "print(df.global.cur_season)"); t0=$(q "print(df.global.cur_year_tick)")
target=$(( (t0 / 100800 + 1) * 100800 + 2000 ))
L "start season=$s0 tick=$t0 target_tick=$target"
done_ticks=0; saved=0
while :; do
    t=$(q "print(df.global.cur_year_tick)"); s=$(q "print(df.global.cur_season)")
    [ -z "$t" ] && { L "RPC gave no tick: DF may be hung"; exit 3; }
    left=$(( target - t )); [ "$left" -le 0 ] && break
    n=$(( left < 10000 ? left : 10000 ))
    r=$(CX_PORT=5555 timeout 900 scripts/cx-lifecycle.sh step "$n" 600 2>&1 | tail -1); rc=$?
    L "step $n: $r (rc $rc) season=$s"
    [ $rc -ne 0 ] && { L "step failed"; exit 2; }
    done_ticks=$(( done_ticks + n ))
    # 8 Oct (V73_OCEAN2_AU): rig embarks carry no drink, and a fort with only salt water died of thirst by mid-summer;
    # water and feed every citizen each chunk (cx-load sustain) so a dry site lasts the run
    q "dfhack.run_command('cx-load','sustain')" >/dev/null
    # no mid-run save: DFHack quicksave writes DF's "autosave 1" slot, not the fort's folder (7 Oct)
done
L "end season=$(q 'print(df.global.cur_season)') tick=$(q 'print(df.global.cur_year_tick)')"
