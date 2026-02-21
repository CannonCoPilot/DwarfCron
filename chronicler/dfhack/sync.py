"""Live sync — pull data from DFHack RPC and upsert into the CDM."""

import json
import logging
from datetime import datetime, timezone

import asyncpg

from chronicler.config import DFHACK_HOST, DFHACK_PORT
from chronicler.dfhack.client import DFHackClient

log = logging.getLogger(__name__)


async def sync_units(conn: asyncpg.Connection, world_id: int = 1) -> dict:
    """Pull all sane units from DFHack and upsert into the units table.

    Returns dict with counts: {'synced': N, 'dwarves': M}.
    """
    with DFHackClient(DFHACK_HOST, DFHACK_PORT) as client:
        units = client.list_units(sane=True)

    now = datetime.now(timezone.utc)
    synced = 0

    for u in units:
        await conn.execute(
            """
            INSERT INTO units (id, world_id, name, race, caste, profession,
                               pos_x, pos_y, pos_z, is_alive,
                               hist_fig_id, civ_id, details, last_synced_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                race = EXCLUDED.race,
                caste = EXCLUDED.caste,
                profession = EXCLUDED.profession,
                pos_x = EXCLUDED.pos_x,
                pos_y = EXCLUDED.pos_y,
                pos_z = EXCLUDED.pos_z,
                is_alive = EXCLUDED.is_alive,
                hist_fig_id = EXCLUDED.hist_fig_id,
                civ_id = EXCLUDED.civ_id,
                details = EXCLUDED.details,
                last_synced_at = EXCLUDED.last_synced_at
            """,
            u['id'],
            world_id,
            u['name'],
            str(u['race']),  # numeric race ID as text until we have creature raws
            str(u['details']['caste']),
            u['profession'],
            u['pos_x'],
            u['pos_y'],
            u['pos_z'],
            u['is_alive'],
            u['hist_fig_id'],
            u['civ_id'],
            json.dumps(u['details']),
            now,
        )
        synced += 1

    dwarves = sum(1 for u in units if u['name'])
    log.info("Synced %d units (%d named) from DFHack", synced, dwarves)
    return {'synced': synced, 'dwarves': dwarves}


async def sync_world_info(conn: asyncpg.Connection) -> dict:
    """Pull world info from DFHack and return it (for display/logging)."""
    with DFHackClient(DFHACK_HOST, DFHACK_PORT) as client:
        return client.get_world_info()
