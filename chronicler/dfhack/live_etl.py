"""Stage 3: Transform on-disk bridge files → Legends Table UPSERTs.

This module reads structured JSON files written by file_writer.py and
propagates live game data INTO the core CDM (Legends Tables), ensuring
the UI reflects current game state.

Design principle: ALL live data terminates in Legends Tables.
No separate "live tables." No dead ends.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .file_writer import (
    prev_is_comparable, read_dict_section, read_list_section, read_meta,
    read_prev_list_section,
)

log = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────

async def _next_event_id_async(conn, world_id: int) -> int:
    """Get next available history_events ID for live event inserts."""
    row = await conn.fetchval(
        "SELECT COALESCE(MAX(id), 0) FROM history_events WHERE world_id = $1",
        world_id,
    )
    # Live events start at 10M to never collide with legends XML IDs
    return max(row + 1, 10_000_000)


#: What DF means by "no death cause". The bridge resolves the enum to a name
#: where it can and falls back to the raw value, so this arrives as a string
#: from one bridge version and as an integer from another.
_NO_DEATH_CAUSE = {None, "", "-1", -1, "NONE", "none"}


def _normalize_death_cause(value) -> str:
    """The death cause as text, or "unknown".

    ⚠️ `death_cause` is a TEXT column and the sentinel arrives as int -1 from
    some bridge versions. The old guard compared against the string "-1"
    only, so the integer went straight through to asyncpg, which refused the
    whole statement: "invalid input for query argument $5: -1 (expected str,
    got int)". One unrecorded cause then cost every death in that cycle.
    """
    if value in _NO_DEATH_CAUSE:
        return "unknown"
    return str(value)


def _hf_id_from_unit(unit: dict) -> int | None:
    """Extract hist_fig_id from a bridge unit record."""
    hf = unit.get("hist_fig_id") or unit.get("histfig_id") or unit.get("hf_id")
    if hf is not None and int(hf) > 0:
        return int(hf)
    return None


# ── Core Sync Functions ──────────────────────────────────────────────────

async def death_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync deaths from live data into historical_figures.

    When a unit departs (present in _prev but not in current),
    update historical_figures with death_year, death_cause, and alive=FALSE.
    Also update hf_entity_links: member → former_member.

    Returns number of deaths synced.
    """
    # ⚠️ Establish that `_prev` is THIS world's previous cycle before diffing
    # against it. `_prev` outlives the process, so the first cycle after a
    # restart otherwise diffs the new fortress against whichever one was left
    # on disk -- and every unit of that one reads as departed, i.e. a death
    # written for each. Measured live: a session opening on world 2 diffed
    # against world 1's units.
    if not prev_is_comparable(world_id, live_dir):
        log.debug("death_sync: _prev is not this world's previous cycle; "
                  "skipping change detection for one cycle")
        return 0

    current_units = read_list_section("fortress_units", live_dir)
    prev_units = read_prev_list_section("fortress_units", live_dir)
    meta = read_meta(live_dir)
    game_year = meta.get("game_year")
    game_tick = meta.get("game_tick")

    if not prev_units:
        return 0  # No previous cycle to diff against

    current_ids = {u.get("id") for u in current_units if u.get("id")}
    deaths = 0

    for prev_unit in prev_units:
        uid = prev_unit.get("id")
        if uid and uid not in current_ids:
            hf_id = _hf_id_from_unit(prev_unit)
            if not hf_id:
                continue

            # Check if HF already has death recorded
            existing = await conn.fetchval(
                "SELECT death_year FROM historical_figures "
                "WHERE world_id = $1 AND id = $2",
                world_id, hf_id,
            )
            if existing is not None:
                continue  # Already recorded

            death_cause = _normalize_death_cause(prev_unit.get("death_cause"))

            # Update historical_figures
            await conn.execute(
                """UPDATE historical_figures
                   SET death_year = $3,
                       death_seconds = $4,
                       death_cause = $5
                   WHERE world_id = $1 AND id = $2
                     AND death_year IS NULL""",
                world_id, hf_id, game_year, game_tick, death_cause,
            )

            # Flip entity links: member → former_member
            await conn.execute(
                """UPDATE hf_entity_links
                   SET link_type = 'former_member'
                   WHERE world_id = $1 AND hf_id = $2
                     AND link_type = 'member'""",
                world_id, hf_id,
            )

            # Insert death event into history_events
            event_id = await _next_event_id_async(conn, world_id)
            site_id = await conn.fetchval(
                """SELECT s.id FROM sites s
                   JOIN entity_site_links esl ON esl.site_id = s.id
                     AND esl.world_id = s.world_id
                   WHERE s.world_id = $1
                     AND esl.link_type IN ('owner', 'founded')
                   ORDER BY esl.entity_id
                   LIMIT 1""",
                world_id,
            )
            await conn.execute(
                """INSERT INTO history_events
                   (world_id, id, year, seconds, event_type,
                    hf_id_1, site_id, details, source)
                   VALUES ($1, $2, $3, $4, 'hf_died',
                           $5, $6, $7, 'live')
                   ON CONFLICT (world_id, id) DO NOTHING""",
                world_id, event_id, game_year, game_tick,
                hf_id, site_id,
                json.dumps({
                    "cause": death_cause,
                    "unit_id": uid,
                    "unit_name": prev_unit.get("name", ""),
                }),
            )

            log.info("Death synced: HF %d (%s) — %s (Y%s T%s)",
                     hf_id, prev_unit.get("name", "?"),
                     death_cause, game_year, game_tick)
            deaths += 1

    return deaths


async def event_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync live history events into history_events table.

    Reads the history section (recent game events) and inserts
    any new events with source='live'.

    Returns number of events synced.
    """
    events = read_list_section("history", live_dir)
    if not events:
        return 0

    meta = read_meta(live_dir)
    game_year = meta.get("game_year")
    inserted = 0

    for evt in events:
        evt_id = evt.get("id")
        evt_type = evt.get("type") or evt.get("type_name", "unknown")
        year = evt.get("year", game_year)
        seconds = evt.get("seconds") or evt.get("tick")

        if evt_id is None:
            continue

        # Check if event already exists (from legends XML or prior live sync)
        exists = await conn.fetchval(
            "SELECT 1 FROM history_events WHERE world_id = $1 AND id = $2",
            world_id, int(evt_id),
        )
        if exists:
            continue

        # Extract common FK fields from event details
        details = {k: v for k, v in evt.items()
                   if k not in ("id", "year", "seconds", "type", "type_name")}
        hf_id_1 = details.pop("hfid", None) or details.pop("hf_id", None)
        hf_id_2 = details.pop("hfid2", None) or details.pop("hf_id_2", None)
        site_id = details.pop("site_id", None)
        entity_id_1 = details.pop("entity_id", None) or details.pop("civ_id", None)

        await conn.execute(
            """INSERT INTO history_events
               (world_id, id, year, seconds, event_type,
                hf_id_1, hf_id_2, site_id, entity_id_1, details, source)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'live')
               ON CONFLICT (world_id, id) DO NOTHING""",
            world_id, int(evt_id), year, seconds, evt_type,
            int(hf_id_1) if hf_id_1 else None,
            int(hf_id_2) if hf_id_2 else None,
            int(site_id) if site_id else None,
            int(entity_id_1) if entity_id_1 else None,
            json.dumps(details, default=str),
        )

        # Update event_entity_xref for cross-referencing
        if hf_id_1:
            await conn.execute(
                """INSERT INTO event_entity_xref
                   (world_id, event_id, entity_type, entity_id, role)
                   VALUES ($1, $2, 'hf', $3, 'subject')
                   ON CONFLICT DO NOTHING""",
                world_id, int(evt_id), int(hf_id_1),
            )
        if site_id:
            await conn.execute(
                """INSERT INTO event_entity_xref
                   (world_id, event_id, entity_type, entity_id, role)
                   VALUES ($1, $2, 'site', $3, 'location')
                   ON CONFLICT DO NOTHING""",
                world_id, int(evt_id), int(site_id),
            )

        inserted += 1

    if inserted:
        log.info("Event sync: %d live events → history_events", inserted)
    return inserted


async def hf_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync live unit data into historical_figures fields.

    Updates: unit_id, skills, whereabouts, details (personality, stress, job).

    Returns number of HFs updated.
    """
    units = read_list_section("fortress_units", live_dir)
    skills = read_list_section("dwarf_skills", live_dir)
    personality = read_list_section("dwarf_personality", live_dir)

    # Build lookup maps by unit_id
    skill_map: dict = {}
    for s in skills:
        uid = s.get("unit_id")
        if uid:
            skill_map[uid] = s.get("skills") or s

    personality_map: dict = {}
    for p in personality:
        uid = p.get("unit_id")
        if uid:
            personality_map[uid] = p

    updated = 0
    for unit in units:
        hf_id = _hf_id_from_unit(unit)
        if not hf_id:
            continue

        uid = unit.get("id")

        # Build skills JSONB (merge live skills into HF format)
        live_skills = skill_map.get(uid, {})
        if isinstance(live_skills, dict) and "skills" in live_skills:
            live_skills = live_skills["skills"]
        skills_json = json.dumps(live_skills, default=str) if live_skills else None

        # Build whereabouts JSONB
        whereabouts = {
            "pos_x": unit.get("pos_x"),
            "pos_y": unit.get("pos_y"),
            "pos_z": unit.get("pos_z"),
            "site_id": unit.get("site_id"),
        }

        # Build details JSONB merge (personality, stress, job, profession)
        live_details: dict = {}
        if unit.get("stress") is not None:
            live_details["live_stress"] = unit["stress"]
        if unit.get("current_job"):
            live_details["current_job"] = unit["current_job"]
        if unit.get("profession"):
            live_details["live_profession"] = unit["profession"]
        if unit.get("happiness"):
            live_details["happiness"] = unit["happiness"]

        # Merge personality data
        pers = personality_map.get(uid)
        if pers:
            if pers.get("traits"):
                live_details["personality_traits"] = pers["traits"]
            if pers.get("values"):
                live_details["personality_values"] = pers["values"]
            if pers.get("dreams"):
                live_details["personality_dreams"] = pers["dreams"]

        # Update historical_figures
        await conn.execute(
            """UPDATE historical_figures
               SET unit_id = COALESCE(unit_id, $3),
                   skills = COALESCE($4::jsonb, skills),
                   whereabouts = $5::jsonb || COALESCE(whereabouts, '{}'::jsonb),
                   details = COALESCE(details, '{}'::jsonb) || $6::jsonb
               WHERE world_id = $1 AND id = $2""",
            world_id, hf_id,
            uid,
            skills_json,
            json.dumps(whereabouts, default=str),
            json.dumps(live_details, default=str),
        )
        updated += 1

    if updated:
        log.info("HF sync: %d historical_figures updated with live data", updated)
    return updated


async def link_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync squad membership and noble positions into HF link tables.

    squads → hf_squad_links
    noble_positions → hf_position_links

    Returns total links synced.
    """
    units = read_list_section("fortress_units", live_dir)
    squads = read_list_section("squads", live_dir)
    nobles = read_list_section("noble_positions", live_dir)
    meta = read_meta(live_dir)
    game_year = meta.get("game_year")

    # Build unit_id → hf_id map from current units
    uid_to_hf: dict = {}
    for u in units:
        hf = _hf_id_from_unit(u)
        if hf and u.get("id"):
            uid_to_hf[u["id"]] = hf

    synced = 0

    # Squad membership → hf_squad_links
    for sq in squads:
        sq_id = sq.get("id")
        entity_id = sq.get("entity_id")
        positions = sq.get("positions", [])
        if not sq_id or not positions:
            continue

        for pos in positions:
            occupant = pos.get("occupant")
            if occupant is None or occupant < 0:
                continue
            hf_id = uid_to_hf.get(occupant)
            if not hf_id:
                continue

            await conn.execute(
                """INSERT INTO hf_squad_links
                   (world_id, hf_id, squad_id, squad_position, entity_id, start_year)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (world_id, hf_id, squad_id, entity_id)
                   DO UPDATE SET squad_position = EXCLUDED.squad_position""",
                world_id, hf_id, sq_id,
                pos.get("position_index", 0),
                entity_id, game_year,
            )
            synced += 1

    # Noble positions → hf_position_links
    for noble in nobles:
        histfig = noble.get("histfig")
        if not histfig or histfig < 0:
            continue
        position_id = noble.get("position_id")
        entity_id = noble.get("entity_id")
        if position_id is None:
            continue

        # Ensure the entity_positions row exists
        await conn.execute(
            """INSERT INTO entity_positions
               (world_id, entity_id, position_id, name)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (world_id, entity_id, position_id) DO NOTHING""",
            world_id, entity_id or 0, position_id,
            noble.get("code", noble.get("name", "unknown")),
        )

        await conn.execute(
            """INSERT INTO hf_position_links
               (world_id, hf_id, entity_id, position_id, start_year)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (world_id, hf_id, entity_id, position_id, start_year)
               DO NOTHING""",
            world_id, histfig, entity_id or 0, position_id, game_year,
        )
        synced += 1

    if synced:
        log.info("Link sync: %d squad/noble links synced", synced)
    return synced


async def structure_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync buildings and artifacts into structures and artifacts tables.

    buildings → structures (fortress site buildings)
    artifacts → artifacts (holder/location updates)
    fortress_state → sites.details JSONB

    Returns items synced.
    """
    buildings = read_list_section("buildings", live_dir)
    artifacts_data = read_list_section("artifacts", live_dir)
    fortress_state = read_dict_section("fortress_state", live_dir)
    meta = read_meta(live_dir)
    synced = 0

    # Determine fortress site_id from meta or world_info
    world_info = read_dict_section("world_info", live_dir)
    site_id = world_info.get("site_id")
    if not site_id:
        site_id = await conn.fetchval(
            """SELECT s.id FROM sites s
               JOIN entity_site_links esl ON esl.site_id = s.id
                 AND esl.world_id = s.world_id
               WHERE s.world_id = $1
                 AND esl.link_type IN ('owner', 'founded')
               LIMIT 1""",
            world_id,
        )

    # Buildings → structures table
    if buildings and site_id:
        for bld in buildings:
            bld_id = bld.get("id")
            if bld_id is None:
                continue
            await conn.execute(
                """INSERT INTO structures
                   (world_id, site_id, id, name, type, details)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (world_id, site_id, id)
                   DO UPDATE SET details = EXCLUDED.details""",
                world_id, site_id, bld_id,
                bld.get("type_name", bld.get("type", "unknown")),
                bld.get("type_name", "building"),
                json.dumps(bld, default=str),
            )
            synced += 1

    # Artifacts → artifacts table (update holder/location)
    for art in artifacts_data:
        art_id = art.get("id")
        if art_id is None:
            continue
        holder_hf = art.get("holder_hf")
        art_site = art.get("site")

        await conn.execute(
            """INSERT INTO artifacts
               (world_id, id, name, item_type, material,
                holder_hf_id, site_id, details)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
               ON CONFLICT (world_id, id)
               DO UPDATE SET holder_hf_id = COALESCE(EXCLUDED.holder_hf_id, artifacts.holder_hf_id),
                             site_id = COALESCE(EXCLUDED.site_id, artifacts.site_id),
                             details = artifacts.details || EXCLUDED.details""",
            world_id, art_id,
            art.get("name"), art.get("item_type"), art.get("mat_type"),
            int(holder_hf) if holder_hf and holder_hf > 0 else None,
            int(art_site) if art_site and art_site > 0 else None,
            json.dumps(art, default=str),
        )
        synced += 1

    # Fortress state → sites.details JSONB
    if fortress_state and site_id:
        state_json = json.dumps({
            "fortress_state": fortress_state,
            "last_updated_tick": meta.get("game_tick"),
            "last_updated_year": meta.get("game_year"),
        }, default=str)
        await conn.execute(
            """UPDATE sites
               SET details = COALESCE(details, '{}'::jsonb) || $3::jsonb
               WHERE world_id = $1 AND id = $2""",
            world_id, site_id, state_json,
        )
        synced += 1

    if synced:
        log.info("Structure sync: %d buildings/artifacts/state synced", synced)
    return synced


async def entity_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync live entity data and diplomacy into entities and entity_entity_links.

    diplomacy → entity_entity_links
    entities → entities.details JSONB
    belief_systems, cultural_identities → entities.details JSONB
    zones → sites.details JSONB

    Returns items synced.
    """
    diplomacy = read_list_section("diplomacy", live_dir)
    entities = read_list_section("entities", live_dir)
    beliefs = read_list_section("belief_systems", live_dir)
    cultures = read_list_section("cultural_identities", live_dir)
    zones = read_list_section("zones", live_dir)
    synced = 0

    # Determine fortress entity_id
    world_info = read_dict_section("world_info", live_dir)
    fort_entity_id = world_info.get("group_id") or world_info.get("civ_id")

    # Diplomacy → entity_entity_links
    for rel in diplomacy:
        target = rel.get("target_entity_id")
        if not target or not fort_entity_id:
            continue
        link_type = "diplomatic"
        if rel.get("war_related"):
            link_type = "war"
        elif rel.get("diplomacy") == 0:
            link_type = "peace"

        await conn.execute(
            """INSERT INTO entity_entity_links
               (world_id, source_entity_id, target_entity_id, link_type, details)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (world_id, source_entity_id, target_entity_id, link_type)
               DO UPDATE SET details = EXCLUDED.details""",
            world_id, fort_entity_id, target, link_type,
            json.dumps(rel, default=str),
        )
        synced += 1

    # Entities → entities.details (update member counts etc.)
    for ent in entities:
        ent_id = ent.get("id")
        if not ent_id:
            continue
        await conn.execute(
            """UPDATE entities
               SET details = COALESCE(details, '{}'::jsonb) || $3::jsonb
               WHERE world_id = $1 AND id = $2""",
            world_id, ent_id,
            json.dumps({"live_data": ent}, default=str),
        )
        synced += 1

    # Belief systems + cultural identities → entities.details
    if beliefs and fort_entity_id:
        await conn.execute(
            """UPDATE entities
               SET details = COALESCE(details, '{}'::jsonb) || $3::jsonb
               WHERE world_id = $1 AND id = $2""",
            world_id, fort_entity_id,
            json.dumps({"belief_systems": beliefs}, default=str),
        )
        synced += 1

    if cultures and fort_entity_id:
        await conn.execute(
            """UPDATE entities
               SET details = COALESCE(details, '{}'::jsonb) || $3::jsonb
               WHERE world_id = $1 AND id = $2""",
            world_id, fort_entity_id,
            json.dumps({"cultural_identities": cultures}, default=str),
        )
        synced += 1

    # Zones → sites.details JSONB
    if zones:
        site_id = world_info.get("site_id")
        if site_id:
            await conn.execute(
                """UPDATE sites
                   SET details = COALESCE(details, '{}'::jsonb) || $3::jsonb
                   WHERE world_id = $1 AND id = $2""",
                world_id, site_id,
                json.dumps({"zones": zones}, default=str),
            )
            synced += 1

    if synced:
        log.info("Entity sync: %d entity/diplomacy items synced", synced)
    return synced


async def arrival_sync(conn, world_id: int, live_dir: Path) -> int:
    """Detect new arrivals and add hf_entity_links + hf_site_links.

    Returns number of arrivals synced.
    """
    current_units = read_list_section("fortress_units", live_dir)
    prev_units = read_prev_list_section("fortress_units", live_dir)
    meta = read_meta(live_dir)
    game_year = meta.get("game_year")
    game_tick = meta.get("game_tick")
    world_info = read_dict_section("world_info", live_dir)

    if not prev_units:
        return 0

    prev_ids = {u.get("id") for u in prev_units if u.get("id")}
    fort_entity_id = world_info.get("group_id")
    site_id = world_info.get("site_id")
    arrivals = 0

    for unit in current_units:
        uid = unit.get("id")
        if uid and uid not in prev_ids:
            hf_id = _hf_id_from_unit(unit)
            if not hf_id:
                continue

            # Add as entity member (if not already)
            if fort_entity_id:
                await conn.execute(
                    """INSERT INTO hf_entity_links
                       (world_id, hf_id, entity_id, link_type)
                       VALUES ($1, $2, $3, 'member')
                       ON CONFLICT (world_id, hf_id, entity_id, link_type)
                       DO NOTHING""",
                    world_id, hf_id, fort_entity_id,
                )

            # NOTE: We do NOT create hf_site_links here. Legends XML already
            # provides proper site links (resident, occupation, seat of power)
            # for HFs with legitimate relationships. Creating synthetic links
            # pollutes citizen queries on entity detail pages.

            # Insert arrival event
            event_id = await _next_event_id_async(conn, world_id)
            await conn.execute(
                """INSERT INTO history_events
                   (world_id, id, year, seconds, event_type,
                    hf_id_1, site_id, details, source)
                   VALUES ($1, $2, $3, $4, 'add_hf_site_link',
                           $5, $6, $7, 'live')
                   ON CONFLICT (world_id, id) DO NOTHING""",
                world_id, event_id, game_year, game_tick,
                hf_id, site_id,
                json.dumps({
                    "unit_id": uid,
                    "unit_name": unit.get("name", ""),
                    "link_type": "arrival",
                }),
            )
            arrivals += 1

    if arrivals:
        log.info("Arrival sync: %d new arrivals synced", arrivals)
    return arrivals


async def misc_event_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync miscellaneous bridge sections into history_events.

    Converts announcements, incidents, mandates, reactive_events,
    daily_events, and interaction_instances into history_events rows.

    Returns total events synced.
    """
    meta = read_meta(live_dir)
    game_year = meta.get("game_year")
    game_tick = meta.get("game_tick")
    world_info = read_dict_section("world_info", live_dir)
    site_id = world_info.get("site_id")
    inserted = 0

    # Map of section → event_type prefix and source tag
    SECTION_MAP = [
        ("announcements", "announcement", "live_announcement"),
        ("incidents", "incident", "live_incident"),
        ("mandates", "mandate_issued", "live_mandate"),
        ("reactive_events", "reactive_event", "live_reactive"),
        ("daily_events", "scheduled_event", "live_daily"),
        ("interaction_instances", "interaction", "live_interaction"),
    ]

    for section_name, event_type, source_tag in SECTION_MAP:
        items = read_list_section(section_name, live_dir)
        if not items:
            continue

        for item in items:
            # Skip items without meaningful content
            if not item:
                continue

            event_id = await _next_event_id_async(conn, world_id)

            # Extract HF references if present
            hf_id_1 = (item.get("hfid") or item.get("hf_id")
                        or item.get("histfig") or item.get("unit_id"))

            # For announcements, use the text as the event detail
            details = item if isinstance(item, dict) else {"text": str(item)}

            await conn.execute(
                """INSERT INTO history_events
                   (world_id, id, year, seconds, event_type,
                    hf_id_1, site_id, details, source)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                   ON CONFLICT (world_id, id) DO NOTHING""",
                world_id, event_id, game_year, game_tick,
                event_type,
                int(hf_id_1) if hf_id_1 else None,
                site_id,
                json.dumps(details, default=str),
                source_tag,
            )
            inserted += 1

    if inserted:
        log.info("Misc event sync: %d events from 6 sections → history_events",
                 inserted)
    return inserted


async def event_collection_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync event_collections into history_event_collections table.

    Returns number of collections synced.
    """
    collections = read_list_section("event_collections", live_dir)
    if not collections:
        return 0

    synced = 0
    for coll in collections:
        coll_id = coll.get("id")
        if coll_id is None:
            continue

        await conn.execute(
            """INSERT INTO history_event_collections
               (world_id, id, type, name, parent_id,
                start_year, start_seconds, end_year, end_seconds,
                attacker_entity_id, defender_entity_id,
                site_id, region_id, details)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
               ON CONFLICT (world_id, id)
               DO UPDATE SET end_year = COALESCE(EXCLUDED.end_year,
                                                  history_event_collections.end_year),
                             end_seconds = COALESCE(EXCLUDED.end_seconds,
                                                     history_event_collections.end_seconds),
                             details = history_event_collections.details || EXCLUDED.details""",
            world_id, int(coll_id),
            coll.get("type"), coll.get("name"),
            int(coll["parent_id"]) if coll.get("parent_id") else None,
            coll.get("start_year"), coll.get("start_seconds"),
            coll.get("end_year"), coll.get("end_seconds"),
            int(coll["attacker_entity_id"]) if coll.get("attacker_entity_id") else None,
            int(coll["defender_entity_id"]) if coll.get("defender_entity_id") else None,
            int(coll["site_id"]) if coll.get("site_id") else None,
            int(coll["region_id"]) if coll.get("region_id") else None,
            json.dumps(coll, default=str),
        )
        synced += 1

    if synced:
        log.info("Event collection sync: %d → history_event_collections", synced)
    return synced


async def occupation_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync occupations into hf_entity_links with position information.

    Returns number of occupations synced.
    """
    occupations = read_list_section("occupations", live_dir)
    if not occupations:
        return 0

    # Build unit_id → hf_id map from fortress_units
    units = read_list_section("fortress_units", live_dir)
    uid_to_hf: dict = {}
    for u in units:
        hf = _hf_id_from_unit(u)
        if hf and u.get("id"):
            uid_to_hf[u["id"]] = hf

    synced = 0
    for occ in occupations:
        hf_id = occ.get("hf_id") or occ.get("histfig")
        unit_id = occ.get("unit_id")
        entity_id = occ.get("entity_id") or occ.get("site_id")

        # Try to resolve unit_id → hf_id if not directly available
        if not hf_id and unit_id:
            hf_id = uid_to_hf.get(unit_id)
        if not hf_id or not entity_id:
            continue

        position_name = occ.get("type") or occ.get("name") or "occupation"

        await conn.execute(
            """INSERT INTO hf_entity_links
               (world_id, hf_id, entity_id, link_type, position_name)
               VALUES ($1, $2, $3, 'occupation', $4)
               ON CONFLICT (world_id, hf_id, entity_id, link_type)
               DO UPDATE SET position_name = EXCLUDED.position_name""",
            world_id, int(hf_id), int(entity_id), position_name,
        )
        synced += 1

    if synced:
        log.info("Occupation sync: %d → hf_entity_links", synced)
    return synced


async def skill_change_sync(conn, world_id: int, live_dir: Path) -> int:
    """Sync skill_changes into historical_figures.skills JSONB.

    The skill_changes section contains CDC diffs (skill rating increases).
    Merge these into the HF's skills field.

    Returns number of HFs updated.
    """
    changes = read_list_section("skill_changes", live_dir)
    if not changes:
        return 0

    # Build unit_id → hf_id map
    units = read_list_section("fortress_units", live_dir)
    uid_to_hf: dict = {}
    for u in units:
        hf = _hf_id_from_unit(u)
        if hf and u.get("id"):
            uid_to_hf[u["id"]] = hf

    # Group changes by HF
    hf_skills: dict[int, list] = {}
    for change in changes:
        unit_id = change.get("unit_id")
        hf_id = uid_to_hf.get(unit_id) if unit_id else None
        if not hf_id:
            hf_id = change.get("hf_id")
        if not hf_id:
            continue

        if hf_id not in hf_skills:
            hf_skills[hf_id] = []
        hf_skills[hf_id].append({
            "skill": change.get("skill") or change.get("skill_name"),
            "old_rating": change.get("old_rating"),
            "new_rating": change.get("new_rating") or change.get("rating"),
        })

    updated = 0
    for hf_id, skill_list in hf_skills.items():
        # Merge skill changes into existing skills JSONB
        await conn.execute(
            """UPDATE historical_figures
               SET details = COALESCE(details, '{}'::jsonb) ||
                   jsonb_build_object('skill_changes', $3::jsonb)
               WHERE world_id = $1 AND id = $2""",
            world_id, hf_id,
            json.dumps(skill_list, default=str),
        )
        updated += 1

    if updated:
        log.info("Skill change sync: %d HFs updated with skill changes", updated)
    return updated


# ── Orchestrator ─────────────────────────────────────────────────────────

async def run_live_etl(conn, world_id: int, live_dir: Path | None = None) -> dict:
    """Run all live ETL transforms in sequence.

    Reads on-disk files and propagates live data into Legends Tables.
    Returns summary of what was synced.
    """
    if live_dir is None:
        from .file_writer import _live_dir
        live_dir = _live_dir()

    meta = read_meta(live_dir)
    if not meta:
        log.debug("No meta file found — skipping live ETL")
        return {}

    summary: dict = {}

    # Run each sync function, capturing errors individually
    for name, func in [
        ("deaths", death_sync),
        ("arrivals", arrival_sync),
        ("events", event_sync),
        ("hf_fields", hf_sync),
        ("links", link_sync),
        ("structures", structure_sync),
        ("entities", entity_sync),
        ("misc_events", misc_event_sync),
        ("event_collections", event_collection_sync),
        ("occupations", occupation_sync),
        ("skill_changes", skill_change_sync),
    ]:
        try:
            count = await func(conn, world_id, live_dir)
            if count:
                summary[name] = count
        except Exception as e:
            log.warning("Live ETL %s failed: %s", name, e)
            summary[f"{name}_error"] = str(e)

    if summary:
        log.info("Live ETL summary: %s", summary)
    return summary
