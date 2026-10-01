"""Pure helpers for the ECO harness (eco-run.py, v7.1 harness pass, 1 Oct 2026). No rig I/O here, so every rule the
runner applies can be unit-tested offline (tests/harness/test_ecolib.py).

  arm_order       H1: the order a rep runs its cells in (counterbalanced by default)
  parse_check     H2: 'kind[k=v].key OP value' -> a check
  eval_check      H2: a check against the 'eco ...' rows a cell has printed so far
  auto_failures   H2: the checks every verb gets without asking (a spawn that placed 0, a relation written to no pair...)
  bouts           H6: attacks with gaps under `gap` ticks, per attacker
  with_roam       H4: a spawn step with DF's roaming flag kept (the 11th cx-eco spawn argument)
  scale_step      R12: shorter reps, every step:N scaled
  estimate        R12: a block's wall time, for `eco-run.py plan`
"""
from __future__ import annotations

import re

# ------------------------------------------------------------------------------------------------ H1: arm order --
ORDERS = ("counterbalance", "rotate", "fixed")


def arm_order(names: list[str], rep: int, mode: str = "counterbalance") -> list[str]:
    """counterbalance: odd reps in the written order, even reps reversed (Part 1 plan H1: 'order reversed in rep 2');
    rotate: rep r starts at cell (r-1) mod n, a Latin-square row, so with n reps = n cells every cell holds every
    position once; fixed: always the written order (the pre-v7.1 behaviour)."""
    names = list(names)
    if mode == "fixed" or len(names) < 2:
        return names
    if mode == "counterbalance":
        return names[::-1] if rep % 2 == 0 else names
    if mode == "rotate":
        k = (rep - 1) % len(names)
        return names[k:] + names[:k]
    raise ValueError(f"unknown order {mode!r}; one of {ORDERS}")


# --------------------------------------------------------------------------------------- H2: manipulation check --
CHECK = re.compile(r"^(?P<kind>\w+)(?:\[(?P<flt>[^\]]*)\])?\.(?P<key>\w+)\s*(?P<op>==|!=|>=|<=|>|<)\s*(?P<val>\S+)$")


class ManipFail(RuntimeError):
    """The dial's internal state did not change (or the subject never arrived): the block's outcomes would be vacuous."""


def parse_check(spec: str) -> dict:
    m = CHECK.match(spec.strip())
    if not m:
        raise ValueError(f"bad check {spec!r}: want kind[k=v,...].key OP value, OP one of == != >= <= > <")
    flt = {}
    if m.group("flt"):
        for part in m.group("flt").split(","):
            k, _, v = part.partition("=")
            flt[k.strip()] = v.strip()
    return dict(kind=m.group("kind"), flt=flt, key=m.group("key"), op=m.group("op"), val=m.group("val"), spec=spec.strip())


def kv(line: str) -> dict:
    """'eco kind k=v k=v' -> {k: v}."""
    return dict(t.split("=", 1) for t in line.split()[2:] if "=" in t)


def _num(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower()
    if s in ("true", "false"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _cmp(a, op, b) -> bool:
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None:
        a, b = na, nb
    else:
        a, b = str(a).lower(), str(b).lower()
        if op not in ("==", "!="):
            return False
    return {"==": a == b, "!=": a != b, ">=": a >= b, "<=": a <= b, ">": a > b, "<": a < b}[op]


def eval_check(chk: dict, rows: list[str]) -> tuple[bool, str]:
    """The LATEST row of the check's kind that matches its filter decides. No such row fails: a receipt that was
    never printed proves nothing."""
    cand = [l for l in rows if l.startswith(f"eco {chk['kind']} ") or l == f"eco {chk['kind']}"]
    cand = [l for l in cand if all(kv(l).get(k) == v for k, v in chk["flt"].items())]
    if not cand:
        return False, f"{chk['spec']}: no '{chk['kind']}' receipt" + (f" matching {chk['flt']}" if chk["flt"] else "")
    got = kv(cand[-1]).get(chk["key"])
    if got is None:
        return False, f"{chk['spec']}: the receipt has no '{chk['key']}' ({cand[-1][:120]})"
    ok = _cmp(got, chk["op"], chk["val"])
    return ok, f"{chk['spec']}: got {chk['key']}={got}"


# A count of 0 in these receipts means the manipulation reached nothing (manifest-subject-receipt; three blocks ran
# vacuously before it). kind -> (key, op, value, guard), guard(row) True when the check applies to that row.
AUTO = {
    "spawn": ("placed", ">", "0", None),
    "rel": ("pairs", ">", "0", None),
    "relfort": ("pairs", ">", "0", None),
    # 'lowest' always names a leader when there are members; 'largest-male' rightly names none without a male (R32)
    "lead": ("leader", ">=", "0", lambda d: d.get("how") == "lowest" and d.get("members", "0") != "0"),
    "adopt": ("adopted", "==", "1", None),
    "sneak": ("units", ">", "0", None),
    "skills": ("units", ">", "0", None),
    "sw7apply": ("applied", ">", "0", None),
    "swreceipt": ("present", ">", "0", None),
    "wipecheck": ("remaining", "==", "0", None),
}


# Receipts written FIRST in a cell's TSV rows (H2: "a manipulation-check receipt printed first"): the AUTO kinds plus
# the read-backs that carry a dial's value.
RECEIPTS = set(AUTO) | {"wipe", "cfg", "skill", "relcount", "ecostate", "flag", "misc", "swv7", "swlimits", "manip"}


def auto_failures(rows: list[str]) -> list[str]:
    """Every AUTO receipt among `rows` that shows the manipulation reached nothing."""
    bad = []
    for l in rows:
        p = l.split()
        if len(p) < 2 or p[0] != "eco" or p[1] not in AUTO:
            continue
        key, op, val, guard = AUTO[p[1]]
        d = kv(l)
        if guard and not guard(d):
            continue
        if key not in d or not _cmp(d[key], op, val):
            bad.append(f"auto {p[1]}.{key}{op}{val}: {l[:160]}")
    return bad


# ------------------------------------------------------------------------------------------------- H6: bouts --
def bouts(times: list[int], gap: int = 100) -> int:
    """Attacks whose gap to the previous one is under `gap` ticks belong to one bout (an engagement)."""
    ts = sorted(times)
    return sum(1 for i, t in enumerate(ts) if i == 0 or t - ts[i - 1] >= gap)


def bouts_from_rows(rows: list[str], gap: int = 100) -> dict:
    """Offline re-count from a TSV's 'atk' rows (cx-eco read): {attacker id: (token, attacks, bouts)}."""
    per: dict[str, list] = {}
    for l in rows:
        if not l.startswith("eco atk "):
            continue
        d = kv(l)
        per.setdefault(d["a"], [d.get("atok", "?"), []])[1].append(int(d["t"]))
    return {a: (tok, len(ts), bouts(ts, gap)) for a, (tok, ts) in per.items()}


# --------------------------------------------------------------------------------------- H4: placement isolation --
SPAWN_DEFAULTS = ["3", "land", "any", "200000"]   # radius, medium, sex, countdown (cx-eco spawn's defaults)
SPAWN_OPTS = ("roam", "legacy", "slot=", "ref=", "debit=")


def spawn_opts(step: str, *opts: str) -> str:
    """'spawn T N X Y Z [r] [medium] [sex] [countdown] [opts...]' with `opts` added after the ten positionals (the
    missing positionals filled with cx-eco's own defaults, so the options land in place). Options already present
    are kept; an option given again is not duplicated."""
    p = step.split()
    if len(p) < 6 or p[0] != "spawn":
        return step
    pos, extra = p[6:], []
    while pos and pos[-1].startswith(SPAWN_OPTS):
        extra.insert(0, pos.pop())
    pos = pos + SPAWN_DEFAULTS[len(pos):]
    for o in opts:
        key = o.split("=")[0] + ("=" if "=" in o else "")
        extra = [e for e in extra if not (e == o or (key.endswith("=") and e.startswith(key)))] + [o]
    return " ".join(p[:6] + pos[:4] + extra)


def with_roam(step: str) -> str:
    """H4: DF keeps the placed units wild, so it does not aim them at newcomers as fort-side units (Part 1 plan 0.3)."""
    return spawn_opts(step, "roam")


# ------------------------------------------------------------------------------------------------ R12: short reps --
def scale_step(step: str, scale: float) -> str:
    if scale == 1.0 or not step.startswith("step:"):
        return step
    return f"step:{max(1, int(round(int(step[5:]) * scale)))}"


def cell_ticks(cell: dict, scale: float = 1.0) -> int:
    n = sum(int(s[5:]) for s in cell.get("steps", []) if isinstance(s, str) and s.startswith("step:"))
    return int(round((n + int(cell.get("ticks", 0))) * scale))


def estimate(block: dict, reps: int, load: str = "arm", tps: float = 450.0, load_s: float = 150.0,
             rpc_s: float = 2.5, scale: float = 1.0, wipe: bool = True) -> dict:
    """Wall-time estimate: ticks / tps, plus one fresh DF + load per arm (or per rep), plus ~rpc_s per verb."""
    cells = block["cells"]
    ticks = sum(cell_ticks(c, scale) for c in cells.values())
    verbs = sum(len(c.get("steps", [])) + len(c.get("post", [])) + 6 + (4 if wipe else 0) for c in cells.values())
    loads = len(cells) if load == "arm" else 1
    per_rep = ticks / tps + loads * load_s + verbs * rpc_s
    return dict(cells=len(cells), reps=reps, ticks_per_rep=ticks, loads=loads * reps, verbs_per_rep=verbs,
                minutes=round(per_rep * reps / 60, 1))
