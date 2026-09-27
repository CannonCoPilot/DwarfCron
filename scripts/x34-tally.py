#!/usr/bin/env python3
"""X3 / X4 tally, from the harness's waves.tsv (one row per wave: species, layer, n, valid).

X3 -- does FREQUENCY weight DF's surface pick? Per replicate: surface waves, the share that are KANGAROO or
      PORCUPINE, and KANGAROO:PORCUPINE. Every other land species sits at frequency 1, so if the raw's
      frequency is the surface weight the high arm (100:25) is mostly the pair and the low arm (4:1) is not.
X4 -- is DF's extra animal structural? Per replicate: the sizes of the waves of BIRD_RAVEN, BIRD_EMU and
      KANGAROO under a written cluster range {1,1}.
Writes tally.txt beside the run.
"""
import sys, collections
from pathlib import Path

def main(run_dir):
    d = Path(run_dir)
    rows = [l.rstrip("\n").split("\t") for l in (d / "waves.tsv").read_text().splitlines()]
    head, rows = rows[0], rows[1:]
    col = {h: i for i, h in enumerate(head)}
    reps = collections.OrderedDict()
    for r in rows:
        if r[col["layer"]] != "surface" or r[col["valid"]] != "True":
            continue
        reps.setdefault((r[col["arm"]], r[col["rep"]]), []).append((r[col["species"]], int(r[col["n"]])))
    out = []
    xid = d.parent.name
    for (arm, rep), waves in reps.items():
        by = collections.Counter(s for s, _ in waves)
        if xid == "X3":
            k, p = by.get("KANGAROO", 0), by.get("PORCUPINE", 0)
            share = 100 * (k + p) / len(waves) if waves else 0
            out.append(f"{arm:5} rep {rep}: {len(waves):3} surface waves; KANGAROO {k}, PORCUPINE {p} -> pair share {share:.0f}%; "
                       f"K:P {k}:{p}; others: " + ", ".join(f"{s} {n}" for s, n in by.most_common() if s not in ("KANGAROO", "PORCUPINE")))
        else:
            sizes = collections.defaultdict(list)
            for s, n in waves:
                if s in ("BIRD_RAVEN", "BIRD_EMU", "KANGAROO"):
                    sizes[s].append(n)
            allz = [n for v in sizes.values() for n in v]
            dist = collections.Counter(allz)
            out.append(f"{arm:5} rep {rep}: {len(allz)} waves of the three; sizes " + ", ".join(f"{n}: {c}" for n, c in sorted(dist.items())) +
                       "; by species " + "; ".join(f"{s} {v}" for s, v in sorted(sizes.items())))
    text = "\n".join(out)
    (d / "tally.txt").write_text(text + "\n")
    print(text)

if __name__ == "__main__":
    main(sys.argv[1])
