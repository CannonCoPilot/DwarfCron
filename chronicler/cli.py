"""Chronicler CLI — init, ingest, and validate Dwarf Fortress world data."""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import click

from chronicler.config import LEGENDS_DIR


def _run(coro):
    """Run an async coroutine from sync Click commands."""
    return asyncio.run(coro)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def cli(verbose):
    """Chronicler — AI storyteller for Dwarf Fortress."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@cli.command("init-db")
def init_db():
    """Create the chronicler database and run schema migrations."""
    from chronicler.db.connection import init_db as _init_db

    async def _run_init():
        await _init_db()
        click.echo("Database initialized successfully.")

    _run(_run_init())


# ── World management ─────────────────────────────────────────────────────────

@cli.group("worlds")
def worlds_group():
    """Manage world records in the database."""


@worlds_group.command("list")
def worlds_list():
    """Show all worlds with summary statistics."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.db.worlds import list_worlds

    async def _run_list():
        pool = await get_pool()
        async with pool.acquire() as conn:
            worlds = await list_worlds(conn)

        if not worlds:
            click.echo("No worlds in database.")
            await close_pool()
            return

        click.echo("── Worlds ──")
        for w in worlds:
            c = w["counts"]
            click.echo(
                f"  [{w['id']:>3d}] {w['name'] or '?':30s} "
                f"({w['alt_name'] or '?'})"
            )
            click.echo(
                f"        HFs: {c['historical_figures']:>8,d}  "
                f"Events: {c['history_events']:>8,d}  "
                f"Sites: {c['sites']:>6,d}  "
                f"Entities: {c['entities']:>6,d}  "
                f"Artifacts: {c['artifacts']:>6,d}"
            )
            if w["import_path"]:
                click.echo(f"        Source: {w['import_path']}")
        click.echo(f"\nTotal: {len(worlds)} world(s)")
        await close_pool()

    _run(_run_list())


@worlds_group.command("delete")
@click.option("--world-id", type=int, default=None, help="ID of the world to delete")
@click.option("--all", "delete_all", is_flag=True, help="Delete all worlds")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
def worlds_delete(world_id, delete_all, yes):
    """Delete world(s) and all associated data."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.db.worlds import delete_world, delete_all_worlds

    if world_id is None and not delete_all:
        click.echo("Specify --world-id N or --all", err=True)
        sys.exit(1)
    if world_id is not None and delete_all:
        click.echo("--world-id and --all are mutually exclusive", err=True)
        sys.exit(1)

    async def _run_delete():
        pool = await get_pool()
        async with pool.acquire() as conn:
            if delete_all:
                if not yes:
                    click.confirm("Delete ALL worlds and data?", abort=True)
                count, deleted = await delete_all_worlds(conn)
                click.echo(f"Deleted {count} world(s).")
                total = sum(deleted.values())
                click.echo(f"  {total:,d} total rows removed across {len(deleted)} tables.")
            else:
                if not yes:
                    click.confirm(f"Delete world {world_id} and all data?", abort=True)
                try:
                    deleted = await delete_world(conn, world_id)
                except ValueError as e:
                    click.echo(str(e), err=True)
                    await close_pool()
                    sys.exit(1)
                total = sum(deleted.values())
                click.echo(f"Deleted world {world_id}.")
                click.echo(f"  {total:,d} total rows removed across {len(deleted)} tables.")
        await close_pool()

    _run(_run_delete())


def _resolve_legends_pair(
    legends_path: str | None,
    legends_plus_path: str | None,
) -> tuple[str, str | None]:
    """Resolve legends/legends_plus paths from files, directories, or defaults.

    Accepts:
      - A directory: auto-detects *-legends.xml and *-legends_plus.xml inside it
      - A file: uses as-is
      - None: falls back to LEGENDS_DIR auto-detection
    """
    # If legends_path is a directory, auto-detect files within it
    if legends_path is not None and Path(legends_path).is_dir():
        search_dir = Path(legends_path)
        candidates = sorted(search_dir.glob("*-legends.xml"))
        if not candidates:
            click.echo(f"No *-legends.xml found in {legends_path}", err=True)
            sys.exit(1)
        legends_path = str(candidates[0])
        # Auto-detect plus from same directory
        if legends_plus_path is None:
            plus_candidates = sorted(search_dir.glob("*-legends_plus.xml"))
            if plus_candidates:
                legends_plus_path = str(plus_candidates[0])

    # Fall back to LEGENDS_DIR if nothing specified
    if legends_path is None:
        candidates = sorted(Path(LEGENDS_DIR).glob("*-legends.xml"))
        if not candidates:
            click.echo("No legends.xml found in data/legends/. Use --legends.", err=True)
            sys.exit(1)
        legends_path = str(candidates[0])

    # Auto-detect plus from same directory as legends if not specified
    if legends_plus_path is None:
        legends_dir = Path(legends_path).parent
        plus_candidates = sorted(legends_dir.glob("*-legends_plus.xml"))
        if plus_candidates:
            legends_plus_path = str(plus_candidates[0])

    return legends_path, legends_plus_path


@cli.command("ingest")
@click.option(
    "--legends", "legends_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to legends.xml or directory containing it",
)
@click.option(
    "--legends-plus", "legends_plus_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to legends_plus.xml (default: auto-detect from legends dir)",
)
def ingest(legends_path, legends_plus_path):
    """Parse and import Dwarf Fortress legends XML into the database."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.ingest.xml_parser import import_legends

    legends_path, legends_plus_path = _resolve_legends_pair(legends_path, legends_plus_path)

    click.echo(f"Legends:      {legends_path}")
    click.echo(f"Legends Plus: {legends_plus_path or '(none)'}")

    async def _run_ingest():
        pool = await get_pool()
        async with pool.acquire() as conn:
            counts = await import_legends(conn, legends_path, legends_plus_path)

        click.echo("\n── Ingestion Complete ──")
        total = 0
        for table, n in sorted(counts.items()):
            click.echo(f"  {table:40s} {n:>8,d}")
            total += n
        click.echo(f"  {'TOTAL':40s} {total:>8,d}")

        await close_pool()

    _run(_run_ingest())


@cli.command("serve")
@click.option("--host", default="127.0.0.1", help="Bind address")
@click.option("--port", default=8080, type=int, help="Port number")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host, port, reload):
    """Launch the Chronicler web UI."""
    import uvicorn

    click.echo(f"Starting Chronicler at http://{host}:{port}")
    uvicorn.run("chronicler.api.app:app", host=host, port=port, reload=reload)


@cli.command("sync-live")
@click.option("--world-id", default=1, type=int, help="World ID to tag units with")
def sync_live(world_id):
    """Pull live unit data from DFHack and upsert into the CDM."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.dfhack.sync import sync_units, sync_world_info

    async def _run_sync():
        pool = await get_pool()
        async with pool.acquire() as conn:
            info = await sync_world_info(conn)
            click.echo(f"World: {info.get('world_english', '?')} ({info.get('mode', '?')})")
            click.echo(f"  Save: {info.get('save_dir', '?')}, Site: {info.get('site_id', '?')}")

            counts = await sync_units(conn, world_id=world_id)
            click.echo(f"\nSynced {counts['synced']} units ({counts['dwarves']} named dwarves)")

        await close_pool()

    _run(_run_sync())


@cli.command("watch")
@click.option("--world-id", default=1, type=int, help="World ID to tag units/events with")
@click.option("--interval", default=30.0, type=float, help="Seconds between polls")
@click.option("--bridge-host", default='', type=str,
              help="Host for Lua bridge HTTP server (default: same as DFHACK_HOST)")
@click.option("--reports", is_flag=True, help="Collect game reports each cycle")
@click.option("--enriched", is_flag=True, help="Enrich units with RFR data (inventory, wounds)")
@click.option("--probe-interval", default=0.0, type=float,
              help="Run Lua probes every N seconds (0 = disabled)")
def watch(world_id, interval, bridge_host, reports, enriched, probe_interval):
    """Continuously poll DFHack and log changes to the CDM."""
    import signal as sig

    from chronicler.db.connection import get_pool, close_pool
    from chronicler.dfhack.watcher import watch_loop, _handle_signal, _shutdown

    async def _run_watch():
        # Register signal handlers for graceful shutdown
        sig.signal(sig.SIGINT, _handle_signal)
        sig.signal(sig.SIGTERM, _handle_signal)

        pool = await get_pool()
        streams = []
        if bridge_host:
            streams.append(f"bridge@{bridge_host}")
        if reports:
            streams.append("reports")
        if enriched:
            streams.append("enriched")
        if probe_interval > 0:
            streams.append(f"probes every {probe_interval}s")
        stream_str = f" + {', '.join(streams)}" if streams else ""
        click.echo(f"Watching DFHack (world_id={world_id}, interval={interval}s{stream_str})")
        click.echo("Press Ctrl+C to stop.\n")

        try:
            await watch_loop(pool, world_id=world_id, interval=interval,
                             bridge_host=bridge_host,
                             enable_reports=reports,
                             enable_enriched=enriched,
                             probe_interval=probe_interval)
        finally:
            await close_pool()
            click.echo("\nWatcher stopped.")

    _run(_run_watch())


@cli.group("worldgen")
def worldgen_group():
    """Monitor, backfill, and explore world generation data."""


@worldgen_group.command("watch")
@click.option("--world-id", default=1, type=int, help="World ID to associate snapshots with")
@click.option("--bridge-host", default='', type=str,
              help="Bridge HTTP host (default: DFHACK_HOST)")
def worldgen_watch(world_id, bridge_host):
    """Monitor world generation progress in real time."""
    import signal as sig

    from chronicler.db.connection import get_pool, close_pool
    from chronicler.dfhack.worldgen import WorldgenIngester

    async def _watch():
        sig.signal(sig.SIGINT, lambda s, f: ingester.stop())
        sig.signal(sig.SIGTERM, lambda s, f: ingester.stop())

        pool = await get_pool()
        click.echo(f"Worldgen monitor started (world_id={world_id})")
        click.echo("Polling for worldgen-status.json every 2s.")
        click.echo("Press Ctrl+C to stop.\n")

        try:
            await ingester.run(pool, world_id=world_id,
                               bridge_host=bridge_host)
        finally:
            await close_pool()
            click.echo("\nWorldgen monitor stopped.")

    ingester = WorldgenIngester()
    _run(_watch())


@worldgen_group.command("backfill")
@click.option("--world-id", required=True, type=int,
              help="World ID to backfill temporal data for")
def worldgen_backfill(world_id):
    """Backfill temporal data from Legends events for a world.

    Runs two post-parse steps:
      1. Backfill sites.founded_year from 'created site' events
      2. Materialize year-by-year world timeline into worldgen_snapshots

    Safe to run multiple times (idempotent).
    """
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.ingest.post_parse import PostParseProcessor

    async def _backfill():
        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                pp = PostParseProcessor(conn, world_id=world_id)
                click.echo(f"Backfilling temporal data for world {world_id}...")

                r1 = await pp.step_9b_backfill_site_temporal_data()
                click.echo(f"  Sites: {r1['founded_backfilled']} founded_year, "
                           f"{r1['destroyed_backfilled']} destroyed_year")

                r2 = await pp.step_12_materialize_world_timeline()
                click.echo(f"  Timeline: {r2['years']} year snapshots")
                click.echo("Done.")
        finally:
            await close_pool()

    _run(_backfill())


@worldgen_group.command("history")
@click.option("--world-id", required=True, type=int,
              help="World ID to show timeline for")
def worldgen_history(world_id):
    """Print timeline summary for a world."""
    from chronicler.db.connection import get_pool, close_pool

    async def _history():
        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT year, hf_count, site_count, event_count, data
                    FROM worldgen_snapshots
                    WHERE world_id = $1
                    ORDER BY year
                    """,
                    world_id,
                )
                if not rows:
                    click.echo(f"No timeline data for world {world_id}. "
                               f"Run 'chronicler worldgen backfill --world-id {world_id}' first.")
                    return

                click.echo(f"── World {world_id} Timeline ({len(rows)} years) ──")
                click.echo(f"  {'Year':>5}  {'Living HFs':>10}  {'Sites':>6}  "
                           f"{'Cum Events':>10}  {'Births':>7}  {'Deaths':>7}")
                click.echo(f"  {'─'*5}  {'─'*10}  {'─'*6}  {'─'*10}  {'─'*7}  {'─'*7}")

                # Show every 25th year + first and last
                for r in rows:
                    y = r["year"]
                    if y == 1 or y == len(rows) or y % 25 == 0:
                        data = r["data"] if isinstance(r["data"], dict) else {}
                        click.echo(
                            f"  {y:>5}  {r['hf_count']:>10}  {r['site_count']:>6}  "
                            f"{r['event_count']:>10}  {data.get('births', ''):>7}  "
                            f"{data.get('deaths', ''):>7}"
                        )

                # Summary
                last = rows[-1]
                data = last["data"] if isinstance(last["data"], dict) else {}
                click.echo(f"\n  Final: {last['hf_count']} living HFs, "
                           f"{last['site_count']} sites, "
                           f"{last['event_count']} total events, "
                           f"{data.get('total_born', '?')} total born, "
                           f"{data.get('total_died', '?')} total died")
        finally:
            await close_pool()

    _run(_history())


@cli.command("probe")
@click.option("--world-id", default=1, type=int, help="World ID for storing results")
@click.option("--unit-id", default=None, type=int, help="Probe a specific unit's personality/stress")
@click.option("--store", is_flag=True, help="Store results in the lua_probes table")
def probe(world_id, unit_id, store):
    """Run one-shot Lua probes against DFHack for debugging."""
    from chronicler.config import DFHACK_HOST, DFHACK_PORT
    from chronicler.dfhack.client import DFHackClient
    from chronicler.dfhack.probe import (
        probe_armies, probe_diplomacy, probe_unit_detail, store_probe,
    )

    client = DFHackClient(DFHACK_HOST, DFHACK_PORT)
    client.connect()

    try:
        results = {}
        if unit_id is not None:
            data = probe_unit_detail(client, unit_id)
            results['unit_detail'] = data
            click.echo(f"Unit {unit_id}: {json.dumps(data, indent=2) if data else 'null'}")
        else:
            armies = probe_armies(client)
            results['armies'] = armies
            click.echo(f"Armies: {json.dumps(armies, indent=2) if armies else 'null'}")

            diplomacy = probe_diplomacy(client)
            results['diplomacy'] = diplomacy
            click.echo(f"Diplomacy: {json.dumps(diplomacy, indent=2) if diplomacy else 'null'}")

        if store:
            async def _store():
                from chronicler.db.connection import get_pool, close_pool
                pool = await get_pool()
                # Get game time for timestamps
                world_map = client.get_world_map()
                game_year = world_map['cur_year'] if world_map else None
                game_tick = world_map['cur_year_tick'] if world_map else None
                async with pool.acquire() as conn:
                    for name, data in results.items():
                        if data:
                            await store_probe(conn, world_id, name, data,
                                              game_year, game_tick)
                            click.echo(f"Stored {name} probe result")
                await close_pool()
            _run(_store())
    finally:
        client.close()


@cli.command("rescore")
@click.option("--world-id", required=True, type=int, help="World ID to compute scores for")
def rescore(world_id):
    """Recompute prominence and salience scores for all entities in a world."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.scoring import compute_scores

    async def _run_rescore():
        pool = await get_pool()
        async with pool.acquire() as conn:
            counts = await compute_scores(conn, world_id)

        click.echo("── Scoring Recomputed ──")
        for entity_type, n in sorted(counts.items()):
            click.echo(f"  {entity_type:30s} {n:>8,d} updated")
        await close_pool()

    _run(_run_rescore())


@cli.command("validate-phase1")
@click.option("--world-id", default=1, type=int, help="World ID to validate")
def validate_phase1(world_id):
    """Validate Phase 1 (Data Foundation) Definition of Done criteria."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.ingest.validate_phase1 import Phase1Validator, format_results

    async def _run_validate():
        pool = await get_pool()
        async with pool.acquire() as conn:
            validator = Phase1Validator(conn, world_id)
            results = await validator.run_all()
        await close_pool()
        return results

    results = _run(_run_validate())
    click.echo(format_results(results))

    # Exit with non-zero status if any checks failed
    failed = sum(1 for r in results if not r["passed"])
    if failed > 0:
        raise SystemExit(1)


@cli.command("dump-schema")
@click.option("--output", "-o", "output_path", default=None,
              type=click.Path(), help="Write to file instead of stdout")
def dump_schema(output_path):
    """Print the full CDM database schema (tables, columns, keys, indexes)."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.db.schema_dump import dump_schema as _dump_schema

    async def _run_dump():
        pool = await get_pool()
        async with pool.acquire() as conn:
            text = await _dump_schema(conn)
        await close_pool()
        return text

    text = _run(_run_dump())

    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
        click.echo(f"Schema written to {output_path}")
    else:
        click.echo(text)


@cli.command("erd")
@click.option("--format", "fmt", default="mermaid",
              type=click.Choice(["mermaid", "dot"]),
              help="Output format (default: mermaid)")
@click.option("--output", "-o", "output_path", default=None,
              type=click.Path(), help="Write to file instead of stdout")
def erd(fmt, output_path):
    """Generate an annotated Entity Relationship Diagram of the CDM schema."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.db.erd import generate_mermaid, generate_dot

    async def _run_erd():
        pool = await get_pool()
        async with pool.acquire() as conn:
            if fmt == "mermaid":
                text = await generate_mermaid(conn)
            else:
                text = await generate_dot(conn)
        await close_pool()
        return text

    text = _run(_run_erd())

    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
        ext = ".mmd" if fmt == "mermaid" else ".dot"
        click.echo(f"ERD written to {output_path}")
        if fmt == "mermaid":
            click.echo("  View: open in VS Code (Mermaid extension) or paste into mermaid.live")
        else:
            click.echo("  Render: dot -Tsvg <file> -o erd.svg  (requires Graphviz)")
    else:
        click.echo(text)


@cli.command("validate")
def validate():
    """Query all CDM tables and print row counts."""
    from chronicler.db.connection import get_pool, close_pool

    tables = [
        "worlds", "landmasses", "mountain_peaks", "regions",
        "underground_regions", "sites", "structures", "world_constructions",
        "art_forms", "rivers",
        "entity_populations", "entities", "entity_positions",
        "historical_figures", "hf_links", "hf_entity_links",
        "hf_site_links", "hf_position_links", "identities",
        "history_events", "history_event_collections",
        "collection_events", "collection_subcollections",
        "event_relationships", "event_entity_xref",
        "artifacts", "written_contents", "historical_eras",
        "units", "unit_events", "embeddings",
        "sync_snapshots", "game_reports",
        "world_map_snapshots", "lua_probes", "fortress_denizens",
        "worldgen_snapshots", "world_modpacks", "storyteller_log",
        # Stage 3.5: Fortress State Capture
        "fortress_state_snapshots", "threat_tracking", "character_arcs",
        "environmental_state", "death_narratives", "session_markers",
    ]

    async def _run_validate():
        pool = await get_pool()
        click.echo("── CDM Table Row Counts ──")
        total = 0
        async with pool.acquire() as conn:
            for table in tables:
                try:
                    n = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    click.echo(f"  {table:40s} {n:>8,d}")
                    total += n
                except Exception:
                    click.echo(f"  {table:40s}    ERROR")
        click.echo(f"  {'TOTAL':40s} {total:>8,d}")
        await close_pool()

    _run(_run_validate())


@cli.command("denizens")
@click.option("--world-id", default=1, type=int, help="World ID to query")
@click.option("--status", "status_filter", default=None,
              type=click.Choice(["resident", "deceased", "missing", "departed",
                                 "visitor", "attacker", "skulker", "historical"]),
              help="Filter by status")
@click.option("--sort", "sort_by", default="narrative_value",
              type=click.Choice(["narrative_value", "name", "status", "arrival_year"]),
              help="Sort column")
@click.option("--limit", default=50, type=int, help="Max rows to display")
def denizens(world_id, status_filter, sort_by, limit):
    """Show the fortress denizen registry."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.denizens import get_fortress_denizens

    async def _run_denizens():
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await get_fortress_denizens(
                conn, world_id,
                status_filter=status_filter,
                sort_by=sort_by,
                limit=limit,
            )

        if not rows:
            click.echo("No denizens found. Run 'chronicler watch' first.")
            await close_pool()
            return

        # Header
        click.echo(f"── Fortress Denizens (world {world_id}) ──")
        click.echo(f"{'Name':<30s} {'Status':<12s} {'Race':<15s} "
                   f"{'Embark':<8s} {'NVS':>6s} {'HF':>6s} {'Unit':>6s}")
        click.echo("─" * 90)

        for r in rows:
            embark = "★" if r['embark'] else ""
            hf_str = str(r['hf_id']) if r['hf_id'] else "—"
            unit_str = str(r['unit_id']) if r['unit_id'] else "—"
            nvs_str = f"{r['narrative_value']:.1f}" if r['narrative_value'] else "0.0"
            name = r['name'] or '(unnamed)'
            english = f" ({r['english_name']})" if r.get('english_name') else ""

            click.echo(f"{(name + english):<30s} {r['status']:<12s} "
                       f"{(r['race'] or '?'):<15s} {embark:<8s} "
                       f"{nvs_str:>6s} {hf_str:>6s} {unit_str:>6s}")

        # Summary
        status_counts = {}
        for r in rows:
            s = r['status']
            status_counts[s] = status_counts.get(s, 0) + 1
        summary = ", ".join(f"{v} {k}" for k, v in sorted(status_counts.items()))
        embark_count = sum(1 for r in rows if r['embark'])
        click.echo(f"\nTotal: {len(rows)} denizens ({summary})")
        if embark_count:
            click.echo(f"Embark dwarves: {embark_count} (★)")

        await close_pool()

    _run(_run_denizens())


# ── Game control ─────────────────────────────────────────────────────────

@cli.group("control")
def control_group():
    """Control the live DF game (pause, unpause, step, status)."""


def _get_controller(host):
    """Create a GameController (SSH-based, no persistent connection)."""
    from chronicler.dfhack.controller import GameController
    return GameController(host=host)


@control_group.command("status")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
def control_status(host):
    """Show current game status (time, pause state, fortress info)."""
    ctrl = _get_controller(host)
    s = ctrl.get_status()
    pause_str = "PAUSED" if s["paused"] else "RUNNING"
    click.echo(f"── Game Status ──")
    click.echo(f"  Fortress:  {s['fortress_name']}")
    click.echo(f"  Citizens:  {s['citizen_count']}")
    click.echo(f"  Year:      {s['cur_year']}")
    click.echo(f"  Season:    {s['season']}")
    click.echo(f"  Tick:      {s['cur_year_tick']}")
    click.echo(f"  State:     {pause_str}")


@control_group.command("pause")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
def control_pause(host):
    """Pause the game."""
    ctrl = _get_controller(host)
    if ctrl.pause():
        click.echo("Game paused.")
    else:
        click.echo("Warning: pause command sent but game may not be paused.")


@control_group.command("unpause")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
def control_unpause(host):
    """Unpause the game."""
    ctrl = _get_controller(host)
    if ctrl.unpause():
        click.echo("Game unpaused.")
    else:
        click.echo("Warning: unpause command sent but game may still be paused.")


@control_group.command("step")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
@click.option("--ticks", default=100, type=int, help="Ticks to advance (default: 100)")
@click.option("--timeout", default=0, type=float,
              help="Max seconds to wait (0=auto-scale based on tick count)")
def control_step(host, ticks, timeout):
    """Advance the game by N ticks then re-pause."""
    ctrl = _get_controller(host)
    click.echo(f"Stepping {ticks} ticks...")
    result = ctrl.step(ticks=ticks, timeout=timeout)
    click.echo(f"  Start:   Y{result['start_year']} T{result['start_tick']}")
    click.echo(f"  End:     Y{result['end_year']} T{result['end_tick']}")
    click.echo(f"  Elapsed: {result['elapsed_ticks']} ticks")
    click.echo(f"  Season:  {result['season']}")


@control_group.command("bridge")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
@click.option("--setup-repeat", is_flag=True,
              help="Register bridge as DFHack repeating job (every 100 ticks)")
def control_bridge(host, setup_repeat):
    """Run the bridge script and/or fetch bridge data."""
    ctrl = _get_controller(host)

    if setup_repeat:
        click.echo("Registering bridge as repeating job...")
        output = ctrl.setup_bridge_repeat()
        click.echo(f"  {output}" if output else "  Registered.")

    click.echo("Running bridge script...")
    output = ctrl.run_bridge()
    click.echo(f"  {output}" if output else "  Done.")

    click.echo("Fetching bridge data via SSH...")
    data = ctrl.fetch_bridge_data()
    if data:
        sections = [k for k in data.keys() if k not in
                    ('cur_year', 'cur_year_tick', 'cur_season',
                     'creature_raws', 'creature_count', 'timestamp',
                     'bridge_version', 'errors')]
        click.echo(f"  Bridge v{data.get('bridge_version', '?')}")
        click.echo(f"  Year {data.get('cur_year')}, Tick {data.get('cur_year_tick')}")
        click.echo(f"  Creatures: {data.get('creature_count', 0)}")
        click.echo(f"  Sections ({len(sections)}): {', '.join(sections)}")
    else:
        click.echo("  Failed to fetch bridge data.")


@control_group.command("save")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
def control_save(host):
    """Quicksave the game (should be paused first)."""
    ctrl = _get_controller(host)
    if not ctrl.is_paused():
        click.echo("Warning: game is not paused. Pausing first...")
        ctrl.pause()
    click.echo("Saving...")
    ctrl.save()
    click.echo("Quicksave complete.")


@control_group.command("exec")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
@click.argument("lua_code")
def control_exec(host, lua_code):
    """Execute raw Lua code via dfhack-run and print the output.

    Useful for ad-hoc introspection of DF memory structures.

    Examples:

      chronicler control exec "print(df.global.cur_year)"

      chronicler control exec "for k,v in pairs(df.global.world) do print(k) end"
    """
    ctrl = _get_controller(host)
    output = ctrl.execute_lua(lua_code)
    if output:
        click.echo(output)
    else:
        click.echo("(no output)")


@control_group.command("citizens")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
def control_citizens(host):
    """List all living citizens with name, profession, sex, and age."""
    ctrl = _get_controller(host)
    citizens = ctrl.get_citizens()
    if not citizens:
        click.echo("No citizens found.")
        return
    click.echo(f"── Citizens ({len(citizens)}) ──")
    # Column headers
    click.echo(f"  {'ID':>6}  {'Name':<28} {'Profession':<22} {'Sex':>3}  {'Age':>3}")
    click.echo(f"  {'─'*6}  {'─'*28} {'─'*22} {'─'*3}  {'─'*3}")
    for c in sorted(citizens, key=lambda x: x["name"]):
        click.echo(
            f"  {c['id']:>6}  {c['name']:<28} {c['profession']:<22} "
            f"{c['sex']:>3}  {c['age']:>3}"
        )


@control_group.command("speed")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
@click.argument("level", type=int)
def control_speed(host, level):
    """Set game speed (1=slow/10fps, 2=normal/50fps, 3=fast/100fps, 4=max)."""
    ctrl = _get_controller(host)
    output = ctrl.set_speed(level)
    click.echo(f"Speed set to {level}: {output}")


@control_group.command("announce")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
@click.option("--limit", default=20, type=int, help="Number of announcements to show")
def control_announce(host, limit):
    """Show recent game announcements/log entries."""
    ctrl = _get_controller(host)
    announcements = ctrl.get_announcements(limit=limit)
    if not announcements:
        click.echo("No announcements found.")
        return
    click.echo(f"── Announcements (last {len(announcements)}) ──")
    for a in announcements:
        click.echo(f"  Y{a['year']} T{a['tick']:>6}: {a['text']}")


@control_group.command("probe")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
@click.argument("path")
def control_probe(host, path):
    """Introspect a df.global path — show type and fields.

    Used for mapping DF memory structures to CDM tables.

    Examples:

      chronicler control probe "df.global.world.units.active[0]"

      chronicler control probe "df.global.world.sites.all[0]"

      chronicler control probe "df.global.world.history"
    """
    ctrl = _get_controller(host)
    output = ctrl.probe_path(path)
    if output:
        click.echo(output)
    else:
        click.echo("(no output — path may be nil)")


@control_group.command("fields")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
@click.argument("path")
def control_fields(host, path):
    """Enumerate fields of a DF object with types and sample values.

    More detailed than 'probe' — shows field name, Lua type, and value.

    Examples:

      chronicler control fields "df.global.world.units.active[0].status"

      chronicler control fields "df.global.world.units.active[0].status.current_soul"
    """
    ctrl = _get_controller(host)
    output = ctrl.enumerate_fields(path)
    if output:
        # Format as a table
        click.echo(f"── Fields of {path} ──")
        click.echo(f"  {'Field':<30} {'Type':<12} {'Value'}")
        click.echo(f"  {'─'*30} {'─'*12} {'─'*40}")
        for line in output.strip().splitlines():
            parts = line.split('\t', 2)
            if len(parts) >= 3:
                click.echo(f"  {parts[0]:<30} {parts[1]:<12} {parts[2]}")
            else:
                click.echo(f"  {line}")
    else:
        click.echo("(no output — path may be nil)")


@control_group.command("stream")
@click.option("--host", default="192.168.64.3", help="VM host (SSH)")
@click.option("--ticks", default=100, type=int,
              help="Ticks per step (default: 100, ~2 in-game hours)")
@click.option("--cycles", default=10, type=int,
              help="Number of step+collect cycles (default: 10)")
@click.option("--interval", default=1.0, type=float,
              help="Seconds to wait between cycles (default: 1)")
@click.option("--timeout", default=30.0, type=float,
              help="Max seconds per step (default: 30)")
@click.option("--dry-run", is_flag=True,
              help="Step and collect but don't ingest into DB")
def control_stream(host, ticks, cycles, interval, timeout, dry_run):
    """Step-and-collect loop: advance game, capture bridge data, ingest.

    Orchestrates the game control + data pipeline:
      1. Step game by N ticks (unpause → poll → re-pause)
      2. Run bridge script to snapshot current state
      3. Read bridge JSON via SSH
      4. Ingest bridge data into PostgreSQL
      5. Repeat for --cycles iterations

    Example: chronicler control stream --ticks 500 --cycles 20
    """
    import asyncio
    import signal as sig
    from chronicler.dfhack.controller import GameController, ControllerError
    from chronicler.dfhack.ingest_live import DeltaDetector

    ctrl = GameController(host=host)
    delta_detector = DeltaDetector()  # persists across cycles for CDC

    # Verify connectivity
    try:
        status = ctrl.get_status()
    except ControllerError as e:
        click.echo(f"Cannot connect to game: {e}")
        return

    click.echo(f"── Streaming from {status['fortress_name']} ──")
    click.echo(f"  Citizens: {status['citizen_count']}, "
               f"Y{status['cur_year']} {status['season']}")
    click.echo(f"  Plan: {cycles} cycles x {ticks} ticks "
               f"= ~{cycles * ticks} total ticks")
    if dry_run:
        click.echo("  Mode: DRY RUN (no DB ingestion)")
    click.echo()

    # Ensure bridge script is deployed
    click.echo("Initializing bridge...")
    ctrl.run_bridge()

    stopped = False

    def _signal_handler(signum, frame):
        nonlocal stopped
        click.echo("\nStopping after current cycle...")
        stopped = True

    old_handler = sig.signal(sig.SIGINT, _signal_handler)

    total_ticks = 0
    total_sections = 0

    try:
        for cycle in range(1, cycles + 1):
            if stopped:
                break

            # Step + collect
            try:
                result = ctrl.step_and_collect(
                    ticks=ticks, timeout=timeout)
            except ControllerError as e:
                click.echo(f"  Cycle {cycle}: ERROR - {e}")
                break

            step = result["step"]
            bridge = result.get("bridge_data")
            total_ticks += step["elapsed_ticks"]

            # Count sections in bridge data
            n_sections = 0
            if bridge:
                n_sections = len([k for k in bridge.keys() if k not in
                                  ('cur_year', 'cur_year_tick', 'cur_season',
                                   'creature_raws', 'creature_count',
                                   'timestamp', 'bridge_version', 'errors')])
                total_sections += n_sections

            # Ingest if not dry run
            ingested = False
            etl_info = ""
            if not dry_run and bridge:
                try:
                    result = asyncio.run(_ingest_bridge_cycle(
                        bridge, step, world_id=1,
                        delta_detector=delta_detector))
                    ingested = bool(result and result.get("stored"))
                    etl = result.get("etl", {})
                    if etl:
                        etl_info = (
                            f" | {etl.get('units_upserted', 0)}u "
                            f"{etl.get('events_generated', 0)}ev "
                            f"+{etl.get('denizens', {}).get('added', 0)}d"
                        )
                except Exception as e:
                    click.echo(f"  Cycle {cycle}: ingest error - {e}")

            # Status line
            status_char = "+" if ingested else ("~" if bridge else "!")
            click.echo(
                f"  [{status_char}] Cycle {cycle}/{cycles}: "
                f"+{step['elapsed_ticks']}t → Y{step['end_year']} "
                f"T{step['end_tick']} {step['season']} "
                f"({n_sections} sections){etl_info}"
            )

            # Inter-cycle pause
            if cycle < cycles and interval > 0 and not stopped:
                time.sleep(interval)

    finally:
        sig.signal(sig.SIGINT, old_handler)

    # Final status
    end_status = ctrl.get_status()
    click.echo()
    click.echo(f"── Stream Complete ──")
    click.echo(f"  Cycles:   {cycle if stopped else cycles}")
    click.echo(f"  Ticks:    {total_ticks}")
    click.echo(f"  Sections: {total_sections}")
    click.echo(f"  Now:      Y{end_status['cur_year']} "
               f"T{end_status['cur_year_tick']} {end_status['season']}")
    click.echo(f"  Citizens: {end_status['citizen_count']}")
    click.echo(f"  State:    {'PAUSED' if end_status['paused'] else 'RUNNING'}")


async def _ingest_bridge_cycle(bridge_data: dict, step_result: dict,
                                world_id: int = 1,
                                delta_detector=None) -> dict:
    """Ingest one cycle of bridge data into the CDM.

    Layer 1: Raw staging — stores bridge sections in lua_probes.
    Layer 2+3: Transform + load — upserts units, generates unit_events,
               syncs fortress_denizens via ingest_live.

    Returns summary dict (or empty dict on failure).
    """
    import json as _json
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.dfhack.ingest_live import ingest_bridge_live

    pool = await get_pool()
    try:
        game_year = bridge_data.get('cur_year')
        game_tick = bridge_data.get('cur_year_tick')

        async with pool.acquire() as conn:
            # ── Layer 1: Raw staging (lua_probes) ──────────────────
            sections = ['armies', 'buildings', 'artifacts', 'announcements',
                        'diplomacy', 'history', 'unit_summary',
                        'world_info', 'entities', 'dwarf_skills',
                        'dwarf_emotions', 'dwarf_personality', 'zones',
                        'event_collections', 'squads', 'mandates', 'incidents',
                        'reactive_events', 'skill_changes']

            stored = 0
            for section in sections:
                data = bridge_data.get(section)
                if data:
                    await conn.execute(
                        """
                        INSERT INTO lua_probes (world_id, probe_name, data,
                                                game_year, game_tick)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        world_id, section, _json.dumps(data),
                        game_year, game_tick,
                    )
                    stored += 1

            # Record snapshot
            unit_count = 0
            if bridge_data.get('unit_summary'):
                units = bridge_data['unit_summary'].get('fortress_units', [])
                unit_count = len(units)

            await conn.execute(
                """
                INSERT INTO sync_snapshots (world_id, unit_count, event_count,
                                            game_year, game_tick)
                VALUES ($1, $2, $3, $4, $5)
                """,
                world_id, unit_count, 0, game_year, game_tick,
            )

            # ── Layer 2+3: Transform + Load (CDM tables) ──────────
            etl_summary = await ingest_bridge_live(
                conn, bridge_data, world_id,
                delta_detector=delta_detector,
            )

        return {
            "stored": stored,
            "etl": etl_summary,
        }
    finally:
        await close_pool()


@cli.command("extract-biome")
@click.option("--world-id", default=1, type=int, help="World ID to associate biome data with")
@click.option("--bridge-host", default='', type=str,
              help="Bridge HTTP host (default: DFHACK_HOST)")
def extract_biome(world_id, bridge_host):
    """Fetch biome/terrain data from the bridge and store in world_terrain table."""
    from chronicler.config import DFHACK_HOST, BRIDGE_PORT
    from chronicler.dfhack.bridge import fetch_biome_data
    from chronicler.db.connection import get_pool, close_pool

    host = bridge_host or DFHACK_HOST
    click.echo(f"Fetching biome data from {host}:{BRIDGE_PORT}...")

    data = fetch_biome_data(host, BRIDGE_PORT)
    if not data:
        click.echo("ERROR: Could not fetch biome data. Is the bridge running?", err=True)
        raise SystemExit(1)

    width = data['width']
    height = data['height']
    click.echo(f"Received {width}x{height} = {width * height} tiles, "
               f"{len(data.get('region_types', {}))} region types")

    # Separate tile arrays from metadata for storage
    tile_keys = ['elevation', 'rainfall', 'vegetation', 'temperature',
                 'evilness', 'drainage', 'volcanism', 'savagery',
                 'salinity', 'region_id', 'landmass_id']
    tile_data = {k: data[k] for k in tile_keys if k in data}

    async def _store():
        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO world_terrain (world_id, width, height, data, region_types)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                    ON CONFLICT (world_id) DO UPDATE SET
                        width = EXCLUDED.width,
                        height = EXCLUDED.height,
                        data = EXCLUDED.data,
                        region_types = EXCLUDED.region_types,
                        extracted_at = now()
                    """,
                    world_id, width, height,
                    json.dumps(tile_data),
                    json.dumps(data.get('region_types', {})),
                )
                click.echo(f"Stored biome data for world_id={world_id}")
        finally:
            await close_pool()

    _run(_store())


# ── Knowledge Horizon ────────────────────────────────────────────────────────

@cli.group("kh")
def kh_group():
    """Knowledge Horizon — visibility masking for fortress perspective."""


@kh_group.command("init")
@click.option("--world-id", default=1, type=int, help="World ID")
def kh_init(world_id):
    """Initialize Knowledge Horizon for a world (runs all phases)."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.kh import KnowledgeHorizonEngine

    async def _run_init():
        pool = await get_pool()
        try:
            engine = KnowledgeHorizonEngine(pool, world_id)
            counts = await engine.initialize()

            click.echo(f"Knowledge Horizon initialized for world {world_id}:")
            for k, v in counts.items():
                click.echo(f"  {k}: {v}")
        finally:
            await close_pool()

    _run(_run_init())


@kh_group.command("stats")
@click.option("--world-id", default=1, type=int, help="World ID")
def kh_stats(world_id):
    """Show Knowledge Horizon coverage statistics."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.kh import KnowledgeHorizonEngine

    async def _run_stats():
        pool = await get_pool()
        try:
            engine = KnowledgeHorizonEngine(pool, world_id)
            stats = await engine.get_stats()

            click.echo(f"Knowledge Horizon — World {world_id}:")
            click.echo(f"{'Type':<12} {'Visible':>8} {'Total':>8} {'Coverage':>8}")
            click.echo("-" * 40)
            for etype in ("hf", "entity", "site", "region", "artifact"):
                v = stats["visible"].get(etype, 0)
                t = stats["total"].get(etype, 0)
                pct = stats["coverage_pct"].get(etype, 0)
                click.echo(f"{etype:<12} {v:>8,} {t:>8,} {pct:>7.1f}%")
        finally:
            await close_pool()

    _run(_run_stats())


@kh_group.command("clear")
@click.option("--world-id", default=1, type=int, help="World ID")
@click.confirmation_option(prompt="Clear all KH data for this world?")
def kh_clear(world_id):
    """Clear Knowledge Horizon data for a world."""
    from chronicler.db.connection import get_pool, close_pool

    async def _run_clear():
        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM knowledge_horizon WHERE world_id = $1",
                    world_id,
                )
                click.echo(f"Cleared KH data: {result}")
        finally:
            await close_pool()

    _run(_run_clear())


# ── Stage 3.5 Validation ────────────────────────────────────────────────────

@cli.command("validate-stage35")
@click.option("--world-id", default=1, type=int, help="World ID to validate")
def validate_stage35(world_id):
    """Validate Stage 3.5 (Fortress State Capture) — all PRD criteria."""
    from chronicler.db.connection import get_pool, close_pool

    checks = []

    async def _run_validate():
        pool = await get_pool()
        async with pool.acquire() as conn:
            # ── Check 1: fortress_state_snapshots ≥ 50 entries ──────────
            n = await conn.fetchval(
                "SELECT COUNT(*) FROM fortress_state_snapshots WHERE world_id = $1",
                world_id,
            )
            checks.append({
                "name": "fortress_state_snapshots ≥ 50 entries",
                "passed": n >= 50,
                "detail": f"{n} rows",
            })

            # Show sample if present
            if n > 0:
                latest = await conn.fetchrow(
                    "SELECT year, season, population, military_count, wealth "
                    "FROM fortress_state_snapshots WHERE world_id = $1 "
                    "ORDER BY tick DESC LIMIT 1",
                    world_id,
                )
                if latest:
                    checks[-1]["detail"] += (
                        f" | latest: Y{latest['year']} {latest['season'] or '?'}, "
                        f"pop={latest['population']}, mil={latest['military_count']}, "
                        f"wealth={latest['wealth']}"
                    )

            # ── Check 2: game_reports with combat category ──────────────
            combat_n = await conn.fetchval(
                "SELECT COUNT(*) FROM game_reports "
                "WHERE world_id = $1 AND category = 'combat'",
                world_id,
            )
            checks.append({
                "name": "game_reports: combat reports captured",
                "passed": combat_n > 0,
                "detail": f"{combat_n} combat reports",
            })

            # ── Check 3: ≥ 5 distinct announcement categories ──────────
            cats = await conn.fetch(
                "SELECT category, COUNT(*) AS n FROM game_reports "
                "WHERE world_id = $1 AND category IS NOT NULL "
                "GROUP BY category ORDER BY n DESC",
                world_id,
            )
            cat_names = [r["category"] for r in cats]
            cat_summary = ", ".join(f"{r['category']}={r['n']}" for r in cats)
            checks.append({
                "name": "game_reports: ≥ 5 distinct categories",
                "passed": len(cat_names) >= 5,
                "detail": f"{len(cat_names)} categories: {cat_summary}" if cats else "0 categories",
            })

            # ── Check 4: threat_tracking records ────────────────────────
            threat_n = await conn.fetchval(
                "SELECT COUNT(*) FROM threat_tracking WHERE world_id = $1",
                world_id,
            )
            max_hostile = await conn.fetchval(
                "SELECT COALESCE(MAX(hostile_count), 0) FROM threat_tracking "
                "WHERE world_id = $1",
                world_id,
            )
            checks.append({
                "name": "threat_tracking populated",
                "passed": threat_n > 0,
                "detail": f"{threat_n} rows, peak hostile={max_hostile}",
            })

            # ── Check 5: character_arcs delta detection ─────────────────
            arc_n = await conn.fetchval(
                "SELECT COUNT(*) FROM character_arcs WHERE world_id = $1",
                world_id,
            )
            # Check for duplicates (same unit, consecutive ticks with identical data)
            dup_n = await conn.fetchval("""
                SELECT COUNT(*) FROM (
                    SELECT unit_id, tick,
                           LAG(skill_snapshot) OVER (
                               PARTITION BY unit_id ORDER BY tick
                           ) AS prev_skills,
                           skill_snapshot,
                           LAG(stress_level) OVER (
                               PARTITION BY unit_id ORDER BY tick
                           ) AS prev_stress,
                           stress_level,
                           LAG(profession) OVER (
                               PARTITION BY unit_id ORDER BY tick
                           ) AS prev_prof,
                           profession
                    FROM character_arcs WHERE world_id = $1
                ) sub
                WHERE prev_skills = skill_snapshot
                  AND prev_stress = stress_level
                  AND prev_prof = profession
            """, world_id)
            distinct_units = await conn.fetchval(
                "SELECT COUNT(DISTINCT unit_id) FROM character_arcs WHERE world_id = $1",
                world_id,
            )
            checks.append({
                "name": "character_arcs: delta detection (no useless dupes)",
                "passed": arc_n > 0 and dup_n == 0,
                "detail": f"{arc_n} rows, {distinct_units} units, {dup_n} identical consecutive snapshots",
            })

            # ── Check 6: death_narratives links combat_report_ids ───────
            death_n = await conn.fetchval(
                "SELECT COUNT(*) FROM death_narratives WHERE world_id = $1",
                world_id,
            )
            linked_n = await conn.fetchval(
                "SELECT COUNT(*) FROM death_narratives "
                "WHERE world_id = $1 AND combat_report_ids IS NOT NULL "
                "AND combat_report_ids != '[]'::jsonb",
                world_id,
            )
            checks.append({
                "name": "death_narratives populated",
                "passed": death_n > 0,
                "detail": f"{death_n} deaths, {linked_n} with combat report links",
            })

            # ── Check 7: session_markers with season_change ─────────────
            marker_n = await conn.fetchval(
                "SELECT COUNT(*) FROM session_markers WHERE world_id = $1",
                world_id,
            )
            season_n = await conn.fetchval(
                "SELECT COUNT(*) FROM session_markers "
                "WHERE world_id = $1 AND event_type = 'season_change'",
                world_id,
            )
            types = await conn.fetch(
                "SELECT event_type, COUNT(*) AS n FROM session_markers "
                "WHERE world_id = $1 GROUP BY event_type ORDER BY n DESC",
                world_id,
            )
            type_summary = ", ".join(f"{r['event_type']}={r['n']}" for r in types)
            checks.append({
                "name": "session_markers: season_change detected",
                "passed": season_n > 0,
                "detail": f"{marker_n} markers ({type_summary})" if types else "0 markers",
            })

            # ── Check 8: environmental_state populated ──────────────────
            env_n = await conn.fetchval(
                "SELECT COUNT(*) FROM environmental_state WHERE world_id = $1",
                world_id,
            )
            checks.append({
                "name": "environmental_state populated",
                "passed": env_n > 0,
                "detail": f"{env_n} rows",
            })

            # ── Check 9: Schema tables exist ────────────────────────────
            stage35_tables = [
                "fortress_state_snapshots", "threat_tracking",
                "character_arcs", "environmental_state",
                "death_narratives", "session_markers",
            ]
            existing = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "AND tablename = ANY($1)",
                stage35_tables,
            )
            existing_names = {r["tablename"] for r in existing}
            missing = [t for t in stage35_tables if t not in existing_names]
            checks.append({
                "name": "all 6 Stage 3.5 tables exist",
                "passed": len(missing) == 0,
                "detail": f"{len(existing_names)}/6 tables"
                + (f" (missing: {', '.join(missing)})" if missing else ""),
            })

        await close_pool()

    _run(_run_validate())

    # ── Print results ───────────────────────────────────────────────
    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)

    click.echo(f"\n── Stage 3.5 Validation (world {world_id}) ──")
    click.echo(f"{'#':<4} {'Status':<8} {'Check':<50} {'Detail'}")
    click.echo("─" * 100)
    for i, c in enumerate(checks, 1):
        status = "PASS" if c["passed"] else "FAIL"
        marker = "✓" if c["passed"] else "✗"
        click.echo(f"{i:<4} {marker} {status:<5} {c['name']:<50} {c['detail']}")
    click.echo("─" * 100)
    click.echo(f"Result: {passed}/{total} checks passed")

    if passed < total:
        click.echo(
            "\nNote: Some checks require live data. Run 'chronicler watch' "
            "with an active DF session to populate Stage 3.5 tables."
        )
        raise SystemExit(1)
    else:
        click.echo("\nStage 3.5: Fortress State Capture — ALL CHECKS PASSED")


@cli.command("validate-stage36")
@click.option("--world-id", default=1, type=int, help="World ID to validate")
def validate_stage36(world_id):
    """Validate Stage 3.6 (Narrative Data Layer) — all PRD criteria."""
    from chronicler.db.connection import get_pool, close_pool

    checks = []

    async def _run_validate():
        pool = await get_pool()
        async with pool.acquire() as conn:
            # ── Check 1: narrative_events table populated (3.6.1) ─────
            ne_n = await conn.fetchval(
                "SELECT COUNT(*) FROM narrative_events WHERE world_id = $1",
                world_id)
            checks.append({
                "name": "3.6.1 narrative_events populated",
                "passed": ne_n > 0,
                "detail": f"{ne_n:,} scored events",
            })

            # Check scoring fields present
            sample = await conn.fetchrow(
                "SELECT narrative_weight, drama_score, emotional_tone, irony_flags "
                "FROM narrative_events WHERE world_id = $1 LIMIT 1", world_id)
            has_fields = sample is not None and all(
                sample[f] is not None for f in
                ("narrative_weight", "drama_score", "emotional_tone"))
            checks.append({
                "name": "3.6.1 scoring fields populated (weight, drama, tone)",
                "passed": has_fields,
                "detail": f"weight={sample['narrative_weight']:.1f}, "
                          f"drama={sample['drama_score']:.1f}, "
                          f"tone={sample['emotional_tone']}" if sample else "no data",
            })

            # ── Check 2: event_causal_links (3.6.2) ──────────────────
            ecl_n = await conn.fetchval(
                "SELECT COUNT(*) FROM event_causal_links WHERE world_id = $1",
                world_id)
            link_types = await conn.fetch(
                "SELECT link_type, COUNT(*) AS n FROM event_causal_links "
                "WHERE world_id = $1 GROUP BY link_type ORDER BY n DESC",
                world_id)
            type_summary = ", ".join(f"{r['link_type']}={r['n']}" for r in link_types)
            checks.append({
                "name": "3.6.2 event_causal_links populated",
                "passed": ecl_n > 0 and len(link_types) >= 2,
                "detail": f"{ecl_n:,} links ({type_summary})",
            })

            # ── Check 3: narrative_arcs (3.6.3) ──────────────────────
            na_n = await conn.fetchval(
                "SELECT COUNT(*) FROM narrative_arcs WHERE world_id = $1",
                world_id)
            titled_n = await conn.fetchval(
                "SELECT COUNT(*) FROM narrative_arcs WHERE world_id = $1 "
                "AND title IS NOT NULL AND title != ''", world_id)
            arc_types = await conn.fetch(
                "SELECT arc_type, COUNT(*) AS n FROM narrative_arcs "
                "WHERE world_id = $1 GROUP BY arc_type ORDER BY n DESC",
                world_id)
            arc_summary = ", ".join(f"{r['arc_type']}={r['n']}" for r in arc_types)
            checks.append({
                "name": "3.6.3 narrative_arcs: ≥ 3 arc types detected",
                "passed": na_n > 0 and len(arc_types) >= 3,
                "detail": f"{na_n:,} arcs, {titled_n} titled ({arc_summary})",
            })

            # ── Check 4: event_summaries (3.6.4) ─────────────────────
            es_n = await conn.fetchval(
                "SELECT COUNT(*) FROM event_summaries WHERE world_id = $1",
                world_id)
            checks.append({
                "name": "3.6.4 event_summaries: year summaries generated",
                "passed": es_n >= 10,
                "detail": f"{es_n} summaries",
            })

            # Check summary quality — non-empty text
            empty_n = await conn.fetchval(
                "SELECT COUNT(*) FROM event_summaries WHERE world_id = $1 "
                "AND (summary_text IS NULL OR length(summary_text) < 20)",
                world_id)
            checks.append({
                "name": "3.6.4 summary quality: all ≥ 20 chars",
                "passed": empty_n == 0,
                "detail": f"{empty_n} empty/short summaries",
            })

            # ── Check 5: fortress_timeline API (3.6.5) ───────────────
            # Verify the timeline query works
            timeline_n = await conn.fetchval("""
                SELECT COUNT(*) FROM history_events he
                JOIN narrative_events ne
                    ON ne.world_id = he.world_id AND ne.event_id = he.id
                WHERE he.world_id = $1 AND ne.narrative_weight >= 5
            """, world_id)
            checks.append({
                "name": "3.6.5 fortress timeline: query returns results",
                "passed": timeline_n > 0,
                "detail": f"{timeline_n:,} events with weight ≥ 5",
            })

            # ── Check 6: character_narratives (3.6.6) ────────────────
            cn_n = await conn.fetchval(
                "SELECT COUNT(*) FROM character_narratives WHERE world_id = $1",
                world_id)
            with_voice = await conn.fetchval(
                "SELECT COUNT(*) FROM character_narratives WHERE world_id = $1 "
                "AND personality_voice IS NOT NULL AND personality_voice != ''",
                world_id)
            checks.append({
                "name": "3.6.6 character_narratives: profiles generated",
                "passed": cn_n >= 5,
                "detail": f"{cn_n} profiles, {with_voice} with personality voice",
            })

            # ── Check 7: narrative_context assembler (3.6.7) ─────────
            from chronicler.storyteller.narrative_context import assemble_context
            ctx = await assemble_context(conn, world_id, "world_overview")
            checks.append({
                "name": "3.6.7 context assembler: world_overview works",
                "passed": ctx.total_tokens > 0 and len(ctx.blocks) >= 3,
                "detail": f"{len(ctx.blocks)} blocks, ~{ctx.total_tokens} tokens",
            })

            ctx2 = await assemble_context(conn, world_id, "fortress_saga")
            checks.append({
                "name": "3.6.7 context assembler: fortress_saga works",
                "passed": ctx2.total_tokens > 0,
                "detail": f"{len(ctx2.blocks)} blocks, ~{ctx2.total_tokens} tokens",
            })

            # ── Check 8: event_clusters (3.6.8) ──────────────────────
            ec_n = await conn.fetchval(
                "SELECT COUNT(*) FROM event_clusters WHERE world_id = $1",
                world_id)
            summarized_n = await conn.fetchval(
                "SELECT COUNT(*) FROM event_clusters WHERE world_id = $1 "
                "AND summary IS NOT NULL AND summary != ''", world_id)
            cluster_types = await conn.fetch(
                "SELECT cluster_type, COUNT(*) AS n FROM event_clusters "
                "WHERE world_id = $1 GROUP BY cluster_type ORDER BY n DESC",
                world_id)
            cl_summary = ", ".join(f"{r['cluster_type']}={r['n']}" for r in cluster_types)
            checks.append({
                "name": "3.6.8 event_clusters: ≥ 3 cluster types",
                "passed": ec_n > 0 and len(cluster_types) >= 3,
                "detail": f"{ec_n:,} clusters, {summarized_n} summarized ({cl_summary})",
            })

            # ── Check 9: Schema completeness ─────────────────────────
            stage36_tables = [
                "narrative_events", "event_causal_links", "narrative_arcs",
                "event_summaries", "character_narratives", "event_clusters",
            ]
            existing = await conn.fetch(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "AND tablename = ANY($1)",
                stage36_tables)
            existing_names = {r["tablename"] for r in existing}
            missing = [t for t in stage36_tables if t not in existing_names]
            checks.append({
                "name": "all 6 Stage 3.6 tables exist",
                "passed": len(missing) == 0,
                "detail": f"{len(existing_names)}/6 tables"
                + (f" (missing: {', '.join(missing)})" if missing else ""),
            })

            # ── Check 10: narrative_weight DESC index ─────────────────
            idx = await conn.fetchval(
                "SELECT COUNT(*) FROM pg_indexes "
                "WHERE tablename = 'narrative_events' "
                "AND indexdef LIKE '%narrative_weight%'")
            checks.append({
                "name": "narrative_events.narrative_weight index exists",
                "passed": idx > 0,
                "detail": f"{idx} matching index(es)",
            })

        await close_pool()

    _run(_run_validate())

    # ── Print results ───────────────────────────────────────────────
    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)

    click.echo(f"\n── Stage 3.6 Validation (world {world_id}) ──")
    click.echo(f"{'#':<4} {'Status':<8} {'Check':<55} {'Detail'}")
    click.echo("─" * 110)
    for i, c in enumerate(checks, 1):
        status = "PASS" if c["passed"] else "FAIL"
        marker = "+" if c["passed"] else "-"
        click.echo(f"{i:<4} {marker} {status:<5} {c['name']:<55} {c['detail']}")
    click.echo("─" * 110)
    click.echo(f"Result: {passed}/{total} checks passed")

    if passed < total:
        click.echo(
            "\nNote: Run 'chronicler narrative generate --target all' to "
            "populate LLM-generated content."
        )
        raise SystemExit(1)
    else:
        click.echo("\nStage 3.6: Narrative Data Layer — ALL CHECKS PASSED")


@cli.command("fortress-state")
@click.option("--world-id", default=1, type=int, help="World ID")
@click.option("--limit", default=10, type=int, help="Number of snapshots to show")
def fortress_state(world_id, limit):
    """Show recent fortress state snapshots (population, wealth, threats)."""
    from chronicler.db.connection import get_pool, close_pool

    async def _run_fs():
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT tick, year, season, population, military_count, "
                "food_stocks, drink_stocks, wealth, happiness_distribution, threats "
                "FROM fortress_state_snapshots WHERE world_id = $1 "
                "ORDER BY tick DESC LIMIT $2",
                world_id, limit,
            )

        if not rows:
            click.echo("No fortress state snapshots. Run 'chronicler watch' first.")
            await close_pool()
            return

        click.echo(f"── Fortress State (world {world_id}, last {limit}) ──")
        click.echo(
            f"{'Tick':>10} {'Year':>5} {'Season':<8} {'Pop':>4} {'Mil':>4} "
            f"{'Food':>6} {'Drink':>6} {'Wealth':>10}"
        )
        click.echo("─" * 70)
        for r in rows:
            click.echo(
                f"{r['tick']:>10} {r['year']:>5} {(r['season'] or '?'):<8} "
                f"{r['population'] or 0:>4} {r['military_count'] or 0:>4} "
                f"{r['food_stocks'] or 0:>6} {r['drink_stocks'] or 0:>6} "
                f"{r['wealth'] or 0:>10,}"
            )

        # Trend summary
        if len(rows) >= 2:
            newest, oldest = rows[0], rows[-1]
            pop_delta = (newest["population"] or 0) - (oldest["population"] or 0)
            wealth_delta = (newest["wealth"] or 0) - (oldest["wealth"] or 0)
            sign = "+" if pop_delta >= 0 else ""
            wsign = "+" if wealth_delta >= 0 else ""
            click.echo(
                f"\nTrend: pop {sign}{pop_delta}, wealth {wsign}{wealth_delta:,}"
            )

        await close_pool()

    _run(_run_fs())


@cli.command("threats")
@click.option("--world-id", default=1, type=int, help="World ID")
@click.option("--limit", default=20, type=int, help="Number of entries to show")
def threats(world_id, limit):
    """Show threat tracking history (hostile counts over time)."""
    from chronicler.db.connection import get_pool, close_pool

    async def _run_threats():
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT tick, hostile_count, undead_count, invader_count, "
                "megabeast_count FROM threat_tracking "
                "WHERE world_id = $1 ORDER BY tick DESC LIMIT $2",
                world_id, limit,
            )

        if not rows:
            click.echo("No threat tracking data. Run 'chronicler watch' first.")
            await close_pool()
            return

        click.echo(f"── Threat Tracking (world {world_id}, last {limit}) ──")
        click.echo(
            f"{'Tick':>10} {'Hostile':>8} {'Undead':>8} {'Invader':>8} {'Mega':>8}"
        )
        click.echo("─" * 50)
        for r in rows:
            click.echo(
                f"{r['tick']:>10} {r['hostile_count']:>8} "
                f"{r['undead_count']:>8} {r['invader_count']:>8} "
                f"{r['megabeast_count']:>8}"
            )

        peak = max(r["hostile_count"] for r in rows)
        click.echo(f"\nPeak hostile count: {peak}")

        await close_pool()

    _run(_run_threats())


@cli.command("deaths")
@click.option("--world-id", default=1, type=int, help="World ID")
@click.option("--limit", default=20, type=int, help="Number of entries to show")
def deaths(world_id, limit):
    """Show death narratives with cause and killer details."""
    from chronicler.db.connection import get_pool, close_pool

    async def _run_deaths():
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT dn.unit_id, dn.hf_id, dn.year, dn.cause, "
                "dn.killer_race, dn.weapon, dn.location, "
                "dn.combat_report_ids, dn.witness_unit_ids, "
                "fd.name AS victim_name "
                "FROM death_narratives dn "
                "LEFT JOIN fortress_denizens fd "
                "  ON fd.world_id = dn.world_id AND fd.unit_id = dn.unit_id "
                "WHERE dn.world_id = $1 "
                "ORDER BY dn.tick DESC LIMIT $2",
                world_id, limit,
            )

        if not rows:
            click.echo("No death narratives. Deaths are recorded during 'chronicler watch'.")
            await close_pool()
            return

        click.echo(f"── Death Narratives (world {world_id}, last {limit}) ──")
        for r in rows:
            name = r["victim_name"] or f"unit#{r['unit_id']}"
            hf = f" (HF {r['hf_id']})" if r["hf_id"] else ""
            click.echo(f"\n  {name}{hf} — Y{r['year']}")
            click.echo(f"    Cause: {r['cause']}")
            if r["killer_race"]:
                click.echo(f"    Killer: {r['killer_race']}")
            if r["weapon"]:
                click.echo(f"    Weapon: {r['weapon']}")
            if r["location"]:
                click.echo(f"    Location: {r['location']}")
            reports = r["combat_report_ids"]
            if reports and reports != []:
                click.echo(f"    Combat reports: {len(reports)} linked")
            witnesses = r["witness_unit_ids"]
            if witnesses and witnesses != []:
                click.echo(f"    Witnesses: {len(witnesses)}")

        await close_pool()

    _run(_run_deaths())


# ── Narrative Generation ─────────────────────────────────────────────────────

@cli.group("narrative")
def narrative_group():
    """Narrative data layer — LLM generation, scoring, context assembly."""


@narrative_group.command("generate")
@click.option("--world-id", default=1, type=int, help="World ID")
@click.option("--target", type=click.Choice(
    ["all", "arcs", "summaries", "profiles", "clusters"]),
    default="all", help="What to generate")
@click.option("--limit", default=100, type=int, help="Max items per generator")
@click.option("--force", is_flag=True, help="Re-generate existing content")
def narrative_generate(world_id, target, limit, force):
    """Generate LLM-powered narrative content (arc titles, summaries, profiles)."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.storyteller.narrative_generation import (
        generate_arc_titles,
        generate_year_summaries,
        generate_character_profiles,
        generate_cluster_summaries,
    )

    async def _run_generate():
        pool = await get_pool()
        async with pool.acquire() as conn:
            results = {}
            targets = [target] if target != "all" else [
                "arcs", "summaries", "profiles", "clusters"]

            for t in targets:
                click.echo(f"Generating {t}...")
                if t == "arcs":
                    results[t] = await generate_arc_titles(conn, world_id)
                elif t == "summaries":
                    results[t] = await generate_year_summaries(
                        conn, world_id, force=force)
                elif t == "profiles":
                    results[t] = await generate_character_profiles(
                        conn, world_id, limit=limit)
                elif t == "clusters":
                    results[t] = await generate_cluster_summaries(
                        conn, world_id)

        click.echo("\n── Narrative Generation Complete ──")
        for name, count in results.items():
            click.echo(f"  {name:20s} {count:>6,d} generated")
        await close_pool()

    _run(_run_generate())


@narrative_group.command("context")
@click.option("--world-id", default=1, type=int, help="World ID")
@click.option("--query-type", type=click.Choice(
    ["fortress_saga", "character_focus", "year_chronicle",
     "event_detail", "world_overview"]),
    default="world_overview", help="Context query type")
@click.option("--target-id", type=int, default=None, help="HF ID or event ID")
@click.option("--year", type=int, default=None, help="Year for year_chronicle")
@click.option("--budget", default=32000, type=int, help="Token budget")
def narrative_context(world_id, query_type, target_id, year, budget):
    """Assemble narrative context for the storyteller LLM."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.storyteller.narrative_context import assemble_context

    async def _run_context():
        pool = await get_pool()
        async with pool.acquire() as conn:
            ctx = await assemble_context(
                conn, world_id, query_type,
                target_id=target_id, year=year, token_budget=budget)

        click.echo(f"── Narrative Context ({query_type}) ──")
        click.echo(f"Blocks: {len(ctx.blocks)}, ~{ctx.total_tokens:,} tokens "
                   f"(budget: {ctx.budget:,}, truncated: {ctx.truncated})")
        click.echo(f"Categories: {', '.join({b.category for b in ctx.blocks})}")
        click.echo("\n" + ctx.text[:3000])
        if len(ctx.text) > 3000:
            click.echo(f"\n... ({len(ctx.text):,} chars total)")
        await close_pool()

    _run(_run_context())


@narrative_group.command("status")
@click.option("--world-id", default=1, type=int, help="World ID")
def narrative_status(world_id):
    """Show narrative data layer statistics."""
    from chronicler.db.connection import get_pool, close_pool

    async def _run_status():
        pool = await get_pool()
        async with pool.acquire() as conn:
            tables = {
                "narrative_events": "SELECT COUNT(*) FROM narrative_events WHERE world_id = $1",
                "event_causal_links": "SELECT COUNT(*) FROM event_causal_links WHERE world_id = $1",
                "narrative_arcs": "SELECT COUNT(*) FROM narrative_arcs WHERE world_id = $1",
                "  titled arcs": "SELECT COUNT(*) FROM narrative_arcs WHERE world_id = $1 AND title IS NOT NULL AND title != ''",
                "event_summaries": "SELECT COUNT(*) FROM event_summaries WHERE world_id = $1",
                "character_narratives": "SELECT COUNT(*) FROM character_narratives WHERE world_id = $1",
                "event_clusters": "SELECT COUNT(*) FROM event_clusters WHERE world_id = $1",
                "  summarized": "SELECT COUNT(*) FROM event_clusters WHERE world_id = $1 AND summary IS NOT NULL AND summary != ''",
            }

            click.echo(f"── Narrative Data Layer (world {world_id}) ──")
            for name, sql in tables.items():
                count = await conn.fetchval(sql, world_id)
                click.echo(f"  {name:30s} {count:>8,d}")

            # Work remaining
            click.echo("\n── Remaining Work ──")
            untitled = await conn.fetchval(
                "SELECT COUNT(*) FROM narrative_arcs WHERE world_id = $1 AND (title IS NULL OR title = '')",
                world_id)
            no_profile = await conn.fetchval(
                "SELECT COUNT(*) FROM historical_figures hf WHERE hf.world_id = $1 "
                "AND hf.prominence_score > 0.3 AND NOT EXISTS ("
                "SELECT 1 FROM character_narratives cn WHERE cn.world_id = $1 AND cn.hf_id = hf.id)",
                world_id)
            unsummarized = await conn.fetchval(
                "SELECT COUNT(*) FROM event_clusters WHERE world_id = $1 AND (summary IS NULL OR summary = '')",
                world_id)
            click.echo(f"  Untitled arcs:             {untitled:>8,d}")
            click.echo(f"  HFs needing profiles:      {no_profile:>8,d}")
            click.echo(f"  Unsummarized clusters:     {unsummarized:>8,d}")

        await close_pool()

    _run(_run_status())


# ── Embedding pipelines ─────────────────────────────────────────────────────

@cli.group("embed")
def embed_group():
    """Embedding pipelines — batch and live entity embedding for semantic search."""


@embed_group.command("run")
@click.option("--world-id", default=1, type=int, help="World ID")
@click.option("--entity-types", default="all",
              help="Comma-separated types or 'all' (art_form,hf,event,site,entity,artifact,written_content)")
@click.option("--force", is_flag=True, help="Re-embed even if content hash unchanged")
@click.option("--batch-size", default=64, type=int, help="Rows per embedding batch")
@click.option("--page-size", default=5000, type=int, help="DB fetch page size")
@click.option("--dry-run", is_flag=True, help="Show counts without embedding")
def embed_run(world_id, entity_types, force, batch_size, page_size, dry_run):
    """Run batch embedding pipeline for legends entities."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.embedding.extractors import BATCH_ENTITY_TYPES
    from chronicler.embedding.pipeline import embed_entities, build_vector_index

    # Parse entity types
    if entity_types == "all":
        types_to_run = list(BATCH_ENTITY_TYPES.keys())
    else:
        types_to_run = [t.strip() for t in entity_types.split(",")]
        for t in types_to_run:
            if t not in BATCH_ENTITY_TYPES:
                click.echo(f"Unknown entity type: {t}", err=True)
                click.echo(f"Available: {', '.join(BATCH_ENTITY_TYPES.keys())}", err=True)
                sys.exit(1)

    async def _run_embed():
        pool = await get_pool()
        grand_total = {"embedded": 0, "skipped": 0, "errors": 0}

        async with pool.acquire() as conn:
            for etype in types_to_run:
                spec = BATCH_ENTITY_TYPES[etype]
                total = await conn.fetchval(spec["count_sql"], world_id)
                click.echo(f"\n── {etype} ({spec['desc']}) — {total:,d} rows ──")

                if dry_run:
                    click.echo(f"  [dry-run] Would process {total:,d} rows")
                    continue

                t0 = time.time()
                type_stats = {"embedded": 0, "skipped": 0, "errors": 0}
                offset = 0

                while offset < total:
                    rows = await conn.fetch(
                        spec["sql"], world_id, page_size, offset)
                    if not rows:
                        break

                    # Process in sub-batches for embedding
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i + batch_size]
                        stats = await embed_entities(
                            conn, world_id, etype, batch,
                            spec["extract"], force=force)
                        for k in type_stats:
                            type_stats[k] += stats[k]

                    offset += page_size

                elapsed = time.time() - t0
                click.echo(
                    f"  Embedded: {type_stats['embedded']:,d}  "
                    f"Skipped: {type_stats['skipped']:,d}  "
                    f"Errors: {type_stats['errors']}  "
                    f"({elapsed:.1f}s)")
                for k in grand_total:
                    grand_total[k] += type_stats[k]

            # Build HNSW index after batch
            if not dry_run and grand_total["embedded"] > 0:
                click.echo("\n── Building vector index ──")
                built = await build_vector_index(conn)
                if built:
                    click.echo("  HNSW index built successfully.")
                else:
                    click.echo("  Skipped (not enough rows).")

        click.echo(f"\n── Total: embedded {grand_total['embedded']:,d}, "
                   f"skipped {grand_total['skipped']:,d}, "
                   f"errors {grand_total['errors']} ──")
        await close_pool()

    _run(_run_embed())


@embed_group.command("status")
@click.option("--world-id", default=1, type=int, help="World ID")
def embed_status(world_id):
    """Show embedding counts per entity type and index status."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.embedding.pipeline import get_embed_stats

    async def _run_status():
        pool = await get_pool()
        async with pool.acquire() as conn:
            stats = await get_embed_stats(conn, world_id)

        click.echo(f"── Embeddings (world {world_id}) ──")
        for row in stats["by_type"]:
            click.echo(
                f"  {row['entity_type']:20s} {row['count']:>8,d}  "
                f"({row['oldest'].strftime('%Y-%m-%d')} — "
                f"{row['newest'].strftime('%Y-%m-%d')})")
        click.echo(f"  {'TOTAL':20s} {stats['total']:>8,d}")
        click.echo(f"\n  Vector index (HNSW): "
                   f"{'YES' if stats['has_vector_index'] else 'NO'}")
        await close_pool()

    _run(_run_status())


# ── Stage 3.5: Fortress State Capture ──────────────────────────────────────

@cli.group("state")
def state_group():
    """Fortress state capture — snapshots, threats, arcs, reports, deaths."""


@state_group.command("status")
@click.option("--world-id", default=1, type=int, help="World ID")
def state_status(world_id):
    """Show Stage 3.5 table counts and latest data."""
    from chronicler.db.connection import get_pool, close_pool

    async def _go():
        pool = await get_pool()
        async with pool.acquire() as conn:
            tables = [
                ('fortress_state_snapshots', 'tick'),
                ('game_reports', 'game_tick'),
                ('threat_tracking', 'tick'),
                ('character_arcs', 'tick'),
                ('environmental_state', 'tick'),
                ('death_narratives', 'tick'),
                ('session_markers', 'tick'),
            ]
            click.echo(f"── State Capture (world {world_id}) ──")
            for table, tick_col in tables:
                count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {table} WHERE world_id = $1",
                    world_id)
                latest = await conn.fetchval(
                    f"SELECT MAX({tick_col}) FROM {table} WHERE world_id = $1",
                    world_id)
                label = f"  {table:30s}"
                if count > 0:
                    click.echo(f"{label} {count:>8,d} rows  (latest tick: {latest})")
                else:
                    click.echo(f"{label} {'---':>8s}")

            # Report classification coverage
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM game_reports WHERE world_id = $1",
                world_id)
            classified = await conn.fetchval(
                "SELECT COUNT(*) FROM game_reports WHERE world_id = $1 "
                "AND category IS NOT NULL", world_id)
            click.echo(f"\n  Report classification: {classified}/{total}"
                       f" ({100*classified//max(total,1)}%)")

            # Category breakdown
            cats = await conn.fetch(
                "SELECT category, COUNT(*) as cnt FROM game_reports "
                "WHERE world_id = $1 AND category IS NOT NULL "
                "GROUP BY category ORDER BY cnt DESC", world_id)
            for c in cats:
                click.echo(f"    {c['category']:15s} {c['cnt']:>6,d}")

        await close_pool()

    _run(_go())


@state_group.command("classify")
@click.option("--world-id", default=1, type=int, help="World ID")
def state_classify(world_id):
    """Classify unclassified game reports."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.dfhack.etl_state_capture import etl_classify_reports

    async def _go():
        pool = await get_pool()
        async with pool.acquire() as conn:
            count = await etl_classify_reports(conn, world_id)
            click.echo(f"Classified {count} reports for world {world_id}")
        await close_pool()

    _run(_go())
