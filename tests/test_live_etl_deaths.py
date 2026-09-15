"""Death change-detection: what `_prev` is allowed to mean.

Two defects met here, both found by running the live watcher against a real
fortress rather than by reading the code:

  * A TEXT column was handed the integer sentinel -1. asyncpg refused the
    whole statement, so a single unreadable cause lost every death in that
    cycle. The old guard tested `== "-1"` and the value arrived as `-1`.
  * `_prev` outlives the process and carried no provenance, so the first
    cycle after a restart diffed the new fortress against whichever one was
    last on disk. That does not produce a few wrong rows: every unit of the
    previous world reads as departed, and a death is written for each.

The second is why the guard refuses rather than repairs. Missing one cycle of
change detection costs a cycle; a false comparison invents a massacre.
"""
from __future__ import annotations

import json

import pytest

from chronicler.dfhack.file_writer import (
    prev_is_comparable,
    read_prev_meta,
    rotate_previous,
)
from chronicler.dfhack.live_etl import _normalize_death_cause


# ── the sentinel, in every shape the bridge emits it ─────────────────────

@pytest.mark.parametrize("value", [None, "", "-1", -1, "NONE", "none"])
def test_a_missing_cause_becomes_unknown(value):
    assert _normalize_death_cause(value) == "unknown"


def test_the_integer_sentinel_is_caught_like_the_string_one():
    """The exact defect: -1 passed where "-1" was caught."""
    assert _normalize_death_cause(-1) == _normalize_death_cause("-1") == "unknown"


def test_a_real_cause_survives():
    assert _normalize_death_cause("STARVED") == "STARVED"


def test_a_numeric_cause_becomes_text_not_an_int():
    """The column is TEXT. An int here is what asyncpg rejected."""
    got = _normalize_death_cause(7)
    assert got == "7"
    assert isinstance(got, str)


# ── provenance on _prev ──────────────────────────────────────────────────

def live_dir(tmp_path, *, world_id, cycle, units=("u1",)):
    """A live dir whose current cycle names `world_id` and `cycle`."""
    d = tmp_path / "live"
    (d / "_prev").mkdir(parents=True, exist_ok=True)
    (d / "_meta.json").write_text(json.dumps(
        {"world_id": world_id, "cycle": cycle, "game_year": 50, "game_tick": 1}))
    (d / "fortress_units.json").write_text(json.dumps(
        [{"id": u, "hist_fig_id": 10} for u in units]))
    return d


def test_rotation_carries_the_metadata_forward(tmp_path):
    """Without this `_prev` cannot say which world it is."""
    d = live_dir(tmp_path, world_id=2, cycle=4)
    rotate_previous(d)
    assert read_prev_meta(d) == {"world_id": 2, "cycle": 4,
                                 "game_year": 50, "game_tick": 1}


def test_consecutive_cycles_of_one_world_are_comparable(tmp_path):
    d = live_dir(tmp_path, world_id=2, cycle=4)
    rotate_previous(d)
    (d / "_meta.json").write_text(json.dumps({"world_id": 2, "cycle": 5}))
    assert prev_is_comparable(2, d) is True


def test_another_world_is_refused(tmp_path):
    """The live failure: a session on world 2 met world 1's units."""
    d = live_dir(tmp_path, world_id=1, cycle=99)
    rotate_previous(d)
    (d / "_meta.json").write_text(json.dumps({"world_id": 2, "cycle": 100}))
    assert prev_is_comparable(2, d) is False


def test_a_gap_in_cycles_is_refused(tmp_path):
    """A restart resumes numbering; the fortress moved on in between."""
    d = live_dir(tmp_path, world_id=2, cycle=4)
    rotate_previous(d)
    (d / "_meta.json").write_text(json.dumps({"world_id": 2, "cycle": 9}))
    assert prev_is_comparable(2, d) is False


def test_the_same_cycle_twice_is_refused(tmp_path):
    """Re-reading one cycle is not a diff; every unit would look unchanged."""
    d = live_dir(tmp_path, world_id=2, cycle=4)
    rotate_previous(d)
    assert prev_is_comparable(2, d) is False


def test_a_prev_written_before_metadata_was_rotated_is_refused(tmp_path):
    """Upgrade case: `_prev` exists on disk with no `_meta.json` beside it.

    It cannot prove which world it holds, so it does not get to be trusted.
    """
    d = live_dir(tmp_path, world_id=2, cycle=5)
    (d / "_prev" / "fortress_units.json").write_text(json.dumps([{"id": "old"}]))
    assert not (d / "_prev" / "_meta.json").exists()
    assert prev_is_comparable(2, d) is False


def test_an_empty_live_dir_is_refused(tmp_path):
    d = tmp_path / "live"
    (d / "_prev").mkdir(parents=True)
    assert prev_is_comparable(2, d) is False
