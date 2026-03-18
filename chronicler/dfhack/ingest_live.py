"""Live data ETL: transform bridge JSON → CDM tables.

Transforms raw bridge cycle data (unit_summary, dwarf_skills, dwarf_personality,
dwarf_emotions, reactive_events, skill_changes) into proper CDM table rows:
  - units: live unit state (upsert by world_id + id)
  - unit_events: state change detection (CDC stream)
  - fortress_denizens: narrative citizen registry

Uses asyncpg for all DB operations. The connection pool is passed in (not created).
"""

import json
import logging
from datetime import datetime, timezone

import asyncpg

log = logging.getLogger(__name__)

# DF profession enum (stable per DF 53.x) — maps integer ID to display name.
# Source: df-structures/df.profession.type (53.11-r1)
_PROF_NAMES = {
    0: "Miner", 1: "Woodworker", 2: "Carpenter", 3: "Bowyer",
    4: "Woodcutter", 5: "Stoneworker", 6: "Engraver", 7: "Mason",
    8: "Metalsmith", 9: "Weaponsmith", 10: "Armorer", 11: "Blacksmith",
    12: "Metalcrafter", 13: "Jeweler", 14: "Gem Cutter", 15: "Gem Setter",
    16: "Craftsman", 17: "Woodcrafter", 18: "Stonecrafter", 19: "Leatherworker",
    20: "Bone Carver", 21: "Weaver", 22: "Clothier", 23: "Glassmaker",
    24: "Potter", 25: "Glazer", 26: "Wax Worker", 27: "Strand Extractor",
    28: "Fishery Worker", 29: "Fish Dissector", 30: "Fish Cleaner",
    31: "Farmer", 32: "Cheese Maker", 33: "Milker", 34: "Cook",
    35: "Thresher", 36: "Miller", 37: "Butcher", 38: "Tanner",
    39: "Dyer", 40: "Planter", 41: "Herbalist", 42: "Brewer",
    43: "Soap Maker", 44: "Potash Maker", 45: "Lye Maker",
    46: "Wood Burner", 47: "Furnace Operator", 48: "Presser",
    49: "Beekeeper", 50: "Engineer", 51: "Mechanic", 52: "Siege Engineer",
    53: "Siege Operator", 54: "Pump Operator", 55: "Clerk",
    56: "Administrator", 57: "Trader", 58: "Architect",
    59: "Alchemist", 60: "Doctor", 61: "Diagnostician",
    62: "Bone Doctor", 63: "Suturer", 64: "Surgeon",
    65: "Merchant", 66: "Hammerman", 67: "Master Hammerman",
    68: "Spearman", 69: "Master Spearman",
    70: "Crossbowman", 71: "Master Crossbowman",
    72: "Wrestler", 73: "Master Wrestler",
    74: "Axeman", 75: "Master Axeman",
    76: "Swordsman", 77: "Master Swordsman",
    78: "Maceman", 79: "Master Maceman",
    80: "Pikeman", 81: "Master Pikeman",
    82: "Bowman", 83: "Master Bowman",
    84: "Blowgunner", 85: "Master Blowgunner",
    86: "Lasher", 87: "Master Lasher",
    88: "Recruit", 89: "Trained Hunter", 90: "Trained War",
    91: "Master Thief", 92: "Thief", 93: "Peasant",
    94: "Child", 95: "Baby", 96: "Drunk",
    97: "Monster Slayer", 98: "Scout", 99: "Beast Hunter",
    100: "Snatcher", 101: "Mercenary",
    102: "Sage", 103: "Scholar",
    104: "Philosopher", 105: "Mathematician", 106: "Historian",
    107: "Astronomer", 108: "Naturalist", 109: "Chemist",
    110: "Geographer", 111: "Scribe",
    112: "Performer", 113: "Poet", 114: "Bard",
    115: "Dancer", 116: "Entertainer",
    117: "Animal Trainer", 118: "Animal Caretaker",
    119: "Ranger", 120: "Trapper",
    131: "Standard", 132: "No Profession",
}


def profession_name(prof_id: int | None) -> str:
    """Resolve a DF profession integer to a display name."""
    if prof_id is None:
        return "Unknown"
    return _PROF_NAMES.get(prof_id, f"Profession {prof_id}")


# ── Unit Transform ────────────────────────────────────────────────────


def transform_unit(raw: dict, personality: dict | None = None,
                   skills: dict | None = None,
                   emotions: dict | None = None) -> dict:
    """Transform a bridge unit_summary entry into a CDM units row.

    Merges data from unit_summary + dwarf_personality + dwarf_skills +
    dwarf_emotions (matched by unit id).
    """
    details = {}

    # Mood
    mood_val = raw.get("mood")
    if mood_val is not None and mood_val != -1:
        details["mood"] = mood_val

    # Stress
    if raw.get("stress") is not None:
        details["stress"] = raw["stress"]
    if raw.get("longterm_stress") is not None:
        details["longterm_stress"] = raw["longterm_stress"]
    if raw.get("focus") is not None:
        details["focus"] = raw["focus"]
    if raw.get("combat_hardened") is not None:
        details["combat_hardened"] = raw["combat_hardened"]

    # Relationships (HF IDs for family/social)
    if raw.get("relationships"):
        details["relationships"] = raw["relationships"]
    if raw.get("family"):
        details["family"] = raw["family"]

    # Squad assignment
    if raw.get("squad_id") is not None:
        details["squad_id"] = raw["squad_id"]

    # Cultural identity
    if raw.get("cultural_identity") is not None:
        details["cultural_identity"] = raw["cultural_identity"]

    # Enriched personality (from dwarf_personality section)
    if personality:
        p = {}
        if personality.get("traits"):
            p["traits"] = personality["traits"]
        if personality.get("values"):
            p["values"] = personality["values"]
        if personality.get("needs"):
            p["needs"] = personality["needs"]
        if personality.get("dreams"):
            p["dreams"] = personality["dreams"]
        if personality.get("mental_attrs"):
            p["mental_attrs"] = personality["mental_attrs"]
        if p:
            details["personality"] = p

    # Skills (from dwarf_skills section)
    if skills:
        details["skills"] = skills

    # Emotions (from dwarf_emotions section)
    if emotions:
        details["emotions"] = emotions

    return {
        "id": raw["id"],
        "name": raw.get("name", ""),
        "english_name": raw.get("first_name", ""),
        "race": "DWARF",  # bridge only captures player-race units
        "caste": str(raw.get("caste", "")),
        "profession": profession_name(raw.get("profession")),
        "pos_x": raw.get("pos_x"),
        "pos_y": raw.get("pos_y"),
        "pos_z": raw.get("pos_z"),
        "is_alive": raw.get("is_alive", True),
        "hist_fig_id": raw.get("hist_fig_id"),
        "civ_id": None,  # bridge filters by civ already
        "birth_year": raw.get("birth_year"),
        "sex": raw.get("sex"),
        "death_cause": raw.get("death_cause"),
        "details": details,
    }


def _index_by_id(section_data: dict | None) -> dict:
    """Index a bridge section's 'dwarves' list by unit id."""
    if not section_data:
        return {}
    dwarves = section_data.get("dwarves", [])
    return {d["id"]: d for d in dwarves if "id" in d}


# ── Upsert Operations ────────────────────────────────────────────────


async def upsert_units(conn: asyncpg.Connection, units: list[dict],
                       world_id: int) -> int:
    """Upsert transformed units into the CDM units table.

    Returns the number of rows upserted.
    """
    if not units:
        return 0

    count = 0
    for u in units:
        await conn.execute(
            """
            INSERT INTO units (world_id, id, name, english_name, race, caste,
                               profession, pos_x, pos_y, pos_z, is_alive,
                               hist_fig_id, civ_id, birth_year, sex,
                               death_cause, details, last_synced_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                    $12, $13, $14, $15, $16, $17, now())
            ON CONFLICT (world_id, id) DO UPDATE SET
                name = EXCLUDED.name,
                profession = EXCLUDED.profession,
                pos_x = EXCLUDED.pos_x,
                pos_y = EXCLUDED.pos_y,
                pos_z = EXCLUDED.pos_z,
                is_alive = EXCLUDED.is_alive,
                death_cause = COALESCE(EXCLUDED.death_cause, units.death_cause),
                details = COALESCE(units.details, '{}'::jsonb) || EXCLUDED.details,
                last_synced_at = now()
            """,
            world_id, u["id"], u["name"], u["english_name"],
            u["race"], u["caste"], u["profession"],
            u["pos_x"], u["pos_y"], u["pos_z"], u["is_alive"],
            u["hist_fig_id"], u["civ_id"], u["birth_year"], u["sex"],
            u["death_cause"], u["details"],  # dict — asyncpg JSONB codec auto-encodes
        )
        count += 1

    return count


# ── Delta Detection (CDC) ────────────────────────────────────────────


class DeltaDetector:
    """Detects unit state changes between bridge cycles.

    Compares current unit state against the previous snapshot, emitting
    unit_events for significant changes (profession, mood, death, stress
    threshold crossings, skill gains).
    """

    # Stress thresholds (DF internal scale)
    _STRESS_THRESHOLDS = [
        (-100000, "content"),
        (-10000, "fine"),
        (0, "not distressed"),
        (100000, "stressed"),
        (250000, "very stressed"),
        (500000, "haggard"),
    ]

    def __init__(self):
        self._prev: dict[int, dict] = {}  # unit_id → snapshot

    def detect(self, unit_id: int, current: dict) -> list[dict]:
        """Compare current unit state to previous, return change events."""
        prev = self._prev.get(unit_id)
        events = []

        if prev is None:
            # First observation — no delta, just record
            self._prev[unit_id] = current
            return events

        # Profession change
        if prev.get("profession") != current.get("profession"):
            events.append({
                "event_type": "profession_change",
                "old_value": {"profession": prev.get("profession")},
                "new_value": {"profession": current.get("profession")},
            })

        # Death
        if prev.get("is_alive") and not current.get("is_alive"):
            events.append({
                "event_type": "death",
                "old_value": {"is_alive": True},
                "new_value": {
                    "is_alive": False,
                    "death_cause": current.get("death_cause"),
                },
            })

        # Mood change
        prev_mood = prev.get("details", {}).get("mood")
        curr_mood = current.get("details", {}).get("mood")
        if prev_mood != curr_mood and curr_mood is not None:
            events.append({
                "event_type": "mood_change",
                "old_value": {"mood": prev_mood},
                "new_value": {"mood": curr_mood},
            })

        # Stress threshold crossing
        prev_stress = prev.get("details", {}).get("stress", 0)
        curr_stress = current.get("details", {}).get("stress", 0)
        prev_band = self._stress_band(prev_stress)
        curr_band = self._stress_band(curr_stress)
        if prev_band != curr_band:
            events.append({
                "event_type": "stress_change",
                "old_value": {"stress": prev_stress, "band": prev_band},
                "new_value": {"stress": curr_stress, "band": curr_band},
            })

        self._prev[unit_id] = current
        return events

    def _stress_band(self, stress: int) -> str:
        """Map stress value to its threshold band name."""
        band = "traumatized"
        for threshold, name in self._STRESS_THRESHOLDS:
            if stress <= threshold:
                return name
            band = name
        return band


async def insert_unit_events(conn: asyncpg.Connection,
                             events: list[dict],
                             world_id: int,
                             game_year: int | None,
                             game_tick: int | None) -> int:
    """Insert unit change events into unit_events table."""
    if not events:
        return 0

    count = 0
    for ev in events:
        await conn.execute(
            """
            INSERT INTO unit_events (unit_id, world_id, event_type,
                                     old_value, new_value,
                                     game_year, game_tick)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            ev["unit_id"], world_id, ev["event_type"],
            ev.get("old_value"),  # dict — asyncpg JSONB codec auto-encodes
            ev.get("new_value"),  # dict — asyncpg JSONB codec auto-encodes
            game_year, game_tick,
        )
        count += 1
    return count


# ── Reactive Events Processing ────────────────────────────────────────


def process_reactive_events(reactive: dict | None) -> list[dict]:
    """Transform bridge reactive_events section into unit_event records."""
    if not reactive:
        return []

    events = []

    # Deaths with enriched cause
    for death in reactive.get("unit_deaths", []):
        ev = {
            "unit_id": death["unit_id"],
            "event_type": "death",
            "old_value": {"is_alive": True},
            "new_value": {
                "is_alive": False,
                "death_cause": death.get("death_cause"),
                "killer_name": death.get("killer_name"),
                "killer_race": death.get("killer_race"),
                "killer_hf_id": death.get("killer_hf_id"),
            },
        }
        events.append(ev)

    # New units arriving
    for new in reactive.get("new_units", []):
        ev = {
            "unit_id": new["unit_id"],
            "event_type": "arrival",
            "old_value": None,
            "new_value": {
                "name": new.get("name"),
                "race": new.get("race"),
                "profession": new.get("profession"),
                "hist_fig_id": new.get("hist_fig_id"),
            },
        }
        events.append(ev)

    # Invasions
    for inv in reactive.get("invasions", []):
        ev = {
            "unit_id": 0,  # system event, no specific unit
            "event_type": "invasion",
            "old_value": None,
            "new_value": {"invasion_id": inv.get("invasion_id"),
                          "tick": inv.get("tick")},
        }
        events.append(ev)

    # Syndromes
    for syn in reactive.get("syndromes", []):
        ev = {
            "unit_id": syn.get("unit_id", 0),
            "event_type": "syndrome",
            "old_value": None,
            "new_value": {"syndrome_index": syn.get("syndrome_index"),
                          "tick": syn.get("tick")},
        }
        events.append(ev)

    return events


def process_skill_changes(skill_data: dict | None) -> list[dict]:
    """Transform bridge skill_changes section into unit_event records."""
    if not skill_data:
        return []

    events = []
    for dwarf in skill_data.get("dwarves", []):
        uid = dwarf.get("id")
        if not uid:
            continue
        for change in dwarf.get("changes", []):
            events.append({
                "unit_id": uid,
                "event_type": "skill_change",
                "old_value": {"skill": change.get("name"),
                              "old_rating": change.get("old_rating")},
                "new_value": {"skill": change.get("name"),
                              "new_rating": change.get("new_rating"),
                              "experience": change.get("experience")},
            })
    return events


# ── Fortress Denizens Tracking ────────────────────────────────────────


async def sync_fortress_denizens(conn: asyncpg.Connection,
                                 units: list[dict],
                                 world_id: int,
                                 game_year: int | None,
                                 game_tick: int | None) -> dict:
    """Sync fortress_denizens from current unit snapshot.

    - New units not in denizens → INSERT as 'resident'
    - Existing residents now dead → UPDATE to 'deceased'
    - Track last_seen_tick for all observed units

    Returns: {"added": N, "deceased": N, "updated": N}
    """
    stats = {"added": 0, "deceased": 0, "updated": 0}
    if not units:
        return stats

    for u in units:
        unit_id = u["id"]
        hf_id = u.get("hist_fig_id")
        if hf_id and hf_id < 0:
            hf_id = None

        # Check if already tracked
        existing = await conn.fetchrow(
            "SELECT id, status FROM fortress_denizens "
            "WHERE world_id = $1 AND unit_id = $2",
            world_id, unit_id,
        )

        if existing is None:
            # New denizen
            status = "resident" if u.get("is_alive") else "deceased"
            await conn.execute(
                """
                INSERT INTO fortress_denizens
                    (world_id, unit_id, hf_id, name, english_name, race,
                     status, arrival_year, arrival_tick, last_seen_tick, details)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, '{}')
                """,
                world_id, unit_id, hf_id,
                u.get("name", ""), u.get("english_name", ""),
                u.get("race", "DWARF"),
                status,
                game_year, game_tick, game_tick,
            )
            stats["added"] += 1
        else:
            # Update existing
            if existing["status"] == "resident" and not u.get("is_alive"):
                # Died
                await conn.execute(
                    """
                    UPDATE fortress_denizens SET
                        status = 'deceased',
                        departure_year = $1,
                        departure_tick = $2,
                        departure_cause = 'death',
                        last_seen_tick = $2
                    WHERE id = $3
                    """,
                    game_year, game_tick, existing["id"],
                )
                stats["deceased"] += 1
            else:
                # Still alive — update last seen
                await conn.execute(
                    "UPDATE fortress_denizens SET last_seen_tick = $1 WHERE id = $2",
                    game_tick, existing["id"],
                )
                stats["updated"] += 1

    return stats


# ── Main ETL Orchestrator ─────────────────────────────────────────────


async def ingest_bridge_live(conn: asyncpg.Connection,
                             bridge_data: dict,
                             world_id: int,
                             delta_detector: DeltaDetector | None = None,
                             ) -> dict:
    """Full ETL cycle: transform bridge JSON → CDM tables.

    Args:
        conn: Active asyncpg connection (caller manages transaction)
        bridge_data: Full bridge cycle JSON (all sections)
        world_id: Target world ID
        delta_detector: Optional DeltaDetector for CDC (reuse across cycles)

    Returns:
        Summary dict with counts: units_upserted, events_generated,
        denizens_synced, reactive_events, skill_events
    """
    game_year = bridge_data.get("cur_year")
    game_tick = bridge_data.get("cur_year_tick")
    summary = {
        "units_upserted": 0,
        "events_generated": 0,
        "denizens": {"added": 0, "deceased": 0, "updated": 0},
        "reactive_events": 0,
        "skill_events": 0,
    }

    # ── 1. Transform units ──────────────────────────────────────────
    unit_summary = bridge_data.get("unit_summary", {})
    raw_units = unit_summary.get("fortress_units", [])
    if not raw_units:
        log.debug("No fortress units in bridge data")
        return summary

    # Index enrichment sections by unit id
    personality_idx = _index_by_id(bridge_data.get("dwarf_personality"))
    skills_idx = _index_by_id(bridge_data.get("dwarf_skills"))
    emotions_idx = _index_by_id(bridge_data.get("dwarf_emotions"))

    # Transform all units
    transformed = []
    for raw in raw_units:
        uid = raw.get("id")
        if uid is None:
            continue
        unit = transform_unit(
            raw,
            personality=personality_idx.get(uid),
            skills=skills_idx.get(uid, {}).get("skills"),
            emotions=emotions_idx.get(uid, {}).get("emotions"),
        )
        transformed.append(unit)

    # ── 2. Upsert units ────────────────────────────────────────────
    summary["units_upserted"] = await upsert_units(conn, transformed, world_id)

    # ── 3. Delta detection → unit_events ────────────────────────────
    all_events = []
    if delta_detector:
        for u in transformed:
            changes = delta_detector.detect(u["id"], u)
            for ch in changes:
                ch["unit_id"] = u["id"]
            all_events.extend(changes)

    # ── 4. Reactive events (from eventful subscriptions) ────────────
    reactive = bridge_data.get("reactive_events")
    reactive_events = process_reactive_events(reactive)
    all_events.extend(reactive_events)
    summary["reactive_events"] = len(reactive_events)

    # ── 5. Skill change events ──────────────────────────────────────
    skill_data = bridge_data.get("skill_changes")
    skill_events = process_skill_changes(skill_data)
    all_events.extend(skill_events)
    summary["skill_events"] = len(skill_events)

    # ── 6. Insert all events ────────────────────────────────────────
    summary["events_generated"] = await insert_unit_events(
        conn, all_events, world_id, game_year, game_tick,
    )

    # ── 7. Sync fortress denizens ───────────────────────────────────
    summary["denizens"] = await sync_fortress_denizens(
        conn, transformed, world_id, game_year, game_tick,
    )

    log.info(
        "Live ETL: %d units upserted, %d events, denizens +%d/-%d",
        summary["units_upserted"],
        summary["events_generated"],
        summary["denizens"]["added"],
        summary["denizens"]["deceased"],
    )

    return summary
