"""Tests for Stage 4.2 narrative generators.

Tests run against the live DB (world_id=1) to validate real data rendering.
"""

import pytest
import pytest_asyncio
import asyncpg

from chronicler.storyteller.narrative_generators import (
    generate_war_narrative,
    generate_battle_detail,
    generate_civilization_narrative,
    generate_character_biography,
    render_age_at_death,
)

DB_DSN = 'postgresql://jarvis:OSDbeydP6TOBGoJUym6rTBfULKJYqqPE@localhost:5432/chronicler'
WORLD_ID = 1


@pytest_asyncio.fixture
async def conn():
    c = await asyncpg.connect(DB_DSN)
    yield c
    await c.close()


# ── War Narrative ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_war_narrative_structure(conn):
    """War narrative returns expected keys."""
    # Get a war with battles
    war = await conn.fetchrow("""
        SELECT w.id FROM history_event_collections w
        WHERE w.world_id = $1 AND w.type = 'war'
          AND EXISTS (
            SELECT 1 FROM history_event_collections b
            WHERE b.world_id = $1 AND b.parent_id = w.id AND b.type = 'battle'
          )
        LIMIT 1
    """, WORLD_ID)
    assert war, "No war with battles found in DB"

    result = await generate_war_narrative(conn, WORLD_ID, war['id'])
    assert 'error' not in result
    assert result['name']
    assert result['start_year'] is not None
    assert isinstance(result['battles'], list)
    assert result['battle_count'] > 0
    assert 'aggressor' in result
    assert 'defender' in result
    assert 'summary_text' in result
    assert len(result['summary_text']) > 10


@pytest.mark.asyncio
async def test_war_narrative_battles_have_outcome(conn):
    """Each battle in a war has an outcome field."""
    war = await conn.fetchrow("""
        SELECT w.id FROM history_event_collections w
        WHERE w.world_id = $1 AND w.type = 'war'
          AND EXISTS (
            SELECT 1 FROM history_event_collections b
            WHERE b.world_id = $1 AND b.parent_id = w.id AND b.type = 'battle'
          )
        LIMIT 1
    """, WORLD_ID)

    result = await generate_war_narrative(conn, WORLD_ID, war['id'])
    for battle in result['battles']:
        assert 'outcome' in battle
        assert 'site' in battle
        assert 'year' in battle


@pytest.mark.asyncio
async def test_war_not_found(conn):
    result = await generate_war_narrative(conn, WORLD_ID, 999999)
    assert 'error' in result


# ── Battle Detail ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_battle_detail_structure(conn):
    """Battle detail returns expected keys."""
    battle = await conn.fetchrow("""
        SELECT id FROM history_event_collections
        WHERE world_id = $1 AND type = 'battle' AND details IS NOT NULL
        LIMIT 1
    """, WORLD_ID)
    assert battle, "No battle with details found"

    result = await generate_battle_detail(conn, WORLD_ID, battle['id'])
    assert 'error' not in result
    assert result['name']
    assert result['year'] is not None
    assert 'outcome' in result
    assert 'attacker_squads' in result
    assert 'defender_squads' in result
    assert isinstance(result['attacker_squads'], list)


@pytest.mark.asyncio
async def test_battle_has_parent_war(conn):
    """Battles with parent_id reference their parent war."""
    battle = await conn.fetchrow("""
        SELECT id FROM history_event_collections
        WHERE world_id = $1 AND type = 'battle' AND parent_id IS NOT NULL
        LIMIT 1
    """, WORLD_ID)

    result = await generate_battle_detail(conn, WORLD_ID, battle['id'])
    assert result.get('parent_war') is not None
    assert 'name' in result['parent_war']


@pytest.mark.asyncio
async def test_battle_not_found(conn):
    result = await generate_battle_detail(conn, WORLD_ID, 999999)
    assert 'error' in result


# ── Civilization Narrative ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_civilization_narrative_structure(conn):
    """Civilization narrative returns expected keys."""
    entity = await conn.fetchrow("""
        SELECT id FROM entities
        WHERE world_id = $1 AND type = 'civilization'
        LIMIT 1
    """, WORLD_ID)
    assert entity, "No civilization found"

    result = await generate_civilization_narrative(conn, WORLD_ID, entity['id'])
    assert 'error' not in result
    assert 'name' in result
    assert result['type'] == 'civilization'
    assert isinstance(result['sites'], list)
    assert isinstance(result['wars'], list)
    assert 'member_count' in result
    assert 'summary_text' in result


@pytest.mark.asyncio
async def test_civilization_wars_have_roles(conn):
    """Each war in civ narrative has aggressor/defender role."""
    # Find a civ that fought wars
    entity = await conn.fetchrow("""
        SELECT e.id FROM entities e
        WHERE e.world_id = $1 AND e.type = 'civilization'
          AND EXISTS (
            SELECT 1 FROM history_event_collections w
            WHERE w.world_id = $1 AND w.type = 'war'
              AND (w.attacker_entity_id = e.id OR w.defender_entity_id = e.id)
          )
        LIMIT 1
    """, WORLD_ID)

    if not entity:
        pytest.skip("No civilization with wars found")

    result = await generate_civilization_narrative(conn, WORLD_ID, entity['id'])
    assert result['war_count'] > 0
    for war in result['wars']:
        assert war['role'] in ('aggressor', 'defender')
        assert war.get('opponent') is not None


@pytest.mark.asyncio
async def test_civilization_not_found(conn):
    result = await generate_civilization_narrative(conn, WORLD_ID, 999999)
    assert 'error' in result


# ── Character Biography ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_biography_structure(conn):
    """Biography returns expected keys."""
    hf = await conn.fetchrow("""
        SELECT id FROM historical_figures
        WHERE world_id = $1 AND prominence_score > 0.3
        ORDER BY prominence_score DESC LIMIT 1
    """, WORLD_ID)
    assert hf, "No prominent HF found"

    result = await generate_character_biography(conn, WORLD_ID, hf['id'])
    assert 'error' not in result
    assert result['name']
    assert result['race']
    assert isinstance(result['relationships'], list)
    assert isinstance(result['memberships'], list)
    assert isinstance(result['top_events'], list)
    assert 'biography_text' in result
    assert len(result['biography_text']) > 20


@pytest.mark.asyncio
async def test_biography_dead_hf_has_death_info(conn):
    """Dead HF biography includes death details."""
    hf = await conn.fetchrow("""
        SELECT id FROM historical_figures
        WHERE world_id = $1 AND death_year IS NOT NULL
          AND death_cause IS NOT NULL AND prominence_score > 0.1
        LIMIT 1
    """, WORLD_ID)
    if not hf:
        pytest.skip("No dead prominent HF found")

    result = await generate_character_biography(conn, WORLD_ID, hf['id'])
    assert result['death_info'] is not None
    assert result['death_info']['year'] is not None
    assert result['death_info']['cause_text']


@pytest.mark.asyncio
async def test_biography_supernatural_flags(conn):
    """Supernatural HF has supernatural list populated."""
    hf = await conn.fetchrow("""
        SELECT id FROM historical_figures
        WHERE world_id = $1 AND (is_deity OR is_vampire OR is_necromancer)
        LIMIT 1
    """, WORLD_ID)
    if not hf:
        pytest.skip("No supernatural HF found")

    result = await generate_character_biography(conn, WORLD_ID, hf['id'])
    assert len(result['supernatural']) > 0


@pytest.mark.asyncio
async def test_biography_not_found(conn):
    result = await generate_character_biography(conn, WORLD_ID, 999999)
    assert 'error' in result


# ── Age at Death ────────────────────────────────────────────────────────────


class TestAgeAtDeath:
    def test_simple_age(self):
        assert render_age_at_death(100, 171) == '71'

    def test_zero_age(self):
        assert render_age_at_death(100, 100) == 'less than a year'

    def test_quarter(self):
        result = render_age_at_death(0, 10, 0, 100800)  # 25% of 403200
        assert 'quarter' in result

    def test_half(self):
        result = render_age_at_death(0, 10, 0, 201600)  # 50% of 403200
        assert 'half' in result

    def test_three_quarters(self):
        result = render_age_at_death(0, 10, 0, 302400)  # 75% of 403200
        assert 'three quarters' in result

    def test_no_fraction_without_seconds(self):
        result = render_age_at_death(100, 171)
        assert result == '71'
