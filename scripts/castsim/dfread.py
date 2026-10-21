"""castsim.dfread: DF's own reading of the creature raws, as seasonal-wildlife's engine reads them (V7.NR.recordOf), dumped
on the rig by `seasonal-wildlife cast nrrecords PATH` into data/castsim/foodweb/df_records.json.

User 20 Oct (rebuild plan rev 7, Phase D; the recommended option): the explorer and the desk take each creature's New Rules
fields from DF's reading, not from parsing the raw text -- DF compiles BONECARN into CARNIVORE and INTELLIGENT into
CAN_LEARN, defaults a missing PETVALUE to 1, gives copied variations their tokens, sizes vermin and expands broad biome
tokens its own way. The rig's probe found 12 fields where the two readings parted. The vermin types stay the rules file's
where it names them (SWV_OVERRIDE). DF_RECORDS=path reads another dump; no file, no overrides.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PATH = Path(os.environ.get('DF_RECORDS') or Path(__file__).resolve().parent.parent.parent / 'data/castsim/foodweb/df_records.json')
DOC = json.loads(PATH.read_text()) if PATH.exists() else {'records': {}}
RECORDS = DOC.get('records', {})
SOURCE = f"{PATH.name} (DFHack {DOC.get('dfhack', '?')}, rules {DOC.get('rules', '?')})" if RECORDS else None


def arr(x):
    """a Lua list as Python (an empty Lua table comes back as {})"""
    return x if isinstance(x, list) else (list(x.values()) if isinstance(x, dict) else [])


def rec(tok):
    return RECORDS.get(tok)


def classify_overrides(tok):
    """the desk's classify fields DF's reading sets, or {}"""
    r = RECORDS.get(tok)
    if not r: return {}
    return dict(habitat=r['h'], aquatic=r['h'] in ('aquatic', 'semiaquatic'), bodies=set(arr(r.get('wb'))), mass=r['m'],
                cmin=r.get('c0') or 0, cmax=r.get('c1') or 0, largePred=bool(r.get('lp')), carnivore=bool(r.get('carn')),
                benign=bool(r.get('bn')), giant=bool(r.get('gi')), sentient=bool(r.get('se')), guild=r['g'], role=r['ro'],
                ap=bool(r.get('ap')), apVermin=bool(r.get('apv')), civ=bool(r.get('civ')), root=r.get('rt'))
