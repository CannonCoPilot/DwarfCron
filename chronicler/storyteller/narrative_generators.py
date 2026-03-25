"""Stage 4.2: Higher-order narrative generators.

Deterministic generators that produce structured narrative text from DB data.
No LLM involvement — these are template-based generators that construct
narratives from event collections, entity histories, and HF records.

Used by: detail page routes, agentic storyteller context, saga generator.
"""

from __future__ import annotations

import json
from typing import Any

from chronicler.explorer.death_cause import DeathCauseRenderer


def _parse_details(raw) -> dict:
    """Parse JSONB details which may be dict, str, or None."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


# ── War Narrative Generator ─────────────────────────────────────────────────


async def generate_war_narrative(
    conn,
    world_id: int,
    war_id: int,
    *,
    linker=None,
) -> dict[str, Any]:
    """Generate a structured war narrative from event collection data.

    Returns dict with: name, start_year, end_year, duration, aggressor, defender,
    battles (list), casualties, summary_text, timeline (list of events).
    """
    war = await conn.fetchrow("""
        SELECT id, name, start_year, end_year,
               attacker_entity_id, defender_entity_id, details
        FROM history_event_collections
        WHERE world_id = $1 AND id = $2 AND type = 'war'
    """, world_id, war_id)
    if not war:
        return {'error': f'War {war_id} not found'}

    # Resolve entity names
    attacker = await _resolve_entity(conn, world_id, war['attacker_entity_id'])
    defender = await _resolve_entity(conn, world_id, war['defender_entity_id'])

    # Get child battles
    battles_raw = await conn.fetch("""
        SELECT id, name, start_year, end_year, site_id, region_id,
               attacker_entity_id, defender_entity_id, details
        FROM history_event_collections
        WHERE world_id = $1 AND parent_id = $2 AND type = 'battle'
        ORDER BY start_year, start_seconds
    """, world_id, war_id)

    battles = []
    total_attacker_deaths = 0
    total_defender_deaths = 0

    for b in battles_raw:
        bd = _parse_details(b['details'])
        site_name = await _resolve_site(conn, world_id, b['site_id'])

        # Count casualties from squad data (may be list or single int)
        a_raw = bd.get('attacking_squad_deaths', [])
        d_raw = bd.get('defending_squad_deaths', [])
        a_deaths = sum(a_raw) if isinstance(a_raw, list) else (a_raw or 0)
        d_deaths = sum(d_raw) if isinstance(d_raw, list) else (d_raw or 0)
        total_attacker_deaths += a_deaths
        total_defender_deaths += d_deaths

        # Notable HFs in battle (may be list or single int)
        attacking_hfs = bd.get('attacking_hfid', [])
        if not isinstance(attacking_hfs, list):
            attacking_hfs = [attacking_hfs] if attacking_hfs else []
        defending_hfs = bd.get('defending_hfid', [])
        if not isinstance(defending_hfs, list):
            defending_hfs = [defending_hfs] if defending_hfs else []

        battles.append({
            'id': b['id'],
            'name': b['name'],
            'year': b['start_year'],
            'site': site_name,
            'site_id': b['site_id'],
            'outcome': bd.get('outcome', 'unknown'),
            'attacker_casualties': a_deaths,
            'defender_casualties': d_deaths,
            'attacker_combatants': len(attacking_hfs),
            'defender_combatants': len(defending_hfs),
        })

    duration = (war['end_year'] or war['start_year']) - war['start_year']

    # Get notable deaths during the war
    notable_deaths = await conn.fetch("""
        SELECT hf.id, hf.name, hf.race, hf.death_year, hf.death_cause,
               hf.prominence_score
        FROM historical_figures hf
        WHERE hf.world_id = $1
          AND hf.death_year >= $2
          AND hf.death_year <= $3
          AND hf.death_cause IS NOT NULL
          AND hf.prominence_score > 0.1
        ORDER BY hf.prominence_score DESC
        LIMIT 10
    """, world_id, war['start_year'],
        war['end_year'] or war['start_year'] + 1)

    # Build summary text
    summary_parts = [
        f"The {war['name']}",
        f"({war['start_year']}–{war['end_year'] or 'ongoing'})",
    ]
    if attacker and defender:
        summary_parts.append(
            f"was a conflict between {attacker['name']} and {defender['name']}.")
    if battles:
        summary_parts.append(
            f"It consisted of {len(battles)} battle{'s' if len(battles) != 1 else ''}.")
    total_casualties = total_attacker_deaths + total_defender_deaths
    if total_casualties:
        summary_parts.append(
            f"Total casualties: {total_casualties:,}"
            f" ({total_attacker_deaths:,} attacker, {total_defender_deaths:,} defender).")

    return {
        'id': war_id,
        'name': war['name'],
        'start_year': war['start_year'],
        'end_year': war['end_year'],
        'duration': duration,
        'aggressor': attacker,
        'defender': defender,
        'battles': battles,
        'battle_count': len(battles),
        'attacker_casualties': total_attacker_deaths,
        'defender_casualties': total_defender_deaths,
        'total_casualties': total_attacker_deaths + total_defender_deaths,
        'notable_deaths': [dict(d) for d in notable_deaths],
        'summary_text': ' '.join(summary_parts),
    }


# ── Battle Detail Renderer ──────────────────────────────────────────────────


async def generate_battle_detail(
    conn,
    world_id: int,
    battle_id: int,
) -> dict[str, Any]:
    """Generate detailed battle narrative.

    Returns dict with: name, year, site, outcome, squads (attacker/defender),
    casualties, notable_participants, events.
    """
    battle = await conn.fetchrow("""
        SELECT id, name, start_year, end_year, site_id, region_id,
               attacker_entity_id, defender_entity_id, parent_id, details
        FROM history_event_collections
        WHERE world_id = $1 AND id = $2
    """, world_id, battle_id)
    if not battle:
        return {'error': f'Battle {battle_id} not found'}

    bd = _parse_details(battle['details'])
    site_name = await _resolve_site(conn, world_id, battle['site_id'])
    attacker = await _resolve_entity(conn, world_id, battle['attacker_entity_id'])
    defender = await _resolve_entity(conn, world_id, battle['defender_entity_id'])

    # Squad breakdown
    a_races = bd.get('attacking_squad_race', [])
    a_numbers = bd.get('attacking_squad_number', [])
    a_deaths = bd.get('attacking_squad_deaths', [])
    d_races = bd.get('defending_squad_race', [])
    d_numbers = bd.get('defending_squad_number', [])
    d_deaths = bd.get('defending_squad_deaths', [])

    attacker_squads = _build_squad_summary(a_races, a_numbers, a_deaths)
    defender_squads = _build_squad_summary(d_races, d_numbers, d_deaths)

    # Notable HF participants (resolve names for top combatants)
    attacking_hfids = bd.get('attacking_hfid', [])[:10]
    defending_hfids = bd.get('defending_hfid', [])[:10]

    a_participants = await _resolve_hf_list(conn, world_id, attacking_hfids)
    d_participants = await _resolve_hf_list(conn, world_id, defending_hfids)

    # Events within this battle (via xref)
    battle_events = await conn.fetch("""
        SELECT he.id, he.year, he.seconds, he.event_type, he.details,
               he.hf_id_1, he.hf_id_2, he.site_id
        FROM history_events he
        JOIN event_entity_xref x ON x.world_id = he.world_id AND x.event_id = he.id
        WHERE he.world_id = $1
          AND x.entity_type = 'event_collection' AND x.entity_id = $2
        ORDER BY he.year, he.seconds
        LIMIT 50
    """, world_id, battle_id)

    # Parent war info
    parent_war = None
    if battle['parent_id']:
        pw = await conn.fetchrow("""
            SELECT id, name FROM history_event_collections
            WHERE world_id = $1 AND id = $2
        """, world_id, battle['parent_id'])
        if pw:
            parent_war = {'id': pw['id'], 'name': pw['name']}

    return {
        'id': battle_id,
        'name': battle['name'],
        'year': battle['start_year'],
        'site': site_name,
        'site_id': battle['site_id'],
        'outcome': bd.get('outcome', 'unknown'),
        'attacker': attacker,
        'defender': defender,
        'attacker_squads': attacker_squads,
        'defender_squads': defender_squads,
        'attacker_participants': a_participants,
        'defender_participants': d_participants,
        'attacker_total': sum(a_numbers) if a_numbers else len(attacking_hfids),
        'defender_total': sum(d_numbers) if d_numbers else len(defending_hfids),
        'attacker_casualties': sum(a_deaths) if a_deaths else 0,
        'defender_casualties': sum(d_deaths) if d_deaths else 0,
        'events': [dict(e) for e in battle_events],
        'event_count': len(battle_events),
        'parent_war': parent_war,
    }


# ── Civilization Rise-and-Fall Narrative ────────────────────────────────────


async def generate_civilization_narrative(
    conn,
    world_id: int,
    entity_id: int,
) -> dict[str, Any]:
    """Generate civilization history narrative.

    Returns dict with: name, race, type, founded_year, sites, wars,
    leader_succession, current_state, summary_text.
    """
    entity = await conn.fetchrow("""
        SELECT id, name, race, type, details
        FROM entities WHERE world_id = $1 AND id = $2
    """, world_id, entity_id)
    if not entity:
        return {'error': f'Entity {entity_id} not found'}

    # Sites owned (current + historical)
    sites = await conn.fetch("""
        SELECT s.id, s.name, s.type, esl.link_type
        FROM entity_site_links esl
        JOIN sites s ON s.world_id = esl.world_id AND s.id = esl.site_id
        WHERE esl.world_id = $1 AND esl.entity_id = $2
        ORDER BY s.type, s.name
    """, world_id, entity_id)

    # Wars fought (as attacker or defender)
    wars = await conn.fetch("""
        SELECT id, name, start_year, end_year,
               attacker_entity_id, defender_entity_id
        FROM history_event_collections
        WHERE world_id = $1 AND type = 'war'
          AND (attacker_entity_id = $2 OR defender_entity_id = $2)
        ORDER BY start_year
    """, world_id, entity_id)

    wars_enriched = []
    for w in wars:
        role = 'aggressor' if w['attacker_entity_id'] == entity_id else 'defender'
        opponent_id = (w['defender_entity_id'] if role == 'aggressor'
                       else w['attacker_entity_id'])
        opponent = await _resolve_entity(conn, world_id, opponent_id)
        wars_enriched.append({
            'id': w['id'],
            'name': w['name'],
            'start_year': w['start_year'],
            'end_year': w['end_year'],
            'role': role,
            'opponent': opponent,
        })

    # Leader succession (position holders)
    leaders = await conn.fetch("""
        SELECT hel.hf_id, hel.link_type, hel.position_name,
               hf.name, hf.race, hf.birth_year, hf.death_year
        FROM hf_entity_links hel
        JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
        WHERE hel.world_id = $1 AND hel.entity_id = $2
          AND hel.link_type IN ('position', 'former position')
        ORDER BY hf.birth_year
    """, world_id, entity_id)

    # Member count
    member_count = await conn.fetchval("""
        SELECT COUNT(*) FROM hf_entity_links
        WHERE world_id = $1 AND entity_id = $2 AND link_type = 'member'
    """, world_id, entity_id)

    # Founded year (first site creation event for this entity)
    founded = await conn.fetchrow("""
        SELECT MIN(year) as year FROM history_events
        WHERE world_id = $1 AND entity_id_1 = $2
          AND event_type IN ('created_site', 'entity_created')
    """, world_id, entity_id)
    founded_year = founded['year'] if founded else None

    # Build summary
    summary_parts = [f"{entity['name']}"]
    if entity['race']:
        summary_parts.append(f"is a {entity['type'] or 'group'} of {entity['race']}s.")
    if founded_year:
        summary_parts.append(f"Founded in year {founded_year}.")
    if member_count:
        summary_parts.append(f"Has {member_count:,} known members.")
    if sites:
        summary_parts.append(f"Controls {len(sites)} site{'s' if len(sites) != 1 else ''}.")
    if wars_enriched:
        summary_parts.append(
            f"Fought in {len(wars_enriched)} war{'s' if len(wars_enriched) != 1 else ''}.")

    return {
        'id': entity_id,
        'name': entity['name'],
        'race': entity['race'],
        'type': entity['type'],
        'founded_year': founded_year,
        'member_count': member_count,
        'sites': [dict(s) for s in sites],
        'site_count': len(sites),
        'wars': wars_enriched,
        'war_count': len(wars_enriched),
        'leaders': [dict(l) for l in leaders],
        'summary_text': ' '.join(summary_parts),
    }


# ── Character Biography Generator ──────────────────────────────────────────


async def generate_character_biography(
    conn,
    world_id: int,
    hf_id: int,
) -> dict[str, Any]:
    """Generate a comprehensive character biography.

    Returns dict with: name, race, sex, birth, death, supernatural,
    career, relationships, achievements, events_summary, biography_text.
    """
    hf = await conn.fetchrow("""
        SELECT id, name, race, caste, sex, birth_year, death_year, death_cause,
               is_deity, is_force, is_vampire, is_necromancer, is_werebeast,
               is_ghost, kill_count, event_count, prominence_score,
               spheres, goals, skills, kills, holds_artifact,
               first_ageless_year, details
        FROM historical_figures
        WHERE world_id = $1 AND id = $2
    """, world_id, hf_id)
    if not hf:
        return {'error': f'HF {hf_id} not found'}

    hf = dict(hf)

    # Relationships (family + social)
    relationships = await conn.fetch("""
        SELECT hl.target_hf_id, hl.link_type, hl.strength,
               hf.name as target_name, hf.race as target_race
        FROM hf_links hl
        JOIN historical_figures hf ON hf.world_id = hl.world_id AND hf.id = hl.target_hf_id
        WHERE hl.world_id = $1 AND hl.hf_id = $2
        ORDER BY hl.link_type
    """, world_id, hf_id)

    # Entity memberships
    memberships = await conn.fetch("""
        SELECT hel.entity_id, hel.link_type, hel.position_name,
               e.name as entity_name, e.type as entity_type
        FROM hf_entity_links hel
        JOIN entities e ON e.world_id = hel.world_id AND e.id = hel.entity_id
        WHERE hel.world_id = $1 AND hel.hf_id = $2
        ORDER BY hel.link_type
    """, world_id, hf_id)

    # Site associations
    site_links = await conn.fetch("""
        SELECT hsl.site_id, hsl.link_type,
               s.name as site_name, s.type as site_type
        FROM hf_site_links hsl
        JOIN sites s ON s.world_id = hsl.world_id AND s.id = hsl.site_id
        WHERE hsl.world_id = $1 AND hsl.hf_id = $2
    """, world_id, hf_id)

    # Artifacts created or held
    artifacts = await conn.fetch("""
        SELECT id, name, details FROM artifacts
        WHERE world_id = $1 AND id = ANY($2::int[])
    """, world_id, hf.get('holds_artifact') or [])

    # Top events by narrative weight
    top_events = await conn.fetch("""
        SELECT he.id, he.year, he.event_type, he.details,
               ne.narrative_weight, ne.emotional_tone
        FROM event_entity_xref x
        JOIN history_events he ON he.world_id = x.world_id AND he.id = x.event_id
        LEFT JOIN narrative_events ne ON ne.world_id = he.world_id AND ne.event_id = he.id
        WHERE x.world_id = $1 AND x.entity_type = 'hf' AND x.entity_id = $2
        ORDER BY COALESCE(ne.narrative_weight, 0) DESC
        LIMIT 20
    """, world_id, hf_id)

    # Supernatural flags
    supernatural = []
    if hf.get('is_deity'):
        spheres = hf.get('spheres') or []
        supernatural.append(f"deity (spheres: {', '.join(spheres)})" if spheres else "deity")
    if hf.get('is_vampire'):
        supernatural.append("vampire")
    if hf.get('is_necromancer'):
        supernatural.append("necromancer")
    if hf.get('is_werebeast'):
        supernatural.append("werebeast")
    if hf.get('is_ghost'):
        supernatural.append("ghost")
    if hf.get('is_force'):
        supernatural.append("force of nature")
    if hf.get('first_ageless_year'):
        supernatural.append(f"became ageless in year {hf['first_ageless_year']}")

    # Death details
    death_info = None
    if hf.get('death_year'):
        cause_text = DeathCauseRenderer.render_hf_cause(
            hf['death_cause']) if hf.get('death_cause') else 'unknown causes'
        age = hf['death_year'] - hf['birth_year'] if hf.get('birth_year') else None
        death_info = {
            'year': hf['death_year'],
            'cause': hf['death_cause'],
            'cause_text': cause_text,
            'age': age,
        }

    # Build biography text
    bio_parts = _build_biography_text(hf, relationships, memberships,
                                       site_links, supernatural, death_info,
                                       top_events)

    return {
        'id': hf_id,
        'name': hf['name'],
        'race': hf['race'],
        'caste': hf.get('caste'),
        'sex': hf.get('sex'),
        'birth_year': hf.get('birth_year'),
        'death_year': hf.get('death_year'),
        'death_info': death_info,
        'prominence_score': hf.get('prominence_score'),
        'kill_count': hf.get('kill_count', 0),
        'event_count': hf.get('event_count', 0),
        'supernatural': supernatural,
        'relationships': [dict(r) for r in relationships],
        'memberships': [dict(m) for m in memberships],
        'site_links': [dict(s) for s in site_links],
        'artifacts': [dict(a) for a in artifacts],
        'top_events': [dict(e) for e in top_events],
        'biography_text': '\n\n'.join(bio_parts),
    }


def _build_biography_text(
    hf: dict,
    relationships: list,
    memberships: list,
    site_links: list,
    supernatural: list,
    death_info: dict | None,
    top_events: list,
) -> list[str]:
    """Construct biography text sections."""
    parts = []

    # Header
    name = hf['name']
    race = (hf.get('race') or 'unknown').replace('_', ' ').lower()
    sex = hf.get('caste', '').lower() if hf.get('caste') else ''
    header = f"{name}, {sex} {race}".strip().rstrip(',')
    if hf.get('birth_year'):
        header += f". Born in year {hf['birth_year']}"
    header += '.'
    parts.append(header)

    # Supernatural nature
    if supernatural:
        parts.append(f"Supernatural nature: {', '.join(supernatural)}.")

    # Career / memberships
    if memberships:
        career_lines = []
        for m in memberships:
            role = m['link_type'].replace('_', ' ')
            career_lines.append(f"{role} of {m['entity_name']} ({m['entity_type']})")
        parts.append("Affiliations: " + '; '.join(career_lines) + '.')

    # Relationships
    family = [r for r in relationships if r['link_type'] in
              ('mother', 'father', 'child', 'spouse')]
    if family:
        family_lines = [f"{r['link_type']}: {r['target_name']}" for r in family]
        parts.append("Family: " + ', '.join(family_lines) + '.')

    other_rels = [r for r in relationships if r['link_type'] not in
                  ('mother', 'father', 'child', 'spouse')]
    if other_rels:
        rel_lines = [f"{r['link_type']}: {r['target_name']}" for r in other_rels[:5]]
        parts.append("Notable bonds: " + ', '.join(rel_lines) + '.')

    # Achievements
    achievements = []
    if hf.get('kill_count') and hf['kill_count'] > 0:
        achievements.append(f"{hf['kill_count']} confirmed kills")
    if hf.get('holds_artifact'):
        achievements.append(f"holds {len(hf['holds_artifact'])} artifact(s)")
    if hf.get('event_count') and hf['event_count'] > 50:
        achievements.append(f"involved in {hf['event_count']} recorded events")
    if achievements:
        parts.append("Achievements: " + ', '.join(achievements) + '.')

    # Key events (top 5 by narrative weight)
    if top_events:
        event_lines = []
        for ev in top_events[:5]:
            etype = (ev['event_type'] or '').replace('_', ' ')
            year = ev.get('year', '?')
            weight = ev.get('narrative_weight')
            w_str = f" (weight: {weight:.1f})" if weight else ""
            event_lines.append(f"Year {year}: {etype}{w_str}")
        parts.append("Key events:\n" + '\n'.join(f"  - {e}" for e in event_lines))

    # Death
    if death_info:
        age_str = f" at the age of {death_info['age']}" if death_info.get('age') else ""
        parts.append(
            f"Death: {death_info['cause_text']}"
            f" in year {death_info['year']}{age_str}.")

    # Site associations
    if site_links:
        sites_str = ', '.join(
            f"{s['site_name']} ({s['link_type']})" for s in site_links[:5])
        parts.append(f"Associated sites: {sites_str}.")

    return parts


# ── Age at Death with Fractions ─────────────────────────────────────────────


def render_age_at_death(
    birth_year: int,
    death_year: int,
    birth_seconds: int = 0,
    death_seconds: int = 0,
) -> str:
    """Render age with 1/4, 1/2, 3/4 fractions."""
    age = death_year - birth_year
    if birth_seconds is not None and death_seconds is not None and death_seconds > 0:
        fraction = (death_seconds - birth_seconds) / 403200  # ticks per year
        if fraction < 0:
            age -= 1
            fraction += 1
        if 0.125 <= fraction < 0.375:
            return f"{age} and a quarter"
        if 0.375 <= fraction < 0.625:
            return f"{age} and a half"
        if 0.625 <= fraction < 0.875:
            return f"{age} and three quarters"
    if age == 0:
        return "less than a year"
    return str(age)


# ── Helper Functions ────────────────────────────────────────────────────────


async def _resolve_entity(conn, world_id: int, entity_id: int | None) -> dict | None:
    if not entity_id:
        return None
    row = await conn.fetchrow(
        "SELECT id, name, race, type FROM entities WHERE world_id = $1 AND id = $2",
        world_id, entity_id)
    return dict(row) if row else None


async def _resolve_site(conn, world_id: int, site_id: int | None) -> str | None:
    if not site_id:
        return None
    row = await conn.fetchrow(
        "SELECT name FROM sites WHERE world_id = $1 AND id = $2",
        world_id, site_id)
    return row['name'] if row else None


async def _resolve_hf_list(conn, world_id: int, hf_ids: list[int]) -> list[dict]:
    if not hf_ids:
        return []
    rows = await conn.fetch("""
        SELECT id, name, race, prominence_score
        FROM historical_figures
        WHERE world_id = $1 AND id = ANY($2::int[])
        ORDER BY COALESCE(prominence_score, 0) DESC
    """, world_id, hf_ids)
    return [dict(r) for r in rows]


def _build_squad_summary(
    races: list,
    numbers: list,
    deaths: list,
) -> list[dict]:
    """Build squad composition summary from parallel arrays."""
    squads = {}
    for i in range(min(len(races), len(numbers), len(deaths))):
        race = str(races[i]).replace('_', ' ').lower()
        if race not in squads:
            squads[race] = {'race': race, 'count': 0, 'deaths': 0}
        squads[race]['count'] += numbers[i] if isinstance(numbers[i], int) else 0
        squads[race]['deaths'] += deaths[i] if isinstance(deaths[i], int) else 0
    return sorted(squads.values(), key=lambda s: s['count'], reverse=True)
