#!/bin/sh
# Wait silently for the next replicate or block boundary in the sec7 chain (a new 'rep N: order' line in the newest
# eco log, a block start/end/abort in the sec7 log, the chain's end) or a DF crash; print it and exit.
cd /Users/nathanielcannon/Claude/Projects/DwarfCron; . scripts/cx-config.sh
S=data/logs/sec7-rc.log
E=$(ls -t data/alpha4-sec7/2*/eco/log.txt 2>/dev/null | head -1)
ns=$(wc -l < $S); ne=$(wc -l < "$E"); ncr=$(ls "$DF_DIR/crashlogs" | wc -l)
while :; do
  ms=$(wc -l < $S); E2=$(ls -t data/alpha4-sec7/2*/eco/log.txt | head -1); [ "$E2" != "$E" ] && { E=$E2; ne=0; }
  me=$(wc -l < "$E")
  [ "$ms" -gt "$ns" ] && { h=$(tail -n +$((ns+1)) $S | grep -E "== S7_|: [0-9.]+ min$|ABORTED|MANIP-FAIL|Traceback|=== sec7" | cut -c1-200); ns=$ms; [ -n "$h" ] && { echo "$h"; exit 0; }; }
  [ "$me" -gt "$ne" ] && { h=$(tail -n +$((ne+1)) "$E" | grep -E "rep [0-9]+: order" | cut -c1-160); ne=$me; [ -n "$h" ] && { echo "$h"; exit 0; }; }
  [ "$(ls "$DF_DIR/crashlogs" | wc -l)" -gt "$ncr" ] && { echo "DF CRASHED: $(ls -t "$DF_DIR/crashlogs" | head -1)"; exit 0; }
  pgrep -f chain-rc.sh >/dev/null || { echo "chain-rc no longer running; last: $(tail -1 $S)"; exit 0; }
  sleep 20
done
