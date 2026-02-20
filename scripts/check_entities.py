"""Quick diagnostic: compare entity data between legends.xml and legends_plus.xml."""
import xml.etree.ElementTree as ET
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "legends"

# ── legends.xml ──────────────────────────────────────────────────────────────
print("=" * 60)
print("LEGENDS.XML")
print("=" * 60)
# Read with cp437 encoding to handle DF's encoding
with open(DATA / "region1-00100-01-01-legends.xml", "r", encoding="cp437", errors="replace") as f:
    content = f.read()
import re
content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", content)
root_l = ET.fromstring(content)

entities_l = root_l.findall(".//entity")
print(f"Entity count: {len(entities_l)}")

# Analyze tags
all_tags_l = set()
with_type_l = 0
with_race_l = 0
for e in entities_l:
    for child in e:
        all_tags_l.add(child.tag)
    if e.find("type") is not None:
        with_type_l += 1
    if e.find("race") is not None:
        with_race_l += 1

print(f"Entities with <type>: {with_type_l}/{len(entities_l)}")
print(f"Entities with <race>: {with_race_l}/{len(entities_l)}")
print(f"All child tags: {sorted(all_tags_l)}")

# Show first 3
print("\nSample entities:")
for e in entities_l[:3]:
    eid = e.findtext("id")
    name = e.findtext("name")
    etype = e.findtext("type")
    race = e.findtext("race")
    tags = [child.tag for child in e]
    print(f"  id={eid} name={name} type={etype} race={race}")
    print(f"    tags: {tags}")

# ── legends_plus.xml ─────────────────────────────────────────────────────────
print()
print("=" * 60)
print("LEGENDS_PLUS.XML")
print("=" * 60)
tree_p = ET.parse(DATA / "region1-00100-01-01-legends_plus.xml")
root_p = tree_p.getroot()

entities_p = root_p.findall(".//entity")
print(f"Entity count: {len(entities_p)}")

all_tags_p = set()
with_type_p = 0
with_race_p = 0
for e in entities_p:
    for child in e:
        all_tags_p.add(child.tag)
    if e.find("type") is not None:
        with_type_p += 1
    if e.find("race") is not None:
        with_race_p += 1

print(f"Entities with <type>: {with_type_p}/{len(entities_p)}")
print(f"Entities with <race>: {with_race_p}/{len(entities_p)}")
print(f"All child tags: {sorted(all_tags_p)}")

# Show first 3
print("\nSample entities:")
for e in entities_p[:3]:
    eid = e.findtext("id")
    name = e.findtext("name")
    etype = e.findtext("type")
    race = e.findtext("race")
    top_tags = [child.tag for child in e if child.tag in ("id", "name", "type", "race")]
    print(f"  id={eid} name={name} type={etype} race={race}")
    all_e_tags = set(child.tag for child in e)
    print(f"    unique tags: {sorted(all_e_tags)}")

# ── Cross-reference ──────────────────────────────────────────────────────────
print()
print("=" * 60)
print("CROSS-REFERENCE")
print("=" * 60)

ids_l = {e.findtext("id") for e in entities_l}
ids_p = {e.findtext("id") for e in entities_p}

only_l = ids_l - ids_p
only_p = ids_p - ids_l
both = ids_l & ids_p

print(f"In legends.xml only: {len(only_l)}")
print(f"In legends_plus.xml only: {len(only_p)}")
print(f"In both: {len(both)}")

if only_l:
    print(f"  Legends-only IDs (first 10): {sorted([x for x in only_l if x], key=int)[:10]}")
if only_p:
    valid_only_p = [x for x in only_p if x]
    print(f"  Plus-only IDs (first 10): {sorted(valid_only_p, key=int)[:10] if valid_only_p else list(only_p)}")

# For shared entities, check field availability
print("\nField availability for SHARED entities:")
legends_map = {e.findtext("id"): e for e in entities_l}
plus_map = {e.findtext("id"): e for e in entities_p}

l_has_type = 0
p_has_type = 0
l_has_race = 0
p_has_race = 0
l_has_name = 0
p_has_name = 0

for eid in both:
    el = legends_map[eid]
    ep = plus_map[eid]
    if el.findtext("type"): l_has_type += 1
    if ep.findtext("type"): p_has_type += 1
    if el.findtext("race"): l_has_race += 1
    if ep.findtext("race"): p_has_race += 1
    if el.findtext("name"): l_has_name += 1
    if ep.findtext("name"): p_has_name += 1

total = len(both)
print(f"  <name>  legends: {l_has_name}/{total}  plus: {p_has_name}/{total}")
print(f"  <type>  legends: {l_has_type}/{total}  plus: {p_has_type}/{total}")
print(f"  <race>  legends: {l_has_race}/{total}  plus: {p_has_race}/{total}")

# Show a specific entity in both forms
if both:
    sample_id = sorted(both, key=int)[0]
    print(f"\nDetailed comparison for entity id={sample_id}:")
    el = legends_map[sample_id]
    ep = plus_map[sample_id]
    print(f"  LEGENDS:  ", {child.tag: (child.text or "")[:40] for child in el})
    print(f"  PLUS:     ", {child.tag: (child.text or "")[:40] for child in ep if child.tag in ("id","name","type","race")})
