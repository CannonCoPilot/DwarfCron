"""Fortress Denizen Registry — tracks every being who touches the fortress.

The denizen registry serves as:
1. LLM Gateway: Starting point for agentic storyteller queries
2. Narrative Value Scoring: Prioritizes characters by storytelling importance
3. Death/Absence Tracking: Detects silent deaths via last_seen_tick gaps

Population sources:
- Watcher poll cycles (unit_summary bridge section)
- First watcher cycle = embark detection (all initial units → embark=TRUE)
- Later cycles: new units → resident, missing units → missing, dead → deceased
"""

import json
import logging
from datetime import datetime, timezone

import asyncpg

log = logging.getLogger(__name__)

# Missing cycle threshold before escalating to 'missing'
MISSING_CYCLE_THRESHOLD = 3


async def has_denizens(conn: asyncpg.Connection, world_id: int) -> bool:
    """Check if any denizens exist for this world (used for embark detection)."""
    return await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM fortress_denizens WHERE world_id = $1)",
        world_id,
    )


async def register_denizen(
    conn: asyncpg.Connection,
    world_id: int,
    unit: dict,
    *,
    is_embark: bool = False,
    game_year: int | None = None,
    game_tick: int | None = None,
) -> int | None:
    """Register or update a denizen from a unit dict.

    Returns the denizen ID (from INSERT or existing row).
    """
    unit_id = unit['id']
    name = unit.get('name') or f"Unit {unit_id}"
    english_name = unit.get('details', {}).get('english_name')
    race = str(unit.get('race_name', unit.get('race', '')))
    hf_id = unit.get('hist_fig_id')

    now = datetime.now(timezone.utc)

    # Try insert; on conflict update last_seen and status if needed
    row = await conn.fetchrow(
        """
        INSERT INTO fortress_denizens
            (world_id, unit_id, hf_id, name, english_name, race,
             status, embark, arrival_year, arrival_tick,
             last_seen_tick, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6,
                'resident', $7, $8, $9,
                $10, $11)
        ON CONFLICT (world_id, unit_id) DO UPDATE SET
            name = COALESCE(EXCLUDED.name, fortress_denizens.name),
            english_name = COALESCE(EXCLUDED.english_name, fortress_denizens.english_name),
            race = COALESCE(EXCLUDED.race, fortress_denizens.race),
            hf_id = COALESCE(EXCLUDED.hf_id, fortress_denizens.hf_id),
            last_seen_tick = EXCLUDED.last_seen_tick,
            updated_at = EXCLUDED.updated_at
        RETURNING id
        """,
        world_id,
        unit_id,
        hf_id if hf_id and hf_id > 0 else None,
        name,
        english_name,
        race,
        is_embark,
        game_year,
        game_tick,
        game_tick,
        now,
    )
    return row['id'] if row else None


async def update_denizen_status(
    conn: asyncpg.Connection,
    world_id: int,
    unit_id: int,
    new_status: str,
    *,
    cause: str | None = None,
    game_year: int | None = None,
    game_tick: int | None = None,
) -> bool:
    """Update a denizen's status with optional departure metadata.

    Returns True if the row was updated.
    """
    now = datetime.now(timezone.utc)

    if new_status in ('deceased', 'departed', 'missing'):
        result = await conn.execute(
            """
            UPDATE fortress_denizens
            SET status = $3,
                departure_year = COALESCE($4, departure_year),
                departure_tick = COALESCE($5, departure_tick),
                departure_cause = COALESCE($6, departure_cause),
                updated_at = $7
            WHERE world_id = $1 AND unit_id = $2
              AND status NOT IN ('deceased')
            """,
            world_id, unit_id, new_status,
            game_year, game_tick, cause, now,
        )
    else:
        result = await conn.execute(
            """
            UPDATE fortress_denizens
            SET status = $3, updated_at = $4
            WHERE world_id = $1 AND unit_id = $2
            """,
            world_id, unit_id, new_status, now,
        )
    # result is like "UPDATE 1" or "UPDATE 0"
    return result.endswith('1') if result else False


async def mark_seen(
    conn: asyncpg.Connection,
    world_id: int,
    unit_ids: list[int],
    game_tick: int | None = None,
) -> int:
    """Bulk-update last_seen_tick for a list of unit IDs.

    Returns the count of rows updated.
    """
    if not unit_ids:
        return 0
    now = datetime.now(timezone.utc)
    result = await conn.execute(
        """
        UPDATE fortress_denizens
        SET last_seen_tick = $3, updated_at = $4
        WHERE world_id = $1 AND unit_id = ANY($2::int[])
        """,
        world_id, unit_ids, game_tick, now,
    )
    return int(result.split()[-1]) if result else 0


async def detect_missing(
    conn: asyncpg.Connection,
    world_id: int,
    current_unit_ids: set[int],
    game_year: int | None = None,
    game_tick: int | None = None,
) -> list[dict]:
    """Find denizens who were residents but are no longer in the unit list.

    Returns list of {unit_id, name, status} for newly missing denizens.
    """
    # Get all current residents
    residents = await conn.fetch(
        """
        SELECT unit_id, name, details
        FROM fortress_denizens
        WHERE world_id = $1 AND status = 'resident' AND unit_id IS NOT NULL
        """,
        world_id,
    )

    missing = []
    now = datetime.now(timezone.utc)
    for row in residents:
        uid = row['unit_id']
        if uid not in current_unit_ids:
            # This resident is no longer in the unit list
            details = json.loads(row['details']) if row['details'] else {}
            miss_count = details.get('consecutive_missing', 0) + 1
            details['consecutive_missing'] = miss_count

            if miss_count >= MISSING_CYCLE_THRESHOLD:
                # Escalate to missing status
                await conn.execute(
                    """
                    UPDATE fortress_denizens
                    SET status = 'missing',
                        departure_year = COALESCE(departure_year, $3),
                        departure_tick = COALESCE(departure_tick, $4),
                        departure_cause = 'unknown',
                        details = $5,
                        updated_at = $6
                    WHERE world_id = $1 AND unit_id = $2
                      AND status = 'resident'
                    """,
                    world_id, uid, game_year, game_tick,
                    json.dumps(details), now,
                )
                missing.append({
                    'unit_id': uid,
                    'name': row['name'],
                    'status': 'missing',
                    'consecutive_missing': miss_count,
                })
                log.warning("Denizen %s (unit %d) → MISSING after %d cycles",
                            row['name'], uid, miss_count)
            else:
                # Just increment the counter, don't change status yet
                await conn.execute(
                    """
                    UPDATE fortress_denizens
                    SET details = $3, updated_at = $4
                    WHERE world_id = $1 AND unit_id = $2
                    """,
                    world_id, uid, json.dumps(details), now,
                )

    return missing


async def detect_deaths(
    conn: asyncpg.Connection,
    world_id: int,
    units: list[dict],
    game_year: int | None = None,
    game_tick: int | None = None,
) -> list[dict]:
    """Detect is_alive=False transitions for registered denizens.

    Checks units where is_alive is False and the denizen status is still
    'resident' or 'missing'. Returns list of confirmed deaths.
    """
    deaths = []
    for unit in units:
        if unit.get('is_alive', True):
            continue
        uid = unit['id']
        updated = await update_denizen_status(
            conn, world_id, uid, 'deceased',
            cause='death',
            game_year=game_year,
            game_tick=game_tick,
        )
        if updated:
            deaths.append({
                'unit_id': uid,
                'name': unit.get('name', f'Unit {uid}'),
                'status': 'deceased',
            })
            log.info("Denizen %s (unit %d) → DECEASED",
                     unit.get('name'), uid)
    return deaths


async def restore_resident(
    conn: asyncpg.Connection,
    world_id: int,
    unit_id: int,
) -> bool:
    """Restore a missing denizen back to resident (reappeared in unit list).

    Clears consecutive_missing counter. Returns True if updated.
    """
    now = datetime.now(timezone.utc)
    result = await conn.execute(
        """
        UPDATE fortress_denizens
        SET status = 'resident',
            departure_year = NULL,
            departure_tick = NULL,
            departure_cause = NULL,
            details = details - 'consecutive_missing',
            updated_at = $3
        WHERE world_id = $1 AND unit_id = $2
          AND status = 'missing'
        """,
        world_id, unit_id, now,
    )
    return result.endswith('1') if result else False


async def compute_nvs(
    conn: asyncpg.Connection,
    world_id: int,
    total_cycles: int,
) -> int:
    """Recompute Narrative Value Scores for all denizens in a world.

    Formula (from PRD v2.1 Section 3):
      NVS = (screen_time * 0.30) + (event_density * 0.25) +
            (relationship_depth * 0.20) + (recency * 0.15) +
            (status_weight * 0.10)

    Each component is normalized to 0-100 range before weighting.

    Returns number of denizens updated.
    """
    if total_cycles < 1:
        return 0

    denizens = await conn.fetch(
        """
        SELECT d.id, d.unit_id, d.hf_id, d.status, d.last_seen_tick
        FROM fortress_denizens d
        WHERE d.world_id = $1
        """,
        world_id,
    )
    if not denizens:
        return 0

    # Get the latest game tick for recency calculation
    latest_tick = await conn.fetchval(
        "SELECT MAX(game_tick) FROM sync_snapshots WHERE world_id = $1",
        world_id,
    )
    latest_tick = latest_tick or 0

    # Status weight map
    status_weights = {
        'resident': 1.0,
        'deceased': 0.8,
        'missing': 0.7,
        'departed': 0.5,
        'visitor': 0.5,
        'attacker': 0.4,
        'skulker': 0.3,
        'historical': 0.3,
        'unknown': 0.1,
    }

    now = datetime.now(timezone.utc)
    count = 0

    for d in denizens:
        # Screen time: fraction of cycles this denizen was observed
        # (approximated via presence of last_seen_tick vs total_cycles)
        screen_time = min(100.0, (1.0 / max(1, total_cycles)) * 100.0 * total_cycles)
        # Better: use unit_events count as proxy for observation frequency
        if d['unit_id']:
            obs_count = await conn.fetchval(
                "SELECT COUNT(*) FROM unit_events WHERE unit_id = $1 AND world_id = $2",
                d['unit_id'], world_id,
            )
            # Normalize: 10+ events = max screen_time
            screen_time = min(100.0, (obs_count or 0) * 10.0)

        # Event density: count of historical events involving this entity
        event_count = 0
        if d['hf_id']:
            event_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM history_events
                WHERE world_id = $1 AND (hf_id_1 = $2 OR hf_id_2 = $2)
                """,
                world_id, d['hf_id'],
            ) or 0
        # Normalize: 50+ events = max
        event_density = min(100.0, event_count * 2.0)

        # Relationship depth: count of hf_links + entity_links
        rel_count = 0
        if d['hf_id']:
            rel_count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM hf_links WHERE world_id = $1 AND (hf_id = $2 OR target_hf_id = $2)
                    UNION ALL
                    SELECT 1 FROM hf_entity_links WHERE world_id = $1 AND hf_id = $2
                ) sub
                """,
                world_id, d['hf_id'],
            ) or 0
        # Normalize: 20+ relationships = max
        relationship_depth = min(100.0, rel_count * 5.0)

        # Recency: inverse of ticks since last observation
        recency = 0.0
        if d['last_seen_tick'] is not None and latest_tick > 0:
            ticks_ago = max(0, latest_tick - d['last_seen_tick'])
            # Full score if seen this tick, decays over ~100K ticks
            recency = max(0.0, 100.0 - (ticks_ago / 1000.0))

        # Status weight
        sw = status_weights.get(d['status'], 0.1) * 100.0

        # Weighted sum
        nvs = (
            screen_time * 0.30
            + event_density * 0.25
            + relationship_depth * 0.20
            + recency * 0.15
            + sw * 0.10
        )
        nvs = round(min(100.0, max(0.0, nvs)), 2)

        await conn.execute(
            """
            UPDATE fortress_denizens
            SET narrative_value = $3, updated_at = $4
            WHERE id = $1 AND world_id = $2
            """,
            d['id'], world_id, nvs, now,
        )
        count += 1

    return count


async def get_fortress_denizens(
    conn: asyncpg.Connection,
    world_id: int,
    *,
    status_filter: str | None = None,
    sort_by: str = 'narrative_value',
    limit: int = 100,
) -> list[dict]:
    """Query fortress denizens with optional filters.

    Args:
        status_filter: Filter by status ('resident', 'deceased', etc.) or None for all
        sort_by: Column to sort by ('narrative_value', 'name', 'status')
        limit: Max rows to return
    """
    # Validate sort column
    valid_sorts = {'narrative_value', 'name', 'status', 'arrival_year', 'created_at'}
    if sort_by not in valid_sorts:
        sort_by = 'narrative_value'

    order = 'DESC' if sort_by == 'narrative_value' else 'ASC'

    if status_filter:
        rows = await conn.fetch(
            f"""
            SELECT id, unit_id, hf_id, name, english_name, race, status,
                   embark, arrival_year, departure_year, departure_cause,
                   narrative_value, last_seen_tick, details
            FROM fortress_denizens
            WHERE world_id = $1 AND status = $2
            ORDER BY {sort_by} {order}
            LIMIT $3
            """,
            world_id, status_filter, limit,
        )
    else:
        rows = await conn.fetch(
            f"""
            SELECT id, unit_id, hf_id, name, english_name, race, status,
                   embark, arrival_year, departure_year, departure_cause,
                   narrative_value, last_seen_tick, details
            FROM fortress_denizens
            WHERE world_id = $1
            ORDER BY {sort_by} {order}
            LIMIT $2
            """,
            world_id, limit,
        )

    return [dict(r) for r in rows]


async def link_hf(
    conn: asyncpg.Connection,
    world_id: int,
) -> int:
    """Link denizens to their historical figure records.

    For each denizen with a unit_id, check the units table for hist_fig_id,
    then verify the HF exists in historical_figures. Updates hf_id on match.

    Returns count of newly linked denizens.
    """
    # Find denizens with unit_id but no hf_id, where the unit has a hist_fig_id
    rows = await conn.fetch(
        """
        SELECT d.id, d.unit_id, u.hist_fig_id
        FROM fortress_denizens d
        JOIN units u ON u.id = d.unit_id
        WHERE d.world_id = $1
          AND d.hf_id IS NULL
          AND u.hist_fig_id IS NOT NULL
          AND u.hist_fig_id > 0
        """,
        world_id,
    )
    if not rows:
        return 0

    now = datetime.now(timezone.utc)
    count = 0
    for r in rows:
        # Verify HF exists
        hf_exists = await conn.fetchval(
            "SELECT 1 FROM historical_figures WHERE world_id = $1 AND id = $2",
            world_id, r['hist_fig_id'],
        )
        if hf_exists:
            await conn.execute(
                """
                UPDATE fortress_denizens
                SET hf_id = $3, updated_at = $4
                WHERE id = $1 AND world_id = $2
                """,
                r['id'], world_id, r['hist_fig_id'], now,
            )
            count += 1

    if count:
        log.info("Linked %d denizens to historical figure records", count)
    return count
