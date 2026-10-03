# web2 live run 20261002-192002 (live)

22 PASS/NT, 0 FAIL

| row | verdict | evidence |
|---|---|---|
| build.luac53 | PASS | luac53 -p on the web, controls and engine scripts: OK |
| deploy | PASS | web2 web files copied into /Users/nathanielcannon/Library/Application Support/CrossOver/Bottles/Win10/drive_c/Program Files (x86)/Steam/steamapps/common/Dwarf Fortress/dfhack-config/scripts (byte-identical True); engine and controls already deployed: True |
| session.load | PASS | screen=viewscreen_dwarfmodest focus=dwarfmode/Default world=true map=true paused=true modal=false year=100 tick=53745 season=0 units=120 |
| session.start | PASS | serving the companion at http://127.0.0.1:8642/?t=01c143ca5ddf55218e36  (copied to the clipboard)  [tiles: 963 creatures, 343 sheets, read in 148 ms] |
| session.build | PASS | fort RinghatchetsReady; 53.16-r2	v0.53.16 win64 STEAM	RinghatchetsReady; tool /Users/nathanielcannon/Claude/Projects/sw-wt/web2/scripts |
| live.date_advances | PASS | abs_day 33644.791666667 -> 33689.5425 over 229 state reads |
| live.units_move | PASS | 338 of 386 consecutive map reads saw a unit move; groups on the map ranged 0-73 |
| live.seq_moves | PASS | history seq [1] -> [427]; ledger count [5] -> [295] |
| live.not_modified | PASS | 9 304 answer(s) to If-None-Match in the 20 s paused window |
| live.budget.state | PASS | 293 reads; server ms p50 0 p95 17 max 42 (budget 50); wall ms p50 45.9 p95 125.4 max 882.6; first {'code': 200, 'wall': 882.6, 'srv': 32, 'bytes': 206829, 't': 1790990464.6338902} |
| live.budget.map | PASS | 387 reads; server ms p50 0 p95 1 max 27 (budget 50); wall ms p50 45.7 p95 89.0 max 200.8; first {'code': 200, 'wall': 123.3, 'srv': 27, 'bytes': 39981, 't': 1790990464.757324} |
| live.budget.events | PASS | 148 reads; server ms p50 0 p95 0 max 0 (budget 50); wall ms p50 34.6 p95 62.9 max 102.4; first {'code': 200, 'wall': 59.0, 'srv': 0, 'bytes': 1314, 't': 1790990464.816345} |
| live.budget.history | PASS | 41 reads; server ms p50 0 p95 0 max 0 (budget 50); wall ms p50 26.5 p95 83.1 max 106.3; first {'code': 200, 'wall': 30.0, 'srv': 0, 'bytes': 620, 't': 1790990464.846425} |
| live.budget.web | PASS | 41 reads; server ms p50 0 p95 41 max 41 (budget 50); wall ms p50 67.9 p95 96.4 max 186.7; first {'code': 200, 'wall': 186.7, 'srv': 0, 'bytes': 86, 't': 1790990465.033149} |
| live.budget.waters | PASS | 120 reads; server ms p50 0 p95 0 max 1 (budget 50); wall ms p50 42.8 p95 66.8 max 229.5; first {'code': 200, 'wall': 202.3, 'srv': 0, 'bytes': 4860, 't': 1790990465.2355142} |
| live.budget.status | PASS | 120 reads; server ms p50 0 p95 0 max 0 (budget 50); wall ms p50 55.3 p95 81.7 max 138.3; first {'code': 200, 'wall': 28.4, 'srv': 0, 'bytes': 4976, 't': 1790990465.263933} |
| live.no_5xx | PASS | 1150 reads; failures [] |
| live.terrain | PASS | done True, 96x96 cells (stride 4), z 55-66, 22611 reads in 66 ms; unknown cells 0 of 9216 |
| browser.errors | PASS | console errors [];  |
| browser.live | PASS | pill at t1 'Liveupdated <1 s ago', fort Ringhatchets, release 7.1.0, DFHack 53.16-r2, offline banner False, 304s seen by the page 8 |
| browser.moved | PASS | 37 of 44 markers moved between t0 and t1 (300 s); date 33647.708333333 -> 33671.9925; history seq 69 -> 255 |
| live.server_status | PASS | serving http://127.0.0.1:8642/?t=01c143ca5ddf55218e36  requests 1794 (commands 0, sets 0, refused 22, errors 0, dropped silent/slow clients 1, deferred to the next poll 252); poll last 4 ms, worst 108 ms; slowest request 98 ms (GET /state.json?t=TOKEN); snapshot last 0 ms, worst 42 ms [pool 36, census 0, gfx 0, species 6, rest 0 ms]; status last 9 ms, worst 9 ms; static species fields 15 ms in all |

Screens: screens/t0, screens/t1. Fixtures for `FIXTURE=/Users/nathanielcannon/Claude/Projects/DwarfCron/data/web2-live/20261002-192002/fixtures python3 tests/web/mock_server.py`.
