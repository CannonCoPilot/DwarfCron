"""Two-score architecture for Chronicler CDM entities.

Computes prominence_score and salience_score independently for 13 entity types.
Prominence = "common knowledge" (structural reach, event count, link count).
Salience = "narrative value" (supernatural flags, rarity, danger, quality).

There is no importance_score. Each score is computed from its own signal sources.

Entity scoring uses TF-IDF: each entity is scored by how many events it
has, weighted by the rarity of those event types *within its own entity
type*. A religion that claimed an artifact (1.1% of religions) scores
higher per-event than one that merely recruited members (100% of religions).
"""

import logging
import math

log = logging.getLogger(__name__)

# Floor weights for inherently significant event types.
# Actual weight = max(floor, computed IDF). The floor prevents narratively
# important but common events from scoring zero.
EVENT_FLOOR_WEIGHTS: dict[str, float] = {
    # Military conflict
    "attacked site": 5.0,
    "field battle": 5.0,
    "destroyed site": 5.0,
    "razed structure": 5.0,
    "plundered site": 5.0,
    "hf attacked site": 4.0,
    "hf destroyed site": 4.0,
    # Political change
    "entity overthrown": 4.0,
    "site taken over": 4.0,
    "new site leader": 3.0,
    "entity dissolved": 3.0,
    # Criminal/unusual
    "entity primary criminals": 4.0,
    "sneak into site": 4.0,
    # Structural creation
    "created site": 2.0,
    "created structure": 2.0,
    "created world construction": 2.0,
    # Cultural
    "artifact claim formed": 3.0,
}

# Floor weights for HF link types
LINK_FLOOR_WEIGHTS: dict[str, float] = {
    "criminal": 3.0,
    "prisoner": 3.0,
    "former prisoner": 2.0,
    "slave": 4.0,
    "former slave": 3.0,
    "enemy": 1.0,
}

# Fixed weights for event collection participation (wars, sieges, etc.)
COLLECTION_WEIGHTS: dict[str, dict[str, float]] = {
    "attacker": {
        "war": 15.0,
        "site conquered": 10.0,
        "abduction": 3.0,
        "theft": 3.0,
    },
    "defender": {
        "war": 12.0,
        "site conquered": 8.0,
        "beast attack": 5.0,
        "abduction": 3.0,
        "theft": 3.0,
    },
}

# Site category scoring baselines
SITE_CATEGORIES: dict[str, dict] = {
    "commonly_known": {
        "types": ["fortress", "castle", "mountain halls", "town", "hillocks", "hamlet"],
        "p_base": 50, "s_base": 0,
    },
    "uncommonly_known": {
        "types": ["cave", "forest retreat", "lair", "camp", "monastery", "fort"],
        "p_base": 15, "s_base": 20,
    },
    "mysterious": {
        "types": ["shrine", "labyrinth", "vault", "tomb", "tower"],
        "p_base": 5, "s_base": 50,
    },
    "dark": {
        "types": ["dark fortress", "dark pits"],
        "p_base": 20, "s_base": 40,
    },
}

# Build reverse lookup: site_type -> (p_base, s_base)
_SITE_TYPE_BASES: dict[str, tuple[float, float]] = {}
for _cat in SITE_CATEGORIES.values():
    for _t in _cat["types"]:
        _SITE_TYPE_BASES[_t] = (_cat["p_base"], _cat["s_base"])

# Structure type weights
STRUCTURE_WEIGHTS: dict[str, dict[str, float]] = {
    "temple":    {"p": 15, "s": 0, "s_deity": 30},
    "fortress":  {"p": 15, "s": 0},
    "tomb":      {"p": 12, "s": 20},
    "dungeon":   {"p": 12, "s": 20},
    "mead_hall": {"p": 10, "s": 0},
    "library":   {"p": 10, "s": 0},
    "market":    {"p": 8,  "s": 0},
    "guildhall": {"p": 6,  "s": 0},
    "shop":      {"p": 4,  "s": 0},
}

# Event collection type weights
COLLECTION_TYPE_WEIGHTS: dict[str, float] = {
    "war": 3.0,
    "insurrection": 2.5,
    "persecution": 2.5,
    "beast attack": 2.0,
    "site conquered": 2.0,
    "battle": 1.5,
    "duel": 1.5,
    "abduction": 1.0,
    "theft": 1.0,
}


async def compute_scores(conn, world_id: int) -> dict[str, int]:
    """Compute and store prominence_score and salience_score for all entities in a world.

    Returns dict with count of updated rows per entity type.
    """
    counts = {}

    # ── [1] Historical Figure prominence + salience (independent) ────
    result = await conn.execute("""
        UPDATE historical_figures hf SET
          prominence_score = (
            LEAST(COALESCE(hf.event_count, 0) * 2, 500)
            + LEAST(COALESCE(links.cnt, 0) * 3, 100)
            + COALESCE(positions.cnt, 0) * 20
            + COALESCE(artifacts.cnt, 0) * 30
            + LEAST(COALESCE(site_links.cnt, 0) * 5, 50)
            + LEAST(COALESCE(entity_links.cnt, 0) * 3, 60)
            + (CASE WHEN hf.death_year IS NOT NULL THEN 5 ELSE 0 END)
          ),
          salience_score = (
            COALESCE(hf.kill_count, 0) * 15
            + (hf.is_vampire::int) * 80
            + (hf.is_necromancer::int) * 100
            + (hf.is_deity::int) * 120
            + (hf.is_force::int) * 90
            + (hf.is_werebeast::int) * 70
          )
        FROM (SELECT id FROM historical_figures WHERE world_id = $1) ids
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_links
            WHERE world_id = $1 AND hf_id = ids.id
        ) links ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_position_links
            WHERE world_id = $1 AND hf_id = ids.id AND end_year IS NULL
        ) positions ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM artifacts
            WHERE world_id = $1 AND holder_hf_id = ids.id
        ) artifacts ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_site_links
            WHERE world_id = $1 AND hf_id = ids.id
        ) site_links ON TRUE
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM hf_entity_links
            WHERE world_id = $1 AND hf_id = ids.id
        ) entity_links ON TRUE
        WHERE hf.world_id = $1 AND hf.id = ids.id
    """, world_id)
    counts["historical_figures"] = int(result.split()[-1]) if result else 0
    log.info("  HF prominence + salience scores: %s", result)

    # ── [2] Site prominence + salience (category-based) ──────────────
    site_count = await _compute_site_scores(conn, world_id)
    counts["sites"] = site_count

    # ── [3] Artifact prominence + salience (independent) ─────────────
    result = await conn.execute("""
        UPDATE artifacts a SET
          prominence_score = (
            COALESCE(events.cnt, 0) * 10
            + (CASE WHEN a.name IS NOT NULL AND a.name != '' THEN 50 ELSE 0 END)
          ),
          salience_score = (
            CASE WHEN a.holder_hf_id IS NOT NULL THEN 20 ELSE 0 END
          )
        FROM (SELECT id FROM artifacts WHERE world_id = $1) ids
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS cnt FROM history_events
            WHERE world_id = $1 AND artifact_id = ids.id
        ) events ON TRUE
        WHERE a.world_id = $1 AND a.id = ids.id
    """, world_id)
    counts["artifacts"] = int(result.split()[-1]) if result else 0
    log.info("  Artifact scores: %s", result)

    # ── [4] Entity scoring (IDF-weighted, per entity type) ───────────
    entity_count = await _compute_entity_scores(conn, world_id)
    counts["entities"] = entity_count
    log.info("  Entity scores: %d entities scored", entity_count)

    # ── [5] Art scoring (written works, traditions, author/auteur) ────
    art_counts = await _compute_art_scores(conn, world_id)
    counts.update(art_counts)

    # ── [6] Geographical feature scoring ─────────────────────────────
    geo_counts = await _compute_geo_scores(conn, world_id)
    counts.update(geo_counts)

    # ── [7] Structure scoring ────────────────────────────────────────
    struct_count = await _compute_structure_scores(conn, world_id)
    counts["structures_scored"] = struct_count

    # ── [8] Event collection scoring ─────────────────────────────────
    coll_count = await _compute_collection_scores(conn, world_id)
    counts["collections_scored"] = coll_count

    # ── [9] Underground region scoring ───────────────────────────────
    ug_count = await _compute_underground_scores(conn, world_id)
    counts["underground_regions_scored"] = ug_count

    # ── [10] Mountain peak scoring ───────────────────────────────────
    mt_count = await _compute_mountain_scores(conn, world_id)
    counts["mountain_peaks_scored"] = mt_count

    # ── [11] Normalize new entity type scores to 0-1 ─────────────────
    new_normalize = [
        ("structures", "prominence_score"),
        ("structures", "salience_score"),
        ("history_event_collections", "prominence_score"),
        ("history_event_collections", "salience_score"),
        ("underground_regions", "prominence_score"),
        ("underground_regions", "salience_score"),
        ("mountain_peaks", "prominence_score"),
        ("mountain_peaks", "salience_score"),
    ]
    for table, col in new_normalize:
        await conn.execute(
            f"UPDATE {table} SET {col} = {col} / NULLIF("
            f"  (SELECT MAX({col}) FROM {table} WHERE world_id = $1), 0) "
            f"WHERE world_id = $1 AND {col} > 0",
            world_id,
        )
    log.info("  New entity type scores normalized to 0-1")

    return counts


async def _compute_site_scores(conn, world_id: int) -> int:
    """Compute category-based prominence and salience for sites.

    Each site type gets a base score from its category, then adds
    event-based signals on top.
    """
    sites = await conn.fetch(
        "SELECT id, type FROM sites WHERE world_id = $1",
        world_id,
    )

    if not sites:
        return 0

    # Batch-query event counts, death counts, structure counts, collection counts
    event_counts = {}
    rows = await conn.fetch(
        "SELECT site_id, COUNT(*) AS cnt FROM history_events "
        "WHERE world_id = $1 AND site_id IS NOT NULL GROUP BY site_id",
        world_id,
    )
    for r in rows:
        event_counts[r["site_id"]] = r["cnt"]

    death_counts = {}
    rows = await conn.fetch(
        "SELECT site_id, COUNT(*) AS cnt FROM history_events "
        "WHERE world_id = $1 AND site_id IS NOT NULL AND event_type = 'hf died' "
        "GROUP BY site_id",
        world_id,
    )
    for r in rows:
        death_counts[r["site_id"]] = r["cnt"]

    structure_counts = {}
    rows = await conn.fetch(
        "SELECT site_id, COUNT(*) AS cnt FROM structures "
        "WHERE world_id = $1 GROUP BY site_id",
        world_id,
    )
    for r in rows:
        structure_counts[r["site_id"]] = r["cnt"]

    collection_counts = {}
    rows = await conn.fetch(
        "SELECT site_id, COUNT(*) AS cnt FROM history_event_collections "
        "WHERE world_id = $1 AND site_id IS NOT NULL GROUP BY site_id",
        world_id,
    )
    for r in rows:
        collection_counts[r["site_id"]] = r["cnt"]

    updates = []
    for s in sites:
        site_type = (s["type"] or "").lower()
        p_base, s_base = _SITE_TYPE_BASES.get(site_type, (10, 0))

        ec = event_counts.get(s["id"], 0)
        sc = structure_counts.get(s["id"], 0)
        cc = collection_counts.get(s["id"], 0)
        dc = death_counts.get(s["id"], 0)

        prominence = p_base + ec + sc * 3
        salience = s_base + cc * 5 + dc * 2

        updates.append((prominence, salience, world_id, s["id"]))

    if updates:
        await conn.executemany(
            "UPDATE sites SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            updates,
        )

    log.info("  Site category-based scores: %d sites scored", len(updates))
    return len(updates)


async def _compute_art_scores(conn, world_id: int) -> dict[str, int]:
    """Compute prominence and salience for written works, art traditions, and HF bonuses.

    Pipeline:
      1. Build artifact->written_content map from artifacts.details->writing_id
      2. Build copy count map from 'artifact copied' events
      3. Written work prominence = copy_num * (1 + quality * 0.3)
      4. Written work salience = quality * (1 + style_count) * 1/(1-quality)
      5. Tradition prominence = count of unique authors
      6. Tradition salience = avg work salience
      7. HF is_author / is_auteur flags
      8. HF prominence_score += author + auteur bonuses
      9. Normalize written_contents and art_forms scores to 0.0-1.0
    """
    counts: dict[str, int] = {}

    # ── Step 1: Build artifact -> written_content map ─────────────────
    art_wc_rows = await conn.fetch(
        "SELECT id, (details->>'writing_id')::INT AS writing_id "
        "FROM artifacts WHERE world_id = $1 "
        "AND details->>'writing_id' IS NOT NULL",
        world_id,
    )
    artifact_to_wc: dict[int, int] = {
        r["id"]: r["writing_id"] for r in art_wc_rows
    }
    wc_to_artifacts: dict[int, set[int]] = {}
    for aid, wid in artifact_to_wc.items():
        wc_to_artifacts.setdefault(wid, set()).add(aid)

    log.info("  Art scoring: %d artifacts linked to %d written works",
             len(artifact_to_wc), len(wc_to_artifacts))

    # ── Step 2: Build copy count map from 'artifact copied' events ───
    copy_rows = await conn.fetch(
        "SELECT artifact_id, COUNT(*) AS cnt FROM history_events "
        "WHERE world_id = $1 AND event_type = 'artifact copied' "
        "AND artifact_id IS NOT NULL GROUP BY artifact_id",
        world_id,
    )
    artifact_copies: dict[int, int] = {
        r["artifact_id"]: r["cnt"] for r in copy_rows
    }
    log.info("  Art scoring: %d artifacts have copy events", len(artifact_copies))

    # ── Step 3+4: Written work prominence and salience ────────────────
    all_wc = await conn.fetch(
        "SELECT id, author_hf_id, form, styles, details "
        "FROM written_contents WHERE world_id = $1",
        world_id,
    )

    wc_prominence: dict[int, float] = {}
    wc_salience: dict[int, float] = {}

    for wc in all_wc:
        wc_id = wc["id"]
        details = wc["details"] or {}

        # Copy number ladder: 1 (composed) + 1 (inscribed) + min(copies, 3) = max 5
        copy_num = 1
        artifacts_for_wc = wc_to_artifacts.get(wc_id, set())
        if artifacts_for_wc:
            copy_num += 1
            total_copies = sum(
                artifact_copies.get(aid, 0) for aid in artifacts_for_wc
            )
            copy_num += min(total_copies, 3)

        # Prominence = copy_num * (1 + quality * 0.3)
        author_roll = details.get("author_roll")
        if author_roll is not None and author_roll > 0:
            quality = author_roll / 256.0
        else:
            quality = 0.0

        wc_prominence[wc_id] = copy_num * (1 + quality * 0.3)

        # Salience = quality * (1 + style_count) * 1/(1 - quality_capped)
        styles = wc["styles"] or []
        style_count = len(styles)

        if quality > 0:
            quality_capped = min(quality, 0.99)
            s_base = quality * (1 + style_count)
            salience = s_base * (1.0 / (1.0 - quality_capped))
        else:
            salience = 0.0

        wc_salience[wc_id] = salience

    # Batch update written_contents
    if wc_prominence:
        await conn.executemany(
            "UPDATE written_contents SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            [
                (wc_prominence[wc_id], wc_salience.get(wc_id, 0.0),
                 world_id, wc_id)
                for wc_id in wc_prominence
            ],
        )
    counts["written_contents_scored"] = len(wc_prominence)
    log.info("  Written work scores: %d works scored", len(wc_prominence))

    # ── Step 5: Tradition prominence (unique authors per tradition) ──
    tradition_rows = await conn.fetch(
        "SELECT af.id, COUNT(DISTINCT wc.author_hf_id) AS unique_authors "
        "FROM art_forms af "
        "LEFT JOIN written_contents wc ON wc.world_id = af.world_id "
        "  AND (wc.details->>'form_id')::INT = af.id "
        "WHERE af.world_id = $1 "
        "GROUP BY af.id",
        world_id,
    )
    tradition_prominence: dict[int, float] = {
        r["id"]: float(r["unique_authors"]) for r in tradition_rows
    }

    # ── Step 6: Tradition salience (avg work salience per tradition) ─
    tradition_salience: dict[int, float] = {}
    trad_sal_rows = await conn.fetch(
        "SELECT (wc.details->>'form_id')::INT AS form_id, "
        "  AVG(wc.salience_score) AS avg_salience "
        "FROM written_contents wc "
        "WHERE wc.world_id = $1 AND wc.details->>'form_id' IS NOT NULL "
        "  AND wc.salience_score > 0 "
        "GROUP BY (wc.details->>'form_id')::INT",
        world_id,
    )
    for r in trad_sal_rows:
        if r["form_id"] is not None:
            tradition_salience[r["form_id"]] = float(r["avg_salience"])

    # Batch update art_forms
    all_traditions = set(tradition_prominence.keys()) | set(tradition_salience.keys())
    if all_traditions:
        await conn.executemany(
            "UPDATE art_forms SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            [
                (tradition_prominence.get(tid, 0.0),
                 tradition_salience.get(tid, 0.0),
                 world_id, tid)
                for tid in all_traditions
            ],
        )
    counts["art_forms_scored"] = len(all_traditions)
    log.info("  Tradition scores: %d traditions scored", len(all_traditions))

    # ── Step 7: HF is_author / is_auteur flags ──────────────────────
    result = await conn.execute(
        "UPDATE historical_figures SET is_author = TRUE "
        "WHERE world_id = $1 AND id IN ("
        "  SELECT DISTINCT author_hf_id FROM written_contents "
        "  WHERE world_id = $1 AND author_hf_id IS NOT NULL"
        ")",
        world_id,
    )
    author_count = int(result.split()[-1]) if result else 0
    log.info("  HF is_author flags: %d", author_count)

    result = await conn.execute(
        "UPDATE historical_figures SET is_auteur = TRUE "
        "WHERE world_id = $1 AND id IN ("
        "  SELECT DISTINCT hf_id_1 FROM history_events "
        "  WHERE world_id = $1 AND event_type IN ("
        "    'dance form created', 'musical form created', 'poetic form created'"
        "  ) AND hf_id_1 IS NOT NULL"
        ")",
        world_id,
    )
    auteur_count = int(result.split()[-1]) if result else 0
    log.info("  HF is_auteur flags: %d", auteur_count)
    counts["hf_authors"] = author_count
    counts["hf_auteurs"] = auteur_count

    # ── Step 8: HF prominence_score += author + auteur bonuses ───────
    # Author bonus: SUM(wc.prominence_score) for all works authored by this HF
    await conn.execute(
        "UPDATE historical_figures hf SET prominence_score = prominence_score + COALESCE(bonus.total, 0) "
        "FROM ("
        "  SELECT wc.author_hf_id AS hf_id, SUM(wc.prominence_score) AS total "
        "  FROM written_contents wc "
        "  WHERE wc.world_id = $1 AND wc.author_hf_id IS NOT NULL "
        "  GROUP BY wc.author_hf_id"
        ") bonus "
        "WHERE hf.world_id = $1 AND hf.id = bonus.hf_id",
        world_id,
    )
    log.info("  HF author prominence bonuses applied")

    # Auteur bonus: COUNT(DISTINCT works in tradition) / 10
    await conn.execute(
        "UPDATE historical_figures hf SET prominence_score = prominence_score + COALESCE(bonus.total, 0) "
        "FROM ("
        "  SELECT he.hf_id_1 AS hf_id, "
        "    SUM(COALESCE(trad_size.cnt, 0)) / 10.0 AS total "
        "  FROM history_events he "
        "  LEFT JOIN LATERAL ("
        "    SELECT COUNT(DISTINCT wc.id) AS cnt "
        "    FROM written_contents wc "
        "    WHERE wc.world_id = $1 "
        "      AND (wc.details->>'form_id')::INT = ("
        "        CASE WHEN he.details->>'form_id' IS NOT NULL "
        "        THEN (he.details->>'form_id')::INT END"
        "      )"
        "  ) trad_size ON TRUE "
        "  WHERE he.world_id = $1 "
        "    AND he.event_type IN ('dance form created', 'musical form created', 'poetic form created') "
        "    AND he.hf_id_1 IS NOT NULL "
        "  GROUP BY he.hf_id_1"
        ") bonus "
        "WHERE hf.world_id = $1 AND hf.id = bonus.hf_id",
        world_id,
    )
    log.info("  HF auteur prominence bonuses applied")

    # ── Step 9: Normalize art scores to 0.0-1.0 ─────────────────────
    normalize_targets = [
        ("written_contents", "prominence_score"),
        ("written_contents", "salience_score"),
        ("art_forms", "prominence_score"),
        ("art_forms", "salience_score"),
    ]
    for table, col in normalize_targets:
        await conn.execute(
            f"UPDATE {table} SET {col} = {col} / NULLIF("
            f"  (SELECT MAX({col}) FROM {table} WHERE world_id = $1), 0) "
            f"WHERE world_id = $1 AND {col} > 0",
            world_id,
        )
    log.info("  Art scores normalized to 0-1")

    return counts


async def _compute_entity_scores(conn, world_id: int) -> int:
    """Compute IDF-weighted prominence and salience for all entities in a world.

    Three signal sources:
    1. Event participation (event_entity_xref) -- weighted by event type rarity
    2. HF membership links (hf_entity_links) -- weighted by link type rarity
    3. Event collection participation -- fixed weights for wars, sieges, etc.

    Prominence = raw event/link counts (unweighted -- how often this entity appears)
    Salience = IDF-weighted counts (rare events score higher -- narrative interest)
    Both normalized to 0-1000 per entity type.
    """
    await conn.execute(
        "UPDATE entities SET prominence_score = 0.0, salience_score = 0.0 "
        "WHERE world_id = $1",
        world_id,
    )

    entity_types = await conn.fetch(
        "SELECT type, COUNT(*) as cnt FROM entities "
        "WHERE world_id = $1 GROUP BY type",
        world_id,
    )

    total_scored = 0
    for row in entity_types:
        etype = row["type"]
        n_entities = row["cnt"]
        if n_entities == 0:
            continue
        scored = await _score_entity_type(conn, world_id, etype, n_entities)
        total_scored += scored
        log.info("    %s: %d entities scored", etype, scored)

    return total_scored


async def _score_entity_type(
    conn, world_id: int, etype: str, n_entities: int
) -> int:
    """Score all entities of a single type using IDF-weighted event rarity."""
    event_idf = await _compute_event_idf(conn, world_id, etype, n_entities)
    link_idf = await _compute_link_idf(conn, world_id, etype, n_entities)

    salience: dict[int, float] = {}
    prominence: dict[int, float] = {}

    # Event participation
    event_rows = await conn.fetch(
        """SELECT eex.entity_id, he.event_type, COUNT(*) as cnt
           FROM event_entity_xref eex
           JOIN history_events he ON eex.event_id = he.id
                AND eex.world_id = he.world_id
           JOIN entities e ON eex.entity_id = e.id
                AND eex.world_id = e.world_id
           WHERE eex.world_id = $1 AND eex.entity_type = 'entity'
                 AND e.type = $2
           GROUP BY eex.entity_id, he.event_type""",
        world_id, etype,
    )
    for er in event_rows:
        eid = er["entity_id"]
        evt = er["event_type"]
        idf = event_idf.get(evt, 0.0)
        floor = EVENT_FLOOR_WEIGHTS.get(evt, 0.0)
        salience[eid] = salience.get(eid, 0.0) + er["cnt"] * max(idf, floor)
        prominence[eid] = prominence.get(eid, 0.0) + er["cnt"]

    # HF link counts
    link_rows = await conn.fetch(
        """SELECT hel.entity_id, hel.link_type, COUNT(*) as cnt
           FROM hf_entity_links hel
           JOIN entities e ON hel.entity_id = e.id
                AND hel.world_id = e.world_id
           WHERE hel.world_id = $1 AND e.type = $2
           GROUP BY hel.entity_id, hel.link_type""",
        world_id, etype,
    )
    for lr in link_rows:
        eid = lr["entity_id"]
        lt = lr["link_type"]
        idf = link_idf.get(lt, 0.0)
        floor = LINK_FLOOR_WEIGHTS.get(lt, 0.0)
        salience[eid] = salience.get(eid, 0.0) + lr["cnt"] * max(idf, floor)
        prominence[eid] = prominence.get(eid, 0.0) + lr["cnt"]

    # Event collection participation
    for role_col, role_weights in [
        ("attacker_entity_id", COLLECTION_WEIGHTS["attacker"]),
        ("defender_entity_id", COLLECTION_WEIGHTS["defender"]),
    ]:
        coll_rows = await conn.fetch(
            f"""SELECT hec.{role_col} as entity_id, hec.type, COUNT(*) as cnt
                FROM history_event_collections hec
                JOIN entities e ON hec.{role_col} = e.id
                     AND hec.world_id = e.world_id
                WHERE hec.world_id = $1 AND e.type = $2
                GROUP BY hec.{role_col}, hec.type""",
            world_id, etype,
        )
        for cr in coll_rows:
            eid = cr["entity_id"]
            weight = role_weights.get(cr["type"], 1.0)
            salience[eid] = salience.get(eid, 0.0) + cr["cnt"] * weight
            prominence[eid] = prominence.get(eid, 0.0) + cr["cnt"]

    if not salience and not prominence:
        return 0

    # Normalize to 0-1000 per entity type
    max_sal = max(salience.values()) if salience else 0
    if max_sal > 0:
        for eid in salience:
            salience[eid] = (salience[eid] / max_sal) * 1000.0

    max_prom = max(prominence.values()) if prominence else 0
    if max_prom > 0:
        for eid in prominence:
            prominence[eid] = (prominence[eid] / max_prom) * 1000.0

    all_eids = set(salience.keys()) | set(prominence.keys())
    await conn.executemany(
        "UPDATE entities SET prominence_score = $1, salience_score = $2 "
        "WHERE world_id = $3 AND id = $4",
        [
            (prominence.get(eid, 0.0), salience.get(eid, 0.0), world_id, eid)
            for eid in all_eids
        ],
    )

    return len(all_eids)


async def _compute_event_idf(
    conn, world_id: int, etype: str, n_entities: int
) -> dict[str, float]:
    """Compute IDF weights for event types within a given entity type."""
    rows = await conn.fetch(
        """SELECT he.event_type, COUNT(DISTINCT eex.entity_id) as entity_count
           FROM event_entity_xref eex
           JOIN history_events he ON eex.event_id = he.id
                AND eex.world_id = he.world_id
           JOIN entities e ON eex.entity_id = e.id AND eex.world_id = e.world_id
           WHERE eex.world_id = $1 AND eex.entity_type = 'entity' AND e.type = $2
           GROUP BY he.event_type""",
        world_id, etype,
    )

    idf: dict[str, float] = {}
    for r in rows:
        n_i = r["entity_count"]
        if n_i > 0 and n_entities > 0:
            idf[r["event_type"]] = math.log2(n_entities / n_i)
    return idf


async def _compute_link_idf(
    conn, world_id: int, etype: str, n_entities: int
) -> dict[str, float]:
    """Compute IDF weights for HF link types within a given entity type."""
    rows = await conn.fetch(
        """SELECT hel.link_type, COUNT(DISTINCT hel.entity_id) as entity_count
           FROM hf_entity_links hel
           JOIN entities e ON hel.entity_id = e.id AND hel.world_id = e.world_id
           WHERE hel.world_id = $1 AND e.type = $2
           GROUP BY hel.link_type""",
        world_id, etype,
    )

    idf: dict[str, float] = {}
    for r in rows:
        n_i = r["entity_count"]
        if n_i > 0 and n_entities > 0:
            idf[r["link_type"]] = math.log2(n_entities / n_i)
    return idf


# ── Geographical Feature Scoring ────────────────────────────────────────────

EVILNESS_FACTOR: dict[str, float] = {
    "evil": 3.0,
    "good": 2.0,
    "neutral": 0.0,
    "unknown": 0.0,
}


def _count_coord_tiles(coords: str | None) -> int:
    """Count the number of coordinate tiles in a pipe-delimited coord string."""
    if not coords:
        return 0
    return len([c for c in coords.split("|") if c.strip()])


def _parse_first_coord(coords_str: str | None) -> tuple[int, int] | None:
    """Extract the first (x, y) coordinate from a pipe-delimited coord string."""
    if not coords_str:
        return None
    first_seg = coords_str.split("|", 1)[0].strip()
    if "," in first_seg:
        parts = first_seg.split(",")
        try:
            return (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            pass
    return None


def _coords_touch_evil_good(
    coords_str: str | None,
    coord_evilness: dict[tuple[int, int], str],
) -> float:
    """Return the max evilness factor for any tile in the coord string."""
    if not coords_str:
        return 0.0
    max_factor = 0.0
    for tile in coords_str.split("|"):
        tile = tile.strip()
        if "," in tile:
            parts = tile.split(",")
            try:
                coord = (int(parts[0]), int(parts[1]))
                ev = coord_evilness.get(coord)
                if ev:
                    max_factor = max(max_factor, EVILNESS_FACTOR.get(ev, 0.0))
            except (ValueError, IndexError):
                pass
    return max_factor


async def _compute_geo_scores(conn, world_id: int) -> dict[str, int]:
    """Compute prominence and salience for geographical features.

    Regions: P = size * evilness_factor, S = evilness_factor / size
    Rivers: P = sqrt(length), S = evilness_factor of starting region
    World Constructions: Roads/tunnels = length-based, Fortifications = fixed high
    """
    counts: dict[str, int] = {}

    # ── Region scoring ──────────────────────────────────────────────
    regions = await conn.fetch(
        "SELECT id, coords, evilness FROM regions WHERE world_id = $1",
        world_id,
    )

    region_updates = []
    coord_evilness: dict[tuple[int, int], str] = {}

    for r in regions:
        evilness = r["evilness"] or "neutral"
        factor = EVILNESS_FACTOR.get(evilness, 0.0)
        coords_str = r["coords"]
        size = _count_coord_tiles(coords_str)

        if factor > 0 and coords_str:
            for tile in coords_str.split("|"):
                tile = tile.strip()
                if "," in tile:
                    parts = tile.split(",", 1)
                    try:
                        coord_evilness[(int(parts[0]), int(parts[1]))] = evilness
                    except ValueError:
                        pass

        if factor > 0 and size > 0:
            prominence = size * factor
            salience = factor / size
            region_updates.append((prominence, salience, world_id, r["id"]))
        else:
            region_updates.append((0.0, 0.0, world_id, r["id"]))

    if region_updates:
        await conn.executemany(
            "UPDATE regions SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            region_updates,
        )
    counts["regions_scored"] = sum(1 for u in region_updates if u[0] > 0)
    log.info("  Region geo scores: %d/%d scored", counts["regions_scored"], len(regions))

    # ── River scoring ───────────────────────────────────────────────
    rivers = await conn.fetch(
        "SELECT id, path FROM rivers WHERE world_id = $1",
        world_id,
    )

    river_updates = []
    for rv in rivers:
        path_str = rv["path"]
        length = _count_coord_tiles(path_str)

        # Prominence = sqrt(length) -- diminishing returns
        prominence = math.sqrt(length) if length > 0 else 0.0

        # Salience = evilness of starting region
        salience = 0.0
        start = _parse_first_coord(path_str)
        if start:
            start_evilness = coord_evilness.get(start, "neutral")
            salience = EVILNESS_FACTOR.get(start_evilness, 0.0)

        river_updates.append((prominence, salience, world_id, rv["id"]))

    if river_updates:
        await conn.executemany(
            "UPDATE rivers SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            river_updates,
        )
    counts["rivers_scored"] = sum(1 for u in river_updates if u[0] > 0 or u[1] > 0)
    log.info("  River geo scores: %d/%d scored", counts["rivers_scored"], len(rivers))

    # ── World Construction scoring ──────────────────────────────────
    wc_rows = await conn.fetch(
        "SELECT id, name, type, coords FROM world_constructions WHERE world_id = $1",
        world_id,
    )

    wc_updates = []
    for wc in wc_rows:
        wc_type = (wc["type"] or "").lower()
        coords_str = wc["coords"]

        if wc_type in ("road", "tunnel"):
            length = _count_coord_tiles(coords_str)
            prominence = float(length) if length > 0 else 0.0
            salience = _coords_touch_evil_good(coords_str, coord_evilness)
        elif wc_type == "fortification":
            # Fixed high values -- rare and significant
            prominence = 100.0
            salience = 100.0
        else:
            # Bridges and other types: no special scoring
            prominence = 0.0
            salience = 0.0

        wc_updates.append({
            "id": wc["id"], "type": wc_type,
            "prominence": prominence, "salience": salience,
        })

    if wc_updates:
        await conn.executemany(
            "UPDATE world_constructions SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            [(wc["prominence"], wc["salience"], world_id, wc["id"]) for wc in wc_updates],
        )
    counts["world_constructions_scored"] = sum(
        1 for wc in wc_updates if wc["prominence"] > 0 or wc["salience"] > 0
    )
    log.info("  World construction geo scores: %d/%d scored",
             counts["world_constructions_scored"], len(wc_rows))

    # ── Normalize all geo + core scores to 0-1 ──────────────────────
    normalize_targets = [
        ("regions", "prominence_score"),
        ("regions", "salience_score"),
        ("rivers", "prominence_score"),
        ("rivers", "salience_score"),
        ("world_constructions", "prominence_score"),
        ("world_constructions", "salience_score"),
        ("sites", "prominence_score"),
        ("sites", "salience_score"),
        ("historical_figures", "prominence_score"),
        ("historical_figures", "salience_score"),
        ("entities", "prominence_score"),
        ("entities", "salience_score"),
        ("artifacts", "prominence_score"),
        ("artifacts", "salience_score"),
    ]
    for table, col in normalize_targets:
        await conn.execute(
            f"UPDATE {table} SET {col} = {col} / NULLIF("
            f"  (SELECT MAX({col}) FROM {table} WHERE world_id = $1), 0) "
            f"WHERE world_id = $1 AND {col} > 0",
            world_id,
        )
    log.info("  All prominence/salience scores normalized to 0-1")

    return counts


async def _compute_structure_scores(conn, world_id: int) -> int:
    """Compute prominence and salience for structures.

    P = type_weight_p + event_count * 2
    S = type_weight_s + has_deity * 30
    """
    structures = await conn.fetch(
        "SELECT id, site_id, type, details FROM structures WHERE world_id = $1",
        world_id,
    )
    if not structures:
        return 0

    # Batch-query event counts per structure
    event_rows = await conn.fetch(
        "SELECT structure_id, COUNT(*) AS cnt FROM history_events "
        "WHERE world_id = $1 AND structure_id IS NOT NULL "
        "GROUP BY structure_id",
        world_id,
    )
    event_counts: dict[int, int] = {r["structure_id"]: r["cnt"] for r in event_rows}

    updates = []
    for s in structures:
        s_type = (s["type"] or "").lower().replace(" ", "_")
        weights = STRUCTURE_WEIGHTS.get(s_type, {"p": 5, "s": 0})

        p_weight = weights["p"]
        s_weight = weights.get("s", 0)

        ec = event_counts.get(s["id"], 0)
        # Deity info is in details JSONB (deity or deity_hf fields)
        details = s["details"] or {}
        has_deity = 1 if details.get("deity") or details.get("deity_hf") else 0

        prominence = p_weight + ec * 2
        salience = s_weight + has_deity * weights.get("s_deity", 30)

        updates.append((float(prominence), float(salience), world_id, s["site_id"], s["id"]))

    if updates:
        await conn.executemany(
            "UPDATE structures SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND site_id = $4 AND id = $5",
            updates,
        )

    log.info("  Structure scores: %d structures scored", len(updates))
    return len(updates)


async def _compute_collection_scores(conn, world_id: int) -> int:
    """Compute prominence and salience for event collections.

    P = duration * type_weight + sub_collection_count * 5 + event_count
    S = death_count * 5 + type_bonus
    """
    collections = await conn.fetch(
        "SELECT id, type, start_year, end_year FROM history_event_collections "
        "WHERE world_id = $1",
        world_id,
    )
    if not collections:
        return 0

    # Batch-query sub-collection counts
    sub_rows = await conn.fetch(
        "SELECT parent_id, COUNT(*) AS cnt FROM history_event_collections "
        "WHERE world_id = $1 AND parent_id IS NOT NULL "
        "GROUP BY parent_id",
        world_id,
    )
    sub_counts: dict[int, int] = {r["parent_id"]: r["cnt"] for r in sub_rows}

    # Batch-query event counts per collection (via collection_events join table)
    event_rows = await conn.fetch(
        "SELECT ce.collection_id, COUNT(*) AS cnt "
        "FROM collection_events ce "
        "WHERE ce.world_id = $1 "
        "GROUP BY ce.collection_id",
        world_id,
    )
    event_counts: dict[int, int] = {r["collection_id"]: r["cnt"] for r in event_rows}

    # Batch-query death counts per collection (via collection_events join)
    death_rows = await conn.fetch(
        "SELECT ce.collection_id, COUNT(*) AS cnt "
        "FROM collection_events ce "
        "JOIN history_events he ON ce.world_id = he.world_id AND ce.event_id = he.id "
        "WHERE ce.world_id = $1 AND he.event_type = 'hf died' "
        "GROUP BY ce.collection_id",
        world_id,
    )
    death_counts: dict[int, int] = {r["collection_id"]: r["cnt"] for r in death_rows}

    updates = []
    for c in collections:
        c_type = (c["type"] or "").lower()
        type_weight = COLLECTION_TYPE_WEIGHTS.get(c_type, 1.0)

        start = c["start_year"] or 0
        end = c["end_year"] or start
        duration = max(end - start, 1)

        sc = sub_counts.get(c["id"], 0)
        ec = event_counts.get(c["id"], 0)
        dc = death_counts.get(c["id"], 0)

        prominence = duration * type_weight + sc * 5 + ec

        # Type bonus for major conflict types
        type_bonus = 20 if c_type in ("war", "insurrection", "persecution") else 0
        salience = dc * 5 + type_bonus

        updates.append((float(prominence), float(salience), world_id, c["id"]))

    if updates:
        await conn.executemany(
            "UPDATE history_event_collections SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            updates,
        )

    log.info("  Collection scores: %d collections scored", len(updates))
    return len(updates)


async def _compute_underground_scores(conn, world_id: int) -> int:
    """Compute prominence and salience for underground regions.

    P = depth_weight + tile_count * 0.5
    S = is_underworld * 50 + is_magma * 30
    """
    ug_regions = await conn.fetch(
        "SELECT id, depth, coords, type FROM underground_regions WHERE world_id = $1",
        world_id,
    )
    if not ug_regions:
        return 0

    updates = []
    for ug in ug_regions:
        depth = ug["depth"] or 1
        depth_weight = {1: 5, 2: 10, 3: 15}.get(depth, 5)
        tile_count = _count_coord_tiles(ug["coords"])

        ug_type = (ug["type"] or "").lower()
        is_underworld = 1 if "underworld" in ug_type else 0
        is_magma = 1 if "magma" in ug_type else 0

        prominence = depth_weight + tile_count * 0.5
        salience = is_underworld * 50 + is_magma * 30

        updates.append((float(prominence), float(salience), world_id, ug["id"]))

    if updates:
        await conn.executemany(
            "UPDATE underground_regions SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            updates,
        )

    log.info("  Underground region scores: %d scored", len(updates))
    return len(updates)


async def _compute_mountain_scores(conn, world_id: int) -> int:
    """Compute prominence and salience for mountain peaks.

    P = (height / 100) + is_volcano * 50
    S = is_volcano * 30
    """
    peaks = await conn.fetch(
        "SELECT id, height, is_volcano FROM mountain_peaks WHERE world_id = $1",
        world_id,
    )
    if not peaks:
        return 0

    updates = []
    for p in peaks:
        height = p["height"] or 0
        is_volcano = 1 if p["is_volcano"] else 0

        prominence = (height / 100.0) + is_volcano * 50
        salience = is_volcano * 30.0

        updates.append((float(prominence), float(salience), world_id, p["id"]))

    if updates:
        await conn.executemany(
            "UPDATE mountain_peaks SET prominence_score = $1, salience_score = $2 "
            "WHERE world_id = $3 AND id = $4",
            updates,
        )

    log.info("  Mountain peak scores: %d scored", len(updates))
    return len(updates)
