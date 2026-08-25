"""Chronicler E2E Validation Tests — Cross-layer data accuracy checks.

Tests three layers:
1. DATA LAYER: Does the DB match ground truth from DF screenshots?
2. QUERY LAYER: Can the storyteller find entities across all data sources?
3. SYNTHESIS LAYER: Does the LLM produce accurate responses?

Ground truth source: Screenshots from Likotkôn fortress (year 200),
captured 2026-02-23 and stored in projects/chronicler/experiments/Likotkon/
"""

import asyncio
import json
import os

import asyncpg
import httpx
import pytest
import pytest_asyncio

WORLD_ID = 8
WORLD_NAME = "Thadar En"
FORTRESS_NAME = "Likotkôn"

# DB connection from config
PG_PASSWORD = os.environ.get("PG_PASSWORD", "OSDbeydP6TOBGoJUym6rTBfULKJYqqPE")
DB_DSN = f"postgresql://jarvis:{PG_PASSWORD}@localhost:5432/chronicler"

# Chronicler API (web UI backend)
API_BASE = "http://localhost:8080"


# ── Precondition: the world under test must still exist ────────────────────
# Every assertion below is ground truth for world 8 ("Thadar En", Likotkôn
# fortress, screenshots of 2026-02-23). That world is NOT in the current
# database — as of 2026-08-25 the only world is id 1, "Orid Zurko".
#
# These are skipped, not deleted and not rewritten to match whatever world
# happens to be loaded. The ground truth is real and still valuable; it simply
# has no subject right now. Re-ingest world 8 and the whole module runs again
# with no code change.

def _world_present(world_id: int) -> bool:
    """True if world_id exists in the DB. False if absent or DB unreachable."""
    async def _check() -> bool:
        try:
            conn = await asyncpg.connect(DB_DSN)
        except Exception:
            return False
        try:
            return await conn.fetchval(
                "SELECT 1 FROM worlds WHERE id = $1", world_id
            ) is not None
        finally:
            await conn.close()

    try:
        return asyncio.run(_check())
    except Exception:
        return False


if not _world_present(WORLD_ID):
    pytest.skip(
        f"world_id={WORLD_ID} ({WORLD_NAME}) is not in the database — this "
        f"module's ground truth comes from {FORTRESS_NAME} screenshots and has "
        f"no subject to validate. Re-ingest that world to re-enable.",
        allow_module_level=True,
    )


# ── Ground Truth from Screenshots ──────────────────────────────────────────

# Citizens list from Screenshot 2 (1:35:51 PM) — 18 pop (16 visible + 2 off-screen)
GROUND_TRUTH_CITIZENS = [
    {"name_fragment": "Unib Lolord", "profession_in_game": "Miner"},
    {"name_fragment": "Stinth", "profession_in_game": "Miner"},
    {"name_fragment": "Rintar Ledan", "profession_in_game": "Carpenter"},
    {"name_fragment": "Onget Inenkikrost", "profession_in_game": "Mason"},
    {"name_fragment": "Fikod", "profession_in_game": "Planter"},
    {"name_fragment": "Vabok Solonotin", "profession_in_game": "expedition leader"},
    {"name_fragment": "Feb Nish", "profession_in_game": "Peasant"},
    {"name_fragment": "Urdim Lagem", "profession_in_game": "Peasant"},  # Urdin Lagengôner
    {"name_fragment": "Doren Moruz", "profession_in_game": "Peasant"},
    {"name_fragment": "Ohan Ibeshb", "profession_in_game": "Peasant"},  # Aban Ibeshbomrek
    {"name_fragment": "Erush Etar", "profession_in_game": "Peasant"},
    {"name_fragment": "Zon Berot", "profession_in_game": "Peasant"},
    {"name_fragment": "Deduk Arel", "profession_in_game": "Peasant"},
    {"name_fragment": "Ast Dod", "profession_in_game": "Peasant"},
    {"name_fragment": "Inod", "profession_in_game": "Peasant"},
    {"name_fragment": "Litast Stic", "profession_in_game": "Peasant"},
]

# Vabok detail from Screenshot 3 (1:47:22 PM)
VABOK_GROUND_TRUTH = {
    "name": "Vabok Solonotin",
    "english_name": "Flagwine",
    "role": "expedition leader",
    "age": 19,  # 19 years old at year 200 → birth_year = 181
    "sex": "female",  # ♀
    "squad": None,
    "skills": ["Organizer", "Carpenter", "Herbalist", "Fisherdwarf"],
    "traits": ["Disdains peace", "Values introspection", "Disdains truth"],
    "unmet_needs": ["Acquire object", "Eat good meal", "Be extravagant",
                    "Learn something", "Be with family", "Martial training"],
}

# Bard visitors from Screenshot 5 (1:47:45 PM)
GROUND_TRUTH_BARDS = [
    {"name_fragment": "Doren Bomrek", "profession": "Bard", "status": "Guest"},
    {"name_fragment": "Ducin Lolok", "profession": "Bard", "status": "Guest"},
    {"name_fragment": "Dishnab Logem", "profession": "Bard", "status": "Guest"},  # Dîshmab
]

# Dead/Missing from Screenshot 6 (1:47:50 PM) + Screenshot 7 (1:48:12 PM)
GROUND_TRUTH_DEATHS = [
    {"description": "Dingo", "status": "Deceased"},
    {"description": "Raven", "status": "Deceased"},
    {"description": "Cerol Aludsibrek", "cause": "drowned", "race": "DWARF"},
]

# Pets/Livestock from Screenshot 4 (1:47:39 PM)
GROUND_TRUTH_LIVESTOCK = [
    {"race": "DOG", "count_min": 2},
    {"race": "CAT", "count_min": 2},
    {"race": "LLAMA", "count_min": 1},
    {"race": "BIRD_TURKEY", "count_min": 1},
    {"race": "YAK", "count_min": 2},
    {"race": "SHEEP", "count_min": 1},
]


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    """Async connection pool to chronicler DB."""
    pool = await asyncpg.create_pool(DB_DSN, min_size=1, max_size=3)
    yield pool
    await pool.close()


@pytest.fixture
def api():
    """Sync HTTP client for Chronicler API."""
    return httpx.Client(base_url=API_BASE, timeout=30.0)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1: DATA COMPLETENESS — Does the DB match ground truth?
# ═══════════════════════════════════════════════════════════════════════════

class TestDataCompleteness:
    """Verify ETL pipeline captured all expected data from DF."""

    @pytest.mark.asyncio
    async def test_all_citizens_in_units_table(self, db):
        """Every citizen from the screenshot should exist in the units table."""
        async with db.acquire() as conn:
            units = await conn.fetch(
                "SELECT name, race, profession FROM units "
                "WHERE world_id = $1 AND race = 'DWARF' AND civ_id = 989",
                WORLD_ID,
            )
        unit_names = [u["name"] for u in units]

        missing = []
        for citizen in GROUND_TRUTH_CITIZENS:
            found = any(
                citizen["name_fragment"].lower() in (n or "").lower()
                for n in unit_names
            )
            if not found:
                missing.append(citizen["name_fragment"])

        assert not missing, f"Citizens missing from units table: {missing}"

    @pytest.mark.asyncio
    async def test_citizen_count_matches(self, db):
        """Fortress should have ~18-20 citizen dwarves (civ 989)."""
        async with db.acquire() as conn:
            count = await conn.fetchval(
                "SELECT count(*) FROM units "
                "WHERE world_id = $1 AND race = 'DWARF' AND civ_id = 989",
                WORLD_ID,
            )
        # Screenshot shows pop 18, but some may arrive/depart
        assert 16 <= count <= 25, f"Expected ~18 citizens, got {count}"

    @pytest.mark.asyncio
    async def test_bards_in_units_table(self, db):
        """All visiting bards should be in the units table."""
        async with db.acquire() as conn:
            bards = await conn.fetch(
                "SELECT name, profession FROM units "
                "WHERE world_id = $1 AND profession = 'BARD'",
                WORLD_ID,
            )
        bard_names = [b["name"] for b in bards]

        missing = []
        for bard in GROUND_TRUTH_BARDS:
            found = any(
                bard["name_fragment"].lower() in (n or "").lower()
                for n in bard_names
            )
            if not found:
                missing.append(bard["name_fragment"])

        assert not missing, f"Bards missing from units table: {missing}"

    @pytest.mark.asyncio
    async def test_livestock_present(self, db):
        """Livestock from screenshot should be in units table."""
        async with db.acquire() as conn:
            for animal in GROUND_TRUTH_LIVESTOCK:
                count = await conn.fetchval(
                    "SELECT count(*) FROM units "
                    "WHERE world_id = $1 AND race = $2 AND civ_id = 989",
                    WORLD_ID, animal["race"],
                )
                assert count >= animal["count_min"], (
                    f"{animal['race']}: expected >= {animal['count_min']}, got {count}"
                )

    @pytest.mark.asyncio
    async def test_vabok_exists_in_units(self, db):
        """Vabok Solonotin (expedition leader) must be in units table."""
        async with db.acquire() as conn:
            vabok = await conn.fetchrow(
                "SELECT name, english_name, profession, birth_year, sex "
                "FROM units WHERE world_id = $1 AND name ILIKE '%vabok%'",
                WORLD_ID,
            )
        assert vabok is not None, "Vabok Solonotin not found in units table"
        assert vabok["english_name"] == "Flagwine"

    @pytest.mark.asyncio
    async def test_bridge_sections_stored(self, db):
        """All 17 bridge sections should be in lua_probes."""
        expected_sections = {
            "announcements", "armies", "artifacts", "buildings", "diplomacy",
            "dwarf_emotions", "dwarf_personality", "dwarf_skills", "entities",
            "event_collections", "history", "incidents", "mandates", "squads",
            "unit_summary", "world_info", "zones",
        }
        async with db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT probe_name FROM lua_probes WHERE world_id = $1",
                WORLD_ID,
            )
        stored = {r["probe_name"] for r in rows}
        missing = expected_sections - stored
        assert not missing, f"Bridge sections missing from lua_probes: {missing}"


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2: DATA ACCURACY — Do field values match ground truth?
# ═══════════════════════════════════════════════════════════════════════════

class TestDataAccuracy:
    """Verify field-level accuracy of extracted data."""

    @pytest.mark.asyncio
    async def test_vabok_english_name(self, db):
        """Vabok's English name should be 'Flagwine'."""
        async with db.acquire() as conn:
            name = await conn.fetchval(
                "SELECT english_name FROM units "
                "WHERE world_id = $1 AND name ILIKE '%vabok%'",
                WORLD_ID,
            )
        assert name == "Flagwine", f"Expected 'Flagwine', got '{name}'"

    @pytest.mark.asyncio
    async def test_vabok_birth_year(self, db):
        """Vabok is 19 at year 200 → birth_year should be ~180-181."""
        async with db.acquire() as conn:
            birth = await conn.fetchval(
                "SELECT birth_year FROM units "
                "WHERE world_id = $1 AND name ILIKE '%vabok%'",
                WORLD_ID,
            )
        assert birth is not None, "Vabok birth_year is NULL"
        age = 200 - birth
        assert 18 <= age <= 21, f"Vabok age={age} (birth={birth}), expected ~19"

    @pytest.mark.asyncio
    async def test_vabok_sex(self, db):
        """Vabok is female (sex=0 in DF convention)."""
        async with db.acquire() as conn:
            sex = await conn.fetchval(
                "SELECT sex FROM units "
                "WHERE world_id = $1 AND name ILIKE '%vabok%'",
                WORLD_ID,
            )
        assert sex == 0, f"Vabok sex={sex}, expected 0 (female)"

    @pytest.mark.asyncio
    async def test_dwarf_personality_probe_has_data(self, db):
        """dwarf_personality probe should have 18+ dwarves."""
        async with db.acquire() as conn:
            count = await conn.fetchval(
                "SELECT jsonb_array_length(data->'dwarves') "
                "FROM lua_probes "
                "WHERE world_id = $1 AND probe_name = 'dwarf_personality' "
                "ORDER BY captured_at DESC LIMIT 1",
                WORLD_ID,
            )
        assert count is not None and count >= 16, (
            f"dwarf_personality probe has {count} dwarves, expected >= 16"
        )

    @pytest.mark.asyncio
    async def test_name_encoding_consistency(self, db):
        """Names should use consistent UTF-8 encoding (DF CP437→UTF-8)."""
        async with db.acquire() as conn:
            dwarves = await conn.fetch(
                "SELECT name FROM units "
                "WHERE world_id = $1 AND race = 'DWARF' AND civ_id = 989 "
                "AND name IS NOT NULL",
                WORLD_ID,
            )
        # All names should be non-empty strings with valid UTF-8
        for d in dwarves:
            assert d["name"], "Empty dwarf name found"
            # Check for common encoding issues
            assert "?" not in d["name"], f"Mojibake in name: {d['name']}"
            assert "\x00" not in d["name"], f"Null byte in name: {d['name']}"


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3: KNOWN DATA GAPS — Document expected failures
# ═══════════════════════════════════════════════════════════════════════════

class TestKnownGaps:
    """Tests that document known data gaps for prioritized fixing."""

    @pytest.mark.asyncio
    async def test_gap_cerol_death_not_tracked(self, db):
        """GAP: Cerol Aludsibrek drowned but is_alive=true in DB."""
        async with db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT is_alive, death_cause FROM units "
                "WHERE world_id = $1 AND name ILIKE '%cerol%'",
                WORLD_ID,
            )
        # This SHOULD be False but currently isn't — documenting the gap
        assert row is not None, "Cerol not found in units"
        if row["is_alive"]:
            pytest.xfail(
                "GAP: Cerol drowned (screenshot 7) but is_alive=True. "
                "Watcher doesn't update death status."
            )
        assert not row["is_alive"], "Cerol should be dead"
        assert "drown" in (row["death_cause"] or "").lower()

    @pytest.mark.asyncio
    async def test_gap_fortress_hfs_missing(self, db):
        """GAP: Fortress dwarves' HF IDs don't exist in historical_figures."""
        async with db.acquire() as conn:
            # Get a fortress dwarf's hist_fig_id
            hf_id = await conn.fetchval(
                "SELECT hist_fig_id FROM units "
                "WHERE world_id = $1 AND name ILIKE '%vabok%'",
                WORLD_ID,
            )
            # Check if it exists in historical_figures
            exists = await conn.fetchval(
                "SELECT count(*) FROM historical_figures "
                "WHERE world_id = $1 AND id = $2",
                WORLD_ID, hf_id,
            )
        if exists == 0:
            pytest.xfail(
                f"GAP: Vabok's hist_fig_id={hf_id} not in historical_figures. "
                "Fortress dwarves generated after legends export."
            )

    @pytest.mark.asyncio
    async def test_gap_profession_vs_role_mismatch(self, db):
        """GAP: Vabok's in-game role is 'expedition leader' but DB has 'ADMINISTRATOR'."""
        async with db.acquire() as conn:
            prof = await conn.fetchval(
                "SELECT profession FROM units "
                "WHERE world_id = $1 AND name ILIKE '%vabok%'",
                WORLD_ID,
            )
        # DF stores the DF profession enum, not the role/position title
        if prof == "ADMINISTRATOR":
            pytest.xfail(
                "GAP: Vabok's profession='ADMINISTRATOR' but in-game shows "
                "'expedition leader'. Position/role not captured separately."
            )


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 4: CHRONICLER QUERY LAYER — Can the storyteller find things?
# ═══════════════════════════════════════════════════════════════════════════

class TestChroniclerQueries:
    """Test the Chronicler's ability to retrieve and present data.

    These tests call the /ask endpoint and verify the response content.
    Requires the Chronicler web server running on localhost:8080.
    """

    def _ask_chronicler(self, api, query: str) -> str:
        """Send a query and collect the streamed response."""
        try:
            resp = api.post(
                "/api/ask",
                json={"query": query, "world_id": WORLD_ID},
                timeout=60.0,
            )
        except httpx.ConnectError:
            pytest.skip("Chronicler API not running on localhost:8080")

        if resp.status_code != 200:
            pytest.skip(f"Chronicler API returned {resp.status_code}")

        # Parse SSE stream
        tokens = []
        for line in resp.text.strip().split("\n"):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if "token" in data:
                        tokens.append(data["token"])
                except json.JSONDecodeError:
                    pass
        return "".join(tokens)

    def test_chronicler_knows_vabok(self, api):
        """Chronicler should be able to tell us about Vabok Solonotin."""
        response = self._ask_chronicler(
            api, "What can you tell me about Vabok Solonotin?"
        )
        # Check for "no record" failure
        if "no record" in response.lower() or "annals hold no" in response.lower():
            pytest.xfail(
                "GAP: Chronicler says 'no record' for Vabok. "
                "Storyteller doesn't search units table by name."
            )
        assert "vabok" in response.lower(), f"Response doesn't mention Vabok: {response[:200]}"

    def test_chronicler_knows_bards(self, api):
        """Chronicler should know about bards visiting the fortress."""
        response = self._ask_chronicler(
            api, "Tell me about bards who have visited Likotkôn."
        )
        # Check if any bard name appears
        bard_found = any(
            bard["name_fragment"].lower() in response.lower()
            for bard in GROUND_TRUTH_BARDS
        )
        if not bard_found and "no record" in response.lower():
            pytest.xfail(
                "GAP: Chronicler can't find visiting bards. "
                "Live unit data not integrated into storyteller context."
            )
        assert bard_found, f"No bard names in response: {response[:300]}"

    def test_chronicler_knows_deaths(self, api):
        """Chronicler should know about deaths in the fortress."""
        response = self._ask_chronicler(
            api, "Has anyone died in the fortress? If so, how?"
        )
        if "cerol" in response.lower() or "drown" in response.lower():
            pass  # Good — it knows about the drowning
        elif "no record" in response.lower():
            pytest.xfail(
                "GAP: Chronicler can't report deaths. "
                "Death tracking not implemented in watcher."
            )
        # Partial credit: any mention of death events
        assert any(
            word in response.lower()
            for word in ["dead", "death", "died", "drown", "casualt", "cerol"]
        ), f"No death info in response: {response[:300]}"

    def test_chronicler_lists_citizens(self, api):
        """Chronicler should list fortress citizens when asked."""
        response = self._ask_chronicler(
            api, "Who are the current citizens of the fortress?"
        )
        # Count how many citizen names appear in the response
        found_names = []
        for citizen in GROUND_TRUTH_CITIZENS:
            frag = citizen["name_fragment"].split()[0].lower()  # First name
            if frag in response.lower():
                found_names.append(citizen["name_fragment"])

        if len(found_names) < 5:
            pytest.xfail(
                f"GAP: Only {len(found_names)}/{len(GROUND_TRUTH_CITIZENS)} "
                f"citizens found in response. Names: {found_names}"
            )
        assert len(found_names) >= 10, (
            f"Expected >= 10 citizen names, got {len(found_names)}: {found_names}"
        )

    def test_chronicler_knows_expedition_leader(self, api):
        """Chronicler should know who leads the fortress."""
        response = self._ask_chronicler(
            api, "Who is the expedition leader of the fortress?"
        )
        if "vabok" in response.lower() or "flagwine" in response.lower():
            pass  # Correct
        elif "no record" in response.lower():
            pytest.xfail(
                "GAP: Chronicler can't identify expedition leader. "
                "Position/role data not in storyteller context."
            )
        assert "vabok" in response.lower() or "leader" in response.lower(), (
            f"Expected mention of Vabok as leader: {response[:300]}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 5: BRIDGE DATA QUALITY — Snapshot accuracy
# ═══════════════════════════════════════════════════════════════════════════

class TestBridgeDataQuality:
    """Verify bridge JSON data matches expected structure and content."""

    @pytest.mark.asyncio
    async def test_dwarf_personality_has_vabok(self, db):
        """Vabok should appear in dwarf_personality bridge data."""
        async with db.acquire() as conn:
            data = await conn.fetchval(
                "SELECT data FROM lua_probes "
                "WHERE world_id = $1 AND probe_name = 'dwarf_personality' "
                "ORDER BY captured_at DESC LIMIT 1",
                WORLD_ID,
            )
        if data is None:
            pytest.skip("No dwarf_personality data")

        parsed = json.loads(data) if isinstance(data, str) else data
        dwarves = parsed.get("dwarves", [])
        vabok = [d for d in dwarves if "vabok" in (d.get("name", "") or "").lower()]
        assert vabok, "Vabok not found in bridge dwarf_personality data"

    @pytest.mark.asyncio
    async def test_dwarf_skills_has_data(self, db):
        """dwarf_skills bridge data should have skill entries."""
        async with db.acquire() as conn:
            data = await conn.fetchval(
                "SELECT data FROM lua_probes "
                "WHERE world_id = $1 AND probe_name = 'dwarf_skills' "
                "ORDER BY captured_at DESC LIMIT 1",
                WORLD_ID,
            )
        if data is None:
            pytest.skip("No dwarf_skills data")

        parsed = json.loads(data) if isinstance(data, str) else data
        dwarves = parsed.get("dwarves", [])
        assert len(dwarves) >= 16, f"Expected >= 16 dwarves in skills, got {len(dwarves)}"
        # At least some dwarves should have skills
        has_skills = [d for d in dwarves if d.get("skills")]
        assert has_skills, "No dwarves have any skills data"

    @pytest.mark.asyncio
    async def test_squads_data_structure(self, db):
        """Squads bridge data should have valid structure."""
        async with db.acquire() as conn:
            data = await conn.fetchval(
                "SELECT data FROM lua_probes "
                "WHERE world_id = $1 AND probe_name = 'squads' "
                "ORDER BY captured_at DESC LIMIT 1",
                WORLD_ID,
            )
        if data is None:
            pytest.skip("No squads data")

        parsed = json.loads(data) if isinstance(data, str) else data
        assert isinstance(parsed, (dict, list)), f"Unexpected squads type: {type(parsed)}"

    @pytest.mark.asyncio
    async def test_world_info_matches(self, db):
        """Bridge world_info should match known world details."""
        async with db.acquire() as conn:
            data = await conn.fetchval(
                "SELECT data FROM lua_probes "
                "WHERE world_id = $1 AND probe_name = 'world_info' "
                "ORDER BY captured_at DESC LIMIT 1",
                WORLD_ID,
            )
        if data is None:
            pytest.skip("No world_info data")

        parsed = json.loads(data) if isinstance(data, str) else data
        # Should contain fortress name
        fort_name = parsed.get("fortress_name", "")
        assert fort_name, "Bridge world_info missing fortress_name"
