"""Explorer API routes — schema browser, data browser, entity graph."""

import json
import re
from datetime import datetime, date
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

VALID_TABLE_RE = re.compile(r'^[a-z_][a-z0-9_]*$')

# Table groupings for the sidebar
TABLE_GROUPS = {
    "Legends": [
        "worlds", "historical_figures", "entities", "history_events",
        "history_event_collections", "artifacts", "written_contents",
        "historical_eras", "identities",
    ],
    "Relationships": [
        "hf_links", "hf_entity_links", "hf_site_links",
        "hf_position_links", "entity_positions",
        "collection_events", "collection_subcollections", "event_relationships",
    ],
    "Geography": [
        "regions", "underground_regions", "sites", "structures",
        "world_constructions", "landmasses", "mountain_peaks",
    ],
    "Live Data": [
        "units", "unit_events", "sync_snapshots", "game_reports",
        "world_map_snapshots", "lua_probes",
    ],
    "System": [
        "embeddings", "storyteller_log",
    ],
}

# Reverse lookup: table_name -> group
_TABLE_TO_GROUP = {}
for group, tables in TABLE_GROUPS.items():
    for t in tables:
        _TABLE_TO_GROUP[t] = group


@router.get("/explorer/tables")
async def list_tables(request: Request):
    """List all tables with approximate row counts, grouped by category."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Use pg_stat for fast approximate counts
        rows = await conn.fetch("""
            SELECT
                t.table_name,
                COALESCE(s.n_live_tup, 0) AS row_count
            FROM information_schema.tables t
            LEFT JOIN pg_stat_user_tables s
                ON s.relname = t.table_name AND s.schemaname = 'public'
            WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name
        """)

    tables = []
    for r in rows:
        tables.append({
            "name": r["table_name"],
            "row_count": r["row_count"],
            "group": _TABLE_TO_GROUP.get(r["table_name"], "Other"),
        })
    return tables


@router.get("/explorer/tables/{name}")
async def table_detail(name: str, request: Request):
    """Column metadata, PKs, FKs, and indexes for a single table."""
    if not VALID_TABLE_RE.match(name):
        raise HTTPException(400, "Invalid table name")

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Verify table exists
        exists = await conn.fetchval(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=$1",
            name,
        )
        if not exists:
            raise HTTPException(404, "Table not found")

        # Exact row count for detail view
        row_count = await conn.fetchval(f'SELECT count(*) FROM "{name}"')

        # Columns
        columns = await conn.fetch("""
            SELECT column_name, data_type, udt_name, is_nullable,
                   column_default, character_maximum_length,
                   ordinal_position
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position
        """, name)

        # Primary key columns
        pk_cols = await conn.fetch("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid
                AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = $1::regclass AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
        """, name)

        # Foreign keys (outgoing)
        fks = await conn.fetch("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.table_name = $1
                AND tc.table_schema = 'public'
                AND tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.constraint_name, kcu.ordinal_position
        """, name)

        # Incoming FKs (tables that reference this one)
        incoming_fks = await conn.fetch("""
            SELECT
                kcu.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.column_name AS target_column,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE ccu.table_name = $1
                AND tc.table_schema = 'public'
                AND tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.constraint_name
        """, name)

        # Indexes
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = $1 AND schemaname = 'public'
        """, name)

    # Group FKs by constraint name for composite FKs
    fk_groups = {}
    for f in fks:
        cn = f["constraint_name"]
        if cn not in fk_groups:
            fk_groups[cn] = {
                "constraint": cn,
                "columns": [],
                "foreign_table": f["foreign_table"],
                "foreign_columns": [],
            }
        fk_groups[cn]["columns"].append(f["column_name"])
        fk_groups[cn]["foreign_columns"].append(f["foreign_column"])

    # Group incoming FKs by constraint
    incoming_groups = {}
    for f in incoming_fks:
        cn = f["constraint_name"]
        if cn not in incoming_groups:
            incoming_groups[cn] = {
                "constraint": cn,
                "source_table": f["source_table"],
                "source_columns": [],
                "target_columns": [],
            }
        incoming_groups[cn]["source_columns"].append(f["source_column"])
        incoming_groups[cn]["target_columns"].append(f["target_column"])

    return {
        "name": name,
        "row_count": row_count,
        "group": _TABLE_TO_GROUP.get(name, "Other"),
        "columns": [dict(c) for c in columns],
        "primary_key": [r["attname"] for r in pk_cols],
        "foreign_keys": list(fk_groups.values()),
        "incoming_foreign_keys": list(incoming_groups.values()),
        "indexes": [{"name": i["indexname"], "definition": i["indexdef"]} for i in indexes],
    }


# ─── Data Browser ───────────────────────────────────────────────────────────

def _serialize_value(v):
    """Convert a single value to JSON-serializable form."""
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, bytes):
        return v.hex()[:200]  # truncate large blobs
    if isinstance(v, (dict, list)):
        return v  # already JSON-compatible (asyncpg decodes JSONB)
    return v


def _serialize_row(row: dict) -> dict:
    """Convert asyncpg record values to JSON-serializable types."""
    return {k: _serialize_value(v) for k, v in row.items()}


@router.get("/explorer/tables/{name}/data")
async def table_data(
    name: str,
    request: Request,
    page: int = 1,
    limit: int = 25,
    sort: str = "",
    order: str = "asc",
    filter: str = "",
):
    """Paginated table data with optional sorting and text filtering."""
    if not VALID_TABLE_RE.match(name):
        raise HTTPException(400, "Invalid table name")
    limit = min(max(limit, 1), 100)
    if order not in ("asc", "desc"):
        order = "asc"
    if page < 1:
        page = 1

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        # Verify table exists
        exists = await conn.fetchval(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name=$1",
            name,
        )
        if not exists:
            raise HTTPException(404, "Table not found")

        # Validate sort column
        valid_sort = ""
        if sort:
            col_exists = await conn.fetchval(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=$1 AND column_name=$2",
                name, sort,
            )
            if col_exists:
                valid_sort = sort

        # Get text columns for filtering
        filter_clause = ""
        filter_params = []
        if filter:
            text_cols = await conn.fetch(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=$1
                   AND data_type IN ('text', 'character varying')""",
                name,
            )
            if text_cols:
                or_parts = []
                for c in text_cols:
                    col = c["column_name"]
                    if VALID_TABLE_RE.match(col):
                        or_parts.append(f'"{col}"::text ILIKE $1')
                if or_parts:
                    filter_clause = "WHERE " + " OR ".join(or_parts)
                    filter_params = [f"%{filter}%"]

        # Total count
        count_sql = f'SELECT count(*) FROM "{name}" {filter_clause}'
        total = await conn.fetchval(count_sql, *filter_params)

        # Data query
        order_clause = f'ORDER BY "{valid_sort}" {order}' if valid_sort else ""
        offset = (page - 1) * limit

        if filter_params:
            data_sql = f'SELECT * FROM "{name}" {filter_clause} {order_clause} LIMIT $2 OFFSET $3'
            rows = await conn.fetch(data_sql, filter_params[0], limit, offset)
        else:
            data_sql = f'SELECT * FROM "{name}" {order_clause} LIMIT $1 OFFSET $2'
            rows = await conn.fetch(data_sql, limit, offset)

        # Column metadata for type-aware rendering
        columns = await conn.fetch(
            """SELECT column_name, data_type, udt_name
               FROM information_schema.columns
               WHERE table_schema='public' AND table_name=$1
               ORDER BY ordinal_position""",
            name,
        )

        # FK metadata for clickable links
        fks = await conn.fetch("""
            SELECT kcu.column_name, ccu.table_name AS foreign_table,
                   ccu.column_name AS foreign_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.table_name = $1 AND tc.table_schema = 'public'
                AND tc.constraint_type = 'FOREIGN KEY'
        """, name)

    fk_map = {f["column_name"]: {"table": f["foreign_table"], "column": f["foreign_column"]}
              for f in fks}

    return {
        "table": name,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": max(1, (total + limit - 1) // limit),
        "columns": [dict(c) for c in columns],
        "foreign_keys": fk_map,
        "rows": [_serialize_row(dict(r)) for r in rows],
    }


class QueryRequest(BaseModel):
    sql: str
    limit: int = 100


_DANGEROUS_KW = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|COPY)\b',
    re.IGNORECASE,
)


@router.post("/explorer/query")
async def run_query(body: QueryRequest, request: Request):
    """Execute a read-only SQL query with enforced LIMIT."""
    sql = body.sql.strip().rstrip(';')

    # Must start with SELECT or WITH
    normalized = sql.lstrip()
    if not (normalized.upper().startswith('SELECT') or normalized.upper().startswith('WITH')):
        raise HTTPException(400, "Only SELECT/WITH queries are allowed")

    # Reject dangerous keywords
    if _DANGEROUS_KW.search(sql):
        raise HTTPException(400, "Query contains forbidden keyword")

    max_limit = min(body.limit, 500)

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            try:
                # Wrap to enforce limit
                wrapped = f"SELECT * FROM ({sql}) _q LIMIT {max_limit}"
                rows = await conn.fetch(wrapped)
            except Exception as e:
                raise HTTPException(400, f"Query error: {str(e)}")

    if not rows:
        return {"columns": [], "rows": [], "count": 0, "truncated": False}

    columns = list(rows[0].keys())
    return {
        "columns": columns,
        "rows": [_serialize_row(dict(r)) for r in rows],
        "count": len(rows),
        "truncated": len(rows) >= max_limit,
    }


# ─── Entity Graph ────────────────────────────────────────────────────────────

# Node styling constants
NODE_COLORS = {
    "hf": "#78716c",       # stone — default HF
    "deity": "#f6b93b",    # gold
    "vampire": "#ef4444",  # red
    "necromancer": "#a855f7",  # purple
    "werebeast": "#f97316",    # orange
    "ghost": "#94a3b8",    # slate
    "entity_civilization": "#3b82f6",  # blue
    "entity_religion": "#a855f7",      # purple
    "entity_other": "#6b7280",         # gray
    "site": "#22c55e",     # green
}

EDGE_COLORS = {
    "child": "#4ade80", "mother": "#4ade80", "father": "#4ade80",
    "spouse": "#f472b6", "former spouse": "#f472b6", "deceased spouse": "#f472b6", "lover": "#f472b6",
    "master": "#60a5fa", "apprentice": "#60a5fa", "former master": "#60a5fa", "former apprentice": "#60a5fa",
    "imprisoner": "#ef4444", "prisoner": "#ef4444",
    "enemy": "#ef4444",
    "member": "#3b82f6", "former member": "#6b7280",
    "criminal": "#f97316", "former prisoner": "#9ca3af",
    "slave": "#ef4444", "former slave": "#9ca3af",
    "home structure": "#a3e635", "occupation": "#a3e635",
    "seat of power": "#f6b93b", "lair": "#94a3b8", "hangout": "#d6d3d1",
}

# Max nodes per hop to prevent graph explosion
MAX_NODES_PER_HOP = 50
# Deity links are worship connections — overwhelm the graph (146K edges)
FILTERED_LINK_TYPES = {"deity"}


def _hf_node(row) -> dict:
    """Build a vis.js node dict for a historical figure."""
    nid = f"hf-{row['id']}"
    label = row["name"] or f"HF #{row['id']}"
    # Determine special type
    if row.get("is_deity"):
        color, group = NODE_COLORS["deity"], "deity"
    elif row.get("is_vampire"):
        color, group = NODE_COLORS["vampire"], "vampire"
    elif row.get("is_necromancer"):
        color, group = NODE_COLORS["necromancer"], "necromancer"
    elif row.get("is_werebeast"):
        color, group = NODE_COLORS["werebeast"], "werebeast"
    elif row.get("is_ghost"):
        color, group = NODE_COLORS["ghost"], "ghost"
    else:
        color, group = NODE_COLORS["hf"], "hf"

    alive = row.get("death_year") is None or row["death_year"] == -1
    death_str = "" if alive else f", Died: {row.get('death_year', '?')}"
    title = (f"{label} ({row.get('race', '?')}, {row.get('caste', '?')})"
             f"\nBorn: {row.get('birth_year', '?')}{death_str}"
             f"\nKills: {row.get('kill_count', 0)}")
    return {
        "id": nid, "label": label, "shape": "dot", "size": 12,
        "color": {"background": color, "border": color, "highlight": {"background": color, "border": "#f6b93b"}},
        "group": group,
        "title": title,
        "meta": {
            "type": "hf", "hf_id": row["id"], "world_id": row["world_id"],
            "name": label, "race": row.get("race"), "caste": row.get("caste"),
            "birth_year": row.get("birth_year"), "death_year": row.get("death_year"),
            "kill_count": row.get("kill_count", 0), "alive": alive,
        },
    }


def _entity_node(row) -> dict:
    """Build a vis.js node dict for an entity (civ/religion/group)."""
    nid = f"ent-{row['id']}"
    etype = (row.get("type") or "").lower()
    if "civilization" in etype:
        color = NODE_COLORS["entity_civilization"]
    elif "religion" in etype:
        color = NODE_COLORS["entity_religion"]
    else:
        color = NODE_COLORS["entity_other"]
    label = row.get("name") or f"Entity #{row['id']}"
    return {
        "id": nid, "label": label, "shape": "diamond", "size": 16,
        "color": {"background": color, "border": color, "highlight": {"background": color, "border": "#f6b93b"}},
        "group": "entity",
        "title": f"{label}\nType: {row.get('type', '?')}\nRace: {row.get('race', '?')}",
        "meta": {
            "type": "entity", "entity_id": row["id"], "world_id": row["world_id"],
            "name": label, "entity_type": row.get("type"), "race": row.get("race"),
        },
    }


def _site_node(row) -> dict:
    """Build a vis.js node dict for a site."""
    nid = f"site-{row['id']}"
    label = row.get("name") or f"Site #{row['id']}"
    color = NODE_COLORS["site"]
    return {
        "id": nid, "label": label, "shape": "square", "size": 14,
        "color": {"background": color, "border": color, "highlight": {"background": color, "border": "#f6b93b"}},
        "group": "site",
        "title": f"{label}\nType: {row.get('type', '?')}\nCoords: ({row.get('coord_x', '?')}, {row.get('coord_y', '?')})",
        "meta": {
            "type": "site", "site_id": row["id"], "world_id": row["world_id"],
            "name": label, "site_type": row.get("type"),
        },
    }


def _edge(from_id: str, to_id: str, label: str, dashed: bool = False) -> dict:
    color = EDGE_COLORS.get(label, "#57534e")
    return {
        "from": from_id, "to": to_id, "label": label,
        "color": {"color": color, "highlight": "#f6b93b"},
        "dashes": dashed,
        "font": {"color": "#78716c", "size": 9, "strokeWidth": 0},
        "arrows": "",
    }


@router.get("/explorer/graph/hf/{world_id}/{hf_id}")
async def graph_hf(world_id: int, hf_id: int, request: Request, depth: int = 1):
    """Ego network centered on a historical figure."""
    depth = max(1, min(depth, 3))
    pool = request.app.state.pool

    nodes = {}  # id -> node dict
    edges = []
    frontier = {hf_id}
    visited_hf = set()

    async with pool.acquire() as conn:
        for hop in range(depth):
            if not frontier:
                break
            frontier_list = list(frontier)
            visited_hf.update(frontier)

            # Fetch HF details for frontier
            hf_rows = await conn.fetch(
                "SELECT * FROM historical_figures WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, frontier_list,
            )
            for r in hf_rows:
                node = _hf_node(r)
                nodes[node["id"]] = node

            # HF-to-HF edges (bidirectional)
            hf_links = await conn.fetch("""
                SELECT hf_id, target_hf_id, link_type FROM hf_links
                WHERE world_id = $1
                  AND (hf_id = ANY($2::int[]) OR target_hf_id = ANY($2::int[]))
                  AND link_type != ALL($3::text[])
            """, world_id, frontier_list, list(FILTERED_LINK_TYPES))

            next_frontier = set()
            for link in hf_links:
                src = f"hf-{link['hf_id']}"
                tgt = f"hf-{link['target_hf_id']}"
                edges.append(_edge(src, tgt, link["link_type"]))
                # Add the other end to next frontier
                other = link["target_hf_id"] if link["hf_id"] in frontier else link["hf_id"]
                if other not in visited_hf:
                    next_frontier.add(other)

            # HF-to-Entity edges (only from frontier HFs)
            ent_links = await conn.fetch("""
                SELECT hf_id, entity_id, link_type, position_name FROM hf_entity_links
                WHERE world_id = $1 AND hf_id = ANY($2::int[])
            """, world_id, frontier_list)

            entity_ids = set()
            for link in ent_links:
                entity_ids.add(link["entity_id"])
                label = link["link_type"]
                if link["position_name"]:
                    label += f" ({link['position_name']})"
                edges.append(_edge(f"hf-{link['hf_id']}", f"ent-{link['entity_id']}", label, dashed=True))

            # Fetch entity details
            if entity_ids:
                ent_rows = await conn.fetch(
                    "SELECT * FROM entities WHERE world_id = $1 AND id = ANY($2::int[])",
                    world_id, list(entity_ids),
                )
                for r in ent_rows:
                    node = _entity_node(r)
                    nodes[node["id"]] = node

            # HF-to-Site edges (only from frontier HFs)
            site_links = await conn.fetch("""
                SELECT hf_id, site_id, link_type FROM hf_site_links
                WHERE world_id = $1 AND hf_id = ANY($2::int[])
            """, world_id, frontier_list)

            site_ids = set()
            for link in site_links:
                site_ids.add(link["site_id"])
                edges.append(_edge(f"hf-{link['hf_id']}", f"site-{link['site_id']}", link["link_type"], dashed=True))

            # Fetch site details
            if site_ids:
                site_rows = await conn.fetch(
                    "SELECT * FROM sites WHERE world_id = $1 AND id = ANY($2::int[])",
                    world_id, list(site_ids),
                )
                for r in site_rows:
                    node = _site_node(r)
                    nodes[node["id"]] = node

            # Cap next frontier to prevent explosion
            frontier = set(list(next_frontier)[:MAX_NODES_PER_HOP])

    # Deduplicate edges
    seen_edges = set()
    unique_edges = []
    for e in edges:
        key = (e["from"], e["to"], e["label"])
        reverse = (e["to"], e["from"], e["label"])
        if key not in seen_edges and reverse not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    return {
        "nodes": list(nodes.values()),
        "edges": unique_edges,
        "center": f"hf-{hf_id}",
        "node_count": len(nodes),
        "edge_count": len(unique_edges),
    }


@router.get("/explorer/graph/entity/{world_id}/{entity_id}")
async def graph_entity(world_id: int, entity_id: int, request: Request, depth: int = 1):
    """Ego network centered on an entity — shows member HFs."""
    depth = max(1, min(depth, 2))  # Cap entity depth at 2 (entities have many members)
    pool = request.app.state.pool

    nodes = {}
    edges = []

    async with pool.acquire() as conn:
        # Fetch the center entity
        ent_row = await conn.fetchrow(
            "SELECT * FROM entities WHERE world_id = $1 AND id = $2",
            world_id, entity_id,
        )
        if not ent_row:
            raise HTTPException(404, "Entity not found")
        center = _entity_node(ent_row)
        nodes[center["id"]] = center

        # Get member HFs (capped)
        member_links = await conn.fetch("""
            SELECT hf_id, link_type, position_name FROM hf_entity_links
            WHERE world_id = $1 AND entity_id = $2
            ORDER BY
                CASE WHEN position_name IS NOT NULL THEN 0 ELSE 1 END,
                link_type
            LIMIT $3
        """, world_id, entity_id, MAX_NODES_PER_HOP)

        hf_ids = [l["hf_id"] for l in member_links]
        if hf_ids:
            hf_rows = await conn.fetch(
                "SELECT * FROM historical_figures WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, hf_ids,
            )
            for r in hf_rows:
                node = _hf_node(r)
                nodes[node["id"]] = node

            for link in member_links:
                label = link["link_type"]
                if link["position_name"]:
                    label += f" ({link['position_name']})"
                edges.append(_edge(f"hf-{link['hf_id']}", f"ent-{entity_id}", label, dashed=True))

            # If depth 2, get HF-to-HF links among these HFs
            if depth >= 2:
                hf_links = await conn.fetch("""
                    SELECT hf_id, target_hf_id, link_type FROM hf_links
                    WHERE world_id = $1
                      AND hf_id = ANY($2::int[])
                      AND target_hf_id = ANY($2::int[])
                      AND link_type != ALL($3::text[])
                """, world_id, hf_ids, list(FILTERED_LINK_TYPES))
                for link in hf_links:
                    edges.append(_edge(f"hf-{link['hf_id']}", f"hf-{link['target_hf_id']}", link["link_type"]))

        # Total member count for display
        total_members = await conn.fetchval(
            "SELECT count(*) FROM hf_entity_links WHERE world_id = $1 AND entity_id = $2",
            world_id, entity_id,
        )

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "center": f"ent-{entity_id}",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "total_members": total_members,
        "capped": total_members > MAX_NODES_PER_HOP,
    }


@router.get("/explorer/graph/site/{world_id}/{site_id}")
async def graph_site(world_id: int, site_id: int, request: Request):
    """Ego network centered on a site — shows linked HFs."""
    pool = request.app.state.pool

    nodes = {}
    edges = []

    async with pool.acquire() as conn:
        site_row = await conn.fetchrow(
            "SELECT * FROM sites WHERE world_id = $1 AND id = $2",
            world_id, site_id,
        )
        if not site_row:
            raise HTTPException(404, "Site not found")
        center = _site_node(site_row)
        nodes[center["id"]] = center

        # Get linked HFs
        site_links = await conn.fetch("""
            SELECT hf_id, link_type FROM hf_site_links
            WHERE world_id = $1 AND site_id = $2
            LIMIT $3
        """, world_id, site_id, MAX_NODES_PER_HOP)

        hf_ids = [l["hf_id"] for l in site_links]
        if hf_ids:
            hf_rows = await conn.fetch(
                "SELECT * FROM historical_figures WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, hf_ids,
            )
            for r in hf_rows:
                node = _hf_node(r)
                nodes[node["id"]] = node

            for link in site_links:
                edges.append(_edge(f"hf-{link['hf_id']}", f"site-{site_id}", link["link_type"], dashed=True))

        # Owner entity
        if site_row.get("owner_entity_id"):
            ent_row = await conn.fetchrow(
                "SELECT * FROM entities WHERE world_id = $1 AND id = $2",
                world_id, site_row["owner_entity_id"],
            )
            if ent_row:
                node = _entity_node(ent_row)
                nodes[node["id"]] = node
                edges.append(_edge(f"ent-{ent_row['id']}", f"site-{site_id}", "owns", dashed=True))

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "center": f"site-{site_id}",
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


@router.get("/explorer/graph/search")
async def graph_search(q: str, request: Request, world_id: int = 0):
    """Typeahead search across HFs, entities, and sites."""
    if len(q) < 2:
        return []

    pool = request.app.state.pool
    pattern = f"%{q}%"
    results = []

    async with pool.acquire() as conn:
        world_filter = "AND world_id = $2" if world_id else ""
        params_hf = [pattern, world_id] if world_id else [pattern]
        params_ent = [pattern, world_id] if world_id else [pattern]
        params_site = [pattern, world_id] if world_id else [pattern]

        # HFs
        hf_rows = await conn.fetch(f"""
            SELECT id, world_id, name, race, is_deity, is_vampire, is_necromancer
            FROM historical_figures
            WHERE name ILIKE $1 {world_filter}
            ORDER BY kill_count DESC NULLS LAST
            LIMIT 10
        """, *params_hf)
        for r in hf_rows:
            tags = []
            if r["is_deity"]: tags.append("deity")
            if r["is_vampire"]: tags.append("vampire")
            if r["is_necromancer"]: tags.append("necromancer")
            tag = f" [{', '.join(tags)}]" if tags else ""
            results.append({
                "type": "hf", "id": r["id"], "world_id": r["world_id"],
                "label": f"{r['name']} ({r['race'] or '?'}){tag}",
                "url": f"/api/explorer/graph/hf/{r['world_id']}/{r['id']}",
            })

        # Entities
        ent_rows = await conn.fetch(f"""
            SELECT id, world_id, name, type
            FROM entities
            WHERE name ILIKE $1 {world_filter}
            ORDER BY name
            LIMIT 10
        """, *params_ent)
        for r in ent_rows:
            results.append({
                "type": "entity", "id": r["id"], "world_id": r["world_id"],
                "label": f"{r['name']} ({r['type'] or 'entity'})",
                "url": f"/api/explorer/graph/entity/{r['world_id']}/{r['id']}",
            })

        # Sites
        site_rows = await conn.fetch(f"""
            SELECT id, world_id, name, type
            FROM sites
            WHERE name ILIKE $1 {world_filter}
            ORDER BY name
            LIMIT 10
        """, *params_site)
        for r in site_rows:
            results.append({
                "type": "site", "id": r["id"], "world_id": r["world_id"],
                "label": f"{r['name']} ({r['type'] or 'site'})",
                "url": f"/api/explorer/graph/site/{r['world_id']}/{r['id']}",
            })

    return results
