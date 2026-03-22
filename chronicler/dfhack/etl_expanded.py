"""Expanded ETL: promote bridge sections from lua_probes → CDM tables.

Handles the 15+ bridge sections that were previously only archived to lua_probes.
Works alongside ingest_live.py (which handles units/unit_events/fortress_denizens).

All functions accept an asyncpg Connection (caller manages transactions) and
return counts of rows affected.
"""

import json
import logging
from datetime import datetime, timezone

import asyncpg

log = logging.getLogger(__name__)


def _sanitize_id(val) -> int | None:
    """Convert negative/zero IDs to None for FK-safe storage."""
    if val is None or (isinstance(val, int) and val < 0):
        return None
    return val


# ── Tier 1: Critical ETL Functions ──────────────────────────────────────


async def etl_live_history(conn: asyncpg.Connection, history_data: dict,
                           world_id: int, game_year: int | None,
                           game_tick: int | None) -> int:
    """Promote bridge 'history' section events into history_events table.

    Bridge provides cursor-based new events since last cycle. These are
    inserted with source='live_bridge' to distinguish from legends XML.

    Returns count of events inserted.
    """
    if not history_data:
        return 0

    events = history_data.get("recent_events") or history_data.get("events") or []
    if not events:
        return 0

    count = 0
    for ev in events:
        event_id = ev.get("id")
        if event_id is None:
            continue

        # Check for duplicates (same world_id + event id)
        exists = await conn.fetchval(
            "SELECT 1 FROM history_events WHERE world_id = $1 AND id = $2",
            world_id, event_id,
        )
        if exists:
            continue

        # Bridge uses 'hfid' (no underscore) and numeric type codes
        top_keys = {"id", "year", "seconds", "type",
                    "hfid", "hf_id", "hf_id_2", "site_id",
                    "entity_id", "entity_id_2"}
        details = {k: v for k, v in ev.items() if k not in top_keys}

        await conn.execute(
            """
            INSERT INTO history_events (world_id, id, year, seconds, event_type,
                                         hf_id_1, hf_id_2, site_id,
                                         entity_id_1, entity_id_2,
                                         details, source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'live_bridge')
            ON CONFLICT (world_id, id) DO NOTHING
            """,
            world_id, event_id,
            ev.get("year"), ev.get("seconds"),
            str(ev.get("type", "")),  # numeric code as string
            ev.get("hfid") or ev.get("hf_id"),
            ev.get("hf_id_2"),
            ev.get("site_id"),
            ev.get("entity_id"), ev.get("entity_id_2"),
            details,
        )
        count += 1

    if count:
        log.info("etl_live_history: %d live events → history_events", count)
    return count


async def etl_incidents(conn: asyncpg.Connection, incidents_data: dict,
                        world_id: int) -> int:
    """Process bridge 'incidents' section for death cause enrichment.

    Enriches unit_events death records with killer info from incidents.

    Returns count of enriched events.
    """
    if not incidents_data:
        return 0

    incidents = incidents_data.get("incidents", [])
    if not incidents:
        return 0

    count = 0
    for inc in incidents:
        victim_id = inc.get("victim_unit_id")
        if not victim_id or inc.get("type") != "death":
            continue

        # Update the most recent unresolved death event for this unit
        result = await conn.execute(
            """
            UPDATE unit_events SET
                new_value = COALESCE(new_value, '{}'::jsonb) || $1::jsonb
            WHERE world_id = $2
              AND unit_id = $3
              AND event_type = 'death'
              AND (new_value->>'killer_name') IS NULL
            ORDER BY detected_at DESC
            LIMIT 1
            """,
            {
                "death_cause": inc.get("death_cause"),
                "killer_name": inc.get("criminal_name"),
                "killer_hf_id": inc.get("criminal_hf_id"),
                "conflict_level": inc.get("conflict_level"),
            },
            world_id, victim_id,
        )
        if result and not result.endswith("0"):
            count += 1

    if count:
        log.info("etl_incidents: %d death events enriched", count)
    return count


async def etl_interaction_instances(conn: asyncpg.Connection,
                                     data: dict,
                                     world_id: int) -> int:
    """Upsert interaction_instances (active curses/syndromes).

    Returns count of rows upserted.
    """
    if not data:
        return 0

    instances = data.get("instances", [])
    if not instances:
        return 0

    count = 0
    for inst in instances:
        inst_id = inst.get("id")
        if inst_id is None:
            continue

        details = {k: v for k, v in inst.items()
                   if k not in ("id", "interaction_type", "source_hf_id",
                                "affected_units")}

        await conn.execute(
            """
            INSERT INTO interaction_instances
                (world_id, id, interaction_type, source_hf_id,
                 affected_units, details)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (world_id, id) DO UPDATE SET
                interaction_type = EXCLUDED.interaction_type,
                source_hf_id = EXCLUDED.source_hf_id,
                affected_units = EXCLUDED.affected_units,
                details = EXCLUDED.details
            """,
            world_id, inst_id,
            inst.get("interaction_type"),
            inst.get("source_hf_id"),
            inst.get("affected_units", []),
            details,
        )
        count += 1

    if count:
        log.info("etl_interaction_instances: %d upserted", count)
    return count


# ── Tier 2: Social/Military/Cultural ETL ────────────────────────────────


async def etl_squads(conn: asyncpg.Connection, squads_data: dict,
                     world_id: int) -> int:
    """Upsert military squads from bridge data.

    Returns count of rows upserted.
    """
    if not squads_data:
        return 0

    squads = squads_data.get("squads", [])
    if not squads:
        return 0

    count = 0
    for sq in squads:
        sq_id = sq.get("id")
        if sq_id is None:
            continue

        members = sq.get("members", [])
        details = {}
        if sq.get("orders"):
            details["orders"] = sq["orders"]
        if sq.get("ammunition"):
            details["ammunition"] = sq["ammunition"]

        await conn.execute(
            """
            INSERT INTO squads
                (world_id, id, entity_id, name, name_english, alias,
                 leader_hf_id, position_count, members, details, last_synced_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, now())
            ON CONFLICT (world_id, id) DO UPDATE SET
                name = EXCLUDED.name,
                name_english = EXCLUDED.name_english,
                alias = EXCLUDED.alias,
                leader_hf_id = EXCLUDED.leader_hf_id,
                position_count = EXCLUDED.position_count,
                members = EXCLUDED.members,
                details = EXCLUDED.details,
                last_synced_at = now()
            """,
            world_id, sq_id,
            _sanitize_id(sq.get("entity_id")),
            sq.get("name"),
            sq.get("name_english"),
            sq.get("alias"),
            _sanitize_id(sq.get("leader_hf_id")),
            len(members),
            members,  # JSONB auto-encode
            details,
        )
        count += 1

    if count:
        log.info("etl_squads: %d squads upserted", count)
    return count


async def etl_announcements(conn: asyncpg.Connection, ann_data: dict,
                            world_id: int, game_year: int | None,
                            game_tick: int | None) -> int:
    """Promote bridge 'announcements' to game_reports table.

    Returns count of reports inserted.
    """
    if not ann_data:
        return 0

    reports = ann_data.get("recent") or ann_data.get("announcements") or []
    if not reports:
        return 0

    count = 0
    for rpt in reports:
        text = rpt.get("text", "").strip()
        report_id = rpt.get("id")
        if not text or report_id is None:
            continue

        await conn.execute(
            """
            INSERT INTO game_reports
                (world_id, report_id, report_type, text, game_year, game_tick,
                 is_announcement)
            VALUES ($1, $2, $3, $4, $5, $6, true)
            ON CONFLICT (world_id, report_id) DO NOTHING
            """,
            world_id, report_id, rpt.get("type"),
            text, rpt.get("year") or game_year, rpt.get("time") or game_tick,
        )
        count += 1

    if count:
        log.info("etl_announcements: %d reports inserted", count)
    return count


async def etl_artifacts_live(conn: asyncpg.Connection, artifacts_data: dict,
                             world_id: int) -> int:
    """Update artifact locations/holders from live bridge data.

    Returns count of artifacts updated.
    """
    if not artifacts_data:
        return 0

    artifacts = artifacts_data.get("artifacts", [])
    if not artifacts:
        return 0

    count = 0
    for art in artifacts:
        art_id = art.get("id")
        if art_id is None:
            continue

        # Update holder/site if changed
        result = await conn.execute(
            """
            UPDATE artifacts SET
                holder_hf_id = COALESCE($3, holder_hf_id),
                site_id = COALESCE($4, site_id),
                details = COALESCE(details, '{}'::jsonb) || $5::jsonb
            WHERE world_id = $1 AND id = $2
            """,
            world_id, art_id,
            art.get("holder_hf_id"),
            art.get("site_id"),
            {"live_name": art.get("name"), "last_seen_tick": art.get("tick")},
        )
        if result and not result.endswith("0"):
            count += 1

    if count:
        log.info("etl_artifacts_live: %d artifacts updated", count)
    return count


async def etl_event_collections(conn: asyncpg.Connection, ec_data: dict,
                                world_id: int) -> int:
    """Update active event collections (wars/battles/sieges) from bridge.

    Returns count of collections updated.
    """
    if not ec_data:
        return 0

    collections = ec_data.get("collections", [])
    if not collections:
        return 0

    count = 0
    for coll in collections:
        coll_id = coll.get("id")
        if coll_id is None:
            continue

        # Update end_year if the collection is still active
        result = await conn.execute(
            """
            UPDATE history_event_collections SET
                end_year = COALESCE($3, end_year),
                details = COALESCE(details, '{}'::jsonb) || $4::jsonb
            WHERE world_id = $1 AND id = $2
            """,
            world_id, coll_id,
            coll.get("end_year"),
            {"live_update": True, "attacker_civ": coll.get("attacker_civ_id"),
             "defender_civ": coll.get("defender_civ_id")},
        )
        if result and not result.endswith("0"):
            count += 1

    if count:
        log.info("etl_event_collections: %d collections updated", count)
    return count


async def etl_entities_live(conn: asyncpg.Connection, entities_data: dict,
                            world_id: int) -> int:
    """Update entities with live state from bridge.

    Returns count of entities updated.
    """
    if not entities_data:
        return 0

    entities = entities_data.get("entities", [])
    if not entities:
        return 0

    count = 0
    for ent in entities:
        ent_id = ent.get("id")
        if ent_id is None:
            continue

        live_details = {k: v for k, v in ent.items()
                        if k not in ("id", "name", "type")}
        if not live_details:
            continue

        result = await conn.execute(
            """
            UPDATE entities SET
                details = COALESCE(details, '{}'::jsonb) || $3::jsonb
            WHERE world_id = $1 AND id = $2
            """,
            world_id, ent_id, live_details,
        )
        if result and not result.endswith("0"):
            count += 1

    if count:
        log.info("etl_entities_live: %d entities updated", count)
    return count


async def etl_diplomacy(conn: asyncpg.Connection, diplo_data: dict,
                        world_id: int) -> int:
    """Update entity_entity_links with diplomatic relations from bridge.

    Returns count of links upserted.
    """
    if not diplo_data:
        return 0

    relations = diplo_data.get("relations", [])
    if not relations:
        return 0

    count = 0
    for rel in relations:
        source_id = rel.get("source_entity_id")
        target_id = rel.get("target_entity_id")
        if source_id is None or target_id is None:
            continue

        diplo_details = {k: v for k, v in rel.items()
                         if k not in ("source_entity_id", "target_entity_id",
                                      "link_type", "strength")}

        await conn.execute(
            """
            INSERT INTO entity_entity_links
                (world_id, source_entity_id, target_entity_id,
                 link_type, strength, details)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (world_id, source_entity_id, target_entity_id, link_type)
            DO UPDATE SET
                strength = EXCLUDED.strength,
                details = COALESCE(entity_entity_links.details, '{}'::jsonb)
                          || EXCLUDED.details
            """,
            world_id, source_id, target_id,
            rel.get("link_type", "DIPLOMACY"),
            rel.get("strength"),
            diplo_details,
        )
        count += 1

    if count:
        log.info("etl_diplomacy: %d diplomatic links upserted", count)
    return count


async def etl_fortress_state(conn: asyncpg.Connection, state_data: dict,
                             world_id: int, game_year: int | None,
                             game_tick: int | None) -> int:
    """Insert a fortress state snapshot (append-only).

    Should be called once per season, not every cycle.

    Returns 1 if inserted, 0 if skipped.
    """
    if not state_data:
        return 0

    site_id = state_data.get("site_id")
    if site_id is None:
        return 0

    # Top-level columns extracted; everything else goes into details JSONB
    top_keys = {"site_id", "fortress_age", "fortress_rank", "population",
                "king_arrived", "infiltrators", "invasion_count",
                "wealth_total", "wealth_imported", "wealth_exported"}
    details = {k: v for k, v in state_data.items() if k not in top_keys}

    await conn.execute(
        """
        INSERT INTO fortress_state
            (world_id, site_id, fortress_age, fortress_rank, population,
             king_arrived, infiltrators, invasion_count,
             wealth_created, wealth_imported, wealth_exported,
             game_year, game_tick, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """,
        world_id, site_id,
        state_data.get("fortress_age"),
        state_data.get("fortress_rank"),
        state_data.get("population"),
        state_data.get("king_arrived", False),
        state_data.get("infiltrators", []),
        state_data.get("invasion_count", 0),
        state_data.get("wealth_total"),       # DF 53.10: 'total' not 'created'
        state_data.get("wealth_imported"),
        state_data.get("wealth_exported"),
        game_year, game_tick,
        details,
    )
    log.info("etl_fortress_state: snapshot captured (year=%s, rank=%s, pop=%s)",
             game_year, state_data.get("fortress_rank"),
             state_data.get("population"))
    return 1


# ── Tier 2: Memory-Only Structure ETL ──────────────────────────────────


async def etl_belief_systems(conn: asyncpg.Connection, data: dict,
                             world_id: int) -> int:
    """Upsert belief systems from bridge extraction.

    Returns count of rows upserted.
    """
    if not data:
        return 0

    systems = data.get("systems", [])
    if not systems:
        return 0

    count = 0
    for bs in systems:
        bs_id = bs.get("id")
        if bs_id is None:
            continue

        details = {k: v for k, v in bs.items()
                   if k not in ("id", "deities", "worship_levels",
                                "cultural_values")}

        await conn.execute(
            """
            INSERT INTO belief_systems
                (world_id, id, deities, worship_levels, cultural_values, details)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (world_id, id) DO UPDATE SET
                deities = EXCLUDED.deities,
                worship_levels = EXCLUDED.worship_levels,
                cultural_values = EXCLUDED.cultural_values,
                details = EXCLUDED.details
            """,
            world_id, bs_id,
            bs.get("deities", []),
            bs.get("worship_levels", []),
            bs.get("cultural_values", {}),
            details,
        )
        count += 1

    if count:
        log.info("etl_belief_systems: %d upserted", count)
    return count


async def etl_cultural_identities(conn: asyncpg.Connection, data: dict,
                                   world_id: int) -> int:
    """Upsert cultural identities from bridge extraction.

    Returns count of rows upserted.
    """
    if not data:
        return 0

    identities = data.get("identities", [])
    if not identities:
        return 0

    count = 0
    for ci in identities:
        ci_id = ci.get("id")
        if ci_id is None:
            continue

        details = {k: v for k, v in ci.items()
                   if k not in ("id", "site_id", "civ_id",
                                "ethics", "cultural_values")}

        await conn.execute(
            """
            INSERT INTO cultural_identities
                (world_id, id, site_id, civ_id, ethics, cultural_values, details)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (world_id, id) DO UPDATE SET
                site_id = EXCLUDED.site_id,
                civ_id = EXCLUDED.civ_id,
                ethics = EXCLUDED.ethics,
                cultural_values = EXCLUDED.cultural_values,
                details = EXCLUDED.details
            """,
            world_id, ci_id,
            _sanitize_id(ci.get("site_id")),
            _sanitize_id(ci.get("civ_id")),
            ci.get("ethics", {}),
            ci.get("cultural_values", {}),
            details,
        )
        count += 1

    if count:
        log.info("etl_cultural_identities: %d upserted", count)
    return count


async def etl_occupations(conn: asyncpg.Connection, data: dict,
                          world_id: int) -> int:
    """Upsert occupations from bridge extraction.

    Returns count of rows upserted.
    """
    if not data:
        return 0

    occupations = data.get("occupations", [])
    if not occupations:
        return 0

    count = 0
    for occ in occupations:
        occ_id = occ.get("id")
        if occ_id is None:
            continue

        details = {k: v for k, v in occ.items()
                   if k not in ("id", "occupation_type", "hf_id", "unit_id",
                                "site_id", "location_id", "entity_id")}

        await conn.execute(
            """
            INSERT INTO occupations
                (world_id, id, occupation_type, hf_id, unit_id,
                 site_id, location_id, entity_id, details)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (world_id, id) DO UPDATE SET
                occupation_type = EXCLUDED.occupation_type,
                hf_id = EXCLUDED.hf_id,
                unit_id = EXCLUDED.unit_id,
                site_id = EXCLUDED.site_id,
                location_id = EXCLUDED.location_id,
                entity_id = EXCLUDED.entity_id,
                details = EXCLUDED.details
            """,
            world_id, occ_id,
            occ.get("occupation_type", "unknown"),
            _sanitize_id(occ.get("hf_id")),
            _sanitize_id(occ.get("unit_id")),
            _sanitize_id(occ.get("site_id")),
            _sanitize_id(occ.get("location_id")),
            _sanitize_id(occ.get("entity_id")),
            details,
        )
        count += 1

    if count:
        log.info("etl_occupations: %d upserted", count)
    return count


async def etl_daily_events(conn: asyncpg.Connection, data: dict,
                           world_id: int, game_year: int | None,
                           game_tick: int | None) -> int:
    """Transform bridge daily_events into unit_events.

    Bridge sends scheduled events as {day_index: [nemesis_ids]} dicts.
    Nemesis IDs reference nemesis_record, not unit/HF IDs directly.
    We store them as-is with source metadata; resolution to HF happens later.

    Returns count of events inserted.
    """
    if not data:
        return 0

    # Replace-all strategy: delete previous scheduled events, then re-insert.
    # Scheduled events are a rolling window that shifts as game time advances,
    # so stale projections must be removed each cycle.
    await conn.execute(
        "DELETE FROM unit_events WHERE world_id = $1 AND event_type LIKE 'scheduled_%'",
        world_id,
    )

    count = 0
    event_mappings = [
        ("births", "scheduled_birth"),
        ("deaths", "scheduled_death"),
        ("pregnancies", "scheduled_pregnancy"),
        ("grown_up", "scheduled_grown_up"),
    ]

    day_index = data.get("day_index")

    for key, event_type in event_mappings:
        day_dict = data.get(key, {})
        if not isinstance(day_dict, dict):
            continue
        for day_idx, nemesis_ids in day_dict.items():
            if not isinstance(nemesis_ids, list):
                continue
            for nid in nemesis_ids:
                if not nid or nid < 0:
                    continue
                await conn.execute(
                    """
                    INSERT INTO unit_events
                        (unit_id, world_id, event_type, new_value,
                         game_year, game_tick)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    nid, world_id, event_type,
                    {"source": "daily_events", "day_index": int(day_idx),
                     "current_day": day_index, "nemesis_id": nid},
                    game_year, game_tick,
                )
                count += 1

    # Handle marriages — pair marriage_1 and marriage_2 nemesis IDs
    m1 = data.get("marriages_1", {})
    m2 = data.get("marriages_2", {})
    if isinstance(m1, dict) and isinstance(m2, dict):
        for day_idx in m1:
            ids1 = m1.get(day_idx, [])
            ids2 = m2.get(day_idx, [])
            for i, nid in enumerate(ids1):
                partner = ids2[i] if i < len(ids2) else None
                if not nid or nid < 0:
                    continue
                await conn.execute(
                    """
                    INSERT INTO unit_events
                        (unit_id, world_id, event_type, new_value,
                         game_year, game_tick)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    nid, world_id, "scheduled_marriage",
                    {"source": "daily_events", "day_index": int(day_idx),
                     "current_day": day_index,
                     "nemesis_id": nid, "partner_nemesis_id": partner},
                    game_year, game_tick,
                )
                count += 1

    if count:
        log.info("etl_daily_events: %d scheduled events (replace-all)", count)
    return count


# ── HF ↔ Unit Bidirectional Link ───────────────────────────────────────


async def etl_hf_unit_links(conn: asyncpg.Connection, bridge_data: dict,
                             world_id: int) -> int:
    """Populate historical_figures.unit_id from bridge unit hist_fig_id.

    Each fortress unit has a hist_fig_id linking it to a historical figure.
    This enables bidirectional navigation between HF detail pages and live
    unit data.

    Returns count of HFs updated.
    """
    us = bridge_data.get("unit_summary", {})
    fortress_units = us.get("fortress_units", [])
    if not fortress_units:
        return 0

    count = 0
    for u in fortress_units:
        hf_id = u.get("hist_fig_id")
        unit_id = u.get("id")
        if not hf_id or hf_id < 0 or not unit_id:
            continue
        result = await conn.execute(
            """UPDATE historical_figures
               SET unit_id = $3
               WHERE world_id = $1 AND id = $2 AND (unit_id IS NULL OR unit_id != $3)""",
            world_id, hf_id, unit_id,
        )
        if result and result.endswith("1"):
            count += 1

    if count:
        log.info("etl_hf_unit_links: %d HFs linked to units", count)
    return count


# ── Reconciliation ──────────────────────────────────────────────────────


async def reconcile_events(conn: asyncpg.Connection, world_id: int) -> int:
    """Match unit_events deaths to history_events deaths.

    Run after legends XML import to link live CDC events to curated history.

    Returns count of events reconciled.
    """
    result = await conn.execute(
        """
        UPDATE unit_events ue
        SET reconciled_event_id = he.id,
            reconciled_at = now()
        FROM history_events he
        JOIN units u ON u.world_id = ue.world_id AND u.id = ue.unit_id
        WHERE ue.event_type = 'death'
          AND ue.reconciled_event_id IS NULL
          AND ue.world_id = $1
          AND he.world_id = $1
          AND he.event_type = 'HF_DIED'
          AND he.hf_id_1 = u.hist_fig_id
          AND he.year = ue.game_year
        """,
        world_id,
    )
    count = int(result.split()[-1]) if result else 0
    if count:
        log.info("reconcile_events: %d deaths matched to history_events", count)
    return count


# ── Noble Position ETL ───────────────────────────────────────────────────


async def etl_noble_positions(
    conn: asyncpg.Connection, positions_data: dict | None,
    world_id: int, game_year: int | None,
) -> int:
    """Sync position assignments from bridge data (ground truth for 'present').

    Compares bridge snapshot against DB active rows (end_year IS NULL) to detect:
    - New appointments  → INSERT with start_year = game_year
    - Removals          → SET end_year = game_year on stale DB rows
    - Reassignments     → end old holder + insert new holder
    - Backfills         → NULL start_year rows get game_year

    Returns count of rows changed (inserts + updates + removals).
    """
    if not positions_data:
        return 0

    count = 0
    for label in ('fortress_entity', 'site_government'):
        section = positions_data.get(label)
        if not section:
            continue
        entity_id = section.get('entity_id')
        if not entity_id:
            continue

        # ── Build bridge truth set: {(position_id, hf_id)} ──
        bridge_active = set()
        for a in section.get('assignments', []):
            hf_id = a.get('histfig_id')
            position_id = a.get('position_id')
            if hf_id is None or position_id is None:
                continue
            if hf_id < 0:
                continue
            bridge_active.add((position_id, hf_id))

        # ── Load DB active rows for this entity ──
        db_rows = await conn.fetch("""
            SELECT id, position_id, hf_id, start_year
            FROM hf_position_links
            WHERE world_id = $1 AND entity_id = $2 AND end_year IS NULL
        """, world_id, entity_id)
        db_active = {}  # (position_id, hf_id) → {id, start_year}
        for r in db_rows:
            key = (r['position_id'], r['hf_id'])
            db_active[key] = {'id': r['id'], 'start_year': r['start_year']}

        # ── Removals: in DB but not in bridge → end the position ──
        removed = set(db_active.keys()) - bridge_active
        for pos_id, hf_id in removed:
            row = db_active[(pos_id, hf_id)]
            await conn.execute("""
                UPDATE hf_position_links SET end_year = $1 WHERE id = $2
            """, game_year, row['id'])
            count += 1
            log.info("Position ended: entity=%d pos=%d hf=%d year=%s",
                     entity_id, pos_id, hf_id, game_year)

        # ── Additions + backfills: in bridge ──
        for pos_id, hf_id in bridge_active:
            existing = db_active.get((pos_id, hf_id))
            if existing:
                # Row exists — backfill NULL start_year if needed
                if existing['start_year'] is None and game_year is not None:
                    await conn.execute("""
                        UPDATE hf_position_links SET start_year = $1 WHERE id = $2
                    """, game_year, existing['id'])
                    count += 1
            else:
                # New appointment — insert
                await conn.execute("""
                    INSERT INTO hf_position_links
                        (world_id, hf_id, entity_id, position_id, start_year)
                    VALUES ($1, $2, $3, $4, $5)
                """, world_id, hf_id, entity_id, pos_id, game_year)
                count += 1
                log.info("Position added: entity=%d pos=%d hf=%d year=%s",
                         entity_id, pos_id, hf_id, game_year)

    return count


# ── Fortress Operational Tables ───────────────────────────────────────


async def etl_armies(conn: asyncpg.Connection, armies_data,
                     world_id: int, game_year: int | None = None,
                     game_tick: int | None = None) -> int:
    """Promote bridge 'armies' section into fortress_armies table.

    Data comes as {"armies": [{id, controller_id, member_count, pos_x, pos_y}]}.
    Double-encoded in lua_probes — raw bridge_data is already parsed.
    """
    if not armies_data:
        return 0

    # Handle both dict wrapper and direct list
    army_list = armies_data
    if isinstance(armies_data, dict):
        army_list = armies_data.get("armies") or []
    if isinstance(army_list, str):
        army_list = json.loads(army_list)
        if isinstance(army_list, dict):
            army_list = army_list.get("armies", [])

    if not army_list:
        return 0

    count = 0
    for a in army_list:
        army_id = a.get("id")
        if army_id is None:
            continue
        await conn.execute("""
            INSERT INTO fortress_armies
                (world_id, army_id, controller_id, member_count, pos_x, pos_y,
                 last_seen_year, last_seen_tick, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
            ON CONFLICT (world_id, army_id) DO UPDATE SET
                controller_id = EXCLUDED.controller_id,
                member_count = EXCLUDED.member_count,
                pos_x = EXCLUDED.pos_x,
                pos_y = EXCLUDED.pos_y,
                last_seen_year = EXCLUDED.last_seen_year,
                last_seen_tick = EXCLUDED.last_seen_tick,
                updated_at = now()
        """, world_id, army_id,
             _sanitize_id(a.get("controller_id")),
             a.get("member_count", 0),
             a.get("pos_x"), a.get("pos_y"),
             game_year, game_tick)
        count += 1

    return count


async def etl_zones(conn: asyncpg.Connection, zones_data,
                    world_id: int) -> int:
    """Promote bridge 'zones' section into fortress_zones table.

    Data comes as {"zones": [{id, type, is_active, assigned_unit_count, ...}]}.
    """
    if not zones_data:
        return 0

    zone_list = zones_data
    if isinstance(zones_data, dict):
        zone_list = zones_data.get("zones") or []
    if isinstance(zone_list, str):
        zone_list = json.loads(zone_list)
        if isinstance(zone_list, dict):
            zone_list = zone_list.get("zones", [])

    if not zone_list:
        return 0

    count = 0
    for z in zone_list:
        zone_id = z.get("id")
        if zone_id is None:
            continue
        await conn.execute("""
            INSERT INTO fortress_zones
                (world_id, zone_id, zone_type, is_active, assigned_unit_count,
                 owner_unit_id, x1, y1, x2, y2, z, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now())
            ON CONFLICT (world_id, zone_id) DO UPDATE SET
                zone_type = EXCLUDED.zone_type,
                is_active = EXCLUDED.is_active,
                assigned_unit_count = EXCLUDED.assigned_unit_count,
                owner_unit_id = EXCLUDED.owner_unit_id,
                x1 = EXCLUDED.x1, y1 = EXCLUDED.y1,
                x2 = EXCLUDED.x2, y2 = EXCLUDED.y2,
                z = EXCLUDED.z,
                updated_at = now()
        """, world_id, zone_id,
             z.get("type"), z.get("is_active", True),
             z.get("assigned_unit_count", 0),
             _sanitize_id(z.get("owner_unit_id")),
             z.get("x1"), z.get("y1"), z.get("x2"), z.get("y2"), z.get("z"))
        count += 1

    return count


async def etl_mandates(conn: asyncpg.Connection, mandates_data,
                       world_id: int) -> int:
    """Promote bridge 'mandates' section into fortress_mandates table.

    Data comes as {"mandates": [{...}]}.
    """
    if not mandates_data:
        return 0

    mandate_list = mandates_data
    if isinstance(mandates_data, dict):
        mandate_list = mandates_data.get("mandates") or []
    if isinstance(mandate_list, str):
        mandate_list = json.loads(mandate_list)
        if isinstance(mandate_list, dict):
            mandate_list = mandate_list.get("mandates", [])

    if not mandate_list:
        return 0

    count = 0
    for idx, m in enumerate(mandate_list):
        mandate_id = m.get("id", idx)
        await conn.execute("""
            INSERT INTO fortress_mandates
                (world_id, mandate_id, mandate_type, item_type, item_subtype,
                 amount_total, amount_remaining, timeout_at, punish_type,
                 issuer_unit_id, details, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, now())
            ON CONFLICT (world_id, mandate_id) DO UPDATE SET
                mandate_type = EXCLUDED.mandate_type,
                item_type = EXCLUDED.item_type,
                item_subtype = EXCLUDED.item_subtype,
                amount_total = EXCLUDED.amount_total,
                amount_remaining = EXCLUDED.amount_remaining,
                timeout_at = EXCLUDED.timeout_at,
                punish_type = EXCLUDED.punish_type,
                issuer_unit_id = EXCLUDED.issuer_unit_id,
                details = EXCLUDED.details,
                updated_at = now()
        """, world_id, mandate_id,
             m.get("type"), m.get("item_type"), m.get("item_subtype"),
             m.get("amount_total", 0), m.get("amount_remaining", 0),
             m.get("timeout_at"), m.get("punish_type"),
             _sanitize_id(m.get("issuer_unit_id")),
             json.dumps({k: v for k, v in m.items()
                         if k not in ("id", "type", "item_type", "item_subtype",
                                      "amount_total", "amount_remaining",
                                      "timeout_at", "punish_type", "issuer_unit_id")}))
        count += 1

    return count


# ── Main Expanded ETL Orchestrator ──────────────────────────────────────


async def ingest_expanded(conn: asyncpg.Connection, bridge_data: dict,
                          world_id: int, game_year: int | None = None,
                          game_tick: int | None = None,
                          season_changed: bool = False) -> dict:
    """Run all expanded ETL functions on bridge data.

    Called from watcher.py after _store_bridge_sections().

    Args:
        conn: Active asyncpg connection
        bridge_data: Full bridge cycle JSON
        world_id: Target world ID
        game_year: Current in-game year
        game_tick: Current in-game tick
        season_changed: True if season boundary crossed (triggers fortress_state)

    Returns:
        Summary dict with counts per ETL function.
    """
    summary = {}

    async def _safe(name, coro):
        """Run an ETL coroutine, catching errors so one failure doesn't kill all."""
        try:
            summary[name] = await coro
        except Exception as e:
            log.warning("etl_%s failed: %s", name, e)
            summary[name] = 0

    # Tier 1: Critical
    await _safe("live_history", etl_live_history(
        conn, bridge_data.get("history"), world_id, game_year, game_tick))
    await _safe("incidents", etl_incidents(
        conn, bridge_data.get("incidents"), world_id))
    await _safe("interaction_instances", etl_interaction_instances(
        conn, bridge_data.get("interaction_instances"), world_id))

    # Tier 2: Social/Military
    await _safe("squads", etl_squads(
        conn, bridge_data.get("squads"), world_id))
    await _safe("announcements", etl_announcements(
        conn, bridge_data.get("announcements"), world_id, game_year, game_tick))
    await _safe("artifacts", etl_artifacts_live(
        conn, bridge_data.get("artifacts"), world_id))
    await _safe("event_collections", etl_event_collections(
        conn, bridge_data.get("event_collections"), world_id))
    await _safe("entities", etl_entities_live(
        conn, bridge_data.get("entities"), world_id))
    await _safe("diplomacy", etl_diplomacy(
        conn, bridge_data.get("diplomacy"), world_id))

    # Fortress state — only on season change; merge buildings counts into details
    if season_changed:
        fs_data = bridge_data.get("fortress_state") or {}
        # Include building counts in fortress state snapshot
        buildings = bridge_data.get("buildings")
        if buildings and isinstance(fs_data, dict):
            fs_data = dict(fs_data)  # copy to avoid mutating bridge_data
            fs_data["buildings"] = buildings
        await _safe("fortress_state", etl_fortress_state(
            conn, fs_data, world_id, game_year, game_tick))

    # Tier 2: Memory-only structures (only if bridge provides them)
    await _safe("belief_systems", etl_belief_systems(
        conn, bridge_data.get("belief_systems"), world_id))
    await _safe("cultural_identities", etl_cultural_identities(
        conn, bridge_data.get("cultural_identities"), world_id))
    await _safe("occupations", etl_occupations(
        conn, bridge_data.get("occupations"), world_id))
    await _safe("daily_events", etl_daily_events(
        conn, bridge_data.get("daily_events"), world_id, game_year, game_tick))

    # Noble position tracking (backfill NULL start_year)
    await _safe("noble_positions", etl_noble_positions(
        conn, bridge_data.get("noble_positions"), world_id, game_year))

    # HF ↔ Unit bidirectional links (from bridge unit hist_fig_id)
    await _safe("hf_unit_links", etl_hf_unit_links(
        conn, bridge_data, world_id))

    # Fortress operational tables
    await _safe("armies", etl_armies(
        conn, bridge_data.get("armies"), world_id, game_year, game_tick))
    await _safe("zones", etl_zones(
        conn, bridge_data.get("zones"), world_id))
    await _safe("mandates", etl_mandates(
        conn, bridge_data.get("mandates"), world_id))

    # Log non-zero results
    active = {k: v for k, v in summary.items() if v}
    if active:
        log.info("Expanded ETL: %s", active)

    return summary
