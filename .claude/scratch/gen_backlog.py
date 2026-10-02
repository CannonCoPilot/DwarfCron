#!/usr/bin/env python3
"""Generate The Wildlife Backlog (1 Oct 2026, evening) from DwarfCron data/eco-report/open-items.json
as revised after the user's review Parts 1 and 2 (95 items; statuses built-untested, test stage, held, decided ...).
Output: .claude/scratch/wildlife-backlog.html in this worktree (the page's local source)."""
import json, html, sys
from collections import Counter

ROOT = '/Users/nathanielcannon/Claude/Projects/dc-wt/pages'
OI = json.load(open(f'{ROOT}/data/eco-report/open-items.json'))
items = {i['id']: i for i in OI['items']}
assert len(items) == 95, len(items)
E = html.escape

WP = 'https://claude.ai/code/artifact/6cebd06e-eafd-44a8-aa6e-d3c108e5fcba'
DS = 'https://claude.ai/code/artifact/a61b06b2-4687-41ea-91f0-2216220d7111'
PT = 'https://claude.ai/code/artifact/3f8ce1ed-4db3-4482-97fa-c27b2eaded7e'
ECO = 'https://claude.ai/artifact/UY2KevMooCW4mRr5F19M26'
A2 = 'https://claude.ai/artifact/3qMtYL2M5K4CRUEwSGKR4W'
A3 = 'https://claude.ai/artifact/7Y8RELyxkHxUV2bfPAeMei'
A4 = 'https://claude.ai/artifact/RCdoPTWhabmMBQQw2azpHr'
DK = 'https://claude.ai/code/artifact/4dac86e8-4f3c-4480-a8d4-8eed3deb5672'

# ---- review notes on individual items (checks against git on the evening of 1 Oct; shown on the item)
NOTES = {
    'push-repos': 'origin/v7.1 is at b7df045 (v7.1-docs merged and pushed). The GitHub repository is still private (gh repo view), so a push publishes nothing; going public is rv-public-release. DwarfCron Dev is 21 commits past origin/Dev in the pages worktree.',
    'state-v68-v69-addenda': 'Written as STATE addendum 99 on the v7.1 branch (a4d8f14, in b7df045). The item closes when v7.1 reaches master.',
    'validator-v70-coverage': 'phase_v71 now carries 149 claims (DwarfCron dee9d58; experiments/VALIDATOR-v71.md). A dry run against the v7.1 tip is clean (luac53, engine names, verbs). None has run on DF.',
    'v70-release-steps': 'v7.0 is not released on its own. PLAN rev 4 step 5 merges v7.1 to master on a passing validate-full on DFHack 53.16-r2, and pushes on the user\'s word.',
    'createunit-upstream': 'Branch create-unit-units-create at fd8681f0 in GitRepos/dfhack-scripts-createunit, on DFHack/scripts master 5d5fb16b (53.16-r2 changelog). Local only. PR-DRAFT.md holds the description and a rig test plan, which has not run. Opening the PR needs the user\'s OK.',
    'alpha-cli-round-and-playtest': 'Alpha Four, a walkthrough of v7.1 by its central features (109 steps), was published on 1 October. It has not been played. The playtest republish stays held.',
    'usage-v7-docs': 'USAGE.md is now the v7.1 guide (v7.1 branch, b7df045).',
}

# ---- stages: (id, number, title, lede, dt label for the dependency row, [(item id, text)])
STAGES = [
  ('s1', '1', 'Testing stage: DFHack r2 and the validator', 'PLAN rev 4 step 1. Every rig step needs the user\'s go and a free rig. Re-validate v7.0 on DFHack 53.16-r2, deploy v7.1 with all five scripts, run phase_v71, and fix the harness and validator items that would make the runs lie.', 'Depends on', [
    ('revalidate-dfhack-r2', 'Nothing. Do first: every later rig run and every number in stages 2 and 3 depends on it.'),
    ('validator-v70-coverage', 'revalidate-dfhack-r2 for the run. The claims are written (149, dry-run clean); they need v7.1 deployed with seasonal-wildlife-controls.lua.'),
    ('validator-full-run-nt', 'Nothing. Lands with the phase_v71 run, so the full run sets up its own subjects.'),
    ('harness-readout-nits', 'Nothing. Before the first region8 block reads a tally.'),
    ('arena-order-and-wildness', 'revalidate-dfhack-r2 (the harness\'s spawn and tp use Units::teleport). Smoke on one region8 fort before any arena block.'),
    ('validator-v70-nt-forts', 'test-region8-forts: the forts give these claims their subjects.'),
  ]),
  ('s2', '2', 'Testing stage: the region8 forts and the experiment queue', 'PLAN rev 4 steps 2 and 3. Every experiment runs on region8 ("The Last Planets"), n = 5 reps per arm with short reps, a fresh load per arm in counterbalanced order, every animal wiped before a cell places anything, and a subject receipt before any arm is compared (R11, R12, R15). Defaults change only on these results.', 'Depends on', [
    ('test-region8-forts', 'Stage 1. Read region8\'s REAL_WORLD_EXTINCT setting at the same time (test-extinct).'),
    ('test-fq1-lpp1', 'test-region8-forts. Closes ladder-drop-apx-step\'s FREQUENCY side.'),
    ('test-g2-groups', 'test-region8-forts. Closes the per-layer caps and the adaptive clock (R7, R31), the cavern gate and water like land.'),
    ('test-irruption', 'test-region8-forts with a civ race in its caverns. M1-M9 first; the A/B/C arms only after them, with fort survival 5 of 5 as the safety criterion.'),
    ('test-ladder-pyramid', 'test-region8-forts. Closes builder-port-vs-v22, ladder-units-vs-waves and the apex scheduler.'),
    ('test-water', 'test-region8-forts (an ocean fort, the shallowest available, and a lake).'),
    ('test-scav-vermin', 'test-region8-forts.'),
    ('test-cbx-wild1', 'test-region8-forts.'),
    ('test-snk-eng', 'test-region8-forts. SNK-L is post-alpha (R8).'),
    ('test-extinct', 'Region8\'s extinct setting. If the world has no extinct entries, another fort.'),
    ('test-pmh1', 'test-region8-forts and the wound logger (desk work, before the rig is free).'),
    ('sw8-confirm', 'Every default ruling is built; runs with the other confirmations, last before release.'),
    ('perf3-unit-count', 'revalidate-dfhack-r2. Read with PERF0-PERF4 (perf-v71-caching).'),
    ('v70-job-cost-and-sweep', 'The perf verb (v7.1 P0) reads the costs; any season run.'),
    ('scav-attribution-and-fallbacks', 'test-scav-vermin (the same SCV3 cells, with v7.1\'s attribution).'),
    ('apex-placement-stock-test', 'test-ladder-pyramid (APX1).'),
    ('flier-pool-steering', 'A desk check of a region8 fort\'s flier entries first.'),
    ('orca-stranding-n', 'test-water. Needs deep ocean columns; v7.1\'s full-column survey says where.'),
    ('solo-package-natural-density', 'test-snk-eng.'),
    ('single-run-defaults', 'Nothing. L3 and A3 in ECO-design.md \'Next experiments\'.'),
    ('lp-separate-pool', 'Low; R63 calls it not applicable now the apex step is gone. Shares FQ1\'s loads if run.'),
  ]),
  ('s3', '3', 'Testing stage: what v7.1 built, waiting on a test', 'The user ruled on all of these on 1 October (R1-R63) and v7.1 built each one, under the directive to build first on an optimistic stance and test after. None has run on the rig. Each card names the claim or test that closes it; they run inside stages 1 and 2. Three proposals were rejected by the ruling, and the ruling\'s own design is what was built.', 'Closed by', [
    ('dflt-ecology-cadence-3000', 'CAD1 and SW8; the default claim in phase_v71.'),
    ('dflt-nudge-off', 'SW8; the default claim in phase_v71.'),
    ('dflt-pack-sneak-0', 'SKL1-2, PK2 and SNK1-3 (test-snk-eng); SNK-L post-alpha.'),
    ('builder-drop-x3-pack-bonus', 'The AP1 desk tally, then an SW7 rerun on a region8 fort (test-ladder-pyramid).'),
    ('ladder-drop-apx-step', 'test-fq1-lpp1 and APX1 (test-ladder-pyramid).'),
    ('cavern-limit-soft-target', 'CAVG (test-g2-groups).'),
    ('water-groups-default-2', 'WAT5 and G2r per water body (test-g2-groups, test-water).'),
    ('cavern-animal-person-group-cap', 'APC1 (test-g2-groups); T-R35 with the irruption.'),
    ('add-invasive-savage-placement', 'INV3: a placed smilodon holds a season on a calm region8 fort.'),
    ('scav-carnivorous-swimmers', 'SCV3\'s water arms (test-scav-vermin).'),
    ('lake-apex-gap', 'FSH3 and FSH4 (test-water) and a lake roster check.'),
    ('builder-port-vs-v22', 'LAD1 (test-ladder-pyramid).'),
    ('ladder-units-vs-waves', 'LAD1 (test-ladder-pyramid).'),
    ('builder-reach-table-refresh', 'STP1, the raptor stoop (test-ladder-pyramid).'),
    ('flying-raptor-slot', 'The flying claim in phase_v71; LAD1.'),
    ('lamprey-not-apex', 'The water apex-limit claim; a lake roster check.'),
    ('port-gobble-edge-table', 'The R20 vermin suite (test-scav-vermin).'),
    ('pelagic-slot-shallow-maps', 'PEL1 and PELA on the ocean fort (test-water).'),
    ('animal-person-mass', 'The AP mass claim; AP1.'),
    ('animal-person-freq-zero', 'The FREQUENCY-floor claim.'),
    ('antman-civ-class', 'The civ claim on a region8 fort with a civ race in its caverns.'),
    ('realms-built-untested', 'The realm-table claim, then a realm rig test.'),
    ('natural-skill-unverified', 'SKL1-2 readback receipts; the rust floor needs unit_skill.natural_skill_lvl, which may be absent on r1.1.'),
    ('bl-water-balance', 'MIX1 (test-water).'),
    ('bl-grouping-table', 'The cohesion claim; COHT and F3.'),
    ('tool-pred-cfg', 'The roster pred claim in phase_v71.'),
    ('v7-switches-on-panel', 'The GUI round trips: every Panel section on the rig, narrow screen included.'),
    ('web-v7-state', 'luasocket on r2 (revalidate-dfhack-r2), then the page round trips.'),
    ('perf-v71-caching', 'PERF0-PERF4.'),
    ('perf-v72-native-slicing', 'PERF0-PERF4; forEachTile is experimental and one raise turns it off for the session.'),
    ('scav-status-diagnostics', 'The fixes claims in phase_v71; F1-F6.'),
    ('spaced-raw-ids-cli', 'The ids claim (HONEY BADGER quoted, #N, SEA_OTTER).'),
    ('cache-world-switch-stale', 'A second world loaded in one DFHack session; the fixes claims.'),
    ('web-cluster-order', 'The web claims; a wolf pack reads min to max.'),
  ]),
  ('s4', '4', 'Release v7.1', 'PLAN rev 4 step 5, after the tests and after alpha phase two (held to the end, R62). v7.1 goes to master on a passing validate-full, with every untested feature named as such in USAGE and the release addendum. The push waits on the user\'s word; so does the create-unit pull request.', 'Depends on', [
    ('v70-release-steps', 'Stages 1-3 and the release gate (luac53 and luacheck on five scripts, five-script deploy, validate-full 0 FAIL, saves byte-identical, the offline harnesses).'),
    ('state-v68-v69-addenda', 'The merge of v7.1 to master.'),
    ('findings-more-slips', 'Nothing.'),
    ('claude-doc-sync', 'Nothing. Low value unless the doc\'s comment threads stay in use.'),
    ('createunit-upstream', 'The user\'s OK, then the rig test in PR-DRAFT.md.'),
  ]),
  ('s5', '&ndash;', 'Held or decided', 'Held by the user (R46, R62, R63), or decided with nothing left to do while the ruling stands.', 'Depends on', [
    ('alpha-cli-round-and-playtest', 'The end of testing (R62): then rebuild the alpha walkthrough and the playtest page for v7.1.'),
    ('fps6-resume-or-drop', 'The user (R46: hold).'),
    ('cavern-traffic-limit', 'More testing later (R63).'),
    ('gobble-feeds', 'Low priority (R63).'),
    ('vermin-stock-bookkeeping', 'gobble-feeds.'),
    ('invasion-exclusion-unvalidated', 'DF re-enabling invasions (R4, R23).'),
    ('deep-layer-demons', 'Nothing (R60).'),
  ]),
  ('s6', '&ndash;', 'Parked', 'Recorded so they are not lost. None scheduled.', 'Depends on', [
    ('realm-placement-path', 'realms-built-untested.'),
    ('bl-eats-history', 'Nothing. v7.1\'s scavenging attribution and vermin eats ledger are a start.'),
    ('bl-misc-curiosities', 'Nothing.'),
    ('design-s7-unmeasured-cells', 'A tool feature that needs one.'),
    ('fva-parked', 'Nothing.'),
    ('leader-size-in-fight', 'Nothing.'),
    ('otter-eats-jaguar-man', 'A player objection.'),
    ('old-wilderpop-e27b-e31c', 'Nothing.'),
    ('irruption-aimed', 'Nothing; IRRUPT v2\'s M-probes may reopen it.'),
  ]),
  ('s7', '&#10003;', 'Done', 'Done on 1 October, kept so the register is whole.', 'Depends on', [
    ('push-repos', 'Done (R39).'),
    ('usage-v7-docs', 'Done.'),
    ('commit-uncommitted-work', 'Done (DwarfCron 1c71037).'),
    ('state-addenda-refresh', 'Done.'),
    ('validator-backlog-stale', 'Done (the v7.1 harness).'),
    ('validator-cli-water-dup', 'Done (the v7.1 harness).'),
    ('cx-probe-invasion-exclusion', 'Done (the v7.1 harness).'),
    ('chronicler-weather-lookup', 'Done (the v7.1 harness).'),
    ('gobble-stale-comment', 'Done (v7.1 vermin stream).'),
    ('report-stale-cells', 'Done.'),
    ('report-done-count', 'Done.'),
    ('design-md-stale', 'Done.'),
    ('findings-small-discrepancies', 'Done.'),
  ]),
]

placed = [i for _, _, _, _, _, lst in STAGES for i, _ in lst]
c = Counter(placed)
dups = [k for k, v in c.items() if v > 1]
missing = set(items) - set(placed)
extra = set(placed) - set(items)
if dups or missing or extra:
    sys.exit(f'dups {dups} missing {missing} extra {extra}')

# every status the register uses has a label; the testing-stage rules hold
STATUS = {
    'done': 'Done 1 Oct',
    'built, untested (v7.1)': 'Built, untested',
    'rejected by ruling; built, untested (v7.1)': 'Ruled otherwise; built, untested',
    'built, untested (harness)': 'Built, untested (harness)',
    'built, PR drafted (not opened)': 'PR drafted; your OK',
    'test stage': 'Testing stage',
    'open': 'Open',
    'held': 'Held',
    'decided': 'Decided',
    'parked': 'Parked',
}
ST_CLS = {
    'done': 'st-done', 'built, untested (v7.1)': 'st-built', 'rejected by ruling; built, untested (v7.1)': 'st-built',
    'built, untested (harness)': 'st-built', 'built, PR drafted (not opened)': 'st-user', 'test stage': 'st-test',
}
unknown = {i['status'] for i in OI['items']} - set(STATUS)
assert not unknown, unknown
where = {i: sid for sid, _, _, _, _, lst in STAGES for i, _ in lst}
for i in OI['items']:
    st, sid = i['status'], where[i['id']]
    if st in ('built, untested (v7.1)', 'rejected by ruling; built, untested (v7.1)'):
        assert sid == 's3', (i['id'], sid)
    if st == 'test stage':
        assert sid in ('s1', 's2'), (i['id'], sid)
    if st == 'done':
        assert sid == 's7', (i['id'], sid)
    if st == 'parked':
        assert sid == 's6', (i['id'], sid)
    if st in ('held', 'decided'):
        assert sid == 's5', (i['id'], sid)
    if i['category'] == 'testing':
        assert sid == 's2', (i['id'], sid)
BUILT = ('built, untested (v7.1)', 'rejected by ruling; built, untested (v7.1)', 'built, untested (harness)')
CAT = {x['id']: x['title'] for x in OI['categories']}
def card(iid, dep, dtl='Depends on'):
    i = items[iid]
    pri = i['priority']
    st = i['status']
    srcs = ' · '.join(E(s) for s in i['source'])
    note = NOTES.get(iid)
    st_cls = ST_CLS.get(st, 'st')
    out = [f'    <div class="item pri-{pri}" id="{E(iid)}">',
           f'      <div class="item-head"><span class="chip pri">{pri}</span><span class="chip {st_cls}">{STATUS[st]}</span><h3>{E(i["title"])}</h3></div>',
           f'      <p class="claim">{E(i["detail"])}</p>',
           '      <dl>']
    if i.get('evidence'):
        out.append(f'        <dt>Evidence</dt><dd>{E(i["evidence"])}</dd>')
    out += [
           f'        <dt>Next</dt><dd>{E(i["next"])}</dd>',
           f'        <dt>{dtl}</dt><dd>{E(dep)}</dd>']
    if note:
        out.append(f'        <dt>Checked 1 October, evening</dt><dd class="note1">{E(note)}</dd>')
    out += ['      </dl>',
            f'      <p class="meta"><code>{E(iid)}</code> · {E(CAT[i["category"]])}' + (f' · effort {E(i["effort"])}' if i.get('effort') else '') + f' · {srcs}</p>',
            '    </div>']
    return '\n'.join(out)

# ---- the old backlog, checked (22 Sep candidates; status as of v7.1, 1 Oct evening)
OLD = [
  ('Frequency as the balance lever', 'done', 'v6.5.0: <code>odds</code> is the raw\'s FREQUENCY per species; the tool writes 1, never 0. Comparative weight confirmed (E36, E21b; X3 on the surface). v7.1 floors the 19 animal people at FREQUENCY 0 to 1 (R61).', 'shipped; validator-backlog-stale done'),
  ('Population number needs no adjustment', 'done', 'v6.5.0: <code>stock</code> is the reserve in the region, debited per arrival and refunded on leaving (STATE 94; USAGE &ldquo;Stock is the reserve&rdquo;).', 'shipped; validator-backlog-stale done'),
  ('Solitary, pack or herd for every creature', 'built', 'v7.1: <code>MODEL.cohesionOf</code>, the whole-list solitary/pack/herd/flock/school table with per-species overrides; leaders, skills and pack detection read it (R62). Not run on the rig.', 'bl-grouping-table'),
  ('The largest male leads', 'built', 'v7.0.0 <code>leader_male</code>; v7.1 makes it the rule: no adult male, no leader, and a lost leader is never replaced and sets off a panic (R32). Rig: largest-male and lowest-id leaders held a group equally well (L2, COH).', 'test-g2-groups (PAN1); leader-size-in-fight'),
  ('Concurrency from the size of the embark', 'built', 'v6.9.0 land <code>auto</code> = floor(&radic;tiles) + 1. v7.1: every layer, each water body and each cavern has its own cap from map size, or one fixed cap by toggle (R7), approached by the adaptive release clock (R31); the caverns gated at 5 (R44).', 'test-g2-groups; cavern-limit-soft-target'),
  ('Deep water is a property of the map', 'built', 'v7.1: the full-column depth survey, column depth kept apart from tile water level (R22), and a pelagic slot on any ocean (R14, R59). OCEAN2 had no column three levels deep.', 'pelagic-slot-shallow-maps; orca-stranding-n'),
  ('Migrants are not broken', 'parked', 'Unchanged. Migration works on DF\'s schedule; the forcing trigger is the open question.', 'bl-misc-curiosities'),
  ('Birds already perch', 'parked', 'Unchanged.', 'bl-misc-curiosities'),
  ('The creature that showed as r2 and r4', 'parked', 'Unchanged.', 'bl-misc-curiosities'),
  ('Grouping creatures by where on Earth they belong', 'built', 'v7.0.0: the realm table (308 species, 13 realms) behind <code>realms</code>, off by default. v7.1 adds <code>realm table</code> and fixes OCE being refused for ocean species (R57). Not run on the rig.', 'realms-built-untested; realm-placement-path'),
  ('Quieting animal-on-animal combat', 'done', 'v6.9.0 ALERTS, <code>alerts on</code> by default: combat alerts with no humanoid are dropped, the reports stay in the log (ECO A2).', 'shipped; validator-backlog-stale done'),
  ('A record of who eats whom, over time', 'parked', 'Ledger, Food web graph and overlay exist. v7.1 adds scavenging attribution (<code>scavenge stats</code>) and <code>vermin eats</code>; the kill tally per pair is unbuilt.', 'bl-eats-history'),
  ('Placement is even; survival is not', 'built', 'v7.1: each water body\'s draw is weighted by what is swimming there now (balance, feed and pyramid factors, an apex limit; R62).', 'bl-water-balance'),
]
LBL = {'done': 'Done', 'built': 'Built, untested', 'part': 'Part-built', 'parked': 'Parked'}
CLS = {'done': 'grade-measured', 'built': 'grade-inferred', 'part': 'grade-inferred', 'parked': 'grade-parked'}

def old_rows():
    r = []
    for name, st, where, now in OLD:
        r.append(f'        <tr><th scope="row">{name}</th><td><span class="chip {CLS[st]}">{LBL[st]}</span></td><td>{where}</td><td class="mono">{now}</td></tr>')
    return '\n'.join(r)

# ---- added by the reviews: items not in open-items.json
ADDED = [
  ('rv-public-release', 'high', 'Open', 'The repository is private; nothing is public yet',
   'github.com/CannonCoPilot/seasonal-wildlife holds master (v6.9.0), v7.0 (99c1ec8) and v7.1 (b7df045), all pushed, but its visibility is PRIVATE. The Docket\'s ship-first verdict needs a public repository and a post in the r/dwarffortress thread (1ut4t9k); neither is an open item.',
   'gh repo view, 1 Oct evening: visibility PRIVATE, pushedAt 2026-10-02 00:14 UTC', 'Ask the user at v7.1\'s release: go public, and who writes the post.', 'v70-release-steps (the v7.1 release)'),
  ('rv-stale-plan-docs', 'medium', 'Done 1 Oct', 'HANDOFF.md and PLAN.md describe tools that no longer exist',
   'Done 1 Oct, twice: PLAN.md rev 3 in the morning for v7.0, and PLAN.md rev 4 in the evening for v7.1 (built, untested; requirements Q1-Q63 with status; the testing stage in order; rev 3 and rev 2 kept below it). HANDOFF.md and README.md are at v7.1 (five scripts; seasonal-wildlife-controls.lua is new and the deploy must copy it).',
   'seasonal-wildlife v7.1: 1714bb8 (PLAN rev 4), f71f46f (HANDOFF, README)', 'Keep PLAN.md current at each release.', 'Nothing.'),
  ('rv-alpha-four', 'medium', 'Published 1 Oct', 'Alpha Four: a walkthrough for v7.1',
   'Published 1 Oct: <a href="https://claude.ai/artifact/RCdoPTWhabmMBQQw2azpHr">Alpha Four</a>, seasonal-wildlife v7.1 at fce7d68 on region8 and DFHack 53.16-r2, 109 steps in the user\'s order of central features (biodiversity above the vanilla seven, active ecosystems in every layer, seasonal food webs, ecological realism, cavern mechanics, other), each grouped by surface: the window, the console, the browser companion. Every step is built, untested and expected by design. Alpha Three (v7.0, 110 steps) stays published.',
   'DwarfCron a544b7e (gen_alpha4.py)', 'Play it only after the testing stage: R62 holds alpha phase two to the end.', 'alpha-cli-round-and-playtest; stages 1-2'),
]

def added_cards(rows=None):
    out = []
    for iid, pri, label, title, detail, ev, nxt, dep in (rows if rows is not None else ADDED):
        cls = 'st-done' if label.startswith(('Done', 'Published')) else 'st'
        out.append(f'''    <div class="item pri-{pri}" id="{iid}">
      <div class="item-head"><span class="chip pri">{pri}</span><span class="chip {cls}">{label}</span><h3>{title}</h3></div>
      <p class="claim">{detail}</p>
      <dl>
        <dt>Evidence</dt><dd>{ev}</dd>
        <dt>Next</dt><dd>{nxt}</dd>
        <dt>Depends on</dt><dd>{dep}</dd>
      </dl>
      <p class="meta"><code>{iid}</code> · added by this page's 1 October reviews · not in open-items.json</p>
    </div>''')
    return '\n'.join(out)

pc = Counter(i['priority'] for i in OI['items'])
cc = Counter(i['category'] for i in OI['items'])
built_n = sum(1 for i in OI['items'] if i['status'] in BUILT)
test_n = sum(1 for i in OI['items'] if i['status'] == 'test stage')
done_n = sum(1 for i in OI['items'] if i['status'] == 'done')

def stage_html():
    out = []
    for sid, num, title, lede, dtl, lst in STAGES:
        out.append(f'  <h2 id="{sid}"><span class="stage-n">{num}</span>{E(title)} <span class="count">{len(lst)}</span></h2>')
        out.append(f'  <p class="lede">{E(lede)}</p>')
        out.append('  <div class="items">')
        out.extend(card(i, d, dtl) for i, d in lst)
        out.append('  </div>')
    return '\n'.join(out)

def glance():
    rows = []
    for sid, num, title, lede, dtl, lst in STAGES:
        hi = sum(1 for i, _ in lst if items[i]['priority'] == 'high' and items[i]['status'] != 'done')
        bu = sum(1 for i, _ in lst if items[i]['status'] in BUILT)
        rows.append(f'        <tr><td class="mono">{num}</td><th scope="row"><a href="#{sid}">{E(title)}</a></th><td class="mono">{len(lst)}</td><td class="mono">{hi}</td><td class="mono">{bu}</td></tr>')
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
  .chip.st-built{{color:var(--inferred); background:var(--inferred-wash); font-weight:600;}}
  .chip.st-test{{color:var(--accent); background:var(--accent-wash);}}
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
    <span>Backlog</span><span>seasonal-wildlife</span><span>v7.1 built, untested</span>
    <span>1 October 2026, evening (first drawn 18 September)</span><span>W2:Urist</span>
  </div>

  <h1>The Wildlife Backlog</h1>
  <p class="standfirst">The work queue for seasonal-wildlife on the evening of 1 October 2026. The user ruled on the whole ECO study that day, in two parts (R1&ndash;R63), and directed the work: build everything first, then test. v7.1 is that build. This page holds all {len(items)} items in the ECO report's register: {built_n} built and waiting on a test ({built_n - 1} in v7.1, one in the harness), {test_n} testing-stage tasks and experiments, {done_n} done, and the rest open, held, decided or parked. It also carries the three gaps this page added. The queue now runs as one testing stage: re-validate on DFHack 53.16-r2 and run the validator, build the region8 forts and run the experiments at n = 5 reps per arm, and close each built feature by its test. Then v7.1 is released to master. Nothing waits on a ruling. Two things wait on the user's word: the push at release, and the create-unit pull request.</p>
  <p class="companions"><strong>Companion pages:</strong> <a href="{DK}">The Fortress Docket</a> (where this sits among all DF work) · <a href="{ECO}">ECO Wildlife Study</a> (the evidence and both review parts, rev 7) · <a href="{WP}">The Wilderpop Model</a> (the measurements) · <a href="{DS}">The Seasonal Wildlife Plugin</a> (the design) · <a href="{PT}">Seasonal Wildlife Playtest</a> · <a href="{A2}">Alpha Two</a> (walkthrough for v6.6) · <a href="{A3}">Alpha Three</a> (walkthrough for v7.0) · <a href="{A4}">Alpha Four</a> (walkthrough for v7.1 on region8 and DFHack 53.16-r2, by central feature)</p>

  <div class="decided">
    <span class="tag">State · 1 October 2026, evening</span>
    <p><strong>Released:</strong> v6.9.0, master <code>1abe109</code>, 30 September; validate-full 20260930-124923, 192 PASS, 0 FAIL (STATE addendum 99).</p>
    <p><strong>Pushed, not merged:</strong> v7.0.0, branch <code>v7.0</code> at <code>99c1ec8</code>; validate-full 20261001-074833, 214 PASS, 0 FAIL, on DFHack 53.16-r1.1 (addendum 98). It will not be released on its own.</p>
    <p><strong>Built, untested:</strong> <strong>v7.1.0</strong>, branch <code>v7.1</code> at <code>b7df045</code> (pushed): twelve stream merges ending at <code>fce7d68</code>, then the docs (USAGE as the v7.1 guide, STATE addenda 99 and 100, PLAN rev 4, HANDOFF, README). Engine 15,943 lines (v7.0: 8,125), window 2,750, web server 631 and page 1,298, and a fifth script, <code>seasonal-wildlife-controls.lua</code> (1,059), the control registry the Panel, the web page and the console share. Offline only: <code>luac53</code> on all scripts, luacheck at the baseline, the web harness 424 pass and the GUI harness 0 fail. <strong>Nothing in v7.1 has run on the rig, and nothing at all has run on DFHack 53.16-r2</strong>, which the rig has carried since about 08:55 on 1 October.</p>
    <p><strong>Beside it, in DwarfCron:</strong> the v7.1 harness (a9a7528: n = 5 counterbalanced fresh-load blocks, a wipe per cell, manipulation checks, region8 by default), the region8 1&times;1 fort embarker (8b157eb), and phase_v71 with 149 claims (dee9d58), all built at the desk and untested. The create-unit port is drafted in GitRepos/dfhack-scripts-createunit, and no pull request has been opened.</p>
  </div>

  <div class="decided">
    <span class="tag">Ruled · 1 October 2026</span>
    <p><strong>All thirteen decisions this page carried are ruled</strong> (DwarfCron <code>data/eco-review/part2/USER-REVIEW-PART2.md</code>). Yes: ecology cadence 3,000 (R37), nudge off (R38), drop the apex step and steer apexes by placement (R34, with the pyramid targets of R9), carnivorous swimmers scavenge (R42, sharks included), an animal-person group cap in caverns lifted during an irruption (R35), Add invasive places SAVAGE species itself (R36), push (R39). Rejected as proposed, with a different design built: the SNEAK write stays and skills span 0&ndash;20 (R8, R40, R58); the &times;3 pack bonus stays and was fixed (R41); no &ldquo;2 per body&rdquo; for water, which is managed like land (R45); the caverns are gated by the tool at 5 groups (R44); the lake apex comes from fishing bears and a curated aquatic list, never the sea lamprey (R43, R49). Held: FPS6 (R46). The lead's water decision (the layer on wherever the map has water, and a body short of in-season species borrowing the season) was confirmed by the user.</p>
    <p><strong>The testing protocol (R11, R12, R15).</strong> Every test runs on region8 (world Snospdastrasp, &ldquo;The Last Planets&rdquo;), at n = 5 reps per arm with short reps, a fresh load per arm in counterbalanced order, and every animal wiped from the map before a cell places anything. This replaces the two-replicate rule of 17 September.</p>
  </div>

  <div class="decided">
    <span class="tag">Decided · still applies</span>
    <p><strong>A managed cavern raid is an <em>irruption</em>.</strong> The word "raid" belongs to Dwarf Fortress's own invasion machinery, which this tool never touches; what the tool does is raise pressure on a cavern layer until a wave arrives angry. Irruption is the ecological term for exactly that — a population surging out of its usual range — and it keeps the tool's vocabulary honest about what it is doing. The v6.1 package is named <strong>Cavern pressure and irruptions</strong>, and the term carries through the plugin's console, its guide and the reports. Since 1 October it has a second reason: DF's own invasions are disabled in its code (R4, R23), and the irruption is the tool's stand-in, built to live alongside them if they return. v7.1's IRRUPT v2 never touches DF's invasion machinery.</p>
  </div>

  <div class="decided">
    <span class="tag">Standing rule · since 18 September</span>
    <p><strong>Never write FREQUENCY 0. Write 1.</strong> Zeroing <code>CREEPY_CRAWLER</code>, the only underground <code>VERMIN_ROTTER</code>, freezes DF silently and for good; 1 against a typical 50 or 100 suppresses as well and is safe. The 18 September finding that "the cavern layer was never actually managed" is resolved: the cavern ceiling holds managed species at frequency 1 (v5.8.1), and irruptions shipped armed, not aimed, on what E29 and E23 allow (v6.1; T9 and T9b passed 2 of 2). v7.1 carries the rule further: the cavern gate holds at frequency 1, never 0 (R44), and the 19 animal people whose raws round to FREQUENCY 0 are floored at 1 (R61).</p>
  </div>

  <h2>The sequence at a glance</h2>
  <p class="lede">Stages 1 and 2 run in order; stage 3 is closed by their claims and tests; stage 4 follows all three. Desk reads can run any time. Every rig step needs the user's go and a free rig.</p>
  <div class="scroll">
    <table>
      <caption>Register items by stage · priorities over all {len(items)}: {pc['high']} high, {pc['medium']} medium, {pc['low']} low · High counts exclude done items</caption>
      <thead><tr><th scope="col">Stage</th><th scope="col">What</th><th scope="col">Items</th><th scope="col">High</th><th scope="col">Built, untested</th></tr></thead>
      <tbody>
{glance()}
      </tbody>
    </table>
  </div>

  <h2 id="old">The old backlog, checked</h2>
  <p class="lede">The thirteen candidates of 22 September, each with what happened to it through v7.1 and the register item that carries what is left. Nothing was dropped.</p>
  <div class="scroll">
    <table>
      <thead><tr><th scope="col">Candidate (22 Sep)</th><th scope="col">1 Oct, v7.1</th><th scope="col">Where</th><th scope="col">Open item now</th></tr></thead>
      <tbody>
{old_rows()}
      </tbody>
    </table>
  </div>

{stage_html()}

  <h2 id="added">Added by this page <span class="count">{len(ADDED)}</span></h2>
  <p class="lede">Gaps not in the open-items register, as of the evening of 1 October.</p>
  <div class="items">
{added_cards()}
  </div>

  <footer>
    <div>Items, ids, priorities, statuses, evidence and sources are from DwarfCron <code>data/eco-report/open-items.json</code> ({E(OI['generated'][:10])}, revised after the user's review Parts 1 and 2; categories: {', '.join(f"{E(x['title'])} {cc[x['id']]}" for x in OI['categories'])}). Stage, &ldquo;Depends on&rdquo;, &ldquo;Closed by&rdquo; and the &ldquo;Checked 1 October, evening&rdquo; notes are this page's, checked against seasonal-wildlife <code>v7.1</code> (STATE addenda 99&ndash;100, PLAN rev 4, <code>docs/v7.1/*.md</code>), <code>sw-wt/BUILD-PLAN.md</code> and DwarfCron <code>experiments/VALIDATOR-v71.md</code> and <code>HARNESS-v71.md</code>.</div>
    <div>Revisions: first drawn 18 September (thirteen candidates beyond v6.2); 22 September, part-built notes after v6.2.0; 1 October morning, rebuilt around the open-items register after v7.0 and the ECO study, the old candidates kept in the table above; <strong>1 October evening, regenerated from the register as revised by the user's rulings (95 items): the decisions stage is gone, every built-untested item moved into the testing stage with the test that closes it, release is v7.1's, and the protocol is n = 5 on region8.</strong></div>
    <div>No rig was run to write this page. Validation figures quoted are from DFHack 53.16-r1.1; nothing has run on 53.16-r2.</div>
  </footer>
</div>
'''
open(f'{ROOT}/.claude/scratch/wildlife-backlog.html', 'w').write(page)
print('ok', len(page), 'items', len(placed), 'added', len(ADDED), 'built', built_n, 'test', test_n)
