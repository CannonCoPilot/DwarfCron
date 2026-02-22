"""DFHack bridge — reads game state from a JSON file served by DFHack's Lua bridge.

DFHack 53.10-r1's RPC CoreSuspend is broken (RunCommand hangs from the RPC
server thread on all platforms). Core API methods (ListUnits, GetWorldInfo,
ListEnums, ListSquads) work fine but don't provide game time or creature raws.

Workaround: A Lua script runs as a DFHack `repeat` job on the console thread
(where CoreSuspend works), writing comprehensive game state to a JSON file.
A PowerShell HTTP server on the DF machine serves the file. This module reads it.

Bridge data sections (v6):
  - game_time: cur_year, cur_year_tick, cur_season
  - creature_raws: race_id -> creature_id mapping (934+ entries)
  - unit_summary: fortress units with stress/profession/flags/mood
  - armies: count + positions + member counts
  - buildings: total + type distribution
  - artifacts: named artifacts with translated names
  - announcements: cursor-based game reports (lossless)
  - diplomacy: player civ diplomatic relations
  - history: cursor-based events with payloads (lossless)
  - world_info: world name, fortress name, civ/site IDs
  - entities: nearby civilizations with names and types
  - dwarf_skills: per-dwarf full skill lists
  - dwarf_emotions: per-dwarf emotion/thought vectors (v6)
  - zones: fortress civzones with types and assignments (v6)
  - event_collections: active wars/battles/sieges (v6)
  - squads: military squads with members and orders (v6)
  - mandates: noble mandates with items and timeouts (v6)
  - incidents: crimes and incidents with victims/criminals (v6)

Setup on the Windows DF machine:
  1. Place chronicler-bridge.lua in a dir listed in script-paths.txt
  2. In DFHack console: repeat --name chronicler --time 100 --timeUnits ticks --command [ chronicler-bridge ]
  3. Start PowerShell HTTP server on port 8888 serving DF directory
"""

import json
import logging
import urllib.request
import urllib.error

log = logging.getLogger(__name__)

_BRIDGE_TIMEOUT = 5.0  # seconds


def fetch_bridge_data(host: str, port: int = 8888,
                      path: str = 'chronicler-state.json') -> dict | None:
    """Fetch bridge data from the PowerShell HTTP server on the DF machine.

    Returns the full parsed dict, or None on any error.
    """
    url = f'http://{host}:{port}/{path}'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=_BRIDGE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            log.debug("Bridge data: year=%s tick=%s creatures=%s sections=%s",
                      data.get('cur_year'), data.get('cur_year_tick'),
                      data.get('creature_count'),
                      [k for k in data.keys() if k not in
                       ('cur_year', 'cur_year_tick', 'cur_season',
                        'creature_raws', 'creature_count', 'timestamp')])
            return data
    except urllib.error.URLError as e:
        log.debug("Bridge fetch failed (URL): %s", e)
        return None
    except json.JSONDecodeError as e:
        log.warning("Bridge data parse error: %s", e)
        return None
    except Exception as e:
        log.debug("Bridge fetch failed: %s", e)
        return None


def build_race_map(bridge_data: dict | None) -> dict[int, str]:
    """Build race_id (int) -> creature_id (str) mapping from bridge data.

    Bridge data has creature_raws as {str_id: name}, e.g. {"572": "DWARF"}.
    Returns {572: "DWARF", ...} for use in unit enrichment.
    """
    if not bridge_data or 'creature_raws' not in bridge_data:
        return {}
    return {int(k): v for k, v in bridge_data['creature_raws'].items()}


def get_game_time(bridge_data: dict | None) -> tuple[int | None, int | None]:
    """Extract game year and tick from bridge data.

    Returns (cur_year, cur_year_tick) or (None, None) if unavailable.
    """
    if not bridge_data:
        return None, None
    return bridge_data.get('cur_year'), bridge_data.get('cur_year_tick')


def get_fortress_units(bridge_data: dict | None) -> list[dict]:
    """Extract fortress unit list from bridge data.

    Returns list of dicts with: id, name, first_name, stress, focus,
    longterm_stress, combat_hardened, profession, squad_id, is_alive, pos.
    """
    if not bridge_data:
        return []
    summary = bridge_data.get('unit_summary', {})
    return summary.get('fortress_units', [])


def get_race_distribution(bridge_data: dict | None) -> dict[str, int]:
    """Get active unit counts by race ID from bridge data.

    Returns {race_id_str: count} from the unit_summary section.
    """
    if not bridge_data:
        return {}
    summary = bridge_data.get('unit_summary', {})
    return summary.get('race_counts', {})


def get_armies(bridge_data: dict | None) -> list[dict]:
    """Get army list from bridge data.

    Returns list of dicts with: id, pos_x, pos_y, member_count, controller_id.
    """
    if not bridge_data:
        return []
    return bridge_data.get('armies', {}).get('armies', [])


def get_buildings(bridge_data: dict | None) -> dict:
    """Get building summary from bridge data.

    Returns dict with: total (int), by_type (dict[str, int]).
    """
    if not bridge_data:
        return {}
    return bridge_data.get('buildings', {})


def get_artifacts(bridge_data: dict | None) -> list[dict]:
    """Get named artifact list from bridge data.

    Returns list of dicts with: id, name, name_english, item_type, site_id.
    """
    if not bridge_data:
        return []
    return bridge_data.get('artifacts', {}).get('artifacts', [])


def get_announcements(bridge_data: dict | None) -> list[dict]:
    """Get recent game announcements from bridge data.

    Returns list of dicts with: id, text, year, time, type.
    """
    if not bridge_data:
        return []
    return bridge_data.get('announcements', {}).get('recent', [])


def get_diplomacy(bridge_data: dict | None) -> dict:
    """Get player civ diplomatic relations from bridge data.

    Returns dict with: civ_id, relation_count, relations (list).
    """
    if not bridge_data:
        return {}
    return bridge_data.get('diplomacy', {})


def get_history(bridge_data: dict | None) -> dict:
    """Get history summary from bridge data.

    Returns dict with: figure_count, event_count, recent_events (list).
    """
    if not bridge_data:
        return {}
    return bridge_data.get('history', {})


def get_world_info(bridge_data: dict | None) -> dict:
    """Get world and fortress names from bridge data.

    Returns dict with: world_name, world_name_english, fortress_name,
    fortress_name_english, civ_id, race_id, site_id.
    """
    if not bridge_data:
        return {}
    return bridge_data.get('world_info', {})


def get_entities(bridge_data: dict | None) -> list[dict]:
    """Get entity/civilization list from bridge data.

    Returns list of dicts with: id, name, name_english, type, race, is_player.
    """
    if not bridge_data:
        return []
    return bridge_data.get('entities', {}).get('entities', [])


def get_dwarf_skills(bridge_data: dict | None) -> list[dict]:
    """Get per-dwarf skill lists from bridge data.

    Returns list of dicts with: id, first_name, skill_count,
    skills (list of {id, rating, experience}).
    """
    if not bridge_data:
        return []
    return bridge_data.get('dwarf_skills', {}).get('dwarves', [])


# ── v6 Accessor Functions ────────────────────────────────────────────


def get_bridge_version(bridge_data: dict | None) -> int:
    """Get bridge script version. Returns 0 if not set (pre-v6)."""
    if not bridge_data:
        return 0
    return bridge_data.get('bridge_version', 0)


def get_dwarf_emotions(bridge_data: dict | None) -> list[dict]:
    """Get per-dwarf emotion vectors from bridge data (v6+).

    Returns list of dicts with: id, first_name, emotion_count,
    emotions (list of {type, thought, subthought, strength, severity, year, year_tick}).
    """
    if not bridge_data:
        return []
    return bridge_data.get('dwarf_emotions', {}).get('dwarves', [])


def get_zones(bridge_data: dict | None) -> list[dict]:
    """Get fortress civzones from bridge data (v6+).

    Returns list of dicts with: id, type, x1, y1, x2, y2, z,
    assigned_unit_count, is_active, name, owner_unit_id.
    """
    if not bridge_data:
        return []
    return bridge_data.get('zones', {}).get('zones', [])


def get_event_collections(bridge_data: dict | None) -> list[dict]:
    """Get historical event collections from bridge data (v6+).

    Returns list of dicts with: id, type, start_year, end_year,
    event_count, name, attacker_civ, defender_civ, site_id,
    attacker_name, defender_name.
    """
    if not bridge_data:
        return []
    return bridge_data.get('event_collections', {}).get('collections', [])


def get_squads(bridge_data: dict | None) -> list[dict]:
    """Get military squads from bridge data (v6+).

    Returns list of dicts with: id, name, name_english, alias,
    members (list of {position, histfig_id}), member_count,
    position_count, order_count, entity_id.
    """
    if not bridge_data:
        return []
    return bridge_data.get('squads', {}).get('squads', [])


def get_mandates(bridge_data: dict | None) -> list[dict]:
    """Get noble mandates from bridge data (v6+).

    Returns list of dicts with: mode, item_type, item_subtype,
    amount_total, amount_remaining, timeout_counter, timeout_limit,
    unit_id, unit_name.
    """
    if not bridge_data:
        return []
    return bridge_data.get('mandates', {}).get('mandates', [])


def get_incidents(bridge_data: dict | None) -> list[dict]:
    """Get crimes and incidents from bridge data (v6+).

    Returns list of dicts with: id, type, event_year, event_time,
    victim, criminal, site, death_cause, conflict_level.
    """
    if not bridge_data:
        return []
    return bridge_data.get('incidents', {}).get('incidents', [])


def get_announcement_cursor(bridge_data: dict | None) -> int:
    """Get the current announcement cursor from bridge data (v6+).

    Returns the highest seen report ID, or -1 if unavailable.
    """
    if not bridge_data:
        return -1
    return bridge_data.get('announcements', {}).get('cursor', -1)


def get_history_cursor(bridge_data: dict | None) -> int:
    """Get the current history event cursor from bridge data (v6+).

    Returns the highest seen event ID, or -1 if unavailable.
    """
    if not bridge_data:
        return -1
    return bridge_data.get('history', {}).get('cursor', -1)
