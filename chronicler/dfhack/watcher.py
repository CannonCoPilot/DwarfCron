"""Polling daemon — continuously captures game state and detects changes.

Polls DFHack every N seconds, tracks in-game time, resolves race names,
detects meaningful changes (arrivals, deaths, skill-ups, mood shifts),
and logs events to PostgreSQL.

Data sources (tried in order):
1. RFR (RemoteFortressReader) — game time, creature raws, reports, enriched units.
   Requires allow_remote=true. Unavailable in DFHack 53.10-r1 (plugin not shipped).
2. Bridge — Lua script writes comprehensive game state to JSON, served over HTTP.
   Provides: game time, creature raws, unit summaries w/ stress, armies, buildings,
   artifacts, announcements, diplomacy, history. Works with any DFHack version.
3. Core API fallback — ListUnits always works. Game time unknown, race IDs numeric.

Core methods (ListUnits, GetWorldInfo) always work regardless of game state.
"""

import asyncio
import json
import logging
import signal
import time

import asyncpg

from chronicler.config import DFHACK_HOST, DFHACK_PORT, BRIDGE_HOST, BRIDGE_PORT
from chronicler.dfhack.bridge import fetch_bridge_data, build_race_map, get_game_time
from chronicler.dfhack.client import DFHackClient
from chronicler.dfhack.detector import ChangeDetector
from chronicler.dfhack.sync import upsert_units, enrich_units

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


async def _store_bridge_sections(conn: asyncpg.Connection, world_id: int,
                                  bridge_data: dict,
                                  game_year: int | None,
                                  game_tick: int | None) -> int:
    """Store expanded bridge data sections in lua_probes table.

    Returns the number of sections stored.
    """
    count = 0
    sections = ['armies', 'buildings', 'artifacts', 'announcements',
                'diplomacy', 'history', 'unit_summary']

    for section in sections:
        data = bridge_data.get(section)
        if data:
            await conn.execute(
                """
                INSERT INTO lua_probes (world_id, probe_name, data,
                                        game_year, game_tick)
                VALUES ($1, $2, $3, $4, $5)
                """,
                world_id, section, json.dumps(data), game_year, game_tick,
            )
            count += 1

    return count


def _log_cycle(cycle: int, game_year: int | None, game_tick: int | None,
               unit_count: int, event_count: int, events: list[dict],
               extras: dict | None = None):
    """Log a summary of the poll cycle."""
    time_str = f"year {game_year}, tick {game_tick}" if game_year else "time unknown"
    extra_parts = []
    if extras:
        if extras.get('reports'):
            extra_parts.append(f"{extras['reports']} new reports")
        if extras.get('enriched'):
            extra_parts.append("enriched")
        if extras.get('world_map'):
            extra_parts.append("world map captured")
        if extras.get('bridge_sections'):
            extra_parts.append(f"{extras['bridge_sections']} bridge sections")
    extra_str = f" [{', '.join(extra_parts)}]" if extra_parts else ""
    log.info("Cycle %d: %d units, %d events (%s)%s", cycle, unit_count,
             event_count, time_str, extra_str)
    for ev in events:
        log.info("  %s unit=%d %s", ev['event_type'], ev['unit_id'],
                 ev.get('new_value', ''))


async def watch_loop(pool: asyncpg.Pool, world_id: int = 1,
                     interval: float = 30.0, *,
                     bridge_host: str = '',
                     enable_reports: bool = False,
                     enable_enriched: bool = False,
                     probe_interval: float = 0):
    """Continuous polling loop. Runs until SIGINT/SIGTERM.

    Each cycle:
    1. Fetch bridge data (game time + expanded sections)
    2. Pull current units via core RPC with race names resolved
    3. Optionally enrich units with RFR data (inventory, wounds, etc.)
    4. Detect changes vs previous cycle
    5. Upsert units + insert events + record snapshot (single txn)
    6. Store expanded bridge sections (armies, buildings, etc.)
    7. Optionally collect reports (RFR only)
    8. Optionally capture world map (first cycle only, RFR only)
    9. Wait for next interval (interruptible by shutdown signal)

    Args:
        pool: asyncpg connection pool
        world_id: World ID to tag data with
        interval: Seconds between poll cycles
        bridge_host: Host for the Lua bridge HTTP server (empty = same as DFHACK_HOST)
        enable_reports: Collect game reports each cycle (RFR only)
        enable_enriched: Enrich units with RFR data each cycle (RFR only)
        probe_interval: Store bridge sections every N seconds (0 = every cycle)
    """
    from chronicler.dfhack.reports import collect_reports
    from chronicler.dfhack.world_map import capture_world_map

    detector = ChangeDetector()
    client = DFHackClient(DFHACK_HOST, DFHACK_PORT)
    client.connect()

    # Resolve bridge host (default: same machine as DFHack)
    _bridge_host = bridge_host or BRIDGE_HOST or DFHACK_HOST
    _bridge_port = BRIDGE_PORT

    # ── Data source negotiation ──────────────────────────────────────
    # Try RFR first (best quality), then bridge (good), then core-only (minimal)
    rfr_available = False
    bridge_available = False

    # 1. Probe RFR (RemoteFortressReader plugin)
    log.info("Probing RFR availability (5s timeout)...")
    try:
        wm_probe = client.get_world_map(timeout=5.0)
        if wm_probe:
            rfr_available = True
            log.info("RFR available — game time: year %d, tick %d",
                     wm_probe['cur_year'], wm_probe['cur_year_tick'])
    except Exception:
        pass

    # 2. If no RFR, probe the Lua bridge
    if not rfr_available:
        log.info("RFR unavailable. Probing bridge at %s:%d...",
                 _bridge_host, _bridge_port)
        bridge_data = fetch_bridge_data(_bridge_host, _bridge_port)
        if bridge_data:
            bridge_available = True
            yr, tk = get_game_time(bridge_data)
            sections = [k for k in bridge_data.keys() if k not in
                        ('cur_year', 'cur_year_tick', 'cur_season',
                         'creature_raws', 'creature_count', 'timestamp')]
            log.info("Bridge available — year %s, tick %s, %d creatures, "
                     "sections: %s",
                     yr, tk, bridge_data.get('creature_count', 0),
                     ', '.join(sections))
        else:
            log.warning("Bridge unavailable at %s:%d — running without game "
                        "time or creature raws. Set up chronicler-bridge.lua "
                        "and PowerShell HTTP server for full data.",
                        _bridge_host, _bridge_port)

    if not rfr_available and not bridge_available:
        # Force-disable RFR-dependent features
        enable_reports = False
        enable_enriched = False

    # ── Build race map ───────────────────────────────────────────────
    race_map = {}
    if rfr_available:
        race_map = client.get_creature_raws() or {}
    elif bridge_available:
        race_map = build_race_map(bridge_data)

    if race_map:
        log.info("Race map: %d creature types loaded (source: %s)",
                 len(race_map), "RFR" if rfr_available else "bridge")
    else:
        # Fallback: label the player race (dwarves) via GetWorldInfo (core)
        info = client.get_world_info()
        player_race = info.get('race_id')
        if player_race is not None:
            race_map = {player_race: 'DWARF'}
            log.info("Using minimal race map (race %d=DWARF only)", player_race)
        else:
            log.warning("Could not load creature raws — using numeric race IDs")

    world_map_captured = False
    last_probe_time = 0.0
    cycle = 0

    try:
        while not _shutdown.is_set():
            cycle += 1
            extras = {}
            bd = None

            # 1. Get game time + full bridge data (RFR > bridge > none)
            game_year = None
            game_tick = None
            if rfr_available:
                world_map = client.get_world_map()
                game_year = world_map['cur_year'] if world_map else None
                game_tick = world_map['cur_year_tick'] if world_map else None
            elif bridge_available:
                bd = fetch_bridge_data(_bridge_host, _bridge_port)
                game_year, game_tick = get_game_time(bd)

            # 2. Pull current units (core method — always works)
            units = client.list_units(sane=True, skills=True, profession=True)
            for u in units:
                u['race_name'] = race_map.get(u['race'], str(u['race']))

            # 3. Optionally enrich units with RFR data
            if enable_enriched:
                try:
                    enriched = client.get_enriched_units()
                    if enriched:
                        enrich_units(units, enriched)
                        extras['enriched'] = True
                except Exception as e:
                    log.debug("Unit enrichment failed: %s", e)

            # 4. Detect changes
            events = detector.detect(units)

            # 5. Upsert units + insert events + record snapshot (single txn)
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await upsert_units(conn, units, world_id)
                    await _insert_events(conn, events, world_id,
                                         game_year, game_tick)
                    await _record_snapshot(conn, world_id, len(units),
                                          len(events), game_year, game_tick)

                # 6. Store expanded bridge sections
                if bd and bridge_available:
                    now = time.monotonic()
                    if probe_interval <= 0 or (now - last_probe_time) >= probe_interval:
                        try:
                            n = await _store_bridge_sections(
                                conn, world_id, bd, game_year, game_tick)
                            if n:
                                extras['bridge_sections'] = n
                        except Exception as e:
                            log.debug("Bridge section storage failed: %s", e)
                        last_probe_time = now

                # 7. Optionally collect reports (RFR only)
                if enable_reports:
                    try:
                        new_reports = await collect_reports(conn, client, world_id)
                        if new_reports:
                            extras['reports'] = new_reports
                    except Exception as e:
                        log.debug("Report collection failed: %s", e)

                # 8. World map capture (first cycle only, RFR required)
                if rfr_available and not world_map_captured:
                    try:
                        world_map_captured = await capture_world_map(
                            conn, client, world_id)
                        if world_map_captured:
                            extras['world_map'] = True
                    except Exception as e:
                        log.debug("World map capture failed: %s", e)

            # 9. Log summary
            _log_cycle(cycle, game_year, game_tick, len(units), len(events),
                       events, extras)

            # 10. Wait (interruptible by shutdown signal)
            try:
                await asyncio.wait_for(_shutdown.wait(), timeout=interval)
                break  # shutdown was set
            except asyncio.TimeoutError:
                continue
    finally:
        client.close()
        log.info("Watcher stopped after %d cycles", cycle)
