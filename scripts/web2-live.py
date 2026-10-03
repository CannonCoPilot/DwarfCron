#!/usr/bin/env python3
"""web2-live.py -- the live run of the seasonal-wildlife web2 companion on the rig: does the page poll the game in real time?

One command, about 15 minutes:
    scripts/web2-live.py                         deploy the web2 web files, restore + load RinghatchetsReady, enable the tool,
                                                 start the server, unpause, poll every route at the page's own cadence for
                                                 --minutes (10), drive the page in headless Chrome (every tab at t0 and t0+5 min),
                                                 then stop, quit to the title WITHOUT saving and diff the save against its backup
    scripts/web2-live.py --dry-run               no rig: luac53, the plan, and the HTTP poll loop against tests/web/mock_server.py
Options: --tool-src DIR (default ~/Claude/Projects/sw-wt/web2/scripts), --deploy web|tree|none (default web: only
seasonal-wildlife-web.lua and .html, so the engine the RC chain deployed stays), --fort NAME, --no-restore, --minutes N,
--fps N (tick cap while it runs; default 100, never below 10), --gap S (browser t0 -> t1, default 300), --leave (keep the
server serving and the fort loaded afterwards for a person's browser pass).

Asserts (each a row in results.json, PASS / FAIL / NOT-TESTABLE):
  live.date_advances      the game date in /state.json moves while unpaused
  live.units_move         unit positions in /map.json change between reads; group counts change over the run
  live.seq_moves          /history.json seq and /events.json (ledger) count increase
  live.not_modified       /state.json answers 304 to If-None-Match during a paused window (nothing moved)
  live.budget.<route>     the server-side build ms (the route's own `ms`) under its budget for p95, and wall ms p95 under 1 s
  live.no_5xx             no 5xx and no connection failure on any route
  live.terrain            the terrain scan completes through /map.json and is not mostly '?'
  live.server_status      `seasonal-wildlife-web status`: poll worst, map worst, history sample worst, handler errors
  browser.*               the page in Chrome: no console error, the pill Live, the header stamped with the live build (no
                          offline banner), map markers moved between t0 and t1
Output: data/web2-live/<run>/ results.json, report.md, log.txt, screens/t0|t1/*.png, fixtures/ (one snapshot of every route,
for tests/web/mock_server.py FIXTURE=). Exit 0 when no row FAILs, 1 when one does, 2 when the run could not start.
Never sets fps to 0. One RPC at a time. Nothing is saved: the fort is restored from its .preverify backup and quit unsaved.
"""
import argparse, http.client, json, os, re, shutil, statistics, subprocess, sys, threading, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
LUAC = Path.home() / "Claude/Projects/sw-wt/.tools/luac53"
DF_DIR = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress"
SAVE_ROOT = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save"
BACKUPS = Path.home() / "Library/Application Support/CrossOver/df-snapshots/saves"
WPORT = 8642
# the page's own cadence (scripts/seasonal-wildlife-web.html FEEDS) and each route's server-side budget (ms)
FEEDS = {"state": 2.0, "map": 1.5, "events": 4.0, "history": 15.0, "web": 15.0, "waters": 5.0, "status": 5.0}
BUDGET = {"state": 50, "map": 50, "events": 50, "history": 50, "web": 50, "waters": 50, "status": 50}
OUT = ROOT / "data" / "web2-live" / RUN
results, LOG = [], None
TOKEN = ""
MODE = "live"

def log(m):
    line = f"{datetime.now().strftime('%H:%M:%S')} {m}"; print(line, flush=True)
    if LOG: LOG.write(line + "\n"); LOG.flush()
def rec(rid, verdict, ev, data=None):
    row = {"id": rid, "verdict": verdict, "evidence": str(ev)}
    if data is not None: row["data"] = data
    results.append(row); log(f"  [{verdict}] {rid}: {str(ev)[:240]}")
    return verdict == "PASS"
def sh(*a, timeout=180):
    if MODE != "live": return 0, "", ""
    try:
        p = subprocess.run([CX, *[str(x) for x in a]], capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=dict(os.environ, CX_RPC_TIMEOUT="45"))
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"

def req(path, q=None, headers=None, method="GET", timeout=20):
    """(code, headers, body bytes, wall ms); code 0 on a connection failure."""
    qs = "t=" + TOKEN + "".join(f"&{k}={v}" for k, v in (q or {}).items() if v is not None)
    t0 = time.time()
    try:
        c = http.client.HTTPConnection("127.0.0.1", WPORT, timeout=timeout)
        c.request(method, f"{path}?{qs}", headers={"Host": f"127.0.0.1:{WPORT}", **(headers or {})})
        r = c.getresponse(); b = r.read(); c.close()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, b, (time.time() - t0) * 1000
    except Exception as e:
        return 0, {}, str(e).encode(), (time.time() - t0) * 1000

class Poller:
    """The page's polling loop, from the host: each feed at its cadence, cursors and the ETag as the page keeps them."""
    def __init__(self):
        self.calls = {k: [] for k in FEEDS}; self.etag = None; self.hist_seq = 0; self.led = 0; self.tv = None; self.wv = None
        self.dates, self.positions, self.groups, self.hseqs, self.leds, self.fail = [], [], [], [], [], []
        self.terrain = None; self.last = {}
    def one(self, feed):
        q, hd = {}, {}
        path = {"state": "/state.json", "map": "/map.json", "events": "/events.json", "history": "/history.json", "web": "/web.json", "waters": "/waters.json", "status": "/status.json"}[feed]
        if feed == "state" and self.etag: hd["If-None-Match"] = self.etag
        if feed == "map": q = {"tv": self.tv, "wv": self.wv, "links": "1"}
        if feed == "events": q = {"since": self.led}
        if feed == "history": q = {"since": self.hist_seq}
        if feed == "status": q = {"s": "groupmap,groups"}
        code, h, b, ms = req(path, q, hd)
        j = None
        if code == 200:
            try: j = json.loads(b)
            except ValueError: code = -1
        self.calls[feed].append({"code": code, "wall": round(ms, 1), "srv": (j or {}).get("ms") if isinstance(j, dict) else None, "bytes": len(b), "t": time.time()})
        if code == 0 or code >= 500 or code == -1: self.fail.append((feed, code, b[:200].decode("utf-8", "replace")))
        if not j: return
        self.last[feed] = j
        if feed == "state":
            self.etag = h.get("etag"); self.dates.append((time.time(), (j.get("date") or {}).get("abs_day")))
        elif feed == "map":
            if j.get("terrain"): self.terrain = j["terrain"]
            self.tv = j.get("tv") if j.get("tdone") else None
            self.wv = j.get("wv") or self.wv
            L = j.get("live") or {}
            self.positions.append({u[0]: (u[1], u[2], u[3]) for u in L.get("units") or []})
            self.groups.append(len(L.get("groups") or []))
        elif feed == "events":
            self.led = max(self.led, j.get("count") or 0); self.leds.append(self.led)
        elif feed == "history":
            self.hist_seq = j.get("seq") or self.hist_seq; self.hseqs.append(self.hist_seq)
    def run(self, seconds, stop=None):
        nxt = {k: 0 for k in FEEDS}; end = time.time() + seconds
        while time.time() < end and not (stop and stop.is_set()):
            now = time.time()
            for f, every in FEEDS.items():
                if now >= nxt[f]: self.one(f); nxt[f] = now + every
            time.sleep(0.1)

def pct(xs, p):
    xs = sorted(x for x in xs if isinstance(x, (int, float)))
    return xs[min(len(xs) - 1, int(len(xs) * p))] if xs else None

def main():
    global MODE, TOKEN, LOG, WPORT
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool-src", default=str(Path.home() / "Claude/Projects/sw-wt/web2/scripts"))
    ap.add_argument("--deploy", choices=["web", "tree", "none"], default="web")
    ap.add_argument("--fort", default="RinghatchetsReady"); ap.add_argument("--no-restore", action="store_true")
    ap.add_argument("--minutes", type=float, default=10); ap.add_argument("--fps", type=int, default=100); ap.add_argument("--gap", type=int, default=300)
    ap.add_argument("--leave", action="store_true"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--mock-port", type=int, default=8790)
    a = ap.parse_args()
    if a.fps < 10: sys.exit("refusing --fps under 10 (0 freezes DF)")
    global OUT
    if a.dry_run:
        MODE = "dry"; OUT = OUT.with_name(RUN + "-dry")
        if a.minutes == 10: a.minutes = 1.5
        if a.gap == 300: a.gap = 30
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "fixtures").mkdir(exist_ok=True)
    LOG = open(OUT / "log.txt", "w")
    src = Path(a.tool_src); repo = src.parent
    log(f"web2-live {RUN}: mode {MODE}, tool {src} ({subprocess.run(['git', '-C', str(repo), 'log', '--oneline', '-1'], capture_output=True, text=True).stdout.strip()}), fort {a.fort}, {a.minutes} min, fps {a.fps}")
    # ---- static checks first (fail fast)
    bad = [f for f in ("seasonal-wildlife-web.lua", "seasonal-wildlife-controls.lua", "seasonal-wildlife.lua") if subprocess.run([str(LUAC), "-p", str(src / f)], capture_output=True).returncode]
    rec("build.luac53", "FAIL" if bad else "PASS", f"luac53 -p on the web, controls and engine scripts: {'failed ' + ', '.join(bad) if bad else 'OK'}")
    if bad: return finish(a, 2)
    mock = None
    if MODE == "dry":
        TOKEN, WPORT = "mock", a.mock_port
        mock = subprocess.Popen([sys.executable, str(repo / "tests/web/mock_server.py"), str(WPORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(240):
            if req("/")[0] == 200: break
            time.sleep(0.5)
        rec("session.server", "PASS", f"mock server on {WPORT} (dry run: the poll loop and the browser check run against the offline sim)")
    else:
        # ---- deploy
        dest = DF_DIR / "dfhack-config/scripts"
        if a.deploy == "tree":
            rc, out, err = sh("deploy-tool", src, timeout=120)
            rec("deploy", "PASS" if rc == 0 else "FAIL", (out + err).strip()[-300:])
            if rc: return finish(a, 2)
        elif a.deploy == "web":
            for f in ("seasonal-wildlife-web.lua", "seasonal-wildlife-web.html"): shutil.copy2(src / f, dest / f)
            same = all((src / f).read_bytes() == (dest / f).read_bytes() for f in ("seasonal-wildlife-web.lua", "seasonal-wildlife-web.html"))
            need = all((dest / f).exists() for f in ("seasonal-wildlife.lua", "seasonal-wildlife-controls.lua"))
            rec("deploy", "PASS" if same and need else "FAIL", f"web2 web files copied into {dest} (byte-identical {same}); engine and controls already deployed: {need}")
            if not (same and need): return finish(a, 2)
        # ---- the fort
        st = sh("state")[1]
        if not a.no_restore:
            if "map=true" in st: sh("title", timeout=200)
            sh("save-restore", f"{a.fort}.preverify", timeout=400); sh("load", a.fort, timeout=400)
            st = sh("state")[1]
        if not rec("session.load", "PASS" if "map=true" in st else "FAIL", st.strip()[:200]): return finish(a, 2)
        sh("popups"); sh("fps", a.fps, 10)
        rc, out, err = sh("cmd", "seasonal-wildlife", "enable", timeout=90); log(f"enable: {out.strip()[:120]}")
        sh("cmd", "seasonal-wildlife-web", "stop", timeout=60)          # a server left by an earlier run reloads the new script
        rc, out, err = sh("cmd", "seasonal-wildlife-web", "start", str(WPORT), timeout=90)
        m = re.search(r"\?t=([0-9a-f]+)", out); TOKEN = m.group(1) if m else ""
        if not rec("session.start", "PASS" if TOKEN else "FAIL", out.strip()[:240]): return finish(a, 2)
        build = sh("lua", "print(dfhack.getDFHackVersion(), dfhack.getDFVersion(), df.global.world.cur_savegame.save_dir)")[1].strip()
        rec("session.build", "PASS", f"fort {a.fort}; {build}; tool {src}", data={"fort": a.fort, "build": build})
        sh("unpause")
    # ---- the page in Chrome, in parallel with the poll loop
    browser = {}
    def drive():
        p = subprocess.run(["node", str(repo / "tests/web/live-browser.mjs"), f"http://127.0.0.1:{WPORT}/?t={TOKEN}", str(OUT / "screens"), "--gap", str(a.gap)],
                           capture_output=True, text=True, timeout=a.gap + 400)
        try: browser.update(json.loads(p.stdout.strip().splitlines()[-1]))
        except Exception: browser["driver"] = (p.stdout + p.stderr)[-600:]
    bt = threading.Thread(target=drive, daemon=True); bt.start()
    P = Poller()
    secs = a.minutes * 60
    log(f"== polling for {a.minutes} min at the page's cadence")
    P.run(secs * 0.55)
    # a paused window: nothing moves, so /state.json must answer 304
    n304_0 = sum(1 for c in P.calls["state"] if c["code"] == 304)
    if MODE == "live": sh("pause")
    P.run(20)
    n304 = sum(1 for c in P.calls["state"] if c["code"] == 304) - n304_0
    if MODE == "live": sh("popups"); sh("unpause")
    P.run(secs * 0.45 - 20)
    bt.join(timeout=a.gap + 420)
    # ---- verdicts
    ds = [d for _, d in P.dates if d is not None]
    rec("live.date_advances", "PASS" if len(ds) > 2 and ds[-1] > ds[0] else "FAIL", f"abs_day {ds[0] if ds else None} -> {ds[-1] if ds else None} over {len(ds)} state reads")
    moves = sum(1 for a_, b_ in zip(P.positions, P.positions[1:]) if any(b_.get(i) != p for i, p in a_.items() if i in b_))
    rec("live.units_move", "PASS" if moves >= max(1, len(P.positions) // 4) else "FAIL",
        f"{moves} of {max(0, len(P.positions) - 1)} consecutive map reads saw a unit move; groups on the map ranged {min(P.groups or [0])}-{max(P.groups or [0])}")
    rec("live.seq_moves", "PASS" if P.hseqs and P.hseqs[-1] > P.hseqs[0] and P.leds and P.leds[-1] >= P.leds[0] else "FAIL",
        f"history seq {P.hseqs[:1]} -> {P.hseqs[-1:]}; ledger count {P.leds[:1]} -> {P.leds[-1:]}")
    rec("live.not_modified", "PASS" if n304 > 0 else ("NOT-TESTABLE" if MODE != "live" else "FAIL"), f"{n304} 304 answer(s) to If-None-Match in the 20 s paused window")
    for f, cs in P.calls.items():
        srv = [c["srv"] for c in cs if c["code"] == 200 and isinstance(c["srv"], (int, float))]
        wall = [c["wall"] for c in cs if c["code"] in (200, 304)]
        s95, w95 = pct(srv[1:], 0.95), pct(wall[1:], 0.95)   # the first build is the cold one (pool, terrain start)
        ok = (s95 is None or s95 <= BUDGET[f]) and (w95 is None or w95 <= 1000)
        rec(f"live.budget.{f}", "PASS" if ok and cs else "FAIL",
            f"{len(cs)} reads; server ms p50 {pct(srv, .5)} p95 {s95} max {max(srv) if srv else None} (budget {BUDGET[f]}); wall ms p50 {pct(wall, .5)} p95 {w95} max {max(wall) if wall else None}; first {cs[0] if cs else None}")
    rec("live.no_5xx", "PASS" if not P.fail else "FAIL", f"{sum(len(c) for c in P.calls.values())} reads; failures {P.fail[:5]}")
    T = (P.terrain or {}).get("terrain") or P.terrain or {}
    cls = T.get("cls") or ""
    rec("live.terrain", "PASS" if T.get("done") and cls and cls.count("?") < len(cls) * 0.3 else "FAIL",
        f"done {T.get('done')}, {T.get('cw')}x{T.get('ch')} cells (stride {T.get('stride')}), z {T.get('zlo')}-{T.get('zhi')}, {T.get('reads')} reads in {T.get('ms')} ms; unknown cells {cls.count('?')} of {len(cls)}")
    b0, b1 = browser.get("t0") or {}, browser.get("t1") or {}
    rec("browser.errors", "PASS" if browser.get("ok") and not browser.get("errors") else "FAIL", f"console errors {browser.get('errors')}; {browser.get('driver', '')}")
    rec("browser.live", "PASS" if b1.get("conn") == "live" and not b1.get("mock") and (MODE != "live" or b1.get("dfhack")) else ("NOT-TESTABLE" if MODE != "live" else "FAIL"),
        f"pill at t1 '{b1.get('pill')}', fort {b1.get('fort')}, release {b1.get('release')}, DFHack {b1.get('dfhack')}, offline banner {b1.get('mock')}, 304s seen by the page {b1.get('notModified')}")
    rec("browser.moved", "PASS" if browser.get("moved", 0) > 0 and (b1.get("date") or 0) > (b0.get("date") or 0) else ("NOT-TESTABLE" if MODE != "live" else "FAIL"),
        f"{browser.get('moved')} of {browser.get('common')} markers moved between t0 and t1 ({a.gap} s); date {b0.get('date')} -> {b1.get('date')}; history seq {b0.get('histSeq')} -> {b1.get('histSeq')}")
    # ---- one snapshot of every route, for the mock (FIXTURE=)
    for name, path, q in (("state", "/state.json", {}), ("map", "/map.json", {"links": "1"}), ("history", "/history.json", {"since": 0}), ("events", "/events.json", {"since": 0}),
                          ("web", "/web.json", {}), ("waters", "/waters.json", {}), ("controls", "/controls.json", {}), ("status", "/status.json", {})):
        code, _, b, _ = req(path, q)
        if code == 200: (OUT / "fixtures" / f"{name}.json").write_bytes(b)
    if P.terrain: (OUT / "fixtures" / "terrain.json").write_text(json.dumps(P.terrain))
    if MODE == "live":
        rc, out, err = sh("cmd", "seasonal-wildlife-web", "status", timeout=60)
        m = re.search(r"errors (\d+)", out)
        rec("live.server_status", "PASS" if m and m.group(1) == "0" else "FAIL", out.strip()[:500])
    if mock: mock.terminate()
    return finish(a, 0)

def finish(a, code):
    if MODE == "live" and not a.leave and TOKEN:
        sh("cmd", "seasonal-wildlife-web", "stop", timeout=60); sh("pause"); sh("title", timeout=200)
        if not a.no_restore:
            d = subprocess.run(["diff", "-rq", str(SAVE_ROOT / a.fort), str(BACKUPS / f"{a.fort}.preverify")], capture_output=True, text=True)
            rec("end.save_diff", "PASS" if d.returncode == 0 else "FAIL", "IDENTICAL (nothing saved)" if d.returncode == 0 else d.stdout[:300])
    fails = [r for r in results if r["verdict"] == "FAIL"]
    json.dump({"run": RUN, "mode": MODE, "rows": results}, open(OUT / "results.json", "w"), indent=1)
    with open(OUT / "report.md", "w") as f:
        f.write(f"# web2 live run {RUN} ({MODE})\n\n{len(results) - len(fails)} PASS/NT, {len(fails)} FAIL\n\n| row | verdict | evidence |\n|---|---|---|\n")
        for r in results: f.write(f"| {r['id']} | {r['verdict']} | {r['evidence'].replace('|', '/')[:400]} |\n")
        f.write(f"\nScreens: screens/t0, screens/t1. Fixtures for `FIXTURE={OUT / 'fixtures'} python3 tests/web/mock_server.py`.\n")
    log(f"== {len(fails)} FAIL; {OUT}")
    return code if code else (1 if fails else 0)

if __name__ == "__main__":
    sys.exit(main())
