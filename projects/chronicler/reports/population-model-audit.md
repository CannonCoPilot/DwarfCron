# Population Model Audit Report

**Date:** 2026-03-06
**Scope:** Critical review of population, member, and resident counting across the Chronicler Explorer
**Case study:** the brave kingdom (1007) -> the nourishing league (1525) -> pocketdumplings (621)

---

## 1. Executive Summary

The Chronicler's population counting system operates across three tiers of increasing granularity: DF-native aggregate counts (`entity_populations`), organizational membership (`hf_entity_links`), and physical site presence (`hf_site_links`). Investigation reveals **one confirmed bug**, **two systemic coverage gaps**, and **three conceptual inconsistencies** that produce confusing or misleading numbers across the Explorer UI.

The most significant finding: **the Population column in the Sites tab of a site government's full-page view always shows 0**, because the query that populates per-entity population counts (`sg_populations`) only queries *child* site governments, never the entity being viewed when that entity is itself a site government.

---

## 2. The Three Tiers — Definitions and Data

### Tier 1: `entity_populations` (DF-Native Aggregate Counts)

| Property | Value |
|---|---|
| **What it counts** | Race-level population totals per civilization, as recorded by DF in legends XML |
| **Granularity** | Race-level aggregates (e.g., "DWARF: 17,097 for civ 1007"), NOT individual HFs |
| **Total for world 1** | 1,663,758 |
| **Coverage** | Only applies to entities of type `civilization` (810 entities); site governments (1,890 entities) have NO entries |
| **Used in UI** | Statistics tab entity_populations summary; not currently shown elsewhere |

**Assessment:** This tier represents DF's own census of each civilization's total racial population, including individuals who may never appear as named historical figures. It is fundamentally incommensurate with tiers 2 and 3, which count named HFs only. The 100x+ difference between entity_populations (1.66M) and hf_entity_links living members (15.4K) reflects this — most population members are anonymous.

### Tier 2: `hf_entity_links` (Organizational Membership)

| Property | Value |
|---|---|
| **What it counts** | Individual HF-to-entity associations with a `link_type` |
| **Link types** | `member` (92,204), `former member` (69,703), `enemy` (26,434), `former prisoner` (3,886), `criminal` (1,147), `prisoner` (302), `former slave` (27), `slave` (8) |
| **Unique HFs with links** | 47,074 of 48,273 (97.5%) |
| **Living members (deduplicated)** | 15,373 (link_type='member' AND death_year IS NULL) |

**Assessment:** This is the primary membership dimension. It captures organizational affiliation, not physical presence. A figure marked as `member` of entity 1525 may live at site 621 or may have no site link at all. The distinction between `member` and `former member` is behavioral — `former member` means the HF actively left or was expelled; dying does NOT change link_type from `member` to `former member`.

### Tier 3: `hf_site_links` (Physical Site Presence)

| Property | Value |
|---|---|
| **What it counts** | Individual HF-to-site associations indicating physical attachment |
| **Link types** | `home structure` (682), `occupation` (632), `seat of power` (502), `lair` (252), `hangout` (4), `home site building` (2) |
| **Total links** | 2,074 |
| **Unique HFs with links** | 2,066 of 48,273 (4.3%) |
| **Living with links** | 1,661 |

**Assessment:** This tier is extremely sparse. Only 4.3% of all HFs and 9.7% of living HFs have any site link. This is by design in DF — site links represent specific structural associations (dwelling, workplace, throne), not mere presence. A dwarf citizen of a fortress has an entity link but may not have a site link unless they hold a specific role or own a structure.

### Cross-Reference: Orthogonality

| Category | Count |
|---|---|
| HFs with both entity AND site links | 2,054 |
| HFs with entity links only | 45,020 |
| HFs with site links only | 12 |
| HFs with neither | 1,187 (2.5%) |

**Key takeaway:** Entity membership and site presence are nearly independent dimensions. 95.7% of HFs have no site link. The 12 HFs with site links but no entity links are likely edge cases (e.g., megabeasts with lairs but no organizational affiliation).

---

## 3. Confirmed Issues

### Issue 1: Sites Tab Pop.=0 for Site Government Entities (BUG)

**Severity:** High
**Location:** `/chronicler/api/routes/civilizations.py:140-150` (query) and `:377-431` (non-civ site_govts assembly)

**Symptom:** When viewing entity 1525 (type=sitegovernment) at `/explorer/entity/1525?world_id=1#tab=sites`, the Sites tab shows Pop.=0 for its single site (pocketdumplings), despite the Overview tile correctly showing Population=101.

**Root cause:** The `sg_populations` dict is populated by querying only `sg_ids` (child site governments found via JSONB PARENT links). When the viewed entity IS a site government:
- `sg_ids` is empty (no children)
- `sg_populations` is therefore empty
- At line 427: `sg_populations.get(entity_id, 0)` returns 0 because `entity_id` was never queried into `sg_populations`

Meanwhile, `total_population` (Overview tile) uses `all_entity_ids = [entity_id] + sg_ids = [1525]` at line 233, which correctly queries the entity's own members. The inconsistency is that `sg_populations` excludes the entity's own ID while `all_entity_ids` includes it.

**Evidence:**
```
API response for entity 1525:
  total_population: 101   (correct — from all_entity_ids query)
  site_govts[0].population: 0   (wrong — from sg_populations query)
```

**Impact:** Every site government entity (1,890 entities) shows Pop.=0 in its own Sites tab.

### Issue 2: Statistics Divergence Table Shows Correct Data, But "All Zeros" Perception

**Severity:** Medium (UX, not data)
**Location:** `/chronicler/api/routes/statistics.py:191-230`

**Symptom:** User reported "Residents column all 0s." Investigation shows this is only true for the top entries (sorted by population descending), which are large civilizations whose sites have high entity membership but zero site links. The data IS correct — most sites genuinely have 0 hf_site_links.

**Evidence:**
```
mirthfultold:    pop=864, res=0   (correct — no hf_site_links for this site)
pocketdumplings: pop=101, res=23  (correct — both exist)
```

The divergence table shows 50 rows sorted by population DESC. The top rows are large civ sites with hundreds of members but no site links (because DF only generates site links for a small subset of HFs). Sites with actual residents appear further down.

**Root cause:** Not a bug, but a **presentation issue**. The default sort (by population DESC) front-loads sites where the divergence is 100% one-sided, creating the impression that ALL values are 0.

### Issue 3: entity_populations Not Linked to Site Governments (DATA GAP)

**Severity:** Medium
**Location:** DB table `entity_populations`

**Symptom:** `entity_populations` records only exist for entities of type `civilization`. Site governments (1,890 entities) have zero records. This means DF's own aggregate population counts exist only at the civilization level, not the site government level.

**Evidence:**
```
entity_populations civ_id=1525: []     (no records — site government)
entity_populations civ_id=1007: 17,097 (1 race — civilization)
```

**Root cause:** DF legends XML only exports `<entity_population>` elements under civilizations, not site governments. This is a DF data limitation, not a Chronicler bug. However, it means Tier 1 data cannot be used for site-level or site-government-level population display.

---

## 4. Conceptual Assessment

### 4.1: Is the system intuitively logical?

**For:**
- The three terms (Population, Members, Residents) map to genuinely distinct DF concepts: alive-current-members, all-members-ever, and site-linked-figures.
- The filter chips on Members and Residents tabs make the dimensions explicit and navigable.
- The Overview tile "Population" label accurately reflects "living citizens" — the intuitive meaning.

**Against:**
- **Pop. in Sites tab vs Population in Overview** appear to measure the same thing but use different code paths with different bugs, producing contradictory numbers (0 vs 101).
- **"Residents" implies physical presence** at a site, but hf_site_links is not a residency register — it's a structural association register. A dwarf who lives at a fortress but doesn't hold a specific structure, occupation, or seat of power will have zero site links despite being a "resident" by any common definition.
- **entity_populations** (1.66M) being labeled alongside hf_entity_links members (15K) in the Statistics tab is misleading without strong contextual framing. They measure fundamentally different things (anonymous aggregate vs. named-individual).

### 4.2: Is there undercounting or overcounting?

**Undercounting — Entity Membership (Tier 2):**
- 937 living HFs (5.5%) have no entity links at all. These are "uncounted" by any membership metric. They include: megabeasts, titans, demons, divine figures, and some animal people created by world generation events without organizational affiliation. This is correct behavior — these figures genuinely have no organizational membership.

**Undercounting — Site Presence (Tier 3):**
- **90.3% of living HFs have no site links.** This is the most severe coverage gap. Most citizens of a DF fortress are members of the site government entity (via hf_entity_links) but have NO hf_site_links entries. The "Residents" tab therefore shows only a small fraction of actual inhabitants.
- For pocketdumplings: 101 living entity members but only 23 site-linked residents. The missing 78 are real living members of the site government who happen to not have structural associations recorded in the legends XML.

**Overcounting:**
- No overcounting detected. The `COUNT(DISTINCT hf_id)` pattern prevents double-counting across entity hierarchies. A figure who belongs to both civ 1007 and site government 1525 is counted once in `total_population`.

### 4.3: Are all sentient denizens counted somewhere?

**No.** Three classes of beings are missing:

1. **Anonymous population** (1.66M minus ~48K named HFs): DF's entity_populations tracks millions of unnamed citizens who never become historical figures. These exist only as aggregate race counts and cannot be individually counted.

2. **Linkless HFs** (1,187 = 2.5%): HFs with neither entity nor site links. Most are supernatural or primordial beings (deities, forces, megabeasts created before civilizations). They appear in the People tab but are invisible to all population metrics.

3. **Site visitors and transients**: DF tracks visitors, merchants, and diplomats who pass through sites but are not members or residents. These are captured in history events but not in the link tables, so they are invisible to all three tiers.

---

## 5. Detailed Issue Analysis

### 5.1: Population Counting Flow for Entity 1525

```
fetch_civilization_data(conn, world_id=1, entity_id=1525)
  |
  |-- entity type = 'sitegovernment' (not 'civilization')
  |-- is_civ = False
  |
  |-- Child SG query (line 93-99):
  |     SELECT id FROM entities WHERE type='sitegovernment'
  |       AND details->'entity_links' @> PARENT target=1525
  |     Result: [] (empty — no children)
  |     sg_ids = []
  |
  |-- sg_populations query (line 140-150):
  |     SELECT entity_id, COUNT(*) FROM hf_entity_links
  |       WHERE entity_id = ANY([]::int[])  -- EMPTY ARRAY
  |     Result: nothing queried
  |     sg_populations = {}
  |
  |-- all_entity_ids = [1525] + [] = [1525]
  |
  |-- total_population query (line 234-248):
  |     SELECT COUNT(DISTINCT hf_id) FROM hf_entity_links
  |       WHERE entity_id = ANY([1525]) AND link_type='member' AND death_year IS NULL
  |     Result: 101 (CORRECT)
  |
  |-- Non-civ direct sites (line 380-385):
  |     SELECT id FROM sites WHERE owner_entity_id=1525
  |     Result: [(621, 'pocketdumplings', 'town')]
  |
  |-- site_govts assembly (line 421-431):
  |     For site 621:
  |       population = sg_populations.get(1525, 0) = 0   (BUG: 1525 was never in sg_populations)
  |
  |-- RESULT:
  |     total_population = 101 (correct)
  |     site_govts[0].population = 0 (WRONG — should be 101)
```

### 5.2: Statistics Divergence Query Analysis

The `entity_pop` CTE in `statistics.py:194-202` correctly joins `sites -> entities(owner) -> hf_entity_links -> historical_figures` and counts living current members of the site's owner entity. For site 621:
- Owner = entity 1525
- Living current members of 1525 = 101
- Query correctly returns population=101

The `site_res` CTE at line 204-210 correctly counts living HFs in `hf_site_links` for each site. For site 621: residents=23.

**The divergence query itself is correct.** The "all zeros" appearance is a sort-order presentation issue.

### 5.3: Civilization-Level vs Site-Government-Level Counting

When viewing entity 1007 (civilization "the brave kingdom"):
- `sg_ids` = [1525, ...other SGs...]
- `sg_populations` correctly queries all child SG IDs and maps their living member counts
- The Sites tab correctly shows Pop. for each child SG

When viewing entity 1525 (site government "the nourishing league"):
- `sg_ids` = [] (no children)
- `sg_populations` = {} (never queried)
- The entity's own living member count (101) exists in `total_population` but is not propagated to the Sites tab

**The inconsistency is architectural:** `sg_populations` was designed to populate child SGs of a civilization, but the `!is_civ` code path at line 377-431 reuses `sg_populations` for the entity itself without ever populating it.

---

## 6. Comprehensive Proposed Solutions

### Fix 1: Populate sg_populations for the entity itself (HIGH PRIORITY)

**File:** `civilizations.py:140-150`

**Change:** When the entity is not a civilization, also query the entity's own ID into `sg_populations`.

```python
# Current (line 140-150):
pop_rows = await conn.fetch(
    "SELECT hel.entity_id, COUNT(*) AS cnt "
    "FROM hf_entity_links hel "
    "JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id "
    "WHERE hel.world_id = $1 AND hel.entity_id = ANY($2::int[]) "
    "AND hel.link_type = 'member' AND hf.death_year IS NULL "
    "GROUP BY hel.entity_id",
    world_id, sg_ids,
)

# Proposed:
pop_query_ids = sg_ids if is_civ else ([entity_id] + sg_ids)
if pop_query_ids:
    pop_rows = await conn.fetch(
        "SELECT hel.entity_id, COUNT(*) AS cnt "
        "FROM hf_entity_links hel "
        "JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id "
        "WHERE hel.world_id = $1 AND hel.entity_id = ANY($2::int[]) "
        "AND hel.link_type = 'member' AND hf.death_year IS NULL "
        "GROUP BY hel.entity_id",
        world_id, pop_query_ids,
    )
```

**Rationale:** For civilizations, `sg_populations` is correctly scoped to children (because the civ row doesn't appear in its own Sites tab). For non-civ entities (site governments, religions, guilds), the entity itself appears as a row in the Sites tab and needs its own population count.

### Fix 2: Statistics divergence table — sort by absolute divergence, not population (MEDIUM)

**File:** `statistics.py:220`

**Current:**
```sql
ORDER BY ep.population DESC
```

**Proposed:**
```sql
ORDER BY ABS(ep.population - COALESCE(sr.residents, 0)) DESC
```

**Rationale:** Sorting by divergence magnitude surfaces the most interesting cases first (sites where entity membership and site presence differ most), rather than showing large populations with trivially zero residents.

**Alternative:** Add a filter to only show sites with at least 1 resident:
```sql
WHERE COALESCE(sr.residents, 0) > 0 OR ep.population > 0
```

### Fix 3: Add "estimated actual residents" annotation to Residents tab (LOW)

**File:** `site_detail.html` (Residents tab header area)

Add a contextual note explaining the coverage gap:

```html
<p class="text-stone-500 text-[10px] mt-1">
  Site links represent structural associations (home, occupation, seat of power).
  The {{ government_name }}'s total living members ({{ population }}) includes
  citizens without specific structural records.
</p>
```

**Rationale:** Users seeing 23 residents at a site whose government has 101 living members will be confused. A brief annotation explains the gap without changing the underlying data model.

### Fix 4: Unified population summary on site detail Overview tile (LOW)

**File:** `site_detail.html` and `detail_pages.py`

Add a "Government Members" count alongside the existing Residents count on the site Overview tile. This shows both dimensions side-by-side without conflating them.

```html
<div class="grid grid-cols-2 gap-4">
  <div>
    <div class="text-stone-500 text-[10px]">Government Members (alive)</div>
    <div class="text-stone-200">{{ gov_population }}</div>
  </div>
  <div>
    <div class="text-stone-500 text-[10px]">Site-Linked Residents</div>
    <div class="text-stone-200">{{ alive_residents }}</div>
  </div>
</div>
```

### Fix 5: Statistics tab — reframe entity_populations as a separate section (LOW)

**File:** `statistics.py` and `explorer.html` (stats panel)

Currently `entity_populations` data is returned but displayed in a way that invites comparison with the per-HF counts. Reframe it as "DF Census Data" with a clear disclaimer:

> These are DF's aggregate race counts per civilization. They include ~1.66M unnamed citizens who never became historical figures. They cannot be directly compared to the ~48K named historical figures tracked in hf_entity_links and hf_site_links.

---

## 7. Summary Matrix

| Issue | Severity | Type | Fix # | Affects |
|---|---|---|---|---|
| Sites tab Pop.=0 for site governments | HIGH | Bug | Fix 1 | 1,890 entities |
| Divergence table shows "all zeros" | MEDIUM | UX | Fix 2 | Statistics tab |
| Residents tab undercounts actual inhabitants | LOW | By design | Fix 3 | All sites |
| No side-by-side gov members vs site residents | LOW | Missing feature | Fix 4 | Site detail pages |
| entity_populations vs hf_entity_links confusion | LOW | UX | Fix 5 | Statistics tab |

---

## 8. Data Appendix

### World 1 ("Tar Thran") Key Statistics

| Metric | Value |
|---|---|
| Total historical figures | 48,273 |
| Living historical figures | 17,073 |
| Total entity_populations (DF aggregate) | 1,663,758 |
| Living HFs with entity links (member) | 15,373 |
| HFs with any site link | 2,066 (4.3%) |
| Living HFs with any site link | 1,661 (9.7%) |
| HFs with no links at all | 1,187 (2.5%) |
| Entities (total) | 4,847 |
| Site governments | 1,890 |
| Civilizations | 810 |
| Sites (total) | 2,154 (22 types) |
| Sites with any hf_site_links | ~544 |

### Case Study: pocketdumplings (site 621)

| Metric | Value | Source |
|---|---|---|
| Government entity | the nourishing league (1525) | sites.owner_entity_id |
| Parent civilization | the brave kingdom (1007) | entities.details JSONB |
| entity_populations for 1525 | 0 records | DF only exports for civilizations |
| entity_populations for 1007 | 17,097 (DWARF) | entity_populations table |
| Living members of 1525 | 101 | hf_entity_links (member + alive) |
| All members of 1525 (incl dead) | 267 | hf_entity_links (member) |
| Former members of 1525 | 116 | hf_entity_links (former member) |
| Total HF links to 1525 | 471 | hf_entity_links (all types) |
| Site-linked residents at 621 | 61 total, 23 alive | hf_site_links |
| Overview tile "Population" | 101 | Correct (total_population) |
| Sites tab "Pop." | 0 | **BUG** (sg_populations miss) |
| Members tab "Current (Alive)" | 136 | Counts include enemy/prisoner?? |

**Note on Members tab count discrepancy (136 vs 101):** The Members tab `alive_total` counts HFs with `death_year IS NULL` across BOTH `member` and `former member` link_types (line 493: `COUNT(*) FILTER (WHERE hf.death_year IS NULL) AS alive_total`). This means 136 = alive current members (101) + alive former members (35). The "Alive" filter chip shows HFs alive regardless of membership status — a valid but potentially confusing dimension. The filter chip system handles this correctly when both "Current" and "Alive" are active simultaneously.
