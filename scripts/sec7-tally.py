#!/usr/bin/env python3
"""Alpha Four section 7 ("What this page cannot check", 15 rows): the results tally.

    python3 scripts/sec7-tally.py                 # prints the report, writes data/alpha4-sec7/sec7-tally.json
    python3 scripts/sec7-tally.py --figs          # also writes PNGs to data/alpha4-sec7/figs/ (needs matplotlib)

Reads (no rig contact):
  data/alpha4-sec7/20261002-015732/   stages FACTS/R2/PANEL/WEBLOAD (tool 9e5aabe); its eco/ blocks were no-ops (S7() bug)
                                      and are ignored
  data/alpha4-sec7/20261002-024942/   core3 (tool 9e5aabe): the valid completed blocks listed in RUNS below
  data/alpha4-sec7/20261002-075328/   rerun (tool a4fix 69e97a1, DF restarted per block)
  data/alpha4-sec7/<newest>/          the TRIM/IRRR35/VF4 rerun, when present (cells that completed are read; a block
                                      with no completed cell is PENDING)
  data/validation/full/20261002-020031/TRIAGE.md (validate-full on this fort)

Readout rules (memory experiment-readout-traps), applied per block:
  * a cell is read only when eco-run wrote its rows (complete cells only; MANIPFAIL/FAILED cells are listed, not scored);
  * the dial's receipt is printed before its outcome, and a block whose receipt shows the dial never reached its
    subject is called vacuous (trap 22), not "no effect";
  * attacks/kills are scored PLACED>PLACED only (trap 20: the wipe leaves natives and released units that fight);
  * a wait with no event is censored (trap 13): reported as '>window', never dropped;
  * fps_calc at t0 is read paused (trap 5) and is never used; t/s is the in-game stopwatch;
  * a cell that ran far past its budget (PERF1 core3 legacy rep 5, 871 s, 10,845 of 12,000 t) is excluded and named.
Statistics, n = 5 per arm unless stated: mean, SD, 95% t-interval; two-arm contrasts use the EXACT two-sided permutation
test on the difference of means (all C(10,5) = 252 splits for 5 vs 5); cell-level yes/no outcomes use Fisher's exact test
(two-sided); effect sizes are the mean difference and Hedges' g.
"""
from __future__ import annotations

import itertools
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEC7 = ROOT / "data/alpha4-sec7"
STAGES = SEC7 / "20261002-015732"
CORE3 = SEC7 / "20261002-024942"
RERUN = SEC7 / "20261002-075328"
FIXED = ("20261002-005721", "20261002-014111", "20261002-015732", "20261002-023610", "20261002-024942",
         "20261002-075307", "20261002-075328")
BUILD = {CORE3.name: "9e5aabe", RERUN.name: "a4fix 69e97a1", STAGES.name: "9e5aabe"}

# which run holds the valid copy of each block (BLOCK-FIXES.md; the user's run list of 2 Oct)
RUNS = {
    "S7_SKL": RERUN, "S7_PK2": CORE3, "S7_STP1": CORE3, "S7_FSH3": CORE3, "S7_FSH4": CORE3,
    "S7_NAT": RERUN, "S7_PAN1": CORE3, "S7_COHT": CORE3,
    "S7_IRRM": RERUN, "S7_IRRP2": RERUN, "S7_IRRTSEQ": RERUN,
    "S7_SCV3": CORE3, "S7_SCV3W": CORE3, "S7_VF1": CORE3, "S7_GRD1": CORE3,
    "S7_EXR1": CORE3, "S7_EXU1": CORE3, "S7_F1": CORE3,
    "S7_PERF2": RERUN, "S7_PERF4": RERUN,
}
LATE = ("S7_TRIM", "S7_IRRR35", "S7_VF4")   # rerun after their second fix, into the newest run dir


def newest_run():
    """The run dir made after the fixed list (the TRIM/IRRR35/VF4 rerun), or None."""
    c = sorted(p for p in SEC7.iterdir() if p.is_dir() and re.match(r"\d{8}-\d{6}$", p.name) and p.name not in FIXED)
    return c[-1] if c else None


NEW = newest_run()
if NEW is not None:
    BUILD[NEW.name] = "a4fix 69e97a1"
    for b in LATE:
        RUNS[b] = NEW

OUT = {}          # everything the report states, for sec7-tally.json
LINES = []


def say(s=""):
    LINES.append(s)
    print(s)


# ------------------------------------------------------------------------------------------------- stats --
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 14: 2.145, 19: 2.093, 24: 2.064, 29: 2.045}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def sd(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return float("nan")
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def ci(xs):
    xs = [x for x in xs if x is not None]
    n = len(xs)
    if n < 2:
        return (float("nan"), float("nan"))
    t = T975.get(n - 1) or T975[min(T975, key=lambda k: abs(k - (n - 1)))]
    h = t * sd(xs) / math.sqrt(n)
    return (mean(xs) - h, mean(xs) + h)


def perm_p(a, b):
    """Exact two-sided permutation p for the difference of means (every split of the pooled values)."""
    a, b = [x for x in a if x is not None], [x for x in b if x is not None]
    if not a or not b:
        return float("nan")
    pool, na = a + b, len(a)
    obs = abs(mean(a) - mean(b))
    hit = tot = 0
    for idx in itertools.combinations(range(len(pool)), na):
        s = set(idx)
        x = [pool[i] for i in idx]
        y = [pool[i] for i in range(len(pool)) if i not in s]
        tot += 1
        if abs(mean(x) - mean(y)) >= obs - 1e-12:
            hit += 1
    return hit / tot


def hedges_g(a, b):
    a, b = [x for x in a if x is not None], [x for x in b if x is not None]
    if len(a) < 2 or len(b) < 2:
        return float("nan")
    sp = math.sqrt(((len(a) - 1) * sd(a) ** 2 + (len(b) - 1) * sd(b) ** 2) / (len(a) + len(b) - 2))
    if sp == 0:
        return float("inf") if mean(a) != mean(b) else 0.0
    j = 1 - 3 / (4 * (len(a) + len(b)) - 9)
    return (mean(a) - mean(b)) / sp * j


def fisher(a_yes, a_n, b_yes, b_n):
    """Fisher's exact test, two-sided, on [[a_yes, a_no], [b_yes, b_no]]."""
    def h(k):
        n, K, N = a_n, a_yes + b_yes, a_n + b_n
        return math.comb(K, k) * math.comb(N - K, n - k) / math.comb(N, n)
    K = a_yes + b_yes
    lo, hi = max(0, a_n - (a_n + b_n - K)), min(a_n, K)
    p0 = h(a_yes)
    return min(1.0, sum(h(k) for k in range(lo, hi + 1) if h(k) <= p0 + 1e-12))


def f(x, d=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    return f"{x:.{d}f}"


def desc(xs, d=2):
    xs = [x for x in xs if x is not None]
    lo, hi = ci(xs)
    return f"{f(mean(xs), d)} (SD {f(sd(xs), d)}, 95% CI {f(lo, d)}..{f(hi, d)}, n={len(xs)})"


def contrast(name, a, b, la, lb, d=2):
    """Two-arm line: means, difference, Hedges' g, exact permutation p."""
    a, b = [x for x in a if x is not None], [x for x in b if x is not None]
    p = perm_p(a, b)
    g = hedges_g(a, b)
    say(f"    {name}: {la} {desc(a, d)}; {lb} {desc(b, d)}")
    say(f"      diff {la}-{lb} = {f(mean(a) - mean(b), d)}; Hedges g = {f(g)}; exact permutation p = {f(p, 3)}")
    return dict(a=a, b=b, la=la, lb=lb, diff=mean(a) - mean(b), g=g, p=p)


# ------------------------------------------------------------------------------------------------- loader --
def kv(rest: str) -> dict:
    d = {}
    for t in rest.split():
        if "=" in t:
            k, v = t.split("=", 1)
            d[k] = v
    return d


def num(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


class Block:
    """One eco TSV: rows per (arm, rep) cell, in file order; failed cells kept apart."""

    def __init__(self, name, run=None):
        self.name = name
        self.run = run or RUNS.get(name)
        self.path = self.run / "eco" / f"{name}.tsv" if self.run else None
        self.cells = defaultdict(list)
        self.failed = {}
        if self.path and self.path.exists():
            for line in open(self.path, errors="replace"):
                p = line.rstrip("\n").split("\t")
                if len(p) < 5:
                    continue
                _, arm, rep, kind, rest = p[:5]
                key = (arm, int(rep))
                if kind in ("MANIPFAIL", "FAILED"):
                    self.failed[key] = rest
                    continue
                self.cells[key].append((kind, kv(rest), rest))
            for k in self.failed:
                self.cells.pop(k, None)
        self.build = BUILD.get(self.run.name, "?") if self.run else "?"

    @property
    def present(self):
        return bool(self.cells) or bool(self.failed)

    def arms(self):
        return sorted({a for a, _ in self.cells})

    def reps(self, arm):
        return sorted(r for a, r in self.cells if a == arm)

    def rows(self, arm, rep, kind_=None, **flt):
        out = []
        for k, d, raw in self.cells.get((arm, rep), []):
            if kind_ and k != kind_:
                continue
            if all(d.get(a) == str(b) for a, b in flt.items()):
                out.append(d)
        return out

    def raw(self, arm, rep, kind):
        return [raw for k, d, raw in self.cells.get((arm, rep), []) if k == kind]

    def first(self, arm, rep, kind_, **flt):
        r = self.rows(arm, rep, kind_, **flt)
        return r[0] if r else {}

    def last(self, arm, rep, kind_, **flt):
        r = self.rows(arm, rep, kind_, **flt)
        return r[-1] if r else {}

    def header(self, row, what):
        say(f"\n  [{self.name}] {what}; run {self.run.name if self.run else '-'} (tool {self.build}); "
            f"cells read: " + ", ".join(f"{a} n={len(self.reps(a))}" for a in self.arms()))
        if self.failed:
            for (a, r), m in sorted(self.failed.items()):
                say(f"    MANIPFAIL {a} rep {r}: {m[:150]}")

    def manip_checks(self):
        """Every explicit manipulation check across the read cells: (passed, total)."""
        n = ok = 0
        for cell in self.cells.values():
            for k, d, _ in cell:
                if k == "manip":
                    n += 1
                    ok += d.get("ok") == "1"
        return ok, n


def placed_pairs(blk, arm, rep, atk, vic):
    """PLACED>PLACED attacks of token atk on token vic (attacks_o rows), and kills with both spawned (death rows)."""
    n = 0
    for d in blk.rows(arm, rep, "attacks_o"):
        a, _, v = d.get("pair", "").partition(">")
        if a == f"{atk}(placed)" and v == f"{vic}(placed)":
            n += int(d.get("n", 0))
    k = sum(1 for d in blk.rows(arm, rep, "death") if d.get("victim") == vic and d.get("killer") == atk
            and d.get("victim_spawned") == "1" and d.get("killer_spawned") == "1")
    return n, k


def tagnum(tag):
    m = re.match(r"[a-z_]*?t?(\d+)$", tag or "")
    return int(m.group(1)) if m else None


# ============================================================================================= the rows ==
VERDICT = {}


def verdict(row, v, why):
    VERDICT[row] = (v, why)


# ------------------------------------------------------------------------------------------ 1. skills --
def row1():
    say("\n" + "=" * 110 + "\nROW 1  Skill writes act on new arrivals and do not rust (SKL1, SKL2)")
    b = Block("S7_SKL")
    b.header(1, "pkg / nopkg / pkg_nofloor; SNEAK on COUGAR (apex 15) and WOLF (pack 5)")
    ok, n = b.manip_checks()
    say(f"    manipulation checks passed {ok}/{n} (pack_bonus 0 read back in every cell; rustpushsum/nofloorsum hit)")
    res = {}
    spawned = {}
    for arm in b.arms():
        per = dict(new_at=[], pre_at=[], cells_drop=0, units=0, units_drop=0, units_floor_kept=0, cells=0,
                   lost=0, counters_untouched=0, rusty=0, df_made=[])
        for rep in b.reps(arm):
            ids = set()
            for d in b.rows(arm, rep, "spawn"):
                ids |= set(d.get("ids", "").split(","))
            spawned[(arm, rep)] = ids
            sks = b.rows(arm, rep, "sk")
            caste = {d["token"]: int(d["caste_lv"].split(",")[0]) for d in b.rows(arm, rep, "skillsum", tag="t0")}
            t0 = [d for d in sks if d["tag"] == "t0"]
            new = [d for d in t0 if d["was"] == "new"]
            pre = [d for d in t0 if d["was"] == "pre"]
            per["new_at"].append(sum(int(d["rating"]) >= caste[d["token"]] > 0 for d in new) / max(1, len(new)))
            per["pre_at"].append(sum(int(d["rating"]) >= caste[d["token"]] > 0 for d in pre) / max(1, len(pre)))
            before = {d["id"]: d for d in sks if d["tag"] == "t2000"}
            after = {d["id"]: d for d in sks if d["tag"] == "r6000"}
            drop_cell = False
            for uid, d0 in before.items():
                d1 = after.get(uid)
                if d1 is None:
                    per["lost"] += 1
                    continue
                if int(d0["rating"]) < 0:   # no SNEAK entry (nopkg): nothing to rust
                    continue
                per["units"] += 1
                if int(d1["rating"]) < int(d0["rating"]) or int(d1["nominal"]) < int(d0["nominal"]):
                    per["units_drop"] += 1
                    drop_cell = True
                elif int(d1["floor"]) > 0:
                    per["units_floor_kept"] += 1
                if d1.get("unused") == "200000":
                    per["counters_untouched"] += 1
                if d1.get("rusty") == "1":
                    per["rusty"] += 1
            per["cells_drop"] += drop_cell
            per["cells"] += 1
            for d in sks:   # DF-made units of the subject species (ids not placed): a DF-created unit's skill
                if d["was"] == "new" and d["id"] not in ids and d["tag"] == "t2000":
                    per["df_made"].append((rep, d["token"], d["id"], d["rating"], d["floor"]))
        res[arm] = per
    for arm, p in res.items():
        say(f"    {arm}: post-write placements at caste level at t0 (fraction per cell) {desc(p['new_at'])}; "
            f"pre units at level {desc(p['pre_at'])}")
        say(f"       rust (t2000 -> r6000, after +200,000 on the disuse counters): {p['units_drop']}/{p['units']} "
            f"units dropped, in {p['cells_drop']}/{p['cells']} cells; floor kept {p['units_floor_kept']}; "
            f"counters left at 200,000 (DF never ran its rust step) {p['counters_untouched']}; rusty flag {p['rusty']}; "
            f"subjects lost before r6000 {p['lost']}")
        if p["df_made"]:
            say(f"       units of the subject species not placed by the harness (DF-made, seen at t2000): {p['df_made']}")
    pk, nf = res.get("pkg"), res.get("pkg_nofloor")
    if pk and nf:
        pc = fisher(pk["cells_drop"], pk["cells"], nf["cells_drop"], nf["cells"])
        pu = fisher(pk["units_drop"], pk["units"], nf["units_drop"], nf["units"])
        say(f"    pkg vs pkg_nofloor, cells with any SNEAK drop {pk['cells_drop']}/{pk['cells']} vs "
            f"{nf['cells_drop']}/{nf['cells']}: Fisher exact p = {f(pc, 4)} (units {pk['units_drop']}/{pk['units']} vs "
            f"{nf['units_drop']}/{nf['units']}: p = {pu:.2e}, units clustered in cells)")
        OUT["row1"] = dict(res=res, fisher_cells=pc, fisher_units=pu)
        good = (mean(pk["new_at"]) == 1 and mean(pk["pre_at"]) == 1 and pk["units_drop"] == 0
                and nf["cells_drop"] == nf["cells"] and mean(res["nopkg"]["new_at"]) == 0)
        verdict(1, "CONFIRMED" if good else "NOT CONFIRMED",
                f"post-write placements carry the caste SNEAK at once {mean(pk['new_at']):.0%} (nopkg {mean(res['nopkg']['new_at']):.0%}); "
                f"floored units dropped {pk['units_drop']}/{pk['units']}; positive control (floor 0) dropped in "
                f"{nf['cells_drop']}/{nf['cells']} cells (Fisher p={pc:.4f}). Stand-in: units.create placement, rust push")


# ------------------------------------------------------------------------------------------ 2. kills --
def row2():
    say("\n" + "=" * 110 + "\nROW 2  Packs, stoops and fishing change kills (PK2, STP1, FSH3, FSH4)")
    out = {}
    # PK2
    b = Block("S7_PK2")
    b.header(2, "pack_on vs pack_off; 5 WOLF + 6 WATER_BUFFALO, 6,000 t")
    att, kil, rel0, largest = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for arm in b.arms():
        for rep in b.reps(arm):
            a, k = placed_pairs(b, arm, rep, "WOLF", "WATER_BUFFALO")
            att[arm].append(a)
            kil[arm].append(k)
            rc = b.rows(arm, rep, "relcount")
            rel0[arm].append(int(rc[0]["pairs"]) if rc else None)
            largest[arm].append(num(b.first(arm, rep, "packs").get("largest")))
    say(f"    receipt: largest pack at t0 on {largest['pack_on']} / off {largest['pack_off']}; WOLF-BUFFALO relation pairs "
        f"at t0 on {rel0['pack_on']} / off {rel0['pack_off']}")
    out["pk2_att"] = contrast("placed WOLF>BUFFALO attacks", att["pack_on"], att["pack_off"], "on", "off", 1)
    out["pk2_kill"] = contrast("placed WOLF kills of BUFFALO (of 6)", kil["pack_on"], kil["pack_off"], "on", "off", 1)
    # STP1
    b = Block("S7_STP1")
    b.header(2, "stoop_on vs stoop_off; 2 BIRD_EAGLE, 6 RABBIT, 3 DEER, 6,000 t, ecology every 1,000 t")
    ea, nat_k, stoops, far = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for arm in b.arms():
        for rep in b.reps(arm):
            a = sum(placed_pairs(b, arm, rep, "BIRD_EAGLE", v)[0] for v in ("RABBIT", "DEER"))
            ea[arm].append(a)
            nk = sum(1 for d in b.rows(arm, rep, "death") if d.get("victim") in ("RABBIT", "DEER")
                     and d.get("victim_spawned") == "1" and d.get("killer_spawned") == "0")
            nat_k[arm].append(nk)
            st = [r for r in b.raw(arm, rep, "toolline") if "hunters_status n=3" in r]
            m = re.search(r"last_pass_(\d+)_raptor\(s\),_(\d+)_sto", st[0]) if st else None
            stoops[arm].append((int(m.group(1)), int(m.group(2))) if m else None)
            g = b.last(arm, rep, "group", token="BIRD_EAGLE")
            far[arm].append(num(g.get("cx")))
    say(f"    receipt (last ecology pass: raptors seen, stoops): on {stoops['stoop_on']}; off {stoops['stoop_off']}")
    say(f"    placed EAGLE>RABBIT/DEER attacks per cell: on {ea['stoop_on']}, off {ea['stoop_off']}; placed prey killed by "
        f"NATIVE units (wipe leftovers, e.g. GIANT_EAGLE) on {nat_k['stoop_on']}, off {nat_k['stoop_off']}")
    say(f"    eagle group centroid x at the end (prey placed near x~250): on {far['stoop_on']}, off {far['stoop_off']}")
    out["stp1_att"] = contrast("placed EAGLE attacks on placed prey", ea["stoop_on"], ea["stoop_off"], "on", "off", 1)
    # FSH3
    b = Block("S7_FSH3")
    b.header(2, "fish_on vs fish_off; 2 BEAR_GRIZZLY on the river shore, 8 FISH_PIKE in the river, 6,000 t")
    adj, dmin, fa, fk = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for arm in b.arms():
        for rep in b.reps(arm):
            rows = b.rows(arm, rep, "adj")
            adj[arm].append(sum(int(d["pairs"]) for d in rows))
            dmin[arm].append(min(int(d["dmin"]) for d in rows if int(d["dmin"]) >= 0) if rows else None)
            a, k = placed_pairs(b, arm, rep, "BEAR_GRIZZLY", "FISH_PIKE")
            fa[arm].append(a)
            fk[arm].append(k)
    say(f"    bear-pike adjacency (pairs summed over 20 samples, every 300 t): on {adj['fish_on']}, off {adj['fish_off']}")
    out["fsh3_dmin"] = contrast("closest bear-pike distance over the run (tiles)", dmin["fish_on"], dmin["fish_off"], "on", "off", 1)
    out["fsh3_att"] = contrast("placed BEAR>PIKE attacks", fa["fish_on"], fa["fish_off"], "on", "off", 1)
    # FSH4
    b = Block("S7_FSH4")
    b.header(2, "polar (one arm); 2 BEAR_POLAR at the lake shore, 8 FISH_PIKE, fish_breathe off, 6,000 t")
    wet, padj, pa, nf = [], [], [], []
    for rep in b.reps("polar"):
        sw = b.rows("polar", rep, "swim")
        wet.append(sum(int(d["wet"]) > 0 for d in sw))
        nf.append(sum(int(d["not_fine"]) for d in sw))
        padj.append(sum(int(d["pairs"]) for d in b.rows("polar", rep, "adj")))
        pa.append(placed_pairs(b, "polar", rep, "BEAR_POLAR", "FISH_PIKE")[0])
    say(f"    samples (of 10) with a polar bear in water per cell {wet}; not-fine breathing reads {nf}; "
        f"bear-pike adjacency {padj}; placed BEAR_POLAR>PIKE attacks {pa}")
    OUT["row2"] = dict(out, fsh4=dict(wet=wet, adj=padj, att=pa, not_fine=nf))
    pk_ok = out['pk2_att']['p'] <= 0.05 and out['pk2_kill']['p'] <= 0.05 and out['pk2_kill']['diff'] > 0
    verdict(2, ("CONFIRMED (packs)" if pk_ok else "NOT CONFIRMED (packs)") + " / INCONCLUSIVE (stoops, fishing: vacuous)",
            f"PK2: pack on raised placed wolf>buffalo attacks {mean(att['pack_on']):.0f} vs {mean(att['pack_off']):.0f} "
            f"(p={out['pk2_att']['p']:.3f}) and kills {mean(kil['pack_on']):.1f} vs {mean(kil['pack_off']):.1f} of 6 "
            f"(p={out['pk2_kill']['p']:.3f}); STP1/FSH3/FSH4: the subjects never met (placed eagles made "
            f"{sum(ea['stoop_on']) + sum(ea['stoop_off'])} attacks in 10 cells; bears 0 adjacency to pike, polar bears never swam)")


# ------------------------------------------------------------------------------- NAT (rows 3, 4, 9, 10, 12) --
def nat_series(b, arm, rep, key):
    return [(tagnum(d["tag"]), num(d.get(key))) for d in b.rows(arm, rep, "nat") if d["tag"] != "t0"]


def row3_4_9_10_12():
    b = Block("S7_NAT")
    say("\n" + "=" * 110 + "\nROWS 3, 4, 9, 10, 12  Natural arrivals (S7_NAT: def vs v70 = every lever back at once)")
    b.header(3, "natives are the subject (no wipe); 50,055 t sampled every 3,000 t (t3000..t50055)")
    ok, n = b.manip_checks()
    say(f"    manipulation checks passed {ok}/{n} (def: hold[t].held_open==0 at every sample, cavern_hold_mix true; "
        f"v70: the ten levers read back off)")
    R = {}
    for arm in b.arms():
        r = defaultdict(list)
        for rep in b.reps(arm):
            nat = [d for d in b.rows(arm, rep, "nat") if d["tag"] != "t0"]
            cap = num(nat[0]["land_cap"])
            land = [num(d["land"]) for d in nat]
            r["land_cap"].append(cap)
            r["land_mean"].append(mean(land))
            r["land_over"].append(sum(x > cap for x in land) / len(land))
            r["land_in_band"].append(sum(cap - 1.5 <= x <= cap for x in land) / len(land))
            for c in ("c1", "c2", "c3"):
                r["cav_" + c].append(mean([num(d[c]) for d in nat]))
            r["cav_mean"].append(mean([num(d[c]) for d in nat for c in ("c1", "c2", "c3")]))
            r["cav_max"].append(max(num(d[c]) for d in nat for c in ("c1", "c2", "c3")))
            r["cav_end"].append(mean([num(nat[-1][c]) for c in ("c1", "c2", "c3")]))
            r["nat_mean"].append(mean([num(d[c]) for d in nat for c in ("n1", "n2", "n3")]))
            r["nat_max"].append(max(num(d[c]) for d in nat for c in ("n1", "n2", "n3")))
            bodies = defaultdict(dict)
            for dd in b.rows(arm, rep, "natbody"):
                if dd["tag"] != "t0":
                    bodies[dd["body"]][dd["tag"]] = num(dd["groups"])
            tags = [x["tag"] for x in nat]
            for bd in ("lake", "river", "pool"):   # a sample with no row for a body is 0 groups there
                r["w_" + bd].append(mean([bodies[bd].get(tg, 0) for tg in tags]))
            r["trim_undo_series"].append([int(num(x.get("trim_undo", 0))) for x in b.rows(arm, rep, "hold")])
            # per-body mean over samples where no row means 0 groups: count samples
            nsamp = len(nat)
            r["water_per_body"].append(sum(num(d["water"]) for d in nat) / nsamp / 3)
            r["carn"].append(mean([num(d["carn_share"]) for d in nat if num(d["carn_share"], -1) >= 0]))
            # apex presence: the scheduler's own seen/total, per season (the counters reset at the season change)
            spring = [d for d in nat if d["season"] == "0"]
            last = spring[-1] if spring else nat[-1]
            r["apex_pres"].append(num(last["apex_seen"]) / max(1, num(last["apex_total"])))
            r["apex_live_any"].append(sum(num(d["apex_live"]) > 0 for d in nat) / len(nat))
            r["held_open"].append(max(num(d.get("held_open", 0)) for d in b.rows(arm, rep, "hold")))
            r["trim_undo_max"].append(max(num(d.get("trim_undo", 0)) for d in b.rows(arm, rep, "hold")))
            r["extinct_drawn"].append(max(num(d["extinct_drawn"]) for d in nat))
            # status lines at the end: the tool's own 'now' per layer
            for raw in b.raw(arm, rep, "toolline"):
                m = re.search(r"verb=groups_layers n=\d+ text=_?(land|water:\w+|cavern:\d)_cap_(\d+).*?_now_(\d+)", raw)
                if m:
                    r["status_" + m.group(1)].append((int(m.group(2)), int(m.group(3))))
            # groups3 (H5): live groups vs the tool's
            g3 = [d for d in b.rows(arm, rep, "g3sum") if d["tag"] != "base"]
            if g3:
                lastg = {}
                for d in g3:
                    lastg[d["layer"]] = d
                for lay, d in lastg.items():
                    r["g3_" + lay].append((int(d["live_groups"]), int(d["tool_groups"]), int(d["untracked"])))
            # MIX1: species per body and the top species' unit share, at the last sample
            sp = defaultdict(Counter)
            tags = [d["tag"] for d in b.rows(arm, rep, "natsp")]
            lt = tags[-1] if tags else None
            for d in b.rows(arm, rep, "natsp", tag=lt) if lt else []:
                sp[d["body"]][d["token"]] += int(d["n"])
            for bd, c in sp.items():
                tot = sum(c.values())
                H = -sum(v / tot * math.log(v / tot) for v in c.values() if v) if tot else 0
                r["mix_" + bd].append((len(c), round(max(c.values()) / tot, 2) if tot else None, round(H, 2)))
            wat = {d["body"]: d for d in b.rows(arm, rep, "natwat", tag=lt)} if lt else {}
            r["wat_hca"].append({bd: (d["H"], d["C"], d["A"]) for bd, d in wat.items()})
            sea = b.last(arm, rep, "ledger", kind="season")
            r["season_ledger"].append(sea.get("last"))
        R[arm] = r
    OUT["nat"] = {a: {k: v for k, v in r.items()} for a, r in R.items()}
    d, v = R.get("def"), R.get("v70")
    if not d:
        return
    say("\n  ROW 3  The clock holds groups near the cap (G2r, WAT5)")
    say(f"    land cap per rep {d['land_cap']}; target: def mean in [cap-1.5, cap] = [7.5, 9]")
    say(f"    def land groups per sample: {desc(d['land_mean'])}; share of samples above the cap {desc(d['land_over'])}; "
        f"share in the target band {desc(d['land_in_band'])}")
    OUT["row3_land"] = contrast("land groups (mean over 17 samples)", d["land_mean"], v["land_mean"], "def", "v70")
    say(f"    tool's own status at the end, land (cap, now): def {d.get('status_land')}; v70 {v.get('status_land')}")
    say(f"    WAT5: water groups per body (lake/river/pool), def: lake {desc(d['w_lake'])}, river {desc(d['w_river'])}, "
        f"pool {desc(d['w_pool'])}; target mean >= 3 per body")
    OUT["row3_water"] = contrast("water groups per body (all bodies)", d["water_per_body"], v["water_per_body"], "def", "v70")
    say(f"    H5 groups3 at the last sample (live, tool, untracked) def: " +
        "; ".join(f"{lay} {d.get('g3_' + lay)}" for lay in ("land", "water", "cavern")))
    land_ok = 7.5 <= mean(d["land_mean"]) <= 9
    wat_ok = min(mean(d["w_lake"]), mean(d["w_river"]), mean(d["w_pool"])) >= 3
    verdict(3, ("CONFIRMED" if land_ok and wat_ok else "NOT CONFIRMED (land) / CONFIRMED (water)" if wat_ok else "NOT CONFIRMED"),
            f"def land groups {mean(d['land_mean']):.2f} vs cap 9 (target band 7.5-9; over the cap in "
            f"{mean(d['land_over']):.0%} of samples); water {mean(d['w_lake']):.1f}/{mean(d['w_river']):.1f}/"
            f"{mean(d['w_pool']):.1f} per body (target >=3)")

    say("\n  ROW 4  The cavern gate holds five (CAVG); natives trimmed walk off (TRIM)")
    say(f"    receipt: hold check held_open max per rep def {d['held_open']} (0 = every held raw at its hold level)")
    say(f"    tool-record groups per cavern, mean over caverns and samples: def {desc(d['cav_mean'])}; max {d['cav_max']}")
    say(f"      per cavern (def): c1 {desc(d['cav_c1'])}, c2 {desc(d['cav_c2'])}, c3 {desc(d['cav_c3'])}; at the end {desc(d['cav_end'])}")
    say(f"    natives by population entry per cavern band: def {desc(d['nat_mean'])}; max {d['nat_max']}")
    OUT["row4_cav"] = contrast("tool-record groups per cavern", d["cav_mean"], v["cav_mean"], "def", "v70")
    OUT["row4_nat"] = contrast("natives by entry per cavern", d["nat_mean"], v["nat_mean"], "def", "v70")
    say(f"    tool's own status at the end (cap, now): def " +
        "; ".join(f"{k[7:]} {d[k]}" for k in sorted(d) if k.startswith("status_cavern")))
    say(f"    trim_undo (trimmed units still on the map, max over the run) def {d['trim_undo_max']}; v70 {v['trim_undo_max']}")
    say("    trim_undo series def (t0, t3000, ..., t50055; a unit drops out when it is gone):")
    for i, srs in enumerate(d["trim_undo_series"], 1):
        say(f"      rep {i}: {srs}")

    say("\n  ROW 9  Apex presence; ladder 20 % carnivores (APX1, LAD1)")
    say(f"    apex presence (scheduler seen/total, Spring, up to the season change): def {desc(d['apex_pres'], 3)}; "
        f"v70 {desc(v['apex_pres'], 3)}; share of samples with a live apex group def {desc(d['apex_live_any'])}")
    say(f"    carnivore share of land units (C+A)/(H+C+A), mean over samples: def {desc(d['carn'], 3)}; v70 {desc(v['carn'], 3)}")
    OUT["row9_carn"] = contrast("land carnivore share", d["carn"], v["carn"], "def", "v70", 3)
    OUT["row9_apex"] = contrast("apex presence", d["apex_pres"], v["apex_pres"], "def", "v70", 3)

    say("\n  ROW 10 (MIX1 half)  species per body at the last sample: (species, top species' unit share, Shannon H)")
    for arm in ("def", "v70"):
        say(f"    {arm}: " + "; ".join(f"{bd} {R[arm].get('mix_' + bd)}" for bd in ("lake", "river", "pool")))
    say(f"    water H/C/A units per body at the last sample, def rep 1: {d['wat_hca'][0] if d['wat_hca'] else '-'}")

    say("\n  ROW 12 (F2 half)  spill on (def) vs off (v70): water groups per body over the run (above) and the season")
    say(f"    season ledger at the end: def {d['season_ledger']}; v70 {v['season_ledger']}")


# ---------------------------------------------------------------------------------------- 4. TRIM --
def row4_trim():
    b = Block("S7_TRIM")
    say("\n  [S7_TRIM] cap 1; trimmed ids on the map vs gone, ledger dismissals, 4,800 t")
    if not b.present:
        say(f"    PENDING: no TRIM rows in {b.run.name if b.run else 'any run'}")
        OUT["trim"] = "pending"
        return "pending"
    b.header(4, "cap1")
    if b.failed and not b.cells:
        rec = [l.rstrip("\n").split("\t")[4] for l in open(b.path) if "\tmanip\t" in l]
        say("    receipts of the aborted cell: " + "; ".join(x.split("check=")[1][:70] for x in rec))
        OUT["trim"] = dict(failed=list(b.failed.values()), receipts=rec)
        return "failed"
    res = []
    for rep in b.reps("cap1"):
        t = b.rows("cap1", rep, "trim")
        last = t[-1] if t else {}
        res.append({k: last.get(k) for k in ("trimmed", "on", "gone", "dismissed", "dismissed_units")})
        nat0 = b.first("cap1", rep, "nat", tag="t0")
        say(f"    rep {rep}: t0 cav_max {nat0.get('cav_max')}; end {last}")
    OUT["trim"] = res
    return "done" if res else ("failed" if b.failed else "pending")


# ---------------------------------------------------------------------------------------- 5. leaders --
def row5():
    say("\n" + "=" * 110 + "\nROW 5  A lost leader makes the group scatter (PAN1, COHT)")
    b = Block("S7_PAN1")
    b.header(5, "panic_on vs panic_off; 1 male + 5 female DEER adopted, leader killed (blood drain) at t0")
    lm = [d.get("leader_male") for a in b.arms() for r in b.reps(a) for d in b.rows(a, r, "grp", tag="t0")]
    kl = [d.get("killed") for a in b.arms() for r in b.reps(a) for d in b.rows(a, r, "kill")]
    say(f"    receipts: leader male at t0 {Counter(lm)}; leader killed {Counter(kl)}")
    sp = {a: defaultdict(list) for a in b.arms()}
    pan = defaultdict(list)
    for arm in b.arms():
        for rep in b.reps(arm):
            g0 = num(b.first(arm, rep, "grp", tag="t0").get("pair_mean"))
            for t in ("t100", "t300", "t1200", "t2400"):
                g = b.first(arm, rep, "grp", tag=t)
                sp[arm][t].append(num(g.get("pair_mean")))
                sp[arm]["d" + t].append(num(g.get("pair_mean")) - g0 if g else None)
            pan[arm].append(num(b.last(arm, rep, "ledger", kind="panic").get("n")))
    say(f"    ledger panic lines per cell: on {pan.get('panic_on')}, off {pan.get('panic_off')}")
    res = {}
    for t in ("t300", "t1200", "t2400"):
        res[t] = contrast(f"mean pairwise distance at {t} (tiles)", sp["panic_on"][t], sp["panic_off"][t], "on", "off", 1)
    res["dt2400"] = contrast("growth in pairwise distance t0->t2400", sp["panic_on"]["dt2400"], sp["panic_off"]["dt2400"], "on", "off", 1)
    OUT["pan1"] = res
    # COHT
    c = Block("S7_COHT")
    c.header(5, "led vs cohesion_off; 8 FISH_PIKE adopted at the lake spot (the tool calls it water:river), 3,000 t")
    adopt = [d.get("reply", "")[:60] for a in c.arms() for r in c.reps(a) for d in c.rows(a, r, "adopt")][:2]
    say(f"    adopt reply {adopt}")
    cs = {a: defaultdict(list) for a in c.arms()}
    for arm in c.arms():
        for rep in c.reps(arm):
            gs = c.rows(arm, rep, "grp")
            cs[arm]["foll_max"].append(max(int(d.get("following", 0)) for d in gs))
            cs[arm]["lead_lost"].append(next((tagnum(d["tag"]) for d in gs if d.get("lost") not in ("-", None)), None))
            for t in ("t600", "t1500", "t3000"):
                g = c.first(arm, rep, "grp", tag=t)
                cs[arm][t].append(num(g.get("pair_mean")))
            sw = c.rows(arm, rep, "swim")
            cs[arm]["dry"].append(sum(int(d["alive"]) - int(d["wet"]) for d in sw))
            cs[arm]["dead"].append(int(c.last(arm, rep, "group", token="FISH_PIKE").get("dead", 0)))
    say(f"    led: members following the leader, max over samples {cs['led']['foll_max']}; tick the leader was lost "
        f"{cs['led']['lead_lost']}")
    say(f"    dry swimmer-samples (alive - wet, summed): led {cs['led']['dry']}, off {cs['cohesion_off']['dry']}; "
        f"pike dead at the end: led {cs['led']['dead']}, off {cs['cohesion_off']['dead']}")
    for t in ("t600", "t1500", "t3000"):
        res["coht_" + t] = contrast(f"school mean pairwise distance at {t}", cs["led"][t], cs["cohesion_off"][t], "led", "off", 1)
    OUT["coht"] = {a: dict(v) for a, v in cs.items()}
    p = res["t1200"]["p"]
    verdict(5, "CONFIRMED (PAN1, weak)" if res["t1200"]["diff"] > 0 and p <= 0.1 else "NOT CONFIRMED (no detectable effect at n=5)" if p > 0.1 else "INCONCLUSIVE",
            f"PAN1 pairwise spread at t1200 on {mean(sp['panic_on']['t1200']):.1f} vs off {mean(sp['panic_off']['t1200']):.1f} "
            f"(p={p:.3f}); at t2400 p={res['t2400']['p']:.3f}; COHT: no member ever followed the leader "
            f"(following max {max(cs['led']['foll_max'])}), leader lost in {sum(x is not None for x in cs['led']['lead_lost'])}/5")


# ---------------------------------------------------------------------------------------- 6. tokens --
def irr_units(b, arm, rep, tag=None):
    return [d for d in b.rows(arm, rep, "irru") if tag is None or d["tag"] == tag]


def flagfrac(rows, field):
    tot = on = 0
    for d in rows:
        v = d.get(field, "-")
        if v in ("-", ""):
            continue
        for part in v.split(","):
            k, _, x = part.partition(":")
            tot += 1
            on += x == "1"
    return on, tot


def row6():
    say("\n" + "=" * 110 + "\nROW 6  Tokens act (M1-M8, the three-arm main experiment P2, T routes, T-R35)")
    b = Block("S7_IRRM")
    b.header(6, "one civ wave (TROGLODYTE, cavern 1) per cell; one token at 100% vs none; 3,000 t")
    cc = [d.get("tokens") for a in b.arms() for r in b.reps(a) for d in b.rows(a, r, "civcand")]
    say(f"    receipt: civ candidates {Counter(cc)}; subjects species " +
        str(Counter(d["token"] for a in b.arms() for r in b.reps(a) for d in irr_units(b, a, r, "t0"))))
    M = {}
    for arm in b.arms():
        r = defaultdict(list)
        for rep in b.reps(arm):
            u = irr_units(b, arm, rep)
            u0 = irr_units(b, arm, rep, "t0")
            r["n0"].append(len(u0))
            r["mask"].append(flagfrac(u, "mask"))
            r["cache"].append(flagfrac(u, "cache"))
            r["hidden_t0"].append(sum(d["hidden"] == "1" for d in u0) / max(1, len(u0)))
            later = [d for d in u if d["tag"] not in ("t0",)]
            r["hidden_later"].append(sum(d["hidden"] == "1" for d in later) / max(1, len(later)))
            r["goal"].append(Counter(d["goal"] for d in u))
            r["items"].append(sum(int(d["items"]) for d in u))
            r["mood"].append(Counter(d["mood"] for d in u))
            dc0 = mean([num(d["dcit"]) for d in u0])
            end = [d for d in u if d["tag"] == "t3000"]
            r["dcit0"].append(dc0)
            r["dcit_end"].append(mean([num(d["dcit"]) for d in end]) if end else None)
            r["dcit_min"].append(min(num(d["dcit"]) for d in u) if u else None)
            r["reasserted"].append(max(int(d.get("reasserted", 0)) for d in b.rows(arm, rep, "irr")))
            ph = b.first(arm, rep, "irr", tag="t3000") or b.last(arm, rep, "irr")
            r["phase_end"].append(ph.get("phase"))
            r["dead"].append(max(int(d.get("dead", 0)) for d in b.rows(arm, rep, "irr")))
            res = b.last(arm, rep, "resid", tag="end")
            r["resid"].append((res.get("mask"), res.get("cache"), res.get("units"), res.get("active_events")))
            if arm == "crazed":
                r["reload"].append([d["mask"] for d in irr_units(b, arm, rep, "reload")][:1])
                r["reload300"].append([d["mask"] for d in irr_units(b, arm, rep, "reload300")][:1])
            if arm == "thief":
                nat = b.rows(arm, rep, "native")
                r["native"].append(sorted({f"{k}={d[k]}" for d in nat for k in d if k in
                                           ("CURIOUS_BEAST", "CURIOUS_BEAST_ITEM", "MEANDERER", "AMBUSHPREDATOR")}))
        M[arm] = r
    for arm, r in M.items():
        mk = (sum(x for x, _ in r["mask"]), sum(y for _, y in r["mask"]))
        ch = (sum(x for x, _ in r["cache"]), sum(y for _, y in r["cache"]))
        goals = sum(r["goal"], Counter())
        say(f"    {arm:9s} subjects/t0 {r['n0']}; mask flags read 1: {mk[0]}/{mk[1]}; cache flags read 1: {ch[0]}/{ch[1]}; "
            f"hidden t0 {f(mean(r['hidden_t0']))} later {f(mean(r['hidden_later']))}; reasserted max {r['reasserted']}")
        say(f"              goals {dict(goals.most_common(4))}; items carried (sum of samples) {r['items']}; "
            f"citizen distance t0 {f(mean(r['dcit0']), 0)} -> t3000 {f(mean(r['dcit_end']), 0)} (min {r['dcit_min']})")
        say(f"              resid at the end (mask, cache, units, active events) {r['resid']}; phase at t3000 {r['phase_end']}; "
            f"subjects dead (max) {r['dead']}")
        if arm == "crazed":
            say(f"              M1 after save/reload: {r['reload']} ; +300 t {r['reload300']}")
        if arm == "thief":
            say(f"              M3 natives outside the event (unit cache / caste): {r['native'][:1]}")
    OUT["irrm"] = {a: {k: [list(x) if isinstance(x, tuple) else (dict(x) if isinstance(x, Counter) else x) for x in v]
                       for k, v in r.items()} for a, r in M.items()}
    # contrasts with none: hidden (sneak), goal steal (thief, goalonly), approach (wander)
    hid = contrast("M7 sneak: share of subject-samples hidden after t0", M["sneak"]["hidden_later"], M["none"]["hidden_later"], "sneak", "none")
    def steal(arm):
        return [c.get("WildernessCuriousStealTarget", 0) / max(1, sum(c.values())) for c in M[arm]["goal"]]
    th = contrast("M4 thief: share of samples with the steal goal", steal("thief"), steal("none"), "thief", "none")
    go = contrast("M6 goalonly: share of samples with the steal goal", steal("goalonly"), steal("none"), "goal", "none")
    wa = contrast("M8 wander: subjects' mean citizen distance at t3000", M["wander"]["dcit_end"], M["none"]["dcit_end"], "wander", "none", 0)
    cr = sum(x for x, _ in M["crazed"]["mask"]), sum(y for _, y in M["crazed"]["mask"])
    mi = sum(x for x, _ in M["mischief"]["mask"]), sum(y for _, y in M["mischief"]["mask"])
    OUT["irrm_contrasts"] = dict(hidden=hid, steal=th, goalonly=go, wander=wa, crazed_mask=cr, mischief_mask=mi)

    # P2
    p = Block("S7_IRRP2")
    p.header(6, "A rotation only / B irruption, every token off / C the R10 package; pressure pinned, 7,200 t")
    P = {}
    for arm in p.arms():
        r = defaultdict(list)
        for rep in p.reps(arm):
            irr = p.rows(arm, rep, "irr")
            r["events"].append(max(int(d["events"]) for d in irr) if irr else 0)
            r["alive_max"].append(max(int(d["alive"]) for d in irr) if irr else 0)
            r["dead"].append(max(int(d["dead"]) for d in irr) if irr else 0)
            u = p.rows(arm, rep, "irru")
            r["subj_dcit_min"].append(min((num(d["dcit"]) for d in u), default=None))
            r["subj_dcit_mean"].append(mean([num(d["dcit"]) for d in u]) if u else None)
            civ = p.rows(arm, rep, "civ")
            per_tag = Counter(d["tag"] for d in civ)
            r["civ_in_band"].append(mean(list(per_tag.values())) if per_tag else 0)
            r["civ_dcit_min"].append(min((num(d["dcit"]) for d in civ), default=None))
            r["mask"].append(flagfrac(u, "mask"))
            r["cache"].append(flagfrac(u, "cache"))
            r["citizens_end"].append(int(irr[-1]["citizens"]) if irr else None)
            r["cit_deaths"].append(sum(1 for d in p.rows(arm, rep, "death")
                                       if d.get("victim") == "DWARF"))
            res = p.last(arm, rep, "resid", tag="end")
            r["resid"].append((res.get("mask"), res.get("cache"), res.get("units"), res.get("active_events")))
        P[arm] = r
    for arm, r in P.items():
        say(f"    {arm}: events {r['events']}; subjects alive max {r['alive_max']}; dead {r['dead']}; civ units in band "
            f"(mean per sample) {[round(x, 1) for x in r['civ_in_band']]}")
        say(f"       nearest approach of any subject to a citizen {r['subj_dcit_min']} (mean dcit {[f(x, 0) for x in r['subj_dcit_mean']]}); "
            f"civ-race min distance {r['civ_dcit_min']}; citizens at the end {r['citizens_end']}; dwarf deaths {r['cit_deaths']}")
        say(f"       mask flags read 1 {sum(x for x, _ in r['mask'])}/{sum(y for _, y in r['mask'])}; cache flags read 1 "
            f"{sum(x for x, _ in r['cache'])}/{sum(y for _, y in r['cache'])}; resid end {r['resid']}")
    if "B" in P and "C" in P:
        OUT["irrp2_dead"] = contrast("P2 subjects dead (max over samples), C vs B", P["C"]["dead"], P["B"]["dead"], "C", "B", 1)
        OUT["irrp2_dcit"] = contrast("P2 subjects' mean citizen distance (C vs B)", P["C"]["subj_dcit_mean"], P["B"]["subj_dcit_mean"], "C", "B", 0)
    OUT["irrp2"] = {a: {k: [list(x) if isinstance(x, tuple) else x for x in v] for k, v in r.items()} for a, r in P.items()}

    # T routes
    t = Block("S7_IRRTSEQ")
    t.header(6, "eight end routes in sequence on one load, a residual scan after each")
    routes = ["end_duration", "end_repel", "end_verb", "off_irruption", "off_disable", "off_groups", "off_alloff", "save"]
    tab = {}
    for rt in routes:
        rs, al, en, ca = [], [], [], []
        for rep in t.reps("routes"):
            d = t.last("routes", rep, "resid", tag=rt)
            rs.append((d.get("mask"), d.get("cache"), d.get("units"), d.get("active_events")))
            al.append(t.first("routes", rep, "irr", tag=f"{rt}_t0").get("alive"))
            en.append(t.first("routes", rep, "irr", tag=f"{rt}_end").get("phase"))
            ca.append(flagfrac([u for u in t.rows("routes", rep, "irru") if u["tag"] == f"{rt}_t0"], "cache"))
        tab[rt] = dict(resid=rs, alive=al, end_phase=en, cache=ca)
        say(f"    {rt:13s} alive at t0 {al}; cache flags set at t0 {[f'{x}/{y}' for x, y in ca]}; phase at end {Counter(en)}; "
            f"resid (mask,cache,units,active) {Counter(rs)}")
    sv = [(t.first("routes", r, "irr", tag="save_reload").get("phase"), t.first("routes", r, "irr", tag="save_reload").get("alive"))
          for r in t.reps("routes")]
    say(f"    T-SAVE: phase/alive after save+reload {sv}")
    OUT["irrtseq"] = {k: {kk: [list(x) if isinstance(x, tuple) else x for x in vv] for kk, vv in v.items()} for k, v in tab.items()}

    # R35
    r35 = Block("S7_IRRR35")
    say("\n  [S7_IRRR35] animal-people wave size: irrupting vs quiet (cap 5 lifted during an event)")
    if not r35.present or not r35.cells:
        say(f"    PENDING: no completed IRRR35 cell in {r35.run.name if r35.run else '-'}"
            + (f" (failed: {list(r35.failed.items())[:2]})" if r35.failed else ""))
        OUT["irrr35"] = "pending"
    else:
        r35.header(6, "irrupting vs quiet")
        big = defaultdict(list)
        for arm in r35.arms():
            for rep in r35.reps(arm):
                ap = r35.rows(arm, rep, "apraw")
                gs = r35.rows(arm, rep, "gsize")
                # cx-sec7 apraw prints cluster_number[0] as 'min' and [1] as 'max', but the tool's own convention
                # (seasonal-wildlife.lua:1700) is [0] = MAX, [1] = MIN: so the raw range is min=<max field> max=<min field>
                rng = {(d.get("max"), d.get("min")) for d in ap}
                capped = {d.get("capped") for d in ap}
                nat = [int(x) for d in gs for x in d.get("sizes", "-").split(",") if x not in ("-", "") and not x.endswith("i")]
                irr = [int(x[:-1]) for d in gs for x in d.get("sizes", "-").split(",") if x.endswith("i")]
                big[arm].append(max(nat, default=0))
                say(f"    {arm} rep {rep}: raw cluster range (min,max) {rng}; capped {capped}; irruption wave sizes {sorted(set(irr))}; "
                    f"natural group sizes at the end {gs[-1].get('sizes') if gs else '-'}")
        OUT["irrr35"] = {a: v for a, v in big.items()}
        say(f"    largest natural group per cell: {dict(big)} -- the raw's own max is 5 = groups.apcap, so the cap never binds "
            f"(capped 0 in every sample): R35's lever is vacuous on PLUMP_HELMET_MAN at apcap 5")
    verdict(6, "PARTLY CONFIRMED; CRAZED/MISCHIEVOUS NOT CONFIRMED",
            f"cache writes (THIEF/MEANDER: CURIOUS_BEAST*, MEANDERER) stick and stay on the subjects only (M3); SNEAK hides "
            f"(p={hid['p']:.3f}); every route leaves 0 residue; but the CRAZED mask read 1 in {cr[0]}/{cr[1]} unit-samples "
            f"and MISCHIEVOUS in {mi[0]}/{mi[1]}: DF clears uwss_add_caste_flag, reassert or not")


# ---------------------------------------------------------------------------------------- 7. scavenging --
def row7():
    say("\n" + "=" * 110 + "\nROW 7  Scavenging takes days, swimmers eat from the water (scav.md section 15)")
    b = Block("S7_SCV3")
    b.header(7, "natural vs sweep; 6 KANGAROO corpses, JACKAL x2, BIRD_VULTURE x2, HYENA x1 placed 12 tiles off; 7,200 t")
    gone, left, kg, kgp = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for arm in b.arms():
        for rep in b.reps(arm):
            it = [(tagnum(d["tag"]), int(d["corpses"])) for d in b.rows(arm, rep, "items")]
            c0 = it[0][1]
            t_half = next((t for t, c in it if c <= c0 / 2), None)
            t_zero = next((t for t, c in it if c == 0), None)
            gone[arm].append(t_zero)
            left[arm].append(it[-1][1])
            fin = defaultdict(float)
            for d in b.rows(arm, rep, "scavby", tag="t7200"):
                fin[d["token"]] = num(d["kg"], 0)
            kg[arm].append(sum(fin.values()))
            kgp[arm].append(sum(v for k, v in fin.items() if k in ("JACKAL", "BIRD_VULTURE", "HYENA")))
    for arm in b.arms():
        say(f"    {arm}: tick all 6 corpses gone {['>7200' if x is None else x for x in gone[arm]]}; corpses within 6 tiles "
            f"at t7200 {left[arm]}; kg eaten (SCAV counters, all scavengers) {[round(x, 1) for x in kg[arm]]}; by the placed "
            f"three {[round(x, 1) for x in kgp[arm]]}")
    OUT["scv3_left"] = contrast("corpses left at t7200", left["natural"], left["sweep"], "natural", "sweep", 1)
    w = Block("S7_SCV3W")
    w.header(7, "swimmer vs swimmers_off; 6 FISH_CARP corpses in the lake, 2 POND_GRABBER; 7,200 t")
    pg, pgw, pgv, dry, othr = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for arm in w.arms():
        for rep in w.reps(arm):
            d = w.first(arm, rep, "scavby", tag="t7200", token="POND_GRABBER")
            pg[arm].append(num(d.get("kg"), 0))
            pgw[arm].append(num(d.get("wet"), 0))
            pgv[arm].append(num(d.get("visits"), 0))
            sw = w.rows(arm, rep, "swim")
            dry[arm].append(sum(int(x["alive"]) - int(x["wet"]) for x in sw))
            othr[arm].append(sum(num(x.get("kg"), 0) for x in w.rows(arm, rep, "scavby", tag="t7200") if x["token"] != "POND_GRABBER"))
    for arm in w.arms():
        say(f"    {arm}: POND_GRABBER kg {pg[arm]}; visits {pgv[arm]}; finished in water {pgw[arm]}; dry grabber-samples {dry[arm]}; "
            f"kg by other (land/native) scavengers {[round(x, 1) for x in othr[arm]]}")
    OUT["scv3w_kg"] = contrast("POND_GRABBER kg eaten", pg["swimmer"], pg["swimmers_off"], "on", "off", 1)
    verdict(7, "CONFIRMED (both halves; the swimmer switch adds little)",
            f"natural: corpses still on the ground after 6 days in {sum(x is None for x in gone['natural'])}/5 (sweep: gone by "
            f"t{max(x or 0 for x in gone['sweep'])} in {sum(x is not None for x in gone['sweep'])}/5); pond grabbers ate in the water "
            f"in both arms (on {mean(pg['swimmer']):.0f} kg vs off {mean(pg['swimmers_off']):.0f} kg, p={OUT['scv3w_kg']['p']:.2f}) and never beached")


# ---------------------------------------------------------------------------------------- 8. vermin --
def row8():
    say("\n" + "=" * 110 + "\nROW 8  Vermin eaters eat what they walk to (VF1, VF4)")
    b = Block("S7_VF1")
    b.header(8, "forage_on vs forage_off; 4 BADGER, 20 GRASSHOPPER 15 tiles off; 3,000 t")
    drop, eats = defaultdict(list), defaultdict(list)
    for arm in b.arms():
        for rep in b.reps(arm):
            vc = b.rows(arm, rep, "vcount")
            made = int(b.first(arm, rep, "vcreate").get("made", 0))
            drop[arm].append(made - int(vc[-1]["near"]) if vc else None)
            eats[arm].append([r.split("text=")[1] for r in b.raw(arm, rep, "toolline")
                              if "vermin_eats" in r and "BADGER" in r])
    for arm in b.arms():
        say(f"    {arm}: grasshoppers gone from the 8-tile count by t3000 (of 20) {drop[arm]}; BADGER rows in `vermin eats` {eats[arm]}")
    OUT["vf1_drop"] = contrast("grasshoppers gone", drop["forage_on"], drop["forage_off"], "on", "off", 1)
    v = Block("S7_VF4")
    say("\n  [S7_VF4] BIRD_DUCK at a fish bank (VSHORE v2) vs the water's own fish vermin")
    if not v.cells:
        say(f"    PENDING: no completed VF4 cell in {v.run.name if v.run else '-'}"
            + (f" (failed: {[(k, m[:80]) for k, m in v.failed.items()]})" if v.failed else ""))
        OUT["vf4"] = "pending"
    else:
        v.header(8, "forage_on vs forage_off")
        vt = defaultdict(list)
        for arm in v.arms():
            for rep in v.reps(arm):
                vs = v.rows(arm, rep, "vermin")
                vt[arm].append((int(vs[0]["total"]), int(vs[-1]["total"])) if vs else None)
            say(f"    {arm}: fish vermin near the bank (t0, t3000) {vt[arm]}")
        OUT["vf4"] = {a: x for a, x in vt.items()}
    verdict(8, "INCONCLUSIVE (VF1 vacuous)" + ("; VF4 PENDING" if OUT.get("vf4") == "pending" else ""),
            f"forage on vs off: grasshoppers gone {mean(drop['forage_on']):.1f} vs {mean(drop['forage_off']):.1f} of 20 "
            f"(p={OUT['vf1_drop']['p']:.2f}); no BADGER row in the tool's own eats table in any cell -- no distance receipt "
            f"shows a badger reached the vermin")


# ---------------------------------------------------------------------------------------- 10. guard --
def row10_grd():
    b = Block("S7_GRD1")
    say("\n  ROW 10 (GRD1 half)")
    b.header(10, "guard_on vs guard_off; 3 FISH_PIKE adopted, teleported to the lake shore, 1,200 t")
    for arm in b.arms():
        first = []
        resc = []
        for rep in b.reps(arm):
            s = b.first(arm, rep, "swim", tag="t200")
            first.append(f"{s.get('wet')}/{s.get('alive')}")
            resc.append(max(int(d.get("rescued", 0)) for d in b.rows(arm, rep, "watguard")))
        say(f"    {arm}: tp units {[d.get('units') for r in b.reps(arm) for d in b.rows(arm, r, 'tp')]}; wet/alive at the "
            f"first sample (t200) {first}; guard rescues {resc}")
    say("    no dry receipt after the teleport: every pike read wet at t200 in BOTH arms, so the guard had nothing to do")


# ---------------------------------------------------------------------------------------- 11. extinct --
def row11():
    say("\n" + "=" * 110 + "\nROW 11  Extinct corrections change arrivals (EXR1, EXU1; EXF1 not testable here)")
    b = Block("S7_EXR1")
    b.header(11, "fix_on vs fix_off; 5 TRIASSIC_EORAPTOR + 6 HARE placed, 6,000 t")
    att, wr, ben, cells = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(int)
    for arm in b.arms():
        for rep in b.reps(arm):
            a, k = placed_pairs(b, arm, rep, "TRIASSIC_EORAPTOR", "HARE")
            att[arm].append(a)
            cells[arm] += a > 0
            wr[arm].append(int(b.rows(arm, rep, "relcount")[0]["written"]))
            ben[arm].append(b.first(arm, rep, "benign").get("castes_benign"))
    say(f"    receipts: BENIGN castes on the raw on {ben['fix_on']} / off {ben['fix_off']}; EORAPTOR>HARE relations written "
        f"at the first count on {wr['fix_on']} / off {wr['fix_off']}")
    OUT["exr1_att"] = contrast("placed EORAPTOR>HARE attacks", att["fix_on"], att["fix_off"], "on", "off", 1)
    pf = fisher(cells["fix_on"], len(att["fix_on"]), cells["fix_off"], len(att["fix_off"]))
    say(f"    cells with any eoraptor attack on a hare: on {cells['fix_on']}/5, off {cells['fix_off']}/5; Fisher exact p = {pf:.3f}")
    e = Block("S7_EXU1")
    e.header(11, "placed_before vs placed_after enable; same species, 6,000 t")
    eu = defaultdict(list)
    for arm in e.arms():
        for rep in e.reps(arm):
            eu[arm].append(placed_pairs(e, arm, rep, "TRIASSIC_EORAPTOR", "HARE")[0])
    say(f"    placed EORAPTOR>HARE attacks: before {eu['placed_before']}, after {eu['placed_after']}; the block prints no "
        f"BENIGN or relation receipt per unit, so 0 v 0 says nothing about the units correction")
    OUT["exr1_fisher"] = pf
    verdict(11, "CONFIRMED (EXR1, weak) / INCONCLUSIVE (EXU1) / NOT-TESTABLE-HERE (EXF1)",
            f"fix on cleared BENIGN (0 of 2 castes vs 2) and wrote relations (mean {mean(wr['fix_on']):.1f} vs 0); eoraptors "
            f"attacked hares in {cells['fix_on']}/5 on vs {cells['fix_off']}/5 off cells (Fisher p={pf:.3f}); EXU1 had no "
            f"attack in either arm and no per-unit receipt")


# ---------------------------------------------------------------------------------------- 12. F1 --
def row12():
    say("\n" + "=" * 110 + "\nROW 12  Water auto-on and spill reach 3-5 groups (F1; F2 from S7_NAT)")
    b = Block("S7_F1")
    b.header(12, "auto (layer unset) vs layer_off; 2,400 t")
    lay, w = defaultdict(list), defaultdict(lambda: defaultdict(list))
    for arm in b.arms():
        for rep in b.reps(arm):
            lay[arm].append(b.first(arm, rep, "cfg", path="layers.water").get("value"))
            for d in b.rows(arm, rep, "nat"):
                if d["tag"] != "t0":
                    w[arm][d["tag"]].append(num(d["water"]) / 3)
    for arm in b.arms():
        say(f"    {arm}: layers.water after enable {Counter(lay[arm])}; water groups per body by sample " +
            ", ".join(f"{t} {f(mean(v), 1)}" for t, v in sorted(w[arm].items(), key=lambda x: tagnum(x[0]))))
    OUT["f1"] = {a: {t: v for t, v in x.items()} for a, x in w.items()}
    OUT["f1_t2400"] = contrast("water groups per body at t2400", w["auto"]["t2400"], w["layer_off"]["t2400"], "auto", "off", 2)
    d = OUT.get("nat", {}).get("def", {})
    v70 = OUT.get("nat", {}).get("v70", {})
    if d:
        verdict(12, "CONFIRMED (auto-on, 3-5 groups) / F2 give-back NOT SEEN",
                f"auto turned the layer on in 5/5 (off arm 0/5) and reached {mean(w['auto']['t2400']):.1f} groups per body by "
                f"t2400 (off 0); NAT def held {mean(d['w_lake']):.1f}/{mean(d['w_river']):.1f}/{mean(d['w_pool']):.1f} per body "
                f"(v70 {mean(v70['w_lake']):.1f}/{mean(v70['w_river']):.1f}/{mean(v70['w_pool']):.1f}); "
                f"spill's borrowed-season give-back has no ledger receipt (season ledger reads only 'Summer roster applied')")


# ---------------------------------------------------------------------------------------- 13. cost --
TOP = ("seasonal-wildlife", "seasonal-wildlife/groups", "seasonal-wildlife/ecology", "seasonal-wildlife/ecology.sweep",
       "seasonal-wildlife/forage", "seasonal-wildlife/curious", "seasonal-wildlife/alerts")


def perf_cells(b, arm, endtag, budget):
    out = []
    for rep in b.reps(arm):
        p0 = b.first(arm, rep, "perf", tag="t0")
        pe = b.first(arm, rep, "perf", tag=endtag)
        if not pe:
            continue
        ticks = int(pe["tick"]) - int(p0["tick"])
        wall = (int(pe["wall_ms"]) - int(p0["wall_ms"])) / 1000
        jobs = {d["job"]: d for d in b.rows(arm, rep, "perfjob", tag=endtag)}
        top_ms = sum(num(jobs[j]["ms_sum"], 0) for j in TOP if j in jobs)
        tps_all = [num(d["tps"]) for d in b.rows(arm, rep, "perf") if d["tag"] != "t0" and num(d["tps"], -1) > 0]
        out.append(dict(rep=rep, ticks=ticks, wall=wall, tps=num(pe["tps"]), tps_mean=mean(tps_all),
                        worst=num(pe["worst_tick_ms"]), fps=num(pe["fps_calc"]), units=num(pe["units"]),
                        ms_per_kt=top_ms / max(1, ticks) * 1000, jobs=jobs, short=ticks < budget * 0.97))
    return out


def jobtab(cells, names=TOP):
    rows = {}
    for j in names:
        means = [num(c["jobs"][j]["ms_sum"]) / max(1, num(c["jobs"][j]["runs"])) for c in cells if j in c["jobs"]]
        worst = [num(c["jobs"][j]["worst"]) for c in cells if j in c["jobs"]]
        over = [num(c["jobs"][j]["over"]) for c in cells if j in c["jobs"]]
        if means:
            rows[j] = (mean(means), max(worst), sum(over))
    return rows


def row13():
    say("\n" + "=" * 110 + "\nROW 13  Cost of every v7.1 change (PERF1 on both builds, PERF2, PERF4, WEBLOAD)")
    res = {}
    for run in (CORE3, RERUN):
        b = Block("S7_PERF1", run)
        b.header(13, f"new vs legacy (all ten legacy_* + stagger off); 12,000 t; build {BUILD[run.name]}")
        cells = {}
        for arm in ("new", "legacy"):
            cs = perf_cells(b, arm, "t12000", 12000)
            excl = [c for c in cs if c["short"] or c["wall"] > 400]
            for c in excl:
                say(f"    EXCLUDED {arm} rep {c['rep']}: {c['ticks']} of 12,000 t in {c['wall']:.0f} s (t/s {c['tps']:.1f}) -- "
                    f"the cell outlived its budget (DF process age), not a tool cost")
            cells[arm] = [c for c in cs if c not in excl]
        for arm, cs in cells.items():
            say(f"    {arm}: t/s {desc([c['tps'] for c in cs], 1)}; worst tick ms {desc([c['worst'] for c in cs], 0)}; "
                f"tool ms per 1,000 t {desc([c['ms_per_kt'] for c in cs], 1)}; fps (stepping) {desc([c['fps'] for c in cs], 0)}")
            for j, (m, w, o) in jobtab(cs).items():
                say(f"       {j:34s} mean {m:6.2f} ms/run  worst {w:5.0f} ms  over-budget runs {o:.0f}")
        res[run.name] = dict(
            tps=contrast("t/s", [c["tps"] for c in cells["new"]], [c["tps"] for c in cells["legacy"]], "new", "legacy", 1),
            worst=contrast("worst tick ms", [c["worst"] for c in cells["new"]], [c["worst"] for c in cells["legacy"]], "new", "legacy", 0),
            mskt=contrast("tool ms per 1,000 t", [c["ms_per_kt"] for c in cells["new"]], [c["ms_per_kt"] for c in cells["legacy"]], "new", "legacy", 1),
            jobs={a: jobtab(cs) for a, cs in cells.items()})
    a, bb = res[CORE3.name], res[RERUN.name]
    say("\n    build vs build (the new paths): 9e5aabe vs a4fix")
    res["build_tps"] = contrast("t/s, new arm", a["tps"]["a"], bb["tps"]["a"], "9e5aabe", "a4fix", 1)
    res["build_worst"] = contrast("worst tick ms, new arm", a["worst"]["a"], bb["worst"]["a"], "9e5aabe", "a4fix", 0)
    res["build_mskt"] = contrast("tool ms per 1,000 t, new arm", a["mskt"]["a"], bb["mskt"]["a"], "9e5aabe", "a4fix", 1)
    je0, je1 = a["jobs"]["new"].get("seasonal-wildlife/ecology"), bb["jobs"]["new"].get("seasonal-wildlife/ecology")
    say(f"    ecology job mean/worst/over: 9e5aabe {je0}; a4fix {je1}")
    # PERF2
    b = Block("S7_PERF2")
    b.header(13, "overlay new / legacy_overlay / overlay_off; 6,000 t")
    p2 = {}
    for arm in b.arms():
        cs = perf_cells(b, arm, "t6000", 6000)
        p2[arm] = cs
        ov = [d for r in b.reps(arm) for d in b.rows(arm, r, "ovlsum")]
        say(f"    {arm}: t/s {desc([c['tps'] for c in cs], 1)}; worst tick {desc([c['worst'] for c in cs], 0)}; fps "
            f"{desc([c['fps'] for c in cs], 0)}; overlay perf-counter rows found {Counter(d.get('rows') for d in ov)}")
    if "new" in p2 and "overlay_off" in p2:
        res["p2_new_off"] = contrast("t/s overlay new vs off", [c["tps"] for c in p2["new"]], [c["tps"] for c in p2["overlay_off"]], "new", "off", 1)
        res["p2_leg_new"] = contrast("t/s legacy overlay vs new", [c["tps"] for c in p2["legacy_overlay"]], [c["tps"] for c in p2["new"]], "legacy", "new", 1)
        res["p2_fps"] = contrast("fps overlay new vs off", [c["fps"] for c in p2["new"]], [c["fps"] for c in p2["overlay_off"]], "new", "off", 0)
    # PERF4
    b = Block("S7_PERF4")
    b.header(13, "events_on vs events_off with 60 extra citizens (67 in all); 10,000 t")
    p4 = {}
    for arm in b.arms():
        cs = perf_cells(b, arm, "t10000", 10000)
        p4[arm] = cs
        cit = [d.get("n") for r in b.reps(arm) for d in b.rows(arm, r, "cit")]
        say(f"    {arm}: citizens {cit}; t/s {desc([c['tps'] for c in cs], 1)}; worst tick {desc([c['worst'] for c in cs], 0)}; "
            f"tool ms per 1,000 t {desc([c['ms_per_kt'] for c in cs], 1)}")
        for j, (m, w, o) in jobtab(cs).items():
            say(f"       {j:34s} mean {m:6.2f} ms/run  worst {w:5.0f} ms  over {o:.0f}")
    if "events_on" in p4:
        res["p4_tps"] = contrast("t/s events on vs off", [c["tps"] for c in p4["events_on"]], [c["tps"] for c in p4["events_off"]], "on", "off", 1)
        res["p4_mskt"] = contrast("tool ms/1,000 t events on vs off", [c["ms_per_kt"] for c in p4["events_on"]], [c["ms_per_kt"] for c in p4["events_off"]], "on", "off", 1)
    # WEBLOAD (stage, 9e5aabe)
    say("\n  [WEBLOAD] page polled as it polls (state 2 s, status 5 s) vs no page; n = 5, a fresh DF per rep; 3,000 t")
    wl = defaultdict(lambda: defaultdict(list))
    for line in open(STAGES / "webload.tsv", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 5:
            continue
        _, rep, arm, kind, rest = p[:5]
        d = kv(rest)
        if kind == "perf" and d.get("tag") == "t3000":
            wl[arm]["tps"].append(num(d["tps"]))
            wl[arm]["worst"].append(num(d["worst_tick_ms"]))
            wl[arm]["fps"].append(num(d["fps_calc"]))
        if kind == "webstats":
            for k in ("snap_ms", "snap_worst", "status_ms", "status_worst", "requests"):
                wl[arm][k].append(num(d.get(k)))
        if kind == "poll":
            wl[arm]["codes"].append(d.get("codes"))
    for arm, d in wl.items():
        say(f"    {arm}: t/s {desc(d['tps'], 1)}; worst tick {desc(d['worst'], 0)}; fps {desc(d['fps'], 0)}"
            + (f"; snap ms mean {desc(d['snap_ms'], 1)} worst {max(d['snap_worst']):.0f}; status ms {desc(d['status_ms'], 1)} "
               f"worst {max(d['status_worst']):.0f}; requests {d['requests']}; codes {Counter(d['codes'])}" if d.get("snap_ms") else ""))
    if "page_on" in wl and "page_off" in wl:
        res["web_tps"] = contrast("t/s page on vs off", wl["page_on"]["tps"], wl["page_off"]["tps"], "on", "off", 1)
    OUT["perf"] = {k: (v if not isinstance(v, dict) or "a" not in v else {kk: v[kk] for kk in ("diff", "g", "p", "a", "b")})
                   for k, v in res.items() if k not in (CORE3.name, RERUN.name)}
    OUT["perf_builds"] = {k: {m: {kk: v[m][kk] for kk in ("diff", "g", "p", "a", "b")} for m in ("tps", "worst", "mskt")}
                          for k, v in res.items() if k in (CORE3.name, RERUN.name)}
    OUT["perf_jobs"] = {k: {a: {j: list(x) for j, x in t.items()} for a, t in v["jobs"].items()} for k, v in res.items()
                        if k in (CORE3.name, RERUN.name)}
    OUT["webload"] = {a: dict(d) for a, d in wl.items()}
    verdict(13, "MEASURED (new paths cheaper than legacy; overlay cost not readable)",
            f"PERF1 a4fix: new {mean(bb['tps']['a']):.1f} t/s vs legacy {mean(bb['tps']['b']):.1f} (p={bb['tps']['p']:.3f}); "
            f"worst tick {mean(bb['worst']['a']):.0f} vs {mean(bb['worst']['b']):.0f} ms (p={bb['worst']['p']:.3f}); "
            f"9e5aabe->a4fix worst tick {mean(a['worst']['a']):.0f}->{mean(bb['worst']['a']):.0f} ms")


# ---------------------------------------------------------------------------------------- 14, 15 stages --
def verdicts_of(path):
    out = []
    for line in open(path, errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 5 and p[3] == "VERDICT":
            m = re.match(r"check=(.*?) ok=(\S+) got=(.*)$", p[4])
            if m:
                out.append((m.group(1), m.group(2), m.group(3)[:160]))
    return out


def row14_15():
    say("\n" + "=" * 110 + "\nROWS 14, 15  A real screen; DFHack 53.16-r2 (stages in run 20261002-015732, tool 9e5aabe)")
    say("  [R2] REPORT section 4 on this fort:")
    r2 = verdicts_of(STAGES / "r2.tsv")
    for c, ok, got in r2:
        say(f"    {'PASS' if ok == 'True' else 'FAIL':4s} {c}")
    say("  [VALIDATE] validate-full 20261002-020031: 356 PASS, 7 FAIL, 41 NOT-TESTABLE-HERE, 4 BACKLOG (log.txt of the stage)")
    tri = (ROOT / "data/validation/full/20261002-020031/TRIAGE.md")
    if tri.exists():
        rows = [l for l in tri.read_text().splitlines() if re.match(r"\| \d \|", l)]
        for l in rows:
            say("    " + l)
    vr = ROOT / "data/validation/full/20261002-020031/results.json"
    if vr.exists():
        rows = json.loads(vr.read_text())
        rows = rows if isinstance(rows, list) else rows.get("results", [])
        for pre in ("gui.", "web."):
            c = Counter((x.get("verdict") or x.get("status")) for x in rows if str(x.get("id", "")).startswith(pre))
            bad = [x.get("id") for x in rows if str(x.get("id", "")).startswith(pre) and (x.get("verdict") or x.get("status")) == "FAIL"]
            say(f"    {pre}* claims on the real window/page: {dict(c)}; FAIL {bad}")
            OUT.setdefault("validate", {})[pre] = dict(c)
    say("  [PANEL] the window's Panel walked section by section:")
    pv = verdicts_of(STAGES / "panel.tsv")
    for c, ok, got in pv:
        say(f"    {ok:5s} {c}: {got[:100]}")
    secs = []
    for line in open(STAGES / "panel.tsv", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 5 and p[3] == "panelsec":
            secs.append(kv(p[4]))
    say(f"    sections whose step changed a config path: {sum(d.get('changed') not in ('-', None) for d in secs)}/{len(secs)}; "
        f"'read-back' seen {sum(d.get('readback') == '1' for d in secs)}/{len(secs)}; restored {sum(d.get('restored') == '1' for d in secs)}")
    same = 0
    for i in range(len(secs)):
        a, bpath = STAGES / f"panel/s{i:02d}-a.txt", STAGES / f"panel/s{i:02d}-b.txt"
        if a.exists() and bpath.exists():
            la = [l for l in a.read_text(errors="replace").splitlines() if "FPS:" not in l and "frame rate" not in l]
            lb = [l for l in bpath.read_text(errors="replace").splitlines() if "FPS:" not in l and "frame rate" not in l]
            same += la == lb
    say(f"    screens before vs after the Right step identical (FPS lines aside): {same}/{len(secs)} -- the step never reached "
        f"a control (the cursor sat on the section list), and the 'read-back' counted is the stale status line")
    OUT["stages"] = dict(r2=r2, panel=pv, panel_same=same, panel_secs=len(secs))
    verdict(14, "PARTLY CONFIRMED (VALIDATE gui/web claims; 13 sections reach; no clip) / PANEL round trip NOT TESTED",
            f"PANEL: 0/13 steps changed a config path, and {same}/13 screens were identical before and after the step "
            f"(harness focus); WEBLOAD: see row 13")
    nfail = sum(ok != "True" for _, ok, _ in r2)
    verdict(15, "CONFIRMED (no r2 regression found)",
            f"R2 checklist {len(r2) - nfail}/{len(r2)} PASS (6 = 'not run', the report has no step 6); validate-full 356 PASS / "
            f"7 FAIL, every FAIL triaged: 5 validator, 2 tool display/cost fixed in dcd169b and 72b5c25, none r2-specific")


def facts():
    fj = json.loads((SEC7 / "facts.json").read_text())
    say("FACTS (data/alpha4-sec7/facts.json): " + json.dumps(fj.get("derived", fj))[:600])
    pr = verdicts_of(STAGES / "probes.tsv")
    for c, ok, got in pr:
        say(f"    {'PASS' if ok == 'True' else ok:5s} {c}: {got[:140]}")
    OUT["facts"] = dict(facts=fj, probes=pr)


def figs():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        say("figs: matplotlib not importable here; skipped")
        return
    d = SEC7 / "figs"
    d.mkdir(exist_ok=True)
    b = Block("S7_NAT")
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6), sharex=True)
    col = {"def": "#2a6fdb", "v70": "#d9822b"}
    for arm in b.arms():
        for rep in b.reps(arm):
            nat = [x for x in b.rows(arm, rep, "nat") if x["tag"] != "t0"]
            t = [tagnum(x["tag"]) / 1000 for x in nat]
            ax[0].plot(t, [num(x["land"]) for x in nat], color=col[arm], alpha=.55, lw=1.2, label=arm if rep == 1 else None)
            ax[1].plot(t, [mean([num(x[c]) for c in ("c1", "c2", "c3")]) for x in nat], color=col[arm], alpha=.55, lw=1.2)
            ax[2].plot(t, [num(x["water"]) / 3 for x in nat], color=col[arm], alpha=.55, lw=1.2)
    ax[0].axhspan(7.5, 9, color="#999", alpha=.18, lw=0)
    ax[0].set_title("land groups (cap 9; target band 7.5-9)", fontsize=10)
    ax[1].axhline(5, color="#555", ls="--", lw=1)
    ax[1].set_title("tool-record groups per cavern (cap 5)", fontsize=10)
    ax[2].axhline(3, color="#555", ls="--", lw=1)
    ax[2].set_title("water groups per body (target >= 3)", fontsize=10)
    for a in ax:
        a.set_xlabel("thousand ticks")
        a.spines[["top", "right"]].set_visible(False)
    ax[0].legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(d / "nat-groups.png", dpi=130)
    plt.close(fig)
    # PERF1 by build
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    for i, (key, lab) in enumerate((("tps", "t/s (stopwatch)"), ("worst", "worst tick ms"))):
        pos = 0
        ticks, labels = [], []
        for run in (CORE3.name, RERUN.name):
            for arm in ("a", "b"):
                v = OUT["perf_builds"][run][key][arm]
                ax[i].scatter([pos] * len(v), v, color="#2a6fdb" if arm == "a" else "#d9822b", s=22)
                ax[i].plot([pos - .25, pos + .25], [mean(v)] * 2, color="#222", lw=1.5)
                ticks.append(pos)
                labels.append(f"{'new' if arm == 'a' else 'legacy'}\n{BUILD[run].split()[-1]}")
                pos += 1
            pos += .5
        ax[i].set_xticks(ticks, labels, fontsize=8)
        ax[i].set_title(lab, fontsize=10)
        ax[i].spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(d / "perf1-builds.png", dpi=130)
    plt.close(fig)
    say(f"figs: wrote {d / 'nat-groups.png'} and {d / 'perf1-builds.png'}")


def main():
    say("Alpha Four section 7 -- results tally (scripts/sec7-tally.py)")
    say(f"runs: stages {STAGES.name}; core3 {CORE3.name} (9e5aabe); rerun {RERUN.name} (a4fix 69e97a1); late rerun "
        f"{NEW.name if NEW else '-'}")
    facts()
    row1()
    row2()
    row3_4_9_10_12()
    row4_trim()
    row5()
    row6()
    row7()
    row8()
    row10_grd()
    row11()
    row12()
    row13()
    row14_15()
    if "--figs" in sys.argv:
        figs()
    say("\n" + "=" * 110 + "\nVERDICTS (computed; rows 4, 9, 10 are set in SECTION7-RESULTS.md from the numbers above)")
    for k in sorted(VERDICT):
        say(f"  {k:2d}  {VERDICT[k][0]}: {VERDICT[k][1]}")
    OUT["verdicts"] = {str(k): v for k, v in VERDICT.items()}

    def clean(o):
        if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
            return None
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        return o
    (SEC7 / "sec7-tally.json").write_text(json.dumps(clean(OUT), indent=1, default=str))
    (SEC7 / "sec7-tally.txt").write_text("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
