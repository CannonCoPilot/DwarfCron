#!/usr/bin/env python3
"""web-live.py -- an exhaustive live test of the seasonal-wildlife v7.1 browser companion as DF serves it.

The server is the tool's own DFHack Lua script (sw-wt/deploy scripts/seasonal-wildlife-web.lua, v7.1 web 2) on
http://127.0.0.1:8642/?t=<token>; CrossOver shares the Mac's loopback, so this driver reaches it with plain HTTP. Every
expectation below is derived from that source and its registry (scripts/seasonal-wildlife-controls.lua), not assumed.

Phases (each check is a row: id, PASS / FAIL / NOT-TESTABLE, evidence):
  session  restore RinghatchetsReady from .preverify and load it (--no-restore: the fort already loaded), fps cap 1000,
           start the server with its console verb (`seasonal-wildlife-web start 8642`) and read the token from its reply
  get      every GET route: /, /index.html, /state.json, /controls.json, /status.json (all and each section),
           /gfx/font and every sheet a species references; status codes, content types, JSON shape the page reads
  sec      token (missing, wrong, prefix), Host (foreign, no port, wrong port, none, localhost), POST-only writes, GET-only
           page, 404s, the /cmd verb whitelist, bad ids/tokens/arguments, response headers, LAN address not served
  ctl      EVERY control in /controls.json: an illegal value refused and the value unchanged; /set to another legal value
           (bool flip, number in range, other choice, seasons, token), the reply's value, the read back from /controls.json
           AND from the console (`seasonal-wildlife-controls get ID` run in the game, batched N per RPC, plus the config the
           engine loads); then /set back to the original and the same three read backs. Controls that share a verb or a
           config key never share a batch; a batch mismatch is re-tested alone before it is called a FAIL
  species  the 7 per-species rows (tok=TOKEN) on a species of the kind each applies to
  read     every /read readout; its output against the same verb run at the console
  cmd      /cmd with a sample of console verbs against `cx-lifecycle.sh cmd seasonal-wildlife ...`
  conc     N parallel GETs while the fort steps 1200 ticks (cx-lifecycle step, the only RPC in flight); then alive
  mal      malformed requests (garbage line, HTTP/2, lowercase method, HEAD, a 64 KB query, a 5000-digit value, idle and
           half-sent connections, a header flood that hides Host, a traversal in /gfx, binary bytes); alive after each
  act      EVERY /act action: safe passes first, then the drawing ones, then the destructive ones last, each followed by
           its effect check (irruption stir/now/end/cool on one reached cavern, stats reset, send-offs, roster build,
           All off, All on)
  end      `seasonal-wildlife-web status` (handler errors), stop, port closed, quit to the title WITHOUT saving, the save
           diffed against its .preverify backup, new stderr.log errors

Rules kept: one RPC at a time (every rig call is sequential; in `conc` the step is the only one); every HTTP call has
a timeout; four failed connections in a row stop the HTTP phases (fail fast); a wall-time budget (--budget-min) stops
the run and still runs `end`; fps is only ever set to 1000 (never 0).

Usage:
  web-live.py                           the whole run (about 20-30 min; --dry-run prints the estimate)
  web-live.py --no-restore              on the fort already loaded (no restore, no load); never saves
  web-live.py --phases get,sec,ctl      only these (session and end always run)
  web-live.py --browser                 leave the server serving and the fort loaded for the lead's Chrome pass
  web-live.py --dry-run                 no rig: the plan, and every control's value generation checked against the
                                        OFFLINE registry (lua tests/web/harness.lua <repo> registry)
  web-live.py --dry-run --mock          also start tests/web/mock_server.py on --mock-port (8790) and run the HTTP phases
                                        against it end to end (/set, /read, /act, /cmd); the console is offline there
Output: data/web-live/<run>/ results.json, report.md, log.txt, browser-checklist.md  (dry runs: <run>-dry, <run>-mock)
Exit: 0 when no row FAILs; 1 when any does; 2 when the run could not start (no fort, no server, no registry).
"""
import argparse, http.client, json, os, re, socket, struct, subprocess, sys, threading, time, traceback, urllib.parse
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
RPC = str(ROOT / "scripts" / "cx-rpc.py")
PY = str(ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else sys.executable
TOOL_REPO = Path.home() / "Claude/Projects/sw-wt/deploy"
RUN = datetime.now().strftime("%Y%m%d-%H%M%S")
FORT, BACKUP_TAG = "RinghatchetsReady", "preverify"
SAVE_ROOT = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save"
BACKUPS = Path.home() / "Library/Application Support/CrossOver/df-snapshots/saves"
DF_DIR = Path.home() / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress"
PHASES = ["get", "sec", "ctl", "species", "read", "cmd", "conc", "mal", "act"]
TABS = ["Status", "Species", "Food web", "Roster", "Groups", "Controls", "Ledger"]

MODE = "live"            # live | dry | mock
WPORT = 8642
TOKEN = ""
RPCPORT = "5555"
HTTP_TIMEOUT = 30.0
SET_TIMEOUT = 90.0       # a /set can re-apply the v7 raws or rebuild a pool inside DF's frame
OUT: Path = ROOT / "data" / "web-live" / RUN
results: list = []
memo: dict = {}
STATS = Counter()
_log = None
T0 = time.time()
DEADLINE = None

class ServerDown(Exception): pass
class OutOfTime(Exception): pass

# =============================================================================================== records
def log(msg):
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    if _log:
        _log.write(line + "\n"); _log.flush()

def rec(rid, verdict, evidence, phase=None, data=None, real_only=False):
    """One row. real_only: the expectation is the real server's; against the mock a FAIL is NOT-TESTABLE."""
    if MODE == "mock" and real_only and verdict == "FAIL":
        verdict, evidence = "NOT-TESTABLE", "(the mock server does not model this) " + str(evidence)
    row = {"id": rid, "phase": phase or memo.get("phase", "?"), "verdict": verdict, "evidence": str(evidence)}
    if data is not None:
        row["data"] = data
    results.append(row)
    if verdict != "PASS" or STATS["rows_logged"] < 4000:
        tag = {"PASS": "PASS", "FAIL": "FAIL", "NOT-TESTABLE": "N/T "}[verdict]
        log(f"  [{tag}] {rid}: {str(evidence)[:220]}")
    return verdict == "PASS"

def budget():
    if DEADLINE and time.time() > DEADLINE:
        raise OutOfTime(f"wall-time budget spent ({(time.time() - T0) / 60:.1f} min)")

def cut(s, n=160):
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s if len(s) <= n else s[:n] + "..."

# =============================================================================================== the rig
def sh(*args, timeout=180):
    """One cx-lifecycle verb: (rc, stdout, stderr)."""
    a = [str(x) for x in args]
    STATS["cx"] += 1
    if MODE != "live":
        return 0, "", ""
    env = dict(os.environ, CX_RPC_TIMEOUT="45")
    try:
        p = subprocess.run([CX, *a], capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env)
        return p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"(cx-lifecycle {' '.join(a[:3])} timed out after {timeout}s)"

def rpc_lua(code, timeout=60):
    STATS["rpc"] += 1
    if MODE != "live":
        return ""
    try:
        p = subprocess.run([PY, RPC, "--port", RPCPORT, "--timeout", str(timeout), "--lua", code],
                           capture_output=True, text=True, timeout=timeout + 30, cwd=ROOT)
        return (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return f"(lua timed out after {timeout}s)"

def luaj(code, timeout=60):
    """Lua that prints one json.encode'd value; parsed bracket to bracket. None when it did not come back."""
    out = rpc_lua("local json=require('json'); " + code, timeout=timeout)
    s = out.strip()
    try:
        return json.loads(s)
    except ValueError:
        pass
    starts = [k for k in (s.find("{"), s.find("[")) if k != -1]
    if not starts:
        memo["last_lua_error"] = s[:600]
        return None
    i = min(starts); j = s.rfind("}" if s[i] == "{" else "]")
    try:
        return json.loads(s[i:j + 1])
    except ValueError:
        memo["last_lua_error"] = s[:600]
        return None

def lua_str(s):
    return json.dumps(str(s))   # a JSON string literal is a valid Lua string literal for these ASCII ids

def console_gets(pairs):
    """`seasonal-wildlife-controls get ID [TOKEN]` for each (id, tok), run in the game in ONE RPC, plus the value the
    engine's loaded config holds (C.valueOf on sw.loadConfig()). Returns [{'get': str, 'cfg': value}] or None."""
    if MODE != "live":
        return None
    req = ",".join("{" + lua_str(i) + ("," + lua_str(t) if t else "") + "}" for i, t in pairs)
    code = ("local C=reqscript('seasonal-wildlife-controls'); local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); local out={}\n"
            f"for i,p in ipairs({{{req}}}) do\n"
            "  local a={'get',p[1]}; if p[2] then a[3]=p[2] end\n"
            "  local ok,o=pcall(dfhack.run_command_silent,'seasonal-wildlife-controls',table.unpack(a))\n"
            "  local r=C.find(p[1]); local pv=nil\n"
            "  if r then local ok2,v=pcall(C.valueOf,r,c,p[2]); if ok2 and v~=nil then pv=v end end\n"
            "  out[i]={get=ok and tostring(o) or ('ERR '..tostring(o)), cfg=pv}\n"
            "end\nprint(json.encode(out))")
    j = luaj(code, timeout=90)
    return j if isinstance(j, list) and len(j) == len(pairs) else None

def console_verbs(verbs, script="seasonal-wildlife"):
    """Each verb (a word list) through dfhack.run_command_silent in ONE RPC; [str] or None."""
    if MODE != "live":
        return None
    req = ",".join("{" + ",".join(lua_str(w) for w in v) + "}" for v in verbs)
    code = (f"local out={{}}\nfor i,a in ipairs({{{req}}}) do\n"
            f"  local ok,o=pcall(dfhack.run_command_silent,{lua_str(script)},table.unpack(a))\n"
            "  out[i]=ok and tostring(o) or ('LUA ERROR '..tostring(o))\nend\nprint(json.encode(out))")
    j = luaj(code, timeout=120)
    return j if isinstance(j, list) and len(j) == len(verbs) else None

# =============================================================================================== HTTP
class Resp:
    def __init__(self, code, ctype, body, headers, ms, err=None):
        self.code, self.ctype, self.body, self.headers, self.ms, self.err = code, ctype, body, headers, ms, err
    @property
    def text(self):
        return self.body.decode("utf-8", "replace") if isinstance(self.body, bytes) else str(self.body)
    def json(self):
        try:
            return json.loads(self.text)
        except ValueError:
            return None
    def short(self, n=120):
        return f"{self.code} {cut(self.err or self.text, n)}"

_fails_in_row = 0
def hreq(method, path, host=..., timeout=None, count=True):
    """One request with an explicit Host header (... = the right one, None = no Host at all)."""
    global _fails_in_row
    t0 = time.time()
    c = http.client.HTTPConnection("127.0.0.1", WPORT, timeout=timeout or HTTP_TIMEOUT)
    try:
        c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        h = f"127.0.0.1:{WPORT}" if host is ... else host
        if h is not None:
            c.putheader("Host", h)
        if method == "POST":
            c.putheader("Content-Length", "0")
        c.endheaders()
        r = c.getresponse()
        body = r.read()
        res = Resp(r.status, r.getheader("Content-Type") or "", body, {k.lower(): v for k, v in r.getheaders()}, int((time.time() - t0) * 1000))
        if count:
            _fails_in_row = 0
    except Exception as e:
        res = Resp(0, "", b"", {}, int((time.time() - t0) * 1000), err=f"{type(e).__name__}: {e}")
        if count:
            _fails_in_row += 1
            if _fails_in_row >= 4:
                raise ServerDown(f"four failed connections in a row; last: {res.err}")
    finally:
        c.close()
    STATS["http"] += 1
    return res

def tq(*pairs, **kw):
    """The query string with the token first; pairs for repeated keys (a=..)."""
    items = [("t", TOKEN)] + list(pairs) + [(k, v) for k, v in kw.items() if v is not None]
    return urllib.parse.urlencode(items)

def get(path, **kw):
    return hreq("GET", path + ("&" if "?" in path else "?") + tq(**kw))

def post(path, *pairs, timeout=None, **kw):
    return hreq("POST", path + "?" + tq(*pairs, **kw), timeout=timeout)

def raw(data: bytes, wait=3.0, linger=0.0, send=True):
    """A raw TCP exchange; returns (first line of the reply or the error, seconds)."""
    t0 = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(wait)
    try:
        s.connect(("127.0.0.1", WPORT))
        if send and data:
            s.sendall(data)
        if linger:
            time.sleep(linger)
        buf = b""
        try:
            while len(buf) < 4096:
                b = s.recv(4096)
                if not b:
                    break
                buf += b
        except socket.timeout:
            if not buf:
                return "(no reply before the client deadline)", time.time() - t0
        except ConnectionResetError:
            if not buf:
                return "(reset by the server)", time.time() - t0
        line = buf.split(b"\r\n", 1)[0].decode("latin-1") if buf else "(closed without a reply)"
        return line, time.time() - t0
    except Exception as e:
        return f"{type(e).__name__}: {e}", time.time() - t0
    finally:
        s.close()

def alive():
    r = hreq("GET", "/", count=False, timeout=15)
    return r.code == 200, r

# =============================================================================================== values
INVERT = {"extinct.skip.{T}"}                 # rowOut does not carry these flags; read from the registry source
BOOL3 = {"hunters.swim_scav_list.{T}"}
TEXT_ALLOW = {"irruption.species": {"auto"}}
TEXT_PATTERN = {"irruption.species": r"^[A-Z0-9_]+$"}
COUPLED = [{"limits.mode", "limits.fixed"}, {"water.enabled", "switch.water", "water.layer_mode", "switch.waterjob"},
           {"water.survey_ms", "water.survey_stride"}, {"curious.stay_min", "curious.stay_max"},
           {"scavenge.discover_min_h", "scavenge.discover_max_h", "scavenge.discover_small_h", "scavenge.discover_medium_h", "scavenge.discover_large_h"},
           {"irruption.warn_min_days", "irruption.warn_max_days"}, {"irruption.spacing_min_days", "irruption.spacing_max_days"},
           {"irruption.leave_min_days", "irruption.leave_max_days"}, {"irruption.size_min", "irruption.size_cap"},
           {"switch.land", "switch.water", "switch.cavern", "switch.deep"}]

def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def canon(v):
    if v is None or v == "-":
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if is_num(v):
        return float(v)
    s = str(v).strip()
    if s in ("true", "false"):
        return s
    try:
        f = float(s)
        if f == f and abs(f) != float("inf"):
            return f
    except ValueError:
        pass
    return s

def same(a, b):
    ca, cb = canon(a), canon(b)
    if isinstance(ca, float) and isinstance(cb, float):
        return abs(ca - cb) <= 1e-6 + 1e-12 * max(abs(ca), abs(cb))
    return ca == cb

def same_restore(r, a, b):
    """The original read back; an absent bool (None) restored as false counts, the store cannot hold 'absent'."""
    if same(a, b):
        return True
    if r.get("type") == "bool" and {canon(a), canon(b)} <= {None, "false"}:
        return True
    return False

def fnum(v, typ):
    if typ == "int" or (isinstance(v, float) and v.is_integer() and abs(v) < 1e15):
        return str(int(round(v)))
    return (f"{v:.6f}".rstrip("0").rstrip(".")) or "0"

def wire(r, v):
    """What the page sends for value v (the page's setControl)."""
    t = r["type"]
    if t == "bool":
        return "on" if v else "off"
    if t == "seasons":
        return "none" if v in ("", None) else str(v)
    if t in ("int", "float") and is_num(v):
        return fnum(v, t)
    return str(v)

def py_validate(r, raw_):
    """A port of seasonal-wildlife-controls validate(): (value, None) or (None, why)."""
    t = r["type"]
    if t == "bool":
        if raw_ in ("on", "true", "1"): return True, None
        if raw_ in ("off", "false", "0"): return False, None
        return None, "on or off"
    if t in ("int", "float"):
        if r.get("nilv") is not None and raw_ == r["nilv"]:
            return raw_, None
        try:
            n = float(raw_)
        except (TypeError, ValueError):
            return None, "a number"
        if n != n or abs(n) == float("inf") or str(raw_).strip().lower() in ("nan", "inf", "-inf", "infinity"):
            return None, "a number"
        if t == "int":
            if n != int(n): return None, "a whole number"
            n = int(n)
        else:
            n = round(n * 1e6) / 1e6
        if r.get("min") is not None and n < r["min"]: return None, f"at least {r['min']}"
        if r.get("max") is not None and n > r["max"]: return None, f"at most {r['max']}"
        return n, None
    if t == "enum":
        for o in r.get("opts") or []:
            if str(o) == str(raw_): return o, None
        return None, "one of " + ", ".join(map(str, r.get("opts") or []))
    if t == "seasons":
        s = str(raw_ or "")
        if s in ("", "none"): return "", None
        if len(s) > 8 or re.sub(r"Sp|Su|Au|Wi", "", s): return None, "season codes"
        return s, None
    if t == "text":
        s = str(raw_ or "")
        if s in TEXT_ALLOW.get(r["id"], set()): return s, None
        if not s or len(s) > 64 or not re.match(TEXT_PATTERN.get(r["id"], r"^[A-Za-z0-9_]+$"), s): return None, "a token"
        return s, None
    return None, "not settable"

def other(r, cur, default=None):
    """Another legal value: tests/web/harness.lua other(), ported."""
    t = r["type"]
    if t == "bool":
        return not (cur is True or canon(cur) == "true" or cur == "on")
    if t == "enum":
        for o in r.get("opts") or []:
            if str(o) != str(cur): return o
        return None
    if t in ("int", "float"):
        lo = r["min"] if r.get("min") is not None else 0
        hi = r["max"] if r.get("max") is not None else 100
        v = canon(cur)
        if not isinstance(v, float):
            v = canon(default)
        if not isinstance(v, float):
            v = float(lo)
        step = 1 if t == "int" else (r.get("step") or 0.1)
        nv = v + step
        if nv > hi: nv = v - step
        if nv < lo: nv = lo
        if t == "int": nv = int(nv // 1)
        else: nv = round(nv * 1e6) / 1e6
        return None if same(nv, cur) else nv
    if t == "seasons":
        return "Au" if cur == "SpWi" else "SpWi"
    if t == "text":
        return "TROGLODYTE" if cur == "auto" else "auto"
    return None

def illegal(r):
    """One value the server must refuse for this row, and the reason it should give."""
    t = r["type"]
    if t == "bool": return "maybe", "on or off"
    if t in ("int", "float"):
        if r.get("max") is not None:
            return fnum(r["max"] + (1 if t == "int" else max(r.get("step") or 0.1, 1)), t), "at most"
        return fnum((r.get("min") or 0) - 1, t), "at least"
    if t == "enum": return "zz_not_a_choice", "one of"
    if t == "seasons": return "Xx", "season codes"
    if t == "text": return "not-a-token", "a token"
    return "?", ""

EXTRA_ILLEGAL = {   # per type, on the first row of that type: (value, the refusal it should give)
    "bool": [("", "on or off"), ("yes", "on or off")],
    "int": [("2.5", "a whole number"), ("abc", "a number"), ("1e999", "a number")],
    "float": [("nan", "a number"), ("inf", "a number"), ("1e999", "a number"), ("", "a number")],
    "enum": [("", "one of")],
    "seasons": [("SpSuAuWiSp", "season codes"), ("spring", "season codes")],
    "text": [("", "a token"), ("A" * 65, "a token"), ("lower_case", "a token")],
}

def display_raw(rid, row, raw_):
    """controls.json maps hold the stored value; the row shows valueOf() of it."""
    if raw_ is None:
        if row.get("nilv") is not None: return row["nilv"]
        if row["type"] == "bool" and rid in INVERT: return True
        return None
    if rid in BOOL3:
        if isinstance(raw_, str): return raw_
        return "on" if raw_ else "off"
    if rid in INVERT and isinstance(raw_, bool): return not raw_
    return raw_

def conflict_keys(r):
    ks = set()
    if r.get("path"): ks.add("p:" + r["path"])
    v = r.get("verb") or ""
    if v == "by choice": ks.add("SOLO")
    elif v and v != "config only":
        ks.add("v:" + " ".join(w for w in v.split() if w != "$" and not w.startswith("@")))
    for grp in COUPLED:
        if r["id"] in grp: ks.add("c:" + min(grp))
    return ks

def make_batches(rows, size):
    batches, cur, keys = [], [], set()
    for r in rows:
        k = conflict_keys(r)
        solo = "SOLO" in k
        if cur and (len(cur) >= size or solo or "SOLO" in keys or (k & keys)):
            batches.append(cur); cur, keys = [], set()
        cur.append(r); keys |= k
    if cur:
        batches.append(cur)
    return batches

def plan_control(r, cur):
    new = other(r, cur, r.get("default"))
    bad, why = illegal(r)
    p = {"id": r["id"], "type": r["type"], "orig": cur, "new": new, "new_wire": None if new is None else wire(r, new),
         "orig_wire": None if cur is None and r["type"] != "bool" else wire(r, cur if cur is not None else False),
         "bad": bad, "bad_why": why, "problems": []}
    if not r.get("available", True):
        p["problems"].append("unavailable")
        return p
    if new is None:
        p["problems"].append("no other legal value")
    else:
        v, w = py_validate(r, p["new_wire"])
        if v is None: p["problems"].append(f"new value {p['new_wire']!r} fails validate: {w}")
        elif same(v, cur): p["problems"].append(f"new value {p['new_wire']!r} equals the current {cur!r}")
    if p["orig_wire"] is not None and cur is not None:
        v, w = py_validate(r, p["orig_wire"])
        if v is None: p["problems"].append(f"restore value {p['orig_wire']!r} fails validate: {w}")
    v, w = py_validate(r, bad)
    if v is not None: p["problems"].append(f"illegal value {bad!r} passes validate")
    return p

# =============================================================================================== registry sources
def offline_registry():
    p = subprocess.run(["lua", str(TOOL_REPO / "tests/web/harness.lua"), str(TOOL_REPO), "registry"], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise RuntimeError("harness registry failed: " + p.stderr[-400:])
    return json.loads(p.stdout)

def ctl_json():
    r = get("/controls.json")
    j = r.json() if r.code == 200 else None
    if not isinstance(j, dict):
        raise RuntimeError(f"/controls.json did not come back: {r.short()}")
    memo["ctl"] = j
    return j

def values_of(j):
    return {c["id"]: c.get("value") for c in j.get("controls") or []}

def state_json():
    r = get("/state.json")
    j = r.json() if r.code == 200 else None
    return j if isinstance(j, dict) else {}

def status_json(sections=None):
    r = get("/status.json", s=sections)
    j = r.json() if r.code == 200 else None
    return j if isinstance(j, dict) else {}

def status_lines(sec):
    return (status_json(sec).get("sections") or {}).get(sec, {}).get("lines") or []

# =============================================================================================== session
def phase_session(a):
    global TOKEN, RPCPORT
    memo["phase"] = "session"
    if MODE == "mock":
        TOKEN = "mock"
        ok, r = alive()
        rec("session.server", "PASS" if ok else "FAIL", f"mock server on 127.0.0.1:{WPORT}: GET / {r.short(60)}")
        return ok
    if MODE == "dry":
        TOKEN = "0" * 20
        return True
    p = sh("port")[1].strip()
    if p.isdigit():
        RPCPORT = p
    logf = DF_DIR / "stderr.log"
    memo["stderr0"] = logf.stat().st_size if logf.exists() else None
    st = sh("state")[1]
    if a.no_restore:
        if "map=true" not in st:
            rec("session.load", "FAIL", f"--no-restore, but no map is loaded: {cut(st)}"); return False
        rec("session.load", "PASS", f"--no-restore: the fort already loaded ({cut(st, 120)})")
    else:
        log(f"== restore {FORT}.{BACKUP_TAG} and load")
        if "map=true" in st:
            sh("title", timeout=200)
        rc, out, err = sh("save-restore", f"{FORT}.{BACKUP_TAG}", timeout=400)
        rc2, out2, err2 = sh("load", FORT, timeout=400)
        st = sh("state")[1]
        ok = "map=true" in st
        rec("session.load", "PASS" if ok else "FAIL", f"restore: {cut((out + err).strip().splitlines()[-1:] or '', 100)}; load: {cut((out2 + err2)[-160:], 160)}; state: {cut(st, 120)}")
        if not ok:
            return False
    sh("popups"); sh("fps", 1000, 10)
    memo["started_at_state"] = st
    rc, out, err = sh("cmd", "seasonal-wildlife-web", "start", str(WPORT), timeout=90)
    memo["web_start"] = out.strip()
    m = re.search(r"\?t=([0-9a-f]+)", out)
    TOKEN = m.group(1) if m else ""
    time.sleep(1.0)
    ok, r = alive()
    rec("session.start", "PASS" if TOKEN and ok and re.search(r"serving the companion at http://127\.0\.0\.1:%d/\?t=[0-9a-f]{20}|already serving" % WPORT, out) else "FAIL",
        f"`seasonal-wildlife-web start {WPORT}` -> '{cut(out, 200)}'; token {'read (' + str(len(TOKEN)) + ' hex)' if TOKEN else 'NOT FOUND'}; GET / {r.short(40)}")
    return bool(TOKEN) and ok

def phase_end(a):
    memo["phase"] = "end"
    if MODE != "live":
        return
    rc, out, err = sh("cmd", "seasonal-wildlife-web", "status", timeout=60)
    m = re.search(r"requests (\d+) \(commands (\d+), sets (\d+), refused (\d+), errors (\d+)[),]", out)
    errs = int(m.group(5)) if m else None
    e0 = memo.get("web_errors0")
    le = re.search(r"last error: (.*)$", out.strip())
    grew = errs is not None and e0 is not None and errs > e0
    rec("end.server_errors", "FAIL" if (errs is None or grew) else "PASS",
        f"`seasonal-wildlife-web status`: {cut(out, 260)}; handler errors {e0} at the start of the run -> {errs}" + (f"; last error: {le.group(1)[:200]}" if le else ""))
    if a.browser:
        rec("end.browser", "NOT-TESTABLE", "--browser: the server is left serving and the fort loaded for the Chrome pass; stop, title and the save diff are the lead's (see browser-checklist.md)")
        return
    rc, out, err = sh("cmd", "seasonal-wildlife-web", "stop", timeout=60)
    time.sleep(1.0)
    r = hreq("GET", "/", count=False, timeout=5)
    rec("end.stop", "PASS" if "stopped" in out and r.code == 0 else "FAIL", f"`seasonal-wildlife-web stop` -> '{cut(out, 60)}'; GET / afterwards: {r.short(60)} (expected: no connection)")
    log("== quit to the title without saving")
    sh("title", timeout=200)
    st = sh("state")[1]
    if a.no_restore:
        rec("end.save_diff", "NOT-TESTABLE", f"--no-restore: no backup was restored, so the save is not compared; state after title: {cut(st, 100)}")
    else:
        d = subprocess.run(["diff", "-rq", str(SAVE_ROOT / FORT), str(BACKUPS / f"{FORT}.{BACKUP_TAG}")], capture_output=True, text=True)
        rec("end.save_diff", "PASS" if d.returncode == 0 else "FAIL", f"{FORT} vs {FORT}.{BACKUP_TAG}: " + ("IDENTICAL (nothing saved)" if d.returncode == 0 else "DIFFERS: " + cut(d.stdout, 300)))
    logf = DF_DIR / "stderr.log"
    s0 = memo.get("stderr0")
    if s0 is not None and logf.exists():
        with open(logf, "rb") as f:
            f.seek(s0); new = f.read().decode("utf-8", "replace")
        bad = [l for l in new.splitlines() if re.search(r"seasonal-wildlife", l) and re.search(r"error|traceback|attempt to", l, re.I)]
        rec("end.stderr", "PASS" if not bad else "FAIL", f"{len(new.splitlines())} new stderr.log lines; tool errors: {len(bad)}" + (f"; first: {cut(bad[0], 200)}" if bad else ""))

# =============================================================================================== get
STATE_KEYS = {"tool": str, "web": int, "loaded": bool, "release": str, "cfg_ver": int, "fort": str, "date": dict, "enabled": bool,
              "hunting": bool, "fuse": str, "budget": (int, float), "undo_depth": int, "limits": dict, "wild": dict, "species": list,
              "pairs": list, "live": list, "jobs": list, "ledger": list, "gfx": dict, "ms": (int, float)}
DATE_KEYS = ["year", "season", "season_name", "day_of_season", "days_to_next", "day_of_month", "month", "abs_day"]
SPECIES_KEYS = ["key", "token", "name", "layer", "habitat", "role", "band", "active", "seasons", "stock", "freq", "gmin", "gmax", "on_map", "why"]
LIMIT_KEYS = ["groups", "ceiling", "wild", "groups_now", "pattern", "on"]
CTL_KEYS = ["rev", "cfg_ver", "sections", "controls", "species", "actions", "readouts", "maps"]
STATUS_IDS = ["jobs", "groups", "roster", "ecology", "water", "scavenging", "vermin", "extinct", "v7", "irruption"]

def png_dims(b):
    if len(b) < 24 or b[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", b[16:24])

def phase_get(a):
    page = hreq("GET", "/")
    body = page.text
    tabs = [t for t in TABS if t in body]
    fetches = [p for p in ("/state.json", "/controls.json", "/status.json", "/cmd", "/set", "/act", "/read") if p in body]
    rec("get.index", "PASS" if page.code == 200 and page.ctype.startswith("text/html") and "seasonal-wildlife" in body and len(tabs) == len(TABS) and len(fetches) == 7 else "FAIL",
        f"GET / {page.code} {page.ctype}, {len(page.body)} bytes; tabs {tabs}; endpoints the page calls {fetches}")
    idx = hreq("GET", "/index.html")
    rec("get.index_html", "PASS" if idx.code == 200 and idx.body == page.body else "FAIL", f"GET /index.html {idx.code}, {len(idx.body)} bytes, identical to /: {idx.body == page.body}")
    rec("get.headers", "PASS" if page.headers.get("x-content-type-options") == "nosniff" and page.headers.get("referrer-policy") == "no-referrer"
        and page.headers.get("cache-control") == "no-store" and page.headers.get("connection", "").lower() == "close" else "FAIL",
        f"X-Content-Type-Options {page.headers.get('x-content-type-options')}, Referrer-Policy {page.headers.get('referrer-policy')}, "
        f"Cache-Control {page.headers.get('cache-control')}, Connection {page.headers.get('connection')}", real_only=True)
    # state.json
    r = get("/state.json")
    st = r.json() or {}
    memo["state"] = st
    missing = [k for k, t in STATE_KEYS.items() if not isinstance(st.get(k), t)]
    dmiss = [k for k in DATE_KEYS if k not in (st.get("date") or {})]
    sp = st.get("species") or []
    smiss = sorted({k for s in sp for k in SPECIES_KEYS if k not in s})
    lim = st.get("limits") or {}
    lmiss = [f"{l}.{k}" for l in ("land", "water", "cavern") for k in LIMIT_KEYS if k not in (lim.get(l) or {})] + [k for k in ("mode",) if k not in lim]
    ok = r.code == 200 and r.ctype.startswith("application/json") and st.get("loaded") is True and sp and not (missing or dmiss or smiss or lmiss)
    rec("get.state", "PASS" if ok else "FAIL",
        f"{r.code} {r.ctype} {len(r.body)} bytes in {r.ms} ms; loaded {st.get('loaded')}, release {st.get('release')}, web {st.get('web')}, fort '{st.get('fort')}', "
        f"{len(sp)} species, {len(st.get('pairs') or [])} pairs, {len(st.get('live') or [])} live; missing/mistyped keys {missing}, date {dmiss}, species fields {smiss}, limits {lmiss}",
        real_only=bool(missing and set(missing) <= {"gfx", "release", "cfg_ver", "fuse", "jobs", "ledger", "ms", "budget"}))
    nv = [s for s in sp if s.get("role") != "vermin"]
    w2 = sorted({k for s in nv for k in ("guild", "slot", "level", "tier", "part") if k not in s})
    rec("get.state_web2", "PASS" if nv and not w2 and all("lk" in g for g in st.get("live") or [] if g.get("tracked")) else "FAIL",
        f"web-2 species fields on {len(nv)} non-vermin species: missing {w2}; tracked live groups carry lk: {all('lk' in g for g in st.get('live') or [] if g.get('tracked'))}")
    r2 = get("/state.json")
    rec("get.state_cached", "PASS" if r2.code == 200 and (r2.body == r.body or r2.ms <= max(250, r.ms)) else "FAIL",
        f"a second read within the 2 s TTL: {r2.code} in {r2.ms} ms (first {r.ms} ms), identical bytes {r2.body == r.body}", real_only=True)
    # controls.json
    r = get("/controls.json")
    c = r.json() or {}
    memo["ctl"] = c
    cm = [k for k in CTL_KEYS if k not in c]
    rows = c.get("controls") or []
    novalue = [x["id"] for x in rows if x.get("available") and "value" not in x]
    unav = [x["id"] for x in rows if not x.get("available")]
    secs = c.get("sections") or []
    sec_ids = {s["id"] for s in secs}
    orphan = [x["id"] for x in rows if x.get("sec") not in sec_ids]
    ok = (r.code == 200 and r.ctype.startswith("application/json") and not cm and len(secs) == 12 and len(rows) >= 350 and not novalue
          and len(c.get("species") or []) == 7 and len(c.get("actions") or []) >= 21 and len(c.get("readouts") or []) >= 27 and not orphan)
    rec("get.controls", "PASS" if ok else "FAIL",
        f"{r.code} {r.ctype} {len(r.body)} bytes in {r.ms} ms; sections {len(secs)}, controls {len(rows)} ({len(unav)} unavailable{': ' + ','.join(unav[:5]) if unav else ''}), "
        f"species rows {len(c.get('species') or [])}, actions {len(c.get('actions') or [])}, readouts {len(c.get('readouts') or [])}; missing keys {cm}; "
        f"available rows without a value {novalue[:8]}; rows in no section {orphan[:5]}")
    rec("get.controls_ver", "PASS" if c.get("cfg_ver") == st.get("cfg_ver") else "FAIL", f"controls.json cfg_ver {c.get('cfg_ver')} == state.json cfg_ver {st.get('cfg_ver')}", real_only=True)
    # status.json
    r = get("/status.json")
    s = r.json() or {}
    sec = s.get("sections") or {}
    want = STATUS_IDS + ["groupmap"]
    miss = [x for x in want if x not in sec]
    errs = {k: v.get("error") for k, v in sec.items() if isinstance(v, dict) and v.get("error")}
    gm = (sec.get("groupmap") or {}).get("layers") or []
    rec("get.status_all", "PASS" if r.code == 200 and r.ctype.startswith("application/json") and not miss and not errs and gm and gm[0].get("key") == "land" else "FAIL",
        f"{r.code} {len(r.body)} bytes in {r.ms} ms ({s.get('ms')} ms in DF); sections {sorted(sec)}; missing {miss}; errors {errs}; groupmap layers "
        f"{[x.get('key') for x in gm][:8]}", real_only=not miss and (bool(errs) or not gm or gm[0].get("key") != "land"))
    for sid in want:
        budget()
        r = get("/status.json", s=sid)
        j = r.json() or {}
        ss = j.get("sections") or {}
        v = ss.get(sid) or {}
        ok = r.code == 200 and list(ss) == [sid] and not v.get("error") and (isinstance(v.get("lines"), list) or isinstance(v.get("layers"), list))
        n = len(v.get("lines") or v.get("layers") or [])
        rec(f"get.status.{sid}", "PASS" if ok else "FAIL", f"{r.code} in {r.ms} ms; only {sid}: {list(ss) == [sid]}; {n} {'layers' if sid == 'groupmap' else 'lines'}; "
            f"error {v.get('error')!r}; first: {cut((v.get('lines') or [''])[0], 120)}", real_only=bool(v.get("error")))
    r = get("/status.json", s="nosuch")
    v = ((r.json() or {}).get("sections") or {}).get("nosuch") or {}
    rec("get.status_unknown", "PASS" if r.code == 200 and v.get("error") == "no such section" else "FAIL", f"?s=nosuch -> {r.code} {cut(r.text, 100)}")
    # gfx
    gx = st.get("gfx") or {}
    pages = gx.get("pages") or {}
    r = get("/gfx/font")
    d = png_dims(r.body)
    font = gx.get("font") or {}
    rec("get.gfx_font", "PASS" if r.code == 200 and r.ctype == "image/png" and d and font.get("url") == "/gfx/font" and d[0] // 16 == font.get("gw") and d[1] // 16 == font.get("gh")
        and r.headers.get("cache-control") == "private, max-age=86400" and len(gx.get("palette") or []) == 16 else "FAIL",
        f"{r.code} {r.ctype} {len(r.body)} bytes, PNG {d}; state font {font}; palette {len(gx.get('palette') or [])} colours; Cache-Control {r.headers.get('cache-control')}", real_only=True)
    ref = sorted({x for s_ in sp for x in ((s_.get("gfx") or {}).get("p"), (s_.get("gfx") or {}).get("ip")) if x})
    bad, sizes = [], 0
    for name in ref:
        budget()
        pg = pages.get(name)
        if not pg:
            bad.append(f"{name}: not in gfx.pages"); continue
        r = hreq("GET", pg["url"] + "?" + tq())
        d = png_dims(r.body)
        sizes += len(r.body)
        if r.code != 200 or r.ctype != "image/png" or not d or (pg.get("w") and d != (pg["w"], pg["h"])):
            bad.append(f"{name}: {r.code} {r.ctype} {d} vs {pg.get('w')}x{pg.get('h')}")
    with_sprite = sum(1 for s_ in sp if s_.get("gfx"))
    rec("get.gfx_sheets", "PASS" if ref and not bad else "FAIL",
        f"{len(ref)} sheets referenced by {with_sprite}/{len(sp)} species (of {len(pages)} served); fetched {sizes // 1024} KB; bad {bad[:6]}", real_only=True)
    r = get("/gfx/p/NO_SUCH_SHEET")
    rec("get.gfx_unknown", "PASS" if r.code == 404 and "no such sheet" in r.text else "FAIL", f"/gfx/p/NO_SUCH_SHEET -> {r.short(60)}", real_only=True)

# =============================================================================================== sec
def phase_sec(a):
    def chk(rid, r, code, contains=None, ctype=None, note="", real_only=False):
        ok = r.code == code and (contains is None or contains in r.text) and (ctype is None or r.ctype.startswith(ctype))
        return rec(rid, "PASS" if ok else "FAIL", f"{note}-> {r.short(90)} [{r.ctype}] (expected {code}{' ' + repr(contains) if contains else ''})", real_only=real_only)
    tokpre = TOKEN[:-1] if len(TOKEN) > 1 else "x"
    chk("sec.page_no_token", hreq("GET", "/"), 200, "seasonal-wildlife", "text/html", "GET / with no token (the page itself needs none) ")
    chk("sec.state_no_token", hreq("GET", "/state.json"), 403, '"token"', "application/json", "GET /state.json, no token ")
    chk("sec.state_wrong_token", hreq("GET", "/state.json?t=" + "f" * 20), 403, '"token"', None, "GET /state.json?t=ffff.. ")
    chk("sec.state_token_prefix", hreq("GET", "/state.json?t=" + tokpre), 403, '"token"', None, "the token less its last digit ")
    chk("sec.state_token_empty", hreq("GET", "/state.json?t="), 403, None, None, "?t= (empty) ")
    chk("sec.controls_no_token", hreq("GET", "/controls.json"), 403, None, None, "GET /controls.json, no token ")
    chk("sec.status_no_token", hreq("GET", "/status.json"), 403, None, None, "GET /status.json, no token ")
    chk("sec.gfx_no_token", hreq("GET", "/gfx/font"), 403, "token", "text/plain", "GET /gfx/font, no token ", real_only=True)
    chk("sec.token_case", hreq("GET", "/state.json?t=" + TOKEN.upper()), 403 if TOKEN.upper() != TOKEN else 200, None, None, "the token upper-cased ", real_only=True)
    # Host (DNS rebinding): checked before everything, the page included
    before = values_of(ctl_json()).get("hunters.stoop.chance")
    for rid, path, host, code in [("sec.host_foreign_page", "/", "evil.example:%d" % WPORT, 403),
                                  ("sec.host_foreign_state", "/state.json?" + tq(), "evil.example:%d" % WPORT, 403),
                                  ("sec.host_no_port", "/state.json?" + tq(), "127.0.0.1", 403),
                                  ("sec.host_wrong_port", "/state.json?" + tq(), "127.0.0.1:9999", 403),
                                  ("sec.host_lan_ip", "/state.json?" + tq(), "192.168.1.10:%d" % WPORT, 403),
                                  ("sec.host_missing", "/state.json?" + tq(), None, 403),
                                  ("sec.host_localhost", "/state.json?" + tq(), "localhost:%d" % WPORT, 200),
                                  ("sec.host_foreign_set", "/set?" + tq(id="hunters.stoop.chance", v="61"), "evil.example:%d" % WPORT, 403)]:
        r = hreq("POST" if "/set" in path else "GET", path, host=host)
        chk(rid, r, code, "wrong host" if code == 403 else None, None, f"Host {host!r} on {path.split('?')[0]} ", real_only=True)
    if before is not None and not same(values_of(ctl_json()).get("hunters.stoop.chance"), before):
        post("/set", id="hunters.stoop.chance", v=fnum(before, "int"))
        log(f"   the foreign-Host /set went through; hunters.stoop.chance put back to {before}")
    # methods
    for p in ("/set", "/act", "/read", "/cmd"):
        chk(f"sec.get_on{p.replace('/', '_')}", hreq("GET", p + "?" + tq(id="x")), 405, "POST only", None, f"GET {p} with the token ")
        chk(f"sec.post_no_token{p.replace('/', '_')}", hreq("POST", p + "?id=x"), 403, None, None, f"POST {p} with no token (token checked first) ")
    chk("sec.post_page", hreq("POST", "/"), 405, "GET only", None, "POST / ", real_only=True)
    r = hreq("POST", "/state.json?" + tq())
    rec("sec.post_state", "PASS" if r.code == 200 else "FAIL", f"POST /state.json with the token -> {r.code} (as coded: the read routes do not check the method; harmless, they write nothing)", real_only=True)
    chk("sec.unknown_path", hreq("GET", "/nope?" + tq()), 404, "not found", None, "GET /nope with the token ", real_only=True)
    chk("sec.unknown_path_no_token", hreq("GET", "/nope"), 403, None, None, "GET /nope, no token ")
    # the /cmd whitelist (seasonal-wildlife-controls checkVerb)
    for rid, words, why in [("preset", ["preset", "x"], "not a verb"), ("gui", ["gui"], "not a verb"), ("place", ["place", "WOLF"], "not a verb"),
                            ("class", ["class", "WOLF", "natural"], "not a verb"), ("lua", ["lua", "print(1)"], "not a verb"),
                            ("groups_adopt", ["groups", "adopt", "1"], "not a groups subverb"), ("groups_nudge", ["groups", "nudge", "on"], "not a groups subverb"),
                            ("space", ["roster", "a b"], "refused an argument"), ("semicolon", ["roster", "x;y"], "refused an argument"),
                            ("quote", ["roster", "x'y"], "refused an argument"), ("long_word", ["roster", "A" * 65], "refused an argument"),
                            ("too_many", ["status"] + ["x"] * 12, "too many words"), ("empty", [], "not a verb")]:
        r = post("/cmd", *[("a", w) for w in words])
        j = r.json() or {}
        rec(f"sec.cmd_refuse.{rid}", "PASS" if r.code == 400 and j.get("ok") is False and why in str(j.get("out")) else "FAIL",
            f"/cmd a={words[:3]}{'...' if len(words) > 3 else ''} -> {r.short(100)} (expected 400 '{why}')", real_only=rid not in ("preset", "gui", "place"))
    # bad ids, tokens and arguments on the write routes
    sp_row = next((x for x in (memo.get("ctl") or {}).get("species") or [] if x.get("type") == "bool"), {"id": "v7.fisher_list.{T}"})
    for rid, path, pairs, why in [("set_unknown", "/set", dict(id="no.such.control", v="1"), "no such control"),
                                  ("set_no_id", "/set", dict(v="1"), "no such control"),
                                  ("set_species_no_tok", "/set", dict(id=sp_row["id"], v="on"), "a creature token is needed"),
                                  ("set_species_bad_tok", "/set", dict(id=sp_row["id"], v="on", tok="bad;tok"), "a creature token is needed"),
                                  ("set_species_lower_tok", "/set", dict(id=sp_row["id"], v="on", tok="wolf"), "a creature token is needed"),
                                  ("act_unknown", "/act", dict(id="no_such_action"), "no such action"),
                                  ("act_bad_arg", "/act", dict(id="roster_build", arg="everything"), "choose one of"),
                                  ("act_missing_arg", "/act", dict(id="irr_now"), "choose one of"),
                                  ("act_water_bad_arg", "/act", dict(id="water_now", arg="lava"), "choose one of"),
                                  ("read_unknown", "/read", dict(id="no_such_readout"), "no such readout")]:
        r = post(path, **pairs)
        j = r.json() or {}
        rec(f"sec.{rid}", "PASS" if r.code == 400 and j.get("ok") is False and why in str(j.get("out")) else "FAIL",
            f"POST {path} {pairs} -> {r.short(100)} (expected 400 '{why}')",
            real_only=rid in ("set_species_no_tok", "set_species_bad_tok", "set_species_lower_tok", "act_bad_arg", "act_missing_arg", "act_water_bad_arg", "set_no_id"))
    # 127.0.0.1 only: the Mac's LAN address must not answer
    lan = None
    try:
        lan = subprocess.run(["ipconfig", "getifaddr", "en0"], capture_output=True, text=True, timeout=5).stdout.strip() or None
    except Exception:
        pass
    if lan:
        s = socket.socket(); s.settimeout(3)
        try:
            s.connect((lan, WPORT)); res = "CONNECTED"
        except Exception as e:
            res = f"{type(e).__name__}"
        finally:
            s.close()
        rec("sec.lan_not_served", "PASS" if res != "CONNECTED" else "FAIL", f"connect to {lan}:{WPORT} (the Mac's en0 address) -> {res} (bound to 127.0.0.1 only)", real_only=True)
    else:
        rec("sec.lan_not_served", "NOT-TESTABLE", "no en0 address to try")

# =============================================================================================== ctl
def console_read(batch_ids):
    """{id: (get_text, cfg_value)} for the batch, or None when the console is offline / did not answer."""
    j = console_gets([(i, None) for i in batch_ids])
    if j is None:
        return None
    return {i: (str(x.get("get", "")).strip(), x.get("cfg")) for i, x in zip(batch_ids, j)}

def phase_ctl(a):
    c = ctl_json()
    rows = [r for r in c.get("controls") or []]
    if a.only_controls:
        pat = re.compile(a.only_controls)
        rows = [r for r in rows if pat.search(r["id"])]
    base = values_of(c)
    memo["ctl_baseline"] = dict(base)
    # the console's whole list once, through cx-lifecycle.sh cmd (the player's own path), against controls.json
    if MODE == "live":
        rc, out, err = sh("cmd", "seasonal-wildlife-controls", "list", timeout=90)
        got = {}
        for line in out.splitlines():
            w = line.split()
            if len(w) >= 2 and w[0] in base:
                got[w[0]] = w[1]
        na = [i for i in base if base[i] is False and got.get(i) == "n/a"]
        dis = [f"{i}: web {base[i]!r} console {got.get(i)!r}" for i in base if i in got and i not in na and not same(base[i], got[i])
               and not (base[i] == "" and got[i] in ("bool", "seasons", "text"))]
        rec("ctl.console_list", "PASS" if len(got) >= len(base) - 2 and not dis else "FAIL",
            f"`cx-lifecycle.sh cmd seasonal-wildlife-controls list`: {len(got)} of {len(base)} rows parsed; disagreeing with /controls.json "
            f"(false-as-n/a counted apart): {len(dis)} {dis[:5]}")
        nfalse = sum(1 for i in base if base[i] is False)
        rec("ctl.console_list_false", "PASS" if not na else "FAIL",
            f"{len(na)} of {nfalse} controls whose value is false print 'n/a' in `seasonal-wildlife-controls list` (e.g. {na[:4]}); "
            "the console list's `available(r) and valueOf(r, cfg) or 'n/a'` drops a false, the bug 03fc38c fixed in controls.json")
    # every type's extra illegal values, on the first row of the type; anything that got through is put back at once
    for t, vals in EXTRA_ILLEGAL.items():
        r0 = next((r for r in rows if r["type"] == t and r.get("available")), None)
        if not r0:
            continue
        for v, why in vals:
            rr = post("/set", id=r0["id"], v=v)
            j = rr.json() or {}
            rec(f"ctl.illegal_{t}.{v[:12] or 'empty'}", "PASS" if rr.code == 400 and j.get("ok") is False and why in str(j.get("out")) else "FAIL",
                f"{r0['id']} = {v[:20]!r} -> {rr.short(90)} (expected 400 '{why}')", real_only=True)
        now = values_of(ctl_json()).get(r0["id"])
        if not same(now, base.get(r0["id"])) and base.get(r0["id"]) is not None:
            rr = post("/set", id=r0["id"], v=wire(r0, base[r0["id"]]))
            log(f"   {r0['id']} moved to {now!r} by an illegal value; put back to {base[r0['id']]!r}: {rr.short(40)}")
    batches = make_batches([r for r in rows if r.get("available")], a.batch)
    for r in rows:
        if not r.get("available"):
            rr = post("/set", id=r["id"], v="1")
            rec(f"ctl.{r['id']}", "NOT-TESTABLE" if rr.code == 400 and "not in this version" in rr.text else "FAIL",
                f"unavailable in this engine (req); /set -> {rr.short(80)}")
    log(f"   {len(rows)} controls in {len(batches)} batches of at most {a.batch}")
    cur = values_of(ctl_json())
    for bi, batch in enumerate(batches):
        budget()
        ids = [r["id"] for r in batch]
        cur = values_of(memo["ctl"])          # the latest read: a coupled verb in an earlier batch may have moved a row
        P = {r["id"]: plan_control(r, cur.get(r["id"])) for r in batch}
        ev = {i: [] for i in ids}
        bad = {i: [] for i in ids}      # failed sub-checks
        soft = {i: [] for i in ids}     # mock-unmodelled sub-checks
        # 1. illegal values: refused, nothing changes
        for r in batch:
            p = P[r["id"]]
            for v, why in [(p["bad"], p["bad_why"])]:
                rr = post("/set", id=r["id"], v=v)
                j = rr.json() or {}
                ok = rr.code == 400 and j.get("ok") is False and why in str(j.get("out"))
                ev[r["id"]].append(f"illegal {v!r} -> {rr.code} '{cut(j.get('out', rr.text), 50)}'")
                if not ok:
                    (soft if (MODE == "mock" and r["type"] == "text") else bad)[r["id"]].append("illegal accepted")
        after_bad = values_of(ctl_json())
        for i in ids:
            if not same(after_bad.get(i), cur.get(i)):
                (soft if (MODE == "mock" and P[i]["type"] == "text") else bad)[i].append(f"changed by the illegal value ({cur.get(i)!r} -> {after_bad.get(i)!r})")
                cur[i] = after_bad.get(i)
        # 2. set every member to another legal value
        for r in batch:
            p = P[r["id"]]
            if p["new"] is None:
                bad[r["id"]].append("no other legal value"); continue
            rr = post("/set", id=r["id"], v=p["new_wire"], timeout=SET_TIMEOUT)
            j = rr.json() or {}
            want, _ = py_validate(r, p["new_wire"])
            p["want"] = want
            ev[r["id"]].append(f"set {cur.get(r['id'])!r}->{p['new_wire']!r}: {rr.code} value={j.get('value')!r} cmd='{cut(j.get('cmd'), 70)}'")
            if not (rr.code == 200 and j.get("ok") is True and same(j.get("value"), want)):
                bad[r["id"]].append(f"set refused or misreported ({rr.code} {cut(j.get('out', rr.text), 120)})")
        web1 = values_of(ctl_json())
        con1 = console_read(ids)
        for r in batch:
            i, want = r["id"], P[r["id"]].get("want")
            if want is None:
                continue
            w = web1.get(i)
            ok_w = same(w, want)
            s_ = f"web={w!r}"
            ok_c = True
            if con1 is not None:
                g, cv = con1[i]
                ok_c = same(g, want) and same(cv, want)
                s_ += f" console get={g!r} cfg={cv!r}"
            else:
                s_ += " console=offline"
            ev[i].append(s_)
            if not (ok_w and ok_c):
                P[i]["mismatch"] = True
        # 3. back to the original, in reverse order (a coupled verb that moved a batch-mate is undone after it)
        for r in reversed(batch):
            p = P[r["id"]]
            if p["new"] is None or p["orig_wire"] is None:
                continue
            rr = post("/set", id=r["id"], v=p["orig_wire"], timeout=SET_TIMEOUT)
            j = rr.json() or {}
            ev[r["id"]].append(f"restore {p['orig_wire']!r}: {rr.code}")
            if not (rr.code == 200 and j.get("ok") is True):
                bad[r["id"]].append(f"restore refused ({rr.code} {cut(j.get('out', rr.text), 120)})")
        web2 = values_of(ctl_json())
        con2 = console_read(ids)
        for r in batch:
            i, orig = r["id"], P[r["id"]]["orig"]
            w = web2.get(i)
            ok = same_restore(r, w, orig)
            s_ = f"restored web={w!r}"
            if con2 is not None:
                g, cv = con2[i]
                ok = ok and same_restore(r, g, orig) and same_restore(r, cv, orig)
                s_ += f" console={g!r}"
            ev[i].append(s_)
            if not ok:
                P[i]["restore_mismatch"] = True
        # 4. a member whose read back disagreed is re-tested alone (a batch-mate may share its key)
        for r in batch:
            i, p = r["id"], P[r["id"]]
            if not (p.get("mismatch") or p.get("restore_mismatch")):
                continue
            budget()
            solo = solo_retest(r, p, cur)
            ev[i].append("SOLO " + solo["ev"])
            if solo["ok"]:
                ev[i].append("(the batch read back differed; alone it agrees: coupling with a batch-mate)")
            else:
                bad[i].append("read back disagrees when set alone")
        for r in batch:
            i = r["id"]
            v = "FAIL" if bad[i] else "PASS"
            note = ("; FAILED: " + "; ".join(bad[i])) if bad[i] else ""
            if soft[i]:
                note += "; mock-unmodelled: " + "; ".join(soft[i])
            rec(f"ctl.{i}", v, f"[{r['type']}{' ' + str(r.get('min')) + '..' + str(r.get('max')) if r['type'] in ('int', 'float') else ''}] " + " | ".join(ev[i]) + note,
                data={"orig": P[i]["orig"], "new": P[i]["new"], "illegal": P[i]["bad"], "batch": bi})
    # 5. the whole registry against the baseline; anything a coupled verb left moved is put back, then compared again
    fin = values_of(ctl_json())
    drift = {i: (base.get(i), fin.get(i)) for i in base if not same_restore({"type": next((r["type"] for r in rows if r["id"] == i), "")}, fin.get(i), base.get(i))}
    repaired = []
    if drift:
        byid = {r["id"]: r for r in rows}
        for i, (b, f) in drift.items():
            if i in byid and b is not None:
                rr = post("/set", id=i, v=wire(byid[i], b), timeout=SET_TIMEOUT)
                repaired.append(f"{i} {f!r}->{b!r}: {rr.code}")
        fin = values_of(ctl_json())
    left = {i: (base.get(i), fin.get(i)) for i in base if not same_restore({"type": next((r["type"] for r in rows if r["id"] == i), "")}, fin.get(i), base.get(i))}
    rec("ctl.registry_restored", "PASS" if not left else "FAIL",
        f"after every control: {len(drift)} value(s) differed from the run's baseline {list(drift.items())[:6]}; put back: {repaired[:6]}; still different: {list(left.items())[:6]}")

def solo_retest(r, p, cur):
    i = r["id"]
    rr = post("/set", id=i, v=p["new_wire"], timeout=SET_TIMEOUT)
    j = rr.json() or {}
    w1 = values_of(ctl_json()).get(i)
    c1 = console_read([i])
    ok = rr.code == 200 and j.get("ok") is True and same(w1, p.get("want")) and (c1 is None or (same(c1[i][0], p.get("want")) and same(c1[i][1], p.get("want"))))
    if p["orig_wire"] is not None:
        rr2 = post("/set", id=i, v=p["orig_wire"], timeout=SET_TIMEOUT)
        ok = ok and rr2.code == 200
    w2 = values_of(ctl_json()).get(i)
    c2 = console_read([i])
    ok = ok and same_restore(r, w2, p["orig"]) and (c2 is None or same_restore(r, c2[i][0], p["orig"]))
    return {"ok": ok, "now": w2, "ev": f"set {p['new_wire']!r}: {rr.code} value={j.get('value')!r} web={w1!r} console={c1 and c1[i]!r}; restore web={w2!r} console={c2 and c2[i]!r}"}

# =============================================================================================== species
def species_tokens(st):
    sp = [s for s in st.get("species") or [] if s.get("role") != "vermin"]
    def first(f):
        return next((s["token"] for s in sp if f(s)), None)
    return {"pred": first(lambda s: s.get("role") == "predator" and s.get("layer") == "land" and s.get("habitat", "land") == "land")
                    or first(lambda s: s.get("role") == "predator"),
            "raptor": first(lambda s: s.get("guild") == "RP" or s.get("slot") == "RP"),
            "aquatic": first(lambda s: s.get("role") == "predator" and s.get("habitat") in ("aquatic", "semiaquatic")),
            "extinct": first(lambda s: s.get("extinct")),
            "all": first(lambda s: True)}

def phase_species(a):
    c = ctl_json()
    st = memo.get("state") or state_json()
    toks = species_tokens(st)
    for r in c.get("species") or []:
        budget()
        i, tok = r["id"], toks.get(r.get("when") or "all")
        if not tok:
            rec(f"species.{i}", "NOT-TESTABLE", f"no species of kind '{r.get('when')}' on this fort"); continue
        maps = (memo.get("ctl") or {}).get("maps") or {}
        m = maps.get(i) if isinstance(maps.get(i), dict) else {}
        orig = display_raw(i, r, m.get(tok))
        bad, ev = [], []
        c0 = console_gets([(i, tok)])
        if c0 and not same(c0[0]["get"].strip(), orig):
            bad.append(f"before the test the web map shows {orig!r} and the console {c0[0]['get'].strip()!r}")
        b, why = illegal(r)
        rr = post("/set", id=i, v=b, tok=tok)
        if not (rr.code == 400 and why in rr.text):
            bad.append("illegal accepted")
        ev.append(f"tok {tok}; illegal {b!r} -> {rr.code}")
        new = other(r, orig)
        nw = wire(r, new)
        want, _ = py_validate(r, nw)
        rr = post("/set", id=i, v=nw, tok=tok, timeout=SET_TIMEOUT)
        j = rr.json() or {}
        ev.append(f"set {orig!r}->{nw!r}: {rr.code} value={j.get('value')!r} cmd='{cut(j.get('cmd'), 60)}'")
        if not (rr.code == 200 and j.get("ok") and same(j.get("value"), want)):
            bad.append(f"set ({rr.code} {cut(j.get('out', rr.text), 100)})")
        cj = ctl_json()
        mm = (cj.get("maps") or {}).get(i)
        wv = display_raw(i, r, (mm if isinstance(mm, dict) else {}).get(tok))
        con = console_gets([(i, tok)])
        ev.append(f"web map={wv!r}" + (f" console={con[0]['get'].strip()!r} cfg={con[0]['cfg']!r}" if con else " console=offline"))
        if not same(wv, want) or (con and not (same(con[0]["get"].strip(), want) and same(con[0]["cfg"], want))):
            bad.append("read back disagrees")
        ow = wire(r, orig) if orig is not None else ("off" if r["type"] == "bool" else str(r.get("nilv") or ""))
        rr = post("/set", id=i, v=ow, tok=tok, timeout=SET_TIMEOUT)
        cj = ctl_json()
        mm = (cj.get("maps") or {}).get(i)
        wv2 = display_raw(i, r, (mm if isinstance(mm, dict) else {}).get(tok))
        con2 = console_gets([(i, tok)])
        ev.append(f"restore {ow!r}: {rr.code} web={wv2!r}" + (f" console={con2[0]['get'].strip()!r}" if con2 else ""))
        if rr.code != 200 or not same_restore(r, wv2, orig):
            bad.append("restore")
        rec(f"species.{i}", "FAIL" if bad else "PASS", " | ".join(ev) + (("; FAILED: " + "; ".join(bad)) if bad else ""))

# =============================================================================================== read / cmd
def norm(s):
    lines = [re.sub(r"\s+", " ", l).strip() for l in str(s).replace("\r", "").splitlines()]
    return [re.sub(r"-?\d+(\.\d+)?", "#", l) for l in lines if l]

def first_diff(a, b):
    na, nb = norm(a), norm(b)
    for k in range(max(len(na), len(nb))):
        x = na[k] if k < len(na) else "(none)"; y = nb[k] if k < len(nb) else "(none)"
        if x != y:
            return f"line {k + 1}: web '{cut(x, 80)}' / console '{cut(y, 80)}'"
    return ""

ERRPAT = r"LUA ERROR|stack traceback|attempt to (index|call|compare|perform|concatenate)|\.lua:\d+:"

def phase_read(a):
    c = memo.get("ctl") or ctl_json()
    ros = c.get("readouts") or []
    web = {}
    for ro in ros:
        budget()
        if not ro.get("available", True):
            rr = post("/read", id=ro["id"])
            rec(f"read.{ro['id']}", "NOT-TESTABLE", f"unavailable in this engine; /read -> {rr.short(80)}"); continue
        rr = post("/read", id=ro["id"], timeout=SET_TIMEOUT)
        web[ro["id"]] = (rr, rr.json() or {})
    avail = [ro for ro in ros if ro["id"] in web]
    con = {}
    for k in range(0, len(avail), 9):
        part = avail[k:k + 9]
        outs = console_verbs([ro["verb"].split() for ro in part])
        for ro, o in zip(part, outs or [None] * len(part)):
            con[ro["id"]] = o
    for ro in avail:
        rr, j = web[ro["id"]]
        out = str(j.get("out") or "")
        ok = rr.code == 200 and j.get("ok") is True and out.strip() and not re.search(r"^\s*[Uu]sage", out) and not re.search(ERRPAT, out) \
            and j.get("cmd") == "seasonal-wildlife " + ro["verb"]
        co = con.get(ro["id"])
        agree = "console offline" if co is None else ("console agrees (digits masked)" if norm(co) == norm(out) else "console DIFFERS (dynamic output?) " + first_diff(out, co))
        rec(f"read.{ro['id']}", "PASS" if ok else "FAIL", f"`{ro['verb']}` -> {rr.code} ok={j.get('ok')} {len(out.splitlines())} lines '{cut(out, 90)}'; {agree}",
            data={"agree": co is not None and norm(co) == norm(out)})

def phase_cmd(a):
    st = memo.get("state") or state_json()
    key = next((s["key"] for s in st.get("species") or [] if s.get("role") != "vermin" and s.get("active") and s.get("layer") == "land"), None) \
        or next((s["key"] for s in st.get("species") or [] if s.get("role") != "vermin"), "WOLF")
    sample = [["status"], ["roster"], ["roster", key], ["seasons", key], ["limits"], ["odds", key], ["stock", key], ["ledger", "5"], ["v7"]]
    for words in sample:
        budget()
        rr = post("/cmd", *[("a", w) for w in words], timeout=SET_TIMEOUT)
        j = rr.json() or {}
        out = str(j.get("out") or "")
        rc, cout, cerr = sh("cmd", "seasonal-wildlife", *words, timeout=90)
        ok = rr.code == 200 and j.get("ok") is True and out.strip() and j.get("cmd") == "seasonal-wildlife " + " ".join(words) and not re.search(ERRPAT, out)
        if MODE == "live":
            agree = norm(out) == norm(cout)
            ok = ok and agree
            note = "console agrees (digits masked)" if agree else "console DIFFERS: " + first_diff(out, cout)
        else:
            note = "console offline"
        rec(f"cmd.{'_'.join(w if w != key else 'KEY' for w in words)}", "PASS" if ok else "FAIL",
            f"/cmd a={words} -> {rr.code} ok={j.get('ok')} '{cut(out, 90)}'; `cx-lifecycle.sh cmd seasonal-wildlife {' '.join(words)}` -> '{cut(cout, 60)}'; {note}")

# =============================================================================================== conc / mal
def phase_conc(a):
    s0 = state_json()
    d0 = (s0.get("date") or {}).get("abs_day")
    paths = ["/state.json?" + tq(), "/status.json?" + tq(s="jobs"), "/controls.json?" + tq(), "/state.json?" + tq()]
    res, lock = [], threading.Lock()
    def worker(n):
        for k in range(a.conc_each):
            r = hreq("GET", paths[(n + k) % len(paths)], count=False, timeout=60)
            with lock:
                res.append(r)
    stepped = {}
    def stepper():
        t = time.time()
        if MODE == "live":
            rc, out, err = sh("step", 1200, 180, timeout=260)
            stepped["out"] = cut(out + err, 160)
        else:
            time.sleep(2.0); stepped["out"] = "(offline: no step)"
        stepped["secs"] = round(time.time() - t, 1)
    th = threading.Thread(target=stepper); th.start()
    time.sleep(0.5)
    ws = [threading.Thread(target=worker, args=(n,)) for n in range(a.conc)]
    t0 = time.time()
    for w in ws: w.start()
    for w in ws: w.join()
    wall = time.time() - t0
    th.join()
    codes = Counter(r.code for r in res)
    errs = [r.err for r in res if r.err][:4]
    badjson = sum(1 for r in res if r.code == 200 and r.json() is None)
    ms = sorted(r.ms for r in res)
    p = lambda q: ms[min(len(ms) - 1, int(q * len(ms)))] if ms else 0
    ok_after, r_after = alive()
    s1 = state_json()
    d1 = (s1.get("date") or {}).get("abs_day")
    moved = MODE != "live" or (d0 is not None and d1 is not None and d1 > d0)
    rec("conc.parallel", "PASS" if codes == Counter({200: len(res)}) and not badjson and ok_after and moved else "FAIL",
        f"{a.conc} clients x {a.conc_each} GETs ({len(res)}) in {wall:.1f}s while the fort stepped 1200 ticks ({stepped.get('out')}; {stepped.get('secs')}s): codes {dict(codes)}, "
        f"unparsable JSON {badjson}, latency p50 {p(0.5)} ms p95 {p(0.95)} ms max {ms[-1] if ms else 0} ms; errors {errs}; alive after: {r_after.short(30)}; abs_day {d0} -> {d1}",
        data={"codes": dict(codes), "p50": p(0.5), "p95": p(0.95), "max": ms[-1] if ms else 0})

def phase_mal(a):
    H = f"Host: 127.0.0.1:{WPORT}\r\n".encode()
    T = TOKEN.encode()
    cases = [
        ("garbage_line", b"GARBAGE\r\n\r\n", "400"),
        ("http2", b"GET /state.json?t=" + T + b" HTTP/2.0\r\n" + H + b"\r\n", "400"),
        ("lowercase_method", b"get / HTTP/1.1\r\n" + H + b"\r\n", "400"),
        ("head", b"HEAD / HTTP/1.1\r\n" + H + b"\r\n", "405"),
        ("binary", b"\x00\xff\xfe\x01\r\n\r\n", "400"),
        ("bad_query", b"GET /state.json?t=" + T + b"&%zz=%&&a==b&=x&&& HTTP/1.1\r\n" + H + b"\r\n", "200"),
        ("bad_percent_token", b"GET /state.json?t=%ZZ%G1 HTTP/1.1\r\n" + H + b"\r\n", "403"),
        ("huge_query", b"GET /state.json?t=" + T + b"&x=" + b"A" * 65536 + b" HTTP/1.1\r\n" + H + b"\r\n", None),
        ("huge_value", b"POST /set?t=" + T + b"&id=hunters.stoop.chance&v=" + b"9" * 5000 + b" HTTP/1.1\r\n" + H + b"Content-Length: 0\r\n\r\n", "400"),
        ("header_flood", b"GET /state.json?t=" + T + b" HTTP/1.1\r\n" + b"".join(b"X-Pad-%d: y\r\n" % k for k in range(80)) + H + b"\r\n", "403"),
        ("traversal", b"GET /gfx/p/..%2F..%2Fprefs%2Finit?t=" + T + b" HTTP/1.1\r\n" + H + b"\r\n", "404"),
        ("traversal_raw", b"GET /gfx/p/../../prefs/init.txt?t=" + T + b" HTTP/1.1\r\n" + H + b"\r\n", "404"),
        ("nul_in_path", b"GET /state.json\x00?t=" + T + b" HTTP/1.1\r\n" + H + b"\r\n", None),
    ]
    for rid, data, want in cases:
        budget()
        line, secs = raw(data, wait=8.0)
        ok_a, r = alive()
        got = re.match(r"HTTP/1\.[01] (\d+)", line)
        code = got.group(1) if got else None
        ok = ok_a and (want is None or code == want or (rid == "header_flood" and line == "(reset by the server)"))
        rec(f"mal.{rid}", "PASS" if ok else "FAIL", f"{len(data)} bytes -> '{cut(line, 70)}' in {secs:.2f}s (expected {want or 'any reply or a close'}); alive after: {r.short(20)}",
            real_only=want is not None)
    line, secs = raw(b"", wait=3.0, send=False)
    ok_a, r = alive()
    rec("mal.idle_connection", "PASS" if ok_a else "FAIL", f"connect and send nothing: '{cut(line, 50)}' after {secs:.1f}s; alive after: {r.short(20)}")
    line, secs = raw(b"GET /state.json?t=" + T + b" HTTP/1.1\r\n" + H, wait=5.0)
    ok_a, r = alive()
    rec("mal.half_request", "PASS" if ok_a else "FAIL", f"request line and Host, no blank line: '{cut(line, 50)}' after {secs:.1f}s; alive after: {r.short(20)}")
    # a burst of connections opened and dropped at once
    socks = []
    for _ in range(20):
        try:
            s = socket.create_connection(("127.0.0.1", WPORT), timeout=2); socks.append(s)
        except Exception:
            pass
    for s in socks:
        s.close()
    time.sleep(1.0)
    ok_a, r = alive()
    rec("mal.dropped_burst", "PASS" if ok_a else "FAIL", f"{len(socks)} connections opened and closed unsent; alive after: {r.short(20)}")

# =============================================================================================== act
SAFE = ["rearm", "water_survey", "ecology_now", "scavenge_now", "curious_now", "forage_now", "v7_apply", "natives_now", "irr_unpin"]
DRAWS = ["water_now", "apex_now"]
DESTRUCTIVE = ["irr_stir", "irr_now", "irr_end", "irr_cool", "scavenge_stats_reset", "sendoff_cavern", "sendoff_land", "roster_build", "all_off", "all_on"]

def act(aid, arg=None):
    rr = post("/act", id=aid, arg=arg, timeout=SET_TIMEOUT)
    return rr, rr.json() or {}

def act_row(aid, arg, rr, j, extra_ok=True, extra="", rid=None):
    out = str(j.get("out") or "")
    ok = rr.code == 200 and j.get("ok") is True and not re.search(ERRPAT, out) and not re.match(r"\s*[Uu]sage", out) and extra_ok
    rec(rid or f"act.{aid}{'.' + arg if arg else ''}", "PASS" if ok else "FAIL",
        f"/act {aid}{' ' + arg if arg else ''} -> {rr.code} ok={j.get('ok')} cmd='{cut(j.get('cmd'), 50)}' out='{cut(out, 140)}'{'; ' + extra if extra else ''}")

def cavern_lines():
    out = {}
    for l in status_lines("irruption"):
        m = re.match(r"\s*cavern (\d): .*?\]\s+(.*)$", l)
        if m:
            out[m.group(1)] = m.group(2)
    return out

def phase_act(a):
    c = memo.get("ctl") or ctl_json()
    acts = {x["id"]: x for x in c.get("actions") or []}
    known = set(SAFE + DRAWS + DESTRUCTIVE)
    for aid in acts:
        if aid not in known:
            rec(f"act.{aid}", "FAIL", f"an action the driver does not classify ({acts[aid].get('label')}); add it to SAFE/DRAWS/DESTRUCTIVE")
    for aid in [x for x in SAFE if x in acts]:
        budget()
        rr, j = act(aid)
        extra_ok, extra = True, ""
        if aid == "rearm":
            extra_ok = MODE != "live" or "re-armed" in str(j.get("out"))
            extra = f"fuse now '{cut(state_json().get('fuse'), 60)}'"
        act_row(aid, None, rr, j, extra_ok, extra)
    for aid in [x for x in DRAWS if x in acts]:
        for arg in acts[aid].get("arg") or [None]:
            budget()
            n0 = len(state_json().get("ledger") or [])
            rr, j = act(aid, arg)
            act_row(aid, arg, rr, j)
    if a.no_destructive:
        for aid in DESTRUCTIVE:
            if aid in acts:
                rec(f"act.{aid}", "NOT-TESTABLE", "--no-destructive")
        return
    # ---- irruptions: on (if off), stir, end, now, end, cool, back as it was
    base = values_of(ctl_json())
    irr0 = base.get("switch.irruption")
    if irr0 is not True:
        rr = post("/set", id="switch.irruption", v="on", timeout=SET_TIMEOUT)
        log(f"   irruptions switched on for the irruption actions: {rr.short(60)}")
    lines = cavern_lines()
    cav = a.irr_cavern or next((k for k, v in sorted(lines.items()) if "not reached" not in v), "1")
    log(f"   irruption cavern {cav}; phases before: {lines}")
    rr, j = act("irr_stir", cav); after = cavern_lines().get(cav, "")
    act_row("irr_stir", cav, rr, j, MODE != "live" or "STIRRING" in after, f"cavern {cav} now '{cut(after, 60)}' (expected STIRRING)")
    rr, j = act("irr_end"); after = cavern_lines().get(cav, "")
    act_row("irr_end", None, rr, j, MODE != "live" or "STIRRING" not in after, f"cavern {cav} now '{cut(after, 60)}' (a warning ends: quiet)", rid="act.irr_end.after_stir")
    rr, j = act("irr_now", cav); after = cavern_lines().get(cav, "")
    act_row("irr_now", cav, rr, j, MODE != "live" or "IRRUPTING" in after, f"cavern {cav} now '{cut(after, 120)}' (expected IRRUPTING)")
    rr, j = act("irr_end"); after = cavern_lines().get(cav, "")
    act_row("irr_end", None, rr, j, MODE != "live" or ("IRRUPTING" not in after and ("cooldown" in after or "write(s) undone" in str(j.get("out")))),
            f"cavern {cav} now '{cut(after, 60)}' (expected cooldown)")
    rr, j = act("irr_cool"); after = cavern_lines().get(cav, "")
    act_row("irr_cool", None, rr, j, MODE != "live" or "cooldown" not in after, f"cavern {cav} now '{cut(after, 60)}' (expected quiet)")
    for other_cav in sorted(set(a_ for a_ in (acts.get("irr_now", {}).get("arg") or [])) - {cav}):
        rec(f"act.irr_now.{other_cav}", "NOT-TESTABLE", f"one cavern is enough to judge the verb; cavern {cav} was used ({lines.get(other_cav, '?')[:60]})")
    if irr0 is not True:
        rr = post("/set", id="switch.irruption", v="off", timeout=SET_TIMEOUT)
        log(f"   irruptions back off: {rr.short(60)}")
    # ---- who-ate-what reset
    b = post("/read", id="scavenge_stats").json() or {}
    rr, j = act("scavenge_stats_reset")
    a2 = post("/read", id="scavenge_stats").json() or {}
    act_row("scavenge_stats_reset", None, rr, j, True, f"`scavenge stats` before '{cut(b.get('out'), 60)}' after '{cut(a2.get('out'), 60)}'")
    # ---- send-offs
    for aid, layer in (("sendoff_cavern", "cavern"), ("sendoff_land", "land")):
        rr, j = act(aid)
        led = [x for x in state_json().get("ledger") or []][:3]
        ok = MODE != "live" or (re.search(r"sent off \d+ gated %s group" % layer, str(j.get("out"))) and any("sent off" in str(x.get("s")) for x in led))
        act_row(aid, None, rr, j, bool(ok), f"ledger head {[cut(x.get('s'), 50) for x in led[:2]]}")
    # ---- roster build, each layer: one undo step each
    builder = base.get("v7.builder")
    for arg in acts.get("roster_build", {}).get("arg") or ["all"]:
        budget()
        u0 = state_json().get("undo_depth")
        rr, j = act("roster_build", arg)
        u1 = state_json().get("undo_depth")
        out = str(j.get("out"))
        if builder is False and "switch is off" in out:
            rec(f"act.roster_build.{arg}", "NOT-TESTABLE", f"v7 builder is off on this fort: '{cut(out, 80)}'"); continue
        ok = MODE != "live" or (out.startswith("roster build") and (u1 == (u0 or 0) + 1 or (u0 or 0) >= 50))
        act_row("roster_build", arg, rr, j, bool(ok), f"undo depth {u0} -> {u1}")
    # ---- All off, then All on (last: every job stops, then the switches come back as they were)
    sw0 = {k: v for k, v in values_of(ctl_json()).items() if k.startswith("switch.")}
    rr, j = act("all_off")
    s1 = state_json(); sw1 = {k: v for k, v in values_of(ctl_json()).items() if k.startswith("switch.")}
    still = [k for k, v in sw1.items() if v and k not in ("switch.land", "switch.water", "switch.cavern", "switch.deep")]
    alive_ok, _ = alive()
    act_row("all_off", None, rr, j, MODE != "live" or (s1.get("enabled") is False and not still and alive_ok),
            f"enabled {s1.get('enabled')}; switches still on (layer switches excepted) {still}; the server still answers: {alive_ok}")
    rr, j = act("all_on")
    s2 = state_json(); sw2 = {k: v for k, v in values_of(ctl_json()).items() if k.startswith("switch.")}
    back = [k for k in sw0 if k != "switch.rotation" and not same(sw0[k], sw2.get(k))]
    act_row("all_on", None, rr, j, MODE != "live" or (s2.get("enabled") is True and not back),
            f"enabled {s2.get('enabled')}; switches not as before All off: {back}")
    if sw0.get("switch.rotation") is False and sw2.get("switch.rotation") is True:
        post("/set", id="switch.rotation", v="off", timeout=SET_TIMEOUT)
        log("   rotation was off before All off; All on turns it on (cfg.enabled = true); put back off")

# =============================================================================================== outputs
def browser_checklist(a):
    c = memo.get("ctl") or {}
    url = f"http://127.0.0.1:{WPORT}/?t={TOKEN}" if MODE != "dry" else f"http://127.0.0.1:{WPORT}/?t=<token from `seasonal-wildlife-web start`>"
    secs = c.get("sections") or []
    n = Counter(r.get("sec") for r in c.get("controls") or [])
    acts = c.get("actions") or []
    L = [f"# Browser checklist: seasonal-wildlife companion (web 2), run {RUN}", "",
         f"Open **{url}** in Chrome on the Mac (CrossOver shares the loopback). Keep DevTools' console open: any red error is a FAIL.",
         f"Mode: {MODE}. Generated by scripts/web-live.py from the live /controls.json ({len(c.get('controls') or [])} controls, "
         f"{len(secs)} sections, {len(acts)} actions, {len(c.get('readouts') or [])} readouts).", "",
         "## Page frame",
         "- [ ] The header shows the fort name, the date, `seasonal-wildlife <release> · web 2`, and a live connection state.",
         "- [ ] Light and dark (system setting) both readable; no horizontal scroll at 500 px window width.",
         "- [ ] The console drawer opens; every set below adds a line (cmd, done/refused).",
         "- [ ] The sprite/ASCII toggle switches species tiles between DF sprites and glyphs.", ""]
    tabchecks = {
        "Status": ["Panel switches with All on / All off / Re-arm", "layer cards with cap pips (formula or fixed), ceiling, wild count, pattern", "jobs status box (lines, no error)"],
        "Species": ["table sorts by every column; search filters", "a row opens its detail: slot/guild/part chips, giant/extinct chips, group size low-high",
                    "per-species v7 rows appear only for the right kinds (raptor: never stoops; aquatic: swimmer scavenger; extinct: correction)"],
        "Food web": ["graph draws predators -> prey (vermin links dashed)", "season and focus filters change it"],
        "Roster": ["H/C/A pyramid per part (land, flying, water, caverns) against the targets", "apex scheduler status", "Build / Apex now ask to confirm"],
        "Groups": ["one card per layer key (land, water:<body>, cavern:<depth>) with cap pips, target, W, next release", "each group: tile, count, origin, panic"],
        "Controls": ["section nav shows counts and changed-from-default dots", "search across all controls", "each row: widget, unit, default, reset, exact console verb"],
        "Ledger": ["entries listed newest first; kind filter works"],
    }
    for t in TABS:
        L.append(f"## Tab: {t}")
        for x in tabchecks[t]:
            L.append(f"- [ ] {x}")
        L.append("")
    L.append("## Controls sections (click each; the status box must show lines, not an error)")
    for s in secs:
        L.append(f"- [ ] **{s['label']}** (`#controls/{s['id']}`, {n.get(s['id'], 0)} controls, status `{s.get('status')}`): change one control, "
                 "see the toast and the console line, see the value stick after the next 2 s poll, reset it")
    L += ["", "## Actions (destructive ones must ask to confirm first)"]
    for x in acts:
        L.append(f"- [ ] {x['label']} (`{x['id']}`, section {x.get('sec')}){' — CONFIRM dialog expected' if x.get('confirm') else ''}"
                 f"{' — argument: ' + '/'.join(map(str, x.get('arg'))) if x.get('arg') else ''}")
    L += ["", "## Deep links", f"- [ ] {url.split('?')[0]}?t=...#controls/water opens Controls on Water", "- [ ] ...#roster opens Roster",
          "- [ ] ...#groups opens Groups", "", "## Refusals", "- [ ] A wrong token in the address shows the token toast and no data",
          "- [ ] An out-of-range number in a control is refused before sending (client check) with the reason", ""]
    if a.browser and MODE == "live":
        L += ["## Cleanup after the browser pass (the driver left these running)",
              "    scripts/cx-lifecycle.sh cmd seasonal-wildlife-web stop",
              "    scripts/cx-lifecycle.sh title",
              f"    diff -rq \"{SAVE_ROOT / FORT}\" \"{BACKUPS / (FORT + '.' + BACKUP_TAG)}\"", ""]
    (OUT / "browser-checklist.md").write_text("\n".join(L) + "\n")

def report(a, wall):
    tally = Counter(r["verdict"] for r in results)
    by_phase = {}
    for r in results:
        by_phase.setdefault(r["phase"], Counter())[r["verdict"]] += 1
    st = memo.get("state") or {}
    sha = subprocess.run(["git", "-C", str(TOOL_REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    L = [f"# Web companion live test, run {RUN} ({MODE})", "",
         f"- Server: http://127.0.0.1:{WPORT}/ ({'the mock server, tests/web/mock_server.py' if MODE == 'mock' else 'seasonal-wildlife-web inside DF' if MODE == 'live' else 'none (dry run)'})",
         f"- Tool: seasonal-wildlife {st.get('release', '?')} (sw-wt/deploy @ {sha or '?'}); fort '{st.get('fort', '?')}'"
         + (f" ({FORT} from .{BACKUP_TAG})" if MODE == "live" and not a.no_restore else ""),
         f"- Wall time {wall / 60:.1f} min; HTTP requests {STATS['http']}, RPCs {STATS['rpc']}, cx-lifecycle calls {STATS['cx']}",
         f"- Rows: {len(results)} — PASS {tally['PASS']}, FAIL {tally['FAIL']}, NOT-TESTABLE {tally['NOT-TESTABLE']}", "",
         "| phase | PASS | FAIL | NOT-TESTABLE |", "|---|---|---|---|"]
    for ph, t in by_phase.items():
        L.append(f"| {ph} | {t['PASS']} | {t['FAIL']} | {t['NOT-TESTABLE']} |")
    fails = [r for r in results if r["verdict"] == "FAIL"]
    if fails:
        L += ["", "## FAIL"] + [f"- **{r['id']}**: {r['evidence'][:600]}" for r in fails]
    nts = [r for r in results if r["verdict"] == "NOT-TESTABLE"]
    if nts:
        L += ["", "## NOT-TESTABLE"] + [f"- {r['id']}: {r['evidence'][:300]}" for r in nts]
    L += ["", "## Every row"]
    cur = None
    for r in results:
        if r["phase"] != cur:
            cur = r["phase"]; L += ["", f"### {cur}", "", "| id | verdict | evidence |", "|---|---|---|"]
        L.append(f"| {r['id']} | {r['verdict']} | {r['evidence'][:400].replace('|', '/')} |")
    (OUT / "report.md").write_text("\n".join(L) + "\n")

# =============================================================================================== dry run
def dry_plan(a, reg):
    memo["phase"] = "plan"
    rows = [r for r in reg.get("controls") or []]
    batches = make_batches([r for r in rows if r.get("available")], a.batch)
    types = Counter(r["type"] for r in rows)
    n_ok = 0
    for bi, b in enumerate(batches):
        for r in b:
            p = plan_control(r, r.get("value"))
            if _log:
                _log.write(f"    plan b{bi:02d} {r['id']:<40} {r['type']:<7} cur={p['orig']!r:<12} new={p['new_wire']!r:<12} restore={p['orig_wire']!r:<12} illegal={p['bad']!r}\n")
            rec(f"plan.ctl.{r['id']}", "FAIL" if p["problems"] else "PASS",
                f"b{bi} {r['type']} cur {p['orig']!r} -> {p['new_wire']!r} (restore {p['orig_wire']!r}); illegal {p['bad']!r} expect '{p['bad_why']}'"
                + (f"; PROBLEMS: {p['problems']}" if p["problems"] else ""))
            n_ok += not p["problems"]
    for bi, b in enumerate(batches):
        print(f"    batch {bi:02d}: " + " ".join(r["id"] for r in b), flush=True)
    keys_overlap = [bi for bi, b in enumerate(batches) if sum(len(conflict_keys(r)) for r in b) != len(set().union(*[conflict_keys(r) for r in b]))]
    rec("plan.batches", "PASS" if not keys_overlap else "FAIL", f"{len(batches)} batches (at most {a.batch}); batches with a shared verb/key: {keys_overlap}")
    for t, vals in EXTRA_ILLEGAL.items():
        r0 = next((r for r in rows if r["type"] == t), None)
        if not r0:
            continue
        acc = [v for v, _ in vals if py_validate(r0, v)[0] is not None]
        rec(f"plan.illegal_{t}", "PASS" if not acc else "FAIL", f"on {r0['id']}: {[v[:12] for v, _ in vals]} all refused by the validate port; accepted {acc}")
    sp_tok = {"pred": "BEAR_GRIZZLY", "raptor": "BIRD_EAGLE", "aquatic": "SHARK_BULL", "extinct": "CENOZOIC_MEGALANIA", "all": "BEAR_GRIZZLY"}
    for r in reg.get("species") or []:
        cur = display_raw(r["id"], r, None)
        new = other(r, cur)
        v, why = py_validate(r, wire(r, new)) if new is not None else (None, "none")
        b, _ = illegal(r)
        okb = py_validate(r, b)[0] is None
        rec(f"plan.species.{r['id']}", "PASS" if v is not None and okb and not same(v, cur) else "FAIL",
            f"on a '{r.get('when')}' species (e.g. {sp_tok.get(r.get('when'))}): {cur!r} -> {wire(r, new) if new is not None else None!r}; illegal {b!r} refused {okb}")
    n_ctl = len(rows); n_b = len(batches)
    http_n = 60 + 3 * n_ctl + 3 * n_b + 12 * len(reg.get("species") or []) + len(reg.get("readouts") or []) + 9 + a.conc * a.conc_each + 40 + 60
    rpc_n = 2 * n_b + 3 * len(reg.get("species") or []) + 4 + 12
    cx_n = 9 + 12
    est = 300 + http_n * 0.25 + rpc_n * 1.5 + cx_n * 2 + 40
    memo["estimate"] = (est, http_n, rpc_n, cx_n)
    log(f"== plan: {n_ctl} controls ({dict(types)}) in {n_b} batches, {len(reg.get('species') or [])} species rows, {len(reg.get('actions') or [])} actions, "
        f"{len(reg.get('readouts') or [])} readouts; value generation clean for {n_ok}/{n_ctl}")
    log(f"== estimate on the rig: ~{http_n} HTTP requests, ~{rpc_n} RPCs, ~{cx_n} cx-lifecycle calls -> about {est / 60:.0f} min "
        f"(restore+load+title ~5 min, 0.25 s per request, 1.5 s per RPC)")
    acts = reg.get("actions") or []
    unk = [x["id"] for x in acts if x["id"] not in set(SAFE + DRAWS + DESTRUCTIVE)]
    rec("plan.actions", "PASS" if not unk else "FAIL", f"order: safe {SAFE}; draws {DRAWS}; destructive last {DESTRUCTIVE}; unclassified {unk}")

# =============================================================================================== main
def main():
    global MODE, WPORT, OUT, _log, DEADLINE
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="no rig: plan and value generation against the offline registry")
    ap.add_argument("--mock", action="store_true", help="with --dry-run: start tests/web/mock_server.py and run the HTTP phases against it")
    ap.add_argument("--mock-port", type=int, default=8790)
    ap.add_argument("--no-restore", action="store_true", help="test the fort already loaded; no restore, no load, no save diff")
    ap.add_argument("--phases", help="comma-separated subset of " + ",".join(PHASES))
    ap.add_argument("--only-controls", help="regex on control ids for the ctl phase")
    ap.add_argument("--batch", type=int, default=10, help="controls per console read-back batch")
    ap.add_argument("--conc", type=int, default=8, help="parallel clients in conc")
    ap.add_argument("--conc-each", type=int, default=10, help="GETs per client in conc")
    ap.add_argument("--irr-cavern", help="cavern (1-3) for the irruption actions; default the first one the fort reached")
    ap.add_argument("--no-destructive", action="store_true", help="skip the destructive actions")
    ap.add_argument("--browser", action="store_true", help="leave the server serving and the fort loaded at the end")
    ap.add_argument("--budget-min", type=float, default=50.0, help="wall-time budget; the end phase still runs")
    a = ap.parse_args()
    if a.mock and not a.dry_run:
        print("--mock needs --dry-run", file=sys.stderr); return 2
    MODE = "mock" if a.mock else "dry" if a.dry_run else "live"
    OUT = ROOT / "data" / "web-live" / (RUN + ("" if MODE == "live" else "-" + MODE))
    OUT.mkdir(parents=True, exist_ok=True)
    _log = open(OUT / "log.txt", "w")
    DEADLINE = T0 + a.budget_min * 60
    phases = [p.strip() for p in a.phases.split(",")] if a.phases else PHASES
    bad = [p for p in phases if p not in PHASES]
    if bad:
        print(f"unknown phase(s) {bad}; known: {PHASES}", file=sys.stderr); return 2
    log(f"== web-live {RUN} ({MODE}): phases {phases}; out {OUT}")
    mock = None
    rc_setup = 0
    try:
        try:
            reg = offline_registry()
            memo["offline_reg"] = reg
        except Exception as e:
            reg = None
            log(f"   offline registry unavailable: {e}")
        if MODE == "dry":
            if not reg:
                rec("plan.registry", "FAIL", "lua tests/web/harness.lua <repo> registry did not run"); rc_setup = 2
            else:
                memo["ctl"] = reg
                rec("plan.registry", "PASS", f"offline registry: {len(reg['controls'])} controls, {len(reg['sections'])} sections, {len(reg['species'])} species rows, "
                    f"{len(reg['actions'])} actions, {len(reg['readouts'])} readouts")
                dry_plan(a, reg)
            return finish(a, rc_setup)
        if MODE == "mock":
            WPORT = a.mock_port
            mock = subprocess.Popen([sys.executable, str(TOOL_REPO / "tests/web/mock_server.py"), str(WPORT)], cwd=TOOL_REPO,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for _ in range(60):
                time.sleep(0.25)
                if mock.poll() is not None:
                    break
                try:
                    socket.create_connection(("127.0.0.1", WPORT), timeout=0.5).close(); break
                except OSError:
                    pass
            log(f"   mock server pid {mock.pid} on {WPORT}")
            if reg:
                dry_plan(a, reg)
        memo["phase"] = "session"
        if not phase_session(a):
            rc_setup = 2
            log("== the server is not reachable; the HTTP phases cannot run")
            for p in phases:
                rec(f"{p}.not_run", "NOT-TESTABLE", "the session did not start (see session rows)", phase=p)
        else:
            if MODE == "live":
                rc, out, err = sh("cmd", "seasonal-wildlife-web", "status", timeout=60)
                m = re.search(r"errors (\d+)[),]", out)
                memo["web_errors0"] = int(m.group(1)) if m else None
            if "get" not in phases:          # the shape checks feed state and controls to the later phases
                memo["state"] = state_json(); memo["ctl"] = ctl_json()
            fns = {"get": phase_get, "sec": phase_sec, "ctl": phase_ctl, "species": phase_species, "read": phase_read,
                   "cmd": phase_cmd, "conc": phase_conc, "mal": phase_mal, "act": phase_act}
            stop = None
            for p in PHASES:
                if p not in phases:
                    continue
                memo["phase"] = p
                if stop:
                    rec(f"{p}.not_run", "NOT-TESTABLE", stop); continue
                log(f"== phase {p}")
                t = time.time()
                try:
                    fns[p](a)
                except OutOfTime as e:
                    rec(f"{p}.budget", "NOT-TESTABLE", f"stopped: {e}"); stop = str(e)
                except ServerDown as e:
                    rec(f"{p}.server_down", "FAIL", f"the server stopped answering: {e}"); stop = f"the server stopped answering in {p}"
                except Exception as e:
                    rec(f"{p}.driver", "FAIL", f"the driver failed: {type(e).__name__}: {e} | {traceback.format_exc()[-600:]}")
                log(f"   phase {p}: {time.time() - t:.1f}s")
    finally:
        try:
            if MODE == "live":
                phase_end(a)
        finally:
            if mock:
                mock.terminate()
                try:
                    mock.wait(5)
                except Exception:
                    mock.kill()
                log(f"   mock server stopped (rc {mock.returncode})")
    return finish(a, rc_setup)

def finish(a, rc_setup):
    wall = time.time() - T0
    try:
        browser_checklist(a)
    except Exception as e:
        log(f"   checklist failed: {e}")
    (OUT / "results.json").write_text(json.dumps({"run": RUN, "mode": MODE, "wall_s": round(wall, 1), "stats": dict(STATS),
                                                  "estimate": memo.get("estimate"), "rows": results}, indent=1, default=str))
    report(a, wall)
    t = Counter(r["verdict"] for r in results)
    log(f"== DONE {OUT} in {wall / 60:.1f} min: {len(results)} rows; PASS {t['PASS']}, FAIL {t['FAIL']}, NOT-TESTABLE {t['NOT-TESTABLE']}")
    if rc_setup:
        return rc_setup
    return 1 if t["FAIL"] else 0

if __name__ == "__main__":
    sys.exit(main())
