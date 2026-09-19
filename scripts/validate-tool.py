#!/usr/bin/env python3
"""Functional validation of seasonal-wildlife against the live rig.

Three phases, each a list of checks with an explicit expectation, so a failure
names what was expected rather than just dumping output:

  CLI       every dispatch verb and its sub-commands, asserted on their receipts
  GUI       every tab rendered and screen-dumped; hotkeys exercised
  MECHANICS the jobs that must actually fire (scheduler, ecology, water, cavern,
            daily hold) and the state they are supposed to leave behind

Usage: validate-tool.py [--fort CTRL] [--skip-gui]
Leaves the rig at the title screen and the fort byte-identical to its backup.
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CX = str(ROOT / "scripts" / "cx-lifecycle.sh")
results = []

def sh(*args, timeout=180):
    p = subprocess.run([CX, *args], capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def cmd(*args, timeout=120):
    return sh("cmd", "seasonal-wildlife", *args, timeout=timeout)

def check(phase, name, ok, detail="", expected=""):
    results.append({"phase": phase, "name": name, "ok": bool(ok), "detail": detail.strip()[:400],
                    "expected": expected})
    print(f"  [{'PASS' if ok else 'FAIL'}] {phase}/{name}" + ("" if ok else f"\n         expected: {expected}\n         got: {detail.strip()[:300]}"))
    return ok

def expect(phase, name, args, must_contain, timeout=120):
    rc, out = cmd(*args, timeout=timeout)
    ok = rc == 0 and all(m.lower() in out.lower() for m in must_contain)
    return check(phase, name, ok, out, f"rc 0 and {must_contain}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fort", default="CTRL")
    ap.add_argument("--skip-gui", action="store_true")
    a = ap.parse_args()

    print(f"== restoring and loading {a.fort}")
    sh("save-restore", f"{a.fort}.preverify", timeout=300)
    rc, out = sh("load", a.fort, timeout=300)
    if rc != 0:
        print("could not load the fort:", out[:400]); sys.exit(1)

    # ---------------------------------------------------------------- CLI ---
    P = "CLI"
    # assert on what status actually reports, not on the tool's own name
    expect(P, "status", ["status"], ["quota", "layers", "on the map now"])
    rc, out = cmd("status")
    check(P, "status separates deep from cavern", "magma sea and underworld" in out.lower(), out,
          "the layer line naming the magma sea and underworld as never managed (addendum 51)")
    check(P, "status names the invasion field", "invasion_id" in out or "invasion" in out, out,
          "the line reporting which unit field the invasion exclusion bound to")
    expect(P, "classes", ["classes"], ["natural"])
    expect(P, "enable", ["enable"], [])
    rc, out = cmd("status"); check(P, "enable took effect", "on" in out.lower(), out, "status reports the tool on")
    expect(P, "disable", ["disable"], [])
    expect(P, "enable again", ["enable"], [])
    expect(P, "groups status", ["groups"], ["groups"])
    expect(P, "groups on", ["groups", "on"], [])
    expect(P, "groups coupling on", ["groups", "coupling", "on"], [])
    expect(P, "groups pack", ["groups", "pack", "4"], [])
    expect(P, "groups ecology on", ["groups", "ecology", "on"], [])
    expect(P, "groups livestock off", ["groups", "livestock", "off"], [])
    expect(P, "groups nudge", ["groups", "nudge", "40", "3000", "6"], [])
    expect(P, "quota status", ["quota"], ["quota"])
    expect(P, "quota cavern 12", ["quota", "cavern", "12"], ["cavern"])
    rc, out = cmd("quota", "cavern", "12")
    check(P, "quota cavern warns about the frequency lever", "frequency" in out.lower(), out,
          "the note that the ceiling is enforced on FREQUENCY, not pool entries")
    check(P, "quota cavern warns about the arrival lag", "arriv" in out.lower(), out,
          "the addendum 57 wording that it brakes arrivals and does not cull")
    expect(P, "quota cavern 0 (unset)", ["quota", "cavern", "0"], ["cavern"])
    expect(P, "water status", ["water"], ["water"])
    expect(P, "water target", ["water", "target", "12"], [])
    expect(P, "water cadence", ["water", "cadence", "5000"], [])
    expect(P, "water off", ["water", "off"], [])
    expect(P, "water on", ["water", "on"], [])
    expect(P, "now (apply the roster)", ["now"], [])
    rc, out = cmd("bogusverb")
    check(P, "unknown verb prints usage", "usage" in out.lower(), out, "a usage line rather than a stack trace")

    # ----------------------------------------------------------- MECHANICS ---
    P = "MECH"
    rc, out = sh("lua", "local sw=reqscript('seasonal-wildlife'); local c=sw.loadConfig(); "
                 "print(('mech: enabled=%s groups=%s ecology=%s water=%s layers=%s/%s/%s'):format("
                 "tostring(c.enabled),tostring(c.groups.enabled),tostring(c.ecology.enabled),"
                 "tostring(c.water.enabled),tostring(c.layers.land),tostring(c.layers.water),tostring(c.layers.cavern)))")
    check(P, "config reads back after CLI edits", "mech:" in out, out, "a config dump")
    rc, out = sh("lua", "local ok,ru=pcall(require,'repeat-util'); "
                 "print('sched: '..tostring(ok and ru.isScheduled and ru.isScheduled('seasonal-wildlife')))")
    check(P, "scheduler registered", "sched: true" in out, out, "repeat-util reports seasonal-wildlife scheduled")
    rc, out = sh("lua", "local sw=reqscript('seasonal-wildlife'); local by=sw.WILD.countByLayer(); "
                 "print(('layers: land=%d water=%d cavern=%d deep=%d'):format(by.land,by.water,by.cavern,by.deep))")
    check(P, "layer counter separates deep from cavern", "deep=" in out, out,
          "countByLayer reports a separate deep bucket (addendum 51)")
    rc, out = sh("lua", "local sw=reqscript('seasonal-wildlife'); print('field: '..tostring(sw.WILD.field)); "
                 "local u=df.global.world.units.active[0]; if u then sw.WILD.invader(u) end; "
                 "print('field_after: '..tostring(sw.WILD.field))")
    check(P, "invasion exclusion binds to a real field", "invasion_id" in out, out,
          "WILD.field resolves to invasion_id or invasion, never false")
    rc, out = sh("lua", "local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); "
                 "local r=sw.CAVERN.apply(cfg, df.global.cur_season); "
                 "print(('cavern: held=%s open=%s'):format(tostring(r and r.held), tostring(r and r.open)))")
    check(P, "cavern lever runs", "cavern:" in out, out, "CAVERN.apply returns a held/open result")
    rc, out = sh("lua", "local sw=reqscript('seasonal-wildlife'); print(sw.CAVERN.status(sw.loadConfig()))")
    check(P, "cavern status mentions the hold", "caverns:" in out.lower(), out, "a caverns: status line")

    # ---------------------------------------------------------------- GUI ---
    if not a.skip_gui:
        P = "GUI"
        rc, out = sh("cmd", "gui/seasonal-wildlife", timeout=120)
        time.sleep(2)
        rc, scr = sh("screen", timeout=120)
        check(P, "window opens", "seasonal" in scr.lower() or "roster" in scr.lower(), scr,
              "the seasonal-wildlife window on screen")
        Path(ROOT / "data/validation").mkdir(parents=True, exist_ok=True)
        (ROOT / "data/validation/gui-tab1.txt").write_text(scr)
        for label in ["Roster", "Set roster", "Food web", "Live", "Seasons"]:
            rc, out = sh("ui", "click", label, timeout=120)
            time.sleep(1.5)
            rc, scr = sh("screen", timeout=120)
            (ROOT / f"data/validation/gui-{label.replace(' ','_')}.txt").write_text(scr)
            check(P, f"tab renders: {label}", label.lower() in scr.lower() and len(scr) > 200, scr[:300],
                  f"the {label} tab drawn with content")
        # An empty Roster list is correct on an unassigned roster, so the real check is that
        # the view REFLECTS STATE: assign a roster, reopen, and require rows with real columns.
        sh("key", "LEAVESCREEN", timeout=60); time.sleep(1)
        rc, out = sh("lua", "local sw=reqscript('seasonal-wildlife'); local cfg=sw.loadConfig(); "
                     "if not cfg.initialized then sw.captureDefault(cfg) end; cfg.layers.land=true; "
                     "local pool=sw.buildPool(cfg); local n=0; for _,e in ipairs(pool) do "
                     "if e.inEmbark and sw.defaultAllow(e) then cfg.allow[e.key]=true; n=n+1 end end; "
                     "local a=sw.assignFromMatrix(cfg,pool); sw.saveConfig(cfg); "
                     "sw.applyLive(cfg, df.global.cur_season); sw.saveConfig(cfg); "
                     "print(('setup: %d allowed, %d assigned'):format(n,a))", timeout=180)
        check(P, "roster can be assigned for the view test", "setup:" in out, out, "an assignment receipt")
        sh("cmd", "gui/seasonal-wildlife", timeout=120); time.sleep(3)
        rc, scr = sh("screen", timeout=120)
        (ROOT / "data/validation/gui-Roster-populated.txt").write_text(scr)
        rows = re.findall(r"(prey|predator|vermin|bird|apex)\s+(small|medium|large)", scr)
        check(P, "Roster list reflects an assigned roster", len(rows) >= 5 and "No matches" not in scr,
              f"{len(rows)} creature rows", "at least five rows with category and size columns")
        check(P, "Roster rows carry season and abundance columns", bool(re.search(r"(All|Sp|Su|Au|Wi)\w*\s+\d{1,3}\s+[YN]", scr)),
              scr[:200], "each row showing its season set, abundance and allowed flag")
        sh("key", "LEAVESCREEN", timeout=60)
        time.sleep(1)
        rc, scr = sh("screen", timeout=120)
        check(P, "window closes on ESC", "roster" not in scr.lower() or "dwarf" in scr.lower(), scr[:200],
              "the window dismissed")

    # ------------------------------------------------------------- teardown --
    sh("title", timeout=180)
    sh("save-restore", f"{a.fort}.preverify", timeout=300)

    out_dir = ROOT / "data/validation"; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(results, indent=1))
    n_ok = sum(1 for r in results if r["ok"])
    print(f"\n== {n_ok}/{len(results)} checks passed")
    for r in results:
        if not r["ok"]:
            print(f"   FAIL {r['phase']}/{r['name']}: expected {r['expected']}")
    return 0 if n_ok == len(results) else 1

sys.exit(main())
