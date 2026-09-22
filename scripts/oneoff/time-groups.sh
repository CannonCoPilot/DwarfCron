#!/bin/bash
# Hand measurement: how long does `seasonal-wildlife groups` take on a loaded CTRL, and does our script write anything to stderr.log?
cd ~/Claude/Projects/DwarfCron || exit 1
source scripts/cx-config.sh
PORT=$(scripts/cx-lifecycle.sh port 2>/dev/null || true)
echo "port=$PORT"
scripts/cx-lifecycle.sh load CTRL; echo "load rc=$?"; sleep 10
before=$(stat -f %z "$DF_DIR/stderr.log")
for verb in "groups" "status" "groups" "ledger 3"; do
  t0=$(date +%s.%N)
  out=$("$CX_PYTHON" scripts/cx-rpc.py --port "$PORT" --timeout 120 --cmd seasonal-wildlife $verb 2>&1)
  rc=$?; t1=$(date +%s.%N)
  printf "verb=%-10s rc=%s  %.2fs  lines=%s  first=%s\n" "$verb" "$rc" "$(echo "$t1 - $t0" | bc)" "$(echo "$out" | wc -l | tr -d ' ')" "$(echo "$out" | head -1 | cut -c1-100)"
done
echo "--- new stderr.log lines (ours only):"; tail -c +$((before + 1)) "$DF_DIR/stderr.log" | grep -vE "^Client connection|^Shutting down" | grep -iE "seasonal|error|traceback" | head -12
scripts/cx-lifecycle.sh title; echo "title rc=$?"
echo "=== time-groups exit $(date +%T) ==="
