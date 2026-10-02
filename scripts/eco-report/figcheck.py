#!/usr/bin/env python3
"""Figure-spec check for the ECO report builder (Part 1 plan H7, 1 Oct 2026).

Eight specs on the ECO page were written value-first (spec.x a number, spec.y the category), so every mark became NaN
and the frame came out empty (data/eco-review/part1/D-frequency-figures.md section 4). The renderer's convention for every
categorical form is spec.x = category, spec.y = value (template.html `build`). This module checks each spec the way the
renderer will read it and returns the problems; build.py refuses to write the page while any placed figure has one.

Checks (static: the same coercion as template.html's num(), no browser):
  value-first   a categorical form whose x column is numeric in every row while its y column holds text
  no-rows       a drawn form with no rows (the frame renders, the marks do not)
  zero-marks    no row carries both a category and a finite value for the mark the form draws
  missing-key   the spec names a field (x, y, lo, hi, value) that no row has
  ref-on-axis   a reference value that lies outside the value column's range by more than 10x (figure 17 drew a tick
                reference, 2,400, on a wave-count axis that ran 0-6) -- reported as a warning, not an error

Usage: python3 scripts/eco-report/figcheck.py [experiments.json ...]   # prints problems, exits 1 when any error
"""
import json
import math
import sys
from pathlib import Path

CATEGORICAL = ("bar", "dot", "dumbbell", "box", "strip", "stackedBar", "groupedBar", "range")
NOT_DRAWN = ("table",)


def num(v):
    """template.html's num(): numbers stay, numeric strings become numbers, everything else is left alone."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v
    if v is not None and v != "":
        try:
            return float(v)
        except (TypeError, ValueError):
            return v
    return v


def finite(v):
    v = num(v)
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def is_text(v):
    v = num(v)
    return isinstance(v, str) and v != ""


def value_keys(spec, rows):
    """The field(s) whose values the form draws as marks."""
    form = spec.get("form")
    if form == "range":
        r0 = rows[0] if rows else {}
        lo = spec.get("lo") or ("min" if "min" in r0 else "lo")
        hi = spec.get("hi") or ("max" if "max" in r0 else "hi")
        return [lo, hi]
    if form == "heatmap":
        s = spec.get("series")
        r0 = rows[0] if rows else {}
        v = spec.get("value") or spec.get("z") or ("value" if "value" in r0 else (s if s and isinstance(num(r0.get(s)), (int, float)) else spec.get("y")))
        return [v]
    if form == "histogram":
        return [spec.get("x")]
    return [spec.get("y")]


def check(spec):
    """Return a list of (severity, code, message) for one figure spec."""
    out = []
    fid, form = spec.get("id", "?"), spec.get("form")
    rows = spec.get("rows") or []
    if form in NOT_DRAWN or form is None:
        return out
    if not rows:
        return [("error", "no-rows", f"{fid}: form {form} has no rows; it renders an empty frame")]
    x, y = spec.get("x"), spec.get("y")
    keys = set().union(*(r.keys() for r in rows))
    for k in [x] + value_keys(spec, rows):
        if k and k not in keys:
            out.append(("error", "missing-key", f"{fid}: field '{k}' is named by the spec but no row has it"))
    if form in CATEGORICAL and x and y and x in keys and y in keys and form != "range":
        if all(finite(r.get(x)) for r in rows) and any(is_text(r.get(y)) for r in rows):
            out.append(("error", "value-first",
                        f"{fid}: {form} spec is value-first (x='{x}' is numeric in every row, y='{y}' holds text); "
                        f"categorical forms read x as the category and y as the value -- swap them"))
    vks = [k for k in value_keys(spec, rows) if k]
    if form in CATEGORICAL or form in ("heatmap", "line", "scatter"):
        cat_ok = (lambda r: r.get(x) is not None) if x else (lambda r: True)
        if form in ("line", "scatter"):
            drawn = [r for r in rows if finite(r.get(x)) or is_text(r.get(x))]
            drawn = [r for r in drawn if all(finite(r.get(k)) for k in vks)]
        elif form == "range":   # the bar needs lo and hi; the renderer also dots spec.y when it is set
            drawn = [r for r in rows if cat_ok(r) and (all(finite(r.get(k)) for k in vks) or (y and finite(r.get(y))))]
        else:
            drawn = [r for r in rows if cat_ok(r) and any(finite(r.get(k)) for k in vks)]
        if vks and not drawn and not any(c == "value-first" for _, c, _ in out):
            out.append(("error", "zero-marks", f"{fid}: no row has both a category and a finite value in {vks}; 0 marks would be drawn"))
    vals = [num(r.get(k)) for r in rows for k in vks if finite(r.get(k))]
    if vals and spec.get("reference"):
        lo, hi = min(vals), max(vals)
        span = max(abs(hi), abs(lo), 1e-9)
        for rf in spec["reference"]:
            v = rf.get("value") if isinstance(rf, dict) else rf
            if isinstance(rf, dict) and rf.get("axis") == "x":   # a category/time-axis reference (N1's tick 2,400), not a value
                continue
            if finite(v) and abs(num(v)) > 10 * span:
                out.append(("warn", "ref-on-axis", f"{fid}: reference {v} is far outside the value axis ({lo}..{hi}); "
                                                   f"is it on the right axis?"))
    return out


def check_all(specs):
    problems = []
    for s in specs:
        problems.extend(check(s))
    return problems


def main(argv):
    paths = argv[1:] or [str(Path(__file__).resolve().parents[2] / "data" / "eco-report" / "experiments.json")]
    errs = 0
    for p in paths:
        specs = json.loads(Path(p).read_text()).get("figures", [])
        for sev, code, msg in check_all(specs):
            print(f"{sev:5} {code:12} {msg}")
            errs += sev == "error"
        print(f"{p}: {len(specs)} specs, {errs} error(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
