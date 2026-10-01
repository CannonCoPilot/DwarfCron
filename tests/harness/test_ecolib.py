"""v7.1 harness rules (scripts/ecolib.py), offline."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import ecolib  # noqa: E402


def test_counterbalance_reverses_even_reps():
    cells = ["a", "b", "c"]
    assert ecolib.arm_order(cells, 1) == ["a", "b", "c"]
    assert ecolib.arm_order(cells, 2) == ["c", "b", "a"]
    assert ecolib.arm_order(cells, 5) == ["a", "b", "c"]


def test_rotate_is_a_latin_square_over_n_reps():
    cells = ["a", "b", "c", "d", "e"]
    rows = [ecolib.arm_order(cells, r, "rotate") for r in range(1, 6)]
    for pos in range(5):
        assert sorted(r[pos] for r in rows) == cells


def test_fixed_and_unknown_order():
    assert ecolib.arm_order(["a", "b"], 2, "fixed") == ["a", "b"]
    with pytest.raises(ValueError):
        ecolib.arm_order(["a", "b"], 1, "random")


def test_parse_and_eval_check_uses_latest_matching_row():
    chk = ecolib.parse_check("cfg[path=v7.pack_sneak].value==1.0")
    rows = ["eco cfg path=v7.pack_floor value=0.05", "eco cfg path=v7.pack_sneak value=0.25",
            "eco cfg path=v7.pack_sneak value=1"]
    ok, msg = ecolib.eval_check(chk, rows)
    assert ok, msg
    ok, _ = ecolib.eval_check(ecolib.parse_check("cfg[path=v7.pack_floor].value==0.2"), rows)
    assert not ok


def test_missing_receipt_fails_and_booleans_compare_as_text():
    ok, msg = ecolib.eval_check(ecolib.parse_check("skill.with>0"), ["eco spawn token=WOLF placed=5"])
    assert not ok and "no 'skill' receipt" in msg
    ok, _ = ecolib.eval_check(ecolib.parse_check("cfg[path=ecology.nudge].value==false"),
                              ["eco cfg path=ecology.nudge value=false"])
    assert ok


def test_bad_check_is_rejected_before_rig_time():
    with pytest.raises(ValueError):
        ecolib.parse_check("cfg value is 3")


def test_auto_failures():
    assert ecolib.auto_failures(["eco spawn token=WOLF asked=5 placed=0 ids="])
    assert not ecolib.auto_failures(["eco spawn token=WOLF asked=5 placed=3 ids=1,2,3"])
    assert ecolib.auto_failures(["eco rel a=WOLF b=DEER pairs=0"])
    assert ecolib.auto_failures(["eco adopt token=WOLF asked=5 groups=0 members=0 adopted=0 roam=0 reply=usage"])
    assert ecolib.auto_failures(["eco wipecheck remaining=2 pending=0 DEER=2"])
    # largest-male with no male names no leader: correct (R32), not a failed manipulation
    assert not ecolib.auto_failures(["eco lead token=DEER how=largest-male leader=-1 leader_size=0 members=6"])
    assert ecolib.auto_failures(["eco lead token=DEER how=lowest leader=-1 leader_size=0 members=6"])
    assert not ecolib.auto_failures(["eco watch incidents0=3 t0=1"])


def test_bouts():
    assert ecolib.bouts([0, 10, 50, 400, 420, 2000], gap=100) == 3
    assert ecolib.bouts([], 100) == 0
    rows = ["eco atk tag=x t=0 a=7 atok=WOLF aor=placed d=9 dtok=DEER dor=placed hid=0 hn=0",
            "eco atk tag=x t=30 a=7 atok=WOLF aor=placed d=9 dtok=DEER dor=placed hid=1 hn=3",
            "eco atk tag=x t=900 a=7 atok=WOLF aor=placed d=9 dtok=DEER dor=placed hid=0 hn=3"]
    assert ecolib.bouts_from_rows(rows) == {"7": ("WOLF", 3, 2)}


def test_spawn_opts_fill_positionals_and_dedupe():
    assert ecolib.with_roam("spawn WOLF 5 {X} {Y} {Z} 3") == "spawn WOLF 5 {X} {Y} {Z} 3 land any 200000 roam"
    assert ecolib.spawn_opts("spawn ORCA 6 1 2 3 4 water", "legacy", "roam") == "spawn ORCA 6 1 2 3 4 water any 200000 legacy roam"
    assert ecolib.with_roam("spawn WOLF 5 1 2 3 3 land any 100 roam") == "spawn WOLF 5 1 2 3 3 land any 100 roam"
    assert ecolib.spawn_opts("spawn WOLF 5 1 2 3 3 land any 100 slot=stranger", "slot=none") == \
        "spawn WOLF 5 1 2 3 3 land any 100 slot=none"
    assert ecolib.with_roam("rel WOLF DEER") == "rel WOLF DEER"


def test_scale_and_estimate():
    assert ecolib.scale_step("step:5040", 0.5) == "step:2520"
    assert ecolib.scale_step("spawn X", 0.5) == "spawn X"
    blk = {"cells": {"a": {"steps": ["step:1000", "spawn W 1 1 1 1"], "ticks": 2000}, "b": {"steps": [], "ticks": 3000}}}
    e = ecolib.estimate(blk, reps=5, load="arm", tps=500, load_s=100, rpc_s=0)
    assert e["ticks_per_rep"] == 6000 and e["loads"] == 10
    assert e["minutes"] == round((6000 / 500 + 2 * 100) * 5 / 60, 1)
