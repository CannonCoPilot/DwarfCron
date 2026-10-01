# Vermin predation: what GOBBLE_VERMIN is, how to test it, how to make the vermin (30 Sep 2026)

Read-only research for the ECO desk. Nothing here has run on the rig yet. Lua is in `lua/`; every file passes `luac -p`
once its placeholders are filled.

## 1. What the raws and DF say

**Who carries the tokens** (DF 53.16 vanilla raws, `data/eco-desk/tokens-by-creature.tsv`, confirmed by grepping
`data/vanilla/vanilla_creatures/objects/*.txt`):

| token | creatures |
|---|---|
| GOBBLE_VERMIN_CLASS:EDIBLE_GROUND_BUG (the only class used) | wild: BIRD_KIWI, BIRD_DUCK, BIRD_GOOSE, BIRD_PEAFOWL_BLUE, HEDGEHOG, PANGOLIN (+ their giants and animal people); domestic: BIRD_CHICKEN, BIRD_GUINEAFOWL, BIRD_TURKEY |
| GOBBLE_VERMIN_CREATURE | nobody in vanilla (the token exists: caste field `gobble_vermin_creature` + `gobble_vermin_caste`) |
| CREATURE_CLASS:EDIBLE_GROUND_BUG (the prey) | ROACH_LARGE (VERMIN_GROUNDER, loose), BEETLE (VERMIN_SOIL), THRIPS (VERMIN_SOIL), ANT (VERMIN_SOIL_COLONY) |
| HUNTS_VERMIN | CAT only |
| DIVE_HUNTS_VERMIN | BIRD_FALCON_PEREGRINE (+ giant) |
| VERMIN_EATER (vermin that raid food stockpiles) | ROACH_LARGE, RAT_DEMON, WAMBLER_FLUFFY, LIZARD_RHINO_TWO_LEGGED, LIZARD, HAMSTER, RAT |

So the vanilla game wires exactly one predator-prey link through GOBBLE: ground birds, hedgehogs and pangolins on four
bug species. Every other vermin family has no consumer in the raws.

**Wiki** ([Creature token](https://dwarffortresswiki.org/index.php/Creature_token)):
- GOBBLE_VERMIN_CLASS: "The creature eats vermin of the specified class."
- GOBBLE_VERMIN_CREATURE: "The creature eats a specified vermin."
- HUNTS_VERMIN: "Creature hunts and kills nearby vermin" (for tame animals: wanders between food on the ground and stockpiles).
- DIVE_HUNTS_VERMIN: hunts vermin by diving from the air; on tame animals it acts like HUNTS_VERMIN.
- CREATURE_CLASS: arbitrary; vanilla uses GENERAL_POISON, EDIBLE_GROUND_BUG, MAMMAL, POISONOUS.

**Wiki** ([Vermin](https://dwarffortresswiki.org/index.php/Vermin)): vermin "do not breed, but 'spawn', spontaneously
appearing in their natural environment"; "cannot be engaged in combat"; "Some types of vermin are inexhaustible"; cats and
peregrines hunt them. No word on GOBBLE, despawn or depletion.

**Player reports** ([Chicken](https://dwarffortresswiki.org/index.php/Chicken),
[Steam: Chicken and vermin](https://steamcommunity.com/app/975370/discussions/0/5792223132450150205/)): poultry
"spend most of their time rooting around on the ground, eating vermin"; chickens locked in a room don't starve because
they eat whatever bugs appear. That reads as a **feeding** mechanic (hunger met by vermin) rather than visible hunting.
Nothing documents whether a gobbled vermin object is deleted, whether wild (never hungry?) units gobble at all, or any
report line. [Bug 5674](https://dwarffortressbugtracker.com/view.php?id=5674) (dwarves eating caged vermin) adds nothing.

**DFHack structures** ([df-structures](https://github.com/DFHack/df-structures), fetched with `gh api`):
- `caste_raw.gobble_vermin_class`, `gobble_vermin_creature`, `gobble_vermin_caste`: `stl-vector` of `stl-string`
  pointers (original names `vermin_gobbler_class/creature/caste`).
- `caste_raw_flags.VERMIN_GOBBLER`: a derived caste flag. DF very likely tests the flag before the strings, so a
  run-time write must set it too (gobble_write.lua does).
- `vermin` (= `event_verminst`, instance vector `world.event.vermin`): race, caste, pos, visible, countdown, item,
  flags {already_deleting, is_colony, triggerable, is_roaming_colony}, amount ("10000001 means infinity"), population
  (world_population_ref), category (vermin_category: Eater, Grounder, Rotter, Swamper, Colony, Triggered, Item, Sphere,
  FromColony), id. Colonies are also listed in `world.event.vermin_colonies`.
- `unit.counters2.hunger_timer` / `thirst_timer`: the feeding readout.

## 2. Answers

1. **What GOBBLE does in fortress mode:** documented only as "eats vermin of the class". The best evidence (poultry
   live without grazing) says it feeds the gobbler. Whether a *wild* unit gobbles, and whether the vermin object
   disappears, is unknown and is exactly what the block below measures, with three readouts (vermin objects near and
   map-wide, the gobbler's hunger_timer, and any report text).
2. **How to observe it:** `world.event.vermin` gives every vermin object with pos and amount; count by race within r,
   skipping `is_colony` and `already_deleting` (vermin_count.lua). Note `cx-eco vermin` counts only `visible ~= false`
   objects and includes colonies: that is why VR/VRL/VRR read bumblebee and termite colonies and saw nothing.
   **Also: the VR duck was a native gobbler, but its only prey class (EDIBLE_GROUND_BUG) was not in that spot** --
   bumblebees and termites are not edible ground bugs. VR could not have shown a gobble even if it worked.
3. **Creating loose vermin is feasible.** DFHack's own `hack/scripts/colonies.lua` (place_vermin) does it:
   `df.vermin:new()`, set race, caste, amount, visible, pos, insert into `world.event.vermin` (and `vermin_colonies`
   for a colony). vermin_create.lua does the loose version: N objects of amount 1, category Grounder, on walkable,
   dry, outdoor tiles within r, population ref copied from a natural vermin of that race (or any loose grounder) so DF
   never meets an empty population ref on despawn. Risk: an uninitialised field DF dereferences later. Mitigation: run
   it first in a 1-cell smoke on a scratch copy, step 2,000 ticks, save and reload.
   **Natural loose spots:** `vspot` should skip `flags.is_colony`, `is_roaming_colony` and categories Colony/FromColony,
   and require >= 20 loose objects within 12 tiles; on CTRL the natural densest spots were colonies, so placement is the
   dependable route.

## 3. Block VRM (proposal for eco-run.py; 2 replicates; CTRL surface 'land' spot)

Each cell: sustain; create 40 ROACH_LARGE (EDIBLE_GROUND_BUG, loose grounder) within r 6 and 20 GRASSHOPPER
(VERMIN_GROUNDER, NOT edible-class: specificity control) within r 6; read; place 4 consumers at r 3; read hunger;
then every 500 ticks for 6,000 ticks: vermin_count for both races + hunger; at the end, report lines that mention a
vermin name.

| arm | consumer | gobble state |
|---|---|---|
| none | - | vermin alone: baseline drift, wander, despawn |
| duck | BIRD_DUCK x4 (wild) | native GOBBLE_VERMIN_CLASS:EDIBLE_GROUND_BUG |
| hedgehog | HEDGEHOG x4 (wild) | native class |
| badger | BADGER x4 | absent (control consumer) |
| badger_cls | BADGER x4 | written: class EDIBLE_GROUND_BUG + VERMIN_GOBBLER |
| badger_cre | BADGER x4 | written: creature ROACH_LARGE:ALL + VERMIN_GOBBLER (tests GOBBLE_VERMIN_CREATURE) |
| cat | CAT x4 (wild) | HUNTS_VERMIN (the other mechanism, for comparison) |
| chicken_tame | BIRD_CHICKEN x4, tamed (`makeown` or set as fort pets) | native; tests whether gobbling needs a hungry (tame) unit |

Readouts per cell: roach near/map/objs at 0 and every 500 t (drop in duck/hedgehog/badger_cls vs none and badger);
grasshopper the same (should not drop: class specificity); hunger_timer trace (resets = fed by vermin).
Post: gobble_restore.lua for BADGER.

Reading: a roach drop in the gobbler arms beyond `none` = GOBBLE removes vermin and the tool can use it as the vermin
link (write GOBBLE_VERMIN_CLASS / _CREATURE on consumers). No drop but hunger resets = GOBBLE feeds without removing,
so the tool must debit stock itself (rule C bookkeeping) but can still use the token for who-eats-what. Neither =
wild units don't gobble in fortress mode; test tame (chicken_tame) to confirm the mechanism exists at all.

eco-run integration (the parent's code; placeholders filled with `.replace`, Lua joined to one line):

```python
VRM = pathlib.Path(__file__).resolve().parents[1] / "data/eco-desk/v2/research/lua"
def inline(name, **kw):
    s = " ".join(l.strip() for l in (VRM / name).read_text().splitlines() if l.strip() and not l.strip().startswith("--"))
    for k, v in kw.items(): s = s.replace("{" + k + "}", str(v))
    return "lua:" + s
def vrm(consumer=None, gob=None, n=4):
    st = ["lua:dfhack.run_command('cx-load','sustain'); print('eco sustain ok=1')",
          inline("vermin_create.lua", RACE="ROACH_LARGE", N=40, R=6), inline("vermin_create.lua", RACE="GRASSHOPPER", N=20, R=6)]
    if gob: st.append(inline("gobble_write.lua", P=consumer, KIND=gob[0], CLS=gob[1]))
    if consumer: st.append(f"spawn {consumer} {n} {{X}} {{Y}} {{Z}} 3")
    for i in range(13):
        st += [inline("vermin_count.lua", RACE="ROACH_LARGE", R=8, TAG=f"t{i*500}"),
               inline("vermin_count.lua", RACE="GRASSHOPPER", R=8, TAG=f"t{i*500}")]
        if consumer: st.append(inline("hunger.lua", P=consumer, TAG=f"t{i*500}"))
        if i < 12: st.append("step:500")
    post = [inline("gobble_restore.lua", P=consumer)] if gob else []
    return dict(steps=st, ticks=10, nowatch=True, post=post)
BLOCKS["VRM"] = dict(fort="CTRL", spot="land", cells={
    "none": vrm(), "duck": vrm("BIRD_DUCK"), "hedgehog": vrm("HEDGEHOG"), "badger": vrm("BADGER"),
    "badger_cls": vrm("BADGER", ("class", "EDIBLE_GROUND_BUG")), "badger_cre": vrm("BADGER", ("creature", "ROACH_LARGE")),
    "cat": vrm("CAT")})
```

Prerequisites: (1) a 1-cell VRM smoke (`--only none`, 1 rep) that saves and reloads after creation, to show created
vermin survive and don't crash DF; (2) a manifest subject receipt per cell: `vcreate made >= 30` before comparing
arms; (3) the `{ new = true, value = ... }` insert into a string-pointer vector is the DFHack idiom but unverified on
53.16 -- the smoke should print `#ca.gobble_vermin_class` after the write (fallback: `local s = df.new('string');
s.value = v; vec:insert('#', s)`).

The tame-chicken arm needs a tame path (`makeown` on the units, or spawn as fort pets); left out of the block code
until the wild arms are read.
