# DF2014:Language token

- Language tokens** are used within the language_*.txt raw files. Each token is permitted in a specific context.

__TOC__

1. WORD

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | - singular
- plural
| Begins defining a noun usage of a word.

| | - adjective
| Begins defining an adjective usage of a word.

| | - prefix
| Begins defining a prefix usage of a word.

| | - present first person
- present third person
- preterite
- past participle
- present participle
| Defines a verb usage of a word.

| | number 1-7
| Determines what order the adjective being defined comes in when in a string of multiple adjectives.

| | | Lets the singular noun form of the word be used after "the" ("The X of Y", where X is the word with the tag).

| | | As above, but with plural ("The Xs of Y").

| | | Lets the singular noun form of the word be used as part of a compound noun after "the" ("The Z-X of Y").

| | | As above, but with plural ("The Z-Xs of Y").

| | | Lets the adjective form of the word be used as part of a compound noun after "the" ("The Z-X of Y").

| | | Lets the singular noun form of the word be used after "of" ("The Y of X").

| | | As above, but with plural ("The Y of Xs").

| | | Lets the singular noun form of the word be used at the front of a compound noun ("XY", as in surnames).

| | | As above, but with plural.

| | | Lets the singular noun form of the word be used at the rear of a compound noun ("YX", as in surnames).

| | | As above, but with plural.

| | | Lets the adjective form of the word be used at the front of a compound noun.

| | | As above, but at the rear instead.

| | | Allows the prefix form to be appended as a prefix to a compound noun.

| | | Allows the prefix form to be appended as a prefix to a compound noun following "the".

| | | Allows the verb to be used in a compound noun and for its participles to be used as adjectives.

1. SYMBOL

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | - WORD
| Specifies the given WORD (defined in #REDIRECT language_words.txt) as belonging to the symbol being defined. A given word can belong to multiple symbols.

1. TRANSLATION

**width="20%" | Token
**width="20%" | Arguments
**width="60%" | Description

| | - WORD
- translation
| Specifies a translation from a given WORD (defined in language_words.txt) into the language being defined.

1. English instead of dwarven language
You can hack the language files with this regular expression command:

    - <nowiki>:%s/T_WORD:\([A-Z_ -]*\):[^\]]*\]/T_WORD:\1:\L\1]/</nowiki>**

1. See also
40d:Language (has expanded explanations of parts of the language system, which seems to still be the same in this version)

ru:Language token
