#!/usr/bin/env python3
"""Pre-flight a manifest's Lua before the rig spends an hour finding out.

Every `pre` / `every.do` / `on_arrival` entry that is not a `probe:` line is Lua that will be
sent over RPC. A syntax error there fails a replicate deep into a chain, usually unattended, so
each chunk is compiled with `luac -p` first. Also re-runs the safety audit that matters most on
this project: any write of `frequency = 0` is refused outright (addendum 54 — zeroing the last
underground vermin-rotter freezes DF unrecoverably; write 1, never 0).
Usage: manifest-lint.py experiments/*.json"""
import json, re, subprocess, sys, tempfile, os
FREQ_ZERO = re.compile(r"\.frequency\s*=\s*0(?!\d)")
bad = 0
for path in sys.argv[1:]:
    man = json.load(open(path))
    chunks = []
    for arm in man.get("arms", []):
        for m in arm.get("pre", []):
            chunks.append(("pre", arm["name"], m))
        for m in arm.get("every", {}).get("do", []):
            chunks.append(("every", arm["name"], m))
        for m in arm.get("on_arrival", []):
            chunks.append(("on_arrival", arm["name"], m))
    errs = []
    for kind, armname, m in chunks:
        if m.startswith("probe:"):
            continue
        if FREQ_ZERO.search(m):
            errs.append(f"  {armname}/{kind}: WRITES frequency = 0 — refused (addendum 54)")
        with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False) as fh:
            fh.write(m); tmp = fh.name
        r = subprocess.run(["luac", "-p", tmp], capture_output=True, text=True)
        os.unlink(tmp)
        if r.returncode != 0:
            errs.append(f"  {armname}/{kind}: {r.stderr.strip().splitlines()[0] if r.stderr.strip() else 'luac failed'}")
    tag = "FAIL" if errs else "ok"
    print(f"{tag:4} {man.get('id', path)}  {len(chunks)} chunk(s), {sum(a['replicates'] for a in man.get('arms', []))} replicate(s)")
    for e in errs:
        print(e)
    bad += len(errs)
sys.exit(1 if bad else 0)
