"""Server-side rendered entity detail pages.

Each entity type gets a dedicated URL and Jinja2 template. The existing
JSON API routes (people.py, civilizations.py, etc.) remain for the SPA
explorer tabs. These page routes add bookmarkable, server-rendered detail
pages that use the cross-linking infrastructure.
"""

import os

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from chronicler.explorer.linking import EntityLinkRenderer, EntityNameCache
from chronicler.explorer.calendar import DFCalendar
from chronicler.explorer.death_cause import DeathCauseRenderer
from chronicler.explorer.perspective import PerspectiveRenderer, merge_columns_into_details, extract_enrichment_details
from chronicler.api.routes.civilizations import (
    fetch_civilization_data, fetch_civilization_members, _categorize_position,
)
from chronicler.api.routes._profession import (
    derive_profession, derive_position,
    batch_fetch_profession_data, batch_fetch_positions,
)

router = APIRouter()

_template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=_template_dir)

# Register custom Jinja2 test: 'containing' — substring match for selectattr
templates.env.tests['containing'] = lambda value, substring: substring in (value or '')

# ── Jinja2 globals for entity detail template ──
_STRUCT_ICONS = {
    'inn tavern': '\U0001f3e8', 'tavern': '\U0001f3e8',
    'temple': '\u26ea', 'mead hall': '\U0001f37a', 'guildhall': '\u2692',
    'tomb': '\u26b0', 'market': '\U0001f3ea', 'dungeon': '\u26d3',
    'counting house': '\U0001f4b0', 'keep': '\U0001f3f0', 'tower': '\U0001f5fc',
    'library': '\U0001f4da', 'underworld spire': '\U0001f52e',
}
_CAT_BADGE_CLASSES = {
    'noble': 'bg-amber-900/50 text-amber-400',
    'military': 'bg-red-900/50 text-red-400',
    'justice': 'bg-purple-900/50 text-purple-400',
    'medical': 'bg-emerald-900/50 text-emerald-400',
    'admin': 'bg-blue-900/50 text-blue-400',
    'other': 'bg-stone-800 text-stone-400',
}
templates.env.globals['struct_icon'] = lambda t: _STRUCT_ICONS.get((t or '').lower(), '\U0001f3e0')
templates.env.globals['cat_badge_class'] = lambda c: _CAT_BADGE_CLASSES.get(c, _CAT_BADGE_CLASSES['other'])
templates.env.filters['clean_race'] = lambda r: _clean_race(r) if r else '?'

# Shared instances
_linker = EntityLinkRenderer()
_name_cache = EntityNameCache()

# ── KH visibility gate ──────────────────────────────────────────────

# Entity type mapping: route entity type → KH entity_type
_KH_ENTITY_MAP = {
    'hf': 'hf', 'entity': 'entity', 'site': 'site',
    'region': 'region', 'artifact': 'artifact',
}

_KH_GATE_HTML = """
<div class="flex flex-col items-center justify-center py-16 text-center">
  <div class="text-stone-600 text-4xl mb-4">&#x1F32B;</div>
  <h2 class="text-lg text-stone-400 mb-2">Beyond the Fortress's Knowledge</h2>
  <p class="text-stone-500 text-sm max-w-md">
    The dwarves of your fortress have no knowledge of this {entity_label}.
    Disable the Knowledge Horizon toggle to view in omniscient mode.
  </p>
</div>
"""

_ENTITY_LABELS = {
    'hf': 'historical figure', 'entity': 'civilization',
    'site': 'site', 'region': 'region', 'artifact': 'artifact',
}


async def _kh_gate_check(
    conn, world_id: int, entity_type: str, entity_id: int, kh: bool,
) -> str | None:
    """Return gate HTML if KH is enabled and entity is NOT visible. None otherwise."""
    if not kh:
        return None
    visible = await conn.fetchval(
        "SELECT visible FROM knowledge_horizon "
        "WHERE world_id = $1 AND entity_type = $2 AND entity_id = $3",
        world_id, _KH_ENTITY_MAP.get(entity_type, entity_type), entity_id,
    )
    if visible:
        return None
    label = _ENTITY_LABELS.get(entity_type, 'entity')
    return _KH_GATE_HTML.format(entity_label=label)

# Edge colors for relationship graphs (matches Graph tab styling in explorer.py)
_GRAPH_EDGE_COLORS = {
    "child": "#4ade80", "mother": "#4ade80", "father": "#4ade80",
    "spouse": "#f472b6", "former spouse": "#f472b6", "deceased spouse": "#f472b6",
    "lover": "#f472b6",
    "master": "#60a5fa", "apprentice": "#60a5fa",
    "former master": "#60a5fa", "former apprentice": "#60a5fa",
    "companion": "#fbbf24", "imprisonment": "#ef4444", "jealous_obsession": "#dc2626",
    "partner": "#f472b6",  # inferred co-parent (dashed edge)
}

_FAMILY_LINK_TYPES = frozenset({
    'mother', 'father', 'child',
    'spouse', 'former spouse', 'deceased spouse', 'lover', 'partner',
})

_MENTORSHIP_LINK_TYPES = frozenset({
    'master', 'apprentice', 'former master', 'former apprentice',
})

_EDGE_CATEGORY = {
    'child': 'family', 'mother': 'family', 'father': 'family',
    'spouse': 'romantic', 'former spouse': 'romantic',
    'deceased spouse': 'romantic', 'lover': 'romantic', 'partner': 'romantic',
    'master': 'mentorship', 'apprentice': 'mentorship',
    'former master': 'mentorship', 'former apprentice': 'mentorship',
    'companion': 'companion',
    'imprisonment': 'imprisonment', 'jealous_obsession': 'imprisonment',
}

# HF node type flags in priority order
_NODE_TYPE_RULES = [
    ('is_deity', 'deity', '#f6b93b'),
    ('is_vampire', 'vampire', '#ef4444'),
    ('is_necromancer', 'necromancer', '#a855f7'),
    ('is_werebeast', 'werebeast', '#92400e'),
    ('is_ghost', 'ghost', '#9ca3af'),
]


def _clean_race(race: str | None) -> str:
    """Clean raw race tokens for display. Resolves HFEXP experiment races."""
    if not race:
        return "Unknown"
    if race.startswith("HFEXP"):
        _MAP = {"E_HUM": "Human", "E_ELF": "Elf", "E_DWF": "Dwarf",
                "E_GOB": "Goblin", "E_KOB": "Kobold"}
        parts = race.split()
        if len(parts) > 1:
            base = parts[-1].rstrip("0123456789")
            if base in _MAP:
                return _MAP[base]
        return "Experiment"
    return race.replace("_", " ").title()


def _build_hf_node(gid: int, hf_map: dict, center_id: int) -> dict:
    """Build a vis.js node dict for a historical figure."""
    r = hf_map.get(gid, {})
    is_center = (gid == center_id)
    color = '#78716c'
    node_type = 'mortal'
    for flag, ntype, ncolor in _NODE_TYPE_RULES:
        if r.get(flag):
            color = ncolor
            node_type = ntype
            break
    alive = r.get('death_year') is None or r.get('death_year') == -1
    border = '#f6b93b' if is_center else ('#22c55e' if alive else '#ef4444')
    return {
        'id': f'hf-{gid}',
        'label': r.get('name') or f'HF #{gid}',
        'size': 20 if is_center else 12,
        'group': node_type,
        'color': {
            'background': color, 'border': border,
            'highlight': {'background': color, 'border': '#f6b93b'},
        },
        'font': {
            'color': '#f6b93b' if is_center else '#d6d3d1',
            'size': 11 if is_center else 9,
        },
        'borderWidth': 3 if is_center else 1,
    }


_HF_GRAPH_COLS = ("id, name, death_year, is_deity, is_vampire, "
                   "is_necromancer, is_werebeast, is_ghost")

# Entity node styles for full network graph (keyed by entities.type)
_ENTITY_NODE_STYLES = {
    'civilization':    {'color': '#3b82f6', 'shape': 'diamond',       'label': 'Civilization'},
    'religion':        {'color': '#8b5cf6', 'shape': 'triangle',      'label': 'Sect'},
    'guild':           {'color': '#f59e0b', 'shape': 'square',        'label': 'Guild'},
    'sitegovernment':  {'color': '#10b981', 'shape': 'diamond',       'label': 'Site Gov'},
    'merchantcompany': {'color': '#ef4444', 'shape': 'square',        'label': 'Mercenary'},
    'performancetroupe': {'color': '#ec4899', 'shape': 'triangle',    'label': 'Troupe'},
    'outcast':         {'color': '#78716c', 'shape': 'triangleDown',  'label': 'Outcast'},
    'militaryunit':    {'color': '#dc2626', 'shape': 'star',          'label': 'Military'},
    'nomadicgroup':    {'color': '#a3a3a3', 'shape': 'triangle',      'label': 'Nomads'},
    'migratinggroup':  {'color': '#a3a3a3', 'shape': 'triangle',      'label': 'Migrants'},
}

# Additional edge colors and categories for entity/site relationships
_GRAPH_EDGE_COLORS.update({
    'member': '#a78bfa', 'former member': '#a78bfa',
    'enemy': '#f87171', 'former prisoner': '#f87171',
    'criminal': '#f87171', 'prisoner': '#ef4444',
    'former slave': '#ef4444', 'slave': '#ef4444',
    'home structure': '#22c55e', 'occupation': '#22c55e',
    'seat of power': '#f6b93b', 'lair': '#92400e',
    'hangout': '#78716c', 'home site building': '#22c55e',
    'resident': '#34d399', 'former resident': '#6ee7b7',
})

_EDGE_CATEGORY.update({
    'member': 'membership', 'former member': 'membership',
    'enemy': 'conflict', 'former prisoner': 'conflict',
    'criminal': 'conflict', 'prisoner': 'imprisonment',
    'former slave': 'imprisonment', 'slave': 'imprisonment',
    'home structure': 'residence', 'occupation': 'residence',
    'seat of power': 'residence', 'lair': 'residence',
    'hangout': 'residence', 'home site building': 'residence',
    'resident': 'residence', 'former resident': 'residence',
})


def _build_entity_node(entity_id: int, entity_row: dict) -> dict:
    """Build a vis.js node dict for an entity (org/group)."""
    etype = entity_row.get('entity_type') or entity_row.get('type') or ''
    style = _ENTITY_NODE_STYLES.get(etype, {'color': '#6b7280', 'shape': 'diamond', 'label': etype})
    return {
        'id': f'entity-{entity_id}',
        'label': entity_row.get('entity_name') or entity_row.get('name') or f'Entity #{entity_id}',
        'size': 14,
        'group': f'entity_{etype}',
        'shape': style['shape'],
        'color': {
            'background': style['color'], 'border': '#44403c',
            'highlight': {'background': style['color'], 'border': '#f6b93b'},
        },
        'font': {'color': '#d6d3d1', 'size': 9},
        'borderWidth': 1,
    }


def _build_site_node(site_id: int, site_row: dict) -> dict:
    """Build a vis.js node dict for a site (location)."""
    return {
        'id': f'site-{site_id}',
        'label': site_row.get('site_name') or site_row.get('name') or f'Site #{site_id}',
        'size': 14,
        'group': 'site',
        'shape': 'hexagon',
        'color': {
            'background': '#22c55e', 'border': '#44403c',
            'highlight': {'background': '#22c55e', 'border': '#f6b93b'},
        },
        'font': {'color': '#d6d3d1', 'size': 9},
        'borderWidth': 1,
    }


_MAX_NODES_PER_GEN = 30  # cap to prevent dynasty explosion


async def _build_pedigree_data(conn, world_id: int, hf_id: int,
                                max_up: int = 5, max_down: int = 5) -> dict:
    """Build ancestor/descendant pedigree graph up to max generations."""
    ANCESTOR_TYPES = ('mother', 'father')
    PARTNER_TYPES = ('spouse', 'former spouse', 'deceased spouse', 'lover')

    hf_generations: dict[int, int] = {hf_id: 0}
    raw_edges: list[tuple] = []  # (from_id, to_id, link_type)
    edge_id = 0

    # --- Ancestor expansion ---
    frontier = {hf_id}
    for gen in range(1, max_up + 1):
        if not frontier:
            break
        rows = await conn.fetch(
            "SELECT hf_id, target_hf_id, link_type FROM hf_links "
            "WHERE world_id = $1 AND hf_id = ANY($2::int[]) "
            "AND link_type = ANY($3::text[])",
            world_id, list(frontier), list(ANCESTOR_TYPES))
        next_frontier: set[int] = set()
        for r in rows:
            parent_id = r['target_hf_id']
            if parent_id not in hf_generations:
                hf_generations[parent_id] = -gen
                next_frontier.add(parent_id)
            raw_edges.append((r['hf_id'], parent_id, r['link_type']))
        # Collect spouses of the ancestor frontier (show at same generation)
        if next_frontier:
            spouse_rows = await conn.fetch(
                "SELECT hf_id, target_hf_id, link_type FROM hf_links "
                "WHERE world_id = $1 AND hf_id = ANY($2::int[]) "
                "AND link_type = ANY($3::text[])",
                world_id, list(next_frontier), list(PARTNER_TYPES))
            for r in spouse_rows:
                sid = r['target_hf_id']
                if sid not in hf_generations:
                    hf_generations[sid] = -gen
                raw_edges.append((r['hf_id'], sid, r['link_type']))
        # Cap frontier size
        frontier = set(list(next_frontier)[:_MAX_NODES_PER_GEN])

    # --- Descendant expansion ---
    frontier = {hf_id}
    for gen in range(1, max_down + 1):
        if not frontier:
            break
        rows = await conn.fetch(
            "SELECT hf_id, target_hf_id, link_type FROM hf_links "
            "WHERE world_id = $1 AND hf_id = ANY($2::int[]) "
            "AND link_type = 'child'",
            world_id, list(frontier))
        next_frontier: set[int] = set()
        for r in rows:
            child_id = r['target_hf_id']
            if child_id not in hf_generations:
                hf_generations[child_id] = gen
                next_frontier.add(child_id)
            raw_edges.append((r['hf_id'], child_id, r['link_type']))
        frontier = set(list(next_frontier)[:_MAX_NODES_PER_GEN])

    # Also add spouses of center HF at generation 0
    spouse_rows = await conn.fetch(
        "SELECT hf_id, target_hf_id, link_type FROM hf_links "
        "WHERE world_id = $1 AND hf_id = $2 "
        "AND link_type = ANY($3::text[])",
        world_id, hf_id, list(PARTNER_TYPES))
    for r in spouse_rows:
        sid = r['target_hf_id']
        if sid not in hf_generations:
            hf_generations[sid] = 0
        raw_edges.append((r['hf_id'], sid, r['link_type']))

    all_ids = list(hf_generations.keys())
    if len(all_ids) <= 1:
        return {'nodes': [], 'edges': [], 'center': f'hf-{hf_id}',
                'max_up': max_up, 'max_down': max_down}

    hf_rows = await conn.fetch(
        f"SELECT {_HF_GRAPH_COLS} FROM historical_figures "
        "WHERE world_id = $1 AND id = ANY($2::int[])",
        world_id, all_ids)
    hf_map = {r['id']: dict(r) for r in hf_rows}

    nodes = []
    for gid in hf_generations:
        node = _build_hf_node(gid, hf_map, hf_id)
        node['generation'] = hf_generations[gid]
        nodes.append(node)

    seen: set[tuple] = set()
    edges = []
    for (from_id, to_id, link_type) in raw_edges:
        key = (min(from_id, to_id), max(from_id, to_id), link_type)
        if key in seen:
            continue
        seen.add(key)
        ec = _GRAPH_EDGE_COLORS.get(link_type, '#57534e')
        is_partner = link_type in PARTNER_TYPES
        edges.append({
            'id': edge_id,
            'from': f'hf-{from_id}',
            'to': f'hf-{to_id}',
            'label': link_type,
            'category': 'romantic' if is_partner else 'family',
            'color': {'color': ec, 'highlight': '#f6b93b'},
            'font': {'color': '#78716c', 'size': 9, 'strokeWidth': 0},
            'arrows': '',
        })
        edge_id += 1

    return {
        'nodes': nodes, 'edges': edges, 'center': f'hf-{hf_id}',
        'max_up': max_up, 'max_down': max_down,
    }


async def _build_career_data(conn, world_id: int, hf_id: int) -> dict:
    """Build directed master->apprentice mentorship graph."""
    rows = await conn.fetch(
        "SELECT hf_id, target_hf_id, link_type FROM hf_links "
        "WHERE world_id = $1 AND (hf_id = $2 OR target_hf_id = $2) "
        "AND link_type = ANY($3::text[])",
        world_id, hf_id, list(_MENTORSHIP_LINK_TYPES))

    if not rows:
        return {'nodes': [], 'edges': [], 'center': f'hf-{hf_id}'}

    hf_ids = {hf_id}
    for r in rows:
        hf_ids.add(r['hf_id'])
        hf_ids.add(r['target_hf_id'])

    hf_rows = await conn.fetch(
        f"SELECT {_HF_GRAPH_COLS} FROM historical_figures "
        "WHERE world_id = $1 AND id = ANY($2::int[])",
        world_id, list(hf_ids))
    hf_map = {r['id']: dict(r) for r in hf_rows}
    nodes = [_build_hf_node(gid, hf_map, hf_id) for gid in hf_ids]

    # Normalize direction: master -> apprentice
    # "X has master Y" means Y taught X → edge from Y to X
    # "X has apprentice Y" means X taught Y → edge from X to Y
    seen: set[tuple] = set()
    edges = []
    edge_id = 0
    for r in rows:
        link_type = r['link_type']
        if link_type in ('master', 'former master'):
            from_id, to_id = r['target_hf_id'], r['hf_id']
        else:  # apprentice, former apprentice
            from_id, to_id = r['hf_id'], r['target_hf_id']
        key = (from_id, to_id)
        if key in seen:
            continue
        seen.add(key)
        is_former = 'former' in link_type
        edges.append({
            'id': edge_id,
            'from': f'hf-{from_id}',
            'to': f'hf-{to_id}',
            'label': 'former' if is_former else 'mentored',
            'category': 'mentorship',
            'color': {'color': '#60a5fa', 'highlight': '#f6b93b'},
            'font': {'color': '#78716c', 'size': 9, 'strokeWidth': 0},
            'arrows': 'to',
            'dashes': [5, 5] if is_former else False,
        })
        edge_id += 1

    return {'nodes': nodes, 'edges': edges, 'center': f'hf-{hf_id}'}


async def _build_full_graph_data(conn, world_id: int, hf_id: int,
                                  relationships, co_parents,
                                  entity_links=None, site_links=None,
                                  degree: int = 1) -> dict:
    """Build the full network graph with BFS expansion and entity/site nodes.

    degree 1 = direct relationships only (default).
    degree 2-3 = BFS expansion through hf_links.
    """
    MAX_HF_NODES = 200

    # ── BFS: collect HF IDs ───────────────────────────────────────────────
    graph_hf_ids = {hf_id}
    for r in relationships:
        if r['link_type'] not in ('deity',):
            graph_hf_ids.add(r['target_hf_id'])
    for cp in co_parents:
        graph_hf_ids.add(cp['target_hf_id'])

    frontier = graph_hf_ids - {hf_id}

    # Degrees 2+ : expand through hf_links
    for _d in range(2, degree + 1):
        if not frontier or len(graph_hf_ids) >= MAX_HF_NODES:
            break
        remaining = MAX_HF_NODES - len(graph_hf_ids)
        flist = list(frontier)
        vlist = list(graph_hf_ids)
        new_fwd = await conn.fetch(
            "SELECT DISTINCT target_hf_id FROM hf_links "
            "WHERE world_id = $1 AND hf_id = ANY($2::int[]) "
            "AND link_type NOT IN ('deity') "
            "AND target_hf_id != ALL($3::int[]) LIMIT $4",
            world_id, flist, vlist, remaining)
        new_rev = await conn.fetch(
            "SELECT DISTINCT hf_id AS target_hf_id FROM hf_links "
            "WHERE world_id = $1 AND target_hf_id = ANY($2::int[]) "
            "AND link_type NOT IN ('deity') "
            "AND hf_id != ALL($3::int[]) LIMIT $4",
            world_id, flist, vlist, remaining)
        next_frontier = set()
        for r in list(new_fwd) + list(new_rev):
            tid = r['target_hf_id']
            if tid not in graph_hf_ids and len(graph_hf_ids) < MAX_HF_NODES:
                graph_hf_ids.add(tid)
                next_frontier.add(tid)
        frontier = next_frontier

    # Cap
    if len(graph_hf_ids) > MAX_HF_NODES:
        graph_hf_ids = {hf_id} | set(list(graph_hf_ids - {hf_id})[:MAX_HF_NODES - 1])

    graph_data: dict = {'nodes': [], 'edges': [], 'center': f'hf-{hf_id}'}

    if len(graph_hf_ids) <= 1 and not entity_links and not site_links:
        return graph_data

    # ── HF nodes ──────────────────────────────────────────────────────────
    if graph_hf_ids:
        hf_rows = await conn.fetch(
            f"SELECT {_HF_GRAPH_COLS} FROM historical_figures "
            "WHERE world_id = $1 AND id = ANY($2::int[])",
            world_id, list(graph_hf_ids))
        hf_map = {r['id']: dict(r) for r in hf_rows}
        for gid in graph_hf_ids:
            graph_data['nodes'].append(_build_hf_node(gid, hf_map, hf_id))

    # ── HF-HF edges (among the collected set) ────────────────────────────
    seen_edges: set[tuple] = set()
    edge_id = 0
    if len(graph_hf_ids) > 1:
        graph_edges_raw = await conn.fetch(
            "SELECT hf_id, target_hf_id, link_type FROM hf_links "
            "WHERE world_id = $1 AND hf_id = ANY($2::int[]) "
            "AND target_hf_id = ANY($2::int[]) AND link_type NOT IN ('deity')",
            world_id, list(graph_hf_ids))
        for e in graph_edges_raw:
            pair = (min(e['hf_id'], e['target_hf_id']),
                    max(e['hf_id'], e['target_hf_id']))
            key = pair + (e['link_type'],)
            if key not in seen_edges:
                seen_edges.add(key)
                ec = _GRAPH_EDGE_COLORS.get(e['link_type'], '#57534e')
                graph_data['edges'].append({
                    'id': edge_id,
                    'from': f"hf-{e['hf_id']}",
                    'to': f"hf-{e['target_hf_id']}",
                    'label': e['link_type'],
                    'category': _EDGE_CATEGORY.get(e['link_type'], 'other'),
                    'color': {'color': ec, 'highlight': '#f6b93b'},
                    'font': {'color': '#78716c', 'size': 9, 'strokeWidth': 0},
                    'arrows': '',
                })
                edge_id += 1

    # ── Inferred co-parent edges (dashed) ─────────────────────────────────
    node_ids = {n['id'] for n in graph_data['nodes']}
    for cp in co_parents:
        cp_id = cp['target_hf_id']
        if f'hf-{cp_id}' in node_ids:
            pair = (min(hf_id, cp_id), max(hf_id, cp_id))
            key = pair + ('partner',)
            if key not in seen_edges:
                seen_edges.add(key)
                graph_data['edges'].append({
                    'id': edge_id,
                    'from': f'hf-{hf_id}',
                    'to': f'hf-{cp_id}',
                    'label': 'partner',
                    'category': 'romantic',
                    'color': {'color': '#f472b6', 'highlight': '#f6b93b'},
                    'font': {'color': '#78716c', 'size': 9, 'strokeWidth': 0},
                    'dashes': [5, 5],
                    'arrows': '',
                })
                edge_id += 1

    # ── Entity nodes + membership edges (center HF only) ─────────────────
    if entity_links:
        seen_entity_ids = set()
        for el in entity_links:
            eid = el['entity_id']
            if eid not in seen_entity_ids:
                seen_entity_ids.add(eid)
                graph_data['nodes'].append(_build_entity_node(eid, dict(el)))
            lt = el.get('link_type') or 'member'
            ec = _GRAPH_EDGE_COLORS.get(lt, '#a78bfa')
            cat = _EDGE_CATEGORY.get(lt, 'membership')
            graph_data['edges'].append({
                'id': edge_id,
                'from': f'hf-{hf_id}',
                'to': f'entity-{eid}',
                'label': lt,
                'category': cat,
                'color': {'color': ec, 'highlight': '#f6b93b'},
                'font': {'color': '#78716c', 'size': 9, 'strokeWidth': 0},
                'arrows': 'to',
            })
            edge_id += 1

        # ── Co-members: other HFs linked to these entities ──────────────
        MAX_CO_MEMBERS_PER_ENTITY = 10
        if seen_entity_ids:
            _hf_cols_ent = ", ".join(
                f"h.{c.strip()}" for c in _HF_GRAPH_COLS.split(","))
            co_mem = await conn.fetch(
                f"SELECT el.hf_id, el.entity_id, el.link_type, "
                f"  {_hf_cols_ent} "
                "FROM hf_entity_links el "
                "JOIN historical_figures h ON h.world_id = el.world_id AND h.id = el.hf_id "
                "WHERE el.world_id = $1 AND el.entity_id = ANY($2::int[]) "
                "  AND el.hf_id != $3 "
                "  AND el.link_type IN ('member', 'former member') "
                "ORDER BY el.entity_id, "
                "  CASE el.link_type WHEN 'member' THEN 0 ELSE 1 END, "
                "  h.name",
                world_id, list(seen_entity_ids), hf_id)

            ent_counts: dict[int, int] = {}
            for row in co_mem:
                eid = row['entity_id']
                ent_counts.setdefault(eid, 0)
                if ent_counts[eid] >= MAX_CO_MEMBERS_PER_ENTITY:
                    continue
                ent_counts[eid] += 1
                co_hf_id = row['hf_id']
                node_id = f'hf-{co_hf_id}'
                if co_hf_id not in graph_hf_ids:
                    graph_hf_ids.add(co_hf_id)
                    co_map = {co_hf_id: dict(row)}
                    graph_data['nodes'].append(_build_hf_node(co_hf_id, co_map, hf_id))
                lt = row['link_type']
                ec = _GRAPH_EDGE_COLORS.get(lt, '#a78bfa')
                cat = _EDGE_CATEGORY.get(lt, 'membership')
                graph_data['edges'].append({
                    'id': edge_id,
                    'from': f'entity-{eid}',
                    'to': node_id,
                    'label': lt,
                    'category': cat,
                    'color': {'color': ec, 'highlight': '#f6b93b'},
                    'font': {'color': '#78716c', 'size': 9, 'strokeWidth': 0},
                    'arrows': '',
                })
                edge_id += 1

    # ── Site nodes + residence edges (center HF only) ─────────────────────
    if site_links:
        seen_site_ids = set()
        for sl in site_links:
            sid = sl['site_id']
            if sid not in seen_site_ids:
                seen_site_ids.add(sid)
                graph_data['nodes'].append(_build_site_node(sid, dict(sl)))
            lt = sl.get('link_type') or 'home'
            ec = _GRAPH_EDGE_COLORS.get(lt, '#22c55e')
            cat = _EDGE_CATEGORY.get(lt, 'residence')
            graph_data['edges'].append({
                'id': edge_id,
                'from': f'hf-{hf_id}',
                'to': f'site-{sid}',
                'label': lt,
                'category': cat,
                'color': {'color': ec, 'highlight': '#f6b93b'},
                'font': {'color': '#78716c', 'size': 9, 'strokeWidth': 0},
                'arrows': '',
            })
            edge_id += 1

        # ── Co-occupants: other HFs linked to these sites ───────────────
        MAX_CO_OCCUPANTS_PER_SITE = 10
        if seen_site_ids:
            _hf_cols_prefixed = ", ".join(
                f"h.{c.strip()}" for c in _HF_GRAPH_COLS.split(","))
            co_occ = await conn.fetch(
                f"SELECT l.hf_id, l.site_id, l.link_type, "
                f"  {_hf_cols_prefixed} "
                "FROM hf_site_links l "
                "JOIN historical_figures h ON h.world_id = l.world_id AND h.id = l.hf_id "
                "WHERE l.world_id = $1 AND l.site_id = ANY($2::int[]) "
                "  AND l.hf_id != $3 "
                "  AND l.link_type IN ('resident', 'former resident', "
                "      'home structure', 'occupation', 'seat of power') "
                "ORDER BY l.site_id, "
                "  CASE l.link_type WHEN 'resident' THEN 0 ELSE 1 END, "
                "  h.name",
                world_id, list(seen_site_ids), hf_id)

            # Group by site and cap per site
            site_counts: dict[int, int] = {}
            for row in co_occ:
                sid = row['site_id']
                site_counts.setdefault(sid, 0)
                if site_counts[sid] >= MAX_CO_OCCUPANTS_PER_SITE:
                    continue
                site_counts[sid] += 1
                co_hf_id = row['hf_id']
                # Add HF node if not already present
                node_id = f'hf-{co_hf_id}'
                if co_hf_id not in graph_hf_ids:
                    graph_hf_ids.add(co_hf_id)
                    co_map = {co_hf_id: dict(row)}
                    graph_data['nodes'].append(_build_hf_node(co_hf_id, co_map, hf_id))
                # Add edge from site to co-occupant
                lt = row['link_type']
                ec = _GRAPH_EDGE_COLORS.get(lt, '#22c55e')
                cat = _EDGE_CATEGORY.get(lt, 'residence')
                graph_data['edges'].append({
                    'id': edge_id,
                    'from': f'site-{sid}',
                    'to': node_id,
                    'label': lt,
                    'category': cat,
                    'color': {'color': ec, 'highlight': '#f6b93b'},
                    'font': {'color': '#78716c', 'size': 9, 'strokeWidth': 0},
                    'arrows': '',
                })
                edge_id += 1

    return graph_data


def _world_id_or_default(request: Request, world_id: int = None) -> int:
    """Get world_id from query param, defaulting to the first available world."""
    if world_id:
        return world_id
    # Will be resolved in each route via DB query if needed
    return 0


async def _get_default_world_id(conn) -> int:
    """Get the first world ID from the database."""
    row = await conn.fetchval("SELECT id FROM worlds ORDER BY id LIMIT 1")
    return row or 0


async def _get_world_info(conn, world_id: int) -> dict:
    """Fetch basic world info for display."""
    row = await conn.fetchrow(
        "SELECT id, name, alt_name FROM worlds WHERE id = $1", world_id
    )
    if row:
        return dict(row)
    return {"id": world_id, "name": "Unknown World", "alt_name": None}


# ─── Historical Figure Detail Page ──────────────────────────────────────────

@router.get("/explorer/hf/{hf_id}", response_class=HTMLResponse)
async def hf_detail_page(hf_id: int, request: Request,
                         world_id: int = Query(None),
                         partial: str = Query(None),
                         kh: bool = Query(False)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        gate = await _kh_gate_check(conn, world_id, 'hf', hf_id, kh)
        if gate:
            return HTMLResponse(gate)

        hf = await conn.fetchrow(
            "SELECT * FROM historical_figures WHERE world_id = $1 AND id = $2",
            world_id, hf_id,
        )
        if not hf:
            raise HTTPException(404, f"Historical figure #{hf_id} not found")
        hf = dict(hf)

        # Resolve race display name from creature_dictionary
        cd_name = await conn.fetchval(
            "SELECT name_singular FROM creature_dictionary "
            "WHERE world_id = $1 AND creature_id = $2",
            world_id, hf.get("race"),
        )
        race_raw = hf.get("race") or ""
        if cd_name:
            # Capitalize first letter of each word, respecting apostrophes
            hf["race_display"] = " ".join(
                w[0].upper() + w[1:] if w else w
                for w in cd_name.split(" ")
            )
        elif race_raw.startswith("HFEXP"):
            hf["race_display"] = "Experiment"
        else:
            hf["race_display"] = race_raw.replace("_", " ").title()

        world = await _get_world_info(conn, world_id)

        # Relationships (hf_links)
        relationships = await conn.fetch("""
            SELECT l.target_hf_id, l.link_type,
                   h.name AS target_name, h.race AS target_race,
                   h.caste AS target_caste, h.death_year AS target_death_year
            FROM hf_links l
            LEFT JOIN historical_figures h ON h.world_id = l.world_id AND h.id = l.target_hf_id
            WHERE l.world_id = $1 AND l.hf_id = $2
            ORDER BY l.link_type, h.name
        """, world_id, hf_id)

        # Infer co-parents: for each child, find the other parent who has no
        # explicit romantic link to this HF.  Recovers ~12,900 invisible partnerships.
        co_parents = await conn.fetch("""
            SELECT other_parent.target_hf_id,
                   other_parent.link_type AS parent_type,
                   h.name AS target_name, h.race AS target_race,
                   h.caste AS target_caste, h.death_year AS target_death_year,
                   array_agg(DISTINCT child_link.target_hf_id) AS shared_child_ids
            FROM hf_links child_link
            JOIN hf_links other_parent
                ON other_parent.world_id = child_link.world_id
                AND other_parent.hf_id = child_link.target_hf_id
                AND other_parent.link_type IN ('mother', 'father')
                AND other_parent.target_hf_id != $2
            LEFT JOIN historical_figures h
                ON h.world_id = other_parent.world_id
                AND h.id = other_parent.target_hf_id
            WHERE child_link.world_id = $1
                AND child_link.hf_id = $2
                AND child_link.link_type = 'child'
                AND NOT EXISTS (
                    SELECT 1 FROM hf_links ex
                    WHERE ex.world_id = $1
                      AND ((ex.hf_id = $2 AND ex.target_hf_id = other_parent.target_hf_id)
                        OR (ex.hf_id = other_parent.target_hf_id AND ex.target_hf_id = $2))
                      AND ex.link_type IN ('spouse', 'former spouse', 'deceased spouse', 'lover')
                )
            GROUP BY other_parent.target_hf_id, other_parent.link_type,
                     h.name, h.race, h.caste, h.death_year
        """, world_id, hf_id)

        # Entity memberships (hf_entity_links) + primary site via LATERAL
        entity_links = await conn.fetch("""
            SELECT l.entity_id, l.link_type, l.position_name,
                   e.name AS entity_name, e.type AS entity_type, e.race AS entity_race,
                   ps.site_id AS primary_site_id, ps.site_name AS primary_site_name
            FROM hf_entity_links l
            LEFT JOIN entities e ON e.world_id = l.world_id AND e.id = l.entity_id
            LEFT JOIN LATERAL (
                SELECT s.id AS site_id, s.name AS site_name
                FROM sites s
                WHERE s.world_id = l.world_id AND s.owner_entity_id = l.entity_id
                ORDER BY s.prominence_score DESC NULLS LAST
                LIMIT 1
            ) ps ON true
            WHERE l.world_id = $1 AND l.hf_id = $2
            ORDER BY l.link_type, e.name
        """, world_id, hf_id)

        # Site links (hf_site_links)
        site_links = await conn.fetch("""
            SELECT l.site_id, l.link_type,
                   s.name AS site_name, s.type AS site_type
            FROM hf_site_links l
            LEFT JOIN sites s ON s.world_id = l.world_id AND s.id = l.site_id
            WHERE l.world_id = $1 AND l.hf_id = $2
            ORDER BY l.link_type, s.name
        """, world_id, hf_id)

        # Position links (hf_position_links) — noble/leadership positions
        # Note: position_name lives in entity_positions, not hf_position_links
        position_links = await conn.fetch("""
            SELECT l.entity_id, l.position_id, l.start_year, l.end_year,
                   e.name AS entity_name,
                   ep.name AS position_name
            FROM hf_position_links l
            LEFT JOIN entities e ON e.world_id = l.world_id AND e.id = l.entity_id
            LEFT JOIN entity_positions ep ON ep.world_id = l.world_id
                  AND ep.entity_id = l.entity_id AND ep.position_id = l.position_id
            WHERE l.world_id = $1 AND l.hf_id = $2
              AND NOT (l.start_year IS NULL AND EXISTS (
                  SELECT 1 FROM hf_position_links l2
                  WHERE l2.world_id = l.world_id AND l2.hf_id = l.hf_id
                    AND l2.entity_id = l.entity_id AND l2.position_id = l.position_id
                    AND l2.start_year IS NOT NULL
              ))
            ORDER BY l.start_year NULLS LAST
        """, world_id, hf_id)

        # Worshippers (if deity) — HFs that worship this one
        worshippers = []
        if hf.get('is_deity'):
            worshippers = await conn.fetch("""
                SELECT l.hf_id, h.name, h.race
                FROM hf_links l
                JOIN historical_figures h ON h.world_id = l.world_id AND h.id = l.hf_id
                WHERE l.world_id = $1 AND l.target_hf_id = $2 AND l.link_type = 'deity'
                ORDER BY h.name
                LIMIT 100
            """, world_id, hf_id)

        # Worshipping entities (if deity)
        worshipping_entities = []
        if hf.get('is_deity'):
            worshipping_entities = await conn.fetch("""
                SELECT DISTINCT l.entity_id, e.name, e.type
                FROM hf_entity_links l
                JOIN entities e ON e.world_id = l.world_id AND e.id = l.entity_id
                WHERE l.world_id = $1 AND l.hf_id = $2 AND l.link_type = 'deity'
                ORDER BY e.name
            """, world_id, hf_id)

        # Artifacts held (use holds_artifact array from HF, column is material not mat)
        artifacts = []
        if hf.get('holds_artifact'):
            artifact_ids = list(hf['holds_artifact'])
            if artifact_ids:
                artifacts = await conn.fetch("""
                    SELECT id, name, item_type, material
                    FROM artifacts
                    WHERE world_id = $1 AND id = ANY($2::int[])
                    ORDER BY name
                """, world_id, artifact_ids)

        # Dedicated structures — for deities, find temples via religion
        # entities that worship this HF. Deity->Religion link is in hf_entity_links.
        dedicated_structures = []
        if hf.get('is_deity'):
            # Find religion entities linked to this deity
            religion_ids = await conn.fetch("""
                SELECT DISTINCT l.entity_id
                FROM hf_entity_links l
                WHERE l.world_id = $1 AND l.hf_id = $2 AND l.link_type = 'deity'
            """, world_id, hf_id)
            rids = [r['entity_id'] for r in religion_ids]
            if rids:
                dedicated_structures = await conn.fetch("""
                    SELECT s.id, s.site_id, s.name, s.type,
                           si.name AS site_name, s.entity_id
                    FROM structures s
                    JOIN sites si ON si.world_id = s.world_id AND si.id = s.site_id
                    WHERE s.world_id = $1 AND s.entity_id = ANY($2::int[])
                    ORDER BY s.name
                    LIMIT 100
                """, world_id, rids)

        # Used identities (column is histfig_id, not hf_id)
        identities = await conn.fetch("""
            SELECT id, name, race, caste
            FROM identities
            WHERE world_id = $1 AND histfig_id = $2
            ORDER BY name
        """, world_id, hf_id)

        # Event count and recent events (paginated)
        event_count = await conn.fetchval("""
            SELECT count(*) FROM event_entity_xref
            WHERE world_id = $1 AND entity_type = 'hf' AND entity_id = $2
        """, world_id, hf_id)

        event_limit = 5000  # Fetch all; client-side show/hide handles truncation
        events_rows = await conn.fetch("""
            SELECT e.id, e.year, e.seconds, e.event_type, e.details,
                   e.hf_id_1, e.hf_id_2, e.site_id, e.region_id,
                   e.entity_id_1, e.entity_id_2, e.artifact_id, e.structure_id
            FROM history_events e
            JOIN event_entity_xref x ON x.world_id = e.world_id AND x.event_id = e.id
            WHERE x.world_id = $1 AND x.entity_type = 'hf' AND x.entity_id = $2
            ORDER BY e.year, e.seconds
            LIMIT $3
        """, world_id, hf_id, event_limit)

        # Batch resolve names for events
        refs = set()
        for ev in events_rows:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        # Render events with perspective (gender-aware pronouns)
        renderer = PerspectiveRenderer(_linker, world_id,
                                       perspective_caste=hf.get('caste'))
        rendered_events = []
        for ev in events_rows:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'seconds': ev['seconds'],
                'type': ev['event_type'],
                'date': DFCalendar.format_date(ev['year'], ev['seconds']),
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'hf', hf_id, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        # Primary entity name
        primary_entity = None
        if hf.get('entity_id'):
            primary_entity = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, hf['entity_id'],
            )

        # Prev/Next HF navigation
        prev_hf = await conn.fetchrow("""
            SELECT id, name FROM historical_figures
            WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, hf_id)
        next_hf = await conn.fetchrow("""
            SELECT id, name FROM historical_figures
            WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, hf_id)

        # Battle/beast attack collections
        all_collections = await conn.fetch("""
            SELECT DISTINCT c.id, c.name, c.type, c.start_year, c.start_seconds, c.end_year, c.end_seconds
            FROM history_event_collections c
            JOIN collection_events ce ON ce.world_id = c.world_id AND ce.collection_id = c.id
            JOIN event_entity_xref x ON x.world_id = ce.world_id AND x.event_id = ce.event_id
            WHERE x.world_id = $1 AND x.entity_type = 'hf' AND x.entity_id = $2
              AND c.type IN ('battle', 'beast attack')
            ORDER BY c.start_year
            LIMIT 50
        """, world_id, hf_id)
        battles = [dict(c) for c in all_collections if c['type'] == 'battle']
        beast_attacks = [dict(c) for c in all_collections if c['type'] == 'beast attack']

        # Snatcher events — HFs abducted by this figure
        snatcher_events = await conn.fetch("""
            SELECT e.id, e.year, e.details
            FROM history_events e
            WHERE e.world_id = $1 AND e.event_type = 'hf abducted'
              AND (e.details->>'snatcher_hfid')::int = $2
            ORDER BY e.year
            LIMIT 50
        """, world_id, hf_id)
        # Resolve victim names for snatcher events
        snatcher_victims = []
        for se in snatcher_events:
            d = se['details'] or {}
            victim_id = d.get('target_hfid')
            victim_name = None
            if victim_id is not None:
                victim_name = (await _name_cache.batch_resolve(
                    conn, world_id, [('hf', int(victim_id))]
                )).get(('hf', int(victim_id)))
            snatcher_victims.append({
                'event_id': se['id'], 'year': se['year'],
                'victim_id': victim_id, 'victim_name': victim_name,
            })

        # Resolve kill victim names, race, entity, and site from kills JSONB
        kills_resolved = []
        raw_kills = hf.get('kills')
        if raw_kills:
            import json
            kills_data = json.loads(raw_kills) if isinstance(raw_kills, str) else raw_kills
            event_kills = kills_data.get('event_kills', []) if isinstance(kills_data, dict) else kills_data
            if event_kills:
                victim_ids = list({int(k['victim_id']) for k in event_kills if k.get('victim_id')})
                if victim_ids:
                    victim_refs = [('hf', vid) for vid in victim_ids]
                    kill_names = await _name_cache.batch_resolve(conn, world_id, victim_refs)
                    # Batch-fetch victim race + entity name
                    victim_details_rows = await conn.fetch("""
                        SELECT h.id, h.race, h.entity_id, e.name AS entity_name
                        FROM historical_figures h
                        LEFT JOIN entities e ON e.world_id = h.world_id AND e.id = h.entity_id
                        WHERE h.world_id = $1 AND h.id = ANY($2::int[])
                    """, world_id, victim_ids)
                    victim_info = {r['id']: dict(r) for r in victim_details_rows}
                    # Batch-fetch kill sites from death events (hf_id_1=victim, hf_id_2=slayer)
                    kill_site_rows = await conn.fetch("""
                        SELECT e.hf_id_1 AS victim_id, e.site_id, s.name AS site_name
                        FROM history_events e
                        LEFT JOIN sites s ON s.world_id = e.world_id AND s.id = e.site_id
                        WHERE e.world_id = $1 AND e.event_type = 'hf died'
                          AND e.hf_id_2 = $2 AND e.hf_id_1 = ANY($3::int[])
                    """, world_id, hf_id, victim_ids)
                    kill_sites = {r['victim_id']: dict(r) for r in kill_site_rows}
                    for k in event_kills:
                        vid = k.get('victim_id')
                        info = victim_info.get(int(vid), {}) if vid else {}
                        site_info = kill_sites.get(int(vid), {}) if vid else {}
                        race_raw = info.get('race', '')
                        kills_resolved.append({
                            'year': k.get('year'),
                            'cause': k.get('cause'),
                            'victim_id': vid,
                            'victim_name': kill_names.get(('hf', int(vid))) if vid else None,
                            'victim_race': race_raw.replace('_', ' ').title() if race_raw else None,
                            'victim_entity_name': info.get('entity_name'),
                            'victim_entity_id': info.get('entity_id'),
                            'site_id': site_info.get('site_id'),
                            'site_name': site_info.get('site_name'),
                        })

        # Parse JSONB fields for template
        import json as _json

        def _parse_jsonb(val):
            if val is None:
                return []
            if isinstance(val, str):
                try:
                    return _json.loads(val)
                except (ValueError, TypeError):
                    return []
            return val

        skills = _parse_jsonb(hf.get('skills'))
        if isinstance(skills, str):
            skills = _parse_jsonb(skills)
        goals = _parse_jsonb(hf.get('goals'))
        journey_pets = _parse_jsonb(hf.get('journey_pets'))
        entity_reputations = _parse_jsonb(hf.get('entity_reputations'))
        intrigue_actors = _parse_jsonb(hf.get('intrigue_actors'))

        # Extract vague relationships from details JSONB
        details_data = _parse_jsonb(hf.get('details'))
        if isinstance(details_data, dict):
            vague_relationships = details_data.get('vague_relationships', [])
        else:
            vague_relationships = []

        # Family members (filter from relationships)
        family_types = {
            'mother', 'father', 'child',
            'spouse', 'former spouse', 'deceased spouse', 'lover',
        }
        family = [dict(r) for r in relationships if r['link_type'] in family_types]

        # Add inferred co-parents (partners with shared children but no explicit link)
        for cp in co_parents:
            family.append({
                'target_hf_id': cp['target_hf_id'],
                'link_type': 'partner',
                'target_name': cp['target_name'],
                'target_race': cp['target_race'],
                'target_caste': cp['target_caste'],
                'target_death_year': cp['target_death_year'],
                'inferred': True,
                'shared_children': len(cp['shared_child_ids']),
            })

        # Sort family: parents → spouses/partners → children
        _FAMILY_ORDER = {
            'father': 0, 'mother': 1,
            'spouse': 2, 'deceased spouse': 3, 'former spouse': 4,
            'lover': 5, 'partner': 6,
            'child': 7,
        }
        family.sort(key=lambda f: (_FAMILY_ORDER.get(f['link_type'], 99),
                                   f.get('target_name') or ''))

        # Worshipped deities (this HF worships)
        worshipped_deities = [dict(r) for r in relationships if r['link_type'] == 'deity']

        # ── Build three graph datasets for vis.js ──
        graph_data_pedigree = await _build_pedigree_data(
            conn, world_id, hf_id, max_up=5, max_down=5)
        graph_data_career = await _build_career_data(conn, world_id, hf_id)
        graph_data_full = await _build_full_graph_data(
            conn, world_id, hf_id, relationships, co_parents,
            entity_links=entity_links, site_links=site_links)

        # Check if this HF is a live fortress unit
        live_unit = await conn.fetchrow(
            """
            SELECT id, name, profession, details
            FROM units
            WHERE world_id = $1 AND hist_fig_id = $2 AND is_alive = true
            LIMIT 1
            """,
            world_id, hf_id,
        )
        live_unit_id = live_unit["id"] if live_unit else None

    # Build type flags
    type_flags = []
    for flag, label in [
        ('is_deity', 'Deity'), ('is_force', 'Force'), ('is_vampire', 'Vampire'),
        ('is_necromancer', 'Necromancer'), ('is_werebeast', 'Werebeast'),
        ('is_ghost', 'Ghost'),
    ]:
        if hf.get(flag):
            type_flags.append(label)

    alive = hf['death_year'] is None or hf['death_year'] == -1

    # Pre-render death cause and age at death
    death_cause_rendered = DeathCauseRenderer.render_hf_cause(
        hf.get('death_cause')) if hf.get('death_cause') else None
    age_at_death = DeathCauseRenderer.render_age_at_death(
        hf.get('birth_year'), hf.get('death_year'),
        hf.get('birth_seconds'), hf.get('death_seconds'),
    ) if not alive else None

    # Also render kill causes
    for k in kills_resolved:
        if k.get('cause'):
            k['cause_rendered'] = DeathCauseRenderer.render_hf_cause(k['cause'])

    # When partial=1, use the minimal base template for inline rendering
    base_tmpl = "detail_partial_base.html" if partial == "1" else "detail_base.html"

    return templates.TemplateResponse("hf_detail.html", {
        "request": request,
        "active": "explorer",
        "base_template": base_tmpl,
        "entity_type_display": "Historical Figure",
        "entity_name": hf['name'] or f"HF #{hf_id}",
        "entity_alt_name": None,
        "hf": hf,
        "world": world,
        "world_id": world_id,
        "alive": alive,
        "type_flags": type_flags,
        "relationships": [dict(r) for r in relationships],
        "entity_links": [dict(e) for e in entity_links],
        "site_links": [dict(s) for s in site_links],
        "position_links": [dict(p) for p in position_links],
        "worshippers": [dict(w) for w in worshippers],
        "worshipping_entities": [dict(w) for w in worshipping_entities],
        "artifacts": [dict(a) for a in artifacts],
        "dedicated_structures": [dict(s) for s in dedicated_structures],
        "identities": [dict(i) for i in identities],
        "events": rendered_events,
        "event_count": event_count,
        "primary_entity": dict(primary_entity) if primary_entity else None,
        "prev_hf": dict(prev_hf) if prev_hf else None,
        "next_hf": dict(next_hf) if next_hf else None,
        "battles": battles,
        "beast_attacks": beast_attacks,
        "snatcher_victims": snatcher_victims,
        "kills_resolved": kills_resolved,
        "skills": skills if isinstance(skills, list) else [],
        "goals": goals if isinstance(goals, list) else [],
        "journey_pets": journey_pets if isinstance(journey_pets, list) else [],
        "entity_reputations_data": entity_reputations if isinstance(entity_reputations, list) else [],
        "intrigue_actors_data": intrigue_actors if isinstance(intrigue_actors, list) else [],
        "vague_relationships": vague_relationships,
        "family": family,
        "co_parents": [dict(cp) for cp in co_parents],
        "worshipped_deities": worshipped_deities,
        "linker": _linker,
        "calendar": DFCalendar,
        "death_cause_rendered": death_cause_rendered,
        "age_at_death": age_at_death,
        "graph_data_pedigree": graph_data_pedigree,
        "graph_data_career": graph_data_career,
        "graph_data_full": graph_data_full,
        "live_unit_id": live_unit_id,
    })


# ─── Graph Data API (AJAX endpoint for degree changes) ─────────────────────

@router.get("/api/hf/{hf_id}/graph")
async def hf_graph_data(hf_id: int, request: Request,
                        world_id: int = Query(None),
                        degree: int = Query(1)):
    """Return graph JSON for the full network at a given hop depth."""
    degree = max(1, min(3, degree))
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        # Direct relationships (same query as hf_detail_page)
        relationships = await conn.fetch(
            "SELECT l.target_hf_id, l.link_type, "
            "h.name AS target_name, h.race AS target_race, "
            "h.caste AS target_caste, h.death_year AS target_death_year "
            "FROM hf_links l "
            "LEFT JOIN historical_figures h ON h.world_id = l.world_id "
            "AND h.id = l.target_hf_id "
            "WHERE l.world_id = $1 AND l.hf_id = $2 "
            "ORDER BY l.link_type, h.name",
            world_id, hf_id)

        # Co-parents (simplified — just need target_hf_id for graph)
        co_parents = await conn.fetch("""
            SELECT other_parent.target_hf_id
            FROM hf_links child_link
            JOIN hf_links other_parent
                ON other_parent.world_id = child_link.world_id
                AND other_parent.hf_id = child_link.target_hf_id
                AND other_parent.link_type IN ('mother', 'father')
                AND other_parent.target_hf_id != $2
            WHERE child_link.world_id = $1
                AND child_link.hf_id = $2
                AND child_link.link_type = 'child'
                AND NOT EXISTS (
                    SELECT 1 FROM hf_links ex
                    WHERE ex.world_id = $1
                      AND ((ex.hf_id = $2 AND ex.target_hf_id = other_parent.target_hf_id)
                        OR (ex.hf_id = other_parent.target_hf_id AND ex.target_hf_id = $2))
                      AND ex.link_type IN ('spouse', 'former spouse', 'deceased spouse', 'lover')
                )
            GROUP BY other_parent.target_hf_id
        """, world_id, hf_id)

        # Entity memberships
        entity_links = await conn.fetch(
            "SELECT l.entity_id, l.link_type, "
            "e.name AS entity_name, e.type AS entity_type "
            "FROM hf_entity_links l "
            "LEFT JOIN entities e ON e.world_id = l.world_id AND e.id = l.entity_id "
            "WHERE l.world_id = $1 AND l.hf_id = $2",
            world_id, hf_id)

        # Site links
        site_links = await conn.fetch(
            "SELECT l.site_id, l.link_type, "
            "s.name AS site_name, s.type AS site_type "
            "FROM hf_site_links l "
            "LEFT JOIN sites s ON s.world_id = l.world_id AND s.id = l.site_id "
            "WHERE l.world_id = $1 AND l.hf_id = $2",
            world_id, hf_id)

        graph_data = await _build_full_graph_data(
            conn, world_id, hf_id,
            [dict(r) for r in relationships],
            [dict(r) for r in co_parents],
            entity_links=[dict(e) for e in entity_links],
            site_links=[dict(s) for s in site_links],
            degree=degree)

    return JSONResponse(graph_data)


# ─── Entity (Civilization) Detail Page ──────────────────────────────────────

@router.get("/explorer/entity/{entity_id}", response_class=HTMLResponse)
async def entity_detail_page(entity_id: int, request: Request,
                             world_id: int = Query(None),
                             kh: bool = Query(False)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        gate = await _kh_gate_check(conn, world_id, 'entity', entity_id, kh)
        if gate:
            return HTMLResponse(gate)

        entity = await conn.fetchrow(
            "SELECT * FROM entities WHERE world_id = $1 AND id = $2",
            world_id, entity_id,
        )
        if not entity:
            raise HTTPException(404, f"Entity #{entity_id} not found")
        entity = dict(entity)

        world = await _get_world_info(conn, world_id)

        # ── Rich civ data from shared helpers ──
        civ_data = await fetch_civilization_data(conn, world_id, entity_id)
        members_data = await fetch_civilization_members(
            conn, world_id, entity_id, limit=10000, offset=0,
        )

        # ── For Site Governments: augment members with all citizen sources ──
        # Citizens come from 3 sources (SG members, site links, position
        # holders), but fetch_civilization_members only queries hf_entity_links.
        # Add the missing citizens so the Members tab shows everyone.
        is_site_government = (entity.get('type') or '').lower() == 'sitegovernment'
        if is_site_government:
            from chronicler.api.routes.civilizations import (
                SENTIENCE_FILTER as _SF, SENTIENCE_JOIN as _SJ,
            )
            existing_hf_ids = {m["hf_id"] for m in members_data["members"]}
            # Find sites governed by this SG (owner_entity_id OR entity_site_links)
            sg_site_ids = [
                r["id"] for r in await conn.fetch(
                    """SELECT DISTINCT s.id FROM sites s
                       LEFT JOIN entity_site_links esl
                         ON esl.world_id = s.world_id AND esl.site_id = s.id
                            AND esl.entity_id = $2
                       WHERE s.world_id = $1
                         AND (s.owner_entity_id = $2
                              OR esl.link_type IN ('governs', 'founded', 'owner'))
                    """,
                    world_id, entity_id,
                )
            ]
            extra_citizens = []
            if sg_site_ids:
                # Source 2: hf_site_links (resident/occupation/seat of power)
                site_link_rows = await conn.fetch(f"""
                    SELECT DISTINCT ON (hsl.hf_id)
                           hsl.hf_id, hf.name, hf.race, hf.death_year,
                           'citizen (site link)' AS link_type,
                           hsl.link_type AS site_link_detail,
                           hf.skills, hf.details,
                           hf.is_deity, hf.is_necromancer, hf.is_vampire,
                           hf.is_werebeast, hf.is_ghost, hf.is_author, hf.is_auteur
                    FROM hf_site_links hsl
                    JOIN historical_figures hf ON hf.world_id = hsl.world_id AND hf.id = hsl.hf_id
                    {_SJ}
                    WHERE hsl.world_id = $1 AND hsl.site_id = ANY($2::int[])
                      AND hsl.link_type NOT IN ('former resident')
                      AND hf.death_year IS NULL AND {_SF}
                    ORDER BY hsl.hf_id
                """, world_id, sg_site_ids)
                # Batch-fetch profession data for site-link citizens
                sl_hf_ids = [r["hf_id"] for r in site_link_rows if r["hf_id"] not in existing_hf_ids]
                sl_prof_data = await batch_fetch_profession_data(conn, world_id, sl_hf_ids) if sl_hf_ids else {}
                sl_positions = await batch_fetch_positions(conn, world_id, sl_hf_ids, viewing_entity_id=entity_id) if sl_hf_ids else {}
                for r in site_link_rows:
                    if r["hf_id"] not in existing_hf_ids:
                        d = dict(r)
                        d.pop("death_year", None)
                        d["profession"] = derive_profession(d, sl_prof_data.get(d["hf_id"]))
                        d["position_display"] = derive_position(sl_positions.get(d["hf_id"]), viewing_entity_id=entity_id)
                        d.pop("skills", None)
                        d.pop("details", None)
                        d["position_name"] = None
                        d["is_alive"] = True
                        d["is_citizen"] = True
                        extra_citizens.append(d)
                        existing_hf_ids.add(r["hf_id"])

            # Source 3: position holders at this SG
            pos_rows = await conn.fetch(f"""
                SELECT DISTINCT ON (hpl.hf_id)
                       hpl.hf_id, hf.name, hf.race, hf.death_year,
                       'citizen (position)' AS link_type,
                       ep.name AS position_name,
                       hf.skills, hf.details,
                       hf.is_deity, hf.is_necromancer, hf.is_vampire,
                       hf.is_werebeast, hf.is_ghost, hf.is_author, hf.is_auteur
                FROM hf_position_links hpl
                JOIN historical_figures hf ON hf.world_id = $1 AND hf.id = hpl.hf_id
                {_SJ}
                LEFT JOIN entity_positions ep ON ep.world_id = hpl.world_id
                    AND ep.entity_id = hpl.entity_id AND ep.position_id = hpl.position_id
                WHERE hpl.world_id = $1 AND hpl.entity_id = $2
                  AND hpl.end_year IS NULL
                  AND hf.death_year IS NULL AND {_SF}
                ORDER BY hpl.hf_id
            """, world_id, entity_id)
            # Batch-fetch profession data for position-holder citizens
            pos_hf_ids = [r["hf_id"] for r in pos_rows if r["hf_id"] not in existing_hf_ids]
            pos_prof_data = await batch_fetch_profession_data(conn, world_id, pos_hf_ids) if pos_hf_ids else {}
            pos_positions = await batch_fetch_positions(conn, world_id, pos_hf_ids, viewing_entity_id=entity_id) if pos_hf_ids else {}
            for r in pos_rows:
                if r["hf_id"] not in existing_hf_ids:
                    d = dict(r)
                    d.pop("death_year", None)
                    d["profession"] = derive_profession(d, pos_prof_data.get(d["hf_id"]))
                    d["position_display"] = derive_position(pos_positions.get(d["hf_id"]), viewing_entity_id=entity_id)
                    d.pop("skills", None)
                    d.pop("details", None)
                    d["is_alive"] = True
                    d["is_citizen"] = True
                    extra_citizens.append(d)
                    existing_hf_ids.add(r["hf_id"])

            if extra_citizens:
                members_data["members"].extend(extra_citizens)
                members_data["total"] += len(extra_citizens)

            # Recalculate is_citizen for ALL members using canonical citizen
            # set. This fixes former members who are citizens via site links
            # (their is_citizen was False because the base query only checks
            # hf_entity_links.link_type = 'member').
            from chronicler.api.routes.civilizations import (
                fetch_site_citizens_batch,
            )
            canonical_citizens = await fetch_site_citizens_batch(
                conn, world_id, sg_site_ids,
            )
            # Get the actual citizen HF IDs by running the citizen query
            citizen_hf_ids_rows = await conn.fetch(f"""
                SELECT DISTINCT hf_id FROM (
                    -- Source 1: SG members
                    SELECT hel.hf_id
                    FROM hf_entity_links hel
                    JOIN historical_figures hf ON hf.world_id = $1 AND hf.id = hel.hf_id
                    {_SJ}
                    WHERE hel.world_id = $1 AND hel.entity_id = $2
                      AND hel.link_type = 'member'
                      AND hf.death_year IS NULL AND {_SF}
                    UNION
                    -- Source 2: site links (exclude former resident)
                    SELECT hsl.hf_id
                    FROM hf_site_links hsl
                    JOIN historical_figures hf ON hf.world_id = hsl.world_id AND hf.id = hsl.hf_id
                    {_SJ}
                    WHERE hsl.world_id = $1 AND hsl.site_id = ANY($3::int[])
                      AND hsl.link_type != 'former resident'
                      AND hf.death_year IS NULL AND {_SF}
                    UNION
                    -- Source 3: position holders
                    SELECT hpl.hf_id
                    FROM hf_position_links hpl
                    JOIN historical_figures hf ON hf.world_id = $1 AND hf.id = hpl.hf_id
                    {_SJ}
                    WHERE hpl.world_id = $1 AND hpl.entity_id = $2
                      AND hpl.end_year IS NULL
                      AND hf.death_year IS NULL AND {_SF}
                ) sub
            """, world_id, entity_id, sg_site_ids)
            citizen_hf_set = {r["hf_id"] for r in citizen_hf_ids_rows}

            # Override is_citizen and recount
            current_total = 0
            alive_total = 0
            current_alive = 0
            former_total = 0
            for m in members_data["members"]:
                m["is_citizen"] = m["hf_id"] in citizen_hf_set
                is_current = (m.get("link_type") == "member"
                              or m["is_citizen"]
                              or (m.get("link_type") or "").startswith("citizen"))
                is_alive = m.get("is_alive", False)
                if is_current:
                    current_total += 1
                    if is_alive:
                        current_alive += 1
                else:
                    former_total += 1
                if is_alive:
                    alive_total += 1
            members_data["current_total"] = current_total
            members_data["former_total"] = former_total
            members_data["alive_total"] = alive_total
            members_data["current_alive"] = current_alive

        # ── For Site Governments: separate ne'er-do-wells from members ──
        sg_neerdowells = []
        if is_site_government:
            # Query adversarial HF links to this SG
            sg_adversarial = await conn.fetch("""
                SELECT hel.hf_id, hel.link_type AS threat_type
                FROM hf_entity_links hel
                WHERE hel.world_id = $1 AND hel.entity_id = $2
                  AND hel.link_type IN ('enemy', 'criminal', 'prisoner',
                                        'former prisoner', 'slave', 'former slave')
            """, world_id, entity_id)
            adversarial_map = {
                r["hf_id"]: r["threat_type"].replace("_", " ").title()
                for r in sg_adversarial
            }

            if adversarial_map:
                clean_members = []
                for m in members_data["members"]:
                    threat = adversarial_map.get(m["hf_id"])
                    if threat:
                        m["threat_type"] = threat
                        m["threat_basis"] = "entity link"
                        sg_neerdowells.append(m)
                    else:
                        clean_members.append(m)
                members_data["members"] = clean_members
                # Recount after filtering
                members_data["total"] = len(clean_members)
                current_total = 0
                alive_total = 0
                current_alive = 0
                former_total = 0
                for m in clean_members:
                    is_current = (m.get("link_type") == "member"
                                  or m.get("is_citizen", False)
                                  or (m.get("link_type") or "").startswith("citizen"))
                    is_alive = m.get("is_alive", False)
                    if is_current:
                        current_total += 1
                        if is_alive:
                            current_alive += 1
                    else:
                        former_total += 1
                    if is_alive:
                        alive_total += 1
                members_data["current_total"] = current_total
                members_data["former_total"] = former_total
                members_data["alive_total"] = alive_total
                members_data["current_alive"] = current_alive

        # Leaders — full position history with start/end years
        # (detail-page advantage over inline viewer which only shows current holders)
        leaders = await conn.fetch("""
            SELECT p.hf_id, p.position_id, p.start_year, p.end_year,
                   h.name AS hf_name, h.race AS hf_race,
                   ep.name AS position_name
            FROM hf_position_links p
            JOIN historical_figures h ON h.world_id = p.world_id AND h.id = p.hf_id
            LEFT JOIN entity_positions ep ON ep.world_id = p.world_id
                  AND ep.entity_id = p.entity_id AND ep.position_id = p.position_id
            WHERE p.world_id = $1 AND p.entity_id = $2
              AND ep.name IS NOT NULL  -- exclude orphaned position IDs
              AND NOT (p.start_year IS NULL AND EXISTS (
                  SELECT 1 FROM hf_position_links p2
                  WHERE p2.world_id = p.world_id AND p2.hf_id = p.hf_id
                    AND p2.entity_id = p.entity_id AND p2.position_id = p.position_id
                    AND p2.start_year IS NOT NULL
              ))
            ORDER BY ep.name ASC NULLS LAST, p.end_year DESC NULLS FIRST
        """, world_id, entity_id)

        # Parent civilization (for site governments)
        parent_civ = None
        if is_site_government:
            parent_row = await conn.fetchrow("""
                SELECT e.id, e.name, e.type FROM entity_entity_links eel
                JOIN entities e ON e.world_id = eel.world_id
                    AND e.id = eel.target_entity_id
                WHERE eel.world_id = $1 AND eel.source_entity_id = $2
                  AND eel.link_type = 'PARENT'
                LIMIT 1
            """, world_id, entity_id)
            if parent_row:
                parent_civ = dict(parent_row)

        # Prev/Next
        prev_ent = await conn.fetchrow("""
            SELECT id, name FROM entities
            WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, entity_id)
        next_ent = await conn.fetchrow("""
            SELECT id, name FROM entities
            WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, entity_id)

    etype = (entity.get('type') or '').lower()
    if 'civilization' in etype:
        badge_class = 'badge-civ'
        entity_type_label = 'Civilization'
    elif etype == 'sitegovernment':
        badge_class = 'badge-type'
        entity_type_label = 'Site Government'
    elif 'religion' in etype:
        badge_class = 'badge-religion'
        entity_type_label = 'Religion'
    else:
        badge_class = 'badge-type'
        entity_type_label = (entity.get('type') or 'Entity').replace('_', ' ').title()

    # Extract rich data from civ_data (may be sparse for non-civilizations)
    ruler = civ_data.get("ruler") if civ_data else None
    citizens = civ_data.get("citizens", 0) if civ_data else 0
    df_population = civ_data.get("df_population", 0) if civ_data else 0
    total_residents = civ_data.get("total_residents", 0) if civ_data else 0
    is_civ = civ_data.get("is_civ", False) if civ_data else False
    site_count = civ_data.get("site_count", 0) if civ_data else 0
    site_govts = civ_data.get("site_govts", []) if civ_data else []
    civ_positions = civ_data.get("positions", []) if civ_data else []
    wars = civ_data.get("wars", []) if civ_data else []

    # Bug fix: For SGs, use actual member count instead of site citizen count
    if is_site_government:
        citizens = civ_data.get("current_members", 0) if civ_data else 0

    # Bug fix: For SGs, if no civ-level ruler (position_id 0), fall back to
    # top administrative position holder (mayor > expedition leader > manager)
    if not ruler and is_site_government and civ_positions:
        _SG_RULER_PRIORITY = [
            'mayor', 'expedition leader', 'manager', 'chief medical dwarf',
            'militia commander', 'sheriff', 'captain of the guard',
        ]
        for pname in _SG_RULER_PRIORITY:
            for p in civ_positions:
                if (p.get("name") or '').lower() == pname and p.get("current_holder"):
                    ruler = {
                        "hf_id": p["current_holder"]["hf_id"],
                        "name": p["current_holder"]["name"],
                        "title": p.get("title") or p["name"],
                    }
                    break
            if ruler:
                break

    members = members_data.get("members", [])
    member_total = members_data.get("total", 0)
    member_counts = {
        "total": member_total,
        "current": members_data.get("current_total", 0),
        "former": members_data.get("former_total", 0),
        "alive": members_data.get("alive_total", 0),
        "current_alive": members_data.get("current_alive", 0),
    }

    return templates.TemplateResponse("entity_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Civilization / Entity",
        "entity_name": entity['name'] or f"Entity #{entity_id}",
        "entity_alt_name": None,
        "entity": entity,
        "world": world,
        "world_id": world_id,
        "badge_class": badge_class,
        "leaders": [
            {**dict(l), "hf_race": _clean_race(l["hf_race"])}
            for l in leaders
        ],
        "ruler": ruler,
        "citizens": citizens,
        "df_population": df_population,
        "total_residents": total_residents,
        "is_civ": is_civ,
        "site_count": site_count,
        "site_govts": site_govts,
        "civ_positions": civ_positions,
        "members": members,
        "member_count": member_total,
        "member_counts": member_counts,
        "wars": wars,
        "sg_neerdowells": sg_neerdowells,
        "entity_type_label": entity_type_label,
        "parent_civ": parent_civ if is_site_government else None,
        "is_site_government": is_site_government,
        "prev_entity": dict(prev_ent) if prev_ent else None,
        "next_entity": dict(next_ent) if next_ent else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Site Detail Page ───────────────────────────────────────────────────────

@router.get("/explorer/site/{site_id}", response_class=HTMLResponse)
async def site_detail_page(site_id: int, request: Request,
                           world_id: int = Query(None),
                           kh: bool = Query(False)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        gate = await _kh_gate_check(conn, world_id, 'site', site_id, kh)
        if gate:
            return HTMLResponse(gate)

        site = await conn.fetchrow(
            "SELECT * FROM sites WHERE world_id = $1 AND id = $2",
            world_id, site_id,
        )
        if not site:
            raise HTTPException(404, f"Site #{site_id} not found")
        site = dict(site)

        world = await _get_world_info(conn, world_id)

        # Structures (join entity for affiliation, HF for deity)
        structures_raw = await conn.fetch("""
            SELECT s.id, s.name, s.type, s.entity_id, s.details,
                   e.name AS entity_name, e.type AS entity_type,
                   hf.name AS deity_name,
                   hf.id AS deity_hf_id
            FROM structures s
            LEFT JOIN entities e ON e.world_id = s.world_id AND e.id = s.entity_id
            LEFT JOIN historical_figures hf
                ON hf.world_id = s.world_id
                AND hf.id = COALESCE(
                    (s.details->>'deity_hf_id')::int,
                    (SELECT e2.worship_id FROM entities e2
                     WHERE e2.world_id = s.world_id AND e2.id = s.entity_id
                       AND e2.worship_id IS NOT NULL)
                )
            WHERE s.world_id = $1 AND s.site_id = $2
            ORDER BY s.type, s.name
        """, world_id, site_id)

        # Enrich structures with attendants (living HFs at this site
        # who are listed as structure inhabitants in the legends XML)
        all_inhabitant_ids = set()
        for s in structures_raw:
            details = s['details'] or {}
            if isinstance(details, dict):
                for hf_id in details.get('inhabitants', []):
                    all_inhabitant_ids.add(hf_id)

        # Filter: alive + residing at this site (site link OR whereabouts)
        attendant_map = {}  # hf_id -> {id, name}
        if all_inhabitant_ids:
            attendant_rows = await conn.fetch("""
                SELECT DISTINCT hf.id, hf.name
                FROM historical_figures hf
                WHERE hf.world_id = $1
                  AND hf.id = ANY($2)
                  AND hf.death_year IS NULL
                  AND (
                    -- Has a current site link to this site
                    EXISTS (
                        SELECT 1 FROM hf_site_links hsl
                        WHERE hsl.world_id = $1 AND hsl.hf_id = hf.id
                          AND hsl.site_id = $3
                          AND hsl.link_type NOT IN ('former resident')
                    )
                    -- OR whereabouts places them at this site
                    OR (hf.whereabouts->>'site_id')::int = $3
                  )
            """, world_id, list(all_inhabitant_ids), site_id)
            attendant_map = {r['id']: r['name'] for r in attendant_rows}

        structures = []
        for s in structures_raw:
            d = dict(s)
            details = d.get('details') or {}
            if isinstance(details, dict):
                d['name2'] = details.get('name2')
                raw_ids = details.get('inhabitants', [])
                d['attendants'] = [
                    {'id': hf_id, 'name': attendant_map[hf_id]}
                    for hf_id in raw_ids
                    if hf_id in attendant_map
                ]
                d['attendant_count'] = len(d['attendants'])
                d['total_listed'] = len(raw_ids)
            else:
                d['name2'] = None
                d['attendants'] = []
                d['attendant_count'] = 0
                d['total_listed'] = 0
            structures.append(d)

        # Owner entity (civilization) and governing SG
        owner = None
        if site.get('owner_entity_id'):
            owner = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, site['owner_entity_id'],
            )
        # Find the site government (SG) that governs this site
        site_government = await conn.fetchrow("""
            SELECT e.id, e.name, e.type FROM entity_site_links esl
            JOIN entities e ON e.world_id = esl.world_id AND e.id = esl.entity_id
            WHERE esl.world_id = $1 AND esl.site_id = $2
              AND esl.link_type IN ('governs', 'owner')
              AND e.type = 'sitegovernment'
            LIMIT 1
        """, world_id, site_id)
        if not site_government:
            # Fallback: check if owner_entity_id itself is a site government
            if owner and dict(owner).get('type') == 'sitegovernment':
                site_government = owner

        # Ownership timeline from JSONB history
        ownership_timeline = []
        _site_details = site.get('details') or {}
        if not isinstance(_site_details, dict):
            _site_details = {}
        oh = _site_details.get('ownership_history', [])
        if oh:
            entity_ids = [e['entity_id'] for e in oh if e.get('entity_id')]
            entity_names = {}
            if entity_ids:
                rows = await conn.fetch("""
                    SELECT id, name, type FROM entities
                    WHERE world_id = $1 AND id = ANY($2)
                """, world_id, entity_ids)
                entity_names = {r['id']: dict(r) for r in rows}
            for entry in oh:
                eid = entry.get('entity_id')
                ent = entity_names.get(eid) if eid else None
                ownership_timeline.append({
                    'year': entry['year'],
                    'event': entry['event'].replace('_', ' ').title(),
                    'entity_id': eid,
                    'entity_name': ent['name'] if ent else None,
                    'entity_type': ent['type'] if ent else None,
                })

        # Event count
        event_count = await conn.fetchval("""
            SELECT count(*) FROM event_entity_xref
            WHERE world_id = $1 AND entity_type = 'site' AND entity_id = $2
        """, world_id, site_id)

        # Recent events
        events = await conn.fetch("""
            SELECT e.id, e.year, e.seconds, e.event_type, e.details,
                   e.hf_id_1, e.hf_id_2, e.site_id, e.region_id,
                   e.entity_id_1, e.entity_id_2, e.artifact_id, e.structure_id
            FROM history_events e
            JOIN event_entity_xref x ON x.world_id = e.world_id AND x.event_id = e.id
            WHERE x.world_id = $1 AND x.entity_type = 'site' AND x.entity_id = $2
            ORDER BY e.year, e.seconds
            LIMIT 50
        """, world_id, site_id)

        # Resolve names for events
        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered_events = []
        for ev in events:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'site', site_id, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        # Residents: canonical UNION of all sources matching fetch_site_residents_batch
        # Sources: SG members + hf_site_links + position holders + whereabouts
        # No LIMIT — load all residents; the UI provides scroll + filtering
        from chronicler.api.routes.civilizations import (
            SENTIENCE_FILTER, SENTIENCE_JOIN, fetch_site_residents_count,
        )
        owner_entity_id = site.get('owner_entity_id')
        # Use the site government entity for SG membership / position checks,
        # NOT the civilization. The civ owns many sites — its position holders
        # (barons, counts etc.) are spread across sites and should only appear
        # at *their* site, not every site the civ owns.
        sg_id = dict(site_government)['id'] if site_government else None
        residents_raw = await conn.fetch(f"""
            SELECT * FROM (
                SELECT DISTINCT ON (sub.hf_id)
                       sub.hf_id, sub.link_type,
                       hf.name, hf.race, hf.caste, hf.birth_year, hf.death_year,
                       hf.is_vampire, hf.is_necromancer, hf.is_werebeast, hf.is_ghost,
                       hf.is_deity, hf.is_force, hf.is_author, hf.is_auteur,
                       hf.skills, hf.details,
                       hf.whereabouts,
                       pos.position_name,
                       mem.member_status,
                       (hf.death_year IS NULL AND {SENTIENCE_FILTER}
                        AND EXISTS (
                            SELECT 1 FROM hf_entity_links hel2
                            WHERE hel2.world_id = hf.world_id AND hel2.hf_id = hf.id
                              AND hel2.link_type = 'member'
                              AND ($3::int IS NULL OR hel2.entity_id = $3)
                        )) AS is_citizen,
                       CASE
                           WHEN hf.death_year IS NOT NULL OR NOT ({SENTIENCE_FILTER}) THEN NULL
                           WHEN mem.member_status = 'member' THEN 'SG member'
                           WHEN sub.link_type IN ('resident', 'occupation', 'seat of power') THEN 'site link'
                           WHEN sub.link_type = 'position_holder' THEN 'position'
                           ELSE NULL
                       END AS citizen_reason,
                       CASE
                           WHEN hf.death_year IS NOT NULL OR NOT ({SENTIENCE_FILTER}) THEN NULL
                           WHEN mem.member_status = 'member' THEN 'citizen'
                           WHEN sub.link_type IN ('resident', 'occupation', 'seat of power') THEN 'citizen'
                           WHEN sub.link_type = 'position_holder' THEN 'citizen'
                           WHEN sub.link_type = 'whereabouts' THEN 'whereabouts'
                           ELSE NULL
                       END AS resident_reason
                FROM (
                    -- Source 1: hf_site_links (residents/former residents)
                    SELECT hsl.hf_id, hsl.link_type,
                        CASE hsl.link_type
                            WHEN 'resident' THEN 1
                            WHEN 'occupation' THEN 2
                            WHEN 'seat of power' THEN 3
                            WHEN 'former resident' THEN 8
                            ELSE 4
                        END AS priority
                    FROM hf_site_links hsl
                    WHERE hsl.world_id = $1 AND hsl.site_id = $2
                    UNION ALL
                    -- Source 2: SG members (citizens via SG entity membership)
                    SELECT hel.hf_id, 'sg_member' AS link_type, 5 AS priority
                    FROM hf_entity_links hel
                    WHERE hel.world_id = $1
                        AND hel.entity_id = COALESCE($4, -1)
                        AND hel.link_type = 'member'
                    UNION ALL
                    -- Source 3: position holders at site government (valid positions only)
                    SELECT hpl.hf_id, 'position_holder' AS link_type, 0 AS priority
                    FROM hf_position_links hpl
                    WHERE hpl.world_id = $1 AND hpl.entity_id = COALESCE($4, -1)
                        AND hpl.end_year IS NULL
                        AND EXISTS (
                            SELECT 1 FROM entity_positions ep
                            WHERE ep.world_id = $1 AND ep.entity_id = hpl.entity_id
                              AND ep.position_id = hpl.position_id
                        )
                    UNION ALL
                    -- Source 4: physical presence via whereabouts
                    SELECT hfw.id AS hf_id, 'whereabouts' AS link_type, 6 AS priority
                    FROM historical_figures hfw
                    WHERE hfw.world_id = $1 AND hfw.death_year IS NULL
                        AND (hfw.whereabouts->>'site_id')::int = $2
                ) sub
                JOIN historical_figures hf ON hf.world_id = $1 AND hf.id = sub.hf_id
                {SENTIENCE_JOIN}
                LEFT JOIN LATERAL (
                    SELECT ep.name AS position_name
                    FROM hf_position_links hpl
                    JOIN entity_positions ep
                        ON ep.world_id = hpl.world_id AND ep.entity_id = hpl.entity_id
                        AND ep.position_id = hpl.position_id
                    WHERE hpl.world_id = $1 AND hpl.hf_id = sub.hf_id
                    ORDER BY hpl.end_year IS NULL DESC, hpl.start_year DESC
                    LIMIT 1
                ) pos ON true
                LEFT JOIN LATERAL (
                    SELECT hel.link_type AS member_status
                    FROM hf_entity_links hel
                    WHERE hel.world_id = $1 AND hel.hf_id = sub.hf_id
                      AND hel.entity_id = COALESCE($4, -1)
                    ORDER BY CASE hel.link_type WHEN 'member' THEN 0 ELSE 1 END
                    LIMIT 1
                ) mem ON true
                ORDER BY sub.hf_id, sub.priority, sub.link_type
            ) deduped
            ORDER BY link_type, name
        """, world_id, site_id, owner_entity_id, sg_id)
        # Batch-fetch profession data (jobs, entity types, events)
        res_hf_ids = [r["hf_id"] for r in residents_raw]
        res_prof_data = await batch_fetch_profession_data(conn, world_id, res_hf_ids)
        # Batch-fetch cross-entity positions for the Position column
        res_positions = await batch_fetch_positions(conn, world_id, res_hf_ids, viewing_entity_id=owner_entity_id)

        residents = []
        for r in residents_raw:
            d = dict(r)
            d["profession"] = derive_profession(d, res_prof_data.get(d["hf_id"]))
            d["position_display"] = derive_position(res_positions.get(d["hf_id"]), viewing_entity_id=owner_entity_id)
            d["race"] = _clean_race(d.get("race"))
            d.pop("skills", None)
            d.pop("details", None)
            residents.append(d)

        # ── Ne'er-do-well detection ──────────────────────────────────────
        # Query adversarial HF links to the governing SG entity
        neerdowell_info = {}  # hf_id -> {"threat_type": str, "basis": str}
        if owner_entity_id:
            adversarial_rows = await conn.fetch("""
                SELECT hel.hf_id, hel.link_type AS threat_type
                FROM hf_entity_links hel
                WHERE hel.world_id = $1 AND hel.entity_id = $2
                  AND hel.link_type IN ('enemy', 'criminal', 'prisoner',
                                        'former prisoner', 'slave', 'former slave')
            """, world_id, owner_entity_id)
            for r in adversarial_rows:
                neerdowell_info[r["hf_id"]] = {
                    "threat_type": r["threat_type"].replace("_", " ").title(),
                    "basis": "entity link",
                }

        # ── Population taxonomy: classify each resident ──────────────────
        # Priority: Ne'er-do-well > Citizen > Resident > Visitor
        # "Native" XML link types are persistent (home structure, seat of power, etc.)
        # "Materialized" link types (resident, former resident) derive from events
        # and may be stale if the HF has since moved elsewhere.
        NATIVE_STRUCTURAL_LINKS = {
            'home structure', 'home site building',
            'seat of power', 'occupation', 'hangout',
        }
        ALL_STRUCTURAL_LINKS = NATIVE_STRUCTURAL_LINKS | {'resident'}
        denizens = []
        neerdowells = []
        citizen_count = 0
        resident_count = 0
        visitor_count = 0

        for r in residents:
            hf_id = r["hf_id"]
            link_type = r.get("link_type", "")

            # Skip former residents with no other presence (fail presence gate)
            if link_type == 'former resident':
                continue

            # Presence gate: cross-check whereabouts for links that may be stale.
            # 'resident' links are materialized from settler events and may be
            # outdated. 'position_holder' links are entity-wide and may place an
            # HF at a site they've never visited. In both cases, if whereabouts
            # places the HF at a different site, skip them here.
            if link_type in ('resident', 'position_holder'):
                whereabouts = r.get("whereabouts") or {}
                if isinstance(whereabouts, dict):
                    wb_site = whereabouts.get("site_id")
                    if wb_site is not None and wb_site != site_id:
                        continue  # HF is physically at a different site

            # Priority 1: Ne'er-do-well
            ndw = neerdowell_info.get(hf_id)
            # Indirect: lair holders
            if not ndw and link_type == 'lair':
                ndw = {"threat_type": "Lair", "basis": "lair at site"}
            # Indirect: werebeast/vampire without SG membership
            if not ndw and (r.get("is_werebeast") or r.get("is_vampire")):
                if not r.get("member_status") or r["member_status"] != 'member':
                    creature = "Werebeast" if r.get("is_werebeast") else "Vampire"
                    ndw = {"threat_type": creature, "basis": f"{creature.lower()} without SG membership"}

            if ndw:
                r["population_type"] = "Ne'er-do-well"
                r["threat_type"] = ndw["threat_type"]
                r["threat_basis"] = ndw["basis"]
                r["has_structural_link"] = link_type in ALL_STRUCTURAL_LINKS
                neerdowells.append(r)
                continue

            # Priority 2: Citizen
            if r.get("is_citizen"):
                r["population_type"] = "Citizen"
                citizen_count += 1
                denizens.append(r)
                continue

            # Priority 3: Resident (structural link)
            if link_type in ALL_STRUCTURAL_LINKS:
                r["population_type"] = "Resident"
                resident_count += 1
                denizens.append(r)
                continue

            # Priority 3b: Settler via whereabouts → Resident
            whereabouts = r.get("whereabouts") or {}
            if isinstance(whereabouts, dict):
                wb_state = whereabouts.get("state", "")
                if wb_state in ("settled", "settler"):
                    r["population_type"] = "Resident"
                    resident_count += 1
                    denizens.append(r)
                    continue

            # Priority 4: Visitor (event-only presence)
            r["population_type"] = "Visitor"
            visitor_count += 1
            denizens.append(r)

        # ── Fortress denizens enrichment (live bridge data) ─────────────
        # If this site is the active fortress, enrich denizens with live
        # data from fortress_denizens and add any bridge-only entries.
        is_active_fortress = False
        live_denizen_count = 0
        fortress_row = await conn.fetchrow(
            "SELECT site_id FROM fortress_state WHERE world_id = $1 LIMIT 1",
            world_id,
        )
        if fortress_row and fortress_row["site_id"] == site_id:
            is_active_fortress = True
            fd_rows = await conn.fetch("""
                SELECT fd.hf_id, fd.unit_id, fd.name, fd.english_name,
                       fd.race, fd.status AS live_status, fd.embark,
                       fd.arrival_year, fd.arrival_tick,
                       fd.departure_year, fd.departure_cause,
                       fd.last_seen_tick, fd.narrative_value
                FROM fortress_denizens fd
                WHERE fd.world_id = $1
            """, world_id)
            # Build lookup by hf_id
            fd_by_hf = {r["hf_id"]: dict(r) for r in fd_rows if r["hf_id"]}
            fd_by_unit = {r["unit_id"]: dict(r) for r in fd_rows if r["unit_id"]}

            # Enrich existing denizens that match by hf_id
            existing_hf_ids = set()
            for d in denizens + neerdowells:
                hf_id = d.get("hf_id")
                existing_hf_ids.add(hf_id)
                fd = fd_by_hf.get(hf_id)
                if fd:
                    d["live_tracked"] = True
                    d["live_status"] = fd["live_status"]
                    d["embark"] = fd["embark"]
                    d["arrival_year"] = fd["arrival_year"]
                    d["unit_id"] = fd["unit_id"]
                    d["narrative_value"] = fd["narrative_value"]
                    live_denizen_count += 1

            # Add fortress_denizens with hf_id NOT already in denizens list
            # Skip departed/missing entries — they're no longer present
            for fd in fd_rows:
                if not fd["hf_id"] or fd["hf_id"] in existing_hf_ids:
                    continue
                # Skip denizens that have departed the fortress
                if fd["departure_year"] is not None:
                    continue
                # Skip 'missing' status — unit no longer visible to bridge
                if fd["live_status"] == "missing":
                    continue
                # Fetch HF record for display
                hf = await conn.fetchrow(
                    "SELECT * FROM historical_figures WHERE world_id = $1 AND id = $2",
                    world_id, fd["hf_id"],
                )
                if not hf:
                    continue
                hf = dict(hf)
                entry = {
                    "hf_id": fd["hf_id"],
                    "link_type": "fortress_denizen",
                    "name": hf.get("name") or fd["name"],
                    "race": hf.get("race") or fd["race"],
                    "caste": hf.get("caste"),
                    "birth_year": hf.get("birth_year"),
                    "death_year": hf.get("death_year"),
                    "is_vampire": hf.get("is_vampire"),
                    "is_necromancer": hf.get("is_necromancer"),
                    "is_werebeast": hf.get("is_werebeast"),
                    "is_ghost": hf.get("is_ghost"),
                    "is_deity": hf.get("is_deity"),
                    "is_force": hf.get("is_force"),
                    "whereabouts": hf.get("whereabouts"),
                    "position_name": None,
                    "member_status": None,
                    "is_citizen": False,
                    "citizen_reason": "live bridge",
                    "resident_reason": "live bridge",
                    "profession": "",
                    "position_display": "",
                    # Live data
                    "live_tracked": True,
                    "live_status": fd["live_status"],
                    "embark": fd["embark"],
                    "arrival_year": fd["arrival_year"],
                    "unit_id": fd["unit_id"],
                    "narrative_value": fd["narrative_value"],
                }
                existing_hf_ids.add(fd["hf_id"])
                # Classify: if live_status is resident → Resident
                if fd["live_status"] in ("resident", "visitor"):
                    entry["population_type"] = "Resident"
                    resident_count += 1
                else:
                    entry["population_type"] = "Visitor"
                    visitor_count += 1
                denizens.append(entry)
                live_denizen_count += 1

            # Enrich bridge-added entries with position data
            bridge_hf_ids = [d["hf_id"] for d in denizens
                             if d.get("link_type") == "fortress_denizen"
                             and not d.get("position_display")]
            if bridge_hf_ids:
                bridge_positions = await batch_fetch_positions(
                    conn, world_id, bridge_hf_ids,
                    viewing_entity_id=owner_entity_id)
                for d in denizens:
                    if d.get("link_type") == "fortress_denizen" and d["hf_id"] in bridge_positions:
                        d["position_display"] = derive_position(
                            bridge_positions[d["hf_id"]],
                            viewing_entity_id=owner_entity_id) or ""

        # Residents: living sentient HFs at this site
        residents_count = await fetch_site_residents_count(conn, world_id, site_id)

        # Region info: find which region this site belongs to
        # Sites don't have region_id directly; use coordinates overlap or events
        region_info = None
        if site.get('coords'):
            # Try to find region from event cross-references
            region_row = await conn.fetchrow("""
                SELECT DISTINCT r.id, r.name, r.type
                FROM regions r
                JOIN event_entity_xref xr ON xr.world_id = r.world_id
                    AND xr.entity_type = 'region' AND xr.entity_id = r.id
                JOIN event_entity_xref xs ON xs.world_id = xr.world_id
                    AND xs.event_id = xr.event_id
                    AND xs.entity_type = 'site' AND xs.entity_id = $2
                WHERE r.world_id = $1
                LIMIT 1
            """, world_id, site_id)
            if region_row:
                region_info = dict(region_row)

        # Co-located sites (same coordinates, different site)
        co_located = []
        if site.get('coord_x') is not None and site.get('coord_y') is not None:
            co_located_rows = await conn.fetch("""
                SELECT id, name, type FROM sites
                WHERE world_id = $1 AND coord_x = $2 AND coord_y = $3
                  AND id != $4
                ORDER BY name
            """, world_id, site['coord_x'], site['coord_y'], site_id)
            co_located = [dict(r) for r in co_located_rows]

        # Prev/Next
        prev_site = await conn.fetchrow("""
            SELECT id, name FROM sites WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, site_id)
        next_site = await conn.fetchrow("""
            SELECT id, name FROM sites WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, site_id)

    _sd = site.get('details')
    is_ruin = _sd.get('ruin') if isinstance(_sd, dict) else False

    return templates.TemplateResponse("site_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Site",
        "entity_name": site['name'] or f"Site #{site_id}",
        "entity_alt_name": None,
        "site": site,
        "world": world,
        "world_id": world_id,
        "is_ruin": is_ruin,
        "structures": [dict(s) for s in structures],
        "owner": dict(owner) if owner else None,
        "site_government": dict(site_government) if site_government else None,
        "ownership_timeline": ownership_timeline,
        "denizens": denizens,
        "neerdowells": neerdowells,
        "citizen_count": citizen_count,
        "resident_count": resident_count,
        "visitor_count": visitor_count,
        "denizens_count": len(denizens),
        "neerdowells_count": len(neerdowells),
        "residents": residents,
        "residents_count": residents_count,
        "events": rendered_events,
        "event_count": event_count,
        "region_info": region_info,
        "co_located": co_located,
        "prev_site": dict(prev_site) if prev_site else None,
        "next_site": dict(next_site) if next_site else None,
        "linker": _linker,
        "calendar": DFCalendar,
        "is_active_fortress": is_active_fortress,
        "live_denizen_count": live_denizen_count,
    })


# ─── Artifact Detail Page ─────────────────────────────────────────────────

@router.get("/explorer/artifact/{artifact_id}", response_class=HTMLResponse)
async def artifact_detail_page(artifact_id: int, request: Request,
                               world_id: int = Query(None),
                               kh: bool = Query(False)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        gate = await _kh_gate_check(conn, world_id, 'artifact', artifact_id, kh)
        if gate:
            return HTMLResponse(gate)

        artifact = await conn.fetchrow(
            "SELECT * FROM artifacts WHERE world_id = $1 AND id = $2",
            world_id, artifact_id,
        )
        if not artifact:
            raise HTTPException(404, f"Artifact #{artifact_id} not found")
        artifact = dict(artifact)

        world = await _get_world_info(conn, world_id)

        # Creator HF
        creator = None
        if artifact.get('creator_hf_id'):
            creator = await conn.fetchrow(
                "SELECT id, name, race FROM historical_figures WHERE world_id = $1 AND id = $2",
                world_id, artifact['creator_hf_id'],
            )

        # Current holder HF
        holder = None
        if artifact.get('holder_hf_id'):
            holder = await conn.fetchrow(
                "SELECT id, name, race FROM historical_figures WHERE world_id = $1 AND id = $2",
                world_id, artifact['holder_hf_id'],
            )

        # Creation site
        site = None
        if artifact.get('site_id'):
            site = await conn.fetchrow(
                "SELECT id, name, type FROM sites WHERE world_id = $1 AND id = $2",
                world_id, artifact['site_id'],
            )

        # Written content link (from details JSONB)
        written_content = None
        details = artifact.get('details') or {}
        wc_id = details.get('writing_written_content_id') or details.get('written_content_id')
        if wc_id:
            written_content = await conn.fetchrow(
                "SELECT id, title, form FROM written_contents WHERE world_id = $1 AND id = $2",
                world_id, int(wc_id),
            )

        # Events involving this artifact
        event_count = await conn.fetchval("""
            SELECT count(*) FROM event_entity_xref
            WHERE world_id = $1 AND entity_type = 'artifact' AND entity_id = $2
        """, world_id, artifact_id)

        events = await conn.fetch("""
            SELECT e.id, e.year, e.seconds, e.event_type, e.details,
                   e.hf_id_1, e.hf_id_2, e.site_id, e.region_id,
                   e.entity_id_1, e.entity_id_2, e.artifact_id, e.structure_id
            FROM history_events e
            JOIN event_entity_xref x ON x.world_id = e.world_id AND x.event_id = e.id
            WHERE x.world_id = $1 AND x.entity_type = 'artifact' AND x.entity_id = $2
            ORDER BY e.year, e.seconds
            LIMIT 50
        """, world_id, artifact_id)

        # Batch resolve names for events
        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered_events = []
        for ev in events:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'artifact', artifact_id, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        # Prev/Next
        prev_art = await conn.fetchrow("""
            SELECT id, name FROM artifacts WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, artifact_id)
        next_art = await conn.fetchrow("""
            SELECT id, name FROM artifacts WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, artifact_id)

    return templates.TemplateResponse("artifact_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Artifact",
        "entity_name": artifact['name'] or f"Artifact #{artifact_id}",
        "entity_alt_name": None,
        "artifact": artifact,
        "world": world,
        "world_id": world_id,
        "creator": dict(creator) if creator else None,
        "holder": dict(holder) if holder else None,
        "site": dict(site) if site else None,
        "written_content": dict(written_content) if written_content else None,
        "events": rendered_events,
        "event_count": event_count,
        "prev_artifact": dict(prev_art) if prev_art else None,
        "next_artifact": dict(next_art) if next_art else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Region Detail Page ───────────────────────────────────────────────────

@router.get("/explorer/region/{region_id}", response_class=HTMLResponse)
async def region_detail_page(region_id: int, request: Request,
                             world_id: int = Query(None),
                             kh: bool = Query(False)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        gate = await _kh_gate_check(conn, world_id, 'region', region_id, kh)
        if gate:
            return HTMLResponse(gate)

        region = await conn.fetchrow(
            "SELECT * FROM regions WHERE world_id = $1 AND id = $2",
            world_id, region_id,
        )
        if not region:
            raise HTTPException(404, f"Region #{region_id} not found")
        region = dict(region)

        world = await _get_world_info(conn, world_id)

        # Sites in this region (sites don't have region_id directly, but events
        # link regions to sites — use coords overlap or event_entity_xref)
        # For now, query sites whose events also reference this region
        sites_in_region = await conn.fetch("""
            SELECT DISTINCT s.id, s.name, s.type
            FROM sites s
            JOIN event_entity_xref xs ON xs.world_id = s.world_id
                 AND xs.entity_type = 'site' AND xs.entity_id = s.id
            JOIN event_entity_xref xr ON xr.world_id = xs.world_id
                 AND xr.event_id = xs.event_id
                 AND xr.entity_type = 'region' AND xr.entity_id = $2
            WHERE s.world_id = $1
            ORDER BY s.name
            LIMIT 50
        """, world_id, region_id)

        # Events in this region
        event_count = await conn.fetchval("""
            SELECT count(*) FROM event_entity_xref
            WHERE world_id = $1 AND entity_type = 'region' AND entity_id = $2
        """, world_id, region_id)

        events = await conn.fetch("""
            SELECT e.id, e.year, e.seconds, e.event_type, e.details,
                   e.hf_id_1, e.hf_id_2, e.site_id, e.region_id,
                   e.entity_id_1, e.entity_id_2, e.artifact_id, e.structure_id
            FROM history_events e
            JOIN event_entity_xref x ON x.world_id = e.world_id AND x.event_id = e.id
            WHERE x.world_id = $1 AND x.entity_type = 'region' AND x.entity_id = $2
            ORDER BY e.year, e.seconds
            LIMIT 50
        """, world_id, region_id)

        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered_events = []
        for ev in events:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'region', region_id, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        prev_reg = await conn.fetchrow("""
            SELECT id, name FROM regions WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, region_id)
        next_reg = await conn.fetchrow("""
            SELECT id, name FROM regions WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, region_id)

    # Determine evilness from region type name
    rtype = (region.get('type') or '').lower()
    if 'evil' in rtype or 'sinister' in rtype or 'terrifying' in rtype:
        evilness = 'evil'
    elif 'good' in rtype or 'serene' in rtype or 'mirthful' in rtype or 'joyous' in rtype:
        evilness = 'benign'
    else:
        evilness = 'neutral'

    return templates.TemplateResponse("region_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Region",
        "entity_name": region['name'] or f"Region #{region_id}",
        "entity_alt_name": None,
        "region": region,
        "world": world,
        "world_id": world_id,
        "evilness": evilness,
        "sites_in_region": [dict(s) for s in sites_in_region],
        "events": rendered_events,
        "event_count": event_count,
        "prev_region": dict(prev_reg) if prev_reg else None,
        "next_region": dict(next_reg) if next_reg else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Structure Detail Page ────────────────────────────────────────────────

@router.get("/explorer/site/{site_id}/structure/{structure_id}", response_class=HTMLResponse)
async def structure_detail_page(site_id: int, structure_id: int, request: Request,
                                world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        structure = await conn.fetchrow(
            "SELECT * FROM structures WHERE world_id = $1 AND site_id = $2 AND id = $3",
            world_id, site_id, structure_id,
        )
        if not structure:
            raise HTTPException(404, f"Structure #{structure_id} at site #{site_id} not found")
        structure = dict(structure)

        world = await _get_world_info(conn, world_id)

        # Parent site
        parent_site = await conn.fetchrow(
            "SELECT id, name, type FROM sites WHERE world_id = $1 AND id = $2",
            world_id, site_id,
        )

        # Owner entity
        owner_entity = None
        if structure.get('entity_id'):
            owner_entity = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, structure['entity_id'],
            )

        # Deity + Religion entity
        deity = None
        religion_entity = None
        details = structure.get('details') or {}

        # Try direct deity fields first
        deity_hf_id = details.get('deity') or details.get('worship_hf_id') or details.get('deity_hf_id')

        # If no direct deity, resolve through religion entity
        religion_entity_id = details.get('religion_entity_id') or structure.get('entity_id')
        if religion_entity_id:
            religion_entity = await conn.fetchrow(
                "SELECT id, name, type, worship_id, details FROM entities WHERE world_id = $1 AND id = $2",
                world_id, int(religion_entity_id),
            )
            if religion_entity and not deity_hf_id:
                # worship_id column is the actual deity; histfig_id in details is just a member
                deity_hf_id = religion_entity['worship_id']

        if deity_hf_id:
            deity = await conn.fetchrow(
                "SELECT id, name, race FROM historical_figures WHERE world_id = $1 AND id = $2",
                world_id, int(deity_hf_id),
            )

        # Positions defined for the religion/owning entity
        positions = []
        position_holders = []
        pos_entity_id = religion_entity_id or structure.get('entity_id')
        if pos_entity_id:
            positions = await conn.fetch(
                "SELECT position_id, name FROM entity_positions WHERE world_id = $1 AND entity_id = $2 ORDER BY position_id",
                world_id, int(pos_entity_id),
            )
            position_holders = await conn.fetch("""
                SELECT pl.position_id, pl.start_year, pl.end_year, hf.id as hf_id, hf.name as hf_name
                FROM hf_position_links pl
                JOIN historical_figures hf ON hf.world_id = pl.world_id AND hf.id = pl.hf_id
                WHERE pl.world_id = $1 AND pl.entity_id = $2
                  AND NOT (pl.start_year IS NULL AND EXISTS (
                      SELECT 1 FROM hf_position_links pl2
                      WHERE pl2.world_id = pl.world_id AND pl2.hf_id = pl.hf_id
                        AND pl2.entity_id = pl.entity_id AND pl2.position_id = pl.position_id
                        AND pl2.start_year IS NOT NULL
                  ))
                ORDER BY pl.position_id, pl.start_year NULLS LAST
            """, world_id, int(pos_entity_id))

        # Membership
        members = []
        if pos_entity_id:
            members = await conn.fetch("""
                SELECT hel.hf_id, hel.link_type, hf.name as hf_name
                FROM hf_entity_links hel
                JOIN historical_figures hf ON hf.world_id = hel.world_id AND hf.id = hel.hf_id
                WHERE hel.world_id = $1 AND hel.entity_id = $2
                ORDER BY hel.link_type, hf.name
                LIMIT 100
            """, world_id, int(pos_entity_id))

        # Events — query directly by structure_id + site_id
        # (structure IDs are site-local, so xref entity_id alone is ambiguous)
        event_count = await conn.fetchval("""
            SELECT count(*) FROM history_events
            WHERE world_id = $1 AND structure_id = $2 AND site_id = $3
        """, world_id, structure_id, site_id)
        events = await conn.fetch("""
            SELECT id, year, seconds, event_type, details,
                   hf_id_1, hf_id_2, site_id, region_id,
                   entity_id_1, entity_id_2, artifact_id, structure_id
            FROM history_events
            WHERE world_id = $1 AND structure_id = $2 AND site_id = $3
            ORDER BY year, seconds
            LIMIT 50
        """, world_id, structure_id, site_id)

        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered_events = []
        for ev in events:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'structure', structure_id, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        # Attendants: living HFs at this site who are listed as structure inhabitants
        attendants = []
        raw_inhabitant_ids = details.get('inhabitants', []) if isinstance(details, dict) else []
        total_listed = len(raw_inhabitant_ids)
        if raw_inhabitant_ids:
            attendant_rows = await conn.fetch("""
                SELECT DISTINCT hf.id, hf.name, hf.race, hf.caste, hf.associated_type
                FROM historical_figures hf
                WHERE hf.world_id = $1
                  AND hf.id = ANY($2)
                  AND hf.death_year IS NULL
                  AND (
                    EXISTS (
                        SELECT 1 FROM hf_site_links hsl
                        WHERE hsl.world_id = $1 AND hsl.hf_id = hf.id
                          AND hsl.site_id = $3
                          AND hsl.link_type NOT IN ('former resident')
                    )
                    OR (hf.whereabouts->>'site_id')::int = $3
                  )
                ORDER BY hf.name
            """, world_id, raw_inhabitant_ids, site_id)
            attendants = [dict(r) for r in attendant_rows]

            att_ids = [a['id'] for a in attendants]

            # Most recent event at this site for each attendant (full row for rendering)
            latest_events = await conn.fetch("""
                SELECT DISTINCT ON (hf_id) hf_id,
                       id, year, seconds, event_type, details,
                       hf_id_1, hf_id_2, site_id, region_id,
                       entity_id_1, entity_id_2, artifact_id, structure_id
                FROM (
                    SELECT hf_id_1 AS hf_id, id, year, seconds, event_type, details,
                           hf_id_1, hf_id_2, site_id, region_id,
                           entity_id_1, entity_id_2, artifact_id, structure_id
                    FROM history_events
                    WHERE world_id = $1 AND site_id = $2
                      AND hf_id_1 = ANY($3)
                    UNION ALL
                    SELECT hf_id_2 AS hf_id, id, year, seconds, event_type, details,
                           hf_id_1, hf_id_2, site_id, region_id,
                           entity_id_1, entity_id_2, artifact_id, structure_id
                    FROM history_events
                    WHERE world_id = $1 AND site_id = $2
                      AND hf_id_2 = ANY($3)
                ) sub
                ORDER BY hf_id, year DESC, seconds DESC
            """, world_id, site_id, att_ids)

            # Resolve entity names for rendering event text
            ev_refs = set()
            for ev in latest_events:
                merged = merge_columns_into_details(dict(ev))
                from chronicler.explorer.perspective import ENTITY_REF_FIELDS
                for field, etype in ENTITY_REF_FIELDS.items():
                    val = merged.get(field)
                    if val is not None:
                        ev_refs.add((etype, int(val)))
            ev_name_map = await _name_cache.batch_resolve(
                conn, world_id, list(ev_refs)
            )

            # Render event text from each HF's perspective, then abbreviate
            import re as _re
            att_caste = {a['id']: a.get('caste') for a in attendants}
            _site_name = dict(parent_site)['name'] if parent_site else ''
            event_map = {}
            for ev in latest_events:
                ev_dict = dict(ev)
                hf_id = ev_dict.pop('hf_id')
                # Render from the HF's perspective so their name becomes a pronoun
                hf_renderer = PerspectiveRenderer(
                    _linker, world_id,
                    perspective_caste=att_caste.get(hf_id),
                )
                raw_text = hf_renderer.render_event(
                    ev_dict, 'hf', hf_id, ev_name_map
                )
                # Strip HTML tags for plain-text abbreviation
                plain = _re.sub(r'<[^>]+>', '', raw_text)
                # Remove leading pronoun (he/she/they/it + space)
                plain = _re.sub(
                    r'^(he|she|they|it|his|her|their|its)\s+',
                    '', plain, flags=_re.IGNORECASE,
                )
                # Remove trailing " at/in <site_name>" or " at here"
                if _site_name:
                    plain = _re.sub(
                        r'\s+(at|in)\s+(' + _re.escape(_site_name) + r'|here)\.?$',
                        '', plain, flags=_re.IGNORECASE,
                    )
                else:
                    plain = _re.sub(
                        r'\s+(at|in)\s+here\.?$',
                        '', plain, flags=_re.IGNORECASE,
                    )
                event_map[hf_id] = {
                    'year': ev_dict['year'],
                    'seconds': ev_dict['seconds'],
                    'event_type': ev_dict['event_type'],
                    'text': plain.strip(),
                }

            # ── Position cascade (5-tier waterfall) ──
            # T1: Formal named position (hf_position_links, end_year IS NULL)
            att_positions = await conn.fetch("""
                SELECT pl.hf_id,
                       COALESCE(ep.name, 'Position ' || pl.position_id) AS position_name,
                       e.name AS entity_name,
                       CASE WHEN ep.name IS NOT NULL THEN 0 ELSE 1 END AS name_rank
                FROM hf_position_links pl
                JOIN entities e ON e.world_id = pl.world_id AND e.id = pl.entity_id
                LEFT JOIN entity_positions ep
                    ON ep.world_id = pl.world_id
                    AND ep.entity_id = pl.entity_id
                    AND ep.position_id = pl.position_id
                WHERE pl.world_id = $1
                  AND pl.hf_id = ANY($2)
                  AND pl.end_year IS NULL
                ORDER BY pl.hf_id,
                         CASE WHEN ep.name IS NOT NULL THEN 0 ELSE 1 END,
                         pl.start_year DESC NULLS LAST
            """, world_id, att_ids)
            pos_t1 = {}
            for r in att_positions:
                if r['hf_id'] not in pos_t1:
                    pos_t1[r['hf_id']] = {
                        'position_name': r['position_name'],
                        'position_entity': r['entity_name'],
                        'position_tier': 'position',
                    }

            # T2: Most recent scholarly job (change hf job event)
            latest_jobs = await conn.fetch("""
                SELECT DISTINCT ON (hf_id_1) hf_id_1 AS hf_id,
                       details->>'new_job' AS new_job, year
                FROM history_events
                WHERE world_id = $1
                  AND event_type = 'change hf job'
                  AND hf_id_1 = ANY($2)
                  AND details->>'new_job' IS NOT NULL
                  AND details->>'new_job' != 'standard'
                ORDER BY hf_id_1, year DESC
            """, world_id, att_ids)
            job_map = {r['hf_id']: r for r in latest_jobs}

            # T3: SG position — find site government entity
            sg_entity = await conn.fetchrow("""
                SELECT e.id, e.name FROM entity_site_links esl
                JOIN entities e ON e.world_id = esl.world_id
                    AND e.id = esl.entity_id
                WHERE esl.world_id = $1 AND esl.site_id = $2
                  AND esl.link_type IN ('governs', 'owner')
                  AND e.type = 'sitegovernment'
                LIMIT 1
            """, world_id, site_id)
            sg_positions = {}
            if sg_entity:
                sg_pos_rows = await conn.fetch("""
                    SELECT pl.hf_id,
                           COALESCE(ep.name, 'Position ' || pl.position_id)
                               AS position_name
                    FROM hf_position_links pl
                    LEFT JOIN entity_positions ep
                        ON ep.world_id = pl.world_id
                        AND ep.entity_id = pl.entity_id
                        AND ep.position_id = pl.position_id
                    WHERE pl.world_id = $1
                      AND pl.entity_id = $2
                      AND pl.hf_id = ANY($3)
                      AND pl.end_year IS NULL
                    ORDER BY pl.hf_id,
                             CASE WHEN ep.name IS NOT NULL THEN 0
                                  ELSE 1 END,
                             pl.start_year DESC NULLS LAST
                """, world_id, sg_entity['id'], att_ids)
                for r in sg_pos_rows:
                    if r['hf_id'] not in sg_positions:
                        sg_positions[r['hf_id']] = r['position_name']

            # Assemble: cascade T1 → T2 → T3 → T4 (occupation link) → T5 (associated_type)
            for a in attendants:
                ev = event_map.get(a['id'])
                if ev:
                    a['last_event_type'] = ev['event_type']
                    a['last_event_date'] = DFCalendar.format_short(
                        ev['year'], ev['seconds']
                    )
                    a['last_event_text'] = ev['text']
                    a['last_event_sort'] = (
                        ev['year'] * 1000000 + (ev['seconds'] or 0)
                    )

                # T1: Formal position
                t1 = pos_t1.get(a['id'])
                if t1:
                    a['position_name'] = t1['position_name']
                    a['position_entity'] = t1['position_entity']
                    a['position_tier'] = 'position'
                    continue

                # T2: Scholarly job from change_hf_job event
                t2 = job_map.get(a['id'])
                if t2 and t2['new_job']:
                    a['position_name'] = t2['new_job'].replace('_', ' ')
                    a['position_entity'] = None
                    a['position_tier'] = 'job'
                    continue

                # T3: SG position
                t3 = sg_positions.get(a['id'])
                if t3:
                    a['position_name'] = t3
                    a['position_entity'] = sg_entity['name'] if sg_entity else None
                    a['position_tier'] = 'sg'
                    continue

                # T4: associated_type (base DF profession)
                at = a.get('associated_type')
                if at and at.lower() != 'standard':
                    a['position_name'] = at.replace('_', ' ')
                    a['position_entity'] = None
                    a['position_tier'] = 'profession'

    # Structure type badge class
    stype = (structure.get('type') or '').lower()
    STRUCTURE_BADGE_MAP = {
        'temple': 'badge-deity', 'tomb': 'badge-dead', 'mead_hall': 'badge-civ',
        'library': 'badge-type', 'dungeon': 'badge-vampire', 'tower': 'badge-type',
        'keep': 'badge-leader', 'inn': 'badge-site', 'tavern': 'badge-site',
        'market': 'badge-site', 'guildhall': 'badge-civ', 'counting_house': 'badge-type',
    }
    badge_class = STRUCTURE_BADGE_MAP.get(stype, 'badge-type')

    # Build position map: {position_id: {name, holders: [{hf_id, hf_name, start, end}]}}
    pos_map = {}
    for p in positions:
        pos_map[p['position_id']] = {'name': p['name'], 'holders': []}
    for ph in position_holders:
        pid = ph['position_id']
        if pid not in pos_map:
            pos_map[pid] = {'name': f'Position {pid}', 'holders': []}
        pos_map[pid]['holders'].append({
            'hf_id': ph['hf_id'], 'hf_name': ph['hf_name'],
            'start_year': ph['start_year'], 'end_year': ph['end_year'],
        })

    # Avoid redundant Owner/Sect when they point to the same entity
    show_religion = religion_entity and (
        not owner_entity or religion_entity['id'] != owner_entity['id']
    )

    return templates.TemplateResponse("structure_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Structure",
        "entity_name": structure['name'] or f"Structure #{structure_id}",
        "entity_alt_name": details.get('name2'),
        "structure": structure,
        "world": world,
        "world_id": world_id,
        "site_id": site_id,
        "parent_site": dict(parent_site) if parent_site else None,
        "owner_entity": dict(owner_entity) if owner_entity else None,
        "deity": dict(deity) if deity else None,
        "religion_entity": dict(religion_entity) if show_religion else None,
        "positions": pos_map,
        "members": [dict(m) for m in members],
        "badge_class": badge_class,
        "events": rendered_events,
        "event_count": event_count,
        "attendants": attendants,
        "total_listed": total_listed,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Written Content Detail Page ──────────────────────────────────────────

@router.get("/explorer/written_content/{wc_id}", response_class=HTMLResponse)
async def written_content_detail_page(wc_id: int, request: Request,
                                      world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        wc = await conn.fetchrow(
            "SELECT * FROM written_contents WHERE world_id = $1 AND id = $2",
            world_id, wc_id,
        )
        if not wc:
            raise HTTPException(404, f"Written content #{wc_id} not found")
        wc = dict(wc)

        world = await _get_world_info(conn, world_id)

        # Author
        author = None
        if wc.get('author_hf_id'):
            author = await conn.fetchrow(
                "SELECT id, name, race FROM historical_figures WHERE world_id = $1 AND id = $2",
                world_id, wc['author_hf_id'],
            )

        # Referenced entities from details.references[] array
        details = wc.get('details') or {}
        raw_refs = details.get('references') or []
        # Group reference IDs by type; track counts for all types
        ref_ids_by_type = {}
        ref_counts_by_type = {}
        for ref in raw_refs:
            rtype = ref.get('type')
            rid = ref.get('id')
            if rtype:
                ref_counts_by_type[rtype] = ref_counts_by_type.get(rtype, 0) + 1
                if rid is not None:
                    ref_ids_by_type.setdefault(rtype, []).append(int(rid))

        referenced_hfs = []
        if ref_ids_by_type.get('HISTORICAL_FIGURE'):
            referenced_hfs = await conn.fetch(
                "SELECT id, name, race FROM historical_figures WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, ref_ids_by_type['HISTORICAL_FIGURE'],
            )
        referenced_sites = []
        if ref_ids_by_type.get('SITE'):
            referenced_sites = await conn.fetch(
                "SELECT id, name, type FROM sites WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, ref_ids_by_type['SITE'],
            )
        referenced_entities = []
        if ref_ids_by_type.get('ENTITY'):
            referenced_entities = await conn.fetch(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, ref_ids_by_type['ENTITY'],
            )
        referenced_events = []
        if ref_ids_by_type.get('HISTORICAL_EVENT'):
            referenced_events = await conn.fetch(
                "SELECT id, event_type, year FROM history_events WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, ref_ids_by_type['HISTORICAL_EVENT'],
            )
        referenced_wcs = []
        if ref_ids_by_type.get('WRITTEN_CONTENT'):
            referenced_wcs = await conn.fetch(
                "SELECT id, title, form FROM written_contents WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, ref_ids_by_type['WRITTEN_CONTENT'],
            )
        # Collect non-linkable reference types for display (use counts, not just ID'd refs)
        other_refs = []
        for rtype in ('KNOWLEDGE_SCHOLAR_FLAG', 'VALUE_LEVEL', 'MUSICAL_FORM',
                       'POETIC_FORM', 'DANCE_FORM', 'LANGUAGE', 'INTERACTION',
                       'ABSTRACT_BUILDING'):
            if rtype in ref_counts_by_type:
                other_refs.append({'type': rtype.replace('_', ' ').title(),
                                   'count': ref_counts_by_type[rtype]})

        # Associated artifact (books)
        associated_artifact = None
        assoc_artifact_id = details.get('artifact_id')
        if assoc_artifact_id:
            associated_artifact = await conn.fetchrow(
                "SELECT id, name, material, item_type FROM artifacts WHERE world_id = $1 AND id = $2",
                world_id, int(assoc_artifact_id),
            )

        # Art form linkage (form_id -> art_forms with correct form_type)
        art_form = None
        form_id = details.get('form_id')
        if form_id is not None:
            form_type_map = {
                'poem': 'poetic', 'musical composition': 'musical',
                'choreography': 'dance',
            }
            mapped_type = form_type_map.get(wc.get('form'))
            if mapped_type:
                art_form = await conn.fetchrow(
                    "SELECT id, name, description, form_type FROM art_forms "
                    "WHERE world_id = $1 AND id = $2 AND form_type = $3",
                    world_id, int(form_id), mapped_type,
                )

        # Composition event (when/why/how it was written)
        composition_event = await conn.fetchrow("""
            SELECT id, year, details FROM history_events
            WHERE world_id = $1 AND event_type = 'written content composed'
            AND details->>'wc_id' = $2
            LIMIT 1
        """, world_id, str(wc_id))
        composition = None
        if composition_event:
            ce = dict(composition_event)
            ce_details = ce.get('details') or {}
            composition = {
                'event_id': ce['id'],
                'year': ce['year'],
                'circumstance': ce_details.get('circumstance'),
                'reason': ce_details.get('reason'),
            }
            # Resolve circumstance/reason HF links
            reason_id = ce_details.get('reason_id')
            circ_id = ce_details.get('circumstance_id')
            link_ids = set()
            if reason_id:
                link_ids.add(int(reason_id))
            if circ_id:
                link_ids.add(int(circ_id))
            if link_ids:
                linked_hfs = await conn.fetch(
                    "SELECT id, name FROM historical_figures WHERE world_id = $1 AND id = ANY($2::int[])",
                    world_id, list(link_ids),
                )
                hf_map = {r['id']: r['name'] for r in linked_hfs}
                if reason_id:
                    composition['reason_hf'] = {'id': int(reason_id),
                                                'name': hf_map.get(int(reason_id))}
                if circ_id:
                    composition['circumstance_hf'] = {'id': int(circ_id),
                                                      'name': hf_map.get(int(circ_id))}

        # Prev/Next
        prev_wc = await conn.fetchrow("""
            SELECT id, title FROM written_contents WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, wc_id)
        next_wc = await conn.fetchrow("""
            SELECT id, title FROM written_contents WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, wc_id)

    return templates.TemplateResponse("written_content_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Written Content",
        "entity_name": wc['title'] or f"Written Content #{wc_id}",
        "entity_alt_name": None,
        "wc": wc,
        "world": world,
        "world_id": world_id,
        "author": dict(author) if author else None,
        "referenced_hfs": [dict(r) for r in referenced_hfs],
        "referenced_sites": [dict(r) for r in referenced_sites],
        "referenced_entities": [dict(r) for r in referenced_entities],
        "referenced_events": [dict(r) for r in referenced_events],
        "referenced_wcs": [dict(r) for r in referenced_wcs],
        "other_refs": other_refs,
        "associated_artifact": dict(associated_artifact) if associated_artifact else None,
        "art_form": dict(art_form) if art_form else None,
        "composition": composition,
        "author_roll": details.get('author_roll'),
        "prev_wc": dict(prev_wc) if prev_wc else None,
        "next_wc": dict(next_wc) if next_wc else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


def _collection_display_name(collection, occasion_info, coll_type, event_schedule_id, occasion_schedules):
    """Derive a meaningful display name for event collections."""
    festival_name = occasion_info['name'] if occasion_info and occasion_info.get('name') else None
    coll_name = collection.get('name')
    # For parent occasion collections, use the festival name
    if coll_type == 'occasion' and festival_name:
        return festival_name
    # For child collections (performance/ceremony/etc.), combine schedule type with festival
    if coll_type in ('performance', 'ceremony', 'procession', 'competition', 'dance_performance'):
        schedule_label = coll_type.replace('_', ' ').title()
        # If we know which schedule this maps to, use its specific type
        if event_schedule_id is not None and occasion_schedules:
            for sched in occasion_schedules:
                if sched.get('schedule_id') == event_schedule_id:
                    schedule_label = (sched.get('type') or coll_type).replace('_', ' ').title()
                    if sched.get('ref_name'):
                        schedule_label = f"{schedule_label}: {sched['ref_name']}"
                    break
        if festival_name:
            return f"{schedule_label} — {festival_name}"
        return schedule_label
    return coll_name or (festival_name if festival_name else f"Collection #{collection['id']}")


# ─── Event Collection Detail Page ─────────────────────────────────────────

@router.get("/explorer/collection/{collection_id}", response_class=HTMLResponse)
async def collection_detail_page(collection_id: int, request: Request,
                                 world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        collection = await conn.fetchrow(
            "SELECT * FROM history_event_collections WHERE world_id = $1 AND id = $2",
            world_id, collection_id,
        )
        if not collection:
            raise HTTPException(404, f"Event collection #{collection_id} not found")
        collection = dict(collection)

        world = await _get_world_info(conn, world_id)

        # Attacker / Defender entities
        attacker = None
        if collection.get('attacker_entity_id'):
            attacker = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, collection['attacker_entity_id'],
            )
        defender = None
        if collection.get('defender_entity_id'):
            defender = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, collection['defender_entity_id'],
            )

        # Site / Region
        site = None
        if collection.get('site_id'):
            site = await conn.fetchrow(
                "SELECT id, name, type FROM sites WHERE world_id = $1 AND id = $2",
                world_id, collection['site_id'],
            )
        col_region = None
        if collection.get('region_id'):
            col_region = await conn.fetchrow(
                "SELECT id, name, type FROM regions WHERE world_id = $1 AND id = $2",
                world_id, collection['region_id'],
            )

        # Parent collection
        parent_collection = None
        if collection.get('parent_id'):
            parent_collection = await conn.fetchrow(
                "SELECT id, name, type, attacker_entity_id, defender_entity_id "
                "FROM history_event_collections WHERE world_id = $1 AND id = $2",
                world_id, collection['parent_id'],
            )

        # Inherit attacker/defender from parent war for battle sub-collections
        if not attacker and parent_collection and parent_collection.get('attacker_entity_id'):
            attacker = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, parent_collection['attacker_entity_id'],
            )
        if not defender and parent_collection and parent_collection.get('defender_entity_id'):
            defender = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, parent_collection['defender_entity_id'],
            )

        # Child collections — check both parent_id (war/battle hierarchy)
        # and collection_subcollections (occasion/competition/beast attack eventcol refs)
        children = await conn.fetch("""
            SELECT DISTINCT c.id, c.name, c.type, c.start_year, c.start_seconds, c.end_year, c.end_seconds
            FROM history_event_collections c
            LEFT JOIN collection_subcollections cs
                ON cs.world_id = c.world_id AND cs.child_id = c.id
            WHERE c.world_id = $1
              AND (c.parent_id = $2 OR (cs.parent_id = $2 AND cs.world_id = $1))
            ORDER BY c.start_year, c.id
        """, world_id, collection_id)

        # Events in this collection
        event_count = await conn.fetchval("""
            SELECT count(*) FROM collection_events
            WHERE world_id = $1 AND collection_id = $2
        """, world_id, collection_id)

        events = await conn.fetch("""
            SELECT e.id, e.year, e.seconds, e.event_type, e.details,
                   e.hf_id_1, e.hf_id_2, e.site_id, e.region_id,
                   e.entity_id_1, e.entity_id_2, e.artifact_id, e.structure_id
            FROM history_events e
            JOIN collection_events ce ON ce.world_id = e.world_id AND ce.event_id = e.id
            WHERE ce.world_id = $1 AND ce.collection_id = $2
            ORDER BY e.year, e.seconds
            LIMIT 50
        """, world_id, collection_id)

        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered_events = []
        for ev in events:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'event_collection', collection_id, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        # ── Resolve HF/entity names from collection details ──
        details = collection.get('details') or {}
        coll_type = collection.get('type', '')

        # Collect HF IDs to resolve from details
        detail_hf_refs = set()
        detail_entity_refs = set()
        detail_site_refs = set()

        # Battle/duel combatants
        for key in ('attacking_hfid', 'defending_hfid', 'noncom_hfid'):
            val = details.get(key)
            if val is not None:
                ids = val if isinstance(val, list) else [val]
                for hf_id in ids:
                    if isinstance(hf_id, int):
                        detail_hf_refs.add(hf_id)

        # Mercenary entities
        for key in ('attacking_merc_enid', 'defending_merc_enid'):
            val = details.get(key)
            if val is not None:
                ids = val if isinstance(val, list) else [val]
                for eid in ids:
                    if isinstance(eid, int):
                        detail_entity_refs.add(eid)

        # Occasion civ
        civ_id = details.get('civ_id')
        if isinstance(civ_id, int):
            detail_entity_refs.add(civ_id)

        # Persecution/overthrow target entity
        target_ent = details.get('target_entity_id')
        if isinstance(target_ent, int):
            detail_entity_refs.add(target_ent)

        # Squad sites
        for key in ('attacking_squad_site', 'defending_squad_site'):
            val = details.get(key)
            if val is not None:
                ids = val if isinstance(val, list) else [val]
                for sid in ids:
                    if isinstance(sid, int):
                        detail_site_refs.add(sid)

        # Batch resolve all references
        all_refs = set()
        for hf_id in detail_hf_refs:
            all_refs.add(('hf', hf_id))
        for eid in detail_entity_refs:
            all_refs.add(('entity', eid))
        for sid in detail_site_refs:
            all_refs.add(('site', sid))
        detail_names = await _name_cache.batch_resolve(conn, world_id, list(all_refs))

        # Build resolved combatant lists
        attacking_hfs = []
        for hf_id in (details.get('attacking_hfid') if isinstance(details.get('attacking_hfid'), list) else [details.get('attacking_hfid')] if details.get('attacking_hfid') else []):
            if isinstance(hf_id, int):
                attacking_hfs.append({'id': hf_id, 'name': detail_names.get(('hf', hf_id), f'HF #{hf_id}')})
        defending_hfs = []
        for hf_id in (details.get('defending_hfid') if isinstance(details.get('defending_hfid'), list) else [details.get('defending_hfid')] if details.get('defending_hfid') else []):
            if isinstance(hf_id, int):
                defending_hfs.append({'id': hf_id, 'name': detail_names.get(('hf', hf_id), f'HF #{hf_id}')})
        noncom_hfs = []
        for hf_id in (details.get('noncom_hfid') if isinstance(details.get('noncom_hfid'), list) else [details.get('noncom_hfid')] if details.get('noncom_hfid') else []):
            if isinstance(hf_id, int):
                noncom_hfs.append({'id': hf_id, 'name': detail_names.get(('hf', hf_id), f'HF #{hf_id}')})

        # Build squad summary (zip parallel arrays)
        attacking_squads = []
        defending_squads = []
        for prefix, squads_list in [('attacking', attacking_squads), ('defending', defending_squads)]:
            races = details.get(f'{prefix}_squad_race', [])
            numbers = details.get(f'{prefix}_squad_number', [])
            deaths = details.get(f'{prefix}_squad_deaths', [])
            sites = details.get(f'{prefix}_squad_site', [])
            if not isinstance(races, list):
                races = [races]
            if not isinstance(numbers, list):
                numbers = [numbers]
            if not isinstance(deaths, list):
                deaths = [deaths]
            if not isinstance(sites, list):
                sites = [sites]
            for i, race in enumerate(races):
                squad = {
                    'race': str(race).replace('_', ' ').title() if race else '?',
                    'number': numbers[i] if i < len(numbers) else '?',
                    'deaths': deaths[i] if i < len(deaths) else 0,
                }
                if i < len(sites) and isinstance(sites[i], int):
                    squad['site_id'] = sites[i]
                    squad['site_name'] = detail_names.get(('site', sites[i]), f'Site #{sites[i]}')
                squads_list.append(squad)

        # Occasion details — look up festival name and schedules
        # For occasion collections, civ_id/occasion_id are in the collection details.
        # For child collections (performance/ceremony/etc.), derive from first event.
        occasion_civ = None
        occasion_info = None
        occasion_schedules = []
        event_schedule_id = None  # which schedule this sub-collection corresponds to

        occ_id_val = details.get('occasion_id')
        if occ_id_val is not None and not isinstance(occ_id_val, int):
            try:
                occ_id_val = int(occ_id_val)
            except (ValueError, TypeError):
                occ_id_val = None

        # For child collections without civ_id — derive from first event
        if not civ_id and coll_type in ('performance', 'ceremony', 'procession',
                                         'competition', 'dance_performance'):
            first_cultural_ev = await conn.fetchrow("""
                SELECT e.entity_id_1, e.details
                FROM history_events e
                JOIN collection_events ce ON ce.world_id = e.world_id AND ce.event_id = e.id
                WHERE ce.world_id = $1 AND ce.collection_id = $2
                LIMIT 1
            """, world_id, collection_id)
            if first_cultural_ev:
                ev_details = first_cultural_ev['details'] or {}
                if isinstance(ev_details, str):
                    import json as _json
                    ev_details = _json.loads(ev_details)
                if first_cultural_ev['entity_id_1']:
                    civ_id = first_cultural_ev['entity_id_1']
                if occ_id_val is None:
                    raw_occ = ev_details.get('occasion_id')
                    if raw_occ is not None:
                        try:
                            occ_id_val = int(raw_occ)
                        except (ValueError, TypeError):
                            pass
                raw_sched = ev_details.get('schedule_id')
                if raw_sched is not None:
                    try:
                        event_schedule_id = int(raw_sched)
                    except (ValueError, TypeError):
                        pass

        if civ_id and isinstance(civ_id, int):
            # Resolve civ name (may not be in detail_names if derived from child event)
            civ_name = detail_names.get(('entity', civ_id))
            if not civ_name:
                extra = await _name_cache.batch_resolve(conn, world_id, [('entity', civ_id)])
                civ_name = extra.get(('entity', civ_id), f'Entity #{civ_id}')
            occasion_civ = {'id': civ_id, 'name': civ_name}
        if civ_id and occ_id_val is not None:
            occasion_info = await conn.fetchrow("""
                SELECT name, event_id FROM entity_occasions
                WHERE world_id = $1 AND entity_id = $2 AND occasion_id = $3
            """, world_id, civ_id, occ_id_val)
            if occasion_info:
                occasion_info = dict(occasion_info)
            occasion_schedules = await conn.fetch("""
                SELECT schedule_id, type, reference, reference2,
                       item_type, item_subtype, features
                FROM occasion_schedules
                WHERE world_id = $1 AND entity_id = $2 AND occasion_id = $3
                ORDER BY schedule_id
            """, world_id, civ_id, occ_id_val)
            occasion_schedules = [dict(s) for s in occasion_schedules]

            # Resolve schedule-level and feature references → art_forms / written_contents
            _FEAT_TO_FORM = {
                'dance_performance': 'dance',
                'musical_performance': 'musical',
                'poetry_recital': 'poetic',
            }
            _FEAT_TO_WC = {'storytelling', 'images'}

            for sched in occasion_schedules:
                # Resolve schedule-level reference (primary art form / written content)
                sched_type = sched.get('type', '')
                sched_ref = sched.get('reference')
                sched['ref_name'] = None
                sched['ref_link'] = None
                if sched_ref is not None:
                    if sched_type in _FEAT_TO_FORM:
                        form_type = _FEAT_TO_FORM[sched_type]
                        af = await conn.fetchrow(
                            "SELECT id, name FROM art_forms WHERE world_id=$1 AND form_type=$2 AND id=$3",
                            world_id, form_type, sched_ref)
                        if af:
                            sched['ref_name'] = af['name']
                            sched['ref_link'] = f'/explorer/art_form/{af["id"]}?world_id={world_id}&form_type={form_type}'
                    elif sched_type in _FEAT_TO_WC:
                        wc = await conn.fetchrow(
                            "SELECT id, title FROM written_contents WHERE world_id=$1 AND id=$2",
                            world_id, sched_ref)
                        if wc:
                            sched['ref_name'] = wc['title']
                            sched['ref_link'] = f'/explorer/written_content/{wc["id"]}?world_id={world_id}'

                raw_feats = sched.get('features')
                if not raw_feats:
                    sched['resolved_features'] = []
                    continue
                if isinstance(raw_feats, str):
                    import json as _json
                    raw_feats = _json.loads(raw_feats)
                if not isinstance(raw_feats, list):
                    sched['resolved_features'] = []
                    continue

                resolved = []
                for feat in raw_feats:
                    ft = feat.get('type', '')
                    ref = feat.get('reference')
                    entry = {
                        'type': ft.replace('_', ' ').title(),
                        'type_raw': ft,
                        'ref_name': None,
                        'ref_link': None,
                    }

                    if ref is not None:
                        if isinstance(ref, str):
                            try:
                                ref = int(ref)
                            except ValueError:
                                ref = None

                    if ref is not None and ft in _FEAT_TO_FORM:
                        form_type = _FEAT_TO_FORM[ft]
                        af = await conn.fetchrow(
                            "SELECT id, name FROM art_forms WHERE world_id=$1 AND form_type=$2 AND id=$3",
                            world_id, form_type, ref)
                        if af:
                            entry['ref_name'] = af['name']
                            entry['ref_link'] = f'/explorer/art_form/{af["id"]}?world_id={world_id}&form_type={form_type}'
                    elif ref is not None and ft in _FEAT_TO_WC:
                        wc = await conn.fetchrow(
                            "SELECT id, title FROM written_contents WHERE world_id=$1 AND id=$2",
                            world_id, ref)
                        if wc:
                            entry['ref_name'] = wc['title']
                            entry['ref_link'] = f'/explorer/written_content/{wc["id"]}?world_id={world_id}'

                    resolved.append(entry)
                sched['resolved_features'] = resolved

        # Cultural event summaries — derive site/civ/participants from child events
        # for collection types that store detail at the event level, not the collection
        event_site = None
        event_civ = None
        competition_results = []
        if coll_type in ('competition', 'performance', 'ceremony', 'procession', 'occasion'):
            # Get site/civ from first child event if collection itself has none
            if not collection.get('site_id'):
                first_ev = await conn.fetchrow("""
                    SELECT e.site_id, e.entity_id_1
                    FROM history_events e
                    JOIN collection_events ce ON ce.world_id = e.world_id AND ce.event_id = e.id
                    WHERE ce.world_id = $1 AND ce.collection_id = $2
                    AND (e.site_id IS NOT NULL OR e.entity_id_1 IS NOT NULL)
                    LIMIT 1
                """, world_id, collection_id)
                if first_ev:
                    if first_ev['site_id']:
                        s = await conn.fetchrow(
                            "SELECT id, name, type FROM sites WHERE world_id=$1 AND id=$2",
                            world_id, first_ev['site_id'])
                        if s:
                            event_site = dict(s)
                    if first_ev['entity_id_1']:
                        event_civ = {
                            'id': first_ev['entity_id_1'],
                            'name': detail_names.get(('entity', first_ev['entity_id_1']),
                                                     f'Entity #{first_ev["entity_id_1"]}')
                        }

            # Competition results — extract competitor/winner HF names
            if coll_type == 'competition':
                comp_events = await conn.fetch("""
                    SELECT e.id, e.details, e.site_id, e.entity_id_1
                    FROM history_events e
                    JOIN collection_events ce ON ce.world_id = e.world_id AND ce.event_id = e.id
                    WHERE ce.world_id = $1 AND ce.collection_id = $2
                    AND e.event_type = 'competition'
                    ORDER BY e.id
                """, world_id, collection_id)
                # Resolve all HF refs
                def _safe_int(v):
                    """Coerce str/int to int, return None on failure."""
                    if isinstance(v, int):
                        return v
                    if isinstance(v, str):
                        try:
                            return int(v)
                        except ValueError:
                            pass
                    return None

                comp_hf_ids = set()
                for cev in comp_events:
                    d = cev['details'] or {}
                    if isinstance(d, str):
                        import json as _json
                        d = _json.loads(d)
                    for key in ('competitor_hfid', 'winner_hfid'):
                        val = d.get(key)
                        if isinstance(val, list):
                            for v in val:
                                iv = _safe_int(v)
                                if iv is not None:
                                    comp_hf_ids.add(iv)
                        else:
                            iv = _safe_int(val)
                            if iv is not None:
                                comp_hf_ids.add(iv)
                if comp_hf_ids:
                    hf_names = await _name_cache.batch_resolve(
                        conn, world_id, [('hf', hid) for hid in comp_hf_ids])
                    for cev in comp_events:
                        d = cev['details'] or {}
                        if isinstance(d, str):
                            import json as _json
                            d = _json.loads(d)
                        sched_id = _safe_int(d.get('schedule_id'))
                        # Look up schedule type from occasion_schedules
                        sched_type = None
                        occ_id_ev = _safe_int(d.get('occasion_id'))
                        # civ_id from: collection details → event entity_id_1
                        civ_id_ev = civ_id or _safe_int((collection.get('details') or {}).get('civ_id'))
                        if civ_id_ev is None and cev['entity_id_1']:
                            civ_id_ev = cev['entity_id_1']
                        if occ_id_ev is not None and civ_id_ev and sched_id is not None:
                            sched_row = await conn.fetchrow("""
                                SELECT type FROM occasion_schedules
                                WHERE world_id=$1 AND entity_id=$2
                                AND occasion_id=$3 AND schedule_id=$4
                            """, world_id, civ_id_ev, occ_id_ev, sched_id)
                            if sched_row:
                                sched_type = sched_row['type']
                        winner_id = _safe_int(d.get('winner_hfid'))
                        raw_comp = d.get('competitor_hfid', [])
                        if not isinstance(raw_comp, list):
                            raw_comp = [raw_comp]
                        competitor_ids = [_safe_int(c) for c in raw_comp]
                        competitor_ids = [c for c in competitor_ids if c is not None]
                        competition_results.append({
                            'schedule_id': sched_id,
                            'schedule_type': (sched_type or '').replace('_', ' ').title() if sched_type else None,
                            'winner': {'id': winner_id, 'name': hf_names.get(('hf', winner_id), f'HF #{winner_id}')} if winner_id is not None else None,
                            'competitors': [{'id': cid, 'name': hf_names.get(('hf', cid), f'HF #{cid}')} for cid in competitor_ids],
                        })

        # Journey route — build ordered list of stops from hf travel events
        journey_traveler = None
        journey_companion = None
        journey_route = []
        if coll_type == 'journey':
            travel_events = await conn.fetch("""
                SELECT e.id, e.hf_id_1, e.site_id, e.region_id, e.details
                FROM history_events e
                JOIN collection_events ce ON ce.world_id = e.world_id AND ce.event_id = e.id
                WHERE ce.world_id = $1 AND ce.collection_id = $2
                  AND e.event_type = 'hf travel'
                ORDER BY e.id
            """, world_id, collection_id)
            # Collect all referenced IDs for batch name resolution
            route_refs = set()
            for tev in travel_events:
                if tev['hf_id_1'] is not None:
                    route_refs.add(('hf', tev['hf_id_1']))
                if tev['site_id'] is not None:
                    route_refs.add(('site', tev['site_id']))
                if tev['region_id'] is not None:
                    route_refs.add(('region', tev['region_id']))
                # Traveling companion
                d = tev['details'] or {}
                if isinstance(d, str):
                    import json as _json
                    d = _json.loads(d)
                ghf = d.get('group_hfid')
                if ghf is not None:
                    try:
                        route_refs.add(('hf', int(ghf)))
                    except (ValueError, TypeError):
                        pass
            route_names = {}
            if route_refs:
                route_names = await _name_cache.batch_resolve(
                    conn, world_id, list(route_refs))
            # Build route stops
            for tev in travel_events:
                d = tev['details'] or {}
                if isinstance(d, str):
                    import json as _json
                    d = _json.loads(d)
                is_return = d.get('return') is True
                stop = {
                    'event_id': tev['id'],
                    'is_return': is_return,
                    'coords': d.get('coords'),
                    'coords_x': d.get('coords_x'),
                    'coords_y': d.get('coords_y'),
                }
                if tev['site_id'] is not None:
                    stop['location_type'] = 'site'
                    stop['location_id'] = tev['site_id']
                    stop['location_name'] = route_names.get(
                        ('site', tev['site_id']), f"Site #{tev['site_id']}")
                elif tev['region_id'] is not None:
                    stop['location_type'] = 'region'
                    stop['location_id'] = tev['region_id']
                    stop['location_name'] = route_names.get(
                        ('region', tev['region_id']), f"Region #{tev['region_id']}")
                else:
                    stop['location_type'] = 'unknown'
                    stop['location_id'] = None
                    stop['location_name'] = 'Unknown location'
                journey_route.append(stop)
                # Use first traveler HF
                if journey_traveler is None and tev['hf_id_1'] is not None:
                    journey_traveler = {
                        'id': tev['hf_id_1'],
                        'name': route_names.get(
                            ('hf', tev['hf_id_1']), f"HF #{tev['hf_id_1']}")
                    }
                # Extract traveling companion from first event that has one
                if journey_companion is None:
                    ghf = d.get('group_hfid')
                    if ghf is not None:
                        try:
                            ghf_id = int(ghf)
                            journey_companion = {
                                'id': ghf_id,
                                'name': route_names.get(
                                    ('hf', ghf_id), f"HF #{ghf_id}")
                            }
                        except (ValueError, TypeError):
                            pass

        # Target entity (persecution/overthrow)
        target_entity = None
        if target_ent and isinstance(target_ent, int):
            target_entity = {'id': target_ent, 'name': detail_names.get(('entity', target_ent), f'Entity #{target_ent}')}

        # Prev/Next
        prev_col = await conn.fetchrow("""
            SELECT id, name FROM history_event_collections WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, collection_id)
        next_col = await conn.fetchrow("""
            SELECT id, name FROM history_event_collections WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, collection_id)

    # Duration display — uses tick-level precision when available
    duration = None
    started = None
    ended = None
    sy = collection.get('start_year')
    ey = collection.get('end_year')
    ss = collection.get('start_seconds')
    es = collection.get('end_seconds')
    if sy is not None:
        started = DFCalendar.format_date(sy, ss)
    if ey is not None:
        ended = DFCalendar.format_date(ey, es)
    if sy is not None and ey is not None:
        duration = DFCalendar.format_duration(sy, ss, ey, es)
    elif sy is not None:
        duration = "ongoing"

    return templates.TemplateResponse("collection_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Event Collection",
        "entity_name": _collection_display_name(collection, occasion_info, coll_type, event_schedule_id, occasion_schedules),
        "entity_alt_name": None,
        "collection": collection,
        "details": details,
        "world": world,
        "world_id": world_id,
        "attacker": dict(attacker) if attacker else None,
        "defender": dict(defender) if defender else None,
        "site": dict(site) if site else None,
        "col_region": dict(col_region) if col_region else None,
        "parent_collection": dict(parent_collection) if parent_collection else None,
        "children": [dict(c) for c in children],
        "duration": duration,
        "started": started,
        "ended": ended,
        "events": rendered_events,
        "event_count": event_count,
        "prev_collection": dict(prev_col) if prev_col else None,
        "next_collection": dict(next_col) if next_col else None,
        "linker": _linker,
        "calendar": DFCalendar,
        # Rich details from JSONB
        "attacking_hfs": attacking_hfs,
        "defending_hfs": defending_hfs,
        "noncom_hfs": noncom_hfs,
        "attacking_squads": attacking_squads,
        "defending_squads": defending_squads,
        "occasion_civ": occasion_civ,
        "occasion_info": occasion_info,
        "occasion_schedules": occasion_schedules,
        "event_schedule_id": event_schedule_id,
        "event_site": event_site,
        "event_civ": event_civ,
        "competition_results": competition_results,
        "target_entity": target_entity,
        "outcome": details.get('outcome'),
        "coords": details.get('coords'),
        "adjective": details.get('adjective'),
        # Journey route
        "journey_traveler": journey_traveler,
        "journey_companion": journey_companion,
        "journey_route": journey_route,
    })


# ═══ STAGE 2.3: SECONDARY ENTITY DETAIL PAGES ═══════════════════════════════


# ─── Underground Region Detail Page ──────────────────────────────────────────

@router.get("/explorer/underground_region/{ur_id}", response_class=HTMLResponse)
async def underground_region_detail_page(ur_id: int, request: Request,
                                          world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        ur = await conn.fetchrow(
            "SELECT * FROM underground_regions WHERE world_id = $1 AND id = $2",
            world_id, ur_id,
        )
        if not ur:
            raise HTTPException(404, f"Underground region #{ur_id} not found")
        ur = dict(ur)

        world = await _get_world_info(conn, world_id)

        # Events referencing this underground region
        event_count = await conn.fetchval("""
            SELECT count(*) FROM event_entity_xref
            WHERE world_id = $1 AND entity_type = 'underground_region' AND entity_id = $2
        """, world_id, ur_id)

        events = await conn.fetch("""
            SELECT e.id, e.year, e.seconds, e.event_type, e.details,
                   e.hf_id_1, e.hf_id_2, e.site_id, e.region_id,
                   e.entity_id_1, e.entity_id_2, e.artifact_id, e.structure_id
            FROM history_events e
            JOIN event_entity_xref x ON x.world_id = e.world_id AND x.event_id = e.id
            WHERE x.world_id = $1 AND x.entity_type = 'underground_region' AND x.entity_id = $2
            ORDER BY e.year, e.seconds
            LIMIT 50
        """, world_id, ur_id)

        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered_events = []
        for ev in events:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'underground_region', ur_id, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        # Prev/Next
        prev_ur = await conn.fetchrow("""
            SELECT id, type, depth FROM underground_regions
            WHERE world_id = $1 AND id < $2 ORDER BY id DESC LIMIT 1
        """, world_id, ur_id)
        next_ur = await conn.fetchrow("""
            SELECT id, type, depth FROM underground_regions
            WHERE world_id = $1 AND id > $2 ORDER BY id ASC LIMIT 1
        """, world_id, ur_id)

    # Display name: "Cavern Layer 1" or "Magma Sea" etc.
    ur_type = (ur.get('type') or 'unknown').replace('_', ' ').title()
    depth = ur.get('depth')
    display_name = f"{ur_type} (Depth {depth})" if depth is not None else ur_type

    def _ur_display(row):
        if not row:
            return None
        d = dict(row)
        t = (d.get('type') or 'unknown').replace('_', ' ').title()
        dp = d.get('depth')
        d['display_name'] = f"{t} (Depth {dp})" if dp is not None else t
        return d

    return templates.TemplateResponse("underground_region_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Underground Region",
        "entity_name": display_name,
        "entity_alt_name": None,
        "ur": ur,
        "world": world,
        "world_id": world_id,
        "events": rendered_events,
        "event_count": event_count,
        "prev_ur": _ur_display(prev_ur),
        "next_ur": _ur_display(next_ur),
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Landmass Detail Page ───────────────────────────────────────────────────

@router.get("/explorer/landmass/{landmass_id}", response_class=HTMLResponse)
async def landmass_detail_page(landmass_id: int, request: Request,
                                world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        landmass = await conn.fetchrow(
            "SELECT * FROM landmasses WHERE world_id = $1 AND id = $2",
            world_id, landmass_id,
        )
        if not landmass:
            raise HTTPException(404, f"Landmass #{landmass_id} not found")
        landmass = dict(landmass)

        world = await _get_world_info(conn, world_id)

        # Prev/Next
        prev_lm = await conn.fetchrow("""
            SELECT id, name FROM landmasses
            WHERE world_id = $1 AND id < $2 ORDER BY id DESC LIMIT 1
        """, world_id, landmass_id)
        next_lm = await conn.fetchrow("""
            SELECT id, name FROM landmasses
            WHERE world_id = $1 AND id > $2 ORDER BY id ASC LIMIT 1
        """, world_id, landmass_id)

    return templates.TemplateResponse("landmass_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Landmass",
        "entity_name": landmass['name'] or f"Landmass #{landmass_id}",
        "entity_alt_name": None,
        "landmass": landmass,
        "world": world,
        "world_id": world_id,
        "prev_landmass": dict(prev_lm) if prev_lm else None,
        "next_landmass": dict(next_lm) if next_lm else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Mountain Peak Detail Page ──────────────────────────────────────────────

@router.get("/explorer/mountain_peak/{peak_id}", response_class=HTMLResponse)
async def mountain_peak_detail_page(peak_id: int, request: Request,
                                     world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        peak = await conn.fetchrow(
            "SELECT * FROM mountain_peaks WHERE world_id = $1 AND id = $2",
            world_id, peak_id,
        )
        if not peak:
            raise HTTPException(404, f"Mountain peak #{peak_id} not found")
        peak = dict(peak)

        world = await _get_world_info(conn, world_id)

        # Events
        event_count = await conn.fetchval("""
            SELECT count(*) FROM event_entity_xref
            WHERE world_id = $1 AND entity_type = 'mountain_peak' AND entity_id = $2
        """, world_id, peak_id)

        events = await conn.fetch("""
            SELECT e.id, e.year, e.seconds, e.event_type, e.details,
                   e.hf_id_1, e.hf_id_2, e.site_id, e.region_id,
                   e.entity_id_1, e.entity_id_2, e.artifact_id, e.structure_id
            FROM history_events e
            JOIN event_entity_xref x ON x.world_id = e.world_id AND x.event_id = e.id
            WHERE x.world_id = $1 AND x.entity_type = 'mountain_peak' AND x.entity_id = $2
            ORDER BY e.year, e.seconds
            LIMIT 50
        """, world_id, peak_id)

        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered_events = []
        for ev in events:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'mountain_peak', peak_id, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        # Prev/Next
        prev_pk = await conn.fetchrow("""
            SELECT id, name FROM mountain_peaks
            WHERE world_id = $1 AND id < $2 ORDER BY id DESC LIMIT 1
        """, world_id, peak_id)
        next_pk = await conn.fetchrow("""
            SELECT id, name FROM mountain_peaks
            WHERE world_id = $1 AND id > $2 ORDER BY id ASC LIMIT 1
        """, world_id, peak_id)

    return templates.TemplateResponse("mountain_peak_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Mountain Peak",
        "entity_name": peak['name'] or f"Peak #{peak_id}",
        "entity_alt_name": None,
        "peak": peak,
        "world": world,
        "world_id": world_id,
        "events": rendered_events,
        "event_count": event_count,
        "prev_peak": dict(prev_pk) if prev_pk else None,
        "next_peak": dict(next_pk) if next_pk else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── River Detail Page ──────────────────────────────────────────────────────

@router.get("/explorer/river/{river_id}", response_class=HTMLResponse)
async def river_detail_page(river_id: int, request: Request,
                             world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        river = await conn.fetchrow(
            "SELECT * FROM rivers WHERE world_id = $1 AND id = $2",
            world_id, river_id,
        )
        if not river:
            raise HTTPException(404, f"River #{river_id} not found")
        river = dict(river)

        world = await _get_world_info(conn, world_id)

        # Prev/Next
        prev_riv = await conn.fetchrow("""
            SELECT id, name FROM rivers
            WHERE world_id = $1 AND id < $2 ORDER BY id DESC LIMIT 1
        """, world_id, river_id)
        next_riv = await conn.fetchrow("""
            SELECT id, name FROM rivers
            WHERE world_id = $1 AND id > $2 ORDER BY id ASC LIMIT 1
        """, world_id, river_id)

    return templates.TemplateResponse("river_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "River",
        "entity_name": river['name'] or f"River #{river_id}",
        "entity_alt_name": river.get('name_english'),
        "river": river,
        "world": world,
        "world_id": world_id,
        "prev_river": dict(prev_riv) if prev_riv else None,
        "next_river": dict(next_riv) if next_riv else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── World Construction Detail Page ─────────────────────────────────────────

@router.get("/explorer/construction/{construction_id}", response_class=HTMLResponse)
async def construction_detail_page(construction_id: int, request: Request,
                                    world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        construction = await conn.fetchrow(
            "SELECT * FROM world_constructions WHERE world_id = $1 AND id = $2",
            world_id, construction_id,
        )
        if not construction:
            raise HTTPException(404, f"World construction #{construction_id} not found")
        construction = dict(construction)

        world = await _get_world_info(conn, world_id)

        # Prev/Next
        prev_wc = await conn.fetchrow("""
            SELECT id, name FROM world_constructions
            WHERE world_id = $1 AND id < $2 ORDER BY id DESC LIMIT 1
        """, world_id, construction_id)
        next_wc = await conn.fetchrow("""
            SELECT id, name FROM world_constructions
            WHERE world_id = $1 AND id > $2 ORDER BY id ASC LIMIT 1
        """, world_id, construction_id)

    return templates.TemplateResponse("construction_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "World Construction",
        "entity_name": construction['name'] or f"Construction #{construction_id}",
        "entity_alt_name": None,
        "construction": construction,
        "world": world,
        "world_id": world_id,
        "prev_construction": dict(prev_wc) if prev_wc else None,
        "next_construction": dict(next_wc) if next_wc else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Art Form Detail Page ───────────────────────────────────────────────────

@router.get("/explorer/art_form/{art_form_id}", response_class=HTMLResponse)
async def art_form_detail_page(art_form_id: int, request: Request,
                                world_id: int = Query(None),
                                form_type: str = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        if form_type:
            art_form = await conn.fetchrow(
                "SELECT * FROM art_forms WHERE world_id = $1 AND id = $2 AND form_type = $3",
                world_id, art_form_id, form_type,
            )
        else:
            art_form = await conn.fetchrow(
                "SELECT * FROM art_forms WHERE world_id = $1 AND id = $2 ORDER BY form_type LIMIT 1",
                world_id, art_form_id,
            )
        if not art_form:
            raise HTTPException(404, f"Art form #{art_form_id} not found")
        art_form = dict(art_form)
        ft = art_form['form_type']

        world = await _get_world_info(conn, world_id)

        # Parse details JSONB for form-specific info
        import json as _json
        details = art_form.get('details')
        if isinstance(details, str):
            try:
                details = _json.loads(details)
            except (ValueError, TypeError):
                details = {}
        elif details is None:
            details = {}

        # Prev/Next within the same form_type
        prev_af = await conn.fetchrow("""
            SELECT id, name, form_type FROM art_forms
            WHERE world_id = $1 AND form_type = $2 AND id < $3 ORDER BY id DESC LIMIT 1
        """, world_id, ft, art_form_id)
        next_af = await conn.fetchrow("""
            SELECT id, name, form_type FROM art_forms
            WHERE world_id = $1 AND form_type = $2 AND id > $3 ORDER BY id ASC LIMIT 1
        """, world_id, ft, art_form_id)

    return templates.TemplateResponse("art_form_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Art Form",
        "entity_name": art_form['name'] or f"Art Form #{art_form_id}",
        "entity_alt_name": None,
        "art_form": art_form,
        "details": details,
        "world": world,
        "world_id": world_id,
        "prev_art_form": dict(prev_af) if prev_af else None,
        "next_art_form": dict(next_af) if next_af else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Identity Detail Page ───────────────────────────────────────────────────

@router.get("/explorer/identity/{identity_id}", response_class=HTMLResponse)
async def identity_detail_page(identity_id: int, request: Request,
                                world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        identity = await conn.fetchrow(
            "SELECT * FROM identities WHERE world_id = $1 AND id = $2",
            world_id, identity_id,
        )
        if not identity:
            raise HTTPException(404, f"Identity #{identity_id} not found")
        identity = dict(identity)

        world = await _get_world_info(conn, world_id)

        # Real person (histfig_id)
        real_hf = None
        if identity.get('histfig_id'):
            real_hf = await conn.fetchrow(
                "SELECT id, name, race FROM historical_figures WHERE world_id = $1 AND id = $2",
                world_id, identity['histfig_id'],
            )

        # Associated entity
        assoc_entity = None
        if identity.get('entity_id'):
            assoc_entity = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, identity['entity_id'],
            )

        # Prev/Next
        prev_id = await conn.fetchrow("""
            SELECT id, name FROM identities
            WHERE world_id = $1 AND id < $2 ORDER BY id DESC LIMIT 1
        """, world_id, identity_id)
        next_id = await conn.fetchrow("""
            SELECT id, name FROM identities
            WHERE world_id = $1 AND id > $2 ORDER BY id ASC LIMIT 1
        """, world_id, identity_id)

    return templates.TemplateResponse("identity_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Identity",
        "entity_name": identity['name'] or f"Identity #{identity_id}",
        "entity_alt_name": None,
        "identity": identity,
        "world": world,
        "world_id": world_id,
        "real_hf": dict(real_hf) if real_hf else None,
        "assoc_entity": dict(assoc_entity) if assoc_entity else None,
        "prev_identity": dict(prev_id) if prev_id else None,
        "next_identity": dict(next_id) if next_id else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Historical Era Detail Page ─────────────────────────────────────────────
# NOTE: historical_eras has NO id column — route uses URL-encoded era name

@router.get("/explorer/era/{era_name:path}", response_class=HTMLResponse)
async def era_detail_page(era_name: str, request: Request,
                           world_id: int = Query(None)):
    from urllib.parse import unquote
    era_name = unquote(era_name)

    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        era = await conn.fetchrow(
            "SELECT * FROM historical_eras WHERE world_id = $1 AND name = $2",
            world_id, era_name,
        )
        if not era:
            raise HTTPException(404, f"Historical era '{era_name}' not found")
        era = dict(era)

        world = await _get_world_info(conn, world_id)

        # Events within this era's time range
        start_year = era.get('start_year', 0)
        # End year: next era's start or world's max year
        next_era_start = await conn.fetchval("""
            SELECT min(start_year) FROM historical_eras
            WHERE world_id = $1 AND start_year > $2
        """, world_id, start_year)
        end_year = next_era_start - 1 if next_era_start else await conn.fetchval(
            "SELECT max(year) FROM history_events WHERE world_id = $1", world_id
        )

        # Event type stats within era
        event_stats = await conn.fetch("""
            SELECT event_type, count(*) as cnt
            FROM history_events
            WHERE world_id = $1 AND year >= $2 AND year <= $3
            GROUP BY event_type ORDER BY cnt DESC
            LIMIT 30
        """, world_id, start_year, end_year or 9999)

        total_events = sum(s['cnt'] for s in event_stats)

        # Sample recent events
        events = await conn.fetch("""
            SELECT id, year, seconds, event_type, details,
                   hf_id_1, hf_id_2, site_id, region_id,
                   entity_id_1, entity_id_2, artifact_id, structure_id
            FROM history_events
            WHERE world_id = $1 AND year >= $2 AND year <= $3
            ORDER BY year, seconds
            LIMIT 50
        """, world_id, start_year, end_year or 9999)

        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered_events = []
        for ev in events:
            rendered_events.append({
                'id': ev['id'],
                'year': ev['year'],
                'type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), 'era', 0, name_map),
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

        # All eras for prev/next
        all_eras = await conn.fetch("""
            SELECT name, start_year FROM historical_eras
            WHERE world_id = $1 ORDER BY start_year
        """, world_id)
        era_list = [dict(e) for e in all_eras]
        current_idx = next((i for i, e in enumerate(era_list) if e['name'] == era_name), -1)
        prev_era = era_list[current_idx - 1] if current_idx > 0 else None
        next_era = era_list[current_idx + 1] if current_idx < len(era_list) - 1 else None

    return templates.TemplateResponse("era_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Historical Era",
        "entity_name": era_name,
        "entity_alt_name": None,
        "era": era,
        "world": world,
        "world_id": world_id,
        "start_year": start_year,
        "end_year": end_year,
        "total_events": total_events,
        "event_stats": [dict(s) for s in event_stats],
        "events": rendered_events,
        "prev_era": prev_era,
        "next_era": next_era,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Years and Events Browser ───────────────────────────────────────────────

@router.get("/explorer/years", response_class=HTMLResponse)
async def years_browser_page(request: Request, world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        world = await _get_world_info(conn, world_id)

        # Year list with event counts
        year_counts = await conn.fetch("""
            SELECT year, count(*) as event_count
            FROM history_events
            WHERE world_id = $1
            GROUP BY year ORDER BY year
        """, world_id)

        # Event type statistics
        event_type_stats = await conn.fetch("""
            SELECT event_type, count(*) as cnt
            FROM history_events
            WHERE world_id = $1
            GROUP BY event_type ORDER BY cnt DESC
        """, world_id)

        total_events = sum(s['cnt'] for s in event_type_stats)

    return templates.TemplateResponse("years_browser.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Chronological Browser",
        "entity_name": "Years & Events",
        "entity_alt_name": None,
        "world": world,
        "world_id": world_id,
        "year_counts": [dict(y) for y in year_counts],
        "event_type_stats": [dict(s) for s in event_type_stats],
        "total_events": total_events,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Global Search API ──────────────────────────────────────────────────────

# (table, name_col, id_col, alt_name_col_or_None)
SEARCH_TABLES = {
    'hf': ('historical_figures', 'name', 'id', None),
    'entity': ('entities', 'name', 'id', None),
    'site': ('sites', 'name', 'id', None),
    'artifact': ('artifacts', 'name', 'id', None),
    'region': ('regions', 'name', 'id', None),
    'structure': ('structures', 'name', 'id', None),
    'written_content': ('written_contents', 'title', 'id', None),
    'event_collection': ('history_event_collections', 'name', 'id', None),
    # underground_regions has no name column — excluded from search
    'landmass': ('landmasses', 'name', 'id', None),
    'mountain_peak': ('mountain_peaks', 'name', 'id', None),
    'river': ('rivers', 'name', 'id', 'name_english'),
    'world_construction': ('world_constructions', 'name', 'id', None),
    'art_form': ('art_forms', 'name', 'id', None),
    'identity': ('identities', 'name', 'id', None),
    'era': ('historical_eras', 'name', 'name', None),  # no id column — use name as identifier
}

ENTITY_TYPE_PRIORITY = {
    'hf': 1, 'entity': 2, 'site': 3, 'artifact': 4,
    'region': 5, 'structure': 6, 'event_collection': 7,
    'written_content': 8, 'era': 9, 'identity': 10,
    'underground_region': 11, 'landmass': 12, 'mountain_peak': 13,
    'river': 14, 'world_construction': 15, 'art_form': 16,
}

ENTITY_TYPE_DISPLAY = {
    'hf': 'Historical Figure', 'entity': 'Civilization',
    'site': 'Site', 'artifact': 'Artifact', 'region': 'Region',
    'structure': 'Structure', 'written_content': 'Written Content',
    'event_collection': 'Event Collection', 'underground_region': 'Underground Region',
    'landmass': 'Landmass', 'mountain_peak': 'Mountain Peak',
    'river': 'River', 'world_construction': 'World Construction',
    'art_form': 'Art Form', 'identity': 'Identity', 'era': 'Historical Era',
}

ENTITY_TYPE_URL = {
    'hf': '/explorer/hf/{id}', 'entity': '/explorer/entity/{id}',
    'site': '/explorer/site/{id}', 'artifact': '/explorer/artifact/{id}',
    'region': '/explorer/region/{id}', 'structure': '/explorer/structure/{id}',
    'written_content': '/explorer/written_content/{id}',
    'event_collection': '/explorer/collection/{id}',
    'underground_region': '/explorer/underground_region/{id}',
    'landmass': '/explorer/landmass/{id}',
    'mountain_peak': '/explorer/mountain_peak/{id}',
    'river': '/explorer/river/{id}',
    'world_construction': '/explorer/construction/{id}',
    'art_form': '/explorer/art_form/{id}',
    'identity': '/explorer/identity/{id}',
    'era': '/explorer/era/{id}',  # {id} will be the era name for eras
}


# KH view mapping: base table -> visible view (for KH-filtered search)
_KH_VIEW_MAP = {
    'historical_figures': 'visible_historical_figures',
    'entities': 'visible_entities',
    'sites': 'visible_sites',
    'regions': 'visible_regions',
    'artifacts': 'visible_artifacts',
}


@router.get("/api/search")
async def global_search(request: Request, term: str = Query(..., min_length=2),
                         world_id: int = Query(None),
                         types: str = Query(None),
                         limit: int = Query(50, ge=1, le=200),
                         kh: bool = Query(False),
                         semantic: bool = Query(False)):
    """Global search across all entity types with accent-insensitive matching.

    When kh=true, results are filtered through the Knowledge Horizon views,
    showing only entities the fortress plausibly knows about.
    When semantic=true, uses hybrid vector+keyword search via pgvector embeddings.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

    # ── Semantic search path ──────────────────────────────────────────
    if semantic:
        return await _semantic_search(pool, world_id, term, limit)

    # ── Text search path (existing) ──────────────────────────────────
    async with pool.acquire() as conn:
        search_types = types.split(',') if types else list(SEARCH_TABLES.keys())
        pattern = f"%{term}%"
        results = []

        for entity_type in search_types:
            if entity_type not in SEARCH_TABLES:
                continue
            table, name_col, id_col, alt_col = SEARCH_TABLES[entity_type]

            # Apply KH view mapping if enabled
            if kh:
                table = _KH_VIEW_MAP.get(table, table)

            order_clause = f"t0.{name_col}"
            if 'historical_figures' in table:
                order_clause = f"t0.kill_count DESC NULLS LAST, t0.{name_col}"

            # Build name match condition including alt_name column
            name_cond = f"unaccent(COALESCE(t0.{name_col}, '')) ILIKE unaccent($2)"
            alt_select = "NULL as alt_name"
            if alt_col:
                name_cond += f" OR unaccent(COALESCE(t0.{alt_col}, '')) ILIKE unaccent($2)"
                alt_select = f"t0.{alt_col} as alt_name"

            # For HFs, also search against linked unit native names
            extra_join = ""
            if entity_type == 'hf':
                extra_join = (
                    "LEFT JOIN units u_gs ON u_gs.hist_fig_id = t0.id "
                    "AND u_gs.world_id = t0.world_id"
                )
                name_cond += " OR unaccent(COALESCE(u_gs.name, '')) ILIKE unaccent($2)"
                alt_select = "u_gs.name as alt_name"

            rows = await conn.fetch(f"""
                SELECT t0.{id_col} as entity_id, t0.{name_col} as name, {alt_select}
                FROM {table} t0
                {extra_join}
                WHERE t0.world_id = $1
                  AND ({name_cond})
                ORDER BY {order_clause}
                LIMIT $3
            """, world_id, pattern, min(limit, 20))

            url_template = ENTITY_TYPE_URL.get(entity_type, '')
            for r in rows:
                eid = r['entity_id']
                results.append({
                    'id': eid,
                    'name': r['name'] or f"#{eid}",
                    'alt_name': r.get('alt_name'),
                    'type': entity_type,
                    'type_display': ENTITY_TYPE_DISPLAY.get(entity_type, entity_type),
                    'url': url_template.format(id=eid) + f"?world_id={world_id}",
                })

        term_lower = term.lower()
        results.sort(key=lambda r: (
            0 if (r['name'] or '').lower() == term_lower else 1,
            ENTITY_TYPE_PRIORITY.get(r['type'], 99),
            (r['name'] or '').lower(),
        ))
        return results[:limit]


# Entity name lookup tables for resolving hybrid search results
_ENTITY_NAME_SQL = {
    'hf': ('historical_figures', 'name', 'id'),
    'entity': ('entities', 'name', 'id'),
    'site': ('sites', 'name', 'id'),
    'artifact': ('artifacts', 'name', 'id'),
    'written_content': ('written_contents', 'title', 'id'),
    'art_form': ('art_forms', 'name', 'id'),
}


async def _semantic_search(pool, world_id, query, limit):
    """Hybrid vector+keyword search, resolving entity names for display."""
    from chronicler.embedding.search import hybrid_search

    try:
        hits = await hybrid_search(pool, world_id, query, limit=limit)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Semantic search failed: %s", e)
        return []

    if not hits:
        return []

    # Batch-resolve entity names by type
    entity_names = {}  # (type, id) → name
    by_type = {}
    for h in hits:
        by_type.setdefault(h['entity_type'], set()).add(h['entity_id'])

    async with pool.acquire() as conn:
        for etype, eids in by_type.items():
            if etype not in _ENTITY_NAME_SQL:
                continue
            table, name_col, id_col = _ENTITY_NAME_SQL[etype]
            rows = await conn.fetch(f"""
                SELECT {id_col} as eid, {name_col} as name
                FROM {table}
                WHERE world_id = $1 AND {id_col} = ANY($2::int[])
            """, world_id, list(eids))
            for r in rows:
                entity_names[(etype, r['eid'])] = r['name']

    # Build results in RRF-ranked order
    seen = set()
    results = []
    for h in hits:
        key = (h['entity_type'], h['entity_id'])
        if key in seen:
            continue
        seen.add(key)
        etype = h['entity_type']
        eid = h['entity_id']
        name = entity_names.get(key) or f"#{eid}"
        url_template = ENTITY_TYPE_URL.get(etype, '')
        if not url_template:
            continue
        results.append({
            'id': eid,
            'name': name,
            'alt_name': None,
            'type': etype,
            'type_display': ENTITY_TYPE_DISPLAY.get(etype, etype),
            'url': url_template.format(id=eid) + f"?world_id={world_id}",
            'snippet': h.get('chunk_text', '')[:120],
            'score': round(h.get('rrf_score', 0), 4),
        })
    return results[:limit]


# ─── Popover API ────────────────────────────────────────────────────────────

@router.get("/api/popover/{entity_type}/{entity_id}")
async def entity_popover(entity_type: str, entity_id: int, request: Request,
                          world_id: int = Query(None),
                          site_id: int = Query(None)):
    """Mini summary for hover popovers."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        if entity_type == 'hf':
            row = await conn.fetchrow("""
                SELECT id, name, race, caste, birth_year, death_year,
                       is_deity, is_vampire, is_necromancer, is_werebeast, is_ghost,
                       is_force, kill_count
                FROM historical_figures WHERE world_id = $1 AND id = $2
            """, world_id, entity_id)
            if not row:
                return {"error": "not found"}
            r = dict(row)
            badges = []
            if r.get('is_deity'): badges.append('deity')
            if r.get('is_force'): badges.append('force')
            if r.get('is_vampire'): badges.append('vampire')
            if r.get('is_necromancer'): badges.append('necromancer')
            if r.get('is_werebeast'): badges.append('werebeast')
            if r.get('is_ghost'): badges.append('ghost')
            death_year = r.get('death_year')
            alive = death_year is None or death_year == -1
            return {
                'type': 'hf', 'id': r['id'], 'name': r['name'],
                'race': r.get('race'), 'caste': r.get('caste'),
                'birth_year': r.get('birth_year'), 'death_year': death_year,
                'alive': alive, 'badges': badges,
                'kill_count': r.get('kill_count', 0),
            }

        elif entity_type == 'site':
            row = await conn.fetchrow("""
                SELECT s.id, s.name, s.type, s.coord_x, s.coord_y,
                       s.owner_entity_id, e.name AS owner_name
                FROM sites s
                LEFT JOIN entities e ON e.world_id = s.world_id AND e.id = s.owner_entity_id
                WHERE s.world_id = $1 AND s.id = $2
            """, world_id, entity_id)
            if not row:
                return {"error": "not found"}
            r = dict(row)
            return {
                'type': 'site', 'id': r['id'], 'name': r['name'],
                'site_type': r.get('type'), 'coord_x': r.get('coord_x'),
                'coord_y': r.get('coord_y'), 'owner': r.get('owner_name'),
            }

        elif entity_type == 'entity':
            row = await conn.fetchrow("""
                SELECT id, name, type, race FROM entities
                WHERE world_id = $1 AND id = $2
            """, world_id, entity_id)
            if not row:
                return {"error": "not found"}
            r = dict(row)
            return {
                'type': 'entity', 'id': r['id'], 'name': r['name'],
                'entity_type': r.get('type'), 'race': r.get('race'),
            }

        elif entity_type == 'artifact':
            row = await conn.fetchrow("""
                SELECT a.id, a.name, a.item_type, a.material,
                       h.name AS holder_name, h.id AS holder_id
                FROM artifacts a
                LEFT JOIN historical_figures h ON h.world_id = a.world_id AND h.id = a.holder_hf_id
                WHERE a.world_id = $1 AND a.id = $2
            """, world_id, entity_id)
            if not row:
                return {"error": "not found"}
            r = dict(row)
            return {
                'type': 'artifact', 'id': r['id'], 'name': r['name'],
                'item_type': r.get('item_type'), 'material': r.get('material'),
                'holder': r.get('holder_name'),
            }

        elif entity_type == 'region':
            row = await conn.fetchrow("""
                SELECT id, name, type, evilness FROM regions
                WHERE world_id = $1 AND id = $2
            """, world_id, entity_id)
            if not row:
                return {"error": "not found"}
            r = dict(row)
            return {
                'type': 'region', 'id': r['id'], 'name': r['name'],
                'biome': r.get('type'), 'evilness': r.get('evilness'),
            }

        elif entity_type == 'structure':
            if site_id:
                row = await conn.fetchrow("""
                    SELECT st.id, st.name, st.type, st.site_id, st.entity_id,
                           st.details, si.name AS site_name,
                           e.name AS entity_name, e.type AS entity_type,
                           hf.name AS deity_name
                    FROM structures st
                    LEFT JOIN sites si ON si.world_id = st.world_id AND si.id = st.site_id
                    LEFT JOIN entities e ON e.world_id = st.world_id AND e.id = st.entity_id
                    LEFT JOIN historical_figures hf ON hf.world_id = st.world_id
                        AND hf.id = (st.details->>'deity_hf_id')::int
                    WHERE st.world_id = $1 AND st.site_id = $2 AND st.id = $3
                """, world_id, site_id, entity_id)
            else:
                row = await conn.fetchrow("""
                    SELECT st.id, st.name, st.type, st.site_id, st.entity_id,
                           st.details, si.name AS site_name,
                           e.name AS entity_name, e.type AS entity_type,
                           hf.name AS deity_name
                    FROM structures st
                    LEFT JOIN sites si ON si.world_id = st.world_id AND si.id = st.site_id
                    LEFT JOIN entities e ON e.world_id = st.world_id AND e.id = st.entity_id
                    LEFT JOIN historical_figures hf ON hf.world_id = st.world_id
                        AND hf.id = (st.details->>'deity_hf_id')::int
                    WHERE st.world_id = $1 AND st.id = $2
                """, world_id, entity_id)
            if not row:
                return {"error": "not found"}
            r = dict(row)
            result = {
                'type': 'structure', 'id': r['id'], 'name': r['name'],
                'structure_type': r.get('type'), 'site': r.get('site_name'),
            }
            if r.get('entity_name'):
                result['affiliation'] = r['entity_name']
                result['affiliation_type'] = r.get('entity_type')
            if r.get('deity_name'):
                result['deity'] = r['deity_name']
            return result

        else:
            if entity_type not in SEARCH_TABLES:
                return {"error": "unknown entity type"}
            table, name_col, id_col, _alt_col = SEARCH_TABLES[entity_type]
            row = await conn.fetchrow(f"""
                SELECT {id_col} as entity_id, {name_col} as name FROM {table}
                WHERE world_id = $1 AND {id_col} = $2
            """, world_id, entity_id)
            if not row:
                return {"error": "not found"}
            return {
                'type': entity_type, 'id': row['entity_id'], 'name': row['name'],
            }


# ─── Years Browser API Routes ───────────────────────────────────────────────
# JSON endpoints for the Years browser's interactive features

@router.get("/api/explorer/years")
async def api_years_list(request: Request, world_id: int = Query(None)):
    """Year list with event counts — powers the year selector."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)
        rows = await conn.fetch("""
            SELECT year, count(*) as event_count
            FROM history_events WHERE world_id = $1
            GROUP BY year ORDER BY year
        """, world_id)
    return [dict(r) for r in rows]


@router.get("/api/explorer/years/{year}")
async def api_year_events(year: int, request: Request,
                           world_id: int = Query(None),
                           page: int = Query(1, ge=1)):
    """Events in a specific year, paginated (1000 per page)."""
    pool = request.app.state.pool
    page_size = 1000
    offset = (page - 1) * page_size
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        total = await conn.fetchval("""
            SELECT count(*) FROM history_events
            WHERE world_id = $1 AND year = $2
        """, world_id, year)

        events = await conn.fetch("""
            SELECT id, year, seconds, event_type, details,
                   hf_id_1, hf_id_2, site_id, region_id,
                   entity_id_1, entity_id_2, artifact_id, structure_id
            FROM history_events
            WHERE world_id = $1 AND year = $2
            ORDER BY seconds, id
            LIMIT $3 OFFSET $4
        """, world_id, year, page_size, offset)

        # Batch resolve names for events
        refs = set()
        for ev in events:
            merged = merge_columns_into_details(dict(ev))
            from chronicler.explorer.perspective import ENTITY_REF_FIELDS
            for field, etype in ENTITY_REF_FIELDS.items():
                val = merged.get(field)
                if val is not None:
                    refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)
        rendered = []
        for ev in events:
            rendered.append({
                'id': ev['id'],
                'year': ev['year'],
                'seconds': ev['seconds'],
                'event_type': ev['event_type'],
                'date_short': DFCalendar.format_short(ev['year'], ev['seconds']),
                'text': renderer.render_event(dict(ev), None, None, name_map),
                'details': dict(ev['details']) if ev['details'] else {},
                'enrichment': extract_enrichment_details(dict(ev), _linker, world_id, name_map),
            })

    return {
        "year": year,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "events": rendered,
    }


@router.get("/api/explorer/event_types")
async def api_event_type_stats(request: Request, world_id: int = Query(None)):
    """Event type statistics — counts per type."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)
        rows = await conn.fetch("""
            SELECT event_type, count(*) as cnt
            FROM history_events WHERE world_id = $1
            GROUP BY event_type ORDER BY cnt DESC
        """, world_id)
    return [dict(r) for r in rows]


@router.get("/api/explorer/event/{event_id}")
async def api_event_detail(event_id: int, request: Request,
                            world_id: int = Query(None)):
    """Single event detail with all JSONB fields rendered."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)
        ev = await conn.fetchrow("""
            SELECT id, year, seconds, event_type, details,
                   hf_id_1, hf_id_2, site_id, region_id,
                   entity_id_1, entity_id_2, artifact_id, structure_id
            FROM history_events WHERE world_id = $1 AND id = $2
        """, world_id, event_id)
        if not ev:
            raise HTTPException(404, f"Event #{event_id} not found")

        # Resolve names
        merged = merge_columns_into_details(dict(ev))
        refs = set()
        from chronicler.explorer.perspective import ENTITY_REF_FIELDS
        for field, etype in ENTITY_REF_FIELDS.items():
            val = merged.get(field)
            if val is not None:
                refs.add((etype, int(val)))
        name_map = await _name_cache.batch_resolve(conn, world_id, list(refs))

        renderer = PerspectiveRenderer(_linker, world_id)

    return {
        "id": ev['id'],
        "year": ev['year'],
        "seconds": ev['seconds'],
        "event_type": ev['event_type'],
        "date": DFCalendar.format_date(ev['year'], ev['seconds']),
        "date_short": DFCalendar.format_short(ev['year'], ev['seconds']),
        "text": renderer.render_event(dict(ev), None, None, name_map),
        "details": dict(ev['details']) if ev['details'] else {},
        "enrichment": extract_enrichment_details(dict(ev), _linker, world_id, name_map),
    }


# ── Knowledge Horizon Check API ────────────────────────────────────────


@router.get("/api/kh/check/{entity_type}/{entity_id}")
async def kh_check(entity_type: str, entity_id: int, request: Request,
                   world_id: int = Query(1)):
    """Check if an entity is visible within the Knowledge Horizon.

    Returns {"visible": true/false, "reason": "..."}.
    Used by the detail page fog-of-war banner.
    """
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT visible, reason
            FROM knowledge_horizon
            WHERE world_id = $1 AND entity_type = $2 AND entity_id = $3
            """,
            world_id, entity_type, entity_id,
        )
        if row:
            return {"visible": row["visible"], "reason": row["reason"]}
        # If not in KH table at all, default to not visible
        return {"visible": False, "reason": "Unknown to the fortress"}
