#!/usr/bin/env python3
"""Alpha 2, round 1: one set of marks from the full pass (131118) and the two reruns (134043, 141723).
A step takes its latest valid result; a rerun result the driver itself broke is not used. Six marks are set by
hand, each with the evidence and the reason in the note (a driver fault on a step the product passed, or a finding
the driver scored as a pass)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
passes = ["20260928-131118", "20260928-134043", "20260928-141723"]
# results the driver broke, per pass: not used
broken = {"20260928-131118": {"2.3", "3.3", "3.6", "4.3", "7.1", "10.1", "16.1", "16.2", "17.1", "7.2"},
          "20260928-134043": {"2.3", "2.4", "4.3", "17.1"},
          "20260928-141723": {"10.1"}}
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
                 "Fill to targets did not ask because there was nothing to do: no target was set, and it said so ('No target set on the land layer ... F leaves unset categories alone'). "
                 "That hint named Shift-B, a target retired in v6.4; fixed in e507876."),
    "10.1": ("a", "The pyramid draws four unlabelled tiers with ^ between them (apex at the top, vermin at the base) and an aquatic chain below; the page promised level labels, which the pyramid does not draw (page corrected). "
                  "Design question: the aquatic chain lists animal people and odd pairings as prey: GIANT_OTTER ----> JAGUAR_MAN, GIANT_GRAY_LANGUR, HONEY BADGER, RIVER OTTER, PANGOLIN, BIRD_OSPREY; "
                  "TOAD_GIANT_CAVE ----> TROGLODYTE, PLUMP_HELMET_MAN, RAT_GIANT, GREMLIN. The size rule allows them; whether animal people should be prey is the user's call.  [runs 131118, 141723]"),
    "17.1": ("p", "Saved to a new folder (A2R141723) and loaded it back: AARDVARK still inactive, the ledger's last entry present after the reload. "
                  "A direct test on the reload copy confirms it: 'land groups at once 4' written, saved to A2LEDG, reloaded, and it is the newest ledger line. "
                  "The reload's ledger showed a reset line still saying 'abundances to 50' (retired in v6.5); fixed in f80d072.  [runs 141723 + direct]"),
    "4.3": ("a", "Alt+O on ALBATROSS_MAN (out of season: Au Wi, now Summer) stored the odds, but the ODDS column shows '-' for every species out of season (Win:oddsOf), so the player sees no effect of the key on the Roster; "
                 "only the detail page shows the share '(if it were in season)'. Works as coded; the column could show the out-of-season share in brackets. Page's promise corrected.  [run 141723]"),
    "8.1": ("a", "Ctrl+X in the Add invasive view added AARDVARK_MAN to the embark and the ledger, but right after the add it had no roster state at all (neither active nor inactive, no season); "
                 "by step 9.2 a later pass had given it one season. For that moment it breaks the roster rule (every species active with a season, or inactive).  [run 131118]"),
    "3.6": ("p", "Called ELEPHANT from its detail page; the next land arrival, 1,538 ticks later, was elephants only (12 in the 1,500-tick window; the raw's CLUSTER_NUMBER is 3:7, so this is most likely two draws inside one sample window).  [run 134043]"),
}
for sid, (v, n) in HAND.items():
    marks[sid] = {"v": v, "n": n}

order = lambda s: [int(x) for x in s.split(".")]
ids = sorted(marks, key=order)
meta = {"tName": "W2:Urist (the rig, scripts/alpha2-run.py)", "tFort": "BOATS (the rig's copy of the alpha one fort; tropical shrubland, ocean, salt river; 29 citizens)",
        "tVer": "53.16 · 53.16-r1.1 · seasonal-wildlife v6.6.0 @ f22fa30 (fixes found here: e507876, f80d072)", "tDate": "2026-09-28"}
out = HERE / "round1"; out.mkdir(exist_ok=True)
(out / "marks.json").write_text(json.dumps({**{i: marks[i] for i in ids}, "_meta": meta}, indent=1, ensure_ascii=False))
p = [i for i in ids if marks[i]["v"] == "p"]; a = [i for i in ids if marks[i]["v"] == "a"]; s = [i for i in ids if marks[i]["v"] == "s"]
L = ["# Seasonal Wildlife alpha trial two (UI, v6.6)", "", f"- Tester: {meta['tName']}", f"- Fort: {meta['tFort']}", f"- Game / DFHack / plugin: {meta['tVer']}", f"- Date: {meta['tDate']}", "",
     f"Tally: {len(p)} pass · {len(a)} anomaly · {len(s)} skipped · {62 - len(ids)} unmarked of 62 steps."]
for title, rows in (("Anomalies", a), ("Skipped (and why)", s), ("Passes", p)):
    if rows:
        L += ["", f"## {title}"] + [f"- **{i} {titles.get(i, '')}**: {marks[i]['n']}" for i in rows]
(out / "report.md").write_text("\n".join(L) + "\n")
print(f"{len(ids)} steps: {len(p)} pass, {len(a)} anomaly, {len(s)} skipped -> {out}")
print("anomalies:", a)
