"""Chronicler CLI — init, ingest, and validate Dwarf Fortress world data."""

import asyncio
import json
import logging
import sys
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


@cli.command("ingest")
@click.option(
    "--legends", "legends_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to legends.xml (default: auto-detect in data/legends/)",
)
@click.option(
    "--legends-plus", "legends_plus_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to legends_plus.xml (default: auto-detect in data/legends/)",
)
def ingest(legends_path, legends_plus_path):
    """Parse and import Dwarf Fortress legends XML into the database."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.ingest.xml_parser import import_legends

    # Auto-detect files if not specified
    if legends_path is None:
        candidates = sorted(Path(LEGENDS_DIR).glob("*-legends.xml"))
        if not candidates:
            click.echo("No legends.xml found in data/legends/. Use --legends.", err=True)
            sys.exit(1)
        legends_path = str(candidates[0])

    if legends_plus_path is None:
        candidates = sorted(Path(LEGENDS_DIR).glob("*-legends_plus.xml"))
        if candidates:
            legends_plus_path = str(candidates[0])

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
    """Recompute importance scores for all entities in a world."""
    from chronicler.db.connection import get_pool, close_pool
    from chronicler.scoring import compute_importance_scores

    async def _run_rescore():
        pool = await get_pool()
        async with pool.acquire() as conn:
            counts = await compute_importance_scores(conn, world_id)

        click.echo("── Importance Scores Recomputed ──")
        for entity_type, n in sorted(counts.items()):
            click.echo(f"  {entity_type:30s} {n:>8,d} updated")
        await close_pool()

    _run(_run_rescore())


@cli.command("validate")
def validate():
    """Query all CDM tables and print row counts."""
    from chronicler.db.connection import get_pool, close_pool

    tables = [
        "worlds", "landmasses", "mountain_peaks", "regions",
        "underground_regions", "sites", "structures", "world_constructions",
        "entities", "historical_figures", "hf_links", "hf_entity_links",
        "hf_site_links", "identities", "history_events",
        "history_event_collections", "collection_events",
        "collection_subcollections", "event_relationships",
        "artifacts", "units", "embeddings",
        "unit_events", "sync_snapshots",
        "game_reports", "world_map_snapshots", "lua_probes",
        "fortress_denizens",
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
