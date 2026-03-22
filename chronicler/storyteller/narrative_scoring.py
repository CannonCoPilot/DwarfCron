"""Stage 3.6.1: Narrative Event Scoring Engine.

Scores every history_events row by storytelling importance:
  narrative_weight = base_weight × character_importance × rarity_multiplier × irony_bonus
  drama_score = base_drama × escalation_factor

Populates the narrative_events table.
"""

import logging
import math
from collections import Counter

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# Base Weights — intrinsic narrative importance per event type (0-100)
# ═══════════════════════════════════════════════════════════════════════

BASE_WEIGHTS: dict[str, float] = {
    # Death & violence — highest narrative value
    "hf died": 80,
    "creature devoured": 75,
    "hf wounded": 40,
    "hf simple battle event": 30,

    # Political upheaval
    "site taken over": 60,
    "entity overthrown": 65,
    "entity dissolved": 55,
    "new site leader": 35,
    "entity created": 40,
    "create entity position": 25,

    # Creation & achievement
    "artifact created": 50,
    "created site": 45,
    "created structure": 30,
    "created world construction": 30,
    "written content composed": 15,
    "knowledge discovered": 25,

    # Military & conflict
    "attacked site": 70,
    "field battle": 70,
    "destroyed site": 75,
    "razed structure": 55,
    "plundered site": 55,
    "hf attacked site": 60,
    "hf destroyed site": 65,

    # Crime & intrigue
    "hf abducted": 55,
    "item stolen": 30,
    "entity primary criminals": 40,
    "sneak into site": 35,
    "assume identity": 45,
    "entity persecuted": 40,
    "hf convicted": 35,
    "failed intrigue corruption": 25,

    # Social & cultural (lower weight — common)
    "add hf entity link": 5,
    "add hf hf link": 8,
    "remove hf hf link": 10,
    "add hf site link": 5,
    "remove hf site link": 8,
    "remove hf entity link": 8,
    "hfs formed reputation relationship": 10,
    "hf relationship denied": 12,
    "agreement formed": 20,

    # Cultural events
    "ceremony": 10,
    "competition": 12,
    "performance": 8,
    "procession": 8,
    "hf preach": 10,
    "gamble": 5,

    # Economic & trade
    "trade": 10,
    "artifact stored": 8,
    "artifact claim formed": 20,
    "artifact lost": 25,

    # State changes (low individual weight, volume-dominated)
    "change hf state": 3,
    "change hf job": 2,
    "hf recruited unit type for entity": 5,
    "hf travel": 3,
}

# Default for unlisted event types
DEFAULT_BASE_WEIGHT = 5.0

# ═══════════════════════════════════════════════════════════════════════
# Drama Scores — dramatic intensity independent of narrative weight
# ═══════════════════════════════════════════════════════════════════════

BASE_DRAMA: dict[str, float] = {
    "hf died": 90,
    "creature devoured": 85,
    "destroyed site": 80,
    "entity overthrown": 75,
    "hf abducted": 70,
    "attacked site": 70,
    "field battle": 65,
    "hf wounded": 60,
    "hf simple battle event": 50,
    "site taken over": 55,
    "artifact created": 30,
    "entity dissolved": 50,
    "assume identity": 45,
    "entity persecuted": 40,
}

DEFAULT_DRAMA = 10.0

# ═══════════════════════════════════════════════════════════════════════
# Emotional Tone Classification
# ═══════════════════════════════════════════════════════════════════════

TONE_RULES: list[tuple[list[str], str]] = [
    # Tragic
    (["hf died", "creature devoured", "hf wounded", "destroyed site",
      "razed structure", "entity dissolved"], "tragic"),
    # Heroic
    (["field battle", "hf simple battle event", "attacked site",
      "hf attacked site", "hf destroyed site"], "heroic"),
    # Ominous
    (["hf abducted", "entity primary criminals", "sneak into site",
      "assume identity", "entity persecuted", "failed intrigue corruption"], "ominous"),
    # Triumphant
    (["artifact created", "site taken over", "created site",
      "created structure", "knowledge discovered", "entity created"], "triumphant"),
    # Peaceful
    (["ceremony", "competition", "performance", "procession",
      "trade", "agreement formed", "written content composed"], "peaceful"),
    # Ironic — set dynamically by irony detection
]


def classify_tone(event_type: str) -> str:
    """Classify emotional tone from event type."""
    for types, tone in TONE_RULES:
        if event_type in types:
            return tone
    return "neutral"


# ═══════════════════════════════════════════════════════════════════════
# Irony Detection
# ═══════════════════════════════════════════════════════════════════════

async def detect_irony(conn, world_id: int, event_id: int,
                       event_type: str, details: dict | None,
                       hf_cache: dict) -> dict | None:
    """Detect ironic circumstances in an event.

    Returns dict of irony flags or None.
    """
    if not details:
        return None

    flags = {}

    if event_type == "hf died":
        victim_hf_id = details.get("hf_id") or details.get("hf_id_1")
        slayer_hf_id = details.get("slayer_hf_id") or details.get("hf_id_2")

        if victim_hf_id:
            victim = hf_cache.get(victim_hf_id, {})

            # Necromancer killed by undead
            if victim.get("is_necromancer") and details.get("death_cause") in (
                "struck_down", "murdered", "killed"
            ):
                if slayer_hf_id:
                    slayer = hf_cache.get(slayer_hf_id, {})
                    if slayer.get("race", "").lower() in (
                        "zombie", "skeleton", "undead"
                    ):
                        flags["necromancer_killed_by_undead"] = True

            # Legendary warrior dies to mundane cause
            if victim.get("kill_count", 0) >= 10:
                mundane = {"old_age", "infection", "thirst", "hunger",
                           "drowning", "cave_in", "falling"}
                if details.get("death_cause") in mundane:
                    flags["legendary_mundane_death"] = True

            # Diplomat murdered
            if victim.get("is_diplomat"):
                if details.get("death_cause") in ("murdered", "struck_down"):
                    flags["diplomat_murdered"] = True

    if event_type == "artifact created":
        # Artifact created during siege/war
        # (checked by caller via temporal context)
        pass

    return flags if flags else None


# ═══════════════════════════════════════════════════════════════════════
# Main Scoring Functions
# ═══════════════════════════════════════════════════════════════════════

async def _build_hf_cache(conn, world_id: int) -> dict:
    """Load HF metadata needed for scoring (prominence, flags, kill count)."""
    rows = await conn.fetch(
        "SELECT id, prominence_score, salience_score, kill_count, "
        "is_necromancer, is_vampire, is_deity, is_force, is_werebeast, "
        "race, caste "
        "FROM historical_figures WHERE world_id = $1",
        world_id,
    )
    cache = {}
    for r in rows:
        cache[r["id"]] = {
            "prominence": r["prominence_score"] or 0,
            "salience": r["salience_score"] or 0,
            "kill_count": r["kill_count"] or 0,
            "is_necromancer": r["is_necromancer"],
            "is_vampire": r["is_vampire"],
            "is_deity": r["is_deity"],
            "is_force": r["is_force"],
            "is_werebeast": r["is_werebeast"],
            "race": r["race"] or "",
            "caste": r["caste"] or "",
        }
    return cache


async def _compute_rarity(conn, world_id: int) -> dict[str, float]:
    """Compute rarity multiplier per event type via inverse frequency.

    Rarity = log2(total_events / type_count) / log2(total_events)
    Normalized to 0.1 - 3.0 range.
    """
    rows = await conn.fetch(
        "SELECT event_type, COUNT(*) AS n FROM history_events "
        "WHERE world_id = $1 GROUP BY event_type",
        world_id,
    )
    total = sum(r["n"] for r in rows)
    if total == 0:
        return {}

    log_total = math.log2(max(total, 2))
    rarity = {}
    for r in rows:
        if r["n"] > 0:
            raw = math.log2(total / r["n"]) / log_total
            # Clamp to 0.1 - 3.0
            rarity[r["event_type"]] = max(0.1, min(3.0, raw))
    return rarity


def _character_importance(details: dict | None, hf_cache: dict) -> float:
    """Compute character importance bonus from involved HFs.

    Returns additive bonus in range 0.0 - 1.0 (added to base multiplier of 1.0).
    So effective multiplier is 1.0 - 2.0.
    """
    if not details:
        return 0.0

    max_prominence = 0.0
    for key in ("hf_id", "hf_id_1", "hf_id_2", "slayer_hf_id",
                "group_hf_id", "snatcher_hf_id"):
        hf_id = details.get(key)
        if hf_id and hf_id in hf_cache:
            p = hf_cache[hf_id]["prominence"]
            max_prominence = max(max_prominence, p)

    # Prominence is normalized 0-1; return as-is for additive bonus
    return max_prominence


async def score_events(conn, world_id: int, force: bool = False) -> dict:
    """Score all history_events for a world and populate narrative_events.

    Args:
        conn: asyncpg connection
        world_id: target world
        force: if True, rescore all events; if False, skip already-scored

    Returns:
        Summary dict with counts.
    """
    log.info("Narrative scoring: starting for world %d (force=%s)", world_id, force)

    # Clear existing if force
    if force:
        result = await conn.execute(
            "DELETE FROM narrative_events WHERE world_id = $1", world_id)
        log.info("  Cleared existing scores: %s", result)

    # Load HF cache
    hf_cache = await _build_hf_cache(conn, world_id)
    log.info("  HF cache: %d figures loaded", len(hf_cache))

    # Compute rarity multipliers
    rarity = await _compute_rarity(conn, world_id)
    log.info("  Rarity: %d event types computed", len(rarity))

    # Count existing scored events (for skip logic)
    existing_count = 0
    if not force:
        existing_count = await conn.fetchval(
            "SELECT COUNT(*) FROM narrative_events WHERE world_id = $1",
            world_id,
        )

    # Fetch events in batches
    batch_size = 5000
    offset = 0
    total_scored = 0
    total_ironic = 0
    tone_counts: Counter = Counter()

    while True:
        if force:
            events = await conn.fetch(
                "SELECT id, event_type, year, details "
                "FROM history_events WHERE world_id = $1 "
                "ORDER BY id LIMIT $2 OFFSET $3",
                world_id, batch_size, offset,
            )
        else:
            events = await conn.fetch(
                "SELECT he.id, he.event_type, he.year, he.details "
                "FROM history_events he "
                "LEFT JOIN narrative_events ne ON ne.world_id = he.world_id "
                "  AND ne.event_id = he.id "
                "WHERE he.world_id = $1 AND ne.id IS NULL "
                "ORDER BY he.id LIMIT $2 OFFSET $3",
                world_id, batch_size, offset,
            )

        if not events:
            break

        batch = []
        for ev in events:
            event_type = ev["event_type"]
            details = ev["details"] if isinstance(ev["details"], dict) else {}

            # Base weight
            base = BASE_WEIGHTS.get(event_type, DEFAULT_BASE_WEIGHT)

            # Character importance bonus (0.0 - 1.0)
            char_bonus = _character_importance(details, hf_cache)

            # Rarity multiplier (0.1 - 3.0)
            rare = rarity.get(event_type, 1.0)

            # Irony detection
            irony = await detect_irony(
                conn, world_id, ev["id"], event_type, details, hf_cache)
            irony_bonus = 20.0 if irony else 0.0
            if irony:
                total_ironic += 1

            # Final narrative weight (0-100 scale)
            # base_weight provides the floor; char/rarity/irony boost it
            weight = min(100.0,
                         base * (1.0 + char_bonus) * rare + irony_bonus)

            # Drama score
            drama_base = BASE_DRAMA.get(event_type, DEFAULT_DRAMA)
            drama = min(100.0, drama_base * (1.0 + char_bonus * 0.5))

            # Emotional tone
            tone = "ironic" if irony else classify_tone(event_type)
            tone_counts[tone] += 1

            batch.append((
                world_id, ev["id"], weight, drama, irony, tone,
            ))

        # Bulk insert
        await conn.executemany(
            "INSERT INTO narrative_events "
            "(world_id, event_id, narrative_weight, drama_score, "
            " irony_flags, emotional_tone) "
            "VALUES ($1, $2, $3, $4, $5, $6) "
            "ON CONFLICT (world_id, event_id) DO UPDATE SET "
            "  narrative_weight = EXCLUDED.narrative_weight, "
            "  drama_score = EXCLUDED.drama_score, "
            "  irony_flags = EXCLUDED.irony_flags, "
            "  emotional_tone = EXCLUDED.emotional_tone",
            batch,
        )

        total_scored += len(batch)
        offset += batch_size
        if total_scored % 50000 == 0:
            log.info("  Progress: %d events scored...", total_scored)

    log.info("Narrative scoring complete: %d events, %d ironic, tones: %s",
             total_scored, total_ironic, dict(tone_counts))

    return {
        "events_scored": total_scored,
        "ironic_events": total_ironic,
        "tone_distribution": dict(tone_counts),
        "previously_scored": existing_count,
    }
