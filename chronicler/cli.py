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
