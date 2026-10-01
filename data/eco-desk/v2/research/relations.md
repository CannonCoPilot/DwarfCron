# DF writes PREDATOR_OR_PREY itself: what is known and a block to pin it down (30 Sep 2026)

Read-only research for the ECO desk. Lua: `lua/rel_sample.lua` (passes `luac -p`).

## 1. What the structures say

[df-structures](https://github.com/DFHack/df-structures) `df.unit_reaction.xml`:
- `world.enemy_status_cache` is a `unit_reaction_handlerst`: `slot_used[500]` (bool), `rel_map[500][500].ur`
  (unit_reaction_type), `next_slot`. **At most 500 units hold a slot at once.**
- `unit.enemy.enemy_status_slot` (`reaction_column`) indexes it; -1 = no slot. RELP saw 0 natives slotted at load and
  42 after 100 ticks: slots are assigned lazily when units start considering each other.
- `unit_reaction_type` (bay12 UnitReactionType) includes WE_ARE_SAME_RACE_WILDERNESS_ANIMALS, **PREDATOR_OR_PREY**,
  **BENIGN_ANIMAL**, **DANGEROUS_ANIMAL**, STRANGER, SAME_CULTURE, ENEMY_FIGHTER, MONSTER, INTRUDER, among others.
- DFHack's `makeown.lua` (`clear_enemy_status`) is the only shipped code touching it: it frees a unit's slot and sets
  its whole row and column to -1. Nothing in DFHack writes PREDATOR_OR_PREY.
- DFHack 51.07-r1 changed `rel_map[x][y]` to `rel_map[x][y].ur` ([changelog](https://docs.dfhack.org/en/stable/docs/about/History.html)).

The wiki ([Creature token](https://dwarffortresswiki.org/index.php/Creature_token)) gives the behaviour side only:
- LARGE_PREDATOR: "Will attack other creatures that are smaller than it."
- BENIGN: "non-aggressive by default", flees unfriendly creatures, fights only when enraged.
- AMBUSHPREDATOR: "start out hidden and remain near its original location until its prey draws near."
- CARNIVORE: "only eats meat." BONECARN implies CARNIVORE.

No wiki, DFHack doc or forum page found names when DF fills PREDATOR_OR_PREY (search: "enemy_status_cache",
"PREDATOR_OR_PREY", "unit_reaction"; only the changelog hit).

## 2. What the rig data already say

- **RELP (1 run, CTRL, tool off):** within 3,000 ticks DF wrote PREDATOR_OR_PREY from a placed LION, from dwarves
  and from yak/horse/pig/reindeer **toward one wild BIRD_KESTREL**; nobody toward the lion (it got STRANGER).
  BIRD_KESTREL raws: BENIGN, BONECARN, FLIER, 250 cm3.
- **Units killed with no written relation:** BADGER (BENIGN, BONECARN, 15,000), EMU, KANGAROO, WOMBAT, PORCUPINE,
  SKUNK, GROUNDHOG, KAKAPO (all BENIGN, non-carnivore except the badger), all smaller than the attacker.
- **AMBUSHPREDATOR is not the cause:** STL2 norel (lion, no AMBUSHPREDATOR) killed 8 badgers; CAL wolves (no
  AMBUSHPREDATOR) killed 53 natives. In STL only the AMBUSHPREDATOR arm hunted natives (103 attacks vs 0 in ctl),
  so the flag may raise the rate; the block below separates it.

**Working hypotheses** (to test, none established):
- H1 carnivore-as-target: units react PREDATOR_OR_PREY to a wild carnivore/bonecarn (the kestrel, the badgers) --
  "that is a predator" from the observer's side.
- H2 large-predator-on-smaller: a LARGE_PREDATOR (or non-BENIGN carnivore) writes PREDATOR_OR_PREY toward smaller
  wild units it perceives (the wiki's "attacks creatures smaller than it").
- H3 time/encounter: entries appear on first sight within vision range; a 30,000-tick cell simply gives more sightings
  than a 3,000-tick one (why P1 saw nothing).

## 3. Block RELS (proposal for eco-run.py; CTRL, tool off; 2 replicates)

Every cell: sustain; `rel_sample reset`; place the subject (no relation written by us); `watch`; then every 3,000 ticks
`rel_sample` (prints each NEW PREDATOR_OR_PREY / DANGEROUS_ANIMAL / BENIGN_ANIMAL entry with both units' species,
class cit/wild/tame/other, flags L B C O A, adult size, distance at that sample, and unit ids) and a summary line;
`read` at the end gives attacks and deaths by pair, so "did an attack follow" = an attack pair matching an entry.

| cell | subject | ticks | separates |
|---|---|---|---|
| nat | nothing placed | 100,800 (one season) | what DF writes among natives, livestock and dwarves alone; rate per season |
| lion | LION x1 | 30,000 | baseline placed hunter |
| lion_benign | LION x1, BENIGN on | 30,000 | does BENIGN stop its outgoing entries (H2)? |
| lion_nolp | LION x1, LARGE_PREDATOR off | 30,000 | is LARGE_PREDATOR the writer (H2)? |
| lion_ambush | LION x1, AMBUSHPREDATOR on | 30,000 | the user's question: does AMBUSHPREDATOR add entries or attacks? |
| deer | DEER x1 (BENIGN herbivore) | 30,000 | negative control: a placed non-predator |
| badger | BADGER x4 (BENIGN BONECARN, small) | 30,000 | H1: do others write PREDATOR_OR_PREY toward a placed carnivore? |

Readings: entries out of LION but not out of lion_nolp -> LARGE_PREDATOR writes them; entries toward BADGER from
many observers -> H1; lion_ambush entries ~ lion but more attacks -> AMBUSHPREDATOR raises follow-through, not the
writes. The `nat` cell gives the background rate the tool's writes add to.

```python
REL = pathlib.Path(__file__).resolve().parents[1] / "data/eco-desk/v2/research/lua"
def rel(tag): return inline("rel_sample.lua", TAG=tag)      # inline() as in vermin.md
def rels(subject=None, n=1, flags=(), ticks=30000):
    st = ["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')", rel("reset")]
    st += [f"flag {subject} {f}" for f in flags]
    if subject: st.append(f"spawn {subject} {n} {{X}} {{Y}} {{Z}} 5")
    st.append("watch")
    for i in range(ticks // 3000):
        st += ["step:3000", rel(f"t{(i+1)*3000}")]
        if i % 10 == 9: st.append("lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')")
    return dict(steps=st, ticks=10)        # watch kept: read gives attacks/deaths by pair
BLOCKS["RELS"] = dict(fort="CTRL", spot="land", cells={
    "nat": rels(ticks=100800), "lion": rels("LION"), "lion_benign": rels("LION", flags=("BENIGN on",)),
    "lion_nolp": rels("LION", flags=("LARGE_PREDATOR off",)), "lion_ambush": rels("LION", flags=("AMBUSHPREDATOR on",)),
    "deer": rels("DEER"), "badger": rels("BADGER", 4)})
```

Notes: rel_sample is O(slotted^2) (<= 500^2 = 250k reads); at the 57 slotted RELP saw it is trivial. Entries are keyed
by unit-id pair, so a pair is reported once per cell (the first sample it appears in). Cell order should alternate across
replicates (session-length effect on speed, memory fps-load-facts).
