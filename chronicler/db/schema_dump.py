"""Dump the full CDM database schema to human-readable text.

Queries information_schema and pg_catalog to produce a complete picture of
every table, column, constraint, index, and foreign key in the public schema.
"""


async def dump_schema(conn) -> str:
    """Produce a full human-readable schema dump from the live database."""
    lines = []

    # ── Gather all tables ────────────────────────────────────────────────
    tables = await conn.fetch("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)

    lines.append("=" * 78)
    lines.append(f"  CHRONICLER CDM SCHEMA — {len(tables)} tables")
    lines.append("=" * 78)

    for tbl in tables:
        table_name = tbl["table_name"]
        lines.append("")
        lines.append("─" * 78)

        # Row count
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
        lines.append(f"TABLE: {table_name}  ({count:,d} rows)")
        lines.append("─" * 78)

        # ── Columns ──────────────────────────────────────────────────────
        columns = await conn.fetch("""
            SELECT
                c.column_name,
                c.data_type,
                c.udt_name,
                c.character_maximum_length,
                c.is_nullable,
                c.column_default
            FROM information_schema.columns c
            WHERE c.table_schema = 'public' AND c.table_name = $1
            ORDER BY c.ordinal_position
        """, table_name)

        # Get primary key columns
        pk_cols = await conn.fetch("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid
                AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = $1::regclass AND i.indisprimary
            ORDER BY array_position(i.indkey, a.attnum)
        """, table_name)
        pk_set = {r["attname"] for r in pk_cols}

        lines.append("")
        lines.append(f"  {'Column':<35s} {'Type':<25s} {'Null':>5s}  {'PK':>3s}  Default")
        lines.append(f"  {'─' * 35} {'─' * 25} {'─' * 5}  {'─' * 3}  {'─' * 30}")

        for col in columns:
            col_name = col["column_name"]
            # Build a readable type string
            dtype = col["udt_name"]
            if dtype == "varchar" and col["character_maximum_length"]:
                dtype = f"varchar({col['character_maximum_length']})"
            elif dtype == "int4":
                dtype = "integer"
            elif dtype == "int8":
                dtype = "bigint"
            elif dtype == "float8":
                dtype = "double precision"
            elif dtype == "bool":
                dtype = "boolean"
            elif dtype == "timestamptz":
                dtype = "timestamptz"
            elif dtype == "_text":
                dtype = "text[]"
            elif dtype == "_int4":
                dtype = "integer[]"
            elif dtype == "_float8":
                dtype = "double precision[]"

            nullable = "YES" if col["is_nullable"] == "YES" else "NO"
            pk_flag = "PK" if col_name in pk_set else ""
            default = col["column_default"] or ""
            if len(default) > 30:
                default = default[:27] + "..."

            lines.append(
                f"  {col_name:<35s} {dtype:<25s} {nullable:>5s}  {pk_flag:>3s}  {default}"
            )

        # ── Foreign keys (outgoing) ─────────────────────────────────────
        fks = await conn.fetch("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS ref_table,
                ccu.column_name AS ref_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = $1
                AND tc.table_schema = 'public'
            ORDER BY tc.constraint_name, kcu.ordinal_position
        """, table_name)

        if fks:
            lines.append("")
            lines.append("  Foreign Keys:")
            seen = set()
            for fk in fks:
                key = (fk["constraint_name"], fk["column_name"])
                if key not in seen:
                    seen.add(key)
                    lines.append(
                        f"    {fk['column_name']} -> {fk['ref_table']}.{fk['ref_column']}"
                    )

        # ── Foreign keys (incoming) ─────────────────────────────────────
        incoming_fks = await conn.fetch("""
            SELECT
                tc.table_name AS from_table,
                kcu.column_name AS from_column,
                ccu.column_name AS to_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND ccu.table_name = $1
                AND tc.table_schema = 'public'
            ORDER BY tc.table_name
        """, table_name)

        if incoming_fks:
            lines.append("")
            lines.append("  Referenced By:")
            seen = set()
            for fk in incoming_fks:
                key = (fk["from_table"], fk["from_column"])
                if key not in seen:
                    seen.add(key)
                    lines.append(
                        f"    {fk['from_table']}.{fk['from_column']} -> {fk['to_column']}"
                    )

        # ── Indexes ─────────────────────────────────────────────────────
        indexes = await conn.fetch("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = $1 AND schemaname = 'public'
            ORDER BY indexname
        """, table_name)

        if indexes:
            lines.append("")
            lines.append("  Indexes:")
            for idx in indexes:
                # Extract just the key part from the full CREATE INDEX statement
                defn = idx["indexdef"]
                lines.append(f"    {idx['indexname']}")
                lines.append(f"      {defn}")

    # ── Summary ──────────────────────────────────────────────────────────
    lines.append("")
    lines.append("=" * 78)
    lines.append(f"  TOTAL: {len(tables)} tables")
    lines.append("=" * 78)

    return "\n".join(lines)
