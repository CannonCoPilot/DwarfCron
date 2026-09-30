#!/usr/bin/env python3
"""apex.md + apex.tsv: every species the APEX rule admits (user rule 2), with BENIGN / sentient / curious-beast flags."""
import csv
from pathlib import Path
from collections import Counter
from species2 import load, boosted, GUILDS

S = load()
HERE = Path(__file__).resolve().parent
A = sorted([s for s in S.values() if s.apex], key=lambda s: (not boosted(s), s.source, s.kind, s.guild, -s.mass))
B = [s for s in A if boosted(s)]
N = [s for s in A if not boosted(s)]
cols = ['id', 'admitted_by', 'source', 'kind', 'guild', 'mass', 'lp', 'benign', 'sentient', 'curious_beast', 'savage', 'layer_hint',
        'biome_tokens', 'freq', 'realms', 'verb_unsafe_id']
def layer_hint(s):
    if s.cavern: return 'cavern %d-%d' % s.depth
    if 'SUBTERRANEAN_LAVA' in s.biomes: return 'magma'
    if s.flier: return 'flying'
    if s.aquatic: return 'ocean' if s.ocean else 'fresh water'
    if s.amphib: return 'land + water'
    return 'land'
with open(HERE / 'apex.tsv', 'w') as f:
    w = csv.writer(f, delimiter='\t'); w.writerow(cols)
    for s in A:
        w.writerow([s.id, s.apex_why, s.source, s.kind, s.guild, s.mass, int(s.lp), int(s.benign), int(s.sentient), int(s.cb),
                    int(s.savage), layer_hint(s), s.biome_tokens, s.freq, ','.join(s.realms), int(' ' in s.id or ',' in s.id)])

def flags(s):
    t = []
    if s.benign: t.append('**BENIGN**')
    if s.sentient: t.append('**sentient**')
    if s.cb: t.append('curious beast')
    if not s.lp: t.append('not LP')
    if ' ' in s.id or ',' in s.id: t.append('id has space/comma')
    return ', '.join(t)
P = ['# APEX boost: every species admitted (DF 53.16 vanilla + extinct, natural class)\n',
     'Rule (user rule 2): IF (guild in {AL apex hunter land, AW water apex, ML ground mesocarnivore, RP raptor} OR CARNIVORE) AND '
     '(giant variant OR adult body size >= 1,000,000 cm3) THEN apex, with or without LARGE_PREDATOR, with or without BENIGN.\n',
     'Readings (stated, not inferred from names):',
     '- CARNIVORE is read as CARNIVORE or BONECARN. Wiki: BONECARN "implies CARNIVORE"; the raws never write both.',
     '- ORCA, GIANT_ORCA and GIANT_CUTTLEFISH carry no diet token and are BENIGN. They enter only through the tool\'s curated predator '
     'override (SW:982). The literal rule would exclude ORCA, which the brief names as an intended case.',
     '- Giant = census kind `giant` (APPLY_CREATURE_VARIATION:GIANT) or an id starting GIANT_. Mass = the tool\'s adult mass (cm3).',
     '- Native apex = AL/AW (LARGE_PREDATOR) below the size/giant bar. They hold the apex slot without the boost.',
     '- BENIGN apex must have BENIGN cleared by the tool before DF acts on a written relation (T1: BENIGN on WOLF + write = 0 attacks; '
     'BENIGN off DEER = it attacked). Sentient apex may not attack by default (roster2 `sentient_attack=False`).',
     '- Every giant and every animal person is SAVAGE in the raws (wiki: SAVAGE creatures "only show up in savage biomes"). '
     'So the boosted giants exist only on savage embarks. 99 of 100 extinct species are also SAVAGE; CRETACEOUS_CARNOTAURUS is not.\n',
     '## Counts\n',
     '| group | boosted | of which BENIGN | of which sentient | curious beast |', '|---|---|---|---|---|']
for key, lab in ((('vanilla', 'giant'), 'vanilla giants'), (('vanilla', 'plain'), 'vanilla natural (non-giant)'),
                 (('vanilla', 'animal_person'), 'vanilla animal people'), (('extinct', 'plain'), 'extinct'),
                 (('extinct', 'animal_person'), 'extinct animal people')):
    X = [s for s in B if (s.source, s.kind) == key]
    P.append('| %s | %d | %d | %d | %d |' % (lab, len(X), sum(s.benign for s in X), sum(s.sentient for s in X), sum(s.cb for s in X)))
P.append('| **total** | **%d** | **%d** | **%d** | **%d** |\n' % (len(B), sum(s.benign for s in B), sum(s.sentient for s in B), sum(s.cb for s in B)))
P.append('Boosted by guild: ' + ', '.join('%s %d' % kv for kv in Counter(s.guild for s in B).most_common()) +
         '. Native apex (not boosted): %d (%d sentient, %d BENIGN).\n' % (len(N), sum(s.sentient for s in N), sum(s.benign for s in N)))
P.append('## BENIGN apex: the tool must clear BENIGN to arm them (%d)\n' % sum(s.benign for s in B))
P.append(', '.join('%s (%s, %.2fM)' % (s.id, s.guild, s.mass / 1e6) for s in B if s.benign) + '\n')
P.append('## Sentient apex: excluded as attackers by default (%d boosted + %d native)\n' % (sum(s.sentient for s in B), sum(s.sentient for s in N)))
P.append('Boosted: ' + ', '.join(s.id for s in B if s.sentient) + '\n')
P.append('Native: ' + ', '.join(s.id for s in N if s.sentient) + '\n')
P.append('## Full list: boosted apex (%d)\n' % len(B))
P.append('| id | admitted by | source / kind | guild | adult cm3 | layer | flags |')
P.append('|---|---|---|---|---|---|---|')
for s in B:
    P.append('| %s | %s | %s / %s | %s | %s | %s | %s |' % (s.id, s.apex_why, s.source, s.kind, s.guild, format(s.mass, ','), layer_hint(s), flags(s)))
P.append('\n## Native apex (LARGE_PREDATOR land/water, below the bar) (%d)\n' % len(N))
P.append('| id | source / kind | guild | adult cm3 | layer | flags |')
P.append('|---|---|---|---|---|---|')
for s in N:
    P.append('| %s | %s / %s | %s | %s | %s | %s |' % (s.id, s.source, s.kind, s.guild, format(s.mass, ','), layer_hint(s), flags(s)))
# near misses: big herbivores and big BENIGN non-carnivores are NOT apex; and carnivores just under the bar
P.append('\n## Not admitted, for the record\n')
big_prey = [s for s in S.values() if not s.vermin and s.mass >= 1_000_000 and not s.apex and s.kind == 'plain']
P.append('- Adult >= 1M cm3 but no predator guild and no diet token (%d, stay prey): ' % len(big_prey) +
         ', '.join(sorted(s.id for s in big_prey)) + '.')
near = sorted([s for s in S.values() if not s.vermin and not s.apex and (s.carn or s.bonecarn) and 300_000 <= s.mass < 1_000_000 and not s.giant],
              key=lambda s: -s.mass)
P.append('- Carnivores between 300k and 1M cm3, not LP, not giant (%d, stay meso): ' % len(near) + ', '.join('%s %dk' % (s.id, s.mass // 1000) for s in near) + '.')
(HERE / 'apex.md').write_text('\n'.join(P) + '\n')
print(len(A), len(B), len(N))
