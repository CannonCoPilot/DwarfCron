
## Addendum 92 — four experiments on v6.2.0: real cavern pressure, the ten-day wait, flier flocks, a real invader (21–22 September 2026)

**T9b — real cavern pressure (DwarfCron run 20260921-224702).** T9 pinned every cavern's pressure at the threshold; T9b earns it.
Three citizens teleported onto cavern 1's floor (the only headless way underground), gain 0.02 per citizen per groups tick
against decay 0.01, steady state 6.0 over a threshold of 1.0; the module left to arm the next roster-admitted cavern-1
arrival on its own, and the cavern gate's gap to halve past 0.5. Control: the same three underground, module off.
Four valid replicates. Pressure on, both replicates: pressure from the three citizens rose past the threshold on day 19 and
reached 3.9–4.1 by mid-season (steady state 6.0 is not reached in a season at these rates); the module armed the next
roster-admitted cavern-1 arrival on its own three times per replicate — troglodytes ×2, a giant earthworm and a cave crocodile
in the first, a giant olm, a giant earthworm and a giant cave swallow in the second — each arming resetting the cavern's
pressure to zero and standing down after its twenty days, the armed troglodytes fighting the miner for two days before the
miners killed them. Control, both replicates: pressure 0.000 at every one of the thirty-four samples, nothing armed, no flag set, the same three
citizens underground. The pressure path is **PASS 2 of 2 in both arms**. Two things the
run did not show. The halved gate: the cavern gate fired once per replicate, before any pressure existed, and never again,
because the tracked cavern groups sat at their cap of two all season — the halving under pressure is untested here, and
the probe's gap readout goes negative once the gate's next tick is stale. The dwarves: all three teleported citizens died about
sixty days after the teleport in every replicate, control included, with no combat report naming a citizen in three of the
four — the cavern floor is cut off from the fort on CTRL, and that is thirst, not the module. The tally beside the run counts
armings from the sample trace, because the manifest's ledger dump filtered on the wave kind and never printed an irruption line.

**T8f — why one first-light release waited ten days (run 20260921-233953).** Hypothesis: a standing gated land group from the
prior season delays DF's next draw after a release. HELD keeps the oldest gated land group across the boundary; CLEAR
dismisses every land group at spring day 70+. Measured: ticks from summer day 1's gate opening to the first surface arrival.
Four valid replicates. HELD, both replicates: the hold took the oldest gated land group at spring day 70 — six ravens in
the first, two in the second — raised every member's leave countdown to sixty days, and none of them left before summer;
the gate released the first group's write at day 80 on its own clock, which moves no bird. On summer day 1 the groups job set
the week's table and opened the gate in both, and DF's first surface arrival followed within the day: a kestrel 102 ticks
after the release, a great horned owl 762 ticks after it. CLEAR, both replicates: the dismissal at day 70 took three land groups each time (a wombat, a
kestrel and four kangaroos; nine emus and two skunks) and all had left by day 74, though DF drew fresh land groups before the
boundary in both, so neither boundary was met clean. In the second, DF's owl came 565 ticks after the release. In the first,
**no surface animal arrived in the 14.7 summer days the replicate observed**, with ravens at 101 of 354, kestrels and owls at
100 open in the population table at the first summer sample; the surface draws that had come every nine or ten days through
spring stopped after day 81 while the deep and cavern draws went on (four demons on summer day 2, a toad and a crocodile on
day 8). HELD 0.1 and 0.6 days against CLEAR 0.5 and more than 14.7: **no separation.** **A standing land group
does not delay DF's draw after a first-light release.** T8d's ten-day wait is not explained by the five badgers that stood
across that boundary. Across T8d, T8e and T8f the first-light release has been answered within the week six times in eight
and waited ten days or more twice, once with a standing group and once without; what the data point at is DF's draw going to
another layer while the surface waits, and that is a candidate for a further experiment, not a finding. The tally reports a
replicate with no arrival as a censored wait rather than dropping it.

**E42b — can a flier flock exceed the written cluster range (run 20260922-004339).** The land roster closed to ravens alone,
then to emus alone, both under trickle so the {2,1} write stands on the one species; every surface wave sized from arrivals
within 500 ticks.
Four valid replicates; the write stood on the one species from the first release (the setup's own receipt read "standing on
0" because it called the write with a stale copy of the config before the scheduler had enabled it, and the tool then wrote
the range itself at spring day 15 — the ledger line is the receipt). Every replicate's first draw lands inside the window
between load and the first sample, where it cannot be placed against the write; those waves are listed and not scored (the
emu arm's first were nine and eight, sizes only the default 2–10 gives, though the ledger showed the write standing by the
first sample — DF may size a wave when it schedules it, ahead of its arrival, which is E42's original caveat). Scored waves, a wave being one run of consecutive unit ids of one species from one population
entry: ravens 1, 1, 2, 2, 1, 2, 2 and 2, 3, 2, 2, 2, 3, 3; emus 2, 2, 3, 2, 1, 1, 2 and 2, 3, 3, 2, 1, 2. **Both species run one
over the written maximum, and neither runs two over**: three raven trios in one replicate, none in the other, one emu trio
in one replicate and two in the other. The trio is DF's draw, not an extra: the population entry is debited by two for a pair and by three for a trio.
So the cluster raw is not a soft ceiling for fliers in particular — it is a range DF reaches one past for a flightless bird
too, and the promise stays *sized 1–2, a flock may run one over*. Why DF reaches one past the written maximum is the open
question; an inclusive-range count in DF's sizing is the candidate, and the harness cannot see DF's arithmetic.

**E23d — the invasion exclusion against a real invader (run 20260922-014731).** E23b drew nothing in two seasons because CTRL had
never opened a cavern. E23d opens it headlessly: every cavern feature marked Discovered, the announcement flag set, three
citizens on cavern 1's floor, irritation pinned at 100000 every sample, two seasons. Control untouched. The exclusion
(addendum 49) must keep every invasion_id >= 0 unit out of the cavern count.
Four valid replicates, two seasons each. Invaded: every precondition E23b lacked was met and held — three cavern features
marked discovered, the first-cavern announcement flag reading true, three citizens on cavern 1's floor, irritation pinned at
100,000 on each depth at every sample (300,000 summed) with the attacker cap at fifty — and **no unit with an invasion id
appeared at any of the samples: zero at 67 of 67 samples in both replicates**. The teleported dwarves died around day 80 as in T9b and migrants brought
the count to nine and twelve; the cavern held up to thirty-six and thirty-seven wild units, the deep layer five to eleven. Control: irritation zero at every sample, nothing discovered, nobody underground, zero invaders, the fort
growing to fourteen and ten by migration.
Three independent routes to a real cavern invasion have now failed — maxed irritation on an unopened cavern (E23b), a forced
army evaluation (E23c), and an opened cavern with dwarves in it under maxed irritation (E23d) — so the flags are not the
missing piece. What none of them checked is the world, and one probe on the freed rig did (`probe-layer-linked.lua`,
its output beside the run): the world holds thirty civilisations, twenty-five of them layer-linked subterranean animal
peoples, every one without a site — normal for that kind, which lives in cavern populations — and **CTRL's own cavern
population table, thirty-five species across three layers, holds not one animal person**. DF sends a cavern invasion from
an animal-people population in the fort's reach, and this embark has none, so no flag, pin or teleport could have produced
one here. E23 needs a fort whose caverns hold animal people, which is a choice of embark, not of settings. Until it exists
the exclusion (addendum 49) stays *wired correctly, not validated end-to-end*, as it has been since E23b.

**v6.2.1, wording only (ed5752e).** E42b takes "flier" out of trickle's promise: USAGE and the header now read *a flock may
run one over, flier or not*; no code changed, luac and luacheck as before. Deployed to the rig at 04:04 after the chain
exited, both files byte-identical to the repository.

Validation: DwarfCron validate-full 20260922-040815 on v6.2.1 — 146 PASS of 176 claims, 1 FAIL, 1 DOC-DRIFT, 0 DEAD;
14 NOT-TESTABLE-HERE, 1 UNWIRED (the plan's arming step, folded into v6.1.0), 13 BACKLOG. The FAIL was `mech.groups.track`
timing out at the RPC on one call while the next check read the same groups eleven seconds later and passed; the DRIFT was
the docket's source line carrying a placeholder where the new hash belonged, which the driver reads. Neither is the tool.
RERUN_RESULT

Companion reports the same night: the Wilderpop Model at rev 32 (T9b, T8f, E42b and E23d cards; §8 rows T9c, T8g, E42c,
E23e in their place), the design at rev 21 and the Backlog re-dated (companion blocks only), the playtest rebuilt from the
clean run, the Docket at rev 13; each names the others.
