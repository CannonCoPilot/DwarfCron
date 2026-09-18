#!/bin/bash
# Compress-archive bridge logs. Verify each archive before removing its source.
# Never removes an original unless `zstd -t` confirms the archive is readable.
LOGDIR="/Users/nathanielcannon/Claude/Projects/DwarfCron/data/bridge-logs"
REPORT="$LOGDIR/ARCHIVE-MANIFEST.txt"

{
  echo "Bridge log archive — created 2026-08-25 by W2:Urist"
  echo "Codec: zstd -12 -T0. Verified with 'zstd -t' before each source removal."
  echo "Restore a file with: zstd -d <file>.jsonl.zst"
  echo ""
  printf "%-52s %12s %12s %8s\n" "FILE" "ORIGINAL" "COMPRESSED" "RATIO"
} > "$REPORT"

total_before=0
total_after=0
failed=0

find "$LOGDIR" -type f -name '*.jsonl' | sort | while read -r f; do
  before=$(stat -f%z "$f")
  if zstd -T0 -12 -q -f "$f" -o "$f.zst" 2>/dev/null && zstd -t "$f.zst" 2>/dev/null; then
    after=$(stat -f%z "$f.zst")
    rm -f "$f"
    ratio=$(echo "scale=1; $before/$after" | bc 2>/dev/null || echo "?")
    printf "%-52s %12s %12s %7sx\n" \
      "$(basename "$f")" \
      "$(echo "scale=1; $before/1048576" | bc)M" \
      "$(echo "scale=1; $after/1048576" | bc)M" \
      "$ratio" >> "$REPORT"
  else
    echo "FAILED (original kept): $(basename "$f")" >> "$REPORT"
    rm -f "$f.zst"
  fi
done

echo "" >> "$REPORT"
echo "DONE $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT"
du -sh "$LOGDIR" >> "$REPORT"
