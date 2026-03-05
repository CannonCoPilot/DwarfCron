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

from chronicler.explorer.death_cause import DeathCauseRenderer
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
    # ── Stage 3.1b: New event templates ──────────────────────────────────────
    # Occasion events
    'competition': '{winner_hfid} won a competition at {site_id}',
    'performance': 'a performance was held at {site_id}',
    'ceremony': 'a ceremony was held at {site_id}',
    'procession': 'a procession was held at {site_id}',
    'gamble': '{gambler_hfid} gambled at {site_id}',
    # Diplomacy / Intrigue
    'agreement formed': 'an agreement was formed',
    'trade': '{trader_hfid} traded goods',
    'failed intrigue corruption': '{corruptor_hfid} failed to corrupt {target_hfid}',
    'hfs formed intrigue relationship': '{corruptor_hfid} corrupted {target_hfid}',
    'hf convicted': '{convicted_hfid} was convicted of {crime}',
    'failed frame attempt': '{framer_hfid} failed to frame {target_hfid} for {crime}',
    'hf interrogated': '{interrogator_hfid} interrogated {target_hfid}',
    'hf ransomed': '{ransomer_hfid} ransomed {ransomed_hfid}',
    'hf enslaved': '{seller_hfid} enslaved {enslaved_hfid}',
    # Artifact events
    'artifact claim formed': '{hfid} claimed {artifact_id}',
    'artifact lost': '{artifact_id} was lost at {site_id}',
    'artifact found': '{hfid} found {artifact_id} at {site_id}',
    'artifact possessed': '{hfid} came to possess {artifact_id}',
    'artifact destroyed': '{artifact_id} was destroyed at {site_id}',
    'artifact copied': '{artifact_id} was copied',
    'hf viewed artifact': '{hfid} viewed {artifact_id} at {site_id}',
    # Site/Construction
    'site dispute': '{civ_id} and {defender_civ_id} had a dispute',
    'new site leader': '{new_leader_hfid} became the new leader of {site_id}',
    'replaced structure': '{civ_id} replaced a structure at {site_id}',
    'modified building': '{modifier_hfid} modified a building at {site_id}',
    'building profile acquired': '{acquirer_hfid} acquired a building profile at {site_id}',
    'sneak into site': '{hfid} snuck into {site_id}',
    'holy city declaration': 'a holy city was declared at {site_id}',
    # Entity events
    'entity dissolved': '{civ_id} dissolved',
    'entity incorporated': '{joiner_entity_id} was incorporated into {joined_entity_id}',
    'entity overthrown': '{instigator_hfid} overthrew {overthrown_hfid} at {site_id}',
    'entity law': '{civ_id} enacted a law',
    'entity persecuted': '{persecutor_hfid} persecuted {target_enid} at {site_id}',
    'entity primary criminals': '{civ_id} identified primary criminals at {site_id}',
    'entity relocate': '{civ_id} relocated at {site_id}',
    'entity alliance formed': '{initiating_enid} formed an alliance with {joining_enid}',
    'entity equipment purchase': '{hfid} purchased equipment for {civ_id}',
    'entity breach feature layer': 'a feature layer was breached at {site_id}',
    'regionpop incorporated into entity': 'a population was incorporated at {site_id}',
    # Culture/Art
    'poetic form created': '{hfid} created a poetic form at {site_id}',
    'musical form created': '{hfid} created a musical form at {site_id}',
    'dance form created': '{hfid} created a dance form at {site_id}',
    # HF actions
    'hf preach': '{speaker_hfid} preached about {topic}',
    'hf prayed inside structure': '{hfid} prayed inside {structure_id} at {site_id}',
    'hf profaned structure': '{hfid} profaned {structure_id} at {site_id}',
    'hf disturbed structure': '{hfid} disturbed {structure_id} at {site_id}',
    'hf performed horrible experiments': '{hfid} performed horrible experiments at {site_id}',
    'hf gains secret goal': '{hfid} gained a secret goal',
    'hf equipment purchase': '{hfid} purchased equipment',
    'add hf entity honor': '{hfid} received an honor from {civ_id}',
    'change hf body state': '{hfid} changed body state at {site_id}',
    'remove hf site link': '{hfid} departed from {site_id}',
    # Military
    'squad vs squad': 'a squad battle occurred at {site_id}',
    'tactical situation': 'a tactical situation developed at {site_id}',
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
    # ── Stage 3.1b: Column maps for new event templates ──────────────────────
    'competition': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id',
    },
    'performance': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id',
    },
    'ceremony': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id',
    },
    'procession': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id',
    },
    'gamble': {
        'site_id': 'site_id', 'structure_id': 'structure_id',
    },
    'trade': {},  # all fields in JSONB
    'failed intrigue corruption': {
        'hf_id_2': 'target_hfid', 'site_id': 'site_id',
    },
    'hfs formed intrigue relationship': {
        'hf_id_2': 'target_hfid', 'site_id': 'site_id',
    },
    'hf convicted': {},  # all fields in JSONB
    'failed frame attempt': {
        'hf_id_2': 'target_hfid',
    },
    'hf interrogated': {
        'hf_id_2': 'target_hfid',
    },
    'hf ransomed': {},  # all fields in JSONB
    'hf enslaved': {},  # all fields in JSONB
    'artifact claim formed': {
        'hf_id_1': 'hfid', 'entity_id_1': 'civ_id', 'artifact_id': 'artifact_id',
    },
    'artifact lost': {
        'site_id': 'site_id', 'artifact_id': 'artifact_id', 'region_id': 'region_id',
    },
    'artifact found': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'artifact_id': 'artifact_id',
    },
    'artifact possessed': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'artifact_id': 'artifact_id',
    },
    'artifact destroyed': {
        'site_id': 'site_id', 'artifact_id': 'artifact_id',
    },
    'artifact copied': {
        'artifact_id': 'artifact_id',
    },
    'hf viewed artifact': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'artifact_id': 'artifact_id',
        'structure_id': 'structure_id',
    },
    'site dispute': {
        'entity_id_1': 'civ_id', 'entity_id_2': 'defender_civ_id',
    },
    'new site leader': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id', 'entity_id_2': 'defender_civ_id',
    },
    'replaced structure': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id', 'entity_id_2': 'defender_civ_id',
    },
    'modified building': {
        'site_id': 'site_id', 'structure_id': 'structure_id',
    },
    'building profile acquired': {
        'site_id': 'site_id',
    },
    'sneak into site': {
        'site_id': 'site_id', 'entity_id_2': 'defender_civ_id',
    },
    'holy city declaration': {
        'site_id': 'site_id',
    },
    'entity dissolved': {
        'entity_id_1': 'civ_id',
    },
    'entity incorporated': {},  # all fields in JSONB
    'entity overthrown': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id',
    },
    'entity law': {
        'hf_id_1': 'hfid', 'entity_id_1': 'civ_id',
    },
    'entity persecuted': {
        'site_id': 'site_id',
    },
    'entity primary criminals': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id',
    },
    'entity relocate': {
        'site_id': 'site_id', 'entity_id_1': 'civ_id', 'structure_id': 'structure_id',
    },
    'entity alliance formed': {},  # all fields in JSONB
    'entity equipment purchase': {
        'hf_id_1': 'hfid', 'entity_id_1': 'civ_id',
    },
    'entity breach feature layer': {
        'site_id': 'site_id',
    },
    'regionpop incorporated into entity': {
        'site_id': 'site_id',
    },
    'poetic form created': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'musical form created': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'dance form created': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'hf preach': {},  # all fields in JSONB
    'hf prayed inside structure': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'structure_id': 'structure_id',
    },
    'hf profaned structure': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'structure_id': 'structure_id',
    },
    'hf disturbed structure': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'structure_id': 'structure_id',
    },
    'hf performed horrible experiments': {
        'hf_id_1': 'hfid', 'site_id': 'site_id',
    },
    'hf gains secret goal': {
        'hf_id_1': 'hfid',
    },
    'hf equipment purchase': {
        'hf_id_1': 'hfid',
    },
    'add hf entity honor': {
        'hf_id_1': 'hfid', 'entity_id_1': 'civ_id',
    },
    'change hf body state': {
        'hf_id_1': 'hfid', 'site_id': 'site_id', 'structure_id': 'structure_id',
    },
    'remove hf site link': {
        'site_id': 'site_id',
    },
    'squad vs squad': {
        'site_id': 'site_id',
    },
    'tactical situation': {
        'site_id': 'site_id',
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
    'source': 'entity', 'destination': 'entity',  # peace accepted/rejected
    'new_site_civ_id': 'entity', 'new_leader_hfid': 'hf',
    'appointer_hfid': 'hf', 'promise_to_hfid': 'hf',
    'creator_hfid': 'hf', 'winner_hfid': 'hf', 'competitor_hfid': 'hf',
    'trader_hfid': 'hf', 'corruptor_hfid': 'hf',
    'builder_hfid': 'hf', 'maker_hfid': 'hf',
    'dest_site_id': 'site', 'source_site_id': 'site',
    'moved_to_site_id': 'site',
    'site_id': 'site', 'site_id1': 'site', 'site_id2': 'site',
    'site_id_1': 'site', 'site_id_2': 'site',
    'artifact_id': 'artifact',
    'structure_id': 'structure',
    'region_id': 'region',
    'wcid': 'world_construction',
    'mountain_peak_id': 'mountain_peak',
    # Stage 3.1b: new JSONB-only entity ref fields
    'gambler_hfid': 'hf', 'speaker_hfid': 'hf', 'site_hfid': 'hf',
    'convicted_hfid': 'hf', 'framer_hfid': 'hf', 'fooled_hfid': 'hf',
    'interrogator_hfid': 'hf', 'ransomer_hfid': 'hf', 'ransomed_hfid': 'hf',
    'seller_hfid': 'hf', 'enslaved_hfid': 'hf', 'payer_hfid': 'hf',
    'instigator_hfid': 'hf', 'overthrown_hfid': 'hf', 'pos_taker_hfid': 'hf',
    'modifier_hfid': 'hf', 'acquirer_hfid': 'hf', 'last_owner_hfid': 'hf',
    'persecutor_hfid': 'hf', 'leader_hfid': 'hf',
    'a_hfid': 'hf', 'a_tactician_hfid': 'hf', 'd_tactician_hfid': 'hf',
    'lure_hfid': 'hf', 'plotter_hfid': 'hf',
    'convicter_enid': 'entity', 'persecutor_enid': 'entity',
    'target_enid': 'entity', 'destroyer_enid': 'entity',
    'arresting_enid': 'entity', 'payer_entity_id': 'entity',
    'site_civ_id': 'entity', 'new_site_civ_id': 'entity',
    'joiner_entity_id': 'entity', 'joined_entity_id': 'entity',
    'initiating_enid': 'entity', 'joining_enid': 'entity',
    'trader_entity_id': 'entity', 'religion_id': 'entity',
    'join_entity_id': 'entity',
    'civ_entity_id': 'entity', 'site_entity_id': 'entity',
    'dest_structure_id': 'structure', 'source_structure_id': 'structure',
    'dest_entity_id': 'entity',
}

# Grammatical roles for pronoun selection
SUBJECT_FIELDS = {
    'hfid', 'hfid1', 'doer_hfid', 'snatcher_hfid', 'attacker_hfid',
    'actor_hfid', 'student_hfid', 'seeker_hfid', 'group_1_hfid',
    'gambler_hfid', 'speaker_hfid', 'corruptor_hfid', 'framer_hfid',
    'instigator_hfid', 'modifier_hfid', 'acquirer_hfid', 'persecutor_hfid',
    'ransomer_hfid', 'seller_hfid', 'interrogator_hfid', 'trader_hfid',
}
OBJECT_FIELDS = {
    'target_hfid', 'hfid_target', 'victim_hfid', 'hfid2', 'wounder_hfid', 'group_2_hfid',
    'convicted_hfid', 'overthrown_hfid', 'ransomed_hfid', 'enslaved_hfid',
    'fooled_hfid', 'lure_hfid',
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

# ── Reason/Circumstance templates for enrichment display ──────────────────
# Map raw DF reason codes to natural-language phrases.
# {hf} placeholder is replaced with a linked HF name when reason_id is present.
REASON_TEMPLATES = {
    'none': None,  # suppress
    'be_with_master': 'to be with their master',
    'glorify hf': 'to glorify {hf}',
    'gather_information': 'to gather information',
    'prefers working alone': 'prefers working alone',
    'as_a_matter_of_course': 'as a matter of course',
    'on_a_pilgrimage': 'on a pilgrimage',
    'flight': 'in flight',
    'scholarship': 'for scholarship',
    'jealousy': 'out of jealousy',
    'threat_of_violence': 'under threat of violence',
    'force_of_argument': 'by force of argument',
    'collaboration': 'through collaboration',
    'wave_of_popular_support': 'on a wave of popular support',
    'failed mood': 'after a failed mood',
    'ageless': 'being ageless',
    'sanctify_hf': 'to sanctify {hf}',
    'murder': 'by murder',
    'artifact is symbol of entity position': 'the artifact symbolizes a position',
    'artifact is heirloom of family hfid': 'the artifact is a family heirloom',
    'heavy losses in battle': 'due to heavy losses in battle',
}

# Map raw DF circumstance codes to natural-language phrases.
# {hf} is replaced with a linked HF name when circumstance_id is present.
CIRCUMSTANCE_TEMPLATES = {
    'dream': 'in a dream',
    'nightmare': 'in a nightmare',
    'pray to hf': 'while praying to {hf}',
    'from afar': 'from afar',
    'dream about hf': 'dreaming about {hf}',
    'is entity subordinate': 'as an entity subordinate',
    'hf is dead': 'after {hf} died',
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
    # Death cause fields consumed by DeathCauseRenderer
    'cause', 'death_cause',
    # Internal scheduling/profiling IDs consumed by templates
    'occasion_id', 'schedule_id', 'form_id', 'agreement_id',
    'building_profile_id', 'honor_id', 'position_profile_id',
    'feature_layer_id', 'production_zone_id', 'allotment_index',
    'pop_srid', 'old_ab_id', 'new_ab_id',
    'relevant_position_profile_id', 'relevant_id_for_method',
    'corruptor_identity', 'target_identity', 'corruptor_seen_as', 'target_seen_as',
    'confessed_after_apb_arrest_enid',
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

    # ── Apply reason/circumstance templates ──────────────────────────────
    for text_field, id_field, template_map in [
        ('reason', 'reason_id', REASON_TEMPLATES),
        ('circumstance', 'circumstance_id', CIRCUMSTANCE_TEMPLATES),
    ]:
        label = text_field.replace('_', ' ').title()
        raw_val = raw_details.get(text_field)
        if raw_val is None:
            continue

        # Handle JSON-object circumstances (e.g. {"type": "favoritepossession"})
        if isinstance(raw_val, dict):
            ctype = raw_val.get('type', '')
            if ctype == 'favoritepossession':
                enrichment[label] = 'regarding a favorite possession'
            elif ctype == 'preservebody':
                enrichment[label] = 'to preserve the body'
            elif ctype == 'histeventcollection':
                coll_id = raw_val.get('hist_event_collection')
                if coll_id and linker:
                    enrichment[label] = (
                        f'during <a href="/explorer/collection/{coll_id}'
                        f'?world_id={world_id}" class="entity-link">'
                        f'event collection #{coll_id}</a>'
                    )
                else:
                    enrichment[label] = f'during event collection #{coll_id}'
            elif ctype == 'defeated':
                defeated_id = raw_val.get('defeated')
                if defeated_id and linker and name_cache:
                    try:
                        did = int(defeated_id)
                        name = name_cache.get(('hf', did), f'HF #{did}')
                        link_html = linker.link('hf', did, name, world_id)
                        enrichment[label] = f'after defeating {link_html}'
                    except (ValueError, TypeError):
                        enrichment[label] = 'after defeating an opponent'
                else:
                    enrichment[label] = 'after defeating an opponent'
            else:
                enrichment[label] = escape(str(raw_val))
            continue

        sv = str(raw_val).strip()
        # Look up template
        tmpl = template_map.get(sv)
        if tmpl is None and sv.lower() != 'none':
            # Fallback: humanize the raw string
            tmpl = sv.replace('_', ' ')

        if tmpl is None:
            # Suppress 'none' values
            enrichment.pop(label, None)
            continue

        # Resolve {hf} placeholder with linked name
        if '{hf}' in tmpl and linker and name_cache:
            hf_id_raw = raw_details.get(id_field)
            if hf_id_raw and str(hf_id_raw) not in ('-1', 'none', ''):
                try:
                    hf_id = int(hf_id_raw)
                    name = name_cache.get(('hf', hf_id), f'HF #{hf_id}')
                    link_html = linker.link('hf', hf_id, name, world_id)
                    tmpl = tmpl.replace('{hf}', link_html)
                except (ValueError, TypeError):
                    tmpl = tmpl.replace('{hf}', '?')
            else:
                tmpl = tmpl.replace('{hf}', '?')

        enrichment[label] = tmpl

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
            # Render cause via DeathCauseRenderer for human-readable text
            if cause:
                rendered_cause = DeathCauseRenderer.render_event_cause(cause)
                details['_rendered_cause'] = rendered_cause
                if has_site:
                    return '{hfid} ' + rendered_cause + ' at {site_id}'
                return '{hfid} ' + rendered_cause
            elif has_site:
                return '{hfid} died at {site_id}'
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

        # ── Dynamic overrides for new event types ─────────────────────────
        if event_type == 'competition':
            has_winner = details.get('winner_hfid') is not None
            has_competitor = details.get('competitor_hfid') is not None
            if has_winner and has_competitor:
                return '{winner_hfid} won a competition against {competitor_hfid} at {site_id}'
            elif has_winner:
                return '{winner_hfid} won a competition at {site_id}'
            return 'a competition was held at {site_id}'

        if event_type == 'gamble':
            account = details.get('new_account')
            old = details.get('old_account')
            if account is not None and old is not None:
                try:
                    shift = int(account) - int(old)
                    verb = 'won' if shift > 0 else 'lost'
                    details['_gamble_result'] = f'{verb} {abs(shift)}'
                except (ValueError, TypeError):
                    pass
            return '{gambler_hfid} gambled at {site_id}'

        if event_type == 'trade':
            has_dest = details.get('dest_site_id') is not None
            has_source = details.get('source_site_id') is not None
            if has_source and has_dest:
                return '{trader_hfid} traded from {source_site_id} to {dest_site_id}'
            elif has_dest:
                return '{trader_hfid} traded at {dest_site_id}'
            return '{trader_hfid} traded goods'

        if event_type == 'entity dissolved':
            reason = details.get('reason', '')
            if reason:
                details['_dissolve_reason'] = reason.replace('_', ' ')
            return '{civ_id} dissolved'

        if event_type == 'entity overthrown':
            has_pos_taker = details.get('pos_taker_hfid') is not None
            if has_pos_taker:
                return '{instigator_hfid} overthrew {overthrown_hfid}, replaced by {pos_taker_hfid}'
            return '{instigator_hfid} overthrew {overthrown_hfid} at {site_id}'

        if event_type == 'hf preach':
            topic = (details.get('topic') or '').replace('_', ' ')
            if topic:
                return '{speaker_hfid} preached about ' + escape(topic)
            return '{speaker_hfid} preached'

        if event_type == 'change hf body state':
            body_state = (details.get('body_state') or '').replace('_', ' ')
            if body_state:
                return '{hfid} became ' + escape(body_state) + ' at {site_id}'
            return '{hfid} changed body state at {site_id}'

        if event_type == 'hf gains secret goal':
            goal = (details.get('secret_goal') or '').replace('_', ' ')
            if goal:
                return '{hfid} gained the secret goal: ' + escape(goal)
            return '{hfid} gained a secret goal'

        if event_type == 'remove hf site link':
            link_type = (details.get('link_type') or '').lower()
            if link_type == 'occupation':
                return '{hfid} ended occupation of {site_id}'
            elif link_type == 'seat of power':
                return '{hfid} left the seat of power at {site_id}'
            elif link_type == 'lair':
                return '{hfid} left their lair at {site_id}'
            return '{hfid} departed from {site_id}'

        if event_type == 'artifact claim formed':
            claim = (details.get('claim') or '').replace('_', ' ')
            if claim:
                return '{hfid} claimed {artifact_id} (' + escape(claim) + ')'
            return '{hfid} claimed {artifact_id}'

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
