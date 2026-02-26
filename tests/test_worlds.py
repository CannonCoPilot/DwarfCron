"""Tests for world management — CLI commands, DB functions, and path resolution."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from chronicler.cli import cli, _resolve_legends_pair
from chronicler.db.worlds import _DELETE_ORDER, delete_world, delete_all_worlds, list_worlds


# ── Path Resolution ─────────────────────────────────────────────────────────


class TestResolveLegendsPair:
    """Unit tests for _resolve_legends_pair() path logic."""

    def test_file_passthrough(self, tmp_path):
        """A direct file path passes through unchanged."""
        legends = tmp_path / "region1-00250-01-01-legends.xml"
        legends.write_text("<df_world/>")
        result, plus = _resolve_legends_pair(str(legends), None)
        assert result == str(legends)

    def test_directory_auto_detect(self, tmp_path):
        """A directory auto-detects *-legends.xml and *-legends_plus.xml."""
        legends = tmp_path / "region1-00250-01-01-legends.xml"
        plus = tmp_path / "region1-00250-01-01-legends_plus.xml"
        legends.write_text("<df_world/>")
        plus.write_text("<df_world/>")
        result_l, result_p = _resolve_legends_pair(str(tmp_path), None)
        assert result_l == str(legends)
        assert result_p == str(plus)

    def test_directory_no_legends_exits(self, tmp_path):
        """A directory with no *-legends.xml causes sys.exit."""
        with pytest.raises(SystemExit):
            _resolve_legends_pair(str(tmp_path), None)

    def test_auto_detect_plus_from_legends_dir(self, tmp_path):
        """When only legends is given as file, plus is auto-detected from same dir."""
        legends = tmp_path / "save1-legends.xml"
        plus = tmp_path / "save1-legends_plus.xml"
        legends.write_text("<df_world/>")
        plus.write_text("<df_world/>")
        result_l, result_p = _resolve_legends_pair(str(legends), None)
        assert result_l == str(legends)
        assert result_p == str(plus)

    def test_explicit_plus_not_overridden(self, tmp_path):
        """When both paths are explicit files, auto-detect doesn't override."""
        legends = tmp_path / "a-legends.xml"
        plus_explicit = tmp_path / "custom-plus.xml"
        plus_auto = tmp_path / "a-legends_plus.xml"
        for f in (legends, plus_explicit, plus_auto):
            f.write_text("<df_world/>")
        result_l, result_p = _resolve_legends_pair(str(legends), str(plus_explicit))
        assert result_p == str(plus_explicit)

    def test_none_falls_back_to_legends_dir(self, tmp_path):
        """When both paths are None, falls back to LEGENDS_DIR."""
        legends = tmp_path / "region1-legends.xml"
        legends.write_text("<df_world/>")
        with patch("chronicler.cli.LEGENDS_DIR", str(tmp_path)):
            result_l, result_p = _resolve_legends_pair(None, None)
        assert result_l == str(legends)

    def test_none_no_legends_dir_files_exits(self, tmp_path):
        """When both paths are None and LEGENDS_DIR is empty, exits."""
        with patch("chronicler.cli.LEGENDS_DIR", str(tmp_path)):
            with pytest.raises(SystemExit):
                _resolve_legends_pair(None, None)

    def test_directory_picks_first_sorted(self, tmp_path):
        """Multiple legends files: picks first alphabetically."""
        f1 = tmp_path / "aaa-legends.xml"
        f2 = tmp_path / "zzz-legends.xml"
        f1.write_text("<df_world/>")
        f2.write_text("<df_world/>")
        result_l, _ = _resolve_legends_pair(str(tmp_path), None)
        assert result_l == str(f1)


# ── DB Function Unit Tests ──────────────────────────────────────────────────


class _AsyncContextManager:
    """Minimal async context manager for mocking conn.transaction() / pool.acquire()."""
    def __init__(self, value=None):
        self._value = value

    async def __aenter__(self):
        return self._value if self._value is not None else self

    async def __aexit__(self, *args):
        pass


def _make_mock_conn():
    """Build an AsyncMock connection that mimics asyncpg.Connection."""
    conn = AsyncMock()
    # asyncpg's transaction() is a sync method returning an async context manager
    conn.transaction = MagicMock(return_value=_AsyncContextManager())
    return conn


def _make_mock_pool(mock_conn):
    """Build a mock pool where pool.acquire() returns mock_conn as async ctx mgr."""
    pool = AsyncMock()
    pool.acquire = MagicMock(return_value=_AsyncContextManager(mock_conn))
    return pool


class TestListWorlds:
    """Unit tests for list_worlds()."""

    def test_empty_db(self):
        conn = _make_mock_conn()
        conn.fetch.return_value = []
        result = asyncio.run(list_worlds(conn))
        assert result == []

    def test_returns_counts(self):
        conn = _make_mock_conn()
        conn.fetch.return_value = [
            {"id": 1, "name": "Tar Thran", "alt_name": "The Land of Dawning",
             "import_path": "/data/legends", "imported_at": None},
        ]
        conn.fetchval.return_value = 42
        result = asyncio.run(list_worlds(conn))
        assert len(result) == 1
        assert result[0]["name"] == "Tar Thran"
        assert result[0]["counts"]["historical_figures"] == 42
        # 5 count queries per world
        assert conn.fetchval.call_count == 5


class TestDeleteWorld:
    """Unit tests for delete_world()."""

    def test_nonexistent_world_raises(self):
        conn = _make_mock_conn()
        conn.fetchval.return_value = None
        with pytest.raises(ValueError, match="does not exist"):
            asyncio.run(delete_world(conn, 999))

    def test_cascade_delete(self):
        conn = _make_mock_conn()
        # First fetchval = world name, then count queries return 10 each
        conn.fetchval.side_effect = ["Test World"] + [10] * len(_DELETE_ORDER)
        result = asyncio.run(delete_world(conn, 1))
        # Should have called execute once (CASCADE delete of worlds row)
        assert conn.execute.call_count == 1
        assert "worlds" in result

    def test_only_counts_nonzero_tables(self):
        conn = _make_mock_conn()
        # First fetchval = world name, then 3 nonzero + rest zero
        counts = [10, 5, 3] + [0] * (len(_DELETE_ORDER) - 3)
        conn.fetchval.side_effect = ["Test World"] + counts
        result = asyncio.run(delete_world(conn, 1))
        # 3 nonzero child tables + worlds = 4
        assert len(result) == 4


class TestDeleteAllWorlds:
    """Unit tests for delete_all_worlds()."""

    def test_empty_db(self):
        conn = _make_mock_conn()
        conn.fetchval.return_value = 0
        count, deleted = asyncio.run(delete_all_worlds(conn))
        assert count == 0
        assert deleted == {}

    def test_deletes_all_and_resets_sequence(self):
        conn = _make_mock_conn()
        # First fetchval = world_count=2, then count queries for each table
        conn.fetchval.side_effect = [2] + [100] * len(_DELETE_ORDER)
        count, deleted = asyncio.run(delete_all_worlds(conn))
        assert count == 2
        assert deleted["worlds"] == 2
        # Should have called execute 3x: DELETE FROM worlds + ALTER SEQUENCE
        calls = [str(c) for c in conn.execute.call_args_list]
        assert any("DELETE FROM worlds" in c for c in calls)
        assert any("RESTART WITH 1" in c for c in calls)


# ── CLI Integration Tests ───────────────────────────────────────────────────


class TestWorldsListCLI:
    """CLI tests for `chronicler worlds list`."""

    @patch("chronicler.db.connection.close_pool", new_callable=AsyncMock)
    @patch("chronicler.db.connection.get_pool")
    def test_empty_worlds(self, mock_get_pool, mock_close_pool):
        mock_conn = _make_mock_conn()
        mock_conn.fetch.return_value = []
        mock_get_pool.return_value = _make_mock_pool(mock_conn)

        runner = CliRunner()
        result = runner.invoke(cli, ["worlds", "list"])
        assert result.exit_code == 0
        assert "No worlds" in result.output


class TestWorldsDeleteCLI:
    """CLI tests for `chronicler worlds delete`."""

    def test_no_flags_error(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["worlds", "delete"])
        assert result.exit_code == 1
        assert "--world-id" in result.output or "Specify" in result.output

    def test_mutual_exclusion(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["worlds", "delete", "--world-id", "1", "--all"])
        assert result.exit_code == 1
        assert "mutually exclusive" in result.output

    @patch("chronicler.db.connection.close_pool", new_callable=AsyncMock)
    @patch("chronicler.db.connection.get_pool")
    def test_delete_world_with_yes(self, mock_get_pool, mock_close_pool):
        mock_conn = _make_mock_conn()
        # First fetchval = world name, then count queries for each table
        mock_conn.fetchval.side_effect = ["Test World"] + [5] * len(_DELETE_ORDER)
        mock_get_pool.return_value = _make_mock_pool(mock_conn)

        runner = CliRunner()
        result = runner.invoke(cli, ["worlds", "delete", "--world-id", "1", "--yes"])
        assert result.exit_code == 0
        assert "Deleted world 1" in result.output

    @patch("chronicler.db.connection.close_pool", new_callable=AsyncMock)
    @patch("chronicler.db.connection.get_pool")
    def test_delete_nonexistent_world(self, mock_get_pool, mock_close_pool):
        mock_conn = _make_mock_conn()
        mock_conn.fetchval.return_value = None  # world doesn't exist
        mock_get_pool.return_value = _make_mock_pool(mock_conn)

        runner = CliRunner()
        result = runner.invoke(cli, ["worlds", "delete", "--world-id", "999", "--yes"])
        assert result.exit_code == 1


class TestIngestPathCLI:
    """CLI tests for ingest --legends accepting directories."""

    @patch("chronicler.db.connection.close_pool", new_callable=AsyncMock)
    @patch("chronicler.db.connection.get_pool")
    @patch("chronicler.ingest.xml_parser.import_legends")
    def test_ingest_with_directory(self, mock_import, mock_get_pool, mock_close_pool, tmp_path):
        legends = tmp_path / "test-legends.xml"
        plus = tmp_path / "test-legends_plus.xml"
        legends.write_text("<df_world/>")
        plus.write_text("<df_world/>")

        mock_conn = _make_mock_conn()
        mock_import.return_value = {"regions": 5}
        mock_get_pool.return_value = _make_mock_pool(mock_conn)

        runner = CliRunner()
        result = runner.invoke(cli, ["ingest", "--legends", str(tmp_path)])
        assert result.exit_code == 0
        assert "Legends:" in result.output


# ── DELETE_ORDER Integrity ──────────────────────────────────────────────────


class TestDeleteOrder:
    """Verify _DELETE_ORDER covers all necessary tables."""

    def test_no_duplicates(self):
        assert len(_DELETE_ORDER) == len(set(_DELETE_ORDER))

    def test_minimum_table_count(self):
        """Should cover at least 30 tables."""
        assert len(_DELETE_ORDER) >= 30

    def test_leaves_first(self):
        """Leaf tables (xref, collection_events) must come before their parents."""
        xref_idx = _DELETE_ORDER.index("event_entity_xref")
        events_idx = _DELETE_ORDER.index("history_events")
        assert xref_idx < events_idx

        coll_events_idx = _DELETE_ORDER.index("collection_events")
        coll_idx = _DELETE_ORDER.index("history_event_collections")
        assert coll_events_idx < coll_idx

    def test_hf_links_before_hf(self):
        """All HF link tables must come before historical_figures."""
        hf_idx = _DELETE_ORDER.index("historical_figures")
        for link_table in ("hf_links", "hf_entity_links", "hf_site_links", "hf_position_links"):
            assert _DELETE_ORDER.index(link_table) < hf_idx, \
                f"{link_table} must be deleted before historical_figures"

    def test_structures_before_sites(self):
        """structures references sites, must be deleted first."""
        assert _DELETE_ORDER.index("structures") < _DELETE_ORDER.index("sites")

    def test_entity_positions_before_entities(self):
        assert _DELETE_ORDER.index("entity_positions") < _DELETE_ORDER.index("entities")


# ── CASCADE Integration Test ────────────────────────────────────────────────

try:
    import asyncpg
    from chronicler.config import DB_DSN
    _loop = asyncio.new_event_loop()
    _test_conn = _loop.run_until_complete(asyncpg.connect(dsn=DB_DSN))
    _loop.run_until_complete(_test_conn.close())
    HAS_DB = True
except Exception:
    HAS_DB = False
    _loop = None


@pytest.mark.skipif(not HAS_DB, reason="chronicler DB not available")
class TestCascadeConstraints:
    """Verify all FK constraints have ON DELETE CASCADE in live DB."""

    @pytest.fixture(scope="class")
    def conn(self):
        c = _loop.run_until_complete(asyncpg.connect(dsn=DB_DSN))
        yield c
        _loop.run_until_complete(c.close())

    def test_all_fks_have_cascade(self, conn):
        rows = _loop.run_until_complete(conn.fetch("""
            SELECT tc.table_name, tc.constraint_name, rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name
        """))
        non_cascade = [
            (r["table_name"], r["constraint_name"], r["delete_rule"])
            for r in rows if r["delete_rule"] != "CASCADE"
        ]
        assert non_cascade == [], \
            f"These FK constraints are missing ON DELETE CASCADE: {non_cascade}"

    def test_cascade_count_matches_schema(self, conn):
        count = _loop.run_until_complete(conn.fetchval("""
            SELECT count(*) FROM information_schema.table_constraints tc
            JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            WHERE rc.delete_rule = 'CASCADE'
        """))
        assert count == 42, f"Expected 42 CASCADE constraints, got {count}"
