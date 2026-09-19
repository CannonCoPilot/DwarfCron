"""Shared guard for the experiment tallies.

`events.tsv` is written incrementally while a replicate steps, so reading it mid-run yields a
replicate that looks finished and is not. On 18 September an E24 tally taken four minutes early
read `qty_20` rep 2 at 16 arrivals in 1 wave when it finished at 35 in 6, and the arm mean went
into a STATE.md addendum wrong (the conclusion survived; the method did not). A replicate is only
complete when the harness has written its `done:` line, so that is what these tallies check.
"""
import json, os, re

DONE = re.compile(r"done: (\{.*\})")
ARMREP = re.compile(r"== \S+ arm=(\S+) rep=(\d+)")


def completed_reps(run_dir):
    """The (arm, rep) keys the harness has reported `done:` for."""
    done, arm, rep = set(), None, None
    path = os.path.join(run_dir, "log.txt")
    if not os.path.exists(path):
        return None                      # no log: caller should not filter
    for line in open(path, errors="replace"):
        m = ARMREP.search(line)
        if m:
            arm, rep = m.group(1), int(m.group(2))
        m = DONE.search(line)
        if m:
            try:
                d = json.loads(m.group(1))
            except ValueError:
                d = {}
            done.add((d.get("arm", arm), int(d.get("rep", rep or 0))))
    return done


def drop_incomplete(run_dir, *dicts):
    """Remove every (arm, rep) key that has not reported done, loudly. Returns the dropped keys."""
    done = completed_reps(run_dir)
    if done is None:
        return set()
    keys = set()
    for d in dicts:
        keys |= set(d)
    stale = {k for k in keys if k not in done}
    if stale:
        print("!! EXCLUDED — still running, no `done:` line yet: "
              + ", ".join(f"{a} rep {r}" for a, r in sorted(stale)))
        print("!! re-run this tally when the replicate finishes; a partial arm must not be averaged.\n")
        for d in dicts:
            for k in stale:
                d.pop(k, None)
    return stale
