"""H7: the ECO report's figure-spec check (scripts/eco-report/figcheck.py). Offline, no browser."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "eco-report"))
import figcheck  # noqa: E402


def codes(spec):
    return {c for _, c, _ in figcheck.check(spec)}


def test_value_first_dot_fails():
    spec = {"id": "coh", "form": "dot", "x": "width", "y": "group",
            "rows": [{"width": 5.2, "group": "Duck flock x12"}, {"width": 139.7, "group": "Orca pod x6"}]}
    assert "value-first" in codes(spec)


def test_category_first_dot_passes():
    spec = {"id": "coh", "form": "dot", "x": "group", "y": "width",
            "rows": [{"width": 5.2, "group": "Duck flock x12"}, {"width": "139.7", "group": "Orca pod x6"}]}
    assert codes(spec) == set()


def test_no_rows_and_zero_marks():
    assert "no-rows" in codes({"id": "a", "form": "bar", "x": "k", "y": "v", "rows": []})
    spec = {"id": "b", "form": "bar", "x": "k", "y": "v", "rows": [{"k": "A", "v": None}, {"k": "B", "v": ""}]}
    assert "zero-marks" in codes(spec)


def test_missing_key_on_range():
    spec = {"id": "15a", "form": "range", "x": "id", "y": "depth_max",
            "rows": [{"id": "FLOATING_GUTS", "depth_min": 2, "depth_max": 3}]}
    c = codes(spec)
    assert "missing-key" in c and "zero-marks" not in c   # the dots still draw; the bars do not


def test_reference_on_wrong_axis_is_a_warning():
    spec = {"id": "n1", "form": "line", "x": "t", "y": "waves", "reference": [{"value": 2400}],
            "rows": [{"t": 0, "waves": 0}, {"t": 5000, "waves": 6}]}
    probs = figcheck.check(spec)
    assert [(s, c) for s, c, _ in probs] == [("warn", "ref-on-axis")]


def test_tables_are_not_checked():
    assert codes({"id": "t", "form": "table", "rows": []}) == set()
