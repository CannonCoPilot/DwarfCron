# DF2014:Weapon token

- Weapon tokens** define weapons. These tokens can only be placed within an ITEM_WEAPON object definition, and most do not function in armor objects.

1. Tokens

**Token
**Arguments
**Description

| | - singular
- plural
| Name of the weapon. <font color="red">Required.</font>

| | - adjective
| Adjective of the weapon, e.g. the "large" in "large copper dagger".

| / 
| - size
| Volume of weapon in mL or cubic cm. Defaults to 100.

| | - value
| The amount of force used when firing projectiles - velocity is presumably determined by the projectile's mass. Defaults to 0.

| | - value
| The maximum speed a fired projectile can have.

| | - Skill token
| The skill to determine effectiveness in melee with this weapon. Defaults to MACE.  AXE skill will allow it to be used to chop down trees. MINING skill will allow it to be used for mining. Outsider adventurers (or regular ones with no points in offensive skills) will receive a weapon with the SPEAR skill, selected at random if multiple ones have been modded in. All adventurers will also start with a weapon using the DAGGER skill, again selected at random if multiple such weapons exist.

| | - Skill token
- Ammo class
| Makes this a ranged weapon that uses the specified ammo. The specified skill determines accuracy in ranged combat.

| | - size
| Creatures under this size (in cm^3) must use the weapon two-handed. Defaults to 50000.

| | - size
| Minimum body size (in cm^3) to use the weapon at all (multigrasp required until TWO_HANDED value). Defaults to 40000.

| | | Allows the weapon to be made at a craftsdwarf's workshop from a sharp ([MAX_EDGE:10000] or higher) stone (i.e. obsidian) plus a wood log.

| | | Restricts this weapon to being made of wood.

| | - value
| Number of bar units needed for forging, as well as the amount gained from melting. <font color="red">Required.</font>

| | - Preparation time
- Recovery time
| Determines the length of time to prepare this attack and until one can perform this attack again.  Values appear to be calculated in adventure mode ticks.

| | | Multiple strikes with this attack cannot be performed effectively.

| | | Multiple strikes with this attack can be performed with no penalty.

| | - attacktype:BLUNT or EDGE
- contact_area:value
- penetration_size:value
- verb2nd:string
- verb3rd:string
- noun:string
- velocity_multiplier:value
| You can have many ATTACK tags and one will be randomly selected for each attack, with EDGE attacks 100 times more common than BLUNT attacks. Contact area is usually high for slashing and low for bludgeoning, piercing, and poking. Penetration value tends to be low for slashing and high for stabbing, and is ignored if attack is BLUNT. Verbs are for the 2nd and 3rd person action verbs used to describe the attack. Noun describes what part of the weapon is being used in the attack, or NO_SUB for none. Velocity_multiplier is a multiplier for the attack momentum, increasing effectiveness; stab attacks use 1000 while the lash of a whip uses 5000.  <font color="red">Required.</font>

ru:Weapon token
