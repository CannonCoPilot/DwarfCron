"""Stage 3.6.7: Narrative Context Assembler.

Given a query type and parameters, assembles an optimal context window
from structured facts + narrative arcs + character profiles + event
summaries within a configurable token budget.

Token budget: defaults to 32K tokens (~128K chars at ~4 chars/token).
Priority tiers (filled in order until budget exhausted):
  T1: Core structured facts (entities, dates, relationships)
  T2: Relevant narrative arcs + event summaries
  T3: Character profiles
  T4: Supporting events + cluster summaries
"""

import json
import logging
from dataclasses import dataclass, field

import asyncpg

log = logging.getLogger(__name__)

# Approximate chars per token for English text (conservative)
CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_BUDGET = 32_000


@dataclass
class ContextBlock:
    """A labeled block of context text with priority metadata."""
    tier: int  # 1-4, lower = higher priority
    category: str
    text: str
    tokens_est: int = 0

    def __post_init__(self):
        self.tokens_est = len(self.text) // CHARS_PER_TOKEN + 1


@dataclass
class AssembledContext:
    """Result of context assembly — ready to inject into LLM prompt."""
    blocks: list[ContextBlock] = field(default_factory=list)
    total_tokens: int = 0
    budget: int = DEFAULT_TOKEN_BUDGET
    truncated: bool = False

    @property
    def text(self) -> str:
        """Render all blocks as a single context string."""
        sections: dict[str, list[str]] = {}
        for b in self.blocks:
            sections.setdefault(b.category, []).append(b.text)
        parts = []
        for cat, texts in sections.items():
            parts.append(f"## {cat}")
            parts.extend(texts)
            parts.append("")
        return "\n".join(parts)

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "total_tokens": self.total_tokens,
            "budget": self.budget,
            "block_count": len(self.blocks),
            "truncated": self.truncated,
            "categories": list({b.category for b in self.blocks}),
        }


async def assemble_context(
    conn: asyncpg.Connection,
    world_id: int,
    query_type: str,
    *,
    target_id: int | None = None,
    year: int | None = None,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
) -> AssembledContext:
    """Assemble narrative context for a given query type.

    Query types:
      - fortress_saga: Full fortress narrative (all arcs, key characters, timeline)
      - character_focus: Deep context for a specific HF (target_id required)
      - year_chronicle: Context for a specific year (year required)
      - event_detail: Context surrounding a specific event (target_id = event_id)
      - world_overview: General world overview

    Returns AssembledContext with blocks sorted by priority, within budget.
    """
    ctx = AssembledContext(budget=token_budget)
    candidates: list[ContextBlock] = []

    if query_type == "fortress_saga":
        candidates = await _gather_fortress_saga(conn, world_id)
    elif query_type == "character_focus":
        candidates = await _gather_character_focus(conn, world_id, target_id or 0)
    elif query_type == "year_chronicle":
        candidates = await _gather_year_chronicle(conn, world_id, year or 1)
    elif query_type == "event_detail":
        candidates = await _gather_event_detail(conn, world_id, target_id or 0)
    elif query_type == "world_overview":
        candidates = await _gather_world_overview(conn, world_id)
    else:
        log.warning("Unknown query_type: %s, using world_overview", query_type)
        candidates = await _gather_world_overview(conn, world_id)

    # Add embedding-based context (semantic search, T3 priority)
    embed_blocks = await _gather_embedding_context(conn, world_id, query_type,
                                                    target_id=target_id)
    candidates.extend(embed_blocks)

    # Sort by tier (priority), then by token cost (smaller blocks first within tier)
    candidates.sort(key=lambda b: (b.tier, b.tokens_est))

    # Fill budget
    used = 0
    for block in candidates:
        if used + block.tokens_est > token_budget:
            ctx.truncated = True
            continue
        ctx.blocks.append(block)
        used += block.tokens_est

    ctx.total_tokens = used
    log.info("Context assembled: %d blocks, ~%d tokens (budget %d, truncated=%s)",
             len(ctx.blocks), used, token_budget, ctx.truncated)
    return ctx


# ═══════════════════════════════════════════════════════════════════════
# Gatherers — each returns candidate ContextBlocks for assembly
# ═══════════════════════════════════════════════════════════════════════

async def _gather_fortress_saga(
    conn: asyncpg.Connection, world_id: int
) -> list[ContextBlock]:
    """Gather context for a full fortress narrative."""
    blocks: list[ContextBlock] = []

    # T1: World facts
    world = await conn.fetchrow(
        "SELECT name, alt_name FROM worlds WHERE id = $1", world_id)
    max_year = await conn.fetchval(
        "SELECT MAX(year) FROM history_events WHERE world_id = $1", world_id)
    if world:
        blocks.append(ContextBlock(
            tier=1, category="World Facts",
            text=f"World: {world['name']} ({world['alt_name'] or ''}), "
                 f"{max_year or '?'} years of history"))

    # T1: Civilization summary
    civs = await conn.fetch("""
        SELECT e.name, e.race, COUNT(s.id) AS site_count
        FROM entities e
        LEFT JOIN sites s ON s.owner_entity_id = e.id AND s.world_id = e.world_id
        WHERE e.world_id = $1 AND e.type = 'civilization'
        GROUP BY e.id, e.name, e.race
        ORDER BY site_count DESC LIMIT 5
    """, world_id)
    for c in civs:
        blocks.append(ContextBlock(
            tier=1, category="Civilizations",
            text=f"{c['name']} ({c['race']}): {c['site_count']} sites"))

    # T1: Fortress denizens summary
    pop = await conn.fetchval(
        "SELECT COUNT(*) FROM fortress_denizens WHERE world_id = $1 AND status = 'alive'",
        world_id)
    blocks.append(ContextBlock(
        tier=1, category="Fortress State",
        text=f"Current population: {pop or 0} living denizens"))

    # T2: Top narrative arcs (by dramatic weight)
    arcs = await conn.fetch("""
        SELECT arc_type, title, start_tick / 403200 AS start_year,
               end_tick / 403200 AS end_year, dramatic_weight, resolution
        FROM narrative_arcs
        WHERE world_id = $1 AND title IS NOT NULL
        ORDER BY dramatic_weight DESC LIMIT 20
    """, world_id)
    for a in arcs:
        title = a['title'] or a['arc_type'].replace('_', ' ')
        blocks.append(ContextBlock(
            tier=2, category="Narrative Arcs",
            text=f"[{a['arc_type']}] {title} (Y{a['start_year']}-Y{a['end_year']}, "
                 f"weight: {a['dramatic_weight']:.1f}, "
                 f"resolution: {a['resolution'] or 'ongoing'})"))

    # T2: Year summaries
    summaries = await conn.fetch("""
        SELECT scope_id AS year, summary_text
        FROM event_summaries
        WHERE world_id = $1 AND granularity = 'year'
        ORDER BY scope_id
    """, world_id)
    for s in summaries:
        blocks.append(ContextBlock(
            tier=2, category="Year Summaries",
            text=f"Year {s['year']}: {s['summary_text']}"))

    # T3: Character profiles (top by prominence)
    profiles = await conn.fetch("""
        SELECT cn.character_name, cn.role_description, cn.arc_summary,
               cn.personality_voice, hf.prominence_score
        FROM character_narratives cn
        JOIN historical_figures hf ON hf.world_id = cn.world_id AND hf.id = cn.hf_id
        WHERE cn.world_id = $1
        ORDER BY hf.prominence_score DESC LIMIT 15
    """, world_id)
    for p in profiles:
        blocks.append(ContextBlock(
            tier=3, category="Character Profiles",
            text=f"{p['character_name']}: {p['role_description']} "
                 f"{p['arc_summary']} Voice: {p['personality_voice']}"))

    # T4: Event clusters
    clusters = await conn.fetch("""
        SELECT cluster_type, summary, start_tick / 403200 AS start_year,
               end_tick / 403200 AS end_year,
               jsonb_array_length(event_ids) AS event_count
        FROM event_clusters
        WHERE world_id = $1 AND summary IS NOT NULL
        ORDER BY jsonb_array_length(event_ids) DESC LIMIT 20
    """, world_id)
    for cl in clusters:
        blocks.append(ContextBlock(
            tier=4, category="Event Clusters",
            text=f"[{cl['cluster_type']}] {cl['summary']} "
                 f"(Y{cl['start_year']}-Y{cl['end_year']}, {cl['event_count']} events)"))

    return blocks


async def _gather_character_focus(
    conn: asyncpg.Connection, world_id: int, hf_id: int
) -> list[ContextBlock]:
    """Gather deep context for a specific character."""
    blocks: list[ContextBlock] = []

    # T1: Character basic info
    hf = await conn.fetchrow("""
        SELECT name, race, caste, birth_year, death_year, kill_count,
               prominence_score, is_necromancer, is_vampire, is_deity, is_werebeast,
               details
        FROM historical_figures WHERE world_id = $1 AND id = $2
    """, world_id, hf_id)
    if not hf:
        return blocks

    flags = []
    for f in ("is_necromancer", "is_vampire", "is_deity", "is_werebeast"):
        if hf[f]:
            flags.append(f.replace("is_", ""))
    lifespan = f"born Y{hf['birth_year'] or '?'}"
    if hf['death_year']:
        lifespan += f", died Y{hf['death_year']}"
    blocks.append(ContextBlock(
        tier=1, category="Character Facts",
        text=f"{hf['name']} — {hf['race']} {hf['caste'] or ''}, {lifespan}, "
             f"kills: {hf['kill_count'] or 0}, traits: {', '.join(flags) or 'none'}"))

    # T1: Character profile (if exists)
    profile = await conn.fetchrow("""
        SELECT role_description, arc_summary, personality_voice, key_moments
        FROM character_narratives WHERE world_id = $1 AND hf_id = $2
    """, world_id, hf_id)
    if profile:
        blocks.append(ContextBlock(
            tier=1, category="Character Profile",
            text=f"Role: {profile['role_description']}\n"
                 f"Arc: {profile['arc_summary']}\n"
                 f"Voice: {profile['personality_voice']}"))

    # T1: Relationships
    links = await conn.fetch("""
        SELECT hl.link_type, hf2.name AS target_name, hf2.race
        FROM hf_links hl
        JOIN historical_figures hf2 ON hf2.world_id = hl.world_id AND hf2.id = hl.target_hf_id
        WHERE hl.world_id = $1 AND hl.hf_id = $2
        LIMIT 15
    """, world_id, hf_id)
    for l in links:
        blocks.append(ContextBlock(
            tier=1, category="Relationships",
            text=f"{l['link_type']}: {l['target_name']} ({l['race']})"))

    # T2: Key events involving this character
    events = await conn.fetch("""
        SELECT he.event_type, he.year, ne.narrative_weight, ne.emotional_tone,
               s.name AS site_name
        FROM history_events he
        JOIN narrative_events ne ON ne.world_id = he.world_id AND ne.event_id = he.id
        LEFT JOIN sites s ON s.world_id = he.world_id AND s.id = he.site_id
        WHERE he.world_id = $1
        AND (he.details->>'hf_id' = $2::text
             OR he.details->>'hf_id_1' = $2::text
             OR he.details->>'hf_id_2' = $2::text
             OR he.details->>'slayer_hf_id' = $2::text)
        ORDER BY ne.narrative_weight DESC
        LIMIT 25
    """, world_id, str(hf_id))
    for ev in events:
        site = f" at {ev['site_name']}" if ev['site_name'] else ""
        blocks.append(ContextBlock(
            tier=2, category="Character Events",
            text=f"Y{ev['year']}: {ev['event_type'].replace('_', ' ')}{site} "
                 f"(weight: {ev['narrative_weight']:.1f}, tone: {ev['emotional_tone']})"))

    # T2: Arcs involving this character
    arcs = await conn.fetch("""
        SELECT arc_type, title, start_tick / 403200 AS start_year,
               end_tick / 403200 AS end_year, dramatic_weight
        FROM narrative_arcs
        WHERE world_id = $1 AND characters @> $2::jsonb
        ORDER BY dramatic_weight DESC LIMIT 10
    """, world_id, json.dumps([hf_id]))
    for a in arcs:
        blocks.append(ContextBlock(
            tier=2, category="Character Arcs",
            text=f"[{a['arc_type']}] {a['title'] or '(untitled)'} "
                 f"(Y{a['start_year']}-Y{a['end_year']}, weight: {a['dramatic_weight']:.1f})"))

    # T3: Entity memberships
    memberships = await conn.fetch("""
        SELECT hel.link_type, hel.position_name, e.name
        FROM hf_entity_links hel
        LEFT JOIN entities e ON e.world_id = hel.world_id AND e.id = hel.entity_id
        WHERE hel.world_id = $1 AND hel.hf_id = $2
        LIMIT 10
    """, world_id, hf_id)
    for m in memberships:
        pos = f" as {m['position_name']}" if m['position_name'] else ""
        blocks.append(ContextBlock(
            tier=3, category="Memberships",
            text=f"{m['link_type']}{pos} of {m['name'] or '(unknown)'}"))

    return blocks


async def _gather_year_chronicle(
    conn: asyncpg.Connection, world_id: int, year: int
) -> list[ContextBlock]:
    """Gather context for a specific year's chronicle."""
    blocks: list[ContextBlock] = []

    # T1: Year summary (if exists)
    summary = await conn.fetchval("""
        SELECT summary_text FROM event_summaries
        WHERE world_id = $1 AND scope = 'world' AND scope_id = $2 AND granularity = 'year'
    """, world_id, year)
    if summary:
        blocks.append(ContextBlock(
            tier=1, category="Year Summary",
            text=f"Year {year}: {summary}"))

    # T1: Top events this year
    events = await conn.fetch("""
        SELECT he.event_type, he.year, he.details, ne.narrative_weight,
               ne.emotional_tone, ne.drama_score,
               s.name AS site_name, hf.name AS hf_name
        FROM history_events he
        JOIN narrative_events ne ON ne.world_id = he.world_id AND ne.event_id = he.id
        LEFT JOIN sites s ON s.world_id = he.world_id AND s.id = he.site_id
        LEFT JOIN historical_figures hf ON hf.world_id = he.world_id
            AND hf.id = CAST(he.details->>'hf_id' AS INTEGER)
        WHERE he.world_id = $1 AND he.year = $2
        ORDER BY ne.narrative_weight DESC
        LIMIT 30
    """, world_id, year)
    for ev in events:
        who = f" — {ev['hf_name']}" if ev['hf_name'] else ""
        where = f" at {ev['site_name']}" if ev['site_name'] else ""
        blocks.append(ContextBlock(
            tier=1, category="Year Events",
            text=f"{ev['event_type'].replace('_', ' ')}{who}{where} "
                 f"(weight: {ev['narrative_weight']:.1f}, "
                 f"tone: {ev['emotional_tone']})"))

    # T2: Arcs active during this year
    tick_start = year * 403200
    tick_end = (year + 1) * 403200
    arcs = await conn.fetch("""
        SELECT arc_type, title, start_tick / 403200 AS start_year,
               end_tick / 403200 AS end_year, dramatic_weight
        FROM narrative_arcs
        WHERE world_id = $1 AND start_tick <= $3 AND end_tick >= $2
        ORDER BY dramatic_weight DESC LIMIT 10
    """, world_id, tick_start, tick_end)
    for a in arcs:
        blocks.append(ContextBlock(
            tier=2, category="Active Arcs",
            text=f"[{a['arc_type']}] {a['title'] or '(untitled)'} "
                 f"(Y{a['start_year']}-Y{a['end_year']}, weight: {a['dramatic_weight']:.1f})"))

    # T2: Adjacent year summaries for narrative continuity
    for adj_year in (year - 1, year + 1):
        adj = await conn.fetchval("""
            SELECT summary_text FROM event_summaries
            WHERE world_id = $1 AND scope = 'world'
            AND scope_id = $2 AND granularity = 'year'
        """, world_id, adj_year)
        if adj:
            blocks.append(ContextBlock(
                tier=2, category="Adjacent Years",
                text=f"Year {adj_year}: {adj}"))

    # T3: Clusters in this year
    clusters = await conn.fetch("""
        SELECT cluster_type, summary, jsonb_array_length(event_ids) AS event_count
        FROM event_clusters
        WHERE world_id = $1 AND start_tick >= $2 AND end_tick <= $3
        AND summary IS NOT NULL
    """, world_id, tick_start, tick_end)
    for cl in clusters:
        blocks.append(ContextBlock(
            tier=3, category="Event Clusters",
            text=f"[{cl['cluster_type']}] {cl['summary']} ({cl['event_count']} events)"))

    return blocks


async def _gather_event_detail(
    conn: asyncpg.Connection, world_id: int, event_id: int
) -> list[ContextBlock]:
    """Gather context surrounding a specific event."""
    blocks: list[ContextBlock] = []

    # T1: The event itself
    ev = await conn.fetchrow("""
        SELECT he.event_type, he.year, he.details, he.site_id,
               ne.narrative_weight, ne.drama_score, ne.emotional_tone,
               ne.irony_flags,
               s.name AS site_name
        FROM history_events he
        JOIN narrative_events ne ON ne.world_id = he.world_id AND ne.event_id = he.id
        LEFT JOIN sites s ON s.world_id = he.world_id AND s.id = he.site_id
        WHERE he.world_id = $1 AND he.id = $2
    """, world_id, event_id)
    if not ev:
        return blocks

    details = ev['details'] if isinstance(ev['details'], dict) else {}
    blocks.append(ContextBlock(
        tier=1, category="Event Detail",
        text=f"{ev['event_type']} in Y{ev['year']} at {ev['site_name'] or '(unknown)'}\n"
             f"Weight: {ev['narrative_weight']:.1f}, Drama: {ev['drama_score']:.1f}, "
             f"Tone: {ev['emotional_tone']}\n"
             f"Details: {json.dumps(details, default=str)[:500]}"))

    # T1: Causal chain — what caused this and what it caused
    causes = await conn.fetch("""
        SELECT ecl.link_type, ecl.confidence,
               he.event_type AS cause_type, he.year AS cause_year
        FROM event_causal_links ecl
        JOIN history_events he ON he.world_id = ecl.world_id AND he.id = ecl.cause_event_id
        WHERE ecl.world_id = $1 AND ecl.effect_event_id = $2
    """, world_id, event_id)
    for c in causes:
        blocks.append(ContextBlock(
            tier=1, category="Causal Chain (Causes)",
            text=f"Caused by: {c['cause_type']} in Y{c['cause_year']} "
                 f"({c['link_type']}, confidence: {c['confidence']:.2f})"))

    effects = await conn.fetch("""
        SELECT ecl.link_type, ecl.confidence,
               he.event_type AS effect_type, he.year AS effect_year
        FROM event_causal_links ecl
        JOIN history_events he ON he.world_id = ecl.world_id AND he.id = ecl.effect_event_id
        WHERE ecl.world_id = $1 AND ecl.cause_event_id = $2
    """, world_id, event_id)
    for e in effects:
        blocks.append(ContextBlock(
            tier=1, category="Causal Chain (Effects)",
            text=f"Led to: {e['effect_type']} in Y{e['effect_year']} "
                 f"({e['link_type']}, confidence: {e['confidence']:.2f})"))

    # T2: Characters involved
    for key in ("hf_id", "hf_id_1", "hf_id_2", "slayer_hf_id"):
        hf_id_str = details.get(key)
        if hf_id_str:
            try:
                hf_id = int(hf_id_str)
            except (ValueError, TypeError):
                continue
            profile = await conn.fetchrow("""
                SELECT cn.character_name, cn.role_description, cn.arc_summary
                FROM character_narratives cn
                WHERE cn.world_id = $1 AND cn.hf_id = $2
            """, world_id, hf_id)
            if profile:
                blocks.append(ContextBlock(
                    tier=2, category="Involved Characters",
                    text=f"{profile['character_name']}: {profile['role_description']} "
                         f"— {profile['arc_summary'][:200]}"))

    # T3: Nearby events (same year, same site)
    nearby = await conn.fetch("""
        SELECT he.id, he.event_type, ne.narrative_weight
        FROM history_events he
        JOIN narrative_events ne ON ne.world_id = he.world_id AND ne.event_id = he.id
        WHERE he.world_id = $1 AND he.year = $2
        AND he.site_id = $3 AND he.id != $4
        ORDER BY ne.narrative_weight DESC LIMIT 10
    """, world_id, ev['year'], ev['site_id'], event_id)
    for n in nearby:
        blocks.append(ContextBlock(
            tier=3, category="Nearby Events",
            text=f"{n['event_type'].replace('_', ' ')} (weight: {n['narrative_weight']:.1f})"))

    return blocks


async def _gather_world_overview(
    conn: asyncpg.Connection, world_id: int
) -> list[ContextBlock]:
    """Gather general world overview context."""
    blocks: list[ContextBlock] = []

    # T1: World basics
    world = await conn.fetchrow(
        "SELECT name, alt_name FROM worlds WHERE id = $1", world_id)
    max_year = await conn.fetchval(
        "SELECT MAX(year) FROM history_events WHERE world_id = $1", world_id)
    if world:
        blocks.append(ContextBlock(
            tier=1, category="World",
            text=f"World: {world['name']} ({world['alt_name'] or ''}), "
                 f"{max_year or '?'} years of history"))

    # T1: Stats
    stats = {}
    for table in ("historical_figures", "sites", "entities", "artifacts"):
        stats[table] = await conn.fetchval(
            f"SELECT COUNT(*) FROM {table} WHERE world_id = $1", world_id)
    event_count = await conn.fetchval(
        "SELECT COUNT(*) FROM history_events WHERE world_id = $1", world_id)
    blocks.append(ContextBlock(
        tier=1, category="World Statistics",
        text=f"HFs: {stats['historical_figures']:,}, Sites: {stats['sites']:,}, "
             f"Entities: {stats['entities']:,}, Artifacts: {stats['artifacts']:,}, "
             f"Events: {event_count:,}"))

    # T2: Top arcs
    arcs = await conn.fetch("""
        SELECT arc_type, title, dramatic_weight
        FROM narrative_arcs WHERE world_id = $1 AND title IS NOT NULL
        ORDER BY dramatic_weight DESC LIMIT 10
    """, world_id)
    for a in arcs:
        blocks.append(ContextBlock(
            tier=2, category="Top Story Arcs",
            text=f"[{a['arc_type']}] {a['title']} (weight: {a['dramatic_weight']:.1f})"))

    # T3: Year summaries (sample every 50 years)
    summaries = await conn.fetch("""
        SELECT scope_id AS year, summary_text FROM event_summaries
        WHERE world_id = $1 AND granularity = 'year'
        ORDER BY scope_id
    """, world_id)
    for i, s in enumerate(summaries):
        if i % 50 == 0 or i == len(summaries) - 1:
            blocks.append(ContextBlock(
                tier=3, category="Timeline Samples",
                text=f"Year {s['year']}: {s['summary_text']}"))

    return blocks


# ═══════════════════════════════════════════════════════════════════════
# Embedding-based context (Stage 3.4)
# ═══════════════════════════════════════════════════════════════════════

# Query type → natural language search query for embedding lookup
_QUERY_PROMPTS = {
    "fortress_saga": "major events and characters in the fortress history",
    "character_focus": None,  # built dynamically from target_id
    "year_chronicle": "notable events and developments during this year",
    "event_detail": "related events and involved figures",
    "world_overview": "most important events and figures in world history",
}


async def _gather_embedding_context(
    conn, world_id, query_type, *, target_id=None, limit=10
) -> list[ContextBlock]:
    """Gather context blocks from embedding semantic search.

    Additive — never replaces SQL-based gatherers. Returns T3-priority
    ContextBlocks from semantically relevant embeddings.
    """
    import numpy as np
    from chronicler.embedding.pipeline import embed_texts

    blocks: list[ContextBlock] = []

    # Check if embeddings table has data
    has_embeddings = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM embeddings WHERE world_id = $1 LIMIT 1)",
        world_id)
    if not has_embeddings:
        return blocks

    # Build search query
    if query_type == "character_focus" and target_id:
        hf = await conn.fetchrow(
            "SELECT name, race FROM historical_figures "
            "WHERE world_id = $1 AND id = $2", world_id, target_id)
        if hf:
            search_query = f"{hf['name']} {hf['race']} events and relationships"
        else:
            return blocks
    else:
        search_query = _QUERY_PROMPTS.get(query_type,
                                           "important events and figures")

    # Embed the query
    vectors = await embed_texts([search_query])
    if not vectors:
        return blocks

    qvec = np.array(vectors[0], dtype=np.float32)

    # Vector search
    rows = await conn.fetch("""
        SELECT entity_type, entity_id, chunk_text,
               1 - (embedding <=> $1::vector) AS similarity
        FROM embeddings
        WHERE world_id = $2 AND embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $3
    """, qvec, world_id, limit)

    for r in rows:
        sim = float(r["similarity"])
        if sim < 0.3:
            continue
        blocks.append(ContextBlock(
            tier=3,
            category="Semantic Context",
            text=f"[{r['entity_type']}] {r['chunk_text']}"))

    if blocks:
        log.debug("Embedding context: %d blocks from semantic search", len(blocks))

    return blocks
