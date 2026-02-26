"""Generate annotated Entity Relationship Diagrams from the live CDM schema.

Supports Mermaid (.mmd) and Graphviz DOT (.dot) output formats.
Queries information_schema and pg_catalog, then produces an annotated ERD
with table groupings, column types, primary keys, and foreign key relationships.
"""

# Logical table groupings for annotations
TABLE_GROUPS = {
    "Geography & World": [
        "worlds", "landmasses", "mountain_peaks", "regions",
        "underground_regions", "sites", "structures",
        "world_constructions", "rivers",
    ],
    "Civilizations & Culture": [
        "entities", "entity_positions", "entity_populations",
        "art_forms", "written_contents", "historical_eras", "identities",
    ],
    "Historical Figures": [
        "historical_figures", "hf_links", "hf_entity_links",
        "hf_site_links", "hf_position_links",
    ],
    "Events & Collections": [
        "history_events", "history_event_collections",
        "collection_events", "collection_subcollections",
        "event_relationships", "event_entity_xref",
    ],
    "Artifacts": [
        "artifacts",
    ],
    "Live / Fortress Data": [
        "units", "unit_events", "fortress_denizens", "sync_snapshots",
        "game_reports", "world_map_snapshots", "lua_probes", "embeddings",
    ],
    "System": [
        "worldgen_snapshots", "world_modpacks", "storyteller_log",
    ],
}

# Short description for each table
TABLE_DESCRIPTIONS = {
    "worlds": "Top-level world record (one per DF export)",
    "landmasses": "Continents and major landmasses",
    "mountain_peaks": "Named peaks, volcanoes",
    "regions": "Surface biome regions",
    "underground_regions": "Cavern layers, magma sea, underworld",
    "sites": "Cities, fortresses, lairs, camps",
    "structures": "Buildings within sites (temples, tombs, libraries)",
    "world_constructions": "Roads, bridges, tunnels connecting sites",
    "rivers": "Named rivers with path coordinates",
    "entities": "Civilizations, religions, performance troupes",
    "entity_positions": "Noble/military/admin positions within entities",
    "entity_populations": "Race/count breakdown per civilization",
    "art_forms": "Dance, musical, and poetic art forms",
    "written_contents": "Books, poems, essays, letters",
    "historical_eras": "Named eras in world history",
    "identities": "False identities (vampires, spies, agents)",
    "historical_figures": "All historical figures (48K+ per world)",
    "hf_links": "HF-to-HF relationships (family, deity, companions)",
    "hf_entity_links": "HF membership in entities (with position/role)",
    "hf_site_links": "HF connections to sites (home, prison, lair)",
    "hf_position_links": "HF position assignments (noble titles, dates)",
    "history_events": "All historical events (436K+ per world)",
    "history_event_collections": "Wars, battles, duels, raids, etc.",
    "collection_events": "Junction: events within collections",
    "collection_subcollections": "Junction: collection hierarchy",
    "event_relationships": "Additional event metadata from legends_plus",
    "event_entity_xref": "Cross-reference: which entities appear in which events",
    "artifacts": "Named artifacts (weapons, books, crowns)",
    "units": "Live fortress units (from DFHack sync)",
    "unit_events": "Live unit events/changes",
    "fortress_denizens": "Denizen registry (arrival, status, narrative value)",
    "sync_snapshots": "DFHack sync metadata",
    "game_reports": "In-game combat/event reports",
    "world_map_snapshots": "Map tile data snapshots",
    "lua_probes": "DFHack Lua probe results",
    "embeddings": "Vector embeddings for semantic search",
    "worldgen_snapshots": "World generation parameter snapshots (Phase 5)",
    "world_modpacks": "Mod/raw configuration records (Phase 6)",
    "storyteller_log": "AI storyteller interaction log",
}


def _type_short(udt_name: str, char_max_len: int | None) -> str:
    """Convert PostgreSQL type name to a short readable form."""
    m = {
        "int4": "int", "int8": "bigint", "float8": "float",
        "bool": "bool", "timestamptz": "timestamptz", "jsonb": "jsonb",
        "text": "text", "varchar": "varchar", "_text": "text[]",
        "_int4": "int[]", "_float8": "float[]",
    }
    short = m.get(udt_name, udt_name)
    if udt_name == "varchar" and char_max_len:
        short = f"varchar({char_max_len})"
    return short


def _group_for_table(table_name: str) -> str:
    """Find the logical group for a table."""
    for group, tables in TABLE_GROUPS.items():
        if table_name in tables:
            return group
    return "Other"


async def _fetch_schema(conn):
    """Fetch all schema metadata needed for ERD generation."""
    tables = [r["table_name"] for r in await conn.fetch(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
        "ORDER BY table_name"
    )]

    columns = {}
    pk_sets = {}
    row_counts = {}

    for t in tables:
        columns[t] = await conn.fetch(
            "SELECT column_name, udt_name, character_maximum_length, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = $1 "
            "ORDER BY ordinal_position", t)

        pk_rows = await conn.fetch(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid "
            "AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = $1::regclass AND i.indisprimary", t)
        pk_sets[t] = {r["attname"] for r in pk_rows}

        row_counts[t] = await conn.fetchval(f"SELECT COUNT(*) FROM {t}")

    # Foreign keys — use pg_catalog to avoid composite FK Cartesian products
    # that information_schema produces when joining key_column_usage with
    # constraint_column_usage on multi-column FKs.
    fk_rows = await conn.fetch("""
        SELECT
            cl_from.relname AS from_table,
            att_from.attname AS from_col,
            cl_to.relname AS to_table,
            att_to.attname AS to_col,
            con.conname AS constraint_name
        FROM pg_constraint con
        JOIN pg_class cl_from ON cl_from.oid = con.conrelid
        JOIN pg_class cl_to ON cl_to.oid = con.confrelid
        JOIN pg_namespace ns ON ns.oid = cl_from.relnamespace
        CROSS JOIN LATERAL unnest(con.conkey, con.confkey)
            WITH ORDINALITY AS cols(from_attnum, to_attnum, ord)
        JOIN pg_attribute att_from
            ON att_from.attrelid = con.conrelid AND att_from.attnum = cols.from_attnum
        JOIN pg_attribute att_to
            ON att_to.attrelid = con.confrelid AND att_to.attnum = cols.to_attnum
        WHERE con.contype = 'f' AND ns.nspname = 'public'
        ORDER BY cl_from.relname, con.conname, cols.ord
    """)

    # For ERD edges: one edge per constraint (not per column pair).
    # Collect constraint -> (from_table, to_table, column pairs) for labels.
    constraint_map = {}
    for r in fk_rows:
        cname = r["constraint_name"]
        if cname not in constraint_map:
            constraint_map[cname] = {
                "from_table": r["from_table"],
                "to_table": r["to_table"],
                "pairs": [],
            }
        constraint_map[cname]["pairs"].append((r["from_col"], r["to_col"]))

    # Also build a flat list of (from_table, from_col, to_table, to_col) for
    # individual column-level FK marking.
    fk_col_set = set()
    for r in fk_rows:
        fk_col_set.add((r["from_table"], r["from_col"]))

    return tables, columns, pk_sets, row_counts, constraint_map, fk_col_set


async def generate_mermaid(conn) -> str:
    """Generate a Mermaid erDiagram from the live schema."""
    tables, columns, pk_sets, row_counts, constraint_map, fk_col_set = \
        await _fetch_schema(conn)

    lines = []
    lines.append("erDiagram")
    lines.append("")

    # Emit entities grouped with comments
    for group_name, group_order in TABLE_GROUPS.items():
        group_tables = [t for t in group_order if t in tables]
        if not group_tables:
            continue

        lines.append(f"    %% ── {group_name} {'─' * (50 - len(group_name))}")
        lines.append("")

        for t in group_tables:
            desc = TABLE_DESCRIPTIONS.get(t, "")
            count = row_counts.get(t, 0)
            lines.append(f"    %% {desc} ({count:,d} rows)")
            lines.append(f"    {t} {{")

            for col in columns[t]:
                col_name = col["column_name"]
                col_type = _type_short(col["udt_name"], col["character_maximum_length"])
                markers = []
                if col_name in pk_sets[t]:
                    markers.append("PK")
                if (t, col_name) in fk_col_set:
                    markers.append("FK")
                marker_str = f' "{",".join(markers)}"' if markers else ""
                lines.append(f"        {col_type} {col_name}{marker_str}")

            lines.append("    }")
            lines.append("")

    # Handle any tables not in predefined groups
    ungrouped = [t for t in tables if _group_for_table(t) == "Other"]
    if ungrouped:
        lines.append("    %% ── Other ──────────────────────────────────────────")
        lines.append("")
        for t in ungrouped:
            count = row_counts.get(t, 0)
            lines.append(f"    %% ({count:,d} rows)")
            lines.append(f"    {t} {{")
            for col in columns[t]:
                col_name = col["column_name"]
                col_type = _type_short(col["udt_name"], col["character_maximum_length"])
                marker = ' "PK"' if col_name in pk_sets[t] else ""
                lines.append(f"        {col_type} {col_name}{marker}")
            lines.append("    }")
            lines.append("")

    # Emit relationships — one edge per FK constraint (not per column)
    lines.append("    %% ── Relationships ────────────────────────────────────")
    lines.append("")

    for cname, info in sorted(constraint_map.items(),
                               key=lambda x: (x[1]["from_table"], x[0])):
        from_t = info["from_table"]
        to_t = info["to_table"]
        pairs = info["pairs"]
        # Label: show column mapping
        label = ", ".join(f"{fc}→{tc}" for fc, tc in pairs)
        # Cardinality: if all from-cols are PK columns, it's a junction table
        all_pk = all(fc in pk_sets.get(from_t, set()) for fc, _ in pairs)
        rel = "}o--||" if all_pk else "}o--o|"
        lines.append(f"    {to_t} {rel} {from_t} : \"{label}\"")

    lines.append("")
    return "\n".join(lines)


async def generate_dot(conn) -> str:
    """Generate a Graphviz DOT graph from the live schema."""
    tables, columns, pk_sets, row_counts, constraint_map, fk_col_set = \
        await _fetch_schema(conn)

    lines = []
    lines.append('digraph CDM {')
    lines.append('    rankdir=LR;')
    lines.append('    node [shape=none, fontname="Helvetica", fontsize=10];')
    lines.append('    edge [fontname="Helvetica", fontsize=8, color="#666666"];')
    lines.append('    graph [fontname="Helvetica", fontsize=12, '
                 'label="Chronicler CDM — Entity Relationship Diagram\\n'
                 f'{len(tables)} tables", labelloc=t];')
    lines.append('')

    # Color scheme per group
    group_colors = {
        "Geography & World": "#4CAF50",
        "Civilizations & Culture": "#2196F3",
        "Historical Figures": "#FF9800",
        "Events & Collections": "#F44336",
        "Artifacts": "#9C27B0",
        "Live / Fortress Data": "#607D8B",
        "System": "#9E9E9E",
    }

    # Emit subgraphs per group
    cluster_idx = 0
    for group_name, group_tables_list in TABLE_GROUPS.items():
        group_tables = [t for t in group_tables_list if t in tables]
        if not group_tables:
            continue

        color = group_colors.get(group_name, "#000000")
        lines.append(f'    subgraph cluster_{cluster_idx} {{')
        lines.append(f'        label="{group_name}";')
        lines.append(f'        color="{color}";')
        lines.append(f'        fontcolor="{color}";')
        lines.append('        style=dashed;')
        lines.append('')

        for t in group_tables:
            desc = TABLE_DESCRIPTIONS.get(t, "")
            count = row_counts.get(t, 0)
            # Build HTML-like label for the table
            header_bg = color
            label_parts = []
            label_parts.append(
                f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
            )
            label_parts.append(
                f'<TR><TD COLSPAN="3" BGCOLOR="{header_bg}">'
                f'<FONT COLOR="white"><B>{t}</B></FONT></TD></TR>'
            )
            label_parts.append(
                f'<TR><TD COLSPAN="3"><FONT POINT-SIZE="7">'
                f'{desc} ({count:,d} rows)</FONT></TD></TR>'
            )

            for col in columns[t]:
                col_name = col["column_name"]
                col_type = _type_short(col["udt_name"], col["character_maximum_length"])
                pk_mark = "PK " if col_name in pk_sets[t] else ""
                fk_mark = "FK " if (t, col_name) in fk_col_set else ""
                marks = pk_mark + fk_mark
                mark_td = f'<TD ALIGN="LEFT"><FONT POINT-SIZE="8">{marks}</FONT></TD>' if marks else '<TD></TD>'
                label_parts.append(
                    f'<TR>{mark_td}'
                    f'<TD ALIGN="LEFT">{col_name}</TD>'
                    f'<TD ALIGN="LEFT"><FONT COLOR="#888888">{col_type}</FONT></TD></TR>'
                )

            label_parts.append('</TABLE>>')
            label = "".join(label_parts)
            lines.append(f'        {t} [label={label}];')

        lines.append('    }')
        lines.append('')
        cluster_idx += 1

    # Ungrouped tables
    ungrouped = [t for t in tables if _group_for_table(t) == "Other"]
    if ungrouped:
        lines.append(f'    subgraph cluster_{cluster_idx} {{')
        lines.append('        label="Other";')
        lines.append('        color="#000000";')
        lines.append('        style=dashed;')
        for t in ungrouped:
            count = row_counts.get(t, 0)
            label_parts = [
                f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
                f'<TR><TD COLSPAN="3" BGCOLOR="#000000">'
                f'<FONT COLOR="white"><B>{t}</B></FONT></TD></TR>'
            ]
            for col in columns[t]:
                col_name = col["column_name"]
                col_type = _type_short(col["udt_name"], col["character_maximum_length"])
                label_parts.append(
                    f'<TR><TD></TD><TD ALIGN="LEFT">{col_name}</TD>'
                    f'<TD ALIGN="LEFT"><FONT COLOR="#888888">{col_type}</FONT></TD></TR>'
                )
            label_parts.append('</TABLE>>')
            lines.append(f'        {t} [label={"".join(label_parts)}];')
        lines.append('    }')
        lines.append('')

    # Emit edges for foreign keys — one per constraint
    lines.append('    // Foreign key relationships')
    for cname, info in sorted(constraint_map.items(),
                               key=lambda x: (x[1]["from_table"], x[0])):
        from_t = info["from_table"]
        to_t = info["to_table"]
        pairs = info["pairs"]
        label = ", ".join(f"{fc}→{tc}" for fc, tc in pairs)
        lines.append(
            f'    {from_t} -> {to_t} '
            f'[label="{label}", '
            f'arrowhead=crow, arrowtail=tee, dir=both];'
        )

    lines.append('}')
    return "\n".join(lines)
