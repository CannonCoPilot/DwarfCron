#!/usr/bin/env python3
"""Realm table for v2 (EXTERNAL real-world knowledge; the DF raws carry no geography - wiki: placement is biome + random
epicenter; the extinct creatures' period class "currently has no effect on how or where they appear").

Sources:
- vanilla non-vermin: parsed from ../../Q9-realms.md "Non-vermin members" (the Q9 judgement calls are kept), plus the two
  descriptive rows (9 gibbons -> IND; ocean-only sharks/fish -> OCE).
- giants and animal people: inherit the realm of their root animal (census copy_from).
- extinct (new here): the best-known fossil locality mapped to the modern realm. Mesozoic and Paleozoic continents were
  arranged differently, so this is a labelling convenience, not biogeography. Marine extinct species are OCE.
- vermin: COS unless listed in VERMIN_REALM (the Q9 examples); Q9 counted realm-specific vermin but did not ship the list.
"""
import re
from pathlib import Path
HERE = Path(__file__).resolve().parent
REALMS = ['AUS', 'NZ', 'AFR', 'MAD', 'NEO', 'NEA', 'PAL', 'IND', 'ARC', 'ANT', 'OCE', 'COS', 'FANT']
REALM_NAME = {'AUS': 'Australasia', 'NZ': 'New Zealand', 'AFR': 'Afrotropics', 'MAD': 'Madagascar / Mascarenes',
              'NEO': 'Neotropics', 'NEA': 'Nearctic', 'PAL': 'Palearctic', 'IND': 'Indomalaya', 'ARC': 'Arctic',
              'ANT': 'Antarctic / southern ocean', 'OCE': 'Oceanic / pelagic', 'COS': 'Cosmopolitan', 'FANT': 'DF-invented'}

def _q9():
    txt = (HERE.parent.parent / 'Q9-realms.md').read_text()
    sec = txt.split('Non-vermin members:')[1].split('Vermin:')[0]
    R = {}
    for line in sec.splitlines():
        m = re.match(r'\| (\w+) \| (.*) \|$', line)
        if not m or m.group(1) == 'realm': continue
        R[m.group(1)] = [n.strip() for n in re.sub(r'\([^)]*\)', '', m.group(2)).split(',')]
    return R
Q9 = _q9()

EXTINCT = {  # fossil locality -> modern realm (external)
 'CAMBRIAN_HALLUCIGENIA': 'OCE', 'CAMBRIAN_HAIKOUICHTHYS': 'OCE', 'CAMBRIAN_OPABINIA': 'OCE', 'CAMBRIAN_ANOMALOCARIS': 'OCE',
 'CAMBRIAN_TRILOBITE': 'OCE', 'CAMBRIAN_WIWAXIA': 'OCE', 'CARBONIFEROUS_OESTOCEPHALUS': 'PAL,NEA',
 'CARBONIFEROUS_TULLIMONSTRUM': 'OCE,NEA', 'CARBONIFEROUS_ARTHROPLEURA': 'NEA,PAL', 'CARBONIFEROUS_MEGANEURA': 'PAL',
 'CENOZOIC_DEINOTHERIUM': 'AFR,PAL,IND', 'CENOZOIC_SMILODON': 'NEO,NEA', 'CENOZOIC_MAMMOTH_PYGMY': 'NEA',
 'CENOZOIC_MEGATHERIUM': 'NEO', 'CENOZOIC_THYLACINE': 'AUS', 'CENOZOIC_ANDREWSARCHUS': 'PAL', 'CENOZOIC_RHINOCEROS_WOOLLY': 'PAL,ARC',
 'CENOZOIC_MIOHIPPUS': 'NEA', 'CENOZOIC_GLYPTODON': 'NEO', 'CENOZOIC_MAMMOTH_WOOLLY': 'PAL,NEA,ARC', 'CENOZOIC_PARACERATHERIUM': 'PAL,IND',
 'CENOZOIC_DODO': 'MAD', 'CENOZOIC_KELENKEN': 'NEO', 'CENOZOIC_MOA': 'NZ', 'CENOZOIC_MEGALODON': 'OCE', 'CENOZOIC_MEGALANIA': 'AUS',
 'CENOZOIC_TITANOBOA': 'NEO', 'CENOZOIC_PLATYBELODON': 'PAL,AFR', 'CENOZOIC_ENTELODON': 'NEA,PAL', 'CENOZOIC_MEGACEROPS': 'NEA',
 'CRETACEOUS_AMMONITE': 'OCE', 'CRETACEOUS_ARCHELON': 'OCE', 'CRETACEOUS_VELOCIRAPTOR': 'PAL', 'CRETACEOUS_MONONYKUS': 'PAL',
 'CRETACEOUS_LINHENYKUS': 'PAL', 'CRETACEOUS_BUITRERAPTOR': 'NEO', 'CRETACEOUS_DEINONYCHUS': 'NEA', 'CRETACEOUS_UTAHRAPTOR': 'NEA',
 'CRETACEOUS_MOSASAURUS': 'OCE', 'CRETACEOUS_PARASAUROLOPHUS': 'NEA', 'CRETACEOUS_IGUANODON': 'PAL', 'CRETACEOUS_TRICERATOPS': 'NEA',
 'CRETACEOUS_KOSMOCERATOPS': 'NEA', 'CRETACEOUS_MICROCERATUS': 'PAL', 'CRETACEOUS_ANKYLOSAURUS': 'NEA',
 'CRETACEOUS_PACHYCEPHALOSAURUS': 'NEA', 'CRETACEOUS_QUETZALCOATLUS': 'NEA', 'CRETACEOUS_COLEPIOCEPHALE': 'NEA',
 'CRETACEOUS_TSINTAOSAURUS': 'PAL', 'CRETACEOUS_THERIZINOSAURUS': 'PAL', 'CRETACEOUS_SUZHOUSAURUS': 'PAL', 'CRETACEOUS_NOTHRONYCHUS': 'NEA',
 'CRETACEOUS_CARNOTAURUS': 'NEO', 'CRETACEOUS_SPINOSAURUS_AEGYPTIACUS': 'AFR', 'CRETACEOUS_TYRANNOSAURUS': 'NEA',
 'CRETACEOUS_AMARGASAURUS': 'NEO', 'CRETACEOUS_OVIRAPTOR': 'PAL', 'CRETACEOUS_SINOPTERUS': 'PAL', 'CRETACEOUS_SPINOSAURUS_MIRABILIS': 'AFR',
 'CRETACEOUS_HYPSILOPHODON': 'PAL', 'CRETACEOUS_NODOSAURUS': 'NEA', 'DEVONIAN_DUNKLEOSTEUS': 'OCE', 'DEVONIAN_TIKTAALIK': 'NEA,ARC',
 'DEVONIAN_HIBBERTOPTERUS_SCOULERI': 'PAL', 'DEVONIAN_HIBBERTOPTERUS_PEACHI': 'PAL', 'DEVONIAN_DREPANOPTERUS': 'PAL',
 'DEVONIAN_MIMETASTER': 'OCE', 'JURASSIC_ICHTHYOSAURUS': 'OCE', 'JURASSIC_TORVOSAURUS': 'NEA,PAL', 'JURASSIC_ARCHAEOPTERYX': 'PAL',
 'JURASSIC_PLESIOSAURUS': 'OCE', 'JURASSIC_STEGOSAURUS': 'NEA', 'JURASSIC_KENTROSAURUS': 'AFR', 'JURASSIC_PTERODACTYLUS': 'PAL',
 'JURASSIC_JEHOLOPTERUS': 'PAL', 'JURASSIC_DILOPHOSAURUS': 'NEA', 'JURASSIC_CERATOSAURUS': 'NEA', 'JURASSIC_EUROPASAURUS': 'PAL',
 'JURASSIC_BRACHIOSAURUS': 'NEA', 'JURASSIC_DIPLODOCUS': 'NEA', 'JURASSIC_BRONTOSAURUS': 'NEA', 'JURASSIC_ALLOSAURUS': 'NEA',
 'JURASSIC_AFROVENATOR': 'AFR', 'JURASSIC_RHAMPHORHYNCHUS': 'PAL', 'JURASSIC_OSTENOCARIS': 'OCE', 'ORDOVICIAN_AEGIROCASSIS': 'OCE',
 'PERMIAN_DIPLOCAULUS': 'NEA', 'PERMIAN_ERYOPS': 'NEA', 'PERMIAN_HELICOPRION': 'OCE', 'PERMIAN_DIMETRODON': 'NEA',
 'PERMIAN_DIADECTES': 'NEA', 'PERMIAN_ANTEOSAURUS': 'AFR', 'PERMIAN_LYSTROSAURUS': 'AFR,IND,ANT', 'SILURIAN_JAEKELOPTERUS': 'PAL',
 'TRIASSIC_GERROTHORAX': 'PAL', 'TRIASSIC_EORAPTOR': 'NEO', 'TRIASSIC_SHAROVIPTERYX': 'PAL', 'TRIASSIC_PSEPHODERMA': 'OCE',
 'TRIASSIC_PROCOMPSOGNATHUS': 'PAL', 'TRIASSIC_DREPANOSAURUS': 'PAL',
}
VERMIN_REALM = {  # Q9 examples of realm-specific vermin; everything else COS
 'BIRD_BLUEJAY': 'NEA', 'BIRD_CARDINAL': 'NEA', 'BIRD_GRACKLE': 'NEA', 'BIRD_ORIOLE': 'NEA,NEO', 'BIRD_RW_BLACKBIRD': 'NEA',
 'BIRD_BUSHTIT': 'NEA', 'CHIPMUNK': 'NEA', 'BIRD_COCKATIEL': 'AUS', 'BIRD_LORIKEET': 'AUS', 'GREEN_TREE_FROG': 'NEA,AUS',
 'FISH_LUNGFISH': 'AFR,AUS,NEO', 'BIRD_LOVEBIRD_PEACH-FACED': 'AFR', 'BIRD_LOVEBIRD_MASKED': 'AFR', 'BIRD_PARAKEET': 'IND,AFR',
}

def realm_of(s, S):
    if s.source == 'extinct':
        root = s.root if s.kind == 'animal_person' else s.id
        return tuple(EXTINCT.get(root, 'COS').split(','))
    root = s.root if s.kind in ('giant', 'animal_person') else s.id
    if root in VERMIN_REALM: return tuple(VERMIN_REALM[root].split(','))
    out = [k for k, v in Q9.items() if root in v]
    if root.startswith('GIBBON_'): out.append('IND')
    if not out:
        r = S.get(root)
        if r is not None and r.biomes and all(b.startswith('OCEAN') for b in r.biomes) and r.aquatic: out = ['OCE']
        elif r is not None and r.vermin: out = ['COS']
        elif r is not None and all(b.startswith('SUBTERRANEAN') for b in r.biomes): out = ['CAVE']
        else: out = ['COS']
    return tuple(dict.fromkeys(out))
