#!/usr/bin/env python3
"""Alpha 2, round 2 (v6.7.0 @ c3b85c7): one full pass (185858). Two marks are set by hand, each a driver scoring fault on
a step the product passed (both scorers fixed in alpha2-run.py after this round); 17.2's 'within noise' is corrected."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
passes = ["20260928-185858"]
broken: dict[str, set] = {}
marks: dict[str, dict] = {}
titles: dict[str, str] = {}
for run in passes:
    for r in json.loads((HERE / run / "results.json").read_text()):
        titles[r["id"]] = r["title"]
        if r["id"] in broken.get(run, set()):
            continue
        marks[r["id"]] = {"v": r["v"], "n": r["note"] + f"  [run {run[-6:]}]"}

HAND = {
    "5.1": ("p", "Matrix assign, Co-align, Fill natural prey and Fill natural predators each asked first; No left the roster unchanged. "
                 "Fill to targets had nothing to do and said why instead of asking: 'No target set on the land layer: Shift-P/R/V set one; F leaves unset categories alone.' "
                 "(The driver scored that as 'did not ask'; its scorer now reads the status line.)  [run 185858]"),
    "10.1": ("p", "The pyramid draws four tiers with ^ between them: LION, LION_MAN, TIGER, TIGER_MAN, VORACIOUS_CAVE_CRAWLER at the apex; "
                  "HYENA_MAN, JAGUAR, JAGUAR_MAN, LEOPARD, LEOPARD_MAN, TROGLODYTE; GIRAFFE_MAN, PANGOLIN, RAT_GIANT, RAT_LARGE, RHINOCEROS_MAN, RUTHERER, WARTHOG_MAN; "
                  "BAT, BIRD_PARAKEET, SPARROW, SPIDER_CAVE at the base; and an aquatic chain below (6 lines). "
                  "Round 1's design question, answered in v6.7: all 24 animal people on this embark mirror their root animal on role, habitat, size and every eats verdict both ways "
                  "(a jaguar man stands with the jaguar in tier two). The driver counted the next section's 'Summer --' header as a fifth tier; parser fixed.  [run 185858]"),
    "17.2": ("p", "The Panel's frame-rate readout and the all-off switch work: tool on 126 t/s, all off 168 t/s, one reading each. "
                  "That is a 25% cost, larger than the 10-15% load noise (the driver's note said 'within'), and larger than FPS1's paired 107 vs 107 on BOATS. "
                  "FPS3 runs tool on vs off in pairs to settle it.  [run 185858]"),
}
for sid, (v, n) in HAND.items():
    marks[sid] = {"v": v, "n": n}

order = lambda s: [int(x) for x in s.split(".")]
ids = sorted(marks, key=order)
meta = {"tName": "W2:Urist (the rig, scripts/alpha2-run.py)", "tFort": "BOATS (the rig's copy of the alpha one fort; tropical shrubland, ocean, salt river; 29 citizens)",
        "tVer": "53.16 · 53.16-r1.1 · seasonal-wildlife v6.7.0 @ c3b85c7", "tDate": "2026-09-28"}
out = HERE / "round2"; out.mkdir(exist_ok=True)
(out / "marks.json").write_text(json.dumps({**{i: marks[i] for i in ids}, "_meta": meta}, indent=1, ensure_ascii=False))
p = [i for i in ids if marks[i]["v"] == "p"]; a = [i for i in ids if marks[i]["v"] == "a"]; s = [i for i in ids if marks[i]["v"] == "s"]
L = ["# Seasonal Wildlife alpha trial two, round 2 (UI, v6.7)", "", f"- Tester: {meta['tName']}", f"- Fort: {meta['tFort']}", f"- Game / DFHack / plugin: {meta['tVer']}", f"- Date: {meta['tDate']}", "",
     f"Tally: {len(p)} pass · {len(a)} anomaly · {len(s)} skipped · {62 - len(ids)} unmarked of 62 steps."]
for title, rows in (("Anomalies", a), ("Skipped (and why)", s), ("Passes", p)):
    if rows:
        L += ["", f"## {title}"] + [f"- **{i} {titles.get(i, '')}**: {marks[i]['n']}" for i in rows]
(out / "report.md").write_text("\n".join(L) + "\n")
print(f"{len(ids)} steps: {len(p)} pass, {len(a)} anomaly, {len(s)} skipped -> {out}")
print("anomalies:", a)
