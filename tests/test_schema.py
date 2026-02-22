"""Tests for Chronicler CDM schema — composite PK enforcement and FK constraints.

These are integration tests that query the live chronicler database.
Skipped automatically if PostgreSQL is unavailable.
Uses asyncpg with a persistent event loop to avoid loop lifecycle issues.
"""

import asyncio
import pytest

from chronicler.config import DB_DSN

# Create a persistent event loop for all asyncpg operations in this module
_loop = asyncio.new_event_loop()

def _run(coro):
    """Run a coroutine on the module's persistent event loop."""
    return _loop.run_until_complete(coro)

try:
    import asyncpg
    _test_conn = _run(asyncpg.connect(dsn=DB_DSN))
    _run(_test_conn.close())
    HAS_DB = True
except Exception:
    HAS_DB = False

pytestmark = pytest.mark.skipif(not HAS_DB, reason="chronicler DB not available")


@pytest.fixture(scope="module")
def conn():
    """Shared read-only asyncpg connection for schema introspection."""
    c = _run(asyncpg.connect(dsn=DB_DSN))
    yield c
    _run(c.close())


def _get_pk_columns(conn, table_name: str) -> list[str]:
    """Get primary key column names for a table."""
    rows = _run(conn.fetch("""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.table_name = $1
            AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
    """, table_name))
    return [row['column_name'] for row in rows]


def _get_fk_constraints(conn, table_name: str) -> list[dict]:
    """Get foreign key constraints for a table."""
    rows = _run(conn.fetch("""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.table_name = $1
            AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.constraint_name, kcu.ordinal_position
    """, table_name))
    return [{
        'constraint': r['constraint_name'],
        'column': r['column_name'],
        'foreign_table': r['foreign_table_name'],
        'foreign_column': r['foreign_column_name'],
    } for r in rows]


def _get_unique_constraints(conn, table_name: str) -> list[list[str]]:
    """Get UNIQUE constraint column groups for a table."""
    rows = _run(conn.fetch("""
        SELECT tc.constraint_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = $1
            AND tc.constraint_type = 'UNIQUE'
        ORDER BY tc.constraint_name, kcu.ordinal_position
    """, table_name))
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        groups[r['constraint_name']].append(r['column_name'])
    return list(groups.values())


# ── Composite Primary Keys ───────────────────────────────────────────────────

class TestCompositePKs:
    """Verify that legends tables use (world_id, id) composite primary keys."""

    COMPOSITE_PK_TABLES = [
        "regions", "underground_regions", "sites", "entities",
        "historical_figures", "history_events", "history_event_collections",
        "artifacts", "written_contents", "landmasses", "mountain_peaks",
        "world_constructions", "identities",
    ]

    @pytest.mark.parametrize("table", COMPOSITE_PK_TABLES)
    def test_composite_pk(self, conn, table):
        pk = _get_pk_columns(conn, table)
        assert pk == ["world_id", "id"] or pk == ["id", "world_id"], \
            f"{table} PK should be (world_id, id), got {pk}"

    def test_structures_triple_pk(self, conn):
        """structures has PK (world_id, site_id, id)."""
        pk = _get_pk_columns(conn, "structures")
        assert set(pk) == {"world_id", "site_id", "id"}

    def test_historical_eras_pk(self, conn):
        """historical_eras has PK (world_id, name)."""
        pk = _get_pk_columns(conn, "historical_eras")
        assert set(pk) == {"world_id", "name"}

    def test_collection_events_triple_pk(self, conn):
        pk = _get_pk_columns(conn, "collection_events")
        assert set(pk) == {"world_id", "collection_id", "event_id"}

    def test_collection_subcollections_triple_pk(self, conn):
        pk = _get_pk_columns(conn, "collection_subcollections")
        assert set(pk) == {"world_id", "parent_id", "child_id"}


# ── Foreign Key Constraints ──────────────────────────────────────────────────

class TestForeignKeys:
    """Verify FK constraints reference correct parent tables."""

    WORLD_FK_TABLES = [
        "regions", "underground_regions", "sites", "entities",
        "historical_figures", "history_events", "history_event_collections",
        "artifacts", "written_contents", "historical_eras",
        "unit_events", "sync_snapshots", "game_reports", "lua_probes",
        "world_map_snapshots", "landmasses", "mountain_peaks",
        "world_constructions", "identities", "event_relationships",
    ]

    @pytest.mark.parametrize("table", WORLD_FK_TABLES)
    def test_world_id_fk_to_worlds(self, conn, table):
        """Every table with world_id should FK to worlds."""
        fks = _get_fk_constraints(conn, table)
        world_fks = [fk for fk in fks if fk['column'] == 'world_id' and fk['foreign_table'] == 'worlds']
        assert len(world_fks) >= 1, \
            f"{table}.world_id should FK to worlds"

    def test_structures_fk_to_sites(self, conn):
        fks = _get_fk_constraints(conn, "structures")
        site_fks = [fk for fk in fks if fk['foreign_table'] == 'sites']
        assert len(site_fks) > 0, "structures should FK to sites"

    def test_hf_links_fk_to_hf(self, conn):
        fks = _get_fk_constraints(conn, "hf_links")
        hf_fks = [fk for fk in fks if fk['foreign_table'] == 'historical_figures']
        assert len(hf_fks) >= 2, "hf_links needs FKs for both hf_id and target_hf_id"

    def test_hf_entity_links_fk_to_entities(self, conn):
        fks = _get_fk_constraints(conn, "hf_entity_links")
        ent_fks = [fk for fk in fks if fk['foreign_table'] == 'entities']
        assert len(ent_fks) >= 1

    def test_hf_site_links_fk_to_sites(self, conn):
        fks = _get_fk_constraints(conn, "hf_site_links")
        site_fks = [fk for fk in fks if fk['foreign_table'] == 'sites']
        assert len(site_fks) >= 1

    def test_collection_events_fks(self, conn):
        fks = _get_fk_constraints(conn, "collection_events")
        coll_fks = [fk for fk in fks if fk['foreign_table'] == 'history_event_collections']
        event_fks = [fk for fk in fks if fk['foreign_table'] == 'history_events']
        assert len(coll_fks) >= 1, "collection_events should FK to history_event_collections"
        assert len(event_fks) >= 1, "collection_events should FK to history_events"


# ── UNIQUE Constraints on Link Tables ────────────────────────────────────────

class TestUniqueConstraints:
    """Verify UNIQUE constraints prevent duplicate link rows."""

    def test_hf_links_unique(self, conn):
        uniques = _get_unique_constraints(conn, "hf_links")
        found = any(
            set(cols) == {"world_id", "hf_id", "target_hf_id", "link_type"}
            for cols in uniques
        )
        assert found, f"hf_links needs UNIQUE(world_id, hf_id, target_hf_id, link_type), got {uniques}"

    def test_hf_entity_links_unique(self, conn):
        uniques = _get_unique_constraints(conn, "hf_entity_links")
        found = any(
            set(cols) == {"world_id", "hf_id", "entity_id", "link_type"}
            for cols in uniques
        )
        assert found, f"hf_entity_links needs UNIQUE(world_id, hf_id, entity_id, link_type), got {uniques}"

    def test_hf_site_links_unique(self, conn):
        uniques = _get_unique_constraints(conn, "hf_site_links")
        found = any(
            set(cols) == {"world_id", "hf_id", "site_id", "link_type"}
            for cols in uniques
        )
        assert found, f"hf_site_links needs UNIQUE(world_id, hf_id, site_id, link_type), got {uniques}"

    def test_game_reports_unique(self, conn):
        uniques = _get_unique_constraints(conn, "game_reports")
        found = any(
            set(cols) == {"world_id", "report_id"}
            for cols in uniques
        )
        assert found, f"game_reports needs UNIQUE(world_id, report_id), got {uniques}"
