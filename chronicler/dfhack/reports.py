"""Reports collector — pulls game announcements and combat logs from DFHack.

Uses RemoteFortressReader's GetReports → Status to capture game reports.
Deduplicates by report_id (INSERT ... ON CONFLICT DO NOTHING) to avoid
re-inserting reports already seen in previous poll cycles.
"""

import json
import logging

import asyncpg

from chronicler.dfhack.client import DFHackClient

log = logging.getLogger(__name__)


async def collect_reports(conn: asyncpg.Connection, client: DFHackClient,
                          world_id: int) -> int:
    """Pull reports from DFHack and insert new ones into game_reports.

    Returns the count of newly inserted reports (excludes duplicates).
    Returns 0 if the RFR call times out.
    """
    reports = client.get_reports()
    if reports is None:
        log.debug("Reports unavailable (RFR timeout)")
        return 0

    inserted = 0
    for r in reports:
        result = await conn.execute(
            """
            INSERT INTO game_reports (world_id, report_id, report_type, text,
                                      game_year, game_tick, pos_x, pos_y, pos_z,
                                      is_announcement)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (world_id, report_id) DO NOTHING
            """,
            world_id,
            r['id'],
            r['type'],
            r['text'],
            r['year'],
            r['time'],
            r['pos_x'],
            r['pos_y'],
            r['pos_z'],
            r['announcement'],
        )
        # asyncpg returns "INSERT 0 1" on success, "INSERT 0 0" on conflict
        if result == 'INSERT 0 1':
            inserted += 1

    if inserted:
        log.info("Collected %d new reports (%d total from RFR)", inserted, len(reports))
    return inserted
