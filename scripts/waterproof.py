#!/usr/bin/env python3
"""Flood-fill the water tiles dumped by waterdump.lua; report which map edges each connected body touches; render PNGs."""
import sys, collections
from PIL import Image, ImageDraw
fort, dump, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
W=H=Z=None; tiles={}
for line in open(dump):
    line=line.strip()
    if line.startswith('#dims'):
        W,H,Z=map(int,line.split()[1].split(',')); continue
    if not line or ',' not in line: continue
    for rec in line.split(';'):
        x,y,z,d,tt=map(int,rec.split(','))
        tiles[(x,y,z)]=(d,tt)
print(f"{fort}: map {W}x{H}x{Z}, water tiles {len(tiles)}")
def edges_of(x,y):
    e=set()
    if x==0: e.add('W')
    if x==W-1: e.add('E')
    if y==0: e.add('N')
    if y==H-1: e.add('S')
    return e
seen=set(); comps=[]
for t in tiles:
    if t in seen: continue
    comp=[]; q=collections.deque([t]); seen.add(t)
    while q:
        x,y,z=q.popleft(); comp.append((x,y,z))
        for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
            n=(x+dx,y+dy,z+dz)
            if n in tiles and n not in seen: seen.add(n); q.append(n)
    comps.append(comp)
comps.sort(key=len, reverse=True)
print("component | tiles | z range | deep(>=4) | edge tiles by side | edges touched")
for i,c in enumerate(comps[:12]):
    zs=[z for _,_,z in c]; deep=sum(1 for t in c if tiles[t][0]>=4)
    side=collections.Counter()
    for x,y,z in c:
        for e in edges_of(x,y): side[e]+=1
    verdict = "EDGE-TO-EDGE" if len(side)>=2 else ("one edge" if side else "landlocked")
    print(f"{i:9d} | {len(c):5d} | {min(zs)}..{max(zs)} | {deep:5d} | {dict(side)} | {verdict}")
# render: one top-down projection (max depth over z, colour by z band) + per-z PNGs for the main component's z range
S=4
img=Image.new('RGB',(W*S,H*S),(238,232,220)); dr=ImageDraw.Draw(img)
zmin=min(z for _,_,z in tiles); zmax=max(z for _,_,z in tiles)
top={}
for (x,y,z),(d,tt) in tiles.items():
    if (x,y) not in top or z>top[(x,y)][0]: top[(x,y)]=(z,d)
for (x,y),(z,d) in top.items():
    f=(z-zmin)/max(1,zmax-zmin)
    col=(int(20+40*f), int(60+120*f), int(140+100*f)) if d>=4 else (150,190,220)
    dr.rectangle([x*S,y*S,x*S+S-1,y*S+S-1], fill=col)
dr.rectangle([0,0,W*S-1,H*S-1], outline=(120,40,40), width=2)
img.save(f"{outdir}/{fort}-water-topdown.png")
print("wrote", f"{outdir}/{fort}-water-topdown.png", "z", zmin, "..", zmax)
for c in comps[:1]:
    zs=sorted(set(z for _,_,z in c))
    for z in zs[:6]:
        im=Image.new('RGB',(W*S,H*S),(238,232,220)); d2=ImageDraw.Draw(im)
        for (x,y,zz),(d,tt) in tiles.items():
            if zz==z: d2.rectangle([x*S,y*S,x*S+S-1,y*S+S-1], fill=(30,90,200) if d>=4 else (150,190,220))
        d2.rectangle([0,0,W*S-1,H*S-1], outline=(120,40,40), width=2)
        im.save(f"{outdir}/{fort}-water-z{z}.png")
    print("per-z pngs for", zs[:6])
