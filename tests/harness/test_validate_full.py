"""Offline checks of scripts/validate-full.py (validator wave 2, v7.1). No rig: --list and --dry-run only.

- the claim register has unique ids, a known surface, and every v7.1 row maps to a phase_v71 sub-phase;
- every shipped backlog item names a claim that exists;
- a --dry-run of phase_v71 against a v7.1 checkout passes luac53, the engine-name check and the verb check
  (skipped when no v7.1 checkout is found: set SW_TOOL to one).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VF = ROOT / "scripts" / "validate-full.py"


def listing():
    p = subprocess.run([sys.executable, str(VF), "--list"], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    return [line.split("\t") for line in p.stdout.splitlines() if line.strip()]


def test_ids_unique_and_surfaces_known():
    rows = listing()
    ids = [r[0] for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    assert not dup, f"duplicate claim ids: {dup}"
    assert all(r[1] in {"GUI", "MECH", "CLI", "DOC", "PERF"} for r in rows), [r[:2] for r in rows if r[1] not in {"GUI", "MECH", "CLI", "DOC", "PERF"}]


def test_v71_rows_map_to_a_sub_phase():
    src = VF.read_text()
    areas = re.search(r"V71_AREAS = \[([^\]]*)\]", src).group(1)
    areas = set(re.findall(r'"(\w+)"', areas))
    rows = listing()
    v71 = [r for r in rows if r[3]]
    assert v71, "no v7.1 rows"
    for r in v71:
        if r[3]:
            assert r[3] in areas, f"{r[0]} maps to unknown area {r[3]}"
            assert f"def v71_{r[3]}():" in src, f"no sub-phase v71_{r[3]} for {r[0]}"
    unassigned = [r[0] for r in rows if r[0].startswith(("mech.v71.", "web.v71.", "perf.p")) and not r[3]]
    assert not unassigned, f"v7.1 rows with no docs/v7.1/<stream>.md source: {unassigned}"


def test_shipped_backlog_points_at_claims():
    src = VF.read_text()
    block = re.search(r"SHIPPED_BACKLOG = \{(.*?)\n\}", src, re.S).group(1)
    ids = {r[0] for r in listing()}
    for bl, via in re.findall(r'"(bl\.\w+)": \[([^\]]*)\]', block):
        assert bl in ids, bl
        for v in re.findall(r'"([\w.]+)"', via):
            assert v in ids, f"{bl} resolves through {v}, which is not a claim"


def v71_checkout():
    for c in (os.environ.get("SW_TOOL"), str(Path.home() / "Claude/Projects/seasonal-wildlife")):
        if c and (Path(c) / "scripts/seasonal-wildlife-controls.lua").exists():
            return c
    return None


@pytest.mark.skipif(v71_checkout() is None, reason="no v7.1 seasonal-wildlife checkout (set SW_TOOL)")
def test_dry_run_v71_clean():
    env = dict(os.environ, SW_TOOL=v71_checkout())
    p = subprocess.run([sys.executable, str(VF), "--dry-run", "--only", "v71"], capture_output=True, text=True, timeout=600, env=env)
    out = p.stdout + p.stderr
    assert "luac53 -p: 0 chunk(s) failed" in out or "SKIPPED" in out, out[-3000:]
    assert "engine names not found in the tool: 0" in out, out[-3000:]
    assert "verbs not in the dispatcher: none" in out, out[-3000:]
    assert "phases or sub-phases that raised: 0" in out, out[-3000:]
    assert p.returncode == 0, out[-3000:]
