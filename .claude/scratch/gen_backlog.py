#!/usr/bin/env python3
"""Generate The Wildlife Backlog (1 Oct 2026) from DwarfCron data/eco-report/open-items.json.
Output: DwarfCron/.claude/scratch/wildlife-backlog.html (the page's local source)."""
import json, html, sys
from collections import Counter

ROOT = '/Users/nathanielcannon/Claude/Projects/DwarfCron'
OI = json.load(open(f'{ROOT}/data/eco-report/open-items.json'))
items = {i['id']: i for i in OI['items']}
assert len(items) == 84, len(items)
E = html.escape

WP = 'https://claude.ai/code/artifact/6cebd06e-eafd-44a8-aa6e-d3c108e5fcba'
DS = 'https://claude.ai/code/artifact/a61b06b2-4687-41ea-91f0-2216220d7111'
PT = 'https://claude.ai/code/artifact/3f8ce1ed-4db3-4482-97fa-c27b2eaded7e'
ECO = 'https://claude.ai/artifact/Qq4zH3VFQPmTaUPownxDyw'
A2 = 'https://claude.ai/artifact/3qMtYL2M5K4CRUEwSGKR4W'
DK = 'https://claude.ai/code/artifact/4dac86e8-4f3c-4480-a8d4-8eed3deb5672'

# ---- 1 Oct review notes on individual items (corrections or checks against git; shown on the item)
NOTES = {
    'push-repos': 'Checked 1 Oct: the seasonal-wildlife GitHub repository is private (gh repo view), so a push alone publishes nothing; going public belongs to the same call (rv-public-release).',
    'state-addenda-refresh': 'Done 1 Oct (status notes under 96, 96e, 97; Addendum 98). The missing v6.8.0/v6.9.0 addendum is now its own item, state-v68-v69-addenda.',
    'validator-backlog-stale': 'This page now records the seven as shipped (see "The old backlog, checked"); the validator register still says BACKLOG.',
    'v70-release-steps': 'Sequenced here as re-validate on r2, then release with today\'s defaults, and the default changes in v7.1. The item\'s own next step puts the default decisions first; which order to take is the user\'s call.',
    'usage-v7-docs': 'README.md and the window script carry no v7.0 content either (brief, 1 Oct).',
}

# ---- stages: (id, depends-on text)
STAGES = [
  ('s1', 'Release v7.0', 'Ship what is on the rig now, with today\'s defaults, after re-validating it on DFHack 53.16-r2. Nothing here changes tool behaviour. Only the push needs the user.', [
    ('revalidate-dfhack-r2', 'Nothing. Do first: every later rig run, ECO number and the release validation depend on it.'),
    ('commit-uncommitted-work', 'Nothing. Do early: the night\'s data and the v2.2 civ desk work are uncommitted.'),
    ('validator-v70-coverage', 'revalidate-dfhack-r2 for the run itself. Must land before the release validation run, or 214 PASS still says nothing about the builder, gobble or scav_ext.'),
    ('usage-v7-docs', 'Nothing. Clears doc.usage.version.'),
    ('state-addenda-refresh', 'Nothing. Addendum 98 should cite the release validation run, so write it last in this stage.'),
    ('state-v68-v69-addenda', 'Nothing. One addendum for v6.8.0 and v6.9.0 from their commits and the 20260930-124923 validations.'),
    ('validator-backlog-stale', 'Nothing.'),
    ('gobble-stale-comment', 'Nothing (a comment; rides with the release commit).'),
    ('validator-cli-water-dup', 'Nothing.'),
    ('v70-release-steps', 'revalidate-dfhack-r2 and all of the above; the push waits on push-repos (stage 2). The Docket rev 16 already names v7.0.0 @ 1e65e03, so doc.docket passes on the deployed script.'),
  ]),
  ('s1b', 'Paperwork beside the release', 'Documents that cite the night. No tool change; any order. Four were done during the 1 October review and stay listed.', [
    ('findings-more-slips', 'Nothing.'),
    ('report-done-count', 'Done.'),
    ('report-stale-cells', 'Done on the page; the doc is claude-doc-sync.'),
    ('design-md-stale', 'Done; uncommitted (commit-uncommitted-work).'),
    ('findings-small-discrepancies', 'Done.'),
    ('claude-doc-sync', 'Nothing. Low value unless the doc\'s comment threads stay in use.'),
  ]),
  ('s2', 'Decisions for the user', 'Thirteen rulings from the open-items register, plus two questions that also need the user. None is decided here. Each names what it unblocks.', [
    ('push-repos', 'Stage 1. Blocks the release\'s last step and a public repository.'),
    ('dflt-ecology-cadence-3000', 'Unblocks the v7.1 default; checked again in SW8.'),
    ('dflt-nudge-off', 'Unblocks the v7.1 default; SW8.'),
    ('dflt-pack-sneak-0', 'Unblocks the v7.1 default and the removal of the SNEAK write; SW8.'),
    ('builder-drop-x3-pack-bonus', 'Unblocks the ladder port (stage 3) and the v2.2 restatement.'),
    ('ladder-drop-apx-step', 'Unblocks the ladder port; if kept, lp-separate-pool becomes worth running; if dropped, an apex placement job needs designing.'),
    ('cavern-limit-soft-target', 'Wording only once ruled.'),
    ('water-groups-default-2', 'Leave auto unless ruled; confirm on OCEAN2 or LAKE if changed.'),
    ('scav-carnivorous-swimmers', 'If yes, a water cell with crocodiles joins scav-attribution-and-fallbacks.'),
    ('cavern-animal-person-group-cap', 'Unblocks a v7 switch and one S8B rerun replicate pair.'),
    ('add-invasive-savage-placement', 'Unblocks either a placement path or a refusal message, then an INV2 rerun.'),
    ('lake-apex-gap', 'Ties to lamprey-not-apex (stage 3).'),
    ('fps6-resume-or-drop', 'Independent of the tool. If resumed: smoke X5a first.'),
    ('ladder-units-vs-waves', 'Decide with the ladder port; the same question drives the plump-helmet-man swamp.'),
    ('deep-layer-demons', 'Ask whether D8 stands; a desk check of the S8 tallies can run now.'),
  ]),
  ('s3', 'Build v7.1', 'The chosen defaults, the ladder port, the bugs, the performance pass, and the harness and validator work the experiments need. Order inside the stage follows the dependencies.', [
    ('scav-status-diagnostics', 'Nothing. Fix before scav-attribution-and-fallbacks reads the status line again.'),
    ('cache-world-switch-stale', 'Nothing. Small; rides with any v7.1 build.'),
    ('perf-v71-caching', 'revalidate-dfhack-r2 (measure on r2). P0 instrumentation lands first; P1-P7 then validate together (PERF0, PERF1, PERF2).'),
    ('web-cluster-order', 'One rig line to read which slot is the minimum.'),
    ('chronicler-weather-lookup', 'Nothing (Chronicler bridge, not the tool).'),
    ('spaced-raw-ids-cli', 'Nothing. REACH and W1O needed it.'),
    ('animal-person-mass', 'Nothing. Do before any builder table rerun.'),
    ('animal-person-freq-zero', 'animal-person-mass (same raws pass).'),
    ('builder-port-vs-v22', 'ladder-drop-apx-step, builder-drop-x3-pack-bonus, ladder-units-vs-waves; then one S8 fort, two replicates.'),
    ('builder-reach-table-refresh', 'Desk; run with the ladder port.'),
    ('flying-raptor-slot', 'The ladder port.'),
    ('lamprey-not-apex', 'lake-apex-gap.'),
    ('port-gobble-edge-table', 'The ladder port; gobble-feeds for the vermin-on-vermin share.'),
    ('tool-pred-cfg', 'Nothing.'),
    ('v7-switches-on-panel', 'The default rulings, so the Panel shows the final set.'),
    ('arena-order-and-wildness', 'Nothing. Before any new arena block.'),
    ('cx-probe-invasion-exclusion', 'Nothing. Before E23f.'),
    ('harness-readout-nits', 'Nothing.'),
    ('validator-v70-nt-forts', 'Nothing; needs a BOATS or OCEAN2 pass in the validator.'),
    ('validator-full-run-nt', 'Nothing.'),
    ('v70-job-cost-and-sweep', 'A desk read of the S8 logs can run now; otherwise a status dump in the next season run.'),
  ]),
  ('s4', 'Experiments', 'Two replicates per arm, counterbalanced when cells share a load. Desk reads first where an item has one.', [
    ('natural-skill-unverified', 'revalidate-dfhack-r2; then a short probe on the v7.0 rig.'),
    ('perf3-unit-count', 'revalidate-dfhack-r2. Its result decides whether sponge and per-layer group defaults change in v7.2.'),
    ('antman-civ-class', 'Nothing; one rig line, then a ruling.'),
    ('pelagic-slot-shallow-maps', 'Nothing; a desk print of OCEAN2\'s pool comes first.'),
    ('cavern-traffic-limit', 'Nothing; a desk read of the T9c logs.'),
    ('realms-built-untested', 'A mech.v70.realms claim (validator-v70-coverage).'),
    ('scav-attribution-and-fallbacks', 'revalidate-dfhack-r2 (r2 changes teleport occupancy, which the fallbacks use; setPathGoal is not used by the walks); scav-status-diagnostics; scav-carnivorous-swimmers if the answer is yes.'),
    ('flier-pool-steering', 'A desk check of CTRL\'s raven entry first.'),
    ('invasion-exclusion-unvalidated', 'cx-probe-invasion-exclusion; a BOATS copy with a cavern breach (fort-load-levers).'),
    ('gobble-feeds', 'Nothing.'),
    ('solo-package-natural-density', 'Nothing.'),
    ('orca-stranding-n', 'revalidate-dfhack-r2 (r2\'s breathing fix may change stranding); a fort with deep ocean columns; OCEAN2 has none (0 of 5,374).'),
    ('apex-placement-stock-test', 'Nothing; run before or with the ladder-drop-apx-step ruling, which assumes placement and stock can steer apexes.'),
    ('single-run-defaults', 'Nothing; L3 and A3 in ECO-design.md \'Next experiments\'.'),
    ('lp-separate-pool', 'Only if ladder-drop-apx-step keeps the apex step.'),
    ('sw8-confirm', 'Every default ruling and the v7.1 build. Last before v7.1 ships.'),
  ]),
  ('s5', 'Parked', 'Recorded so they are not lost. None scheduled.', [
    ('realm-placement-path', 'realms-built-untested.'),
    ('perf-v72-native-slicing', 'perf-v71-caching measured; forEachTile needs the r1.1 fallback.'),
    ('web-v7-state', 'v70-release-steps; luasocket checked on r2.'),
    ('vermin-stock-bookkeeping', 'gobble-feeds.'),
    ('bl-eats-history', 'Nothing.'),
    ('bl-water-balance', 'Nothing.'),
    ('bl-grouping-table', 'Nothing.'),
    ('bl-misc-curiosities', 'Nothing.'),
    ('design-s7-unmeasured-cells', 'A tool feature that needs one.'),
    ('fva-parked', 'Nothing.'),
    ('leader-size-in-fight', 'Nothing.'),
    ('otter-eats-jaguar-man', 'A player objection.'),
    ('old-wilderpop-e27b-e31c', 'Nothing.'),
    ('irruption-aimed', 'Nothing.'),
    ('createunit-upstream', 'The user.'),
    ('alpha-cli-round-and-playtest', 'usage-v7-docs.'),
  ]),
]

placed = [i for _, _, _, lst in STAGES for i, _ in lst]
c = Counter(placed)
dups = [k for k, v in c.items() if v > 1]
missing = set(items) - set(placed)
extra = set(placed) - set(items)
if dups or missing or extra:
    sys.exit(f'dups {dups} missing {missing} extra {extra}')

CAT = {x['id']: x['title'] for x in OI['categories']}
STATUS = {'done': 'Done 1 Oct', 'awaiting-user': 'Your call', 'blocked': 'Blocked', 'open': 'Open', 'proposed': 'Proposed', 'parked': 'Parked'}

def card(iid, dep):
    i = items[iid]
    pri = i['priority']
    st = i['status']
    srcs = ' · '.join(E(s) for s in i['source'])
    note = NOTES.get(iid)
    st_cls = 'st-user' if st == 'awaiting-user' else ('st-blocked' if st == 'blocked' else ('st-done' if st == 'done' else 'st'))
    out = [f'    <div class="item pri-{pri}" id="{E(iid)}">',
           f'      <div class="item-head"><span class="chip pri">{pri}</span><span class="chip {st_cls}">{STATUS.get(st, E(st))}</span><h3>{E(i["title"])}</h3></div>',
           f'      <p class="claim">{E(i["detail"])}</p>',
           '      <dl>',
           f'        <dt>Evidence</dt><dd>{E(i["evidence"])}</dd>',
           f'        <dt>Next</dt><dd>{E(i["next"])}</dd>',
           f'        <dt>Depends on</dt><dd>{E(dep)}</dd>']
    if note:
        out.append(f'        <dt>Checked 1 October</dt><dd class="note1">{E(note)}</dd>')
    out += ['      </dl>',
            f'      <p class="meta"><code>{E(iid)}</code> · {E(CAT[i["category"]])} · effort {E(i["effort"])} · {srcs}</p>',
            '    </div>']
    return '\n'.join(out)

# ---- the old backlog, checked
OLD = [
  ('Frequency as the balance lever', 'done', 'v6.5.0: <code>odds</code> is the raw\'s FREQUENCY per species; the tool writes 1, never 0 (engine v7.0 :3004, :3080). Comparative weight confirmed (E36, E21b; X3 on the surface).', 'validator-backlog-stale (bl.frequency)'),
  ('Population number needs no adjustment', 'done', 'v6.5.0: <code>stock</code> is the reserve in the region, debited per arrival and refunded on leaving (STATE 94; USAGE &ldquo;Stock is the reserve&rdquo;; gui line 1493).', 'validator-backlog-stale (bl.popnumber)'),
  ('Solitary, pack or herd for every creature', 'part', 'The Live tab labels tracked species with the raw reason (v5.11.2). The whole-list table and per-species override are unbuilt.', 'bl-grouping-table'),
  ('The largest male leads', 'done', 'v7.0.0 <code>leader_male</code>, on (STATE 96; 49fde90). Rig: largest-male and lowest-id leaders hold a group equally well (L2, COH).', 'validator-backlog-stale (bl.largestmale); leader-size-in-fight'),
  ('Concurrency from the size of the embark', 'done', 'v6.9.0: land groups at once <code>auto</code> = floor(&radic;tiles) + 1 (058d0b2); v7.0.0 <code>layer_groups</code> per water body and cavern depth. Measured: cap 1 &lt; 3 &le; auto (SW3, SW3B).', 'validator-backlog-stale (bl.concurrency); cavern-limit-soft-target'),
  ('Deep water is a property of the map', 'part', 'v7.0.0: the roster builder surveys ocean columns (<code>water.deep_levels</code> 3; df0aa83) and raises the pelagic slot only where deep columns exist. Never seen on a deep map: OCEAN2 had none.', 'pelagic-slot-shallow-maps; orca-stranding-n'),
  ('Migrants are not broken', 'parked', 'Unchanged. Migration works on DF\'s schedule; the forcing trigger is the open question.', 'bl-misc-curiosities'),
  ('Birds already perch', 'parked', 'Unchanged.', 'bl-misc-curiosities'),
  ('The creature that showed as r2 and r4', 'parked', 'Unchanged.', 'bl-misc-curiosities'),
  ('Grouping creatures by where on Earth they belong', 'part', 'v7.0.0: the realm table (308 species, 13 realms) behind <code>realms</code>, off by default, with <code>realm &lt;name|auto|off&gt;</code> (e8cbda7, 466baec). Not run on the rig.', 'realms-built-untested; realm-placement-path'),
  ('Quieting animal-on-animal combat', 'done', 'v6.9.0 ALERTS, <code>alerts on</code> by default: combat alerts with no humanoid are dropped, the reports stay in the log (engine :6726; ECO A2: wolf &times; deer 3 dropped, 0 left; wolf man kept).', 'validator-backlog-stale (bl.quiet)'),
  ('A record of who eats whom, over time', 'parked', 'Ledger, Food web graph and overlay exist; the kill tally per pair is unbuilt.', 'bl-eats-history'),
  ('Placement is even; survival is not', 'parked', 'Unchanged. The water stocking job still places round-robin (engine :4494).', 'bl-water-balance'),
]
LBL = {'done': 'Done', 'part': 'Part-built', 'parked': 'Parked'}
CLS = {'done': 'grade-measured', 'part': 'grade-inferred', 'parked': 'grade-parked'}

def old_rows():
    r = []
    for name, st, where, now in OLD:
        r.append(f'        <tr><th scope="row">{name}</th><td><span class="chip {CLS[st]}">{LBL[st]}</span></td><td>{where}</td><td class="mono">{now}</td></tr>')
    return '\n'.join(r)

# ---- added by the review: items not in open-items.json
ADDED = [
  ('rv-public-release', 'high', 'The repository is private; nothing is public yet',
   'github.com/CannonCoPilot/seasonal-wildlife exists (master v6.9.0, pushed 30 Sep) but its visibility is PRIVATE. The Docket\'s ship-first verdict needs a public repository and a post in the r/dwarffortress thread (1ut4t9k); neither is an open item.',
   'gh repo view: visibility PRIVATE, pushedAt 2026-09-30', 'Ask the user with push-repos: go public at v7.0, and who writes the post.', 'push-repos; v70-release-steps'),
  ('rv-stale-plan-docs', 'medium', 'HANDOFF.md and PLAN.md describe tools that no longer exist',
   'HANDOFF.md describes the v3.1 engine and the v4 plan; PLAN.md is the v6 plan, rev 2 of 17 Sep, stopping around v6.0. A new reader meets them before STATE.md.',
   'brief, 1 Oct', 'Done 1 Oct: PLAN.md rev 3 (current state v5.11&ndash;v7.0, 26 v7 switches, 39 requirements with status, steps in order; rev 2 kept as Appendix A) and HANDOFF.md rewritten for v7.0. Keep PLAN.md current at each release.', 'usage-v7-docs'),
  ('rv-alpha-three', 'medium', 'Alpha Three: a walkthrough for v7.0',
   'Done 1 Oct (published). A GUI-only tester still needs the switches on the Panel (v7-switches-on-panel); the console steps use the USAGE v7.0 section drafted the same day.',
   'Alpha Two covered v6.6 (62 steps, round 1: 59 pass, 3 anomalies)', 'Published 1 Oct: <a href="https://claude.ai/artifact/7Y8RELyxkHxUV2bfPAeMei">Alpha Three</a> (v7.0 on DFHack 53.16-r2, 110 steps, console verbs included). Next: play round 1 after the r2 re-validation.', 'usage-v7-docs; v7-switches-on-panel'),
]

def added_cards(rows=None, label='Added 1 Oct'):
    out = []
    for iid, pri, title, detail, ev, nxt, dep in (rows if rows is not None else ADDED):
        out.append(f'''    <div class="item pri-{pri}" id="{iid}">
      <div class="item-head"><span class="chip pri">{pri}</span><span class="chip st">{label}</span><h3>{title}</h3></div>
      <p class="claim">{detail}</p>
      <dl>
        <dt>Evidence</dt><dd>{ev}</dd>
        <dt>Next</dt><dd>{nxt}</dd>
        <dt>Depends on</dt><dd>{dep}</dd>
      </dl>
      <p class="meta"><code>{iid}</code> · added by the 1 October review · not in open-items.json</p>
    </div>''')
    return '\n'.join(out)

pc = Counter(i['priority'] for i in OI['items'])
cc = Counter(i['category'] for i in OI['items'])
user_n = sum(1 for i in OI['items'] if i['status'] == 'awaiting-user')

def stage_html():
    out = []
    for n, (sid, title, lede, lst) in enumerate(STAGES):
        num = {'s1': '1', 's1b': '1b', 's2': '2', 's3': '3', 's4': '4', 's5': '&ndash;'}[sid]
        out.append(f'  <h2 id="{sid}"><span class="stage-n">{num}</span>{E(title)} <span class="count">{len(lst)}</span></h2>')
        out.append(f'  <p class="lede">{E(lede)}</p>')
        out.append('  <div class="items">')
        out.extend(card(i, d) for i, d in lst)
        out.append('  </div>')
    return '\n'.join(out)

def glance():
    rows = []
    for sid, title, lede, lst in STAGES:
        hi = sum(1 for i, _ in lst if items[i]['priority'] == 'high')
        usr = sum(1 for i, _ in lst if items[i]['status'] == 'awaiting-user')
        num = {'s1': '1', 's1b': '1b', 's2': '2', 's3': '3', 's4': '4', 's5': '&ndash;'}[sid]
        extra = 0
        rows.append(f'        <tr><td class="mono">{num}</td><th scope="row"><a href="#{sid}">{E(title)}</a></th><td class="mono">{len(lst) + extra}</td><td class="mono">{hi + extra}</td><td class="mono">{usr}</td></tr>')
    return '\n'.join(rows)

page = f'''<title>The Wildlife Backlog</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
  :root{{
    --paper:#E8EBEF; --card:#F3F5F8; --sunk:#DBE0E7; --rule:#C2CAD4; --rule-soft:#D3D9E1;
    --ink:#141821; --ink-mid:#48515F; --ink-faint:#6F7886;
    --accent:#2C4C7C; --accent-deep:#1D3557; --accent-wash:#DCE4F0;
    --measured:#1A6B54; --measured-wash:#D8E8E1;
    --inferred:#8A6014; --inferred-wash:#F2E7CF;
    --assumed:#9B3B2F; --assumed-wash:#F2DFDA;
    --measure:68ch;
  }}
  @media (prefers-color-scheme: dark){{ :root:not([data-theme="light"]){{
    color-scheme:dark;
    --paper:#0E1218; --card:#161B23; --sunk:#1F2630; --rule:#2C3542; --rule-soft:#232B36;
    --ink:#E3E8EF; --ink-mid:#A6B0BE; --ink-faint:#78828F;
    --accent:#7FA3D8; --accent-deep:#A8C3E8; --accent-wash:#16202E;
    --measured:#63C2A3; --measured-wash:#10201B;
    --inferred:#D7AC5E; --inferred-wash:#241E10;
    --assumed:#E08A78; --assumed-wash:#261512;
  }}}}
  :root[data-theme="dark"]{{
    color-scheme:dark;
    --paper:#0E1218; --card:#161B23; --sunk:#1F2630; --rule:#2C3542; --rule-soft:#232B36;
    --ink:#E3E8EF; --ink-mid:#A6B0BE; --ink-faint:#78828F;
    --accent:#7FA3D8; --accent-deep:#A8C3E8; --accent-wash:#16202E;
    --measured:#63C2A3; --measured-wash:#10201B;
    --inferred:#D7AC5E; --inferred-wash:#241E10;
    --assumed:#E08A78; --assumed-wash:#261512;
  }}

  *{{box-sizing:border-box;}}
  body{{
    margin:0; background:var(--paper); color:var(--ink);
    font-family:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;
    font-size:16px; line-height:1.6; -webkit-font-smoothing:antialiased;
  }}
  .wrap{{max-width:min(var(--measure), calc(100vw - 2rem)); margin:0 auto; padding-block:3.5rem 6rem;}}
  .wide{{max-width:min(96ch, calc(100vw - 2rem));}}

  .eyebrow{{
    font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    font-size:.72rem; letter-spacing:.14em; text-transform:uppercase;
    color:var(--ink-faint); display:flex; flex-wrap:wrap; gap:.9rem;
    padding-bottom:.9rem; border-bottom:1px solid var(--rule);
  }}
  h1{{
    font-family:"IBM Plex Serif",Georgia,serif; font-weight:700;
    font-size:clamp(2rem,5vw,2.9rem); line-height:1.12; letter-spacing:-.015em;
    text-wrap:balance; margin:1.6rem 0 .8rem;
  }}
  .standfirst{{font-size:1.06rem; color:var(--ink-mid); margin:0 0 1.2rem; text-wrap:pretty;}}
  .companions{{font-size:.92rem; color:var(--ink-mid); margin:0 0 2.4rem;}}

  .decided{{
    background:var(--accent-wash); border-left:3px solid var(--accent);
    padding:1.1rem 1.3rem; margin:0 0 2rem;
    display:flex; flex-direction:column; gap:.5rem;
  }}
  .decided .tag{{
    font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    font-size:.7rem; letter-spacing:.14em; text-transform:uppercase; color:var(--accent-deep);
  }}
  .decided p{{margin:0; color:var(--ink);}}

  h2{{
    font-family:"IBM Plex Serif",Georgia,serif; font-weight:600;
    font-size:1.5rem; letter-spacing:-.01em; margin:3.2rem 0 .4rem; text-wrap:balance;
    display:flex; align-items:baseline; gap:.7rem; flex-wrap:wrap;
  }}
  /* the stage number is real: the stages run in this order */
  .stage-n{{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:.95rem; font-weight:600; color:var(--accent);
    border:1px solid var(--accent); padding:.05rem .45rem; line-height:1.3;}}
  .count{{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:.8rem; font-weight:500; color:var(--ink-faint);}}
  .lede{{color:var(--ink-mid); margin:0 0 1.8rem; font-size:.97rem;}}

  .items{{display:flex; flex-direction:column; gap:2rem;}}
  .item{{
    border-left:3px solid var(--grade,var(--rule));
    padding-left:1.15rem;
    display:flex; flex-direction:column; gap:.65rem;
  }}
  .item-head{{display:flex; align-items:baseline; gap:.5rem .7rem; flex-wrap:wrap;}}
  .chip{{
    font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    font-size:.68rem; letter-spacing:.1em; text-transform:uppercase;
    color:var(--grade,var(--ink-faint)); background:var(--grade-wash,var(--sunk));
    padding:.16rem .5rem; white-space:nowrap;
  }}
  .chip.st{{color:var(--ink-mid); background:var(--sunk);}}
  .chip.st-user{{color:var(--accent-deep); background:var(--accent-wash); font-weight:600;}}
  .chip.st-done{{color:var(--measured); background:var(--measured-wash);}}
  .chip.st-blocked{{color:var(--assumed); background:var(--assumed-wash);}}
  h3{{
    font-family:"IBM Plex Serif",Georgia,serif; font-weight:600;
    font-size:1.13rem; margin:0; letter-spacing:-.005em; text-wrap:balance; flex-basis:100%;
  }}
  .claim{{margin:0; color:var(--ink); font-size:1rem;}}
  dl{{margin:.2rem 0 0; display:flex; flex-direction:column; gap:.55rem;}}
  dt{{
    font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    font-size:.68rem; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-faint);
  }}
  dd{{margin:.1rem 0 0; color:var(--ink-mid); font-size:.95rem;}}
  dd strong{{color:var(--ink); font-weight:600;}}
  dd.note1{{color:var(--ink); border-left:2px solid var(--inferred); padding-left:.6rem;}}
  .meta{{margin:0; font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:.72rem; color:var(--ink-faint); overflow-wrap:anywhere;}}
  code{{
    font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;
    font-size:.87em; background:var(--sunk); padding:.06em .32em; color:var(--ink);
  }}
  .grade-measured{{--grade:var(--measured); --grade-wash:var(--measured-wash);}}
  .grade-inferred{{--grade:var(--inferred); --grade-wash:var(--inferred-wash);}}
  .grade-assumed{{--grade:var(--assumed); --grade-wash:var(--assumed-wash);}}
  .grade-parked{{--grade:var(--ink-faint); --grade-wash:var(--sunk);}}
  /* priority sets the stripe: high red, medium amber, low the plain rule */
  .pri-high{{--grade:var(--assumed); --grade-wash:var(--assumed-wash);}}
  .pri-medium{{--grade:var(--inferred); --grade-wash:var(--inferred-wash);}}
  .pri-low{{--grade:var(--rule); --grade-wash:var(--sunk);}}
  .pri-low .chip.pri{{color:var(--ink-faint);}}

  .scroll{{overflow-x:auto; margin:0 0 1rem;}}
  table{{border-collapse:collapse; width:100%; font-size:.9rem; min-width:34rem;}}
  caption{{caption-side:top; text-align:left; font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:.72rem; color:var(--ink-faint); padding-bottom:.5rem;}}
  th,td{{text-align:left; vertical-align:top; padding:.5rem .8rem .5rem 0; border-bottom:1px solid var(--rule-soft);}}
  thead th{{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:.68rem; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-faint); font-weight:500; border-bottom:1px solid var(--rule);}}
  tbody th{{font-weight:600;}}
  td{{color:var(--ink-mid);}}
  .mono{{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace; font-size:.8rem; font-variant-numeric:tabular-nums; overflow-wrap:anywhere;}}

  footer{{
    margin-top:4.5rem; padding-top:1.4rem; border-top:1px solid var(--rule);
    color:var(--ink-faint); font-size:.86rem; display:flex; flex-direction:column; gap:.5rem;
  }}
  a{{color:var(--accent); text-underline-offset:.18em;}}
  a:focus-visible{{outline:2px solid var(--accent); outline-offset:2px;}}
</style>

<div class="wrap">
  <div class="eyebrow">
    <span>Backlog</span><span>seasonal-wildlife</span><span>v7.0 and after</span>
    <span>1 October 2026 (first drawn 18 September)</span><span>W2:Urist</span>
  </div>

  <h1>The Wildlife Backlog</h1>
  <p class="standfirst">The work queue for seasonal-wildlife on 1 October 2026. It holds all {len(items)} items in the ECO report's register ({sum(1 for i in OI['items'] if i['status'] != 'done')} open, {sum(1 for i in OI['items'] if i['status'] == 'done')} done during the 1 October review), with their ids, priority, sources and evidence, plus three gaps this review added. The thirteen candidates this page carried on 22 September are checked against STATE addenda 90&ndash;97 and git: seven are shipped, three part-built, the rest parked. The queue runs in four stages: re-validate on DFHack 53.16-r2 and release v7.0, the user's decisions, the v7.1 build, then the experiments, with two replicates per arm. {user_n} items wait on the user.</p>
  <p class="companions"><strong>Companion pages:</strong> <a href="{DK}">The Fortress Docket</a> (where this sits among all DF work) · <a href="{ECO}">ECO Wildlife Study</a> (the night's evidence) · <a href="{WP}">The Wilderpop Model</a> (the measurements) · <a href="{DS}">The Seasonal Wildlife Plugin</a> (the design) · <a href="{PT}">Seasonal Wildlife Playtest</a> · <a href="{A2}">Alpha Two</a> (walkthrough for v6.6) · <a href="https://claude.ai/artifact/7Y8RELyxkHxUV2bfPAeMei">Alpha Three</a> (walkthrough for v7.0 on DFHack 53.16-r2)</p>

  <div class="decided">
    <span class="tag">State · 1 October 2026</span>
    <p><strong>Released:</strong> v6.9.0, master <code>1abe109</code>, 30 September; validate-full 20260930-124923, 192 PASS, 0 FAIL; pushed to a private GitHub repository.</p>
    <p><strong>On the rig, not released:</strong> v7.0.0, branch <code>v7.0</code> at <code>1e65e03</code>, 26 commits past master, with roster-port, realm-pair, scav-ext and vermin-gobble merged in. Validate-full 20261001-074833: 214 PASS, 0 FAIL, 30 not testable here, 13 BACKLOG, 2 DOC-DRIFT (USAGE's header and the Docket's version line; the Docket is fixed in rev 16). Not merged, not pushed. <strong>Both runs were on DFHack 53.16-r1.1.</strong> The rig has run <strong>53.16-r2</strong> (02e77acf) since about 08:55 on 1 October, and nothing has been validated on it yet.</p>
    <p><strong>v7.0 defaults</strong> (engine line 499): on &mdash; aligned, cave_aligned, fanciful, leader_male, layer_groups, seasons_own, solo, scav_mapwide, scav_ext, civ_hunt, civ_prey, fb_safe, sweep, sponges, gate_drain, gobble, builder; pack_floor 0.05, pack_sneak 0.25, outgun 2.0, gobble_creature_fallback 3. Off &mdash; fishers, fish_breathe, domestic, outgun_cap, realms. Ecology cadence 1,500. All set from the console only (<code>seasonal-wildlife v7</code>).</p>
  </div>

  <div class="decided">
    <span class="tag">Decided · still applies</span>
    <p><strong>A managed cavern raid is an <em>irruption</em>.</strong> The word "raid" belongs to Dwarf Fortress's own invasion machinery, which this tool never touches; what the tool does is raise pressure on a cavern layer until a wave arrives angry. Irruption is the ecological term for exactly that — a population surging out of its usual range — and it keeps the tool's vocabulary honest about what it is doing. The v6.1 package is named <strong>Cavern pressure and irruptions</strong>, and the term carries through the plugin's console, its guide and the reports.</p>
  </div>

  <div class="decided">
    <span class="tag">Standing rule · since 18 September</span>
    <p><strong>Never write FREQUENCY 0. Write 1.</strong> Zeroing <code>CREEPY_CRAWLER</code>, the only underground <code>VERMIN_ROTTER</code>, freezes DF silently and for good; 1 against a typical 50 or 100 suppresses as well and is safe. The 18 September finding that "the cavern layer was never actually managed" is resolved: the cavern ceiling holds managed species at frequency 1 (v5.8.1), and irruptions shipped armed, not aimed, on what E29 and E23 allow (v6.1; T9 and T9b passed 2 of 2). Engine v7.0 :2954 still carries the rule.</p>
  </div>

  <h2>The sequence at a glance</h2>
  <p class="lede">Each stage needs the one before it, except where an item's &ldquo;Depends on&rdquo; says otherwise. Desk reads in stage 4 can run any time.</p>
  <div class="scroll">
    <table>
      <caption>Open items by stage · priorities: {pc['high']} high, {pc['medium']} medium, {pc['low']} low</caption>
      <thead><tr><th scope="col">Stage</th><th scope="col">What</th><th scope="col">Items</th><th scope="col">High</th><th scope="col">Your call</th></tr></thead>
      <tbody>
{glance()}
      </tbody>
    </table>
  </div>

  <h2 id="old">The old backlog, checked</h2>
  <p class="lede">The thirteen candidates of 22 September, each with what happened to it and the open item that carries what is left. Nothing was dropped.</p>
  <div class="scroll">
    <table>
      <thead><tr><th scope="col">Candidate (22 Sep)</th><th scope="col">1 Oct</th><th scope="col">Where</th><th scope="col">Open item now</th></tr></thead>
      <tbody>
{old_rows()}
      </tbody>
    </table>
  </div>

{stage_html()}

  <h2 id="added">Added by the 1 October review <span class="count">{len(ADDED)}</span></h2>
  <p class="lede">Gaps not in the open-items register.</p>
  <div class="items">
{added_cards()}
  </div>

  <footer>
    <div>Items, ids, priorities, statuses, evidence and sources are from DwarfCron <code>data/eco-report/open-items.json</code> ({E(OI['generated'][:10])}; categories: {', '.join(f"{E(x['title'])} {cc[x['id']]}" for x in OI['categories'])}). Stage, &ldquo;Depends on&rdquo; and the &ldquo;Checked 1 October&rdquo; notes are this page's.</div>
    <div>Revisions: first drawn 18 September (thirteen candidates beyond v6.2); 22 September, part-built notes after v6.2.0; 1 October, rebuilt around the open-items register after v7.0 and the ECO study, the old candidates kept in the table above.</div>
    <div>Experiments here run two replicates per arm. No rig was run to write this page. Validation figures quoted are from DFHack 53.16-r1.1; the rig runs 53.16-r2 since 1 October.</div>
  </footer>
</div>
'''
open(f'{ROOT}/.claude/scratch/wildlife-backlog.html', 'w').write(page)
print('ok', len(page), 'items', len(placed), 'added', len(ADDED))
