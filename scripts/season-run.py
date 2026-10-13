#!/usr/bin/env python3
"""season-run: one driver for every seasonal-wildlife season run on the CrossOver rig (the run kit, ECO report X).

    season-run.py backup [FORT ...] [--tag preverify] [--dry-run]
    season-run.py run SPEC.json [--reps N] [--arm A,B] [overrides] [--dry-run [--dry-hang-at N]]
    season-run.py run --fort F --name RUN [--arm NAME] [--until season:N|ticks:N|before_change:N] [--chunk 20000]
                      [--save-chunks] [--sustain] [--recorder] [--pairs-every 3000] [--ledger-live]
                      [--pre CMD]... [--receipt 'CMD ~ REGEX']... [--reps N] [--restart-between-arms] [--dry-run]
    season-run.py analyse RUNDIR
    season-run.py park RUNDIR [--dry-run]       move the run's chunk saves out of DF's save dir (DF must be stopped)

backup   copies each fort with `cx-lifecycle.sh save-backup FORT preverify` and proves the copy byte-identical (size and
         sha256 of every file). It refuses a fort DF has loaded (memory save-dir-while-running): DF must be stopped, at
         the title, or holding another fort. Default forts: V73_LAKE2 V73_OCEAN2 V73_BROOK T1END_WATERFALL.
run      one cell = one (arm, replicate): restore the fort from its backup (never run on the original) and hash it,
         load it by folder, read the ledger's baseline, run the arm's pre commands (the manipulation), its receipts
         (any failure ABORTS the cell: memory manifest-subject-receipt), start sw-t1-recorder, step in chunks with a
         timeout per step, every --pairs-every ticks dump `ecology pairs tsv` + `cast status` and read the ledger live,
         every chunk run `cx-load sustain`, dump `perf` and save to a NEW folder (never quicksave: memory
         rig-fast-step-hang). On a hang: record it, `restart` DF, load the last chunk save, re-run the receipts, start a
         new recorder segment and go on. At the end: stop the recorder, copy its TSVs, `title` (quit without saving),
         and hash the fort's folder against its backup again. Arms run counterbalanced (odd reps as listed, even
         reversed), a fresh load per cell, DF restarted between arms with --restart-between-arms.
         A spec may replace the default cell (pre, receipts, run) with its own `phases` (runs X1 and X2).
analyse  writes cell.json per cell (v73_check's verdicts plus the X3 measures: off-cast arrivals and their lead time
         after the season change, in-cast trims, turnover send-offs and whether they left, stand-ins, reserve
         conservation from the state dumps, drownings after a water draw, tool time per pass) and RUNDIR/summary.json
         + summary.md. It reuses data/t1-season/v73_check.py and f0_compare.py; it never touches the rig.
--dry-run replaces every cx-lifecycle / RPC call with a fake that logs the call and answers from a finished run folder
         (data/t1-season/V73_LAKE3 and friends), so the whole pipeline runs offline. Output goes to
         data/season-run/dryrun/<RUN>/. --dry-hang-at N makes the Nth step hang, to exercise the recovery path.

Output: data/season-run/<RUN>/run.json (spec, provenance, times, saves written) and <arm>/rep<k>/ with run.log,
receipts.txt, pre.txt, ledger.txt (+ ledger-before.txt), pairs/<tick>.tsv, casts/<tick>.txt, perf/<tick>.txt,
states/<tag>.json, the recorder's events/positions/reports/samples/ledger(.tsv) (merged over segments; raw segments in
recorder/), pairs.tsv, casts-start.txt, casts-end.txt and cell.json. Spec format and the traps: experiments/season-runs/README.md.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import functools
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIFECYCLE = ROOT / 'scripts' / 'cx-lifecycle.sh'
RPC = ROOT / 'scripts' / 'cx-rpc.py'
PY = ROOT / '.venv' / 'bin' / 'python'
if not PY.exists():
    PY = Path(sys.executable)
T1 = ROOT / 'data' / 't1-season'
OUT_ROOT = ROOT / 'data' / 'season-run'
STATE_LUA = T1 / 'sw-state-check.lua'
AUDIT_LUA = T1 / 'sw-group-audit.lua'

HOME = Path.home()
CX_ROOT = HOME / 'Library/Application Support/CrossOver'
DF_DIR = Path(os.environ.get('DF_DIR', CX_ROOT / 'Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress'))
SAVE_ROOT = Path(os.environ.get('DF_SAVE_DIR', CX_ROOT / 'Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save'))
BACKUP_ROOT = Path(os.environ.get('CX_SAVE_BACKUPS', CX_ROOT / 'df-snapshots/saves'))
PARK_ROOT = CX_ROOT / 'df-snapshots/parked'
SW_REPO = Path(os.environ.get('SW_REPO', HOME / 'Claude/Projects/sw-wt/plugin'))
PORT = os.environ.get('CX_PORT', '5555')

TPY, TPS, TPD = 403_200, 100_800, 1_200
SEASONS = ['Spring', 'Summer', 'Autumn', 'Winter']
MANAGED = ('land', 'water', 'cavern')
PLACED_PLANTS = {'SPONGE', 'GIANT_SPONGE'}
DEFAULT_FORTS = ['V73_LAKE2', 'V73_OCEAN2', 'V73_BROOK', 'T1END_WATERFALL']
# dry run: the finished run folder each fort's fake answers come from
CANNED = {'V73_LAKE2': 'V73_LAKE3', 'V73_OCEAN2': 'V73_OCEAN3', 'V73_BROOK': 'V73_BROOK', 'T1END_WATERFALL': 'V73_WATERFALL'}
# readout trap 24: a Lua or script error is not a value
ERR_RE = re.compile(r'traceback|Could not find script|\.lua:\d+:|attempt to (?:index|call|compare|perform)|^Error|qerror', re.I | re.M)

DEFAULTS = dict(reps=1, until='season:1', chunk=20000, save_chunks=True, sustain=True, recorder=True, recorder_every=100,
                pairs_every=3000, ledger_live=True, perf=True, state_every_chunk=False, restart_between_arms=False,
                restart_each_cell=False, check_files=False,
                fps=1000, gfps=10, max_hangs=3, pre_on_resume=False, live_count=False, backup_tag='preverify',
                pre=[], receipts=[], phases=None, finally_=[])


def now() -> str:
    return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def safe(name: str) -> str:
    """DF save and recorder names: letters and digits only, so SR_<run>_<arm>_r01_c001 names are prefix-free"""
    return re.sub(r'[^A-Za-z0-9]', '', str(name)) or 'X'


class Hang(Exception):
    """DF stopped answering (a step or RPC call ran past its deadline): memory rig-fast-step-hang"""


class CellFail(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status, self.reason = status, reason


class RunFail(Exception):
    pass


# ------------------------------------------------------------------ files --

def tree_manifest(root: Path) -> dict:
    """{relative path: (size, sha256)} of every file under root"""
    out = {}
    for p in sorted(root.rglob('*')):
        if p.is_file():
            h = hashlib.sha256()
            with open(p, 'rb') as f:
                for b in iter(lambda: f.read(1 << 20), b''):
                    h.update(b)
            out[str(p.relative_to(root))] = (p.stat().st_size, h.hexdigest())
    return out


def compare_trees(a: Path, b: Path) -> list[str]:
    """every difference between two trees (missing files, size or sha mismatches); [] = byte-identical"""
    ma, mb = tree_manifest(a), tree_manifest(b)
    diffs = [f'only in {a.name}: {k}' for k in sorted(set(ma) - set(mb))]
    diffs += [f'only in {b.name}: {k}' for k in sorted(set(mb) - set(ma))]
    diffs += [f'differs: {k} {ma[k][0]}B vs {mb[k][0]}B' for k in sorted(set(ma) & set(mb)) if ma[k] != mb[k]]
    return diffs


def git(repo: Path, *args) -> str:
    try:
        return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ''


def tick_of(name: str) -> int:
    m = re.match(r'^(\d+)', name)
    return int(m.group(1)) if m else -1


# ------------------------------------------------------------------- rig --

class Rig:
    """Sequential access to the rig: one subprocess per call, never two at once (the one-RPC-at-a-time rule)."""
    dry = False

    def __init__(self, log):
        self.log = log

    def sh(self, *verb, timeout=600, env=None) -> tuple[int, str, str]:
        e = dict(os.environ, CX_PORT=PORT, **(env or {}))
        try:
            p = subprocess.run([str(LIFECYCLE), *map(str, verb)], capture_output=True, text=True, timeout=timeout, env=e)
        except subprocess.TimeoutExpired:
            raise Hang(f'cx-lifecycle {verb[0]} ran past {timeout}s')
        return p.returncode, p.stdout.replace('\r', ''), p.stderr.replace('\r', '')

    def must(self, *verb, timeout=600) -> str:
        rc, out, err = self.sh(*verb, timeout=timeout)
        for line in err.strip().splitlines():
            self.log(f'  [rig] {line.replace("[cx-lifecycle] ", "")}')
        if rc != 0:
            raise RuntimeError(f'cx-lifecycle {" ".join(map(str, verb))} failed rc={rc}: {err.strip()[-300:]}')
        return out

    def lua(self, code: str, timeout=60) -> str:
        try:
            p = subprocess.run([str(PY), str(RPC), '--port', PORT, '--timeout', str(timeout), '--lua', code],
                               capture_output=True, text=True, timeout=timeout + 30)
        except subprocess.TimeoutExpired:
            raise Hang(f'lua ran past {timeout + 30}s')
        if p.returncode != 0:
            if 'timed out' in p.stderr.lower() or 'timeout' in p.stderr.lower():
                raise Hang(f'lua timed out: {p.stderr.strip()[-200:]}')
            raise RuntimeError(f'lua failed: {p.stderr.strip()[-300:]}')
        return p.stdout.replace('\r', '')

    def cmd(self, *words, timeout=60) -> tuple[int, str, str]:
        """a DFHack command, its words passed apart (readout trap 8: one spaced string is never answered)"""
        return self.sh('cmd', *words, timeout=timeout + 30, env={'CX_RPC_TIMEOUT': str(timeout)})

    def running(self) -> bool:
        rc, out, _ = self.sh('status', timeout=60)   # pgrep + lsof only; does not talk to DF
        return out.startswith('running')

    def clock(self) -> tuple[int, int, bool]:
        """(absolute tick, season, map loaded); an empty read twice is a hang"""
        for _ in range(2):
            out = self.lua('-- sr:clock\nprint(df.global.cur_year*403200+df.global.cur_year_tick, df.global.cur_season, '
                           'dfhack.isMapLoaded() and 1 or 0)', timeout=30).strip().split()
            if len(out) == 3 and all(x.lstrip('-').isdigit() for x in out):
                return int(out[0]), int(out[1]), out[2] == '1'
            time.sleep(2)
        raise Hang('RPC gave no tick')

    def where(self) -> tuple[bool, str]:
        """(map loaded, the save folder DF has loaded)"""
        out = self.lua('-- sr:where\nprint(dfhack.isMapLoaded() and "true" or "false", '
                       'dfhack.isMapLoaded() and df.global.world.cur_savegame.save_dir or "")', timeout=30).strip()
        parts = out.split(None, 1)
        return (parts[0] == 'true') if parts else False, parts[1].strip() if len(parts) > 1 else ''

    def fetch_recorder(self, name: str, dest: Path):
        src = DF_DIR / 'sw-t1' / name
        dest.mkdir(parents=True, exist_ok=True)
        for f in src.glob('*.tsv'):
            shutil.copy2(f, dest / f.name)


class FakeRig(Rig):
    """--dry-run: every call is logged and answered from a finished run folder; nothing reaches DF. The fake keeps a
    clock, the loaded fort, named saves, the recorder's segments and the tool's on/off and cast switches, so receipts,
    checks, resume-after-hang and the analysis all see consistent data."""
    dry = True

    def __init__(self, log, hang_at=0):
        super().__init__(log)
        self.up, self.map, self.t, self.steps, self.hang_at, self.hung = True, None, 0, 0, hang_at, False
        self.saves, self.rec, self.rec_on = {}, {}, None
        self.tool_on, self.cast_on, self.canned = True, True, T1 / 'V73_LAKE3'
        self._led = {}

    def _canned_for(self, fort):
        d = T1 / CANNED.get(fort, 'V73_LAKE3')
        return d if (d / 'events.tsv').exists() else T1 / 'V73_LAKE3'

    @staticmethod
    def _start(d: Path) -> int:
        with open(d / 'events.tsv', encoding='cp437') as f:
            next(f)
            return int(next(f).split('\t')[0])

    def _ledger(self):
        if self.canned not in self._led:
            rows = []
            p = self.canned / 'ledger.tsv'
            if p.exists():
                for line in open(p, encoding='cp437').read().splitlines()[1:]:
                    x = line.split('\t')
                    if len(x) >= 4 and x[0].isdigit() and x[1] != 'GAP':
                        rows.append((int(x[0]), x[1], x[2], x[3]))
            self._led[self.canned] = rows
        return self._led[self.canned]

    def sh(self, *verb, timeout=600, env=None):
        v, a = verb[0], [str(x) for x in verb[1:]]
        self.log('  [dry] cx-lifecycle.sh ' + ' '.join(shlex.quote(str(x)) for x in verb))
        if self.hung and v not in ('restart', 'stop', 'start', 'status'):
            raise Hang(f'dry run: DF is hung ({v} never returns)')
        ok = lambda msg='': (0, '', f'[cx-lifecycle] {msg}\n' if msg else '')  # noqa: E731
        if v == 'status':
            return 0, ('running   pid 0 (dry run)\n' if self.up else 'stopped\n'), ''
        if v in ('start', 'restart'):
            self.up, self.map, self.hung, self.rec_on = True, None, False, None
            return ok('DF up (dry run)')
        if v == 'stop':
            self.up, self.map, self.hung = False, None, False
            return ok('stopped (dry run)')
        if v == 'save-backup':
            return ok(f'backed up {a[0]} -> {BACKUP_ROOT}/{a[0]}.{a[1] if len(a) > 1 else "TAG"} (dry run: nothing copied)')
        if v == 'save-restore':
            return (1, '', '[cx-lifecycle] ERROR: leave the fort first\n') if self.map else ok(f'restored {a[0]} (dry run)')
        if v == 'load':
            if a[0] in self.saves:
                self.canned, self.t, self.tool_on, self.cast_on = self.saves[a[0]]
            else:
                self.canned = self._canned_for(a[0])
                self.t, self.tool_on, self.cast_on = self._start(self.canned), True, True
            self.map = a[0]
            return ok(f'loaded after 21s (dry run; canned {self.canned.name}, tick {self.t})')
        if v == 'title':
            self.map, self.rec_on = None, None
            return ok('back at the title screen')
        if v == 'step':
            self.steps += 1
            if self.steps == self.hang_at:
                self.hung = True
                raise Hang(f'dry run: simulated hang on step {self.steps}')
            n = int(a[0])
            t0, self.t = self.t, self.t + n + 30
            return ok(f'stepped {n + 30} ticks ({t0 % TPY} -> {self.t % TPY}) in 33s')
        if v == 'save':
            self.saves[a[0]] = (self.canned, self.t, self.tool_on, self.cast_on)
            return ok(f'saved -> {a[0]} (27M, 12s)')
        if v == 'cmd':
            return 0, self._cmd(a), ''
        if v == 'port':
            return 0, PORT + '\n', ''
        return ok(f'{v}: ok (dry run)')

    def _cmd(self, w):
        j = ' '.join(w)
        if w[:2] == ['cx-load', 'sustain']:
            return 'sustain: 7 citizen(s) watered and fed (dry run)\n'
        if w[:1] == ['sw-t1-recorder']:
            if w[1] == 'start':
                self.rec[Path(w[2]).name], self.rec_on = [self.t, None], Path(w[2]).name
                return f'sw-t1-recorder: recording into {w[2]} every {w[3] if len(w) > 3 else 100} ticks (11 units present at start)\n'
            if w[1] == 'stop':
                if self.rec_on:
                    self.rec[self.rec_on][1] = self.t
                self.rec_on = None
                return 'sw-t1-recorder: stopped; 20 samples, 40 events, 10 reports\n'
            return f'sw-t1-recorder: {"recording" if self.rec_on else "stopped"}; dir sw-t1/{self.rec_on}\n'
        if w[0] != 'seasonal-wildlife':
            return f'(dry run: no canned answer for `{j}`)\n'
        sub = w[1:]
        if sub[:1] == ['ledger']:
            n = int(sub[1]) if len(sub) > 1 and sub[1].isdigit() else 20
            rows = [r for r in self._ledger() if r[0] <= self.t]
            lines = [f'{stamp(r[0]):<14s} {r[1]:<9s} {r[2] or "-":<7s} {r[3]}' for r in rows[-n:]]
            return '\n'.join(lines + [f'ledger: {len(lines)} of {len(rows)} recorded shown']) + '\n'
        if sub[:3] == ['ecology', 'pairs', 'tsv']:
            return (self.canned / 'pairs.tsv').read_text(encoding='cp437')
        if sub[:2] == ['cast', 'status']:
            txt = (self.canned / 'casts-start.txt').read_text(encoding='utf-8', errors='replace')
            return re.sub(r'season casts \w+', 'season casts ' + ('on' if self.cast_on else 'off'), txt)
        if sub[:2] in (['cast', 'on'], ['cast', 'off']):
            self.cast_on = sub[1] == 'on'
            return f'cast: {sub[1]}\n'
        if sub[:2] == ['cast', 'restfreq']:
            return f'cast: resting cavern species held at frequency {sub[2]} (vermin at 1)\n'
        if sub[:1] in (['on'], ['off']):     # the lines turn_on / turn_off print (seasonal-wildlife v7.2+)
            self.tool_on = sub[0] == 'on'
            if self.tool_on:
                return 'water renderer: on\nautostart: on\nthis fort: on (dry run)\n'
            return ('water renderer: off\nautostart: off\nthis fort: off (every job stopped and every write put back; '
                    'the switches keep their settings for `on`)\n')
        if sub[:1] == ['status']:
            return ('Layers: cavern, deep, land, water\n'
                    f'rotation: {"enabled" if self.tool_on else "disabled"}\nautostart: {"on" if self.tool_on else "off"}\n')
        if sub[:1] == ['perf']:
            return ('job / lap                            runs   last  worst  over   ms/run   KB last  KB worst defer\n'
                    '~:groups                              120      3     40     0      3.2        12        40     0\n'
                    '~:season                               14      9     61     0      8.4         -         -     0\n'
                    f'worst single tick: 61 ms (tick {self.t}: season); ticks shared by two or more jobs: 2\n')
        if sub[:2] == ['water', 'bodies']:
            p = self.canned / 'water-bodies-end.txt'
            return p.read_text() if p.exists() else 'water bodies (dry run): ocean 0, lake 0, river 1, pool 0, cavern_pool 0\n'
        if sub[:1] == ['sendoff']:
            return f'sent off 1 gated {sub[1] if len(sub) > 1 else "land"} group(s); the gate is open\n'
        return f'(dry run: no canned answer for `{j}`)\n'

    def lua(self, code, timeout=60):
        tag = re.match(r'--\s*sr:(\w+)', code.lstrip())
        tag = tag.group(1) if tag else ''
        self.log(f'  [dry] lua ({tag or "code"}, {len(code)} chars)')
        if self.hung:
            raise Hang('dry run: DF is hung (lua never returns)')
        if tag == 'clock':
            return f'{self.t} {(self.t % TPY) // TPS} 1\n' if self.map else '0 0 0\n'
        if tag == 'where':
            return f'{"true" if self.map else "false"} {self.map or ""}\n'
        if tag == 'prov':
            return '0.53.16\t53.16-r2 (dry run)\n'
        if tag == 'wildcount':
            last = 0
            for line in open(self.canned / 'samples.tsv', encoding='cp437').read().splitlines()[1:]:
                x = line.split('\t')
                if x[0].isdigit() and int(x[0]) <= self.t:
                    last = int(x[1])
            return f'{last}\n'
        if tag == 'state':
            toks = sorted(set(re.findall(r'\b[A-Z][A-Z_]{2,}\b', (self.canned / 'casts-start.txt').read_text())))[:12]
            pops = [[i, t, t, 100 + 7 * i, False, 'Animal'] for i, t in enumerate(toks)]
            return json.dumps({'ok': True, 'tick': self.t, 'season': (self.t % TPY) // TPS, 'site': self.map,
                               'scope': 'embark+1', 'tool': {'config': True, 'enabled': self.tool_on, 'cast_enabled': self.cast_on},
                               'snapshot': {p[2]: p[3] for p in pops}, 'reserve': {}, 'pops': pops,
                               'raws': {t: [50, 3, 1, 10, 5, '----'] for t in toks},
                               'rel': {'units': 40, 'slots': 60, 'wild_any': 0, 'wild_wild': 0, 'wild_other': 0,
                                       'other_other': 0}}, separators=(',', ':')) + '\n'
        if tag == 'audit':
            return json.dumps({'ok': True, 'tick': self.t, 'season': (self.t % TPY) // TPS, 'cast_on': self.cast_on,
                               'groups': [], 'offcast': 0, 'offcast_units': 0}) + '\n'
        return '(dry run lua)\n'

    def fetch_recorder(self, name, dest):
        """the canned run's recorder files, cut to the ticks this segment covered"""
        t0, t1 = self.rec.get(name, [self.t, self.t])
        t1 = self.t if t1 is None else t1
        dest.mkdir(parents=True, exist_ok=True)
        for f in ('events.tsv', 'positions.tsv', 'reports.tsv', 'samples.tsv', 'ledger.tsv', 'pops.tsv'):
            src = self.canned / f
            if not src.exists():
                if f == 'ledger.tsv':   # the recorder always writes its ledger table (V73_WATERFALL predates it)
                    (dest / f).write_text('tick\tkind\tlayer\ttext\n')
                continue
            lines = src.read_text(encoding='cp437').splitlines()
            keep = [lines[0]] + [l for l in lines[1:] if l.split('\t')[0].isdigit() and t0 <= int(l.split('\t')[0]) <= t1]
            (dest / f).write_text('\n'.join(keep) + '\n', encoding='cp437')


def stamp(t: int) -> str:
    """the tool's ledger stamp, 'y250 Summer 9'"""
    yt = t % TPY
    return f'y{t // TPY} {SEASONS[yt // TPS]} {(yt % TPS) // TPD + 1}'


def unstamp(s: str) -> int | None:
    m = re.match(r'^y(\d+)\s+(\w+)\s+(\d+)', s)
    if not m or m.group(2) not in SEASONS:
        return None
    return int(m.group(1)) * TPY + SEASONS.index(m.group(2)) * TPS + (int(m.group(3)) - 1) * TPD


# ------------------------------------------------------------------ spec --

def parse_item(x) -> dict:
    """a pre / receipt / finally item: 'words', 'lua:CODE', 'words ~ REGEX', or a dict (cmd|lua|lua_file + keys)"""
    if isinstance(x, dict):
        d = dict(x)
        if isinstance(d.get('cmd'), str):
            d['cmd'] = shlex.split(d['cmd'])
        return d
    s = str(x)
    if s.startswith('lua:'):
        return {'lua': s[4:]}
    words, sep, rx = s.partition(' ~ ')
    d = {'cmd': shlex.split(words)}
    if sep:
        d['expect'] = rx.strip()
    return d


def item_label(d: dict) -> str:
    if 'cmd' in d:
        return ' '.join(d['cmd'])
    if 'lua_file' in d:
        return f'lua_file {d["lua_file"]} {" ".join(map(str, d.get("args", [])))}'.strip()
    return 'lua: ' + d.get('lua', '')[:80].replace('\n', ' ')


def resolve_until(u: str, t: int) -> int:
    """season:N[+K] = K ticks (default 2,000) past the Nth season change from t; ticks:N = t+N;
    before_change:N = N ticks before the next change; tick:N = absolute"""
    kind, _, val = str(u).partition(':')
    if kind == 'season':
        n, _, k = val.partition('+')
        return (t // TPS + int(n)) * TPS + int(k or 2000)
    if kind == 'ticks':
        return t + int(val)
    if kind == 'before_change':
        x = (t // TPS + 1) * TPS - int(val)
        return x if x > t else x + TPS
    if kind == 'tick':
        return int(val)
    raise ValueError(f'bad --until {u!r} (season:N, ticks:N, before_change:N, tick:N)')


def arm_order(arms: list, reps: int):
    """counterbalanced: rep k runs the arms as written for odd k and reversed for even k"""
    for k in range(1, reps + 1):
        for a in (arms if k % 2 else list(reversed(arms))):
            yield k, a


def load_spec(args) -> dict:
    if args.spec:
        spec = json.loads(Path(args.spec).read_text())
    else:
        if not (args.fort and args.name):
            sys.exit('run: give SPEC.json, or --fort F --name RUN')
        spec = {'id': args.name, 'arms': [{'name': args.arm or 'A', 'fort': args.fort}]}
    if args.name:
        spec['id'] = args.name
    for k in ('until', 'chunk', 'save_chunks', 'sustain', 'recorder', 'pairs_every', 'ledger_live', 'reps',
              'restart_between_arms'):
        v = getattr(args, k)
        if v is not None:
            spec[k] = v
    if args.pre:
        spec['pre'] = list(spec.get('pre', [])) + args.pre
    if args.receipt:
        spec['receipts'] = list(spec.get('receipts', [])) + args.receipt
    if args.spec and args.arm:
        keep = set(args.arm.split(','))
        spec['arms'] = [a for a in spec['arms'] if a['name'] in keep]
    if not spec.get('arms'):
        sys.exit('run: the spec has no arms')
    return spec


def arm_config(spec: dict, arm: dict) -> dict:
    c = dict(DEFAULTS)
    c.update({k: v for k, v in spec.items() if k not in ('arms', 'pre', 'receipts', 'finally')})
    c.update({k: v for k, v in arm.items() if k not in ('pre', 'receipts', 'finally')})
    c['pre'] = [parse_item(x) for x in list(spec.get('pre', [])) + list(arm.get('pre', []))]
    c['receipts'] = [parse_item(x) for x in list(spec.get('receipts', [])) + list(arm.get('receipts', []))]
    c['finally_'] = [parse_item(x) for x in list(spec.get('finally', [])) + list(arm.get('finally', []))]
    c['phases'] = arm.get('phases', spec.get('phases')) or [{'do': 'pre'}, {'do': 'receipts'}, {'do': 'run'}]
    if not c.get('fort'):
        raise SystemExit(f'arm {arm.get("name")}: no fort')
    return c


# ----------------------------------------------------------- provenance --

def find_commit(blob: str) -> str:
    """the newest sw-wt/plugin commit whose scripts/seasonal-wildlife.lua is this blob"""
    if not blob or not SW_REPO.exists():
        return ''
    work = git(SW_REPO, 'hash-object', 'scripts/seasonal-wildlife.lua')
    if work == blob:
        dirty = git(SW_REPO, 'status', '--porcelain', '--', 'scripts/seasonal-wildlife.lua')
        if dirty:
            return f'working tree (uncommitted; HEAD {git(SW_REPO, "rev-parse", "--short", "HEAD")})'
    out = git(SW_REPO, 'log', '-n', '400', '--format=C %H %s', '--raw', '--no-abbrev', '--', 'scripts/seasonal-wildlife.lua')
    cur = None
    for line in out.splitlines():
        if line.startswith('C '):
            cur = line[2:12] + line[42:]
        elif line.startswith(':') and cur:
            parts = line.split()
            if len(parts) >= 4 and parts[3] == blob:
                return cur[:120]
    return 'no commit in the last 400 matches'


def provenance(rig: Rig) -> dict:
    p = {'dwarfcron_commit': git(ROOT, 'rev-parse', '--short', 'HEAD'), 'sw_repo': str(SW_REPO), 'dry_run': rig.dry}
    eng = {}
    for label, path in (('shadow (dfhack-config/scripts)', DF_DIR / 'dfhack-config/scripts/seasonal-wildlife.lua'),
                        ('package (DFHack/hack/scripts)', DF_DIR.parent / 'DFHack/hack/scripts/seasonal-wildlife.lua')):
        if path.exists():
            text = path.read_bytes()
            blob = git(ROOT, 'hash-object', str(path))
            rel = re.search(rb"CACHE\.release ~= '([^']+)'", text)
            eng[label] = {'bytes': len(text), 'blob': blob, 'release': rel.group(1).decode() if rel else '?',
                          'mtime': dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds'),
                          'commit': find_commit(blob)}
    p['engine'] = eng
    # DFHack finds dfhack-config/scripts first: a shadow copy is the engine in use (memory v72-package)
    p['engine_in_use'] = next(iter(eng), 'none found')
    rec = DF_DIR / 'dfhack-config/scripts/sw-t1-recorder.lua'
    p['recorder_deployed'] = rec.exists()
    p['recorder_matches_repo'] = rec.exists() and rec.read_bytes() == (T1 / 'sw-t1-recorder.lua').read_bytes()
    auto = DF_DIR / 'dfhack-config/seasonal-wildlife.json'
    p['autostart_file'] = auto.read_text().strip() if auto.exists() else None
    try:
        out = rig.lua('-- sr:prov\nprint(dfhack.getDFVersion(), dfhack.getDFHackVersion())', timeout=20).strip()
        p['df_dfhack'] = out
    except (Hang, RuntimeError) as e:
        p['df_dfhack'] = f'unread: {e}'
    return p


# ------------------------------------------------------------------ cell --

class Cell:
    """one (arm, replicate): restore, load, phases, end. All rig calls go through self.rig."""

    def __init__(self, run, arm_name: str, rep: int, cfg: dict, d: Path):
        self.run, self.rig, self.arm, self.rep, self.c, self.d = run, run.rig, arm_name, rep, cfg, d
        self.fort = cfg['fort']
        self.base = f'SR_{safe(run.id)}_{safe(arm_name)}_r{rep:02d}'
        self.info = {'run': run.id, 'arm': arm_name, 'rep': rep, 'fort': self.fort, 'status': 'RUNNING', 'reason': '',
                     'started': now(), 'hangs': [], 'saves': [], 'segments': [], 'receipts': [], 'checks': [],
                     'dump_errors': [], 'step_s': 0.0, 'ticks': 0}
        self.chunk_no, self.last_save, self.seg = 0, None, 0
        self.segments: list[tuple[str, int]] = []
        self.led_total, self.led_seen = None, set()
        self.rec_on, self.casts_first = False, None
        self.saved_tags: dict[str, str] = {}

    # -- logging and files
    def L(self, msg):
        line = f'{dt.datetime.now().strftime("%H:%M:%S")} {msg}'
        print(f'[{self.arm} r{self.rep}] {line}', flush=True)
        with open(self.d / 'run.log', 'a') as f:
            f.write(line + '\n')

    def write(self, rel: str, text: str):
        p = self.d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def check(self, name: str, ok: bool, detail=''):
        self.info['checks'].append({'name': name, 'pass': bool(ok), 'detail': detail})
        self.L(f'check {name}: {"PASS" if ok else "FAIL"} {detail}')

    # -- one item (a pre command, a receipt, a cmd/lua phase)
    def do_item(self, d: dict, kind: str) -> str:
        label = item_label(d)
        t = int(d.get('timeout', 60))
        if 'cmd' in d:
            rc, out, err = self.rig.cmd(*d['cmd'], timeout=t)
        else:
            code = d.get('lua', '')
            if 'lua_file' in d:
                code = lua_with_args((ROOT / d['lua_file']).read_text(), d.get('args', []), Path(d['lua_file']).stem)
            rc, out, err = 0, self.rig.lua(code, timeout=t), ''
        hard, soft = [], []   # hard: the item failed (aborts a pre, receipt or phase); soft: a recorded check failed
        if rc != 0:
            hard.append(f'rc {rc}')
        if not out.strip():
            (hard if kind == 'receipt' else soft).append('empty output')
        e = ERR_RE.search(out) or (ERR_RE.search(err) if kind != 'dump' else None)
        if e:
            hard.append('error text: ' + e.group(0))
        for key, want in (('expect', True), ('expect_not', False), ('check', True), ('check_not', False)):
            if key in d and bool(re.search(d[key], out, re.M)) != want:
                (hard if key.startswith('expect') else soft).append(f'{key} /{d[key]}/ ' + ('not found' if want else 'found'))
        why = hard + soft
        with open(self.d / ('receipts.txt' if kind == 'receipt' else f'{kind}.txt'), 'a') as f:
            f.write(f'### {now()} {label}\n{out.rstrip()}\n{err.strip()}\n=> {"PASS" if not why else "FAIL: " + "; ".join(why)}\n\n')
        if d.get('save_as'):
            self.write(d['save_as'], out)
        if kind == 'receipt':
            self.info['receipts'].append({'what': label, 'pass': not why, 'why': '; '.join(why)})
        if any(k in d for k in ('check', 'check_not')):
            self.check(d.get('name', label), not why, '; '.join(why) or 'matched')
        if hard and kind in ('receipt', 'pre', 'phase'):
            raise CellFail('ABORTED', f'{kind} `{label}` failed: {"; ".join(hard)}')
        return out

    def json_item(self, path: Path, args: list, tag: str, folder: str) -> dict:
        out = self.rig.lua(lua_with_args(path.read_text(), args, 'state' if path == STATE_LUA else 'audit'), timeout=120)
        line = next((l for l in out.splitlines() if l.startswith('{')), '')
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            raise CellFail('ABORTED', f'{path.name} printed no JSON line: {out.strip()[:200]}')
        if not j.get('ok'):
            raise CellFail('ABORTED', f'{path.name} failed: {j.get("error")}')
        self.write(f'{folder}/{tag}.json', json.dumps(j, separators=(',', ':')) + '\n')
        return j

    # -- the cell
    def go(self):
        t_wall = time.time()
        try:
            self.restore_and_load()
            self.poll_ledger(first=True)
            for ph in self.c['phases']:
                self.phase(ph)
            self.info['status'] = 'OK'
        except CellFail as e:
            self.info['status'], self.info['reason'] = e.status, e.reason
            self.L(f'CELL {e.status}: {e.reason}')
        except Hang as e:
            self.info['status'], self.info['reason'] = 'HUNG', str(e)
            self.L(f'CELL HUNG outside the stepping loop: {e}')
            self.restart_rig()
        except Exception as e:   # noqa: BLE001 -- a broken cell is recorded and the run goes on
            self.info['status'], self.info['reason'] = 'FAILED', f'{type(e).__name__}: {e}'
            self.L(f'CELL FAILED: {e}')
        finally:
            try:
                self.end()
            finally:
                self.info['wall_s'] = round(time.time() - t_wall, 1)
                self.info['ended'] = now()
                if self.info['step_s'] > 1:
                    self.info['ticks_per_s'] = round(self.info['ticks'] / self.info['step_s'], 1)
                self.write('cell.json', json.dumps({'run': self.info}, indent=1) + '\n')
        return self.info

    def restore_and_load(self):
        ml, sd = self.rig.where() if self.rig.running() else (False, '')
        if ml:
            self.L(f'a map is loaded ({sd}); quitting it without saving')
            self.rig.must('title', timeout=200)
        tag = self.c['backup_tag']
        self.rig.must('save-restore', f'{self.fort}.{tag}', timeout=300)
        if self.c.get('restart_each_cell'):
            # DF reads its Continue list once at start; every chunk save joins the world's list above the restored fort,
            # and `load` scrolls at most ~30 rows. A restart after the restore puts the fort (touched: newest) on top,
            # and resets process age (memory fps-load-facts).
            self.L('restarting DF after the restore (restart_each_cell)')
            self.restart_rig(park=True)
        if self.rig.dry:
            self.info['restore_verified'] = 'dry run (not hashed)'
        else:
            diffs = compare_trees(BACKUP_ROOT / f'{self.fort}.{tag}', SAVE_ROOT / self.fort)
            self.info['restore_verified'] = not diffs
            if diffs:
                raise CellFail('FAILED', f'restored {self.fort} differs from its backup: {diffs[:3]}')
        self.load(self.fort)
        t, s, _ = self.rig.clock()
        self.info['start_tick'] = t
        self.L(f'loaded {self.fort} (restored from {tag}): tick {t} ({stamp(t)}), season {SEASONS[s]}')

    def load(self, folder):
        try:
            self.rig.must('load', folder, timeout=int(os.environ.get('CX_LOAD_TIMEOUT', 180)) + 150)
        except Hang:
            self.L(f'load {folder} hung; restarting DF and trying once more')
            self.restart_rig()
            self.rig.must('load', folder, timeout=int(os.environ.get('CX_LOAD_TIMEOUT', 180)) + 150)
        self.rig.must('fps', self.c['fps'], self.c['gfps'], timeout=60)

    def restart_rig(self, park=False):
        try:
            if not park:
                self.rig.must('restart', timeout=400)
                return
            # the run's earlier cells' chunk saves share their fort's world name and, past ~12 under one world, push the
            # fort off DF's load list (X2, 9 Oct); move them out while DF is down (never with DF up: 2 Oct crash)
            self.rig.must('stop', timeout=200)
            mine = self.base + '_'
            done = sorted(n for n in (os.listdir(SAVE_ROOT) if SAVE_ROOT.exists() else [])
                          if n.startswith(f'SR_{safe(self.run.id)}_') and not n.startswith(mine))
            if done:
                dest = PARK_ROOT / f'season-run-{self.run.id}'
                if not self.rig.dry:
                    dest.mkdir(parents=True, exist_ok=True)
                    for n in done:
                        shutil.move(str(SAVE_ROOT / n), str(dest / n))
                self.L(f'parked {len(done)} earlier cell save(s) -> {dest}')
            self.rig.must('start', timeout=300)
        except (Hang, RuntimeError) as e:
            raise RunFail(f'DF could not be restarted: {e}')

    def phase(self, ph: dict):
        do = ph.get('do')
        self.L(f'phase {do} {json.dumps({k: v for k, v in ph.items() if k != "do"})[:160]}')
        if do == 'pre':
            for d in self.c['pre']:
                self.do_item(d, 'pre')
        elif do == 'receipts':
            self.receipts()
        elif do == 'run':
            self.run_phase(ph)
        elif do in ('cmd', 'lua', 'lua_file'):
            d = {k: v for k, v in ph.items() if k != 'do'}
            if do == 'cmd' and 'args' in d:
                d['cmd'] = d.pop('args')
            self.do_item(parse_item(d), 'phase')
        elif do == 'state':
            self.json_item(STATE_LUA, ['all'] if ph.get('all') else [], ph['tag'], 'states')
        elif do == 'audit':
            self.json_item(AUDIT_LUA, [], ph['tag'], 'audits')
        elif do == 'save':
            self.save(f'{self.base}_{safe(ph["tag"])}', tag=ph['tag'])
        elif do == 'title':
            self.stop_recorder()
            self.rig.must('title', timeout=200)
        elif do == 'load_saved':
            name = self.saved_tags[ph['tag']]
            self.load(name)
            t, _, _ = self.rig.clock()
            self.L(f'loaded the save {name}: tick {t} ({stamp(t)})')
        elif do == 'restart':
            self.stop_recorder()
            self.restart_rig()
        elif do == 'diff':
            self.diff(ph)
        elif do == 'diff_text':
            a, b = (self.d / ph['a']).read_text(), (self.d / ph['b']).read_text()
            self.check(ph.get('name', f'{ph["a"]} == {ph["b"]}'), a == b, '' if a == b else 'texts differ')
        elif do == 'json_check':
            j = json.loads((self.d / ph['file']).read_text())
            v = j
            for k in ph['key'].split('.'):
                v = v.get(k) if isinstance(v, dict) else None
            ok = {'==': v == ph['value'], '<=': v is not None and v <= ph['value'],
                  '>=': v is not None and v >= ph['value']}[ph.get('op', '==')]
            self.check(ph.get('name', f'{ph["file"]} {ph["key"]} {ph.get("op", "==")} {ph["value"]}'), ok, f'value {v}')
        else:
            raise CellFail('FAILED', f'unknown phase {do!r}')

    def receipts(self):
        for d in self.c['receipts']:
            self.do_item(d, 'receipt')
        if not self.c['receipts']:
            self.L('no receipts in the spec: nothing proves the subject (memory manifest-subject-receipt)')

    # -- stepping
    def run_phase(self, ph: dict):
        c = dict(self.c, **{k: v for k, v in ph.items() if k != 'do'})
        t0, _, _ = self.rig.clock()
        target = resolve_until(c['until'], t0)
        self.L(f'run from {t0} ({stamp(t0)}) to {target} ({stamp(target)}): {target - t0} ticks, chunk {c["chunk"]}, '
               f'dumps every {c["pairs_every"]}')
        if c['recorder']:
            self.start_recorder(c)
        self.dumps(t0, c)
        if c['save_chunks']:
            self.save_chunk()       # a resume point holding the manipulation, before the first step
        next_dump = t0 + c['pairs_every']
        next_chunk = t0 + c['chunk']
        stalls = 0
        while True:
            try:
                t, s, ml = self.rig.clock()
                if not ml:
                    raise CellFail('FAILED', 'the map is gone (DF left the fort)')
                if t >= target - 50:
                    break
                stop = min(target, next_dump, next_chunk)
                n = max(stop - t, 50)
                secs = max(120, n // 40)
                t1 = time.time()
                rc, out, err = self.rig.sh('step', n, secs, timeout=secs + 120)
                dt_s = time.time() - t1
                lines = err.strip().splitlines() or ['(no output)']
                msg = next((l for l in reversed(lines) if 'stepped' in l), lines[-1])   # f0_compare reads this line
                for w in (l for l in lines if 'WARNING' in l or 'drained' in l):
                    self.L(f'  step: {w.replace("[cx-lifecycle] ", "")}')
                tn, _, _ = self.rig.clock()
                self.L(f'step {n}: {msg} (rc {rc}) season={s}')
                self.info['step_s'] += dt_s
                self.info['ticks'] += max(0, tn - t)
                if rc != 0:
                    raise CellFail('FAILED', f'step failed: {msg}')
                stalls = stalls + 1 if tn - t < max(10, n // 10) else 0
                if stalls >= 2:
                    raise Hang(f'two steps in a row moved under a tenth of their ticks ({t} -> {tn})')
                if tn >= next_dump:
                    self.dumps(tn, c)
                    while next_dump <= tn:
                        next_dump += c['pairs_every']
                if tn >= next_chunk or tn >= target - 50:
                    self.chunk_end(tn, c)
                    next_chunk = tn + c['chunk']
            except Hang as e:
                tr = self.recover(e, c)
                next_dump, next_chunk = tr + c['pairs_every'], tr + c['chunk']
                stalls = 0
        if c.get('live_count'):
            self.live_count()
        if c['recorder']:
            self.stop_recorder()

    def chunk_end(self, t: int, c: dict):
        if c['sustain']:
            # rig embarks carry no drink: a dry or salt-only fort dies of thirst ~115k ticks in (memory embark-site-traps)
            self.do_item({'cmd': ['cx-load', 'sustain']}, 'dump')
        if c['ledger_live']:
            self.poll_ledger()
        if c['perf']:
            self.dump_one(['seasonal-wildlife', 'perf'], f'perf/{t}.txt')
        if c['state_every_chunk']:
            try:
                self.json_item(STATE_LUA, [], str(t), 'states')
            except CellFail as e:
                self.info['dump_errors'].append(f'state {t}: {e.reason}')
        if c['save_chunks']:
            self.save_chunk()

    def dumps(self, t: int, c: dict):
        p = self.dump_one(['seasonal-wildlife', 'ecology', 'pairs', 'tsv'], f'pairs/{t}.tsv')
        k = self.dump_one(['seasonal-wildlife', 'cast', 'status'], f'casts/{t}.txt')
        if k is not None and self.casts_first is None:
            self.casts_first = k
            self.write('casts-start.txt', k)
        if c['ledger_live']:
            self.poll_ledger()
        return p

    def dump_one(self, words: list, rel: str):
        """a time-series dump: an error is logged and counted, never written as data (trap 24)"""
        rc, out, err = self.rig.cmd(*words, timeout=60)
        if rc != 0 or not out.strip() or ERR_RE.search(out):
            self.info['dump_errors'].append(f'{" ".join(words)} -> rc {rc}: {(out or err).strip()[:120]}')
            self.L(f'DUMP ERROR {" ".join(words)}: rc {rc} {(out or err).strip()[:120]}')
            return None
        self.write(rel, out)
        return out

    def poll_ledger(self, first=False):
        """append the ledger's new lines to ledger.txt: the tool keeps only its newest 300 (trap 33), so this runs at
        every dump. New lines are counted from the footer's running total; without a footer, deduped by stamp+text."""
        rc, out, _ = self.rig.cmd('seasonal-wildlife', 'ledger', '300', timeout=60)
        if rc != 0 or ERR_RE.search(out):
            self.info['dump_errors'].append(f'ledger rc {rc}: {out.strip()[:120]}')
            return
        lines = [l for l in out.splitlines() if re.match(r'^y\d+\s', l)]
        m = re.search(r'ledger: (\d+) of (\d+) recorded shown', out)
        total = int(m.group(2)) if m else None
        if first:
            self.write('ledger-before.txt', '\n'.join(lines) + '\n')
            self.write('ledger.txt', '')
            self.led_total, self.led_seen = total, set(lines)
            return
        new, notes = [], []
        if total is not None and self.led_total is not None:
            k = total - self.led_total
            if k < 0:
                notes.append(f'# {now()} the ledger went back from {self.led_total} to {total} entries (reloaded from a save)')
                k = 0
            if k > len(lines):
                notes.append(f'# GAP: {k - len(lines)} ledger entries lost between two reads')
                k = len(lines)
            new = lines[len(lines) - k:] if k else []
            self.led_total = total
        else:
            new = [l for l in lines if l not in self.led_seen]
        self.led_seen.update(new)
        if new or notes:
            with open(self.d / 'ledger.txt', 'a') as f:
                f.write(''.join(n + '\n' for n in notes + new))

    def save_chunk(self):
        self.chunk_no += 1
        self.save(f'{self.base}_c{self.chunk_no:03d}')

    def save(self, name: str, tag: str | None = None):
        """a manual save to a NEW folder (never quicksave: it writes DF's autosave slot, memory rig-fast-step-hang)"""
        known = set(os.listdir(SAVE_ROOT)) if SAVE_ROOT.exists() else set()
        known |= set(self.run.saves)
        clash = [k for k in known if k != name and (k.startswith(name) or name.startswith(k))]
        if name in known or clash:
            raise CellFail('FAILED', f'save name {name} exists or is a prefix of/prefixed by {clash[:3]} (load would pick the wrong one)')
        self.rig.must('save', name, timeout=200)
        t, _, _ = self.rig.clock()
        self.last_save = (name, t)
        self.run.saves.append(name)
        self.info['saves'].append({'name': name, 'tick': t})
        if tag:
            self.saved_tags[tag] = name

    # -- the recorder (sw-t1-recorder writes DF_DIR/sw-t1/<name>/*.tsv in game, no RPC polling)
    def start_recorder(self, c):
        self.seg += 1
        name = f'{self.base}_s{self.seg}'
        t, _, _ = self.rig.clock()
        self.do_item({'cmd': ['sw-t1-recorder', 'start', f'sw-t1/{name}', str(c['recorder_every'])], 'expect': 'recording into'}, 'receipt')
        self.segments.append((name, t))
        self.info['segments'].append({'name': name, 'start_tick': t})
        self.rec_on = True

    def stop_recorder(self):
        if not self.rec_on:
            return
        self.rec_on = False
        try:
            rc, out, _ = self.rig.cmd('sw-t1-recorder', 'stop', timeout=60)
            self.L(f'recorder: {out.strip()}')
        except Hang:
            self.L('recorder stop hung')
        self.rig.fetch_recorder(self.segments[-1][0], self.d / 'recorder' / self.segments[-1][0])

    def merge_recorder(self):
        """one events/positions/... table over every segment: segment k keeps its rows up to the tick segment k+1
        started from (a resume rewinds to the chunk save, so the abandoned rows after it are dropped)"""
        if not self.segments:
            return
        for f in ('events.tsv', 'positions.tsv', 'reports.tsv', 'samples.tsv', 'ledger.tsv', 'pops.tsv'):
            head, rows = None, []
            for i, (name, _) in enumerate(self.segments):
                p = self.d / 'recorder' / name / f
                if not p.exists():
                    continue
                upto = self.segments[i + 1][1] if i + 1 < len(self.segments) else None
                lines = p.read_text(encoding='cp437').splitlines()
                head = head or lines[0]
                rows += [l for l in lines[1:] if upto is None or tick_of(l) <= upto]
            if head:
                (self.d / f).write_text('\n'.join([head] + rows) + '\n', encoding='cp437')

    def live_count(self):
        """X0: the recorder's last 'wild' sample against a live count made the recorder's way"""
        code = ('-- sr:wildcount\nlocal U, n = dfhack.units, 0\nfor _, u in ipairs(df.global.world.units.all) do\n'
                ' if not (U.isCitizen(u) or U.isResident(u) or U.isMerchant(u) or U.isInvader(u) or U.isVisitor(u))\n'
                '  and not (U.isAnimal(u) and (U.isTame(u) or U.isDomesticated(u) or U.isFortControlled(u)))\n'
                '  and (U.isWildlife(u) or U.isAnimal(u)) and U.isActive(u) and not u.flags1.inactive and not U.isDead(u)\n'
                ' then n = n + 1 end\nend\nprint(n)')
        out = self.rig.lua(code, timeout=60).strip()
        self.info['live_wild'] = int(out) if out.isdigit() else out

    # -- a hang
    def recover(self, e: Exception, c: dict) -> int:
        t_lost = time.time()
        self.info['hangs'].append({'at': now(), 'why': str(e), 'resume_from': self.last_save[0] if self.last_save else None})
        self.L(f'HANG: {e}')
        if len(self.info['hangs']) > c['max_hangs']:
            raise CellFail('HUNG', f'{len(self.info["hangs"])} hangs (max {c["max_hangs"]})')
        if not self.last_save:
            raise CellFail('HUNG', 'hung before the first chunk save; nothing to resume from')
        self.restart_rig()
        name, tr = self.last_save
        self.load(name)
        self.L(f'resumed from {name} at tick {tr} after {time.time() - t_lost:.0f}s')
        for sub in ('pairs', 'casts', 'perf', 'states'):   # dumps from the abandoned stretch after the save
            for p in (self.d / sub).glob('*') if (self.d / sub).exists() else []:
                if p.is_file() and tick_of(p.name) > tr:
                    (self.d / sub / 'abandoned').mkdir(exist_ok=True)
                    p.rename(self.d / sub / 'abandoned' / p.name)
        with open(self.d / 'ledger.txt', 'a') as f:
            f.write(f'# {now()} resumed from {name} (tick {tr}) after a hang; lines above this one past {stamp(tr)} are from the abandoned stretch\n')
        if c['pre_on_resume']:
            for d in self.c['pre']:
                self.do_item(d, 'pre')
        self.receipts()
        if self.rec_on:
            self.rec_on = False      # the recorder died with DF; its files hold the rows up to the hang
            self.rig.fetch_recorder(self.segments[-1][0], self.d / 'recorder' / self.segments[-1][0])
            self.start_recorder(c)
        return tr

    def diff(self, ph: dict):
        a = json.loads((self.d / 'states' / f'{ph["a"]}.json').read_text()) if ph.get('a') else None
        b = json.loads((self.d / 'states' / f'{ph["b"]}.json').read_text())
        res = diff_states(a, b, ph.get('what', ['pops', 'raws', 'rel']))
        self.write(f'diffs/{ph.get("a", "snapshot")}__{ph["b"]}.json', json.dumps(res, indent=1) + '\n')
        for k in ph.get('expect_zero', []):
            n = res.get('counts', {}).get(k)
            self.check(ph.get('name', 'diff') + f' {k}', n == 0, f'{n} difference(s) ({ph.get("a", "snapshot")} vs {ph["b"]})')

    # -- the end of every cell, whatever happened
    def end(self):
        for step in (self.stop_recorder_safe, self.final_dumps, self.finally_items, self.quit_and_hash):
            try:
                step()
            except RunFail:
                raise
            except Exception as e:   # noqa: BLE001
                self.L(f'end step {step.__name__}: {type(e).__name__}: {e}')
        self.merge_recorder()
        if (self.d / 'pairs').exists():
            last = sorted((p for p in (self.d / 'pairs').glob('*.tsv')), key=lambda p: tick_of(p.name))
            if last:
                shutil.copy2(last[-1], self.d / 'pairs.tsv')
        if (self.d / 'casts').exists():
            last = sorted((p for p in (self.d / 'casts').glob('*.txt')), key=lambda p: tick_of(p.name))
            if last:
                shutil.copy2(last[-1], self.d / 'casts-end.txt')
        want = [f for f in EXPECTED_FILES if self.c['recorder'] or f not in RECORDER_FILES]
        self.info['files'] = {f: (self.d / f).exists() for f in want}
        if self.c.get('check_files'):
            gone = [f for f, ok in self.info['files'].items() if not ok]
            gone += [s for s in ('pairs', 'casts') if not any((self.d / s).glob('*'))] if self.d.exists() else []
            self.check('every receipt and output file present', not gone and bool(self.info['receipts'])
                       and all(r['pass'] for r in self.info['receipts']), f'missing {gone}' if gone else
                       f'{len(self.info["receipts"])} receipt(s), {len(want)} file(s)')
        if 'live_wild' in self.info and (self.d / 'samples.tsv').exists():
            rows = (self.d / 'samples.tsv').read_text(encoding='cp437').splitlines()[1:]
            last = int(rows[-1].split('\t')[1]) if rows else None
            ok = isinstance(self.info['live_wild'], int) and last is not None and abs(last - self.info['live_wild']) <= 2
            self.check('recorder rows match a live count', ok, f'recorder {last} vs live {self.info["live_wild"]} (within 2)')

    def stop_recorder_safe(self):
        if self.rec_on:
            self.stop_recorder()

    def final_dumps(self):
        if self.info['status'] == 'HUNG':
            return
        t, _, ml = self.rig.clock()
        if not ml:
            return
        self.info['end_tick'] = t
        if self.c['ledger_live']:
            self.poll_ledger()
        self.dump_one(['seasonal-wildlife', 'ecology', 'pairs', 'tsv'], f'pairs/{t}.tsv')
        self.dump_one(['seasonal-wildlife', 'cast', 'status'], f'casts/{t}.txt')

    def finally_items(self):
        _, _, ml = self.rig.clock()
        if ml:
            for d in self.c['finally_']:
                try:
                    self.do_item(d, 'finally')
                except CellFail as e:
                    self.L(f'finally: {e.reason}')

    def quit_and_hash(self):
        self.rig.must('title', timeout=200)    # quit WITHOUT saving
        if not self.rig.dry:
            diffs = compare_trees(BACKUP_ROOT / f'{self.fort}.{self.c["backup_tag"]}', SAVE_ROOT / self.fort)
            self.info['post_hash_ok'] = not diffs
            if diffs:
                self.L(f'WARNING: the fort folder changed during the cell: {diffs[:3]}')


EXPECTED_FILES = ['run.log', 'receipts.txt', 'ledger.txt', 'pairs.tsv', 'casts-start.txt', 'casts-end.txt', 'events.tsv',
                  'positions.tsv', 'reports.tsv', 'samples.tsv', 'ledger.tsv']
RECORDER_FILES = {'events.tsv', 'positions.tsv', 'reports.tsv', 'samples.tsv', 'ledger.tsv'}


def lua_with_args(code: str, args: list, tag: str = 'code') -> str:
    """a deployable script sent as code: its arguments as SWSC_ARGS, and a first-line tag naming it (the dry run's fake
    answers by the tag)"""
    return f'-- sr:{re.sub(r"[^A-Za-z0-9_]", "_", tag)}\nlocal SWSC_ARGS = {{' + ', '.join(json.dumps(str(a)) for a in args) + '}\n' + code


def diff_states(a: dict | None, b: dict, what: list) -> dict:
    """differences between two sw-state-check dumps (or one against its worldgen snapshot)"""
    out, counts = {}, {}
    if a is not None and 'pops' in what:
        pa, pb = {p[0]: p for p in a['pops']}, {p[0]: p for p in b['pops']}
        ch = []
        for i in sorted(set(pa) | set(pb)):
            x, y = pa.get(i), pb.get(i)
            if x is None or y is None or x[1] != y[1] or x[3] != y[3] or x[4] != y[4]:
                ch.append({'idx': i, 'a': x, 'b': y})
        out['pops'], counts['pops'] = ch, len(ch)
    if a is not None and 'raws' in what:
        ra, rb = a.get('raws', {}), b.get('raws', {})
        ch = {k: {'a': ra.get(k), 'b': rb.get(k)} for k in sorted(set(ra) & set(rb)) if ra[k] != rb[k]}
        out['raws'], counts['raws'] = ch, len(ch)
    if a is not None and 'rel' in what:
        ra, rb = a.get('rel', {}), b.get('rel', {})
        out['rel'] = {k: [ra.get(k), rb.get(k)] for k in sorted(set(ra) | set(rb))}
        counts['rel_wild'] = (rb.get('wild_any') or 0)
    if 'snapshot' in what:
        snap = b.get('snapshot') or {}
        zeroed, extinct, other = [], [], []
        for p in b['pops']:
            key = p[2]
            s = snap.get(key)
            if s is None and key.startswith('cave:'):
                s = snap.get('cavern:' + p[1], snap.get('deep:' + p[1]))
            if s is None:
                continue
            if p[4] and s > 0:
                extinct.append(p)
            elif p[3] == 0 and s > 0:
                zeroed.append(p)
            elif p[3] != s:
                other.append(p + [s])
        out['snapshot'] = {'zeroed': zeroed, 'extinct': extinct, 'differs': other}
        counts.update(zeroed=len(zeroed), extinct=len(extinct), differs=len(other))
    out['counts'] = counts
    return out


# ------------------------------------------------------------------- run --

class Run:
    def __init__(self, spec: dict, rig: Rig, out: Path):
        self.spec, self.rig, self.out, self.id = spec, rig, out, spec['id']
        self.saves: list[str] = []

    def log(self, msg):
        line = f'{dt.datetime.now().strftime("%H:%M:%S")} {msg}'
        print(line, flush=True)
        with open(self.out / 'run.log', 'a') as f:
            f.write(line + '\n')

    def preflight(self, quit_loaded: bool):
        forts = sorted({a.get('fort') or self.spec.get('fort') for a in self.spec['arms']})
        tag = self.spec.get('backup_tag', 'preverify')
        missing = [f for f in forts if not (BACKUP_ROOT / f'{f}.{tag}').is_dir()]
        if missing:
            msg = f'no {tag} backup for {missing}: run `season-run.py backup {" ".join(missing)}` first (X0)'
            if not self.rig.dry:
                raise RunFail(msg)
            self.log(f'dry run: {msg} (a real run refuses)')
        if self.spec.get('recorder', True) and not (DF_DIR / 'dfhack-config/scripts/sw-t1-recorder.lua').exists():
            msg = 'sw-t1-recorder is not deployed in dfhack-config/scripts'
            if not self.rig.dry:
                raise RunFail(msg)
            self.log(f'dry run: {msg}')
        old = [p.name for p in (DF_DIR / 'sw-t1').glob(f'SR_{safe(self.id)}_*')] if (DF_DIR / 'sw-t1').exists() else []
        old += [p for p in (os.listdir(SAVE_ROOT) if SAVE_ROOT.exists() else []) if p.startswith(f'SR_{safe(self.id)}_')]
        if old and not self.rig.dry:
            raise RunFail(f'run {self.id} has left recorder dirs or saves already ({old[:3]}); pick another --name')
        # other runs' chunk saves share their fort's world name and push the fort off DF's load list (X2, 9 Oct)
        left = sorted(p for p in (os.listdir(SAVE_ROOT) if SAVE_ROOT.exists() else []) if p.startswith('SR_'))
        if left and not self.rig.dry:
            runs = sorted({re.match(r'SR_(.+?)_[^_]+_r\d+_', p).group(1) for p in left if re.match(r'SR_(.+?)_[^_]+_r\d+_', p)})
            raise RunFail(f'{len(left)} chunk save(s) from earlier runs are still in the save dir ({", ".join(runs) or left[0]}): '
                          'park them with DF stopped (season-run.py park data/season-run/RUN) before a new run')
        if not self.rig.running():
            self.log('DF is not running: starting it')
            self.rig.must('start', timeout=300)
        ml, sd = self.rig.where()
        if ml:
            if not quit_loaded:
                raise RunFail(f'a fort is loaded ({sd or "?"}): another session may be using the rig. Leave it, or '
                              'pass --quit-loaded to quit it without saving')
            self.log(f'quitting the loaded fort {sd} without saving (--quit-loaded)')
            self.rig.must('title', timeout=200)

    def go(self, quit_loaded=False):
        meta = {'id': self.id, 'spec': self.spec, 'started': now(), 'dry_run': self.rig.dry}
        self.preflight(quit_loaded)
        meta['provenance'] = provenance(self.rig)
        (self.out / 'run.json').write_text(json.dumps(meta, indent=1) + '\n')
        arms = self.spec['arms']
        reps = int(self.spec.get('reps', 1))
        cells, prev = [], None
        for k, arm in arm_order(arms, reps):
            cfg = arm_config(self.spec, arm)
            if prev is not None and arm['name'] != prev and cfg['restart_between_arms']:
                self.log(f'restarting DF between arms ({prev} -> {arm["name"]}): process age costs speed (memory fps-load-facts)')
                self.rig.must('restart', timeout=400)
            prev = arm['name']
            d = self.out / safe(arm['name']) / f'rep{k}'
            d.mkdir(parents=True, exist_ok=True)
            self.log(f'cell {arm["name"]} rep {k} on {cfg["fort"]}')
            try:
                info = Cell(self, arm['name'], k, cfg, d).go()
            except RunFail as e:
                self.log(f'RUN STOPPED: {e}')
                meta['stopped'] = str(e)
                break
            cells.append({k2: info.get(k2) for k2 in ('arm', 'rep', 'fort', 'status', 'reason', 'wall_s', 'ticks', 'ticks_per_s')})
            self.log(f'cell {arm["name"]} rep {k}: {info["status"]} {info["reason"]}')
        meta.update(ended=now(), cells=cells, saves_written=self.saves)
        auto = DF_DIR / 'dfhack-config/seasonal-wildlife.json'
        meta['autostart_file_after'] = auto.read_text().strip() if auto.exists() else None
        if meta['autostart_file_after'] != meta['provenance'].get('autostart_file'):
            self.log(f'WARNING: the tool\'s autostart file changed during the run: {meta["autostart_file_after"]!r}')
        (self.out / 'run.json').write_text(json.dumps(meta, indent=1) + '\n')
        self.log(f'run {self.id} done: ' + ', '.join(f'{c["arm"]}/r{c["rep"]} {c["status"]}' for c in cells))
        if self.saves:
            self.log(f'{len(self.saves)} save folder(s) written; park them with DF stopped: season-run.py park {self.out}')
        return meta


# --------------------------------------------------------------- analyse --

@functools.lru_cache(maxsize=1)
def v73():
    sys.path.insert(0, str(T1))
    import v73_check  # noqa: E402
    v73_check.raw_tokens = functools.lru_cache(maxsize=1)(v73_check.raw_tokens)
    return v73_check


def ledger_rows(d: Path) -> list[tuple]:
    """[(abs tick, kind, layer, text)]: the recorder's live ledger.tsv, else ledger.txt with day-resolution ticks"""
    p = d / 'ledger.tsv'
    if p.exists():
        out = []
        for line in p.read_text(encoding='cp437').splitlines()[1:]:
            x = line.split('\t')
            if len(x) >= 4 and x[0].isdigit() and x[1] != 'GAP':
                out.append((int(x[0]), x[1], x[2] or '-', x[3]))
        return out
    out = []
    for line in (d / 'ledger.txt').read_text(errors='replace').splitlines() if (d / 'ledger.txt').exists() else []:
        m = re.match(r'^(y\d+\s+\w+\s+\d+)\s+(\w+)\s+(\S+)\s+(.*)$', line)
        if m:
            out.append((unstamp(m.group(1)), m.group(2), m.group(3), m.group(4)))
    return out


def season_of(t: int) -> str:
    return SEASONS[(t % TPY) // TPS]


def positions_by_tick(d: Path) -> dict:
    """{snapshot tick: Counter(race)} of wild units in positions.tsv (written every 1,000 ticks)"""
    snaps = collections.defaultdict(collections.Counter)
    p = d / 'positions.tsv'
    if p.exists():
        for line in p.read_text(encoding='cp437').splitlines()[1:]:
            x = line.split('\t')
            if len(x) >= 4 and x[0].isdigit() and x[3] in ('wild', 'wild-group'):
                snaps[int(x[0])][x[2]] += 1
    return dict(sorted(snaps.items()))


def left_after(snaps: dict, race: str, t: int, end: int) -> dict:
    """units of race on the map at the first snapshot after t, and the first snapshot within 10 days where none are"""
    ticks = [k for k in snaps if k >= t]
    if not ticks:
        return {'at_dismiss': None, 'left': None, 'note': 'no snapshot after the send-off'}
    n0 = snaps[ticks[0]][race]
    gone = next((k for k in ticks if k <= t + 10 * TPD and snaps[k][race] == 0), None)
    censored = gone is None and end < t + 10 * TPD
    return {'at_dismiss': n0, 'gone_after_days': round((gone - t) / TPD, 1) if gone is not None else None,
            'left': True if gone is not None else (None if censored else False),
            'note': 'run ended within 10 days' if censored else ''}


def analyse_cell(d: Path) -> dict:
    A: dict = {}
    if (d / 'events.tsv').exists() and (d / 'casts-start.txt').exists():
        V = v73()
        S = V.summarize(str(d))
        C = V.casts(str(d / 'casts-start.txt'))
        ev = V.fill_removed(V.read(str(d / 'events.tsv')))
        led = ledger_rows(d)
        starts = [int(r['tick']) for r in ev if r['event'] == 'SAMPLE_START']
        t_start = min(starts) if starts else min((int(r['tick']) for r in ev), default=0)
        t_end = max((int(r['tick']) for r in ev), default=t_start)
        A['ticks'] = [t_start, t_end]
        A['season_changes'] = [b for b in range((t_start // TPS + 1) * TPS, t_end + 1, TPS)]
        # off-cast arrivals with their lead time after the season change
        per = collections.defaultdict(lambda: collections.Counter())
        offs, arrive_tick = [], {}
        for r in ev:
            if r['event'] != 'ARRIVE':
                continue
            arrive_tick[r['id']] = int(r['tick'])
            L = r.get('tlayer')
            if L not in MANAGED:
                continue
            if r['race'] in PLACED_PLANTS:   # v7.5: sponges are scenery the tool places, never cast (user 12 Oct)
                continue
            t = int(r['tick'])
            s = season_of(t)
            det = r.get('detail', '')
            age = re.search(r'age (-?\d+)', det)
            birth = 'mother #' in det or ('inside' in det and age is not None and int(age.group(1)) < 10 * TPD)
            if r['race'] in C.get((L, s), set()):
                per[(L, s)]['in_cast'] += 1
                continue
            # a species another layer casts this season, arriving through its other entry (X3 brook: ALLIGATOR, a curated
            # water apex in the summer water cast, walks in through its land entry and records as land) is in the cast:
            # the tool's turnover keys it the same way and rightly leaves it
            if any(r['race'] in C.get((L2, s), set()) for L2 in MANAGED):
                per[(L, s)]['in_cast_other_layer'] += 1
                continue
            stand = (L, s, r['race']) in S['stand']
            lead = t - (t - t % TPS)
            per[(L, s)]['stand_in' if stand else ('off_birth' if birth else 'off')] += 1
            if not stand and not birth and lead > TPD:
                per[(L, s)]['off_late'] += 1
            offs.append({'layer': L, 'season': s, 'race': r['race'], 'id': r['id'], 'tick': t, 'lead_days': round(lead / TPD, 2),
                         'birth': birth, 'stand_in': stand, 'change_in_run': t - lead >= t_start})
        A['arrivals'] = {f'{L} {s}': dict(c) for (L, s), c in sorted(per.items())}
        A['offcast_arrivals'] = offs
        A['offcast_late'] = sum(c['off_late'] for c in per.values())
        A['managed_arrivals'] = sum(sum(c.values()) - c['off_late'] for c in per.values())
        A['ledger_groups_off'] = [{'layer': k[0], 'season': k[1], 'source': k[2], 'race': k[4], 'units': v}
                                  for k, v in sorted(S['src'].items()) if k[3] == 'OFF']
        A['ledger_complete'] = S['complete']
        A['handovers_before_apply'] = dict(S['early'])
        # send-offs: in-cast trims (should be 0) and the turnover's dismissals (should all leave within 10 days)
        snaps = positions_by_tick(d)
        # one record per (tick, layer, species): its groups' own dismiss lines summed; the turnover's summary line
        # ("season cast: N group(s) ... sent off (A, B)") names the same groups, so it only tags them
        turn = collections.defaultdict(collections.Counter)
        for t, kind, L, text in led:
            m = re.search(r'season cast: .*sent off \((.*)\)', text) if kind == 'dismiss' and t is not None else None
            if m:
                turn[t].update(x.strip() for x in m.group(1).split(','))
        recs, taken = collections.OrderedDict(), []
        for t, kind, L, text in led:
            if kind == 'dismiss' and 'taken off the map' in text:   # v7.4 leaveCheck: an earlier send-off taken off, not a new one
                mt = re.search(r'([A-Z][A-Z0-9_ ]*?) x(\d+) sent off ([0-9.]+) days ago', text)
                if mt:
                    taken.append({'tick': t, 'layer': L, 'race': mt.group(1).strip(), 'units': int(mt.group(2)), 'after_days': float(mt.group(3))})
                continue
            m = re.search(r'([A-Z][A-Z0-9_ ]*?) x(\d+) (?:dismissed|sent off)', text) if kind == 'dismiss' and t is not None else None
            if not (m and L in MANAGED):
                continue
            race, s = m.group(1).strip(), season_of(t)
            r = recs.setdefault((t, L, race), {'tick': t, 'layer': L, 'season': s, 'race': race, 'groups': 0, 'units': 0,
                                               'why': 'turnover' if turn[t][race] else ('gate' if 'over its cap' in text else 'dismiss'),
                                               'in_cast': race in C.get((L, s), set())})
            r['groups'] += 1
            r['units'] += int(m.group(2))
        for t, c in turn.items():          # a species the turnover named with no dismiss line of its own
            for race, n in c.items():
                if not any(k[0] == t and k[2] == race for k in recs):
                    s = season_of(t)
                    recs[(t, '?', race)] = {'tick': t, 'layer': '?', 'season': s, 'race': race, 'groups': n, 'units': None,
                                            'why': 'turnover', 'in_cast': any(race in C.get((L2, s), set()) for L2 in MANAGED)}
        trims, turnover, depth_off = [], [], []
        # v7.5: each cavern has its own cast, so the turnover rightly sends off a group at a depth its species is not
        # cast at while it is cast at another (folded 'cavern' says in cast). castTurnover dismisses a species whose key
        # is in season for that reason only, so a turnover send-off of a species cast in some caverns but not all is one;
        # the 'detached RACE xN in cavern K' lines before it give the depths where known (an adopted group has none).
        det = collections.defaultdict(list)
        for t, kind, L, text in led:
            m = re.match(r'detached (.+?) x\d+ in cavern (\d)', text) if kind == 'wave' and t is not None else None
            if m:
                det[m.group(1)].append((t, int(m.group(2))))
        for r in recs.values():
            r.update(left_after(snaps, r['race'], r['tick'], t_end))
            if r['in_cast'] and r['layer'] == 'cavern' and r['why'] == 'turnover' and any(L.startswith('cavern') and L != 'cavern' for L, _ in C):
                cast_at = {k for k in (1, 2, 3) if r['race'] in C.get((f'cavern{k}', r['season']), set())}
                off_depth = [k for t, k in det.get(r['race'], []) if t < r['tick'] and k not in cast_at]
                caverns = {int(L[-1]) for L, _ in C if L.startswith('cavern') and L != 'cavern'}
                if cast_at and cast_at != caverns:
                    r.update(why='depth turnover', in_cast=False, depths=sorted(set(off_depth)), cast_at=sorted(cast_at),
                             note='left is by race: other units of it stay in its cast cavern')
                    depth_off.append(r)
                    continue
            (trims if r['in_cast'] else turnover).append(r)
        A['depth_sendoffs'] = depth_off
        # the cavern gate holding a layer to its group cap sends in-cast groups off by design (F19); only a turnover's
        # or a trim's send-off of an in-cast group is the fault X3 looks for
        A['taken_off'] = taken   # v7.4: send-offs still here after the grace, taken off the map by the tool
        A['in_cast_sendoffs'] = [r for r in trims if r['why'] != 'gate']
        A['gate_sendoffs'] = [r for r in trims if r['why'] == 'gate']
        A['offcast_sendoffs'] = turnover
        A['sendoffs_not_left'] = [x for x in turnover if x.get('left') is False]
        # stand-ins made, and whether the stand-in species went on arriving off-cast after its season
        A['stand_ins'] = [{'layer': L, 'season': s, 'stand_in': si, 'for': fo,
                           'arrivals_in_season': sum(1 for o in offs if o['stand_in'] and o['race'] == si and o['season'] == s),
                           'arrivals_off_cast_later': sum(1 for o in offs if not o['stand_in'] and o['race'] == si
                                                          and SEASONS.index(o['season']) > SEASONS.index(s))}
                          for (L, s, si), fo in sorted(S['stand'].items())]
        # drownings within 2 days of arriving, and of a tool draw into a water body
        draws = [(t, re.match(r'^(.+?) x\d+ drawn', text).group(1)) for t, k, L, text in led
                 if k == 'arrive' and t is not None and re.match(r'^(.+?) x\d+ drawn', text)]
        drown = collections.defaultdict(collections.Counter)
        for r in ev:
            if r['event'] == 'DIE' and 'cause DROWN' in r.get('detail', ''):
                t, a = int(r['tick']), arrive_tick.get(r['id'])
                c = drown[r['race']]
                c['drowned'] += 1
                if a is not None and t - a <= 2 * TPD:
                    c['within_2d_of_arrival'] += 1
                    if any(race == r['race'] and a - 600 <= td <= a + 300 for td, race in draws):
                        c['within_2d_of_a_draw'] += 1
        A['drownings'] = {k: dict(v) for k, v in sorted(drown.items())}
        A.update(v75_audit(d, ev, C, t_start))
        yt = year_turn(d, ev, C, t_start, t_end)
        if yt:
            A['year_turn'] = yt
    # reserve conservation, from consecutive state dumps (live quantity + held reserve per config key)
    states = sorted((json.loads(p.read_text()) for p in (d / 'states').glob('*.json')), key=lambda j: j['tick']) \
        if (d / 'states').exists() else []
    if len(states) >= 2:
        arrivals = []
        if (d / 'events.tsv').exists():
            arrivals = [(int(r['tick']), r['race']) for r in v73().read(str(d / 'events.tsv')) if r['event'] == 'ARRIVE']
        pairs = []
        for a, b in zip(states, states[1:]):
            lost, drawn, short, untracked = [], [], [], []
            ta, tb = totals(a), totals(b)
            # DF itself draws vermin and colony stock with no ARRIVE event (spawning from the entry), so a drop there
            # is DF's draw, not a lost reserve
            vermin = {p[2] for p in a['pops'] if len(p) > 5 and ('Vermin' in str(p[5]) or 'Colony' in str(p[5]))}
            # F7 is about the tool's reserve: an entry it never held is DF's to draw (X3 ocean: cave:MAGMA_CRAB 180 -> 175,
            # a magma-sea species of the unmanaged deep layer whose arrivals the recorder does not log)
            held = {p[2] for st in (a, b) for p in st['pops'] if str(p[0]) in ((st.get('reserve') or {}) if isinstance(st.get('reserve'), dict) else {})}
            for key, (race, before) in ta.items():
                after = tb.get(key, (race, 0))[1]
                came = sum(1 for t, r in arrivals if a['tick'] < t <= b['tick'] and r == race)
                if before > 0 and after < before - came - 2:
                    row = {'key': key, 'before': before, 'after': after, 'arrivals_between': came}
                    # DF debits a wave's planned size from the entry and may land fewer animals (X3 ocean: SEA OTTER
                    # 13 -> 6 on one entry, "x2 arrived", no tool action), so a drop with a DF arrival of the species
                    # in the window is DF's draw, not a lost reserve
                    (drawn if key in vermin else short if came else lost if key in held else untracked).append(row)
            pairs.append({'from': a['tick'], 'to': b['tick'], 'crosses_change': a['tick'] // TPS != b['tick'] // TPS,
                          'keys_lost': lost, 'vermin_drawn': drawn, 'df_wave_shortfall': short, 'never_held': untracked})
        A['reserve'] = {'pairs': pairs, 'conserved': all(not p['keys_lost'] for p in pairs)}
    # tool time per pass: the last perf table of each DF session (FUSE stats reset at a reload)
    perf = sorted((d / 'perf').glob('*.txt'), key=lambda p: tick_of(p.name)) if (d / 'perf').exists() else []
    if perf:
        jobs, worst = {}, None
        for line in perf[-1].read_text().splitlines():
            m = re.match(r'^(\S.*?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+(\S+)\s+(\S+)\s+(\d+)$', line)
            if m and m.group(1) != 'job / lap':
                jobs[m.group(1)] = {'runs': int(m.group(2)), 'ms_per_run': float(m.group(6)), 'worst_ms': int(m.group(4))}
            w = re.search(r'worst single tick: (\d+) ms', line)
            if w:
                worst = int(w.group(1))
        A['perf'] = {'from': perf[-1].name, 'jobs': jobs, 'worst_tick_ms': worst}
    if (d / 'run.log').exists() and (d / 'events.tsv').exists() and (d / 'samples.tsv').exists():
        try:
            S2, species, gate, fps, steps = __import__('f0_compare').cavern(str(d))
            A['cavern'] = {s: {'species': dict(species[s].most_common(8)), 'gate_sendoffs': gate[s]} for s in species}
            A['fps_median'] = sorted(fps)[len(fps) // 2] if fps else None
            A['s_per_10k_median'] = sorted(steps)[len(steps) // 2] if steps else None
        except Exception as e:   # noqa: BLE001
            A['cavern'] = f'f0_compare failed: {e}'
    # the X3 criteria, where the data allow them
    if 'offcast_late' in A and not A['season_changes']:
        A['verdict'] = 'n/a (no season change in the run)'
    elif 'offcast_late' in A:
        thin = A['managed_arrivals'] < 5
        crit = {'no off-cast arrival later than a day after a change': A['offcast_late'] == 0,
                'no in-cast group trimmed or sent off': not A['in_cast_sendoffs'],
                'every dismissed group off the map within 10 days': not A['sendoffs_not_left']}
        if 'year_turn' in A:   # the casts are built once: the year turn changes nothing
            crit['the casts unchanged across the new year, none rebuilt'] = A['year_turn']['casts_unchanged'] and not A['year_turn']['cast_builds_after_start']
        if 'cavern_wrong_depth_late' in A:   # v7.5: each cavern its own cast
            crit['no cavern arrival at a depth its species is not cast at, later than a day'] = A['cavern_wrong_depth_late'] == 0
        A['criteria'] = crit
        A['verdict'] = (f'PENDING (inconclusive: {A["managed_arrivals"]} managed-layer arrivals)' if thin
                        else ('PASS' if all(crit.values()) else 'FAIL'))
    return A


def v75_audit(d: Path, ev: list, C: dict, t_start: int) -> dict:
    """v7.5: cavern arrivals against their own depth's cast (the band of the arrival's z, from the `caverns` receipt),
    and the arrivals of species whose population entry the tool created (the fp_created receipt)"""
    out: dict = {}
    rc = (d / 'receipts.txt').read_text(errors='replace') if (d / 'receipts.txt').exists() else ''
    bands = [(int(m.group(1)), int(m.group(2)), int(m.group(3)))
             for m in re.finditer(r'depth (\d) \(cave -?\d+\) z(\d+)-(\d+)', rc)]
    created = collections.defaultdict(set)   # token -> {'surface'} | {depth, ...}
    for m in re.finditer(r'^fp_created (surface|cave) (.+?) (-?\d+)$', rc, re.M):
        created[m.group(2)].add('surface' if m.group(1) == 'surface' else int(m.group(3)))
    seven = any(L.startswith('cavern') and L != 'cavern' for L, _ in C)
    # by entry: the tool's group tracker names the cavern of the population entry a group came from ("detached TOKEN xN in
    # cavern K"), which is what the per-depth mask controls. The arrival's z (below) is where DF put it: a cavern band's
    # z range from the survey is only where it opens at the map edge (X3v75: units of the cavern-3 entry arrived at z26,
    # inside cavern 2's edge band)
    if seven and (d / 'ledger.tsv').exists():
        per_e = collections.defaultdict(collections.Counter)
        wrong_e = []
        for t, kind, L, text in ledger_rows(d):
            m = re.match(r'detached (.+?) x(\d+) in cavern (\d)', text) if kind == 'wave' and t is not None else None
            if not m:
                continue
            tok, n, k, s = m.group(1), int(m.group(2)), int(m.group(3)), season_of(t)
            here = tok in C.get((f'cavern{k}', s), set())
            other = [j for j in (1, 2, 3) if j != k and tok in C.get((f'cavern{j}', s), set())]
            per_e[(k, s)]['own_depth_cast' if here else ('other_depth_cast_only' if other else 'no_cavern_cast')] += n
            if not here and other:
                wrong_e.append({'race': tok, 'units': n, 'depth': k, 'season': s, 'cast_at': other,
                                'lead_days': round((t % TPS) / TPD, 2), 'tick': t})
        out['cavern_entry_depth'] = {f'cavern{k} {s}': dict(c) for (k, s), c in sorted(per_e.items(), key=str)}
        out['cavern_wrong_depth'] = wrong_e
        out['cavern_wrong_depth_late'] = sum(w['units'] for w in wrong_e if w['lead_days'] > 1)
    if bands and seven:
        per = collections.defaultdict(collections.Counter)
        wrong = []
        for r in ev:
            if r['event'] != 'ARRIVE' or r.get('tlayer') != 'cavern':
                continue
            z, t = int(r['z']), int(r['tick'])
            dep = next((b[0] for b in bands if b[1] <= z <= b[2]), None)
            s = season_of(t)
            if dep is None:
                per[('?', s)]['no_band'] += 1
                continue
            here = r['race'] in C.get((f'cavern{dep + 1}', s), set())
            other = [k for k in (1, 2, 3) if k != dep + 1 and r['race'] in C.get((f'cavern{k}', s), set())]
            lead = t - (t - t % TPS)
            kind = 'own_depth_cast' if here else ('other_depth_cast_only' if other else 'no_cavern_cast')
            per[(dep + 1, s)][kind] += 1
            if not here and other:
                wrong.append({'race': r['race'], 'id': r['id'], 'depth': dep + 1, 'season': s, 'cast_at': other,
                              'lead_days': round(lead / TPD, 2), 'tick': t})
        out['cavern_z_depth'] = {f'cavern{k} {s}': dict(c) for (k, s), c in sorted(per.items(), key=str)}
        out['cavern_z_elsewhere'] = len(wrong)   # where DF put the units; informational
    if created:
        drawn = collections.Counter()
        for r in ev:
            if r['event'] == 'ARRIVE' and r['race'] in created and int(r['tick']) >= t_start:
                drawn[(r['race'], r.get('tlayer') or r.get('layer'))] += 1
        out['created_entries'] = {'species': len(created),
                                  'cave_species': sorted(k for k, v in created.items() if v - {'surface'}),
                                  'arrived': {f'{k[0]} ({k[1]})': n for k, n in sorted(drawn.items())}}
    return out


def year_turn(d: Path, ev: list, C: dict, t_start: int, t_end: int) -> dict:
    """a run that crosses a new year: the casts are the same at the end (no rebuild: casts are built once, user 12 Oct),
    no cast build in the ledger after the start, and the new year's arrivals are the cast of their season"""
    y0, y1 = t_start // TPY, t_end // TPY
    if y1 <= y0:
        return {}
    out: dict = {'from_year_tick': y1 * TPY}
    def body(f):
        t = (d / f).read_text(errors='replace') if (d / f).exists() else ''
        return t.split('\n', 1)[0], [ln for ln in t.splitlines()[1:] if ln.strip()]
    h0, b0 = body('casts-start.txt')
    h1, b1 = body('casts-end.txt')
    out['casts_header'] = [h0, h1]
    out['casts_unchanged'] = bool(b0) and b0 == b1
    out['cast_builds_after_start'] = [text for t, kind, L, text in ledger_rows(d)
                                      if t is not None and t > t_start + 600 and 'casts for year' in text]
    per = collections.Counter()
    for r in ev:
        if r['event'] != 'ARRIVE' or int(r['tick']) < y1 * TPY or r.get('tlayer') not in MANAGED or r['race'] in PLACED_PLANTS:
            continue
        s = season_of(int(r['tick']))
        per['in_cast' if any(r['race'] in C.get((L, s), set()) for L in MANAGED) else 'off_cast'] += 1
    out['new_year_arrivals'] = dict(per)
    return out


def totals(state: dict) -> dict:
    res = state.get('reserve') or {}
    if isinstance(res, list):
        res = {}
    out = {}
    for p in state['pops']:
        race, q = p[1], p[3] + int(res.get(str(p[0]), 0) or 0)
        r0, n = out.get(p[2], (race, 0))
        out[p[2]] = (race, n + q)
    return out


def cmd_analyse(rundir: Path):
    rundir = rundir.resolve()
    cells = sorted(p.parent for p in rundir.glob('*/rep*/cell.json'))
    if not cells:
        cells = sorted({p.parent for p in rundir.glob('*/rep*/run.log')})
    if not cells:
        sys.exit(f'analyse: no cells under {rundir}')
    sys.path.insert(0, str(T1))
    rows = []
    for d in cells:
        cj = d / 'cell.json'
        J = json.loads(cj.read_text()) if cj.exists() else {}
        J['analysis'] = analyse_cell(d)
        if (d / 'events.tsv').exists() and (d / 'casts-start.txt').exists():
            p = subprocess.run([sys.executable, str(T1 / 'v73_check.py'), str(d)], capture_output=True, text=True, cwd=str(T1))
            (d / 'v73_check.txt').write_text(p.stdout + (('\n' + p.stderr) if p.returncode else ''))
        cj.write_text(json.dumps(J, indent=1, default=str) + '\n')
        R, A = J.get('run', {}), J['analysis']
        rows.append({'cell': str(d.relative_to(rundir)), 'arm': R.get('arm', d.parent.name), 'rep': R.get('rep'),
                     'status': R.get('status', '?'), 'reason': R.get('reason', ''), 'verdict': A.get('verdict', '-'),
                     'managed_arrivals': A.get('managed_arrivals'), 'offcast_late': A.get('offcast_late'),
                     'in_cast_sendoffs': len(A.get('in_cast_sendoffs', [])),
                     'gate_sendoffs': len(A.get('gate_sendoffs', [])),
                     'sendoffs_not_left': len(A.get('sendoffs_not_left', [])),
                     'drowned_2d_draw': sum(v.get('within_2d_of_a_draw', 0) for v in A.get('drownings', {}).values()),
                     'reserve_conserved': A.get('reserve', {}).get('conserved'),
                     'checks_failed': [c['name'] for c in R.get('checks', []) if not c['pass']],
                     'checks_passed': sum(1 for c in R.get('checks', []) if c['pass']),
                     'hangs': len(R.get('hangs', [])), 'ticks_per_s': R.get('ticks_per_s'),
                     'wrong_depth_late': A.get('cavern_wrong_depth_late'),
                     'created_arrivals': sum((A.get('created_entries') or {}).get('arrived', {}).values()) if A.get('created_entries') else None})
        print(f'{rows[-1]["cell"]}: {rows[-1]["status"]} {rows[-1]["verdict"]}')
    arms = collections.OrderedDict()
    for r in rows:
        a = arms.setdefault(r['arm'], collections.Counter())
        a['cells'] += 1
        a['ok'] += r['status'] == 'OK'
        for k in ('managed_arrivals', 'offcast_late', 'in_cast_sendoffs', 'gate_sendoffs', 'sendoffs_not_left', 'drowned_2d_draw', 'hangs'):
            a[k] += r[k] or 0
        a['checks_failed'] += len(r['checks_failed'])
    summary = {'rundir': str(rundir), 'analysed': now(), 'cells': rows, 'arms': {k: dict(v) for k, v in arms.items()}}
    (rundir / 'summary.json').write_text(json.dumps(summary, indent=1, default=str) + '\n')
    md = [f'# {rundir.name}: season-run summary ({now()})', '',
          '| cell | status | verdict | managed arrivals | off-cast late | in-cast send-offs | gate send-offs | not left in 10 d | drowned after a draw | reserve kept | checks failed | hangs | t/s | cavern wrong depth late | arrivals from created entries |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        md.append(f'| {r["cell"]} | {r["status"]} {r["reason"][:60]} | {r["verdict"]} | {r["managed_arrivals"]} | {r["offcast_late"]} | '
                  f'{r["in_cast_sendoffs"]} | {r["gate_sendoffs"]} | {r["sendoffs_not_left"]} | {r["drowned_2d_draw"]} | {r["reserve_conserved"]} | '
                  f'{", ".join(r["checks_failed"]) or "-"} ({r["checks_passed"]} passed) | {r["hangs"]} | {r["ticks_per_s"]} | '
                  f'{"-" if r["wrong_depth_late"] is None else r["wrong_depth_late"]} | {"-" if r["created_arrivals"] is None else r["created_arrivals"]} |')
    md += ['', '| arm | cells | OK | managed arrivals | off-cast late | in-cast send-offs | gate send-offs | not left | drowned after a draw | checks failed | hangs |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    for k, a in arms.items():
        md.append(f'| {k} | {a["cells"]} | {a["ok"]} | {a["managed_arrivals"]} | {a["offcast_late"]} | {a["in_cast_sendoffs"]} | {a["gate_sendoffs"]} | '
                  f'{a["sendoffs_not_left"]} | {a["drowned_2d_draw"]} | {a["checks_failed"]} | {a["hangs"]} |')
    (rundir / 'summary.md').write_text('\n'.join(md) + '\n')
    print(f'wrote {rundir / "summary.json"} and summary.md ({len(rows)} cells)')


# ---------------------------------------------------------------- backup --

def cmd_backup(forts: list, tag: str, rig: Rig):
    """save-backup each fort and prove the copy byte-identical; refuse a fort DF has loaded"""
    running = rig.running()
    loaded, save_dir = rig.where() if running else (False, '')
    print(f'DF {"running" if running else "stopped"}; ' + (f'map loaded: {save_dir or "?"}' if loaded else 'no map loaded'))
    bad = 0
    for f in forts:
        src, dest = SAVE_ROOT / f, BACKUP_ROOT / f'{f}.{tag}'
        if not src.is_dir():
            print(f'{f}: MISSING (no folder in the save dir)'); bad += 1
            continue
        if loaded and (save_dir == f or save_dir in ('', 'current')):
            print(f'{f}: REFUSED -- DF has {"this fort" if save_dir == f else "an unidentified fort"} loaded; '
                  'leave it (title) or stop DF first (memory save-dir-while-running)'); bad += 1
            continue
        if dest.exists():
            diffs = compare_trees(src, dest)
            print(f'{f}: backup exists, ' + ('byte-identical (kept)' if not diffs else f'DIFFERS from the save ({len(diffs)}: {diffs[:2]}); left alone'))
            bad += bool(diffs)
            continue
        rig.must('save-backup', f, tag, timeout=600)
        if rig.dry:
            m = tree_manifest(src)
            print(f'{f}: dry run: would copy {len(m)} file(s), {sum(s for s, _ in m.values()) / 1e6:.1f} MB to {dest.name}')
            continue
        diffs = compare_trees(src, dest)
        n = len(tree_manifest(dest))
        print(f'{f}: backed up to {dest} -- ' + ('byte-identical (%d files, size + sha256)' % n if not diffs else f'MISMATCH {diffs[:3]}'))
        bad += bool(diffs)
    return 1 if bad else 0


def cmd_park(rundir: Path, rig: Rig):
    """move the run's save folders out of DF's save dir: only with DF stopped (memory save-dir-while-running)"""
    meta = json.loads((rundir / 'run.json').read_text())
    if rig.running():
        sys.exit('park: DF is running; stop it first (moving saves under a running DF crashed it, 2 Oct)')
    dest = PARK_ROOT / f'season-run-{meta["id"]}'
    for name in meta.get('saves_written', []):
        if (SAVE_ROOT / name).is_dir():
            print(f'{"would move" if rig.dry else "moving"} {name} -> {dest}')
            if not rig.dry:
                dest.mkdir(parents=True, exist_ok=True)
                shutil.move(str(SAVE_ROOT / name), str(dest / name))


# ------------------------------------------------------------------ main --

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='verb', required=True)
    b = sub.add_parser('backup')
    b.add_argument('forts', nargs='*', default=DEFAULT_FORTS)
    b.add_argument('--tag', default='preverify')
    r = sub.add_parser('run')
    r.add_argument('spec', nargs='?')
    r.add_argument('--fort'); r.add_argument('--name'); r.add_argument('--arm')
    r.add_argument('--until'); r.add_argument('--chunk', type=int); r.add_argument('--pairs-every', type=int)
    r.add_argument('--reps', type=int)
    for k in ('save-chunks', 'sustain', 'recorder', 'ledger-live', 'restart-between-arms'):
        r.add_argument(f'--{k}', action=argparse.BooleanOptionalAction, default=None)
    r.add_argument('--pre', action='append', help="a manipulation: 'seasonal-wildlife cast restfreq 0' or 'lua:CODE'")
    r.add_argument('--receipt', action='append', help="'CMD ~ REGEX': the output must match, or the cell aborts")
    r.add_argument('--quit-loaded', action='store_true', help='quit a fort found loaded at the start (without saving)')
    r.add_argument('--out', type=Path, help='output root (default data/season-run, dry runs data/season-run/dryrun)')
    r.add_argument('--dry-hang-at', type=int, default=0, help='dry run: the Nth step hangs')
    a = sub.add_parser('analyse')
    a.add_argument('rundir', type=Path)
    p = sub.add_parser('park')
    p.add_argument('rundir', type=Path)
    for x in (b, r, p):
        x.add_argument('--dry-run', action='store_true', help='fake every rig call; nothing reaches DF')
    args = ap.parse_args()

    if args.verb == 'analyse':
        return cmd_analyse(args.rundir)
    log = lambda m: print(m, flush=True)  # noqa: E731
    rig = FakeRig(log, getattr(args, 'dry_hang_at', 0)) if args.dry_run else Rig(log)
    if args.verb == 'backup':
        return cmd_backup(args.forts, args.tag, rig)
    if args.verb == 'park':
        return cmd_park(args.rundir, rig)
    spec = load_spec(args)
    root = args.out or (OUT_ROOT / 'dryrun' if args.dry_run else OUT_ROOT)
    out = root / re.sub(r'[^\w.-]', '_', spec['id'])
    if out.exists():
        if not args.dry_run:
            sys.exit(f'{out} exists: a run name is used once (its saves and recorder dirs carry it)')
        shutil.rmtree(out)
    out.mkdir(parents=True)
    run = Run(spec, rig, out)
    rig.log = run.log
    try:
        meta = run.go(quit_loaded=args.quit_loaded)
    except RunFail as e:
        run.log(f'REFUSED: {e}')
        return 2
    print(f'\noutput: {out}\nnext:   {Path(sys.argv[0]).name} analyse {out}')
    return 0 if all(c['status'] == 'OK' for c in meta['cells']) else 1


if __name__ == '__main__':
    sys.exit(main())
