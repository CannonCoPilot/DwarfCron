# DF2014:Tissue definition token

__TOC__

1. Tokens

**Token
**Arguments
**Description

| | - name
- plural
| plural can alternatively be NP (No Plural) or STP (Standard Plural, adds an 's' on the end).

| | - material token
| Defines the tissue material.

| | - value
| The relative thickness of the tissue. A higher thickness is harder to penetrate, but raising a tissue's relative thickness decreases the thickness of all other tissues.

| | - value
| Lower is faster. Omitting the token will result in a tissue that never heals.

| | - value
| Related to how much said tissue bleeds. Higher = More bleeding (Which is why the heart has the highest value.)

| | - value
| Related to how much pain your character will suffer when said tissue is damaged. Higher = More pain when damaged (Which is why the bone tissue has a much higher value than other tissues. A broken bone hurts a lot more than a flesh cut.)

| | | The thickness of the tissue increases when character strength increases.

| | | Thickness of said tissue increases when the character eats and doesn't exercise sufficiently.

| | | The tissue contains arteries. Edged attacks have the chance to break an artery, increasing blood loss.

| | | Simply, whether or not the tissue will be scarred once healed.

| | | Holds the body part together. A cut or a fracture disables the body part it's in.

| | | Any ligaments or tendons are part of this tissue. Vulnerable to edged attacks, damage disables the limb.

| | | The tissue will not heal, or heals slower, until it is set by a bone doctor.

| | | The broken tissue can be fixed with a cast or a splint to restore function while it heals.

| | | The tissue performs some sort of special function (e.g. sight, hearing, breathing, etc.)  An organ with such a function will stop working if a sufficient amount of damage is sustained by its FUNCTIONAL tissues. If an organ has no FUNCTIONAL tissues, it will stop working only if it is severed or destroyed entirely by heat or cold.

| | | Nervous function - not used. This token is used in [OBJECT:BODY] tokens.

| | | If a creature has no functioning parts with the THOUGHT token, it will be unable to move or breathe.  NO_THOUGHT_CENTER_FOR_MOVEMENT bypasses this limitation.

| | | Seems to affect where sensory or motor nerves are located, and whether damage to this tissue will render a limb useless.

| | | Used to smell - not used. This token is used in [OBJECT:BODY] tokens.

| | | Used to hearing - not used. This token is used in [OBJECT:BODY] tokens.

| | | Unknown - not used. Most likely related to flying, see [[Body_token#FLIER|[FLIER] in [OBJECT:BODY]]]. 

| | | Used to breathing - not used. This token is used in [OBJECT:BODY] tokens.

| | | Used to seeing - not used. This token is used in [OBJECT:BODY] tokens.

| | | Holds body parts together.  A body part will not be severed unless all of its component tissues with the CONNECTS tag are severed.

| | | Causes tissue to sometimes severely bleed when damaged.  This is independent of its VASCULAR value.

| | - value
| Tissue supplies the creature with heat insulation. Higher values result in more insulation.

| | | ?

| | | The tissue can be styled as per a tissue style (defined in an entity entry)

| | - value
| Value can be one of the following:
;LAYER
:Regular layer tissue.
;STRANDS
:Can be spun into thread at a farmer's workshop. Edge attacks will pass right through the tissue.
;FEATHERS
:Edge attacks will pass right through the tissue.
;SCALES
:?
;CUSTOM
:?

| | - value
| Tissue is implicitly attached to another tissue and will fall off if that tissue layer is destroyed. Used for hair and feathers, which are subordinate to skin.

| | - SOLID, SOLID_POWDER, LIQUID, or GAS
(possibly others, as well. Needs testing.)
| Sets/forces a default material state for the selected tissue.

| | | The selected tissue leaks out of the creature when the layers above it are pierced.

1. Tissue layer tokens

These are used in creature raws to override the above for whatever reason.

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | - tissue
| Sets a tissue layer to be made of a different tissue.

| | - value
| Sets a new relative thickness for selected tissue layers.

| | | Gives the CONNECTS attribute to selected layers.

| | | Gives Major Artery attribute to selected layers.

| | - value
| Sets a new HEALING_RATE of the selected tissue layers.

| | | Sets a new VASCULAR value (which modulates bleeding) for selected tissue layers.

| | | Sets a new number of pain receptors for selected tissue layers.

1. Default tissues

1. Values

**style="font-size: 150%;"| TISSUE_TEMPLATE !! TISSUE_NAME !! TISSUE_MATERIAL !! TISSUE_MAT_STATE !! RELATIVE_THICKNESS !! HEALING_RATE !! VASCULAR !! PAIN_RECEPTORS !! SUBORDINATE_TO_TISSUE !! INSULATION !! TISSUE_SHAPE

| SKIN_TEMPLATE || skin:NP || LOCAL_CREATURE_MAT:SKIN || || 1 || 100 || 1 || 5 || || || LAYER

| FAT_TEMPLATE || fat:NP || LOCAL_CREATURE_MAT:FAT || || 1 || 100 || 3 || 5 || || 100 || LAYER

| MUSCLE_TEMPLATE || muscle:muscles || LOCAL_CREATURE_MAT:MUSCLE || || 3 || 100 || 5 || 5 || || || LAYER

| BONE_TEMPLATE || bone:NP || LOCAL_CREATURE_MAT:BONE || || 2 || 1000 || 3 || 50 || || || LAYER

| SHELL_TEMPLATE || shell:NP || LOCAL_CREATURE_MAT:SHELL || || 2 || 1000 || || || || || LAYER

| HORN_TEMPLATE || horn:NP || LOCAL_CREATURE_MAT:HORN || || 2 || || || || || || LAYER

| HOOF_TEMPLATE || hoof:NP || LOCAL_CREATURE_MAT:HOOF || || 2 || || || || || || LAYER

| CARTILAGE_TEMPLATE || cartilage:NP || LOCAL_CREATURE_MAT:CARTILAGE || || 2 || || || || || || LAYER

| HAIR_TEMPLATE || hair:NP || LOCAL_CREATURE_MAT:HAIR || || 1 || || || || SKIN || 100 || STRANDS

| CHEEK_WHISKERS_TEMPLATE || cheek whisker:STP || LOCAL_CREATURE_MAT:HAIR || || 2 || || || || SKIN || || STRANDS

| CHIN_WHISKERS_TEMPLATE || chin whisker:STP || LOCAL_CREATURE_MAT:HAIR || || 2 || || || || SKIN || || STRANDS

| MOUSTACHE_TEMPLATE || moustache:NP || LOCAL_CREATURE_MAT:HAIR || || 2 || || || || SKIN || || STRANDS

| SIDEBURNS_TEMPLATE || sideburns:NP || LOCAL_CREATURE_MAT:HAIR || || 2 || || || || SKIN || || STRANDS

| EYEBROW_TEMPLATE || eyebrow:NP || LOCAL_CREATURE_MAT:HAIR || || 2 || || || || SKIN || || STRANDS

| EYELASH_TEMPLATE || eyelash:eyelashes || LOCAL_CREATURE_MAT:HAIR || || 2 || || || || SKIN || || STRANDS

| FEATHER_TEMPLATE || feather:STP || LOCAL_CREATURE_MAT:FEATHER || || 2 || || || || SKIN || 100 || FEATHERS

| SCALE_TEMPLATE || scale:STP || LOCAL_CREATURE_MAT:SCALE || || 1 || 100 || 1 || 5 || || || SCALES

| NAIL_TEMPLATE || nail:NP || LOCAL_CREATURE_MAT:NAIL || || 2 || || || || || || LAYER

| CLAW_TEMPLATE || claw:NP || LOCAL_CREATURE_MAT:CLAW || || 2 || || || || || || LAYER

| TALON_TEMPLATE || talon:NP || LOCAL_CREATURE_MAT:TALON || || 2 || || || || || || LAYER

| TOOTH_TEMPLATE || tooth:NP || LOCAL_CREATURE_MAT:TOOTH || || 2 || || || || || || LAYER

| IVORY_TEMPLATE || ivory:NP || LOCAL_CREATURE_MAT:IVORY || || 2 || || || || || || LAYER

| EYE_TEMPLATE || eye tissue:NP || LOCAL_CREATURE_MAT:EYE || || 1 || 100 || 3 || 5 || || || LAYER

| NERVE_TEMPLATE || nervous tissue:NP || LOCAL_CREATURE_MAT:NERVE || || 1 || || 3 || || || || LAYER

| BRAIN_TEMPLATE || brain tissue:NP || LOCAL_CREATURE_MAT:BRAIN || || 1 || || 3 || || || || LAYER

| LUNG_TEMPLATE || lung tissue:NP || LOCAL_CREATURE_MAT:LUNG || || 1 || 100 || 8 || 5 || || || LAYER

| HEART_TEMPLATE || heart tissue:NP || LOCAL_CREATURE_MAT:HEART || || 1 || 100 || 10 || 5 || || || LAYER

| LIVER_TEMPLATE || liver tissue:NP || LOCAL_CREATURE_MAT:LIVER || || 1 || 100 || 8 || 5 || || || LAYER

| GUT_TEMPLATE || gut:NP || LOCAL_CREATURE_MAT:GUT || || 1 || 100 || 3 || 5 || || || LAYER

| STOMACH_TEMPLATE || stomach tissue:NP || LOCAL_CREATURE_MAT:STOMACH || || 1 || 100 || 3 || 5 || || || LAYER

| PANCREAS_TEMPLATE || pancreatic tissue:NP || LOCAL_CREATURE_MAT:PANCREAS || || 1 || 100 || 3 || 5 || || || LAYER

| SPLEEN_TEMPLATE || spleen tissue:NP || LOCAL_CREATURE_MAT:SPLEEN || || 1 || 100 || 5 || 5 || || || LAYER

| KIDNEY_TEMPLATE || kidney tissue:NP || LOCAL_CREATURE_MAT:KIDNEY || || 1 || 100 || 8 || 5 || || || LAYER

| FLAME_TEMPLATE || flames:NP || LOCAL_CREATURE_MAT:FLAME || GAS || 1 || || || || || || LAYER

| CHITIN_TEMPLATE || chitin:NP || LOCAL_CREATURE_MAT:CHITIN || || 1 || 100 || 1 || 5 || || || LAYER

| SPINE_TEMPLATE || spine:NP || LOCAL_CREATURE_MAT:SPINE || || 2 || || || || || || LAYER

| SPONGE_TEMPLATE || sponge:NP || LOCAL_CREATURE_MAT:SPONGE || || 1 || 100 || 3 || 5 || || 100 || LAYER

**style="font-size: 150%;"| TISSUE_TEMPLATE !! TISSUE_NAME !! TISSUE_MATERIAL !! TISSUE_MAT_STATE !! RELATIVE_THICKNESS !! HEALING_RATE !! VASCULAR !! PAIN_RECEPTORS !! SUBORDINATE_TO_TISSUE !! INSULATION !! TISSUE_SHAPE

1. Flags

**style="font-size: 150%;"| TISSUE_TEMPLATE !! THICKENS_ON_ENERGY_STORAGE !! THICKENS_ON_STRENGTH !! ARTERIES !! SCARS !! MUSCULAR !! FUNCTIONAL !!  STRUCTURAL !! CONNECTIVE_TISSUE_ANCHOR !! CONNECTS !! SETTABLE !! SPLINTABLE !! COSMETIC !! STYLEABLE 

| SKIN_TEMPLATE || || || || X || || || || || X || || || || 

| FAT_TEMPLATE || X || || || X || ||  || || || X || || || || 

| MUSCLE_TEMPLATE || || X || X || X || X || || || || X || || || || 

| BONE_TEMPLATE || || || || || || || X || X || X || X || X  || || 

| SHELL_TEMPLATE || || || || || || || X || || X || X || X || || 

| HORN_TEMPLATE || || || || || || || X || || X || || || || 

| HOOF_TEMPLATE || || || || || || || X || || X || || || || 

| CARTILAGE_TEMPLATE || || || || || || || X || || X || || || || 

| HAIR_TEMPLATE || || || || || || || || || || || || X || X 

| CHEEK_WHISKERS_TEMPLATE || || || || || || || || || || || || X || X 

| CHIN_WHISKERS_TEMPLATE || || || || || || || || || || || || X || X 

| MOUSTACHE_TEMPLATE || || || || || || || || || || || || X || X 

| SIDEBURNS_TEMPLATE || || || || || || || || || || || || X || X 

| EYEBROW_TEMPLATE || || || || || || || || || || || || X || X 

| EYELASH_TEMPLATE || || || || || || || || || || || || X || X 

| FEATHER_TEMPLATE || || || || || || || || || || || || || 

| SCALE_TEMPLATE || || || || X || || || || || X || || || || 

| NAIL_TEMPLATE || || || || || || || X || || X || || || || 

| CLAW_TEMPLATE || || || || || || || X || || X || || || || 

| TALON_TEMPLATE || || || || || || || X || || X || || || || 

| TOOTH_TEMPLATE || || || || || || || X || || X || || || || 

| IVORY_TEMPLATE || || || || || || || X || || X || || || || 

| EYE_TEMPLATE || || || || X || || X || X || || X || || || || 

| NERVE_TEMPLATE || || || || X || || X || || || X || || || || 

| BRAIN_TEMPLATE || || || || X || || X || X || || X || || || || 

| LUNG_TEMPLATE || || || || X || || X || X || || X || || || || 

| HEART_TEMPLATE || || || || X || || X || X || || X || || || || 

| LIVER_TEMPLATE || || || || X || || X || X || || X || || || || 

| GUT_TEMPLATE || || || || X || || X || X || || X || || || || 

| STOMACH_TEMPLATE || || || || X || || X || X || || X || || || || 

| PANCREAS_TEMPLATE || || || || X || || X || X || || X || || || || 

| SPLEEN_TEMPLATE || || || || X || || X || X || || X || || || || 

| KIDNEY_TEMPLATE || || || || X || || X || X || || X || || || || 

| FLAME_TEMPLATE || || || || || X || X || X || || X || || || || 

| CHITIN_TEMPLATE || || || || X || || || X || X || X || X || X || || 

| SPINE_TEMPLATE || || || || || || || X || || X || || || || 

| SPONGE_TEMPLATE || || || || X || || || || || X || || || || 

**style="font-size: 150%;"| TISSUE_TEMPLATE !! THICKENS_ON_ENERGY_STORAGE !! THICKENS_ON_STRENGTH !! ARTERIES !! SCARS !! MUSCULAR !! FUNCTIONAL !!  STRUCTURAL !! CONNECTIVE_TISSUE_ANCHOR !! CONNECTS !! SETTABLE !! SPLINTABLE !! COSMETIC !! STYLEABLE 

1. See also
- Material definition token

ru:Tissue definition token
