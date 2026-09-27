#!/usr/bin/env python3
"""X2 / X5 / X6 tally, from the probe lines each manifest prints every sample (events.tsv, every_applied rows).

X2 -- Driver B groups. Per drawn group (by its ids): members placed, members wet at the first sample, the widest
      spread seen, whether they all left and how long after the draw, the stock at the first and last samples it
      was seen (debit at the draw, refund as members leave), its body and salinity, and whether a coupled draw
      followed a prey draw.
X5 -- vermin hunting. Per replicate: the subjects, the share of samples with a vermin-related job, the mean vermin
      within 6 tiles, catch reports, and the map's vermin count first and last.
X6 -- marine birds. Per replicate: each bird's share of samples in water, over water, dry.
Writes tally.txt beside the run.
"""
import re, sys, collections
from pathlib import Path

def samples(run, tag):
    """(arm, rep, tick, text) for every probe line carrying `tag`."""
    out = []
    for line in (run / "events.tsv").read_text(errors="replace").splitlines()[1:]:
        f = line.split("\t")
        if len(f) < 7 or f[5] not in ("every_applied", "manipulation"):
            continue
        blob = "\t".join(f[6:])
        for m in re.finditer(tag + r"(.*?)(?=\t|$)", blob):
            out.append((f[1], f[2], int(f[3]), m.group(1)))
    return out

def x2(run):
    out, groups = [], collections.OrderedDict()
    for arm, rep, tick, txt in samples(run, "x2 groups: "):
        for g in txt.split(" || "):
            m = re.match(r"(\S+) ids=([\d,]+) placed=(\d+) here=(\d+) wet=(\d+) spread=(\d+) cd=(\S*) body=(\S+) salt=(\S+) arrived=(\d+) leader=(\S+) stock=(\d+)", g.strip())
            if not m: continue
            k = (arm, rep, m.group(2))
            r = groups.setdefault(k, {"token": m.group(1), "placed": int(m.group(3)), "first": tick, "wet0": int(m.group(5)), "here0": int(m.group(4)),
                                      "spread": 0, "last_here": None, "gone_at": None, "body": m.group(8), "salt": m.group(9), "arrived": int(m.group(10)),
                                      "stock0": int(m.group(12)), "stock_last": None, "led": False})
            here = int(m.group(4))
            r["spread"] = max(r["spread"], int(m.group(6)))
            r["last_here"] = here; r["stock_last"] = int(m.group(12)); r["led"] = r["led"] or m.group(11) != "nil"
            if here == 0 and r["gone_at"] is None: r["gone_at"] = tick
    for (arm, rep, ids), r in groups.items():
        out.append(f"{arm} rep {rep}: {r['token']} x{r['placed']} into the {r['body']} ({r['salt']}); wet at first sample {r['wet0']}/{r['here0']}; widest spread {r['spread']}; "
                   f"led {r['led']}; {'all gone by tick %d' % r['gone_at'] if r['gone_at'] else 'still %d on the map at the end' % (r['last_here'] or 0)}; stock {r['stock0']} -> {r['stock_last']}")
    couples = sorted({(a, rp, t) for a, rp, t, txt in samples(run, "couple=") if not txt.startswith("nil")})
    out.append(f"coupled windows seen at {len(couples)} sample(s)")
    return out

def x5(run):
    out, by = [], collections.defaultdict(list)
    for arm, rep, tick, txt in samples(run, "x5 sample: "):
        by[(arm, rep)].append(txt)
    for (arm, rep), lines in by.items():
        jobs = catches = 0; near = []; vs = []
        for t in lines:
            m = re.search(r"vermin (-?\d+); near subjects ([\d,]*); jobs (.*?); report hits (\d+)", t)
            if not m: continue
            vs.append(int(m.group(1))); near += [int(x) for x in m.group(2).split(",") if x]
            js = m.group(3).split()
            jobs += sum(1 for j in js if not j.endswith(":none") and "ermin" in j or "Catch" in j or "Hunt" in j)
            catches = max(catches, int(m.group(4)))
        out.append(f"{arm} rep {rep}: {len(lines)} samples; vermin on the map {vs[0] if vs else '?'} -> {vs[-1] if vs else '?'}; mean vermin within 6 tiles {sum(near)/len(near) if near else 0:.2f}; "
                   f"subject samples on a vermin/catch/hunt job {jobs}; catch reports (max in the last 60) {catches}")
    return out

def x6(run):
    out, by = [], collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for arm, rep, tick, txt in samples(run, "x6 sample: "):
        for item in txt.split():
            m = re.match(r"(\S+)#(\d+)=(in|over|dry)", item)
            if m: by[(arm, rep)][m.group(1)][m.group(3)] += 1
    for (arm, rep), sp in by.items():
        parts = []
        for tok, c in sorted(sp.items()):
            n = sum(c.values())
            parts.append(f"{tok}: in {100*c['in']/n:.0f}% over {100*c['over']/n:.0f}% dry {100*c['dry']/n:.0f}% of {n}")
        out.append(f"{arm} rep {rep}: " + "; ".join(parts))
    return out

def main(run_dir):
    run = Path(run_dir)
    xid = run.parent.name
    lines = {"X2": x2, "X5": x5, "X6": x6}[xid](run)
    text = "\n".join(lines)
    (run / "tally.txt").write_text(text + "\n")
    print(text)

if __name__ == "__main__":
    main(sys.argv[1])
