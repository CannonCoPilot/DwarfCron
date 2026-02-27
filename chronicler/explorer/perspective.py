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
    'hf new pet': '{hfid} gained a new pet {pet}',
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
        'hf_id_1': 'hfid', 'site_id': 'site_id',
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
    'civ_id': 'entity', 'source_entity_id': 'entity', 'target_entity_id': 'entity',
    'attacker_civ_id': 'entity', 'defender_civ_id': 'entity',
    'entity_id': 'entity',
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

        # Try template-based rendering first
        template = EVENT_TEMPLATES.get(event_type)
        if template:
            return self._render_template(
                template, details, perspective_type, perspective_id, name_cache
            )

        # Fallback: build a generic description from details
        return self._render_generic(
            event_type, details, perspective_type, perspective_id, name_cache
        )

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

        return result

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
