"""Stage 3.5: Fortress State Capture ETL.

Captures high-frequency fortress state, classifies game reports,
tracks threats, records character arcs, and enriches death narratives.

All functions accept an asyncpg Connection (caller manages transactions)
and return counts of rows affected.
"""

import json
import logging
import re
from datetime import datetime, timezone

import asyncpg

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Season Mapping (DF sends int 0-3, schema expects TEXT)
# ═══════════════════════════════════════════════════════════════════════

_SEASON_MAP = {0: 'Spring', 1: 'Summer', 2: 'Autumn', 3: 'Winter'}


def _season_str(raw) -> str:
    """Convert DF season (int or str) to TEXT."""
    if isinstance(raw, int):
        return _SEASON_MAP.get(raw, f'Season_{raw}')
    return str(raw) if raw else 'Unknown'


# ═══════════════════════════════════════════════════════════════════════
# Report Classification
# ═══════════════════════════════════════════════════════════════════════

# Keyword patterns for classifying game reports into categories
_CATEGORY_PATTERNS = [
    # Death — must check before combat (deaths often mention strikes)
    ('death', re.compile(
        r'has died|has been struck down|has been found dead|'
        r'has bled to death|has suffocated|has starved|has drowned|'
        r'has been murdered|was shot and killed|has been killed|'
        r'has been crushed|gave in to his|gave in to her|'
        r'has been missing', re.IGNORECASE)),
    # Diplomacy — must check before migration ("diplomat has arrived")
    ('diplomacy', re.compile(
        r'diplomat|liaison|caravan|merchants|trade|guild rep|'
        r'ambassador|emissary|envoy', re.IGNORECASE)),
    # Combat
    ('combat', re.compile(
        r'strikes|bites|kicks|scratches|bashes|slashes|stabs|'
        r'punches|charges|gores|lashes|hacks|attacks|blocks|'
        r'dodges|misses|grabs|throws|wrestle|choke|'
        r'the .+ collapses|a .+ is fighting', re.IGNORECASE)),
    # Migration
    ('migration', re.compile(
        r'has arrived|have arrived|petition|migrant|immigrant|'
        r'a group of |has come to |visitors have', re.IGNORECASE)),
    # Social
    ('social', re.compile(
        r'elected|mandate|has been promoted|'
        r'has become a |married|given birth|has grown to|'
        r'has been re-elected|party|celebration|'
        r'has created a |artifact', re.IGNORECASE)),
    # Economic
    ('economic', re.compile(
        r'crafted|masterwork|constructed|mined|designated|'
        r'hauled|planted|harvested|brewed|cooked|smelted|forged',
        re.IGNORECASE)),
    # Environmental
    ('environmental', re.compile(
        r'weather|season|spring|summer|autumn|winter|'
        r'it has started raining|the waterfall|cave-in|'
        r'a .+ has been spotted|magma|flood|fire|'
        r'forgotten beast|titan|dragon|giant', re.IGNORECASE)),
]


def classify_report(text: str) -> str:
    """Classify a game report text into a category.

    Returns the first matching category, or 'other' if no match.
    """
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return 'other'


# Combat report parsing patterns
_COMBAT_ATTACKER = re.compile(
    r'^The (.+?) (strikes|bites|kicks|scratches|bashes|slashes|'
    r'stabs|punches|charges|gores|lashes|hacks|attacks|'
    r'grabs|throws|misses)', re.IGNORECASE)
_COMBAT_DEFENDER = re.compile(
    r'(?:strikes|bites|kicks|scratches|bashes|slashes|stabs|'
    r'punches|charges|gores|lashes|hacks|attacks|grabs|throws|misses)'
    r'\s+(?:the\s+)?(.+?)(?:\s+in\s+the\s+|\s*!|\s*,|\s*$)', re.IGNORECASE)
_BODY_PART = re.compile(
    r'in the ([\w\s]+?)(?:\s*!|\s*,|\s+with|\s+and|\s*$)', re.IGNORECASE)
_WEAPON = re.compile(
    r'with (?:his|her|its|the) (.+?)(?:\s*!|\s*,|\s*$)', re.IGNORECASE)
_ATTACK_TYPE_MAP = {
    'strikes': 'strike', 'bites': 'bite', 'kicks': 'kick',
    'scratches': 'scratch', 'bashes': 'bash', 'slashes': 'slash',
    'stabs': 'stab', 'punches': 'punch', 'charges': 'charge',
    'gores': 'gore', 'lashes': 'lash', 'hacks': 'hack',
    'attacks': 'attack', 'grabs': 'grab', 'throws': 'throw',
    'misses': 'miss',
}


def parse_combat_report(text: str) -> dict:
    """Extract structured fields from a combat report text.

    Returns dict with optional keys: attack_type, body_part, weapon.
    Attacker/defender names are extracted but unit_id resolution
    happens separately via name matching.
    """
    result = {}

    # Attack type
    m = _COMBAT_ATTACKER.search(text)
    if m:
        result['attacker_name'] = m.group(1).strip()
        verb = m.group(2).lower()
        result['attack_type'] = _ATTACK_TYPE_MAP.get(verb, verb)

    # Defender
    m = _COMBAT_DEFENDER.search(text)
    if m:
        result['defender_name'] = m.group(1).strip()

    # Body part
    m = _BODY_PART.search(text)
    if m:
        result['body_part'] = m.group(1).strip()

    # Weapon
    m = _WEAPON.search(text)
    if m:
        result['weapon'] = m.group(1).strip()

    return result


# ═══════════════════════════════════════════════════════════════════════
# Happiness Classification
# ═══════════════════════════════════════════════════════════════════════

def _classify_happiness(stress: int | None) -> str:
    """Classify a stress level into a happiness category.

    DF stress ranges (lower is happier):
    - <  -100000: ecstatic
    - < -25000: happy
    - < 25000: content
    - < 100000: unhappy
    - >= 100000: miserable
    """
    if stress is None:
        return 'unknown'
    if stress < -100000:
        return 'ecstatic'
    if stress < -25000:
        return 'happy'
    if stress < 25000:
        return 'content'
    if stress < 100000:
        return 'unhappy'
    return 'miserable'


def compute_happiness_distribution(units: list[dict]) -> dict:
    """Compute happiness distribution from bridge unit_summary data.

    Returns dict like {"ecstatic": 3, "happy": 5, "content": 4, ...}
    """
    dist = {'ecstatic': 0, 'happy': 0, 'content': 0,
            'unhappy': 0, 'miserable': 0, 'unknown': 0}
    for u in units:
        cat = _classify_happiness(u.get('stress'))
        dist[cat] = dist.get(cat, 0) + 1
    # Remove zero/unknown entries for cleaner JSON
    return {k: v for k, v in dist.items() if v > 0 and k != 'unknown'}


# ═══════════════════════════════════════════════════════════════════════
# ETL Functions
# ═══════════════════════════════════════════════════════════════════════


async def etl_fortress_state_snapshot(
    conn: asyncpg.Connection,
    bridge_data: dict,
    world_id: int,
    game_year: int | None,
    game_tick: int | None,
) -> int:
    """Capture a high-frequency fortress state snapshot.

    Promotes bridge fortress_state + unit_summary sections into
    fortress_state_snapshots table.

    Returns 1 if inserted, 0 if skipped.
    """
    fs = bridge_data.get('fortress_state') or {}
    if not fs:
        return 0

    # Population from fortress_state (most accurate)
    population = fs.get('population')

    # Military count: count members in fortress squads only
    # Filter by group_id (site government entity) from fortress_state
    military_count = 0
    fortress_group = fs.get('group_id')
    squads = bridge_data.get('squads') or {}
    for sq in (squads.get('squads') if isinstance(squads, dict) else squads) or []:
        # Only count squads belonging to our fortress entity
        if fortress_group is not None and sq.get('entity_id') != fortress_group:
            continue
        members = sq.get('members', [])
        military_count += len(members)

    # Food/drink: prefer fortress_state (v9.1+), fall back to buildings
    food_stocks = fs.get('food_stocks')
    drink_stocks = fs.get('drink_stocks')
    if food_stocks is None:
        buildings = bridge_data.get('buildings') or {}
        food_stocks = buildings.get('food_count') if isinstance(buildings, dict) else None
    if drink_stocks is None:
        buildings = bridge_data.get('buildings') or {}
        drink_stocks = buildings.get('drink_count') if isinstance(buildings, dict) else None

    # Wealth
    wealth = fs.get('wealth_total')

    # Happiness distribution from unit_summary
    unit_summary = bridge_data.get('unit_summary') or {}
    units_list = ((unit_summary.get('fortress_units') or unit_summary.get('units'))
                  if isinstance(unit_summary, dict) else unit_summary) or []
    happiness = compute_happiness_distribution(
        units_list if isinstance(units_list, list) else [])

    # Threats from threat_tracking bridge section (if available)
    threat_data = bridge_data.get('threat_tracking') or {}
    threats = None
    if threat_data:
        threats = []
        for ttype in ('undead', 'invader', 'megabeast', 'wildlife'):
            count = threat_data.get(f'{ttype}_count', 0)
            if count > 0:
                threats.append({'type': ttype, 'count': count})

    season_raw = bridge_data.get('cur_season')
    season = _season_str(season_raw)
    tick = game_tick or 0

    await conn.execute(
        """
        INSERT INTO fortress_state_snapshots
            (world_id, tick, year, season, population, military_count,
             food_stocks, drink_stocks, wealth, happiness_distribution, threats)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (world_id, tick) DO NOTHING
        """,
        world_id, tick, game_year or 0, season,
        population, military_count, food_stocks, drink_stocks,
        wealth, happiness, threats,
    )
    return 1


async def etl_classify_reports(
    conn: asyncpg.Connection,
    world_id: int,
) -> int:
    """Classify unclassified game_reports with category + combat fields.

    Processes all reports where category IS NULL.
    Returns count of reports classified.
    """
    rows = await conn.fetch(
        """
        SELECT id, text, report_type FROM game_reports
        WHERE world_id = $1 AND category IS NULL
        ORDER BY id
        LIMIT 500
        """,
        world_id,
    )
    if not rows:
        return 0

    count = 0
    for row in rows:
        text = row['text']
        category = classify_report(text)

        # Parse combat fields if this is a combat report
        attacker_uid = None
        defender_uid = None
        body_part = None
        attack_type = None
        weapon = None

        if category == 'combat':
            parsed = parse_combat_report(text)
            body_part = parsed.get('body_part')
            attack_type = parsed.get('attack_type')
            weapon = parsed.get('weapon')

        await conn.execute(
            """
            UPDATE game_reports SET
                category = $2,
                body_part = $3,
                attack_type = $4,
                weapon = $5
            WHERE id = $1
            """,
            row['id'], category, body_part, attack_type, weapon,
        )
        count += 1

    if count:
        log.info("etl_classify_reports: %d reports classified", count)
    return count


async def etl_threat_tracking(
    conn: asyncpg.Connection,
    bridge_data: dict,
    world_id: int,
    game_tick: int | None,
) -> int:
    """Record threat level snapshot from bridge data.

    Counts hostile units from unit_summary (active_invader flag, undead race).
    Returns 1 if inserted, 0 if skipped.
    """
    unit_summary = bridge_data.get('unit_summary') or {}
    units_list = ((unit_summary.get('fortress_units') or unit_summary.get('units'))
                  if isinstance(unit_summary, dict) else unit_summary) or []
    if not isinstance(units_list, list):
        units_list = []

    hostile_count = 0
    undead_count = 0
    invader_count = 0
    megabeast_count = 0
    details = []

    for u in units_list:
        is_hostile = False

        if u.get('active_invader'):
            invader_count += 1
            is_hostile = True

        race = str(u.get('race_name', '')).lower()
        if 'zombie' in race or 'skeleton' in race or 'undead' in race:
            undead_count += 1
            is_hostile = True

        # Megabeasts are typically identified by size/type flags
        if u.get('is_megabeast') or u.get('is_titan'):
            megabeast_count += 1
            is_hostile = True

        if is_hostile:
            hostile_count += 1
            details.append({
                'unit_id': u.get('id'),
                'race': u.get('race_name'),
                'name': u.get('name'),
            })

    # Also check armies section for approaching threats
    armies = bridge_data.get('armies') or {}
    army_list = (armies.get('armies') if isinstance(armies, dict)
                 else armies) or []
    if isinstance(army_list, list):
        for army in army_list:
            members = army.get('member_count', 0)
            if members > 0:
                hostile_count += members
                details.append({
                    'type': 'army',
                    'army_id': army.get('id'),
                    'member_count': members,
                    'pos': army.get('pos'),
                })

    tick = game_tick or 0

    await conn.execute(
        """
        INSERT INTO threat_tracking
            (world_id, tick, hostile_count, undead_count, invader_count,
             megabeast_count, threat_details)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (world_id, tick) DO NOTHING
        """,
        world_id, tick,
        hostile_count, undead_count, invader_count, megabeast_count,
        details if details else None,
    )
    return 1 if hostile_count > 0 else 0


async def etl_character_arcs(
    conn: asyncpg.Connection,
    bridge_data: dict,
    world_id: int,
    game_year: int | None,
    game_tick: int | None,
    recent_events: list[dict] | None = None,
) -> int:
    """Capture per-unit development snapshots with delta detection.

    Only writes a snapshot when meaningful change detected:
    - Skill rating increase
    - Stress change > 5000
    - Profession change
    - Squad assignment change

    Returns count of snapshots written.
    """
    unit_summary = bridge_data.get('unit_summary') or {}
    units_list = ((unit_summary.get('fortress_units') or unit_summary.get('units'))
                  if isinstance(unit_summary, dict) else unit_summary) or []
    if not isinstance(units_list, list):
        return 0

    # Get dwarf skills from bridge
    # Bridge format: {dwarf_count: N, dwarves: [{id, skills: [...]}]}
    # OR legacy: {uid_str: [skills]} or [{unit_id, skills}]
    skills_data = bridge_data.get('dwarf_skills') or {}
    skills_by_unit = {}
    if isinstance(skills_data, dict):
        # New format: {dwarves: [{id, skills}]}
        if 'dwarves' in skills_data:
            for entry in (skills_data.get('dwarves') or []):
                uid = entry.get('id')
                if uid is not None:
                    skills_by_unit[uid] = entry.get('skills', [])
        else:
            # Legacy format: {uid_str: [skills]}
            for uid_str, skill_list in skills_data.items():
                try:
                    skills_by_unit[int(uid_str)] = skill_list
                except (ValueError, TypeError):
                    pass
    elif isinstance(skills_data, list):
        for entry in skills_data:
            uid = entry.get('unit_id') or entry.get('id')
            if uid is not None:
                skills_by_unit[uid] = entry.get('skills', [])

    # Get squad assignments
    squads = bridge_data.get('squads') or {}
    squad_list = (squads.get('squads') if isinstance(squads, dict)
                  else squads) or []
    unit_squad = {}
    if isinstance(squad_list, list):
        for sq in squad_list:
            sq_id = sq.get('id')
            for member_id in (sq.get('members') or []):
                if isinstance(member_id, int):
                    unit_squad[member_id] = sq_id

    # Build notable events by unit from recent_events
    events_by_unit = {}
    for ev in (recent_events or []):
        uid = ev.get('unit_id')
        if uid:
            events_by_unit.setdefault(uid, []).append(
                ev.get('event_type', 'unknown'))

    tick = game_tick or 0
    count = 0

    for u in units_list:
        uid = u.get('id')
        if uid is None:
            continue

        stress = u.get('stress')
        raw_prof = u.get('profession')
        profession = str(raw_prof) if raw_prof is not None else None
        squad_id = unit_squad.get(uid)

        # Build skill snapshot
        unit_skills = skills_by_unit.get(uid, [])
        skill_snap = {}
        if isinstance(unit_skills, list):
            for sk in unit_skills:
                name = sk.get('name') or sk.get('id')
                if name:
                    skill_snap[str(name)] = {
                        'rating': sk.get('rating', 0),
                        'xp': sk.get('experience', sk.get('xp', 0)),
                    }
        elif isinstance(unit_skills, dict):
            skill_snap = unit_skills

        # Delta detection: check last snapshot for this unit
        last = await conn.fetchrow(
            """
            SELECT stress_level, profession, squad_id, skill_snapshot
            FROM character_arcs
            WHERE world_id = $1 AND unit_id = $2
            ORDER BY tick DESC LIMIT 1
            """,
            world_id, uid,
        )

        if last:
            changed = False
            # Stress change > 5000
            if (stress is not None and last['stress_level'] is not None
                    and abs(stress - last['stress_level']) > 5000):
                changed = True
            # Profession change
            if profession and profession != last['profession']:
                changed = True
            # Squad change
            if squad_id != last['squad_id']:
                changed = True
            # Skill rating increase (any skill)
            old_skills = last['skill_snapshot'] or {}
            if isinstance(old_skills, str):
                try:
                    old_skills = json.loads(old_skills)
                except (json.JSONDecodeError, TypeError):
                    old_skills = {}
            for sk_name, sk_val in skill_snap.items():
                old_rating = (old_skills.get(sk_name, {}).get('rating', 0)
                              if isinstance(old_skills.get(sk_name), dict) else 0)
                if sk_val.get('rating', 0) > old_rating:
                    changed = True
                    break
            # Notable events always trigger
            if uid in events_by_unit:
                changed = True

            if not changed:
                continue

        happiness = _classify_happiness(stress)
        notable = events_by_unit.get(uid)

        await conn.execute(
            """
            INSERT INTO character_arcs
                (world_id, unit_id, tick, year, stress_level, happiness,
                 skill_snapshot, profession, squad_id,
                 notable_events_since_last)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (world_id, unit_id, tick) DO NOTHING
            """,
            world_id, uid, tick, game_year or 0,
            stress, happiness, skill_snap, profession, squad_id,
            notable,
        )
        count += 1

    if count:
        log.info("etl_character_arcs: %d snapshots written", count)
    return count


async def etl_environmental_state(
    conn: asyncpg.Connection,
    bridge_data: dict,
    world_id: int,
    game_year: int | None,
    game_tick: int | None,
) -> int:
    """Capture environmental state on season transitions.

    Returns 1 if inserted, 0 if skipped.
    """
    season_raw = bridge_data.get('cur_season')
    if season_raw is None:
        return 0
    season = _season_str(season_raw)

    tick = game_tick or 0

    # Fortress depth and weather from bridge fortress_state
    fs = bridge_data.get('fortress_state') or {}
    fortress_depth = fs.get('fortress_depth')
    weather = str(fs.get('weather_type')) if fs.get('weather_type') is not None else None

    # Features discovered: from bridge if available
    features = fs.get('features_discovered')

    await conn.execute(
        """
        INSERT INTO environmental_state
            (world_id, tick, year, season, fortress_depth,
             weather, features_discovered)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (world_id, tick) DO NOTHING
        """,
        world_id, tick, game_year or 0, season,
        fortress_depth, weather, features,
    )
    return 1


async def etl_session_marker(
    conn: asyncpg.Connection,
    world_id: int,
    game_tick: int | None,
    event_type: str,
    fortress_state_data: dict | None = None,
) -> int:
    """Record a session boundary marker.

    Called on season changes, year changes, and game save/load events.
    Returns 1 if inserted, 0 if skipped.
    """
    tick = game_tick or 0

    await conn.execute(
        """
        INSERT INTO session_markers
            (world_id, tick, event_type, fortress_state_at_marker)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (world_id, tick, event_type) DO NOTHING
        """,
        world_id, tick, event_type, fortress_state_data,
    )
    return 1


async def etl_death_narrative(
    conn: asyncpg.Connection,
    world_id: int,
    unit_id: int,
    hf_id: int | None,
    game_year: int | None,
    game_tick: int | None,
    death_data: dict | None = None,
) -> int:
    """Create an enriched death narrative from reactive event data.

    Pulls combat reports from the 200 ticks before death, identifies
    killer and witnesses, and assembles the incident chain.

    Returns 1 if inserted, 0 if skipped.
    """
    tick = game_tick or 0
    cause = 'unknown'
    killer_unit_id = None
    killer_race = None
    weapon = None
    body_part = None
    combat_report_ids = []
    witness_unit_ids = []
    location = None

    if death_data:
        cause = str(death_data.get('cause', 'unknown'))
        killer_unit_id = death_data.get('killer_unit_id')
        raw_race = death_data.get('killer_race')
        killer_race = str(raw_race) if raw_race is not None else None
        weapon = str(death_data.get('weapon')) if death_data.get('weapon') else None
        location = str(death_data.get('location')) if death_data.get('location') else None

    # Find combat reports in the 200 ticks before death
    if tick > 0:
        reports = await conn.fetch(
            """
            SELECT id, report_id, text, attacker_unit_id, defender_unit_id,
                   body_part, weapon
            FROM game_reports
            WHERE world_id = $1
              AND game_tick BETWEEN $2 AND $3
              AND category = 'combat'
            ORDER BY game_tick DESC, report_id DESC
            LIMIT 50
            """,
            world_id, max(0, tick - 200), tick,
        )

        for rpt in reports:
            combat_report_ids.append(rpt['report_id'])
            # Identify reports involving this unit as defender
            if rpt['defender_unit_id'] == unit_id:
                if not killer_unit_id and rpt['attacker_unit_id']:
                    killer_unit_id = rpt['attacker_unit_id']
                if not body_part and rpt['body_part']:
                    body_part = rpt['body_part']
                if not weapon and rpt['weapon']:
                    weapon = rpt['weapon']

        # Witnesses: other units involved in combat reports during this period
        if combat_report_ids:
            witness_rows = await conn.fetch(
                """
                SELECT DISTINCT attacker_unit_id AS uid FROM game_reports
                WHERE world_id = $1 AND report_id = ANY($2::int[])
                  AND attacker_unit_id IS NOT NULL
                  AND attacker_unit_id != $3
                UNION
                SELECT DISTINCT defender_unit_id FROM game_reports
                WHERE world_id = $1 AND report_id = ANY($2::int[])
                  AND defender_unit_id IS NOT NULL
                  AND defender_unit_id != $3
                """,
                world_id, combat_report_ids, unit_id,
            )
            witness_unit_ids = [r['uid'] for r in witness_rows if r['uid']]

    await conn.execute(
        """
        INSERT INTO death_narratives
            (world_id, unit_id, hf_id, tick, year, cause,
             killer_unit_id, killer_race, weapon, body_part,
             combat_report_ids, witness_unit_ids, location)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        ON CONFLICT (world_id, unit_id, tick) DO NOTHING
        """,
        world_id, unit_id, hf_id, tick, game_year or 0, cause,
        killer_unit_id, killer_race, weapon, body_part,
        combat_report_ids if combat_report_ids else None,
        witness_unit_ids if witness_unit_ids else None,
        location,
    )
    log.info("death_narrative: unit %d — cause=%s, killer=%s, %d combat reports",
             unit_id, cause, killer_unit_id, len(combat_report_ids))
    return 1


# ═══════════════════════════════════════════════════════════════════════
# Main Orchestrator
# ═══════════════════════════════════════════════════════════════════════

async def ingest_state_capture(
    conn: asyncpg.Connection,
    bridge_data: dict,
    world_id: int,
    game_year: int | None = None,
    game_tick: int | None = None,
    season_changed: bool = False,
    year_changed: bool = False,
    recent_events: list[dict] | None = None,
    snapshot_interval: int = 200,
    last_snapshot_tick: int = 0,
) -> dict:
    """Run all Stage 3.5 ETL functions on bridge data.

    Args:
        conn: Active asyncpg connection
        bridge_data: Full bridge cycle JSON
        world_id: Target world ID
        game_year: Current in-game year
        game_tick: Current in-game tick
        season_changed: True if season boundary crossed
        year_changed: True if year boundary crossed
        recent_events: Detected change events from this cycle
        snapshot_interval: Tick interval for state snapshots (default 200)
        last_snapshot_tick: Tick of the last state snapshot

    Returns:
        Summary dict with counts per function + 'last_snapshot_tick'.
    """
    summary = {}
    tick = game_tick or 0

    async def _safe(name, coro):
        try:
            summary[name] = await coro
        except Exception as e:
            log.warning("state_capture_%s failed: %s", name, e)
            summary[name] = 0

    # 1. Fortress state snapshot (every snapshot_interval ticks)
    if tick - last_snapshot_tick >= snapshot_interval:
        await _safe('fortress_snapshot', etl_fortress_state_snapshot(
            conn, bridge_data, world_id, game_year, game_tick))
        if summary.get('fortress_snapshot', 0) > 0:
            summary['last_snapshot_tick'] = tick

    # 2. Classify new game reports
    await _safe('classify_reports', etl_classify_reports(conn, world_id))

    # 3. Threat tracking (every cycle — cheap)
    await _safe('threat_tracking', etl_threat_tracking(
        conn, bridge_data, world_id, game_tick))

    # 4. Character arcs (every cycle — delta detection skips no-change units)
    await _safe('character_arcs', etl_character_arcs(
        conn, bridge_data, world_id, game_year, game_tick, recent_events))

    # 5. Environmental state (on season change)
    if season_changed:
        await _safe('environmental_state', etl_environmental_state(
            conn, bridge_data, world_id, game_year, game_tick))

    # 6. Session markers (on season/year change)
    if season_changed:
        fs = bridge_data.get('fortress_state') or {}
        await _safe('session_marker_season', etl_session_marker(
            conn, world_id, game_tick, 'season_change', fs))
    if year_changed:
        fs = bridge_data.get('fortress_state') or {}
        await _safe('session_marker_year', etl_session_marker(
            conn, world_id, game_tick, 'year_change', fs))

    # 7. Death narratives — from both detector events AND reactive bridge deaths
    death_count = 0
    processed_death_units = set()

    # 7a. From change detector events
    for ev in (recent_events or []):
        if ev.get('event_type') in ('DIED', 'DEATH', 'death'):
            uid = ev.get('unit_id', 0)
            processed_death_units.add(uid)
            await _safe(f'death_{death_count}', etl_death_narrative(
                conn, world_id, uid,
                ev.get('hf_id'),
                game_year, game_tick,
                ev.get('death_data'),
            ))
            death_count += 1

    # 7b. From bridge reactive_events.unit_deaths (enriched with cause)
    reactive = bridge_data.get('reactive_events', {})
    for rd in (reactive.get('unit_deaths') or []):
        uid = rd.get('unit_id', 0)
        if uid in processed_death_units:
            continue  # Already handled above
        processed_death_units.add(uid)
        death_data = {
            'cause': rd.get('death_cause', 'unknown'),
            'killer_unit_id': rd.get('killer_unit_id'),
            'killer_race': rd.get('killer_race'),
            'weapon': rd.get('weapon'),
        }
        await _safe(f'death_{death_count}', etl_death_narrative(
            conn, world_id, uid,
            rd.get('hf_id'),
            game_year, rd.get('tick') or game_tick,
            death_data,
        ))
        death_count += 1

    if death_count:
        summary['death_narratives'] = death_count

    # Log active results
    active = {k: v for k, v in summary.items() if v}
    if active:
        log.info("State capture: %s", active)

    return summary
