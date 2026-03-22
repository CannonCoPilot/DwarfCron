"""Stage 3.4.2-3.4.5: Embedding pipeline — chunking, MLX client, DB operations.

Combines:
  - Text chunking with content_hash deduplication
  - MLX embedding server client (localhost:8000)
  - Batch embedding pipeline (extract → chunk → hash-check → embed → upsert)
  - Live embedding pipeline (incremental changes from watcher cycles)
"""

import hashlib
import logging
import time

import httpx
import numpy as np

from chronicler.config import MLX_EMBED_URL, EMBED_DIM

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Chunking
# ═══════════════════════════════════════════════════════════════════════

def chunk_text(text: str, max_chars: int = 2048, overlap_chars: int = 256):
    """Split text into chunks with overlap.

    Returns list of dicts: [{chunk_index, chunk_text, content_hash}, ...]
    Most entities produce a single chunk. Only art_forms (avg 1528 chars)
    may produce 2 chunks.
    """
    if not text:
        return []

    text = text.strip()
    if len(text) <= max_chars:
        return [{
            "chunk_index": 0,
            "chunk_text": text,
            "content_hash": _hash(text),
        }]

    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end]
        chunks.append({
            "chunk_index": idx,
            "chunk_text": chunk,
            "content_hash": _hash(chunk),
        })
        idx += 1
        start = end - overlap_chars if end < len(text) else len(text)

    return chunks


def _hash(text: str) -> str:
    """SHA-256 truncated to 16 hex chars."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════
# MLX Embedding Client
# ═══════════════════════════════════════════════════════════════════════

async def embed_texts(texts: list[str], batch_size: int = 512) -> list[list[float]]:
    """Embed a list of texts via MLX server at localhost:8000.

    Auto-chunks into groups of batch_size per HTTP call.
    Returns list of embedding vectors (2560-dim floats).
    Returns empty list on server unavailable.
    """
    if not texts:
        return []

    all_embeddings = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                resp = await client.post(
                    f"{MLX_EMBED_URL}/embed_batch",
                    json={"texts": batch},
                )
                resp.raise_for_status()
                data = resp.json()
                all_embeddings.extend(data["embeddings"])
            except httpx.ConnectError:
                log.warning("MLX embed server unavailable at %s", MLX_EMBED_URL)
                return []
            except Exception as e:
                log.error("MLX embed error at batch %d: %s", i, e)
                return []

    return all_embeddings


# ═══════════════════════════════════════════════════════════════════════
# Batch Embedding Pipeline
# ═══════════════════════════════════════════════════════════════════════

async def embed_entities(conn, world_id, entity_type, rows, extract_fn,
                         *, force=False):
    """Full pipeline for a batch of entity rows.

    1. Extract text via extract_fn(row)
    2. Chunk each text
    3. Hash-check against existing embeddings (skip unchanged)
    4. Embed new/changed chunks via MLX
    5. Upsert into embeddings table

    Returns dict: {embedded: N, skipped: N, errors: N}
    """
    stats = {"embedded": 0, "skipped": 0, "errors": 0}

    # Step 1-2: Extract and chunk
    to_embed = []  # [(entity_id, chunk_index, chunk_text, content_hash)]
    for row in rows:
        try:
            text = extract_fn(row)
            if not text:
                continue
            chunks = chunk_text(text)
            for chunk in chunks:
                to_embed.append((
                    row["id"],
                    chunk["chunk_index"],
                    chunk["chunk_text"],
                    chunk["content_hash"],
                ))
        except Exception as e:
            log.debug("Extract error for %s/%d: %s", entity_type, row.get("id", -1), e)
            stats["errors"] += 1

    if not to_embed:
        return stats

    # Step 3: Hash-check (skip unchanged unless force)
    if not force:
        existing = await conn.fetch("""
            SELECT entity_id, chunk_index, content_hash
            FROM embeddings
            WHERE world_id = $1 AND entity_type = $2
            AND entity_id = ANY($3::int[])
        """, world_id, entity_type,
            list({eid for eid, _, _, _ in to_embed}))

        existing_hashes = {
            (r["entity_id"], r["chunk_index"]): r["content_hash"]
            for r in existing
        }

        filtered = []
        for eid, cidx, ctext, chash in to_embed:
            old_hash = existing_hashes.get((eid, cidx))
            if old_hash == chash:
                stats["skipped"] += 1
            else:
                filtered.append((eid, cidx, ctext, chash))
        to_embed = filtered

    if not to_embed:
        return stats

    # Step 4: Embed via MLX
    texts_to_embed = [ctext for _, _, ctext, _ in to_embed]
    vectors = await embed_texts(texts_to_embed)
    if not vectors:
        log.warning("No vectors returned — MLX server may be down")
        stats["errors"] += len(to_embed)
        return stats

    if len(vectors) != len(to_embed):
        log.error("Vector count mismatch: got %d for %d texts",
                  len(vectors), len(to_embed))
        stats["errors"] += len(to_embed)
        return stats

    # Step 5: Batch upsert into embeddings table
    upsert_sql = """
        INSERT INTO embeddings (world_id, entity_type, entity_id,
                                chunk_index, chunk_text, content_hash,
                                embedding, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, now())
        ON CONFLICT (world_id, entity_type, entity_id, chunk_index)
        DO UPDATE SET chunk_text = EXCLUDED.chunk_text,
                      content_hash = EXCLUDED.content_hash,
                      embedding = EXCLUDED.embedding,
                      created_at = now()
    """

    args = []
    for i, (eid, cidx, ctext, chash) in enumerate(to_embed):
        vec = np.array(vectors[i], dtype=np.float32)
        args.append((world_id, entity_type, eid, cidx, ctext, chash, vec))

    try:
        await conn.executemany(upsert_sql, args)
        stats["embedded"] += len(args)
    except Exception as e:
        log.error("Batch upsert error for %s: %s", entity_type, e)
        stats["errors"] += len(args)

    return stats


async def embed_changed(conn, world_id, changes):
    """Embed a list of changed entities from a watcher cycle.

    changes: list of (entity_type, entity_id, rendered_text) tuples.
    Returns count of newly embedded items.
    """
    if not changes:
        return 0

    count = 0
    # Group by entity_type for batch embedding
    by_type = {}
    for etype, eid, text in changes:
        by_type.setdefault(etype, []).append((eid, text))

    for etype, items in by_type.items():
        # Chunk all texts
        to_embed = []
        for eid, text in items:
            chunks = chunk_text(text)
            for chunk in chunks:
                to_embed.append((eid, chunk["chunk_index"],
                                 chunk["chunk_text"], chunk["content_hash"]))

        # Hash-check
        existing = await conn.fetch("""
            SELECT entity_id, chunk_index, content_hash
            FROM embeddings
            WHERE world_id = $1 AND entity_type = $2
            AND entity_id = ANY($3::int[])
        """, world_id, etype, list({eid for eid, _, _, _ in to_embed}))

        existing_hashes = {
            (r["entity_id"], r["chunk_index"]): r["content_hash"]
            for r in existing
        }

        filtered = [(eid, cidx, ctext, chash)
                     for eid, cidx, ctext, chash in to_embed
                     if existing_hashes.get((eid, cidx)) != chash]

        if not filtered:
            continue

        # Embed
        vectors = await embed_texts([t for _, _, t, _ in filtered])
        if not vectors or len(vectors) != len(filtered):
            continue

        # Upsert
        upsert_sql = """
            INSERT INTO embeddings (world_id, entity_type, entity_id,
                                    chunk_index, chunk_text, content_hash,
                                    embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, now())
            ON CONFLICT (world_id, entity_type, entity_id, chunk_index)
            DO UPDATE SET chunk_text = EXCLUDED.chunk_text,
                          content_hash = EXCLUDED.content_hash,
                          embedding = EXCLUDED.embedding,
                          created_at = now()
        """
        args = []
        for i, (eid, cidx, ctext, chash) in enumerate(filtered):
            vec = np.array(vectors[i], dtype=np.float32)
            args.append((world_id, etype, eid, cidx, ctext, chash, vec))

        try:
            await conn.executemany(upsert_sql, args)
            count += len(args)
        except Exception as e:
            log.debug("Live embed batch upsert error: %s", e)

    return count


async def build_vector_index(conn, min_rows=1000):
    """Build vector index if enough rows exist and dimensions allow.

    pgvector caps IVFFlat/HNSW indexes at 2000 dimensions. Our Qwen3
    embeddings are 2560-dim, so index creation is skipped. Sequential
    scan is fast enough for <1M vectors. For larger datasets, consider
    halfvec (4000 dim limit) or dimension truncation.
    """
    from chronicler.config import EMBED_DIM

    row_count = await conn.fetchval("SELECT COUNT(*) FROM embeddings")
    if row_count < min_rows:
        log.info("Only %d embeddings — skipping vector index (need %d)",
                 row_count, min_rows)
        return False

    if EMBED_DIM > 2000:
        log.info("Embedding dim %d exceeds pgvector index limit (2000). "
                 "Using sequential scan (fast enough for %d rows).",
                 EMBED_DIM, row_count)
        return False

    m = 16
    ef = 64
    log.info("Building HNSW index for %d embeddings (m=%d, ef=%d)...",
             row_count, m, ef)
    t0 = time.time()

    await conn.execute("DROP INDEX IF EXISTS idx_embeddings_vector",
                       timeout=600)
    await conn.execute(f"""
        CREATE INDEX idx_embeddings_vector
        ON embeddings USING hnsw (embedding vector_cosine_ops)
        WITH (m = {m}, ef_construction = {ef})
    """, timeout=600)

    elapsed = time.time() - t0
    log.info("HNSW index built in %.1fs", elapsed)
    return True


async def get_embed_stats(conn, world_id):
    """Get embedding statistics per entity type."""
    rows = await conn.fetch("""
        SELECT entity_type, COUNT(*) AS count,
               MIN(created_at) AS oldest,
               MAX(created_at) AS newest
        FROM embeddings
        WHERE world_id = $1
        GROUP BY entity_type
        ORDER BY entity_type
    """, world_id)

    total = await conn.fetchval(
        "SELECT COUNT(*) FROM embeddings WHERE world_id = $1", world_id)

    # Check if IVFFlat index exists
    has_index = await conn.fetchval("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'embeddings' AND indexname = 'idx_embeddings_vector'
    """)

    return {
        "by_type": [dict(r) for r in rows],
        "total": total,
        "has_vector_index": bool(has_index),
    }
