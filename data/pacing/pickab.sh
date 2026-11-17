#!/bin/bash
# data/pacing/pickab.sh SAVE DEPTH RACE_A RACE_B STOCK_A STOCK_B DAYS [TAG] -- does DF's cavern wave pick follow entry STOCK?
# (17 Nov 2026, P10: flesh balls with 395 stock at FREQUENCY 10 took 54% of cavern 3 against members with 16-43 at 50.)
# Restart DF, load SAVE, `seasonal-wildlife off` (every entry given back), then on DF's nine draw tiles at cavern DEPTH
# (0-2) close every Animal entry except one site-tile entry each of RACE_A and RACE_B, stocked STOCK_A / STOCK_B (both
# open). Step DAYS days in one-day chunks; each day record the new living units of each race on the map. A wave = a day
# with new units of that race. Results: pickab/<TAG>.tsv (day, race, new units). The player's config is put back.
set -uo pipefail
SAVE=$1; DEPTH=$2; RA=$3; RB=$4; QA=$5; QB=$6; DAYS=$7; TAG=${8:-${SAVE}_${RA}${QA}_${RB}${QB}}
cd ~/Claude/Projects/DwarfCron || exit 1
source scripts/cx-config.sh
L=scripts/cx-lifecycle.sh; D=data/pacing/pickab; mkdir -p "$D"; OUT="$D/$TAG.tsv"; LOG="$D/$TAG.log"
CFG="$DF_DIR/dfhack-config/seasonal-wildlife.json"; BAK="$D/.seasonal-wildlife.json.bak"
cp -p "$CFG" "$BAK" || { echo "cannot back up $CFG" >&2; exit 1; }
restore() { cmp -s "$BAK" "$CFG" || { cp -p "$BAK" "$CFG"; echo "[pickab] restored $CFG" | tee -a "$LOG"; }; }
trap 'restore; rm -f "$BAK"' EXIT
log() { echo "[pickab $(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
rpc() { .venv/bin/python scripts/cx-rpc.py --port 5555 --timeout 60 --lua "$1" 2>&1 | tr -d '\r'; }

$L restart >/dev/null 2>&1
$L load "$SAVE" >> "$LOG" 2>&1 || { log "load $SAVE failed"; exit 1; }
$L cmd seasonal-wildlife off >> "$LOG" 2>&1; restore
SETUP="
local D, A, B, QA, QB = $DEPTH, '$RA', '$RB', $QA, $QB
local SX, SY = df.global.world.map.region_x // 16, df.global.world.map.region_y // 16
local dep = {}
local function depth(id) if dep[id] == nil then local ok, r = pcall(function() return df.global.world.world_data.underground_regions[id] end); dep[id] = (ok and r) and r.layer_depth or -1 end return dep[id] end
local set, closed, missing = {}, 0, {}
for _, p in ipairs(df.global.world.populations.all) do
    local P = p.population
    if P.cave_id ~= -1 and df.world_population_type[p.type] == 'Animal' and depth(P.cave_id) == D
       and math.abs(P.region_x - SX) <= 1 and math.abs(P.region_y - SY) <= 1 then
        local t = df.creature_raw.find(p.race).creature_id
        local q = (P.region_x == SX and P.region_y == SY and not set[t]) and ((t == A and QA) or (t == B and QB)) or nil
        if q then p.quantity = q; if p.quantity_max < q then p.quantity_max = q end; p.flags.extinct = false; set[t] = q
        else p.quantity = 0; p.flags.extinct = true; closed = closed + 1 end
    end
end
for _, t in ipairs({ A, B }) do if not set[t] then missing[#missing + 1] = t end end
print(('setup: %s=%s %s=%s, %d entries closed, missing: %s'):format(A, tostring(set[A]), B, tostring(set[B]), closed, table.concat(missing, ',')))"
log "$(rpc "$SETUP" | tail -1)"
grep -q 'missing: $' <<< "$(tail -1 "$LOG")" || { log "a race has no site-tile entry at this depth: stop"; exit 1; }
COUNT="
local want = { ['$RA'] = true, ['$RB'] = true }
for _, u in ipairs(df.global.world.units.active) do
    local t = df.creature_raw.find(u.race).creature_id
    if want[t] and dfhack.units.isAlive(u) and not dfhack.units.isCitizen(u) then print(t .. ' ' .. u.id) end
end"
seen=$(rpc "$COUNT" | grep -E '^[A-Z_]+ [0-9]+$' | sort -u)
log "on the map at the start: $(wc -l <<< "${seen:-}" | tr -d ' ') unit(s) of $RA/$RB"
[ -f "$OUT" ] || printf 'day\trace\tnew_units\n' > "$OUT"
$L fps 1000 10 >/dev/null 2>&1
for d in $(seq 1 "$DAYS"); do
    $L cmd cx-load sustain >/dev/null 2>&1
    out=$($L step 1200 300 2>&1) || { log "day $d: step rc $?: $(tail -1 <<< "$out")"; break; }
    now=$(rpc "$COUNT" | grep -E '^[A-Z_]+ [0-9]+$' | sort -u)
    new=$(comm -13 <(printf '%s\n' "$seen") <(printf '%s\n' "$now"))
    for t in "$RA" "$RB"; do
        n=$(grep -c "^$t " <<< "$new")
        [ "$n" -gt 0 ] && { printf '%s\t%s\t%s\n' "$d" "$t" "$n" >> "$OUT"; log "day $d: $t +$n"; }
    done
    seen=$(printf '%s\n%s\n' "$seen" "$now" | grep . | sort -u)
done
log "done: $(awk -F'\t' 'NR>1{w[$2]++; u[$2]+=$3} END{for(t in w) printf "%s %d waves %d units; ", t, w[t], u[t]}' "$OUT")"
$L title >/dev/null 2>&1
