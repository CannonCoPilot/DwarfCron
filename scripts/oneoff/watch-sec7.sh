#!/bin/sh
# Wait silently until the sec7 log gains a line worth acting on (abort, FAIL, traceback, run exit), print it, exit.
# One notification per real event; no periodic expiries. Usage: watch-sec7.sh <log>
LOG="$1"; N=$(wc -l < "$LOG")
while :; do
  M=$(wc -l < "$LOG")
  if [ "$M" -gt "$N" ]; then
    HIT=$(tail -n +"$((N + 1))" "$LOG" | head -n "$((M - N))" | grep -E "\[FAIL\]|ABORTED|MANIP-FAIL|Traceback|=== sec7")
    N=$M
    if [ -n "$HIT" ]; then echo "$HIT" | cut -c1-300; exit 0; fi
  fi
  pgrep -f "alpha4-sec7.py" >/dev/null || { echo "sec7 runner no longer running; last: $(tail -1 "$LOG" | cut -c1-200)"; exit 0; }
  sleep 30
done
