"""Item 6: pick a GOOD and an EVIL embark tile from a `cx-lifecycle survey` TSV. A tile qualifies when it is land (no ocean,
lake, mountain or glacier), has no site, and its evilness is < 33 (good) or >= 66 (evil); among those, prefer the most
neighbours of the same alignment (the tool reads all 9 region tiles a fort draws from). Prints 'good rx ry' and 'evil rx ry'."""
import sys, csv
rows = [r for r in csv.DictReader(open(sys.argv[1]), delimiter="\t") if r.get("x", "").isdigit()]
E = {(int(r["x"]), int(r["y"])): int(r["evil"]) for r in rows}
def land(r): return not any(k in r["biome"] for k in ("OCEAN", "LAKE", "MOUNTAIN", "GLACIER", "POOL")) and r["site"] in ("0", "false", "")
for name, test in (("good", lambda v: v < 33), ("evil", lambda v: v >= 66)):
    best = None
    for r in rows:
        x, y = int(r["x"]), int(r["y"])
        if not land(r) or not test(E[(x, y)]): continue
        score = sum(1 for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and test(E.get((x + dx, y + dy), 50)))
        if best is None or score > best[0]: best = (score, x, y, r["biome"], E[(x, y)])
    print(name, *(best[1:3] if best else ("none", "none")), "#", best and f"nbrs {best[0]}/8 {best[3]} evil {best[4]}")
