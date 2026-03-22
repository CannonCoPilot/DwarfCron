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
from chronicler.dfhack.bridge import (
    fetch_bridge_data, build_race_map, get_game_time, get_world_info,
    get_fortress_units, get_bridge_version, merge_bridge_into_units,
)
from chronicler.dfhack.etl_expanded import ingest_expanded
from chronicler.dfhack.etl_state_capture import ingest_state_capture
from chronicler.dfhack.client import DFHackClient
from chronicler.dfhack.detector import ChangeDetector
from chronicler.dfhack.sync import upsert_units, enrich_units
from chronicler.denizens import (
    has_denizens, register_denizen, detect_missing, detect_deaths,
    mark_seen, restore_resident, compute_nvs, link_hf,
)
from chronicler.dfhack.bridge_log import BridgeLogger

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


async def _insert_reactive_events(conn: asyncpg.Connection,
                                   bridge_data: dict, world_id: int,
                                   game_year: int | None,
                                   game_tick: int | None) -> int:
    """Persist reactive events (jobs, items, syndromes) as unit_events.

    These come from DFHack eventful subscriptions and were previously
    WebSocket-only. Now stored in unit_events for the Explorer UI.
    """
    reactive = bridge_data.get("reactive_events", {})
    if not reactive:
        return 0

    count = 0

    for job in (reactive.get("jobs_completed") or []):
        await conn.execute(
            "INSERT INTO unit_events (unit_id, world_id, event_type, "
            "new_value, game_year, game_tick) VALUES ($1,$2,$3,$4,$5,$6)",
            0, world_id, "job_completed",
            json.dumps({"job_type": job.get("job_type"),
                        "pos": job.get("pos"), "tick": job.get("tick")}),
            game_year, game_tick,
        )
        count += 1

    for item in (reactive.get("items_created") or []):
        await conn.execute(
            "INSERT INTO unit_events (unit_id, world_id, event_type, "
            "new_value, game_year, game_tick) VALUES ($1,$2,$3,$4,$5,$6)",
            item.get("unit_id", 0), world_id, "item_created",
            json.dumps({"item_id": item.get("item_id"),
                        "book_title": item.get("book_title"),
                        "tick": item.get("tick")}),
            game_year, game_tick,
        )
        count += 1

    for syn in (reactive.get("syndromes") or []):
        await conn.execute(
            "INSERT INTO unit_events (unit_id, world_id, event_type, "
            "new_value, game_year, game_tick) VALUES ($1,$2,$3,$4,$5,$6)",
            syn.get("unit_id", 0), world_id, "syndrome_applied",
            json.dumps({"syndrome_index": syn.get("syndrome_index"),
                        "tick": syn.get("tick")}),
            game_year, game_tick,
        )
        count += 1

    return count


async def _expand_kh_from_events(
    pool: asyncpg.Pool, world_id: int,
    events: list[dict], bridge_data: dict | None,
) -> int:
    """Expand Knowledge Horizon based on detected events and bridge data.

    Processes:
    - ARRIVED events: new arrivals may bring knowledge of origin sites
    - Invasion data from reactive events: reveals attacking entity
    - Diplomacy data from bridge: trade caravans reveal source civ/site
    """
    # Check if KH has been initialized for this world
    async with pool.acquire() as conn:
        has_kh = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM knowledge_horizon WHERE world_id = $1)",
            world_id,
        )
    if not has_kh:
        return 0

    from chronicler.kh import KnowledgeHorizonEngine
    kh = KnowledgeHorizonEngine(pool, world_id)

    total = 0

    # Process unit arrival events — new arrivals expand what the fortress knows
    for ev in events:
        if ev["event_type"] == "ARRIVED":
            total += await kh.process_revelation_event({
                "type": "migrant",
                "data": {"unit_id": ev["unit_id"]},
            })

    # Process invasion events from bridge reactive data
    if bridge_data:
        reactive = bridge_data.get("reactive_events", {})
        for inv in (reactive.get("invasions") or []):
            total += await kh.process_revelation_event({
                "type": "invasion",
                "data": inv,
            })

    return total


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
                'diplomacy', 'history', 'unit_summary',
                'world_info', 'entities', 'dwarf_skills',
                'dwarf_emotions', 'dwarf_personality', 'zones',
                'event_collections', 'squads', 'mandates', 'incidents']

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


async def _embed_cycle_changes(conn, world_id, units, events, bd):
    """Embed changed entities from a watcher cycle (Stage 3.4 live pipeline).

    Collects: unit deltas, new history events, announcements.
    Extracts text, checks content hashes, embeds changed items.
    Returns count of newly embedded items.
    """
    from chronicler.embedding.extractors import extract_unit, extract_announcement
    from chronicler.embedding.pipeline import embed_changed

    changes = []

    # Units that changed this cycle
    for u in units:
        try:
            text = extract_unit(u)
            if text:
                changes.append(("unit", u.get("id", 0), text))
        except Exception:
            pass

    # Announcements from bridge
    recent = bd.get("announcements", {}).get("recent", [])
    for ann in recent:
        try:
            text = extract_announcement(ann)
            if text:
                changes.append(("announcement", ann.get("id", 0), text))
        except Exception:
            pass

    if not changes:
        return 0

    return await embed_changed(conn, world_id, changes)


async def _cleanup_lua_probes_count(conn: asyncpg.Connection, world_id: int,
                                     keep: int = 10) -> int:
    """Delete old lua_probes rows, keeping the last `keep` per probe_name.

    Returns the number of rows deleted.
    """
    result = await conn.execute(
        """
        DELETE FROM lua_probes
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY probe_name ORDER BY captured_at DESC
                ) AS rn
                FROM lua_probes
                WHERE world_id = $1
            ) ranked
            WHERE rn > $2
        )
        """,
        world_id, keep,
    )
    # result is like "DELETE 42"
    return int(result.split()[-1]) if result else 0


async def _update_denizen_registry(
    conn: asyncpg.Connection,
    world_id: int,
    units: list[dict],
    cycle: int,
    game_year: int | None,
    game_tick: int | None,
) -> None:
    """Update the fortress denizen registry from current unit data.

    On the first cycle (no existing denizens), all units are marked as
    embark dwarves. Subsequent cycles register new arrivals, detect
    deaths and absences, and periodically recompute NVS.
    """
    is_first = not await has_denizens(conn, world_id)

    current_unit_ids = set()
    for u in units:
        uid = u['id']
        current_unit_ids.add(uid)
        await register_denizen(
            conn, world_id, u,
            is_embark=is_first,
            game_year=game_year,
            game_tick=game_tick,
        )

    if is_first:
        log.info("Denizen registry: %d embark dwarves registered", len(units))
    else:
        # Detect deaths (is_alive=False transitions)
        deaths = await detect_deaths(
            conn, world_id, units,
            game_year=game_year, game_tick=game_tick,
        )
        if deaths:
            log.info("Denizen deaths detected: %d", len(deaths))

        # Detect missing (residents no longer in unit list)
        missing = await detect_missing(
            conn, world_id, current_unit_ids,
            game_year=game_year, game_tick=game_tick,
        )
        if missing:
            log.info("Denizen missing detected: %d", len(missing))

        # Restore any previously missing denizens who reappeared
        restored = await conn.fetch(
            """
            SELECT unit_id FROM fortress_denizens
            WHERE world_id = $1 AND status = 'missing'
              AND unit_id = ANY($2::int[])
            """,
            world_id, list(current_unit_ids),
        )
        for r in restored:
            if await restore_resident(conn, world_id, r['unit_id']):
                log.info("Denizen unit %d restored to resident", r['unit_id'])

    # Update last_seen_tick for all observed units
    await mark_seen(conn, world_id, list(current_unit_ids), game_tick)

    # Periodic: HF linking + NVS recomputation (every 10 cycles)
    if cycle % 10 == 0:
        await link_hf(conn, world_id)
        await compute_nvs(conn, world_id, total_cycles=cycle)


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
        if extras.get('denizens'):
            extra_parts.append("denizens")
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
    bridge_data = None
    if not rfr_available:
        log.info("RFR unavailable. Probing bridge at %s:%d...",
                 _bridge_host, _bridge_port)
        bridge_data = fetch_bridge_data(_bridge_host, _bridge_port)
        if bridge_data:
            bridge_available = True
            yr, tk = get_game_time(bridge_data)
            sections = [k for k in bridge_data.keys() if k not in
                        ('cur_year', 'cur_year_tick', 'cur_season',
                         'creature_raws', 'creature_count', 'timestamp',
                         'bridge_version', 'errors')]
            bver = get_bridge_version(bridge_data)
            log.info("Bridge v%d available — year %s, tick %s, %d creatures, "
                     "%d sections: %s",
                     bver, yr, tk, bridge_data.get('creature_count', 0),
                     len(sections), ', '.join(sections))
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

    # ── Auto-update world name from bridge ──────────────────────────────
    if bridge_available and bridge_data:
        wi = get_world_info(bridge_data)
        if wi.get('world_name') or wi.get('world_name_english'):
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE worlds SET name = COALESCE(NULLIF($2, ''), name), "
                    "alt_name = COALESCE(NULLIF($3, ''), alt_name) "
                    "WHERE id = $1",
                    world_id,
                    wi.get('world_name', ''),
                    wi.get('world_name_english', ''),
                )
            log.info("World %d: name=%s / %s, fortress=%s",
                     world_id, wi.get('world_name'), wi.get('world_name_english'),
                     wi.get('fortress_name'))

    # ── Bridge JSONL logger (durable capture of raw bridge data) ─────
    bridge_logger = BridgeLogger()
    if bridge_available and bridge_data:
        wi = get_world_info(bridge_data)
        world_name = wi.get('world_name_english') or wi.get('world_name') or 'unknown'
        bridge_logger.open(world_name)

    world_map_captured = False
    last_probe_time = 0.0
    last_cleanup_cycle = 0
    bridge_failures = 0
    cycle = 0
    prev_season = None  # Track season changes for fortress_state snapshots
    prev_year = None    # Track year changes for session markers
    last_snapshot_tick = 0  # Tick of last fortress_state_snapshot

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
                if bd:
                    bridge_failures = 0
                    game_year, game_tick = get_game_time(bd)
                    # Durable capture: append raw bridge data to JSONL log
                    bridge_logger.append(bd, cycle, game_year, game_tick)
                else:
                    bridge_failures += 1
                    if bridge_failures == 3:
                        log.warning("Bridge failed 3 consecutive times — "
                                    "continuing with core-only data. Check "
                                    "HTTP server at %s:%d",
                                    _bridge_host, _bridge_port)
                    elif bridge_failures % 10 == 0:
                        log.warning("Bridge failure streak: %d", bridge_failures)

            # 2. Pull current units (core method — may timeout under timestream)
            try:
                units = client.list_units(sane=True, skills=True, profession=True)
            except (TimeoutError, OSError) as e:
                log.warning("ListUnits RPC timeout (cycle %d): %s — "
                            "using bridge units only", cycle, e)
                # Fall back to bridge fortress_units if available
                if bd:
                    bridge_units = get_fortress_units(bd)
                    units = []
                    for bu in (bridge_units or []):
                        units.append({
                            'id': bu.get('id', 0),
                            'name': bu.get('name', ''),
                            'race': bu.get('race', 0),
                            'race_name': 'DWARF',
                            'profession': bu.get('profession', 0),
                        })
                else:
                    log.warning("No fallback data — skipping cycle %d", cycle)
                    try:
                        await asyncio.wait_for(_shutdown.wait(),
                                               timeout=interval)
                        break
                    except asyncio.TimeoutError:
                        continue
            for u in units:
                if 'race_name' not in u:
                    u['race_name'] = race_map.get(u.get('race', 0),
                                                  str(u.get('race', 0)))

            # 3. Optionally enrich units with RFR data
            if enable_enriched:
                try:
                    enriched = client.get_enriched_units()
                    if enriched:
                        enrich_units(units, enriched)
                        extras['enriched'] = True
                except Exception as e:
                    log.debug("Unit enrichment failed: %s", e)

            # 4. Detect changes (core RPC units)
            events = detector.detect(units)

            # 4b. Detect bridge-based changes (mood, pregnancy, ghost, stress)
            if bd and get_bridge_version(bd) >= 6:
                bridge_units = get_fortress_units(bd)
                if bridge_units:
                    bridge_events = detector.detect_bridge(bridge_units)
                    events.extend(bridge_events)

            # 4c. Merge bridge biographical + personality data into units
            if bd and get_bridge_version(bd) >= 7:
                merge_bridge_into_units(units, bd)

            # 5. Upsert units + insert events + record snapshot (single txn)
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await upsert_units(conn, units, world_id)
                    await _insert_events(conn, events, world_id,
                                         game_year, game_tick)
                    # Persist reactive events (jobs, items, syndromes)
                    reactive_count = 0
                    if bd:
                        reactive_count = await _insert_reactive_events(
                            conn, bd, world_id, game_year, game_tick)
                    await _record_snapshot(conn, world_id, len(units),
                                          len(events) + reactive_count,
                                          game_year, game_tick)

                # 5b. Denizen registry tracking
                try:
                    await _update_denizen_registry(
                        conn, world_id, units, cycle,
                        game_year, game_tick)
                    extras['denizens'] = True
                except Exception as e:
                    log.debug("Denizen tracking failed: %s", e)

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

                # 6b. Expanded ETL: promote bridge sections → CDM tables
                if bd and bridge_available:
                    try:
                        cur_season = bd.get("cur_season")
                        season_changed = (prev_season is not None
                                          and cur_season != prev_season)
                        prev_season = cur_season

                        year_changed = (prev_year is not None
                                        and game_year is not None
                                        and game_year != prev_year)
                        if game_year is not None:
                            prev_year = game_year

                        etl_summary = await ingest_expanded(
                            conn, bd, world_id,
                            game_year=game_year, game_tick=game_tick,
                            season_changed=season_changed)
                        active_etl = {k: v for k, v in etl_summary.items() if v}
                        if active_etl:
                            extras['expanded_etl'] = active_etl
                    except Exception as e:
                        log.debug("Expanded ETL failed: %s", e)

                # 6b2. Stage 3.5: Fortress state capture
                if bd and bridge_available:
                    try:
                        sc_summary = await ingest_state_capture(
                            conn, bd, world_id,
                            game_year=game_year, game_tick=game_tick,
                            season_changed=season_changed,
                            year_changed=year_changed,
                            recent_events=events,
                            last_snapshot_tick=last_snapshot_tick)
                        if sc_summary.get('last_snapshot_tick'):
                            last_snapshot_tick = sc_summary['last_snapshot_tick']
                        active_sc = {k: v for k, v in sc_summary.items()
                                     if v and k != 'last_snapshot_tick'}
                        if active_sc:
                            extras['state_capture'] = active_sc
                    except Exception as e:
                        log.debug("State capture failed: %s", e)

                # 6b3. Live embedding (incremental)
                if bd and bridge_available:
                    try:
                        embed_count = await _embed_cycle_changes(
                            conn, world_id, units, events, bd)
                        if embed_count:
                            extras['embedded'] = embed_count
                    except Exception as e:
                        log.debug("Live embedding failed: %s", e)

                # 6c. Knowledge Horizon expansion (every 10 cycles)
                if cycle % 10 == 0 and events:
                    try:
                        kh_count = await _expand_kh_from_events(
                            pool, world_id, events, bd)
                        if kh_count:
                            extras['kh_reveals'] = kh_count
                    except Exception as e:
                        log.debug("KH expansion failed: %s", e)

                # 6d. Retention cleanup (every 10 cycles)
                if cycle - last_cleanup_cycle >= 10:
                    try:
                        deleted = await _cleanup_lua_probes_count(
                            conn, world_id, keep=10)
                        if deleted > 0:
                            log.debug("lua_probes cleanup: %d old rows deleted", deleted)
                    except Exception as e:
                        log.debug("lua_probes cleanup failed: %s", e)
                    last_cleanup_cycle = cycle

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
        bridge_logger.close()
        client.close()
        log.info("Watcher stopped after %d cycles", cycle)
