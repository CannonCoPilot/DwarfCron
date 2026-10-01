import re,sys,os,glob,json
files={'steam':sys.argv[1],'classic':sys.argv[2],'dfhack':sys.argv[3]}
pat=re.compile(rb'[\x20-\x7e]{4,}')
kw=re.compile(r'(?i)wave|mist|ocean|spray|foam|fog|liquid|water|underwater|surf|multilevel|flow_|glass_.*floor|brook|river_')
out={}
for k,p in files.items():
    b=open(p,'rb').read()
    s=set(m.group().decode() for m in pat.finditer(b))
    # utf16 too
    s16=set(m.group().decode('utf-16le') for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}',b))
    out[k]=sorted(x for x in s|s16 if kw.search(x))
json.dump(out,open(sys.argv[4],'w'),indent=0)
for k,v in out.items(): print(k,len(v))
