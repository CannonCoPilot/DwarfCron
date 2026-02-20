"""Chronicler CLI — init, ingest, and validate Dwarf Fortress world data."""

import asyncio
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
