#!/bin/sh
# After the RC sec7 chain (2 Oct, user): merge v7.1-web2 into v7.1-rc, deploy the merged tree, re-check RinghatchetsReady
# (gui + w0 phases: the 3 fixed FAILs), re-time the companion live (5 min), then the full aquarium run (embarks AQUA_SHORE).
# The aquarium fix loop after it is interactive (the lead). Log: data/logs/chain-post.log; one line per step.
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
L=data/logs/chain-post.log; RC=/Users/nathanielcannon/Claude/Projects/sw-wt/rc; LUAC=/Users/nathanielcannon/Claude/Projects/sw-wt/.tools/luac53
say() { echo "$(date +%H:%M:%S) $*" >> $L; }
say "waiting for the RC chain to end"
while pgrep -f chain-rc.sh >/dev/null; do sleep 20; done
say "chain ended: $(tail -1 data/logs/sec7-rc.log)"
git -C $RC merge --no-edit v7.1-web2 >> $L 2>&1 || { say "!! web2 merge FAILED"; exit 1; }
say "merged web2: rc now $(git -C $RC log -1 --format=%h)"
for f in $RC/scripts/*.lua; do $LUAC -p "$f" || { say "!! luac53 $f"; exit 1; }; done
say "luac53 ok"
scripts/cx-lifecycle.sh title >> $L 2>&1
scripts/cx-lifecycle.sh deploy >> $L 2>&1
scripts/cx-lifecycle.sh deploy-tool $RC/scripts >> $L 2>&1 || { say "!! deploy-tool FAILED"; exit 1; }
say "deployed rc $(git -C $RC log -1 --format=%h)"
export SW_TOOL=$RC
.venv/bin/python scripts/validate-full.py --fort RinghatchetsReady --only gui > data/logs/post-validate-gui.log 2>&1
say "validate RH gui exit $?: $(tail -2 data/logs/post-validate-gui.log | tr '\n' ' ' | cut -c1-200)"
.venv/bin/python scripts/validate-full.py --fort RinghatchetsReady --only w0 > data/logs/post-validate-w0.log 2>&1
say "validate RH w0 exit $?: $(tail -2 data/logs/post-validate-w0.log | tr '\n' ' ' | cut -c1-200)"
python3 scripts/web2-live.py --tool-src $RC/scripts --deploy none --minutes 5 --gap 120 > data/logs/post-web2-live.log 2>&1
say "web2-live re-time exit $?: $(grep -E '== [0-9]+ FAIL' data/logs/post-web2-live.log | tail -1)"
python3 scripts/aquarium-run.py --tool-src $RC --deploy --embark-shore > data/logs/post-aquarium.log 2>&1
say "aquarium-run exit $?: $(tail -1 data/logs/post-aquarium.log | cut -c1-200)"
say "=== chain-post done"
