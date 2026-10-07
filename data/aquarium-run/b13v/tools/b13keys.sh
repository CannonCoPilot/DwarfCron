#!/bin/bash
# b13keys.sh X Y Z HEAL(on|off) ROUNDS KEY : real held-key pans from X,Y,Z, compose check after each (heal off = debug 5)
cd /Users/nathanielcannon/Claude/Projects/DwarfCron || exit 1
r() { timeout 30 .venv/bin/python scripts/cx-rpc.py --port 5000 --timeout 25 "$@"; }
X=$1 Y=$2 Z=$3 HEAL=$4 N=$5 KEY=${6:-s}
case "$HEAL" in off) M=5;; on) M=0;; *) M=$HEAL;; esac; r --cmd aquarium-plugin composecheck debug $M >/dev/null
durs=(tap tap 0.2 0.4 tap 0.3)
for ((i=0; i<N; i++)); do
  if [ $((i % 2)) = 0 ]; then r --lua "df.global.window_x=$X; df.global.window_y=$Y; df.global.window_z=$Z" >/dev/null; sleep 1; fi
  d=${durs[$((i % ${#durs[@]}))]}
  if [ "$d" = tap ]; then .venv/bin/python scripts/cx-mouse.py key $KEY >/dev/null; else .venv/bin/python scripts/cx-mouse.py hold $KEY $d >/dev/null; fi
  sleep 0.3
  r --cmd aquarium-plugin composecheck now >/dev/null; sleep 0.8
  cc=$(r --cmd aquarium-plugin composecheck 2>&1 | sed 's/aquarium: compose check: //')
  cam=$(r --lua "print(df.global.window_x..','..df.global.window_y..','..df.global.window_z)" 2>&1 | tail -1)
  c2=$(echo "$cc" | grep -oE "^corner [0-9]+,[0-9]+,[0-9]+" | cut -d" " -f2); [ "$c2" = "$cam" ] || cc="NOT RUN (no water in view at $cam; last result was for $c2)"
  echo "round $i hold $KEY ${d}s cam $cam | $cc"
done
r --cmd aquarium-plugin composecheck debug 0 >/dev/null
