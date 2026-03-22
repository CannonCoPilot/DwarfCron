"""Cross-linking infrastructure — entity link rendering and name resolution.

Provides EntityLinkRenderer for generating HTML <a> tags for entity references,
and EntityNameCache for batch-loading entity names from the database with caching.
"""

import time
from html import escape


class EntityLinkRenderer:
    """Converts entity type + ID references into navigable HTML links."""

    # Entity type -> URL path template
    ROUTES = {
        'hf': '/explorer/hf/{id}',
        'entity': '/explorer/entity/{id}',
        'site': '/explorer/site/{id}',
        'artifact': '/explorer/artifact/{id}',
        'region': '/explorer/region/{id}',
        'structure': '/explorer/site/{site_id}/structure/{id}',
        'written_content': '/explorer/written_content/{id}',
        'event_collection': '/explorer/collection/{id}',
        'world_construction': '/explorer/construction/{id}',
        'art_form': '/explorer/art_form/{id}',
        'identity': '/explorer/identity/{id}',
        'landmass': '/explorer/landmass/{id}',
        'mountain_peak': '/explorer/mountain_peak/{id}',
        'river': '/explorer/river/{id}',
        'underground_region': '/explorer/underground_region/{id}',
        'era': '/explorer/era/{id}',
    }

    # Display labels for entity types
    TYPE_LABELS = {
        'hf': 'Historical Figure',
        'entity': 'Civilization',
        'site': 'Site',
        'artifact': 'Artifact',
        'region': 'Region',
        'structure': 'Structure',
        'written_content': 'Written Content',
        'event_collection': 'Event Collection',
        'world_construction': 'Construction',
        'art_form': 'Art Form',
        'identity': 'Identity',
        'landmass': 'Landmass',
        'mountain_peak': 'Mountain Peak',
        'river': 'River',
        'underground_region': 'Underground Region',
        'era': 'Era',
    }

    def link(self, entity_type: str, entity_id, display_name: str = None,
             world_id: int = None, css_class: str = '',
             site_id: int = None) -> str:
        """Generate HTML link for an entity reference.

        Args:
            entity_type: One of the keys in ROUTES (e.g., 'hf', 'site')
            entity_id: The entity's ID
            display_name: Text to show (falls back to "Unknown {type} #{id}")
            world_id: World ID for query parameter
            css_class: Additional CSS classes
            site_id: Required for structure links (parent site)

        Returns:
            HTML <a> tag string, or plain text if entity_type is unknown.
        """
        if entity_id is None:
            return escape(display_name or '?')

        name = escape(display_name or f"Unknown {self.TYPE_LABELS.get(entity_type, entity_type)} #{entity_id}")

        route = self.ROUTES.get(entity_type)
        if not route:
            return name

        url = route.format(id=entity_id, site_id=site_id or 0)
        if world_id is not None:
            url = f"{url}?world_id={world_id}"

        classes = f"entity-link entity-{entity_type}"
        if css_class:
            classes += f" {css_class}"

        # Extra data attributes for composite-key entities
        extra_attrs = ''
        if entity_type == 'structure' and site_id:
            extra_attrs = f' data-site-id="{site_id}"'
        if world_id is not None:
            extra_attrs += f' data-world-id="{world_id}"'

        return (
            f'<a href="{url}" class="{classes}" '
            f'data-entity-type="{entity_type}" '
            f'data-entity-id="{entity_id}"{extra_attrs}>'
            f'{name}</a>'
        )

    def url_for(self, entity_type: str, entity_id: int,
                world_id: int = None, site_id: int = None) -> str:
        """Generate just the URL (no HTML) for an entity."""
        route = self.ROUTES.get(entity_type)
        if not route:
            return '#'
        url = route.format(id=entity_id, site_id=site_id or 0)
        if world_id is not None:
            url = f"{url}?world_id={world_id}"
        return url


class EntityNameCache:
    """Lazily cached entity name resolution with batch loading.

    Names are loaded per (entity_type, entity_id) on demand, using batch
    queries grouped by entity type for efficiency. Results are cached with
    a per-world TTL.
    """

    # entity_type -> (table_name, name_column)
    TABLE_MAP = {
        'hf': ('historical_figures', 'name'),
        'entity': ('entities', 'name'),
        'site': ('sites', 'name'),
        'artifact': ('artifacts', 'name'),
        'region': ('regions', 'name'),
        'structure': ('structures', 'name'),
        'written_content': ('written_contents', 'title'),
        'event_collection': ('history_event_collections', 'name'),
        'world_construction': ('world_constructions', 'name'),
        'art_form': ('art_forms', 'name'),
        'identity': ('identities', 'name'),
        'landmass': ('landmasses', 'name'),
        'mountain_peak': ('mountain_peaks', 'name'),
        'river': ('rivers', 'name'),
        'underground_region': ('underground_regions', 'type'),
        'era': ('historical_eras', 'name'),
    }

    TTL = 300  # 5-minute cache TTL

    def __init__(self):
        # world_id -> {(entity_type, entity_id): name}
        self._cache: dict[int, dict[tuple[str, int], str]] = {}
        self._loaded_at: dict[int, float] = {}

    def _get_world_cache(self, world_id: int) -> dict:
        """Get or create the cache dict for a world, respecting TTL."""
        now = time.monotonic()
        if world_id in self._loaded_at:
            if now - self._loaded_at[world_id] > self.TTL:
                # TTL expired — clear this world's cache
                self._cache.pop(world_id, None)
                self._loaded_at.pop(world_id, None)

        if world_id not in self._cache:
            self._cache[world_id] = {}
            self._loaded_at[world_id] = now

        return self._cache[world_id]

    def get_name(self, world_id: int, entity_type: str, entity_id: int) -> str | None:
        """Get a cached name, or None if not yet loaded."""
        cache = self._get_world_cache(world_id)
        return cache.get((entity_type, entity_id))

    def put_name(self, world_id: int, entity_type: str, entity_id: int, name: str):
        """Manually insert a name into the cache."""
        cache = self._get_world_cache(world_id)
        cache[(entity_type, entity_id)] = name

    async def batch_resolve(self, conn, world_id: int,
                            refs: list[tuple[str, int]]) -> dict[tuple[str, int], str]:
        """Batch-load names for a list of (entity_type, entity_id) tuples.

        Only queries the DB for refs not already in cache. Returns a dict
        mapping each ref to its resolved name.
        """
        cache = self._get_world_cache(world_id)
        result = {}
        missing_by_type: dict[str, list[int]] = {}

        for entity_type, entity_id in refs:
            if entity_id is None:
                continue
            key = (entity_type, entity_id)
            if key in cache:
                result[key] = cache[key]
            else:
                missing_by_type.setdefault(entity_type, []).append(entity_id)

        # Batch query per entity type
        for entity_type, ids in missing_by_type.items():
            if entity_type not in self.TABLE_MAP:
                for eid in ids:
                    fallback = f"Unknown {entity_type} #{eid}"
                    cache[(entity_type, eid)] = fallback
                    result[(entity_type, eid)] = fallback
                continue

            table, col = self.TABLE_MAP[entity_type]
            unique_ids = list(set(ids))
            rows = await conn.fetch(
                f'SELECT id, {col} AS name FROM {table} '
                f'WHERE world_id = $1 AND id = ANY($2::int[])',
                world_id, unique_ids,
            )
            found = {r['id']: r['name'] for r in rows}

            for eid in unique_ids:
                name = found.get(eid) or f"Unknown {entity_type} #{eid}"
                cache[(entity_type, eid)] = name
                result[(entity_type, eid)] = name

        return result

    def clear(self, world_id: int = None):
        """Clear cache for a specific world or all worlds."""
        if world_id is not None:
            self._cache.pop(world_id, None)
            self._loaded_at.pop(world_id, None)
        else:
            self._cache.clear()
            self._loaded_at.clear()
