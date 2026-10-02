"""Appendix panels for the ECO page: sections of the earlier doc text (data/eco-report/eco-report-doc-rev326.md),
kept whole as collapsed history, plus the current data-and-code table."""
import re
from pathlib import Path
from mdlite import convert, inline

ROOT = Path(__file__).resolve().parents[2]
MD = (ROOT / "data/eco-report/eco-report-doc-rev326.md").read_text()

PANELS = [  # (summary, start heading line, stop heading regex) -- text between, converted
    ("Design history 1: the roster rules as first written, and what went wrong", "## The imposed roster and food-web rules", r"^### Guild-first rebuild"),
    ("Design history 2: the guild-first rebuild (v2) and your four decisions", "### Guild-first rebuild (v2)", r"^### The 5× size gate"),
    ("Design history 3: the 5× size gate, pack-size and calibration detail (PK, WB, CAL)", "### The 5× size gate, drawn", r"^### Solitary hunters"),
    ("Solitary hunters: the full STL and STL2 tables", "### Solitary hunters: speed, stealth and skills (STL, STL2)", r"^### v2\.1"),
    ("Design history 4: v2.1, your answers worked through (30 Sep)", "### v2.1: your answers worked through (30 Sep)", r"^### Third round"),
    ("Design history 5: third round, your notes worked through (30 Sep evening)", "### Third round (30 Sep evening): your notes worked through", r"^### GOOD, EVIL and FANCIFUL creatures"),
    ("GOOD, EVIL and FANCIFUL creatures: the full table", "### GOOD, EVIL and FANCIFUL creatures", r"^### A lone hunter"),
    ("LONE: the five-run tables", "### A lone hunter among 48 prey (LONE)", r"^### Reach tests"),
    ("Vermin: the first run (VRM) and its flaw", "### Vermin predation (VRM)", r"^### Domestic animals"),
    ("A mechanistic version for a new embark (superseded in part)", "### A mechanistic version for a new embark", r"^## Overnight blocks"),
    ("Token effects: the full table and the desk triage", "## Token effects", r"^## Scavenging"),
    ("Token census: tokens in no creature definition, and the value distributions", "## Token census: what the raws hold", r"^## Token effects"),
    ("Across the land/water boundary: the full table and the tool audit", "## Across the land/water boundary, and the tool's sorting", r"^## Every layer"),
    ("Every layer: caverns, pools, river, ocean, lake — the full table", "## Every layer: caverns, cavern pools, river, ocean, lake", r"^## Token census"),
    ("Groups at once by embark size (ECO2-G): the full table", "**Groups at once versus embark size (ECO2-G).**", r"^## Spawn levers"),
    ("Guilds and realms: the 15 tag set-groups and the realm table", "## Geography and tag set-groups", r"^## The imposed roster"),
    ("Scavenging: the first tests (S, S2) and who should scavenge", "## Scavenging", r"^## Groups"),
    ("Overnight blocks, 30 Sep – 1 Oct: the summary table", "## Overnight blocks, 30 Sep – 1 Oct", r"^### Cohesion with a leader"),
    ("The former 34-item tracker (all done)", "| # | Item | What's missing | Next step | When |", r"^## Data, code and sources"),
]


def section(start, stop):
    i = MD.find(start)
    if i < 0:
        return f"<p>(section '{start}' not found)</p>"
    rest = MD[i:]
    first, _, body = rest.partition("\n")
    if not start.startswith("#"):
        body = rest
    m = re.search(stop, body, re.M)
    return convert(body[: m.start()] if m else body)


DATA_TABLE = [
    ("Every block's findings, one paragraph each", "data/eco-desk/findings.md"),
    ("Cell runs and logs (ECO, ECO2, ECO3, CAL, STL, LONE, REACH, VRM, RELS, SW, SCV, COH, GPK …)", "data/experiments/ECO/<block>-<timestamp>/, data/logs/<block>.log"),
    ("Manifest runs (F1, T2, N1, G1, S8C/S8B/S8O, T9c, E23e)", "data/experiments/<id>/<run>/ (events.tsv, rows.tsv, log.txt); manifests in experiments/"),
    ("Runner, in-game instrument, analysis", "scripts/eco-run.py, chronicler/dfhack/scripts/cx-eco.lua, scripts/eco-analyze.py"),
    ("Tallies", "scripts/stl-tally.py, lone-tally.py, vrm-tally.py, rels*-tally.py, sweep-tally.py, s8-tally.py, t9c-tally.py, e23e-tally.py"),
    ("Designs", "experiments/ECO-design.md, experiments/SWEEP-design.md, data/eco-desk/v2/guilds/design.md"),
    ("Roster builder v2–v2.2 (offline)", "data/eco-desk/v2/guilds/ (roster2.py, species2.py, results*.md, ge22.md)"),
    ("Token census and wiki definitions", "data/eco-desk/v2/tokens/, data/eco-desk/"),
    ("Research notes (vermin, DF's own relation writes)", "data/eco-desk/v2/research/"),
    ("This page: builder, content, data", "scripts/eco-report/ (build.py, content.html, template.html), data/eco-report/*.json"),
    ("Validator and latest run", "scripts/validate-full.py; data/validation/full/20261001-074833"),
    ("Your review and the answers", "data/eco-review/part1/ (USER-REVIEW-PART1.md, PLAN-PART1.md, A-D desk reports, fig-diag/), data/eco-review/part2/ (USER-REVIEW-PART2.md, ANSWERS.md, R3/R24/R28 analyses)"),
    ("Figure fixes from the review", "scripts/eco-report/patch_review.py (after part1/fig-diag/patch_exp.py); scripts/eco-report/figcheck.py guards the build"),
    ("Harness for the testing stage", "experiments/HARNESS-v71.md; scripts/eco-run.py, scripts/eco-v71-tally.py, scripts/b1-forts.py"),
    ("Tool", "seasonal-wildlife: v6.9.0 on master (released); v7.0 at 99c1ec8 (validated, pushed, not merged); v7.1 at fce7d68 (every build stream merged, pushed, untested; notes in docs/v7.1/)"),
]


def build():
    parts = ['<div class="card tbl"><table><thead><tr><th>What</th><th>Where (DwarfCron unless noted)</th></tr></thead><tbody>'
             + "".join(f"<tr><td>{inline(a)}</td><td><code>{inline(b)}</code></td></tr>" for a, b in DATA_TABLE) + "</tbody></table></div>",
             '<p style="max-width:none;font:14px var(--ui);color:var(--ink2)">Token definitions come from the wiki\'s '
             '<a href="https://dwarffortresswiki.org/index.php/Creature_token">Creature token</a> page and the pages it links, read as raw wikitext. '
             'DF 53.16, DFHack 53.16-r1.1. The panels below keep the earlier report\'s full tables and the design history, including your rulings, as they stood.</p>']
    for summary, start, stop in PANELS:
        parts.append(f'<details class="appx"><summary>{inline(summary)}</summary><div class="prose">{section(start, stop)}</div></details>')
    return "\n".join(parts)
