# User review of the ECO Wildlife Study page, Part 1 of 2 (1 Oct 2026)
Page: https://claude.ai/artifact/Qq4zH3VFQPmTaUPownxDyw . HOLD all revisions of the report until Part 2 arrives.
Instruction: "Thoroughly and critically explore all issues, make plans, discover solutions."

1. "BENIGN is the switch, not LARGE_PREDATOR." What exactly is the effect of LARGE_PREDATOR? How does the game use it?
2. "In the caverns it pairs natives freely." What are natives and what are wilds? Mutually exclusive? Do the two include all creatures?
3. "Pack size decides kills, not prey size." Is the ability to kill = (pack mass)/(prey mass)? Is prey mass NOT a determining factor
   for pairing, attacks and kills by a pack?
4. "The apex FREQUENCY doesn't bring apexes." Test incrementally along the full FREQUENCY range. How often do we want APEX anyway?
   We do want to simulate a trophic pyramid (levels: producers, herbivores, carnivores/omnivores, apex; ~10% energy transfer per
   level; pyramids of energy (always upright), biomass (can invert, e.g. oceans), numbers).
5. "Curious beasts come to steal, then leave." Is that tick counter reachable, and can we simply increase it?
6. "Most of the tool's dials don't move the map." Explain each dial's mechanism (as inferred from evidence and documentation). If they
   don't move the map, are we measuring the wrong metrics? Failing to control lurking variables? Need tighter designs and spaces?
7. "Flags don't start cavern invasions." DF's invasion mechanic is disabled. We want an alternative, loosely based on invasion, not
   replicating it. Clarify 'irruption' vs 'invasion'. Irruption should trigger waves of cavern civilization units, in larger numbers
   than the default roster rotation. Creature tokens applied to individuals on the map can trigger more wandering, rage, sneaking,
   stealing, meandering. Experiment with a layer that lets the tool assign tokens to cavern civ units during irruption events.
   Systematically establish the impact on cavern dweller behaviour during irruption waves vs normal cavern roster rotation. Then
   rebalance irruption for in-game realistic ecological responsiveness. Clarify purpose, features, functions; plan redesign/rebuild.
8. "Fortress water is shallow." Probably needs a rebalance: prey species on the map should pull pelagic predators into the shallow
   waters of any OCEAN biome fort.
9. "Placed orcas strand when unled." Ensure all pods, schools or other grouping aquatic groups are led.
10. "A cell." Redesign experiments to use only 1x1 embarks, one per distinct biome in the world map; make sure embarks exist for
    OCEAN, LAKE, RIVER, SAVAGE, GOOD and EVIL.
11. "DF aims every non-wild unit" figure makes no sense to the user.
12. "No skill or ambush arm beat the unchanged lone hunter." The data looks like SNEAK alone was best. Apply it even if not conclusive.
13. "Wild animals never sneak." Confirm or invalidate another way; the SNEAK attack data suggests SNEAK affects hunting success.
14. "Combat skills raise engagement." Need better data. If true, more engagements even without more kills is a success.
15. "Wildlife tokens travel in a few tight blocks" figure: widen to page width, resize font, caption must explain and interpret
    the grouping and sorting.
16. "A groups-at-once limit of sqrt(embark tiles)+1 adds about one group on 5x5 and 6x6 maps." What other factor or mechanic (vanilla or
    the tool) could hold concurrent groups well below the limits? Tested in all layer types? Re-run for per-layer and cumulative
    on-map group counts. Critically review the rig's testing mechanisms: are distinct groups identified and counted correctly?
17. "When the kangaroo entry hit 0 no kangaroo came" figure: reset the Y-axis scale.
18. "A leader holds flocks and schools" figure appears empty; revise.
19. "On the desk, the v2.2 ladder" figure appears empty; revise.
