#!/bin/sh
# Wait silently for the next event in a chain: a new '===' line in the chain log, or an abort/FAIL/traceback in the
# sec7 log; print it and exit (re-launch after each). Also exits if DF has crashed (a new crashlog) or the chain died.
cd /Users/nathanielcannon/Claude/Projects/DwarfCron; . scripts/cx-config.sh
C=data/logs/chain-rc.log; S=data/logs/sec7-rc.log
nc=$(wc -l < $C); ns=$(wc -l < $S); ncr=$(ls "$DF_DIR/crashlogs" | wc -l)
while :; do
  mc=$(wc -l < $C); ms=$(wc -l < $S)
  [ "$mc" -gt "$nc" ] && { h=$(tail -n +$((nc+1)) $C | grep "^===" | cut -c1-400); nc=$mc; [ -n "$h" ] && { echo "$h"; exit 0; }; }
  [ "$ms" -gt "$ns" ] && { h=$(tail -n +$((ns+1)) $S | grep -E "ABORTED|MANIP-FAIL|Traceback|\[FAIL\]|=== sec7" | cut -c1-300); ns=$ms; [ -n "$h" ] && { echo "$h"; exit 0; }; }
  [ "$(ls "$DF_DIR/crashlogs" | wc -l)" -gt "$ncr" ] && { echo "DF CRASHED: $(ls -t "$DF_DIR/crashlogs" | head -1)"; exit 0; }
  pgrep -f chain-rc.sh >/dev/null || { echo "chain-rc no longer running; last: $(tail -1 $C)"; exit 0; }
  sleep 20
done
