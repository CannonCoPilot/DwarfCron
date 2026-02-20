"""Streaming XML parser for Dwarf Fortress legends exports.

Parses both legends.xml (CP437, primary data) and legends_plus.xml (UTF-8,
enrichment data: landmasses, mountains, rivers, identities, relationships).

Uses lxml.iterparse for memory efficiency on large files, with batch INSERTs
(1000 rows per flush) for performance.
"""

import re
import logging
from pathlib import Path
from xml.etree.ElementTree import iterparse, tostring

import asyncpg

log = logging.getLogger(__name__)

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_BATCH_SIZE = 1000

# ── Event field → CDM column mapping ─────────────────────────────────────────
# Maps XML child tag names to history_events columns for the ~30 most common
# event types. Unmapped fields go into the JSONB 'details' column.

_EVENT_HF1_FIELDS = {
    "hfid", "hist_figure_id", "hist_fig_id", "builder_hfid",
    "trickster_hfid", "snatcher_hfid", "changee_hfid", "doer_hfid",
    "attacker_hfid", "woundee_hfid", "seeker_hfid", "hfid1",
    "group_hfid", "body_hfid", "student_hfid", "hfid_target",
}
_EVENT_HF2_FIELDS = {
    "slayer_hfid", "hfid2", "changer_hfid", "wounder_hfid",
    "target_hfid", "cover_hfid", "teacher_hfid", "trainer_hfid",
    "hfid_attacker", "hfid_defender", "defender_hfid",
}
_EVENT_SITE_FIELDS = {"site_id", "site"}
_EVENT_REGION_FIELDS = {"subregion_id", "region_id"}
_EVENT_ENTITY1_FIELDS = {"civ_id", "entity_id", "entity_id_1", "attacker_civ_id"}
_EVENT_ENTITY2_FIELDS = {"entity_id_2", "site_civ_id", "defender_civ_id"}
_EVENT_ARTIFACT_FIELDS = {"artifact_id"}
_EVENT_STRUCTURE_FIELDS = {"structure_id"}

_SKIP_VALUES = frozenset(("-1", "", "-1,-1"))


def _clean_legends_xml(filepath: str) -> str:
    """Read CP437-encoded legends.xml, strip invalid XML control characters."""
    log.info("Reading and cleaning %s", filepath)
    with open(filepath, "r", encoding="cp437", errors="replace") as f:
        content = f.read()
    return _CONTROL_CHAR_RE.sub("", content)


def _int_or_none(text: str | None) -> int | None:
    if text is None or text in _SKIP_VALUES:
        return None
    try:
        return int(text)
    except (ValueError, TypeError):
        return None


def _text(elem, tag: str) -> str | None:
    """Get text content of a child element, or None."""
    child = elem.find(tag)
    return child.text if child is not None and child.text else None


def _int(elem, tag: str) -> int | None:
    return _int_or_none(_text(elem, tag))


def _bool_flag(elem, tag: str) -> bool:
    """Check if an element has a child tag (presence = True)."""
    return elem.find(tag) is not None


# ── Parse regions ─────────────────────────────────────────────────────────────

def _parse_regions(root, world_id: int) -> list[tuple]:
    rows = []
    for r in root.findall(".//region"):
        rows.append((
            _int(r, "id"),
            world_id,
            _text(r, "name"),
            _text(r, "type"),
            _text(r, "coords"),
        ))
    return rows


# ── Parse sites ───────────────────────────────────────────────────────────────

def _parse_sites(root, world_id: int) -> tuple[list[tuple], list[tuple]]:
    site_rows = []
    struct_rows = []
    for s in root.findall(".//site"):
        sid = _int(s, "id")
        coords = _text(s, "coords")
        cx, cy = None, None
        if coords and "," in coords:
            parts = coords.split(",", 1)
            cx, cy = _int_or_none(parts[0]), _int_or_none(parts[1])
        site_rows.append((
            sid, world_id, _text(s, "name"), _text(s, "type"),
            cx, cy, coords, None, None,  # owner_entity_id, details
        ))
        for st in s.findall(".//structure"):
            struct_rows.append((
                sid,
                _int(st, "local_id"),
                _text(st, "name"),
                _text(st, "type"),
                _int(st, "entity_id"),
                None,  # details
            ))
    return site_rows, struct_rows


# ── Parse entities ────────────────────────────────────────────────────────────

def _parse_entities(root, world_id: int) -> list[tuple]:
    rows = []
    # Use scoped path to avoid matching bare <entity>ID</entity> refs inside events
    entities_section = root.find("entities")
    if entities_section is None:
        return rows
    for e in entities_section.findall("entity"):
        eid = _int(e, "id")
        if eid is None:
            continue
        rows.append((
            eid,
            world_id,
            _text(e, "name"),
            _text(e, "type"),
            _text(e, "race"),
            None,  # details
        ))
    return rows


# ── Parse historical figures ──────────────────────────────────────────────────

def _parse_historical_figures(root, world_id: int) -> tuple[list, list, list, list]:
    hf_rows = []
    hf_link_rows = []
    hf_entity_link_rows = []
    hf_site_link_rows = []

    for hf in root.findall(".//historical_figure"):
        hfid = _int(hf, "id")
        name = _text(hf, "name")
        race = _text(hf, "race")

        # Detect special types from associated_type or flags
        assoc_type = (_text(hf, "associated_type") or "").lower()

        hf_rows.append((
            hfid, world_id, name, race,
            _text(hf, "caste"),
            _int(hf, "sex"),
            _int(hf, "birth_year"),
            _int(hf, "birth_seconds72"),
            _int(hf, "death_year"),
            _int(hf, "death_seconds72"),
            _text(hf, "death_cause"),
            None,  # entity_id (filled from entity_links later)
            _bool_flag(hf, "deity"),
            _bool_flag(hf, "force"),
            "vampire" in assoc_type,
            "necromancer" in assoc_type,
            "werebeast" in assoc_type or "were" in assoc_type,
            _bool_flag(hf, "ghost"),
            0, 0,  # kill_count, event_count (computed later)
            None,  # details JSONB
        ))

        # HF-to-HF links
        for link in hf.findall("hf_link"):
            hf_link_rows.append((
                hfid,
                _int(link, "hfid"),
                _text(link, "link_type"),
            ))

        # Entity links
        for link in hf.findall("entity_link"):
            hf_entity_link_rows.append((
                hfid,
                _int(link, "entity_id"),
                _text(link, "link_type"),
                _text(link, "position_name"),
            ))

        # Site links
        for link in hf.findall("site_link"):
            hf_site_link_rows.append((
                hfid,
                _int(link, "site_id"),
                _text(link, "link_type"),
            ))

    return hf_rows, hf_link_rows, hf_entity_link_rows, hf_site_link_rows


# ── Parse events ──────────────────────────────────────────────────────────────

def _parse_event(ev, world_id: int) -> tuple:
    """Parse a single event element into a row tuple."""
    eid = _int(ev, "id")
    year = _int(ev, "year")
    seconds = _int(ev, "seconds72")
    event_type = _text(ev, "type")

    hf1 = hf2 = site = region = ent1 = ent2 = artifact = structure = None
    details = {}

    for child in ev:
        tag = child.tag
        val = child.text
        if tag in ("id", "year", "seconds72", "type") or val in _SKIP_VALUES:
            continue
        if not val:
            continue

        if tag in _EVENT_HF1_FIELDS and hf1 is None:
            hf1 = _int_or_none(val)
        elif tag in _EVENT_HF2_FIELDS and hf2 is None:
            hf2 = _int_or_none(val)
        elif tag in _EVENT_SITE_FIELDS and site is None:
            site = _int_or_none(val)
        elif tag in _EVENT_REGION_FIELDS and region is None:
            region = _int_or_none(val)
        elif tag in _EVENT_ENTITY1_FIELDS and ent1 is None:
            ent1 = _int_or_none(val)
        elif tag in _EVENT_ENTITY2_FIELDS and ent2 is None:
            ent2 = _int_or_none(val)
        elif tag in _EVENT_ARTIFACT_FIELDS and artifact is None:
            artifact = _int_or_none(val)
        elif tag in _EVENT_STRUCTURE_FIELDS and structure is None:
            structure = _int_or_none(val)
        else:
            # Unmapped field → details JSONB
            details[tag] = val

    import json
    return (
        eid, world_id, year, seconds, event_type,
        hf1, hf2, site, region, ent1, ent2, artifact, structure,
        json.dumps(details) if details else "{}",
    )


def _parse_events(root, world_id: int) -> list[tuple]:
    rows = []
    for ev in root.findall(".//historical_event"):
        rows.append(_parse_event(ev, world_id))
    return rows


# ── Parse event collections ──────────────────────────────────────────────────

def _parse_event_collections(root, world_id: int) -> tuple[list, list, list]:
    coll_rows = []
    coll_event_rows = []
    coll_sub_rows = []

    for coll in root.findall(".//historical_event_collection"):
        cid = _int(coll, "id")

        coll_rows.append((
            cid, world_id,
            _text(coll, "type"),
            _text(coll, "name"),
            _int(coll, "parent_eventcol") or _int(coll, "war_eventcol"),
            _int(coll, "start_year"),
            _int(coll, "start_seconds72"),
            _int(coll, "end_year"),
            _int(coll, "end_seconds72"),
            _int(coll, "aggressor_ent_id") or _int(coll, "attacking_enid"),
            _int(coll, "defender_ent_id") or _int(coll, "defending_enid"),
            _int(coll, "site_id"),
            _int(coll, "subregion_id"),
            None,  # details
        ))

        for ev_elem in coll.findall("event"):
            if ev_elem.text:
                eid = _int_or_none(ev_elem.text)
                if eid is not None:
                    coll_event_rows.append((cid, eid))

        for sc_elem in coll.findall("eventcol"):
            if sc_elem.text:
                scid = _int_or_none(sc_elem.text)
                if scid is not None:
                    coll_sub_rows.append((cid, scid))

    return coll_rows, coll_event_rows, coll_sub_rows


# ── Parse artifacts ───────────────────────────────────────────────────────────

def _parse_artifacts(root, world_id: int) -> list[tuple]:
    rows = []
    for a in root.findall(".//artifact"):
        rows.append((
            _int(a, "id"),
            world_id,
            _text(a, "name") or _text(a, "name_string"),
            _text(a, "item_type") or _text(a, "item"),
            _text(a, "item_subtype"),
            _text(a, "mat") or _text(a, "material"),
            _int(a, "creator_hfid") or _int(a, "hist_figure_id"),
            _int(a, "holder_hfid"),
            _int(a, "site_id"),
            None,  # details
        ))
    return rows


# ── Parse legends_plus enrichment ─────────────────────────────────────────────

def _parse_legends_plus(filepath: str, world_id: int) -> dict:
    """Parse legends_plus.xml for supplementary data."""
    import xml.etree.ElementTree as ET

    log.info("Parsing legends_plus: %s", filepath)
    tree = ET.parse(filepath)
    root = tree.getroot()

    result = {
        "world_name": root.findtext("name"),
        "world_alt_name": root.findtext("altname"),
        "landmasses": [],
        "mountain_peaks": [],
        "underground_regions": [],
        "identities": [],
        "event_relationships": [],
        "entities": [],
    }

    for lm in root.findall(".//landmass"):
        result["landmasses"].append((
            _int(lm, "id"), world_id,
            _text(lm, "name"),
            _text(lm, "coord_1"),
            _text(lm, "coord_2"),
        ))

    for mp in root.findall(".//mountain_peak"):
        result["mountain_peaks"].append((
            _int(mp, "id"), world_id,
            _text(mp, "name"),
            _text(mp, "coords"),
            _int(mp, "height"),
        ))

    for ur in root.findall(".//underground_region"):
        result["underground_regions"].append((
            _int(ur, "id"), world_id,
            _text(ur, "type"),
            _int(ur, "depth"),
            _text(ur, "coords"),
        ))

    for ident in root.findall(".//identity"):
        result["identities"].append((
            _int(ident, "id"), world_id,
            _text(ident, "name"),
            _int(ident, "histfig_id"),
            _int(ident, "birth_year"),
            _int(ident, "birth_second"),
            _int(ident, "entity_id"),
        ))

    for rel in root.findall(".//historical_event_relationship"):
        result["event_relationships"].append((
            world_id,
            _int(rel, "event"),
            _text(rel, "relationship"),
            _int(rel, "source_hf"),
            _int(rel, "target_hf"),
            _int(rel, "year"),
        ))

    # Entities (type, race, metadata not in legends.xml)
    import json as _json
    entities_section = root.find("entities")
    if entities_section is not None:
        for ent in entities_section.findall("entity"):
            eid = _int(ent, "id")
            if eid is None:
                continue
            ent_details = {}
            hfid = _int(ent, "histfig_id")
            child = _int(ent, "child")
            if hfid is not None:
                ent_details["histfig_id"] = hfid
            if child is not None:
                ent_details["child"] = child
            result["entities"].append((
                eid,
                world_id,
                _text(ent, "name"),
                _text(ent, "type"),
                _text(ent, "race"),
                _json.dumps(ent_details) if ent_details else None,
            ))

    return result


# ── Batch INSERT helpers ──────────────────────────────────────────────────────

async def _batch_insert(conn: asyncpg.Connection, table: str,
                        columns: list[str], rows: list[tuple],
                        on_conflict: str = "DO NOTHING"):
    """Insert rows in batches using COPY or executemany with conflict handling."""
    if not rows:
        return 0

    placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
    col_str = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders}) ON CONFLICT {on_conflict}"

    inserted = 0
    for i in range(0, len(rows), _BATCH_SIZE):
        batch = rows[i : i + _BATCH_SIZE]
        await conn.executemany(sql, batch)
        inserted += len(batch)

    return inserted


# ── Main import pipeline ──────────────────────────────────────────────────────

async def import_legends(
    conn: asyncpg.Connection,
    legends_path: str,
    legends_plus_path: str | None = None,
) -> dict[str, int]:
    """Import legends XML files into the CDM.

    Returns dict of table names → row counts inserted.
    """
    import json
    import xml.etree.ElementTree as ET

    counts = {}

    # ── Step 1: Clean and parse legends.xml ───────────────────────────────
    log.info("Step 1: Parsing legends.xml")
    cleaned = _clean_legends_xml(legends_path)
    root = ET.fromstring(cleaned)

    # ── Step 2: Parse legends_plus for world name ─────────────────────────
    world_name = None
    world_alt_name = None
    plus_data = None

    if legends_plus_path:
        plus_data = _parse_legends_plus(legends_plus_path, 0)  # world_id=0 temp
        world_name = plus_data["world_name"]
        world_alt_name = plus_data["world_alt_name"]

    # ── Step 3: Create world record ───────────────────────────────────────
    world_id = await conn.fetchval(
        "INSERT INTO worlds (name, alt_name, import_path) VALUES ($1, $2, $3) RETURNING id",
        world_name, world_alt_name, legends_path,
    )
    log.info("Created world %d: %s (%s)", world_id, world_name, world_alt_name)

    # Update world_id in plus_data tuples
    if plus_data:
        for key in ("landmasses", "mountain_peaks", "underground_regions",
                     "identities", "event_relationships", "entities"):
            plus_data[key] = [
                (row[0], world_id, *row[2:]) if key != "event_relationships"
                else (world_id, *row[1:])
                for row in plus_data[key]
            ]

    # ── Step 4: Insert in FK dependency order ─────────────────────────────

    # Regions
    region_rows = _parse_regions(root, world_id)
    n = await _batch_insert(conn, "regions",
        ["id", "world_id", "name", "type", "coords"], region_rows)
    counts["regions"] = n
    log.info("  regions: %d", n)

    # Sites + structures
    site_rows, struct_rows = _parse_sites(root, world_id)
    n = await _batch_insert(conn, "sites",
        ["id", "world_id", "name", "type", "coord_x", "coord_y", "coords",
         "owner_entity_id", "details"],
        site_rows)
    counts["sites"] = n
    log.info("  sites: %d", n)

    n = await _batch_insert(conn, "structures",
        ["site_id", "id", "name", "type", "entity_id", "details"],
        struct_rows, on_conflict="(site_id, id) DO NOTHING")
    counts["structures"] = n
    log.info("  structures: %d", n)

    # Entities
    entity_rows = _parse_entities(root, world_id)
    n = await _batch_insert(conn, "entities",
        ["id", "world_id", "name", "type", "race", "details"], entity_rows)
    counts["entities"] = n
    log.info("  entities: %d", n)

    # Historical figures + links
    hf_rows, hf_link_rows, hf_entity_link_rows, hf_site_link_rows = \
        _parse_historical_figures(root, world_id)
    n = await _batch_insert(conn, "historical_figures",
        ["id", "world_id", "name", "race", "caste", "sex",
         "birth_year", "birth_seconds", "death_year", "death_seconds",
         "death_cause", "entity_id",
         "is_deity", "is_force", "is_vampire", "is_necromancer",
         "is_werebeast", "is_ghost", "kill_count", "event_count", "details"],
        hf_rows)
    counts["historical_figures"] = n
    log.info("  historical_figures: %d", n)

    n = await _batch_insert(conn, "hf_links",
        ["hf_id", "target_hf_id", "link_type"], hf_link_rows,
        on_conflict="DO NOTHING")
    counts["hf_links"] = n
    log.info("  hf_links: %d", n)

    n = await _batch_insert(conn, "hf_entity_links",
        ["hf_id", "entity_id", "link_type", "position_name"],
        hf_entity_link_rows, on_conflict="DO NOTHING")
    counts["hf_entity_links"] = n
    log.info("  hf_entity_links: %d", n)

    n = await _batch_insert(conn, "hf_site_links",
        ["hf_id", "site_id", "link_type"], hf_site_link_rows,
        on_conflict="DO NOTHING")
    counts["hf_site_links"] = n
    log.info("  hf_site_links: %d", n)

    # Events
    event_rows = _parse_events(root, world_id)
    n = await _batch_insert(conn, "history_events",
        ["id", "world_id", "year", "seconds", "event_type",
         "hf_id_1", "hf_id_2", "site_id", "region_id",
         "entity_id_1", "entity_id_2", "artifact_id", "structure_id",
         "details"],
        event_rows)
    counts["history_events"] = n
    log.info("  history_events: %d", n)

    # Event collections
    coll_rows, coll_event_rows, coll_sub_rows = _parse_event_collections(root, world_id)
    n = await _batch_insert(conn, "history_event_collections",
        ["id", "world_id", "type", "name", "parent_id",
         "start_year", "start_seconds", "end_year", "end_seconds",
         "attacker_entity_id", "defender_entity_id", "site_id", "region_id",
         "details"],
        coll_rows)
    counts["history_event_collections"] = n
    log.info("  history_event_collections: %d", n)

    n = await _batch_insert(conn, "collection_events",
        ["collection_id", "event_id"], coll_event_rows,
        on_conflict="(collection_id, event_id) DO NOTHING")
    counts["collection_events"] = n
    log.info("  collection_events: %d", n)

    n = await _batch_insert(conn, "collection_subcollections",
        ["parent_id", "child_id"], coll_sub_rows,
        on_conflict="(parent_id, child_id) DO NOTHING")
    counts["collection_subcollections"] = n
    log.info("  collection_subcollections: %d", n)

    # Artifacts
    artifact_rows = _parse_artifacts(root, world_id)
    n = await _batch_insert(conn, "artifacts",
        ["id", "world_id", "name", "item_type", "item_subtype", "material",
         "creator_hf_id", "holder_hf_id", "site_id", "details"],
        artifact_rows)
    counts["artifacts"] = n
    log.info("  artifacts: %d", n)

    # ── Step 5: legends_plus enrichment ───────────────────────────────────
    if plus_data:
        n = await _batch_insert(conn, "landmasses",
            ["id", "world_id", "name", "coord_1", "coord_2"],
            plus_data["landmasses"])
        counts["landmasses"] = n
        log.info("  landmasses: %d", n)

        n = await _batch_insert(conn, "mountain_peaks",
            ["id", "world_id", "name", "coords", "height"],
            plus_data["mountain_peaks"])
        counts["mountain_peaks"] = n
        log.info("  mountain_peaks: %d", n)

        n = await _batch_insert(conn, "underground_regions",
            ["id", "world_id", "type", "depth", "coords"],
            plus_data["underground_regions"])
        counts["underground_regions"] = n
        log.info("  underground_regions: %d", n)

        n = await _batch_insert(conn, "identities",
            ["id", "world_id", "name", "histfig_id", "birth_year",
             "birth_second", "entity_id"],
            plus_data["identities"])
        counts["identities"] = n
        log.info("  identities: %d", n)

        n = await _batch_insert(conn, "event_relationships",
            ["world_id", "event_id", "relationship", "source_hf",
             "target_hf", "year"],
            plus_data["event_relationships"],
            on_conflict="DO NOTHING")
        counts["event_relationships"] = n
        log.info("  event_relationships: %d", n)

        # Entity enrichment: merge type/race from legends_plus into
        # entities already inserted from legends.xml, and insert new
        # sub-entities (site governments, military units, etc.)
        n = await _batch_insert(conn, "entities",
            ["id", "world_id", "name", "type", "race", "details"],
            plus_data["entities"],
            on_conflict="(id) DO UPDATE SET "
                "type = COALESCE(EXCLUDED.type, entities.type), "
                "race = COALESCE(EXCLUDED.race, entities.race), "
                "details = COALESCE(EXCLUDED.details, entities.details)")
        counts["entities_plus"] = n
        log.info("  entities (plus enrichment): %d", n)

    # ── Step 6: Update computed counts ────────────────────────────────────
    await conn.execute("""
        UPDATE historical_figures hf SET
            event_count = COALESCE(e.cnt, 0),
            kill_count = COALESCE(k.cnt, 0)
        FROM (
            SELECT hf_id_1 AS hfid, COUNT(*) AS cnt
            FROM history_events WHERE hf_id_1 IS NOT NULL
            GROUP BY hf_id_1
        ) e
        LEFT JOIN (
            SELECT hf_id_1 AS hfid, COUNT(*) AS cnt
            FROM history_events WHERE event_type = 'hf died' AND hf_id_2 IS NOT NULL
            GROUP BY hf_id_1
        ) k ON k.hfid = e.hfid
        WHERE hf.id = e.hfid
    """)
    # Also count hf_id_2 participation
    await conn.execute("""
        UPDATE historical_figures hf SET
            event_count = hf.event_count + COALESCE(e.cnt, 0)
        FROM (
            SELECT hf_id_2 AS hfid, COUNT(*) AS cnt
            FROM history_events WHERE hf_id_2 IS NOT NULL
            GROUP BY hf_id_2
        ) e
        WHERE hf.id = e.hfid
    """)
    log.info("Updated event/kill counts on historical_figures")

    # Free memory
    del root, cleaned
    if plus_data:
        del plus_data

    return counts
