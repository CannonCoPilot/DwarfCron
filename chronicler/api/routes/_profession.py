"""Profession and Position derivation for Historical Figures.

Provides two independent derivations:
  - **Profession**: What an HF does day-to-day (potter, farmer, bard, mercenary)
  - **Position**: Formal titled role in an organization (lord, alderperson, sacred virtue)

Profession waterfall priority:
  1. Latest productive job from `change hf job` events (DF's own assignment)
  2. Active position title (from details->'positions' where end_year IS NULL)
  3. Supernatural flags (deity, necromancer; vampire/werebeast deferred)
  4. Entity-type-derived role (performer, merchant, guild member, nomad, soldier)
  3b. Vampire/werebeast (after entity types — they often have cover identities)
  5. Craft/labor/scholar/performance skill (highest IP among eligible skills)
  6. Author/auteur flags (scholar/auteur)
  7. Event reconstruction (artifact_created, written_content_composed, etc.)
  8. Ghost flag
  9. None (blank)

Position derivation:
  - Current position in the *viewing* entity (if entity_id provided)
  - Else: current position in *any* entity, with entity name context

Usage:
    from chronicler.api.routes._profession import (
        derive_profession, derive_position,
        batch_fetch_profession_data, batch_fetch_positions,
    )

    # After main query, batch-fetch all profession data for HF IDs:
    prof_data = await batch_fetch_profession_data(conn, world_id, hf_ids)

    # Then for each HF row:
    profession = derive_profession(row_dict, prof_data.get(hf_id))

    # For position column (optional — separate from profession):
    positions = await batch_fetch_positions(conn, world_id, hf_ids, viewing_entity_id=1525)
    position_label = derive_position(positions.get(hf_id))
"""

# ── Jobs that are "status" rather than productive profession ───────────
# These are excluded from profession derivation; surfaced elsewhere (e.g., Ne'er-do-well tab).
_STATUS_JOBS = frozenset({"standard", "criminal", "snatcher", "thief"})

# ── Job name formatting overrides ──────────────────────────────────────
# Most jobs format well with underscore→space + title case, but some need overrides.
_JOB_DISPLAY_NAMES: dict[str, str] = {
    "animal_caretaker": "Animal Caretaker",
    "animal_dissector": "Animal Dissector",
    "animal_trainer": "Animal Trainer",
    "beast_hunter": "Beast Hunter",
    "bone_carver": "Bone Carver",
    "cheese_maker": "Cheesemaker",
    "fish_cleaner": "Fish Cleaner",
    "fish_dissector": "Fish Dissector",
    "fishery_worker": "Fishery Worker",
    "gem_cutter": "Gem Cutter",
    "gem_setter": "Gem Setter",
    "lye_maker": "Lye Maker",
    "monster_slayer": "Monster Slayer",
    "soap_maker": "Soap Maker",
    "tavern_keeper": "Tavern Keeper",
    "wax_worker": "Wax Worker",
    "wood_burner": "Wood Burner",
}

# ── Skill-to-profession mapping ─────────────────────────────────────────
# Only skills that represent genuine occupations/professions.
# Combat, social, movement, and generic skills are EXCLUDED.
SKILL_PROFESSIONS: dict[str, str] = {
    # Metalworking
    "FORGE_WEAPON": "Weaponsmith",
    "FORGE_ARMOR": "Armorsmith",
    "FORGE_FURNITURE": "Metalsmith",
    "METALCRAFT": "Metalcrafter",
    "SMELT": "Smelter",
    # Stonework
    "MASONRY": "Mason",
    "STONECRAFT": "Stonecrafter",
    "CUT_STONE": "Stone Cutter",
    "CARVE_STONE": "Stone Carver",
    "ENGRAVE_STONE": "Engraver",
    "CUTGEM": "Gem Cutter",
    "ENCRUSTGEM": "Gem Setter",
    # Woodwork
    "CARPENTRY": "Carpenter",
    "WOODCRAFT": "Woodcrafter",
    "BOWYER": "Bowyer",
    "WOODCUTTING": "Woodcutter",
    # Textile / Leather
    "CLOTHESMAKING": "Clothier",
    "WEAVING": "Weaver",
    "SPINNING": "Spinner",
    "LEATHERWORK": "Leatherworker",
    "TANNER": "Tanner",
    "DYE": "Dyer",
    # Food / Drink
    "COOK": "Cook",
    "BREWING": "Brewer",
    "BUTCHER": "Butcher",
    "PROCESSPLANTS": "Thresher",
    "MILLING": "Miller",
    "CHEESEMAKING": "Cheesemaker",
    "PROCESSFISH": "Fish Cleaner",
    "DISSECT_FISH": "Fish Dissector",
    "DISSECT_VERMIN": "Pest Handler",
    # Other crafts
    "BONECARVE": "Bone Carver",
    "GLASSMAKER": "Glassmaker",
    "POTTERY": "Potter",
    "WAX_WORKING": "Wax Worker",
    "BOOKBINDING": "Bookbinder",
    "SOAP_MAKING": "Soap Maker",
    "POTASH_MAKING": "Potash Maker",
    "LYE_MAKING": "Lye Maker",
    "PRESSING": "Presser",
    "GLAZING": "Glazer",
    "EXTRACT_STRAND": "Strand Extractor",
    "WOOD_BURNING": "Charcoal Burner",
    # Agriculture / Nature
    "PLANT": "Farmer",
    "FISH": "Fisher",
    "HERBALISM": "Herbalist",
    "ANIMALCARE": "Animal Caretaker",
    "ANIMALTRAIN": "Animal Trainer",
    "BEEKEEPING": "Beekeeper",
    "SHEARING": "Shearer",
    "MILK": "Milker",
    "GELD": "Gelder",
    # Medical
    "DIAGNOSE": "Diagnostician",
    "SURGERY": "Surgeon",
    "SET_BONE": "Bone Doctor",
    "SUTURE": "Surgeon",
    "DRESS_WOUNDS": "Doctor",
    # Engineering / Labor
    "MECHANICS": "Mechanic",
    "OPERATE_PUMP": "Pump Operator",
    "FLUID_ENGINEER": "Engineer",
    "MINING": "Miner",
    # Scholar / Knowledge
    "WRITING": "Writer",
    "READING": "Scholar",
    "MATHEMATICS": "Scholar",
    "ASTRONOMY": "Astronomer",
    "CHEMISTRY": "Alchemist",
    "GEOGRAPHY": "Geographer",
    "OPTICS_ENGINEER": "Optician",
    "LOGIC": "Philosopher",
    "CRITICAL_THINKING": "Scholar",
    "KNOWLEDGE_ACQUISITION": "Scholar",
    # Performance
    "SING": "Singer",
    "DANCE": "Dancer",
    "POETRY": "Poet",
    "PROSE": "Writer",
    "COMEDY": "Comedian",
    "MAKE_MUSIC": "Musician",
    "PLAY_KEYBOARD_INSTRUMENT": "Musician",
    "PLAY_PERCUSSION_INSTRUMENT": "Musician",
    "PLAY_STRINGED_INSTRUMENT": "Musician",
    "PLAY_WIND_INSTRUMENT": "Musician",
}

# ── Entity type → profession label ──────────────────────────────────────
ENTITY_TYPE_PROFESSIONS: dict[str, str] = {
    "merchantcompany": "Merchant",
    "performancetroupe": "Performer",
    "guild": "Guild Member",
    "militaryunit": "Soldier",
    "nomadicgroup": "Nomad",
    "outcast": "Outcast",
}

# Priority order for entity types (lower = higher priority)
_ENTITY_TYPE_PRIORITY = {
    "merchantcompany": 1,
    "performancetroupe": 2,
    "guild": 3,
    "militaryunit": 4,
    "nomadicgroup": 5,
    "outcast": 6,
}


def _format_job(job: str) -> str:
    """Format a DF job name for display."""
    if job in _JOB_DISPLAY_NAMES:
        return _JOB_DISPLAY_NAMES[job]
    return job.replace("_", " ").title()


# ── Batch fetch functions ──────────────────────────────────────────────


async def batch_fetch_profession_data(
    conn, world_id: int, hf_ids: list[int],
) -> dict[int, dict]:
    """Fetch all profession-relevant data for a batch of HFs.

    Returns {hf_id: {"job": str|None, "entity_types": [str, ...], "events": [str, ...]}}
    Combines: latest productive job, entity type memberships, and event-based reconstruction.
    """
    if not hf_ids:
        return {}

    result: dict[int, dict] = {}

    # 1. Latest productive job from change_hf_job events
    job_rows = await conn.fetch("""
        SELECT DISTINCT ON (hf_id_1) hf_id_1 AS hf_id, details->>'new_job' AS job
        FROM history_events
        WHERE world_id = $1
          AND hf_id_1 = ANY($2::int[])
          AND event_type = 'change hf job'
          AND details->>'new_job' NOT IN ('standard', 'criminal', 'snatcher', 'thief')
        ORDER BY hf_id_1, year DESC, id DESC
    """, world_id, hf_ids)
    for r in job_rows:
        result.setdefault(r["hf_id"], {})["job"] = r["job"]

    # 2. Entity type memberships
    entity_rows = await conn.fetch("""
        SELECT hel.hf_id, e.type AS entity_type
        FROM hf_entity_links hel
        JOIN entities e ON e.world_id = hel.world_id AND e.id = hel.entity_id
        WHERE hel.world_id = $1
          AND hel.hf_id = ANY($2::int[])
          AND hel.link_type = 'member'
          AND e.type IN ('performancetroupe', 'merchantcompany', 'guild',
                         'nomadicgroup', 'militaryunit', 'outcast')
    """, world_id, hf_ids)
    for r in entity_rows:
        d = result.setdefault(r["hf_id"], {})
        d.setdefault("entity_types", []).append(r["entity_type"])

    # 3. Event-based reconstruction for HFs with no job and no qualifying skills
    # Only fetch for HFs not already covered by jobs
    hf_ids_without_jobs = [hid for hid in hf_ids if hid not in result or "job" not in result[hid]]
    if hf_ids_without_jobs:
        event_rows = await conn.fetch("""
            SELECT DISTINCT ON (hf_id_1, event_type) hf_id_1 AS hf_id, event_type
            FROM history_events
            WHERE world_id = $1
              AND hf_id_1 = ANY($2::int[])
              AND event_type IN ('artifact created', 'written content composed',
                                 'knowledge discovered', 'masterpiece created item',
                                 'masterpiece created food', 'masterpiece created engraving',
                                 'masterpiece created arch design', 'masterpiece created dye item')
            ORDER BY hf_id_1, event_type
        """, world_id, hf_ids_without_jobs)
        for r in event_rows:
            d = result.setdefault(r["hf_id"], {})
            d.setdefault("events", []).append(r["event_type"])

    return result


async def batch_fetch_profession_entities(
    conn, world_id: int, hf_ids: list[int],
) -> dict[int, list[str]]:
    """Legacy wrapper — fetch entity type memberships only.

    Kept for backward compatibility. Prefer batch_fetch_profession_data.
    """
    if not hf_ids:
        return {}
    rows = await conn.fetch("""
        SELECT hel.hf_id, e.type AS entity_type
        FROM hf_entity_links hel
        JOIN entities e ON e.world_id = hel.world_id AND e.id = hel.entity_id
        WHERE hel.world_id = $1
          AND hel.hf_id = ANY($2::int[])
          AND hel.link_type = 'member'
          AND e.type IN ('performancetroupe', 'merchantcompany', 'guild',
                         'nomadicgroup', 'militaryunit', 'outcast')
    """, world_id, hf_ids)
    result: dict[int, list[str]] = {}
    for r in rows:
        result.setdefault(r["hf_id"], []).append(r["entity_type"])
    return result


# ── Position batch fetch ───────────────────────────────────────────────


async def batch_fetch_positions(
    conn, world_id: int, hf_ids: list[int],
    viewing_entity_id: int | None = None,
) -> dict[int, list[dict]]:
    """Fetch current positions for a batch of HFs, with entity context.

    Returns {hf_id: [{"position_name": str, "entity_name": str, "entity_type": str,
                       "entity_id": int, "is_viewing_entity": bool}, ...]}

    Positions are sorted: viewing-entity positions first, then by entity type priority.
    """
    if not hf_ids:
        return {}
    rows = await conn.fetch("""
        SELECT hpl.hf_id, ep.name AS position_name,
               e.name AS entity_name, e.type AS entity_type, e.id AS entity_id
        FROM hf_position_links hpl
        JOIN entities e ON e.world_id = hpl.world_id AND e.id = hpl.entity_id
        LEFT JOIN entity_positions ep ON ep.world_id = hpl.world_id
            AND ep.entity_id = hpl.entity_id AND ep.position_id = hpl.position_id
        WHERE hpl.world_id = $1
          AND hpl.hf_id = ANY($2::int[])
          AND hpl.end_year IS NULL
        ORDER BY hpl.hf_id
    """, world_id, hf_ids)

    result: dict[int, list[dict]] = {}
    for r in rows:
        pos_name = r["position_name"] or "Unknown"
        is_viewing = (r["entity_id"] == viewing_entity_id) if viewing_entity_id else False
        result.setdefault(r["hf_id"], []).append({
            "position_name": pos_name,
            "entity_name": r["entity_name"],
            "entity_type": r["entity_type"],
            "entity_id": r["entity_id"],
            "is_viewing_entity": is_viewing,
        })

    # Sort: viewing-entity positions first, then by entity type
    _type_order = {
        "sitegovernment": 0, "civilization": 1, "guild": 2,
        "religion": 3, "militaryunit": 4, "merchantcompany": 5,
        "performancetroupe": 6, "outcast": 7, "nomadicgroup": 8,
    }
    for hf_id, positions in result.items():
        positions.sort(key=lambda p: (
            0 if p["is_viewing_entity"] else 1,
            0 if p["position_name"] != "Unknown" else 1,
            _type_order.get(p["entity_type"], 99),
        ))

    return result


def derive_position(
    positions: list[dict] | None,
    viewing_entity_id: int | None = None,
) -> str | None:
    """Derive a display-ready position label from batch_fetch_positions output.

    If viewing an entity page, prioritizes positions in that entity.
    Appends entity name in parentheses for cross-entity positions.
    Skips orphaned "Unknown" positions and tries the next one.
    """
    if not positions:
        return None

    for pos in positions:
        name = pos["position_name"]
        if name == "Unknown":
            continue

        label = name.title()

        # If position is in a different entity, add context
        if not pos["is_viewing_entity"]:
            entity_name = pos["entity_name"]
            if entity_name:
                label = f"{label} ({entity_name})"

        return label

    return None


# ── Profession derivation ──────────────────────────────────────────────


def derive_profession(
    hf: dict,
    prof_data: dict | None = None,
    entity_types: list[str] | None = None,
) -> str | None:
    """Derive the best profession label for a Historical Figure.

    Args:
        hf: Dict with HF data. Expected keys (all optional):
            - details: JSONB dict (may contain 'positions' array)
            - is_deity, is_necromancer, is_vampire, is_werebeast, is_ghost: bool
            - is_author, is_auteur: bool
            - skills: list of {name: str, total_ip: int}
        prof_data: Dict from batch_fetch_profession_data (keys: job, entity_types, events).
        entity_types: Legacy — list of entity type strings. Used if prof_data not provided.

    Returns:
        Profession string or None.
    """
    _job = None
    _entity_types = entity_types
    _events = None

    if prof_data:
        _job = prof_data.get("job")
        _entity_types = prof_data.get("entity_types", _entity_types)
        _events = prof_data.get("events")

    # ── Priority 1: Latest productive job from DF events ──────────────
    if _job:
        return _format_job(_job)

    # ── Priority 2: Active position title ─────────────────────────────
    details = hf.get("details")
    if details and isinstance(details, dict):
        positions = details.get("positions")
        if positions and isinstance(positions, list):
            for pos in positions:
                if pos.get("end_year") is not None:
                    continue  # historical position
                name = pos.get("position_name", "")
                if name and name != "Unknown":
                    return name.title()

    # ── Priority 3: Supernatural flags ────────────────────────────────
    if hf.get("is_deity"):
        return "Deity"
    if hf.get("is_necromancer"):
        return "Necromancer"

    # ── Priority 4: Entity-type-derived role ──────────────────────────
    if _entity_types:
        best = min(
            _entity_types,
            key=lambda t: _ENTITY_TYPE_PRIORITY.get(t, 99),
        )
        label = ENTITY_TYPE_PROFESSIONS.get(best)
        if label:
            return label

    # ── Priority 3b: Vampire/werebeast (after entity types) ───────────
    if hf.get("is_vampire"):
        return "Vampire"
    if hf.get("is_werebeast"):
        return "Werebeast"

    # ── Priority 5: Craft/labor/scholar/performance skill ─────────────
    skills = hf.get("skills")
    if skills and isinstance(skills, list):
        eligible = [
            s for s in skills
            if s.get("name") in SKILL_PROFESSIONS
        ]
        if eligible:
            top = max(eligible, key=lambda s: s.get("total_ip", 0))
            return SKILL_PROFESSIONS[top["name"]]

    # ── Priority 6: Author/auteur flags ───────────────────────────────
    if hf.get("is_author"):
        return "Scholar"
    if hf.get("is_auteur"):
        return "Auteur"

    # ── Priority 7: Event-based reconstruction ────────────────────────
    if _events:
        # Prioritize more specific events
        event_set = set(_events)
        if event_set & {
            "masterpiece created item", "masterpiece created food",
            "masterpiece created engraving", "masterpiece created arch design",
            "masterpiece created dye item",
        }:
            return "Artisan"
        if "artifact created" in event_set:
            return "Artisan"
        if "written content composed" in event_set:
            return "Writer"
        if "knowledge discovered" in event_set:
            return "Scholar"

    # ── Priority 8: Ghost ─────────────────────────────────────────────
    if hf.get("is_ghost"):
        return "Ghost"

    return None
