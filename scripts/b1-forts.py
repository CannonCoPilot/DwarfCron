#!/usr/bin/env python3
"""The 1x1-per-biome test forts, embarked from the R11 test world (region8: Snospdastrasp, "The Last Planets").

User ruling R11 (1 Oct 2026): all testing and experimentation from now on uses the world in save folder region8.
The programme is data/eco-review/part1/B-dials-groups-forts.md section 10, moved from region6 to region8: one 1x1
fort per distinct biome, plus the six named needs (OCEAN shoreline, LAKE, RIVER, SAVAGE, a calm fort, GOOD, EVIL).

Steps (each prints what it would do with --dry-run and touches nothing):
  survey   RIG. `cx-lifecycle.sh survey region8` and `rivers region8` -> data/forts/region8-survey.tsv and
           data/forts/region8-rivers.tsv. No survey of region8 exists yet (1 Oct 2026); the world was generated
           outside the rig, and its region data is not readable from the save on disk.
  pick     DESK. Read the survey and choose one tile per need and per biome -> data/forts/region8-b1-picks.tsv.
  embark   RIG. For each pick: `cx-lifecycle.sh embark1 rx ry NAME ox oy` (a 1x1 at offset ox,oy), `facts NAME`
           (saved beside the registry), `save-backup NAME preverify` (what eco-run and cx-experiment restore), then
           region8's bytes are hashed again: any change to the world folder stops the programme at once.
           One row per fort in data/forts/b1-forts.tsv (eco-run.py builds a B1BASE_<save> block from each).
  status   DESK. The registry, and which picks are not yet embarked.

Names (section 10.5): B1-R8-<CODE>-<rx>_<ry>[-NEED], e.g. B1-R8-FTCN-12_40 or B1-R8-OCNT-03_17-SHORE.
Thresholds as the tool's V7.alignment (seasonal-wildlife.lua V7.alignment): good evilness < 33, evil >= 66; savagery
calm < 33, savage >= 66. The world_region good/evil flags V7.alignment also reads are not in the survey; `facts` after
the embark is the check.

Usage: b1-forts.py survey [--dry-run]
       b1-forts.py pick [--survey F] [--rivers F] [--out F]
       b1-forts.py embark [--picks F] [--only NEED,NEED] [--dry-run]
       b1-forts.py status
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LC = ROOT / "scripts" / "cx-lifecycle.sh"
FORTS = ROOT / "data" / "forts"
WORLD = os.environ.get("CX_TEST_WORLD", "region8")
TAG = os.environ.get("CX_TEST_WORLD_TAG", "R8")
SAVE_ROOT = Path(os.environ.get(
    "DF_SAVE_DIR", Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save"))
SURVEY = FORTS / f"{WORLD}-survey.tsv"
RIVERS = FORTS / f"{WORLD}-rivers.tsv"
PICKS = FORTS / f"{WORLD}-b1-picks.tsv"
REGISTRY = FORTS / "b1-forts.tsv"
FACTS = FORTS / "b1"

CALM, SAVAGE, GOOD, EVIL = 33, 66, 33, 66
CODES = {
    "MOUNTAIN": "MNTN", "GLACIER": "GLAC", "TUNDRA": "TNDR",
    "SWAMP_TEMPERATE_FRESHWATER": "SWTF", "SWAMP_TEMPERATE_SALTWATER": "SWTS", "MARSH_TEMPERATE_FRESHWATER": "MRTF",
    "MARSH_TEMPERATE_SALTWATER": "MRTS", "SWAMP_TROPICAL_FRESHWATER": "SWPF", "SWAMP_TROPICAL_SALTWATER": "SWPS",
    "SWAMP_MANGROVE": "SWMG", "MARSH_TROPICAL_FRESHWATER": "MRPF", "MARSH_TROPICAL_SALTWATER": "MRPS",
    "FOREST_TAIGA": "TAIG", "FOREST_TEMPERATE_CONIFER": "FTCN", "FOREST_TEMPERATE_BROADLEAF": "FTBL",
    "FOREST_TROPICAL_CONIFER": "FTTC", "FOREST_TROPICAL_DRY_BROADLEAF": "FTDB", "FOREST_TROPICAL_MOIST_BROADLEAF": "FTMB",
    "GRASSLAND_TEMPERATE": "GRTM", "SAVANNA_TEMPERATE": "SVTM", "SHRUBLAND_TEMPERATE": "SHTM",
    "GRASSLAND_TROPICAL": "GRTR", "SAVANNA_TROPICAL": "SVTR", "SHRUBLAND_TROPICAL": "SHTR",
    "DESERT_BADLAND": "DSBD", "DESERT_ROCK": "DSRK", "DESERT_SAND": "DSSD",
    "OCEAN_TROPICAL": "OCNP", "OCEAN_TEMPERATE": "OCNT", "OCEAN_ARCTIC": "OCNA",
    "LAKE_TEMPERATE_FRESHWATER": "LKTF", "LAKE_TEMPERATE_BRACKISHWATER": "LKTB", "LAKE_TEMPERATE_SALTWATER": "LKTS",
    "LAKE_TROPICAL_FRESHWATER": "LKPF", "LAKE_TROPICAL_BRACKISHWATER": "LKPB", "LAKE_TROPICAL_SALTWATER": "LKPS",
}
PICK_COLS = ["need", "save", "rx", "ry", "ox", "oy", "biome", "sav", "evil", "river", "major", "lake", "site", "same8",
             "nbr_ocean", "why", "flags"]
REG_COLS = ["save", "status", "world", "tag", "need", "rx", "ry", "ox", "oy", "biome", "sav", "evil", "spot", "facts", "note"]


def code(biome: str) -> str:
    return CODES.get(biome) or "".join(w[:2] for w in biome.split("_"))[:4].upper()


def read_tsv(p: Path) -> list[dict]:
    with open(p) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def write_tsv(p: Path, cols: list[str], rows: list[dict]):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def i(r, k, d=0):
    try:
        return int(r.get(k, d))
    except (TypeError, ValueError):
        return d


# ------------------------------------------------------------------------------------------------------ pick --
def is_ocean(b): return b.startswith("OCEAN")
def is_lake(b): return b.startswith("LAKE")


def ocean_side(grid: dict, x: int, y: int) -> tuple[int, int] | None:
    """The 1x1 offset that puts the fort on the side of the tile facing the ocean: 0 or 15 on that axis, 7 on the
    other. A 1x1 is one mid-level tile of the region's 16x16; DF's biome edges are ragged across those tiles, so the
    edge one facing an ocean tile is the likeliest to hold both shore and water (B section 10.2: 'place it on the
    shoreline'). Checked after the embark by `facts` (water by body)."""
    for dx, dy, off in ((1, 0, (15, 7)), (-1, 0, (0, 7)), (0, 1, (7, 15)), (0, -1, (7, 0))):
        n = grid.get((x + dx, y + dy))
        if n and is_ocean(n["biome"]):
            return off
    return None


def score_interior(r: dict) -> tuple:
    """Lower is better: no site, interior (same8 = 8), no volcano, mid savagery and evilness (no alignment confound)."""
    return (i(r, "site"), -i(r, "same8"), i(r, "volcano"), abs(i(r, "sav") - 50) // 10, abs(i(r, "evil") - 50) // 10,
            i(r, "y"), i(r, "x"))


def pick(survey: list[dict], rivers: list[dict] | None = None) -> list[dict]:
    grid = {(i(r, "x"), i(r, "y")): r for r in survey}
    land = [r for r in survey if not is_ocean(r["biome"]) and not is_lake(r["biome"])]
    out, used = [], set()

    def add(need, r, why, ox=7, oy=7, flags=""):
        x, y = i(r, "x"), i(r, "y")
        used.add((x, y))
        suffix = "" if need.startswith("biome:") else "-" + need.upper()
        out.append(dict(need=need, save=f"B1-{TAG}-{code(r['biome'])}-{x:02d}_{y:02d}{suffix}", rx=x, ry=y, ox=ox, oy=oy,
                        biome=r["biome"], sav=r.get("sav"), evil=r.get("evil"), river=r.get("river"), major=r.get("major"),
                        lake=r.get("lake"), site=r.get("site"), same8=r.get("same8"), nbr_ocean=r.get("nbr_ocean"),
                        why=why, flags=flags))

    # OCEAN: a land tile with ocean neighbours, the fort on the side facing the water
    shore = sorted((r for r in land if i(r, "nbr_ocean") >= 2 and ocean_side(grid, i(r, "x"), i(r, "y"))),
                   key=lambda r: (i(r, "site"), -i(r, "nbr_ocean"), i(r, "volcano"), i(r, "y"), i(r, "x")))
    if shore:
        r = shore[0]; ox, oy = ocean_side(grid, i(r, "x"), i(r, "y"))
        add("shore", r, f"land tile with {r.get('nbr_ocean')} ocean neighbours; 1x1 on the ocean side", ox, oy, "verify-water")
    # LAKE: a lake tile; prefer one inside a lake of 2+ tiles (same8 >= 1) and no major river (the LAKE fort's inflow)
    lakes = sorted((r for r in survey if is_lake(r["biome"]) or i(r, "lake")),
                   key=lambda r: (i(r, "major"), -i(r, "same8"), i(r, "site"), i(r, "y"), i(r, "x")))
    if lakes:
        add("lake", lakes[0], "lake tile; away from a major river where one exists", flags="verify-water")
    # RIVER: a major river through interior land; the rivers survey (when present) names the exit edge
    rv = {(i(r, "x"), i(r, "y")): r for r in (rivers or [])}
    rivs = sorted((r for r in land if i(r, "major") and (i(r, "x"), i(r, "y")) not in used),
                  key=lambda r: ((i(r, "x"), i(r, "y")) not in rv, ) + score_interior(r))
    if rivs:
        add("river", rivs[0], "major river through interior land", flags="verify-river")
    # SAVAGE (prefer not mountain, mid evilness), CALM, GOOD (calm or mid savagery), EVIL (not savage)
    def best(cands, need, why, flags=""):
        cands = [r for r in cands if (i(r, "x"), i(r, "y")) not in used]
        if cands:
            add(need, sorted(cands, key=score_interior)[0], why, flags=flags)
            return True
        return False
    best([r for r in land if i(r, "sav") >= SAVAGE and r["biome"] != "MOUNTAIN"] or
         [r for r in land if i(r, "sav") >= SAVAGE], "savage", f"savagery >= {SAVAGE}")
    best([r for r in land if i(r, "sav") < CALM and r["biome"] != "MOUNTAIN"] or
         [r for r in land if i(r, "sav") < CALM], "calm", f"savagery < {CALM}")
    if not best([r for r in land if i(r, "evil") < GOOD and i(r, "sav") < SAVAGE], "good", f"evilness < {GOOD}, not savage"):
        best([r for r in land if i(r, "evil") < GOOD], "good", f"evilness < {GOOD}", flags="good-and-savage")
    if not best([r for r in land if i(r, "evil") >= EVIL and i(r, "sav") < SAVAGE], "evil", f"evilness >= {EVIL}, not savage"):
        best([r for r in land if i(r, "evil") >= EVIL], "evil", f"evilness >= {EVIL}", flags="evil-and-savage")
    # one per remaining land biome (oceans and lakes are covered by shore and lake)
    for b in sorted({r["biome"] for r in land}):
        cands = [r for r in land if r["biome"] == b]
        best(cands, f"biome:{b}", f"interior {b} (same8 {sorted(cands, key=score_interior)[0].get('same8')})")
    missing = [n for n in ("shore", "lake", "river", "savage", "calm", "good", "evil") if n not in {p["need"] for p in out}]
    for n in missing:
        out.append(dict(need=n, save="", why="no tile in this world meets it", flags="MISSING: seed search (B 10.2)"))
    return out


# ------------------------------------------------------------------------------------------------------- rig --
def sh(*args, dry=False, timeout=1800) -> str:
    cmd = [str(LC), *map(str, args)]
    if dry:
        print("  would run: cx-lifecycle.sh " + " ".join(map(str, args)))
        return ""
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    out = (p.stdout + p.stderr).replace("\r", "")
    if p.returncode != 0:
        raise RuntimeError(f"cx-lifecycle {' '.join(map(str, args))} rc={p.returncode}: {out.strip()[-400:]}")
    return p.stdout.replace("\r", "")


def tree_hash(path: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(path)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def cmd_survey(a):
    if not (SAVE_ROOT / WORLD).is_dir():
        sys.exit(f"no world folder {SAVE_ROOT / WORLD}")
    print(f"survey of {WORLD} (R11 test world) -> {SURVEY}, {RIVERS}")
    out = sh("survey", WORLD, dry=a.dry_run)
    if not a.dry_run:
        lines = [l for l in out.splitlines() if "\t" in l]
        SURVEY.write_text("\n".join(lines) + "\n")
        print(f"  {len(lines) - 1} region tiles")
    out = sh("rivers", WORLD, dry=a.dry_run)
    if not a.dry_run:
        lines = [l for l in out.splitlines() if "\t" in l]
        RIVERS.write_text("\n".join(lines) + "\n")
        print(f"  {max(0, len(lines) - 1)} river tiles")
    return 0


def cmd_pick(a):
    src = Path(a.survey) if a.survey else SURVEY
    if not src.exists():
        sys.exit(f"no survey at {src}: run `b1-forts.py survey` on the rig first (none of {WORLD} exists yet)")
    rv = Path(a.rivers) if a.rivers else RIVERS
    rows = pick(read_tsv(src), read_tsv(rv) if rv.exists() else None)
    dest = Path(a.out) if a.out else PICKS
    write_tsv(dest, PICK_COLS, rows)
    for r in rows:
        print(f"  {r['need']:<32} {r.get('save') or '-':<34} {r.get('biome') or '':<30} sav {r.get('sav') or '':>3} "
              f"evil {r.get('evil') or '':>3}  {r.get('flags') or ''}")
    print(f"{len(rows)} picks -> {dest}")
    return 0


def cmd_embark(a):
    src = Path(a.picks) if a.picks else PICKS
    if not src.exists():
        sys.exit(f"no picks at {src}: run `b1-forts.py pick` first")
    picks = [p for p in read_tsv(src) if p.get("save")]
    if a.only:
        want = set(a.only.split(","))
        picks = [p for p in picks if p["need"] in want or p["save"] in want]
    reg = read_tsv(REGISTRY) if REGISTRY.exists() else []
    done = {r["save"] for r in reg if r.get("status") == "ok"}
    todo = [p for p in picks if p["save"] not in done]
    world_dir = SAVE_ROOT / WORLD
    if not world_dir.is_dir():
        sys.exit(f"no world folder {world_dir}")
    print(f"{len(todo)} fort(s) to embark from {WORLD} ({len(done)} already registered)")
    h0 = None if a.dry_run else tree_hash(world_dir)
    if not a.dry_run:
        print(f"  {WORLD} sha256 {h0[:12]} (checked again after every embark)")
        sh("save-backup", WORLD, "pre-b1")   # a copy of the world before the programme, never restored by this script
    FACTS.mkdir(parents=True, exist_ok=True)
    for p in todo:
        name = p["save"]
        print(f"== {name}: {p['biome']} at {p['rx']},{p['ry']} offset {p['ox']},{p['oy']} ({p['need']})")
        row = dict(save=name, status="failed", world=WORLD, tag=TAG, need=p["need"], rx=p["rx"], ry=p["ry"], ox=p["ox"],
                   oy=p["oy"], biome=p["biome"], sav=p["sav"], evil=p["evil"], spot="land",   # every embark has land
                   facts=str((FACTS / f"{name}.facts.txt").relative_to(ROOT)), note=p.get("flags", ""))
        try:
            sh("embark1", p["rx"], p["ry"], name, p["ox"], p["oy"], dry=a.dry_run)
            sh("title", dry=a.dry_run)
            facts = sh("facts", name, dry=a.dry_run)
            if not a.dry_run:
                (FACTS / f"{name}.facts.txt").write_text(facts)
            sh("save-backup", name, "preverify", dry=a.dry_run)
            row["status"] = "ok"
        except Exception as e:
            row["note"] = f"{row['note']} {e!r}"[:300]
            print(f"  !! {e!r}"[:400])
        if not a.dry_run:
            h1 = tree_hash(world_dir)
            if h1 != h0:
                reg.append(row); write_tsv(REGISTRY, REG_COLS, reg)
                sys.exit(f"!! {WORLD} CHANGED during the embark of {name} ({h0[:12]} -> {h1[:12]}): stopping. The world "
                         f"copy taken before the programme is the backup '{WORLD}.pre-b1'; ask the user before restoring.")
            reg.append(row); write_tsv(REGISTRY, REG_COLS, reg)
    print(f"registry: {REGISTRY}" + (" (dry run: nothing written)" if a.dry_run else ""))
    return 0


def cmd_status(a):
    reg = read_tsv(REGISTRY) if REGISTRY.exists() else []
    picks = read_tsv(PICKS) if PICKS.exists() else []
    have = {r["save"]: r for r in reg}
    print(f"test world {WORLD} ({TAG}); survey {'present' if SURVEY.exists() else 'NOT YET RUN'}; "
          f"{len(picks)} picks; {sum(1 for r in reg if r.get('status') == 'ok')} forts registered")
    for p in picks:
        r = have.get(p.get("save"))
        print(f"  {p['need']:<32} {p.get('save') or '-':<34} {r['status'] if r else 'not embarked'}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("survey"); s.add_argument("--dry-run", action="store_true"); s.set_defaults(fn=cmd_survey)
    p = sub.add_parser("pick"); p.add_argument("--survey"); p.add_argument("--rivers"); p.add_argument("--out"); p.set_defaults(fn=cmd_pick)
    e = sub.add_parser("embark"); e.add_argument("--picks"); e.add_argument("--only"); e.add_argument("--dry-run", action="store_true")
    e.set_defaults(fn=cmd_embark)
    t = sub.add_parser("status"); t.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
