#!/usr/bin/env python3
"""Run roster.build over every embark x layer x season x 20 seeds for each config; write runs/<label>.jsonl and tables.md.
usage: run.py [label ...]   (default: all configs)
"""
import sys, json, itertools, statistics as st
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import replace
from roster import *   # noqa

OUT = HERE / 'runs'; OUT.mkdir(exist_ok=True)
SEEDS = range(1, 21)
B0 = Cfg()
FIX = replace(B0, cls='lp+1', E_large_max=3, B_small_extra=1, D='tag', weight='frequency', hv_mode='nogiant',
              hv_fallback=True, benign_filter=True, seed_linked=True, label='FIX')
CONFIGS = {
    'baseline': B0,
    'A_role': replace(B0, A='role', label='A_role'),
    'D_tag': replace(B0, D='tag', label='D_tag'),
    'D_size': replace(B0, D='size', label='D_size'),
    'F_lp_cluster': replace(B0, F='lp_cluster', label='F_lp_cluster'),
    'F_none': replace(B0, F='none', label='F_none'),
    'cls_tag+size': replace(B0, cls='tag+size', label='cls_tag+size'),
    'cav_depth': replace(B0, cav='depth', label='cav_depth'),
    'cav_score': replace(B0, cav='score', label='cav_score'),
    'weight_freq': replace(B0, weight='frequency', label='weight_freq'),
    'no_AP': replace(B0, ap=False, label='no_AP'),
    'hv_fallback': replace(B0, hv_fallback=True, label='hv_fallback'),
    'cls_lp+1': replace(B0, cls='lp+1', label='cls_lp+1'),
    'hv_nogiant': replace(B0, hv_mode='nogiant', label='hv_nogiant'),
    'E_large': replace(B0, E_large_max=3, label='E_large'),
    'B_plus_small': replace(B0, B_small_extra=1, label='B_plus_small'),
    'benign_filter': replace(B0, benign_filter=True, label='benign_filter'),
    'seed_linked': replace(B0, seed_linked=True, label='seed_linked'),
    'FIX_noseedlink': replace(FIX, seed_linked=False, label='FIX_noseedlink'),
    # minimal fix set (see results.md)
    'FIX': FIX,
    'FIX_keepB': replace(FIX, B_small_extra=0, label='FIX_keepB'),
    'FIX_keepE': replace(FIX, E_large_max=2, label='FIX_keepE'),
    'FIX_keepD': replace(FIX, D='tag_and_size', label='FIX_keepD'),
    'FIX_keepBenign': replace(FIX, benign_filter=False, label='FIX_keepBenign'),
    'FIX_uniform': replace(FIX, weight='uniform', hv_mode='abs', label='FIX_uniform'),
    'FIX_tag+size': replace(FIX, cls='tag+size', label='FIX_tag+size'),
    'FIX_ratio': replace(FIX, size='ratio', label='FIX_ratio'),
    'FIX2': replace(FIX, sentient_pred=False, label='FIX2'),
    'FIX2_ratio': replace(FIX, size='ratio', sentient_pred=False, label='FIX2_ratio'),
    'FIX3': replace(FIX, sentient_pred=False, peer=True, label='FIX3'),
    'FIX3_ratio': replace(FIX, size='ratio', sentient_pred=False, peer=True, label='FIX3_ratio'),
    'peer': replace(B0, peer=True, label='peer'),
    'sentient_prey_only': replace(B0, sentient_pred=False, label='sentient_prey_only'),
    'FIX_ratio_keepBenign': replace(FIX, size='ratio', benign_filter=False, label='FIX_ratio_keepBenign'),
}

def jobs():
    for b in EMBARKS:
        for l in SURFACE_LAYERS:
            for s in SEASONS:
                for sd in SEEDS: yield b, l, s, sd
    for l in UNDER_LAYERS:
        for s in SEASONS:
            for sd in SEEDS: yield 'UNDER', l, s, sd

def run(label):
    cfg = CONFIGS[label]
    rows = [build(b, l, s, sd, cfg) for b, l, s, sd in jobs()]
    with open(OUT / (label + '.jsonl'), 'w') as f:
        for r in rows: f.write(json.dumps(r) + '\n')
    return rows

if __name__ == '__main__':
    labels = sys.argv[1:] or list(CONFIGS)
    for lb in labels:
        rows = run(lb)
        print(lb, len(rows), 'rosters')
