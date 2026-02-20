# DF2014:Speech file

- Speech files** are text files that define sentences which can be spoken by people in adventure mode. They are found in the `data/speech` folder.

1. List of files

**File !! Uses !! Example

| | | seek out [CONTEXT:HIST_FIG:TRANS_NAME] at [CONTEXT:ABSTRACT_BUILDING:TRANS_NAME] over in [CONTEXT:SITE:TRANS_NAME]

| | | I have taken down [CONTEXT:NUMBER] [CONTEXT:RACE:NUMBERED_NAME] while stalking [CONTEXT:PLACE:TRANS_NAME].

| | | It is said that the [CONTEXT:ARCH_ELEMENT] of [CONTEXT:ABSTRACT_BUILDING:TRANS_NAME] [CONTEXT:JUSTIFICATION] [CONTEXT:DEF_SPHERE] for the glory of [CONTEXT:HIST_FIG:TRANS_NAME].

| | | I'm [CONTEXT:NUMBER]!

| | | I am a [CONTEXT:UNIT_NAME].

| | | This is my [CONTEXT:ORDINAL] year as a [CONTEXT:UNIT_NAME].

| | | Who dares to enter my house?  I curse you!

| | Used when boasting about killing a dwarf. See also Creature token#SPEECH.
| whose hammer shattered on the anvil of my power

| | Used when boasting about killing an elf. See also Creature token#SPEECH.
| whose fragile bones shattered before the power of my contempt

| | | [CONTEXT:HIST_FIG:PRO_SUB] is also my [CONTEXT:FAMILY_RELATIONSHIP]

| | | [CONTEXT:HIST_FIG:PRO_SUB] was also my [CONTEXT:FAMILY_RELATIONSHIP]

| | | I have [CONTEXT:INDEF_FAMILY_RELATIONSHIP] named [CONTEXT:HIST_FIG:TRANS_NAME]

| | | I had [CONTEXT:INDEF_FAMILY_RELATIONSHIP] named [CONTEXT:HIST_FIG:TRANS_NAME]

| | | my [CONTEXT:FAMILY_RELATIONSHIP] is named [CONTEXT:HIST_FIG:TRANS_NAME]

| | | my [CONTEXT:FAMILY_RELATIONSHIP] was named [CONTEXT:HIST_FIG:TRANS_NAME]

| | | who lies dead, now only an embarrassing memory

| | | upon arising in the mornings,

| | | always remember to

| | | speak the praises of [SPEAKER:HF_LINK:DEITY:RANDOM_DEF_SPHERE]

| | Used when greeting another person.
| Greetings. My name is [SPEAKER:TRANS_NAME].

| | Used when greeting a baby.
| A baby! How adorable!

| | Used when replying to another person's greeting.
| Ah, hello. I'm [SPEAKER:TRANS_NAME].

| | Used by NPCs when replying to the player character's greeting after becoming a hero.
| I am [SPEAKER:TRANS_NAME]. How can I be of service?

| | Used when replying to the greeting of a person who is of another race.
| Hello, [AUDIENCE:RACE]. I am [SPEAKER:TRANS_NAME].

| | Used when replying to the greeting of a person whose first name is unusual.
| You know, you don't meet many people with the name [AUDIENCE:FIRST_NAME]

| | Used for greetings by priests and faithful people.
| This servant of [SPEAKER:HF_LINK:DEITY:TRANS_NAME] greets you.

| | Used by guards when you ask them about their profession. See also soldier_profession.
| I am a guard.

| | | Don't start any trouble.

| | | It is I that felled [CONTEXT:HIST_FIG:TRANS_NAME] the [CONTEXT:HIST_FIG:RACE].

| | | I hunt great beasts in [CONTEXT:PLACE:TRANS_NAME].

| | | I have hunted great beasts in [CONTEXT:PLACE:TRANS_NAME] for [CONTEXT:NUMBER] of my years.

| | | can be thought of as the antithesis of

| | | can allow one to experience

| | | can bring one near to

| | | can remind one of

| | | can be thought of as a representation of

| | Used by minotaurs while hunting adventures in their lairs. See also Creature token#LAIR_HUNTER_SPEECH.
| I'll eat you whole!

| | | I seek fortune and glory by offering my skill at arms in [CONTEXT:PLACE:TRANS_NAME].

| | | I have sought fortune and glory by offering my skill at arms in [CONTEXT:PLACE:TRANS_NAME] for [CONTEXT:NUMBER] of my years.

| | Used by NPCs when you ask them about their family, but they don't have any.
| I have no family to speak of.

| | | In the past, I hunted great beasts.

| | | In the past, I sought fortune and glory by offering my skill at arms.

| | | I was once a [CONTEXT:UNIT_NAME].

| | | I was a [CONTEXT:UNIT_NAME] for [CONTEXT:NUMBER] of the years of my life.

| | | At one time, I was a scout.

| | | Once it was my calling to rescue lost children.

| | | I once sought great treasures.

| | | I once wandered the wilds.

| | Used to express positive feelings.
| wonderful!fantastic!very good

| | | seek out [CONTEXT:HIST_FIG:TRANS_NAME] here in [CONTEXT:SITE:TRANS_NAME] at [CONTEXT:ABSTRACT_BUILDING:TRANS_NAME]

| | | seek out [CONTEXT:HIST_FIG:TRANS_NAME] here in [CONTEXT:SITE:TRANS_NAME]

| (removed in 0.44.01)
| | It is my duty to scout the area around [CONTEXT:PLACE:TRANS_NAME].

| (removed in 0.44.01)
| | I have been scouting the area around [CONTEXT:PLACE:TRANS_NAME] for [CONTEXT:NUMBER] of my years.

| | | seek out [CONTEXT:HIST_FIG:TRANS_NAME] over in [CONTEXT:SITE:TRANS_NAME]

| | | banedeathnemesisvanquisher

| | | I rescue lost children and bring them back to [CONTEXT:PLACE:TRANS_NAME].

| | | For [CONTEXT:NUMBER] of my years, I have been rescuing lost children and bringing them back to [CONTEXT:PLACE:TRANS_NAME].

| | Used by soldiers when you ask them about their profession. See also guard_profession.
| I am a soldier.

| | | [CONTEXT:ANY:TRANS_NAME] might have a task for you

| | | your task is simple;all you need is to

| | | Welcome to [CONTEXT:ENTITY:TRANS_NAME].  Praise be to [CONTEXT:ENTITY:WORSHIP_HF:TRANS_NAME]!As a member of [CONTEXT:ENTITY:TRANS_NAME], you can now seek the higher mysteries of [CONTEXT:ENTITY:WORSHIP_HF:TRANS_NAME].

| | | I seek treasures and bring them back to [CONTEXT:PLACE:TRANS_NAME].

| | | I seek treasures and bring them back to [CONTEXT:PLACE:TRANS_NAME] and have done so for [CONTEXT:NUMBER] of the years of my life.

| | Used by NPC bandits before attacking you.
| Prepare to die!

| | | seek out [CONTEXT:HIST_FIG:TRANS_NAME], wherever [CONTEXT:HIST_FIG:PRO_SUB] might be

| | | I wander [CONTEXT:PLACE:TRANS_NAME].

| | | I have wandered [CONTEXT:PLACE:TRANS_NAME] for [CONTEXT:NUMBER] of my years.

1. Adding custom files

While any of the hardcoded speech files can be edited to customize the used phrases, it is also possible to add new files and associate them with custom creatures.

| + Creature tokens
**Token !! Example uses

| CASTE_SPEECH
| | LAIR_HUNTER_SPEECH
| minotaur (lair_hunter_minotaur.txt)

| SPEECH
| dwarf (dwarf.txt), elf (elf.txt)

| SPEECH_FEMALE
| | SPEECH_MALE
| 1. Special tokens

Speech files can contain tokens in square brackets (`[]`), which are replaced with context-specific strings before the speech is displayed.

1. Context tokens

These give special information about the background of the conversation.

**Token !! Type !! Meaning

| [CONTEXT:ABSTRACT_BUILDING]
| building
| - ab_specific_hf_seeker: the building in which the historical figure that the speaker wants you to seek is

| [CONTEXT:HIST_FIG]
| creature
| - ab_specific_hf_seeker: the historical figure the speaker wants you to seek

| [CONTEXT:NUMBER]
| number
| - animal_slayer: number of animals slain
- child_age_proclamation: age in years of the child

| [CONTEXT:ORDINAL]
| number
| - current_profession_year: the number of years the speaker has had their profession

| [CONTEXT:PLACE]
| site
| - animal_slayer: the place where the speaker slew the animals

| [CONTEXT:RACE]
| race
| - animal_slayer: the race of the animals the speaker has slain

| [CONTEXT:SITE]
| site
| - ab_specific_hf_seeker: the site where the historical figure the speaker wants you to seek is

| [CONTEXT:UNIT_NAME]
| text
| - current_profession_no_year: the name of the speaker's profession

Category:DF2014:Files
Category:DF2014:Modding
