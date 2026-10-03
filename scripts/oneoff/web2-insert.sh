#!/bin/sh
# Slot the web2 live run into the RC sec7 chain at its next block boundary (2 Oct, user: "a working version that polls
# the live in-game data in real time"). Pauses the alpha4-sec7 runner (SIGSTOP) after a block ends and before the next
# eco-run starts, runs web2-live.py --leave, holds the fort + server up for a browser pass until data/logs/web2-resume
# exists (or HOLD_MIN minutes), then stops the server, redeploys the RC tree (puts the RC web files back), restarts DF
# fresh (the runner's per-block restart) and resumes the runner (SIGCONT). The runner keeps its run dir and order.
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
L=data/logs/web2-insert.log; S=data/logs/sec7-rc.log; HOLD_MIN=${HOLD_MIN:-30}; RES=data/logs/web2-resume
RC=/Users/nathanielcannon/Claude/Projects/sw-wt/rc
say() { echo "$(date +%H:%M:%S) $*" >> $L; }
rm -f $RES
P=$(pgrep -f "scripts/alpha4-sec7.py" | head -1)
[ -n "$P" ] || { say "no alpha4-sec7 runner; abort"; exit 2; }
say "waiting for the next block end (runner $P)"
n=$(wc -l < $S)
while :; do
  m=$(wc -l < $S)
  if [ "$m" -gt "$n" ]; then
    h=$(tail -n +$((n+1)) $S | grep -E "^ *[0-9:]* +S7_[A-Z0-9]+: [0-9.]+ min$|=== sec7 exit" | tail -1); n=$m
    [ -n "$h" ] && break
  fi
  pgrep -f chain-rc.sh >/dev/null || { say "chain ended before a boundary; running web2 with the rig free"; P=; break; }
  sleep 2
done
if [ -n "$P" ]; then
  kill -STOP $P; say "boundary: $h -> runner $P stopped"
  # the runner may already be in its DF stop/start: let that child finish; an eco-run child means we missed the gap
  while c=$(pgrep -P $P); [ -n "$c" ]; do
    ps -o command= -p $c | grep -q eco-run && { kill -CONT $P; say "missed the gap (eco-run started); resumed, abort"; exit 3; }
    sleep 2
  done
  say "runner idle; rig is ours"
fi
scripts/cx-lifecycle.sh title >> $L 2>&1
say "web2-live start"
python3 scripts/web2-live.py --leave > data/logs/web2-live.log 2>&1; rc=$?
say "web2-live exit $rc: $(grep -E 'PASS|FAIL' data/logs/web2-live.log | tail -1)"
say "holding fort + server for the browser pass: touch $RES to resume (or ${HOLD_MIN} min)"
i=0; while [ ! -e $RES ] && [ $i -lt $((HOLD_MIN*6)) ]; do sleep 10; i=$((i+1)); done
say "resume: stop server, title, redeploy RC tree, fresh DF"
scripts/cx-lifecycle.sh cmd seasonal-wildlife-web stop >> $L 2>&1
scripts/cx-lifecycle.sh title >> $L 2>&1
scripts/cx-lifecycle.sh deploy-tool $RC/scripts >> $L 2>&1 || say "!! RC redeploy FAILED"
scripts/cx-lifecycle.sh stop >> $L 2>&1; scripts/cx-lifecycle.sh start >> $L 2>&1
[ -n "$P" ] && { kill -CONT $P; say "runner $P resumed"; }
say "=== web2-insert done"
