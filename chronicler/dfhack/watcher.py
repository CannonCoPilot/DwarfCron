"""Polling daemon — continuously captures game state and detects changes.

Polls DFHack every N seconds, tracks in-game time, resolves race names,
detects meaningful changes (arrivals, deaths, skill-ups, mood shifts),
and logs events to PostgreSQL.

RFR calls (game time, creature raws) gracefully degrade when the game is
paused — core methods (ListUnits) always work regardless of game state.
"""

import asyncio
import json
import logging
import signal

import asyncpg

from chronicler.config import DFHACK_HOST, DFHACK_PORT
from chronicler.dfhack.client import DFHackClient
from chronicler.dfhack.detector import ChangeDetector
from chronicler.dfhack.sync import upsert_units

log = logging.getLogger(__name__)

_shutdown = asyncio.Event()


def _handle_signal(sig, _frame):
    """Signal handler — sets the shutdown event."""
    log.info("Received %s, shutting down gracefully...", signal.Signals(sig).name)
    _shutdown.set()


async def _insert_events(conn: asyncpg.Connection, events: list[dict],
                         world_id: int, game_year: int | None,
                         game_tick: int | None):
    """Insert detected change events into unit_events."""
    for ev in events:
        await conn.execute(
            """
            INSERT INTO unit_events (unit_id, world_id, event_type,
                                     old_value, new_value, game_year, game_tick)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            ev['unit_id'],
            world_id,
            ev['event_type'],
            json.dumps(ev['old_value']) if ev['old_value'] else None,
            json.dumps(ev['new_value']) if ev['new_value'] else None,
            game_year,
            game_tick,
        )


async def _record_snapshot(conn: asyncpg.Connection, world_id: int,
                           unit_count: int, event_count: int,
                           game_year: int | None, game_tick: int | None):
    """Record a poll cycle snapshot."""
    await conn.execute(
        """
        INSERT INTO sync_snapshots (world_id, unit_count, event_count,
                                    game_year, game_tick)
        VALUES ($1, $2, $3, $4, $5)
        """,
        world_id, unit_count, event_count, game_year, game_tick,
    )


def _log_cycle(cycle: int, game_year: int | None, game_tick: int | None,
               unit_count: int, event_count: int, events: list[dict]):
    """Log a summary of the poll cycle."""
    time_str = f"year {game_year}, tick {game_tick}" if game_year else "time unknown"
    log.info("Cycle %d: %d units, %d events (%s)", cycle, unit_count,
             event_count, time_str)
    for ev in events:
        log.info("  %s unit=%d %s", ev['event_type'], ev['unit_id'],
                 ev.get('new_value', ''))


async def watch_loop(pool: asyncpg.Pool, world_id: int = 1,
                     interval: float = 30.0):
    """Continuous polling loop. Runs until SIGINT/SIGTERM.

    Each cycle:
    1. Get game time (RFR — degrades gracefully if paused)
    2. Pull current units with race names resolved
    3. Detect changes vs previous cycle
    4. Upsert units + insert events + record snapshot (single txn)
    5. Wait for next interval (interruptible by shutdown signal)
    """
    detector = ChangeDetector()
    client = DFHackClient(DFHACK_HOST, DFHACK_PORT)
    client.connect()

    # One-time: try to build race cache from creature raws
    race_map = client.get_creature_raws() or {}
    if race_map:
        log.info("Race map: %d creature types loaded", len(race_map))
    else:
        # Fallback: at minimum label the player race (dwarves) via GetWorldInfo
        info = client.get_world_info()
        player_race = info.get('race_id')
        if player_race is not None:
            race_map = {player_race: 'DWARF'}
            log.warning("RFR unavailable — using minimal race map "
                        "(race %d=DWARF only)", player_race)
        else:
            log.warning("Could not load creature raws — using numeric race IDs")

    cycle = 0
    try:
        while not _shutdown.is_set():
            cycle += 1

            # 1. Get game time (may return None if game paused)
            world_map = client.get_world_map()
            game_year = world_map['cur_year'] if world_map else None
            game_tick = world_map['cur_year_tick'] if world_map else None

            # Retry race map if we didn't get it at startup
            if not race_map:
                race_map = client.get_creature_raws() or {}

            # 2. Pull current units (core method — always works)
            units = client.list_units(sane=True, skills=True, profession=True)
            for u in units:
                u['race_name'] = race_map.get(u['race'], str(u['race']))

            # 3. Detect changes
            events = detector.detect(units)

            # 4. Upsert units + insert events + record snapshot (single txn)
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await upsert_units(conn, units, world_id)
                    await _insert_events(conn, events, world_id,
                                         game_year, game_tick)
                    await _record_snapshot(conn, world_id, len(units),
                                          len(events), game_year, game_tick)

            # 5. Log summary
            _log_cycle(cycle, game_year, game_tick, len(units), len(events),
                       events)

            # 6. Wait (interruptible by shutdown signal)
            try:
                await asyncio.wait_for(_shutdown.wait(), timeout=interval)
                break  # shutdown was set
            except asyncio.TimeoutError:
                continue
    finally:
        client.close()
        log.info("Watcher stopped after %d cycles", cycle)
