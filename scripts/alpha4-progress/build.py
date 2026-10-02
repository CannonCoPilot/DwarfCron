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
AS_OF = "2 Oct 2026, 16:45 MDT"

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
    2: ("partial", "Packs confirmed. STP1 re-designed to place a raptor from the fort's own pool beside prey; it ran in the RC chain "
        "(25.5 min) and awaits the tally. The tool only acts on pool species, which is why the eagles and bears never engaged.",
        "FSH3/FSH4 are NOT-TESTABLE on RinghatchetsReady: no fishing species in its pool. Needs a region10 fort whose pool has bears."),
    3: ("fixed", "Land overshoot partly a tool bug: after one release, gate_drain released up to 8 more held groups. Fixed in "
        "f3c8d11 (stops at the cap); the status now says how far over and who brought the groups. DF still sends a wave per "
        "border source.", "Rig check of the land count on the release candidate; S7_NAT re-run (flying-aware) is running now."),
    4: ("fixed", "You ruled yes: groups cavern trim_gated (default ON, 30873d4) also sends off the oldest DF wave when no "
        "resident group is left. TRIM re-designed to place 3 resident groups over cap 1.",
        "TRIM runs in the RC chain on the build before trim_gated, so it tests the resident trim only. A second TRIM run on "
        "30873d4 checks DF waves get trimmed."),
    5: ("open", "No detectable scatter from a lost leader at n = 5 (25.9 v 20.7 tiles, p = 0.33).",
        "Decide: a larger n, a different measure (time to regroup), or accept as no effect."),
    6: ("fixed", "CRAZED / MISCHIEVOUS / NOFEAR never stuck: DF rebuilds those flags from wounds. 594cc9d carries them on a "
        "body-less wound (save-safe, default) or a runtime syndrome. Irruptions now admit out-of-season civ races (69e97a1). "
        "R35 cap set to 2 so it bites.", "Rig check that the flags read 1 after 20 t, survive save + reload, and read 0 after "
        "the end. IRRM / IRRP2 / IRRR35 re-run in the RC chain."),
    7: ("done", "Both halves confirmed.", "Nothing."),
    8: ("partial", "VF4 re-run completed (no abort) on the Alpha Four fixes with the fish-vermin bank finder; result not tallied yet. VF1 "
        "re-designed with a gobble receipt; runs in the RC chain.", "Tally VF4; VF1 result from the chain."),
    9: ("explained", "No defect. Apex presence 0.17 is what a one-month run predicts (expected 0.17, none placed in 0.48 of "
        "runs). The carnivore share read 0.05 because 93% of 'land' units were ravens from the flying pool.",
        "S7_NAT re-run scores walking land animals only and checks the ladder reaches the raws daily (running now). APX1 over a "
        "full season is optional. INV3 needs a calm map."),
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
    ("Web companion", "part", "Live test passed",
     "551 PASS / 0 FAIL on an earlier build (the server's false error count fell from ~400,000 to 0). A re-run on the final "
     "build and the Chrome pass are pending."),
    ("Aquarium package", "part", "Built, offline-tested",
     "Translucent-water mod (generated from your own sheets), depth lens, legend, waves, 17 controls. Aquarium world region10 "
     "(region9's terrain with the mod) and fort AQUA_LAKE exist. In-game tests T1-T11 and AQUA_SHORE are pending."),
    ("Release", "open", "Waiting", "Merge into v7.1, push, release notes, and the pages, after the above."),
]

RUNNING = [
    ("done", "Deploy v7.1-rc (16f85e6) and Chronicler scripts"),
    ("done", "Full validation: CTRL 357 / 0 FAIL; RinghatchetsReady 360 / 3 FAIL (fixes ready, re-run pending)"),
    ("done", "FACTS on RinghatchetsReady"),
    ("done", "PANEL: 13 sections reached; round trip 0/13 (harness fix in progress at the desk)"),
    ("skip", "S7_FSH3 / S7_FSH4: not testable here (no fishing species in the pool)"),
    ("done", "S7_STP1: 25.5 min, awaiting the tally"),
    ("run", "S7_NAT: flying-aware scoring, daily ladder check; rep 3 of 5 at 16:45, ~13 min per cell, done ~17:50"),
    ("wait", "S7_GRD1, S7_EXU1, S7_VF1 (~1 h)"),
    ("wait", "S7_IRRM, S7_IRRP2, S7_IRRR35 (~2 h)"),
    ("wait", "S7_TRIM (resident groups, first real run); chain done ~21:00"),
]

PENDING = [
    ("Re-deploy and re-check", [
        "Deploy the latest release candidate (30873d4: trim_gated on, the water-draw timing fix).",
        "Re-run RinghatchetsReady validation, the gui and timing phases (the 3 fixed FAILs).",
    ]),
    ("Rig checks for the new tool fixes", [
        "Irruption flags read 1 after 20 t, survive save and reload, and read 0 after the end (wound carrier, then syndrome).",
        "The land count holds at its cap after a release.",
        "trim_gated sends off a DF wave from a cavern over its cap (a second S7_TRIM run).",
    ]),
    ("Section 7 leftovers", [
        "Fix the Panel round-trip harness and re-run PANEL.",
        "Tally the RC chain and the VF4 re-run into SECTION7-RESULTS.md.",
        "Re-run any block that aborts.",
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
    running = "".join(f'<li class="{c}"><span class="dot"></span>{E(t)}</li>' for c, t in RUNNING)
    pending = "".join(f"<li><h3>{E(h)}</h3><ul>" + "".join(f"<li>{E(x)}</li>" for x in items) + "</ul></li>"
                      for h, items in PENDING)
    decisions = "".join(f'<li><span class="chip {"ok" if a == "Answered" else "open"}">{a}</span> {E(t)}</li>'
                        for a, t in DECISIONS)
    nt = mdlite.convert(RES.split("## Not testable here, and what each needs", 1)[1].split("## Reproduce", 1)[0])
    page = TEMPLATE.format(as_of=AS_OF, stages=stages, running=running, s7="".join(s7), tally=tally, pending=pending,
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
  <span class="meta">As of {as_of} · release candidate v7.1-rc 30873d4 · rig running v7.1-rc 16f85e6</span>
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
