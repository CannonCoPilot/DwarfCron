"""End-to-end validation test suite for the Chronicler data pipeline.

Tests data completeness, query resolution, and response quality across
all layers: extraction → DB storage → context retrieval → LLM response.

Ground truth is derived from Dwarf Fortress screenshots taken at Likotkon
fortress on 2026-02-23 (year 200, world "Thadar En", world_id=8).

Ground Truth Summary:
- 18 citizen dwarves (visible in Citizens tab)
- Vabok Solonotin = expedition leader, 19yo female, skills: Organizer, Carpenter, Herbalist, Fisherdwarf
- 3 visiting bards: Doren Bomrekmatzang, Ducin Lolokgan, Dishnab Logenneng
- Dead/Missing: 1 Dingo (deceased), 1 Raven (deceased)
- Cerol Aludsibrek, Peasant has been found dead, drowned
- 11 pets/livestock: 2 dogs, 2 cats, 1 llama, 1 turkey gobbler, 1 yak bull, 1 yak cow, 1 lamb, 1 baby llama, 1 camel calf
"""

import asyncio
import json
import sys
from dataclasses import dataclass, field
from typing import Any

import asyncpg

# DB connection string (from chronicler.config)
DB_DSN = "postgresql://jarvis:OSDbeydP6TOBGoJUym6rTBfULKJYqqPE@localhost:5432/chronicler"
WORLD_ID = 8  # "Thadar En" — The Planet of Legends

# ---------------------------------------------------------------------------
# Ground truth from screenshots
# ---------------------------------------------------------------------------

GROUND_TRUTH_CITIZENS = [
    # (name_fragment, profession_if_known)
    # Names use DF diacriticals (ô, ä, ê, ó, ù, î)
    ("Unib Lolordodók", "Miner"),
    ("Stinthäd Nitigmeng", "Miner"),
    ("Rimtar Ledanan", "Carpenter"),
    ("Onget Inenkikrost", "Mason"),
    ("Fikod Aknûnmûthkat", "Planter"),
    ("Vabôk Solonotin", "Expedition Leader"),
    ("Feb Nishkêshshak", "Peasant"),
    ("Urdim Logemgósmer", "Peasant"),
    ("Doren Momuzsodel", "Peasant"),
    ("Aban Ibeshbomrek", "Peasant"),
    ("Erush Etarcerol", "Peasant"),
    ("Zon Berotsus", "Peasant"),
    ("Deduk Arelzon", "Peasant"),
    ("Ast Dodókùst", "Peasant"),
    ("Inod Adakrul", "Peasant"),
    ("Litast Stizashonol", "Peasant"),
    ("Cerol Aludsibrek", "Peasant"),
    ("Mistêm Nishtusung", "Peasant"),
]

GROUND_TRUTH_BARDS = [
    # name, currently visiting
    ("Doren Bomrekmâtzang", True),
    ("Ducin Lolokgan", True),
    ("Dîshmab Logemmeng", True),
]

GROUND_TRUTH_DEATHS = [
    # (description, type)
    ("Dingo", "animal_deceased"),
    ("Raven", "animal_deceased"),
    ("Cerol Aludsibrek", "dwarf_drowned"),
]

GROUND_TRUTH_LIVESTOCK = [
    # (race, count)
    ("DOG", 2),
    ("CAT", 2),
    ("LLAMA", 1),
    ("BIRD_TURKEY", 1),
    # yaks, lamb, baby llama, camel calf also visible
]


# ---------------------------------------------------------------------------
# Test result tracking
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    severity: str = "INFO"  # INFO, WARNING, GAP, CRITICAL

@dataclass
class ValidationReport:
    results: list[TestResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str, severity: str = "INFO"):
        self.results.append(TestResult(name, passed, message, severity))

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def gaps(self) -> list[TestResult]:
        return [r for r in self.results if not r.passed and r.severity in ("GAP", "CRITICAL")]

    def print_report(self):
        print("\n" + "=" * 72)
        print("CHRONICLER VALIDATION REPORT")
        print("=" * 72)

        sections: dict[str, list[TestResult]] = {}
        for r in self.results:
            section = r.name.split(":")[0] if ":" in r.name else "General"
            sections.setdefault(section, []).append(r)

        for section, tests in sections.items():
            print(f"\n--- {section} ---")
            for t in tests:
                status = "PASS" if t.passed else "FAIL"
                icon = "+" if t.passed else "X"
                sev = f" [{t.severity}]" if not t.passed else ""
                print(f"  [{icon}] {status}{sev} {t.name}")
                print(f"      {t.message}")

        print(f"\n{'=' * 72}")
        print(f"TOTALS: {self.passed} passed, {self.failed} failed ({len(self.results)} total)")
        if self.gaps:
            print(f"\nIDENTIFIED GAPS ({len(self.gaps)}):")
            for g in self.gaps:
                print(f"  [{g.severity}] {g.name}: {g.message}")
        print("=" * 72)


# ---------------------------------------------------------------------------
# Layer 1: Data Extraction & Loading Tests
# ---------------------------------------------------------------------------

async def test_data_layer(conn: asyncpg.Connection, report: ValidationReport):
    """Test that the watcher extracted and loaded data correctly."""

    # T1.1: All citizen dwarves present in units table
    dwarves = await conn.fetch(
        "SELECT name, profession FROM units WHERE LOWER(race) = 'dwarf' AND world_id = $1",
        WORLD_ID,
    )
    dwarf_names = {r["name"] for r in dwarves}

    for gt_name, gt_prof in GROUND_TRUTH_CITIZENS:
        found = gt_name in dwarf_names
        report.add(
            f"DataLayer: Citizen '{gt_name}' in DB",
            found,
            f"Found in units table" if found else f"MISSING from units table",
            "GAP" if not found else "INFO",
        )

    # T1.2: Total dwarf count matches (should be ~18 citizens + extras)
    citizen_count = len([d for d in dwarves if d["profession"] != "BARD"])
    report.add(
        "DataLayer: Citizen count",
        citizen_count >= 18,
        f"Found {citizen_count} non-bard dwarves (expected >= 18)",
        "GAP" if citizen_count < 18 else "INFO",
    )

    # T1.3: Bards present
    bards = await conn.fetch(
        "SELECT name, profession FROM units WHERE profession = 'BARD' AND world_id = $1",
        WORLD_ID,
    )
    bard_names = {r["name"] for r in bards}
    for gt_name, _ in GROUND_TRUTH_BARDS:
        found = gt_name in bard_names
        report.add(
            f"DataLayer: Bard '{gt_name}' in DB",
            found,
            f"Found as BARD" if found else f"MISSING — searched bard_names={bard_names}",
            "GAP" if not found else "INFO",
        )

    # T1.4: Vabok's profession stored correctly
    vabok = await conn.fetchrow(
        "SELECT profession, details FROM units WHERE unaccent(name) ILIKE unaccent('%Vabok Solonotin%') AND world_id = $1",
        WORLD_ID,
    )
    if vabok:
        # In DF, expedition leader is shown as ADMINISTRATOR or has custom_profession
        details = vabok["details"] if vabok["details"] else {}
        if isinstance(details, str):
            details = json.loads(details)
        custom_prof = details.get("custom_profession", "") if isinstance(details, dict) else ""
        prof_ok = vabok["profession"] in ("ADMINISTRATOR", "EXPEDITION_LEADER") or "leader" in custom_prof.lower()
        report.add(
            "DataLayer: Vabok profession",
            prof_ok,
            f"profession='{vabok['profession']}', custom='{custom_prof}' (expected expedition leader)",
            "WARNING" if not prof_ok else "INFO",
        )
    else:
        report.add("DataLayer: Vabok profession", False, "Vabok not found in units table!", "CRITICAL")

    # T1.5: Death detection — Cerol Aludsibrek should be dead
    cerol = await conn.fetchrow(
        "SELECT is_alive, death_cause FROM units WHERE name = 'Cerol Aludsibrek' AND world_id = $1",
        WORLD_ID,
    )
    if cerol:
        report.add(
            "DataLayer: Cerol death detected",
            cerol["is_alive"] is False,
            f"is_alive={cerol['is_alive']}, death_cause={cerol['death_cause']} (expected dead, drowned)",
            "GAP" if cerol["is_alive"] else "INFO",
        )
    else:
        report.add("DataLayer: Cerol death detected", False, "Cerol not found in DB", "CRITICAL")

    # T1.6: Animal deaths detected (Dingo and Raven)
    dead_animals = await conn.fetch(
        "SELECT race, is_alive, death_cause FROM units WHERE is_alive = false AND LOWER(race) IN ('dingo', 'bird_raven') AND world_id = $1",
        WORLD_ID,
    )
    report.add(
        "DataLayer: Animal deaths captured",
        len(dead_animals) >= 2,
        f"Found {len(dead_animals)} dead dingo/raven (expected >= 2)",
        "GAP" if len(dead_animals) < 2 else "INFO",
    )

    # T1.7: Game reports captured (drowning announcement)
    report_count = await conn.fetchval("SELECT COUNT(*) FROM game_reports WHERE world_id = $1", WORLD_ID)
    report.add(
        "DataLayer: Game reports captured",
        report_count > 0,
        f"Found {report_count} game reports (expected > 0 for drowning announcement)",
        "GAP" if report_count == 0 else "INFO",
    )

    # T1.8: HF records exist for fortress dwarves
    hf_gap = await conn.fetch(
        """
        SELECT u.name, u.hist_fig_id,
               EXISTS(SELECT 1 FROM historical_figures hf WHERE hf.id = u.hist_fig_id AND hf.world_id = u.world_id) as hf_exists
        FROM units u
        WHERE u.world_id = $1 AND LOWER(u.race) = 'dwarf' AND u.profession != 'BARD'
        """,
        WORLD_ID,
    )
    missing_hf = [r for r in hf_gap if not r["hf_exists"]]
    report.add(
        "DataLayer: HF records for fortress dwarves",
        len(missing_hf) == 0,
        f"{len(missing_hf)}/{len(hf_gap)} dwarves have no HF record (HF IDs above legends export range)",
        "GAP" if missing_hf else "INFO",
    )

    # T1.9: HF records exist for visiting bards (they should be older historical figures)
    bard_hf = await conn.fetch(
        """
        SELECT u.name, u.hist_fig_id,
               (SELECT hf.name FROM historical_figures hf WHERE hf.id = u.hist_fig_id AND hf.world_id = u.world_id) as hf_name
        FROM units u
        WHERE u.world_id = $1 AND u.profession = 'BARD'
        """,
        WORLD_ID,
    )
    for b in bard_hf:
        has_hf = b["hf_name"] is not None
        report.add(
            f"DataLayer: Bard '{b['name']}' HF cross-ref",
            has_hf,
            f"HF name: '{b['hf_name']}' (unit name: '{b['name']}')" if has_hf else f"No HF record for hist_fig_id={b['hist_fig_id']}",
            "WARNING" if not has_hf else "INFO",
        )


# ---------------------------------------------------------------------------
# Layer 2: Name Resolution & Query Tests
# ---------------------------------------------------------------------------

async def test_query_layer(conn: asyncpg.Connection, report: ValidationReport):
    """Test the storyteller's ability to find entities by name."""

    # T2.1: Plain ILIKE for "Vabok" on HF table (what storyteller does)
    hf_ilike = await conn.fetch(
        "SELECT id, name FROM historical_figures WHERE name ILIKE '%Vabok%' AND world_id = $1 LIMIT 10",
        WORLD_ID,
    )
    # These are OTHER Vaboks, not our fortress leader
    vabok_in_hf = any("solonotin" in r["name"].lower() for r in hf_ilike)
    report.add(
        "QueryLayer: Storyteller ILIKE finds Vabok Solonotin in HF",
        vabok_in_hf,
        f"Found {len(hf_ilike)} HF matches, Solonotin present: {vabok_in_hf}. Other matches: {[r['name'] for r in hf_ilike[:3]]}",
        "GAP" if not vabok_in_hf else "INFO",
    )

    # T2.2: Unaccent ILIKE for "Vabok" on units table
    unit_unaccent = await conn.fetch(
        "SELECT name, hist_fig_id FROM units WHERE unaccent(name) ILIKE unaccent('%Vabok%') AND world_id = $1",
        WORLD_ID,
    )
    found = any("solonotin" in r["name"].lower() for r in unit_unaccent)
    report.add(
        "QueryLayer: Unaccent search finds Vabok in units",
        found,
        f"Found {len(unit_unaccent)} unit matches with unaccent",
        "INFO",
    )

    # T2.3: Plain ILIKE for accented names — tests accent sensitivity
    accent_tests = [
        ("Stinthäd", "units"),  # ä
        ("Vabôk", "units"),     # ô
        ("Dodókùst", "units"),  # ó, ù
        ("Nishkêshshak", "units"),  # ê
    ]
    for name, table in accent_tests:
        plain = await conn.fetchval(
            f"SELECT COUNT(*) FROM {table} WHERE name ILIKE $1 AND world_id = $2",
            f"%{name}%", WORLD_ID,
        )
        stripped = name.replace("ä", "a").replace("ô", "o").replace("ó", "o").replace("ù", "u").replace("ê", "e").replace("î", "i")
        plain_ascii = await conn.fetchval(
            f"SELECT COUNT(*) FROM {table} WHERE name ILIKE $1 AND world_id = $2",
            f"%{stripped}%", WORLD_ID,
        )
        unaccent_match = await conn.fetchval(
            f"SELECT COUNT(*) FROM {table} WHERE unaccent(name) ILIKE unaccent($1) AND world_id = $2",
            f"%{stripped}%", WORLD_ID,
        )
        report.add(
            f"QueryLayer: Accent handling '{name}'",
            unaccent_match > 0,
            f"Exact ILIKE: {plain}, ASCII ILIKE: {plain_ascii}, Unaccent: {unaccent_match}",
            "GAP" if unaccent_match == 0 else ("WARNING" if plain_ascii == 0 else "INFO"),
        )

    # T2.4: Storyteller keyword extraction test
    # Import the extract_keywords function
    sys.path.insert(0, "/Users/nathanielcannon/Claude/Projects/DwarfCron")
    from chronicler.storyteller.context import extract_keywords

    test_queries = [
        ("Tell me about Vabok Solonotin", ["vabok", "solonotin"]),
        ("Have any bards visited the fortress?", ["bards", "visited"]),
        ("Has anyone died in the fort?", ["anyone", "died", "fort"]),
        ("Who is the expedition leader?", ["expedition", "leader"]),
        ("What dwarves live in the fortress?", ["dwarves", "live"]),
    ]
    for query, expected_keywords in test_queries:
        actual = extract_keywords(query)
        # Check that at least some expected keywords appear
        overlap = set(actual) & set(expected_keywords)
        report.add(
            f"QueryLayer: Keywords for '{query[:40]}...'",
            len(overlap) > 0,
            f"Extracted: {actual}, Expected overlap: {expected_keywords}, Got: {list(overlap)}",
            "WARNING" if len(overlap) == 0 else "INFO",
        )

    # T2.5: Category routing for "dwarves" triggers live_units
    from chronicler.storyteller.context import _CATEGORY_ROUTES
    category_tests = [
        ("dwarves", "live_units"),
        ("fortress", "live_units"),
        ("bards", None),       # "bards" is NOT routed — it falls through to name search!
        ("died", None),        # "died" is NOT routed
        ("dead", None),        # "dead" is NOT routed
        ("announcement", "live_reports"),
    ]
    for keyword, expected_route_type in category_tests:
        route = _CATEGORY_ROUTES.get(keyword)
        actual_type = route[0] if route else None
        matched = actual_type == expected_route_type
        report.add(
            f"QueryLayer: Category route '{keyword}'",
            matched,
            f"Routes to: {actual_type} (expected: {expected_route_type})",
            "WARNING" if not matched and expected_route_type is not None else "INFO",
        )

    # T2.6: Name mismatch between units and HF tables for bards
    bard_name_check = await conn.fetch(
        """
        SELECT u.name as unit_name, hf.name as hf_name
        FROM units u
        JOIN historical_figures hf ON hf.id = u.hist_fig_id AND hf.world_id = u.world_id
        WHERE u.world_id = $1 AND u.profession = 'BARD'
        """,
        WORLD_ID,
    )
    for b in bard_name_check:
        names_match = b["unit_name"].lower() == b["hf_name"].lower()
        report.add(
            f"QueryLayer: Bard name consistency '{b['unit_name']}'",
            names_match,
            f"Unit: '{b['unit_name']}' vs HF: '{b['hf_name']}' — {'match' if names_match else 'MISMATCH (native vs English)'}",
            "WARNING" if not names_match else "INFO",
        )


# ---------------------------------------------------------------------------
# Layer 3: Context Retrieval Tests (without LLM)
# ---------------------------------------------------------------------------

async def test_context_layer(pool: asyncpg.Pool, report: ValidationReport):
    """Test the context retrieval pipeline produces useful context for key queries."""
    sys.path.insert(0, "/Users/nathanielcannon/Claude/Projects/DwarfCron")
    from chronicler.storyteller.context import retrieve_context
    from chronicler.storyteller.prompts import format_context

    test_cases = [
        {
            "query": "Tell me about Vabok Solonotin",
            "expected_content": ["vabok", "solonotin"],
            "description": "Should find the expedition leader by name",
        },
        {
            "query": "Have any bards visited Likotkon?",
            "expected_content": ["bard", "doren", "ducim"],
            "description": "Should find visiting bards",
        },
        {
            "query": "Has anyone died in the fort?",
            "expected_content": ["dead", "died", "drowned", "cerol"],
            "description": "Should find death events",
        },
        {
            "query": "Who are the dwarves in the fortress?",
            "expected_content": ["dwarf", "fortress"],
            "description": "Should trigger live_units route and list inhabitants",
        },
        {
            "query": "What is the expedition leader doing?",
            "expected_content": ["expedition", "leader"],
            "description": "Should find position info or leader dwarf",
        },
    ]

    for tc in test_cases:
        try:
            records = await retrieve_context(pool, WORLD_ID, tc["query"])
            context_text = format_context(records)
            context_lower = context_text.lower()

            # Check if any expected content appears in context
            found_keywords = [kw for kw in tc["expected_content"] if kw.lower() in context_lower]
            has_content = len(found_keywords) > 0
            categories = list({r["category"] for r in records})

            report.add(
                f"ContextLayer: '{tc['query'][:45]}...'",
                has_content,
                f"Records: {len(records)}, Categories: {categories}, "
                f"Found keywords: {found_keywords}/{tc['expected_content']}, "
                f"Context chars: {len(context_text)}",
                "GAP" if not has_content else "INFO",
            )
        except Exception as e:
            report.add(
                f"ContextLayer: '{tc['query'][:45]}...'",
                False,
                f"ERROR: {e}",
                "CRITICAL",
            )


# ---------------------------------------------------------------------------
# Layer 4: Chronicler API Tests (via HTTP)
# ---------------------------------------------------------------------------

async def test_api_layer(report: ValidationReport):
    """Test the Chronicler API endpoint responses.

    Requires the Chronicler server to be running at localhost:8080.
    Uses the /api/ask endpoint which streams SSE responses.
    """
    try:
        import httpx
    except ImportError:
        report.add("APILayer: httpx available", False, "httpx not installed — skipping API tests", "WARNING")
        return

    base_url = "http://localhost:8080"

    # Check if server is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/")
            if resp.status_code != 200:
                report.add("APILayer: Server reachable", False, f"Status {resp.status_code}", "WARNING")
                return
    except Exception as e:
        report.add("APILayer: Server reachable", False, f"Cannot reach {base_url}: {e}", "WARNING")
        return

    report.add("APILayer: Server reachable", True, f"Chronicler running at {base_url}", "INFO")

    # Test /api/ask with SSE streaming
    test_queries = [
        {
            "query": "What can you tell me about Vabok Solonotin of Likotkon?",
            "world_id": WORLD_ID,
            "check_not": ["no record", "no information", "cannot find"],
            "check_has": ["vabok"],
            "description": "Should NOT say 'no record' for the expedition leader",
        },
        {
            "query": "Who are the dwarves living in the fortress?",
            "world_id": WORLD_ID,
            "check_not": [],
            "check_has": ["dwarf"],
            "description": "Should list fortress inhabitants",
        },
    ]

    for tc in test_queries:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # The /api/ask endpoint uses SSE, so we need to handle streaming
                response_text = ""
                async with client.stream(
                    "POST",
                    f"{base_url}/api/ask",
                    json={"query": tc["query"], "world_id": tc["world_id"]},
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            if "token" in data:
                                response_text += data["token"]
                            elif "done" in data:
                                break

                response_lower = response_text.lower()

                # Check for forbidden phrases
                forbidden_found = [p for p in tc["check_not"] if p in response_lower]
                # Check for expected content
                expected_found = [p for p in tc["check_has"] if p in response_lower]

                passed = len(forbidden_found) == 0 and len(expected_found) > 0
                report.add(
                    f"APILayer: '{tc['query'][:45]}...'",
                    passed,
                    f"Response ({len(response_text)} chars): "
                    f"forbidden={forbidden_found}, expected={expected_found}. "
                    f"Preview: '{response_text[:150]}...'",
                    "GAP" if not passed else "INFO",
                )
        except Exception as e:
            report.add(
                f"APILayer: '{tc['query'][:45]}...'",
                False,
                f"ERROR: {e}",
                "CRITICAL",
            )


# ---------------------------------------------------------------------------
# Layer 5: Cross-Layer Consistency Tests
# ---------------------------------------------------------------------------

async def test_cross_layer(conn: asyncpg.Connection, report: ValidationReport):
    """Test consistency between different data sources."""

    # T5.1: Units table has world_id matching worlds table
    world_exists = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM worlds WHERE id = $1)", WORLD_ID
    )
    report.add(
        "CrossLayer: World ID consistency",
        world_exists,
        f"world_id={WORLD_ID} exists in worlds table: {world_exists}",
        "CRITICAL" if not world_exists else "INFO",
    )

    # T5.2: All units have valid world_id
    orphan_units = await conn.fetchval(
        "SELECT COUNT(*) FROM units WHERE world_id NOT IN (SELECT id FROM worlds)"
    )
    report.add(
        "CrossLayer: No orphan units",
        orphan_units == 0,
        f"{orphan_units} units with invalid world_id",
        "WARNING" if orphan_units > 0 else "INFO",
    )

    # T5.3: HF cross-references from units are resolvable
    unresolvable = await conn.fetch(
        """
        SELECT u.name, u.hist_fig_id
        FROM units u
        WHERE u.world_id = $1
          AND u.hist_fig_id IS NOT NULL
          AND NOT EXISTS(
            SELECT 1 FROM historical_figures hf
            WHERE hf.id = u.hist_fig_id AND hf.world_id = u.world_id
          )
        """,
        WORLD_ID,
    )
    report.add(
        "CrossLayer: Unresolvable HF references",
        len(unresolvable) == 0,
        f"{len(unresolvable)} units have hist_fig_ids with no matching HF record. "
        f"Examples: {[(r['name'], r['hist_fig_id']) for r in unresolvable[:5]]}",
        "GAP" if unresolvable else "INFO",
    )

    # T5.4: Unit events reference valid units
    orphan_events = await conn.fetchval(
        """
        SELECT COUNT(*) FROM unit_events ue
        WHERE NOT EXISTS(
            SELECT 1 FROM units u WHERE u.id = ue.unit_id AND u.world_id = ue.world_id
        )
        """
    )
    report.add(
        "CrossLayer: Unit events reference valid units",
        orphan_events == 0,
        f"{orphan_events} orphan unit events",
        "WARNING" if orphan_events > 0 else "INFO",
    )

    # T5.5: Sync snapshots recent
    latest_sync = await conn.fetchval(
        "SELECT MAX(synced_at) FROM sync_snapshots WHERE world_id = $1", WORLD_ID
    )
    report.add(
        "CrossLayer: Recent sync snapshot",
        latest_sync is not None,
        f"Latest sync: {latest_sync}",
        "WARNING" if latest_sync is None else "INFO",
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def main():
    report = ValidationReport()

    print("Connecting to database...")
    pool = await asyncpg.create_pool(DB_DSN, min_size=1, max_size=3)
    conn = await pool.acquire()

    try:
        print("Running Layer 1: Data Extraction & Loading...")
        await test_data_layer(conn, report)

        print("Running Layer 2: Name Resolution & Query...")
        await test_query_layer(conn, report)

        print("Running Layer 3: Context Retrieval...")
        await test_context_layer(pool, report)

        print("Running Layer 4: Chronicler API...")
        await test_api_layer(report)

        print("Running Layer 5: Cross-Layer Consistency...")
        await test_cross_layer(conn, report)

    finally:
        await pool.release(conn)
        await pool.close()

    report.print_report()
    return report


if __name__ == "__main__":
    report = asyncio.run(main())
    sys.exit(0 if report.failed == 0 else 1)
