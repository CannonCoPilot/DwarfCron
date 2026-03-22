"""Stage 3.4.1: Entity text extractors for embedding pipeline.

Each extract_*() function takes an asyncpg.Record and returns a plain-text
string suitable for embedding. Strings are designed to capture the semantic
essence of each entity: who/what it is, what it did, why it matters.

Registry dict BATCH_ENTITY_TYPES maps entity type name to:
  (SQL query, extract function, description)
"""

import json
import logging

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Entity extractors — one per type
# ═══════════════════════════════════════════════════════════════════════

def extract_hf(row) -> str:
    """Extract text for a historical figure."""
    parts = [row["name"] or "(unnamed)"]

    if row["race"]:
        rc = row["race"]
        if row.get("caste"):
            rc += f" {row['caste']}"
        parts.append(rc)

    # Supernatural flags
    flags = []
    for f in ("is_deity", "is_force", "is_vampire", "is_necromancer",
              "is_werebeast", "is_ghost", "is_author", "is_auteur"):
        if row.get(f):
            flags.append(f.replace("is_", ""))
    if flags:
        parts.append(", ".join(flags))

    # Lifespan
    if row.get("birth_year") and row["birth_year"] != -1:
        span = f"born year {row['birth_year']}"
        if row.get("death_year") and row["death_year"] != -1:
            span += f", died year {row['death_year']}"
            if row.get("death_cause"):
                span += f" ({row['death_cause']})"
        parts.append(span)

    if row.get("kill_count") and row["kill_count"] > 0:
        parts.append(f"{row['kill_count']} kills")

    # Spheres (deity domains)
    if row.get("spheres"):
        spheres = row["spheres"]
        if isinstance(spheres, str):
            try:
                spheres = json.loads(spheres)
            except (json.JSONDecodeError, TypeError):
                spheres = None
        if isinstance(spheres, list) and spheres:
            parts.append(f"spheres: {', '.join(str(s) for s in spheres)}")

    # Goals
    if row.get("goals"):
        goals = row["goals"]
        if isinstance(goals, str):
            try:
                goals = json.loads(goals)
            except (json.JSONDecodeError, TypeError):
                goals = None
        if isinstance(goals, list) and goals:
            parts.append(f"goals: {', '.join(str(g) for g in goals[:5])}")

    # Skills (top 5 by rating)
    if row.get("skills"):
        skills = row["skills"]
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except (json.JSONDecodeError, TypeError):
                skills = None
        if isinstance(skills, list) and skills:
            top = sorted(skills, key=lambda s: s.get("rating", 0)
                         if isinstance(s, dict) else 0, reverse=True)[:5]
            skill_strs = []
            for s in top:
                if isinstance(s, dict):
                    skill_strs.append(
                        f"{s.get('name', s.get('skill', '?'))}"
                        f" ({s.get('rating', '?')})")
                else:
                    skill_strs.append(str(s))
            if skill_strs:
                parts.append(f"skills: {', '.join(skill_strs)}")

    # Entity memberships (from joined data)
    if row.get("entity_names"):
        parts.append(f"member of: {row['entity_names']}")

    return " — ".join(parts[:3]) + (". " + ". ".join(parts[3:]) if len(parts) > 3 else "")


def extract_event(row) -> str:
    """Extract text for a history event (only those with narrative_weight >= 10)."""
    parts = [f"Year {row['year']}"]
    etype = row.get("event_type") or "unknown"

    # Resolved names from JOINs
    hf1 = row.get("hf1_name")
    hf2 = row.get("hf2_name")
    site = row.get("site_name")

    if etype == "hf died" and hf1:
        desc = f"{hf1} died"
        if hf2:
            desc += f", slain by {hf2}"
        if site:
            desc += f" at {site}"
    elif "battle" in etype and hf1 and hf2:
        desc = f"{hf1} fought {hf2}"
        if site:
            desc += f" at {site}"
    elif etype == "created site" and hf1 and site:
        desc = f"{hf1} founded {site}"
    elif etype == "artifact created" and hf1:
        desc = f"{hf1} created an artifact"
        if site:
            desc += f" at {site}"
    elif etype == "destroyed site" and site:
        desc = f"{site} was destroyed"
        if hf1:
            desc += f" by {hf1}"
    elif etype == "change hf state" and hf1:
        desc = f"{hf1} changed state"
        if site:
            desc += f" at {site}"
    else:
        desc = etype.replace("_", " ")
        if hf1:
            desc += f" involving {hf1}"
        if hf2:
            desc += f" and {hf2}"
        if site:
            desc += f" at {site}"

    parts.append(desc)

    # Weight and tone from narrative_events
    if row.get("narrative_weight"):
        parts.append(f"weight: {row['narrative_weight']:.0f}")
    if row.get("emotional_tone"):
        parts.append(f"tone: {row['emotional_tone']}")

    return ". ".join(parts)


def extract_site(row) -> str:
    """Extract text for a site."""
    parts = [row["name"] or "(unnamed site)"]
    if row.get("type"):
        parts.append(row["type"].replace("_", " "))
    if row.get("coords"):
        parts.append(f"at {row['coords']}")
    if row.get("owner_name"):
        parts.append(f"owned by {row['owner_name']}")
    if row.get("founded_year"):
        parts.append(f"founded year {row['founded_year']}")
    return " — ".join(parts)


def extract_entity(row) -> str:
    """Extract text for an entity (civilization, site government, etc.)."""
    parts = [row["name"] or "(unnamed entity)"]
    if row.get("type"):
        parts.append(row["type"].replace("_", " "))
    if row.get("race"):
        parts.append(row["race"])
    if row.get("site_count"):
        parts.append(f"{row['site_count']} sites")
    return " — ".join(parts)


def extract_artifact(row) -> str:
    """Extract text for an artifact."""
    parts = [row["name"] or "(unnamed artifact)"]
    if row.get("item_type"):
        parts.append(row["item_type"])
    if row.get("item_subtype"):
        parts[-1] += f" ({row['item_subtype']})"
    if row.get("material"):
        parts.append(f"made of {row['material']}")
    if row.get("creator_name"):
        parts.append(f"created by {row['creator_name']}")
    if row.get("site_name"):
        parts.append(f"at {row['site_name']}")
    return " — ".join(parts)


def extract_written_content(row) -> str:
    """Extract text for written content (books, poems, etc.)."""
    parts = [row.get("title") or "(untitled)"]
    if row.get("form"):
        parts.append(row["form"])
    if row.get("type"):
        parts.append(row["type"])
    if row.get("author_name"):
        parts.append(f"by {row['author_name']}")
    if row.get("styles"):
        styles = row["styles"]
        if isinstance(styles, str):
            try:
                styles = json.loads(styles)
            except (json.JSONDecodeError, TypeError):
                styles = None
        if isinstance(styles, list) and styles:
            parts.append(f"style: {', '.join(str(s) for s in styles[:3])}")
    return " — ".join(parts)


def extract_art_form(row) -> str:
    """Extract text for an art form (can be multi-chunk — long descriptions)."""
    parts = [row["name"] or "(unnamed art form)"]
    if row.get("form_type"):
        parts.append(row["form_type"])
    if row.get("description"):
        parts.append(row["description"])
    return " — ".join(parts)


def extract_unit(row) -> str:
    """Extract text for a live unit (fortress denizen)."""
    parts = [row.get("name") or row.get("english_name") or "(unnamed unit)"]
    if row.get("race"):
        rc = row["race"]
        if row.get("caste"):
            rc += f" {row['caste']}"
        parts.append(rc)
    if row.get("profession"):
        parts.append(row["profession"])

    # Personality from details JSONB
    details = row.get("details")
    if details:
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except (json.JSONDecodeError, TypeError):
                details = {}
        if isinstance(details, dict):
            # Personality traits
            traits = details.get("personality_traits")
            if isinstance(traits, list) and traits:
                parts.append(f"traits: {', '.join(str(t) for t in traits[:5])}")
            # Values/beliefs
            values = details.get("values")
            if isinstance(values, list) and values:
                parts.append(f"values: {', '.join(str(v) for v in values[:5])}")
            # Dreams
            dream = details.get("dream")
            if dream:
                parts.append(f"dream: {dream}")
            # Skills
            skills = details.get("skills")
            if isinstance(skills, list) and skills:
                top = sorted(skills, key=lambda s: s.get("rating", 0)
                             if isinstance(s, dict) else 0, reverse=True)[:5]
                skill_strs = []
                for s in top:
                    if isinstance(s, dict):
                        skill_strs.append(
                            f"{s.get('name', '?')} ({s.get('rating', '?')})")
                if skill_strs:
                    parts.append(f"skills: {', '.join(skill_strs)}")
            # Stress
            stress = details.get("stress")
            if stress is not None:
                parts.append(f"stress: {stress}")

    return " — ".join(parts[:3]) + (". " + ". ".join(parts[3:]) if len(parts) > 3 else "")


def extract_announcement(row) -> str:
    """Extract text for a game announcement/report."""
    parts = []
    if row.get("game_year"):
        parts.append(f"Year {row['game_year']}")
    if row.get("category"):
        parts.append(f"[{row['category']}]")
    if row.get("text"):
        parts.append(row["text"])
    return " ".join(parts)


# ═══════════════════════════════════════════════════════════════════════
# Registry — maps entity type to (SQL, extractor, description)
# ═══════════════════════════════════════════════════════════════════════

BATCH_ENTITY_TYPES = {
    "art_form": {
        "sql": """
            SELECT ROW_NUMBER() OVER (ORDER BY id, form_type) - 1 AS id,
                   name, form_type, description, details
            FROM art_forms WHERE world_id = $1
            ORDER BY id, form_type
            LIMIT $2 OFFSET $3
        """,
        "extract": extract_art_form,
        "desc": "Art forms (dances, musical forms, poetic forms)",
        "count_sql": "SELECT COUNT(*) FROM art_forms WHERE world_id = $1",
    },
    "hf": {
        "sql": """
            SELECT hf.id, hf.name, hf.race, hf.caste,
                   hf.birth_year, hf.death_year, hf.death_cause,
                   hf.kill_count, hf.is_deity, hf.is_force,
                   hf.is_vampire, hf.is_necromancer, hf.is_werebeast,
                   hf.is_ghost, hf.is_author, hf.is_auteur,
                   hf.spheres, hf.goals, hf.skills,
                   string_agg(DISTINCT e.name, ', ') AS entity_names
            FROM historical_figures hf
            LEFT JOIN hf_entity_links hel
                ON hel.world_id = hf.world_id AND hel.hf_id = hf.id
            LEFT JOIN entities e
                ON e.world_id = hel.world_id AND e.id = hel.entity_id
            WHERE hf.world_id = $1
            GROUP BY hf.id, hf.world_id
            ORDER BY hf.id
            LIMIT $2 OFFSET $3
        """,
        "extract": extract_hf,
        "desc": "Historical figures",
        "count_sql": "SELECT COUNT(*) FROM historical_figures WHERE world_id = $1",
    },
    "event": {
        "sql": """
            SELECT he.id, he.event_type, he.year, he.site_id,
                   ne.narrative_weight, ne.emotional_tone,
                   hf1.name AS hf1_name, hf2.name AS hf2_name,
                   s.name AS site_name
            FROM history_events he
            JOIN narrative_events ne
                ON ne.world_id = he.world_id AND ne.event_id = he.id
            LEFT JOIN historical_figures hf1
                ON hf1.world_id = he.world_id
                AND hf1.id = CAST(he.details->>'hf_id' AS INTEGER)
            LEFT JOIN historical_figures hf2
                ON hf2.world_id = he.world_id
                AND hf2.id = CAST(he.details->>'slayer_hf_id' AS INTEGER)
            LEFT JOIN sites s
                ON s.world_id = he.world_id AND s.id = he.site_id
            WHERE he.world_id = $1 AND ne.narrative_weight >= 10
            ORDER BY he.id
            LIMIT $2 OFFSET $3
        """,
        "extract": extract_event,
        "desc": "History events (narrative weight >= 10)",
        "count_sql": """
            SELECT COUNT(*) FROM history_events he
            JOIN narrative_events ne
                ON ne.world_id = he.world_id AND ne.event_id = he.id
            WHERE he.world_id = $1 AND ne.narrative_weight >= 10
        """,
    },
    "site": {
        "sql": """
            SELECT s.id, s.name, s.type, s.coords, s.founded_year,
                   e.name AS owner_name
            FROM sites s
            LEFT JOIN entities e
                ON e.world_id = s.world_id AND e.id = s.owner_entity_id
            WHERE s.world_id = $1
            ORDER BY s.id
            LIMIT $2 OFFSET $3
        """,
        "extract": extract_site,
        "desc": "Sites (fortresses, towns, lairs, etc.)",
        "count_sql": "SELECT COUNT(*) FROM sites WHERE world_id = $1",
    },
    "entity": {
        "sql": """
            SELECT e.id, e.name, e.type, e.race,
                   COUNT(s.id) AS site_count
            FROM entities e
            LEFT JOIN sites s
                ON s.world_id = e.world_id AND s.owner_entity_id = e.id
            WHERE e.world_id = $1
            GROUP BY e.id, e.world_id
            ORDER BY e.id
            LIMIT $2 OFFSET $3
        """,
        "extract": extract_entity,
        "desc": "Entities (civilizations, site governments, religions)",
        "count_sql": "SELECT COUNT(*) FROM entities WHERE world_id = $1",
    },
    "artifact": {
        "sql": """
            SELECT a.id, a.name, a.item_type, a.item_subtype, a.material,
                   hf.name AS creator_name, s.name AS site_name
            FROM artifacts a
            LEFT JOIN historical_figures hf
                ON hf.world_id = a.world_id AND hf.id = a.creator_hf_id
            LEFT JOIN sites s
                ON s.world_id = a.world_id AND s.id = a.site_id
            WHERE a.world_id = $1
            ORDER BY a.id
            LIMIT $2 OFFSET $3
        """,
        "extract": extract_artifact,
        "desc": "Artifacts",
        "count_sql": "SELECT COUNT(*) FROM artifacts WHERE world_id = $1",
    },
    "written_content": {
        "sql": """
            SELECT wc.id, wc.title, wc.form, wc.type, wc.styles,
                   hf.name AS author_name
            FROM written_contents wc
            LEFT JOIN historical_figures hf
                ON hf.world_id = wc.world_id AND hf.id = wc.author_hf_id
            WHERE wc.world_id = $1
            ORDER BY wc.id
            LIMIT $2 OFFSET $3
        """,
        "extract": extract_written_content,
        "desc": "Written content (books, poems, essays)",
        "count_sql": "SELECT COUNT(*) FROM written_contents WHERE world_id = $1",
    },
}

# Live entity types (used by watcher, not batch CLI)
LIVE_ENTITY_TYPES = {
    "unit": {
        "extract": extract_unit,
        "desc": "Live fortress units",
    },
    "announcement": {
        "extract": extract_announcement,
        "desc": "Game announcements and reports",
    },
}
