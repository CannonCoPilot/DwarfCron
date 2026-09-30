#!/usr/bin/env python3
"""Extra per-creature raw facts for the roster prototype (files only).

Re-resolves the vanilla raws with eco/census.py's resolver and adds what census.json lacks:
body plan (BODY templates -> stance parts = legs/feet, HEAD parts), syndrome/extract/web flags,
physiology flags (NOBREATHE, NOT_LIVING, NO_EAT ...), valuable-material templates.
Writes roster/features.json {id: {...}}.
"""
import sys, json, re
from pathlib import Path
from collections import defaultdict
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import census as C  # noqa: E402

TAG = re.compile(r"\[([^\[\]]+)\]")

def body_templates():
    out, cur = {}, None
    for p in sorted((C.VAN / "vanilla_bodies/objects").glob("body_*.txt")):
        txt = p.read_text(encoding="latin-1", errors="replace")
        for m in TAG.finditer(txt):
            parts = m.group(1).split(":")
            t = parts[0]
            if t == "BODY":
                cur = parts[1]; out[cur] = {"parts": 0, "stance": 0, "head": 0, "limb": 0, "grasp": 0, "sight": 0}
            elif cur is None:
                continue
            elif t == "BP":
                out[cur]["parts"] += 1
            elif t == "STANCE": out[cur]["stance"] += 1
            elif t == "HEAD": out[cur]["head"] += 1
            elif t == "LIMB": out[cur]["limb"] += 1
            elif t == "GRASP": out[cur]["grasp"] += 1
            elif t == "SIGHT": out[cur]["sight"] += 1
    return out

FLAGS = ["NOBREATHE", "NOT_LIVING", "NO_EAT", "NO_DRINK", "NO_SLEEP", "NOPAIN", "NOEMOTION", "NOFEAR", "NOSTUN",
         "NONAUSEA", "NOTHOUGHT", "NO_THOUGHT_CENTER_FOR_MOVEMENT", "NOBONES", "EXTRAVISION", "FIREIMMUNE",
         "FIREIMMUNE_SUPER", "MAGMA_VISION", "WEBBER", "THICKWEB", "WEBIMMUNE", "AMBUSHPREDATOR", "FANCIFUL",
         "MUNDANE", "NOT_FLESHY", "LIGHT_GEN", "CAN_SPEAK", "CAN_LEARN", "INTELLIGENT", "TRAINABLE_WAR",
         "TRAINABLE_HUNTING", "TRAINABLE", "MILKABLE", "SPECIALATTACK_INJECT_EXTRACT", "SPECIALATTACK_SUCK_BLOOD",
         "EXTRACT", "SYNDROME", "CAN_DO_INTERACTION", "CDI", "BUILDINGDESTROYER", "MEGABEAST", "SEMIMEGABEAST",
         "FEATURE_BEAST", "TITAN", "DEMON", "GOOD", "EVIL", "SAVAGE", "LOCAL_POPS_CONTROLLABLE", "CANOPENDOORS",
         "EQUIPS", "IMMOBILE", "VERMIN_BITE", "SECRETION", "ANTLER", "SHELL", "YARN", "HOMEOTHERM"]
VALUE_TEMPLATES = ("IVORY", "HORN", "PEARL", "SILK", "SHELL", "HOOF", "ANTLER", "TUSK", "YARN", "HAIR", "WOOL", "FEATHER", "CHITIN")

def main():
    bodies = body_templates()
    paths = [(p, "vanilla") for p in sorted((C.VAN / "vanilla_creatures/objects").glob("*.txt"))]
    paths += [(p, "extinct") for p in sorted((C.VAN / "vanilla_creatures_extinct/objects").glob("*.txt"))]
    creatures, variations, source = C.read_objects(paths)
    cache, info, out = {}, {}, {}
    for cid in creatures:
        tags = C.resolve(cid, creatures, variations, cache, info)
        castes, occ = C.caste_walk(tags)
        # body: use the first caste-agnostic/selected BODY lines (union of template names, per-caste dup ignored)
        seen, tmpl = set(), []
        for sel, t, _ in occ.get("BODY", []):
            for name in t[1:]:
                if name not in seen: seen.add(name); tmpl.append(name)
        agg = defaultdict(int)
        for name in tmpl:
            for k, v in bodies.get(name, {}).items(): agg[k] += v
        mats = set()
        for _, t, _ in occ.get("USE_MATERIAL_TEMPLATE", []):
            mats.add(t[1]); mats.update(t[2:])
        blood = [":".join(t[1:]) for _, t, _ in occ.get("BLOOD", [])]
        valuable = sorted({v for v in VALUE_TEMPLATES for m in mats if v in m.upper()})
        # any creature-effect token (CE_*) signals a syndrome effect
        ce = sorted({k for k in occ if k.startswith("CE_")})
        f = {k: int(k in occ) for k in FLAGS}
        f.update({"body_templates": tmpl, "stance": agg["stance"], "heads": agg["head"], "limbs": agg["limb"],
                  "grasp": agg["grasp"], "sight": agg["sight"], "bp": agg["parts"], "mats": sorted(mats),
                  "valuable_mats": valuable, "blood": blood[:1], "ce": ce,
                  "venom_mat": int(any("VENOM" in m.upper() or "POISON" in m.upper() or "EXTRACT" in m.upper() for m in mats))})
        out[cid] = f
    (HERE / "features.json").write_text(json.dumps(out))
    print(len(out), "creatures;", len(bodies), "body templates")

if __name__ == "__main__":
    main()
