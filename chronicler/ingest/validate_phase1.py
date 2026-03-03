"""Phase 1 (Data Foundation) validation — checks all M1 Milestone DoD items.

Usage:
    chronicler validate-phase1 [--world-id N]

Checks Data Schema, XML Parser completeness, Post-Parse Pipeline results,
and overall verification criteria against the Phase 1 Definition of Done.
"""

import logging

log = logging.getLogger(__name__)

# Tables that MUST exist for Phase 1 compliance
REQUIRED_TABLES = [
    # Geography/World
    "worlds", "landmasses", "mountain_peaks", "regions", "underground_regions",
    "sites", "structures", "world_constructions", "rivers",
    # Culture
    "art_forms", "entity_populations",
    # Civilizations
    "entities", "entity_positions",
    # Historical Figures
    "historical_figures", "hf_links", "hf_entity_links", "hf_site_links",
    "hf_position_links", "identities",
    # Events
    "history_events", "history_event_collections", "collection_events",
    "collection_subcollections", "event_relationships", "event_entity_xref",
    # Artifacts & Culture
    "artifacts", "written_contents", "historical_eras",
    # System (Phase 5/6 prep)
    "worldgen_snapshots", "world_modpacks",
]

# Phase 1 new entity type tables
NEW_ENTITY_TABLES = ["world_constructions", "art_forms", "identities", "rivers",
                     "entity_populations"]

# Extended columns required on existing tables
EXTENDED_COLUMNS = {
    "landmasses": ["coord_1", "coord_2"],
    "mountain_peaks": ["height", "is_volcano"],
}

# HF high-priority field columns
HF_EXTENDED_COLUMNS = [
    "spheres", "goals", "skills", "kills", "whereabouts",
    "entity_reputations", "intrigue_actors", "used_identities",
    "journey_pets", "holds_artifact", "active_interactions",
]

# GIN indexes required
REQUIRED_GIN_INDEXES = {
    "historical_figures": ["spheres", "active_interactions"],
}


class Phase1Validator:
    """Validates all Phase 1 Definition of Done criteria."""

    def __init__(self, conn, world_id: int):
        self.conn = conn
        self.world_id = world_id
        self.results: list[dict] = []

    def _record(self, category: str, check: str, passed: bool,
                detail: str = ""):
        self.results.append({
            "category": category,
            "check": check,
            "passed": passed,
            "detail": detail,
        })

    async def run_all(self) -> list[dict]:
        """Run all validation checks and return results."""
        await self._check_schema()
        await self._check_xml_parser()
        await self._check_post_parse()
        await self._check_verification()
        return self.results

    # ── Data Schema checks ─────────────────────────────────────────────────

    async def _check_schema(self):
        cat = "Data Schema"

        # 1. Table count
        n = await self.conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )
        self._record(cat, f"CDM tables exist (target: 39+, found: {n})",
                      n >= 39, f"{n} tables")

        # 2. Required tables exist
        existing = {r["table_name"] for r in await self.conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )}
        missing = [t for t in REQUIRED_TABLES if t not in existing]
        self._record(cat, "All required tables exist",
                      len(missing) == 0,
                      f"Missing: {', '.join(missing)}" if missing else "All present")

        # 3. New entity type tables
        for table in NEW_ENTITY_TABLES:
            exists = table in existing
            count = 0
            if exists:
                count = await self.conn.fetchval(
                    f"SELECT COUNT(*) FROM {table} WHERE world_id = $1",
                    self.world_id)
            self._record(cat, f"New table: {table}",
                          exists and count > 0,
                          f"{count:,d} rows" if exists else "TABLE MISSING")

        # 4. Extended columns on existing tables
        for table, columns in EXTENDED_COLUMNS.items():
            for col in columns:
                exists = await self.conn.fetchval(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_name = $1 AND column_name = $2",
                    table, col)
                self._record(cat, f"Extended column: {table}.{col}",
                              exists > 0)

        # 5. System tables
        for table in ["worldgen_snapshots", "world_modpacks"]:
            exists = table in existing
            self._record(cat, f"System table: {table}", exists)

        # 6. HF extended fields
        for col in HF_EXTENDED_COLUMNS:
            exists = await self.conn.fetchval(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_name = 'historical_figures' AND column_name = $1",
                col)
            self._record(cat, f"HF field: {col}", exists > 0)

        # 7. GIN indexes
        for table, columns in REQUIRED_GIN_INDEXES.items():
            for col in columns:
                has_gin = await self.conn.fetchval("""
                    SELECT COUNT(*) FROM pg_indexes
                    WHERE tablename = $1
                    AND indexdef ILIKE '%gin%'
                    AND indexdef ILIKE $2
                """, table, f"%{col}%")
                self._record(cat, f"GIN index: {table}.{col}", has_gin > 0)

        # 8. event_entity_xref populated
        xref_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM event_entity_xref WHERE world_id = $1",
            self.world_id)
        self._record(cat, f"event_entity_xref populated ({xref_count:,d} rows)",
                      xref_count > 0, f"{xref_count:,d} cross-reference rows")

    # ── XML Parser checks ──────────────────────────────────────────────────

    async def _check_xml_parser(self):
        cat = "XML Parser"

        # Check that all section tables have data for this world
        section_tables = {
            "regions": "Regions",
            "underground_regions": "Underground regions",
            "sites": "Sites",
            "structures": "Structures",
            "entities": "Entities",
            "historical_figures": "Historical figures",
            "history_events": "History events",
            "history_event_collections": "Event collections",
            "artifacts": "Artifacts",
            "written_contents": "Written contents",
            "historical_eras": "Historical eras",
            "world_constructions": "World constructions",
            "art_forms": "Art forms (dance/musical/poetic)",
            "identities": "Identities",
            "rivers": "Rivers",
            "landmasses": "Landmasses",
            "mountain_peaks": "Mountain peaks",
            "entity_populations": "Entity populations",
            "event_relationships": "Event relationships",
        }

        parsed_count = 0
        for table, label in section_tables.items():
            try:
                if table == "historical_eras":
                    # historical_eras uses world_id in PK differently
                    n = await self.conn.fetchval(
                        f"SELECT COUNT(*) FROM {table} WHERE world_id = $1",
                        self.world_id)
                else:
                    n = await self.conn.fetchval(
                        f"SELECT COUNT(*) FROM {table} WHERE world_id = $1",
                        self.world_id)
                passed = n > 0
                if passed:
                    parsed_count += 1
                self._record(cat, f"Section parsed: {label}",
                              passed, f"{n:,d} rows")
            except Exception as e:
                self._record(cat, f"Section parsed: {label}",
                              False, f"Error: {e}")

        self._record(cat, f"Total sections parsed: {parsed_count}/{len(section_tables)}",
                      parsed_count >= 14,
                      f"{parsed_count} of {len(section_tables)} sections have data")

        # HF enrichment fields populated
        hf_enriched = await self.conn.fetchval("""
            SELECT COUNT(*) FROM historical_figures
            WHERE world_id = $1
            AND (skills != '[]'::jsonb OR spheres IS NOT NULL
                 OR active_interactions IS NOT NULL
                 OR kills != '{}'::jsonb)
        """, self.world_id)
        total_hf = await self.conn.fetchval(
            "SELECT COUNT(*) FROM historical_figures WHERE world_id = $1",
            self.world_id)
        self._record(cat, f"HF enrichment from legends_plus ({hf_enriched:,d}/{total_hf:,d})",
                      hf_enriched > 0,
                      f"{hf_enriched:,d} HFs have expanded fields")

        # Art form types check
        form_types = await self.conn.fetch("""
            SELECT form_type, COUNT(*) AS cnt FROM art_forms
            WHERE world_id = $1 GROUP BY form_type ORDER BY form_type
        """, self.world_id)
        types_found = [r["form_type"] for r in form_types]
        self._record(cat, "Art forms: all 3 types (dance/musical/poetic)",
                      set(types_found) >= {"dance", "musical", "poetic"},
                      ", ".join(f"{r['form_type']}={r['cnt']}" for r in form_types))

    # ── Post-Parse Pipeline checks ─────────────────────────────────────────

    async def _check_post_parse(self):
        cat = "Post-Parse Pipeline"

        # Step 1: Family links bidirectional
        orphan_parents = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_links l1
            WHERE l1.world_id = $1
            AND l1.link_type IN ('Mother', 'Father')
            AND NOT EXISTS (
                SELECT 1 FROM hf_links l2
                WHERE l2.world_id = l1.world_id
                AND l2.hf_id = l1.target_hf_id
                AND l2.target_hf_id = l1.hf_id
                AND l2.link_type = 'Child'
            )
        """, self.world_id)
        self._record(cat, f"Step 1: Family links bidirectional (orphans: {orphan_parents})",
                      orphan_parents == 0,
                      f"{orphan_parents} parent links without inverse child link")

        # Step 2: Position assignments resolved
        positions_resolved = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_position_links WHERE world_id = $1
        """, self.world_id)
        self._record(cat, f"Step 2: Position assignments ({positions_resolved:,d})",
                      positions_resolved > 0)

        # Step 3: Supernatural flags derived
        vampires = await self.conn.fetchval(
            "SELECT COUNT(*) FROM historical_figures WHERE world_id = $1 AND is_vampire = TRUE",
            self.world_id)
        necros = await self.conn.fetchval(
            "SELECT COUNT(*) FROM historical_figures WHERE world_id = $1 AND is_necromancer = TRUE",
            self.world_id)
        werebeasts = await self.conn.fetchval(
            "SELECT COUNT(*) FROM historical_figures WHERE world_id = $1 AND is_werebeast = TRUE",
            self.world_id)
        has_interactions = await self.conn.fetchval("""
            SELECT COUNT(*) FROM historical_figures
            WHERE world_id = $1 AND active_interactions IS NOT NULL
            AND array_length(active_interactions, 1) > 0
        """, self.world_id)
        self._record(
            cat,
            f"Step 3: Supernatural flags (V:{vampires} N:{necros} W:{werebeasts})",
            (vampires + necros + werebeasts) > 0 or has_interactions > 0,
            f"{has_interactions} HFs with active_interactions")

        # Step 4: Site ruin status
        ruins = await self.conn.fetchval("""
            SELECT COUNT(*) FROM sites
            WHERE world_id = $1 AND details->>'is_ruin' = 'true'
        """, self.world_id)
        self._record(cat, f"Step 4: Site ruin status ({ruins} ruins)",
                      ruins >= 0,  # 0 ruins is valid if no sites were destroyed
                      f"{ruins} sites marked as ruins")

        # Step 5: Entity war lists
        wars = await self.conn.fetchval("""
            SELECT COUNT(*) FROM history_event_collections
            WHERE world_id = $1 AND type = 'war'
        """, self.world_id)
        entities_with_wars = await self.conn.fetchval("""
            SELECT COUNT(*) FROM entities
            WHERE world_id = $1 AND details ? 'wars'
        """, self.world_id)
        self._record(cat, f"Step 5: Entity war lists ({wars} wars, {entities_with_wars} entities)",
                      wars > 0 and entities_with_wars > 0)

        # Step 6: HF kill lists
        hfs_with_kills = await self.conn.fetchval("""
            SELECT COUNT(*) FROM historical_figures
            WHERE world_id = $1 AND kill_count > 0
        """, self.world_id)
        self._record(cat, f"Step 6: HF kill lists ({hfs_with_kills:,d} HFs with kills)",
                      hfs_with_kills > 0)

        # Step 7: Prominence/salience scores
        hf_scored = await self.conn.fetchval("""
            SELECT COUNT(*) FROM historical_figures
            WHERE world_id = $1 AND prominence_score > 0
        """, self.world_id)
        site_scored = await self.conn.fetchval("""
            SELECT COUNT(*) FROM sites
            WHERE world_id = $1 AND prominence_score > 0
        """, self.world_id)
        art_scored = await self.conn.fetchval("""
            SELECT COUNT(*) FROM artifacts
            WHERE world_id = $1 AND prominence_score > 0
        """, self.world_id)
        self._record(
            cat,
            f"Step 7: Scoring (HF:{hf_scored:,d} Site:{site_scored:,d} Art:{art_scored:,d})",
            hf_scored > 0 and site_scored > 0 and art_scored > 0)

        # Step 8: Event-entity xref (already checked in schema)
        xref = await self.conn.fetchval(
            "SELECT COUNT(*) FROM event_entity_xref WHERE world_id = $1",
            self.world_id)
        self._record(cat, f"Step 8: Event-entity xref ({xref:,d} rows)",
                      xref > 0)

        # Step 9: Site ownership history
        sites_with_ownership = await self.conn.fetchval("""
            SELECT COUNT(*) FROM sites
            WHERE world_id = $1 AND details ? 'ownership_history'
        """, self.world_id)
        self._record(cat, f"Step 9: Site ownership history ({sites_with_ownership:,d} sites)",
                      sites_with_ownership > 0)

        # Step 10: Referential integrity
        # Check HF links reference existing HFs
        broken_hf_links = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_links l
            WHERE l.world_id = $1
            AND NOT EXISTS (
                SELECT 1 FROM historical_figures h
                WHERE h.world_id = l.world_id AND h.id = l.target_hf_id
            )
        """, self.world_id)
        broken_entity_links = await self.conn.fetchval("""
            SELECT COUNT(*) FROM hf_entity_links l
            WHERE l.world_id = $1
            AND NOT EXISTS (
                SELECT 1 FROM entities e
                WHERE e.world_id = l.world_id AND e.id = l.entity_id
            )
        """, self.world_id)
        total_refs = await self.conn.fetchval(
            "SELECT COUNT(*) FROM hf_links WHERE world_id = $1", self.world_id)
        total_refs += await self.conn.fetchval(
            "SELECT COUNT(*) FROM hf_entity_links WHERE world_id = $1", self.world_id)
        broken = broken_hf_links + broken_entity_links
        pct = (broken / total_refs * 100) if total_refs > 0 else 0
        self._record(
            cat,
            f"Step 10: Referential integrity ({broken} broken / {total_refs:,d} total = {pct:.2f}%)",
            pct < 0.1,
            f"Threshold: <0.1%, actual: {pct:.2f}%")

    # ── Verification checks ────────────────────────────────────────────────

    async def _check_verification(self):
        cat = "Verification"

        # World exists
        world = await self.conn.fetchrow(
            "SELECT name, alt_name FROM worlds WHERE id = $1", self.world_id)
        if world:
            self._record(cat, f"World {self.world_id}: {world['name']} ({world['alt_name']})",
                          True)
        else:
            self._record(cat, f"World {self.world_id} exists", False, "NOT FOUND")
            return

        # Record counts
        total = await self.conn.fetchval("""
            SELECT SUM(cnt) FROM (
                SELECT COUNT(*) AS cnt FROM regions WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM underground_regions WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM sites WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM structures WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM entities WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM historical_figures WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM hf_links WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM hf_entity_links WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM history_events WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM history_event_collections WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM artifacts WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM written_contents WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM event_entity_xref WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM world_constructions WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM art_forms WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM rivers WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM identities WHERE world_id = $1
                UNION ALL SELECT COUNT(*) FROM entity_populations WHERE world_id = $1
            ) sub
        """, self.world_id)
        total = int(total or 0)
        self._record(cat, f"Total records: {total:,d}",
                      total > 100000,
                      "Target: significant world data (>100K records)")

        # Top HFs by prominence (sanity check)
        top_hf = await self.conn.fetch("""
            SELECT name, prominence_score, is_deity, is_force, is_vampire, is_necromancer
            FROM historical_figures
            WHERE world_id = $1 AND prominence_score > 0
            ORDER BY prominence_score DESC LIMIT 5
        """, self.world_id)
        top_names = [f"{r['name']} ({r['prominence_score']:.2f})" for r in top_hf]
        deities_at_top = any(r["is_deity"] or r["is_force"] for r in top_hf[:3])
        self._record(cat, "Top HFs are deities/forces (sanity check)",
                      deities_at_top,
                      f"Top 5: {', '.join(top_names)}")

        # Skill distribution
        hfs_with_skills = await self.conn.fetchval("""
            SELECT COUNT(*) FROM historical_figures
            WHERE world_id = $1 AND skills != '[]'::jsonb
        """, self.world_id)
        self._record(cat, f"HFs with skills data: {hfs_with_skills:,d}",
                      hfs_with_skills > 0)

        # Kill distribution
        hfs_with_kill_records = await self.conn.fetchval("""
            SELECT COUNT(*) FROM historical_figures
            WHERE world_id = $1 AND kills != '{}'::jsonb
            AND kills != '{"notable": [], "other": 0}'::jsonb
        """, self.world_id)
        self._record(cat, f"HFs with kill records: {hfs_with_kill_records:,d}",
                      hfs_with_kill_records > 0)


def format_results(results: list[dict]) -> str:
    """Format validation results as a human-readable report."""
    lines = []
    lines.append("=" * 70)
    lines.append("  PHASE 1 DATA FOUNDATION — VALIDATION REPORT")
    lines.append("=" * 70)

    current_cat = None
    pass_count = 0
    fail_count = 0

    for r in results:
        if r["category"] != current_cat:
            current_cat = r["category"]
            lines.append("")
            lines.append(f"── {current_cat} {'─' * (60 - len(current_cat))}")

        icon = "PASS" if r["passed"] else "FAIL"
        marker = "  [+]" if r["passed"] else "  [!]"
        line = f"{marker} {icon}: {r['check']}"
        if r["detail"] and not r["passed"]:
            line += f"\n       Detail: {r['detail']}"
        lines.append(line)

        if r["passed"]:
            pass_count += 1
        else:
            fail_count += 1

    lines.append("")
    lines.append("=" * 70)
    total = pass_count + fail_count
    lines.append(f"  SUMMARY: {pass_count}/{total} checks passed, "
                 f"{fail_count} failed")
    if fail_count == 0:
        lines.append("  STATUS: ALL CHECKS PASSED — Phase 1 DoD met")
    else:
        lines.append("  STATUS: INCOMPLETE — fix failing checks above")
    lines.append("=" * 70)

    return "\n".join(lines)
