"""Perspective-aware event rendering.

When viewing events on an entity's detail page, the current entity is the
"perspective" entity. Self-references are replaced with relational pronouns,
while all other entity references become clickable links.

The DB stores entity IDs in generic columns (hf_id_1, hf_id_2, site_id,
entity_id_1, entity_id_2, etc.) while templates use DF XML field names
(hfid, snatcher_hfid, civ_id, etc.). COLUMN_MAP_BY_EVENT maps each event
type's DB columns back to the template field names used by EVENT_TEMPLATES.
"""

from html import escape

from chronicler.explorer.linking import EntityLinkRenderer


# Event type -> human-readable description templates
# Fields like {hfid} get replaced with linked entity names or pronouns
EVENT_TEMPLATES = {
    'add hf entity link': '{hfid} joined {civ_id} as {link}',
    'attacked site': '{attacker_civ_id} attacked {site_id} (defended by {defender_civ_id})',
    'body abused': '{hfid} abused the body of {target_hfid} at {site_id}',
    'change hf state': '{hfid} became {state} in {site_id}',
    'change hf job': '{hfid} changed profession in {site_id}',
    'changed creature type': '{hfid} changed from {old_race} to {new_race}',
    'create entity position': '{hfid} created the position {position} in {civ_id}',
    'created site': '{civ_id} founded {site_id}',
    'created world construction': '{civ_id} constructed {wcid} between {site_id1} and {site_id2}',
    'creature devoured': '{hfid} devoured {target_hfid}',
    'destroyed site': '{attacker_civ_id} destroyed {site_id}',
    'field battle': '{attacker_civ_id} fought {defender_civ_id} at {site_id}',
    'hf abducted': '{snatcher_hfid} abducted {target_hfid} from {site_id}',
    'hf attacked site': '{attacker_hfid} attacked {site_id}',
    'hf confronted': '{hfid} confronted {target_hfid}',
    'hf destroyed site': '{attacker_hfid} destroyed {site_id}',
    'hf died': '{hfid} died ({cause}) at {site_id}',
    'hf does interaction': '{doer_hfid} {interaction} on {target_hfid}',
    'hf gains secret knowledge': '{hfid} gained secret knowledge of {secret}',
    'hf learns secret': '{hfid} learned {interaction}',
    'hf new pet': '{hfid} tamed a {pets}',
    'hf reach summit': '{hfid} reached the summit of {mountain_peak_id}',
    'hf relationship denied': '{seeker_hfid} was denied by {target_hfid}',
    'hf reunion': '{group_1_hfid} reunited with {group_2_hfid}',
    'hf revived': '{hfid} was revived by {actor_hfid}',
    'hf simple battle event': '{group_1_hfid} fought {group_2_hfid}',
    'hf travel': '{hfid} traveled to {site_id}',
    'hf wounded': '{hfid} was wounded by {wounder_hfid}',
    'item stolen': '{hfid} stole {item} from {site_id}',
    'masterpiece item': '{hfid} created a masterpiece {item} at {site_id}',
    'peace accepted': '{source} and {destination} agreed to peace',
    'peace rejected': '{source} rejected peace with {destination}',
    'plundered site': '{attacker_civ_id} plundered {site_id}',
    'razed structure': '{attacker_civ_id} razed {structure_id} at {site_id}',
    'reclaim site': '{civ_id} reclaimed {site_id}',
    'remove hf entity link': '{hfid} left {civ_id} ({link})',
    'site taken over': '{attacker_civ_id} took over {site_id} from {defender_civ_id}',
    'war declared': '{source_entity_id} declared war on {target_entity_id}',
    'written content composed': '{hfid} composed a written work at {site_id}',
    'add hf hf link': '{hfid} formed a relationship with {hfid_target}',
    'remove hf hf link': '{hfid} ended a relationship with {hfid_target}',
    'artifact created': '{hfid} created {artifact_id} at {site_id}',
    'add hf site link': '{hfid} became associated with {site_id}',
    'hf recruited unit type for entity': '{hfid} recruited units for {civ_id}',
    'assume identity': '{hfid} assumed an identity',
    'knowledge discovered': '{hfid} discovered knowledge',
    'created structure': '{civ_id} constructed {structure_id} at {site_id}',
    'entity created': '{civ_id} was founded at {site_id}',
    'artifact stored': '{hfid} stored {artifact_id} at {site_id}',
    'artifact recovered': '{hfid} recovered {artifact_id} at {site_id}',
    'artifact given': '{giver_hist_figure_id} gave {artifact_id} to {receiver_hist_figure_id}',
    'hfs formed reputation relationship': '{hfid} formed a reputation with {target_hfid}',
}

# ── DB column → template field mapping per event type ────────────────────────
# During XML ingestion, various field names were normalized into generic DB
# columns: hf_id_1, hf_id_2, site_id, entity_id_1, entity_id_2, etc.
# This map reverses that normalization for template rendering.
#
# Structure: {event_type: {db_column: template_field_name}}
# Uses _DEFAULT_COLUMN_MAP as fallback for event types not listed here.

_DEFAULT_COLUMN_MAP = {
    'hf_id_1': 'hfid',
    'hf_id_2': 'target_hfid',
    'site_id': 'site_id',
    'region_id': 'region_id',
    'entity_id_1': 'civ_id',
    'entity_id_2': 'defender_civ_id',
    'artifact_id': 'artifact_id',
    'structure_id': 'structure_id',
}

COLUMN_MAP_BY_EVENT = {
    'add hf entity link': {
        'hf_id_1': 'hfid', 'entity_id_1': 'civ_id', 'site_id': 'site_id',
    },
    'attacked site': {
        'entity_id_1': 'attacker_civ_id', 'entity_id_2': 'defender_civ_id',
        'site_id': 'site_id',
    },
    'body abused': {
        'hf_id_1': 'hfid', 'hf_id_2': 'target_hfid', 'site_id': 'site_id',
    },
    'change hf state': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'change hf job': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'changed creature type': {
        'hf_id_1': 'hfid',
    },
    'create entity position': {
        'hf_id_1': 'hfid', 'entity_id_1': 'civ_id',
    },
    'created site': {
        'entity_id_1': 'civ_id', 'site_id': 'site_id',
    },
    'creature devoured': {
        'hf_id_1': 'hfid', 'hf_id_2': 'target_hfid',
    },
    'destroyed site': {
        'entity_id_1': 'attacker_civ_id', 'site_id': 'site_id',
    },
    'field battle': {
        'entity_id_1': 'attacker_civ_id', 'entity_id_2': 'defender_civ_id',
        'site_id': 'site_id',
    },
    'hf abducted': {
        'hf_id_1': 'snatcher_hfid', 'hf_id_2': 'target_hfid',
        'site_id': 'site_id',
    },
    'hf attacked site': {
        'hf_id_1': 'attacker_hfid', 'site_id': 'site_id',
    },
    'hf confronted': {
        'hf_id_1': 'hfid', 'hf_id_2': 'target_hfid',
    },
    'hf destroyed site': {
        'hf_id_1': 'attacker_hfid', 'site_id': 'site_id',
    },
    'hf died': {
        'hf_id_1': 'hfid', 'hf_id_2': 'slayer_hfid', 'site_id': 'site_id',
    },
    'hf does interaction': {
        'hf_id_1': 'doer_hfid', 'hf_id_2': 'target_hfid',
    },
    'hf gains secret knowledge': {
        'hf_id_1': 'hfid',
    },
    'hf learns secret': {
        'hf_id_1': 'hfid',
    },
    'hf new pet': {
        'hf_id_1': 'hfid',
    },
    'hf reach summit': {
        'hf_id_1': 'hfid',
    },
    'hf relationship denied': {
        'hf_id_1': 'seeker_hfid', 'hf_id_2': 'target_hfid',
    },
    'hf reunion': {
        'hf_id_1': 'hfid1', 'hf_id_2': 'hfid2',
    },
    'hf revived': {
        'hf_id_1': 'hfid', 'hf_id_2': 'actor_hfid',
    },
    'hf simple battle event': {
        'hf_id_1': 'hfid1', 'hf_id_2': 'hfid2',
    },
    'hf travel': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'region_id': 'region_id',
    },
    'hf wounded': {
        'hf_id_1': 'hfid', 'hf_id_2': 'wounder_hfid',
    },
    'item stolen': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'masterpiece item': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'plundered site': {
        'entity_id_1': 'attacker_civ_id', 'site_id': 'site_id',
    },
    'razed structure': {
        'entity_id_1': 'attacker_civ_id', 'site_id': 'site_id',
        'structure_id': 'structure_id',
    },
    'reclaim site': {
        'entity_id_1': 'civ_id', 'site_id': 'site_id',
    },
    'remove hf entity link': {
        'hf_id_1': 'hfid', 'entity_id_1': 'civ_id',
    },
    'site taken over': {
        'entity_id_1': 'attacker_civ_id', 'entity_id_2': 'defender_civ_id',
        'site_id': 'site_id',
    },
    'war declared': {
        'entity_id_1': 'source_entity_id', 'entity_id_2': 'target_entity_id',
    },
    'written content composed': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'add hf hf link': {
        'hf_id_1': 'hfid', 'hf_id_2': 'target_hfid',
    },
    'remove hf hf link': {
        'hf_id_1': 'hfid', 'hf_id_2': 'target_hfid',
    },
    'artifact created': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'artifact_id': 'artifact_id',
    },
    'add hf site link': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'hf recruited unit type for entity': {
        'hf_id_1': 'hfid', 'entity_id_1': 'civ_id',
    },
    'assume identity': {
        'hf_id_1': 'hfid',
    },
    'knowledge discovered': {
        'hf_id_1': 'hfid',
    },
    'created structure': {
        'entity_id_1': 'civ_id', 'site_id': 'site_id',
        'structure_id': 'structure_id',
    },
    'entity created': {
        'entity_id_1': 'civ_id', 'site_id': 'site_id',
    },
    'artifact stored': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'artifact_id': 'artifact_id',
    },
    'artifact recovered': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'artifact_id': 'artifact_id',
        'structure_id': 'structure_id',
    },
    'artifact given': {
        'artifact_id': 'artifact_id',
    },
    'hfs formed reputation relationship': {
        'hf_id_1': 'hfid', 'hf_id_2': 'target_hfid',
    },
}

# DB columns that hold entity references
ENTITY_COLUMNS = (
    'hf_id_1', 'hf_id_2', 'site_id', 'region_id',
    'entity_id_1', 'entity_id_2', 'artifact_id', 'structure_id',
)

# Fields that refer to entity IDs, mapped to entity types
ENTITY_REF_FIELDS = {
    'hfid': 'hf', 'hfid1': 'hf', 'hfid2': 'hf',
    'group_1_hfid': 'hf', 'group_2_hfid': 'hf',
    'doer_hfid': 'hf', 'target_hfid': 'hf', 'hfid_target': 'hf', 'snatcher_hfid': 'hf',
    'attacker_hfid': 'hf', 'wounder_hfid': 'hf', 'slayer_hfid': 'hf',
    'actor_hfid': 'hf', 'student_hfid': 'hf', 'teacher_hfid': 'hf',
    'seeker_hfid': 'hf', 'victim_hfid': 'hf', 'hist_fig_id': 'hf',
    'giver_hist_figure_id': 'hf', 'receiver_hist_figure_id': 'hf',
    'group_hfid': 'hf',
    'civ_id': 'entity', 'source_entity_id': 'entity', 'target_entity_id': 'entity',
    'attacker_civ_id': 'entity', 'defender_civ_id': 'entity',
    'entity_id': 'entity', 'receiver_entity_id': 'entity', 'giver_entity_id': 'entity',
    'site_id': 'site', 'site_id1': 'site', 'site_id2': 'site',
    'artifact_id': 'artifact',
    'structure_id': 'structure',
    'region_id': 'region',
    'wcid': 'world_construction',
    'mountain_peak_id': 'mountain_peak',
}

# Grammatical roles for pronoun selection
SUBJECT_FIELDS = {
    'hfid', 'hfid1', 'doer_hfid', 'snatcher_hfid', 'attacker_hfid',
    'actor_hfid', 'student_hfid', 'seeker_hfid', 'group_1_hfid',
}
OBJECT_FIELDS = {
    'target_hfid', 'hfid_target', 'victim_hfid', 'hfid2', 'wounder_hfid', 'group_2_hfid',
}


def merge_columns_into_details(event: dict) -> dict:
    """Merge DB entity columns into the details dict using event-type-aware mapping.

    The DB stores entity IDs in generic columns (hf_id_1, hf_id_2, etc.)
    while templates expect DF XML field names (hfid, snatcher_hfid, etc.).
    This function maps columns back to their original template field names.
    """
    details = dict(event.get('details') or {})
    event_type = event.get('event_type') or event.get('type', '')
    col_map = COLUMN_MAP_BY_EVENT.get(event_type, _DEFAULT_COLUMN_MAP)

    for col in ENTITY_COLUMNS:
        val = event.get(col)
        if val is None:
            continue
        field_name = col_map.get(col)
        if field_name and field_name not in details:
            details[field_name] = val

    return details


# ── Link-type-aware templates for 'add hf entity link' ─────────────────────
_ADD_HF_LINK_TEMPLATES = {
    'enemy': '{hfid} became an enemy of {civ_id}',
    'member': '{hfid} joined {civ_id}',
    'prisoner': '{hfid} was imprisoned by {civ_id}',
    'slave': '{hfid} was enslaved by {civ_id}',
    'squad': '{hfid} joined a squad in {civ_id}',
    'criminal': '{hfid} became a criminal of {civ_id}',
}

# Fields to suppress from enrichment display — entity refs (already linked in
# narrative text), internal IDs, and coordinate noise.
_SUPPRESS_FROM_ENRICHMENT = frozenset(ENTITY_REF_FIELDS.keys()) | frozenset({
    'type', 'subtype', 'hist_event_collection_id', 'coords',
    # Plus-XML short entity reference names (values are raw numeric IDs)
    'histfig', 'civ', 'eater', 'entity', 'victim', 'woundee', 'wounder',
    'group', 'site_civ', 'slayer_hf', 'victim_hf', 'hf', 'hf_target',
    'trickster', 'student', 'teacher', 'target', 'stash_site',
    'victim_entity', 'entity_1', 'entity_2',
    'giver_hist_figure_id', 'receiver_hist_figure_id',
    'giver_entity_id', 'receiver_entity_id',
    # Numeric race/caste indices (not human-readable)
    'slayer_race', 'slayer_caste', 'woundee_race', 'woundee_caste',
    # Link/position fields consumed by dynamic templates
    'link_type', 'position',
    # Journey/travel fields consumed by dynamic templates or route UI
    'return', 'coords_x', 'coords_y',
})

# Numeric fields where integer values ARE meaningful (not entity IDs)
_NUMERIC_KEEP = frozenset({
    'quality', 'prison_months', 'bodies', 'account_shift',
    'top_value_rating', 'top_facet_rating', 'top_relationship_rating',
    'top_value_modifier', 'top_facet_modifier', 'top_relationship_modifier',
    'ally_defense_bonus',
})

# DF sentinel values that mean "no data"
_SENTINEL_VALUES = frozenset({'none', '-1', 'unknown', ''})


def extract_enrichment_details(event: dict, linker=None,
                               world_id: int = None,
                               name_cache: dict = None) -> dict:
    """Extract displayable enrichment fields not already shown in event text.

    Returns {display_label: display_value} for fields in the JSONB details
    that are NOT entity references, NOT consumed by template placeholders,
    and NOT sentinel/noise values.

    Values are HTML-escaped.  When *linker* / *name_cache* are provided,
    fields like ``reason`` and ``circumstance`` that reference HFs (via a
    companion ``*_id`` field) are enriched with clickable links.  Callers
    should render values with ``|safe`` in templates.
    """
    raw_details = event.get('details') or {}
    if not raw_details:
        return {}

    event_type = event.get('event_type') or event.get('type', '')
    template = EVENT_TEMPLATES.get(event_type, '')

    enrichment = {}
    for key, val in raw_details.items():
        if key in _SUPPRESS_FROM_ENRICHMENT:
            continue
        if val is None:
            continue
        # Skip fields already substituted into template text
        if '{' + key + '}' in template:
            continue
        # Suppress keys that look like entity ID references
        if key.endswith('_hfid') or key.endswith('_id') or key.endswith('_enid'):
            continue

        # Suppress pure-integer values (likely entity IDs) unless whitelisted
        if key not in _NUMERIC_KEEP and isinstance(val, (int, float)):
            continue
        if key not in _NUMERIC_KEEP and isinstance(val, str):
            try:
                int(val)
                continue  # Pure integer string → likely an entity ID
            except (ValueError, TypeError):
                pass

        label = key.replace('_', ' ').title()

        if isinstance(val, dict):
            parts = [f"{escape(k.replace('_', ' ').title())}: {escape(str(v))}"
                     for k, v in val.items()
                     if v is not None and str(v).lower() not in _SENTINEL_VALUES]
            if parts:
                enrichment[label] = '; '.join(parts)
        elif isinstance(val, list):
            enrichment[label] = ', '.join(escape(str(v)) for v in val)
        else:
            sv = str(val)
            if sv.lower() in _SENTINEL_VALUES:
                continue
            enrichment[label] = escape(sv)

    # ── Resolve HF references in reason/circumstance fields ─────────────
    if linker and name_cache:
        for text_field, id_field in [('reason', 'reason_id'),
                                     ('circumstance', 'circumstance_id')]:
            label = text_field.replace('_', ' ').title()
            if label not in enrichment:
                continue
            hf_id_raw = raw_details.get(id_field)
            if not hf_id_raw or str(hf_id_raw) in ('-1', 'none', ''):
                continue
            try:
                hf_id = int(hf_id_raw)
            except (ValueError, TypeError):
                continue
            name = name_cache.get(('hf', hf_id), f'HF #{hf_id}')
            link_html = linker.link('hf', hf_id, name, world_id)
            # Replace bare 'hf' placeholder in text like "glorify hf"
            text = enrichment[label]
            if ' hf' in text.lower():
                enrichment[label] = text.replace(' hf', f' {link_html}')
                enrichment[label] = enrichment[label].replace(' Hf',
                                                              f' {link_html}')
            else:
                # Append link if no 'hf' placeholder found
                enrichment[label] = f'{text} ({link_html})'

    return enrichment


class PerspectiveRenderer:
    """Render events from a specific entity's perspective.

    When the 'perspective entity' appears in an event, it is replaced with
    gender-aware pronouns (he/she/they). All other entities become cross-linked.
    """

    def __init__(self, linker: EntityLinkRenderer, world_id: int,
                 perspective_caste: str = None):
        self.linker = linker
        self.world_id = world_id
        # DF caste encodes biological sex: MALE, FEMALE, or None
        self._gender = self._caste_to_gender(perspective_caste)

    @staticmethod
    def _caste_to_gender(caste: str | None) -> str:
        """Map DF caste field to grammatical gender for pronoun selection."""
        if not caste:
            return 'neutral'
        c = caste.strip().upper()
        if c in ('MALE', 'M'):
            return 'male'
        if c in ('FEMALE', 'F'):
            return 'female'
        return 'neutral'

    def render_event(self, event: dict, perspective_type: str,
                     perspective_id: int, name_cache: dict = None) -> str:
        """Render a single event with perspective-aware substitutions.

        Args:
            event: Dict with at least 'type' and 'details' (JSONB),
                   plus optional DB columns (hf_id_1, hf_id_2, etc.).
            perspective_type: Entity type being viewed ('hf', 'site', etc.)
            perspective_id: Entity ID of the page owner
            name_cache: Optional {(type, id): name} mapping for fast lookups

        Returns:
            HTML string with linked entity names and perspective pronouns.
        """
        details = merge_columns_into_details(event)
        event_type = event.get('event_type') or event.get('type', '')

        # Custom renderer for complex event types
        if event_type == 'hf does interaction':
            return self._render_hf_does_interaction(
                details, perspective_type, perspective_id, name_cache
            )

        # Template-based rendering (dynamic overrides + static fallback)
        template = self._resolve_template(event_type, details)
        if template:
            return self._render_template(
                template, details, perspective_type, perspective_id, name_cache
            )

        # Fallback: build a generic description from details
        return self._render_generic(
            event_type, details, perspective_type, perspective_id, name_cache
        )

    # ── Dynamic template resolution ────────────────────────────────────────
    def _resolve_template(self, event_type: str, details: dict) -> str | None:
        """Select the right template, handling context-dependent event types."""
        if event_type == 'add hf entity link':
            link = (details.get('link_type')
                    or details.get('link') or 'member').lower()
            if link == 'position':
                pos = details.get('position', '')
                if pos and pos != '-1':
                    # {position} placeholder will be replaced by _render_template
                    return '{hfid} became {position} of {civ_id}'
                return '{hfid} took a position in {civ_id}'
            return _ADD_HF_LINK_TEMPLATES.get(link,
                                              '{hfid} joined {civ_id}')

        if event_type == 'change hf state':
            if details.get('site_id') is not None:
                return '{hfid} became {state} in {site_id}'
            return '{hfid} became {state}'

        if event_type == 'artifact stored':
            has_hf = details.get('hfid') is not None
            has_site = details.get('site_id') is not None
            if has_hf and has_site:
                return '{hfid} stored {artifact_id} at {site_id}'
            elif has_hf:
                return '{hfid} stored {artifact_id}'
            elif has_site:
                return '{artifact_id} was stored at {site_id}'
            return '{artifact_id} was stored'

        if event_type == 'artifact recovered':
            has_hf = details.get('hfid') is not None
            has_site = details.get('site_id') is not None
            if has_hf and has_site:
                return '{hfid} recovered {artifact_id} at {site_id}'
            elif has_hf:
                return '{hfid} recovered {artifact_id}'
            elif has_site:
                return '{artifact_id} was recovered at {site_id}'
            return '{artifact_id} was recovered'

        if event_type == 'hf died':
            has_site = details.get('site_id') is not None
            cause = details.get('cause', '')
            if has_site and cause:
                return '{hfid} died ({cause}) at {site_id}'
            elif has_site:
                return '{hfid} died at {site_id}'
            elif cause:
                return '{hfid} died ({cause})'
            return '{hfid} died'

        if event_type == 'creature devoured':
            has_eater = details.get('hfid') is not None
            has_victim = details.get('target_hfid') is not None
            if has_eater and has_victim:
                return '{hfid} devoured {target_hfid}'
            elif has_eater:
                return '{hfid} devoured a creature'
            elif has_victim:
                return '{target_hfid} was devoured'
            return 'a creature was devoured'

        if event_type == 'item stolen':
            has_hf = details.get('hfid') is not None
            has_site = details.get('site_id') is not None
            if has_hf and has_site:
                return '{hfid} stole {item} from {site_id}'
            elif has_hf:
                return '{hfid} stole {item}'
            elif has_site:
                return '{item} was stolen from {site_id}'
            return '{item} was stolen'

        if event_type == 'artifact given':
            has_giver_hf = details.get('giver_hist_figure_id') is not None
            has_receiver_hf = details.get('receiver_hist_figure_id') is not None
            has_receiver_ent = details.get('receiver_entity_id') is not None
            if has_giver_hf and has_receiver_hf:
                return '{giver_hist_figure_id} gave {artifact_id} to {receiver_hist_figure_id}'
            elif has_giver_hf and has_receiver_ent:
                return '{giver_hist_figure_id} gave {artifact_id} to {receiver_entity_id}'
            elif has_giver_hf:
                return '{giver_hist_figure_id} gave away {artifact_id}'
            return '{artifact_id} was given'

        if event_type == 'hf simple battle event':
            subtype = (details.get('subtype') or '').lower()
            verb_map = {
                'attacked': 'attacked',
                'scuffle': 'scuffled with',
                'ambushed': 'ambushed',
                'confront': 'confronted',
                'happen upon': 'happened upon',
                'corner': 'cornered',
                'surprised': 'surprised',
                'subdued': 'subdued',
                'got into a brawl': 'brawled with',
            }
            if '2 lost after' in subtype:
                return '{group_1_hfid} fought {group_2_hfid} (' + subtype + ')'
            verb = verb_map.get(subtype, 'fought')
            return '{group_1_hfid} ' + verb + ' {group_2_hfid}'

        if event_type == 'hf travel':
            is_return = details.get('return') is True
            has_site = details.get('site_id') is not None
            has_region = details.get('region_id') is not None
            if is_return and has_site:
                return '{hfid} returned to {site_id}'
            elif is_return and has_region:
                return '{hfid} returned to {region_id}'
            elif has_site:
                return '{hfid} traveled to {site_id}'
            elif has_region:
                return '{hfid} traveled through {region_id}'
            return '{hfid} traveled'

        return EVENT_TEMPLATES.get(event_type)

    # ── Custom renderer: hf does interaction ───────────────────────────────
    def _render_hf_does_interaction(self, details: dict, persp_type: str,
                                    persp_id: int,
                                    name_cache: dict = None) -> str:
        """Render interaction events with readable verbs instead of raw IDs.

        Raw DF identifiers like ``DEITY_CURSE_WEREBEAST_bull_BITE`` are
        replaced with a human-readable verb, with the raw ID shown in a
        muted parenthetical for reference.
        """
        raw_interaction = details.get('interaction', '')

        # Choose a clean verb based on the interaction pattern
        if '_BITE' in raw_interaction:
            verb = 'afflicted'
        elif 'CURSE' in raw_interaction:
            verb = 'cursed'
        else:
            verb = 'interacted with'

        # Render doer (subject)
        doer_val = details.get('doer_hfid')
        if doer_val is not None:
            if persp_type == 'hf' and int(doer_val) == persp_id:
                doer_html = f'<em>{self._pronoun("doer_hfid", persp_type)}</em>'
            else:
                name = self._resolve_name('hf', doer_val, name_cache)
                doer_html = self.linker.link('hf', doer_val, name,
                                             self.world_id)
        else:
            doer_html = '?'

        # Render target (object)
        target_val = details.get('target_hfid')
        if target_val is not None:
            if persp_type == 'hf' and int(target_val) == persp_id:
                target_html = (
                    f'<em>{self._pronoun("target_hfid", persp_type)}</em>')
            else:
                name = self._resolve_name('hf', target_val, name_cache)
                target_html = self.linker.link('hf', target_val, name,
                                               self.world_id)
        else:
            target_html = ''

        # Build result
        parts = [doer_html, verb]
        if target_html:
            parts.append(target_html)
        result = ' '.join(parts)

        # Append raw identifier in muted parens for reference
        if raw_interaction:
            result += (f' <span class="text-stone-600 text-xs">'
                       f'({escape(raw_interaction)})</span>')

        return result

    def _render_template(self, template: str, details: dict,
                         persp_type: str, persp_id: int,
                         name_cache: dict = None) -> str:
        """Replace template placeholders with linked names or pronouns."""
        result = template
        for field, entity_type in ENTITY_REF_FIELDS.items():
            placeholder = '{' + field + '}'
            if placeholder not in result:
                continue

            val = details.get(field)
            if val is None:
                result = result.replace(placeholder, '?')
                continue

            # Is this the perspective entity?
            if entity_type == persp_type and int(val) == persp_id:
                pronoun = self._pronoun(field, persp_type)
                result = result.replace(placeholder, f'<em>{pronoun}</em>')
            else:
                name = self._resolve_name(entity_type, val, name_cache)
                link = self.linker.link(entity_type, val, name, self.world_id)
                result = result.replace(placeholder, link)

        # Replace non-entity placeholders with raw values
        for key, val in details.items():
            placeholder = '{' + key + '}'
            if placeholder in result:
                result = result.replace(placeholder, escape(str(val)) if val else '?')

        # Clean up unresolved '?' placeholders left from any remaining {field}
        # patterns that didn't match details keys
        import re as _re
        result = _re.sub(r'\{[a-z_]+\}', '?', result)

        # Post-render cleanup: rewrite sentences with leading '?' to passive
        result = self._clean_unresolved(result)
        return result

    @staticmethod
    def _clean_unresolved(text: str) -> str:
        """Rewrite sentences containing '?' to remove ambiguity.

        Patterns handled:
        - '? verb obj ...'  → 'obj was verb-ed ...' (passive rewrite)
        - '... at ?'        → '...' (drop trailing unknown location)
        - '... to ?'        → '...' (drop trailing unknown destination)
        - '... from ?'      → '...' (drop trailing unknown origin)
        """
        import re as _re
        # Drop trailing ' at/to/from/by ?' (unknown location/destination)
        text = _re.sub(r'\s+(?:at|to|from|by|in)\s+\?$', '', text)
        # Drop mid-sentence ' at/to/from ?' before other clauses
        text = _re.sub(r'\s+(?:at|to|from|by|in)\s+\?\s*(?=[—(])', ' ', text)
        # Leading '? verb ...' → passive: move the verb's object forward
        if text.startswith('? '):
            rest = text[2:]
            # Try to find the verb + known object pattern:
            # '? stored <obj> at <loc>' → '<obj> was stored at <loc>'
            # '? stole <obj> from <loc>' → '<obj> was stolen from <loc>'
            passive_map = {
                'stored': 'was stored',
                'stole': 'was stolen',
                'recovered': 'was recovered',
                'created': 'was created',
                'devoured': 'was devoured',
                'fought': 'fought',
                'attacked': 'was attacked',
                'abducted': 'was abducted',
            }
            for verb, passive in passive_map.items():
                if rest.startswith(verb + ' '):
                    after_verb = rest[len(verb) + 1:]
                    text = f'{after_verb.split(" ", 1)[0] if after_verb else "something"} {passive}'
                    if ' ' in after_verb:
                        text += ' ' + after_verb.split(' ', 1)[1]
                    break
            else:
                # Generic: just drop the '?'
                text = rest
        # Clean up any remaining isolated '?'
        text = _re.sub(r'\s*—\s*\?\s*', '', text)
        text = _re.sub(r'\?\s*$', '', text).strip()
        return text

    def _render_generic(self, event_type: str, details: dict,
                        persp_type: str, persp_id: int,
                        name_cache: dict = None) -> str:
        """Build a generic event description by listing entity references."""
        parts = [f'<span class="text-stone-500">{escape(event_type)}</span>']

        for field, entity_type in ENTITY_REF_FIELDS.items():
            val = details.get(field)
            if val is None:
                continue

            if entity_type == persp_type and int(val) == persp_id:
                pronoun = self._pronoun(field, persp_type)
                parts.append(f'<em>{pronoun}</em>')
            else:
                name = self._resolve_name(entity_type, val, name_cache)
                link = self.linker.link(entity_type, val, name, self.world_id)
                label = field.replace('_', ' ').replace('hfid', 'HF').replace('id', '')
                parts.append(f'{label}: {link}')

        return ' — '.join(parts) if len(parts) > 1 else parts[0]

    def _pronoun(self, field: str, persp_type: str = 'hf') -> str:
        """Select pronoun based on entity type, gender, and grammatical role.

        For HFs, uses caste-derived gender:
          MALE   -> he/him/his
          FEMALE -> she/her/her
          other  -> they/them/their
        """
        if persp_type == 'hf':
            g = self._gender
            if field in SUBJECT_FIELDS:
                return {'male': 'he', 'female': 'she'}.get(g, 'they')
            if field in OBJECT_FIELDS:
                return {'male': 'him', 'female': 'her'}.get(g, 'them')
            # possessive/default
            return {'male': 'he', 'female': 'she'}.get(g, 'they')
        if persp_type == 'site':
            return 'here'
        if persp_type == 'entity':
            return 'the civilization'
        if persp_type == 'artifact':
            return 'this artifact'
        if persp_type == 'region':
            return 'this region'
        if persp_type == 'structure':
            return 'this structure'
        return 'this'

    @staticmethod
    def _resolve_name(entity_type: str, entity_id, name_cache: dict = None) -> str:
        """Look up a name from the cache or return a fallback."""
        if name_cache:
            key = (entity_type, int(entity_id))
            cached = name_cache.get(key)
            if cached:
                return cached
        type_label = entity_type.replace('_', ' ').title()
        return f"{type_label} #{entity_id}"
