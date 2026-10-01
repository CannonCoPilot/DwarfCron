#!/usr/bin/env python3
"""s8-tally: item 8 (a season of v7.0 with the roster builder), read off cx-experiment runs of S8C/S8B/S8O.

  .venv/bin/python scripts/s8-tally.py data/experiments/S8C/<run> [more run dirs...]

Per replicate:
  build     the 's8 build <layer>: ...' receipts (the kill criterion: no build line with filled slots voids the run)
  arrivals  units DF/the tool brought in (events.tsv 'arrival'), by layer and guild; a wave = one (token, listed_at)
            -- guilds come from the manifest's own per-sample 's8 tick=' line (layer:guild:token for every new unit),
            so the guild is the tool's (buildPool), not re-derived here
  predator share of surface arrivals, units and waves (guilds AL AW RP ML MW, species2.PRED_GUILDS)
  apex      AL/AW arrivals (item 15: does the apex FREQUENCY matter -- compare against the builder-off run)
  deaths    events.tsv 'death' rows by victim, and kills per surface arrival
  beached   the largest pelagic_beached count any sample saw (item 16)
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PRED = {"AL", "AW", "RP", "ML", "MW"}
APEX = {"AL", "AW"}


def kv(s):
    return dict(t.split("=", 1) for t in s.split() if "=" in t)


def tally(run):
    ev = run / "events.tsv"
    if not ev.exists():
        print(f"-- {run}: no events.tsv")
        return
    guild = {}                       # token -> guild, from the s8 sample lines
    beached = defaultdict(int)       # rep -> max pelagic_beached
    samples = Counter()
    arrivals = defaultdict(list)     # rep -> [(layer, token, listed_at)]
    deaths = defaultdict(Counter)    # rep -> victim token counts
    for line in open(ev):
        p = line.rstrip("\n").split("\t")
        if len(p) < 7 or p[0] == "run":
            continue
        rep, kind = p[2], p[5]
        m = re.search(r"s8 tick=\d+ units (.*?) \| new (.*?) \| pelagic_beached=(\d+)", line)
        if m:
            samples[rep] += 1
            for item in m.group(2).split():
                parts = item.split(":")
                if len(parts) == 3:
                    guild.setdefault(parts[2], parts[1])
            beached[rep] = max(beached[rep], int(m.group(3)))
            continue
        if kind == "arrival":
            d = kv(" ".join(p[7:]))
            tok = p[7].split()[0] if len(p) > 7 else "?"
            arrivals[rep].append((d.get("layer", "?"), tok, d.get("listed_at", p[4])))
        elif kind == "death":
            det = " ".join(p[6:])
            v = re.search(r"victim=(\S+)", det) or re.search(r"^(\S+)", p[7] if len(p) > 7 else "")
            deaths[rep][v.group(1) if v else det.split()[0]] += 1
    builds = defaultdict(list)
    log = run / "log.txt"
    if log.exists():
        rep = "?"
        for line in open(log):
            r = re.search(r"arm=\S+ rep=(\d+)", line)
            if r:
                rep = r.group(1)
            for b in re.findall(r"s8 build (\w+): (.{0,160})", line):
                builds[rep].append(f"{b[0]}: {b[1]}")
    print(f"\n== {run}")
    for rep in sorted(set(arrivals) | set(samples) | set(builds)):
        print(f"  rep {rep}: {samples[rep]} samples, pelagic_beached max {beached[rep]}")
        for b in builds.get(rep, []) or ["(no 's8 build' line: builder did not run -> void for item 8)"]:
            print(f"    build {b}")
        arr = arrivals[rep]
        units = Counter((lay, guild.get(t, "-")) for lay, t, _ in arr)
        waves = Counter((lay, guild.get(t, "-")) for lay, t, _ in set(arr))
        for lay in sorted({l for l, _ in units}):
            row = sorted(((g, units[(lay, g)], waves[(lay, g)]) for (l, g) in units if l == lay), key=lambda x: -x[1])
            tot_u = sum(n for _, n, _ in row)
            tot_w = sum(w for _, _, w in row)
            pu = sum(n for g, n, _ in row if g in PRED)
            pw = sum(w for g, _, w in row if g in PRED)
            ap = sum(n for g, n, _ in row if g in APEX)
            print(f"    {lay:8s} {tot_u:4d} units / {tot_w:3d} waves; predators {pu} units ({pu / tot_u:.0%}), "
                  f"{pw} waves ({pw / tot_w if tot_w else 0:.0%}); apex {ap} units")
            print("             " + "  ".join(f"{g} {n}/{w}" for g, n, w in row))
        toks = Counter(t for _, t, _ in arr)
        print("    tokens: " + ", ".join(f"{t} {n}" for t, n in toks.most_common(14)))
        surf = sum(1 for lay, _, _ in arr if lay == "surface")
        dsum = sum(deaths[rep].values())
        print(f"    deaths {dsum} ({', '.join(f'{t} {n}' for t, n in deaths[rep].most_common(8))}); "
              f"per surface arrival {dsum / surf if surf else 0:.2f}")


if __name__ == "__main__":
    for a in sys.argv[1:]:
        tally(Path(a))
