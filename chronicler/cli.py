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
@click.option("--timeout", default=30.0, type=float, help="Max seconds to wait")
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
