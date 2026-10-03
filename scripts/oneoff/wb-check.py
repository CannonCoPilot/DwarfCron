#!/usr/bin/env python3
"""Water body registry + edge/centroid placement: the 4-step rig check from sw-wt/rc docs/v7.1/water-bodies.md, on
RinghatchetsReady (region9: lake + river, caverns open). Reuses aquarium-run.py's rig helpers (one RPC at a time,
receipts for every call). Output: data/aquarium-run/<run>-wb/{log.txt,results.json,receipts/}.
Usage: python3 scripts/oneoff/wb-check.py [--no-load]
"""
import importlib.util, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("aqr", ROOT / "scripts/aquarium-run.py")
A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)

class Args: tool_src = str(Path.home() / "Claude/Projects/sw-wt/rc"); view = None; dry_run = False
A.ARGS = Args(); A.MODE = "live"; A.STAGE = "wb"
A.OUT = A.OUT.with_name(A.RUN + "-wb"); A.OUT.mkdir(parents=True, exist_ok=True)
A.LOG = open(A.OUT / "log.txt", "w")

MEMBERS = r"""
local sw = reqscript('seasonal-wildlife'); local R = sw.V7.WB.get(); local rows = {}
for _, grp in ipairs(sw.loadGroups().groups) do if grp.entry then
  local bad = 0
  for _, id in ipairs(grp.ids) do local u = df.unit.find(id); if u then
    local d = dfhack.maps.getTileFlags(u.pos); local B = sw.V7.WB.at(R, u.pos.x, u.pos.y, u.pos.z)
    if not (d and d.flow_size >= 4 and B and B.id == grp.wb) then bad = bad + 1 end end end
  rows[#rows + 1] = { token = grp.token, body = grp.body, wb = grp.wb, how = grp.entry.how, x = grp.entry.x,
    y = grp.entry.y, z = grp.entry.z, level = grp.entry.level, n = #grp.ids, off = bad }
end end
local M = df.global.world.map
return { W = M.x_count, H = M.y_count, rows = rows }
"""

ENTRY = re.compile(r"entered (\w+) #(\d+) (at the map edge|nearest its centroid [\d.,-]+): (\d+),(\d+),(\d+) \(level (\d)/7, column depth (\d+)\)")


def out_of(rc_out_err):
    return (rc_out_err[1] + rc_out_err[2]).strip()


def main():
    if "--no-load" not in sys.argv and not A.load_fort("RinghatchetsReady", "(water body check)"):
        return 1
    # 1. registry
    A.STAGE = "wb1"
    A.sw("water", "scan"); A.cx("step", "300", "120")
    A.cx("pause")
    bodies = out_of(A.sw("water", "bodies")); A.log("bodies:\n" + bodies)
    led = out_of(A.sw("ledger", "5", "bodies")); A.log("ledger bodies:\n" + led)
    types = set(re.findall(r"\b(ocean|river|lake|pool|cavern_pool)\b", bodies))
    A.rec("wb1.river", "PASS" if "river" in types else "FAIL", f"types {sorted(types)}")
    A.rec("wb1.lake", "PASS" if "lake" in types else "FAIL", f"types {sorted(types)}")
    A.rec("wb1.cavern_pool", "PASS" if "cavern_pool" in types else "NOT-TESTABLE", f"types {sorted(types)}")
    ms = re.findall(r"([\d.]+) ?ms", led)
    A.rec("wb1.rescan_ledger", "PASS" if ms else "FAIL", led[-300:] or "no rescan line")
    # 2. arrivals (the validator's phase_lake setup: tool on, water layer on, in-embark water species allowed all year)
    A.STAGE = "wb2"
    A.sw("enable")
    A.cx("lua", "local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); if not cfg.initialized then sw.captureDefault(cfg) end; "
         "cfg.layers.water=true; cfg.water.enabled=true; sw.saveConfig(cfg); local pool=sw.buildPool(cfg); local n=0; "
         "for _,e in ipairs(pool) do if e.inEmbark and e.layer=='water' and sw.defaultAllow(e) then cfg.allow[e.key]=true; cfg.assign[e.key]={0,1,2,3}; n=n+1 end end; "
         "sw.saveConfig(cfg); sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg); print('wb setup: water species allowed '..n)", timeout=180)
    A.log("water on: " + out_of(A.sw("water", "on")))
    replies = []
    for kind in ("river", "lake"):
        for _ in range(3):
            replies.append((kind, out_of(A.sw("water", "now", kind))))
    led = out_of(A.sw("ledger", "12", "arrive", "water")); A.log("arrive ledger:\n" + led)
    G, raw = A.lua("wb-members", MEMBERS, timeout=120)
    W, H = (G or {}).get("W", 0), (G or {}).get("H", 0)
    entries = ENTRY.findall("\n".join(r for _, r in replies) + "\n" + led)
    A.log(f"entries {len(entries)}: {entries[:12]}")
    if not entries:
        A.rec("wb2.entries", "FAIL", "no 'entered' line in replies or ledger: " + " | ".join(r[:160] for _, r in replies))
    seen = set()
    for typ, bid, rule, x, y, z, lvl, depth in entries:
        key = (typ, bid, x, y, z)
        if key in seen: continue
        seen.add(key)
        x, y, lvl = int(x), int(y), int(lvl)
        edge = x in (0, W - 1) or y in (0, H - 1)
        if typ in ("river", "ocean"):
            A.rec(f"wb2.{typ}.edge.{x},{y}", "PASS" if edge else "FAIL", f"{rule} {x},{y},{z} map {W}x{H} L{lvl}")
        else:
            A.rec(f"wb2.{typ}.rule.{x},{y}", "PASS" if (edge or "centroid" in rule) else "FAIL", f"{rule} {x},{y},{z} L{lvl}")
        A.rec(f"wb2.{typ}.level.{x},{y}", "PASS" if lvl >= 4 else "FAIL", f"L{lvl} depth {depth}")
    # 3. members
    A.STAGE = "wb3"
    if not G:
        A.rec("wb3.members", "FAIL", raw[-300:])
    else:
        bad = [r for r in G["rows"] if r["off"]]
        A.rec("wb3.members", "PASS" if G["rows"] and not bad else "FAIL",
              f"{len(G['rows'])} entry groups, off-body {sum(r['off'] for r in G['rows'])}: {bad[:4]}", data=G["rows"])
    A.cx("step", "1200", "300"); A.cx("pause")
    strand = out_of(A.sw("ledger", "20", "strand")); A.log("strand ledger:\n" + strand)
    A.rec("wb3.no_guard_lines", "PASS" if not re.search(r"guard|strand(ed)? .*moved", strand, re.I) else "FAIL", strand[-300:])
    G2, raw2 = A.lua("wb-members-after", MEMBERS, timeout=120)
    if G2:
        A.rec("wb3.after1200", "INFO", f"off-body after 1200 t: {sum(r['off'] for r in G2['rows'])} of "
              f"{sum(r['n'] for r in G2['rows'])} (DF's own beaching allowed)", data=G2["rows"])
    # 4. restriction and refusal
    A.STAGE = "wb4"
    rw = out_of(A.sw("roster", "water")); A.log("roster water:\n" + rw[:1500])
    rows = re.findall(r"^water-bodies ([A-Z][A-Z0-9_ ]*?)\s+([a-z_,]+)\s+raws", rw, re.M)
    river = [t for t, b in rows if "river" in b.split(",") and " " not in t]
    tok = next((t for t in river if t.startswith("FISH_")), river[0] if river else None)
    if not tok:
        A.rec("wb4.pick", "NOT-TESTABLE", "no river species in roster water"); finish(); return 0
    A.log(f"river fish: {tok}")
    A.sw("roster", "water", tok, "bodies", "lake")
    r = out_of(A.sw("call", "water:" + tok)); A.log("call: " + r)
    e = ENTRY.findall(r) or ENTRY.findall(out_of(A.sw("ledger", "1", "arrive", "water")))
    A.rec("wb4.lake_only", "PASS" if e and all(t[0] == "lake" for t in e) else "FAIL", r[-300:] + f" | entries {e}")
    A.sw("roster", "water", tok, "bodies", "cavern_pool")
    r = out_of(A.sw("place", tok, "3", "water")); A.log("place: " + r)
    A.rec("wb4.refused", "PASS" if "no registered water body" in r else "FAIL", r[-300:])
    r = out_of(A.sw("roster", "water", tok, "bodies", "default")); A.log("default: " + r)
    r = out_of(A.sw("water", "guard"))
    A.rec("wb4.guard_removed", "PASS" if re.search(r"removed", r, re.I) else "FAIL", r[-300:])
    finish(); return 0


def finish():
    (A.OUT / "results.json").write_text(json.dumps(A.RESULTS, indent=1))
    tally = {}
    for r in A.RESULTS: tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    A.log(f"DONE {tally} -> {A.OUT}")


if __name__ == "__main__":
    sys.exit(main())
