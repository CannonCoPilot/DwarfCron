# DF2014:Interaction examples

This page was created to aid those curious about the interaction process by providing example interactions for them to use or study. Those familiar with interaction raws should feel free to add helpful/obscure information to the lists below to help members of the community less experienced with interactions.

1. General Tips

1. Synchronizing Adventure and Fort Mode syndrome timers
Fort mode runs 144 times faster than adventure mode - which means that a syndrome that lasts a single tick in Fort Mode will last 144 ticks in Adventure Mode.  For short-term syndromes, this will cause very different behaviors between the two modes.  In order to ensure that a syndrome operates the same way regardless of mode, add DWF_STRETCH:144 to the end of the CE effect tag.

It is not possible to make a syndrome that lasts shorter than 144 ticks in Adventure Mode

1. Syndromes with no effect
There are times you will want to create a syndrome that has no actual effect - generally in order to add a SYN_CLASS that renders the target untargetable by a different interaction.  Syndromes disappear once their effects have expired, so to do this you will need to add an effect that does nothing.
Some examples:

So if you see tags like this in the examples below, this is what they are for.

1. Material Emission Interactions

Following are several examples of material emission interactions.

1. Multiple Projectile Emission

By adding additional [I_EFFECT:MATERIAL_EMISSION] tags with their associated targets, you may stack additional projectiles.

1. Predefined Material Emissions

If a material is listed in this format, the creature will not need a [CDI:MATERIAL] tag in their creature raws in order to use it. This allows projectile attacks to be gained through substance ingestion, other interactions, etc.

1. Predefined Emissions of Different Types

This interaction fires both a solid glob of basalt and a liquid glob of granite magma.

1. Material Emissions With Immunity

Material emissions used in this format are affected by [IT_CANNOT_HAVE_SYNDROME_CLASS:X] tags (given above as the custom tag NO_EMISSION). This allows a modder to create immunity syndromes, disallowing a creature using the emission interaction from targeting the creature with immunity.

1. Targeted Interactions
Interactions that are specifically intended to target particular types of creatures.

1. Turn Undead
An attack that hits all procedurally-generated zombies and ghouls.

1. Smite Evil
An attack that hits all procedurally-generated bogeymen, night creatures, vampires, werebeasts, demons, and... angels. There does not currently appear to be a way of excluding angels. (Eh, it's DF angels, they probably count as evil anyway).

1. Multi-Stage Interactions
These are more elaborate groups of interactions that allow you to create complex behaviors by using interactions to enable or disable other interactions.

1. Timed Self-Destruct (or other powerful ability) with Override Ability

This will allow the user to explode after spending a certain amount of time in combat.  A few ticks before exploding, it will flash with a "!" as a warning.
You can also replace the explosion with any other powerful ability that you want it to use only after a countdown.
It also comes with a syndrome that will disable the explosion.
This is intended to be used by non-playable units, like animals or zombies.

1. Transformation Interactions
These are interactions that will cause a creature to transform into another creature.

1. Demon Transformation

This is a fairly straightforward transformation, as it only relies on one caste token. This interaction will transform a creature into a random non-unique demon

Note that this interaction will not work in arena mode due to the lack of generated creatures in that mode. However, it will work if a creature performs the interaction in a loaded world that contains generated demons.

1. Vault Guardian Transformation

Transformation syndromes that turn a creature into a titan or demon only really rely on the [DEMON] and [TITAN] tokens, but how can the same be achieved with vault guardians? Below is an example of an interaction that will reliably transform a creature into a random angel.

Note that this interaction will not work in arena mode due to the lack of generated creatures in that mode. However, it will work if a creature performs the interaction in a loaded world that contains vault guardians.

1. See Also
- Creature examples
- Reaction examples
