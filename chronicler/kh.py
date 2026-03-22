"""Knowledge Horizon — dynamic visibility masking for Chronicler.

The Knowledge Horizon (KH) limits what the storyteller and explorer can see
to what the fortress plausibly knows. It operates in three phases:

Phase 1 (Denizen Registry): Fortress inhabitants are visible.
Phase 2 (Individual Scope): Direct family of visible HFs are visible.
Phase 3 (Geographic + Civilization): Nearby regions/sites and parent civ structure.

Plus event-based revelation rules for live events (wars, caravans, migrants, etc.).
"""

import logging
from typing import Any

import asyncpg

log = logging.getLogger(__name__)


class KnowledgeHorizonEngine:
    """Initialize and expand the knowledge horizon for a fortress world."""

    def __init__(self, pool: asyncpg.Pool, world_id: int):
        self.pool = pool
        self.world_id = world_id

    # ── Full initialization (run all phases) ─────────────────────────

    async def initialize(self) -> dict[str, int]:
        """Run all KH phases and return counts per phase."""
        counts = {}

        # Clear existing KH data for this world
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM knowledge_horizon WHERE world_id = $1",
                self.world_id,
            )

        counts["phase1_denizens"] = await self._phase1_denizen_registry()
        counts["phase2_family"] = await self._phase2_individual_scope()
        counts["phase3_geo"] = await self._phase3_geographic_scope()
        counts["phase3_civ"] = await self._phase3_civilization_scope()
        counts["cav002_nobles"] = await self._cav002_nobles_always_visible()

        # Summary
        async with self.pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT count(*) FROM knowledge_horizon "
                "WHERE world_id = $1 AND visible = TRUE",
                self.world_id,
            )
        counts["total_visible"] = total

        log.info(
            "KH initialized for world %d: %d visible entities",
            self.world_id, total,
        )
        return counts

    # ── Phase 1: Denizen Registry ────────────────────────────────────

    async def _phase1_denizen_registry(self) -> int:
        """Make all fortress denizens (and their HFs) visible."""
        async with self.pool.acquire() as conn:
            # Get all denizens with HF links
            denizens = await conn.fetch(
                "SELECT hf_id FROM fortress_denizens "
                "WHERE world_id = $1 AND hf_id IS NOT NULL AND hf_id > 0",
                self.world_id,
            )

            entries = [
                (self.world_id, "hf", row["hf_id"], "fortress_denizen", "phase1")
                for row in denizens
            ]

            # Also make the fortress site itself visible
            fortress = await conn.fetchrow(
                "SELECT site_id FROM fortress_state WHERE world_id = $1",
                self.world_id,
            )
            if fortress:
                entries.append(
                    (self.world_id, "site", fortress["site_id"],
                     "fortress_site", "phase1")
                )

            count = await self._batch_insert(conn, entries)
            log.info("Phase 1: %d denizen HFs + fortress site visible", count)
            return count

    # ── Phase 2: Individual Scope (direct family) ────────────────────

    async def _phase2_individual_scope(self) -> int:
        """Expand visibility to direct family of all visible HFs."""
        async with self.pool.acquire() as conn:
            # Get all currently visible HFs
            visible_hfs = await conn.fetch(
                "SELECT entity_id FROM knowledge_horizon "
                "WHERE world_id = $1 AND entity_type = 'hf' AND visible = TRUE",
                self.world_id,
            )
            hf_ids = [r["entity_id"] for r in visible_hfs]
            if not hf_ids:
                return 0

            # Get direct family links for all visible HFs at once
            family_types = ("mother", "father", "child", "spouse",
                            "deceased spouse", "former spouse")
            family = await conn.fetch(
                "SELECT DISTINCT target_hf_id, link_type, hf_id "
                "FROM hf_links "
                "WHERE world_id = $1 AND hf_id = ANY($2::int[]) "
                "AND link_type = ANY($3::text[])",
                self.world_id, hf_ids, list(family_types),
            )

            entries = [
                (self.world_id, "hf", row["target_hf_id"],
                 f"family_of_{row['hf_id']}_{row['link_type']}", "phase2")
                for row in family
            ]

            count = await self._batch_insert(conn, entries)
            log.info("Phase 2: %d family members revealed", count)
            return count

    # ── Phase 3a: Geographic Scope ───────────────────────────────────

    async def _phase3_geographic_scope(self) -> int:
        """Make fortress region + nearby regions and their sites visible."""
        async with self.pool.acquire() as conn:
            # Get fortress coordinates
            fortress = await conn.fetchrow(
                "SELECT s.coord_x, s.coord_y, fs.site_id "
                "FROM fortress_state fs "
                "JOIN sites s ON s.world_id = fs.world_id AND s.id = fs.site_id "
                "WHERE fs.world_id = $1",
                self.world_id,
            )
            if not fortress:
                return 0

            fx, fy = fortress["coord_x"], fortress["coord_y"]

            # Geographic proximity: regions within 10 tiles of fortress
            # Regions have coord arrays, but we can also use sites as proxies.
            # Simple approach: reveal all sites within radius and their regions.
            radius = 10
            nearby_sites = await conn.fetch(
                "SELECT id, coord_x, coord_y FROM sites "
                "WHERE world_id = $1 "
                "AND coord_x BETWEEN $2 AND $3 "
                "AND coord_y BETWEEN $4 AND $5",
                self.world_id, fx - radius, fx + radius, fy - radius, fy + radius,
            )

            entries = []
            for site in nearby_sites:
                entries.append(
                    (self.world_id, "site", site["id"],
                     "geographic_proximity", "phase3_geo")
                )

            # Regions use pipe-delimited "x,y" coords (some may be empty).
            # Find regions containing any coord tile within radius.
            nearby_regions = await conn.fetch(
                "SELECT DISTINCT r.id FROM regions r, "
                "unnest(string_to_array(r.coords, '|')) AS coord "
                "WHERE r.world_id = $1 "
                "AND coord LIKE '%,%' "
                "AND split_part(coord, ',', 1)::int BETWEEN $2 AND $3 "
                "AND split_part(coord, ',', 2)::int BETWEEN $4 AND $5",
                self.world_id, fx - radius, fx + radius, fy - radius, fy + radius,
            )

            for region in nearby_regions:
                entries.append(
                    (self.world_id, "region", region["id"],
                     "geographic_proximity", "phase3_geo")
                )

            count = await self._batch_insert(conn, entries)
            log.info("Phase 3a: %d nearby sites + regions revealed (radius=%d)",
                     count, radius)
            return count

    # ── Phase 3b: Civilization Scope ─────────────────────────────────

    async def _phase3_civilization_scope(self) -> int:
        """Make parent civilization, its sites, and structure visible."""
        async with self.pool.acquire() as conn:
            # Get fortress governing entity and parent civ
            fortress = await conn.fetchrow(
                "SELECT site_id FROM fortress_state WHERE world_id = $1",
                self.world_id,
            )
            if not fortress:
                return 0

            # Find who governs and founded the fortress site
            site_links = await conn.fetch(
                "SELECT entity_id, link_type FROM entity_site_links "
                "WHERE world_id = $1 AND site_id = $2",
                self.world_id, fortress["site_id"],
            )

            entries = []
            civ_ids = set()

            for link in site_links:
                eid = link["entity_id"]
                entries.append(
                    (self.world_id, "entity", eid,
                     f"fortress_{link['link_type']}", "phase3_civ")
                )

                # Find parent civ via entity_entity_links
                parents = await conn.fetch(
                    "SELECT target_entity_id FROM entity_entity_links "
                    "WHERE world_id = $1 AND source_entity_id = $2 "
                    "AND link_type = 'PARENT'",
                    self.world_id, eid,
                )
                for p in parents:
                    civ_ids.add(p["target_entity_id"])
                    entries.append(
                        (self.world_id, "entity", p["target_entity_id"],
                         f"parent_civ_of_{eid}", "phase3_civ")
                    )

                # The entity itself might be a civ
                entity = await conn.fetchrow(
                    "SELECT type FROM entities WHERE world_id = $1 AND id = $2",
                    self.world_id, eid,
                )
                if entity and entity["type"] == "civilization":
                    civ_ids.add(eid)

            # Reveal all sites owned by known civs
            if civ_ids:
                civ_sites = await conn.fetch(
                    "SELECT DISTINCT site_id FROM entity_site_links "
                    "WHERE world_id = $1 AND entity_id = ANY($2::int[])",
                    self.world_id, list(civ_ids),
                )
                for cs in civ_sites:
                    entries.append(
                        (self.world_id, "site", cs["site_id"],
                         "civ_owned_site", "phase3_civ")
                    )

                # Reveal child entities of civs (site governments etc.)
                children = await conn.fetch(
                    "SELECT target_entity_id FROM entity_entity_links "
                    "WHERE world_id = $1 AND source_entity_id = ANY($2::int[]) "
                    "AND link_type = 'CHILD'",
                    self.world_id, list(civ_ids),
                )
                for ch in children:
                    entries.append(
                        (self.world_id, "entity", ch["target_entity_id"],
                         "civ_child_entity", "phase3_civ")
                    )

            count = await self._batch_insert(conn, entries)
            log.info("Phase 3b: %d civ entities/sites revealed", count)
            return count

    # ── CAV-002: Nobles always visible ───────────────────────────────

    async def _cav002_nobles_always_visible(self) -> int:
        """Make all HFs holding positions in visible entities visible."""
        async with self.pool.acquire() as conn:
            # Get all visible entities
            visible_entities = await conn.fetch(
                "SELECT entity_id FROM knowledge_horizon "
                "WHERE world_id = $1 AND entity_type = 'entity' AND visible = TRUE",
                self.world_id,
            )
            if not visible_entities:
                return 0

            ent_ids = [r["entity_id"] for r in visible_entities]

            # HFs with active position links (end_year IS NULL = still serving)
            position_holders = await conn.fetch(
                "SELECT DISTINCT hf_id FROM hf_position_links "
                "WHERE world_id = $1 AND entity_id = ANY($2::int[]) "
                "AND end_year IS NULL",
                self.world_id, ent_ids,
            )

            entries = [
                (self.world_id, "hf", row["hf_id"],
                 "noble_cav002", "cav002")
                for row in position_holders
            ]

            count = await self._batch_insert(conn, entries)
            log.info("CAV-002: %d noble position holders revealed", count)
            return count

    # ── Event-based revelation ───────────────────────────────────────

    async def process_revelation_event(self, event: dict) -> int:
        """Process a live event for KH revelations. Returns count of new reveals."""
        event_type = event.get("type", "")
        data = event.get("data", {})
        details = data if isinstance(data, dict) else {}

        entries = []

        if event_type == "invasion":
            # Invasions reveal attacking entity
            attacker = details.get("attacker_entity_id")
            if attacker:
                entries.append(
                    (self.world_id, "entity", attacker,
                     "invasion_revelation", "event")
                )

        elif event_type == "caravan":
            source_eid = details.get("source_entity_id")
            source_sid = details.get("source_site_id")
            if source_eid:
                entries.append(
                    (self.world_id, "entity", source_eid,
                     "caravan_contact", "event")
                )
            if source_sid:
                entries.append(
                    (self.world_id, "site", source_sid,
                     "caravan_origin", "event")
                )

        elif event_type == "migrant":
            origin_sid = details.get("origin_site_id")
            if origin_sid:
                entries.append(
                    (self.world_id, "site", origin_sid,
                     "migrant_knowledge", "event")
                )

        elif event_type == "artifact_found":
            artifact_id = details.get("artifact_id")
            if artifact_id:
                entries.append(
                    (self.world_id, "artifact", artifact_id,
                     "artifact_discovery", "event")
                )

        if not entries:
            return 0

        async with self.pool.acquire() as conn:
            count = await self._batch_insert(conn, entries)
            if count > 0:
                log.info("Event revelation: %d new entities from %s",
                         count, event_type)
            return count

    # ── CAV-001: Organization membership propagation ─────────────────

    async def expand_org_membership(
        self, entity_id: int, entity_type_str: str
    ) -> int:
        """Propagate visibility through organization membership.

        Rules per CAV-001:
        - cults: full membership revealed
        - squads: chain-of-command
        - guilds: same-site members only
        - religion: nearby temples/worshippers
        - civilization: NO propagation (too broad)
        """
        async with self.pool.acquire() as conn:
            entity = await conn.fetchrow(
                "SELECT type FROM entities WHERE world_id = $1 AND id = $2",
                self.world_id, entity_id,
            )
            if not entity:
                return 0

            etype = entity["type"]
            entries = []

            if etype == "civilization":
                # CAV-001: No automatic propagation for civilizations
                return 0

            # For all other org types, reveal members
            members = await conn.fetch(
                "SELECT hf_id FROM hf_entity_links "
                "WHERE world_id = $1 AND entity_id = $2",
                self.world_id, entity_id,
            )

            if etype in ("cult", "performancetroupe", "militaryunit"):
                # Full membership
                for m in members:
                    entries.append(
                        (self.world_id, "hf", m["hf_id"],
                         f"member_of_{entity_id}", "cav001")
                    )
            elif etype == "guild":
                # Same-site members only — need fortress site_id
                fortress = await conn.fetchrow(
                    "SELECT site_id FROM fortress_state WHERE world_id = $1",
                    self.world_id,
                )
                if fortress:
                    site_members = await conn.fetch(
                        "SELECT DISTINCT hel.hf_id "
                        "FROM hf_entity_links hel "
                        "JOIN hf_site_links hsl "
                        "  ON hsl.world_id = hel.world_id AND hsl.hf_id = hel.hf_id "
                        "WHERE hel.world_id = $1 AND hel.entity_id = $2 "
                        "AND hsl.site_id = $3",
                        self.world_id, entity_id, fortress["site_id"],
                    )
                    for m in site_members:
                        entries.append(
                            (self.world_id, "hf", m["hf_id"],
                             f"guild_same_site_{entity_id}", "cav001")
                        )

            count = await self._batch_insert(conn, entries)
            return count

    # ── Utility ──────────────────────────────────────────────────────

    async def _batch_insert(
        self, conn: asyncpg.Connection,
        entries: list[tuple[int, str, int, str, str]],
    ) -> int:
        """Insert KH entries with ON CONFLICT DO NOTHING. Returns rows inserted."""
        if not entries:
            return 0

        count = 0
        for world_id, etype, eid, reason, revealed_by in entries:
            result = await conn.execute(
                "INSERT INTO knowledge_horizon "
                "(world_id, entity_type, entity_id, visible, reason, revealed_by) "
                "VALUES ($1, $2, $3, TRUE, $4, $5) "
                "ON CONFLICT (world_id, entity_type, entity_id) DO NOTHING",
                world_id, etype, eid, reason, revealed_by,
            )
            # asyncpg returns 'INSERT 0 1' or 'INSERT 0 0'
            if result.endswith("1"):
                count += 1

        return count

    # ── Stats ────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Return KH visibility statistics."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT entity_type, count(*) as cnt "
                "FROM knowledge_horizon "
                "WHERE world_id = $1 AND visible = TRUE "
                "GROUP BY entity_type ORDER BY entity_type",
                self.world_id,
            )
            by_type = {r["entity_type"]: r["cnt"] for r in rows}

            # Compare with totals
            totals = {}
            for etype, table in [
                ("hf", "historical_figures"),
                ("entity", "entities"),
                ("site", "sites"),
                ("region", "regions"),
                ("artifact", "artifacts"),
            ]:
                total = await conn.fetchval(
                    f"SELECT count(*) FROM {table} WHERE world_id = $1",
                    self.world_id,
                )
                totals[etype] = total

            return {
                "world_id": self.world_id,
                "visible": by_type,
                "total": totals,
                "coverage_pct": {
                    k: round(by_type.get(k, 0) / totals[k] * 100, 1)
                    if totals[k] > 0 else 0
                    for k in totals
                },
            }


# ── LLM Knowledge Horizon prompt addendum (CAV-007) ─────────────────

KH_SYSTEM_PROMPT = """## Knowledge Horizon
You are limited to knowledge that the fortress plausibly possesses.
You know about:
- All inhabitants of the fortress and their direct families
- Your parent civilization and its public figures
- Civilizations you have had contact with (trade, war, diplomacy)
- Geographic regions near the fortress
- Events that have directly affected the fortress

You do NOT know about:
- Distant civilizations with no contact
- Events in far-off lands
- Historical figures unconnected to your civilization
- Secret identities (unless revealed in-game)

If asked about something outside your knowledge, say:
"The fortress has no knowledge of this."
Treat this as an in-world limitation, not a system error.
"""
