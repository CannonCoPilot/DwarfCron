#!/usr/bin/env python3
"""X1 / X1c tally: do inactive species stay away, on every layer? And X7: job and tab timings over the season.

Reads one run directory (data/experiments/X1*/<run>/). For each replicate:
  - the roster the tool held at t0, from the pre's 'x1 roster N: KEY=allow/seasons ...' line
    (allow true/false/nil; seasons as digits 0-3, empty = none);
  - every arrival (events.tsv, event=arrival), keyed the way the tool keys species: TOKEN on land,
    water:TOKEN for a feature entry, cavern:TOKEN for a cave entry (ref6 = rx,ry,feature,cave,site,idx);
  - each arrival is classed against the roster: inactive (allow false), unseasoned (allow true or nil with
    no season -- v6.2.1's unmanaged state), out of season (active, the arrival's season not among its
    seasons), in season, or off the roster (a species the tool does not manage: the deep layer, DF's own).
X7: the 'x7 jobs:' and 'x7 tabs:' lines from the log, worst per job / tab over the replicate.
Writes tally.txt beside the run.
"""
import re, sys, collections
from pathlib import Path

TICKS_PER_YEAR, SEASON = 403200, 100800
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]

def key_of(token, ref6):
    parts = ref6.split(",")
    feat, cave = int(parts[2]), int(parts[3])
    if cave != -1:
        return "cavern:" + token
    if feat != -1:
        return "water:" + token
    return token

def main(run_dir):
    d = Path(run_dir)
    rows = [l.rstrip("\n").split("\t") for l in (d / "events.tsv").read_text().splitlines()[1:]]
    log = (d / "log.txt").read_text(errors="replace")
    reps = collections.OrderedDict()
    for r in rows:
        if len(r) < 7:
            continue
        _run, arm, rep, _tick, abs_tick, ev, subj = r[:7]
        detail = r[7] if len(r) > 7 else ""
        k = (arm, rep)
        R = reps.setdefault(k, {"roster": {}, "arrivals": []})
        if ev == "manipulation":
            blob = "\t".join(r[6:])
            m = re.search(r"x1 roster \d+: (.*)", blob)
            if m:
                for item in m.group(1).split():
                    if "=" in item and "/" in item:
                        kk, v = item.split("=", 1)
                        allow, seasons = v.split("/", 1)
                        R["roster"][kk] = (allow, set(int(c) for c in seasons if c.isdigit()))
        elif ev == "arrival":
            m = re.match(r"(\S+) .*ref6=(\S+)", detail)
            if m:
                R["arrivals"].append((int(abs_tick), subj, m.group(1), m.group(2)))
    out = []
    for (arm, rep), R in reps.items():
        roster = R["roster"]
        cls = collections.Counter()
        by = collections.defaultdict(list)
        for abs_tick, _uid, token, ref6 in R["arrivals"]:
            k = key_of(token, ref6)
            season = (abs_tick % TICKS_PER_YEAR) // SEASON
            if k not in roster:
                c = "off the roster"
            else:
                allow, seasons = roster[k]
                if allow == "false":
                    c = "INACTIVE"
                elif not seasons:
                    c = "UNSEASONED"
                elif season not in seasons:
                    c = "out of season"
                else:
                    c = "in season"
            cls[c] += 1
            by[c].append(f"{k}@{SEASONS[season][:2]}")
        n_inactive = sum(1 for v in roster.values() if v[0] == "false")
        n_unseasoned = sum(1 for v in roster.values() if v[0] != "false" and not v[1])
        out.append(f"== {arm} rep {rep}: roster {len(roster)} species ({n_inactive} inactive, {n_unseasoned} active or unmanaged with no season); {len(R['arrivals'])} arrivals")
        for c in ("INACTIVE", "UNSEASONED", "out of season", "in season", "off the roster"):
            if cls[c]:
                species = collections.Counter(x.split("@")[0] for x in by[c])
                out.append(f"   {c:<15} {cls[c]:>4}   " + ", ".join(f"{s} x{n}" for s, n in species.most_common(12)))
    # X7: worst job and tab times per replicate, from the log's 'x7' lines in order
    worst_jobs, worst_tabs = collections.defaultdict(int), collections.defaultdict(int)
    for m in re.finditer(r"x7 jobs: (.*)", log):
        for part in m.group(1).split(" | "):
            mm = re.match(r"(\S*) runs=(\d+) last=(\d+) worst=(\d+) over=(\d+)", part.strip())
            if mm:
                worst_jobs[mm.group(1) or "season"] = max(worst_jobs[mm.group(1) or "season"], int(mm.group(4)))
    for m in re.finditer(r"x7 tabs: (.*)", log):
        for part in m.group(1).split():
            mm = re.match(r"([\w:]+)=(\d+)", part)
            if mm and mm.group(1) != "open":
                worst_tabs[mm.group(1)] = max(worst_tabs[mm.group(1)], int(mm.group(2)))
    if worst_jobs:
        out.append("X7 worst job pass over the run (ms, budget 50): " + ", ".join(f"{k} {v}" for k, v in sorted(worst_jobs.items())))
    if worst_tabs:
        out.append("X7 worst tab refresh over the run (ms, budget 100): " + ", ".join(f"{k} {v}" for k, v in sorted(worst_tabs.items())))
    text = "\n".join(out)
    (d / "tally.txt").write_text(text + "\n")
    print(text)

if __name__ == "__main__":
    main(sys.argv[1])
