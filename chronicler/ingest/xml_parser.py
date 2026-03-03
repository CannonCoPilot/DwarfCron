"""Streaming XML parser for Dwarf Fortress legends exports.

Parses both legends.xml (CP437, primary data) and legends_plus.xml (UTF-8,
enrichment data: landmasses, mountains, rivers, identities, relationships).

Uses lxml.iterparse for memory efficiency on large files, with batch INSERTs
(1000 rows per flush) for performance.
"""

import json
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
    for r in root.findall("regions/region"):
        rows.append((
            _int(r, "id"),
            world_id,
            _text(r, "name"),
            _text(r, "type"),
            _text(r, "coords"),
        ))
    return rows


# ── Parse underground regions ────────────────────────────────────────────────

def _parse_underground_regions(root, world_id: int) -> list[tuple]:
    """Parse underground_regions from legends.xml (has type + depth).

    legends_plus.xml adds coords but lacks type/depth, so we parse
    from legends.xml first and enrich from plus later.
    """
    rows = []
    for ur in root.findall("underground_regions/underground_region"):
        rows.append((
            _int(ur, "id"),
            world_id,
            _text(ur, "type"),
            _int(ur, "depth"),
            _text(ur, "coords"),  # Usually absent in legends.xml
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
                world_id,
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

def _parse_historical_figures(root, world_id: int) -> tuple[list, list, list, list, list]:
    hf_rows = []
    hf_link_rows = []
    hf_entity_link_rows = []
    hf_site_link_rows = []
    hf_position_link_rows = []

    for hf in root.findall(".//historical_figure"):
        hfid = _int(hf, "id")
        name = _text(hf, "name")
        race = _text(hf, "race")

        # Detect supernatural types from XML structure:
        # - Deities/forces have <sphere> child elements
        # - Vampires have <active_interaction> with DEITY_MAJOR_CURSE_*
        # - Necromancers have <interaction_knowledge> with SECRET_*
        # - Werebeasts have <active_interaction> with DEITY_CURSE_WEREBEAST_*
        spheres = [s.text for s in hf.findall("sphere") if s.text]
        interactions = [
            (ai.text or "").upper()
            for ai in hf.findall("active_interaction")
        ]
        knowledge = [
            (ik.text or "").upper()
            for ik in hf.findall("interaction_knowledge")
        ]

        is_deity = len(spheres) > 0
        is_force = False  # TODO: distinguish from deity via entity worship links
        is_vampire = any(
            i.startswith("DEITY_MAJOR_CURSE") for i in interactions
        )
        is_necromancer = any(k.startswith("SECRET") for k in knowledge)
        is_werebeast = any(
            i.startswith("DEITY_CURSE_WEREBEAST") for i in interactions
        )
        is_ghost = False  # No reliable XML tag; detected via events

        # Goals (from legends.xml <goal> elements)
        goals = [g.text for g in hf.findall("goal") if g.text]

        # Skills (from legends.xml <hf_skill> elements)
        skills = []
        for sk in hf.findall("hf_skill"):
            skill_name = _text(sk, "skill")
            total_ip = _int(sk, "total_ip")
            if skill_name:
                skills.append({"name": skill_name, "total_ip": total_ip})

        # Holds artifact (from legends.xml <holds_artifact> elements)
        held_artifacts = [_int_or_none(ha.text) for ha in hf.findall("holds_artifact") if ha.text]
        held_artifacts = [h for h in held_artifacts if h is not None]

        # Overflow details: interaction_knowledge and other misc data
        details: dict | None = None
        if knowledge:
            details = {"interaction_knowledge": knowledge}

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
            is_deity,
            is_force,
            is_vampire,
            is_necromancer,
            is_werebeast,
            is_ghost,
            0, 0,  # kill_count, event_count (computed later)
            spheres or None,  # spheres TEXT[]
            goals if goals else None,  # goals JSONB
            skills if skills else None,  # skills JSONB
            held_artifacts or None,  # holds_artifact INTEGER[]
            interactions or None,  # active_interactions TEXT[]
            details if details else None,
        ))

        # HF-to-HF links
        for link in hf.findall("hf_link"):
            hf_link_rows.append((
                world_id,
                hfid,
                _int(link, "hfid"),
                _text(link, "link_type"),
            ))

        # Entity links
        for link in hf.findall("entity_link"):
            hf_entity_link_rows.append((
                world_id,
                hfid,
                _int(link, "entity_id"),
                _text(link, "link_type"),
                _text(link, "position_name"),
            ))

        # Site links
        for link in hf.findall("site_link"):
            hf_site_link_rows.append((
                world_id,
                hfid,
                _int(link, "site_id"),
                _text(link, "link_type"),
            ))

        # Position links (active)
        for link in hf.findall("entity_position_link"):
            hf_position_link_rows.append((
                world_id, hfid,
                _int(link, "entity_id"),
                _int(link, "position_profile_id"),
                _int(link, "start_year"),
                None,  # end_year (active = currently held)
            ))

        # Former position links
        for link in hf.findall("entity_former_position_link"):
            hf_position_link_rows.append((
                world_id, hfid,
                _int(link, "entity_id"),
                _int(link, "position_profile_id"),
                _int(link, "start_year"),
                _int(link, "end_year"),
            ))

    return hf_rows, hf_link_rows, hf_entity_link_rows, hf_site_link_rows, hf_position_link_rows


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
        details if details else {},
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
                    coll_event_rows.append((world_id, cid, eid))

        for sc_elem in coll.findall("eventcol"):
            if sc_elem.text:
                scid = _int_or_none(sc_elem.text)
                if scid is not None:
                    coll_sub_rows.append((world_id, cid, scid))

    return coll_rows, coll_event_rows, coll_sub_rows


# ── Parse artifacts ───────────────────────────────────────────────────────────

def _parse_artifacts(root, world_id: int) -> list[tuple]:
    rows = []
    for a in root.findall(".//artifact"):
        # Build details JSONB from any extra tags in legends.xml
        details = {}
        writing_id = _int(a, "writing")
        if writing_id is not None:
            details["writing_id"] = writing_id
        page_count = _int(a, "page_count")
        if page_count is not None:
            details["page_count"] = page_count
        item_desc = _text(a, "item_description")
        if item_desc:
            details["item_description"] = item_desc
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
            details if details else None,
        ))
    return rows


# ── Parse written contents ───────────────────────────────────────────────────

def _parse_written_contents(root, world_id: int) -> list[tuple]:
    """Parse written_contents from legends.xml.

    Fields: id, title, author_hfid, form (lowercase text), form_id.
    Style entries are "key:value" pairs (e.g. "melancholy:4").
    """
    rows = []
    section = root.find("written_contents")
    if section is None:
        return rows
    for wc in section.findall("written_content"):
        wcid = _int(wc, "id")
        if wcid is None:
            continue
        # Collect style elements
        styles = [s.text for s in wc.findall("style") if s.text]
        # Build details for extra fields
        details = {}
        form_id = _int(wc, "form_id")
        if form_id is not None:
            details["form_id"] = form_id
        author_roll = _int(wc, "author_roll")
        if author_roll is not None:
            details["author_roll"] = author_roll
        rows.append((
            wcid, world_id,
            _text(wc, "title"),
            _int(wc, "author_hfid"),
            _text(wc, "form"),
            None,  # type (filled from legends_plus)
            None, None,  # page_start, page_end (filled from legends_plus)
            styles or None,
            details if details else None,
        ))
    return rows


# ── Parse historical eras ────────────────────────────────────────────────────

def _parse_historical_eras(root, world_id: int) -> list[tuple]:
    """Parse historical_eras from legends.xml.

    Note: start_year uses raw int parsing (not _int) because -1 means
    "beginning of time" for eras, whereas _int skips -1 as a null marker.
    """
    rows = []
    section = root.find("historical_eras")
    if section is None:
        return rows
    for era in section.findall("historical_era"):
        name = _text(era, "name")
        if not name:
            continue
        start_year_text = _text(era, "start_year")
        start_year = int(start_year_text) if start_year_text is not None else None
        rows.append((
            world_id,
            name,
            start_year,
        ))
    return rows


# ── Parse legends_plus enrichment ─────────────────────────────────────────────

def _parse_creature_raw(root, world_id: int) -> list[tuple]:
    """Parse <creature_raw> section from legends_plus.xml.

    Extracts creature_id, name_singular, name_plural, and all boolean flags
    (self-closing tags with no text content) into a JSONB dict.
    """
    import json as _json
    rows = []
    cr = root.find("creature_raw")
    if cr is None:
        return rows
    for creature in cr.findall("creature"):
        cid = _text(creature, "creature_id")
        if not cid:
            continue
        ns = _text(creature, "name_singular")
        np = _text(creature, "name_plural")
        # Boolean flags: child tags with None text (self-closing)
        flags = {}
        for child in creature:
            if child.tag not in ("creature_id", "name_singular", "name_plural") and child.text is None:
                flags[child.tag] = True
        rows.append((world_id, cid, ns, np, flags if flags else {}))
    return rows


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
        "site_owners": [],  # (site_id, owner_entity_id) from cur_owner_id
        "written_contents": [],  # enrichment from plus (type, pages, references)
        "world_constructions": [],
        "entity_positions": [],  # position definitions from <entity_position>
        "entity_position_assignments": [],  # current holders from <entity_position_assignment>
        "art_forms": [],
        "rivers": [],
        "entity_populations": [],
        "hf_enrichment": [],  # (hf_id, world_id, field_dict) for HF UPDATE pass
        "region_enrichment": [],  # (id, world_id, coords, evilness) for region UPDATE
        "creature_dictionary": [],  # (world_id, creature_id, name_singular, name_plural, flags_json)
        "artifact_enrichment": [],  # (artifact_id, world_id, details_dict) for artifact UPDATE
        "event_enrichment": [],  # (event_id, world_id, details_dict) for event UPDATE
        "structure_enrichment": [],  # (world_id, site_id, struct_id, details_dict) for structure UPDATE
        "relationship_supplements": [],  # (world_id, event_id, occasion_type, site_id, reason)
    }

    # Region enrichment: legends_plus has coords + evilness for surface regions
    for r in root.findall("regions/region"):
        result["region_enrichment"].append((
            _int(r, "id"), world_id,
            _text(r, "coords"),
            _text(r, "evilness"),
        ))

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
            _bool_flag(mp, "is_volcano"),
        ))

    for ur in root.findall("underground_regions/underground_region"):
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
            _text(ident, "race"),
            _text(ident, "caste"),
            _text(ident, "profession"),
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

    # Event enrichment: capture plus-only fields (reason, nested circumstance, etc.)
    # Skip tags already handled by base parser (structured columns + core fields)
    _ALREADY_HANDLED = (
        frozenset({"id", "year", "seconds72", "type"})
        | _EVENT_HF1_FIELDS | _EVENT_HF2_FIELDS
        | _EVENT_SITE_FIELDS | _EVENT_REGION_FIELDS
        | _EVENT_ENTITY1_FIELDS | _EVENT_ENTITY2_FIELDS
        | _EVENT_ARTIFACT_FIELDS | _EVENT_STRUCTURE_FIELDS
    )
    events_section = root.find("historical_events")
    if events_section is not None:
        for ev in events_section.findall("historical_event"):
            eid = _int(ev, "id")
            if eid is None:
                continue
            enrichment = {}
            for child in ev:
                tag = child.tag
                if tag in _ALREADY_HANDLED:
                    continue  # Already captured from base into structured columns
                sub_elems = list(child)
                if sub_elems:
                    # Nested element (e.g., <circumstance>)
                    nested = {}
                    for sub in sub_elems:
                        nested[sub.tag] = sub.text
                    enrichment[tag] = nested
                elif child.text:
                    enrichment[tag] = child.text
            if enrichment:
                result["event_enrichment"].append((eid, world_id, enrichment))

    # Relationship supplements (plus-only: occasion_type, site, reason)
    for sup in root.findall(".//historical_event_relationship_supplement"):
        result["relationship_supplements"].append((
            world_id,
            _int(sup, "event"),
            _text(sup, "occasion_type"),
            _int(sup, "site"),
            _text(sup, "reason"),
        ))

    # Site ownership from legends_plus (cur_owner_id)
    sites_section = root.find("sites")
    if sites_section is not None:
        for site in sites_section.findall("site"):
            sid = _int(site, "id")
            owner = _int(site, "cur_owner_id")
            if sid is not None and owner is not None:
                result["site_owners"].append((sid, owner))

            # Structure enrichment: deity, religion, inhabitant, name2
            for struct in site.findall(".//structure"):
                struct_id = _int(struct, "local_id") or _int(struct, "id")
                if struct_id is None or sid is None:
                    continue
                s_enrichment = {}
                deity = _int(struct, "deity")
                if deity is not None:
                    s_enrichment["deity_hf_id"] = deity
                deity_type = _int(struct, "deity_type")
                if deity_type is not None:
                    s_enrichment["deity_type"] = deity_type
                religion = _int(struct, "religion")
                if religion is not None:
                    s_enrichment["religion_entity_id"] = religion
                name2 = _text(struct, "name2")
                if name2:
                    s_enrichment["name2"] = name2
                # Inhabitants (can be multiple)
                inhabitants = [_int_or_none(inh.text) for inh in struct.findall("inhabitant") if inh.text]
                inhabitants = [i for i in inhabitants if i is not None]
                if inhabitants:
                    s_enrichment["inhabitants"] = inhabitants
                if s_enrichment:
                    result["structure_enrichment"].append((world_id, sid, struct_id, s_enrichment))

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
            if hfid is not None:
                ent_details["histfig_id"] = hfid
            # Capture ALL <child> elements as an array (not just the first)
            children = [int(c.text) for c in ent.findall("child") if c.text]
            if children:
                ent_details["children"] = children
            # Capture <entity_link> elements (typed relationships to other entities)
            entity_links = []
            for el in ent.findall("entity_link"):
                link = {}
                lt = el.findtext("type")
                target = el.findtext("target")
                strength = el.findtext("strength")
                if lt:
                    link["type"] = lt
                if target:
                    link["target"] = int(target)
                if strength:
                    link["strength"] = int(strength)
                if link:
                    entity_links.append(link)
            if entity_links:
                ent_details["entity_links"] = entity_links
            result["entities"].append((
                eid,
                world_id,
                _text(ent, "name"),
                _text(ent, "type"),
                _text(ent, "race"),
                ent_details if ent_details else None,
            ))

            # Position definitions
            for pos in ent.findall("entity_position"):
                result["entity_positions"].append((
                    world_id, eid,
                    _int(pos, "id"),
                    _text(pos, "name"),
                    _text(pos, "name_male"),
                    _text(pos, "name_female"),
                    _text(pos, "spouse"),
                    _text(pos, "spouse_male"),
                    _text(pos, "spouse_female"),
                ))

            # Current position assignments
            for assign in ent.findall("entity_position_assignment"):
                histfig = _int(assign, "histfig")
                pos_id = _int(assign, "position_id")
                if histfig is not None and pos_id is not None:
                    result["entity_position_assignments"].append((
                        world_id, histfig, eid, pos_id,
                        None, None,  # start/end year not in assignments
                    ))

    # Written contents enrichment (type, pages, styles, references)
    wc_section = root.find("written_contents")
    if wc_section is not None:
        for wc in wc_section.findall("written_content"):
            wcid = _int(wc, "id")
            if wcid is None:
                continue
            styles = [s.text for s in wc.findall("style") if s.text]
            # Collect references as JSONB
            refs = []
            for ref in wc.findall("reference"):
                ref_type = _text(ref, "type")
                ref_id = _int(ref, "id")
                if ref_type or ref_id is not None:
                    refs.append({"type": ref_type, "id": ref_id})
            wc_details = {}
            if refs:
                wc_details["references"] = refs
            result["written_contents"].append((
                wcid, world_id,
                _text(wc, "title"),
                _int(wc, "author"),
                None,  # form (from legends.xml, not in plus)
                _text(wc, "type"),
                _int(wc, "page_start"),
                _int(wc, "page_end"),
                styles or None,
                wc_details if wc_details else None,
            ))

    # World constructions (roads, bridges, tunnels)
    for wcon in root.findall(".//world_construction"):
        result["world_constructions"].append((
            _int(wcon, "id"), world_id,
            _text(wcon, "name"),
            _text(wcon, "type"),
            _text(wcon, "coords"),
        ))

    # Art forms: dance_forms, musical_forms, poetic_forms → unified art_forms table
    for form_type, tag in [("dance", "dance_form"), ("musical", "musical_form"), ("poetic", "poetic_form")]:
        for af in root.findall(f".//{tag}"):
            af_details = {}
            # Collect form-type-specific fields into details
            for child in af:
                if child.tag not in ("id", "name", "description") and child.text:
                    af_details[child.tag] = child.text
            result["art_forms"].append((
                _int(af, "id"), world_id,
                _text(af, "name"),
                form_type,
                _text(af, "description"),
                af_details if af_details else None,
            ))

    # Rivers — DF XML has no <id> element, so we generate synthetic sequential IDs
    for idx, river in enumerate(root.findall(".//river")):
        r_details = {}
        for child in river:
            if child.tag not in ("name", "name_english", "path", "end_type", "end_pos") and child.text:
                r_details[child.tag] = child.text
        # end_pos is DF's actual field; store as end_type for our schema
        end_info = _text(river, "end_pos") or _text(river, "end_type")
        if end_info:
            r_details["end_pos"] = end_info
        result["rivers"].append((
            idx, world_id,
            _text(river, "name"),
            _text(river, "name_english"),
            _text(river, "path"),
            None,  # end_type (DF uses end_pos coords, not a type string)
            r_details if r_details else None,
        ))

    # Entity populations (race:count pairs per civilization)
    for ep in root.findall(".//entity_population"):
        ep_id = _int(ep, "id")
        if ep_id is None:
            continue
        race_raw = _text(ep, "race") or ""
        # DF encodes as "race_token:count" — split into race and count
        if ":" in race_raw:
            race_str, count_str = race_raw.rsplit(":", 1)
            try:
                pop_count = int(count_str)
            except ValueError:
                race_str = race_raw
                pop_count = None
        else:
            race_str = race_raw
            pop_count = None
        result["entity_populations"].append((
            ep_id, world_id,
            race_str or None,
            pop_count,
            _int(ep, "civ_id"),
        ))

    # HF enrichment: expanded fields from legends_plus HF elements
    hf_section = root.find("historical_figures")
    if hf_section is not None:
        for hf in hf_section.findall("historical_figure"):
            hfid = _int(hf, "id")
            if hfid is None:
                continue
            enrichment = {}

            # Spheres (TEXT[])
            spheres = [s.text for s in hf.findall("sphere") if s.text]
            if spheres:
                enrichment["spheres"] = spheres

            # Active interactions (TEXT[])
            interactions = [ai.text for ai in hf.findall("active_interaction") if ai.text]
            if interactions:
                enrichment["active_interactions"] = interactions

            # Goals (JSONB array)
            goals = []
            for goal_elem in hf.findall("goal"):
                goals.append(goal_elem.text or "")
            if goals:
                enrichment["goals"] = goals

            # Skills (JSONB array with id, rating, xp)
            skills = []
            for skill_elem in hf.findall(".//skill"):
                skill_id = _int(skill_elem, "id")
                rating = _int(skill_elem, "rating")
                xp = _int(skill_elem, "experience")
                if skill_id is not None:
                    skills.append({"id": skill_id, "rating": rating, "xp": xp})
            if skills:
                enrichment["skills"] = skills

            # Kills (JSONB with notable + other count)
            kills = {"notable": [], "other": 0}
            for kill_elem in hf.findall(".//notable_kill"):
                kills["notable"].append({
                    "hf_id": _int(kill_elem, "hf_id"),
                    "type": _text(kill_elem, "type"),
                })
            other_kills = _int(hf, "other_kill_count")
            if other_kills is not None:
                kills["other"] = other_kills
            if kills["notable"] or kills["other"]:
                enrichment["kills"] = kills

            # Whereabouts (JSONB)
            current_state = _text(hf, "current_state")
            if current_state:
                enrichment["whereabouts"] = {
                    "state": current_state,
                    "site_id": _int(hf, "cur_site_id"),
                    "subregion_id": _int(hf, "cur_subregion_id"),
                }

            # Entity reputations (JSONB array)
            reputations = []
            for rep in hf.findall("entity_reputation"):
                reputations.append({
                    "entity_id": _int(rep, "entity_id"),
                    "type": _text(rep, "type"),
                    "severity": _int(rep, "severity"),
                })
            if reputations:
                enrichment["entity_reputations"] = reputations

            # Intrigue actors (JSONB array)
            intrigue = []
            for ia in hf.findall("intrigue_actor"):
                intrigue.append({
                    "role": _text(ia, "role"),
                    "strategy": _text(ia, "strategy"),
                    "entity_id": _int(ia, "entity_id"),
                    "hf_id": _int(ia, "hf_id"),
                })
            if intrigue:
                enrichment["intrigue_actors"] = intrigue

            # Used identities (JSONB array of IDs)
            used_ids = [_int_or_none(uid.text) for uid in hf.findall("used_identity_id") if uid.text]
            used_ids = [u for u in used_ids if u is not None]
            if used_ids:
                enrichment["used_identities"] = used_ids

            # Journey pets (JSONB array)
            pets = [jp.text for jp in hf.findall("journey_pet") if jp.text]
            if pets:
                enrichment["journey_pets"] = pets

            # Holds artifact (INTEGER[])
            held = [_int_or_none(ha.text) for ha in hf.findall("holds_artifact") if ha.text]
            held = [h for h in held if h is not None]
            if held:
                enrichment["holds_artifact"] = held

            if enrichment:
                result["hf_enrichment"].append((hfid, world_id, enrichment))

    # Creature dictionary (creature_raw section)
    result["creature_dictionary"] = _parse_creature_raw(root, world_id)

    # Artifact enrichment: capture writing_id and page_count from legends_plus
    for a in root.findall(".//artifact"):
        aid = _int(a, "id")
        if aid is None:
            continue
        details = {}
        writing_id = _int(a, "writing")
        if writing_id is not None:
            details["writing_id"] = writing_id
        page_count = _int(a, "page_count")
        if page_count is not None:
            details["page_count"] = page_count
        item_desc = _text(a, "item_description")
        if item_desc:
            details["item_description"] = item_desc
        if details:
            result["artifact_enrichment"].append((aid, world_id, details))

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
                     "identities", "event_relationships", "entities",
                     "written_contents", "world_constructions",
                     "entity_positions", "entity_position_assignments",
                     "art_forms", "rivers", "entity_populations",
                     "region_enrichment", "creature_dictionary",
                     "relationship_supplements"):
            # Keys where world_id is at position [0] (not [1])
            world_id_at_zero = key in (
                "event_relationships", "entity_positions",
                "entity_position_assignments", "creature_dictionary",
                "relationship_supplements",
            )
            plus_data[key] = [
                (world_id, *row[1:]) if world_id_at_zero
                else (row[0], world_id, *row[2:])
                for row in plus_data[key]
            ]
        # HF enrichment: update world_id at position [1]
        plus_data["hf_enrichment"] = [
            (row[0], world_id, row[2]) for row in plus_data["hf_enrichment"]
        ]
        # Artifact enrichment: update world_id at position [1]
        plus_data["artifact_enrichment"] = [
            (row[0], world_id, row[2]) for row in plus_data["artifact_enrichment"]
        ]
        # Event enrichment: update world_id at position [1]
        plus_data["event_enrichment"] = [
            (row[0], world_id, row[2]) for row in plus_data["event_enrichment"]
        ]
        # Structure enrichment: update world_id at position [0]
        plus_data["structure_enrichment"] = [
            (world_id, row[1], row[2], row[3]) for row in plus_data["structure_enrichment"]
        ]

    # ── Step 4: Insert in FK dependency order ─────────────────────────────

    # Regions
    region_rows = _parse_regions(root, world_id)
    n = await _batch_insert(conn, "regions",
        ["id", "world_id", "name", "type", "coords"], region_rows)
    counts["regions"] = n
    log.info("  regions: %d", n)

    # Underground regions (type, depth from legends.xml; coords enriched from plus)
    ur_rows = _parse_underground_regions(root, world_id)
    n = await _batch_insert(conn, "underground_regions",
        ["id", "world_id", "type", "depth", "coords"], ur_rows)
    counts["underground_regions"] = n
    log.info("  underground_regions: %d", n)

    # Sites + structures
    site_rows, struct_rows = _parse_sites(root, world_id)
    n = await _batch_insert(conn, "sites",
        ["id", "world_id", "name", "type", "coord_x", "coord_y", "coords",
         "owner_entity_id", "details"],
        site_rows)
    counts["sites"] = n
    log.info("  sites: %d", n)

    n = await _batch_insert(conn, "structures",
        ["world_id", "site_id", "id", "name", "type", "entity_id", "details"],
        struct_rows, on_conflict="(world_id, site_id, id) DO NOTHING")
    counts["structures"] = n
    log.info("  structures: %d", n)

    # Entities
    entity_rows = _parse_entities(root, world_id)
    n = await _batch_insert(conn, "entities",
        ["id", "world_id", "name", "type", "race", "details"], entity_rows)
    counts["entities"] = n
    log.info("  entities: %d", n)

    # Historical figures + links
    hf_rows, hf_link_rows, hf_entity_link_rows, hf_site_link_rows, hf_position_link_rows = \
        _parse_historical_figures(root, world_id)
    n = await _batch_insert(conn, "historical_figures",
        ["id", "world_id", "name", "race", "caste", "sex",
         "birth_year", "birth_seconds", "death_year", "death_seconds",
         "death_cause", "entity_id",
         "is_deity", "is_force", "is_vampire", "is_necromancer",
         "is_werebeast", "is_ghost", "kill_count", "event_count",
         "spheres", "goals", "skills", "holds_artifact",
         "active_interactions", "details"],
        hf_rows)
    counts["historical_figures"] = n
    log.info("  historical_figures: %d", n)

    n = await _batch_insert(conn, "hf_links",
        ["world_id", "hf_id", "target_hf_id", "link_type"], hf_link_rows,
        on_conflict="(world_id, hf_id, target_hf_id, link_type) DO NOTHING")
    counts["hf_links"] = n
    log.info("  hf_links: %d", n)

    n = await _batch_insert(conn, "hf_entity_links",
        ["world_id", "hf_id", "entity_id", "link_type", "position_name"],
        hf_entity_link_rows,
        on_conflict="(world_id, hf_id, entity_id, link_type) DO UPDATE SET position_name = EXCLUDED.position_name")
    counts["hf_entity_links"] = n
    log.info("  hf_entity_links: %d", n)

    n = await _batch_insert(conn, "hf_site_links",
        ["world_id", "hf_id", "site_id", "link_type"], hf_site_link_rows,
        on_conflict="(world_id, hf_id, site_id, link_type) DO NOTHING")
    counts["hf_site_links"] = n
    log.info("  hf_site_links: %d", n)

    # HF position links (from standard legends)
    n = await _batch_insert(conn, "hf_position_links",
        ["world_id", "hf_id", "entity_id", "position_id",
         "start_year", "end_year"],
        hf_position_link_rows,
        on_conflict="(world_id, hf_id, entity_id, position_id, start_year) DO NOTHING")
    counts["hf_position_links"] = n
    log.info("  hf_position_links: %d", n)

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
        ["world_id", "collection_id", "event_id"], coll_event_rows,
        on_conflict="(world_id, collection_id, event_id) DO NOTHING")
    counts["collection_events"] = n
    log.info("  collection_events: %d", n)

    n = await _batch_insert(conn, "collection_subcollections",
        ["world_id", "parent_id", "child_id"], coll_sub_rows,
        on_conflict="(world_id, parent_id, child_id) DO NOTHING")
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

    # Written contents (from legends.xml)
    wc_rows = _parse_written_contents(root, world_id)
    n = await _batch_insert(conn, "written_contents",
        ["id", "world_id", "title", "author_hf_id", "form", "type",
         "page_start", "page_end", "styles", "details"],
        wc_rows)
    counts["written_contents"] = n
    log.info("  written_contents: %d", n)

    # Historical eras (from legends.xml)
    era_rows = _parse_historical_eras(root, world_id)
    n = await _batch_insert(conn, "historical_eras",
        ["world_id", "name", "start_year"],
        era_rows, on_conflict="(world_id, name) DO NOTHING")
    counts["historical_eras"] = n
    log.info("  historical_eras: %d", n)

    # ── Step 5: legends_plus enrichment ───────────────────────────────────
    if plus_data:
        n = await _batch_insert(conn, "landmasses",
            ["id", "world_id", "name", "coord_1", "coord_2"],
            plus_data["landmasses"])
        counts["landmasses"] = n
        log.info("  landmasses: %d", n)

        n = await _batch_insert(conn, "mountain_peaks",
            ["id", "world_id", "name", "coords", "height", "is_volcano"],
            plus_data["mountain_peaks"])
        counts["mountain_peaks"] = n
        log.info("  mountain_peaks: %d", n)

        n = await _batch_insert(conn, "underground_regions",
            ["id", "world_id", "type", "depth", "coords"],
            plus_data["underground_regions"],
            on_conflict="(world_id, id) DO UPDATE SET "
                "coords = COALESCE(EXCLUDED.coords, underground_regions.coords), "
                "type = COALESCE(underground_regions.type, EXCLUDED.type), "
                "depth = COALESCE(underground_regions.depth, EXCLUDED.depth)")
        counts["underground_regions_plus"] = n
        log.info("  underground_regions (plus enrichment): %d", n)

        # Region enrichment: coords + evilness from legends_plus
        if plus_data["region_enrichment"]:
            n = await _batch_insert(conn, "regions",
                ["id", "world_id", "coords", "evilness"],
                plus_data["region_enrichment"],
                on_conflict="(world_id, id) DO UPDATE SET "
                    "coords = COALESCE(EXCLUDED.coords, regions.coords), "
                    "evilness = COALESCE(EXCLUDED.evilness, regions.evilness)")
            counts["regions_plus"] = n
            log.info("  regions (plus enrichment): %d", n)

        n = await _batch_insert(conn, "identities",
            ["id", "world_id", "name", "histfig_id", "birth_year",
             "birth_second", "entity_id", "race", "caste", "profession"],
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
            on_conflict="(world_id, id) DO UPDATE SET "
                "type = COALESCE(EXCLUDED.type, entities.type), "
                "race = COALESCE(EXCLUDED.race, entities.race), "
                "details = COALESCE(EXCLUDED.details, entities.details)")
        counts["entities_plus"] = n
        log.info("  entities (plus enrichment): %d", n)

        # Entity position definitions
        if plus_data.get("entity_positions"):
            n = await _batch_insert(conn, "entity_positions",
                ["world_id", "entity_id", "position_id", "name",
                 "name_male", "name_female", "spouse", "spouse_male", "spouse_female"],
                plus_data["entity_positions"],
                on_conflict="(world_id, entity_id, position_id) DO UPDATE SET "
                    "name = COALESCE(EXCLUDED.name, entity_positions.name), "
                    "name_male = COALESCE(EXCLUDED.name_male, entity_positions.name_male), "
                    "name_female = COALESCE(EXCLUDED.name_female, entity_positions.name_female), "
                    "spouse = COALESCE(EXCLUDED.spouse, entity_positions.spouse), "
                    "spouse_male = COALESCE(EXCLUDED.spouse_male, entity_positions.spouse_male), "
                    "spouse_female = COALESCE(EXCLUDED.spouse_female, entity_positions.spouse_female)")
            counts["entity_positions"] = n
            log.info("  entity_positions: %d", n)

        # Position assignments from legends_plus (merge with position links)
        if plus_data.get("entity_position_assignments"):
            n = await _batch_insert(conn, "hf_position_links",
                ["world_id", "hf_id", "entity_id", "position_id",
                 "start_year", "end_year"],
                plus_data["entity_position_assignments"],
                on_conflict="DO NOTHING")  # bare DO NOTHING: catches partial unique index on NULL start_year
            counts["entity_position_assignments"] = n
            log.info("  entity_position_assignments: %d", n)

        # Written contents enrichment: merge type/pages from legends_plus
        # into written_contents already inserted from legends.xml
        if plus_data["written_contents"]:
            n = await _batch_insert(conn, "written_contents",
                ["id", "world_id", "title", "author_hf_id", "form", "type",
                 "page_start", "page_end", "styles", "details"],
                plus_data["written_contents"],
                on_conflict="(world_id, id) DO UPDATE SET "
                    "type = COALESCE(EXCLUDED.type, written_contents.type), "
                    "page_start = COALESCE(EXCLUDED.page_start, written_contents.page_start), "
                    "page_end = COALESCE(EXCLUDED.page_end, written_contents.page_end), "
                    "styles = COALESCE(EXCLUDED.styles, written_contents.styles), "
                    "details = COALESCE(EXCLUDED.details, written_contents.details)")
            counts["written_contents_plus"] = n
            log.info("  written_contents (plus enrichment): %d", n)

        # World constructions (roads, bridges, tunnels — only in legends_plus)
        if plus_data["world_constructions"]:
            n = await _batch_insert(conn, "world_constructions",
                ["id", "world_id", "name", "type", "coords"],
                plus_data["world_constructions"])
            counts["world_constructions"] = n
            log.info("  world_constructions: %d", n)

        # Art forms (dance, musical, poetic)
        # Merge descriptions from base legends XML (has id+description but no name)
        # into legends_plus data (has id+name but no description)
        if plus_data["art_forms"]:
            base_descs: dict[tuple[str, int], str] = {}
            for form_type, tag in [("dance", "dance_form"), ("musical", "musical_form"),
                                   ("poetic", "poetic_form")]:
                for af in root.findall(f".//{tag}"):
                    af_id = _int(af, "id")
                    desc = _text(af, "description")
                    if af_id is not None and desc:
                        base_descs[(form_type, af_id)] = desc
            if base_descs:
                log.info("  art_forms: merging %d descriptions from base legends",
                         len(base_descs))
                merged = []
                for row in plus_data["art_forms"]:
                    # row = (id, world_id, name, form_type, description, details)
                    af_id, wid, name, ft, existing_desc, details = row
                    desc = existing_desc or base_descs.get((ft, af_id))
                    merged.append((af_id, wid, name, ft, desc, details))
                plus_data["art_forms"] = merged

            n = await _batch_insert(conn, "art_forms",
                ["id", "world_id", "name", "form_type", "description", "details"],
                plus_data["art_forms"])
            counts["art_forms"] = n
            log.info("  art_forms: %d", n)

        # Rivers
        if plus_data["rivers"]:
            n = await _batch_insert(conn, "rivers",
                ["id", "world_id", "name", "name_english", "path", "end_type", "details"],
                plus_data["rivers"])
            counts["rivers"] = n
            log.info("  rivers: %d", n)

        # Entity populations (race composition per entity/civilization)
        if plus_data["entity_populations"]:
            n = await _batch_insert(conn, "entity_populations",
                ["id", "world_id", "race", "count", "civ_id"],
                plus_data["entity_populations"])
            counts["entity_populations"] = n
            log.info("  entity_populations: %d", n)

        # Creature dictionary (creature_raw section — Stage 1.5)
        if plus_data["creature_dictionary"]:
            n = await _batch_insert(conn, "creature_dictionary",
                ["world_id", "creature_id", "name_singular", "name_plural", "flags"],
                plus_data["creature_dictionary"])
            counts["creature_dictionary"] = n
            log.info("  creature_dictionary: %d", n)

        # HF enrichment: update expanded fields from legends_plus
        if plus_data["hf_enrichment"]:
            hf_updated = 0
            for hfid, wid, enrichment in plus_data["hf_enrichment"]:
                sets = []
                params = [wid, hfid]
                idx = 3  # $1=world_id, $2=hfid

                if "spheres" in enrichment:
                    sets.append(f"spheres = ${idx}::TEXT[]")
                    params.append(enrichment["spheres"])
                    idx += 1
                if "active_interactions" in enrichment:
                    sets.append(f"active_interactions = ${idx}::TEXT[]")
                    params.append(enrichment["active_interactions"])
                    idx += 1
                if "goals" in enrichment:
                    sets.append(f"goals = ${idx}::JSONB")
                    params.append(enrichment["goals"])
                    idx += 1
                if "skills" in enrichment:
                    sets.append(f"skills = ${idx}::JSONB")
                    params.append(enrichment["skills"])
                    idx += 1
                if "kills" in enrichment:
                    sets.append(f"kills = ${idx}::JSONB")
                    params.append(enrichment["kills"])
                    idx += 1
                if "whereabouts" in enrichment:
                    sets.append(f"whereabouts = ${idx}::JSONB")
                    params.append(enrichment["whereabouts"])
                    idx += 1
                if "entity_reputations" in enrichment:
                    sets.append(f"entity_reputations = ${idx}::JSONB")
                    params.append(enrichment["entity_reputations"])
                    idx += 1
                if "intrigue_actors" in enrichment:
                    sets.append(f"intrigue_actors = ${idx}::JSONB")
                    params.append(enrichment["intrigue_actors"])
                    idx += 1
                if "used_identities" in enrichment:
                    sets.append(f"used_identities = ${idx}::JSONB")
                    params.append(enrichment["used_identities"])
                    idx += 1
                if "journey_pets" in enrichment:
                    sets.append(f"journey_pets = ${idx}::JSONB")
                    params.append(enrichment["journey_pets"])
                    idx += 1
                if "holds_artifact" in enrichment:
                    sets.append(f"holds_artifact = ${idx}::INTEGER[]")
                    params.append(enrichment["holds_artifact"])
                    idx += 1

                if sets:
                    sql = f"UPDATE historical_figures SET {', '.join(sets)} WHERE world_id = $1 AND id = $2"
                    await conn.execute(sql, *params)
                    hf_updated += 1

            counts["hf_enrichment"] = hf_updated
            log.info("  hf_enrichment: %d HFs updated", hf_updated)

        # Site ownership: update owner_entity_id from legends_plus cur_owner_id
        if plus_data["site_owners"]:
            updated_sites = 0
            for sid, owner_id in plus_data["site_owners"]:
                result = await conn.execute(
                    "UPDATE sites SET owner_entity_id = $1 WHERE id = $2 AND world_id = $3",
                    owner_id, sid, world_id,
                )
                if "UPDATE 1" in result:
                    updated_sites += 1
            counts["site_owners"] = updated_sites
            log.info("  site ownership: %d", updated_sites)

        # Artifact enrichment: writing_id, page_count from legends_plus
        if plus_data["artifact_enrichment"]:
            art_updated = 0
            for aid, wid, details in plus_data["artifact_enrichment"]:
                await conn.execute(
                    "UPDATE artifacts SET details = COALESCE(details, '{}'::jsonb) || $1::jsonb "
                    "WHERE world_id = $2 AND id = $3",
                    details, wid, aid,
                )
                art_updated += 1
            counts["artifact_enrichment"] = art_updated
            log.info("  artifact_enrichment: %d artifacts updated", art_updated)

        # Event enrichment: merge plus-only fields (reason, circumstance, etc.)
        # into the details JSONB of events already inserted from base
        if plus_data["event_enrichment"]:
            ev_sql = ("UPDATE history_events "
                      "SET details = COALESCE(details, '{}'::jsonb) || $1::jsonb "
                      "WHERE world_id = $2 AND id = $3")
            ev_updated = 0
            for batch_start in range(0, len(plus_data["event_enrichment"]), _BATCH_SIZE):
                batch = plus_data["event_enrichment"][batch_start:batch_start + _BATCH_SIZE]
                params = [(enrichment, wid, eid) for eid, wid, enrichment in batch]
                await conn.executemany(ev_sql, params)
                ev_updated += len(batch)
            counts["event_enrichment"] = ev_updated
            log.info("  event_enrichment: %d events updated", ev_updated)

        # Structure enrichment: deity, religion, inhabitant from legends_plus
        if plus_data["structure_enrichment"]:
            struct_sql = ("UPDATE structures "
                          "SET details = COALESCE(details, '{}'::jsonb) || $1::jsonb "
                          "WHERE world_id = $2 AND site_id = $3 AND id = $4")
            struct_params = [
                (enrichment, wid, sid, struct_id)
                for wid, sid, struct_id, enrichment in plus_data["structure_enrichment"]
            ]
            for batch_start in range(0, len(struct_params), _BATCH_SIZE):
                batch = struct_params[batch_start:batch_start + _BATCH_SIZE]
                await conn.executemany(struct_sql, batch)
            counts["structure_enrichment"] = len(struct_params)
            log.info("  structure_enrichment: %d structures updated", len(struct_params))

        # Relationship supplements: occasion_type/site/reason for event_relationships
        # The <event> tag in supplements references event_relationships.event_id
        # (the shared history_event FK), NOT the auto-generated serial id
        if plus_data["relationship_supplements"]:
            sup_params = []
            for wid, event_id, occasion_type, site_id, reason in plus_data["relationship_supplements"]:
                if event_id is None:
                    continue
                supplement = {}
                if occasion_type:
                    supplement["occasion_type"] = occasion_type
                if site_id is not None:
                    supplement["supplement_site_id"] = site_id
                if reason:
                    supplement["supplement_reason"] = reason
                if supplement:
                    sup_params.append((supplement, wid, event_id))
            if sup_params:
                sup_sql = ("UPDATE event_relationships "
                           "SET details = COALESCE(details, '{}'::jsonb) || $1::jsonb "
                           "WHERE world_id = $2 AND event_id = $3")
                await conn.executemany(sup_sql, sup_params)
            counts["relationship_supplements"] = len(sup_params)
            log.info("  relationship_supplements: %d relationships supplemented", len(sup_params))

    # ── Step 6: Update computed counts (scoped to current world) ──────────
    await conn.execute("""
        UPDATE historical_figures hf SET
            event_count = COALESCE(e.cnt, 0)
        FROM (
            SELECT hf_id_1 AS hfid, COUNT(*) AS cnt
            FROM history_events WHERE world_id = $1 AND hf_id_1 IS NOT NULL
            GROUP BY hf_id_1
        ) e
        WHERE hf.world_id = $1 AND hf.id = e.hfid
    """, world_id)
    # Kill count: count victims per slayer (hf_id_2 is the killer in 'hf died' events)
    await conn.execute("""
        UPDATE historical_figures hf SET
            kill_count = k.cnt
        FROM (
            SELECT hf_id_2 AS hfid, COUNT(*) AS cnt
            FROM history_events WHERE world_id = $1 AND event_type = 'hf died' AND hf_id_2 IS NOT NULL
            GROUP BY hf_id_2
        ) k
        WHERE hf.world_id = $1 AND hf.id = k.hfid
    """, world_id)
    # Also count hf_id_2 participation
    await conn.execute("""
        UPDATE historical_figures hf SET
            event_count = hf.event_count + COALESCE(e.cnt, 0)
        FROM (
            SELECT hf_id_2 AS hfid, COUNT(*) AS cnt
            FROM history_events WHERE world_id = $1 AND hf_id_2 IS NOT NULL
            GROUP BY hf_id_2
        ) e
        WHERE hf.world_id = $1 AND hf.id = e.hfid
    """, world_id)
    log.info("Updated event/kill counts on historical_figures")

    # ── Step 7: Post-parse processing pipeline ────────────────────────
    from chronicler.ingest.post_parse import PostParseProcessor
    processor = PostParseProcessor(conn, world_id)
    pipeline_results = await processor.run_all()
    log.info("Post-parse pipeline complete: %s",
             {k: v for k, v in pipeline_results.items() if k != "step_10"})

    # Free memory
    del root, cleaned
    if plus_data:
        del plus_data

    return counts
