#!/usr/bin/env python3
"""Run a wilderpop experiment from a manifest, on the CrossOver rig.

The apparatus the Wilderpop Model (section 7) specifies, built as data-in,
data-out:

    cx-experiment.py run experiments/E9a.json [--reps N] [--arm NAME] [--budget T]
    cx-experiment.py report data/experiments/E9a/<run-id>

One replicate = restore the fort's backup, load it, prove the wildlife tool is
disarmed, read provenance, take a baseline, apply the arm's manipulations, then
step-and-sample until the tick budget is spent or the arm's stop rule fires.
Every observation is one record. Arrivals are attributed by NEW unit id and
the six-field reference the unit carries -- never by entry debits. A liveness
breach invalidates the replicate and stops it. The fort is quit WITHOUT saving
and its folder is checksummed against the backup, so a replicate can never
contaminate the next.

Outputs, under data/experiments/<id>/<run-id>/:
    manifest.json     the manifest as run (copied, with CLI overrides applied)
    provenance.json   versions, seed, fort, commits, fps cap, per-replicate rates
    rows.tsv          long format: run arm rep tick abs_tick subject metric value
    units.tsv         wide, per sample: every wild unit's record
    pops.tsv          wide, per sample: every pool entry
    events.tsv        arrivals, departures, deaths, manipulations, breaches
    log.txt

Rules this obeys (df-rig skill): one RPC call at a time; never fps 0; fort
state is in memory until `save`, and this never calls save.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIFECYCLE = ROOT / "scripts" / "cx-lifecycle.sh"
RPC = ROOT / "scripts" / "cx-rpc.py"
PY = ROOT / ".venv" / "bin" / "python"
if not PY.exists():
    PY = Path(sys.executable)

TICKS_PER_YEAR = 403_200
HOME = Path.home()
SAVE_ROOT = Path(os.environ.get(
    "DF_SAVE_DIR",
    HOME / "Library/Application Support/CrossOver/Bottles/Win10/drive_c/users/crossover/AppData/Roaming/Bay 12 Games/Dwarf Fortress/save"))
BACKUP_ROOT = Path(os.environ.get(
    "CX_SAVE_BACKUPS", HOME / "Library/Application Support/CrossOver/df-snapshots/saves"))
TOOL_REPO = Path(os.environ.get("SW_REPO", HOME / "Claude/Projects/seasonal-wildlife"))


# ----------------------------------------------------------------- rig I/O --

class Rig:
    """Sequential access to the rig. Every call is one subprocess; nothing
    here runs concurrently, which is the one-RPC-at-a-time rule by construction."""

    def __init__(self, log):
        self.log = log
        self.port = None

    def sh(self, *verb, timeout=600) -> tuple[int, str, str]:
        p = subprocess.run([str(LIFECYCLE), *map(str, verb)], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.replace("\r", ""), p.stderr.replace("\r", "")

    def must(self, *verb, timeout=600) -> str:
        rc, out, err = self.sh(*verb, timeout=timeout)
        if rc != 0:
            raise RuntimeError(f"cx-lifecycle {' '.join(map(str, verb))} failed rc={rc}\n{err.strip()}")
        for line in err.strip().splitlines():
            self.log(f"  [rig] {line.replace('[cx-lifecycle] ', '')}")
        return out

    def _port(self) -> str:
        if not self.port:
            _, out, _ = self.sh("port")
            self.port = out.strip()
            if not self.port:
                raise RuntimeError("no DFHack port; is the rig running?")
        return self.port

    def lua(self, script: str, timeout=120) -> str:
        p = subprocess.run([str(PY), str(RPC), "--port", self._port(), "--timeout", str(timeout), "--lua", script],
                           capture_output=True, text=True, timeout=timeout + 30)
        if p.returncode != 0:
            raise RuntimeError(f"lua failed: {p.stderr.strip()}\n{script[:200]}")
        return p.stdout.replace("\r", "")

    def probe(self, *args) -> list[dict]:
        """Run cx-probe <args> and return its TSV as a list of dicts."""
        q = ", ".join(json.dumps(str(a)) for a in args)
        out = self.lua(f"dfhack.run_script('cx-probe', {q})")
        lines = [l for l in out.splitlines() if l.strip()]
        if not lines:
            raise RuntimeError(f"cx-probe {' '.join(map(str, args))} printed nothing")
        if lines[0].startswith(("Error", "error", "usage")) or "traceback" in out.lower():
            raise RuntimeError(f"cx-probe {' '.join(map(str, args))}: {out.strip()[:400]}")
        head = lines[0].split("\t")
        return [dict(zip(head, l.split("\t"))) for l in lines[1:]]

    def probe_line(self, *args) -> str:
        q = ", ".join(json.dumps(str(a)) for a in args)
        return self.lua(f"dfhack.run_script('cx-probe', {q})").strip()

    def state(self) -> dict:
        line = self.must("state")
        return dict(kv.split("=", 1) for kv in line.split() if "=" in kv)

    def step(self, ticks: int, secs: int) -> tuple[int, float, list[str]]:
        """Run the fort `ticks` ticks. Returns (ticks stepped, wall seconds, drained-popup notes)."""
        t0 = time.monotonic()
        rc, out, err = self.sh("step", ticks, secs, timeout=secs + 120)
        wall = time.monotonic() - t0
        m = re.search(r"stepped (-?\d+) ticks", err)
        if rc != 0 or not m:
            raise RuntimeError(f"step failed: {err.strip()}")
        drained = [l for l in err.splitlines() if "drained" in l]
        return int(m.group(1)), wall, drained


# --------------------------------------------------------------- checksums --

def tree_hash(path: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(path)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def git_head(repo: Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or "?"
    except OSError:
        return "?"


# ------------------------------------------------------------------ writer --

class Out:
    def __init__(self, run_dir: Path):
        self.dir = run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
        self._log = open(run_dir / "log.txt", "a")
        self.rows = open(run_dir / "rows.tsv", "a")
        self.events = open(run_dir / "events.tsv", "a")
        self.units = open(run_dir / "units.tsv", "a")
        self.pops = open(run_dir / "pops.tsv", "a")
        # the WHOLE pool (every region tile DF loaded), once at the start and once at the
        # end of each replicate: the second instrument for "which tile was debited"
        self.pops_all = open(run_dir / "pops_all.tsv", "a")
        self.combat = open(run_dir / "combat.tsv", "a")
        if self.rows.tell() == 0:
            self.rows.write("run\tarm\trep\ttick\tabs_tick\tsubject\tmetric\tvalue\n")
        if self.events.tell() == 0:
            self.events.write("run\tarm\trep\ttick\tabs_tick\tevent\tsubject\tdetail\n")
        self._unit_head = None
        self._pop_head = None
        self._pops_all_head = None
        self._combat_head = None

    def log(self, msg: str):
        line = f"{dt.datetime.now():%H:%M:%S} {msg}"
        print(line, flush=True)
        self._log.write(line + "\n"); self._log.flush()

    def row(self, ctx, tick, abs_tick, subject, metric, value):
        self.rows.write(f"{ctx['run']}\t{ctx['arm']}\t{ctx['rep']}\t{tick}\t{abs_tick}\t{subject}\t{metric}\t{value}\n")

    def event(self, ctx, tick, abs_tick, event, subject, detail):
        detail = str(detail).replace("\t", " ").replace("\r", " ").replace("\n", " | ")
        subject = str(subject).replace("\t", " ").replace("\n", " ")
        self.events.write(f"{ctx['run']}\t{ctx['arm']}\t{ctx['rep']}\t{tick}\t{abs_tick}\t{event}\t{subject}\t{detail}\n")
        self.events.flush()

    def wide(self, fh, headattr, ctx, tick, abs_tick, recs: list[dict]):
        if not recs:
            return
        head = list(recs[0].keys())
        if getattr(self, headattr) is None:
            setattr(self, headattr, head)
            if fh.tell() == 0:
                fh.write("run\tarm\trep\ttick\tabs_tick\t" + "\t".join(head) + "\n")
        for r in recs:
            fh.write(f"{ctx['run']}\t{ctx['arm']}\t{ctx['rep']}\t{tick}\t{abs_tick}\t" + "\t".join(r.get(k, "") for k in head) + "\n")

    def flush(self):
        for fh in (self.rows, self.events, self.units, self.pops, self.pops_all, self.combat, self._log):
            fh.flush()


# ---------------------------------------------------------------- the run --

def abs_tick_of(clock: dict) -> int:
    return int(clock["year"]) * TICKS_PER_YEAR + int(clock["tick"])


def apply_manipulation(rig: Rig, out: Out, ctx, tick, abs_tick, m: str):
    """A manipulation is either `probe:<args>` or raw Lua."""
    if m.startswith("probe:"):
        receipt = rig.probe_line(*m[6:].split())
    else:
        receipt = rig.lua(m).strip()
    out.log(f"  manipulation: {m} -> {receipt}")
    out.event(ctx, tick, abs_tick, "manipulation", m, receipt)


def stop_rule_fires(rule: dict | None, stats: dict) -> str | None:
    if not rule:
        return None
    if stats["ticks"] < rule.get("min_ticks", 0):
        return None
    if "arrivals_min" in rule and stats["arrivals"] >= rule["arrivals_min"]:
        return f"arrivals {stats['arrivals']} >= {rule['arrivals_min']}"
    if "departures_min" in rule and stats["departures"] >= rule["departures_min"]:
        return f"departures {stats['departures']} >= {rule['departures_min']}"
    if "arrived_all_departed" in rule and stats["arrivals"] > 0 and stats["arrived_present"] == 0:
        return "every arrived unit has left or died"
    if "ticks_after_on_arrival" in rule and stats.get("on_arrival_at") is not None \
            and stats["ticks"] - stats["on_arrival_at"] >= rule["ticks_after_on_arrival"]:
        return f"{rule['ticks_after_on_arrival']} ticks after the on_arrival manipulation"
    if "ticks_after_first_exit" in rule and stats.get("first_exit") is not None \
            and stats["ticks"] - stats["first_exit"] >= rule["ticks_after_first_exit"]:
        return f"{rule['ticks_after_first_exit']} ticks after the first departure or death"
    return None


def run_replicate(rig: Rig, out: Out, man: dict, arm: dict, rep: int, run_id: str, prov: dict) -> dict:
    ctx = {"run": run_id, "arm": arm["name"], "rep": rep}
    # an arm may name its own fort (E26 runs RIVER3 and LAKE arms in one manifest)
    fort, backup = arm.get("fort", man["fort"]), arm.get("backup", man["backup"])
    sample_every = int(arm.get("sample_every", man.get("sample_every", 200)))
    budget = int(arm.get("tick_budget", man.get("tick_budget", 20000)))
    fps = int(man.get("fps", 1000))
    step_secs = max(30, int(sample_every / 20) + 30)
    summary = {"arm": arm["name"], "rep": rep, "valid": True, "breaches": [], "control": None,
               "arrivals": 0, "departures": 0, "deaths": 0, "ticks": 0, "wall_s": 0.0, "stop": None}

    out.log(f"== {man['id']} arm={arm['name']} rep={rep} fort={fort} budget={budget} every={sample_every}")

    # 1. a clean fort: DF at the title, restore the backup, prove the bytes.
    st = rig.state()
    if st.get("map") == "true":
        rig.must("title")
    rig.must("save-restore", backup)
    h_backup = prov["backup_sha256"]
    h_restored = tree_hash(SAVE_ROOT / fort)
    if h_restored != h_backup:
        raise RuntimeError(f"restored save does not match backup: {h_restored[:12]} vs {h_backup[:12]}")
    out.log(f"  restored {backup} -> {fort} sha256 {h_backup[:12]}")

    # 2. load, drain, cap the tick rate.
    rig.must("load", fort, timeout=400)
    rig.must("popups")
    rig.must("fps", fps, 10)

    # 3. (the tool-state assertion runs after the t0 manipulations, which may enable it)

    # 4. baseline.
    clock = rig.probe("clock")[0]
    t_start = abs_tick_of(clock)
    tick = int(clock["tick"]); abs_tick = t_start
    units = rig.probe("units")
    pops = rig.probe("pops")
    out.wide(out.units, "_unit_head", ctx, tick, abs_tick, units)
    out.wide(out.pops, "_pop_head", ctx, tick, abs_tick, pops)
    pops_all0 = rig.probe("pops", "all")
    out.wide(out.pops_all, "_pops_all_head", ctx, tick, abs_tick, [dict(phase="start", **r) for r in pops_all0])
    for k, v in clock.items():
        out.row(ctx, tick, abs_tick, "clock", k, v)
    present = {u["id"]: u for u in units if u["wild"] == "1" and u["dead"] == "0" and u["inactive"] == "0"}
    ever_present = set(present.keys())          # every id that has ever been on the map here
    first_listed: dict[str, int] = {u["id"]: t_start for u in units}   # a unit is listed inactive for a sample before it is present
    arrived: dict[str, dict] = {}                # id -> record at first sighting
    first_seen: dict[str, int] = {}
    out.log(f"  baseline: {len(present)} wild units on map, {len(pops)} pool entries, tick {tick} year {clock['year']}")
    out.event(ctx, tick, abs_tick, "baseline", "wild_present", str(len(present)))
    for u in present.values():
        out.event(ctx, tick, abs_tick, "present_at_start", u["id"], f"{u['species']} ref6={u['ref6']} countdown={u['countdown']} flag_src={u['flag_src']}")

    # 5. manipulations at t0.
    for m in arm.get("pre", []):
        apply_manipulation(rig, out, ctx, tick, abs_tick, m)
    # the tool must now be in the state the manifest demands, and stay there
    tool = rig.probe("tool")[0]
    want = man.get("tool_must_be", {"enabled": 0, "groups_enabled": 0, "scheduled": 0})
    bad = {k: tool.get(k) for k, v in want.items() if str(tool.get(k)) != str(v)}
    if bad:
        raise RuntimeError(f"seasonal-wildlife state {tool} violates tool_must_be {want}: {bad}")
    out.log(f"  tool state ok: {tool}")
    if man.get("roster"):
        roster = rig.probe("roster")
        with open(out.dir / "roster.tsv", "a") as fh:
            if fh.tell() == 0:
                fh.write("run\tarm\trep\ttoken\tseasons\tallowed\n")
            for r in roster:
                fh.write(f"{ctx['run']}\t{ctx['arm']}\t{ctx['rep']}\t{r['token']}\t{r['seasons']}\t{r['allowed']}\n")
        out.log(f"  roster: {len(roster)} assigned tokens")
    # manipulations deferred to the first SURFACE wave of at least on_arrival_min_units
    # units; {ids} = all their ids, {id0} {id1} ... = by index, {ids_after1} / {ids_after2}
    # = every id but the first one / two. Applied once.
    on_arrival = list(arm.get("on_arrival", []))
    on_arrival_min = int(arm.get("on_arrival_min_units", 1))
    on_arrival_done = False
    on_arrival_at = None
    # a second batch applied `ticks` after on_arrival (the restore step of a loop)
    after = arm.get("after_on_arrival") or {}
    after_done = not after
    first_exit = None
    combat_since = -1
    # a repeating manipulation: every `ticks`, run `do` (a release cadence for a census)
    every = arm.get("every") or {}
    every_next = int(every.get("ticks", 0)) if every else None
    every_count = 0
    want_combat = bool(man.get("combat") or arm.get("combat"))

    # 6. step and sample.
    control = arm.get("control") or man.get("control")
    control_met = None
    stop = arm.get("stop_when")
    stepped_total = 0
    wall_total = 0.0
    while stepped_total < budget:
        n, wall, drained = rig.step(sample_every, step_secs)
        wall_total += wall
        for d in drained:
            out.event(ctx, tick, abs_tick, "popups_drained", "step", d.strip())
        clock = rig.probe("clock")[0]
        new_abs = abs_tick_of(clock)
        advanced = new_abs - abs_tick
        tick = int(clock["tick"]); abs_tick = new_abs
        stepped_total += max(advanced, 0)
        for k in ("fps_achieved", "units_active", "popups", "paused"):
            out.row(ctx, tick, abs_tick, "clock", k, clock[k])
        out.row(ctx, tick, abs_tick, "clock", "ticks_per_wall_s", f"{n / wall:.1f}" if wall else "")

        # liveness invariants: tick advanced, popups empty, tool unchanged, unit count sane
        breach = []
        if advanced <= 0:
            breach.append(f"tick did not advance ({abs_tick})")
        if int(clock["popups"]) != 0:
            breach.append(f"popup queue not empty ({clock['popups']})")
        if not (0 < int(clock["units_active"]) < 10000):
            breach.append(f"unit count insane ({clock['units_active']})")
        tool_now = rig.probe("tool")[0]
        if tool_now != tool:
            breach.append(f"tool state changed {tool} -> {tool_now}")
        if breach:
            summary["breaches"].extend(breach); summary["valid"] = False
            for b_ in breach:
                out.event(ctx, tick, abs_tick, "breach", "invariant", b_)
                out.log(f"  BREACH: {b_}")
            break

        units = rig.probe("units")
        pops = rig.probe("pops")
        out.wide(out.units, "_unit_head", ctx, tick, abs_tick, units)
        out.wide(out.pops, "_pop_head", ctx, tick, abs_tick, pops)
        if want_combat:
            reps_ = rig.probe("combat", combat_since)
            if reps_:
                out.wide(out.combat, "_combat_head", ctx, tick, abs_tick, reps_)
                combat_since = max(int(r["report"]) for r in reps_)
                summary["combat_reports"] = summary.get("combat_reports", 0) + len(reps_)

        now = {u["id"]: u for u in units}
        for i in now:
            first_listed.setdefault(i, abs_tick)
        now_present = {i: u for i, u in now.items() if u["wild"] == "1" and u["dead"] == "0" and u["inactive"] == "0"}
        # arrivals: a wild unit id that has never been PRESENT before. (Not "never seen":
        # a unit can be listed inactive for a sample before it is on the map, and E9a
        # run 1 lost four emus to that distinction.)
        for i, u in now_present.items():
            if i not in ever_present:
                arrived[i] = u; first_seen[i] = abs_tick
                summary["arrivals"] += 1
                out.event(ctx, tick, abs_tick, "arrival", i,
                          f"{u['species']} caste={u['caste']} ref6={u['ref6']} layer={u['layer']} countdown={u['countdown']} "
                          f"vanish={u['vanish']} flag_src={u['flag_src']} flag_nf={u['flag_nf']} pos={u['x']},{u['y']},{u['z']} "
                          f"listed_at={first_listed.get(i, abs_tick)}")
                out.row(ctx, tick, abs_tick, i, "arrival_species", u["species"])
                out.row(ctx, tick, abs_tick, i, "arrival_countdown", u["countdown"])
        wave_ids = [i for i, u in now_present.items() if i in arrived and first_seen.get(i) == abs_tick and u["layer"] == "surface"]
        if on_arrival and not on_arrival_done and len(wave_ids) >= on_arrival_min:
            subst = {"ids": " ".join(wave_ids), "ids_after1": " ".join(wave_ids[1:]), "ids_after2": " ".join(wave_ids[2:])}
            subst.update({f"id{k}": v for k, v in enumerate(wave_ids)})
            for m in on_arrival:
                try:
                    apply_manipulation(rig, out, ctx, tick, abs_tick, m.format(**subst))
                except KeyError as e:
                    out.log(f"  on_arrival skipped {m}: placeholder {e} not available with {len(wave_ids)} units")
            on_arrival_done = True
            on_arrival_at = stepped_total
            out.event(ctx, tick, abs_tick, "on_arrival_applied", "wave", " ".join(wave_ids))
        if every and every_next is not None and stepped_total >= every_next and every_count < int(every.get("max", 10**9)):
            for m in every.get("do", []):
                apply_manipulation(rig, out, ctx, tick, abs_tick, m)
            every_count += 1
            every_next = stepped_total + int(every["ticks"])
            out.event(ctx, tick, abs_tick, "every_applied", str(every_count), " ".join(every.get("do", [])))
        if not after_done and on_arrival_at is not None and stepped_total - on_arrival_at >= int(after.get("ticks", 0)):
            for m in after.get("do", []):
                apply_manipulation(rig, out, ctx, tick, abs_tick, m)
            after_done = True
            out.event(ctx, tick, abs_tick, "after_on_arrival_applied", "restore", str(len(after.get("do", []))))
        # departures and deaths: a unit that was present and is not now
        for i, u in present.items():
            if i not in now_present:
                rec = now.get(i)
                if first_exit is None and u["layer"] == "surface":
                    first_exit = stepped_total
                if rec and rec["dead"] == "1":
                    summary["deaths"] += 1; kind = "death"
                else:
                    summary["departures"] += 1; kind = "departure"
                out.event(ctx, tick, abs_tick, kind, i,
                          f"{u['species']} ref6={u['ref6']} last_countdown={u['countdown']} last_flag_src={u['flag_src']} "
                          f"arrived_at={first_seen.get(i, 'pre')}")
                out.row(ctx, tick, abs_tick, i, kind, u["species"])
        # per-unit countdown trace (long format), for every wild unit on the map
        for i, u in now_present.items():
            out.row(ctx, tick, abs_tick, i, "countdown", u["countdown"])
            out.row(ctx, tick, abs_tick, i, "flag_src", u["flag_src"])
        ever_present |= set(now_present.keys())
        present = now_present

        stats = {"ticks": stepped_total, "arrivals": summary["arrivals"], "departures": summary["departures"],
                 "arrived_present": sum(1 for i in arrived if i in present), "first_exit": first_exit,
                 "on_arrival_at": on_arrival_at}
        if control and control_met is None and stepped_total >= int(control.get("arrivals_within_ticks", 0)):
            control_met = summary["arrivals"] >= int(control.get("arrivals_min", 1))
            summary["control"] = "PASS" if control_met else "FAIL"
            out.event(ctx, tick, abs_tick, "control", "arrivals_within_ticks", f"{summary['control']} ({summary['arrivals']} arrivals by {stepped_total} ticks)")
            out.log(f"  control {summary['control']}: {summary['arrivals']} arrivals by tick +{stepped_total}")
        fired = stop_rule_fires(stop, stats)
        if stepped_total % (sample_every * 10) < sample_every:
            out.log(f"  +{stepped_total:>6} ticks | wild {len(present):>3} | arrivals {summary['arrivals']:>3} | departures {summary['departures']:>3} | deaths {summary['deaths']:>2} | {n / wall:.0f} t/s")
        out.flush()
        if fired:
            summary["stop"] = fired
            out.log(f"  stop rule: {fired}")
            break

    summary["ticks"] = stepped_total
    summary["wall_s"] = round(wall_total, 1)
    summary["ticks_per_s"] = round(stepped_total / wall_total, 1) if wall_total else None
    if control and summary["control"] is None:
        summary["control"] = "PASS" if summary["arrivals"] >= int(control.get("arrivals_min", 1)) else "FAIL"

    # 7. the whole pool again, then leave without saving; the folder must still equal the backup.
    try:
        pops_all1 = rig.probe("pops", "all")
        out.wide(out.pops_all, "_pops_all_head", ctx, tick, abs_tick, [dict(phase="end", **r) for r in pops_all1])
        before = {r["idx"]: r for r in pops_all0}
        for r in pops_all1:
            b0 = before.get(r["idx"])
            if b0 and (b0["quantity"], b0["quantity_max"], b0["discovered"], b0["extinct"]) != (r["quantity"], r["quantity_max"], r["discovered"], r["extinct"]):
                out.event(ctx, tick, abs_tick, "pool_delta", r["idx"],
                          f"{r['species']} ref6={r['ref6']} quantity {b0['quantity']}->{r['quantity']} max {b0['quantity_max']}->{r['quantity_max']} discovered {b0['discovered']}->{r['discovered']} extinct {b0['extinct']}->{r['extinct']}")
    except Exception as e:
        out.log(f"  end-of-replicate pool snapshot failed: {e}")
    rig.must("title")
    h_after = tree_hash(SAVE_ROOT / fort)
    summary["save_untouched"] = (h_after == h_backup)
    if not summary["save_untouched"]:
        summary["valid"] = False; summary["breaches"].append("save folder changed during the replicate")
        out.log("  BREACH: the save folder changed; the replicate wrote to disk")
    out.event(ctx, tick, abs_tick, "end", "summary", json.dumps(summary))
    out.log(f"  done: {json.dumps(summary)}")
    return summary


def cmd_run(a):
    man = json.loads(Path(a.manifest).read_text())
    if a.reps:
        for arm in man["arms"]:
            arm["replicates"] = a.reps
    if a.arm:
        man["arms"] = [x for x in man["arms"] if x["name"] in a.arm.split(",")]
        if not man["arms"]:
            sys.exit(f"no arm named {a.arm}")
    if a.budget:
        man["tick_budget"] = a.budget
        for arm in man["arms"]:
            arm.pop("tick_budget", None)
    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "data" / "experiments" / man["id"] / run_id
    out = Out(run_dir)
    (run_dir / "manifest.json").write_text(json.dumps(man, indent=2))
    rig = Rig(out.log)
    out.log(f"run {man['id']} {run_id}: {man.get('title', '')}")

    backup_dir = BACKUP_ROOT / man["backup"]
    if not backup_dir.is_dir():
        sys.exit(f"no backup {backup_dir}")
    prov = {
        "experiment": man["id"], "run": run_id, "fort": man["fort"], "backup": man["backup"],
        "backup_sha256": tree_hash(backup_dir),
        "dwarfcron_commit": git_head(ROOT), "seasonal_wildlife_commit": git_head(TOOL_REPO),
        "fps_cap": man.get("fps", 1000), "started": dt.datetime.now().isoformat(timespec="seconds"),
        "replicates": [],
    }
    rig.must("start", timeout=200)
    for arm in man["arms"]:
        for rep in range(1, int(arm.get("replicates", 1)) + 1):
            try:
                s = run_replicate(rig, out, man, arm, rep, run_id, prov)
            except Exception as e:  # a failed replicate is recorded and the run goes on
                s = {"arm": arm["name"], "rep": rep, "valid": False, "breaches": [f"exception: {e}"]}
                out.log(f"  REPLICATE FAILED: {e}")
                try:
                    if rig.state().get("map") == "true":
                        rig.must("title")
                except Exception as e2:
                    out.log(f"  could not get back to the title: {e2}; restarting the rig")
                    rig.sh("stop"); rig.port = None; rig.must("start", timeout=200)
            prov["replicates"].append(s)
            (run_dir / "provenance.json").write_text(json.dumps(prov, indent=2))
    # versions, read once at the end from a fresh load of the fort
    try:
        rig.must("load", man["fort"], timeout=400)
        prov["rig"] = rig.probe("provenance")[0]
        rig.must("title")
    except Exception as e:
        prov["rig"] = {"error": str(e)}
    prov["finished"] = dt.datetime.now().isoformat(timespec="seconds")
    (run_dir / "provenance.json").write_text(json.dumps(prov, indent=2))
    out.log(f"run complete -> {run_dir}")
    print(run_dir)
    cmd_report(argparse.Namespace(run_dir=str(run_dir)))


# ------------------------------------------------------------------ report --

def read_tsv(p: Path) -> list[dict]:
    if not p.exists() or p.stat().st_size == 0:
        return []
    lines = p.read_text().splitlines()
    head = lines[0].split("\t")
    return [dict(zip(head, l.split("\t"))) for l in lines[1:] if l.strip()]


def cmd_report(a):
    run_dir = Path(a.run_dir)
    man = json.loads((run_dir / "manifest.json").read_text())
    prov = json.loads((run_dir / "provenance.json").read_text()) if (run_dir / "provenance.json").exists() else {}
    events = read_tsv(run_dir / "events.tsv")
    rows = read_tsv(run_dir / "rows.tsv")
    print(f"\n# {man['id']} -- {man.get('title', '')}\nrun {run_dir.name} fort {man['fort']} backup {man['backup']}")
    rig = prov.get("rig", {})
    if rig:
        print(f"DF {rig.get('df_version')} DFHack {rig.get('dfhack_version')} world {rig.get('world')} site {rig.get('site_id')} tiles {rig.get('site_tiles')} seed {rig.get('seed')}")
    print(f"commits: DwarfCron {prov.get('dwarfcron_commit')} seasonal-wildlife {prov.get('seasonal_wildlife_commit')} fps cap {prov.get('fps_cap')}")
    if man.get("predictions"):
        print("\n## Predictions (written before the run)")
        for p in man["predictions"]:
            print(f"- {p['model']}: {p['expects']}")

    print("\n## Replicates")
    print("arm | rep | valid | control | ticks | t/s | arrivals | departures | deaths | stop | breaches")
    for s in prov.get("replicates", []):
        print(f"{s.get('arm')} | {s.get('rep')} | {s.get('valid')} | {s.get('control')} | {s.get('ticks', '')} | {s.get('ticks_per_s', '')} | "
              f"{s.get('arrivals', '')} | {s.get('departures', '')} | {s.get('deaths', '')} | {s.get('stop') or ''} | {'; '.join(s.get('breaches', []))}")

    # culling, fixed in advance: invalid replicates and arms whose control failed are dropped from the analysis
    valid = {(s["arm"], str(s["rep"])) for s in prov.get("replicates", []) if s.get("valid") and s.get("control") in (None, "PASS")}
    dropped = [(s["arm"], s["rep"]) for s in prov.get("replicates", []) if (s["arm"], str(s["rep"])) not in valid]
    if dropped:
        print(f"\nculled: {dropped}")

    # arrivals: group by (arm, rep, species, ref6, tick of first sighting)
    print("\n## Arrivals (new unit ids, attributed by the six-tuple they carry)")
    print("arm | rep | tick | species | ref6 | n | countdown at first sighting | departed at (rel ticks) | outcome")
    groups: dict[tuple, dict] = {}
    dep = {}
    for e in events:
        if e["event"] in ("departure", "death"):
            dep[(e["arm"], e["rep"], e["subject"])] = (e["event"], int(e["abs_tick"]))
    for e in events:
        if e["event"] != "arrival":
            continue
        d = dict(kv.split("=", 1) for kv in e["detail"].split() if "=" in kv)
        species = e["detail"].split()[0]
        key = (e["arm"], e["rep"], e["abs_tick"], species, d.get("ref6"))
        g = groups.setdefault(key, {"n": 0, "countdowns": [], "ids": [], "layer": d.get("layer", ""),
                                    "listed_at": d.get("listed_at", e["abs_tick"])})
        g["n"] += 1; g["countdowns"].append(d.get("countdown")); g["ids"].append(e["subject"])
    starts = {}
    for e in events:
        if e["event"] == "baseline":
            starts[(e["arm"], e["rep"])] = int(e["abs_tick"])
    for (arm, rep, abs_t, species, ref6), g in sorted(groups.items(), key=lambda kv: (kv[0][0], int(kv[0][1]), int(kv[0][2]))):
        t0 = starts.get((arm, rep), int(abs_t))
        outs = []
        rel = []
        for i in g["ids"]:
            if (arm, rep, i) in dep:
                kind, at = dep[(arm, rep, i)]
                outs.append(kind); rel.append(str(at - int(abs_t)))
            else:
                outs.append("present")
        cd = sorted(set(g["countdowns"]), key=lambda x: int(x) if x and x.lstrip('-').isdigit() else 0)
        mark = "" if (arm, rep) in valid else " (culled)"
        print(f"{arm} | {rep} | +{int(abs_t) - t0} | {species} | {ref6} | {g['n']} | {','.join(cd)} | {','.join(rel) or '-'} | {'/'.join(sorted(set(outs)))}{mark}")

    # waves.tsv: one row per wave, keyed on the tick the units were FIRST LISTED (stragglers that
    # became present a sample later are folded into the wave they were listed with), with layer,
    # size, countdown range and fate. This is the per-wave summary the report used to need awk for.
    waves: dict[tuple, dict] = {}
    for (arm, rep, abs_t, species, ref6), g in groups.items():
        wk = (arm, rep, g["listed_at"], species, ref6)
        w = waves.setdefault(wk, {"layer": g["layer"], "n": 0, "first_present": int(abs_t), "countdowns": [], "ids": []})
        w["n"] += g["n"]; w["countdowns"] += [int(c) for c in g["countdowns"] if c and c.lstrip('-').isdigit()]
        w["ids"] += g["ids"]; w["first_present"] = min(w["first_present"], int(abs_t))
    with open(run_dir / "waves.tsv", "w") as fh:
        fh.write("arm\trep\tlisted_rel\tfirst_present_rel\tspecies\tref6\tlayer\tn\tcountdown_min\tcountdown_max\tdeparted\tdied\tpresent\tdeparted_rel_min\tdeparted_rel_max\tvalid\n")
        for (arm, rep, listed, species, ref6), w in sorted(waves.items(), key=lambda kv: (kv[0][0], int(kv[0][1]), int(kv[0][2]))):
            t0 = starts.get((arm, rep), int(listed))
            fates = [dep.get((arm, rep, i)) for i in w["ids"]]
            deps = [at - int(listed) for f in fates if f and f[0] == "departure" for at in [f[1]]]
            died = sum(1 for f in fates if f and f[0] == "death")
            fh.write("\t".join(str(x) for x in [
                arm, rep, int(listed) - t0, w["first_present"] - t0, species, ref6, w["layer"], w["n"],
                min(w["countdowns"]) if w["countdowns"] else "", max(w["countdowns"]) if w["countdowns"] else "",
                len(deps), died, w["n"] - len(deps) - died,
                min(deps) if deps else "", max(deps) if deps else "", (arm, rep) in valid]) + "\n")
    print(f"\n## Waves ({len(waves)}; per-wave summary written to waves.tsv, keyed on first-listed tick)")
    print("arm | rep | listed | species | layer | n | departed | died | present")
    for (arm, rep, listed, species, ref6), w in sorted(waves.items(), key=lambda kv: (kv[0][0], int(kv[0][1]), int(kv[0][2]))):
        t0 = starts.get((arm, rep), int(listed))
        fates = [dep.get((arm, rep, i)) for i in w["ids"]]
        nd = sum(1 for f in fates if f and f[0] == "departure"); nk = sum(1 for f in fates if f and f[0] == "death")
        print(f"{arm} | {rep} | +{int(listed) - t0} | {species} | {w['layer']} | {w['n']} | {nd} | {nk} | {w['n'] - nd - nk}")

    # countdown slope: for arrived units, first and last countdown reading with ticks between
    print("\n## Countdown behaviour per arrived unit (first reading -> last reading over ticks)")
    trace: dict[tuple, list] = {}
    for r in rows:
        if r["metric"] == "countdown":
            trace.setdefault((r["arm"], r["rep"], r["subject"]), []).append((int(r["abs_tick"]), int(r["value"])))
    printed = 0
    for key, g in groups.items():
        arm, rep, abs_t, species, ref6 = key
        for i in g["ids"][:2]:      # two per group is enough to show the slope
            tr = trace.get((arm, rep, i))
            if not tr or len(tr) < 2:
                continue
            (ta, ca), (tb, cb) = tr[0], tr[-1]
            slope = (cb - ca) / (tb - ta) if tb != ta else 0
            print(f"{arm} | {rep} | unit {i} {species}: {ca} -> {cb} over {tb - ta} ticks (slope {slope:+.3f}/tick)")
            printed += 1
            if printed > 40:
                break
    pops = read_tsv(run_dir / "pops.tsv")
    if pops:
        print("\n## Entry quantity around each departure or death (sample before -> sample of the event -> next sample)")
        print("arm | rep | event | unit | species | ref6 | quantity before -> at -> after")
        byrep: dict[tuple, dict] = {}
        for r in pops:
            byrep.setdefault((r["arm"], r["rep"], r["ref6"]), {})[int(r["abs_tick"])] = r["quantity"]
        for e in events:
            if e["event"] not in ("departure", "death"):
                continue
            d = dict(kv.split("=", 1) for kv in e["detail"].split() if "=" in kv)
            series = byrep.get((e["arm"], e["rep"], d.get("ref6")), {})
            ticks = sorted(series)
            t = int(e["abs_tick"])
            before = [x for x in ticks if x < t]; after = [x for x in ticks if x > t]
            q = lambda x: series[x] if x is not None else "-"
            print(f"{e['arm']} | {e['rep']} | {e['event']} | {e['subject']} | {e['detail'].split()[0]} | {d.get('ref6')} | "
                  f"{q(before[-1] if before else None)} -> {q(t) if t in series else '-'} -> {q(after[0] if after else None)}")
    manips = [e for e in events if e["event"] in ("manipulation", "on_arrival_applied")]
    if manips:
        print("\n## Manipulations applied")
        for e in manips:
            print(f"{e['arm']} | {e['rep']} | +{int(e['abs_tick']) - starts.get((e['arm'], e['rep']), int(e['abs_tick']))} | {e['subject']} | {e['detail']}")
    deltas = [e for e in events if e["event"] == "pool_delta"]
    print(f"\n## Pool entries that changed between load and end of replicate ({len(deltas)}; the second instrument)")
    for e in deltas:
        print(f"{e['arm']} | {e['rep']} | idx {e['subject']} | {e['detail']}")
    pres = [e for e in events if e["event"] == "present_at_start"]
    if pres:
        print(f"\n## Units present at load (held group from the save), {len(pres)} rows; first few:")
        for e in pres[:8]:
            print(f"{e['arm']} | {e['rep']} | {e['subject']} | {e['detail']}")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("manifest"); r.add_argument("--reps", type=int); r.add_argument("--arm"); r.add_argument("--budget", type=int)
    r.set_defaults(fn=cmd_run)
    p = sub.add_parser("report"); p.add_argument("run_dir"); p.set_defaults(fn=cmd_report)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
