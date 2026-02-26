"""World management — list, delete, and query world records."""

import logging

import asyncpg

log = logging.getLogger(__name__)

# FK-safe deletion order: child tables before parents, leaves first.
# Every table with a world_id column, ordered so FK constraints are never violated.
_DELETE_ORDER = [
    # Leaf tables (no other table references these)
    "event_entity_xref",
    "collection_events",
    "collection_subcollections",
    # Link tables referencing HF + sites + entities
    "hf_position_links",
    "hf_site_links",
    "hf_entity_links",
    "hf_links",
    # Tables referencing entities/sites
    "entity_positions",
    "structures",
    # Core data tables
    "history_event_collections",
    "event_relationships",
    "history_events",
    "written_contents",
    "artifacts",
    "identities",
    "historical_figures",
    "sites",
    "entities",
    # Geography / metadata
    "historical_eras",
    "art_forms",
    "rivers",
    "world_constructions",
    "landmasses",
    "mountain_peaks",
    "regions",
    "underground_regions",
    # Live data tables
    "fortress_denizens",
    "lua_probes",
    "world_map_snapshots",
    "game_reports",
    "sync_snapshots",
    "unit_events",
    "units",
    "worldgen_snapshots",
    "world_modpacks",
]


async def list_worlds(conn: asyncpg.Connection) -> list[dict]:
    """Return all worlds with summary record counts."""
    worlds = await conn.fetch(
        "SELECT id, name, alt_name, import_path, imported_at FROM worlds ORDER BY id"
    )
    result = []
    for w in worlds:
        wid = w["id"]
        counts = {}
        for table in ("historical_figures", "history_events", "sites", "entities", "artifacts"):
            counts[table] = await conn.fetchval(
                f"SELECT count(*) FROM {table} WHERE world_id = $1", wid
            )
        result.append({
            "id": wid,
            "name": w["name"],
            "alt_name": w["alt_name"],
            "import_path": w["import_path"],
            "imported_at": w["imported_at"],
            "counts": counts,
        })
    return result


async def delete_world(conn: asyncpg.Connection, world_id: int) -> dict[str, int]:
    """Delete a world and all child rows via CASCADE.

    All FK constraints have ON DELETE CASCADE, so deleting the worlds row
    automatically removes all child data. We count child rows beforehand
    to provide a useful summary.

    Returns dict of table → rows deleted. Raises ValueError if world doesn't exist.
    """
    existing = await conn.fetchval("SELECT name FROM worlds WHERE id = $1", world_id)
    if existing is None:
        raise ValueError(f"World {world_id} does not exist")

    # Snapshot counts before delete (for reporting)
    deleted = {}
    for table in _DELETE_ORDER:
        count = await conn.fetchval(
            f"SELECT count(*) FROM {table} WHERE world_id = $1", world_id
        )
        if count > 0:
            deleted[table] = count

    # Single DELETE cascades to all child tables
    await conn.execute("DELETE FROM worlds WHERE id = $1", world_id)
    deleted["worlds"] = 1

    log.info("Deleted world %d (%s): %d tables affected",
             world_id, existing, len(deleted))
    return deleted


async def delete_all_worlds(conn: asyncpg.Connection) -> tuple[int, dict[str, int]]:
    """Delete all worlds and child rows via CASCADE. Returns (world_count, table_counts)."""
    world_count = await conn.fetchval("SELECT count(*) FROM worlds")
    if world_count == 0:
        return 0, {}

    # Snapshot counts before delete (for reporting)
    deleted = {}
    for table in _DELETE_ORDER:
        count = await conn.fetchval(f"SELECT count(*) FROM {table}")
        if count > 0:
            deleted[table] = count

    # Single DELETE cascades to all child tables
    await conn.execute("DELETE FROM worlds")
    deleted["worlds"] = world_count

    # Reset world ID sequence
    await conn.execute("ALTER SEQUENCE worlds_id_seq RESTART WITH 1")

    log.info("Deleted all %d worlds: %d tables affected", world_count, len(deleted))
    return world_count, deleted
