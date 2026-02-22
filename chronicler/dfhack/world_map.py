"""World map collector — captures geography data from DFHack.

Pulls the full world map (elevation, rainfall, vegetation, temperature, etc.)
via RemoteFortressReader's GetWorldMapNew. This is a one-time capture per world —
geography doesn't change mid-game, so we upsert once and skip on subsequent calls.
"""

import json
import logging

import asyncpg

from chronicler.dfhack.client import DFHackClient

log = logging.getLogger(__name__)


async def capture_world_map(conn: asyncpg.Connection, client: DFHackClient,
                             world_id: int) -> bool:
    """Pull full world map from DFHack and upsert into world_map_snapshots.

    Returns True if data was captured, False if unavailable (timeout).
    Skips if a snapshot already exists for this world_id.
    """
    # Check if we already have a snapshot for this world
    existing = await conn.fetchval(
        "SELECT 1 FROM world_map_snapshots WHERE world_id = $1", world_id
    )
    if existing:
        log.debug("World map snapshot already exists for world_id=%d", world_id)
        return True

    data = client.get_full_world_map()
    if data is None:
        log.debug("World map unavailable (RFR timeout)")
        return False

    # Pack geography arrays into JSONB
    geography = {
        key: data[key]
        for key in ('elevation', 'rainfall', 'vegetation', 'temperature',
                     'evilness', 'drainage', 'volcanism', 'savagery', 'salinity')
    }

    await conn.execute(
        """
        INSERT INTO world_map_snapshots (world_id, world_width, world_height,
                                          name, name_english, geography)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (world_id) DO UPDATE SET
            geography = EXCLUDED.geography,
            captured_at = now()
        """,
        world_id,
        data['world_width'],
        data['world_height'],
        data['name'],
        data['name_english'],
        json.dumps(geography),
    )

    log.info("Captured world map: %dx%d '%s' (%d geography data points)",
             data['world_width'], data['world_height'],
             data['name_english'] or data['name'],
             sum(len(v) for v in geography.values()))
    return True
