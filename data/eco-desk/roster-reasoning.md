# Reasoning through the imposed roster / food-web rules (draft, 30 Sep 00:3x; numbers from the prototype to follow)

## What DF will and will not carry out (measured today, ECO P1/T1/S, plus E-series)
- A predator edge is only real if the tool WRITES it (PREDATOR_OR_PREY). With no write, 0 attacks in 40 pairs over 3,000 t.
- A written edge is carried out only by a NON-BENIGN attacker (coyote yes; fox, badger, BENIGN-flipped wolf never).
  LARGE_PREDATOR is not needed once the edge is written. So "who can eat" in DF = not BENIGN; the rules' size classes
  are the tool's policy on top of that, not DF's.
- Prey that is not BENIGN fights back and can kill the predator (deer made non-BENIGN killed 2 wolves; buffalo killed a lion).
- Vermin are not units. No unit fights a vermin; vermin never fight each other. Vermin "predation" in DF exists only as
  HUNTS_VERMIN / DIVE_HUNTS_VERMIN / VERMIN_GOBBLER jobs on units (X5: no measurable effect at natural exposure).
- Nothing in DF eats a corpse (S1); eating remains is the tool's own walk + delete (S2 pending).
- One wildlife group per layer at a time in DF (wiki; the tool's gate allows 3 land / 2 water / 2 cavern). A roster of
  8 animals per layer-season is a menu; the map shows 1–3 of them at once, chosen by FREQUENCY (X3, F1).

## Rule by rule
**A. Only GIANT and PREDATOR eat non-giant predators.** Sound as an apex rule. Ambiguity: "PREDATOR" = the LARGE_PREDATOR
tag or the tool's role? If the tag, then coyote/jackal/bobcat/snakes (non-BENIGN, carnivorous, no LP tag) can never eat
another predator — consistent. Edge case: a GIANT prey species (giant deer) is not a predator, so rule A says nothing
about who eats it; E/F decide. Emergent: apex predators become one-directional sinks (nothing eats them) — fine, but
predator-on-predator edges are also where DF produces the most combat (E11c: rival predators fight as STRANGERs anyway).

**B. Small predators eat vermin only.** Mechanically this is the only thing small predators CAN do: they are mostly
BENIGN+BONECARN (fox, stoat, mongoose, raptors, otters) and never act on a unit relation. So B matches DF. But their
vermin eating is only the hunting flags (HUNTS_VERMIN etc.), which showed no effect at natural vermin density (X5).
Contradiction risk: under the tool's size bands (small < 150k cm³) WOLF (40k), DINGO, COYOTE, HYENA, CHEETAH are all
"small" — B would forbid the classic pack hunters from eating deer. Size classes for predators must not be the prey
bands; see "Size" below.

**C. Split bird vermin / flying-insect vermin; birds eat insects.** The split already exists in the tool (families
'fliers' HAS_ANY_FLIER vs 'flies' VERMIN_MICRO/ROTTER). A vermin-on-vermin layer cannot be a DF relation (vermin are
not units); it can only be tool bookkeeping: debit the insect family's abundance by a rate proportional to the bird
family's abundance each tick-pass (a Lotka–Volterra step). Runaway risk: with no floor, insects hit 0 and stay there
(vermin that live in features don't restock — wiki bug 2780 for aquatic vermin); with no ceiling, birds grow without
bound if the tool also credits birds. Needs a floor and a ceiling, or it is cosmetic.

**D. Only large (tag AND size) and GIANT predators attack sentients / animal people.** Sound for fort safety. But "tag
AND size" is nearly empty under the tool's bands: large ≥ 1M cm³ excludes every land LARGE_PREDATOR except crocodiles/
giants; lion 200k, grizzly 200k, polar bear 400k are "medium". With AND, almost nothing may touch animal people, so
animal-person prey (a large share of cavern and some surface lists) get no predator → isolated nodes → step 6 must draw
an edge that D forbids (mutual exclusion). Also: whether DF attacks a sentient depends on the relation write and
BENIGN, not size; and a written edge between a predator and an animal-person group of a civ can drag the fort in
(E22: gathered dingoes killed a caravan animal). D should be an exclusion list in the WRITE, not a roster rule.

**E. Medium eat small–medium; large eat small–medium.** As written, large and medium predators have the same diet, and
nobody eats LARGE prey except GIANTs (A only covers predators) → "giant or large prey [1]" slot is filled but uneaten
unless a pack bonus (F) lifts a large predator — only pack LPs (wolves, dingoes, hyenas) get there, and they are "small"
by size. Likely intended: large eat medium–large. Otherwise the large-prey slot is an isolated node every time (step 6
must break E).

**F. Pack +1 size class.** Good and matches reality (wolf packs on elk, E17/P1: 6 wolves killed deer 3.5× their mass).
Runaway: with + 1 on an already-"large" predator there is no class above; clamp. Definition of pack matters:
cluster_number > 1 includes herd grazers; restrict to (not BENIGN) ∧ carnivore ∧ cluster > 1. DF's group size is
honoured at the draw (X4) and the tool can hold a group together with a leader (L1: spread 52 → 2–4 tiles), so the pack
is real on the map.

**G. Caverns as three ecosystems by "bizarreness".** DF already stratifies caverns: UNDERGROUND_DEPTH min:max on each
creature gates which cavern layers it can appear in, so part of the "bizarre" gradient is native. A score is feasible
from raw facts (not MUNDANE, no MAMMAL class, body plan, syndromes/extracts, NOBREATHE, webs, size extremes) — the
prototype computes it and its correlation with UNDERGROUND_DEPTH. Constraint: each cavern layer's pool is small (CTRL:
~a dozen species over three layers) — a bizarre cut may leave slots empty; the cut must be a preference order, not a
hard filter, or layers go unfillable.

## The algorithm (steps 0–8)
- Step 0 caps sum to 8 non-vermin + 3–6 vermin per layer per season → up to 7 layers × 4 seasons × 8 = 224 animal
  slots. A region pool rarely holds that many distinct species per layer; either species repeat across seasons (which is
  good: continuity) or slots go empty. Termination of step 4 "until caps reached" is NOT guaranteed: a class with no
  candidate in the pool (e.g. no giant predator in a temperate grassland; no large predator in temperate-only biomes —
  census: zero temperate-only LPs) blocks forever → needs "until caps reached OR no progress in a full pass".
- Step 1 random high-value seed: biases rosters toward exotic, large, trainable animals; the seed then drives steps 2–3,
  so the web is shaped around it. With a fixed seed per embark this is reproducible; the effect on variety is large.
- Steps 2–3 branching: each added animal pulls a predator and a prey → growth ×2 per round; the caps stop it after ~2
  rounds. Order-dependence: whichever class fills first starves later ones (a small-prey slot taken by the 2nd round's
  prey). Deterministic ordering by class need (fill the emptiest class first) removes most of this.
- Step 5 adds every allowed edge → density rises sharply (P1: every non-BENIGN predator attacks every written prey).
  Every written edge costs (a) a rel_map pair (500×500 slots) and (b) combat on the map. Dense webs are more combat,
  more alerts (A1 filter needed), more deaths → POPULATION exhaustion (N1) sooner.
- Step 6 isolated nodes: after 5, the isolated nodes are exactly the ones A–F exclude (large prey under E, animal people
  under D, vermin that no unit can eat). Drawing "an appropriate edge" then violates a rule → the rules need a priority
  order (safety D > physical realm > size E/F > coverage 6).
- Step 7 frequencies 1×…9×: FREQUENCY is a comparative weight at DF's pick (X3; F1 measures proportionality) — the
  ladder is implementable for units. For vermin FREQUENCY is not the lever (vermin come from pool abundance) → use the
  tool's abundance/stock. Ratios across layers do not interact (each layer draws separately).
- Step 8 pack/herd guarantee: can fail in cavern layers and in solitary-predator biomes (cheetah/tiger/leopard are
  cluster 1) → needs a fallback (group size lever: the tool can set cluster {N,N} on any species; X4/E12).

## Seasons (cross-cutting)
- Per-season webs break predator–prey continuity: a predator present in Winter whose prey are all Summer-only has
  nothing to eat (harmless in DF — it just wanders — but the web is fiction). Require each predator's season set to be
  a subset of the union of its prey's seasons.
- Raw NO_SPRING/SUMMER/AUTUMN/WINTER must be respected (the tool currently ignores them: 22 NO_WINTER species can be
  dealt Winter — T0/W2). Whether DF itself honours them at the pick is T2 (running).

## Size (cross-cutting)
Predators and prey need different class boundaries. Prey bands by body size are fine; predator classes should come from
(a) BENIGN or not (can it act), (b) LARGE_PREDATOR tag, (c) size relative to prey (take/need of eats(): mass ×
group^0.75 × 1.5 for LP vs prey mass × 0.9/0.6), not fixed bands. The eats() rule already encodes E and F continuously.
