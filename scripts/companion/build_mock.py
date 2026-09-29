#!/usr/bin/env python3
"""Build the browser companion prototype (mock data) for seasonal-wildlife.

Sample data: the BOATS roster snapshot inside data/bestiary/creatures.json (boats_* fields, 26 Sep 2026): the 115
species with an active flag. Food-web pairs follow the tool's habitat rule (USAGE.md 'The species model') with the
size bands as a stand-in for its prey-size test. Output: the page, with the data inlined, at argv[1].
Usage: build_mock.py <out.html>
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BR = {"small": 0, "medium": 1, "large": 2}

def species():
    out = []
    for x in json.load(open(ROOT / "data/bestiary/creatures.json")):
        if not x.get("boats_layers") or x.get("boats_active") is None:
            continue
        lay = x["boats_layers"]
        layer = "cavern" if "cavern" in lay else ("water" if lay == ["water"] else "land")
        s = dict(key=(layer + ":" if layer != "land" else "") + x["id"], token=x["id"], name=x["name"], layer=layer,
                 habitat=x["habitat"], role=x["role"], band=x["band"], active=bool(x["boats_active"]),
                 seasons=sorted({int(c) for c in (x["boats_seasons"] or "")}), stock=int(x["boats_stock"] or 0),
                 freq=int(x["frequency"] or 50), gmin=x["cluster_min"] or 1, gmax=x["cluster_max"] or 1,
                 arrivals=int(x["x1_arrivals"] or 0), climate=round(x["climate_lean"] or 0.5, 2), flier=x["flier"],
                 cls=x["class"], biomes=x["n_biomes"], animal_person=x["animal_person"], giant=x["giant"])
        if s["active"] and not s["seasons"]:   # the one rule: an active species has a season
            s["seasons"] = [3 if s["climate"] < 0.35 else 1 if s["climate"] > 0.65 else 0]
        if not s["active"]:
            s["seasons"] = []
        out.append(s)
    return out

def eats(p, q):
    if p["role"] != "predator" or q["role"] != "prey" or p is q or (p["layer"] == "cavern") != (q["layer"] == "cavern"):
        return False
    if BR[q["band"]] > BR[p["band"]]:
        return False
    ph, qh = p["habitat"], q["habitat"]
    return {"land": qh in ("land", "flier", "waterbird", "semiaquatic"),
            "flier": qh in ("land", "flier", "waterbird") and BR[q["band"]] == 0,
            "waterbird": qh == "aquatic" or (qh in ("flier", "waterbird") and BR[q["band"]] == 0),
            "semiaquatic": qh in ("aquatic", "semiaquatic", "land", "waterbird"),
            "aquatic": qh in ("aquatic", "semiaquatic", "waterbird")}.get(ph, False)

if __name__ == "__main__":
    sp = species()
    data = json.dumps(dict(species=sp, pairs=[[p["key"], q["key"]] for p in sp for q in sp if eats(p, q)]))
    tpl = (Path(__file__).parent / "wildlife-companion.tpl.html").read_text()
    Path(sys.argv[1]).write_text(tpl.replace("__DATA__", data))
