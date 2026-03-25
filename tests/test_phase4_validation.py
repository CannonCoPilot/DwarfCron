"""Phase 4 Stages 4.1 + 4.2 — Comprehensive Validation Suite.

Three layers of testing:
  1. API endpoint validation (correct HTTP responses, data shapes)
  2. UI page rendering (HTML loads, expected content present)
  3. Scenario-based end-user reality checks (what would a user expect?)

Tests run against the live server at localhost:8080 and live DB.
"""

import pytest
import pytest_asyncio
import asyncpg
import httpx

BASE_URL = 'http://localhost:8080'
DB_DSN = 'postgresql://jarvis:OSDbeydP6TOBGoJUym6rTBfULKJYqqPE@localhost:5432/chronicler'
WORLD_ID = 1

# ── Test entity IDs (from live DB) ──────────────────────────────────────────
# These are real entities in world 1 (Tar Thran / The Land of Dawning)
TOP_HF_ID = 42730       # espir massivetakes the unseen (demon, prominence 1.0)
KILLER_HF_ID = 1170     # ngusna scalecrows (47 kills)
VAMPIRE_HF_ID = 8291    # sodel diamondcult
NECRO_HF_ID = 6294      # bomrek helmfrills
BIGGEST_WAR_ID = 9387   # the riddled war (43 battles)
BUSIEST_SITE_ID = 331   # mergedtongs (fortress, 6934 events)
LARGEST_CIV_ID = 1006   # the mighty confederations (human)
ARTIFACT_ID = 211        # tombssweat


@pytest_asyncio.fixture
async def conn():
    c = await asyncpg.connect(DB_DSN)
    yield c
    await c.close()


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=30)


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1: API Endpoint Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestNarrativeAPIs:
    """Validate all Stage 4.2 narrative API endpoints."""

    def test_war_narrative_api(self, client):
        r = client.get(f'/api/narrative/war/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        assert r.status_code == 200
        data = r.json()
        assert data['name'] == 'the riddled war'
        assert data['battle_count'] == 43
        assert isinstance(data['battles'], list)
        assert data['total_casualties'] >= 0
        assert data['summary_text']

    def test_war_narrative_battles_have_all_fields(self, client):
        r = client.get(f'/api/narrative/war/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        data = r.json()
        for battle in data['battles']:
            assert 'name' in battle
            assert 'year' in battle
            assert 'outcome' in battle
            assert 'attacker_casualties' in battle
            assert 'defender_casualties' in battle

    def test_battle_detail_api(self, client):
        # Get first battle of the biggest war
        r = client.get(f'/api/narrative/war/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        battle_id = r.json()['battles'][0]['id']
        r2 = client.get(f'/api/narrative/battle/{battle_id}?world_id={WORLD_ID}')
        assert r2.status_code == 200
        data = r2.json()
        assert data['name']
        assert data['parent_war'] is not None
        assert data['parent_war']['name'] == 'the riddled war'
        assert isinstance(data['attacker_squads'], list)

    def test_civilization_narrative_api(self, client):
        r = client.get(f'/api/narrative/civilization/{LARGEST_CIV_ID}?world_id={WORLD_ID}')
        assert r.status_code == 200
        data = r.json()
        assert data['type'] == 'civilization'
        assert data['member_count'] > 0
        assert isinstance(data['sites'], list)
        assert isinstance(data['wars'], list)
        assert data['summary_text']

    def test_biography_api(self, client):
        r = client.get(f'/api/narrative/biography/{TOP_HF_ID}?world_id={WORLD_ID}')
        assert r.status_code == 200
        data = r.json()
        assert data['name'] == 'espir massivetakes the unseen'
        assert data['race'] == 'DEMON_18'
        assert isinstance(data['relationships'], list)
        assert isinstance(data['memberships'], list)
        assert isinstance(data['top_events'], list)
        assert len(data['biography_text']) > 50

    def test_biography_supernatural_flags(self, client):
        r = client.get(f'/api/narrative/biography/{VAMPIRE_HF_ID}?world_id={WORLD_ID}')
        data = r.json()
        assert len(data['supernatural']) > 0
        assert 'vampire' in data['supernatural']

    def test_narrative_timeline_api(self, client):
        r = client.get(f'/api/narrative/timeline?world_id={WORLD_ID}&min_weight=5&limit=10')
        assert r.status_code == 200
        data = r.json()
        assert data['count'] > 0
        assert data['count'] <= 10
        for ev in data['events']:
            assert ev['narrative_weight'] >= 5

    def test_narrative_arcs_api(self, client):
        r = client.get(f'/api/narrative/arcs?world_id={WORLD_ID}&limit=10')
        assert r.status_code == 200
        data = r.json()
        assert data['count'] > 0
        for arc in data['arcs']:
            assert 'arc_type' in arc
            assert 'dramatic_weight' in arc

    def test_narrative_status_api(self, client):
        r = client.get(f'/api/narrative/status?world_id={WORLD_ID}')
        assert r.status_code == 200
        data = r.json()
        assert data['table_counts']['narrative_events'] > 400000
        assert data['table_counts']['narrative_arcs'] > 10000
        assert data['table_counts']['event_causal_links'] > 20000

    def test_narrative_context_api(self, client):
        r = client.get(f'/api/narrative/context?world_id={WORLD_ID}&query_type=world_overview')
        assert r.status_code == 200
        data = r.json()
        assert 'text' in data or 'blocks' in data

    def test_not_found_returns_error(self, client):
        r = client.get(f'/api/narrative/war/999999?world_id={WORLD_ID}')
        assert r.status_code == 200  # API returns 200 with error key
        assert 'error' in r.json()

        r2 = client.get(f'/api/narrative/biography/999999?world_id={WORLD_ID}')
        assert 'error' in r2.json()


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2: UI Page Rendering
# ═══════════════════════════════════════════════════════════════════════════


class TestUIPages:
    """Validate that HTML pages load and contain expected content."""

    def test_world_page_loads(self, client):
        r = client.get(f'/explorer?world_id={WORLD_ID}')
        assert r.status_code == 200
        assert 'text/html' in r.headers.get('content-type', '')

    def test_hf_detail_page_loads(self, client):
        r = client.get(f'/explorer/hf/{TOP_HF_ID}?world_id={WORLD_ID}')
        assert r.status_code == 200
        html = r.text
        assert 'espir massivetakes' in html.lower() or 'espir' in html.lower()

    def test_hf_detail_has_events_tab(self, client):
        r = client.get(f'/explorer/hf/{TOP_HF_ID}?world_id={WORLD_ID}')
        html = r.text
        assert 'dtab-events' in html or 'Events' in html

    def test_hf_detail_has_year_headers(self, client):
        """Stage 4.1: year headers should appear in event table."""
        r = client.get(f'/explorer/hf/{KILLER_HF_ID}?world_id={WORLD_ID}')
        html = r.text
        assert 'year-header-row' in html or 'Year ' in html

    def test_hf_events_render_with_template(self, client):
        """Events should render with template text, not raw JSON."""
        r = client.get(f'/explorer/hf/{KILLER_HF_ID}?world_id={WORLD_ID}')
        html = r.text
        # Should contain rendered event text (not raw event_type strings)
        # The event-text class wraps rendered output
        assert 'event-text' in html
        # Should NOT contain raw JSON-like content in event cells
        assert '{"hfid":' not in html

    def test_site_detail_page_loads(self, client):
        r = client.get(f'/explorer/site/{BUSIEST_SITE_ID}?world_id={WORLD_ID}')
        assert r.status_code == 200
        html = r.text
        assert 'mergedtongs' in html.lower() or 'Mergedtongs' in html

    def test_entity_detail_page_loads(self, client):
        r = client.get(f'/explorer/entity/{LARGEST_CIV_ID}?world_id={WORLD_ID}')
        assert r.status_code == 200
        html = r.text
        assert 'mighty confederations' in html.lower() or 'confederation' in html.lower()

    def test_artifact_detail_page_loads(self, client):
        r = client.get(f'/explorer/artifact/{ARTIFACT_ID}?world_id={WORLD_ID}')
        assert r.status_code == 200

    def test_explorer_page_loads(self, client):
        r = client.get(f'/explorer?world_id={WORLD_ID}')
        assert r.status_code == 200

    def test_event_collection_page_loads(self, client):
        """War/battle collection pages should load."""
        r = client.get(f'/explorer/collection/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        assert r.status_code == 200
        html = r.text
        assert 'riddled war' in html.lower() or 'riddled' in html.lower()

    def test_vampire_hf_page_shows_flag(self, client):
        """Vampire HF page should indicate vampire status."""
        r = client.get(f'/explorer/hf/{VAMPIRE_HF_ID}?world_id={WORLD_ID}')
        html = r.text.lower()
        assert 'vampire' in html

    def test_necromancer_hf_page_shows_flag(self, client):
        r = client.get(f'/explorer/hf/{NECRO_HF_ID}?world_id={WORLD_ID}')
        html = r.text.lower()
        assert 'necromancer' in html


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3: Scenario-Based End-User Reality Checks
# ═══════════════════════════════════════════════════════════════════════════


class TestUserScenarios:
    """End-user perspective tests: what would a player expect to see?"""

    # ── Scenario 1: "Tell me about the biggest war" ─────────────────────

    def test_scenario_war_overview_is_coherent(self, client):
        """User asks about the biggest war — the response should make sense."""
        r = client.get(f'/api/narrative/war/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        data = r.json()
        # War should have a name
        assert data['name'], "War has no name"
        # War should have start year
        assert data['start_year'] is not None, "War has no start year"
        # Should have at least 1 battle
        assert data['battle_count'] > 0, "War has no battles"
        # Summary text should mention the war name
        assert data['name'] in data['summary_text'], \
            f"Summary doesn't mention war name: {data['summary_text'][:100]}"
        # Aggressor and defender should be different entities (or one is None)
        if data['aggressor'] and data['defender']:
            assert data['aggressor']['id'] != data['defender']['id'], \
                "Aggressor and defender are the same entity"

    def test_scenario_war_battles_are_chronological(self, client):
        """Battles within a war should be in chronological order."""
        r = client.get(f'/api/narrative/war/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        battles = r.json()['battles']
        years = [b['year'] for b in battles]
        assert years == sorted(years), \
            f"Battles not chronological: {years[:10]}"

    def test_scenario_war_casualties_are_non_negative(self, client):
        """No negative casualty counts."""
        r = client.get(f'/api/narrative/war/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        data = r.json()
        assert data['attacker_casualties'] >= 0
        assert data['defender_casualties'] >= 0
        assert data['total_casualties'] == \
            data['attacker_casualties'] + data['defender_casualties']

    # ── Scenario 2: "Who is this famous figure?" ────────────────────────

    def test_scenario_biography_has_birth(self, client):
        """User looks up a famous figure — should see birth year."""
        r = client.get(f'/api/narrative/biography/{TOP_HF_ID}?world_id={WORLD_ID}')
        data = r.json()
        assert data['birth_year'] is not None, "Top HF has no birth year"

    def test_scenario_biography_text_mentions_name(self, client):
        """Biography text should start with or mention the figure's name."""
        r = client.get(f'/api/narrative/biography/{TOP_HF_ID}?world_id={WORLD_ID}')
        data = r.json()
        assert data['name'] in data['biography_text'], \
            f"Biography doesn't mention name: {data['biography_text'][:200]}"

    def test_scenario_biography_killer_shows_kill_count(self, client):
        """A prolific killer's biography should mention their kills."""
        r = client.get(f'/api/narrative/biography/{KILLER_HF_ID}?world_id={WORLD_ID}')
        data = r.json()
        assert data['kill_count'] > 0, "Killer HF shows 0 kills"
        assert 'kill' in data['biography_text'].lower(), \
            "Biography doesn't mention kills for prolific killer"

    def test_scenario_biography_vampire_shows_nature(self, client):
        """Looking up a vampire — user expects to see vampire mentioned."""
        r = client.get(f'/api/narrative/biography/{VAMPIRE_HF_ID}?world_id={WORLD_ID}')
        data = r.json()
        assert 'vampire' in data['supernatural'], \
            "Vampire not listed in supernatural flags"
        assert 'vampire' in data['biography_text'].lower(), \
            "Biography doesn't mention vampire nature"

    def test_scenario_biography_has_key_events(self, client):
        """An important figure should have events listed."""
        r = client.get(f'/api/narrative/biography/{TOP_HF_ID}?world_id={WORLD_ID}')
        data = r.json()
        assert len(data['top_events']) > 0, \
            "Top HF has no events — xref problem?"

    # ── Scenario 3: "What's the history of this civilization?" ──────────

    def test_scenario_civ_has_members(self, client):
        """Largest civ should have many members."""
        r = client.get(f'/api/narrative/civilization/{LARGEST_CIV_ID}?world_id={WORLD_ID}')
        data = r.json()
        assert data['member_count'] > 100, \
            f"Largest civ has only {data['member_count']} members"

    def test_scenario_civ_summary_mentions_name(self, client):
        """Civ summary should mention the civilization's name."""
        r = client.get(f'/api/narrative/civilization/{LARGEST_CIV_ID}?world_id={WORLD_ID}')
        data = r.json()
        name = data.get('name') or ''
        if name:
            assert name.lower() in data['summary_text'].lower(), \
                f"Summary doesn't mention civ name"

    def test_scenario_civ_wars_have_opponents(self, client):
        """Each war a civ fought should name the opponent."""
        r = client.get(f'/api/narrative/civilization/{LARGEST_CIV_ID}?world_id={WORLD_ID}')
        data = r.json()
        for war in data['wars'][:5]:  # check first 5
            assert war.get('opponent'), \
                f"War '{war['name']}' has no opponent info"

    # ── Scenario 4: "Show me what happened at this site" ────────────────

    def test_scenario_site_page_has_events(self, client):
        """A busy site should show events on its detail page."""
        r = client.get(f'/explorer/site/{BUSIEST_SITE_ID}?world_id={WORLD_ID}')
        html = r.text
        # Should have event rows in the page
        assert 'event-row' in html or 'event-text' in html or \
            'event_type' in html.lower(), \
            "Site page has no visible events"

    # ── Scenario 5: "What happened in the biggest battle?" ──────────────

    def test_scenario_battle_has_combatants(self, client):
        """User clicks on a battle — expects to see who fought."""
        # Get first battle of biggest war
        r = client.get(f'/api/narrative/war/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        battle_id = r.json()['battles'][0]['id']
        r2 = client.get(f'/api/narrative/battle/{battle_id}?world_id={WORLD_ID}')
        data = r2.json()
        # Should have combatant info
        has_combatants = (
            data.get('attacker_total', 0) > 0 or
            data.get('defender_total', 0) > 0 or
            len(data.get('attacker_participants', [])) > 0
        )
        assert has_combatants, "Battle has no combatant information"

    def test_scenario_battle_outcome_is_valid(self, client):
        """Battle outcome should be a recognizable string."""
        r = client.get(f'/api/narrative/war/{BIGGEST_WAR_ID}?world_id={WORLD_ID}')
        battle_id = r.json()['battles'][0]['id']
        r2 = client.get(f'/api/narrative/battle/{battle_id}?world_id={WORLD_ID}')
        outcome = r2.json()['outcome']
        valid_outcomes = {
            'attacker won', 'defender won', 'unknown',
            'attacker victory', 'defender victory', 'stalemate',
        }
        assert outcome in valid_outcomes or 'won' in outcome or outcome == 'unknown', \
            f"Unrecognized battle outcome: '{outcome}'"


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 4: Data Integrity Checks
# ═══════════════════════════════════════════════════════════════════════════


class TestDataIntegrity:
    """Verify data consistency between generators and DB."""

    @pytest.mark.asyncio
    async def test_war_battle_count_matches_db(self, conn):
        """War generator battle count should match DB query."""
        from chronicler.storyteller.narrative_generators import generate_war_narrative
        result = await generate_war_narrative(conn, WORLD_ID, BIGGEST_WAR_ID)
        db_count = await conn.fetchval("""
            SELECT COUNT(*) FROM history_event_collections
            WHERE world_id = $1 AND parent_id = $2 AND type = 'battle'
        """, WORLD_ID, BIGGEST_WAR_ID)
        assert result['battle_count'] == db_count, \
            f"Generator says {result['battle_count']} battles, DB has {db_count}"

    @pytest.mark.asyncio
    async def test_civ_member_count_matches_db(self, conn):
        """Civ generator member count should match DB."""
        from chronicler.storyteller.narrative_generators import generate_civilization_narrative
        result = await generate_civilization_narrative(conn, WORLD_ID, LARGEST_CIV_ID)
        db_count = await conn.fetchval("""
            SELECT COUNT(*) FROM hf_entity_links
            WHERE world_id = $1 AND entity_id = $2 AND link_type = 'member'
        """, WORLD_ID, LARGEST_CIV_ID)
        assert result['member_count'] == db_count

    @pytest.mark.asyncio
    async def test_biography_event_count_matches_xref(self, conn):
        """Biography top_events should come from xref."""
        from chronicler.storyteller.narrative_generators import generate_character_biography
        result = await generate_character_biography(conn, WORLD_ID, TOP_HF_ID)
        db_count = await conn.fetchval("""
            SELECT COUNT(*) FROM event_entity_xref
            WHERE world_id = $1 AND entity_type = 'hf' AND entity_id = $2
        """, WORLD_ID, TOP_HF_ID)
        # top_events is limited to 20 but should be <= actual count
        assert len(result['top_events']) <= db_count
        assert len(result['top_events']) <= 20

    @pytest.mark.asyncio
    async def test_template_coverage_is_complete(self, conn):
        """All event types in DB should have a template (Stage 4.1 DoD)."""
        from chronicler.explorer.perspective import EVENT_TEMPLATES
        rows = await conn.fetch("""
            SELECT DISTINCT event_type FROM history_events WHERE world_id = $1
        """, WORLD_ID)
        uncovered = []
        for r in rows:
            et = r['event_type']
            if et not in EVENT_TEMPLATES and et.replace('_', ' ') not in EVENT_TEMPLATES:
                uncovered.append(et)
        assert len(uncovered) == 0, \
            f"Uncovered event types: {uncovered}"

    @pytest.mark.asyncio
    async def test_narrative_tables_populated(self, conn):
        """All 6 Stage 3.6 narrative tables should have data."""
        tables = {
            'narrative_events': 400000,
            'event_causal_links': 20000,
            'narrative_arcs': 10000,
            'event_clusters': 500,
            'event_summaries': 100,
            'character_narratives': 100,
        }
        for table, min_rows in tables.items():
            count = await conn.fetchval(
                f'SELECT COUNT(*) FROM {table} WHERE world_id = $1', WORLD_ID)
            assert count >= min_rows, \
                f"{table} has {count} rows, expected >= {min_rows}"


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 5: Perspective Renderer Deep Checks
# ═══════════════════════════════════════════════════════════════════════════


class TestPerspectiveRendererDeep:
    """Detailed checks on event rendering quality."""

    @pytest.mark.asyncio
    async def test_render_sample_events_no_crashes(self, conn):
        """Render one event of each type — none should crash."""
        from chronicler.explorer.perspective import PerspectiveRenderer
        from chronicler.explorer.linking import EntityLinkRenderer

        # Minimal linker (no pool needed for link generation)
        class StubLinker(EntityLinkRenderer):
            def __init__(self): pass
            def link(self, et, eid, name, wid=1): return f'[{name}]'

        renderer = PerspectiveRenderer(StubLinker(), WORLD_ID)

        # Get one event of each type
        rows = await conn.fetch("""
            SELECT DISTINCT ON (event_type)
                id, year, seconds, event_type, details,
                hf_id_1, hf_id_2, site_id, region_id,
                entity_id_1, entity_id_2, artifact_id, structure_id
            FROM history_events WHERE world_id = $1
            ORDER BY event_type, id
        """, WORLD_ID)

        failures = []
        for row in rows:
            try:
                result = renderer.render_event(dict(row), 'hf', 0)
                if not result or len(result) == 0:
                    failures.append(f"{row['event_type']}: empty render")
            except Exception as e:
                failures.append(f"{row['event_type']}: {e}")

        assert len(failures) == 0, \
            f"{len(failures)} event types failed to render:\n" + \
            '\n'.join(failures[:10])

    @pytest.mark.asyncio
    async def test_no_unresolved_placeholders(self, conn):
        """Rendered events should not contain raw {placeholder} strings."""
        from chronicler.explorer.perspective import PerspectiveRenderer
        from chronicler.explorer.linking import EntityLinkRenderer

        class StubLinker(EntityLinkRenderer):
            def __init__(self): pass
            def link(self, et, eid, name, wid=1): return f'[{name}]'

        renderer = PerspectiveRenderer(StubLinker(), WORLD_ID)

        rows = await conn.fetch("""
            SELECT id, year, seconds, event_type, details,
                   hf_id_1, hf_id_2, site_id, region_id,
                   entity_id_1, entity_id_2, artifact_id, structure_id
            FROM history_events WHERE world_id = $1
            ORDER BY RANDOM() LIMIT 200
        """, WORLD_ID)

        placeholder_events = []
        for row in rows:
            try:
                result = renderer.render_event(dict(row), 'hf', 0)
                # Check for unresolved template placeholders like {hfid}
                if '{' in result and '}' in result:
                    # Exclude HTML attributes and CSS
                    import re
                    placeholders = re.findall(r'\{[a-z_]+\}', result)
                    if placeholders:
                        placeholder_events.append(
                            f"{row['event_type']}: {placeholders}")
            except Exception:
                pass  # rendering failures caught by other test

        assert len(placeholder_events) == 0, \
            f"{len(placeholder_events)} events with unresolved placeholders:\n" + \
            '\n'.join(placeholder_events[:10])
