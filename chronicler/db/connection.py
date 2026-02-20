"""Asyncpg connection pool with pgvector codec registration."""

import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

from chronicler.config import DB_DSN

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the module-level connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DB_DSN,
            min_size=2,
            max_size=10,
            init=_init_connection,
        )
    return _pool


async def _init_connection(conn: asyncpg.Connection):
    """Register pgvector type codec on each new connection."""
    await register_vector(conn)


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def init_db():
    """Create the chronicler database if it doesn't exist, then run schema."""
    import os

    # Connect to default 'jarvis' DB to create chronicler DB
    jarvis_dsn = DB_DSN.rsplit("/", 1)[0] + "/jarvis"
    conn = await asyncpg.connect(jarvis_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'chronicler'"
        )
        if not exists:
            await conn.execute("CREATE DATABASE chronicler OWNER jarvis")
    finally:
        await conn.close()

    # Run schema on a plain connection (no vector codec — extension not yet created)
    conn = await asyncpg.connect(DB_DSN)
    try:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path) as f:
            await conn.execute(f.read())
    finally:
        await conn.close()
