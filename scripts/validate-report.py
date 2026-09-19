#!/usr/bin/env python3
"""Build the seasonal-wildlife playtest report as one self-contained HTML page.

Reads a validate-full run (results.json, claims.json, shots/, screens/, ground/) and, when
present, the E37/E38 tallies, and writes an HTML file with every screenshot inlined as a
JPEG data URI so the page can be published as a single artifact.

Usage: validate-report.py [run_dir] [-o out.html]
"""
import base64, html, json, sys
from pathlib import Path
from collections import OrderedDict

ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("-o")]
run_dir = Path(args[0]) if args else sorted((ROOT / "data/validation/full").glob("*"))[-1]
out_path = Path(sys.argv[sys.argv.index("-o") + 1]) if "-o" in sys.argv else ROOT / ".claude/scratch/seasonal-wildlife-playtest.html"

results = json.loads((run_dir / "results.json").read_text())
claims = json.loads((run_dir / "claims.json").read_text())
log = (run_dir / "log.txt").read_text(errors="replace") if (run_dir / "log.txt").exists() else ""

def esc(s):
    return html.escape(str(s) if s is not None else "")

def img(rel):
    p = run_dir / rel
    if not p.exists():
        return ""
    mime = "image/jpeg" if p.suffix == ".jpg" else "image/png"
    b = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b}"

def screen_txt(name):
    p = run_dir / "screens" / f"{name}.txt"
    return p.read_text(errors="replace") if p.exists() else ""

def ground(name):
    p = run_dir / "ground" / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else {}

VERDICTS = ["PASS", "FAIL", "DEAD", "DOC-DRIFT", "UNWIRED", "NOT-TESTABLE-HERE", "BACKLOG"]
# bar segments are ordered so the two hues a deutan reader finds closest (green, red) are never neighbours
BAR_ORDER = ["PASS", "DOC-DRIFT", "FAIL", "UNWIRED", "DEAD", "NOT-TESTABLE-HERE", "BACKLOG"]
VCLASS = {"PASS": "v-pass", "FIXED": "v-pass", "FAIL": "v-fail", "DEAD": "v-dead", "DOC-DRIFT": "v-drift",
          "UNWIRED": "v-unwired", "NOT-TESTABLE-HERE": "v-nt", "BACKLOG": "v-backlog"}
VGLOSS = {
    "PASS": "did what was claimed; receipt and ground truth attached",
    "FAIL": "claimed shipped, exercised on the rig, did not do it",
    "DEAD": "present in the code and inert — stores a number, prints a line, moves nothing",
    "DOC-DRIFT": "the documentation contradicts the shipped code",
    "UNWIRED": "promised in a plan or report; no code behind it",
    "NOT-TESTABLE-HERE": "needs a condition one session cannot manufacture; the experiment that measured it is cited",
    "BACKLOG": "explicitly unscheduled; recorded so nothing promised is missing from this page",
}

# ---- group results by section, one row per result (a claim can have several)
SECTIONS = OrderedDict([
    ("summary", "Summary"), ("cli", "Console"), ("mech", "Mechanics"), ("gui", "The window"),
    ("water", "Water layer"), ("v6", "Unwired views"), ("plan", "Unbuilt packages"),
    ("doc", "Documentation drift"), ("bl", "Backlog"), ("perf", "What it costs"), ("method", "Method"),
])
def section_of(r):
    cid = r["id"]
    if cid.startswith("cli."): return "cli"
    if cid.startswith("gui."): return "gui"
    if cid.startswith("mech.water") or cid == "cli.water": return "water"
    if cid.startswith("mech."): return "mech"
    if cid.startswith("v6."): return "v6"
    if cid.startswith("plan."): return "plan"
    if cid.startswith("doc."): return "doc"
    if cid.startswith("bl."): return "bl"
    return "mech"
by_sec = {k: [] for k in SECTIONS}
for r in results:
    by_sec[section_of(r)].append(r)

tally = {v: 0 for v in VERDICTS}
per_claim = OrderedDict()
for r in results:
    per_claim.setdefault(r["id"], []).append(r)
# a claim's verdict is its worst row
ORDER = {"FAIL": 0, "DEAD": 1, "DOC-DRIFT": 2, "UNWIRED": 3, "PASS": 4, "NOT-TESTABLE-HERE": 5, "BACKLOG": 6}
claim_verdict = {cid: sorted((r["verdict"] for r in rows), key=lambda v: ORDER.get(v, 9))[0] for cid, rows in per_claim.items()}
for v in claim_verdict.values():
    tally[v] = tally.get(v, 0) + 1
surf_tally = {}
for cid, v in claim_verdict.items():
    s = per_claim[cid][0]["surface"]
    surf_tally.setdefault(s, {vv: 0 for vv in VERDICTS})[v] += 1

def chip(v):
    return f'<span class="chip {VCLASS.get(v, "v-nt")}">{esc(v)}</span>'

def kv_table(data):
    if not data:
        return ""
    if isinstance(data, dict):
        rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(json.dumps(v) if isinstance(v, (dict, list)) else v)}</td></tr>" for k, v in data.items())
        return f'<div class="scroll"><table class="kv">{rows}</table></div>'
    if isinstance(data, list):
        return f'<div class="scroll"><pre class="mono small">{esc(json.dumps(data, indent=1)[:2500])}</pre></div>'
    return f'<pre class="mono small">{esc(data)}</pre>'

def receipt(r):
    shots = "".join(
        f'<figure><img src="{img(s)}" alt="{esc(Path(s).stem)}" loading="lazy"><figcaption>{esc(Path(s).stem)}</figcaption></figure>'
        for s in r.get("shots", []) if img(s))
    got = r.get("got", "")
    note = f'<p class="note">{esc(r["note"])}</p>' if r.get("note") else ""
    return f"""
<article class="receipt {VCLASS.get(r['verdict'], 'v-nt')}" id="{esc(r['id'])}">
  <header>
    {chip(r['verdict'])}
    <h4>{esc(r['claim'])}</h4>
    <div class="meta"><span class="mono">{esc(r['id'])}</span> · claimed in <em>{esc(r['source'])}</em> · as <em>{esc(r['claimed'])}</em></div>
  </header>
  <dl class="eg">
    <dt>Expected</dt><dd>{esc(r['expected'])}</dd>
    {'<dt>Got</dt><dd><pre class="mono small">' + esc(got) + '</pre></dd>' if got else ''}
  </dl>
  {note}
  {kv_table(r.get('data'))}
  {'<div class="shots">' + shots + '</div>' if shots else ''}
</article>"""

def section_html(key, intro=""):
    rows = by_sec.get(key, [])
    if not rows:
        return ""
    # worst first inside a section, then by id
    rows = sorted(rows, key=lambda r: (ORDER.get(r["verdict"], 9), r["id"]))
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    strip = " ".join(f'{chip(v)}<span class="n">{n}</span>' for v, n in sorted(counts.items(), key=lambda x: ORDER.get(x[0], 9)))
    return f"""
<section id="{key}">
  <h2>{esc(SECTIONS[key])}</h2>
  <div class="strip">{strip}</div>
  {intro}
  {''.join(receipt(r) for r in rows)}
</section>"""

# ---- ground truth summaries
g0 = ground("A0-baseline"); gl = ground("D0-lake-baseline"); gl1 = ground("D1-lake-after-water-now")
def units_table(g, cap=14):
    if not g or not g.get("units"):
        return "<p class='muted'>no wild units recorded</p>"
    agg = {}
    for u in g["units"]:
        k = (u.get("token"), u.get("layer"))
        agg[k] = agg.get(k, 0) + 1
    rows = "".join(f"<tr><td class='mono'>{esc(t)}</td><td>{esc(l)}</td><td class='num'>{n}</td></tr>"
                   for (t, l), n in sorted(agg.items(), key=lambda x: -x[1])[:cap])
    return f"""<div class="scroll"><table class="data"><thead><tr><th>species</th><th>layer</th><th class="num">on map</th></tr></thead><tbody>{rows}</tbody></table></div>"""

def ground_card(title, g):
    if not g:
        return ""
    return f"""
<div class="gcard">
  <h4>{esc(title)}</h4>
  <div class="gfacts">
    <span>year {esc(g.get('year'))} · tick {esc(g.get('tick'))} · season {esc(g.get('season'))}</span>
    <span>citizens {esc(g.get('citizens'))}</span>
    <span>land {esc(g.get('land'))} · water {esc(g.get('water'))} · cavern {esc(g.get('cavern'))} · deep {esc(g.get('deep'))}</span>
    <span>tool {'on' if g.get('enabled') else 'off'} · scheduler {'registered' if g.get('sched') else 'idle'} · groups {'on' if g.get('groups') else 'off'} · ecology {'on' if g.get('ecology') else 'off'}</span>
    <span>{esc(g.get('allowed'))} allowed · {esc(g.get('assigned'))} with seasons</span>
  </div>
  {units_table(g)}
</div>"""

# ---- the two experiments, if their tallies exist
def tally_text(exp):
    dirs = sorted(d for d in (ROOT / "data/experiments" / exp).glob("*") if "VACUOUS" not in d.name)
    for d in reversed(dirs):
        t = d / "tally.txt"
        if t.exists():
            return d.name, t.read_text(errors="replace")
    return None, ""
e37_run, e37 = tally_text("E37"); e38_run, e38 = tally_text("E38")

# ---- stat tiles and per-surface bars
n_claims = len(claim_verdict)
tiles = "".join(f'<div class="tile {VCLASS[v]}"><div class="big">{tally.get(v, 0)}</div><div class="lab">{esc(v)}</div><div class="gloss">{esc(VGLOSS[v])}</div></div>'
                for v in VERDICTS)
def bar(surface, counts):
    total = sum(counts.values()) or 1
    segs = "".join(f'<span class="seg {VCLASS[v]}" style="width:{100*counts[v]/total:.1f}%" title="{v} {counts[v]}"></span>'
                   for v in BAR_ORDER if counts[v])
    labs = " · ".join(f"{v} {counts[v]}" for v in BAR_ORDER if counts[v])
    return f'<div class="barrow"><div class="barlab">{esc(surface)} <span class="muted">{total}</span></div><div class="bar">{segs}</div><div class="barlegend mono">{esc(labs)}</div></div>'
bars = "".join(bar(s, c) for s, c in sorted(surf_tally.items()))

fails = [cid for cid, v in claim_verdict.items() if v == "FAIL"]
deads = [cid for cid, v in claim_verdict.items() if v == "DEAD"]
drifts = [cid for cid, v in claim_verdict.items() if v == "DOC-DRIFT"]
unwired = [cid for cid, v in claim_verdict.items() if v == "UNWIRED"]
def cid_link(cid):
    return f'<a href="#{esc(cid)}" class="mono">{esc(cid)}</a>'

headline = (f"{tally['PASS']} of the {tally['PASS'] + tally['FAIL'] + tally['DEAD']} claims that ship today did what they said on the rig"
            + (f"; {tally['FAIL']} failed" if tally['FAIL'] else "; none failed")
            + (f"; {tally['DEAD']} is present and inert" if tally['DEAD'] == 1 else (f"; {tally['DEAD']} are present and inert" if tally['DEAD'] else ""))
            + f". {tally['UNWIRED']} promised views and packages have no code behind them, {tally['DOC-DRIFT']} documents contradict the code, and {tally['BACKLOG']} backlog items are recorded so nothing promised is missing.")

run_id = run_dir.name
summary = f"""
<section id="summary">
  <p class="eyebrow">Functional playtest · seasonal-wildlife v5.8.5 · DF 53.16 / DFHack 53.16-r1.1 · run {esc(run_id)}</p>
  <h1>Seasonal Wildlife Playtest</h1>
  <p class="lede">{esc(headline)}</p>
  <div class="tiles">{tiles}</div>
  <h3>By surface</h3>
  <div class="bars">{bars}</div>
  <div class="cols">
    <div>
      <h3>What failed or is inert</h3>
      <ul class="plain">{''.join(f"<li>{chip('FAIL')} {cid_link(c)} — {esc(per_claim[c][0]['claim'])}</li>" for c in fails) or '<li class="muted">nothing exercised failed</li>'}
      {''.join(f"<li>{chip('DEAD')} {cid_link(c)} — {esc(per_claim[c][0]['claim'])}</li>" for c in deads)}</ul>
    </div>
    <div>
      <h3>Documentation that contradicts the code</h3>
      <ul class="plain">{''.join(f"<li>{cid_link(c)} — {esc(per_claim[c][0]['claim'])}</li>" for c in drifts) or '<li class="muted">none</li>'}</ul>
    </div>
  </div>
  <h3>Promised, not built</h3>
  <p class="muted">The design report's §11 draws thirteen views and PLAN §3.5–3.6b schedules three packages. The window ships five tabs. Each of these is listed below with the identifier search that proved it absent.</p>
  <ul class="plain wrap">{''.join(f"<li>{cid_link(c)}</li>" for c in unwired)}</ul>
  <h3>The fort, as found</h3>
  <div class="gcards">{ground_card('CTRL at load — the inland fort every console and window check ran on', g0)}{ground_card('LAKE at load — the one fort where the water layer is live', gl)}</div>
</section>"""

perf = ""
if e37 or e38:
    perf = f"""
<section id="perf">
  <h2>What it costs</h2>
  <p>Two experiments, both with the save byte-identical afterwards. E37 crossed tool-on against tool-off at two load levels between rig loads and could only <em>bound</em> the cost, because identical replicates disagree by 10–16%. E38 toggled the jobs in alternating 8,000-tick blocks inside one replicate so both phases share a load, with a sham arm that never toggles.</p>
  {'<h3>E37 · ' + esc(e37_run) + '</h3><pre class="mono small scroll">' + esc(e37) + '</pre>' if e37 else ''}
  {'<h3>E38 · ' + esc(e38_run) + '</h3><pre class="mono small scroll">' + esc(e38) + '</pre>' if e38 else ''}
</section>"""

method = f"""
<section id="method">
  <h2>Method</h2>
  <p>The claim set is everything the tool has been said to do: <em>USAGE.md</em>, the script's own docstring, the design report (§2 capability list, §5 work packages, §11 the thirteen views), <em>PLAN.md</em> §1 and §3.5–3.6b, the Wildlife Backlog and the Fortress Docket — {n_claims} claims. Each was exercised on the live rig by <code>scripts/validate-full.py</code>: console verbs by their receipts, the window by feeding its own hotkeys and reading the text grid back, mechanics by a Lua probe of the game state before and after (pool quantities, units on the map by species and layer, leave countdowns, the reaction cache, leader flags), and anything visible by a PNG of the DF window. Screenshots are the actual 1920×1080 window, reduced to 1280 wide.</p>
  <p>Verdicts are one of seven words, each with a fixed meaning: {' · '.join(f'<strong>{esc(v)}</strong> {esc(VGLOSS[v])}' for v in VERDICTS)}.</p>
  <p>Ticks are the game's own clock: 1,200 to a day, 100,800 to a season. A step of 3,000 ticks is two and a half days. The rig was left at the title and both forts restored from their <code>.preverify</code> backups; <code>diff -rq</code> against the backup is itself a check (<a href="#mech.save.untouched" class="mono">mech.save.untouched</a>).</p>
  <details><summary>Run log</summary><pre class="mono small scroll">{esc(log[-12000:])}</pre></details>
</section>"""

# ---- hand-driven findings, written by the operator during the playtest
narr = json.loads((run_dir / "narrative.json").read_text()) if (run_dir / "narrative.json").exists() else []
def narr_html(n):
    shots = "".join(f'<figure><img src="{img(s)}" alt="{esc(Path(s).stem)}" loading="lazy"><figcaption>{esc(Path(s).stem)}</figcaption></figure>' for s in n.get("shots", []) if img(s))
    links = " ".join(f'<a href="#{esc(c)}" class="mono">{esc(c)}</a>' for c in n.get("claims", []))
    return f"""<article class="receipt {VCLASS.get(n.get('verdict', 'PASS'), 'v-nt')}"><header>{chip(n.get('verdict', 'PASS'))}<h4>{esc(n['title'])}</h4><div class="meta">{links}</div></header><p class="narr">{esc(n['text'])}</p>{'<div class="shots">' + shots + '</div>' if shots else ''}</article>"""
hand = ""
if narr:
    hand = f"""
<section id="hand">
  <h2>Driven by hand</h2>
  <p class="muted">What the scripted checks could not settle was driven by hand on the rig — one key, one screen read, one probe of the game at a time (the logs are in <code>hand/</code>). These are the findings that came from that, with the screenshots that proved them.</p>
  {''.join(narr_html(n) for n in narr)}
</section>"""
SECTIONS["hand"] = "Driven by hand"

nav_order = [k for k in SECTIONS if k != "hand"]; nav_order.insert(1, "hand")   # the hand-driven findings sit right after the summary
nav = "".join(f'<a href="#{k}">{esc(SECTIONS[k])}</a>' for k in nav_order if (k in ("summary", "method") or by_sec.get(k) or (k == "perf" and perf) or (k == "hand" and hand)))

page = f"""<title>Seasonal Wildlife Playtest</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{{
  --bg:#F1F3EE; --ink:#1C2321; --muted:#5D6B66; --rule:#D3D8D2; --panel:#FAFBF8; --accent:#0E7C86; --accent-ink:#0B5F67;
  --pass:#1F8A57; --fail:#C43A2E; --dead:#B5680C; --drift:#6E48B8; --nt:#6B7A75; --unwired:#4A5652; --backlog:#9AA6A1;
  --pass-bg:#E3F1E9; --fail-bg:#F6E3E0; --dead-bg:#F5EAD8; --drift-bg:#ECE5F6; --nt-bg:#E8ECEA; --unwired-bg:#E4E8E6; --backlog-bg:#EEF0EE;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace; --sans:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif; --disp:"Spectral",Georgia,"Times New Roman",serif;
  color-scheme:light;
}}
@media (prefers-color-scheme: dark){{ :root:not([data-theme="light"]){{
  --bg:#101614; --ink:#E4E9E4; --muted:#93A19B; --rule:#243029; --panel:#161D1A; --accent:#5CD3DD; --accent-ink:#8FE3EA;
  --pass:#33A56A; --fail:#E05A4A; --dead:#BD7E14; --drift:#A47CE6; --nt:#8E9C97; --unwired:#A9B5B0; --backlog:#6B7873;
  --pass-bg:#15291E; --fail-bg:#2E1815; --dead-bg:#2C2113; --drift-bg:#221A32; --nt-bg:#1C2421; --unwired-bg:#1A2320; --backlog-bg:#151B19;
  color-scheme:dark;
}} }}
:root[data-theme="dark"]{{
  --bg:#101614; --ink:#E4E9E4; --muted:#93A19B; --rule:#243029; --panel:#161D1A; --accent:#5CD3DD; --accent-ink:#8FE3EA;
  --pass:#33A56A; --fail:#E05A4A; --dead:#BD7E14; --drift:#A47CE6; --nt:#8E9C97; --unwired:#A9B5B0; --backlog:#6B7873;
  --pass-bg:#15291E; --fail-bg:#2E1815; --dead-bg:#2C2113; --drift-bg:#221A32; --nt-bg:#1C2421; --unwired-bg:#1A2320; --backlog-bg:#151B19;
  color-scheme:dark;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 var(--sans);-webkit-font-smoothing:antialiased}}
a{{color:var(--accent-ink)}} a:focus-visible,button:focus-visible,summary:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
.wrap{{display:grid;grid-template-columns:200px minmax(0,1fr);gap:40px;max-width:1180px;margin:0 auto;padding:32px 24px 80px}}
nav{{position:sticky;top:24px;align-self:start;display:flex;flex-direction:column;gap:6px;font-size:14px}}
nav a{{text-decoration:none;color:var(--muted);padding:4px 0;border-left:2px solid transparent;padding-left:10px}}
nav a:hover{{color:var(--ink);border-left-color:var(--accent)}}
main{{min-width:0}}
h1{{font:600 44px/1.05 var(--disp);letter-spacing:-.01em;margin:6px 0 14px;text-wrap:balance}}
h2{{font:600 30px/1.15 var(--disp);margin:56px 0 12px;padding-top:24px;border-top:1px solid var(--rule);text-wrap:balance}}
h3{{font:500 20px/1.25 var(--disp);margin:28px 0 10px}}
h4{{font:600 16px/1.35 var(--sans);margin:0;text-wrap:balance}}
p{{max-width:68ch}} .lede{{font-size:19px;line-height:1.5;max-width:66ch}}
.eyebrow{{font:500 12px/1.4 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:0}}
.muted{{color:var(--muted)}} .mono{{font-family:var(--mono)}} .small{{font-size:12.5px;line-height:1.45}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:22px 0 8px}}
.tile{{background:var(--panel);border:1px solid var(--rule);border-top:3px solid var(--vc);padding:12px 12px 10px}}
.tile .big{{font:600 34px/1 var(--disp);font-variant-numeric:tabular-nums;color:var(--vc)}}
.tile .lab{{font:500 11px/1.3 var(--mono);letter-spacing:.06em;text-transform:uppercase;margin-top:6px}}
.tile .gloss{{font-size:12px;color:var(--muted);margin-top:4px;line-height:1.35}}
.v-pass{{--vc:var(--pass);--vbg:var(--pass-bg)}} .v-fail{{--vc:var(--fail);--vbg:var(--fail-bg)}} .v-dead{{--vc:var(--dead);--vbg:var(--dead-bg)}}
.v-drift{{--vc:var(--drift);--vbg:var(--drift-bg)}} .v-nt{{--vc:var(--nt);--vbg:var(--nt-bg)}} .v-unwired{{--vc:var(--unwired);--vbg:var(--unwired-bg)}} .v-backlog{{--vc:var(--backlog);--vbg:var(--backlog-bg)}}
.chip{{display:inline-block;font:500 11px/1 var(--mono);letter-spacing:.05em;padding:5px 8px;border-radius:3px;color:var(--vc);background:var(--vbg);border:1px solid color-mix(in oklab,var(--vc) 35%,transparent);white-space:nowrap}}
.strip{{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;margin:0 0 14px}} .strip .n{{font:500 13px var(--mono);color:var(--muted);margin-left:-6px}}
.bars{{display:grid;gap:10px;margin:8px 0 6px}}
.barrow{{display:grid;grid-template-columns:110px 1fr;gap:4px 14px;align-items:center}}
.barlab{{font:500 14px var(--sans)}} .bar{{display:flex;height:14px;gap:2px;background:transparent}}
.seg{{display:block;height:100%;background:var(--vc);border-radius:2px;min-width:3px}}
.barlegend{{grid-column:2;font-size:11.5px;color:var(--muted)}}
.cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}}
ul.plain{{list-style:none;padding:0;margin:0;display:grid;gap:8px}} ul.plain li{{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;font-size:14.5px}}
ul.wrap{{grid-template-columns:repeat(auto-fill,minmax(180px,1fr))}}
.gcards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}}
.gcard{{background:var(--panel);border:1px solid var(--rule);padding:14px 16px}} .gcard h4{{margin-bottom:8px}}
.gfacts{{display:flex;flex-wrap:wrap;gap:4px 14px;font:13px var(--mono);color:var(--muted);margin-bottom:10px}}
.receipt{{border-left:3px solid var(--vc);padding:14px 18px 16px;margin:14px 0;background:var(--panel);border-top:1px solid var(--rule);border-right:1px solid var(--rule);border-bottom:1px solid var(--rule)}}
.receipt header{{display:grid;grid-template-columns:auto 1fr;gap:6px 12px;align-items:start}}
.receipt header h4{{grid-column:2}} .receipt .meta{{grid-column:2;font-size:12.5px;color:var(--muted)}}
dl.eg{{display:grid;grid-template-columns:84px 1fr;gap:6px 12px;margin:12px 0 0;font-size:14px}}
dl.eg dt{{font:500 11px/1.9 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}} dl.eg dd{{margin:0;min-width:0}}
pre{{margin:0;white-space:pre-wrap;word-break:break-word}} pre.mono{{background:color-mix(in oklab,var(--ink) 5%,transparent);padding:8px 10px;border-radius:3px}}
.note{{font-size:13.5px;color:var(--muted);margin:10px 0 0;max-width:80ch}} .narr{{margin:12px 0 0;max-width:78ch;font-size:15px}}
.scroll{{overflow-x:auto;max-width:100%}} table{{border-collapse:collapse;font-size:13px;margin-top:10px}}
table.kv th{{text-align:left;font:500 11.5px var(--mono);color:var(--muted);padding:3px 12px 3px 0;vertical-align:top;white-space:nowrap}} table.kv td{{padding:3px 0;font-family:var(--mono);font-size:12.5px;word-break:break-word}}
table.data th,table.data td{{padding:4px 10px 4px 0;border-bottom:1px solid var(--rule);text-align:left}} table.data th{{font:500 11px var(--mono);letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}}
.shots{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin-top:14px}}
figure{{margin:0}} figure img{{width:100%;height:auto;display:block;border:1px solid var(--rule);background:#000}}
figcaption{{font:12px var(--mono);color:var(--muted);margin-top:4px}}
details summary{{cursor:pointer;color:var(--accent-ink)}}
code{{font-family:var(--mono);font-size:.92em}}
@media (max-width:820px){{.wrap{{grid-template-columns:1fr;gap:16px}} nav{{position:static;flex-direction:row;flex-wrap:wrap;gap:4px 12px}} h1{{font-size:34px}}}}
@media (prefers-reduced-motion: reduce){{*{{scroll-behavior:auto}}}}
</style>
<div class="wrap">
<nav>{nav}</nav>
<main>
{summary}
{hand}
{section_html('cli', '<p class="muted">Every verb in the dispatch table and every sub-command, asserted on the receipt it prints rather than on an exit code. Error paths are exercised too — a bad argument must print a usage line and change nothing.</p>')}
{section_html('mech', '<p class="muted">Each mechanic is read from the game itself before and after: pool quantities by species and layer, wild units on the map by id, leave countdowns, the reaction-cache write count, cavern creature frequencies, the leader chosen for a group. Where a mechanic needs a season boundary or a stationary animal for 5,000 ticks, the experiment that measured it is cited instead of a hollow pass.</p>')}
{section_html('gui', '<p class="muted">Driven with the window’s own hotkeys, exactly as a player would press them: each one is followed by a read of the text grid and, where the change lives in the config or the pool, a Lua probe. Screenshots are the DF window at that moment.</p>')}
{section_html('water', '<p class="muted">CTRL is inland, so the water layer is dormant there and must say why. LAKE is the fort where it is live: the water job places, and the placed animals are on the map afterwards.</p>')}
{section_html('v6', '<p class="muted">Each of these was searched for in the shipped script by the identifiers a built view would carry (a tab label, a refresh function, a hotkey binding). The only hits for <code>undo</code>, <code>ledger</code> and <code>Herds</code> are comments; <code>Vermin</code> is a population type.</p>')}
{section_html('plan')}
{section_html('doc')}
{section_html('bl', '<p class="muted">The Backlog says none of these is scheduled. They are here so the page holds every promise made anywhere, not only the ones that were supposed to be kept by now.</p>')}
{perf}
{method}
</main>
</div>
"""
out_path.parent.mkdir(parents=True, exist_ok=True)
page = page.replace("\ufffd", "&#xFFFD;")   # a replacement char from a lossy screen dump is written as an entity, not the raw code point
out_path.write_text(page)
print(f"wrote {out_path} ({out_path.stat().st_size/1e6:.1f} MB) from {run_dir}; claims {n_claims}; " + " ".join(f"{k} {v}" for k, v in tally.items() if v))
