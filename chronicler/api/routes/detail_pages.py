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
from chronicler.explorer.perspective import PerspectiveRenderer, merge_columns_into_details

router = APIRouter()

_template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=_template_dir)

# Register custom Jinja2 test: 'containing' — substring match for selectattr
templates.env.tests['containing'] = lambda value, substring: substring in (value or '')

# Shared instances
_linker = EntityLinkRenderer()
_name_cache = EntityNameCache()

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
                         partial: str = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

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
            ORDER BY l.start_year
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
            SELECT DISTINCT c.id, c.name, c.type, c.start_year, c.end_year
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
        "graph_data_pedigree": graph_data_pedigree,
        "graph_data_career": graph_data_career,
        "graph_data_full": graph_data_full,
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
                             world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        entity = await conn.fetchrow(
            "SELECT * FROM entities WHERE world_id = $1 AND id = $2",
            world_id, entity_id,
        )
        if not entity:
            raise HTTPException(404, f"Entity #{entity_id} not found")
        entity = dict(entity)

        world = await _get_world_info(conn, world_id)

        # Leaders — position holders (join entity_positions for name)
        leaders = await conn.fetch("""
            SELECT p.hf_id, p.position_id, p.start_year, p.end_year,
                   h.name AS hf_name, h.race AS hf_race,
                   ep.name AS position_name
            FROM hf_position_links p
            JOIN historical_figures h ON h.world_id = p.world_id AND h.id = p.hf_id
            LEFT JOIN entity_positions ep ON ep.world_id = p.world_id
                  AND ep.entity_id = p.entity_id AND ep.position_id = p.position_id
            WHERE p.world_id = $1 AND p.entity_id = $2
            ORDER BY p.start_year DESC
        """, world_id, entity_id)

        # Owned sites — include child entity ownership + ownership history
        # 1) Get child entity IDs from JSONB entity_links
        child_ids = []
        elinks = (entity.get('details') or {}).get('entity_links', [])
        for link in elinks:
            if link.get('type') == 'CHILD':
                child_ids.append(link['target'])

        # 2) Sites directly owned or owned by child entities
        owner_ids = [entity_id] + child_ids
        sites_direct = await conn.fetch("""
            SELECT DISTINCT s.id, s.name, s.type, s.coord_x, s.coord_y,
                   'current' AS ownership
            FROM sites s
            WHERE s.world_id = $1 AND s.owner_entity_id = ANY($2)
            ORDER BY s.name
        """, world_id, owner_ids)

        # 3) Sites from ownership history (founded/historically owned)
        sites_history = await conn.fetch("""
            SELECT DISTINCT s.id, s.name, s.type, s.coord_x, s.coord_y,
                   'historical' AS ownership
            FROM sites s,
                 jsonb_array_elements(s.details->'ownership_history') elem
            WHERE s.world_id = $1
              AND (elem->>'entity_id')::int = $2
              AND s.id NOT IN (
                  SELECT id FROM sites WHERE world_id = $1 AND owner_entity_id = ANY($3)
              )
            ORDER BY s.name
        """, world_id, entity_id, owner_ids)

        sites = [dict(s) for s in sites_direct] + [dict(s) for s in sites_history]

        # Notable members by importance
        members = await conn.fetch("""
            SELECT l.hf_id, l.link_type, l.position_name,
                   h.name AS hf_name, h.race AS hf_race, h.prominence_score,
                   h.is_deity, h.is_vampire, h.is_necromancer
            FROM hf_entity_links l
            JOIN historical_figures h ON h.world_id = l.world_id AND h.id = l.hf_id
            WHERE l.world_id = $1 AND l.entity_id = $2
            ORDER BY h.prominence_score DESC NULLS LAST
            LIMIT 100
        """, world_id, entity_id)

        member_count = await conn.fetchval("""
            SELECT count(*) FROM hf_entity_links
            WHERE world_id = $1 AND entity_id = $2
        """, world_id, entity_id)

        # Wars
        wars = await conn.fetch("""
            SELECT DISTINCT c.id, c.name, c.type, c.start_year, c.end_year
            FROM history_event_collections c
            JOIN collection_events ce ON ce.world_id = c.world_id AND ce.collection_id = c.id
            JOIN event_entity_xref x ON x.world_id = ce.world_id AND x.event_id = ce.event_id
            WHERE x.world_id = $1 AND x.entity_type = 'entity' AND x.entity_id = $2
              AND c.type = 'war'
            ORDER BY c.start_year
        """, world_id, entity_id)

        # Entity positions
        positions = await conn.fetch("""
            SELECT id, name FROM entity_positions
            WHERE world_id = $1 AND entity_id = $2
            ORDER BY name
        """, world_id, entity_id)

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
    elif 'religion' in etype:
        badge_class = 'badge-religion'
    else:
        badge_class = 'badge-type'

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
        "leaders": [dict(l) for l in leaders],
        "sites": [dict(s) for s in sites],
        "members": [dict(m) for m in members],
        "member_count": member_count,
        "wars": [dict(w) for w in wars],
        "positions": [dict(p) for p in positions],
        "prev_entity": dict(prev_ent) if prev_ent else None,
        "next_entity": dict(next_ent) if next_ent else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Site Detail Page ───────────────────────────────────────────────────────

@router.get("/explorer/site/{site_id}", response_class=HTMLResponse)
async def site_detail_page(site_id: int, request: Request,
                           world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        site = await conn.fetchrow(
            "SELECT * FROM sites WHERE world_id = $1 AND id = $2",
            world_id, site_id,
        )
        if not site:
            raise HTTPException(404, f"Site #{site_id} not found")
        site = dict(site)

        world = await _get_world_info(conn, world_id)

        # Structures (join entity for owner info)
        structures = await conn.fetch("""
            SELECT s.id, s.name, s.type, s.entity_id,
                   e.name AS entity_name, e.type AS entity_type
            FROM structures s
            LEFT JOIN entities e ON e.world_id = s.world_id AND e.id = s.entity_id
            WHERE s.world_id = $1 AND s.site_id = $2
            ORDER BY s.type, s.name
        """, world_id, site_id)

        # Owner entity
        owner = None
        if site.get('owner_entity_id'):
            owner = await conn.fetchrow(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = $2",
                world_id, site['owner_entity_id'],
            )

        # Ownership timeline from JSONB history
        ownership_timeline = []
        oh = (site.get('details') or {}).get('ownership_history', [])
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
            })

        # Residents (HFs linked to this site via hf_site_links)
        residents = await conn.fetch("""
            SELECT l.hf_id, l.link_type,
                   h.name, h.race, h.caste, h.birth_year, h.death_year,
                   h.is_vampire, h.is_necromancer, h.is_werebeast, h.is_ghost,
                   h.is_deity, h.is_force
            FROM hf_site_links l
            JOIN historical_figures h ON h.world_id = l.world_id AND h.id = l.hf_id
            WHERE l.world_id = $1 AND l.site_id = $2
            ORDER BY l.link_type, h.name
            LIMIT 200
        """, world_id, site_id)
        residents = [dict(r) for r in residents]

        # Prev/Next
        prev_site = await conn.fetchrow("""
            SELECT id, name FROM sites WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, site_id)
        next_site = await conn.fetchrow("""
            SELECT id, name FROM sites WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, site_id)

    is_ruin = site.get('details', {}).get('ruin') if site.get('details') else False

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
        "ownership_timeline": ownership_timeline,
        "residents": residents,
        "events": rendered_events,
        "event_count": event_count,
        "prev_site": dict(prev_site) if prev_site else None,
        "next_site": dict(next_site) if next_site else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


# ─── Artifact Detail Page ─────────────────────────────────────────────────

@router.get("/explorer/artifact/{artifact_id}", response_class=HTMLResponse)
async def artifact_detail_page(artifact_id: int, request: Request,
                               world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

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
                             world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

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

        # Deity (from details JSONB — check for deity or worship_hf_id)
        deity = None
        details = structure.get('details') or {}
        deity_hf_id = details.get('deity') or details.get('worship_hf_id') or details.get('deity_hf_id')
        if deity_hf_id:
            deity = await conn.fetchrow(
                "SELECT id, name, race FROM historical_figures WHERE world_id = $1 AND id = $2",
                world_id, int(deity_hf_id),
            )

        # Events at this structure
        event_count = await conn.fetchval("""
            SELECT count(*) FROM event_entity_xref
            WHERE world_id = $1 AND entity_type = 'structure' AND entity_id = $2
        """, world_id, structure_id)

        events = await conn.fetch("""
            SELECT e.id, e.year, e.seconds, e.event_type, e.details,
                   e.hf_id_1, e.hf_id_2, e.site_id, e.region_id,
                   e.entity_id_1, e.entity_id_2, e.artifact_id, e.structure_id
            FROM history_events e
            JOIN event_entity_xref x ON x.world_id = e.world_id AND x.event_id = e.id
            WHERE x.world_id = $1 AND x.entity_type = 'structure' AND x.entity_id = $2
            ORDER BY e.year, e.seconds
            LIMIT 50
        """, world_id, structure_id)

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
            })

    # Structure type badge class
    stype = (structure.get('type') or '').lower()
    STRUCTURE_BADGE_MAP = {
        'temple': 'badge-deity', 'tomb': 'badge-dead', 'mead_hall': 'badge-civ',
        'library': 'badge-type', 'dungeon': 'badge-vampire', 'tower': 'badge-type',
        'keep': 'badge-leader', 'inn': 'badge-site', 'tavern': 'badge-site',
        'market': 'badge-site', 'guildhall': 'badge-civ', 'counting_house': 'badge-type',
    }
    badge_class = STRUCTURE_BADGE_MAP.get(stype, 'badge-type')

    return templates.TemplateResponse("structure_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Structure",
        "entity_name": structure['name'] or f"Structure #{structure_id}",
        "entity_alt_name": None,
        "structure": structure,
        "world": world,
        "world_id": world_id,
        "site_id": site_id,
        "parent_site": dict(parent_site) if parent_site else None,
        "owner_entity": dict(owner_entity) if owner_entity else None,
        "deity": dict(deity) if deity else None,
        "badge_class": badge_class,
        "events": rendered_events,
        "event_count": event_count,
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

        # Referenced entities from details JSONB
        details = wc.get('details') or {}
        referenced_hfs = []
        ref_hf_ids = details.get('referenced_hf_ids') or details.get('hf_ids') or []
        if ref_hf_ids and isinstance(ref_hf_ids, list):
            referenced_hfs = await conn.fetch(
                "SELECT id, name, race FROM historical_figures WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, [int(x) for x in ref_hf_ids],
            )
        referenced_sites = []
        ref_site_ids = details.get('referenced_site_ids') or details.get('site_ids') or []
        if ref_site_ids and isinstance(ref_site_ids, list):
            referenced_sites = await conn.fetch(
                "SELECT id, name, type FROM sites WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, [int(x) for x in ref_site_ids],
            )
        referenced_entities = []
        ref_ent_ids = details.get('referenced_entity_ids') or details.get('entity_ids') or []
        if ref_ent_ids and isinstance(ref_ent_ids, list):
            referenced_entities = await conn.fetch(
                "SELECT id, name, type FROM entities WHERE world_id = $1 AND id = ANY($2::int[])",
                world_id, [int(x) for x in ref_ent_ids],
            )

        # Associated artifact (books)
        associated_artifact = None
        assoc_artifact_id = details.get('artifact_id')
        if assoc_artifact_id:
            associated_artifact = await conn.fetchrow(
                "SELECT id, name, material, item_type FROM artifacts WHERE world_id = $1 AND id = $2",
                world_id, int(assoc_artifact_id),
            )

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
        "associated_artifact": dict(associated_artifact) if associated_artifact else None,
        "prev_wc": dict(prev_wc) if prev_wc else None,
        "next_wc": dict(next_wc) if next_wc else None,
        "linker": _linker,
        "calendar": DFCalendar,
    })


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
                "SELECT id, name, type FROM history_event_collections WHERE world_id = $1 AND id = $2",
                world_id, collection['parent_id'],
            )

        # Child collections (sub-battles, sub-events)
        children = await conn.fetch("""
            SELECT id, name, type, start_year, end_year
            FROM history_event_collections
            WHERE world_id = $1 AND parent_id = $2
            ORDER BY start_year, id
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
            })

        # Prev/Next
        prev_col = await conn.fetchrow("""
            SELECT id, name FROM history_event_collections WHERE world_id = $1 AND id < $2
            ORDER BY id DESC LIMIT 1
        """, world_id, collection_id)
        next_col = await conn.fetchrow("""
            SELECT id, name FROM history_event_collections WHERE world_id = $1 AND id > $2
            ORDER BY id ASC LIMIT 1
        """, world_id, collection_id)

    # Duration display
    duration = None
    if collection.get('start_year') and collection.get('end_year'):
        if collection['end_year'] != collection['start_year']:
            duration = f"Year {collection['start_year']} – Year {collection['end_year']}"
        else:
            duration = f"Year {collection['start_year']}"
    elif collection.get('start_year'):
        duration = f"Year {collection['start_year']} – ongoing"

    return templates.TemplateResponse("collection_detail.html", {
        "request": request,
        "active": "explorer",
        "entity_type_display": "Event Collection",
        "entity_name": collection['name'] or f"Collection #{collection_id}",
        "entity_alt_name": None,
        "collection": collection,
        "world": world,
        "world_id": world_id,
        "attacker": dict(attacker) if attacker else None,
        "defender": dict(defender) if defender else None,
        "site": dict(site) if site else None,
        "col_region": dict(col_region) if col_region else None,
        "parent_collection": dict(parent_collection) if parent_collection else None,
        "children": [dict(c) for c in children],
        "duration": duration,
        "events": rendered_events,
        "event_count": event_count,
        "prev_collection": dict(prev_col) if prev_col else None,
        "next_collection": dict(next_col) if next_col else None,
        "linker": _linker,
        "calendar": DFCalendar,
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
                                world_id: int = Query(None)):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        art_form = await conn.fetchrow(
            "SELECT * FROM art_forms WHERE world_id = $1 AND id = $2",
            world_id, art_form_id,
        )
        if not art_form:
            raise HTTPException(404, f"Art form #{art_form_id} not found")
        art_form = dict(art_form)

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

        # Prev/Next
        prev_af = await conn.fetchrow("""
            SELECT id, name FROM art_forms
            WHERE world_id = $1 AND id < $2 ORDER BY id DESC LIMIT 1
        """, world_id, art_form_id)
        next_af = await conn.fetchrow("""
            SELECT id, name FROM art_forms
            WHERE world_id = $1 AND id > $2 ORDER BY id ASC LIMIT 1
        """, world_id, art_form_id)

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

SEARCH_TABLES = {
    'hf': ('historical_figures', 'name', 'id'),
    'entity': ('entities', 'name', 'id'),
    'site': ('sites', 'name', 'id'),
    'artifact': ('artifacts', 'name', 'id'),
    'region': ('regions', 'name', 'id'),
    'structure': ('structures', 'name', 'id'),
    'written_content': ('written_contents', 'title', 'id'),
    'event_collection': ('history_event_collections', 'name', 'id'),
    # underground_regions has no name column — excluded from search
    'landmass': ('landmasses', 'name', 'id'),
    'mountain_peak': ('mountain_peaks', 'name', 'id'),
    'river': ('rivers', 'name', 'id'),
    'world_construction': ('world_constructions', 'name', 'id'),
    'art_form': ('art_forms', 'name', 'id'),
    'identity': ('identities', 'name', 'id'),
    'era': ('historical_eras', 'name', 'name'),  # no id column — use name as identifier
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


@router.get("/api/search")
async def global_search(request: Request, term: str = Query(..., min_length=2),
                         world_id: int = Query(None),
                         types: str = Query(None),
                         limit: int = Query(50, ge=1, le=200)):
    """Global search across all entity types with accent-insensitive matching."""
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        if not world_id:
            world_id = await _get_default_world_id(conn)

        search_types = types.split(',') if types else list(SEARCH_TABLES.keys())
        pattern = f"%{term}%"
        results = []

        for entity_type in search_types:
            if entity_type not in SEARCH_TABLES:
                continue
            table, name_col, id_col = SEARCH_TABLES[entity_type]

            order_clause = "name"
            if table == 'historical_figures':
                order_clause = "kill_count DESC NULLS LAST, name"

            rows = await conn.fetch(f"""
                SELECT {id_col} as entity_id, {name_col} as name
                FROM {table}
                WHERE world_id = $1
                  AND unaccent(COALESCE({name_col}, '')) ILIKE unaccent($2)
                ORDER BY {order_clause}
                LIMIT $3
            """, world_id, pattern, min(limit, 20))

            url_template = ENTITY_TYPE_URL.get(entity_type, '')
            for r in rows:
                eid = r['entity_id']
                results.append({
                    'id': eid,
                    'name': r['name'] or f"#{eid}",
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


# ─── Popover API ────────────────────────────────────────────────────────────

@router.get("/api/popover/{entity_type}/{entity_id}")
async def entity_popover(entity_type: str, entity_id: int, request: Request,
                          world_id: int = Query(None)):
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
            row = await conn.fetchrow("""
                SELECT st.id, st.name, st.type, st.site_id,
                       si.name AS site_name
                FROM structures st
                LEFT JOIN sites si ON si.world_id = st.world_id AND si.id = st.site_id
                WHERE st.world_id = $1 AND st.id = $2
            """, world_id, entity_id)
            if not row:
                return {"error": "not found"}
            r = dict(row)
            return {
                'type': 'structure', 'id': r['id'], 'name': r['name'],
                'structure_type': r.get('type'), 'site': r.get('site_name'),
            }

        else:
            if entity_type not in SEARCH_TABLES:
                return {"error": "unknown entity type"}
            table, name_col, id_col = SEARCH_TABLES[entity_type]
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
    }
