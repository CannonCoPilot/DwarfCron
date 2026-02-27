# Phase 2: Explorer Core — Completion Report

**Date**: 2026-02-26
**Phase**: 2 of 7 (Explorer Core)
**Milestone**: M2 — Explorer Complete
**Status**: COMPLETE — 30/30 DoD items pass

---

## Executive Summary

Phase 2 transforms Chronicler from a data ingestion tool into a full-featured world browser. Starting from Phase 1's 6-tab data grid, the Explorer Core adds **17 entity detail pages**, **global search with live autocomplete**, **perspective-aware event rendering**, **hover popovers**, and **complete cross-linking** across all entity types. The world "Tar Thran" (250 years, 436,455 events, 48,273 historical figures) is fully browsable.

---

## Features Implemented

### Entity Detail Pages (17 types)

| # | Entity Type | Route | Key Features |
|---|------------|-------|--------------|
| 1 | **Historical Figure** | `/explorer/hf/{id}` | 4 tabs (Overview, Relationships, Career, Events), 24 sections, kill count, relationship profiles, type badges (deity, vampire, necromancer, werebeast, ghost), associated civilization, artifacts held, 50-event default with "Load all" option |
| 2 | **Entity/Civilization** | `/explorer/entity/{id}` | 5 tabs: Leaders, Sites, Members, Groups, Wars |
| 3 | **Site** | `/explorer/site/{id}` | 3 tabs: Structures, Properties, History with linked owner civilization |
| 4 | **Artifact** | `/explorer/artifact/{id}` | Item type, material, current holder, creation events |
| 5 | **Region** | `/explorer/region/{id}` | Biome badges, evilness classification (benign/neutral/evil) |
| 6 | **Structure** | `/explorer/site/{sid}/structure/{id}` | 12+ type badges (mead_hall, temple, etc.), deity link for temples |
| 7 | **Written Content** | `/explorer/written_content/{id}` | Author link, referenced entities, form type |
| 8 | **Event Collection** | `/explorer/collection/{id}` | Hierarchy: War > Battles > Events, sub-collections |
| 9 | **Underground Region** | `/explorer/underground_region/{id}` | Type, depth info |
| 10 | **Landmass** | `/explorer/landmass/{id}` | Name, associated regions |
| 11 | **Mountain Peak** | `/explorer/mountain_peak/{id}` | Height, coordinates |
| 12 | **River** | `/explorer/river/{id}` | Name, path info |
| 13 | **World Construction** | `/explorer/construction/{id}` | Type, associated entities |
| 14 | **Art Form** | `/explorer/art_form/{id}` | 3 types (musical, poetic, dance) |
| 15 | **Identity** | `/explorer/identity/{id}` | Linked historical figure, assumed identity details |
| 16 | **Historical Era** | `/explorer/era/{name}` | Time range, event type breakdown, sample events |
| 17 | **Years Browser** | `/explorer/years` | Chronological event index, year list with event counts, drill into year detail |

### Search and Navigation (8 features)

| Feature | Implementation |
|---------|---------------|
| **Global search** | Live autocomplete in nav bar, all pages, 200ms debounce, keyboard nav (arrow/enter/escape) |
| **Accent-insensitive** | PostgreSQL `unaccent()` on both search term and column values |
| **HF type filtering** | Checkbox filters: Deity, Vampire, Necromancer, Werebeast, Ghost |
| **Hover popovers** | Tippy.js on all entity links, AJAX-loaded from `/api/popover/{type}/{id}`, LRU cache |
| **Breadcrumb nav** | Explorer > Category > Entity name, on all detail pages |
| **Prev/Next nav** | Sequential entity navigation buttons on all detail pages |
| **URL hash persistence** | `#tab=name` in URL, restored on page load, updated on tab switch |
| **JSONB field inventory** | `/api/explorer/schema/jsonb_keys/{table}/{column}` endpoint |
| **Row detail overlay** | Modal overlay in data browser for inspecting individual rows |
| **Query export** | CSV/JSON export for both table data and custom SQL queries |

### Cross-Cutting Infrastructure (5 systems)

| System | Module | Purpose |
|--------|--------|---------|
| **EntityLinkRenderer** | `chronicler/explorer/linking.py:11` | Generates HTML `<a>` tags for 15 entity types with CSS classes and data attributes |
| **EntityNameCache** | `chronicler/explorer/linking.py:106` | Batch name resolution with per-world 5-minute TTL cache |
| **PerspectiveRenderer** | `chronicler/explorer/perspective.py` | Caste-aware pronoun substitution (MALE→he/him/his, FEMALE→she/her/her, DEFAULT→they/them/their; site→here, civ→the civilization) |
| **DFCalendar** | `chronicler/explorer/calendar.py` | DF 12-month calendar with months, seasons, ordinals, tick conversion |
| **Popover system** | `detail_base.html` + `/api/popover/` | Tippy.js initialization, AJAX loading, per-type rendering, XSS-safe HTML |

### API Endpoints Added

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/search` | GET | Global entity search (accent-insensitive) |
| `/api/popover/{type}/{id}` | GET | Hover popover content (HTML) |
| `/api/explorer/years` | GET | Year list with event counts |
| `/api/explorer/years/{year}` | GET | Paginated events for a year |
| `/api/explorer/event_types` | GET | All event type names |
| `/api/explorer/event/{id}` | GET | Single event detail |
| `/api/explorer/schema/jsonb_keys/{table}/{col}` | GET | JSONB key inventory |
| `/api/explorer/export/data/{table}` | GET | Table data export (CSV/JSON) |
| `/api/explorer/export/query` | POST | Custom SQL export (CSV/JSON) |

---

## Test Results

### Automated Tests
- **195 passed** — Core functionality (parser, schema, ingestion, CLI, API routes)
- **12 failed** — All in live-data integration tests (DFHack units, bridge sections) — Phase 5 scope
- **5 errors** — Separate validation harness requiring specific setup
- **2 xfailed** — Expected failures (known gaps)

### Manual Endpoint Testing (30/30 DoD items)

Every DoD item was tested via HTTP requests against the running server:
- All 17 entity detail pages return HTTP 200 with substantial content (4.5KB–30KB)
- Search returns properly ranked results with type badges and snippets
- Popovers return rich HTML with entity-type-specific fields
- Cross-links verified: 50+ links on HF pages spanning 5+ entity types
- Perspective rendering confirmed: 21 `<em>` markers on HF event lists
- Calendar formatting: "Year N" throughout, "the Nth of Month, Year N" for dated events

### Performance

- Entity detail pages load in <100ms (server-side)
- Search autocomplete: 200ms debounce + fast ILIKE with unaccent
- Name cache: 5-minute TTL, batch loading by entity type (1 query per type, not per entity)

---

## Architecture

### File Structure

```
chronicler/
├── explorer/                     # Phase 2 core module
│   ├── __init__.py
│   ├── calendar.py               # DF calendar (114 lines)
│   ├── linking.py                # EntityLinkRenderer + EntityNameCache (219 lines)
│   └── perspective.py            # PerspectiveRenderer (423 lines)
├── api/
│   ├── routes/
│   │   ├── detail_pages.py       # 17 entity detail routes + search/popover/export (2188 lines)
│   │   └── explorer.py           # Data browser, graph, JSONB keys, export (1071 lines)
│   └── templates/
│       ├── detail_base.html      # Shared detail page layout (274 lines)
│       ├── partials/_nav.html    # Shared nav with global search (112 lines)
│       ├── hf_detail.html        # Historical Figure (most complex)
│       ├── entity_detail.html    # Entity/Civilization
│       ├── site_detail.html      # Site
│       ├── artifact_detail.html  # Artifact
│       ├── region_detail.html    # Region
│       ├── structure_detail.html # Structure
│       ├── written_content_detail.html
│       ├── collection_detail.html
│       ├── underground_region_detail.html
│       ├── landmass_detail.html
│       ├── mountain_peak_detail.html
│       ├── river_detail.html
│       ├── construction_detail.html
│       ├── art_form_detail.html
│       ├── identity_detail.html
│       ├── era_detail.html
│       └── years_browser.html
```

### Dependencies Added
- Tippy.js v6 (CDN) — hover popovers
- Popper.js v2 (CDN) — popover positioning
- Bootstrap 5 (already present) — tabs, badges, breadcrumbs

---

## Definition of Done — Complete Checklist

### Entity Detail Pages ✓
- [x] Historical Figure detail page (4 tabs, 24 sections)
- [x] Entity/Civilization detail page (5 tabs)
- [x] Site detail page (3 tabs)
- [x] Artifact detail page (chain-of-custody)
- [x] Region detail page (biome + evilness badges)
- [x] Structure detail page (12+ type badges)
- [x] Written Content detail page (author, refs, form type)
- [x] Event Collection detail page (hierarchy)
- [x] Underground Region detail page
- [x] Landmass detail page
- [x] Mountain Peak detail page
- [x] River detail page
- [x] World Construction detail page
- [x] Art Form detail pages (3 types)
- [x] Identity detail page
- [x] Historical Era detail page
- [x] Years and Events browser

### Search and Navigation ✓
- [x] Global search with live autocomplete (accent-insensitive)
- [x] HF filtering by type flags
- [x] Hover popovers on all entity links
- [x] Breadcrumb / Prev-Next navigation
- [x] URL hash tab persistence
- [x] JSONB field inventory in schema browser
- [x] Row detail overlay in data browser
- [x] Query results export (CSV/JSON)

### Cross-Cutting ✓
- [x] Cross-linked entity references everywhere
- [x] Perspective-aware event rendering
- [x] DF calendar formatting
- [x] Entity name cache for performance
- [x] All pages load within performance targets

---

## Standalone Execution

```bash
# From the DwarfCron project directory:
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
.venv/bin/chronicler serve --port 8000

# Then open: http://localhost:8000/explorer
```

No special handling required. The server starts, connects to PostgreSQL, and serves all pages.

---

## Next Phase

**Phase 3: Narrative Engine** — AI-powered story generation from event data, character biographies, and civilization histories. See `projects/chronicler/reports/phases/phase-3-narrative-engine.md`.

---

*Phase 2: Explorer Core — Completion Report*
*Chronicler v0.2.0 — 30/30 DoD items verified*
