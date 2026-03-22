"""Stage 3.4.6-3.4.7: Hybrid search — vector + keyword with RRF merge.

Provides:
  - hybrid_search(): combined vector + ILIKE with Reciprocal Rank Fusion
  - semantic_search(): pure vector search with similarity threshold
  - narrative_context_search(): returns ContextBlocks for narrative assembly
"""

import logging

import numpy as np

from chronicler.embedding.pipeline import embed_texts
from chronicler.storyteller.context import extract_keywords

log = logging.getLogger(__name__)


async def hybrid_search(pool, world_id, query, *, limit=20):
    """Combined vector + keyword search with Reciprocal Rank Fusion.

    1. Embed query via MLX
    2. pgvector cosine search (top N)
    3. ILIKE keyword search (top N)
    4. RRF merge (k=60) to combine ranked lists
    5. Return sorted by RRF score

    Returns list of dicts: [{entity_type, entity_id, chunk_text, score}, ...]
    """
    async with pool.acquire() as conn:
        # Vector search
        vector_results = []
        query_vectors = await embed_texts([query])
        if query_vectors:
            qvec = np.array(query_vectors[0], dtype=np.float32)
            vector_results = await conn.fetch("""
                SELECT entity_type, entity_id, chunk_index, chunk_text,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM embeddings
                WHERE world_id = $2 AND embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, qvec, world_id, limit * 2)

        # Keyword search
        keywords = extract_keywords(query)
        keyword_results = []
        if keywords:
            conditions = " OR ".join(
                f"chunk_text ILIKE '%' || ${i+2} || '%'"
                for i in range(len(keywords)))
            keyword_results = await conn.fetch(f"""
                SELECT entity_type, entity_id, chunk_index, chunk_text,
                       0.0::float AS similarity
                FROM embeddings
                WHERE world_id = $1 AND ({conditions})
                LIMIT {limit * 2}
            """, world_id, *keywords)

        # RRF merge (k=60)
        return _rrf_merge(vector_results, keyword_results, limit=limit)


def _rrf_merge(vector_results, keyword_results, *, k=60, limit=20):
    """Reciprocal Rank Fusion to merge two ranked lists.

    RRF score = sum(1 / (k + rank)) for each list the item appears in.
    """
    scores = {}  # (entity_type, entity_id, chunk_index) → {score, data}

    for rank, r in enumerate(vector_results):
        key = (r["entity_type"], r["entity_id"], r["chunk_index"])
        if key not in scores:
            scores[key] = {
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "chunk_text": r["chunk_text"],
                "similarity": float(r["similarity"]),
                "rrf_score": 0.0,
            }
        scores[key]["rrf_score"] += 1.0 / (k + rank)

    for rank, r in enumerate(keyword_results):
        key = (r["entity_type"], r["entity_id"], r["chunk_index"])
        if key not in scores:
            scores[key] = {
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "chunk_text": r["chunk_text"],
                "similarity": 0.0,
                "rrf_score": 0.0,
            }
        scores[key]["rrf_score"] += 1.0 / (k + rank)

    ranked = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
    return ranked[:limit]


async def semantic_search(pool, world_id, query_vector, *,
                          limit=10, threshold=0.3):
    """Pure vector search with similarity threshold.

    query_vector: pre-computed embedding vector (np.array or list).
    Returns list of dicts with similarity >= threshold.
    """
    if isinstance(query_vector, list):
        query_vector = np.array(query_vector, dtype=np.float32)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT entity_type, entity_id, chunk_index, chunk_text,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM embeddings
            WHERE world_id = $2 AND embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """, query_vector, world_id, limit * 2)

    return [
        {
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "chunk_text": r["chunk_text"],
            "similarity": float(r["similarity"]),
        }
        for r in rows
        if float(r["similarity"]) >= threshold
    ][:limit]
