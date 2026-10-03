"""Build the Alpha Four Progress page: overall status, the section-7 breakdown (summary rows and per-row detail read from
data/alpha4-sec7/SECTION7-RESULTS.md), what is running, and the pending work. Output: data/alpha4-progress/alpha4-progress.html"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "eco-report"))
import mdlite  # noqa: E402

RES = (ROOT / "data/alpha4-sec7/SECTION7-RESULTS.md").read_text()
OUT = ROOT / "data/alpha4-progress/alpha4-progress.html"
AS_OF = None   # None: the build time

E = html.escape


def summary_rows():
    rows = {}
    for ln in RES.splitlines():
        m = re.match(r"^\| (\d+) \| (.*?) \| (.*?) \| (.*) \|$", ln)
        if m:
            rows[int(m.group(1))] = (m.group(2), m.group(3), m.group(4))
    return rows


def per_row_sections():
    """'### N. Title' blocks of the Per row section, keyed by every row number in the heading."""
    body = RES.split("## Per row", 1)[1].split("## Not testable here", 1)[0]
    out = {}
    for part in re.split(r"(?m)^### ", body)[1:]:
        head, _, text = part.partition("\n")
        nums = [int(n) for n in re.findall(r"\d+", head.split(".")[0] if "." in head else head)]
        nums = nums or [int(n) for n in re.findall(r"^\d+", head)]
        for n in nums:
            out.setdefault(n, []).append((head.strip(), text))
    return out


def inl(s):
    # claim globs like `gui.*` are names, not emphasis: shield the asterisk from the italic rule
    s = re.sub(r"(\w)\.\*", r"\1.ASTERISKPH", s.replace("<br>", " • "))
    return mdlite.inline(s).replace("ASTERISKPH", "*")


# Status since the tally (the lead's knowledge, 2 Oct 16:00): state chip, what changed, what remains.
SINCE = {
    1: ("done", "Re-run on the Alpha Four fixes (69e97a1) with the wolves moved away from the cougars and the sneak bonus zeroed.",
        "Nothing for the core check. A DF-drawn wave inheriting the skill is a FULL-tier run."),
    2: ("partial", "Packs confirmed. STP1 on the release candidate placed the fort's own GIANT_OSPREY beside prey: it hunts in "
        "both arms (6.0 v 6.4 attacks, 2.6 v 2.6 kills of 9 per cell, p = 0.78) -- the stoop switch adds nothing over the "
        "ecology write. The earlier eagles never engaged because the tool only acts on pool species.",
        "FSH3/FSH4 are NOT-TESTABLE on RinghatchetsReady: no fishing species in its pool. Needs a region10 fort whose pool has bears."),
    3: ("done", "Land overshoot partly a tool bug: after one release, gate_drain released up to 8 more held groups. Fixed in "
        "f3c8d11 (stops at the cap); the status now says how far over and who brought the groups. DF still sends a wave per "
        "border source. S7_NAT on the release candidate: land groups 9.65 v cap 9 (was 10.79), over the cap in 54% of "
        "samples (was 84%).", "Nothing: you accepted 9.65 v 9 (the residual is DF's per-border waves)."),
    4: ("fixed", "You ruled yes: groups cavern trim_gated (default ON, 30873d4) also sends off the oldest DF wave when no "
        "resident group is left. TRIM re-designed to place 3 resident groups over cap 1.",
        "TRIM PENDING: in the RC chain it aborted at its receipt (only 1 of 3 placed groups was adopted as resident), so "
        "it was skipped, not re-fixed. The trim_gated rig check waits on the same harness fix, after this round."),
    5: ("open", "No detectable scatter from a lost leader at n = 5 (25.9 v 20.7 tiles, p = 0.33).",
        "Decide: a larger n, a different measure (time to regroup), or accept as no effect."),
    6: ("fixed", "CRAZED / MISCHIEVOUS / NOFEAR never stuck: DF rebuilds those flags from wounds. 594cc9d carries them on a "
        "body-less wound (save-safe, default) or a runtime syndrome. Irruptions now admit out-of-season civ races (69e97a1). "
        "R35 cap set to 2 so it bites.", "Rig check that the flags read 1 after 20 t, survive save + reload, and read 0 after "
        "the end. IRRM / IRRP2 / IRRR35 re-run in the RC chain."),
    7: ("done", "Both halves confirmed.", "Nothing."),
    8: ("partial", "VF4 tallied: too few fish vermin near the bank to read (1-3 per cell; forage on 5 to 3, off 7 to 8 "
        "summed over 5 cells). VF1 re-designed with a gobble receipt; runs in the RC chain.",
        "VF1 result from the chain. VF4 PENDING (inconclusive: too few fish vermin), not re-run this round."),
    9: ("explained", "No defect. Apex presence 0.17 is what a one-month run predicts (expected 0.17, none placed in 0.48 of "
        "runs). The carnivore share read 0.05 because 93% of 'land' units were ravens from the flying pool.",
        "S7_NAT on the release candidate: apex presence 0.11 v 0 without the tool (p = 0.048); carnivore share 0.036 v "
        "0.004 (p = 0.09); the ladder reaches the raws for every open key. Walking land units averaged under one per sample, "
        "so the walking-only share cannot be read on this fort. APX1 over a full season is optional. INV3 needs a calm map."),
    10: ("partial", "SURV confirmed (130 ms). GRD1 re-designed to record the stranding the moment the pike are moved.",
         "GRD1 in the RC chain. PELA needs an ocean fort (AQUA_SHORE)."),
    11: ("partial", "EXR1 confirmed (weak). EXU1 re-designed with per-unit BENIGN receipts.",
         "EXU1 in the RC chain. EXF1 needs an extinct land apex in the embark."),
    12: ("open", "Auto-on confirmed. The spill's give-back was not seen in the run.", "F2 over two seasons is a FULL-tier run."),
    13: ("done", "Measured. The release candidate cut the worst tick 71 to 52 ms and tool time 112 to 80 ms per 1,000 t; "
         "over-budget groups passes 26 to 0. Water draws now take one body per pass (3fadb99) after a 110 ms spike on "
         "RinghatchetsReady.", "Timing re-check on RinghatchetsReady with 3fadb99. PERF3 needs an ocean fort."),
    14: ("partial", "gui and web claims confirmed. The Panel stage reaches all 13 sections, but its set-and-read-back round "
         "trip still scores 0/13 (harness).", "Fix the Panel round-trip harness; the Chrome pass of the web page."),
    15: ("done", "No regression from DFHack 53.16-r2.", "Nothing."),
}
CHIP = {"done": ("Done", "ok"), "fixed": ("Fixed, needs rig check", "fix"), "partial": ("Partly done", "part"),
        "explained": ("Explained", "ok2"), "open": ("Open", "open")}

STAGES = [
    ("DFHack r2 re-validation", "ok", "Done",
     "CTRL 357 PASS / 0 FAIL and RinghatchetsReady 360 / 3 on the release candidate. The 3 are fixed (2 probe scrolling, "
     "1 water-draw timing) and wait for a re-run."),
    ("Alpha Four walkthrough, 109 steps", "part", "Round 1 resolved",
     "Round 1: 83 PASS, 19 ANOMALY, 7 SKIPPED. All 19 anomalies resolved (11 tool fixes, driver and page fixes) and passing "
     "on re-run. A full round on the final build is still to run; the 7 skips need an ocean, a bear, a curious beast, a calm "
     "map or a water draw."),
    ("Section 7, the 15 rows the page cannot check", "part", "Mostly measured",
     "13 blocks completed on 9e5aabe, 8 re-run on the Alpha Four fixes, and a release-candidate list running now. Detail "
     "below."),
    ("Web companion", "ok", "Live run passed",
     "Rebuilt on branch v7.1-web2 (10 tabs: map, groups, species, food web, seasons, roster, waters and caverns, controls, "
     "ledger). Live on RinghatchetsReady, 19:21-19:31: 0 FAIL of 23 checks. 1,150 reads at the page's own cadence, no "
     "5xx; the game date, units, groups, history and ledger all moved; 304s while paused; every route's server time p95 "
     "under 50 ms (state 17, worst poll 108 ms); terrain scan 66 ms; 37 of 44 markers moved in 5 min; 0 console errors. "
     "Display nits: per-body caps read as '27 / 9'; a few cavern sprites blank. Merge with the release."),
    ("Aquarium package", "part", "Built, offline-tested",
     "Translucent-water mod (generated from your own sheets), depth lens, legend, waves, 17 controls. Aquarium world region10 "
     "(region9's terrain with the mod) and fort AQUA_LAKE exist. In-game tests T1-T11 and AQUA_SHORE are pending."),
    ("Release", "open", "Waiting", "Merge into v7.1, push, release notes, and the pages, after the above."),
]

RUNNING_HEAD = [
    ("done", "Deploy v7.1-rc (16f85e6) and Chronicler scripts"),
    ("done", "Full validation: CTRL 357 / 0 FAIL; RinghatchetsReady 360 / 3 FAIL (fixes ready, re-run pending)"),
]
# the chain's stages in run order (alpha4-sec7.py orders by item), and notes the log cannot carry
QUEUE = ["FACTS", "PANEL", "S7_FSH3", "S7_FSH4", "S7_STP1", "S7_NAT", "S7_GRD1", "S7_EXU1", "S7_VF1", "S7_IRRM",
         "S7_IRRP2", "S7_IRRR35", "S7_TRIM"]
NOTE = {"PANEL": "13 sections reached; the round trip scored 0/13 (wrong key; fixed d69ed56, re-run after the chain)",
        "S7_FSH3": "not testable here (no fishing species in the pool)",
        "S7_FSH4": "not testable here (no fishing species in the pool)"}


def live_running():
    """The chain's state from its own logs: each finished stage with its minutes, the running block with its replicate
    and cell count, the queue after it."""
    log = ROOT / "data/logs/sec7-rc.log"
    txt = log.read_text() if log.exists() else ""
    done, cur = {}, None
    for ln in txt.splitlines():
        m = re.search(r"== (S7_\w+|FACTS|PANEL)\b", ln)
        if m:
            cur = m.group(1)
            if "NOT-TESTABLE" in ln:
                done[cur] = "skip"
        m = re.search(r"\s(S7_\w+|FACTS|PANEL): ([0-9.]+) min$", ln)
        if m:
            done.setdefault(m.group(1), f"{m.group(2)} min")
        if "ABORTED" in ln and cur:
            done[cur] = "ABORTED"
    runs = sorted((ROOT / "data/alpha4-sec7").glob("2*/eco/log.txt"))
    eco = runs[-1].read_text() if runs else ""
    out = list(RUNNING_HEAD)
    for b in QUEUE:
        st = done.get(b)
        if st == "skip":
            out.append(("skip", f"{b}: {NOTE.get(b, 'not testable here')}"))
        elif st == "ABORTED":
            out.append(("skip", f"{b}: aborted at its setup check; marked pending, not re-run this round"))
        elif st:
            out.append(("done", f"{b}: done in {st}" + (f"; {NOTE[b]}" if b in NOTE else "")))
        elif b == cur and "=== sec7 exit" not in txt:
            part = eco.split(f"== block {b} on", 1)[1] if f"== block {b} on" in eco else ""
            reps = re.findall(r"rep (\d+): order", part)
            cells = len(re.findall(r"manip ok|MANIP-FAIL", part))
            arms = len(re.findall(r"^\S+\s+manip \S+: ", part, re.M))
            out.append(("run", f"{b}: running, replicate {reps[-1] if reps else 1} of 5, {cells} of "
                               f"{arms * 5 if arms else '?'} cells done"))
        else:
            out.append(("wait", b))
    if "=== sec7 exit" in txt:
        out.append(("done", "Chain finished"))
    return out

PENDING = [
    ("Re-deploy and re-check", [
        "Deploy the latest release candidate (30873d4: trim_gated on, the water-draw timing fix).",
        "Re-run RinghatchetsReady validation, the gui and timing phases (the 3 fixed FAILs).",
    ]),
    ("Rig checks for the new tool fixes", [
        "Irruption flags read 1 after 20 t, survive save and reload, and read 0 after the end (wound carrier, then syndrome).",
        "trim_gated sends off a DF wave from a cavern over its cap: PENDING with S7_TRIM (harness), after this round.",
    ]),
    ("Section 7 leftovers", [
        "Fix the Panel round-trip harness and re-run PANEL.",
        "Tally the RC chain and the VF4 re-run into SECTION7-RESULTS.md.",
        "A block that comes back thin (too few subjects) is marked pending, not re-run this round.",
    ]),
    ("Ocean and aquarium (region10)", [
        "Embark AQUA_SHORE (candidate tile 205,170, ocean to the south, 6x6).",
        "Aquarium tests T1-T11 with screenshots: floor through water, units below the view, deep ocean, waves spawn, the lens, "
        "the legend, the cost.",
        "Section 7 ocean rows: PELA, PEL1, orca cohesion, PERF3, the ocean half of FSH4.",
        "The walkthrough's ocean skips (1.8, 4.11).",
    ]),
    ("Forts still needed", [
        "A fort whose pool has bears, for FSH3/FSH4.",
        "A calm map, for INV3 and walkthrough step 1.3.",
        "An extinct land apex in the embark, for EXF1.",
    ]),
    ("Final rounds", [
        "A full Alpha Four regression round on the final build.",
        "A web companion re-run, and the Chrome pass of every tab.",
    ]),
    ("Release and pages", [
        "Merge v7.1-rc into v7.1, push, release notes.",
        "Republish the docket, backlog, design and Wilderpop pages (with the new ECO link) and the Alpha Four page with this "
        "round's marks.",
    ]),
]

DECISIONS = [
    ("Answered", "Should the cavern trim also send off DF waves? Yes: trim_gated, default on."),
    ("Answered", "Land cap overshoot (9.65 v cap 9 on the release candidate): acceptable."),
    ("Answered", "Inconclusive results (too few subjects) are marked pending; the round moves on without re-fixing."),
    ("Answered", "Irruption flags carrier: the save-safe wound by default, the syndrome route as an option."),
    ("Open", "Row 5: no detectable scatter from a lost leader at n = 5. A larger n, another measure, or accept?"),
    ("Open", "Irruption pressure: a cavern whose species are all held out of season reads as scarce and gains a little "
     "pressure. Keep?"),
    ("Open", "A stock you set by hand is rewritten when its season returns, so an irruption's draw on it doesn't carry over."),
    ("Open", "Exhaustion on the cavern layer can open an out-of-season cavern species for the rest of a season. Keep it off "
     "the caverns?"),
    ("Open", "Optional tidy: drop the Live tab's 'Wild on map' list, which repeats the by-origin breakdown (frees ~10 rows)."),
]


def build():
    rows, sec = summary_rows(), per_row_sections()
    s7 = []
    for n in range(1, 16):
        title, verdict, nums = rows.get(n, ("?", "?", ""))
        st, changed, remains = SINCE[n]
        label, cls = CHIP[st]
        detail = "".join(f"<h4>{E(h)}</h4>" + mdlite.convert(t) for h, t in sec.get(n, []))
        s7.append(f"""
<article class="row" id="r{n}">
  <header><span class="num">{n}</span><h3>{inl(title)}</h3><span class="chip {cls}">{label}</span></header>
  <dl>
    <dt>Tally verdict</dt><dd>{inl(verdict)}</dd>
    <dt>Key numbers</dt><dd class="nums">{inl(nums)}</dd>
    <dt>Since the tally</dt><dd>{E(changed)}</dd>
    <dt>Remaining</dt><dd>{E(remains)}</dd>
  </dl>
  {f'<details><summary>Full analysis</summary><div class="md">{detail}</div></details>' if detail else ''}
</article>""")
    counts = {}
    for v in SINCE.values():
        counts[v[0]] = counts.get(v[0], 0) + 1
    tally = " · ".join(f"{counts.get(k, 0)} {CHIP[k][0].lower()}" for k in ("done", "explained", "fixed", "partial", "open"))
    stages = "".join(f'<li class="stage"><span class="chip {c}">{E(lab)}</span><h3>{E(t)}</h3><p>{E(d)}</p></li>'
                     for t, c, lab, d in STAGES)
    running = "".join(f'<li class="{c}"><span class="dot"></span>{E(t)}</li>' for c, t in live_running())
    pending = "".join(f"<li><h3>{E(h)}</h3><ul>" + "".join(f"<li>{E(x)}</li>" for x in items) + "</ul></li>"
                      for h, items in PENDING)
    decisions = "".join(f'<li><span class="chip {"ok" if a == "Answered" else "open"}">{a}</span> {E(t)}</li>'
                        for a, t in DECISIONS)
    nt = mdlite.convert(RES.split("## Not testable here, and what each needs", 1)[1].split("## Reproduce", 1)[0])
    page = TEMPLATE.format(as_of=AS_OF or __import__("datetime").datetime.now().strftime("%-d %b %Y, %H:%M MDT"), stages=stages, running=running, s7="".join(s7), tally=tally, pending=pending,
                           decisions=decisions, nt=nt)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page)
    print("wrote", OUT, len(page))


TEMPLATE = """<title>Alpha Four Progress</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@500;700&family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root {{
  --bg: #f2f4f1; --surface: #ffffff; --sunk: #e8ece8; --ink: #1c2420; --muted: #5a665f; --line: #d3dad5;
  --accent: #2f6a52; --water: #2a6688;
  --ok: #2f7a4a; --ok-bg: #e2f1e7; --fix: #2a6688; --fix-bg: #e1edf5; --part: #9a6a12; --part-bg: #f6ecd6;
  --open: #a2402e; --open-bg: #f6e3de; --ok2: #5b5f8a; --ok2-bg: #e7e8f3;
  --serif: "Bitter", Georgia, serif; --sans: "Atkinson Hyperlegible", system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  color-scheme: dark;
  --bg: #131816; --surface: #1b2220; --sunk: #222a27; --ink: #e2e8e4; --muted: #9aa69f; --line: #2f3a35;
  --accent: #7fb79a; --water: #7fb2d4;
  --ok: #8fd0a6; --ok-bg: #1f3428; --fix: #8cc0e2; --fix-bg: #1b2d3a; --part: #e2b765; --part-bg: #3a2f1a;
  --open: #ee9a86; --open-bg: #3d2420; --ok2: #b3b6e6; --ok2-bg: #262840;
}} }}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --bg: #131816; --surface: #1b2220; --sunk: #222a27; --ink: #e2e8e4; --muted: #9aa69f; --line: #2f3a35;
  --accent: #7fb79a; --water: #7fb2d4;
  --ok: #8fd0a6; --ok-bg: #1f3428; --fix: #8cc0e2; --fix-bg: #1b2d3a; --part: #e2b765; --part-bg: #3a2f1a;
  --open: #ee9a86; --open-bg: #3d2420; --ok2: #b3b6e6; --ok2-bg: #262840;
}}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.55 var(--sans); }}
.wrap {{ max-width: 1040px; margin: 0 auto; padding-inline: 20px; padding-block: 28px 64px; }}
h1, h2, h3, h4 {{ font-family: var(--serif); text-wrap: balance; margin: 0; }}
h1 {{ font-size: 2rem; letter-spacing: -0.01em; }}
h2 {{ font-size: 1.35rem; margin-block: 40px 14px; padding-top: 10px; border-top: 1px solid var(--line); }}
h3 {{ font-size: 1.02rem; }}
p {{ margin: 0; max-width: 72ch; }}
code {{ font: 0.86em var(--mono); background: var(--sunk); padding: 0 4px; border-radius: 3px; }}
.lede {{ display: grid; gap: 8px; }}
.meta {{ color: var(--muted); font: 0.82rem var(--mono); }}
.eyebrow {{ text-transform: uppercase; letter-spacing: 0.08em; font: 600 0.72rem var(--mono); color: var(--accent); }}
.chip {{ display: inline-block; font: 600 0.7rem var(--mono); letter-spacing: 0.04em; text-transform: uppercase;
  padding: 2px 8px; border-radius: 999px; white-space: nowrap; }}
.chip.ok {{ color: var(--ok); background: var(--ok-bg); }} .chip.fix {{ color: var(--fix); background: var(--fix-bg); }}
.chip.part {{ color: var(--part); background: var(--part-bg); }} .chip.open {{ color: var(--open); background: var(--open-bg); }}
.chip.ok2 {{ color: var(--ok2); background: var(--ok2-bg); }}
.stages {{ list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 12px; }}
.stage {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; display: grid; gap: 6px; align-content: start; }}
.stage p {{ color: var(--muted); font-size: 0.92rem; }}
.run {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 6px; }}
.run li {{ display: flex; gap: 10px; align-items: baseline; }}
.run .dot {{ width: 9px; height: 9px; border-radius: 50%; flex: none; transform: translateY(1px); background: var(--line); }}
.run .done .dot {{ background: var(--ok); }} .run .run .dot {{ background: var(--water); box-shadow: 0 0 0 3px var(--fix-bg); }}
.run .skip .dot {{ background: var(--part); }} .run .skip, .run .wait {{ color: var(--muted); }}
.run li.run {{ font-weight: 700; }}
.tally {{ font: 0.85rem var(--mono); color: var(--muted); margin-bottom: 12px; }}
.row {{ background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; }}
.row > header {{ display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }}
.row > header h3 {{ flex: 1 1 300px; }}
.num {{ font: 700 1.1rem var(--serif); color: var(--accent); min-width: 1.6em; }}
dl {{ display: grid; grid-template-columns: 9.5rem 1fr; gap: 6px 14px; margin: 12px 0 0; }}
dt {{ font: 600 0.72rem var(--mono); text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); padding-top: 3px; }}
dd {{ margin: 0; max-width: 78ch; }}
dd.nums {{ font-variant-numeric: tabular-nums; }}
details {{ margin-top: 10px; border-top: 1px dashed var(--line); padding-top: 8px; }}
summary {{ cursor: pointer; color: var(--accent); font-weight: 700; }}
summary:focus-visible, a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
.md {{ display: grid; gap: 8px; margin-top: 8px; font-size: 0.93rem; }}
.md h4, .md h5 {{ font-size: 0.95rem; margin-top: 8px; }}
.md ul, .md ol {{ margin: 0; padding-left: 1.2rem; }}
.tbl {{ overflow-x: auto; }}
table {{ border-collapse: collapse; font-size: 0.86rem; font-variant-numeric: tabular-nums; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 4px 8px; text-align: left; vertical-align: top; }}
th {{ font: 600 0.72rem var(--mono); text-transform: uppercase; color: var(--muted); }}
.pending {{ list-style: none; padding: 0; margin: 0; counter-reset: p; display: grid; gap: 12px; }}
.pending > li {{ counter-increment: p; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px 16px 12px 48px; position: relative; }}
.pending > li::before {{ content: counter(p); position: absolute; left: 16px; top: 11px; font: 700 1.05rem var(--serif); color: var(--accent); }}
.pending ul {{ margin: 6px 0 0; padding-left: 1.1rem; display: grid; gap: 3px; }}
.decisions {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }}
.decisions li {{ display: flex; gap: 10px; align-items: baseline; }}
.nt {{ display: grid; gap: 6px; }} .nt ul {{ margin: 0; padding-left: 1.2rem; }}
@media (max-width: 560px) {{ dl {{ grid-template-columns: 1fr; }} dt {{ padding-top: 6px; }} .pending > li {{ padding-left: 40px; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
</style>
<div class="wrap">
<section class="lede">
  <span class="eyebrow">Seasonal Wildlife v7.1 · test fort RinghatchetsReady (region9)</span>
  <h1>Alpha Four Progress</h1>
  <p>Where every part of Alpha Four testing stands: the r2 re-validation, the 109-step walkthrough, the 15 rows the
  walkthrough page cannot check, the web companion, the new aquarium package, and what is left before the release.</p>
  <span class="meta">As of {as_of} · release candidate v7.1-rc c2adab0 · rig running v7.1-rc 16f85e6</span>
</section>

<h2>Stages</h2>
<ul class="stages">{stages}</ul>

<h2>On the rig now</h2>
<p class="meta" style="margin-bottom:10px">The release-candidate chain: deploy, both validations (done), then the section-7 re-run list.</p>
<ul class="run">{running}</ul>

<h2>Section 7, row by row</h2>
<p style="margin-bottom:8px">Fort RinghatchetsReady, n = 5 per arm, a fresh load per arm. Tests: exact two-sided
permutation test on the difference of means (5 v 5, so p cannot go below 0.008) and Fisher's exact test for yes/no
outcomes. Attacks and kills count harness-placed units only. A row is vacuous when its receipts show the setting never
reached the animals. Full analysis lives in <code>data/alpha4-sec7/SECTION7-RESULTS.md</code>.</p>
<div class="tally">{tally}</div>
{s7}

<h3 style="margin-top:20px">Not testable on RinghatchetsReady</h3>
<div class="nt md">{nt}</div>

<h2>Pending work, in order</h2>
<ol class="pending">{pending}</ol>

<h2>Decisions</h2>
<ul class="decisions">{decisions}</ul>
</div>
"""

if __name__ == "__main__":
    build()
