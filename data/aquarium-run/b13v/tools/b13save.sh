#!/bin/bash
# b13save.sh SAVE : for each water pick in the loaded save, at the water's level and one above:
#   4 real held-'s' pans with the heal off + compose check each; then a 60 fps recording of taps + a hold, slide-checked.
S=$(cd "$(dirname "$0")" && pwd)  # these tools
cd /Users/nathanielcannon/Claude/Projects/DwarfCron || exit 1
r() { timeout 30 .venv/bin/python scripts/cx-rpc.py --port 5000 --timeout 25 "$@"; }
SAVE=$1; D=data/aquarium-run/b13v/$SAVE; mkdir -p "$D"
r --cmd aquarium-plugin depth on >/dev/null 2>&1; sleep 1
while read -r cn x y zb zt; do
  cx=$((x > 20 ? x - 20 : 0)); cy=$((y > 18 ? y - 18 : 0))
  for z in $zt $((zt + 1)); do
    echo "== $SAVE $cn corner $cx,$cy z$z" | tee -a "$D/keys.txt"
    $S/b13keys.sh $cx $cy $z off 6 s 2>&1 | tee -a "$D/keys.txt"
    r --lua "df.global.window_x=$cx; df.global.window_y=$cy; df.global.window_z=$z" >/dev/null; sleep 1.5
    out=data/recordings/b13-$SAVE-$cn-z$z; rm -rf "$out"; mkdir -p "$out"
    (scripts/cx-record.sh 7 rec --fps 60 --frames 60 --out "$out" > "$out/rec.txt" 2>&1 &)
    sleep 1.2
    for t in 1 2 3; do .venv/bin/python scripts/cx-mouse.py key s >/dev/null; sleep 0.5; done
    .venv/bin/python scripts/cx-mouse.py hold s 1.5 >/dev/null
    sleep 5
    while pgrep -f "cx-wincap" >/dev/null || pgrep -f "ffmpeg.*$out" >/dev/null; do sleep 1; done
    echo "-- recording $cn z$z: $(tail -1 $out/rec.txt | grep -oE '[0-9]+ frames over')" | tee -a "$D/keys.txt"
    python3 $S/shiftcheck.py "$out/frames" 48 10 1640 160 1015 2>&1 | tail -6 | tee -a "$D/keys.txt"
    python3 $S/bandscan.py "$out"/frames/*.png 2>&1 | tail -4 | tee -a "$D/keys.txt"
    # keep the mp4, drop the PNGs
    rm -rf "$out/frames"
  done
done < data/aquarium-run/b9v/$SAVE/picks.txt
r --cmd aquarium-plugin status 2>&1 | grep -c "fault at pc" | sed 's/^/bed printer faults: /' | tee -a "$D/keys.txt"
