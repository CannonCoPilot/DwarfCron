"""Live sync — pull data from DFHack RPC and upsert into the CDM."""

import json
import logging
from datetime import datetime, timezone

import asyncpg

from chronicler.config import DFHACK_HOST, DFHACK_PORT
from chronicler.dfhack.client import DFHackClient

log = logging.getLogger(__name__)


async def upsert_units(conn: asyncpg.Connection, units: list[dict],
                       world_id: int) -> int:
    """Upsert a list of unit dicts into the units table.

    Shared by both sync_units (one-shot) and watch_loop (continuous).
    Returns the number of units upserted.
    """
    now = datetime.now(timezone.utc)
    count = 0

    for u in units:
        await conn.execute(
            """
            INSERT INTO units (id, world_id, name, english_name, race, caste,
                               profession, pos_x, pos_y, pos_z, is_alive,
                               hist_fig_id, civ_id, birth_year, sex,
                               death_cause, details, last_synced_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
                    $14, $15, $16, $17, $18)
            ON CONFLICT (id) DO UPDATE SET
                world_id = EXCLUDED.world_id,
                name = EXCLUDED.name,
                english_name = EXCLUDED.english_name,
                race = EXCLUDED.race,
                caste = EXCLUDED.caste,
                profession = EXCLUDED.profession,
                pos_x = EXCLUDED.pos_x,
                pos_y = EXCLUDED.pos_y,
                pos_z = EXCLUDED.pos_z,
                is_alive = EXCLUDED.is_alive,
                hist_fig_id = EXCLUDED.hist_fig_id,
                civ_id = EXCLUDED.civ_id,
                birth_year = COALESCE(EXCLUDED.birth_year, units.birth_year),
                sex = COALESCE(EXCLUDED.sex, units.sex),
                death_cause = COALESCE(EXCLUDED.death_cause, units.death_cause),
                details = EXCLUDED.details,
                last_synced_at = EXCLUDED.last_synced_at
            """,
            u['id'],
            world_id,
            u['name'],
            u.get('details', {}).get('english_name'),
            str(u.get('race_name', u['race'])),
            str(u['details']['caste']),
            u['profession'],
            u['pos_x'],
            u['pos_y'],
            u['pos_z'],
            u['is_alive'],
            u['hist_fig_id'],
            u['civ_id'],
            u.get('birth_year'),
            u.get('sex'),
            u.get('death_cause'),
            json.dumps(u['details']),
            now,
        )
        count += 1

    return count


async def sync_units(conn: asyncpg.Connection, world_id: int = 1) -> dict:
    """Pull all sane units from DFHack and upsert into the units table.

    Returns dict with counts: {'synced': N, 'dwarves': M}.
    """
    with DFHackClient(DFHACK_HOST, DFHACK_PORT) as client:
        units = client.list_units(sane=True)

    synced = await upsert_units(conn, units, world_id)
    dwarves = sum(1 for u in units if u['name'])
    log.info("Synced %d units (%d named) from DFHack", synced, dwarves)
    return {'synced': synced, 'dwarves': dwarves}


def enrich_units(base_units: list[dict],
                 enriched_units: list[dict]) -> list[dict]:
    """Merge RFR UnitDefinition data into core ListUnits data.

    Matches by unit ID. Adds inventory, wounds, noble_positions, blood stats,
    soldier status, and age into the unit's 'details' dict.

    Args:
        base_units: Units from DFHackClient.list_units()
        enriched_units: Units from DFHackClient.get_enriched_units()

    Returns:
        The base_units list (mutated in place) with enriched details.
    """
    enriched_by_id = {u['id']: u for u in enriched_units}

    for unit in base_units:
        enriched = enriched_by_id.get(unit['id'])
        if enriched is None:
            continue

        details = unit.get('details', {})
        details['is_soldier'] = enriched.get('is_soldier', False)
        details['blood_max'] = enriched.get('blood_max')
        details['blood_count'] = enriched.get('blood_count')
        details['age'] = enriched.get('age')
        details['noble_positions'] = enriched.get('noble_positions', [])
        details['inventory'] = enriched.get('inventory', [])
        details['wounds'] = enriched.get('wounds', [])
        unit['details'] = details

    return base_units


async def sync_world_info(conn: asyncpg.Connection) -> dict:
    """Pull world info from DFHack and return it (for display/logging)."""
    with DFHackClient(DFHACK_HOST, DFHACK_PORT) as client:
        return client.get_world_info()
