# Phase 2: Explorer Core — Validation Walkthrough

**Purpose**: Step-by-step guide for manually verifying all Phase 2 features.
**Prerequisites**: PostgreSQL running with Chronicler data (world "Tar Thran" ingested).

---

## Setup

```bash
cd /Users/nathanielcannon/Claude/Projects/DwarfCron
.venv/bin/chronicler serve --port 8000
```

Open your browser to **http://localhost:8000/explorer**

---

## 1. Global Search (all pages)

The search bar is in the top navigation bar, visible on every page.

1. Click the search input in the top-right corner
2. Type `dwarf` — results should appear after 200ms with color-coded type badges
3. Type `asob` — should find "Asob Worshipfuliron the Jade Trumpet of Channeling" (Historical Figure)
4. Use **Arrow Down/Up** to navigate results, **Enter** to select, **Escape** to dismiss
5. Click a result to navigate to that entity's detail page

**Verify**: Results show type badges (HF in gold, Entity in blue, Site in green), names match search term, keyboard navigation works.

---

## 2. Historical Figure Detail Page

Navigate to: **http://localhost:8000/explorer/hf/1**

### Check these features:
- **Header**: Name "Asob Worshipfuliron the Jade Trumpet of Channeling" in gold, race/caste info
- **Type badges**: Look for badges like "deity", "vampire", etc. (this HF may not have special types, but check HF #1779 for a vampire+werebeast+necromancer)
- **Tabs**: 4 tabs should be visible: **Overview**, **Relationships**, **Career**, **Events** (click through each)
- **Events**: Events section with perspective-aware rendering — the current HF's name should appear in **gold bold** (`<em>` tags), while other entities are blue clickable links
- **Cross-links**: Click any blue entity name — it should navigate to that entity's detail page
- **Popovers**: Hover over any blue entity link — a tooltip should appear after 300ms showing a mini-summary (name, type, key stats)
- **Breadcrumb**: Top bar shows "Explorer > People > [name]"
- **Prev/Next**: Navigation buttons for Previous/Next HF by ID
- **Load All events**: Events tab shows "Showing first 50 of N events" with a "Load all" link. Clicking "Load all" (or appending `?events=all` to the URL) loads the full event list

### Caste-Aware Pronouns

Navigate to: **http://localhost:8000/explorer/hf/0** (HF #0, "Slalsto Tundrateal", FEMALE)
- Events should use **she/her** pronouns for this HF (rendered in gold `<em>` tags)

Navigate to: **http://localhost:8000/explorer/hf/1** (HF #1, check caste)
- Male HFs should use **he/him/his**; unknown/default caste uses **they/them/their**

### Vampire/Special HF

Navigate to: **http://localhost:8000/explorer/hf/1779**
- Should show type badges for vampire, werebeast, necromancer

---

## 3. Entity/Civilization Detail Page

Navigate to: **http://localhost:8000/explorer/entity/24** (The Dwarven Diamond)

### Check these features:
- **Tabs**: Leaders, Sites, Members, Groups, Wars (5 tabs)
- **Leaders tab**: List of historical figures who led this civilization
- **Sites tab**: Sites owned or controlled by this civilization
- **Members tab**: Historical figures associated with this civilization
- **Cross-links**: All entity names are clickable links with popovers

---

## 4. Site Detail Page

Navigate to: **http://localhost:8000/explorer/site/1**

### Check these features:
- **Tabs**: Structures, Properties, History (3 tabs)
- **Structures tab**: List of structures at this site, each linked to its detail page
- **Owner**: Current owner civilization linked
- **Cross-links**: All referenced entities are clickable

---

## 5. Artifact Detail Page

Navigate to: **http://localhost:8000/explorer/artifact/1**

### Check these features:
- **Item details**: Type, material, creation info
- **Events**: Related events showing artifact creation, transfers
- **Cross-links**: Creator and holder links

---

## 6. Region Detail Page

Navigate to: **http://localhost:8000/explorer/region/1**

### Check these features:
- **Biome badge**: Shows the region's biome type
- **Evilness badge**: Benign (cyan), Neutral (gray), or Evil (purple)
- **Events**: Events that occurred in this region

---

## 7. Structure Detail Page

Navigate to: **http://localhost:8000/explorer/site/38/structure/0** (site 1 has no structures; site 38 has a market)

If you want to test a temple, try: **http://localhost:8000/explorer/site/301/structure/6** ("The Cradled Temple")

### Check these features:
- **Type badge**: Structure type (e.g., "market", "temple", "tomb", "mead_hall")
- **Deity link**: For temples with deity data, shows linked deity as clickable HF link
- **Parent site**: Link back to the parent site

---

## 8. Written Content Detail Page

Navigate to: **http://localhost:8000/explorer/written_content/1**

### Check these features:
- **Author**: Linked historical figure who wrote/created this
- **Referenced entities**: Other entities mentioned in the content
- **Form type**: Musical composition, poem, choreography, etc.

---

## 9. Event Collection Detail Page

Navigate to: **http://localhost:8000/explorer/collection/1**

### Check these features:
- **Hierarchy**: If this is a war, should show sub-collections (battles)
- **Events**: Events within this collection
- **Related entities**: Combatants, locations linked

---

## 10. Secondary Entity Pages

Test each of these — they should all render with basic info and cross-links:

| Entity Type | URL | What to Check |
|------------|-----|---------------|
| Underground Region | http://localhost:8000/explorer/underground_region/1 | Type, depth info |
| Landmass | http://localhost:8000/explorer/landmass/1 | Name, regions |
| Mountain Peak | http://localhost:8000/explorer/mountain_peak/1 | Name, height |
| River | http://localhost:8000/explorer/river/1 | Name, path |
| World Construction | http://localhost:8000/explorer/construction/1 | Type, name |
| Art Form | http://localhost:8000/explorer/art_form/1 | Type (musical/poetic/dance) |
| Identity | http://localhost:8000/explorer/identity/1 | Linked HF |
| Historical Era | http://localhost:8000/explorer/era/Age%20of%20Myth | Time range, events |

---

## 11. Years and Events Browser

Navigate to: **http://localhost:8000/explorer/years**

### Check these features:
- **Year list**: Shows all years with event counts
- **Click a year**: Drill into events for that year
- **Event count**: Total should be ~436,455 events
- **Navigation**: Pagination for large event lists

---

## 12. HF Type Filtering

Navigate to: **http://localhost:8000/explorer** (main explorer, People tab)

### Check these features:
- **Type checkboxes**: Deity, Vampire, Necromancer, Werebeast, Ghost
- Check "Vampire" — list should filter to show only vampires
- Check multiple types — should show union of selected types
- **Text filter**: Additional name filter below the checkboxes

---

## 13. Data Browser Features

Navigate to: **http://localhost:8000/explorer** and click the **Data** tab

### JSONB Field Inventory
1. Select a table with JSONB columns (e.g., `historical_figures`)
2. Look for the JSONB column `details`
3. The schema browser should show available JSONB keys

### Row Detail Overlay
1. Click on a data row in the table
2. A modal overlay should appear showing all fields for that row
3. JSONB fields should be displayed in expanded format
4. Close the overlay by clicking outside or pressing Escape

### Query Results Export
1. Go to the **SQL** tab
2. Run a query: `SELECT name, race, birth_year FROM historical_figures LIMIT 10`
3. Look for export buttons (CSV/JSON)
4. Click CSV — should download a CSV file
5. Click JSON — should download a JSON file

---

## 14. URL Hash Tab Persistence

1. Navigate to an entity with tabs (e.g., http://localhost:8000/explorer/entity/24)
2. Click the "Wars" tab — URL should update to include `#tab=wars`
3. Copy the URL and open in a new tab — the Wars tab should be pre-selected
4. Navigate away and use browser back — tab state should be preserved

---

## 15. Cross-Cutting Verification

### Cross-Links
- On any detail page, every entity name should be a clickable blue link
- Clicking a link navigates to that entity's detail page
- Links span all entity types: HF (gold), Entity (blue), Site (green), Artifact (purple), Region (orange)

### Perspective Rendering
- On HF detail pages, the current HF's name is replaced with **caste-aware pronouns** in gold bold:
  - MALE HFs: he/him/his
  - FEMALE HFs: she/her/her
  - Unknown/DEFAULT caste: they/them/their
- On Site detail pages, the current site is replaced with "here"
- Other entities remain as clickable links

### DF Calendar
- Events display dates as "Year N" or "the Nth of Month, Year N"
- Month names are DF-canonical: Granite, Slate, Felsite, Hematite, Malachite, Galena, Limestone, Sandstone, Timber, Moonstone, Opal, Obsidian

### Hover Popovers
- Hover over any entity link for 300ms — a tooltip appears
- HF popovers show: name, race, caste, born/died years, kill count, type badges
- Site popovers show: name, type, owner, coordinates
- Entity popovers show: name, type, race
- Artifact popovers show: name, item type, material, holder

---

## Validation Checklist

Check off each item as you verify it:

- [ ] Global search works from all pages with 200ms debounce
- [ ] HF detail page renders with tabs, events, badges
- [ ] Entity/Civilization detail page shows 5 tabs
- [ ] Site detail page shows 3 tabs with structures
- [ ] Artifact detail page renders with holder info
- [ ] Region detail page shows biome + evilness badges
- [ ] Structure detail page shows type badge
- [ ] Written Content detail page shows author link
- [ ] Event Collection detail page shows hierarchy
- [ ] All 8 secondary entity pages render (underground region through era)
- [ ] Years browser shows chronological event index
- [ ] HF type filtering works (vampire, deity, etc.)
- [ ] Hover popovers appear on entity links
- [ ] Breadcrumb navigation present on all detail pages
- [ ] Prev/Next navigation present on all detail pages
- [ ] URL hash tab persistence works
- [ ] Row detail overlay works in data browser
- [ ] Query export (CSV/JSON) works
- [ ] Cross-links are clickable and navigate correctly
- [ ] Perspective rendering shows gold text for current entity
- [ ] DF calendar dates display correctly

---

*Phase 2: Explorer Core — Validation Walkthrough*
*21 verification items covering all 30 DoD requirements*
